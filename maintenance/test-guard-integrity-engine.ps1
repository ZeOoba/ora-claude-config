# End-to-end tests for scheduled-tasks/ora-task-integrity-guard/guard.ps1 (TDD, 2026-08-09).
#
# The pure decision core is covered by test-task-integrity-lib.ps1. THIS suite drives the
# REAL engine against synthetic fixtures in a temp dir, because the 2026-08-09 revert was a
# wiring-level failure (which copy gets written over which), not a logic-level one.
#
# Scenario 1 replays the incident exactly: a mirror holding OLDER CONTENT with a NEWER
# MTIME. Under the old newest-wins engine that mirror overwrote canonical. It must not now.
#
# Never touches live paths -- every root is injected via the engine's -*Override params.

$script:failures = @()
function Check($label, [bool]$cond) {
    if ($cond) { Write-Output "PASS  $label" }
    else { Write-Output "FAIL  $label"; $script:failures += $label }
}

$guard = Join-Path $PSScriptRoot '..\scheduled-tasks\ora-task-integrity-guard\guard.ps1'
if (-not (Test-Path -LiteralPath $guard)) { Write-Output "FAIL  cannot locate guard.ps1 at $guard"; exit 1 }

$NEW_CONTENT = "# SKILL v2 -- the 2026-08-05 rewrite that must survive`nlocal-first beacon`n"
$OLD_CONTENT = "# SKILL v1 -- superseded 2026-08-03 text`n"

function New-Fixture {
    param([string]$Root, [string]$CanonContent, [string]$GovContent, [string]$LocalContent)

    $canonDir = Join-Path $Root 'canon\t1'
    $govDir   = Join-Path $Root 'gov'
    $locDir   = Join-Path $Root 'local'
    $storeDir = Join-Path $Root 'store\cc-sessions\aaa\bbb'
    foreach ($d in @($canonDir, (Join-Path $govDir 't1'), (Join-Path $locDir 't1'), $storeDir)) {
        New-Item -ItemType Directory -Force -Path $d | Out-Null
    }
    $canonFile = Join-Path $canonDir 'SKILL.md'

    if ($null -ne $CanonContent) { Set-Content -LiteralPath $canonFile -Value $CanonContent -NoNewline }
    if ($null -ne $GovContent)   { Set-Content -LiteralPath (Join-Path $govDir 't1\SKILL.md')   -Value $GovContent   -NoNewline }
    if ($null -ne $LocalContent) { Set-Content -LiteralPath (Join-Path $locDir 't1\SKILL.md')   -Value $LocalContent -NoNewline }

    $reg = @{ scheduledTasks = @(@{ id = 't1'; filePath = $canonFile }) }
    $reg | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $storeDir 'scheduled-tasks.json')

    return [PSCustomObject]@{
        CanonFile = $canonFile
        Gov       = $govDir
        Local     = $locDir
        Store     = (Join-Path $Root 'store')
        Ledger    = (Join-Path $Root 'ledger.json')
    }
}

function Invoke-Guard($fx) {
    return & $guard -GovOverride $fx.Gov -LocalOverride $fx.Local `
                    -LedgerPathOverride $fx.Ledger -StoreRootsOverride @($fx.Store) `
                    -CcRepoOverride (Join-Path $env:TEMP 'no-such-repo')
}

function New-TempRoot {
    $p = Join-Path $env:TEMP ("guard-test-" + [Guid]::NewGuid().ToString('N').Substring(0, 8))
    New-Item -ItemType Directory -Force -Path $p | Out-Null
    return $p
}

# ===========================================================================
# 1. THE INCIDENT REPLAY. Canonical holds the NEW content with an OLD mtime;
#    the local backup holds OLD content stamped with a NEWER mtime (exactly the
#    2026-08-09 shape: local mtime 08-05 17:58:04 over pre-08-05 content).
#    The old engine copied the mirror over canonical. This must not happen.
# ===========================================================================
$root = New-TempRoot
$fx = New-Fixture -Root $root -CanonContent $NEW_CONTENT -GovContent $OLD_CONTENT -LocalContent $OLD_CONTENT

# Make the stale mirrors look NEWER than canonical on the filesystem.
(Get-Item -LiteralPath $fx.CanonFile).LastWriteTime            = Get-Date '2026-08-05T09:00:00'
(Get-Item -LiteralPath "$($fx.Gov)\t1\SKILL.md").LastWriteTime = Get-Date '2026-08-05T17:58:04'
(Get-Item -LiteralPath "$($fx.Local)\t1\SKILL.md").LastWriteTime = Get-Date '2026-08-05T17:58:04'

$out  = Invoke-Guard $fx | ConvertFrom-Json
$after = Get-Content -LiteralPath $fx.CanonFile -Raw

Check "INCIDENT REPLAY: canonical content SURVIVES a newer-mtime stale mirror" ($after -eq $NEW_CONTENT)
Check "INCIDENT REPLAY: nothing reported as restored"                          (@($out.restored).Count -eq 0)
Check "INCIDENT REPLAY: engine reported a non-zero checked count"              ($out.checked -ge 1)

# FIRST-OBSERVATION SAFETY: with no ledger baseline yet, an existing mirror is NOT
# overwritten -- it may be the only surviving copy of the good content, and the guard
# cannot yet tell a good canonical from an already-reverted one.
Check "first run leaves existing mirrors untouched" `
    ((Get-Content -LiteralPath "$($fx.Gov)\t1\SKILL.md" -Raw) -eq $OLD_CONTENT)

# SECOND run: a baseline now exists, so the stale mirrors are refreshed FROM canonical.
$out2 = Invoke-Guard $fx | ConvertFrom-Json
Check "second run re-syncs the stale mirrors from canonical" (@($out2.backed_up) -contains 't1')
Check "second run: gov mirror now holds the NEW content" `
    ((Get-Content -LiteralPath "$($fx.Gov)\t1\SKILL.md" -Raw) -eq $NEW_CONTENT)
Check "second run: local mirror now holds the NEW content" `
    ((Get-Content -LiteralPath "$($fx.Local)\t1\SKILL.md" -Raw) -eq $NEW_CONTENT)
Check "second run: canonical still intact"                   ((Get-Content -LiteralPath $fx.CanonFile -Raw) -eq $NEW_CONTENT)
Check "second run restores nothing"                          (@($out2.restored).Count -eq 0)

# THIRD run must be a clean no-op -- no oscillation (the 2026-07-24 property).
$out3 = Invoke-Guard $fx | ConvertFrom-Json
Check "third run is a no-op: nothing restored"  (@($out3.restored).Count -eq 0)
Check "third run is a no-op: nothing backed up" (@($out3.backed_up).Count -eq 0)
Check "third run: canonical still intact"       ((Get-Content -LiteralPath $fx.CanonFile -Raw) -eq $NEW_CONTENT)
Remove-Item -Recurse -Force $root

# ===========================================================================
# 2. LOAD-BEARING: a MISSING canonical is still restored, and the ledger's
#    known-good is preferred over a stale mirror.
# ===========================================================================
$root = New-TempRoot
$fx = New-Fixture -Root $root -CanonContent $NEW_CONTENT -GovContent $NEW_CONTENT -LocalContent $NEW_CONTENT
Invoke-Guard $fx | Out-Null                                   # run 1: records NEW as known-good

Set-Content -LiteralPath "$($fx.Local)\t1\SKILL.md" -Value $OLD_CONTENT -NoNewline   # poison one mirror
Remove-Item -LiteralPath $fx.CanonFile -Force                                        # canonical disappears

$out = Invoke-Guard $fx | ConvertFrom-Json
Check "MISSING canonical is restored"                    (Test-Path -LiteralPath $fx.CanonFile)
Check "MISSING canonical restored to the KNOWN-GOOD content" `
    ((Get-Content -LiteralPath $fx.CanonFile -Raw) -eq $NEW_CONTENT)
Check "MISSING canonical restore is reported (alarm path)" (@($out.restored).Count -eq 1)
Check "restore is attributed to the known-good source"     (@($out.restored)[0] -match 'known_good')
Remove-Item -Recurse -Force $root

# ===========================================================================
# 3. A legitimate edit to canonical is ADOPTED and propagated, never reverted.
# ===========================================================================
$root = New-TempRoot
$fx = New-Fixture -Root $root -CanonContent $OLD_CONTENT -GovContent $OLD_CONTENT -LocalContent $OLD_CONTENT
Invoke-Guard $fx | Out-Null                                   # baseline
Set-Content -LiteralPath $fx.CanonFile -Value $NEW_CONTENT -NoNewline
$out = Invoke-Guard $fx | ConvertFrom-Json
Check "edited canonical is kept"          ((Get-Content -LiteralPath $fx.CanonFile -Raw) -eq $NEW_CONTENT)
Check "edited canonical propagates to gov" ((Get-Content -LiteralPath "$($fx.Gov)\t1\SKILL.md" -Raw) -eq $NEW_CONTENT)
Check "adopting an edit is not an alarm"  (@($out.restored).Count -eq 0 -and @($out.regressed).Count -eq 0)
Remove-Item -Recurse -Force $root

# ===========================================================================
# 4. A DELIBERATE revert of canonical to a recorded ancestor is DETECTED and
#    REPORTED, but not silently undone -- and mirror sync freezes so the last
#    good copy is not overwritten by the regressed content.
# ===========================================================================
$root = New-TempRoot
$fx = New-Fixture -Root $root -CanonContent $OLD_CONTENT -GovContent $OLD_CONTENT -LocalContent $OLD_CONTENT
Invoke-Guard $fx | Out-Null                                   # ancestor recorded
Set-Content -LiteralPath $fx.CanonFile -Value $NEW_CONTENT -NoNewline
Invoke-Guard $fx | Out-Null                                   # NEW is now known-good, mirrors = NEW
Set-Content -LiteralPath $fx.CanonFile -Value $OLD_CONTENT -NoNewline   # someone reverts canonical
$out = Invoke-Guard $fx | ConvertFrom-Json

Check "regression to a recorded ancestor is REPORTED" (@($out.regressed).Count -eq 1)
Check "regression is NOT silently undone"             ((Get-Content -LiteralPath $fx.CanonFile -Raw) -eq $OLD_CONTENT)
Check "regression FREEZES mirror sync (gov keeps known-good)" `
    ((Get-Content -LiteralPath "$($fx.Gov)\t1\SKILL.md" -Raw) -eq $NEW_CONTENT)
Remove-Item -Recurse -Force $root

# ===========================================================================
# 5. The checked==0 self-check (2026-07-09) must still fire and exit non-zero.
# ===========================================================================
$root = New-TempRoot
New-Item -ItemType Directory -Force -Path (Join-Path $root 'empty-store') | Out-Null
$o = & $guard -GovOverride (Join-Path $root 'g') -LocalOverride (Join-Path $root 'l') `
              -LedgerPathOverride (Join-Path $root 'led.json') `
              -StoreRootsOverride @((Join-Path $root 'empty-store')) `
              -CcRepoOverride (Join-Path $env:TEMP 'no-such-repo')
$code = $LASTEXITCODE
Check "checked==0 still reported as an engine error" ($o -match 'checked==0')
Check "checked==0 still exits non-zero"              ($code -ne 0)
Remove-Item -Recurse -Force $root

# ===========================================================================
# 6. A registry entry with no filePath must be skipped, not throw. Real registries
#    carry malformed/partial entries, and `if ($t.id -and $t.filePath)` only works
#    while property access on a missing member yields $null.
# ===========================================================================
$root = New-TempRoot
$fx = New-Fixture -Root $root -CanonContent $NEW_CONTENT -GovContent $NEW_CONTENT -LocalContent $NEW_CONTENT
$storeDir = Join-Path $root 'store\cc-sessions\aaa\bbb'
@{ scheduledTasks = @(
      @{ id = 't1'; filePath = $fx.CanonFile },
      @{ id = 'no-path-task' },
      @{ filePath = 'C:\nowhere\SKILL.md' }
) } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $storeDir 'scheduled-tasks.json')

$ok = $true
try { $out = Invoke-Guard $fx | ConvertFrom-Json } catch { $ok = $false }
Check "malformed registry entries do not throw"        $ok
Check "malformed entries are skipped, valid one kept"  ($ok -and $out.checked -eq 1)
Check "canonical untouched despite malformed siblings" ((Get-Content -LiteralPath $fx.CanonFile -Raw) -eq $NEW_CONTENT)
Remove-Item -Recurse -Force $root

# ===========================================================================
# 7. GIT RESTORE PATH -- the one place the engine writes bytes it CONSTRUCTED rather
#    than copied, and the path every earlier scenario disabled via -CcRepoOverride to a
#    nonexistent repo. That blind spot hid a corruption bug: `& git show` output is decoded
#    through [Console]::OutputEncoding (IBM437 unattended), mangling every non-ASCII char.
#    ORA SKILL.mds are full of them, so this fixture uses ORA house style deliberately.
# ===========================================================================
$root = New-TempRoot
$repo = Join-Path $root 'repo'
$canonDir = Join-Path $repo 'scheduled-tasks\t1'
New-Item -ItemType Directory -Force -Path $canonDir | Out-Null
$canonFile = Join-Path $canonDir 'SKILL.md'
$UNICODE = "# ORA task`n" + [char]0x2014 + " em-dash, " + [char]0x2192 + " arrow, " +
           [char]0x201C + "curly" + [char]0x201D + ", " + [char]0x2265 + " ge, " + [char]0x00B7 + " mid`n"
[System.IO.File]::WriteAllText($canonFile, $UNICODE, (New-Object System.Text.UTF8Encoding($false)))
$committed = [System.IO.File]::ReadAllBytes($canonFile)

Push-Location $repo
& git init -q . 2>$null
& git add -A 2>$null
& git -c user.email=t@ora -c user.name=t commit -qm fixture 2>$null
Pop-Location

$govD = Join-Path $root 'gov'; $locD = Join-Path $root 'local'
$storeDir = Join-Path $root 'store\cc-sessions\aaa\bbb'
New-Item -ItemType Directory -Force -Path $storeDir | Out-Null
@{ scheduledTasks = @(@{ id = 't1'; filePath = $canonFile }) } | ConvertTo-Json -Depth 5 |
    Set-Content -LiteralPath (Join-Path $storeDir 'scheduled-tasks.json')
$fxg = [PSCustomObject]@{ Gov = $govD; Local = $locD; Store = (Join-Path $root 'store'); Ledger = (Join-Path $root 'l.json') }
function Invoke-GuardRepo($fx, $repoPath) {
    return & $guard -GovOverride $fx.Gov -LocalOverride $fx.Local -LedgerPathOverride $fx.Ledger `
                    -StoreRootsOverride @($fx.Store) -CcRepoOverride $repoPath
}
Invoke-GuardRepo $fxg $repo | Out-Null                      # adopt + create absent mirrors
Remove-Item -LiteralPath $canonFile -Force
Remove-Item -Recurse -Force $govD, $locD -ErrorAction SilentlyContinue   # git is the ONLY source
$out = Invoke-GuardRepo $fxg $repo | ConvertFrom-Json
$restoredBytes = if (Test-Path -LiteralPath $canonFile) { [System.IO.File]::ReadAllBytes($canonFile) } else { @() }

Check "GIT RESTORE: canonical was restored"        (Test-Path -LiteralPath $canonFile)
Check "GIT RESTORE: restored from git"             (@($out.restored) -match 'from git')
Check "GIT RESTORE: byte-identical to the committed blob (no encoding corruption)" `
    ($restoredBytes.Length -eq $committed.Length -and (Compare-Object $restoredBytes $committed -SyncWindow 0) -eq $null)
Check "GIT RESTORE: non-ASCII survived intact" `
    (([System.IO.File]::ReadAllText($canonFile)) -eq $UNICODE)
Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue

# ===========================================================================
# 8. A 0-BYTE canonical is NOT content. It hashes to the SHA of the empty string -- a
#    perfectly valid hash -- so it used to be adopted and pushed over both backups,
#    destroying the definition and both copies while reporting a clean sync.
# ===========================================================================
$root = New-TempRoot
$fx = New-Fixture -Root $root -CanonContent $NEW_CONTENT -GovContent $NEW_CONTENT -LocalContent $NEW_CONTENT
Invoke-Guard $fx | Out-Null
[System.IO.File]::WriteAllBytes($fx.CanonFile, @())          # truncation
$out = Invoke-Guard $fx | ConvertFrom-Json
Check "0-BYTE canonical is reported unreadable"  (@($out.unreadable) -contains 't1')
Check "0-BYTE canonical is NOT adopted"          (@($out.backed_up).Count -eq 0)
Check "0-BYTE canonical did not reach the mirrors" `
    ((Get-Content -LiteralPath "$($fx.Gov)\t1\SKILL.md" -Raw) -eq $NEW_CONTENT)
Remove-Item -Recurse -Force $root

# ===========================================================================
# 9. An UNVERIFIED restore must not overwrite an existing mirror. Mirror protection is
#    gated on whether the restore was lineage-VERIFIED, not on having any baseline --
#    otherwise a guess overwrites the only surviving good copy.
# ===========================================================================
$root = New-TempRoot
$fx = New-Fixture -Root $root -CanonContent $OLD_CONTENT -GovContent $OLD_CONTENT -LocalContent $NEW_CONTENT
Remove-Item -LiteralPath $fx.CanonFile -Force                # no ledger yet -> unverified restore
$out = Invoke-Guard $fx | ConvertFrom-Json
Check "UNVERIFIED restore still restores canonical" (Test-Path -LiteralPath $fx.CanonFile)
Check "UNVERIFIED restore is flagged as such"       (@($out.restored) -match 'unverified')
Check "UNVERIFIED restore does NOT overwrite the surviving good mirror" `
    ((Get-Content -LiteralPath "$($fx.Local)\t1\SKILL.md" -Raw) -eq $NEW_CONTENT)
Remove-Item -Recurse -Force $root

# ===========================================================================
# 10. A DELIBERATE rollback that persists across runs is adopted, so the entry cannot
#     stick in regression_detected forever and a later loss of canonical cannot
#     "restore" the operator's rollback away through the permitted absent-canonical door.
# ===========================================================================
$root = New-TempRoot
$fx = New-Fixture -Root $root -CanonContent $OLD_CONTENT -GovContent $OLD_CONTENT -LocalContent $OLD_CONTENT
Invoke-Guard $fx | Out-Null
Set-Content -LiteralPath $fx.CanonFile -Value $NEW_CONTENT -NoNewline
Invoke-Guard $fx | Out-Null                                   # NEW is known-good
Set-Content -LiteralPath $fx.CanonFile -Value $OLD_CONTENT -NoNewline   # operator rolls back
$o1 = Invoke-Guard $fx | ConvertFrom-Json                     # run A: report, freeze
$o2 = Invoke-Guard $fx | ConvertFrom-Json                     # run B: persisted -> adopt
Check "rollback run A reports a regression"       (@($o1.regressed).Count -eq 1)
Check "rollback run B adopts the deliberate rollback" (@($o2.regressed) -match 'adopted_deliberate_rollback')
Check "rollback run B propagates it to the mirrors" `
    ((Get-Content -LiteralPath "$($fx.Gov)\t1\SKILL.md" -Raw) -eq $OLD_CONTENT)
Remove-Item -LiteralPath $fx.CanonFile -Force
$o3 = Invoke-Guard $fx | ConvertFrom-Json
Check "after adoption, a lost canonical restores the ROLLBACK, not the undone version" `
    ((Get-Content -LiteralPath $fx.CanonFile -Raw) -eq $OLD_CONTENT)
Remove-Item -Recurse -Force $root

# ===========================================================================
# 11. One malformed registry row must not fail the fleet, and the ledger must still be written.
# ===========================================================================
$root = New-TempRoot
$fx = New-Fixture -Root $root -CanonContent $NEW_CONTENT -GovContent $NEW_CONTENT -LocalContent $NEW_CONTENT
$storeDir = Join-Path $root 'store\cc-sessions\aaa\bbb'
@{ scheduledTasks = @(
      @{ id = 'bad-row'; filePath = 'SKILL.md' },        # no directory component
      @{ id = 't1';      filePath = $fx.CanonFile },
      @{ id = 'T1';      filePath = $fx.CanonFile }      # case-variant of t1
) } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $storeDir 'scheduled-tasks.json')
$out = Invoke-Guard $fx | ConvertFrom-Json
Check "malformed row does not fail the run"        ($null -ne $out.checked)
Check "case-variant ids are counted separately"    ($out.checked -eq 3)
Check "canonical untouched by the malformed row"   ((Get-Content -LiteralPath $fx.CanonFile -Raw) -eq $NEW_CONTENT)
Check "the ledger was still written"               (Test-Path -LiteralPath $fx.Ledger)
Remove-Item -Recurse -Force $root

# ===========================================================================
# 12. A corrupt ledger must be REPORTED, not silently treated as "no history". Regression
#     detection is off for that run; a zero that could mean "couldn't look" is a failure.
# ===========================================================================
$root = New-TempRoot
$fx = New-Fixture -Root $root -CanonContent $NEW_CONTENT -GovContent $NEW_CONTENT -LocalContent $NEW_CONTENT
Set-Content -LiteralPath $fx.Ledger -Value '{ this is not json'
$out = Invoke-Guard $fx | ConvertFrom-Json
Check "corrupt ledger is reported via ledger_status" ($out.ledger_status -eq 'unreadable')
Check "corrupt ledger does not crash the run"        ($out.checked -ge 1)
Check "corrupt ledger leaves canonical intact"       ((Get-Content -LiteralPath $fx.CanonFile -Raw) -eq $NEW_CONTENT)
Remove-Item -Recurse -Force $root

# ===========================================================================
# 13. -ReportOnly writes NOTHING. dry-run-task-integrity-guard.ps1 drives the real engine,
#     so without a genuine no-write mode the "dry run" mutated the live ledger and mirrors.
# ===========================================================================
$root = New-TempRoot
$fx = New-Fixture -Root $root -CanonContent $NEW_CONTENT -GovContent $OLD_CONTENT -LocalContent $OLD_CONTENT
Invoke-Guard $fx | Out-Null                                  # baseline so a sync would be due
Set-Content -LiteralPath $fx.CanonFile -Value $NEW_CONTENT -NoNewline
$govBefore = Get-Content -LiteralPath "$($fx.Gov)\t1\SKILL.md" -Raw
Remove-Item -LiteralPath $fx.Ledger -Force
$out = & $guard -GovOverride $fx.Gov -LocalOverride $fx.Local -LedgerPathOverride $fx.Ledger `
                -StoreRootsOverride @($fx.Store) -CcRepoOverride (Join-Path $env:TEMP 'no-such-repo') `
                -ReportOnly | ConvertFrom-Json
Check "ReportOnly is flagged in the output"    ($out.report_only -eq $true)
Check "ReportOnly wrote NO ledger"             (-not (Test-Path -LiteralPath $fx.Ledger))
Check "ReportOnly did not touch the mirrors"   ((Get-Content -LiteralPath "$($fx.Gov)\t1\SKILL.md" -Raw) -eq $govBefore)

Remove-Item -LiteralPath $fx.CanonFile -Force
$out = & $guard -GovOverride $fx.Gov -LocalOverride $fx.Local -LedgerPathOverride $fx.Ledger `
                -StoreRootsOverride @($fx.Store) -CcRepoOverride (Join-Path $env:TEMP 'no-such-repo') `
                -ReportOnly | ConvertFrom-Json
Check "ReportOnly reports a WOULD-restore"     (@($out.restored) -match 'WOULD restore')
Check "ReportOnly did NOT recreate canonical"  (-not (Test-Path -LiteralPath $fx.CanonFile))
Remove-Item -Recurse -Force $root

# ===========================================================================
if ($script:failures.Count -eq 0) {
    Write-Output ""; Write-Output "ALL TESTS PASSED"; exit 0
} else {
    Write-Output ""; Write-Output ("FAILURES: " + $script:failures.Count)
    $script:failures | ForEach-Object { Write-Output "  - $_" }
    exit 1
}
