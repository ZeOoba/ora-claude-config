# Insights Friction Remediation — OI-250 / 251 / 252 / 253

**Date:** 2026-09-10
**Lane:** L3 `/build`
**Branch:** `fix/insights-friction-remediation` off `origin/main` @ 422a414
**Worktree:** `.claude/worktrees/insights-friction-remediation`
**Claim:** `hooks-override-auth` (session 9ca9fdea)
**Origin:** `/insights` report 2026-09-10 ("Where Things Go Wrong") + Fable coverage verification

## Framing

The insights report prescribed building guards. Ground-truth verification found the
guards already exist. **Every gap is adoption or enforcement strength, not capability.**
Local lane telemetry (1,367 records, 07-24 → 09-08) corroborates:

| Signal | Rate |
|---|---|
| `verification_seen` | 94.1% |
| `lane_declared` | 56.7% |
| `bash_test_ran` | 51.9% |
| `task_dispatched` | **19.0%** |

Guards fire; adversaries are rarely dispatched. Only OI-252 changes that ratio, by
converting an advisory into a block.

**Explicitly out of scope** (verified already solved): staged-vs-reviewed enforcement —
`eos-review-gate.py:496-506` already hashes the index blob and blocks pre-commit for
risk paths. Notion/GitHub MCP — already wired / `gh` 2.96.0 authenticated. A
consolidated ship skill — exists across `isolated-commit` + `dirty-tree-triage`.

## Standing constraints

1. **Fleet is PAUSED.** All 38 CC tasks `enabled: false`; `ora-routine-pause-resume-2026-09-11`
   is armed to resume them. No work here flips an `enabled` flag. OI-250 should land
   before that resume or 22 unguarded side-effecting tasks return at once.
2. **Registry is never spliced.** OI-250 edits task-folder SKILL.md files only. Any
   registry mutation goes through supervised `create_scheduled_task` / `update_scheduled_task`.
3. **Reviewer >= implementer.** Implementation at Fable means the REFUTE pass runs at
   Fable or above.
4. **All guards fail open.** Consistent with every existing ORA guard. A guard must never
   become the reason the morning brief stops going out.
5. **TDD.** Failing test first, for every item.

---

## OI-252 — Branch-identity BLOCK (REVISED 2026-09-10 mid-build)

**Highest leverage. Do first.** The only item that moves `task_dispatched`, because it
converts a warning that is demonstrably read past into a stop.

### PLAN CORRECTION — two findings that invalidated the first draft

**(1) `commit-hygiene-guard.py` must NOT be made to block.** Its docstring records a
deliberate architectural invariant (`:42`): "warn-only, fail-open BY CONSTRUCTION.
permissionDecision is ALWAYS 'allow'", citing `feedback_confidentiality_guard_selfdeadlock.md`
where a fail-CLOSED guard bricked Write/Edit/Bash machine-wide. Decisively, `:70-73`
states its detection deliberately lacks "memory-orphan-link-guard.py's full adversarial
tearing defence" *because* it only prints — "this one only ever prints, so a crafted
command costs an advisory". Flipping `NEVER deny` would leave a blocking gate resting on
detection explicitly built for advisories. The branch check therefore moves to a NEW
purpose-built blocking guard.

`:82-87` ("this repo already tried blocking-by-syntax for git flags once and the lesson
held") does NOT forbid the new guard: that lesson is about blocking on git *flag syntax*
(`-a`, `add -A`), which fires on ordinary commands. This design keys on session *state*
plus a blast-radius path filter — structurally `commit-provenance-guard.py`'s
three-affirmative-signal model, which does block and has held since 07-16.

**(2) Empty-commit detection is DROPPED — git already enforces it.** Verified directly:
`git commit` with nothing staged => "nothing to commit, working tree clean";
`git add -- 'nope*.py'` => `fatal: pathspec 'nope*.py' did not match any files`.
The report's claim that a failed pathspec "silently produced a commit" is wrong on
*silently* — git errors loudly; the session proceeded past it. No PreToolUse hook can
catch that (the fatal occurs at execution), so it is replaced by a PostToolUse check.

### Current state
`hooks/commit-hygiene-guard.py:598-613, 700-706` computes destination branch, emits
"BRANCH CHANGED since your last commit", returns allow. Evidence it is read past: OI-247
(09-08, CLAUDE.md change bypassed its own worktree+PR process), and the live tree — HEAD
on `feat/model-canary-probe-step25`, 29 ahead / 84 behind `origin/main`, 77 dirty, 6
worktrees.

### Design

**A. `hooks/branch-identity-guard.py`** — new, blocking, fail-open by construction.
BLOCK only on THREE affirmative signals:
  (a) the commit candidate set contains a blast-radius path, AND
  (b) a session-branch record EXISTS for this session naming a DIFFERENT branch, AND
  (c) the destination branch resolves unambiguously (reuse commit-hygiene-guard's
      already-hardened `cd`/`git -C` resolution — do not reimplement).
Any missing, stale, or unreadable signal => "no information" => ALLOW. Never a lock.
Provenance recorded at `hooks/state/session-branch/<session_id>.json`; absent record =>
first commit of session => record and allow.

Blast-radius scope only (`hooks/**`, `*.env*`, `*credentials*`, `confidential-terms.json`,
`settings.json`, `CLAUDE.md`, scheduled-task registries, governor/financial constants). A
blanket branch block would fire on every ordinary commit and be overridden into
irrelevance within a day.

Override: existing token tier under `hooks/sessions/<id>/overrides/`. No new tier.

**B. PostToolUse pathspec-fatal check** — flag when a Bash `git add` returned
`fatal: pathspec ... did not match`. Advisory (PostToolUse cannot block), but it surfaces
the real failure at the only point it is observable.

### Tests (write first, all must fail)
1. `test_blocks_foreign_branch_with_blast_radius`
2. `test_allows_foreign_branch_without_blast_radius`
3. `test_allows_first_commit_of_session` (no state file)
4. `test_records_provenance_on_first_commit`
5. `test_allows_same_branch_subsequent_commit`
6. `test_corrupt_state_file_fails_open`
7. `test_unresolvable_branch_fails_open` (signal (c) absent)
8. `test_override_token_permits_blocked_branch`
9. `test_postuse_flags_pathspec_fatal`
10. `test_postuse_silent_on_successful_add`
11. Regression: existing `test-commit-hygiene-guard.py` (A1-E-n1) stays green and
    commit-hygiene-guard remains warn-only — assert `permissionDecision == "allow"`
    is still unconditional in that file.

Test 11 is the guarantee that this change did not erode the invariant it respected.

### Risk / rollback
Highest-blast-radius item — it can wedge commits. Mitigations: three-signal discipline,
narrow path scope, fail-open on any missing signal, existing override tier, no lock held.
Rollback = remove one dispatcher chain entry; the guard is a new additive file.

---

## OI-253 — Path-scoped heredoc / non-ASCII write guard

### Current state
Doctrine only. `rules.md §24` forbids multi-line heredocs; two feedback memories in 17
days (`feedback_commit_message_via_write_tool_not_heredoc.md` 08-21,
`feedback_bash_tool_heredoc_collapses_newlines.md` 09-07). Zero enforcement.
`config-write-guard.py:453-474` `_strip_heredoc_bodies` actively *excludes* heredoc bodies
from scanning — the opposite of blocking. No ASCII check exists anywhere
(`isascii`/`ord(c)` greps return zero).

### Design
New PreToolUse guard `hooks/heredoc-write-guard.py`, appended to the existing
`pretooluse-dispatcher.py --chain bash` chain (no new settings.json hook entry; one more
link in a chain that already runs 10).

**Check 1 — heredoc file write.** BLOCK a Bash command that writes file content via
heredoc (`<<EOF`, `<<'EOF'`, `<<-EOF`) or multi-line `echo`/`printf` redirection into a
tracked path. Message names the Write/Edit tool as the fix.

**Check 2 — non-ASCII, PATH-SCOPED.** BLOCK only for `hooks/**`, `maintenance/**`, and
`*.py`. This scoping is load-bearing and must not be widened: SKILL.md and memory prose
are legitimately dense with `— → " " ≥ ·`
(`reference_powershell_git_show_corrupts_nonascii.md`). A blanket ASCII gate would fight
the repo's own content and be overridden immediately.

Deliberately NOT blocking: heredocs that do not write files (`python - <<EOF`, `cat <<EOF`
into a pipe). Those are legitimate and frequent.

### Tests (write first)
1. `test_heredoc_write_to_tracked_path_blocked`
2. `test_heredoc_into_pipe_allowed` (no file write)
3. `test_python_stdin_heredoc_allowed`
4. `test_nonascii_blocked_in_hooks_path`
5. `test_nonascii_allowed_in_skill_md`  <- the scoping guarantee
6. `test_nonascii_allowed_in_memory_prose`
7. `test_multiline_echo_redirect_blocked`
8. `test_guard_fails_open_on_internal_error`
9. `test_scratchpad_path_exempt`

### Risk / rollback
Medium. False positives annoy rather than destroy; fail-open contract holds. Rollback =
remove one line from the dispatcher chain.

---

## OI-251 — Push wrapper (background + bounded poll)

### Current state
>=7 open items on one symptom: OI-168 (push killed at Bash 120s), OI-146 (3x exit-124),
OI-127/135, OI-119, OI-174, OI-057/059 reopened, OI-111. Root cause is pre-push gate
runtime exceeding the Bash tool's default timeout, not the push itself.
`maintenance/verify-push.py` (08-15) only diagnoses after the fact;
`git-prepush-hook-tests-gate.py:164` already carries `PER_TEST_TIMEOUT_SECONDS = 240`.

**Correction to the original recommendation:** the report prescribed PR-fallback on
branch-protection rejection. `gh api` shows `ora-claude-config` and `ora-skills` main are
**unprotected** (404); only `oxford-command-center` and Website enforce checks. PR-fallback
is therefore near-dead code for this repo and is descoped to a flag, not the default path.
The unprotected state of those two mains is a separate finding for Gabriel, not a fix here.

### Design
`maintenance/push-with-retry.py` — a wrapper, not a hook. Nothing is forced to use it;
`commands/ship.md` and `isolated-commit` are updated to call it.

- Launch `git push` detached; poll with bounded total budget (default 600s, `--timeout`).
- Distinguish **still-running** from **hung**: poll the child's own output, not wall clock
  alone (the flaky wall-clock lesson from the deterministic process-spawn fix).
- On success: invoke existing `verify-push.py` for the `ls-remote` truth check. Do not
  reimplement it.
- On protected-branch rejection (GH006 / `protected branch hook declined`): report and, with
  `--pr-on-reject`, open a PR via `gh`. Off by default.
- Exit codes distinct for: success, timeout, rejected-protected, rejected-other.

### Tests (write first)
1. `test_successful_push_returns_zero`
2. `test_timeout_returns_timeout_exit_code`
3. `test_protected_branch_rejection_detected` (GH006 fixture)
4. `test_pr_fallback_off_by_default`
5. `test_pr_fallback_invoked_with_flag`
6. `test_verify_push_invoked_on_success`
7. `test_no_wall_clock_assertion` — deterministic child-process proxy, not sleep timing
8. `test_non_protected_rejection_distinguished`

All subprocess-mocked. No test performs a real network push.

### Risk / rollback
Low — additive, opt-in, nothing depends on it until call sites are switched. Rollback =
stop calling it.

---

## OI-250 — block-sentinel `--period` fleet adoption

**Largest surface, highest consequence** (external email + Notion writes), but mechanical.

### Current state
`scheduled-tasks/_shared/block-sentinel.py` implements claim-then-complete with TTL,
exits 10/11/12, fail-open, and gained `--period day|week|month` on 2026-09-06 (`0ba45bc`)
specifically to stop period double-fires. **Adoption is 9 of 38 task folders.**

The task that actually caused the incident — `ora-entry-market-scan`, 11 duplicate Notion
rows + duplicate email on 09-07 (`event_log.md:390`) — is not among them; it carries a
bespoke outputs-directory check (`SKILL.md:21`, v1.7). `event_log.md:601` records 23 CC
tasks double-firing on the 09-02/09-05 clock shift; the `--period` fix landed the next day
and task adoption never followed.

### Scoping (this is the plan's main contribution)
Not all 38 need a guard. A read-only probe that double-fires is harmless. Retrofit only
tasks with a genuine external side effect (email / Notion write / git push):

**22 tasks need retrofit** — grouped by the `--period` their cron requires:

*period=day* (9): `ora-aaos-expire-leases`, `ora-aaos-publish-contracts`,
`ora-doctrine-integrity-guard`, `ora-pm-ledger`, `ora-task-integrity-guard`,
`ora-checkout-merge-forward`, `ora-command-center-mirror-drift-check` (1-5),
`ora-lease-snapshot-refresh` (1-5), `ora-sofr-direct-prefetch` (1-5)

*period=week* (10): `ora-appsec-sweep`, `ora-ar-feed-sweep`, `ora-cc-snapshot-refresh`,
`ora-deal-command-board`, `ora-deal-sourcing-scan`, `ora-entry-market-scan`,
`ora-financial-code-integrity-sweep`, `ora-master-workbook-ingest`,
`ora-model-release-watch`, `ora-site-exposure-probe`

*period=month* (3): `ora-broker-touch-cadence`, `ora-pm-monthly-billing`,
`ora-calibration-snapshot` (quarterly — month key is correct; it fires on the 1st of
Jan/Apr/Jul/Oct, so a month bucket can never collide across quarters)

**7 need no guard** (no external side effect): `ora-acquisition-underwriting-eval-harness`,
`ora-cc-schematic-refresh`, `ora-claude-setup-audit`, `ora-memory-commit-sweep`,
`ora-pm-daily-crons`, `ora-psa-drift-watch`, `ora-routine-pause-resume-2026-09-11`

**9 already guarded** — audit only, confirm each passes the correct `--period`:
`ora-am-brief`, `ora-health-guard`, `ora-open-sessions-board`, `ora-county-sales-monitor`
(monthly, 15th), `ora-deal-aging-sla`, `ora-monthly-portfolio-briefing`,
`ora-passed-deal-tracker` (monthly, 15th), `ora-tenant-hubspot-reconciliation` (monthly, 1st)

Note `ora-open-sessions-board` (Mon/Wed/Fri) and `ora-cc-schematic-refresh` (Mon/Thu) fire
multiple times per week — `period=day` is correct for those, not `week`.

### Design
Per task SKILL.md, insert as step 0 before any generation work:
- `claim` with `--task <id> --block main --run-id <id> --period <p>`
- exit 10 => report NORMAL skip (so health monitors do not read it as a miss)
- exit 11 => stand down
- `complete` after side effects succeed
- **side effects ordered last**, after all reads and validation, so a partial failure never
  leaves half-sent output

`ora-entry-market-scan`: replace the bespoke outputs-directory check with the shared
sentinel. Do not stack both.

### Tests
1. `test_second_invocation_same_period_is_noop` — parametrised across day/week/month
2. `test_week_period_does_not_rearm_next_day` — the exact 09-05 clock-shift bug
3. `test_month_period_does_not_rearm_next_day`
4. `test_quarterly_task_month_key_no_cross_quarter_collision`
5. `test_crashed_run_past_ttl_reclaims`
6. `test_sentinel_absent_fails_open`
7. Static conformance test over all 38 folders: every side-effecting task references
   block-sentinel with a `--period` matching its registry cron. **This is the regression
   that prevents adoption drifting back down** — it fails when a new side-effecting task
   is added without a guard.

Test 7 is the durable fix. Items 1-6 test the sentinel; 7 tests the fleet.

### Risk / rollback
Touches 22 task definitions while the fleet is paused — the safest possible window, and an
argument for landing before the 09-11 16:01 resume. Each edit is additive (a step 0 and a
completion call). Rollback = revert per task. No registry mutation, so no cross-fleet blast
radius.

---

## Execution order

1. **OI-252** — highest leverage, changes the dispatch ratio
2. **OI-253** — smallest, shares the dispatcher wiring touched in 252
3. **OI-251** — independent, additive
4. **OI-250** — largest surface; benefits from landing before the 09-11 resume

Each: failing tests -> implementation -> full suite -> Fable REFUTE pass -> stage ->
`git diff --cached --name-only` verify -> commit -> PR.

## Open decisions for Gabriel

1. `ora-claude-config` and `ora-skills` `main` are **unprotected** on GitHub. Deliberate or drift?
2. The 09-11 16:01 fleet resume — hold it until OI-250 lands, or let it fire and retrofit after?
3. OI-252's branch block is scoped to blast-radius paths. Widen to all commits, or keep narrow?
