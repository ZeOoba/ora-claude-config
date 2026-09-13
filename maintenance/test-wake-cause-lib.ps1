# Tests for wake-cause-lib.ps1 -- sleep-time power attribution (TDD, 2026-09-12).
#
# WHY THIS EXISTS: on 2026-09-12 ora-health-guard fired at 16:21 ET, after Gabriel
# woke and re-plugged the laptop. A.0b chose its late-wake annotation from
# Win32_Battery.BatteryStatus read AT RUN TIME (2 = AC) and emitted "Sleep config
# intact and machine on AC -- the 2026-08-12 sleep cause is EXCLUDED". Wrong: the
# host had been unplugged since 09-11 17:38:02 (Kernel-Power 105 AcOnline=false) and
# the lid was closed at 23:38:19 (506 Reason=15 LidOpenState=false). Run-time state
# says nothing about sleep-time state. The lib therefore takes NO run-time input:
# every verdict comes from events stamped at or before standby entry.
#
# Fixtures below are the real 2026-09-11/12 Kernel-Power events from this host.
# Same PASS/FAIL-and-exit-code convention as the other PowerShell suites here.

. (Join-Path $PSScriptRoot 'wake-cause-lib.ps1')

$script:failures = @()
function Check($label, [bool]$cond) {
    if ($cond) { Write-Output "PASS  $label" }
    else { Write-Output "FAIL  $label"; $script:failures += $label }
}
function T($s) { [datetime]::ParseExact($s, 'yyyy-MM-dd HH:mm:ss', $null) }
function Enter($t, $reason, $lid, $ext, $rem, $full, $v2) {
    [pscustomobject]@{ time = (T $t); data = @{
        Reason = $reason; LidOpenState = $lid; ExternalMonitorConnectedState = $ext
        BatteryRemainingCapacityOnEnter = $rem; BatteryFullChargeCapacityOnEnter = $full
        ScenarioInstanceIdV2 = $v2 } }
}
function Exit507($t, $ac, $v2) {
    [pscustomobject]@{ time = (T $t); data = @{ PowerStateAc = $ac; ScenarioInstanceIdV2 = $v2 } }
}
function AcEv($t, $on) { [pscustomobject]@{ time = (T $t); acOnline = $on } }

$ac = @(
    (AcEv '2026-09-11 13:41:49' $true),  (AcEv '2026-09-11 14:12:34' $false),
    (AcEv '2026-09-11 14:13:02' $false), (AcEv '2026-09-11 15:12:22' $true),
    (AcEv '2026-09-11 17:38:02' $false), (AcEv '2026-09-12 16:18:44' $true)
)
$enters = @(
    (Enter '2026-09-11 21:26:05' 20 $true  $true  76103 75461 2),
    (Enter '2026-09-11 23:38:19' 15 $false $false 55409 75461 5),
    (Enter '2026-09-12 01:38:05' 55 $false $false 54703 75461 7),
    (Enter '2026-09-12 16:19:08' 1  $true  $false 51270 75461 10)
)
$exits = @(
    (Exit507 '2026-09-11 21:26:06' $false 2),  (Exit507 '2026-09-12 01:38:05' $false 5),
    (Exit507 '2026-09-12 16:18:45' $false 7),  (Exit507 '2026-09-12 16:19:08' $true 10)
)
$now = T '2026-09-12 16:21:00'

# ---------------------------------------------------------------------------
# 1. THE INCIDENT, entry by entry.
# ---------------------------------------------------------------------------
$e = @(Get-StandbyEntries -Enters $enters -Exits $exits -AcEvents $ac -Now $now)
Check "4 entries parsed" ($e.Count -eq 4)
Check "23:38 lid close -> LID-CLOSED-ON-BATTERY" ($e[1].cause -eq 'LID-CLOSED-ON-BATTERY')
Check "23:38 power source is Kernel-Power 105 (authoritative)" ($e[1].power.source -eq 'kp105')
Check "23:38 reason name is Lid" ($e[1].reasonName -eq 'Lid')
# Regression for the mis-read premise: 76103 remaining >= 75461 full looks 'plugged,
# full', but 105 says AC was pulled at 17:38. Capacity snapshots are not AC evidence.
Check "21:26 is ON BATTERY despite remaining>=full" ($e[0].cause -eq 'STANDBY-ON-BATTERY')
Check "01:38 session ends at the 16:18:45 exit (V2 match)" ($e[2].sessionEnd -eq (T '2026-09-12 16:18:45'))
Check "16:19 post-wake entry is ON AC" ($e[3].power.state -eq 'AC')

# ---------------------------------------------------------------------------
# 2. Governing entry = the standby that held the missed slot.
# ---------------------------------------------------------------------------
$s = Get-SleepTimePowerSummary -Entries $e -SlotTime (T '2026-09-12 05:15:00')
Check "slot 05:15 governed by 01:38 entry" ($s.entryTime -eq (T '2026-09-12 01:38:05'))
Check "slot summary state DC" ($s.state -eq 'DC')
Check "slot summary cause LID-CLOSED-ON-BATTERY" ($s.cause -eq 'LID-CLOSED-ON-BATTERY')
$s2 = Get-SleepTimePowerSummary -Entries $e
Check "no slot -> longest session (01:38, ~14.7h)" ($s2.entryTime -eq (T '2026-09-12 01:38:05'))
$line = Format-StandbyCause $e[2]
Check "CAUSE line format" ($line -like '`[CAUSE`] LID-CLOSED-ON-BATTERY at 2026-09-12 01:38:05 ::*')

# ---------------------------------------------------------------------------
# 3. Fallback chain: 105 -> 507 PowerStateAc -> falling capacity -> UNKNOWN.
# ---------------------------------------------------------------------------
$e507 = @(Get-StandbyEntries -Enters $enters -Exits $exits -AcEvents @() -Now $now)
Check "no 105 -> 507 PowerStateAc fallback gives DC" ($e507[1].power.state -eq 'DC' -and $e507[1].power.source -eq 'kp507')
$eCap = @(Get-StandbyEntries -Enters $enters -Exits @() -AcEvents @() -Now $now)
Check "no 105/507 -> falling capacity infers DC" ($eCap[1].power.state -eq 'DC' -and $eCap[1].power.source -eq 'capacity-trend')
Check "first entry with no prior -> UNKNOWN" ($eCap[0].power.state -eq 'UNKNOWN')
Check "UNKNOWN power + lid open -> STANDBY-POWER-UNKNOWN" ($eCap[0].cause -eq 'STANDBY-POWER-UNKNOWN')
$rising = @(
    (Enter '2026-09-11 21:00:00' 12 $true $false 40000 75461 1),
    (Enter '2026-09-11 23:00:00' 12 $true $false 60000 75461 2)
)
$eRise = @(Get-StandbyEntries -Enters $rising -Exits @() -AcEvents @() -Now $now)
Check "rising capacity is NOT evidence of AC at sleep -> UNKNOWN" ($eRise[1].power.state -eq 'UNKNOWN')

# Boot boundary: this host does NOT reliably log a 105 after boot (09-11 boots at
# 13:59, 14:12, 16:31 had none), and the charger can change while powered off. A 105
# from a previous boot must not describe a later boot's standby.
$eBootOk = @(Get-StandbyEntries -Enters $enters -Exits $exits -AcEvents $ac `
               -BootTimes @((T '2026-09-11 17:36:37')) -Now $now)
Check "real 09-11 17:36:37 boot precedes the 17:38 105 -> still kp105" ($eBootOk[1].power.source -eq 'kp105')
$eBootX = @(Get-StandbyEntries -Enters $enters -Exits $exits -AcEvents $ac `
               -BootTimes @((T '2026-09-11 20:00:00')) -Now $now)
Check "105 from a previous boot is ignored -> kp507" ($eBootX[1].power.source -eq 'kp507' -and $eBootX[1].power.state -eq 'DC')
Check "ignored 105 is named in detail" ($eBootX[1].power.detail -like '*predates boot*')
$eBootCap = @(Get-StandbyEntries -Enters $enters -Exits @() -AcEvents @((AcEv '2026-09-11 17:38:02' $true)) `
               -BootTimes @((T '2026-09-11 20:00:00')) -Now $now)
Check "stale AC 105 across boot never yields AC -> capacity DC" ($eBootCap[1].power.state -eq 'DC' -and $eBootCap[1].power.source -eq 'capacity-trend')

# ScenarioInstanceIdV2 is per boot. With the real exit missing, a later boot's exit
# reusing V2=5 must NOT be paired with this boot's entry.
$eb1 = (Enter '2026-09-11 23:38:19' 15 $false $false 55409 75461 5); $eb1.data['BootId'] = 144
$xb2 = (Exit507 '2026-09-13 02:00:00' $true 5); $xb2.data['BootId'] = 145
$eBootId = @(Get-StandbyEntries -Enters @($eb1) -Exits @($xb2) -AcEvents @() -Now $now)
Check "V2 reused in another boot is not paired" ($null -eq $eBootId[0].sessionEnd -and $eBootId[0].power.state -eq 'UNKNOWN')

# ---------------------------------------------------------------------------
# 3b. Refute-pass regressions (2026-09-12, adversarial review R1-R7).
# ---------------------------------------------------------------------------
# R1: a slot no standby session covered must not inherit an earlier entry's verdict.
$r1 = @(Get-StandbyEntries -Enters @((Enter '2026-09-12 01:00:00' 12 $true $false 70000 75461 3)) `
          -Exits @((Exit507 '2026-09-12 01:05:00' $true 3)) -AcEvents @((AcEv '2026-09-11 20:00:00' $true)) -Now $now)
$r1s = Get-SleepTimePowerSummary -Entries $r1 -SlotTime (T '2026-09-12 05:15:00') -AcEvents @((AcEv '2026-09-11 20:00:00' $true))
Check "R1 slot outside every session -> UNKNOWN, never AC" ($r1s.state -eq 'UNKNOWN' -and $r1s.source -eq 'no-session-spans-slot')

# R2: unplugged DURING standby, before the slot -> power is judged AT THE SLOT.
$r2ac = @((AcEv '2026-09-11 20:00:00' $true), (AcEv '2026-09-12 03:00:00' $false))
$r2 = @(Get-StandbyEntries -Enters @((Enter '2026-09-12 01:00:00' 12 $true $false 70000 75461 3)) `
          -Exits @((Exit507 '2026-09-12 09:00:00' $false 3)) -AcEvents $r2ac -Now $now)
$r2s = Get-SleepTimePowerSummary -Entries $r2 -SlotTime (T '2026-09-12 05:15:00') -AcEvents $r2ac
Check "R2 unplug mid-standby before slot -> DC at slot" ($r2s.state -eq 'DC' -and $r2s.source -eq 'kp105')
# 105 says AC at entry but the session's 507 says DC: conflicting evidence is not a verdict.
$r2b = @(Get-StandbyEntries -Enters @((Enter '2026-09-12 01:00:00' 12 $true $false 70000 75461 3)) `
          -Exits @((Exit507 '2026-09-12 09:00:00' $false 3)) -AcEvents @((AcEv '2026-09-11 20:00:00' $true)) -Now $now)
Check "R2b 105/507 CONFLICT -> UNKNOWN" ($r2b[0].power.state -eq 'UNKNOWN' -and $r2b[0].power.detail -like '*CONFLICT*')

# R2c: slept on battery, charger plugged in DURING standby before the slot. The sleep
# that caused the miss began on DC -- AC at the slot alone must never mean EXCLUDED.
$r2cac = @((AcEv '2026-09-11 20:00:00' $false), (AcEv '2026-09-12 03:00:00' $true))
$r2c = @(Get-StandbyEntries -Enters @((Enter '2026-09-12 01:00:00' 15 $false $false 70000 75461 3)) `
          -Exits @((Exit507 '2026-09-12 09:00:00' $true 3)) -AcEvents $r2cac -Now $now)
$r2cs = Get-SleepTimePowerSummary -Entries $r2c -SlotTime (T '2026-09-12 05:15:00') -AcEvents $r2cac
Check "R2c replug mid-standby -> summary UNKNOWN, not AC" ($r2cs.state -eq 'UNKNOWN')
# Both judgments AC -> AC is still reachable.
$r2dac = @((AcEv '2026-09-11 20:00:00' $true))
$r2d = @(Get-StandbyEntries -Enters @((Enter '2026-09-12 01:00:00' 12 $true $false 70000 75461 3)) `
          -Exits @((Exit507 '2026-09-12 09:00:00' $true 3)) -AcEvents $r2dac -Now $now)
$r2ds = Get-SleepTimePowerSummary -Entries $r2d -SlotTime (T '2026-09-12 05:15:00') -AcEvents $r2dac
Check "R2d AC at entry AND at slot -> AC" ($r2ds.state -eq 'AC')

# R4: boot times unreadable -> 105 cannot be proven same-boot -> not used.
$r4 = @(Get-StandbyEntries -Enters $enters -Exits @() -AcEvents @((AcEv '2026-09-11 17:38:02' $true)) `
          -BootTimesUnknown -Now $now)
Check "R4 boot times unknown -> 105 skipped, never AC" ($r4[1].power.source -ne 'kp105' -and $r4[1].power.state -ne 'AC')

# R6: capacity trend only within one boot.
$c1 = (Enter '2026-09-11 21:00:00' 12 $true $false 70000 75461 1); $c1.data['BootId'] = 143
$c2 = (Enter '2026-09-12 02:00:00' 12 $true $false 50000 75461 1); $c2.data['BootId'] = 144
$r6 = @(Get-StandbyEntries -Enters @($c1, $c2) -Exits @() -AcEvents @() -Now $now)
Check "R6 capacity fall across boots is not DC evidence" ($r6[1].power.state -eq 'UNKNOWN')

# R7: '05:15' given after midnight-before-05:15 must resolve to the most recent PAST 05:15.
Check "R7 slot later than now rolls back a day" ((Resolve-SlotTime '05:15' (T '2026-09-13 01:00:00')) -eq (T '2026-09-12 05:15:00'))
Check "R7 slot earlier today stays today" ((Resolve-SlotTime '05:15' (T '2026-09-12 16:21:00')) -eq (T '2026-09-12 05:15:00'))
Check "R7 explicit full date is kept" ((Resolve-SlotTime '2026-09-10 05:15' (T '2026-09-12 16:21:00')) -eq (T '2026-09-10 05:15:00'))

# ---------------------------------------------------------------------------
# 4. AC case, empty window.
# ---------------------------------------------------------------------------
$eAc = @(Get-StandbyEntries -Enters @((Enter '2026-09-12 02:00:00' 12 $true $false 70000 75461 3)) `
            -Exits @() -AcEvents @((AcEv '2026-09-11 20:00:00' $true)) -Now $now)
Check "AC via 105, lid open -> STANDBY-ON-AC" ($eAc[0].cause -eq 'STANDBY-ON-AC')
$sNone = Get-SleepTimePowerSummary -Entries @()
Check "no entries -> summary UNKNOWN, never AC" ($sNone.state -eq 'UNKNOWN')

# ---------------------------------------------------------------------------
# 5. Reason codes (ntpoapi.h POWER_MONITOR_REQUEST_REASON, positional).
# ---------------------------------------------------------------------------
Check "reason 0 Unknown"         ((Get-StandbyReasonName 0)  -eq 'Unknown')
Check "reason 1 PowerButton"     ((Get-StandbyReasonName 1)  -eq 'PowerButton')
Check "reason 12 IdleTimeout"    ((Get-StandbyReasonName 12) -eq 'IdleTimeout')
Check "reason 15 Lid"            ((Get-StandbyReasonName 15) -eq 'Lid')
Check "reason 20 SxTransition"   ((Get-StandbyReasonName 20) -eq 'SxTransition')
Check "reason 54 UserInputTouch" ((Get-StandbyReasonName 54) -eq 'UserInputTouch')
Check "reason 55 flagged version-dependent" ((Get-StandbyReasonName 55) -like '*?*')
Check "reason 99 UNKNOWN(99)"    ((Get-StandbyReasonName 99) -eq 'UNKNOWN(99)')

# ---------------------------------------------------------------------------
# 6. EventData XML parse.
# ---------------------------------------------------------------------------
$xml = @'
<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event"><System><EventID>506</EventID></System><EventData><Data Name="Reason">15</Data><Data Name="LidOpenState">false</Data><Data Name="ExternalMonitorConnectedState">false</Data><Data Name="BatteryRemainingCapacityOnEnter">55409</Data><Data Name="BatteryFullChargeCapacityOnEnter">75461</Data><Data Name="ScenarioInstanceIdV2">5</Data></EventData></Event>
'@
$d = ConvertFrom-KpEventData $xml
Check "xml Reason -> int 15" ($d.Reason -is [int] -and $d.Reason -eq 15)
Check "xml LidOpenState -> bool false" ($d.LidOpenState -is [bool] -and -not $d.LidOpenState)
Check "xml capacity -> number" ([long]$d.BatteryRemainingCapacityOnEnter -eq 55409)

if ($script:failures.Count -gt 0) { Write-Output "`n$($script:failures.Count) FAILED"; exit 1 }
Write-Output "`nALL PASS"
exit 0
