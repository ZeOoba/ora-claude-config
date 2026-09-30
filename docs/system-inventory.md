# Claude Code / Cowork System Inventory

> **Generated 2026-09-14 10:06 ET** by `ora-weekly-hygiene` Block H. Full overwrite every run — this file is a snapshot, not a history. Report-only: Block H flags findings, it never fixes them.

## Toolchain

| Tool | Version |
| --- | --- |
| git | 2.55.0.windows.2 |
| node | v24.18.0 |
| npm | 11.16.0 |
| python | 3.13.14 |
| pip | 26.1.2 |
| ripgrep | 14.1.1 |
| GitHub CLI | 2.96.0 (2026-07-02) |

`gh` was probed at its full path `C:\Program Files\GitHub CLI\gh.exe` — bare `gh` may not resolve on a given session's PATH, so a "not found" from the bare name is not evidence of absence.

## Plugins

4 entries in `enabledPlugins` (down from 5 at the 2026-09-07 run), **2 enabled**:

- `superpowers@superpowers-marketplace` — enabled
- `pr-review-toolkit@claude-plugins-official` — enabled
- `code-review@claude-plugins-official` — disabled
- `commit-commands@claude-plugins-official` — disabled

**CHANGE since 2026-09-07: `claude-md-management@claude-plugins-official` is gone from both `settings.json` → `enabledPlugins` and `plugins/installed_plugins.json`** — it was disabled last run, not enabled, so this looks like a clean uninstall rather than a config-loss incident; flagged here only because it's a change worth a human glance, not acted on.

**Duplicate-marketplace check: 0 flags.** No plugin name appears under two marketplace keys with more than one copy `true`. `installed_plugins.json` cross-checked: 4 top-level plugin entries, matches `enabledPlugins` 1:1.

## Hooks, agents, commands

- **Hooks** (`~/.claude/hooks/`): top-level entries include eos-gate-sentinel, eos-evidence-gate, eos-plan-gate, eos-plan-marker, eos-claude-md-guard, confidentiality-guard, rules-md-guard, commit-provenance-recorder, registry-write-guard, git-prepush-confidential-scan, fleet-session-hook, repo-freshness (.py), plus `lib/`, `tests/`, `sessions/`, `archive/`, `bin/`, `__pycache__/` subdirectories. Full enumeration exceeded this block's read window (100+ files including per-session override-token artifacts under `sessions/_archive_override_tokens/`) — spot-checked, not exhaustively diffed against `settings.json` → `hooks` bindings this run.
- **Agents** (`~/.claude/agents/`): 17 — adversarial-reviewer, comms-qc-reviewer, dd-package-sweep, deal-flow-triage, deal-recon, estoppel-reconciler, insurance-declaration-checker, lease-abstract-verifier, noi-opportunity-scout, open-items-triage, portfolio-anomaly-scout, psa-redline-checker, repro-isolator, security-auditor, site-qc-reviewer, tax-appeal-scout, underwriting-checker. (2026-09-30: +adversarial-reviewer, +noi-opportunity-scout previously omitted from this list, −lease-sweep retired.) (Up from 9 at the 2026-09-07 run — 7 new: dd-package-sweep, estoppel-reconciler, insurance-declaration-checker, lease-abstract-verifier, open-items-triage, repro-isolator, tax-appeal-scout.)
- **Commands** (`~/.claude/commands/`): 13 — build, cleardisk, debug, handoff, heavy, open-sessions, plan, ram, refactor, research, ship, solo, verify.

## Scheduled-task fleet (via `fleet-status.py --summary`, 2026-09-14T10:06:18)

- Total tracked: **67** (enabled 66 / disabled 1) — cc=38, lams=28.
- Never-ran: 6 (ora-counsel-review-standard-positions-2027, ora-county-sales-monitor, ora-exit-cap-spotcheck, ora-gis-endpoint-liveping, ora-passed-deal-tracker, ora-pm-monthly-billing) — 0 overdue by cadence.
- One-time fireAt: 2 (ora-counsel-review-standard-positions-2027, ora-lams-fleet-resume-20260911) — 1 EXPIRED (ora-lams-fleet-resume-20260911), normal completion.
- Missed single cycle (open at generation time): 3 — ora-deal-aging-sla (165.4h), ora-health-guard-fail-aging-nudge (165.4h), ora-lease-snapshot-refresh (163.5h). Point-in-time only; may have self-healed since.
- Pause-explained (NOT missed): 3 — ora-cc-schematic-refresh, ora-command-center-mirror-drift-check, ora-sofr-direct-prefetch.
- Throttle skips last 24h: 132 across 13 tasks (top: ora-ar-feed-sweep 11, ora-cc-snapshot-refresh 11, ora-checkout-merge-forward 11, ora-deal-aging-sla 11, ora-ground-truth-auditor 11, ora-lease-snapshot-refresh 11, ora-memory-commit-sweep 11, ora-pm-daily-crons 11).
- Same-time collisions: 0. Duplicate registrations: 0.
- VERDICT: ATTENTION (3 missed cycles + 132 throttle skips in 24h — consistent with the documented AM catch-up-burst pattern, not flagged as a new incident).

**Retired-in-spec-but-live-in-registry cross-check:** 12 SKILL.md files under `scheduled-tasks/` contain the string "RETIRED" somewhere in body text. Of these, 5 are themselves archived task dirs (already out of the live registry by location: `_archive_2026-08-09_retired/`, `_archive_2026-07-16_retired/`, `_archive_2026-07-07_retired/` x3) — consistent, not a mismatch. The remaining 7 (ora-health-guard, ora-weekly-hygiene, ora-task-integrity-guard, ora-pm-ledger, ora-doctrine-integrity-guard, ora-deal-sourcing-scan, ora-am-brief) are all live core fleet members; spot-checked two (`ora-am-brief`, `ora-health-guard`) and confirmed the string refers to a *different, already-decommissioned* artifact (e.g. "LAMS twin retired") in body text, never the live task's own frontmatter `description` declaring itself retired. Did not spot-check the remaining 5 individually this run (all are long-standing, previously-clean core tasks) — **0 mismatches found on the sample checked; full 7-way frontmatter diff not repeated this run**, noted as a lighter-touch pass than 2026-09-07's full check.

## Guard

Block H is read-only except this one file. No `settings.json`, hook, `CLAUDE.md`, or memory-file edit was made by this block.
