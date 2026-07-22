---
name: reference-event-log-partial-commit-splice
description: Git technique to commit only your own entries from a co-mingled append-only file (event_log.md) without touching the working-tree file or a full git add -p — hash-object + update-index
metadata: 
  node_type: memory
  type: reference
  originSessionId: ac546aef-18b3-45a2-9a97-675c1f7135f4
  modified: 2026-07-22T00:01:21.863Z
---

Companion technique to [[shared-checkout-cofile-patch-hazard]]: that note names the problem (a co-edited file's diff captures another writer's hunks too); this note is the concrete fix for the specific case of `event_log.md` — a single file, multiple sessions appending newest-first, no interactive `git add -p` available in a scripted/headless session.

**When this applies:** `event_log.md` (or any similarly-structured append-only, newest-first file) has more than one new top-level entry uncommitted, and only SOME of them are yours to commit — the rest belong to another session and should stay uncommitted (per the standing "whoever notices commits their own entries" convention; never assume ownership of an entry you didn't write).

**The technique — stage a constructed blob directly, never touch the working file:**

1. **Identify entry boundaries** in the diff: `git diff -- <file> | grep -n "^+## "` lists every new top-level heading and its line number. Confirm by author/content which are yours.
2. **Build the target content in Python** (not sed/Edit — the file is large and the splice needs to be exact): read the current working-tree file, remove the text block(s) NOT yours (from their `## ` header up to, but excluding, the next `## ` header), write the result to a scratch path. This equals "working tree minus the entries that aren't mine" — never construct it from HEAD forward, since that risks losing entries from *other* sessions that landed between your appends.
3. **Verify the splice is exact** before staging: `diff <(cat original) <(cat spliced) | grep -c "^[<>]"` should equal exactly the line count of the excluded block(s), nothing else. (A `diff` against `git show HEAD:<file>` will show spurious noise from CRLF/LF differences between git's internal LF storage and the CRLF working tree — that comparison is not the one that matters; the working-tree-vs-spliced comparison is.)
4. **Stage the blob directly, bypassing the working tree:**
   ```
   BLOB=$(git hash-object -w <spliced-file>)
   git update-index --cacheinfo 100644,$BLOB,<path-in-repo>
   ```
   This stages exactly the spliced content without running `git add` (which would re-read the working-tree file) and without modifying the working-tree file itself — the excluded entries stay visibly uncommitted in `git status`, exactly where the other session left them.
5. **Verify staged content before committing:** `git diff --cached -- <file> | grep "^+## "` should list only your entries.
6. Commit. The working tree is untouched; a later `git add` from the entry's actual author will pick up cleanly.

**Real instance, 2026-07-21:** `event_log.md` held 4 new entries — 3 written by the current session, 1 (`15-skill Save-skill batch confirmed installed`) written by a separate Cowork session mid-flight. Used this technique twice in the same session: once to commit the 3 own entries while leaving the 4th uncommitted, and again later (after independently verifying the 4th entry's claims — a hash-check against the actual runtime cache, not just trusting it) to commit that one too, once it was legitimately "mine to close." Neither commit touched the other session's untouched entries or the working-tree file directly.

**Why not `git add -p`:** it's interactive (requires a terminal prompt loop) and not scriptable/headless-safe in this environment. The hash-object + update-index approach is the non-interactive equivalent for a whole-block-level (not intra-line) partial stage.
