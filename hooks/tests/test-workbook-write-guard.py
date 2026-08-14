"""Tests for workbook-write-guard.py -- the hard write-gate over the ORA Master
Workbook, enforcing the ratified openpyxl-write ban.

Written FIRST (TDD). Drives the real hook as a subprocess with real PreToolUse
payloads, isolated from the live machine via the documented TEST-SEAM env var:
  ORA_WORKBOOK_GUARD_NAME    -> stand-in for the master workbook's basename
  ORA_OVERRIDE_SESSIONS_DIR  -> temp stand-in for hooks/sessions (lib seam)

WHY THIS GUARD EXISTS (2026-08-13/14 incident). An openpyxl re-save of the master
workbook wrote ABSOLUTE comment relationship targets, which exceljs cannot parse.
That broke three downstream consumers -- ora-lease-snapshot-refresh, ora-cc-snapshot-
refresh, and the hourly Command Center mirror deploy (down 9 consecutive runs, ~15h,
surfacing only as `build:mirror failed (1)`). The ban on openpyxl WRITES was already
ratified 2026-08-03 in ora-master-workbook-ingest/SKILL.md sec 1c, but lived as prose
in one task's skill file where no other session would ever read it. This hook is the
enforcement that doctrine never had.

CONTRACT:
  * exit 2 + stderr == block; exit 0 == allow (PreToolUse convention -- exit 1 would
    be NON-blocking, see reference_pretooluse_vs_git_hook_exit_codes.md)
  * mcp__excel__* is DENY-BY-DEFAULT against the master workbook: only an explicit
    read-class allowlist passes, so a write tool added to that MCP later is blocked
    on arrival rather than silently permitted
  * openpyxl READS stay allowed -- read-only openpyxl is the SANCTIONED primary read
    path in sec 1c and is structurally incapable of saving. Only a save is blocked.
  * Excel COM stays allowed -- it is the sanctioned WRITE path
  * other workbooks are untouched; this guard is scoped to the master workbook only
  * any internal error fails OPEN (a bug here must never brick a session --
    cf. feedback_confidentiality_guard_selfdeadlock.md)

Run: python test-workbook-write-guard.py
Stdlib only. ASCII-only. Windows (`python`).
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(HOOKS_DIR, "workbook-write-guard.py")

# WHITE-BOX handle on the module (REFUTE round 3, third-review finding): round 3's
# own regression tests (test_variable_bound_save_path_blocks et al) drove the hook
# only as a black-box subprocess and asserted the OVERALL exit code. That let a real
# bug in `_resolve_identifier_literal` (the `r?` prefix sat INSIDE the capture group,
# so `\1` backreferenced "r'" instead of "'", making a lone r-prefixed assignment --
# the idiomatic Windows-path form -- resolve to NOTHING) survive self-testing
# entirely: the "should block" case passed via fail-toward-block, and the "should
# allow" case passed via an unrelated literal-clearing path, so the resolver's own
# return value was never actually checked. Importing the module directly lets these
# tests assert on `_resolve_identifier_literal`'s and `_arg_verdict`'s own return
# values, not just an externally-observable side effect that can pass for the wrong
# reason.
_spec = importlib.util.spec_from_file_location("workbook_write_guard", HOOK)
wwg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wwg)

SID = "test-session-0123456789abcdef"
WB_NAME = "Master Excel Template Company Wide -- Oxford.xlsx"
WB = ("C:\\Users\\Owner\\OneDrive - Oxford Capital Partners\\eric spreadsheets\\"
      + WB_NAME)
OTHER = ("C:\\Users\\Owner\\OneDrive - Oxford Capital Partners\\outputs\\"
         "2026-08-14_Scratch_v01.xlsx")

_failures = []
_SESSIONS = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("  " + detail if detail else ""))
        _failures.append(name)


def _sessions_dir():
    if not _SESSIONS:
        _SESSIONS.append(tempfile.mkdtemp(prefix="wwg-sess-"))
    return _SESSIONS[0]


def run(tool_name, tool_input, session_id=SID, raw=None, env_extra=None):
    """Drive the hook; return (exit_code, stderr)."""
    env = dict(os.environ)
    env["ORA_WORKBOOK_GUARD_NAME"] = WB_NAME
    env["ORA_OVERRIDE_SESSIONS_DIR"] = _sessions_dir()
    if env_extra:
        env.update(env_extra)
    payload = raw if raw is not None else json.dumps({
        "tool_name": tool_name,
        "tool_input": tool_input,
        "session_id": session_id,
    })
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=payload.encode("utf-8"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
    )
    return proc.returncode, proc.stderr.decode("utf-8", "replace")


def blocked(rc, err):
    return rc == 2 and bool(err.strip())


# ------------------------------------------------------------------ excel MCP
def test_excel_mcp_write_to_master_blocks():
    rc, err = run("mcp__excel__write_data_to_excel",
                  {"filepath": WB, "sheet_name": "Rent Roll", "data": [[1]]})
    check("excel MCP write_data_to_excel on master blocks", blocked(rc, err),
          repr(err[:200]))
    check("block message names the sanctioned Excel COM path",
          "excel com" in err.lower(), repr(err[:200]))


def test_excel_mcp_formula_write_blocks():
    rc, err = run("mcp__excel__apply_formula",
                  {"filepath": WB, "sheet_name": "S", "cell": "A1", "formula": "=1"})
    check("excel MCP apply_formula on master blocks", blocked(rc, err))


def test_excel_mcp_unknown_tool_denies_by_default():
    """A write tool added to the excel MCP later must be blocked on arrival."""
    rc, err = run("mcp__excel__some_future_write_tool", {"filepath": WB})
    check("unknown excel MCP tool on master denies by default", blocked(rc, err))


def test_excel_mcp_read_class_allowed():
    for tool in ("read_data_from_excel", "get_workbook_metadata", "get_merged_cells",
                 "get_data_validation_info", "validate_excel_range",
                 "validate_formula_syntax"):
        rc, err = run("mcp__excel__" + tool, {"filepath": WB})
        check("excel MCP %s on master allowed" % tool, rc == 0, repr(err[:160]))


def test_excel_mcp_undocumented_field_name_blocks():
    """REFUTE 2026-08-14 hole 1: a path under a field name not on any allowlist.

    The first draft scanned a FIXED list of path-shaped field names, so an excel MCP
    schema using any other spelling sailed straight through a deny-by-default gate.
    """
    rc, err = run("mcp__excel__write_data_to_excel", {"workbook": WB})
    check("excel MCP path under an undocumented field name blocks", blocked(rc, err),
          repr(err[:200]))


def test_excel_mcp_nested_path_blocks():
    """REFUTE 2026-08-14 hole 2: a path nested below the top level of tool_input."""
    rc, err = run("mcp__excel__write_data_to_excel", {"opts": {"filepath": WB}})
    check("excel MCP nested path blocks", blocked(rc, err), repr(err[:200]))
    rc, err = run("mcp__excel__write_data_to_excel", {"batch": [{"target": WB}]})
    check("excel MCP path nested in a list blocks", blocked(rc, err), repr(err[:200]))


def test_excel_mcp_tool_name_case_insensitive():
    """REFUTE 2026-08-14 hole 3: case-varied tool name bypassed a case-sensitive
    startswith. Defense in depth -- settings.json's matcher is case-sensitive too,
    but the gate must not depend on the router's casing to be correct."""
    rc, err = run("MCP__EXCEL__WRITE_DATA_TO_EXCEL", {"filepath": WB})
    check("case-varied excel MCP tool name still blocks", blocked(rc, err),
          repr(err[:200]))


def test_pandas_to_excel_blocks():
    """openpyxl is not the only python writer that produces this corruption."""
    rc, err = run("Bash", {"command": "python -c \"import pandas; "
                                      "df.to_excel(r'%s')\"" % WB})
    check("pandas to_excel on master blocks", blocked(rc, err), repr(err[:200]))


def test_dc_start_process_openpyxl_save_blocks():
    rc, err = run("mcp__Desktop_Commander__start_process",
                  {"command": "python -c \"import openpyxl; wb.save(r'%s')\"" % WB})
    check("DC start_process openpyxl save blocks", blocked(rc, err), repr(err[:200]))


def test_resolve_identifier_literal_actually_resolves():
    """WHITE-BOX (REFUTE round 3, third-review finding): asserts on
    `_resolve_identifier_literal`'s own return value, not an externally-observable
    side effect that can pass for the wrong reason (see the module-level comment on
    the `wwg` import for the exact bug this catches -- a lone r-prefixed assignment,
    the idiomatic Windows-path form, resolved to NOTHING before the fix)."""
    text = "p=r'%s'; wb.save(p)" % WB.lower().replace("\\", "/")
    resolved = wwg._resolve_identifier_literal(text, "p")
    check("r-prefixed single assignment actually resolves",
          resolved is not None and WB_NAME.lower() in resolved,
          repr(resolved))
    text_plain = "p='%s'; wb.save(p)" % WB.lower().replace("\\", "/")
    resolved_plain = wwg._resolve_identifier_literal(text_plain, "p")
    check("plain-quoted (no r-prefix) single assignment also resolves",
          resolved_plain is not None and WB_NAME.lower() in resolved_plain,
          repr(resolved_plain))


def test_resolve_identifier_literal_last_assignment_wins():
    """WHITE-BOX: two assignments to the same name -- resolution must use the LAST
    one (matching normal execution order), not silently span across both (the
    round-3 bug's second symptom: `r?` inside the capture group let the failed
    match on the first r-string bleed into matching across both statements)."""
    text = "p=r'%s'; p=r'%s'" % (OTHER.lower().replace("\\", "/"),
                                  WB.lower().replace("\\", "/"))
    resolved = wwg._resolve_identifier_literal(text, "p")
    check("double assignment resolves to the LAST (master) value",
          resolved is not None and WB_NAME.lower() in resolved
          and "scratch" not in resolved, repr(resolved))


def test_variable_bound_save_path_blocks():
    """REFUTE round 3, finding R1 (verified live against the first argument-scoped
    fix): binding the path to a variable once, then saving via the variable,
    defeated a check that only inspected the save call's OWN argument text."""
    rc, err = run("Bash", {"command": "python -c \"import openpyxl; p=r'%s'; "
                                      "wb=openpyxl.load_workbook(p); wb.save(p)\""
                                      % WB})
    check("p = master; wb.save(p) blocks", blocked(rc, err), repr(err[:200]))


def test_double_assignment_to_master_blocks():
    """REFUTE round 3, third-review finding: reproduces the reviewer's exact
    counter-example live end-to-end. Rebind `p` to an unrelated file, THEN to the
    master, then save via `p` -- the realistic accident shape (a script that writes
    an output file, rebinds the path variable, then saves the master)."""
    rc, err = run("Bash", {"command": "python -c \"import openpyxl; p=r'%s'; "
                                      "p=r'%s'; wb.save(p)\"" % (OTHER, WB)})
    check("p=other; p=master; wb.save(p) blocks (double assignment)",
          blocked(rc, err), repr(err[:200]))
    rc, err = run("Bash", {"command": "python -c \"import pandas as pd; "
                                      "p=r'%s'; p=r'%s'; w=pd.ExcelWriter(p); "
                                      "df.to_excel(w)\"" % (OTHER, WB)})
    check("ExcelWriter double assignment to master blocks", blocked(rc, err),
          repr(err[:200]))
    # Control: reversed order (master first, then rebound away) must ALLOW --
    # confirms this is genuinely tracking the LAST assignment, not just "the
    # workbook's name appears somewhere in the command" (which the outer
    # _names_workbook gate would also see here, but must not be what decides it).
    rc, err = run("Bash", {"command": "python -c \"import openpyxl; p=r'%s'; "
                                      "p=r'%s'; wb.save(p)\"" % (WB, OTHER)})
    check("p=master; p=other; wb.save(p) allowed (control, last wins)",
          rc == 0, repr(err[:200]))


def test_variable_bound_save_to_other_file_allowed():
    """The same mechanism must not fail-toward-block a variable bound to an
    UNRELATED file -- only resolving to the master should block."""
    rc, err = run("Bash", {"command": "python -c \"import openpyxl; p=r'%s'; "
                                      "wb=openpyxl.Workbook(); wb.save(p)\""
                                      % OTHER})
    check("p = other file; wb.save(p) allowed", rc == 0, repr(err[:160]))


def test_excelwriter_constructor_targeting_master_blocks():
    """REFUTE round 3, R1: pandas' ExcelWriter names its target at CONSTRUCTION,
    not at to_excel() -- the object handed to to_excel() is normally a writer,
    not a path, so the constructor call is the only place the real target
    appears in text."""
    rc, err = run("Bash", {"command": "python -c \"import pandas as pd; "
                                      "w=pd.ExcelWriter(r'%s'); "
                                      "df.to_excel(w,'S'); w.close()\"" % WB})
    check("ExcelWriter(master) constructor blocks", blocked(rc, err), repr(err[:200]))
    rc, err = run("Bash", {"command": "python -c \"import pandas as pd; "
                                      "pd.ExcelWriter(r'%s', mode='a', "
                                      "engine='openpyxl')\"" % WB})
    check("ExcelWriter(master, mode='a') append blocks", blocked(rc, err),
          repr(err[:200]))


def test_xlsxwriter_workbook_constructor_targeting_master_blocks():
    rc, err = run("Bash", {"command": "python -c \"import xlsxwriter; "
                                      "xlsxwriter.Workbook(r'%s').close()\"" % WB})
    check("xlsxwriter.Workbook(master).close() blocks", blocked(rc, err),
          repr(err[:200]))


def test_to_excel_with_unresolvable_writer_object_allowed():
    """A writer-OBJECT argument to to_excel() that this cannot trace to a literal
    (the ordinary case -- it's an object, not a path) must NOT fail toward block,
    or the round-2 read-master-write-elsewhere fix regresses for every real
    ExcelWriter usage pattern."""
    rc, err = run("Bash", {"command": "python -c \"import pandas as pd; "
                                      "pd.read_excel(r'%s'); w=make_writer(); "
                                      "df.to_excel(w)\"" % WB})
    check("to_excel(unresolvable writer var) allowed", rc == 0, repr(err[:160]))


def test_attribute_access_save_arg_fails_toward_block():
    """`wb.save(wb.path)` -- the argument is an attribute access, not a literal or
    a resolvable identifier. Not provably safe -> fails toward block."""
    rc, err = run("Bash", {"command": "python -c \"import openpyxl; "
                                      "wb=openpyxl.load_workbook(r'%s'); "
                                      "wb.save(wb.path)\"" % WB})
    check("wb.save(wb.path) fails toward block", blocked(rc, err), repr(err[:200]))


def test_read_master_write_other_literal_path_allowed():
    """REGRESSION GUARD for a bug caught in this session's own self-testing before
    it ever reached review: the round-3 fix's first pass had NO positive check for
    "this argument is a well-formed literal for some OTHER file" -- so a genuine
    save to a different file, once it failed the master-name check, fell all the
    way through to the unresolvable/fail-toward-block branch. This is the exact
    scenario round 2 was built to fix; it must stay fixed."""
    rc, err = run("Bash", {"command": "python -c \"import openpyxl; "
                                      "wb=openpyxl.load_workbook(r'%s', "
                                      "read_only=True); out=openpyxl.Workbook(); "
                                      "out.save(r'%s')\"" % (WB, OTHER)})
    check("read master, save other (literal path) allowed", rc == 0, repr(err[:200]))


def test_com_exemption_requires_real_invocation_phrase():
    """REFUTE round 3, finding R2 (verified live): the original COM exemption fired
    on any of 3 short words ANYWHERE in the command, so a plain copy or a real
    openpyxl save decorated with a trailing comment mentioning 'comobject' was
    exempted with no COM invocation present at all."""
    rc, err = run("Bash", {"command": "python -c \"import openpyxl; "
                                      "wb=openpyxl.load_workbook(r'%s'); "
                                      "wb.save(r'%s')\"  # comobject decoration"
                                      % (WB, WB)})
    check("openpyxl save + decorative 'comobject' comment still blocks",
          blocked(rc, err), repr(err[:200]))
    # A PURE copy/move command (no python writer marker either way) decorated with
    # the literal COM phrase is the documented, deliberately ACCEPTED residual (see
    # the hook's own _COM_INVOCATION_RE comment) -- closing it needs real command
    # parsing, not text matching. Pinned here as a KNOWN state, not asserted closed.
    rc, err = run("Bash", {"command": 'copy /Y t.xlsx "%s" # -ComObject '
                                      'Excel.Application' % WB})
    check("plain copy + decorative COM phrase: documented accepted residual "
          "(allowed)", rc == 0, repr(err[:200]))


def test_com_exemption_still_allows_real_com():
    rc, err = run("Bash", {"command": "powershell -NoProfile -Command "
                                      "\"$x=New-Object -ComObject "
                                      "Excel.Application; $wb=$x.Workbooks."
                                      "Open('%s'); $wb.Save(); $wb.Close()\""
                                      % WB})
    check("real Excel COM invocation still allowed", rc == 0, repr(err[:200]))


def test_documented_indirection_ceiling_is_allowed():
    """The HONEST LIMIT, pinned so it is a known state and not a silent surprise.

    Text matching cannot follow a path through a variable or a script file. These
    ALLOW, by construction. maintenance/workbook-integrity-probe.py is the detection
    half that covers this gap. If a future change makes these block, that is a real
    improvement -- update this test deliberately rather than deleting it.
    """
    rc, _ = run("Bash", {"command": "python -c \"import openpyxl,os; "
                                    "wb.save(os.environ['WORKBOOK_PATH'])\""})
    check("indirection via env var allowed (documented ceiling)", rc == 0)
    rc, _ = run("Bash", {"command": "python do_the_thing.py"})
    check("indirection via script file allowed (documented ceiling)", rc == 0)


def test_excel_mcp_write_to_other_workbook_allowed():
    rc, err = run("mcp__excel__write_data_to_excel",
                  {"filepath": OTHER, "sheet_name": "S", "data": [[1]]})
    check("excel MCP write to a DIFFERENT workbook allowed", rc == 0, repr(err[:160]))


# ------------------------------------------------------------------ shell / openpyxl
def test_shell_openpyxl_save_blocks():
    cmd = ('python -c "import openpyxl; wb=openpyxl.load_workbook(r\'%s\'); '
           'wb.save(r\'%s\')"' % (WB, WB))
    rc, err = run("Bash", {"command": cmd})
    check("Bash openpyxl .save() on master blocks", blocked(rc, err), repr(err[:200]))


def test_shell_openpyxl_readonly_allowed():
    """sec 1c's SANCTIONED primary read path must not be broken by this guard."""
    cmd = ('python -c "import openpyxl; '
           'wb=openpyxl.load_workbook(r\'%s\', data_only=True, read_only=True); '
           'print(len(wb.sheetnames))"' % WB)
    rc, err = run("Bash", {"command": cmd})
    check("Bash read-only openpyxl load on master ALLOWED", rc == 0, repr(err[:200]))


def test_shell_excel_com_write_allowed():
    """Excel COM is the sanctioned WRITE path -- must stay open."""
    cmd = ('powershell -NoProfile -Command "$x=New-Object -ComObject '
           'Excel.Application; $wb=$x.Workbooks.Open(\'%s\'); $wb.Save(); '
           '$wb.Close()"' % WB)
    rc, err = run("Bash", {"command": cmd})
    check("Bash Excel COM save on master ALLOWED", rc == 0, repr(err[:200]))


def test_shell_heredoc_openpyxl_save_blocks():
    cmd = ("python - <<'PY'\nimport openpyxl\n"
           "wb = openpyxl.load_workbook(r'%s')\nwb.save(r'%s')\nPY" % (WB, WB))
    rc, err = run("Bash", {"command": cmd})
    check("Bash heredoc openpyxl save on master blocks", blocked(rc, err),
          repr(err[:200]))


def test_shell_save_on_other_workbook_allowed():
    cmd = ('python -c "import openpyxl; wb=openpyxl.Workbook(); wb.save(r\'%s\')"'
           % OTHER)
    rc, err = run("Bash", {"command": cmd})
    check("Bash openpyxl save on a DIFFERENT workbook allowed", rc == 0,
          repr(err[:160]))


def test_shell_quote_split_path_still_blocks():
    """Quote-split defeats naive contiguous-path matching (cf. config-write-guard)."""
    cmd = ('python -c "import openpyxl; wb.save(\'C:/x/\'"Master Excel Template '
           'Company Wide -- Oxford.xlsx\')"')
    rc, err = run("Bash", {"command": cmd})
    check("quote-split workbook path with openpyxl save still blocks",
          blocked(rc, err), repr(err[:200]))


def test_case_insensitive_match_blocks():
    cmd = ('python -c "import openpyxl; wb.save(r\'C:/d/%s\')"' % WB_NAME.upper())
    rc, err = run("Bash", {"command": cmd})
    check("uppercase workbook name still blocks", blocked(rc, err), repr(err[:200]))


def test_shell_no_openpyxl_no_block():
    """A command naming the workbook without any writer is not this guard's business."""
    rc, err = run("Bash", {"command": 'ls -la "%s"' % WB})
    check("plain ls on master ALLOWED", rc == 0, repr(err[:160]))


# ------------------------------------------------------------------ file tools
def test_write_tool_on_master_blocks():
    rc, err = run("Write", {"file_path": WB, "content": "x"})
    check("Write tool targeting master blocks", blocked(rc, err), repr(err[:200]))


def test_read_tool_on_master_allowed():
    rc, err = run("Read", {"file_path": WB})
    check("Read tool on master ALLOWED", rc == 0, repr(err[:160]))


# ------------------------------------------------------------------ robustness
def test_fail_open_on_garbage_input():
    rc, err = run(None, None, raw="not json at all {{{")
    check("garbage payload fails OPEN", rc == 0, repr(err[:160]))
    rc, err = run(None, None, raw=json.dumps(["not", "a", "dict"]))
    check("non-dict payload fails OPEN", rc == 0, repr(err[:160]))


def test_missing_tool_input_fails_open():
    rc, err = run(None, None, raw=json.dumps({"tool_name": "Bash", "session_id": SID}))
    check("missing tool_input fails OPEN", rc == 0, repr(err[:160]))


def test_exit_code_is_never_one():
    """exit 1 is NON-blocking for PreToolUse -- it would silently disable the gate."""
    for tool, ti in (("mcp__excel__write_data_to_excel", {"filepath": WB}),
                     ("Bash", {"command": "echo hi"}),
                     ("Read", {"file_path": WB}),
                     ("Write", {"file_path": WB, "content": "x"})):
        rc, _ = run(tool, ti)
        check("exit code never 1 (%s)" % tool, rc in (0, 2), "rc=%r" % rc)


if __name__ == "__main__":
    test_excel_mcp_write_to_master_blocks()
    test_excel_mcp_formula_write_blocks()
    test_excel_mcp_unknown_tool_denies_by_default()
    test_excel_mcp_undocumented_field_name_blocks()
    test_excel_mcp_nested_path_blocks()
    test_excel_mcp_tool_name_case_insensitive()
    test_pandas_to_excel_blocks()
    test_dc_start_process_openpyxl_save_blocks()
    test_resolve_identifier_literal_actually_resolves()
    test_resolve_identifier_literal_last_assignment_wins()
    test_variable_bound_save_path_blocks()
    test_double_assignment_to_master_blocks()
    test_variable_bound_save_to_other_file_allowed()
    test_excelwriter_constructor_targeting_master_blocks()
    test_xlsxwriter_workbook_constructor_targeting_master_blocks()
    test_to_excel_with_unresolvable_writer_object_allowed()
    test_attribute_access_save_arg_fails_toward_block()
    test_read_master_write_other_literal_path_allowed()
    test_com_exemption_requires_real_invocation_phrase()
    test_com_exemption_still_allows_real_com()
    test_documented_indirection_ceiling_is_allowed()
    test_excel_mcp_read_class_allowed()
    test_excel_mcp_write_to_other_workbook_allowed()
    test_shell_openpyxl_save_blocks()
    test_shell_openpyxl_readonly_allowed()
    test_shell_excel_com_write_allowed()
    test_shell_heredoc_openpyxl_save_blocks()
    test_shell_save_on_other_workbook_allowed()
    test_shell_quote_split_path_still_blocks()
    test_case_insensitive_match_blocks()
    test_shell_no_openpyxl_no_block()
    test_write_tool_on_master_blocks()
    test_read_tool_on_master_allowed()
    test_fail_open_on_garbage_input()
    test_missing_tool_input_fails_open()
    test_exit_code_is_never_one()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures)))
        sys.exit(1)
    print("\nALL workbook-write-guard tests passed.")
    sys.exit(0)
