# Tests for ensure-claude-renderer.ps1's Get-RendererState (TDD, 2026-08-05).
# Synthetic fixtures only -- never touches a real process, never launches anything.
# Command lines copied from the live process table 2026-08-05.

# Dot-source ONLY the function: running the script body would launch the app.
$src = Get-Content -Raw (Join-Path $PSScriptRoot 'ensure-claude-renderer.ps1')
$fn  = [regex]::Match($src, '(?s)function Get-RendererState \{.*?\n\}').Value
if (-not $fn) { Write-Output 'FAIL  could not extract Get-RendererState'; exit 1 }
Invoke-Expression $fn

$script:failures = @()
function Check($label, [bool]$cond) {
    if ($cond) { Write-Output "PASS  $label" }
    else { Write-Output "FAIL  $label"; $script:failures += $label }
}

$pkg = '"C:\Program Files\WindowsApps\Claude_1.25927.0.0_x64__pzs8sxrjxfjjc\Claude.exe"'
function App($type) {
    if ($type) { return "$pkg --type=$type --user-data-dir=""C:\Users\Owner\AppData\Roaming\Claude"" --mojo-platform-channel-handle=2312" }
    return $pkg
}
$cli = 'C:\Users\Owner\AppData\Roaming\Claude\claude-code\2.1.221\claude.exe --output-format stream-json --permission-mode bypassPermissions'

# 1. Healthy: shell + renderer present.
Check "shell + renderer -> RENDERER" ((Get-RendererState -Procs @(
    [pscustomobject]@{ProcessId=9480; CommandLine=(App $null)}
    [pscustomobject]@{ProcessId=8324; CommandLine=(App 'renderer')}
)) -eq 'RENDERER')

# 2. THE BUG THE OLD GUARD MISSED: app running, gpu+utility alive, NO renderer.
#    Get-Process Claude is TRUE here, so the old task did nothing -- yet the fleet
#    is dead. This is the exact 2026-08-05 07:03-11:08 state.
Check "app running but headless -> NO-RENDERER (old guard saw 'running')" ((Get-RendererState -Procs @(
    [pscustomobject]@{ProcessId=20820; CommandLine=(App $null)}
    [pscustomobject]@{ProcessId=6428;  CommandLine=(App 'gpu-process')}
    [pscustomobject]@{ProcessId=20772; CommandLine=(App 'utility')}
)) -eq 'NO-RENDERER')

# 3. Cold start: nothing running at all.
Check "no processes -> NOT-RUNNING" ((Get-RendererState -Procs @()) -eq 'NOT-RUNNING')

# 4. CLI task sessions must NOT be mistaken for the desktop app. Sessions can be
#    running while the app is headless -- that is precisely the phantom state.
Check "only CLI sessions running -> NOT-RUNNING (sessions are not the app)" ((Get-RendererState -Procs @(
    [pscustomobject]@{ProcessId=34012; CommandLine=$cli}
    [pscustomobject]@{ProcessId=35100; CommandLine=$cli}
)) -eq 'NOT-RUNNING')

# 5. A CLI session must never be misread as a renderer.
Check "CLI sessions + headless app -> NO-RENDERER" ((Get-RendererState -Procs @(
    [pscustomobject]@{ProcessId=20820; CommandLine=(App $null)}
    [pscustomobject]@{ProcessId=34012; CommandLine=$cli}
)) -eq 'NO-RENDERER')

# 6. Multiple renderers (several windows/webviews) still reads healthy.
Check "multiple renderers -> RENDERER" ((Get-RendererState -Procs @(
    [pscustomobject]@{ProcessId=20820; CommandLine=(App $null)}
    [pscustomobject]@{ProcessId=8324;  CommandLine=(App 'renderer')}
    [pscustomobject]@{ProcessId=15592; CommandLine=(App 'renderer')}
)) -eq 'RENDERER')

# 7. Defensive: a null CommandLine in the batch must not crash the classifier.
Check "null CommandLine tolerated" ((Get-RendererState -Procs @(
    [pscustomobject]@{ProcessId=1; CommandLine=$null}
    [pscustomobject]@{ProcessId=8324; CommandLine=(App 'renderer')}
)) -eq 'RENDERER')

Write-Output ""
if ($script:failures.Count -gt 0) {
    Write-Output "$($script:failures.Count) FAILED: $($script:failures -join '; ')"
    exit 1
}
Write-Output "ALL PASS - renderer-state classification correct"
exit 0
