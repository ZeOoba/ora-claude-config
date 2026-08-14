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
missing enforcement, not a new policy.

WHY NOT AUTO-REPAIR (rejected design, 2026-08-14). "Normalize the rel targets after
an openpyxl write" was considered and REJECTED. openpyxl's damage is not limited to
the rel targets: sec 1c documents that its save also drops conditional formatting
("Conditional Formatting extension is not supported and will be removed"), and a
`data_only=True` round-trip flattens every formula in all 50 tabs to static values.
Repairing only the rel targets would make the file PARSE again while leaving Eric's
model silently gutted -- converting a loud failure that announces itself within the
hour into a silent one that survives into reporting. Prevent and detect; never repair.

WHAT IT GATES (target: the master workbook, matched by BASENAME):
  1. mcp__excel__*  -- DENY-BY-DEFAULT. That MCP server is openpyxl-backed, so every
     write tool it exposes produces exactly this corruption. Only an explicit
     read-class allowlist passes; a write tool added to that server later is blocked
     on arrival rather than silently permitted.
  2. Shell (Bash / DC start_process / DC interact_with_process) -- blocked when the
     command carries a PYTHON-WRITER marker AND a SAVE indicator AND names the
     workbook. Read-only openpyxl (the SANCTIONED primary read path in sec 1c, and
     structurally incapable of saving) carries no save indicator and passes. Excel
     COM (the sanctioned WRITE path) carries no python-writer marker and passes.
  3. Native/DC file tools -- Write/Edit/move/write_file aimed at the workbook.

MATCHED BY BASENAME, deliberately. The workbook is OneDrive-hosted and this machine
has TWO sync roots for the same tenant ("...Oxford Capital Partners" and the
"...(1)" variant -- see reference_memory_scope_fragmentation.md), plus per-worktree
WORKBOOK_PATH divergence (project_oxford-command-center_worktree_gotchas.md). An
absolute-path matcher would silently miss the same file reached by another root.

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
    from tool_call_paths import normalize_text, write_targets  # noqa: E402
    TOOL_PATHS_LOADED = True
except Exception:
    TOOL_PATHS_LOADED = False

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

# --- shell -------------------------------------------------------------------
# A python-level xlsx WRITER. Excel COM carries none of these, which is exactly how
# the sanctioned write path stays open without needing an explicit exemption.
WRITER_MARKERS = ("openpyxl", "xlsxwriter", "pyexcelerate", "to_excel",
                  "excelwriter")

# A SAVE/persist indicator. Read-only openpyxl (sec 1c's sanctioned read path)
# carries none of these.
SAVE_RE = re.compile(
    r"\.save\s*\(|\bsave_workbook\s*\(|\bto_excel\s*\(|\bsave_as\s*\(")

SHELL_TOOL_MARKERS = ("bash", "start_process", "interact_with_process")

SHELL_COMMAND_FIELDS = ("command", "cmd", "input", "script")


def workbook_name():
    return (os.environ.get("ORA_WORKBOOK_GUARD_NAME")
            or DEFAULT_WORKBOOK_NAME).strip().lower()


def _names_workbook(text):
    """True if `text` names the master workbook, under quote/caret normalization.

    UNION-ONLY normalization, same approach and same reasoning as
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
    return any(name in v for v in variants)


def _is_shell_tool(tool_name):
    lowered = (tool_name or "").lower()
    return any(marker in lowered for marker in SHELL_TOOL_MARKERS)


def _all_strings(obj, _depth=0):
    """Every string anywhere in a nested tool_input, with the key that carried it.

    REFUTE 2026-08-14 (adversarial pass on this hook's own first draft, which found
    three holes; this closes two of them). The excel MCP branch originally scanned a
    FIXED list of path-shaped field names at the TOP level only. Both assumptions
    failed under attack:
      * `{"workbook": <path>}`        -- a field name not on the list sailed through
      * `{"opts": {"filepath": ...}}` -- a nested path was never looked at
    A deny-by-default gate cannot depend on having guessed an external MCP server's
    schema correctly. Scanning every string at any depth removes the guess: the
    field name stops mattering, only whether the call names the workbook does.
    Depth-capped so a pathological payload cannot spin.
    """
    if _depth > 6:
        return
    if isinstance(obj, str):
        yield ("<value>", obj)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str):
                yield (str(key), value)
            else:
                for pair in _all_strings(value, _depth + 1):
                    yield pair
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            for pair in _all_strings(value, _depth + 1):
                yield pair


def _shell_text(tool_input):
    parts = []
    for field in SHELL_COMMAND_FIELDS:
        value = tool_input.get(field)
        if isinstance(value, str) and value:
            parts.append(value)
    return "\n".join(parts)


def _shell_writes_workbook(text):
    """(True, detail) when shell text is a python-writer save aimed at the workbook.

    NOTE: heredoc bodies are deliberately NOT stripped here, unlike
    config-write-guard.py. There a heredoc body is DATA being written into a file, so
    prose mentioning a governance path was a false positive. Here `python - <<'PY'`
    EXECUTES its body, so the save lives in the body and stripping it would blind the
    gate to the most natural way to write this exact call.
    """
    if not text:
        return (False, "")
    try:
        normalized = normalize_text(text) if TOOL_PATHS_LOADED else text
    except Exception:
        normalized = text
    lowered = normalized.lower()
    writer = next((m for m in WRITER_MARKERS if m in lowered), None)
    if not writer:
        return (False, "")
    if not SAVE_RE.search(lowered):
        return (False, "")
    if not _names_workbook(normalized):
        return (False, "")
    return (True, "python writer '%s' + save aimed at the master workbook" % writer)


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
        "and its save also strips conditional formatting and (with data_only=True)\n"
        "flattens every formula in all 50 tabs to static values. On 2026-08-13 this\n"
        "took down ora-lease-snapshot-refresh, ora-cc-snapshot-refresh, AND the hourly\n"
        "Command Center mirror deploy -- 9 consecutive failed runs, ~15h of a stale\n"
        "public mirror, surfacing only as `build:mirror failed (1)`.\n"
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
                if _names_workbook(raw):
                    hit = ("write-class excel MCP tool '%s' aimed at the ORA Master "
                           "Workbook (this MCP server is openpyxl-backed)" % suffix,
                           "%s (field '%s')" % (raw, field))
                    break

    # 2. Shell -- python writer + save + workbook.
    if hit is None and _is_shell_tool(tool_name):
        text = _shell_text(tool_input)
        writes, detail = _shell_writes_workbook(text)
        if writes:
            hit = (detail, "shell command via %s: %s"
                   % (tool_name, text.strip()[:200]))

    # 3. Native / DC file tools aimed at the workbook.
    if hit is None and TOOL_PATHS_LOADED and not _is_shell_tool(tool_name):
        try:
            targets = write_targets(tool_name, tool_input)
        except Exception:
            targets = []
        for target in targets:
            if _names_workbook(target.raw_path):
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
