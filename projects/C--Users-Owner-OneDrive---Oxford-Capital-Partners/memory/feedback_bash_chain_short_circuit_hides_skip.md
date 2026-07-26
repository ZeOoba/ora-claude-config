---
name: feedback-bash-chain-short-circuit-hides-skip
description: "A long && chained Bash command can print later, unrelated success/echo lines even though an earlier command in the same chain failed and silently skipped everything after it — always re-verify actual state after a multi-step destructive chain, never trust the printed narration alone."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e3f980f6-f186-4928-ba79-212963641f99
  modified: 2026-07-25T18:18:34.524Z
---

Caught during a worktree-cleanup pass (2026-07-24/25, `oxford-command-center`): a single Bash tool call chained `git worktree remove && echo "removed" && ... && git branch -D <branch> && ... && git fetch ... && git ls-remote ... && echo "not on origin"` end to end with `&&`. `git worktree remove` failed partway through (blocked by an untracked file), which by ordinary shell semantics should have short-circuited every command after it — including the `git branch -D` sitting in the middle of the chain. But the tool's captured output still showed the chain's FINAL echo line ("not on origin — nothing further to do") printing normally, reading as if the whole chain had completed successfully.

It had not. A direct, independent re-check (`git branch --list <name>`) showed the branch was still present — the `git branch -D` step never ran, despite later output in the same invocation appearing to confirm the job was done.

**Why this matters generally, not just for this one command:** the printed output of a multi-step chained shell command is not reliable evidence that every step in the middle actually ran. Whatever the exact mechanism (buffering, how the tool assembles a multi-line `&&` chain, or a parsing quirk), the *empirical* result was a false positive — trusting the echoed text would have reported a branch as deleted when it was not.

**Mitigation:** for any multi-step destructive operation (delete, force-remove, branch prune, multi-file commit), prefer separate tool calls per step with an explicit state check in between. If a long chain is unavoidable, re-verify the actual resource state independently afterward — never conclude success solely from an echoed confirmation string that shares an invocation with the risky step. Same discipline as [[feedback_verify_probe_findings_before_acting]] and [[feedback_verify_negative_glob_results]], applied specifically to chained-shell-command output.
