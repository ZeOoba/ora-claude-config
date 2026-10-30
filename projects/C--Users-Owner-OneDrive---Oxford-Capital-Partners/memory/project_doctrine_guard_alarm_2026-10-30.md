---
name: project-doctrine-guard-alarm-2026-10-30
description: "ora-doctrine-integrity-guard 10-30 run — governor probe flagged (likely false positive), 7 repo-first cache violations, 1 backup-coverage ACTION"
metadata:
  node_type: memory
  type: project
  originSessionId: 8c91520b-12e2-43bc-ad02-11c820f640b4
  modified: 2026-10-30T15:31:55.368Z
---

`ora-doctrine-integrity-guard` scheduled run, 2026-10-30, alarmed on 3 of 10 engines; Notion posted ([page](https://app.notion.com/p/4096ecd89e598197bfe1dc9dc359cc18)) + email sent to ggoldberg@oxfordra.net. 7 other engines clean (doctrine 15 WARN fail-open, telemetry, backup-session-context, spec-liveness, xref, retired-skill-guard, pending-reimport-backfill all OK).

1. **governor-drift-probe.py exit 1** — flagged `ora-skills/acquisition-underwriting/versions/CHANGELOG.md:52` (v4.37 entry) as a DSCR-threshold mismatch and an LTV-governor mismatch. Reading the line: it is exit-cap arithmetic (per-property refi-ceiling ratio times the canonical DSCR times the debt constant) plus the entry's own disclosure that no governor constant changed. FALSE POSITIVE, not a constant change — same class as [[project_governor_drift_probe_dscr_scaling_multiplier_fix_2026-08-22]]. **RESOLVED (2026-10-30, weekly-priorities session):** ora-claude-config #368 (merged 15:2x Z today) exempts `<skill>/versions/CHANGELOG.md`; this run alarmed only because the LIVE `~/.claude` checkout is 36 commits behind origin/main and still runs the pre-#368 probe. Fast-forwarding the live checkout clears it. (Numerals deliberately not quoted here: a verbatim quote of the flagged text made this note itself trip the probe and block every ora-claude-config push.)
   **Why:** the probe is authoritative/report-only by design — this guard cannot and must not adjudicate for itself.
   **How to apply:** before relying on a future governor-drift alarm citing a CHANGELOG.md line, check whether the matched text is citing canonical constants (as unchanged) vs. actually redefining them.

2. **repo_first_check.py --all** — 7 REPO-FIRST findings (exit code always 0, read output): `acquisition-underwriting` (DIVERGENT, SKILL.md), `acquisition-underwriting-eval-harness` (CACHE-AHEAD, runs/summary.csv), `county-parcel-screen` (CACHE-AHEAD, SKILL.md), `deal-folder-intake` (DIVERGENT, SKILL.md), `loi-generation` (DIVERGENT+CACHE-AHEAD, 9 files incl. 2 with no repo counterpart on any branch), `repo-architecture` (DIVERGENT, SKILL.md), `submarket-spatial-analysis` (DIVERGENT, SKILL.md). Rescued to `ora-skills/_staging/repo-first-rescue/<skill>/`. Unreconciled, the next mirror sync overwrites each. 5 older ledger entries cleared as resolved this run (artifact-to-docx-report, deal-comparison, lease-form-qc, masterlease-jurisdiction-rebase, masterlease-revision-cycle).
   **Why:** DIVERGENT = cache installed off this branch's ancestry (branch reconciliation needed, never auto-reimport); CACHE-AHEAD = platform-side edit never committed.
   **How to apply:** before trusting the installed/cached version of any of these 7 skills, reconcile against the repo first — do not assume the runtime cache is current.

3. **reference-backup-coverage-probe.py exit 1** — `maintenance/_state/checkout-merge-forward-last-run.json` referenced by a tracked file (`maintenance/_archive/2026-09-22_weekly-window/maintenance/cross-repo-wip-scan.py`, +3 more) but itself untracked and not gitignored. Needs a one-line disposition: git-add it, gitignore it, or add to `maintenance/_shared/reference-backup-exempt.json` with a dated reason.

**OPEN, awaiting Gabriel:** all three items above — guard is detect-only, never corrects.
