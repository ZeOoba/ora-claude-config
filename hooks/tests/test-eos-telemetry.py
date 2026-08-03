"""Tests for eos-telemetry.py SessionEnd hook.

Run: python test-eos-telemetry.py
Stdlib only. ASCII-only. Self-contained (creates its own temp dirs/files).
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/ (test in hooks/tests/)
HOOK = os.path.join(HERE, "eos-telemetry.py")


def run_hook(stdin_text, telemetry_dir, sessions_dir=None):
    """Run the hook as a subprocess. Returns (returncode, stdout, stderr)."""
    env = dict(os.environ)
    env["EOS_TELEMETRY_DIR"] = telemetry_dir
    if sessions_dir is not None:
        env["EOS_SESSIONS_DIR"] = sessions_dir
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=stdin_text,
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def make_transcript(path):
    """Write a fake JSONL transcript with an Edit, a Bash 'npm run gate',
    an Agent tool_use, and an assistant text line containing 'Dispatch: Inline'."""
    lines = [
        # assistant message with a tool_use Edit
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Edit",
                        "input": {"file_path": "C:/proj/foo.py"},
                    }
                ],
            },
        },
        # assistant message with a Bash tool_use running the gate
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "npm run gate"},
                    }
                ],
            },
        },
        # assistant message dispatching a subagent. The tool is named
        # "Agent" -- "Task" has never appeared in any real transcript, so a
        # fixture built on that name certifies a dead branch.
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Agent",
                        "input": {"description": "do thing"},
                    }
                ],
            },
        },
        # assistant text line with a lane declaration
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Dispatch: Inline - claude-opus-4-8"}
                ],
            },
        },
        # a deliberately malformed line should be skipped, not crash
        "this is not json at all",
    ]
    with open(path, "w", encoding="ascii") as fh:
        for ln in lines:
            if isinstance(ln, str):
                fh.write(ln + "\n")
            else:
                fh.write(json.dumps(ln) + "\n")


def test_happy_path():
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    transcript = os.path.join(tmp, "transcript.jsonl")
    tele_dir = os.path.join(tmp, "telemetry")
    make_transcript(transcript)

    stdin = json.dumps({"session_id": "test123", "transcript_path": transcript})
    rc, out, err = run_hook(stdin, tele_dir)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)

    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    assert os.path.exists(out_file), "telemetry file was not created"
    with open(out_file, "r", encoding="ascii") as fh:
        data_lines = [l for l in fh.read().splitlines() if l.strip()]
    assert len(data_lines) == 1, "expected exactly 1 line, got %d" % len(data_lines)

    rec = json.loads(data_lines[0])
    assert rec["session_id"] == "test123", rec
    assert rec["edits"] >= 1, rec
    assert rec["bash_test_ran"] is True, rec
    assert rec["task_dispatched"] is True, rec
    assert rec["lane_declared"] is True, rec
    assert "C:/proj/foo.py" in rec["files"], rec
    print("PASS test_happy_path")


def test_record_carries_schema_and_detectors():
    """Every emitted record must self-describe its detection capability.

    `ts` presence is only a PROXY for "this emitter could see subagent
    dispatch". A regressed DISPATCH_TOOLS that still stamped `ts` would be
    silently trusted by the rollup and report a wrongly-low dispatch rate --
    the exact failure the 2026-07-24 fix was written to stop. The schema
    version plus a detectors block derived from the LIVE constant make that
    regression self-reporting instead of invisible."""
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    transcript = os.path.join(tmp, "transcript.jsonl")
    tele_dir = os.path.join(tmp, "telemetry")
    make_transcript(transcript)

    stdin = json.dumps({"session_id": "schema-test", "transcript_path": transcript})
    rc, out, err = run_hook(stdin, tele_dir)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)

    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    with open(out_file, "r", encoding="ascii") as fh:
        rec = json.loads(fh.read().splitlines()[-1])

    assert rec.get("schema") == 2, "expected schema version 2, got %r" % rec.get("schema")
    detectors = rec.get("detectors")
    assert isinstance(detectors, dict), "expected a detectors dict, got %r" % detectors
    dispatch = detectors.get("dispatch")
    assert isinstance(dispatch, list), "expected detectors.dispatch list, got %r" % dispatch
    assert "Agent" in dispatch, (
        "detectors.dispatch must advertise the real subagent tool name: %r" % dispatch
    )
    print("PASS test_record_carries_schema_and_detectors")


def test_detectors_are_derived_from_live_constant():
    """The detectors block must be DERIVED from DISPATCH_TOOLS, not a
    hand-maintained literal. A literal would keep advertising "Agent" after
    the constant regressed, defeating the whole mechanism."""
    with open(HOOK, "r", encoding="ascii") as fh:
        src = fh.read()
    assert "sorted(DISPATCH_TOOLS)" in src, (
        "detectors.dispatch must be computed from DISPATCH_TOOLS, not hardcoded"
    )
    print("PASS test_detectors_are_derived_from_live_constant")


def test_malformed_stdin_fails_open():
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    tele_dir = os.path.join(tmp, "telemetry")
    rc, out, err = run_hook("not json", tele_dir)
    assert rc == 0, "malformed stdin must exit 0, got %s" % rc
    assert out == "", "expected no stdout, got %r" % out
    print("PASS test_malformed_stdin_fails_open")


def test_empty_object_fails_open():
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    tele_dir = os.path.join(tmp, "telemetry")
    rc, out, err = run_hook(json.dumps({}), tele_dir)
    assert rc == 0, "empty object must exit 0, got %s" % rc
    print("PASS test_empty_object_fails_open")


def test_missing_transcript_fails_open():
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    tele_dir = os.path.join(tmp, "telemetry")
    stdin = json.dumps(
        {"session_id": "x", "transcript_path": os.path.join(tmp, "nope.jsonl")}
    )
    rc, out, err = run_hook(stdin, tele_dir)
    assert rc == 0, "missing transcript must exit 0, got %s" % rc
    # No code activity / unreadable -> nothing written
    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    assert not os.path.exists(out_file) or os.path.getsize(out_file) == 0, (
        "should not write telemetry for missing transcript"
    )
    print("PASS test_missing_transcript_fails_open")


def test_no_code_activity_skipped():
    """A transcript with only text (no edits, no bash test, no task) writes nothing."""
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    transcript = os.path.join(tmp, "t.jsonl")
    tele_dir = os.path.join(tmp, "telemetry")
    with open(transcript, "w", encoding="ascii") as fh:
        fh.write(
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "hello there"}],
                    },
                }
            )
            + "\n"
        )
    stdin = json.dumps({"session_id": "y", "transcript_path": transcript})
    rc, out, err = run_hook(stdin, tele_dir)
    assert rc == 0, rc
    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    assert not os.path.exists(out_file) or os.path.getsize(out_file) == 0, (
        "non-coding session should write nothing"
    )
    print("PASS test_no_code_activity_skipped")


def test_task_management_tools_are_not_dispatch():
    """TaskCreate/TaskUpdate/TaskList are todo-management tools, NOT subagent
    dispatch. A prefix or substring match on "Task" would silently inflate
    task_dispatched with todo churn -- detection must be exact-match."""
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    transcript = os.path.join(tmp, "t.jsonl")
    tele_dir = os.path.join(tmp, "telemetry")
    lines = [
        # one real edit so the session still qualifies as a coding session
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Edit",
                        "input": {"file_path": "C:/proj/bar.py"},
                    }
                ],
            },
        },
    ]
    # Real Task* management tools, plus two synthetic names that are proper
    # SUBSTRINGS of "Agent". The latter pin exact-match semantics regardless of
    # container type: if DISPATCH_TOOLS ever degrades to a bare string, `tname
    # in DISPATCH_TOOLS` becomes substring containment and these two match.
    for tool in ("TaskCreate", "TaskUpdate", "TaskList", "TaskGet",
                 "TaskOutput", "TaskStop", "Age", "gen"):
        lines.append(
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "name": tool, "input": {}}
                    ],
                },
            }
        )
    with open(transcript, "w", encoding="ascii") as fh:
        for ln in lines:
            fh.write(json.dumps(ln) + "\n")

    stdin = json.dumps({"session_id": "task-mgmt", "transcript_path": transcript})
    rc, out, err = run_hook(stdin, tele_dir)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)

    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    with open(out_file, "r", encoding="ascii") as fh:
        rec = json.loads(fh.read().splitlines()[-1])
    assert rec["task_dispatched"] is False, (
        "Task* management tools must NOT count as subagent dispatch: %r" % rec
    )
    print("PASS test_task_management_tools_are_not_dispatch")


def test_unchanged_re_emission_is_skipped():
    """SessionEnd fires on every resume/clear/compaction, and each fire
    re-parses the WHOLE transcript. When nothing changed between fires the
    second record is byte-identical noise -- 67% of the 569 duplicate records
    on the live file were exactly this. Firing twice on an unchanged
    transcript must leave ONE line."""
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    transcript = os.path.join(tmp, "transcript.jsonl")
    tele_dir = os.path.join(tmp, "telemetry")
    make_transcript(transcript)
    stdin = json.dumps({"session_id": "dup1", "transcript_path": transcript})

    for _ in range(3):
        rc, out, err = run_hook(stdin, tele_dir)
        assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)

    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    with open(out_file, "r", encoding="ascii") as fh:
        lines = [l for l in fh.read().splitlines() if l.strip()]
    assert len(lines) == 1, (
        "3 fires on an unchanged transcript must write 1 record, got %d" % len(lines)
    )
    print("PASS test_unchanged_re_emission_is_skipped")


def test_changed_transcript_still_appends():
    """The skip must be driven by CONTENT, never by 'have I written before'.
    When the transcript genuinely grew, the new observation has to be
    recorded -- suppressing it would lose the signal the hook exists for."""
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    transcript = os.path.join(tmp, "transcript.jsonl")
    tele_dir = os.path.join(tmp, "telemetry")
    make_transcript(transcript)
    stdin = json.dumps({"session_id": "grow1", "transcript_path": transcript})

    rc, out, err = run_hook(stdin, tele_dir)
    assert rc == 0, err
    # the session continues: another edit lands, then SessionEnd fires again
    with open(transcript, "a", encoding="ascii") as fh:
        fh.write(json.dumps({
            "type": "assistant",
            "message": {"role": "assistant", "content": [
                {"type": "tool_use", "name": "Edit",
                 "input": {"file_path": "C:/proj/second.py"}}]},
        }) + "\n")
    rc, out, err = run_hook(stdin, tele_dir)
    assert rc == 0, err

    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    with open(out_file, "r", encoding="ascii") as fh:
        lines = [l for l in fh.read().splitlines() if l.strip()]
    assert len(lines) == 2, (
        "a grown transcript must append a fresh record, got %d line(s)" % len(lines)
    )
    first, second = json.loads(lines[0]), json.loads(lines[1])
    assert second["edits"] > first["edits"], (first, second)
    assert "C:/proj/second.py" in second["files"], second
    print("PASS test_changed_transcript_still_appends")


def test_skip_compares_only_this_session():
    """The comparison must key on session_id. Another session writing an
    identical-looking record in between must not suppress ours, and ours
    must not suppress theirs -- 7+ sessions interleave in this file."""
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    transcript = os.path.join(tmp, "transcript.jsonl")
    tele_dir = os.path.join(tmp, "telemetry")
    make_transcript(transcript)

    rc, _, err = run_hook(
        json.dumps({"session_id": "sA", "transcript_path": transcript}), tele_dir)
    assert rc == 0, err
    rc, _, err = run_hook(
        json.dumps({"session_id": "sB", "transcript_path": transcript}), tele_dir)
    assert rc == 0, err

    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    with open(out_file, "r", encoding="ascii") as fh:
        lines = [l for l in fh.read().splitlines() if l.strip()]
    assert len(lines) == 2, (
        "two DIFFERENT sessions must each get a record, got %d" % len(lines)
    )
    assert {json.loads(l)["session_id"] for l in lines} == {"sA", "sB"}, lines
    print("PASS test_skip_compares_only_this_session")


def test_skip_ignores_interleaved_other_sessions():
    """Our previous record is not necessarily the LAST line -- other sessions
    append after it. Scanning only the tail would miss it and duplicate."""
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    transcript = os.path.join(tmp, "transcript.jsonl")
    tele_dir = os.path.join(tmp, "telemetry")
    make_transcript(transcript)
    mine = json.dumps({"session_id": "mine", "transcript_path": transcript})

    rc, _, err = run_hook(mine, tele_dir)
    assert rc == 0, err
    for other in range(5):
        rc, _, err = run_hook(json.dumps(
            {"session_id": "other%d" % other, "transcript_path": transcript}), tele_dir)
        assert rc == 0, err
    rc, _, err = run_hook(mine, tele_dir)   # our unchanged re-emission
    assert rc == 0, err

    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    with open(out_file, "r", encoding="ascii") as fh:
        lines = [json.loads(l) for l in fh.read().splitlines() if l.strip()]
    mine_lines = [r for r in lines if r["session_id"] == "mine"]
    assert len(mine_lines) == 1, (
        "our earlier record must be found past 5 interleaved sessions, got %d"
        % len(mine_lines)
    )
    assert len(lines) == 6, lines
    print("PASS test_skip_ignores_interleaved_other_sessions")


def test_unreadable_telemetry_file_still_appends():
    """FAIL OPEN, and fail toward WRITING. If the existing file cannot be read
    or parsed, the hook must append anyway -- a duplicate record is harmless
    (the rollup dedupes), silently dropping telemetry is not."""
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    transcript = os.path.join(tmp, "transcript.jsonl")
    tele_dir = os.path.join(tmp, "telemetry")
    make_transcript(transcript)
    os.makedirs(tele_dir)
    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    with open(out_file, "w", encoding="ascii") as fh:
        fh.write("\x00 not json \x01\n{{{ broken\n")

    stdin = json.dumps({"session_id": "gar1", "transcript_path": transcript})
    rc, out, err = run_hook(stdin, tele_dir)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    with open(out_file, "r", encoding="ascii", errors="replace") as fh:
        lines = [l for l in fh.read().splitlines() if l.strip()]
    assert len(lines) == 3, (
        "a corrupt existing file must not suppress the append, got %d" % len(lines)
    )
    assert json.loads(lines[-1])["session_id"] == "gar1", lines[-1]
    print("PASS test_unreadable_telemetry_file_still_appends")


def test_override_used_surfaces_reason():
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    transcript = os.path.join(tmp, "transcript.jsonl")
    tele_dir = os.path.join(tmp, "telemetry")
    sessions_dir = os.path.join(tmp, "sessions")
    make_transcript(transcript)

    sess_dir = os.path.join(sessions_dir, "test-override")
    os.makedirs(sess_dir, exist_ok=True)
    with open(os.path.join(sess_dir, "override"), "w", encoding="utf-8") as fh:
        fh.write("reason: applying planned fleet migration, plan doc pending")

    stdin = json.dumps({"session_id": "test-override", "transcript_path": transcript})
    rc, out, err = run_hook(stdin, tele_dir, sessions_dir)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)

    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    with open(out_file, "r", encoding="ascii") as fh:
        rec = json.loads(fh.read().splitlines()[-1])
    assert rec["override_used"] is True, rec
    assert rec["override_reason"] == "reason: applying planned fleet migration, plan doc pending", rec
    assert rec["override_at"], "expected a non-empty override_at timestamp, got %r" % rec
    print("PASS test_override_used_surfaces_reason")


def test_override_used_no_reason_backward_compat():
    """Old-style 0-byte override files (pre-fix) must still surface override_used=True
    with a null reason, not crash telemetry."""
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    transcript = os.path.join(tmp, "transcript.jsonl")
    tele_dir = os.path.join(tmp, "telemetry")
    sessions_dir = os.path.join(tmp, "sessions")
    make_transcript(transcript)

    sess_dir = os.path.join(sessions_dir, "test-empty-override")
    os.makedirs(sess_dir, exist_ok=True)
    open(os.path.join(sess_dir, "override"), "w").close()  # 0 bytes, old style

    stdin = json.dumps({"session_id": "test-empty-override", "transcript_path": transcript})
    rc, out, err = run_hook(stdin, tele_dir, sessions_dir)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)

    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    with open(out_file, "r", encoding="ascii") as fh:
        rec = json.loads(fh.read().splitlines()[-1])
    assert rec["override_used"] is True, rec
    assert rec["override_reason"] is None, rec
    print("PASS test_override_used_no_reason_backward_compat")


def test_no_override_file():
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    transcript = os.path.join(tmp, "transcript.jsonl")
    tele_dir = os.path.join(tmp, "telemetry")
    sessions_dir = os.path.join(tmp, "sessions")
    make_transcript(transcript)

    stdin = json.dumps({"session_id": "test-no-override", "transcript_path": transcript})
    rc, out, err = run_hook(stdin, tele_dir, sessions_dir)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)

    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    with open(out_file, "r", encoding="ascii") as fh:
        rec = json.loads(fh.read().splitlines()[-1])
    assert rec["override_used"] is False, rec
    assert rec["override_reason"] is None, rec
    assert rec["override_at"] is None, rec
    print("PASS test_no_override_file")


if __name__ == "__main__":
    test_happy_path()
    test_record_carries_schema_and_detectors()
    test_detectors_are_derived_from_live_constant()
    test_malformed_stdin_fails_open()
    test_empty_object_fails_open()
    test_missing_transcript_fails_open()
    test_no_code_activity_skipped()
    test_task_management_tools_are_not_dispatch()
    test_unchanged_re_emission_is_skipped()
    test_changed_transcript_still_appends()
    test_skip_compares_only_this_session()
    test_skip_ignores_interleaved_other_sessions()
    test_unreadable_telemetry_file_still_appends()
    test_override_used_surfaces_reason()
    test_override_used_no_reason_backward_compat()
    test_no_override_file()
    print("ALL TELEMETRY TESTS PASS")
