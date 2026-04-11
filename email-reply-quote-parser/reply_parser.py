"""
Layered email reply/quote parser.

Extracts just the new content a person wrote, stripping quoted replies,
forwarded messages, signatures, and disclaimers.

Architecture:
    Layer 1: Microsoft Graph uniqueBody (if provided)
    Layer 2: HTML-aware parsing (provider-specific CSS/ID cuts + checkpoint fallback)
    Layer 3: Plain-text heuristic parsing (splitter detection + line classification)
    Layer 4: Return full body flagged as "unparsed"

Each layer is independent. The system works without M365 (skip layer 1),
without HTML (skip layer 2), and degrades gracefully.

No external dependencies beyond the standard library and lxml (for HTML parsing).
This is a deliberate choice — the prototype reimplements the key patterns from
talon, mail-parser-reply, and quotequail rather than depending on unmaintained
libraries.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# Optional: lxml for HTML parsing. Falls back to text-only if not available.
try:
    from lxml import html as lxml_html
    from lxml import etree

    HAS_LXML = True
except ImportError:
    HAS_LXML = False


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class ParseMethod(Enum):
    GRAPH_UNIQUE_BODY = "graph_unique_body"
    HTML_PROVIDER_CUT = "html_provider_cut"
    HTML_CHECKPOINT = "html_checkpoint"
    TEXT_HEURISTIC = "text_heuristic"
    UNPARSED = "unparsed"


@dataclass
class ParseResult:
    """Result of parsing an email body."""

    reply: str  # The extracted new content
    quoted: str  # The quoted/forwarded content that was removed
    method: ParseMethod  # Which layer produced this result
    confidence: float  # 0.0 - 1.0
    signature: Optional[str] = None  # Detected signature, if any
    disclaimer: Optional[str] = None  # Detected disclaimer, if any

    @property
    def is_empty(self) -> bool:
        return not self.reply.strip()

    @property
    def was_parsed(self) -> bool:
        return self.method != ParseMethod.UNPARSED


# ---------------------------------------------------------------------------
# Plain text patterns (drawn from talon, mail-parser-reply, quotequail)
# ---------------------------------------------------------------------------

# "On [date], [person] wrote:" in multiple languages
# Consolidated from talon (10 languages), mail-parser-reply (13), quotequail (8)
RE_ON_WROTE = re.compile(
    r"^(?:>[ ]?)*"  # optional quote markers
    r"(?:"
    # English: On ... wrote:
    r"On\s.+?wrote:"
    # German: Am ... schrieb ...:
    r"|Am\s.+?schrieb\s.+?:"
    # French: Le ... a écrit ... :
    r"|Le\s.+?a\sécrit[^:]*:"
    # Dutch: Op ... schreef:
    r"|Op\s.+?schreef:"
    # Spanish: El ... escribió:
    r"|El\s.+?escribió:"
    # Italian: Il ... ha scritto:
    r"|Il\s.+?ha\sscritto:"
    # Polish: Dnia ... napisał(a): / W dniu ... napisał:
    r"|(?:Dnia|W\sdniu)\s.+?(?:napisał(?:\(a\))?|nadesłał):"
    # Swedish: Den ... skrev ...:
    r"|(?:Den|mån|tis|ons|tor|fre|lör|sön).+?skrev\s.+?:"
    # Portuguese: Em ... escreveu:
    r"|Em\s.+?escreveu:"
    # Norwegian/Danish: ... skrev ...:
    r"|Den\s.+?skrev:"
    # Vietnamese: Vào ... đã viết:
    r"|Vào\s.+?đã\sviết:"
    # Russian: ... написал(а):
    r"|.+?\sнаписал(?:\(а\))?:"
    # Japanese: 2024年1月15日(月) 10:30 Person <email>:
    r"|\d{4}年\d{1,2}月\d{1,2}日\(.\)\s\d{1,2}:\d{2}.+?<.+?>:"
    # Korean: ... 님이 작성하였습니다:
    r"|\d{4}년\s\d{1,2}월\s\d{1,2}일\s.+님이\s작성하였습니다:"
    # Chinese: ... 写道：
    r"|\d{4}年\d{1,2}月\d{1,2}日.+?写道[：:]"
    # Czech: Dne ... napsal(a):
    r"|Dne\s.+?napsal\(a\):"
    r")\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# "-----Original Message-----" and translations
RE_ORIGINAL_MESSAGE = re.compile(
    r"^\s*-{3,}\s*(?:"
    r"Original Message|Reply Message"
    r"|Ursprüngliche Nachricht|Antwort Nachricht"
    r"|Oprindelig meddelelse"
    r"|Mensaje original|Mensaje reenviado"
    r"|Message transféré"
    r"|Forwarded message"
    r"|Begin forwarded message"
    r"|Anfang der weitergeleiteten E-Mail"
    r"|Début du message réexpédié"
    r"|Inicio del mensaje reenviado"
    r"|Пересылаемое сообщение"
    r")\s*-{0,}",
    re.MULTILINE | re.IGNORECASE,
)

# Outlook underscore separator (32+ underscores)
RE_OUTLOOK_SEPARATOR = re.compile(r"^\s*[_]{32,}\s*$", re.MULTILINE)

# From:/Sent:/To:/Subject: header block (2+ consecutive, multilingual)
RE_HEADER_BLOCK = re.compile(
    r"(?:^[ *>]*(?:"
    r"From|Van|De|Von|Fra|Från|Od|보낸사람|发件人"
    r"|Sent|Date|Datum|Envoyé|Skickat|Sendt|Gesendet|Enviado|Odesláno|보낸날짜|发送时间"
    r"|To|An|Til|À|Till|Komu|받는사람|收件人"
    r"|Subject|Betreff|Objet|Emne|Ämne|Předmět|Asunto|Oggetto|제목|主题"
    r"|Cc|Kopie|Kopia|DW|참조|抄送"
    r")[*]?\s*:[ ]*[^\n]+\n?){2,}",
    re.MULTILINE | re.IGNORECASE,
)

# Samsung / mobile "Sent from" patterns
RE_SENT_FROM = re.compile(
    r"^\s*(?:Sent from (?:my |Samsung |Yahoo ).+|"
    r"Get Outlook for .+|"
    r"Sent from Mail for .+)\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# Signature delimiter
RE_SIGNATURE_DELIMITER = re.compile(r"^(?:>[ ]?)*-- ?\s*$", re.MULTILINE)

# Common closing phrases (signature starters)
RE_CLOSING_PHRASES = re.compile(
    r"^\s*(?:"
    r"Best regards|Kind regards|Best|Regards|Thanks|Thank you|Cheers"
    r"|Mit freundlichen Grüßen|Beste Grüße|Viele Grüße"
    r"|Cordialement|Salutations"
    r"|Saludos|Atentamente"
    r"|Cordiali saluti|Distinti saluti"
    r"|Met vriendelijke groet"
    r"|Med vänliga hälsningar"
    r")[\s,]*$",
    re.MULTILINE | re.IGNORECASE,
)

# Disclaimer indicators
RE_DISCLAIMER = re.compile(
    r"^\s*(?:CAUTION|Disclaimer|DISCLAIMER|Warning|WARNING"
    r"|CONFIDENTIAL|Confidential|CONFIDENTIALITY"
    r"|Wichtiger Hinweis|Achtung"
    r"|This (?:email|message|communication) (?:and any|is)"
    r")[\s:].{0,200}(?:mail|email|message|recipient|intended)",
    re.MULTILINE | re.IGNORECASE | re.DOTALL,
)

# Quoted line marker
RE_QUOTED_LINE = re.compile(r"^>+\s?", re.MULTILINE)


# ---------------------------------------------------------------------------
# HTML patterns (CSS selectors and IDs for provider-specific cuts)
# ---------------------------------------------------------------------------

# Gmail quote wrapper
GMAIL_QUOTE_SELECTOR = "div.gmail_quote"
GMAIL_ATTR_SELECTOR = "div.gmail_attr"

# Outlook reply/forward marker
OUTLOOK_RPLY_FWD_ID = "divRplyFwdMsg"

# Outlook append-on-send marker
OUTLOOK_APPEND_ID = "appendonsend"

# Outlook OLK source body section
OUTLOOK_OLK_ID = "OLK_SRC_BODY_SECTION"

# Apple Mail / Thunderbird blockquote
APPLE_BLOCKQUOTE_TYPE = "cite"

# ProtonMail
PROTONMAIL_QUOTE_SELECTOR = "div.protonmail_quote"

# Outlook border-top separator styles (multiple versions)
RE_OUTLOOK_BORDER_STYLE = re.compile(
    r"border:none;\s*border-top:solid\s+#[0-9a-fA-F]{6}\s+1\.0pt;\s*"
    r"padding:3\.0pt\s+0(?:in|cm)\s+0(?:in|cm)\s+0(?:in|cm)"
)

# Windows Mail border style
RE_WINDOWS_MAIL_STYLE = re.compile(
    r"padding-top:\s*5px;\s*border-top-color:\s*rgb\(229,\s*229,\s*229\);\s*"
    r"border-top-width:\s*1px;\s*border-top-style:\s*solid"
)

# Forwarded message text marker (used in both HTML and plain text)
RE_FWD_MARKER = re.compile(
    r"^[-]+\s*Forwarded message\s*[-]+", re.IGNORECASE | re.MULTILINE
)


# ---------------------------------------------------------------------------
# Layer 1: Microsoft Graph uniqueBody
# ---------------------------------------------------------------------------


def parse_with_unique_body(
    unique_body: Optional[str],
    full_body: Optional[str],
) -> Optional[ParseResult]:
    """
    Use Microsoft Graph's uniqueBody if available.

    Returns None if uniqueBody is missing, empty, or suspiciously equals
    the full body (which indicates Exchange failed to compute it).
    """
    if not unique_body or not unique_body.strip():
        return None

    if full_body and unique_body.strip() == full_body.strip():
        # uniqueBody equals full body — Exchange didn't actually strip anything.
        # This happens with fresh messages (correct) or when uniqueBody fails.
        # Return it but with lower confidence.
        return ParseResult(
            reply=unique_body.strip(),
            quoted="",
            method=ParseMethod.GRAPH_UNIQUE_BODY,
            confidence=0.6,
        )

    quoted = ""
    if full_body:
        # The quoted portion is what's in full_body but not in unique_body
        # This is approximate but useful for display
        idx = full_body.find(unique_body.strip()[:50])
        if idx >= 0:
            quoted = full_body[idx + len(unique_body.strip()) :]

    return ParseResult(
        reply=unique_body.strip(),
        quoted=quoted.strip(),
        method=ParseMethod.GRAPH_UNIQUE_BODY,
        confidence=0.9,
    )


# ---------------------------------------------------------------------------
# Layer 2: HTML-aware parsing
# ---------------------------------------------------------------------------


def _strip_html_to_text(html_str: str) -> str:
    """Convert HTML to plain text, preserving block structure."""
    if not html_str:
        return ""

    if HAS_LXML:
        try:
            doc = lxml_html.fromstring(html_str)
            return _tree_to_text(doc)
        except Exception:
            pass

    # Fallback: regex-based strip
    text = re.sub(r"<style[^>]*>.*?</style>", "", html_str, flags=re.DOTALL | re.I)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</?(?:p|div|tr|li|h[1-6])[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&[a-zA-Z]+;", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _tree_to_text(element) -> str:
    """Convert an lxml element tree to readable text."""
    block_tags = {
        "div",
        "p",
        "ul",
        "ol",
        "li",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "tr",
        "table",
        "blockquote",
        "pre",
    }
    break_tags = {"br", "hr"}
    lines = []

    def _walk(el, depth=0):
        tag = el.tag if isinstance(el.tag, str) else ""
        if tag in ("style", "script", "head"):
            return

        if tag in block_tags or tag in break_tags:
            lines.append("\n")

        text = (el.text or "").strip()
        if text:
            lines.append(text)

        for child in el:
            _walk(child, depth + 1)

        tail = (el.tail or "").strip()
        if tail:
            if tag in block_tags or tag in break_tags:
                lines.append("\n")
            lines.append(tail)

        if tag in block_tags:
            lines.append("\n")

    _walk(element)
    result = " ".join(lines)
    result = re.sub(r" *\n *", "\n", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def _remove_element_and_tail(el):
    """Remove an element and everything after it among siblings."""
    parent = el.getparent()
    if parent is None:
        return
    # Preserve text before the element
    prev = el.getprevious()
    if el.tail:
        if prev is not None:
            prev.tail = (prev.tail or "") + el.tail
        else:
            parent.text = (parent.text or "") + el.tail
    parent.remove(el)


def _remove_element_and_following_siblings(el):
    """Remove an element and all siblings that follow it."""
    parent = el.getparent()
    if parent is None:
        return
    siblings = list(parent)
    idx = siblings.index(el)
    for sibling in siblings[idx:]:
        parent.remove(sibling)


def _try_cut_gmail(doc) -> Optional[str]:
    """Remove Gmail quote div."""
    for el in doc.cssselect(GMAIL_QUOTE_SELECTOR):
        text_content = (el.text_content() or "").strip()
        # Don't cut forwarded messages
        if RE_FWD_MARKER.match(text_content):
            continue
        _remove_element_and_following_siblings(el)
        return _tree_to_text(doc)
    return None


def _try_cut_outlook(doc) -> Optional[str]:
    """Remove Outlook reply/forward markers and everything below."""
    # Method 1: divRplyFwdMsg
    for el in doc.iter():
        el_id = el.get("id", "")
        if el_id == OUTLOOK_RPLY_FWD_ID:
            _remove_element_and_following_siblings(el)
            return _tree_to_text(doc)

    # Method 2: Outlook border-top separator styles
    for el in doc.iter():
        style = el.get("style") or ""
        if style and (
            RE_OUTLOOK_BORDER_STYLE.search(style)
            or RE_WINDOWS_MAIL_STYLE.search(style)
        ):
            _remove_element_and_following_siblings(el)
            return _tree_to_text(doc)

    # Method 3: OLK_SRC_BODY_SECTION — everything OUTSIDE this is the quote
    for el in doc.iter():
        if el.get("id") == OUTLOOK_OLK_ID:
            return el.text_content().strip()

    # Method 4: HR with tabindex="-1" (Outlook separator)
    for el in doc.iter("hr"):
        if el.get("tabindex") == "-1":
            parent = el.getparent()
            if parent is not None and parent.get("id") == OUTLOOK_RPLY_FWD_ID:
                continue  # Already handled above
            _remove_element_and_following_siblings(el)
            return _tree_to_text(doc)

    return None


def _try_cut_apple_mail(doc) -> Optional[str]:
    """Remove Apple Mail / Thunderbird blockquote type=cite."""
    for el in doc.iter("blockquote"):
        if el.get("type") == APPLE_BLOCKQUOTE_TYPE:
            _remove_element_and_following_siblings(el)
            return _tree_to_text(doc)
    return None


def _try_cut_protonmail(doc) -> Optional[str]:
    """Remove ProtonMail quote div."""
    for el in doc.cssselect(PROTONMAIL_QUOTE_SELECTOR):
        _remove_element_and_following_siblings(el)
        return _tree_to_text(doc)
    return None


def _try_cut_generic_blockquote(doc) -> Optional[str]:
    """Remove the last non-nested blockquote (generic fallback)."""
    blockquotes = doc.xpath(
        "(.//blockquote)[not(ancestor::blockquote)][last()]"
    )
    if blockquotes:
        bq = blockquotes[0]
        _remove_element_and_following_siblings(bq)
        return _tree_to_text(doc)
    return None


def parse_html(html_str: str) -> Optional[ParseResult]:
    """
    Layer 2: Parse HTML email body using provider-specific cuts.

    Tries each provider's known HTML patterns in order. Returns None
    if no quote structure is detected in the HTML.
    """
    if not html_str or not html_str.strip():
        return None

    if not HAS_LXML:
        # Can't do HTML parsing without lxml — fall through to text layer
        return None

    full_text = _strip_html_to_text(html_str)

    # Try each provider's cut in order (most specific first)
    cuts = [
        ("gmail", _try_cut_gmail),
        ("outlook", _try_cut_outlook),
        ("apple", _try_cut_apple_mail),
        ("protonmail", _try_cut_protonmail),
        ("blockquote", _try_cut_generic_blockquote),
    ]

    for name, cut_fn in cuts:
        try:
            doc = lxml_html.fromstring(html_str)
        except Exception:
            return None

        result = cut_fn(doc)
        if result is not None:
            reply = result.strip()
            quoted = ""
            if len(reply) < len(full_text):
                # Approximate the quoted portion
                idx = full_text.find(reply[:50]) if reply else -1
                if idx >= 0:
                    quoted = full_text[idx + len(reply) :].strip()
                else:
                    quoted = full_text[len(reply) :].strip()

            return ParseResult(
                reply=reply,
                quoted=quoted,
                method=ParseMethod.HTML_PROVIDER_CUT,
                confidence=0.85,
            )

    return None


# ---------------------------------------------------------------------------
# Layer 3: Plain-text heuristic parsing
# ---------------------------------------------------------------------------


def _classify_line(line: str) -> str:
    """Classify a single line. Returns a marker character."""
    stripped = line.strip()
    if not stripped:
        return "e"  # empty
    if RE_QUOTED_LINE.match(line):
        return "m"  # quoted marker
    if RE_FWD_MARKER.match(stripped):
        return "f"  # forwarded
    if RE_ORIGINAL_MESSAGE.match(stripped):
        return "s"  # splitter
    if RE_OUTLOOK_SEPARATOR.match(stripped):
        return "s"  # splitter
    return "t"  # text


def _find_splitter_position(lines: list[str]) -> Optional[int]:
    """
    Find the line index where quoted content begins.

    Tries multiple strategies in order of specificity.
    """
    # Strategy 1: "On ... wrote:" pattern (may span 2 lines)
    text = "\n".join(lines)
    m = RE_ON_WROTE.search(text)
    if m:
        # Find which line this match starts on
        pos = m.start()
        line_idx = text[:pos].count("\n")
        return line_idx

    # Strategy 2: "-----Original Message-----" and translations
    for i, line in enumerate(lines):
        if RE_ORIGINAL_MESSAGE.match(line.strip()):
            return i

    # Strategy 3: Outlook underscore separator
    for i, line in enumerate(lines):
        if RE_OUTLOOK_SEPARATOR.match(line.strip()):
            return i

    # Strategy 4: From:/Sent:/To:/Subject: header block
    m = RE_HEADER_BLOCK.search(text)
    if m:
        pos = m.start()
        line_idx = text[:pos].count("\n")
        # Only split here if it's in the bottom half of the email
        # (header blocks at the top are part of the original message)
        if line_idx > len(lines) * 0.3:
            return line_idx

    # Strategy 5: 3+ consecutive lines starting with >
    consecutive_quoted = 0
    for i, line in enumerate(lines):
        if RE_QUOTED_LINE.match(line):
            consecutive_quoted += 1
            if consecutive_quoted >= 3:
                return i - 2  # start of the quoted block
        else:
            consecutive_quoted = 0

    return None


def _find_signature_position(lines: list[str], split_at: Optional[int]) -> Optional[int]:
    """Find where a signature starts (searching from bottom up)."""
    # Only look in the reply portion (before the quote split)
    search_end = split_at if split_at is not None else len(lines)

    # Don't look in the first few lines (a signature won't be at the very top)
    search_start = max(0, search_end - 15)

    # Look for explicit signature delimiter "--"
    for i in range(search_end - 1, search_start - 1, -1):
        if RE_SIGNATURE_DELIMITER.match(lines[i]):
            return i

    # Look for "Sent from my..." patterns
    for i in range(search_end - 1, search_start - 1, -1):
        if RE_SENT_FROM.match(lines[i].strip()):
            return i

    # Look for closing phrases (Best regards, Thanks, etc.)
    # Only if it's in the last ~6 lines of the reply portion
    close_search_start = max(search_start, search_end - 6)
    for i in range(search_end - 1, close_search_start - 1, -1):
        if RE_CLOSING_PHRASES.match(lines[i].strip()):
            return i

    return None


def _find_disclaimer_position(lines: list[str], split_at: Optional[int]) -> Optional[int]:
    """Find where a disclaimer/legal notice starts."""
    search_end = split_at if split_at is not None else len(lines)
    text = "\n".join(lines[:search_end])
    m = RE_DISCLAIMER.search(text)
    if m:
        pos = m.start()
        return text[:pos].count("\n")
    return None


def parse_text(text: str) -> ParseResult:
    """
    Layer 3: Parse plain text email body using heuristics.

    This always returns a result (it's the fallback before "unparsed").
    """
    if not text or not text.strip():
        return ParseResult(
            reply="",
            quoted="",
            method=ParseMethod.TEXT_HEURISTIC,
            confidence=0.5,
        )

    lines = text.split("\n")

    # Find where quoted content starts
    split_at = _find_splitter_position(lines)

    # Find signature within the reply portion
    sig_at = _find_signature_position(lines, split_at)

    # Find disclaimer
    disc_at = _find_disclaimer_position(lines, split_at)

    # Determine the effective end of the reply
    reply_end = split_at or len(lines)
    if sig_at is not None and sig_at < reply_end:
        reply_end = sig_at
    if disc_at is not None and disc_at < reply_end:
        reply_end = disc_at

    reply_lines = lines[:reply_end]
    reply_text = "\n".join(reply_lines).strip()

    # Everything after the reply is quoted
    quoted_text = ""
    if split_at is not None:
        quoted_text = "\n".join(lines[split_at:]).strip()

    # Extract signature if found
    signature = None
    if sig_at is not None:
        sig_end = split_at or len(lines)
        signature = "\n".join(lines[sig_at:sig_end]).strip()

    # Extract disclaimer if found
    disclaimer = None
    if disc_at is not None:
        disc_end = sig_at or split_at or len(lines)
        disclaimer = "\n".join(lines[disc_at:disc_end]).strip()

    confidence = 0.75 if split_at is not None else 0.5

    return ParseResult(
        reply=reply_text,
        quoted=quoted_text,
        method=ParseMethod.TEXT_HEURISTIC,
        confidence=confidence,
        signature=signature,
        disclaimer=disclaimer,
    )


# ---------------------------------------------------------------------------
# Main entry point: layered parsing
# ---------------------------------------------------------------------------


def parse_reply(
    html: Optional[str] = None,
    text: Optional[str] = None,
    unique_body: Optional[str] = None,
    full_body: Optional[str] = None,
) -> ParseResult:
    """
    Extract the reply content from an email, using a layered approach.

    Args:
        html: The HTML body of the email (if available)
        text: The plain text body of the email (if available)
        unique_body: Microsoft Graph uniqueBody value (if available)
        full_body: The full body for comparison with uniqueBody

    Returns:
        ParseResult with the extracted reply, quoted content, and metadata
    """
    # Layer 1: Microsoft Graph uniqueBody
    if unique_body is not None:
        result = parse_with_unique_body(unique_body, full_body)
        if result is not None and not result.is_empty:
            return result

    # Layer 2: HTML-aware parsing
    if html:
        result = parse_html(html)
        if result is not None and not result.is_empty:
            # Also try to find signature/disclaimer in the extracted text
            text_result = parse_text(result.reply)
            if text_result.signature:
                # Re-extract without signature
                clean_reply = result.reply
                sig_idx = clean_reply.rfind(text_result.signature)
                if sig_idx > 0:
                    clean_reply = clean_reply[:sig_idx].strip()
                return ParseResult(
                    reply=clean_reply,
                    quoted=result.quoted,
                    method=result.method,
                    confidence=result.confidence,
                    signature=text_result.signature,
                    disclaimer=text_result.disclaimer,
                )
            return result

    # Layer 3: Plain-text heuristic parsing
    plain = text or (html and _strip_html_to_text(html)) or ""
    if plain.strip():
        return parse_text(plain)

    # Layer 4: Unparsed fallback
    body = html or text or ""
    return ParseResult(
        reply=_strip_html_to_text(body) if html and not text else body,
        quoted="",
        method=ParseMethod.UNPARSED,
        confidence=0.0,
    )
