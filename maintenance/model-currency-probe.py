#!/usr/bin/env python3
"""ORA model-currency probe (CC/MCP fleet).

Reads every CC/MCP scheduled task's SKILL.md frontmatter `description` field under
~/.claude/scheduled-tasks/ and checks it for a `[MODEL: ...]` tag, so the fleet-wide
tagging gap is a standing, coded check instead of only a prose methodology someone
has to remember to run by hand.

WHY A SEPARATE, CODED PROBE (not just automation-health-monitor's Step 1.5):
automation-health-monitor runs on the LAMS/Cowork fleet. Its own SKILL.md documents
that ~/.claude/scheduled-tasks/ is "host-protected and not mountable" from that
surface -- so its Step 1.5 CC/MCP tag check can only ever actually run from a
Code-surface session, never from its own scheduled fire on Cowork.

WIRING (corrected 2026-07-29, Phase-2 defect T10 -- the prior claim "wired into
ora-health-guard" was never true and misdirected a forensic trace): NO scheduled
task invokes this script. The daily producer of _state/model-currency-cc.md is
ora-task-integrity-guard STEP 2.5, which performs the same check INLINE in its
prompt body (v1.1 2026-07-08 onward) and appends the state file directly. This
script is the standalone/manual diagnostic twin of that inline check -- keep the
two classification rules in sync via reference_scheduled_task_model_standard.md
(the single source of truth both cite). Sibling to connector-drift-probe.py's
same "make a one-time manual finding self-detecting" pattern.

The CC/MCP fleet's model is SERVER-PINNED, not settable (see
memory/reference_scheduled_task_model_standard.md) -- so this is a presence +
well-formedness check, NOT a match-the-standard check:
  * a task with NO `[MODEL: ...]` tag anywhere in its description -> UNTAGGED
    (the real, actionable gap -- a newer task created without one).
  * a task with a `[MODEL:` marker present but not matching the well-formed
    `[MODEL: <id> | checked YYYY-MM-DD]` shape -> MALFORMED.
Comparing a `checked` date against the release-check cadence is a separate,
less mechanical judgment call already made in automation-health-monitor's prose
methodology (it needs the release checklist's own "last known release" state) --
deliberately out of scope here, matching connector-drift-probe.py's own
precision-over-recall philosophy (verify only what's locally, unambiguously true).

Exit 0 = every task folder found has a well-formed tag; exit 1 = one or more
UNTAGGED/MALFORMED; exit 2 = probe error (missing directory, zero task folders
found -- fail loud, never silent).

Usage: python model-currency-probe.py [--quiet] [--tasks-dir=PATH]
"""
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HOME = os.path.expanduser("~")
DEFAULT_TASKS_DIR = os.path.join(HOME, ".claude", "scheduled-tasks")

MODEL_TAG_RE = re.compile(r"\[MODEL:\s*([^|\]]+?)\s*\|\s*checked\s+(\d{4}-\d{2}-\d{2})\s*\]")
DESCRIPTION_RE = re.compile(r"^description:\s*(.*)$", re.MULTILINE)
# Folders that are not live scheduled-task specs (shared helper scripts, archives).
SKIP_PREFIXES = ("_",)


def die(msg):
    """Fail loud: print an [ACTION] line and exit 2 (probe error)."""
    print("[ACTION] model-currency-probe: %s" % msg, file=sys.stderr)
    sys.exit(2)


def parse_args(argv):
    opts = {"tasks_dir": DEFAULT_TASKS_DIR, "quiet": False}
    for a in argv:
        if a == "--quiet":
            opts["quiet"] = True
        elif a.startswith("--tasks-dir="):
            opts["tasks_dir"] = a.split("=", 1)[1]
        else:
            die("unknown option: %s" % a)
    return opts


def read_text(path, label):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except Exception as e:
        die("cannot read %s (%s): %s" % (label, path, e))


def extract_description(skill_md_text, task_id):
    """Pull the frontmatter `description:` field out of a SKILL.md. Handles both the
    bare-scalar form (description: text...) and a single layer of enclosing quotes
    (description: 'text...'). Dies on missing/malformed frontmatter -- precision over
    recall, matching connector-drift-probe.py's fail-loud philosophy."""
    if not skill_md_text.startswith("---"):
        die("%s: SKILL.md has no frontmatter" % task_id)
    end = skill_md_text.find("\n---", 3)
    if end == -1:
        die("%s: SKILL.md frontmatter never closes" % task_id)
    frontmatter = skill_md_text[3:end]
    m = DESCRIPTION_RE.search(frontmatter)
    if not m:
        die("%s: SKILL.md frontmatter has no description field" % task_id)
    desc = m.group(1).strip()
    if len(desc) >= 2 and desc[0] == desc[-1] and desc[0] in ("'", '"'):
        desc = desc[1:-1]
    return desc


def list_task_dirs(tasks_dir):
    try:
        names = sorted(os.listdir(tasks_dir))
    except Exception as e:
        die("cannot list tasks dir (%s): %s" % (tasks_dir, e))
    return [n for n in names
            if not n.startswith(SKIP_PREFIXES)
            and os.path.isfile(os.path.join(tasks_dir, n, "SKILL.md"))]


def main():
    opts = parse_args(sys.argv[1:])
    task_ids = list_task_dirs(opts["tasks_dir"])
    if not task_ids:
        die("no task folders with a SKILL.md found under %s" % opts["tasks_dir"])

    untagged = []
    malformed = []
    tagged = []
    for task_id in task_ids:
        skill_path = os.path.join(opts["tasks_dir"], task_id, "SKILL.md")
        text = read_text(skill_path, "SKILL.md (%s)" % task_id)
        desc = extract_description(text, task_id)
        m = MODEL_TAG_RE.search(desc)
        if not m:
            if "[MODEL:" in desc:
                malformed.append(task_id)
            else:
                untagged.append(task_id)
            continue
        tagged.append((task_id, m.group(1).strip(), m.group(2)))

    findings = []
    for task_id in untagged:
        findings.append("%s: no [MODEL: ...] tag in SKILL.md description" % task_id)
    for task_id in malformed:
        findings.append("%s: has a '[MODEL:' marker that does not parse as "
                        "'[MODEL: <id> | checked YYYY-MM-DD]'" % task_id)

    if findings:
        print("MODEL-CURRENCY GAP DETECTED (%d of %d task(s)) under %s:"
              % (len(findings), len(task_ids), opts["tasks_dir"]))
        for f in findings:
            print("  " + f)
        if not opts["quiet"]:
            print("%d task(s) correctly tagged." % len(tagged))
        sys.exit(1)

    if not opts["quiet"]:
        print("model-currency-probe OK -- all %d CC/MCP task(s) carry a well-formed "
              "[MODEL: ...] tag." % len(task_ids))
    sys.exit(0)


if __name__ == "__main__":
    main()
