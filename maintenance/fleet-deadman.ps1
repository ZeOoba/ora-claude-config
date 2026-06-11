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

param([int]$ThresholdHours = 30)

$sendLog = Join-Path $env:USERPROFILE '.claude\scheduled-tasks\_shared\send-log.txt'
$log     = Join-Path $env:USERPROFILE '.claude\maintenance\fleet-deadman.log'
$alert   = Join-Path ([Environment]::GetFolderPath('Desktop')) 'FLEET-DOWN_ALERT.txt'

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

Checks: (1) BOTH live registries present (cc = claude-code-sessions, lams = local-agent-mode-
sessions; Roaming + MSIX LocalCache mirror, biggest-then-newest, GUIDs never hardcoded);
(2) per-fleet liveness via newest lastRunAt (fallback registry mtime); (3) send-log.txt freshness.
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
