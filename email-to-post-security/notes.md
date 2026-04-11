# Research Notes: Email-to-Post Authentication & Security Patterns

## Research Process

### Searches Conducted
1. Email authentication protocols (SPF, DKIM, DMARC) for sender verification
2. Mailgun inbound webhook - DKIM/SPF verification results in headers
3. SendGrid inbound parse webhook - authentication fields available
4. Postmark inbound webhook - authentication data in payload
5. AWS SES inbound email - SPF/DKIM/DMARC verification for Lambda processing
6. Cloudflare Email Workers - runtime API and auth header access
7. WordPress Post by Email / Jetpack implementation details
8. Tumblr post-by-email feature and its security model
9. Blogger/Mail2Blogger security vulnerability (secret word brute-force)
10. Buttondown sending-via-email feature
11. Substack email posting model
12. Micro.blog email features (could not find a post-by-email feature)
13. PGP/S-MIME email signature verification for automated systems
14. Challenge-response spam filtering history and limitations
15. Secret email address leakage and rotation strategies
16. Per-user unique addresses, plus addressing, catch-all patterns
17. Email HTML sanitization (DOMPurify, bleach) and XSS prevention
18. Email header injection attacks
19. Malicious attachment scanning (ClamAV, VirusTotal)
20. GDPR/privacy implications of storing raw emails
21. Defense-in-depth email security best practices

### Key Findings

#### Provider DKIM/SPF Verification Support
- **Mailgun**: Exposes `X-Mailgun-Dkim-Check-Result` (Pass/Fail) and `X-Mailgun-Spf` (Pass/Neutral/Fail/SoftFail) headers on inbound messages when spam filtering is enabled. Also provides spam score and classification.
- **SendGrid**: Inbound parse webhook includes `dkim` field (JSON with per-domain pass/fail) and `SPF` field (none/fail/pass). Also provides SpamAssassin score when spam checking enabled.
- **Postmark**: Inbound webhook includes `Headers` array with `X-Spam-Tests` containing values like `DKIM_SIGNED,DKIM_VALID,SPF_PASS`. Results embedded in SpamAssassin test names rather than dedicated fields.
- **AWS SES**: Verifies SPF, DKIM, DMARC by default on inbound email. Results provided in SNS notifications. Lambda blueprint for inbound email checks SPF/DKIM/spam/virus status.
- **Cloudflare Email Workers**: Requires emails pass SPF or DKIM to forward (as of July 2025). Workers get access to `headers` object but DKIM/SPF results not explicitly documented in the runtime API.

#### From-Address Spoofing Reality
- From addresses are trivially spoofed because SPF checks the envelope Return-Path, DKIM checks the d= domain, but neither inherently protects the visible From: header.
- DMARC is required to enforce alignment between SPF/DKIM and the From: header.
- Even with DMARC, many sending domains still have p=none policy, meaning failures are only reported, not enforced.
- Relying solely on From-address allowlisting is insecure by design.

#### Blogger Mail2Blogger Vulnerability (Real-World Case Study)
- Blogger used a user-chosen "secret word" appended to an email address for post-by-email.
- Attackers brute-forced weak secret words, gaining the ability to publish spam posts to victim blogs.
- Blogger eventually disabled easily guessable secret words, but the damage was done.
- Lesson: User-chosen secrets are weak. System-generated random tokens are essential.

#### Tumblr Post-by-Email
- Used a per-blog secret email address (system-generated).
- Did NOT verify the From: address -- anyone with the secret address could post.
- Could regenerate if leaked.
- Feature was discontinued in July 2016.

#### WordPress/Jetpack Post by Email
- Uses `<random-string>@post.wordpress.com` format.
- Address is system-generated (random letters and numbers).
- Can be regenerated on demand.
- No From-address verification -- security relies entirely on address secrecy.
- Still active via Jetpack.

#### Buttondown
- Uses email address matching: sender must match newsletter's configured email.
- No rate limiting or additional auth documented.
- Uses Postmark MX records for inbound processing.
- Images supported, attachments rejected.

#### Substack
- Does NOT appear to offer post-by-email for authors.
- Authors publish through the web interface.
- Subscriber replies forwarded to author's email.

#### Micro.blog
- Could not find evidence of a post-by-email feature.
- Uses Micropub API and app tokens for posting.
- Has email newsletter features (outbound only).

#### Challenge-Response Systems
- Originated in 1997. Sends a challenge (CAPTCHA, reply link) to alleged sender.
- Major problem: backscatter -- when spammers forge addresses, challenges go to innocent parties.
- Interacts badly with mailing lists and automated senders.
- Largely fallen out of favor.
- Could work for email-to-post if implemented as "we received your post, click here to confirm publication" but adds friction.

#### PGP/S-MIME for Email Authentication
- PGP clearsigning works well conceptually: sign the email body, receiver verifies with sender's public key.
- S/MIME certificates provide CA-backed identity verification.
- Both can be verified programmatically (gpg --verify, OpenSSL libraries).
- Major barrier: almost nobody uses PGP/S-MIME in practice. Very niche audience.
- Would provide strongest authentication but worst usability.

#### HTML Sanitization for Email Content
- Email HTML is notoriously messy and dangerous -- different from web HTML.
- OWASP recommends DOMPurify (JavaScript) or bleach (Python, now deprecated -- successor is nh3/ammonia).
- Must strip: script tags, event handlers (onclick, onerror), javascript: URLs, data: URLs, style tags with expressions, form elements, iframes, embeds, objects.
- Content Security Policy (CSP) provides defense-in-depth on the rendered page.
- Strict allowlist of tags (p, a, img, h1-h6, ul, ol, li, blockquote, br, em, strong, code, pre) is safest.

#### Attachment Security
- ClamAV: open-source, designed for email gateway scanning, detects millions of threats.
- VirusTotal API: 70+ scanner engines, hash-based lookups, rate-limited.
- Best practice: scan before storing/serving, reject or quarantine suspicious files.
- Allowlist file types (images only is safest for blog posts).
- Check file headers (magic bytes), not just extensions.

#### GDPR/Privacy Considerations
- Email addresses are PII under GDPR.
- Raw emails may contain sender IP, routing headers, personal content.
- Must have data retention policy -- don't store raw emails indefinitely.
- Right to erasure (Article 17) applies.
- Encrypt stored email data at rest.
- Minimize what you store -- extract content, discard raw email.
