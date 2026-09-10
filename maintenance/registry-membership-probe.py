#!/usr/bin/env python3
"""ORA registry-membership probe -- detects silent scheduled-task registry drops.

!! THIS PROBE WRITES SHARED STATE ON EVERY RUN, AND TAKES NO FLAGS. !!
    There is no argparse here, so no --help, --dry-run or --read-only. ANY
    invocation -- including one you meant as `--help` -- runs the probe for real
    and REWRITES two files every session depends on:
        ~/.claude/session-context.md      (the BEGIN/END-GENERATED-FLEET block)
        ~/.claude/maintenance/_state/fleet-roster.md
    Confirmed live 2026-09-10: a `registry-membership-probe.py --help` typed to
    inspect the interface silently ran the probe and rewrote the shared block
    from "36 live recurring | 27" to "0 live recurring | 2" -- accurate (a
    bounded fleet pause was in force) but indistinguishable, to the next session
    that loads session-context.md at startup, from a destroyed fleet.

    CONSEQUENCES, both of which have bitten:
      1. Do NOT call this from an unattended/scheduled wrapper. An automated job
         continuously rewriting a file every session reads at startup is a
         monitoring hazard, not monitoring. `maintenance/headless/run-check.py`
         deliberately EXCLUDES this probe for exactly that reason and uses
         fleet-status.py (read-only) + phantom-dispatch-probe.py instead.
      2. Do NOT run it casually to "see what it does" while a pause, rebuild or
         recovery is in progress -- the snapshot it writes becomes the new
         baseline for the NEXT run's temporal diff. Read fleet-roster.md or the
         live registry instead if you only want to look.

    If you need a read-only view of fleet membership, use `fleet-status.py`
    (--summary / --json), which reads both fleets and writes no shared state.

WHY: the 2026-06-09 fleet rebuild silently dropped registry ENTRIES
(ora-cowork-heartbeat, scheduled-task-integrity-guard) while their SKILL.md
files survived -- the heartbeat stayed dark 2026-05-31..06-10 with no alarm.
File-level guards (scheduled-task-integrity-guard) cannot see entry drops;
this probe snapshots the enabled RECURRING task ids across BOTH live
registries (dual-fleet doctrine 2026-06-10: cc = claude-code-sessions/MCP,
lams = local-agent-mode-sessions/Cowork) and alarms on any disappearance
versus the prior snapshot.

Exit 0 = no drops (snapshot refreshed). Exit 1 = [ACTION] drop detected.
The snapshot is refreshed even on a drop, so each drop alarms exactly once;
re-register the task or ratify the retirement (and note it in event_log.md).
A drop is auto-reconciled (reported INFO, exit stays 0) by EITHER of two
recent (<=14d) event_log.md signals, so a planned retirement never raises a
one-time false [ACTION]:
  1. ratified_drops -- the ceremonial token 'RATIFIED' anywhere in the drop's
     '## ' section (2026-06-11); and
  2. retired_drops  -- COMPLETED-retirement language on the SAME LINE as the task
     id (2026-07-17). ORA documents most retirements in plain prose, never the
     uppercase token -- ora-skills-reimport-watch's 2026-07-17 retirement was
     twice-logged yet still raised a false [ACTION] because only 'RATIFIED' was
     honored. Requires accomplished-fact wording ('retired', 'decommissioned',
     'retirement completed', 'registry entry deleted/removed') and NEVER a merely
     planned, hypothetical, or in-progress mention ('should retire', 'plan to
     decommission', 'pending deletion'). Two payoffs: (a) a forward-looking note
     that names a task cannot reconcile a genuine drop of it, and neither can an
     incident report ABOUT a silent drop ('disappeared'/'dropped'/'dark'); and
     (b) a two-part retirement reconciles only on its completion line, not on the
     part-1 line that still says the entry exists. Completion-only wording makes
     tense/negation parsing unnecessary.
One-time fireAt tasks are ignored -- they expire by design.

An enabled->DISABLED task (still registered, just paused) is a WARN regression,
NOT a drop -- disabling is a legitimate user action (2026-07-08). A whole registry
FILE that is absent is treated as transient for MISSING_STORE_GRACE_RUNS consecutive
runs (reinstall / session-dir rotation) before escalating to [ACTION] -- the
2026-07-05 reinstall's mid-recovery probe cried CRITICAL on a store that reappeared
hours later (2026-07-08).

ORPHANED_FILEPATH (2026-08-22): flags ANY recurring registry entry -- enabled or
DISABLED -- whose filePath no longer exists on disk. task-folder-registration-
probe.py's ORPHANED_REGISTRATION check covers similar ground but is deliberately
enabled-only ("won't fire, not actively dangerous"), so a DISABLED/pending-
retirement entry with a dangling filePath is invisible to it by design. Confirmed
case: the ora-passed-deal-tracker LAMS entry sat enabled:false with its SKILL.md
already archived away (retirement step 1 of 2 done, registry row never dropped)
and nothing alarmed. This check has no reconciliation window (unlike drops) --
once the registry row is actually deleted, the check has nothing left to flag,
so it self-clears on completion rather than needing a RATIFIED/retired-prose gate.

Run daily from the ora-setup-audit STEP 1 block. First run writes a baseline.
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shared"))
try:
    import store_discovery as _sd
except Exception:
    _sd = None  # fail-open: discover_store() returns None -> missing-store path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_state")
STATE = os.path.join(STATE_DIR, "registry-membership.json")
LOG = os.path.join(STATE_DIR, "registry-membership.log")

# session-context.md roster is GENERATED between these markers (audit 2026-06-11:
# hand-edited fleet counts were the recurring doctrine-drift root cause).
SESSION_CONTEXT = os.path.join(os.path.expanduser("~"), ".claude", "session-context.md")
BEGIN_MARKER = "<!--BEGIN-GENERATED-FLEET-->"
END_MARKER = "<!--END-GENERATED-FLEET-->"

# Auto-ratification of planned retirements (2026-06-11): a drop is ratified iff a
# recent event_log entry both contains the literal token 'RATIFIED' and names the
# task id. Conservative by design -- anything unparseable is NOT ratified.
EVENT_LOG = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                         "C--Users-Owner-OneDrive---Oxford-Capital-Partners",
                         "memory", "event_log.md")
RATIFY_WINDOW_DAYS = 14

# A whole registry FILE vanishing is treated as transient (reinstall / session-dir
# rotation / app-not-yet-initialized) until it persists across this many consecutive
# probe runs -- the 2026-07-05 reinstall's mid-recovery probe cried CRITICAL on a
# store that reappeared hours later. Per-ENTRY drops still alarm on the first run.
MISSING_STORE_GRACE_RUNS = 2


def ratified_drops(log_text, ids, today, window_days=RATIFY_WINDOW_DAYS):
    """Subset of `ids` ratified by a recent event_log entry.

    An entry = a '## YYYY-MM-DD ...' header section (append-event-log.py's
    enforced header level -- this previously read '### ' and so never matched
    a real entry; fixed 2026-07-16). Requires the literal token 'RATIFIED'
    (case-sensitive) AND the exact task id in the same entry, with the entry
    dated within `window_days` of `today`. Pure function."""
    out = set()
    for chunk in log_text.split("\n## ")[1:]:
        try:
            d = datetime.date.fromisoformat(chunk[:10])
        except ValueError:
            continue
        if (today - d).days > window_days or "RATIFIED" not in chunk:
            continue
        for i in ids:
            if i and i in chunk:
                out.add(i)
    return out


def _leading_date(line):
    """Date from a line's inline 'YYYY-MM-DD' prefix (after stripping leading
    '-', '*', whitespace), else None. ORA logs bullet/paragraph entries like
    '2026-07-17: ...' and '- **2026-07-17 ...' under an older '## ' header, so a
    line's own date can differ from its section header. Pure."""
    s = line.lstrip("-* \t")
    try:
        return datetime.date.fromisoformat(s[:10])
    except ValueError:
        return None


def _retirement_completed(low):
    """True iff a lowercased event_log line asserts a COMPLETED retirement/removal
    (accomplished fact), not a planned, hypothetical, or in-progress one.

    Every clause is past-tense/perfect, so contemplation never qualifies:
      - 'retired'/'decommissioned'/'deregistered' -- past-participle verbs. The
        infinitive/present forms ('retire', 'decommission') are deliberately NOT
        matched, so 'should retire', 'plan to decommission', 'do not retire' all
        fail.
      - 'retirement' + 'completed' -- the noun alone is ambiguous ('retirement
        plan'); pairing it with 'completed' pins it to done. ('complete' is
        avoided -- it is a substring of 'incomplete'.)
      - 'registry' + 'deleted'/'removed' -- the registry entry is gone. Note
        'deleted'/'removed' (past) exclude 'deletion'/'deleting'/'pending
        deletion'/'removing', so a part-1 'entry still exists, pending deletion'
        line does NOT qualify -- only the part-2 completion line does.
    Requiring completion wording is what makes tense/negation parsing
    unnecessary. Pure."""
    if "retired" in low or "decommissioned" in low or "deregistered" in low:
        return True
    if "retirement" in low and "completed" in low:
        return True
    if "registry" in low and ("deleted" in low or "removed" in low):
        return True
    return False


def retired_drops(log_text, ids, today, window_days=RATIFY_WINDOW_DAYS):
    """Subset of `ids` reconciled by a recent event_log LINE that names the task
    id AND asserts a COMPLETED retirement (_retirement_completed) on the SAME line.

    Complements ratified_drops: that requires the ceremonial 'RATIFIED' token in
    a '## ' section, but ORA usually documents a retirement in plain prose
    ('... retirement completed ...', 'registry entry deleted ...'). Same-line
    coupling keeps it tight -- a section that merely mentions task A in one line
    and retires task B in another does NOT reconcile A -- and the completion-only
    gate keeps a forward-looking 'should retire ora-A next quarter' or an
    in-progress 'ora-A pending deletion' from reconciling a genuine drop of A.

    Date per line, newest-wins: an inline leading 'YYYY-MM-DD' wins; otherwise the
    line inherits the nearest '## YYYY-MM-DD' header above it. Eligible only if
    that date is within `window_days` of `today`. Pure."""
    ids = [i for i in ids if i]
    if not ids:
        return set()
    out, header_date = set(), None
    for raw in log_text.splitlines():
        stripped = raw.strip()
        is_header = stripped.startswith("## ")
        if is_header:
            try:
                header_date = datetime.date.fromisoformat(stripped[3:13])
            except ValueError:
                header_date = None
        if not _retirement_completed(stripped.lower()):
            continue
        d = header_date if is_header else (_leading_date(stripped) or header_date)
        if d is None or (today - d).days > window_days:
            continue
        for i in ids:
            if i in raw:
                out.add(i)
    return out


def discover_store(store):
    """Biggest-then-newest scheduled-tasks.json for a store. Delegates to
    maintenance/_shared/store_discovery.py (single source of truth 2026-07-09;
    roots live in scheduler-stores.json). None when the helper or store is
    unavailable -- callers already treat None as a missing store."""
    return _sd.discover_store(store) if _sd else None


def enabled_recurring(path):
    """Sorted enabled task ids with a cron expression (one-time fireAt excluded)."""
    detail = enabled_recurring_detail(path)
    return None if detail is None else [i for i, _ in detail]


def enabled_recurring_detail(path):
    """Sorted (id, cron) pairs for enabled recurring tasks (one-time fireAt excluded)."""
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception:
        return None
    out = []
    for t in d.get("scheduledTasks", []) or []:
        expr = t.get("cronExpression")
        is_cron = isinstance(expr, str) and len(expr.split()) == 5
        if t.get("enabled") and is_cron:
            out.append((t.get("id") or "?", expr))
    return sorted(out)


def enabled_onetime_detail(path):
    """Sorted (id, '@YYYY-MM-DD') pairs for ENABLED one-time (fireAt) tasks.
    PRESENTATION ONLY (2026-07-18): one-time tasks stay deliberately EXCLUDED from
    the membership/drop sets (they expire by design and would raise spurious drops),
    but omitting them from the generated roster made session-context understate the
    live fleet — LAMS read 19 while fleet-status.py counted 21 on 07-17/18 because
    two enabled future-fireAt tasks were invisible here. None/[] on unreadable."""
    import datetime as _dt
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception:
        return None
    out = []
    for t in d.get("scheduledTasks", []) or []:
        expr = t.get("cronExpression")
        is_cron = isinstance(expr, str) and len(expr.split()) == 5
        fa = t.get("fireAt")
        if t.get("enabled") and not is_cron and fa:
            try:
                if isinstance(fa, (int, float)):  # epoch ms in the registry file
                    stamp = _dt.datetime.fromtimestamp(
                        fa / 1000, _dt.timezone.utc).strftime("%Y-%m-%d")
                else:  # ISO string
                    stamp = str(fa)[:10]
            except Exception:
                stamp = "?"
            out.append((t.get("id") or "?", "@%s" % stamp))
    return sorted(out)


def all_recurring_states(path):
    """{id: enabled_bool} for every recurring (5-field cron) task in the store,
    regardless of enabled state. None if unreadable. Lets the caller tell a
    DISABLED task apart from a DELETED one -- both leave the enabled set."""
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception:
        return None
    out = {}
    for t in d.get("scheduledTasks", []) or []:
        expr = t.get("cronExpression")
        if isinstance(expr, str) and len(expr.split()) == 5:
            out[t.get("id") or "?"] = bool(t.get("enabled"))
    return out


def all_recurring_entries(path):
    """[{'id','filePath','enabled'}] for every recurring (5-field cron) task in
    the store, regardless of enabled state. None if unreadable. Companion to
    all_recurring_states() -- that one drops filePath, which orphaned_filepaths()
    needs."""
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception:
        return None
    out = []
    for t in d.get("scheduledTasks", []) or []:
        expr = t.get("cronExpression")
        if isinstance(expr, str) and len(expr.split()) == 5:
            out.append({"id": t.get("id") or "?", "filePath": t.get("filePath"),
                        "enabled": bool(t.get("enabled"))})
    return out


def orphaned_filepaths(entries, exists_fn=os.path.isfile):
    """entries: [{'id','filePath','enabled'}] (any enabled state). Sorted ids
    whose filePath is set but does not resolve on disk.

    Deliberately NOT enabled-only, unlike task-folder-registration-probe.py's
    ORPHANED_REGISTRATION -- the failure mode this closes is a DISABLED /
    pending-retirement row whose SKILL.md is already gone, which an
    enabled-only check treats as harmless ("won't fire"). A dangling filePath
    on a row that is otherwise done being retired is exactly the half-executed
    state that should keep alarming until the row itself is deleted. Pure."""
    return sorted(
        e["id"] for e in entries
        if e.get("filePath") and not exists_fn(e["filePath"])
    )


def classify_absent(prior_enabled_ids, current_states):
    """Split ids that left the ENABLED set into (disabled_regressions, true_drops).

    current_states = {id: enabled} for all recurring tasks now in the store. A
    prior-enabled id still present but disabled => regression (e.g. a task that came
    back DISABLED after a recovery); absent from the registry entirely => true drop
    (the 2026-06-09 silent-drop failure mode). Pure."""
    regressions, drops = [], []
    for i in prior_enabled_ids:
        if i in current_states and not current_states[i]:
            regressions.append(i)
        elif i not in current_states:
            drops.append(i)
    return sorted(regressions), sorted(drops)


def next_missing_streaks(prior_streaks, missing_labels, all_labels):
    """Consecutive-run absence counter per store label: +1 while missing, 0 when
    present. Pure."""
    return {label: (prior_streaks.get(label, 0) + 1) if label in missing_labels else 0
            for label in all_labels}


def missing_is_actionable(streak, grace=MISSING_STORE_GRACE_RUNS):
    """A whole-store absence escalates to [ACTION] only once it has persisted across
    `grace` consecutive probe runs."""
    return streak >= grace


FLEET_ROSTER_FILE = os.path.join(os.path.expanduser("~"), ".claude", "maintenance",
                                 "_state", "fleet-roster.md")


def render_fleet_block(detail, ts, onetime=None):
    """COMPACT session-context block (markers included): per-fleet COUNTS + pointer to
    the generated full roster file. Compressed 2026-07-29 (Phase 4 of the approved
    target-architecture blueprint): the per-task id+cron listing cost ~1k recurring
    tokens EVERY session and duplicated the live registries; the full listing now
    lives in FLEET_ROSTER_FILE (render_fleet_roster, regenerated in the same run) and
    loads on demand. Counts still reconcile with fleet-status.py's enabled totals
    (recurring + pending one-time, the 2026-07-18 undercount fix preserved)."""
    labels = {"cc": "CC/MCP", "lams": "LAMS/Cowork"}
    onetime = onetime or {}
    parts = []
    for label in ("cc", "lams"):
        tasks = detail.get(label, [])
        seg = "%s — %d live recurring" % (labels.get(label, label), len(tasks))
        ot = onetime.get(label) or []
        if ot:
            seg += " · +%d pending one-time" % len(ot)
        parts.append(seg)
    return "\n".join([
        BEGIN_MARKER,
        "  **Live fleet summary** (generated by registry-membership-probe.py %s — "
        "do NOT hand-edit between markers; counts come from the live registries):" % ts,
        "  " + " | ".join(parts),
        "  Per-task ids/crons: read `~/.claude/maintenance/_state/fleet-roster.md` "
        "(regenerated with this block) or the live registry — NEVER answer per-task "
        "fleet questions from memory.",
        END_MARKER])


def render_fleet_roster(detail, ts, onetime=None):
    """FULL per-task roster (the pre-2026-07-29 block body) for FLEET_ROSTER_FILE —
    generated artifact, overwritten each run, never hand-edited."""
    labels = {"cc": "CC/MCP", "lams": "LAMS/Cowork"}
    onetime = onetime or {}
    lines = ["# Live fleet roster (GENERATED by registry-membership-probe.py %s — "
             "do not hand-edit; counts/crons come from the live registries)" % ts, ""]
    for label in ("cc", "lams"):
        tasks = detail.get(label, [])
        names = " · ".join("%s (%s)" % (i, c) for i, c in tasks) or "—"
        line = "%s — %d live recurring: %s" % (labels.get(label, label), len(tasks), names)
        ot = onetime.get(label) or []
        if ot:
            line += " · +%d pending one-time: %s" % (
                len(ot), " · ".join("%s (%s)" % (i, s) for i, s in ot))
        lines.append(line)
        lines.append("")
    return "\n".join(lines)


def splice_generated_block(content, block):
    """Replace marker-to-marker span with `block`. (content, False) if markers are
    absent, BEGIN is duplicated, or no END follows BEGIN — never guess an anchor."""
    b = content.find(BEGIN_MARKER)
    if b == -1 or content.find(BEGIN_MARKER, b + len(BEGIN_MARKER)) != -1:
        return content, False
    e = content.find(END_MARKER, b)
    if e == -1:
        return content, False
    return content[:b] + block + content[e + len(END_MARKER):], True


def main():
    current, current_detail, current_states, missing_stores = {}, {}, {}, []
    current_onetime = {}
    current_entries = {}
    all_labels = ["cc", "lams"]
    for label, store in (("cc", "claude-code-sessions"),
                         ("lams", "local-agent-mode-sessions")):
        p = discover_store(store)
        detail = enabled_recurring_detail(p) if p else None
        if detail is None:
            missing_stores.append(label)
            continue
        current[label] = [i for i, _ in detail]
        current_detail[label] = detail
        current_states[label] = all_recurring_states(p) or {}
        current_onetime[label] = enabled_onetime_detail(p) or []
        current_entries[label] = all_recurring_entries(p) or []

    prior, prior_streaks = {}, {}
    if os.path.isfile(STATE):
        try:
            _s = json.load(open(STATE, encoding="utf-8"))
            prior = _s.get("fleets", {})
            prior_streaks = _s.get("missing_streaks", {})
        except Exception:
            prior, prior_streaks = {}, {}

    # Split ids that left the ENABLED set into disabled-regressions (still registered,
    # just paused -> WARN) and true drops (gone from the registry -> [ACTION]).
    regressions, drops, adds = {}, {}, {}
    for label, ids in current.items():
        before = set(prior.get(label, []))
        now = set(ids)
        absent = sorted(before - now)
        if absent:
            reg, drp = classify_absent(absent, current_states.get(label, {}))
            if reg:
                regressions[label] = reg
            if drp:
                drops[label] = drp
        if now - before and prior:
            adds[label] = sorted(now - before)
    # a whole store vanishing (in prior, absent now) is a missing-store event
    for label in prior:
        if label not in current and label not in missing_stores:
            missing_stores.append(label)

    streaks = next_missing_streaks(prior_streaks, set(missing_stores), all_labels)

    orphaned = {}
    for label, entries in current_entries.items():
        found = orphaned_filepaths(entries)
        if found:
            orphaned[label] = found

    ts = datetime.datetime.now().isoformat(timespec="seconds")
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump({"ts": ts, "fleets": current, "missing_streaks": streaks},
                  f, indent=1)

    # ROSTER ANNOTATION (2026-08-14). This line used to read a bare `cc=29 lams=26`.
    # One-time fireAt tasks are excluded from the recurring set BY DESIGN (see
    # enabled_onetime_detail's note), so those numbers are correct but do NOT match
    # `list_scheduled_tasks`, which returns recurring + pending one-time. The
    # session-context block and the roster file have carried "+N pending one-time"
    # since 2026-07-18, but THIS log line never did — and it is the artifact monitors
    # actually read. automation-health-monitor re-derived "lams=26 vs live 28 = the
    # 2 one-time entries" from scratch on 2026-08-14, at least the second time that
    # reconciliation had been done by hand. Annotate it at the source instead.
    def _roster(label):
        rec = len(current.get(label, []))
        ot = len(current_onetime.get(label) or [])
        return f"{label}={rec}" + (f"(+{ot} one-time={rec + ot})" if ot else "")

    line = (f"{ts} {_roster('cc')} {_roster('lams')}"
            f" drops={drops or '-'} regressions={regressions or '-'} adds={adds or '-'}"
            f" missing_stores={missing_stores or '-'} orphaned_filepaths={orphaned or '-'}")
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        # HARDENED 2026-08-05: this used to be a bare `pass` -- a log-append
        # failure was invisible on stdout while STATE (registry-membership.json)
        # still wrote fine, so the run looked clean even though its append-only
        # audit trail silently stopped growing (found during the 2026-08-04/
        # 08-05 ora-task-integrity-guard investigation: this file's newest line
        # was stuck at 2026-08-03T16:20:04 for 2 consecutive days with zero
        # WARN anywhere). Printing WARN matches the fail-soft convention already
        # used below for the fleet-roster and session-context writes in this
        # same function -- SKILL.md STEP 1.5 already treats any WARN line here
        # as worth surfacing, so this alone closes most of the silent-miss gap.
        print(f"  WARN registry-membership.log append failed: {e}")

    print("ORA REGISTRY-MEMBERSHIP PROBE (dual-fleet)")
    for label in ("cc", "lams"):
        rec = len(current.get(label, []))
        ot = len(current_onetime.get(label) or [])
        tail = (f" (+{ot} pending one-time = {rec + ot} total, which is what "
                f"list_scheduled_tasks returns)" if ot else "")
        print(f"  {label}: {rec} enabled recurring{tail}")

    # Write the FULL roster file first (generated artifact; fail-soft), then the
    # compact session-context block that points at it (Phase 4, 2026-07-29).
    try:
        os.makedirs(os.path.dirname(FLEET_ROSTER_FILE), exist_ok=True)
        tmp_r = FLEET_ROSTER_FILE + ".tmp"
        with open(tmp_r, "w", encoding="utf-8") as f:
            f.write(render_fleet_roster(current_detail, ts, current_onetime))
        os.replace(tmp_r, FLEET_ROSTER_FILE)
    except Exception as e:
        print(f"  WARN fleet-roster file write skipped: {e}")
    # Regenerate session-context.md's fleet roster (fail-soft: a context-file
    # problem must never mask a membership drop).
    try:
        if os.path.isfile(SESSION_CONTEXT):
            doc = open(SESSION_CONTEXT, encoding="utf-8").read()
            new_doc, replaced = splice_generated_block(
                doc, render_fleet_block(current_detail, ts, current_onetime))
            if not replaced:
                print("  WARN session-context.md has no generated-fleet markers -- "
                      "roster not synced.")
            elif new_doc != doc:
                tmp = SESSION_CONTEXT + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(new_doc)
                os.replace(tmp, SESSION_CONTEXT)  # atomic — never leave a torn context file
                print("  INFO session-context.md fleet roster regenerated.")
    except Exception as e:
        print(f"  WARN session-context update skipped: {e}")

    # ORPHANED_FILEPATH is a direct point-in-time check on the current registry --
    # unlike drops/regressions/adds it needs no prior snapshot to diff against, so
    # it must fire even on the baseline (first-ever) run, before the `not prior`
    # early return below.
    bad = False
    if orphaned:
        for label, ids in orphaned.items():
            print(f"  [ACTION] ORPHANED_FILEPATH in {label}: {', '.join(ids)} -- "
                  "registry row's filePath no longer exists on disk (file deleted/"
                  "moved without dropping the registry entry -- e.g. a half-executed "
                  "retirement). Complete the retirement (delete_scheduled_task) or "
                  "restore the file. Checked regardless of enabled state.")
            bad = True

    if not prior:
        print("  BASELINE written -- no prior snapshot to diff against.")
        return 1 if bad else 0
    if adds:
        for label, ids in adds.items():
            print(f"  INFO new in {label}: {', '.join(ids)}")
    # Recovery/flux signal: any membership change means the roster is a moving target.
    if adds or drops or regressions or missing_stores:
        print("  INFO fleet membership CHANGED this run -- if a recovery/rebuild is in "
              "progress, re-run the probe until two consecutive clean runs before "
              "trusting the generated roster as settled.")
    if missing_stores:
        for label in missing_stores:
            streak = streaks.get(label, 1)
            if missing_is_actionable(streak):
                print(f"  [ACTION] registry store '{label}' absent for {streak} "
                      f"consecutive probe runs (>= {MISSING_STORE_GRACE_RUNS}) -- fleet "
                      "is dark or the store moved; investigate.")
                bad = True
            else:
                print(f"  WARN registry store '{label}' not found (absence run {streak}/"
                      f"{MISSING_STORE_GRACE_RUNS}) -- treating as transient (reinstall / "
                      "session-dir rotation); escalates to [ACTION] if still absent next "
                      "run.")
    if regressions:
        for label, ids in regressions.items():
            print(f"  WARN enabled->DISABLED in {label}: {', '.join(ids)} -- still "
                  "registered but no longer firing. Deliberate pause or a restore that "
                  "came back disabled? Re-enable via update_scheduled_task or note the "
                  "pause. (NOT a silent drop; no exit-1.)")
    if drops:
        reconciled = set()
        try:
            if os.path.isfile(EVENT_LOG):
                all_ids = sorted({i for ids in drops.values() for i in ids})
                today = datetime.date.today()
                log_text = open(EVENT_LOG, encoding="utf-8").read()
                # Two independent reconciliation signals (see module docstring):
                # ceremonial 'RATIFIED' token, or plain-prose retirement verb.
                reconciled = (ratified_drops(log_text, all_ids, today)
                              | retired_drops(log_text, all_ids, today))
        except Exception as e:  # fail-loud: an unreadable log reconciles nothing
            print(f"  WARN reconciliation check skipped: {e}")
        for label, ids in drops.items():
            rat = [i for i in ids if i in reconciled]
            hot = [i for i in ids if i not in reconciled]
            if rat:
                print(f"  INFO reconciled drop from {label} (recent event_log "
                      f"retirement/RATIFIED entry <= {RATIFY_WINDOW_DAYS}d): "
                      f"{', '.join(rat)}")
            if hot:
                print(f"  [ACTION] DROPPED from {label} registry: {', '.join(hot)} -- "
                      "re-register on the owning surface or ratify the retirement "
                      "(log to event_log.md). This is the 2026-06-09 silent-drop "
                      "failure mode.")
                bad = True
    if not bad:
        print("  OK -- no actionable drift.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
