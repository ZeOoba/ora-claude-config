---
name: reference-worktree-wrong-base-branch-2026-08-21
description: "Always pass an explicit base ref to `git worktree add -b <branch>` in the shared ~/.claude checkout -- with none given it branches from the checkout's CURRENT branch, which in a shared checkout is often another session's live feature branch, not main."
metadata: 
  node_type: memory
  type: reference
  originSessionId: ebb79ea0-b175-4704-a8be-c1b84203d48e
  modified: 2026-08-21T22:20:54.846Z
---

`git worktree add <path> -b <newbranch>` with no explicit start-point branches from HEAD of
whatever branch the checkout you run it in currently has checked out -- NOT necessarily `main`.
In the shared `~/.claude` checkout, another session's `git checkout <feature-branch>` can leave
that as the live branch indefinitely (git-prepush-doctrine-gate and friends don't force it back
to main), so a worktree created without specifying a base silently forks from that stranger
branch instead.

**Why:** hit directly in this session (2026-08-21) doing hooks/** work. The main checkout was on
`feat/model-canary-probe-step25` (another session's WIP, 2 commits ahead of main) at the time.
`cd ~/.claude && git worktree add .claude/worktrees/x -b fix/y` created `fix/y` on top of that
branch's tip, not main's. Uncommitted edits made directly in the shared checkout beforehand (via
Edit tool on absolute `C:\Users\Owner\.claude\...` paths) landed on that same wrong branch too,
since Edit/Write operate on the checkout's actual working tree regardless of which branch is
checked out -- there is no per-branch isolation without a worktree. Recovery required: diffing
out the accidental changes, reverting the shared checkout, deleting and recreating the worktree
with an explicit base (`git worktree add <path> -b <branch> main`), then reapplying.

**How to apply:**
1. Before ANY edit in the shared `~/.claude` checkout, run `git branch --show-current` -- if it
   is not `main`, STOP; do not edit there (another session's WIP is checked out).
2. Always pass an explicit base ref: `git worktree add <path> -b <branch> main` (or
   `origin/main`), never bare `git worktree add <path> -b <branch>`.
3. The `EnterWorktree` tool only operates relative to the session's primary working directory;
   when that is not itself the target git repo (e.g. this session's primary dir is the OneDrive
   folder, not `~/.claude`), it errors "not in a git repository" -- fall back to raw
   `git worktree add` with an explicit base, as above.

See also [[feedback_commit_message_via_write_tool_not_heredoc]] from the same session/incident.
