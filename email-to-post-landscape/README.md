# Email-to-Post Landscape Research

**Date:** 2026-04-11  
**Objective:** Investigate the current landscape of inbound email processing services and self-hosted alternatives for building an "email-to-post" feature.

---

## Table of Contents

1. [Webhook-Based Inbound Email Services](#1-webhook-based-inbound-email-services)
2. [Self-Hosted Approaches](#2-self-hosted-approaches)
3. [Existing Email-to-Post Implementations](#3-existing-email-to-post-implementations)
4. [Email Content Parsing Libraries](#4-email-content-parsing-libraries)
5. [Architecture Recommendations](#5-architecture-recommendations)

---

## 1. Webhook-Based Inbound Email Services

### Mailgun

**How it works:** Define "Routes" that match incoming emails by recipient address or custom filters (regex, catch-all). When matched, Mailgun can forward the parsed email to a webhook URL, forward to another email, or store it temporarily (3 days) for retrieval.

**Webhook payload (multipart/form-data POST):**

| Field | Description |
|-------|-------------|
| `recipient` | Envelope RCPT TO address |
| `sender` | Envelope MAIL FROM address |
| `from` | Header From (e.g., `"Bob <bob@example.com>"`) |
| `subject` | Email subject line |
| `body-plain` | Full plain text body (always present) |
| `body-html` | Array of all `text/html` MIME parts, UTF-8 encoded |
| `stripped-text` | **Text body with quoted sections and signature removed** |
| `stripped-signature` | The extracted signature block |
| `stripped-html` | HTML body with quoted sections removed |
| `message-headers` | JSON string of all MIME headers |
| `attachment-count` | Number of attachments |
| `attachment-N` | Individual attachment files (numbered from 1) |
| `content-id-map` | JSON map of Content-ID to attachment name |
| `timestamp` | Unix timestamp |
| `token` | Random 50-char string for verification |
| `signature` | HMAC-SHA256 signature for webhook authentication |

**Key advantage:** Mailgun is the only service that automatically strips quoted replies and signatures from the email body. The `stripped-text` and `stripped-html` fields are extremely valuable for email-to-post, saving significant parsing work.

**Pricing (as of 2026):**
- Free: 100 emails/day (no inbound routing)
- Foundation: $35/mo for 50,000 emails (includes inbound routing)
- Scale: $90/mo for 100,000 emails
- Flex/pay-as-you-go: $2.00 per 1,000 messages (increased from $1.00 in Dec 2025)
- Inbound emails count toward your monthly message volume

**Docs:** https://documentation.mailgun.com/docs/mailgun/user-manual/receive-forward-store/receive-http

---

### SendGrid (Twilio)

**How it works:** "Inbound Parse Webhook" — point your domain's MX record to `mx.sendgrid.net`, configure a webhook URL, and SendGrid POSTs parsed email data to your endpoint.

**Webhook payload (multipart/form-data POST, NOT JSON):**

| Field | Description |
|-------|-------------|
| `headers` | Raw email headers as a string |
| `from` | Sender from message headers |
| `to` | Recipient addresses (JSON object) |
| `subject` | Email subject line |
| `text` | Plain text body |
| `html` | HTML body |
| `sender_ip` | IP address of the sending server |
| `envelope` | JSON object with `from` and `to` from SMTP envelope |
| `attachments` | Number of attachments |
| `attachment-info` | JSON with filename, type, content-id per attachment |
| `charsets` | JSON object mapping each field to its character encoding |
| `dkim` | DKIM verification results |
| `SPF` | SPF verification results |
| `spam_report` | SpamAssassin report (if spam checking enabled) |
| `spam_score` | SpamAssassin score (if spam checking enabled) |
| `email` | Raw MIME message (only if "POST raw MIME" option enabled) |

**Important quirks:**
- Payload is multipart/form-data (like HTML file upload), not JSON — this differs from SendGrid's Event Webhook
- 30 MB total message size limit
- SendGrid expects a response within 20 seconds
- Retries for 3 days on 5xx errors, then drops the message
- Will not follow HTTP redirects

**Pricing (as of 2026):**
- No permanent free tier (retired May 2025); 60-day free trial only
- Essentials: $19.95/mo for 50,000 emails
- Pro: $89.95/mo for 100,000 emails
- Inbound Parse is included in all paid plans; emails count toward volume

**Docs:** https://www.twilio.com/docs/sendgrid/for-developers/parsing-email/setting-up-the-inbound-parse-webhook

---

### Postmark

**How it works:** Each Postmark server has an inbound email address (`{hash}@inbound.postmarkapp.com`). Emails sent to that address are parsed and POSTed as JSON to your configured webhook URL.

**Webhook payload (JSON POST):**

| Field | Description |
|-------|-------------|
| `From`, `FromName`, `FromFull` | Sender details with parsed name/email |
| `To`, `ToFull` | Recipients with parsed name/email |
| `Cc`, `CcFull`, `Bcc`, `BccFull` | CC/BCC recipients |
| `Subject` | Email subject |
| `MessageID` | Unique message identifier |
| `Date` | Email date |
| `TextBody` | Plain text body |
| `HtmlBody` | HTML body |
| `StrippedTextReply` | **Reply text with quoted content removed** |
| `MailboxHash` | Plus-addressing hash (e.g., `user+12345@` yields `12345`) |
| `Headers` | Array of `{Name, Value}` objects |
| `Attachments` | Array with `Name`, `Content` (base64), `ContentType`, `ContentLength` |
| `MessageStream` | Always `"inbound"` |

**Key advantages:**
- Clean JSON payload (unlike SendGrid's multipart/form-data)
- `StrippedTextReply` field for reply content extraction
- `MailboxHash` for plus-addressing (useful for routing posts to specific blogs)
- Built-in SpamAssassin integration (X-Spam-Status, X-Spam-Score headers)
- 10 retry attempts with growing intervals on webhook failure

**Pricing (as of 2026):**
- Inbound requires Pro tier: $16.50/mo for 10,000 emails
- Inbound messages count as regular emails toward monthly volume
- Overage: $1.30 per 1,000 additional emails on Pro

**Docs:** https://postmarkapp.com/developer/webhooks/inbound-webhook

---

### Amazon SES

**How it works:** Configure Receipt Rules to process inbound email. SES can store raw emails in S3, invoke Lambda functions, publish to SNS, or bounce/stop. The typical pattern is: SES -> S3 (store raw email) -> Lambda (process it).

**Lambda event structure (NOT the email body):**

```json
{
  "Records": [{
    "eventSource": "aws:ses",
    "ses": {
      "mail": {
        "timestamp": "2019-08-05T21:30:02.028Z",
        "source": "sender@example.com",
        "messageId": "EXAMPLE...",
        "destination": ["recipient@example.com"],
        "headers": [{"name": "From", "value": "..."}],
        "commonHeaders": {
          "from": ["sender@example.com"],
          "to": ["recipient@example.com"],
          "subject": "This is a test"
        }
      },
      "receipt": {
        "spamVerdict": {"status": "PASS"},
        "virusVerdict": {"status": "PASS"},
        "spfVerdict": {"status": "PASS"},
        "dkimVerdict": {"status": "PASS"},
        "dmarcVerdict": {"status": "GRAY"}
      }
    }
  }]
}
```

**Critical detail:** The Lambda event contains only headers and metadata — NOT the email body. To get the actual content, you must first store the email in S3 via a receipt rule action, then fetch and parse it from S3 in your Lambda function.

**Key advantages:**
- Built-in spam, virus, SPF, DKIM, and DMARC verdicts
- Handles emails up to 40 MB
- Pay-per-use pricing (extremely cheap at scale)
- Can chain multiple actions per receipt rule

**Pricing (as of 2026):**
- $0.10 per 1,000 incoming emails (each 256 KB chunk)
- Additional costs: S3 storage, Lambda invocations, SNS notifications
- Free tier: accounts before July 2025 get 3,000 free messages/month for 12 months; after July 2025, $200 in AWS credits
- Regional availability: inbound receiving only available in select regions

**Docs:** https://docs.aws.amazon.com/ses/latest/dg/receiving-email-concepts.html

---

### Cloudflare Email Workers

**How it works:** Route emails to Cloudflare Workers code that runs at the edge. Your Worker receives a `ForwardableEmailMessage` object with the raw email as a `ReadableStream`. You parse it yourself (typically with `postal-mime`) and can forward, reject, or reply.

**Runtime API:**

```javascript
import PostalMime from 'postal-mime';

export default {
  async email(message, env, ctx) {
    // message.from - envelope From
    // message.to - envelope To
    // message.headers - Headers object
    // message.raw - ReadableStream of raw email
    // message.rawSize - size in bytes

    const email = await PostalMime.parse(message.raw);
    console.log(email.subject, email.text, email.html);
    email.attachments.forEach(att => {
      console.log(att.filename, att.mimeType);
    });

    // Available actions:
    await message.forward("other@example.com");
    message.setReject("Not accepted");
    await message.reply(new EmailMessage(...));
  },
};
```

**Key advantages:**
- **Free.** Email Routing is free; Workers free tier gives 100,000 requests/day
- Code runs at the edge (low latency, no server to manage)
- Full programmability — you can integrate with Workers KV, D1, R2, Queues
- Access to Workers AI for content processing
- Auto-configured MX, SPF, DKIM records

**Key limitations:**
- You must parse the raw MIME email yourself (no pre-parsed payload)
- No built-in signature/quote stripping
- Requires your domain to be on Cloudflare
- The `postal-mime` library adds a dependency for parsing

**New development (Sept 2025):** Cloudflare Email Service launched in private beta, unifying Email Routing and Email Sending with native Worker bindings.

**Pricing:**
- Email Routing: Free
- Workers: Free tier (100k req/day), then $5/mo + $0.50 per million requests
- Storage (KV, D1, R2) has its own pricing if you need to store emails

**Docs:** https://developers.cloudflare.com/email-routing/email-workers/

---

### Service Comparison Summary

| Feature | Mailgun | SendGrid | Postmark | Amazon SES | Cloudflare |
|---------|---------|----------|----------|------------|------------|
| **Payload format** | multipart/form-data | multipart/form-data | JSON | Raw MIME in S3 | ReadableStream |
| **Auto-strips quotes** | Yes | No | Yes (text only) | No | No |
| **Auto-strips signature** | Yes | No | No | No | No |
| **Spam checking** | Via routes | SpamAssassin opt-in | SpamAssassin built-in | Spam/virus verdicts | No |
| **DKIM/SPF in payload** | No | Yes | Via headers | Yes (verdicts) | Via headers |
| **Max message size** | 25 MB | 30 MB | 25 MB | 40 MB | ~25 MB |
| **Cheapest option** | $35/mo | $19.95/mo | $16.50/mo | ~$0.10/1000 | **Free** |
| **Retry on failure** | Yes | 3 days on 5xx | 10 retries | N/A (Lambda) | N/A (Worker) |
| **Setup complexity** | Low | Low | Low | Medium-High | Medium |

---

## 2. Self-Hosted Approaches

### IMAP Polling

**How it works:** Connect to an existing email account via IMAP, periodically check for new messages, download and parse them.

**Python libraries:**

- **`imap_tools`** (recommended): High-level library wrapping imaplib. Supports IDLE for real-time push, search queries, flag/move/delete operations. Zero dependencies.
  ```python
  from imap_tools import MailBox, AND
  with MailBox('imap.gmail.com').login('user@gmail.com', 'app_password') as mailbox:
      for msg in mailbox.fetch(AND(seen=False)):
          print(msg.subject, msg.from_, msg.text, msg.html)
          for att in msg.attachments:
              print(att.filename, att.content_type, len(att.payload))
  ```
  - IDLE support: `mailbox.idle.wait(timeout=60)` for push notifications
  - GitHub: https://github.com/ikvk/imap_tools

- **`imaplib`** (stdlib): Low-level, requires manual MIME parsing. Useful when you need full control.

- **`aioimaplib`**: Async IMAP client for asyncio-based applications.

**Pros:**
- Works with any email provider (Gmail, Outlook, self-hosted)
- No domain configuration needed (no MX records to change)
- Simple to understand and debug

**Cons:**
- Polling introduces latency (typically 1-5 minute intervals)
- OAuth 2.0 now required for Gmail (March 2025) and Microsoft (2026) — no more basic auth
- Must manage IMAP connection lifecycle, reconnection, token refresh
- IDLE can be unreliable across providers
- Doesn't scale well for high volume

---

### Custom SMTP Server with aiosmtpd (Python)

**How it works:** Run your own SMTP server that receives emails directly. Uses Python's asyncio for non-blocking I/O.

```python
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP
import email

class EmailHandler:
    async def handle_DATA(self, server, session, envelope):
        mail_from = envelope.mail_from
        rcpt_tos = envelope.rcpt_tos
        msg = email.message_from_bytes(envelope.content)

        subject = msg['subject']
        # Extract body, attachments, etc.
        # Create blog post...

        return '250 Message accepted for delivery'

controller = Controller(EmailHandler(), hostname='0.0.0.0', port=25)
controller.start()
```

**Key details:**
- Part of aio-libs ecosystem, actively maintained
- Supports STARTTLS, AUTH, and other SMTP extensions
- Handler classes define behavior via `handle_RCPT`, `handle_DATA`, etc.
- Runs in a subthread via Controller, or directly via SMTP class
- GitHub: https://github.com/aio-libs/aiosmtpd

**Pros:**
- Full control over email processing pipeline
- Real-time processing (no polling delay)
- Python-native (easy integration with Django, Flask, etc.)
- Lightweight

**Cons:**
- Must manage TLS certificates
- Port 25 is blocked by most cloud providers (need port 587 or alternative)
- Must implement your own spam filtering
- Requires proper DNS (MX records) and firewall configuration
- Not battle-tested at high scale

---

### Haraka (Node.js SMTP Server)

**How it works:** Plugin-based SMTP server written in Node.js. Almost all functionality is implemented as plugins, making it highly extensible.

**Key features:**
- Handles thousands of simultaneous SMTP connections (used by Craigslist, Bounce.io)
- Built-in plugins for SpamAssassin, DNS blocklists, DKIM, SPF, greylisting
- Plugin hooks into every stage of SMTP conversation
- Can act as inbound server, outbound relay, or filtering MTA

**Custom plugin example:**
```javascript
exports.hook_data_post = function(next, connection) {
    const txn = connection.transaction;
    const body = txn.body;
    const subject = txn.header.get('Subject');
    const from = txn.header.get('From');
    // Process email, create blog post...
    next();
};
```

**Pros:**
- Battle-tested at scale
- Rich plugin ecosystem
- Good anti-spam tooling out of the box
- Active community

**Cons:**
- Node.js only
- More complex setup than aiosmtpd
- Still requires port 25 access and DNS configuration

**GitHub:** https://github.com/haraka/Haraka

---

### Postfix + Pipe-to-Script

**How it works:** Use Postfix (widely-deployed MTA) to receive email and pipe it to a custom script via transport configuration.

**Configuration approach:**

1. In `/etc/postfix/master.cf`, add a transport:
   ```
   email-to-post unix - n n - - pipe
     flags=DRhu user=www-data:www-data
     argv=/path/to/process_email.py
   ```

2. In `/etc/postfix/main.cf`, route specific addresses:
   ```
   transport_maps = hash:/etc/postfix/transport
   ```

3. In `/etc/postfix/transport`:
   ```
   post@yourdomain.com  email-to-post:
   ```

**Alternative: Procmail recipes:**
```
:0
* ^To:.*post@yourdomain\.com
| /path/to/process_email.py
```

**Pros:**
- Leverages proven, high-performance MTA
- Postfix handles TLS, authentication, queue management, retries
- Extensive documentation and community knowledge
- Works with any programming language for the script

**Cons:**
- Complex configuration (Postfix has hundreds of settings)
- The piped script user must not be postfix or root
- Debugging mail flow can be challenging
- Procmail is unmaintained (last release 2001) — consider Sieve instead

---

### MXHook (Open-Source Inbound Email Webhook)

**How it works:** Self-hosted SMTP server that receives email, parses it into structured JSON, and delivers it to your application via webhooks. Essentially a self-hosted alternative to Mailgun Routes / SendGrid Inbound Parse.

**Key features:**
- Structured JSON webhook payloads
- Built-in webhook signing for security
- Dead letter queue with replay capability
- Prometheus metrics for monitoring
- Attachment parsing with metadata
- Docker Compose deployment
- Apache 2.0 license

**Pros:**
- Simplest self-hosted path to webhook-based inbound email
- No vendor lock-in, no per-message fees
- Data stays on your infrastructure

**Cons:**
- Newer project, less battle-tested
- Still requires port 25 access and MX records
- Strictly inbound (need separate service for sending)

**Website:** https://mxhook.dev

---

### Postal (Full Self-Hosted Mail Platform)

**How it works:** Complete open-source mail delivery platform comparable to Mailgun/SendGrid/Postmark. Handles both inbound and outbound email with a web UI and REST API.

**Key features:**
- RESTful API for programmatic access
- Webhooks for delivery notifications
- Mail forwarding to HTTP endpoints
- SpamAssassin, rspamd, and ClamAV integration
- Multi-domain and multi-tenant support
- Click and open tracking
- IP pool management

**Pros:**
- Full replacement for commercial services
- Both inbound and outbound in one platform
- Good admin UI

**Cons:**
- Significant infrastructure requirements (Ruby, MySQL/MariaDB, RabbitMQ)
- More operational complexity
- Designed for organizations, may be overkill for a single blog feature

**GitHub:** https://github.com/postalserver/postal  
**Docs:** https://docs.postalserver.io

---

### Other Notable Self-Hosted Tools

- **smtp2http** (Go): Minimal binary that receives SMTP and forwards to an HTTP endpoint. No parsing, just raw forwarding. Good for simple use cases. https://github.com/alash3al/smtp2http
- **mox** (Go): Modern, full-featured, secure mail server designed for low-maintenance self-hosted email. https://github.com/mjl-/mox

---

## 3. Existing Email-to-Post Implementations

### Posterous (defunct, 2008-2013) — The Gold Standard

Posterous was the canonical email-to-blog platform. Understanding its approach is essential.

**How it worked:**
- Send email to `post@posterous.com` from your registered address
- Posterous identifies the blog by the sender's email address
- Subject line becomes the post title
- Email body becomes the post content
- Attachments handled automatically:
  - Multiple images -> photo gallery with slideshow
  - Audio files -> embedded player
  - Video files -> embedded player
  - Documents -> embedded viewer

**Advanced features:**
- `private@posterous.com` -> private post
- `draft@posterous.com` -> saved as draft
- `blog+facebook@posterous.com` -> crosspost to specific platforms
- AutoPost: automatically syndicate to Twitter, Facebook, Flickr, YouTube, etc.
- Rich text formatting preserved from email

**Authentication:** Sender email address verification (from-address matching). Simple but vulnerable to spoofing.

**What happened:** Acquired by Twitter in 2012, shut down April 30, 2013.

**Lesson:** Posterous proved email-to-post has real demand. Its downfall was business model (VC-funded free service), not the feature itself.

---

### Posthaven (2013-present) — Posterous Successor

Created by Posterous co-founder Garry Tan as a sustainable successor.

**How it works:**
- Send email to `post@{subdomain}.posthaven.com`
- Subject = title, body = content
- Supports images, video, audio, documents as attachments
- Upload limits determined by email provider (typically 10-25 MB)
- Special addresses: `private@`, `draft@`
- AutoPost to Twitter and Facebook

**Business model:** $5/month, member-supported, explicitly not venture-backed. "Meant to last forever."

**Lesson:** Sustainable business model matters for longevity. Email-to-post users need to trust the service will persist.

---

### WordPress — Post by Email

**Evolution:**

1. **WordPress Core (wp-mail.php):** Original built-in feature using POP3 polling. Configured via Settings > Writing with a POP3 mail server. A cron job would hit `wp-mail.php` to check for new emails. **Deprecated and marked for removal** — deemed too limited and insecure for core.

2. **Jetpack Post by Email:** The recommended replacement. Uses a per-user secret email address (`{random-string}@post.wordpress.com`).
   - Email subject = post title
   - Supports images, galleries, rich formatting, shortcodes
   - Can specify categories, tags, and publish delay via shortcode-like syntax in the email body
   - Free for all Jetpack users

3. **Post By Email Plugin** (standalone): Community plugin replacing core functionality. Supports both IMAP and POP3 with or without SSL.

**Lessons:**
- WordPress moved from sender-verification (POP3 polling known accounts) to secret-address (Jetpack) — simpler and more secure
- The core implementation was too brittle and was rightly deprecated
- Jetpack processes the email server-side (on WordPress.com infrastructure), not on the user's server

---

### Ghost

Ghost does **not** have an email-to-post feature. Ghost's email functionality is about sending newsletters to subscribers (outbound), not receiving emails to create posts (inbound). Posts are created through the Ghost Editor (web UI) or the Admin API.

**Lesson:** Not every blogging platform needs email-to-post. Ghost focuses on the editor experience instead.

---

### Tumblr

**How it worked:** Each blog had a private/secret email address (found in blog settings). Emails sent to that address became posts.

**Current status:** Tumblr **discontinued** the Post by Email feature (announced in 2016).

**Lesson:** Even major platforms may drop email-to-post if usage is low or maintenance burden is high.

---

### Micro.blog

Micro.blog does **not** appear to have a direct email-to-post feature. It uses the Micropub protocol (W3C recommendation) for posting from third-party apps. Email newsletter functionality is outbound (sending posts to subscribers).

**Lesson:** The IndieWeb approach (Micropub) is an alternative to email-to-post for programmatic posting.

---

### Jekyll (via JekyllMail)

**JekyllMail plugin:** Community-built solution for email-to-post with static site generators.

**How it works:**
- Polls a POP3 email account
- Checks for a pre-defined secret in the subject line
- Converts emails to properly-named files in `_posts/` directory
- Extracts image attachments to dated directories
- Updates image tags in the document to point to correct paths

**Limitations:**
- POP3 only (no IMAP)
- Requires a separate email account per blog
- Still requires a site rebuild after receiving the email

**GitHub:** https://github.com/masukomi/JekyllMail

**Lesson:** Static site generators need a trigger mechanism to rebuild after receiving an email. This adds complexity compared to dynamic platforms.

---

### Common Patterns Across Implementations

| Pattern | Used By | Pros | Cons |
|---------|---------|------|------|
| **Secret address** | Jetpack, Tumblr, Posthaven | Simple, no spoofing risk | Address can leak; one address per blog |
| **Sender verification** | Posterous, WordPress core | Convenient (send from any client) | From-address spoofing risk |
| **Subject-line secret** | JekyllMail | Works with any email | Easy to forget; visible in email logs |
| **Plus-addressing routing** | Postmark (MailboxHash) | Route to different blogs/categories | Requires plus-addressing support |

**Universal conventions:**
- Subject line = post title (every implementation)
- Email body = post content (every implementation)
- Attachments = media (images, audio, video)
- Special keywords or shortcodes in body for metadata (categories, tags, draft status)

---

## 4. Email Content Parsing Libraries

### MIME Parsing (Step 1: Decompose the Email)

#### Python

| Library | Description | Notes |
|---------|-------------|-------|
| **`email`** (stdlib) | Built-in Python email parsing. `email.parser.BytesParser` / `email.message.EmailMessage` | Always available; low-level; full RFC 5322 support |
| **`mail-parser`** | Enhanced wrapper around stdlib. Extracts all details into a comprehensive object | Multi-format bodies (text/HTML), full attachment metadata. GitHub: SpamScope/mail-parser |
| **`flanker`** (Mailgun) | High-performance MIME parser. Up to 20x faster than stdlib, 0.47x memory usage | Also includes email address validation. GitHub: mailgun/flanker |
| **`imap_tools`** | IMAP client with built-in message parsing | Parses directly from IMAP fetch. See self-hosted section above |

#### Node.js / JavaScript

| Library | Description | Notes |
|---------|-------------|-------|
| **`mailparser`** (Nodemailer) | Streaming parser, handles 100MB+ messages. `simpleParser` for convenience | Most popular Node.js email parser. npm: mailparser |
| **`postal-mime`** | Isomorphic parser for browser, Node.js, and Cloudflare Workers. Zero dependencies, TypeScript | Recommended for Cloudflare Email Workers. npm: postal-mime |
| **`letterparser`** | Isomorphic alternative to mailparser. TypeScript, works in browser | Lighter weight than mailparser. npm: letterparser |
| **`emailjs-mime-parser`** | Low-level MIME tree parser with no magic | For when you need raw MIME structure access |

---

### Reply/Quotation Stripping (Step 2: Extract Only the New Content)

This is the hardest part of email-to-post parsing. Email clients format quoted replies differently, and there's no standard.

#### Python

| Library | Description | Notes |
|---------|-------------|-------|
| **`email-reply-parser`** (Zapier) | Extracts most recent reply, strips quoted text | Simple API: `EmailReplyParser.parse_reply(text)`. MIT license. GitHub: zapier/email-reply-parser |
| **`mail-parser-reply`** | Multi-language reply splitting (EN, DE, FR, ES, IT, JA, ZH, etc.) | Improved version of Zapier's parser with language support. GitHub: alfonsrv/mail-parser-reply |
| **`talon`** (Mailgun) | ML-based quotation and signature extraction using SVM classifiers | Most sophisticated approach. Trained on Enron dataset. Handles both plain text and HTML. GitHub: mailgun/talon |

#### Node.js / JavaScript

| Library | Description | Notes |
|---------|-------------|-------|
| **`email-reply-parser`** (Crisp) | Supports ~10 locales, uses RE2 regex engine for safety | npm: email-reply-parser |
| **`node-email-reply-parser`** | Port of GitHub's Ruby library with "aggressive" mode for Gmail line-breaking | npm: node-email-reply-parser |
| **`planer`** | JavaScript port of Mailgun's talon | npm: planer. GitHub: lever/planer |

**Recommendation:** For Python, use `mail-parser-reply` for multilingual support or `talon` for the most robust extraction. For Node.js, use `email-reply-parser` (Crisp) or `planer`.

---

### Signature Removal (Step 3: Remove Email Signatures)

| Library | Language | Description |
|---------|----------|-------------|
| **`talon`** (Mailgun) | Python | Uses ML (SVM classifier) for signature detection. Pre-trained model included. The most sophisticated approach available |
| **`node-talon`** | Node.js | Port of Mailgun's talon to JavaScript |
| **`talon-v2`** | Python | Updated fork of talon |

Note: Many reply parsers also handle signatures to some degree, but talon's ML approach is significantly more accurate than regex-based methods.

---

### HTML-to-Clean-Content Conversion (Step 4: Convert Email HTML to Blog Content)

Email HTML is notoriously dirty — inline styles, table-based layouts, Outlook conditional comments (`<!--[if mso]>`), tracking pixels, etc. Converting to clean blog content requires dedicated tools.

#### Python

| Library | Description | Notes |
|---------|-------------|-------|
| **`markdownify`** | HTML to Markdown using BeautifulSoup4. Customizable tag handling | Supports ATX, SETEXT heading styles. Can strip or convert specific tags. GitHub: matthewwithanm/python-markdownify |
| **`html2text`** | HTML to clean Markdown. Originally by Aaron Swartz | Battle-tested, clean output. Good for email HTML. PyPI: html2text |
| **`html-to-markdown`** | Newer alternative with additional options | PyPI: html-to-markdown |
| **`BeautifulSoup4`** | HTML parser for full manual control | Use when you need to pre-clean HTML before conversion (remove tracking pixels, strip inline styles, etc.) |

#### Node.js / JavaScript

| Library | Description | Notes |
|---------|-------------|-------|
| **`html-to-text`** | Converts HTML to readable plain text | Used in Cloudflare Workers examples for email processing |
| **`turndown`** | HTML to Markdown converter | Popular, well-maintained, plugin system |
| **`rehype` / `remark`** ecosystem | Unified.js pipeline for HTML/Markdown transformation | Most flexible; can build custom processing pipelines |

**Recommended pipeline for email HTML -> blog content:**

1. Parse MIME to get HTML body
2. Strip quoted replies and signatures
3. Remove email-specific cruft (tracking pixels, inline styles, table layouts)
4. Convert cleaned HTML to Markdown (or your target format)

---

### Complete Parsing Pipeline Example (Python)

```python
import email
from mail_parser_reply import EmailReplyParser
import markdownify
from bs4 import BeautifulSoup

def email_to_post(raw_email: bytes) -> dict:
    # Step 1: Parse MIME
    msg = email.message_from_bytes(raw_email)
    subject = msg['subject']
    sender = msg['from']

    # Get body parts
    text_body = None
    html_body = None
    attachments = []

    for part in msg.walk():
        content_type = part.get_content_type()
        if content_type == 'text/plain' and not text_body:
            text_body = part.get_payload(decode=True).decode()
        elif content_type == 'text/html' and not html_body:
            html_body = part.get_payload(decode=True).decode()
        elif part.get_filename():
            attachments.append({
                'filename': part.get_filename(),
                'content_type': content_type,
                'data': part.get_payload(decode=True)
            })

    # Step 2: Strip quoted replies
    parser = EmailReplyParser(languages=['en'])
    if text_body:
        parsed = parser.read(text=text_body)
        clean_text = str(parsed.replies[0]) if parsed.replies else text_body

    # Step 3: Convert HTML to Markdown (if HTML body available)
    if html_body:
        soup = BeautifulSoup(html_body, 'html.parser')
        # Remove tracking pixels
        for img in soup.find_all('img', width='1'):
            img.decompose()
        # Remove inline styles
        for tag in soup.find_all(style=True):
            del tag['style']
        clean_markdown = markdownify.markdownify(str(soup), strip=['style'])
    else:
        clean_markdown = clean_text

    return {
        'title': subject,
        'author_email': sender,
        'content': clean_markdown,
        'attachments': attachments,
    }
```

---

## 5. Architecture Recommendations

### For a New Email-to-Post Feature

#### Option A: Cloudflare Email Workers (Best for: cost-sensitive, Cloudflare users)

```
Email -> Cloudflare Email Routing -> Email Worker
  -> postal-mime (parse)
  -> planer or custom stripping (clean)
  -> POST to your blog API (or store in D1/R2)
```

**Cost:** Free for low volume  
**Complexity:** Medium  
**Latency:** Very low (edge processing)

#### Option B: Mailgun Routes (Best for: simplicity, best out-of-box parsing)

```
Email -> Mailgun (MX records) -> Route match -> Webhook POST to your server
  -> Use stripped-text/stripped-html fields directly
  -> Convert to blog post
```

**Cost:** $35/mo minimum  
**Complexity:** Low  
**Latency:** Low (near real-time webhook)

#### Option C: Amazon SES + Lambda (Best for: AWS users, high scale)

```
Email -> SES (MX records) -> Receipt Rule -> S3 (store raw) -> Lambda (process)
  -> Parse with Python email module
  -> Strip replies with mail-parser-reply
  -> Store as blog post
```

**Cost:** ~$0.10/1000 emails + S3/Lambda  
**Complexity:** Medium-High  
**Latency:** Low

#### Option D: MXHook Self-Hosted (Best for: data sovereignty, no vendor lock-in)

```
Email -> MXHook (MX records, your server) -> Webhook POST to your app
  -> Parse JSON payload
  -> Process and store as blog post
```

**Cost:** Server costs only  
**Complexity:** Medium  
**Latency:** Low

#### Option E: IMAP Polling (Best for: quick prototype, no DNS changes needed)

```
Existing email account <- imap_tools polling (cron or IDLE)
  -> Parse with mail-parser-reply
  -> Convert with markdownify
  -> Create blog post
```

**Cost:** Free (use existing email)  
**Complexity:** Low to start, higher with OAuth  
**Latency:** 1-5 minutes (polling interval)

### Authentication Strategy

For an email-to-post system, combine multiple approaches:

1. **Secret address** (primary): Generate a unique, unguessable email address per user (like Jetpack). This is the simplest and most secure approach.
2. **Sender verification** (secondary): Optionally verify the From address matches the account owner. Reduces risk if the secret address leaks.
3. **DKIM verification** (if available): Check DKIM signatures on inbound email to confirm the sending domain. SES, Postmark, and SendGrid include this in their payloads.
4. **Rate limiting**: Prevent abuse if an address is discovered.

### Content Processing Pipeline

Regardless of which inbound service you choose, the content processing pipeline should be:

1. **Receive** email (webhook or poll)
2. **Authenticate** sender (secret address + optional sender check)
3. **Parse** MIME structure (extract text, HTML, attachments)
4. **Strip** quoted replies and signatures
5. **Clean** HTML (remove tracking pixels, inline styles, table layouts)
6. **Convert** to target format (Markdown, HTML, etc.)
7. **Extract** metadata from subject/body (title, tags, categories, draft status)
8. **Process** attachments (resize images, store in CDN)
9. **Create** blog post via your CMS API

---

## Sources

### Service Documentation
- [Mailgun Inbound Routes](https://documentation.mailgun.com/docs/mailgun/user-manual/receive-forward-store/receive-http)
- [SendGrid Inbound Parse Webhook](https://www.twilio.com/docs/sendgrid/for-developers/parsing-email/setting-up-the-inbound-parse-webhook)
- [Postmark Inbound Webhook](https://postmarkapp.com/developer/webhooks/inbound-webhook)
- [Amazon SES Receiving Email](https://docs.aws.amazon.com/ses/latest/dg/receiving-email-concepts.html)
- [Amazon SES Lambda Event](https://docs.aws.amazon.com/ses/latest/dg/receiving-email-action-lambda-event.html)
- [Cloudflare Email Workers](https://developers.cloudflare.com/email-routing/email-workers/)
- [Cloudflare Email Workers Runtime API](https://developers.cloudflare.com/email-routing/email-workers/runtime-api/)

### Pricing
- [Mailgun Pricing](https://www.mailgun.com/pricing/)
- [SendGrid Pricing](https://sendgrid.com/en-us/pricing)
- [Postmark Pricing](https://postmarkapp.com/pricing)
- [Amazon SES Pricing](https://aws.amazon.com/ses/pricing/)
- [Cloudflare Workers Pricing](https://developers.cloudflare.com/workers/platform/pricing/)

### Self-Hosted Tools
- [aiosmtpd](https://github.com/aio-libs/aiosmtpd)
- [Haraka](https://github.com/haraka/Haraka)
- [MXHook](https://mxhook.dev/)
- [Postal](https://github.com/postalserver/postal)
- [smtp2http](https://github.com/alash3al/smtp2http)
- [mox](https://github.com/mjl-/mox)

### Email Parsing Libraries
- [imap_tools](https://github.com/ikvk/imap_tools)
- [mail-parser](https://github.com/SpamScope/mail-parser)
- [flanker](https://github.com/mailgun/flanker)
- [talon](https://github.com/mailgun/talon)
- [mailparser (Node.js)](https://github.com/nodemailer/mailparser)
- [postal-mime](https://github.com/postalsys/postal-mime)
- [email-reply-parser (Zapier)](https://github.com/zapier/email-reply-parser)
- [mail-parser-reply](https://github.com/alfonsrv/mail-parser-reply)
- [email-reply-parser (Crisp, Node.js)](https://github.com/crisp-oss/email-reply-parser)
- [planer (Node.js port of talon)](https://github.com/lever/planer)
- [markdownify](https://github.com/matthewwithanm/python-markdownify)
- [html2text](https://github.com/Alir3z4/html2text)

### Existing Implementations
- [Jetpack Post by Email](https://jetpack.com/support/post-by-email/)
- [WordPress Post by Email (core)](https://github.com/WordPress/WordPress/blob/master/wp-mail.php)
- [WordPress Trac #22942 - Remove Post by Email](https://core.trac.wordpress.org/ticket/22942)
- [Posthaven Post by Email](https://posthaven.com/help/post_by_email)
- [JekyllMail](https://github.com/masukomi/JekyllMail)
- [Posterous (Wikipedia)](https://en.wikipedia.org/wiki/Posterous)
- [Tumblr Post by Email Discontinuation](https://unwrapping.tumblr.com/post/147147742877/post-by-email)
- [Best Inbound Email APIs 2026 (Pingram)](https://www.pingram.io/blog/best-inbound-email-notification-apis)
