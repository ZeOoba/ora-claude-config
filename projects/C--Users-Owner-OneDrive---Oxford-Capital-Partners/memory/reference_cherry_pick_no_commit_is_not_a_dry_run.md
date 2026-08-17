---
name: cherry-pick-no-commit-is-not-a-dry-run
description: "git cherry-pick --no-commit WRITES to the working tree and index -- it is not a dry-run, and --abort will not undo it. Use git merge-tree --write-tree for a genuinely read-only conflict check."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 6797e01b-7631-40f5-a01e-6fdabdbe6b60
  modified: 2026-08-16T20:29:08.248Z
---

**`git cherry-pick --no-commit` is a WRITE, not a preview.** It applies the patch to the working tree and stages it. It only skips the *commit* step. There is no `--dry-run` for cherry-pick.

**`git cherry-pick --abort` will not clean it up.** With `--no-commit` on a clean apply, git finishes the operation and leaves no sequencer state — so `--abort` exits with "no cherry-pick in progress" and changes nothing. The staged files just sit there.

Burned on 2026-08-16 checking whether the recursive-delete-guard commits would apply to the live `~/.claude` checkout: the "dry-run" dirtied 4 files in a tree that already held 25 files of other sessions' WIP (25 → 29). Recovery was only safe because those 4 paths had been verified clean beforehand, so `git restore --staged --worktree <exact paths>` provably destroyed nothing of anyone else's.

**Use instead — genuinely read-only:**

```bash
git merge-tree --write-tree --name-only HEAD origin/main
```

Exit 0 = clean, exit 1 = conflicts; first output line is the resulting tree oid, remaining lines are the conflicted paths. Writes nothing to the working tree or index. Requires git ≥ 2.38 (this machine is on 2.55). In the same incident it correctly reported the 4 real conflicts — `memory-integrity-probe.py`, its test, `MEMORY.md`, `event_log.md` — which is what made the "cherry-pick the 2 commits instead of merging" call defensible.

**For a full apply-and-test rehearsal**, use a throwaway worktree — additive, and disposable:

```bash
git worktree add <scratch path> -b <temp branch> origin/main
```

That path was used successfully twice the same day; the mistake was reaching for `--no-commit` on the live tree after already knowing the safer pattern.

**Generalisation worth keeping:** on a shared checkout, treat any git verb that lacks an explicit `--dry-run` as a write until proven otherwise. `git merge`, `git rebase`, `git stash`, `git apply` (has `--check`), `git am` (has no dry-run) all mutate. Related: [[polling-claim-loop-default]] on contested state, and the single-writer rules in [[tech]].
