#!/usr/bin/env python3
"""ORA skill-governor restore (companion to governor-drift-probe).

deal-comparison and portfolio-growth are Cowork CLOUD-synced skills (no on-disk durable
source), so a Cowork re-sync can revert the G5 governor fix (DSCR 1.75x -> 1.25x) in the
live AppData runtime copies. governor-drift-probe.py DETECTS that; this script FIXES it,
idempotently, in one command. Safe to run anytime (no-op if already correct). Does NOT
need the app closed (these are plain files the runtime reads).

Usage: python restore-skill-governor.py        # apply; prints what changed
       python restore-skill-governor.py --check # report only, exit 1 if any 1.75 remains
"""
import os, sys, glob

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

HOME = os.path.expanduser("~")
TARGET_SKILLS = ("deal-comparison", "portfolio-growth")
# governor-context replacements (all 1.75 occurrences in these 2 files are DSCR-governor refs)
REPLACEMENTS = (("1.75x", "1.25x"), ("1.75-1.99", "1.25-1.99"), ("1.75 ", "1.25 "))

def discover_skills_root():
    base = os.path.join(os.environ.get("APPDATA", os.path.join(HOME, "AppData", "Roaming")),
                        "Claude", "local-agent-mode-sessions", "skills-plugin")
    hits = [h for h in glob.glob(os.path.join(base, "*", "*", "skills")) if os.path.isdir(h)]
    return max(hits, key=os.path.getmtime) if hits else None

def main():
    check = "--check" in sys.argv
    root = discover_skills_root()
    if not root:
        sys.stderr.write("[ACTION] restore-skill-governor: skills runtime dir not found.\n")
        sys.exit(2)
    changed, dirty = [], []
    for skill in TARGET_SKILLS:
        p = os.path.join(root, skill, "SKILL.md")
        if not os.path.isfile(p):
            sys.stderr.write("[ACTION] missing %s\n" % p); sys.exit(2)
        txt = open(p, encoding="utf-8").read()
        if "1.75" in txt:
            dirty.append(skill)
        if check:
            continue
        new = txt
        for a, b in REPLACEMENTS:
            new = new.replace(a, b)
        if new != txt:
            open(p, "w", encoding="utf-8").write(new)
            changed.append(skill)
    if check:
        if dirty:
            print("DRIFT: 1.75 governor value present in: %s — run without --check to fix." % ", ".join(dirty))
            sys.exit(1)
        print("OK — deal-comparison + portfolio-growth at 1.25x governor.")
        sys.exit(0)
    if changed:
        print("RESTORED 1.25x governor in: %s (skills root: %s)" % (", ".join(changed), root))
    else:
        print("No change needed — already at 1.25x governor.")
    sys.exit(0)

if __name__ == "__main__":
    main()
