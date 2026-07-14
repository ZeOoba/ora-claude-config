# ORA Claude Code — System Inventory

Point-in-time snapshot. **Refreshed 2026-07-12 (Sunday 20:00) by `ora-weekly-hygiene` Block H** — this task
owns keeping the doc current (weekly). Full overwrite each run; no history preserved here (history →
`memory/event_log.md`). Read-only except this one file: Block H flags, it does not fix.

## Hardware / OS
- Windows 11 Home, build 10.0.26200
- RAM: 32 GB physical (LAPTOP-CSHSCBE6, ASUS Zenbook S14 — in service 2026-07); working ceiling
  ~24 GB. Engineering OS concurrency guidance keys off the ~24 GB working ceiling. No RAM-heavy standing
  services (Docker etc.) — nothing here needs them.

## Toolchain (verified present this pass)
- git 2.55.0.windows.2
- node v24.18.0 / npm 11.16.0
- python 3.13.14 (pip not re-probed this pass)
- ripgrep 14.1.1
- GitHub CLI 2.96.0 (2026-07-02) — at `C:\Program Files\GitHub CLI\gh.exe`; confirmed working via full
  path this pass. Invoke by full path when in doubt (bare-`gh` PATH resolution from the Bash tool is a
  harness-snapshot matter).

## Not present (confirmed absent previously; not re-probed this pass)
pnpm, uv, Docker, VS Code CLI (`code`), fd, fzf, jq, yq, make, just — none justified by any live workflow.
Do not install Docker/Postgres/Redis: QuickBooks Desktop + Notion + HubSpot are the data layer (MCP-wired).

## Claude Code plugins (17 installed, 14 active — dedup CLEAN this pass, 0 flags)
`enabledPlugins` = 14 entries; automated same-name-under-2-marketplaces dedup check returned **0 duplicate-
enabled names** this pass (the 2026-07-07 dedup on code-review / pr-review-toolkit / superpowers still holds).
`installed_plugins.json` present (keys: version, plugins).

## Custom domain agents (`~/.claude/agents/`, 6)
deal-flow-triage, deal-recon, lease-sweep, portfolio-anomaly-scout, site-qc-reviewer, underwriting-checker.

## Custom slash commands (`~/.claude/commands/`, 12)
build, cleardisk, debug, handoff, heavy, open-sessions, plan, ram, refactor, research, ship, solo — the
Engineering OS lane dispatch (L1–L7).

## Hooks (`~/.claude/hooks/`) — directory enumerated this pass
Scripts present: confidentiality-guard.py, engineering-router.py, eos-claude-md-guard.py, eos-evidence-gate.py,
eos-gate-sentinel.py, eos-plan-gate.py, eos-plan-marker.py, eos-telemetry.py, fleet-session-hook.py,
git-prepush-confidential-scan.py, git-prepush-doctrine-gate.py, ora-autonomy-gate.py, ram-guard.ps1,
ram-watchdog.sh, repo-freshness.py, shared-checkout-guard.py, test-ora-autonomy-gate.py — plus `lib/`,
`overrides/`, `sessions/`, `tests/`, `__pycache__/`.
Lifecycle bindings (from settings.json, last verified 2026-07-07 — not re-parsed this pass):
UserPromptSubmit engineering-router · PreToolUse confidentiality-guard / eos-evidence-gate / eos-plan-gate /
ora-autonomy-gate / shared-checkout-guard (+ eos-claude-md-guard) · PostToolUse eos-gate-sentinel /
eos-plan-marker / fleet-session-hook · SessionStart fleet-session-hook / repo-freshness · Stop
fleet-session-hook · SessionEnd eos-telemetry / fleet-session-hook.

## Scheduled tasks — VOLATILE (flag, not fixed — Block H is read-only)
`fleet-status.py --summary` this pass: **44 tasks (40 enabled / 4 disabled); per-fleet enabled cc=19, lams=21.**
Both registry files present and read. Fleet has grown vs. the 2026-07-09 generated roster (30 enabled) —
expected growth, but the SessionStart roster is stale relative to the live registries; regenerate before
trusting counts.
Health verdict: **ATTENTION** — 13 never-ran · **3 EXPIRED one-time** (continue-cc-setup-optimization-batch-2c-3,
efulton-post-legalhold-consolidation, investigate-plan-gate-worktree — candidates for `delete_scheduled_task`
from a fresh session) · 10 throttle skips over ceiling (top: ora-aaos-expire-leases=9) · 0 same-time
collisions · 15-task AM pileup (05:00–09:30).

**RETIRED-marker cross-check (Block H spec):** 0 genuine "task self-marked RETIRED in its own SKILL.md
description yet still live." The grep hits (ora-doctrine-integrity-guard, ora-health-guard, ora-open-sessions-board,
ora-pm-ledger, ora-task-integrity-guard, ora-week-ahead-briefing, ora-weekly-hygiene) are all body-prose
references to *other* things being retired (e.g. "LAMS twin retired", "Rube shut down") in legitimately-live
core tasks — not self-retirement markers.

## MCP servers connected (~30)
Notion, HubSpot, Microsoft 365 (Outlook/Calendar/SharePoint), Netlify, Excel, FRED, PDF viewer, scheduled-tasks,
computer-use, claude-in-chrome, context7, Desktop Commander (both Extension + plugin connections live from
Code), Apify, plus the standard toolset. Composio and Rube are GONE — never reference them. Full live list is
in the session tool inventory (drifts fastest; not duplicated here).

## Known git repos
`ora-skills` (content repo — no CI, quality-checked by `ora-skill-text-audit`), `website-canonical` /
`oxford-site` (oxfordra.net — invariant-2 protected, not inspected), `oxford-command-center` (**Block I this
pass: 0 broken refs, 0 fsck-missing — the 2026-07-07 ref-rot repair of 23 tombstone refs holds; ~20 benign
dangling commits present, gc-able**), `oxford-perfection` (ad-hoc scripts), brain mirror, `ora-pm`.

## Environment caveats — status this pass
- **Outlook COM send path: RESTORED.** The 2026-07-07 machine-wide COM-down incident is cleared — this pass
  sent 5 Block emails via `send-via-outlook.ps1` with exit 0 / OK logs on each. No stuck powershell processes.
- **OneDrive split-brain: RESOLVED.** Canonical scope ratified as the no-suffix `OneDrive - Oxford Capital
  Partners` (egoldberg's synced account); the `(1)` root is a deprecated partial (tombstoned, see Block C).
  Live hygiene-engine paths repointed 2026-07-09.
