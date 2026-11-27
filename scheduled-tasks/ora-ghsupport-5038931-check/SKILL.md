---
name: ora-ghsupport-5038931-check
description: One-time 2026-11-27: check GitHub Support ticket #5038931 (refs/pull purge for ZeOoba/ora-claude-config) and count PR refs still on pre-purge commits; email ggoldberg@ only.
---

CONNECTOR SCOPE: Claude in Chrome (read-only, support.github.com only) plus local shell and the Outlook COM send script. Do not call Notion, Microsoft 365, HubSpot, Netlify or any other connector.

Step 0 - double-fire guard (added 2026-11-25; see scheduled-tasks/_shared/README-DOUBLE-FIRE-GUARD.md). Before anything else, compute RUN_ID once with `date +%s`, then claim (one line, as written):
  python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py claim --task ora-ghsupport-5038931-check --block main --run-id <run_id> --ttl-min 30
  - Exit 0 -> proceed. Run date = the claim output's `etDate` (YYYY-MM-DD, ET), reused VERBATIM everywhere below as YYYY-MM-DD. Never do timezone math in the shell.
  - Exit 10 -> today's check already completed. End silently: no browsing, no email. This is a normal skip, not a miss.
  - Exit 11 -> another run holds the claim. Stand down the same way.
  - Any other exit code -> tooling failure: fail open. Run steps 1-3 without a claim, take the run date from PowerShell `Get-Date -Format yyyy-MM-dd` (never Git Bash `date`, which returns UTC), call neither complete nor fail, and quote the code in the email.
  Only a run that got exit 0 closes the claim (Step 4); a run that stood down calls neither complete nor fail.

Purpose: one-time follow-up on GitHub Support ticket #5038931 ("Remove sensitive data: purge PR refs and caches after history rewrite", account ZeOoba). On 2026-11-20 the public repo ZeOoba/ora-claude-config had its history rewritten with git-filter-repo; the ticket asks GitHub to purge the 470 old refs/pull/* references and cached views that still expose pre-rewrite commits. Baseline on 2026-11-23: ticket Open, no reply from GitHub (only the owner's two comments); 470 of 488 refs/pull/*/head on the remote still pointed at pre-purge commits (the other 18 are PRs opened after the rewrite). Re-checked 2026-11-24: ticket still Open, still no reply from GitHub; 470 of 494 (6 more post-rewrite PRs). On 2026-11-25 the history was rewritten a SECOND time (19 contact emails purged; 4,777 of 4,917 commits rewritten), so PR refs created between the two rewrites now also point at superseded commits. Step 2 counts both generations. Baseline on 2026-11-25 after the second rewrite: 499 of 500 (470 from the 11-20 rewrite, 29 from the 11-25 one).

Step 1 - ticket status (read only). Using Claude in Chrome: open a new tab at https://help.github.com/support/tickets and wait a few seconds (the list loads late and can first read "No support tickets"), then open ticket #5038931 from the list; its page is https://help.github.com/ticket/personal/0/5038931 (the /support/tickets/5038931 address does not exist). Read the page text. Record: status (Open/Closed/Archived), and whether any comment from GitHub Support exists after the owner's two comments; if so, summarise what it says or asks in two or three plain sentences (no quotes longer than one sentence). Never type, comment, close, or click anything that changes the ticket. If Chrome is unavailable, not signed in, or the page will not load, do not try to sign in or work around it: record ticket status as UNVERIFIED and the reason. Close the tab you opened.

Step 2 - PR ref count (read only). Run in Git Bash:
  B=C:/Users/Owner/_archive/ora-claude-config-prepurge-2026-11-20/mirror.git
  M=C:/Users/Owner/_archive/ora-claude-config-prepurge-2026-11-25/filter-repo/commit-map
  awk 'NR>1 && $1!=$2 {print $1}' $M > "$TEMP/changed25.txt"
  git ls-remote https://github.com/ZeOoba/ora-claude-config.git 'refs/pull/*/head' > "$TEMP/pr-refs.txt"
  total=$(wc -l < "$TEMP/pr-refs.txt"); o20=0; o25=0; for s in $(cut -f1 "$TEMP/pr-refs.txt"); do if git -C $B cat-file -e $s 2>/dev/null; then o20=$((o20+1)); elif grep -qxF $s "$TEMP/changed25.txt"; then o25=$((o25+1)); fi; done; echo "total=$total old20=$o20 old25=$o25 old=$((o20+o25))"
Count every line: do not add a head/limit to the loop. The 11-20 mirror holds every commit from before the first rewrite (old20). The 11-25 commit-map lists, as "old new" pairs, every commit the second rewrite changed; a pair with old == new was unchanged and is still current history, so only changed SHAs count (old25). "old" = old20 + old25, the PR refs still pointing at superseded history. PR refs for commits that were in neither rewrite's input (e.g. a branch deleted before 11-25 and squash-merged) are not detected, so "old" is a lower bound. Do not modify, fetch into, or delete anything in either backup folder. Print counts only, never file contents.

Step 3 - report by email, always (one email, ggoldberg@ only):
  powershell -NoProfile -ExecutionPolicy Bypass -File C:/Users/Owner/.claude/scheduled-tasks/_shared/send-via-outlook.ps1 -To ggoldberg@oxfordra.net -Subject "GitHub Support #5038931 check YYYY-MM-DD" -Body "<body>" -BodyFormat text -DedupTaskId ora-ghsupport-5038931-check -DedupPeriodKey YYYY-MM-DD
Body, plain text: ticket status and whether GitHub replied (with the short summary if so, or UNVERIFIED and why); "PR refs on superseded history: <old> of <total> (<old20> from the 11-20 rewrite, <old25> from the 11-25 rewrite; baseline 499 of 500 on 2026-11-25)"; then one line of what it means: if old is 0 or close to it, "Purge appears done: spot-check an old PR's Files changed tab"; if GitHub asked a question, "GitHub is waiting on a reply from you"; otherwise "No change yet; nothing for you to do."
This is contract mode (rules.md §2). Run the send command once only, whatever its exit code: the script handles transient COM failures itself, and an exit 6 means the message MAY have gone out. On any non-zero exit, flag it loudly in the run summary with the script's output line. Do not halt for it.

Step 4 - close the claim (only if Step 0 returned exit 0). When the run ends normally, after the Step 3 email (whatever its exit code):
  python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py complete --task ora-ghsupport-5038931-check --block main --run-id <run_id>
If the run aborts before reaching Step 3:
  python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py fail --task ora-ghsupport-5038931-check --block main --run-id <run_id> --error "<what broke>"

Never fabricate a status or a count: anything you could not read is reported as UNVERIFIED with the reason. If something needs Gabriel's decision, put it under a "QUESTIONS FOR GABRIEL" line at the end of the email. Do not reply to GitHub, do not post anything, and do not change any repo, ref, file or task.