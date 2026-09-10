"""ASCII-only guard -- PreToolUse hook, matcher: Write|Edit (+ the Desktop
Commander write twins).

BLOCKS a write that would introduce a non-ASCII byte into a file whose MODULE
DOCSTRING declares itself ASCII-only. Also ships a `--repair` CLI that rewrites
such a file to ASCII, and a `--check` CLI for sweeps.

WHY THE CONVENTION IS LOAD-BEARING, NOT STYLE. 64 of this repo's 258 tracked
.py files declare "ASCII-only" in their module docstring by the matcher below
(78 if you match the phrase loosely -- see the carve-out), and the claim is
measured, not aesthetic:
reference_powershell_git_show_corrupts_nonascii.md recorded that
`& git show "HEAD:path"` in an unattended `powershell.exe -NoProfile` run on
this machine decodes child stdout as IBM437, silently mangling every non-ASCII
byte -- no error, no exit code, just wrong bytes flowing into whatever consumed
them. reference_windows_hook_stdin_cp1252_encoding_gap.md documents the stdin
twin: a hook's own payload arriving cp1252-decoded. Any hook or maintenance
script whose text can round-trip through either path has to be ASCII to be
correct, and the guards themselves are precisely that class of file.

WHY THIS EXISTS. Until now NOTHING enforced the declaration. At c27d3b6 SIX
files declared ASCII-only by this matcher and were measurably in violation --
the convention was documentation, honored by habit, drifting silently. A
declaration nothing checks is worse than no declaration: it is a claim later
readers rely on.

THREE OF THOSE SIX ARE REPAIRED ON THIS BRANCH; THREE ARE NOT, AND THE
DIFFERENCE IS THE POINT. Repaired (prose that merely LOOKED typographic):
hooks/eos-review-gate.py and hooks/lib/scheduled_task_frontmatter.py each held a
literal U+FEFF inside a comment ABOUT BOM handling; maintenance/eos-telemetry-
rollup.py held three em dashes. The other three -- hooks/tests/test-config-write-
guard.py, hooks/tests/test-ora-autonomy-gate.py, hooks/tests/test-tool-call-
paths.py -- carry U+200B, U+FF20, U+202E, U+0332 and U+00AD as ADVERSARIAL
FIXTURES: the homoglyph, zero-width, combining, soft-hyphen and
right-to-left-override strings those very tests feed to
config-write-guard, ora-autonomy-gate and the path-canonicalizer to prove the
guards are not fooled by them. --repair correctly REFUSES all three (no canonical
ASCII spelling), and mechanically "fixing" them would delete the test. They are
remedy 2 in the block message below: escape the fixture as \\uXXXX, or qualify
the docstring claim the way hooks/tests/test-eos-claude-md-guard.py already does
("ASCII-only source (payloads below may contain literal non-ASCII"), which is why
that file reads as UNdeclared here and is not counted among the six. That tree is
owned by another session, so `--check` still reports those three until it lands.

SAFETY INVARIANT -- FAIL OPEN BY CONSTRUCTION, not by exception handling. This
guard blocks only on THREE affirmative signals:
  (a) the target EXISTS, parses, and its MODULE DOCSTRING declares ASCII-only,
  (b) the post-write content DEMONSTRABLY carries a codepoint > 127, and
  (c) both were read reliably and UNAMBIGUOUSLY (exactly one target path, a
      string content field, a recognized tool).
Anything missing, unreadable, undecodable, unparseable, mistyped or ambiguous
is NO INFORMATION -> ALLOW. The shape is copied deliberately from
commit-provenance-guard.py, whose three-affirmative-signal model has held since
2026-07-16, and the reason is feedback_confidentiality_guard_selfdeadlock.md: a
fail-CLOSED guard fed a malformed input once bricked Write/Edit/Bash
machine-wide. A guard over a STYLE convention has no business being able to do
that, so the whole body is wrapped IN main() ITSELF -- not merely under
`if __name__ == "__main__"`, which the in-process dispatcher path never runs --
and any internal error allows. See main()'s own docstring for the escape that
proved the distinction matters.

EXIT CODES (reference_pretooluse_vs_git_hook_exit_codes.md -- PreToolUse
family): exit 0 = allow; exit 2 + stderr = block. NEVER exit 1, which is the
NON-blocking error code: the tool call would PROCEED, silently disabling the
gate.

TOOL AND FIELD COVERAGE IS MEASURED, NOT ASSUMED. Per
feedback_fixture_shaped_tests_certify_dead_branches.md -- eos-telemetry.py
matched tool name "Task" and its fixture agreed, both wrong, the real tool is
"Agent" (0 vs 672 occurrences), a green test over a dead branch for months --
every name below was counted across the 1628 real transcripts under
C:/Users/Owner/.claude/projects/**/*.jsonl before it was written:

    Write                        2386 calls   file_path + content
    Edit                         5398 calls   file_path + old_string +
                                              new_string (3 calls carried NO
                                              new_string -> that shape allows)
    mcp__*__edit_block             30 calls   file_path + old_string + new_string
    mcp__*__write_file              4 calls   path + content
                                              -- `path`, NOT `file_path`.
    MultiEdit                       0 calls   -> NO branch. Writing one would
    NotebookEdit                    0 calls      be the exact dead-branch trap.

For an Edit the introduced text is `new_string` alone: an edit can only ADD the
bytes it inserts, so a pure-ASCII new_string cannot introduce a violation no
matter what the file already holds. That keeps the check sound without having
to reconstruct post-edit content (which would need old_string to match, an
ambiguity this guard refuses to resolve).

DELIBERATE NON-COVERAGE, stated so nobody mistakes this for a boundary:
  * Shell writes (Bash, DC start_process) are NOT gated. Their content is
    pre-expansion command text; the same structural ceiling ora-autonomy-gate.py
    documents applies, and a text guess here would be false positives with no
    compensating precision.
  * Non-.py targets are NOT gated. "Module docstring" is a Python concept; the
    words appearing in a .md file are prose about the convention, not a
    declaration of it.
  * This is a RAIL AGAINST DRIFT, not an adversarial control. Anything that
    writes bytes without going through these tools bypasses it entirely.

OVERRIDE. Uses the SHARED session-scoped contract (hooks/lib/override_tokens.py)
-- no new mechanism, and specifically not the retired flat mtime-only sentinel
whose four defects that module's docstring catalogues. It carries its OWN tier
NAME because that module's rule is "one name, one tier": reusing, say,
allow-config-write would mean approving a routine config edit silently
authorized an encoding violation too, which is exactly defect 3 the shared
contract exists to prevent.

    hooks/sessions/<session_id>/overrides/allow-ascii-only-write
        scope: ascii-only-write
        session: <the session_id it was minted in>
        reason: <free text, for the audit trail>

TEST SEAM: the lib's ORA_OVERRIDE_SESSIONS_DIR only. TEST ONLY -- setting it in
settings.json or a scheduled task would redirect an override lookup to an
arbitrary directory.

NOT WIRED YET -- AND WIRING IT TAKES *TWO* ENTRIES, NOT ONE. As shipped this
guard runs only via --check / --repair; pretooluse-dispatcher.py's GUARD_CHAIN
was owned by a concurrent session when this landed, so the entry was deferred
rather than spliced. Whoever wires it:

  1. Add "ascii-only-guard" to GUARD_CHAIN in pretooluse-dispatcher.py -- NOT
     as a new settings.json PreToolUse entry. That file's header is explicit:
     a second entry would run the guard twice on every Edit/Write.
  2. THEN ADD A SEPARATE settings.json ENTRY FOR THE DESKTOP COMMANDER TWINS.
     This is the step that is easy to miss and it is why step 1 alone is not
     enough: GUARD_CHAIN's matcher is EXACTLY `Edit|Write|MultiEdit`, so
     mcp__*__write_file and mcp__*__edit_block payloads would never reach this
     guard at all -- and is_full_write_tool()/is_edit_tool()'s DC branches, plus
     the tests that cover them (1h, 1i), would become green tests over dead
     code: exactly the failure this file's own TOOL COVERAGE section cites.
     Copy registry-write-guard.py's matcher, which already spells both the
     `mcp__Desktop_Commander__*` and `mcp__plugin_desktop-commander_*` forms
     that _mcp_family() handles.
  3. Add a wiring assertion in the shape of hooks/tests/test-write-guard-
     coverage.py, so the wiring itself is testable rather than assumed.

Stdlib only. ASCII-only. Windows (`python`).
"""
import ast
import json
import os
import re
import sys

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))

# Import posture mirrors config-write-guard.py and ora-autonomy-gate.py. Letting
# an ImportError propagate would exit 1 -- NON-blocking, silently disabling the
# gate; a sys.exit(2) at import time would brick every Write and Edit in every
# session. So degrade to "no override exists". For THIS guard that degrade is
# strictly safe in the other direction too: it can only ever make a block
# stickier, never create one, and the block is itself rare and advisory.
try:
    from override_tokens import (Tier, describe_token, token_grants,  # noqa: E402
                                 token_path)
    TOKEN_CONTRACT_LOADED = True
except Exception:
    TOKEN_CONTRACT_LOADED = False

    class Tier(object):
        def __init__(self, name, scope, ttl, single_use=False,
                     requires_extra_check=False):
            self.name = name
            self.scope = scope
            self.ttl = ttl
            self.single_use = single_use
            self.requires_extra_check = requires_extra_check

    def token_grants(session_id, tier, extra_check=None):
        return None  # no validator -> no grant, ever

    def token_path(session_id, name):
        return None  # no addressable token location -> treated as unreadable

    def describe_token(session_id, tier):
        return ("  <hooks/lib/override_tokens.py could not be imported -- no "
                "override can be honored; fix the module, do not mint a token>\n")

ASCII_ONLY_WRITE = Tier("allow-ascii-only-write", "ascii-only-write", 3600)

# The declaration as it is ACTUALLY written across the repo: the standalone
# sentence "ASCII-only." inside the trailing "Stdlib only. ASCII-only. Windows
# (`python`)." line. It must sit in the MODULE DOCSTRING, because a mention in a
# comment (this file has several) is prose about the convention, not a claim.
#
# THE REASON THIS REGEX IS NOT `ascii[-_ ]?only` is that a naive substring match
# conflates TWO DIFFERENT CLAIMS that happen to share a word, and the difference
# is not cosmetic:
#
#   "Stdlib only. ASCII-only."            -> the SOURCE BYTES are ASCII.
#   "Pure stdlib. ASCII-only output       -> what the script PRINTS is ASCII.
#    (Windows cp1252 console)."              Says nothing about its source.
#
# Three files make the second claim and honor it deliberately:
# maintenance/doctrine-integrity-probe.py (which even ships an ascii_safe()
# encoding its output with backslashreplace), its test, and
# maintenance/test-governor-drift-probe.py. All three MUST hold non-ASCII source
# literals to do their jobs -- governor-drift-probe.py's regexes contain literal
# U+00D7 and U+2264 inside character classes (a "[x<U+00D7>]?" optional
# multiplier suffix, a "[<U+2264><]=?" comparator) that match real doctrine
# text, so its test's fixtures have to reproduce those bytes or the branches go
# untested. A loose matcher reads all three as violating and would
# block every future edit to them forever, which is how a guard over a
# convention becomes a guard against work. It also inflates the violation count,
# measured over the 256 tracked .py files at c27d3b6: a loose substring scan
# calls 76 files declared and 10 of them violating; this matcher calls 62
# declared and 6 violating. The four it drops are those three plus
# hooks/tests/test-eos-claude-md-guard.py, whose claim is qualified in prose
# ("ASCII-only source (payloads below may contain literal non-ASCII").
#
# WHICH CLAUSE ACTUALLY DOES THAT WORK, measured rather than assumed
# (independent review 2026-09-10 -- an earlier revision of this comment credited
# the noun lookahead with it and was wrong): all four are dropped by the
# STANDALONE-SENTENCE assertion, not by the noun list. Deleting the lookahead
# changes the verdict on ZERO of the 256 files. It is kept anyway because `$` is
# multiline here, so a docstring that line-wraps as "ASCII-only\noutput" WOULD
# otherwise match -- that wrapped form is the only shape the lookahead defends,
# and test 2f pins exactly it. Do not delete the lookahead on the grounds that
# the flat corpus does not exercise it; do not credit it with more either.
#
# Mechanically: the phrase must stand as its own sentence or clause (the next
# non-space character terminates it), OR be followed by an affirmative
# source-noun; an explicit lookahead rejects the scoped "ASCII-only <noun>"
# forms even when punctuated; and a preceding negation ("NOT ASCII-only") is
# refused outright, since reading a disclaimer as a declaration would BLOCK on a
# file that just said the opposite.
DECLARATION_RE = re.compile(
    # A disclaimer is not a declaration. Without this, "This file is NOT
    # ASCII-only." reads as a claim and BLOCKS a file that said the opposite --
    # a false BLOCK, the only direction this guard must never fail in. This
    # guard's own remedy text invites people to write about the convention in
    # docstrings, so the shape is reachable.
    #
    # KNOWN LIMIT, stated rather than papered over: only an IMMEDIATELY
    # preceding negation is caught. "Do not assume ASCII-only." still reads as
    # a declaration. Widening to arbitrary-distance negation was rejected --
    # it would start swallowing real declarations that merely sit in a sentence
    # containing the word "not", trading a rare false positive for a class of
    # silent false negatives (ungated files), which is the worse error here.
    r"(?<!\bnot )(?<!\bnever )(?<!\bnon-)"
    r"\bascii[-_ ]?only\b"
    # The SCOPED claim: "ASCII-only output" is about what a script PRINTS.
    r"(?!\s*(?:output|stdout|stderr|console|print|printing|report|reports"
    r"|log|logs|logging|filenames?|paths?|names?)\b)"
    # STANDALONE SENTENCE OR CLAUSE: the next non-space character terminates it.
    # This is the ONLY affirmative form, deliberately.
    #
    # AN EARLIER REVISION OF THIS COMMIT ALSO ACCEPTED "ASCII-only source|file|
    # bytes|encoding", on review feedback that the longhand reads as UNdeclared.
    # MEASURED, IT WAS A REGRESSION and was reverted: the sole in-repo use of
    # that longhand is hooks/tests/test-eos-claude-md-guard.py's "ASCII-only
    # source (payloads below may contain literal non-ASCII" -- a QUALIFIED
    # claim on a file that deliberately holds non-ASCII fixtures. Accepting the
    # noun flipped it from correctly-excluded to VIOLATING (3 -> 4), i.e. a
    # permanent false block on a file that had told the truth. The longhand is
    # therefore ambiguous in exactly the way "ASCII-only." is not, and a
    # false-negative (an ungated file) is the cheap error here while a
    # false-positive is the expensive one.
    r"\s*(?=[.,;:!)\]]|$)",
    re.I | re.M)

# Canonical ASCII spellings. Deliberately conservative: a codepoint absent from
# this map has no unambiguous ASCII equivalent, and --repair REFUSES the file
# rather than dropping or approximating it. Guessing is how a mechanical repair
# silently changes meaning.
REPLACEMENTS = {
    0x2010: "-", 0x2011: "-", 0x2012: "-", 0x2013: "-", 0x2014: "--",
    0x2015: "--", 0x2212: "-",
    0x2018: "'", 0x2019: "'", 0x201A: "'", 0x201B: "'",
    0x201C: '"', 0x201D: '"', 0x201E: '"', 0x201F: '"',
    0x2026: "...", 0x00A0: " ", 0x2007: " ", 0x202F: " ", 0x2009: " ",
    0x2190: "<-", 0x2192: "->", 0x2194: "<->",
    0x21D0: "<=", 0x21D2: "=>",
    0x2264: "<=", 0x2265: ">=", 0x2260: "!=", 0x2248: "~=",
    0x00B7: "-", 0x2022: "*", 0x00B0: " deg",
    0x00A7: "sec ", 0x00B6: "para ",
    0x00D7: "x", 0x00F7: "/", 0x00B1: "+/-",
    0x2032: "'", 0x2033: '"',
    0x00BD: "1/2", 0x00BC: "1/4", 0x00BE: "3/4",
    0x2122: "(TM)", 0x00AE: "(R)", 0x00A9: "(C)",
    # PROSE ABOUT a byte-order mark, which is the only in-repo shape: both real
    # cases sit inside a comment explaining that a BOM survived .strip(). A
    # genuine BOM at offset 0 is a different object entirely and --repair
    # refuses that file outright (see repair_text).
    0xFEFF: "U+FEFF",
}

MAX_REPORTED = 8


# ------------------------------------------------------------------ tool shapes
def _mcp_family(tool_name, suffix):
    return isinstance(tool_name, str) and tool_name.startswith("mcp__") \
        and tool_name.endswith(suffix)


def is_full_write_tool(tool_name):
    """Tools whose payload carries whole-file content rather than a fragment.

    NOT always the WHOLE post-write content: 2 of the 4 real
    mcp__*__write_file calls passed mode=append, where `content` is a fragment.
    That does not affect block correctness -- an append, like an Edit's
    new_string, can only ADD the bytes it carries, so a pure-ASCII payload
    cannot introduce a violation either way -- but it does mean the reported
    offsets are offsets into the payload, which the block message now says."""
    return tool_name == "Write" or _mcp_family(tool_name, "write_file")


def is_edit_tool(tool_name):
    """Tools whose payload carries only the INSERTED text (`new_string`)."""
    return tool_name == "Edit" or _mcp_family(tool_name, "edit_block")


def target_path(tool_input):
    """The single unambiguous write target, or None.

    Both real path fields are considered (`file_path` for Write/Edit/edit_block,
    `path` for DC write_file). If they are BOTH present and DISAGREE the call is
    ambiguous -- this guard cannot know which one the tool will honor, so it
    declines to guess and allows. (config-write-guard.py resolves the same
    ambiguity the opposite way, gating EVERY candidate, because a missed block
    there is a governance hole. Here a missed block is a stray em dash.)
    """
    seen = []
    for field in ("file_path", "path"):
        raw = tool_input.get(field)
        if isinstance(raw, str) and raw.strip() and raw not in seen:
            seen.append(raw)
    return seen[0] if len(seen) == 1 else None


def introduced_text(tool_name, tool_input):
    """The text this call would put INTO the file, or None if unknowable."""
    if is_full_write_tool(tool_name):
        value = tool_input.get("content")
    elif is_edit_tool(tool_name):
        # 3 of 5398 real Edit calls carried no new_string at all. Absent, null
        # or non-string -> no information -> allow.
        value = tool_input.get("new_string")
    else:
        return None
    return value if isinstance(value, str) else None


# ------------------------------------------------------------- the declaration
def declares_ascii_only(path):
    """True / False / None, where None means "could not read the signal".

    Both False and None allow; they are kept distinct so the intent is legible
    at the call site and a future edit cannot collapse "no declaration" into
    "unreadable, assume the worst".
    """
    if not path.lower().endswith(".py"):
        return False  # a module docstring is a Python concept -- no signal
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except (OSError, ValueError):
        # Missing, a directory, ACL-denied, locked, too long -- all the same
        # answer: no information. ValueError is NOT redundant with OSError: a
        # path carrying an embedded NUL raises ValueError from open() itself,
        # before any OS call happens, and that one escaped an earlier revision
        # (independent review 2026-09-10).
        return None
    try:
        # utf-8-sig, so a BOM'd source still parses rather than reading as an
        # unreadable signal (same reasoning as override_tokens.parse_token).
        text = raw.decode("utf-8-sig")
    except (UnicodeDecodeError, ValueError):
        return None
    try:
        doc = ast.get_docstring(ast.parse(text))
    except Exception:
        return None  # syntax error, recursion limit, anything -> no signal
    if not doc:
        return False
    return bool(DECLARATION_RE.search(doc))


def offenders(text):
    """[(utf8_byte_offset, character)] for every codepoint > 127 in `text`.

    The str.isascii() short-circuit is not micro-optimisation: this runs on the
    hot path of EVERY Edit and Write, and the loop below costs a per-character
    .encode(). Measured on a 1 MB payload: 93 ms for the loop, 3 microseconds
    for isascii(). The whole reason pretooluse-dispatcher.py exists is to
    recover 585 ms per call, so spending 93 ms here on the overwhelmingly common
    all-ASCII payload would hand a meaningful slice of that straight back."""
    if text.isascii():
        return []
    out = []
    offset = 0
    for ch in text:
        if ord(ch) > 127:
            out.append((offset, ch))
        offset += len(ch.encode("utf-8"))
    return out


def describe_offenders(hits):
    """One line per distinct codepoint: where it is, and what to write instead."""
    order = []
    grouped = {}
    for offset, ch in hits:
        cp = ord(ch)
        if cp not in grouped:
            grouped[cp] = []
            order.append(cp)
        grouped[cp].append(offset)
    lines = []
    # BOTH axes are capped. Capping only the offsets-per-codepoint (as an
    # earlier revision did) still let a payload with thousands of DISTINCT
    # codepoints emit thousands of lines into a blocking stderr message, which
    # is a message nobody reads and a denial dressed as a diagnostic.
    for cp in order[:MAX_REPORTED]:
        offsets = grouped[cp]
        shown = ", ".join(str(o) for o in offsets[:MAX_REPORTED])
        if len(offsets) > MAX_REPORTED:
            shown += ", ... (%d more)" % (len(offsets) - MAX_REPORTED)
        fix = REPLACEMENTS.get(cp)
        if cp == 0xFEFF and 0 in offsets:
            # At offset 0 this is a real byte-order mark, not prose about one,
            # and rewriting it into the letters "U+FEFF" would be wrong -- which
            # is exactly why --repair refuses that file. Advising the mapping
            # here while --repair refuses would be the guard contradicting
            # itself in two messages about the same byte.
            fix = ("re-save the file as UTF-8 WITHOUT a BOM (at offset 0 this "
                   "is a real byte-order mark, not prose about one)")
        elif fix is not None:
            fix = "write %r instead" % fix
        else:
            fix = "no canonical ASCII spelling -- rewrite the phrase"
        lines.append("  U+%04X at byte offset %s  ->  %s" % (cp, shown, fix))
    if len(order) > MAX_REPORTED:
        lines.append("  ... and %d more distinct codepoint(s)"
                     % (len(order) - MAX_REPORTED))
    return "\n".join(lines)


# ---------------------------------------------------------------- repair / check
class RepairRefused(Exception):
    pass


def repair_text(text):
    """`text` with every mapped non-ASCII codepoint replaced. Pure and
    idempotent: every replacement is itself ASCII, so a second pass is a no-op.

    Raises RepairRefused rather than guessing when the file opens with a real
    byte-order mark (U+FEFF at offset 0 is an encoding artifact, not the prose
    the map is for) or carries a codepoint with no canonical ASCII spelling.
    """
    if text[:1] == "\ufeff":
        raise RepairRefused(
            "file opens with a real byte-order mark (U+FEFF at offset 0); "
            "re-save it as UTF-8 without BOM rather than letting --repair "
            "rewrite the mark into the words \"U+FEFF\"")
    unmapped = []
    for ch in text:
        cp = ord(ch)
        if cp > 127 and cp not in REPLACEMENTS and cp not in unmapped:
            unmapped.append(cp)
    if unmapped:
        raise RepairRefused(
            "no canonical ASCII spelling for: "
            + ", ".join("U+%04X" % cp for cp in unmapped)
            + " -- rewrite those phrases by hand, or drop the file's "
              "ASCII-only declaration if the character is load-bearing")
    return "".join(REPLACEMENTS.get(ord(ch), ch) for ch in text)


def scan_file(path):
    """(declared, hits, error) for a path. `hits` is offenders() over the file."""
    declared = declares_ascii_only(path)
    if declared is not True:
        return declared, [], None
    try:
        with open(path, "rb") as fh:
            # Plain utf-8, NOT utf-8-sig. utf-8-sig silently CONSUMES a leading
            # byte-order mark, so a BOM'd file scanned that way reported CLEAN
            # while carrying three non-ASCII bytes at offset 0 -- caught by
            # test_repair_refuses_a_real_bom before this shipped. Declaration
            # detection above still uses utf-8-sig, because there the BOM is
            # noise in front of the docstring; here it IS the finding.
            text = fh.read().decode("utf-8")
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return declared, [], str(exc)
    return True, offenders(text), None


def cli(argv):
    """--check / --repair. NEVER reachable from the hook path: the hook is
    stdin-driven and the harness invokes it with no argv at all. A guard that
    could rewrite files as a side effect of being consulted would be a far worse
    hazard than the drift it guards against."""
    mode = argv[0]
    paths = argv[1:]
    if not paths:
        sys.stderr.write("usage: ascii-only-guard.py (--check|--repair) <path>...\n")
        return 2
    bad = 0
    for path in paths:
        declared, hits, err = scan_file(path)
        if err:
            print("SKIP   %s  (unreadable: %s)" % (path, err))
            bad += 1
            continue
        if declared is None:
            print("SKIP   %s  (declaration unreadable)" % path)
            continue
        if declared is False:
            print("N/A    %s  (does not declare ASCII-only)" % path)
            continue
        if not hits:
            print("CLEAN  %s" % path)
            continue
        if mode == "--check":
            print("VIOLAT %s  (%d non-ASCII character(s))" % (path, len(hits)))
            print(describe_offenders(hits))
            bad += 1
            continue
        with open(path, "rb") as fh:
            raw = fh.read()
        try:
            # Plain utf-8 (not -sig): repair must SEE a leading BOM so it can
            # refuse the file, rather than silently consuming it and writing the
            # file back without it.
            new = repair_text(raw.decode("utf-8")).encode("ascii")
        except RepairRefused as exc:
            print("REFUSE %s  (%s)" % (path, exc))
            bad += 1
            continue
        except (UnicodeDecodeError, UnicodeEncodeError) as exc:
            print("REFUSE %s  (%s)" % (path, exc))
            bad += 1
            continue
        if new != raw:
            # Binary I/O throughout, so line endings are preserved byte-exactly.
            with open(path, "wb") as fh:
                fh.write(new)
        print("REPAIR %s  (%d non-ASCII character(s) -> ASCII)" % (path, len(hits)))
    return 1 if bad else 0


# ------------------------------------------------------------------- hook path
def main():
    """FAIL-OPEN WRAPPER. THE BODY MUST BE WRAPPED HERE, NOT ONLY UNDER
    `if __name__ == "__main__"`.

    Caught in independent review 2026-09-10. Since 2026-08-05 the Edit/Write
    matcher runs through hooks/pretooluse-dispatcher.py, which IMPORTS this
    module and calls main() IN-PROCESS -- the `__main__` block never executes on
    that path, so its `except Exception: pass` protected nothing where it
    mattered. Proven: a `file_path` carrying a NUL byte raises ValueError out of
    declares_ascii_only (open() rejects it before OSError is reachable), which
    escaped main() entirely. The call was still ALLOWED, but only because the
    dispatcher catches the exception and re-runs the guard as a subprocess,
    where the `__main__` wrapper does catch it. The invariant was being upheld
    by a SIBLING FILE's fallback behavior rather than by construction -- exactly
    the thing this guard's docstring claims it does not do. Now it does."""
    try:
        _evaluate()
    except SystemExit:
        raise  # a real block (exit 2) must propagate
    except Exception:
        return  # any internal error -> no information -> allow


def _evaluate():
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except Exception:
        return  # malformed stdin -> no information -> allow
    if not isinstance(payload, dict):
        return

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return

    tool_name = payload.get("tool_name")
    text = introduced_text(tool_name, tool_input)
    if text is None:
        return  # unrecognized tool, or no readable content field -> allow

    path = target_path(tool_input)
    if path is None:
        return  # absent, mistyped, or ambiguous target -> allow

    hits = offenders(text)
    if not hits:
        return  # signal (b) absent: nothing non-ASCII is being introduced

    if declares_ascii_only(path) is not True:
        return  # signal (a) absent or unreadable

    session_id = payload.get("session_id")
    # THE TEST IS "CAN AN OVERRIDE BE ADDRESSED?", NOT "IS THIS A NON-EMPTY
    # STRING?" -- and the difference is a real hole, caught in independent
    # review 2026-09-10. An earlier revision tested `isinstance(str) and
    # session_id`, but token_path() ALSO requires the id to match the shared
    # contract's SESSION_ID_RE. A session_id of "../../.." is a non-empty string
    # and so passed that test, blocked the write, and then printed a remedy
    # reading "<no usable session id -- an override cannot be created or
    # honored in this context>": a block with no escape hatch, which is exactly
    # what the reasoning below says this guard must never produce. Asking
    # token_path() directly makes the check the real predicate instead of a
    # proxy for it, and cannot drift from the contract it is guessing at.
    #
    # ALLOW HERE DIVERGES from the sibling gates: commit-provenance-guard.py
    # substitutes "nosession" and blocks anyway, and config-write-guard.py's
    # token gate blocks on a positive path match regardless. Both are right for
    # THEM -- a governance or provenance hole is unrecoverable, so an
    # un-overridable block is the lesser harm. This guard is the opposite trade.
    # With no addressable token location, blocking would be a block with no
    # escape hatch, on a STYLE convention, on a signal (who is asking) this
    # guard could not read. That is the fail-open rule applied honestly rather
    # than selectively: any signal it cannot read is no information. The cost of
    # the resulting false negative is one stray em dash, recoverable at any time
    # with `--repair`, which is precisely why this guard can afford the most
    # conservative posture available to it.
    try:
        addressable = token_path(session_id, ASCII_ONLY_WRITE.name) is not None
    except Exception:
        addressable = False
    if not addressable:
        return
    if token_grants(session_id, ASCII_ONLY_WRITE) is not None:
        return  # Gabriel approved this write in-turn
    remedy = describe_token(session_id, ASCII_ONLY_WRITE)

    reason = (
        "This write would introduce %d non-ASCII character(s) into a file whose "
        "module docstring declares it ASCII-only:\n"
        "  %s\n\n"
        "%s\n"
        "  (offsets are into the text BEING INSERTED, not into the file)\n\n"
        "That declaration is load-bearing, not style: an unattended "
        "`powershell.exe -NoProfile` run on this machine decodes child stdout "
        "as IBM437 (reference_powershell_git_show_corrupts_nonascii.md), and "
        "hook stdin as cp1252 (reference_windows_hook_stdin_cp1252_encoding_"
        "gap.md) -- both mangle these bytes silently, with no error and no "
        "exit code.\n\n"
        "Four ways forward:\n"
        "  1. Use the ASCII spelling above. This is almost always the answer.\n"
        "  2. If the character is genuinely LOAD-BEARING (a test fixture that "
        "must reproduce real doctrine bytes, a separator set matched against "
        "real files), then the file's ASCII-only claim is the thing that is "
        "wrong -- drop that claim from its docstring, or write the character "
        "as a \\uXXXX escape so the SOURCE stays ASCII.\n"
        "  3. Sweep an existing file to ASCII mechanically:\n"
        "     python \"%s\" --repair <path>\n"
        "  4. To override this write deliberately, mint:\n"
        "%s"
        % (len(hits), path, describe_offenders(hits),
           os.path.join(HOOKS_DIR, "ascii-only-guard.py").replace("\\", "/"),
           remedy)
    )
    sys.stderr.write("BLOCKED (ascii-only-guard): " + reason + "\n")
    sys.exit(2)


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] in ("--check", "--repair"):
            sys.exit(cli(sys.argv[1:]))
        main()
    except SystemExit:
        raise  # a real block (exit 2) and the CLI's own codes must propagate
    except Exception:
        pass  # fail open: any internal error must never block a tool call
    sys.exit(0)
