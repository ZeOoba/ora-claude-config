# AM-cluster late wake — root cause, 2026-08-13

**Status:** RESOLVED as a diagnosis. Two remediations are host-level and await Gabriel's decision.
**Supersedes as the default hypothesis:** "the host is sleeping / the sleep config regressed."
**Escalation trigger:** three consecutive 5h+ late mornings (08-11, 08-12, 08-13) with
`STANDBYIDLE` AC = 0 confirmed intact on each. The question was reframed as *why the Desktop app
does not dispatch through 05:15–06:30 ET.* The answer is that on those mornings **it was not
running.** Not throttled, not hung, not misconfigured — absent.

## The finding, in one line

Three system-initiated reboots out of Modern Standby at **04:32 / 04:40 / 04:41 ET on 2026-08-13**,
driven by Windows Update, killed the Claude Desktop process ~33 minutes before the 05:15 slot.
Claude Desktop has no launch-at-logon or launch-at-startup entry, so the scheduler did not exist
again until the app was opened manually at **10:50:41**.

## Why A.0b could never have caught it

`ora-health-guard` A.0b (added 2026-08-12) reads `STANDBYIDLE`'s **AC index** and escalates a
non-zero value. On this host that check is scoped to one cause out of at least four:

| | AC STANDBYIDLE | Visible to A.0b? |
|---|---|---|
| Host powered off | irrelevant | no |
| Modern Standby (S0ix) | irrelevant | no |
| WU reboot from Modern Standby | irrelevant | no |
| Classic S3 sleep-after regression | relevant | yes |

**This host is Modern Standby.** `powercfg /a` reports `Standby (S0 Low Power Idle) Network
Connected`, `Hibernate`, `Fast Startup` available; S1/S2/S3 all unavailable ("This standby state is
disabled when S0 low power idle is supported"). Under S0ix the machine enters low-power idle
irrespective of `STANDBYIDLE`. **A clean AC index is therefore not evidence the host stayed awake** —
which is exactly why "sleep config confirmed intact" and "the host slept anyway" looked
contradictory. Both were simply true.

Current power config, for the record (`powercfg /q SCHEME_CURRENT SUB_SLEEP`, 2026-08-13):
`STANDBYIDLE` AC `0x0` (Never) / DC `0x2a30` (3h, ratified 2026-08-12) ·
`HIBERNATEIDLE` AC `0x0` / DC `0x0` · `RTCWAKE` enabled both · `HYBRIDSLEEP` on both
(inert — Hybrid Sleep unavailable because S3 is). Machine was on AC, battery 100%, at time of
reading. **Nothing here is misconfigured.**

## Three mornings, three different causes

Each is a distinct failure mode. Conflating them is what kept the sleep hypothesis alive.

**2026-08-11 — HOST POWERED OFF.** `User32` 1074 at 2026-08-10 12:50:37 ET: `winlogon.exe`
initiated the *power off* of the computer. No log lines of any kind until the app cold-started
2026-08-11 17:01:20. Nothing was running to be late.

**2026-08-12 — MODERN STANDBY, PROCESS SUSPENDED.** Last activity 2026-08-11 19:38:18
(`sessions-bridge` `ERR_NETWORK_IO_SUSPENDED`), first activity 2026-08-12 11:00:16
(`event-loop-stall … 2654ms [likely sleep: power_event]` → `System resumed; waking poll loop`).
~15h22m in S0ix. The app process **survived** — a resume, not a cold start — and
`ora-health-guard` spawned at 11:00:19, three seconds after resume. A suspended process correctly
does not dispatch; there is no defect here beyond the host being asleep at 05:15.

**2026-08-13 — WINDOWS UPDATE REBOOT STORM.** The decisive case, and the only one where something
is actually fixable:

```
00:33:05  WU started downloading  2026-08 Security Update
00:38:05  WU install started
03:28:10  Modern Standby exit/enter churn begins
04:28-04:31  four more S0ix exit/enter cycles; scheduler logs
             "Deferring check: N s post-wake delay remaining" each time
04:32:22  User32 1074 — MoUsoCoreWorker.exe initiated RESTART
             (reason: Operating System: Service pack (Planned))
04:36:49  Kernel-Power 109  shutdown transition
04:36:56  Kernel-Power 577  prepared for system initiated reboot FROM MODERN STANDBY
04:37:23  Kernel-Power 578  detected system initiated reboot from Modern Standby
04:40:09  User32 1074 — TrustedInstaller.exe initiated RESTART  (#2)
04:41:18  User32 1074 — TrustedInstaller.exe initiated RESTART  (#3)
04:45:54  WU install successful: 2026-08 Security Update + .NET Framework rollup
--------  05:15 ET ora-health-guard slot passes with NO Claude Desktop process alive
--------  06:00 ET ora-am-brief slot passes, same
10:50:33  Modern Standby exit (user)
10:50:41  [keep-awake] started (id=0) / wake-scheduler claim id=scheduled-tasks
10:50:42  [ScheduledTasks] Reset
10:50:43  [ScheduledTasks] Renderer listener ready
10:50:46  [ScheduledTasks] Initialized      <-- COLD START
10:50:49  ora-health-guard spawns, 5h35m late
11:03:49  ora-am-brief spawns
```

## The diagnostic signature that separates the three — do not re-derive this

**COLD START** = `[keep-awake] started` → `Reset` → `Renderer listener ready` → `Initialized`,
with **no** preceding large `event-loop-stall … [likely sleep: power_event]`. A new process. The
app did not exist before this moment.

**RESUME** = a large `event-loop-stall … [likely sleep: power_event]` (2026-08-12 14:06:10 logged
`blocked for 6914695ms` ≈ 115 min) followed by `System resumed; waking poll loop`, then
`Deferring check: N s post-wake delay remaining`. Same process, throughout.

The 2026-08-13 10:50 recovery is unambiguously the first. That single distinction is the whole
diagnosis: **a scheduler cannot dispatch a slot that falls while its process is gone**, and no
amount of power-scheme correctness changes that.

Secondary observation, 04:28–04:31: each S0ix resume re-armed a fresh ~60s post-wake deferral
(`52s`, `59s`, `51s`, `10s` remaining across four cycles). Rapid resume churn can therefore starve
the dispatcher of a clean tick even while the process is alive. Not the cause on 08-13 — the
reboots were — but worth knowing before attributing a near-miss to something else.

## Remediations — REPORT ONLY, Gabriel's decision

Neither is a power-scheme change; neither is reachable by A.0b; both are host-level and outside
the fleet's authority.

1. **Windows Update active hours currently permit an unattended reboot in the AM-cluster window.**
   The 04:32 reboot was `Operating System: Service pack (Planned)` — a scheduled maintenance
   action, not a crash. Setting active hours to cover roughly 00:00–08:00 would move it out of the
   05:15–06:30 band. Trade-off: updates then install during the working day.
2. **Claude Desktop has no launch-at-logon / launch-at-startup entry.** After any reboot — WU or
   otherwise — fleet dispatch stops silently until a human opens the app. This is the larger of the
   two: it converts every reboot into a total outage of unknown duration. Note the app needs an
   interactive user session, so a "run whether logged on or not" Task Scheduler entry will not
   work; the realistic options are a Run-key/Startup-folder entry plus auto-logon, or accepting
   that reboots require a manual restart.

Detection is now in place regardless of which is chosen: `ora-health-guard` v1.7 A.0c runs
`maintenance/wake-cause-probe.ps1` on every late fire and names the cause in the alert body
(`WU-REBOOT` / `HOST-POWER-OFF` / `MODERN-STANDBY` / `SCHEDULER-COLD-START`), so the next late
morning arrives with its cause attached instead of a sleep-config guess.

## What NOT to do next time

- Do not read a clean `STANDBYIDLE` AC index as evidence the host stayed awake. Under S0ix it is
  not evidence of anything about wakefulness.
- Do not treat "the Desktop app isn't dispatching" as the question until a cold-start check has
  ruled out "the Desktop app isn't running." They look identical from the registry.
- Do not re-run the `powercfg` investigation. Both indices are recorded above and both are correct.
- `powercfg /sleepstudy`, `/waketimers`, and `/lastwake` all require elevation and were unavailable
  from an unelevated session. `/sleepstudy` is the one worth running under elevation if this
  recurs *without* a WU reboot in the window.

## Sources (all primary, all on-host, all 2026-08-13)

Windows System event log: `Microsoft-Windows-Kernel-Power` 42/107/109/506/507/577/578 ·
`User32` 1074 · `Microsoft-Windows-WindowsUpdateClient` 19/43/44 · `EventLog` 6005/6006.
Claude Desktop `%APPDATA%\Claude\logs\main*.log`. `powercfg /q SCHEME_CURRENT SUB_SLEEP`,
`powercfg /a`. Registry `lastRunAt` / `lastScheduledFor` from both scheduled-tasks.json stores.
