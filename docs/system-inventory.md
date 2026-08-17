# Claude Code / Cowork System Inventory

> **Generated 2026-08-16 20:45 ET** by `ora-weekly-hygiene` Block H. Full overwrite every run — this file is a snapshot, not a history. Report-only: Block H flags findings, it never fixes them.

## Toolchain

| Tool | Version |
| --- | --- |
| git | 2.55.0.windows.2 |
| node | v24.18.0 |
| npm | 11.16.0 |
| python | 3.13.14 |
| ripgrep | 14.1.1 |
| GitHub CLI | 2.96.0 (2026-07-02) |

`gh` was probed at its full path `C:\Program Files\GitHub CLI\gh.exe` — bare `gh` may not resolve on a given session's PATH, so a "not found" from the bare name is not evidence of absence.

## Plugins

5 entries in `enabledPlugins`, **2 enabled**:

- `superpowers@superpowers-marketplace` — enabled
- `pr-review-toolkit@claude-plugins-official` — enabled
- `claude-md-management@claude-plugins-official` — disabled
- `code-review@claude-plugins-official` — disabled
- `commit-commands@claude-plugins-official` — disabled

**Duplicate-marketplace check: 0 flags.** No plugin name appears under two marketplace keys with more than one copy `true`. The duplication fixed on 2026-07-07 has not recurred.

## Hooks, agents, commands

| Surface | Count |
| --- | --- |
| Hook scripts (`hooks/*.py`, `hooks/*.ps1`) | 31 |
| Custom agents (`agents/`) | 9 |
| Custom commands (`commands/`) | 13 |

Two hooks were observed firing correctly during this run and are worth recording as live-verified rather than merely present:

- **`eos-plan-gate`** blocked at the 4-file threshold and accepted a written override reason.
- **`config-write-guard`** blocked a Bash command that merely *named* `settings.json` inside a `python -c` read. That is the documented breadth-over-precision behaviour, and the correct response was to re-run the read through Grep rather than mint `allow-config-write` — which is what happened. No token was minted.

## Scheduled-task fleet

From `maintenance/fleet-status.py --summary` (reads both registries regardless of surface):

| Metric | Value |
| --- | --- |
| Total tasks | 65 (63 enabled / 2 disabled) |
| Per-fleet enabled | CC/MCP 37 · LAMS/Cowork 26 |
| Never-ran | 11 (0 overdue — none yet due by cadence) |
| One-time `fireAt` | 6 (1 expired: `ora-cam-data-backfill`) |
| Missed single cycle (open) | 0 |
| Throttle skips, last 24h | 3 (`ora-am-brief` 2, `ora-aaos-publish-contracts` 1) |
| Same-time collisions | 0 |
| AM pileup (05:00–09:30) | 22 tasks |

**Verdict from the probe: ATTENTION** — 3 throttle skips in 24h and one task registered on both fleets.

### Flag 1 — dual-fleet registration

`ora-passed-deal-tracker` is registered on **both** CC/MCP and LAMS/Cowork. Per the probe's own note this is not a collision and is not safe to clean up casually: the sidebar delete is folder-destructive, the two fleets take opposite archive/delete orderings, and a pair can share one `SKILL.md` path. Check each registry entry's description for a deliberate migration before touching it. **Screen finding — not fixed here.**

### Flag 2 — retired/live mismatches: **0**

Method stated so the null is verifiable rather than inferred: every live task folder's own frontmatter `description` was scanned for a RETIRED marker. Fourteen `SKILL.md` files contain the word "RETIRED" somewhere in the body, and five carry it inside the description — but in all five (`ora-am-brief`, `ora-doctrine-integrity-guard`, `ora-entry-market-scan`, `ora-open-sessions-board`, `ora-task-integrity-guard`) the word refers to a *different* task, most often a retired LAMS twin. **No task declares itself retired while remaining live in a registry.**

## Repository health

`oxford-command-center`: **59 refs, 0 broken, 0 `missing` objects.** `git fsck --connectivity-only` reports 275 dangling objects — unreferenced but present, the normal residue of heavy worktree and branch churn, and categorically different from the 23 broken refs of the 2026-07-07 incident. No repair was run; Block I is detection-only.

Cross-repo uncommitted-WIP aging (`cross-repo-wip-scan.py`), all under the 48h threshold:

| Repo | Uncommitted | Oldest |
| --- | --- | --- |
| `~/.claude` | 30 | 29.7h |
| `ora-skills` | 2 | 4.6h |
| `oxford-command-center` | 1 | 5.8h |
| `AAOS`, `ora-pm`, `website-canonical` | 0 | — |

Nothing is `[ACTION] STALE` or `[ACTION] MISSING`, but the `~/.claude` backlog at 30 items / 29.7h is within 18 hours of tripping the flag and is the one to watch.

## Guard / contract probes

- `fleet-contract-check.py` — **all 3 seeded producer contracts fresh** (registry-membership→doctrine-status 8.9h, write-doctrine-status→prepush gate 3.1h, emit-fleet-heartbeat→watchdog 8.9h).
- `check-open-items-duplicate-ids.py` — **clean**: 175 rows, 175 unique ids, 162 detail sections, 0 collisions.
- `eos-telemetry-rollup.py` — 568 coding sessions; `verification_seen` 92.4%, `lane_declared` 52.5%, `bash_test_ran` 45.6%, `task_dispatched` 41.7% of the 266-session dispatch-capable cohort (the weakest signal).
