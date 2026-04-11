# Research Notes: Email-to-Post Landscape

## Research Process

Started by searching for each webhook-based inbound email service individually (Mailgun, SendGrid, Postmark, Amazon SES, Cloudflare Email Workers). Then searched for self-hosted approaches (IMAP polling, aiosmtpd, Haraka, Postfix+pipe). Then investigated existing email-to-post implementations and email parsing libraries.

## Key Findings Along the Way

### Webhook Services

- Mailgun has the richest inbound parsing - it strips signatures and quoted text automatically (stripped-text, stripped-signature, stripped-html fields). This is unique and very valuable for email-to-post.
- SendGrid uses multipart/form-data for its inbound parse webhook (not JSON like its event webhook). This is a quirk to watch out for.
- Postmark delivers clean JSON with StrippedTextReply field and runs SpamAssassin on inbound.
- Amazon SES Lambda events do NOT include the email body - only headers and metadata. You need to store the raw email in S3 first, then fetch it from Lambda. This is a two-step process.
- Cloudflare Email Workers gives you a ReadableStream (message.raw) and you need postal-mime to parse it. Very different model - code runs at the edge, not via webhook to your server.

### Pricing Surprises

- Cloudflare Email Routing is FREE. Email Workers run on Workers free tier (100k requests/day). This is by far the cheapest option.
- Amazon SES inbound is $0.10 per 1,000 emails. Very cheap but you also pay for S3 storage and Lambda invocations.
- Mailgun raised Flex plan prices from $1 to $2 per 1,000 messages in Dec 2025. Inbound counts toward message volume.
- Postmark counts inbound messages the same as outbound - they both consume your monthly allocation. Inbound requires Pro tier ($16.50/mo).
- SendGrid killed its permanent free tier in May 2025. Now only a 60-day trial.

### Self-Hosted Discoveries

- MXHook is a new open-source project specifically for inbound email to webhook. Basically a self-hosted Mailgun Routes alternative. Apache 2.0 license. Docker Compose deployment. This is a great find.
- smtp2http is another lightweight option - a tiny Go binary that receives SMTP and forwards to HTTP webhook.
- Postal (postalserver.io) is a full self-hosted email platform comparable to Mailgun/SendGrid but open source.
- aiosmtpd is the standard Python approach for a custom SMTP server. The handle_DATA method is the key integration point.
- Haraka is battle-tested (used by Craigslist) and can handle thousands of connections per second. Plugin architecture makes it very flexible.

### Email-to-Post Implementation Patterns

Two main approaches emerged across all implementations:

1. **Secret address pattern** (Jetpack, Tumblr, Posthaven): Generate a unique secret email address per user. Anyone who knows the address can post. Simple but relies on address secrecy for auth.

2. **Sender verification pattern** (Posterous, WordPress core): Accept email from known sender addresses. More convenient but less secure (from addresses can be spoofed).

Posterous was the gold standard - it had the most seamless UX:
- Email to post@posterous.com from your registered address
- Subject = title, body = content
- Attachments auto-processed (images -> gallery, audio -> player, video -> embed)
- Special addresses: private@, draft@, blog+facebook@
- Auto-crosspost to social media

### Email Parsing Libraries - Key Insight

The biggest challenge in email-to-post is not receiving the email, it's CLEANING the content. Email HTML is notoriously messy (inline styles, table layouts, Outlook conditional comments). The stack you need:

1. MIME parsing (get the parts): Python email module, mail-parser, flanker; Node: mailparser, postal-mime
2. Reply/quote stripping: email-reply-parser (Zapier), mail-parser-reply (multilingual), talon (ML-based)
3. Signature removal: talon (Mailgun), separate from quote stripping
4. HTML to clean content: html2text, markdownify, BeautifulSoup
5. Image extraction: handle CID-referenced inline images, base64 data URIs, attached images

Mailgun's talon library is impressive - it uses machine learning (SVM classifier trained on Enron dataset) for signature detection. Much more robust than regex-based approaches.

### Security Considerations for Email-to-Post

- DKIM verification can confirm the sending domain hasn't been spoofed
- SPF checks confirm the sending IP is authorized
- DMARC ties SPF and DKIM together
- Google killed Basic Auth in March 2025, everything needs OAuth 2.0 now for IMAP
- Secret address approach avoids sender verification entirely but addresses can leak
- Best practice: combine secret address + sender verification + optional DKIM check

### Modern Authentication Impact on IMAP Polling

- Google disabled Basic Auth for all accounts March 2025
- Microsoft enforcing Modern Authentication (OAuth 2.0) in 2026
- This makes IMAP polling significantly more complex - you need OAuth token management
- Webhook-based approaches avoid this entirely
