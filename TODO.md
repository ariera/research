# Research — Improvement Ideas

---

## 1. Plugin system

**The idea:** Allow extending the app's functionality through a plugin architecture
rather than modifying core code directly.

**Things to figure out:**
- Plugin discovery and loading mechanism (entry points, directory scan, config-based)
- Hook/event system — what lifecycle events can plugins tap into
- Plugin API surface — what do plugins have access to
- Configuration: per-plugin settings
- Isolation and error handling — a broken plugin shouldn't crash the host

---

## 2. Receive via email (email-to-post)

**The idea:** Publish a blog post by sending an email to a dedicated address. The
email subject becomes the title, the body becomes the content.

**Things to figure out:**
- Inbound email handling: dedicated mailbox polling (IMAP), or an inbound email
  service (Mailgun, SendGrid, Postmark all offer inbound routing via webhooks)
- Authentication: how to verify the sender is authorized (allowlist of from-addresses,
  secret token in subject, DKIM verification)
- Content parsing: HTML email → clean post content (strip signatures, quoted replies,
  email client boilerplate)
- Attachments: handle inline images
- Workflow: publish immediately, or save as draft for review?
