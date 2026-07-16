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
    Two hard exclusions, in order:
      1. CommandLine.Length <= 200 -- the bare desktop-app shell has no flags at all
         (~84 chars observed live); a real scheduled-task session's command line runs into
         the thousands of characters (--allowedTools/--disallowedTools lists). Too short to
         be a task session -- never a candidate, regardless of age.
      2. CommandLine contains "--resume=" -- an interactive session being resumed. This is
         the ONE hard safety line: a resumed session might be a live, active conversation
         with someone at the keyboard, and this watchdog must never kill one, no matter how
         old. A scheduled task fires FRESH (a new invocation, not a reconnect), so it never
         carries --resume=.
    Everything else is a genuine candidate; only those older than $ThresholdMinutes (strictly
    greater than -- age exactly at the threshold is NOT yet a candidate) are returned.
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
