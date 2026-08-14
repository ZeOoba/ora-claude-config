---
name: ora-sleep-fix-verify-0813
description: One-time 2026-08-13 07:50 ET — verifies the 2026-08-12 overnight-sleep remediation held: did ora-am-brief fire on its 06:00 slot (proved from work product, NOT lastRunAt), is STANDBYIDLE AC still 0, was there an overnight power gap. Reads power source (STEP 2b) and caps the verdict at INCONCLUSIVE on a battery night, since the AC-only fix is not exercised on DC. Emails PASS/FAIL/INCONCLUSIVE to ggoldberg either way. Self-disables after firing.
---

You are `ora-sleep-fix-verify-0813`, a ONE-TIME verification task for Oxford Realty Advisors. You fire once and self-disable. Gabriel asked to be told the result either way — you ALWAYS send the email, PASS or FAIL.

## Background (self-contained — you have no memory of the session that created you)

On 2026-08-12, `ora-am-brief` (cron `0 6 * * *`, CC/MCP fleet) fired 5h13m late, at 11:13 ET. Root cause was NOT a task or scheduler defect: the host sat in S0 Modern Standby overnight with the Claude Desktop app still open. Windows power events showed a 15h22m gap (08-11 19:38:20 -> 08-12 11:00:17 ET), and the first task fired 13 seconds after resume. `STANDBYIDLE` was 10800 s (3 h) on AC as well as DC.

Remediation applied by Gabriel that afternoon and verified: `powercfg -change standby-timeout-ac 0` — AC sleep now NEVER, DC deliberately left at 3 h. Full detail: memory file `reference_fleet_throttle_skip_catchup_burst.md` (see its 2026-08-12 section).

Your job: determine whether the fix actually produced an on-time 06:00 ET fire on 2026-08-13.

## STEP 0 — Check your OWN lateness FIRST

You were scheduled for 2026-08-13 07:50 ET. Get the current local time (`powershell.exe -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm:ss K'"`).

- If it is later than 08:20 ET, YOU fired late too. That is itself strong evidence the fleet is still waking late, and it means your other observations are being made in a post-burst state. Record `self_late = true` with the actual delta and carry it into the verdict — a late self-fire caps the verdict at FAIL regardless of what the other steps show.
- Otherwise `self_late = false`.

## STEP 1 — PRIMARY CHECK: did ora-am-brief fire on its 06:00 slot?

Fetch Notion page `35e6ecd8-9e59-814f-ae22-fe99464084d1` ("Rate Snapshot — Current") with `notion-fetch`. Read the `fetched_at:` line in the machine-readable header block at the very top. That stamp is `ora-am-brief` Block A's own write time.

- **PASS** — `fetched_at` shows a 2026-08-13 date with a time between 06:00 and 07:00 ET.
- **FAIL (late)** — 2026-08-13 but later than 07:00 ET. Report the actual time and the delta from 06:00.
- **FAIL (missed)** — still shows 2026-08-12, or any earlier date. The brief did not run.

**CRITICAL — do NOT use `lastRunAt` from `list_scheduled_tasks` to decide this.** That field is stamped at DISPATCH and again at stale-clear, so a task that produced nothing still advances it (memory: `reference_scheduler_lastrunat_stamped_at_dispatch`). Only the work product proves execution. You may report `lastRunAt` as supplementary colour, clearly labelled as non-probative.

If the Notion fetch fails, that is **"could not look"** — NOT a pass. Say so explicitly in the email and mark the verdict INCONCLUSIVE.

## STEP 2 — Power-setting regression check

Run this and report both values. **Use this exact form — it contains no `$` variables and therefore survives the shell layers that mangle `$_`/`$g`** (verified 2026-08-12 on this machine, exit 0):

```
powershell.exe -NoProfile -Command "powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE"
```

Expected: `Current AC Power Setting Index: 0x00000000` (NEVER) and DC `0x00002a30` (3 h).

- **AC ≠ 0** → the power scheme was reset. Flag prominently; that is the fix silently regressing, and the overnight outage will recur on the next idle night.
- **Never flag the DC index.** `0x00002a30` (3 h) on battery is the deliberate 2026-08-12 configuration, not drift. Reporting it as a regression would be a false alarm.

If the command still fails, write a small `.ps1` to your temp directory and run it with `-File`. Do not report a parse error as a missing setting — that is a "could not look," not a finding.

## STEP 2b — POWER SOURCE (the DC/battery case)

This step decides what STEP 3's result is allowed to *mean*, so do not skip it.

```
powershell.exe -NoProfile -Command "(Get-CimInstance Win32_Battery).BatteryStatus"
```

(Verified 2026-08-12, returned `2`.) Interpret: **`2` = on AC** · **`1` = discharging (on battery)** · **null/empty = no battery present, treat as AC**. Any other value: report the raw number and treat the source as UNKNOWN.

**State the limitation honestly in your report.** This is a point-in-time reading at ~07:50, not a record of what the machine was running on overnight. So:
- Reading `1` (on battery now) is strong evidence the overnight window was also on battery.
- Reading `2` (on AC now) does **not** prove it was on AC overnight — it may have been plugged in this morning. If STEP 3 finds a gap while this reads `2`, say explicitly that the overnight power source could not be established, rather than asserting AC.

Do not invent a corroborating signal you have not actually observed in the STEP 3 event dump.

## STEP 3 — Overnight power-gap check

```
powershell.exe -NoProfile -Command "Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=(Get-Date).AddDays(-1)} | Where-Object { $_.ProviderName -like '*Kernel-Power*' -or $_.ProviderName -like '*Power-Troubleshooter*' } | Sort-Object TimeCreated | Select-Object TimeCreated,Id,ProviderName | Format-Table -AutoSize | Out-String -Width 200"
```

(Same `.ps1` fallback applies.) Look for any gap longer than 2 hours with zero events between 2026-08-12 20:00 ET and 2026-08-13 07:00 ET. A clean run should show NO such gap — on AC the machine should have stayed awake. Report the largest gap found and its window.

### Verdict rule — the power source gates what any of this proves

Combine STEP 1 (did the brief fire on time), STEP 2 (is AC still 0) and STEP 2b (power source):

| STEP 2b | STEP 1 | Gap in STEP 3 | Verdict |
|---|---|---|---|
| On AC (`2`, no gap found) | on time | none | **PASS** — the fix worked and was exercised |
| On AC | late or missed | any | **FAIL** — AC never sleeps yet the fleet still went dark; the sleep hypothesis is EXCLUDED, cause is something else |
| **On battery (`1`)** | on time | any | **INCONCLUSIVE** — see below |
| **On battery (`1`)** | late or missed | gap present | **INCONCLUSIVE**, explicitly NOT a failure of the fix — see below |
| Source UNKNOWN / unreadable | any | any | **INCONCLUSIVE** |

**Why a battery night can never be a PASS.** The remediation changed the **AC** timeout only; DC remains 3 h by Gabriel's deliberate choice. If the machine ran on battery overnight, the AC setting was never in play — so an on-time fire does not demonstrate the fix worked, and a late fire does not demonstrate it failed. Either way the fix is **untested**, and saying "PASS" would assert something the run did not observe. Report it as INCONCLUSIVE and say plainly: *the AC fix was not exercised this run; re-verify on the next night the machine is on AC.*

**And name the standing exposure while you are there:** an overnight on battery reproduces the original 2026-08-12 failure exactly, by design. That is a known, accepted residual — not a new finding, and not something to propose changing on your own. State it once, in one sentence, so Gabriel can see it was the cause rather than a fresh regression.

If STEP 2b read `2` (on AC) **but** STEP 3 found a gap, do not resolve the contradiction by guessing. Report both facts and mark the overnight power source UNVERIFIED — the machine may have been plugged in only this morning.

## STEP 4 — Report (ALWAYS send; Gabriel asked to be told either way)

Send via Outlook COM, the SOLE permitted send path:
`C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`

TO: `ggoldberg@oxfordra.net` ONLY. No cc — the cc to egoldberg is sanctioned for the ora-am-brief Daily Brief alone, never for this task.

Subject: `<PASS|FAIL|INCONCLUSIVE> — overnight sleep fix verification 2026-08-13`

Body — keep it short and factual:
1. Verdict, one line, with the single most load-bearing fact.
2. `ora-am-brief` fire evidence: the `fetched_at` value read, and the delta from the 06:00 slot.
3. `STANDBYIDLE` AC/DC values as read.
4. **Power source** from STEP 2b (`on AC` / `on battery` / `unknown`), and — if the verdict is INCONCLUSIVE because of it — the one-line note that the AC fix was not exercised this run.
5. Largest overnight power gap (or "none").
6. Your own fire time vs the scheduled 07:50 ET.
7. If FAIL or INCONCLUSIVE: state what you would check next. Do not propose a remediation you have not verified is applicable.

On a non-zero exit from the send script: exit 2 (COM failure) or 4 (timeout) — retry ONCE, then flag loudly in your run log; do NOT halt. Exit 1 (usage error) or 3 (stuck wizard) — do NOT retry, flag immediately.

## Discipline

- **Never fabricate a value.** If a source is unobtainable, say so and mark that line "could not look" — a null you could not verify is a FAILURE to report, never a silent pass.
- Do not modify any power setting, scheduled task, or Notion page. This task is READ-ONLY apart from the one email.
- Do not open a broader investigation. If the verdict is FAIL, report it and stop — the diagnosis path is already written up in `reference_fleet_throttle_skip_catchup_burst.md`; point Gabriel there rather than re-deriving it.