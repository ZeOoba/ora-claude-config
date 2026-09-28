---
name: isolated-commit
description: Use when landing your own reviewed, ready-to-commit change in a shared ORA git checkout (~/.claude, ora-skills, website-canonical, oxford-command-center) that other Claude Code sessions may be concurrently editing — claiming/staging/pushing a change you just finished writing, not triaging someone else's ambient dirty files.
license: ORA Internal
---

# Isolated Commit

## Overview

One command for landing a change you just finished writing in a shared ORA checkout — claim, pathspec-scoped stage+verify, an independent review pass, commit, push with gate-flake-vs-regression triage, then PR. Complements `dirty-tree-triage` (which triages OTHER sessions' ambient dirty files with no claim on their content) — this is for YOUR OWN finished work.

## When to Use

- You've written and tested a change in `~/.claude`, `ora-skills`, `website-canonical`, or `oxford-command-center` and need to land it.
- NOT for cleaning up a pile of pre-existing uncommitted files you didn't write — use `dirty-tree-triage` instead.
- NOT a substitute for the mandatory Fable/Opus independent review gate on `hooks/**`/financial/governor code (`eos-review-gate.py`) — this skill's own review step (4) is the SAME requirement generalized to repos/files that gate doesn't cover.

## Workflow

1. **Claim.** `python hooks/lib/claim_work.py claim <slug> "<what/why>" --paths <target files>` (repo-appropriate slug; `ora-skills` additionally needs `git log --oneline -1` + `git status` per its own single-writer rule). Absent/stale claim data reads as "cannot prove disjoint" — never skip this to save a round-trip.

2. **Isolate.** Blast-radius paths (`hooks/**`, `settings.json`, governor/financial constants, CLAUDE.md) go in a fresh `git worktree` off `main` — never edited live in the shared checkout. Lower-risk paths may be edited in place once step 1 confirms they're disjoint from any other session's dirty set (`git status --short -- <paths>` must come back empty before you start).

3. **Stage + verify.** `git add -- <exact paths>` — never `-A`/`.`/`-a`. Then `git diff --cached --name-only` and abort if anything you didn't intend appears.

4. **Independent review.** Dispatch a review agent with NO knowledge of your reasoning — diff and repo access only — to (a) re-derive every numeric/factual claim your commit message is about to make from the actual repo state, and (b) confirm the diff matches exactly the pathspec from step 3. For `hooks/**`/financial/governor code this IS `eos-review-gate.py`'s mandatory pass (pin the reviewer model, record the verdict, re-review if the diff changes after — a stale verdict does not carry over an edit). For everything else, spawn the same shape of review anyway; do not skip it just because no gate enforces it mechanically.

5. **Commit.** Bare `git commit -F <message-file> -- <paths>` (a message file, not `-m`/a heredoc, sidesteps quoting fragility — see rules.md §24). Every claim in the message must trace to a command you actually ran this session.

6. **Push, triage don't retry-blind.** On a pre-push gate timeout, this repo's own gates already retry once at doubled budget — that's not a flake for you to react to. On a genuine test *failure*: run that one failing test directly, outside the gate, against the unmodified base branch. Confirms pre-existing and unrelated → say so explicitly and get the user's authorization before minting any override token (never mint one un-prompted, never force-push). Confirms caused by your diff → fix it, don't override it.

7. **PR.** Open with a summary + test plan that cites the review verdict from step 4.

## Quick Reference

| Step | Never do | Do instead |
|---|---|---|
| Stage | `git add -A` / `git add .` / `git commit -a` | `git add -- <exact paths>`, verify with `git diff --cached --name-only` |
| Review | Skip it because "it's a small diff" | Independent agent re-derives claims + checks pathspec, every time |
| Gate failure | Retry blindly or override immediately | Run the failing test directly first; distinguish flake/pre-existing from real regression |
| Override token | Mint it yourself on a hunch | Only after the user's explicit in-turn authorization, one confirmed reason |
| Commit message | Inline `-m`/heredoc for anything nontrivial | A message file via `-F` |

## Common Mistakes

- Claiming a slug but not passing `--paths`, which reads as "cannot prove disjoint" and defeats the point of claiming.
- Treating a gate's own timeout-retry as evidence of a flake worth overriding — it already self-resolved; nothing to do.
- Recording an independent review verdict, then editing the files again before committing — the verdict is keyed to exact content; re-review, don't re-use.
