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

Exit: 0 = no unexplained gap   1 = cause identified (report it)   2 = could not look
#>
param(
  [double]$WindowHours = 24,
  [string]$JsonOut
)

$ErrorActionPreference = 'Continue'
$start = (Get-Date).AddHours(-$WindowHours)
$findings = New-Object System.Collections.ArrayList
$events   = New-Object System.Collections.ArrayList
$unver    = New-Object System.Collections.ArrayList

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
    }
} catch {
  [void]$unver.Add("Kernel-Power log unreadable: $($_.Exception.Message)")
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
