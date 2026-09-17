# Register the ORA headless checks on WINDOWS Task Scheduler (four defined; only
# the ones this checkout's run-check.py implements are actually registered).
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
#   ora-task-integrity-guard              5 7 * * 1    -> Mondays 07:05, headless 07:20 (+15)
#   ora-command-center-mirror-drift-check 40 10 * * 1  -> Mondays 10:40, headless 10:55 (+15)
#   freshness has no in-fleet twin -- it ages the other three heartbeats, so it runs
#   at 07:50, AFTER the 07:20 pair, or it would read their previous run's files and
#   page on a staleness it created by running too early.
#
# WEEKLY, NOT DAILY (2026-09-17, Gabriel-directed "all routines at most once per
# week"): the in-fleet twins were capped the same day, and these must not drift
# back to a cadence the fleet no longer runs. Re-running this script previously
# reset the live tasks to DAILY, silently undoing that policy.
$tasks = @(
    @{ Name = 'ORA Headless - integrity-guard'; Check = 'integrity-guard'; Sc = 'WEEKLY'; St = '07:20'; Days = 'MON' },
    @{ Name = 'ORA Headless - stranded-spec';   Check = 'stranded-spec';   Sc = 'WEEKLY'; St = '07:20'; Days = 'MON' },
    @{ Name = 'ORA Headless - mirror-drift';    Check = 'mirror-drift';    Sc = 'WEEKLY'; St = '10:55'; Days = 'MON' },
    @{ Name = 'ORA Headless - freshness';       Check = 'freshness';       Sc = 'WEEKLY'; St = '07:50'; Days = 'MON' }
)

# WHY THIS EXISTS -- these three flags are the difference between a registered
# task and a task that RUNS (root incident 2026-09-17, diagnosed live):
# `schtasks /Create` cannot set them, and its defaults are wrong for a laptop.
#   StartWhenAvailable        $false -> a missed slot is DROPPED, not caught up.
#   DisallowStartIfOnBatteries $true -> a catch-up run on battery is REFUSED.
#   StopIfGoingOnBatteries     $true -> a running check dies when AC is unplugged.
# integrity-guard and stranded-spec were registered 2026-09-10 and had NEVER
# executed once by 09-17: this machine is asleep or hibernated at 07:20 every
# day and unplugged overnight, so every slot was missed, then refused on wake
# with 0x800710E0 (ERROR_REQUEST_REFUSED). The log files the runner appends to
# did not exist at all, which is how we know. Task Scheduler reported the tasks
# as Ready the whole time. Do not "simplify" this away -- the other out-of-band
# ORA guards (Fleet Dead-Man, Pause-Resume Guard, Wake-and-Launch, Mirror
# Deploy) all carry StartWhenAvailable for the same reason.
function Set-HeadlessRunConditions {
    param([Parameter(Mandatory)][string]$TaskName)
    # -TaskPath '\' on BOTH queries: without it a same-named task in a subfolder
    # makes $task an array and -TaskPath $task.TaskPath throws. These tasks are
    # registered at the root by the schtasks call above.
    try {
        $task = Get-ScheduledTask -TaskName $TaskName -TaskPath '\' -ErrorAction Stop
        $s = $task.Settings
        $s.StartWhenAvailable = $true
        $s.DisallowStartIfOnBatteries = $false
        $s.StopIfGoingOnBatteries = $false
        # NOTE for anyone copying this helper: Set-ScheduledTask DROPS a stored
        # password on a Password-logon task. Safe here -- these run InteractiveToken.
        Set-ScheduledTask -TaskName $TaskName -TaskPath $task.TaskPath -Settings $s | Out-Null
        $v = (Get-ScheduledTask -TaskName $TaskName -TaskPath '\' -ErrorAction Stop).Settings
        if ($v.StartWhenAvailable -and -not $v.DisallowStartIfOnBatteries -and
            -not $v.StopIfGoingOnBatteries) {
            Write-Host "    run conditions: catch-up ON, battery restrictions OFF"
            return $true
        }
        Write-Warning ("    run conditions NOT applied to {0} -- it will drop missed slots" -f $TaskName)
        return $false
    } catch {
        Write-Warning ("    could not set run conditions on {0}: {1}" -f $TaskName, $_.Exception.Message)
        return $false
    }
}

# NEVER REGISTER A CHECK THE RUNNER DOES NOT IMPLEMENT (2026-09-17). The four
# task names here are a superset of what a given checkout's run-check.py can
# actually run: `freshness` exists on main but not in the 09-10 pre-review draft
# that is still the LIVE copy on this machine. Registering it there creates a
# task that exits 2 ("unknown check") every week, writes no heartbeat, and pages
# nobody -- a permanently dead task the other guards then trip over. run-check.py
# --help lists its checks machine-readably, so ask it rather than assuming.
function Get-RunnerChecks {
    param([Parameter(Mandatory)][string]$Python, [Parameter(Mandatory)][string]$Runner)
    try {
        $help = & $Python $Runner --help 2>&1 | Out-String
    } catch {
        return $null   # cannot ask -> caller registers everything, as before
    }
    # (?i) so a future '--help' that capitalises the label still matches.
    $m = [regex]::Match($help, '(?im)^\s*checks:\s*(.+)$')
    if (-not $m.Success) { return $null }
    return ($m.Groups[1].Value -split ',' | ForEach-Object { $_.Trim() } |
            Where-Object { $_ })
}

$failed = 0

# Fail-OPEN on purpose: if the runner cannot be asked, register everything, as
# this script always did. Fail-closed would leave the machine with ZERO headless
# guards, which is worse than a task that exits 2 into a log that exists. But it
# still counts toward $failed -- "I could not verify what I registered" must not
# report success to a caller, which is the same silent-success this script's
# exit-1 block exists to close.
$runnerChecks = Get-RunnerChecks -Python $py -Runner $runner
if ($runnerChecks) {
    Write-Host ("runner implements: {0}" -f ($runnerChecks -join ', '))
} else {
    Write-Warning "could not read the runner's check list -- registering all tasks unfiltered"
    $failed++
}

foreach ($t in $tasks) {
    if ($runnerChecks -and ($runnerChecks -notcontains $t.Check)) {
        Write-Warning ("SKIPPED {0}: this checkout's run-check.py does not implement '{1}' -- register it after the runner catches up" -f $t.Name, $t.Check)
        continue
    }
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
        if ($LASTEXITCODE -eq 0) {
            Write-Host "registered: $($t.Name)  [$($t.Sc) $($t.St), starts 09/11/2026]"
            if (-not (Set-HeadlessRunConditions -TaskName $t.Name)) { $failed++ }
        }
        else {
            Write-Warning "FAILED to register $($t.Name) (rc=$LASTEXITCODE)"
            $failed++
        }
    }
}

if (-not $WhatIf) {
    Write-Host ""
    Write-Host "Verify:  schtasks /Query /TN `"ORA Headless - integrity-guard`" /V /FO LIST"
    # A task registered WITHOUT its run conditions is the exact silent failure
    # this script exists to close -- it must not report success to a caller or CI.
    if ($failed -gt 0) {
        Write-Warning ("{0} task(s) did not get their run conditions -- they will DROP missed slots" -f $failed)
        exit 1
    }
}
