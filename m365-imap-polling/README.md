# M365 Email Reaction System: IMAP Polling & Graph API

## Executive Summary

For a daemon/service that reacts to incoming email on Microsoft 365, there are two viable approaches: **IMAP with OAuth2** and **Microsoft Graph API**. This report covers both in detail. The recommendation for new projects is to **use Microsoft Graph API** (webhooks + delta queries) unless you have a specific reason to use IMAP.

**Why Graph over IMAP:**
- Near-real-time push notifications via webhooks (avg <1 min latency)
- No persistent connection management
- Granular mailbox scoping via RBAC for Applications
- Richer filtering and query capabilities
- Better supported long-term (EWS deprecated Oct 2026; IMAP is "legacy protocol" in Microsoft's docs)
- Conditional Access policies frequently block IMAP; Graph is unaffected

---

## 1. OAuth 2.0 for IMAP on M365

### 1.1 Azure AD / Entra ID App Registration

**Step-by-step:**

1. Go to **portal.azure.com** > **Microsoft Entra ID** > **App registrations** > **New registration**
2. Name your app (e.g., "Email Processor Service")
3. Set **Supported account types** to "Accounts in this organizational directory only" (for single-tenant)
4. No redirect URI needed for daemon apps
5. Click **Register**
6. Copy the **Application (client) ID** and **Directory (tenant) ID**
7. Go to **Certificates & secrets** > **New client secret** > copy the secret value immediately (it won't be shown again)

### 1.2 OAuth Flow Selection for Daemon/Service

| Flow | Use Case | Recommendation |
|------|----------|----------------|
| **Client Credentials** | Daemon with no user interaction | **Best for services** |
| ROPC (Resource Owner Password) | Legacy; requires username/password | **Avoid** - deprecated pattern |
| Device Code | Interactive device login | Not suitable for unattended services |
| Authorization Code | User-interactive apps | Not suitable for daemons |

**Use the Client Credentials flow.** This is the only flow appropriate for unattended daemon services.

### 1.3 Required API Permissions

For IMAP access via client credentials:

1. In your app registration, go to **API Permissions** > **Add a permission**
2. Select the **APIs my organization uses** tab
3. Search for **"Office 365 Exchange Online"**
4. Select **Application permissions**
5. Choose **IMAP.AccessAsApp**
6. Click **Add permissions**
7. Click **Grant admin consent for [your org]**

**Critical distinction:**
- `IMAP.AccessAsApp` = Application permission (for daemons) 
- `IMAP.AccessAsUser.All` = Delegated permission (for interactive apps)

**Token scope for the request:** `https://outlook.office365.com/.default`

For multi-tenant or ISV apps, the admin consent scope for POP/IMAP is `https://ps.outlook.com/.default`.

### 1.4 Exchange Online Service Principal Registration (CRITICAL STEP)

This is the step most people miss. Even after granting admin consent, you must register the service principal in Exchange and grant mailbox permissions:

```powershell
# Install and connect
Install-Module -Name ExchangeOnlineManagement
Import-Module ExchangeOnlineManagement
Connect-ExchangeOnline -Organization <tenantId>

# Register the service principal
# IMPORTANT: Use the Object ID from Enterprise Applications, NOT App Registrations
$AADServicePrincipalDetails = Get-AzureADServicePrincipal -SearchString "Email Processor Service"

New-ServicePrincipal -AppId $AADServicePrincipalDetails.AppId `
    -ObjectId $AADServicePrincipalDetails.ObjectId `
    -DisplayName "EXO SP for Email Processor"

# Get the Exchange service principal identity
$EXOServicePrincipal = Get-ServicePrincipal -Identity "EXO SP for Email Processor"

# Grant access to specific mailbox(es)
Add-MailboxPermission -Identity "inbox@contoso.com" `
    -User $EXOServicePrincipal.Identity `
    -AccessRights FullAccess
```

**Key gotcha:** The `ObjectId` parameter must come from the **Enterprise Applications** blade in Entra, not the **App Registrations** blade. These are different Object IDs.

### 1.5 Token Acquisition & Refresh

```python
import msal

TENANT_ID = "your-tenant-id"
CLIENT_ID = "your-client-id"
CLIENT_SECRET = "your-client-secret"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["https://outlook.office365.com/.default"]

app = msal.ConfidentialClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    client_credential=CLIENT_SECRET,
)

def get_access_token():
    # MSAL caches tokens and handles refresh automatically
    result = app.acquire_token_for_client(scopes=SCOPES)
    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception(f"Token acquisition failed: {result.get('error_description')}")
```

**Token refresh handling:** With client credentials flow, there are no refresh tokens. The access token is typically valid for 1 hour. MSAL's `acquire_token_for_client()` automatically caches tokens and returns cached ones if still valid. Just call it before each operation.

### 1.6 Shared Mailbox Access

For IMAP with client credentials:
- Obtain the access token as normal (the token is for the application, not a user)
- In the SASL XOAUTH2 string, use the **shared mailbox email address** as the username
- The service principal must have `FullAccess` permission on the shared mailbox via `Add-MailboxPermission`

```python
# For shared mailbox, just use the shared mailbox email in auth string
shared_mailbox = "shared-inbox@contoso.com"
auth_string = f"user={shared_mailbox}\x01auth=Bearer {access_token}\x01\x01"
```

---

## 2. Microsoft Graph API (Recommended Alternative)

### 2.1 App Registration for Graph

Same registration process as IMAP, but with different permissions:

1. **API Permissions** > **Add a permission** > **Microsoft Graph**
2. **Application permissions** (not delegated)
3. Add: `Mail.Read` (or `Mail.ReadBasic` for metadata only)
4. Grant admin consent

### 2.2 Restricting Access to Specific Mailboxes (RBAC for Applications)

By default, `Mail.Read` application permission grants access to ALL mailboxes in the tenant. To restrict:

**New approach (RBAC for Applications) - replaces Application Access Policies:**

```powershell
# Connect to Exchange Online
Connect-ExchangeOnline -Organization <tenantId>

# Create service principal pointer
New-ServicePrincipal -AppId <Client-App-ID> `
    -ObjectId <Enterprise-App-Object-ID> `
    -DisplayName "Email Processor"

# Create a management scope to limit access
New-ManagementScope -Name "ProcessorMailboxes" `
    -RecipientRestrictionFilter "CustomAttribute1 -eq 'EmailProcessor'"

# Assign the Mail.Read role with scope restriction
New-ManagementRoleAssignment `
    -App <Enterprise-App-Object-ID> `
    -Role "Application Mail.Read" `
    -CustomResourceScope "ProcessorMailboxes"

# IMPORTANT: Remove the unscoped Mail.Read from Entra ID
# Otherwise the union of scoped + unscoped = unscoped (all mailboxes)
```

**Cache note:** RBAC permission changes take 30 minutes to 2 hours to propagate.

### 2.3 Graph Mail Endpoints

```
# List messages in a mailbox
GET /users/{user-id-or-email}/messages
GET /users/{user-id-or-email}/mailFolders/inbox/messages

# Get a specific message
GET /users/{user-id-or-email}/messages/{message-id}

# Get message with specific properties
GET /users/{user-id-or-email}/messages/{message-id}?$select=subject,from,receivedDateTime,body

# List attachments
GET /users/{user-id-or-email}/messages/{message-id}/attachments

# Get specific attachment content
GET /users/{user-id-or-email}/messages/{message-id}/attachments/{attachment-id}/$value
```

### 2.4 Graph Webhooks (Change Notifications)

Webhooks provide near-real-time push notifications when new emails arrive.

**Creating a subscription:**

```http
POST https://graph.microsoft.com/v1.0/subscriptions
Content-Type: application/json

{
    "changeType": "created",
    "notificationUrl": "https://your-service.example.com/api/webhook",
    "resource": "users/inbox@contoso.com/messages",
    "expirationDateTime": "2026-04-18T00:00:00Z",
    "clientState": "your-secret-validation-token"
}
```

**Key parameters:**

| Parameter | Details |
|-----------|---------|
| `changeType` | `created`, `updated`, `deleted` (comma-separated for multiple) |
| `resource` | `users/{id}/messages` or `users/{id}/mailFolders('inbox')/messages` |
| `expirationDateTime` | Max 7 days (10,080 min) for basic; max 1 day for rich notifications |
| `notificationUrl` | Must be HTTPS, TLS 1.2+, respond to validation within 10 seconds |
| `lifecycleNotificationUrl` | Recommended: receives `subscriptionRemoved`, `reauthorizationRequired`, `missed` events |

**Subscription lifetime:**
- Basic notifications (no resource data): **max 7 days**
- Rich notifications (with resource data): **max 1 day**
- Must renew before expiry via `PATCH /subscriptions/{id}`

**Notification latency:** Average <1 minute, maximum 3 minutes for mail.

**Limits:** Max 1,000 active subscriptions per mailbox across all applications.

**Rich notifications (with message content in the payload):**

```http
POST https://graph.microsoft.com/v1.0/subscriptions
{
    "changeType": "created",
    "notificationUrl": "https://your-service.example.com/api/webhook",
    "resource": "users/inbox@contoso.com/messages?$select=subject,bodyPreview,from,receivedDateTime",
    "expirationDateTime": "2026-04-12T00:00:00Z",
    "clientState": "your-secret",
    "includeResourceData": true,
    "encryptionCertificate": "<base64-encoded-public-key>",
    "encryptionCertificateId": "myCertId"
}
```

Rich notifications encrypt the resource data with your public key. You must decrypt with the corresponding private key.

**Filtering notifications:**

```
# Only new unread messages
"resource": "users/{id}/mailFolders('inbox')/messages?$filter=isRead eq false"

# Only messages with attachments and high importance
"resource": "users/{id}/mailFolders('Drafts')/messages?$filter=hasAttachments eq true AND importance eq 'High'"
```

### 2.5 Delta Queries (Efficient Polling)

Delta queries let you poll for changes since the last check without re-fetching everything.

```
# Initial request
GET /users/{id}/mailFolders/{folder-id}/messages/delta

# Returns @odata.nextLink (more pages) or @odata.deltaLink (caught up)
# Save the deltaLink

# Subsequent polls - only returns changes since last deltaLink
GET {saved-deltaLink}
```

**Delta query supports filtering by change type:**
```
GET /users/{id}/mailFolders/{folder-id}/messages/delta?changeType=created
```

**OData query support in delta:**
- `$select` - specify properties (always returns `id`)
- `$top` - limit page size  
- `$filter` - limited: only `receivedDateTime ge/gt {value}`
- `$orderby` - only `receivedDateTime desc`
- No `$search` support

**Important caveat:** Delta queries can return events that don't match your filter:
- `@removed` entries with `"reason": "deleted"` when items are deleted or moved
- Read/unread state changes
- These are inherent to folder-level sync tracking

### 2.6 Webhooks vs IMAP IDLE Comparison

| Feature | Graph Webhooks | IMAP IDLE |
|---------|---------------|-----------|
| Latency | Avg <1 min, max 3 min | Near-instant (seconds) |
| Connection model | Stateless HTTP push | Persistent TCP connection |
| Requires public endpoint | Yes (HTTPS) | No |
| Connection stability | No connection to maintain | Must handle drops, reconnect |
| Concurrent connection limits | N/A | ~8 per mailbox (Exchange Online) |
| Filtering | Rich OData filters | Folder-level only |
| Payload in notification | Optional (rich notifications) | Must FETCH separately |
| Max lifetime | 7 days (must renew) | Must re-IDLE every 29 min (RFC) |
| Alternative delivery | Event Hubs, Event Grid | N/A |
| Works behind firewall | Needs inbound HTTPS | Outbound only |

**For services without a public endpoint:** Use Graph delta queries (polling) or Event Hubs delivery instead of webhooks.

### 2.7 Alternative Notification Delivery (No Public Endpoint Needed)

**Azure Event Hubs:** Graph can push notifications to an Event Hub instead of a webhook URL. Best for:
- High-throughput scenarios
- Multi-tenant applications
- Services behind firewalls (no inbound HTTPS needed)

**Azure Event Grid:** For event-driven architectures. Supports routing to multiple destinations from a single Graph subscription.

### 2.8 Attachment Handling

| Size | Method |
|------|--------|
| < 3 MB | Direct GET on attachment endpoint |
| 3 MB - 150 MB | Upload session (chunked upload/download) |

**Downloading attachments:**
```
# List attachments
GET /users/{id}/messages/{msg-id}/attachments

# Get attachment content (small files)
GET /users/{id}/messages/{msg-id}/attachments/{att-id}

# For large files, the content is in the response's contentBytes property
# or use $value for raw binary
GET /users/{id}/messages/{msg-id}/attachments/{att-id}/$value
```

The 3 MB guideline exists because base64 encoding adds ~33% overhead, and the JSON payload limit is 4 MB.

---

## 3. Python Libraries

### 3.1 MSAL (Microsoft Authentication Library) - Token Management

**Install:** `pip install msal`

The foundation for all approaches. Handles OAuth2 token acquisition, caching, and refresh.

```python
import msal

# Client credentials flow (daemon)
app = msal.ConfidentialClientApplication(
    "client-id",
    authority="https://login.microsoftonline.com/tenant-id",
    client_credential="client-secret",
)

# For IMAP
token = app.acquire_token_for_client(
    scopes=["https://outlook.office365.com/.default"]
)

# For Graph API
token = app.acquire_token_for_client(
    scopes=["https://graph.microsoft.com/.default"]
)
```

### 3.2 Python imaplib + MSAL (IMAP with OAuth2)

Complete working example for daemon IMAP access:

```python
import imaplib
import base64
import msal
import email
import time

TENANT_ID = "your-tenant-id"
CLIENT_ID = "your-client-id"
CLIENT_SECRET = "your-client-secret"
MAILBOX = "inbox@contoso.com"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["https://outlook.office365.com/.default"]

app = msal.ConfidentialClientApplication(
    CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
)

def get_access_token():
    result = app.acquire_token_for_client(scopes=SCOPES)
    if "access_token" in result:
        return result["access_token"]
    raise Exception(f"Failed: {result.get('error_description')}")

def generate_xoauth2_string(user, token):
    """Generate SASL XOAUTH2 auth string."""
    auth_string = f"user={user}\x01auth=Bearer {token}\x01\x01"
    return auth_string.encode()

def connect_imap():
    token = get_access_token()
    imap = imaplib.IMAP4_SSL("outlook.office365.com", 993)
    
    # Authenticate with XOAUTH2
    imap.authenticate(
        "XOAUTH2",
        lambda _: generate_xoauth2_string(MAILBOX, token)
    )
    return imap

def poll_inbox(interval_seconds=60):
    """Simple polling loop."""
    seen_uids = set()
    
    while True:
        try:
            imap = connect_imap()
            imap.select("INBOX")
            
            # Search for unseen messages
            status, data = imap.search(None, "UNSEEN")
            if status == "OK":
                uids = data[0].split()
                for uid in uids:
                    if uid not in seen_uids:
                        seen_uids.add(uid)
                        status, msg_data = imap.fetch(uid, "(RFC822)")
                        if status == "OK":
                            msg = email.message_from_bytes(msg_data[0][1])
                            process_email(msg)
            
            imap.logout()
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(interval_seconds)

def process_email(msg):
    print(f"New email: {msg['Subject']} from {msg['From']}")
```

### 3.3 imap_tools + MSAL

`imap_tools` provides a cleaner API than raw imaplib and has built-in XOAUTH2 support:

**Install:** `pip install imap-tools msal`

```python
from imap_tools import MailBox, AND
import msal

app = msal.ConfidentialClientApplication(
    CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
)

def get_token():
    result = app.acquire_token_for_client(scopes=["https://outlook.office365.com/.default"])
    return result["access_token"]

# Connect using xoauth2
token = get_token()
with MailBox("outlook.office365.com").xoauth2(MAILBOX, token) as mailbox:
    # Fetch unread messages
    for msg in mailbox.fetch(AND(seen=False)):
        print(f"Subject: {msg.subject}")
        print(f"From: {msg.from_}")
        print(f"Date: {msg.date}")
        print(f"Body: {msg.text[:200]}")
        
        # Handle attachments
        for att in msg.attachments:
            print(f"  Attachment: {att.filename} ({len(att.payload)} bytes)")
```

### 3.4 python-o365 (Graph API wrapper)

**Install:** `pip install O365`

Version 2.1 (Feb 2025). Actively maintained. Wraps Graph API with Pythonic interface.

```python
from O365 import Account

credentials = ("client-id", "client-secret")

# Client credentials flow (daemon) - requires tenant_id
account = Account(
    credentials,
    auth_flow_type="credentials",
    tenant_id="your-tenant-id",
)

# Access a specific mailbox
mailbox = account.mailbox(resource="inbox@contoso.com")
inbox = mailbox.inbox_folder()

# Get unread messages
for message in inbox.get_messages(limit=25, query=mailbox.new_query().on_attribute("isRead").equals(False)):
    print(f"Subject: {message.subject}")
    print(f"From: {message.sender}")
    
    # Download attachments
    for attachment in message.attachments:
        attachment.save("/tmp/attachments/")
    
    # Mark as read
    message.mark_as_read()
```

**Features:**
- Automatic token refresh
- Shared mailbox support via `resource` parameter
- Built-in pagination
- OData query builder
- Attachment handling

**Limitations:** No built-in webhook/subscription support for notifications.

### 3.5 msgraph-sdk-python (Official Microsoft SDK)

**Install:** `pip install msgraph-sdk azure-identity`

Version 1.51.0 (Jan 2026). Official Microsoft SDK. Async-friendly.

```python
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.users.item.mail_folders.item.messages.delta.delta_request_builder import DeltaRequestBuilder
from kiota_abstractions.base_request_configuration import RequestConfiguration

# Authentication
credential = ClientSecretCredential(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-client-secret",
)

client = GraphServiceClient(credential)

# List messages
async def list_messages(user_id: str):
    messages = await client.users.by_user_id(user_id).messages.get()
    for msg in messages.value:
        print(f"{msg.subject} - {msg.from_.email_address.address}")

# Delta query for efficient polling
async def poll_with_delta(user_id: str, folder_id: str):
    config = RequestConfiguration()
    config.headers.add("Prefer", "odata.maxpagesize=50")
    
    result = await client.users.by_user_id(user_id)\
        .mail_folders.by_mail_folder_id(folder_id)\
        .messages.delta.get(request_configuration=config)
    
    # Process messages
    for msg in result.value:
        print(f"New/changed: {msg.subject}")
    
    # Save the delta link for next poll
    # result.odata_delta_link contains the URL for next call
    return result.odata_delta_link

# Create webhook subscription
async def create_subscription(user_id: str):
    from msgraph.generated.models.subscription import Subscription
    
    sub = Subscription()
    sub.change_type = "created"
    sub.notification_url = "https://your-service.example.com/webhook"
    sub.resource = f"users/{user_id}/messages"
    sub.expiration_date_time = "2026-04-18T00:00:00Z"
    sub.client_state = "secret-validation-token"
    
    result = await client.subscriptions.post(sub)
    return result

# Get message with attachments
async def get_attachments(user_id: str, message_id: str):
    attachments = await client.users.by_user_id(user_id)\
        .messages.by_message_id(message_id)\
        .attachments.get()
    
    for att in attachments.value:
        print(f"Attachment: {att.name}, Size: {att.size}")
```

### 3.6 exchangelib

**Install:** `pip install exchangelib`

**Status:** Actively maintained (latest release Oct 2025), supports OAuth2.

**WARNING:** exchangelib uses Exchange Web Services (EWS), which Microsoft is deprecating. **EWS will be turned off October 1, 2026 for Exchange Online.** Do not use for new projects targeting M365.

### 3.7 Library Comparison

| Library | Protocol | Auth | Daemon Support | Webhooks | Best For |
|---------|----------|------|----------------|----------|----------|
| imaplib + msal | IMAP | OAuth2 | Yes | No | Low-level IMAP control |
| imap_tools + msal | IMAP | OAuth2 | Yes | No | Simple IMAP with nice API |
| python-o365 | Graph | OAuth2 | Yes | No | Quick Graph API integration |
| msgraph-sdk | Graph | OAuth2 | Yes | Yes | Full Graph feature set |
| exchangelib | EWS | OAuth2 | Yes | No | **Avoid** (EWS deprecated Oct 2026) |

---

## 4. Practical Gotchas

### 4.1 Rate Limiting & Throttling

**Graph API (Outlook service):**
- **10,000 requests per 10 minutes** per app per mailbox
- **4 concurrent requests** per app per mailbox
- **130,000 requests per 10 seconds** per app across all tenants (global)
- Starting **September 30, 2025**: per-app/per-user limit reduced to half of per-tenant limit
- Webhook notification delivery is NOT counted against Graph API limits
- 429 responses include `Retry-After` header; honor it
- Microsoft Graph SDKs have built-in retry handlers

**IMAP (Exchange Online):**
- ~**8 concurrent IMAP connections** per mailbox (not officially documented, observed in practice)
- Microsoft does not publish IMAP-specific throttling numbers
- Throttling policies are not exposed or configurable in Exchange Online
- Connection can be silently dropped under load

**Best practices:**
```python
import time
from requests.exceptions import HTTPError

def graph_request_with_retry(func, max_retries=5):
    for attempt in range(max_retries):
        try:
            return func()
        except HTTPError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", 30))
                print(f"Throttled. Waiting {retry_after}s...")
                time.sleep(retry_after)
            else:
                raise
    raise Exception("Max retries exceeded")
```

### 4.2 Shared Mailbox Access

**Via Graph (recommended):**
```
GET /users/{shared-mailbox-email}/messages
```
Works with application permissions (`Mail.Read`). No special configuration beyond ensuring the mailbox is in the RBAC scope.

**Via IMAP:**
- Service principal must have `FullAccess` on the shared mailbox via `Add-MailboxPermission`
- Use the shared mailbox email in the XOAUTH2 auth string

**Shared mailboxes do not need a license** for Graph API access with application permissions. They do need to exist in Exchange Online.

### 4.3 Large Attachments

**Graph API:**
- Inline attachments up to ~3 MB (4 MB JSON limit minus base64 overhead)
- For larger: use upload sessions (chunked, up to 150 MB)
- Download: `GET /users/{id}/messages/{id}/attachments/{id}/$value` returns raw binary

**IMAP:**
- No special handling needed; IMAP FETCH returns the full RFC822 message
- Very large messages may hit Exchange Online's 150 MB message size limit
- Consider streaming for large attachments to avoid memory issues

### 4.4 Connection Stability (IMAP)

**Problems:**
- Exchange Online drops idle IMAP connections after varying intervals
- IMAP IDLE has a 29-minute RFC timeout; Exchange may drop sooner
- Network issues cause silent connection loss
- OAuth2 tokens expire after ~1 hour

**Mitigation pattern:**
```python
import imaplib
import time

class ResilientIMAPPoller:
    def __init__(self, mailbox, get_token_func):
        self.mailbox = mailbox
        self.get_token = get_token_func
        self.imap = None
    
    def connect(self):
        token = self.get_token()
        self.imap = imaplib.IMAP4_SSL("outlook.office365.com", 993)
        auth_string = f"user={self.mailbox}\x01auth=Bearer {token}\x01\x01"
        self.imap.authenticate("XOAUTH2", lambda _: auth_string.encode())
        self.imap.select("INBOX")
    
    def poll(self):
        """Reconnect-on-failure polling loop."""
        while True:
            try:
                if self.imap is None:
                    self.connect()
                
                # NOOP keeps connection alive and checks for new mail
                status, response = self.imap.noop()
                if status != "OK":
                    raise Exception("NOOP failed")
                
                # Check for unseen messages
                status, data = self.imap.search(None, "UNSEEN")
                if status == "OK" and data[0]:
                    yield from self._fetch_messages(data[0].split())
                
            except (imaplib.IMAP4.error, OSError, Exception) as e:
                print(f"Connection error: {e}. Reconnecting...")
                self.imap = None
                time.sleep(5)  # Brief pause before reconnect
                continue
            
            time.sleep(30)  # Poll interval
    
    def _fetch_messages(self, uids):
        for uid in uids:
            status, data = self.imap.fetch(uid, "(RFC822)")
            if status == "OK":
                yield data[0][1]
```

### 4.5 Admin Policies That Block Access

**Conditional Access - "Block Legacy Authentication":**
- Many organizations enable this Microsoft-managed policy
- It blocks protocols like IMAP, POP, SMTP identified as "Other clients"
- **Even with OAuth2**, IMAP can be blocked if the Conditional Access policy targets "Other clients" without distinguishing auth method
- This is the #1 reason IMAP OAuth2 fails in practice despite correct configuration
- **Graph API is NOT affected** by legacy auth blocking policies

**Security Defaults:**
- Enabled by default on new tenants
- Blocks legacy authentication protocols including IMAP
- Must be disabled (or use Conditional Access instead) to allow IMAP

**Authentication Policies:**
- Per-user authentication policies can disable IMAP/POP
- Check: `Get-CASMailbox -Identity user@contoso.com | Select ImapEnabled`

**Recommendation:** If you control the tenant, verify IMAP is allowed. If you don't control the tenant (multi-tenant app), use Graph API to avoid these issues entirely.

### 4.6 SMTP AUTH Deprecation Timeline

- Basic Authentication for SMTP AUTH: **March 2026** start of permanent removal
- **April 30, 2026**: 100% rejection of Basic Auth SMTP submissions
- OAuth2 SMTP will continue to work

### 4.7 EWS Deprecation

- EWS will be **turned off October 1, 2026** for Exchange Online
- On-premises Exchange Server EWS continues indefinitely
- All new development should use Graph API

---

## 5. Recommended Architecture

### For a Daemon Email Reaction System:

**Option A: Graph Webhooks + Delta Queries (Best for most cases)**

```
[Graph Webhook] --> [Your HTTPS endpoint] --> [Process notification]
                                            --> [Fetch full message via Graph]
                                            --> [React/process]

[Periodic delta query] --> [Catch any missed notifications]
```

1. Create Graph subscription for `created` events on target mailbox inbox
2. Receive webhook notification when new email arrives (avg <1 min)
3. Fetch the full message content via Graph API
4. Process/react to the email
5. Run delta query every 5-10 minutes as a safety net for missed notifications
6. Renew subscription before 7-day expiry

**Option B: Graph Delta Query Polling (No public endpoint needed)**

```
[Cron/scheduler] --> [Delta query] --> [Process new messages]
```

1. Run delta query on a schedule (e.g., every 1-5 minutes)
2. First call returns all current messages; save deltaLink
3. Subsequent calls return only changes since last deltaLink
4. Process new/changed messages

**Option C: IMAP Polling (When IMAP is specifically required)**

```
[Daemon process] --> [IMAP connect + SEARCH UNSEEN] --> [FETCH + process]
                 --> [Reconnect on failure]
                 --> [Re-authenticate on token expiry]
```

1. Connect via IMAP with OAuth2
2. Poll INBOX for UNSEEN messages on interval
3. Fetch and process new messages
4. Handle connection drops and token refresh
5. Consider IMAP IDLE for lower latency (but manage 29-min timeout)

---

## Sources

- [Authenticate IMAP/POP/SMTP with OAuth - Microsoft Learn](https://learn.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth)
- [Change notifications for Outlook resources - Microsoft Graph](https://learn.microsoft.com/en-us/graph/outlook-change-notifications-overview)
- [Microsoft Graph change notifications API overview](https://learn.microsoft.com/en-us/graph/api/resources/change-notifications-api-overview?view=graph-rest-1.0)
- [Subscription resource type - Microsoft Graph](https://learn.microsoft.com/en-us/graph/api/resources/subscription?view=graph-rest-1.0)
- [message: delta - Microsoft Graph](https://learn.microsoft.com/en-us/graph/api/message-delta?view=graph-rest-1.0)
- [Microsoft Graph throttling guidance](https://learn.microsoft.com/en-us/graph/throttling)
- [Microsoft Graph service-specific throttling limits](https://learn.microsoft.com/en-us/graph/throttling-limits)
- [RBAC for Applications in Exchange Online](https://learn.microsoft.com/en-us/exchange/permissions-exo/application-rbac)
- [Exchange Online limits](https://learn.microsoft.com/en-us/office365/servicedescriptions/exchange-online-service-description/exchange-online-limits)
- [Block legacy authentication with Conditional Access](https://learn.microsoft.com/en-us/entra/identity/conditional-access/policy-block-legacy-authentication)
- [Receive change notifications through Azure Event Hubs](https://learn.microsoft.com/en-us/graph/change-notifications-delivery-event-hubs)
- [python-o365 GitHub](https://github.com/O365/python-o365)
- [msgraph-sdk-python GitHub](https://github.com/microsoftgraph/msgraph-sdk-python)
- [M365-IMAP (UvA-FNWI) GitHub](https://github.com/UvA-FNWI/M365-IMAP)
- [exchangelib GitHub](https://github.com/ecederstrand/exchangelib)
- [Deprecation of Basic authentication in Exchange Online](https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-online/deprecation-of-basic-authentication-exchange-online)
- [Microsoft's Modern Authentication Enforcement 2026](https://www.getmailbird.com/microsoft-modern-authentication-enforcement-email-guide/)
