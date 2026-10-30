# Supervisor for the live Command Center. Usage: run-live.ps1 -Role server|web
# Restarts the child on exit OR when it stops answering (tsx sometimes hangs before binding — see package.json devServerNote).
# Loopback binds only; Tailscale Serve provides tailnet access.
param([Parameter(Mandatory)][ValidateSet('server','web')][string]$Role)
# Single instance per role (the headless launcher exits immediately, so Task Scheduler's IgnoreNew can't dedupe).
$mutex = New-Object System.Threading.Mutex($false, "Global\ORA-LiveCC-$Role")
if (-not $mutex.WaitOne(0)) { exit 0 }
$wt = 'C:\Users\Owner\oxford-command-center\.claude\worktrees\main-live'
$log = Join-Path $PSScriptRoot "$Role.log"
$ts = 'C:\Program Files\Tailscale\tailscale.exe'
$url = if ($Role -eq 'web') { 'http://127.0.0.1:5273/' } else { 'http://127.0.0.1:8911/api/snapshot' }
$bootSec = if ($Role -eq 'web') { 90 } else { 900 }
Set-Location $wt
$env:BRAIN_ALLOWED_HOSTS = '<TAILNET_HOST>'
$node = (Get-Command node -ErrorAction SilentlyContinue).Source
if (-not $node) { $node = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_*\node-*\node.exe" | Select-Object -First 1).FullName }
function Log($m) { "[$(Get-Date -Format s)] $m" | Add-Content $log }
function Healthy { try { (Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 8).StatusCode -eq 200 } catch { $false } }
while ($true) {
  if ((Get-Item $log -ErrorAction SilentlyContinue).Length -gt 5MB) { Move-Item $log "$log.old" -Force }
  if (Healthy) {
    Log "$Role already healthy; adopting running instance"
    $bad = 0
    while ($bad -lt 4) { Start-Sleep 15; if (Healthy) { $bad = 0 } else { $bad++ } }
    Log "$Role adopted instance unhealthy 4x; restarting"
  }
  # Clear any stale listener left by a previous supervisor/child.
  $port = if ($Role -eq 'web') { 5273 } else { 8911 }
  Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
  if ($Role -eq 'web') {
    # Isolated console: tailscale's CLI must not share (and signal) the supervisor's console.
    Start-Process $ts -ArgumentList 'serve','--bg','--https=443','http://127.0.0.1:5273' -WindowStyle Hidden -Wait -RedirectStandardOutput "$log.ts" | Out-Null
    $args2 = @('node_modules/vite/bin/vite.js','preview','--config','vite.live.config.ts','--host','127.0.0.1','--port','5273','--strictPort')
  } else {
    $args2 = @('node_modules\tsx\dist\cli.mjs','server\index.ts')
  }
  $p = Start-Process $node -ArgumentList $args2 -WorkingDirectory $wt -WindowStyle Hidden -PassThru -RedirectStandardOutput "$log.out" -RedirectStandardError "$log.err"
  Log "started $Role pid $($p.Id)"
  $t0 = Get-Date; $up = $false; $bad = 0
  while (-not $p.HasExited) {
    Start-Sleep 15
    if (Healthy) { if (-not $up) { Log "$Role healthy after $([int]((Get-Date)-$t0).TotalSeconds)s" }; $up = $true; $bad = 0 }
    elseif ($up) { $bad++; if ($bad -ge 4) { Log "$Role unhealthy 4x; killing"; break } }
    elseif (((Get-Date)-$t0).TotalSeconds -gt $bootSec) { Log "$Role never became healthy in ${bootSec}s (startup hang); killing"; break }
  }
  Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
  Log "$Role exited; restarting in 5s"
  Start-Sleep 5
}
