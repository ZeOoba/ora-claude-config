---
name: feedback-commit-message-via-write-tool-not-heredoc
description: "Compose git commit messages with the Write tool + an in-repo scratch file, not /tmp + a Bash heredoc -- the heredoc pattern did not persist reliably across separate Bash tool calls in this environment."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ebb79ea0-b175-4704-a8be-c1b84203d48e
  modified: 2026-08-21T22:20:37.009Z
---

For a multi-line git commit message, write it to a file with the Write tool and commit via
`git commit -F <file>`, then delete the file. Do not use `/tmp/<file> <<'EOF' ... EOF` split
across separate Bash tool calls -- the heredoc content did not reliably persist between the
call that wrote it and the later call that read it back for `git commit -F`, in this harness's
Windows/Git-Bash environment (each Bash call is a fresh shell; state does not carry the way a
single interactive shell session would).

**Why:** observed directly in this session (2026-08-21) while committing a hooks fix -- the
heredoc-written temp file was empty/missing by the time `git commit -F` ran in a later call.
The scratchpad path this harness provides is also outside the repo, adding a second reason a
git operation shouldn't reach for it.

**How to apply:** write the commit message to a file INSIDE the target repo/worktree (e.g.
`.git-commit-msg.txt` at the repo root) via the Write tool, run `git commit -F
.git-commit-msg.txt` via Bash, then delete the file before it can be mistaken for a tracked
file. Works uniformly whether the target is the shared checkout or an isolated worktree. See
also [[reference_worktree_wrong_base_branch_2026-08-21]] for the adjacent worktree-basing
lesson from the same session.
