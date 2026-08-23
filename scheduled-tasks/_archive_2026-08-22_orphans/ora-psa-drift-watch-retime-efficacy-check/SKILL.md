---
name: ora-psa-drift-watch-retime-efficacy-check
description: One-time 2026-08-19 15:00 ET — verifies the ora-psa-drift-watch 30 13 * * 3 → 45 13 * * 3 retime (applied 2026-08-13 to fix a fleet cron collision with ora-appsec-sweep) actually worked on its first-ever fire. No pre-retime baseline exists (task never ran before the retime) so this checks fire-time correctness, collision-freedom, and Notion delivery rather than a before/after miss rate. Emails ggoldberg only. Auto-disables after firing. One-time CC/MCP task = MODEL-N/A (one-time), exempt from the [MODEL:] tag per memory/reference_scheduled_task_model_standard.md.
---

You are running a ONE-TIME efficacy check on the `ora-psa-drift-watch` retime. Be rigorous and do NOT fabricate: every fact must come from a live read (the scheduled-task registry, the Notion Ops Hub), never assumed or carried forward from this prompt.

# BACKGROUND (recorded — do NOT re-derive)

`ora-psa-drift-watch` (weekly, Wednesday, catches PSA-vs-Notion narrative drift on executed deals) was retimed 2026-08-13 from `30 13 * * 3` to `45 13 * * 3` via the supervised `update_scheduled_task` MCP tool, to fix a same-time fleet cron collision with `ora-appsec-sweep` (both were Wed 13:30 ET) — see `event_log.md` 2026-08-13 and `project_automation_audit_rev7_2026-08-13.md`. As of the retime, `ora-psa-drift-watch` had NEVER fired (registered 2026-08-12, first eligible Wednesday was 2026-08-19) — so unlike sibling efficacy checks (e.g. `ora-pm-ledger-retime-efficacy-check`), there is no pre-retime delivery-history baseline to compare against. This check instead verifies the retime's actual goal directly: did the first fire land at the corrected time, without colliding with `ora-appsec-sweep`, and did the task actually complete and deliver.

# STEP 0 — DATE GUARD (do this FIRST, before any analysis)

**Do NOT trust any date asserted in prose — including in this prompt.** Derive today from the system clock:
`C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe -c "import datetime;print(datetime.datetime.now().isoformat())"`
(Use that FULL interpreter path everywhere; bare `python`/`python3` are unreliable in scheduled sessions.)

This task is armed to fire 2026-08-19 15:00 ET, after the target's first-ever post-retime fire (~13:45 ET the same day, plus scheduler jitter). A sibling task (`ora-pm-ledger-retime-efficacy-check`) has fired days early before due to a scheduler bug — do not repeat that.

**HARD ABORT CONDITION:** if today's date is earlier than 2026-08-19, OR the current time is before 14:00 ET on 2026-08-19, the target fire has not necessarily happened yet. In that case do NOT compute a verdict and do NOT estimate. Email a short COVERAGE GAP notice (subject: `ORA ora-psa-drift-watch retime efficacy — COVERAGE GAP — fired early`) stating the clock date/time and that the check needs re-arming. Then STOP. Reporting "cannot be computed" is a correct, valuable outcome — a fabricated verdict is not.

# STEP 1 — CHECK THE REGISTRY (read-only)

Call `list_scheduled_tasks` (MCP tool — do NOT read the registry JSON file directly via Bash/`python -c`; `config-write-guard` blocks any Bash command whose text names the registry path, even for a read). From the returned entries for `ora-psa-drift-watch` and `ora-appsec-sweep`, record:
- `ora-psa-drift-watch`: `lastRunAt` (did it fire at all this cycle?), `cronExpression` (confirm it is still `45 13 * * 3`, i.e. the retime has not silently reverted), `enabled`.
- `ora-appsec-sweep`: `lastRunAt` for the same Wednesday, `cronExpression` (confirm still `30 13 * * 3`).

If `ora-psa-drift-watch`'s `lastRunAt` is absent or predates 2026-08-19, this is a MISSED-FIRE finding — the retime did not result in an actual run. Report this plainly; do not guess why.

# STEP 2 — COLLISION CHECK

Compare the two `lastRunAt` timestamps (or, if unavailable, the two `nextRunAt`/scheduled fire windows from before this run). Before the retime both tasks nominally fired at 13:30 ET Wednesday (the collision this retime was built to fix). Confirm the two actual fire times are now separated by several minutes (nominal targets are 13:30 for `ora-appsec-sweep` and 13:45 for `ora-psa-drift-watch`, each subject to independent scheduler jitter — a few minutes' gap either way is expected and fine; anything landing within ~1 minute of each other on the same date is a genuine residual collision worth flagging).

# STEP 3 — CONFIRM NOTION DELIVERY

`ora-psa-drift-watch`'s own spec (Step 5/6) posts a run report to the Notion Operations Hub (page `32b6ecd8-9e59-81f2-b329-df3fd0e25062`) titled `PSA Drift Watch — 2026-08-19`, ending with a producer-beacon line: `ora-psa-drift-watch v1.0 completed <ISO timestamp> · deals scanned: N · class A: N · class B: N`.

`notion-search` scoped with `page_url: "32b6ecd8-9e59-81f2-b329-df3fd0e25062"` for `"PSA Drift Watch — 2026-08-19"`. If found, `notion-fetch` it and confirm the producer-beacon line is present and its timestamp is consistent with the registry's `lastRunAt` from STEP 1. If not found, this is a DELIVERY-GAP finding (the task may have fired per the registry but not completed/posted) — report it explicitly, do not assume a cause.

# STEP 4 — RULE ON IT

State a clear verdict on each of three independent questions (a partial pass is possible and should be reported as such, not forced into a single pass/fail):
1. **Fired at all?** Y/N, with the actual `lastRunAt`.
2. **Fired at the corrected time, not the old 13:30 collision slot?** Y/N — compare against `ora-appsec-sweep`'s fire time per STEP 2.
3. **Completed and delivered to Notion?** Y/N per STEP 3.

Overall: RETIME EFFECTIVE (all three Y), RETIME INEFFECTIVE (fired but still collided, or a delivery gap despite firing on time — name which), or DID NOT FIRE (question 1 is N — the retime is moot until the task actually runs).

This is a single-cycle (N=1) observation — say so plainly; a genuine collision or delivery gap on this one Wednesday is real evidence, but do not extrapolate a durable trend from one data point. If the verdict is anything other than clean RETIME EFFECTIVE, recommend a repeat check on the following Wednesday (2026-08-26) rather than asserting the fix failed outright — note this recommendation in the email but do not register the follow-up task yourself (Gabriel's call, same as any schedule change).

# STEP 5 — DELIVER

Email via Outlook COM, the SOLE send path: `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`
TO `ggoldberg@oxfordra.net` ONLY — no cc (the ora-am-brief Daily Brief is the sole cc-Eric exception; this is not it). Never ze@.

Subject: `ORA ora-psa-drift-watch retime efficacy — 2026-08-19 — <verdict>` where `<verdict>` is one of `RETIME EFFECTIVE` / `RETIME INEFFECTIVE` / `DID NOT FIRE` — computed, never presumed. If STEP 0 aborted, use that step's COVERAGE GAP subject instead.

Body: ORA institutional HTML, inline CSS only (Navy #1B2A4A, Gold #C9A96E, Parchment #F5F0E8; EB Garamond/Georgia serif body, DM Sans labels, IBM Plex Mono for ids). Include: the three STEP 4 sub-verdicts with their supporting timestamps, the registry read from STEP 1, the Notion check from STEP 3, and the overall verdict with recommendation.

On non-zero exit: the script already retries once internally on RPC_E_CALL_REJECTED. Do NOT retry further — flag loudly in your output and write the HTML to `C:\Users\Owner\OneDrive - Oxford Capital Partners\Business\ORA\Briefs\outputs\2026-08-19_psa-drift-watch-retime-efficacy.html` as fallback. Exit codes: 0 sent · 1 usage · 2 COM failure · 3 Outlook wizard stuck · 4 COM timeout.

# CONSTRAINTS

- READ-ONLY analysis. Do NOT change any cron, do NOT call `update_scheduled_task`, do NOT modify any SKILL.md, do NOT register a follow-up task yourself. If the verdict recommends a repeat check or a further retime, RECOMMEND it in the email — any schedule change is Gabriel's call.
- Do not fabricate. If the registry or Notion is unreadable, report a COVERAGE GAP rather than estimating.
- End with a short `QUESTIONS FOR GABRIEL` section if anything genuinely needs his ruling.
- One-time task; auto-disables after this run. No cleanup needed.