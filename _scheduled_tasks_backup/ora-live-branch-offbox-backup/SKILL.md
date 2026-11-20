---
name: ora-live-branch-offbox-backup
description: Daily off-box backup of the live ~/.claude branch: runs maintenance/push-live-backup.py, which pushes live/primary-checkout HEAD to origin backup/live-primary with an explicit --force-with-lease through the normal pre-push gates (shim allowlist + compressed-scan canary; never --no-verify). Emails ggoldberg@oxfordra.net ONLY on a non-success verdict; silent on PUSHED/UP_TO_DATE. Not claim-bearing. [MODEL: UNVERIFIABLE | checked 2026-11-09]
---

CONNECTOR SCOPE: none -- this task uses no connectors; it runs a local script and, on failure only, sends via the local Outlook COM script. Do not call Notion, Microsoft 365, HubSpot, Netlify, Context7, Claude Code Remote, or any other connector, even if they are available in this session. If the local shell or Outlook COM is unavailable, stop and report that in the run summary rather than reaching for a connector.

You are `ora-live-branch-offbox-backup`. Single deterministic step -- do not improvise beyond what's below.

## What this task exists for
`~/.claude` runs on `live/primary-checkout`, whose commits otherwise reach GitHub only when a session happens to push them. `C:\Users\Owner\.claude\maintenance\push-live-backup.py` pushes that branch's HEAD to `refs/heads/backup/live-primary` on origin with an explicit `--force-with-lease`, through the normal pre-push gates (doctrine gate, hook-tests gate, confidentiality scan incl. compressed blobs). Before pushing it refuses unless the pre-push shim is an allowlisted shape and a canary proves the scan blocks a credential inside a .gz. It never skips hooks. Every failure writes `maintenance\_state\live-backup-push-failed.json`; success writes `live-backup-push-ok.json`. The `ORA Fleet Dead-Man` (check 6, `push-live-backup.py --check`) alarms independently when the live branch stays off GitHub -- this task does not need to duplicate that alarm, only report its own run.

DOUBLE-FIRE ENTRY GUARD (added 2026-11-14; run FIRST, before step 0; see scheduled-tasks/_shared/README-DOUBLE-FIRE-GUARD.md):
python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py claim --task ora-live-branch-offbox-backup --block main --run-id <session run_id> --ttl-min 30
- Exit 0 (PROCEED): this run owns the claim and MUST end in `complete` or `fail` below.
- Exit 10 (SKIP_ALREADY_COMPLETE): today's run already completed. Skip the whole task (no writes, no email) and report a normal skip.
- Exit 11 (STAND_DOWN_IN_PROGRESS): another run holds the claim. Stand down and report it.
- Exit 12 or anything else: stop, run none of the steps, and report the exit and output.
Terminal call, after step 3 or step 4, whichever ran:
python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py complete --task ora-live-branch-offbox-backup --block main --run-id <run_id>
(append `--email-sent-at <ISO time>` when step 4 sent the email).
If the run cannot finish (any step fails and the task stops), release the claim instead:
python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py fail --task ora-live-branch-offbox-backup --block main --run-id <run_id> --error "<one line>"
Never pass --force from a scheduled fire.

## Steps
0. Compute the run date ONCE at start: `date '+%A %Y-%m-%d'`. Reuse that exact value everywhere below (date part only in the subject).
1. Run exactly (allow up to ~45 minutes; the pre-push gate alone runs ~11): `C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:/Users/Owner/.claude/maintenance/push-live-backup.py`
2. Read the LAST line of its output, `RESULT_JSON={...}`, and its `verdict`.
3. **verdict PUSHED or UP_TO_DATE (exit 0):** no email. Note the verdict and `sha` in your run summary.
4. **Any other verdict (non-zero exit), or the script failed to run at all:** send an email via `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (Outlook COM -- the SOLE send path) to `ggoldberg@oxfordra.net` ONLY (never egoldberg, never ze@). Subject: `ora-live-branch-offbox-backup -- <VERDICT> -- <YYYY-MM-DD>` (date part of the run date from step 0). Body: the RESULT_JSON line verbatim, plus ONE plain line by verdict:
   - PRECONDITION: the live checkout's gate or branch state does not allow a safe push (e.g. the live branch predates the compressed-blob scan or the zero-ref guard -- merge origin/main forward in a supervised session; or HEAD is not on live/primary-checkout; or the pre-push shim is not an allowlisted shape). Nothing was pushed.
   - BLOCKED_OR_FAILED: the pre-push gate blocked (confidential term or credential-shaped string in the history being pushed) or auth/network failed. Nothing was pushed. A gate block needs a supervised history cleanup -- never retried around.
   - LEASE_REJECTED: something else moved backup/live-primary; nothing was overwritten.
   - REJECTED / PUSHED_UNVERIFIED / ERROR: as reported in the JSON.
   COM exit codes per rules.md section 2: retry once on 2 or 4; on 5 or 6 (or any other code) do NOT retry -- flag it loudly in the run summary and never resend (6 = send state unknown). A send failure never halts the run summary.
5. Never fabricate a verdict, sha, path or error you did not see in the script's actual output. If the output is missing or unparseable, say so in the run summary under QUESTIONS FOR GABRIEL and email that fact.

## Guardrails
- NEVER run `git push` yourself, NEVER pass `--no-verify`, never set override tokens, never edit `push-live-backup.py`, the pre-push shim, `hooks/**` or `confidential-terms.json` from within this task.
- Never try to make a block go away (no history rewrite, no untracking, no rebasing) -- report it and stop; a fix belongs in a supervised session.
- Not claim-bearing: this task makes no working-tree or index writes. It writes only the two `maintenance\_state\live-backup-push-*.json` beacons and the remote ref `backup/live-primary`.
- No Notion writes and no event-log writes from this task (any event-log entry belongs to a supervised session, via `python ~/.claude/maintenance/append-event-log.py` only).