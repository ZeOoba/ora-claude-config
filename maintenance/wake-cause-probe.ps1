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
      Id = @(42, 107, 109, 506, 507, 577, 578)
      StartTime = $start
    } -ErrorAction Stop | ForEach-Object {
      $k = switch ($_.Id) {
        42  { 'SLEEP-ENTER' }      107 { 'SLEEP-EXIT' }
        506 { 'MODERN-STANDBY-ENTER' } 507 { 'MODERN-STANDBY-EXIT' }
        109 { 'SHUTDOWN-TRANSITION' }
        577 { 'REBOOT-PREPARED' }  578 { 'REBOOT-DETECTED' }
      }
      Add-Ev $_.TimeCreated $k ($_.Message -split "`n")[0].Trim()
      if ($libOk -and $_.Id -in @(506, 507)) {
        try {
          $rec = [pscustomobject]@{ time = $_.TimeCreated; data = (ConvertFrom-KpEventData $_.ToXml()) }
          if ($_.Id -eq 506) { [void]$msEnters.Add($rec) } else { [void]$msExits.Add($rec) }
        } catch { [void]$unver.Add("Kernel-Power $($_.Id) EventData unparseable at $($_.TimeCreated): $($_.Exception.Message)") }
      }
    }
} catch {
  [void]$unver.Add("Kernel-Power log unreadable: $($_.Exception.Message)")
}

# --- 1b. Power-source changes (Kernel-Power 105 AcOnline), longer lookback -----
# Plus OS starts (Kernel-General 12): a 105 is only valid within its own boot.
$bootTimes = New-Object System.Collections.ArrayList
$bootUnknown = $false
if ($libOk) {
  try {
    Get-WinEvent -FilterHashtable @{
        LogName = 'System'; ProviderName = 'Microsoft-Windows-Kernel-General'
        Id = 12; StartTime = $start.AddDays(-$AcLookbackDays)
      } -ErrorAction Stop | ForEach-Object { [void]$bootTimes.Add($_.TimeCreated) }
  } catch {
    if ($_.Exception.Message -notmatch 'No events were found') {
      $bootUnknown = $true
      [void]$unver.Add("Kernel-General 12 unreadable -- 105 unused (cannot prove same boot): $($_.Exception.Message)")
    }
  }
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
  Get-WinEvent -FilterHashtable @{ LogName='System'; Id=1074; StartTime=$start } -ErrorAction Stop |
    ForEach-Object {
      $m = ($_.Message -split "`n")[0].Trim()
      $kind = if ($m -match 'MoUsoCoreWorker|TrustedInstaller|wuauclt') { 'WU-REBOOT' }
              elseif ($m -match 'power off')                            { 'HOST-POWER-OFF' }
              else                                                      { 'RESTART-INITIATED' }
      Add-Ev $_.TimeCreated $kind $m
    }
} catch { [void]$unver.Add("User32 1074 unreadable: $($_.Exception.Message)") }

# --- 3. Windows Update installs in the window --------------------------------
try {
  Get-WinEvent -FilterHashtable @{
      LogName='System'; ProviderName='Microsoft-Windows-WindowsUpdateClient'
      Id=@(19,43); StartTime=$start } -ErrorAction Stop |
    ForEach-Object { Add-Ev $_.TimeCreated 'WU-INSTALL' (($_.Message -split "`n")[0].Trim()) }
} catch { [void]$unver.Add("WindowsUpdateClient log unreadable: $($_.Exception.Message)") }

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

foreach ($e in ($events | Sort-Object time)) {
  if ($e.kind -in @('WU-REBOOT','HOST-POWER-OFF')) {
    [void]$findings.Add("[CAUSE] $($e.kind) at $($e.time.ToString('yyyy-MM-dd HH:mm:ss')) :: $($e.detail)")
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
