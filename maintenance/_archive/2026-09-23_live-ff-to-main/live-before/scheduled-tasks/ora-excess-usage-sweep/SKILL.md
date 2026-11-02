---
name: ora-excess-usage-sweep
description: Weekly Friday 3:00 PM ET check of remaining weekly Claude usage — if meaningful capacity remains before the 4:00 PM reset, works down the Open Items tracker (open-items-triage priority order) via Engineering OS lanes for the remaining window; opens PRs for anything above trivial L1 fixes, never merges, never touches Hard-Invariant blast-radius paths or oxfordra.net without confirmation. Silent no-op if usage is already near cap. Reports to ggoldberg@oxfordra.net only. v1.0 2026-09-18. [MODEL: claude-opus-5 | set 2026-09-18]
---

PURPOSE: Each Friday at 3:00 PM ET, check whether meaningful weekly Claude usage capacity remains before the 4:00 PM ET weekly reset, and if so, spend it productively on the highest-priority items in the ORA Open Items tracker before the reset — rather than let unused capacity go to waste. This is a Code-surface (CC/MCP fleet) task: filesystem, git, PRs.

## STEP 0 — DOUBLE-FIRE ENTRY GUARD (added 2026-09-18; run before STEP 1)

This task shares the same overnight-offline catch-up-burst exposure that hit `ora-am-brief`/`ora-deal-aging-sla` on 2026-08-09 (both fleets fire only while the Desktop app is open, so a stretch offline through a Friday 3pm slot re-arms this task at next open) — nothing stands a second fire down today, and a duplicate mid-window run would burn a second usage check, a second backlog pass, and could open duplicate PRs for the same Open Items. Run this first, before STEP 1:

```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py claim --task ora-excess-usage-sweep --block main --run-id <run_id> --ttl-min 60
```

TTL is 60, not the 30 default, because this run's own budget spans the full 3:00-4:00 PM ET window (STEP 1 hard-stops work ~10 minutes before the 4:00 PM reset) — longer than the default assumes.

- **Exit 10** → today's run already completed. Log `BLOCK_MAIN_ALREADY_COMPLETE_TODAY`, do not proceed to STEP 1, and report it as a NORMAL skip (not a miss), citing the earlier run's summary email/PR links.
- **Exit 11** → another fire is live. Stand down identically.
- **Exit 0** → proceed to STEP 1.

Close the claim on whichever exit the run actually takes:

```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py complete --task ora-excess-usage-sweep --block main --run-id <run_id> --email-sent-at <ISO8601>
```

Omit `--email-sent-at` on the STEP 1 no-op path (no send happened — a legitimate complete with no send, same convention as `ora-open-sessions-board`'s 0-actionable-items path). If the run aborts instead, call `fail --error "<what broke>"` so the claim does not strand at IN_PROGRESS for the full TTL. **Only the run that holds the claim may call `complete` or `fail`** — a run that stood down at STEP 0 (exit 10 or 11) calls neither. Full contract: `_shared/README-DOUBLE-FIRE-GUARD.md`. Do not "fix" a double-fire by retiming this task's cron — the burst is documented fleet-wide behavior; the guard belongs here.

STEP 1 — USAGE CHECK.
Call mcp__ccd_session_mgmt__get_usage (session_id "self"). Read plan.windows. Find the window labeled "Weekly · all models" (fall back to any window whose label starts with "Weekly" if that exact label is absent — plan tiers can change). Note its percentUsed and resetsAt/resetsIn.
- If percentUsed >= 97, OR resetsIn indicates less than ~15 minutes remain: there is no meaningful excess capacity. Log a one-line NO-OP note (date, percentUsed, resetsIn) and STOP — close the STEP 0 claim with `complete` (no `--email-sent-at`, per above). Do not send an email for a pure no-op (matches fleet convention of silence on clean/no-op runs).
- Otherwise: proceed to Step 2. Note resetsAt — that is your hard stop for this run. Budget your work to finish (including any commits, PR pushes, and the summary email) at least ~10 minutes before resetsAt.

STEP 2 — CLAIM + SOURCE THE BACKLOG.
Run `python hooks/lib/claim_work.py claim sched-open-items-tracker "excess-usage sweep <today's date>" --paths open-items-tracker.md` before any write to the tracker (scheduled-task claim-bearing-task rule — unattended run, sched- prefixed slug, 30-min TTL, force-takeover is routine against a stale unattended holder). If refused against a live claim from another active session, log that and skip tracker writes this run (read-only triage is still fine).
Then invoke the `open-items-triage` agent to get the reconciled, deduped, prioritized Open Items list. This is the SOLE source of "pressing matters" for this task — do not substitute your own discretion or pull from anywhere else (Gabriel's explicit choice, 2026-09-18).

STEP 3 — WORK THE BACKLOG.
Starting from the top of the triaged list, for each item within your time budget:
- Triage it to an Engineering OS lane per CLAUDE.md's lane table (L1 Fast / L2 debug / L3 build / L4 refactor / L5 research / L6 domain skill / L7 ship), same as any other non-trivial request. Run the pre-flight failure analysis for L2+ items (assume it fails; name the top failure modes; verify against ground truth) before touching anything.
- Hard stop conditions — never touch, under any lane, regardless of time pressure: anything in the Hard-Invariant blast-radius list (hooks/**, *.env*/*credentials*, confidential-terms.json, settings.json, CLAUDE.md/~/.claude config, scheduled-task registries, CSP/headers, financial-constant/governor files) without the full supervised single-writer procedure; any oxfordra.net deploy (always needs Gabriel's per-deploy confirmation, no unattended exception); any financial model or governor constant edit (DSCR/LTV) without permission; any active confidential-deal data exposed externally.
- Financial/governor-adjacent code (oxford-command-center scoring/NOI/capital-config, underwriting models) must be dispatched at Fable tier or above per CLAUDE.md's Dispatch invariants, never below Fable for that class, even though this run's own driving model may be Opus.
- TERMINAL ACTION CAP (Gabriel-directed, 2026-09-18): trivial L1 fixes that pass blast-radius may complete inline with a normal commit. Everything else — L2 and above — must land as an OPEN PULL REQUEST on a feature branch, with whatever local review/verification an unattended run can do (tests, linting, a self-review pass), and then STOP. Never merge to main autonomously, regardless of what the ordinary merge-gate/adversarial-review machinery would otherwise permit.
- Respect existing single-writer/claim protocols for whatever repo/checkout the item touches (isolated-commit skill for shared checkouts under ~/.claude-family; ordinary git branch+PR for app repos like website-canonical/oxford-command-center/ora-pm).
- Stop taking on new items once within ~15 minutes of the Step 1 hard stop; finish whatever is in flight cleanly rather than starting something new.

STEP 4 — CLOSE OUT.
For every item completed inline or PR'd, mark it appropriately in open-items-tracker.md (done, or "PR open: <link>") — respecting the Step 2 claim. Release the claim (`claim_work.py release sched-open-items-tracker`) when done, even on a partial run.

STEP 5 — REPORT.
Compose the summary subject with a **dated stem**, `Excess-Usage Sweep - {YYYY-MM-DD}` (today's date, computed once at run start with `date '+%A %Y-%m-%d'` — date part in every date slot, weekday only where one is named — and reused exactly in every title, subject and body), and append whatever run-specific counts/tags fleet convention uses — the stem is what the pre-send probe below matches on.

**PRE-SEND SENT-ITEMS PROBE (mandatory, immediately before the send).** Layer 2 of the STEP 0 guard:

```
powershell -ExecutionPolicy Bypass -File C:\Users\Owner\.claude\scheduled-tasks\_shared\outlook-sent-probe.ps1 -SubjectFile "<temp .txt containing exactly: Excess-Usage Sweep - {YYYY-MM-DD}>"
```

Exit 10 → do NOT send, log `MAIN_EMAIL_ALREADY_IN_SENT_ITEMS`, record a NORMAL skip, and still call `block-sentinel.py complete` below so Layer 1 re-converges with reality. Exit 1 → fail open: send anyway, and record the probe gap in the summary.

Send ONE summary email via the Outlook COM send-via-outlook.ps1 script (C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 — the sole send path; on non-zero exit, retry once, then flag loudly) to ggoldberg@oxfordra.net ONLY (no cc — no Daily-Brief exception applies here). Include: the usage window's percentUsed/resetsIn observed at Step 1, which OI items were worked, which completed inline vs. opened as PRs (with links), which were skipped and why (blast-radius/invariant/time-budget), and what remains at the top of the backlog for next week. Never fabricate progress — if the backlog was empty or nothing could be safely started, say so plainly.

Close the STEP 0 claim now that the durable output has landed:

```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py complete --task ora-excess-usage-sweep --block main --run-id <run_id> --email-sent-at <ISO8601>
```

NEVER: merge a PR to main, deploy oxfordra.net, edit a financial model/governor constant, touch a Hard-Invariant blast-radius path outside its supervised procedure, or expose confidential deal data — regardless of remaining time budget or usage pressure to "use it all."