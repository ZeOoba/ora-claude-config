<#
.SYNOPSIS
  Register the "ORA Fleet Pause-Resume Guard" Windows scheduled task (WO-5,
  2026-08-21 repo-architecture-review).

.DESCRIPTION
  Runs maintenance/pause-resume-guard.py every 6 hours, natively via Windows
  Task Scheduler -- so it keeps checking even during a full CC/MCP or LAMS
  fleet pause, which is exactly the scenario it exists to catch (a paused
  fleet whose resume silently failed, per the live OI-202 incident 2026-08-21:
  a resume task fired but only re-enabled 2 of 35 tasks, with no error and no
  email, caught only by a human happening to check).

  Deliberately native-only -- see pause-resume-guard.py's own module
  docstring for why this doesn't need a Notion beacon / GitHub Actions layer
  (that combination was designed for OI-197's fix (a) and explicitly deferred
  there too, same day CRON_SECRET was rotated -- not compounding a second
  rushed secret decision).

  Run this ONCE (not invoked automatically). Re-running updates the existing
  task.

.EXAMPLE
  pwsh -File maintenance/register-pause-resume-guard-task.ps1
#>
[CmdletBinding()]
param(
  [string]$TaskName = 'ORA Fleet Pause-Resume Guard',
  [string]$PythonExe = 'C:\Users\Owner\AppData\Local\Programs\Python\Python313\python.exe'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$script = Join-Path $repo 'maintenance\pause-resume-guard.py'

$action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$script`"" -WorkingDirectory $repo
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

# Every 6 hours, offset from the hourly mirror-deploy cadence and the 4h-cycle
# GitHub Actions watchdogs so nothing collides by coincidence.
$trigger = New-ScheduledTaskTrigger -Once -At 2:20am -RepetitionInterval (New-TimeSpan -Hours 6) -RepetitionDuration (New-TimeSpan -Days 3650)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force -Description 'Fleet pause/resume guard (WO-5, OI-202) -- alarms if a fleet is near-zero enabled with an overdue/missing resume. Native, off-fleet, survives a full fleet pause. See open-items-tracker.md#OI-202.'
Write-Host "Registered '$TaskName': every 6h -> $script"
