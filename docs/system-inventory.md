# ORA Claude Code — System Inventory

Point-in-time snapshot. **Refreshed 2026-07-22 by `ora-weekly-hygiene` Block H** (Sunday-cadence task; this
was a mid-week catch-up fire) — this task owns keeping the doc current (weekly). Full overwrite each run; no
history preserved here (history → `memory/event_log.md`). Read-only except this one file: Block H flags, it
does not fix.

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

## Claude Code plugins (14 active — dedup CLEAN this pass, 0 flags)
`enabledPlugins` = 14 `true` entries: firecrawl, andrej-karpathy-skills, coderabbit, document-skills,
superpowers, claude-code-setup, claude-md-management, hookify, code-review, commit-commands,
pr-review-toolkit, obsidian (+ frontend-design and claude-api present but `false`). Automated same-name-under-
2-marketplaces dedup check returned **0 duplicate-enabled names** this pass (the 2026-07-07 dedup on
code-review / pr-review-toolkit / superpowers still holds). `installed_plugins.json` present.

## Custom domain agents (`~/.claude/agents/`, 7)
deal-flow-triage, deal-recon, lease-sweep, portfolio-anomaly-scout, security-auditor, site-qc-reviewer,
underwriting-checker. (security-auditor added since the prior snapshot's 6.)

## Custom slash commands (`~/.claude/commands/`, 12)
build, cleardisk, debug, handoff, heavy, open-sessions, plan, ram, refactor, research, ship, solo — the
Engineering OS lane dispatch (L1–L7).

## Hooks (`~/.claude/hooks/`) — directory enumerated this pass
Scripts present: commit-provenance-guard.py, commit-provenance-recorder.py, confidentiality-guard.py,
config-write-guard.py, engineering-router.py, eos-claude-md-guard.py, eos-evidence-gate.py,
eos-gate-sentinel.py, eos-plan-gate.py, eos-plan-marker.py, eos-telemetry.py, fleet-session-hook.py,
git-prepush-confidential-scan.py, git-prepush-doctrine-gate.py, memory-index-guard.py, ora-autonomy-gate.py,
registry-write-guard.py, repo-freshness.py, rules-md-guard.py, shared-checkout-guard.py,
test-ora-autonomy-gate.py — plus `archive/`, `bin/`, `lib/`, `overrides/`, `sessions/`, `tests/`,
`__pycache__/`. (New vs. prior snapshot: commit-provenance-{guard,recorder}, config-write-guard,
memory-index-guard, registry-write-guard, rules-md-guard, bin/, archive/. The config-write-guard is live and
correctly fired this pass — it blocked even a read-shaped Bash command that named settings.json, a known
matcher false-positive; reads should route through Read/Grep, not Bash.)
Lifecycle bindings (from settings.json, last verified 2026-07-07 — not re-parsed this pass; likely stale given
the new guard scripts above).

## Scheduled tasks — VOLATILE (flag, not fixed — Block H is read-only)
`fleet-status.py --summary` this pass: **52 tasks (49 enabled / 3 disabled); per-fleet enabled cc=27, lams=22.**
Both registry files present and read. Fleet grown vs. the prior snapshot (40 enabled) — expected growth
(new: ora-appsec-sweep, ora-cc-snapshot-refresh, ora-tenant-hubspot-reconciliation, ora-underwrite-doctrine-
staleness-check, among others).
Health verdict: **ATTENTION** — 4 never-ran (not yet due) · **2 EXPIRED one-time** (check-appsec-sweep-beacon-
pickup, ora-heartbeat-fix-verify-0718am — 0 missed/stuck, normal completions; candidates for
`delete_scheduled_task` from a fresh session) · **7 throttle skips in last 24h** (ora-pm-ledger=5,
ora-aaos-publish-contracts=1, ora-am-brief=1) · **0 same-time collisions** (the 2026-07-21 ora-deal-aging-sla
retime + fleet-status.py `crons_share_a_day()` fix hold) · 16-task AM pileup (05:00–09:30). The throttle skips
are the documented benign catch-up-burst signature (`reference_fleet_throttle_skip_catchup_burst.md`), not a
per-task defect.

**RETIRED-marker cross-check (Block H spec):** 0 genuine "task self-marked RETIRED in its own SKILL.md
description yet still live." Known retirements (LAMS ora-am-brief → migrated to CC/MCP; ora-dashboard-refresh
removed) are reflected correctly in the live registries — the CC/MCP ora-am-brief copy is legitimately enabled,
the LAMS copy stays retired.

## MCP servers connected (~30)
Notion, HubSpot, Microsoft 365 (Outlook/Calendar/SharePoint), Netlify, Excel, FRED, PDF viewer, scheduled-tasks,
computer-use, claude-in-chrome, context7, Desktop Commander (both Extension + plugin connections live from
Code), plus the standard toolset. Composio and Rube are GONE — never reference them. Full live list is in the
session tool inventory (drifts fastest; not duplicated here).

## Known git repos
`ora-skills` (content repo — no CI, quality-checked by `ora-skill-text-audit`), `website-canonical` /
`oxford-site` (oxfordra.net — invariant-2 protected, not inspected), `oxford-command-center` (**Block I this
pass: 0 broken refs, 0 fsck-missing/error — the 2026-07-07 ref-rot repair of 23 tombstone refs holds; ~20+
benign dangling commits/trees present, gc-able**), brain mirror, `ora-pm`.

## Environment caveats — status this pass
- **Outlook COM send path:** SOLE automated send path (`send-via-outlook.ps1`); Composio fallback removed.
  On COM failure: retry once, flag loudly. Not independently re-probed this pass.
- **OneDrive split-brain: RESOLVED.** Canonical scope = the no-suffix `OneDrive - Oxford Capital
  Partners` (egoldberg's synced account); the `(1)` root is a deprecated partial. Live hygiene-engine paths
  repointed 2026-07-09.
- **Block B onedrive-cleanup engine:** present and ran clean this pass (0 quarantined / 0 purged).
