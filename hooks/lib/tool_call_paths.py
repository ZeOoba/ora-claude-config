"""Shared tool-call -> write-target normalization for the ORA write-guard hooks.

WHY THIS MODULE EXISTS (2026-07-18, write-guard architecture hardening). Two guards
-- memory-index-guard.py and registry-write-guard.py -- EACH independently
rediscovered the same blind spot on 2026-07-14: a guard written for the native
Write/Edit/MultiEdit tool-call shapes is silently bypassed by Desktop Commander's
write_file/edit_block (different tool names AND a different path field: "path", not
"file_path"), and one real regression reached disk that way (MEMORY.md line 85,
170 chars). That was a guard-ARCHITECTURE gap, not a one-off bug: every guard
re-parsed tool calls from scratch, so every guard shipped with whatever shapes its
author remembered that day. This module is the ONE place that knowledge lives. A new
write-guard imports from here; it does not re-enumerate tool shapes.

WHAT IT COVERS (the write-capable tool-call shapes known in this stack):
  file  : Write / Edit / MultiEdit           (file_path)
          NotebookEdit                        (notebook_path)
          DC write_file                       ("path" -- live schema -- OR "file_path",
                                               both arg spellings seen historically)
          DC edit_block                       (file_path, with "path" fallback)
  move  : DC move_file                        (source AND destination -- moving a file
                                               away deletes it; moving onto a path
                                               overwrites it; both are writes)
  shell : Bash, DC start_process,             (command / input text -- BEST-EFFORT:
          DC interact_with_process             a shell command cannot be statically
                                               resolved to file targets; shell_analysis
                                               flags may_write and NEVER claims a safe
                                               resolution -- resolved is always False,
                                               so a consumer must treat a may_write
                                               shell command as unresolved rather than
                                               silently passing it through as safe)

"DC" means BOTH live tool-name prefixes (mcp__Desktop_Commander__ and
mcp__plugin_desktop-commander_desktop-commander__ -- both exist in this stack, and
prefix-coverage was half of the 2026-07-14 gap).

BEHAVIOR-PRESERVATION CONTRACT for the legacy guards: both guards historically
applied `tool_input.get("file_path") or tool_input.get("path")` for ANY tool name.
primary_write_path() keeps that generic fallback for unknown tool names, so
refactoring a guard onto this module changes HOW it parses, never WHAT it blocks.

SAFETY POSTURE: this module never raises on malformed input -- every function
returns None / [] / False for shapes it cannot read. Fail-open vs fail-closed is
the CALLING GUARD's decision, not this module's.

Stdlib only. ASCII-only. Windows (`python`).
"""
import bisect
import os
import re
import sys
import unicodedata
from collections import namedtuple

# Same self-sufficient sibling-import pattern as email_send_tier.py / website_deploy_tier.py:
# resolve lib/ from this file rather than trusting whatever a consumer put on sys.path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from text_normalization import STRIP_CATEGORIES  # noqa: E402
    # Shape-validate before trusting it: a shared module that imports but exports the
    # wrong TYPE would raise inside normalize_text on every call instead of here.
    if (not isinstance(STRIP_CATEGORIES, tuple) or not STRIP_CATEGORIES
            or not all(isinstance(c, str) for c in STRIP_CATEGORIES)):
        raise TypeError("STRIP_CATEGORIES must be a non-empty tuple of str")
except BaseException:
    # MEASURED, not theoretical (2026-09-18 adversarial review). An unguarded import here
    # is not "the documented degrade-to-inert": losing this one file takes THIS module
    # down, and with it config-write-guard (225 of its checks fail) and lint-config-guard
    # (17) go fully inert -- including their protection of hooks/** itself, i.e. of this
    # file and of ora-autonomy-gate.py. The most likely trigger is mundane: a commit that
    # misses the untracked module, or a partial pull on the shared checkout.
    #
    # BaseException, not Exception: a shared module that called sys.exit() at import time
    # would raise SystemExit, which Exception does not catch, and the guard importing this
    # module would die rather than degrade.
    #
    # Pinned to the canonical tuple by
    # test-tool-call-paths.py::test_strip_categories_fallbacks_match_shared_module.
    STRIP_CATEGORIES = ("Cf", "Mn")

# --------------------------------------------------------------------- tool names
DC_PREFIXES = (
    "mcp__Desktop_Commander__",
    "mcp__plugin_desktop-commander_desktop-commander__",
)


def _dc_names(suffix):
    return frozenset(prefix + suffix for prefix in DC_PREFIXES)


DC_WRITE_FILE_NAMES = _dc_names("write_file")
DC_EDIT_BLOCK_NAMES = _dc_names("edit_block")
DC_MOVE_FILE_NAMES = _dc_names("move_file")
DC_WRITE_PDF_NAMES = _dc_names("write_pdf")
DC_START_PROCESS_NAMES = _dc_names("start_process")
DC_INTERACT_PROCESS_NAMES = _dc_names("interact_with_process")

NATIVE_FILE_TOOLS = frozenset(("Write", "Edit", "MultiEdit"))
NOTEBOOK_TOOLS = frozenset(("NotebookEdit",))


# MCP tool-family recognition is SUFFIX-based, not an exact-name allowlist: the
# 2026-07-14 gap was partly a PREFIX-coverage gap (mcp__Desktop_Commander__ vs
# mcp__plugin_desktop-commander_desktop-commander__ -- both live), and a THIRD
# prefix (a renamed/re-registered connector) would silently re-open an exact-name
# matcher. Suffix matching closes the whole family at once; a false hit on some
# unrelated future "..._write_file" tool merely subjects it to write-guard
# scrutiny, which is the correct default for a tool named like a writer
# (deny-by-default, same direction as ora-autonomy-gate check_mcp's Round 3 fix).
def _mcp_family(tool_name, suffix):
    return isinstance(tool_name, str) and tool_name.startswith("mcp__") \
        and tool_name.endswith(suffix)


def is_dc_write_file(tool_name):
    return _mcp_family(tool_name, "write_file")


def is_dc_edit_block(tool_name):
    return _mcp_family(tool_name, "edit_block")


def is_dc_move_file(tool_name):
    return _mcp_family(tool_name, "move_file")


def is_dc_write_pdf(tool_name):
    return _mcp_family(tool_name, "write_pdf")


def is_shell_tool(tool_name):
    return tool_name == "Bash" or _mcp_family(tool_name, "start_process") \
        or _mcp_family(tool_name, "interact_with_process")


def is_file_tool(tool_name):
    return tool_name in NATIVE_FILE_TOOLS or tool_name in NOTEBOOK_TOOLS \
        or is_dc_write_file(tool_name) or is_dc_edit_block(tool_name) \
        or is_dc_write_pdf(tool_name)


# Exact-name sets kept for consumers that need enumeration (legacy guards' content
# simulation, the SHAPES registry, settings matchers) -- recognition FUNCTIONS above
# are what the normalization paths use.
SHELL_TOOLS = frozenset(("Bash",)) | DC_START_PROCESS_NAMES | DC_INTERACT_PROCESS_NAMES
FILE_TOOLS = (NATIVE_FILE_TOOLS | NOTEBOOK_TOOLS | DC_WRITE_FILE_NAMES
              | DC_EDIT_BLOCK_NAMES | DC_WRITE_PDF_NAMES)
WRITE_CAPABLE_TOOLS = FILE_TOOLS | DC_MOVE_FILE_NAMES | SHELL_TOOLS


def is_write_capable(tool_name):
    return tool_name in WRITE_CAPABLE_TOOLS or is_file_tool(tool_name) \
        or is_dc_move_file(tool_name) or is_shell_tool(tool_name)


# --------------------------------------------------------------------- normalization
# The stripped-category set is SHARED with ora-autonomy-gate.py via
# hooks/lib/text_normalization.py (2026-09-18). It used to be an independent copy of the
# same tuple here, mirroring the gate's by convention only -- read that module for the
# Round 3 (2026-07-17) rationale, for why the two consumers share the CONSTANT but
# deliberately NOT the matcher, and for the path-ordering rule.
#
# The non-str contract below is this module's half of that split and is deliberate: this
# function parses arbitrary tool_input JSON, where a field may legitimately be any type, so
# an odd payload must not raise inside every importing guard.


def normalize_text(text):
    """NFKC-fold compatibility Unicode forms, then strip invisible format/combining
    characters, so marker matching sees what a human reads. Returns "" on non-str."""
    if not isinstance(text, str):
        return ""
    folded = unicodedata.normalize("NFKC", text)
    return "".join(ch for ch in folded
                   if unicodedata.category(ch) not in STRIP_CATEGORIES)


def resolve_path(path):
    """Case-normalized, junction/symlink-resolved absolute form of `path`.

    realpath() follows Windows junctions/symlinks to their real target even when the
    final component does not exist yet (the ordinary Write-a-new-file case) -- the
    same junction-evasion fix ora-autonomy-gate.py's check_file_write adopted
    2026-07-17. Falls back to plain abspath on OS errors. Known residual gaps, same
    as the autonomy gate's: a relative path evaluated against a different effective
    cwd, and a HARDLINK (two equally-real names for one inode -- no target to
    resolve)."""
    try:
        return os.path.normcase(os.path.realpath(path))
    except (OSError, ValueError):
        try:
            return os.path.normcase(os.path.abspath(path))
        except (OSError, ValueError):
            return os.path.normcase(path)


def _clean_str(value):
    return value if isinstance(value, str) and value else None


# --------------------------------------------------------------------- file targets
WriteTarget = namedtuple("WriteTarget", "tool_name raw_path path operation")
# operation is one of: "write", "edit", "notebook-edit", "move-source", "move-dest"


def primary_write_path(tool_name, tool_input):
    """The single file path a direct file-write tool call targets, or None.

    This is the drop-in replacement for the legacy guards' hand-rolled
    `tool_input.get("file_path") or tool_input.get("path")` -- including that exact
    generic fallback for tool names not otherwise listed, so adopting this function
    is behavior-preserving for them."""
    if not isinstance(tool_input, dict):
        return None
    if tool_name in NOTEBOOK_TOOLS:
        return _clean_str(tool_input.get("notebook_path")) \
            or _clean_str(tool_input.get("file_path"))
    if is_dc_write_pdf(tool_name):
        return _clean_str(tool_input.get("file_path")) \
            or _clean_str(tool_input.get("path")) \
            or _clean_str(tool_input.get("output_path"))
    # DC write_file: the live DC schema uses "path"; older payloads used "file_path"
    # -- accept both. Field ORDER is file_path-first for every branch below, because
    # that is the legacy guards' exact historical behavior (`file_path or path`) and
    # this function's contract is behavior preservation. A payload carrying BOTH
    # fields with different values is ambiguous under any single-path answer -- a
    # guard that must be decoy-proof against that shape should use write_targets(),
    # which returns a target per distinct candidate path.
    return _clean_str(tool_input.get("file_path")) \
        or _clean_str(tool_input.get("path"))


def _file_operation(tool_name):
    if tool_name in ("Edit", "MultiEdit") or is_dc_edit_block(tool_name):
        return "edit"
    if tool_name in NOTEBOOK_TOOLS:
        return "notebook-edit"
    return "write"  # Write, DC write_file, DC write_pdf, anything else file-shaped


def write_targets(tool_name, tool_input):
    """Every file path this tool call writes, as WriteTarget tuples with `path`
    resolved (absolute, case-normalized, junction-followed). Shell tools return []
    -- use shell_analysis() for those; they cannot be statically resolved."""
    if not isinstance(tool_input, dict):
        return []
    if is_dc_move_file(tool_name):
        targets = []
        src = _clean_str(tool_input.get("source"))
        dst = _clean_str(tool_input.get("destination"))
        if src:
            targets.append(WriteTarget(tool_name, src, resolve_path(src),
                                       "move-source"))
        if dst:
            targets.append(WriteTarget(tool_name, dst, resolve_path(dst),
                                       "move-dest"))
        return targets
    if is_shell_tool(tool_name):
        return []
    if is_file_tool(tool_name):
        op = _file_operation(tool_name)
        # DECOY DEFENSE: a payload may carry more than one plausible path field
        # (e.g. DC write_file with both "path" -- the live schema field the tool
        # actually honors -- and "file_path"). A gate checking only one of them can
        # be steered onto the innocent value while the tool writes the other. So a
        # path-gating consumer gets a target for EVERY distinct candidate, not just
        # primary_write_path()'s single legacy-ordered answer.
        candidates = []
        for field in ("file_path", "path", "notebook_path", "output_path"):
            raw = _clean_str(tool_input.get(field))
            if raw is not None and raw not in candidates:
                candidates.append(raw)
        return [WriteTarget(tool_name, raw, resolve_path(raw), op)
                for raw in candidates]
    return []


# --------------------------------------------------------------------- shell analysis
ShellAnalysis = namedtuple("ShellAnalysis", "tool_name command may_write resolved")

# Mutating shell/REPL verbs. Superset of ora-autonomy-gate.py's SITE_WRITE_INDICATORS
# plus REPL-flavored writers (interact_with_process feeds a live python/node shell).
# Breadth over precision, per the autonomy-gate doctrine: a false positive costs a
# retry; a false negative silently bypasses a guard.
SHELL_WRITE_INDICATORS = (
    ">", "cp ", "copy ", "mv ", "move ", "rm ", "del ", "remove-item",
    "set-content", "add-content", "out-file", "tee ", "new-item", "mkdir ",
    "touch ", "ren ", "rename ", "sed -i", "dd ",
    # PowerShell item cmdlets (REFUTE 2026-07-18: "move " never matches
    # "move-item" -- a Move-Item onto settings.json reached exit 0 before this)
    "move-item", "copy-item", "rename-item",
    # REPL / scripting writers ("open(" excluded here -- see _open_may_write
    # below; a bare substring check cannot tell open(p,'rb') from open(p,'w'))
    "write_text", "write_bytes", "writefile", "shutil.", "os.remove",
    "os.rename", "os.replace", "unlink(", "rmtree",
    # COMPOSITE WRITERS (2026-08-03, independent-review finding D1). These were
    # caught only ACCIDENTALLY, as substrings of the short verbs above --
    # "copy " inside "robocopy "/"xcopy ", "cp " inside "scp "/"rcp "/"pscp ".
    # Word-anchoring those verbs (below) removed that accident and un-flagged
    # all of them; robocopy.EXE, xcopy.EXE and scp.EXE are all present on this
    # box, and `robocopy <src> <hooks> /MIR` MIRRORS -- it deletes and replaces
    # the entire target tree. config-write-guard is the only control on that
    # path. Named explicitly here so the coverage is deliberate rather than a
    # side effect; each is distinctive enough that bare substring cannot
    # collide with an ordinary word. "rsync " closes a PRE-EXISTING gap found
    # in the same sweep (it was never matched, by either version).
    "robocopy ", "xcopy ", "scp ", "rcp ", "pscp ", "rsync ",
    "git-rm ", "git-mv ",
)
# WORD-BOUNDARY BUG (2026-08-03, live-proven). The short verbs above were matched
# as BARE SUBSTRINGS, so they fired from inside ordinary unrelated words:
#     "del " matched "--model "     -> every `--model <id>` argument
#     "dd "  matched "git add "     -> every `git add`
#     "rm "  matched "confirm "
#     "ren " matched "children "
# This is NOT the benign "false positive costs a retry" the doctrine above
# accepts. It DEADLOCKED a gate: eos-review-gate is satisfied by
# `eos-review-gate.py --record ... --model <id>`, whose "--model " tripped
# "del ", so config-write-guard blocked the ONLY sanctioned way to clear the
# review gate -- and its documented exit was minting a 60-minute, multi-use,
# governance-WIDE write token to permit one single-file write. A false positive
# that forces a strictly broader privilege is a security regression, not caution.
#
# Fix: a verb must START at a word boundary. `del x`, `/usr/bin/rm x`, `;rm x`,
# `&&dd if=..` all still match, because the character before the verb is not a
# word character.
#
# THIS ANCHORING IS NOT FREE, and the first draft of it shipped a security
# regression (caught by independent review, D1). Several REAL writers were being
# caught only as accidental substrings of these verbs -- robocopy/xcopy (via
# "copy "), scp/rcp/pscp (via "cp "), git-rm/git-mv. Anchoring removed that
# accident and silently un-flagged all of them. They are now named explicitly in
# SHELL_WRITE_INDICATORS above. Do NOT assume "the verb list still covers it":
# before anchoring anything else here, enumerate the real command names that
# CONTAIN the verb, because that is where the accidental coverage lived.
#
# The lookbehind excludes `\w` and `-`. `-` is deliberate: it keeps the very
# common benign `docker run --rm <img>` from reading as a write, and the
# hyphenated writers it would otherwise cost (git-rm, git-mv) are listed
# explicitly above instead. `.` is deliberately NOT excluded -- it would cost
# `foo.rm x` and `./cp x` and buys nothing anyone could construct.
#
# The differential battery in tests/test-tool-call-paths.py pins BOTH directions
# and mechanically enumerates the collision class; no real write may become
# allowed, which is the only regression that matters.
_BOUNDED_VERBS = ("cp", "copy", "mv", "move", "rm", "del", "tee",
                  "mkdir", "touch", "ren", "rename", "dd")

# What may sit between a verb and its target. A LITERAL SPACE is not enough.
# Every form below was EXECUTED on this box to confirm it is a real invocation
# and not theoretical coverage (2026-08-03):
#   `"rm" f`      -- bash runs a quoted command name
#   `& 'del' x`   -- PowerShell runs it via the call operator
#                    (cmd.exe does NOT: `"del" x` is "not recognized" there,
#                     and `del"x"` concatenates into `delx` in every shell --
#                     do not cite that form as motivation, it executes nowhere)
#   `del/f x`     -- cmd.exe switch form, no space at all
#   `del,x` `del;x` `del=x`
#                 -- cmd.exe treats , ; = as token delimiters exactly like / .
#                    All three were verified to actually DELETE a file via a
#                    .bat harness. Missing them was the same evasion class the
#                    `/` fix claimed to close but only closed one third of.
#   `rm<f`        -- redirect character doubles as a separator in bash
#   `rm\tx`       -- tab is a valid separator in bash and cmd
#
# KNOWN COST, accepted deliberately -- 19 false positives measured across 107
# probed benign commands (9 from a 73-command realistic corpus, 10 from a
# 34-command probe set targeting `, ; = <`), in three classes:
#   quoted/regex TEXT (from `"` `'` `/`):
#       grep -rn '"del"' <hooks>/...   sed -n 's/rm/x/p' <hooks>/...
#       --notes "the 'rm' case is closed"
#   env-var ASSIGNMENT prefixes (from `=`) -- the POSIX/make idiom, and RM/CP/DD
#   are GNU make built-ins, so this is the least obvious of the three:
#       make clean RM=del    env DD=1 python x.py    $env:DD=1; python ...
#   command CHAINING (from `;` `,`):
#       which rm;which cp    grep rm; echo done    --series=rm,cp
# All 19 flag only when ALSO paired with a governance-path marker.
#
# Why this is accepted rather than a repeat of the PR#32 deadlock: every
# governance-tree operation that has NO ungated substitute was probed and still
# ALLOWs -- `--record` (plain and with notes), `--key`, running any hook test or
# the full suite, fleet-status, doctrine-integrity-probe, governor-drift-probe.
# The FPs all have trivial substitutes (Read/Grep/Glob for the reads, reword the
# notes, set the env var in a separate call), so nothing is forced toward the
# governance-wide token. No Makefile is tracked under ~/.claude, and no path
# segment there is named cp/rm/mv/del -- so `/` and `=` collide with command
# TEXT only, never with a real governance path.
# Widening this class is what reintroduced the original bug the last time a
# matcher here was touched, so note WHY it is safe now: the lookbehind carries
# the whole load. `--model=x` puts a word character immediately before "del",
# so it is rejected on the anchor regardless of how permissive the separator
# is. Verified across the FULL 7-character class, not just one member:
# `--model=`, `--model,`, `--model;`, `--model<`, `--model/`, `model,version`,
# `remodel/`, `remodel=`, `confirm/`, `confirm;`, `x-rm=y`.
#
# This change is STRICTLY BROADENING -- a wider separator class can only add
# matches, never remove one -- so unlike the anchoring change it cannot lose a
# true positive. That property is pinned by
# test_widening_the_separator_is_strictly_broadening.
_VERB_SEPARATOR = r"[\s\"'/,;=<]"
_BOUNDED_VERB_RE = re.compile(
    r"(?<![\w-])(?:%s)%s"
    % ("|".join(re.escape(v) for v in _BOUNDED_VERBS), _VERB_SEPARATOR))
# Composite writers get the SAME separator class as the bounded verbs. They used
# to be plain substrings ending in a literal space, which left the two matchers
# inconsistent: `rm\tx` was caught but `robocopy\tsrc <hooks> /MIR` was not --
# and /MIR mirrors, i.e. deletes and replaces the whole target tree.
#
# NO lookbehind here, deliberately, unlike the bounded verbs. Anchoring these
# would drop coverage the bare-substring form had (`prescp`, `descp` and similar
# were flagged via the `cp `/`rm ` substrings). None of those is a real command,
# but dropping them would still be a flag->unflag delta, and losing a true
# positive is the one regression that matters here. No English word contains
# robocopy/xcopy/scp/rcp/pscp/rsync/git-rm/git-mv, so bare matching is safe.
_COMPOSITE_WRITERS = ("robocopy", "xcopy", "scp", "rcp", "pscp", "rsync",
                      "git-rm", "git-mv")
_COMPOSITE_WRITER_RE = re.compile(
    r"(?:%s)%s"
    % ("|".join(re.escape(v) for v in _COMPOSITE_WRITERS), _VERB_SEPARATOR))

# Indicators distinctive enough that a bare substring test cannot collide with an
# ordinary word (hyphenated cmdlets, dotted module calls, redirection).
UNBOUNDED_WRITE_INDICATORS = tuple(
    ind for ind in SHELL_WRITE_INDICATORS
    if ind.strip() not in _BOUNDED_VERBS
    and ind.strip() not in _COMPOSITE_WRITERS)

# open() mode-awareness (BUG, 2026-07-21: "open(" as a bare substring flagged
# open(p,'rb') -- an ordinary READ -- identically to open(p,'w')). Only an
# UNAMBIGUOUS read-only call is exempt: a single simple (non-nested-paren,
# non-comma) path argument, optionally followed by an explicit 'r'/'rb'/'rt'
# string-literal mode and nothing else. Anything else -- a write-mode literal,
# an indirect/variable mode, extra positional or keyword args, or a path
# argument this regex cannot cleanly isolate (e.g. a nested call like
# os.path.join(...)) -- stays flagged. Fail-toward-block on any unresolved
# shape, the same posture as the rest of this module's static text analysis.
_OPEN_CALL_RE = re.compile(r"open\(([^()]*)\)")
_OPEN_SAFE_ARGS_RE = re.compile(r"^\s*[^,]*?\s*(?:,\s*['\"]r[bt]?['\"]\s*)?$")


def _open_may_write(lowered):
    """True if `lowered` contains an open() call that is write-shaped or whose
    shape this module cannot cleanly resolve to an unambiguous read."""
    if "open(" not in lowered:
        return False
    calls = list(_OPEN_CALL_RE.finditer(lowered))
    if len(calls) != lowered.count("open("):
        return True  # some open( call has a shape we can't cleanly isolate
                     # (nested parens, etc.) -- unresolved, fail toward block
    return any(not _OPEN_SAFE_ARGS_RE.match(m.group(1)) for m in calls)
# fd-duplication (2>&1, >&2, &>) and null-device (2>/dev/null, >nul) redirects write
# nothing -- must not trip the bare ">" indicator (autonomy-gate 2026-07-09/10 fixes).
_FD_DUP_RE = re.compile(r"\d*>&\d*|&>{1,2}")
_NULL_REDIRECT_RE = re.compile(r"\d*>\s*(?:/dev/null|nul)\b", re.IGNORECASE)
# git verbs that REWRITE working-tree files (REFUTE 2026-07-18: `git -C ~/.claude
# checkout main -- hooks/` rewrites the live governance layer with no classic write
# verb in its text -- and the verb is NOT adjacent to "git", so a literal
# "git checkout" substring also missed it; live-proven). Matches "git", then any
# same-segment args (no |;&), then a mutating verb as a whole word. Read-only git
# (log/diff/status/show/ls-files) is deliberately absent.
#
# TIME BOUND (PR #234 follow-up, measured 2026-09-20). The single pattern
#     \bgit\b[^|;&\n]*?\b(verb)\b
# is O(n^2): re.search retries it at every `git` and each failed attempt rescans the
# rest of the segment ("git" + " git" * n: 16KB 1.2-3.9s CPU, 32KB 11-15s, 64KB
# 46-60s -- the spread is machine load; the growth is 4x per doubling). This runs on
# EVERY Bash call via shell_may_write() -- config-write-guard.py and
# workbook-write-guard.py, whatever the hooks/lib health -- and the dispatcher runs
# guards in-process with no per-guard timeout, so one slow scan stalls every guard
# behind it.
#
# EXACT, NOT CAPPED: no size cap, no decision change, so nothing legitimate is
# stranded and no protective direction has to be chosen. The pattern matches iff
# some segment (maximal run of non-[|;&\n]) holds a whole-word `git` followed LATER IN
# THAT SEGMENT by a whole-word verb. The FIRST `git` of a segment offers the widest
# tail, so if any `git` works it does; hence one `git` search and one verb search per
# segment, each linear. `pos`/`endpos` (not slicing) keep `\b` reading the real
# neighbouring characters; at a segment edge that neighbour is a separator (a
# non-word char) or the end of the text, exactly what the one-shot pattern saw.
# test-always-on-regex-bound.py pins equality with the raw pattern by seeded
# differential fuzz and pins the CPU bound at 64KB on several worst-case shapes.
_GIT_WORD_RE = re.compile(r"\bgit\b", re.IGNORECASE)
_GIT_VERB_RE = re.compile(
    r"\b(checkout|restore|reset|apply|stash|merge|rebase|"
    r"cherry-pick|clean|revert|pull|switch)\b", re.IGNORECASE)
_GIT_SEGMENT_RE = re.compile(r"[^|;&\n]+")


class _GitMutateMatcher(object):
    """Drop-in for the old compiled GIT_MUTATE_RE: `.search(text)` returns the
    verb's re.Match (truthy) or None. Linear in len(text). Consumers only test
    truthiness; the Match is the mutating verb, not the whole `git ... verb` span."""

    def search(self, text):
        for seg in _GIT_SEGMENT_RE.finditer(text):
            start, end = seg.span()
            git = _GIT_WORD_RE.search(text, start, end)
            if git is None:
                continue
            verb = _GIT_VERB_RE.search(text, git.end(), end)
            if verb is not None:
                return verb
        return None


GIT_MUTATE_RE = _GitMutateMatcher()


# ------------------------------------------------------ heredoc body stripping
# Shared by config-write-guard.py and lint-config-guard.py (each had its own copy of
# the same regex). A heredoc body is DATA being written into a file, not a path any
# command argument names; a commit message that merely MENTIONS hooks/** in prose
# must not trip a governance marker. The opening line and everything after the
# closing delimiter stay untouched, so a heredoc actually used to write INTO a
# protected path is still caught via its redirect target.
#
# TIME BOUND (PR #234 follow-up, measured 2026-09-20). The original single regex
#     <<-?\s*['"]?(WORD)['"]?[^\n]*\n.*?\n[ \t]*\1(?=[ \t\r\n]|$)     (DOTALL)
# rescans to the end of the input for the closer of EVERY `<<WORD` marker that has
# none, so N unclosed markers cost O(N * len): 5000 markers/37KB 7s CPU, 8000 markers
# in a 63KB command 15-20s. Always-on (every Bash call), in-process, no per-guard
# timeout -> it stalls every guard behind it.
#
# EXACT, NOT CAPPED: strip_heredoc_bodies() returns byte-for-byte what
# RAW.sub(_blank, text) returns (test-always-on-regex-bound.py fuzzes the equality
# against the verbatim original), in near-linear time. What the regex
# actually does, which the scanner reproduces on purpose (quirks included):
#   * the opener's `-?`, `\s*` and quote are forced (nothing else can precede the
#     word), so the delimiter word is the maximal [A-Za-z0-9_] run `w`; group 1 may
#     backtrack to any non-empty PREFIX of `w`, longest first (so `<<EOFX` can be
#     closed by a bare `EOF` line -- an existing quirk, preserved, not endorsed);
#   * the opening line ends at the first newline at/after the word (`[^\n]*\n`);
#   * the closer is a newline at index >= that newline + 1, then `[ \t]*`, then
#     exactly the delimiter, then space/tab/CR/LF/end. Because the delimiter is all
#     word characters and must be followed by a non-word character, a closer line
#     is simply "word run W after optional indentation, then [ \t\r\n] or end";
#   * leftmost opener wins, then the longest prefix that has a closer, then the
#     EARLIEST such closer (lazy body); scanning resumes after the match.
# So: index every candidate closer line ONCE (word -> ascending positions), then
# each opener is a dict lookup + bisect instead of a scan to end of input.
#
# COST, STATED HONESTLY: the git matcher is linear. The heredoc scanner is linear
# for every shape tried EXCEPT one, where it is O(n * sqrt(n)): each opener tries
# every distinct closer length <= its word length, slicing/hashing word[:L] (O(L))
# each time, so k distinct closer lengths (which cost ~k^2/2 chars to build) times
# k/2 long-word openers grows ~2.5-4x per doubling (independent review, 2026-09-21):
# 1MB 0.16s, 2MB 0.43s, 4MB 1.1s, 8MB 4.8s, 16MB 16s CPU. At 64KB it is ~5ms. It is
# left as-is deliberately: no bash command anywhere near 1MB exists in this fleet,
# and the exact O(n log n) alternative (walk a prefix-linked sorted key list) adds
# real complexity to security-gate code for a case that cannot occur. If commands
# ever reach MBs, revisit; do NOT add a size cap (it would have to pick a direction
# and would strand legitimate large heredocs).
_HEREDOC_OPEN_RE = re.compile(r"<<-?\s*['\"]?([a-zA-Z0-9_]+)")
_HEREDOC_CLOSER_RE = re.compile(r"\n[ \t]*([a-zA-Z0-9_]+)(?=[ \t\r\n]|$)")


def _heredoc_closer_index(text):
    """({word: [newline_index, ...]}, {word: [closer_end, ...]}, sorted key lengths)."""
    starts, ends = {}, {}
    for m in _HEREDOC_CLOSER_RE.finditer(text):
        word = m.group(1)
        starts.setdefault(word, []).append(m.start())
        ends.setdefault(word, []).append(m.end())
    return starts, ends, sorted({len(w) for w in starts})


def strip_heredoc_bodies(text):
    """Replace each heredoc body with ' <heredoc-body> ' (see the block comment)."""
    if "<<" not in text:
        return text
    out = []
    copied = 0            # text[:copied] is already in `out`
    index = None          # built lazily, once
    newline = None        # cached first "\n" at/after the last word end (-1: none)
    at = text.find("<<")
    while at != -1:
        opener = _HEREDOC_OPEN_RE.match(text, at)
        if opener is None:
            at = text.find("<<", at + 1)
            continue
        word, word_end = opener.group(1), opener.end(1)
        # Openers are visited left to right and word_end only grows, so a cached
        # newline still valid for this word_end (or "no newline left") is reusable.
        if newline is None or (newline != -1 and newline < word_end):
            newline = text.find("\n", word_end)
        if newline == -1:
            break         # no later opener can have an opening line either
        if index is None:
            index = _heredoc_closer_index(text)
        starts, ends, lengths = index
        found = None
        for i in range(bisect.bisect_right(lengths, len(word)) - 1, -1, -1):
            key = word[:lengths[i]]
            positions = starts.get(key)
            if positions is None:
                continue
            j = bisect.bisect_left(positions, newline + 1)
            if j < len(positions):
                found = (key, ends[key][j])
                break
        if found is None:
            at = text.find("<<", at + 1)
            continue
        key, end = found
        first_nl = text.find("\n", at, end)
        out.append(text[copied:at])
        out.append(text[at:first_nl] + "\n <heredoc-body> \n" + key)
        copied = end
        at = text.find("<<", end)
    if not out:
        return text
    out.append(text[copied:])
    return "".join(out)


def _shell_text(tool_name, tool_input):
    if not isinstance(tool_input, dict):
        return None
    if _mcp_family(tool_name, "interact_with_process"):
        return tool_input.get("input")
    return tool_input.get("command")


def shell_may_write(command):
    """True if the command text carries a write-shaped verb/redirect. Static text
    analysis only -- value indirection (variables, concatenation, files read at run
    time) is a documented structural ceiling of this approach (see
    ora-autonomy-gate.py's HONEST LIMIT section); callers must not treat False as
    proof of read-only-ness for adversarial input."""
    if not isinstance(command, str):
        return False
    lowered = normalize_text(command).lower()
    lowered = _FD_DUP_RE.sub(" ", lowered)
    lowered = _NULL_REDIRECT_RE.sub(" ", lowered)
    if GIT_MUTATE_RE.search(lowered):
        return True
    if _open_may_write(lowered):
        return True
    if _BOUNDED_VERB_RE.search(lowered):
        return True
    if _COMPOSITE_WRITER_RE.search(lowered):
        return True
    return any(ind in lowered for ind in UNBOUNDED_WRITE_INDICATORS)


def shell_analysis(tool_name, tool_input):
    """ShellAnalysis for a shell-carrying tool call, else None.

    resolved is ALWAYS False: this module cannot statically resolve a shell command
    to its file targets. A consumer guard must therefore do its own marker matching
    on the (normalized) command text and must NOT interpret may_write=True with no
    marker hit as "safe" -- it is merely "unresolvable", the honest limit."""
    if not is_shell_tool(tool_name):
        return None
    text = _shell_text(tool_name, tool_input)
    if not isinstance(text, str):
        text = ""
    return ShellAnalysis(tool_name, text, shell_may_write(text), False)


# ------------------------------------------------ recursive tree delete (2026-08-14)
# THE GAP THIS CLOSES. Everything above answers "does this command write?" -- and
# every consumer of that answer (config-write-guard.py, workbook-write-guard.py,
# lint-config-guard.py) only BLOCKS when the write indicator is ALSO paired with a
# path marker for the surface that guard protects. The comment on _BOUNDED_VERBS
# says so explicitly: "All 19 flag only when ALSO paired with a governance-path
# marker." That pairing is correct for those guards -- and it leaves a hole:
#     rm -rf ~/.claude/hooks/     -> blocked (governance marker)
#     rm -rf /                    -> blocked (settings.json deny rule)
#     rm -rf ~/Documents/deals    -> UNGUARDED
#     rm -rf .                    -> UNGUARDED
# A recursive tree deletion is destructive because of WHAT IT DOES, not because of
# where it points, so it needs a predicate with no path condition at all.
#
# WHY THIS IS A SEPARATE FUNCTION RATHER THAN A WIDENING. Widening
# SHELL_WRITE_INDICATORS / _BOUNDED_VERBS / _VERB_SEPARATOR changes shell_may_write()
# for ALL THREE consumers simultaneously. That shared-matcher move is exactly what
# produced the 2026-08-03 robocopy regression (anchoring silently un-flagged real
# writers) and the PR#32 eos-review-gate deadlock (a false positive forced a
# strictly BROADER governance-wide token). recursive_delete() touches none of that
# machinery: shell_may_write(), its regexes and its indicator tuples are unchanged,
# byte for byte. A consumer opts in by CALLING this; until one does, behavior is
# identical -- proven by the diff itself (0 deletions, a single contiguous
# insertion) and by the differential battery (zero deltas on shell_may_write,
# shell_analysis, and normalize_text across an 11k-command adversarial corpus,
# independently re-run and confirmed 2026-08-15).
#
# NOT A STRICT SUBSET, and the module does not claim to be one. Two known,
# INTENTIONAL broadenings exist where this detector correctly flags a real
# recursive delete that shell_may_write's OLD predicate misses:
#   - `rm.exe -rf x` / any `verb.exe` spelling -- _BOUNDED_VERB_RE's separator
#     class lacks `.`, so shell_may_write is blind to the .exe form on Windows.
#   - `rm${IFS}-rf${IFS}/x` -- bash's ${IFS} word-splitting evasion.
# test_recursive_delete_known_broadenings_over_shell_may_write pins both as
# documented, expected divergences -- not a defect in this detector, and not
# evidence against the additivity claim (which is about shell_may_write's
# UNCHANGED behavior, never about this detector matching it exactly). It is,
# however, a reason shell_may_write's own verb/separator handling should
# eventually widen -- tracked separately, out of scope here.
#
# SCOPE, stated honestly (see also the PR body). This detects POSIX `rm` with a
# recursive flag. It does NOT detect the Windows-native equivalents -- `rmdir /s`,
# `del /s`, `Remove-Item -Recurse` -- nor Python `shutil.rmtree`, nor any form
# reached through value indirection ($VAR, a variable holding the whole command,
# a script file). Those are deliberate non-goals of THIS change, not oversights;
# each needs its own false-positive analysis, and `Remove-Item -Recurse` already
# has a settings.json deny rule for the Bash tool.
#
# FORCE IS NOT REQUIRED. `-f` only suppresses the interactive prompt, and a
# hook-driven shell is non-interactive, so there is nothing to suppress: `rm -r x`
# destroys the tree just as thoroughly as `rm -rf x`. Recursion is the destructive
# property; `force` is reported as metadata for a consumer that wants to rank
# severity.
RecursiveDelete = namedtuple("RecursiveDelete", "command recursive force targets")

# fd-duplication redirects, WIDER than the shared _FD_DUP_RE: this one also
# covers INPUT duplication (`0<&1`, `<&-`, `3<&0`), which the shared pattern
# omits.
#
# WHY A SECOND PATTERN RATHER THAN WIDENING _FD_DUP_RE. The round-4 reviewer
# suggested widening the shared one to `\d*[<>]&\d*`. That would have been a
# behavior change to shell_may_write(), which applies _FD_DUP_RE at line ~452 to
# decide whether a command writes at all -- stripping MORE text there means fewer
# commands read as writers, silently weakening config-write-guard,
# workbook-write-guard and lint-config-guard at once. That is precisely the
# shared-matcher regression the 2026-08-03 robocopy incident and the PR#32
# eos-review-gate deadlock were caused by, and which this whole change set has
# been careful to avoid. A separate constant used ONLY by recursive_delete()
# keeps the additivity guarantee intact.
_RD_FD_DUP_RE = re.compile(r"\d*[<>]&\d*-?|&>{1,2}")

# A redirect operator separated from its `&` by whitespace (`2> &1`). This exists
# because ${IFS} normalization CREATES that shape: `2>${IFS}&1` becomes `2> &1`,
# which no longer matches the contiguous fd-dup pattern, so the `&` survived to
# _SEGMENT_SPLIT_RE and severed the command from its operand (round-4 finding 2).
# Re-joining is done BEFORE fd-dup stripping so ordering cannot matter.
_SPACED_FD_DUP_RE = re.compile(r"([<>])\s+&")

# `${IFS}` / `$IFS` -- bash's word separator, used as a whitespace evasion.
# Normalized to a real space before parsing so that firing and target extraction
# agree; see the pre-parse block in recursive_delete().
_IFS_TOKEN_RE = re.compile(r"\$\{IFS\}|\$IFS")

# A command SEGMENT boundary. Scoping matters: without it, the individually-benign
# `rm x.txt && ls -R` reads as a tree deletion, because a `-r` belonging to a
# different command would arm the `rm`.
_SEGMENT_SPLIT_RE = re.compile(r"[;&|\n]+")

# `rm` as its own command word. The LOOKBEHIND IS THE SAME `(?<![\w-])` THE
# BOUNDED VERBS USE, and for the same two reasons: `-` keeps `docker run --rm`
# benign (a deliberate, separately-pinned carve-out -- re-breaking it is a
# regression), and `\w` keeps `confirm`/`alarm` benign. The trailing `(?![\w-])`
# is what separates `rm` from `rmdir`, which is a different command with a
# different flag grammar and is deliberately out of scope.
_RM_VERB_RE = re.compile(r"(?<![\w-])rm(?![\w-])", re.IGNORECASE)

# A recursive flag in any spelling rm accepts: `--recursive`, or a short-option
# bundle containing r/R (`-r`, `-rf`, `-fr`, `-vrf`, `-irf`, `-Rf`). The
# `--recursive` alternative must come FIRST -- the short-bundle branch cannot
# match a double dash (its second `-` fails the lookbehind), so without the long
# alternative `--recursive` would go undetected.
#
# THE BUNDLE IS RESTRICTED TO rm's OWN SHORT OPTIONS (rRfiIdv), not `[a-z]`.
# Caught by the REFUTE differential battery, which the hand-written test corpus
# had missed: `-[a-z]*r[a-z]*` matches ANY single-dash flag containing the letter
# "r", so `find . -type d -name rm -print` read as a recursive delete -- the `rm`
# there is a search ARGUMENT and `-print` is find's flag, not rm's. Same class
# would have hit `-perm`, `-newer`, `-prune`. Restricting the character class to
# the options GNU rm actually accepts closes THAT false-positive class (verified
# by the permutation sweep in the differential harness over GNU's option set: 0
# bundles fire without an r, 0 bundles with an r stay silent) while keeping every
# real GNU bundle. Two things this restriction does NOT do, stated honestly
# rather than left for a reader to discover: (1) BSD/macOS rm's own short options
# outside {r,f,i,d,v} -- e.g. `-P`, `-W`, `-x` -- are false NEGATIVES here (`rm
# -rfP x` does not arm), since this machine's differential corpus only exercises
# GNU coreutils; (2) restricting the CHARACTER CLASS does not give `rm` a notion
# of command position, so a bundle-shaped `-r`/`-rf` still arms even when `rm`
# is itself an ARGUMENT to something else, not the command being run -- `git rm
# -r --cached node_modules` (does not delete from disk), `grep rm -r .`, `history
# | grep 'rm -rf'`, and a shell comment `# rm -rf x` all currently read as a
# recursive delete. Both gaps are real and both are deferred, same as every
# other SCOPE item above: nothing consumes this detector yet, so nothing new
# blocks on either gap today. A consumer wiring this into an actual guard must
# close (2) first -- command-position false positives are the operationally
# damaging class, not a cosmetic one.
_RM_SHORT_OPTS = "rfidv"  # r/R recursive, f force, i/I prompt, d dir, v verbose
_RECURSIVE_FLAG_RE = re.compile(
    r"(?<![\w-])--recursive(?![\w-])"
    r"|(?<![\w-])-[%s]*r[%s]*(?![\w-])" % (_RM_SHORT_OPTS, _RM_SHORT_OPTS),
    re.IGNORECASE)
_FORCE_FLAG_RE = re.compile(
    r"(?<![\w-])--force(?![\w-])"
    r"|(?<![\w-])-[%s]*f[%s]*(?![\w-])" % (_RM_SHORT_OPTS, _RM_SHORT_OPTS),
    re.IGNORECASE)

# Argument tokens, quote-aware so a quoted path keeps its spaces.
_ARG_TOKEN_RE = re.compile(r"\"[^\"]*\"|'[^']*'|[^\s\"']+")
# A redirect token (`>log`, `2>/dev/null`, `>`, `2>&1`). It does NOT end the
# operand list -- shell grammar allows redirects before, between, and after
# operands -- so _delete_targets skips it rather than stopping (see MAJOR B).
_REDIRECT_TOKEN_RE = re.compile(r"^\d*[<>]")
# A redirect operator with NO target attached: the target is the next token.
_BARE_REDIRECT_RE = re.compile(r"^\d*[<>]{1,2}&?\d*$")


def _delete_targets(rest):
    """Operands of an `rm` invocation: non-flag tokens up to the first redirect,
    with surrounding quotes removed and original case preserved."""
    # PARTIAL QUOTING IS ONE OPERAND, NOT TWO. `"$HOME"/scratch` and
    # `~/"my folder"/x` are the CORRECT shell idioms (a tilde must stay unquoted
    # to expand), but the token regex alternates between quoted and bare runs, so
    # they arrive as adjacent matches. Splitting them yielded bare `$HOME` and
    # `~/` operands, which a consumer then read as "delete the whole home tree"
    # and blocked -- a false positive that forced a broader override token, the
    # exact regression class this module's 2026-08-03 anchoring work exists to
    # prevent (independent review 2026-08-16, MAJOR 5). Adjacency = no whitespace
    # between matches, so merge on position.
    pieces, spans = [], []
    for m in _ARG_TOKEN_RE.finditer(rest):
        token = m.group(0)
        if pieces and spans[-1] == m.start():
            pieces[-1] += token
        else:
            pieces.append(token)
            spans.append(0)
        spans[-1] = m.end()

    targets = []
    skip_next = False
    for token in pieces:
        if skip_next:
            skip_next = False
            continue
        if _REDIRECT_TOKEN_RE.match(token):
            # A REDIRECT MAY PRECEDE OPERANDS. This loop used to `break` here,
            # which silently dropped the real target: `rm -rf 2>/dev/null <path>`
            # extracted NO operands at all, so the detector fired with an empty
            # target list and every path-based consumer had nothing to judge --
            # a clean bypass using a routine error-suppression idiom
            # (independent re-review 2026-08-16, MAJOR B). Skip the redirect and
            # keep scanning; only a BARE operator consumes the following token.
            if _BARE_REDIRECT_RE.match(token):
                skip_next = True
            continue
        if token.startswith("-"):
            continue  # a flag, or the bare `--` end-of-options separator
        # Strip quotes wherever they appear, so a merged operand keeps its shape.
        token = token.replace("\"", "").replace("'", "")
        # TRAILING GROUP DELIMITERS BELONG TO THE SHELL, NOT THE PATH. `(rm -rf /)`
        # yields the operand `/)`, and that one extra character defeated every
        # exact-match block class -- catastrophic literals, the drive-root regex,
        # and the profile-ancestor test -- while substring markers still matched,
        # which is exactly why it stayed hidden (independent re-review 2026-08-16,
        # MAJOR A). Strip only UNBALANCED delimiters, so a real directory named
        # "Closing (final)" survives intact.
        for close, open_ in ((")", "("), ("}", "{")):
            while (token.endswith(close)
                   and token.count(close) > token.count(open_)):
                token = token[:-1]
        while token.endswith("`") and token.count("`") % 2 == 1:
            token = token[:-1]
        if token:
            targets.append(token)
    return targets


# ---- command position (2026-08-16) -------------------------------------------
# A leading `VAR=value`, which every shell allows before the command word.
_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_]\w*=")

# Commands that EXEC their argument, so an `rm` after one is still the thing being
# run. Deliberately a CLOSED list of exec-wrappers: `git`, `grep`, `echo`, `man`,
# `which` are NOT here, and that omission is the entire point of this table.
_EXEC_WRAPPERS = frozenset((
    "sudo", "doas", "env", "command", "builtin", "exec", "time", "nohup",
    "nice", "ionice", "stdbuf", "setsid", "xargs", "then", "do", "else", "elif",
    "timeout", "watch",
))

# A bare duration/number operand belonging to a wrapper (`timeout 5 rm -rf x`).
_WRAPPER_OPERAND_RE = re.compile(r"^\d+(\.\d+)?[smhd]?$")

# A path prefix attached directly to the command word: /bin/rm, ./rm, C:\bin\rm.
_ATTACHED_PATH_RE = re.compile(r"[\w.:$~\\/-]*[\\/]$")


def _in_command_position(prefix):
    """True if `prefix` -- the segment text before an `rm` match -- leaves that
    `rm` as the command actually being EXECUTED.

    WHY THIS EXISTS. Without it the detector fires on any line that merely
    CONTAINS `rm` beside an r-bundle: `git rm -r --cached node_modules` (which
    unstages and never touches disk), `grep rm -r .`, `history | grep 'rm -rf'`,
    and even the shell comment `# rm -rf x`. The SCOPE note above named that class
    "the operationally damaging class, not a cosmetic one" and made closing it a
    precondition for wiring this detector into any guard -- because a guard that
    blocks `git rm --cached` does not just annoy, it teaches people to route
    around the guard, which costs more than the gap it closed.

    CONSERVATIVE BY CONSTRUCTION, and the asymmetry is deliberate. Any token this
    does not RECOGNIZE as an env-assignment or an exec-wrapper makes the position
    invalid. So an unlisted wrapper (`timeout 5 rm -rf x`, a novel launcher)
    yields a false NEGATIVE -- the detector stays silent -- never a false positive
    that blocks real work. For a guard, silence is recoverable and a wrong block
    is not; the same reasoning the module already applies to value indirection.

    KNOWN FALSE NEGATIVE, stated rather than left to be discovered: an `rm` nested
    inside a quoted sub-invocation (`bash -c "rm -rf x"`, `ssh host 'rm -rf x'`)
    reads as not-in-command-position, because its prefix is `bash -c "`. That is
    the same value-indirection limit recursive_delete() already disclaims, not a
    new one -- statically, the quoted string is data until the inner shell runs
    it."""
    # Subshell / group / command-substitution syntax is POSITION-NEUTRAL: in
    # `(rm -rf x)`, `{ rm -rf x; }`, `$(rm -rf x)` and backticks, the rm is still
    # the command being run. Stripping these is load-bearing -- leaving them
    # unrecognized made a single `(` a deliberate one-character bypass of the
    # whole guard (independent review 2026-08-16, MAJOR 1).
    prefix = prefix.replace("$(", " ").replace("`", " ")
    prefix = re.sub(r"[(){}]", " ", prefix)
    toks = prefix.split()
    # `find ... -exec rm -rf {} +` genuinely deletes: -exec HANDS OFF command
    # position, so everything left of it is find's own arguments, not a caller.
    # Take the text after the LAST hand-off and validate only that.
    for i in range(len(toks) - 1, -1, -1):
        if toks[i].lower() in ("-exec", "-execdir", "-ok", "-okdir"):
            toks = toks[i + 1:]
            break
    prefix = _ATTACHED_PATH_RE.sub(" ", " ".join(toks))
    seen_wrapper = False
    for tok in prefix.split():
        if _ENV_ASSIGN_RE.match(tok):
            continue
        if tok.lower() in _EXEC_WRAPPERS:
            seen_wrapper = True
            continue
        if _WRAPPER_OPERAND_RE.match(tok):
            continue  # `timeout 5 rm -rf x` -- the 5 belongs to the wrapper
        if seen_wrapper and tok.startswith("-"):
            continue  # a FLAG OF a recognized wrapper: `sudo -u x rm -rf ...`,
            # `xargs -0 rm -rf`, `nice -n 10 rm -rf ...`, `env -i rm -rf ...`.
            # Gated on seen_wrapper so a bare `-flag` before an unrecognized
            # command still invalidates the position.
        return False
    return True


def recursive_delete(command):
    """RecursiveDelete if `command` textually performs a recursive `rm`, else None.

    NO PATH CONDITION -- that is the whole point. Static text analysis only, with
    the same honest limit as shell_may_write(): value indirection (a variable
    holding the path or the flags, a command assembled at run time, a script file)
    is not statically decidable, so False here is never proof of safety.

    SCOPE: detects ACCIDENTAL and CARELESS recursive deletes. It is NOT an
    adversarial control and no caller should treat it as one. This matches
    pre-expansion command text, and the shell has unboundedly many spellings that
    expand to the same operand ($'\\057', a variable holding the path, encode-then-
    pipe-to-sh). Four independent review rounds closed every idiom a
    non-adversarial operator would plausibly type; the remainder is that infinite
    tail, and it is open by design rather than by omission."""
    if not isinstance(command, str) or not command:
        return None
    text = normalize_text(command)

    # ---- pre-parse normalization (2026-08-16, independent review round 3) ----
    # BOTH of these separate `rm` from the path it deletes, before any of the
    # parsing below gets a chance to see them.
    #
    # 1. FD-DUPLICATION REDIRECTS. `_SEGMENT_SPLIT_RE` splits on `&`, and `2>&1`
    #    contains one -- so `rm -rf 2>&1 ~/Documents/deals` was severed into
    #    `rm -rf 2>` and `1 ~/Documents/deals`. The rm segment kept the flags and
    #    lost the path, so the detector fired with NO targets and every
    #    path-based consumer had nothing to block. `2>&1` is among the most
    #    common shell idioms and is routinely written before the operand, so this
    #    was careless-agent-plausible, not merely adversarial. Reuses the SAME
    #    _FD_DUP_RE shell_may_write() already applies for the same reason --
    #    a second, parallel pattern here would be a divergence waiting to rot.
    # 2. ${IFS} WORD-SPLITTING. The module advertises seeing through this and
    #    is_recursive_delete() does fire, but _delete_targets() did not treat it
    #    as whitespace, so it yielded the junk operand `${IFS}-rf${IFS}/` that no
    #    consumer could resolve -- the detector claimed a coverage the guard
    #    layer then failed to honor. Normalizing here keeps firing and extraction
    #    consistent by construction, rather than fixing them in two places.
    text = _IFS_TOKEN_RE.sub(" ", text)
    text = _SPACED_FD_DUP_RE.sub(r"\1&", text)  # re-join `2> &1` that IFS created
    text = _RD_FD_DUP_RE.sub(" ", text)

    targets, force = [], False
    hit = False
    for segment in _SEGMENT_SPLIT_RE.split(text):
        for m in _RM_VERB_RE.finditer(segment):
            rest = segment[m.end():]
            if not _RECURSIVE_FLAG_RE.search(rest):
                continue
            if not _in_command_position(segment[:m.start()]):
                continue  # `git rm -r --cached`, `grep rm -r .`, `# rm -rf x`
            hit = True
            force = force or bool(_FORCE_FLAG_RE.search(rest))
            for t in _delete_targets(rest):
                if t not in targets:
                    targets.append(t)
    if not hit:
        return None
    return RecursiveDelete(text, True, force, targets)


def is_recursive_delete(command):
    """True if `command` textually performs a recursive `rm`, anywhere."""
    return recursive_delete(command) is not None


# --------------------------------------------------------------------- shape registry
class Shape(object):
    """One write-capable tool-call shape, with a payload factory for tests.

    build(path, content=..., old=..., new=...) returns a tool_input dict that
    performs (or, for shell shapes, textually implies) a write to `path`. The
    coverage meta-test iterates SHAPES x guards so no future guard can ship covering
    only the shapes its author remembered."""

    def __init__(self, name, tool_name, kind, build):
        self.name = name
        self.tool_name = tool_name
        self.kind = kind  # "file" | "move" | "shell"
        self._build = build

    def build(self, path, content="x", old="OLD", new="NEW"):
        return self._build(path, content, old, new)

    def __repr__(self):
        return "Shape(%s)" % self.name


def _build_shapes():
    shapes = [
        Shape("native-write", "Write", "file",
              lambda p, c, o, n: {"file_path": p, "content": c}),
        Shape("native-edit", "Edit", "file",
              lambda p, c, o, n: {"file_path": p, "old_string": o, "new_string": n}),
        Shape("native-multiedit", "MultiEdit", "file",
              lambda p, c, o, n: {"file_path": p,
                                  "edits": [{"old_string": o, "new_string": n}]}),
        Shape("native-notebookedit", "NotebookEdit", "file",
              lambda p, c, o, n: {"notebook_path": p, "new_source": c}),
        Shape("bash", "Bash", "shell",
              lambda p, c, o, n: {"command": 'echo %s > "%s"' % (c, p)}),
    ]
    for i, prefix in enumerate(DC_PREFIXES):
        tag = "" if i == 0 else "-plugin"
        shapes.extend([
            Shape("dc-write-file%s" % tag, prefix + "write_file", "file",
                  lambda p, c, o, n: {"path": p, "content": c}),
            Shape("dc-write-file-filepath-arg%s" % tag, prefix + "write_file", "file",
                  lambda p, c, o, n: {"file_path": p, "content": c}),
            Shape("dc-edit-block%s" % tag, prefix + "edit_block", "file",
                  lambda p, c, o, n: {"file_path": p, "old_string": o,
                                      "new_string": n}),
            Shape("dc-move-file-dest%s" % tag, prefix + "move_file", "move",
                  lambda p, c, o, n: {"source": "C:/Users/Owner/other/src.tmp",
                                      "destination": p}),
            Shape("dc-move-file-source%s" % tag, prefix + "move_file", "move",
                  lambda p, c, o, n: {"source": p,
                                      "destination": "C:/Users/Owner/other/dst.tmp"}),
            Shape("dc-write-pdf%s" % tag, prefix + "write_pdf", "file",
                  lambda p, c, o, n: {"path": p, "content": c}),
            Shape("dc-start-process%s" % tag, prefix + "start_process", "shell",
                  lambda p, c, o, n: {"command": 'cmd /c echo %s > "%s"' % (c, p)}),
            Shape("dc-interact-with-process%s" % tag,
                  prefix + "interact_with_process", "shell",
                  lambda p, c, o, n: {"pid": 1,
                                      "input": "open(r'%s','w').write('%s')" % (p, c)}),
        ])
    return tuple(shapes)


SHAPES = _build_shapes()
