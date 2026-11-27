#!/usr/bin/env python3
"""Regression: an ora-task-integrity-guard run cannot re-dirty the public repo with the
third-party contacts held in LAMS task specs.

WHY (2026-11-25). guard.ps1's mirror sync copies each task's live canonical SKILL.md
verbatim into _scheduled_tasks_backup/<id>/SKILL.md. For LAMS tasks the canonical lives in
OneDrive and still carries real third-party emails / policy numbers, so every run overwrote
the #454-scrubbed tracked mirrors with real values. The mirror is the guard's restore source
and must stay faithful, so the fix is: those mirrors are untracked + gitignored, and
hooks/lib/exposure_leak_check.py rule 5 blocks a push that adds a third-party email to any
task spec (tested in hooks/tests/test-exposure-leak-check.py).

Checks:
  1. STATIC  -- each of the five mirrors is untracked and ignored in this checkout.
  2. REPLAY  -- the REAL guard.ps1, pointed by its override params at a throwaway git repo that
                carries this checkout's .gitignore, writes a canonical holding a SYNTHETIC
                third-party email into the mirror (proves the guard is the writer) and leaves
                `git status` clean and `git add -A` empty (proves a re-run cannot re-dirty).
     CONTROL -- the same run for an id NOT on the ignore list shows up as untracked, so a clean
                status above is not the test failing to see the write.
REPLAY is skipped (stated, not passed) when no Windows PowerShell is on PATH.

Run: python maintenance/_tests/test_task_backup_pii_untracked.py   (exit 0 = pass)
Stdlib only; synthetic addresses only -- never a real contact in this public repo.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
GUARD = os.path.join(REPO, "scheduled-tasks", "ora-task-integrity-guard", "guard.ps1")

IGNORED_IDS = (
    "ora-counsel-review-standard-positions-2027",
    "ora-hubspot-notion-contact-sync",
    "ora-insurance-renewal-monitor",
    "ora-stale-pipeline-nudge",
    "ora-tenant-contact-gap-sweep",
)
CONTROL_ID = "ora-zz-control-not-ignored"
FAKE = "cc: jane.broker@acmebrokerage-synthetic.com\n"

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    print(("  ok   " if cond else "  FAIL ") + label + ("" if cond else " " + str(detail)[:300]))


def git(args, cwd):
    return subprocess.run(["git", "-C", cwd] + args, capture_output=True, text=True)


# --- 1. static ------------------------------------------------------------------------------
for tid in IGNORED_IDS:
    rel = "_scheduled_tasks_backup/%s/SKILL.md" % tid
    tracked = git(["ls-files", "--error-unmatch", rel], REPO).returncode == 0
    ignored = git(["check-ignore", "-q", "--no-index", rel], REPO).returncode == 0
    expect("untracked: %s" % tid, not tracked)
    expect("ignored:   %s" % tid, ignored)

# --- 2. replay ------------------------------------------------------------------------------
ps = shutil.which("powershell") or shutil.which("powershell.exe")
if not ps or not os.path.exists(GUARD):
    print("  SKIP replay: no Windows PowerShell / guard.ps1 on this host")
else:
    tmp = tempfile.mkdtemp(prefix="stb-pii-")
    try:
        repo = os.path.join(tmp, "repo")
        os.makedirs(repo)
        git(["init", "-q"], repo)
        shutil.copy(os.path.join(REPO, ".gitignore"), os.path.join(repo, ".gitignore"))
        git(["add", ".gitignore"], repo)
        git(["-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "base"], repo)

        canon_root = os.path.join(tmp, "canon")
        store = os.path.join(tmp, "store", "local-agent-mode-sessions", "a", "b")
        os.makedirs(store)
        tasks = []
        for tid in IGNORED_IDS + (CONTROL_ID,):
            d = os.path.join(canon_root, tid)
            os.makedirs(d)
            fp = os.path.join(d, "SKILL.md")
            with open(fp, "w", encoding="utf-8", newline="\n") as f:
                f.write("# %s (synthetic canonical)\n%s" % (tid, FAKE))
            tasks.append({"id": tid, "filePath": fp})
        with open(os.path.join(store, "scheduled-tasks.json"), "w", encoding="utf-8") as f:
            json.dump({"scheduledTasks": tasks}, f)

        local = os.path.join(repo, "_scheduled_tasks_backup")
        args = [ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", GUARD,
                "-GovOverride", os.path.join(tmp, "gov"), "-LocalOverride", local,
                "-LedgerPathOverride", os.path.join(tmp, "ledger.json"),
                "-StoreRootsOverride", os.path.join(tmp, "store"),
                "-CcRepoOverride", os.path.join(tmp, "no-such-repo")]
        # Twice: the first run sets the ledger baseline, the second is the steady-state re-run.
        for n in (1, 2):
            r = subprocess.run(args, capture_output=True, text=True, timeout=300)
            expect("guard run %d exits 0" % n, r.returncode == 0, r.stdout[-300:] + r.stderr[-300:])

        for tid in IGNORED_IDS:
            mp = os.path.join(local, tid, "SKILL.md")
            body = open(mp, encoding="utf-8").read() if os.path.exists(mp) else ""
            expect("guard wrote mirror (writer proven): %s" % tid, FAKE.strip() in body)

        st = git(["status", "--porcelain", "--untracked-files=all"], repo).stdout.splitlines()
        leaked = [l for l in st if any(t in l for t in IGNORED_IDS)]
        expect("re-run leaves the five mirrors invisible to git status", leaked == [], leaked)
        added = git(["add", "-A", "--dry-run"], repo).stdout
        expect("`git add -A` would stage none of the five", not any(t in added for t in IGNORED_IDS),
               added)
        expect("CONTROL: a non-ignored mirror write IS visible",
               any(CONTROL_ID in l for l in st), st)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

failed = [l for ok, l in results if not ok]
print("task-backup PII untrack: %d/%d passed" % (len(results) - len(failed), len(results)))
sys.exit(1 if failed else 0)
