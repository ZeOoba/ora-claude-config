# Tests for task-integrity-lib.ps1's Resolve-TaskAction (TDD, 2026-08-09).
#
# WHY THIS EXISTS: on 2026-08-09 08:54:47 the integrity guard reverted live SKILL.md
# content for ora-health-guard, ora-task-integrity-guard and automation-health-monitor.
# Root cause: the engine picked a winner by newest MTIME across {canonical, gov mirror,
# local backup}. A mirror can carry OLDER CONTENT with a NEWER MTIME (OneDrive sync and
# bulk backup passes stamp mtimes without regard to content lineage), so mtime is not a
# version. This was the THIRD iteration of that bug class (mtime oscillation patched
# 2026-07-24, checked:0 silent no-op 2026-07-09), so the fix is NOT a fourth mtime
# heuristic: Resolve-TaskAction takes NO mtime input at all. Decisions come from a
# recorded content-hash ledger plus (where available) the git HEAD blob.
#
# Same PASS/FAIL-and-exit-code convention as the other PowerShell/Python suites here.

. (Join-Path $PSScriptRoot 'task-integrity-lib.ps1')

$script:failures = @()

function Check($label, [bool]$cond) {
    if ($cond) { Write-Output "PASS  $label" }
    else { Write-Output "FAIL  $label"; $script:failures += $label }
}

# Stand-in content hashes. Names encode lineage: OLD predates NEW.
$OLD  = 'aaaa000000000000000000000000000000000000000000000000000000000000'
$NEW  = 'bbbb111111111111111111111111111111111111111111111111111111111111'
$NEW2 = 'cccc222222222222222222222222222222222222222222222222222222222222'

function Ledger($current, $history) {
    return [PSCustomObject]@{ current = $current; history = @($history) }
}

# ---------------------------------------------------------------------------
# 1. THE INCIDENT. Canonical holds the CURRENT content; a mirror holds OLD content
#    (and, on 2026-08-09, a newer mtime). The engine must NOT touch canonical.
#    Resolve-TaskAction has no mtime parameter, so the stale mirror cannot win.
# ---------------------------------------------------------------------------
$r = Resolve-TaskAction -Id 'ora-health-guard' -CanonHash $NEW `
        -MirrorHashes @{ gov = $OLD; local = $OLD } -LedgerEntry (Ledger $NEW @($OLD, $NEW))
Check "INCIDENT: stale mirror never overwrites a current canonical" ($r.Action -eq 'ok' -and -not $r.RestoreCanonical)
Check "INCIDENT: stale mirrors are re-synced from canonical"        ($r.SyncMirrors -eq $true)

# ---------------------------------------------------------------------------
# 2. Canonical legitimately edited since last run -> ADOPT it, never revert it.
#    (An unrecognised-new hash is an edit, not corruption.)
# ---------------------------------------------------------------------------
$r = Resolve-TaskAction -Id 't' -CanonHash $NEW2 `
        -MirrorHashes @{ gov = $NEW; local = $NEW } -LedgerEntry (Ledger $NEW @($OLD, $NEW))
Check "new canonical content is adopted, not reverted" ($r.Action -eq 'adopt' -and -not $r.RestoreCanonical)
Check "adopt records the new hash as current"          ($r.NewCurrent -eq $NEW2)
Check "adopt is not an alarm"                          ($r.Alarm -eq $false)

# ---------------------------------------------------------------------------
# 3. LOAD-BEARING: a MISSING canonical must still be restored. This is the guard's
#    actual job -- a missing SKILL.md silently disables a task.
# ---------------------------------------------------------------------------
$r = Resolve-TaskAction -Id 't' -CanonHash $null `
        -MirrorHashes @{ gov = $OLD; local = $NEW } -LedgerEntry (Ledger $NEW @($OLD, $NEW))
Check "missing canonical IS restored"                  ($r.Action -eq 'restore' -and $r.RestoreCanonical)
Check "restore prefers the mirror holding known-good"  ($r.RestoreFrom -eq 'local')
Check "restoring a missing canonical alarms"           ($r.Alarm -eq $true)

# 3b. Missing canonical, ledger has no entry at all (first ever run) -> still restore.
$r = Resolve-TaskAction -Id 't' -CanonHash $null -MirrorHashes @{ gov = $OLD } -LedgerEntry $null
Check "missing canonical restored even with no ledger" ($r.Action -eq 'restore' -and $r.RestoreFrom -eq 'gov')
Check "no-ledger restore is flagged unverified"        ($r.Reason -match 'unverified_lineage')

# 3c. Missing canonical, no mirror holds known-good, but git HEAD does -> restore from git.
$r = Resolve-TaskAction -Id 't' -CanonHash $null -MirrorHashes @{ gov = $OLD; local = $OLD } `
        -LedgerEntry (Ledger $NEW @($OLD, $NEW)) -GitHeadHash $NEW
Check "missing canonical restored from git HEAD when mirrors are stale" `
    ($r.Action -eq 'restore' -and $r.RestoreFrom -eq 'git')

# 3d. Nothing anywhere -> missing_everywhere, alarm, no write.
$r = Resolve-TaskAction -Id 't' -CanonHash $null -MirrorHashes @{} -LedgerEntry $null
Check "nothing anywhere -> missing_everywhere" ($r.Action -eq 'missing_everywhere' -and $r.Alarm -eq $true)
Check "missing_everywhere writes nothing"      (-not $r.RestoreCanonical -and -not $r.SyncMirrors)

# ---------------------------------------------------------------------------
# 4. REGRESSION DETECTION (detect-only, never auto-write). Canonical has moved BACK
#    to a recorded ancestor while a mirror still holds the recorded current.
#    Alarm, but do NOT rewrite canonical: an operator may have reverted deliberately,
#    and a guard that "fixes" that is the very failure mode being removed here.
# ---------------------------------------------------------------------------
$r = Resolve-TaskAction -Id 't' -CanonHash $OLD `
        -MirrorHashes @{ gov = $NEW; local = $NEW } -LedgerEntry (Ledger $NEW @($OLD, $NEW))
Check "canonical regressed to an ancestor -> alarm"        ($r.Action -eq 'regression_detected' -and $r.Alarm)
Check "regression NEVER rewrites canonical"                (-not $r.RestoreCanonical)
Check "regression FREEZES mirror sync (last good copy)"    ($r.SyncMirrors -eq $false)
Check "regression names where known-good still lives"      ($r.KnownGoodAt -contains 'gov')

# 4b. Canonical regressed and NO copy anywhere holds the recorded current -> louder alarm.
$r = Resolve-TaskAction -Id 't' -CanonHash $OLD `
        -MirrorHashes @{ gov = $OLD; local = $OLD } -LedgerEntry (Ledger $NEW @($OLD, $NEW))
Check "known-good content lost everywhere -> distinct alarm" ($r.Action -eq 'known_good_lost' -and $r.Alarm)
Check "known_good_lost writes nothing"                       (-not $r.RestoreCanonical -and $r.SyncMirrors -eq $false)

# ---------------------------------------------------------------------------
# 5. First observation of a task the ledger has never seen -> trust canonical.
# ---------------------------------------------------------------------------
$r = Resolve-TaskAction -Id 't' -CanonHash $NEW -MirrorHashes @{ gov = $OLD } -LedgerEntry $null
Check "first observation adopts canonical" ($r.Action -eq 'adopt' -and $r.NewCurrent -eq $NEW -and -not $r.Alarm)

# 5b. FIRST-OBSERVATION SAFETY: with no baseline recorded, an EXISTING mirror is never
#     overwritten -- it may be the only surviving copy of the good content, and the guard
#     cannot yet tell a good canonical from an already-reverted one. An ABSENT mirror is
#     still created (that destroys nothing).
$r = Resolve-TaskAction -Id 't' -CanonHash $NEW -MirrorHashes @{ gov = $OLD; local = $null } -LedgerEntry $null
Check "first observation does NOT overwrite an existing mirror" ($r.MirrorsToSync -notcontains 'gov')
Check "first observation DOES create an absent mirror"          ($r.MirrorsToSync -contains 'local')

# 5c. Once a baseline exists, a stale mirror IS refreshed from canonical.
$r = Resolve-TaskAction -Id 't' -CanonHash $NEW -MirrorHashes @{ gov = $OLD; local = $OLD } -LedgerEntry (Ledger $NEW @($NEW))
Check "with a baseline, stale mirrors ARE refreshed" ($r.MirrorsToSync -contains 'gov' -and $r.MirrorsToSync -contains 'local')

# ---------------------------------------------------------------------------
# 6. Mirrors already in sync -> no redundant copying (the 2026-07-24 churn property
#    must survive: byte-identical mirrors are never rewritten).
# ---------------------------------------------------------------------------
$r = Resolve-TaskAction -Id 't' -CanonHash $NEW `
        -MirrorHashes @{ gov = $NEW; local = $NEW } -LedgerEntry (Ledger $NEW @($NEW))
Check "in-sync mirrors are not rewritten" ($r.Action -eq 'ok' -and $r.SyncMirrors -eq $false)

# ---------------------------------------------------------------------------
# 7. git HEAD disagreeing with a current canonical is EVIDENCE, never a write trigger.
#    A CC-fleet canonical that is legitimately ahead of the last commit must not be
#    dragged back to HEAD.
# ---------------------------------------------------------------------------
$r = Resolve-TaskAction -Id 't' -CanonHash $NEW2 `
        -MirrorHashes @{ gov = $NEW2; local = $NEW2 } -LedgerEntry (Ledger $NEW2 @($NEW, $NEW2)) `
        -GitHeadHash $NEW
Check "canonical ahead of git HEAD is left alone" ($r.Action -eq 'ok' -and -not $r.RestoreCanonical)

# ---------------------------------------------------------------------------
# 8. STRUCTURAL GUARANTEE: the decision function accepts no mtime input, so no future
#    caller can reintroduce a mtime heuristic without changing this signature.
# ---------------------------------------------------------------------------
$params = (Get-Command Resolve-TaskAction).Parameters.Keys
Check "Resolve-TaskAction takes no mtime/time parameter" (-not ($params -match 'time|mtime|date|stamp'))

# ---------------------------------------------------------------------------
# 9. A present canonical is NEVER overwritten, across every ledger shape.
#    Property check rather than another example.
# ---------------------------------------------------------------------------
$never = $true
foreach ($ch in @($OLD, $NEW, $NEW2)) {
  foreach ($cur in @($OLD, $NEW, $NEW2)) {
    foreach ($mir in @($OLD, $NEW, $NEW2)) {
      $rr = Resolve-TaskAction -Id 't' -CanonHash $ch -MirrorHashes @{ gov = $mir; local = $mir } `
              -LedgerEntry (Ledger $cur @($OLD, $NEW, $NEW2))
      if ($rr.RestoreCanonical) { $never = $false }
    }
  }
}
Check "PROPERTY: a canonical that EXISTS is never overwritten (27 combos)" $never

# ---------------------------------------------------------------------------
# 10. HISTORY IS UNBOUNDED. The old 40-entry cap silently turned a revert past the cap
#     into an adopt, which was then pushed over both mirrors -- destructive AND silent.
# ---------------------------------------------------------------------------
$entry = $null
$hashes = @()
for ($i = 0; $i -lt 60; $i++) {
    $h = ('{0:x2}' -f $i) * 32
    $hashes += $h
    $entry = Update-TaskLedgerEntry $entry $h $null $false
}
Check "history retains all 60 revisions (no cap)" (@($entry.history).Count -ge 60)
$r = Resolve-TaskAction -Id 't' -CanonHash $hashes[0] `
        -MirrorHashes @{ gov = $entry.current; local = $entry.current } -LedgerEntry $entry
Check "a revert to the OLDEST ancestor is still detected" ($r.Action -eq 'regression_detected')
Check "deep revert does not push to mirrors"              ($r.SyncMirrors -eq $false)

# ---------------------------------------------------------------------------
# 11. UNVERIFIED restore protects existing mirrors; VERIFIED restore refreshes them.
#     Gating on verified-ness, not on "has a baseline", is the fix: an unverified restore
#     is a guess, and overwriting a mirror with a guess destroys the last good copy.
# ---------------------------------------------------------------------------
$r = Resolve-TaskAction -Id 't' -CanonHash $null `
        -MirrorHashes @{ gov = $OLD; local = $NEW2 } -LedgerEntry (Ledger $NEW @($OLD, $NEW))
Check "unverified restore is marked unverified"        ($r.Verified -eq $false -and $r.Reason -match 'unverified')
Check "unverified restore leaves existing mirrors alone" ($r.MirrorsToSync -notcontains 'local')

$r = Resolve-TaskAction -Id 't' -CanonHash $null `
        -MirrorHashes @{ gov = $NEW; local = $OLD } -LedgerEntry (Ledger $NEW @($OLD, $NEW))
Check "verified restore is marked verified"             ($r.Verified -eq $true)
Check "verified restore DOES refresh the stale mirror"  ($r.MirrorsToSync -contains 'local')

# 11b. Git is preferred over mirrors when NO copy matches the known-good. Mirrors are what a
#      bulk backup pass poisons; git is version-controlled. Trying mirrors first let a poisoned
#      local backup beat a pristine git HEAD -- the 2026-08-09 shape.
$r = Resolve-TaskAction -Id 't' -CanonHash $null -MirrorHashes @{ gov = $OLD; local = $OLD } `
        -LedgerEntry $null -GitHeadHash $NEW2
Check "with no lineage, git outranks the mirrors" ($r.RestoreFrom -eq 'git')

# ---------------------------------------------------------------------------
# 12. A rollback that PERSISTS across runs is adopted, so the entry cannot stick in
#     regression_detected forever (which also left canonical restorable to the undone version).
# ---------------------------------------------------------------------------
$stuck = [PSCustomObject]@{ current = $NEW; history = @($OLD, $NEW); pending = $OLD }
$r = Resolve-TaskAction -Id 't' -CanonHash $OLD -MirrorHashes @{ gov = $NEW; local = $NEW } -LedgerEntry $stuck
Check "persisted rollback is adopted"            ($r.Action -eq 'adopt_after_regression')
Check "adopted rollback advances known-good"     ($r.NewCurrent -eq $OLD)
Check "adopted rollback still alarms"            ($r.Alarm -eq $true)
Check "adopted rollback propagates to mirrors"   ($r.MirrorsToSync -contains 'gov')

# 12b. First sighting sets pending and writes nothing.
$fresh = [PSCustomObject]@{ current = $NEW; history = @($OLD, $NEW) }
$r = Resolve-TaskAction -Id 't' -CanonHash $OLD -MirrorHashes @{ gov = $NEW; local = $NEW } -LedgerEntry $fresh
Check "first rollback sighting sets pending"     ($r.SetPending -eq $OLD)
Check "first rollback sighting writes nothing"   (-not $r.RestoreCanonical -and $r.SyncMirrors -eq $false)

# ---------------------------------------------------------------------------
if ($script:failures.Count -eq 0) {
    Write-Output ""
    Write-Output "ALL TESTS PASSED"
    exit 0
} else {
    Write-Output ""
    Write-Output ("FAILURES: " + $script:failures.Count)
    $script:failures | ForEach-Object { Write-Output "  - $_" }
    exit 1
}
