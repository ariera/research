# Email Reply/Quote Parser Research Notes

## Investigation Process

1. Searched for GitHub repos for all three libraries:
   - talon: https://github.com/mailgun/talon
   - mail-parser-reply: https://github.com/alfonsrv/mail-parser-reply
   - quotequail: https://github.com/closeio/quotequail

2. Cloned all three repos to /tmp and read their source code directly.

3. Also investigated `superops-talon` on PyPI - it's a fork of talon 1.6.0 by Superops that adds "new html xPaths expressions on filtering reply messages" but doesn't document what those XPaths are. The core algorithm is the same as mailgun/talon.

## Key files read:
- talon: `quotations.py`, `html_quotations.py`, `utils.py`, `constants.py`
- mail-parser-reply: `mailparser_reply/constants.py`, `mailparser_reply/parser.py`
- quotequail: `__init__.py`, `_patterns.py`, `_internal.py`, `_html.py`, `_enums.py`

## Interesting findings:
- talon uses a marker-based line classification system (e/m/s/t/f markers) followed by regex matching on the marker string itself
- talon's HTML approach inserts checkpoint strings into the DOM, converts to text, runs the text algo, then maps deleted checkpoints back to remove DOM nodes
- mail-parser-reply is much simpler - just regex-finds headers and splits text at those positions
- quotequail has the most careful HTML line extraction (tree_line_generator) and handles blockquote indentation levels
- quotequail's Outlook detection is limited to the FORWARD_STYLES list which only checks border-top style patterns
- All three libraries share similar "On ... wrote:" patterns but with different language coverage
