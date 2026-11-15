# Claude Code / Cowork System Inventory

> **Generated 2026-11-08 20:36 ET** — `ora-weekly-hygiene` Block H, scheduled run (Sunday
> 2026-11-08, on-cadence; prior fire 2026-11-02 was itself a catch-up fire after a 7-week gap).
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

Unchanged since 2026-10-06/10-29/11-02. `gh` was probed at its full path
`C:\Program Files\GitHub CLI\gh.exe` — bare `gh` may not resolve on a given session's PATH, so a
"not found" from the bare name is not evidence of absence.

## Plugins

3 entries in `enabledPlugins`, **3 enabled** (up from 2 on 2026-11-02 — `ora-ops-panel@ora-mods`
installed 2026-11-07):

- `superpowers@superpowers-marketplace` — enabled
- `pr-review-toolkit@claude-plugins-official` — enabled
- `ora-ops-panel@ora-mods` — enabled

`plugins/installed_plugins.json` lists the same 3 plugins (1:1 with `enabledPlugins`), each under
exactly one marketplace key.

**Duplicate-marketplace check: 0 flags.**

## Hooks, agents, commands

Live counts on disk (2026-11-08):

- **Hooks** (`hooks/`): 42 top-level `.py` hook scripts, 23 `lib/` modules, 73 `tests/test-*.py`
  suites. `settings.json` wires hook `command` entries across 6 events (UserPromptSubmit 1,
  PreToolUse 11 matcher blocks, PostToolUse 5 matcher blocks, SessionStart 4, Stop 1,
  SessionEnd 2).
- **Agents** (`agents/`): 22 on disk — adversarial-reviewer, comms-qc-reviewer, dd-package-sweep,
  deal-flow-triage, deal-recon, estoppel-reconciler, insurance-declaration-checker,
  lease-abstract-verifier, listing-channel-scout, listing-poster, listing-syndication-auditor,
  mfg-investment-scout, noi-opportunity-scout, open-items-triage, portfolio-anomaly-scout,
  psa-redline-checker, repro-isolator, security-auditor, site-qc-reviewer, tax-appeal-scout,
  underwriting-checker, vacancy-listing-packager.
- **Commands** (`commands/`): 13 on disk — build, cleardisk, cleardisk-sessions, debug, handoff,
  heavy, open-sessions, plan, ram, refactor, research, ship, solo.
- **Task folders** (`scheduled-tasks/`, excluding `_archive*`): **76** on disk — up from 75 on
  2026-11-02 (+1; not reconciled against the registry this run). Registry totals below are higher
  because the registry also holds LAMS/Cowork rows and one-time entries.

**Git tracking state (coverage gap — not re-verified against `git ls-tree origin/main`):** the
live primary checkout is on branch `live/primary-checkout`, **29 commits behind `origin/main`**,
with **5 uncommitted items** (oldest ~50.7h) per `cross-repo-wip-scan.py` (Block I, this run) —
flagged `[ACTION] BRANCH_DRIFT` and `[ACTION] STALE`. Block I additionally flagged
`[ACTION] CORRECTOR_STUCK`: the `ora-checkout-merge-forward` corrector has not synced in 4
consecutive runs since 2026-11-05 (last status `BLOCKED_CONFLICT`) — remedy is the
`dirty-tree-triage` skill, a supervised in-session action, not something this block attempts. The
on-disk counts above may not match what's tracked at `origin/main`'s tip.

## Scheduled-task fleet (via `fleet-status.py --summary`, 2026-11-08T20:36:26)

- Total tracked: **101** (enabled 49 / disabled 52) — per-fleet enabled: cc=48, lams=1.
- Never-ran: 12 — of which **4 overdue** by cadence: ora-incentive-registry-refresh [cc],
  ora-loan-balance-check [cc], ora-exit-cap-spotcheck [lams], ora-gis-endpoint-liveping [lams]
  (unchanged from 2026-11-02).
- One-time fireAt: 5 — 1 EXPIRED (ora-lams-fleet-resume-20260911), a normal completion.
- Missed single cycle (open at generation time): **1** — ora-pm-monthly-billing (44.0h open).
- Throttle skips: 207 all-time across 14 tasks; 0 in the last 24h (no active catch-up burst this
  run, unlike 2026-11-02's 100/24h).
- Same-time collisions: 5 — 10:00 {ora-claude-setup-audit, ora-cc-acq-sync-weekly}; 10:50
  {ora-edge-news-overlay-refresh, ora-rep-hours-monthly, ora-tenant-contact-gap-sweep}; 11:05
  {ora-automation-health-monitor, automation-health-monitor}; 11:30 {ora-full-gate-weekly,
  ora-ar-export-freshness-nudge}; 14:10 {ora-audit-log-sweep, ora-site-seo-crawl-weekly}.
  Duplicate registrations (same id on both fleets, by design per registry notes): 2 —
  ora-cowork-heartbeat, ora-owner-outreach-queue-refresh.
- AM pileup (05:00-09:30): 22 tasks.
- VERDICT: ATTENTION — 4 never-ran past cadence; 1 missed-cycle (open); 5 collisions; 2 dual-fleet
  registrations. Snapshot, not live state — re-run before acting.
- **This file's own writer:** `ora-weekly-hygiene` ran on-cadence today (2026-11-08),
  `nextRunAt` ~2026-11-15.

**Retired-in-spec cross-check (grep-based on frontmatter `description:` line only — coverage
caveat):** 21 non-archived SKILL.md files contain the string "RETIRED" somewhere in the body; of
those, only 4 (ora-am-brief, ora-cc-snapshot-refresh, ora-doctrine-integrity-guard,
ora-task-integrity-guard) carry it in their own frontmatter `description:` line, and in every case
it reads as a reference to a *sibling/twin* task or a *different, superseded* task being retired
(e.g. "the superseded LAMS registration is being retired separately"), never a self-description —
**0 retired/live registry mismatches found**, consistent with prior runs.

## Windows Task Scheduler

Not re-probed this run (coverage gap) — last live-checked 2026-10-29: `maintenance/windows-task-xml/`
holds 8 exported ORA tasks; `ORA PM Crons` was Disabled (superseded by `ora-pm-daily-crons`); the
other 7 were not re-probed then either.

## Guard

This refresh edited only this file. No `settings.json`, hook, `CLAUDE.md`, or memory-file edit was
made.
