# Inbound Email Reactive Systems: Research Notes

## Reframing

User clarified: the core question is **how to build a system that reacts to receiving an email**. Blog posting (email-to-post) is just one anchoring example. The real design space is broader — any application triggered by an inbound email.

Other examples beyond blog posting: issue creation, task assignment, data ingestion, approval workflows, IoT triggers, helpdesk ticketing, notification routing.

## Starting questions (from TODO.md, generalized)

- Inbound email handling: IMAP polling vs webhook-based services vs self-hosted SMTP
- Authentication: verifying the sender is authorized
- Content parsing: extracting meaningful content from email HTML
- Attachments: handling files and inline images
- Workflow: immediate action vs queued/confirmed

## Research approach

1. Map the inbound email infrastructure landscape
2. Compare webhook-based services, self-hosted options, and hybrid approaches
3. Investigate authentication and sender verification patterns
4. Explore content parsing tools and challenges
5. Study what existing email-reactive systems have done well (and badly)
6. Sketch candidate architectures at different complexity levels

---

## Findings: Inbound Email Infrastructure

### Webhook-based services (managed)

| Service | Price floor | Key strength | Payload format |
|---------|-----------|-------------|----------------|
| **Mailgun** | $35/mo | Auto-strips quotes/signatures (`stripped-text`, `stripped-html`) | multipart/form-data |
| **SendGrid** | $19.95/mo | Includes SPF/DKIM/SpamAssassin results | multipart/form-data |
| **Postmark** | $16.50/mo (Pro) | `StrippedTextReply`, `MailboxHash` for plus-addressing, clean JSON | JSON |
| **Amazon SES** | ~$0.10/1000 | Cheapest at scale; spam/virus/SPF/DKIM/DMARC verdicts | Lambda event (body stored in S3, must fetch separately) |
| **Cloudflare Email Workers** | Free | Zero cost; runs in Worker runtime | ReadableStream (parse with `postal-mime`) |

**Key differences:**
- Mailgun uniquely provides pre-parsed content with signatures and quotes already stripped — huge time-saver
- SES is cheapest but most complex (body not in the event payload — must round-trip through S3)
- Cloudflare is free but requires domain on Cloudflare and has no pre-parsed fields
- Postmark's JSON payloads are cleanest to work with

### Self-hosted approaches

- **IMAP polling** (`imap_tools` in Python): Simplest to start, no DNS changes needed. But OAuth 2.0 now required for Gmail/Microsoft. Polling = latency.
- **aiosmtpd** (Python): Lightweight async SMTP server, hook is `handle_DATA`. Good for Python codebases.
- **Haraka** (Node.js): Battle-tested (Craigslist-scale). Plugin architecture. Built-in anti-spam.
- **Postfix + pipe-to-script**: Proven MTA, complex config. Classic Unix approach.
- **MXHook**: Open-source self-hosted SMTP-to-webhook server (Apache 2.0). Docker deployment, webhook signing, dead letter queue. Like self-hosted Mailgun Routes.
- **Postal**: Full open-source mail platform (like self-hosted Mailgun).

### Hybrid: Cloudflare Email Workers

Interesting middle ground — managed infrastructure (Cloudflare DNS + Workers) but you write the processing code yourself. No per-email cost. You get the raw email stream and parse it in the Worker.

---

## Findings: Authentication & Sender Verification

Ranked by strength:

1. **PGP/S-MIME signatures** — Cryptographic proof. Nobody uses them in practice.
2. **Per-user secret email addresses** (e.g. `post-abc123@blog.example.com`) — Dominant pattern. Used by WordPress, Tumblr, Blogger. Security = address secrecy. Must be system-generated random tokens (Blogger's user-chosen "secret words" were brute-forced in 2010).
3. **DKIM/SPF/DMARC verification** — All major inbound providers expose results. Good supplementary layer but SPF/DKIM alone don't protect the visible From: header; DMARC alignment is needed, and many domains still use `p=none`.
4. **Secret token in subject/body** — Works but poor UX, leaks via forwarding.
5. **Reply-to-a-challenge** — Confirms sender controls address but adds friction + backscatter risk.
6. **From-address allowlist alone** — Fundamentally insecure. From: is trivially spoofed.

**Best practice: defense in depth.** Per-user secret address as primary, DKIM/SPF as secondary, rate limiting, content sanitization.

---

## Findings: Content Parsing

The hardest part. Email HTML is notoriously messy — every client generates different markup.

### Python stack
- MIME parsing: `mail-parser` or `flanker`
- Quote/signature stripping: `mail-parser-reply` (multilingual) or `talon` (ML-based, trained on Enron dataset — SVM for signature detection)
- HTML to clean content: `markdownify` or `html2text`

### Node.js stack
- MIME parsing: `mailparser` or `postal-mime`
- Quote/signature stripping: `email-reply-parser` (Crisp) or `planer` (talon port)
- HTML to clean content: `turndown`

### Key insight
Mailgun's `talon` library uses machine learning for signature detection — significantly more accurate than regex. If not using Mailgun's built-in stripping, `talon` is worth pulling in separately.

---

## Findings: Existing Email-Reactive Systems

### Blog/posting platforms
- **Posterous** (defunct): Gold standard. Auto-galleries, embedded media, crossposting. Subject = title, body = content, attachments = media.
- **Posthaven** ($5/mo): Continues the Posterous model sustainably.
- **WordPress/Jetpack**: Moved from POP3 polling to secret-address webhooks.
- **Tumblr**: Had it, discontinued it.
- **Ghost / Micro.blog**: Deliberately chose not to offer it.

### Universal convention
Subject = title/identifier, body = content/payload, attachments = associated files. This convention is so consistent across implementations that it's essentially a de facto standard.

---

## Security Considerations

- **HTML sanitization**: Strict tag/attribute allowlist (DOMPurify or equivalent) — email HTML can contain XSS
- **Malicious attachments**: File type allowlisting, magic byte validation, re-encode images, ClamAV for scanning
- **Header injection**: Strip newlines from any input used in headers
- **Rate limiting**: Per-address and per-sender limits
- **Address rotation**: If a secret address leaks, must be able to rotate it
- **Privacy/GDPR**: Extract needed content, discard raw email, encrypt at rest, retention policies

---

## Deep Dive: Microsoft 365 / Exchange Online

User specifically interested in IMAP polling against M365 Exchange. This turns out to be a surprisingly involved setup due to Microsoft's OAuth2 requirements.

### IMAP on M365: The Setup Nobody Warns You About

1. Register app in Entra ID (formerly Azure AD)
2. Add `IMAP.AccessAsApp` permission (NOT `IMAP.AccessAsUser.All` — that's delegated)
3. Grant admin consent
4. **The step most people miss**: Register service principal in Exchange Online via PowerShell (`New-ServicePrincipal`) AND grant per-mailbox access (`Add-MailboxPermission`)
5. Use Enterprise Applications Object ID (NOT App Registrations Object ID — they're different values)
6. Token scope: `https://outlook.office365.com/.default`
7. Auth method: SASL XOAUTH2

### The #1 Gotcha: Conditional Access

Many M365 tenants have "Block Legacy Authentication" Conditional Access policies. These can block IMAP **even with OAuth2** because the policy targets "Other clients" without distinguishing auth method. This is the most common reason IMAP OAuth2 fails in practice. Graph API is unaffected.

### Graph API: The Better Alternative for M365

Microsoft's recommended path. Key advantages:
- **Webhooks**: Near-real-time push (avg <1 min, max 3 min latency). Max 7 day subscription lifetime, must renew.
- **Delta queries**: Efficient polling — only returns changes since last check. Save the deltaLink between polls.
- **Not blocked by Conditional Access** legacy auth policies
- **RBAC for Applications**: Scope access to specific mailboxes (replaces old Application Access Policies). Uses management scopes with recipient filters.
- Three delivery channels: webhooks, Azure Event Hubs (no public endpoint needed), Event Grid

### Deprecation Timeline (Important)
- EWS: **Off October 1, 2026** — don't use exchangelib for new projects
- SMTP AUTH basic auth: **April 30, 2026** — OAuth2 SMTP continues
- IMAP basic auth: Already dead. OAuth2 IMAP works but Microsoft considers it "legacy protocol"

### Python Library Options for M365
| Library | Protocol | Daemon support | Webhooks | Verdict |
|---------|----------|---------------|----------|---------|
| `imaplib` + `msal` | IMAP | Yes | No | Low-level, full control |
| `imap_tools` + `msal` | IMAP | Yes (`.xoauth2()`) | No | Cleanest IMAP API |
| `python-o365` v2.1 | Graph | Yes | No | Pythonic, auto token refresh |
| `msgraph-sdk-python` | Graph | Yes | Yes | Official, async, full features |
| `exchangelib` | EWS | Yes | No | **Avoid** — EWS dying Oct 2026 |

### Rate Limits
- Graph: 10,000 requests/10 min per app per mailbox, 4 concurrent
- IMAP: ~8 concurrent connections per mailbox (undocumented, observed)
- Shared mailboxes: Work with both IMAP and Graph. No license needed for Graph with app permissions.

### Practical Decision
If you control the tenant and can confirm IMAP isn't blocked by Conditional Access, IMAP polling with `imap_tools` + `msal` is the simplest path.

If you don't control the tenant, or want the most robust approach, use Graph delta queries (no public endpoint needed) or Graph webhooks (needs HTTPS endpoint).

---

## Specific Use Case: Identifier Extraction from Shared Mailbox

### The scenario
- One shared M365 mailbox, many senders (including customers)
- No schema or structure — people write freeform emails
- Need to detect an identifier matching a pattern like `\b\d{1,4}-\d{4}\b` (e.g. "1234-2026")
- Identifier could be in subject, body, or anywhere really
- If found: match against database record, trigger processing
- If not found: ignore (or flag for manual review)

### Design considerations

**Identifier extraction challenges:**
- Pattern could appear in email signatures, quoted replies, headers, footers
- False positives: phone numbers, dates, order numbers that happen to match
- Customers may format inconsistently: "1234-2026", "#1234-2026", "ref: 1234-2026", "RE: 1234/2026"
- The identifier might be in an HTML link, an image alt text, or a forwarded message

**Approach: scan everything, rank by location**
1. Check subject line first (highest confidence if found there)
2. Check plain text body (strip quotes/signatures first to avoid matching forwarded content)
3. Check HTML body as fallback (after stripping tags)
4. Optionally check attachment filenames

**Multiple matches?**
If the same email contains multiple identifiers (e.g. "RE: 1234-2026" in subject plus "see also 5678-2025" in body), need a strategy:
- Take the first/most prominent one?
- Process all of them?
- Flag for human review?

**Resilience:**
- What if the regex matches but the identifier doesn't exist in the database? → Log + flag for review
- What if the same email is processed twice? → Idempotency key (message ID + identifier)
- What about replies/forwards creating duplicate processing? → Track message threading (In-Reply-To, References headers) or track which message IDs have been processed

---

## Shared Mailbox Concurrency: Staff + Bot Coexistence

### The problem
The shared mailbox isn't a passive inbox — staff officers actively use it. They read, move, tag, delete, and organize emails. A bot polling every 30-60s must coexist without interfering.

### Key finding: `SEARCH UNSEEN` is fatally broken
Exchange Online shared mailboxes have a **single global read state**. The `\Seen` flag is shared across ALL users and sessions (IMAP, Outlook, OWA, mobile). There is NO per-user read state.

- Staff reads email at 10:00:01 → email marked `\Seen`
- Poller runs `SEARCH UNSEEN` at 10:00:30 → email NOT returned
- **Permanently missed**

This alone makes naive IMAP polling unreliable for shared mailboxes with active human users.

### IMAP is the wrong protocol for this use case
- Exchange Online does NOT support custom IMAP keyword flags (`PERMANENTFLAGS` lacks `\*`)
- IMAP UIDs **change when messages are moved between folders**
- Exchange categories are NOT accessible via IMAP
- ~8 concurrent connections per mailbox (undocumented limit)

### Graph API solves the concurrency problems
- `immutableId` survives folder moves within same mailbox (opt-in via `Prefer: IdType="ImmutableId"`)
- Delta queries detect new, updated, and deleted/moved messages
- Categories can be set programmatically as "processed" markers (visible to staff in Outlook)
- Extended properties/open extensions can store invisible custom data on messages
- No connection stability issues (stateless HTTP)

### Two architectural patterns

**Pattern A: Transport Rule + Dedicated Processing Mailbox (strongest)**
- Mail flow rule BCC's all inbound to a separate bot-only mailbox
- Complete isolation — bot never touches the shared mailbox
- No race conditions. Bot can freely mark as read, delete, etc. in its own mailbox
- Limitation: only catches mail processed through Exchange transport (not drag-and-drop moves between mailboxes)

**Pattern B: Graph API Observer on Shared Mailbox**
- Bot monitors shared mailbox directly via Graph change notifications + delta queries
- Observer-only: NEVER modifies read state, only adds categories
- Tracks processed messages by `immutableId` in external database
- Tolerates moves/deletes by staff
- More complex but catches all messages regardless of how they arrive

### Safety net: Litigation Hold
Preserves all content including deleted items. Even if staff deletes before the poller processes, email is recoverable from Recoverable Items. Requires Exchange Online Plan 2.

---

## Reply/Quote Parsing: Separating New Content from Quoted Thread

### Why this matters
When ingesting emails, we need to store just what the person actually wrote — not the entire quoted conversation thread below it. This affects:
- Database storage efficiency
- Front-end UX (displaying only the new content)
- Identifier scanning (avoiding false matches in quoted content)

### The core problem: no standard exists
Every email client formats quoted replies differently:
- Gmail: `<div class="gmail_quote">`
- Outlook: `<div id="divRplyFwdMsg">` (inconsistent across versions!)
- Apple Mail: `<blockquote type="cite">`
- Plain text: `>` prefix, "On [date] wrote:" headers
- No universal marker

### Best discovery: Microsoft Graph `uniqueBody`
The `uniqueBody` property on the message resource returns just the unique part of the message — computed server-side by Exchange.

```
GET /users/{id}/messages/{id}?$select=uniqueBody
Prefer: outlook.body-content-type="text"
```

**When it works, it's the cleanest solution.** Exchange has full context about the thread and Outlook's own formatting. But it has known reliability issues:
- Sometimes returns null (SDK bugs)
- Sometimes returns the full conversation instead of just new content
- Incomplete Base64 image data
- Must be explicitly `$select`ed (not returned by default)

**Verdict:** Use as primary strategy, but always have a library-based fallback.

### Library landscape (Python)

| Library | HTML? | Languages | Maintained? | Accuracy | Notes |
|---------|-------|-----------|-------------|----------|-------|
| `talon` / `superops-talon` | Yes | ~10 | Fork: Mar 2023 | 93.8% | Best overall. ML signature detection. Heavy deps. |
| `mail-parser-reply` | No | 13 | Dec 2025 | Good | Most maintained. Disclaimer detection. Text-only. |
| `quotequail` | Yes | Limited | Sep 2024 | ~85% | Good for forwarded message metadata. Weak on Outlook. |
| `email-reply-parser` (Zapier) | No | English only | No | Good (en) | Simple reference implementation. |

### Recommended layered approach for M365

1. **Primary**: Graph `uniqueBody` — free, server-computed, no dependencies
2. **Fallback**: HTML-aware library (talon/superops-talon) — catches provider-specific HTML markers
3. **Further fallback**: Plain-text heuristic (mail-parser-reply) — widest language support
4. **Last resort**: Store full body flagged as "unparsed" for manual review

### What cannot be solved
- **Inline/interleaved replies**: No library handles them reliably. ~94% is the accuracy ceiling.
- **All Outlook versions**: Too many HTML variations across Outlook Desktop, OWA, and Mobile.
- **Signature removal without false positives**: Signatures blend with content. Even ML approaches struggle.
