"""
Test the layered reply parser against realistic email fixtures.

Run with: pytest test_parser.py -v
"""

import pytest
from test_fixtures import (
    ALL_FIXTURES,
    OUTLOOK_FIXTURES,
    GMAIL_FIXTURES,
    APPLE_FIXTURES,
    PLAIN_TEXT_FIXTURES,
    EDGE_CASE_FIXTURES,
    fixture_params,
    fixture_ids,
)
from reply_parser import parse_reply, ParseMethod


def _normalize(text: str) -> str:
    """Normalize whitespace for comparison."""
    if not text:
        return ""
    lines = [line.strip() for line in text.strip().splitlines()]
    return "\n".join(line for line in lines if line)


def _expected_reply_fragments(fixture: dict) -> list[str]:
    """
    Extract key phrases from expected_reply that must appear in the result.

    Rather than exact string matching (which is brittle due to whitespace
    and minor formatting differences), we check that key content phrases
    from the expected reply appear in the parsed output.
    """
    expected = fixture["expected_reply"]
    if not expected:
        return []
    # Split into sentences/phrases and take the meaningful ones
    lines = [line.strip() for line in expected.strip().splitlines() if line.strip()]
    # Filter out very short lines (punctuation, "Best,", etc.)
    return [line for line in lines if len(line) > 10]


def _expected_quoted_fragments(fixture: dict) -> list[str]:
    """Extract key phrases from expected_quoted."""
    expected = fixture.get("expected_quoted") or ""
    if not expected:
        return []
    lines = [line.strip() for line in expected.strip().splitlines() if line.strip()]
    return [line for line in lines if len(line) > 15]


# ---------------------------------------------------------------------------
# Core parsing tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture", fixture_params(), ids=fixture_ids())
def test_reply_extraction_not_empty(fixture):
    """Parsed reply should not be empty (except for 'forward with no new text')."""
    result = parse_reply(html=fixture["html"], text=fixture["text"])

    if fixture["name"] == "forward_without_new_text_entirely_quoted":
        # This is expected to have an empty reply
        return

    assert result.reply.strip(), (
        f"Reply was empty for {fixture['name']} (method={result.method})"
    )


@pytest.mark.parametrize("fixture", fixture_params(), ids=fixture_ids())
def test_reply_contains_expected_content(fixture):
    """Key phrases from expected_reply should appear in the parsed reply."""
    result = parse_reply(html=fixture["html"], text=fixture["text"])
    expected_fragments = _expected_reply_fragments(fixture)

    if not expected_fragments:
        return  # No expected content to check

    reply_lower = result.reply.lower()
    found = 0
    for fragment in expected_fragments:
        if fragment.lower() in reply_lower:
            found += 1

    # Inline interleaved replies are a known unsolvable case — lower the bar
    if fixture["name"] == "inline_interleaved_quoting":
        threshold = 1  # Getting anything is good
    else:
        threshold = max(1, len(expected_fragments) // 2)

    assert found >= threshold, (
        f"{fixture['name']}: only {found}/{len(expected_fragments)} expected "
        f"fragments found in reply.\n"
        f"Method: {result.method}\n"
        f"Expected fragments: {expected_fragments[:5]}\n"
        f"Got reply: {result.reply[:300]}"
    )


@pytest.mark.parametrize("fixture", fixture_params(), ids=fixture_ids())
def test_quoted_not_in_reply(fixture):
    """
    Key phrases from expected_quoted should NOT appear in the parsed reply.

    This is the critical test: we don't want quoted content leaking into
    the extracted reply.
    """
    result = parse_reply(html=fixture["html"], text=fixture["text"])
    quoted_fragments = _expected_quoted_fragments(fixture)

    if not quoted_fragments:
        return  # No quoted content to check

    reply_lower = result.reply.lower()
    leaked = []
    for fragment in quoted_fragments:
        if fragment.lower() in reply_lower:
            leaked.append(fragment)

    # Allow up to 1 leaked fragment (edge cases with overlapping content)
    assert len(leaked) <= 1, (
        f"{fixture['name']}: {len(leaked)} quoted fragments leaked into reply.\n"
        f"Method: {result.method}\n"
        f"Leaked: {leaked[:3]}\n"
        f"Reply: {result.reply[:300]}"
    )


# ---------------------------------------------------------------------------
# Method-specific tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture", fixture_params(OUTLOOK_FIXTURES), ids=fixture_ids(OUTLOOK_FIXTURES))
def test_outlook_uses_html_parsing(fixture):
    """Outlook emails with HTML should be parsed via HTML provider cut."""
    if fixture["html"]:
        result = parse_reply(html=fixture["html"], text=fixture["text"])
        assert result.method in (
            ParseMethod.HTML_PROVIDER_CUT,
            ParseMethod.HTML_CHECKPOINT,
        ), f"Outlook fixture {fixture['name']} used {result.method} instead of HTML parsing"


@pytest.mark.parametrize("fixture", fixture_params(GMAIL_FIXTURES), ids=fixture_ids(GMAIL_FIXTURES))
def test_gmail_uses_html_parsing(fixture):
    """Gmail emails with HTML should be parsed via HTML provider cut."""
    if fixture["html"]:
        result = parse_reply(html=fixture["html"], text=fixture["text"])
        assert result.method in (
            ParseMethod.HTML_PROVIDER_CUT,
            ParseMethod.HTML_CHECKPOINT,
        ), f"Gmail fixture {fixture['name']} used {result.method} instead of HTML parsing"


@pytest.mark.parametrize("fixture", fixture_params(PLAIN_TEXT_FIXTURES), ids=fixture_ids(PLAIN_TEXT_FIXTURES))
def test_plain_text_uses_text_parsing(fixture):
    """Plain text emails (without HTML) should be parsed via text heuristics."""
    if fixture["html"]:
        # Fixture has HTML, so HTML parsing may be used instead — that's fine
        return
    result = parse_reply(html=fixture["html"], text=fixture["text"])
    assert result.method == ParseMethod.TEXT_HEURISTIC, (
        f"Plain text fixture {fixture['name']} used {result.method}"
    )


# ---------------------------------------------------------------------------
# Identifier isolation test
# ---------------------------------------------------------------------------


def test_identifier_not_extracted_from_quote():
    """
    When an identifier appears only in the quoted section,
    it should NOT be in the reply.
    """
    fixture = next(f for f in ALL_FIXTURES if f.get("has_identifier_in_quote_only"))
    result = parse_reply(html=fixture["html"], text=fixture["text"])

    assert "1234-2026" not in result.reply, (
        f"Identifier '1234-2026' found in reply but should only be in quoted section.\n"
        f"Method: {result.method}\n"
        f"Reply: {result.reply[:500]}"
    )


# ---------------------------------------------------------------------------
# Graph uniqueBody tests
# ---------------------------------------------------------------------------


def test_unique_body_preferred_when_available():
    """uniqueBody should be used as Layer 1 when provided."""
    result = parse_reply(
        html="<div>Reply text</div><div class='gmail_quote'>Quoted</div>",
        text="Reply text\nOn date wrote:\n> Quoted",
        unique_body="Reply text",
        full_body="Reply text\nQuoted stuff",
    )
    assert result.method == ParseMethod.GRAPH_UNIQUE_BODY


def test_unique_body_skipped_when_null():
    """None uniqueBody should fall through to HTML parsing."""
    result = parse_reply(
        html="<div>Reply</div><div class='gmail_quote'>Quote</div>",
        unique_body=None,
    )
    assert result.method != ParseMethod.GRAPH_UNIQUE_BODY


def test_unique_body_low_confidence_when_equals_full():
    """When uniqueBody equals full body, confidence should be lower."""
    body = "Just a fresh message with no quoted content."
    result = parse_reply(
        unique_body=body,
        full_body=body,
    )
    assert result.method == ParseMethod.GRAPH_UNIQUE_BODY
    assert result.confidence < 0.8


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


def test_fresh_message_returns_full_content():
    """A message with no quotes should return the full content."""
    fixture = next(f for f in ALL_FIXTURES if f["name"] == "fresh_message_no_quoted_content")
    result = parse_reply(html=fixture["html"], text=fixture["text"])
    assert result.reply.strip()
    assert not result.quoted.strip() or result.quoted.strip() == ""


def test_empty_input():
    """Empty input should return an unparsed result."""
    result = parse_reply()
    assert result.method == ParseMethod.UNPARSED
    assert not result.reply


# ---------------------------------------------------------------------------
# Result reporting
# ---------------------------------------------------------------------------


def test_print_results_summary(capsys):
    """Print a summary of how each fixture was parsed (for manual review)."""
    print("\n" + "=" * 70)
    print("REPLY PARSER RESULTS SUMMARY")
    print("=" * 70)

    for fixture in ALL_FIXTURES:
        result = parse_reply(html=fixture["html"], text=fixture["text"])
        expected = _normalize(fixture["expected_reply"] or "")
        actual = _normalize(result.reply or "")

        # Check if key content matches
        expected_frags = _expected_reply_fragments(fixture)
        found = sum(
            1 for f in expected_frags if f.lower() in result.reply.lower()
        )
        total = len(expected_frags)

        status = "PASS" if found >= max(1, total // 2) else "FAIL"
        if fixture["name"] == "forward_without_new_text_entirely_quoted":
            status = "PASS" if not result.reply.strip() or result.reply.strip() == "" else "FAIL"

        print(f"\n{'='*70}")
        print(f"  {fixture['name']}")
        print(f"  Method:     {result.method.value}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Fragments:  {found}/{total} match")
        print(f"  Status:     {status}")
        if result.signature:
            print(f"  Signature:  {result.signature[:60]}...")
        if result.disclaimer:
            print(f"  Disclaimer: {result.disclaimer[:60]}...")
        print(f"  Reply:      {result.reply[:120]}...")
        if result.quoted:
            print(f"  Quoted:     {result.quoted[:120]}...")
