---
name: ora-claude-config-push-when-settled
description: One-time (fires 2026-07-26 15:00 ET) -- pushes ~/.claude (ora-claude-config) local main to origin once the shared checkout has settled (no live cross-session claims, HEAD stable 10+ min). Never force-pushes; reports and self-disables either way. Registered 2026-07-26 at Gabriel's direction after a concurrent-session commit swept an isolated event_log.md hunk into someone else's commit while trying to push manually.
---

You are running the ONE-TIME scheduled task `ora-claude-config-push-when-settled` for Oxford Realty Advisors. Context: earlier today (2026-07-26) several Claude Code sessions were concurrently active in the shared, non-worktree checkout at `C:\Users\Owner\.claude` (git remote `ZeOoba/ora-claude-config`, private). Gabriel asked to push the local `main` branch to `origin/main` once the other sessions' work settles down, rather than right now while things are still churning. This task is that one-shot check. It fires once, then self-disables automatically (fireAt semantics) -- do not try to reschedule or repeat it.

## Step 1 -- Settle check (BOTH must pass; if either fails, treat as NOT settled)

(a) **Cross-session claim check.** Read `C:\Users\Owner\.claude\hooks\active-work\*.json` (glob the directory; if it doesn't exist or is empty, this check passes). CORRECTED 2026-07-26 (actual on-disk shape, verified against live claim files -- the original `{sessionId, startedAt, expiresAt}` description here did not match): each claim file is `{session_id, title, description, claimed_at, cwd}` -- there is no `expiresAt` field. Compute expiry yourself: a claim is live if `claimed_at` + the ~2-hour TTL (see `memory/tech.md` §3e for the mechanism) is still in the future. If ANY claim file is still live by that computation, that is a live claim on shared `~/.claude` subsystems -- NOT settled, regardless of what step (b) shows. Fail open: if this directory/files are unreadable or malformed, don't block on it -- log a note and fall through to step (b) alone.

(b) **HEAD stability check.** From `C:\Users\Owner\.claude`, run `git log -1 --format="%ci"` to get the last commit's timestamp. Compare to the current time. If the last commit landed less than 10 minutes ago, treat that as active/recent writer activity -- NOT settled (someone just committed; give it room to finish before you push on top of it).

If BOTH (a) shows no live claims AND (b) shows the last commit is 10+ minutes old: settled, proceed to Step 2.
If either fails: NOT settled. Do not push. Go straight to Step 4 (report) with a clear one-line reason (e.g., "live claim: <slug>, expires <time>" or "HEAD moved <N> min ago at <hash>"). This task cannot retry itself (one-time, self-disabling) -- if Gabriel still wants this pushed, that becomes a fresh ask.

## Step 2 -- Push (only if settled)

From `C:\Users\Owner\.claude`: run `git status -sb` first to confirm the branch is `main`, tracking `origin/main`, and shows an "ahead N" count (N should be at least 4 based on today's work, possibly more). Then run `git push origin main`.

**Never force-push. Never rebase. Never reset.** This is a plain fast-forward push only.
- If it succeeds: note the before/after commit range from the push output (e.g. `abc123..def456 main -> main`).
- If it's rejected (non-fast-forward -- meaning someone pushed to origin directly in the meantime, from a different machine/session with independent push access): do NOT retry with `--force` or `--force-with-lease`, and do NOT attempt a merge/rebase to reconcile. Just capture the exact git error and report it as a blocker needing a human decision.
- If it fails for any other reason (auth, network, etc.): capture the exact error, do not retry more than once.

## Step 3 -- Verify (only if push succeeded)

Run `git log -1 --format="%h %ci %s"` and `git status -sb` again to confirm `origin/main` now matches local `main` (ahead 0).

## Step 4 -- Report

Post a brief note to the Notion Operations Hub (page `32b6ecd8-9e59-81f2-b329-df3fd0e25062` -- if that ID has moved, search for "Operations Hub" and verify before trusting a hardcoded ID) covering whichever happened:
- **Settled + pushed:** state the commit range pushed and that origin/main is now current.
- **Not settled:** state which check failed (live claim, or how recently HEAD moved) and that no push was attempted. This is expected/routine, not an alarm -- word it that way.
- **Push failed/rejected:** state the exact git error. This DOES need a human look -- also email `ggoldberg@oxfordra.net` ONLY (no cc; never `egoldberg@`) via the sole send path `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`, subject "ORA config-push (one-time) -- push failed, needs a look". On a COM send failure (exit 2 or 4): retry once, then note in the Notion row if it still fails -- don't loop further.

A brief note is appropriate in ALL THREE cases (Gabriel's own instruction for this one-off task) -- this is the one exception to the usual "silent unless notable" scheduled-task convention; don't suppress the routine not-settled case here.

## Never fabricate

If any step's output is ambiguous, unparseable, or you're not confident what happened (e.g., git status doesn't show what you expect, the branch isn't `main`, the remote isn't `ZeOoba/ora-claude-config`), do NOT guess or force a push to make progress. Post a `QUESTIONS FOR GABRIEL` note in the Notion row stating exactly what was unclear, and stop there.

## Guard conditions

- If the repo at `C:\Users\Owner\.claude` is somehow not on branch `main`, or `origin` doesn't point to `ZeOoba/ora-claude-config`, stop and report via QUESTIONS FOR GABRIEL rather than pushing blind.
- Do not touch, stage, or commit anything yourself -- this task's ONLY job is to push what is already committed on local `main`. If `git status` shows uncommitted working-tree changes, that's informational context for the report, not something to act on.
