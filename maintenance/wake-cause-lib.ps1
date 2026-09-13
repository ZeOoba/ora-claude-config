<#
wake-cause-lib.ps1 -- pure functions for SLEEP-TIME power/lid attribution.
Dot-sourced by wake-cause-probe.ps1; tested by test-wake-cause-lib.ps1.

WHY (2026-09-12). ora-health-guard A.0b picked its late-wake annotation from
Win32_Battery.BatteryStatus read AT RUN TIME. The 09-12 run fired at 16:21 ET after
the laptop had been re-plugged, read AC, and declared the sleep cause EXCLUDED. The
host had actually been on battery since 09-11 17:38:02 with the lid closed from
23:38:19. Run-time state is not sleep-time state. Nothing in this file reads the
live machine: every verdict is derived from logged events describing the standby
session (105/506 at or before the judged instant, 507 for the same session).

EVIDENCE SOURCES, in precedence order (all Microsoft-Windows-Kernel-Power, System log):
  kp105          Event 105 "Power source change", EventData AcOnline. The last 105 at
                 or before the judged instant (the 506 entry, or the slot for the
                 governing summary) is the power source then. Authoritative
                 ONLY within the same boot: a 105 older than the last OS start
                 (Kernel-General 12) before the entry is ignored, because this host does
                 not reliably log a 105 after boot (09-11 boots at 13:59, 14:12 and 16:31
                 had none) and the charger can change while the machine is off.
  kp507          Event 507 (Modern Standby exit) PowerStateAc for the SAME session
                 (matched on ScenarioInstanceIdV2). Observed on this host to describe
                 the session, not the exit instant: 09-12 16:18:45 507 PowerStateAc=false
                 one second AFTER 105 AcOnline=true at 16:18:44. Semantics are not
                 documented by Microsoft -- secondary source only.
  capacity-trend BatteryRemainingCapacityOnEnter FALLING vs the prior 506 entry -> DC
                 (inferred). A RISING value is NOT treated as AC: charging between two
                 entries does not prove the charger was still attached at the second.
                 Capacity snapshots are also not AC evidence on their own -- 09-11 21:26
                 read 76103 remaining vs 75461 full while 105 said DC since 17:38.
  (none)         UNKNOWN. Never defaults to AC.

REASON CODES. 506 Reason is decoded positionally against POWER_MONITOR_REQUEST_REASON
(ntpoapi.h), https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntpoapi/ne-ntpoapi-power_monitor_request_reason
(page updated 2026-06-29; the enum is "reserved for system use"). Microsoft does not
document that 506 Reason uses this enum; the mapping is corroborated locally by
Reason=15 (Lid) co-occurring with LidOpenState=false. Indices 0-54 appear in both the
page's Syntax block and its Constants table. 55-57 (RestrictedStandbyBatteryDrain,
DozeRestrictedStandby, SmartRestrictedStandby) appear ONLY in the Syntax block; in the
Constants table 55 is Max. They are therefore reported with a trailing '?'. Anything
else is UNKNOWN(n).
#>

$script:StandbyReasonNames = @(
  'Unknown','PowerButton','RemoteConnection','ScMonitorpower','UserInput',
  'AcDcDisplayBurst','UserDisplayBurst','PoSetSystemState','SetThreadExecutionState','FullWake',
  'SessionUnlock','ScreenOffRequest','IdleTimeout','PolicyChange','SleepButton',
  'Lid','BatteryCountChange','GracePeriod','PnP','DP',
  'SxTransition','SystemIdle','NearProximity','ThermalStandby','ResumePdc',
  'ResumeS4','Terminal','PdcSignal','AcDcDisplayBurstSuppressed','SystemStateEntered',
  'Winrt','UserInputKeyboard','UserInputMouse','UserInputTouchpad','UserInputPen',
  'UserInputAccelerometer','UserInputHid','UserInputPoUserPresent','UserInputSessionSwitch','UserInputInitialization',
  'PdcSignalWindowsMobilePwrNotif','PdcSignalWindowsMobileShell','PdcSignalHeyCortana','PdcSignalHolographicShell','PdcSignalFingerprint',
  'DirectedDrips','Dim','BuiltinPanel','DisplayRequiredUnDim','BatteryCountChangeSuppressed',
  'ResumeModernStandby','TerminalInit','PdcSignalSensorsHumanPresence','BatteryPreCritical','UserInputTouch'
)
$script:StandbyReasonNamesVersionDependent = @(
  'RestrictedStandbyBatteryDrain','DozeRestrictedStandby','SmartRestrictedStandby'
)

function Get-StandbyReasonName([object]$Code) {
  if ($null -eq $Code) { return 'UNKNOWN(null)' }
  $n = [int]$Code
  if ($n -ge 0 -and $n -lt $script:StandbyReasonNames.Count) { return $script:StandbyReasonNames[$n] }
  $v = $n - $script:StandbyReasonNames.Count
  if ($v -ge 0 -and $v -lt $script:StandbyReasonNamesVersionDependent.Count) {
    return ($script:StandbyReasonNamesVersionDependent[$v] + '?')
  }
  return "UNKNOWN($n)"
}

# EventData XML -> hashtable with typed values (bool / int / long; else raw string).
function ConvertFrom-KpEventData([string]$Xml) {
  $h = @{}
  $doc = [xml]$Xml
  foreach ($node in @($doc.Event.EventData.Data)) {
    if ($null -eq $node -or -not $node.Name) { continue }
    $raw = [string]$node.'#text'
    $i = 0; $l = [long]0
    if ($raw -eq 'true') { $val = $true }
    elseif ($raw -eq 'false') { $val = $false }
    elseif ([int]::TryParse($raw, [ref]$i)) { $val = $i }
    elseif ([long]::TryParse($raw, [ref]$l)) { $val = $l }
    else { $val = $raw }
    $h[$node.Name] = $val
  }
  return $h
}

# Power source in force at $AtTime (default: the 506 entry instant). Returns
# { state AC|DC|UNKNOWN; source kp105|kp507|capacity-trend|none; detail }.
function Resolve-SleepTimePower {
  param($Entry, $PriorEntry, $Exit, $AcEvents = @(), $BootTimes = @(),
        [switch]$BootTimesUnknown, [Nullable[datetime]]$AtTime = $null)
  $at = if ($null -ne $AtTime) { [datetime]$AtTime } else { $Entry.time }
  $atTxt = $at.ToString('yyyy-MM-dd HH:mm:ss')
  $note = ''
  $last105 = $null
  if ($BootTimesUnknown) {
    $note = 'boot times unreadable, 105 cannot be proven same-boot and is unused; '
  } else {
    $lastBoot = @($BootTimes | Where-Object { $_ -and $_ -le $at } | Sort-Object) | Select-Object -Last 1
    $last105 = @($AcEvents | Where-Object { $_ -and $_.time -le $at } | Sort-Object time) | Select-Object -Last 1
    if ($last105 -and $lastBoot -and $last105.time -lt $lastBoot) {
      $note = "105 AcOnline=$($last105.acOnline.ToString().ToLower()) @ $($last105.time.ToString('yyyy-MM-dd HH:mm:ss')) predates boot at $($lastBoot.ToString('yyyy-MM-dd HH:mm:ss')), ignored; "
      $last105 = $null
    }
  }
  $ac507 = $null
  if ($Exit -and $Exit.data -and $Exit.data.ContainsKey('PowerStateAc')) { $ac507 = [bool]$Exit.data['PowerStateAc'] }

  if ($last105) {
    $state = if ($last105.acOnline) { 'AC' } else { 'DC' }
    $detail = "Kernel-Power 105 AcOnline=$($last105.acOnline.ToString().ToLower()) @ $($last105.time.ToString('yyyy-MM-dd HH:mm:ss')) (judged at $atTxt)"
    if ($null -ne $ac507 -and $ac507 -ne [bool]$last105.acOnline) {
      # Contradicting evidence is not a verdict -- an AC read here is what A.0b turns
      # into "EXCLUDED", so the conservative answer is UNKNOWN.
      return [pscustomobject]@{ state = 'UNKNOWN'; source = 'kp105'
        detail = "$detail; CONFLICT: session 507 PowerStateAc=$($ac507.ToString().ToLower())" }
    }
    return [pscustomobject]@{ state = $state; source = 'kp105'; detail = $detail }
  }
  if ($null -ne $ac507) {
    $state = if ($ac507) { 'AC' } else { 'DC' }
    return [pscustomobject]@{ state = $state; source = 'kp507'
      detail = "${note}session 507 PowerStateAc=$($ac507.ToString().ToLower()) @ $($Exit.time.ToString('yyyy-MM-dd HH:mm:ss')) (no usable same-boot 105)" }
  }
  $cur = $Entry.data['BatteryRemainingCapacityOnEnter']
  $prev = $null
  if ($PriorEntry) {
    $b1 = $Entry.data['BootId']; $b0 = $PriorEntry.data['BootId']
    # A fall across a reboot says nothing about the charger at this entry.
    if ($null -eq $b1 -or $null -eq $b0 -or $b1 -eq $b0) { $prev = $PriorEntry.data['BatteryRemainingCapacityOnEnter'] }
  }
  if ($null -ne $cur -and $null -ne $prev -and [long]$cur -lt [long]$prev) {
    return [pscustomobject]@{ state = 'DC'; source = 'capacity-trend'
      detail = "${note}inferred: BatteryRemainingCapacityOnEnter fell $prev -> $cur since $($PriorEntry.time.ToString('yyyy-MM-dd HH:mm:ss')) (same boot)" }
  }
  return [pscustomobject]@{ state = 'UNKNOWN'; source = 'none'
    detail = "${note}no usable same-boot 105, no session 507 PowerStateAc, no same-boot falling capacity" }
}

# Enters/Exits: objects { time [datetime]; data [hashtable] } from 506 / 507.
# AcEvents:     objects { time [datetime]; acOnline [bool] } from 105.
# BootTimes:    [datetime] OS starts (Kernel-General 12) -- bounds 105 validity.
#               Pass -BootTimesUnknown when they could not be read.
function Get-StandbyEntries {
  [CmdletBinding()]
  param($Enters = @(), $Exits = @(), $AcEvents = @(), $BootTimes = @(),
        [switch]$BootTimesUnknown, [datetime]$Now = (Get-Date))
  $ent = @($Enters | Where-Object { $_ } | Sort-Object time)
  $ex  = @($Exits  | Where-Object { $_ } | Sort-Object time)
  $out = New-Object System.Collections.ArrayList
  $prior = $null
  foreach ($en in $ent) {
    $d = $en.data
    $v2 = $d['ScenarioInstanceIdV2']
    $boot = $d['BootId']
    if ($null -ne $v2) {
      # V2 is per boot -- also require the same BootId when both events carry one.
      $exit = $ex | Where-Object { $_.time -ge $en.time -and $_.data['ScenarioInstanceIdV2'] -eq $v2 -and
                                   ($null -eq $boot -or $null -eq $_.data['BootId'] -or $_.data['BootId'] -eq $boot) } |
              Select-Object -First 1
    } else {
      $exit = $ex | Where-Object { $_.time -ge $en.time } | Select-Object -First 1
    }
    $power = Resolve-SleepTimePower -Entry $en -PriorEntry $prior -Exit $exit -AcEvents $AcEvents `
               -BootTimes $BootTimes -BootTimesUnknown:$BootTimesUnknown
    $end = if ($exit) { $exit.time } else { $null }
    $until = if ($end) { $end } else { $Now }
    [void]$out.Add([pscustomobject]@{
      time        = $en.time
      reason      = $d['Reason']
      reasonName  = Get-StandbyReasonName $d['Reason']
      lidOpen     = $d['LidOpenState']
      extMonitor  = $d['ExternalMonitorConnectedState']
      battRemain  = $d['BatteryRemainingCapacityOnEnter']
      battFull    = $d['BatteryFullChargeCapacityOnEnter']
      power       = $power
      cause       = Get-StandbyCauseLabel $d['LidOpenState'] $power.state
      sessionEnd  = $end
      durationMin = [math]::Round(($until - $en.time).TotalMinutes, 1)
      src         = [pscustomobject]@{ entry = $en; prior = $prior; exit = $exit }
    })
    $prior = $en
  }
  # Unrolled on purpose: callers wrap in @(), and a comma-wrapped return nests.
  return $out.ToArray()
}

function Get-StandbyCauseLabel($LidOpen, [string]$PowerState) {
  $prefix = if ($null -ne $LidOpen -and -not [bool]$LidOpen) { 'LID-CLOSED' } else { 'STANDBY' }
  $suffix = switch ($PowerState) { 'AC' { 'ON-AC' } 'DC' { 'ON-BATTERY' } default { 'POWER-UNKNOWN' } }
  return "$prefix-$suffix"
}

# '05:15' -> the most recent PAST 05:15 relative to $Now (a catch-up run after
# midnight must not target a slot in the future). A string with a date is kept as-is.
function Resolve-SlotTime([string]$Text, [datetime]$Now = (Get-Date)) {
  $t = [datetime]::Parse($Text)
  if ($Text.Trim() -match '^\d{1,2}:\d{2}(:\d{2})?$') {
    $t = $Now.Date.Add($t.TimeOfDay)
    if ($t -gt $Now) { $t = $t.AddDays(-1) }
  }
  return $t
}

# The entry that governs a late wake. With -SlotTime: the standby session that was
# open AT the slot, with power re-judged AT the slot (an unplug mid-standby counts);
# if no session spans the slot the answer is UNKNOWN -- an earlier, finished session
# says nothing about 05:15. Without -SlotTime: the longest session, judged at entry.
function Get-SleepTimePowerSummary {
  param($Entries = @(), [Nullable[datetime]]$SlotTime = $null, $AcEvents = @(), $BootTimes = @(),
        [switch]$BootTimesUnknown)
  $es = @($Entries | Where-Object { $_ })
  if ($es.Count -eq 0) { return (New-UnknownSummary 'no-standby-entry' 'no 506 entry in window') }

  if ($null -eq $SlotTime) {
    $g = $es | Sort-Object durationMin -Descending | Select-Object -First 1
    return [pscustomobject]@{ state = $g.power.state; source = $g.power.source; cause = $g.cause
      entryTime = $g.time; lidOpen = $g.lidOpen; reason = $g.reason; reasonName = $g.reasonName
      detail = $g.power.detail }
  }
  $slot = [datetime]$SlotTime
  $g = @($es | Where-Object { $_.time -le $slot -and ($null -eq $_.sessionEnd -or $_.sessionEnd -ge $slot) } |
         Sort-Object time) | Select-Object -Last 1
  if (-not $g) {
    $near = @($es | Where-Object { $_.time -le $slot } | Sort-Object time) | Select-Object -Last 1
    if ($near) {
      $nearEnd = if ($near.sessionEnd) { $near.sessionEnd.ToString('yyyy-MM-dd HH:mm:ss') } else { 'open' }
      $det = "latest earlier standby $($near.time.ToString('yyyy-MM-dd HH:mm:ss')) ended $nearEnd, before the slot"
    } else { $det = 'no standby entry at or before the slot' }
    return (New-UnknownSummary 'no-session-spans-slot' "$det -- host was awake, off, or unobserved at $($slot.ToString('yyyy-MM-dd HH:mm'))")
  }
  $p = Resolve-SleepTimePower -Entry $g.src.entry -PriorEntry $g.src.prior -Exit $g.src.exit -AcEvents $AcEvents `
         -BootTimes $BootTimes -BootTimesUnknown:$BootTimesUnknown -AtTime $slot
  # AC is the answer A.0b turns into "EXCLUDED", so it needs BOTH judgments: a sleep
  # that began on battery and was plugged in before the slot is not an AC sleep.
  # DC at the slot stands on its own (the battery policy governed the slot).
  if ($p.state -eq 'AC' -and $g.power.state -ne 'AC') {
    $p = [pscustomobject]@{ state = 'UNKNOWN'; source = $p.source
      detail = "AC at slot ($($p.detail)) but $($g.power.state) at entry ($($g.power.detail)) -- charger changed during standby" }
  }
  return [pscustomobject]@{ state = $p.state; source = $p.source; cause = (Get-StandbyCauseLabel $g.lidOpen $p.state)
    entryTime = $g.time; lidOpen = $g.lidOpen; reason = $g.reason; reasonName = $g.reasonName
    detail = $p.detail }
}

function New-UnknownSummary([string]$Source, [string]$Detail) {
  return [pscustomobject]@{ state = 'UNKNOWN'; source = $Source; cause = $null; entryTime = $null
    lidOpen = $null; reason = $null; reasonName = $null; detail = $Detail }
}

function Format-StandbyCause($E) {
  $lid = if ($null -eq $E.lidOpen) { 'unknown' } elseif ($E.lidOpen) { 'open' } else { 'closed' }
  $batt = 'unknown'
  if ($null -ne $E.battRemain -and $null -ne $E.battFull -and [long]$E.battFull -gt 0) {
    $batt = "$($E.battRemain)/$($E.battFull) ($([math]::Round(100.0 * [long]$E.battRemain / [long]$E.battFull))%)"
  }
  $end = if ($E.sessionEnd) { $E.sessionEnd.ToString('yyyy-MM-dd HH:mm:ss') } else { 'open' }
  return ("[CAUSE] $($E.cause) at $($E.time.ToString('yyyy-MM-dd HH:mm:ss')) :: " +
    "reason=$($E.reason) $($E.reasonName) lid=$lid ext_monitor=$($E.extMonitor) battery=$batt " +
    "power=$($E.power.state) via $($E.power.source) ($($E.power.detail)) " +
    "session_end=$end ($([math]::Round($E.durationMin / 60, 1))h)")
}
