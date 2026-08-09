# ORA scheduled-task integrity guard -- decision core.
#
# POLARITY (the whole point): CANONICAL IS AUTHORITATIVE. Mirrors are DERIVED copies.
# The engine therefore writes canonical in exactly one situation -- canonical is ABSENT --
# and never otherwise. Everything else is either a mirror refresh from canonical, or a
# detect-only alarm.
#
# Why not "newest wins": mtime is not a version. OneDrive sync and bulk backup passes
# stamp mtimes without regard to content lineage, so a mirror can hold OLDER CONTENT with
# a NEWER MTIME. That is exactly what reverted three live SKILL.mds on 2026-08-09 08:54:47
# (the local backup carried mtime 2026-08-05 17:58:04 over pre-08-05 content, beat
# canonical, and was copied over it; Copy-Item preserves the source mtime, so the revert
# was invisible to any later mtime check).
#
# This is the THIRD iteration of the mtime bug class (oscillation 2026-07-24, checked:0
# silent no-op 2026-07-09), so a fourth mtime heuristic is the wrong shape of fix.
# Resolve-TaskAction accepts NO time input of any kind -- enforced by a test. Decisions
# are made from a recorded content-hash ledger (per task id) plus, where the canonical
# path is version-controlled, the git HEAD blob hash.
#
# Tests: maintenance/test-task-integrity-lib.ps1

# NOTE: deliberately no Set-StrictMode here. This file is dot-sourced INTO guard.ps1, so a
# strict mode set here would also govern guard.ps1's registry parsing, where reading a
# missing property (a scheduled-tasks.json entry with no filePath) must yield $null rather
# than throw -- `if ($t.id -and $t.filePath)` is load-bearing there.

# Deterministic mirror preference when several could serve as a restore source.
$script:MirrorOrder = @('gov', 'local')

function Get-OrderedMirrorNames($MirrorHashes) {
    $known = @($script:MirrorOrder | Where-Object { $MirrorHashes.ContainsKey($_) })
    $rest  = @($MirrorHashes.Keys | Where-Object { $script:MirrorOrder -notcontains $_ } | Sort-Object)
    return @($known + $rest)
}

function Resolve-TaskAction {
    <#
      .SYNOPSIS
        Decide what the guard should do for one task id, from content lineage alone.

      .OUTPUTS
        PSCustomObject with:
          Action           ok | adopt | restore | regression_detected | known_good_lost | missing_everywhere
          RestoreCanonical [bool]  write canonical? (true ONLY when canonical was absent)
          RestoreFrom      mirror name or 'git' -- the source to copy from
          SyncMirrors      [bool]  refresh mirrors from canonical?
          MirrorsToSync    names of mirrors whose content differs (or that are absent)
          NewCurrent       hash to record as the new ledger 'current' ($null = leave as is)
          KnownGoodAt      where the recorded 'current' content still exists
          Alarm            [bool]
          Reason           short machine-readable reason string
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Id,

        # SHA256 of the canonical file. $null/empty means the canonical file is ABSENT.
        [string]$CanonHash,

        # name -> SHA256 for every mirror location the caller manages.
        # Value $null/empty means that mirror file is absent.
        [hashtable]$MirrorHashes = @{},

        # Recorded lineage for this id: object with .current and .history. $null if unseen.
        $LedgerEntry = $null,

        # SHA256 of the git HEAD blob for the canonical path, when it is tracked.
        [string]$GitHeadHash
    )

    $names   = Get-OrderedMirrorNames $MirrorHashes
    $current = $null
    $history = @()
    if ($LedgerEntry) {
        if ($LedgerEntry.PSObject.Properties.Name -contains 'current') { $current = $LedgerEntry.current }
        if ($LedgerEntry.PSObject.Properties.Name -contains 'history') { $history = @($LedgerEntry.history) }
    }

    # Where does the recorded known-good content still physically exist?
    $knownGoodAt = @()
    if ($current) {
        foreach ($n in $names) { if ($MirrorHashes[$n] -eq $current) { $knownGoodAt += $n } }
        if ($GitHeadHash -and $GitHeadHash -eq $current) { $knownGoodAt += 'git' }
    }

    function New-Result($Action, $RestoreCanonical, $RestoreFrom, $SyncMirrors, $MirrorsToSync,
                        $NewCurrent, $KnownGoodAt, $Alarm, $Reason) {
        return [PSCustomObject]@{
            Id               = $Id
            Action           = $Action
            RestoreCanonical = [bool]$RestoreCanonical
            RestoreFrom      = $RestoreFrom
            SyncMirrors      = [bool]$SyncMirrors
            MirrorsToSync    = @($MirrorsToSync)
            NewCurrent       = $NewCurrent
            KnownGoodAt      = @($KnownGoodAt)
            Alarm            = [bool]$Alarm
            Reason           = $Reason
        }
    }

    # Mirrors whose content differs from a given hash (absent mirrors always need writing).
    function Get-StaleMirrors($Target) {
        return @($names | Where-Object { $MirrorHashes[$_] -ne $Target })
    }

    # Mirrors that do not exist at all.
    function Get-AbsentMirrors() {
        return @($names | Where-Object { -not $MirrorHashes[$_] })
    }

    # UNTIL A LINEAGE BASELINE EXISTS, MIRRORS ARE READ-ONLY except for creating one that
    # is missing outright. Rationale: on the guard's first sight of a task id it has no way
    # to tell a good canonical from an already-reverted one, and a differing mirror may be
    # the ONLY surviving copy of the good content. Overwriting it would destroy the evidence
    # before the ledger ever records it -- the same class of irreversible loss this rewrite
    # exists to prevent. One extra cycle of mirror staleness is a cheap price.
    function Get-MirrorsToWrite($Target, [bool]$HasBaseline) {
        if ($HasBaseline) { return @(Get-StaleMirrors $Target) }
        return @(Get-AbsentMirrors)
    }

    # =======================================================================
    # CASE 1 -- CANONICAL IS ABSENT. Restoring it is the guard's load-bearing
    # job: a missing SKILL.md silently disables a task. This is the ONLY path
    # that writes canonical.
    # =======================================================================
    if (-not $CanonHash) {
        $src = $null; $reason = $null

        # (a) Prefer a copy that provably holds the recorded known-good content.
        if ($current) {
            foreach ($n in $names) {
                if ($MirrorHashes[$n] -eq $current) { $src = $n; $reason = 'restored_from_known_good'; break }
            }
            if (-not $src -and $GitHeadHash -and $GitHeadHash -eq $current) {
                $src = 'git'; $reason = 'restored_from_git_known_good'
            }
        }

        # (b) No lineage evidence -- fall back to any available copy, deterministic order.
        #     Flagged so the caller can report that the restore was not lineage-verified.
        if (-not $src) {
            foreach ($n in $names) {
                if ($MirrorHashes[$n]) { $src = $n; $reason = 'restored_unverified_lineage'; break }
            }
            if (-not $src -and $GitHeadHash) { $src = 'git'; $reason = 'restored_unverified_lineage' }
        }

        if (-not $src) {
            return New-Result 'missing_everywhere' $false $null $false @() $null $knownGoodAt $true `
                              'no copy of this task definition exists in any location'
        }

        $restoredHash = $null
        if ($src -eq 'git') { $restoredHash = $GitHeadHash } else { $restoredHash = $MirrorHashes[$src] }
        $write = @(Get-MirrorsToWrite $restoredHash ([bool]$current))
        return New-Result 'restore' $true $src ($write.Count -gt 0) $write $restoredHash $knownGoodAt $true $reason
    }

    # =======================================================================
    # CASE 2 -- CANONICAL EXISTS. It is never overwritten. Past here the engine
    # can only refresh mirrors, or alarm.
    # =======================================================================

    # 2a. Never seen before -> trust canonical and start its lineage.
    if (-not $current) {
        $write = @(Get-MirrorsToWrite $CanonHash $false)
        return New-Result 'adopt' $false $null ($write.Count -gt 0) $write $CanonHash $knownGoodAt $false `
                          'first observation of this task id -- canonical adopted as baseline; existing mirrors left untouched'
    }

    # 2b. Canonical matches the recorded known-good -> steady state.
    if ($CanonHash -eq $current) {
        $stale = @(Get-StaleMirrors $CanonHash)
        return New-Result 'ok' $false $null ($stale.Count -gt 0) $stale $null $knownGoodAt $false 'in_sync'
    }

    # 2c. Canonical holds content never recorded before -> a legitimate edit landed
    #     since the last run. Adopt it. This is the branch the 2026-08-09 incident
    #     needed and did not have: under newest-wins, an edited canonical whose mtime
    #     lost to a bulk-stamped mirror was silently reverted instead of adopted.
    if ($history -notcontains $CanonHash) {
        $stale = @(Get-StaleMirrors $CanonHash)
        return New-Result 'adopt' $false $null ($stale.Count -gt 0) $stale $CanonHash $knownGoodAt $false `
                          'canonical changed since last run -- adopted as new known-good'
    }

    # 2d. Canonical has moved BACK to a recorded ancestor. Report it; do not "fix" it.
    #     An operator may have reverted deliberately, and a guard that silently undoes
    #     that is the exact failure mode being removed. Mirror sync is FROZEN so the
    #     regressed content cannot overwrite the last good copy.
    if ($knownGoodAt.Count -gt 0) {
        return New-Result 'regression_detected' $false $null $false @() $null $knownGoodAt $true `
                          'canonical content matches a recorded ANCESTOR -- known-good still available'
    }

    return New-Result 'known_good_lost' $false $null $false @() $null @() $true `
                      'canonical regressed to an ancestor and the recorded known-good exists nowhere'
}

# ---------------------------------------------------------------------------
# Ledger persistence. The ledger is the guard's memory of content lineage; it is
# what makes "newer" a recorded fact rather than a filesystem guess.
# ---------------------------------------------------------------------------

$script:LedgerHistoryCap = 40

function Read-TaskLedger([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return @{} }
    try {
        $raw = Get-Content -LiteralPath $Path -Raw
        if (-not $raw -or -not $raw.Trim()) { return @{} }
        $j = $raw | ConvertFrom-Json
        $out = @{}
        if ($j.PSObject.Properties.Name -contains 'tasks' -and $j.tasks) {
            foreach ($p in $j.tasks.PSObject.Properties) { $out[$p.Name] = $p.Value }
        }
        return $out
    } catch {
        # A corrupt ledger must not brick the guard. Empty ledger == "trust canonical",
        # which is the safe direction: it can never cause a revert, only a lost alarm.
        return @{}
    }
}

function Update-TaskLedgerEntry($Entry, [string]$NewCurrent) {
    $history = @()
    $current = $null
    if ($Entry) {
        if ($Entry.PSObject.Properties.Name -contains 'history') { $history = @($Entry.history) }
        if ($Entry.PSObject.Properties.Name -contains 'current') { $current = $Entry.current }
    }
    if ($current -and $history -notcontains $current) { $history += $current }
    if ($NewCurrent -and $history -notcontains $NewCurrent) { $history += $NewCurrent }
    if ($history.Count -gt $script:LedgerHistoryCap) {
        $history = @($history[($history.Count - $script:LedgerHistoryCap)..($history.Count - 1)])
    }
    $final = $current
    if ($NewCurrent) { $final = $NewCurrent }
    return [PSCustomObject]@{ current = $final; history = @($history) }
}

function Write-TaskLedger([string]$Path, $Ledger, [string]$Stamp) {
    $tasks = [ordered]@{}
    foreach ($k in ($Ledger.Keys | Sort-Object)) { $tasks[$k] = $Ledger[$k] }
    $doc = [ordered]@{ version = 1; updated = $Stamp; tasks = $tasks }
    $dir = Split-Path $Path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    $tmp = "$Path.tmp"
    $doc | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $tmp -Encoding UTF8
    Move-Item -LiteralPath $tmp -Destination $Path -Force
}
