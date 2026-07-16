---
name: shared-checkout-cofile-patch-hazard
description: "On a shared/contaminated checkout, git diff of a file you co-edited with another writer captures THEIR hunks too — inspect per-file diff CONTENT before committing"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b396e8dd-bf47-4574-8642-ede11fbd81eb
---

When landing your own change from a git checkout that also holds **another session's uncommitted work** (the multi-writer situation the [[reference_worktree_node_modules_junction_hazard]] / single-writer doctrine warns about), an **explicit-path patch is NOT sufficient isolation**. If a single file was modified by BOTH you and the other writer, `git diff -- <that file>` (or `git add <that file>`) captures **both** sets of hunks — so an isolated-worktree commit built from that patch silently includes the other writer's work.

**Why:** explicit paths scope WHICH files, not WHICH hunks within a file. `git diff <file>` always emits the whole working-tree-vs-HEAD delta for that file.

**How to apply:**
- Before committing on/from a contaminated checkout, inspect each file's diff **content** (`git diff origin/main..HEAD -- <file>`), not just `--stat`. A line count far larger than your edit (e.g. 53 lines for a one-line doc change) = a co-mingled hunk or a CRLF flip (see [[reference_command_center_crlf_hazard]]).
- If a file is mixed: in the isolated worktree, `git checkout origin/main -- <file>` to reset it, re-apply ONLY your hunk with the Edit tool (EOL-preserving), then `git commit --amend`.
- Real instance 2026-06-15: WAL `busy_timeout` fix landed on `fix/warehouse-busy-timeout` off origin/main; the captured patch for `architecture/system-overview.md` had swept in another session's Module Map table reformat. Caught via per-file content inspection, reset + re-applied the single line, amended. The other writer's WIP stayed intact in the main checkout.
