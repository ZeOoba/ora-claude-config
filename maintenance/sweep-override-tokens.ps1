# sweep-override-tokens.ps1 -- periodic ARCHIVE sweep for stale hook-override tokens under
# C:\Users\Owner\.claude\hooks\sessions\<sessionId>\.
#
# Three token types accumulate there and are never cleaned up by the hooks themselves:
#   1. override               (eos-plan-gate.py)          -- presence-only, NO built-in TTL.
#   2. allow-foreign-commit    (commit-provenance-guard.py) -- presence-only, NO built-in TTL.
#   3. overrides\allow-config-write, overrides\allow-website-write (config-write-guard.py)
#      -- Tier-based, hook enforces a real 3600s (60min) TTL already; anything older is
#      already functionally inert to the hook, sweeping it changes no behavior.
#      Same class: overrides\allow-hubspot-cms-write, overrides\allow-hubspot-social-publish
#      (ora-autonomy-gate.py; 600s / 300s TTLs) -- added 2026-11-08, audit E5.
# Manual sweep 2026-07-21 found 114 stale tokens (all from sessions long since idle/closed)
# with zero functional impact -- this script automates that, on the same weekly cadence as
# Block K's session-env-retention.ps1, and follows the identical safety pattern: live-sessionId
# cross-check + age window + MOVE to archive (never delete -- ORA archive invariant), full log,
# fail-open exit 0.
#
# Policy windows (deliberately more conservative than the TTL-backed type for the two
# no-TTL token types, since sweeping those is a policy choice, not just matching existing
# hook semantics):
#   - override / allow-foreign-commit:              $NoTtlWindowHours (default 24h)
#   - overrides\allow-config-write / allow-website-write: $TtlWindowMinutes (default 60min,
#     matches config-write-guard.py's own CLAIM_TTL_SECONDS=3600 exactly)
#
# Safety checks, in order (mirrors session-env-retention.ps1):
#   1. Re-read ~/.claude/sessions/*.json fresh; never touch a session dir whose sessionId is live.
#   2. Skip anything with LastWriteTime inside its window.
#   3. _archive_override_tokens\ itself is never enumerated as a candidate.
#   4. Every action and every skip-for-safety is logged; nothing happens silently.
param(
  [double]$NoTtlWindowHours = 24,
  [double]$TtlWindowMinutes = 60,
  [switch]$DryRun
)
$ErrorActionPreference = 'SilentlyContinue'
$root    = Join-Path $env:USERPROFILE '.claude\hooks\sessions'
$archive = Join-Path $root '_archive_override_tokens'
$logFile = Join-Path $env:USERPROFILE '.claude\maintenance\override-token-sweep.log'
function Log([string]$m) {
  $line = "{0:yyyy-MM-ddTHH:mm:ss} {1}" -f (Get-Date), $m
  Add-Content -Path $logFile -Value $line
  Write-Host $line
}
if (-not (Test-Path $root)) { Log "hooks/sessions missing -- nothing to do"; exit 0 }
if (-not (Test-Path $archive)) { New-Item -ItemType Directory -Path $archive -Force | Out-Null }

# Live sessionId set (check 1) -- read fresh every run, same source as session-env-retention.ps1.
$live = @{}
Get-ChildItem (Join-Path $env:USERPROFILE '.claude\sessions') -Filter '*.json' -File -ErrorAction SilentlyContinue | ForEach-Object {
  try {
    $j = Get-Content $_.FullName -Raw | ConvertFrom-Json
    if ($j.sessionId) { $live[[string]$j.sessionId] = $true }
  } catch {}
}

$noTtlCut = (Get-Date).AddHours(-$NoTtlWindowHours)
$ttlCut   = (Get-Date).AddMinutes(-$TtlWindowMinutes)

# Candidate token relative paths (within each session dir) and which cutoff governs them.
$noTtlNames = @('override', 'allow-foreign-commit')
# HubSpot tiers added 2026-11-08 (audit E5): ora-autonomy-gate.py's allow-hubspot-cms-write
# (600s TTL) and allow-hubspot-social-publish (300s TTL, single-use). Both TTLs are shorter
# than $TtlWindowMinutes, so anything swept is already inert to the gate.
$ttlNames   = @('overrides\allow-config-write', 'overrides\allow-website-write',
                'overrides\allow-hubspot-cms-write', 'overrides\allow-hubspot-social-publish')

$sessionDirs = Get-ChildItem $root -Directory | Where-Object { $_.Name -ne '_archive_override_tokens' }
$moved = 0; $keptLive = 0; $keptYoung = 0; $scanned = 0
foreach ($d in $sessionDirs) {
  $sid = $d.Name
  $isLive = $live.ContainsKey($sid)
  foreach ($rel in $noTtlNames) {
    $p = Join-Path $d.FullName $rel
    if (-not (Test-Path $p -PathType Leaf)) { continue }
    $scanned++
    if ($isLive) { $keptLive++; continue }
    $lw = (Get-Item $p).LastWriteTime
    if ($lw -ge $noTtlCut) { $keptYoung++; continue }
    $dest = Join-Path $archive "$sid`_$($rel -replace '\\','_')"
    if ($DryRun) { Log ("DRYRUN would-archive {0} (lastWrite {1:yyyy-MM-dd HH:mm}, session-live={2})" -f $p, $lw, $isLive); $moved++; continue }
    Move-Item -Path $p -Destination $dest -Force
    if ($?) { $moved++; Log ("ARCHIVED {0} -> {1}" -f $p, $dest) } else { Log ("SKIP move-failed {0}" -f $p) }
  }
  foreach ($rel in $ttlNames) {
    $p = Join-Path $d.FullName $rel
    if (-not (Test-Path $p -PathType Leaf)) { continue }
    $scanned++
    if ($isLive) { $keptLive++; continue }
    $lw = (Get-Item $p).LastWriteTime
    if ($lw -ge $ttlCut) { $keptYoung++; continue }
    $dest = Join-Path $archive "$sid`_$($rel -replace '\\','_')"
    if ($DryRun) { Log ("DRYRUN would-archive {0} (lastWrite {1:yyyy-MM-dd HH:mm}, session-live={2})" -f $p, $lw, $isLive); $moved++; continue }
    Move-Item -Path $p -Destination $dest -Force
    if ($?) { $moved++; Log ("ARCHIVED {0} -> {1}" -f $p, $dest) } else { Log ("SKIP move-failed {0}" -f $p) }
  }
  # Clean up a now-empty overrides\ dir (cosmetic only -- never removes anything with content).
  $overridesDir = Join-Path $d.FullName 'overrides'
  if ((Test-Path $overridesDir -PathType Container) -and -not (Get-ChildItem $overridesDir -Force -ErrorAction SilentlyContinue | Select-Object -First 1)) {
    if (-not $DryRun) { Remove-Item $overridesDir -Force -ErrorAction SilentlyContinue }
  }
}
$mode = if ($DryRun) { 'DRYRUN' } else { 'LIVE' }
Log ("{0} sweep done: no-ttl-window={1}h ttl-window={2}min tokens-archived={3} kept-live-session={4} kept-in-window={5} tokens-scanned={6} sessions-scanned={7}" -f $mode, $NoTtlWindowHours, $TtlWindowMinutes, $moved, $keptLive, $keptYoung, $scanned, $sessionDirs.Count)
exit 0
