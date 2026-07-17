---
name: reference_event_log_uncommitted_backlog
description: "event_log.md commit convention + the git-commit-pathspec gotcha discovered while landing a same-day close-out entry cleanly amid other sessions' uncommitted work. Read before committing event_log.md when other sessions have unrelated entries mixed into the same uncommitted diff."
metadata:
  node_type: memory
  type: reference
  originSessionId: 0888c827-119f-4877-98ae-23ac7c404a27
---

# event_log.md: who commits it, and how to do it safely when it's tangled

**The problem (2026-07-17):** `append-event-log.py` is collision-safe at the
*file* level (atomic insert, in-place fallback, spooling — see its own
docstring) but has no opinion at the *git* level. Multiple concurrent
sessions each append their own entries over a day without committing, and by
evening the file's uncommitted diff is one large blob spanning several
sessions' unrelated work — exactly what made a same-day close-out entry hard
to land without sweeping other sessions' substantive work into a foreign
commit.

**Standing convention (append this, don't re-litigate it):** no single
"structural writer" is assigned for event_log.md the way `ora-skills`
single-writer or the scheduled-task registry are — appends are meant to be
cheap and lock-free for everyone. Instead: **whoever notices the backlog is
the one who commits it**, isolating only their own entry (or entries) rather
than committing blind. `append-event-log.py` now prints a best-effort WARN
(`warn_if_uncommitted_backlog()`) once 4+ entries have piled up uncommitted,
as a nudge — it never blocks the append itself.

## How to commit YOUR entry when others are mixed in — the technique that works

**`git commit -- <pathspec>` does NOT commit what's staged.** This is the
mistake that actually happened tonight: `git apply --cached` staged exactly
one isolated entry, verified clean via `git diff --cached`, and then `git
commit -m "..." -- event_log.md` was run — which silently **re-added the
full working-tree version of that path before committing**, sweeping in
every other session's uncommitted entry that happened to be sitting in the
working tree. The fix: **stage exactly what you want via `git apply
--cached`, then commit with `git commit -m "..."` and NO pathspec at all.**
A bare `git commit` (no `--`, no path arguments) commits precisely the
index/staged content — it never reaches into the working tree the way a
pathspec does. This was caught before pushing (local-only, `git reset --soft
HEAD~1` undid it cleanly) — see [[event_log]] 2026-07-17 for the incident
itself.

**Isolating your own entry when the diff has multiple hunks from different
sessions** (event_log.md is newest-first-insert, so several sessions'
uncommitted appends often land as *separate* hunks, not one contiguous
block — do not assume `git diff`'s first hunk is "just yours"; inspect it):

1. `git show HEAD:<path>` → save as the known-clean base.
2. Construct `base + your_exact_entry_text` in a scratch file (insert at the
   same position `append-event-log.py` used — right after the header/intro,
   since it's newest-first).
3. `git diff --no-index -- base.md base_plus_mine.md` → a clean single-hunk
   patch containing ONLY your content.
4. Retarget the patch's `a/`/`b/` paths to the real file path (`sed`).
5. `git apply --cached --check` then `git apply --cached` the retargeted
   patch — stages only your entry, leaves the working tree (and everyone
   else's uncommitted content in it) completely untouched.
6. `git diff --cached` — visually confirm it's exactly your entry, nothing
   else, before committing.
7. `git commit -m "..."` with **no pathspec** (see above — this is the part
   that actually matters).

This is the same isolated-hunk technique used earlier the same session for a
co-edited `open-items-tracker.md` (that one only needed step 3 as a plain
`git diff -- <file> | head` slice, since the co-edit there was a single
contiguous hunk at the top of the file — event_log.md needed the fuller
base+reconstruct approach because the other sessions' entries were NOT
contiguous with the target entry).

## What NOT to do

- Don't commit event_log.md wholesale via `git add <file>` / `git commit
  <file>` when `git status` shows it modified and you didn't author every
  line of the diff — verify content first (`git diff`), always.
- Don't assume `commit-provenance-guard.py` will catch this for you. It
  checks touched-file provenance and (as of the 2026-07-17 recency-heuristic
  fix, see [[reference_commit_provenance_guard]]) whether a flagged edit is
  already safely committed — it does not know or care whether a bare `git
  commit` with a pathspec is about to silently re-add working-tree content
  outside what you staged. That failure mode is orthogonal to what the guard
  protects against.
- Don't wait for "the one true committer" — there isn't one for this file.
  If you notice the backlog (or the WARN fires), you're the one who commits
  it, isolating only what you actually intend to land.

Related: [[reference_commit_provenance_guard]] · [[event_log]]
