# ORA Claude Code — System Inventory

Point-in-time snapshot. **Refreshed 2026-07-26 by `ora-weekly-hygiene` Block H** (Sunday cadence) — this task
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
- ripgrep 14.1.1 (rev f6d0fcd24a)
- GitHub CLI 2.96.0 (2026-07-02) — at `C:\Program Files\GitHub CLI\gh.exe`; confirmed working via full
  path this pass. Invoke by full path when in doubt (bare-`gh` PATH resolution from the Bash tool is a
  harness-snapshot matter, not evidence of absence).

## Not present (confirmed absent previously; not re-probed this pass)
pnpm, uv, Docker, VS Code CLI (`code`), fd, fzf, jq, yq, make, just — none justified by any live workflow.
Do not install Docker/Postgres/Redis: QuickBooks Desktop + Notion + HubSpot are the data layer (MCP-wired).

## Claude Code plugins (14 enabled — dedup CLEAN this pass, 0 flags)
`settings.json` → `enabledPlugins` = **14** entries. `installed_plugins.json` present (schema
`{version, plugins}`). The automated same-name-under-2-marketplaces check returned **0 duplicate-enabled
names** — the 2026-07-07 dedup on code-review / pr-review-toolkit / superpowers still holds.

## Custom domain agents (`~/.claude/agents/`, 7)
deal-flow-triage, deal-recon, lease-sweep, portfolio-anomaly-scout, security-auditor, site-qc-reviewer,
underwriting-checker.

## Custom slash commands (`~/.claude/commands/`, 12)
build, cleardisk, debug, handoff, heavy, open-sessions, plan, ram, refactor, research, ship, solo — the
Engineering OS lane dispatch (L1–L7).

## Hooks (`~/.claude/hooks/`) — 25 `*.py` scripts this pass (was 21)
Directory enumerated; count is up 4 vs. the 2026-07-22 snapshot. Subdirectories present: `archive/`, `bin/`,
`lib/`, `overrides/`, `sessions/`, `tests/`, `__pycache__/`.

**Live-fire note this pass:** `ora-autonomy-gate.py` blocked two Bash commands whose only connection to the
site tree was the literal string `oxford-site` inside a quoted *read* path (a PDF being tested for a text
layer) combined with an unrelated `>` elsewhere in the command. Per the hook's own guidance no override was
minted — the work was re-run via the Write tool and a marker-free command instead. This is the documented
match-anywhere false-positive class, behaving as designed (fail-closed), not a defect.

Lifecycle bindings (from `settings.json` → `hooks`) last verified 2026-07-07 — **not re-parsed this pass; treat
as stale** given the 4 new guard scripts since.

## Scheduled tasks — VOLATILE (flag, not fixed — Block H is read-only)
`fleet-status.py --summary` this pass: **55 tasks (53 enabled / 2 disabled); per-fleet enabled cc=28, lams=25.**
Both registry files present and read. Fleet grown vs. the prior snapshot (52 / 49 enabled).

Health verdict: **ATTENTION** — driven solely by throttle skips.
- Never-ran: **7** — all not-yet-due by cadence, **0 overdue**.
- **EXPIRED one-time entries still in the registry: 2** → `ora-claude-config-push-when-settled`,
  `ora-override-sweep-dryrun-check`. Both are normal completions (0 missed/stuck); they are candidates for
  `delete_scheduled_task` from a fresh session. *Standing pattern: expired one-time entries linger until
  explicitly deleted — the same finding appeared on 2026-07-22 with a different pair.*
- Throttle skips: 136 all-time across 14 tasks; **14 in the last 24h** (`ora-override-sweep-dryrun-check`=6,
  `ora-doctrine-integrity-guard`=5, `ora-am-brief`=2, `ora-aaos-publish-contracts`=1). This is the documented
  benign catch-up-burst signature (`reference_fleet_throttle_skip_catchup_burst.md`), not a per-task defect.
- Same-time collisions: **0**. AM pileup (05:00–09:30): **19 tasks** (was 16).

**RETIRED-marker cross-check — 0 genuine mismatches, but the check itself is mis-specified.**
A naive substring scan of the first 20 lines of all **48** task `SKILL.md` files returns 7 hits; narrowing to
the frontmatter `description` returns 4. All 4 are FALSE POSITIVES — each uses "retired" about something other
than the task itself:

| Task | What is actually described as retired |
|---|---|
| `ora-am-brief` | its superseded **LAMS** registration (the CC/MCP copy must stay enabled) |
| `ora-doctrine-integrity-guard` | the superseded **"ORA EOS Health" Windows task** |
| `ora-open-sessions-board` | the retired **`(1)`-suffixed OneDrive memory scope** |
| `ora-task-integrity-guard` | the retired **MODEL-CURRENT / MODEL-STALE status labels** |

**Screen recommendation:** a substring match on a free-text `description` cannot make this check actionable —
it will keep yielding 4 false positives weekly. It needs a structured marker (e.g. a literal `status: RETIRED`
frontmatter key) to be worth anything.

## MCP servers connected (~30)
Notion, HubSpot, Microsoft 365 (Outlook/Calendar/SharePoint), Netlify, Excel, FRED, PDF viewer, scheduled-tasks,
computer-use, claude-in-chrome, context7, Desktop Commander (both Extension + plugin connections live from
Code), plus the standard toolset. Composio and Rube are GONE — never reference them. Full live list is in the
session tool inventory (drifts fastest; not duplicated here).

## Known git repos
`ora-skills` (content repo — no CI, quality-checked by `ora-skill-text-audit`), `website-canonical` /
`oxford-site` (oxfordra.net — invariant-2 protected, not inspected), `oxford-command-center` (**Block I this
pass: 29 refs, 0 broken, 0 fsck missing/error; 232 benign dangling objects, gc-able** — the 2026-07-07
ref-rot repair of 23 tombstone refs holds), brain mirror, `ora-pm`.

## Environment caveats — status this pass
- **Outlook COM send path:** SOLE automated send path (`send-via-outlook.ps1`); Composio fallback removed.
  On COM failure: retry once, flag loudly.
- **OneDrive split-brain: RESOLVED.** Canonical scope = the no-suffix `OneDrive - Oxford Capital
  Partners` (egoldberg's synced account); the `(1)` root is a deprecated partial.
- **Block B onedrive-cleanup engine:** present and ran clean this pass (0 quarantined / 0 purged).
- **`Claude_Workspace` folder names diverge from the ora-weekly-hygiene spec.** The tree actually has
  `02_Outputs/` and `03_Code/`; the Block A/C spec text still names `02_Phase_Outputs/`, `03_Tool_Outputs/`
  and `04_Code_and_Previews/`. Blocks are being run against the real folders. Worth reconciling the spec text.
