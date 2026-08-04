---
name: reference-event-log-partial-commit-splice
description: Git technique to commit only your own entries from a co-mingled append-only file (event_log.md) without touching the working-tree file or a full git add -p — hash-object + update-index
metadata: 
  node_type: memory
  type: reference
  originSessionId: ac546aef-18b3-45a2-9a97-675c1f7135f4
  modified: 2026-08-04T19:38:14.905Z
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
6. Commit with a **BARE `git commit -m "..."` — NO pathspec, NO `-- <file>`.** The working tree is untouched; a later `git add` from the entry's actual author will pick up cleanly.
   **CRITICAL (confirmed 2026-07-22):** `git commit -m "..." -- <file>` — the pathspec form commit-provenance-guard.py itself suggests as a remediation — does NOT commit what you staged via `update-index --cacheinfo`. It re-reads the **working tree** for that path at commit time and commits that instead, silently discarding the surgical splice and re-sweeping every foreign hunk back in. Real incident: a MEMORY.md single-line splice, staged correctly, was blown away this way and four unrelated hunks from another live session landed in the same commit under an unrelated message (commit 61facf4, caught and amended to 62e5a35). If anything else happens to be staged in the index for other paths when you run the bare commit, unstage it first (`git reset -- <other-path>`) so the commit captures only the splice.

**Real instance, 2026-07-21:** `event_log.md` held 4 new entries — 3 written by the current session, 1 (`15-skill Save-skill batch confirmed installed`) written by a separate Cowork session mid-flight. Used this technique twice in the same session: once to commit the 3 own entries while leaving the 4th uncommitted, and again later (after independently verifying the 4th entry's claims — a hash-check against the actual runtime cache, not just trusting it) to commit that one too, once it was legitimately "mine to close." Neither commit touched the other session's untouched entries or the working-tree file directly.

**Why not `git add -p`:** it's interactive (requires a terminal prompt loop) and not scriptable/headless-safe in this environment. The hash-object + update-index approach is the non-interactive equivalent for a whole-block-level (not intra-line) partial stage.

**Failure mode found 2026-08-04, and the fix to step 2: picking a "resume anchor" deeper in the file is not safe — verify against the parent commit instead.** Step 2 as written assumes the new content is a clean, contiguous run: `[mine] + [all foreign blocks] + [rest of file, unchanged]`. Under heavy same-day concurrent load this is false — an already-committed entry (part of real HEAD, landed between this session's own commits) can sit interleaved *among* several sessions' still-uncommitted appends, because every `append-event-log.py` call inserts at the same top position regardless of whether the entry above it is committed or not. Picking "the next heading that looks like old content" and excising everything between mine and it therefore risks silently dropping a legitimate, already-committed entry along with the genuinely-foreign ones — nothing is lost from disk (the working tree is never touched), but the *commit's snapshot* becomes wrong, which is just as bad since that's what gets pushed and read by everyone else.

**The robust fix: don't hand-pick a resume anchor in the messy working tree at all.** Read the direct parent commit's content via `git show <parent-sha>:<path>` — that is unambiguous ground truth for "what's already committed, in the right order." Extract your own new entry from the working tree (it's the only part that's genuinely new and yours), then build the spliced content as `parent_content` with your entry inserted at the top (right after the intro paragraph) — never by subtracting foreign spans from the working tree. This sidesteps the whole classification problem: every already-committed entry survives by construction, because it's never removed from anywhere.

**Verify a splice that used this method** by diffing the result against the parent directly (`diff <(git show <parent>:<path>) <spliced>`) — it should show *only* your entry's own lines as additions, zero removals. If it shows any `<` (removed) lines, something is still wrong. Also grep for duplicate headings in the result (`grep -c "^## <exact title>"` should be 1) — inserting on top of the parent instead of the working tree means you must confirm you haven't also left a second copy sitting in the excluded-from-commit working tree that a later commit could redundantly re-add.

**Real instance, 2026-08-04:** used the old (working-tree-anchor) method, excised a ~30KB span between "mine" and a chosen resume heading, and it turned out an already-committed entry ("Atomic OI-id allocator shipped...") plus two more sat inside that span. Caught only because the commit's own diff showed those headings as *removed* relative to the true parent — a signal worth checking for on every splice commit, not just this one. Fixed with a second corrective commit rebuilt via the parent-content method above; verified byte-exact against parent + own entry only.
