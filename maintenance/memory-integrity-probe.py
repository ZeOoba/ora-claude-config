#!/usr/bin/env python3
"""ORA memory-integrity probe (Phase 4.D). REPORT-ONLY — never edits memory (I6).

Checks the consolidated memory set for:
  1. Index reconciliation  — every MEMORY.md link resolves to a file; every root .md
     (except the index itself) is listed. No orphans, no unlisted files.
  2. Contradictions        — governor (DSCR != 1.25x / LTV != 40%, delegated to
     governor-drift-probe if present), digest-recipient drift (stray non-canonical
     addresses in a recipient context), and references to retired/archived docs as if live.
  3. Staleness (warnings)  — newest in-file date vs a per-type window. Warnings do NOT fail.
  4. Open-items tracker (open-items-tracker.md, added 2026-07-17 after the
     oxford-cc-repo-health.md -> session-context.md dead-pointer incident):
       4a. dead pointers — any "open-items-tracker.md#OI-NNN" reference elsewhere in
           memory/*.md whose ID has no matching row in the tracker           [fail]
       4b. auto-check drift (warnings) — any tracker item marked OPEN that carries an
           Auto-check line gets evaluated against live fleet-status.py --json output
           (bounded vocabulary only, no code execution); a match means the item looks
           resolved but is still marked OPEN — WARN, never auto-closes.  Skipped
           entirely if open-items-tracker.md doesn't exist (optional companion file).

Exit 0 = integrity OK (staleness warnings allowed). Exit 1 = integrity issue. Exit 2 = probe error.
"""
import os, re, sys, glob, json, subprocess, datetime

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

# --- open-items tracker (check 4) ---
TRACKER = os.path.join(MEM, "open-items-tracker.md")
FLEET_STATUS_PROBE = os.path.join(HOME, ".claude", "maintenance", "fleet-status.py")
OI_ID_RE = re.compile(r"^###\s+(OI-\d{3,})\s*$", re.M)
OI_STATUS_RE = re.compile(r"\*\*Status:\*\*\s*(\S+)")
OI_AUTOCHECK_RE = re.compile(r"\*\*Auto-check:\*\*\s*(.+)")
OI_REF_RE = re.compile(r"open-items-tracker\.md#(OI-\d{3,})")
KV_RE = re.compile(r'(\w+)=("[^"]*"|\S+)')


def parse_open_items(text):
    """### OI-NNN header blocks -> {id: {status, autocheck}}. Tolerant of missing fields."""
    items = {}
    headers = list(OI_ID_RE.finditer(text))
    for i, m in enumerate(headers):
        oid = m.group(1)
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        body = text[m.end():end]
        sm = OI_STATUS_RE.search(body)
        am = OI_AUTOCHECK_RE.search(body)
        items[oid] = {
            "status": sm.group(1).upper() if sm else None,
            "autocheck": am.group(1).strip() if am else None,
        }
    return items


def parse_kv(raw):
    return {k: v.strip('"') for k, v in KV_RE.findall(raw)}


def load_fleet_json():
    """Best-effort live fleet snapshot for auto-check evaluation. (result, error)."""
    if not os.path.isfile(FLEET_STATUS_PROBE):
        return None, "fleet-status.py not found at %s" % FLEET_STATUS_PROBE
    try:
        r = subprocess.run([sys.executable, FLEET_STATUS_PROBE, "--json"],
                           capture_output=True, text=True, timeout=30)
    except Exception as e:
        return None, "fleet-status.py failed to run: %s" % e
    if r.returncode != 0:
        return None, "fleet-status.py exited %d: %s" % (r.returncode, (r.stderr or "").strip()[:200])
    try:
        return json.loads(r.stdout), None
    except Exception as e:
        return None, "fleet-status.py --json unparseable: %s" % e


def eval_autocheck(kv, fleet_json):
    """Bounded vocabulary only -- no arbitrary code execution. True/False/None (unsupported/malformed)."""
    kind = kv.get("kind")
    try:
        if kind == "registry_disabled_count":
            fleet = kv.get("fleet", "all")
            expect = int(kv.get("expect"))
            dbf = fleet_json.get("disabled_by_fleet", {}) or {}
            actual = sum(dbf.values()) if fleet == "all" else dbf.get(fleet, 0)
            return actual == expect
        if kind == "registry_field_equals":
            fleet, task_id, field, expect = kv.get("fleet"), kv.get("task_id"), kv.get("field"), kv.get("expect")
            for t in fleet_json.get("tasks", []) or []:
                if t.get("fleet") == fleet and t.get("id") == task_id:
                    actual = t.get(field)
                    if field == "enabled":
                        return str(bool(actual)).lower() == str(expect).lower()
                    return str(actual) == str(expect)
            return False  # task not present in that fleet -> condition not met
    except Exception:
        return None
    return None  # unknown kind


def fail(findings):
    print("MEMORY INTEGRITY: %d issue(s)" % len(findings))
    for f in findings:
        print("  - " + f)
    sys.exit(1)


def _git(*args):
    """Run git inside MEM. Returns stdout, or None on any failure (not a repo, no git,
    no HEAD yet). Every caller treats None as 'skip the git check'.

    encoding=utf-8/errors=replace (not the default locale codec, cp1252 on this machine):
    a memory filename or title with a byte invalid in cp1252 would otherwise raise
    UnicodeDecodeError, get swallowed below, and SILENTLY disable the whole check. Matches
    how this script already opens files and reconfigures its streams. timeout so a stuck
    index lock can never hang the daily health guard (parity with load_fleet_json)."""
    try:
        r = subprocess.run(["git"] + list(args), cwd=MEM, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=30)
    except Exception:
        return None
    return r.stdout if r.returncode == 0 else None


def head_orphans():
    """Basenames linked by HEAD's MEMORY.md but absent from HEAD's tree -- i.e. exactly the
    pointers a fresh clone would find broken. Sorted; empty when the check cannot apply.

    WHY THIS EXISTS, given check 1 already reconciles the index. Check 1 globs the
    FILESYSTEM, so it answers "is the file on this disk?" -- and a file can sit on disk,
    indexed and healthy-looking, while git has never heard of it. That is not hypothetical:
    32f3065 committed a MEMORY.md pointer without the file it points at (`git commit -am`
    stages tracked files only and silently skips new ones), the probe stayed green, and the
    dangling pointer reached the remote. A check that asks the working tree a question only
    git can answer.

    The precise failure is worth keeping straight, because check 1 is not simply blind here:
    replayed against a CLONE of 32f3065, check 1 DOES flag it -- the file is absent from that
    disk, so it looks like an ordinary orphan. But this probe runs daily via ora-health-guard
    on the machine that AUTHORED the commit, where the file is sitting right there on disk,
    untracked and healthy-looking. So check 1 is blind exactly where it runs and sighted only
    where nobody runs it. That is why this check reads HEAD instead of the disk: HEAD is the
    same everywhere, so the probe sees what every other reader sees.

    THE RULE IS HEAD-vs-HEAD, deliberately -- not "every memory file must be committed".
    Writing a memory and not having committed it yet is the normal state of a live session;
    failing on that would make this probe cry wolf on every new note and train everyone to
    ignore it. What is never legitimate is a COMMITTED pointer to a file git does not have,
    because that is broken for every reader but the machine that wrote it.

    Skips silently (returns []) when the check cannot apply: memory dir not in a git repo
    (the pre-existing probe tests run over plain temp dirs), git unavailable, no commits
    yet, or MEMORY.md not yet tracked. A probe that cannot look must not invent findings --
    this is report-only and must never crash the daily health guard.
    """
    prefix = _git("rev-parse", "--show-prefix")
    if prefix is None:
        return []  # not a git work tree -> nothing to reconcile
    prefix = prefix.strip()
    index_rel = prefix + "MEMORY.md"

    head_index = _git("show", "HEAD:" + index_rel)
    if head_index is None:
        return []  # no HEAD, or MEMORY.md not committed -> nothing committed to be wrong

    # NON-recursive ls-tree (no -r), and pathspec "." with cwd=MEM: list only the entries
    # in the memory dir's OWN level, which is exactly where the index's bare-basename links
    # (`](reference_x.md)`) must resolve. A recursive tree would flatten in a namesake from a
    # subdir -- e.g. HEAD holding `_archive/reference_x.md` but not root `reference_x.md`
    # would look satisfied while a clone's root link is broken (adversarial review, 2026-07-17).
    # (Pathspec "." not `prefix`: ls-tree resolves pathspecs against the CURRENT directory,
    # and we run with cwd=MEM; passing the repo-root-relative prefix matched 0 files and once
    # flagged all 132 memory files as orphans -- only the fixtures caught it.)
    tree = _git("ls-tree", "--name-only", "HEAD", "--", ".")
    if tree is None:
        return []
    # Non-recursive output is one name per line; subdir entries appear as the dir name (e.g.
    # "_archive"), which .endswith(".md") already excludes.
    head_files = {os.path.basename(p) for p in tree.splitlines() if p.endswith(".md")}
    head_files.discard("MEMORY.md")

    head_linked = {os.path.basename(p)
                   for p in re.findall(r"\]\(([A-Za-z0-9_./-]+\.md)\)", head_index)}
    return sorted(head_linked - head_files)


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

    # --- 1b. the same reconciliation, as GIT sees it (added 2026-07-17) ---
    for o in head_orphans():
        issues.append(
            "orphan index link IN GIT (HEAD's MEMORY.md links it; HEAD's tree lacks it -- "
            "a clone gets a broken pointer): %s" % o)

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

    # --- 4. open-items tracker: dead pointers [fail] + auto-check drift [warn] ---
    # Optional companion file -- absent tracker just means no items exist to check yet.
    tracker_items = {}
    if os.path.isfile(TRACKER):
        try:
            tracker_items = parse_open_items(open(TRACKER, encoding="utf-8").read())
        except Exception as e:
            warnings.append("open-items-tracker.md unreadable: %s" % e)

    # 4a. dead pointers -- any #OI-NNN reference elsewhere that doesn't resolve here.
    for path in glob.glob(os.path.join(MEM, "*.md")):
        name = os.path.basename(path)
        if name == "open-items-tracker.md":
            continue
        try:
            txt = open(path, encoding="utf-8").read()
        except Exception:
            continue
        for ref in sorted(set(OI_REF_RE.findall(txt))):
            if ref not in tracker_items:
                issues.append("%s references open-items-tracker.md#%s, which has no matching "
                              "row in the tracker (dead pointer)" % (name, ref))

    # 4b. auto-check drift -- OPEN items whose stated condition now mechanically matches.
    open_autochecks = [(oid, it) for oid, it in tracker_items.items()
                       if it["status"] == "OPEN" and it["autocheck"]]
    if open_autochecks:
        fleet_json, ferr = load_fleet_json()
        for oid, it in open_autochecks:
            if fleet_json is None:
                warnings.append("open-items-tracker.md#%s: auto-check could not run (%s)" % (oid, ferr))
                continue
            kv = parse_kv(it["autocheck"])
            result = eval_autocheck(kv, fleet_json)
            if result is None:
                warnings.append("open-items-tracker.md#%s: auto-check malformed or unsupported kind "
                                "(%s)" % (oid, it["autocheck"]))
            elif result is True:
                warnings.append("open-items-tracker.md#%s is marked OPEN but its auto-check now "
                                "MATCHES the closing condition (%s) -- verify and close it out"
                                % (oid, it["autocheck"]))

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
