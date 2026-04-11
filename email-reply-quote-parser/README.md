# Email Reply/Quote Parser

Separating the new content a person actually wrote from the quoted thread, forwarded headers, signatures, and disclaimers stacked below it.

## The Problem

There is no standard for how email clients format quoted replies. Gmail wraps quotes in `<div class="gmail_quote">`. Outlook uses `<div id="divRplyFwdMsg">` — except when it doesn't (different versions produce different HTML). Apple Mail uses `<blockquote type="cite">`. Plain text clients use `>` prefixes and "On [date] wrote:" headers in dozens of languages.

This means parsing email replies is a heuristics problem, not a standards problem. Every approach involves pattern matching against known client behaviors, with a long tail of edge cases that no library fully covers.

## Library Landscape

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

## Recommended Architecture: Layered Parsing

```
Layer 1: Microsoft Graph uniqueBody (if on M365)
    ↓ (if null, empty, or suspiciously equals full body)
Layer 2: HTML-aware library parsing (talon)
    ↓ (if HTML parsing fails or no HTML available)
Layer 3: Plain-text heuristic parsing (mail-parser-reply)
    ↓ (if all else fails)
Layer 4: Store full body, flag as "unparsed"
```

Each layer is independent. The system works without M365 (skip layer 1), without HTML (skip layer 2), and degrades gracefully to storing the full body when nothing else works.

## What Cannot Be Reliably Solved

- **Inline/interleaved replies** — responses interspersed between quoted lines. No library handles this.
- **100% accuracy** — best library achieves ~94%. Budget for 5-10% error rate.
- **All Outlook versions** — too many HTML variations for a single detection strategy.
- **Signature removal without false positives** — signatures blend with content.

## Files

| File | Description |
|------|-------------|
| `notes.md` | Detailed research notes, library analysis, and findings |

*Prototype implementation to follow.*
