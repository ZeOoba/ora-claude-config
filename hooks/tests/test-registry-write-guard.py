"""Tests for registry-write-guard.py PreToolUse hook (Edit|Write|MultiEdit).

Run: python test-registry-write-guard.py
Stdlib only. ASCII-only. Self-contained (pure path-string matching -- no files created).

Contract under test:
  * A direct Edit/Write/MultiEdit to EITHER fleet's registry backing file
    (`.../claude-code-sessions/<guid>/<guid>/scheduled-tasks.json` or
     `.../local-agent-mode-sessions/<guid>/<guid>/scheduled-tasks.json`) -> BLOCK (exit 2).
  * Everything else -> ALLOW (exit 0), including a task SKILL.md, an unrelated
    scheduled-tasks.json elsewhere, and ordinary files.
  * Fail-OPEN on the hook's own errors (malformed/empty stdin) -> exit 0.
The registry doctrine: register via mcp__scheduled-tasks__create_scheduled_task /
the register-scheduled-task skill, NEVER by splicing the registry JSON directly.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/ (test in hooks/tests/)
HOOK = os.path.join(HERE, "registry-write-guard.py")

# Realistic live backing paths (GUIDs are per-session; the guard must be GUID-agnostic).
CC_REG = ("C:/Users/Owner/AppData/Roaming/Claude/claude-code-sessions/"
          "a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3/583f08bc-0123-4111-8158-8fe3d927e350/"
          "scheduled-tasks.json")
LAMS_REG = ("C:/Users/Owner/AppData/Roaming/Claude/local-agent-mode-sessions/"
            "a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3/583f08bc-0123-4111-8158-8fe3d927e350/"
            "scheduled-tasks.json")
# A different session's GUIDs -- must still block (robustness to session rotation).
CC_REG_OTHER_GUID = ("C:/Users/Owner/AppData/Roaming/Claude/claude-code-sessions/"
                     "ffffffff-0000-1111-2222-333333333333/"
                     "00000000-aaaa-bbbb-cccc-dddddddddddd/scheduled-tasks.json")
# Backslash form (Windows editors pass native separators).
CC_REG_BACKSLASH = CC_REG.replace("/", "\\")

_failures = []


def run_hook(stdin_text):
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=stdin_text, capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def payload(file_path, tool_name="Write"):
    return json.dumps({"session_id": "s1", "tool_name": tool_name,
                       "tool_input": {"file_path": file_path}})


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + "  " + detail)
        _failures.append(name)


def test_block_cc_registry_write():
    rc, out, err = run_hook(payload(CC_REG, "Write"))
    check("test_block_cc_registry_write", rc == 2 and "register" in (err + out).lower(),
          "expected exit 2 + guidance, got rc=%s err=%r" % (rc, err))


def test_block_lams_registry_write():
    rc, out, err = run_hook(payload(LAMS_REG, "Write"))
    check("test_block_lams_registry_write", rc == 2,
          "expected exit 2, got rc=%s err=%r" % (rc, err))


def test_block_edit_and_multiedit():
    for tool in ("Edit", "MultiEdit"):
        rc, out, err = run_hook(payload(CC_REG, tool))
        check("test_block_%s" % tool.lower(), rc == 2,
              "%s to registry expected exit 2, got rc=%s" % (tool, rc))


def test_block_other_guid():
    rc, out, err = run_hook(payload(CC_REG_OTHER_GUID, "Write"))
    check("test_block_other_guid", rc == 2,
          "different-GUID registry path must still block, got rc=%s" % rc)


def test_block_backslash_path():
    rc, out, err = run_hook(payload(CC_REG_BACKSLASH, "Write"))
    check("test_block_backslash_path", rc == 2,
          "backslash registry path must block, got rc=%s" % rc)


def test_allow_task_skill_md():
    # Editing a CC task's SKILL.md is the SANCTIONED way to change a spec -- never blocked.
    p = "C:/Users/Owner/.claude/scheduled-tasks/ora-pm-ledger/SKILL.md"
    rc, out, err = run_hook(payload(p, "Edit"))
    check("test_allow_task_skill_md", rc == 0,
          "SKILL.md edit must be allowed, got rc=%s err=%r" % (rc, err))


def test_allow_unrelated_scheduled_tasks_json():
    # A scheduled-tasks.json NOT under a session registry dir is unrelated config.
    p = "C:/Users/Owner/some-project/config/scheduled-tasks.json"
    rc, out, err = run_hook(payload(p, "Write"))
    check("test_allow_unrelated_scheduled_tasks_json", rc == 0,
          "unrelated scheduled-tasks.json must be allowed, got rc=%s" % rc)


def test_allow_ordinary_file():
    p = "C:/Users/Owner/.claude/hooks/registry-write-guard.py"
    rc, out, err = run_hook(payload(p, "Write"))
    check("test_allow_ordinary_file", rc == 0,
          "ordinary file write must be allowed, got rc=%s" % rc)


def test_allow_registry_named_dir_not_json():
    # A file inside the session dir that is NOT the registry json (e.g. a sibling) is allowed.
    p = ("C:/Users/Owner/AppData/Roaming/Claude/claude-code-sessions/"
         "a6ad2c61/583f08bc/notes.txt")
    rc, out, err = run_hook(payload(p, "Write"))
    check("test_allow_registry_named_dir_not_json", rc == 0,
          "non-registry file under session dir must be allowed, got rc=%s" % rc)


def test_failopen_empty_stdin():
    rc, out, err = run_hook("")
    check("test_failopen_empty_stdin", rc == 0,
          "empty stdin must fail open (exit 0), got rc=%s" % rc)


def test_failopen_malformed_json():
    rc, out, err = run_hook("{not json")
    check("test_failopen_malformed_json", rc == 0,
          "malformed json must fail open (exit 0), got rc=%s" % rc)


def test_failopen_missing_file_path():
    rc, out, err = run_hook(json.dumps({"tool_input": {}}))
    check("test_failopen_missing_file_path", rc == 0,
          "missing file_path must fail open (exit 0), got rc=%s" % rc)


if __name__ == "__main__":
    test_block_cc_registry_write()
    test_block_lams_registry_write()
    test_block_edit_and_multiedit()
    test_block_other_guid()
    test_block_backslash_path()
    test_allow_task_skill_md()
    test_allow_unrelated_scheduled_tasks_json()
    test_allow_ordinary_file()
    test_allow_registry_named_dir_not_json()
    test_failopen_empty_stdin()
    test_failopen_malformed_json()
    test_failopen_missing_file_path()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures)))
        sys.exit(1)
    print("\nALL registry-write-guard tests passed.")
    sys.exit(0)
