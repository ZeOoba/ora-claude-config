---
name: investigate-plan-gate-worktree
description: One-time reconnaissance of the stale plan-gate-and-site-markers worktree under ~/.claude to determine if it's abandoned WIP needing reconciliation
---

Read-only reconnaissance task. Do NOT commit, push, discard, reset, or edit anything in any repo or worktree touched below — this is investigation only, to inform a later human decision about reconciling a possibly-abandoned worktree.

## Context
A prior session found a git worktree at `C:\Users\Owner\.claude\.claude\worktrees\plan-gate-and-site-markers` (inside the `~/.claude` config repo, which mirrors to the private GitHub repo `ZeOoba/ora-claude-config`). It is on branch `plan-gate-and-site-markers`, tracking `origin/plan-gate-and-site-markers`. Its HEAD commit was `3a67b8e` ("fix(hooks): plan-gate override enforcement, native plan-path recognition, site-marker dedup"). On top of that committed history, the worktree has real UNCOMMITTED modifications to:
- `hooks/confidentiality-guard.py`
- `hooks/lib/site_markers.py`
- `hooks/ora-autonomy-gate.py`
- `hooks/tests/test-confidentiality-guard.py`
- `hooks/tests/test-ora-autonomy-gate.py`
- `maintenance/_state/doctrine-status.json`

Separately, the main `~/.claude` checkout (branch `main`) has HEAD commit `f9ee2ec` ("docs(plans): add plan doc for plan-gate enforcement + site-marker dedup (PR #15)"), suggesting a PR #15 exists on `ZeOoba/ora-claude-config` covering this same topic area.

## What to determine
1. **Is there a live sibling session working on this right now?** Call the CCD session-management tools (`list_sessions`, and if useful `search_session_transcripts` for terms like "plan-gate", "site-marker", "site_markers.py") to check for any other active or recent session whose title/content matches this topic. Note especially whether any session shows recent activity concurrent with this check.
2. **What's the state of PR #15 (and any other open PR) on `ZeOoba/ora-claude-config` for this branch?** Use `gh pr list --repo ZeOoba/ora-claude-config --state all --search "plan-gate-and-site-markers"` and `gh pr view 15 --repo ZeOoba/ora-claude-config` (or equivalent) to see if it's open, merged, or closed, and whether the merged/closed version already supersedes the worktree's uncommitted changes.
3. **Has `origin/plan-gate-and-site-markers` moved beyond `3a67b8e`?** `cd` into the worktree and run `git fetch origin` then compare `origin/plan-gate-and-site-markers` to local HEAD.
4. **What do the uncommitted changes actually contain?** Run `git diff` (or `git -c core.autocrlf=false diff --ignore-all-space` given this repo has a known CRLF hazard — see `reference_command_center_crlf_hazard.md`-style issue, though check first whether `.gitattributes` now covers this worktree) inside the worktree and summarize: does it look like finished, ready-to-commit work, or broken/experimental mid-edit state? Does it overlap with or duplicate what PR #15 already shipped?
5. Cross-check `maintenance/_state/doctrine-status.json`'s uncommitted diff specifically — this file is also modified on the main `~/.claude` checkout itself (per a prior session's `git status`), so confirm whether the worktree's version and main's version are the same drift or different.

## Output
Write a clear, concise finding: is this worktree (a) abandoned and safe to reconcile/discard, (b) superseded by an already-merged PR #15 (in which case the uncommitted diff is likely redundant and safe to drop), or (c) still-relevant unfinished work that should be finished and committed. Give your evidence for each of the four checks above. Do not take any reconciling action yourself (no commit/push/discard/worktree removal) — this is purely to inform Gabriel's next decision.

If your findings show a clear, actionable conclusion (e.g., confirmed-abandoned-safe-to-discard, or confirmed-still-needed), send a brief summary email via the sanctioned Outlook COM path (`_shared/send-via-outlook.ps1`) to `ggoldberg@oxfordra.net` only (no cc, per ORA routing canon). If the findings are inconclusive or need Gabriel's judgment call, a written report is sufficient — no need to force an email.