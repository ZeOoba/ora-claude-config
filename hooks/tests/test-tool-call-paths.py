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


def test_refute_family_suffix_matching_and_new_shapes():
    """2026-07-18 REFUTE regressions at the lib layer."""
    # a THIRD DC prefix (renamed/re-registered connector) must still be recognized
    check("third-prefix write_file recognized",
          tcp.primary_write_path("mcp__desktop-commander-v2__write_file",
                                 {"path": P}) == P)
    check("third-prefix write_file yields targets",
          any(t.raw_path == P for t in
              tcp.write_targets("mcp__desktop-commander-v2__write_file",
                                {"path": P})))
    check("third-prefix start_process is a shell tool",
          tcp.shell_analysis("mcp__dc-v2__start_process",
                             {"command": "echo x > f"}) is not None)
    # write_pdf is a file-writing shape
    for prefix in DC_PREFIXES:
        t = tcp.write_targets(prefix + "write_pdf", {"path": P, "content": "x"})
        check("%swrite_pdf yields a write target" % prefix,
              len(t) == 1 and t[0].operation == "write")
    check("SHAPES includes dc-write-pdf",
          any("dc-write-pdf" in s.name for s in tcp.SHAPES))
    # file-rewriting git and PS item cmdlets read as writes
    for cmd in ("git -C ~/.claude checkout main -- hooks/",
                "git restore hooks/x.py",
                "Move-Item a.json b.json",
                "Copy-Item a.json b.json"):
        check("shell_may_write: %r" % cmd, tcp.shell_may_write(cmd))
    check("read-only git is not write-shaped",
          not tcp.shell_may_write("git -C ~/.claude log --oneline -- hooks/"))


def test_resolve_path_absolute_and_casefolded():
    r = tcp.resolve_path("C:/Users/Owner/.claude/HOOKS/x.py")
    check("resolve_path absolute", os.path.isabs(r))
    check("resolve_path case-normalized", r == os.path.normcase(r))


# ---------------------------------------------------------------- open() mode-awareness
# BUG (2026-07-21, oxford-command-center worktree session): "open(" was an
# unconditional write indicator regardless of mode -- `open(path, 'rb')` (an
# ordinary READ) tripped the same signal as `open(path, 'w')`. Only an
# UNAMBIGUOUS read-only call (no mode arg, or an explicit 'r'/'rb'/'rt' string
# literal, and nothing else) is exempt; anything else -- a write-mode literal, a
# variable/indirect mode, extra args, nested-paren arguments this module cannot
# cleanly parse -- stays flagged. Fail-toward-block on any unresolved shape,
# same posture as the rest of this module.
def test_shell_may_write_open_readonly_not_flagged():
    for label, cmd in [
        ("open(path,'rb') read", "open(r'C:/x/y.json','rb').read()"),
        ("open(path,'r') read", "open('C:/x/y.json','r').read()"),
        ("open(path,'rt') read", "open('C:/x/y.json','rt').read()"),
        ("open(path) no mode (defaults to read)", "open('C:/x/y.json').read()"),
    ]:
        check("%s -> not may_write" % label, not tcp.shell_may_write(cmd),
              "cmd=%r" % cmd)


def test_shell_may_write_open_write_modes_still_flagged():
    for label, cmd in [
        ("open(path,'w')", "open('C:/x/y.json','w').write('x')"),
        ("open(path,'wb')", "open('C:/x/y.json','wb').write(b'x')"),
        ("open(path,'a')", "open('C:/x/y.json','a').write('x')"),
        ("open(path,'x')", "open('C:/x/y.json','x').write('x')"),
        ("open(path,'r+')", "open('C:/x/y.json','r+').write('x')"),
    ]:
        check("%s -> may_write" % label, tcp.shell_may_write(cmd), "cmd=%r" % cmd)


def test_shell_may_write_open_indirect_or_unparseable_stays_flagged():
    # Fail-toward-block: any shape this module cannot cleanly resolve as an
    # unambiguous read must still read as a possible write -- same "honest
    # limit" posture as value indirection elsewhere in this module.
    for label, cmd in [
        ("mode via variable", "m = 'rb'\nopen('C:/x/y.json', m).read()"),
        ("nested-paren path arg", "open(os.path.join(a, 'y.json'), 'rb').read()"),
        ("extra keyword arg", "open('C:/x/y.json', 'rb', encoding='utf-8').read()"),
    ]:
        check("%s -> still may_write (unresolved)" % label,
              tcp.shell_may_write(cmd), "cmd=%r" % cmd)


def test_shell_may_write_open_readonly_does_not_mask_other_indicators():
    # The open()-mode carve-out must only suppress the "open(" signal itself --
    # a write indicator anywhere else in the same command must still fire.
    cmd = "open('C:/x/y.json','rb').read(); os.remove('C:/x/other.txt')"
    check("read-mode open + os.remove elsewhere -> still may_write",
          tcp.shell_may_write(cmd), "cmd=%r" % cmd)
    cmd2 = "echo hi > out.txt; open('C:/x/y.json','rb').read()"
    check("read-mode open + unrelated redirect -> still may_write",
          tcp.shell_may_write(cmd2), "cmd=%r" % cmd2)


def test_write_verbs_require_a_word_boundary():
    """A verb buried inside an unrelated word is not a write.

    Live cost of the bare-substring version (2026-08-03): "del " matched
    "--model ", so `eos-review-gate.py --record ... --model <id>` read as a
    write to the governance layer. config-write-guard then blocked the ONLY
    sanctioned way to satisfy eos-review-gate, and the documented exit was a
    60-minute governance-WIDE write token to permit one single-file write.
    A false positive that forces a strictly BROADER privilege is a security
    regression, not caution."""
    benign = [
        "python gate.py --record --verdict approved --model claude-fable-5",
        "git add -A",                       # "dd " inside "add "
        "git add hooks/x.py && git status",
        "echo please confirm the value",    # "rm " inside "confirm "
        "ls children/",                     # "ren " inside "children "
        "grep remodel notes.txt",           # "del " inside "remodel "
        "cat model.json",
        "python train.py --model resnet",
    ]
    for cmd in benign:
        check("benign not write-shaped: %r" % cmd,
              not tcp.shell_may_write(cmd), cmd)


def test_word_boundary_fix_loses_no_genuine_write():
    """THE regression that matters. Anchoring may not let a real write through.

    Every genuine verb still matches, because the character preceding it is
    never a word character -- start of string, whitespace, quote, slash, or a
    shell metacharacter. Judged as a DELTA against the old bare-substring
    behavior: the fix is only acceptable if this set is unchanged."""
    genuine = [
        "del C:/Users/Owner/.claude/hooks/eos-review-gate.py",
        "rm -rf hooks/",
        "rm hooks/x.py",
        "/usr/bin/rm hooks/x.py",
        "cp a.py hooks/b.py",
        "mv a.py hooks/b.py",
        "dd if=/dev/zero of=hooks/x.py",
        "mkdir newdir",
        "touch hooks/x.py",
        "tee hooks/x.py",
        "ren old.py new.py",
        "rename old.py new.py",
        "copy a.py b.py",
        "move a.py b.py",
        'echo x && del hooks/x.py',
        'true;rm hooks/x.py',
        'false||rm hooks/x.py',
        "sudo rm hooks/x.py",
        # non-verb indicators must be untouched by the anchoring change
        "echo x > hooks/x.py",
        "Remove-Item hooks/x.py",
        "Set-Content hooks/x.py",
        "python -c \"shutil.copy('a','b')\"",
        "python -c \"os.remove('hooks/x.py')\"",
        "sed -i s/a/b/ hooks/x.py",
    ]
    for cmd in genuine:
        check("genuine write still flagged: %r" % cmd,
              tcp.shell_may_write(cmd), cmd)


def test_composite_writers_containing_a_bounded_verb_are_still_flagged():
    """THE regression the hand-written corpus above missed (review finding D1).

    Real writers were caught only ACCIDENTALLY, as substrings of the short
    verbs: "copy " inside robocopy/xcopy, "cp " inside scp/rcp/pscp. Anchoring
    removed that accident and un-flagged every one of them -- and robocopy.EXE,
    xcopy.EXE and scp.EXE are all present on this machine, where
    `robocopy <src> <hooks> /MIR` MIRRORS: it deletes and replaces the whole
    target tree.

    Enumerated MECHANICALLY rather than remembered, because remembering is
    exactly what failed: the first battery listed only simple `rm`/`cp`/`dd`
    forms, so a green suite certified the regression."""
    real_command_names = [
        "robocopy", "xcopy", "scp", "rcp", "pscp", "rsync", "git-rm", "git-mv",
    ]
    for name in real_command_names:
        cmd = "%s src C:/Users/Owner/.claude/hooks/x.py" % name
        check("composite writer flagged: %r" % name, tcp.shell_may_write(cmd), cmd)

    # Every command name that CONTAINS a bounded verb must be consciously
    # classified -- either it is a real writer (flagged above) or a benign word
    # (unflagged below). A new bounded verb whose collision set is unexamined is
    # how D1 happened.
    for verb in tcp._BOUNDED_VERBS:
        containing = [n for n in real_command_names if verb in n]
        for name in containing:
            check("collision-set writer %r (contains %r) flagged" % (name, verb),
                  tcp.shell_may_write("%s a b" % name), name)


def test_anchoring_details_are_pinned():
    """The two most load-bearing characters in the regex, pinned directly.

    Mutation testing found both unobserved: dropping the trailing `\\s` and
    changing the lookbehind class each survived the original battery."""
    # trailing \s is required -- without it, ordinary words re-flag
    check("'copyright notice' is not a write", not tcp.shell_may_write("copyright notice"))
    check("'movement plan' is not a write", not tcp.shell_may_write("movement plan"))
    # lookbehind excludes '-' so the common benign docker flag is not a write...
    check("'docker run --rm img' is not a write",
          not tcp.shell_may_write("docker run --rm img"))
    # ...and the hyphenated writers that costs are covered explicitly instead
    check("'git-rm x' IS a write", tcp.shell_may_write("git-rm x"))
    # lookbehind does NOT exclude '.' or '/' -- these are real invocations
    check("'foo.rm x' IS a write", tcp.shell_may_write("foo.rm x"))
    check("'./cp a b' IS a write", tcp.shell_may_write("./cp a b"))
    check("'/usr/bin/rm x' IS a write", tcp.shell_may_write("/usr/bin/rm x"))


def test_indicator_partition_is_total():
    """Every canonical indicator must still be reachable by one of the two
    matchers. A verb added to SHELL_WRITE_INDICATORS but never classified would
    otherwise fall between them and silently stop being detected."""
    for ind in tcp.SHELL_WRITE_INDICATORS:
        bounded = ind.strip() in tcp._BOUNDED_VERBS
        in_unbounded = ind in tcp.UNBOUNDED_WRITE_INDICATORS
        check("indicator %r is classified exactly once" % ind,
              bounded != in_unbounded, "bounded=%s unbounded=%s" % (bounded, in_unbounded))


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
    test_refute_family_suffix_matching_and_new_shapes()
    test_resolve_path_absolute_and_casefolded()
    test_shell_may_write_open_readonly_not_flagged()
    test_shell_may_write_open_write_modes_still_flagged()
    test_shell_may_write_open_indirect_or_unparseable_stays_flagged()
    test_shell_may_write_open_readonly_does_not_mask_other_indicators()
    test_write_verbs_require_a_word_boundary()
    test_word_boundary_fix_loses_no_genuine_write()
    test_composite_writers_containing_a_bounded_verb_are_still_flagged()
    test_anchoring_details_are_pinned()
    test_indicator_partition_is_total()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures)))
        sys.exit(1)
    print("\nALL tool-call-paths tests passed.")
    sys.exit(0)
