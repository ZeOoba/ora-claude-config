---
name: reference_event_log_uncommitted_backlog
description: "event_log.md commit convention + THREE ways a shared-checkout commit goes wrong: the git-commit-pathspec gotcha (working-tree re-add, 2026-07-17), the non-empty-index gotcha (the prescribed bare `git commit` commits foreign STAGED files, 2026-08-12), and the CRLF/text=auto trap where `git apply --cached` rejects a byte-identical base because event_log.md's stored blob holds unnormalized CRLF despite text=auto (2026-08-17, fix: write the blob directly via `git hash-object -w --stdin` + `git update-index --cacheinfo`, no --path) — plus the temp-index variant and the staged-revert repair it leaves behind. Read before committing event_log.md, or any file, when other sessions have uncommitted or staged work in the same checkout."
metadata:
  node_type: memory
  type: reference
  originSessionId: 0888c827-119f-4877-98ae-23ac7c404a27
  modified: 2026-08-17T17:55:00.000Z
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

**Necessary but NOT sufficient (2026-08-12).** A bare `git commit` avoids the
working tree, but it commits *the whole index* — safe only when the index is
otherwise empty. On a shared checkout it frequently is not: on 2026-08-12 it
held 8 files staged by another session. Check `git diff --cached` for foreign
staged content before trusting this paragraph; if there is any, use the
temp-index variant below instead.

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
7. **`git diff --cached --stat` must come back EMPTY apart from your own
   staged hunk.** The bare commit in step 8 commits the entire index, so it is
   only safe on an otherwise-clean index. If another session has files staged,
   STOP here and use the non-empty-index variant below — do not proceed.
8. `git commit -m "..."` with **no pathspec** (see above — this is the part
   that actually matters).

This is the same isolated-hunk technique used earlier the same session for a
co-edited `open-items-tracker.md` (that one only needed step 3 as a plain
`git diff -- <file> | head` slice, since the co-edit there was a single
contiguous hunk at the top of the file — event_log.md needed the fuller
base+reconstruct approach because the other sessions' entries were NOT
contiguous with the target entry).

## When the index is NOT empty — the temp-index variant (added 2026-08-12)

**The gap (2026-08-12):** everything above silently assumes the index starts
clean. It did not. `git diff --cached --stat` showed **8 files already staged
by another session** — a 930-line `property_register_snapshot_diff.py`,
`governor-drift-probe.py` + its test, three unrelated task SKILL.mds, two
memory files. Step 8's bare `git commit` commits *the whole index*, so it
would have swept every one of them into an unrelated commit. The 2026-07-17
technique protects against the pathspec re-adding **working-tree** content; it
has nothing to say about foreign content already sitting in the **index**.
Both traps end the same way — a commit containing other sessions' work — so
check for both.

Do NOT fix this with `git reset` to clear the index: that destroys another
session's staging work. Use a scratch index instead, which never writes
`.git/index` at all:

```bash
export GIT_INDEX_FILE=/abs/path/to/scratchpad/tmpindex   # NOT in .git/
git read-tree HEAD                    # temp index = HEAD tree, nothing else
git apply --cached isolated.patch     # your event_log hunk only (steps 1-6)
git add path/to/other/file            # whole-file changes you DO want
git diff --cached --stat              # verify: exactly your files, nothing else
git commit -F -                       # commits the TEMP index; real one untouched
```

**The trap this leaves behind — you must repair it.** The real `.git/index`
still holds the committed paths at their *pre-commit* blobs. Once HEAD moves,
`git status` in the shared checkout reports those paths as **staged reverts**
(`event_log.md | 15 -`), and the next session to run a bare `git commit` will
silently undo your work. Repair immediately, path-limited so other sessions'
staged files are left alone:

```bash
git reset -q -- <only the paths you just committed>
```

Then verify twice: your paths gone from `git diff --cached`, and the other
session's staged files still listed. (Watch out when comparing before/after
counts — a concurrent session committing its own staged file will legitimately
drop it from that list. On 2026-08-12 the count went 8 → 7 for exactly that
reason, not because the reset over-reached. Confirm the delta matches the
other commit's stat before concluding you broke something.)

Also expect `config-write-guard.py` to BLOCK any git write against the live
`~/.claude` checkout — it needs an `allow-config-write` override token, which
requires Gabriel's explicit in-turn approval. Mint it with the approving quote
as the reason, and delete it as soon as the commit lands rather than leaving
the 60-minute multi-use window open.

## When `git apply --cached` rejects a byte-identical base (CRLF/text=auto trap, added 2026-08-17)

**The gap:** steps 3-5 assume a clean base (`git show HEAD:<path>`) plus a
correctly-retargeted patch will always apply. It did not, twice, even after
confirming the reconstructed base was **byte-identical** to the real HEAD
blob (`git cat-file -p <blob> == reconstructed base`, verified directly) —
`git apply --cached --check` still failed with `patch does not apply` at the
insertion point. Cause: `event_log.md` carries `text=auto` with
`core.autocrlf=true` (`git check-attr text eol -- event_log.md`), but its
**stored blob holds raw, unnormalized CRLF** — it predates whatever point
this repo started renormalizing on write, or was written by a path that
bypassed the clean filter. Any git plumbing that looks up this path's
attributes (`git hash-object --path <event_log.md path>`, and evidently
`git apply`'s own internal text handling for `text=auto` paths) will treat
the content as normalizable and diverge from what's actually stored,
even though a byte comparison of the reconstructed base against the real
blob shows zero difference. First symptom of the same root cause: building
the new blob via `git hash-object -w --path <path> --stdin` produced a blob
that diffed the **entire file** (CRLF→LF on every line) instead of a clean
insert — `git diff --cached --stat` showed thousands of insertions/deletions
for a 20-line append.

**Fix that worked — skip `git apply` entirely, write the blob directly:**

```bash
git show HEAD:<path>                       # base content, raw bytes, decode as utf-8
# construct new_content = base[:insert_point] + your_entry + base[insert_point:]
# in-memory string concatenation only — do not round-trip through a file with
# text-mode line-ending translation (see the CRLF note in the isolation script)
git hash-object -w --stdin                  # NO --path: skips attribute lookup,
                                             # stores raw bytes as-is, matching
                                             # how the existing blob is actually stored
git update-index --cacheinfo 100644,<new-blob-sha>,<path>
git diff --cached --stat                    # must show ONLY this file, insertions
                                             # only, no deletions -- if you see a
                                             # full-file rewrite, you used --path
                                             # (or --renormalize) somewhere; redo
                                             # without it
git diff --cached                           # visually confirm exactly your entry
git commit -m "..."                         # no pathspec, same rule as step 8 above
```

This produces the same end state as the `git apply --cached` route (index
holds base + your entry, working tree untouched) without ever needing the
patch to context-match, so the CRLF/attribute mismatch never has a chance to
bite. Prefer this over steps 3-5 for this specific file going forward; the
`git apply` route may still work fine on other shared files that don't carry
this blob/attribute inconsistency, but re-verify with `git diff --cached
--stat` (only your file, only insertions) before trusting either route
blind.

## What NOT to do

- Don't commit event_log.md wholesale via `git add <file>` / `git commit
  <file>` when `git status` shows it modified and you didn't author every
  line of the diff — verify content first (`git diff`), always.
- Don't run the bare `git commit` of step 8 without checking `git diff
  --cached` first. On a shared checkout the index is frequently NOT yours;
  "no pathspec" protects you from the working tree, not from foreign staged
  content. See the temp-index variant above.
- Don't clear a dirty index with `git reset` (no pathspec) to make the bare
  commit safe — that throws away another session's staging work. Path-limited
  `git reset -- <your paths>` is fine; a blanket one is not.
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

Related: [[reference_commit_provenance_guard]] · [[event_log]] ·
[[feedback_pathspec_commit_discards_index_splice]] (the `--only` form is the
same trap, not a safer one) · [[reference_event_log_partial_commit_splice]]
