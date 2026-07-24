# ORA scheduled-task integrity guard (authoritative engine)
# Self-heals the scheduler's canonical task-definition home from dual backups.
# Source of truth = the active scheduled-tasks.json registries under the packaged app store.
# Newest-wins across {canonical, governance mirror, local mirror}. Never deletes; only adds/updates.
$ErrorActionPreference = 'Stop'
try {
    # dual-base discovery (2026-07-09): the live store moved to AppData\Roaming\Claude
    # after the 2026-07-05 migration; the MSIX LocalCache mirror is gone on this machine,
    # so scanning it alone yielded checked:0 (a silent no-op).
    # Roots come from the shared config (single source of truth, same file the python
    # probes read via _shared/store_discovery.py); the literals below are only the
    # fail-open fallback if the config is missing/unreadable.
    $storeRoots = @(
        'C:\Users\Owner\AppData\Roaming\Claude',
        'C:\Users\Owner\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude'
    )
    try {
        $storeCfg = Get-Content -LiteralPath 'C:\Users\Owner\.claude\maintenance\_shared\scheduler-stores.json' -Raw | ConvertFrom-Json
        if ($storeCfg.storeRoots) {
            $storeRoots = @($storeCfg.storeRoots | ForEach-Object { [Environment]::ExpandEnvironmentVariables($_) })
        }
    } catch {}
    $canonRoot = 'C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled'
    $gov   = 'C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\00_Governance\Scheduled'
    $local = 'C:\Users\Owner\.claude\_scheduled_tasks_backup'
    foreach ($d in @($canonRoot, $gov, $local)) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

    # 1. Build active task set {id -> canonical filePath} from every registry under the app store.
    $ids = @{}
    Get-ChildItem -Path ($storeRoots | ForEach-Object { Join-Path $_ '*-sessions\*\*\scheduled-tasks.json' }) -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $j = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
            foreach ($t in $j.scheduledTasks) {
                if ($t.id -and $t.filePath) { $ids[$t.id] = $t.filePath }
            }
        } catch {}
    }

    if ($ids.Count -eq 0) {
        # Self-check for the self-healer: zero discovered registry entries means store
        # discovery itself is broken -- the 2026-07 checked:0 silent no-op ran ~4 days
        # undetected. Surface it as an engine error (exit 1) so the wrapper alarms.
        Write-Output '{"error":"checked==0 -- no registry entries discovered under any store root; store discovery is broken (silent no-op)","checked":0}'
        exit 1
    }

    $restored = @(); $backed = @(); $missing = @(); $churn = @()

    # CONTENT-EQUALITY GATE (2026-07-24). mtime alone is NOT evidence that a copy diverged.
    # The governance mirror lives in OneDrive, whose sync bumps mtimes after this script copies
    # canonical -> mirror. On the next run newest-wins therefore points AT the mirror and copies
    # it back, so the same ids oscillated between backed_up[] and restored[] on consecutive runs
    # (observed live 2026-07-24: 6 ids in backed_up at 12:12, the same 6 in restored at 12:33,
    # with canonical/gov/local byte-identical throughout). restored[] non-empty is a STEP-3 EMAIL
    # alarm, so ordinary OneDrive sync was able to page Gabriel about a "restore" that moved no
    # bytes. Fix: hash first, act only on real divergence. Suppressed churn is REPORTED in
    # churn_suppressed[] -- never silently swallowed, since an invisible suppressor would just be
    # a new blind spot of exactly the kind this guard exists to catch.
    function Get-ContentHash([string]$Path) {
        try { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash } catch { return $null }
    }

    foreach ($id in $ids.Keys) {
        $fp   = $ids[$id]                  # canonical filePath (Documents\Claude\Scheduled\<id>\SKILL.md)
        $name = Split-Path $fp -Leaf
        $cands = @($fp, (Join-Path $gov "$id\$name"), (Join-Path $local "$id\$name")) |
                 Where-Object { Test-Path -LiteralPath $_ }
        if ($cands.Count -eq 0) { $missing += $id; continue }
        $good = $cands | Sort-Object { (Get-Item -LiteralPath $_).LastWriteTime } -Descending | Select-Object -First 1

        # restore canonical if MISSING, or if a newer-mtime copy genuinely differs in content
        $canonAbsent = -not (Test-Path -LiteralPath $fp)
        $needCanon = $canonAbsent
        if (-not $canonAbsent) {
            if ((Get-Item -LiteralPath $good).LastWriteTime -gt (Get-Item -LiteralPath $fp).LastWriteTime) {
                $hGood = Get-ContentHash $good
                $hCanon = Get-ContentHash $fp
                if ($null -eq $hGood -or $null -eq $hCanon) {
                    # Unreadable file: fail SAFE by preserving the old mtime-only behaviour rather
                    # than silently skipping a restore we cannot prove is unnecessary.
                    $needCanon = $true
                } elseif ($hGood -ne $hCanon) {
                    $needCanon = $true
                } else {
                    if ($churn -notcontains $id) { $churn += $id }
                }
            }
        }
        if ($needCanon) {
            New-Item -ItemType Directory -Force -Path (Split-Path $fp) | Out-Null
            Copy-Item -LiteralPath $good -Destination $fp -Force
            if ($restored -notcontains $id) { $restored += $id }
        }

        # refresh both mirrors from the (now newest) canonical -- same content gate, so an
        # mtime-only difference does not trigger a copy that would re-arm the oscillation.
        $hCanonNow = Get-ContentHash $fp
        foreach ($m in @($gov, $local)) {
            $mp = Join-Path $m "$id\$name"
            $mirrorAbsent = -not (Test-Path -LiteralPath $mp)
            $needM = $mirrorAbsent
            if (-not $mirrorAbsent) {
                if ((Get-Item -LiteralPath $fp).LastWriteTime -gt (Get-Item -LiteralPath $mp).LastWriteTime) {
                    $hMirror = Get-ContentHash $mp
                    if ($null -eq $hCanonNow -or $null -eq $hMirror) { $needM = $true }
                    elseif ($hCanonNow -ne $hMirror) { $needM = $true }
                    else { if ($churn -notcontains $id) { $churn += $id } }
                }
            }
            if ($needM) {
                New-Item -ItemType Directory -Force -Path (Split-Path $mp) | Out-Null
                Copy-Item -LiteralPath $fp -Destination $mp -Force
                if ($backed -notcontains $id) { $backed += $id }
            }
        }
    }

    [ordered]@{
        checked            = $ids.Count
        restored           = @($restored)
        backed_up          = @($backed)
        missing_everywhere = @($missing)
        churn_suppressed   = @($churn)   # mtime-newer but byte-identical; NOT an alarm (2026-07-24)
        ts                 = (Get-Date).ToString('s')
    } | ConvertTo-Json -Compress
} catch {
    Write-Output ('{"error":"' + ($_.Exception.Message -replace '"','\"') + '"}')
    exit 1
}
