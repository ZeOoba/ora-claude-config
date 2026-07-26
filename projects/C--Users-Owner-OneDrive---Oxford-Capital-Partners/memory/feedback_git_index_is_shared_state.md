---
name: git-index-is-shared-state
description: "In a shared checkout the git INDEX is shared too — another session's `git add` lands in your commit. Re-check `git diff --cached` in its own call immediately before committing."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d6635568-ae53-453c-9bd7-ec8551f96c73
  modified: 2026-07-26T18:28:24.198Z
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

**Observed again 2026-07-26** — a TOCTOU variant, not just a stale-check variant. Sequence:
staged exactly 2 files (a new reference memo + a spliced MEMORY.md hunk), ran
`git diff --cached` in its own call immediately before committing — clean, only those 2 —
then ran a bare `git commit -m "..."` a few tool-calls later. The landed commit (`7b44254`)
contained 3 files: `event_log.md` had picked up 22 lines from another live session between
the check and the commit. Ruled out, by directly reading source rather than guessing:
no git-native `pre-commit` hook exists (`.git/hooks/` has only `.sample` files + an unrelated
real `pre-push`); `commit-provenance-recorder.py` only fires on `Write|Edit|MultiEdit`
PostToolUse and never stages anything; `append-event-log.py` (the documented single-writer
append path) only writes + warns on backlog size, never runs `git add`/`git commit`. Reflog
showed another session landing its own commit (`f364bd6`) 2.5 minutes later — that session
was genuinely staging concurrently, and its `git add` on `event_log.md` landed in the window
between this session's own clean check and the bare commit executing.
`commit-provenance-guard.py` did not block it — most likely its own documented blind spot
("does NOT catch foreign files written by a script rather than the Edit tool") applied, or
the other session's `git add` simply postdated the guard's own candidate-check. Either way:
**"check immediately before" narrows the window, it does not close it.** No harm this time —
`event_log.md` is append-only and the swept content was legitimate — but the same race
against a co-mingled non-append-only file would not be as forgiving.

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
4. **For the final commit itself, prefer an explicit pathspec over a bare `git commit`** —
   `git commit -m "..." -- <your/file> <your/other-file>` commits only those paths'
   current content regardless of whatever else lands in the shared index in the interim,
   which is exactly the protection a bare commit lacks. The one case where pathspec is
   UNSAFE is a co-mingled same-file partial splice (you staged only some hunks of a file
   others also touched) — there, `git commit -- <path>` re-reads the working tree and
   discards your splice, resweeping the foreign hunks back in
   ([[feedback_pathspec_commit_discards_index_splice]]); use bare `git commit` with no
   pathspec ONLY for that specific case, immediately after the splice, with nothing else
   pending in the index. Genuinely separate, not-touched-by-you dirty files (the common
   case, including this 2026-07-26 incident) are exactly what pathspec protects against —
   don't default to bare commit out of over-general caution from that one caveat.
   **Untracked-file caveat (confirmed 2026-07-26):** `git commit -m "..." -- <path>`'s
   implicit-add only works for already-tracked files. For a brand-new untracked file it
   fails outright (`error: pathspec '<path>' did not match any file(s) known to git`) —
   run an explicit `git add <path>` first, then the same pathspec commit. Still safe: the
   `git add` only touches the one path you named.

Attribute positively; never infer ownership from mtime quiet
([[positive-attribution-over-mtime]]).
