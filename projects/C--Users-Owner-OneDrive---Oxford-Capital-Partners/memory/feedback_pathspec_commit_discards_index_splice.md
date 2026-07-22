---
name: feedback-pathspec-commit-discards-index-splice
description: git commit -m "..." -- <path> re-reads the WORKING TREE for that path, silently discarding a surgical update-index --cacheinfo splice and re-sweeping foreign hunks back in
metadata:
  node_type: memory
  type: feedback
  originSessionId: 4b990758-3f81-487d-b49d-f24cc9aeb058
  modified: 2026-07-22T22:00:28.146Z
---

Never follow a pathspec-scoped `git commit -m "..." -- <file>` with a same-file surgical splice already staged via `hash-object` + `update-index --cacheinfo`. The pathspec form re-reads the **working tree** for that path at commit time regardless of what the index holds — it silently discards the splice and commits the raw working-tree file instead, re-sweeping in whatever a co-mingled writer left there.

**Why:** confirmed by a real incident 2026-07-22. [[reference_commit_provenance_guard]] correctly blocked a commit because another live session (`40a4b051`, SEO-audit work) had touched the same MEMORY.md within TTL. Once that session ended, I re-staged just my one-line fix via `hash-object` + `update-index --cacheinfo` — the exact [[reference-event-log-partial-commit-splice]] technique — and verified `git diff --cached` showed only my line. But I then ran `git commit -m "..." -- MEMORY.md`, which is the guard's own suggested remediation text ("commit only your own files with an explicit pathspec"). That pathspec form ignored the surgical index and committed the full working-tree file, landing four unrelated hunks from the other session's SEO-audit work under my commit message (`61facf4`). Caught by re-reading the diff after commit, not before — the guard has no post-commit check. Fixed by amending the message to accurately describe all five changes (`62e5a35`) rather than reverting, since the swept-in content was itself complete, correct, finished work — reverting would have destroyed it.

**How to apply:** after any `update-index --cacheinfo` splice, the closing commit must be a **bare `git commit -m "..."` with no pathspec at all** — unstage any other paths first (`git reset -- <other-path>`) if the index has anything else in it. A pathspec is only safe when the named file's working tree already equals exactly what you intend to commit (i.e., no splice involved). Both [[reference-event-log-partial-commit-splice]] step 6 and the guard's own block-time remediation text in `hooks/commit-provenance-guard.py` now carry this caveat inline, so future sessions following either shouldn't hit this blind.
