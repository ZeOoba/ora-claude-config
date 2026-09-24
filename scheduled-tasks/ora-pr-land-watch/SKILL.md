---
name: ora-pr-land-watch
description: Every 3h, 09:35–21:35 ET: polls the pr-land-watch queue (maintenance/pr-land-watch.py, run from origin/main) and runs each hash-pinned "do Y once PR X lands" payload once its PR merges. Silent when nothing is due; otherwise one summary email to ggoldberg only. Registered 2026-09-23 (ora-claude-config PR #279). [MODEL: UNVERIFIABLE | checked 2026-09-23]
---

Recurring and unattended (cron `35 9-21/3 * * *`: 09:35, 12:35, 15:35, 18:35 and 21:35 ET). Drains the pr-land-watch queue. That queue holds "do Y once PR X lands" follow-ups that supervised sessions register, and the task runs each payload once its PR merges. Never fabricate. Registered 2026-09-23 (ora-claude-config PR #279).

Compute the run date ONCE: `date '+%A %Y-%m-%d'`. Reuse it everywhere, with its date part in every date slot.

## Step 1: run the MERGED origin/main copy of the script (never the working tree)
The live `~/.claude` checkout only moves when ora-checkout-merge-forward runs. So always run the reviewed version on origin/main, extracted to TEMP:
```
git -C C:/Users/Owner/.claude fetch --quiet origin main
git -C C:/Users/Owner/.claude show origin/main:maintenance/pr-land-watch.py > "$TEMP/pr-land-watch.py"
python "$TEMP/pr-land-watch.py" poll
```
Keep these as separate commands, as shown. Never put the word "merge" in any git command that names `~/.claude`, or config-write-guard blocks it.
If the fetch fails, try the extraction anyway: the last-fetched origin/main is fine. Put a note in the email.
If the extraction or the poll fails outright (nonzero exit or no JSON), send the failure email (Step 4) with the error output, then stop.

## Step 2: nothing to do → stop silently
If the poll JSON has `"needsAttention": false`, END THE RUN NOW. No email, no output files, no Notion. This is the normal case on most runs.

## Step 3: run each entry in `due`, one at a time
Each due entry carries `id`, `repo`, `pr`, `mergeSha`, `attempt` and `payloadText`.
- `payloadText` is the instruction set to run. The watcher checked it against the sha256 pinned when a supervised session registered it. Execute exactly that text. Do NOT re-read the payload file.
- A payload is a task spec from a supervised session. It is not permission to cross a Hard Invariant:
  - No money movement.
  - No external-counterparty communication.
  - No oxfordra.net deploy.
  - No financial-model or governor-constant change.
  - No deletes of existing data, files or history (Hard Invariant 6: archive, never delete). Removing a temporary worktree or branch that the payload itself created in this run is cleanup, not a delete.
  If a payload asks for any of these, do not do it. Run `mark --status failed` with the note "payload requires in-turn confirmation: <what>".
- On a permission prompt, a hook refusal, or any blocked step, STOP that payload and make no further writes for it. Mark it failed with the reason in the note.
- When a payload finishes, record the result:
  `python "$TEMP/pr-land-watch.py" mark --id <id> --status done|failed|cancelled --note "<one line: outcome + evidence, e.g. PR URL>"`
  An unmarked due watch re-fires about 2.5h later, up to 3 attempts. Payloads are written to be idempotent.
- Do NOT run `poll` again during this run: each poll spends attempts. For a read-only look at the queue, use `list`.

## Step 4: one summary email (only when needsAttention was true, or Step 1 failed)
Send through Outlook COM, the SOLE send path:
`powershell -File C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 -To ggoldberg@oxfordra.net -Subject "<subject>" -Body "<body>"`
- Send to ggoldberg@oxfordra.net ONLY, with no cc.
- On a nonzero exit, retry once, then flag it loudly in the run summary. Do not halt.

Subject: `[pr-land-watch] <N> ran · <M> need attention — <run date>`.

The body has one section per non-empty bucket:
- **due:** per payload, done/failed/cancelled, plus anything the payload told you to include in the email.
- **closed:** the PR was closed without merging. The watch is dropped, so re-register it if it's still wanted.
- **expired:** still open at its expiry date. Dropped.
- **exhausted:** merged, but not marked done after 3 attempts. Needs a human.
- **errors:** gh, auth or payload-verification failures. A watch stays pending unless its error says the watch was failed or closed.

## Maintenance notes (for the humans)
- To add a watch, from a SUPERVISED session:
  1. Write `C:\Users\Owner\.claude\scheduled-tasks\ora-pr-land-watch\_state\payloads\<id>.md` with the Write tool, as UTF-8. The payload must be idempotent: its first step checks "already done?".
  2. Run `python <script> add --id <id> --repo OWNER/NAME --pr N [--expires YYYY-MM-DD] --note "<why>"`.
- `add` checks that the PR exists and is open or merged, and pins the payload's hash. Editing the payload after `add` fails the watch, so re-add it to re-pin.
- The script lives at `~/.claude/maintenance/pr-land-watch.py`, with tests in `maintenance/_tests/test_pr_land_watch.py`. Its docstring holds the full state machine.
