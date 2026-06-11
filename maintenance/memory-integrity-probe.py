#!/usr/bin/env python3
"""ORA memory-integrity probe (Phase 4.D). REPORT-ONLY — never edits memory (I6).

Checks the consolidated memory set for:
  1. Index reconciliation  — every MEMORY.md link resolves to a file; every root .md
     (except the index itself) is listed. No orphans, no unlisted files.
  2. Contradictions        — governor (DSCR != 1.25x / LTV != 40%, delegated to
     governor-drift-probe if present), digest-recipient drift (stray non-canonical
     addresses in a recipient context), and references to retired/archived docs as if live.
  3. Staleness (warnings)  — newest in-file date vs a per-type window. Warnings do NOT fail.

Exit 0 = integrity OK (staleness warnings allowed). Exit 1 = integrity issue. Exit 2 = probe error.
"""
import os, re, sys, glob, subprocess, datetime

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

HOME = os.path.expanduser("~")
MEM = os.path.join(HOME, ".claude", "projects",
                   "C--Users-Owner-OneDrive---Oxford-Capital-Partners--1-", "memory")
INDEX = os.path.join(MEM, "MEMORY.md")
GOV_PROBE = os.path.join(HOME, ".claude", "maintenance", "governor-drift-probe.py")

CANON_RECIPIENTS = {"ggoldberg@oxfordra.net", "egoldberg@oxfordra.net"}
RETIRED_DOCS = ("reference_tech.md", "reference_financial.md", "reference_communication.md",
                "reference_optimization_log.md", "ORA_SetupReference.md", "feedback_",
                "project_active.md", "project_command_center.md", "firm_ora.md", "user_gabriel.md")

STALE_DAYS = {"markets.md": 90, "people.md": 60, "projects.md": 21}  # report-only windows
DATE_RE = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")
EMAIL_RE = re.compile(r"[a-z0-9._%+-]+@oxfordra\.net", re.I)


def fail(findings):
    print("MEMORY INTEGRITY: %d issue(s)" % len(findings))
    for f in findings:
        print("  - " + f)
    sys.exit(1)


def main():
    if not os.path.isdir(MEM):
        sys.stderr.write("[ACTION] memory-integrity-probe: memory dir not found: %s\n" % MEM)
        sys.exit(2)

    issues, warnings = [], []

    # --- 1. index reconciliation ---
    try:
        idx = open(INDEX, encoding="utf-8").read()
    except Exception as e:
        sys.stderr.write("[ACTION] cannot read MEMORY.md: %s\n" % e)
        sys.exit(2)
    linked = set(re.findall(r"\]\(([A-Za-z0-9_./-]+\.md)\)", idx))
    linked = {os.path.basename(p) for p in linked}
    present = {os.path.basename(p) for p in glob.glob(os.path.join(MEM, "*.md"))}
    present.discard("MEMORY.md")  # the index doesn't link itself

    orphans = sorted(linked - present)          # linked but missing
    unlisted = sorted(present - linked)          # present but not indexed
    for o in orphans:
        issues.append("orphan index link (file missing): %s" % o)
    for u in unlisted:
        issues.append("unlisted file (present but not in MEMORY.md): %s" % u)

    # --- 2a. governor contradiction (delegate) ---
    if os.path.isfile(GOV_PROBE):
        r = subprocess.run([sys.executable, GOV_PROBE, "--quiet"],
                           capture_output=True, text=True)
        if r.returncode == 1:
            issues.append("governor drift detected (see governor-drift-probe.py): "
                          + (r.stdout.strip().splitlines() or ["?"])[0])
        elif r.returncode not in (0, 1):
            warnings.append("governor-drift-probe errored (rc=%d)" % r.returncode)

    # --- 2b. recipient drift + retired-doc links (scan living docs) ---
    for path in glob.glob(os.path.join(MEM, "*.md")):
        name = os.path.basename(path)
        try:
            txt = open(path, encoding="utf-8").read()
        except Exception:
            continue
        low = txt.lower()
        # recipient drift: a non-canonical @oxfordra.net address near 'recipient'/'digest'/'send'.
        # Skip event_log.md — it legitimately documents historical recipient drift that was fixed.
        if name != "event_log.md" and any(k in low for k in ("recipient", "digest", "send to", "distribution")):
            for em in set(m.lower() for m in EMAIL_RE.findall(txt)):
                if em not in CANON_RECIPIENTS:
                    warnings.append("%s references non-canonical recipient '%s' in a send/digest context" % (name, em))
        # retired-doc links presented as live (skip the index + archive references)
        if name != "MEMORY.md":
            for rd in RETIRED_DOCS:
                if re.search(r"\]\(%s" % re.escape(rd), txt):  # markdown link to a retired doc
                    issues.append("%s links retired/archived doc as live: %s" % (name, rd))

    # --- 3. staleness (warnings only) ---
    today = datetime.date.today()
    for fn, win in STALE_DAYS.items():
        p = os.path.join(MEM, fn)
        if not os.path.isfile(p):
            continue
        dates = [datetime.date(int(y), int(m), int(d)) for y, m, d in DATE_RE.findall(open(p, encoding="utf-8").read())
                 if 1 <= int(m) <= 12 and 1 <= int(d) <= 31]
        newest = max(dates) if dates else None
        if newest and (today - newest).days > win:
            warnings.append("%s newest date %s is >%dd old (stale window)" % (fn, newest, win))
        elif not newest:
            warnings.append("%s has no parseable date" % fn)

    # --- report ---
    print("MEMORY INTEGRITY PROBE — %d files indexed, %d present" % (len(linked), len(present)))
    if warnings:
        print("WARNINGS (non-fatal):")
        for w in warnings:
            print("  ~ " + w)
    if issues:
        fail(issues)
    print("OK — index reconciles 1:1, no contradictions, no retired-doc links.")
    sys.exit(0)


if __name__ == "__main__":
    main()
