# dry-run-task-integrity-guard.ps1 (2026-07-17) -- read-mostly diagnostic that answers
# "would ora-task-integrity-guard's next scheduled run alarm or report GUARD OK?" without
# waiting for the schedule.
#
# WHY: confirming this by hand on 2026-07-16/17 required running 5 separate engines in
# the right order and hand-interpreting their JSON/stdout against the alarm-condition list
# in ora-task-integrity-guard\SKILL.md STEP 3. STEP 0.5 is an easy silent-stale-baseline
# trap (see 2026-07-16 event_log.md "ora-task-integrity-guard next-run-clean confirmed by
# live dry-run") if it's skipped or run out of order.
#
# THE ENGINES ARE AUTHORITATIVE -- this script reimplements NONE of their alarm logic; it
# only orchestrates them in the documented order and reads their own JSON/exit-code output
# against SKILL.md's STEP 3 conditions. If SKILL.md's alarm list ever changes, update the
# reading below to match -- do not let this script and the guard's own doctrine drift apart.
#
# NOT RUN: push-fleet-heartbeat.ps1 (STEP 1.5 script 3) -- it commits+pushes to the
# ora-claude-config repo, and SKILL.md itself notes a push failure there is a STEP-4 note
# only, never a STEP-3 alarm, so it has no bearing on "would this alarm" and this tool
# should not cause pushes just to answer a read-only question.
#
# STEP 0.5's real engine call (list_scheduled_tasks) is an MCP tool only an agent session
# can invoke -- a standalone script cannot call it. Pass a freshly-fetched result via
# -SnapshotJsonPath (a JSON file: bare array, {tasks:[...]}, or {scheduledTasks:[...]},
# each task having id/taskId, enabled, cronExpression, lastRunAt) when running this from an
# agent turn, for full fidelity with the guard's own STEP 0.5. Without it, this script
# falls back to reading the live CC/MCP scheduled-tasks.json registry file directly off
# disk (the same file guard.ps1 itself scans) -- equally current, just not a live MCP
# round-trip; the run output says which path was used.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File dry-run-task-integrity-guard.ps1 [-SnapshotJsonPath <path>]
#
# Idempotent / safe to run anytime: writes only today's _state-history\<date>.cc.DRYRUN.json
# and reads/executes the same read-mostly engines the real scheduled run does. Does not touch
# scheduled-task registration. Not a replacement for the real scheduled run -- a diagnostic only.
#
# FIXED 2026-07-24 -- this wrapper used to write the REAL '<date>.cc.json', described here as
# "harmlessly overwritable". It was not harmless, for two independent reasons:
#   1. FORGED LIVENESS BEACON (the serious one). ora-task-integrity-guard\SKILL.md declares
#      '{DATE}.cc.json' in its output_contract as is_primary_health_signal:true /
#      on_missing_severity:alarm -- it is the ONLY evidence that a guard which is silent-by-design
#      on a clean run actually fired. automation-health-monitor Step 0.56 consumes it. A dry-run
#      writing that exact filename makes a DARK guard look alive, masking precisely the
#      failure class this whole chain exists to catch.
#   2. FIDELITY DOWNGRADE. Without -SnapshotJsonPath this wrapper falls back to the on-disk
#      registry rather than a live list_scheduled_tasks round-trip, so it would replace the
#      real run's authoritative snapshot with a lower-fidelity one.
# The '.cc.dryrun.json' suffix is deliberately NOT matched by the output_contract's
# '{DATE}.cc.json' pattern, nor by membership-guard.ps1's '.lams.json' filter. Do not "simplify"
# it back to .cc.json.

param(
    [string]$SnapshotJsonPath = $null
)

$ErrorActionPreference = 'Stop'
$psExe = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$pyExe = 'C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe'
if (-not (Test-Path -LiteralPath $pyExe)) { $pyExe = 'python' }

$guardDir = 'C:\Users\Owner\.claude\scheduled-tasks\ora-task-integrity-guard'
$maintDir = 'C:\Users\Owner\.claude\maintenance'
$snapDir  = 'C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\_state-history'

$reasons = New-Object System.Collections.Generic.List[string]
$raw     = [ordered]@{}

function Write-Section($title) {
    Write-Output ''
    Write-Output ('=' * 78)
    Write-Output $title
    Write-Output ('=' * 78)
}

function Invoke-Engine([string]$Label, [string]$FilePath, [string[]]$ArgList) {
    # Runs one engine, returns @{ stdout=<string>; exit=<int> }. Never throws --
    # engine failures are data for the verdict, not script failures.
    $stdout = & $FilePath @ArgList 2>&1 | Out-String
    $code = $LASTEXITCODE
    return @{ stdout = $stdout.TrimEnd(); exit = $code }
}

# ---------------------------------------------------------------------------
# STEP 0.5 -- write a DRY-RUN-ONLY copy of the CC/MCP snapshot (<date>.cc.dryrun.json)
#
# NOTE (corrected 2026-07-24): the old comment here claimed this had to run "BEFORE
# membership-guard.ps1" because that engine reads the snapshot. It does not, and has not
# since the 2026-07-15 filename split -- membership-guard.ps1 folds in the LAMS baseline
# ONLY, filtering '20*-*.lams.json' (membership-guard.ps1:78-79) and explicitly excluding
# .cc.json (its own line 63). So this write feeds NOTHING downstream in this wrapper; it is
# kept purely as a diagnostic record of the task list this dry-run actually saw, under a
# filename that cannot be mistaken for the real run's output_contract artifact.
# ---------------------------------------------------------------------------
Write-Section 'STEP 0.5 -- write dry-run CC/MCP snapshot (.cc.dryrun.json -- NOT the real .cc.json)'

$today = (Get-Date).ToString('yyyy-MM-dd')
$ccSnapPath = Join-Path $snapDir "$today.cc.dryrun.json"
$tasks = $null
$source = $null

if ($SnapshotJsonPath) {
    if (Test-Path -LiteralPath $SnapshotJsonPath) {
        try {
            $parsed = Get-Content -LiteralPath $SnapshotJsonPath -Raw | ConvertFrom-Json
            if ($parsed.tasks) { $tasks = $parsed.tasks }
            elseif ($parsed.scheduledTasks) { $tasks = $parsed.scheduledTasks }
            elseif ($parsed -is [array]) { $tasks = $parsed }
            if ($tasks) {
                $source = "supplied -SnapshotJsonPath ($SnapshotJsonPath) -- treated as a fresh list_scheduled_tasks result"
            } else {
                Write-Output "WARN -SnapshotJsonPath parsed but no task array found under tasks/scheduledTasks/bare-array -- falling back to on-disk registry read."
            }
        } catch {
            Write-Output "WARN failed to parse -SnapshotJsonPath ($SnapshotJsonPath): $($_.Exception.Message) -- falling back to on-disk registry read."
        }
    } else {
        Write-Output "WARN -SnapshotJsonPath '$SnapshotJsonPath' not found -- falling back to on-disk registry read."
    }
}

if (-not $tasks) {
    # Fallback: read the live CC/MCP scheduled-tasks.json directly, mirroring guard.ps1's
    # own store discovery -- this is the same file a live list_scheduled_tasks call would
    # reflect, just read locally instead of via an agent-only MCP round-trip.
    $storeRoots = @(
        'C:\Users\Owner\AppData\Roaming\Claude',
        'C:\Users\Owner\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude'
    )
    try {
        $storeCfg = Get-Content -LiteralPath (Join-Path $maintDir '_shared\scheduler-stores.json') -Raw | ConvertFrom-Json
        if ($storeCfg.storeRoots) {
            $storeRoots = @($storeCfg.storeRoots | ForEach-Object { [Environment]::ExpandEnvironmentVariables($_) })
        }
    } catch {}

    $best = $null
    foreach ($base in $storeRoots) {
        $glob = Join-Path $base 'claude-code-sessions\*\*\scheduled-tasks.json'
        $candidates = Get-ChildItem -Path $glob -ErrorAction SilentlyContinue
        foreach ($c in $candidates) {
            try {
                $j = Get-Content -LiteralPath $c.FullName -Raw | ConvertFrom-Json
                $n = @($j.scheduledTasks).Count
                if ($n -gt 0 -and ($null -eq $best -or $n -gt $best.n -or ($n -eq $best.n -and $c.LastWriteTime -gt $best.mtime))) {
                    $best = @{ n = $n; path = $c.FullName; json = $j; mtime = $c.LastWriteTime }
                }
            } catch {}
        }
    }
    if ($best) {
        $tasks = $best.json.scheduledTasks
        $source = "on-disk registry fallback ($($best.path)) -- no -SnapshotJsonPath supplied"
    }
}

if (-not $tasks) {
    Write-Output "STEP 0.5 FAILED -- no CC/MCP task list obtained from -SnapshotJsonPath or on-disk fallback."
    # NOT a WOULD-ALARM reason: this dry-run-only snapshot feeds nothing (see the STEP 0.5
    # header note -- membership-guard.ps1 reads .lams.json only). Failing to write it says
    # nothing about whether the real run would alarm, so it must not poison the verdict.
    Write-Output "NOTE -- could not write the dry-run snapshot. Diagnostic only; does not affect the verdict below (membership-guard.ps1 does not read this file)."
    $raw['step0_5'] = [ordered]@{ ok = $false; error = 'no data source available' }
} else {
    $snapshotTasks = @()
    foreach ($t in $tasks) {
        $id = $t.id
        if (-not $id) { $id = $t.taskId }
        $snapshotTasks += [ordered]@{
            taskId         = $id
            enabled        = [bool]$t.enabled
            cronExpression = $t.cronExpression
            lastRunAt      = $t.lastRunAt
        }
    }
    $snapshot = [ordered]@{
        snapshotDate  = $today
        capturedAtUtc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        source        = "dry-run-task-integrity-guard.ps1 STEP 0.5 ($source)"
        tasks         = $snapshotTasks
    }
    New-Item -ItemType Directory -Force -Path $snapDir | Out-Null
    $snapshot | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ccSnapPath -Encoding UTF8
    Write-Output "OK -- wrote $ccSnapPath ($($snapshotTasks.Count) tasks)"
    Write-Output "     source: $source"
    $raw['step0_5'] = [ordered]@{ ok = $true; path = $ccSnapPath; taskCount = $snapshotTasks.Count; source = $source }
}

# ---------------------------------------------------------------------------
# STEP 1 -- guard.ps1 then membership-guard.ps1
# ---------------------------------------------------------------------------
Write-Section 'STEP 1a -- guard.ps1'
$g = Invoke-Engine 'guard' $psExe @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $guardDir 'guard.ps1'))
Write-Output $g.stdout
Write-Output "exit=$($g.exit)"
$raw['guard'] = $g
$guardJson = $null
try { $guardJson = $g.stdout | ConvertFrom-Json } catch {}
if ($guardJson) {
    $checkedIsZero = ($guardJson.PSObject.Properties['checked'] -and [int]$guardJson.checked -eq 0)
    $restoredNonEmpty = @($guardJson.restored).Count -gt 0
    $missingNonEmpty  = @($guardJson.missing_everywhere).Count -gt 0
    if ($checkedIsZero) { $reasons.Add('guard.ps1 reports checked==0 (store discovery broken -- self-check for the self-healer)') }
    if ($restoredNonEmpty) { $reasons.Add("guard.ps1 restored[] non-empty: $($guardJson.restored -join ', ')") }
    if ($missingNonEmpty) { $reasons.Add("guard.ps1 missing_everywhere[] non-empty: $($guardJson.missing_everywhere -join ', ')") }
    # churn_suppressed is INFORMATIONAL, never a WOULD-ALARM reason (guard.ps1 content-equality
    # gate, 2026-07-24) -- surface it so the suppressor stays observable, but do not escalate.
    if (@($guardJson.churn_suppressed).Count -gt 0) {
        Write-Output "INFO churn_suppressed (mtime-newer but byte-identical, NOT an alarm): $($guardJson.churn_suppressed -join ', ')"
    }
} else {
    Write-Output "WARN guard.ps1 stdout did not parse as JSON -- engine error, not itself a STEP-3 alarm unless it's the checked==0 case (STEP 4 failure note territory); flagging as inconclusive."
    $reasons.Add('guard.ps1 output unparseable -- inconclusive, treat as a guard failure needing manual look (STEP 4 territory)')
}

Write-Section 'STEP 1b -- membership-guard.ps1'
$m = Invoke-Engine 'membership' $psExe @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $guardDir 'membership-guard.ps1'))
Write-Output $m.stdout
Write-Output "exit=$($m.exit)"
$raw['membership'] = $m
$memJson = $null
try { $memJson = $m.stdout | ConvertFrom-Json } catch {}
if ($memJson) {
    $disappearedNonEmpty = @($memJson.disappeared).Count -gt 0
    $disabledNonEmpty    = @($memJson.disabled).Count -gt 0
    $parseMissNonEmpty   = @($memJson.parse_miss).Count -gt 0
    if ($disappearedNonEmpty) { $reasons.Add("membership-guard.ps1 disappeared[] non-empty: $($memJson.disappeared -join ', ')") }
    if ($disabledNonEmpty)    { $reasons.Add("membership-guard.ps1 disabled[] non-empty: $($memJson.disabled -join ', ')") }
    if ($parseMissNonEmpty)   { $reasons.Add("membership-guard.ps1 parse_miss[] non-empty: $($memJson.parse_miss -join ', ')") }
} else {
    Write-Output "WARN membership-guard.ps1 stdout did not parse as JSON -- inconclusive."
    $reasons.Add('membership-guard.ps1 output unparseable -- inconclusive, treat as a guard failure needing manual look')
}

# ---------------------------------------------------------------------------
# STEP 1.5 -- registry-membership-probe.py + emit-fleet-heartbeat.py (push-fleet-heartbeat.ps1 SKIPPED by design)
# ---------------------------------------------------------------------------
Write-Section 'STEP 1.5a -- registry-membership-probe.py'
$rmp = Invoke-Engine 'rmp' $pyExe @((Join-Path $maintDir 'registry-membership-probe.py'))
Write-Output $rmp.stdout
Write-Output "exit=$($rmp.exit)"
$raw['registry_membership_probe'] = $rmp
$rmpActionLines = ($rmp.stdout -split "`n") | Where-Object { $_ -match '\[ACTION\]' }
if ($rmpActionLines -or $rmp.exit -ne 0) {
    $joined = if ($rmpActionLines) { ($rmpActionLines -join ' | ') } else { '(no [ACTION] line captured, but exit was non-zero)' }
    $reasons.Add("registry-membership-probe.py: $joined")
}

Write-Section 'STEP 1.5b -- emit-fleet-heartbeat.py'
$efh = Invoke-Engine 'efh' $pyExe @((Join-Path $maintDir 'emit-fleet-heartbeat.py'))
Write-Output $efh.stdout
Write-Output "exit=$($efh.exit)"
$raw['emit_fleet_heartbeat'] = $efh
if ($efh.exit -ne 0) {
    $reasons.Add("emit-fleet-heartbeat.py exited non-zero ($($efh.exit))")
}

Write-Output ''
Write-Output 'SKIPPED (by design, per this wrapper''s scope): push-fleet-heartbeat.ps1 (STEP 1.5 script 3) -- commits+pushes to ora-claude-config; a push failure there is a STEP-4 note only, never a STEP-3 alarm.'

# ---------------------------------------------------------------------------
# STEP 2.75 -- task-folder-registration-probe.py
# ---------------------------------------------------------------------------
Write-Section 'STEP 2.75 -- task-folder-registration-probe.py'
$tfrp = Invoke-Engine 'tfrp' $pyExe @((Join-Path $maintDir 'task-folder-registration-probe.py'))
Write-Output $tfrp.stdout
Write-Output "exit=$($tfrp.exit)"
$raw['task_folder_registration_probe'] = $tfrp
$tfrpActionLines = ($tfrp.stdout -split "`n") | Where-Object { $_ -match '\[ACTION\] (UNREGISTERED|ORPHANED_REGISTRATION)' }
if ($tfrpActionLines -or $tfrp.exit -ne 0) {
    $joined = if ($tfrpActionLines) { ($tfrpActionLines -join ' | ') } else { '(no matching [ACTION] line captured, but exit was non-zero)' }
    $reasons.Add("task-folder-registration-probe.py: $joined")
}

# ---------------------------------------------------------------------------
# VERDICT
# ---------------------------------------------------------------------------
Write-Section 'VERDICT'
if ($reasons.Count -gt 0) {
    Write-Output 'WOULD ALARM:'
    foreach ($r in $reasons) { Write-Output "  - $r" }
} else {
    Write-Output 'CLEAN -- next run would report GUARD OK'
}

Write-Output ''
Write-Output '(Reminder: this is a diagnostic dry-run, not the real scheduled run -- the actual'
Write-Output 'scheduled ora-task-integrity-guard execution is still the authoritative one, and it'
Write-Output 'also runs STEP 2.5 model-currency (informational-only, never alarms) and the real'
Write-Output 'push-fleet-heartbeat.ps1 pulse, neither of which this wrapper attempts.)'
