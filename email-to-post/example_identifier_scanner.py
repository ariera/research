"""
Identifier Scanner: Extract structured IDs from freeform emails

Scans a shared M365 mailbox for emails containing an identifier matching
a pattern like "1234-2026" (up to 4 digits, dash, 4-digit year).

The identifier could appear anywhere: subject, body, signature, forwarded
content. The scanner extracts candidates, ranks them by location, and
matches against a database.

Install: pip install msal imap-tools
"""

import re
import logging
from dataclasses import dataclass, field
from email.utils import parseaddr
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Identifier pattern
# ---------------------------------------------------------------------------

# Core pattern: 1-4 digits, dash, 4-digit year
# Flexible: allows optional leading # or "ref" prefix, slash instead of dash
IDENTIFIER_PATTERN = re.compile(
    r"""
    (?:^|(?<=[\s(#:]))       # preceded by whitespace, (, #, :, or start of string
    (\d{1,4})                 # 1-4 digits (capture group 1)
    [-/]                      # dash or slash separator
    (20\d{2})                 # 4-digit year starting with 20 (capture group 2)
    (?=$|[\s).,;!?])          # followed by whitespace, punctuation, or end of string
    """,
    re.VERBOSE,
)


@dataclass
class IdentifierMatch:
    """A candidate identifier found in an email."""

    raw: str  # the matched text, e.g. "1234-2026"
    normalized: str  # canonical form, e.g. "1234-2026"
    location: str  # "subject", "body", "html", "attachment_filename"
    confidence: float  # 0.0 - 1.0

    @property
    def number(self) -> int:
        return int(self.normalized.split("-")[0])

    @property
    def year(self) -> int:
        return int(self.normalized.split("-")[1])


@dataclass
class ScanResult:
    """Result of scanning one email."""

    message_id: str
    from_address: str
    subject: str
    matches: list[IdentifierMatch] = field(default_factory=list)

    @property
    def best_match(self) -> Optional[IdentifierMatch]:
        """Highest-confidence match, or None."""
        if not self.matches:
            return None
        return max(self.matches, key=lambda m: m.confidence)

    @property
    def has_identifier(self) -> bool:
        return len(self.matches) > 0


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

def strip_html_tags(html: str) -> str:
    """Rough HTML tag strip. Not for sanitization — just for text extraction."""
    import re as _re
    text = _re.sub(r"<style[^>]*>.*?</style>", "", html, flags=_re.DOTALL | _re.IGNORECASE)
    text = _re.sub(r"<script[^>]*>.*?</script>", "", text, flags=_re.DOTALL | _re.IGNORECASE)
    text = _re.sub(r"<[^>]+>", " ", text)
    text = _re.sub(r"&nbsp;", " ", text)
    text = _re.sub(r"&[a-zA-Z]+;", "", text)
    text = _re.sub(r"\s+", " ", text)
    return text.strip()


def extract_identifiers(text: str, location: str) -> list[IdentifierMatch]:
    """Find all identifier-pattern matches in a text string."""
    matches = []
    seen = set()

    for m in IDENTIFIER_PATTERN.finditer(text):
        number_part = m.group(1)
        year_part = m.group(2)
        raw = m.group(0)
        normalized = f"{number_part}-{year_part}"

        if normalized in seen:
            continue
        seen.add(normalized)

        # Confidence based on location
        confidence_by_location = {
            "subject": 0.95,
            "body": 0.80,
            "html": 0.60,
            "attachment_filename": 0.50,
        }
        confidence = confidence_by_location.get(location, 0.40)

        matches.append(IdentifierMatch(
            raw=raw,
            normalized=normalized,
            location=location,
            confidence=confidence,
        ))

    return matches


# ---------------------------------------------------------------------------
# Email scanner
# ---------------------------------------------------------------------------

def scan_email(msg) -> ScanResult:
    """
    Scan an imap_tools MailMessage for identifiers.

    Checks subject, plain text body, HTML body, and attachment filenames.
    Returns a ScanResult with all matches ranked by confidence.

    Args:
        msg: an imap_tools MailMessage (from mailbox.fetch())
    """
    result = ScanResult(
        message_id=msg.uid or "",
        from_address=msg.from_ or "",
        subject=msg.subject or "",
    )

    # 1. Subject line (highest confidence)
    if msg.subject:
        result.matches.extend(extract_identifiers(msg.subject, "subject"))

    # 2. Plain text body
    if msg.text:
        result.matches.extend(extract_identifiers(msg.text, "body"))

    # 3. HTML body (lower confidence — might be in boilerplate)
    if msg.html and not msg.text:
        # Only fall back to HTML if no plain text
        plain_from_html = strip_html_tags(msg.html)
        result.matches.extend(extract_identifiers(plain_from_html, "html"))

    # 4. Attachment filenames
    for att in msg.attachments:
        if att.filename:
            result.matches.extend(
                extract_identifiers(att.filename, "attachment_filename")
            )

    # Deduplicate: if the same normalized ID was found in multiple locations,
    # keep the highest-confidence one
    best_per_id: dict[str, IdentifierMatch] = {}
    for match in result.matches:
        existing = best_per_id.get(match.normalized)
        if existing is None or match.confidence > existing.confidence:
            best_per_id[match.normalized] = match
    result.matches = list(best_per_id.values())

    return result


# ---------------------------------------------------------------------------
# Database matching stub
# ---------------------------------------------------------------------------

def lookup_identifier(normalized_id: str) -> Optional[dict]:
    """
    Look up an identifier in the database.

    Replace this stub with your actual database query.
    Returns the matching record dict, or None if not found.
    """
    # Example: SELECT * FROM records WHERE identifier = %s
    log.info("Database lookup for identifier: %s", normalized_id)
    # return db.query("SELECT * FROM records WHERE identifier = ?", normalized_id)
    return None  # stub


# ---------------------------------------------------------------------------
# Processing pipeline
# ---------------------------------------------------------------------------

def process_email(msg) -> None:
    """
    Full pipeline: scan email for identifiers, look up in database, act.

    This is the handler function you'd pass to the IMAP poller or Graph poller.
    """
    result = scan_email(msg)

    if not result.has_identifier:
        log.debug(
            "No identifier found in email from=%s subject=%r — skipping",
            result.from_address,
            result.subject,
        )
        return

    best = result.best_match
    log.info(
        "Found identifier %s (confidence=%.2f, location=%s) in email from=%s subject=%r",
        best.normalized,
        best.confidence,
        best.location,
        result.from_address,
        result.subject,
    )

    # Look up in database
    record = lookup_identifier(best.normalized)
    if record is None:
        log.warning(
            "Identifier %s not found in database — flagging for review",
            best.normalized,
        )
        # TODO: send to a review queue, notify someone, etc.
        return

    # Identifier found and matched — do something with it
    log.info("Matched record: %s", record)
    # TODO: ingest email content, update record, trigger workflow, etc.

    # If there were multiple identifiers, log them
    if len(result.matches) > 1:
        others = [m.normalized for m in result.matches if m.normalized != best.normalized]
        log.info("Additional identifiers found (not processed): %s", others)


# ---------------------------------------------------------------------------
# Integration with the IMAP poller
# ---------------------------------------------------------------------------

def main():
    """
    Example: wire the identifier scanner to the M365 IMAP poller.
    """
    import msal
    from imap_tools import MailBox, AND

    TENANT_ID = "YOUR_TENANT_ID"
    CLIENT_ID = "YOUR_CLIENT_ID"
    CLIENT_SECRET = "YOUR_CLIENT_SECRET"
    MAILBOX = "shared-inbox@contoso.com"

    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        client_credential=CLIENT_SECRET,
    )

    def get_token():
        result = app.acquire_token_for_client(
            scopes=["https://outlook.office365.com/.default"]
        )
        return result["access_token"]

    # Poll loop
    import time

    while True:
        try:
            token = get_token()
            with MailBox("outlook.office365.com").xoauth2(
                MAILBOX, token, initial_folder="INBOX"
            ) as mailbox:
                for msg in mailbox.fetch(AND(seen=False), limit=50):
                    process_email(msg)
        except KeyboardInterrupt:
            break
        except Exception:
            log.exception("Poll cycle failed; retrying in 60s")

        time.sleep(60)


if __name__ == "__main__":
    main()
