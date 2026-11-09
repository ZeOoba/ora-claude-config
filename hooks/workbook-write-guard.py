"""ORA Master Workbook write-gate -- PreToolUse hook.

WHY (2026-08-13/14 incident). On 2026-08-13 at 19:11 ET something re-saved the ORA
Master Workbook with openpyxl. openpyxl writes worksheet comment relationships with
ABSOLUTE targets (`/xl/comments/comment1.xml`, Id="comments") where Excel writes them
RELATIVE (`../comments/comment1.xml`, `rId1`). exceljs's reconcile() keys on the
relative form, so the absolute lookup is `undefined` and `.comments` throws --
aborting the ENTIRE parse. Three downstream consumers broke:

  * ora-lease-snapshot-refresh          -> Exit 3, TypeError surfaced directly
  * ora-cc-snapshot-refresh             -> `npm run extract` fails the same way
  * ORA Command Center - Mirror Deploy  -> `npm run bake` fails, surfacing ONLY as
                                           `build:mirror failed (1)`. Down 9
                                           consecutive hourly runs (~15h) before the
                                           drift check caught it; the public mirror
                                           served stale data the whole time.

The ban this hook enforces was ALREADY RATIFIED on 2026-08-03 in
`scheduled-tasks/ora-master-workbook-ingest/SKILL.md` sec 1c:

    "WRITING to this workbook (any task, any reason): use Excel COM, never openpyxl."

It had no enforcement. It lived as prose inside ONE scheduled task's skill file --
a place no other session, and no ad-hoc Bash call, would ever read. This hook is the
missing enforcement, not a new policy. (A separate session independently identified
the actual writer as the openpyxl-backed `excel` MCP server, driven interactively --
not a script -- confirming the mcp__excel__* branch below is the primary vector.)

WHY NOT AUTO-REPAIR (rejected design, 2026-08-14). "Normalize the rel targets after
an openpyxl write" was considered and REJECTED. openpyxl's damage is not limited to
the rel targets: sec 1c documents that its save also drops conditional formatting,
and the actual incident stripped the CACHED VALUE of 14,711 of 14,715 formula cells
(only 4 survived) -- exceljs reads cached values, so had the rel-target crash not
existed the parse would have "succeeded" and published NULL for every rent, NOI,
debt-service and DSCR figure. The crash was protective. Repairing only the rel
targets would make the file PARSE again while leaving Eric's model silently gutted --
converting a loud failure that announces itself within the hour into a silent one
that survives into reporting. Prevent and detect; never repair.

WHAT IT GATES (target: the master workbook, matched by BASENAME):
  1. mcp__excel__*  -- DENY-BY-DEFAULT. That MCP server is openpyxl-backed
     (excel_mcp/data.py: load_workbook() -> wb.save()), so every write tool it
     exposes produces exactly this corruption. Only an explicit read-class allowlist
     passes; a write tool added to that server later is blocked on arrival rather
     than silently permitted. The whole payload is scanned recursively (any field
     name, any nesting depth) for a string naming the workbook -- see REFUTE notes
     below for why a fixed top-level field list was not enough.
  2. Shell (Bash / DC start_process / DC interact_with_process) -- blocked when the
     command (a) is not an Excel COM invocation, (b) names the workbook, and (c)
     either a save-shaped call's OWN arguments name the workbook, or the command
     text independently carries a mutating shell verb (copy/move/cp/robocopy/
     shutil.* etc, via the shared tool_call_paths.shell_may_write() battery). Read-
     only openpyxl (the SANCTIONED primary read path in sec 1c) and Excel COM (the
     sanctioned WRITE path) pass by construction -- see REFUTE notes for why the
     original "python-writer marker present" requirement was dropped.
  3. Native/DC file tools -- Write/Edit/MultiEdit/move/write_file aimed at the
     workbook, matched on BOTH the raw path text and its realpath-resolved form (see
     REFUTE notes on 8.3 short names).

MATCHED BY BASENAME, deliberately. The workbook is OneDrive-hosted and this machine
has TWO sync roots for the same tenant ("...Oxford Capital Partners" and the
"...(1)" variant -- see reference_memory_scope_fragmentation.md), plus per-worktree
WORKBOOK_PATH divergence (project_oxford-command-center_worktree_gotchas.md). An
absolute-path matcher would silently miss the same file reached by another root.

REFUTE 2026-08-14 (independent review, model-pinned per the ratified blast-radius
review doctrine). Three real bypasses were found and verified LIVE against this
file's first draft, all closed here:
  * B1, 8.3 SHORT-NAME BYPASS. Short-name generation is enabled on this volume:
    `C:\\...\\ONEDRI~1\\ERICSP~1\\MASTER~1.XLS` resolves to the real workbook via
    `os.path.exists()` while matching none of the literal-basename checks --
    verified live against the actual file. `os.path.realpath()` on Windows expands
    a short name to its long form for a path that already exists, which is exactly
    the mechanism `tool_call_paths.resolve_path()` already used for branch 3's
    `target.path` -- this closed the gap there by also matching `target.path`, not
    only `target.raw_path`, and added the same realpath-resolution to branches 1
    and 2 via `_short_name_basename()`.
  * B2, SHELL AND-BYPASS. Requiring a writer-marker (openpyxl/pandas/etc literally
    present in THIS command's text) AND a save call let the actual corrupting
    action through in the most natural way to trigger it: splitting the write
    across two `interact_with_process` REPL turns (`wb = openpyxl.load_workbook(..)`
    in turn 1, bare `wb.save(path)` with no marker text in turn 2), or a plain
    `copy`/`cp`/`Copy-Item`/`shutil.copy` onto the workbook, which needs no python
    writer marker at all. Fixed by dropping the marker requirement: a save-shaped
    call whose OWN arguments name the workbook blocks regardless of what wrote it,
    and `tool_call_paths.shell_may_write()` (the same mature, word-boundary-anchored
    copy/move/robocopy/shutil battery config-write-guard.py already trusts) is
    checked independently. An explicit COM exemption (`-comobject`/
    `excel.application`) replaces "absence of a writer marker" as the reason Excel
    COM still passes, since that absence is no longer load-bearing.
  * B3, settings.json MATCHER OMITTED MultiEdit. The hook's own file-tool branch
    already blocks MultiEdit targets; the harness just never routed them to it.
    Fixed in settings.json alongside this file.
  Two FALSE-POSITIVE classes were also found and fixed, both by making the shell
  branch ARGUMENT-SCOPED rather than whole-command-scoped: reading the master and
  writing a DIFFERENT file (`pd.read_excel(<master>); df.to_excel(<other>)`) no
  longer blocks, because `<other>`, not the master, sits inside the `to_excel(...)`
  call that actually writes; and prose merely DESCRIBING a save() call (e.g. a git
  commit message about this very hook) no longer blocks, for the same reason. A
  save-shaped call whose arguments cannot be cleanly isolated (nested parens) fails
  TOWARD block rather than silently clearing, mirroring `_open_may_write()`'s
  established posture in `tool_call_paths.py`. The excel-MCP branch also stopped
  scanning bulk spreadsheet PAYLOAD fields (`data`/`values`/`rows`/`cells`) for the
  workbook's name -- a data CELL happening to contain the workbook's own path as
  content (e.g. a provenance note) is not evidence of a write TARGET, and scanning
  it produced a false block on a write to an unrelated file.

REFUTE ROUND 3 (2026-08-14, second independent review of the round-2 fixes above --
same ratified doctrine, a fresh model-pinned reviewer with no knowledge of round 2's
reasoning). Found the round-2 argument-scoping fix, in closing the false-positive
class, had also reopened two real holes:
  * R1, VARIABLE-BOUND SAVE PATH. `_save_call_targets_workbook` checked only
    whether a save call's OWN argument text was a path LITERAL naming the
    workbook -- `p = r'<master>'; wb.save(p)` (bind once, save via the variable)
    cleared, because `p` alone names nothing. Also missed: `pd.ExcelWriter(path)`
    used as a context manager or held across `to_excel(writer, ...)` calls, and
    `xlsxwriter.Workbook(path).close()`, neither of which the call-shape battery
    even recognized. Fixed by splitting call shapes into DIRECT-PATH-ARGUMENT
    calls (`.save()`/`save_workbook()`/`save_as()`/`ExcelWriter()`/
    `xlsxwriter.Workbook()` -- the argument IS the target) and WRITER-OBJECT calls
    (`to_excel(writer, ...)` -- the argument is normally an object, not a path),
    plus `_resolve_identifier_literal()`: a bare-identifier argument to a direct-
    path call is traced to its last `ident = <literal>` assignment in the same
    command text; if that trace fails (assigned via a call, an f-string, method
    chaining, or the identifier was never assigned in this text at all -- the
    REPL-turn shape from B2) the call fails TOWARD BLOCK rather than clearing. A
    writer-object call's unresolvable identifier does NOT fail toward block,
    since that is the ordinary, overwhelmingly common shape and forcing it closed
    would reopen the exact false-positive round 2 fixed.
  * R2, COM EXEMPTION WAS A BARE SUBSTRING MATCH. The original exemption fired on
    any of three short words ("comobject", "excel.application", "-comobject")
    appearing ANYWHERE in the command text -- so `copy /Y t.xlsx <master> #
    comobject`, with no COM invocation at all, was exempted by a trailing
    decoration. Tightened to the actual PowerShell instantiation phrase
    (`-ComObject Excel.Application`, `_COM_INVOCATION_RE`) plus a belt-and-
    suspenders check that no python writer marker is ALSO present in the text (a
    genuine COM script never contains "openpyxl" etc). Residual, deliberately
    accepted: a command that is purely a copy/move (no writer marker either way)
    and separately contains the literal instantiation phrase as decoration would
    still clear -- closing that needs real command parsing, the same documented
    ceiling as everywhere else in this file.
  Both were verified LIVE with reproduction commands before and after the fix, not
  just reasoned about; the differential (blocked-before / allowed-after, now
  re-blocked) is what confirmed each was a genuine regression, not a false alarm.

EXIT CODES (reference_pretooluse_vs_git_hook_exit_codes.md -- PreToolUse family):
exit 0 = allow; exit 2 + stderr = block. NEVER exit 1 (non-blocking error: the tool
call would PROCEED, silently disabling the gate).

HONEST LIMITS, stated rather than papered over:
  * VALUE INDIRECTION. A script FILE that opens and saves the workbook
    (`python do_the_thing.py`) names neither a writer nor the workbook in the command
    text and is NOT caught. This is the same documented structural ceiling as
    ora-autonomy-gate.py and config-write-guard.py -- text matching cannot follow a
    path through a variable or a file. `maintenance/workbook-integrity-probe.py` is
    the DETECTION half that covers what prevention cannot; run it before parsing.
  * The excel MCP read allowlist is a point-in-time snapshot of that server's tool
    surface. Deny-by-default means drift costs a false BLOCK (a retry), never a
    silent hole -- the correct direction for a security gate.
  * Short-name resolution (`_short_name_basename`) only fires for a path that
    EXISTS on disk right now. A short-name path to a file that does not yet exist
    cannot be resolved this way -- an accepted residual, since a not-yet-existing
    workbook is not the corruption scenario this hook defends against.

FAIL OPEN on any internal error (whole body wrapped, exit 0). A bug in this hook must
never brick a session -- cf. feedback_confidentiality_guard_selfdeadlock.md, where a
fail-CLOSED guard with malformed input bricked Write/Edit/Bash machine-wide.

TEST SEAMS (env vars -- TEST ONLY, never set in settings.json or a scheduled task;
setting them in production would point a security gate at an attacker-chosen name,
same caveat as ORA_CONFIG_GUARD_ROOT / ORA_OVERRIDE_SESSIONS_DIR):
  ORA_WORKBOOK_GUARD_NAME, and the lib's ORA_OVERRIDE_SESSIONS_DIR.

Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import re
import sys

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))

# The canonical master workbook basename. Lower-cased at use.
DEFAULT_WORKBOOK_NAME = "Master Excel Template Company Wide -- Oxford.xlsx"

# Import posture mirrors config-write-guard.py exactly, and for the same reason
# (reference_pretooluse_vs_git_hook_exit_codes.md): letting an ImportError propagate
# would exit 1, which is NON-blocking and would silently disable this gate; a
# sys.exit(2) at import time would brick every tool call. Degrade to "no override
# exists" -- ungated calls still pass, every gated call blocks.
try:
    from override_tokens import Tier, describe_token, token_grants  # noqa: E402
except Exception:
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

    def describe_token(session_id, tier):
        return ("  <hooks/lib/override_tokens.py could not be imported -- no "
                "override can be honored; fix the module, do not mint a token>\n")

try:
    from tool_call_paths import normalize_text, shell_may_write, write_targets  # noqa: E402
    TOOL_PATHS_LOADED = True
except Exception:
    TOOL_PATHS_LOADED = False

    def shell_may_write(command):
        return False  # degrade: this signal is simply unavailable, not a false ALLOW
                       # for the whole hook -- the save-argument check below still runs

WORKBOOK_WRITE = Tier("allow-workbook-write", "workbook-write", 1800, single_use=True)

# --- excel MCP ---------------------------------------------------------------
EXCEL_MCP_PREFIX = "mcp__excel__"

# READ-CLASS ALLOWLIST. Everything else in the family is denied by default.
EXCEL_READ_TOOLS = frozenset((
    "read_data_from_excel",
    "get_workbook_metadata",
    "get_merged_cells",
    "get_data_validation_info",
    "validate_excel_range",
    "validate_formula_syntax",
))

# BULK PAYLOAD KEYS (REFUTE 2026-08-14, false-positive finding): spreadsheet CELL
# CONTENT is arbitrary user data, not a write-target field. Scanning it for the
# workbook's name treats "a cell happens to mention this file" as "this call writes
# this file" -- verified false-blocking a write to an UNRELATED workbook whose data
# payload merely cited the master's path. Only structural fields (filepath,
# sheet_name, cell, ...) determine the target.
EXCEL_MCP_PAYLOAD_KEYS = frozenset(("data", "values", "rows", "cells", "content",
                                    "row_data", "cell_data"))

# --- shell -------------------------------------------------------------------
# A python-level xlsx WRITER. Used to LABEL a block message, and (REFUTE round 3)
# as a belt-and-suspenders disqualifier for the COM exemption below.
WRITER_MARKERS = ("openpyxl", "xlsxwriter", "pyexcelerate", "to_excel",
                  "excelwriter")

# DIRECT-PATH-ARGUMENT call shapes: in every real API these five take the write
# target as their own argument -- .save(path), save_workbook(wb, path),
# save_as(path), ExcelWriter(path, ...), xlsxwriter.Workbook(path). A bare-
# identifier argument here (REFUTE round 3, R1) gets IDENTIFIER RESOLUTION
# (_resolve_identifier_literal) and, if unresolvable, FAILS TOWARD BLOCK -- see
# _arg_verdict.
_DIRECT_PATH_CALL_RE = re.compile(
    r"(?:\.save\s*\(|\bsave_workbook\s*\(|\bsave_as\s*\(|\bexcelwriter\s*\(|"
    r"\bxlsxwriter\.workbook\s*\()([^()]*)\)")

# WRITER-OBJECT call shape: pandas' `df.to_excel(writer, sheet_name=...)` takes an
# ExcelWriter OBJECT, not a path -- the real target was already named at that
# object's OWN construction site (a _DIRECT_PATH_CALL_RE match, above). An
# unresolvable identifier here is the NORMAL, overwhelmingly common case (the
# writer variable), so it does NOT fail toward block -- only a LITERAL path
# argument here (a less common but real to_excel(path) form) is checked.
_WRITER_OBJECT_CALL_RE = re.compile(r"\bto_excel\s*\(([^()]*)\)")

# Union of both, used only to detect "some save-shaped call exists" and to cross-
# check against the two call-shape regexes above for nested-parens detection.
SAVE_RE = re.compile(
    r"\.save\s*\(|\bsave_workbook\s*\(|\bto_excel\s*\(|\bsave_as\s*\(|"
    r"\bexcelwriter\s*\(|\bxlsxwriter\.workbook\s*\(")

# A bare python identifier -- used to detect when a save-shaped call's argument is
# a VARIABLE rather than a literal path, so it can be resolved (or, if it can't be,
# fail toward block). Deliberately ASCII/simple: real identifiers in this threat
# model are ordinary variable names (`p`, `wb`, `path`), not unicode.
_IDENT_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

# A well-formed quoted string literal, optionally r-prefixed -- deliberately NOT
# f-prefixed, since an f-string's interpolated content is not statically known and
# must stay unresolvable. Loose about what's between the quotes (up to and
# including a trailing kwarg like `, mode='a'`, which still ends in a quote char)
# by design: the workbook-name check above already inspected the FULL argument
# text, so by the time this runs, "is this some kind of quoted-argument shape" is
# all that's left to confirm before clearing it.
_STRING_LITERAL_RE = re.compile(r"^r?(['\"]).*\1$", re.DOTALL)


# WORK BOUND (2026-09-21). Every save-shaped call whose argument is a bare identifier
# used to rescan the WHOLE command for that identifier's assignment, so
# `wb.save(p); ` * N + <master name> was O(N * len): 64KB 10.4s, ~4x per doubling,
# on the shell path of every Bash call that names the workbook. Resolutions are now
# memoized per identifier (exact: same text, same ident, same answer), and a command
# needing more than _MAX_DISTINCT_IDENTIFIERS DISTINCT identifiers resolved fails
# TOWARD BLOCK -- the same (None, True) "unresolved" verdict a nested-paren save call
# already gets. Consequence for legitimate use: a command that names the master
# workbook AND holds >64 save-shaped calls with distinct bare-identifier arguments
# needs the allow-workbook-write token. Nothing that blocked before stops blocking.
_MAX_DISTINCT_IDENTIFIERS = 64


class _TooManyIdentifiers(Exception):
    pass


def _resolve_identifier_literal(lowered_text, ident, cache=None):
    """The literal string value of the LAST plain `ident = <quoted literal>`
    assignment in `lowered_text`, or None if `ident` is never assigned a plain
    literal there.

    REFUTE round 3, finding R1 (verified live): the first argument-scoped fix
    cleared `p = r'<master>'; wb.save(p)` because `p` is not itself the workbook's
    name -- the literal that IS the workbook's name sits in a SEPARATE assignment
    statement. This resolves the common single-hop case. None (unresolvable) is
    the caller's signal to fail toward block, not to clear -- an identifier this
    cannot trace to a literal (assigned via a function call, an f-string, method
    chaining, or not assigned at all in this text -- e.g. it came from a prior
    Desktop-Commander REPL turn, exactly the B2 shape) is NOT provably safe."""
    if not _IDENT_RE.match(ident):
        return None
    if cache is not None:
        if ident in cache:
            return cache[ident]
        if len(cache) >= _MAX_DISTINCT_IDENTIFIERS:
            raise _TooManyIdentifiers()
    # BUG (found by round-3's independent review, live-verified): `r?` sat INSIDE
    # the capture group, so for `p = r'...'` group 1 captured the two characters
    # "r'" and the closing `\1` backreference then demanded a literal "r'" to
    # terminate -- which never appears, so a lone r-prefixed assignment (the
    # idiomatic form for a Windows path, used throughout this very file) matched
    # ZERO times and silently fell through to fail-toward-block. Worse: with TWO
    # r-prefixed assignments to the same name, the failed match on the first
    # bled into matching across both statements, resolving to the WRONG (earlier)
    # assignment's value -- allowing `p=r'<other>'; p=r'<master>'; wb.save(p)`,
    # a genuine write to the master. `r?` must sit OUTSIDE the group so `\1` only
    # ever backreferences the bare quote character.
    pattern = re.compile(r"\b%s\s*=\s*r?(['\"])((?:(?!\1).)*)\1"
                         % re.escape(ident))
    matches = list(pattern.finditer(lowered_text))
    result = matches[-1].group(2) if matches else None  # last assignment wins
    if cache is not None:
        cache[ident] = result
    return result


def _arg_verdict(lowered_text, arg_text, strict, cache=None):
    """True/False/None for whether one save-shaped call's argument names the
    workbook. None means unresolvable -- the caller fails toward block ONLY when
    `strict` (a direct-path-argument call, e.g. .save()); a writer-object call
    (to_excel(writer_var, ...)) is not strict, since an unresolvable identifier
    there is normally just the writer object, not a path."""
    stripped = arg_text.strip()
    if _names_workbook(stripped):
        return True
    # BUG (caught in this session's own round-3 self-testing, before the fix ever
    # left the machine): with no positive check for "this argument is a WELL-FORMED
    # literal for some OTHER file," a genuine `.save(r'<other file>')` fell all the
    # way through to the final unresolvable/fail-toward-block branch below --
    # `_names_workbook` correctly says "not the master," but that alone is not
    # "provably some other identifiable literal," so the ordinary read-master-
    # write-elsewhere case (round 2's own headline false-positive fix) silently
    # regressed. `_STRING_LITERAL_RE` positively recognizes a quoted string
    # literal (optionally r-prefixed; an f-string is deliberately EXCLUDED, since
    # its interpolated content is not statically known) so it can be cleared here
    # instead of falling through.
    if _STRING_LITERAL_RE.match(stripped):
        return False
    first_token = stripped.split(",", 1)[0].strip()
    if _IDENT_RE.match(first_token):
        resolved = _resolve_identifier_literal(lowered_text, first_token, cache)
        if resolved is None:
            return None if strict else False
        return _names_workbook(resolved)
    if not stripped:
        return False  # a bare `.save()` mentioned in prose, e.g. a commit message
    return None if strict else False  # attribute access, concatenation, an
                                       # f-string, a function call, or anything
                                       # else not provably safe to clear


# Excel COM exemption. REFUTE round 3, finding R2 (verified live): the original
# exemption was "any of these three short words appears ANYWHERE in the command
# text", so a plain `copy /Y t.xlsx <master> # comobject` -- no COM invocation at
# all -- was exempted by a trailing decoration. Tightened to the actual PowerShell
# instantiation phrase, plus a belt-and-suspenders check that no python writer
# marker is ALSO present (a genuine COM script never contains "openpyxl" etc; an
# injected marker into an otherwise-real writer command is caught here even if the
# phrase match alone were spoofed). Residual, deliberately accepted: a command
# that is genuinely just a copy/move (carries no writer marker either way) and
# ALSO contains the literal instantiation phrase as pure decoration would still
# clear. Closing that fully needs real command parsing, not text matching -- the
# same documented ceiling as the rest of this file and its sibling guards.
_COM_INVOCATION_RE = re.compile(r"-comobject\s+['\"]?excel\.application['\"]?")

SHELL_TOOL_MARKERS = ("bash", "start_process", "interact_with_process",
                      "powershell", "run_in_terminal")  # 2026-11-09 egress-tool wiring

SHELL_COMMAND_FIELDS = ("command", "cmd", "input", "script")


def workbook_name():
    return (os.environ.get("ORA_WORKBOOK_GUARD_NAME")
            or DEFAULT_WORKBOOK_NAME).strip().lower()


# Drive-letter absolute path token, either slash style, stopping at whitespace or a
# quote -- used only to find CANDIDATES to realpath-resolve (short-name check), not
# as the primary name matcher. Deliberately permissive on internal characters (a
# short name has none of them anyway); the cost of an occasional non-path match is
# one wasted, harmless os.path.exists() check.
_WIN_ABS_PATH_RE = re.compile(r"[A-Za-z]:[\\/][^\s\"'<>|]*")


def _short_name_basename(candidate):
    """The basename of `candidate`'s REAL (long-form) path if it currently exists on
    disk, else None. See module docstring, REFUTE B1: os.path.realpath() expands a
    Windows 8.3 short name (MASTER~1.XLS) to its long form for a path that exists --
    the exact mechanism tool_call_paths.resolve_path() already relies on for native
    file-tool targets, extended here to the MCP and shell branches."""
    try:
        if not os.path.isabs(candidate):
            return None
        if not os.path.exists(candidate):
            return None
        return os.path.basename(os.path.realpath(candidate)).lower()
    except (OSError, ValueError, TypeError):
        return None


def _names_workbook(text):
    """True if `text` names the master workbook -- literally, under quote/caret
    normalization, OR via an absolute path token that resolves (through a Windows
    8.3 short name or a junction/symlink) to a file whose real basename matches.

    UNION-ONLY normalization for the literal check, same approach and reasoning as
    config-write-guard.py: each variant can only ADD a hit, never remove one, so no
    previously-caught command can become allowed. Quote-split (`'C:/x/'"Master
    ...xlsx"`) and cmd.exe caret-escape (`Mas^ter`) both defeat a naive contiguous
    substring match; the shell strips those characters before the filesystem ever
    sees the path.
    """
    if not text:
        return False
    name = workbook_name()
    lowered = text.replace("\\", "/").lower()
    variants = (
        lowered,
        lowered.replace('"', "").replace("'", ""),
        re.sub(r"\^(.)", r"\1", lowered),
        re.sub(r"\^(.)", r"\1", lowered.replace('"', "").replace("'", "")),
    )
    if any(name in v for v in variants):
        return True
    for token in _WIN_ABS_PATH_RE.findall(text):
        real_base = _short_name_basename(token)
        if real_base and name in real_base:
            return True
    return False


def _is_shell_tool(tool_name):
    lowered = (tool_name or "").lower()
    return any(marker in lowered for marker in SHELL_TOOL_MARKERS)


def _all_strings(obj, _depth=0, _key=None):
    """Every string anywhere in a nested tool_input, with the key that carried it --
    skipping bulk spreadsheet PAYLOAD values (see EXCEL_MCP_PAYLOAD_KEYS).

    REFUTE 2026-08-14 (adversarial pass on this hook's own first draft, which found
    three holes; this closes two of them). The excel MCP branch originally scanned a
    FIXED list of path-shaped field names at the TOP level only. Both assumptions
    failed under attack:
      * `{"workbook": <path>}`        -- a field name not on the list sailed through
      * `{"opts": {"filepath": ...}}` -- a nested path was never looked at
    A deny-by-default gate cannot depend on having guessed an external MCP server's
    schema correctly. Scanning every string at any depth removes the guess: the
    field name stops mattering, only whether the call names the workbook does.
    Depth-capped so a pathological payload cannot spin; a payload nesting this deep
    is implausible for a real spreadsheet-tool call, so the cap costs nothing real.
    """
    if _depth > 10:
        return
    if isinstance(_key, str) and _key.lower() in EXCEL_MCP_PAYLOAD_KEYS:
        return
    if isinstance(obj, str):
        yield (_key if isinstance(_key, str) else "<value>", obj)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            for pair in _all_strings(value, _depth + 1, key):
                yield pair
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            for pair in _all_strings(value, _depth + 1, _key):
                yield pair


def _shell_text(tool_input):
    parts = []
    for field in SHELL_COMMAND_FIELDS:
        value = tool_input.get(field)
        if isinstance(value, str) and value:
            parts.append(value)
        elif isinstance(value, (list, tuple)):
            parts.extend(v for v in value if isinstance(v, str) and v)
    return "\n".join(parts)


def _com_exempt(lowered_text):
    if not _COM_INVOCATION_RE.search(lowered_text):
        return False
    return not any(marker in lowered_text for marker in WRITER_MARKERS)


def _save_call_targets_workbook(lowered_text):
    """(verdict, unresolved) for whether a save-shaped call in `lowered_text` has ITS
    OWN arguments naming the workbook -- across BOTH call-shape classes (see
    _DIRECT_PATH_CALL_RE / _WRITER_OBJECT_CALL_RE, and _arg_verdict for the per-
    argument resolution rules).

    verdict is True/False/None (None = no save-shaped call present at all, OR every
    call's argument was itself unresolvable -- see below).
    unresolved is True when a save-shaped call exists but at least one instance
    could not be cleanly ISOLATED (nested parens) -- the caller must fail TOWARD
    block on that, mirroring tool_call_paths._open_may_write()'s established
    posture for the same non-nested-parens limitation. This is a DIFFERENT kind of
    "unresolved" than an unresolvable ARGUMENT VALUE (a bare identifier with no
    traceable literal) -- that case is folded into `verdict is None` via
    _arg_verdict returning None, since it means the same thing to the caller
    (fail toward block) but isn't a parse failure.

    ARGUMENT-SCOPED, not whole-command-scoped (REFUTE 2026-08-14, false-positive
    finding): `pd.read_excel(<master>); df.to_excel(<other>)` must not block --
    the workbook is the READ source, and `<other>`, not the master, sits inside the
    call that actually writes. A prose mention of ".save()" (e.g. a git commit
    message describing this very hook) has an EMPTY or unrelated argument list and
    also clears here, for the same reason.
    """
    total_save_shaped = len(SAVE_RE.findall(lowered_text))
    if total_save_shaped == 0:
        return (None, False)  # no save-shaped call at all
    direct_calls = list(_DIRECT_PATH_CALL_RE.finditer(lowered_text))
    writer_calls = list(_WRITER_OBJECT_CALL_RE.finditer(lowered_text))
    # BUG (caught in round-2 self-testing before this ever reached review): checking
    # `if not calls` FIRST treated a save call whose args are ENTIRELY nested parens
    # as "no save-shaped call present" instead of "unresolvable" -- silently
    # ALLOWING the exact case this was built to fail toward block on. Comparing
    # against total_save_shaped (computed above, before any early return) is what
    # actually detects that mismatch.
    if len(direct_calls) + len(writer_calls) != total_save_shaped:
        return (None, True)  # some call's args have nested parens -- unresolvable
    cache = {}
    try:
        verdicts = [_arg_verdict(lowered_text, m.group(1), True, cache)
                    for m in direct_calls]
        verdicts += [_arg_verdict(lowered_text, m.group(1), False, cache)
                     for m in writer_calls]
    except _TooManyIdentifiers:
        return (None, True)  # bounded work: fail toward block (see _MAX_DISTINCT_IDENTIFIERS)
    if any(v is True for v in verdicts):
        return (True, False)
    if any(v is None for v in verdicts):
        return (None, True)  # some argument unresolvable -- fail toward block
    return (False, False)


def _shell_writes_workbook(text):
    """(True, detail) when a shell command is a genuine, non-COM write aimed at the
    master workbook. See module docstring REFUTE notes (B2 + false-positive fixes)
    for the reasoning behind each branch below."""
    if not text:
        return (False, "")
    try:
        normalized = normalize_text(text) if TOOL_PATHS_LOADED else text
    except Exception:
        normalized = text
    lowered = normalized.lower()
    if _com_exempt(lowered):
        return (False, "")
    if not _names_workbook(normalized):
        return (False, "")

    verdict, unresolved = _save_call_targets_workbook(lowered)
    if unresolved:
        return (True, "save()-shaped call with an argument shape this cannot "
                      "cleanly isolate (nested parens), naming the master "
                      "workbook elsewhere in the command -- failing toward block")
    if verdict:
        writer = next((m for m in WRITER_MARKERS if m in lowered), None)
        return (True, "%s save() call targets the master workbook"
                % ("python writer '%s'" % writer if writer else "a"))

    # No save-shaped call targeted the workbook (or none exists at all). A mutating
    # shell verb that ISN'T a python save call -- copy/cp/robocopy/shutil.*/a
    # redirect, etc -- naming the workbook is still a real write path (REFUTE B2:
    # `copy /Y t.xlsx <master>`, `shutil.copy(..., <master>)`). Reuses the same
    # word-boundary-anchored battery config-write-guard.py already trusts.
    if TOOL_PATHS_LOADED and shell_may_write(_neutralize_quoted_heredoc_bodies(text)):
        return (True, "mutating shell command names the master workbook")

    return (False, "")


# The ONLY command shape whose `>` characters are exempted (see the function below):
#   [cd <path> &&] python[3][.exe] - <<'DELIM'  ...body...  DELIM        (and nothing else)
# The unquoted <path> excludes `#`: `cd #&& python - <<'EOF'` is a bash COMMENT, so no heredoc
# opens and the "body" lines run as shell (REFUTE 2026-10-13).
_PY_STDIN_HEREDOC_RE = re.compile(
    r"\A[ \t]*(?:cd[ \t]+(?:\"[^\"\n]*\"|'[^'\n]*'|[^\s;&|<>`$#]+)[ \t]*&&[ \t]*)?"
    r"(?:python3?|py)(?:\.exe)?[ \t]+-[ \t]*<<[ \t]*'([A-Za-z0-9_]+)'[ \t]*\r?\n"
    r"(.*)\n[ \t]*\1[ \t]*\r?\n?[ \t\r\n]*\Z", re.DOTALL)


def _neutralize_quoted_heredoc_bodies(text):
    """`text` with the `>` characters in the BODY of a lone `python - <<'DELIM'` heredoc
    replaced by spaces, ONLY when the whole command is exactly that one heredoc.

    The shared shell_may_write treats a bare `>` as a redirect (breadth over precision,
    deliberately, for the governance guards). In THIS guard that produced a false
    positive (2026-10-06): a python comparison (`if i>48`) inside a read-only openpyxl
    heredoc blocked the sanctioned read path. The body of a quoted-delimiter heredoc is
    literal text to the shell, so a `>` there is never a redirect.

    WHY SO NARROW. Two adversarial reviews REFUTED broader designs: judging `>` by
    whether the same line names the workbook (a target held in a variable, on the next
    line or in a glob slipped through), then a general heredoc scanner (an opener in a
    comment, a here-string `<<<`, an arithmetic `1<<'3'`, a partly quoted delimiter or
    a quote-count trick made the scanner believe a heredoc had opened when bash did not,
    blanking a real redirect on a later line). Recognising a heredoc inside arbitrary
    shell text needs a real shell parser. So this accepts exactly one shape, anchored at
    both ends, with no shell text outside the opener line and the body -- there is no
    later line for a mis-parse to hide a redirect on -- and refuses (returns `text`
    unchanged, i.e. the old block behavior) if any body line equals the delimiter, since
    bash would end the heredoc there and run what follows."""
    m = _PY_STDIN_HEREDOC_RE.match(text)
    if not m:
        return text
    delim = m.group(1)
    body = m.group(2)
    if any(ln.strip() == delim for ln in body.split("\n")):
        return text
    blanked = _blank_python_operator_gt(body)
    if blanked is None:
        return text
    return text[:m.start(2)] + blanked + text[m.end(2):]


def _blank_python_operator_gt(body):
    """`body` with every `>` that Python's tokenizer reports as an OPERATOR token
    (>, >=, >>, ->) replaced by a space; a `>` inside a string literal or comment is
    left alone. None if the body does not tokenize (caller then keeps the old
    behavior). Third adversarial review: blanking EVERY `>` in the body let a shell-out
    through (os.system('echo x > M'), subprocess.run('... > M', shell=True)) -- the
    redirect lives in a string that a shell later runs, so it must stay visible."""
    import io
    import tokenize
    lines = body.split("\n")
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(body + "\n").readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return None
    for tok in toks:
        if tok.type == tokenize.OP and ">" in tok.string:
            (r1, c1), (r2, c2) = tok.start, tok.end
            if r1 != r2 or r1 - 1 >= len(lines):
                return None
            ln = lines[r1 - 1]
            lines[r1 - 1] = ln[:c1] + tok.string.replace(">", " ") + ln[c2:]
    return "\n".join(lines)


def _block(reason, detail, session_id):
    sys.stderr.write(
        "BLOCKED (workbook-write-guard): %s\n"
        "  target: %s\n"
        "\n"
        "The ORA Master Workbook must never be written by openpyxl or any other\n"
        "python xlsx writer. This is RATIFIED doctrine (2026-08-03), not a new rule:\n"
        "  scheduled-tasks/ora-master-workbook-ingest/SKILL.md sec 1c --\n"
        "  \"WRITING to this workbook (any task, any reason): use Excel COM,\n"
        "   never openpyxl.\"\n"
        "\n"
        "WHY: openpyxl writes ABSOLUTE comment rel targets that exceljs cannot parse,\n"
        "and its save also strips conditional formatting and cached formula values.\n"
        "On 2026-08-13 this took down ora-lease-snapshot-refresh,\n"
        "ora-cc-snapshot-refresh, AND the hourly Command Center mirror deploy -- 9\n"
        "consecutive failed runs, ~15h of a stale public mirror, surfacing only as\n"
        "`build:mirror failed (1)`.\n"
        "\n"
        "SANCTIONED PATHS:\n"
        "  * READ  -- read-only openpyxl is fine and is the PRIMARY read path:\n"
        "             openpyxl.load_workbook(path, data_only=True, read_only=True)\n"
        "             (it never saves, so it is structurally safe). Or the excel MCP\n"
        "             read tools, or mcp__excel__get_workbook_metadata.\n"
        "  * WRITE -- Excel COM only. Back up first, then diff against the backup:\n"
        "             the workbook is OneDrive-hosted, so AutoSave can persist a cell\n"
        "             before an error path can roll it back (sec 1c).\n"
        "\n"
        "If the workbook is ALREADY broken, do not hand-repair the XML -- open it in\n"
        "Excel and re-save; that restores relative rels. Verify with\n"
        "  python maintenance/workbook-integrity-probe.py\n"
        "\n"
        "If Gabriel has explicitly approved this specific write, mint this token and\n"
        "retry:\n%s"
        % (reason, detail, describe_token(session_id, WORKBOOK_WRITE)))
    sys.exit(2)


def main():
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    if not isinstance(payload, dict):
        return
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input")
    session_id = payload.get("session_id")
    if not isinstance(session_id, str):
        session_id = ""
    if not isinstance(tool_input, dict):
        return  # nothing inspectable -> status quo, allow

    hit = None  # (reason, detail)

    # 1. excel MCP -- deny-by-default against the master workbook.
    # Tool-name comparison is CASE-INSENSITIVE (REFUTE 2026-08-14, third hole found:
    # a case-varied `MCP__EXCEL__WRITE_DATA_TO_EXCEL` slipped past a case-sensitive
    # startswith). settings.json's matcher is itself case-sensitive so this is
    # defense in depth rather than the only line, but a gate should not depend on
    # the router's casing behavior to be correct.
    lowered_tool = tool_name.lower()
    if lowered_tool.startswith(EXCEL_MCP_PREFIX):
        suffix = lowered_tool[len(EXCEL_MCP_PREFIX):]
        if suffix not in EXCEL_READ_TOOLS:
            for field, raw in _all_strings(tool_input):
                try:
                    candidate = normalize_text(raw) if TOOL_PATHS_LOADED else raw
                except Exception:
                    candidate = raw
                if _names_workbook(candidate):
                    hit = ("write-class excel MCP tool '%s' aimed at the ORA Master "
                           "Workbook (this MCP server is openpyxl-backed)" % suffix,
                           "%s (field '%s')" % (raw, field))
                    break

    # 2. Shell -- see _shell_writes_workbook for the full ruleset.
    if hit is None and _is_shell_tool(tool_name):
        text = _shell_text(tool_input)
        writes, detail = _shell_writes_workbook(text)
        if writes:
            hit = (detail, "shell command via %s: %s"
                   % (tool_name, text.strip()[:200]))

    # 3. Native / DC file tools aimed at the workbook -- matched on BOTH the raw
    # path text and its realpath-resolved form (REFUTE B1: a Windows 8.3 short name
    # like MASTER~1.XLS matches neither the workbook's literal name nor any of
    # _names_workbook's quote/caret variants, but write_targets() already hands us
    # `target.path`, pre-resolved via tool_call_paths.resolve_path() -- realpath,
    # which expands short names for a path that exists. The original draft threw
    # that resolved form away and matched only raw_path; matching both closes it).
    if hit is None and TOOL_PATHS_LOADED and not _is_shell_tool(tool_name):
        try:
            targets = write_targets(tool_name, tool_input)
        except Exception:
            targets = []
        for target in targets:
            if _names_workbook(target.raw_path) or (
                    target.path and workbook_name() in
                    os.path.basename(target.path).lower()):
                hit = ("file-tool write aimed at the ORA Master Workbook",
                       "%s (%s via %s)" % (target.raw_path, target.operation,
                                           tool_name))
                break

    if hit is None:
        return

    # token_grants CONSUMES a single-use token, so it is evaluated only once, and
    # only after we know a block would otherwise fire.
    if token_grants(session_id, WORKBOOK_WRITE) is None:
        _block(hit[0], hit[1], session_id)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise  # a real block (exit 2) must propagate
    except Exception:
        pass  # FAIL OPEN: an internal bug must never block a tool call
    sys.exit(0)
