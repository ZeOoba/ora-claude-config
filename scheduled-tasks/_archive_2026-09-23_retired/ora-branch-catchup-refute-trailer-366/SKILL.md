---
name: ora-branch-catchup-refute-trailer-366
description: One-time 2026-09-24 10:15 ET: checks whether ZeOoba/oxford-command-center PR #366 (per-commit refute attestation) has merged. If yes, adds the merge-commit refute-trailer rule to Step 6 of branch-catchup SKILL.md via a PR to ora-claude-config (not merged). If no, makes no edit. Either way emails ggoldberg a status plus the PR #364 trailer reminder. Registered 2026-09-23.
---

One-time, unattended. Registered 2026-09-23 from a supervised Claude Code session. Never fabricate. If any step is blocked (permission prompt, hook refusal, preflight nonzero, conflict), STOP at that step, make no further writes, and report exactly where and why in the email (step 6).

Run date: compute ONCE at start with `date '+%A %Y-%m-%d'` and reuse that exact value everywhere. Use its date part in every date slot.

Progress markers: after each numbered step, run
`C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:\Users\Owner\.claude\maintenance\task-progress-marker.py write --fleet cc --task-id ora-branch-catchup-refute-trailer-366 --step N --of 6 --note "<short state>"`

## Step 1: is PR #366 merged?
`gh pr view 366 --repo ZeOoba/oxford-command-center --json state,mergedAt,mergeCommit`
- state != MERGED → skip steps 2–5 (make NO edit) and go to step 6 with outcome NOT-MERGED. This task does not re-schedule itself; the email tells Gabriel to re-register or apply the edit by hand.
- MERGED → record the merge commit sha, then run `git -C <any oxford-command-center checkout> fetch origin` and confirm `scripts/check-refute-required.ts` on origin/main still supports `--strict` and `--base=` (grep the file). If it doesn't, STOP (report the mismatch; don't write doctrine that names a flag that isn't there).

## Step 2: already done?
Canonical source = the `~/.claude` repo (remote ZeOoba/ora-claude-config), path `skills/branch-catchup/SKILL.md`. It is NOT in ZeOoba/ora-skills. Fetch origin, then check whether `origin/main:skills/branch-catchup/SKILL.md` already contains "Refute-Skip". Also check for an open PR in ZeOoba/ora-claude-config touching that file (`gh pr list --repo ZeOoba/ora-claude-config --search "branch-catchup" --state open`). If either is true, skip to step 6 with outcome ALREADY-DONE (cite what you found).

## Step 3: isolated worktree + single-writer gate
Never edit the shared `~/.claude` checkout (it is often dirty and may be on a detached HEAD). Follow `memory/rules.md` §14 (shared-checkout hygiene) and the `isolated-commit` skill:
- `git -C ~/.claude worktree add <scratch path outside ~/.claude> -b docs/branch-catchup-refute-trailer origin/main`, and record the origin/main sha as SESSION_SHA.
- Claim the work first: `python ~/.claude/hooks/lib/claim_work.py claim sched-repo-housekeeping "branch-catchup Step 6 refute-trailer edit" --paths skills/branch-catchup/SKILL.md`. It must be the `sched-` slug, never the bare one. Exit 3 (live claim) → STOP.
- Run `python ~/.claude/maintenance/preflight-shared-checkout.py --repo <worktree path> --paths skills/branch-catchup/SKILL.md --since <SESSION_SHA>`. 0 = go; any nonzero = STOP. Never pass --force.

## Step 4: the edit (use the Edit tool, not Bash/sed, because provenance is recorded only by Edit/Write)
In the worktree's `skills/branch-catchup/SKILL.md`, section `## Step 6 -- commit and push`, insert this bullet directly after the first bullet ("Commit the merge with the standard attribution trailer..."):

- **oxford-command-center: a merge that resolved a conflict in a financial path needs its own refute trailer** (per-commit attestation, PR #366). `scripts/check-refute-required.ts` reads two-parent merges with `git show --remerge-diff`. A clean catch-up merge needs no trailer, but a merge that resolved a conflict (including `--theirs`/`--ours`) in any financial-decision path is listed on its own. Financial paths: `server/**`; `scripts/**` by default (minus `NON_FINANCIAL_ROOT_PATHS`); `src/analytics/**`; the named contract/seed/config files. Such a merge commit message must carry `Refute-Skip: conflict resolution taken verbatim from main; no financial logic changed` (only when literally true) or `Refute-Reviewed: <run>`. Otherwise the required CI check `refute-required` fails. Verify before pushing: `npx tsx scripts/check-refute-required.ts --strict --base=origin/main` must exit 0.

Match the file's existing style (`--` dashes, bullet format, line endings). Grep the rest of the file for any other statement that a catch-up merge needs no trailer or attestation. If one exists, reconcile it in the same edit and quote every site in the report. Check the diff: `git diff --stat` shows one file, and the diff shows only the intended lines.

## Step 5: commit + PR (do NOT merge)
- `git add skills/branch-catchup/SKILL.md` (explicit path; never -A).
- Commit message `docs(skills): branch-catchup Step 6 — merge commits resolving financial-path conflicts need a refute trailer (oxford-command-center #366)`, ending with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Push the branch (non-force) and open a PR against main in ZeOoba/ora-claude-config with `gh pr create`. The body cites PR #366's merge sha and states that the live `~/.claude/skills/branch-catchup/SKILL.md` updates only after this PR merges and the shared checkout moves. End the body with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- Do NOT merge. It is a `~/.claude` doctrine change, so under the merge gate it needs a real review before merge. Leave that to Gabriel.
- Release the claim (`claim_work.py release sched-repo-housekeeping`). Remove the worktree (`git worktree remove`) after the push lands; verify the push with `git ls-remote`, not the exit code.

## Step 6: report (always runs)
Send ONE email via Outlook COM: `powershell -File C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 -To ggoldberg@oxfordra.net -Subject "<subject>" -Body "<body>"`. This is the SOLE send path. Send to ggoldberg@oxfordra.net ONLY, with no cc. On a non-zero exit, retry once, then flag loudly in the run summary. Do not halt.
Subject: `[branch-catchup #366] <OUTCOME> — <run date>`, where OUTCOME ∈ PR-OPENED / NOT-MERGED / ALREADY-DONE / BLOCKED.
The body states the outcome with evidence (PR #366 state/sha; the new ora-claude-config PR URL, or the blocked step and its error output). It ALWAYS includes this reminder:
"PR #364 (ZeOoba/oxford-command-center, 'fix(cc): 2026-09-23 review — correctness') conflicts with main on scripts/commitmsg-trailer-guard.mjs after #365. `scripts/**` is a financial path by default. Once #366 is on main, #364's catch-up merge commit that resolves that conflict needs its own `Refute-Skip:` (only if taken verbatim from main) or `Refute-Reviewed:` trailer, even for a --theirs resolution. Otherwise the required `refute-required` check fails. Verify with `npx tsx scripts/check-refute-required.ts --strict --base=origin/main` before pushing."
First run `gh pr view 364 --repo ZeOoba/oxford-command-center --json state,mergeable`. If #364 is already MERGED or CLOSED, replace the reminder with that fact.