# ORA Stuck-Session Watchdog -- pure decision logic (no side effects, no live process access).
# Separated from stuck-session-watchdog.ps1 so it can be dot-sourced and unit-tested against
# synthetic fixtures (test-stuck-session-watchdog.ps1) without ever touching a real process --
# mirrors the memory-index-guard.py / rules-md-guard.py pattern of keeping the "what should
# happen" decision pure and testable, separate from the "make it happen" IO.

function Get-KillCandidates {
    <#
    .SYNOPSIS
    Given a list of claude.exe process records, return the ones that should be killed:
    scheduled-task-fired sessions (no --resume flag, not the bare desktop-app shell) that
    have been running longer than $ThresholdMinutes.

    .DESCRIPTION
    Four hard exclusions, in order. Exclusions 3 and 4 were added 2026-08-05 after
    forensics showed this function had been culling the DESKTOP APP'S OWN Electron
    child processes: 391 electron_utility, 155 electron_renderer, 88 electron_gpu
    and 4 electron_main killed, identified by cross-referencing the kill log against
    the app's own [process-memory] PID->role telemetry. Electron names its children
    claude.exe too, gives them 851-5016 char command lines, and keeps them alive for
    the life of the window -- so exclusions 1 and 2 passed every one of them straight
    through to the age test. The renderer is the process the scheduler needs in order
    to attach a dispatch: with a renderer present 74 of 76 dispatches confirmed; with
    none, 0 of 53 did. Killing it every ~2h was the single largest contributor to the
    fleet's ~45% phantom-dispatch rate -- a watchdog built to protect the fleet was
    the main thing breaking it.
      1. CommandLine.Length <= 200 -- the bare desktop-app shell has no flags at all
         (~84 chars observed live); a real scheduled-task session's command line runs into
         the thousands of characters (--allowedTools/--disallowedTools lists). Too short to
         be a task session -- never a candidate, regardless of age.
      2. CommandLine contains "--resume=" -- an interactive session being resumed. This is
         the ONE hard safety line: a resumed session might be a live, active conversation
         with someone at the keyboard, and this watchdog must never kill one, no matter how
         old. A scheduled task fires FRESH (a new invocation, not a reconnect), so it never
         carries --resume=.
      3. CommandLine contains "--type=" -- an Electron CHILD process of the desktop app
         (--type=renderer / gpu-process / utility). Electron always tags its children
         this way; the Claude Code CLI never passes --type=. Verified against the live
         process table 2026-08-05: every desktop child carried it, no task session did.
      4. CommandLine contains "WindowsApps\Claude_" -- any process whose image is the
         packaged desktop app rather than the CLI. Belt-and-braces behind exclusion 3:
         if a future Electron drops or renames --type=, the package path still holds.
         Task sessions always run from ...\Claude\claude-code\<version>\claude.exe.
    Everything else is a genuine candidate; only those older than $ThresholdMinutes (strictly
    greater than -- age exactly at the threshold is NOT yet a candidate) are returned.

    Both new exclusions fail SAFE (toward not killing). If they ever over-match, the cost
    is a stuck session surviving until the next run -- the cost of under-matching was three
    weeks of a silently-dead fleet.
    #>
    param(
        [Parameter(Mandatory)] $Procs,
        [Parameter(Mandatory)] [datetime] $Now,
        [int] $ThresholdMinutes = 90
    )
    $out = @()
    foreach ($p in $Procs) {
        if ($null -eq $p.CommandLine -or $p.CommandLine.Length -le 200) { continue }
        if ($p.CommandLine -match '--resume=') { continue }
        if ($p.CommandLine -match '--type=') { continue }              # Electron child of the desktop app
        if ($p.CommandLine -match 'WindowsApps\\Claude_') { continue } # packaged desktop app, not the CLI
        $ageMin = ($Now - [datetime]$p.CreationDate).TotalMinutes
        if ($ageMin -gt $ThresholdMinutes) {
            $out += [PSCustomObject]@{
                ProcessId = $p.ProcessId
                AgeMin    = [math]::Round($ageMin, 1)
                Created   = $p.CreationDate
            }
        }
    }
    # Unary comma forces array output -- PowerShell silently unwraps a 1-element array to
    # a bare scalar on return otherwise, which breaks every caller's .Count check exactly
    # when there's precisely one candidate (caught by this function's own test suite).
    return ,$out
}
