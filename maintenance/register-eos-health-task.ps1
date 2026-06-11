# Registers the "ORA EOS Health" weekly scheduled task that runs eos-health-report.ps1.
# Weekly Monday 05:30 local (= 05:30 ET on this host), just after the daily Health Guard (05:15).
# Interactive/Limited principal: runs while the current user is logged on; no elevation, no app-closed needed.
# Re-runnable (-Force overwrites). Outlook desktop must be running at fire time for the COM send.

$here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $here 'eos-health-report.ps1'

$action  = New-ScheduledTaskAction -Execute 'powershell.exe' `
  -Argument ('-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $script)
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At '5:30AM'
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
  -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -MultipleInstances IgnoreNew

try {
  Register-ScheduledTask -TaskName 'ORA EOS Health' -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force -ErrorAction Stop `
    -Description 'Weekly Mon 05:30 ET Engineering-OS health: doctrine-integrity drift probe + lane-compliance telemetry rollup, emailed to ggoldberg+egoldberg via Outlook COM. Scripts in ~/.claude/maintenance/ (eos-health-report.ps1).' | Out-Null
  Write-Output 'OK: registered task "ORA EOS Health"'
} catch {
  Write-Output ('FAILED: ' + $_.Exception.Message)
  exit 1
}
