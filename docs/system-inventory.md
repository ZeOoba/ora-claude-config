# Claude Code / Cowork System Inventory

> **Generated 2026-10-06 15:45 ET** — MANUAL refresh (repo-eval Phase 0, worktree branch
> `docs/phase0-ci-hardening`), not a Block H run. The normal writer is `ora-weekly-hygiene`
> Block H (full overwrite every run — this file is a snapshot, not a history; report-only).
> The previous stamp (2026-09-14) was 22 days old because Block H had not overwritten it.
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

Unchanged since 2026-09-14. `gh` was probed at its full path `C:\Program Files\GitHub CLI\gh.exe`
— bare `gh` may not resolve on a given session's PATH, so a "not found" from the bare name is
not evidence of absence.

## Plugins

2 entries in `enabledPlugins` (down from 4 at the 2026-09-14 run), **2 enabled**:

- `superpowers@superpowers-marketplace` — enabled
- `pr-review-toolkit@claude-plugins-official` — enabled

**CHANGE since 2026-09-14:** the two previously-disabled entries (`code-review@claude-plugins-official`,
`commit-commands@claude-plugins-official`) are gone from `settings.json` → `enabledPlugins`, and
`plugins/installed_plugins.json` now lists the same 2 plugins (1:1 with `enabledPlugins`). Both
were disabled, so this reads as a clean uninstall, not config loss.

**Duplicate-marketplace check: 0 flags.**

## Hooks, agents, commands

Tracked counts are from `git ls-tree origin/main` at `11cce1d` (2026-10-06); on-disk counts are
from the live `~/.claude` directory.

- **Hooks** (`hooks/`): 36 top-level `.py` hook scripts, 19 `lib/` modules, 61 `tests/test-*.py`
  suites. `settings.json` wires 28 hook `command` entries across 6 events (UserPromptSubmit,
  PreToolUse, PostToolUse, SessionStart, Stop, SessionEnd); PreToolUse Edit/Write and Bash calls go
  through `pretooluse-dispatcher.py` (see README §4a and `docs/diagrams/01_hook_lifecycle.mmd`).
- **Agents** (`agents/`): **17 tracked**, **21 on disk**. The 4 on-disk-only definitions —
  `listing-channel-scout`, `listing-poster`, `listing-syndication-auditor`,
  `vacancy-listing-packager` — are untracked new files in the live checkout (not ignored, never
  committed on any branch). Flagged for a human glance; not acted on.
  Tracked: adversarial-reviewer, comms-qc-reviewer, dd-package-sweep, deal-flow-triage,
  deal-recon, estoppel-reconciler, insurance-declaration-checker, lease-abstract-verifier,
  noi-opportunity-scout, open-items-triage, portfolio-anomaly-scout, psa-redline-checker,
  repro-isolator, security-auditor, site-qc-reviewer, tax-appeal-scout, underwriting-checker.
- **Commands** (`commands/`): 13 tracked and on disk — build, cleardisk, cleardisk-sessions,
  debug, handoff, heavy, open-sessions, plan, ram, refactor, research, ship, solo.

## Scheduled-task fleet (via `fleet-status.py --summary`, 2026-10-06T15:44:59)

- Total tracked: **88** (enabled 15 / disabled 73) — per-fleet enabled: cc=14, lams=1.
  (2026-09-14: 67 total, 66 enabled. The large disabled share is a fleet-level pause/state
  change since the last run; verify against `list_scheduled_tasks` before acting.)
- Never-ran: 21 — of which **5 overdue** by cadence: ora-incentive-registry-refresh [cc],
  ora-passed-deal-tracker [cc], ora-sourcing-construction-verify [cc],
  ora-exit-cap-spotcheck [lams], ora-gis-endpoint-liveping [lams].
- One-time fireAt: 6 — 3 EXPIRED (ora-county-sales-refresh-1003,
  ora-lams-fleet-resume-20260911, ora-notion-trial-expiry-reminder), all normal completions.
- Missed single cycle (open at generation time): 0. Pause-explained: 0 (0 recorded windows).
- Throttle skips: 0 (all-time and last 24h). Same-time collisions: 0. Duplicate registrations: 0.
- AM pileup (05:00-09:30): 23 tasks.
- VERDICT: ATTENTION — 5 never-ran past their expected cadence. Snapshot, not live state.

**Retired-in-spec cross-check:** not repeated in this manual refresh (last done 2026-09-14,
0 mismatches on the sample checked).

## Guard

This refresh edited only this file (in a worktree). No `settings.json`, hook, `CLAUDE.md`, or
memory-file edit was made.
