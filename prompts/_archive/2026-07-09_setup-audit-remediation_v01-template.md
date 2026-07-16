# ORA Setup-Audit Remediation — Claude Code Master Prompt
**Session date issued:** 2026-07-09 (evening chat-surface audit — companion to the same-day morning audit in `memory/project_claude-setup-audit-2026-07-09.md`)
**Save to:** `~/.claude/prompts/2026-07-09_setup-audit-remediation.md`
**Lane:** sequence of L1/L2/L3 tasks — announce lane + Dispatch per task. Suggested dispatch: subagent-driven-development for Tasks 5–6 (independent, code-heavy); inline for the rest. Reviewer ≥ implementer; never below top tier for anything touching financial/governor text.

---

## DECISIONS (filled from Gabriel's MCQ answers — do NOT execute a gated task while its value is blank)

- `LTV_DOCTRINE` = [ 15% | 20% | VERIFY-FROM-WORKBOOK ]
- `ONEDRIVE_CONSOLIDATION` = [ EXECUTE | PLAN-ONLY | DEFER ]
- `CC_DAILY_BRIEF` = [ KILL | REPAIR-KEEP-CC-ERIC (ratifies a second cc exception) | REPAIR-GGOLDBERG-ONLY ]
- `PLUGIN_KEEP` = [ list of ora-operations-extensions skills to keep ]
- `SESSION_ENV_RETENTION` = [ 30-DAY | 90-DAY | DEFER ]
- `AUTOMATION_BUDGET_S9` = [ RE-RATIFY-SAME | RAISE | LET-LAPSE ]
- `RAM_POSTURE` = [ RETUNE-32GB | KEEP-5.7GB ]
- `DISPATCH_ALIAS` = [ AMEND-TO-TOP-TIER-ALIAS | KEEP-OPUS ]
- `THIRD_CLONE` = [ ARCHIVE | RECONCILE-COMMITS | DEFER ]
- `DEADMAN_APPROACH` = [ GITHUB-ACTION | EXTEND-WATCHDOG | DEFER ]
- `B4_OLD_MACHINE` = [ STILL-EXISTS-DECOMMISSION | ALREADY-GONE | DEFER ]
- `COWORK_SETTINGS_V21` = [ RATIFIED | NEEDS-CHANGES | DEFER ]

## PRE-FLIGHT (mandatory, before Task 1)
1. Failure modes: stale/misread input · wrong target · already-fixed (a same-day morning audit closed 25 items — re-verify EVERY finding against current state before touching it) · shared-file blast radius across fleets · guardrailed surface.
2. Single-writer checks: `git status` + `git log --oneline -1` on `ora-skills`; latest timestamp in `~/.claude/maintenance/_state/registry-membership.log` for concurrent registry activity; event_log appends ONLY via `python ~/.claude/maintenance/append-event-log.py`.
3. Confirm no stuck `powershell` processes and Desktop Commander responsive (it hung twice in the audit session).
4. Standing invariants apply in full: never touch oxfordra.net repos; never modify governor constants (DSCR 1.25 / LTV 40); never JSON-splice a scheduler registry; archive, never delete; external sends require in-turn confirmation.

---

## Task 1 — session-context HALT note (L1)
In `~/.claude/session-context.md`, replace the ⛔ 2026-06-11 COORDINATION bullet (which falsely asserts the new machine has NOT arrived) with:
> **⛔ MIGRATION STATE (2026-07-09):** New machine CONFIRMED in service (LAPTOP-CSHSCBE6, 32GB RAM). Do NOT auto-run Phase B2 fleet re-registration — both fleets already live here; re-registration duplicates tasks. B4 old-machine decommission per `B4_OLD_MACHINE` decision. B3 burn-in partially complete (see morning-audit memory).
Do not touch the generated-fleet markers. Log to event_log.

## Task 2 — Task-guard zombie/baseline (L2 /debug)
Today's guard email flagged `ora-lender-covenant-tracker` as "1 DROPPED" — that task is on the ratified-retired list (2026-06-11). Determine which: (a) stale expected-roster baseline inside `~/.claude/scheduled-tasks/ora-task-integrity-guard/` → fix the baseline; or (b) the task was zombie-re-registered during the 07-05/08 fleet recovery and has since vanished → confirm it is absent from BOTH registries and record "drift, not intent" in event_log. Evidence: raw registry grep, not probe output alone.

## Task 3 — Frozen-date "[ORA Command Center] Daily Brief — 2026-06-01" (L2)
Sent 07-08 and 07-09 to ggoldberg + egoldberg. Locate the producing task in `oxford-command-center` (repo is PRIVATE — E. Fulton figures — keep it that way). Root-cause the frozen date variable. Then per `CC_DAILY_BRIEF`: KILL → disable via supervised path + archive; REPAIR-* → fix the date bug and set recipients per the decision. If REPAIR-KEEP-CC-ERIC, append the new sanctioned exception to the routing canon in `CLAUDE.md` and event_log it as a doctrine change.

## Task 4 — 17:08 CRITICAL "Access gate check failed" (L2)
Root-cause in `oxford-command-center`. Read-only diagnosis first; smallest surgical fix; evidence before any "resolved" claim. If it touches financial/governor code, top-tier model only.

## Task 5 — ora-skills PRs ×3 (L3; one PR per skill; repackage via `package-and-stage-skill` after merge and stage for Gabriel's one-click reimport)
5a. `monthly-close` v2.0 → v2.1: SCHEDULED TASK BEHAVIOR step 6 currently emails ggoldberg AND egoldberg — routing-canon violation. Change to ggoldberg-only (unless `CC_DAILY_BRIEF` ratified a broader exception — it does NOT extend here regardless). Also reconcile the section header against the retired `monthly-close-kickoff` task: if no live task fires it, retitle the section "IF INVOKED AS A SCHEDULED TASK" so the skill stops implying a registration that doesn't exist.
5b. `psa-reconciliation` v1.3 → v1.4: Step 4 title banner hardcodes "E. Fulton Portfolio" — replace with `[PropertyShortName]` template token. Changelog note: template-token fix, no behavior change.
5c. `acquisition-underwriting` v3.5 → v3.6: CAPITAL STRUCTURE CONTEXT says "~20% portfolio LTV"; doctrine elsewhere says ~15%. Set per `LTV_DOCTRINE`; if VERIFY-FROM-WORKBOOK, read the live ORA Master Workbook (SharePoint, source of record) and cite the figure + date. No scorecard weights or governors change.

## Task 6 — External cross-fleet dead-man (L3, gated on `DEADMAN_APPROACH`)
Close the self-referential-monitoring gap (guard died with the registry it guards; 14 CC functions dark ~3 weeks). Per decision:
- GITHUB-ACTION: scheduled Action in the PRIVATE `ZeOoba/ora-claude-config` repo — the nightly local push includes a machine-generated `fleet-heartbeat.json` (probe output: registry file hashes + task counts + timestamp); the Action alerts (GitHub issue + email) if the heartbeat is stale >24h or CC count drops below the ratified floor.
- EXTEND-WATCHDOG: extend `ZeOoba/ora-cowork-watchdog` to also consume a CC/MCP heartbeat pushed alongside the existing Notion heartbeat.
Never commit deal terms or credentials into the heartbeat payload (fail-closed gitignore stays authoritative). TDD applies; independent local review before done.

## Task 7 — RAM doctrine re-tune (gated on `RAM_POSTURE` = RETUNE-32GB)
Update every Claude-system reference to the 5.7GB old-box ceiling: `CLAUDE.md` Engineering OS RAM modifier, `hooks/ram-guard.ps1` thresholds, `/ram` + `/heavy` command docs, `memory/reference_lean_ram_toolkit.md`, `docs/system-inventory.md` hardware section. Propose a working ceiling of ~24GB (32GB − OS/app headroom) and raise the fan-out concurrency default accordingly; state old→new values in event_log. NOTE: the 5.7GB line in Gabriel's User Preferences is his manual edit — flag, do not attempt.

## Task 8 — Dispatch model alias (gated on `DISPATCH_ALIAS`)
Amend the Dispatch section of `CLAUDE.md`: "default opus" → "default: current top-tier model alias (Fable/Mythos class as of 2026-07); invariants unchanged (reviewer ≥ implementer; never below top tier for confidential/financial/governor code)." Flag the mirrored line in User Preferences for Gabriel's manual pass.

## Task 9 — LAMS skill hardening (content edits ONLY — never touch registry JSON)
9a. `ora-skill-text-audit` SKILL.md: add a routing-canon check — grep all skills for `egoldberg` outside the ora-am-brief exception (plus any exception ratified in Task 3); flag hits in its ACTION-REQUIRED email.
9b. `ora-outbox-qc-sweep` SKILL.md (or the outbox-QC logic's home): add a frozen-date defect class — any subject-line date differing from send date by >1 day = MED defect.
Single-writer check on the OneDrive `Documents\Claude\Scheduled\<id>\` files before editing (shared across fleets).

## Task 10 — session-env retention (gated on `SESSION_ENV_RETENTION`)
Implement the existing `reference_session_env_retention_proposal.md` at the chosen window: archive (never delete) session-env dirs older than the window to `_archive/`; wire the sweep into `ora-weekly-hygiene` Block coverage so it self-maintains. ~803 dirs currently.

## Task 11 — third ora-skills clone (gated on `THIRD_CLONE`)
`Claude_Workspace/01_Workspace/.claude/skills/` is 45 commits behind canonical with its own uncommitted edits. ARCHIVE → diff the uncommitted edits first, save the diff to the archive folder, then move the clone to `_archive/`; RECONCILE-COMMITS → cherry-pick anything real into canonical via PR, then archive.

## Task 12 — OneDrive split-brain (gated on `ONEDRIVE_CONSOLIDATION`; supervised — OneDrive business writes/moves are permission-gated by invariant)
EXECUTE: (i) inventory both roots (`OneDrive - Oxford Capital Partners` canonical vs `...(1)`); (ii) create canonical `Documents\Claude\{Outputs,Workspace}`; (iii) move `(1)` content to canonical mirrors with a full move-manifest; (iv) repoint every hardcoded `(1)` path in hygiene engines and scheduled-task SKILL.mds (search first, list all hits, then edit); (v) leave a `MOVED-SEE-CANONICAL.md` tombstone at each vacated location; (vi) post-verify each scheduled task's next run finds its paths. PLAN-ONLY: produce (i)+(iv) hit-list + move-manifest as a report, execute nothing.

## Task 13 — doctrine entries (L1)
- Add the audit-ledger convention to `memory/rules.md`: "Before launching any setup/system audit, grep memory for a same-day or superseding `project_*-audit` entry; extend, don't duplicate."
- rules.md §9 automation budget per `AUTOMATION_BUDGET_S9` (lapses 2026-07-11 — do this task first if running near that date).
- If `COWORK_SETTINGS_V21` = RATIFIED: rename `20260709_ORA_CoworkGlobalSettings_v2_1_DRAFT.md` → ratified filename per `cowork-settings` skill versioning and event_log it. The paste into Cowork Settings remains Gabriel-manual.

## DONE CRITERIA (every task)
Evidence (command output / diff / registry grep) before any "done" claim · smallest surgical change · event_log append per task · repo gates green where applicable · end the session with ≤5 workflow-optimization bullets · list all items flagged-for-Gabriel in one block.

## OUT OF SCOPE — Gabriel-manual (do not attempt)
User Preferences edits (E. Fulton tombstone deletion, 5.7GB→32GB line, dispatch alias mirror, VP-vs-principal identity) · cowork-settings v2.1 paste into Cowork Settings · Cowork UI toggle: `ora-cam-reconciliation-annual` → enabled:false (December-only) · OneDrive online recycle-bin recovery of `ora-health-guard` spec · Settings→Capabilities plugin skill management + staged skill reimports · reading the 17:08 CRITICAL email · old-machine physical decommission.
