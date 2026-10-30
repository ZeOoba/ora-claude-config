# Claude Code / Cowork System Inventory

> **Generated 2026-10-29 16:35 ET** — MANUAL run of `ora-weekly-hygiene` Block H (steps 1-2),
> executed from a Claude Code session; not a scheduled run. The normal writer is Block H (full
> overwrite every run — this file is a snapshot, not a history; report-only). The previous stamp
> (2026-10-06) was 23 days old: `ora-weekly-hygiene` has been disabled in the CC/MCP registry since
> its last run on 2026-09-14, so Block H has not fired since.
> **Treat this file as STALE once its stamp is more than 8 days old**; re-run
> `python maintenance/fleet-status.py --summary` for live fleet state.

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

Unchanged since 2026-10-06. `gh` was probed at its full path `C:\Program Files\GitHub CLI\gh.exe`
— bare `gh` may not resolve on a given session's PATH, so a "not found" from the bare name is
not evidence of absence.

## Plugins

2 entries in `enabledPlugins`, **2 enabled**:

- `superpowers@superpowers-marketplace` — enabled
- `pr-review-toolkit@claude-plugins-official` — enabled

`plugins/installed_plugins.json` lists the same 2 plugins (1:1 with `enabledPlugins`). Unchanged
since 2026-10-06.

**Duplicate-marketplace check: 0 flags.**

## Hooks, agents, commands

Tracked counts are from `git ls-tree origin/main` at `b37f7857` (2026-10-29). The live primary
checkout is behind `origin/main` (it lacks `hooks/rewrite-advisory-guard.py` and
`hooks/tests/test-rewrite-advisory-guard.py`, so it reads 41 / 71 against 42 / 72 tracked).
`settings.json` counts are from the live file.

- **Hooks** (`hooks/`): 42 top-level `.py` hook scripts, 23 `lib/` modules, 72 `tests/test-*.py`
  suites. `settings.json` wires 28 hook `command` entries across 6 events (UserPromptSubmit 1,
  PreToolUse 14, PostToolUse 6, SessionStart 4, Stop 1, SessionEnd 2); PreToolUse Edit/Write and
  Bash calls go through `pretooluse-dispatcher.py` (see README §4a and
  `docs/diagrams/01_hook_lifecycle.mmd`).
- **Agents** (`agents/`): **22 tracked**, 22 on disk — the four listing agents flagged untracked on
  2026-10-06 are now committed. adversarial-reviewer, comms-qc-reviewer, dd-package-sweep,
  deal-flow-triage, deal-recon, estoppel-reconciler, insurance-declaration-checker,
  lease-abstract-verifier, listing-channel-scout, listing-poster, listing-syndication-auditor,
  mfg-investment-scout, noi-opportunity-scout, open-items-triage, portfolio-anomaly-scout,
  psa-redline-checker, repro-isolator, security-auditor, site-qc-reviewer, tax-appeal-scout,
  underwriting-checker, vacancy-listing-packager.
- **Commands** (`commands/`): 13 tracked and on disk — build, cleardisk, cleardisk-sessions,
  debug, handoff, heavy, open-sessions, plan, ram, refactor, research, ship, solo.
- **Task folders** (`scheduled-tasks/`, excluding `_archive*`): 69 on disk. Registry totals below
  are higher because the registry also holds LAMS/Cowork rows and one-time entries.

## Scheduled-task fleet (via `fleet-status.py --summary`, 2026-10-29T16:28:24)

- Total tracked: **94** (enabled 25 / disabled 69) — per-fleet enabled: cc=24, lams=1.
  (2026-10-06: 88 total, 15 enabled.)
- Never-ran: 13 — of which **4 overdue** by cadence: ora-incentive-registry-refresh [cc],
  ora-loan-balance-check [cc], ora-exit-cap-spotcheck [lams], ora-gis-endpoint-liveping [lams].
- One-time fireAt: 4 — 1 EXPIRED (ora-lams-fleet-resume-20260911), a normal completion.
- Missed single cycle (open at generation time): 0. Pause-explained: 0 (2 recorded windows).
- Throttle skips: 21 all-time across 2 tasks (ora-pr-land-watch 11, ora-pm-daily-crons 10); 0 in
  the last 24h. Same-time collisions: 3. Duplicate registrations: 0.
- AM pileup (05:00-09:30): 23 tasks.
- VERDICT: ATTENTION — 4 never-ran past their expected cadence; 3 schedule collisions. Snapshot,
  not live state.
- **Disabled and relevant to this file:** `ora-weekly-hygiene` (its Block H is this file's writer;
  last run 2026-09-14), `ora-doctrine-integrity-guard` (last run 2026-09-14) and
  `ora-task-integrity-guard` (last run 2026-09-14) are all OFF.

**Retired-in-spec cross-check:** 4 task specs mention "RETIRED" in their description
(`ora-am-brief`, `ora-cc-snapshot-refresh`, `ora-doctrine-integrity-guard`,
`ora-task-integrity-guard`); each refers to a retired twin or sibling, not to itself, so
**0 retired/live registry mismatches**.

## Windows Task Scheduler

`maintenance/windows-task-xml/` holds 8 exported ORA tasks. Live state checked 2026-10-29:
`ORA PM Crons` is **Disabled** (superseded by the fleet task `ora-pm-daily-crons`); the other 7
were not re-probed in this run.

## Guard

This refresh edited only this file (in a worktree). No `settings.json`, hook, `CLAUDE.md`, or
memory-file edit was made.
