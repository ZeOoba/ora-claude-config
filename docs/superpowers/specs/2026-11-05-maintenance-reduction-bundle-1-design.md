# Maintenance Reduction, Bundle 1: Stop the Bleeding (design)

- **Date:** 2026-11-05
- **Status:** Design approved section by section by Gabriel (brainstorming session 2026-11-05); awaiting spec review
- **Lane:** L5 research → L3/L4 implementation per PR
- **Repos:** ora-claude-config (`~/.claude`), oxford-command-center (OCC), ora-skills, Website (`website-canonical`), AAOS
- **Objective:** cut recurring owner maintenance time. Adding capability is out of scope.

## 1. Context and evidence

Five read-only surveys (Sonnet Explore, one per repo, against `origin/main`, 2026-11-05) found about 3,300 commits across the five repos in 90 days. The main driver is that Claude sessions keep generating more work for each other: fix-the-fix chains, extra review rounds, wording-only version bumps, and amendment loops on systems that nothing uses. Content volume is not the problem. The surveys also found two cross-repo patterns:

1. **Hand-maintained counts and registries drift**, in all five repos. Examples: the README counts are wrong in every repo; the OCC CLAUDE.md says the gate has 11 steps when `package.json` has 12; `GATED_SKILL_SUITES` and `test:site` are hand-written lists.
2. **Unused systems still get maintenance.** AAOS had no live seam traffic after 2026-08-16. Both of its scheduled tasks have been disabled since September (verified against the live registry). It still received about 60 commits in 90 days, and CI failed on 7 of its last 12 runs.

Hour estimates come from commit counts multiplied by an assumed 15–20 minutes per commit. They are directional and were not measured. Bundle 1's estimated saving is 11–18 owner-hours/month directly, and it also reduces the follow-up commits that drive the costs in later bundles.

### Ranked backlog (bundles after this one get their own spec cycle)

| # | Sub-project | Est. hrs/mo | Status |
|---|---|---|---|
| 1 | Freeze AAOS | 3–6 | **This spec** |
| 2 | Derive counts and registries; stop hand-maintaining them | 8–12 | **This spec** |
| 7 | Stop-when-unused doctrine | multiplier | **This spec** |
| 3 | Commit-noise diet: split `event_log.md` per day, throttle `fleet-heartbeat.json`, auto-expire `status.json`, refresh `ownership.json`, prune branches and worktrees (OCC has 235 remote branches; about 25 stale worktrees under `~/.claude`), probe-suppressor allowlist with expiry | 9–13 | Next spec |
| 4 | Collapse the ora-skills re-upload loop into a hash manifest | 8–12 | Later |
| 5 | acquisition-underwriting SKILL.md becomes a thin router | 6–10 | Later |
| 6 | Single-source boilerplate: Website partials and CSP externalization; scheduled-task spec templating | 7–11 | Later |

## 2. Component A: AAOS freeze

**AAOS repo (one PR):**
- Add a `FROZEN` banner at the top of `README.md`. It states the evidence (last seam traffic 2026-08-16; both tasks disabled since September 2026) and the revival trigger: a real cross-surface task requirement, followed by an un-freeze ADR.
- Add `docs/adr/0007-freeze.md`. It records the decision and evidence, marks AMD-0003, AMD-0004 and AMD-0006 "suspended by ADR-0007", and lists each `amd/*` branch name with its head SHA.
- Delete the 33 `amd/*` remote branches. The SHAs are recorded in ADR-0007 first, so the work stays recoverable. Deleting remote branches is outward-facing, so it needs Gabriel's confirmation when the PR runs.
- Change the CI workflow trigger to `workflow_dispatch` only. The Python-version chase (CPython-oracle timestamp tests) is not fixed, because it doesn't matter while the repo is frozen.
- Delete the hardcoded test counts from the README.
- **No other deletions or cleanup.** The heartbeat chain, the stray `docs/adr/*.py`, `docs/_task-reports/` and the archive all stay as they are. Cleaning up a frozen repo would be exactly the churn this bundle is meant to stop.

**`~/.claude` (task retirement, via the `register-scheduled-task` skill only):**
1. Run the registry single-writer check (`_state/registry-membership.log`).
2. Run `delete_scheduled_task` for `ora-aaos-expire-leases` and `ora-aaos-publish-contracts`. The CC/MCP retire order is registry first, which leaves the folders in place.
3. Move both folders to `scheduled-tasks/_archive_2026-11-05_aaos-frozen/`.
4. Append a "do NOT re-register, see AAOS ADR-0007" entry with `maintenance/append-event-log.py`.
5. Check `ora-weekly-hygiene` for AAOS scope text. Change it only if it would fail without the retired tasks.

## 3. Component B: derive, don't hand-maintain

The rules:
- Delete counts written into prose.
- Lists that only code reads are auto-discovered.
- A list that has to exist as data is checked by a test or a `--check` step.

| Repo | Change | Mechanism |
|---|---|---|
| `~/.claude` | Remove the 14 count and verification stamps from `README.md`. Link to the weekly-regenerated `system-inventory.md` for current numbers. | Delete only |
| ora-skills | (a) Delete the README counts. Generate the skill inventory table from SKILL.md frontmatter with a new `tools/gen_readme_inventory.py` (`--write` / `--check`). The existing #175 README-inventory gate switches to the generator's `--check`. (b) Replace `GATED_SKILL_SUITES` with discovery of every `*/tests/test_*.py` under skill dirs, excluding `_archive/`. An exclusion becomes a module-level `CI_EXCLUDE = "<reason>"` inside that test file, and `EXCLUDED_SKILL_SUITES` is removed. | 1 generator; `tools/skill_ci_gates.py` gets simpler |
| OCC | Remove the gate step count and the step list from CLAUDE.md and point to `package.json`. Add one vitest test that asserts the set of `gate:ci` steps equals the `gate` steps + {build, bundle} − {reconcile}. That intentional divergence is encoded in the test, and any other divergence fails it. | 1 test; no financial-decision code is touched |
| Website | Replace the 30-file `test:site` list in `package.json` with a glob. Delete the README test count. Remove the stale `?v=N` query strings from source HTML; `stamp-asset-versions` already restamps them. | `dist/` must be byte-identical before and after |
| AAOS | Covered in Component A | — |

**Deliberately excluded:** generating `settings.json` hook wiring (an existing test already checks the wiring, and generation is high blast-radius for 1–2 h/mo); `status.json` and `ownership.json` (state ledgers, moved to Bundle 3).

## 4. Component C: stop-when-unused doctrine

This goes in one place only: a new section in `projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/reference_engineering_os_done_bar.md`. CLAUDE.md already points to that file, so CLAUDE.md does not change.

- **D1. Follow-up fixes go on the parent PR.** Fixes from a review round, QC pass or residual commit to the same branch as the original change. They never open a new PR. If the parent PR has already merged, the follow-up PR must name the parent in its title.
- **D2. Usage evidence before maintenance.** Before amending, re-tuning cadence, or adding tests or docs to a system, scheduled task or skill, cite usage evidence from the last 30 days (task runs, seam traffic, invocations, page reads). With no evidence, propose freeze or retirement instead. Exempt: security and confidentiality fixes, and anything Gabriel explicitly requests.
- **D3. Small edits wait for the next real change.** A wording-only or changelog-only edit to a SKILL.md or task spec gets no version bump or PR of its own; it ships with the next behavior change. Exempt: factual errors in doctrine, and anything a gate blocks.

## 5. Sequencing

Seven steps, one PR (or one isolated commit) each:

1. Doctrine (Component C), committed to `~/.claude`.
2. AAOS freeze PR.
3. Retire both AAOS tasks in `~/.claude`. This must come after step 2 so the event-log entry can cite ADR-0007.
4. ora-skills inventory generator and suite discovery.
5. OCC CLAUDE.md edit and gate-divergence test.
6. `~/.claude` README counts. Same checkout as steps 1 and 3, so it is a separate isolated commit made after both.
7. Website, last: run the `dist/` byte-identical check, preview the deploy, then deploy to prod **only on Gabriel's in-turn confirmation** (Invariant 2; a merge to `main` counts as a deploy).

Steps 2, 4 and 5 are in different repos and can run in parallel.

## 6. Gates and verification

- Every PR passes its repo's existing gate: `bash tools/run_suite.sh` (ora-skills), `npm run gate` (OCC), `npm run verify` (Website), and hook tests plus native pre-push (`~/.claude`).
- New checks are written test-first:
  - Hand-edit the generated inventory and confirm `gen_readme_inventory.py --check` exits nonzero.
  - Add an unlisted `test_*.py` and confirm discovery runs it.
  - Make `gate` and `gate:ci` diverge and confirm the vitest test fails.
- Shared `~/.claude` work (steps 1, 3, 6): run `preflight-shared-checkout.py` first, claim `repo-housekeeping` with `--paths`, and never `git add -A`.
- Review: pr-review-toolkit code-reviewer for each PR. `tools/skill_ci_gates.py` is a CI gate, so it also gets an adversarial-reviewer pass pinned to Opus 5.5 before merge.
- Website: a byte-identical `dist/` (hash every file before and after) is the acceptance test, followed by `node scripts/verify-live-csp.mjs` after the deploy.

## 7. Done criteria

- No README.md or CLAUDE.md in the five repos contains a hand-typed inventory count. The check is a grep for a number followed by tests, hooks, skills, agents, steps or suites. It must return nothing, apart from generated sections and the evidence lines in ADR-0007 and the AAOS README banner.
- `GATED_SKILL_SUITES` and `EXCLUDED_SKILL_SUITES` no longer exist. A new skill `test_*.py` runs in CI without anyone editing a list.
- AAOS: the FROZEN banner and ADR-0007 are merged, there are 0 `amd/*` remote branches, CI is manual-only, and neither task id is in the live registry.
- The doctrine section (D1–D3) is present in the done-bar doc.

## 8. Success measure (30 days)

An optional one-time check around 2026-12-05:
- Commits that only fix counts, README or gate lists across the five repos drop to about zero (the baseline is about 15–20 per 90 days).
- AAOS has 0 commits.
- The share of follow-up PRs (PRs that reference a parent PR) drops.

If Gabriel wants the check, register it through `register-scheduled-task`. It is not registered by default.

## 9. Rollback

Each PR reverts on its own. The `amd/*` branches can be restored from the SHAs in ADR-0007. The retired task folders are archived, not deleted, and can be re-registered through `register-scheduled-task` if AAOS is revived.

## 11. Corrections made while writing the implementation plan (2026-11-05, code read against `origin/main`)

These supersede the text above where they conflict:

1. **ora-skills inventory generator: dropped.** `skills_missing_from_readme()` already enforces the README inventory: each skill name must appear in backticks, which is a list checked by code. A generator would add code without removing drift. The only ora-skills README count is "(5 skills)" in a diagram, and it is deleted.
2. **AAOS branches.** There are 3 `amd/*` branches. 33 was the total remote-branch count, which is about 31 once `main`/`HEAD` are excluded. ADR-0007 records the SHAs of every non-`main` branch, and all of them are deleted on Gabriel's confirmation. This is the same count he approved, with corrected scope.
3. **AAOS README counts.** Instead of editing counts in a frozen repo, the FROZEN banner declares the README a historical snapshot whose counts are not maintained.
4. **OCC `gate:ci` vs `gate`.** The actual relationship is `gate:ci` = `gate` − {reconcile, reconcile:noi-crosscheck, warehouse:verify, warehouse:drift} + {build, check:bundle}. The test pins that, and also checks that CLAUDE.md §6 describes every `gate` step, which catches the missing `check:css-tokens`. CLAUDE.md is Architect-owned, so a `status.json` entry with `review_needed: true` comes first.
5. **Website `?v=N`: dropped.** `stamp-asset-versions.mjs` states that source `?v=` values are read by tests and tooling. The Website change becomes `scripts/run-site-tests.mjs`, which enumerates `tests/site/*.test.mjs` minus the 4 files that have their own scripts (enumeration, not a glob, because Node 20 and Node 21+ treat globs differently). The README "list of 25" cell is also updated; the real list had 26.
6. **`ora-weekly-hygiene` needs no change.** Its AAOS references already say to re-derive from the live registry.
7. **Added during execution (Gabriel's ruling after the round-1 refute of ora-skills#206).** Auto-discovery alone lost the old lists' side benefit: a renamed or deleted suite used to fail CI, and now it would silently leave. Gabriel chose an AST-parsed `CI_EXCLUDE` marker plus a new `suite-continuity --base` CI step. A base suite that disappears fails CI unless it moved under `_archive/<skill>/…` or `_archive/<skill>_retired-YYYY-MM-DD/…` (paths *added* in the PR only), or a commit carries `Suite-Removed: <path>`. As a result, `tools/skill_ci_gates.py` grew instead of getting simpler (§3 said simpler). The trade is about 120 lines for keeping the "a suite can't silently vanish" guarantee.
8. **Task 3 outcome.** The two AAOS tasks are ratified for retirement but not executed. `delete_scheduled_task` is blocked by the MCP delete gate's store-scan timeout (OI-396), so per Gabriel's ruling they stay `enabled:false` and are recorded in `maintenance/_state/retire-pending.json`. AAOS#38/#39 (a concurrent session's late fixes) were closed unmerged on the freeze ruling; their two branches are kept, outside ADR-0007's restore table.

## 10. Out of scope

- GitHub-archiving the AAOS repo (declined).
- Generating `settings.json`.
- Every Bundle 3–6 item listed in §1.
- Fixing the Linux case-folding bug in `test_parse_replays.py`. Its exclusion moves to a `CI_EXCLUDE` marker unchanged.
- Any change to financial-decision code, governor constants or `config/*.json`.
