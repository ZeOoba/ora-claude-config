# Pull origin/main into the main-live worktree, rebuild the production bundle, restart the web task.
#   rebuild-live.ps1                 update + rebuild only if origin/main moved
#   rebuild-live.ps1 -ForceBuild     rebuild even if nothing moved
#   rebuild-live.ps1 -RestartServer  also restart the API server (slow: ~2-8 min until healthy)
# Server-side changes (server/, src/contracts, config, package*.json) need -RestartServer to take effect;
# the script tells you when that is the case. Dependency changes are NOT installed (node_modules is a
# shared junction) - the script stops and tells you.
param([switch]$ForceBuild, [switch]$RestartServer)
$ErrorActionPreference = 'Stop'
$wt = 'C:\Users\Owner\oxford-command-center\.claude\worktrees\main-live'
$here = $PSScriptRoot
$node = (Get-Command node -ErrorAction SilentlyContinue).Source
if (-not $node) { $node = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_*\node-*\node.exe" | Select-Object -First 1).FullName }
function Invoke-Git { & git -C $wt @args; if ($LASTEXITCODE -ne 0) { throw "git $($args -join ' ') failed ($LASTEXITCODE)" } }
function Get-GitOut { $o = & git -C $wt @args; if ($LASTEXITCODE -ne 0) { throw "git $($args -join ' ') failed ($LASTEXITCODE)" }; $o }

Invoke-Git fetch -q origin
$old = (Get-GitOut rev-parse HEAD).Trim()
$new = (Get-GitOut rev-parse origin/main).Trim()
$moved = $old -ne $new
Write-Host "main-live: $($old.Substring(0,8)) -> origin/main $($new.Substring(0,8))$(if (-not $moved) { ' (up to date)' })"
if (-not $moved -and -not $ForceBuild) { Write-Host 'Nothing to do. Use -ForceBuild to rebuild anyway.'; exit 0 }

$changed = @()
if ($moved) {
  $changed = @(Get-GitOut diff --name-only $old $new)
  if ($changed | Where-Object { $_ -match '^(package(-lock)?\.json)$' }) {
    throw 'package.json / package-lock.json changed upstream. node_modules is a shared junction - install deps deliberately, then re-run with -ForceBuild.'
  }
  # Tracked files the live server rewrites (e.g. data/snapshots/portfolio.json) would block the checkout.
  # Park them on a throwaway branch, same as the manual procedure.
  $dirty = @(Get-GitOut status --porcelain --untracked-files=no | ForEach-Object { $_.Substring(3).Trim() })
  if ($dirty.Count) {
    $branch = "wip/main-live-drift-$(Get-Date -Format yyyyMMdd-HHmmss)"
    Write-Host "Parking drift on $branch : $($dirty -join ', ')"
    Invoke-Git checkout -q -b $branch
    Invoke-Git add -- @dirty
    Invoke-Git commit -q -m 'wip: main-live drift backup (rebuild-live.ps1)' -m 'Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>'
  }
  Invoke-Git checkout -q --detach origin/main
}

# Build to a side directory so a failed build never leaves the served dist half-written.
$side = Join-Path $here 'dist-next'
Push-Location $wt
try {
  Write-Host 'Building...'
  & $node node_modules/vite/bin/vite.js build --config vite.live.config.ts --outDir $side --emptyOutDir 2>&1 | Select-Object -Last 6
  if ($LASTEXITCODE -ne 0 -or -not (Test-Path (Join-Path $side 'index.html'))) { throw 'Build failed - served dist left untouched.' }
} finally { Pop-Location }

$dist = Join-Path $wt 'dist'
robocopy $side $dist /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($LASTEXITCODE)" }
Write-Host 'dist updated. Restarting web...'
& "$here\restart-web.ps1"

$serverChanged = @($changed | Where-Object { $_ -match '^(server/|src/contracts/|config/|\.env|package)' })
if ($RestartServer) {
  Write-Host 'Restarting server (takes a few minutes to become healthy)...'
  & "$here/restart-task.ps1" -Role server
} elseif ($serverChanged.Count) {
  Write-Warning "Server-side files changed ($($serverChanged.Count)); the API is still running old code. Re-run with -RestartServer to apply."
}
Write-Host "Done. https://<TAILNET_HOST>"
