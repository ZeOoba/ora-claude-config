---
name: enterworktree-launch-dir-repo-detection
description: "EnterWorktree anchors to the launch directory's repo, not any repo on disk — fails for ~/.claude when the session launch dir isn't a git repo (or isn't nested inside one). Manual git worktree add fallback + the baseRef trap it surfaced."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 79c92b15-49f5-46e8-b85d-01b789e04218
  modified: 2026-08-05T22:15:42.413Z
---

**EnterWorktree requires the *launch directory* to be a git repo, or the target to be nested inside one it can walk down into — it will not discover a sibling repo elsewhere on disk.** Confirmed 2026-08-05: `EnterWorktree({name})` from a normal session (launch dir `C:\Users\Owner\OneDrive - Oxford Capital Partners`, not a git repo) failed with "Cannot create a worktree: not in a git repository and no WorktreeCreate hooks are configured," even though `~/.claude` is a healthy git repo — because it's a sibling, not nested under the launch dir. The tool's own `path`-mode doc confirms the same constraint: entering an *existing* worktree also requires it to belong to "the current repository or ... a repository nested inside it."

**Investigated whether WorktreeCreate/WorktreeRemove hooks would fix this — concluded no clean fix, working as intended.** Those are real, generic hook events (confirmed present in the Claude Code settings.json schema — same shape as any other hook: matcher + command, no special contract beyond that). But they're global to every session, and the ORA launch directory is *never* a git repo by design. Pointing them at `~/.claude` would silently redirect every future `EnterWorktree` call made from any non-git launch dir — regardless of what that session actually wanted isolated — into the `~/.claude` repo, and would swap the session's cwd out from under it. That's a scope mismatch dressed as a fix, not a real one. Left unconfigured; use the manual fallback below for the occasional deliberate `~/.claude` worktree (see [tech.md §3f — single-writer shared-checkout rule](tech.md) for when that's warranted).

**Manual fallback:**
```bash
git worktree add ~/.claude/worktrees/<name> -b <branch> <base>
```
No `.gitignore` entry needed — `~/.claude/.gitignore` is fail-closed (`/*` default-deny, explicit opt-ins only), so `worktrees/` is ignored by omission, not a specific rule.

**The trap this surfaced: `worktree.baseRef` was unset in settings.json → silently defaulted to `"fresh"`** (branches new worktrees from `origin/<default-branch>`, per the tool's own doc). `~/.claude`'s local `main` routinely runs ahead of `origin/main` in this environment (frequent local commits, infrequent pushes — same pattern as `ora-skills` and `oxford-command-center`, both also single-writer shared checkouts). A worktree branched "fresh" would silently drop that ahead-of-origin work — no error, just a worktree missing recent local commits. **RESOLVED 2026-08-05:** Gabriel approved setting `worktree.baseRef: "head"` globally in `settings.json` (branches from current local HEAD instead) — applies to `EnterWorktree` everywhere, not just `~/.claude`, and matches the actual push cadence across all the shared-checkout repos in this workspace. Manual `git worktree add` invocations must still pass an explicit base (`main`, not `origin/main`) regardless — the setting only governs the native tool.

See also: [shared-checkout single-writer rule](tech.md) · [worktree node_modules junction hazard](reference_worktree_node_modules_junction_hazard.md) · [worktree staleness ancestor-check insufficient](reference_worktree_staleness_ancestor_check_insufficient.md).
