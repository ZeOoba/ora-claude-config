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
# Required since oxford-command-center #560/#562: the tailnet ACL (Tailscale Serve) is the auth boundary, not Cloudflare Access.
$env:BRAIN_HOST_AUTH = 'tailnet'
# Required since oxford-command-center #(RCT runtime config, 2026-11-13): the acquisition engine verifies the private
# replacement-cost table against RCT_PIN_KEY and fails closed (503, no BUY) without it. main-live has no .env, so
# pass ONLY this key from the canonical checkout's .env; the secret stays in that file, never in this script.
$canonEnv = 'C:\Users\Owner\oxford-command-center\.env'
if (Test-Path $canonEnv) {
  $pinLine = Get-Content $canonEnv | Where-Object { $_ -match '^RCT_PIN_KEY=' } | Select-Object -First 1
  if ($pinLine) { $env:RCT_PIN_KEY = ($pinLine -replace '^RCT_PIN_KEY=', '').Trim().Trim('"') }
}
$node = (Get-Command node -ErrorAction SilentlyContinue).Source
if (-not $node) { $node = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_*\node-*\node.exe" | Select-Object -First 1).FullName }
function Log($m) { "[$(Get-Date -Format s)] $m" | Add-Content $log }
# Each check runs in a fresh curl.exe process. 2026-11-12..18: the in-process Invoke-WebRequest check stopped succeeding
# after the first pass in a long-lived supervisor and killed a healthy server every 900s (406 "startup hang" kills).
$curl = Join-Path $env:SystemRoot 'System32\curl.exe'
$script:lastCode = ''
function Healthy {
  if (Test-Path $curl) {
    $script:lastCode = try { "$(& $curl -s -o NUL -w '%{http_code}' --max-time 8 $url 2>$null)" } catch { 'err' }
    return $script:lastCode -eq '200'
  }
  try { $r = Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 8 -DisableKeepAlive; $script:lastCode = "$($r.StatusCode)"; $r.StatusCode -eq 200 } catch { $script:lastCode = 'err'; $false }
}
while ($true) {
  if ((Get-Item $log -ErrorAction SilentlyContinue).Length -gt 5MB) { Move-Item $log "$log.old" -Force }
  if (Healthy) {
    Log "$Role already healthy; adopting running instance"
    $bad = 0
    while ($bad -lt 4) { Start-Sleep 15; if (Healthy) { $bad = 0 } else { $bad++ } }
    Log "$Role adopted instance unhealthy 4x (last http=$script:lastCode); restarting"
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
    elseif ($up) { $bad++; if ($bad -ge 4) { Log "$Role unhealthy 4x (last http=$script:lastCode); killing"; break } }
    elseif (((Get-Date)-$t0).TotalSeconds -gt $bootSec) { Log "$Role never became healthy in ${bootSec}s (last http=$script:lastCode; startup hang); killing"; break }
  }
  Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
  Log "$Role exited; restarting in 5s"
  Start-Sleep 5
}
