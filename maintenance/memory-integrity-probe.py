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
# ORA_MEMORY_DIR overrides the scanned directory (tests only -- production runs use the default).
MEM = os.environ.get("ORA_MEMORY_DIR") or os.path.join(
    HOME, ".claude", "projects",
    "C--Users-Owner-OneDrive---Oxford-Capital-Partners", "memory")
INDEX = os.path.join(MEM, "MEMORY.md")
GOV_PROBE = os.path.join(HOME, ".claude", "maintenance", "governor-drift-probe.py")

CANON_RECIPIENTS = {"ggoldberg@oxfordra.net", "egoldberg@oxfordra.net"}
RETIRED_DOCS = ("reference_tech.md", "reference_financial.md", "reference_communication.md",
                "reference_optimization_log.md", "ORA_SetupReference.md", "feedback_",
                "project_active.md", "project_command_center.md", "firm_ora.md", "user_gabriel.md")

STALE_DAYS = {"markets.md": 90, "people.md": 60, "projects.md": 21}  # report-only windows
DATE_RE = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")
EMAIL_RE = re.compile(r"[a-z0-9._%+-]+@oxfordra\.net", re.I)
# A dated memory (a watch note, a "check back after X" tracking item) may declare its own
# expiry in frontmatter:  review_by: YYYY-MM-DD
# Once that date passes, the note is overdue for a resolve-or-archive decision and this probe
# says so every run. Added 2026-07-14 after project_owner_outreach_stale_guard_watch sat a day
# past its own stated deadline with nobody looking -- and the answer, when finally checked,
# inverted the note's premise. Report-only: an overdue note is a nudge, never a hard failure.
REVIEW_BY_RE = re.compile(r"^review_by:\s*(20\d{2}-\d{2}-\d{2})\s*$", re.M)


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
        # retired-doc links presented as live (skip the index + archive references).
        # Guard on presence first: a link whose target still exists as a LIVE root
        # memory file is never a violation, even when its name shares a retired prefix.
        # The current scheme reuses the "feedback_" prefix for LIVE notes while the
        # retired ones were merged into rules.md and moved to _archive/ (so they are
        # absent from `present`); without this guard the broad "feedback_" prefix
        # false-positives on every live feedback_* file that gets body-linked.
        if name != "MEMORY.md":
            for tgt in re.findall(r"\]\(([A-Za-z0-9_./-]+\.md)[^)]*\)", txt):
                base = os.path.basename(tgt)
                if base in present:
                    continue  # links to a live file are fine
                for rd in RETIRED_DOCS:
                    if base.startswith(rd):  # link to a retired/archived doc name
                        issues.append("%s links retired/archived doc as live: %s" % (name, base))
                        break

    # --- 2c. overdue review_by (warnings only) ---
    # Scanned in the same pass as 2b would be cheaper, but this reads the file fresh so the
    # check stands alone and can't be broken by an early `continue` above.
    today = datetime.date.today()
    for path in sorted(glob.glob(os.path.join(MEM, "*.md"))):
        name = os.path.basename(path)
        try:
            txt = open(path, encoding="utf-8").read()
        except Exception:
            continue
        m = REVIEW_BY_RE.search(txt)
        if not m:
            continue
        try:
            due = datetime.datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            warnings.append("%s has an unparseable review_by: %s" % (name, m.group(1)))
            continue
        if due < today:
            warnings.append(
                "%s is OVERDUE for review (review_by: %s, %d day(s) ago) -- resolve it or "
                "archive it; do not let it rot" % (name, due, (today - due).days))

    # --- 3. staleness (warnings only) ---
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
