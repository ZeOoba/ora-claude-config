# Plan: plan-gate enforcement + native plan-path recognition + site-marker dedup

**Size:** small (4 files + tests). Worktree: `.claude/worktrees/plan-gate-and-site-markers` (branch `plan-gate-and-site-markers`, off local HEAD `f678965`).

## Problem 1 — plan-gate override is presence-only, not content-checked
Today's earlier PR #12 fixed `eos-plan-gate.py`'s denial *message* (asks for a reason) but never
changed the actual allow logic — `os.path.exists(override)` still returns ALLOW regardless of
content. 76/79 override markers are still empty even after PR #12 shipped. Separately,
`eos-plan-marker.py` only recognizes `docs/superpowers/plans/` — it does NOT recognize native
Claude Code plan-mode's own output path (`~/.claude/plans/*.md`), confirmed today that THIS
session's own plan file wouldn't have cleared the gate.

## Fix 1
- `eos-plan-gate.py`: change the override check from `os.path.exists` to requiring non-empty
  (non-whitespace) file content before returning ALLOW. Keep fail-open (any read error still
  falls through to existing behavior, never crashes the hook).
- `eos-plan-marker.py`: add `~/.claude/plans/` (both slash forms) to `PLAN_SUBSTR` alongside the
  existing `docs/superpowers/plans/` entries.

## Problem 2 — site-path marker lists have already drifted apart
`ora-autonomy-gate.py`'s `SITE_PATH_MARKERS = ("website-canonical", "oxford-site")` and
`confidentiality-guard.py`'s `SITE_MARKERS = ("oxford-site", "oxfordra.net", "oxfordra_net",
"website-canonical")` are two independently-maintained copies of the same concept — the
confidentiality guard already added domain-form aliases the autonomy gate lacks, meaning a
domain-named path would be leak-scanned but not human-gated for a website write.

## Fix 2
- New `hooks/lib/site_markers.py` (the `hooks/lib/` dir already exists) exporting the union list.
- Both `ora-autonomy-gate.py` and `confidentiality-guard.py` import from it instead of declaring
  their own tuple.

## Tests (TDD — write first, watch fail, then implement)
- `test-eos-plan-gate.py`: new test asserting the override file must have non-empty content to
  allow past the 4-edit threshold (empty file → still denied). All existing tests must still pass.
- `test-eos-plan-marker.py`: new test asserting a `~/.claude/plans/*.md` write creates the
  `plan-approved` marker. All existing tests must still pass.
- `test-ora-autonomy-gate.py` / `test-confidentiality-guard.py`: assert both hooks still recognize
  every marker they did before (no regression), sourced from the same shared list now.

## Out of scope
Batch 2c (scheduled-task registry write-guard) — needs a separate pre-flight to confirm actual
backing file paths before any code is written. Not part of this worktree.

## Land
Local test run (all 4 files' suites) green → self-review against the diff → push branch → PR
(same pattern as PR #12) → merge once CI/review clean → log to `event_log.md` → remove worktree.
