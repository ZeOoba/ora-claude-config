# ORA Stuck-Session Watchdog -- kills scheduled-task-fired claude.exe sessions that have run
# past a reasonable ceiling. The mirror-image failure mode to fleet-deadman.ps1 (which detects
# the fleet going SILENT); this detects a session that fired and never finished.
#
# WHY (2026-07-15): ora-health-guard bounds retries PER STEP ("retry Notion at most twice")
# but no scheduled task in this fleet has an OVERALL session timeout -- if any single step (an
# MCP connector call opened via ToolSearch, a subprocess, a network fetch) hangs without its
# own internal timeout, the whole session hangs with it, along with everything it spawned
# underneath. Confirmed same-day: 3 stuck ora-health-guard/ora-site-exposure-probe sessions
# each had 4 separate branches of nested child processes when killed (~14-15 procs apiece),
# not the normal 2-pair MCP-server pattern -- consistent with several connector/subprocess
# handles opened and never released. This happened twice in one day (a 16-process batch
# overnight, this 3-process batch that afternoon) with nothing to stop either one. No existing
# mechanism anywhere in this fleet watches for a session that's stuck-and-running -- checked
# fleet-deadman.ps1 specifically; it only covers the fleet going quiet, the opposite case.
#
# DETECTION (Get-KillCandidates, stuck-session-watchdog-lib.ps1 -- unit-tested against
# synthetic fixtures in test-stuck-session-watchdog.ps1, never against real processes): a
# scheduled-task-fired session has NO --resume=<id> flag (it's a fresh invocation, not a
# reconnect) and a long CommandLine (the bare desktop-app shell has no flags at all, ~84 chars
# observed live; a real task session's command line runs into the thousands of characters).
# An interactive session being resumed ALWAYS carries --resume= and is NEVER touched -- that
# is the one hard safety line this script honors, since a resumed session might be a live,
# active conversation with someone at the keyboard.
#
# Runs from WINDOWS Task Scheduler (outside Claude), same pattern as fleet-deadman.ps1.
# Fail-OPEN toward NOT killing: any internal error -> log and stop this run, kill nothing.
# ALARM = file-only (Desktop STUCK-SESSION-ALERT.txt + this log) when something was actually
# killed. Silent (log-only, no desktop file) on a clean run. NO email, NO toast.
#
# Install/refresh (run once):
#   schtasks /Create /TN "ORA Stuck-Session Watchdog" /SC MINUTE /MO 30 /F `
#     /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"C:\Users\Owner\.claude\maintenance\stuck-session-watchdog.ps1\""
#
# Manual dry run (logs what WOULD be killed, kills nothing):
#   powershell -NoProfile -ExecutionPolicy Bypass -File stuck-session-watchdog.ps1 -WhatIf

param(
    [int]$ThresholdMinutes = 90,
    [switch]$WhatIf
)

. (Join-Path $PSScriptRoot 'stuck-session-watchdog-lib.ps1')

$log   = Join-Path $env:USERPROFILE '.claude\maintenance\stuck-session-watchdog.log'

# --- Log rotation (added 2026-09-06, Automation Audit R21-10 / R22-8) ------------
# This log had no cap of ANY kind: `grep -icE "rotat|MaxLog|trim|Clear-Content|prune|archive"`
# returned 0 against this file, and it was growing unbounded (~8.0KB/day for the
# watchdog, ~5.5KB/day for the heartbeat push). Rotation ARCHIVES, never deletes,
# per standing invariant 6, and is wrapped in try/catch so a rotation failure can
# never take down the caller -- these scripts fail open, like every other guard here.
function Invoke-LogRotation($path, $maxBytes = 1048576) {
    try {
        if (Test-Path -LiteralPath $path) {
            if ((Get-Item -LiteralPath $path).Length -ge $maxBytes) {
                $archDir = Join-Path (Split-Path $path -Parent) '_log_archive'
                if (-not (Test-Path -LiteralPath $archDir)) {
                    New-Item -ItemType Directory -Path $archDir -Force | Out-Null
                }
                $base = [IO.Path]::GetFileNameWithoutExtension($path)
                $dest = Join-Path $archDir ("{0}-{1}.log" -f $base, [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss'))
                Move-Item -LiteralPath $path -Destination $dest -Force
            }
        }
    } catch { }
}
Invoke-LogRotation $log

$alert = Join-Path ([Environment]::GetFolderPath('Desktop')) 'STUCK-SESSION-ALERT.txt'

function Log($m) { "$([DateTime]::UtcNow.ToString('s'))Z  $m" | Out-File -FilePath $log -Append -Encoding utf8 }

function Main {
    try {
        $now = Get-Date
        $procs = Get-CimInstance Win32_Process -Filter "Name = 'claude.exe'" |
                 Select-Object ProcessId, CommandLine, CreationDate
        $candidates = Get-KillCandidates -Procs $procs -Now $now -ThresholdMinutes $ThresholdMinutes

        if ($candidates.Count -eq 0) {
            Log "clean run -- 0 stuck sessions (checked $($procs.Count) claude.exe processes, threshold ${ThresholdMinutes}m)"
            return
        }

        $actionLines = @()
        foreach ($c in $candidates) {
            if ($WhatIf) {
                Log "WHATIF would kill PID $($c.ProcessId), age $($c.AgeMin) min (created $($c.Created))"
                $actionLines += "WOULD KILL: PID $($c.ProcessId), age $($c.AgeMin) min, created $($c.Created)"
                continue
            }
            try {
                $result = taskkill /F /T /PID $c.ProcessId 2>&1
                Log "KILLED PID $($c.ProcessId), age $($c.AgeMin) min (created $($c.Created)): $result"
                $actionLines += "KILLED: PID $($c.ProcessId), age $($c.AgeMin) min, created $($c.Created)"
            } catch {
                Log "FAILED to kill PID $($c.ProcessId): $_"
                $actionLines += "FAILED TO KILL: PID $($c.ProcessId) -- $_"
            }
        }

        if (-not $WhatIf) {
            $alertBody = @(
                "ORA Stuck-Session Watchdog acted at $($now.ToString('s'))",
                "Threshold: ${ThresholdMinutes} minutes. These were scheduled-task-fired sessions",
                "(no --resume flag) that ran past the ceiling -- almost certainly hung on a step",
                "with no internal timeout (a connector call, a subprocess, a network fetch).",
                "Worth checking: which task was it (cross-reference the kill time against each",
                "task's lastRunAt), and whether that specific step needs its own timeout added",
                "to its SKILL.md rather than relying on this watchdog to clean up after it.",
                ""
            ) + $actionLines
            $alertBody -join "`n" | Out-File -FilePath $alert -Encoding utf8
        }
    } catch {
        Log "WATCHDOG ERROR (fail-open, nothing killed this run): $_"
    }
}

Main
