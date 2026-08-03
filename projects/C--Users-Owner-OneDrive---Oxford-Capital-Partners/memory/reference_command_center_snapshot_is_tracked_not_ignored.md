---
name: reference_command_center_snapshot_is_tracked_not_ignored
description: "oxford-command-center's data/snapshots/portfolio.json is TRACKED in git and auto-committed unattended — the ora-cc-snapshot-refresh task file wrongly calls it git-ignored"
metadata: 
  node_type: memory
  type: reference
  originSessionId: d935c53e-d25d-4d65-ba47-f27485998667
  modified: 2026-08-03T16:04:20.838Z
---

`C:\Users\Owner\oxford-command-center\data\snapshots\portfolio.json` is **tracked in git**, not ignored. It was committed deliberately at `b53c93c` ("Track data/snapshots/portfolio.json in git"). Verify: `git check-ignore -v` returns no match, `git ls-files --error-unmatch` resolves it.

**The `ora-cc-snapshot-refresh` SKILL.md states the opposite** — "this task only writes the git-ignored `data/snapshots/portfolio.json`" — and its Step 1 single-writer reasoning is built on that false premise. Correct the task file when convenient.

**Why it matters:** a sibling automation **commits this file unattended** (`Auto-refresh: lease snapshot (138 leases, no drift)` — `3692385`, `c22cf50`, `ab81db4`, `b0a55e6`). So any bad extract does not merely sit in the working tree; it gets committed under an innocuous message and becomes the baseline that subsequent drift checks diff against — the corruption stops looking like drift and starts looking like the truth. This is exactly the exposure created by [[reference_parseleases_vacancy_block_phantom_leases_2026-08-03]] (left uncommitted-but-dirty 2026-08-03, pending Gabriel's hold-or-revert call).

**How to apply:** treat a `portfolio.json` write as a tracked-file change with real blast radius — check `git status` before and after any extract, and never assume "it's just a snapshot artifact." When an extract produces known-bad data, flag it rather than committing, and say explicitly that the dirty tree is deliberate so another session does not "helpfully" commit it. Related: [[reference_command_center_mirror_deploy_gap]], [[feedback_git_index_is_shared_state]].
