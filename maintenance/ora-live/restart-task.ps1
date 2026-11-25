# Restart one live task cleanly: kill the old supervisor AND its node children (Stop-ScheduledTask can orphan the
# supervisor, and killing only the supervisor orphans the child), kill any orphaned live child left by an earlier
# supervisor, confirm the old instance has stopped answering, then start the task.
#
# Why not by port: Get-NetTCPConnection / netstat on this machine list connections on 8911/5273 but not the
# listening socket, so a port-owner kill silently matched nothing and the fresh supervisor "adopted" the old,
# still-healthy process (2026-11-03: a merge was restarted for and kept serving the previous day's code).
# Live children are matched by run-live.ps1's exact launch arguments instead -- npm dev scripts and other
# worktrees' servers use different argument forms (`tsx server/index.ts`, `vite` with no `preview`).
param([Parameter(Mandatory)][ValidateSet('server','web')][string]$Role)
$ErrorActionPreference = 'Stop'
$url = if ($Role -eq 'web') { 'http://127.0.0.1:5273/' } else { 'http://127.0.0.1:8911/api/snapshot' }
# Must stay in step with $args2 in run-live.ps1.
$childArgs = if ($Role -eq 'web') { '*node_modules/vite/bin/vite.js preview --config vite.live.config.ts --host 127.0.0.1 --port 5273 --strictPort*' }
             else { '*node_modules\tsx\dist\cli.mjs server\index.ts*' }
function Healthy { try { (Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200 } catch { $false } }
# Local 'Continue': under Windows PowerShell 5.1 a native command's redirected stderr is a terminating error when
# the preference is 'Stop', and taskkill writes to stderr for a PID already taken down by an earlier tree kill.
function Kill-Tree([int]$id) { $ErrorActionPreference = 'Continue'; & taskkill.exe /PID $id /T /F 2>&1 | Out-Null }

Stop-ScheduledTask "ORA-LiveCC-$Role" -ErrorAction SilentlyContinue
$procs = @(Get-CimInstance Win32_Process)
$supervisors = @($procs | Where-Object { $_.ProcessId -ne $PID -and $_.Name -match 'powershell|conhost' -and $_.CommandLine -like "*run-live.ps1*-Role $Role*" })
$children = @($procs | Where-Object { $_.Name -eq 'node.exe' -and $_.CommandLine -like $childArgs })
# taskkill /T takes the whole tree (supervisor -> node -> tsx child); the explicit child pass catches orphans.
foreach ($p in $supervisors + $children) { Kill-Tree $p.ProcessId }
Write-Host "stopped $($supervisors.Count) supervisor(s), $($children.Count) live $Role process(es): $((@($children | ForEach-Object ProcessId)) -join ', ')"

# The old instance must be gone before the task starts, or the new supervisor adopts it.
$deadline = (Get-Date).AddSeconds(20)
while ((Healthy) -and (Get-Date) -lt $deadline) { Start-Sleep 2 }
if (Healthy) {
  throw "$url still answers after stopping every known live $Role process -- something else is serving it. Not starting ORA-LiveCC-$Role (it would adopt that instance)."
}
Start-ScheduledTask "ORA-LiveCC-$Role"
Write-Host "started ORA-LiveCC-$Role"
