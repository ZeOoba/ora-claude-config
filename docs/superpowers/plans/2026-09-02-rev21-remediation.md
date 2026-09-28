# Automation Audit Revision 21 — Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the code-fixable findings from Automation Audit Revision 21 — chiefly the detection gap that let a money-moving billing job miss its only monthly fire without any monitor noticing.

**Architecture:** Five independent workstreams, each landing on its own branch with its own test cycle. W-A (fleet detection) is the only one that changes behaviour anything else depends on; the rest are isolated. No workstream touches a financial model, a governor constant, a scheduled-task registry, or `settings.json`.

**Tech Stack:** Python 3.13 (stdlib only — `fleet-status.py` is deliberately dependency-free), PowerShell 5.1, Markdown skill definitions.

**Dispatch model:** every task in this plan dispatches at **Fable 5.1** (`model: fable`, resolves to `claude-fable-5-1`). See Global Constraints for the mandatory post-dispatch floor verification — a `model:` pin is known to fall back mid-run in this environment.

---

## ⚠️ STATUS RE-VERIFIED 2026-09-06 — most of this plan is OBSOLETE. Read before executing.

Written 2026-09-02. Revisions 22 and 23 ran in the interval and other sessions landed most of this work by other routes. **Verified against live ground truth 2026-09-06, not inferred.**

| Workstream | Status 2026-09-06 | Evidence |
|---|---|---|
| **W-A** fleet detection (R21-2b) | ✅ **DONE on `origin/main` — do NOT re-implement** | `never_ran_overdue_reason` carries `"first slot %sZ elapsed >%dh unfired"` + `"age exceeds %dd cadence buffer"`; DST-aware walkers via `_local_utc_offset()`; 19 tests incl. `test_monthly_never_ran_first_slot_elapsed_is_overdue` and `test_monthly_never_ran_slot_before_registration_not_overdue`. Landed via **PR #158**, not #160. |
| **W-B** log rotation (R21-10) | ✅ **DONE** — PR #162 (`fbb875d`) | Inline `Invoke-LogRotation` in both `.ps1` writers (archives to `_log_archive/`, never deletes). Implemented inline, **not** as the `lib/Rotate-Log.ps1` this plan specified. |
| **W-C** ora-pm-ledger retention (R21-9) | ❗ **STILL OPEN and worsening** | `grep -c state_retention scheduled-tasks/ora-pm-ledger/SKILL.md` = **0**. `state/` now **41,241,247B** — up from 36.28MB at audit time (**+13.7%**). |
| **W-D1** "health check" collision | ✅ mostly done — `10ecba4` | `exception-detection` now reads **"portfolio health check"** (bare phrase gone), exactly as this plan specified. **Residual:** CLAUDE.md's `Exception scans:` tie-break still names only `exception-detection · portfolio-anomaly-scout` — `automation-health-monitor` is still unarbitrated there. Blast radius, Gabriel's call. |
| **W-D2** three low-severity overlaps | ✅ **DONE** — `10ecba4` | `ora-millage-lookup` and `pma-qc` now carry "Distinct from" clauses. |
| **W-E1** Thread-4 paths (R21-13) | likely done at v1.7 (`10ecba4`) — verify, don't re-apply | File is already **v1.7**, not the v1.6 this plan assumed. |
| **W-E2/E3** section cap + working-copy rule | ❗ **STILL OPEN** | `grep -c "Section cap\|R21-11\|authored fragment"` = **0**. Dispatched 2026-09-06. Bump to **v1.8** (v1.7 is taken). |
| **W-F** off-host watchdog (R21-4) | ❓ unverified | Not investigated since. |

### Two corrections this re-verification produced

1. **A PR's `MERGED` state is not proof its code is on `main`.** `gh pr view 160` reports `MERGED` — but `b9c8d1b` / PR #164 (`fix/revert-160-stale-merge`) reverted it hours later. Check for a revert commit before concluding a fix landed.
2. **MEMORY.md's "R21-2b's never-ran detector gap is still OPEN" is itself wrong** and should not be cited. It correctly noted #160 was reverted, then inferred the gap was still open — but the fix had already arrived via PR #158. The revert *restored* the better implementation rather than removing the fix.

### The reusable lesson — it applies to this plan

PR #164's post-mortem: *"Verifying a stale branch in isolation tells you it is internally consistent, never that it is still correct against a main that moved."* PR #160 was internally consistent and its tests passed; merging it silently replaced newer DST-aware logic with its own older copy, because git saw no textual conflict. **This plan is that stale branch.** Executing it wholesale on 2026-09-06 would have re-introduced exactly that class of regression. Re-verify every workstream against live state before dispatching it.

### Local checkout caveat

`~/.claude` is on branch `feat/model-canary-probe-step25` at `0ba45bc`, **53 commits behind `origin/main`** — so W-A and W-B's fixes are on main but NOT in the local working tree. Reconciling that is claimed by session `cfa82179` (`repo-housekeeping`). **Do not do git surgery on `~/.claude` while that claim is live** — which is also why W-C is deferred rather than executed now.

---

## Global Constraints

- **Model floor: Fable.** Every `Agent` dispatch pins `model: fable`. After each workstream, run `python ~/.claude/maintenance/check-dispatch-model-floor.py --session $CLAUDE_CODE_SESSION_ID --floor fable`. Exit 0 = floor held; exit 1 = a subagent ran below floor or fell back — **redo that task's review at Fable or above.** A pin is not proof (memory: `feedback_agent_model_pin_not_held_end_to_end`).
- **Reviewer ≥ implementer.** Fable implements, Fable or Opus reviews. Never review below the implementer's tier.
- **`~/ora-skills` is SINGLE-WRITER.** Before any edit there: `git log --oneline -1` + `git status -sb`. If HEAD is newer than session start, or uncommitted changes are not yours, STOP. Full protocol: `memory/rules.md §14`. Use `anthropic-skills:isolated-commit` to land.
- **`~/.claude` MAIN checkout is dirty** (29 uncommitted changes at plan time, session `bc62c964` has recorded edits in that set). Do **not** commit from the main checkout. Use an isolated worktree (`EnterWorktree` / `npm run worktree`) and `git diff --cached` before every commit — a bare `git commit` sweeps another session's staged index (this exact failure is on record in the audit artifact).
- **Blast radius — needs Gabriel's explicit sign-off before landing:** `hooks/**`, `settings.json`, `CLAUDE.md`, scheduled-task registries, governor-constant files. W-D1 Step 5 touches CLAUDE.md and is gated on that; no other task in this plan does.
- **Never delete — move to `/archive/`** (Hard Invariant 6). This is why `state_retention.py` archives rather than prunes; do not "fix" that into a delete.
- **Do not run `ora-pm-monthly-billing` or any billing trigger from this plan.** Money-moving, Hard Invariant 1 — see "Not code-fixable" below.
- **Allocate OI ids, never hand-compute:** `ID=$(python ~/.claude/maintenance/allocate-oi-id.py --session $CLAUDE_CODE_SESSION_ID --note "<why>")`.
- **Event-log writes go through `python ~/.claude/maintenance/append-event-log.py` only.** Never Edit-anchor the header.

---

## Finding coverage

Every Revision 21 finding is either assigned a task or explicitly declared not code-fixable. No finding is silently dropped.

| Finding | Disposition |
|---|---|
| R21-1 four-day host outage | **Not code-fixable** — host availability. Its *detectability* is R21-4. |
| R21-2 billing missed its only fire | **CLOSED 2026-09-02** — self-healed via catch-up, registry-verified. See below. |
| R21-2b `fleet-status.py` blind to it | **W-A** (A1–A3) |
| R21-3 two daily tasks unrecovered + `ORA PM Crons` disabled | **CLOSED** (both recovered, verified) + **Gabriel** (`ORA PM Crons` re-enable decision) |
| R21-4 monitors co-located on the failing host | **W-F** — investigation task, cannot plan a fix blind |
| R21-5 windows-tasks WARN root-caused | **Closed at Rev 21.** No task. |
| R21-6 three-way "health check" collision | **W-D1** |
| R21-7 millage/tax-appeal, pma-qc, annual-report | **W-D2** |
| R21-8 `ora-setup-audit` ×3 byte-identical copies | **Gabriel** — which copy is canonical is a decision, not a defect |
| R21-9 `ora-pm-ledger` retention unwired | **W-C** (scope corrected — see W-C preamble) |
| R21-10 unrotated maintenance logs | **W-B** |
| R21-11 artifact cap covers only the masthead | **W-E2** (mechanism) + **Gabriel** (how much stays inline) |
| R21-12 two items closed | **Closed at Rev 21.** No task. |
| R21-13 skill runbook path errors | **W-E1** |
| R21-14 frame-runtime wrappers in working copy | **Fixed at Rev 21**; **W-E3** adds the rule so it cannot recur |

### Not code-fixable — these need Gabriel, not a dispatch

1. ~~**`ora-pm-monthly-billing`'s September run.**~~ **CLOSED 2026-09-02 — no action needed.** It fired via normal automated catch-up at `10:43:30Z` carrying `lastScheduledFor 2026-09-01T09:10:00Z` — i.e. it ran the exact slot it had missed — and posted **139 charges, 0 skipped, 0 errors, remaining=0** in a single pass. Registry-verified directly, not taken from another session's note. Autopay was unexercised (0 eligible leases, OI-068 still open), so no Stripe debit was ever at risk.

   **Timing footnote worth keeping.** The audit's `fleet-status.py` snapshot was stamped 12:36:30 local; the task fired at 12:43:30 local (this host is UTC+2) — **seven minutes later.** The finding was correct at read time, and the tool's own header warning ("SNAPSHOT, NOT LIVE STATE — re-run immediately before acting on any flagged item") was precisely the right caveat. **This does not weaken W-A:** for roughly 25 hours a money-moving task sat past its only monthly slot while the probe reported `0 overdue`. Self-healing is not detection.
2. **`ORA PM Crons`** (Windows task, `state=Disabled` since 2026-08-16, `0x8007042B` ERROR_PROCESS_ABORTED). Re-enable, retire, or leave — it has been dead 17 days without anyone missing it, which is itself evidence.
3. **R21-8 canonical copy.** Three byte-identical copies is only a problem once they diverge; the post-commit auto-sync currently prevents that. Declaring one canonical is a doctrine call.
4. **R21-11's retention parameter.** W-E2 builds the section cap; *how many* revisions of finding-sections stay inline is your editorial judgment. Plan assumes **2** unless told otherwise.

---

## File Structure

| File | Responsibility | Workstream |
|---|---|---|
| `~/.claude/maintenance/fleet-status.py` | add `--now-iso`; add elapsed-slot rule to `never_ran_overdue` | W-A |
| `~/.claude/maintenance/test-fleet-status.py` | deterministic clock; new regression tests | W-A |
| `~/.claude/maintenance/lib/Rotate-Log.ps1` | **new** — shared log rotation helper | W-B |
| `~/.claude/maintenance/test-rotate-log.py` | **new** — rotation tests | W-B |
| `~/.claude/maintenance/push-fleet-heartbeat.ps1` | dot-source + call rotation | W-B |
| `~/.claude/maintenance/stuck-session-watchdog.ps1` | dot-source + call rotation | W-B |
| `~/.claude/scheduled-tasks/ora-pm-ledger/SKILL.md` | wire `state_retention.py` into the run path | W-C |
| `~/ora-skills/exception-detection/SKILL.md` | drop `health check` trigger | W-D1 |
| `~/ora-skills/{ora-millage-lookup,pma-qc,annual-cycle}/SKILL.md` | add disambiguating clauses | W-D2 |
| `~/.claude/CLAUDE.md` | one exception-scan tie-break clause naming `automation-health-monitor` | W-D1 (**blast radius**) |
| `~/ora-skills/ora-setup-audit/SKILL.md` | Thread-4 paths, section cap, working-copy rule → v1.7 | W-E |

---

## W-A — Fleet detection: a never-ran task whose first slot elapsed (R21-2b)

**Why this is still the highest-value task in the plan, even though the incident closed itself.** The billing job caught up on its own seven minutes after the audit read it (see above). That resolves the *consequence* and changes nothing about the *blindness*: for ~25 hours a money-moving task was past its only monthly slot and `fleet-status.py` reported `of which overdue 0 - (not yet due, by cadence)`. The next miss may land on a day the host stays down. `cadence_buffer_days()` grants a day-of-month-restricted cron a **40-day grace measured from `createdAt`**. It is an *age* heuristic answering "has this task reached its first fire yet?" — it structurally cannot see that a slot came and went. `ora-pm-monthly-billing` (registered 08-21, cron `10 11 1 * *`) missed 09-01 and would have read "0 overdue" until ~09-30. The missed-cycle detector cannot cover the gap either: it returns early on never-ran tasks by design (`fleet-status.py:475`).

**Do not fix this by lowering the buffer.** The 40-day value is a deliberate 2026-07-14 recalibration that stopped quarterly tasks pinning the fleet at permanent ATTENTION. The fix is an *additional, independent* trigger.

`most_recent_expected_fire_utc(expr, now_local)` (line 387) already does the cron walk-back and is exercised by `find_missed_cycles`. Reuse it — do not write a new cron parser.

### Task A1: Make the clock injectable

Existing cadence tests are date-dependent and will flip under A2 (`test_monthly_recent_creation_not_overdue` uses `cron="0 5 1 * *", created_days_ago=10` — on any run date after the 1st, a real slot has elapsed). Fix the harness *before* changing behaviour, so A2's test failure is a real signal.

**Files:**
- Modify: `~/.claude/maintenance/fleet-status.py:617-624` (argparse), `:650` (now_ms), `:779` (now_local)
- Modify: `~/.claude/maintenance/test-fleet-status.py:64-79` (`run()` helper)

**Interfaces:**
- Produces: `fleet-status.py --now-iso <naive local ISO8601>` overrides the process clock. Absent → real clock, byte-identical behaviour to today.
- Produces: `run(tasks, skips=None, now_iso=None)` in the test harness.

- [ ] **Step 1: Add the CLI flag**

In `main()`, after the `--json` argument:

```python
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--now-iso",
                    help="override 'now' with a naive local ISO8601 timestamp "
                         "(tests only -- makes cadence/slot checks deterministic)")
    args = ap.parse_args()
```

- [ ] **Step 2: Route every clock read through it**

Replace line 650:

```python
    now_ms = datetime.datetime.now().timestamp() * 1000
```

with:

```python
    if args.now_iso:
        now_ms = datetime.datetime.fromisoformat(args.now_iso).timestamp() * 1000
    else:
        now_ms = datetime.datetime.now().timestamp() * 1000
```

and replace line 779:

```python
    now_local = datetime.datetime.now()
```

with:

```python
    now_local = datetime.datetime.fromtimestamp(now_ms / 1000.0)
```

- [ ] **Step 3: Thread it through the test harness**

In `test-fleet-status.py`, change `run()`:

```python
def run(tasks, skips=None, now_iso=None):
    """Write a synthetic registry, run fleet-status.py --json against it, return the
    parsed JSON (or None + stderr on a hard failure). Pass now_iso to pin the clock
    so cadence/slot assertions do not depend on the calendar date of the test run."""
    reg = {"scheduledTasks": tasks, "recordedSkips": skips or {}}
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "scheduled-tasks.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(reg, fh)
        cmd = [sys.executable, HOOK, "--registry", p, "--json"]
        if now_iso:
            cmd += ["--now-iso", now_iso]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            return None, proc.stderr
        return json.loads(proc.stdout), proc.stderr
```

`task()` builds `createdAt` from `now_ms()` (wall clock). Add a pinned variant next to it:

```python
FIXED_NOW = "2026-09-02T12:00:00"


def fixed_now_ms():
    import datetime as _dt
    return _dt.datetime.fromisoformat(FIXED_NOW).timestamp() * 1000


def pinned_task(id_, cron=None, created_days_ago=None, **kw):
    """task() but with createdAt measured back from FIXED_NOW, not wall clock."""
    t = task(id_, cron=cron, **kw)
    if created_days_ago is not None:
        t["createdAt"] = fixed_now_ms() - int(created_days_ago * DAY)
    return t
```

- [ ] **Step 4: Pin the two date-dependent cadence tests**

Replace `test_quarterly_not_yet_due_is_not_overdue` and `test_monthly_recent_creation_not_overdue`:

```python
# 2. A quarterly task created 10 days ago has NOT reached its first fire.
#    Pinned to FIXED_NOW: most recent Jan/Apr/Jul/Oct-1 fire is 2026-07-01,
#    which PRECEDES creation (2026-08-23), so no slot has elapsed.
def test_quarterly_not_yet_due_is_not_overdue():
    tasks = [pinned_task("quarterly-new", cron="0 8 1 1,4,7,10 *", created_days_ago=10)]
    data, _ = run(tasks, now_iso=FIXED_NOW)
    check("test_quarterly_not_yet_due_is_not_overdue",
          data is not None and data.get("never_ran_overdue") == [],
          "expected no overdue never-ran, got %r" % (data,))


# 4. A monthly task created 1 day ago has NOT exceeded its cadence buffer AND
#    has had no slot elapse since creation (created 2026-09-01T12:00, the 09-01
#    05:00 fire precedes it).
def test_monthly_recent_creation_not_overdue():
    tasks = [pinned_task("monthly-new", cron="0 5 1 * *", created_days_ago=1)]
    data, _ = run(tasks, now_iso=FIXED_NOW)
    check("test_monthly_recent_creation_not_overdue",
          data is not None and data.get("never_ran_overdue") == [],
          "expected not overdue, got %r" % (data,))
```

- [ ] **Step 5: Run the full suite — must be green before any behaviour change**

Run: `python ~/.claude/maintenance/test-fleet-status.py`
Expected: `ALL fleet-status verdict-recalibration tests passed.`, exit 0.

- [ ] **Step 6: Prove `--now-iso` changes nothing when absent**

Run:
```bash
python ~/.claude/maintenance/fleet-status.py --json > /tmp/a.json && python ~/.claude/maintenance/fleet-status.py --json > /tmp/b.json && python -c "
import json;a=json.load(open('/tmp/a.json'));b=json.load(open('/tmp/b.json'))
for k in ('never_ran_overdue','missed_cycles','collisions'):
    assert a.get(k)==b.get(k), k
print('live output stable across runs: PASS')"
```
Expected: `live output stable across runs: PASS`

- [ ] **Step 7: Commit**

```bash
git add maintenance/fleet-status.py maintenance/test-fleet-status.py
git commit -m "test(fleet-status): inject clock via --now-iso, pin date-dependent cadence tests

No behaviour change. Two cadence tests silently depended on the calendar
date of the run; pinning them first so the R21-2b slot-elapsed change
produces a real failure signal rather than a coincidence."
```

### Task A2: Flag a never-ran task whose first real slot has elapsed

**Files:**
- Modify: `~/.claude/maintenance/fleet-status.py:660-672`
- Test: `~/.claude/maintenance/test-fleet-status.py`

**Interfaces:**
- Consumes: `most_recent_expected_fire_utc(expr, now_local) -> naive UTC datetime | None` (line 387); `_local_utc_offset() -> timedelta` (line 367); `MISSED_CYCLE_GRACE_HOURS = 24` (line 347).
- Produces: no signature change. `never_ran_overdue` in `--json` gains entries it previously missed.

- [ ] **Step 1: Write the failing test**

Add to `test-fleet-status.py`. `cron="0 5 1-28 * *"` is day-of-month-restricted (so `cadence_buffer_days` returns 40 and the *old* rule cannot fire at 5 days) but fires nearly daily, so a slot has certainly elapsed since creation:

```python
# 4b. R21-2b: a never-ran WEEKLY task whose slot elapsed 55h ago is overdue,
#     even though its cadence buffer (10d, dow-restricted) has not expired at
#     7 days. Simulated against the real helper before landing:
#     most_recent_expected_fire = 2026-08-31 05:00 local > created 2026-08-26,
#     elapsed 55.0h > the 24h grace; old rule 7 > 10 == False.
def test_never_ran_with_elapsed_slot_is_overdue():
    tasks = [pinned_task("slot-elapsed", cron="0 5 * * 1", created_days_ago=7)]
    data, _ = run(tasks, now_iso=FIXED_NOW)
    check("test_never_ran_with_elapsed_slot_is_overdue",
          data is not None and data.get("never_ran_overdue") == ["slot-elapsed"],
          "expected slot-elapsed flagged overdue, got %r" % (data,))


# 4c. The real regression: monthly-on-the-1st, registered mid-August, slot on
#     09-01 elapsed. Must flag on 09-02 despite the 40-day buffer.
def test_monthly_billing_missed_first_fire_is_overdue():
    tasks = [pinned_task("ora-pm-monthly-billing", cron="10 11 1 * *",
                         created_days_ago=12)]
    data, _ = run(tasks, now_iso=FIXED_NOW)
    check("test_monthly_billing_missed_first_fire_is_overdue",
          data is not None
          and data.get("never_ran_overdue") == ["ora-pm-monthly-billing"],
          "expected billing task flagged overdue, got %r" % (data,))


# 4d. Guard against over-firing: a slot that elapsed LESS than the 24h grace
#     ago is not yet a miss -- the fleet only runs while the app is open.
def test_slot_inside_grace_window_not_yet_overdue():
    tasks = [pinned_task("just-fired-slot", cron="0 6 1-28 * *", created_days_ago=5)]
    data, _ = run(tasks, now_iso="2026-09-02T09:00:00")
    check("test_slot_inside_grace_window_not_yet_overdue",
          data is not None and data.get("never_ran_overdue") == [],
          "slot 3h old must not flag, got %r" % (data,))
```

Register all three in the `__main__` block alongside the existing calls.

> **Known limitation, accepted deliberately — say so in the commit, do not silently ship it.** The rule keys off the MOST RECENT expected fire. For a cron that is day-of-month-restricted yet fires near-daily (e.g. `0 5 1-28 * *`), the latest slot is always <24h old so the grace never trips, while the age buffer is 40 days — such a task stays invisible to both rules. **No task in either live registry has that shape** (checked 2026-09-02). Closing it properly needs a forward slot-walker from `createdAt`, a larger change than this finding justifies. Revisit if that cron shape appears.

- [ ] **Step 2: Run to verify they fail**

Run: `python ~/.claude/maintenance/test-fleet-status.py`
Expected: FAIL on `test_never_ran_with_elapsed_slot_is_overdue`, `test_monthly_billing_missed_first_fire_is_overdue` (`expected ... got []`). `test_slot_inside_grace_window_not_yet_overdue` PASSES already (it asserts current behaviour) — that is correct; it is the over-firing guard.

- [ ] **Step 3: Implement**

Replace the `never_ran_overdue` loop (lines 660-672):

```python
    never_ran_overdue = []
    now_local_slots = datetime.datetime.fromtimestamp(now_ms / 1000.0)
    now_utc_slots = now_local_slots - _local_utc_offset()
    for t in never_ran:
        if fire_at(t):
            continue  # one-time -- not this check's business
        created = t.get("createdAt")
        if not isinstance(created, (int, float)):
            continue  # can't determine age -- don't flag on missing data
        # R21-2b (2026-09-02): SLOT-ELAPSED rule, independent of the age buffer.
        # cadence_buffer_days() answers "has this task reached its first fire
        # yet?" from AGE alone -- it structurally cannot see that a scheduled
        # slot came and went. ora-pm-monthly-billing (money-moving, cron
        # "10 11 1 * *", registered 08-21) missed its 09-01 slot and would have
        # read "0 overdue" until ~09-30 on the 40-day monthly buffer alone.
        # Deliberately NOT a lower buffer: the 40-day value is the 2026-07-14
        # recalibration that stopped quarterly tasks pinning the fleet at
        # permanent ATTENTION. This is an additional trigger, not a replacement.
        expected_utc = most_recent_expected_fire_utc(
            t.get("cronExpression"), now_local_slots)
        if expected_utc is not None:
            created_utc = datetime.datetime.utcfromtimestamp(created / 1000.0)
            if (expected_utc > created_utc
                    and (now_utc_slots - expected_utc)
                    > datetime.timedelta(hours=MISSED_CYCLE_GRACE_HOURS)):
                never_ran_overdue.append(t)
                continue
        buf = cadence_buffer_days(t.get("cronExpression"))
        if buf is None:
            continue  # can't classify cadence -- don't guess
        if (now_ms - created) / 86400000.0 > buf:
            never_ran_overdue.append(t)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python ~/.claude/maintenance/test-fleet-status.py`
Expected: `ALL fleet-status verdict-recalibration tests passed.`, exit 0, **18 tests** (15 original + 3 new).

- [ ] **Step 5: Update the never-ran summary line so the reason is legible**

At line 809-810, the `- (not yet due, by cadence)` fallback now under-describes the check. Replace the label:

```python
    print("      of which overdue  %d   %s" % (len(never_ran_overdue),
          ", ".join(sorted(t.get("id") for t in never_ran_overdue))
          or "- (not yet due: no elapsed slot since registration, and inside cadence buffer)"))
```

- [ ] **Step 6: Commit**

```bash
git add maintenance/fleet-status.py maintenance/test-fleet-status.py
git commit -m "fix(fleet-status): flag never-ran tasks whose first slot already elapsed

Automation Audit R21-2b. cadence_buffer_days() is an age heuristic and
cannot see an elapsed slot; find_missed_cycles() returns early on never-ran
tasks by design (:475). ora-pm-monthly-billing -- money-moving -- missed
2026-09-01 and read '0 overdue' for another four weeks. Adds an independent
slot-elapsed trigger reusing most_recent_expected_fire_utc(), guarded by the
existing 24h grace so a just-passed slot is not a false positive.
3 new tests; buffer semantics unchanged."
```

### Task A3: Verify against the live registry

- [ ] **Step 1: Confirm the live fleet stays clean**

`ora-pm-monthly-billing` has since run, so it correctly no longer qualifies and the live fleet can no longer reproduce the finding. The behaviour proof is A2's pinned regression test, which reconstructs the exact registry state.

Run: `python ~/.claude/maintenance/fleet-status.py | sed -n '/never-ran/,/one-time/p'`
Expected: `never-ran 6`, `of which overdue 0`. **Any non-zero here is a false positive introduced by A2 — do not land.**

- [ ] **Step 2: Confirm no false positives appeared**

The five other never-ran tasks must stay clean: `ora-county-sales-monitor` (due 09-15), `ora-passed-deal-tracker` (09-15), `ora-loan-terms-reconciliation` (09-06), `ora-exit-cap-spotcheck` and `ora-gis-endpoint-liveping` (quarterly, 09-09), plus one-time `ora-counsel-review-standard-positions-2027`.

Run:
```bash
python ~/.claude/maintenance/fleet-status.py --json | python -c "
import json,sys
d=json.load(sys.stdin); od=set(d.get('never_ran_overdue') or [])
bad = od - {'ora-pm-monthly-billing'}
print('unexpected overdue:', sorted(bad) or 'NONE')
sys.exit(1 if bad else 0)"
```
Expected: `unexpected overdue: NONE`, exit 0. **A non-empty result means the rule over-fires — do not land.**

- [ ] **Step 3: Run the full maintenance guard set**

Run: `python ~/.claude/maintenance/setup-self-audit.py`
Expected: no NEW critical; `fleet:` line still `[ OK ]`.

### Task A4: ~~Confirm the two stalled daily tasks recovered~~ — CLOSED, verified 2026-09-02

Both recovered unaided in the same catch-up wave, registry-verified: `ora-pm-daily-crons` ran `10:41:30Z` (slot `2026-09-02T07:40Z`), `ora-memory-commit-sweep` ran `10:42:31Z` (slot `2026-09-01T17:00Z`). `fleet-status.py`'s `missed single cycle (currently open)` is now **0**, down from 2. No `orphaned-task-forensics` escalation needed.

Residual, unchanged and still Gabriel's call: the off-fleet Windows task `ORA PM Crons`, `state=Disabled` since 2026-08-16 (`0x8007042B`).

- [ ] **Step 1: Record the outcome**

```bash
python ~/.claude/maintenance/append-event-log.py --note "R21-3 follow-up: ora-memory-commit-sweep / ora-pm-daily-crons post-outage recovery status verified"
```

---

## W-B — Log rotation for unrotated maintenance logs (R21-10)

`stuck-session-watchdog.log` (963,914B, ~22KB/day) and `push-fleet-heartbeat.log` (508,320B, ~9.6KB/day) append forever. `grep -iE "rotat|MaxLog|trim|Clear-Content|prune|archive"` returns **zero hits** in both writers. Each has exactly one write site — a `Log()` function at line 50 and 48 respectively — so this is a one-point fix in each.

### Task B1: Shared rotation helper, wired into both writers

**Files:**
- Create: `~/.claude/maintenance/lib/Rotate-Log.ps1`
- Create: `~/.claude/maintenance/test-rotate-log.py`
- Modify: `~/.claude/maintenance/push-fleet-heartbeat.ps1:48-50`
- Modify: `~/.claude/maintenance/stuck-session-watchdog.ps1:45-48`

**Interfaces:**
- Produces: `Invoke-LogRotation -Path <string> [-MaxBytes <int>] [-Keep <int>]`. Rotates `x.log` → `x.log.1` → `x.log.2` → `x.log.3`, dropping nothing below `Keep`. Returns `$true` if it rotated.

- [ ] **Step 1: Write the failing test**

`~/.claude/maintenance/test-rotate-log.py`:

```python
#!/usr/bin/env python3
"""Tests for lib/Rotate-Log.ps1 (Automation Audit R21-10)."""
import os
import subprocess
import sys
import tempfile

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib", "Rotate-Log.ps1")
_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + "  " + detail)
        _failures.append(name)


def ps(script):
    return subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                           "-Command", script],
                          capture_output=True, text=True)


def test_small_log_is_not_rotated():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.log")
        open(p, "w").write("small\n")
        ps(". '%s'; Invoke-LogRotation -Path '%s' -MaxBytes 1048576" % (LIB, p))
        check("test_small_log_is_not_rotated",
              os.path.exists(p) and not os.path.exists(p + ".1"),
              "a sub-threshold log must not rotate")


def test_oversized_log_rotates_to_dot1():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.log")
        open(p, "w").write("x" * 2048)
        ps(". '%s'; Invoke-LogRotation -Path '%s' -MaxBytes 1024" % (LIB, p))
        check("test_oversized_log_rotates_to_dot1",
              os.path.exists(p + ".1") and not os.path.exists(p),
              "oversized log must move to .1")


def test_rotation_shifts_and_bounds_at_keep():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.log")
        for i in range(5):
            open(p, "w").write("x" * 2048)
            ps(". '%s'; Invoke-LogRotation -Path '%s' -MaxBytes 1024 -Keep 3"
               % (LIB, p))
        check("test_rotation_shifts_and_bounds_at_keep",
              os.path.exists(p + ".1") and os.path.exists(p + ".3")
              and not os.path.exists(p + ".4"),
              "must keep exactly 3 generations, no .4")


def test_missing_log_is_a_noop():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "absent.log")
        r = ps(". '%s'; Invoke-LogRotation -Path '%s' -MaxBytes 1024" % (LIB, p))
        check("test_missing_log_is_a_noop",
              r.returncode == 0 and not os.path.exists(p + ".1"),
              "absent log must not error, got rc=%s %s" % (r.returncode, r.stderr))


if __name__ == "__main__":
    test_small_log_is_not_rotated()
    test_oversized_log_rotates_to_dot1()
    test_rotation_shifts_and_bounds_at_keep()
    test_missing_log_is_a_noop()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures)))
        sys.exit(1)
    print("\nALL Rotate-Log tests passed.")
    sys.exit(0)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python ~/.claude/maintenance/test-rotate-log.py`
Expected: all four FAIL — `lib/Rotate-Log.ps1` does not exist yet.

- [ ] **Step 3: Implement the helper**

`~/.claude/maintenance/lib/Rotate-Log.ps1`:

```powershell
# Rotate-Log.ps1 -- size-bounded log rotation for ORA maintenance writers.
# Automation Audit R21-10 (2026-09-02): stuck-session-watchdog.log (964KB,
# ~22KB/day) and push-fleet-heartbeat.log (508KB) appended forever with no
# rotation mechanism anywhere in either writer.
#
# FAIL-OPEN by design, matching ORA guard doctrine: a rotation failure must
# never stop the caller from doing its actual job or writing its log line.

function Invoke-LogRotation {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [int]$MaxBytes = 1048576,   # 1 MB
        [int]$Keep = 3              # x.log.1 .. x.log.3 -> ~4 MB bounded total
    )
    try {
        if (-not (Test-Path -LiteralPath $Path)) { return $false }
        if ((Get-Item -LiteralPath $Path).Length -lt $MaxBytes) { return $false }
        for ($i = $Keep - 1; $i -ge 1; $i--) {
            $src = "${Path}.${i}"
            $dst = "${Path}.$($i + 1)"
            if (Test-Path -LiteralPath $src) {
                Move-Item -LiteralPath $src -Destination $dst -Force
            }
        }
        Move-Item -LiteralPath $Path -Destination "${Path}.1" -Force
        return $true
    } catch {
        return $false
    }
}
```

Note the `.4` bound: with `-Keep 3`, the loop shifts `.2`→`.3` and `.1`→`.2`, then the live log becomes `.1`. Nothing ever writes `.4`, so the oldest generation is dropped by being overwritten at `.3`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python ~/.claude/maintenance/test-rotate-log.py`
Expected: `ALL Rotate-Log tests passed.`, exit 0.

- [ ] **Step 5: Wire into `push-fleet-heartbeat.ps1`**

Replace lines 48-50:

```powershell
$log         = Join-Path $primaryRepo 'maintenance\push-fleet-heartbeat.log'

function Log($m) { "$([DateTime]::UtcNow.ToString('s'))Z  $m" | Out-File -FilePath $log -Append -Encoding utf8 }
```

with:

```powershell
$log         = Join-Path $primaryRepo 'maintenance\push-fleet-heartbeat.log'

# R21-10: bound the log before the first write of this run. Fail-open.
$rotLib = Join-Path $env:USERPROFILE '.claude\maintenance\lib\Rotate-Log.ps1'
if (Test-Path -LiteralPath $rotLib) { . $rotLib; Invoke-LogRotation -Path $log | Out-Null }

function Log($m) { "$([DateTime]::UtcNow.ToString('s'))Z  $m" | Out-File -FilePath $log -Append -Encoding utf8 }
```

- [ ] **Step 6: Wire into `stuck-session-watchdog.ps1`**

Replace lines 45-48:

```powershell
$log   = Join-Path $env:USERPROFILE '.claude\maintenance\stuck-session-watchdog.log'
```
...through the `Log` definition at line 48, adding the same three lines immediately before `function Log`:

```powershell
# R21-10: bound the log before the first write of this run. Fail-open.
$rotLib = Join-Path $env:USERPROFILE '.claude\maintenance\lib\Rotate-Log.ps1'
if (Test-Path -LiteralPath $rotLib) { . $rotLib; Invoke-LogRotation -Path $log | Out-Null }
```

- [ ] **Step 7: Verify both scripts still parse and the live logs rotate**

```bash
powershell -NoProfile -Command "\$ErrorActionPreference='Stop'; \$null=[System.Management.Automation.Language.Parser]::ParseFile('C:\Users\Owner\.claude\maintenance\push-fleet-heartbeat.ps1',[ref]\$null,[ref]\$null); \$null=[System.Management.Automation.Language.Parser]::ParseFile('C:\Users\Owner\.claude\maintenance\stuck-session-watchdog.ps1',[ref]\$null,[ref]\$null); 'both parse: PASS'"
```
Expected: `both parse: PASS`

Then confirm the 964KB log actually rotates:
```bash
powershell -NoProfile -Command ". 'C:\Users\Owner\.claude\maintenance\lib\Rotate-Log.ps1'; Invoke-LogRotation -Path 'C:\Users\Owner\.claude\maintenance\stuck-session-watchdog.log'"
ls -la "C:/Users/Owner/.claude/maintenance/stuck-session-watchdog.log"*
```
Expected: `stuck-session-watchdog.log.1` exists at ~964KB; the live log is gone until the next run recreates it. **This is a move, not a delete — Invariant 6 satisfied.**

- [ ] **Step 8: Commit**

```bash
git add maintenance/lib/Rotate-Log.ps1 maintenance/test-rotate-log.py maintenance/push-fleet-heartbeat.ps1 maintenance/stuck-session-watchdog.ps1
git commit -m "fix(maintenance): bound stuck-session-watchdog and push-fleet-heartbeat logs

Automation Audit R21-10. Neither writer had any rotation mechanism; the
watchdog log was 964KB at ~22KB/day and crossed 2MB by mid-November.
Shared fail-open Invoke-LogRotation, 1MB threshold, 3 generations kept
(move, never delete -- Invariant 6). 4 tests."
```

---

## W-C — Wire `ora-pm-ledger` retention into its run path (R21-9)

**Scope correction — read before starting.** Revision 21 reported that `state_retention.py` "covers 3 of 5 categories, omitting `deal-sourcing` and `acquisition-pipeline`." **That is wrong.** `plan()` discovers categories from filenames via `SNAPSHOT_RE` and groups generically; the audit inferred coverage from which `_archive/` subdirectories happened to exist. Its own dry-run, run 2026-09-02, lists **all five**: `acquisition-pipeline` 1, `capex` 3, `deal-sourcing` 2, `property-register` 3, `tenant-db` 3 — 12 files. Do not "fix" category coverage; there is nothing to fix.

Two of the three reported defects are real: it is **wired into nothing** (zero invocations across `scheduled-tasks/` and `maintenance/`), and it **archives by move**, so no disk is reclaimed. The second is correct by design (Invariant 6) and is not a defect — leave it.

The `-latest.json` duplication (2.29MB/day) is also **out of scope**: those files are read back by the five diff engines, and `state_retention.py`'s own docstring explicitly refuses to touch a working production script "for a refactor nobody asked for." Removing them means editing five reviewed engines to save disk that is already trivial. Not worth it.

### Task C1: Add the retention pass to `ora-pm-ledger`'s run

**Files:**
- Modify: `~/.claude/scheduled-tasks/ora-pm-ledger/SKILL.md`

- [ ] **Step 1: Confirm single-writer safety and current state**

```bash
python ~/.claude/maintenance/fleet-status.py | grep ora-pm-ledger
cd "C:/Users/Owner/.claude/scheduled-tasks/ora-pm-ledger" && python state_retention.py --dry-run
```
Expected: task is enabled, cron `0 15 * * *`; dry-run lists 5 categories / 12 files.

- [ ] **Step 2: Append the retention step to the task body**

Add as the final numbered step in `~/.claude/scheduled-tasks/ora-pm-ledger/SKILL.md`:

```markdown
N. **State retention (Automation Audit R21-9, added 2026-09-02).** After the snapshot-diff engines have finished, bound this task's own `state/` directory:

    python "C:\Users\Owner\.claude\scheduled-tasks\ora-pm-ledger\state_retention.py" --keep-days 14

   It MOVES dated snapshots older than 14 days into `state/_archive/<category>/` — never deletes (Invariant 6) — and never touches a `-latest.json` pointer, which the diff engines read back. It is category-agnostic: it discovers categories from filenames, so a new snapshot engine is covered automatically with no edit here.

   Report the `archived N file(s)` line in this run's summary. A `FileExistsError` means a same-dated archive copy already exists — that is a no-op for that file, not a failure; do not retry past it. If the script is missing or exits non-zero, note it and CONTINUE — retention is housekeeping and must never block the ledger run.
```

Replace `N` with the actual next step number in the live file.

- [ ] **Step 3: Verify the SKILL.md frontmatter survived**

Per `reference_update_scheduled_task_drops_frontmatter_keys.md`, a description retag drops sibling keys. This is a **body-only file edit**, so no `update_scheduled_task` call is needed or permitted. Confirm:

```bash
cd "C:/Users/Owner/.claude" && git diff -- scheduled-tasks/ora-pm-ledger/SKILL.md | head -40
```
Expected: additions only, none inside the `---` frontmatter block.

- [ ] **Step 4: Run the retention pass once, for real**

```bash
cd "C:/Users/Owner/.claude/scheduled-tasks/ora-pm-ledger" && python state_retention.py --keep-days 14
du -sb state/
```
Expected: `archived 12 file(s) ...`; `state/` shrinks by roughly the size of those 12 files (they move into `state/_archive/`, so the parent total is unchanged — measure `state/` excluding `_archive/` to see the effect).

- [ ] **Step 5: Commit**

```bash
git add scheduled-tasks/ora-pm-ledger/SKILL.md
git commit -m "fix(ora-pm-ledger): wire state_retention.py into the daily run

Automation Audit R21-9. The retention script was merged 2026-09-02 but
referenced by nothing -- zero invocations across scheduled-tasks/ and
maintenance/; it had been hand-run exactly once. state/ had grown to
36.28MB (+17% since Rev 19). Corrects the audit's own 'covers 3 of 5
categories' claim: plan() is category-agnostic and its dry-run lists all
five. Archives by move, per Invariant 6."
```

---

## W-D — Skill trigger collisions (R21-6, R21-7)

**Read this before editing anything.** Two traps:

1. **`automation-health-monitor` has two copies with different descriptions.** `~/ora-skills/automation-health-monitor/SKILL.md` (28,443B, v1.8) is what the **catalog** serves; `OneDrive\...\Documents\Claude\Scheduled\automation-health-monitor\SKILL.md` (105,437B) is what the **scheduled task executes**, and its description is entirely different text. Edit the **ora-skills** copy for routing. Do **not** touch the `Scheduled\` copy (memory: `reference_automation_health_monitor_repo_copy_is_not_live`).
2. **A description edit does not reach the catalog on commit.** These are `anthropic-skills:` (`@inline`) store skills. The routing change only takes effect after `anthropic-skills:package-and-stage-skill` repackages and **Gabriel clicks Save skill**. Plan the commit; flag the install as a Gabriel step.

### Task D1: Resolve the three-way "health check" collision

Three skills claim the literal phrase, with no CLAUDE.md line arbitrating any pair:
- `exception-detection/SKILL.md:4` — `"...flag issues, health check, scan for problems..."`
- `automation-health-monitor/SKILL.md:4` — `"Trigger phrases: automation health, task health, health check, scheduled task status..."`
- `desktop-commander:computer-health-check` (plugin, not editable here) — `"...'tune-up', 'checkup', 'system report', 'health check'"`

The plugin skill cannot be edited, so the ORA skills must yield the bare phrase. `exception-detection` is the one to lose it: it is an ORA *operations* exception scanner, and its body already delegates scheduled-task misses to `automation-health-monitor` (line 77). `automation-health-monitor` keeps a *qualified* form.

**Files:**
- Modify: `~/ora-skills/exception-detection/SKILL.md:4`
- Modify: `~/ora-skills/automation-health-monitor/SKILL.md:4`

- [ ] **Step 1: Claim the single-writer repo**

```bash
cd "C:/Users/Owner/ora-skills" && git log --oneline -1 && git status -sb
```
Expected HEAD `1c35a7e` (or newer with a known author). Only `?? tools/reimport_correlate.py` untracked. **If anything else is dirty, STOP.**

- [ ] **Step 2: Drop the bare phrase from `exception-detection`**

In the frontmatter `description`, replace:

```
Triggers: exception scan, anomaly detection, what's wrong, flag issues, health check, scan for problems, audit exceptions, find anomalies, red flags.
```

with:

```
Triggers: exception scan, anomaly detection, what's wrong, flag issues, portfolio health check, scan for problems, audit exceptions, find anomalies, red flags. NOT scheduled-task/automation health — that is automation-health-monitor.
```

Bump the version tag in the same description from `v1.4` to `v1.5`.

- [ ] **Step 3: Qualify the phrase in `automation-health-monitor`**

Replace:

```
Trigger phrases: automation health, task health, health check, scheduled task status, automation monitor, did my tasks run.
```

with:

```
Trigger phrases: automation health, task health, fleet health check, scheduled task status, automation monitor, did my tasks run. NOT portfolio/operations exceptions (exception-detection) and NOT this machine's hardware/OS health (desktop-commander:computer-health-check).
```

Bump `v1.8` → `v1.9` in the same description.

- [ ] **Step 4: Verify the bare phrase is gone from both**

```bash
cd "C:/Users/Owner/ora-skills" && grep -c "health check" exception-detection/SKILL.md automation-health-monitor/SKILL.md
python -c "
import re
for p in ['exception-detection/SKILL.md','automation-health-monitor/SKILL.md']:
    d=open(p,encoding='utf-8').read().split('---')[1]
    m=re.search(r'description:\s*(.*?)(?=\n[a-z_]+:|\Z)',d,re.S)
    s=' '.join(m.group(1).split())
    bare = re.search(r'(?<!portfolio )(?<!fleet )health check', s)
    print(p, 'BARE PHRASE PRESENT' if bare else 'clean')
"
```
Expected: both report `clean`.

- [ ] **Step 5: Add the tie-break to CLAUDE.md** — **BLAST RADIUS, needs Gabriel's sign-off**

Append to the `Exception scans:` line in the Skill tie-breaks section:

```
- Comms drafting: ... Exception scans: `exception-detection` (live Notion/HubSpot) · `portfolio-anomaly-scout` (file-export sweeps) · `automation-health-monitor` (scheduled-task fleet, not portfolio data).
```

Then verify the word budget did not cross the FAIL gate:

```bash
python ~/.claude/maintenance/doctrine-integrity-probe.py 2>&1 | grep -iE "word|FAIL|WARN"
```
Expected: word count **under 1,850**. Current 1,787 with 63 words of headroom; this clause is ~10 words. **If it would cross, do not trim inside the 1694–1755 band — relocate a rule instead** (`reference_claude_md_word_budget_is_a_floor.md`).

- [ ] **Step 6: Commit via the isolated-commit skill**

```bash
cd "C:/Users/Owner/ora-skills"
git add exception-detection/SKILL.md automation-health-monitor/SKILL.md
git commit -m "fix(skills): resolve three-way 'health check' trigger collision

Automation Audit R21-6. exception-detection, automation-health-monitor and
desktop-commander:computer-health-check all claimed the bare literal phrase
with no CLAUDE.md line arbitrating any pair. The plugin skill cannot be
edited, so the two ORA skills qualify theirs (portfolio / fleet). Bodies
unchanged; descriptions are what route."
```

- [ ] **Step 7: Hand off the install**

The catalog still serves the OLD descriptions until repackaged. Run `anthropic-skills:package-and-stage-skill` for both skills, then tell Gabriel which two `.skill` packages need a **Save skill** click. **This task is not complete on commit.**

### Task D2: Three low-severity overlaps

All three are `fix (low)`. Batch them into one commit — individually they are not worth a repackage cycle.

**Files:**
- Modify: `~/ora-skills/ora-millage-lookup/SKILL.md:4`, `~/ora-skills/pma-qc/SKILL.md:4`, `~/ora-skills/annual-cycle/SKILL.md:4`

- [ ] **Step 1: `ora-millage-lookup` — declare the `tax-appeal` boundary**

It already self-resolves against `acquisition-underwriting` but has **zero** reference to `tax-appeal` anywhere, while both claim "millage" and "assessed value". Append to its description:

```
Companion to tax-appeal: this skill PULLS a rate or assessed value; tax-appeal decides whether to CONTEST one. A request to challenge, appeal or reduce an assessment routes to tax-appeal.
```

- [ ] **Step 2: `pma-qc` — add the sibling-distinction line its two peers carry**

`lease-form-qc` and `listing-agreement-qc` both carry a "Distinct from…" clause in their *descriptions*; `pma-qc` carries it only in its body (lines 14-16), leaving `legal-intelligence`'s "uploads a PDF or DOCX that appears to be a lease, **contract**, PSA…" catch-all free to swallow a PMA. Append:

```
Distinct from legal-intelligence (general counterparty paper) and from listing-agreement-qc (broker listings): this is the SOLE path for a property management agreement where an ORA entity is Owner.
```

- [ ] **Step 3: `annual-cycle` — yield "annual report"**

`portfolio-reporting` is the reporting engine; `annual-cycle` is a calendar/close rhythm. Replace `annual report` in `annual-cycle`'s trigger list with `annual close calendar`, and append:

```
Investor-facing annual/portfolio REPORTS route to portfolio-reporting; this skill owns the year-end close rhythm, not the report artifact.
```

- [ ] **Step 4: Verify no bare collisions remain**

```bash
cd "C:/Users/Owner/ora-skills" && python -c "
import re,glob
def desc(p):
    d=open(p,encoding='utf-8').read().split('---')[1]
    m=re.search(r'description:\s*(.*?)(?=\n[a-z_]+:|\Z)',d,re.S)
    return ' '.join(m.group(1).split()).lower()
pairs=[('ora-millage-lookup','tax-appeal'),('annual-cycle','portfolio-reporting')]
for a,b in pairs:
    da,db=desc(a+'/SKILL.md'),desc(b+'/SKILL.md')
    print(a,'->',b,':','cross-referenced' if b in da or a in db else 'STILL UNARBITRATED')
print('pma-qc names legal-intelligence:', 'legal-intelligence' in desc('pma-qc/SKILL.md'))
print('annual-cycle still claims annual report:', 'annual report' in desc('annual-cycle/SKILL.md'))
"
```
Expected: both pairs `cross-referenced`; `pma-qc names legal-intelligence: True`; `annual-cycle still claims annual report: False`.

- [ ] **Step 5: Commit**

```bash
git add ora-millage-lookup/SKILL.md pma-qc/SKILL.md annual-cycle/SKILL.md
git commit -m "fix(skills): arbitrate three low-severity trigger overlaps

Automation Audit R21-7. millage/assessed-value (ora-millage-lookup vs
tax-appeal), PMA uploads (pma-qc vs legal-intelligence's contract
catch-all), and 'annual report' (annual-cycle vs portfolio-reporting).
Descriptions only; no body or procedure changed."
```

- [ ] **Step 6: Fold into D1's repackage batch** — same Save-skill handoff, five skills total.

---

## W-E — `ora-setup-audit` skill hardening (R21-11, R21-13, R21-14)

One commit, `v1.6` → `v1.7`. All three are doc/mechanism fixes to the skill that produced the audit.

### Task E1: Give Thread 4 verified inline paths (R21-13)

v1.6 already did exactly this for Thread 1 after Revision 18 guessed `hooks/` wrong. Thread 4 has the same defect: it names CLAUDE.md, MEMORY.md and `session-context.md` with **no paths**, and a live pass consequently looked for `session-context.md` under `maintenance/`.

- [ ] **Step 1: Add paths to the Thread 4 scope line**

In `~/ora-skills/ora-setup-audit/SKILL.md`, Scope item 4, replace the opening:

```
4. **Token-bloat sources** — CLAUDE.md word count vs. its WARN/FAIL gate, MEMORY.md size vs. its gate,
```

with:

```
4. **Token-bloat sources** — CLAUDE.md (`~/.claude/CLAUDE.md`) word count vs. its WARN 1700 / FAIL 1850 gate, counted ONLY by `~/.claude/maintenance/doctrine-integrity-probe.py` (NOT `~/.claude/hooks/`, and never bare `wc -w` — it undercounts by ~135 words, R17-3); MEMORY.md size vs. its 21,500B WARN / 24,400B HARD gate; `~/.claude/session-context.md` (the SessionStart-injected block — at the repo root, NOT under `maintenance/`, which holds only `session-context-xref-probe.py`) against its 40-line / 80-word-per-bullet caps,
```

### Task E2: Extend the cap to the finding sections (R21-11)

Step 4a caps "the masthead's stacked `rev-band` divs" and says nothing about the `<section>` blocks below — which measured **88,769B across 16 uncapped sections**, back to Revision 7, i.e. **52% of the artifact sits outside the cap written to bound it.**

- [ ] **Step 1: Add a section cap to Step 4a**

After the existing third bullet in Step 4a (line 46), add:

```markdown
   - **Section cap (added v1.7, closing R21-11).** The same bound applies to the per-finding `<section>` blocks below the masthead, which Step 4a's original wording did not cover — at Revision 21 they were 88,769B across 16 sections reaching back to Revision 7, 52% of the file and larger than the capped masthead. Keep at most **2 revisions' worth of finding sections inline**; move older ones, full markup and all, to `ora-automation-audit-history.md` under a `## Sections — Revision N` heading, and leave a single collapsed line in their place naming what moved and where. Sections that are not per-revision verdict tables — the standing reference sections (`Where the description payload sits`, `Not the problem`) — are exempt: they are current-state, not revision history.
   - **Do not add a new `<section>` for a revision whose findings already fit in its rev-band.** Revision 21 deliberately added none for exactly this reason; a revision that appends both a band and a section pays the cost twice.
```

### Task E3: Stop the working copy re-accumulating the frame runtime (R21-14)

The durable working copy is refreshed from `Artifact action:read`, whose saved bytes include the platform's frame-runtime preamble — `<!doctype>/<html>/<head>/<body>` plus ~34KB of minified JS. It had **two** nested copies (the published file had three), 18% of the file, re-added on every such refresh.

- [ ] **Step 1: Amend the durable-working-copy bullet**

Replace the tail of Step 4a's third bullet (line 46), from "If the working copy and the published artifact disagree" onward:

```markdown
If the working copy and the published artifact disagree (a prior session updated one without the other), the published artifact is authoritative — pull it into the working copy first, then apply this revision on top. **When you do, store ONLY the authored fragment — never a saved read verbatim (added v1.7, R21-14).** An `Artifact action:read` saves the platform's frame-runtime wrapper along with the content: `<!doctype html><html><head>` plus ~34KB of minified runtime JS, ending in a trailing `</body></html>`. That wrapper is re-added on every refresh and nests: at Revision 21 the working copy carried **two** of them (34,026B, 18% of the file) and the published copy three. Before saving, slice from the first `<title>` to the last `</div>` preceding the trailing `</body></html>`, and assert `content.count('<script') == 0` — the authored artifact contains no scripts, so any script tag means wrapper bytes survived. The publisher supplies its own skeleton, so the fragment is what it wants anyway.
```

- [ ] **Step 2: Add the changelog entry and bump the version**

Add above the v1.6 entry:

```markdown
- **v1.7 (2026-09-02): closed three defects the skill's own Revision 21 pass found in itself.** (1) **R21-13** — Thread 4 named CLAUDE.md, MEMORY.md and `session-context.md` with no paths, the same defect class v1.6 fixed for Thread 1 after Revision 18 guessed `hooks/` wrong; a live pass duly looked for `session-context.md` under `maintenance/` (it is at `~/.claude/session-context.md`) and for `doctrine-integrity-probe.py` under `hooks/` (it is under `maintenance/`). All now carry verified inline paths. (2) **R21-11** — Step 4a's cap was scoped verbatim to "the masthead's stacked `rev-band` divs" and never bounded the per-finding `<section>` blocks, which had grown to 88,769B across 16 sections reaching back to Revision 7: **52% of the artifact sat outside the cap written to bound it.** Added a 2-revision section cap with the same rollover, plus an explicit "don't pay twice" rule. (3) **R21-14** — the durable working copy silently accumulated the platform's frame-runtime wrapper on every `Artifact action:read` refresh, nesting to two copies (34,026B, 18%); Step 4a now requires storing only the authored fragment, with a `count('<script') == 0` assertion. Fourth time this skill has found its own output carrying the defect class it exists to detect (Rev 8 rev-log, Rev 10 stale mirror, Rev 21 wrapper + section cap).
```

Bump the frontmatter `description` version tag from `v1.6` to `v1.7`.

- [ ] **Step 3: Verify frontmatter parses and the mirror auto-syncs**

```bash
cd "C:/Users/Owner/ora-skills" && python -c "
import re
t=open('ora-setup-audit/SKILL.md',encoding='utf-8').read()
assert t.startswith('---'), 'frontmatter fence missing'
d=t.split('---')[1]
assert 'name: ora-setup-audit' in d
assert 'v1.7' in d, 'version tag not bumped'
print('frontmatter OK, v1.7')
"
```
Expected: `frontmatter OK, v1.7`

- [ ] **Step 4: Commit — the post-commit hook re-syncs the local mirror**

```bash
git add ora-setup-audit/SKILL.md
git commit -m "fix(ora-setup-audit): section cap, Thread-4 paths, working-copy rule (v1.7)

Automation Audit R21-11/R21-13/R21-14 -- three defects the skill's own
Revision 21 pass found in itself. Step 4a now bounds the finding sections
(52% of the artifact sat outside the cap written to bound it), Thread 4
carries verified inline paths, and the durable working copy must store the
authored fragment rather than a saved read (two nested frame-runtime
wrappers, 18% of the file)."
```

- [ ] **Step 5: Confirm the mirror synced**

`tools/sync_local_skills_mirror.py` runs from `tools/hooks/post-commit`.

```bash
diff "C:/Users/Owner/ora-skills/ora-setup-audit/SKILL.md" "C:/Users/Owner/.claude/skills/ora-setup-audit/SKILL.md" && echo "mirror in sync: PASS"
```
Expected: `mirror in sync: PASS`. If it differs, the post-commit hook did not fire — re-run it manually and file that as a regression against v1.5's structural fix.

- [ ] **Step 6: Apply the section cap to the live artifact**

The cap takes effect from Revision 22, but the 16 existing sections are already over it. Roll all but the two most recent revisions' sections to `ora-automation-audit-history.md` (append, never overwrite), leaving collapsed lines, then republish with `url:` and **do not omit it**. Confirm afterwards:

```bash
python -c "
s=open(r'C:\Users\Owner\.claude\artifacts\ora-automation-audit.html',encoding='utf-8').read()
print('sections:',s.count('<section'),'| scripts:',s.count('<script'),'| bytes:',len(s))
assert s.count('<script')==0
"
```
Expected: sections materially below 16, `scripts: 0`.

---

## W-F — Off-host outage detection (R21-4)

**This is an investigation, not an implementation.** Every monitor that could have caught the four-day outage is on the host that was down: `automation-health-monitor` and `ora-cowork-heartbeat` are fleet members, `ORA Fleet Dead-Man` is a local Windows task. The only genuinely off-host link is the GitHub Actions cron in `ZeOoba/ora-cowork-watchdog` — and **whether it alarmed during 08-29→09-01 is unverified**, because the repo is not cloned locally and Revision 21 ran unattended. Do not design a fix before answering that.

### Task F1: Determine whether the off-host watchdog fired

- [ ] **Step 1: Read the watchdog's actual run history**

```bash
gh run list --repo ZeOoba/ora-cowork-watchdog --limit 30 --json name,status,conclusion,createdAt
```
Expected: runs covering 2026-08-29 → 09-01. Record for each: did it run, and did it *alarm* on the missing heartbeat?

- [ ] **Step 2: Read the heartbeat contract**

```bash
gh api repos/ZeOoba/ora-cowork-watchdog/contents/.github/workflows --jq '.[].name'
```
Then read the workflow that consumes the Notion heartbeat page (`35c6ecd8`) and record its staleness threshold.

- [ ] **Step 3: Classify the outcome — this determines what, if anything, to build**

- **(a) It ran and alarmed** → the chain works; the gap is that the alarm went nowhere Gabriel saw. Fix is routing, not detection. Cheap.
- **(b) It ran and did not alarm** → its staleness threshold is longer than 4 days, or it reads a field the heartbeat stopped updating. Fix is a threshold/contract change in the workflow. Moderate.
- **(c) It did not run** → the dead-man chain is itself dead and has been silently so. This is the most serious outcome and supersedes R21-4's framing. Escalate to Gabriel before building anything.

- [ ] **Step 4: Report, do not build**

Write the finding into `event_log.md` via `append-event-log.py` and bring the classification back to Gabriel with a costed option per branch. **A four-day blind spot on a fleet that triggers money movement is a Gabriel-level design decision, not a subagent's call.**

---

## Execution order

W-A first — it is the only workstream that closes the finding with material consequences, and it is self-contained. W-F next, because its answer may change what else is worth building. W-B and W-C are independent and can run in parallel with anything. W-D and W-E both end in a repackage/Save-skill handoff, so batch them together to spend one install cycle instead of two.

```
W-A (A1 → A2 → A3 → A4)      ← start here
W-F (F1)                      ← investigation, blocks nothing but informs scope
W-B ∥ W-C                     ← independent, parallelisable
W-D ∥ W-E → single repackage → Gabriel's Save-skill clicks
```

## Self-review

**Spec coverage.** All 14 Revision 21 findings are in the coverage table; four are declared not code-fixable with the reason stated, two were already closed at Rev 21, eight map to tasks. No finding is unaccounted for.

**Placeholder scan.** Every code step carries real code. Two deliberate non-literals, both flagged inline: the step number `N` in W-C Step 2 (depends on the live file's current numbering) and the exact CLAUDE.md tie-break insertion point in W-D1 Step 5 (blast-radius file, needs the live line read at edit time).

**Type consistency.** `Invoke-LogRotation -Path/-MaxBytes/-Keep` is used identically in the tests, the helper and both call sites. `run(tasks, skips=None, now_iso=None)` and `pinned_task(...)` are defined in A1 before A2 uses them. `most_recent_expected_fire_utc(expr, now_local)` and `_local_utc_offset()` are consumed with the signatures read from `fleet-status.py:387` and `:367`.

**One correction carried into this plan:** Revision 21's "`state_retention.py` covers 3 of 5 categories" is refuted here with its own dry-run output. W-C fixes the two real defects and explicitly does not touch the non-defect.
