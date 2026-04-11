# Authentication, Authorization, and Security Patterns for Email-to-Post Systems

An investigation into how email-to-post systems (where sending an email to a special address publishes a blog post) can authenticate senders, prevent abuse, and handle the various security challenges inherent in accepting untrusted email input.

---

## 1. Sender Verification Approaches

### 1.1 From-Address Allowlisting

The simplest approach: maintain a list of authorized sender email addresses and only accept posts from those addresses.

**How it works**: Check the `From:` header of incoming email against an allowlist. Reject emails from unknown senders.

**Critical weakness**: From-address spoofing is trivial. The SMTP protocol does not inherently authenticate the `From:` header. An attacker who knows the target address and the allowlisted sender address can forge emails that pass this check. This approach should never be used as the sole authentication mechanism.

### 1.2 DKIM/SPF/DMARC Verification

These three protocols work together to authenticate email senders at the domain level:

- **SPF** (Sender Policy Framework): Specifies which IP addresses may send mail for a domain. Checks the envelope `Return-Path`, not the visible `From:` header.
- **DKIM** (DomainKeys Identified Mail): Cryptographically signs email content. The receiving server verifies the signature using the sender domain's public key from DNS. Validates the `d=` domain in the signature, not the visible `From:` header.
- **DMARC** (Domain-based Message Authentication, Reporting & Conformance): Bridges the gap by requiring alignment between SPF/DKIM results and the visible `From:` header. Lets domain owners publish policies (none/quarantine/reject) for messages that fail alignment.

**The alignment problem**: SPF and DKIM alone do not protect the `From:` header that users see. An attacker can set `From: you@yourdomain.com` while using their own domain for SPF/DKIM -- and both will pass. DMARC is required to catch this by enforcing that SPF or DKIM domains align with the `From:` domain.

**Practical limitation**: Many domains still publish `p=none` DMARC policies (report-only), meaning failures are logged but not enforced. You cannot rely on the sender's domain having a strict DMARC policy.

**Can webhook services verify these?** Yes -- the major inbound email providers expose verification results:

| Provider | DKIM Result | SPF Result | How Exposed |
|----------|-------------|------------|-------------|
| **Mailgun** | `X-Mailgun-Dkim-Check-Result`: Pass/Fail | `X-Mailgun-Spf`: Pass/Neutral/Fail/SoftFail | MIME headers (requires spam filtering enabled) |
| **SendGrid** | `dkim` field: JSON with per-domain pass/fail | `SPF` field: none/fail/pass | Webhook payload fields |
| **Postmark** | In `X-Spam-Tests` header: `DKIM_SIGNED`, `DKIM_VALID` | In `X-Spam-Tests` header: `SPF_PASS` | Embedded in SpamAssassin test results within Headers array |
| **AWS SES** | Verified by default, results in SNS notifications | Verified by default, results in SNS notifications | SNS notification payload; Lambda blueprint checks all three |
| **Cloudflare Email Workers** | Required for forwarding (as of July 2025) | Required for forwarding (as of July 2025) | `headers` object available but specific results not documented |

**Recommendation for email-to-post**: Check DKIM and SPF results from your inbound provider and require DMARC alignment. Use as a necessary-but-not-sufficient layer -- combine with other verification methods. A message that fails DKIM/SPF should be rejected outright, but a message that passes still needs additional verification since the sender may be anyone at the claimed domain.

### 1.3 Secret Token in Subject Line or Email Body

**How it works**: Assign each user a secret token (e.g., a random UUID). The user includes this token in the email subject or body. The system extracts and validates it before publishing.

**Advantages**:
- Simple to implement
- Works with any email client
- Token is not visible in transit to intermediaries who only see envelope headers

**Disadvantages**:
- Awkward UX -- users must remember to include the token
- Token may appear in blog post if not carefully stripped
- Token transmitted in the clear within the email body (unless the email is encrypted)
- If email is forwarded or quoted, the token leaks

**Variant**: Token in a specific header (e.g., `X-Post-Token: abc123`). More elegant but many email clients cannot set custom headers.

### 1.4 Per-User Secret Email Addresses

**How it works**: Each user is assigned a unique, unguessable email address such as `post-a7f2c9e4b1d8@blog.example.com`. Knowing this address is the credential. The system uses a catch-all or wildcard domain to receive mail, then looks up the random token in the local part to identify and authenticate the sender.

**This is the dominant pattern.** WordPress, Tumblr, Blogger, and Jetpack all used (or use) this approach:

| Platform | Format | From-Address Checked? | Regeneratable? |
|----------|--------|-----------------------|----------------|
| WordPress.com / Jetpack | `<random>@post.wordpress.com` | No | Yes |
| Tumblr (discontinued 2016) | Per-blog secret address | No | Yes |
| Blogger (Mail2Blogger) | `<username>.secretword@blogger.com` | No | Yes (after vulnerability fix) |
| Buttondown | Newsletter's configured email address | Yes (matches registered email) | N/A -- uses sender matching |

**Advantages**:
- No extra step for the user beyond addressing the email
- No token to remember or embed in content
- Address secrecy provides authentication
- Simple server-side lookup

**Disadvantages**:
- Security depends entirely on address secrecy
- If the address leaks (email client autocomplete, forwarding, screenshots, breach), anyone can publish
- Blogger's real-world vulnerability: brute-forced weak "secret words" to hijack blogs for spam
- No sender identity verification -- the "credential" is the address itself

**Best practices for this approach**:
- Use cryptographically random tokens (at least 128 bits of entropy, e.g., 22+ character base62 string)
- Offer one-click address regeneration
- Rate-limit posts per address
- Optionally combine with From-address check for defense-in-depth (even though spoofable, it raises the bar)
- Monitor for unusual posting patterns

### 1.5 PGP/S-MIME Signed Emails

**How it works**: The sender cryptographically signs the email using their PGP private key or S/MIME certificate. The receiving system verifies the signature against the sender's known public key before publishing.

**PGP**:
- Sender uses `gpg --clearsign` or their email client's PGP signing feature
- Receiving system runs `gpg --verify` against the sender's pre-registered public key
- Clearsigning is particularly suitable as it preserves the readable message body

**S/MIME**:
- Uses X.509 certificates issued by Certificate Authorities
- Email clients (Outlook, Apple Mail, Thunderbird) support S/MIME natively
- Verification uses OpenSSL libraries
- CA-backed identity verification provides stronger identity assurance than PGP's web of trust

**This is the strongest authentication mechanism available** -- it provides cryptographic proof of sender identity and message integrity. However:

- Almost nobody uses PGP or S/MIME in practice
- Key management is burdensome for non-technical users
- Mobile email clients have limited PGP/S/MIME support
- Suitable only for highly technical or security-conscious audiences

### 1.6 Reply-to-a-Challenge (Confirmation Link)

**How it works**: When an email arrives, the system does not publish immediately. Instead, it sends a confirmation email back to the sender with a unique link or code. The post is only published after the sender clicks the link or replies with the code.

**This is essentially challenge-response spam filtering** applied to publishing. Challenge-response systems were invented in 1997 and have a well-documented history.

**Advantages**:
- Confirms the sender controls the From: address (prevents spoofing)
- No pre-shared secrets needed beyond the email address
- Familiar UX pattern (similar to email confirmation during account signup)

**Disadvantages**:
- Adds delay and friction to every post
- Backscatter risk: if the From: address is forged, the challenge goes to an innocent third party (though for email-to-post this is less severe than for general anti-spam)
- Does not work for time-sensitive posts
- Interacts poorly with automated or scheduled posting workflows
- The confirmation email itself could be spoofed (unlikely but theoretically possible)

**Mitigation**: Use challenge-response selectively -- require it for the first post from a new sender, or when DKIM/SPF checks fail, but skip it for recognized senders with passing authentication.

---

## 2. What Existing Platforms Do

### WordPress.com / Jetpack Post by Email

- **Mechanism**: Per-user secret email address (`<random>@post.wordpress.com`)
- **Authentication**: Address secrecy only. No From-address verification.
- **Address format**: System-generated random string of letters and numbers
- **Regeneration**: Users can click "Regenerate address" to get a new secret address at any time
- **Features**: Email subject becomes post title, body becomes content
- **Status**: Active via Jetpack (free feature)

### Tumblr Post by Email (Discontinued)

- **Mechanism**: Per-blog secret email address
- **Authentication**: Address secrecy only. Explicitly documented as NOT checking the From: address -- "anybody who knows what the email address for a particular blog can post to that blog"
- **Regeneration**: Could deactivate and generate a new address
- **Status**: Discontinued in July 2016

### Blogger / Mail2Blogger

- **Mechanism**: `<username>.<secret-word>@blogger.com` format
- **Authentication**: Secret word (originally user-chosen)
- **Vulnerability**: In 2010, an organized attack brute-forced weak user-chosen secret words. Blogs with easily guessable passwords were hijacked and used as spam hosts. Blogger responded by disabling weak secret words and requiring stronger ones.
- **Lesson**: User-chosen secrets are vulnerable to brute-force. Always use system-generated cryptographically random tokens.

### Buttondown (Sending via Email)

- **Mechanism**: Sender email matching -- the From: address must match the newsletter's configured email address
- **Authentication**: Email address matching (no secret address pattern)
- **Inbound processing**: Uses Postmark MX records
- **Limitations**: No documented rate limiting or additional auth layers. Images supported, but file attachments rejected.

### Substack

- **Does NOT offer post-by-email for authors.** All publishing happens through the web interface.
- Reader replies to newsletters are forwarded to the author's registered email.
- This is notable as a design choice: avoiding email-based publishing eliminates the entire class of email authentication problems.

### Micro.blog

- **No evidence of a post-by-email feature.** Uses Micropub API and app tokens for posting.
- Has email newsletter features (outbound to subscribers), but does not accept inbound email for publishing.

---

## 3. Spam and Abuse Prevention

### 3.1 Rate Limiting

Essential regardless of the authentication mechanism used:

- **Per-address rate limits**: Cap the number of posts per secret address per time period (e.g., 10 posts per hour, 50 per day)
- **Per-sender rate limits**: If checking From: addresses, limit posts per sender
- **Global rate limits**: Cap total inbound posts across all users to protect system resources
- **Graduated response**: First excess: queue for manual review. Continued excess: temporarily disable the address.

### 3.2 Content Scanning

- **Spam detection**: Use SpamAssassin scores (available from Mailgun, SendGrid, Postmark) to flag or reject likely spam
- **Keyword/pattern filtering**: Block posts containing known spam patterns, excessive URLs, or pharmaceutical keywords
- **Link analysis**: Check URLs against blocklists (Google Safe Browsing, PhishTank)
- **Image analysis**: Scan attached images for inappropriate content if applicable

### 3.3 What Happens if the Secret Address Leaks?

This is the central risk of the per-user secret address model. Leakage vectors include:

- **Email client autocomplete** suggesting the address to other contacts
- **Screenshots or recordings** showing the address
- **Forwarded emails** where the address appears in headers
- **Data breaches** of email providers storing sent-mail records
- **Shoulder surfing** or screen sharing
- **Malware** on the sender's device capturing sent mail

**Mitigation strategies**:

1. **One-click regeneration**: Allow users to immediately generate a new secret address, invalidating the old one. WordPress/Jetpack and Tumblr both offered this.
2. **Automatic rotation**: Periodically rotate addresses (e.g., every 90 days), emailing the user the new address. Follow the dual-secrets pattern: keep the old address valid for a grace period.
3. **Anomaly detection**: Alert the user if posting patterns change (different IP geolocation, unusual posting frequency, sudden content style change).
4. **Confirmation mode**: Optionally require email confirmation for posts, either always or when anomalies are detected.
5. **Address scoping**: Bind each address to additional constraints (allowed sender domains, allowed time windows).
6. **Post moderation queue**: Rather than publishing immediately, queue posts for review, especially from addresses that have been active for a long time without rotation.

### 3.4 Address Rotation Strategies

Borrowing from secrets management best practices:

- **Scheduled rotation**: Rotate every N days. The OWASP Secrets Management Cheat Sheet recommends regular rotation regardless of breach status.
- **Dual-address overlap**: When rotating, keep both old and new addresses active during a grace period (e.g., 7 days) to avoid disrupting the user.
- **Event-driven rotation**: Rotate immediately when suspicious activity is detected.
- **Traceability**: If using per-post unique tokens (embedded in the address or body), leaked tokens can be traced to specific contexts.

---

## 4. Security Considerations

### 4.1 Email Header Injection

**The attack**: If any part of an incoming email (subject, From, body) is used to construct outgoing emails or HTTP headers, an attacker can inject additional headers by including newline characters (`\r\n`).

**Email-to-post relevance**: If the system sends notification emails ("Your post was published") and includes the original subject line, an attacker could inject BCC headers to copy the notification to arbitrary addresses, or inject content headers to modify the email body.

**Prevention**:
- Strip or reject any input containing `\r` or `\n` characters before using it in headers
- Use email-sending libraries that handle header encoding properly (most modern libraries do)
- Never concatenate user input directly into email headers
- Validate and sanitize the subject line before using it as a post title

### 4.2 Malicious Attachments

Email-to-post systems that support image uploads via attachments face significant risk:

**Threats**:
- Executable files disguised as images (e.g., `photo.jpg.exe`)
- Polyglot files that are valid images but also contain embedded scripts
- Zip bombs or oversized files designed to exhaust storage
- EXIF data containing malicious payloads
- SVG files containing embedded JavaScript

**Prevention**:
- **Strict file type allowlist**: Accept only specific image types (JPEG, PNG, GIF, WebP). Reject everything else.
- **Magic byte validation**: Check file headers (magic bytes), not just extensions. A file named `.jpg` should start with `FF D8 FF`.
- **Re-encode images**: Process all images through an image library (e.g., Pillow, Sharp) to strip metadata, normalize format, and destroy any embedded payloads. This is the single most effective defense.
- **Virus scanning**: Scan with ClamAV (open-source, designed for email gateway scanning) or the VirusTotal API (70+ scanner engines, hash-based lookups).
- **Size limits**: Enforce maximum file size per attachment and per email (e.g., 10MB total).
- **Strip EXIF data**: Remove metadata that may contain PII (GPS coordinates, device info) or malicious content.

### 4.3 HTML Content Sanitization (XSS via Email HTML)

This is arguably the most dangerous security concern for email-to-post systems. Email HTML is notoriously messy, and rendering it on a blog creates XSS opportunities.

**The threat**: An attacker sends an email containing HTML with:
- `<script>` tags
- Event handlers (`onclick`, `onerror`, `onload`, `onmouseover`)
- `javascript:` or `data:` URLs
- CSS expressions (`expression()`, `-moz-binding`)
- `<iframe>`, `<embed>`, `<object>` tags
- `<form>` elements that could phish blog readers
- `<meta http-equiv="refresh">` for redirects
- `<base>` tags that redirect relative URLs
- SVG with embedded scripts

**Prevention -- strict allowlist approach**:

Recommended allowed tags:
```
p, br, h1-h6, a (href only, http/https), img (src only, http/https),
ul, ol, li, blockquote, pre, code, em, strong, b, i, u, s, sub, sup,
table, thead, tbody, tr, th, td, hr, dl, dt, dd
```

Recommended allowed attributes:
```
href (on a only, http/https schemes only)
src (on img only, http/https schemes only)
alt (on img)
title (on most elements)
class (for styling, with a prefix requirement)
```

**Strip everything else.** Do not try to blocklist dangerous elements -- the allowlist approach is the only safe strategy.

**Recommended libraries**:
- **JavaScript**: [DOMPurify](https://github.com/cure53/DOMPurify) -- OWASP-recommended, DOM-based sanitizer
- **Python**: [nh3](https://github.com/messense/nh3) (Rust-based, successor to bleach) or [bleach](https://github.com/mozilla/bleach) (deprecated but still widely used)
- **Go**: [bluemonday](https://github.com/microcosm-cc/bluemonday)
- **Rust**: [ammonia](https://github.com/rust-ammonia/ammonia)

**Additional defenses**:
- Set `Content-Security-Policy` headers on blog pages to block inline scripts even if sanitization is bypassed
- Convert HTML emails to Markdown as an intermediate step (strips all HTML structure)
- Offer a "plain text only" mode that ignores HTML entirely
- Sandbox displayed content in an iframe with `sandbox` attribute

### 4.4 Privacy Implications of Storing Raw Emails

Raw emails contain significant PII:

- **Sender identity**: Email address, display name
- **Routing metadata**: Sender IP address, intermediate server IPs, timestamps, email client/user-agent
- **Content**: The email body may contain personal information beyond the intended blog post
- **Attachments**: May contain EXIF data with GPS coordinates, device information
- **Authentication headers**: DKIM signatures, SPF results, received chains

**GDPR compliance requirements**:
- Email addresses are personal data (confirmed under GDPR and CCPA)
- Principle of data minimization (Article 5(1)(c)): only store what is necessary
- Storage limitation (Article 5(1)(e)): don't keep data longer than needed
- Right to erasure (Article 17): must be able to delete all stored data on request
- Security of processing (Article 32): encrypt data at rest

**Best practices**:
- Extract the content you need (post body, title, images) and discard the raw email
- Do not store full email headers beyond what is needed for authentication verification
- Strip EXIF data from images before storing
- If you must store raw emails (for audit/debugging), encrypt at rest and auto-delete after a short retention period (e.g., 30 days)
- Document your data processing in a privacy policy
- Provide a mechanism for users to request deletion of all their stored email data

---

## 5. Recommended Architecture

For a new email-to-post system, use a layered defense-in-depth approach:

### Layer 1: Per-User Secret Addresses (Primary Authentication)
- Generate cryptographically random addresses: `post-<22-char-base62>@blog.example.com`
- Use catch-all routing to receive all mail to the domain
- Look up the token to identify the user
- Offer one-click regeneration

### Layer 2: DKIM/SPF/DMARC Verification (Sender Domain Authentication)
- Require passing DKIM or SPF from your inbound provider (Mailgun, SendGrid, Postmark, or AWS SES all expose this)
- Optionally restrict to specific sender domains per user
- Reject messages that fail all authentication checks

### Layer 3: Rate Limiting and Anomaly Detection
- Per-address rate limits (e.g., 10 posts/hour)
- Alert on unusual patterns
- Automatic temporary lockout on excessive failures

### Layer 4: Content Security
- Sanitize HTML with DOMPurify or equivalent (strict allowlist)
- Scan attachments (allowlist image types, re-encode, virus scan)
- Strip EXIF metadata
- Enforce size limits

### Layer 5: Optional Confirmation
- For first-time posters or anomalous activity, send a confirmation email
- Allow users to opt into always-confirm mode for maximum security

### Layer 6: Privacy and Data Handling
- Extract needed content, discard raw email promptly
- Encrypt stored data at rest
- Implement retention policies and deletion mechanisms

---

## Sources

- [Mailgun Email Authentication](https://www.mailgun.com/blog/deliverability/email-authentication-your-id-card-sending/)
- [Mailgun Storing and Retrieving Messages](https://documentation.mailgun.com/docs/mailgun/user-manual/receive-forward-store/storing-and-retrieving-messages)
- [Mailgun Securing Webhooks](https://documentation.mailgun.com/docs/mailgun/user-manual/webhooks/securing-webhooks)
- [SendGrid Inbound Parse Webhook](https://www.twilio.com/docs/sendgrid/for-developers/parsing-email/setting-up-the-inbound-parse-webhook)
- [Postmark Inbound Webhook](https://postmarkapp.com/developer/webhooks/inbound-webhook)
- [AWS SES Email Receiving Concepts](https://docs.aws.amazon.com/ses/latest/dg/receiving-email-concepts.html)
- [AWS Lambda Blueprint for SES Email Filtering](https://aws.amazon.com/blogs/messaging-and-targeting/introducing-the-aws-lambda-blueprint-for-filtering-emails-received-through-amazon-ses/)
- [Cloudflare Email Workers](https://developers.cloudflare.com/email-routing/email-workers/)
- [Cloudflare Email Workers Runtime API](https://developers.cloudflare.com/email-routing/email-workers/runtime-api/)
- [Cloudflare Mail Authentication Requirements](https://developers.cloudflare.com/changelog/post/2025-06-30-mail-authentication/)
- [WordPress Post by Email](https://wordpress.com/support/post-by-email/)
- [Jetpack Post by Email](https://jetpack.com/support/post-by-email/)
- [Tumblr Email Publishing](https://jimharland.tumblr.com/post/40281969083/mobile-and-email-publishing-with-tumblr)
- [Tumblr Discontinued Post by Email](https://unwrapping.tumblr.com/post/147147742877/post-by-email)
- [Blogger Mail2Blogger Security Vulnerability](https://blogging.nitecruzr.net/2010/05/security-vulnerability-in-mail-to.html)
- [Buttondown Sending via Email](https://docs.buttondown.com/sending-via-email)
- [Why SPF and DKIM Are Not Enough](https://knowledge.ondmarc.redsift.com/en/articles/5042154-why-spf-dkim-are-not-enough)
- [SPF and DKIM Don't Stop Spoofing](https://dmarcwise.io/blog/why-you-need-dmarc)
- [Challenge-Response Spam Filtering (Wikipedia)](https://en.wikipedia.org/wiki/Challenge%E2%80%93response_spam_filtering)
- [DOMPurify](https://github.com/cure53/DOMPurify)
- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [ClamAV Documentation](https://docs.clamav.net/)
- [GDPR and Email](https://gdpr.eu/email-encryption/)
- [Email Injection (Invicti)](https://www.invicti.com/learn/email-injection)
- [Twilio: Email HTML Injection Protection](https://www.twilio.com/en-us/blog/developers/tutorials/building-blocks/dont-get-pwned-via-email-html-injection)
- [Mailtrap Email Authentication Explained](https://mailtrap.io/blog/email-authentication/)
