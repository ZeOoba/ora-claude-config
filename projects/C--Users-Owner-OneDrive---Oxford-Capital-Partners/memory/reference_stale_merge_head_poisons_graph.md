---
name: reference-stale-merge-head-poisons-graph
description: "A staged-but-uncommitted git merge in the shared ~/.claude checkout gets silently absorbed as a 2-parent merge commit by another session's ordinary commit, poisoning the merge-base for any later real merge of that branch"
metadata:
  node_type: memory
  type: reference
  originSessionId: 7a4a4780-8a9c-48c2-839a-f10e60f49524
  modified: 2026-07-24T18:28:58.489Z
---

**The mechanism:** `git merge --no-commit --no-ff <branch>` in the live
`~/.claude` checkout stages the merge and writes `MERGE_HEAD`, but does not
commit. If left staged (e.g. while a review round runs) and ANOTHER live
session runs an ordinary `git commit` in the same checkout — even one that
never touches the merge's files — plain `git commit` always reads `MERGE_HEAD`
if present and records it as a **second parent**, regardless of what's
actually in that session's index. The resulting commit's TREE reflects only
what that session staged; the merge's staged content is not necessarily
included (and was NOT, in the observed case — apparently cleared from the
index by whatever staging step their commit script used). Net effect: a
commit that looks like a merge in the graph (2 parents) but whose tree never
actually contains the merged branch's content.

**Why this breaks things:** any SUBSEQUENT `git merge <branch>` computes its
merge-base assuming the branch's earlier commit really did land — since it's
now a reachable ancestor of HEAD via the poisoned edge — so a 3-way merge can
silently skip re-applying files whose content the poisoned "ours" side never
actually received. Observed: files that were never really deleted showed as
`CONFLICT (modify/delete)`, and other files were silently skipped entirely
(no conflict, no change) because the merge-base's version already matched
"theirs", masking that HEAD's actual tree did not match "ours" either.

**Detection:** `git log --pretty="%H %P %s" -1 <suspect-commit>` — two parent
hashes on a commit whose message doesn't say "Merge" is the tell.
`git diff <parent1> <suspect-commit> --stat` showing none of the expected
merge files is the confirmation (the merge's content never landed despite the
graph edge).

**Recovery, in order:**
1. `git merge --abort` (often already a no-op — `MERGE_HEAD` may already be
   gone, consumed by the other session's commit).
2. Confirm no other live session has touched your target files recently
   (scan `hooks/sessions/*/touched-files.txt` mtimes).
3. Do NOT attempt another `git merge <branch>` — the merge-base is poisoned.
   Instead apply the branch's exact content directly:
   `git checkout <branch> -- <path1> <path2> ...`
4. Byte-diff the result against the branch (`git show :<path>` vs
   `git show <branch>:<path>`) to confirm zero drift before committing.
5. Commit as a normal single-parent commit, not a merge — the message should
   explain why (avoids a future session repeating this same graph confusion
   when they see a non-merge commit that clearly landed a whole feature).

**How to apply:** never leave a `git merge --no-commit` staged across a long
gap (e.g. while dispatching a review agent) in the SHARED `~/.claude`
checkout — either commit promptly or `git merge --abort` before stepping away.
If a gap is unavoidable (review takes minutes), redo the merge fresh
immediately before committing rather than trusting a staged merge survived
untouched. Companion incident from the same session:
[[project-eos-review-gate-shipped-2026-07-24]]. Distinct from the existing
commit-provenance-guard class of collision (foreign files swept into your
commit) — this is the opposite failure: YOUR staged work silently vanishes
from the graph while still polluting it structurally.
