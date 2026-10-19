# LAMS/Cowork R-05 edits table

Generated from `edits.json` (same directory), read-only against the live OneDrive specs on 2026-10-19. `sha base` / `sha new` = first 12 hex of SHA-256 of the file with CRLF normalized to LF (same convention as the CC batch guide). `sha new` was computed by applying the replacements byte-exactly to a scratch copy (each old string matches exactly once in the live file). No BOM in any target. Registry state is read from the LAMS `scheduled-tasks.json` (`enabled`, cron/fireAt).

Flags: **mechanical** = one send sentence, per-code wording, no judgment. **DESIGN-CALL** = proposed wording below needs Gabriel's ratification before apply. **mechanical-but-retired / -spent** = drafted, but recommend SKIP. **REVIEW-ONLY** = no edit.

## Summary

| # | id | live path (under `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\`) | EOL | sha base | sha new | registry enabled | cron / fireAt | hunks | flag |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ora-ar-export-freshness-nudge | `ora-ar-export-freshness-nudge\SKILL.md` | LF | 58d1cac12245 | 84acf9b77f9c | False | `30 11 1,15 * *` | 1 | mechanical |
| 2 | ora-bearmode-refresh | `ora-bearmode-refresh\SKILL.md` | LF | 5256624182b2 | fdddb0d6a3c8 | False | `25 6 9 3,6,9,12 *` | 1 | mechanical |
| 3 | ora-capex-idea-stage-nudge | `ora-capex-idea-stage-nudge\SKILL.md` | LF | 71f3459d08ad | cf13da6884b6 | False | `15 12 1 * *` | 1 | mechanical |
| 4 | ora-consolidate-memory-monthly | `ora-consolidate-memory-monthly\SKILL.md` | LF | 3aba51734b19 | 328d4f120908 | False | `0 5 2 * *` | 1 | mechanical |
| 5 | ora-counsel-review-standard-positions-2027 | `ora-counsel-review-standard-positions-2027\SKILL.md` | LF | 6848f19509d7 | 8e614f0a2fb9 | True | `1817211600000` | 1 | mechanical |
| 6 | ora-dd-critical-tracker | `ora-dd-critical-tracker\SKILL.md` | CRLF | 2ae77bf39339 | 14b9ae37cf92 | False | `35 9 * * 4` | 1 | mechanical |
| 7 | ora-exit-cap-spotcheck | `ora-exit-cap-spotcheck\SKILL.md` | LF | ef872532ee13 | 87979602588f | False | `45 6 9 3,6,9,12 *` | 1 | mechanical |
| 8 | ora-friday-closeout | `ora-friday-closeout\SKILL.md` | LF | b0ca5b8ec586 | 79b3a806b16d | False | `30 16 * * 5` | 1 | mechanical |
| 9 | ora-gis-endpoint-liveping | `ora-gis-endpoint-liveping\SKILL.md` | LF | a2357007dccd | 736b90ba728f | False | `35 6 9 3,6,9,12 *` | 1 | mechanical |
| 10 | ora-health-guard-fail-aging-nudge | `ora-health-guard-fail-aging-nudge\SKILL.md` | LF | 91f7695eed59 | 04a145b2fabc | False | `0 9 * * 1-5` | 1 | mechanical-but-retired |
| 11 | ora-ic-memo-pipeline-reconciliation | `ora-ic-memo-pipeline-reconciliation\SKILL.md` | LF | 8cc0cce94434 | df17b29076b6 | False | `30 10 * * 2` | 1 | mechanical |
| 12 | ora-insurance-renewal-monitor | `ora-insurance-renewal-monitor\SKILL.md` | LF | f299c03d8cc2 | 439d3d0ba4f5 | False | `40 11 * * 1` | 2 | mechanical |
| 13 | ora-lams-fleet-resume-20260911 | `ora-lams-fleet-resume-20260911\SKILL.md` | LF | c671b4a89193 | 806b271d94e4 | False | `1789156860000` | 1 | mechanical-but-spent |
| 14 | ora-lease-expiration-brief | `ora-lease-expiration-brief\SKILL.md` | CRLF | efcfec723143 | e080ecb33b4d | False | `45 10 * * 1` | 1 | mechanical |
| 15 | ora-loan-terms-reconciliation | `ora-loan-terms-reconciliation\SKILL.md` | LF | ab6acb4a1976 | b0cf2c36ffe3 | False | `20 13 6 * *` | 1 | mechanical |
| 16 | ora-monday-sync | `ora-monday-sync\SKILL.md` | CRLF | 58cf14f1611a | 7ff2b79e2b13 | False | `35 10 * * 1` | 1 | mechanical |
| 17 | ora-om-intake-ocr | `ora-om-intake-ocr\SKILL.md` | LF | 5064c9ea0a4e | 7a3f2fb5700d | False | `15 6 * * 3` | 2 | mechanical |
| 18 | ora-owner-outreach-queue-refresh | `ora-owner-outreach-queue-refresh\SKILL.md` | LF | 7dbdd7082b98 | a1abb01ce15d | False | `55 10 * * 1` | 1 | mechanical |
| 19 | ora-replacement-cost-refresh | `ora-replacement-cost-refresh\SKILL.md` | LF | a29c0fe04b9f | b49c186ce5bc | False | `10 6 9 3,6,9,12 *` | 1 | mechanical |
| 20 | ora-underwrite-doctrine-staleness-check | `ora-underwrite-doctrine-staleness-check\SKILL.md` | LF | edc226b6a0d3 | 6abe8b273460 | False | `0 13 * * 3` | 1 | mechanical |
| 21 | automation-health-monitor | `automation-health-monitor\SKILL.md` | LF | 779db55fc74f | 4c696881f07a | False | `5 11 * * 1-5` | 3 | DESIGN-CALL |
| 22 | ora-skill-text-audit | `ora-skill-text-audit\SKILL.md` | CRLF | 14348255aaa2 | 4dd6f8b99122 | False | `45 9 15 * *` | 2 | DESIGN-CALL |
| 23 | ora-stale-pipeline-nudge | `ora-stale-pipeline-nudge\SKILL.md` | LF | 4a642510d982 | (no edit) | False | `15 10 * * 4` | 0 | REVIEW-ONLY-NO-EDIT |

Totals: 23 specs reviewed; 20 mechanical (two of them, `ora-health-guard-fail-aging-nudge` and `ora-lams-fleet-resume-20260911`, are retired / spent: recommend skip), 2 design-call (`automation-health-monitor`, `ora-skill-text-audit`), 1 review-only (`ora-stale-pipeline-nudge`, no edit). The repo send-contract lint reports generic-retry INFO hits on 22 of these specs today; against the scratch copies it reports none.

## Standard wording (same per-code contract as the CC fleet)

- Retry once on exit 2 or 4 (legacy mode). Exit 5 or 6, or any other code: do NOT retry, never resend, flag loudly. Exit 6 = send state unknown, the message MAY have gone out (rules.md section 2).
- Where the CC wording says "the failure record named above", the LAMS specs name no such record, so the flag target is the spec's own existing sink (Notion completion row / Notion page / run summary).
- Variant B (`ora-friday-closeout`, `ora-lease-expiration-brief`, `ora-monday-sync`): the spec retries on "failure or missing bridge". A missing Desktop Commander bridge is not an exit code and nothing was sent, so that retry is kept; only the send-exit part is made per-code.
- Non-send retries are left alone: Notion create-page search-then-retry, SNAPSHOT-WRITE-INVALID re-write and dispatcher retry-line checks in the monitor, driver / promotion non-zero exits in owner-outreach, the claim `fail` release in monday-sync, quota fallback in lease-expiration-brief.

## Per-spec replacements

### ora-ar-export-freshness-nudge  (mechanical)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-ar-export-freshness-nudge\SKILL.md`
- sha base `58d1cac12245` -> sha new `84acf9b77f9c`; LF; registry enabled=False, cron/fireAt `30 11 1,15 * *`, lastRunAt `2026-09-15T15:44:05.548Z`

**Hunk 1 old:**
```text
On non-zero exit, retry once; if still failing, post the full gap detail to the Notion Ops Hub as a fallback.
```
**Hunk 1 new:**
```text
On exit 2 or 4, retry once; if still failing, post the full gap detail to the Notion Ops Hub as a fallback. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the Notion Ops Hub post, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.
```

### ora-bearmode-refresh  (mechanical)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-bearmode-refresh\SKILL.md`
- sha base `5256624182b2` -> sha new `fdddb0d6a3c8`; LF; registry enabled=False, cron/fireAt `25 6 9 3,6,9,12 *`, lastRunAt `2026-07-12T17:04:37.752Z`

**Hunk 1 old:**
```text
on a non-zero COM exit retry once, then flag)
```
**Hunk 1 new:**
```text
on COM exit 2 or 4 retry once, then flag; on exit 5 or 6 (or any code other than 2 or 4) do NOT retry and never resend (exit 6 = send state unknown — the message MAY have gone out), flag it loudly in the run summary)
```

### ora-capex-idea-stage-nudge  (mechanical)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-capex-idea-stage-nudge\SKILL.md`
- sha base `71f3459d08ad` -> sha new `cf13da6884b6`; LF; registry enabled=False, cron/fireAt `15 12 1 * *`, lastRunAt `2026-09-02T09:38:06.904Z`

**Hunk 1 old:**
```text
On a non-zero COM exit code: retry once, then flag the failure loudly in the Notion completion row — do not halt the task.
```
**Hunk 1 new:**
```text
On COM exit code 2 or 4: retry once, then flag the failure loudly in the Notion completion row — do not halt the task. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the Notion completion row, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.
```

### ora-consolidate-memory-monthly  (mechanical)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-consolidate-memory-monthly\SKILL.md`
- sha base `3aba51734b19` -> sha new `328d4f120908`; LF; registry enabled=False, cron/fireAt `0 5 2 * *`, lastRunAt `2026-09-02T09:35:05.760Z`

**Hunk 1 old:**
```text
On non-zero exit: retry once, then flag the failure (do not halt)
```
**Hunk 1 new:**
```text
On exit 2 or 4: retry once, then flag the failure (do not halt); on exit 5 or 6 (or any code other than 2 or 4) do NOT retry and never resend (exit 6 = send state unknown — the message MAY have gone out), flag it loudly in the run summary
```

### ora-counsel-review-standard-positions-2027  (mechanical)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-counsel-review-standard-positions-2027\SKILL.md`
- sha base `6848f19509d7` -> sha new `8e614f0a2fb9`; LF; registry enabled=True, cron/fireAt `1817211600000`, lastRunAt `None`
- note: One-time task (fireAt 2027-08), the only ENABLED LAMS row.

**Hunk 1 old:**
```text
(on non-zero exit: retry once, then flag loudly — do not halt)
```
**Hunk 1 new:**
```text
(on exit 2 or 4: retry once, then flag loudly — do not halt; on exit 5 or 6 (or any code other than 2 or 4) do NOT retry and never resend (exit 6 = send state unknown — the message MAY have gone out), flag it loudly in the run summary)
```

### ora-dd-critical-tracker  (mechanical)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-dd-critical-tracker\SKILL.md`
- sha base `2ae77bf39339` -> sha new `14b9ae37cf92`; CRLF; registry enabled=False, cron/fireAt `35 9 * * 4`, lastRunAt `2026-09-05T19:06:55.886Z`
- note: ASCII-only spec (uses -- and no section sign); CRLF file.

**Hunk 1 old:**
```text
On send failure: retry once, then flag loudly in the Notion page -- do NOT halt.
```
**Hunk 1 new:**
```text
On send exit 2 or 4: retry once, then flag loudly in the Notion page -- do NOT halt. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the Notion page, and never resend (exit 6 = send state unknown -- the message MAY have gone out), per rules.md section 2.
```

### ora-exit-cap-spotcheck  (mechanical)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-exit-cap-spotcheck\SKILL.md`
- sha base `ef872532ee13` -> sha new `87979602588f`; LF; registry enabled=False, cron/fireAt `45 6 9 3,6,9,12 *`, lastRunAt `None`

**Hunk 1 old:**
```text
On a non-zero exit code: retry once, then flag loudly in the Notion completion row; do not halt the task.
```
**Hunk 1 new:**
```text
On exit code 2 or 4: retry once, then flag loudly in the Notion completion row; do not halt the task. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the Notion completion row, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.
```

### ora-friday-closeout  (mechanical)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-friday-closeout\SKILL.md`
- sha base `b0ca5b8ec586` -> sha new `79b3a806b16d`; LF; registry enabled=False, cron/fireAt `30 16 * * 5`, lastRunAt `2026-09-05T17:32:00.068Z`
- note: Variant B: 'missing bridge' is not an exit code and nothing was sent, so its one retry is kept.

**Hunk 1 old:**
```text
On failure or missing bridge: retry once, flag SEND FAILED loudly in the Notion row, continue — do NOT halt.
```
**Hunk 1 new:**
```text
On send exit 2 or 4, or a missing bridge (nothing was sent): retry once, flag SEND FAILED loudly in the Notion row, continue — do NOT halt. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the Notion row, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.
```

### ora-gis-endpoint-liveping  (mechanical)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-gis-endpoint-liveping\SKILL.md`
- sha base `a2357007dccd` -> sha new `736b90ba728f`; LF; registry enabled=False, cron/fireAt `35 6 9 3,6,9,12 *`, lastRunAt `None`

**Hunk 1 old:**
```text
on non-zero exit, retry once then flag loudly in the Notion post rather than halting.
```
**Hunk 1 new:**
```text
on exit 2 or 4, retry once then flag loudly in the Notion post rather than halting; on exit 5 or 6 (or any code other than 2 or 4) do NOT retry and never resend (exit 6 = send state unknown — the message MAY have gone out), flag it loudly in the Notion post.
```

### ora-health-guard-fail-aging-nudge  (mechanical-but-retired)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-health-guard-fail-aging-nudge\SKILL.md`
- sha base `91f7695eed59` -> sha new `04a145b2fabc`; LF; registry enabled=False, cron/fireAt `0 9 * * 1-5`, lastRunAt `2026-09-15T14:44:04.610Z`
- note: Registry row disabled; automation-health-monitor l.267 marks it RETIRED 2026-09-22 (retire-pending). Skip unless it is un-retired.

**Hunk 1 old:**
```text
On send failure: retry once, then flag loudly in the Notion page -- do NOT halt.
```
**Hunk 1 new:**
```text
On send exit 2 or 4: retry once, then flag loudly in the Notion page -- do NOT halt. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the Notion page, and never resend (exit 6 = send state unknown -- the message MAY have gone out), per rules.md section 2.
```

### ora-ic-memo-pipeline-reconciliation  (mechanical)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-ic-memo-pipeline-reconciliation\SKILL.md`
- sha base `8cc0cce94434` -> sha new `df17b29076b6`; LF; registry enabled=False, cron/fireAt `30 10 * * 2`, lastRunAt `2026-10-14T22:06:21.373Z`

**Hunk 1 old:**
```text
On non-zero COM exit: retry once, then flag loudly in the Notion completion row — do not halt.
```
**Hunk 1 new:**
```text
On COM exit 2 or 4: retry once, then flag loudly in the Notion completion row — do not halt. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the Notion completion row, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.
```

### ora-insurance-renewal-monitor  (mechanical)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-insurance-renewal-monitor\SKILL.md`
- sha base `f299c03d8cc2` -> sha new `439d3d0ba4f5`; LF; registry enabled=False, cron/fireAt `40 11 * * 1`, lastRunAt `2026-09-14T15:54:17.613Z`

**Hunk 1 old:**
```text
On a non-zero COM exit code: retry once, then if it still fails, flag it loudly in the Notion completion row instead of halting
```
**Hunk 1 new:**
```text
On COM exit code 2 or 4: retry once, then if it still fails, flag it loudly in the Notion completion row instead of halting
```

**Hunk 2 old:**
```text
do not treat a failed send as a reason to stop the rest of this task.
```
**Hunk 2 new:**
```text
do not treat a failed send as a reason to stop the rest of this task. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the Notion completion row, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.
```

### ora-lams-fleet-resume-20260911  (mechanical-but-spent)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-lams-fleet-resume-20260911\SKILL.md`
- sha base `c671b4a89193` -> sha new `806b271d94e4`; LF; registry enabled=False, cron/fireAt `1789156860000`, lastRunAt `2026-09-11T20:01:37.879Z`
- note: One-time task, lastRunAt 2026-09-11, already auto-disabled. Editing is cosmetic; recommend SKIP (or retire).

**Hunk 1 old:**
```text
on non-zero exit, retry once, then flag loudly and do not halt)
```
**Hunk 1 new:**
```text
on exit 2 or 4, retry once, then flag loudly and do not halt; on exit 5 or 6 (or any code other than 2 or 4) do NOT retry and never resend (exit 6 = send state unknown — the message MAY have gone out), flag it loudly in the run summary)
```

### ora-lease-expiration-brief  (mechanical)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-lease-expiration-brief\SKILL.md`
- sha base `efcfec723143` -> sha new `e080ecb33b4d`; CRLF; registry enabled=False, cron/fireAt `45 10 * * 1`, lastRunAt `2026-09-14T14:50:32.180Z`
- note: Variant B (missing bridge); CRLF file.

**Hunk 1 old:**
```text
On failure or missing bridge: retry once, flag SEND FAILED loudly in the Notion row, continue — do NOT halt.
```
**Hunk 1 new:**
```text
On send exit 2 or 4, or a missing bridge (nothing was sent): retry once, flag SEND FAILED loudly in the Notion row, continue — do NOT halt. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the Notion row, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.
```

### ora-loan-terms-reconciliation  (mechanical)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-loan-terms-reconciliation\SKILL.md`
- sha base `ab6acb4a1976` -> sha new `b0cf2c36ffe3`; LF; registry enabled=False, cron/fireAt `20 13 6 * *`, lastRunAt `2026-09-06T17:21:06.791Z`

**Hunk 1 old:**
```text
On non-zero exit: retry once, then note the failure loudly in the Notion entry and continue. Do NOT halt.
```
**Hunk 1 new:**
```text
On exit 2 or 4: retry once, then note the failure loudly in the Notion entry and continue. Do NOT halt. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the Notion entry, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.
```

### ora-monday-sync  (mechanical)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-monday-sync\SKILL.md`
- sha base `58cf14f1611a` -> sha new `7ff2b79e2b13`; CRLF; registry enabled=False, cron/fireAt `35 10 * * 1`, lastRunAt `2026-09-14T14:44:27.377Z`
- note: Variant B (missing bridge); CRLF; Layer-2 Sent-Items probe at step 6b is unchanged.

**Hunk 1 old:**
```text
On failure or missing bridge: retry once, flag SEND FAILED loudly in the Notion row, continue — do NOT halt.
```
**Hunk 1 new:**
```text
On send exit 2 or 4, or a missing bridge (nothing was sent): retry once, flag SEND FAILED loudly in the Notion row, continue — do NOT halt. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the Notion row, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.
```

### ora-om-intake-ocr  (mechanical)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-om-intake-ocr\SKILL.md`
- sha base `5064c9ea0a4e` -> sha new `7a3f2fb5700d`; LF; registry enabled=False, cron/fireAt `15 6 * * 3`, lastRunAt `2026-10-14T22:06:29.613Z`
- note: Two hunks: the send sentence (l.109) and the close-out 'fails after the one retry' (l.115). The folder-report fallback is NOT a resend, so it is kept for exit 5/6.

**Hunk 1 old:**
```text
on COM failure retry once then flag, do not halt)
```
**Hunk 1 new:**
```text
on COM exit 2 or 4 retry once then flag, do not halt; on exit 5 or 6 (or any code other than 2 or 4) do NOT retry and never resend (exit 6 = send state unknown — the message MAY have gone out): take the folder-report path below and flag it loudly in the run-complete runLog entry)
```

**Hunk 2 old:**
```text
If the Outlook COM send is unavailable or fails after the one retry (e.g. Desktop Commander/PowerShell
```
**Hunk 2 new:**
```text
If the Outlook COM send is unavailable, fails after its one retry (exit 2 or 4), or ends in exit 5 or 6 with no retry (e.g. Desktop Commander/PowerShell
```

### ora-owner-outreach-queue-refresh  (mechanical)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-owner-outreach-queue-refresh\SKILL.md`
- sha base `7dbdd7082b98` -> sha new `a1abb01ce15d`; LF; registry enabled=False, cron/fireAt `55 10 * * 1`, lastRunAt `2026-09-23T16:18:23.399Z`
- note: Other 'NON-ZERO exit' lines (l.54 driver, l.80 promotion) are not sends: untouched.

**Hunk 1 old:**
```text
On a NON-ZERO exit from the send script: retry once, then flag loudly in the Notion Operations Hub completion row (page 32b6ecd8) — do NOT halt.
```
**Hunk 1 new:**
```text
On exit 2 or 4 from the send script: retry once, then flag loudly in the Notion Operations Hub completion row (page 32b6ecd8) — do NOT halt. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the Notion Operations Hub completion row, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.
```

### ora-replacement-cost-refresh  (mechanical)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-replacement-cost-refresh\SKILL.md`
- sha base `a29c0fe04b9f` -> sha new `b49c186ce5bc`; LF; registry enabled=False, cron/fireAt `10 6 9 3,6,9,12 *`, lastRunAt `2026-07-12T17:05:08.454Z`

**Hunk 1 old:**
```text
on COM failure retry once then flag)
```
**Hunk 1 new:**
```text
on COM exit 2 or 4 retry once then flag; on exit 5 or 6 (or any code other than 2 or 4) do NOT retry and never resend (exit 6 = send state unknown — the message MAY have gone out), flag it loudly in the run summary)
```

### ora-underwrite-doctrine-staleness-check  (mechanical)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-underwrite-doctrine-staleness-check\SKILL.md`
- sha base `edc226b6a0d3` -> sha new `6abe8b273460`; LF; registry enabled=False, cron/fireAt `0 13 * * 3`, lastRunAt `2026-09-05T18:55:23.853Z`
- note: ASCII-style dashes (--).

**Hunk 1 old:**
```text
On a non-zero COM exit: retry once, then note the failure loudly in the Notion completion post -- do not halt the task.
```
**Hunk 1 new:**
```text
On COM exit 2 or 4: retry once, then note the failure loudly in the Notion completion post -- do not halt the task. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the Notion completion post, and never resend (exit 6 = send state unknown -- the message MAY have gone out), per rules.md section 2.
```

### automation-health-monitor  (DESIGN-CALL)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\automation-health-monitor\SKILL.md`
- sha base `779db55fc74f` -> sha new `4c696881f07a`; LF; registry enabled=False, cron/fireAt `5 11 * * 1-5`, lastRunAt `2026-09-15T15:14:55.180Z`
- note: Three send sentences (l.10 routing header, l.425 Step 2 alert, l.431 Step 3 meta-failure send which has NO retry sentence today). l.10 also carries the 2026-07-08 'OUTLOOK-COM-SEND-BROKEN ... exit 4' KNOWN ISSUE: historical, left as is (exit 4 stays retryable). Open: (a) this spec's job is to audit send-log for exit-6 / SEND-STATE-UNKNOWN, so the new text should say a stray exit 6 is itself a finding; (b) it is also a synced skill in github.com/ZeOoba/ora-skills (guide section 3C/E), so the same edit must land there or the next sync reverts it; (c) it carries a version changelog (v1.26 last), so decide whether to add a v1.27 line. Registry row is DISABLED (cron 5 11 * * 1-5).

**Hunk 1 old:**
```text
on a non-zero COM exit retry once, then flag — do not halt). **KNOWN ISSUE
```
**Hunk 1 new:**
```text
on COM exit 2 or 4 retry once, then flag — do not halt; on exit 5 or 6 (or any code other than 2 or 4) do NOT retry and never resend (exit 6 = send state unknown — the message MAY have gone out), flag it loudly in the run summary and the chat summary). **KNOWN ISSUE
```

**Hunk 2 old:**
```text
On non-zero COM exit retry once, then flag in the Notion completion row.
```
**Hunk 2 new:**
```text
On COM exit 2 or 4 retry once, then flag in the Notion completion row. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the Notion completion row and the chat summary, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.
```

**Hunk 3 old:**
```text
If Step 1 fails after one retry, AUTO-SEND an Outlook email via the SOLE send path:
```
**Hunk 3 new:**
```text
If Step 1 fails after one retry, AUTO-SEND an Outlook email via the SOLE send path (on COM exit 2 or 4 retry once, then flag in the Notion completion row; on exit 5 or 6 do NOT retry and never resend — exit 6 = send state unknown, the message MAY have gone out — flag it loudly in the chat summary, per rules.md §2):
```

### ora-skill-text-audit  (DESIGN-CALL)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-skill-text-audit\SKILL.md`
- sha base `14348255aaa2` -> sha new `4dd6f8b99122`; CRLF; registry enabled=False, cron/fireAt `45 9 15 * *`, lastRunAt `2026-10-14T22:05:58.338Z`
- note: l.8 routing header (mechanical on its own) and l.107 meta-failure auto-send. Open: the Step 5 'Publish:' enum has only [direct | retry | fallback-sent | total-blackout]; after an exit 6 the fallback alert's state is unknown, which fits none of them. Proposed text keeps the enum unchanged and says to log the value as ❌ fallback-sent plus the words 'state unknown' in the chat summary; alternative is a new enum value (changes the line other consumers may parse). Registry row DISABLED (cron 45 9 15 * *), lastRunAt 2026-10-14. CRLF file.

**Hunk 1 old:**
```text
on a non-zero COM exit retry once, then flag — do not halt). HubSpot
```
**Hunk 1 new:**
```text
on COM exit 2 or 4 retry once, then flag — do not halt; on exit 5 or 6 (or any code other than 2 or 4) do NOT retry and never resend (exit 6 = send state unknown — the message MAY have gone out), flag it loudly in the run summary). HubSpot
```

**Hunk 2 old:**
```text
On a non-zero COM exit retry once, then record the failure.
```
**Hunk 2 new:**
```text
On COM exit 2 or 4 retry once, then record the failure. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: record the failure, log `Publish: ❌ fallback-sent` with the words 'send state unknown' in the chat summary, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.
```

### ora-stale-pipeline-nudge  (REVIEW-ONLY-NO-EDIT)

- live path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-stale-pipeline-nudge\SKILL.md`
- sha base `4a642510d982` -> sha new `4a642510d982`; LF; registry enabled=False, cron/fireAt `15 10 * * 4`, lastRunAt `2026-09-05T17:38:54.872Z`
- note: Caller with no retry: l.100 says a non-zero exit 'is not this task's bug' (Notion is primary; the spec states LAMS has no COM reach). No retry sentence to change and no resend path. Optional later: contract-mode adoption. Registry row DISABLED.
- no replacement.
