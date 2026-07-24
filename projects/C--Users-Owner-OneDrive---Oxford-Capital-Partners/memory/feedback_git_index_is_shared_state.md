---
name: git-index-is-shared-state
description: "In a shared checkout the git INDEX is shared too — another session's `git add` lands in your commit. Re-check `git diff --cached` in its own call immediately before committing."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d6635568-ae53-453c-9bd7-ec8551f96c73
  modified: 2026-07-24T17:00:50.799Z
---

`~/.claude` is one working copy driven by many concurrent sessions, so **the index is
shared state, not yours.** Another session running `git add` stages into the same index
you are about to commit from. `git commit` with no pathspec commits *the index* — theirs
included.

Observed 2026-07-24: two files another session had staged (`feedback_positive_attribution
_over_mtime.md`, `reference_provenance_claim_mechanism_already_exists.md`) appeared in my
staged set although I had only ever `git add`-ed my own paths. A later check picked up a
third (`event_log.md`) that arrived between two of my own commands.

**Why:** `commit-provenance-guard.py` exists for this, but it suppresses on recency/TTL
heuristics and did not fire here. Do not treat it as the only line of defence.

**How to apply:**
1. Run `git diff --cached --name-only` **in its own tool call**, immediately before the
   commit, and read it. Not as part of a compound command — a PreToolUse guard, and your
   own reasoning, both evaluate the pre-command state
   ([[pretooluse-evaluates-pre-command-state]]).
2. `git restore --staged` anything you cannot positively attribute to yourself. That
   leaves the other session's working tree untouched; they only need to re-add.
3. Prefer committing bodies you own and leaving a contested shared file (MEMORY.md,
   event_log.md) for its owner — or splice only your hunks
   ([[reference_event_log_partial_commit_splice.md]]).
4. Never `git commit -- <path>` to work around it: a pathspec commit re-reads the working
   tree and discards an index splice
   ([[feedback_pathspec_commit_discards_index_splice]]).

Attribute positively; never infer ownership from mtime quiet
([[positive-attribution-over-mtime]]).
