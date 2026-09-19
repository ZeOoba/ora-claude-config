---
name: ora-notion-trial-expiry-reminder
description: One-time 2026-09-29 10:00 ET — reminds Gabriel the 14-day Notion paid-plan trial (started 2026-09-18 to resolve OI-288's free-block quota) is about to lapse; re-verifies notion-create-pages live and re-arms the degraded-mode fallback if it has already reverted to free. Sends and stops.
---

You are a one-time reminder task for Oxford Realty Advisors (ORA). Run once, then stop. Do not fabricate anything — if a step is inconclusive, say so plainly in the email rather than asserting a result.

CONTEXT (read before acting, do not restate their content, just use it):
- `C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\reference_notion_free_block_quota_exhausted_2026-09-12.md` — full history of OI-288 (Notion free-plan 1,000-block cap blocking `notion-create-pages` fleet-wide). Key facts already established: deleting/archiving/emptying trash NEVER frees blocks (verified against Notion's own docs) — the only real fix is a paid plan. Gabriel started a 14-day trial on 2026-09-18 (assumed expiry ~2026-10-02 — not independently confirmed against a billing timestamp). Workspace has exactly 2 human members (Gabriel + Eric Goldberg), which is why the free-plan cap applies; Plus-tier pricing at that seat count is roughly $16-20/month.
- `C:\Users\Owner\.claude\maintenance\_state\notion-publish-degraded.json` — degraded-mode state file. Currently `active: false` with a `trial_expiry_risk` field describing this exact situation.
- `open-items-tracker.md#OI-288` — kept OPEN (not closed) pending permanent conversion.

STEP 0 — DOUBLE-FIRE ENTRY GUARD (added 2026-09-18; run before STEP 1). This is a one-time reminder, but a catch-up burst (both fleets fire only while the Desktop app is open) or a manual re-run before the auto-disable takes effect would create a duplicate Notion test page and a duplicate email. Run this first:

```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py claim --task ora-notion-trial-expiry-reminder --block main --run-id <run_id> --ttl-min 30
```

- **Exit 10** → this already ran. Log `BLOCK_MAIN_ALREADY_COMPLETE_TODAY`, do not create a test page or send, and stop — this task auto-disables after firing, so a second fire finding a COMPLETE record confirms the auto-disable is doing its job.
- **Exit 11** → another fire is live. Stand down identically.
- **Exit 0** → proceed to STEP 1.

**Only the run that holds the claim may call `complete` or `fail`.** A run that stood down (exit 10 or 11) calls neither. Full contract: `_shared/README-DOUBLE-FIRE-GUARD.md`.

STEPS:

1. Live-check whether the trial (or a converted paid plan) is still in effect: use the Notion MCP connector to call `notion-create-pages`, creating one small test page under the Ops Hub parent (`32b6ecd8-9e59-81f2-b329-df3fd0e25062`), titled "OI-288 Trial-Expiry Check — <today's date>". If it succeeds, the cap is still lifted (trial active, or already converted). If it fails with "used all of its free blocks" (or similar), the trial has already lapsed back to free and the cap is back.

2. **PRE-SEND SENT-ITEMS PROBE (mandatory, immediately before the send below).** Layer 2 of the STEP 0 guard, dated stem:

```
powershell -ExecutionPolicy Bypass -File C:\Users\Owner\.claude\scheduled-tasks\_shared\outlook-sent-probe.ps1 -SubjectFile "<temp .txt containing exactly: Notion trial ending soon - OI-288 - <today's date>>"
```

Exit 10 → do NOT send, log `MAIN_EMAIL_ALREADY_IN_SENT_ITEMS`, and still call `block-sentinel.py complete` below so Layer 1 re-converges. Exit 1 → fail open: send anyway, and note the probe gap in the email body.

Draft and send ONE email via Outlook COM (`C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` — the sole send path) to `ggoldberg@oxfordra.net` ONLY (no cc). Subject: "[ACTION] Notion trial ending soon — OI-288 — <today's date>" (the date suffix gives the probe above a stable dated stem to match on). Body must state, plainly:
   - Today's date and how many days remain until the assumed ~2026-10-02 expiry (recompute from today, don't hardcode "a few days" if it's actually different).
   - The result of step 1's live check, stated as a fact you just observed, not inferred.
   - If step 1 SUCCEEDED (still on a working plan): remind Gabriel this is very likely still the 14-day trial, not a permanent conversion, and that he needs to explicitly convert to a paid tier (Plus, ~$16-20/mo at 2 seats) in Notion's Settings → Upgrade Plan before it lapses, or the block cap returns fleet-wide with no further warning from this task (it fires once and stops).
   - If step 1 FAILED (cap already back): say so as an [ACTION] item — the trial already lapsed, every Notion-writing scheduled task is degraded again as of now, and this needs his decision today, not just a heads-up. In this case also flip `notion-publish-degraded.json`'s `active` field back to `true` and clear the `trial_expiry_risk`/`cleared_at`/`cleared_how` fields (restore the pre-trial `active:true` shape), since the degraded-mode fallback needs to be live again — this file is a plain state file, not a shared registry, so editing it directly is fine.
   - A one-line pointer to `reference_notion_free_block_quota_exhausted_2026-09-12.md` and `open-items-tracker.md#OI-288` for full history — do not restate their content beyond what's above.

3. If (and only if) you touched `open-items-tracker.md` in step 2 (you should NOT need to for this task — it's a state-file edit, not a tracker edit): first claim `sched-open-items-tracker` via `python hooks/lib/claim_work.py claim sched-open-items-tracker "OI-288 trial-expiry reminder" --paths open-items-tracker.md`, release it after, and if the claim is refused (another session holds it), skip that edit and just note in the email that the tracker note itself couldn't be updated this run.

4. This task auto-disables after firing (one-time). Nothing further to schedule — do not re-register a follow-up unless a future session decides that's needed.

5. Close the STEP 0 claim now that the email has sent (or been skipped as an already-sent duplicate per STEP 2's probe):

```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py complete --task ora-notion-trial-expiry-reminder --block main --run-id <run_id> --email-sent-at <ISO8601>
```

If the run aborts before sending, call `fail --task ora-notion-trial-expiry-reminder --block main --run-id <run_id> --error "<what broke>"` instead, so the claim does not strand at IN_PROGRESS for the full TTL.

Do not attempt to check the exact trial expiry date/timestamp in Notion's billing UI — that's not available via the connector; rely only on the live `notion-create-pages` functional check in step 1.