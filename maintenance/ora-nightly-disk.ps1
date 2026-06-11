# ORA Nightly Disk Clean -- scheduled maintenance (safe regardless of desktop GUI state).
# Always: npm content cache (_cacache). If the Claude desktop GUI is NOT running, also
# deletes non-core _npx CLI dirs while PRESERVING the Outlook/mcp-remote bridge.
# Never quits the GUI (would break overnight scheduled tasks). Logs to a sibling .log.

$ErrorActionPreference = 'SilentlyContinue'
$log = Join-Path $env:USERPROFILE '.claude\maintenance\ora-nightly-disk.log'
function Log($m) { ("{0}  {1}" -f ([DateTime]::Now.ToString('yyyy-MM-dd HH:mm:ss')), $m) | Add-Content -Path $log }
function DirMB($p) { if (Test-Path $p) { [math]::Round(((Get-ChildItem $p -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum) / 1MB, 0) } else { 0 } }

$cacache = Join-Path $env:LOCALAPPDATA 'npm-cache\_cacache'
$npx     = Join-Path $env:LOCALAPPDATA 'npm-cache\_npx'
$before  = (DirMB $cacache) + (DirMB $npx)
Log "START  (cacache+npx = $before MB)"

# 1) npm content cache -- always safe, npm regenerates
if (Get-Command npm -ErrorAction SilentlyContinue) { npm cache clean --force *> $null; Log "npm cache clean --force done" }

# 2) _npx non-core dirs -- only when GUI is down so live MCP bridges aren't held
if (Get-Process -Name Claude -ErrorAction SilentlyContinue) {
  Log "Claude GUI running -> skipped _npx cleanup (safe partial run)"
}
else {
  $preserve = 'mcp-remote', 'composio', 'excel-mcp', 'context7'
  if (Test-Path $npx) {
    Get-ChildItem $npx -Directory -ErrorAction SilentlyContinue | ForEach-Object {
      $nm = Join-Path $_.FullName 'node_modules'; $keep = $false
      if (Test-Path $nm) { foreach ($k in $preserve) { if (Get-ChildItem $nm -Directory -Filter "*$k*" -ErrorAction SilentlyContinue) { $keep = $true; break } } }
      if (-not $keep) { Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue; Log "deleted _npx\$($_.Name)" }
    }
  }
  Log "Claude GUI down -> _npx non-core cleanup done (Outlook bridge preserved)"
}

$after = (DirMB $cacache) + (DirMB $npx)
Log "DONE   reclaimed ~$($before - $after) MB ($before -> $after MB)"

# 3) send-log.txt rotation -- keep last 500 lines; MUST preserve LastWriteTime.
#    fleet-deadman.ps1 reads send-log's LastWriteTime as the send-liveness proxy (>30h = alert);
#    a naive rewrite would reset mtime and FALSELY clear a real stale-send alert. Only acts above cap.
$sendLog = Join-Path $env:USERPROFILE '.claude\scheduled-tasks\_shared\send-log.txt'
if (Test-Path $sendLog) {
  $lines = @(Get-Content -LiteralPath $sendLog)
  if ($lines.Count -gt 500) {
    $orig = (Get-Item $sendLog).LastWriteTime
    $lines | Select-Object -Last 500 | Set-Content -LiteralPath $sendLog -Encoding UTF8
    (Get-Item $sendLog).LastWriteTime = $orig
    Log "send-log.txt trimmed $($lines.Count) -> 500 lines (mtime preserved)"
  }
}

# 4) hooks/sessions/ prune -- delete EOS marker dirs not modified in 30+ days.
#    A 30-day age gate can never select a live session (its dir is touched within seconds of now).
$sessDir = Join-Path $env:USERPROFILE '.claude\hooks\sessions'
if (Test-Path $sessDir) {
  $cut = (Get-Date).AddDays(-30); $pruned = 0
  Get-ChildItem -LiteralPath $sessDir -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -lt $cut } |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue; $pruned++ }
  if ($pruned -gt 0) { Log "hooks/sessions pruned $pruned dir(s) older than 30d" }
}
