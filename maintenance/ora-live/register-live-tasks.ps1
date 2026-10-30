$me = "$env:USERDOMAIN\$env:USERNAME"
foreach ($role in 'server','web') {
  $name = "ORA-LiveCC-$role"
  $act = New-ScheduledTaskAction -Execute 'conhost.exe' -Argument "--headless powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\run-live.ps1`" -Role $role"
  $trg = New-ScheduledTaskTrigger -AtLogOn -User $me
  # Self-heal: re-fire every 5 min; IgnoreNew makes it a no-op while the supervisor lives, and a dead supervisor adopts the healthy child.
  $rep = (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)).Repetition
  $trg.Repetition = $rep
  $set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
  $pri = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
  Register-ScheduledTask -TaskName $name -Action $act -Trigger $trg -Settings $set -Principal $pri -Force | Out-Null
  "registered $name"
}
