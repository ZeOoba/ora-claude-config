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
#   schtasks /Create /TN "ORA Fleet Dead-Man" /SC DAILY /ST 07:45 /F `
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

# START breadcrumbs go to a SEPARATE file (merge-gate finding 2026-09-22). state-freshness-probe
# judges fleet-deadman.log by mtime at 48h, so a START line written there by every run that is
# then killed would keep a dead dead-man looking fresh -- exactly the failure it exists to catch.
# fleet-deadman.log is touched only by runs that reach a verdict.
$startLog = Join-Path $env:USERPROFILE '.claude\maintenance\fleet-deadman.start.log'
function LogStart($m) { "$([DateTime]::UtcNow.ToString('s'))Z  $m" | Out-File -FilePath $startLog -Append -Encoding utf8 }

function Resolve-ProbeRc($r) {
    # A hung phantom probe is "could not look" (exit 2), never clean.
    if ($r.TimedOut) { return 2 }
    return $r.Rc
}

function Get-PublishVerdict($pr) {
    # Returns @{ Ok; Problem } for publish-fleet-heartbeat.py --status. A timeout is UNKNOWN, never ok.
    if ($pr.TimedOut) {
        return @{ Ok = $false; Problem = 'publish-fleet-heartbeat.py --status TIMED OUT after 120s - heartbeat publish state UNKNOWN, not clean' }
    }
    if ($pr.Rc -eq 1) {
        return @{ Ok = $false; Problem = ('HEARTBEAT PUBLISH FAILED: ' + (($pr.Out | Out-String).Trim()) +
                                          ' - the GitHub dead-man is reading a stale heartbeat') }
    }
    if ($pr.Rc -eq 0) { return @{ Ok = $true; Problem = $null } }
    return @{ Ok = $false; Problem = ('publish-fleet-heartbeat.py --status returned unexpected exit ' + $pr.Rc) }
}

function Invoke-PyBounded($py, [string[]]$pyArgs, [int]$TimeoutSec = 120) {
    # Added 2026-09-22. Runs a child with a hard wall-clock limit and returns
    # @{ Out; Rc; TimedOut }. Before this, both python calls below were unbounded: a child
    # that hung (e.g. reading desktop logs that Claude Desktop holds open right after a
    # logon catch-up) held the whole run open until Windows ended it with 0xC000013A. That
    # run then wrote NO log line at all, which is how 5 of 9 days from 09-12 to 09-21 left
    # no trace. A timeout is reported as a problem ("could not look"), never as clean.
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $py
    $psi.Arguments = (@($pyArgs | ForEach-Object { ConvertTo-WinArg $_ }) -join ' ')
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $p = [System.Diagnostics.Process]::Start($psi)
    $so = $p.StandardOutput.ReadToEndAsync()
    $se = $p.StandardError.ReadToEndAsync()
    $limitMs = $TimeoutSec * 1000
    if (-not $p.WaitForExit($limitMs)) {
        # Kill the whole TREE: a grandchild would otherwise outlive the kill (merge-gate R4).
        try { & taskkill.exe /T /F /PID $p.Id 2>&1 | Out-Null } catch { }
        try { $p.Kill() } catch { }
        return @{ Out = ''; Rc = $null; TimedOut = $true }
    }
    # The child exited, but a grandchild that inherited stdout/stderr keeps the streams open,
    # and waiting for them unbounded would hang the run (merge-gate R4). Give them only the
    # time remaining; if they are still open, report "could not look".
    $remain = [Math]::Max(0, $limitMs - [int]$sw.ElapsedMilliseconds)
    if (-not [System.Threading.Tasks.Task]::WaitAll([System.Threading.Tasks.Task[]]@($so, $se), $remain)) {
        return @{ Out = ''; Rc = $null; TimedOut = $true }
    }
    return @{ Out = ($so.Result + $se.Result); Rc = $p.ExitCode; TimedOut = $false }
}

function ConvertTo-WinArg([string]$a) {
    # Standard Windows argv quoting (CommandLineToArgvW rules): backslashes are literal except
    # before a quote, where they must be doubled, plus one more to escape the quote itself;
    # a trailing run of backslashes is doubled before the closing quote. Merge-gate R4: the
    # previous `"` -> `\"` replacement merged 'C:\dir\' and the next argument into one.
    if ($a.Length -gt 0 -and $a -notmatch '[\s"]') { return $a }
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append('"')
    $bs = 0
    foreach ($c in $a.ToCharArray()) {
        if ($c -eq '\') { $bs++; continue }
        if ($c -eq '"') { [void]$sb.Append('\' * (2 * $bs + 1)); [void]$sb.Append('"') }
        else            { [void]$sb.Append('\' * $bs); [void]$sb.Append($c) }
        $bs = 0
    }
    [void]$sb.Append('\' * (2 * $bs))
    [void]$sb.Append('"')
    return $sb.ToString()
}

function Get-PhantomSummary($r) {
    # Parses phantom-dispatch-probe.py's result: @{ Rc; Count; Detail }. Extracted so the
    # stdout parse is testable (merge-gate R4: losing stdout silently zeroed the count, which
    # suppresses a PHANTOM DISPATCH alarm).
    $rc = Resolve-ProbeRc $r
    $count = 0
    $detail = @()
    $lines = if ($r.TimedOut) { @() } else { [string]$r.Out -split "`r?`n" }
    foreach ($ln in $lines) {
        $s = [string]$ln
        if ($s -match '^\s*phantom\s*:\s*(\d+)') { $count = [int]$Matches[1] }
        if ($s -match '^\s{2}\d{4}-\d\d-\d\d .*\[(cleared-stale|never-confirmed)\]') { $detail += $s.Trim() }
    }
    return @{ Rc = $rc; Count = $count; Detail = $detail }
}

function Get-CarveOutIds($label) {
    # Carve-outs (2026-09-22): recurring tasks that stay ENABLED through every pause by
    # standing rule, so their being enabled is not evidence the fleet is live. Mirrors
    # _shared/fleet_pause.py PAUSE_CARVE_OUTS. Keep the two lists identical. Before this,
    # the ora-am-brief carve-out made every real CC pause read as live.
    $carveOuts = @{ cc = @('ora-am-brief'); lams = @() }
    if ($label -and $carveOuts.ContainsKey($label)) { return @($carveOuts[$label]) }
    return @()
}

function Get-RegistryTasks($src) {
    # Merge-gate R8 (race): the fleet loop parses each registry ONCE and hands the parsed
    # task list to every pause / carve-out check, so all checks judge one snapshot. Four
    # separate re-reads could straddle a Desktop-app rewrite; a torn read in the carve-out
    # helper silently read as "no carve-out enabled". Accepts a registry path (parsed here)
    # or an already-parsed task list (returned as-is). Returns $null if a path won't parse.
    if ($src -is [string]) {
        try { return ,@((Get-Content -Raw -Path $src | ConvertFrom-Json).scheduledTasks) } catch { return $null }
    }
    if ($null -eq $src) { return $null }
    return ,@($src)
}

function Get-EnabledCarveOutTasks($src, $label) {
    $ids = @(Get-CarveOutIds $label)
    if ($ids.Count -eq 0) { return @() }
    $tasks = Get-RegistryTasks $src
    if ($null -eq $tasks) { return @() }
    return @($tasks | Where-Object {
        $tid = if ($_.id) { $_.id } else { $_.taskId }
        $_.cronExpression -and $_.enabled -and ($ids -contains $tid) })
}

function Test-HasEnabledCarveOut($src, $label) {
    # A fleet whose carve-out task is still enabled is NOT "all paused" for the send-log
    # check: that task still sends (the Daily Brief). Merge-gate R7, 2026-09-22.
    return (@(Get-EnabledCarveOutTasks $src $label).Count -gt 0)
}

function Get-StaleCarveOuts($src, $label, [double]$thresholdH) {
    # Merge-gate R7, 2026-09-22: a carve-out task keeps running through a bounded pause, so
    # the pause must NOT excuse it. Before this, a dead ora-am-brief during a CC pause read as
    # "BOUNDED PAUSE, alarm suppressed" for up to 14 days. Returns 'id (Nh)' for each enabled
    # carve-out task whose own lastRunAt is older than the threshold, or has never run.
    $out = @()
    foreach ($t in @(Get-EnabledCarveOutTasks $src $label)) {
        $tid = if ($t.id) { $t.id } else { $t.taskId }
        $ageH = $null
        if ($t.lastRunAt) { try { $ageH = [math]::Round(((Get-Date).ToUniversalTime() - ([DateTime]::Parse($t.lastRunAt)).ToUniversalTime()).TotalHours, 1) } catch { } }
        if ($null -eq $ageH) { $out += ($tid + ' (never ran)') }
        elseif ($ageH -gt $thresholdH) { $out += ($tid + ' (' + $ageH + 'h)') }
    }
    return $out
}

function Test-BoundedPause($src, $label = '') {
    # Added 2026-09-10 (ORA Automation Audit R24-3). Returns the earliest future resume
    # time (UTC DateTime) if this fleet is under a DELIBERATE bounded pause, else $null.
    #
    # WHY: on 2026-09-07 both fleets were deliberately paused with synchronized one-time
    # resume tasks. This watchdog has no knowledge of that, so it logged
    # "fleet cc: no task run in 45.6h (threshold 30h)" on 09-09 with no resolving OK line
    # and would have re-alarmed every cycle until the Friday resume. An alarm channel that
    # fires continuously through a correctly-registered pause trains its reader to ignore
    # it -- which is exactly backwards for the one out-of-band monitor that has to be
    # believed during a REAL outage (see Revision 21's four-day fleet outage).
    #
    # The test is STRUCTURAL, deliberately not name-matching on "resume"/"pause": a task
    # can be renamed, and a title is not state. A bounded pause is:
    #     every recurring task disabled  AND  >=1 ENABLED one-time task with a FUTURE fireAt.
    # A fleet that is merely idle still has enabled recurring tasks, so it cannot match.
    # Fail-OPEN like everything else here: any parse problem returns $null (alarm normally).
    try {
        $tasks = Get-RegistryTasks $src
        if ($null -eq $tasks -or $tasks.Count -eq 0) { return $null }
        $carve = @(Get-CarveOutIds $label)
        # id first, taskId as fallback -- same key order as fleet_pause.py.
        $recurring = @($tasks | Where-Object {
            $tid = if ($_.id) { $_.id } else { $_.taskId }
            $_.cronExpression -and ($carve -notcontains $tid) })
        if ($recurring.Count -eq 0) { return $null }
        $enabledRecurring = @($recurring | Where-Object { $_.enabled })
        if ($enabledRecurring.Count -gt 0) { return $null }   # not paused: something still fires
        $nowMs  = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
        # 2026-09-12 review finding: a resume must fire within 14 days (mirrors
        # _shared/fleet_pause.py MAX_RESUME_HORIZON_DAYS). Unbounded, any far-future one-time
        # task (LAMS has one dated ~2027-08) turned a real mass-disable into a year of silence.
        $horizonMs = $nowMs + [long](14 * 86400000)
        $resume = $null
        foreach ($t in $tasks) {
            if ($t.enabled -and $t.fireAt) {
                try {
                    $ms = [long]$t.fireAt
                    if ($ms -gt $nowMs -and $ms -le $horizonMs) {
                        $ts = [DateTimeOffset]::FromUnixTimeMilliseconds($ms).UtcDateTime
                        if ($null -eq $resume -or $ts -lt $resume) { $resume = $ts }
                    }
                } catch { }
            }
        }
        return $resume    # $null if every recurring task is disabled with NO resume queued
    } catch { return $null }
}

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
    # START breadcrumb (2026-09-22): the verdict line is written at the END, so a run killed
    # mid-way was indistinguishable from one that never started. A START in fleet-deadman.start.log
    # with no verdict in fleet-deadman.log at a matching time means "started and died".
    LogStart ('START pid=' + $PID)
    $problems     = @()
    $okBits       = @()
    $pausedFleets = @()   # R24-3: fleets under a deliberate bounded pause with NO enabled carve-out task (R7)

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
        $regTasks = Get-RegistryTasks $reg   # ONE parse; every check below reads this snapshot (R8)
        try {
            $tasks = if ($null -ne $regTasks) { $regTasks } else { @() }
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
            # R24-3: a deliberate bounded pause is not an outage. Suppress the alarm, but
            # ALWAYS log the suppression and the resume time -- the evidence is never hidden,
            # only the alert, same principle as $PhantomThreshold above.
            $pauseUntil = if ($null -ne $regTasks) { Test-BoundedPause $regTasks $fleet.Label } else { $null }
            if ($null -ne $pauseUntil) {
                if (-not (Test-HasEnabledCarveOut $regTasks $fleet.Label)) { $pausedFleets += $fleet.Label }
                $okBits += ($fleet.Label + '=' + $count + ' tasks, BOUNDED PAUSE (all recurring disabled, resume queued ' +
                            $pauseUntil.ToString('s') + 'Z) - last run ' + $ageH + 'h ago, alarm suppressed')
                # R7: carve-out tasks run THROUGH the pause, so the pause never excuses them.
                $staleCarve = @(Get-StaleCarveOuts $regTasks $fleet.Label $ThresholdHours)
                if ($staleCarve.Count -gt 0) {
                    $problems += ('fleet ' + $fleet.Label + ': carve-out task(s) not run during the bounded pause: ' +
                                  ($staleCarve -join ', ') + ' (threshold ' + $ThresholdHours + 'h)')
                }
            } else {
                $problems += ('fleet ' + $fleet.Label + ': no task run in ' + $ageH + 'h (threshold ' + $ThresholdHours + 'h)  [' + $reg + ']')
            }
        } else {
            $okBits += ($fleet.Label + '=' + $count + ' tasks, last run ' + $ageH + 'h ago')
        }
    }

    # Secondary liveness proxy (kept from v2): send-log freshness.
    $sendAgeH = $null
    if (Test-Path $sendLog) {
        $sendAgeH = [math]::Round(((Get-Date) - (Get-Item $sendLog).LastWriteTime).TotalHours, 1)
    }
    # R24-3: when EVERY fleet is under a bounded pause (and none still has an enabled carve-out
    # task such as ora-am-brief, which keeps sending -- R7), nothing is scheduled to send, so a
    # stale send-log is the expected consequence of the pause rather than independent evidence
    # of a broken send path. Suppress it only in that total-pause case -- if even one fleet is
    # live and still nothing has sent, that is a real finding and still alarms.
    $allPaused = ($pausedFleets.Count -gt 0 -and $pausedFleets.Count -eq $fleets.Count)
    if ($null -eq $sendAgeH) { $problems += 'no send-log.txt - no successful send ever recorded' }
    elseif ($sendAgeH -gt $ThresholdHours) {
        if ($allPaused) {
            $okBits += ('send-log ' + $sendAgeH + 'h stale - expected, all fleets under bounded pause')
        } else {
            $problems += ('no successful Outlook send in ' + $sendAgeH + 'h (threshold ' + $ThresholdHours + 'h)')
        }
    }

    # (4) Phantom dispatch -- tasks that never started. Invisible to checks 1-3.
    $phantomDetail = @()
    if (-not (Test-Path $probe)) {
        $problems += 'phantom-dispatch-probe.py MISSING - the never-started blind spot is unmonitored'
    } else {
        $py = 'C:\Users\Owner\AppData\Local\Programs\Python\Python313\python.exe'
        if (-not (Test-Path $py)) { $py = 'python' }
        $r   = Invoke-PyBounded $py @($probe, '--hours', [string]$PhantomHours) 120
        $ph  = Get-PhantomSummary $r
        $rc  = $ph.Rc   # a hang is "could not look" (2), never clean -- via Resolve-ProbeRc
        $count = $ph.Count
        $phantomDetail += @($ph.Detail)
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

    # (5) Heartbeat publish (OI-323, 2026-09-19). push-fleet-heartbeat.ps1 publishes the
    # heartbeat to GitHub and, on failure, leaves a marker; the GitHub Action only notices a day
    # later and buries it in issue #19. --status exits 1 when the marker is present OR when no
    # successful publish is on record within ~26h (a task that never ran leaves no marker).
    # This task fires once a day: it reports the publish that finished BEFORE it. It only sees
    # the same morning's result if it is scheduled after the 07:30 ET publish (07:45 or later);
    # at the same minute it reads the previous cycle.
    $pub = Join-Path $env:USERPROFILE '.claude\maintenance\publish-fleet-heartbeat.py'
    if (-not (Test-Path $pub)) {
        $problems += 'publish-fleet-heartbeat.py MISSING - the external dead-man heartbeat publish is unmonitored'
    } else {
        $py = 'C:\Users\Owner\AppData\Local\Programs\Python\Python313\python.exe'
        if (-not (Test-Path $py)) { $py = 'python' }
        $pr   = Invoke-PyBounded $py @($pub, '--status') 120
        $v = Get-PublishVerdict $pr
        if ($v.Ok) { $okBits += 'heartbeat-publish=ok' } else { $problems += $v.Problem }
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
NOT trust lastRunAt); (5) heartbeat publish via maintenance\publish-fleet-heartbeat.py --status
(marker left by push-fleet-heartbeat.ps1 when the GitHub publish failed).
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
