# Merged Remediation Plan — 2026-06-10 (Code+Cowork cross-audit)

Decisions ratified by Gabriel 2026-06-10: routing = Eric gets Daily Brief ONLY (all other
automated sends -> ggoldberg alone) · naming = keep three standing schemas · title = VP
Acquisitions · Zapier = keep connected/never use · lanes /debug /build /refactor become
Claude-invocable · fleet = re-space + off-app dead-man · Composio re-auth + prune Guru/Midpage.

## Phase 0 — Safety chain (this window where possible)
- 0c. Read watchdog YAML + script (gh api, read-only). VERIFY target page ID == canonical
  35c6ecd8-9e59-81d5-8d2c-d08002458b78. If mismatch -> fix via gh api PUT (show diff).
- 0d. `gh workflow enable` — first run = live alarm-path test (one expected stale alarm).
- 0f-early. Redact the plaintext ntn_ token literal in the two on-disk files (Cowork memory
  remediation file + saved audit doc). Rotation by Gabriel still REQUIRED (token was exposed).
- GABRIEL: rotate Notion token -> update repo secret NOTION_TOKEN -> Run-now both new tasks
  -> paste the confidential deal's Appendix A (Cowork surface).

## Phase 1 — Single source of truth (this window, Code-reachable)
- 1a. settings.json: remove user-invocable-only for debug/build/refactor. Verify JSON parses.
- 1b. settings.json: remove dead OXFORD_DEALS env (grep first for any consumer).
- 1c. session-context.md: correct "LAMS orphaned & dark" -> two live registries doctrine;
  routing line -> Eric=brief-only.
- 1d. ~/.claude/CLAUDE.md: routing rule update only (naming/title unchanged per rulings);
  add 2-line dual-fleet scheduler doctrine; splice-registration prohibition.
- 1e. Memory: rules.md routing; tech.md + 00_system_of_record.md dual-fleet correction.
- 1f. daily-setup-audit-prompt.md: fleet-status.py is live (re-pointed 6/09), not deprecated.
- 1g. Routing sweep over the 14 main-store SKILL.mds (canonical filePath copies; guard.ps1
  mirrors them): remove egoldberg cc except ora-am-brief.
- 1h. fleet-status.py + cc-verifier-probe.py -> enumerate BOTH registries (expect 14 CC + 4 LAMS).
  Verify by running both.
- 1i. NEW maintenance/registry-membership-probe.py: snapshot enabled task IDs across both
  registries, diff vs prior snapshot, nonzero-exit + report on any disappearance. Wire into
  ora-setup-audit SKILL.md checklist. Verify by running (first run = baseline).
- 1j. ora-automation-health-monitor SKILL.md: ORPHANED-BEACON rule (beacon listed but task
  absent from BOTH registries -> warn, never silent skip); task list -> 18 across 2 fleets.
- 1k. Merged disposition ledger (Cowork Appendix D + the 8 Tier-2 retirements of 6/09) ->
  00_Governance/outputs/2026-06-10_fleet-disposition-ledger.md.
- DEFER to Cowork surface: Cowork CLAUDE.md core block, 5 dead skill refs, register-scheduled-task
  v2.0 cloud copy, skill-cache refresh, confidential-deal instructions.

## Phase 2 — Hygiene (this window where reachable)
- 2a. Re-space: deal-sourcing-scan Tue 07:20 -> Tue 10:45 via update_scheduled_task MCP
  (main store). LAMS heartbeat 18:00->17:50 deferred to Cowork (registry owned by app).
- 2b. June 9 skill-text CRITICALs: fix what is reachable on disk; defer cloud-cache copies.
- GABRIEL: Composio re-auth, prune Guru/Midpage connectors, Zapier untouched.

## Gates
After each edit: cheapest verify (parse/run/grep). End: doctrine-integrity-probe.py +
fleet-status.py green; event_log entry; handoff list for Gabriel/Cowork items.
