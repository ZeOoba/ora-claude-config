<#
  register-task.ps1 - registers (or refreshes) the "ClaudeFleetMirror" Windows scheduled
  task that runs write-fleet.ps1 every 60 seconds via the hidden VBS shim.
  Runs only while the current user is logged on (no stored credentials, no admin needed).

  To remove later:  Unregister-ScheduledTask -TaskName 'ClaudeFleetMirror' -Confirm:$false
#>
$ErrorActionPreference = 'Stop'
$TaskName = 'ClaudeFleetMirror'
$vbs      = 'C:\Users\Owner\.claude\obsidian-fleet-mirror\run-hidden.vbs'

$action   = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument ('"{0}"' -f $vbs)
$trigger  = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 1)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
              -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal -UserId ('{0}\{1}' -f $env:USERDOMAIN, $env:USERNAME) `
              -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
  -Principal $principal -Description 'Mirror Claude scheduled-task fleet into Obsidian BrainVault every 60s.' -Force | Out-Null

Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 3

$t = Get-ScheduledTask -TaskName $TaskName
$i = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Output ('TaskName      : {0}' -f $t.TaskName)
Write-Output ('State         : {0}' -f $t.State)
Write-Output ('LastRunTime   : {0}' -f $i.LastRunTime)
Write-Output ('LastTaskResult: 0x{0:X8}' -f $i.LastTaskResult)
Write-Output ('NextRunTime   : {0}' -f $i.NextRunTime)
