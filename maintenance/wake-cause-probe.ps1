<#
wake-cause-probe.ps1 -- classify WHY the scheduler did not dispatch in a window.

WHY THIS EXISTS (2026-08-13). ora-health-guard A.0b checks STANDBYIDLE on AC and
escalates a non-zero index as POWER SLEEP REGRESSION. On this host that check is
structurally incapable of explaining a late morning:

  * AC STANDBYIDLE = 0 (Never) and HIBERNATEIDLE = 0 on both AC and DC. Clean.
  * The host is Modern Standby (S0 Low Power Idle) -- `powercfg /a` confirms S1/S2/S3
    are all unavailable. Under S0ix the machine enters low-power idle regardless of
    STANDBYIDLE, so a clean STANDBYIDLE proves nothing about whether the host slept.
  * DC STANDBYIDLE = 10800s (3h) is unchecked entirely.
  * Neither index can see the two causes actually observed: a host POWER-OFF, and a
    Windows Update Orchestrator REBOOT out of Modern Standby.

Three consecutive 5h+ late mornings, three DIFFERENT causes, none of them "the
Desktop app is running but not dispatching":
  2026-08-11  host powered off (winlogon 1074 power-off 2026-08-10 12:50) until 17:01
  2026-08-12  host in Modern Standby 2026-08-11 19:38 -> 2026-08-12 11:00; app
              process suspended, correctly not dispatching
  2026-08-13  MoUsoCoreWorker.exe (Update Orchestrator) restarted the machine at
              04:32, then TrustedInstaller twice more at 04:40 and 04:41 -- three
              system-initiated reboots from Modern Standby, all BEFORE the 05:15
              slot. Claude Desktop does not auto-start after a reboot, so the
              scheduler process did not exist until manual launch at 10:50.

This probe reports the CAUSE, so a late morning is never again attributed to a
sleep-config regression by default.

SLEEP-TIME STATE (2026-09-12). A late-wake annotation must describe the machine AT
STANDBY ENTRY, never at run time. On 09-12 ora-health-guard read Win32_Battery at
16:21, after the laptop was re-plugged, and declared the sleep cause EXCLUDED while
the host had in fact slept on battery with the lid closed (506 at 23:38:19 Reason=15
LidOpenState=false; 105 AcOnline=false since 09-11 17:38:02). This probe now decodes
506/507/105 EventData via wake-cause-lib.ps1 and emits one [CAUSE] line per standby
entry (LID-CLOSED-ON-BATTERY, STANDBY-ON-AC, ...), plus a SLEEP-TIME-POWER summary
for the entry that governed -SlotTime (or the longest session). Evidence precedence
and Reason-code provenance are documented in wake-cause-lib.ps1.

HOST-OFF CONFIRMATION (2026-09-12 follow-up). A User32 1074 is a REQUEST. It is
reported as HOST-POWER-OFF / WU-REBOOT / RESTART only when Kernel-General 13 (full
shutdown) or Kernel-Power 42 TargetState=6 (Fast Startup hybrid shutdown -- this host
has HiberbootEnabled=1, and those log no 6006/109/13) follows it, with the power-restore
time taken from the next Kernel-Boot 27. Unconfirmed requests print as [note], never
[CAUSE]. Standalone 42 TargetState=5 is HOST-HIBERNATE, standalone 13 is HOST-SHUTDOWN.
Boot boundaries come from Kernel-Boot 27, which is logged on every boot; Kernel-General
12 is not logged on Fast Startup or hibernate-resume boots. Details: wake-cause-lib.ps1.
A Get-WinEvent "No events were found" is an empty result, never [unverifiable].

Exit: 0 = no unexplained gap   1 = cause identified (report it)   2 = could not look
#>
param(
  [double]$WindowHours = 24,
  [string]$JsonOut,
  # Missed slot to attribute, e.g. '05:15' (today) or '2026-09-12 05:15'. Optional.
  [string]$SlotTime,
  # 105 power-source events are rare; look back further than the window so the
  # source in force at the first standby entry is known.
  [int]$AcLookbackDays = 7
)

$ErrorActionPreference = 'Continue'
$start = (Get-Date).AddHours(-$WindowHours)
$findings = New-Object System.Collections.ArrayList
$events   = New-Object System.Collections.ArrayList
$unver    = New-Object System.Collections.ArrayList

$libOk = $false
try { . (Join-Path $PSScriptRoot 'wake-cause-lib.ps1'); $libOk = $true }
catch { [void]$unver.Add("wake-cause-lib.ps1 unloadable -- no sleep-time attribution: $($_.Exception.Message)") }
$slot = $null
if ($SlotTime) {
  try { $slot = Resolve-SlotTime $SlotTime (Get-Date) }
  catch { [void]$unver.Add("SlotTime '$SlotTime' unparseable -- governing entry falls back to longest session") }
}
$msEnters = New-Object System.Collections.ArrayList
$sleep42  = New-Object System.Collections.ArrayList
$kp41     = New-Object System.Collections.ArrayList
$requests = New-Object System.Collections.ArrayList
$markers13 = New-Object System.Collections.ArrayList
$boot27   = New-Object System.Collections.ArrayList
$boot12   = New-Object System.Collections.ArrayList
$bootRecords = @()
$offPeriods = @()
$msExits  = New-Object System.Collections.ArrayList
$acEvents = New-Object System.Collections.ArrayList

function Add-Ev($t, $kind, $detail) {
  [void]$events.Add([pscustomobject]@{ time = $t; kind = $kind; detail = $detail })
}

# --- 1. Power / reboot events -------------------------------------------------
try {
  Get-WinEvent -FilterHashtable @{
      LogName = 'System'
      ProviderName = 'Microsoft-Windows-Kernel-Power'
      Id = @(41, 42, 107, 109, 506, 507, 577, 578)
      StartTime = $start
    } -ErrorAction Stop | ForEach-Object {
      $k = switch ($_.Id) {
        41  { 'DIRTY-REBOOT' }
        42  { 'SLEEP-ENTER' }      107 { 'SLEEP-EXIT' }
        506 { 'MODERN-STANDBY-ENTER' } 507 { 'MODERN-STANDBY-EXIT' }
        109 { 'SHUTDOWN-TRANSITION' }
        577 { 'REBOOT-PREPARED' }  578 { 'REBOOT-DETECTED' }
      }
      Add-Ev $_.TimeCreated $k ($_.Message -split "`n")[0].Trim()
      if ($libOk -and $_.Id -eq 41) { [void]$kp41.Add($_.TimeCreated) }
      if ($libOk -and $_.Id -in @(42, 506, 507)) {
        try {
          $rec = [pscustomobject]@{ time = $_.TimeCreated; data = (ConvertFrom-KpEventData $_.ToXml()) }
          if ($_.Id -eq 506) { [void]$msEnters.Add($rec) }
          elseif ($_.Id -eq 507) { [void]$msExits.Add($rec) }
          else {
            [void]$sleep42.Add([pscustomobject]@{ time = $_.TimeCreated; targetState = $rec.data['TargetState']
              effectiveState = $rec.data['EffectiveState']; reason = $rec.data['Reason'] })
          }
        } catch { [void]$unver.Add("Kernel-Power $($_.Id) EventData unparseable at $($_.TimeCreated): $($_.Exception.Message)") }
      }
    }
} catch {
  if ($_.Exception.Message -notmatch 'No events were found') {
    [void]$unver.Add("Kernel-Power log unreadable: $($_.Exception.Message)")
  }
}

# --- 1b. Power-source changes (Kernel-Power 105 AcOnline), longer lookback -----
# Plus boots: a 105 is only valid within its own boot. Kernel-Boot 27 is logged on
# EVERY boot; Kernel-General 12 misses Fast Startup and hibernate-resume boots, so 12
# only fills in where no 27 exists. Kernel-General 13 marks full shutdowns.
$bootTimes = @()
$bootUnknown = $false
if ($libOk) {
  try {
    Get-WinEvent -FilterHashtable @{
        LogName = 'System'; ProviderName = 'Microsoft-Windows-Kernel-Boot'
        Id = 27; StartTime = $start.AddDays(-$AcLookbackDays)
      } -ErrorAction Stop | ForEach-Object {
        $d = ConvertFrom-KpEventData $_.ToXml()
        [void]$boot27.Add([pscustomobject]@{ time = $_.TimeCreated; bootType = $d['BootType'] })
      }
  } catch {
    if ($_.Exception.Message -notmatch 'No events were found') {
      $bootUnknown = $true
      [void]$unver.Add("Kernel-Boot 27 unreadable -- boot boundaries incomplete, 105 unused: $($_.Exception.Message)")
    }
  }
  try {
    Get-WinEvent -FilterHashtable @{
        LogName = 'System'; ProviderName = 'Microsoft-Windows-Kernel-General'
        Id = @(12, 13); StartTime = $start.AddDays(-$AcLookbackDays)
      } -ErrorAction Stop | ForEach-Object {
        if ($_.Id -eq 12) { [void]$boot12.Add($_.TimeCreated) }
        elseif ($_.TimeCreated -ge $start) { [void]$markers13.Add($_.TimeCreated) }
      }
  } catch {
    if ($_.Exception.Message -notmatch 'No events were found') {
      [void]$unver.Add("Kernel-General 12/13 unreadable -- full-shutdown confirmation unavailable: $($_.Exception.Message)")
    }
  }
  if ($boot27.Count -eq 0 -and $boot12.Count -gt 0 -and -not $bootUnknown) {
    # 12 is blind to Fast Startup / hibernate boots; 12 without any 27 is not a boundary set.
    $bootUnknown = $true
    [void]$unver.Add("Kernel-Boot 27 returned no events while Kernel-General 12 did -- boot boundaries incomplete, 105 unused")
  }
  $bootRecords = @(Get-BootRecords -Boot27 $boot27 -KernelGeneral12 $boot12)
  $bootTimes = @($bootRecords | ForEach-Object { $_.time })
  try {
    Get-WinEvent -FilterHashtable @{
        LogName = 'System'; ProviderName = 'Microsoft-Windows-Kernel-Power'
        Id = 105; StartTime = $start.AddDays(-$AcLookbackDays)
      } -ErrorAction Stop | ForEach-Object {
        $d = ConvertFrom-KpEventData $_.ToXml()
        if ($d.ContainsKey('AcOnline')) {
          [void]$acEvents.Add([pscustomobject]@{ time = $_.TimeCreated; acOnline = [bool]$d['AcOnline'] })
        }
      }
  } catch {
    # Get-WinEvent throws "No events were found" when the filter matches nothing --
    # that is a real empty result, not a failure to look.
    if ($_.Exception.Message -notmatch 'No events were found') {
      [void]$unver.Add("Kernel-Power 105 unreadable -- sleep-time power falls back to 507/capacity: $($_.Exception.Message)")
    }
  }
}

# --- 2. Who initiated a restart / power-off (User32 1074) ---------------------
try {
  # 30-min lookback: a request just before the window can own a shutdown just inside it.
  Get-WinEvent -FilterHashtable @{ LogName='System'; Id=1074; StartTime=$start.AddMinutes(-30) } -ErrorAction Stop |
    ForEach-Object {
      $m = ($_.Message -split "`n")[0].Trim()
      if ($libOk) {
        # A request, not an outcome -- Resolve-HostOffPeriods decides what happened.
        $d = @{}
        try { $d = ConvertFrom-KpEventData $_.ToXml() } catch { }
        $action = if ($d['param5']) { [string]$d['param5'] } elseif ($m -match 'power off') { 'power off' } else { 'restart' }
        $proc = if ($d['param1']) { [string]$d['param1'] } else { $m }
        [void]$requests.Add([pscustomobject]@{ time = $_.TimeCreated; action = $action; process = $proc })
        Add-Ev $_.TimeCreated "REQUEST-$($action.ToUpper() -replace ' ', '-')" $m
      } else {
        $kind = if ($m -match 'MoUsoCoreWorker|TrustedInstaller|wuauclt') { 'WU-REBOOT' }
                elseif ($m -match 'power off')                            { 'HOST-POWER-OFF' }
                else                                                      { 'RESTART-INITIATED' }
        Add-Ev $_.TimeCreated $kind $m
      }
    }
} catch {
  if ($_.Exception.Message -notmatch 'No events were found') {
    [void]$unver.Add("User32 1074 unreadable: $($_.Exception.Message)")
  }
}

# --- 3. Windows Update installs in the window --------------------------------
try {
  Get-WinEvent -FilterHashtable @{
      LogName='System'; ProviderName='Microsoft-Windows-WindowsUpdateClient'
      Id=@(19,43); StartTime=$start } -ErrorAction Stop |
    ForEach-Object { Add-Ev $_.TimeCreated 'WU-INSTALL' (($_.Message -split "`n")[0].Trim()) }
} catch {
  if ($_.Exception.Message -notmatch 'No events were found') {
    [void]$unver.Add("WindowsUpdateClient log unreadable: $($_.Exception.Message)")
  }
}

# --- 4. Power configuration, for the record (NOT a verdict on its own) --------
$pcfg = @{}
try {
  $q = powercfg /q SCHEME_CURRENT SUB_SLEEP 2>$null | Out-String
  if ($q -match '(?s)STANDBYIDLE.*?Current AC Power Setting Index: (0x[0-9a-f]+).*?Current DC Power Setting Index: (0x[0-9a-f]+)') {
    $pcfg['standbyidle_ac_secs'] = [Convert]::ToInt32($Matches[1], 16)
    $pcfg['standbyidle_dc_secs'] = [Convert]::ToInt32($Matches[2], 16)
  }
  $pcfg['modern_standby'] = ((powercfg /a 2>$null | Out-String) -match 'S0 Low Power Idle')
} catch { [void]$unver.Add("powercfg unreadable: $($_.Exception.Message)") }

# --- 5. When did the scheduler process actually come up? ----------------------
# "Reset" + "Renderer listener ready" + "Initialized" with no preceding giant
# event-loop-stall is a COLD START (new process). A large "[likely sleep:
# power_event]" stall followed by "System resumed" is a RESUME of a surviving
# process. The two are different failures and must not be conflated.
$logDir = Join-Path $env:APPDATA 'Claude\logs'
$coldStarts = New-Object System.Collections.ArrayList
$resumes    = New-Object System.Collections.ArrayList
try {
  # main-window.log is a different, frequently-locked stream -- exclude it, and
  # isolate each file so one lock cannot blank the whole scan (a zero that means
  # "couldn't look" is a failure, not a clean result).
  Get-ChildItem -Path $logDir -Filter 'main*.log' -ErrorAction Stop |
    Where-Object { $_.Name -match '^main\d*\.log$' } | ForEach-Object {
      try {
        # main.log is held open by the running app. [IO.File]::ReadLines opens
        # without a share mode and throws. Open explicitly with FileShare
        # ReadWrite+Delete, which is how Python reads the same file fine.
        $share = [System.IO.FileShare]([int][System.IO.FileShare]::ReadWrite -bor
                                       [int][System.IO.FileShare]::Delete)
        $fs = New-Object System.IO.FileStream($_.FullName, [System.IO.FileMode]::Open,
                                              [System.IO.FileAccess]::Read, $share)
        $sr = New-Object System.IO.StreamReader($fs)
        while ($null -ne ($line = $sr.ReadLine())) {
          if ($line -notmatch '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}') { continue }
          $t = [datetime]::ParseExact($line.Substring(0,19), 'yyyy-MM-dd HH:mm:ss', $null)
          if ($t -lt $start) { continue }
          if ($line -match '\[ScheduledTasks\] Initialized')      { [void]$coldStarts.Add($t) }
          elseif ($line -match 'System resumed; waking poll loop'){ [void]$resumes.Add($t) }
        }
      } catch { [void]$unver.Add("$($_.Exception.Message)") }
      finally { if ($sr) { $sr.Dispose() }; if ($fs) { $fs.Dispose() }; $sr=$null; $fs=$null }
    }
} catch { [void]$unver.Add("log directory unreadable: $($_.Exception.Message)") }

$notes = New-Object System.Collections.ArrayList
if ($libOk) {
  $dirty = New-Object System.Collections.ArrayList
  foreach ($t41 in $kp41) {
    $b = @($bootRecords | Where-Object { $_.time -le $t41 -and ($t41 - $_.time).TotalSeconds -le 120 }) | Select-Object -Last 1
    $cut = if ($b) { $b.time.AddSeconds(-1) } else { $t41.AddSeconds(-1) }
    $last = $null
    try {
      $last = (Get-WinEvent -FilterHashtable @{ LogName = 'System'; EndTime = $cut; StartTime = $cut.AddDays(-$AcLookbackDays) } -MaxEvents 1 -ErrorAction Stop).TimeCreated
    } catch {
      if ($_.Exception.Message -notmatch 'No events were found') {
        [void]$unver.Add("last event before Kernel-Power 41 at $t41 unreadable -- dirty-off start unknown: $($_.Exception.Message)")
      }
    }
    [void]$dirty.Add([pscustomobject]@{ time = $t41; lastSeen = $last })
  }
  $offPeriods = @(Resolve-HostOffPeriods -Requests $requests -Sleep42 $sleep42 -ShutdownMarkers $markers13 -Boots $bootRecords `
                    -DirtyOff $dirty -StandbyExitTimes @($msExits | ForEach-Object { $_.time }))
  foreach ($p in $offPeriods) {
    $line = Format-HostOffPeriod $p
    if ($p.confirmed) { [void]$findings.Add($line) } else { [void]$notes.Add($line) }
  }
} else {
  # Legacy path (lib unavailable): request-based, unconfirmed.
  foreach ($e in ($events | Sort-Object time)) {
    if ($e.kind -in @('WU-REBOOT','HOST-POWER-OFF')) {
      [void]$findings.Add("[CAUSE] $($e.kind) at $($e.time.ToString('yyyy-MM-dd HH:mm:ss')) :: $($e.detail) (UNCONFIRMED -- lib unavailable)")
    }
  }
}

$msEnter = ($events | Where-Object kind -eq 'MODERN-STANDBY-ENTER' | Measure-Object).Count
if ($msEnter -gt 0) {
  [void]$findings.Add("[CAUSE] MODERN-STANDBY x$msEnter enter event(s) in window -- " +
    "host was in S0 low-power idle. STANDBYIDLE=Never on AC does NOT prevent this; " +
    "do not read a clean STANDBYIDLE as evidence the host stayed awake.")
}
$standby = @()
$sleepPower = $null
if ($libOk) {
  $standby = @(Get-StandbyEntries -Enters $msEnters -Exits $msExits -AcEvents $acEvents -BootTimes $bootTimes -BootTimesUnknown:$bootUnknown -Now (Get-Date))
  foreach ($se in $standby) { [void]$findings.Add((Format-StandbyCause $se)) }
  $sleepPower = Get-SleepTimePowerSummary -Entries $standby -SlotTime $slot -AcEvents $acEvents `
                  -BootTimes $bootTimes -BootTimesUnknown:$bootUnknown
}
if ($coldStarts.Count -gt 0) {
  [void]$findings.Add("[CAUSE] SCHEDULER-COLD-START x$($coldStarts.Count) at " +
    (($coldStarts | Sort-Object | ForEach-Object { $_.ToString('MM-dd HH:mm:ss') }) -join ', ') +
    " -- a cold Initialized means the app process did not exist before that moment. " +
    "The scheduler cannot dispatch a slot that falls while the process is absent, " +
    "and Claude Desktop does not auto-start after a reboot.")
}

Write-Output ("WAKE-CAUSE PROBE window=${WindowHours}h  events=$($events.Count)  " +
  "cold_starts=$($coldStarts.Count)  resumes=$($resumes.Count)")
Write-Output ("POWERCFG standbyidle_ac=$($pcfg['standbyidle_ac_secs'])s " +
  "standbyidle_dc=$($pcfg['standbyidle_dc_secs'])s modern_standby=$($pcfg['modern_standby'])")
if ($sleepPower) {
  $et = if ($sleepPower.entryTime) { $sleepPower.entryTime.ToString('yyyy-MM-dd HH:mm:ss') } else { 'n/a' }
  Write-Output ("SLEEP-TIME-POWER state=$($sleepPower.state) cause=$($sleepPower.cause) entry=$et " +
    "slot=$(if ($slot) { $slot.ToString('yyyy-MM-dd HH:mm') } else { 'longest-session' }) " +
    "source=$($sleepPower.source) :: $($sleepPower.detail)")
} else {
  Write-Output "SLEEP-TIME-POWER state=UNKNOWN source=lib-unavailable"
}
if ($findings.Count -eq 0) { Write-Output "NO CAUSE FOUND in window -- gap is unexplained, escalate." }
foreach ($f in $findings) { Write-Output $f }
foreach ($n in $notes)    { Write-Output $n }
foreach ($u in $unver)    { Write-Output "[unverifiable] $u" }
foreach ($e in ($events | Sort-Object time)) {
  Write-Output ("  {0}  {1,-22} {2}" -f $e.time.ToString('yyyy-MM-dd HH:mm:ss'), $e.kind,
                $e.detail.Substring(0, [Math]::Min(96, $e.detail.Length)))
}

if ($JsonOut) {
  try {
    [pscustomobject]@{
      ts           = (Get-Date).ToUniversalTime().ToString('o')
      windowHours  = $WindowHours
      powercfg     = $pcfg
      slotTime     = $(if ($slot) { $slot.ToString('o') } else { $null })
      sleepTimePower = $(if ($sleepPower) {
                          [pscustomobject]@{ state = $sleepPower.state; source = $sleepPower.source
                            cause = $sleepPower.cause
                            entryTime = $(if ($sleepPower.entryTime) { $sleepPower.entryTime.ToString('o') } else { $null })
                            lidOpen = $sleepPower.lidOpen; reason = $sleepPower.reason
                            reasonName = $sleepPower.reasonName; detail = $sleepPower.detail }
                        } else { [pscustomobject]@{ state = 'UNKNOWN'; source = 'lib-unavailable' } })
      standbyEntries = @($standby | ForEach-Object {
                          [pscustomobject]@{ time = $_.time.ToString('o'); cause = $_.cause
                            reason = $_.reason; reasonName = $_.reasonName; lidOpen = $_.lidOpen
                            extMonitor = $_.extMonitor; battRemain = $_.battRemain; battFull = $_.battFull
                            powerState = $_.power.state; powerSource = $_.power.source
                            powerDetail = $_.power.detail
                            sessionEnd = $(if ($_.sessionEnd) { $_.sessionEnd.ToString('o') } else { $null })
                            durationMin = $_.durationMin } })
      hostOffPeriods = @($offPeriods | ForEach-Object {
                          [pscustomobject]@{ kind = $_.kind; confirmed = $_.confirmed; mode = $_.mode
                            start = $_.start.ToString('o')
                            downAt = $(if ($_.downAt) { $_.downAt.ToString('o') } else { $null })
                            end = $(if ($_.end) { $_.end.ToString('o') } else { $null })
                            bootType = $_.bootType; confirmedBy = $_.confirmedBy; process = $_.process } })
      notes        = @($notes)
      coldStarts   = @($coldStarts | Sort-Object | ForEach-Object { $_.ToString('o') })
      resumes      = @($resumes    | Sort-Object | ForEach-Object { $_.ToString('o') })
      findings     = @($findings)
      unverifiable = @($unver)
      events       = @($events | Sort-Object time | ForEach-Object {
                        [pscustomobject]@{ time = $_.time.ToString('o')
                                           kind = $_.kind; detail = $_.detail } })
    } | ConvertTo-Json -Depth 6 | Set-Content -Path $JsonOut -Encoding UTF8
  } catch {
    Write-Output "[unverifiable] JsonOut write failed: $($_.Exception.Message)"
    exit 2
  }
}

if ($unver.Count -gt 0 -and $events.Count -eq 0) { exit 2 }
if ($findings.Count -gt 0) { exit 1 }
exit 0
