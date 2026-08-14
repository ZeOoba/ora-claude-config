---
name: ora-skill-cache-drift-alert
description: Every 30 min (CC/MCP fleet) — runs ora-skills' tools/repo_first_check.py --all (the REPO-FIRST cache-ahead-of-repo sweep already built 2026-08-03/04, PR store-ahead-of-repo-ledger) and, on any finding, immediately posts to Notion + files an OI-NNN item — closing the gap between a Cowork save_skill/create-skill platform-side edit and someone noticing. ora-doctrine-integrity-guard already runs this same sweep DAILY (55 12 * * *) with email+Notion alarming; that is too slow for same-day drift (3 occurrences in one day, 2026-08-04, each caught only by a session manually diffing the two stores — see OI-075). This task does NOT re-run the other 3 doctrine-guard engines (doctrine/governor probes, telemetry rollup) — narrowly scoped to just this one sweep so a 30-min cadence stays cheap. A clean run is silent (no Notion post, no OI item, no email) — same posture as every other guard in this fleet. v1.0 (2026-08-04, OI-075). v1.1 (2026-08-05, Gabriel-directed, ORA-wide once/day cadence policy): collapsed 30-min cadence -> 1x/day (11:00 ET). NOTE: this now runs the identical sweep as ora-doctrine-integrity-guard (12:55 ET daily) roughly 2h apart — the original rationale for this task (same-day drift detection faster than the daily guard) no longer holds at this cadence. Flagged as a retirement candidate, not retired. [MODEL: claude-opus-5 observed | checked 2026-08-09 via live-run transcript canary]
---

# ⛔ RETIRED 2026-08-09 (Gabriel-directed, in-turn) — DO NOT RUN, DO NOT RE-REGISTER

**STEP 0 — HARD STOP.** This task is RETIRED. If you are ever dispatched here, print
`ora-skill-cache-drift-alert: RETIRED 2026-08-09 — no action taken` and exit immediately.
Run nothing below this banner. Post nothing. Send nothing. File no OI item.

**Why retired:** it ran the identical `repo_first_check.py --all` sweep as
`ora-doctrine-integrity-guard` (v1.1, engine 4, `55 12 * * *`), roughly 2h apart, after the
2026-08-05 ORA-wide once/day cadence policy collapsed this task from every-30-min to `0 11 * * *`.
That collapse destroyed its entire reason to exist — same-day drift detection *faster* than the
daily guard — which v1.1 itself recorded ("Flagged as a retirement candidate, not retired").
Duplicate coverage confirmed 2026-08-09: a live sweep here returned 50 skills, 0 findings.

**Registry state:** `enabled: false`. The registry entry is deliberately RETAINED with this
SKILL.md in place, because `ora-task-integrity-guard`'s `guard.ps1` enumerates every registry
entry with an id + filePath and does **not** filter on `enabled` (`guard.ps1:153-163`) — archiving
this folder while the entry lives would make that guard resurrect the file and report a restore
every single day. This is the same sanctioned end-state used for the LAMS twin
`scheduled-task-integrity-guard` (retired 2026-06-11): registry `enabled:false`, SKILL.md kept
in place and marked retired. To complete removal, delete the registry entry from a regular
(non-scheduled) session — the scheduler refuses to delete the task that launched a session —
and only then move this folder to `_archive_YYYY-MM-DD_retired\`.

**Coverage NOT lost:** `repo_first_check.py` retains two live invokers — the `ora-skills`
pre-commit hook (`--check-staged`) and `ora-doctrine-integrity-guard`'s daily engine 4.
**Coverage delta accepted:** this task additionally filed a durable OI-NNN item on findings;
the daily guard alarms via email + Notion only.

---

You are the ORA skill-cache drift alert, on the Claude Code (CC/MCP) fleet — this surface has native Bash/shell access, use it. You start fresh with no memory of prior runs; everything you need is below.

WHY THIS TASK EXISTS: Cowork's `save_skill`/`create-skill` writes straight to the AppData runtime skill cache from outside git entirely — no repo commit required, no hook can intercept it (it's a different app from Code). `tools/repo_first_check.py` (merged to `ora-skills` main 2026-08-03/04) already detects this precisely — per-file, git-ancestry-based direction, CACHE-AHEAD/DIVERGENT/REPO-MISSING verdicts — and rescues about-to-be-clobbered cache content. It's wired into two places today: the ora-skills pre-commit hook (`--check-staged`, only fires when someone happens to be committing that exact skill) and `ora-doctrine-integrity-guard`'s daily sweep (`--all`, 55 12 * * *, alarms via email+Notion). Neither catches drift on a skill nobody is committing to AND is edited platform-side same-day — which is exactly what happened twice on 2026-08-04 (event_log.md's two "REVERSE-DIRECTION reconcile" entries, commits `a2b34ad` and `3825ac5`), both discovered only by a session manually diffing the two stores hours after the drift occurred. This task closes that window to ≤30 min, and — unlike the daily guard — also files a durable OI-NNN item so the finding survives past a scrolled terminal or an unread Notion page.

STEP 1 — RUN THE SWEEP:
  "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" "C:/Users/Owner/ora-skills/tools/repo_first_check.py" --all
Always exits 0 by design — its exit code carries no information; read its OUTPUT. A finding is any line beginning `!! REPO-FIRST` on stderr, naming the skill and verdict (CACHE-AHEAD, DIVERGENT, or REPO-MISSING — see the script's own docstring for what each means). `IN-SYNC` / `REPO-AHEAD` / `NOT-INSTALLED` are never findings — REPO-AHEAD just means a committed change awaits reimport (package-and-stage-skill's job, not this task's). If the script does not exist, note "repo-first sweep: SKIPPED (script absent)" in the run log and stop — never treat its absence as a finding.

STEP 2 — NO FINDINGS: send nothing (no Notion, no email, no OI item) — a clean run is silent, matching every other guard in this fleet. Print one run-log line: `DRIFT-ALERT OK — repo-first clean (N skills swept)`.

STEP 3 — FINDINGS PRESENT — DEDUP AGAINST ALREADY-FILED ITEMS FIRST. For each drifted skill, read (read-only) `C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\open-items-tracker.md` and check whether an OPEN item already references this skill name together with "REPO-FIRST" or "CACHE-AHEAD" or "skill-cache drift." If yes, that skill is already tracked — do not re-file or re-alert for it this run (avoids re-filing every 30 min for the same unresolved drift). Only the genuinely NEW findings (not already tracked) proceed to STEP 4/5. If every finding is already tracked, log `DRIFT-ALERT OK — N finding(s), all already tracked (<OI-ids>)` and stop (still silent — no new Notion post, no new email, no duplicate OI item).

STEP 4 — FILE AN OI ITEM for each new finding (do this BEFORE the Notion/email alert in STEP 5, so the alert can cite the real id):
  1. Allocate an id: `ID=$(python C:/Users/Owner/.claude/maintenance/allocate-oi-id.py --session $CLAUDE_CODE_SESSION_ID --note "repo-first sweep: <skill> <verdict>")`. Never hand-compute — this is exactly the collision class (OI-027/061/066) that script exists to prevent.
  2. RE-VERIFY current state of open-items-tracker.md before writing — this is a live, heavily concurrent checkout; do not trust anything read earlier in this run. `git status`/`git log -1` it first.
  3. Append a new entry (status OPEN) under the skill's finding: skill name, verdict, the specific file(s) reported by the sweep, the rescue path (`_staging/repo-first-rescue/<skill>/` if the script reported one), and required action — "commit the drifted content to ora-skills first (repo-first rule); see tools/repo_first_check.py's own remedy text for the specific verdict."
  4. Commit ONLY your own hunk to this file (isolate — this file is routinely dirty with other sessions' unrelated uncommitted work; never `git add -A` or `git commit -a` here). Push per this repo's normal discipline (background — the pre-push gate can take several minutes).

STEP 5 — ALERT on the new findings only (both (a) and (b); a failure of one does not skip the other):
  (a) POST to the Notion Operations Hub, parent page `32b6ecd8-9e59-81f2-b329-df3fd0e25062`. Title `Skill Cache Drift Alert — [today's YYYY-MM-DD HH:mm]`. Body: each new finding's skill/verdict/file(s)/rescue path and the OI-NNN id just filed. Verify via a direct `notion-fetch` on the returned page id (never `notion-search` — index lag). Retry once on failure; if still failed, fall back to (c).
  (b) SEND a best-effort email via the sole send path — Outlook COM:
      C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "ORA Skill Cache Drift — <skill list>" -BodyFile "<temp html>" -BodyFormat html
      TO ggoldberg@oxfordra.net ONLY — never cc egoldberg@oxfordra.net, never ze@. Exit-code doctrine matches every other guard: exit 2/4 → retry once then flag loudly; exit 1/3 → do not retry, flag immediately.
  (c) NOTION-FAIL FALLBACK: if (a) failed after its retry, say so explicitly in the email body (b) so the alert still reaches Gabriel.

STEP 6 — ENGINE ERROR you cannot classify (interpreter path wrong, script crashes before producing readable output): write a short note to `C:\Users\Owner\.claude\maintenance\_state\skill-drift-alert-failure-[YYYY-MM-DD-HHmm].md` describing what failed. Never let this look like a clean run.

HARD RULES: Never edit, move, or delete anything in the ora-skills AppData runtime cache — this task only reads it (via repo_first_check.py) and writes to the repo side (open-items-tracker.md) and external systems (Notion, email). Never fabricate a finding the sweep didn't report. Never re-implement or second-guess repo_first_check.py's verdicts — they are authoritative (same posture as ora-doctrine-integrity-guard's probes). This task never posts to the ora-appsec-sweep or automation-health-monitor Notion threads — its own titled page only.