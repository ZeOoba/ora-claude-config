# membership-guard.ps1 v1.0 (2026-06-10) — registry-MEMBERSHIP snapshot/diff across BOTH fleets.
# Closes cross-audit gap B-prime: integrity guard protects FILES, watchdog detects TOTAL outage,
# but nothing detected silent disappearance/disable of individual registry entries
# (the 2026-06-09 rebuild failure mode that left ora-cowork-heartbeat dark 10 days).
# One-time tasks (fireAt) EXCLUDED — they auto-disable by design (false-positive trap).
# Output: single-line JSON {ts,first_run,stores,enabled_total,disappeared,disabled,added,parse_miss,snapshot_suppressed}.
$ErrorActionPreference = 'SilentlyContinue'
# LAMS roots come from the shared config (single source of truth 2026-07-09, same file
# the python probes read via _shared/store_discovery.py); the literals are the fail-open
# fallback. The extra $env:USERPROFILE\.claude root is this engine's own sweep, kept as-is.
$roots = @(
  "$env:USERPROFILE\AppData\Roaming\Claude\local-agent-mode-sessions",
  "$env:LOCALAPPDATA\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\local-agent-mode-sessions",
  "$env:USERPROFILE\.claude"
)
try {
  $storeCfg = Get-Content -LiteralPath "$env:USERPROFILE\.claude\maintenance\_shared\scheduler-stores.json" -Raw -ErrorAction Stop | ConvertFrom-Json
  if ($storeCfg.storeRoots) {
    $roots = @($storeCfg.storeRoots | ForEach-Object {
      Join-Path ([Environment]::ExpandEnvironmentVariables($_)) 'local-agent-mode-sessions'
    }) + @("$env:USERPROFILE\.claude")
  }
} catch {}
$stateFile = "$env:USERPROFILE\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\_state-history\membership-state.json"
$now = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$current = @{}; $stores = @(); $parseMiss = @(); $files = @(); $seen = @{}; $liveLamsOk = $false
foreach ($r in $roots) {
  if (Test-Path $r) {
    $files += Get-ChildItem -Path $r -Filter 'scheduled-tasks.json' -Recurse -File -ErrorAction SilentlyContinue
  }
}
foreach ($f in $files) {
  $hash = (Get-FileHash $f.FullName -Algorithm SHA256).Hash
  if ($seen.ContainsKey($hash)) { continue }
  $seen[$hash] = $true; $stores += $f.FullName
  try {
    $j = Get-Content $f.FullName -Raw | ConvertFrom-Json
    $tasks = @()
    if ($j.scheduledTasks) { $tasks = @($j.scheduledTasks) }
    elseif ($j.tasks) { $tasks = @($j.tasks) }
    elseif ($j -is [array]) { $tasks = @($j) }
    $got = 0
    foreach ($t in $tasks) {
      $id = $t.id; if (-not $id) { $id = $t.taskId }
      if (-not $id) { continue }
      $got++
      if ($t.PSObject.Properties['fireAt'] -and $t.fireAt) { continue }  # one-time: skip
      $en = $true
      if ($t.PSObject.Properties['enabled']) { $en = [bool]$t.enabled }
      if (-not $current.ContainsKey($id) -or $en) { $current[$id] = $en }
    }
    if ($got -eq 0) { $parseMiss += $f.FullName } else { $liveLamsOk = $true }
  } catch { $parseMiss += $f.FullName }
}
# Fold in the LAMS-fleet daily snapshot (produced by automation-health-monitor Step 0).
# The main-fleet registry is internal to the Desktop runtime (not a discoverable scheduled-tasks.json);
# the monitor's _state-history snapshot is its authoritative daily export. Staleness is reported.
# FILENAME FIX (2026-07-15): this used to match the bare 'YYYY-MM-DD.json' name, which
# ora-task-integrity-guard's OWN Step 0.5 also wrote to (CC/MCP-fleet data) -- whichever
# producer ran later in the day clobbered the other, so this fold-in sometimes silently
# read CC/MCP data back into itself instead of the intended LAMS baseline. Fixed: match
# the LAMS-specific '.lams.json' suffix only; automation-health-monitor's Step 0.5 CC/MCP
# snapshot is now written to '.cc.json' and is intentionally excluded from this fold-in.
# STICKY-TRUE FIX (2026-07-16): the fold-in used to unconditionally trust this once-daily
# snapshot's 'true' over the live direct scan above, even when the live scan is fresher and
# already determined an id is genuinely gone -- reproduced same-day when a LAMS task was
# retired AFTER automation-health-monitor's ~11:05 ET capture: every run that day kept
# resurrecting the retired id as enabled:true, which would have alarmed the NEXT day as a
# false "disappeared" once a correct fresh snapshot landed and diffed against the wrongly-
# true persisted baseline. Fix: when the live direct scan above found at least one
# successfully-parsed store ($liveLamsOk), treat it as closed-world for this run and skip
# the snapshot fold-in's mutation entirely -- it only still contributes to $stores/staleness
# reporting. The snapshot only gets to mutate $current as a genuine fallback when the live
# scan found nothing usable this run. See event_log.md 2026-07-16 for the full incident.
$snapDir = "$env:USERPROFILE\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\_state-history"
$mcpSnapshotStaleDays = $null
$snapshotSuppressed = $false
$snap = Get-ChildItem -Path $snapDir -Filter '20*-*.lams.json' -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^\d{4}-\d{2}-\d{2}\.lams\.json$' } |
        Sort-Object Name -Descending | Select-Object -First 1
if ($snap) {
  $mcpSnapshotStaleDays = [math]::Round(((Get-Date) - $snap.LastWriteTime).TotalDays, 1)
  try {
    $s = Get-Content $snap.FullName -Raw | ConvertFrom-Json
    if ($s.tasks) {
      $stores += ("mcp-fleet-snapshot:" + $snap.Name)
      if ($liveLamsOk) {
        $snapshotSuppressed = $true
      } else {
        foreach ($t in @($s.tasks)) {
          $id = $t.taskId; if (-not $id) { $id = $t.id }
          if (-not $id) { continue }
          $en = $true; if ($t.PSObject.Properties['enabled']) { $en = [bool]$t.enabled }
          if (-not $current.ContainsKey($id) -or $en) { $current[$id] = $en }
        }
      }
    }
  } catch { $parseMiss += $snap.FullName }
}
$prev = @{}; $firstRun = $true
if (Test-Path $stateFile) {
  try {
    $p = Get-Content $stateFile -Raw | ConvertFrom-Json
    if ($p.enabled) {
      $firstRun = $false
      foreach ($prop in $p.enabled.PSObject.Properties) { $prev[$prop.Name] = [bool]$prop.Value }
    }
  } catch {}
}
$disappeared = @(); $disabled = @(); $added = @()
foreach ($k in $prev.Keys) {
  if ($prev[$k]) {
    if (-not $current.ContainsKey($k)) { $disappeared += $k }
    elseif (-not $current[$k]) { $disabled += $k }
  }
}
foreach ($k in $current.Keys) { if (-not $prev.ContainsKey($k)) { $added += $k } }
$stateDir = Split-Path $stateFile -Parent
if (-not (Test-Path $stateDir)) { New-Item -ItemType Directory -Path $stateDir -Force | Out-Null }
$enabledMap = @{}
foreach ($k in $current.Keys) { $enabledMap[$k] = $current[$k] }
@{ ts = $now; enabled = $enabledMap } | ConvertTo-Json -Depth 4 | Set-Content -Path $stateFile -Encoding UTF8
$out = [ordered]@{
  ts = $now; first_run = $firstRun; stores = $stores
  enabled_total = @($current.Keys | Where-Object { $current[$_] }).Count
  disappeared = $disappeared; disabled = $disabled; added = $added; parse_miss = $parseMiss
  mcp_snapshot_stale_days = $mcpSnapshotStaleDays; snapshot_suppressed = $snapshotSuppressed
}
$out | ConvertTo-Json -Compress -Depth 5
