# ORA Ground-Truth Auditor — Design Spec

- **Date:** 2026-09-10
- **Author:** Claude Code (session 5271f2eb), for Gabriel Goldberg
- **Lane:** L3 (/build)
- **Status:** Approved design, pending implementation plan
- **Task id:** `ora-ground-truth-auditor`
- **Fleet:** CC/MCP (filesystem, git, transcripts, subagent dispatch)

## 1. Problem

The dual-fleet autonomous fleet (64 recurring tasks: 37 CC + 27 LAMS) has three
existing watchers, none of which answers the question this spec addresses:

| Existing | Question it answers |
|---|---|
| `automation-health-monitor` | Did the task run? |
| `ora-task-integrity-guard` | Is the task still registered and intact? |
| `cc-verifier-probe.py` | Do the end-states on disk match the expected table? |
| **(gap)** | **Was what the run said actually true?** |

Gabriel has observed runs make incorrect factual claims and propose flawed fixes.
Liveness monitoring cannot detect this class of failure: a run that emails a
confidently wrong number is, to every existing watcher, a healthy run.

## 2. Goal

A nightly auditor that re-derives every claim made by the previous 24h of scheduled
runs from primary sources, and reports on four axes: IDEMPOTENCY, CLAIM ACCURACY,
STALENESS, and FRESHNESS OF INPUTS.

### The absolute rule

**No verifier may treat a prior summary, log line, or finding as evidence.** Every
claim must be re-derived from a primary source: raw data files, lease documents, git
history, or the actual current contents of the Notion page. This is enforced
structurally (§6), not by instruction alone — an instruction not to trust a summary
is worth little when the summary is sitting in the context window.

## 3. Ground truth established during recon (2026-09-10)

These are verified facts about the substrate, not assumptions.

1. **Both registries carry per-task run records.** `lastRunAt`, `lastScheduledFor`,
   `enabled`, `cronExpression`, `filePath`.
   **`model` is NOT reliably present:** CC carries it on 20/38 tasks, LAMS on 1/29 —
   absent for ~69% of the fleet. LAMS additionally carries no `cwd` (0/29).
   Any mechanism keyed on the registry's `model` needs a fallback (§5 Stage 2).
   - CC: `%APPDATA%\Claude\claude-code-sessions\<a>\<b>\scheduled-tasks.json` — 38 tasks
   - LAMS: `%APPDATA%\Claude\local-agent-mode-sessions\<a>\<b>\scheduled-tasks.json` — 29 tasks
2. **`recordedSkips`** exists in both registries (29 CC / 10 LAMS) — a ledger of fires
   that did not happen. Feeds STALENESS.
3. **Session records:** 1,285 `local_<uuid>.json` (CC, measured 2026-09-10) and 501
   (LAMS). The CC figure is a **live monotonic counter** — it moved from 1,271 to
   1,285 during this recon. Recompute it at run time; never hard-code it. Each carries
   `sessionId`, `cliSessionId`, `createdAt`, `lastActivityAt`, and *sometimes* `model`.
4. **Transcripts — two different shapes, one per fleet.**
   - CC: transcripts are **spread across all 17 `~/.claude/projects/*` directories**,
     one per cwd — not confined to the OneDrive one. Task cwd alone does not explain
     that spread: the 38 CC tasks carry only **2 distinct cwd values** (37 OneDrive,
     1 `C:\Users\Owner`). Most of the other 15 dirs come from interactive and worktree
     sessions. The operative point is empirical, not causal: **Stage 0 must search
     every project dir**, because scoping to the OneDrive dir alone drops the join
     rate from 100/100 to 80/100 on the most recent 100 sessions (§3.5).
     The OneDrive dir specifically holds 519 top-level `.jsonl` and 1,536 recursive;
     the 1,017 difference sits in 182 immediate subdirectories (181 session-uuid dirs
     plus `memory`), 145 of which hold a `subagents/` dir — 769 `.jsonl` directly in
     those, and a further 248 in `subagents/` dirs nested deeper.
     **Stage 0 indexes top-level transcripts only**; subagent transcripts are evidence
     *within* a run, not runs in their own right.
   - LAMS: 501 transcripts, each at `<sessionId>/audit.jsonl` in the LAMS store.
     They are **all** named `audit.jsonl` — exactly one distinct basename.
     **`sessionId` already carries the `local_` prefix** (`local_<uuid>`, 501/501), so
     the path is `<sessionId>/audit.jsonl` and **never** `local_<sessionId>/...`, which
     would build `local_local_<uuid>` and match 0/501.
5. **The join therefore differs by fleet, and a single join implementation will fail.**
   - CC: `registry.task → local_*.json → cliSessionId → <cliSessionId>.jsonl`.
     **The rate is recency-dependent, and the corpus searched decides it.**
     Searching **all 17 project dirs** (what Stage 0 must do): 100/100 over the most
     recent 100 sessions, 200/200 over the most recent 200, and 552/1,285 = **43.0%**
     fleet-wide. Searching the OneDrive dir alone: 80/100, 180/200, 519/1,285 =
     **40.4%**. The gap is widest exactly where the auditor reads: 20 points at n=100,
     10 at n=200, 2.6 fleet-wide. Scoping too narrowly would trip any floor anchored on
     the all-dirs figure.
     Confirmed for the recent window the auditor normally reads — and *not* a
     property that survives an arbitrarily widened window. See §9 R1a.
     (1,285 is today's session-record count, not a constant — §3.3. Recompute the
     denominator at run time; never hard-code it.)
   - LAMS: `registry.task → <sessionId>/audit.jsonl`, keyed on `sessionId`
     (which already includes the `local_` prefix — do not re-add it), **not** on
     `cliSessionId`. A `<cliSessionId>.jsonl` lookup matches 0/501 on LAMS.
     **Confirmed, but by a different key** — Stage 0 implements both.
5a. **[SUPERSEDED IN PART, 2026-09-11 — read §3.5b before implementing against
   this. Its `notifySessionId` finding stands; its claim that no documented
   field exists, and the createdAt/title algorithm it proposed as the primary
   key, are FACTUALLY WRONG. Left in place, not rewritten, so the error is
   visible rather than laundered.]**

   **The unstated middle step — how a task's firing finds ITS session record —
   was never a documented field, and the obvious candidate is wrong.**
   `notifySessionId` on a task record looks like a per-run pointer and is not
   one: verified against 4 real tasks across both fleets (`automation-health-
   monitor`, `ora-doctrine-integrity-guard`, `ora-command-center-mirror-drift-
   check`, `ora-am-brief`), every `notifySessionId` record's `createdAt` sits
   months before the task's `lastRunAt` — it is a static "notify here" target
   fixed at registration/last-edit time, unrelated to any specific firing.

   **The real key, confirmed on the same 4 tasks: the session record's
   `createdAt` equals the task's `lastRunAt` to within ~1ms, and its `title` is
   `task_id.replace('-', ' ').capitalize()`** (`ora-doctrine-integrity-guard`
   → `"Ora doctrine integrity guard"`). Stage 0 finds the executing session by:

   1. scan `local_*.json` in the same registry directory for
      `abs(createdAt_ms - lastRunAt_ms) <= 2000`;
   2. among candidates, prefer `titleSource == "auto"` and
      `title == task_id.replace('-', ' ').capitalize()`;
   3. **more than one surviving candidate, or none at all, is UNJOINED** — never
      guess under ambiguity (a catch-up burst is exactly where two sessions can
      land inside one 2s window).

   Only once the session record is identified do §3.5's two per-fleet transcript
   lookups apply (CC: its `cliSessionId` → search all project dirs; LAMS: its own
   `sessionId` → `<sessionId>/audit.jsonl` next to the registry). This was found
   during plan-writing, after spec approval — corrected here rather than left
   for the implementer to rediscover or, worse, to silently join on
   `notifySessionId` and get a run-old, wrong transcript for every audited run.

5b. **CORRECTION (2026-09-11, found during final whole-branch adversarial
   review — NOT during original authoring): §3.5a's central claim was wrong.
   `scheduledTaskId` is a real, present field, it holds the executing task's
   id verbatim, and it is the correct PRIMARY join key.**

   Measured directly against the live stores on 2026-09-11 by dumping the full
   key list of every session record (not a cherry-picked field subset — that
   sampling error is exactly how §3.5a missed this):

   | store | session records | carrying `scheduledTaskId` | rate |
   |---|---|---|---|
   | CC (`claude-code-sessions`) | 1,288 | 753 | **58.5%** |
   | LAMS (`local-agent-mode-sessions`) | 501 | 301 | **60.1%** |
   | both | 1,789 | 1,054 | **58.9%** |

   The ~41% without it are ordinary interactive sessions, which have no task to
   name — the field is not "missing" from them, it is inapplicable. (Counts are
   today's, not constants — §3.3 applies here too; recompute at run time.)

   Two further measured facts, both load-bearing:

   - **The value is the task id verbatim**, so this is an exact-match key, not a
     similarity test. Records whose `scheduledTaskId` names a task absent from
     that fleet's registry — retired tasks, 72/753 CC and 38/301 LAMS — simply
     never match a live task, which is the correct outcome.
   - **`titleSource == "auto"` and `scheduledTaskId` are perfectly mutually
     exclusive.** On CC: 397 records are `titleSource: "auto"` and *none* of
     them carries a `scheduledTaskId`; all 753 that do carry one have
     `titleSource` null. On LAMS `titleSource` is absent from all 501 records.
     **§3.5a step 2's title-disambiguation branch is therefore unreachable for
     any session a scheduled task produced** — it could never have fired in
     production. The test fixtures written against §3.5a fabricated
     `titleSource: "auto"` onto scheduled-run records, which is why two review
     rounds passed the dead branch: they verified the fixtures, not reality.

   **Revised algorithm — `scheduledTaskId` primary, §3.5a's heuristic as
   fallback only:**

   1. **Primary.** Filter session records to `rec["scheduledTaskId"] ==
      task["id"]`. Exactly one → that IS the executing session; return it with
      no time or title check, because the id match already IS the
      disambiguation. More than one (the normal case — a daily task accumulates
      one record per firing, measured up to n=105) → tiebreak by whichever
      `createdAt` is nearest the task's `lastRunAt`. This is a choice among
      records *already proven* to belong to this task, not a guess across the
      whole population: measured across all 55 in-window tasks on both fleets,
      the winner sat **0–2 ms** from `lastRunAt` while the runner-up was never
      closer than **~82,000,000 ms (~23 h)** — unambiguous by seven orders of
      magnitude.
   2. **Fallback.** Zero records claim the task → fall back to §3.5a's
      createdAt-within-2s + auto-title heuristic, which remains correct and is
      the only key available for session records that never carry
      `scheduledTaskId` at all — ordinary interactive/non-scheduled sessions.
      This is NOT a "records that predate the field" claim: measured directly
      against both stores' createdAt ranges (2026-09-11 final review), records
      with and without `scheduledTaskId` are interleaved across the same date
      range in both fleets — field presence tracks session TYPE, not time.
      Every current task with a `lastRunAt` has at least one
      `scheduledTaskId`-carrying claimant, so this fallback is dead-but-correct
      defensive code on today's live data, not an active legacy path. Records
      that *do* carry some other task's `scheduledTaskId` are excluded
      from the fallback pool — they have already declared their owner, and
      admitting them lets the timing heuristic silently join another task's
      session that happens to land in the tolerance window. This exclusion is
      by field PRESENCE, not truthiness — a record with `scheduledTaskId: ""`
      or `null` has still declared an owner.
   3. Ambiguity in the fallback is still UNJOINED, never guessed.

   **Measured effect on the real join rate** (old primary vs. new primary,
   same corpus, 2026-09-11): over a 168 h window, CC **23/30 → 30/30** and
   LAMS **11/18 → 18/18**; over 720 h, CC **23/32 → 32/32** and LAMS
   **12/23 → 23/23**. The 24 h window held at 2/2 both ways (only two runs
   were in range under the standing fleet pause), so the nightly floor in §9
   R1a is unaffected — but the widened-window floors now have far more headroom
   than they were written against.

   This same field is what makes duplicate detection possible at all; see §5
   Stage 0's `same_cycle_refire`, rebuilt on it in the same correction.
6. **Scheduled-vs-actual drift is real and large.** `automation-health-monitor`
   (a **LAMS** task — its row carries no `cwd`, but it *does* carry
   `model: claude-sonnet-5`; it is precisely the 1/29 counted in §3.1) on
   2026-09-10 had `lastScheduledFor` 15:05Z but `lastRunAt` 17:13Z — a 2h08m lag,
   the documented consequence of the fleet firing only while the Desktop app is open.
   **Therefore `run_id` keys on `lastScheduledFor`, never `lastRunAt`** — otherwise
   every catch-up fire reads as a distinct logical cycle and idempotency detection
   collapses.
7. **Fleet state at time of writing:** both fleets are under a bounded pause
   (CC 1 of 38 enabled; LAMS 3 of 29). Resume tasks on both fleets fire
   2026-09-11 16:01 ET. The CC resume re-enables a **hardcoded 37-id list**.

## 4. Landing strategy (constrained by §3.7)

The task **will be** registered `enabled: false`, then appended as **item 38** to
`scheduled-tasks/ora-routine-pause-resume-2026-09-11/SKILL.md`. Neither has happened
yet — as of this writing `ora-ground-truth-auditor` is absent from both registries and
that SKILL.md still ends at item 37.

This follows the precedent that task's own SKILL.md documents: `ora-checkout-merge-forward`
was registered mid-pause, defaulted to `enabled: true`, was flipped back to false to
respect the standing pause, and was appended to the resume list as item 37 —
explicitly so it would not "sit silently paused forever with nothing pointing at it."

Consequence: the auditor comes online with the rest of the fleet at 16:01 ET on
2026-09-11, and **its first run audits the resume catch-up burst** — 63 tasks
re-enabled at once (37 CC + 26 LAMS) plus the 2 never-paused LAMS carve-outs.
(63 + 2 = 65 exceeds the 64 recurring tasks of §1 because one entry on the LAMS
resume list, `ora-counsel-review-standard-positions-2027`, is a one-time task with no
cron: 62 recurring re-enabled + 2 carve-outs = 64.) That burst is the single
richest idempotency target available.

## 5. Architecture

Five stages. Stages 0 and 1 are deterministic Python; only stage 2 spends agents.

### Stage 0 — Deterministic run index (no LLM)

`maintenance/ground-truth-run-index.py`, reusing the existing
`maintenance/_shared/store_discovery.py` for registry roots.

- Read both registries; select runs with `lastRunAt` inside the window.

**Window sizing is automatic, not manual.** Default 24h, but Stage 0 widens the window
to cover the full gap when either condition holds:

  1. a MEASURED gap since the previous auditor run exceeds 24h (last_auditor_run_at
     is not None and the gap is too large — e.g., the auditor itself was paused,
     or the host was closed), or
  2. the window contains a fleet-resume event — detected by a one-time
     `*-resume-*` / `*-pause-resume-*` task with `lastRunAt` in range.

A literal "never ran" (no prior auditor run at all, e.g., the auditor's very first
invocation) is recorded for visibility but does NOT by itself widen the window — there
is no measurable gap to widen by, and the realistic backfill scenario (registering the
auditor mid-pause) is already covered by condition 2's resume-event detection.

Rationale: a catch-up burst delivers many fires whose `lastScheduledFor` values are
*older* than 24h even though the fires themselves are minutes old. A fixed 24h window
keyed on `lastScheduledFor` would silently drop exactly the runs most likely to have
duplicated side effects. `--window-hours` remains available to override for ad-hoc
investigation. The digest always states the window actually used and why.
- Join to session record and transcript; emit `transcript: <path|null>`.
- Read `recordedSkips`.
- Emit `_state/ground-truth/run-index-<date>.json`, one record per run keyed
  `run_id = <fleet>:<task_id>:<lastScheduledFor>`.
- **Assert the per-fleet join-rate floor defined in §9 R1a** — a width-dependent
  floor, not a non-zero check — and carry joined/unjoined counts into the digest.

**Duplicate detection lives here, in Python, not in an agent.** An agent can be
reasoned out of a duplicate; a key comparison cannot. Stage 0 flags:

- two fires sharing one `lastScheduledFor` (re-fire of the same logical cycle)
- two distinct `lastScheduledFor` values falling inside one cron period
- **the same task id enabled on both fleets** — the known dual-fleet double-fire hazard
- any `fireAt`/cron collision among one-time and recurring slots

**CORRECTION (2026-09-11, same final-review pass as §3.5b).** The first two
bullets above, as originally implemented, compared **registry rows within a
single `build_run_index()` call** — and the registry keeps exactly **one row
per task id**, overwriting `lastRunAt`/`lastScheduledFor` on every fire.
Verified 2026-09-11: 38/38 CC and 29/29 LAMS task ids unique, zero
registry-level duplicates. One call therefore can never hold two rows for one
task, and both checks were **structurally dead code**. Restated honestly:

- `same_cycle_refire` is now keyed on §3.5b's `scheduledTaskId`, via
  `find_all_sessions_for_task(task, session_records, window_seconds=300)`:
  **two or more session records both stamped with the same `scheduledTaskId`
  and created near the same firing time is direct evidence of two executions**,
  which is the only place a duplicate fire is observable at all. The count is
  persisted per run as `candidate_session_count`, and the flag fires when it
  exceeds 1. (On the corpus as of 2026-09-11 no in-window task has more than
  one such record — the check is live and correct, and currently finds nothing,
  which is the intended reading of a clean fleet.)
- `cron_period_collision` is **DORMANT within a single invocation** and is
  documented as such rather than left as a silent no-op. It requires two
  distinct `lastScheduledFor` values for one task, which only a *sequence* of
  run-index documents across multiple invocations can supply. The comparison
  itself is correct and is kept ready for that input; it must **not** be
  "fixed" by re-deriving collisions from registry row counts.
- `cross_fleet_twin` is unaffected and was always correct per-invocation: each
  fleet's registry is a separate one-row-per-task source, so comparing the two
  enabled-id **sets** is a real comparison.

### Stage 1 — Side-effect extraction (no LLM)

Per run, derive *candidate* side effects.

- **Transcript present:** match a line-by-line regex against the transcript's
  RAW TEXT -- NOT a parsed/typed `tool_use` record -- for `send-via-outlook.ps1`
  invocations, `notion-create-pages` / `notion-update-page`, `git push`,
  `allocate-oi-id.py`, and file writes. This is a deliberate
  simplicity/robustness tradeoff: it matches whatever text a line contains, so
  it can never miss a real side effect, and its only failure direction is
  OVER-triggering (e.g. a transcript line that merely prints or reads text
  mentioning "git push" with no actual push). An over-trigger costs one extra
  verifier dispatch in Stage 2; it never lets a real side effect go
  unverified.
- **Transcript absent:** external enumeration only (§9 R1 fallback).

Runs with **zero** side effects receive a cheap deterministic stamp and **no agent**.
This is the approved cost gate: expected ~8–15 verifiers/night rather than 64.

### Stage 2 — Verifier dispatch (one agent per side-effecting run)

See §6 for the trust-enforcement mechanism.

**Model floor** per CLAUDE.md Dispatch: verifier model ≥ the audited run's own model
(reviewer ≥ implementer). Runs touching financial data, governor constants, or
confidential deals never verify below Fable. Every dispatch pins an explicit `model`.

**Resolving the audited run's model requires a ladder, not a field lookup.** The
registry's `model` is absent for ~69% of the fleet (§3.1), so Stage 2 resolves in order:

1. registry `model` field, when present;
2. the `[MODEL: <id> | set <date>]` tag in the task's SKILL.md frontmatter description;
3. the session record's `model`, when the run joined to one;
4. **failing all three, assume the highest tier** and verify at Fable.

Step 4 is deliberately fail-safe: an unknown model must never silently license a
*cheaper* verifier than the run it audits, which is the failure mode the
reviewer ≥ implementer invariant exists to prevent.

### Stage 3 — Four axes

Each verifier reports all four.

**IDEMPOTENCY.** Consumes Stage 0's deterministic flags, then checks the *actual
target* for doubles: two Notion pages for one logical cycle, two emails with the same
subject on one date, two commits with identical content. Cron/trigger double-fire
analysis belongs to Stage 0 and is inherited, not re-derived.

**CLAIM ACCURACY.** Enumerate every factual assertion **from the published artifact
re-read at its source** — the Notion page as it now reads, the message as it sits in
Sent Items — never from the transcript's account of what was published. Each claim is
marked `SUPPORTED` / `CONTRADICTED` / `UNVERIFIABLE` and must cite the primary source
that supports it (§6.2). `UNVERIFIABLE` is a first-class outcome, not a failure to
try: it means the primary source was unreachable, and it is reported as such rather
than silently upgraded to SUPPORTED.

**STALENESS.** For each plan item, pin, or config the run acted on, compare the state
at run time (git history gives this precisely) against current state. Flag work that
was a no-op and work that reverted a newer state. `recordedSkips` feeds this axis.

**FRESHNESS OF INPUTS.** For every upstream source, report last-updated timestamp and
whether a staleness alarm should have fired but did not. Canon: the ORA Master
Workbook mirror >7 days behind is STALE and must never be presented as current.

### Stage 4 — Morning digest

One HTML email to `ggoldberg@oxfordra.net` **only** (routing canon — no cc; the
ora-am-brief Eric cc exception does not extend here), via `_shared/send-via-outlook.ps1`.
Exit-code handling per canon: exit 2/4 retry once then flag loudly; exit 1/3 never retry.

Sections, in this order:

1. **Runs audited** — count, fleet split, side-effecting vs stamped, any skipped.
2. **CONTRADICTED claims** — highest priority, each with a drafted correction.
3. **Duplicate side effects** — with remediation steps.
4. **Open items filed** for systemic causes — ids allocated via
   `maintenance/allocate-oi-id.py`, never hand-computed as max+1.

Cron `0 4 * * *` (04:00 ET), ahead of `ora-am-brief` at 06:00 so the digest is
waiting before the brief.

**Self-exclusion:** the auditor omits its own run from its own index. Without this it
audits itself and trivially passes.

## 6. Enforcing "never trust a summary"

Three independent layers. Any one failing still leaves two.

### 6.1 Input starvation (primary defence)

The verifier prompt is assembled from the Stage 0/1 record and contains **only
primary-source locators**: Notion page id, message id, commit sha, file path, parcel
or lease identifier. It does **not** contain the run's summary, the body of what it
emailed, or any prior finding about it.

A verifier cannot be misled by a summary it is never shown. This is why the rule is
architectural rather than a line of prompt text.

### 6.2 F-id dossier discipline

Reuses the existing `evidence-dossier-drafting` skill. The verifier compiles numbered
facts (F-1, F-2, …), each bound to a source it opened itself. Every axis verdict must
cite at least one F-id. **A verdict with no F-id, or citing an F-id whose source does
not support it, is dropped before the digest.**

### 6.3 Adversarial refuter on CONTRADICTED

Every `CONTRADICTED` verdict goes to a second agent whose only job is to kill it —
re-reading the same primary source and arguing the original claim was right.
Contradictions that survive reach the digest; those that do not are downgraded and
logged.

Rationale: Gabriel's stated failure mode is runs making incorrect claims and proposing
flawed fixes. An auditor is a run. Applying that suspicion reflexively to the auditor
is the difference between reducing bad claims and relocating them.

## 7. Approval gate (Hard Invariant 1)

Any correction requiring a **retraction email** or an **edit to a published page** is:

1. drafted in full to `_state/ground-truth-pending-approval/<date>/<run_id>/`,
2. **named in the digest** with a one-line summary of what it would change,
3. **not sent and not applied.**

Nothing in this system sends external-counterparty communication or edits a published
artifact without Gabriel's explicit in-turn confirmation. The digest itself is an
internal scheduled send to ggoldberg@ only and is pre-authorized under the routing
canon carve-out.

## 8. Testing (Done Bar, L3)

TDD. Stages 0 and 1 are pure functions over registry/transcript fixtures and carry the
correctness burden, so they carry the tests.

Required fixtures:

- **catch-up burst** — many tasks, `lastRunAt` clustered, `lastScheduledFor` spread
- **same-cycle re-fire** — two fires, one `lastScheduledFor` → must flag
- **cross-fleet twin** — same id enabled on both registries → must flag
- **scheduled-vs-actual drift** — the real 2h08m AHM case from §3.6. Build against the
  **LAMS** row shape: no `cwd`, but `model` present (AHM is the one LAMS row that has
  it). A second fixture must cover the *typical* LAMS row, which has neither
- **transcript-absent run** → must degrade to external-only, never to "clean"
- **self-run present in window** → must be excluded

An adversarial REFUTE pass is mandatory before this ships: the auditor gates financial
and governor-touching output, which puts it in the class CLAUDE.md requires it for.

## 9. Risks resolved during build, not papered over

**R1 — RESOLVED during review; downgraded to an implementation requirement.** The
LAMS join is not missing, it is *differently shaped*: 501 transcripts, each at
`<sessionId>/audit.jsonl` — where `sessionId` already carries the `local_` prefix —
keyed on `sessionId` rather than `cliSessionId` (§3.5). A single CC-style join would have matched 0/501 and — worse — would have
looked like "LAMS runs produce no evidence" rather than "the lookup used the wrong
key." Stage 0 therefore implements **two** join strategies, one per fleet.

**R1a — the join rate decays with window width, and the widener makes that worse.**
CC `cliSessionId` resolution is 100% over the most recent 100–200 sessions but only
~43% fleet-wide (§3.5) — **both measured across all 17 project dirs**; a narrower
corpus reads ~20 points lower on the recent window and would false-alarm nightly. Stage 0's automatic window widening (§5 Stage 0) is precisely
the mechanism that pushes the audit into the older region where the join thins — the
architecture's own escape hatch erodes the fact it depends on. Two consequences,
both required:

- Stage 0 asserts a **join-rate floor that is a function of window width**, not a
  non-zero check. A ~50% join rate on a widened window is expected and must not
  alarm; the same rate on a 24h window means the join is broken and must.
- An unjoined run is `UNVERIFIABLE` and audited from external artifacts only. It is
  never `SUPPORTED`, and the digest reports joined vs unjoined counts per fleet so a
  silently decaying join surfaces as a trend rather than as an unexplained drop in
  findings.

**The hard gate survives regardless:** if a run cannot be joined to a transcript, it
is audited from external artifacts only (Notion, Sent Items, git) and **the digest
says so explicitly for that run**. Silent degradation to "clean" is the one outcome
that is unacceptable — an unjoinable run is `UNVERIFIABLE`, never `SUPPORTED`.

**R2 — Outlook Sent Items readability.** CLAIM ACCURACY on emailed output requires
re-reading the sent message. If Sent Items cannot be read for a given run, its emailed
claims are reported `UNVERIFIABLE`, never `SUPPORTED`.

**R3 — Cost drift.** The side-effect gate is what keeps this affordable. If a change
causes most runs to register side effects, verifier count approaches 64 and the job
becomes expensive. Stage 1 emits the gated/ungated counts into the digest so the trend
is visible rather than discovered on a bill.

**R4 — Registry single-writer.** Registration touches the dual-fleet registry.
Per doctrine: check `maintenance/_state/registry-membership.log` for concurrent
activity before registering, and register **only** via supervised
`create_scheduled_task` — never by splicing registry JSON.

## 10. Explicitly out of scope

- Auto-sending any correction or retraction (§7).
- Auto-editing any published Notion page or artifact (§7).
- Auditing non-fleet automation (Windows Task Scheduler, GitHub Actions crons) —
  `automation-health-monitor` already enumerates those.
- Replacing `automation-health-monitor` or `ora-task-integrity-guard`. This is
  additive; overlapping their liveness checks would repeat the mistake that got
  `ora-skill-cache-drift-alert` retired.
