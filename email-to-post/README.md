# Building Systems That React to Receiving an Email

How do you build a system where sending an email triggers an action? This report surveys the design space, with a deep dive into Microsoft 365 / Exchange Online — specifically IMAP polling and the Graph API alternative.

The anchoring example is "email-to-post" (send an email, publish a blog post), but the patterns apply to any email-triggered workflow: issue creation, data ingestion, approval flows, helpdesk ticketing, notification routing.

## Three Architectural Families

Every inbound email system falls into one of three categories, distinguished by **who receives the SMTP connection**.

### 1. Managed webhook services

A third-party service accepts mail on your behalf and POSTs a parsed payload to your HTTP endpoint.

```
Sender → MX record → [Mailgun/SendGrid/Postmark/SES] → HTTP POST → Your app
```

| Service | Price | Standout feature | Gotcha |
|---------|-------|-----------------|--------|
| Mailgun | $35/mo | Pre-strips quotes and signatures (`stripped-text`) | Priciest for low volume |
| SendGrid | $19.95/mo | SPF/DKIM/SpamAssassin in payload | Free tier discontinued May 2025 |
| Postmark | $16.50/mo | Clean JSON, `StrippedTextReply`, plus-addressing | Requires Pro tier |
| Amazon SES | ~$0.10/1K | Cheapest at scale; full auth verdicts | Body not in event — must fetch from S3 |
| Cloudflare Email Workers | Free | Zero marginal cost | Must parse email yourself; domain on Cloudflare |

### 2. Self-hosted SMTP server

You run your own mail server that accepts SMTP connections and triggers your code directly.

```
Sender → MX record → [Your SMTP server] → Your processing code
```

Options: **aiosmtpd** (Python, lightweight async), **Haraka** (Node.js, battle-tested at Craigslist scale), **Postfix + pipe-to-script** (classic Unix), **MXHook** (open-source SMTP-to-webhook bridge, like self-hosted Mailgun Routes), **Postal** (full open-source mail platform).

### 3. IMAP polling / mailbox monitoring

Your application periodically checks a standard mailbox for new messages. No DNS changes, no exposed servers.

```
Sender → Any mail provider → Mailbox ← [Your poller] (periodic fetch)
```

This is the focus of the rest of this report, specifically against Microsoft 365.

---

## Deep Dive: M365 Exchange Online

Two viable paths for reacting to email in a Microsoft 365 environment:

| | IMAP Polling | Graph API |
|---|---|---|
| **Protocol** | IMAP4 over TLS | HTTPS REST |
| **Auth** | OAuth2 client credentials + XOAUTH2 | OAuth2 client credentials |
| **Latency** | Polling interval (you choose) | Webhooks: avg <1 min. Delta polling: you choose |
| **Public endpoint needed** | No | Only for webhooks (not for delta polling) |
| **Connection management** | Must handle drops, reconnect, token refresh | Stateless HTTP calls |
| **Blocked by Conditional Access** | Often yes, even with OAuth2 | No |
| **Microsoft's recommendation** | "Legacy protocol" | Preferred path |
| **Setup complexity** | Medium-high (Exchange PowerShell required) | Medium |

### Path A: IMAP Polling with OAuth2

#### Setup Steps

**1. Register app in Entra ID (Azure portal)**

- Microsoft Entra ID > App registrations > New registration
- Name: e.g. "Email Processor Service"
- Account type: "Accounts in this organizational directory only"
- No redirect URI (daemon app)
- Copy the Application (client) ID and Directory (tenant) ID
- Certificates & secrets > New client secret > copy immediately

**2. Add API permissions**

- API Permissions > Add a permission > APIs my organization uses > "Office 365 Exchange Online"
- Application permissions > `IMAP.AccessAsApp`
- Grant admin consent

Critical distinction: `IMAP.AccessAsApp` is the application permission for daemons. `IMAP.AccessAsUser.All` is delegated (interactive apps) — wrong choice here.

**3. Register service principal in Exchange Online (the step everyone misses)**

This is the #1 reason IMAP OAuth2 setups fail. Admin consent in Entra is not enough — you must also register in Exchange:

```powershell
Install-Module -Name ExchangeOnlineManagement
Connect-ExchangeOnline -Organization <tenantId>

# IMPORTANT: Use Object ID from Enterprise Applications blade, NOT App Registrations
New-ServicePrincipal -AppId <client-id> `
    -ObjectId <enterprise-app-object-id> `
    -DisplayName "Email Processor"

# Grant access to the target mailbox
$sp = Get-ServicePrincipal | Where-Object { $_.AppId -eq "<client-id>" }
Add-MailboxPermission -Identity "inbox@contoso.com" `
    -User $sp.Identity -AccessRights FullAccess
```

See `setup_exchange_online.ps1` for the complete script.

**4. Connect and poll**

Token scope: `https://outlook.office365.com/.default`

```python
import msal
from imap_tools import MailBox, AND

app = msal.ConfidentialClientApplication(
    CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    client_credential=CLIENT_SECRET,
)

token = app.acquire_token_for_client(
    scopes=["https://outlook.office365.com/.default"]
)["access_token"]

with MailBox("outlook.office365.com").xoauth2(MAILBOX, token) as mailbox:
    for msg in mailbox.fetch(AND(seen=False)):
        # React to the email
        print(f"{msg.subject} from {msg.from_}")
        for att in msg.attachments:
            print(f"  Attachment: {att.filename} ({len(att.payload)} bytes)")
```

See `example_imap_poller.py` for a resilient polling loop with reconnection handling.

#### The Conditional Access Problem

Many M365 tenants enable "Block Legacy Authentication" policies. These can block IMAP **even when using OAuth2**, because the Conditional Access policy targets "Other clients" without distinguishing authentication method. This is the most common reason IMAP OAuth2 fails in practice despite correct configuration.

If you control the tenant, verify: Entra ID > Security > Conditional Access > check if any policy blocks "Other clients" or "Legacy authentication clients". You may need to exclude your service principal.

If you don't control the tenant, use Graph API instead — it is never affected by legacy auth blocking.

### Path B: Microsoft Graph API

Graph avoids the connection management and Conditional Access problems of IMAP, and offers both push (webhooks) and pull (delta queries).

#### Setup

Same Entra app registration, but different permission: `Mail.Read` (application permission) under Microsoft Graph. By default this grants access to **all mailboxes in the tenant**. Use RBAC for Applications to scope it:

```powershell
# Create a scope that limits to specific mailboxes
New-ManagementScope -Name "ProcessorMailboxes" `
    -RecipientRestrictionFilter "CustomAttribute1 -eq 'EmailProcessor'"

# Assign scoped role
New-ManagementRoleAssignment -App <object-id> `
    -Role "Application Mail.Read" `
    -CustomResourceScope "ProcessorMailboxes"

# Then remove the unscoped Mail.Read from Entra — otherwise the union = all mailboxes
```

RBAC changes take 30 min to 2 hours to propagate.

#### Option B1: Delta Query Polling (no public endpoint needed)

Delta queries return only messages that changed since your last check. First call returns everything; save the `deltaLink`. Subsequent calls return only new/changed items.

```python
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient

credential = ClientSecretCredential(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
client = GraphServiceClient(credential)

# First call: full sync
result = await client.users.by_user_id(MAILBOX)\
    .mail_folders.by_mail_folder_id("inbox")\
    .messages.delta.get()

for msg in result.value:
    print(f"{msg.subject} from {msg.from_.email_address.address}")

# Save result.odata_delta_link → use it for next poll (only returns changes)
```

See `example_graph_poller.py` for a complete implementation with state persistence.

#### Option B2: Webhooks (near-real-time push)

Graph pushes a notification to your HTTPS endpoint when new mail arrives. Average latency <1 minute.

```http
POST https://graph.microsoft.com/v1.0/subscriptions
{
    "changeType": "created",
    "notificationUrl": "https://your-app.example.com/api/webhook",
    "resource": "users/inbox@contoso.com/mailFolders('inbox')/messages",
    "expirationDateTime": "2026-04-18T00:00:00Z",
    "clientState": "your-secret-validation-token"
}
```

Key constraints:
- Max subscription lifetime: **7 days** (must renew)
- Notification URL must be HTTPS with TLS 1.2+, must respond to validation within 10 seconds
- Must return 2xx within 3 seconds on each notification (enqueue for async processing)
- Use `lifecycleNotificationUrl` to catch `missed` events — then backfill with a delta query

See `example_graph_webhook_handler.py` for a Flask handler.

**If you don't have a public endpoint**: Use Azure Event Hubs as the delivery channel instead of webhooks. Same subscription API, different delivery target. Or just use delta query polling (Option B1).

#### Option B3: Hybrid (recommended for production)

Webhooks for real-time notification + delta query every 5-10 minutes as a safety net for missed notifications. The delta query catches anything the webhook missed.

### Python Libraries for M365

| Library | Protocol | Daemon? | Webhooks? | Notes |
|---------|----------|---------|-----------|-------|
| `imap_tools` + `msal` | IMAP | Yes | No | Cleanest IMAP API, `.xoauth2()` method |
| `imaplib` + `msal` | IMAP | Yes | No | stdlib, lower level |
| `python-o365` v2.1 | Graph | Yes | No | Pythonic wrapper, auto token refresh, shared mailbox support |
| `msgraph-sdk-python` | Graph | Yes | Yes | Official Microsoft SDK, async, full feature set |
| `exchangelib` | EWS | Yes | No | **Avoid** — EWS shuts down Oct 1, 2026 |

### Rate Limits

- **Graph**: 10,000 requests / 10 min per app per mailbox; 4 concurrent requests
- **IMAP**: ~8 concurrent connections per mailbox (undocumented but observed)
- **Graph webhook delivery** is NOT counted against API throttling limits
- 429 responses include `Retry-After` header; the official SDK handles retry automatically

### Shared Mailboxes

Work with both approaches. No license needed for Graph API with application permissions. For IMAP, grant `FullAccess` via `Add-MailboxPermission` and use the shared mailbox email in the XOAUTH2 auth string.

---

## Specific Scenario: Identifier Extraction from a Shared Mailbox

A concrete use case that shaped this research: one shared M365 mailbox receives emails from many people (including customers). Some of those emails contain an identifier — something like `1234-2026` (up to 4 digits, dash, year). The system needs to detect the identifier, match it against a database, and trigger processing. Emails without an identifier are ignored.

### The challenges

**Freeform email from non-technical senders.** Customers don't follow schemas. The identifier might appear as:
- `1234-2026` in the subject line
- "Reference: 1234-2026" buried in the body
- `#1234/2026` with a slash instead of a dash
- Inside a forwarded message or quoted reply
- In an attachment filename

**False positives.** Phone numbers, dates, postal codes, and order numbers can match simple numeric patterns. The regex needs to be specific enough to minimize noise but flexible enough to handle real-world formatting.

**Duplicate processing.** Reply chains create multiple emails referencing the same identifier. Need idempotency — track which (message ID, identifier) pairs have been processed.

### Architecture for this scenario

```
Shared Mailbox ← [Poller] → Scan for pattern → DB lookup → Process / Flag for review
                                  ↓ (no match)
                              Skip silently
```

The pattern: `\d{1,4}[-/]20\d{2}` — flexible enough to catch `1234-2026` and `1234/2026`, anchored to word boundaries to reduce false positives.

**Scan in priority order:**
1. Subject line (highest confidence — if someone puts the ID in the subject, that's intentional)
2. Plain text body (good confidence)
3. HTML body stripped of tags (lower confidence — might be in email boilerplate)
4. Attachment filenames (lowest confidence)

If the same identifier appears in multiple locations, take the highest-confidence match. If multiple *different* identifiers appear, take the most prominent one and log the others.

**Database lookup result:**
- Found → ingest the email, link to the record, trigger workflow
- Not found → flag for manual review (could be a typo, could be a new record)
- No identifier at all → skip silently

See `example_identifier_scanner.py` for a working implementation of this pipeline, wired to the IMAP poller.

### Edge cases to plan for

| Situation | Suggested handling |
|-----------|-------------------|
| Multiple different identifiers in one email | Process the highest-confidence one, log the rest |
| Identifier exists but not in database | Flag for human review |
| Reply chain repeating the same identifier | Idempotency check on (message-id, identifier) |
| Identifier in a forwarded message (not the sender's intent) | Strip quoted/forwarded content before scanning body (use `talon` or `mail-parser-reply`) |
| Near-miss pattern (e.g. `12345-2026`, 5 digits) | Log near-misses for review if you want to catch typos |
| Same email processed twice (poller restart) | Mark as read after processing; track processed message IDs |

---

## Shared Mailbox Concurrency: Bot + Staff Coexistence

This is the make-or-break design question. The shared mailbox isn't a passive drop zone — staff officers are actively reading, moving, tagging, and deleting emails in it. A naive poller will miss messages.

### Why `SEARCH UNSEEN` is broken

Exchange Online shared mailboxes have a **single global read state**. The `\Seen` flag is shared across all users and sessions. There is no per-user read state.

```
Staff reads email at 10:00:01  →  email marked \Seen
Poller runs SEARCH UNSEEN at 10:00:30  →  email NOT returned
→ Permanently missed
```

Any architecture relying on the `\Seen` flag for message discovery has a race condition with human users. This is the single most common mistake in shared mailbox automation.

### Why IMAP is the wrong protocol here

Beyond the `\Seen` problem:
- Exchange Online does **not** support custom IMAP keyword flags (no `\*` in `PERMANENTFLAGS`)
- IMAP UIDs **change when messages are moved between folders** — staff moving an email from Inbox to a subfolder invalidates your tracking
- Exchange categories (color tags) are **not accessible via IMAP**
- Staff can delete an email before the poller sees it, with no IMAP mechanism to detect "was in Inbox, now gone"

### Graph API solves these problems

| Feature | How it helps |
|---------|-------------|
| `immutableId` | Survives folder moves within the same mailbox. Opt-in via `Prefer: IdType="ImmutableId"` |
| Delta queries | Returns new, updated, AND removed/moved messages. Detects everything. |
| Categories | Programmatic "Bot-Processed" marker, visible to staff in Outlook |
| Extended properties | Invisible custom data stamped on messages (more robust than categories) |
| Change notifications | Near-real-time push instead of polling — eliminates the scan window entirely |

### Recommended: Transport Rule + Dedicated Processing Mailbox

The strongest pattern. Complete isolation between bot and staff.

```
                    ┌─────────────────────┐
  Inbound Email ───>│  Exchange Transport │
                    └────────┬────────────┘
                             │
                    ┌────────┴────────┐
                    │  Mail Flow Rule  │
                    │  (BCC action)    │
                    └───┬─────────┬───┘
                        │         │
                        v         v
              ┌─────────────┐  ┌──────────────────┐
              │   Shared    │  │   Processing     │
              │   Mailbox   │  │   Mailbox        │
              │ (staff use) │  │ (bot-only)       │
              └─────────────┘  └────────┬─────────┘
                                        │
                                        v
                               ┌────────────────┐
                               │  Poller/Bot    │
                               │  (Graph API)   │
                               └────────────────┘
```

**Setup:**
```powershell
New-TransportRule -Name "Copy to Processing Mailbox" `
  -RecipientAddressContainsWords "shared-mailbox@domain.com" `
  -BlindCopyTo "processing-mailbox@domain.com" `
  -Priority 0
```

The bot monitors its own mailbox exclusively. Staff workflow is completely unaffected. No race conditions. Bot can freely mark messages as read, move them, delete them in its own space.

**Limitation:** Transport rules only catch mail processed through Exchange transport — not messages dragged into the shared mailbox from another folder, or created directly via Graph API.

### Fallback: Graph API Observer on Shared Mailbox

When the transport rule isn't sufficient (messages arriving by means other than Exchange transport), monitor the shared mailbox directly:

1. Subscribe to Graph change notifications for `created` events on Inbox
2. On notification: fetch message using `immutableId`, check if already processed
3. If identifier found: ingest, stamp with "Bot-Processed" category
4. Periodic delta query catch-up (every 5-10 minutes) for missed notifications
5. Track all processed `immutableId` values in an external database

**Observer-only rules — the bot must:**
- NEVER modify `isRead` state
- ONLY add categories (never remove existing ones)
- Tolerate messages being moved or deleted by staff at any time
- Use `$select` to fetch only needed properties

### Safety net: Litigation Hold

Applying Litigation Hold to the shared mailbox ensures nothing is permanently lost, even if staff delete before the bot processes. Requires Exchange Online Plan 2. The bot can scan Recoverable Items as a last resort.

---

## Separating Reply Content from Quoted Thread

When ingesting emails, you want the new content the person wrote — not the entire quoted conversation thread below it. This matters for storage efficiency, front-end display, and avoiding false identifier matches in quoted content.

### The problem: no standard exists

Every email client formats quoted replies differently, and there is no RFC governing it:

| Client | HTML marker | Plain text marker |
|--------|------------|-------------------|
| Gmail | `<div class="gmail_quote">` | `On [date], [person] wrote:` |
| Outlook | `<div id="divRplyFwdMsg">` (inconsistent across versions) | `-----Original Message-----` |
| Apple Mail | `<blockquote type="cite">` | `Begin forwarded message:` |
| Thunderbird | `<blockquote type="cite">`, `<div class="moz-cite-prefix">` | `>` prefixes |

Outlook is the worst offender — different versions (Desktop 2016/2019/2021/365, OWA, Mobile) produce different HTML with no universal marker.

### Best discovery: Microsoft Graph `uniqueBody`

If you're on M365, Exchange itself can solve this. The `uniqueBody` property returns just the new part of a message, computed server-side:

```
GET /users/{id}/messages/{id}?$select=uniqueBody,body
Prefer: outlook.body-content-type="text"
```

**When it works, it's the cleanest solution** — Exchange has full thread context. But it has known reliability issues:
- Sometimes returns `null` (documented SDK bugs)
- Sometimes returns the full conversation instead of just the unique part
- Must be explicitly `$select`ed (not returned by default)
- Not efficient in list/batch operations

**Verdict:** Use as primary strategy. Always have a fallback.

### Library comparison (Python)

| Library | HTML? | Languages | Maintained? | Accuracy | Notes |
|---------|-------|-----------|-------------|----------|-------|
| `talon` / `superops-talon` | Yes | ~10 | Fork: Mar 2023 | 93.8% | Best overall. ML signature detection (SVM on Enron dataset). Heavy deps (scikit-learn, lxml). |
| `mail-parser-reply` | No | 13 | Dec 2025 | Good | Most actively maintained. Disclaimer detection. Text-only — major gap for Outlook HTML. |
| `quotequail` | Yes | Limited | Sep 2024 | ~85% | Good for forwarded message metadata. Known Outlook detection issue since 2015. |

**How talon works (HTML):** Tries provider-specific cuts in order — Gmail quote div, Zimbra, generic blockquote, Microsoft-specific patterns, ID-based cuts, "From:" blocks. Falls back to: insert checkpoints in HTML tags, convert to text, apply plain-text algorithm, remove corresponding HTML elements.

**How talon works (plain text):** Classifies each line as empty/quoted-marker/splitter/forwarded/text. Analyzes the marker sequence to find where the reply ends and the quote begins.

### Library comparison (Node.js)

| Library | HTML? | Maintained? | Notes |
|---------|-------|-------------|-------|
| `email-reply-parser` (Crisp) | No | Nov 2025 | Best maintained. ~1M emails/day at Crisp. RE2 for ReDoS safety. |
| `planer` | Yes | ~2022 | Talon port. CoffeeScript. No signature detection. |

### Recommended layered strategy

```
Layer 1: Microsoft Graph uniqueBody
    ↓ (if null, empty, or equals full body)
Layer 2: HTML-aware library (talon/superops-talon)
    ↓ (if HTML parsing fails or no HTML)
Layer 3: Plain-text heuristics (mail-parser-reply)
    ↓ (if all else fails)
Layer 4: Store full body, flag as "unparsed"
```

Compare `uniqueBody` to `body` — if they're identical, `uniqueBody` failed and you should fall through.

### What cannot be reliably solved

- **Inline/interleaved replies** (responses interspersed between quoted lines) — no library handles this. ~94% is the accuracy ceiling.
- **All Outlook versions** — too many HTML variations for a single detection strategy.
- **Signature removal without false positives** — signatures blend with content. Even talon's ML only gets 25-30% accuracy on complex signatures.
- **100% accuracy** — budget for a 5-10% error rate. Consider flagging low-confidence parses for human review.

### Multilingual considerations

The "On [date], [person] wrote:" pattern varies by language. Libraries with <5 language patterns will fail on non-English emails. `mail-parser-reply` supports 13 languages (the widest coverage). `talon` covers ~10.

---

## Content Parsing (General)

Beyond reply/quote separation, the full parsing pipeline:

```
Raw email → MIME parse → Extract body → Strip quotes/signatures → Sanitize → Convert
```

### Python Libraries

| Stage | Library | Notes |
|-------|---------|-------|
| MIME parsing | `mail-parser`, `flanker` | Or `imap_tools` gives you parsed messages directly |
| Quote/signature stripping | `talon` (Mailgun, ML-based) | SVM trained on Enron dataset, best accuracy |
| Quote/signature stripping | `mail-parser-reply` | Multilingual, regex-based, actively maintained |
| HTML to Markdown | `markdownify`, `html2text` | |
| HTML sanitization | `nh3`, `bleach` | Allowlist-based, prevent XSS |

---

## Authentication: Who Sent This Email?

If your system takes action based on inbound email, you need to verify the sender is authorized.

**Per-user secret addresses** (e.g. `action-j8k2m9x4@app.example.com`) are the dominant pattern — used by WordPress, Tumblr, Blogger. Security depends on keeping the address secret. Must be system-generated random tokens (Blogger's user-chosen "secret words" were brute-forced in 2010). Support rotation.

**DKIM/SPF/DMARC**: Good supplementary layer. All major inbound services expose verification results. But SPF/DKIM alone don't protect the visible From: header — DMARC alignment is needed, and many domains use `p=none`.

**From-address allowlist alone**: Insecure. From: is trivially spoofed.

For M365 IMAP/Graph, you're reading from a known mailbox, so the authentication question is really about the application's access to the mailbox (OAuth2 + RBAC scoping) rather than sender verification — unless your workflow logic depends on who the sender is.

---

## Security Checklist

- **HTML sanitization**: Email HTML can contain XSS. Use allowlist-based sanitizer (`nh3`, `DOMPurify`) before storing or rendering.
- **Attachment safety**: Allowlist file types, validate magic bytes, re-encode images, consider ClamAV.
- **Header injection**: Strip newlines from any email content used in headers or new emails.
- **Rate limiting**: Per-address and per-sender.
- **RBAC scoping**: Don't leave Graph `Mail.Read` unscoped to all tenant mailboxes.
- **Secret rotation**: If using secret addresses, build rotation in from the start.
- **Privacy**: Extract what you need, discard raw email. Encrypt at rest if storing.

---

## Deprecation Timeline

| What | When | Impact |
|------|------|--------|
| EWS (Exchange Web Services) | Off **October 1, 2026** | Don't use `exchangelib` for new projects |
| SMTP AUTH basic auth | Off **April 30, 2026** | OAuth2 SMTP continues |
| IMAP/POP basic auth | Already dead | OAuth2 works but IMAP is "legacy protocol" |
| Application Access Policies | Replaced by RBAC for Applications | Migrate existing policies |

---

## Decision Guide

**IMAP polling on M365** — choose this when:
- You want the conceptually simplest approach (poll a mailbox, process new messages)
- You control the tenant and can confirm Conditional Access doesn't block IMAP
- You don't need sub-minute latency
- You're comfortable with connection management (reconnect on drop, token refresh)

**Graph delta query polling** — choose this when:
- You don't have a public HTTPS endpoint
- You don't control the tenant's Conditional Access policies
- You want efficient incremental sync without connection management
- You're OK with polling-interval latency

**Graph webhooks** — choose this when:
- You need near-real-time reaction (<1 min)
- You have a public HTTPS endpoint (or can use Azure Event Hubs)
- You're building for production reliability (pair with delta queries as safety net)

**Managed webhook service (Mailgun et al.)** — choose this when:
- You own the receiving domain and can set MX records
- You want the email pre-parsed (especially Mailgun's signature stripping)
- The M365 mailbox isn't a requirement

---

## Files in This Report

| File | Description |
|------|-------------|
| `example_imap_poller.py` | Resilient M365 IMAP poller with OAuth2 client credentials, reconnection handling |
| `example_graph_poller.py` | Graph API delta query poller with state persistence, plus webhook subscription management |
| `example_identifier_scanner.py` | Identifier extraction pipeline: regex scanning, confidence ranking, database matching stub |
| `example_graph_webhook_handler.py` | Flask webhook receiver for Graph change notifications, including lifecycle events |
| `setup_exchange_online.ps1` | PowerShell script for Exchange Online service principal registration and mailbox permission setup |
| `notes.md` | Raw research notes |
