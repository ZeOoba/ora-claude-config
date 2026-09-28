# R27 Phase 0 baseline: 2026-09-22

Plan: `~/.claude/docs/plans/2026-09-22-setup-remediation-plan.md`. Everything later phases must not regress against.

## 0.1 Rollback points (local annotated tags, NOT pushed)
| Repo | Branch | Tag `pre-r27-2026-09-22` → | Dirty files |
|---|---|---|---|
| ~/.claude | feat/model-canary-probe-step25 | b394e1c | 125 (116 existing snapshotted to `claude-dirty-snapshot.tgz`, 31.6MB; 9 are deletions, recoverable from the tag) |
| ora-skills | main | 275bb39 | 0 |
| oxford-command-center | main | f5ec375 | 1 |
| ora-pm | main | 35669b8 | 2 |
Warehouse DB: `oxford-command-center/data/warehouse/archive/finance.sqlite.pre-r27-2026-09-22` (sqlite backup API, integrity ok, 46 tables, git-ignored).

## 0.2 Suites
| Suite | Result |
|---|---|
| hooks/tests (57 scripts) | **57/57 pass** (`tests-hk.tsv`) |
| maintenance test-*.py (41) | **41/41 pass** (`tests-maint.tsv`) |
| oxford-command-center vitest | 5167/5168. The 1 failure (`briefing-pdf-narrative`) was a load timeout; **passes 11/11 in isolation** |
| oxford-command-center typecheck | pass |
| ora-pm vitest | 616/619. The 3 failures (`pdf-extract`) were load timeouts; **pass 3/3 in isolation** |
| ora-pm tsc | pass |
| frontmatter_sweep | 72 dirs, 0 findings |
| mirror check | clean (rc 0) |
| doctrine-integrity-probe | rc 0. CLAUDE.md 1,843w (WARN floor); 4 aging session-context tombstones (lines 7, 12, 14) |
| governor-drift-probe | rc 0 |
| session-context-xref-probe | rc 0 |
| memory-integrity-probe | rc 1: 1 known issue (the event_log OI-270 anchor, left deliberately per R26-3) |
| state-freshness-probe | rc 1: 8 ok / 25 stale / 0 pause-explained (see known issues) |
| setup-self-audit | ATTENTION: 0 critical / 3 warn |

Known suite constraint: the JS suites time out when run concurrently. Run them serially in later gates.

## 0.3 Fleet snapshot (`registries/`, `fleet-status.txt`)
CC 55 tasks / 6 enabled · LAMS 29 / 1 enabled. The deliberate pause runs to 09-28.

## 0.4 Capability ledger
`r27-capability-ledger.csv` (268 rows) + `-summary.md`. Step breakdowns: HUBSPOT_RECONCILE ≈43 steps / 5 tasks · CC_MIRROR ≈20 / 3 · HEALTH_GUARD ≈14+ (Blocks A/B not fully enumerated).
**Gaps to close before Phases 3/4:** full enumeration of HEALTH_GUARD Blocks A/B; hook capability lines were inferred from matcher/filename, so read each hook's docstring before Phase 4.

## 0.5 Hook latency (idle machine; `hook-latency.tsv`)
Blocking per Bash call: **Pre 538ms + Post 784ms = 1,323ms median** (catch_up_main 377 · deploy-check 139 · eos-gate-sentinel 268; fleet-session-hook 353ms async). Under load (4 suites running) the same chain measured 7,438ms.
The deploy-check hook exits rc=1 on every non-deploy Bash call (non-blocking, but noisy).

## Known issues at baseline (pre-existing; not introduced by R27)
1. **Off-machine dead-man chain is failing to complete.** Windows tasks `ORA Fleet Dead-Man`, `ORA Fleet Heartbeat Push` and `ORA Claude Desktop Wake-and-Launch` last result `0xC000013A` (killed mid-run) at 09-22 09:37. The `ORA Headless - *` trio got the same result on 09-21. `fleet-deadman.log` is 57h stale. Highest-priority item surfaced by Phase 0.
2. state-freshness-probe credits 0 stale outputs to the pause: it reads LAMS as "all disabled, NO resume queued", because the LAMS re-enable is an OI-340 handoff, not a registered resume task. Most of the 25 are ~198h (the 09-14 pause start). `ora-nightly-disk.log` is weekly, so it is a false STALE against the 48h limit.
3. `ORA PM Crons` Windows task Disabled since 08-16 (rc 0x8007052B). Confirm intent.
4. `ORA Command Center - Mirror Deploy` last rc 0x41306 (task terminated).
5. setup-self-audit: 8 builtin skillOverrides keys unresolvable (expected for builtins).
