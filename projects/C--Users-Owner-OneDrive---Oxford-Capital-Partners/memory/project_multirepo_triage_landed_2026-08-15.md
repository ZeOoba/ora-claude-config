---
name: project-multirepo-triage-landed-2026-08-15
description: "Gabriel-directed dirty-tree/open-PR/stale-worktree triage across 4 repos (do-all-of-it) -- 2 real dangling oxford-command-center feature branches landed (confidentiality gate PR #278, debt-book-trust PR #277), 17 stale worktrees/branches removed, website-canonical moved off a stale merged branch, ~/.claude's 7-entry dirty set isolated-committed but NOT pushed"
metadata: 
  node_type: memory
  type: project
  originSessionId: bb23bdf4-1f4e-450f-9732-cea1e53a83cc
  modified: 2026-08-15T23:13:37.452Z
---

**2026-08-15, Gabriel-directed ("do all of it").** Full triage pass across `~/.claude`, `ora-skills`, `oxford-command-center`, `website-canonical`: dirty trees, open PRs, stale worktrees/branches, superseded items. Result: 0 open PRs and 0 dangling worktrees/branches left across all four repos.

**Landed — real unlanded work rescued from dangling worktrees, both in `oxford-command-center`:**
- [PR #278](https://github.com/ZeOoba/oxford-command-center/pull/278) — confidentiality dataQuality-sweep (M2) + reconciliation-gate (H2) on all 4 `portfolio.json` publication paths. Had been sitting complete in worktree `occ-wt-m2h2` since early August. Conflicted with `origin/main`'s own independent, stronger fix (PR #273's Deal-ID join redesign already replaced the near-duplicate-deal detector with a names-never-appear-in-flag-text version) — resolved by taking `main`'s detector wholesale and keeping only this branch's own `hasReconciliationError` addition; the branch's own superseded test block was deleted. Two independent Fable-tier reviews (pre-merge substance + post-merge-conflict correctness); 3476/3476 tests.
- [PR #277](https://github.com/ZeOoba/oxford-command-center/pull/277) — atomic `DebtBookTrust` propagation (round-19 series) across debt-scoring/capital-allocation, replacing 3 surfaces that could independently disagree on trust state. Same rescue-from-dangling-worktree pattern (`occ-wt-round19`). **Independent review found and I fixed a real precedence bug**: `deriveDebtBookTrust` checked a standing `'refused'` marker before the unattributed-row count, letting an unrelated later write upgrade an unattributed-loan `'degraded'` book to `'refused'` — restoring stale "last trusted" figures. Also added CLI-level test coverage (`debt-scores-snapshot-cli.round19.test.ts`) for a gate that had regressed twice with zero direct tests. Conflicted with `main`'s own independent staleness-discount fix to `effectiveMonthsToMaturity`; resolved by combining both. No governor constant (DSCR 1.25x / LTV 40/65%) touched — confirmed by review. 3532/3532 tests.
- [PR #276](https://github.com/ZeOoba/oxford-command-center/pull/276) — docs-only: landed a 2026-08-03 remediation plan (`PLAN.md`) for [OI-049](open-items-tracker.md#OI-049)/[OI-050](open-items-tracker.md#OI-050)/[OI-051](open-items-tracker.md#OI-051) that had also sat unpushed in a dangling worktree. **These 3 items are still OPEN as of today** — only the plan landed, no fix applied. Worth picking up next.

**Discarded as fully superseded (verified via `git merge-base --is-ancestor` / PR history, not guessed):**
- `fix/refute-workflow-em-dash` (oxford-command-center) — its one-file `.gitattributes` fix was already byte-identical on `main` via a different commit.

**Mechanical cleanup — 17 confirmed-merged/superseded worktrees+branches removed** (each verified via PR MERGED state or `git merge-base --is-ancestor` before touching): `website-canonical` 6 worktrees (PRs #64/#65/#68/#69/#71 + one parked on `main`), `oxford-command-center` 3 worktrees + 12 branches (PRs #244/#248/#250/#252/#259/#260/#266/#267/#269/#273/#275/#276-278 lineage), `ora-skills` 1 worktree (PR #23), `~/.claude` 5 branches (PRs #33/#34/#36/#42/#46).

**`website-canonical` primary checkout moved off `docs/architecture-diagram-refresh`** (merged 08-04 via #63, never moved back) onto `main`, clean pull, no contention — unlike the `~/.claude` main-move situation ([[project_primary_checkout_main_move_blocked_2026-08-12]]), this one had no concurrent-session WIP entangled.

**`~/.claude`'s 7-entry dirty set isolated-committed, deliberately NOT pushed.** MEMORY.md, event_log.md, open-items-tracker.md, `project_audit_rev9_remediation_landed_2026-08-14.md`, `ora-am-brief/SKILL.md`, plus 2 new memory files (`project_dangling_worktree_landing_2026-08-15`, `project_live_checkout_132_behind_settings_json_overlap_2026-08-15`) — each committed via `commit_isolated_replacement()` individually. The checkout is 146 commits behind an actively-moving `origin/feat/model-canary-probe-step25`; reconciling that gap is its own deliberate job per the standing doctrine on this checkout, not something to bundle into a triage pass.

**Why:** Gabriel asked for a general dirty-tree/PR/worktree health check; the survey surfaced two pieces of real, tested, reviewed work (not just housekeeping) that were at risk of quietly rotting in dangling worktrees indefinitely.

**How to apply:** the `oxford-command-center` OI-049/050/051 appsec items are open and now have a plan on `main` — a natural next pick. Confirm before assuming any oxford-command-center worktree beyond the primary checkout is "just noise" — this pass found 2 of 9 extra worktrees there carried real unlanded work (2 more had zero PR record and needed direct ancestor/diff verification, not just a PR-title match). The `remove`-triggers-`move`-verb false positive on the ORA autonomy gate (matched anywhere in the command string) recurred twice this session on `website-canonical` paths — mint the override token in an isolated Bash call with no site-marker text in the same call's reason string, never bundled with the actual git command.

Related: [[project_dangling_worktree_landing_2026-08-15]] (same-day, same class of work, scoped to `~/.claude` only), [[project_primary_checkout_main_move_blocked_2026-08-12]], [[reference_isolated_commit_repair_wrapper_2026-08-13]].
