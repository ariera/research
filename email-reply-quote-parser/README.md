# Email Reply/Quote Parser

Separating the new content a person actually wrote from the quoted thread, forwarded headers, signatures, and disclaimers stacked below it.

## The Problem

There is no standard for how email clients format quoted replies. Gmail wraps quotes in `<div class="gmail_quote">`. Outlook uses `<div id="divRplyFwdMsg">` — except when it doesn't (different versions produce different HTML). Apple Mail uses `<blockquote type="cite">`. Plain text clients use `>` prefixes and "On [date] wrote:" headers in dozens of languages.

This means parsing email replies is a heuristics problem, not a standards problem. Every approach involves pattern matching against known client behaviors, with a long tail of edge cases that no library fully covers.

## Existing Library Landscape

### Python

| Library | HTML? | Languages | Maintained? | Accuracy | Approach |
|---------|-------|-----------|-------------|----------|----------|
| `talon` / `superops-talon` | Yes | ~10 | Fork: Mar 2023 | 93.8% | Heuristics + ML (SVM for signatures) |
| `mail-parser-reply` | No | 13 | Dec 2025 | Good | Regex heuristics |
| `quotequail` | Yes | Limited | Sep 2024 | ~85% | Regex heuristics |
| `email-reply-parser` (Zapier) | No | English | No | Good (en) | Regex heuristics |

### Node.js

| Library | HTML? | Maintained? | Approach |
|---------|-------|-------------|----------|
| `email-reply-parser` (Crisp) | No | Nov 2025 | Regex heuristics, RE2 |
| `planer` | Yes | ~2022 | Talon port (CoffeeScript) |

### Microsoft Graph `uniqueBody`

Exchange computes the unique part of a message server-side. When it works, it's the cleanest solution — zero dependencies, full thread context. But it has documented reliability issues (null returns, sometimes returns full body instead of unique part).

## The Prototype

Rather than depending on unmaintained libraries, the prototype (`reply_parser.py`) reimplements the key patterns from talon, mail-parser-reply, and quotequail in a single ~500-line module with a layered architecture:

### Layered Architecture

```
Layer 1: Microsoft Graph uniqueBody (if on M365)
    ↓ (if null, empty, or suspiciously equals full body)
Layer 2: HTML-aware provider-specific cuts (lxml)
    ↓ (if no HTML structure detected)
Layer 3: Plain-text heuristic parsing
    ↓ (if all else fails)
Layer 4: Return full body, flagged as "unparsed"
```

Each layer is independent. The system works without M365 (skip layer 1), without HTML (skip layer 2), and degrades gracefully.

### Layer 2: HTML Provider Cuts

Tried in order (first match wins):

1. **Gmail** — `div.gmail_quote` CSS selector (skips forwarded messages)
2. **Outlook** — `div#divRplyFwdMsg`, border-top separator styles (Outlook 2007/2010/2013, Windows Mail), `OLK_SRC_BODY_SECTION` ID, HR with `tabindex="-1"`
3. **Apple Mail / Thunderbird** — `<blockquote type="cite">`
4. **ProtonMail** — `div.protonmail_quote`
5. **Generic blockquote** — last non-nested `<blockquote>` in the document

### Layer 3: Plain-Text Splitter Detection

Consolidated patterns from talon (10 languages), mail-parser-reply (13 languages), and quotequail (8 languages):

- "On [date], [person] wrote:" in 14+ languages (English, German, French, Dutch, Spanish, Italian, Polish, Swedish, Portuguese, Vietnamese, Russian, Japanese, Korean, Chinese, Czech)
- "-----Original Message-----" and translations (German, Danish, Spanish, French, Russian)
- Outlook underscore separator (32+ underscores)
- From:/Sent:/To:/Subject: header blocks (multilingual, requires 2+ consecutive headers)
- `>` quoted line blocks (3+ consecutive)

Plus signature detection (delimiter `--`, "Sent from my...", closing phrases in multiple languages) and disclaimer detection.

### Test Results

61/61 tests pass against 15 realistic email fixtures:

| # | Fixture | Method | Status |
|---|---------|--------|--------|
| 1 | Outlook Desktop (`divRplyFwdMsg`) | HTML provider cut | Pass |
| 2 | Outlook Web App (OWA) | HTML provider cut | Pass |
| 3 | Outlook reply chain (3 deep) | HTML provider cut | Pass |
| 4 | Outlook forwarded message | HTML provider cut | Pass |
| 5 | Gmail reply (`gmail_quote`) | HTML provider cut | Pass |
| 6 | Gmail forwarded message | HTML provider cut | Pass |
| 7 | Apple Mail (`blockquote type="cite"`) | HTML provider cut | Pass |
| 8 | Plain text top-post ("On ... wrote:") | Text heuristic | Pass |
| 9 | Plain text Outlook ("-----Original Message-----") | Text heuristic | Pass |
| 10 | German reply ("Am ... schrieb:") | HTML provider cut | Pass |
| 11 | Fresh message (no quote) | HTML provider cut | Pass |
| 12 | Signature + disclaimer (no quote) | HTML provider cut | Pass |
| 13 | Inline interleaved quoting | Text heuristic | Pass* |
| 14 | Forward with no new text | HTML provider cut | Pass |
| 15 | Identifier in quote only (not in reply) | HTML provider cut | Pass |

\* Inline interleaved replies are a known hard case — no library solves them. The test accepts partial extraction.

### Critical test: Identifier isolation

Fixture #15 tests the scenario where "1234-2026" appears only in the quoted section. The parser correctly excludes it from the extracted reply, meaning downstream identifier scanning won't produce false matches from quoted content.

## What Cannot Be Reliably Solved

- **Inline/interleaved replies** — responses interspersed between quoted lines. No library handles this. ~94% is the accuracy ceiling.
- **100% accuracy** — best library achieves ~94%. Budget for 5-10% error rate.
- **All Outlook versions** — too many HTML variations for a single detection strategy.
- **Signature removal without false positives** — signatures blend with content.

## Dependencies

- `lxml` + `cssselect` — for HTML parsing (Layer 2). Falls back to text-only if not installed.
- `pytest` — for tests.
- No ML dependencies, no scikit-learn, no numpy.

## Files

| File | Description |
|------|-------------|
| `reply_parser.py` | The layered parser (~500 lines). Entry point: `parse_reply()` |
| `test_parser.py` | pytest test suite — 61 tests across all fixtures |
| `test_fixtures.py` | 15 realistic email fixtures (Outlook, Gmail, Apple Mail, plain text, edge cases) |
| `notes.md` | Detailed research notes, library analysis, source code examination |
