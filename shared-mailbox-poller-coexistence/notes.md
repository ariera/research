# Research Notes: Shared Mailbox Poller Coexistence with Human Users

## Research Log

### 2026-04-11 - Initial Research Phase

#### Topic 1: UNSEEN/Read Flag Problem

**Key finding:** Exchange Online shared mailboxes use a GLOBAL read state. The `\Seen` flag is shared across all users and all sessions (IMAP, Outlook desktop, OWA, mobile). There is NO per-user read state on shared mailboxes.

- Microsoft Q&A confirms: "the read flag is connected to the mailbox, so if one user reads an email, other users will see that message was read"
- Per-user read/unread status CANNOT be set for a shared mailbox
- Alternative: Public Folders or Office 365 Groups DO maintain per-user read counts
- This means `IMAP SEARCH UNSEEN` is fundamentally broken for this use case - any staff member reading the email will cause the poller to miss it

**Implication:** Using `SEARCH UNSEEN` is a non-starter for a shared mailbox. You MUST use a different tracking mechanism.

#### Topic 2: IMAP UID Stability

**Key finding:** IMAP UIDs are folder-specific. When a message is moved to another folder, it gets a NEW UID in the destination folder. The old UID in the source folder becomes invalid.

- UIDs are assigned in strictly ascending order within a folder
- UIDs must not change during a session and should not change between sessions (within the same folder)
- UIDVALIDITY changes when UIDs have been reassigned - if the UIDVALIDITY value changes between sessions, the client must discard cached UIDs and re-sync
- Known issues with Microsoft Exchange: reports of same email getting different UID with same messageId and UIDVALIDITY, with differences in attachment sizes
- **Critical:** Moving a message between folders changes its UID. This means you cannot track messages by IMAP UID across folders.

#### Topic 3: Message-ID Header

**Key finding:** Message-ID is generally reliable but NOT sufficient alone for duplicate detection.

- Exchange duplicate detection uses BOTH Internet Message ID AND client submit time
- Message-ID alone is not enough because some applications reuse the same Message-ID
- Same combination of message-id and date header can trick Exchange into treating messages as duplicates
- Message-ID is the most portable identifier across protocols (IMAP, Graph, EWS)
- For the use case of finding emails with a specific identifier pattern, Message-ID combined with other headers (Subject, Date) would be a reasonable tracking key

#### Topic 4: Graph API immutableId

**Key findings from official Microsoft documentation:**
- immutableId does NOT change when item is moved to a different folder within the same mailbox
- immutableId DOES change if: user moves item to archive mailbox, or exports and re-imports
- Opt-in via `Prefer: IdType="ImmutableId"` header
- Supported on: message, attachment, event, eventMessage, contact, outlookTask
- Container types (mailFolder, calendar) don't support immutableId, but their regular IDs are already constant
- Works with delta queries and change notifications
- Can translate between regular IDs and immutable IDs via `translateExchangeIds` function
- **Important caveat for shared mailboxes:** One Q&A source suggests immutableId has limitations for shared mailbox scenarios (specifically mailFolder not supported), but the message resource itself should still work.

#### Topic 5: Exchange Categories via Graph API

**Key findings:**
- IMAP does NOT support Exchange categories (color tags). Outlook's IMAP implementation doesn't expose categories.
- Exchange Online PERMANENTFLAGS response does NOT include `\*`, meaning custom IMAP KEYWORD flags are NOT supported
- Graph API DOES support categories on messages via the `categories` property (string array)
- Can PATCH a message to add/update categories: `PATCH /users/{id}/messages/{id}` with body `{"categories":["Processed"]}`
- For shared mailbox master category list: requires application permission `MailboxSettings.ReadWrite` (no delegate permission available)
- Categories are visible to all users accessing the shared mailbox via Outlook/OWA
- This is a viable "processed" marker strategy when using Graph API

#### Topic 6: Extended Properties / Open Extensions via Graph API

**Key findings:**
- Open extensions (recommended): stored as MAPI named properties, flexible JSON-like data
- Extended properties (legacy): single or multi-value, direct MAPI property access
- Microsoft recommends open extensions for most scenarios
- Can filter messages by extended property value: `$filter=singleValueExtendedProperties/Any(ep: ep/id eq '...' and ep/value eq '...')`
- Caution: MAPI named properties are a finite resource per mailbox (quota can be exhausted)
- Extended properties are invisible to Outlook users (pro and con)

#### Topic 7: Graph API Delta Queries

**Key findings from official docs:**
- Delta query is PER-FOLDER. Must track each folder individually.
- Returns `@removed` entries with `"reason": "deleted"` when items are deleted or moved from folder
- Supports `changeType` filter: `created`, `updated`, `deleted`
- Supports immutable IDs via `Prefer: IdType="ImmutableId"` header
- Important note from docs: "Delta queries for messages can return change events that don't match the filter conditions specified in the initial request" including `@removed` entries and read/unread state changes
- For tracking across all folders: first use mailFolder delta to sync folder structure, then message delta per folder
- Can use `$select` to limit returned properties
- Can filter by `receivedDateTime` to narrow scope

#### Topic 8: Graph API Change Notifications (Webhooks)

**Key findings:**
- Maximum 1000 active subscriptions per mailbox (all applications combined)
- For shared mailboxes: MUST use application permissions (not delegate)
- DO NOT use `.Shared` permissions (Mail.Read.Shared etc.) - they don't support subscriptions
- Can include resource data in notifications (encrypted)
- Can filter notifications (e.g., `$filter=isRead eq false`)
- Lifecycle notifications available for detecting missed notifications
- Subscription expiration: must renew before expiry
- Best practice: combine webhooks with periodic delta query catch-up (every 6-24 hours)
- Can subscribe to specific folders or all messages in mailbox

#### Topic 9: Concurrent Access Limits

**IMAP Limits:**
- Exchange Online: approximately 8 concurrent IMAP connections per mailbox (based on throttling policy)
- Exchange does not publish exact throttling settings for Exchange Online
- Per-user connection default: 16 connections (Exchange Server docs)
- Basic auth permanently disabled; OAuth2 required for all IMAP connections

**Graph API Limits:**
- MailboxConcurrency: 4 concurrent requests per app per mailbox
- Rate limit: 10,000 requests per 10-minute window per app per mailbox (~17/sec theoretical, recommended 4-10/sec)
- Global limit: 130,000 requests per 10 seconds per app across all tenants
- Batch requests: max 4 concurrent to same mailbox within a batch
- HTTP 429 + Retry-After header when throttled

**IMAP + Outlook/OWA Coexistence:**
- No documented conflicts between IMAP sessions and Outlook/OWA access to same mailbox
- All protocols see the same mailbox state (shared \Seen flags, etc.)
- IMAP sessions count against the per-mailbox connection limit

#### Topic 10: Mail Flow Rules (Transport Rules)

**Key findings:**
- Can BCC all inbound messages to a separate processing mailbox
- Server-side rules: work regardless of client configuration
- Rule deployment: up to 30 minutes to propagate across Exchange Online servers
- BCC action: delivers original to shared mailbox AND copy to processing mailbox
- Conditions available: recipient, subject pattern, headers, etc.
- Can scope rules specifically (e.g., "if recipient is shared-mailbox@domain.com")
- Separate processing mailbox = complete isolation from human users
- Copy is a true separate message with its own Message-ID (though InternetMessageId may differ from original)

#### Topic 11: Journaling

**Key findings:**
- Exchange Online journaling does NOT support delivering journal reports to an Exchange Online mailbox
- Must use on-premises archiving or third-party archiving service as journal target
- Not practical for this use case (processing mailbox must be Exchange Online accessible)
- Journal rules can scope to internal, external, or all messages

#### Topic 12: Retention/Compliance Features

**Key findings:**
- Litigation Hold: preserves ALL mailbox content including deleted items, indefinitely or for specified duration
- Overrides retention policies and user actions
- Shared mailbox: retention holds can be applied without additional licenses, BUT litigation hold requires Exchange Online Plan 2 license
- Recoverable Items folder: deleted items preserved even after user empties Deleted Items
- This provides a safety net but is not a primary processing strategy

#### Topic 13: IMAP OAuth2 for Shared Mailboxes

**Key findings:**
- Service principal approach: register app in Entra ID, use client credentials flow
- Permission: IMAP.AccessAsApp
- Mailbox access: `Add-MailboxPermission -User <ServicePrincipalId> -AccessRights FullAccess`
- Application access policy can restrict which mailboxes the app can access
- Basic auth completely deprecated for IMAP
- SMTP basic auth ending April 30, 2026

### Architecture Decision Summary

**Best Architecture: Transport Rule + Dedicated Processing Mailbox + Graph API**

1. Transport rule BCC's all inbound mail to shared mailbox also to a dedicated processing mailbox
2. Poller uses Graph API (not IMAP) to monitor the processing mailbox
3. Graph change notifications (webhooks) for near-real-time detection
4. Delta queries as catch-up mechanism
5. Categories or extended properties to mark processed messages
6. Original shared mailbox completely untouched by automation

**Fallback Architecture: Graph API Direct on Shared Mailbox**

1. Graph API with immutableId to track messages
2. Delta queries to detect new/moved/deleted messages
3. Categories to mark processed messages
4. Observer-only pattern (never modify read state)
5. External database tracks processed message IDs
