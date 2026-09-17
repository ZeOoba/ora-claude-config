---
name: event_log
description: "ORA append-only event log — system changes, deal milestones, decisions. Newest first. This is the ONLY append-wall; living docs are overwritten to current state and point here for history."
metadata: 
  node_type: memory
  type: log
  originSessionId: 8ffab475-017d-4acd-9f70-f4496936d089
  modified: 2026-09-17T20:58:32.186Z
---

# ORA Event Log (append-only, newest first)

Renamed/expanded 2026-06-03 from reference_optimization_log.md. Living docs (firm/projects/tech/etc.) hold current state; their history accumulates HERE.

## 2026-09-17 — Both workflow optimizations implemented (83d07bc); live checkout fast-forwarded twice

Gabriel-directed, same turn: "fast-forward the live branch now then implement the following workflow optimizations".

**FF #1 (7027cc8):** the live checkout was 1 behind origin and still carried the UNFIXED `git_commit_parse.py`, so the live review gate could still fail open. Fast-forwarded under an `allow-config-write` token minted ONLY after Gabriel's explicit in-turn approval, then retired to `overrides/_used/`. Live gates verified 73/73 + 113/113 after.

**Knowledge item — directional assertions.** Swept `maintenance/_tests` + `hooks/tests` for assertions pinned to live-state counts: the orphaned-sections one (fixed earlier today in faf2c6b) was the ONLY real instance; everything else is fixture-based. Captured the rule durably as memory `feedback_directional_assertions_over_live_state.md` (+ MEMORY.md pointer): a test reading live state asserts a DIRECTION or invariant, never a snapshot count, because a hardcoded baseline inverts once the backlog it describes is cleaned up — and inside a push gate its staleness blocks every session, not just its author.

**Friction item — gates failing open (83d07bc, 4 files, 455 insertions).** Both gates returned SILENTLY when their guarded `hooks/lib` import failed. Now:
- `eos-review-gate` FAILS CLOSED on commit-shaped commands; non-commit calls pass with a loud warning; `EOS_REVIEW_GATE_MODE=off/warn` and the single-use token all still work, and the SAFETY INVARIANT docstring carries the carve-out.
- `commit-provenance-guard` still ALLOWS everything per the ratified 2026-07-17 ruling (blocking there would freeze commits fleet-wide on one broken lib file) but now says "UNGATED" instead of nothing.
- **The asymmetry is Gabriel's call.** The ask collided with that 2026-07-17 invariant, which is pinned by `test_broken_sibling_import_allows_...`; the options were put to him and he chose the split rather than letting me overturn a prior adversarial-review decision.
- Detector over-matches on purpose (inline, duplicated, NOT shared via hooks/lib — the premise is hooks/lib is unreachable). The repair command is not matched, so no bootstrap deadlock. A SECOND stricter pattern gates token spend only: a loose-only match blocks WITHOUT consuming the single-use token, closing a sharper form of the 2026-07-24 m7 waste.

**Independent review: 3 rounds, BLOCKED twice.** Round 2 caught four blocking defects incl. a block message telling the operator to mint a token the code never checked, and a docstring still promising the opposite behavior. Round 3 caught that the fixes were only in the WORKTREE while the index still held the defective version — decisive here because this gate hashes the INDEX blob, so the commit would have landed all four defects under a review keyed to other content. Artifact d5942ccf122d.

**Self-inflicted flake, fixed:** a new test fixture `copytree`'d all of `hooks/`, including `hooks/sessions/` which other live sessions write concurrently; it raced once. Narrowed to gate + `lib/*.py`.

**FF #2:** live checkout fast-forwarded to 83d07bc under a second single-purpose token (also retired); live suites now 82/82 + 62/62. Both worktrees (`gate-degraded-failclosed`, `hooks-git-lines-encoding`) removed and their temp branches deleted.

**Residual (non-blocking, recorded by the reviewer):** the loose detector still misses a commit whose `-C` argument contains a quoted `;` or `|`; `git commit-tree` strict-matches and would spend a token; `EOS_REVIEW_GATE_MODE=off` allows silently while degraded (consistent with the non-degraded path).

## 2026-09-17 -- acquisition-underwriting-eval-harness reimported (PR #65)

Packaged acquisition-underwriting-eval-harness from main @ e90f89d (squash-merge
of PR #65, "eval-harness: parse replay transcripts straight into aggregate/diff/record",
folding in 57c8992 and 1c7fe4e). plugin_of returned None (standalone skill).
tools/package_skills.py exited clean: description 682/1024 chars OK, 39 entries OK.
Staged to OneDrive Claude_Workspace/01_Workspace/outputs/2026-09-17_skill-staging/
acquisition-underwriting-eval-harness.skill and to the Cowork session outputs;
Gabriel confirmed the Save-skill click.

Verification: tools/reimport_correlate.py verify -> CONFIRMED (first install) --
cache directory CreationTime moved from ABSENT to 2026-09-17T15:40:59.987495,
main.log Local (%LOCALAPPDATA%\Claude\Logs\main.log) showed
"Sync complete: 1 downloaded" at 2026-09-17T15:41:00, an exact-second match.
verify_installed_cache.py: balanced=True, stray_body_quotes=0. Installed cache
dir file listing hand-checked against the 39-entry package manifest -- all
present, nothing missing.

Closing sweep: repo_first_check.py -> no cache-ahead skills; frontmatter_sweep.py
-> 0 findings across 70 skill dirs.

This is the Save-skill click being logged, not just the repo commit.

## 2026-09-17 — CONFIRMED Save-skill install of acquisition-underwriting-eval-harness (post-#65 merge), cache now matches origin/main

Gabriel clicked Save skill in Cowork at ~15:41 ET. Install proven first-hand, not inferred from the ledger.

- **Correlation (tools/reimport_correlate.py verify, ad-hoc `--baseline 2026-09-17 12:00:00` — no pre-click baseline had been captured, my omission in the handoff prompt):** `CONFIRMED -- CreationTime moved 2026-09-17T12:00:00 -> 2026-09-17T15:40:59.987495; main.log Sync complete: 1 downloaded @ 2026-09-17T15:41:00 (exact-second match)`. Both halves present: a real teardown/recreate of the cache dir AND the Local-log sync pair at the same second.
- **WHAT installed (hash, the "never WHETHER" check):** cache copy of `lib/parse_replays.py` is byte-identical to `origin/main` after newline normalization — normalized sha256 `15808e5d…` on both sides; the raw-hash gap was purely CRLF (398 CRLF lines in the packaged copy vs the LF git blob). Both post-review markers present (`PR #65 review, F1`, `REFUTE pass, R1`).
- **Net effect:** the Cowork runtime cache no longer runs the pre-fix parser. Before this, a Cowork-surface harness run would still have double-counted a duplicated `--agent-ids` value and silently swallowed a mistyped `--failed-agent-ids`; Code-surface runs read the repo and already had the fixes from `e90f89d`.
- `pending_reimport.py clear` REFUSED until this entry existed ("records no confirmed install in the newest event_log.md entry") — the gate worked as designed; the line is cleared in the same pass, after this.
- **Noted, not acted on:** the ledger carries 9 pending lines, including an OLDER 2026-09-12 entry for this same skill (commit 09d5f00, SKILL.md + golden_set + doctrine_skip_gate) and one for `acquisition-underwriting` itself. Today's confirmed install re-synced the whole skill package, so the older same-skill line is very likely stale too, but that is an inference, not evidence — it is left in place rather than cleared on a guess.

## 2026-09-17 — ora-skills PR #65 (eval-harness replay parser) reviewed, fixed twice, merged as e90f89d

Session 74d112a1, all steps Gabriel-approved in-turn. Chain: dirty-tree triage found the commit unpushed → push → PR → review → fixes → adversarial REFUTE → fixes → merge.

- **Origin:** `a45caa5` (authored 2026-09-13 in the eval-transcript-parser worktree) sat unpushed on this laptop for 4 days — found by the 09-17 worktree sweep, which kept it precisely because it was clean-but-unmerged. Pushed to the private `ZeOoba/ora-skills`, then opened as PR #65.
- **`/code-review` (high, this session): 7 findings**, all in `lib/parse_replays.py`. The three that mattered each corrupted `n` or the deal set with NO signal, which is the one thing this gate exists to get right: (F1) a `--failed-agent-ids` typo silently no-opped, leaving the replay the orchestrator rejected in the sample with the run still exiting CLEAN; (F2) a repeated `--agent-ids` value parsed one transcript twice as two independent samples; (F3) two goldens sharing a `deal_id` silently dropped a whole deal from the gate. Plus (F4) one malformed transcript aborted an 18-replay run with a traceback, (F5) entries lacking `requestId` split one response and failed good replays, (F6) the Step 1.5 flag erased the transcript's own error, (F7) the docstring contradicted SKILL.md Step 2. Fixed TDD in `1c7fe4e` (7 regression tests written first, watched fail).
- **Adversarial REFUTE pass on those fixes (Fable subagent): SOUND**, via a revert matrix (each fix reverted alone, matching test must fail), 11 constructed scenarios, a scan of 600 real transcripts / 29,048 assistant entries, and an old-vs-new re-parse of 41 real replays across 2 sessions with identical per-deal n/values/failures. **It caught a real error in my F4**: `_requests` still dereferenced raw content items, so the "non-dict blocks are skipped" claim did not hold and its test passed for the wrong reason. Also found (R1) the de-dup was bypassable by a case-differing id, since `Path.exists()` is case-insensitive on Windows (measured `replays=[14.0, 14.0]`), (R2) a duplicated id exited 0 CLEAN with a recorded snapshot, (R5) a golden-set defect escaped as a traceback outside the documented 0/3/4 contract. All four fixed TDD in `57c8992`.
- **Verification at merge:** parse_replays 45/45, full harness lib suite 137/137. No CI is configured on that repo and `main` is not branch-protected, so the adversarial pass WAS the gate — a bot check was never available to mistake for one.
- **Squash-merged** by Gabriel as `e90f89d` (19:30Z); fix markers verified present on `origin/main`. Because it was a squash, `57c8992` is not an ancestor of main — content parity was verified by grep, not by ancestry. The merged worktree was removed (clean); the branch ref is kept, no branches deleted.
- **Standing caveat, recorded deliberately:** every reviewer in this chain was this session or its subagent (review → own fixes → own subagent's refute), and the implementer ran at Opus 5 while the refute ran at Fable. Gabriel merged with that stated. The first real exercise is the next scheduled eval-harness run.
- **OPEN — Cowork reimport:** `_staging/PENDING_REIMPORT.md` still lists `acquisition-underwriting-eval-harness`. The runtime cache holds the PRE-FIX parser until a manual Save-skill click; packaging must come from merged `main` (the squash sha `e90f89d`, NOT the branch shas). Ledger is not an install oracle — confirm via main.log `Delta: N` + `Sync complete`, then `pending_reimport.py clear`.
- **Unrelated, noted not acted on:** local `ora-skills` main is 6 ahead / 1 behind origin/main (another session's forward-merge pattern).

## 2026-09-17 — Branch pushed (7027cc8); two unrelated blockers fixed, incl. a fail-OPEN review gate

Gabriel: "push the branch". `feat/model-canary-probe-step25` pushed at `fb97a42..7027cc8`, exit 0. Another session had already pushed a7d87ca + 0260e8e, so only aa24f15 was outstanding at the start.

**Blocker 1 — stale test baseline (faf2c6b).** Pre-push hook-tests gate failed 59/60 on `test_check_open_items_duplicate_ids.py`: the assertion hardcodes the orphaned-sections set, other sessions reconciled every one, and live is now `[]` (273 rows / 273 unique ids / 244 sections, no collisions). FIXING the backlog broke the test, and it blocked pushes for EVERY session. Baseline is now `set()`. Includes session 8a276a28's uncommitted 5-to-7 bump (09-13 11:10, four days idle, no claim) — superseded rather than dropped, credited in the message, Gabriel approved including it.

**Blocker 2 — `eos-review-gate` failing OPEN (7027cc8).** `test-eos-review-gate.py::test_index_realcase_path_survives_non_ascii_under_quotepath_false` failed. Real defect, reproduced twice independently: this branch's `git_lines()` used a bare `text=True`, so a non-UTF-8 byte in git stdout raised UnicodeDecodeError in subprocess's READER THREAD, which does not propagate — `subprocess.run` returned rc=0 with `stdout=None`, the `except Exception` caught nothing, and `None.splitlines()` raised AttributeError that unwound to the gate's top-level `except Exception: pass`. The whole gate aborted and exited 0 on a blast-radius commit.
- **First fix attempt was BLOCKED by independent review, correctly:** main ALREADY fixed this by making `git_lines` a thin adapter over `hooks/lib/git_probe_common.py::git()` — a file this branch did not have at all. A hand-written inline fix would have reinstated a duplicate wrapper a prior review removed, guaranteed a conflict in gate code, and left `eos-review-gate.py:411` + the test docstring asserting a delegation that did not exist. Landed as a verbatim 2-file sync from origin/main instead, per main's own LANDING NOTE that they never land split (a prior split cascaded 1 failure into 54).
- **Root cause of the split:** the branch is 159 behind main and `ora-checkout-merge-forward` has been blocked since 09-14 — the gate + its test had been synced down, the two lib files had not. Monday's STEP 1b addresses the same root cause.
- Done in an isolated worktree (`worktrees/hooks-git-lines-encoding`) because config-write-guard gates live `hooks/**`; NO override token minted, for either gate block, all session. `eos-review-gate` then blocked the commit itself for want of a review artifact keyed to the new content — dispatched a second opus reviewer (APPROVE; reproduced the failure from scratch, symbol diff zero removed/renamed), recorded via `--record --notes-file`, then committed.
- Verified: review-gate 73/73 · hook-tests 113/113 (was 112/1) · commit-provenance 59/59 · doctrine gate OK · both files byte-identical to origin/main.

**Gate flake noted, not acted on:** `allocate-oi-id` concurrency test failed 9/12 on the push's first gate run with `PermissionError(13)`, passed on the gate's own rerun. Known lock-contention flake; the gate's retry handled it.

**RESIDUAL (open):** the LIVE checkout is 1 commit behind origin and its `hooks/lib/git_commit_parse.py` is still the unfixed copy (`grep git_probe_common` = 0), so the live review gate can still fail open on a non-ASCII path until the live branch fast-forwards. Monday's STEP 1b merge-forward would fix it as a side effect; a deliberate FF needs a gated live write.

## 2026-09-17 — STEP 1b merge-forward unblock added to the 09-21 resume (aa24f15)

Gabriel approved in-turn after this session independently verified the dirty-tree-triage session's script (peer claims treated as data, re-derived here): `maintenance/merge-forward-unblock.py` landed 6c55134; `python -m pytest maintenance/_tests/test_merge_forward_unblock.py maintenance/_tests/test_scheduled_task_run_guard.py` = 12 passed; `--json --dry-run` against the live checkout returned `DRY_RUN / "all preconditions hold"`, exit 0, no writes. Chosen option: dry-run then real merge (not dry-run-only).

- **STEP 1b** (before STEP 2, so the merge runs while the fleet is still disabled): claim `sched-repo-housekeeping` -> dry-run -> real run with `--state-file _state/checkout-merge-forward-last-run.json` -> release -> status into the STEP 5 email. A non-MERGED result never stops the resume. Markers renumbered `--of 6`.
- **Third independent Opus review: APPROVE.** It confirmed from live state that the merge delta (158 commits) touches exactly ONE of the 9 catch-up prompts -- `ora-health-guard` -> main's reviewed v1.15 (PR #204), and 4d runs it last -- and cannot delete `pause_windows.py` (local-only, absent at merge base AND on main), `send-via-outlook.ps1`, or either `offhost-backup:` line (STEP 3's grep runs after 1b regardless). Applied its three non-blocking fixes verbatim: ERROR *does* write before rolling back (only REFUSED is "nothing touched"); a dry-run crash with no JSON also means STOP; `_rollback()` swallows `OSError` per file, so a true `rolled_back` must be confirmed on disk -- those 4 files are what the Monday Headless tasks execute.
- **Corrected a premise:** a MERGED outcome does NOT reset the Windows triggers. Triggers live in the Task Scheduler store, not the repo, and nothing re-runs `register-headless-checks.ps1` (whose main copy would re-register integrity-guard/stranded-spec DAILY and mirror-drift Mon-Fri).
- **Two gate blocks today, both correct, no token minted:** (1) `config-write-guard` on a read-shaped `git show` that carried a `2>&1` redirect and named the live checkout -- re-run without redirects; (2) the autonomy gate fired TWICE on the Anthropic co-author trailer address appearing in a Bash command's text (once in a commit-message heredoc, once in this very log entry), read as an external recipient. Workaround both times: write the file with the Write tool / avoid the literal address in command text, then run the command. Worth a matcher note: a git trailer is not a send.

## 2026-09-17 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `74d112a1-fd27-444f-9b89-6cc045340e00` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel confirmed in-turn 2026-09-17 ("push it again") for a SECOND fast-forward push of feat/model-canary-probe-step25 -- 5 commits (50cc8f7 event_log backlog, 0260e8e peer's catch-up spec, 6c55134 merge-forward-unblock + tests, 536a1df run-guard classification, fb97a42 gitignore backup fix), backup to ora-claude-config. Same two pre-existing BRANCH-STALE failures as this morning's push, re-verified just now and unrelated to the pushed content: (1) test-eos-review-gate.py -- abb2ef0 synced main's test without fix 4c5d441 and its new dependency hooks/lib/git_probe_common.py, which does not exist on this branch; passes 73/73 on origin/main. (2) test_check_open_items_duplicate_ids.py -- this branch's stale copy pins an orphan count against the live tracker; passes 60/60 on origin/main. Both resolve with the 09-21 merge-forward. The THIRD failure from this morning (test_scheduled_task_run_guard.py) is FIXED in 536a1df and that suite is green, so this override covers strictly less than the first one. Token deleted immediately after the push.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-09-17 13:57:06 local.

## 2026-09-17 — five-item triage follow-through: step25 pushed (override), merge-forward unblocker built TDD, gitignore backup gap closed, 30 worktrees + 9 stale claims pruned

Session 74d112a1, Gabriel-approved in-turn ("Proceed with all 5 in priority using superpowers"). Continues the same day's dirty-tree-triage entries.

**1. `feat/model-canary-probe-step25` PUSHED to `ora-claude-config`** (`abb2ef0..a7d87ca`, 66 commits; local == remote). The pre-push hook-test gate blocked first; all three failures were bisected in clean worktrees BEFORE any override was considered:
- `test-eos-review-gate.py` — fails at `eef4e18` AND `6fa8c8c`, passes 73/73 on origin/main. Root cause: `abb2ef0` synced main's test file onto this branch without its fix `4c5d441` (git_lines UTF-8 adapter) or that fix's new dependency `hooks/lib/git_probe_common.py`, which does not exist on this branch at all.
- `test_check_open_items_duplicate_ids.py` — fails at both commits, passes 60/60 on origin/main (this branch's stale copy pins an orphan count against the live tracker).
- `test_scheduled_task_run_guard.py` — PASSES at both commits, fails only in the live tree: the untracked `ora-routine-pause-resume-09-21` spec was unclassified.
Gabriel chose "override + push" on that evidence. `allow-hook-test-failure` minted with the bisect quoted, used once, deleted; the gate logged it (see the same-day override entry). Items 1–2 resolve with the 09-21 merge-forward; item 3 fixed below.

**2. Background tasks** (spawned 09-17): headless-task diagnosis and the scan_dirty_trees worktree-classification fix are both running in their own sessions.

**3. `maintenance/merge-forward-unblock.py` + tests — `6c55134`.** TDD: tests written first, watched fail (module absent), then 5 tests / 27 assertions ALL PASS, including a real-merge happy path and a rollback case. Two findings forced the design: (a) `git merge` refuses over an untracked file EVEN WHEN byte-identical to the incoming one (verified in a scratch repo, git 2.55.0.windows.2 — `verify_absent` never compares content), so "overwrite the drafts in place" is not an alternative; (b) three live Windows tasks execute the LOCAL `maintenance/headless/run-check.py`, so archive+merge must be one operation with a rollback. One python invocation by design: `git checkout --`/`mv`/`git show >` equivalents all trip `config-write-guard`. Refuses on a non-empty shared index (a live dry-run did exactly that against another session's staged file), an in-progress op, a failed fetch, a draft absent from origin/main, or a restore path differing beyond `--ignore-json-keys` (default `ts`). Never deletes; archives to `maintenance/_archive/<date>_merge-forward-unblock/`.
- **Cross-session coordination:** session f8735323 held the live claim on `ora-routine-pause-resume-09-21/SKILL.md` and commit `a7d87ca`/`0260e8e`, so THIS session never edited that spec. It will add the STEP 1b call itself and put it to Gabriel in its own session. It also reported that Monday's `fireAt` moved to 10:00 ET, 15 CC routines are now weekly (merge-forward exempt, still daily 16:45), and the 3 ORA Headless Windows tasks moved to Mondays (07:20 pair, 10:55 mirror-drift) — the ~10:00 unblock falls between them, and either outcome leaves `run-check.py` present.
- `536a1df` — classified `ora-routine-pause-resume-09-21` on the frozen `UNGUARDED_BACKLOG` (precedent: `ora-routine-pause-resume-2026-09-11`). Suite green again.

**4. `fb97a42` — `.gitignore` now tracks `scheduled-tasks/ora-pm-ledger/references/`.** Rule 2b's `/scheduled-tasks/*/*` ignored the 30KB `CHANGELOG-2026-07-08-to-2026-08-16.md` holding 13 dated NOTE sections extracted from the SKILL.md on 09-06: the citing spec was tracked, the cited text was in NO backup. Directory negation (a per-file `!` cannot reach inside an excluded directory); `state/` stays ignored and no other task folder is affected (`git check-ignore` verified).

**5. Pruned 30 worktrees, 0 branches deleted.** `~/.claude` 44→27 registered, `ora-pm` 21→8; branch counts 73 and 37 intact. Removal criteria re-verified per worktree at removal time: clean tree AND HEAD an ancestor of `origin/main`, no `--force` anywhere (git refuses a dirty worktree). `ora-skills` EXCLUDED — another session held `ora-skills-housekeeping`. Left alone: 8 dirty and ~19 unmerged worktrees. Also released 9 expired claims (ages 115h–859h, TTL 2h; no host session running) via `claim_work.py release --force`, which preserves an undo record — `active-work/` is now just the two live claims.

Tokens: `allow-config-write` and `allow-hook-test-failure` both minted with Gabriel's words quoted and both deleted; the guard re-blocked a later command, confirming they are off.

## 2026-09-17 — Monday 09-21 resume now runs 9 catch-up tasks (0260e8e)

Gabriel approved adding the four Monday-weekly tasks stranded by the 10:00 resume, then approved adding the five more that the same-day weekly retime stranded. New STEP 4 in `ora-routine-pause-resume-09-21/SKILL.md`, committed 0260e8e (local branch only; not pushed).

- **Order:** 4a master-workbook-ingest + pm-daily-crons + deal-aging-sla in parallel · 4b oxford-command-center writers strictly sequential (cc-snapshot-refresh -> lease-snapshot-refresh -> ar-feed-sweep, stop-on-failure, SKIPPED-CHAIN) · 4c deal-command-board · 4d task-integrity-guard -> health-guard last. Old STEP 4 report became STEP 5 with a catch-up table; markers `--of 5`.
- **Excluded on purpose:** `ora-aaos-expire-leases` (Mon 07:20) — the reviewer verified live that `ora-ops/locks/` holds no live lock files and `aaos-events.ndjson` has not been written since 2026-08-16, so the sweep is a guaranteed no-op. Ten tasks lost their pre-10:00 Monday slot; nine are caught up.
- **Independent Opus review (read-only, no context) returned BLOCK first:** (1) the message said nine stranded tasks when ten are; (2) the WAIT rule polled `list_task_runs(limit:1)` and would have read a PRIOR WEEK's `succeeded` row as this run finishing — which would have started `ora-lease-snapshot-refresh` while `ora-cc-snapshot-refresh` was still writing `data/snapshots/portfolio.json`, the exact collision 4b exists to prevent. Both fixed (the rule now anchors on the session_id `run_scheduled_task` returns), re-reviewed -> APPROVE. Also applied its non-blocking notes: aaos do-not-add line, attended window "typically 1-2h, up to ~5h worst case" (6 x 45-min caps), and a 4a Outlook-COM contention note that forbids re-running a task to force a send (an `ora-deal-aging-sla` re-run would duplicate drafts).
- **Registry untouched by design:** the commit changed only the SKILL.md at the registered filePath; fireAt 2026-09-21 10:00 ET + enabled were verified via `list_scheduled_tasks` when the move was made. A post-commit re-read was attempted and correctly BLOCKED by config-write-guard (read-shaped command naming the registry path); no override token minted.
- **Peer request (dirty-tree-triage session, NOT actioned):** asked for a STEP 1b calling `maintenance/merge-forward-unblock.py` to clear ora-checkout-merge-forward's BLOCKED_DIRTY_OVERLAP. Declined for now — the script does not exist yet, and a step calling a missing script would fail the attended run. Told them to send the commit sha; the step then needs `--of 6` markers and a STEP 5 (not 4) email reference, and goes to Gabriel in this session rather than riding on their approval. Warned them their 4 headless drafts are now load-bearing WEEKLY (Mon 07:20 pair, Mon 10:55 mirror-drift) and their ~10:00 unblock window sits between those runs.

## 2026-09-17 — event_log rollover + ora-skills worktree prune (7 removed, 1 kept); catch-up hook proven in production

**Rollover.** `maintenance/rollover-event-log.py` run alone (no competing claim on memory; last write was this session's own append): 2281 -> 612 live lines, 1673 archived to `memory/_archive/event_log_2026-09-17.md` (1677 lines incl. header). Live log was 410565 bytes, past the 400000 threshold.

**Worktree prune (ora-skills).** 10 worktrees; claimed `repo-housekeeping-ora-skills-worktrees` first (the standard `ora-skills-housekeeping` slug was held live by session ce23ff04 on disjoint paths -- `.github/workflows/tools-tests.yml`, `tools/test_pending_reimport.py`). All candidates verified clean (`git status --porcelain` empty), branch state confirmed against `gh pr list` rather than ancestry (every PR here is squash-merged, so `merged=false` is the norm and proves nothing), and idle by newest-file mtime. Ignored-but-real content (`_staging/` PENDING_REIMPORT ledgers + repo-first-rescue copies, one `.superpowers` review diff; 21 files, 409K) was copied to `_archive/2026-09-17_worktree-prune/<name>/` BEFORE removal per Hard Invariant 6 -- `git worktree remove` deletes ignored files with the directory.

REMOVED (7): `ora-skills-review-d5b1a43`, `ora-skills-review-main`, `_staging/worktree-dd0f26f` (all detached, HEAD contained in local main, idle 5-10 days); `offhost-backup-liveness` (#52 MERGED), `ora-skills-wp` (#56 MERGED), `ora-skills-wt-dtt-worktree` (#59 MERGED), `ora-skills-wt-oi283` (#51 MERGED). Branches left intact -- worktree removal does not delete them.

KEPT (1): `ora-skills-worktrees/eval-transcript-parser` (`feat/eval-harness-transcript-parser`) -- NO PR and 1 commit not on origin/main; unmerged work, not stale. NOT touched: `ora-skills-wt-ci-tools` (PR #63 open + written 3 min before the sweep + live claim) -- session ce23ff04 merged #63 and removed that worktree itself mid-sweep.

**Catch-up hook proven in production (unprompted, another session).** ce23ff04 merged #63 at 17:40Z; the PostToolUse entry added earlier today fired in THAT session and forward-merged it into local main as `0dea20c` with no human action -- the first real-world exercise of the automation built this morning. Local main is now `ahead 5`, `behind 0`.

**Note.** #63 (ci: run tools/test_*.py on every push) means ora-skills now has real CI on the tools suite -- the gap noted when #62 merged with only a rate-limited CodeRabbit check.

## 2026-09-17 — ora-skills local-main catch-up automated (repo-first false-alarm class closed)

**Problem.** Local `main` in `C:\Users\Owner\ora-skills` carries unpushed commits and never tracks `origin/main`, so every merged PR left it behind until someone hand-merged. Four times in four days (#55/#56, #57, #58/#59) `repo_first_check.py --all` reported skills installed from already-merged PRs as `!! REPO-FIRST DIVERGENT` — a false alarm the daily `ora-doctrine-integrity-guard` would email on. A fifth (#60/#61) was found and cleared while building this.

**Built (PR #62, squash 30f02af).**
- `tools/catch_up_main.py` — safe forward-merge of `origin/main` into local main. Merges only when: on `main`, `merge-tree --write-tree` dry run clean, no local tracked/untracked work overlapping incoming paths, `preflight-shared-checkout.py` CLEAR (absent gate = fail closed), HEAD unmoved. Fast-forwards when it can, else the established `merge origin/main into local main (forward-merge #N, #M)` commit. Never pushes. `--hook` mode serves a PostToolUse entry, acting only on `gh pr merge` aimed at ZeOoba/ora-skills (`-R/--repo` flag, else the cwd's origin remote).
- `tools/repo_first_check.py` — new non-alarm verdict `MAIN-BEHIND-ORIGIN` for cache content matching `HEAD..origin/main`, printed with a pointer to the tool; full sweep now does a best-effort non-interactive fetch first so a GitHub-web merge is recognized (without it, an unfetched merged PR read as CACHE-AHEAD — a second false-alarm shape).
- `~/.claude/settings.json` — one PostToolUse Bash entry (timeout 360) running `catch_up_main.py --hook`. Gabriel approved in-turn; `allow-config-write` token minted for that single edit and removed immediately after. **The settings.json edit is UNCOMMITTED** — the `.claude` checkout sits on another session's branch (`feat/model-canary-probe-step25`, 67 unpushed, 86 dirty), so it was deliberately not committed there; needs dirty-tree-triage.

**Review (local `/code-review` high, 2 findings, both fixed with regression tests written first).**
1. CONFIRMED: matching all of `origin/main`'s ancestry relabeled a cache-only file deleted by an already-merged PR as MAIN-BEHIND-ORIGIN even with local main fully caught up — masking a real REPO-MISSING that catch-up could never clear (reproduced in a scratch repo). Scoped to `HEAD..origin/main`.
2. PLAUSIBLE: unattended fetches could stall on a Git Credential Manager prompt; all git calls in both paths now set `GIT_TERMINAL_PROMPT=0` / `GCM_INTERACTIVE=never`.

**Verification.** All 12 `tools/test_*.py` green (repo_first_check 25, catch_up_main 15). Mutation checks: disabling the preflight guard or the overlap guard fails its own test. First live run forward-merged #60/#61/#62 into local main (`b33bdcb`). Hook verified live end-to-end (fired on a matching command, reported NOOP) without a session restart.

**Open follow-up.** `ora-doctrine-integrity-guard`'s SKILL.md still lists only IN-SYNC/REPO-AHEAD/NOT-INSTALLED as the normal verdicts; `MAIN-BEHIND-ORIGIN` prints without `!!` so STEP 3 does not alarm, but the doc should name it.

## 2026-09-17 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `74d112a1-fd27-444f-9b89-6cc045340e00` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel confirmed in-turn 2026-09-17 ("Override + push now") for ONE fast-forward push of feat/model-canary-probe-step25 (66 commits, backup to ora-claude-config). All 3 failures are pre-existing and unrelated to the pushed content, and were bisected in clean worktrees. (1) test-eos-review-gate.py fails at eef4e18 AND 6fa8c8c: abb2ef0 synced main's test without its fix 4c5d441 (git_commit_parse.git_lines UTF-8 adapter + new git_probe_common.py); passes 73/73 on origin/main. (2) test_check_open_items_duplicate_ids.py fails at eef4e18 AND 6fa8c8c (stale pinned orphan count vs the live tracker); passes 60/60 on origin/main. (3) test_scheduled_task_run_guard.py passes at both commits and fails only in the live tree (untracked ora-routine-pause-resume-09-21 spec unclassified). (1)+(2) resolve with the 09-21 merge-forward. Token deleted immediately after the push.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-09-17 13:34:19 local.

## 2026-09-17 — Fleet cadence capped at once/week (Gabriel-directed) + 09-21 resume moved to 10:00

**Authority:** Gabriel, in-turn: "all routines to run at most once per week". Scope, chosen by question: CC + LAMS routines + ORA Windows tasks. **Exceptions kept at current cadence:** `ora-am-brief` (daily), dead-man/watchdogs (`ora-cowork-heartbeat`, Fleet Dead-Man, Heartbeat Push, Pause-Resume Guard, Stuck-Session Watchdog, ClaudeFleetMirror), `ora-checkout-merge-forward` (daily), Command Center Mirror Deploy (hourly). `ora-pm-daily-crons` was deliberately NOT exempted.

**Resume:** `ora-routine-pause-resume-09-21` fireAt 05:00 → **2026-09-21 10:00 ET** (verified via `list_scheduled_tasks`; committed SKILL.md unchanged). Collision check: the Monday-weekly slots before 10:00 are lost (`ora-master-workbook-ingest` 05:45, `ora-cc-snapshot-refresh` 06:15, `ora-ar-feed-sweep` 08:20, `ora-deal-command-board` 09:50), so the next fire is 09-28. Workbook ingest would then reach 14 days, past the 7-day DSOR stale line. Recommended: `run_scheduled_task` those four right after the resume. The previous 05:00 fire would have stalled unattended anyway (v2.23).

**CC/MCP retimed (15, all still `enabled:false` under the pause; SKILL.mds byte-identical to pre-update snapshots; `offhost-backup:` intact):** health-guard `15 5 * * 1` · task-integrity-guard `5 7 * * 1` · lease-snapshot-refresh `40 7 * * 1` · deal-aging-sla `25 9 * * 1` · pm-daily-crons `40 9 * * 1` · sofr-direct-prefetch `10 10 * * 1` · command-center-mirror-drift-check `40 10 * * 1` · ground-truth-auditor `0 4 * * 2` · aaos-publish-contracts `15 9 * * 2` · acquisition-underwriting-eval-harness `14 12 * * 3` · doctrine-integrity-guard `55 12 * * 3` · cc-schematic-refresh `15 14 * * 4` · pm-ledger `0 15 * * 5` · open-sessions-board `0 17 * * 5` · memory-commit-sweep `0 19 * * 5`.

**⚠ Footgun found (tooling):** `update_scheduled_task` with `cronExpression` alone RE-ENABLED a paused task (`ora-memory-commit-sweep`, first test call). It was re-disabled within ~1 min; its next slot was Friday, so nothing fired. Every later call passed `enabled:false` in the same call. This belongs in register-scheduled-task's UPDATE section.

**Windows retimed (5; XML backups `maintenance/_state/task-xml-backup-2026-09-17-weekly/`):** Headless integrity-guard + stranded-spec → Mon 07:20 · Headless mirror-drift → Mon 10:55 · Mirror Deploy Classifier → Mon 10:40 · Nightly Disk Clean → Sun 04:00. Settings (SWA/battery) preserved. **Left daily on my call:** `ORA Claude Desktop Wake-and-Launch` (04:45). Both fleets fire only while Desktop is open, so weekly would break the kept daily `ora-am-brief` and heartbeat.

**LAMS (not writable from Code):** handoff brief `maintenance/_state/handoffs/2026-09-17_LAMS-weekly-cadence_brief.md` for a native on-device Cowork session: `automation-health-monitor` → `5 11 * * 1`, `ora-health-guard-fail-aging-nudge` → `0 9 * * 1`. NOT yet applied.

**Not in scope, unchanged:** GitHub Actions `ora-pm` `delinquency-backup.yml` stays daily, so late-fee posting (one per lease per month, idempotent) continues daily off-host. Only the critical-dates digest goes weekly.

**Known side effects (not addressed):** task descriptions still say "Daily"/"Weekday". pm-ledger's "daily close" now covers one day a week. ground-truth-auditor audits only the prior 24h (Monday's runs). health-guard's daily-brief fallback and missed-cycle checks run Mondays only. SOFR 180d/Index patch is weekly. Detectors with daily freshness thresholds (task-integrity-guard Step 2.95, the headless freshness check once registered, automation-health-monitor) may false-alarm. Re-running `register-headless-checks.ps1` resets the Windows tasks to DAILY. The pending headless catch-up verification moves to the Mon 09-21 07:20 slot.

## 2026-09-17 — 09-16 ora-am-brief miss: gap ACCEPTED (Gabriel decision)

- The 09-16 CC/MCP `ora-am-brief` was never produced. It was a phantom dispatch at 10:01:35, cleared stale at 10:16:35, and no email-fallback delivery exists for that day. Gabriel chose to accept the gap: no backfill, no send. A re-run could only produce today's data labelled 09-16, and 09-17's brief already reflects the current state.
- Open, not resolved by this: the Notion block-quota exhaustion (OI-281/OI-288) that forces the brief into email fallback.

## 2026-09-17 — Landed ora-routine-pause-resume-09-21 spec (a7d87ca, local only)

- Committed the untracked `scheduled-tasks/ora-routine-pause-resume-09-21/SKILL.md` **as-is**, with Gabriel's in-turn approval, via isolated-commit. Pathspec-only stage. The committed blob is byte-identical to the working file (sha256 06b4a141…7819, LF in both). Claim taken and released. An independent Opus reviewer returned APPROVE and re-derived every message claim.
- Author session not attributable: no touched-files entry lists the path. Registry `createdAt` 09-14 14:38:34.803 matches the file mtime, so the registration tool wrote it.
- **Not pushed:** `feat/model-canary-probe-step25` is now 67 ahead / 0 behind its upstream. The other 66 commits are other sessions' work, and publishing them is a separate decision.
- **Risk surfaced by review (open):** the task is ATTENDED, since every `update_scheduled_task` call needs Desktop approval, but it fires 09-21 05:00. Unwatched, it will likely stall at STEP 2 and the 37 CC tasks stay paused, including `ora-checkout-merge-forward`, which the 09-21 headless-drafts archive → merge sequence depends on.
- Non-blocking spec nits (not edited): description cites register-scheduled-task v2.23 but the body says v2.24; the progress marker says 4 steps over a 5-step flow (STEP 1 exclusions writes no marker); the "N/37" denominator is fixed even if an id is excluded (pending list is empty today).

## 2026-09-17 — oxford-command-center local main realigned to origin/main (5040518); redundant 85dfecf kept on a backup branch

Session 74d112a1, Gabriel-approved in-turn ("pull oxford-command-center up to origin/main").

- **Before:** local `main` at `85dfecf` (09-09 "Auto-refresh: snapshot sync", local-only on main), 1 ahead / 28 behind origin/main. A `git merge-tree` dry run showed a content conflict in `data/snapshots/portfolio.json`.
- **Evidence the local commit was redundant:** `85dfecf` is already on `origin/feat/write-schema-drift-check`, which squash-merged as `5040518` (#329). Its `data/ar-mapping-cache.json` and `data/ar/review-queue.json` blobs are identical to origin/main's. Its `portfolio.json` differs from origin/main (`32702df`, #321) only in `meta.generatedAt` and `quickbooks.parsedAt`: the same asOf 2026-09-06 snapshot regenerated ~80 min later, with no data difference.
- **Action:** created branch `backup/main-85dfecf-2026-09-17` at `85dfecf`, then `git reset --keep origin/main` (clean tree verified first; no merge commit, nothing pushed). Result: `main...origin/main` level, 0 dirty, HEAD `5040518`.
- **Upstream delta pulled in:** 28 commits / 75 files (+6658/−477), including #327 appsec CSRF, #328 OI-090 rate-limit follow-up, #329 write-schema drift check (adds `check:schema-drift` to `npm run gate`). `package.json` changed scripts only (no dependency change, no `npm install` needed); no `server/warehouse/migrations` changes. `npm run gate` was not run locally; origin/main is the CI-merged state.
- **Unaffected:** all OCC worktrees (feat/lease-market-intel, which is live session 5e58f532's, plus fix/m365-refute-fixes, fix/ar-matching-refute, agent/detached worktrees) and `oxford-command-center-deploy-build` (detached at 5040518). No OCC dev server process was running.
- **Rollback:** `git -C C:/Users/Owner/oxford-command-center reset --keep backup/main-85dfecf-2026-09-17`.

## 2026-09-17 — Headless integrity-guard + stranded-spec first-ever runs (manual, Gabriel-requested): launch path proven, 2 real findings

**Run:** `Start-ScheduledTask` at 11:56:43 on both tasks, not a direct python call, so the real launch path was tested. Events 325/110/129/100/200/201/102 fired for both, finishing in 17–20s. LastTaskResult=1 for both, which is the FINDINGS exit per the e39bc29 contract. `logs/integrity-guard.log` and `logs/stranded-spec.log` exist for the first time. Both paged ggoldberg via Outlook COM (internal routing canon). Separately, `ORA Stuck-Session Watchdog` at 11:35:01 on AC launched normally with result 0x0, the first post-fix scheduled launch. Catch-up after a missed slot while on battery is still unproven until the 09-18 wake.

**Finding 1 (integrity-guard, HIGH):** phantom dispatch of CC/MCP `ora-am-brief` at 09-16 10:01:35, cleared stale at 10:16:35 after 900s pending. Corroborated in Outlook: ora-am-brief email-fallback deliveries exist for 09-15 (10:53) and 09-17 (10:43), but none for 09-16. The only 09-16 "Daily Brief" mail is the separate `[ORA Command Center] Daily Brief`. Notion was not checked; the 09-15 and 09-17 runs both fell back to email because of block-quota exhaustion (OI-281/OI-288). So the 09-16 AM brief was most likely never produced. Oddity: the wrapper reports HIGH while the underlying probe block prints `VERDICT: OK`.

**Finding 2 (stranded-spec, HIGH):** `scheduled-tasks/ora-routine-pause-resume-09-21/` (SKILL.md written 09-14 14:38) is registered in CC/MCP but **untracked** in `~/.claude` git (`??`), so the bytes the scheduler will run on 09-21 exist in no commit. The probe's "differs from HEAD" wording is imprecise; it is untracked, not modified. LAMS reconciles clean.

## 2026-09-17 — dirty-tree triage: oxford-command-center working tree cleaned (archive + restore, no commits)

Session 74d112a1, Gabriel-approved in-turn ("clean up oxford-command-center too"). HEAD `85dfecf` unchanged; working tree now clean.

- **`fix3files.patch`** (untracked, repo root, 09-11 16:41, no recorded owner): a UTF-16 PowerShell-redirect diff over `server/brain.ts`, `tests/unit/brain.test.ts` and `tests/unit/warehouse-reconcile-noi.test.ts` that applies neither forward nor in reverse against HEAD, so it is stale. Moved to `data/_backup/dirty-tree-triage-2026-09-17/fix3files.utf16.2026-09-11.patch`.
- **`data/ar-mapping-cache.json`** (tracked durable name→lease rulings): the local diff was the `savedAt` stamp only (09-07 → 09-14), with no mapping change, and upstream also changed the file, so it would block a pull. Byte-verified copy saved as `data/_backup/dirty-tree-triage-2026-09-17/ar-mapping-cache.local-savedAt-2026-09-14.json`, then restored to HEAD. Its sole writer (`scripts/ar-import-headless.ts` via `ora-ar-feed-sweep`) is paused until 09-21.
- `data/_backup/` is gitignored (existing archive convention, PR #309). Preflight returned CONTESTED on non-self dirty files with no live owner and no competing claims; proceeded on the in-turn instruction. `repo-housekeeping` claimed and released.
- **Not touched:** branch divergence (local `main` 1 ahead / 28 behind origin/main); the local-only commit is `85dfecf`, the 09-09 triage snapshot sync. A pull/merge is Gabriel's call.

## 2026-09-17 — APPLIED: catch-up + battery-condition fix on 4 Windows tasks (Gabriel approved in-turn)

Follow-up to the same-day "ORA Headless ... have NEVER executed" entry. Gabriel approved the fix and asked for it to cover `ORA Stuck-Session Watchdog` as well.

**Change:** at 11:10 EDT, in-place `Set-ScheduledTask -Settings` on `ORA Headless - integrity-guard`, `- stranded-spec`, `- mirror-drift` and `ORA Stuck-Session Watchdog`: StartWhenAvailable false→true, DisallowStartIfOnBatteries true→false, StopIfGoingOnBatteries true→false. Nothing else was changed. Before/after XML diff shows exactly those 3 lines per task; triggers, actions and principal (InteractiveToken) are unchanged, and the untracked `maintenance/headless/*` files were not touched. Pre-flight: `registry-membership.log` showed no concurrent activity (last write 09-14).

**Rollback:** `Register-ScheduledTask -TaskName "<name>" -Xml (Get-Content -Raw <backup>) -Force` using `maintenance/_state/task-xml-backup-2026-09-17/*.xml` (pre-change exports).

**Still to verify:** (1) Stuck-Session Watchdog next run 09-17 11:35 should launch (event 100/200) rather than refuse 0x800710E0. (2) At the first wake after the 09-18 07:20 slot, integrity-guard/stranded-spec should log event 100/129/200 instead of 153, and `headless/logs/integrity-guard.log` + `stranded-spec.log` should appear. Until then the fix is applied but unproven.

**Durable follow-up (open):** after the 09-21 merge-forward, PR on main so `register-headless-checks.ps1` sets these flags. Otherwise re-running it resets them to the `schtasks /Create` defaults. Also stagger the freshness (07:50) catch-up behind the 07:20 pair.

## 2026-09-17 — ORA Headless integrity-guard + stranded-spec have NEVER executed (missed-schedule refusal, not a code bug)

**Symptom:** `ORA Headless - integrity-guard` / `- stranded-spec` did not fire at 07:20 on 09-17; LastTaskResult 0x800710E0 (ERROR_REQUEST_REFUSED). `mirror-drift` (10:55 weekdays) runs.

**Evidence (live, 09-17):**
- TaskScheduler/Operational: event **153** "did not launch ... as it missed its schedule" for both tasks at 09-15 10:41:54, 09-16 10:18:20, 09-17 10:36:34 (log retention starts 09-14 10:27). No 100/129/200 launch events ever. The 0x800710E0 + LastRunTime stamps are the *wake-time refusal*, not a run.
- `maintenance/headless/logs/` holds ONLY `mirror-drift.log`; the `cmd /c ... >> <check>.log` redirect creates the file on launch, so neither check has run once since registration on 09-10, including 09-11..09-13 (the dates before log retention starts).
- Power at every 07:20 slot, 09-11..09-17: machine in Modern Standby (lid closed) or hibernated. 09-17: Modern Standby on DC from 09-16 20:30, hibernate 04:32:44 (standby battery budget exceeded), wake 10:30:36, AC on 10:30:35. AC was off at 07:20 on every day except 09-13 (AC on, but lid-closed standby).
- Task XML (all three): `StartWhenAvailable` absent (=false), `DisallowStartIfOnBatteries=true`, `StopIfGoingOnBatteries=true`, WakeToRun false, InteractiveToken. These are `schtasks.exe /Create` defaults; `register-headless-checks.ps1` passes no settings. The other out-of-band ORA guards (Dead-Man, Pause-Resume Guard, Wake-and-Launch, Mirror Deploy) all have SWA=True, NoBatt=False.
- mirror-drift only "works" because the laptop is usually awake and on AC by 10:55.

**Root cause:** a scheduling-substrate config defect (tooling/environment class). A daily 07:20 trigger with no catch-up on a laptop that is never awake at 07:20: the missed slot is dropped (153) on wake. The battery conditions would also refuse any DC-power catch-up run. This defeats the design goal in e39bc29, which was to fire when the Desktop app is shut.

**Not fixed by merge-forward:** origin/main e39bc29 `register-headless-checks.ps1` has the same `schtasks` call without settings. It also adds `ORA Headless - freshness` (07:50), which is not registered live.

**Sibling with the same defect:** `ORA Stuck-Session Watchdog` (SWA=False, NoBatt=True, last result 0x800710E0).

**Proposed minimal fix (NOT applied, awaiting Gabriel approval):** in-place `Set-ScheduledTask -Settings` on the 3 headless tasks: StartWhenAvailable=true, DisallowStartIfOnBatteries=false, StopIfGoingOnBatteries=false. Trigger, action and principal stay unchanged, and the untracked local files are not touched. The durable follow-up after 09-21 merge-forward is a PR on main so the register script sets these flags (Register-ScheduledTask + New-ScheduledTaskSettingsSet, or Set-ScheduledTask after schtasks). Catch-up ordering matters then: freshness (07:50) would catch up in the same wake burst as the 07:20 pair and could false-page on staleness.

**Also observed (separate issue):** mirror-drift rc=1 on 09-15 and 09-17. This is working as designed: it paged `ALARM_UNEXPLAINED_KILL` on `ORA Command Center - Mirror Deploy` (rc 0xC000013A, run 10:36:34, ended 10:41:08; local main 1 ahead / 28 behind origin).

## 2026-09-17 — dirty-tree triage: 49 settled files landed on the primary ~/.claude checkout (5 isolated commits)

Session 74d112a1, Gabriel-approved in-turn ("commit the 50 settled files"). The approved count was a miscount: the set is 49. The 50th was the `ora-754` archive move, which was listed separately and not approved, so it stays uncommitted. Follows the report-only entry of the same date.

- **Commits** on `feat/model-canary-probe-step25` (local only, not pushed; branch now 66 ahead of its upstream, 99 ahead / 158 behind origin/main):
  - `7525b67` 34 `_scheduled_tasks_backup/*` spec mirrors
  - `82dbb86` live specs `ora-acquisition-underwriting-eval-harness`, `ora-entry-market-scan`, `ora-pm-ledger`
  - `000f3a5` 6 `skills/*` files (county-parcel-screen + 2 refs, county-sales-monitor, ora-setup-audit v1.12, security-and-hardening)
  - `9221b25` `spec-liveness-probe.py` + test (suite run first: ALL PASS)
  - `6fa8c8c` `system-inventory.md`, `deal-stage-snapshot.json`, `health-guard-beacon.json`, `reference_notion_free_block_quota_exhausted_2026-09-12.md`
- **Selection:** modified-tracked files untouched on origin/main since merge-base, mtime-settled across 09-16 16:50 → 09-17 (re-verified immediately before commit), excluding the live-session file `INDEX_reference.md` (5e58f532). Index empty and no MERGE_HEAD verified before each commit; each commit's path list asserted equal to its group file.
- **Preflight:** `preflight-shared-checkout.py` returned CONTESTED because every path is non-self dirty WIP (inherent to triage). Recorded owners' last activity was 09-14 15:30 or earlier, against a 6h TTL; no competing claims; HEAD unchanged. Proceeded on Gabriel's explicit in-turn instruction after full attribution disclosure. `repo-housekeeping` claimed and released; `allow-config-write` token minted with the approval quoted and deleted immediately after.
- **Still dirty (tracked), intentionally:** `fleet-heartbeat.json` + 4 untracked `maintenance/headless/*` drafts (merge-forward blockers; unblock deferred to the 09-21 resume because live Windows `ORA Headless` tasks run the local `run-check.py`); `MEMORY.md`, `event_log.md`, `test_check_open_items_duplicate_ids.py`, `ora-cc-snapshot-refresh`/`ora-lease-snapshot-refresh`/`ora-pm-daily-crons`/`ora-pm-monthly-billing` specs (upstream-changed: land after the merge); `INDEX_reference.md` (live session); `ora-754` deletion.
- **Backup gap found:** `.gitignore:61` `/scheduled-tasks/*/*` excludes `scheduled-tasks/ora-pm-ledger/references/CHANGELOG-2026-07-08-to-2026-08-16.md` (30KB, the 09-06 extraction of 13 build-history sections). The committed `ora-pm-ledger/SKILL.md` points at it, but it is in no git backup. Not force-added (outside scope).

## 2026-09-17 — dirty-tree triage (report-only): merge-forward blockers are superseded copies, but unblock deferred to the 09-21 resume

Session 74d112a1. Four default repos scanned, two-pass mtime settlement (16:50 → 17:16 ET 09-16, re-checked 10:31 09-17). **No commits, archives or restores.** Gabriel approved the merge-forward unblock; it was halted before any write when a live dependency surfaced (below). Final disposition defaulted to report-only.

- **`~/.claude`** (`feat/model-canary-probe-step25`, 94 ahead / 156 behind origin/main, 61 unpushed): 122 dirty entries, all mtime-settled.
  - **Merge-forward blockers** (`checkout-merge-forward-last-run.json`, BLOCKED_DIRTY_OVERLAP since 09-14): the 4 untracked `maintenance/headless/*` files are 09-10 pre-review drafts (session 1bae3021) of what landed as `e39bc29`. `fleet-heartbeat.json` differs from origin/main `d154541` by a 7-second `ts` only. Both are superseded.
  - **Why the unblock was NOT executed:** three Windows tasks (`ORA Headless - integrity-guard/stranded-spec/mirror-drift`) run the LOCAL `maintenance/headless/run-check.py`. `ora-checkout-merge-forward` is paused until the 09-21 resume, so archiving now would break those checks for 5+ days with no merge to replace them. main's `run-check.py` supports all three check names. Correct sequencing is archive → merge back-to-back on 09-21.
  - **Contested (live session 5e58f532):** `reference_costar_loopnet_subscriptions.md`, `INDEX_reference.md`.
  - **Committable when approved** (settled, owners idle/unrecorded, untouched upstream since merge-base): 50 tracked files (34 `_scheduled_tasks_backup/*`, 4 live `scheduled-tasks/*/SKILL.md` incl. `ora-pm-ledger`, 5 `skills/*` incl. `ora-setup-audit` v1.12 vs v1.6 at HEAD, `system-inventory.md`, spec-liveness probe + test, 2 state files, 1 memory file) + the `ora-754` archive move (archive blob == HEAD).
  - **Hold until after the merge** (upstream also changed them): `MEMORY.md`, `event_log.md`, `test_check_open_items_duplicate_ids.py`, the `ora-cc-snapshot-refresh`, `ora-lease-snapshot-refresh`, `ora-pm-daily-crons` and `ora-pm-monthly-billing` specs.
  - **Anomaly:** all 59 modified-tracked files carry mtime 09-14 10:30:46.02–.04, the merge-forward run's exact second, though the script reports git refused before writing. Content is newer than HEAD. [SPECULATIVE] git-side stat/refresh rewrite. Consequence: mtime no longer indicates authorship for these files.
- **oxford-command-center** (1 ahead / 28 behind): `data/ar-mapping-cache.json` is a `savedAt`-only change, also changed upstream (will block a pull). `fix3files.patch` (09-11) is UTF-16 and applies neither forward nor reverse, so it is stale. Proposed: restore + archive; not approved.
- **ora-skills:** only untracked `_archive/*` dirs. **website-canonical:** clean.
- **Side finding:** `ORA Headless - integrity-guard` and `stranded-spec` did not fire 09-17 07:20. Last run 09-16 10:18, result `0x800710E0` (request refused). Unrelated to triage; not investigated.
- **Skill gap:** `scan_dirty_trees.py` stray-clone discovery labels registered `git worktree` checkouts as `stray`, and labels `website-canonical` stray because `wc-seo-fixes` sorts first.

## 2026-09-14 — Claude Desktop startup-freeze investigation + mitigations

- **Root cause (evidence: `%LOCALAPPDATA%\Claude\Logs\main.log`):** at each launch the main process reached ~1.4 GB RSS within 25–40 s, stalled 5–6 s, then logged "Main webview is unresponsive, will kill and reload". The reload repeated the load → hang loop (8 launches 16:43–16:58). Contributors: 591 non-archived sessions (~175 MB JSON, loaded eagerly) + 776 archived (deferred); post-wake scheduled-task catch-up burst (137 children / 10.9 GB tree RSS at 10:54).
- **Red herring:** DAX3API.exe (Dolby) crashes and "Claude service terminated" events are side effects of 3 user-initiated reboots (2:34/4:31/5:00 PM), not causes.
- **Log path moved:** live desktop logs are now `%LOCALAPPDATA%\Claude\Logs` (the `%APPDATA%\Claude\logs` copy stopped 2026-08-20).
- **Applied:** 519 stale sessions archived via `archive_session` (scheduled runs >3d, interactive >14d, excluding starred/pinned/worktree-backed). Non-archived 591 → 72 (175 → 32 MB). Reversible via unarchive.
- **Already in place (other session):** 37 CC tasks paused until 09-21 (`ora-routine-pause-resume-09-21`); the burst returns on resume unless staggered.
- **Pending Gabriel (UI-only):** disable the remote `desktop-commander` plugin (duplicates the Desktop Extension; spawns `npx @latest` per Code session). File the bug report at `Claude_Workspace/01_Workspace/outputs/2026-09-14_ClaudeDesktopFreeze_BugReport_v01.md`.

## 2026-09-14 — ora-cc-schematic-refresh (scheduled, Rev 2026-09-14a)

Routine 2x/week schematic refresh. Producer-clobber pre-check CLEAN (published == source REV 2026-09-06a). All five standing probes re-run live, exit codes captured unpiped; durable status snapshot written to `maintenance/_state/doctrine-status.json`.

**Material findings this run (reason for this log entry — not a routine no-op day):**
- doctrine-integrity-probe.py: warnings jumped 4 → 7. Two brand-new warning classes never seen in this series: the backup-coverage sweep flags top-level dirs `archive/` and `file-history/` under `~/.claude` as having no git-tracked files and being off the transient allowlist — invisible to the private-remote backup and to git-status single-writer checks. Needs a scrub-for-confidential-terms-then-`.gitignore`-opt-in review (or an addition to `BACKUP_SWEEP_TRANSIENT_DIRS`); not actioned by this task. Aging tombstones in session-context.md also grew 1 → 3 (lines 7/14/22, 41/36/36 days old).
- `oxford-command-center`: went from level-with-origin (09-06a) to **28 commits BEHIND origin/main** — the largest gap this series has recorded — plus a newly modified tracked file (`data/ar-mapping-cache.json`) and an untracked `fix3files.patch`. Origin has advanced through PR #327 (appsec CSRF fix), #328 (OI-090 rate-limit follow-up), #329 (warehouse write-schema drift check).
- `ora-pm`: worsened from 3 to **8 commits behind origin/main** (PRs #37/#39/#40) and newly shows a dirty working tree (`package-lock.json`, `package.json` both modified, uncommitted) — not present at 09-06a.
- Fleet: cc enabled rose 36 → 38, LAMS gained 1 disabled (EXPIRED one-time `ora-lams-fleet-resume-20260911`, normal completion). Throttle skips fell 753 → 314/24h (burst continuing to drain). Verdict stays ATTENTION.
- Confidentiality-guard 131/131 (12th consecutive green); memory-integrity EXIT 0, 332/332 (a transient rc=2 in its internal `governor-drift-probe.py --quiet` sub-call did not reproduce on immediate re-check, treated as non-persistent).

Neither repo was pulled/pushed (read-only diagnostics only, per task scope) — both flagged for whoever next touches either checkout. No registry writes, no email. One file edit (schematic HTML) + history-file rollover (4-entry title-block cap, 8-node keep-2 per-node cap, both validated with `node --check`) + one republish (Version 21).

## 2026-09-14 — oxfordra.net release: outline-button contrast + hover-label fix (ZeOoba/Website#80)
- **Target:** oxfordra.net production (Netlify auto-publish on merge). Gabriel confirmed in-turn: "Merge it to production".
- **Pre-flight (session resumed next day):** PR #80 head 7a1057d unchanged, branch 0 behind main, MERGEABLE/CLEAN, CI + Netlify header/redirect checks pass; dist rebuilt from 7a1057d.
- **QC:** site-qc-reviewer APPROVE. The Fable dispatch failed on the monthly spend limit (HTTP 429), so it was re-dispatched on Opus 5 — reviewer >= implementer (Opus 5) holds; a CSS-only site change is not confidential/financial/governor code, so the Fable floor does not apply. Every dark-ground outline button is covered by an override, no uncovered cases, CSS braces balanced, 0 confidential hits (roster verified 2026-09-13).
- **Shipped:** merge `31f5cef` -> deploy `6aa80b4f3cf9eb0007e6235d` (published 14:57 UTC). QC-8 base `.btn--outline` text -> `--gold-accessible` on contact/index/portfolio/track-record/tenant-resources, with dark-ground overrides; QC-9 all dark-ground gold overrides scoped `:not(:hover)` on 15 pages (the hover label had been invisible on navy bands).
- **Post-verify (live, headless Chromium):** light ground rgb(128,99,57); home hero + navy, for-brokers, sell-your-building subpage-hero, Maryland, resources dark grounds rgb(201,169,110); every hover rgb(27,42,74) on rgb(201,169,110). Smoke: `/`, `/contact` 200; `/about.html`, `/tenant-application.html` 301; `/404`, `/assets/chat.test.js` 404. No console errors; the only failed requests are aborted GA4 `/g/collect` beacons on page close, identical on the prior deploy (not a regression). Secret scan 0.
- **Lighthouse:** Netlify single-run mobile Perf 92 / A11y 100 / BP 100 / SEO 100. Within the documented single-run noise band (production 88–100, median 97; identical trees 77 vs 100 — see 2026-09-13 entry); the diff touches no LCP-path assets. No action.
- **Rollback:** publish prior production deploy `6aa6f429d28c240008907baa` (27672b6).

## 2026-09-13 — oxfordra.net perf-score investigation, confidential roster re-verified, outline-button a11y fix (ZeOoba/Website#80)
- **Lighthouse 96 (post-#79) = measurement noise, no code cause.** Netlify's per-deploy Lighthouse is ONE mobile lab run. Byte-identical git trees (preview vs. its squash-merge) scored 77 vs 100 (990400f/ac1356c), 97 vs 96 (7194a1b/27672b6), 97 vs 100 (1bfe019/76a9d34). 19 production deploys 2026-08-13 to 09-13: median 97, range 88-100, stdev 2.9. **Rule:** never read one deploy's score as a regression; pull `npx netlify api listSiteDeploys` history and compare `git rev-parse <sha>^{tree}` first. Local Lighthouse is not viable from the Claude Bash sandbox (chrome-launcher spawn UNKNOWN; a Playwright CDP port handoff hung) and the keyless PSI API quota was exhausted.
- **Confidential roster re-verified; `_meta.roster_last_verified` 2026-08-09 to 2026-09-13** (Gabriel in-turn approval). Checked session-context.md (none active), memory/projects.md (E. Fulton declassified 2026-07-09, nothing added) and this log (no new confidential designations). Roster content unchanged. Gitignored file, no commit. Preflight CLEAR; claim `confidential-roster-verify` taken and released; single-use `allow-config-write` token minted with the quoted approval and revoked (archived) immediately after; an expired `allow-website-write` token also archived.
- **PR #80 (open, not deployed):** QC-8 inline `.btn--outline` base text raw `--gold` (about 2.2:1) on contact/index/portfolio/track-record/tenant-resources now `--gold-accessible` with dark-ground overrides. QC-9, found while fixing: `.section--navy .btn--outline{color:gold}` equal specificity and after `:hover`, so gold text on a gold hover fill (label invisible) on 10 pages; reproduced in headless Chromium; all overrides scoped `:not(:hover)`. Chromium verification on dist: light rgb(128,99,57); dark rgb(201,169,110); hovers rgb(27,42,74) on gold. `npm run verify` green (unit 160, site 29).
- **Hook friction:** the autonomy gate matches the site-repo name inside this repo's per-project memory folder path under ~/.claude/projects, so per-project memory writes for the site repo are blocked without a site-write token; scratchpad writes hit the same false positive.

## 2026-09-13 — eval-harness transcript parser built (branch, not merged)
- `ora-skills` branch `feat/eval-harness-transcript-parser` @ `a45caa5` (worktree `C:\Users\Owner\ora-skills-worktrees\eval-transcript-parser`): new `acquisition-underwriting-eval-harness/lib/parse_replays.py` reads replay subagent transcripts (`<session>/subagents/agent-<id>.jsonl`) straight into aggregate → diff → record_run. Removes the hand-copy of replay scores into a scratch driver.
- Fable REFUTE pass found 1 Critical (≈5% of real completed replays carry no `end_turn`; 09-12 E Fulton r2) + 5 Important; all fixed with tests before commit. Residual, documented: a differing earlier completion notification can leave no transcript trace (09-12 Hamilton r3) → orchestrator passes `--failed-agent-ids`.
- Verified: 2026-09-13 run's 18 transcripts reproduce identical combined_observed/category_deltas/status (exit 0). Suite 126/126. Not pushed; scheduled-task wrapper unchanged (it defers to harness SKILL.md).

## 2026-09-13 -- OI-296 run-index dedup + OI-288 Notion email-only rule: 6 PRs merged and landed on the live step25 branch

- **Merged after independent review verdicts** (reviewer tier at or above the implementer each round; heads pinned with --match-head-commit):
  - ora-claude-config #199 -> 9816047, ora-health-guard v1.14 email-only rule + `maintenance/_state/notion-publish-degraded.json`. Fable CHANGES-REQUESTED once, then APPROVE.
  - ora-skills #55 -> b8b7024, automation-health-monitor v1.11. Approved conditionally, then APPROVE after the rule block was re-synced.
  - ora-claude-config #200 -> a95f4f0, OI-296: skip Stage-0 runs whose prior digest send is confirmed in the send-log. Opus reviewed 3 rounds of CHANGES-REQUESTED, then APPROVE.
  - ora-claude-config #204 -> 230f9a4 and ora-skills #58 -> ad46140: re-review minors (min_bytes floors, hygiene must_not_match, flag-age excluded from FAIL-aging). Fable APPROVE.
  - ora-claude-config #205 -> 09b22ad, OI-296 minors (attempt always logged, manual runs go to adhoc/). Fable APPROVE.
- **Landed on feat/model-canary-probe-step25**, because the primary checkout runs from this branch and merge-forward is blocked: 8bb1e13 (#199 + #200), 2f2dd7e (#204 state file + replay test), 7a22999 (#205). Each commit's blobs were verified equal to origin/main, except ora-health-guard/SKILL.md, which is this branch's v1.12/v1.13 plus the PR hunks.
- **Commit-message correction:** 8bb1e13's message names only PR #199's SKILL.md hunks, but the live file had already been synced with #204's item-6 and v1.15 lines, so 8bb1e13 carried those too while they were still unreviewed. They were then reviewed, approved and merged unchanged in #204. 2f2dd7e's message records this.
- **Live Cowork edits (OneDrive store, no git):**
  - automation-health-monitor task SKILL.md -> v1.27, Step 0.55a; backup `_state-history/_skill-versions/SKILL.v1.26-...`.
  - ora-health-guard-fail-aging-nudge step 3a exclusion.
  - The installed Cowork skill copy for automation-health-monitor was synced by the ora-skills push hook.
- **Follow-ups:** OI-304 (pm-ledger double-send while degraded). The flag file's `dark_producers` lists 28 tasks that go silent while Notion page creation is blocked. Flag review_by is 2026-09-22.
- **Tonight's first run:** the ground-truth auditor uses the round-2 fallback, because `stage0-attempts.jsonl` does not exist yet. The reviewer confirmed it cannot mis-credit, since every existing digest has a confirmed [OK] Sent line.

## 2026-09-13 — oxfordra.net release: PR #77 QC follow-ups (ZeOoba/Website#79)
- **Target:** oxfordra.net production (Netlify auto-publish on merge). Gabriel confirmed deploy in-turn via AskUserQuestion ("Deploy now").
- **Shipped:** merge `27672b6` → deploy `6aa6f429d28c240008907baa` (published 19:06 UTC). QC-1 gold stat text on parchment → `--gold-accessible` (for-brokers, sell-your-building); QC-2 sitemap lastmod (about, sell-your-building, 4 guides); QC-3 Article publisher.logo → 512px logo; QC-4 `--gold-accessible` added to inline `:root` on 16 pages (reviewer flagged 1, site-wide test found 15 more); QC-5 guide-card CSS promoted to styles.css, `?v=16`→`?v=17` on 22 pages; QC-6 build-dist excludes `*.test.js` from dist and `assets/chat.test.js` (7 tests) now runs in CI; QC-7 `301!` for `/tenant-application.html` + `/application-received.html`. Guards QC-1..7 added to `tests/site/seo.test.mjs`.
- **Gates:** `npm run verify` green (unit 160, site 27); CI + Netlify header/redirect checks green; CodeRabbit no comments; preview proof (new 301s, chat.test.js 404); site-qc-reviewer APPROVE (0 confidential hits; roster stale caveat — session context confirms no active confidential deals).
- **Post-verify (live):** both new `.html` paths 301; `/about.html` 301; `/404` + unknown 404; `/assets/chat.test.js` 404; `styles.css?v=17` 200 with guide rules; 5 sampled pages on v17; 4 accessible-gold stats on for-brokers; no inline guide CSS on home. Netlify Lighthouse mobile `/`: Perf 96 / A11y 100 / BP 100 / SEO 100 (prior deploys: 100 after #77, 97 after content-identical #78 → within observed ±3–4 lab variance; PSI API quota exhausted, independent recheck pending). Secret scan 0.
- **Rollback:** publish prior production deploy `6aa6c9a265ed3d0008ea9c69` (ac1356c).
- **Open (non-blocking QC):** raw `--gold` `.btn--outline` on contact/index/portfolio/track-record/tenant-resources (light-ground buttons ~2.2:1); sitemap lastmod not bumped for pages whose only change was the CSS version; confidential roster `roster_last_verified` still 2026-08-09 (governance write needs Gabriel).
- **Tooling lesson:** Browser pane rAF does not fire while the pane isn't painting → async `media="print"` stylesheet swap never completes → false layout regressions; force `link.media='all'` for measurement only.

## 2026-09-13 -- ora-ground-truth-auditor frozen-backlog push blocker cleared on live step25 branch (session 4af15615)
- Root cause (reported by peer session f2a12aac and verified here): scheduled-tasks/ora-ground-truth-auditor/SKILL.md was UNTRACKED on feat/model-canary-probe-step25, a stale 2026-09-10 20:26 copy (blob c790c41b, identical to 1059741/e35a4de) predating the run guard. test_scheduled_task_run_guard.py:385 failed "unguarded notion side effect is on the frozen backlog", which blocked the pre-push hook-tests gate.
- Fix: commit e8ecb53 lands origin/main's guarded version (blob 5d70be51, origin/main 95448e6) via a pathspec commit. The stale copy was moved to the gitignored scheduled-tasks/_archive_2026-09-13_stale-copies/ (byte-verified). UNGUARDED_BACKLOG was not touched. The live CC/MCP ora-ground-truth-auditor now runs the guarded spec.
- Gates: preflight-shared-checkout returned CONTESTED rc=1 because the orphan untracked file is inherently "not yours". The evidence showed no live owner, no claim, and no live-tree touch by any session. Gabriel approved proceeding in-turn ("proceed"), with allow-config-write minted for that approval. eos-review-gate does not cover this path (empty key); an independent opus review confirmed the pathspec, blob ids, guard-marker match at SKILL.md:39, and that no folder probe treats the _archive_ dir as a task.
- Verify: test_scheduled_task_run_guard.py ALL passed ("ora-ground-truth-auditor :: guarded" PASS). Not pushed. The event_log uncommitted backlog the peer flagged was already committed by the b3300ed memory sync.

## 2026-09-13 -- Graft D landed: acquisition-underwriting v4.22 Discount Decomposition (ora-skills #57) + underwriting-checker tie-out (ora-claude-config #203) MERGED

- Gabriel in-turn: "MERGE THEM WHEN READY".
- #57 merged as `b57acfe`; #203 merged as `95448e6`.
- origin/main blobs verified equal to the reviewed heads: `02bee5b` (SKILL.md, ic-memo-structure.md, CHANGELOG-v3.2-v4.18.md) and `32ed0e2` (checker).
- Review chain: 3 Fable passes. 1st: APPROVE-WITH-FIXES, 4 Important. 2nd: APPROVE-WITH-FIXES, 1 Medium. 3rd, on the exact staged content: APPROVE.
  - The CodeRabbit "SUCCESS" status was rate-limited and is not a verdict.
  - Qodo posted a trial-ended notice; Qodo was retired 2026-09-06, but the GitHub app still appears installed.
- Local ora-skills main forward-merged as `93688f1`. `repo_first_check`: acquisition-underwriting IN-SYNC; the DIVERGENT ledger entry cleared.
  - The remaining DIVERGENT `automation-health-monitor` is not from this work: it came from #55/#56, forward-merged by another session.
- Side effect noted: the ora-skills post-commit hook synced the FEATURE-branch content into the installed Cowork cache before merge. Surfaced by a peer session. Harmless here only because the PR merged unchanged after its last sync.
- The live `~/.claude/agents/underwriting-checker.md` stays pre-v4.22 until `ora-checkout-merge-forward` runs: that checkout is on another session's branch and was left untouched.
- Worktrees removed, local branches deleted. Remote branches left in place.
- Eval-harness rerun is expected on the next `14 12 * * *` fire (SKILL.md hash change); expected Combined delta is ~0.
- Remaining grafts: B, E, A-groundwork. Tracker rows OI-301..303 are still pending, blocked on a tracker claim held by a scheduled run.

## 2026-09-13 — oxfordra.net release: SEO audit fixes (ZeOoba/Website#77)
- **Target:** oxfordra.net production (Netlify auto-publish on merge to main). Gabriel confirmed deploy in-turn; scope choice "fix grid, then deploy".
- **Shipped:** merge `ac1356c` → Netlify deploy `6aa6c9a265ed3d0008ea9c69` (published 16:05 UTC). `.html`→clean-URL `301!` rules for all sitemap pages; `/404` real 404 + no canonical on 404.html; Organization logo → `images/oxford-logo-512.png`; closing claim unified to 30–45 days (site copy + `scripts/meta.md` chat KB); Article dates on 4 guides; owner-guide card blocks (home/for-brokers/markets hub/Columbus/Maryland, 1/2/4 and 1/3 breakpoints); meta/title/OG fixes; `tests/site/seo.test.mjs` in CI. KC market page (#4) and H1 rewrites (#7) out of scope by decision.
- **Gates:** `npm run verify` green; CI + Netlify header/redirect checks green; deploy-preview redirect proof (no loops); site-qc-reviewer APPROVE (0 confidential-term hits; roster `_meta.roster_last_verified` 2026-08-09 flagged stale >30d).
- **Post-verify (live):** `/about.html`→301 `/about` (1 hop); `/index.html`, `/markets/index.html`, `/resources/index.html`, `/privacy.html` → 301; `/404` + unknown → 404; logo 200; new hero copy + guides section served. Netlify Lighthouse (mobile, `/`): Perf 100 (was 97) / A11y 100 / BP 100 / SEO 100; secret scan 0 matches.
- **Rollback:** Netlify "publish deploy" on prior production `6aa6c7b64b7bde00084a963a` (commit 80ee86c).
- **Follow-ups (non-blocking QC):** `--gold` on parchment stat text (for-brokers:213-225, sell-your-building:271,275) → `--gold-accessible`; sitemap lastmod for resources/* + about; Article publisher.logo → 512 logo; `--gold-accessible` missing from application-received inline :root; promote guide-card CSS to styles.css; exclude `assets/chat.test.js` from dist; `/tenant-application.html` duplicate 200. Related: ora-skills#56 (website-perfection v1.1) open; website-canonical `.claude/launch.json` now has `site`/`worktree` serve-dist configs.

## 2026-09-13 -- PR #202 prepush worktree test fix landed on live step25 branch (session 4af15615)
- Landed blob 39a73ffa (4015782, PR #202) of hooks/tests/test-git-prepush-doctrine-gate-worktree.py onto feat/model-canary-probe-step25 in the primary ~/.claude checkout as commit 63dd51a: single-file checkout plus pathspec commit, no merge or cherry-pick, so none of the ~110 foreign dirty files were touched.
- Gates: preflight-shared-checkout CLEAR (rc=0, run twice); claim repo-housekeeping; allow-config-write minted on Gabriel's in-turn "approve"; eos-review-gate key 629aa2190d77 matched the prior review, and a fresh independent review (claude-fable-5-1) was recorded APPROVED because review artifacts are session-scoped. Three nits, none reachable via the production writer.
- Verify: test-git-prepush-doctrine-gate-worktree.py 34/34 passed. doctrine-status.json has 0 "2020-01-01" records; the newest record is 2026-09-13T11:47:34 (clean). File mtime 11:51:56 predates the test run, so the canonical file was untouched. The 11:50 fixture record was already gone, and no scrub was needed.
- Not pushed (Gabriel-scoped). Pushing the branch still hits the pre-existing frozen-backlog finding (ora-ground-truth-auditor unguarded notion side effect), which is unclaimed and needs a separate override decision by the branch owner. HEAD has since advanced to b3300ed (8bb1e13 PR #199/#200 landing, memory sync), and 63dd51a is an ancestor with the blob intact.

## 2026-09-13 -- Pre-push worktree test stopped polluting canonical doctrine-status.json (PR #202 merged); 19 fixture records scrubbed

- **Cause.** `hooks/tests/test-git-prepush-doctrine-gate-worktree.py` ran `dg.main()` with the real probe but never set `STATUS_PATH_OVERRIDE`. Every push since 2026-09-06 therefore wrote `rc=1 "[MISSING] bare date 2020-01-01 at line 6"` into `maintenance/_state/doctrine-status.json`, 1-3 min after the real clean result.
- **Fix: ZeOoba/ora-claude-config#202, merged.**
  - Test-only change: redirect to a temp dir, plus a non-vacuity assertion and a leak assertion against the writer's `DEFAULT_STATUS_PATH`.
  - TDD: RED 32/33, then GREEN 34/34.
  - Independent review by claude-fable-5-1: APPROVED, recorded via `eos-review-gate.py --record`.
- **Scrub.**
  - Removed 19 history records whose summary carries the fixture signature. The top-level snapshot was reset to the newest real record (2026-09-13T10:37:32 pre-push, clean).
  - 30-day doctrine summary went from 20 pass / 19 fail to 20 pass / 0 fail.
  - Pre-scrub copy: `maintenance/_state/_archive/2026-09-13_doctrine-status_pre-fixture-scrub.json.bak`.
- **Not live in the primary checkout yet.** `~/.claude` is on `feat/model-canary-probe-step25` (131 behind main, 53 unpushed, 109 dirty). `preflight-shared-checkout.py` returned HEAD_MOVED (rc=3), so nothing was applied there. Until that branch takes main, pushes from it will re-add fixture records.

## 2026-09-13 -- External-AI grafts: Step-0 capability audit re-scoped A-E; Gabriel rulings

- 5 read-only code/data audits (A/B/E Sonnet, C/D Fable) ran before design, per /build step 0.
- **D (curable/incurable discount decomposition) -- BUILD.** Inputs already exist (Stage 2.5 CapEx in all-in basis, SKILL.md:114 comp-vs-RCT rule, FORG BDS-5 cure cost). The table itself is verified-absent. Scope: sub-block in Stage 3 + IC memo §9. Reported, not scored. `[est]` + source on every row. No golden-set address as worked example. Eval-harness delta expected ~0 (scored path is Stage -1..2.2).
- **B (broker scorecard) -- BUILD; Notion schema change APPROVED in-turn.**
  - Broker relation on Deal Sourcing Log + Pipeline Tracker. Name-match backfill goes through a Gabriel review list before any link is written.
  - Computed Sent/LOI/Closed added in Broker Relationships alongside the manual Deals Referred/Closed/Volume fields, which stay untouched.
  - Touch-cadence cites the broker's own Deal Sourcing Log listings; county recorder data carries no broker field.
- **E (long-lead renewals) -- BUILD reduced.**
  - 24-mo queue built on command-center `bucketExpiry` 12-24m.
  - Tenant DB gains Market Rent Source + Market Rent As-Of (APPROVED). Offer recs are blocked when market rent is unsourced or older than **12 months** (ruled).
  - External growth check covers tenants expiring <=24 mo or in the SAME BUILDING as a vacancy. Suite adjacency is not computable (free-text units), so it is dropped.
- **A (vanished listings) -- GROUNDWORK ONLY (ruled).** Sourcing scans write a Last Confirmed Listed date. Blockers:
  - No positive absence check.
  - No address->Parcel ID resolver.
  - Sales verifiable in 3/10 markets.
  - `outreach-ratification.json` re_trigger requires a new ruling for any new signal.
  - Revisit: OI-303.
- **C (NNN recoverability audit) -- PARKED (ruled).** No transaction-level QB GL exists (CSV = 2024 annual totals). F31 CAM Recovery Type is populated on 7/298 Tenant DB rows, none multi-tenant. Running it now would fabricate $ (Inv 7). Prereqs: OI-301 (abstract multi-tenant leases) and OI-302 (QB Transaction Detail by Account exports).
- OI-301/302/303 allocated. Tracker rows are pending because open-items-tracker was claimed by session 8a276a28 at the time.

## 2026-09-13 -- External AI agent proposals (ChatGPT / Grok / Gemini "Oxford AI OS") intake: SUPERSEDED + 5 grafts ratified

- Ran `external-artifact-intake` against the live stack (ora-skills, 16 agents, 65-task dual fleet). ~80% already covered (county-parcel-screen/owner-outreach, acquisition-underwriting Edge Scan + FORG + RCT, passed-deal-tracker/calibration loop, deal-decision-ledger, deal-execution/dd-critical-tracker, loi-generation, deal-comparison/portfolio-growth/bearmode, om-intake-ocr, county-sales-monitor).
- **Disposition: SUPERSEDED** for all three documents except the grafts below. No new agents, no orchestrator layer.
- **Gabriel ratified all five grafts (in-turn):** A vanished-listing join (Deal Sourcing Log x county-sales-monitor, no recorded sale -> owner-outreach queue) · B broker scorecard (sent/LOI/closed into Notion Broker Relationships DB; broker-touch-cadence cites a specific recorded sale, still draft-only) · C lease-recoverability vs QB GL expense-line audit (quarterly) · D curable/incurable discount decomposition in acquisition-underwriting Edge Scan (eval-harness rerun, no weight change) · E 18-24-mo mark-to-market renewal queue + external growth signals for tenants expiring <=24 mo or adjacent to vacancy.
- **Rejected (recorded):** automated broker/owner sends (Inv 1); self-adjusting scoring weights (Inv 4); 300-500-attribute Deal Genome ML (n=22 decisions); point sale-likelihood %s (no calibration set); owner-age/utility/capital-call/competitor-cap-structure signals (unobtainable / Inv 7 risk); headless QBD RPA (SharePoint export canon); Gemini FAR<30% filter (contradicts FAR info-only doctrine); vision underwriting, contractor bid DB, negotiation simulator (low ROI).
- Verified gaps: county-parcel-screen mentions delisted listings only as manual enrichment; no broker hit-rate anywhere; monthly-close/exception-detection have no GL recoverability check; lease-renewal-pipeline window is 6 mo; tenant-intelligence signals are internal-only.

## 2026-09-13 -- OI-120 (config-write-guard GIT_MUTATE_RE false block) reproduced live again; separately, preflight-shared-checkout.py zero-live-owner blind spot documented

- **OI-120 confirmation, not a new defect:** while repairing the real index after an isolated event_log.md commit, `git reset -q -- <memory file>` was BLOCKED as "file-rewriting git command referencing the live ~/.claude checkout" -- an index-only operation, no working-tree rewrite, and the target wasn't even a governance path. Trigger this time: a habitual `cd /c/Users/Owner/.claude &&` prefix put the literal `.claude` root-mention in the same command as `reset` (a `GIT_MUTATE_RE` verb), tripping the coarser "root mentioned anywhere + mutate verb anywhere" branch in `config-write-guard.py`. Same root cause OI-120 already names (`hooks/lib/tool_call_paths.py`'s `GIT_MUTATE_RE` treats index-only verbs as working-tree rewrites, deliberately breadth-over-precision) -- did NOT open a duplicate OI or attempt a `hooks/**` fix (OI-120 already scopes candidate fixes behind a mandatory adversarial REFUTE + differential battery). Workaround used: drop the redundant `cd` -- shell cwd already there -- which cleared it with no override token. `open-items-tracker.md` was CONTESTED at edit time (5 live owners + a competing live claim, session 8a276a28 mid-fix on OI-500/pre-push), so this confirmation is recorded here instead of appended to OI-120 directly; fold it in on the next open-items pass.
- **Separately, real (fixed) gap:** `preflight-shared-checkout.py`'s `--accept-stale` only clears the partial-commit shape (caller IS a live owner, others merely stale) -- it cannot clear a file with ZERO live owners at all, which is event_log.md's permanent state (written only via `append-event-log.py`, bypassing the Edit/Write provenance hook). Confirmed live: `--accept-stale <path>` on the exact contested path still returned CONTESTED. Fixed via doc-only cross-reference, commit `e57848f`: the tool's own docstring and `memory/rules.md` sec 14 now both name event_log.md as the known instance and point to `reference_event_log_uncommitted_backlog.md`'s already-safe bespoke procedure, so a future session doesn't spend an investigation (an agent dispatch, in this case) rediscovering the same dead end.

## 2026-09-13 — ora-pm PR #37 merged + live (deploy-env gate)

- Merged `7061eda` (main had not moved since the branch base; PR CI green). First strict main run: build-env check OK, Pages production env check OK (3 Stripe deferred warnings), deploy succeeded and is the current Production deployment; `/api/health` 200, admin route with a bogus token 401 (not 503). Every future main deploy now blocks on a missing required Pages/build var. At tenant-payments launch, promote the 3 Stripe vars to `required` in `scripts/check-deploy-env.mjs`.

## 2026-09-13 -- PR #201 (json_field_equals auto-check) MERGED; main verified == reviewed head
- Merged `83c23a0` at 2026-09-13T15:06:27Z by ZeOoba.
- Verified (not assumed from MERGED state):
  - `origin/main` blobs for memory-integrity-probe.py and its test equal the reviewed head `bb86040`.
  - No revert commits touch the probe.
  - The runtime copies already equal them via mirror `f4cd1b5`, so merge-forward sees identical content.
- Cleanup: the merged worktree `memory-integrity-json-autocheck` was removed. Local branch deleted; `bb86040` is still reachable from main.
- Remote branch `feat/memory-integrity-json-field-autocheck` was left in place.

## 2026-09-13 -- memory-integrity-probe: json_field_equals auto-check (PR #201), mirrored to runtime; OI-278 wired
- Why: open-items auto-checks could only read fleet-registry state. So OI-278's closing condition (`ora-pm-cron/payments-feed-state.json` status=PRESENT) could not flag itself.
- Shipped: [PR #201](https://github.com/ZeOoba/ora-claude-config/pull/201), head `bb86040`, OPEN (not merged).
  - Adds `kind=json_field_equals path= field= expect= [max_age_hours=]`.
  - True/False/None as before, plus a new str "could not evaluate" warning for missing, stale, oversized or unreadable evidence, so it is never a silent False.
  - Unquoted values shed markdown punctuation and backticks.
  - fleet-status is loaded lazily and only for registry kinds.
- Tests 84/84, 48 of them new. Two Opus adversarial rounds:
  - Round 1: 1 Important (trailing period -> silent False) plus 6 minors, all fixed test-first.
  - Round 2: verified closed.
  - Live-memory probe output is byte-identical to the pre-change probe.
- Runtime mirror `f4cd1b5` on feat/model-canary-probe-step25:
  - Both blobs == bb86040. Committed with `--only` on those two paths.
  - Preflight --since b711880 CLEAR. Gabriel approved in-turn.
  - allow-config-write token minted for this one mirror, then moved to the session overrides `_archive/`.
- Tracker:
  - Convention section documents the new kind.
  - OI-278 carries `kind=json_field_equals ... expect=PRESENT max_age_hours=96`, which evaluates False today (feed ABSENT).
  - An `Auto-check scope` note says a match covers only the feed half; the ruling on the 68 pre-guard fees is still manual.

## 2026-09-13 — ora-pm deploy-env gate: PR #37 open (NOT merged)

- [ZeOoba/ora-pm#37](https://github.com/ZeOoba/ora-pm/pull/37) (`ci/pages-secrets-check` @ `ff22265`): `scripts/check-deploy-env.mjs` + ci.yml block the production deploy when a required Pages production var (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, CRON_SECRET, ADMIN_EMAILS, CONFIDENTIAL_TERMS, ANTHROPIC_API_KEY) or build var (VITE_SUPABASE_URL/ANON_KEY) is missing; Stripe vars `deferred` (warn only) until tenant payments launch — promote them to `required` at launch. Fail-closed on Cloudflare API/credential error; warn-only on PRs.
- Evidence: 646/646 tests, typecheck clean; adversarial review → drift-guard gaps fixed + mutation-checked (4 access patterns); PR CI run 34763674157 proved the existing `CLOUDFLARE_API_TOKEN` can read the Pages project (OK + the 3 expected Stripe warnings). Known limit: an existing-but-empty secret_text passes (API never returns secret values).

## 2026-09-13 -- config-write-guard commit/run friction was already fixed; no new helper built

- Session-end friction report claimed the config-write-guard blocked `git commit` and test-run commands twice, solely because their text mentioned `~/.claude`/`CLAUDE.md`, and proposed a new helper (commit message via a scratch file in a worktree) to route around it.
- Before building, ran `hooks/config-write-guard.py` directly against synthetic PreToolUse payloads instead of trusting the report: a plain `git commit -m "... CLAUDE.md ..."`, the same message via the documented heredoc form, and `python hooks/tests/test-eos-claude-md-guard.py` (both bare and under pytest) all exited 0 (allow) on the current checkout (HEAD `602e64b`).
- `git log -- hooks/config-write-guard.py` shows both false-positive classes already closed: `569ef4b` (shell-matcher false positives) and `7d01eff` (evidence-based WIP attribution; read-only escape hatch). The friction predates these fixes and does not reproduce now.
- Decision: no helper built -- it would have re-solved an already-fixed problem. `hooks/lib/isolated_commit.py` was also checked and does not overlap (it solves cross-session staging collisions, not this false-positive class).
- Lesson (reinforces `feedback_measure_before_arguing.md`): a friction report is a memory of a past event, not a claim about current code -- check `git log` on the implicated file before proposing a build, not just before asserting a gate's *behavior*.

## 2026-09-13 -- ora-routine-pause-resume-2026-09-11 folder archived (retire step 2/2)

- Completes the same-day RATIFIED retire (registry entry deleted earlier). Folder moved to `scheduled-tasks/_archive_2026-09-13_onetime-complete/ora-routine-pause-resume-2026-09-11/` (Gabriel-directed "archive once 5271f2eb is reconciled").
- Reconciliation: preflight had returned CONTESTED on the SKILL.md (uncommitted hunk owned by session 5271f2eb). Evidence: owner idle since 2026-09-10 20:49 ET (transcript mtime), no active claim on the path, hunk = item 38 `ora-ground-truth-auditor` added to the resume list, already consumed by the 2026-09-11 fire; task no longer registered. SKILL.md moved intact with the hunk (sha1 a956be4b, verified pre/post); hunk also saved as `uncommitted-hunk-session-5271f2eb.patch` + ARCHIVED.txt beside it.
- Primary checkout now shows ` D scheduled-tasks/ora-routine-pause-resume-2026-09-11/SKILL.md` + untracked archive dir -- left for commit hygiene. `_scheduled_tasks_backup/` copy left in place per the 2026-08-28 onetime-complete precedent.

## 2026-09-13 -- ora-pm payments-feed-absent notice de-noised; OI-278 filed (was a dead pointer)
- Trigger: the ora-pm#26 guard sends an identical "PAYMENTS FEED ABSENT" digest on every daily run. That trains the reader to ignore it. OI-278 was also cited in 3 places but had no tracker row.
- Shipped (`C:/Users/Owner/ora-pm-cron`, not git; originals in `_archive/2026-09-13_pre-oi278-feed-state/`):
  - `ping-crons-lib.ps1` adds `Get-PaymentsFeedPolicy` plus Read/Save state helpers.
  - `ping-crons.ps1` gates delinquency-check emails on `payments-feed-state.json`. It sends on the first absent run, every 7 days, and on any nonzero or malformed fee count. Other days it logs `SEND SUPPRESSED ... tracked=OI-278`. When the feed returns it sends a one-time `PAYMENTS FEED RESTORED - OI-278 can be closed`.
  - Every malformed shape fails open (sends). State advances only after a successful send. critical-dates-alerts is unchanged.
- State seeded ABSENT since 2026-09-13T09:47:13, matching the 09:47 notice already sent. First suppressed run: 09-14. First reminder: 09-20.
- Verified:
  - `-SelfTest` 38/38.
  - Stubbed end-to-end harness: 11 scenarios.
  - Opus adversarial refute: 0 Critical, 1 Important (a non-integer fee count threw into the POST-error catch). That and Minor findings 2-6 were fixed test-first.
- Also: OI-278 row and stub filed in open-items-tracker.md. `ora-pm-daily-crons` SKILL.md now treats SEND SUPPRESSED as expected (file edit only, no update_scheduled_task call). Neither is committed; the `~/.claude` checkout is dirty with other sessions' WIP.

## 2026-09-13 — ora-pm PR #33 live-verified end to end

- First expense ever created through the admin UI: `expenses` row `e6cb00aa-0efe-4a00-97be-7b3315ebb54a` (3540 E 5th Ave, taxes, $5,000, 2026-09-13), created 14:29:24Z, with `recoverable=true` and `vendor`/`invoice_ref`/`description` null — exactly the payload that previously failed PGRST204/422. Confirms both the schema fix (PR #33) and the `ADMIN_EMAILS` production secret fix from the prior entry. Test row to be deleted by Gabriel in the UI. Still open: production Stripe secrets absent (not investigated).

## 2026-09-13 -- Ground-truth audit follow-ups (Gabriel-directed): expire-leases weekly, one-time resume RATIFIED retire, heartbeat clock source, sweep doc fix

- **ora-aaos-expire-leases retimed daily -> weekly** (cron `20 7 * * *` -> `20 7 * * 1`, Mondays 07:20 ET) via update_scheduled_task; SKILL.md frontmatter v1.3 note added, `[MODEL:]` tag moved back to the end of the description (checked date left at 2026-07-26 -- not re-observed). Evidence: 2026-09-13 audit verifier found ora-ops `locks/` empty and `aaos-events.ndjson` unchanged since 2026-08-16, so the daily sweep was a guaranteed no-op. Revert trigger: any new lock file or event. Reclaim window now up to ~7d.
- **RATIFIED retire: ora-routine-pause-resume-2026-09-11** (CC/MCP one-time, fired 2026-09-11T20:01:42Z, enabled:false since). Registry entry deleted via delete_scheduled_task (CC/MCP order: delete first). Folder archive NOT done: preflight-shared-checkout.py returned CONTESTED on `scheduled-tasks/ora-routine-pause-resume-2026-09-11/SKILL.md` (uncommitted edit owned by session 5271f2eb; stale owner 57f9ecd1). Archive the folder to `_archive_*` once that owner is reconciled. OI-277's stalled progress marker for this id is moot now the registration is gone.
- **ora-cowork-heartbeat v07 (OI-297)** -- LAMS SKILL.md (OneDrive store, hand-edited; governance mirror `00_Governance/Scheduled/ora-cowork-heartbeat/SKILL.md` synced to the same hash 31e95b16b1d0; pre-edit copy kept in session scratchpad). Step 1 now requires `now_utc` from a real clock (shell `date -u` -> notion-fetch "as of" server timestamp -> abort `HB ❌ no clock source`), never derived from the prior page value. Watchdog prose 16h/KNOWN GAP -> 30h (OI-280 closed that gap 2026-09-12). Note: the LAMS registry description may lag this frontmatter until the next Cowork-side update. The live page still shows the wrong 2026-09-13T20:22:00Z value -- correction draft remains in ground-truth-pending-approval/2026-09-13/ (not applied).
- **ora-memory-commit-sweep SKILL.md**: exit-1 line said "retries automatically next cycle 15 minutes later"; corrected to the registry cron `0 19 * * *` (next daily run, ~24h). Doc-only.
- **Archived** `ground-truth-pending-approval/2026-09-12/cc_ora-doctrine-integrity-guard_...` -> `_archive/2026-09-12_resolved/` (finding resolved in-session 2026-09-12, OI-287 closed; never sent/applied).
- **portfolio.json staleness (asOf 2026-09-06)**: not refreshed from this session -- `run_scheduled_task` is refused in unattended-classified sessions. Next producer fire: ora-cc-snapshot-refresh Mon 2026-09-14 06:15 ET (worktree-isolated extract + guarded auto-push). EXCEL.EXE currently holds the Master Workbook open.
- Preflight gate CLEAR for both ~/.claude SKILL.md edits; edits sit uncommitted in the primary checkout (feat/model-canary-probe-step25) for memory/scheduled-task commit hygiene to pick up.

## 2026-09-13 — ora-pm CI: main deploys serialized + tip-of-main guard (PR #36 merged)
- ZeOoba/ora-pm PR #36 merged at `35669b8`. `ci.yml` now has workflow-level `concurrency` (`CI-<ref>`, cancel-in-progress only for PRs) plus a step that skips the Cloudflare Pages deploy unless `GITHUB_SHA` is the exact `refs/heads/main` tip. Fails closed if origin/main can't be resolved.
- Verified on the first post-merge main run `34762480302`: the tip check succeeded (checkout-token `ls-remote` auth works), and wrangler deployed `https://1f9d35ac.ora-pm.pages.dev` (0 new files; CI-only change).
- Adversarial subagent review (opus): no blockers. Fixed: `ls-remote` tail-match, notice→warning on skip, wrong incident citation.
- ⚠️ Until 2026-10-13: do NOT re-run any ora-pm main CI run created before `35669b8`. It re-runs with the old `ci.yml` (no concurrency, no guard) and would redeploy a stale build over production.
- Open: a main CI re-run of `6321afd` at 12:48:33Z (actor ZeOoba) was not started by the PR session and is unattributed; it was harmless (same tip). Actions also never fired for PR push `4f54173`; an empty commit re-triggered it.

## 2026-09-13 — /ship ora-pm target: PR #198 MERGED after 3-round adversarial review
- Merge commit `108f048` = origin/main tip; ship.md content verified on main; no revert. Head `a83212d` merged with `--match-head-commit`.
- Review (independent opus subagent, read-only against ora-pm ci.yml, server/index.ts ADMIN_EXEMPT, live GETs, secrets, run history): R1 BLOCK — post-verify bundle check impossible for server-only changes, wrong 401 rationale, crons "don't ride the deploy" misleading (they POST to live `/api/cron/*`, money-moving), migrations omitted, merge=prod-deploy/unprotected main unstated, concurrency wording would rot on ora-pm PR #36. R2 BLOCK — my migration step was unexecutable (`db-migrate.yml` main-only; `SUPABASE_ACCESS_TOKEN`/`SUPABASE_DB_PASSWORD` secrets absent; its only run 32583466897 failed). R3 APPROVE-WITH-NITS — dashboard-fallback full-paste + money-table atomicity probe folded in.
- Deferred follow-up (task chip): stale "manual deploy / Windows Task crons" copies in EOS spec §table, memory `reference_ora_pm.md` + `tech.md`, ora-pm `wrangler.toml`.
- Runtime `~/.claude` checkout (on `feat/model-canary-probe-step25`) not yet carrying the fix — picks up via merge-forward.

## 2026-09-13 — PR #193 (OI-249 corrector + preflight gate to main) and PR #196 (runtime doctrine promotion) merged

- **#193** merged as `4fdc982` at reviewed head `f18a339`. It lands on `main` `checkout-merge-forward.py`, `cross-repo-wip-scan.py`, `preflight-shared-checkout.py`, and the `ora-checkout-merge-forward` SKILL.md.
  - The five code-review findings were fixed, each reproduced first:
    - The corrector stranded the shared checkout mid-merge on a commit failure.
    - In-progress operations were reported as a silent BLOCKED_STAGED.
    - Preflight read CLEAR for a `--paths` entry outside `--repo`. This fix was authored in a separate session and cherry-picked.
    - The SKILL.md send-retry rule contradicted itself.
    - Work claims could never make the corrector yield.
  - Independent Opus adversarial review ran three rounds (REJECT, APPROVE, APPROVE). It added fixes for:
    - another session's merge being aborted when it started during the fetch;
    - rev-parse rc 127/128 read as MERGE_HEAD absent;
    - a stale index.lock reported as routine;
    - this run's own conflict stranded when origin moved mid-run;
    - refusal markers matched against file paths; the fix also pins `LC_ALL=C`;
    - the dir-to-file overlap header;
    - a whole-repo STEP 0 claim putting every preflight into CONTESTED;
    - a literal `~` in preflight `--paths` reading CLEAR.
  - Tests: corrector 127/127, preflight 185/185, wip-scan 63/63.
  - Pre-push gate: two attempts were blocked by a load timeout in `maintenance/test-append-event-log.py`, which #193 doesn't touch (40/40 in isolation, 11 min). Gabriel approved an allow-hook-test-failure token in-turn. The final gate run passed 119/119, so the token was not used.
- **#196** was retargeted to `main` after #193 merged, then merged as `299cbf9` at head `0ddf9ea`. The diff was exactly `CLAUDE.md` and `memory/rules.md`: line 35 now points to rules.md §2, line 78 carries the preflight gate with `--repo` and fail-closed exits, and rules.md §2 gains the exit-5 row.
- **Runtime:** `94c9ca6` on `feat/model-canary-probe-step25` mirrors the five #193 files byte-identically from `f18a339`, under Gabriel's in-turn allow-config-write approval with preflight CLEAR. Not pushed. The runtime CLAUDE.md/rules.md mirror is `c100167`, from earlier.
- **Follow-ups, not done:**
  - The corrector's claim gate matches paths by prefix, so claims on gitignored or worktree paths block it (fails safe).
  - The CORRECTOR_STUCK remedy text still says dirty-tree-triage for BLOCKED_CLAIMED and BLOCKED_OP_IN_PROGRESS.
  - The pre-push gate's 480s budget times out `test-append-event-log.py` under load.

## 2026-09-13 — /ship ora-pm target corrected (PR #198, open)
- `commands/ship.md` ora-pm target was stale: said MANUAL wrangler deploy + health-only verify + crons on Windows Task. Ground truth: ora-pm `ci.yml` auto-deploys on push to main (no concurrency group); `/api/health` is unauthenticated while other `/api` routes 401 without admin auth, so a health hit can't prove a route shipped; Windows Task `ORA PM Crons` Disabled since 08-16 (OI-162), crons on CC fleet `ora-pm-daily-crons` + `ora-pm-monthly-billing` with GH Actions backups.
- New target: gate = PR CI green on merge ref · deploy = merge (wait out in-flight main push run) · post-verify = deploy step ok + served `/assets/index-*.js` changed w/ change-unique string + health 200 + origin/main tip == merge commit · rollback = revert merge commit.
- Isolated worktree `fix/ship-ora-pm-target` off origin/main; preflight CLEAR (first run HEAD_MOVED from a concurrent commit, ship.md untouched); verify-push MATCH d02aec3. https://github.com/ZeOoba/ora-claude-config/pull/198 — needs merge + runtime checkout sync (runtime is on `feat/model-canary-probe-step25`, 48 ahead).

## 2026-09-13 — ora-pm: admin API dark in production since OI-036 (ADMIN_EMAILS never set) — FIXED; expense schema PR #33 merged

- **Symptom:** a test expense saved from the admin UI after merging [PR #33](https://github.com/ZeOoba/ora-pm/pull/33) (expense schema `is_cam_recoverable`→`recoverable` fix) never reached the DB; `expenses` held 0 rows.
- **Root cause (verified):** `adminAuthMiddleware` fails closed with 503 when `ADMIN_EMAILS` is empty (OI-036, `079be5c`, 2026-08-03). Cloudflare Pages production held no `ADMIN_EMAILS` (neither secret_text nor plain_text, confirmed via Pages project API). Every admin `/api/*` call returned `503 "Admin access is disabled: ADMIN_EMAILS is not configured."` — the entire admin console was non-functional in production, independent of the schema bug. Portal/cron/webhooks exempt and unaffected. Gabriel's last Supabase sign-in 2026-08-16 is consistent with this.
- **Fix (Gabriel-approved 2026-09-13):** `ADMIN_EMAILS=ggoldberg@oxfordra.net,egoldberg@oxfordra.net` set as a Pages production secret (both verified to have 0 `tenants` rows); redeployed the already-live commit `6321afd` by re-running CI run 34733280462 (Pages deploys are Direct Upload from CI, so the Cloudflare "retry" API refuses them). Verified: bogus token now gets 401 "Invalid or expired token", not 503.
- **Open:** live end-to-end expense create not yet re-verified; production also has no `STRIPE_SECRET_KEY`/`STRIPE_WEBHOOK_SECRET` secrets (not investigated). Lesson: an app whose tables stay at 0 rows for weeks is a dead-path signal — check the auth gate's env before blaming the payload.

## 2026-09-12 — preflight-shared-checkout: wrong-repo fail-open closed (PR #197, stacked on #193, NOT merged)

- **Defect:** `--paths` never checked against `--repo`. A file dirty in ora-skills gated with `--repo ~/.claude` returned exit 0 CLEAR, both relative and absolute (reproduced in the #196 review). Two further forms: paths inside `~/.claude/.claude/worktrees/<name>` (string-inside, separate checkout), and `--paths .claude` returning CLEAR while 6 nested worktrees held uncommitted work.
- **Fix** ([PR #197](https://github.com/ZeOoba/ora-claude-config/pull/197), branch `fix/preflight-path-containment` @ `e6be957`, 4 commits, 2 files):
  - New **exit 5 OUT_OF_REPO**, ranked just below NOT_A_REPO. A path counts as inside only when its realpath sits under the toplevel AND git's own toplevel for it matches.
  - `RESULT_JSON.out_of_repo_paths` lists `{path, suggested_repo, reason}`.
  - A dirty nested worktree under a directory scope → CONTESTED; clean ones are counted only.
  - `\\?\` spellings are normalized, and `GIT_DIR`/`GIT_WORK_TREE` are scrubbed from git calls.
- **Evidence:**
  - Tests were written first and run red; suite 184/184 with no skips.
  - Live replay: the wrong `--repo` now exits 5 with an ora-skills hint.
  - Independent Opus REFUTE, 3 rounds: REQUEST-CHANGES ×2, then APPROVE-WITH-NITS (nits fixed).
- **Doctrine:** unchanged. CLAUDE.md `0=go · any nonzero=STOP` already fails closed on 5.
- **Open:** awaiting Gabriel's go to merge. Retarget to main after #193 merges. The live `~/.claude/maintenance` copy (from #193's branch) still has the defect until this lands.

## 2026-09-12 — ora-pm release: PR #30 (+ stacked #32) merged to main and deploy VERIFIED on served assets

Gabriel-directed ("MERGE 30 VERIFY THE DEPLOY"), run through /ship L7.
- **Shipped (merge 6321afd on c3d120b):**
  - #30: /reports/actuals and /exports/qb-iif reads are keyset-paged and chunked, and every error is checked. A failed read or unknown property no longer yields $0 actuals or a $0 QuickBooks journal entry. The paging helpers moved to server/lib/postgrest-paging.ts.
  - #32 (merged into #30's branch as 188ed9e): new GET /api/cam/recoverable-expenses computes the CAM recoverable total server-side. The page previously summed a 50-row /expenses page, and its UTC-parse/ET-read year filter moved Jan 1 expenses into the prior year. CAMList gates Calculate on a settled load.
- **Gate:** PR CI run 34732803154 (tests + build on #30 merged into main incl. #31/#33) passed. Both PRs had independent Opus refute passes with no blocking findings.
- **Deploy:** push run 34733280462 passed all steps, including Deploy to Cloudflare Pages (wrangler: https://9059e573.ora-pm.pages.dev).
- **Verified on served assets:**
  - ora-pm.pages.dev bundle changed index-D6se7rE4.js -> index-lU7WOFbf.js. The new bundle contains `cam/recoverable-expenses` (0 before, 1 after) and the new load-error text; the hash URL serves the same bundle.
  - /api/health returned 200. origin/main tip is 6321afd, and no later push run could overwrite the deploy.
  - Not verifiable without an admin JWT: the API routes' behavior (unauthenticated requests get 401 before routing).
- **Race avoided:** ci.yml has no `concurrency` group. #35's deploy run was still in flight when the merge was requested, so I waited for it to finish; an older build finishing last would have silently overwritten this one.
- **Doctrine drift:** /ship's ora-pm target says "MANUAL — no git auto-deploy". False: ci.yml deploys via wrangler on every push to main after tests and build. The skill needs correcting.
- **Rollback:** revert 6321afd on main (CI redeploys c3d120b's tree).

## 2026-09-12 — ora-pm admin-form schema drift fixed (PR #34 merged) + tenant email/422 display (PR #35 open)
- PR #34 (merged 44a9102, then #33 at 35eb2c3; main CI green, 558 tests on combined main): Property/Tenant/Payment insert schemas now accept the admin forms' nulls (.nullish), add payments.check_number (was silently stripped), .strict() per OI-041; manual POST /payments no longer accepts stripe_payment_intent_id or ach_stripe (forged PI id would occupy payments_stripe_pi_uniq); properties.zip optional per 0005.
- PR #35 (open, not merged): TenantForm email check now matches server zod .email() (copied regex, parity-tested; zod import would add 54 KB); src/lib/api.ts rendered 422 fieldErrors as "[object Object]" on every admin form — now "field: msg".
- Cloudflare Pages served-asset deploy of #34 NOT independently verified.

## 2026-09-12 -- Runtime CLAUDE.md doctrine fork found and closed: PR #196 promotes 2 stranded triage refinements, exception-scan clause dropped

Gabriel-directed investigation ("investigate further", then "proceed with all recommendations").

**Finding: the live runtime's CLAUDE.md had forked from origin/main.** The whole content delta was one dirty-tree-triage commit, `b777625` (2026-09-11), plus its rules.md companion `607a2d0`. Both sat only on the stale runtime branch `feat/model-canary-probe-step25`. They made three changes: (1) line 35, the Outlook per-exit-code procedure relocated to a rules.md §2 pointer (R24-4); (2) line 78, a shared-checkout gate rule telling sessions to run `maintenance/preflight-shared-checkout.py`, a script absent from main; (3) line 51, the `automation-health-monitor` exception-scan clause. A reconciliation onto main (OI-249) would silently revert all three, including a gating rule sessions currently follow.

**Closed:**
- **PR #196** (stacked on #193, which ports the preflight script): promotes lines 35 and 78 plus the rules.md §2 hunk, byte-identical, and leaves line 51 off. Merge #193 first. An independent Opus review APPROVED the content on all 10 mechanical checks. It REJECTED the first commit message on D1–D5; all five were corrected before push.
- **Runtime commit `876b9b3`** (pathspec, NOT pushed): removed line 51 from the live CLAUDE.md, restoring it byte-identical to origin/main. preflight-shared-checkout.py returned CLEAR after the prior repo-housekeeping claim expired. A first run returned CONTESTED, and I waited rather than forcing. Words 1,817 -> 1,810 (40 headroom).
- **Orphaned worktree** `worktrees/claude-md-tiebreak` and branch `fix/claude-md-exception-scan-tiebreak` (0 unique commits): archived to `_archive/2026-09-12_orphaned-worktree-claude-md-tiebreak/` (patch + restore README), then removed.

**Correction recorded:** the clause was NOT unreviewed. Gabriel approved it in-turn 2026-09-06, and b777625 records an independent review APPROVED; the 2026-09-07 review rejected only a commit message. It was dropped on Gabriel's 2026-09-12 ruling as redundant: tenant-intelligence v1.1's description already routes "fleet health to automation-health-monitor". A draft message of mine claimed otherwise and was caught by the reviewer before it landed.

**Process gap surfaced:** a dirty-tree-triage pass that "lands what's already in effect" commits governance edits onto whatever branch the runtime is on. When that branch isn't main, doctrine forks silently. This happened twice here (`b777625`, `607a2d0`).

**Follow-ups:** the four line-78 wording gaps are listed in PR #196 (exit 2 omitted, `--since` optional, `--repo` unmentioned, rules.md §14 silent on the script). OI-247 tracks my stale 2026-09-07 repo-housekeeping claim on CLAUDE.md, which is now moot.

## 2026-09-12 — Why dispatch-skip.json stopped updating after 09-08 (investigation, report-only)

**Producer:** LAMS `automation-health-monitor` (`5 11 * * 1-5`) Step 0.08 runs `dispatch-skip-probe.py --json-out _state/dispatch-skip.json`. Last write 2026-09-08 11:19:48 ET. It was a carve-out, so it was NOT paused 09-07→09-11.

**Per-run evidence** (run session records, transcripts and Desktop `main.log`):
- **09-07 and 09-08:** probe called, file written. 09-08's Notion publish failed ("workspace has used all of its free blocks").
- **09-09** (`local_2d8ae630`): run executed, 0 probe calls; it improvised `ahm_probe_20260909.py` instead. Desktop Commander disconnected mid-run at 11:17/11:19. Run dominated by the Notion block-quota failure.
- **09-10** (`local_e59d1b67`, 42 min): 0 probe calls. It derived "no throttling" from `Select-String` on main.log (the method its SKILL.md says must not be restored). It spent the run moving 20 old Automation Health pages to the archive (does not free blocks). It rewrote its own 105 KB SKILL.md at 13:28 (change not diffed; no git history for LAMS SKILL files).
- **09-11** (`local_853cf6e7`, 4 min): 0 probe calls; hit the quota and fell straight to the email fallback.
- **09-12:** Saturday, not scheduled.

**Root cause:**
- **Proximate:** the model skipped a mandated deterministic step on three consecutive runs. The LLM run is the only thing that ever writes this file.
- **Contributing:** (1) Notion workspace block quota exhausted since ≤09-08, which hijacked each run's attention. The quota blocks ALL new-page creation workspace-wide; in-place edits still work. (2) A 105 KB SKILL.md.

**Forward risk:** the Cowork VM cannot mount C: since 2026-09-10 21:54. `startVM failed: Claude couldn't connect your C: drive to its workspace ... Reinstalling won't fix this` recurred 8 times through 09-12 16:21, and bash inside the VM fails `failed to mount /mnt/.virtiofs-root/shared/c/...`. The next run (Mon 09-14) may be unable to touch local files at all.

**Correct detection:** state-freshness-probe (branch `feat/freshness-probe-pause-record`) keeps this file STALE because its producer was not paused.

## 2026-09-12 -- Preflight gate committed + hardened; stale-owner reporting; OI-249 port branch; isolated-commit foreign-file rule

- **Preflight gate is now in git:** `maintenance/preflight-shared-checkout.py` and its tests, untracked everywhere since 2026-09-10 (author session b708ef7f), landed as `bf41aca` on `feat/model-canary-probe-step25` with Gabriel's in-turn authorization. Five independent Opus review rounds each surfaced false-CLEAR paths, all fixed with pinned tests: C-quoted non-ASCII porcelain names, subdirectory `--repo`, junction/8.3 spellings on repo and provenance, 8-char session-prefix matching, never-raise `_git`, and `--since` validation.
- **Stale-owner reporting (`c9f2624`):** ownership records older than a file's last commit are shown as STALE, not as live owners. Files whose only other owners are stale still CONTEST; `--accept-stale <path>` clears them after the caller checks `git diff HEAD`. Auto-discounting was rejected because review reproduced a false CLEAR through a partial commit (`isolated_commit.py` single-hunk). The real fix, per-touch blob hashes in `commit-provenance-recorder.py`, is filed as **OI-290**.
- **isolated-commit skill (`ora-skills` `0220ccf`):** new "Foreign untracked files" section covering attribution, snapshot-before-edit, user authorization, and crediting the author session. It passed three review rounds. The post-commit hook synced the skill to the plugin store and queued it in PENDING_REIMPORT.md.
- **OI-249 + preflight on main:** branch `feat/oi249-corrector-to-main` (worktree `worktrees/oi249-to-main`) carries `d7e6bdb` and `bbe2b9e`, file-level ports byte-identical to the reviewed branch blobs. Tests against main's tree: 55/55, 63/63, 98/98. **Push blocked** by the pre-push hook-tests gate on `test_scheduled_task_run_guard.py` (`ora-ground-truth-auditor` unguarded Notion side effect). The same failure reproduces on untouched `origin/main` 7bdd5ef, so it is pre-existing; PR #192 targets it. No override token was minted, pending Gabriel.
- **Concurrent context:** session 97171ad9 (unattended) holds a whole-repo `repo-housekeeping` claim for a Gabriel-approved dirty-tree triage and a planned merge-forward. SendMessage could not reach it. My commits were pathspec-scoped to my own files.

## 2026-09-12 — state-freshness-probe judges stale outputs against the durable pause record (branch, not yet live)

**Why:** after the 09-07→09-11 pause ended, `state-freshness-probe.py` reported 5 [STALE] with 0 pause-explained. It only knew LIVE pauses, so `ora-task-integrity-guard` STEP 2.95 would alarm daily on pause-frozen outputs.

**Landed on branch `feat/freshness-probe-pause-record`** (worktree `.claude/worktrees/freshness`), stacked on `feat/pause-aware-health-checks` + `feat/land-rev24-pause-awareness`. Commits `2dd9c9d` → `4f01c1b` → `9e11096`.
- **Declared producer map, not inference:** `PAUSABLE_PRODUCERS` lists 4 files, each with a cited writer. Only declared files can be excused by the record, via the MIN overlap across their declared producers.
- **Live pause:** it excuses a declared file only if every declared producer is disabled now.
- **Invalid declaration** (producer missing from a registry): no excuse of any kind.
- **Undeclared files:** keep the original live-pause rule.
- **Cadence overrides:** weekly hygiene logs 192h; weekday producers 84h.
- **Tests:** 14.

**Refute history:** 3 adversarial passes. The first killed inferred attribution (native scripts outside maintenance/, case, two-hop chains, non-ORA/.vbs tasks, empty scheduler read, carve-out excused by a live pause). The second found an invalid declaration falling back to the live excuse. The third approved.

**Live result** (worktree code on live data, read-only): 26 ok, 1 pause-explained (`sofr-supersede-status.log`), 2 real STALE.
- `ora-nightly-disk.log`: native Windows task, last result 0x40010004.
- `dispatch-skip.json`: producer LAMS `automation-health-monitor` was a pause carve-out that kept running, yet the file has not been written since 09-08 15:19Z. **This is a genuine finding worth investigating.**

**Not live yet:** the shared checkout is claimed whole by session 97171ad9 (dirty-tree triage, preflight CONTESTED), so this was built in a worktree. The live probe still alarms until the 3 branches push after PR #192 merges (Gabriel: wait, no override) and land on main.

## 2026-09-12 — CORRECTION: OI-273 resume cannot be fixed by permission mode; attended resume only

Correcting the same-day OI-273 entry. The 09-11 resume run's Desktop session record (`claude-code-sessions/.../local_c210fc02-....json`) shows `"permissionMode": "bypassPermissions"`, `"alwaysAllowedReasons": []`, and the run still blocked on every `update_scheduled_task` call. The approval prompt sits above both the settings.json allow list and bypass mode. register-scheduled-task v2.23's "(b) set the resume task's permission mode in the Desktop UI" option was therefore wrong and has been removed (`ora-skills` commit on PR #53). **A scheduled resume must be attended.**

Also measured: TaskScheduler shows `ORA Fleet Pause-Resume Guard` ran 09-11 at 14:20 ET, then logged nothing until event 332 at 21:26 ET. No run fell in the 20:01–20:45Z resume window, and the 20:20 ET slot never launched. `find_incomplete_resumes()` is a slow backstop, not a timely alarm.

## 2026-09-12 — OI-273 root-caused and fixed; lid-close watch; Rev 24 files landed; commits staged for main via PR (OI-249 friction)

**OI-273: RESOLVED.** The 09-11 resume did not crash. The Desktop scheduled-task runner never auto-approves `update_scheduled_task` unattended (`Not auto-approving ... no suggestions on request`; ignores the settings.json allow rule). The run blocked on a prompt from 20:02Z until opened at 20:28Z, approved 6 calls, blocked on call 7, and still reported `succeeded`. Its marker call also lacked the required `--fleet`. Claude Code docs: no SKILL.md/MCP field pre-approves tools; permission mode is Desktop-UI only.
- **Fixes:** `pause-resume-guard.py` `find_incomplete_resumes()` (`~/.claude` `79cd1e8`, +7 tests), hardened in `8d7f186` after review: naive/epoch `lastRunAt`, and a fail-open wrapper so the check can never crash the native guard (+2 tests). register-scheduled-task v2.23 requires an attended resume or a UI-set permission mode (`ora-skills` `d8ce703`, nit `5102dca`).
- **Stale marker:** completed 38/38 after verifying all 38 ids enabled; `find_stalled()` = [].

**Lid-close watch:** ora-health-guard v1.13 A.0b-2 (`1e6dc71`) reads LIDACTION via `powercfg /qh`, because the setting is hidden and `/query` prints nothing. AC ≠ Do nothing → `LID ACTION REGRESSION` FAIL. Live value is still 0x1 (Sleep): **Gabriel has not yet run the setting**, so the check FAILs until he does, by design.

**Rev 24 landed:** session fd011007's `fleet_pause.py`, its test, `state-freshness-probe.py`, `fleet-deadman.ps1` and the integrity-guard STEP 2.95 were live since 09-10 but uncommitted. Committed as authored (`7199c53`) after review.
- **Review finding, fixed in `cc1fd72`:** an unbounded resume horizon was a fail-open. LAMS holds an enabled one-time task dated ~2027-08, so a real LAMS mass-disable would have silenced fleet-deadman for a year. Now a resume must fire within 14 days, in both Python and PowerShell.
- **Still open:** `state-freshness-probe.py` sees only LIVE pauses, so STEP 2.95 will alarm on 5 pause-frozen outputs until they refresh.

**OI-249 friction:** commits are replayed onto fresh worktree branches off `origin/main` via cherry-pick, each verified with the full tests and `check-branch-point --expect N`.
- **Branches:** `feat/pause-aware-health-checks` (4 commits), `feat/land-rev24-pause-awareness` (2), and `ora-skills` `docs/register-scheduled-task-v2.23` (3 commits, **pushed; PR ZeOoba/ora-skills#53 open**).
- **Push blocked by a PRE-EXISTING gate failure:** `test_scheduled_task_run_guard.py` (ora-ground-truth-auditor backlog) fails identically on untouched `origin/main` 7bdd5ef. Another session's PR #192 fixes it and is OPEN (bot check only). No override minted. The merge-forward corrector itself belongs to session 5b055082 and was untouched.

## 2026-09-12 -- ora-pm DEPLOYED: delinquency-check fails closed when payments feed absent (OI-278)
- Trigger: the 2026-09-12 Ground-Truth Audit found `payments` has 0 rows and all 139 `ar_ledger` rows have total_paid=0. `/delinquency-check` had posted 68 $50 late fees ($5,150) on that artifact data. [FORECAST] It would have posted 139 more on 2026-10-05.
- Shipped: ZeOoba/ora-pm#26, squash `fa72f52`. The liveness probe requires >=1 qualifying payment (ar_ledger predicate: check/wire/other, or ach_stripe succeeded) dated within [today-45d, today]. If absent: 0 fees, `payments_feed_absent: true`, and a "PAYMENTS FEED ABSENT" email even at 0 delinquents. A probe error returns 500 before any insert. Live-feed behaviour is unchanged.
- Review: two Fable adversarial passes. The first found a Critical issue (a failed/pending ACH row lifted the guard), fixed in 90af77f. The second approved, with a mutation check confirming.
- Authorization: Gabriel approved merge+deploy in-turn 2026-09-12 (decision form).
- Verification: CI run 34722765640 green, including "Deploy to Cloudflare Pages". `wrangler pages deployment list` shows Production `537cfa66` with source `fa72f52`. `GET /api/health` returns 200.
- Open: the 68 already-posted fees are untouched (no decision yet). Liveness is portfolio-wide, so one qualifying payment re-enables fees for all leases. /ship's ora-pm target text is stale: CI auto-deploys on push to main, not a manual wrangler run.
- Rollback: redeploy Cloudflare Pages deployment prior to `537cfa66`, or revert `fa72f52` on main.

## 2026-09-12 -- Merge-forward corrector: blocker diagnostics, unsynced-streak escalation (3412434, 9df2954)

- **Trigger:** the daily `ora-checkout-merge-forward` run returned BLOCKED_DIRTY_OVERLAP. git's LF->CRLF warnings used up the 500-char `detail` before any blocking file was named, and nothing tracks how long the corrector has been blocked.
- **Landed on `feat/model-canary-probe-step25`, not pushed:** `3412434` adds `blocked_paths`, the `--state-file` streak counter (`consecutiveUnsynced`), weekly `CORRECTOR_STUCK` at 7+ runs, and the SKILL.md event-log python path fix. `9df2954` adds the daily email once the streak reaches 14 runs (then every 7), a 72h `lastRun` staleness flag, and `.tmp` cleanup. Tests pass 55/55 and 63/63. Each commit got an independent Opus review with PASS.
- **Finding, OI-249 is branch-only:** `checkout-merge-forward.py`, its tests, and the task are NOT on `origin/main`. They exist only on this never-pushed branch, now 37 commits ahead of upstream.
- **Finding, preflight gate is untracked:** `maintenance/preflight-shared-checkout.py` and its test, which CLAUDE.md requires before every shared-checkout edit, are committed on no branch. They are untracked WIP from session b708ef7f (2026-09-10). This session added an advisory LOCAL-ONLY check to them (61/61 tests) but left them uncommitted pending Gabriel.
- **Premise corrected:** "a restore from `_scheduled_tasks_backup/` would silently undo changes" is false. `guard.ps1` restores from backup only when the live copy is ABSENT, and refreshes backups from live daily. Of 21 current live/backup differences, 17 are line-ending only and 4 are same-day live edits waiting for the 07:05 sync. No parity checker was built.

## 2026-09-12 -- OI-287 filed CLOSED-on-arrival (duplicate of same-session xref-probe fix)

`ora-ground-truth-auditor`'s 2026-09-12 run independently allocated OI-287 for the
`session-context-xref-probe.py` search-root gap already fixed earlier this session
(see the prior entry above, "session-context-xref-probe [XREF-MISSING] false alarm
fixed"). Rather than let it sit as a live-looking open item and risk re-work by the
in-progress `fix/ground-truth-remediation-2026-09-12` remediation pass, filed it
directly into open-items-tracker-history.md as CLOSED, citing the existing fix and
verification (probe re-run exit 0, doctrine probe re-run clean). No new code changed;
tracker-only.

Also confirmed while checking: `worktrees/gtr-remediation` has genuine live
uncommitted WIP (modified `ora-ground-truth-auditor/SKILL.md` + a new remediation
plan doc) -- another session is actively working the rest of today's digest batch
(OI-278..OI-286, OI-288) there. Left untouched; flagged to Gabriel rather than
duplicated.

## 2026-09-12 -- event_log.md.lock swept into git: .gitignore gap from PR #172 closed (PR #191, 7bdd5ef)

memory-commit-sweep.py committed `memory/event_log.md.lock` (9ce0923). The sweep behaved correctly: PR #172 added the permanent msvcrt lock sidecar and renamed the tmp-append scratch file to `.tmp-append.<pid>.<ns>` without touching .gitignore, so the lock was unignored and the exact-name tmp-append rule stopped matching.

Fix (PR #191, merged 7bdd5ef): .gitignore ignores `event_log.md.lock` + `event_log.md.tmp-append.*`; new `hooks/tests/test-memory-sidecar-hygiene.py` derives sidecar names from append-event-log.py source and fails on any unignored or tracked one. Red before, green after, 6/6 mutants red; 2 independent opus-5 reviews (1 changes-requested, fixed; 1 approved).

Runtime checkout: c27a9ec untracks the lock on feat/model-canary-probe-step25; `.git/info/exclude` bridge line (dated 2026-09-12) must be REMOVED once that branch merges forward from main.

Pushed with a Gabriel-approved one-time allow-hook-test-failure override: origin/main was already red on test_scheduled_task_run_guard.py (ora-ground-truth-auditor detector false positive, from #190). Spun off as task_2a64ba39. Lesson: a PR that adds a sidecar next to a tracked file owes its .gitignore line in the same PR.


---

*Entries at and before “2026-09-12 -- event_log.md.lock swept into git: .gitignore gap from PR #172 closed (PR #191, 7bdd5ef)” rolled over 2026-09-17 to [_archive/event_log_2026-09-17.md](_archive/event_log_2026-09-17.md) per memory-policy.md's rollover rule.*
