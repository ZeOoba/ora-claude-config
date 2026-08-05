# ORA Fleet Dead-Man's-Switch  (out-of-band watchdog) -- v3, DUAL-FLEET re-point 2026-06-10
# ----------------------------------------------------------------------------------
# Runs from WINDOWS Task Scheduler (outside Claude) so it still fires if the fleet goes dark.
# DUAL-FLEET DOCTRINE (2026-06-10, supersedes the v2 "live store = .claude\scheduled-tasks"
# claim): TWO live registries, both firing only while the Desktop app is open:
#   (1) CC/MCP fleet  -- %APPDATA%\Claude\claude-code-sessions\**\scheduled-tasks.json
#   (2) LAMS/Cowork   -- %APPDATA%\Claude\local-agent-mode-sessions\**\scheduled-tasks.json
# The MSIX LocalCache path (Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\) mirrors
# Roaming via virtualization. GUIDs rotate -> NEVER hardcode; discovery = glob both bases,
# keep ONE registry per store (most tasks, tie-break newest mtime) -- mirrors
# maintenance\fleet-status.py discover_registries().
# Checks per fleet: registry PRESENT + LIVENESS (newest lastRunAt across tasks; falls back to
# registry mtime). Secondary proxy kept from v2: _shared\send-log.txt freshness (appended on
# every successful Outlook send). Confound: during a Composio key-rotation window sends fail,
# so send-log stays stale even if tasks run -- first SUCCESSFUL send after rotation clears it.
# ALARM = file-only (Desktop FLEET-DOWN_ALERT.txt + this log). NO email, NO toast.
# Fail-OPEN: any internal error -> exit 0 (never nag on a bug). ASCII-only (PS 5.1 reads non-BOM as ANSI).
#
# Install/refresh (run once):
#   schtasks /Create /TN "ORA Fleet Dead-Man" /SC DAILY /ST 07:30 /F `
#     /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"C:\Users\Owner\.claude\maintenance\fleet-deadman.ps1\""

# CHECK 4 added 2026-08-05: PHANTOM DISPATCH (maintenance\phantom-dispatch-probe.py).
# Checks 1-3 all read lastRunAt, which the scheduler stamps at DISPATCH and stamps
# AGAIN when it garbage-collects a dispatch that never attached -- so a task that
# never started is byte-identical here to one that ran. Measured 2026-08-05: 44% of
# all dispatches over the prior 4 days never started, and this watchdog logged "OK"
# through every one of them. The probe reads the desktop app's own
# "Confirmed task run for:" line, the only reliable execution proof on this machine.
# It lives OUTSIDE both fleets deliberately -- ora-task-integrity-guard was itself
# phantom-dispatched on 08-04 AND 08-05, so an in-fleet check would have been silent
# on exactly the days it was needed.

param(
    [int]$ThresholdHours   = 30,
    [double]$PhantomHours  = 26,
    # Phantom dispatches inside PhantomHours needed to raise the desktop alert.
    # 1 = alarm on any. Raise it if the noise floor gets ignored -- but the count
    # is ALWAYS written to fleet-deadman.log regardless, so raising it hides the
    # alert, never the evidence.
    [int]$PhantomThreshold = 1
)

$sendLog = Join-Path $env:USERPROFILE '.claude\scheduled-tasks\_shared\send-log.txt'
$log     = Join-Path $env:USERPROFILE '.claude\maintenance\fleet-deadman.log'
$alert   = Join-Path ([Environment]::GetFolderPath('Desktop')) 'FLEET-DOWN_ALERT.txt'
$probe   = Join-Path $env:USERPROFILE '.claude\maintenance\phantom-dispatch-probe.py'

function Log($m) { "$([DateTime]::UtcNow.ToString('s'))Z  $m" | Out-File -FilePath $log -Append -Encoding utf8 }

function Find-Registry($store) {
    # One live registry per store: most tasks wins, tie-break newest mtime (Roaming listed first).
    $appdata = if ($env:APPDATA) { $env:APPDATA } else { Join-Path $env:USERPROFILE 'AppData\Roaming' }
    $local   = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $env:USERPROFILE 'AppData\Local' }
    $bases = @(
        (Join-Path $appdata ('Claude\' + $store)),
        (Join-Path $local   ('Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\' + $store))
    )
    $scored = @()
    foreach ($base in $bases) {
        if (-not (Test-Path $base)) { continue }
        $cands = Get-ChildItem -Path $base -Recurse -Filter 'scheduled-tasks.json' -File -ErrorAction SilentlyContinue
        foreach ($f in $cands) {
            try {
                $d = Get-Content -Raw -Path $f.FullName | ConvertFrom-Json
                $n = @($d.scheduledTasks).Count
                if ($n -gt 0) { $scored += [pscustomobject]@{ N = $n; M = $f.LastWriteTime; P = $f.FullName } }
            } catch { }
        }
    }
    if ($scored.Count -eq 0) { return $null }
    return ($scored | Sort-Object -Property N, M -Descending | Select-Object -First 1).P
}

try {
    $problems = @()
    $okBits   = @()

    $fleets = @(
        @{ Label = 'cc';   Store = 'claude-code-sessions' },
        @{ Label = 'lams'; Store = 'local-agent-mode-sessions' }
    )
    foreach ($fleet in $fleets) {
        $reg = Find-Registry $fleet.Store
        if ($null -eq $reg) {
            $problems += ('fleet ' + $fleet.Label + ': NO live registry (scheduled-tasks.json) found under ' + $fleet.Store)
            continue
        }
        $last = $null
        $count = 0
        try {
            $d = Get-Content -Raw -Path $reg | ConvertFrom-Json
            $tasks = @($d.scheduledTasks)
            $count = $tasks.Count
            foreach ($t in $tasks) {
                if ($t.lastRunAt) {
                    try {
                        $ts = [DateTime]::Parse($t.lastRunAt)
                        if ($null -eq $last -or $ts -gt $last) { $last = $ts }
                    } catch { }
                }
            }
        } catch { }
        if ($null -eq $last) { $last = (Get-Item $reg).LastWriteTime }   # fallback: registry mtime
        $ageH = [math]::Round(((Get-Date) - $last).TotalHours, 1)
        if ($ageH -gt $ThresholdHours) {
            $problems += ('fleet ' + $fleet.Label + ': no task run in ' + $ageH + 'h (threshold ' + $ThresholdHours + 'h)  [' + $reg + ']')
        } else {
            $okBits += ($fleet.Label + '=' + $count + ' tasks, last run ' + $ageH + 'h ago')
        }
    }

    # Secondary liveness proxy (kept from v2): send-log freshness.
    $sendAgeH = $null
    if (Test-Path $sendLog) {
        $sendAgeH = [math]::Round(((Get-Date) - (Get-Item $sendLog).LastWriteTime).TotalHours, 1)
    }
    if ($null -eq $sendAgeH) { $problems += 'no send-log.txt - no successful send ever recorded' }
    elseif ($sendAgeH -gt $ThresholdHours) { $problems += ('no successful Outlook send in ' + $sendAgeH + 'h (threshold ' + $ThresholdHours + 'h)') }

    # (4) Phantom dispatch -- tasks that never started. Invisible to checks 1-3.
    $phantomDetail = @()
    if (-not (Test-Path $probe)) {
        $problems += 'phantom-dispatch-probe.py MISSING - the never-started blind spot is unmonitored'
    } else {
        $py = 'C:\Users\Owner\AppData\Local\Programs\Python\Python313\python.exe'
        if (-not (Test-Path $py)) { $py = 'python' }
        $out = & $py $probe --hours $PhantomHours 2>&1
        $rc  = $LASTEXITCODE
        $count = 0
        foreach ($ln in $out) {
            $s = [string]$ln
            if ($s -match '^\s*phantom\s*:\s*(\d+)') { $count = [int]$Matches[1] }
            if ($s -match '^\s{2}\d{4}-\d\d-\d\d .*\[(cleared-stale|never-confirmed)\]') { $phantomDetail += $s.Trim() }
        }
        if ($rc -eq 2) {
            # "Could not look" must never read as "nothing wrong" (verified null).
            $problems += 'phantom-dispatch-probe COULD NOT LOOK (exit 2) - desktop logs unreadable; phantom state UNKNOWN, not clean'
        } elseif ($rc -eq 1) {
            Log ('phantom-dispatch: ' + $count + ' dispatch(es) never started in the last ' + $PhantomHours + 'h')
            if ($count -ge $PhantomThreshold) {
                $problems += ('PHANTOM DISPATCH: ' + $count + ' task dispatch(es) never started in ' +
                              $PhantomHours + 'h (threshold ' + $PhantomThreshold +
                              ') - lastRunAt reports these as healthy runs')
            }
        } elseif ($rc -eq 0) {
            $okBits += 'phantom=0'
        } else {
            $problems += ('phantom-dispatch-probe returned unexpected exit ' + $rc)
        }
    }

    if ($problems.Count -eq 0) {
        Log ('OK: ' + ($okBits -join '; ') + '; last send ' + $sendAgeH + 'h ago')
        if (Test-Path $alert) { Remove-Item $alert -Force }
        exit 0
    }

    $msg = 'ORA FLEET WATCHDOG: ' + ($problems -join '  |  ')
    Log $msg
    $body = @"
ORA FLEET DEAD-MAN ALERT   $((Get-Date).ToString('u'))
============================================================
$msg

$(if ($phantomDetail.Count -gt 0) {
"DISPATCHES THAT NEVER STARTED (last $PhantomHours h)
------------------------------------------------------------
$($phantomDetail -join [Environment]::NewLine)

These produced NO output. lastRunAt reports every one of them as a healthy run --
the scheduler stamps it at dispatch AND again when it clears the stale dispatch.
Do NOT confirm recovery with lastRunAt, fleet-status.py, or recordedSkips; check the
task's OUTPUT. Full list: maintenance\_state\phantom-dispatch.json
Background: memory\reference_scheduler_lastrunat_stamped_at_dispatch.md
"})
Checks: (1) BOTH live registries present (cc = claude-code-sessions, lams = local-agent-mode-
sessions; Roaming + MSIX LocalCache mirror, biggest-then-newest, GUIDs never hardcoded);
(2) per-fleet liveness via newest lastRunAt (fallback registry mtime); (3) send-log.txt freshness;
(4) phantom dispatch via maintenance\phantom-dispatch-probe.py (the only check here that does
NOT trust lastRunAt).
NOTE: during a Composio key-rotation window, sends fail so send-log stays stale even if tasks
run -- the first SUCCESSFUL send after rotation clears this. Both fleets fire only while the
Desktop app is open -- if a registry is stale, check the app is running before re-creating tasks.
Re-check inside Claude:  list_scheduled_tasks (cc fleet)  or  maintenance\fleet-status.py (both).
(This file auto-deletes once the fleet is healthy again.)
"@
    $body | Out-File -FilePath $alert -Encoding utf8
    exit 1
}
catch {
    Log ('ERROR (fail-open): ' + $_.Exception.Message)
    exit 0
}
