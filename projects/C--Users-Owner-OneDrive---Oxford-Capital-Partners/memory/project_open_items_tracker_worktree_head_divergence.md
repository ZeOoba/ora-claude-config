---
name: project-open-items-tracker-worktree-head-divergence
description: "open-items-tracker.md's on-disk working-tree copy was missing session 15ec64e8's committed OI-023 content as of 2026-07-20 — needs a from-scratch check next session touching ~/.claude, not acted on same-session to avoid clobbering possible live WIP."
metadata:
  type: project
  originSessionId: ea223c6a-64e1-43b5-ad96-ad4f150a6768
  modified: 2026-07-21T02:20:54.098Z
---

**Status:** OPEN — needs a fresh check next session in this checkout.

**Finding (2026-07-20):** while investigating a [[reference_commit_provenance_guard]] false-positive
block, found that `projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/open-items-tracker.md`'s
**working-tree file on disk did not match `HEAD`**. Session `15ec64e8` had committed `fd78609`
("docs(memory): open OI-023 for the IWNS LLC rent-roll gap") on top of this session's `c29935b`
(OI-022 SHA correction) — `HEAD` and the index both contain OI-023 — but `git diff` against the
working tree showed OI-023's ~25 lines as a "deletion," meaning the actual file content on disk at
that moment did not have it. `git diff --cached` was empty (index == HEAD), so this wasn't a staged
change either — the on-disk file itself appeared to be running behind what was already committed.

**Why:** unconfirmed. Candidates, none verified: (a) session `15ec64e8` was mid-edit on a fresh
revert/removal of OI-023 at that exact moment (it was "open right now (idle)" per the shared-checkout
hook, not confirmed actively writing that file); (b) a OneDrive on-demand-sync artifact briefly served
an older cached blob for the file; (c) something else. **Not investigated further in that session** —
deliberately left untouched rather than risk clobbering another session's possible in-progress work by
running `git checkout HEAD -- <path>` or any other resync.

**No data was lost regardless** — `fd78609` already holds OI-023 safely in git history either way;
the only open question is whether the *working tree* ever needs to be nudged back in sync, and why it
drifted in the first place.

**How to apply — do this next session that touches `~/.claude`:**
1. `cd ~/.claude && git status --short` and `git log -3 --oneline -- projects/.../memory/open-items-tracker.md`.
2. Compare the on-disk file's OI-023 section against `git show HEAD:projects/.../memory/open-items-tracker.md`.
   If they now match, this resolved itself (likely candidate (b) above) — close this item, no action needed.
3. If they still diverge AND no session shows as live/working on this file (check
   `hooks/sessions/<sid>/touched-files.txt` mtimes and `session_liveness`, same technique used in
   [[reference_commit_provenance_guard]]'s 2026-07-20 entry), it's safe to
   `git checkout HEAD -- projects/.../memory/open-items-tracker.md` to resync — this only discards a
   stray on-disk artifact, since HEAD already has everything committed.
4. If another session DOES show as live and working on this exact file, stop and let them resolve it
   — do not force a resync over live WIP.

**Auto-check:** none — this is a one-off diagnostic, not a recurring fleet item.
