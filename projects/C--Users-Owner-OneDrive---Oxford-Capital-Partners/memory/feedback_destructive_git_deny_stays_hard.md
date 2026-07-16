---
name: feedback-destructive-git-deny-stays-hard
description: "git reset --hard / git push --force are a categorical permissions.deny in ~/.claude/settings.json, confirmed intentional and kept as-is — never suggest loosening it"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 006ecde9-8f07-4a02-8e6b-5927591bda0d
---

`~/.claude/settings.json`'s `permissions.deny` has `"Bash(git push --force*)"` and `"Bash(git reset --hard*)"` as unconditional deny rules — these override even `defaultMode: "bypassPermissions"` and any in-chat "run it"/"do it" confirmation. This is mechanical enforcement of CLAUDE.md's own Git Safety Protocol line, not a bug.

**Why:** Hit this live 2026-07-08 — the user asked me to run `git reset --hard origin/main` on a shared checkout three times (including once after confirming the checkout was clean and once more after an explicit "run it"), and it was denied every time. When asked whether to loosen this (downgrade to `ask`, or scope an exception for worktree paths), the user chose **leave it as-is**.

**How to apply:** When `git reset --hard` or `git push --force` gets denied, do not retry, do not suggest workarounds through other tools (Desktop Commander, etc.), and do not propose loosening the rule unprompted — tell the user to run it themselves. Only revisit this if the user brings it up again themselves.
