# Email Reply/Quote Parser: Research Notes

## Origin

Extracted from the broader email-to-post research project. The reply/quote separation problem is significant enough to warrant its own investigation and prototype.

## The problem

When ingesting emails, you want just the new content the person actually wrote — not the entire quoted conversation thread, forwarded headers, signatures, or legal disclaimers stacked below it. This matters for:
- Storage efficiency (don't store the same text N times across a thread)
- Front-end UX (display only what's new)
- Downstream processing (e.g. identifier scanning — avoid false matches in quoted content)
- AI/LLM pipelines (don't waste tokens on repeated quoted material)

## Research phase 1: Landscape survey

### How email clients format quoted replies

No standard exists. Every client does it differently.

**Plain text conventions:**
- `>` prefix per line (universal-ish, loosely based on RFC 3676)
- "On [date], [person] wrote:" (Gmail, Thunderbird — varies by language)
- "-----Original Message-----" (Outlook)
- "---------- Forwarded message ----------" (Gmail)
- "Begin forwarded message:" (Apple Mail)
- "From: / Sent: / To: / Subject:" block (Outlook)

**HTML conventions:**
- Gmail: `<div class="gmail_quote">`, `<div class="gmail_attr">`
- Outlook: `<div id="divRplyFwdMsg">` (inconsistent across versions), `<div id="appendonsend">`, `<hr>` with specific border styling
- Apple Mail: `<blockquote type="cite">`
- Thunderbird: `<blockquote type="cite">`, `<div class="moz-cite-prefix">`
- ProtonMail: `<div class="protonmail_quote">`

**Outlook is the worst:** Different versions (Desktop 2016/2019/2021/365, OWA, Mobile) produce different HTML. No single universal marker.

### Posting styles

- **Top-posting** (~90% of corporate email): Reply above, full quote below. Easiest to parse.
- **Bottom-posting**: Reply below trimmed original. Must find where quote ends.
- **Inline/interleaved**: Responses interspersed between quoted lines. **No library handles this reliably.**

### Multilingual challenge

"On [date], [person] wrote:" varies by language:
- English: "On [date], [person] wrote:"
- French: "Le [date], [person] a ecrit :"
- German: "Am [date] schrieb [person]:"
- Spanish: "El [date], [person] escribio:"
- 10+ more variations

Libraries with <5 language patterns fail on non-English emails.

## Research phase 1: Library survey

### Python

**talon (Mailgun)** — superops-talon fork
- 93.8% accuracy, 1.92ms average
- HTML + plain text support
- ML signature detection (SVM on Enron dataset)
- ~10 languages
- Original unmaintained since 2016. Use `superops-talon` fork (Mar 2023).
- Heavy deps: scikit-learn, lxml, numpy
- HTML pipeline: tries provider-specific cuts (Gmail, Zimbra, blockquote, Microsoft, ID-based, From-block), falls back to checkpoint-based approach
- Plain text pipeline: classifies lines as empty/quoted-marker/splitter/forwarded/text, analyzes marker sequences

**mail-parser-reply**
- Most actively maintained (v1.36, Dec 2025)
- 13 languages (widest coverage)
- Disclaimer detection (unique feature)
- Text-only — no HTML support (major gap for Outlook)
- Returns list of EmailReply objects with .content, .body, headers, signatures, disclaimers

**quotequail (Close.io)**
- HTML + plain text
- ~85% accuracy, 0.96ms
- `unwrap()` function extracts forwarded message metadata
- Known Outlook detection issue open since 2015
- Last updated Sep 2024

**email-reply-parser (Zapier)**
- Port of GitHub's original Ruby lib
- English only, plain text only
- Semi-abandoned

### Node.js

**email-reply-parser (Crisp)** — best maintained
- ~1M emails/day at Crisp in production
- ~10 locales, RE2 for ReDoS safety
- Plain text only

**planer (Lever)** — talon port
- HTML + text support
- CoffeeScript, unmaintained (~2022)
- No signature detection

### Microsoft Graph `uniqueBody`

Exchange computes the unique part of a message server-side.
- `GET /users/{id}/messages/{id}?$select=uniqueBody`
- When it works: cleanest solution, zero dependencies
- Known issues: sometimes null, sometimes returns full conversation, incomplete Base64 images
- Must be explicitly $selected

## Proposed layered architecture

```
Layer 1: Microsoft Graph uniqueBody (if available)
    ↓ (if null, empty, or equals full body)
Layer 2: HTML-aware library (talon/superops-talon)
    ↓ (if fails or no HTML)
Layer 3: Plain-text heuristics (mail-parser-reply)
    ↓ (if all else fails)
Layer 4: Store full body, flag as "unparsed"
```

## Research phase 2: TODO

- [ ] Actually install and test the libraries against real-world email samples
- [ ] Examine talon's source code — understand the cut functions
- [ ] Test uniqueBody behavior with different email clients
- [ ] Collect/create realistic test fixtures (Outlook, Gmail, Apple Mail, plain text, multilingual)
- [ ] Benchmark accuracy and speed
- [ ] Build the layered prototype
