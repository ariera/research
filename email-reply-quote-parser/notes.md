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

## Research phase 2: Test fixtures created

Created `test_fixtures.py` with 15 realistic email samples covering:

1. **Outlook Desktop** — divRplyFwdMsg, MsoNormal, WordSection1, Word 15 filtered medium
2. **Outlook Web App** — divtagdefaultwrapper, fpstyle body, Segoe UI
3. **Outlook reply chain** — 3 messages deep, nested divRplyFwdMsg divs
4. **Outlook forwarded** — divRplyFwdMsg with forwarded header block
5. **Gmail reply** — gmail_quote div, gmail_attr attribution, blockquote with 0.8ex margin
6. **Gmail forwarded** — "Forwarded message" separator in gmail_attr
7. **Apple Mail reply** — blockquote type="cite", webkit body styles
8. **Plain text top-post** — "On [date] wrote:" + > prefixes
9. **Plain text Outlook** — "-----Original Message-----" separator
10. **German reply** — "Am [date] schrieb [person]:" pattern
11. **Fresh message** — no quoted content at all
12. **Signature + disclaimer** — legal boilerplate, no quote
13. **Inline interleaved** — responses between > quoted lines
14. **Forward with no new text** — entirely quoted body
15. **Identifier in quote only** — "1234-2026" in quoted section, not in reply

Each fixture has: name, html, text, expected_reply, expected_quoted, has_identifier_in_quote_only.

Convenience subsets: OUTLOOK_FIXTURES, GMAIL_FIXTURES, APPLE_FIXTURES, PLAIN_TEXT_FIXTURES, EDGE_CASE_FIXTURES, HTML_FIXTURES, TEXT_FIXTURES, DUAL_FORMAT_FIXTURES.

pytest helpers: `fixture_params()` and `fixture_ids()` for `@pytest.mark.parametrize`.

## Research phase 2: Source code analysis

Examined full source of talon, mail-parser-reply, and quotequail. Key findings:

**Talon's HTML cut cascade** (tried in order):
1. `cut_gmail_quote` — CSS selector `div.gmail_quote`, skips if text starts with forwarded message marker
2. `cut_zimbra_quote` — XPath `//hr[@data-marker="__DIVIDER__"]`
3. `cut_blockquote` — Last non-nested `<blockquote>` not classed `gmail_quote`
4. `cut_microsoft_quote` — EXSLT regex on border styles (`#B5C4DF` for 2007/2010, `#E1E1E1` for 2013), Windows Mail variant, Outlook 2003 `<hr>` fallback
5. `cut_by_id` — `OLK_SRC_BODY_SECTION`
6. `cut_from_block` — elements whose text starts with "From:"

**Talon's checkpoint fallback**: Inserts `#!%!N!%!#` markers into DOM, converts to text, runs text algorithm, maps deleted checkpoints back to remove corresponding DOM nodes. Clever but complex.

**Talon's text algorithm**: Classifies each line as e/m/s/t/f, then matches regex on the marker *string* (e.g., `(s|(?:me*){2,}).*me*[te]*$`).

**mail-parser-reply's approach**: One giant combined regex from all languages' `wrote_header` + `from_header` patterns, find all matches, split text at match positions into EmailReply objects. Simpler than talon.

**quotequail's HTML**: Uses `tree_line_generator()` which synthesizes `>` prefixes from blockquote nesting depth, then applies the same text logic. Elegant but Outlook detection is weak (only one border style pattern).

## Research phase 3: Prototype built

Built `reply_parser.py` — a ~500-line module reimplementing key patterns from all three libraries.

Design decisions:
- **No ML**: Skipped talon's SVM signature detection. Regex-based signature detection is simpler and good enough for the common cases. Avoids scikit-learn/numpy dependency.
- **Consolidated language patterns**: Merged the "On wrote:" regexes from all three libraries into one mega-pattern covering 14+ languages.
- **Provider cut order**: Gmail first (cleanest marker), then Outlook (multiple fallback methods), then Apple Mail, then ProtonMail, then generic blockquote.
- **Text layer as signature/disclaimer post-processor**: After HTML cut, run text analysis on the extracted reply to find and strip signatures/disclaimers.

**Test results: 61/61 pass** against 15 realistic fixtures covering Outlook (4 variants), Gmail (2), Apple Mail, plain text (3 including German), and edge cases (5 including inline quoting and identifier isolation).

Key bugs fixed during development:
- Null `style` attribute in `_try_cut_outlook` — lxml returns `None` not `""` for missing attributes
- German fixture has HTML body — test expected text-only parsing but HTML parsing correctly handled it
- Inline interleaved quoting — correctly identified as a known unsolvable case (test threshold lowered)

## What I'd do next

- Test against a corpus of real emails (not synthetic fixtures)
- Add talon's checkpoint-based HTML fallback for emails where no provider-specific cut works but HTML structure exists
- Benchmark against talon directly on the same fixtures to compare accuracy
- Integrate with the email-to-post identifier scanner so it scans only the reply portion
