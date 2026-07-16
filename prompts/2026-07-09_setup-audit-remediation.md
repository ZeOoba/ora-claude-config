# ORA Setup-Audit Remediation — Claude Code Master Prompt (v02 FINAL — all decisions ratified)
**Issued:** 2026-07-09 evening chat-surface audit (companion to `memory/project_claude-setup-audit-2026-07-09.md`).
**Save to:** `~/.claude/prompts/2026-07-09_setup-audit-remediation.md`
**Lane:** L1/L2/L3 sequence — announce lane + Dispatch per task. Suggested: subagent-driven-development for Tasks 5–6 (independent, code-heavy); inline for the rest. Reviewer ≥ implementer; top tier only for anything touching financial/governor text.

---

## DECISIONS (ratified by Gabriel via MCQ, 2026-07-09; ★ = Claude-recommended default accepted via "continue")

- `LTV_DOCTRINE` = **~15%** (doctrine/memory correct; skill wrong)
- `ONEDRIVE_CONSOLIDATION` = **EXECUTE** (full consolidation + repoint paths)
- `CC_DAILY_BRIEF` = **REPAIR-GGOLDBERG-ONLY**
- `PLUGIN_KEEP` = **capex-budgeting, submarket-spatial-analysis** (prune the other 6)
- `SESSION_ENV_RETENTION` = **90-DAY**
- `AUTOMATION_BUDGET_S9` = **MOOT** — already re-ratified 2026-07-09, expires 2026-10-07, one-in-one-out dropped (rules.md §9). No action.
- `RAM_POSTURE` = **RETUNE-32GB** (~24GB working ceiling)
- `DISPATCH_ALIAS` = **AMEND-TO-TOP-TIER-ALIAS**
- `THIRD_CLONE` = **RECONCILE-COMMITS** (cherry-pick real edits via PR, then archive)
- `DEADMAN_APPROACH` = **GITHUB-ACTION** ★
- `B4_OLD_MACHINE` = **DEFER** ★ (flag, don't act)
- `COWORK_SETTINGS_V21` = **DEFER** ★ (pre-July-21 review)

## PRE-FLIGHT (mandatory, before Task 1)
1. Failure modes to check per task: stale/misread input · wrong target · **already-fixed** (a same-day morning audit closed 25 items and rules.md §9 was re-ratified the same day — re-verify EVERY finding against current state before touching it) · cross-fleet shared-file blast radius · guardrailed surface.
2. Single-writer checks: `git status` + `git log --oneline -1` on `ora-skills`; latest timestamp in `~/.claude/maintenance/_state/registry-membership.log` for concurrent registry activity; event_log appends ONLY via `python ~/.claude/maintenance/append-event-log.py`.
3. Confirm no stuck `powershell` processes; Desktop Commander healthy (hung twice during the audit session).
4. Invariants in full force: never touch oxfordra.net repos · never modify governor constants (DSCR 1.25 / LTV 40 are UNCHANGED by Task 5c — the ~15% figure is a descriptive portfolio-leverage fact, not the 40% LTV governor) · never JSON-splice a scheduler registry · archive, never delete · external sends need in-turn confirmation · rules.md §10 bypass regime + ora-autonomy-gate stand.

---

## Task 1 — session-context HALT note (L1)
In `~/.claude/session-context.md`, replace the ⛔ 2026-06-11 COORDINATION bullet (falsely asserts the new machine has NOT arrived) with:
> **⛔ MIGRATION STATE (2026-07-09):** New machine CONFIRMED in service (LAPTOP-CSHSCBE6, 32GB RAM). Do NOT auto-run Phase B2 fleet re-registration — both fleets already live here; re-registration duplicates tasks. B4 old-machine decommission status UNCONFIRMED (Gabriel deferred 2026-07-09). B3 burn-in partially complete (see `memory/project_claude-setup-audit-2026-07-09.md`).
Do not touch the generated-fleet markers. Event_log the change.

## Task 2 — Task-guard zombie/baseline (L2 /debug)
The 2026-07-09 12:57 guard email flagged `ora-lender-covenant-tracker` "1 DROPPED" — that task is ratified-retired (2026-06-11 list). Determine which: (a) stale expected-roster baseline inside `~/.claude/scheduled-tasks/ora-task-integrity-guard/` → fix the baseline; or (b) zombie re-registration during the 07-05/08 fleet recovery, since vanished → confirm absent from BOTH raw registries (direct grep of the two `scheduled-tasks.json` files, not probe output) and event_log "drift, not intent."

## Task 3 — Frozen-date "[ORA Command Center] Daily Brief — 2026-06-01" (L2) — DECISION: REPAIR-GGOLDBERG-ONLY
Sent 07-08 06:45 and 07-09 06:45 to ggoldberg + egoldberg. Locate the producing task in `oxford-command-center` (PRIVATE — E. Fulton figures — stays private). Root-cause the frozen date variable (likely a pinned seed/config date), fix it, and set recipients to **ggoldberg@oxfordra.net only** — no cc. Verify against the next send in `_shared/send-log.txt`.

## Task 4 — 17:08 CRITICAL "Access gate check failed" (L2)
Root-cause in `oxford-command-center`. Read-only diagnosis first; smallest surgical fix; evidence (command output) before any "resolved" claim. Financial/governor code → top-tier model only.

## Task 5 — ora-skills PRs ×3 (L3; one PR per skill; after merge, repackage via `package-and-stage-skill` and stage for Gabriel's one-click reimport)
5a. `monthly-close` v2.0 → v2.1: SCHEDULED TASK BEHAVIOR step 6 emails ggoldberg AND egoldberg — routing-canon violation; change to **ggoldberg-only**. Also: `monthly-close-kickoff` is a retired task — if no live task fires this section, retitle it "IF INVOKED AS A SCHEDULED TASK" so the skill stops implying a registration that doesn't exist.
5b. `psa-reconciliation` v1.3 → v1.4: Step 4 title banner hardcodes "E. Fulton Portfolio" — replace with the `[PropertyShortName]` template token. No behavior change.
5c. `acquisition-underwriting` v3.5 → v3.6: CAPITAL STRUCTURE CONTEXT "~20% portfolio LTV" → **"~15% portfolio LTV"** (Gabriel-ratified 2026-07-09). No scorecard weights or governors change.

## Task 5d — ora-ops-plugin prune (L3) — DECISION: keep capex-budgeting + submarket-spatial-analysis
In `~/.claude/ora-ops-plugin`, remove from the plugin manifest/skill set: `annual-cycle`, `vendor-management`, `debt-management` (duplicate of canonical user skill v1.2 — live routing collision), `deal-retirement`, `cash-position-monitor`, `investor-relations` (LP/capital-call model contradicts proprietary-capital doctrine; several reference ratified-retired tasks). Archive removed skill dirs (never delete). Version-bump the plugin; stage the updated package; flag Gabriel's manual Settings → Capabilities update as the activation step.

## Task 6 — External cross-fleet dead-man (L3) — DECISION: GITHUB-ACTION
Closes the self-referential gap (guard died with the registry it guards; ~14 CC functions dark ~3 weeks). Build:
1. A probe emission: extend `registry-membership-probe.py` (or a thin sibling) to write `fleet-heartbeat.json` — timestamp, per-fleet task counts, registry-file existence + hashes. NO deal terms, NO credentials (fail-closed .gitignore stays authoritative; this file is explicitly opted IN).
2. Local push cadence: include it in the existing nightly `~/.claude` push to PRIVATE `ZeOoba/ora-claude-config`.
3. Scheduled GitHub Action in that repo: daily; alerts (GitHub issue + email to ggoldberg@oxfordra.net) if heartbeat >24h stale OR CC count < ratified floor (current: 10 live per the 2026-07-09 probe) OR LAMS count < 18.
TDD; independent local review; evidence before done. This is a NEW monitoring layer — justification vs. rules.md §9 bar: P0-critical (it is the fix for the July fleet-loss incident class).

## Task 7 — RAM doctrine re-tune (L2) — DECISION: RETUNE-32GB, ~24GB working ceiling
Update every Claude-system reference to the 5.7GB old-box ceiling: `CLAUDE.md` Engineering OS RAM modifier · `hooks/ram-guard.ps1` thresholds · `/ram` + `/heavy` command docs · `memory/reference_lean_ram_toolkit.md` · `docs/system-inventory.md` hardware section. New posture: 32GB physical, ~24GB working ceiling (OS/app headroom), raise fan-out concurrency default proportionally (propose specific old→new values; event_log them). The 5.7GB line in Gabriel's User Preferences is his manual edit — flag only.

## Task 8 — Dispatch model alias (L1) — DECISION: AMEND
`CLAUDE.md` Dispatch section: "default opus" → "default: current top-tier model alias (Fable/Mythos class as of 2026-07); invariants unchanged (reviewer ≥ implementer; never below top tier for confidential/financial/governor code)." Flag the mirrored User Preferences line for Gabriel's manual pass.

## Task 9 — LAMS skill hardening (content edits ONLY — never registry JSON; single-writer check on the OneDrive `Documents\Claude\Scheduled\<id>\` files first)
9a. `ora-skill-text-audit` SKILL.md: add routing-canon check — grep all skills for `egoldberg` outside the ora-am-brief exception; flag hits in its ACTION-REQUIRED email. (Would have caught Task 5a mechanically.)
9b. Outbox-QC logic (`ora-outbox-qc-sweep`'s home): add frozen-date defect class — subject-line date differing from send date by >1 day = MED defect. (Would have caught Task 3 on 07-08.)

## Task 10 — session-env retention (L2) — DECISION: 90-DAY
Implement `memory/reference_session_env_retention_proposal.md` at a 90-day window: archive (never delete) `~/.claude/session-env/` dirs older than 90 days to `_archive/`; wire the sweep into `ora-weekly-hygiene` so it self-maintains. ~803 dirs at audit time.

## Task 11 — third ora-skills clone (L3) — DECISION: RECONCILE-COMMITS
`Claude_Workspace/01_Workspace/.claude/skills/` (45 commits behind canonical, own uncommitted edits): diff the uncommitted edits → cherry-pick anything real into canonical `C:\Users\Owner\ora-skills` via PR → save the full diff into the archive folder → move the clone to `_archive/`. Two-path lockstep doctrine then has ONE fewer divergence surface; verify no live task or VS Code config references the archived path before moving.

## Task 12 — OneDrive split-brain consolidation (L3, supervised) — DECISION: EXECUTE
Per rules.md §1: writes/moves in non-Claude Oxford OneDrive business folders are permission-gated — **this decision IS that permission**, scope limited to the split-brain consolidation below; anything outside scope still asks.
1. Inventory both roots: `OneDrive - Oxford Capital Partners` (canonical) vs `OneDrive - Oxford Capital Partners (1)` (stale pre-migration duplicate per `reference_memory_scope_fragmentation.md`).
2. Create canonical `Documents\Claude\{Outputs,Workspace}`.
3. Move `(1)` content into canonical mirrors with a full move-manifest (path-by-path); collisions → keep-newest + manifest-flag, never overwrite silently.
4. Search-then-repoint every hardcoded `(1)` path (hygiene engines, scheduled-task SKILL.mds, configs) — list ALL hits before editing any.
5. Leave `MOVED-SEE-CANONICAL.md` tombstones at vacated locations.
6. Post-verify: each scheduled task whose paths were repointed finds its targets on next fire; spot-check via fleet-status + send-log.
Consult `reference_onedrive_business_scope.md` before any broad root scan; Personal-list content is out of scope entirely.

## Task 13 — doctrine entry (L1)
Add the audit-ledger convention to `memory/rules.md` §1: "Before launching any setup/system audit, grep memory for a same-day or superseding `project_*-audit` entry; extend it, don't duplicate." (§9 budget item is MOOT — re-ratified 2026-07-09 through 2026-10-07.) cowork-settings v2.1 stays DRAFT pending the pre-July-21 review — no action.

## DONE CRITERIA (every task)
Evidence (command output / diff / raw-registry grep) before any "done" claim · smallest surgical change · event_log append per task · single flagged-for-Gabriel block at session end · ≤5 workflow-optimization bullets.

## OUT OF SCOPE — Gabriel-manual checklist (do not attempt)
1. User Preferences edits (one pass): delete E. Fulton Hard-Invariant-3 tombstone · 5.7GB → 32GB/~24GB RAM line · "default opus" → top-tier alias mirror · reconcile "VP Acquisitions" vs "principal" identity.
2. Read the 2026-07-09 17:08 CRITICAL access-gate email.
3. Cowork UI: `ora-cam-reconciliation-annual` → enabled:false (December-only; re-enable each December).
4. OneDrive online recycle bin: recover `ora-health-guard` spec, then confirm re-enable (plus confirm re-enable of rebuilt `ora-pm-ledger` / `ora-weekly-hygiene` if not already done).
5. Settings → Capabilities: import the repackaged skills from Tasks 5/5d when staged.
6. cowork-settings v2.1 ratification + paste (pre-July-21 review).
7. B4 old-machine status + decommission decision (deferred 2026-07-09).
