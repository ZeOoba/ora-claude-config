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
    ("Netlify token", re.compile(r"\bnfp_[A-Za-z0-9]{20,}\b")),
    # 2026-07-30 GAP FIX (credential-exposure sweep). The prior pattern was
    #   \b(?:FRED_API_KEY|SECRET|TOKEN)\b
    # and `_` is a WORD character, so no \b exists before TOKEN in NETLIFY_AUTH_TOKEN --
    # the boundary silently required the keyword to stand alone. Measured: 10 of 12
    # realistic shapes evaded EVERY pattern in this module, including every secret name in
    # ORA's own stack (tech.md 7). Live proof: the archived oxfordra-net repo's commit
    # 4b7a3bb carries NETLIFY_AUTH_TOKEN = nfp_..., and a whole-history scan using this
    # module returned CLEAN -- the pre-push exfiltration gate was blind to it.
    # The name side now allows an optional UPPER_SNAKE prefix (NETLIFY_AUTH_, STRIPE_,
    # SUPABASE_SERVICE_ROLE_) and an optional lower_snake prefix for the common
    # access_/refresh_/auth_/client_ forms. Value side unchanged at 12+ chars; the
    # placeholder/env-reference suppressor below keeps the widening from adding noise.
    # Both EDGES need the same treatment: `_` is a word char, so \b fails before the
    # keyword (NETLIFY_AUTH_TOKEN) AND after it (STRIPE_SECRET_KEY -- SECRET is followed
    # by _KEY). Optional UPPER_SNAKE prefix AND suffix. The explicit KEY-ending names are
    # curated: bare `*_KEY` is DELIBERATELY EXCLUDED because the 2026-07-30 sweep measured
    # it firing on localStorage keys (STORAGE_KEY/SESSION_KEY/HISTORY_KEY in chat.js) --
    # a precision trade, documented, not an oversight.
    ("secret/token assignment",
     re.compile(r"(?i)\b(?:[A-Z][A-Z0-9]*_)*"
                r"(?:FRED_API_KEY|SECRET|TOKEN|PASSWD"
                r"|SERVICE_ROLE_KEY|ANON_KEY|PRIVATE_KEY|ACCESS_KEY"
                r"|SIGNING_KEY|ENCRYPTION_KEY|AUTH_KEY|MASTER_KEY)"
                r"(?:_[A-Z0-9]+)*\b"
                r"\s*[:=]\s*[\"']?[A-Za-z0-9_\-\.]{12,}")),
    ("secret/token assignment",
     re.compile(r"(?i)\b(?:access|refresh|auth|session|client|private|bearer)_"
                r"(?:token|secret|key)\b\s*[:=]\s*[\"']?[A-Za-z0-9_\-\.]{12,}")),
    ("generic API key assignment",
     re.compile(r"(?i)\b(?:[A-Z][A-Z0-9]*_)+API[_-]?KEY\b"
                r"\s*[:=]\s*[\"']?[A-Za-z0-9_\-\.]{12,}")),
    ("generic bearer token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}")),
    ("password assignment",
     re.compile(r"(?i)\bpassword\b\s*[:=]\s*[\"']?[^\s\"']{6,}")),
    ("PEM private-key block",
     re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    # 2026-11-08 audit finding secret-patterns-missing-stack-token-prefixes: prefixed
    # tokens ORA's own stack issues (tech.md 7) that no rule above matched. APPENDED, never
    # inserted -- callers report by index. Value sides are length-bound so prose and short
    # identifiers (`secret_sauce`, `ntn_notes`, `pat-na1-portal`) never fire.
    #   github_pat_  GitHub fine-grained PAT ([A-Za-z0-9_], ~82 chars after the prefix)
    #   ntn_         Notion integration token (current issuance)
    #   secret_      Notion legacy integration token (43 alnum) -- bound at 43+ so the
    #                common `secret_<word>` identifier stays quiet
    #   pat-<rgn>N-  HubSpot private-app token (region tag + UUID)
    #   sbp_         Supabase personal access token (40 hex)
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}")),
    ("Notion token", re.compile(r"\bntn_[A-Za-z0-9]{30,}\b")),
    ("Notion token", re.compile(r"\bsecret_[A-Za-z0-9]{43,}\b")),
    ("HubSpot private app token",
     re.compile(r"(?i)\bpat-[a-z]{2}[0-9]-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}"
                r"-[0-9a-f]{12}\b")),
    ("Supabase access token", re.compile(r"\bsbp_(?:v\d+_)?[A-Za-z0-9]{32,}\b")),
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
    """True if credential-shaped text at `path` is a fixture/doc, not a leak.

    The path is normalized to a LEADING SLASH before the substring test (2026-07-30,
    REFUTE pass 2): the "/tests/" entry requires one, so a repo-RELATIVE path such as
    `tests/unit/x.test.ts` was not exempt while `src/tests/x.ts` was -- 12 of 13
    newly-flagged files in the ora-pm / oxford-command-center differential were exactly
    the test fixtures this exemption exists for."""
    low = str(path).replace("\\", "/").lower()
    if not low.startswith("/"):
        low = "/" + low
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
# 2026-08-03: the ALL-CAPS branch is now DIGIT-FREE. It previously allowed [A-Z0-9_], so a
# genuine SHOUTED password carrying digits was suppressed as a placeholder (see the
# regression tests for the shapes -- deliberately not restated here, because a live
# example in this comment is itself credential-shaped and would make the module
# unpushable through its own gate, the F4 defect from the 2026-07-30 REFUTE round)
# -- the same entropy-swallowing bug the 2026-07-30 word-form fix addressed,
# but this older shape regex (2026-07-24) was never given the same gate. Found by the
# REFUTE pass on the scrub routing change. Real placeholders (PASSWORD, YOUR_PASSWORD,
# CHANGEME) carry no digits, so the gate costs no suppression we want; digit-bearing
# ALL-CAPS values now fire. The bracketed/starred/x-run/dotted branches are unchanged --
# they carry no entropy by construction.
_PLACEHOLDER_SHAPE_RE = re.compile(
    r"^(?:[A-Z][A-Z_]{4,}|[<{\[$].*|\*+|x{6,}|\.{3,})$")
_PASSWORD_VALUE_RE = re.compile(r"(?i)\bpassword\b\s*[:=]\s*[\"']?([^\s\"']{6,})")


def _is_placeholder(value):
    v = value.strip().strip("\"'`,;)")
    return (v.lower() in _PLACEHOLDER_VALUES) or bool(_PLACEHOLDER_SHAPE_RE.match(v))


# --- 2026-07-30: reference / placeholder suppressor for the WIDENED name matcher -------
# Widening the name side (NETLIFY_AUTH_TOKEN, SUPABASE_SERVICE_ROLE_KEY, access_token...)
# also makes ordinary CODE match: `process.env.GITHUB_TOKEN`, `os.environ["CRON_SECRET"]`,
# `NETLIFY_AUTH_TOKEN = "${NETLIFY_AUTH_TOKEN}"`. Those are REFERENCES, not credentials.
# Per the 2026-07-24 alarm-fatigue ruling, precision here protects the gate's usefulness.
# DELIBERATELY NARROW -- each entry is a construct that cannot itself BE a secret:
#   * an env/config LOOKUP on the value side  * a template/interpolation placeholder
#   * an obvious YOUR_/EXAMPLE/CHANGEME literal
# A real 12+ char literal still fires. Suppression is a false NEGATIVE, so nothing here
# may match a value that could be genuine.
# Split a single NAME<sep>VALUE match into its value side. Per-match, so no greedy
# capture across a following assignment (a REFUTED design, 2026-07-30).
_SEP_SPLIT_RE = re.compile(r"[:=]")


def _match_value(matched_text):
    parts = _SEP_SPLIT_RE.split(matched_text, maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""
_REFERENCE_VALUE_RE = re.compile(
    r"""(?ix)^\s*["']?(?:
          (?:process\.)?env(?:iron)?[\.\[\(]      # process.env.X / environ["X"] / env(
        | os\.environ | os\.getenv | getenv
        | Deno\.env | import\.meta\.env
        | \$\{ | \{\{ | %\( | <%                  # template interpolation
        | \$env: | \$Env:                          # PowerShell
        | Get-Item\s+env: | \[Environment\]::
        | secrets\. | vars\.                       # GH Actions
    )""")
# ANCHORED and case-SENSITIVE for the word forms (REFUTE finding 3, 2026-07-30): the
# earlier unanchored (?i) version suppressed any value merely BEGINNING with
# your/sample/todo/fake/redacted -- including quoted 14+ char high-entropy values, 6
# proven false negatives. A placeholder must now be essentially the WHOLE value, and the
# word forms must be SHOUTED (real keys are mixed-case/lowercase; template placeholders
# are conventionally upper). Bracketed/starred/dotted forms stay case-agnostic.
# WORD-FORM branch is additionally gated DIGIT-FREE (REFUTE pass 2, 2026-07-30): the
# anchored tail [A-Z0-9_-]* still consumed arbitrary ENTROPY, so any ALL-CAPS value merely
# BEGINNING with a placeholder word was suppressed whole -- including `ADDF9E2B41C77A03`,
# a perfectly valid uppercase-hex secret (`ADD` is hex; ~1 in 4096 random hex secrets
# starts with it). Real placeholders (YOUR_TOKEN_HERE_XXXXXXXX, CHANGE_ME,
# REPLACE_WITH_YOUR_TOKEN) carry no digits, so digit-free costs no suppression we want.
_PLACEHOLDER_WORD_RE = re.compile(
    r"""^\s*["']?(?:YOUR|REPLACE|CHANGEME|CHANGE_ME|EXAMPLE|PLACEHOLDER|TODO|FIXME
        |DUMMY|FAKE|SAMPLE|REDACTED|INSERT|ADD)[A-Z_\-]*["']?\s*$""", re.X)
# Shape forms carry no entropy by construction, so they need no digit gate.
_PLACEHOLDER_SHAPE2_RE = re.compile(
    r"""^\s*["']?(?:[Xx]{4,}|\.{3,}|\*{4,}|<[^>]*>|\{\{[^}]*\}\})["']?\s*$""", re.X)


# CODE-REFERENCE discriminator (2026-07-30, measured): the widened name matcher also fires
# on ordinary source -- `token = _normalize(new_stage)` (a function call) and
# `SECRET_PATTERNS = sp.SECRET_PATTERNS` (a constant reference) were 3 of 3 newly-flagged
# TRACKED files in the differential run. Left unfixed those would block EVERY push, which
# is a worse outcome than the gap: a gate that always fires gets bypassed.
# Discriminator: a real credential literal is QUOTED or contains a DIGIT (entropy);
# a code identifier is typically neither, and a call is followed by '('. Conservative --
# an unquoted digit-bearing value still fires, so nfp_/sk-/AKIA-style keys are unaffected.
# EXACTLY one dot, identifier both sides -> `module.CONST` / `lib.SOME_CONSTANT`.
# A JWT (eyJ...eyJ...sig) has TWO dots and always carries digits, so it never matches.
_DOTTED_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$")
# A function CALL is detected from the character FOLLOWING the match, not from the value:
# the routed patterns' value class excludes '(', so it can never appear inside the match
# (REFUTE pass 2 proved the old in-value check was dead code, which silently turned
# `AUTH_TOKEN = get_credential_from_vault(scope)` into a false positive).
# IMMEDIATE paren only -- no leading \s* (REFUTE pass 3): a whitespace run let a PROSE
# PARENTHETICAL after an unquoted secret read as a call, suppressing real findings like
#   SECRET = <value> (rotate monthly)
# and, because \s* also spans newlines, a value whose NEXT LINE opened with '('. Both were
# executed OLD-caught / NEW-missed regressions. A call has no space before its paren; the
# `helper (scope)` style becomes a false positive instead, which is the safe direction.
_TRAILING_CALL_RE = re.compile(r"^\(")


def _looks_like_code_reference(raw_value):
    """A CODE construct that cannot itself be a credential. Deliberately narrow -- an
    earlier, broader 'unquoted and no digits' rule suppressed this module's OWN long-
    standing fixtures, i.e. it would have silently weakened real detection. Two shapes.
    ACCEPTED residual (REFUTE, 2026-07-30): an UNQUOTED passphrase-style secret of the
    form word.word with no digits reads as a module.CONST reference and is suppressed.
    Quoting it restores detection; the code-reference FP it prevents is far more common."""
    v = raw_value.strip().rstrip(",;)")
    # module.CONST reference, with NO digits anywhere (a real key has entropy)
    return bool(_DOTTED_IDENT_RE.match(v)) and not any(c.isdigit() for c in v)


def _value_is_reference(value, trailing=""):
    """True when THIS match's own value is an env lookup / template / placeholder / code
    reference rather than a credential. `trailing` is the source text immediately AFTER
    the match, used only to spot a function call -- the routed value class cannot contain
    '(', so an in-value check was dead code (REFUTE pass 2). Suppression is the
    false-negative direction, so anything not positively recognized here keeps the
    finding."""
    v = (value or "").strip()
    if not v:
        # Unreachable today: every routed pattern requires 12+ value chars after the
        # separator (REFUTE pass 2 verified across 1,667 tracked files). Retained as a
        # defensive default in the SAFE direction should a future pattern relax that.
        return True
    # NAME = some_helper(...) -> a call. BOTH guards required (REFUTE pass 3): the paren
    # must be immediate AND the callee digit-free. An identifier is rarely digit-dense; a
    # real secret almost always is -- so a digit-bearing value keeps its finding even if
    # something paren-shaped follows it.
    if _TRAILING_CALL_RE.match(trailing or "") and not any(c.isdigit() for c in v):
        return True
    return bool(_REFERENCE_VALUE_RE.match(v)
                or _PLACEHOLDER_SHAPE2_RE.match(v)
                or (_PLACEHOLDER_WORD_RE.match(v) and not any(c.isdigit() for c in v))
                or _looks_like_code_reference(v))


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
        if label in ("secret/token assignment", "generic API key assignment"):
            # widened-name matcher: suppress env-reference / placeholder / code-reference
            # matches only. Evaluated PER MATCH -- each match is tested against ITS OWN
            # value. Two earlier designs were REFUTED (2026-07-30) and must not return:
            #   * whole-TEXT: all-or-nothing; one genuine value anywhere defeated
            #     suppression everywhere, and vice versa.
            #   * per-LINE: the pattern's `\s*` after [:=] spans newlines, so a YAML-style
            #     `TOKEN:\n  <value>` matched the full text while matching NO single line
            #     -- the label was dropped entirely. A real false negative.
            # Per-match also fixes the greedy-capture evasion (`A=${TPL} SECRET=real`):
            # the match's value side stops at whitespace, so the real assignment is its
            # own match and is judged on its own.
            # Prefix-shaped credentials (nfp_/sk-ant-/ghp_/AKIA) carry their own labels
            # and never route through here, so a real key is unaffected either way.
            if all(_value_is_reference(_match_value(m.group(0)), text[m.end():m.end() + 2])
                   for m in rx.finditer(text)):
                continue
        found.add(label)
    return sorted(found)


# A `git log -p` body concatenates every file, which destroys the file attribution that
# is_exempt_path() needs -- scanning it as one blob makes the gate unusable, because a test
# fixture anywhere in the pushed history would block every push forever. Splitting on the
# diff header restores per-file attribution.
# A merge commit scanned with `git log -p --cc` (2026-11-08, prepush-scan-skips-merge-commit-
# diffs) emits `diff --cc <path>` (or `diff --combined <path>`) headers instead. Each must open
# its own section: otherwise the merge's hunks are folded into the PREVIOUS file's section and
# silently dropped whenever that file is an exempt test path.
_DIFF_HEADER_RE = re.compile(
    r"^diff (?:--git a/(.+?) b/(.+?)|--(?:cc|combined) (.+?))$", re.M)


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
        path = m.group(2) or m.group(3)  # b/<path> post-image name, or the combined-diff path
        if is_exempt_path(path):
            continue
        labels = scan_text(diff_text[m.start():end])
        if labels:
            out.append((path, labels))
    return out
