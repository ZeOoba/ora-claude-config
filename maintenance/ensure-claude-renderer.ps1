# ORA Claude Desktop renderer guard -- v1.0 2026-08-05
# ----------------------------------------------------------------------------------
# WHY: both scheduled-task fleets need a live Electron RENDERER to attach a dispatch.
# Measured 2026-08-05 over the desktop app's own logs: with a renderer present, 74 of
# 76 dispatches confirmed; with none, 0 of 53 did -- the dispatch is queued, never
# attaches, and is cleared as a stale pending dispatch minutes later, while lastRunAt
# is advanced anyway so every registry-based check still reports the task healthy.
#
# The task this replaces guarded on `Get-Process Claude`, which is TRUE for an app
# sitting in the tray with no window and no renderer -- exactly the state in which
# dispatches die. It therefore never relaunched during the very outages it existed to
# prevent (e.g. 2026-08-05 07:03-11:08, 4.1h dark, 11 tasks lost, process up the
# whole time).
#
# Renderer absence had TWO causes. The larger one -- ORA's own stuck-session-watchdog
# culling the app's Electron children (155 renderers killed) -- is fixed at source in
# stuck-session-watchdog-lib.ps1. This script covers the remainder: the machine slept,
# or the window was closed.
#
# Launching the AppsFolder shell verb on an ALREADY-RUNNING app activates the existing
# instance and restores its window (which spawns a renderer); it does not start a
# second copy.
#
# Fail-OPEN: any internal error -> log + exit 0. Never block, never nag.
# ASCII-only (PS 5.1 reads non-BOM as ANSI).
#
# Install/refresh (run once):
#   schtasks /Create /TN "ORA Claude Desktop Wake-and-Launch" /SC DAILY /ST 04:45 /F `
#     /TR "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File \"C:\Users\Owner\.claude\maintenance\ensure-claude-renderer.ps1\""
#
# StartWhenAvailable FIX (2026-08-17, fleet-advisory-remediation): the schtasks /Create
# form above does NOT set StartWhenAvailable -- without it, a 04:45 trigger that fires
# while the host is asleep/off is simply ABANDONED (Task Scheduler event 153, "did not
# launch task ... as it missed its schedule"), not deferred, recording Last Result
# 0x80070420 (Task Scheduler's generic code for exactly this) even though the script
# itself is fail-open on every internal path and was never reached. This host's first
# scheduler dispatch varies 03:31-17:09 (reference_am_cluster_late_wake_root_cause),
# so a hard 04:45-or-never trigger silently missed most mornings -- the log had exactly
# ONE line total (2026-08-05) despite running daily since 2026-08-04. Fixed live via:
#   $t = Get-ScheduledTask -TaskName "ORA Claude Desktop Wake-and-Launch"
#   $t.Settings.StartWhenAvailable = $true
#   Set-ScheduledTask -InputObject $t
# If this task is ever deleted and recreated with the /Create one-liner above, RE-APPLY
# this immediately after -- schtasks.exe's CLI has no direct switch for this setting.

param([switch]$WhatIf)

$log    = Join-Path $env:USERPROFILE '.claude\maintenance\ensure-claude-renderer.log'
$appId  = 'shell:AppsFolder\Claude_pzs8sxrjxfjjc!Claude'

function Log($m) { "$([DateTime]::UtcNow.ToString('s'))Z  $m" | Out-File -FilePath $log -Append -Encoding utf8 }

function Get-RendererState {
    <#
    .SYNOPSIS
    Pure decision logic: classify the desktop app's state from process records.
    Returns 'RENDERER' (healthy), 'NO-RENDERER' (running but headless -- relaunch to
    restore the window), or 'NOT-RUNNING' (cold start).
    Separated for unit testing against synthetic fixtures, same pattern as
    stuck-session-watchdog-lib.ps1's Get-KillCandidates.
    #>
    param([Parameter(Mandatory)][AllowEmptyCollection()] $Procs)
    $app = @($Procs | Where-Object { $_.CommandLine -match 'WindowsApps\\Claude_' })
    if ($app.Count -eq 0) { return 'NOT-RUNNING' }
    $rend = @($app | Where-Object { $_.CommandLine -match '--type=renderer' })
    if ($rend.Count -gt 0) { return 'RENDERER' }
    return 'NO-RENDERER'
}

try {
    $procs = @(Get-CimInstance Win32_Process -Filter "Name='claude.exe'" -ErrorAction Stop |
               Select-Object ProcessId, CommandLine)
    $state = Get-RendererState -Procs $procs

    if ($state -eq 'RENDERER') {
        Log "OK - renderer present; fleet can attach dispatches"
        exit 0
    }

    $why = if ($state -eq 'NOT-RUNNING') { 'app not running' }
           else { 'app running but HEADLESS (no renderer) - the old Get-Process guard missed this' }

    if ($WhatIf) { Log "WHATIF - would launch ($why)"; exit 0 }

    Log "LAUNCHING - $why"
    Start-Process explorer.exe $appId
    Start-Sleep -Seconds 25          # give Electron time to spawn the renderer

    $after = @(Get-CimInstance Win32_Process -Filter "Name='claude.exe'" -ErrorAction Stop |
               Select-Object ProcessId, CommandLine)
    $now = Get-RendererState -Procs $after
    if ($now -eq 'RENDERER') { Log "recovered - renderer up" }
    else { Log "STILL $now after launch - fleet remains unable to attach dispatches" }
    exit 0
}
catch {
    Log ('ERROR (fail-open): ' + $_.Exception.Message)
    exit 0
}
