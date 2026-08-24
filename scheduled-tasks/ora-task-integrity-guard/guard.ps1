# ORA scheduled-task integrity guard (authoritative engine)
# Self-heals the scheduler's canonical task-definition home from dual backups.
# Source of truth = the active scheduled-tasks.json registries under the packaged app store.
#
# WRITE POLICY (rewritten 2026-08-09 -- read before changing anything below):
#   CANONICAL IS AUTHORITATIVE. Mirrors are DERIVED. Canonical is written in exactly one
#   situation -- it is ABSENT -- and never otherwise. Never deletes.
#
#   The previous engine was newest-WINS-BY-MTIME across {canonical, gov mirror, local backup}.
#   On 2026-08-09 08:54:47 that reverted live content for ora-health-guard,
#   ora-task-integrity-guard and automation-health-monitor: the local backup carried mtime
#   2026-08-05 17:58:04 over PRE-08-05 CONTENT, beat canonical, and was copied over it.
#   Copy-Item preserves the source mtime, so the revert was invisible to any later mtime check.
#   mtime is NOT a version. THIRD iteration of that bug class, so mtime is gone entirely:
#   the decision core (maintenance/task-integrity-lib.ps1) takes no time input, test-enforced.
#
# HARDENED 2026-08-09 after independent review + adversarial REFUTE. The defects fixed here were
# all in the ENGINE, not the decision core, and all ended in the same irreversible loss:
#   * git restore CORRUPTED every non-ASCII character. `& git show` output is decoded through
#     [Console]::OutputEncoding -- IBM437 in an unattended -NoProfile run -- so em-dashes,
#     arrows and curly quotes (which every ORA SKILL.md is full of) were mangled BEFORE being
#     re-encoded as UTF-8. The corrupted file was then adopted as known-good and propagated to
#     both mirrors. Blobs are now read as RAW BYTES off the redirected stdout stream.
#     The same bug made the git hash unable to ever equal a file hash, so every git branch was
#     dead code and a poisoned mirror silently outranked a pristine git HEAD.
#   * a failed `git show` wrote a ZERO-BYTE SKILL.md (no exit-code check) -- a silently
#     disabled task -- which then propagated to both mirrors.
#   * a 0-byte canonical hashes to the SHA of the empty string, a VALID hash, so truncation was
#     adopted as content. 0-byte files are now UNUSABLE everywhere.
#   * $ErrorActionPreference='Stop' turns a native command's stderr into a terminating error, so
#     an ordinary git autocrlf warning could abort the run mid-loop AFTER filesystem writes but
#     BEFORE the ledger was written. Git is no longer invoked through the PowerShell pipeline,
#     and every per-task body is isolated so one bad row cannot fail the fleet.
# The -*Override parameters exist ONLY so maintenance/test-guard-integrity-engine.ps1 can drive
# the real engine against synthetic fixtures. Unattended runs pass nothing.
# param() must be the first statement in the script -- it precedes $ErrorActionPreference.
param(
    [string]  $GovOverride,
    [string]  $LocalOverride,
    [string]  $LedgerPathOverride,
    [string[]]$StoreRootsOverride,
    [string]  $CcRepoOverride,
    # Compute and report every decision, WRITE NOTHING (no canonical, no mirrors, no ledger).
    # maintenance/dry-run-task-integrity-guard.ps1 calls the real engine; without this it was
    # a "dry run" that mutated the live ledger and mirrors.
    [switch]  $ReportOnly
)
$ErrorActionPreference = 'Stop'

$ledgerPath = $null; $ledgerTasks = @{}; $ledgerStatus = 'not-read'; $lockStream = $null
try {
    $libPath = Join-Path $PSScriptRoot '..\..\maintenance\task-integrity-lib.ps1'
    if (-not (Test-Path -LiteralPath $libPath)) {
        $libPath = 'C:\Users\Owner\.claude\maintenance\task-integrity-lib.ps1'
    }
    if (-not (Test-Path -LiteralPath $libPath)) {
        # Report through the checked==0 channel: that is the one engine error the consuming
        # SKILL.md escalates to EMAIL. A missing lib would otherwise leave a permanently dead
        # guard whose only symptom is a local log nobody reads.
        Write-Output '{"error":"task-integrity-lib.ps1 not found -- decision core missing, guard cannot run","checked":0}'
        exit 1
    }
    . $libPath

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

    $gov        = 'C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\00_Governance\Scheduled'
    $local      = 'C:\Users\Owner\.claude\_scheduled_tasks_backup'
    $ledgerPath = 'C:\Users\Owner\.claude\maintenance\_state\task-content-ledger.json'
    $ccRepo     = 'C:\Users\Owner\.claude'
    if ($GovOverride)        { $gov        = $GovOverride }
    if ($LocalOverride)      { $local      = $LocalOverride }
    if ($LedgerPathOverride) { $ledgerPath = $LedgerPathOverride }
    if ($CcRepoOverride)     { $ccRepo     = $CcRepoOverride }
    # NOTE: the old $canonRoot (Documents\Claude\Scheduled) is gone. It was dead -- canonical
    # paths come from each registry entry's filePath -- and its comment asserted a canonical
    # root that is wrong for the CC fleet, inviting someone to re-derive the wrong location.
    foreach ($d in @($gov, $local)) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

    # ---- content identity ------------------------------------------------
    # SHA256 over the bytes with CR removed, so a line-ending-only difference (git's autocrlf
    # smudge vs an OneDrive-written copy) is not treated as content divergence. Byte-based on
    # BOTH sides so a git blob hash and a file hash are directly comparable.
    function Get-HashFromBytes([byte[]]$Bytes) {
        if ($null -eq $Bytes -or $Bytes.Length -eq 0) { return $null }   # 0 bytes is NEVER content
        $text  = [System.Text.Encoding]::UTF8.GetString($Bytes)
        $norm  = [System.Text.Encoding]::UTF8.GetBytes(($text -replace "`r", ''))
        if ($norm.Length -eq 0) { return $null }
        $sha = [System.Security.Cryptography.SHA256]::Create()
        try { return ([BitConverter]::ToString($sha.ComputeHash($norm)) -replace '-', '') }
        finally { $sha.Dispose() }
    }

    # Returns $null for absent, unreadable, OR 0-byte. All three are "no usable content",
    # and the caller must never treat any of them as a hash to adopt.
    function Get-FileHash-Usable([string]$Path) {
        try {
            if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
            return Get-HashFromBytes ([System.IO.File]::ReadAllBytes($Path))
        } catch { return $null }
    }

    # Read a git blob as RAW BYTES. Never through the PowerShell pipeline: `& git` output is
    # decoded via [Console]::OutputEncoding (IBM437 here), which mangles every non-ASCII
    # character, and line-joining also drops the trailing newline. Both made the hash
    # uncomparable and the restored content wrong.
    function Get-GitBlobBytes([string]$Repo, [string]$Rel) {
        $proc = $null
        try {
            $psi = New-Object System.Diagnostics.ProcessStartInfo
            $psi.FileName               = 'git'
            $psi.Arguments              = "-C `"$Repo`" show `"HEAD:$Rel`""
            $psi.UseShellExecute        = $false
            $psi.RedirectStandardOutput = $true
            $psi.RedirectStandardError  = $true
            $psi.CreateNoWindow         = $true
            $proc = [System.Diagnostics.Process]::Start($psi)
            $errTask = $proc.StandardError.ReadToEndAsync()      # drain stderr, avoid deadlock
            $ms = New-Object System.IO.MemoryStream
            $proc.StandardOutput.BaseStream.CopyTo($ms)          # BaseStream = undecoded bytes
            $proc.WaitForExit()
            $null = $errTask.Result
            if ($proc.ExitCode -ne 0) { return $null }
            $b = $ms.ToArray()
            if ($b.Length -eq 0) { return $null }                # never write an empty file
            return $b
        } catch { return $null }
        finally { if ($proc) { $proc.Dispose() } }
    }

    function Get-RepoRelative([string]$Path, [string]$Repo) {
        $r = $Repo.TrimEnd('\', '/') + '\'
        if (-not $Path.StartsWith($r, [StringComparison]::OrdinalIgnoreCase)) { return $null }  # path-boundary safe
        return $Path.Substring($r.Length).Replace('\', '/')
    }

    # ---- 1. active task set from every registry --------------------------
    # Case-SENSITIVE: a default PowerShell hashtable is case-insensitive, so registry ids
    # differing only in case silently collapsed and one real task went unguarded, unreported.
    $ids        = New-Object 'System.Collections.Generic.Dictionary[string,string]' ([StringComparer]::Ordinal)
    $parseMiss  = @()
    $collisions = @()
    Get-ChildItem -Path ($storeRoots | ForEach-Object { Join-Path $_ '*-sessions\*\*\scheduled-tasks.json' }) -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $j = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
            foreach ($t in $j.scheduledTasks) {
                if ($t.id -and $t.filePath) {
                    if ($ids.ContainsKey($t.id) -and $ids[$t.id] -ne $t.filePath) {
                        $collisions += ('{0} -> {1} | {2}' -f $t.id, $ids[$t.id], $t.filePath)
                    }
                    $ids[$t.id] = $t.filePath
                }
            }
        } catch {
            # A registry that will not parse is exactly the blind spot this guard exists to
            # catch -- report it, never swallow it.
            $parseMiss += $_.FullName
        }
    }

    if ($ids.Count -eq 0) {
        Write-Output '{"error":"checked==0 -- no registry entries discovered under any store root; store discovery is broken (silent no-op)","checked":0}'
        exit 1
    }

    # ---- id-collision acknowledgment (2026-08-24, Gabriel-directed) ------
    # A collision is re-derived from a live registry scan every run -- there is no persistence
    # of its own, so by construction it never silently disappears. This lets Gabriel dated-ack a
    # SPECIFIC (id, path-pair) he already knows about and has a plan for, without inventing a new
    # blind spot: the ack is pinned to the exact path pair, so if either path ever changes (the
    # known leg gets resolved, or a DIFFERENT collision appears on the same id) the old ack stops
    # matching and the finding re-alarms on its own. Same bar as dangling-mutation-acknowledged.json
    # / ora-appsec-sweep/suppressions.md: added deliberately with a dated reason, never to quiet a
    # noisy run. Fail-open: an absent or unparseable ack file suppresses nothing.
    $idCollisionAckPath = 'C:\Users\Owner\.claude\maintenance\_shared\id-collision-acknowledged.json'
    $idCollisionAcks = @()
    try {
        if (Test-Path -LiteralPath $idCollisionAckPath) {
            $idCollisionAcks = @(Get-Content -LiteralPath $idCollisionAckPath -Raw | ConvertFrom-Json)
        }
    } catch { $idCollisionAcks = @() }

    $collisionsSuppressed = @()
    $collisionsLive = @()
    foreach ($c in $collisions) {
        # Format is '{id} -> {path1} | {path2}' (built above). Split defensively -- an ack that
        # fails to parse against a given entry just falls through to "live", never to "suppressed".
        $isSuppressed = $false
        try {
            $idPart, $pathsPart = $c -split ' -> ', 2
            $p1, $p2 = @($pathsPart -split ' \| ', 2)
            $pairKey = (@($p1, $p2) | Sort-Object) -join '|'
            foreach ($ack in $idCollisionAcks) {
                if ($ack.task_id -ceq $idPart -and $ack.paths -and
                    ((@($ack.paths) | Sort-Object) -join '|') -eq $pairKey) {
                    $isSuppressed = $true
                    break
                }
            }
        } catch { $isSuppressed = $false }
        if ($isSuppressed) { $collisionsSuppressed += $c } else { $collisionsLive += $c }
    }

    # ---- ledger lock -----------------------------------------------------
    # The ledger is read-modify-write and this engine has TWO scheduled callers, which an
    # overnight-outage catch-up burst can fire together. Unlocked, concurrent runs silently lost
    # whole entries (measured: 150 expected, 100 present).
    $lockPath = "$ledgerPath.lock"
    $lockDir = Split-Path $lockPath
    if ($lockDir -and -not (Test-Path -LiteralPath $lockDir)) { New-Item -ItemType Directory -Force -Path $lockDir | Out-Null }
    $deadline = (Get-Date).AddSeconds(120)
    while ($null -eq $lockStream -and (Get-Date) -lt $deadline) {
        try { $lockStream = [System.IO.File]::Open($lockPath, 'OpenOrCreate', 'ReadWrite', 'None') }
        catch { Start-Sleep -Milliseconds 500 }
    }
    if ($null -eq $lockStream) {
        # Benign by construction: the run holding the lock performs the identical work. Reported
        # rather than silent, so it cannot become an invisible skip.
        Write-Output ('{"skipped_concurrent_run":true,"checked":' + $ids.Count + ',"note":"another guard run holds the ledger lock; it is doing this work"}')
        exit 0
    }

    $led         = Read-TaskLedger $ledgerPath
    $ledgerTasks = $led.Tasks
    $ledgerStatus = $led.Status

    $restored = @(); $backed = @(); $missing = @(); $regressed = @(); $unreadable = @(); $errors = @()

    foreach ($id in @($ids.Keys)) {
        # PER-TASK ISOLATION: one malformed row (empty directory component, a filePath aliased
        # onto its own backup) used to abort the whole run under EAP=Stop, discarding every
        # lineage update decided that run while the filesystem writes had already happened.
        try {
            $fp   = $ids[$id]
            $name = Split-Path $fp -Leaf
            if (-not $name) { throw "registry filePath has no file component: '$fp'" }

            $canonExists = Test-Path -LiteralPath $fp -PathType Leaf
            $canonHash   = if ($canonExists) { Get-FileHash-Usable $fp } else { $null }

            # Exists but yields no usable hash = locked, unhydrated, or 0-byte. NOT missing.
            # Restoring over it would destroy a file we merely could not read.
            if ($canonExists -and -not $canonHash) { $unreadable += $id; continue }

            $mirrorPaths  = [ordered]@{ gov = (Join-Path $gov "$id\$name"); local = (Join-Path $local "$id\$name") }
            $mirrorHashes = @{}
            foreach ($m in $mirrorPaths.Keys) { $mirrorHashes[$m] = Get-FileHash-Usable $mirrorPaths[$m] }

            $gitRel = Get-RepoRelative $fp $ccRepo
            $gitHead = $null
            if (-not $canonHash -and $gitRel) { $gitHead = Get-HashFromBytes (Get-GitBlobBytes $ccRepo $gitRel) }

            $entry = $null
            if ($ledgerTasks.ContainsKey($id)) { $entry = $ledgerTasks[$id] }

            $r = Resolve-TaskAction -Id $id -CanonHash $canonHash -MirrorHashes $mirrorHashes `
                                    -LedgerEntry $entry -GitHeadHash $gitHead

            if ($r.Action -eq 'missing_everywhere') { $missing += $id; continue }
            if ($r.Action -eq 'regression_detected' -or $r.Action -eq 'known_good_lost') {
                $regressed += ('{0} [{1}; known-good at: {2}]' -f $id, $r.Action, (@($r.KnownGoodAt) -join ','))
                if ($r.SetPending) { $ledgerTasks[$id] = Update-TaskLedgerEntry $entry $null $r.SetPending $false }
                continue
            }
            if ($r.Action -eq 'adopt_after_regression') {
                $regressed += ('{0} [adopted_deliberate_rollback]' -f $id)
            }

            if ($r.RestoreCanonical) {
                # TOCTOU re-check: hashing two mirrors and shelling out to git takes real time,
                # and a session or OneDrive hydration can land the file in that window.
                if (Test-Path -LiteralPath $fp -PathType Leaf) {
                    $errors += ('{0} [canonical reappeared mid-run; restore skipped]' -f $id)
                    continue
                }
                if (-not $ReportOnly) { New-Item -ItemType Directory -Force -Path (Split-Path $fp) | Out-Null }
                if ($ReportOnly) {
                    $restored += ('{0} [WOULD restore from {1}; {2}]' -f $id, $r.RestoreFrom, $r.Reason)
                } elseif ($r.RestoreFrom -eq 'git') {
                    $bytes = Get-GitBlobBytes $ccRepo $gitRel
                    if ($null -eq $bytes -or $bytes.Length -eq 0) {
                        $errors += ('{0} [git restore aborted: blob unreadable or empty]' -f $id); continue
                    }
                    [System.IO.File]::WriteAllBytes($fp, $bytes)     # verbatim bytes, no re-encode
                } else {
                    Copy-Item -LiteralPath $mirrorPaths[$r.RestoreFrom] -Destination $fp -Force
                }
                if (-not $ReportOnly) { $restored += ('{0} [from {1}; {2}]' -f $id, $r.RestoreFrom, $r.Reason) }
            }

            if ($r.SyncMirrors) {
                foreach ($m in @($r.MirrorsToSync)) {
                    if ($ReportOnly) { continue }
                    $mp = $mirrorPaths[$m]
                    New-Item -ItemType Directory -Force -Path (Split-Path $mp) | Out-Null
                    Copy-Item -LiteralPath $fp -Destination $mp -Force
                }
                if ($backed -notcontains $id) { $backed += $id }
            }

            if ($r.NewCurrent -or $r.ClearPending) {
                $ledgerTasks[$id] = Update-TaskLedgerEntry $entry $r.NewCurrent $r.SetPending $r.ClearPending
            }
        } catch {
            $errors += ('{0} [{1}]' -f $id, ($_.Exception.Message -replace '[\r\n]+', ' '))
        }
    }

    if (-not $ReportOnly) { Write-TaskLedger $ledgerPath $ledgerTasks (Get-Date).ToString('s') }

    [ordered]@{
        report_only        = [bool]$ReportOnly
        checked            = $ids.Count
        restored           = @($restored)     # canonical was ABSENT and was rebuilt
        backed_up          = @($backed)       # mirrors refreshed from canonical
        missing_everywhere = @($missing)
        regressed          = @($regressed)    # canonical matches a recorded ANCESTOR -- NOT auto-fixed
        unreadable         = @($unreadable)   # exists but unreadable/0-byte -- left strictly untouched
        errors             = @($errors)       # per-task failures; the run continued
        parse_miss         = @($parseMiss)    # registry files that would not parse
        id_collisions      = @($collisionsLive)       # live -- unacknowledged, STEP-3 alarm
        id_collisions_suppressed = @($collisionsSuppressed)  # dated-acked in id-collision-acknowledged.json; reported, never escalated
        ledger_status      = $ledgerStatus    # ok | absent | unreadable -- 'unreadable' means
                                              # regression detection was OFF this run
        churn_suppressed   = @()              # vestigial: kept so older parsing does not break.
        ts                 = (Get-Date).ToString('s')
    } | ConvertTo-Json -Compress
} catch {
    Write-Output ('{"error":"' + (($_.Exception.Message -replace '[\r\n]+', ' ') -replace '"', '\"') + '"}')
    exit 1
} finally {
    if ($lockStream) { $lockStream.Close(); $lockStream.Dispose() }
}
