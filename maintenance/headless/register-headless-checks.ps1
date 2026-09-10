# Register the three ORA headless checks on WINDOWS Task Scheduler.
# ---------------------------------------------------------------------------
# WHY WINDOWS TASK SCHEDULER AND NOT create_scheduled_task:
# The dual CC/MCP + LAMS fleets do not run scripts -- they launch Claude sessions
# from a SKILL.md folder, and only while the Desktop app is open. A wrapper script
# is not a thing either registry can hold. Windows Task Scheduler is the substrate
# the other out-of-band ORA guards already use (fleet-deadman.ps1,
# push-fleet-heartbeat.ps1, ora-nightly-disk.ps1, the mirror deploy task itself).
# Running here is the actual prize: these checks keep firing when the Desktop app
# is shut, which is the structural gap both in-fleet guards name in their own
# SKILL.mds ("this guard cannot alarm on its own fleet's disappearance"; "only
# fires while Claude Desktop is open").
#
# START DATE IS DELIBERATE. Gabriel paused the whole fleet 2026-09-07 ("pause all
# routines until Friday at 4:01 PM"); ora-routine-pause-resume-2026-09-11 re-enables
# all 37 CC ids. Standing up three new automated jobs mid-pause would defeat that,
# and the parallel burn-in needs the in-fleet twins running to compare against.
# So every task below starts 2026-09-11, after the resume.
#
# Uninstall:  schtasks /Delete /TN "ORA Headless - <name>" /F
# ASCII-only (PS 5.1 reads a non-BOM file as ANSI).

param([switch]$WhatIf)

$py     = (Get-Command python).Source
$runner = Join-Path $env:USERPROFILE '.claude\maintenance\headless\run-check.py'
$logDir = Join-Path $env:USERPROFILE '.claude\maintenance\headless\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if (-not (Test-Path $runner)) { throw "runner not found: $runner" }

# Cadences mirror the in-fleet twins (offset ~15 min so the headless run observes
# the same day's state) so burn-in is an apples-to-apples comparison:
#   ora-task-integrity-guard            5 7 * * *      -> 07:20 daily
#   ora-command-center-mirror-drift-check weekday 10:40 -> 10:55 weekdays
#   freshness has no in-fleet twin -- it ages the other three heartbeats, so it runs
#   at 07:50, AFTER the 07:20 pair, or it would read their previous day's files and
#   page on a staleness it created by running too early.
$tasks = @(
    @{ Name = 'ORA Headless - integrity-guard'; Check = 'integrity-guard'; Sc = 'DAILY';  St = '07:20'; Days = $null },
    @{ Name = 'ORA Headless - stranded-spec';   Check = 'stranded-spec';   Sc = 'DAILY';  St = '07:20'; Days = $null },
    @{ Name = 'ORA Headless - mirror-drift';    Check = 'mirror-drift';    Sc = 'WEEKLY'; St = '10:55'; Days = 'MON,TUE,WED,THU,FRI' },
    @{ Name = 'ORA Headless - freshness';       Check = 'freshness';       Sc = 'DAILY';  St = '07:50'; Days = $null }
)

foreach ($t in $tasks) {
    $log = Join-Path $logDir ("{0}.log" -f $t.Check)
    # cmd wrapper so the exit code is preserved in LastTaskResult AND the output
    # is teed to a log: a clean run is silent to the user but must not be silent
    # to the evidence trail.
    $cmd = 'cmd.exe /c ""{0}" "{1}" {2} >> "{3}" 2>&1"' -f $py, $runner, $t.Check, $log

    $args = @('/Create', '/TN', $t.Name, '/SC', $t.Sc, '/ST', $t.St,
              '/SD', '09/11/2026', '/F', '/TR', $cmd)
    if ($t.Days) { $args += @('/D', $t.Days) }

    if ($WhatIf) {
        Write-Host "WOULD REGISTER: $($t.Name)  [$($t.Sc) $($t.St)]"
        Write-Host "    $cmd"
    } else {
        & schtasks.exe @args | Out-Null
        if ($LASTEXITCODE -eq 0) { Write-Host "registered: $($t.Name)  [$($t.Sc) $($t.St), starts 09/11/2026]" }
        else { Write-Warning "FAILED to register $($t.Name) (rc=$LASTEXITCODE)" }
    }
}

if (-not $WhatIf) {
    Write-Host ""
    Write-Host "Verify:  schtasks /Query /TN `"ORA Headless - integrity-guard`" /V /FO LIST"
}
