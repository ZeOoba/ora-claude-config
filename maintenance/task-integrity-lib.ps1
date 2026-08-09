# ORA scheduled-task integrity guard -- decision core.
#
# POLARITY (the whole point): CANONICAL IS AUTHORITATIVE. Mirrors are DERIVED copies.
# The engine writes canonical in exactly one situation -- canonical is ABSENT -- and never
# otherwise. Everything else is either a mirror refresh from canonical, or a detect-only alarm.
#
# Why not "newest wins": mtime is not a version. OneDrive sync and bulk backup passes stamp
# mtimes without regard to content lineage, so a mirror can hold OLDER CONTENT with a NEWER
# MTIME. That reverted three live SKILL.mds on 2026-08-09 08:54:47 (the local backup carried
# mtime 2026-08-05 17:58:04 over pre-08-05 content, beat canonical, and was copied over it;
# Copy-Item preserves the source mtime, so the revert was invisible afterwards).
#
# THIRD iteration of the mtime bug class (oscillation 2026-07-24, checked:0 2026-07-09), so a
# fourth mtime heuristic is the wrong shape of fix. Resolve-TaskAction accepts NO time input --
# test-enforced. "Newer" comes from a recorded content-hash ledger plus the git HEAD blob.
#
# HARDENED 2026-08-09 after an independent review + adversarial REFUTE pass. Protecting
# canonical alone was NOT sufficient -- the review broke the engine three ways that all end in
# the same irreversible loss:
#   R3  an UNVERIFIED restore (no lineage evidence) then overwrote the mirrors, destroying the
#       only surviving good copy. Mirror protection was gated on "is there a baseline" when the
#       thing that actually matters is "was this restore a guess".
#   R4  a 0-byte canonical hashes to the SHA of the empty string -- a VALID hash -- so truncation
#       was adopted as legitimate content and pushed over both backups.
#   R5  a deliberate rollback stuck in regression_detected forever (current never advanced), and
#       if canonical was later lost the guard "restored" the operator's rollback away.
#   R6  past the history cap a revert silently became an adopt and was propagated.
# Mirrors are now protected on VERIFIED-ness, a rollback that persists across runs is adopted,
# and history is unbounded.
#
# Tests: maintenance/test-task-integrity-lib.ps1 (core) + test-guard-integrity-engine.ps1 (engine)

# NOTE: deliberately no Set-StrictMode. This file is dot-sourced INTO guard.ps1, so a strict
# mode set here would also govern guard.ps1's registry parsing, where reading a missing property
# (an entry with no filePath) must yield $null rather than throw.

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
      .NOTES
        CanonHash / mirror hashes must be $null for a file that is absent OR unusable
        (0 bytes, unreadable). The caller owns that mapping -- see guard.ps1.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Id,
        [string]$CanonHash,
        [hashtable]$MirrorHashes = @{},
        $LedgerEntry = $null,
        [string]$GitHeadHash
    )

    $names   = Get-OrderedMirrorNames $MirrorHashes
    $current = $null; $history = @(); $pending = $null
    if ($LedgerEntry) {
        $p = $LedgerEntry.PSObject.Properties.Name
        if ($p -contains 'current') { $current = $LedgerEntry.current }
        if ($p -contains 'history') { $history = @($LedgerEntry.history) }
        if ($p -contains 'pending') { $pending = $LedgerEntry.pending }
    }

    $knownGoodAt = @()
    if ($current) {
        foreach ($n in $names) { if ($MirrorHashes[$n] -eq $current) { $knownGoodAt += $n } }
        if ($GitHeadHash -and $GitHeadHash -eq $current) { $knownGoodAt += 'git' }
    }

    function New-Result($o) {
        $d = @{ Id = $Id; Action = $null; RestoreCanonical = $false; RestoreFrom = $null
                SyncMirrors = $false; MirrorsToSync = @(); NewCurrent = $null
                SetPending = $null; ClearPending = $false
                KnownGoodAt = @($knownGoodAt); Alarm = $false; Reason = $null; Verified = $false }
        foreach ($k in $o.Keys) { $d[$k] = $o[$k] }
        $d.MirrorsToSync = @($d.MirrorsToSync)
        $d.KnownGoodAt   = @($d.KnownGoodAt)
        return [PSCustomObject]$d
    }

    function Get-StaleMirrors($Target)  { return @($names | Where-Object { $MirrorHashes[$_] -ne $Target }) }
    function Get-AbsentMirrors()        { return @($names | Where-Object { -not $MirrorHashes[$_] }) }

    # =====================================================================
    # CASE 1 -- CANONICAL ABSENT. The guard's load-bearing job; the ONLY path
    # that writes canonical.
    # =====================================================================
    if (-not $CanonHash) {
        $src = $null; $reason = $null; $verified = $false

        # (a) A copy that PROVABLY holds the recorded known-good content.
        if ($current) {
            foreach ($n in $names) {
                if ($MirrorHashes[$n] -eq $current) { $src = $n; $reason = 'restored_from_known_good'; $verified = $true; break }
            }
            if (-not $src -and $GitHeadHash -and $GitHeadHash -eq $current) {
                $src = 'git'; $reason = 'restored_from_git_known_good'; $verified = $true
            }
        }

        # (b) No lineage evidence. GIT FIRST (REFUTE R2): it is version-controlled and
        #     tamper-resistant, whereas a mirror is precisely what gets poisoned by a bulk
        #     backup pass. Trying mirrors first let a poisoned local backup beat a pristine
        #     git HEAD -- the 2026-08-09 shape, reintroduced.
        if (-not $src) {
            if ($GitHeadHash) { $src = 'git'; $reason = 'restored_unverified_lineage_from_git' }
            else {
                foreach ($n in $names) {
                    if ($MirrorHashes[$n]) { $src = $n; $reason = 'restored_unverified_lineage'; break }
                }
            }
        }

        if (-not $src) {
            return New-Result @{ Action = 'missing_everywhere'; Alarm = $true
                                 Reason = 'no usable copy of this task definition exists in any location' }
        }

        $restoredHash = if ($src -eq 'git') { $GitHeadHash } else { $MirrorHashes[$src] }

        # MIRROR PROTECTION IS GATED ON VERIFIED-NESS, NOT ON HAVING A BASELINE (REFUTE R3).
        # An unverified restore is a GUESS. Overwriting mirrors with a guess destroys the only
        # surviving good copy -- reproduced: a mirror holding the sole unrecorded-good version
        # was overwritten with ancient content pulled from the other mirror. When unverified we
        # only CREATE mirrors that are missing outright; that destroys nothing.
        $write = if ($verified) { @(Get-StaleMirrors $restoredHash) } else { @(Get-AbsentMirrors) }

        return New-Result @{ Action = 'restore'; RestoreCanonical = $true; RestoreFrom = $src
                             SyncMirrors = ($write.Count -gt 0); MirrorsToSync = $write
                             NewCurrent = $restoredHash; Alarm = $true; Reason = $reason; Verified = $verified }
    }

    # =====================================================================
    # CASE 2 -- CANONICAL EXISTS. Never overwritten. Only mirror refresh or alarm.
    # =====================================================================

    # 2a. Never seen. Trust canonical, but do NOT overwrite an existing differing mirror --
    #     without a baseline the guard cannot tell a good canonical from an already-reverted
    #     one, and that mirror may be the only surviving good copy.
    if (-not $current) {
        $write = @(Get-AbsentMirrors)
        return New-Result @{ Action = 'adopt'; SyncMirrors = ($write.Count -gt 0); MirrorsToSync = $write
                             NewCurrent = $CanonHash; ClearPending = $true
                             Reason = 'first observation -- canonical adopted as baseline; existing mirrors untouched' }
    }

    # 2b. Steady state.
    if ($CanonHash -eq $current) {
        $stale = @(Get-StaleMirrors $CanonHash)
        return New-Result @{ Action = 'ok'; SyncMirrors = ($stale.Count -gt 0); MirrorsToSync = $stale
                             ClearPending = $true; Reason = 'in_sync' }
    }

    # 2c. Content never recorded before -> a legitimate edit landed since the last run.
    #     This is the branch the 2026-08-09 incident needed and did not have.
    if ($history -notcontains $CanonHash) {
        $stale = @(Get-StaleMirrors $CanonHash)
        return New-Result @{ Action = 'adopt'; SyncMirrors = ($stale.Count -gt 0); MirrorsToSync = $stale
                             NewCurrent = $CanonHash; ClearPending = $true
                             Reason = 'canonical changed since last run -- adopted as new known-good' }
    }

    # 2d. Canonical has moved BACK to a recorded ancestor.
    #     If it ALSO held that ancestor on the previous run, the rollback has persisted across
    #     runs and is deliberate -- adopt it (REFUTE R5). Without this the entry stuck in
    #     regression_detected forever, and a later loss of canonical "restored" the operator's
    #     rollback away through the permitted absent-canonical door.
    if ($pending -and $pending -eq $CanonHash) {
        $stale = @(Get-StaleMirrors $CanonHash)
        return New-Result @{ Action = 'adopt_after_regression'; SyncMirrors = ($stale.Count -gt 0)
                             MirrorsToSync = $stale; NewCurrent = $CanonHash; ClearPending = $true; Alarm = $true
                             Reason = 'canonical held a recorded ancestor across two consecutive runs -- treated as a deliberate rollback and adopted' }
    }

    # First sighting of the rollback: report it, write nothing, and FREEZE mirror sync so the
    # regressed content cannot overwrite the last good copy.
    if ($knownGoodAt.Count -gt 0) {
        return New-Result @{ Action = 'regression_detected'; SetPending = $CanonHash; Alarm = $true
                             Reason = 'canonical content matches a recorded ANCESTOR -- known-good still available' }
    }
    return New-Result @{ Action = 'known_good_lost'; SetPending = $CanonHash; Alarm = $true
                         Reason = 'canonical regressed to an ancestor and the recorded known-good exists nowhere' }
}

# ---------------------------------------------------------------------------
# Ledger persistence -- the guard's memory of content lineage.
# ---------------------------------------------------------------------------

function Read-TaskLedger([string]$Path) {
    # Returns @{ Tasks = @{}; Status = 'ok'|'absent'|'unreadable' }.
    # Status is REPORTED by the caller and alarmed on. An empty ledger silently means
    # "trust every canonical", which is safe for canonical but turns regression detection
    # OFF for that run -- a zero that could mean "couldn't look" is a failure, not a pass
    # (feedback_verified_null_vs_inferred_null.md).
    if (-not (Test-Path -LiteralPath $Path)) { return @{ Tasks = @{}; Status = 'absent' } }
    try {
        $raw = Get-Content -LiteralPath $Path -Raw -ErrorAction Stop
        if (-not $raw -or -not $raw.Trim()) { return @{ Tasks = @{}; Status = 'unreadable' } }
        $j = $raw | ConvertFrom-Json
        $out = @{}
        if ($j.PSObject.Properties.Name -contains 'tasks' -and $j.tasks -and
            $j.tasks -isnot [string] -and $j.tasks -isnot [bool]) {
            foreach ($p in $j.tasks.PSObject.Properties) { $out[$p.Name] = $p.Value }
            return @{ Tasks = $out; Status = 'ok' }
        }
        return @{ Tasks = @{}; Status = 'unreadable' }
    } catch { return @{ Tasks = @{}; Status = 'unreadable' } }
}

function Update-TaskLedgerEntry($Entry, [string]$NewCurrent, [string]$SetPending, [bool]$ClearPending) {
    $history = @(); $current = $null; $pending = $null
    if ($Entry) {
        $p = $Entry.PSObject.Properties.Name
        if ($p -contains 'history') { $history = @($Entry.history) }
        if ($p -contains 'current') { $current = $Entry.current }
        if ($p -contains 'pending') { $pending = $Entry.pending }
    }
    if ($current -and $history -notcontains $current) { $history += $current }
    if ($NewCurrent -and $history -notcontains $NewCurrent) { $history += $NewCurrent }
    # HISTORY IS UNBOUNDED (REFUTE R6). The old 40-entry cap silently turned a revert past the
    # cap into an adopt that was then pushed over both mirrors. These are 64-char strings; the
    # storage is trivial next to losing revert detection without any signal.
    $final = if ($NewCurrent) { $NewCurrent } else { $current }
    $newPending = if ($ClearPending) { $null } elseif ($SetPending) { $SetPending } else { $pending }
    return [PSCustomObject]@{ current = $final; history = @($history); pending = $newPending }
}

function Write-TaskLedger([string]$Path, $Tasks, [string]$Stamp) {
    $ordered = [ordered]@{}
    foreach ($k in ($Tasks.Keys | Sort-Object)) { $ordered[$k] = $Tasks[$k] }
    $doc = [ordered]@{ version = 2; updated = $Stamp; tasks = $ordered }
    $dir = Split-Path $Path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    # Per-process temp name (REFUTE R7): two scheduled callers run this engine daily, and a
    # catch-up burst can overlap them. A fixed "$Path.tmp" made concurrent runs either kill each
    # other ("being used by another process") or move a half-written file into place.
    $tmp = "$Path.$PID.tmp"
    $doc | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $tmp -Encoding UTF8
    Move-Item -LiteralPath $tmp -Destination $Path -Force
}
