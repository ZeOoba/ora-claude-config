# ORA scheduled-task integrity guard (authoritative engine)
# Self-heals the scheduler's canonical task-definition home from dual backups.
# Source of truth = the active scheduled-tasks.json registries under the packaged app store.
#
# WRITE POLICY (rewritten 2026-08-09 -- read this before changing anything below):
#   CANONICAL IS AUTHORITATIVE. Mirrors are DERIVED. Canonical is written in exactly one
#   situation -- it is ABSENT -- and never otherwise. Everything else is a mirror refresh
#   from canonical, or a detect-only alarm. Never deletes.
#
#   The previous engine was newest-WINS-BY-MTIME across {canonical, gov mirror, local
#   backup}. On 2026-08-09 08:54:47 that reverted live content for ora-health-guard,
#   ora-task-integrity-guard and automation-health-monitor: the local backup carried mtime
#   2026-08-05 17:58:04 over PRE-08-05 CONTENT, beat canonical on mtime, and was copied
#   over it. Copy-Item preserves the source mtime, so the revert was invisible to any later
#   mtime check. mtime is NOT a version -- OneDrive sync and bulk backup passes stamp it
#   without regard to content lineage.
#
#   That was the THIRD iteration of the mtime bug class (oscillation patched 2026-07-24,
#   checked:0 silent no-op 2026-07-09). A fourth mtime heuristic would be the wrong shape
#   of fix, so mtime is gone entirely: the decision core (maintenance/task-integrity-lib.ps1,
#   Resolve-TaskAction) accepts no time input at all, and a test enforces that. "Newer" is
#   decided from a recorded content-hash ledger, plus the git HEAD blob for the CC-fleet
#   paths that are version-controlled.
#
# The -*Override parameters exist ONLY so maintenance/test-guard-integrity-engine.ps1 can
# drive the real engine against synthetic fixtures in a temp dir. Unattended runs pass
# nothing and get the live paths below.
param(
    [string]  $GovOverride,
    [string]  $LocalOverride,
    [string]  $LedgerPathOverride,
    [string[]]$StoreRootsOverride,
    [string]  $CcRepoOverride
)
$ErrorActionPreference = 'Stop'
try {
    # Resolve the decision core relative to this script so a worktree copy loads the
    # worktree lib (and the live copy loads the live lib). $PSScriptRoot is only safe
    # inside the body -- it is empty in param defaults
    # (reference_powershell_psscriptroot_empty_in_param_defaults.md).
    $libPath = Join-Path $PSScriptRoot '..\..\maintenance\task-integrity-lib.ps1'
    if (-not (Test-Path -LiteralPath $libPath)) {
        $libPath = 'C:\Users\Owner\.claude\maintenance\task-integrity-lib.ps1'
    }
    . $libPath

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
    if ($StoreRootsOverride) { $storeRoots = $StoreRootsOverride }
    $canonRoot  = 'C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled'
    $gov        = 'C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\00_Governance\Scheduled'
    $local      = 'C:\Users\Owner\.claude\_scheduled_tasks_backup'
    $ledgerPath = 'C:\Users\Owner\.claude\maintenance\_state\task-content-ledger.json'
    $ccRepo     = 'C:\Users\Owner\.claude'
    if ($GovOverride)        { $gov        = $GovOverride }
    if ($LocalOverride)      { $local      = $LocalOverride }
    if ($LedgerPathOverride) { $ledgerPath = $LedgerPathOverride }
    if ($CcRepoOverride)     { $ccRepo     = $CcRepoOverride }
    foreach ($d in @($canonRoot, $gov, $local)) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

    # Content identity = SHA256 over the file with CR stripped. Line-ending-only
    # differences (git's autocrlf smudge vs an OneDrive-written copy) are NOT content
    # divergence, and treating them as such would both churn the mirrors and make the
    # git HEAD comparison below useless.
    function Get-NormalizedHash([string]$Path) {
        try {
            $text = [System.IO.File]::ReadAllText($Path)
            $bytes = [System.Text.Encoding]::UTF8.GetBytes(($text -replace "`r", ''))
            $sha = [System.Security.Cryptography.SHA256]::Create()
            try { return ([BitConverter]::ToString($sha.ComputeHash($bytes)) -replace '-', '') }
            finally { $sha.Dispose() }
        } catch { return $null }
    }

    # git HEAD blob for a canonical path that lives inside the ~/.claude checkout (CC fleet).
    # Lineage evidence that survives even if the ledger and BOTH mirrors are poisoned.
    # Computed lazily -- only when canonical is absent, the one case where it changes a write.
    function Get-GitHeadHash([string]$Path) {
        try {
            if (-not $Path.StartsWith($ccRepo, [StringComparison]::OrdinalIgnoreCase)) { return $null }
            $rel = $Path.Substring($ccRepo.Length).TrimStart('\', '/') -replace '\\', '/'
            $blob = & git -C $ccRepo show "HEAD:$rel" 2>$null
            if ($LASTEXITCODE -ne 0 -or $null -eq $blob) { return $null }
            $text = ($blob -join "`n")
            $bytes = [System.Text.Encoding]::UTF8.GetBytes(($text -replace "`r", ''))
            $sha = [System.Security.Cryptography.SHA256]::Create()
            try { return ([BitConverter]::ToString($sha.ComputeHash($bytes)) -replace '-', '') }
            finally { $sha.Dispose() }
        } catch { return $null }
    }

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

    $ledger = Read-TaskLedger $ledgerPath

    $restored = @(); $backed = @(); $missing = @(); $regressed = @(); $unreadable = @()

    foreach ($id in $ids.Keys) {
        $fp   = $ids[$id]                  # canonical filePath from the live registry
        $name = Split-Path $fp -Leaf

        $canonExists = Test-Path -LiteralPath $fp
        $canonHash   = $null
        if ($canonExists) { $canonHash = Get-NormalizedHash $fp }

        # A file that EXISTS but cannot be read is NOT a missing file. The old engine
        # failed "safe" by restoring in that case, which meant an unreadable canonical
        # (transient lock, OneDrive placeholder not yet hydrated) got overwritten from a
        # mirror. Under canonical-is-authoritative the safe direction is the opposite:
        # touch nothing, and alarm so a human looks.
        if ($canonExists -and -not $canonHash) {
            $unreadable += $id
            continue
        }

        $mirrorPaths  = [ordered]@{ gov = (Join-Path $gov "$id\$name"); local = (Join-Path $local "$id\$name") }
        $mirrorHashes = @{}
        foreach ($m in $mirrorPaths.Keys) { $mirrorHashes[$m] = Get-NormalizedHash $mirrorPaths[$m] }

        $gitHead = $null
        if (-not $canonHash) { $gitHead = Get-GitHeadHash $fp }

        $entry = $null
        if ($ledger.ContainsKey($id)) { $entry = $ledger[$id] }

        $r = Resolve-TaskAction -Id $id -CanonHash $canonHash -MirrorHashes $mirrorHashes `
                                -LedgerEntry $entry -GitHeadHash $gitHead

        # --- act -------------------------------------------------------------
        if ($r.Action -eq 'missing_everywhere') { $missing += $id; continue }
        if ($r.Action -eq 'regression_detected' -or $r.Action -eq 'known_good_lost') {
            # Detect-only. Canonical is left exactly as found and mirror sync is FROZEN so
            # the regressed content cannot overwrite the last good copy.
            $regressed += ('{0} [{1}; known-good at: {2}]' -f $id, $r.Action, (@($r.KnownGoodAt) -join ',' ))
            continue
        }

        if ($r.RestoreCanonical) {
            $srcPath = $null
            if ($r.RestoreFrom -eq 'git') {
                New-Item -ItemType Directory -Force -Path (Split-Path $fp) | Out-Null
                $rel = $fp.Substring($ccRepo.Length).TrimStart('\', '/') -replace '\\', '/'
                # WriteAllText with an explicit no-BOM encoder: Set-Content -Encoding UTF8
                # emits a BOM on Windows PowerShell 5.1, which would silently alter every
                # git-restored SKILL.md relative to its committed bytes.
                $blob = (& git -C $ccRepo show "HEAD:$rel") -join "`r`n"
                [System.IO.File]::WriteAllText($fp, $blob, (New-Object System.Text.UTF8Encoding($false)))
            } else {
                $srcPath = $mirrorPaths[$r.RestoreFrom]
                New-Item -ItemType Directory -Force -Path (Split-Path $fp) | Out-Null
                Copy-Item -LiteralPath $srcPath -Destination $fp -Force
            }
            $restored += ('{0} [from {1}; {2}]' -f $id, $r.RestoreFrom, $r.Reason)
        }

        if ($r.SyncMirrors) {
            foreach ($m in @($r.MirrorsToSync)) {
                $mp = $mirrorPaths[$m]
                New-Item -ItemType Directory -Force -Path (Split-Path $mp) | Out-Null
                Copy-Item -LiteralPath $fp -Destination $mp -Force
            }
            if ($backed -notcontains $id) { $backed += $id }
        }

        if ($r.NewCurrent) { $ledger[$id] = Update-TaskLedgerEntry $entry $r.NewCurrent }
    }

    Write-TaskLedger $ledgerPath $ledger (Get-Date).ToString('s')

    [ordered]@{
        checked            = $ids.Count
        restored           = @($restored)          # canonical was ABSENT and was rebuilt
        backed_up          = @($backed)            # mirrors refreshed from canonical
        missing_everywhere = @($missing)
        regressed          = @($regressed)         # canonical matches a recorded ANCESTOR -- NOT auto-fixed
        unreadable         = @($unreadable)        # canonical exists but could not be read -- untouched
        churn_suppressed   = @()                   # vestigial: kept for output-contract compatibility.
                                                   # Structurally always empty now -- mirrors are written
                                                   # iff content differs, so mtime churn cannot occur.
        ts                 = (Get-Date).ToString('s')
    } | ConvertTo-Json -Compress
} catch {
    Write-Output ('{"error":"' + ($_.Exception.Message -replace '"', '\"') + '"}')
    exit 1
}
