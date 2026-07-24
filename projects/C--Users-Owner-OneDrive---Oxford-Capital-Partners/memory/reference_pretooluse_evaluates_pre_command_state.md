---
name: pretooluse-evaluates-pre-command-state
description: "PreToolUse hooks inspect repo/disk state BEFORE the command runs, so a compound command that mutates then acts on that state is judged on the stale view — in both directions."
metadata: 
  node_type: memory
  type: reference
  originSessionId: d6635568-ae53-453c-9bd7-ec8551f96c73
  modified: 2026-07-24T17:00:36.341Z
---

A PreToolUse hook receives the command string and runs **before** it. Any state the hook
reads — the git index, the working tree, a lock file — is the state *before* the command's
own earlier segments have executed. For a compound command (`A && B`), a hook judging `B`
sees the world as it was before `A`.

Both directions bite, and the second is the dangerous one:

| Compound command | Hook sees | Reality | Failure |
|---|---|---|---|
| `git restore --staged MEMORY.md && git commit` | staged | not in the commit | blocks wrongly — noisy but safe |
| `git add MEMORY.md && git commit` | not staged | **is** in the commit | **guard silently bypassed** |

Confirmed 2026-07-24 in `memory-orphan-link-guard.py`, which returned "not our business"
whenever MEMORY.md was unstaged at hook time — so the single most natural way to commit
(`git add … && git commit`) walked straight past it. Same class as the config-write-guard
compound-add blind spot fixed the same day. Fixed by simulating the command's segments in
order rather than trusting the pre-command index; see
[[project-orphan-guard-timing-2026-07-24]].

**When writing a guard:** never trust read-back state alone — derive what the command
*will* do from the command itself, and err toward blocking. **When hitting a guard:** if a
compound command is blocked or waved through unexpectedly, split it into separate tool
calls and re-check; the verdict can change.

## Corollary: read a hook's verdict from stdout, not the exit code

While verifying this, an ad-hoc probe read the guard's **process exit code** and reported
ALLOW for everything. This hook class always exits 0 and signals a block via a stdout JSON
`hookSpecificOutput.permissionDecision`. The probe was the broken instrument, and it
briefly looked like a fix had failed. Parse stdout the way `hooks/tests/*` do — and when a
new measurement contradicts a passing test, suspect the new instrument first.

Related: [[reference_pretooluse_vs_git_hook_exit_codes]],
[[feedback_autonomy_gate_matcher_cannot_be_safely_narrowed]],
[[feedback_verify_probe_findings_before_acting]].
