"""Tests for hooks/lib/tool_call_paths.py -- the shared tool-call -> write-target
normalization layer (2026-07-18, write-guard architecture hardening).

Written FIRST (TDD): each case encodes one tool-call shape a write-guard must be able
to see. The module's job is to make sure the NEXT guard cannot ship with the Desktop
Commander blind spot that memory-index-guard.py and registry-write-guard.py each
independently rediscovered on 2026-07-14.

Run: python test-tool-call-paths.py
Stdlib only. ASCII-only. Windows (`python`).
"""
import os
import sys

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))

import tool_call_paths as tcp  # noqa: E402

_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("  " + detail if detail else ""))
        _failures.append(name)


P = "C:/Users/Owner/.claude/hooks/example-target.py"
P2 = "C:/Users/Owner/somewhere/else.txt"

DC_PREFIXES = (
    "mcp__Desktop_Commander__",
    "mcp__plugin_desktop-commander_desktop-commander__",
)


# ---------------------------------------------------------------- primary_write_path
def test_primary_write_path_native():
    check("native Write file_path",
          tcp.primary_write_path("Write", {"file_path": P, "content": "x"}) == P)
    check("native Edit file_path",
          tcp.primary_write_path("Edit", {"file_path": P, "old_string": "a",
                                          "new_string": "b"}) == P)
    check("native MultiEdit file_path",
          tcp.primary_write_path("MultiEdit", {"file_path": P, "edits": []}) == P)
    check("NotebookEdit notebook_path",
          tcp.primary_write_path("NotebookEdit", {"notebook_path": P}) == P)


def test_primary_write_path_dc_write_file_both_prefixes_both_arg_names():
    for prefix in DC_PREFIXES:
        name = prefix + "write_file"
        # historical arg name #1: "path" (the live DC schema)
        check("%s path arg" % name,
              tcp.primary_write_path(name, {"path": P, "content": "x"}) == P)
        # historical arg name #2: "file_path" (older payload shape seen in transcripts)
        check("%s file_path arg" % name,
              tcp.primary_write_path(name, {"file_path": P, "content": "x"}) == P)


def test_primary_write_path_dc_edit_block_both_prefixes():
    for prefix in DC_PREFIXES:
        name = prefix + "edit_block"
        check("%s file_path arg" % name,
              tcp.primary_write_path(name, {"file_path": P, "old_string": "a",
                                            "new_string": "b"}) == P)
        check("%s path fallback arg" % name,
              tcp.primary_write_path(name, {"path": P, "old_string": "a",
                                            "new_string": "b"}) == P)


def test_primary_write_path_generic_fallback_preserves_legacy_behavior():
    # The two legacy guards applied `file_path or path` for ANY tool name. The lib must
    # preserve that for unknown/unlisted tools so the refactor is behavior-preserving.
    check("unknown tool file_path fallback",
          tcp.primary_write_path("SomeFutureTool", {"file_path": P}) == P)
    check("unknown tool path fallback",
          tcp.primary_write_path("SomeFutureTool", {"path": P}) == P)


def test_primary_write_path_rejects_garbage():
    check("non-string path -> None",
          tcp.primary_write_path("Write", {"file_path": 123}) is None)
    check("empty path -> None",
          tcp.primary_write_path("Write", {"file_path": ""}) is None)
    check("missing path -> None",
          tcp.primary_write_path("Write", {}) is None)
    check("non-dict tool_input -> None",
          tcp.primary_write_path("Write", "not-a-dict") is None)


# ---------------------------------------------------------------- write_targets
def test_write_targets_file_tools():
    t = tcp.write_targets("Write", {"file_path": P, "content": "x"})
    check("Write -> one target", len(t) == 1)
    check("Write target raw path", t and t[0].raw_path == P)
    check("Write target resolved absolute",
          t and os.path.isabs(t[0].path))
    check("Write target operation", t and t[0].operation == "write")

    t = tcp.write_targets("Edit", {"file_path": P, "old_string": "a", "new_string": "b"})
    check("Edit operation", t and t[0].operation == "edit")

    t = tcp.write_targets("NotebookEdit", {"notebook_path": P})
    check("NotebookEdit covered", len(t) == 1 and t[0].raw_path == P)


def test_write_targets_decoy_double_field():
    # A DC write_file payload carrying BOTH "file_path" (innocent decoy) and "path"
    # (the field the tool actually honors) must surface BOTH as targets -- a gate
    # checking only one is steerable onto the decoy.
    for prefix in DC_PREFIXES:
        name = prefix + "write_file"
        t = tcp.write_targets(name, {"file_path": P2, "path": P, "content": "x"})
        raws = {x.raw_path for x in t}
        check("%s double-field surfaces both paths" % name,
              raws == {P, P2}, "got %s" % raws)
    # while primary_write_path stays legacy-ordered (file_path first) for the
    # behavior-preserving refactor of the two 2026-07-14 guards
    check("primary_write_path keeps legacy file_path-first order",
          tcp.primary_write_path(DC_PREFIXES[0] + "write_file",
                                 {"file_path": P2, "path": P}) == P2)


def test_write_targets_dc_move_file():
    for prefix in DC_PREFIXES:
        name = prefix + "move_file"
        t = tcp.write_targets(name, {"source": P, "destination": P2})
        check("%s -> two targets" % name, len(t) == 2)
        ops = sorted(x.operation for x in t)
        check("%s ops move-source+move-dest" % name,
              ops == ["move-dest", "move-source"], "got %s" % ops)
        raws = {x.operation: x.raw_path for x in t}
        check("%s source mapping" % name, raws.get("move-source") == P)
        check("%s dest mapping" % name, raws.get("move-dest") == P2)


def test_write_targets_shell_tools_return_no_file_targets():
    # Shell commands are handled via shell_analysis(), not static path targets.
    check("Bash -> no file targets",
          tcp.write_targets("Bash", {"command": "echo hi"}) == [])
    for prefix in DC_PREFIXES:
        check("%sstart_process -> no file targets" % prefix,
              tcp.write_targets(prefix + "start_process", {"command": "echo hi"}) == [])


# ---------------------------------------------------------------- shell analysis
def test_shell_analysis_basic():
    a = tcp.shell_analysis("Bash", {"command": "echo x > out.txt"})
    check("Bash write redirect -> may_write", a is not None and a.may_write)
    check("shell analysis is flagged unresolved (never claims a safe static resolution)",
          a is not None and a.resolved is False)

    a = tcp.shell_analysis("Bash", {"command": "cat out.txt"})
    check("Bash pure read -> not may_write", a is not None and not a.may_write)

    # fd-duplication / null redirects are NOT writes (autonomy-gate precedent 2026-07-09/10)
    a = tcp.shell_analysis("Bash", {"command": "ls foo 2>&1"})
    check("2>&1 not a write", a is not None and not a.may_write)
    a = tcp.shell_analysis("Bash", {"command": "grep x foo 2>/dev/null"})
    check("2>/dev/null not a write", a is not None and not a.may_write)


def test_shell_analysis_dc_start_process_and_interact():
    for prefix in DC_PREFIXES:
        a = tcp.shell_analysis(prefix + "start_process",
                               {"command": "cmd /c copy a.txt b.txt"})
        check("%sstart_process copy -> may_write" % prefix,
              a is not None and a.may_write)
        # interact_with_process feeds text into a live REPL -- that text can write files
        a = tcp.shell_analysis(prefix + "interact_with_process",
                               {"pid": 123, "input": "open('x','w').write('hi')"})
        check("%sinteract_with_process open(...,'w') -> may_write" % prefix,
              a is not None and a.may_write)


def test_shell_analysis_non_shell_tool_is_none():
    check("Write is not a shell tool",
          tcp.shell_analysis("Write", {"file_path": P, "content": "x"}) is None)


def test_shell_analysis_unicode_evasion_folded():
    # ZWSP inserted into the redirect target must not hide the path from marker
    # matching done on normalize_text() output (autonomy-gate Round 3 precedent).
    cmd = "echo x > C:/Users/Owner/.claude/ho​oks/f.py"
    normalized = tcp.normalize_text(cmd)
    check("normalize_text strips zero-width chars", ".claude/hooks" in
          normalized.replace("\\", "/").lower())


# ---------------------------------------------------------------- coverage registry
def test_shapes_registry_enumerates_all_write_capable_shapes():
    names = {s.name for s in tcp.SHAPES}
    expected_fragments = [
        "native-write", "native-edit", "native-multiedit", "native-notebookedit",
        "dc-write-file", "dc-edit-block", "dc-move-file", "bash",
        "dc-start-process",
    ]
    for frag in expected_fragments:
        check("SHAPES includes %s*" % frag, any(frag in n for n in names),
              "have: %s" % sorted(names))
    # every shape must build a payload that round-trips through the module's own
    # extraction: file/move shapes must surface the target path; shell shapes must
    # surface may_write.
    for s in tcp.SHAPES:
        tool_input = s.build(P)
        if s.kind in ("file", "move"):
            targets = tcp.write_targets(s.tool_name, tool_input)
            check("shape %s round-trips its own path" % s.name,
                  any(t.raw_path == P for t in targets),
                  "targets=%s" % (targets,))
        else:
            a = tcp.shell_analysis(s.tool_name, tool_input)
            check("shape %s reads as a possible write" % s.name,
                  a is not None and a.may_write)
    # both DC prefixes must appear in the registry (the 2026-07-14 gap was partly
    # a prefix-coverage gap)
    tools = {s.tool_name for s in tcp.SHAPES}
    for prefix in DC_PREFIXES:
        check("SHAPES covers prefix %s" % prefix,
              any(t.startswith(prefix) for t in tools))


def test_is_write_capable():
    check("Write is write-capable", tcp.is_write_capable("Write"))
    check("Bash is write-capable", tcp.is_write_capable("Bash"))
    for prefix in DC_PREFIXES:
        for suffix in ("write_file", "edit_block", "move_file", "start_process"):
            check("%s%s is write-capable" % (prefix, suffix),
                  tcp.is_write_capable(prefix + suffix))
    check("Read is not write-capable", not tcp.is_write_capable("Read"))
    check("Glob is not write-capable", not tcp.is_write_capable("Glob"))


def test_resolve_path_absolute_and_casefolded():
    r = tcp.resolve_path("C:/Users/Owner/.claude/HOOKS/x.py")
    check("resolve_path absolute", os.path.isabs(r))
    check("resolve_path case-normalized", r == os.path.normcase(r))


if __name__ == "__main__":
    test_primary_write_path_native()
    test_primary_write_path_dc_write_file_both_prefixes_both_arg_names()
    test_primary_write_path_dc_edit_block_both_prefixes()
    test_primary_write_path_generic_fallback_preserves_legacy_behavior()
    test_primary_write_path_rejects_garbage()
    test_write_targets_file_tools()
    test_write_targets_decoy_double_field()
    test_write_targets_dc_move_file()
    test_write_targets_shell_tools_return_no_file_targets()
    test_shell_analysis_basic()
    test_shell_analysis_dc_start_process_and_interact()
    test_shell_analysis_non_shell_tool_is_none()
    test_shell_analysis_unicode_evasion_folded()
    test_shapes_registry_enumerates_all_write_capable_shapes()
    test_is_write_capable()
    test_resolve_path_absolute_and_casefolded()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures)))
        sys.exit(1)
    print("\nALL tool-call-paths tests passed.")
    sys.exit(0)
