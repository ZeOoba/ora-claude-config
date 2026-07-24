#!/usr/bin/env python3
"""Canonical credential-shape patterns for ~/.claude -- ONE source, three consumers.

WHY THIS EXISTS (Gabriel ruling, 2026-07-24): three tools needed "does this text contain a
credential" and two of them had independently hand-maintained lists that had already
diverged -- setup-self-audit.py carried 5 patterns, scrub-before-optin.py carried 8, and
NEITHER was a superset of the other. That is the same duplication failure
scrub-before-optin's own docstring warns about for confidential-term matching, which it
solved by importing doctrine-integrity-probe's matcher instead of copying it. This module
does the same for secrets.

Consumers:
  * hooks/git-prepush-confidential-scan.py -- BLOCKS a push carrying a credential
    (the exfiltration boundary: ~/.claude pushes to ZeOoba/ora-claude-config)
  * maintenance/setup-self-audit.py        -- daily detection
  * maintenance/scrub-before-optin.py      -- pre-opt-in check

PATTERNS ARE A UNION, not either prior list. Taking scrub's 8 alone would have silently
WEAKENED the daily scan by dropping shapes only setup-self-audit carried:
  - `ak_...`  Composio key shape (connector retired 2026-06-11; the shape still guards
    historical copies -- a rotated-away key sitting in an old file is still a leak to scrub)
  - bare `SECRET` / `TOKEN` assignments (scrub covered only api_key/apikey)
`x-api-key:` needs no separate pattern: the `-` before `api` is a word boundary, so scrub's
api[_-]?key alternation already matches inside it -- verified, not assumed.

REPORTING RULE: callers get labels, NEVER the matched text. A scanner that echoes the
secret it found has leaked it into a log, an email, or a terminal transcript.
"""
import os
import re

# (label, compiled regex). Order is stable -- some callers report by index.
SECRET_PATTERNS = [
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{8,}")),
    ("Composio-style key", re.compile(r"\bak_[A-Za-z0-9]{12,}")),
    ("AWS access key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("generic API key assignment",
     re.compile(r"(?i)\b(?:api[_-]?key|apikey)\b\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{16,}")),
    ("secret/token assignment",
     re.compile(r"(?i)\b(?:FRED_API_KEY|SECRET|TOKEN)\b\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{12,}")),
    ("generic bearer token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}")),
    ("password assignment",
     re.compile(r"(?i)\bpassword\b\s*[:=]\s*[\"']?[^\s\"']{6,}")),
    ("PEM private-key block",
     re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
]

# Paths whose credential-SHAPED strings are fixtures or documentation, never live keys.
# Kept deliberately narrow: EVERY entry here is a hole in a security gate, so it must be a
# path class that cannot hold a real credential by construction.
#   * test fixtures -- a scanner's own test corpus necessarily contains fake keys. Without
#     this the pre-push gate blocks EVERY push, because maintenance/test-scrub-before-
#     optin.py is itself tracked (measured 2026-07-24: the ONLY hit across all 628 tracked
#     files, and it is that fixture).
#   * mcp-builder reference docs -- carry example "x-api-key:" strings.
EXEMPT_PATH_PARTS = (
    "/tests/",
    "/_tests/",
    "mcp-builder",
    "/reference/",
    "evaluation.md",
)
EXEMPT_BASENAME_RE = re.compile(r"(^test[-_]|[-_]test\.py$|^test_)", re.I)

# The LEGITIMATE homes for a live MCP key -- a key here is configuration, not a leak.
LEGIT_KEY_HOMES = frozenset({"claude_desktop_config.json", ".claude.json"})


def is_exempt_path(path):
    """True if credential-shaped text at `path` is a fixture/doc, not a leak."""
    low = str(path).replace("\\", "/").lower()
    if any(part in low for part in EXEMPT_PATH_PARTS):
        return True
    return bool(EXEMPT_BASENAME_RE.search(os.path.basename(low)))


# `password assignment` is by far the loosest pattern here -- its value side is
# [^\s"']{6,}, i.e. any 6+ non-space characters -- so it fires on documentation. Measured
# 2026-07-24: 2 of the daily scan's 3 findings were the stock `pdf` skill's own docs
# (`qpdf --password=secret123 --decrypt`). A daily CRIT that is always the same two doc
# lines is alarm fatigue, and alarm fatigue is how the real third finding gets ignored.
#
# Suppress ONLY well-known example values and obvious placeholder shapes. This is a
# precision/recall trade made deliberately and narrowly: anything not on this list still
# fires, so a real password is unaffected. Never add a value here that could be real.
_PLACEHOLDER_VALUES = frozenset({
    "password", "secret123", "mypassword", "yourpassword", "yourpasswordhere",
    "changeme", "hunter2", "placeholder", "example", "topsecret", "letmein",
    "password123", "s3cret", "notarealpassword",
})
# ALL-CAPS / bracketed / templated placeholders: PASSWORD, YOUR_PASSWORD, <password>,
# {{password}}, ${PASSWORD}, ****** .
_PLACEHOLDER_SHAPE_RE = re.compile(
    r"^(?:[A-Z][A-Z0-9_]{4,}|[<{\[$].*|\*+|x{6,}|\.{3,})$")
_PASSWORD_VALUE_RE = re.compile(r"(?i)\bpassword\b\s*[:=]\s*[\"']?([^\s\"']{6,})")


def _is_placeholder(value):
    v = value.strip().strip("\"'`,;)")
    return (v.lower() in _PLACEHOLDER_VALUES) or bool(_PLACEHOLDER_SHAPE_RE.match(v))


def scan_text(text):
    """Sorted, de-duplicated labels of patterns present in `text`.

    Labels only -- never the matched substring (see REPORTING RULE above).
    """
    found = set()
    for label, rx in SECRET_PATTERNS:
        if not rx.search(text):
            continue
        if label == "password assignment":
            # report only if at least one assigned value is not a documented placeholder
            vals = _PASSWORD_VALUE_RE.findall(text)
            if vals and all(_is_placeholder(v) for v in vals):
                continue
        found.add(label)
    return sorted(found)


# A `git log -p` body concatenates every file, which destroys the file attribution that
# is_exempt_path() needs -- scanning it as one blob makes the gate unusable, because a test
# fixture anywhere in the pushed history would block every push forever. Splitting on the
# diff header restores per-file attribution.
_DIFF_HEADER_RE = re.compile(r"^diff --git a/(.+?) b/(.+?)$", re.M)


def scan_diff(diff_text):
    """Scan a `git log -p` body per file. Returns [(path, [labels]), ...]; exempt paths
    are dropped. Text before the first `diff --git` header (commit messages) is attributed
    to a synthetic '<commit-message>' path and IS scanned -- a key pasted into a commit
    message is pushed just the same, and has no path to exempt it."""
    out = []
    marks = list(_DIFF_HEADER_RE.finditer(diff_text))
    if not marks:
        labels = scan_text(diff_text)
        return [("<commit-message>", labels)] if labels else []

    labels = scan_text(diff_text[: marks[0].start()])
    if labels:
        out.append(("<commit-message>", labels))

    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(diff_text)
        path = m.group(2)  # b/<path> -- the post-image name
        if is_exempt_path(path):
            continue
        labels = scan_text(diff_text[m.start():end])
        if labels:
            out.append((path, labels))
    return out
