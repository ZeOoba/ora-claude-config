---
name: reference-isolated-commit-repair-wrapper-2026-08-13
description: isolated_commit.py gained a commit_isolated_replacement() stage->commit->repair wrapper; two independent-review rounds caught real bugs (pathspec-commit discards the staged hunk; hash-based safety checks are wrong in both directions) before it shipped
metadata: 
  node_type: memory
  type: reference
  originSessionId: b34ec269-3c65-4bc6-ba23-039298513853
  modified: 2026-08-13T04:32:07.625Z
---

`hooks/lib/isolated_commit.py` (the temp-index isolated-staging tool) gained `commit_isolated_replacement()` — stages an isolated hunk, commits it, and syncs the working tree to the new HEAD in one call/CLI flag (`--message`). Built in a worktree (`.claude/worktrees/isolated-commit-wrapper`, branch `feature/isolated-commit-repair-wrapper`), not yet merged to the live checkout as of 2026-08-13 (pending `eos-review-gate` final sign-off + landing).

**Why it exists.** `stage_isolated_replacement()` (the original function) never touches the working tree by design — correct for staging, but its documented finish step was "run `git commit` yourself," which leaves the working tree wherever it was. When used to REPAIR already-committed shared content (not just isolate a live local edit), that's a latent revert: HEAD says the fix, the working tree doesn't, and the next broad `git add -A && git commit` (anyone's) silently reverts the fix. Four sessions in one day independently rediscovered the same manual third step (`git checkout HEAD -- <path>`). This wraps all three.

**Two real bugs found and fixed during build, both worth remembering as general git gotchas, not just this file's history:**

1. **`git commit -- <pathspec>` re-derives from the WORKING TREE, not the staged index.** Live-reproduced: stage an isolated hunk via `git apply --cached` while the working tree still holds the old content (the repair case), then `git commit -m msg -- path` reports "nothing to commit, working tree clean" — it compared the unchanged working tree against HEAD and never looked at the index. A pathspec-scoped commit silently discards carefully isolated staging. Fix: a BARE `git commit` (no pathspec), relying on the existing precondition that nothing else is staged.

2. **Neither `git hash-object` mode expresses git's own equivalence relation.** To decide whether a repair-step checkout is safe (i.e., whether the working tree currently equals either the pre-fix or post-fix committed content, so nothing is lost), a hash comparison seems natural — but the plain filtered hash (`git hash-object path`) false-refuses a file committed under a *different* `core.autocrlf` setting than the current one even when the tree is exactly what that commit produced, and the raw hash (`git hash-object --no-filters path`) false-refuses the far more common case: an ordinary `git checkout`-smudged working tree (an LF blob checked out to CRLF under `autocrlf=true`), because raw-byte identity is strictly stronger than "git considers this equivalent." The correct primitive is `git diff --quiet <sha> -- path` against both candidate commits — it applies the same clean/smudge filters symmetrically in both directions, which is what "matches" actually means to git. **General lesson: when checking whether a working-tree file "equals" a committed version, use `git diff --quiet`, never a hash comparison — there is no hash mode that is correct for both a byte-identical check and a filter-normalized one, and picking either introduces a false-positive class in the other direction.**

Both bugs were caught by an independently dispatched reviewer (`pr-review-toolkit:code-reviewer`, model pinned to `claude-fable-5` per the hooks/** blast-radius review-gate requirement), not by the implementer's own re-reading — matching [[feedback_refute_pass_proactive_default]]. The second bug was found on a *second* review round, after the first fix (which itself fixed a real defect) was resubmitted — worth remembering that one review pass fixing a real bug doesn't mean the fix itself is correct; re-verify the fix, don't just verify the original code.

**Also added:** detection (not prevention — no atomic git-CLI way to prevent it) of the TOCTOU window between `stage_isolated_replacement`'s "nothing else is staged" precondition and the actual `git commit`: after commit, `git diff-tree --no-commit-id --name-only -r HEAD` is checked against `{rel_path}` and raises loudly (naming the commit sha) if another session's concurrent `git add` was swept in.

Final suite: 54/54 tests passing, including a fixture (`repo13`) that forces a genuine `git checkout` smudge (not just a coincidentally-matching one) to specifically pin the second bug.

**How to apply:** when this lands in the live checkout, prefer `commit_isolated_replacement()`/`--message` over the old manual stage-then-commit-then-remember-to-checkout sequence for any isolated fix to a shared single-writer file (`open-items-tracker.md`, `event_log.md`, scheduled-task registries, etc.) in a dirty multi-session checkout.
