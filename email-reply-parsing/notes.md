# Email Reply Parsing Research - Working Notes

## Research Approach

Started by searching broadly for the problem space, then dove deep into specific libraries, their source code and algorithms, Microsoft Graph API capabilities, and email client formatting differences.

## Key Searches Performed

1. General email reply parsing library comparison
2. Talon by Mailgun - GitHub, PyPI, accuracy benchmarks, source code analysis
3. Microsoft Graph API uniqueBody property - docs, known issues, reliability
4. Email client quoted reply format differences across Outlook, Gmail, Apple Mail, Thunderbird
5. quotequail by Close.io - GitHub, capabilities, Outlook issues
6. Crisp email-reply-parser for Node.js - npm, GitHub, patterns
7. mail-parser-reply by alfonsrv - PyPI, GitHub
8. unquotemail by Fernand - GitHub, PyPI
9. Planer (talon JS port) by Lever - npm, GitHub
10. Zapier email-reply-parser Python - source code patterns
11. Outlook HTML structure: divRplyFwdMsg, appendonsend, OLK_SRC_BODY_SECTION
12. Posting styles: top-posting, bottom-posting, inline replying
13. Signature vs quoted text confusion
14. talon-v2, superops-talon, and other maintained forks
15. JetBrains email-parser (Kotlin)
16. Exchange EWS UniqueBody vs Graph API uniqueBody

## Key Findings

### Microsoft uniqueBody is promising but unreliable
- Not returned by default; must use `$select=uniqueBody`
- Reports of it returning null in certain SDKs (C# SDK issue #862)
- Reports of it not being truly unique - returning full conversation (PHP SDK issue #1576)
- Incomplete Base64 resources in images
- When it works, it's the cleanest solution since Exchange itself strips the quotes

### Talon is the most battle-tested but unmaintained
- Last PyPI release: April 2016 (v1.2.5)
- Last meaningful commit: years old
- 93.8% accuracy across real-world tests per AgentMail benchmark
- 98%+ on regular replies, struggles with forwarded messages (3 of 4 failures were forwards)
- Processing speed: 1.92ms average
- Multiple forks exist: talon-v2 (2021), superops-talon (2023), talon-main
- HTML extraction is the standout feature - handles gmail_quote, blockquote, Microsoft quotes, Zimbra quotes

### Talon's HTML extraction algorithm
The _extract_from_html function tries these cuts in order:
1. cut_gmail_quote (div class="gmail_quote")
2. cut_zimbra_quote
3. cut_blockquote (generic blockquote elements)
4. cut_microsoft_quote
5. cut_by_id (various provider-specific IDs)
6. cut_from_block
Then falls back to: convert HTML to text with checkpoints, apply plain-text algorithm, delete corresponding HTML tags

### Talon's plain text algorithm
Marks each line with a character:
- 'e' = empty
- 'm' = starts with ">" (quotation marker)
- 's' = splitter line (separator like "-----Original Message-----")
- 'f' = forwarded message indicator
- 't' = content text
Then analyzes marker sequences to identify quotation blocks.

### mail-parser-reply is the most actively maintained Python option
- Version 1.36, released December 2025
- 13 languages supported
- Detects headers, signatures, and disclaimers separately
- Returns list of EmailReply objects
- BUT: text-only, no HTML support
- Architecture: builds on GitHub's original approach but treats emails as distinct replies instead of fragments

### quotequail handles both HTML and plain text
- Last updated September 2024 (v0.4.0, July 2024)
- Has unwrap() function that extracts forwarded message metadata
- Known Outlook detection issue (open since 2015)
- ~85% accuracy per AgentMail benchmark
- Processing: 0.96ms average (faster than talon)
- No mandatory dependencies; HTML requires libxml

### Crisp email-reply-parser (Node.js) is the best maintained JS option
- ~1 million inbound emails/day in production at Crisp
- v2.0.1 published ~November 2025
- 10+ locales
- Uses RE2 regex engine for ReDoS protection
- Plain text only - no HTML parsing
- 152 commits, actively maintained

### Planer (Node.js) is the talon port but poorly maintained
- Last published ~2024, described as "2 years ago"
- Written in CoffeeScript (!)
- Handles both HTML and plain text
- Does NOT do signature detection
- Requires injected DOM (jsdom for server)

### unquotemail is young and incomplete
- 105 of 168 tests passing
- Progressive approach: known markup first, then regex fallback
- Supports Gmail/ProtonMail specific classes
- HTML-first approach with html2text conversion
- Last commit March 2025

### Zapier email-reply-parser (Python)
- 523 stars, 9 open issues, 10 open PRs
- Appears semi-abandoned
- Simple regex patterns: SIG_REGEX, QUOTE_HDR_REGEX, QUOTED_REGEX, HEADER_REGEX
- Only matches English "On.*wrote:" - no localization
- Plain text only

### Email Client Format Specifics Discovered

**Gmail (HTML):**
- `<div class="gmail_quote">` wraps quoted content
- `<div class="gmail_attr">` wraps "On [date] wrote:" line
- Uses blockquote for older format

**Outlook (HTML):**
- `<div id="divRplyFwdMsg">` - main reply/forward container
- `<div id="appendonsend">` - append-on-send marker
- `<span id="OLK_SRC_BODY_SECTION">` - NOT present in all Outlook emails
- `<div class="WordSection1">` - common container
- `<hr>` separator with specific styling
- Bold "From:", "Sent:", "To:", "Subject:" fields
- Calibri font, specific border-top styling
- No consistent universal marker across Outlook versions

**Apple Mail (HTML):**
- `<blockquote type="cite">` - key identifier
- Vertical bar "|" visual indicator
- Different from standard blockquote (uses type attribute)

**Thunderbird (HTML):**
- Also uses `<blockquote type="cite">`
- `<div class="moz-cite-prefix">` for attribution

**ProtonMail:**
- `<div class="protonmail_quote">`

**Zimbra:**
- Has specific quote format handled by talon

**Plain text (universal conventions):**
- ">" prefix for quoted lines
- ">>" for nested quotes
- "On [date], [person] wrote:" header
- "-----Original Message-----" (Outlook)
- "---------- Forwarded message ----------" (Gmail)
- "Begin forwarded message:" (Apple Mail)
- "----Reply Message----"
- "From: / Date: / To: / Subject:" block headers

### Posting Styles Complicate Everything
- **Top-posting (TOFU)**: Reply above, full quote below. Most common. Easiest to parse.
- **Bottom-posting**: Reply below trimmed quote. Parser must identify where quote ends and reply begins.
- **Inline/interleaved**: Reply interspersed with quoted sections. Nearly impossible to parse programmatically. Most parsers give up or produce wrong results.

### Signature vs Quote Confusion
- Signatures often use "--" delimiter but not always
- "Sent from my iPhone" type signatures
- Legal disclaimers can look like quoted text
- Talon uses ML (SVM classifier) specifically for signature detection
- Signature detection accuracy reportedly 25-30% for complex cases

### The uniqueBody advantage for M365
If the system is ingesting from Microsoft 365 via Graph API:
- uniqueBody is the FIRST thing to try
- It's computed server-side by Exchange
- Returns just the new content as HTML or text
- Doesn't require `$select` on list operations - only on individual GET
- Caveats: can be null, can be inaccurate, incomplete base64 in images
- Should be used as primary strategy with library-based fallback

## Conclusions

For an M365-centric system, the recommended approach is:

1. **Primary**: Use Microsoft Graph `uniqueBody` - it's free, server-computed, no dependencies
2. **Fallback for when uniqueBody is null/unreliable**: Use a library
3. **Best Python library**: talon (via superops-talon fork) for HTML+text, or mail-parser-reply for text-only
4. **Best Node.js library**: Crisp email-reply-parser for text, planer for HTML
5. **Always strip signatures separately** if needed
6. **Accept that inline replies cannot be reliably parsed** by any library
