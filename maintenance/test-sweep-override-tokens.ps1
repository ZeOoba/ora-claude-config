# Tests for sweep-override-tokens.ps1 (TDD, 2026-11-08 audit E5).
# Runs the real script in a CHILD powershell against a FIXTURE USERPROFILE -- never the live
# ~/.claude. Pins: the HubSpot CMS and social-publish token files are swept once past the
# window, like the config/website TTL tokens; a young token and a live session's token are kept.

$ErrorActionPreference = 'Stop'
$script:failures = @()
function Check($label, [bool]$cond) {
    if ($cond) { Write-Output "PASS  $label" }
    else { Write-Output "FAIL  $label"; $script:failures += $label }
}

$sweep = Join-Path $PSScriptRoot 'sweep-override-tokens.ps1'
$home_ = Join-Path ([System.IO.Path]::GetTempPath()) ("sot-" + [guid]::NewGuid().ToString('N').Substring(0, 12))
$sessions = Join-Path $home_ '.claude\hooks\sessions'
New-Item -ItemType Directory -Force -Path (Join-Path $home_ '.claude\maintenance') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $home_ '.claude\sessions') | Out-Null

function Token($sid, $name, $ageMinutes) {
    $dir = Join-Path $sessions "$sid\overrides"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $p = Join-Path $dir $name
    Set-Content -Path $p -Value 'reason: fixture' -Encoding ASCII
    (Get-Item $p).LastWriteTime = (Get-Date).AddMinutes(-$ageMinutes)
    return $p
}

$oldCms    = Token 'dead-session-1' 'allow-hubspot-cms-write' 180
$oldSocial = Token 'dead-session-1' 'allow-hubspot-social-publish' 180
$oldCfg    = Token 'dead-session-1' 'allow-config-write' 180
$youngCms  = Token 'dead-session-2' 'allow-hubspot-cms-write' 5
$liveSoc   = Token 'live-session-1' 'allow-hubspot-social-publish' 180
'{"sessionId": "live-session-1"}' | Set-Content -Path (Join-Path $home_ '.claude\sessions\1.json') -Encoding ASCII

$ps = (Get-Process -Id $PID).Path
$saved = $env:USERPROFILE
try {
    $env:USERPROFILE = $home_
    & $ps -NoProfile -ExecutionPolicy Bypass -File $sweep | Out-Null
    $rc = $LASTEXITCODE
} finally {
    $env:USERPROFILE = $saved
}
$archive = Join-Path $sessions '_archive_override_tokens'

Check "sweep exits 0" ($rc -eq 0)
Check "expired allow-hubspot-cms-write is archived" (-not (Test-Path $oldCms))
Check "expired allow-hubspot-social-publish is archived" (-not (Test-Path $oldSocial))
Check "expired allow-config-write is still archived (regression)" (-not (Test-Path $oldCfg))
Check "archived cms token lands in _archive_override_tokens (moved, not deleted)" `
    (Test-Path (Join-Path $archive 'dead-session-1_overrides_allow-hubspot-cms-write'))
Check "archived social token lands in _archive_override_tokens (moved, not deleted)" `
    (Test-Path (Join-Path $archive 'dead-session-1_overrides_allow-hubspot-social-publish'))
Check "a token inside the window is kept" (Test-Path $youngCms)
Check "a live session's token is kept" (Test-Path $liveSoc)

Remove-Item -Recurse -Force $home_ -ErrorAction SilentlyContinue
if ($script:failures.Count) { Write-Output ("{0} FAILED" -f $script:failures.Count); exit 1 }
Write-Output "ALL PASS"
exit 0
