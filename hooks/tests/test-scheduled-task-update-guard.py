"""Tests for the scheduled-task update frontmatter-integrity guard pair:
  scheduled-task-update-preguard.py  (PreToolUse -- hand-edit desync warning)
  scheduled-task-update-postguard.py (PostToolUse -- dropped frontmatter key warning)

Run: python test-scheduled-task-update-guard.py
Stdlib only. ASCII-only. Self-contained: builds a throwaway
scheduled-tasks/<task_id>/SKILL.md fixture and a throwaway state dir under a
temp CLAUDE_DIR-like tree, patched in via the ORA_TEST_CLAUDE_DIR env var --
see the two guards' skill_md_path()/state_dir() calls, which both resolve
relative to hooks/lib/scheduled_task_frontmatter.py's own location, so tests
instead monkeypatch by running the guards against a temp copy of hooks/.

Contract under test:
  * PreToolUse: no ledger entry for a task -> silent (nothing to compare).
  * PreToolUse: ledger sha == current sha -> silent (no desync).
  * PreToolUse: ledger sha != current sha -> warn via additionalContext,
    mentioning the task id.
  * PreToolUse: always leaves a pre-snapshot (sha + keys) for the post half,
    even when no warning fires.
  * PostToolUse: no pre-snapshot -> silent (nothing to diff).
  * PostToolUse: pre-snapshot keys superset of post keys -> warn naming the
    dropped key(s).
  * PostToolUse: pre-snapshot keys == post keys -> silent.
  * PostToolUse: updates the ledger to the post-call sha UNLESS tool_response
    signals the call failed, and consumes (deletes) the pre-snapshot file.
  * Fail-open on malformed/empty stdin, missing taskId, missing SKILL.md.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREGUARD = os.path.join(HOOKS_DIR, "scheduled-task-update-preguard.py")
POSTGUARD = os.path.join(HOOKS_DIR, "scheduled-task-update-postguard.py")

_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + "  " + detail)
        _failures.append(name)


class TempClaudeDir:
    """A throwaway directory shaped like ~/.claude (scheduled-tasks/, hooks/lib/,
    hooks/state/) so the guards' path helpers -- which resolve relative to their
    OWN file location -- operate on isolated fixtures instead of the real
    ~/.claude tree. We copy hooks/lib + the two guard scripts in, so the guards
    run unmodified against fixture data."""

    def __enter__(self):
        self.root = tempfile.mkdtemp(prefix="stug-")
        hooks = os.path.join(self.root, "hooks")
        os.makedirs(os.path.join(hooks, "lib"))
        os.makedirs(os.path.join(hooks, "state"))
        os.makedirs(os.path.join(self.root, "scheduled-tasks"))
        shutil.copy(os.path.join(HOOKS_DIR, "lib", "scheduled_task_frontmatter.py"),
                    os.path.join(hooks, "lib", "scheduled_task_frontmatter.py"))
        shutil.copy(PREGUARD, os.path.join(hooks, "scheduled-task-update-preguard.py"))
        shutil.copy(POSTGUARD, os.path.join(hooks, "scheduled-task-update-postguard.py"))
        self.preguard = os.path.join(hooks, "scheduled-task-update-preguard.py")
        self.postguard = os.path.join(hooks, "scheduled-task-update-postguard.py")
        self.ledger = os.path.join(hooks, "state", "scheduled-task-update-guard",
                                    "last-tool-sha.json")
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.root, ignore_errors=True)

    def write_skill_md(self, task_id, frontmatter_lines, body="body text\n"):
        d = os.path.join(self.root, "scheduled-tasks", task_id)
        os.makedirs(d, exist_ok=True)
        text = "---\n" + "\n".join(frontmatter_lines) + "\n---\n" + body
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write(text)
        return text

    def seed_ledger(self, task_id, sha):
        os.makedirs(os.path.dirname(self.ledger), exist_ok=True)
        with open(self.ledger, "w", encoding="utf-8") as fh:
            json.dump({task_id: {"sha": sha, "ts": 0}}, fh)

    def read_ledger(self):
        try:
            with open(self.ledger, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}


def run(script, session_id, task_id, tool_name="mcp__scheduled-tasks__update_scheduled_task",
        tool_response=None):
    body = {
        "session_id": session_id,
        "tool_name": tool_name,
        "tool_input": {"taskId": task_id, "description": "irrelevant"},
    }
    if tool_response is not None:
        body["tool_response"] = tool_response
    proc = subprocess.run([sys.executable, script], input=json.dumps(body),
                           capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def sha256_of(text):
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---- PreToolUse ---------------------------------------------------------

def test_pre_silent_no_ledger_entry():
    with TempClaudeDir() as t:
        t.write_skill_md("task-a", ["name: task-a", "description: hi"])
        rc, out, err = run(t.preguard, "s1", "task-a")
        check("test_pre_silent_no_ledger_entry", rc == 0 and out == "",
              "expected silent allow, got rc=%s out=%r" % (rc, out))


def test_pre_silent_unchanged_sha():
    with TempClaudeDir() as t:
        text = t.write_skill_md("task-a", ["name: task-a", "description: hi"])
        t.seed_ledger("task-a", sha256_of(text))
        rc, out, err = run(t.preguard, "s1", "task-a")
        check("test_pre_silent_unchanged_sha", rc == 0 and out == "",
              "expected silent allow (no desync), got out=%r" % out)


def test_pre_warns_on_hand_edit_desync():
    with TempClaudeDir() as t:
        t.write_skill_md("task-a", ["name: task-a", "description: hand-edited"])
        t.seed_ledger("task-a", "deadbeef" * 8)  # stale sha -> looks hand-edited
        rc, out, err = run(t.preguard, "s1", "task-a")
        ok = rc == 0 and "task-a" in out and "hand-edit" in out.lower()
        check("test_pre_warns_on_hand_edit_desync", ok,
              "expected non-blocking warn naming task-a, got rc=%s out=%r" % (rc, out))


def test_pre_leaves_snapshot_even_when_silent():
    with TempClaudeDir() as t:
        t.write_skill_md("task-a", ["name: task-a", "description: hi"])
        run(t.preguard, "s1", "task-a")
        snap_dir = os.path.join(t.root, "hooks", "state", "scheduled-task-update-guard")
        snaps = [f for f in os.listdir(snap_dir) if f.startswith("pre-")]
        check("test_pre_leaves_snapshot_even_when_silent", len(snaps) == 1,
              "expected exactly one pre-snapshot file, found %r" % snaps)


def test_pre_never_blocks():
    with TempClaudeDir() as t:
        rc, out, err = run(t.preguard, "s1", "nonexistent-task")
        check("test_pre_never_blocks_missing_task", rc == 0)


def test_pre_warning_shape_is_dual_delivery_and_never_denies():
    """Adversarial review finding N4a/b (2026-08-13): a warning that only sets
    systemMessage is silently useless to the agent (shared-checkout-guard.py's
    own 7-day live bug); a warning that ever emits deny/ask would violate the
    warn-only contract. Assert the actual JSON shape, not just that SOMETHING
    printed."""
    with TempClaudeDir() as t:
        t.write_skill_md("task-a", ["name: task-a", "description: hand-edited"])
        t.seed_ledger("task-a", "deadbeef" * 8)
        rc, out, err = run(t.preguard, "s1", "task-a")
        try:
            obj = json.loads(out)
        except Exception:
            obj = None
        hso = (obj or {}).get("hookSpecificOutput", {})
        ok = (
            isinstance(obj, dict)
            and isinstance(obj.get("systemMessage"), str) and obj["systemMessage"]
            and isinstance(hso.get("additionalContext"), str) and hso["additionalContext"]
            and hso.get("permissionDecision") == "allow"
        )
        check("test_pre_warning_shape_is_dual_delivery_and_never_denies", ok,
              "expected systemMessage + additionalContext + permissionDecision=allow, "
              "got out=%r" % out)


# ---- PostToolUse ----------------------------------------------------------

def test_post_silent_no_snapshot():
    with TempClaudeDir() as t:
        t.write_skill_md("task-a", ["name: task-a", "description: hi"])
        rc, out, err = run(t.postguard, "s1", "task-a")
        check("test_post_silent_no_snapshot", rc == 0 and out == "",
              "expected silent allow (no pre-snapshot), got out=%r" % out)


def test_post_warns_on_dropped_key():
    with TempClaudeDir() as t:
        # Simulate: preguard ran while output_contract still existed...
        t.write_skill_md("task-a", ["name: task-a", "description: hi",
                                     "output_contract:", "  version: 1"])
        run(t.preguard, "s1", "task-a")
        # ...then update_scheduled_task rewrote the file, dropping output_contract.
        t.write_skill_md("task-a", ["name: task-a", "description: new desc"])
        rc, out, err = run(t.postguard, "s1", "task-a")
        ok = rc == 0 and "output_contract" in out and "task-a" in out
        check("test_post_warns_on_dropped_key", ok,
              "expected warn naming output_contract, got rc=%s out=%r" % (rc, out))


def test_post_silent_when_keys_preserved():
    with TempClaudeDir() as t:
        t.write_skill_md("task-a", ["name: task-a", "description: hi"])
        run(t.preguard, "s1", "task-a")
        t.write_skill_md("task-a", ["name: task-a", "description: new desc"])
        rc, out, err = run(t.postguard, "s1", "task-a")
        check("test_post_silent_when_keys_preserved", rc == 0 and out == "",
              "expected silent allow (no key dropped), got out=%r" % out)


def test_post_updates_ledger_after_call():
    with TempClaudeDir() as t:
        t.write_skill_md("task-a", ["name: task-a", "description: hi"])
        run(t.preguard, "s1", "task-a")
        final_text = t.write_skill_md("task-a", ["name: task-a", "description: v2"])
        run(t.postguard, "s1", "task-a")
        ledger = t.read_ledger()
        ok = ledger.get("task-a", {}).get("sha") == sha256_of(final_text)
        check("test_post_updates_ledger_after_call", ok,
              "expected ledger sha to match post-call file, got %r" % ledger)


def test_post_consumes_snapshot():
    with TempClaudeDir() as t:
        t.write_skill_md("task-a", ["name: task-a", "description: hi"])
        run(t.preguard, "s1", "task-a")
        snap_dir = os.path.join(t.root, "hooks", "state", "scheduled-task-update-guard")
        before = [f for f in os.listdir(snap_dir) if f.startswith("pre-")]
        run(t.postguard, "s1", "task-a")
        after = [f for f in os.listdir(snap_dir) if f.startswith("pre-")]
        check("test_post_consumes_snapshot", len(before) == 1 and len(after) == 0,
              "expected snapshot removed after post-guard, before=%r after=%r" %
              (before, after))


def test_post_warning_shape_no_permission_decision():
    """PostToolUse cannot block (the call already ran) -- assert the shipped shape
    omits permissionDecision entirely (memory-nag-correction.py's convention) while
    still delivering via both channels (N4a/b)."""
    with TempClaudeDir() as t:
        t.write_skill_md("task-a", ["name: task-a", "description: hi",
                                     "output_contract:", "  version: 1"])
        run(t.preguard, "s1", "task-a")
        t.write_skill_md("task-a", ["name: task-a", "description: new desc"])
        rc, out, err = run(t.postguard, "s1", "task-a")
        try:
            obj = json.loads(out)
        except Exception:
            obj = None
        hso = (obj or {}).get("hookSpecificOutput", {})
        ok = (
            isinstance(obj, dict)
            and isinstance(obj.get("systemMessage"), str) and obj["systemMessage"]
            and isinstance(hso.get("additionalContext"), str) and hso["additionalContext"]
            and "permissionDecision" not in hso
        )
        check("test_post_warning_shape_no_permission_decision", ok,
              "expected systemMessage + additionalContext, no permissionDecision, "
              "got out=%r" % out)


def test_post_skips_ledger_update_on_tool_error():
    """Adversarial review finding N2 (2026-08-13): if update_scheduled_task itself
    reported failure, SKILL.md on disk may still be the pre-call (possibly
    hand-edited) content -- recording it as "last tool-mediated" would suppress the
    preguard's hand-edit warning on a retry."""
    with TempClaudeDir() as t:
        text = t.write_skill_md("task-a", ["name: task-a", "description: hi"])
        t.seed_ledger("task-a", "deadbeef" * 8)  # pre-existing stale ledger entry
        run(t.postguard, "s1", "task-a", tool_response={"is_error": True})
        ledger = t.read_ledger()
        ok = ledger.get("task-a", {}).get("sha") == "deadbeef" * 8
        check("test_post_skips_ledger_update_on_tool_error", ok,
              "expected ledger UNCHANGED on tool error, got %r (file sha would be %s)"
              % (ledger, sha256_of(text)))


def test_post_updates_ledger_on_tool_success_flag():
    with TempClaudeDir() as t:
        final_text = t.write_skill_md("task-a", ["name: task-a", "description: hi"])
        run(t.postguard, "s1", "task-a", tool_response={"is_error": False})
        ledger = t.read_ledger()
        ok = ledger.get("task-a", {}).get("sha") == sha256_of(final_text)
        check("test_post_updates_ledger_on_tool_success_flag", ok,
              "expected ledger updated on explicit success, got %r" % ledger)


def test_pre_and_post_silent_on_wrong_tool_name():
    """N6: correctness should key off the settings.json matcher, but a future
    matcher typo (or a hand-run of this script against the wrong payload) must be
    inert, not noisy."""
    with TempClaudeDir() as t:
        t.write_skill_md("task-a", ["name: task-a", "description: hi"])
        t.seed_ledger("task-a", "deadbeef" * 8)  # would normally trigger a warning
        rc1, out1, _ = run(t.preguard, "s1", "task-a", tool_name="Write")
        rc2, out2, _ = run(t.postguard, "s1", "task-a", tool_name="Write")
        check("test_pre_and_post_silent_on_wrong_tool_name",
              rc1 == 0 and out1 == "" and rc2 == 0 and out2 == "",
              "expected both silent for a non-matching tool_name, got out1=%r out2=%r"
              % (out1, out2))


def test_bom_frontmatter_does_not_crash_and_is_still_parsed():
    """N3: a UTF-8 BOM at the start of SKILL.md must not silently disable coverage
    for that task -- frontmatter_keys() must still see the fence and the keys."""
    with TempClaudeDir() as t:
        d = os.path.join(t.root, "scheduled-tasks", "task-a")
        os.makedirs(d, exist_ok=True)
        text = "---\nname: task-a\ndescription: hi\noutput_contract:\n  version: 1\n---\nbody\n"
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8-sig") as fh:
            fh.write(text)
        run(t.preguard, "s1", "task-a")
        # Now drop output_contract on the "post-call" write -- BOM-free this time,
        # simulating the tool's own rewrite.
        t.write_skill_md("task-a", ["name: task-a", "description: new desc"])
        rc, out, err = run(t.postguard, "s1", "task-a")
        ok = rc == 0 and "output_contract" in out
        check("test_bom_frontmatter_does_not_crash_and_is_still_parsed", ok,
              "expected BOM'd frontmatter still parsed and diffed, got rc=%s out=%r"
              % (rc, out))


def test_post_never_blocks():
    with TempClaudeDir() as t:
        rc, out, err = run(t.postguard, "s1", "nonexistent-task")
        check("test_post_never_blocks_missing_task", rc == 0)


# ---- End-to-end round trip: full pre -> real update -> post cycle --------

def test_end_to_end_full_cycle_no_false_positive():
    """A completely ordinary update (only description changes, no keys touched,
    no hand-edit in between) must be silent on BOTH ends -- the common case must
    never nag."""
    with TempClaudeDir() as t:
        t.write_skill_md("task-a", ["name: task-a", "description: v1"])
        rc1, out1, _ = run(t.preguard, "s1", "task-a")
        t.write_skill_md("task-a", ["name: task-a", "description: v2"])
        rc2, out2, _ = run(t.postguard, "s1", "task-a")
        check("test_end_to_end_full_cycle_no_false_positive",
              rc1 == 0 and out1 == "" and rc2 == 0 and out2 == "",
              "expected fully silent ordinary cycle, got out1=%r out2=%r" % (out1, out2))


# ---- Fail-open on malformed input -----------------------------------------

def test_failopen_empty_stdin():
    for script in (PREGUARD, POSTGUARD):
        proc = subprocess.run([sys.executable, script], input="",
                               capture_output=True, text=True)
        check("test_failopen_empty_stdin_%s" % os.path.basename(script),
              proc.returncode == 0 and proc.stdout == "",
              "got rc=%s out=%r" % (proc.returncode, proc.stdout))


def test_failopen_malformed_json():
    for script in (PREGUARD, POSTGUARD):
        proc = subprocess.run([sys.executable, script], input="{not json",
                               capture_output=True, text=True)
        check("test_failopen_malformed_json_%s" % os.path.basename(script),
              proc.returncode == 0 and proc.stdout == "",
              "got rc=%s out=%r" % (proc.returncode, proc.stdout))


def test_failopen_missing_task_id():
    for script in (PREGUARD, POSTGUARD):
        payload = json.dumps({
            "session_id": "s1",
            "tool_name": "mcp__scheduled-tasks__update_scheduled_task",
            "tool_input": {},
        })
        proc = subprocess.run([sys.executable, script], input=payload,
                               capture_output=True, text=True)
        check("test_failopen_missing_task_id_%s" % os.path.basename(script),
              proc.returncode == 0 and proc.stdout == "",
              "got rc=%s out=%r" % (proc.returncode, proc.stdout))


if __name__ == "__main__":
    test_pre_silent_no_ledger_entry()
    test_pre_silent_unchanged_sha()
    test_pre_warns_on_hand_edit_desync()
    test_pre_leaves_snapshot_even_when_silent()
    test_pre_never_blocks()
    test_pre_warning_shape_is_dual_delivery_and_never_denies()
    test_post_silent_no_snapshot()
    test_post_warns_on_dropped_key()
    test_post_silent_when_keys_preserved()
    test_post_updates_ledger_after_call()
    test_post_consumes_snapshot()
    test_post_warning_shape_no_permission_decision()
    test_post_skips_ledger_update_on_tool_error()
    test_post_updates_ledger_on_tool_success_flag()
    test_pre_and_post_silent_on_wrong_tool_name()
    test_bom_frontmatter_does_not_crash_and_is_still_parsed()
    test_post_never_blocks()
    test_end_to_end_full_cycle_no_false_positive()
    test_failopen_empty_stdin()
    test_failopen_malformed_json()
    test_failopen_missing_task_id()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures)))
        sys.exit(1)
    print("\nALL scheduled-task-update-guard tests passed.")
    sys.exit(0)
