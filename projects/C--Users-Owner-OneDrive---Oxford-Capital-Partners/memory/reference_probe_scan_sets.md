---
name: reference-probe-scan-sets
description: "What each maintenance/*-probe.py actually globs — read this before trusting any probe's \"all N\" green line; governor-drift is the one live coverage gap."
metadata: 
  node_type: memory
  type: reference
  originSessionId: d6635568-ae53-453c-9bd7-ec8551f96c73
  modified: 2026-07-24T15:26:52.437Z
---

Audited 2026-07-24, all 11 probes. A probe's `[OK]` is only as good as its scan set, and
most scan sets are invisible from the output line. See
[[project-setup-self-audit-frontmatter-probe-2026-07-24]] for the case that prompted this.

| Probe | Scans | Verdict |
|---|---|---|
| `setup-self-audit.py` (skill-frontmatter) | `~/.claude/skills`, Cowork mirror, **+ both fleet roots** via `_sd.skill_folder_root` | FIXED 07-24 (was 57 → now 110) |
| `governor-drift-probe.py` | `memory/`, `CLAUDE.md`, `agents/`, `hooks/`, `maintenance/`, `ora-skills` repo, `oxford-command-center/{src,server,scripts,data}`, **+ both fleet roots** | FIXED 07-24 (643 → 704 files) |
| `doctrine-integrity-probe.py` | `~/.claude/{skills,plugins}` + `Claude_Workspace` | Correct — scoped to CLAUDE.md skill resolution; roots documented inline |
| `memory-integrity-probe.py` | `memory/*.md` only | Correct — that IS its subject |
| `task-folder-registration-probe.py` | both fleet roots via `_sd.skill_folder_root` | Correct |
| `registry-membership-probe.py` / `fleet-status.py` / `cc-verifier-probe.py` | registry JSON via `_shared/store_discovery.py` | Correct — single source is `_shared/scheduler-stores.json` |
| `connector-drift-probe.py` / `open_sessions_probe.py` | connector config / session stores | Correct — scoped |
| `model-currency-probe.py` | `tasks_dir` is a **required CLI arg, no default** | Caller-determined; not registered to any live task (only `plans/` + tests) — dormant |

## governor-drift-probe gap — CLOSED 2026-07-24 (Gabriel-approved)

`build_targets()` scanned neither fleet root while **17 fleet SKILL.md files declare
DSCR/LTV** (`ora-am-brief`, `ora-monthly-portfolio-briefing`, `ora-master-workbook-ingest`,
`ora-underwrite-doctrine-staleness-check`, …), so a governor edit landing in one was
invisible to the Hard-Invariant-4 guard. The tree was clean throughout — latent hole, never
an active breach.

Three changes, all in `governor-drift-probe.py`; **no governor constant was touched**:

1. Both fleet roots added to `build_targets()` (`.md` only). Roots hardcoded, not imported
   from `store_discovery`, to keep the probe pure-stdlib and runnable when that is broken.
2. `iter_files()` prune widened from exact `_archive`/`_staging` to also match the
   `_archive_<date>[_suffix]` convention — **26 such dirs exist and NONE were being pruned**,
   a pre-existing gap independent of the fleet roots. Kept tight (requires the `_` separator)
   because over-pruning a governor guard is a false negative.
3. `RE_SENTINEL_PROSE` suppresses a 1.75 inside the probe's own term of art
   ("1.75 regression sentinel") — `ora-doctrine-integrity-guard`'s SKILL.md documents this
   probe's exit codes and must quote the sentinel to be useful. Span-scoped like the
   correction-note suppressors.

**REFUTE pass (mandatory, governor code) — three attacks, all survived:**
- *Did the new prune drop live coverage?* **0 files** dropped from pre-existing targets,
  0 that would have reported drift. Purely additive.
- *Is exit 0 real or over-suppression?* Re-scanned the fleet roots with the new suppressor
  **disabled**: exactly 1 hit, the known-benign self-documentation line. Not laundering.
- *Is the suppressor evadable?* No — and better than designed: appending "1.75 regression
  sentinel" to a real declaration still flags, because the suppressor silences only branch 1
  (loose proximity) while every explicit-declaration branch stays armed. That asymmetry is
  now pinned by a regression test.

Evidence: governor tests 5 new + all pre-existing pass; all 8 maintenance probe suites pass;
live probe `OK -- 704 files scanned` exit 0; `doctrine-integrity-probe` exit 0.

Related: [[skill-frontmatter-lenient-parse]], [[reference_scheduled_task_staleness_guard_trips]].
