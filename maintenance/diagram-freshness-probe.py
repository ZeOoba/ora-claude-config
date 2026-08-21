#!/usr/bin/env python3
"""Flag stale or missing `<!-- diagram-verified: YYYY-MM-DD -->` stamps across
ORA's diagram-bearing repo READMEs (WO-3, 2026-08-21 repo-architecture-review).

OI-201 existed for 5 days before a full cross-repo audit caught it, because
nothing made diagram staleness visible without re-reading every repo by hand.
This probe is the machine-checkable half of that fix -- report-only, never
edits a README itself.

Local repos are read directly off disk; repos with no local clone are read
via `gh api repos/<repo>/contents/README.md` (requires `gh` authenticated).

Usage:
    python diagram-freshness-probe.py [--max-age-days N] [--json]

Default staleness threshold: 90 days (opening bid, per WO-3 -- adjust with
--max-age-days once real drift data exists).
"""
import argparse
import base64
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

STAMP_RE = re.compile(r"<!--\s*diagram-verified:\s*(\d{4}-\d{2}-\d{2})\s*-->")
MERMAID_RE = re.compile(r"```mermaid")

# (label, local path or None, remote "owner/repo" or None) -- exactly one of
# local path / remote repo should be set per entry.
TARGETS = [
    ("ora-claude-config (~/.claude)", r"C:\Users\Owner\.claude\README.md", None),
    ("ora-skills", r"C:\Users\Owner\ora-skills\README.md", None),
    ("ora-pm", r"C:\Users\Owner\ora-pm\README.md", None),
    ("AAOS", r"C:\Users\Owner\AAOS\README.md", None),
    ("oxford-command-center", r"C:\Users\Owner\oxford-command-center\README.md", None),
    ("ora-cowork-watchdog", None, "ZeOoba/ora-cowork-watchdog"),
    ("BrainVault", None, "ZeOoba/BrainVault"),
    # website-canonical deliberately excluded -- Hard Invariant 2, needs a
    # separate per-write confirmation pass, not swept into an automated probe.
]


def read_local(path):
    p = Path(path)
    if not p.exists():
        return None, "no README.md at that path"
    return p.read_text(encoding="utf-8", errors="replace"), None


def read_remote(repo):
    proc = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/README.md", "--jq", ".content"],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        return None, proc.stderr.strip() or "gh api call failed"
    try:
        raw = base64.b64decode(proc.stdout.strip())
        return raw.decode("utf-8", errors="replace"), None
    except Exception as e:
        return None, f"decode failed: {e}"


def check_one(label, local_path, remote_repo, max_age_days):
    if local_path:
        content, err = read_local(local_path)
    else:
        content, err = read_remote(remote_repo)

    if err:
        return {"repo": label, "status": "UNREADABLE", "detail": err}

    if not MERMAID_RE.search(content):
        return {"repo": label, "status": "NO_DIAGRAM", "detail": "no ```mermaid fence found -- not in scope for a stamp"}

    m = STAMP_RE.search(content)
    if not m:
        return {"repo": label, "status": "MISSING_STAMP", "detail": "has a mermaid diagram but no diagram-verified stamp"}

    stamp_date = date.fromisoformat(m.group(1))
    age_days = (date.today() - stamp_date).days
    if age_days < 0:
        return {"repo": label, "status": "FUTURE_STAMP", "detail": f"stamp dated {stamp_date} is in the future -- check for a typo"}
    if age_days > max_age_days:
        return {"repo": label, "status": "STALE", "detail": f"stamped {stamp_date}, {age_days}d ago (threshold {max_age_days}d)"}
    return {"repo": label, "status": "FRESH", "detail": f"stamped {stamp_date}, {age_days}d ago"}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-age-days", type=int, default=90)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results = [check_one(label, local, remote, args.max_age_days) for label, local, remote in TARGETS]

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"{r['status']:14s} {r['repo']:30s} {r['detail']}")

    problems = [r for r in results if r["status"] in ("STALE", "MISSING_STAMP", "UNREADABLE", "FUTURE_STAMP")]
    if not args.json:
        print()
        if problems:
            print(f"[ACTION] {len(problems)} repo(s) need attention: "
                  + ", ".join(f"{r['repo']} ({r['status']})" for r in problems))
        else:
            print("All diagram-bearing repos in scope have a fresh stamp.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
