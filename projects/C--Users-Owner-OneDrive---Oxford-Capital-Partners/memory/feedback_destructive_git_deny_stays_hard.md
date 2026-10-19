---
name: feedback-destructive-git-deny-stays-hard
description: "git reset --hard / git push --force are a categorical permissions.deny in ~/.claude/settings.json, confirmed intentional and kept as-is — never suggest loosening it. 2026-10-15: narrowing it for --force-with-lease was tried at the user's request and BLOCKED twice by adversarial review (glob cannot express safe variants); reverted"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 006ecde9-8f07-4a02-8e6b-5927591bda0d
---

`~/.claude/settings.json`'s `permissions.deny` has `"Bash(git push --force*)"` and `"Bash(git reset --hard*)"` as unconditional deny rules — these override even `defaultMode: "bypassPermissions"` and any in-chat "run it"/"do it" confirmation. This is mechanical enforcement of CLAUDE.md's own Git Safety Protocol line, not a bug.

**Why:** Hit this live 2026-07-08 — the user asked me to run `git reset --hard origin/main` on a shared checkout three times (including once after confirming the checkout was clean and once more after an explicit "run it"), and it was denied every time. When asked whether to loosen this (downgrade to `ask`, or scope an exception for worktree paths), the user chose **leave it as-is**.

**How to apply:** When `git reset --hard` or `git push --force` gets denied, do not retry, do not suggest workarounds through other tools (Desktop Commander, etc.), and do not propose loosening the rule unprompted — tell the user to run it themselves. Only revisit this if the user brings it up again themselves.

## 2026-10-14/15: the user DID ask to narrow it for `--force-with-lease`, and it failed twice

Trigger: a lease-protected push (`--force-with-lease=<ref>:<sha>`) was denied because `Bash(git push --force*)` is a prefix glob that also matches `--force-with-lease`. A project-level allow rule cannot help (deny outranks allow at every scope). The user chose to narrow the GLOBAL deny. Two independent Opus 5.5 adversarial passes both returned BLOCK, so the narrowing was reverted to the original line (verified, other sessions' hunks untouched).

**Why a glob deny cannot express "lease push only":** a prefix glob is a text match, and `--force*` was catching variants no replacement set covers. Each fix opened the next hole (same structural limit as [[feedback_autonomy_gate_matcher_cannot_be_safely_narrowed]]). Bypasses the reviewers CONFIRMED by actually running git against a throwaway local bare repo:
- `git push --force-with-lease --force origin main` (a later plain `--force` overrides the lease; also `... -f`)
- `git push --force'' origin main` and `--force<TAB>origin` (quote- or tab-suffixed flag; only a regex model, real matcher source unread)
- `git push --force-with-lease=a:b origin c:d +local:other` (a `+refspec` forces a DIFFERENT ref than the one the lease guards; no layer catches it anywhere)
- `git push --mirror origin` (force-resets and deletes remote refs; caught nowhere; pre-existing)

**Second layer is repo-local:** `oxford-command-center/.claude/hooks/bash-guard.mjs` (~lines 585-610) checks `--force`/`-f` tokens in any position and deliberately allows `--force-with-lease`, but it is registered only in that repo. website-canonical (a push to main deploys), ora-skills and the brain repo have the glob deny as their ONLY layer.

**How to apply:** if a lease push is needed, the user runs it themselves; do not narrow the glob. The only sound replacement is a wrapper script that parses argv and rejects `--force`, `-f`, `+` refspecs and `--mirror`, with ONLY that script allowed. That is new security-gate code needing the multi-round adversarial gauntlet; judged not worth it for a one-off need (2026-10-15). Revisit only if lease pushes become routine.
