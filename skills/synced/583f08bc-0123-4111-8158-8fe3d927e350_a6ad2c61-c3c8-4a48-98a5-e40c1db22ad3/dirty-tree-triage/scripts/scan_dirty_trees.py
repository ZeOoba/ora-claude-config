#!/usr/bin/env python3
"""Enumerate and classify dirty git working trees across ORA's known checkouts.

Mechanical scan only -- no attribution, no settlement judgment, no commits.
Those steps need session-roster + provenance + mtime-over-time evidence that
this script has no access to; see dirty-tree-triage/SKILL.md Standard Workflow
steps 3-6 for how a Claude session should follow up on this script's output.

Usage:
    python scan_dirty_trees.py [--repo PATH ...] [--json]

With no --repo given, scans the default ORA repo set below. Pass --repo one
or more times to scan a different/additional set instead.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_REPOS = [
    r"C:\Users\Owner\.claude",
    r"C:\Users\Owner\ora-skills",
    r"C:\Users\Owner\website-canonical",
    r"C:\Users\Owner\oxford-command-center",
]

# Name fragments that make an untracked entry read as obvious scratch/throwaway
# content rather than someone's real WIP. Conservative on purpose -- anything
# not matching one of these stays in the "modified/untracked, needs review"
# bucket rather than being auto-labeled trivial.
TRIVIAL_HINTS = ("scratch", "preview-deploy", "_archive/", ".tmp", "tmpindex")


def classify(porcelain_line):
    """One `git status --porcelain=v1` line -> (category, path)."""
    status = porcelain_line[:2]
    path = porcelain_line[3:].strip()
    if status == "??":
        is_dir = path.endswith("/")
        is_trivial = any(hint in path.lower() for hint in TRIVIAL_HINTS)
        category = "untracked-trivial" if is_trivial else (
            "untracked-dir" if is_dir else "untracked-file"
        )
    elif status[0] not in (" ", "?"):
        category = "staged"
    else:
        category = "modified-tracked"
    return category, path


def scan_repo(repo_path):
    repo = Path(repo_path)
    if not (repo / ".git").exists():
        return {"repo": str(repo), "error": "not a git repo (no .git)"}

    branch_proc = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain=v1", "--branch"],
        capture_output=True, text=True, check=False,
    )
    if branch_proc.returncode != 0:
        return {"repo": str(repo), "error": branch_proc.stderr.strip()}

    lines = branch_proc.stdout.splitlines()
    branch_line = lines[0] if lines and lines[0].startswith("##") else "## (unknown)"
    entries = []
    for line in lines[1:]:
        if not line.strip():
            continue
        category, path = classify(line)
        entries.append({"category": category, "path": path, "raw": line})

    by_category = {}
    for e in entries:
        by_category.setdefault(e["category"], 0)
        by_category[e["category"]] += 1

    return {
        "repo": str(repo),
        "branch": branch_line.lstrip("#").strip(),
        "dirty_count": len(entries),
        "by_category": by_category,
        "entries": entries,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", action="append", dest="repos", default=None,
                         help="Repo path to scan (repeatable). Default: the ORA known set.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a text table.")
    args = parser.parse_args()

    repos = args.repos or DEFAULT_REPOS
    results = [scan_repo(r) for r in repos]

    if args.json:
        print(json.dumps(results, indent=2))
        return

    for r in results:
        print(f"=== {r['repo']} ===")
        if "error" in r:
            print(f"  {r['error']}")
            continue
        print(f"  branch: {r['branch']}")
        print(f"  dirty:  {r['dirty_count']} entr{'y' if r['dirty_count'] == 1 else 'ies'}")
        for cat, count in sorted(r["by_category"].items()):
            print(f"    {cat}: {count}")
        print()

    total = sum(r.get("dirty_count", 0) for r in results)
    print(f"TOTAL across {len(results)} repo(s): {total} dirty entries")
    if total:
        print("Next: attribute + settle before touching anything -- see SKILL.md steps 3-6. "
              "This script does not commit, archive, or delete anything.")


if __name__ == "__main__":
    sys.exit(main())
