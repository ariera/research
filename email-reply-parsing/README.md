# Email Reply/Quote Parser: Deep Source Code Analysis

Analysis of three Python libraries for extracting original messages from email threads:
**talon** (Mailgun), **mail-parser-reply** (alfonsrv), and **quotequail** (Close.io).

---

## 1. Talon (Mailgun)

**Repo:** https://github.com/mailgun/talon  
**Key files:** `talon/quotations.py`, `talon/html_quotations.py`, `talon/utils.py`

### 1.1 Plain Text Line Classification Algorithm

Talon classifies each line of an email with a single-character marker:

| Marker | Meaning |
|--------|---------|
| `e` | Empty line |
| `m` | Quoted line (starts with `>`) |
| `s` | Splitter line (header/separator between emails) |
| `t` | Text line (presumably from the latest message) |
| `f` | Forwarded message marker (`--- Forwarded message ---`) |

The classification happens in `mark_message_lines()`:

```python
QUOT_PATTERN = re.compile('^>+ ?')
RE_FWD = re.compile("^[-]+[ ]*Forwarded message[ ]*[-]+\s*$", re.I | re.M)
```

For each line:
1. If empty -> `e`
2. If matches `^>+ ?` -> `m`
3. If matches forwarded message pattern -> `f`
4. Otherwise, check if it's a splitter by joining up to `SPLITTER_MAX_LINES=6` consecutive lines and testing against all splitter patterns
5. If splitter match, mark all lines of the splitter as `s`
6. Otherwise -> `t`

### 1.2 Splitter Patterns (Exact Regexes)

These are the patterns talon uses to identify boundaries between emails. They are tested in order:

```python
# 1. ------Original Message------ or ---- Reply Message ----
RE_ORIGINAL_MESSAGE = re.compile(
    '[\s]*[-]+[ ]*(Original Message|Reply Message|'
    'Ursprüngliche Nachricht|Antwort Nachricht|'
    'Oprindelig meddelelse)[ ]*[-]+', re.I)

# 2. "On <date>, <person> wrote:" in 10 languages
RE_ON_DATE_SMB_WROTE = re.compile(
    '(-*[>]?[ ]?('
    'On|Le|W dniu|Op|Am|Em|På|Den|Vào'  # "On" in various languages
    ')[ ].*('
    ',|użytkownik'  # date/sender separator
    ')(.*\n){0,2}.*('
    'wrote|sent|a écrit|napisał|schreef|verzond|geschreven|'
    'schrieb|escreveu|skrev|đã viết'  # "wrote" in various languages
    '):?-*)')

# 3. Reversed word order: "Op/Am <date> schreef/schrieb <person>:"
RE_ON_DATE_WROTE_SMB = re.compile(
    '(-*[>]?[ ]?(Op|Am)[ ].*(.*\n){0,2}.*'
    '(schreef|verzond|geschreven|schrieb)[ ]*.*:)')

# 4. From:/Date:/Subject:/To: header blocks (2+ consecutive headers)
RE_FROM_COLON_OR_DATE_COLON = re.compile(
    '((_+\r?\n)?[\s]*:?[*]?('
    'From|Van|De|Von|Fra|Från|'          # "From"
    'Date|[S]ent|Datum|Envoyé|Skickat|Sendt|Gesendet|'  # "Date/Sent"
    'Subject|Betreff|Objet|Emne|Ämne|'   # "Subject"
    'To|An|Til|À|Till'                    # "To"
    ')[\s]?:([^\n$]+\n){1,2}){2,}', re.I | re.M)

# 5. Russian date format: "02.04.2012 14:20 пользователь email написал:"
re.compile("(\d+/\d+/\d+|\d+\.\d+\.\d+).*\s\S+@\S+", re.S)

# 6. ISO date with GMT: "2014-10-17 11:28 GMT+03:00 Bob <email>:"
re.compile("\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+GMT.*\s\S+@\S+", re.S)

# 7. RFC-style date: "Thu, 26 Jun 2014 14:00:51 +0400 Bob <email>:"
re.compile('\S{3,10}, \d\d? \S{3,10} 20\d\d,? \d\d?:\d\d(:\d\d)?'
           '( \S+){3,6}@\S+:')

# 8. Samsung devices: "Sent from Samsung... <email> wrote:"
re.compile('Sent from Samsung.* \S+@\S+> wrote')

# 9. Android: "---- <person> wrote ----"
RE_ANDROID_WROTE = re.compile('[\s]*[-]+.*(wrote)[ ]*[-]+', re.I)

# 10. Polymail.io format (multi-line mailto)
RE_POLYMAIL = re.compile('On.*\s{2}<\smailto:.*\s> wrote:', re.I)
```

### 1.3 Marker String Regex Matching

After marking all lines, talon applies regex patterns to the marker string itself:

```python
# Main quotation pattern: splitter or 2+ quote markers, followed by anything,
# ending with quote marker lines, then only text/empty after
RE_QUOTATION = re.compile(r"""
    (
        (?:s|(?:me*){2,})   # quotation border: splitter or 2+ quoted lines
        .*                    # anything in between
        me*                   # must end with quoted line
    )
    [te]*$                    # only text or empty after
    """, re.VERBOSE)

# Empty quotation (just splitters/markers, no text)
RE_EMPTY_QUOTATION = re.compile(r"""
    (
        (?:(?:se*)+|(?:me*){2,})
    )
    e*
    """, re.VERBOSE)
```

Key logic in `process_marked_lines()`:
- If no splitter `s` and fewer than 3 consecutive `m` markers, treat all `m` as `t` (no quotation detected)
- If starts with forwarded marker `f`, return everything (don't strip forwards)
- Detect inline replies: pattern `(?<=m)e*(t[te]*)m` means text sandwiched between quoted blocks
- Cut text after splitter: pattern `(se*)+((t|f)+e*)+` removes everything from splitter onward
- Otherwise use RE_QUOTATION or RE_EMPTY_QUOTATION to find and remove the quoted section

### 1.4 Preprocessing

Before classification:
1. **Link bracket replacement:** `<http://...>` becomes `@@http://...@@` to prevent `>` from being mistaken for quote markers (only when the line doesn't already start with `>`)
2. **Splitter line wrapping:** If "On ... wrote:" appears mid-line, insert a newline before it
3. **Max 1000 lines** processed

### 1.5 HTML Quote Cutting Functions

The HTML extraction runs a cascade -- the first function that succeeds wins:

#### `cut_gmail_quote(html_tree)`
```python
# CSS selector: div.gmail_quote
# Removes the element UNLESS its text content starts with "--- Forwarded message ---"
gmail_quote = cssselect('div.gmail_quote', html_message)
if gmail_quote and not RE_FWD.match(gmail_quote[0].text or ''):
    gmail_quote[0].getparent().remove(gmail_quote[0])
```

#### `cut_zimbra_quote(html_tree)`
```python
# XPath: //hr[@data-marker="__DIVIDER__"]
zDivider = html_message.xpath('//hr[@data-marker="__DIVIDER__"]')
```

#### `cut_blockquote(html_tree)`
```python
# XPath: last non-nested blockquote that isn't a gmail_quote
quote = html_message.xpath(
    '(.//blockquote)'
    '[not(@class="gmail_quote") and not(ancestor::blockquote)]'
    '[last()]')
```

#### `cut_microsoft_quote(html_tree)`
Uses EXSLT regex extensions in XPath:

```python
# Outlook 2007/2010/2013 (international + american)
# Pattern: border:none;border-top:solid #COLOR 1.0pt;padding:3.0pt 0UNIT 0UNIT 0UNIT
# Colors: #B5C4DF (Outlook 2007/2010), #E1E1E1 (Outlook 2013)
# Units: cm (international), pt/in (american)
splitter = html_message.xpath(
    "//div[@style[re:match(., "
    "'border:none; ?border-top:solid #(E1E1E1|B5C4DF) 1.0pt; ?"
    "padding:3.0pt 0(in|cm) 0(in|cm) 0(in|cm)')]]|"
    # Windows Mail variant
    "//div[@style='padding-top: 5px; "
    "border-top-color: rgb(229, 229, 229); "
    "border-top-width: 1px; border-top-style: solid;']",
    namespaces={"re": "http://exslt.org/regular-expressions"})

# Special case: Outlook 2010 where splitter is first child
if splitter == splitter.getparent().getchildren()[0]:
    splitter = splitter.getparent()

# Outlook 2003 fallback:
# //div/div[@class='MsoNormal'][@align='center'][@style='text-align:center']
#   /font/span/hr[@size='3'][@width='100%'][@align='center'][@tabindex='-1']
```

After finding the splitter, removes it and ALL following siblings.

#### `cut_by_id(html_tree)`
```python
# Removes elements with specific IDs
QUOTE_IDS = ['OLK_SRC_BODY_SECTION']
```

#### `cut_from_block(html_tree)`
Finds elements whose text content starts with `"From:"` or `"Date:"` using custom XPath functions:
```python
"//*[starts-with(mg:text_content(), 'From:')]|"
"//*[starts-with(mg:text_content(), 'Date:')]"
```
Then walks up to the nearest `<div>`, and removes that div plus all following siblings. Also handles the case where `From:` appears in an element's tail text (after `<hr>` etc.).

### 1.6 Checkpoint-Based HTML Fallback

After the tag-based cuts above, talon runs its text algorithm on the HTML as a fallback:

1. **Add checkpoints:** Recursively insert `#!%!N!%!#` markers after every element's text and tail in the DOM tree. Each gets a unique incrementing number.

2. **Convert to text:** Uses `html_tree_to_text()` which:
   - Removes `<style>` tags and HTML comments
   - Iterates all elements, concatenating text+tail
   - Inserts `\n` before block tags (`div`, `p`, `ul`, `li`, `h1-h3`) and hard breaks (`br`, `hr`, `tr`)
   - Appends href URLs in parentheses
   - Collapses 2-10 consecutive newlines to 2

3. **Record checkpoint positions:** For each text line, record which checkpoint numbers appear on it.

4. **Run text algorithm:** Apply `mark_message_lines()` and `process_marked_lines()` on the plain text (with checkpoints stripped).

5. **Map back to HTML:** If lines were deleted, mark all checkpoints on those lines as "in quotation". Then recursively walk the original HTML tree: if ALL of a node's checkpoints (text + children + tail) are in quotation, remove the entire node. If only some children are in quotation, remove just those children.

---

## 2. mail-parser-reply (alfonsrv)

**Repo:** https://github.com/alfonsrv/mail-parser-reply  
**Key files:** `mailparser_reply/constants.py`, `mailparser_reply/parser.py`

### 2.1 Supported Languages and "On ... wrote:" Patterns

Each language defines a `wrote_header` regex (Apple Mail/Gmail style) and a `from_header` regex (Outlook style):

#### English
```python
# wrote_header (Apple Mail/Gmail):
r'^(?!On[.\s]*On\s(.+?\s?.+?)\swrote:)((?:> ?)*On\s(?:.+?\s?.+?)\s?wrote:)$'
# Negative lookahead prevents matching "On ... On ... wrote:" (double On)

# from_header (Outlook):
r'((?:(?:^|\n|\n(?:> ?)*)[* ]*(?:From|Sent|To|Subject|Date|Cc|Organization):[ *]*(?:\s{,2}).*){2,}(?:\n.*){,1})'
# Requires 2+ consecutive header lines (From:, Sent:, To:, Subject:, etc.)
```

#### German
```python
# wrote_header: Am <date> schrieb <person>:
r'^(?!Am.*Am\s.+?schrieb.*:)((?:> ?)*Am\s(?:.+?\s?)schrieb\s(?:.+?\s?.+?):)$'
# from_header headers: Von|Gesendet|An|Betreff|Datum|Cc|Organisation
```

#### Czech
```python
# wrote_header: Dne <date> napsal(a):
r'^(?!Dne[.\s]*Dne\s(.+?\s?.+?)\snapsal\(a\):)((?:> ?)*Dne\s(?:.+?\s?.+?)\s?napsal\(a\):)$'
# from_header headers: Od|Odesláno|Komu|Předmět|Datum|Kopie
```

#### Danish
```python
# wrote_header: Den/weekday <date> skrev <person>:
r"^(?!Den[.\s]*Den\s(.+?)\sskrev:)((?:> ?)*(?:Den|man|tir|ons|tor|fre|lør|søn|[0-9]).+?\sskrev\s.+?:)$"
# Also matches day names: man, tir, ons, tor, fre, lør, søn
# from_header: includes -----Oprindelig meddelelse----- prefix
# headers: Fra|Sendt|Til|Emne|Dato|Cc|Kopi|Vedhæftet
```

#### Spanish
```python
# wrote_header: El <date> escribió:
r'^(?!El\s.+\s escribió:)((?:> ?)*El\s.+\s escribió:)$'
# from_header headers: De|Enviado|Para|Asunto|Fecha|CC|Organización
```

#### French
```python
# wrote_header: Le <date> a écrit:
r'^(?!Le.*Le\s.+?a écrit[a-zA-Z0-9.:;<>()&@ -]*:)((?:> ?)*Le\s(.+?)a écrit[a-zA-Z0-9.:;<>()&@ -]*:)$'
# from_header headers: De |Envoyé |À |Objet |  |Cc  (note trailing spaces)
```

#### Italian
```python
# wrote_header: Il <date> ha scritto:
r'^(?!Il[.\s]*Il\s(.+?\s?.+?)\sha scritto:)((?:> ?)*Il\s(?:.+?\s?.+?)\s?ha scritto:)$'
# from_header headers: Da|Inviato|A|Oggetto|Data|Cc
```

#### Japanese
```python
# wrote_header: 2024年1月15日(月) 10:30 Person <email>:
r'^(?!.*\d{4}年\d{1,2}月\d{1,2}日\(.\) \d{1,2}:\d{2}.+? <.+?>:.*...)((?:> ?)*\d{4}年\d{1,2}月\d{1,2}日\(.\) \d{1,2}:\d{2}.+? <.+?>):$'
# from_header: uses English headers (From|Sent|To|Subject|Date|Cc)
```

#### Korean
```python
# wrote_header: 2024년 1월 15일 ... 님이 작성하였습니다:
r'^(?!.*\d{4}년 \d{1,2}월 \d{1,2}일.*?님이 작성하였습니다:)((?:> ?)*\d{4}년 \d{1,2}월 \d{1,2}일 .*님이 작성하였습니다:)$'
# from_header headers: 보낸사람|보낸날짜|받는사람|제목|참조
```

#### Dutch
```python
# wrote_header: Op <date> schreef:
r'^(?!Op[.\s]*Op\s(.+?\s?.+?)\sschreef:)((?:> ?)*Op\s(?:.+?\s?.+?)\s?schreef:)$'
# from_header headers: Van|Verzonden|Aan|Onderwerp|Datum|Cc
```

#### Polish
```python
# wrote_header: Dnia <date> nadesłał/napisał(a):
r'^(?!Dnia[.\s]*Dnia\s(.+?\s?.+?)\s(?:nadesłał|napisał\(a\)):)((?:> ?)*Dnia\s(?:.+?\s?.+?)\s?(?:nadesłał|napisał\(a\)):)$'
# from_header headers: Od|Wysłano|Do|Temat|Data|DW
# NOTE: {1,} instead of {2,} -- only requires 1 header line (more permissive)
```

#### Swedish
```python
# wrote_header: Den/weekday ... skrev <person>:
r"^(?!Den[.\s]*Den\s(.+?\s?.+?)\skrev:)((?:> ?)*(?:Den|mån|tis|ons|tor|fre|lör|sön|(?:[0-9]+\s+(?:jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)))[^\n]*skrev\s(?:.+?\s?.+?):)$"
# from_header headers: Från|Skickat|Till|Ämne|Datum|Kopia
```

#### Chinese
```python
# wrote_header: 2024年1月15日 ... 写道：
r'^(?!.*\d{4}年\d{1,2}月\d{1,2}日.*?写道：)((?:> ?)*\d{4}年\d{1,2}月\d{1,2}日.*?写道：)$'
# from_header headers: 发件人|发送时间|收件人|主题|抄送|组织
```

#### "david" (custom software)
```python
# from_header: matches "[Original Message processed by david..." followed by headers
r'((?:^ *(?:> ?)*\[?Original Message processed by david.+?$\n{,4})'
r'(?:.*\n?){,2}'
r'(?:(?:^|\n|\n(?:> ?)*)[* ]*(?:Von|An|Cc)(?:\s{,2}).*){2,})'
```

### 2.2 Additional Separator Patterns

```python
# Outlook 32-underscore separator
OUTLOOK_MAIL_SEPARATOR = r'(\n{2,} ?[_-]{32,})'

# Generic "Original Message" separator
GENERIC_MAIL_SEPARATOR = r'^-{5,} ?Original Message ?-{5,}$'
```

### 2.3 How Splitting Works

The algorithm is straightforward:

1. **Normalize text:** Replace `\r\n` with `\n`, strip each line, ensure underscore separators have 2+ newlines before them.

2. **Build combined regex:** Combine all `wrote_header` + `from_header` patterns for selected languages into one giant regex with `|` alternation.

3. **Find all header matches:** `HEADER_REGEX.findall(text)` returns all header positions.

4. **Split at headers:** For each header match, the text between the previous header and this one becomes an `EmailReply`. The header text itself is stored in the next reply's `.headers` field.

5. **Process each reply:** For each reply fragment, detect signatures and disclaimers.

### 2.4 Signature Detection

```python
# Default: line starts with optional whitespace + "-- \n" or "- word..."
DEFAULT_SIGNATURE_REGEX = r'\s*^(?:> ?)*(?:[-_]{2}\n|- ?\w).*'

# Without list capture (won't match "- item" lists)
NOLIST_SIGNATURE_REGEX = r'\s*^(?:> ?)*(?:[-_]{2}\n).*'

# Language-specific signature phrases (examples):
# English: 'Best regards', 'Kind Regards', 'Thanks,', 'Thank you,', 'Best,'
# German: 'Mit freundlichen Grüßen', 'Beste Grüße'
# French: 'cordialement', 'salutations', 'bonne réception'
```

The full signature regex combines:
- The `--` / `- ` pattern
- Outlook underscore separator (`_{32,}`)
- "Sent from my..." / "Get Outlook for..." patterns
- Language-specific closing phrases

Once a signature is matched, everything from it to the end of the reply is considered signature.

### 2.5 Disclaimer Detection

Disclaimers are matched by patterns like:
```python
# English: 'CAUTION:', 'Disclaimer:', 'Warning:', 'Confidential:', 'CONFIDENTIALITY:'
# German: 'Wichtiger Hinweis:', 'Achtung:'
# Czech: 'Upozornění:', 'Důvěrné:', 'Varování:'
# etc.
```

The disclaimer regex wraps these with flexible whitespace matching and requires the word "mail" to appear within 1-2 lines (to avoid false positives on non-email disclaimer text):
```python
f'{SENTENCE_START}(?:{disclaimers})(?:{OPTIONAL_LINEBREAK}{ALLOW_ANY_EXTENSION}?(?:mail){ALLOW_ANY_EXTENSION}){1,2}'
```

---

## 3. quotequail (Close.io)

**Repo:** https://github.com/closeio/quotequail  
**Key files:** `quotequail/_patterns.py`, `quotequail/_internal.py`, `quotequail/_html.py`

### 3.1 Reply/Forward Patterns

#### Reply patterns (plain text "On ... wrote:" detection):
```python
REPLY_PATTERNS = [
    "^On (.*) wrote:$",                           # English (Apple Mail/Gmail)
    "^Am (.*) schrieb (.*):$",                     # German
    "^Le (.*) a écrit :$",                         # French
    "El (.*) escribió:$",                          # Spanish
    r"^(.*) написал\(а\):$",                       # Russian
    "^Den (.*) skrev (.*):$",                      # Swedish
    "^Em (.*) escreveu:$",                         # Brazilian Portuguese
    "([0-9]{4}/[0-9]{1,2}/[0-9]{1,2}) (.* <.*@.*>)$",  # Gmail YYYY/MM/DD format
]
```

#### Forward patterns:
```python
FORWARD_MESSAGES = [
    "Begin forwarded message",                      # Apple Mail (English)
    "Anfang der weitergeleiteten E-Mail",           # Apple Mail (German)
    "Début du message réexpédié",                   # Apple Mail (French)
    "Inicio del mensaje reenviado",                 # Apple Mail (Spanish)
    "Forwarded [mM]essage",                         # Gmail/Evolution
    "Mensaje reenviado",                            # Gmail (Spanish)
    "Vidarebefordrat meddelande",                   # Gmail (Swedish)
    "Original [mM]essage",                          # Outlook
    "Ursprüngliche Nachricht",                      # Outlook (German)
    "Mensaje [oO]riginal",                          # Outlook (Spanish)
    "Message transféré",                            # Thunderbird (French)
    "Пересылаемое сообщение",                       # mail.ru (Russian)
]

FORWARD_LINE = "________________________________"   # 32 underscores (Outlook/Yahoo)

# Combined: "---+ Forward Message ---+" and "Forward Message:" formats
FORWARD_PATTERNS = (
    [f"^{FORWARD_LINE}$"]
    + [f"^---+ ?{p} ?---+$" for p in FORWARD_MESSAGES]
    + [f"^{p}:$" for p in FORWARD_MESSAGES]
)
```

### 3.2 Outlook HTML Detection (the known bug area)

```python
FORWARD_STYLES = [
    re.compile(
        r"^border:none;border-top:solid #[0-9a-fA-f]{6} 1\.0pt;"
        r"padding:3\.0pt 0(in|cm) 0(in|cm) 0(in|cm)$",
        re.UNICODE,
    ),
]
```

This only matches the exact `border:none;border-top:solid #COLOR 1.0pt;padding:3.0pt 0UNIT...` pattern. Notable limitations:
- No space-after-semicolon variant (talon handles `border:none; border-top:...`)
- No Windows Mail `padding-top: 5px; border-top-color: rgb(229, 229, 229)...` pattern
- No Outlook 2003 `<hr>` inside `MsoNormal` pattern
- The `tree_line_generator` in `_html.py` checks for forward styles and synthesizes a `FORWARD_LINE` ("____...") when it finds one, but this only fires for block elements at the start position

### 3.3 Header Extraction

```python
HEADER_RE = re.compile(r"\*?([-\w ]+):\*?(.*)$", re.UNICODE)
```

Recognizes headers by the `Key: Value` pattern and maps them via `HEADER_MAP`:

```python
HEADER_MAP = {
    # "from" mappings
    "from": "from", "von": "from", "de": "from",
    "от кого": "from", "från": "from",
    # "to" mappings
    "to": "to", "an": "to", "para": "to", "à": "to",
    "pour": "to", "кому": "to", "till": "to",
    # "cc" mappings
    "cc": "cc", "kopie": "cc", "kopia": "cc",
    # "bcc" mappings
    "bcc": "bcc", "cco": "bcc", "blindkopie": "bcc",
    # "reply-to" mappings
    "reply-to": "reply-to", "antwort an": "reply-to",
    "répondre à": "reply-to", "responder a": "reply-to",
    # "date" mappings
    "date": "date", "sent": "date", "received": "date",
    "datum": "date", "gesendet": "date", "enviado el": "date",
    "enviados": "date", "fecha": "date", "дата": "date",
    # "subject" mappings
    "subject": "subject", "betreff": "subject", "asunto": "subject",
    "objet": "subject", "sujet": "subject", "тема": "subject",
    "ämne": "subject",
}
```

Requires `MIN_HEADER_LINES = 2` recognized headers to count as a valid header block.

### 3.4 `unwrap()` Logic

The `unwrap()` function tries to extract the forwarded/replied message structure:

1. **`find_unwrap_start()`** scans lines for:
   - A forward/reply pattern (e.g., "On ... wrote:" or "--- Forwarded message ---")
   - A quoted block (3+ lines starting with `>`)
   - A header block (2+ recognized `Key: Value` headers)

2. **Pattern found:** If forward/reply pattern found, look for headers or quoted block after it:
   - If quoted block follows: unindent the `>` prefixes, check for headers inside the unindented text
   - If headers follow: extract headers, everything after is the forwarded body
   - Otherwise: everything below the pattern is the body

3. **Headers found (no pattern):** Treat as forward, extract headers, rest is body

4. **Quoted block found:** Unindent, check for headers inside. If headers found, treat as forward. Otherwise treat as generic quote.

5. **Reply line parsing:** For "On DATE, USER wrote:" lines, splits date and user:
   ```python
   REPLY_DATE_SPLIT_REGEX = re.compile(
       r"^(.*(:[0-9]{2}( [apAP]\.?[mM]\.?)?)), (.*)?$"
   )
   ```
   Tries to split at the time portion's comma (after seconds/AM/PM), falling back to simple `rsplit(",", 1)`.

### 3.5 HTML Line Extraction

quotequail's HTML handling is notably different from talon's checkpoint approach. It uses `tree_line_generator()`:

1. Walks the HTML tree yielding tokens: element start/end tuples and text strings
2. Accumulates text until hitting a block element or `<br>`, then yields a "line"
3. Tracks `<blockquote>` nesting depth as indentation level
4. Wraps lines with `"> "` prefix per indentation level (like email quoting)
5. Synthesizes a `FORWARD_LINE` ("____...") when encountering a div with Outlook forward styles

This produces plain-text-like lines with quoting markers, allowing the same `find_quote_position()` / `unwrap()` logic to work on HTML. The `slice_tree()` function then cuts the HTML tree at the detected positions using element references tracked during line generation.

### 3.6 Line Wrapping Handling

quotequail handles wrapped lines (long "On ... wrote:" that spans 2 lines) via `MAX_WRAP_LINES = 2`:

```python
def join_wrapped_lines(lines):
    # If previous line ends with < ( [ { " ', join without space
    # Otherwise join with space
    STRIP_SPACE_CHARS = r"""<([{\"'"""
```

---

## Comparative Analysis

### Language Coverage

| Feature | talon | mail-parser-reply | quotequail |
|---------|-------|-------------------|------------|
| "On wrote" languages | 10 | 13 | 8 |
| Outlook header languages | 6 | 13 | 8 (via HEADER_MAP) |
| Forward message patterns | 2 (EN, DE) | per language | 12 |
| Japanese/Korean/Chinese | No | Yes | No |
| Russian | Partial (date format) | No | Yes (wrote/forward) |
| Danish/Czech | No | Yes | No |
| Swedish | Yes (partial) | Yes | Yes |

### HTML Handling

| Feature | talon | mail-parser-reply | quotequail |
|---------|-------|-------------------|------------|
| Gmail `div.gmail_quote` | Yes | No (text-only) | No (uses blockquote) |
| Outlook border styles | Yes (3 versions) | No | Yes (1 version) |
| Windows Mail | Yes | No | No |
| Outlook 2003 `<hr>` | Yes | No | No |
| Zimbra `data-marker` | Yes | No | No |
| `OLK_SRC_BODY_SECTION` id | Yes | No | No |
| Blockquote removal | Yes | No | Yes (via indentation) |
| Checkpoint fallback | Yes | No | No (uses line refs) |

### Algorithm Approach

| Aspect | talon | mail-parser-reply | quotequail |
|--------|-------|-------------------|------------|
| Core approach | Line classification + marker regex | Regex header finding + split | Pattern matching + header extraction |
| Handles inline replies | Yes (detects `m-t-m` pattern) | No | No |
| Signature detection | Separate ML module | Regex-based (per language) | No |
| Disclaimer detection | No | Yes (per language) | No |
| Returns structure | Text only | Reply objects with headers/body/sig | Dict with type/headers/text |
| Output format | Stripped text | List of EmailReply objects | Dict or list of (expanded, text) tuples |

### Key Strengths

- **talon:** Most robust HTML handling, inline reply detection, checkpoint system as fallback
- **mail-parser-reply:** Best language coverage (13 languages), signature/disclaimer detection, structured output
- **quotequail:** Cleanest unwrap/forward metadata extraction, proper `blockquote` indentation handling, forward style synthesis in HTML
