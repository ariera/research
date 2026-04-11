# Separating Reply Content from Quoted/Forwarded Text in Email Messages

## Executive Summary

Extracting just the new content a person wrote in an email reply -- stripping out quoted threads, forwarded messages, and signatures -- is a well-studied but unsolved problem. There is no universal standard for how email clients format quoted replies, and different clients (Outlook, Gmail, Apple Mail, Thunderbird, mobile clients) use different HTML structures, text conventions, and localized patterns. Multiple open-source libraries exist with varying approaches (regex heuristics, ML classifiers, HTML DOM parsing), but none achieve perfect accuracy across all edge cases.

**For a system ingesting emails from Microsoft 365**: The strongest strategy is to use Microsoft Graph API's `uniqueBody` property as the primary extraction method, with a library-based fallback for cases where `uniqueBody` is null or unreliable.

---

## 1. The Problem Space

### 1.1 How Email Clients Format Quoted Replies

Every email client formats quoted/replied content differently. There is no RFC or standard governing this.

#### Plain Text Conventions

| Pattern | Used By | Example |
|---------|---------|---------|
| `>` prefix per line | Universal (RFC-ish) | `> This is quoted text` |
| `>>` nested depth | Universal | `>> Deeper quote` |
| `On [date], [person] wrote:` | Gmail, Thunderbird, generic | `On Jan 5, 2026, Alice wrote:` |
| `-----Original Message-----` | Outlook | Dashes surrounding "Original Message" |
| `---------- Forwarded message ----------` | Gmail | Dashes surrounding "Forwarded message" |
| `Begin forwarded message:` | Apple Mail | Plain text header |
| `----Reply Message----` | Some clients | Dashes around "Reply Message" |
| `From: / Sent: / To: / Subject:` block | Outlook | Multi-line metadata header |

#### HTML Conventions

| Element/Attribute | Used By | Notes |
|-------------------|---------|-------|
| `<div class="gmail_quote">` | Gmail | Primary quote wrapper |
| `<div class="gmail_attr">` | Gmail | "On [date] wrote:" attribution |
| `<div id="divRplyFwdMsg">` | Outlook | Reply/forward metadata container |
| `<div id="appendonsend">` | Outlook | Append-on-send marker |
| `<span id="OLK_SRC_BODY_SECTION">` | Outlook (some versions) | NOT present in all Outlook emails |
| `<div class="WordSection1">` | Outlook | Common container |
| `<hr>` with inline styling | Outlook | Separator with border-top |
| `<blockquote type="cite">` | Apple Mail, Thunderbird | Key differentiator from generic blockquote |
| `<div class="moz-cite-prefix">` | Thunderbird | Attribution prefix |
| `<div class="protonmail_quote">` | ProtonMail | Quote wrapper |
| Generic `<blockquote>` | Various | Standard HTML quote element |
| `border-left` inline CSS | Various | Visual left-border indicator |

**Critical Outlook detail**: Outlook has no single, universal HTML marker across all its versions (desktop 2016/2019/2021/365, OWA, Outlook mobile). Detection requires combining multiple signals: `divRplyFwdMsg`, specific Calibri font styling, `border-top` patterns, and bold "From:"/"Sent:"/"To:"/"Subject:" metadata fields.

### 1.2 Posting Styles

| Style | Description | Parsing Difficulty |
|-------|-------------|-------------------|
| **Top-posting (TOFU)** | Reply above, full quote below. Used by ~90% of corporate email. | Easiest -- split at first separator |
| **Bottom-posting** | Reply below trimmed original. Common in technical mailing lists. | Moderate -- must find where quote ends |
| **Inline/interleaved** | Responses interspersed between quoted lines. | Extremely hard -- no reliable automated solution |

Inline replying is the hardest case. Microsoft Outlook, Gmail, and Yahoo make inline replying difficult or impossible in HTML mode, so it is less common in corporate contexts. However, technical mailing list users and plain-text email users frequently use it.

**No library handles inline replies reliably.** All major parsers either collapse inline replies into a single block or misclassify interleaved content.

### 1.3 Forwarded Messages

Forwarded messages use distinct markers:
- Gmail: `---------- Forwarded message ----------`
- Apple Mail: `Begin forwarded message:`
- Outlook: `-----Original Message-----` (same as replies)
- Generic: `From: / Date: / To: / Subject:` header block

Some libraries (quotequail, talon) can distinguish forwards from replies and extract the forwarded message metadata separately.

### 1.4 Multilingual Challenges

The "On [date], [person] wrote:" pattern varies by language:

| Language | Pattern |
|----------|---------|
| English | `On [date], [person] wrote:` |
| French | `Le [date], [person] a ecrit :` |
| German | `Am [date] schrieb [person]:` |
| Spanish | `El [date], [person] escribio:` |
| Dutch | `Op [date] heeft [person] geschreven:` |
| Polish | `W dniu [date] uzytkownik [person] napisal:` |
| Swedish | `Pa [date] skrev [person]:` |
| Japanese | `[date], [person] wrote:` (plus Japanese-specific patterns) |

Libraries that only match English patterns will fail on non-English emails.

---

## 2. Library Comparison

### 2.1 Python Libraries

#### Talon (Mailgun)

| Attribute | Detail |
|-----------|--------|
| **Repository** | [github.com/mailgun/talon](https://github.com/mailgun/talon) |
| **PyPI** | `talon` (v1.4.4), `talon-v2` (v1.0.0), `superops-talon` (v0.4) |
| **Last original release** | April 2016 (effectively unmaintained) |
| **Latest fork** | `superops-talon` v0.4, March 2023 |
| **Approach** | Heuristics + ML (SVM for signatures) |
| **HTML support** | Yes -- full HTML parsing with provider-specific handlers |
| **Plain text support** | Yes |
| **Languages** | ~10 (English, French, German, Polish, Dutch, Swedish, Vietnamese, Portuguese, Norwegian) |
| **Accuracy** | 93.8% overall; 98%+ on regular replies; weaker on forwards |
| **Processing speed** | 1.92ms average |
| **Dependencies** | scikit-learn, lxml, numpy (heavy) |

**How it works (plain text)**: Marks each line as empty ('e'), quoted-marker ('m'), splitter ('s'), forwarded ('f'), or text ('t'). Analyzes marker sequences to identify quotation blocks using regex patterns for "On...wrote:", "-----Original Message-----", "From:/Date:/To:/Subject:" blocks, and forwarded message headers.

**How it works (HTML)**: Tries provider-specific cuts in order: `cut_gmail_quote`, `cut_zimbra_quote`, `cut_blockquote`, `cut_microsoft_quote`, `cut_by_id`, `cut_from_block`. Falls back to converting HTML to text with checkpoints, applying the plain-text algorithm, then removing corresponding HTML elements.

**ML component**: SVM with Linear Kernel trained on Mailgun internal emails + ENRON dataset. Used only for signature line classification (not quote detection). The heuristic approach handles ~90% of cases; ML handles remaining edge cases.

**Failure modes**: Forwarded messages (3/4 failures in benchmarks), complex signatures before quoted sections, inline replies, Gmail forwarded HTML headers.

**Outlook handling**: Has `cut_microsoft_quote` specifically for Outlook HTML. Detects "-----Original Message-----" in plain text and localized equivalents.

**Verdict**: The most comprehensive library available. HTML support is its standout feature. But it is unmaintained and has heavy dependencies. Use a fork (`superops-talon`) if choosing this path.

---

#### mail-parser-reply

| Attribute | Detail |
|-----------|--------|
| **Repository** | [github.com/alfonsrv/mail-parser-reply](https://github.com/alfonsrv/mail-parser-reply) |
| **PyPI** | `mail-parser-reply` v1.36 |
| **Last release** | December 2025 |
| **Approach** | Regex heuristics |
| **HTML support** | No (text-only) |
| **Plain text support** | Yes |
| **Languages** | 13 (English, German, Danish, Dutch, French, Italian, Swedish, Polish, Japanese, Czech, Spanish, Korean, Chinese) |
| **Dependencies** | Minimal |

**How it works**: Splits email into separate `EmailReply` objects using language-specific regex patterns matching "On [date]...[person] wrote:" headers. Each reply exposes `.content` (raw), `.body` (cleaned), plus separately identified headers, signatures, and disclaimers.

**Strengths**: Most actively maintained Python option. Widest language support. Clean architecture. Disclaimer detection is unique among these libraries. Low dependency footprint. Type-annotated code.

**Limitations**: No HTML support means you must convert HTML to plain text first, losing structural cues that HTML-aware parsers exploit. This is a significant limitation for Outlook emails where the HTML structure carries most of the separation signal.

**Verdict**: Best choice for text-only Python processing. Actively maintained, good language coverage, but the lack of HTML support is a real gap for corporate email.

---

#### quotequail (Close.io)

| Attribute | Detail |
|-----------|--------|
| **Repository** | [github.com/closeio/quotequail](https://github.com/closeio/quotequail) |
| **PyPI** | `quotequail` v0.4.0 |
| **Last release** | July 2024; last commit September 2024 |
| **Approach** | Regex heuristics |
| **HTML support** | Yes (requires libxml) |
| **Plain text support** | Yes |
| **Dependencies** | None mandatory (libxml for HTML) |

**Key functions**:
- `quote(text)` / `quote_html(html)` -- returns list of (is_visible, content) tuples
- `unwrap(text)` / `unwrap_html(html)` -- extracts forwarded/replied message structure with parsed headers

**Accuracy**: ~85% per comparative benchmarks. Processing: 0.96ms average (faster than talon).

**Known issue**: Open bug since 2015 for Outlook reply detection (#4). Outlook's inconsistent HTML markers make detection unreliable. The library looks for specific div styling and `OLK_SRC_BODY_SECTION` span, but these are not present in all Outlook emails.

**Verdict**: Good for extracting forwarded message metadata. Lighter than talon. But Outlook support is weak, which is a problem for M365 environments.

---

#### Zapier email-reply-parser

| Attribute | Detail |
|-----------|--------|
| **Repository** | [github.com/zapier/email-reply-parser](https://github.com/zapier/email-reply-parser) |
| **PyPI** | `email-reply-parser` |
| **Stars** | 523 |
| **Status** | Semi-abandoned (9 open issues, 10 open PRs) |
| **Approach** | Regex heuristics |
| **HTML support** | No |
| **Languages** | English only |

**Core patterns**:
```
SIG_REGEX:        (--|__|-\w)|(^Sent from my (\w+\s*){1,3})
QUOTE_HDR_REGEX:  On.*wrote:$
QUOTED_REGEX:     (>+)
HEADER_REGEX:     ^\*?(From|Sent|To|Subject):\*? .+
```

**Algorithm**: Processes lines in reverse, classifying as quoted/header/signature/content. Merges consecutive similar lines into fragments. Marks fragments hidden based on position relative to headers.

**Verdict**: Simple, well-understood, but English-only and unmaintained. The port of GitHub's original Ruby library. Useful as a reference implementation but not for production multilingual use.

---

#### unquotemail

| Attribute | Detail |
|-----------|--------|
| **Repository** | [github.com/getfernand/unquotemail](https://github.com/getfernand/unquotemail) |
| **PyPI** | `unquotemail` v1.0.11 (January 2026) |
| **Approach** | Progressive: known CSS classes first, then regex fallback |
| **HTML support** | Yes (primary focus) |
| **Test coverage** | 105/168 tests passing (62.5%) |

**How it works**: First checks for provider-specific CSS classes (`.gmail_quote`, `.protonmail_quote`). If not found, falls back to regex matching "On YYYY/MM/dd HH:mm:ss, [sender] wrote:" patterns. Uses html2text for conversion.

**Verdict**: Interesting HTML-first approach, but too immature (37.5% test failure rate). Not production-ready.

---

### 2.2 Node.js Libraries

#### email-reply-parser (Crisp)

| Attribute | Detail |
|-----------|--------|
| **Repository** | [github.com/crisp-oss/email-reply-parser](https://github.com/crisp-oss/email-reply-parser) |
| **npm** | `email-reply-parser` v2.0.1 |
| **Last release** | ~November 2025 |
| **Production use** | ~1 million inbound emails/day at Crisp |
| **Approach** | Regex heuristics |
| **HTML support** | No (plain text only) |
| **Languages** | ~10 (English, French, Spanish, Portuguese, Italian, Japanese, Chinese) |
| **Regex engine** | RE2 (with native RegExp fallback) -- ReDoS safe |

**Verdict**: The best-maintained Node.js option. Battle-tested at scale. But plain-text only, so HTML emails must be converted first.

---

#### Planer (Lever)

| Attribute | Detail |
|-----------|--------|
| **Repository** | [github.com/lever/planer](https://github.com/lever/planer) |
| **npm** | `planer` v1.2.0 |
| **Last release** | ~2022-2023 (not recently updated) |
| **Approach** | Port of talon's heuristics |
| **HTML support** | Yes (requires injected DOM -- jsdom on server) |
| **Languages** | Same as talon |
| **Written in** | CoffeeScript (60.6%) |

**Limitations**: Does NOT handle signatures. Requires providing a DOM implementation. CoffeeScript source is a maintenance concern.

**Verdict**: Only Node.js option with HTML support, but unmaintained and missing signature detection. Use if HTML parsing in JS is a hard requirement.

---

#### node-email-reply-parser

| Attribute | Detail |
|-----------|--------|
| **Repository** | [github.com/t2bot/node-email-reply-parser](https://github.com/t2bot/node-email-reply-parser) |
| **Approach** | Port of GitHub's Ruby library via PHP port |
| **HTML support** | No |

Has an "aggressive" mode for Gmail's multi-line quote breaking. Less maintained than Crisp's version.

---

### 2.3 Other Languages

| Library | Language | Notes |
|---------|----------|-------|
| `email_reply_parser` (GitHub) | Ruby | The original. All others derive from this. |
| `EmailReplyParser` (willdurand) | PHP | Port of GitHub's Ruby library. |
| `email-reply-parser` (ximura) | Go | Supports most locales and signatures. |
| `email-parser` (JetBrains) | Kotlin | QuoteParser class. Separates body, quote header, quotation. |

---

### 2.4 Comparison Matrix

| Library | Language | HTML | Text | Languages | Maintained | Accuracy | Speed |
|---------|----------|------|------|-----------|------------|----------|-------|
| **talon** (superops fork) | Python | Yes | Yes | ~10 | Fork: 2023 | 93.8% | 1.92ms |
| **mail-parser-reply** | Python | No | Yes | 13 | Yes (Dec 2025) | Good | Fast |
| **quotequail** | Python | Yes | Yes | Limited | Yes (Sep 2024) | ~85% | 0.96ms |
| **zapier email-reply-parser** | Python | No | Yes | 1 (English) | No | Good (en) | Fast |
| **unquotemail** | Python | Yes | Yes | Limited | Partial (Mar 2025) | 62.5% tests | Fast |
| **Crisp email-reply-parser** | Node.js | No | Yes | ~10 | Yes (Nov 2025) | Good | Fast |
| **planer** | Node.js | Yes | Yes | ~10 | No (~2022) | ~90.6% | 1.88ms |

---

## 3. Technical Deep Dive: How the Best Libraries Work

### 3.1 Talon's Algorithm (the gold standard for comprehensiveness)

#### Plain Text Pipeline

1. **Preprocessing**: Normalize line endings. Wrap URLs in special markers to prevent `<`/`>` in URLs from being misidentified as quote markers. Insert newlines before splitters that appear on the same line as text.

2. **Line classification**: Each line gets a single-character marker:
   - `'e'` -- empty line
   - `'m'` -- starts with `>` (quotation marker)
   - `'s'` -- matches a splitter regex (separator pattern)
   - `'f'` -- forwarded message marker
   - `'t'` -- text from current message

3. **Splitter detection** via regex matching against:
   - `On [date], [person] wrote:` (9+ languages)
   - `-----Original Message-----` (+ translations)
   - `---------- Forwarded message ----------`
   - `From:/Date:/To:/Subject:` header blocks
   - Android format: `---- [Person] wrote ----`
   - Various date formats (DD/MM/YYYY, ISO 8601, RFC 2822)

4. **Marker sequence analysis**: Examines patterns like `(se*)+` (splitter followed by empties) and `me*` repetitions (quoted lines) to identify quotation blocks.

5. **Postprocessing**: Restore URL brackets, strip trailing whitespace.

#### HTML Pipeline

1. **Provider-specific cuts** (tried in order):
   - `cut_gmail_quote` -- remove `<div class="gmail_quote">`
   - `cut_zimbra_quote` -- Zimbra-specific
   - `cut_blockquote` -- generic `<blockquote>` removal
   - `cut_microsoft_quote` -- Outlook-specific patterns
   - `cut_by_id` -- elements with known IDs
   - `cut_from_block` -- "From:" metadata blocks

2. **Checkpoint fallback**: If no provider-specific cut works:
   - Add unique checkpoint strings to all HTML tags
   - Convert HTML to plain text (preserving checkpoints)
   - Apply the plain-text algorithm
   - Identify which checkpoints were in deleted (quoted) sections
   - Remove corresponding HTML elements

#### Signature Detection (ML)

- **Algorithm**: SVM with Linear Kernel (scikit-learn)
- **Features**: Defined in `featurespace.py` (line position, content patterns, etc.)
- **Training data**: Mailgun internal emails + ENRON dataset
- **Brute force fallback**: Looks for `--` delimiter and common patterns; works ~90% of the time without ML

### 3.2 How Simpler Libraries Work

The GitHub/Zapier/Crisp family of parsers all use the same core approach:

1. Split the email into lines
2. Process lines (often in reverse)
3. Classify each line as: quoted (`>`), header (`From:`/`Sent:`), signature (`--`), or content
4. Group consecutive same-type lines into fragments
5. Mark fragments as visible or hidden based on their position
6. Return only visible fragments

This is simpler than talon but misses HTML structure entirely.

---

## 4. Edge Cases and Failure Modes

### Cases all libraries handle well
- Standard top-posted replies with clear separator
- Fresh emails with no quoted content
- Simple "On [date] wrote:" headers (in supported languages)
- `>` prefixed quoted text

### Cases that cause problems

| Edge Case | Difficulty | Notes |
|-----------|-----------|-------|
| **Inline/interleaved replies** | Very High | No library handles this reliably. Content is interspersed with quotes. |
| **Emails entirely quoted** (forward without new text) | High | Libraries may return empty or full text. Talon handles some cases. |
| **Signatures that look like quoted text** | High | "--" can be a signature delimiter or just dashes in content. ML helps but 25-30% accuracy on complex signatures. |
| **Legal disclaimers/footers** | Medium | mail-parser-reply has explicit disclaimer detection. Others may treat as content or signature. |
| **Auto-generated emails** (notifications, receipts) | Medium | Often have non-standard formatting. Template-based structure doesn't match reply patterns. |
| **Rich formatting, tables, images** | Medium | HTML-only libraries (talon, quotequail) handle these; text-only libraries lose structural context. |
| **Non-English emails** | Medium | Libraries with <5 languages will fail. mail-parser-reply (13 languages) and talon (~10) are best. |
| **Bottom-posted replies** | Medium | Most libraries assume top-posting. Bottom-posted content may be classified as part of the quote. |
| **Outlook's inconsistent HTML** | Medium | No universal marker. Different Outlook versions produce different HTML. |
| **Multiple signatures/disclaimers** | Low-Med | Exchange admins often append organization disclaimers. These stack in threads. |
| **Mobile client signatures** | Low | "Sent from my iPhone" is well-known but variants exist. |

---

## 5. Microsoft-Specific Considerations

### 5.1 Microsoft Graph API `uniqueBody`

The `uniqueBody` property on the [message resource](https://learn.microsoft.com/en-us/graph/api/resources/message?view=graph-rest-1.0) is Microsoft's built-in solution to this exact problem.

**What it is**: The part of the body of the message that is unique to the current message -- computed server-side by Exchange.

**How to retrieve it**:
```
GET /me/messages/{id}?$select=uniqueBody
Prefer: outlook.body-content-type="text"   (or "html")
```

**Key characteristics**:
- Not returned by default -- must explicitly `$select`
- Returns an `itemBody` object with `contentType` (html/text) and `content`
- Computed by Exchange, not by Graph API itself
- Available in both v1.0 and beta endpoints
- Also existed in EWS as the `UniqueBody` element

**Known issues**:
1. **Null returns**: Reports of `uniqueBody` returning null in certain SDK implementations (C# SDK issue [#862](https://github.com/microsoftgraph/msgraph-sdk-dotnet/issues/862)), though it works via Graph Explorer
2. **Not actually unique**: Reports of `uniqueBody` containing the full conversation thread instead of just new content ([PHP SDK issue #1576](https://github.com/microsoftgraph/msgraph-sdk-php/issues/1576))
3. **Incomplete Base64 resources**: Images in `uniqueBody` may have truncated Base64 data
4. **Not available in list operations**: Cannot `$select=uniqueBody` in a batch list request efficiently -- works best on individual message GETs

**Verdict**: When it works, `uniqueBody` is the cleanest solution because Exchange has full context about the message thread and Outlook's own formatting. But it has reliability issues that necessitate a fallback strategy.

### 5.2 Exchange `conversationId` and Threading

Graph API provides `conversationId` and `conversationIndex` on messages, enabling you to:
- Group messages by conversation
- Understand message order within a thread
- Cross-reference: if you have the previous message's body, you can diff against the current message's body as an alternative to library-based parsing

### 5.3 Outlook's HTML Structure

When processing Outlook-originated emails outside of Graph (e.g., emails forwarded to your system from Outlook users via a non-M365 path), key HTML patterns to detect:

```html
<!-- Reply/Forward marker -->
<div id="divRplyFwdMsg" dir="ltr">
  <font face="Calibri, sans-serif" style="font-size:11pt" color="#000000">
    <b>From:</b> ...
    <b>Sent:</b> ...
    <b>To:</b> ...
    <b>Subject:</b> ...
  </font>
</div>

<!-- Other Outlook markers (not universal) -->
<div id="appendonsend">...</div>
<span id="OLK_SRC_BODY_SECTION">...</span>
<div class="WordSection1">...</div>

<!-- Separator line -->
<hr style="display:inline-block;width:98%" tabindex="-1">
```

**Warning**: These patterns vary across Outlook Desktop, OWA (Outlook Web App), and Outlook Mobile. No single pattern is guaranteed to be present.

---

## 6. Recommended Architecture

For a system ingesting emails from M365 that needs to store just the new reply content:

### Strategy: Layered Approach

```
Layer 1: Microsoft Graph uniqueBody
    |
    v  (if null, empty, or suspiciously equals full body)
    |
Layer 2: HTML-aware library parsing
    |
    v  (if HTML parsing fails or no HTML available)
    |
Layer 3: Plain-text heuristic parsing
    |
    v  (if all else fails)
    |
Layer 4: Store full body with metadata flag "unparsed"
```

### Implementation Details

**Layer 1 -- Graph uniqueBody**:
```
GET /me/messages/{id}?$select=subject,uniqueBody,body
Prefer: outlook.body-content-type="text"
```
Compare `uniqueBody` to `body`. If they're identical or `uniqueBody` is null, fall to Layer 2.

**Layer 2 -- HTML-aware parsing** (Python: talon/superops-talon; Node.js: planer):
Parse the HTML body using provider-specific cut functions. This catches Gmail's `gmail_quote`, Outlook's `divRplyFwdMsg`, Apple Mail's `blockquote type="cite"`, etc.

**Layer 3 -- Plain text parsing** (Python: mail-parser-reply; Node.js: Crisp email-reply-parser):
Convert HTML to text if needed, then apply text-based heuristics.

**Layer 4 -- Graceful fallback**:
Store the full body but flag it for potential manual review or reprocessing.

### Language-Specific Recommendations

**If using Python**:
- Primary: `superops-talon` (fork of talon, March 2023) -- best accuracy, HTML support
- Alternative: `mail-parser-reply` (actively maintained, Dec 2025) -- best language support, text-only
- For forwarded message metadata extraction: `quotequail`

**If using Node.js**:
- Primary: `email-reply-parser` by Crisp (actively maintained, Nov 2025) -- best maintained, text-only
- For HTML: `planer` (unmaintained but functional port of talon)
- Consider: calling Python talon via subprocess if HTML accuracy is critical

### What You Cannot Reliably Solve

1. **Inline replies** -- No automated solution exists. These require human reading or AI/LLM-based extraction.
2. **100% accuracy** -- Even the best library (talon) achieves ~94%. Budget for ~5-10% error rate.
3. **All Outlook versions** -- Outlook's HTML varies too much across versions for any single detection strategy.
4. **Signature removal without false positives** -- Signatures blend with content. ML helps but is not reliable enough for production use without human review.

---

## Sources

- [Talon - GitHub (Mailgun)](https://github.com/mailgun/talon)
- [Talon Reply Extraction Benchmark (AgentMail)](https://docs.agentmail.to/talon-reply-extraction)
- [mail-parser-reply - PyPI](https://pypi.org/project/mail-parser-reply/)
- [mail-parser-reply - GitHub](https://github.com/alfonsrv/mail-parser-reply)
- [quotequail - GitHub (Close.io)](https://github.com/closeio/quotequail)
- [quotequail Outlook issue #4](https://github.com/closeio/quotequail/issues/4)
- [email-reply-parser - GitHub (Crisp)](https://github.com/crisp-oss/email-reply-parser)
- [email-reply-parser - npm](https://www.npmjs.com/package/email-reply-parser)
- [planer - GitHub (Lever)](https://github.com/lever/planer)
- [Zapier email-reply-parser - GitHub](https://github.com/zapier/email-reply-parser)
- [unquotemail - GitHub](https://github.com/getfernand/unquotemail)
- [superops-talon - PyPI](https://pypi.org/project/superops-talon/)
- [talon-v2 - PyPI](https://pypi.org/project/talon-v2/)
- [Microsoft Graph message resource (uniqueBody)](https://learn.microsoft.com/en-us/graph/api/resources/message?view=graph-rest-1.0)
- [Exchange UniqueBody element](https://learn.microsoft.com/en-us/exchange/client-developer/web-service-reference/uniquebody)
- [uniqueBody null issue - .NET SDK #862](https://github.com/microsoftgraph/msgraph-sdk-dotnet/issues/862)
- [uniqueBody not unique - PHP SDK #1576](https://github.com/microsoftgraph/msgraph-sdk-php/issues/1576)
- [Outlook quoted content detection (Microsoft Q&A)](https://learn.microsoft.com/en-gb/answers/questions/5514300/how-to-detect-quoted-content-patterns-in-outlook-e)
- [Posting style - Wikipedia](https://en.wikipedia.org/wiki/Posting_style)
- [W3C HTML Threading conventions](https://www.w3.org/TR/1998/NOTE-HTMLThreading-0105)
- [GitHub email_reply_parser (Ruby original)](https://github.com/github/email_reply_parser)
- [JetBrains email-parser (Kotlin)](https://github.com/JetBrains/email-parser)
- [Mailgun signature parsing blog post](https://www.mailgun.com/blog/product/open-sourcing-our-email-signature-parsing-library/)
