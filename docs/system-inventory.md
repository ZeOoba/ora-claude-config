# ORA Claude Code — System Inventory

Point-in-time snapshot. **Refreshed 2026-07-07 (evening) by `ora-weekly-hygiene` Block H** — this task now
owns keeping the doc current (weekly, Sunday 20:00), resolving the prior "no owning task" open item. Full
overwrite each run; no history preserved here (history → `memory/event_log.md`).

## Hardware / OS
- Windows 11 Home, build 10.0.26200
- RAM: 32 GB physical (LAPTOP-CSHSCBE6, ASUS Zenbook S14 — in service 2026-07); working ceiling
  ~24 GB (OS/app headroom). Retuned 2026-07-09 from the old 5.7 GB box (RAM_POSTURE=RETUNE-32GB);
  Engineering OS concurrency guidance keys off the ~24 GB working ceiling. Still no RAM-heavy
  standing services (Docker Desktop etc.) without justification — nothing here needs them.

## Toolchain (verified present this pass)
- git 2.55.0.windows.2
- node v24.18.0 / npm 11.16.0
- python 3.13.14 / pip 26.1.2
- ripgrep 14.1.1
- GitHub CLI 2.96.0 (2026-07-02) — at `C:\Program Files\GitHub CLI\gh.exe`; confirmed working via full
  path this pass. Bare-`gh` PATH resolution from the Bash tool remains a harness-PATH-snapshot matter;
  invoke by full path when in doubt.

## Not present (confirmed absent, not just off-PATH)
pnpm, uv, Docker, VS Code CLI (`code`), fd, fzf, jq, yq, make, just — none justified by any live workflow.
Do not install Docker/Postgres/Redis: nothing here needs containers or a server DB (QuickBooks Desktop +
Notion + HubSpot are the data layer, already MCP-wired); even on the 32 GB box a standing Docker VM is
unjustified footprint.

## Claude Code plugins (17 installed, 14 active — dedup CLEAN this pass, 0 flags)
The 2026-07-07 dedup held: `code-review`, `pr-review-toolkit`, and `superpowers` each appear under two
marketplace keys, but exactly ONE copy of each is `enabledPlugins:true` — no re-regression to the
double-enabled state. Kept copies: `code-review@claude-plugins-official`,
`pr-review-toolkit@claude-plugins-official`, `superpowers@superpowers-marketplace`; the older copies stay
`false`.
Active: firecrawl, superpowers, frontend-design, andrej-karpathy-skills, code-review, coderabbit,
claude-api, document-skills, pr-review-toolkit, claude-code-setup, claude-md-management, hookify,
commit-commands. Installed-but-disabled: chrome-devtools-mcp@chrome-devtools-plugins (still off — confirm
if wanted or dead weight).

## Custom domain agents (`~/.claude/agents/`, 6)
deal-flow-triage, deal-recon, lease-sweep, portfolio-anomaly-scout, site-qc-reviewer, underwriting-checker.

## Custom slash commands (`~/.claude/commands/`, 12)
build, cleardisk, debug, handoff, heavy, open-sessions, plan, ram, refactor, research, ship, solo — the
Engineering OS lane dispatch (L1–L7).

## Hooks (`~/.claude/hooks/`) — bindings from `settings.json` this pass
- **UserPromptSubmit:** engineering-router.py
- **PreToolUse:** confidentiality-guard.py · eos-evidence-gate.py · eos-plan-gate.py · ora-autonomy-gate.py
  · shared-checkout-guard.py
- **PostToolUse:** eos-gate-sentinel.py · eos-plan-marker.py · fleet-session-hook.py
- **SessionStart:** fleet-session-hook.py · repo-freshness.py
- **Stop:** fleet-session-hook.py
- **SessionEnd:** eos-telemetry.py · fleet-session-hook.py

Also in the dir but not lifecycle-bound in settings (git-hook / standalone / test): git-prepush-confidential-scan.py,
ram-guard.ps1, ram-watchdog.sh, test-ora-autonomy-gate.py, plus `overrides/`, `sessions/`, `tests/` subdirs.
(Live confidentiality proof this pass: the PreToolUse confidentiality-guard fail-closed on a Block C Notion
write that named a confidential deal folder — working as designed.)

## Permissions
102 allow · 24 deny · 0 ask (unchanged).

## Scheduled tasks — ⚠️ VOLATILE / UNRECONCILED (flag, not fixed — Block H is read-only)
`fleet-status.py --summary` this pass: **27 tasks, all enabled (cc=8, lams=19).** CC-live 8:
ora-deal-sourcing-scan, ora-financial-code-integrity-sweep, ora-health-guard, ora-master-workbook-ingest,
ora-monthly-portfolio-briefing, ora-pm-ledger, ora-task-integrity-guard, ora-weekly-hygiene.

**Three sources disagree — needs Gabriel's reconciliation, NOT an autonomous fix:**
1. This pass reads **both** registry files present (`claude-code-sessions` + `local-agent-mode-sessions`).
2. The SessionStart-generated fleet roster (2026-07-07 11:51) says **lams=8**; the live registry + fleet-status
   say **lams=19**.
3. `event_log.md` (2026-07-07, earlier) states the **CC/MCP registry file was GONE** (0 tasks) — yet it
   exists now with 8. So the store was recreated/restored between that entry and this pass, with nothing
   logging the recreation.
Health verdict from fleet-status: ATTENTION — 14 never-ran, 5 throttle skips (over ceiling), 5 same-time
collisions, 14-task AM pileup (05:00–09:30).

**RETIRED-marker cross-check (Block H spec):** 0 genuine "task self-marked RETIRED in its own SKILL.md
description yet still live" this pass. (One grep hit — `ora-automation-health-monitor` — was a false
positive: "retired" there refers to a retired *connector* (Composio/Rube), not the task; and the live LAMS
id is `automation-health-monitor` without the `ora-` prefix anyway. The prior doc's `ora-setup-audit` /
`ora-weekly-tooling-intel-sweep` zombie flag no longer reproduces on the CC side — `ora-setup-audit` is not
in the current CC-live 8.)

## MCP servers connected (~30)
Notion, HubSpot, Microsoft 365 (Outlook/Calendar/SharePoint), Netlify, Excel, PDF viewer, scheduled-tasks,
computer-use, claude-in-chrome, context7, Mnemoverse Memory, Desktop Commander, plus the standard toolset.
Composio and Rube are GONE (removed 2026-06-11) — never reference them. Full live list is in the session
tool inventory (drifts fastest; not duplicated here).

## Known git repos
`ora-skills` (content repo — no package.json/CI, quality-checked by `ora-skill-text-audit`),
`website-canonical` / `oxford-site` (oxfordra.net — invariant-2 protected, not inspected),
`oxford-command-center` (**Block I this pass: 0 broken refs, 0 fsck-missing — the 2026-07-07 ref-rot
repair of 23 tombstone refs held; ~20 benign dangling commits present, gc-able; 100 refs / 21 worktrees**),
`oxford-perfection` (ad-hoc diagnostic-script pile), brain mirror, `ora-pm`.

## Environment caveats surfaced this pass (2026-07-07)
- **Outlook COM send path DOWN** — machine-wide; all automation email delivery failing today
  (RPC_E_CALL_REJECTED / E_ABORT / indefinite hang). Outlook.exe runs but rejects automation. Blocks every
  scheduled task's email output until cleared (likely a modal dialog or COM contention; 13 stuck powershell
  processes observed). This is the top operational issue right now.
- **Two OneDrive business roots coexist** post-migration: `OneDrive - Oxford Capital Partners` (no suffix,
  canonical) and `...(1)` (pre-migration). `Documents\Claude\outputs` + several hygiene-engine hardcoded
  paths still point at `(1)`; canonical `Documents\Claude` has no `Outputs`/`Workspace`. Split-brain to
  reconcile.
