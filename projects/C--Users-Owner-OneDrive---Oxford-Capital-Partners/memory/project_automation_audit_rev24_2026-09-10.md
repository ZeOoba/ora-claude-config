---
name: project-automation-audit-rev24-2026-09-10
description: ORA Automation Audit Revision 24 (2026-09-10) — 15 findings; both fleets under a deliberate bounded pause that masks a Rev-22-shaped frozen-detector cluster; R22-1 closed; CLAUDE.md 26 words from FAIL; both of the audit's own artifact caps applied for the first time.
metadata:
  type: project
---

Revision 24 of the ORA Automation Audit, Gabriel-invoked via `/ora-setup-audit`. Artifact: https://claude.ai/code/artifact/8b29049b-d7a0-4394-a602-d51e52fd21e7 (same URL, continued in place). Supersedes [[project_automation_audit_rev23_2026-09-06]]; folds in [[project-automation-audit-interim-2026-09-09]], which was never published as a numbered revision.

**Four threads, all command-bounded per R22-14, all four completed. 15 findings, 0 delete-candidates, 3 subagent claims refuted on measurement.**

## Three things a future session must know before trusting the artifact

1. **The CC fleet is paused, not broken — and the pause is why ~12 `_state/` outputs look dead.** Disabled 2026-09-07 with a resume task firing 2026-09-11T20:01Z; 63 of 67 tasks disabled. Every frozen detector output froze inside one 21-minute window that afternoon. **This is byte-for-byte the signature R22-3 called a silent-failure cluster.** ⚠️ **CORRECTED during remediation: only CC is paused, NOT both fleets** — LAMS deliberately kept `automation-health-monitor` and `ora-cowork-heartbeat` enabled and runs hourly. The original claim came from reading "63 of 67 disabled" as fleet-wide. **This is no longer a reasoning problem: `maintenance/state-freshness-probe.py` now makes the distinction mechanically** (stale DURING a pause = expected; already stale WHEN it began = finding), so a future pass should run it rather than re-deriving.
2. **Two numbers moved fast and will keep moving.** CLAUDE.md is **1,824w, 26 words from the 1,850 FAIL gate** (Rev 23 measured 1,682w and explicitly planned around "~168 words of headroom" — that plan is dead; arbitration must now relocate, never add). The live `~/.claude` checkout is **84 commits behind `origin/main`, up from 40 the previous day** (OI-249, 3rd recurrence, still on `feat/model-canary-probe-step25`). Re-measure both; do not carry these forward.
3. **The obvious inference about the stale checkout was tested and is FALSE.** Merged fixes are *not* missing from the runtime: `log_liveness.py` is present live, and rotation logic in `eos-telemetry.py` (16 hits) and both `.ps1` writers (7 each) is live **at exact parity with `origin/main`**. The risk is the divergence *rate*, not damage already done. Do not re-derive this as "the fixes aren't running."

## Closed this pass

- **R22-1 CLOSED** — `ora-pm-monthly-billing` and `ora-pm-daily-crons` are present on a live membership diff: **36/36 CC and 27/27 LAMS** match the frozen snapshot. The one live-only id (`ora-checkout-merge-forward`, created 09-09) postdates it. `registry-membership-probe.py` deliberately NOT run, so the pre-drop baseline survives.
- **R23-1 / R23-2 hold closed** — Step 0 and 0b both fully clean for the first time in the series: repo, local mirror and account store agree on all three canaries (`ora-setup-audit` v1.12, `register-scheduled-task` v2.21, `acquisition-underwriting` v4.19), exactly one enabled entry each.
- **R23-9 fully closed** — ~22 candidate trigger pairs checked; **zero** unresolved collisions. First clean routing sweep.
- **Interim 4 of 5 closed** — workspace-pointer WARN, the dead `non_fleet_task_sweep` detector (archived, so it stops re-tripping as a false stopped-writer every pass), both orphaned LAMS spec folders, and `investor-relations` (retired outright, `2b24e9e`).

## Remediation, 2026-09-10 — Gabriel in-turn: "Fix all of the above"

**Shipped and verified:**
- **Retention rules** (`ora-skills` `9568128`, isolated worktree, disjoint-verified, pushed): `loi-generation` v1.9 and `deal-execution` v1.8 gained a 6-entry + ~2,000-char cap; `acquisition-underwriting` v4.20 gained the length cap it was left out of on 09-07, archiving v4.16 to honour its own four-most-recent rule. Cap calibrated on measured entries (127–2,142 chars). Every extraction asserted byte-present in its `versions/` file before removal. **The rule costs ~800 chars per skill up front and bounds growth only thereafter — it is not an immediate size win.** A first run left `loi-generation` at 7 entries against the 6-cap it was introducing; caught before commit. **3 skills are in `_staging/PENDING_REIMPORT.md` awaiting a Gabriel Save-skill click** (plus `disposition-analysis` = 4).
- **`fleet-deadman.ps1` is pause-aware** (R24-3). Structural test — every recurring task disabled AND an enabled future one-time task — never a name match; a fleet disabled with NO resume queued still alarms. Verified against the live condition that caused the false alarm.
- **`maintenance/state-freshness-probe.py` + `_shared/fleet_pause.py` + `_tests/test_fleet_pause.py` (10 passing)** — the probe R22-2/R22-3 specified on 09-05 and nobody built. Wired into `ora-task-integrity-guard` STEP 2.95 with a STEP 3 alarm condition. First run: 13 ok, 12 pause-explained, 1 genuine. **Known limitation, stated in the spec: it is itself a CC-fleet member, so during a total CC pause it does not run — the out-of-band deadman is the only off-fleet witness.**
- **CLAUDE.md 1,824→1,817w** by relocating the Outlook per-exit-code procedure to `rules.md` §2. Plus `disposition-analysis`'s stale H1 (`d6272d9`), clearing a probe WARN (8→7).

**⚠️ Three claims in the published Revision 24 were WRONG and are corrected in the artifact — do not re-report them:**
1. "Both fleets paused" — only CC.
2. "OI-153 still wired into zero tasks" — it IS wired, into `ora-doctrine-integrity-guard` STEP 1 on 2026-09-09. All five interim findings are closed, not four.
3. "R22-4 tracker split still not executed" — it WAS executed; `open-items-tracker.md` is 672,196B with `open-items-tracker-history.md` (271,860B) beside it.

**And one proposed fix was refuted before execution:** R24-13's Desktop Commander dedupe. `settings.json` has **no `mcpServers` key at all** — DC is registered once (`desktop-commander@inline`). The 13 bare allows are legacy PERMISSION entries and permissions do not load tool schemas, so removing them saves nothing; the 4 hook matchers name both namespaces deliberately so the write-guards fire whichever serves. Deleting them would have weakened guard coverage for zero gain. **Fourth measure-the-payload correction in this series.**

## Open, needing Gabriel

- **OI-249 / R24-5 — BLOCKED, and the blocker is the finding.** Gabriel's chosen corrector (`maintenance/checkout-merge-forward.py` + the daily `ora-checkout-merge-forward` task, selected 2026-09-09) already exists and has not run *because the CC fleet is paused*. Run manually this pass: returned **`BLOCKED_DIRTY_OVERLAP`**, tree untouched, exactly as designed. **14 files overlap `origin/main`; 13 are other sessions' uncommitted WIP** (only MEMORY.md was mine) — `hooks/eos-*`, `hooks/lib/claim_work.py`, both rotation `.ps1` files, `event_log.md`, the tracker, two task specs. Committing those is the documented hazard the script refuses by design. **Structural gap now visible: a merge-forward corrector cannot correct a checkout that is permanently dirty**, which this one is with 5+ concurrent sessions. Needs a `dirty-tree-triage` companion pass — Gabriel's call, since it commits other sessions' work.
- **CLAUDE.md — the band has closed.** 1,817w sits AT the 1,700 consolidation floor and 33 words from the 1,850 FAIL gate. Further relocation is NOT mechanical: `tech.md` §3f records that `doctrine-integrity-probe.py` Check 11 **requires** the eight guard names to stay inline, and the probe resolves the subsumed skill names on the tie-break lines — so the obvious candidates are load-bearing. Which whole rule moves down a layer next is Gabriel's editorial call. Concurrent sessions are adding words faster than a relocation pass removes them.
- **`claude-md-management`** — a `false` `enabledPlugins` flag for a plugin that was never installed. Real but trivial; not fixed (settings.json edit, deliberately not bundled with the refuted DC change).
- **R22-4 residual** — the split IS done; what remains is only whether the 672KB live tracker wants a further pass. Not urgent.
- **3 skills + `disposition-analysis` await a Save-skill click** — see `ora-skills/_staging/PENDING_REIMPORT.md`. Gabriel-only.

## Method notes worth keeping

- **Three subagent claims refuted on direct measurement**, all from reading a label or a tail instead of the payload — the same class as R23-8: (a) `stuck-session-watchdog.log` reported as over its 1MB cap is **1,022,997B against a 1,048,576B cap — 25,579B under**, rotation armed and correctly not yet fired; (b) the null-`Procs` error reported as a 30-minute loop is **108 occurrences across 55 days** (~2/day); (c) `tenant-email` / `disposition-analysis` reported unreachable are both `enabled:true` on a live `ListSkills`, and `capex-budgeting`'s absence is the deliberate 2026-08 unpublish. **(c) is the third recurrence** — a Code session's roster is never evidence about the account store. See [[feedback_absence_claims_need_verification_before_building]].
- **The artifact's own caps were applied for the first time.** 85% of it sat outside them: 16 sections/79,865B against a 2-revision cap written into the skill on 2026-09-06, and 109,144B of rev-band against a 48,000B ceiling (per-band cap written 2026-09-07). 14 sections + Rev 20's band rolled to `ora-automation-audit-history.md`; Rev 23/22/21 trimmed in place. **224,613 → 68,284 chars.**
- **A near-miss worth the paragraph:** the first archival run wrote the 14 section bodies through a shell heredoc whose backticks the shell consumed, producing 14 correct headings with **empty bodies** — 74,556B removed from the artifact and not preserved, briefly violating invariant 6. Caught only by verifying the archive rather than trusting the exit code; repaired from a pre-edit backup and re-verified by asserting every body byte-present. **An archive step that is not verified is not an archive step.**
- `config-write-guard` correctly blocked two read-only commands (this session and Thread 2) because an interpreter one-liner named the registry path. Both reworded to the ungated Read/Grep tools; **no override token minted anywhere in this pass**.
