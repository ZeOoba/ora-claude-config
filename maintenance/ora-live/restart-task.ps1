# Restart one live task cleanly: kill the old supervisor explicitly (Stop-ScheduledTask can orphan it, and an
# orphan holds the single-instance mutex while its health probe silently fails), free the port, start the task.
param([Parameter(Mandatory)][ValidateSet('server','web')][string]$Role)
$port = if ($Role -eq 'web') { 5273 } else { 8911 }
Stop-ScheduledTask "ORA-LiveCC-$Role" -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.Name -match 'powershell|conhost' -and $_.CommandLine -like "*run-live.ps1*-Role $Role*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep 2
Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Start-Sleep 3
Start-ScheduledTask "ORA-LiveCC-$Role"
