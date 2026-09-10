# Ground-Truth Auditor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `ora-ground-truth-auditor` -- a nightly CC/MCP scheduled task that re-derives every claim made by the previous 24h of scheduled runs from primary sources and reports on IDEMPOTENCY, CLAIM ACCURACY, STALENESS, and FRESHNESS OF INPUTS.

**Architecture:** Two deterministic Python modules (Stage 0 run-index, Stage 1 side-effect extraction) plus a model-resolution ladder module, all covered by plain-Python tests (house style: no pytest). A SKILL.md then drives the live agent session through verifier dispatch, the four axes, digest composition, and the approval gate. Landed disabled and appended to the 2026-09-11 fleet-resume list.

**Tech Stack:** Python 3.13 (stdlib only -- `argparse`, `json`, `glob`, `re`, `datetime`), existing `maintenance/_shared/store_discovery.py`, `maintenance/allocate-oi-id.py`, `scheduled-tasks/_shared/send-via-outlook.ps1`, the `evidence-dossier-drafting` skill.

## Global Constraints

- Working directory for every task: `C:/Users/Owner/.claude/.claude/worktrees/ground-truth-auditor`, branch `feat/ground-truth-auditor` (already exists, spec committed at `eabb551`). Do not create a new worktree.
- Claim `ground-truth-auditor` is held by this session (renew with `python hooks/lib/claim_work.py renew ground-truth-auditor` if a task runs long).
- `run_id` format: `"{fleet}:{task_id}:{last_scheduled_for}"`, keyed on `lastScheduledFor` never `lastRunAt` (spec Sec 3.6).
- Task-to-session join tolerance: `abs(createdAt_ms - lastRunAt_ms) <= 2000` (spec Sec 3.5a). Never use `notifySessionId` -- it is a stale registration-time field.
- CC transcript join: session's `cliSessionId` -> `<cliSessionId>.jsonl`, searched across **every** `~/.claude/projects/*` directory, top-level files only (spec Sec 3.4).
- LAMS transcript join: session's own `sessionId` (already carries the `local_` prefix -- never re-add it) -> `<sessionId>/audit.jsonl`, in the same directory as the LAMS `scheduled-tasks.json` (spec Sec 3.4/9 R1).
- Join-rate floor (spec Sec 9 R1a): >=90% at window <=24h, >=60% at window <=72h, >=30% beyond that. `total_count == 0` is trivially OK.
- Model floor ladder (spec Sec 5 Stage 2): registry `model` -> SKILL.md `[MODEL: ...]` tag -> session record `model` -> unresolved means verify at Fable (`claude-fable-5-1`), never a cheaper guess.
- Self-exclusion: task id `ora-ground-truth-auditor` is always dropped from its own index (spec Sec 5 Stage 4).
- Digest routing: `ggoldberg@oxfordra.net` only, no cc (CLAUDE.md Email & scheduler canon).
- Any retraction email or published-page edit is drafted and named in the digest, **never sent or applied** (Hard Invariant 1, spec Sec 7).
- Cron: `0 4 * * *` ET.
- Landed `enabled: false`; appended as item 38 to `scheduled-tasks/ora-routine-pause-resume-2026-09-11/SKILL.md` (spec Sec 4) -- coordinate with session `9ca9fdea`'s `hooks-override-auth` claim on that path before editing (Task 11).
- Test house style: plain Python, no pytest, `importlib.util.spec_from_file_location` to load the hyphenated module under test, a `check(label, cond, detail)` accumulator, exit 1 on any `FAILURES`.

---

## Task 1: Stage 0 -- window sizing and run_id construction

**Files:**
- Create: `maintenance/ground-truth-run-index.py`
- Test: `maintenance/test-ground-truth-run-index.py`

**Interfaces:**
- Produces: `build_run_id(fleet: str, task_id: str, last_scheduled_for: str) -> str`; `decide_window_hours(now: datetime, last_auditor_run_at: datetime|None, cc_tasks: list[dict], lams_tasks: list[dict], default_hours: float = 24) -> tuple[float, str]`; `_parse_iso(ts: str|None) -> datetime|None`; module constants `DEFAULT_WINDOW_HOURS = 24`, `JOIN_TOLERANCE_MS = 2000`.

- [ ] **Step 1: Write the failing tests**

Create `maintenance/test-ground-truth-run-index.py`:

```python
#!/usr/bin/env python3
"""Tests for ground-truth-run-index.py -- Stage 0 of the ground-truth auditor.

House style matches the other maintenance test rigs: plain python, no pytest.
Run: python test-ground-truth-run-index.py   (exit 0 = all pass)
"""
import importlib.util
import os
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "ground_truth_run_index", os.path.join(HERE, "ground-truth-run-index.py"))
gti = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gti)

FAILURES = []


def check(label, cond, detail=""):
    if cond:
        print("  [OK] %s" % label)
    else:
        print("  [FAIL] %s %s" % (label, detail))
        FAILURES.append(label)


def test_build_run_id_keys_on_last_scheduled_for():
    # The real AHM case (spec Sec 3.6): lastScheduledFor 15:05Z, lastRunAt
    # 17:13Z -- a catch-up fire 2h08m late. run_id must be built from
    # lastScheduledFor so this reads as the SAME logical cycle as any other
    # fire scheduled for the same slot, regardless of when it actually ran.
    rid = gti.build_run_id("lams", "automation-health-monitor", "2026-09-10T15:05:00.000Z")
    check("run_id uses lastScheduledFor verbatim",
          rid == "lams:automation-health-monitor:2026-09-10T15:05:00.000Z", rid)
    rid_again = gti.build_run_id("lams", "automation-health-monitor", "2026-09-10T15:05:00.000Z")
    check("two fires of the same lastScheduledFor produce the SAME run_id "
          "(this is what makes duplicate detection possible)", rid == rid_again)


def test_window_default_when_nothing_widens():
    now = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
    last_run = now - timedelta(hours=6)  # auditor ran 6h ago, well inside 24h
    hours, reason = gti.decide_window_hours(now, last_run, [], [])
    check("default window when auditor is current and no resume in range",
          hours == 24.0, "hours=%s reason=%s" % (hours, reason))


def test_window_widens_when_auditor_gap_exceeds_default():
    # Fixture: catch-up burst -- the auditor itself was paused/host-closed for
    # 3 days, so its own last run is 72h old.
    now = datetime(2026, 9, 11, 4, 0, tzinfo=timezone.utc)
    last_run = now - timedelta(hours=72)
    hours, reason = gti.decide_window_hours(now, last_run, [], [])
    check("window widens to cover the auditor's own gap",
          hours >= 72.0, "hours=%s reason=%s" % (hours, reason))
    check("reason names the gap", "prior auditor run" in reason, reason)


def test_window_widens_on_fleet_resume_event():
    # Fixture: the 2026-09-11 16:01 ET fleet resume -- a one-time task with no
    # cronExpression, id containing 'resume', that just fired.
    now = datetime(2026, 9, 11, 16, 5, tzinfo=timezone.utc)
    resume_task = {
        "id": "ora-routine-pause-resume-2026-09-11",
        "enabled": True,
        "lastRunAt": "2026-09-11T16:01:00.000Z",
        # no cronExpression -- one-time
    }
    hours, reason = gti.decide_window_hours(now, now - timedelta(hours=1),
                                             [resume_task], [])
    check("window widens on a fleet-resume event even when the auditor itself "
          "is current", hours > 24.0, "hours=%s reason=%s" % (hours, reason))
    check("reason names the resume task", "fleet-resume event" in reason, reason)


def test_recurring_task_named_resume_does_not_widen():
    # A recurring task that happens to have 'resume' in its id must NOT be
    # mistaken for a one-time fleet-resume marker.
    now = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
    recurring = {
        "id": "ora-resume-watch",
        "enabled": True,
        "cronExpression": "0 * * * *",
        "lastRunAt": "2026-09-10T11:59:00.000Z",
    }
    hours, reason = gti.decide_window_hours(now, now - timedelta(hours=1), [recurring], [])
    check("a RECURRING task named *resume* does not trigger the resume widen",
          hours == 24.0, "hours=%s reason=%s" % (hours, reason))


if __name__ == "__main__":
    test_build_run_id_keys_on_last_scheduled_for()
    test_window_default_when_nothing_widens()
    test_window_widens_when_auditor_gap_exceeds_default()
    test_window_widens_on_fleet_resume_event()
    test_recurring_task_named_resume_does_not_widen()
    print("-" * 72)
    if FAILURES:
        print("FAIL: %d failure(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python maintenance/test-ground-truth-run-index.py`
Expected: `FileNotFoundError` or `ModuleNotFoundError` -- `ground-truth-run-index.py` does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Create `maintenance/ground-truth-run-index.py`:

```python
#!/usr/bin/env python3
"""ground-truth-run-index.py -- Stage 0 of the ORA Ground-Truth Auditor.

Deterministic run index: reads both scheduled-task registries, resolves each
run's actual transcript (task -> session record -> transcript, one join per
fleet -- see docs/superpowers/specs/2026-09-10-ground-truth-auditor-design.md
Sec 3.4/3.5/3.5a), flags duplicate side effects, and asserts a join-rate floor
before any verifier agent is dispatched. No LLM judgment happens in this file
-- duplicate detection is a key comparison, not something an agent can be
argued out of (design spec Sec 5 Stage 0).

Usage:
    python ground-truth-run-index.py [--window-hours N] [--out PATH] [--json]

Emits one run-index JSON document (see build_run_index()'s docstring for the
schema) to --out, or stdout with --json.
"""
import argparse
import glob
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shared"))
try:
    import store_discovery as _sd
except Exception:
    _sd = None

DEFAULT_WINDOW_HOURS = 24
JOIN_TOLERANCE_MS = 2000  # createdAt vs lastRunAt match window (spec Sec 3.5a)


def build_run_id(fleet, task_id, last_scheduled_for):
    """run_id keys on lastScheduledFor (the logical cycle), never lastRunAt --
    a catch-up fire's lastRunAt can lag lastScheduledFor by hours (measured:
    automation-health-monitor 2026-09-10, 2h08m10s -- spec Sec 3.6). Keying on
    lastRunAt would make every catch-up fire read as a distinct logical cycle
    and collapse idempotency detection."""
    return "{}:{}:{}".format(fleet, task_id, last_scheduled_for)


def _parse_iso(ts):
    """Parse a registry ISO8601 timestamp ('...Z' or '...+00:00') to an
    aware UTC datetime, or None if ts is falsy/unparseable."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def decide_window_hours(now, last_auditor_run_at, cc_tasks, lams_tasks,
                         default_hours=DEFAULT_WINDOW_HOURS):
    """Automatic window sizing (design spec Sec 5 Stage 0). Widens past
    default_hours when either holds:

      1. a MEASURED gap since the previous auditor run exceeds default_hours
         (last_auditor_run_at is not None and the gap is too large), or
      2. the window contains a fleet-resume event -- a one-time task (no
         cronExpression) whose id contains 'resume', fired within
         default_hours of `now`.

    A fixed 24h window keyed on lastScheduledFor would silently drop the
    catch-up runs most likely to have duplicated side effects (spec Sec 5).

    Returns (window_hours: float, reason: str). `now` and `last_auditor_run_at`
    are aware UTC datetimes (or None for the latter).
    """
    reasons = []
    window_hours = float(default_hours)
    gap_hours = None

    if last_auditor_run_at is None:
        reasons.append("no prior auditor run recorded")
    else:
        gap_hours = (now - last_auditor_run_at).total_seconds() / 3600.0
        if gap_hours > default_hours:
            reasons.append(
                "prior auditor run was {:.1f}h ago (> {}h)".format(gap_hours, default_hours))
            window_hours = max(window_hours, gap_hours)

    resume_cutoff = now - timedelta(hours=default_hours)
    resume_hit = False
    for t in list(cc_tasks) + list(lams_tasks):
        if t.get("cronExpression"):
            continue  # recurring, not a one-time resume marker
        tid = (t.get("id") or "").lower()
        if "resume" not in tid:
            continue
        ts = _parse_iso(t.get("lastRunAt"))
        if ts is not None and ts >= resume_cutoff:
            resume_hit = True
            reasons.append("fleet-resume event '{}' fired in window".format(t.get("id")))

    if resume_hit:
        # A resume alone (auditor otherwise on schedule) still needs the
        # window widened enough to reach the paused period it just
        # re-enabled -- a bounded pause can span days.
        window_hours = max(window_hours, default_hours * 3)

    if not reasons:
        return float(default_hours), "default {}h window (no widen condition met)".format(default_hours)
    return window_hours, "; ".join(reasons)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python maintenance/test-ground-truth-run-index.py`
Expected: `ALL PASS`, exit 0.

- [ ] **Step 5: Commit**

```bash
git add maintenance/ground-truth-run-index.py maintenance/test-ground-truth-run-index.py
git commit -m "feat(ground-truth-auditor): Stage 0 window sizing and run_id construction"
```

---

## Task 2: Stage 0 -- task-to-session identification and dual-fleet transcript join

**Files:**
- Modify: `maintenance/ground-truth-run-index.py` (append functions)
- Modify: `maintenance/test-ground-truth-run-index.py` (append tests)

**Interfaces:**
- Consumes: `_parse_iso`, `JOIN_TOLERANCE_MS` (Task 1).
- Produces: `find_project_dirs(claude_home: str|None = None) -> list[str]`; `find_executing_session(task: dict, session_records: list[dict], tolerance_ms: int = JOIN_TOLERANCE_MS) -> dict|None`; `join_cc_transcript(session_record: dict|None, project_dirs: list[str]) -> str|None`; `join_lams_transcript(session_record: dict|None, lams_registry_dir: str|None) -> str|None`; `load_session_records(registry_dir: str|None) -> list[dict]`.

- [ ] **Step 1: Write the failing tests**

Append to `maintenance/test-ground-truth-run-index.py` (insert `import tempfile, shutil` at the top alongside the existing imports, and add these functions before the `if __name__ == "__main__":` block):

```python
def test_find_executing_session_matches_by_createdat_and_title():
    # Real values from the live registries (2026-09-10): AHM's lastRunAt is
    # 2026-09-10T17:13:10.632Z; its session record's createdAt is the same
    # instant in epoch ms (1789060990632).
    task = {"id": "automation-health-monitor", "lastRunAt": "2026-09-10T17:13:10.632Z"}
    records = [
        # decoy: a notifySessionId-style stale record, months earlier
        {"createdAt": 1783537999843, "title": "Some old chat", "titleSource": "auto"},
        {"createdAt": 1789060990632, "title": "Automation health monitor", "titleSource": "auto",
         "sessionId": "local_e59d1b67-bf90-4e6b-9883-3e8a52dec80c",
         "cliSessionId": "696009a7-1727-470b-917d-51df0ec81803"},
    ]
    found = gti.find_executing_session(task, records)
    check("finds the session created at the same ms as lastRunAt",
          found is not None and found["cliSessionId"] == "696009a7-1727-470b-917d-51df0ec81803")


def test_find_executing_session_ambiguous_window_is_unjoined():
    # Catch-up burst: two sessions created inside the same 2s tolerance
    # window, neither titled for this task.
    task = {"id": "ora-weekly-hygiene", "lastRunAt": "2026-09-11T16:01:02.000Z"}
    t_ms = 1789156862000
    records = [
        {"createdAt": t_ms + 100, "title": "Ora deal sourcing scan", "titleSource": "auto"},
        {"createdAt": t_ms - 100, "title": "Ora pm ledger", "titleSource": "auto"},
    ]
    found = gti.find_executing_session(task, records)
    check("two candidates, neither titled for this task -> unjoined (never guessed)",
          found is None)


def test_find_executing_session_disambiguates_by_title_in_a_burst():
    task = {"id": "ora-weekly-hygiene", "lastRunAt": "2026-09-11T16:01:02.000Z"}
    t_ms = 1789156862000
    records = [
        {"createdAt": t_ms + 50, "title": "Ora deal sourcing scan", "titleSource": "auto"},
        {"createdAt": t_ms - 50, "title": "Ora weekly hygiene", "titleSource": "auto",
         "cliSessionId": "aaaa"},
    ]
    found = gti.find_executing_session(task, records)
    check("title match resolves an otherwise-ambiguous burst window",
          found is not None and found["cliSessionId"] == "aaaa")


def test_find_executing_session_ignores_notify_session_id():
    # A task's notifySessionId points at a record with a matching cliSessionId
    # but a createdAt from months earlier -- must NOT be selected.
    task = {"id": "ora-am-brief", "lastRunAt": "2026-09-10T06:00:00.000Z",
            "notifySessionId": "local_STALE"}
    records = [
        {"createdAt": 1783537999843, "title": "ORA EOD action ledger coverage gaps",
         "titleSource": "auto", "sessionId": "local_STALE", "cliSessionId": "stale-cli-id"},
    ]
    found = gti.find_executing_session(task, records)
    check("a notifySessionId record with the wrong createdAt is never selected",
          found is None)


def test_join_cc_transcript_across_multiple_project_dirs():
    tmp = tempfile.mkdtemp()
    try:
        dir_a = os.path.join(tmp, "projA")
        dir_b = os.path.join(tmp, "projB")
        os.makedirs(dir_a)
        os.makedirs(dir_b)
        cli_id = "c2673895-9f28-47c4-9bb1-61b07a1cc87f"
        open(os.path.join(dir_b, cli_id + ".jsonl"), "w").close()
        result = gti.join_cc_transcript({"cliSessionId": cli_id}, [dir_a, dir_b])
        check("finds the transcript even when it's in the SECOND dir searched, "
              "not the first (spec Sec 3.4: scoping to one dir loses the join)",
              result == os.path.join(dir_b, cli_id + ".jsonl"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_join_cc_transcript_absent_degrades_to_none():
    result = gti.join_cc_transcript({"cliSessionId": "does-not-exist"}, ["/nonexistent"])
    check("missing CC transcript degrades to None, not an exception", result is None)


def test_join_lams_transcript_uses_session_id_with_prefix_intact():
    tmp = tempfile.mkdtemp()
    try:
        session_id = "local_00a0caa8-2a71-4ec2-94f4-b00e2c542b1b"  # already prefixed
        os.makedirs(os.path.join(tmp, session_id))
        open(os.path.join(tmp, session_id, "audit.jsonl"), "w").close()
        result = gti.join_lams_transcript({"sessionId": session_id}, tmp)
        check("LAMS join uses sessionId as-is (no re-added local_ prefix)",
              result == os.path.join(tmp, session_id, "audit.jsonl"))
        doubled = os.path.join(tmp, "local_" + session_id)
        check("doubling the prefix would NOT be the real path (regression guard)",
              not os.path.isdir(doubled))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_join_lams_transcript_absent_degrades_to_none():
    result = gti.join_lams_transcript({"sessionId": "local_missing"}, tempfile.gettempdir())
    check("missing LAMS transcript degrades to None, not an exception", result is None)
```

Add `import tempfile` and `import shutil` to the top-of-file imports in `maintenance/test-ground-truth-run-index.py`, and add the 8 new `test_*()` calls to the `if __name__ == "__main__":` block (after the existing 5 calls, before the `print("-" * 72)` line).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python maintenance/test-ground-truth-run-index.py`
Expected: `AttributeError: module 'ground_truth_run_index' has no attribute 'find_executing_session'` (and similarly for the other new functions).

- [ ] **Step 3: Write the minimal implementation**

Append to `maintenance/ground-truth-run-index.py` (after `_parse_iso`, before any `if __name__` block -- there is none yet):

```python
def find_project_dirs(claude_home=None):
    """All ~/.claude/projects/* directories (CC transcripts are spread across
    all of them, one per cwd -- spec Sec 3.4; NOT confined to the OneDrive
    one). Returns a list of absolute directory paths; [] if the projects dir
    doesn't exist."""
    home = claude_home or os.path.expanduser("~/.claude")
    proj_root = os.path.join(home, "projects")
    if not os.path.isdir(proj_root):
        return []
    return [os.path.join(proj_root, d) for d in os.listdir(proj_root)
            if os.path.isdir(os.path.join(proj_root, d))]


def find_executing_session(task, session_records, tolerance_ms=JOIN_TOLERANCE_MS):
    """Identify which session record executed a task's most recent firing.

    NOT notifySessionId -- that field is a static "notify here" target fixed
    at registration/last-edit time (verified against 4 real tasks across both
    fleets: every notifySessionId record's createdAt predates the audited
    lastRunAt by weeks to months). Spec Sec 3.5a.

    The real key: the executing session's createdAt matches the task's
    lastRunAt to within `tolerance_ms`, disambiguated by title when more than
    one candidate falls in that window (a catch-up burst can create several
    sessions inside one tolerance window).

    `session_records` is an iterable of dicts as loaded from local_*.json
    (must include at least createdAt; title/titleSource optional).

    Returns the single matching session dict, or None if zero or more than
    one candidate survives -- ambiguity is never resolved by guessing.
    """
    last_run = _parse_iso(task.get("lastRunAt"))
    if last_run is None:
        return None
    target_ms = int(last_run.timestamp() * 1000)
    expected_title = (task.get("id") or "").replace("-", " ").capitalize()

    candidates = []
    for rec in session_records:
        ca = rec.get("createdAt")
        if ca is None:
            continue
        try:
            ca_ms = int(ca)
        except (TypeError, ValueError):
            continue
        if abs(ca_ms - target_ms) <= tolerance_ms:
            candidates.append(rec)

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    # Ambiguous window -- disambiguate by title. Only trust auto-generated
    # titles (a user-renamed title, titleSource != "auto", cannot be expected
    # to match the task-id-derived form).
    titled = [r for r in candidates
              if r.get("titleSource") == "auto" and r.get("title") == expected_title]
    if len(titled) == 1:
        return titled[0]
    return None  # still ambiguous -- unjoined, never guessed


def join_cc_transcript(session_record, project_dirs):
    """CC transcript path for a session record, or None.

    session record -> cliSessionId -> <cliSessionId>.jsonl, searched across
    EVERY project dir (spec Sec 3.4: scoping to one dir drops the join rate
    100/100 -> 80/100 on the most recent 100 sessions). Top-level transcripts
    only -- a subagent transcript is evidence WITHIN a run, not a run in its
    own right.
    """
    cli_session_id = (session_record or {}).get("cliSessionId")
    if not cli_session_id:
        return None
    for d in project_dirs:
        candidate = os.path.join(d, cli_session_id + ".jsonl")
        if os.path.isfile(candidate):
            return candidate
    return None


def join_lams_transcript(session_record, lams_registry_dir):
    """LAMS transcript path for a session record, or None.

    session record -> <sessionId>/audit.jsonl, in the SAME directory as the
    LAMS scheduled-tasks.json registry (confirmed: all 501/501 real
    audit.jsonl files sit at exactly this depth). Keyed on sessionId, NOT
    cliSessionId -- sessionId already carries the 'local_' prefix (spec
    Sec 3.4/3.5); do not re-add it.
    """
    session_id = (session_record or {}).get("sessionId")
    if not session_id or not lams_registry_dir:
        return None
    candidate = os.path.join(lams_registry_dir, session_id, "audit.jsonl")
    return candidate if os.path.isfile(candidate) else None


def load_session_records(registry_dir):
    """All local_*.json session records in a registry's directory, as a list
    of dicts. Unreadable files are skipped, never raise."""
    records = []
    for p in glob.glob(os.path.join(registry_dir or "", "local_*.json")):
        try:
            records.append(json.load(open(p, encoding="utf-8-sig")))
        except Exception:
            continue
    return records
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python maintenance/test-ground-truth-run-index.py`
Expected: `ALL PASS`, exit 0 (13 checks total: 6 from Task 1 + 8 new, minus overlap -- verify the printed `[OK]` count matches the number of `check(...)` calls).

- [ ] **Step 5: Commit**

```bash
git add maintenance/ground-truth-run-index.py maintenance/test-ground-truth-run-index.py
git commit -m "feat(ground-truth-auditor): Stage 0 task-to-session join and dual-fleet transcript resolution"
```

---

## Task 3: Stage 0 -- duplicate detection

**Files:**
- Modify: `maintenance/ground-truth-run-index.py` (append functions)
- Modify: `maintenance/test-ground-truth-run-index.py` (append tests)

**Interfaces:**
- Consumes: `_parse_iso` (Task 1).
- Produces: `detect_duplicates(runs: list[dict], cc_task_ids_enabled: set[str], lams_task_ids_enabled: set[str]) -> list[dict]` where each returned flag is `{"type": str, "detail": str, "run_ids": list[str]}`; helper `_min_cron_period(cron_expression: str|None) -> timedelta|None`.

- [ ] **Step 1: Write the failing tests**

Append to `maintenance/test-ground-truth-run-index.py`:

```python
def test_detect_duplicates_same_cycle_refire():
    runs = [
        {"fleet": "cc", "task_id": "ora-weekly-hygiene", "run_id": "cc:ora-weekly-hygiene:X",
         "last_scheduled_for": "X"},
        {"fleet": "cc", "task_id": "ora-weekly-hygiene", "run_id": "cc:ora-weekly-hygiene:X-dup",
         "last_scheduled_for": "X"},
    ]
    flags = gti.detect_duplicates(runs, [], [])
    hits = [f for f in flags if f["type"] == "same_cycle_refire"]
    check("same lastScheduledFor fired twice is flagged", len(hits) == 1, flags)


def test_detect_duplicates_cross_fleet_twin():
    runs = [
        {"fleet": "cc", "task_id": "ora-passed-deal-tracker",
         "run_id": "cc:ora-passed-deal-tracker:X", "last_scheduled_for": "X"},
        {"fleet": "lams", "task_id": "ora-passed-deal-tracker",
         "run_id": "lams:ora-passed-deal-tracker:Y", "last_scheduled_for": "Y"},
    ]
    flags = gti.detect_duplicates(runs, ["ora-passed-deal-tracker"], ["ora-passed-deal-tracker"])
    hits = [f for f in flags if f["type"] == "cross_fleet_twin"]
    check("same task id enabled on both fleets is flagged", len(hits) == 1, flags)


def test_detect_duplicates_cron_period_collision():
    runs = [
        {"fleet": "lams", "task_id": "automation-health-monitor",
         "run_id": "lams:automation-health-monitor:A", "last_scheduled_for": "2026-09-10T15:05:00.000Z",
         "cron_expression": "5 11 * * 1-5"},
        {"fleet": "lams", "task_id": "automation-health-monitor",
         "run_id": "lams:automation-health-monitor:B", "last_scheduled_for": "2026-09-10T15:06:00.000Z",
         "cron_expression": "5 11 * * 1-5"},
    ]
    flags = gti.detect_duplicates(runs, [], [])
    hits = [f for f in flags if f["type"] == "cron_period_collision"]
    check("two schedules 1 minute apart on a daily cron are flagged", len(hits) == 1, flags)


def test_detect_duplicates_no_false_positive_on_normal_daily_runs():
    runs = [
        {"fleet": "lams", "task_id": "automation-health-monitor",
         "run_id": "lams:automation-health-monitor:day1", "last_scheduled_for": "2026-09-09T15:05:00.000Z",
         "cron_expression": "5 11 * * 1-5"},
        {"fleet": "lams", "task_id": "automation-health-monitor",
         "run_id": "lams:automation-health-monitor:day2", "last_scheduled_for": "2026-09-10T15:05:00.000Z",
         "cron_expression": "5 11 * * 1-5"},
    ]
    flags = gti.detect_duplicates(runs, [], [])
    check("two normal consecutive daily fires are NOT flagged", flags == [], flags)
```

Add the 4 new `test_*()` calls to the `if __name__ == "__main__":` block.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python maintenance/test-ground-truth-run-index.py`
Expected: `AttributeError: module 'ground_truth_run_index' has no attribute 'detect_duplicates'`.

- [ ] **Step 3: Write the minimal implementation**

Append to `maintenance/ground-truth-run-index.py`:

```python
from collections import defaultdict


def _min_cron_period(cron_expression):
    """Coarse minimum-period estimate for a 5-field cron expression, used
    only to flag an implausibly tight re-schedule -- not a full cron parser.
    Returns a timedelta, or None if the expression can't be classified."""
    if not cron_expression:
        return None
    fields = cron_expression.split()
    if len(fields) != 5:
        return None
    minute, hour = fields[0], fields[1]
    if minute.startswith("*/"):
        try:
            return timedelta(minutes=int(minute[2:]))
        except ValueError:
            return None
    if minute == "*":
        return timedelta(minutes=1)
    if hour == "*":
        return timedelta(hours=1)
    return timedelta(days=1)  # daily/weekly/monthly all lower-bound at 1 day


def detect_duplicates(runs, cc_task_ids_enabled, lams_task_ids_enabled):
    """Deterministic duplicate/collision flags across a set of run records
    (spec Sec 5 Stage 0). `runs` is a list of dicts each carrying at least
    fleet, task_id, run_id, last_scheduled_for (and cron_expression where
    recurring). Returns a list of flag dicts: {"type", "detail", "run_ids"}.

    Three flag types -- duplicate detection is a key comparison, never an
    agent's judgment call:
      - same_cycle_refire: two fires share one lastScheduledFor
      - cron_period_collision: two distinct lastScheduledFor values fall
        inside the same cron period for the same task
      - cross_fleet_twin: the same task id is enabled on BOTH registries
    """
    flags = []

    by_cycle = defaultdict(list)
    for r in runs:
        key = (r["fleet"], r["task_id"], r.get("last_scheduled_for"))
        by_cycle[key].append(r["run_id"])
    for (fleet, task_id, cycle), run_ids in by_cycle.items():
        if cycle and len(run_ids) > 1:
            flags.append({
                "type": "same_cycle_refire",
                "detail": "{} fired {} times for the same logical cycle {}".format(
                    task_id, len(run_ids), cycle),
                "run_ids": run_ids,
            })

    twins = set(cc_task_ids_enabled) & set(lams_task_ids_enabled)
    for task_id in sorted(twins):
        flags.append({
            "type": "cross_fleet_twin",
            "detail": "'{}' is enabled on BOTH the CC and LAMS registries -- "
                      "known dual-fleet double-fire hazard".format(task_id),
            "run_ids": [r["run_id"] for r in runs if r["task_id"] == task_id],
        })

    by_task = defaultdict(list)
    for r in runs:
        if r.get("cron_expression") and r.get("last_scheduled_for"):
            by_task[(r["fleet"], r["task_id"])].append(r)
    for (fleet, task_id), task_runs in by_task.items():
        times = sorted((_parse_iso(r["last_scheduled_for"]) for r in task_runs
                        if _parse_iso(r["last_scheduled_for"]) is not None))
        min_period = _min_cron_period(task_runs[0].get("cron_expression"))
        for a, b in zip(times, times[1:]):
            if min_period is not None and (b - a) < min_period:
                flags.append({
                    "type": "cron_period_collision",
                    "detail": "{} scheduled twice ({} and {}) inside one cron "
                              "period ({})".format(task_id, a.isoformat(), b.isoformat(),
                                                    task_runs[0].get("cron_expression")),
                    "run_ids": [r["run_id"] for r in task_runs],
                })

    return flags
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python maintenance/test-ground-truth-run-index.py`
Expected: `ALL PASS`, exit 0.

- [ ] **Step 5: Commit**

```bash
git add maintenance/ground-truth-run-index.py maintenance/test-ground-truth-run-index.py
git commit -m "feat(ground-truth-auditor): Stage 0 duplicate-side-effect detection"
```

---

## Task 4: Stage 0 -- join-rate floor

**Files:**
- Modify: `maintenance/ground-truth-run-index.py` (append function)
- Modify: `maintenance/test-ground-truth-run-index.py` (append tests)

**Interfaces:**
- Produces: `assert_join_rate_floor(joined_count: int, total_count: int, window_hours: float, default_hours: float = DEFAULT_WINDOW_HOURS) -> tuple[bool, str]`.

- [ ] **Step 1: Write the failing tests**

Append to `maintenance/test-ground-truth-run-index.py`:

```python
def test_join_rate_floor_normal_window_high_rate_passes():
    ok, msg = gti.assert_join_rate_floor(95, 100, window_hours=24.0)
    check("95/100 on a normal 24h window passes the 90% floor", ok, msg)


def test_join_rate_floor_normal_window_low_rate_fails():
    ok, msg = gti.assert_join_rate_floor(50, 100, window_hours=24.0)
    check("50/100 on a normal 24h window FAILS the 90% floor "
          "(this is what R1a exists to catch)", not ok, msg)


def test_join_rate_floor_widened_window_same_low_rate_passes():
    # The exact scenario R1a exists to distinguish: the SAME ~50% rate is
    # expected, not alarming, on a widened window.
    ok, msg = gti.assert_join_rate_floor(50, 100, window_hours=100.0)
    check("50/100 on a widened (>72h) window passes the 30% floor -- "
          "the widener must not false-alarm nightly", ok, msg)


def test_join_rate_floor_empty_window_is_trivially_ok():
    ok, msg = gti.assert_join_rate_floor(0, 0, window_hours=24.0)
    check("an empty window never fails the floor", ok, msg)
```

Add the 4 new `test_*()` calls to the `if __name__ == "__main__":` block.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python maintenance/test-ground-truth-run-index.py`
Expected: `AttributeError: module 'ground_truth_run_index' has no attribute 'assert_join_rate_floor'`.

- [ ] **Step 3: Write the minimal implementation**

Append to `maintenance/ground-truth-run-index.py`:

```python
def assert_join_rate_floor(joined_count, total_count, window_hours,
                            default_hours=DEFAULT_WINDOW_HOURS):
    """Width-dependent join-rate floor (spec Sec 9 R1a) -- NOT a non-zero
    check. Measured on the live CC store (spec Sec 3.5, all 17 project dirs):
    100% at n=100-200 recent sessions, ~43% fleet-wide. A widened window is
    expected to read lower; the SAME low rate on a normal 24h window means the
    join is broken.

    Floor schedule:
      - window_hours <= default_hours (normal night): >= 90%
      - window_hours <= default_hours * 3 (a moderate widen): >= 60%
      - wider than that (a multi-day catch-up burst): >= 30%

    Returns (ok: bool, message: str). total_count == 0 is trivially ok (an
    empty window has nothing to fail to join).
    """
    if total_count == 0:
        return True, "no runs in window -- floor not applicable"
    rate = joined_count / total_count
    if window_hours <= default_hours:
        floor = 0.90
    elif window_hours <= default_hours * 3:
        floor = 0.60
    else:
        floor = 0.30
    ok = rate >= floor
    msg = "{}/{} joined ({:.0%}) against a {:.0%} floor for a {:.1f}h window".format(
        joined_count, total_count, rate, floor, window_hours)
    return ok, msg
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python maintenance/test-ground-truth-run-index.py`
Expected: `ALL PASS`, exit 0.

- [ ] **Step 5: Commit**

```bash
git add maintenance/ground-truth-run-index.py maintenance/test-ground-truth-run-index.py
git commit -m "feat(ground-truth-auditor): Stage 0 width-dependent join-rate floor"
```

---

## Task 5: Stage 0 -- CLI orchestrator

**Files:**
- Modify: `maintenance/ground-truth-run-index.py` (append orchestrator + CLI)
- Modify: `maintenance/test-ground-truth-run-index.py` (append tests)

**Interfaces:**
- Consumes: every function from Tasks 1-4, plus `store_discovery.discover_store` (existing).
- Produces: `build_run_index(cc_registry_path: str|None, lams_registry_path: str|None, project_dirs: list[str], now: datetime|None = None, window_hours_override: float|None = None) -> dict`; `main(argv=None) -> int`; module constant `SELF_TASK_ID = "ora-ground-truth-auditor"`.

- [ ] **Step 1: Write the failing tests**

Append to `maintenance/test-ground-truth-run-index.py`:

```python
def _write_registry(path, tasks, recorded_skips=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump({"scheduledTasks": tasks, "recordedSkips": recorded_skips or {}},
              open(path, "w", encoding="utf-8"))


def _write_session_record(registry_dir, session_id, created_at_ms, title,
                           cli_session_id=None):
    rec = {"sessionId": session_id, "createdAt": created_at_ms,
           "title": title, "titleSource": "auto"}
    if cli_session_id:
        rec["cliSessionId"] = cli_session_id
    json.dump(rec, open(os.path.join(registry_dir, session_id + ".json"), "w", encoding="utf-8"))


def test_build_run_index_excludes_its_own_run():
    tmp = tempfile.mkdtemp()
    try:
        cc_reg = os.path.join(tmp, "cc", "scheduled-tasks.json")
        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        now = datetime(2026, 9, 11, 20, 5, tzinfo=timezone.utc)
        _write_registry(cc_reg, [
            {"id": "ora-ground-truth-auditor", "cronExpression": "0 4 * * *",
             "enabled": True, "lastRunAt": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
             "lastScheduledFor": now.strftime("%Y-%m-%dT%H:%M:%S.000Z")},
        ])
        _write_registry(lams_reg, [])
        index = gti.build_run_index(cc_reg, lams_reg, [], now=now)
        check("the auditor's own run never appears in its own index",
              all(r["task_id"] != "ora-ground-truth-auditor" for r in index["runs"]),
              index["runs"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_run_index_end_to_end_joins_a_real_shaped_run():
    tmp = tempfile.mkdtemp()
    try:
        cc_dir = os.path.join(tmp, "cc")
        cc_reg = os.path.join(cc_dir, "scheduled-tasks.json")
        now = datetime(2026, 9, 10, 20, 0, tzinfo=timezone.utc)
        last_run = "2026-09-10T16:56:58.667Z"
        _write_registry(cc_reg, [
            {"id": "ora-doctrine-integrity-guard", "cronExpression": "5 7 * * *",
             "enabled": True, "lastRunAt": last_run, "lastScheduledFor": last_run,
             "model": "claude-opus-5"},
        ])
        t_ms = int(datetime.fromisoformat(last_run.replace("Z", "+00:00")).timestamp() * 1000)
        _write_session_record(cc_dir, "local_aa8cdc0f", t_ms,
                               "Ora doctrine integrity guard", cli_session_id="abc123")
        proj_dir = os.path.join(tmp, "proj")
        os.makedirs(proj_dir)
        open(os.path.join(proj_dir, "abc123.jsonl"), "w").close()

        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        _write_registry(lams_reg, [])

        index = gti.build_run_index(cc_reg, lams_reg, [proj_dir], now=now)
        check("exactly one run indexed", len(index["runs"]) == 1, index["runs"])
        run = index["runs"][0]
        check("run is joined to its transcript", run["joined"] is True, run)
        check("run_id keys on lastScheduledFor", run["run_id"].endswith(last_run), run)
        check("CC join-rate floor passes at 1/1", index["join_stats"]["cc"]["rate_ok"] is True,
              index["join_stats"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
```

Add the 2 new `test_*()` calls to the `if __name__ == "__main__":` block.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python maintenance/test-ground-truth-run-index.py`
Expected: `AttributeError: module 'ground_truth_run_index' has no attribute 'build_run_index'`.

- [ ] **Step 3: Write the minimal implementation**

Append to `maintenance/ground-truth-run-index.py`:

```python
SELF_TASK_ID = "ora-ground-truth-auditor"
LAST_RUN_MARKER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "_state", "ground-truth",
    "last-auditor-run.json")


def _read_last_auditor_run():
    try:
        d = json.load(open(LAST_RUN_MARKER, encoding="utf-8"))
        return _parse_iso(d.get("completed_at"))
    except Exception:
        return None


def _write_last_auditor_run(now):
    os.makedirs(os.path.dirname(LAST_RUN_MARKER), exist_ok=True)
    json.dump({"completed_at": now.strftime("%Y-%m-%dT%H:%M:%S.000Z")},
              open(LAST_RUN_MARKER, "w", encoding="utf-8"))


def _registry_tasks(registry_path):
    try:
        d = json.load(open(registry_path, encoding="utf-8-sig"))
    except Exception:
        return []
    return d.get("scheduledTasks", []) or []


def _registry_recorded_skips(registry_path):
    try:
        d = json.load(open(registry_path, encoding="utf-8-sig"))
    except Exception:
        return {}
    return d.get("recordedSkips", {}) or {}


def _in_window(task, window_start):
    ts = _parse_iso(task.get("lastRunAt"))
    return ts is not None and ts >= window_start


def build_run_index(cc_registry_path, lams_registry_path, project_dirs,
                     now=None, window_hours_override=None):
    """Stage 0 orchestrator -- produces the complete run-index document.

    Returns a dict:
      {
        "generated_at": iso str,
        "window_hours": float,
        "window_reason": str,
        "runs": [ { run_id, fleet, task_id, last_scheduled_for, last_run_at,
                    cron_expression, model, transcript, joined: bool,
                    recorded_skips: [...] }, ... ],
        "duplicate_flags": [ ... ],
        "join_stats": { "cc": {joined, total, rate_ok, message},
                         "lams": {...} },
      }
    """
    now = now or datetime.now(timezone.utc)
    cc_tasks_all = _registry_tasks(cc_registry_path)
    lams_tasks_all = _registry_tasks(lams_registry_path)

    if window_hours_override is not None:
        window_hours, window_reason = float(window_hours_override), "explicit --window-hours override"
    else:
        window_hours, window_reason = decide_window_hours(
            now, _read_last_auditor_run(), cc_tasks_all, lams_tasks_all)

    window_start = now - timedelta(hours=window_hours)

    cc_session_records = load_session_records(
        os.path.dirname(cc_registry_path) if cc_registry_path else None)
    lams_registry_dir = os.path.dirname(lams_registry_path) if lams_registry_path else None
    lams_session_records = load_session_records(lams_registry_dir)
    cc_recorded_skips = _registry_recorded_skips(cc_registry_path)
    lams_recorded_skips = _registry_recorded_skips(lams_registry_path)

    runs = []
    cc_joined = cc_total = 0
    lams_joined = lams_total = 0

    for fleet, tasks, session_records, skips in (
            ("cc", cc_tasks_all, cc_session_records, cc_recorded_skips),
            ("lams", lams_tasks_all, lams_session_records, lams_recorded_skips)):
        for t in tasks:
            task_id = t.get("id")
            if task_id == SELF_TASK_ID:
                continue  # self-exclusion (spec Sec 5 Stage 4)
            if not _in_window(t, window_start):
                continue
            session = find_executing_session(t, session_records)
            if fleet == "cc":
                transcript = join_cc_transcript(session, project_dirs) if session else None
                cc_total += 1
                if transcript:
                    cc_joined += 1
            else:
                transcript = join_lams_transcript(session, lams_registry_dir) if session else None
                lams_total += 1
                if transcript:
                    lams_joined += 1
            runs.append({
                "run_id": build_run_id(fleet, task_id, t.get("lastScheduledFor")),
                "fleet": fleet,
                "task_id": task_id,
                "last_scheduled_for": t.get("lastScheduledFor"),
                "last_run_at": t.get("lastRunAt"),
                "cron_expression": t.get("cronExpression"),
                "model": t.get("model"),
                "transcript": transcript,
                "joined": transcript is not None,
                "recorded_skips": skips.get(task_id, []),
            })

    cc_enabled = {t.get("id") for t in cc_tasks_all if t.get("enabled")}
    lams_enabled = {t.get("id") for t in lams_tasks_all if t.get("enabled")}
    duplicate_flags = detect_duplicates(runs, cc_enabled, lams_enabled)

    cc_ok, cc_msg = assert_join_rate_floor(cc_joined, cc_total, window_hours)
    lams_ok, lams_msg = assert_join_rate_floor(lams_joined, lams_total, window_hours)

    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "window_hours": window_hours,
        "window_reason": window_reason,
        "runs": runs,
        "duplicate_flags": duplicate_flags,
        "join_stats": {
            "cc": {"joined": cc_joined, "total": cc_total, "rate_ok": cc_ok, "message": cc_msg},
            "lams": {"joined": lams_joined, "total": lams_total, "rate_ok": lams_ok, "message": lams_msg},
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window-hours", type=float, default=None,
                         help="Override automatic window sizing (ad-hoc investigation only).")
    parser.add_argument("--out", default=None,
                         help="Output path. Default: _state/ground-truth/run-index-<date>.json")
    parser.add_argument("--json", action="store_true",
                         help="Print the run index to stdout instead of writing a file.")
    args = parser.parse_args(argv)

    cc_path = _sd.discover_store("claude-code-sessions") if _sd else None
    lams_path = _sd.discover_store("local-agent-mode-sessions") if _sd else None
    project_dirs = find_project_dirs()

    now = datetime.now(timezone.utc)
    index = build_run_index(cc_path, lams_path, project_dirs, now=now,
                             window_hours_override=args.window_hours)

    if args.json:
        print(json.dumps(index, indent=2))
    else:
        out = args.out or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "_state", "ground-truth",
            "run-index-{}.json".format(now.strftime("%Y-%m-%d")))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump(index, open(out, "w", encoding="utf-8"), indent=2)
        print("wrote {} ({} runs, {} duplicate flags)".format(
            out, len(index["runs"]), len(index["duplicate_flags"])))

    _write_last_auditor_run(now)

    floor_failures = [f for f in (index["join_stats"]["cc"], index["join_stats"]["lams"])
                      if not f["rate_ok"]]
    if floor_failures:
        print("JOIN-RATE FLOOR BREACHED: " + "; ".join(f["message"] for f in floor_failures),
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Note: `from collections import defaultdict` was already added at module scope in Task 3 -- do not duplicate the import.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python maintenance/test-ground-truth-run-index.py`
Expected: `ALL PASS`, exit 0.

- [ ] **Step 5: Commit**

```bash
git add maintenance/ground-truth-run-index.py maintenance/test-ground-truth-run-index.py
git commit -m "feat(ground-truth-auditor): Stage 0 CLI orchestrator"
```

---

## Task 6: Stage 1 -- side-effect extraction and cost gate

**Files:**
- Create: `maintenance/ground-truth-side-effects.py`
- Test: `maintenance/test-ground-truth-side-effects.py`

**Interfaces:**
- Consumes: a run-index JSON document shaped as `build_run_index()` produces (Task 5) -- specifically each run's `transcript` and `joined` fields.
- Produces: `extract_side_effects(transcript_path: str|None) -> dict[str, int]`; `has_side_effects(run_record: dict) -> bool`; `annotate_run_index(run_index: dict) -> dict` (mutates in place, adds `side_effects` per run and top-level `side_effect_stats`); `main(argv=None) -> int`.

- [ ] **Step 1: Write the failing tests**

Create `maintenance/test-ground-truth-side-effects.py`:

```python
#!/usr/bin/env python3
"""Tests for ground-truth-side-effects.py -- Stage 1 of the ground-truth auditor."""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "ground_truth_side_effects", os.path.join(HERE, "ground-truth-side-effects.py"))
gse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gse)

FAILURES = []


def check(label, cond, detail=""):
    if cond:
        print("  [OK] %s" % label)
    else:
        print("  [FAIL] %s %s" % (label, detail))
        FAILURES.append(label)


def _write_transcript(lines):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")
    return path


def test_extract_side_effects_detects_email_send():
    path = _write_transcript([
        {"type": "tool_use", "name": "Bash",
         "input": {"command": "powershell scheduled-tasks/_shared/send-via-outlook.ps1 -To x"}},
    ])
    effects = gse.extract_side_effects(path)
    check("email send detected", effects.get("email_sent") == 1, effects)
    os.remove(path)


def test_extract_side_effects_detects_notion_write():
    path = _write_transcript([
        {"type": "tool_use", "name": "mcp__notion__notion-create-pages", "input": {}},
    ])
    effects = gse.extract_side_effects(path)
    check("notion write detected", effects.get("notion_write") == 1, effects)
    os.remove(path)


def test_extract_side_effects_empty_for_read_only_run():
    path = _write_transcript([
        {"type": "tool_use", "name": "Read", "input": {"file_path": "x.md"}},
        {"type": "tool_use", "name": "Grep", "input": {"pattern": "x"}},
    ])
    effects = gse.extract_side_effects(path)
    check("a read-only run has no side effects", effects == {}, effects)
    os.remove(path)


def test_extract_side_effects_missing_transcript_is_empty_not_an_exception():
    effects = gse.extract_side_effects("/does/not/exist.jsonl")
    check("missing transcript degrades to {} without raising", effects == {})


def test_has_side_effects_unjoined_run_is_never_gated_out():
    run = {"joined": False, "side_effects": {}}
    check("an unjoined run always goes to a verifier -- it cannot be proven "
          "clean (spec Sec 9 R1a)", gse.has_side_effects(run) is True)


def test_has_side_effects_joined_clean_run_is_gated():
    run = {"joined": True, "side_effects": {}}
    check("a joined run with zero side effects is gated out (cost gate)",
          gse.has_side_effects(run) is False)


def test_annotate_run_index_produces_correct_counts():
    path_email = _write_transcript([
        {"type": "tool_use", "name": "Bash", "input": {"command": "send-via-outlook.ps1"}}])
    run_index = {
        "runs": [
            {"run_id": "a", "joined": True, "transcript": path_email},
            {"run_id": "b", "joined": True, "transcript": None},
            {"run_id": "c", "joined": False, "transcript": None},
        ]
    }
    gse.annotate_run_index(run_index)
    stats = run_index["side_effect_stats"]
    check("1 verifier dispatched (email) + 1 unjoined = 2, 1 stamped clean",
          stats == {"verifiers_dispatched": 2, "stamped_clean": 1, "total": 3}, stats)
    os.remove(path_email)


if __name__ == "__main__":
    test_extract_side_effects_detects_email_send()
    test_extract_side_effects_detects_notion_write()
    test_extract_side_effects_empty_for_read_only_run()
    test_extract_side_effects_missing_transcript_is_empty_not_an_exception()
    test_has_side_effects_unjoined_run_is_never_gated_out()
    test_has_side_effects_joined_clean_run_is_gated()
    test_annotate_run_index_produces_correct_counts()
    print("-" * 72)
    if FAILURES:
        print("FAIL: %d failure(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python maintenance/test-ground-truth-side-effects.py`
Expected: `FileNotFoundError` -- `ground-truth-side-effects.py` does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Create `maintenance/ground-truth-side-effects.py`:

```python
#!/usr/bin/env python3
"""ground-truth-side-effects.py -- Stage 1 of the ORA Ground-Truth Auditor.

Per run, derives CANDIDATE side effects from its transcript (or, if unjoined,
treats it as requiring a verifier -- see has_side_effects()). Runs with zero
side effects get a cheap deterministic stamp and never reach a verifier
agent -- this is the approved cost gate (design spec Sec 5 Stage 1): ~8-15
verifiers/night instead of 64.

Usage:
    python ground-truth-side-effects.py --run-index PATH [--out PATH]
"""
import argparse
import json
import os
import re
import sys

# Patterns matched against a transcript's tool_use records (Bash commands and
# MCP tool names) to detect a candidate side effect. Matching the TOOL CALL,
# not its outcome -- Stage 3's CLAIM ACCURACY axis re-verifies the actual
# published artifact; Stage 1 only decides whether a verifier is worth
# dispatching at all.
SIDE_EFFECT_PATTERNS = {
    "email_sent": re.compile(r"send-via-outlook\.ps1", re.IGNORECASE),
    "notion_write": re.compile(r"notion-(create-pages|update-page)"),
    "git_push": re.compile(r"\bgit\s+push\b"),
    "oi_filed": re.compile(r"allocate-oi-id\.py"),
    "file_write": re.compile(r'"name"\s*:\s*"(Write|Edit)"'),
}


def extract_side_effects(transcript_path):
    """Scan one transcript .jsonl for candidate side effects. Returns a dict
    {effect_name: count}; empty dict if the transcript has none or cannot be
    read. Never raises -- an unreadable transcript degrades to {} exactly
    like a run with no side effects (has_side_effects()'s `joined` check,
    not this function, is where "could not read" is distinguished from
    "read and clean")."""
    if not transcript_path or not os.path.isfile(transcript_path):
        return {}
    found = {}
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                for name, pattern in SIDE_EFFECT_PATTERNS.items():
                    if pattern.search(line):
                        found[name] = found.get(name, 0) + 1
    except Exception:
        return {}
    return found


def has_side_effects(run_record):
    """True if a run record (from the Stage 0 index, annotated with
    side_effects) registered at least one candidate side effect, OR if it
    could not be joined to a transcript at all -- an unjoined run cannot be
    proven clean, so it is never silently gated out (spec Sec 9 R1a: an
    unjoined run is UNVERIFIABLE, never treated as clean)."""
    if not run_record.get("joined"):
        return True  # external enumeration required -- never assume clean
    return bool(run_record.get("side_effects"))


def annotate_run_index(run_index):
    """Adds `side_effects` (dict) to every run in a loaded run-index document,
    and a top-level `side_effect_stats` summary (gated vs ungated counts --
    spec Sec 9 R3, so cost drift is visible in the digest rather than
    discovered on a bill). Mutates and returns run_index."""
    gated = ungated = 0
    for run in run_index.get("runs", []):
        run["side_effects"] = extract_side_effects(run.get("transcript"))
        if has_side_effects(run):
            ungated += 1  # dispatched to a verifier
        else:
            gated += 1  # stamped clean, no agent
    run_index["side_effect_stats"] = {
        "verifiers_dispatched": ungated,
        "stamped_clean": gated,
        "total": ungated + gated,
    }
    return run_index


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-index", required=True, help="Stage 0 run-index JSON path")
    parser.add_argument("--out", default=None, help="Output path (default: overwrite --run-index)")
    args = parser.parse_args(argv)

    run_index = json.load(open(args.run_index, encoding="utf-8"))
    annotate_run_index(run_index)

    out = args.out or args.run_index
    json.dump(run_index, open(out, "w", encoding="utf-8"), indent=2)
    stats = run_index["side_effect_stats"]
    print("{} runs: {} to verifier, {} stamped clean".format(
        stats["total"], stats["verifiers_dispatched"], stats["stamped_clean"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python maintenance/test-ground-truth-side-effects.py`
Expected: `ALL PASS`, exit 0.

- [ ] **Step 5: Commit**

```bash
git add maintenance/ground-truth-side-effects.py maintenance/test-ground-truth-side-effects.py
git commit -m "feat(ground-truth-auditor): Stage 1 side-effect extraction and cost gate"
```

---

## Task 7: Model-resolution ladder

**Files:**
- Create: `maintenance/ground-truth-model-resolve.py`
- Test: `maintenance/test-ground-truth-model-resolve.py`

**Interfaces:**
- Produces: `extract_model_tag(skill_md_text: str|None) -> str|None`; `resolve_audited_model(task_record: dict, skill_md_text: str|None = None, session_record: dict|None = None) -> tuple[str|None, str]`; `resolve_verifier_model(task_record: dict, skill_md_text: str|None = None, session_record: dict|None = None) -> tuple[str, str]`; module constant `FABLE_MODEL = "claude-fable-5-1"`.

- [ ] **Step 1: Write the failing tests**

Create `maintenance/test-ground-truth-model-resolve.py`:

```python
#!/usr/bin/env python3
"""Tests for ground-truth-model-resolve.py -- verifier model floor ladder."""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "ground_truth_model_resolve", os.path.join(HERE, "ground-truth-model-resolve.py"))
gmr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gmr)

FAILURES = []


def check(label, cond, detail=""):
    if cond:
        print("  [OK] %s" % label)
    else:
        print("  [FAIL] %s %s" % (label, detail))
        FAILURES.append(label)


def test_rung1_registry_model_wins():
    model, source = gmr.resolve_audited_model(
        {"model": "claude-opus-5"}, skill_md_text="[MODEL: claude-sonnet-5 | set 2026-01-01]")
    check("registry model field takes priority over the SKILL.md tag",
          (model, source) == ("claude-opus-5", "registry"), (model, source))


def test_rung2_skill_md_tag_used_when_registry_absent():
    model, source = gmr.resolve_audited_model(
        {}, skill_md_text="[MODEL: claude-opus-5 | checked 2026-08-12]")
    check("SKILL.md tag used when registry has no model field",
          (model, source) == ("claude-opus-5", "skill_md_tag"), (model, source))


def test_rung3_session_record_used_when_registry_and_tag_absent():
    model, source = gmr.resolve_audited_model(
        {}, skill_md_text=None, session_record={"model": "claude-sonnet-5"})
    check("session record model used as the last resort before fail-safe",
          (model, source) == ("claude-sonnet-5", "session_record"), (model, source))


def test_rung4_all_absent_fails_safe_to_none():
    model, source = gmr.resolve_audited_model({}, skill_md_text=None, session_record=None)
    check("all three rungs absent resolves to None, not a guess",
          (model, source) == (None, "unresolved"), (model, source))


def test_verifier_model_matches_or_exceeds_audited_tier():
    verifier, reasoning = gmr.resolve_verifier_model({"model": "claude-sonnet-5"})
    check("verifier model is at least the audited model's tier",
          gmr._tier(verifier) >= gmr._tier("claude-sonnet-5"), (verifier, reasoning))


def test_verifier_model_unresolved_audited_model_forces_fable():
    verifier, reasoning = gmr.resolve_verifier_model({})
    check("an unresolved audited model forces the verifier to Fable "
          "(reviewer >= implementer must never be silently violated)",
          verifier == gmr.FABLE_MODEL, (verifier, reasoning))


def test_verifier_model_unknown_audited_model_also_forces_fable():
    verifier, reasoning = gmr.resolve_verifier_model({"model": "some-future-model-not-in-the-table"})
    check("an audited model outside the known tier table also fails safe to Fable "
          "(never silently license a cheaper verifier)",
          verifier == gmr.FABLE_MODEL, (verifier, reasoning))


def test_extract_model_tag_parses_the_real_frontmatter_format():
    # Real production format includes a bare word (e.g. "observed") between
    # the model id and the pipe.
    text = ("description: ...supersedes the retired task... "
            "[MODEL: claude-opus-5 observed | checked 2026-08-12 via live-run transcript canary]")
    tag = gmr.extract_model_tag(text)
    check("parses the real [MODEL: ...] tag format used in production SKILL.md files "
          "(including the trailing 'observed' annotation)", tag == "claude-opus-5", tag)


def test_extract_model_tag_parses_the_simple_format():
    tag = gmr.extract_model_tag("[MODEL: claude-sonnet-5 | set 2026-01-01]")
    check("parses the simple [MODEL: <id> | ...] tag format", tag == "claude-sonnet-5", tag)


if __name__ == "__main__":
    test_rung1_registry_model_wins()
    test_rung2_skill_md_tag_used_when_registry_absent()
    test_rung3_session_record_used_when_registry_and_tag_absent()
    test_rung4_all_absent_fails_safe_to_none()
    test_verifier_model_matches_or_exceeds_audited_tier()
    test_verifier_model_unresolved_audited_model_forces_fable()
    test_verifier_model_unknown_audited_model_also_forces_fable()
    test_extract_model_tag_parses_the_real_frontmatter_format()
    test_extract_model_tag_parses_the_simple_format()
    print("-" * 72)
    if FAILURES:
        print("FAIL: %d failure(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python maintenance/test-ground-truth-model-resolve.py`
Expected: `FileNotFoundError` -- `ground-truth-model-resolve.py` does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Create `maintenance/ground-truth-model-resolve.py`:

```python
#!/usr/bin/env python3
"""ground-truth-model-resolve.py -- verifier model-floor ladder for the ORA
Ground-Truth Auditor (design spec Sec 5 Stage 2).

The registry's `model` field is absent for ~69% of the fleet (CC 20/38, LAMS
1/29 -- spec Sec 3.1), so the audited run's model cannot be a simple field
lookup. Resolves in order:

  1. registry `model` field, when present;
  2. the `[MODEL: <id> ...]` tag in the task's SKILL.md frontmatter
     description (a bare word, e.g. "observed", may follow the id before the
     closing `|`/`]` -- the real production format does this);
  3. the joined session record's `model`, when present;
  4. failing all three (or an audited model outside the known tier table),
     assume the highest tier and verify at Fable.

Step 4 is deliberately fail-safe: an unknown model must never silently
license a CHEAPER verifier than the run it audits (reviewer >= implementer).
"""
import re

FABLE_MODEL = "claude-fable-5-1"

# Captures the model id, tolerating one bare trailing word (e.g. "observed")
# before the required '|' or ']' -- matches the real production tag format:
# "[MODEL: claude-opus-5 observed | checked 2026-08-12 via ... canary]".
MODEL_TAG_RE = re.compile(r"\[MODEL:\s*([a-zA-Z0-9._-]+)(?:\s+\w+)*\s*(?:\||\])")

# Coarse tier ordering (lowest to highest) for "reviewer >= implementer".
# Unknown models are never assumed cheap -- see resolve_verifier_model step 4.
MODEL_TIERS = ["claude-haiku-4-5-20251001", "claude-sonnet-5", "claude-opus-5", FABLE_MODEL]


def _tier(model_id):
    try:
        return MODEL_TIERS.index(model_id)
    except ValueError:
        return -1  # unknown model: never in the known table


def extract_model_tag(skill_md_text):
    """The `[MODEL: <id> ...]` tag from a SKILL.md frontmatter description,
    or None if absent/unparseable."""
    if not skill_md_text:
        return None
    m = MODEL_TAG_RE.search(skill_md_text)
    return m.group(1) if m else None


def resolve_audited_model(task_record, skill_md_text=None, session_record=None):
    """Resolve which model actually ran the audited task, per the 3-rung
    ladder (registry -> SKILL.md tag -> session record). Returns
    (model_id_or_None, source: str)."""
    model = task_record.get("model")
    if model:
        return model, "registry"
    tagged = extract_model_tag(skill_md_text)
    if tagged:
        return tagged, "skill_md_tag"
    session_model = (session_record or {}).get("model")
    if session_model:
        return session_model, "session_record"
    return None, "unresolved"


def resolve_verifier_model(task_record, skill_md_text=None, session_record=None):
    """The model the VERIFIER must run at: >= the audited run's own model
    (reviewer >= implementer), or Fable if the audited model could not be
    resolved, or was resolved to something outside the known tier table
    (fail-safe -- spec Sec 5 Stage 2 step 4).

    Returns (verifier_model_id: str, reasoning: str).
    """
    audited_model, source = resolve_audited_model(task_record, skill_md_text, session_record)
    if audited_model is None:
        return FABLE_MODEL, ("audited model unresolved (registry/SKILL.md tag/session "
                              "record all absent) -- fail-safe to Fable, never assume cheap")
    audited_tier = _tier(audited_model)
    if audited_tier < 0:
        return FABLE_MODEL, ("audited model '{}' not in the known tier table -- "
                              "fail-safe to Fable".format(audited_model))
    return MODEL_TIERS[audited_tier], (
        "audited model '{}' resolved via {} -- verifying at >= that tier".format(
            audited_model, source))
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python maintenance/test-ground-truth-model-resolve.py`
Expected: `ALL PASS`, exit 0.

- [ ] **Step 5: Commit**

```bash
git add maintenance/ground-truth-model-resolve.py maintenance/test-ground-truth-model-resolve.py
git commit -m "feat(ground-truth-auditor): verifier model-floor resolution ladder"
```

---

## Task 8: SKILL.md -- runtime instructions (Stage 2-4, trust enforcement, approval gate)

**Files:**
- Create: `scheduled-tasks/ora-ground-truth-auditor/SKILL.md`

**Interfaces:**
- Consumes (as scripts the live agent session runs): `maintenance/ground-truth-run-index.py`, `maintenance/ground-truth-side-effects.py`, `maintenance/ground-truth-model-resolve.py`, `maintenance/allocate-oi-id.py`, `skills/evidence-dossier-drafting/SKILL.md`, `scheduled-tasks/_shared/send-via-outlook.ps1`.
- Produces: nothing importable -- this is the prose that drives the scheduled agent session end to end.

There is no test cycle for this file (it is instructions for a live LLM session, not code) -- its correctness is checked in Task 9 (dry run) and Task 10 (adversarial review).

- [ ] **Step 1: Write the SKILL.md**

Create `scheduled-tasks/ora-ground-truth-auditor/SKILL.md`:

```markdown
---
name: ora-ground-truth-auditor
description: Nightly re-derivation audit of the previous 24h of scheduled-task runs across both fleets. Dispatches one verifier agent per side-effecting run (side-effect-free runs get a cheap deterministic stamp, no agent) to re-derive every factual claim from PRIMARY SOURCES ONLY -- never a prior summary, log line, or finding. Reports on four axes: IDEMPOTENCY, CLAIM ACCURACY, STALENESS, FRESHNESS OF INPUTS. Emails one morning digest to ggoldberg@oxfordra.net; any retraction or published-page edit is drafted and named in the digest, never sent or applied. Full design: docs/superpowers/specs/2026-09-10-ground-truth-auditor-design.md. [MODEL: claude-opus-5 | set 2026-09-10]
---

# ORA Ground-Truth Auditor

Full design rationale, verified ground-truth facts about the substrate, and every risk
this run must respect: `docs/superpowers/specs/2026-09-10-ground-truth-auditor-design.md`.
Read it if anything below is ambiguous -- do not improvise around a gap, the spec's own
Sec 9 exists to close exactly that kind of gap.

## STEP 0 -- self-exclusion sanity check

Before anything else, confirm your OWN task id is `ora-ground-truth-auditor`. Stage 0
excludes this id from its own index automatically -- if you ever see this task's own
run listed as something to audit, STOP. That means self-exclusion broke, and auditing
your own run trivially "passes" every axis, which is worse than not auditing at all.

## STEP 1 -- build the run index (Stage 0, deterministic, no judgment)

```
"C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" "C:/Users/Owner/.claude/maintenance/ground-truth-run-index.py" --out "C:/Users/Owner/.claude/maintenance/_state/ground-truth/run-index-<today's date, YYYY-MM-DD>.json"
```

This script decides its own window (default 24h, auto-widened for a catch-up burst or a
gap in the auditor's own last run -- read its stdout `window_reason`), joins every run to
its transcript, flags duplicates, and asserts the join-rate floor. **If it exits non-zero
(JOIN-RATE FLOOR BREACHED on stderr), do not silently continue** -- this means the join
mechanism itself may be broken, not just noisy. Include the exact stderr line in the
digest's own status section regardless of what else the run finds, and still complete
every other step below (a broken floor is a finding, not a reason to abort the audit).

## STEP 2 -- extract side effects (Stage 1, deterministic, no judgment)

```
"C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" "C:/Users/Owner/.claude/maintenance/ground-truth-side-effects.py" --run-index "<the file STEP 1 wrote>"
```

Read its stdout line (`N runs: M to verifier, K stamped clean`) -- this is the
`side_effect_stats` figure the digest's Runs Audited section reports verbatim, and the
gated/ungated trend that Sec 9 R3 exists to make visible.

## STEP 3 -- dispatch one verifier per side-effecting run

For every run in the annotated index where `has_side_effects` was true (i.e. every run
in the index MINUS the `stamped_clean` count from STEP 2), dispatch one subagent.

**Model floor for each dispatch** -- resolve with:

```python
import sys
sys.path.insert(0, r"C:\Users\Owner\.claude\maintenance")
import importlib.util
spec = importlib.util.spec_from_file_location("gmr", r"C:\Users\Owner\.claude\maintenance\ground-truth-model-resolve.py")
gmr = importlib.util.module_from_spec(spec); spec.loader.exec_module(gmr)
verifier_model, reasoning = gmr.resolve_verifier_model(task_record, skill_md_text, session_record)
```

where `task_record` is the run's registry entry, `skill_md_text` is the contents of the
audited task's own SKILL.md (read its `filePath` from the registry), and `session_record`
is the joined session dict if one exists. **Runs touching financial data, governor
constants (DSCR/LTV), or a confidential deal never verify below Fable regardless of what
the ladder returns** -- round up explicitly for those, per CLAUDE.md's Dispatch
invariants. Pin the resolved model explicitly on every dispatch; never omit it.

**The verifier's prompt is assembled from ONLY the following** -- this is the input-starvation
mechanism (spec Sec 6.1), the primary defence for the absolute rule. Do NOT include the
run's own summary, the body of what it emailed, or any prior finding about it:

- the run's `run_id`, `task_id`, `fleet`, `last_scheduled_for`
- primary-source LOCATORS ONLY, derived from the run's side_effects and transcript --
  a Notion page id, an Outlook message subject+date to search Sent Items for, a commit
  sha, a file path, a parcel/lease identifier. Extract these by grep'ing the transcript
  for the same patterns STEP 2's script matched (Notion page ids appear near
  `notion-create-pages`/`notion-update-page` calls; commit shas follow `git push`
  output; file paths follow `Write`/`Edit` tool_use blocks).
- the four axes below, verbatim
- the absolute rule, verbatim: "Never treat a prior summary, log line, or finding as
  evidence. Re-derive every claim from the primary source you just read yourself."

**Verifier task prompt template** (fill the bracketed fields, dispatch via the Agent tool,
`subagent_type: general-purpose`, the resolved `verifier_model`, in parallel across all
side-effecting runs in one message so they run concurrently):

> You are an independent verifier auditing one prior scheduled-task run. You have NO
> access to and must NOT trust any summary, email body, log line, or finding this run
> produced. Every claim you report must be re-derived by YOU, right now, from the actual
> primary source: read the raw file, the actual current Notion page contents, the git
> history, the lease document -- not a description of it.
>
> Run under audit: `[run_id]`, task `[task_id]`, fleet `[fleet]`, scheduled for
> `[last_scheduled_for]`.
>
> Primary-source locators for this run (go read these yourself; do not ask for more
> context about the run itself):
> `[locator list]`
>
> Report on all four axes:
>
> **IDEMPOTENCY** -- read the actual target(s) named above. Are there two Notion pages
> for one logical cycle? Two emails with the same subject on the relevant date in Sent
> Items? Two commits with identical content? (Cron/trigger double-fire detection was
> already done deterministically upstream -- you are checking the ACTUAL TARGET STATE
> for doubles, not re-deriving the cron analysis.)
>
> **CLAIM ACCURACY** -- enumerate every factual assertion in the published artifact,
> read AT ITS SOURCE (the live Notion page, the actual Sent Items message) -- never from
> a transcript's account of what was published. For each claim, cite the primary source
> you personally read that supports or contradicts it, and mark it SUPPORTED,
> CONTRADICTED, or UNVERIFIABLE. UNVERIFIABLE means the primary source was unreachable --
> report that plainly, never upgrade it to SUPPORTED because you couldn't check.
>
> **STALENESS** -- for each plan item, pin, or config value this run acted on, compare
> the state AT RUN TIME (use `git log` / `git show` to reconstruct it precisely) against
> the CURRENT state. Flag anything that was a no-op, or that reverted a newer state.
>
> **FRESHNESS OF INPUTS** -- for every upstream data source this run depended on, report
> its actual last-updated timestamp (read it yourself) and state whether a staleness
> alarm should have fired but did not. The ORA Master Workbook mirror is STALE past 7
> days -- if this run used it, check its age explicitly.
>
> Compile your findings as a numbered facts dossier (F-1, F-2, ...) per the
> evidence-dossier-drafting skill's VERIFY step -- every fact carries the exact command
> or read you ran to establish it. Every axis verdict above must cite at least one F-id.
> A verdict with no F-id, or citing an F-id whose source does not actually support it,
> will be dropped before publication -- so do not write one.

## STEP 4 -- F-id discipline and the refuter pass (Sec 6.2, 6.3)

After every verifier returns, drop any verdict that cites no F-id or whose cited F-id's
source text does not actually support the claim made (read the F-id's evidence yourself
-- do not take the verifier's word that its own citation is valid).

For every surviving **CONTRADICTED** verdict, dispatch a second agent (same or higher
model tier as the verifier that produced it) with this brief:

> Re-read the exact primary source at `[locator]` yourself. A prior verifier concluded
> the claim "`[claim text]`" is CONTRADICTED, citing `[F-id and its evidence]`. Argue
> the ORIGINAL claim was actually right. If you cannot construct a good-faith argument
> that the original claim holds, say so and explain why the contradiction survives.

A contradiction that survives this refuter pass goes to the digest. One that does not
survive is downgraded to UNVERIFIABLE (not silently dropped) and logged in the run's own
notes for STEP 6's systemic-cause review.

## STEP 5 -- STALENESS and FRESHNESS roll-up

Independent of the per-run verifiers, using the `recorded_skips` field already present
on every run in the index (no re-derivation needed -- Stage 0 read this from the
registry directly): for every run with a non-empty `recorded_skips` list, note the skip
reasons and dates in the digest's Runs Audited section as context, not as a separate
axis finding.

## STEP 6 -- approval gate for corrections (Hard Invariant 1, spec Sec 7)

For any CONTRADICTED claim (post-refuter) or duplicate side effect whose fix would mean
sending a retraction email or editing a published page:

1. Draft the full correction (email body or page edit) to
   `C:\Users\Owner\.claude\maintenance\_state\ground-truth-pending-approval\<today's date>\<run_id>\`.
2. Name it in the digest with a one-line summary of what it would change.
3. **Do NOT send it. Do NOT apply it.** No exception -- this is an outbound
   counterparty send or a live-page edit, both of which require Gabriel's explicit
   in-turn confirmation regardless of how confident the verifier+refuter pair was.

## STEP 7 -- systemic-cause open items

For any finding that points at a systemic cause (not a one-off) -- a cron collision that
will recur nightly, a join mechanism that is silently degrading, a skill that
structurally cannot avoid duplicating a side effect -- file an open item:

```
ID=$("C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" "C:/Users/Owner/.claude/maintenance/allocate-oi-id.py" --session $CLAUDE_CODE_SESSION_ID --note "<why>")
```

Never hand-compute the next OI-NNN. Reference the allocated id in the digest's Open
Items section.

## STEP 8 -- compose and send the morning digest

One HTML email, `ggoldberg@oxfordra.net` **only** -- no cc (the ora-am-brief Eric-cc
exception does not extend here). Sections, in this exact order:

1. **Runs audited** -- total count, fleet split, `side_effect_stats` from STEP 2
   verbatim (verifiers dispatched vs stamped clean), the join-rate floor result from
   STEP 1 (state the window actually used and why, per its `window_reason`), and any
   run skipped entirely with the reason.
2. **CONTRADICTED claims** -- highest priority. For each: the claim, the F-id evidence
   that contradicts it, and the drafted correction's location from STEP 6 (never its
   content inline if it's a page edit -- link the path).
3. **Duplicate side effects** -- from STEP 1's `duplicate_flags` plus anything a
   verifier found at the target itself (STEP 3's IDEMPOTENCY axis). Remediation steps
   for each.
4. **Open items filed** -- the OI-NNN ids from STEP 7, one line each.

Send via:

```
powershell -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "[ORA] Ground-Truth Audit -- <today's date>" -BodyFile "<path to the composed HTML>" -BodyFormat html
```

Exit-code handling (canon): exit 2 (COM failure) or 4 (timeout) -- retry once, then flag
loudly if it fails again (do not halt the task over a send failure once the digest is
drafted and saved). Exit 1 (usage error) or 3 (stuck wizard) -- do not retry, flag
immediately with the exact exit code and stderr.

## STEP 9 -- completion note

Do not email a second time. Report in the task's own completion notification: runs
audited, verifiers dispatched, CONTRADICTED count (pre- and post-refuter), duplicate
flags, OI ids filed, and the join-rate floor's pass/fail state per fleet.
```

- [ ] **Step 2: Commit**

```bash
mkdir -p scheduled-tasks/ora-ground-truth-auditor
git add scheduled-tasks/ora-ground-truth-auditor/SKILL.md
git commit -m "feat(ground-truth-auditor): SKILL.md runtime instructions (Stage 2-4, trust enforcement, approval gate)"
```

---

## Task 9: Dry-run integration check against the live registries

**Files:** none created or modified -- this task is verification only (Done Bar: evidence-before-claim).

**Interfaces:**
- Consumes: `maintenance/ground-truth-run-index.py`, `maintenance/ground-truth-side-effects.py` (Tasks 5, 6), run against the REAL live registries.

- [ ] **Step 1: Run Stage 0 against the live registries**

```bash
"C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" "C:/Users/Owner/.claude/maintenance/ground-truth-run-index.py" --out "C:/Users/Owner/.claude/maintenance/_state/ground-truth/DRYRUN-run-index.json"
```

Expected: exit 0, a printed `wrote ... (N runs, M duplicate flags)` line. Given the fleet
is paused as of this writing (spec Sec 3.7: CC 1/38 enabled, LAMS 3/29), N will be small
(likely 0-3 runs) until the 2026-09-11 16:01 ET resume. **This is expected, not a bug** --
re-run this same command any time after the resume to see a fuller index.

- [ ] **Step 2: Inspect the output for correctness**

```bash
python -c "import json; d=json.load(open(r'C:\Users\Owner\.claude\maintenance\_state\ground-truth\DRYRUN-run-index.json', encoding='utf-8')); print('window:', d['window_hours'], d['window_reason']); print('runs:', len(d['runs'])); [print(' ', r['run_id'], 'joined=' + str(r['joined'])) for r in d['runs']]; print('join_stats:', d['join_stats']); print('dup flags:', d['duplicate_flags'])"
```

Confirm: `window_hours` and `window_reason` make sense given the pause state; every run's
`joined` field is `True` or `False` (never missing); `join_stats` for each fleet shows
`rate_ok: true` (or, if `false`, that the message names a plausible cause -- e.g. the
paused fleet producing a tiny denominator where one miss swings the rate hard. If
`rate_ok` is `false` for a reason that does NOT trace to the small-denominator pause
state, STOP and re-examine the join logic before proceeding to Task 10).

- [ ] **Step 3: Run Stage 1 against the same output**

```bash
"C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" "C:/Users/Owner/.claude/maintenance/ground-truth-side-effects.py" --run-index "C:/Users/Owner/.claude/maintenance/_state/ground-truth/DRYRUN-run-index.json"
```

Expected: exit 0, a printed `N runs: M to verifier, K stamped clean` line where `M + K == N`.

- [ ] **Step 4: Clean up the dry-run artifact**

```bash
rm -f "C:/Users/Owner/.claude/maintenance/_state/ground-truth/DRYRUN-run-index.json"
```

This was a throwaway verification file, not the real nightly output -- do not commit it.

- [ ] **Step 5: No commit** -- this task produces no file changes, only evidence that Tasks 1-6 behave correctly against real data before Task 10's review and Task 11's registration.

---

## Task 10: Adversarial REFUTE pass (mandatory, Done Bar)

**Files:** none created -- this task dispatches a review, per CLAUDE.md's Done Bar: "mandatory adversarial REFUTE pass for financial/security-gate code." This auditor gates financial and governor-touching output (spec Sec 8), which puts it in that class.

**Interfaces:**
- Consumes: the full diff from Tasks 1-8 (3 Python modules + 3 test files + 1 SKILL.md).

- [ ] **Step 1: Confirm the branch is clean and every test passes**

```bash
cd C:/Users/Owner/.claude/.claude/worktrees/ground-truth-auditor
python maintenance/test-ground-truth-run-index.py && \
python maintenance/test-ground-truth-side-effects.py && \
python maintenance/test-ground-truth-model-resolve.py
git status --porcelain
```

Expected: all three test files print `ALL PASS`; `git status --porcelain` shows nothing
uncommitted (everything from Tasks 1-8 already committed).

- [ ] **Step 2: Dispatch the adversarial review**

Use the `Skill` tool to invoke `requesting-code-review` (per CLAUDE.md's code-review
tie-break: `requesting-code-review` routes to native `/code-review` on the diff, not a
bare subagent), scoped to the diff between `main` and `feat/ground-truth-auditor`.
Brief it explicitly to REFUTE, not confirm, with these specific things to try to break:

- the task-to-session join's 2-second tolerance window and title-disambiguation logic
  (Sec 3.5a) -- try to construct a plausible burst scenario where it silently picks the
  WRONG session rather than degrading to unjoined;
- the join-rate floor's three-tier schedule -- try to construct a window width where
  the floor is either too strict (false-alarms a legitimate widen) or too loose (misses
  a genuinely broken join);
- the model-resolution ladder's fail-safe -- confirm there is no code path where an
  unresolved or unrecognized audited model resolves to anything OTHER than Fable;
- the SKILL.md's STEP 6 approval gate -- confirm there is no path where a drafted
  correction is sent or a page edit applied without Gabriel's in-turn confirmation;
- the self-exclusion mechanism -- confirm `SELF_TASK_ID` filtering happens before the
  window filter, not after (an ordering bug here would still audit a self-run that
  happens to fall outside a narrow window, but not one inside it -- check both).

- [ ] **Step 3: Address every CONFIRMED finding**

For each finding the review returns with verdict CONFIRMED, fix it in the relevant file,
re-run that file's own test suite, and commit the fix with a message referencing what the
review caught. A finding marked PLAUSIBLE-but-not-CONFIRMED gets a one-line note in the
next commit message explaining why it was not actioned, not silence.

- [ ] **Step 4: Commit any fixes**

```bash
git add -A -- maintenance/ scheduled-tasks/ora-ground-truth-auditor/
git commit -m "fix(ground-truth-auditor): address adversarial review findings"
```

(Skip this step entirely if the review returned zero CONFIRMED findings -- do not
manufacture a commit.)

---

## Task 11: Landing -- registration and resume-list append

**Files:**
- Modify: `scheduled-tasks/ora-routine-pause-resume-2026-09-11/SKILL.md` (append item 38)

**Interfaces:** none -- this task is operational (MCP tool calls + one coordinated file edit), not code.

- [ ] **Step 1: Check for concurrent activity on the registry**

```bash
tail -20 "C:/Users/Owner/.claude/maintenance/_state/registry-membership.log"
```

Confirm no other session's activity is mid-flight on the CC registry in the last few
minutes. If there is, stop and reconcile per the single-writer doctrine before
proceeding (do not register concurrently with another session's registry write).

- [ ] **Step 2: Coordinate on the resume SKILL.md's existing claim**

Session `9ca9fdea` (`hooks-override-auth`) held a claim on
`scheduled-tasks/ora-routine-pause-resume-2026-09-11/SKILL.md` as of this plan's
brainstorming phase (block-sentinel fleet adoption work, touching scheduled-task
SKILL.mds broadly). Before editing that file:

```bash
python "C:/Users/Owner/.claude/hooks/lib/claim_work.py" list
```

If `hooks-override-auth` (or any other slug) still shows a live claim covering that
path, use `ListAgents` to find session `9ca9fdea` (or whichever session holds it) and
send a message describing the single-line append you intend (item 38, appending after
the existing item 37, no other change) before touching the file. Proceed only after
either (a) the claim has expired/been released, or (b) the other session confirms no
conflict. Do not silently edit a file another session has claimed.

- [ ] **Step 3: Claim the paths for this landing step**

```bash
python "C:/Users/Owner/.claude/hooks/lib/claim_work.py" renew ground-truth-auditor
python "C:/Users/Owner/.claude/maintenance/preflight-shared-checkout.py" --paths "scheduled-tasks/ora-routine-pause-resume-2026-09-11/SKILL.md" "scheduled-tasks/ora-ground-truth-auditor" --repo "C:/Users/Owner/.claude"
```

Expected exit 0 (CLEAR). Any other exit code -- stop and resolve per that script's own
precedence (NOT_A_REPO > HEAD_MOVED > CONTESTED > INDETERMINATE) before continuing.

- [ ] **Step 4: Register the task, disabled**

In a supervised session with the `scheduled-tasks` MCP tools available, call
`create_scheduled_task` with:
- `id`: `ora-ground-truth-auditor`
- `cronExpression`: `0 4 * * *`
- `filePath`: `C:\Users\Owner\.claude\scheduled-tasks\ora-ground-truth-auditor\SKILL.md`
- `enabled`: `false` (respects the standing fleet pause -- spec Sec 4)
- `model`: `claude-opus-5`

Per Rule 1 of `register-scheduled-task`: if this session lacks the MCP tool, STOP and
report that registration must happen from a supervised session with it -- do not
improvise a registry JSON edit.

- [ ] **Step 5: Verify registration**

Call `list_scheduled_tasks` and confirm `ora-ground-truth-auditor` appears with
`enabled: false` and the correct `cronExpression`/`filePath`.

- [ ] **Step 6: Append item 38 to the resume list**

Read the current end of `scheduled-tasks/ora-routine-pause-resume-2026-09-11/SKILL.md`
(the numbered list currently ends at item 37, `ora-checkout-merge-forward`, per the
NOTE block explaining why that item was added mid-pause). Add:

```
38. ora-ground-truth-auditor
```

immediately after item 37, and update the `STEP 1` instruction line that currently reads
`for each of the following 37 task ids` to `for each of the following 38 task ids`.
Update the frontmatter `description` line's count similarly if it names "37" anywhere.
Also add one sentence to the existing explanatory NOTE (the one that already explains
why `ora-checkout-merge-forward` was appended as item 37) noting that
`ora-ground-truth-auditor` was registered after this pause began, for the same reason,
and follows the same precedent -- so a future reader sees why item 38 exists without
re-deriving it from git blame.

- [ ] **Step 7: Commit**

```bash
git add scheduled-tasks/ora-routine-pause-resume-2026-09-11/SKILL.md
git commit -m "feat(ground-truth-auditor): register disabled, append to 2026-09-11 fleet-resume list"
```

- [ ] **Step 8: Push and open the PR**

```bash
git push -u origin feat/ground-truth-auditor
gh pr create --title "Ground-Truth Auditor: nightly claim re-derivation for the fleet" --body "$(cat <<'EOF'
Implements the ground-truth auditor per docs/superpowers/specs/2026-09-10-ground-truth-auditor-design.md.

- Stage 0 (deterministic): dual-fleet run index, task-to-session join (createdAt/title match, NOT notifySessionId -- see spec Sec 3.5a), duplicate detection, width-dependent join-rate floor.
- Stage 1 (deterministic): side-effect extraction and the cost gate (~8-15 verifiers/night vs 64).
- Model-resolution ladder: registry -> SKILL.md tag -> session record -> fail-safe to Fable.
- SKILL.md: verifier dispatch (input-starvation + F-id discipline + adversarial refuter), the four axes, the digest, and the Hard-Invariant-1 approval gate (drafted, never sent/applied).
- Registered disabled, appended as item 38 to the 2026-09-11 fleet-resume list.

Adversarial review: see commit history for findings addressed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 9: Release the claim**

```bash
python "C:/Users/Owner/.claude/hooks/lib/claim_work.py" release ground-truth-auditor
```

---

## Self-Review Notes

**Spec coverage:** Sec 1-2 (problem/goal) -> Task 8's SKILL.md header and absolute-rule
enforcement. Sec 3 (ground truth, incl. 3.5a) -> Tasks 1-2's constants and join logic.
Sec 4 (landing) -> Task 11. Sec 5 Stage 0 -> Tasks 1-5. Stage 1 -> Task 6. Stage 2
(verifier dispatch + model ladder) -> Task 7 + Task 8 STEP 3. Stage 3 (four axes) ->
Task 8 STEP 3's prompt template. Stage 4 (digest) -> Task 8 STEP 8. Sec 6 (trust
enforcement) -> Task 8 STEP 3 (input starvation), STEP 4 (F-id + refuter). Sec 7
(approval gate) -> Task 8 STEP 6. Sec 8 (testing) -> every task's fixtures map 1:1 to
the spec's required-fixtures list (catch-up burst -> Task 1; same-cycle re-fire,
cross-fleet twin -> Task 3; scheduled-vs-actual drift -> Task 1's AHM fixture;
transcript-absent -> Task 2; self-run-present -> Task 5) plus Task 10's mandatory
REFUTE pass. Sec 9 risks -> R1/R1a into Tasks 2/4, R2 into Task 8's CLAIM ACCURACY
prompt, R3 into Task 6's stats, R4 into Task 11 Steps 1-3. Sec 10 (out of scope) ->
nothing in this plan touches automation-health-monitor, ora-task-integrity-guard, or
non-fleet automation.

**Placeholder scan:** none found -- every step has complete code or an exact command.

**Type consistency:** `run_record`/`run` dicts carry the same keys everywhere they cross
a function boundary (`joined`, `transcript`, `side_effects`, `run_id`, `fleet`,
`task_id`) -- verified across Tasks 5 and 6. `resolve_verifier_model`'s return shape
`(model_id: str, reasoning: str)` matches its one caller in Task 8 STEP 3.
