---
name: reference-git-merge-blocks-on-identical-dirty-files-targeted-deploy
description: "A working file byte-identical to the incoming merge version STILL blocks git merge (staged or unstaged), so the drifted shared ~/.claude checkout cannot merge-forward while any overlapping dirty path exists. To ship one merged file to the fleet, do a targeted single-file swap, not a merge. Proven by scratch clone 2026-09-19."
metadata:
  node_type: memory
  type: reference
---

**The trap.** The fleet executes the WORKING TREE of the shared `~/.claude` checkout, which sits on a
long-drifted branch (179 commits behind origin/main on 2026-09-19). A merged PR to a fleet-shared
script therefore does not reach production ([[reference_scheduled_task_staleness_guard_trips]]-adjacent:
"merged is not deployed"). The corrector, `maintenance/checkout-merge-forward.py`, refuses over any
staged content, any live overlapping claim, and any overlapping dirty path.

**What a scratch clone proved (git 2.55, `core.autocrlf` on AND off):**
- A file byte-identical to the incoming merge version blocks `git merge --no-commit --no-ff` with
  "local changes would be overwritten" whether it is STAGED or UNSTAGED. Identical content is no shield,
  so unstaging such a file gains nothing. It is also not a line-ending artifact.
- `git restore --source=HEAD --staged --worktree <path>` on just that path lets the merge succeed
  (the merge recreates the identical content), and unrelated dirty files upstream never touches are fine.
- ONE other dirty path that upstream also changes blocks the WHOLE merge. Measure that overlap first
  (upstream-changed ∩ dirty), not the raw dirty count: 23 tracked + 4 untracked here.

**How to apply.** To deploy one merged file to the fleet without touching other sessions' WIP: confirm
the path is clean and unstaged, take a rollback copy, write `git cat-file --filters origin/main:<path>`
over it (applies the same line-ending conversion a checkout would), verify `git hash-object <path>`
equals `git rev-parse origin/main:<path>`, confirm the staged set did not change, then prove it with a
real run. Before any later merge-forward, `git restore --source=HEAD` that path so it is not a new
blocker. Needs Gabriel's in-turn approval and a short-lived `allow-config-write` token, deleted
immediately after — never left for its 60 minutes. Worked example and residual risks: OI-326.

Related: [[feedback_git_index_is_shared_state]], [[feedback_preexisting_failure_verify_against_push_target]].
