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

# MEMORY.md size gates. HARD is a REAL tool constraint: past it the index no longer fits
# in one Read call and index maintenance itself becomes unreliable. WARN is a runway
# marker BELOW that cliff -- it exists to fire while there is still time to act, not to
# describe a target size. Bytes, not KiB, to match how du/wc report it.
#
# RECALIBRATED 2026-07-31 (warn 17100 -> 21500), Gabriel's in-turn direction. The old
# 17100 was calibrated against a much smaller corpus and never rescaled, so it had become
# UNSATISFIABLE without destroying the index. Measured against the live 176-file corpus
# (182 links) at the time of recalibration:
#   * stripping EVERY hook (the prose after each link), leaving only bullets + links +
#     titles, floors the file at 15183 bytes -- just 1917 below the old 17100 WARN. So
#     satisfying 17100 allowed ~10 characters of description per entry across 182 entries.
#     The hook is exactly what recall reads to judge relevance; at that length the file is
#     a list of filenames, not an index. The gate's own purpose defeats the file's.
#   * the only other way to reach 17100 was deleting ~30 entries (17% of all memories, at
#     a measured mean of 112.4 bytes/entry) -- i.e. losing recall to satisfy a number.
#   * archiving the CLOSED/superseded entries (the usual escape hatch) was checked
#     file-by-file and does NOT work unaided: all 10 candidates have inbound refs from
#     OTHER LIVE memory files, so archiving orphans real pointers unless those files are
#     repaired in the same pass.
# Same failure class as the CLAUDE.md word budget -- see the memory
# reference_claude_md_word_budget_is_a_floor.md: a WARN sitting at/below the honest floor
# reads as "approaching a limit" and drives trimming that cuts load-bearing content. Its
# ratified point 4 -- "if the WARN line itself is the irritant, the honest fix is
# recalibrating the constant upward, not shrinking the file to satisfy a marker" -- is
# what this change implements.
#
# 21500 leaves ~2900 bytes (~26 entries) of runway below HARD. It is deliberately close
# enough to fire soon: the corpus grows monotonically (~112 bytes of index per new memory)
# and HARD does NOT scale, so a real structural decision IS approaching. When WARN fires
# the lever is archival-with-inbound-ref-repair or splitting the index -- NOT prose
# trimming, which is now known to buy almost nothing. NOTE: splitting is currently blocked
# by check 1 below, which requires every top-level *.md to be linked from MEMORY.md
# ITSELF; a sub-index would leave every file it lists reported as "unlisted". Amending
# check 1 to follow sub-indexes is the structural fix and is a separate, signed-off change.
MEMORY_WARN_BYTES = 21500     # runway marker below HARD (see calibration above)
MEMORY_HARD_BYTES = 24400     # 24.4KB Read-tool limit -- a real constraint, do not raise

CANON_RECIPIENTS = {"ggoldberg@oxfordra.net", "egoldberg@oxfordra.net"}
RECIPIENT_DRIFT_EXEMPT_FILES = {
    "event_log.md",
    "project_autonomy_gate_indirection_ceiling_followup.md",
}
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
        # Last match wins, not first: a section can narrate an inline status update
        # (e.g. "Status: OPEN" ... later in the same body ... "Status: CLOSED.") rather
        # than moving to a fresh Closed-table section. Reading the first match would
        # silently misclassify an actually-closed item as still open (found live on
        # OI-016, 2026-07-27).
        sm_all = list(OI_STATUS_RE.finditer(body))
        am = OI_AUTOCHECK_RE.search(body)
        items[oid] = {
            "status": sm_all[-1].group(1).upper() if sm_all else None,
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
                           capture_output=True, text=True, timeout=30,
                           encoding="utf-8", errors="replace")
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


SUBINDEX_PREFIX = "INDEX_"   # top-level sub-index files, e.g. INDEX_reference.md
_LINK_RE = re.compile(r"\]\(([A-Za-z0-9_./-]+\.md)\)")


def _links_in(text):
    """Set of linked memory basenames in a markdown body. Pure."""
    return {os.path.basename(p) for p in _LINK_RE.findall(text or "")}


def collect_indexed_links(index_text, mem_dir):
    """(links, subindexes_followed) -- every memory basename reachable from the
    index: MEMORY.md's own links, unioned with the links of each INDEX_*.md that
    MEMORY.md ITSELF links.

    WHY: MEMORY.md is read whole into every session and is bounded by the
    24.4KB Read-tool limit, which the corpus was days from hitting (2026-08-03).
    Splitting a section into a sub-index is the only lever that scales, but
    check 1 previously reconciled against MEMORY.md alone, so every file a
    sub-index listed came back as "unlisted file" -- which is precisely why the
    split was recorded as BLOCKED in reference_memory_index_size_gate_is_a_runway_marker.

    ONE LEVEL, and only sub-indexes the root index actually links. Both limits
    are deliberate: a stray INDEX_*.md dropped into the directory cannot grant
    itself -- or anything it lists -- coverage, so it keeps showing up as an
    unlisted file until the root index adopts it. Chaining would let a file
    smuggle in arbitrary coverage two hops from anything a human reviews.

    A sub-index that is linked but MISSING is not swallowed here: it stays in
    `links`, so check 1 reports it as an ordinary orphan pointer. Pure apart
    from reading the sub-index files.
    """
    links = _links_in(index_text)
    followed = []
    for name in sorted(links):          # sorted() copies -- safe to grow `links` inside
        if not name.startswith(SUBINDEX_PREFIX):
            continue
        try:
            with open(os.path.join(mem_dir, name), encoding="utf-8") as fh:
                links |= _links_in(fh.read())
        except Exception:
            continue                    # missing/unreadable -> reported as an orphan below
        followed.append(name)
    return links, followed


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

    # Sub-index aware, matching check 1 (2026-08-03). Read each followed sub-index
    # from HEAD too, never from disk: the whole point of this check is to see what a
    # CLONE sees, and a sub-index sitting uncommitted on the authoring machine would
    # otherwise vouch for pointers no other reader can resolve -- reintroducing, one
    # level down, exactly the 32f3065 failure this function exists to catch.
    head_linked = _links_in(head_index)
    for name in sorted(head_linked):
        if not name.startswith(SUBINDEX_PREFIX):
            continue
        sub = _git("show", "HEAD:" + prefix + name)
        if sub is not None:
            head_linked |= _links_in(sub)
    return sorted(head_linked - head_files)


def main():
    if not os.path.isdir(MEM):
        sys.stderr.write("[ACTION] memory-integrity-probe: memory dir not found: %s\n" % MEM)
        sys.exit(2)

    issues, warnings = [], []

    # --- 0. size gate --- MEMORY.md is read whole into every session's context, so its
    # byte size (not line count -- `·` separators and other non-ASCII are multi-byte in
    # UTF-8) is bounded on both ends: WARN past the compaction target, hard-fail only if
    # it would no longer fit in one Read call.
    try:
        idx_bytes = os.path.getsize(INDEX)
    except OSError as e:
        sys.stderr.write("[ACTION] cannot stat MEMORY.md: %s\n" % e)
        sys.exit(2)
    if idx_bytes > MEMORY_HARD_BYTES:
        issues.append(
            "MEMORY.md is %d bytes, over the %d-byte Read-tool limit -- it no longer "
            "fits in one Read call; compact now, not on the next pass" % (idx_bytes, MEMORY_HARD_BYTES))
    elif idx_bytes > MEMORY_WARN_BYTES:
        warnings.append(
            "MEMORY.md is %d bytes, past the %d-byte runway marker (%d bytes left before "
            "the %d-byte Read-tool limit). The lever here is ARCHIVAL (move dead entries "
            "to _archive/ AND repair the inbound refs in other memory files, which is what "
            "makes it non-trivial) or SPLITTING the index -- NOT prose trimming, which is "
            "measured to buy almost nothing (see the calibration comment on "
            "MEMORY_WARN_BYTES). Do not delete live pointers to satisfy this number." % (
                idx_bytes, MEMORY_WARN_BYTES, MEMORY_HARD_BYTES - idx_bytes, MEMORY_HARD_BYTES))

    # --- 1. index reconciliation ---
    try:
        idx = open(INDEX, encoding="utf-8").read()
    except Exception as e:
        sys.stderr.write("[ACTION] cannot read MEMORY.md: %s\n" % e)
        sys.exit(2)
    linked, subindexes = collect_indexed_links(idx, MEM)
    present = {os.path.basename(p) for p in glob.glob(os.path.join(MEM, "*.md"))}
    present.discard("MEMORY.md")  # the root index is not an entry in itself
    # ...and a SUB-index legitimately links back home ("Sub-index of MEMORY.md"), which
    # would otherwise make the root index look like an orphan pointer to a missing file.
    # Discard from both sides, not just `present` (found by the 2026-08-03 split itself).
    linked.discard("MEMORY.md")

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
    # SANDBOX ISOLATION (2026-07-29): the delegate scans its OWN live build_targets, not this
    # probe's MEM dir -- so under ORA_MEMORY_DIR (test fixtures) live-tree drift bled into every
    # sandboxed expectation and failed 3 hook test files (the 2026-07-29 pre-push gate incident).
    # Delegation runs only against the real memory dir. encoding pinned utf-8/errors=replace:
    # the delegate's drift output quotes file excerpts (≥, →, curly quotes) that crashed the
    # default cp1252 pipe with UnicodeDecodeError -- same fix class as run_git() at line ~158.
    if os.path.isfile(GOV_PROBE) and not os.environ.get("ORA_MEMORY_DIR"):
        r = subprocess.run([sys.executable, GOV_PROBE, "--quiet"],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
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
        # Skip files that legitimately document a historical recipient issue that was fixed,
        # rather than a live routing config:
        #   - event_log.md: narrates historical recipient drift that was fixed.
        #   - project_autonomy_gate_indirection_ceiling_followup.md: quotes the double-@
        #     spoofing PoC (`attacker@evilhost.com@oxfordra.net`) that the 2026-07-17 Gate 1
        #     fix closed -- an illustrative attack string, not a real digest recipient.
        if name not in RECIPIENT_DRIFT_EXEMPT_FILES and any(k in low for k in ("recipient", "digest", "send to", "distribution")):
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
    # Only text that looks like a real kind=... attempt is evaluated -- the convention's
    # documented "no auto-check configured" placeholder is the literal word "none" (with
    # or without trailing prose), which is not itself a malformed kind= attempt and must
    # not be reported as one (found live on OI-009/016/021/022/024/025, 2026-07-27).
    open_autochecks = [(oid, it) for oid, it in tracker_items.items()
                       if it["status"] == "OPEN" and it["autocheck"] and "kind=" in it["autocheck"]]
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
