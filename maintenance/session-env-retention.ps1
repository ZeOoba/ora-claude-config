# session-env-retention.ps1 -- 90-day ARCHIVE sweep for C:\Users\Owner\.claude\session-env\
# (setup-audit remediation Task 10, SESSION_ENV_RETENTION=90-DAY, Gabriel-ratified 2026-07-09).
#
# session-env\ holds UUID-named, empirically-empty per-session scratch dirs created by the
# Claude app itself (~150-350/day; see memory/reference_session_env_retention_proposal.md).
# Policy: dirs older than 90 days are MOVED (never deleted -- ORA archive invariant) to
# session-env\_archive\. Invoked weekly by the ora-weekly-hygiene scheduled task; safe to
# run ad hoc. Exit 0 always (fail-open maintenance posture).
#
# Safety checks, in order (proposal's belt-and-suspenders retained even at 90 days):
#   1. Re-read ~/.claude/sessions/*.json fresh; never touch a dir whose name matches a live sessionId.
#   2. Skip anything with LastWriteTime inside the window (default 90 days).
#   3. _archive\ itself is never enumerated as a candidate.
#   4. Non-empty candidates are still archived (a move preserves content) but logged loudly
#      as ANOMALY -- these dirs are empty by observation; content appearing means the app's
#      behavior changed and the policy should be re-reviewed.
#   5. Every action and every skip-for-safety is logged; nothing happens silently.
param(
  [double]$WindowDays = 90,
  [switch]$DryRun
)
$ErrorActionPreference = 'SilentlyContinue'
$root    = Join-Path $env:USERPROFILE '.claude\session-env'
$archive = Join-Path $root '_archive'
$logFile = Join-Path $env:USERPROFILE '.claude\maintenance\session-env-retention.log'
function Log([string]$m) {
  $line = "{0:yyyy-MM-ddTHH:mm:ss} {1}" -f (Get-Date), $m
  Add-Content -Path $logFile -Value $line
  Write-Host $line
}
if (-not (Test-Path $root)) { Log "session-env missing -- nothing to do"; exit 0 }
if (-not (Test-Path $archive)) { New-Item -ItemType Directory -Path $archive -Force | Out-Null }

# Live sessionId set (check 1) -- read fresh every run.
$live = @{}
Get-ChildItem (Join-Path $env:USERPROFILE '.claude\sessions') -Filter '*.json' -File -ErrorAction SilentlyContinue | ForEach-Object {
  try {
    $j = Get-Content $_.FullName -Raw | ConvertFrom-Json
    if ($j.sessionId) { $live[[string]$j.sessionId] = $true }
  } catch {}
}

$cut = (Get-Date).AddDays(-$WindowDays)
$dirs = Get-ChildItem $root -Directory | Where-Object { $_.Name -ne '_archive' }
$moved = 0; $keptLive = 0; $keptYoung = 0; $anomalies = 0
foreach ($d in $dirs) {
  if ($live.ContainsKey($d.Name)) { $keptYoung++; $keptLive++; continue }
  if ($d.LastWriteTime -ge $cut)  { $keptYoung++; continue }
  $isEmpty = -not (Get-ChildItem $d.FullName -Force -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1)
  if (-not $isEmpty) { $anomalies++; Log ("ANOMALY non-empty candidate {0} (lastWrite {1:yyyy-MM-dd}) -- archiving anyway, review policy" -f $d.Name, $d.LastWriteTime) }
  if ($DryRun) { Log ("DRYRUN would-archive {0} (lastWrite {1:yyyy-MM-dd})" -f $d.Name, $d.LastWriteTime); $moved++; continue }
  Move-Item -Path $d.FullName -Destination (Join-Path $archive $d.Name) -Force
  if ($?) { $moved++ } else { Log ("SKIP move-failed {0}" -f $d.Name) }
}
$mode = if ($DryRun) { 'DRYRUN' } else { 'LIVE' }
Log ("{0} sweep done: window={1}d candidates-archived={2} kept-in-window={3} (of which live-session={4}) non-empty-anomalies={5} total-scanned={6}" -f $mode, $WindowDays, $moved, $keptYoung, $keptLive, $anomalies, $dirs.Count)
exit 0
