#!/usr/bin/env python3
"""Tests for model-currency-probe.py (TDD).

Runs the probe as a subprocess against synthetic scheduled-task-folder fixtures
(via the --tasks-dir override) and asserts the exit-code contract (0 clean /
1 gap / 2 probe error) and the finding content. Mirrors
test-connector-drift-probe.py's fixture-and-subprocess style.

Run: python test-model-currency-probe.py
Pure stdlib. ASCII-only output.
"""
import os
import sys
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, "model-currency-probe.py")

_failures = []


def check(name, cond, detail=""):
    if cond:
        print("  PASS " + name)
    else:
        print("  FAIL " + name + "  " + detail)
        _failures.append(name)


def make_tasks_dir(tasks):
    """tasks: dict of task_id -> description string (or None to omit the field
    entirely, or a raw frontmatter override string starting with 'RAW:')."""
    d = tempfile.mkdtemp(prefix="mcp-tasks-")
    for task_id, desc in tasks.items():
        task_dir = os.path.join(d, task_id)
        os.makedirs(task_dir)
        skill_path = os.path.join(task_dir, "SKILL.md")
        with open(skill_path, "w", encoding="utf-8") as fh:
            if isinstance(desc, str) and desc.startswith("RAW:"):
                fh.write(desc[len("RAW:"):])
            elif desc is None:
                fh.write("---\nname: %s\n---\n\nbody text, no description field\n" % task_id)
            else:
                fh.write("---\nname: %s\ndescription: %s\n---\n\nbody text\n" % (task_id, desc))
    return d


def run(tasks_dir, extra_args=None):
    args = [sys.executable, PROBE, "--tasks-dir=" + tasks_dir]
    if extra_args:
        args += extra_args
    proc = subprocess.run(args, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def test_all_tagged_clean():
    d = make_tasks_dir({
        "ora-alpha": "Alpha task. [MODEL: UNVERIFIABLE | checked 2026-07-09]",
        "ora-beta": "Beta task. [MODEL: claude-sonnet-5 | checked 2026-07-12]",
    })
    rc, out = run(d)
    check("test_all_tagged_clean", rc == 0, "expected exit 0, got %s\n%s" % (rc, out))


def test_untagged_flags():
    d = make_tasks_dir({
        "ora-alpha": "Alpha task. [MODEL: UNVERIFIABLE | checked 2026-07-09]",
        "ora-untagged": "A task with no model tag at all.",
    })
    rc, out = run(d)
    check("test_untagged_flags", rc == 1 and "ora-untagged" in out and "no [MODEL" in out,
          "expected exit 1 naming ora-untagged as untagged, got %s\n%s" % (rc, out))


def test_malformed_tag_flags():
    d = make_tasks_dir({
        "ora-broken": "Has a marker but [MODEL: no-checked-date-here] is malformed.",
    })
    rc, out = run(d)
    check("test_malformed_tag_flags", rc == 1 and "ora-broken" in out and "does not parse" in out,
          "expected exit 1 naming ora-broken as malformed, got %s\n%s" % (rc, out))


def test_missing_description_field_is_probe_error():
    d = make_tasks_dir({"ora-nodesc": None})
    rc, out = run(d)
    check("test_missing_description_field_is_probe_error", rc == 2,
          "expected exit 2 (no description field), got %s\n%s" % (rc, out))


def test_missing_tasks_dir_is_probe_error():
    rc, out = run(os.path.join(tempfile.gettempdir(), "does-not-exist-mcp-dir"))
    check("test_missing_tasks_dir_is_probe_error", rc == 2,
          "expected exit 2 (missing dir), got %s\n%s" % (rc, out))


def test_empty_tasks_dir_is_probe_error():
    d = tempfile.mkdtemp(prefix="mcp-empty-")
    rc, out = run(d)
    check("test_empty_tasks_dir_is_probe_error", rc == 2,
          "expected exit 2 (no task folders), got %s\n%s" % (rc, out))


def test_underscore_prefixed_folders_skipped():
    d = make_tasks_dir({
        "ora-alpha": "Alpha task. [MODEL: UNVERIFIABLE | checked 2026-07-09]",
        "_shared": "Helper scripts, not a real task, no model tag.",
    })
    rc, out = run(d)
    check("test_underscore_prefixed_folders_skipped", rc == 0 and "_shared" not in out,
          "expected exit 0, _shared must be skipped, got %s\n%s" % (rc, out))


def test_quoted_description_form_parses():
    d = make_tasks_dir({
        "ora-quoted": "RAW:---\nname: ora-quoted\ndescription: 'Quoted task. [MODEL: claude-sonnet-5 | checked 2026-07-12]'\n---\n\nbody\n",
    })
    rc, out = run(d)
    check("test_quoted_description_form_parses", rc == 0,
          "expected exit 0 for quoted description form, got %s\n%s" % (rc, out))


def test_live_probe_smoke():
    # The probe with NO override runs against the real tree; it must not crash.
    proc = subprocess.run([sys.executable, PROBE], capture_output=True, text=True)
    check("test_live_probe_smoke", proc.returncode in (0, 1),
          "live probe should exit 0 or 1, got %s\n%s" % (proc.returncode, proc.stdout + proc.stderr))


if __name__ == "__main__":
    test_all_tagged_clean()
    test_untagged_flags()
    test_malformed_tag_flags()
    test_missing_description_field_is_probe_error()
    test_missing_tasks_dir_is_probe_error()
    test_empty_tasks_dir_is_probe_error()
    test_underscore_prefixed_folders_skipped()
    test_quoted_description_form_parses()
    test_live_probe_smoke()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures)))
        sys.exit(1)
    print("\nALL model-currency-probe tests passed.")
    sys.exit(0)
