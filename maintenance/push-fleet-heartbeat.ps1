# ORA Fleet Heartbeat + Pending-Work Push -- local pulse leg of the EXTERNAL cross-fleet dead-man (v3.2 2026-09-23)
# ----------------------------------------------------------------------------------
# WHY v1.0 (2026-07-09): Task 6 (DEADMAN_APPROACH=GITHUB-ACTION, Gabriel-ratified). The
# GitHub Action .github/workflows/fleet-deadman.yml checks a copy of the heartbeat on GitHub
# daily (14:00 UTC since v3.0; 13:00 UTC originally) and alarms if it is >24h stale, late, or
# below the ratified fleet floors. Something on THIS machine must therefore refresh + publish
# the heartbeat daily. No automated ~/.claude push existed when this was built (verified
# 2026-07-09: commits to ZeOoba/ora-claude-config are manual/per-session) -- this
# script IS that missing pulse. (Through v2.0 the Action read maintenance/_state/
# fleet-heartbeat.json on main; since v3.0 it reads the deadman-heartbeat branch.)
#
# WHY v2.0 (2026-08-23, Gabriel-ratified): v1.0's narrow scope (heartbeat commit
# only) meant any OTHER work already committed in the main-checkout worktree sat
# unpushed until a session happened to notice -- found live 2026-08-23: a real
# feature commit (ORPHANED_FILEPATH check) sat unpushed >15h, discovered only
# because a session doing something unrelated synced the worktree by hand. Root
# cause was never the commit scope (git push origin main already pushes the FULL
# local-ahead-of-remote delta, not just the newest commit) -- it was reconciliation:
# the old step 2 tried --ff-only ONLY and gave up on ANY real divergence (both
# sides have unique commits), even when the two sides touch entirely different
# files and would merge cleanly. v2.0 adds one real `git merge` attempt behind the
# ff-only fast path, with an UNCONDITIONAL abort-and-bail on any actual conflict --
# conflict resolution needs human/session judgment (see the 2026-08-23
# governor-drift-probe.py merge: real conflicts there took two Fable-tier agents and
# 3 review rounds to resolve correctly) that a scheduled script can never safely
# automate. This still never force-pushes, never rebases, and never resolves a
# real conflict itself -- it only closes the gap where two NON-conflicting commit
# sets sat needlessly unpushed. Safety net is the existing pre-push hook suite
# (git-prepush-doctrine-gate.py / hook-tests-gate), same gate every manual push
# already goes through -- no additional gate added, per Gabriel's explicit call.
#
# Runs from WINDOWS Task Scheduler (outside both Claude fleets, like
# fleet-deadman.ps1) so it keeps pulsing even if the fleets are dark -- and when
# the whole MACHINE is dark, the pulse stops and the GitHub Action alarms. That
# is the dead-man working as designed.
#
# WHY v3.0 (2026-09-19, OI-323): the heartbeat rode the SAME `git push origin main` as the
# backup work, so the ~12-min pre-push gate (unrelated failing hook tests, or a remote main
# that moved mid-gate) kept it off GitHub for days -- while this script exited 0, so Task
# Scheduler showed green. v3.0 publishes the heartbeat FIRST via publish-fleet-heartbeat.py
# (GitHub API, dedicated branch, no gate) and exits NONZERO when that publish fails. The
# backup push below is unchanged and stays best-effort.
#
# WHY v3.1 (2026-09-22, OI-331): v3.0 fixed the heartbeat's own signal but left the backup
# push (the OTHER thing this script does -- getting pending main-checkout work onto GitHub)
# with none of its own. Its failures (no worktree on main, a real merge conflict, or the push
# itself failing) were only ever a log line -- the exit code never reflected them, and nothing
# outside this script's own log read them, so ~a dozen hook-test-gate failures and 4 remote-
# main races since 08-15 went unnoticed until a second adversarial review of the OI-323 build
# found them by hand. Fix (Gabriel-ratified 2026-09-22, option (a) of three): the backup push
# now writes its own marker/stamp pair, same pattern as publish-fleet-heartbeat.py's
# heartbeat-publish-failed.json/-ok.json -- backup-push-failed.json on any of the three
# failure paths (cleared on the next success), backup-push-ok.json on every success
# (including a no-op day with nothing to push). This is a SEPARATE signal from $pubExit,
# which still reflects ONLY the heartbeat publish -- the backup step stays Fail-OPEN and this
# script's own exit code is unchanged by it, per the same reasoning as v3.0: a stuck merge or
# a gate failure needs a human session to reconcile, not a louder scheduled-task alarm racing
# ahead of that.
#
# WHY v3.2 (2026-09-23, OI-353): the ~11-min pre-push gate gives other sessions time to move
# remote main, so the backup push kept losing the race (`cannot lock ref ... but expected`;
# consecutive runs 09-22 and 09-23). On a push rejection that is recognisably a lost race, the
# step-1 reconcile (now Invoke-MainReconcile) runs once more -- merge, never rebase -- and the
# push is retried ONCE. Any other failure, a second loss, or an unclean reconcile fails loud
# as before. A failed fetch is now its own outcome instead of a silent stale ff-only.
#
# Backup step is Fail-OPEN: any internal error, or any real merge conflict, -> log and carry
# on (a stuck merge is exactly what a human session must resolve); only the heartbeat publish
# sets the exit code. ASCII-only (PS 5.1 reads non-BOM as ANSI).
#
# Install (run once -- NOT auto-installed; needs Gabriel's ratification, choose
# 07:30 local so both winter and summer land before the 13:00 UTC check):
#   schtasks /Create /TN "ORA Fleet Heartbeat Push" /SC DAILY /ST 07:30 /F `
#     /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"C:\Users\Owner\.claude\maintenance\push-fleet-heartbeat.ps1\""

$primaryRepo = Join-Path $env:USERPROFILE '.claude'
$hbRel       = 'maintenance/_state/fleet-heartbeat.json'
$log         = Join-Path $primaryRepo 'maintenance\push-fleet-heartbeat.log'

# --- Log rotation (added 2026-09-06, Automation Audit R21-10 / R22-8; restored 2026-09-11,
#     Automation Audit R25-3 -- this code merged to main in PR #162 but was absent from the
#     live checkout, the same regression found in stuck-session-watchdog.ps1) ------------
# This log had no cap of ANY kind: `grep -icE "rotat|MaxLog|trim|Clear-Content|prune|archive"`
# returned 0 against this file, and it was growing unbounded (~8.0KB/day for the
# watchdog, ~5.5KB/day for the heartbeat push). Rotation ARCHIVES, never deletes,
# per standing invariant 6, and is wrapped in try/catch so a rotation failure can
# never take down the caller -- these scripts fail open, like every other guard here.
function Invoke-LogRotation($path, $maxBytes = 1048576) {
    try {
        if (Test-Path -LiteralPath $path) {
            if ((Get-Item -LiteralPath $path).Length -ge $maxBytes) {
                $archDir = Join-Path (Split-Path $path -Parent) '_log_archive'
                if (-not (Test-Path -LiteralPath $archDir)) {
                    New-Item -ItemType Directory -Path $archDir -Force | Out-Null
                }
                $base = [IO.Path]::GetFileNameWithoutExtension($path)
                $dest = Join-Path $archDir ("{0}-{1}.log" -f $base, [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss'))
                Move-Item -LiteralPath $path -Destination $dest -Force
            }
        }
    } catch { }
}
Invoke-LogRotation $log

# Non-throwing (OI-331 gate finding): two overlapping runs (the daily Windows task and the
# integrity guard's STEP 1.5 script 3) can collide on this log; an IOException here used to
# land in the publish try/catch and set $pubExit = 2, so a SUCCESSFUL publish could exit
# nonzero and trip the STEP-3 alarm. A lost log line must never change the exit code.
function Log($m) { try { "$([DateTime]::UtcNow.ToString('s'))Z  $m" | Out-File -FilePath $log -Append -Encoding utf8 } catch { } }

# --- Backup-push marker/stamp (added 2026-09-22, OI-331) -----------------------------------
# Same pattern as publish-fleet-heartbeat.py's heartbeat-publish-failed.json/-ok.json: a
# marker written on failure (cleared on the next success) and a stamp written on every
# success, both in maintenance/_state/ so any session or probe can check the backup push's
# OWN status independently of this script's exit code (which stays reserved for the
# heartbeat publish, unchanged from v3.0). Fail-open: a write error here is logged and
# swallowed, never allowed to affect the backup step's own fail-open behavior.
$stateDir       = Join-Path $primaryRepo 'maintenance\_state'
$backupMarker   = Join-Path $stateDir 'backup-push-failed.json'
$backupStamp    = Join-Path $stateDir 'backup-push-ok.json'

function Write-BackupPushFailed($reason) {
    try {
        if (-not (Test-Path -LiteralPath $stateDir)) { New-Item -ItemType Directory -Path $stateDir -Force | Out-Null }
        $obj = @{ ts = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ'); reason = $reason }
        ($obj | ConvertTo-Json -Compress) | Out-File -LiteralPath $backupMarker -Encoding utf8
    } catch { Log ('backup-push marker write FAILED (non-fatal): ' + $_.Exception.Message) }
}

function Write-BackupPushOk {
    try {
        if (-not (Test-Path -LiteralPath $stateDir)) { New-Item -ItemType Directory -Path $stateDir -Force | Out-Null }
        $obj = @{ ts = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ') }
        ($obj | ConvertTo-Json -Compress) | Out-File -LiteralPath $backupStamp -Encoding utf8
        if (Test-Path -LiteralPath $backupMarker) { Remove-Item -LiteralPath $backupMarker -Force }
    } catch { Log ('backup-push stamp write FAILED (non-fatal): ' + $_.Exception.Message) }
}

# --- Self-heal a heartbeat file stranded by a KILLED run (v3.3, 2026-10-13 diagnosis). Step 3
# does `git add` then `git commit --only` on the heartbeat path. A run killed in between (Task
# Scheduler catch-ups at wake exit 0xC000013A within ~45s) leaves that ONE file staged or
# modified; from then on every step-1 merge is refused ("local changes ... would be
# overwritten", seen 2026-10-07), so no later run ever reaches the emit, commit or push and the
# backup goes stale for good. Step 2 regenerates this file every run, so a STALE uncommitted
# copy is worthless. Restore ONLY that path from HEAD, and only once it has sat dirty longer
# than $minAgeMinutes: a younger change may belong to a sibling run that is mid-flight (the daily
# task and the integrity guard's script 3 can overlap). Pathspec-scoped: other staged work,
# untracked files and every other path are never touched; an untracked or unmerged heartbeat
# path is not ours to discard. Returns 'clean', 'fresh', 'cleared' or 'restore-failed'; never
# throws (fail-open like the rest of the backup step).
function Clear-StaleHeartbeatState($repo, $rel, $minAgeMinutes = 30) {
    try {
        $dirty = @(git -C $repo status --porcelain -- $rel 2>$null)
        if ($LASTEXITCODE -ne 0) { return 'restore-failed' }
        if ($dirty.Count -eq 0) { return 'clean' }
        $full = Join-Path $repo ($rel -replace '/', '\')
        if (Test-Path -LiteralPath $full) {
            $age = ((Get-Date) - (Get-Item -LiteralPath $full).LastWriteTime).TotalMinutes
            if ($age -lt $minAgeMinutes) { return 'fresh' }
        }
        if ("$($dirty[0])" -match '^(\?\?|U.|.U|AA|DD)') { return 'restore-failed' }
        # A path absent from HEAD (e.g. staged as a NEW file) has nothing to restore TO: git restore
        # would delete it. Not ours to discard (adversarial review finding, 2026-10-13).
        git -C $repo cat-file -e ('HEAD:' + $rel) 2>$null
        if ($LASTEXITCODE -ne 0) { return 'restore-failed' }
        Log ('stale heartbeat state left by a killed run - restoring ' + $rel + ' from HEAD (was: ' + ((@($dirty) -join ' ').Trim()) + ')')
        git -C $repo restore --source=HEAD --staged --worktree -- $rel 2>&1 | ForEach-Object { Log ("restore: " + $_) }
        if ($LASTEXITCODE -ne 0) { return 'restore-failed' }
        if (@(git -C $repo status --porcelain -- $rel 2>$null).Count -ne 0) { return 'restore-failed' }
        return 'cleared'
    } catch {
        Log ('heartbeat self-heal ERROR (non-fatal): ' + $_.Exception.Message)
        return 'restore-failed'
    }
}

# --- Reconcile main with origin/main (v3.2, OI-353: factored out of step 1 so step 4 can
# run it again before its one retry push). Fetch, then ff-only (the common case per the
# 2026-08-04 fix: 6 of 8 historical failures were pure races, not real conflicts); only on
# ff-only failure (true two-sided divergence) one real merge, and ANY failure from that
# aborts immediately, leaving the tree exactly as found. MERGE, NEVER REBASE: main-checkout
# carries prior auto-reconcile merge commits, and this script never rewrites history or
# resolves a conflict itself. Returns 'ok', 'conflict', 'merge-failed' or 'fetch-failed'.
function Invoke-MainReconcile($repo) {
    git -C $repo fetch origin main 2>&1 | ForEach-Object { Log ("fetch: " + $_) }
    # A failed fetch leaves origin/main stale, so ff-only would report "up to date" and a
    # retry push would re-run the whole gate only to lose again (merge-gate finding, OI-353).
    if ($LASTEXITCODE -ne 0) { return 'fetch-failed' }
    git -C $repo merge --ff-only origin/main 2>&1 | ForEach-Object { Log ("ff-only: " + $_) }
    if ($LASTEXITCODE -eq 0) { return 'ok' }
    Log 'ff-only merge failed (real divergence, not just a race) - attempting one real merge'
    $mergeMsg = 'Merge origin/main into main-checkout (auto-reconcile, push-fleet-heartbeat v2.0, ' + [DateTime]::UtcNow.ToString('yyyy-MM-dd') + ')'
    git -C $repo merge origin/main -m $mergeMsg 2>&1 | ForEach-Object { Log ("merge: " + $_) }
    $mergeExit = $LASTEXITCODE
    $unmerged = git -C $repo diff --name-only --diff-filter=U
    if ($mergeExit -ne 0 -or $unmerged) {
        git -C $repo merge --abort 2>&1 | ForEach-Object { Log ("abort: " + $_) }
        if ($unmerged) { return 'conflict' }
        return 'merge-failed'
    }
    Log 'auto-merge clean, no conflicts - reconciled, will push everything below'
    return 'ok'
}

# Push main, and on a lost race reconcile once and push once more (v3.2, OI-353). Output is
# streamed to the log line by line as it arrives -- the pre-push gate runs ~11 min and a
# killed run (0xC000013A, seen 09-22) must still leave the gate lines behind. Returns the
# final push exit code.
function Invoke-BackupPush($repo) {
    $script:pushOut = New-Object System.Collections.Generic.List[string]
    git -C $repo push origin main 2>&1 | ForEach-Object { $script:pushOut.Add("$_"); Log ("push: " + $_) }
    $pushExit = $LASTEXITCODE
    if ($pushExit -eq 0 -or -not (Test-PushRaceRejection $script:pushOut)) { return $pushExit }
    Log 'push lost a race (remote main moved during the pre-push gate) - reconciling once more and retrying the push once'
    $rec = Invoke-MainReconcile $repo
    if ($rec -ne 'ok') {
        Log ('retry reconcile did not come back clean (' + $rec + ') - tree left unchanged; not retrying the push')
        return $pushExit
    }
    git -C $repo push origin main 2>&1 | ForEach-Object { Log ("push-retry: " + $_) }
    return $LASTEXITCODE
}

# OI-353: a push rejected because remote main moved while the ~11-min pre-push gate ran
# (`cannot lock ref ... but expected`, or git's own fetch-first / non-fast-forward refusal)
# is a lost race -- worth one reconcile + retry. Anything else (a failing gate, auth,
# network) is not, and a retry would only burn another gate run.
function Test-PushRaceRejection($lines) {
    $text = (@($lines) | ForEach-Object { "$_" }) -join "`n"
    return [bool]($text -match "cannot lock ref '[^']*': is at \S+ but expected" -or
                  $text -match '\[rejected\].*\((fetch first|non-fast-forward)\)')
}

# v3.0 (OI-323): publish the heartbeat FIRST, on its own path. It goes to the dedicated
# deadman-heartbeat branch through the GitHub API, so it no longer waits on the reconcile,
# the ~12-min pre-push gate or a race with main below. This is the ONLY result that sets the
# exit code: nonzero (2) on failure, and publish-fleet-heartbeat.py leaves a marker that
# fleet-deadman.ps1 reports the same day. The backup push below stays best-effort.
$pubExit = 0
# START breadcrumb (2026-09-22): on 09-22 this task and ORA Fleet Dead-Man both launched at
# 09:37:33 and both ended 0xC000013A with NO log line, so "killed before the publish printed"
# and "never started" could not be told apart. A START with nothing after it now means the
# run started and died. It goes to a SEPARATE file (merge-gate finding 2026-09-22):
# state-freshness-probe judges push-fleet-heartbeat.log by mtime at 48h, and a START written
# there by a killed run would keep that log looking fresh.
$startLog = Join-Path $primaryRepo 'maintenance\push-fleet-heartbeat.start.log'
function LogStart($m) { "$([DateTime]::UtcNow.ToString('s'))Z  $m" | Out-File -FilePath $startLog -Append -Encoding utf8 }
LogStart ('START pid=' + $PID)
try {
    $py = 'C:\Users\Owner\AppData\Local\Programs\Python\Python313\python.exe'
    if (-not (Test-Path $py)) { $py = 'python' }
    & $py (Join-Path $PSScriptRoot 'publish-fleet-heartbeat.py') 2>&1 | ForEach-Object { Log ("publish: " + $_) }
    $pubExit = $LASTEXITCODE
} catch {
    Log ('publish ERROR: ' + $_.Exception.Message)
    $pubExit = 2
}
if ($pubExit -ne 0) { $pubExit = 2 }

try {
    # 0) Resolve whichever worktree actually has 'main' checked out -- NEVER
    #    assume the primary checkout ($primaryRepo) is on main (fixed 2026-08-22,
    #    closes an incident where the primary checkout was on
    #    feat/model-canary-probe-step25: this script committed the heartbeat
    #    refresh there instead of on main, then `git push origin main` pushed the
    #    untouched local main ref -- a silent no-op that looked like success while
    #    the heartbeat actually went stale on origin). Resolved dynamically via
    #    `git worktree list`, not a hardcoded worktree path, so a future
    #    rename/recreation of the main-checkout worktree can't silently regress
    #    this fix back to the same bug.
    $repo = $null
    $wtPath = $null
    git -C $primaryRepo worktree list --porcelain 2>&1 | ForEach-Object {
        if ($_ -match '^worktree (.+)$') { $wtPath = $Matches[1] }
        elseif ($_ -match '^branch refs/heads/main$') { $repo = $wtPath }
    }
    if (-not $repo) {
        Log 'FAIL-OPEN: no worktree has main checked out (git worktree list) - skipping backup push'
        Write-BackupPushFailed 'no worktree has main checked out'
        exit $pubExit
    }
    Log ("using main worktree: " + $repo)

    # 1) Reconcile FIRST, on a clean tree -- BEFORE the heartbeat emit in step 2
    #    below dirties the working copy, so a real merge here never has to
    #    contend with an uncommitted change to the exact file this script is
    #    about to write (v2.0: this ordering swap is deliberate -- doing the
    #    reconcile after the emit, as v1.0 effectively did by only ever
    #    attempting --ff-only post-emit, risks "would be overwritten by merge"
    #    on heartbeat.json specifically, since that file is the one both this
    #    script's local run AND a prior day's already-pushed commit both touch).
    #    ff-only first (the common case per the 2026-08-04 fix: 6 of 8 historical
    #    failures were pure races, not real conflicts) -- only on ff-only failure
    #    (true two-sided divergence) do we attempt one real merge, and ANY
    #    conflict from that aborts immediately, leaving the tree exactly as
    #    found. This script NEVER resolves a conflict itself. (Logic lives in
    #    Invoke-MainReconcile since v3.2 so step 4's race retry reuses it.)
    #    v3.3: first clear a heartbeat file stranded (staged or modified) by a KILLED earlier run,
    #    which would otherwise make every merge below fail forever -- see Clear-StaleHeartbeatState.
    $heal = Clear-StaleHeartbeatState $repo $hbRel
    if ($heal -ne 'clean') { Log ('heartbeat self-heal: ' + $heal) }
    $rec = Invoke-MainReconcile $repo
    # Only unmerged paths make it a genuine conflict. A nonzero merge with none has more than
    # one possible cause (another run holding .git/index.lock -- the daily Windows task and
    # the guard's script 3 can overlap -- or local changes that the merge would overwrite),
    # and only the second is not cured by retrying, so name both rather than assert one.
    if ($rec -eq 'conflict') {
        Log 'REAL CONFLICT - merge aborted, tree left clean and unchanged; needs a session to reconcile by hand. Backup push skipped this cycle (the heartbeat itself was published above)'
        Write-BackupPushFailed 'real merge conflict - aborted, needs a session to reconcile'
        exit $pubExit
    } elseif ($rec -eq 'fetch-failed') {
        Log 'fetch of origin/main FAILED - see the fetch: lines above; backup push skipped this cycle (the heartbeat itself was published above)'
        Write-BackupPushFailed 'git fetch origin main failed - see the fetch: lines in push-fleet-heartbeat.log'
        exit $pubExit
    } elseif ($rec -ne 'ok') {
        Log 'merge failed with no conflicting files - see the merge: lines above (git lock contention with an overlapping run, or local changes blocking the merge). Merge aborted; backup push skipped this cycle (the heartbeat itself was published above)'
        Write-BackupPushFailed 'merge failed with no conflicting files (git lock contention with an overlapping run, or local changes blocking the merge) - see the merge: lines in push-fleet-heartbeat.log'
        exit $pubExit
    }

    # 2) Refresh the heartbeat (full interpreter path first -- scheduled sessions
    #    may not have python on PATH; bare python as fallback), now that the tree
    #    is reconciled. Runs the emitter FROM the resolved main worktree so it
    #    writes that worktree's copy of the heartbeat file (emit-fleet-heartbeat.py
    #    resolves its output path relative to its own script location, not cwd) --
    #    step 3 below commits that copy.
    $emitter = Join-Path $repo 'maintenance\emit-fleet-heartbeat.py'
    $py = 'C:\Users\Owner\AppData\Local\Programs\Python\Python313\python.exe'
    if (-not (Test-Path $py)) { $py = 'python' }
    & $py $emitter 2>&1 | ForEach-Object { Log ("emit: " + $_) }
    if ($LASTEXITCODE -ne 0) { Log 'emit FAILED - continuing with the previous heartbeat unchanged' }

    # 3) Commit ONLY the heartbeat path, if it changed. --only scopes the commit
    #    to the pathspec even if other work is staged (shared single-writer
    #    checkout: other sessions' hunks must never ride along in THIS script's
    #    own commit -- separate from step 4's decision to push whatever else is
    #    already committed).
    $changed = git -C $repo status --porcelain -- $hbRel
    if ($changed) {
        git -C $repo add -- $hbRel 2>&1 | ForEach-Object { Log ("add: " + $_) }
        $msg = 'chore(deadman): fleet-heartbeat refresh ' + [DateTime]::UtcNow.ToString('yyyy-MM-dd')
        git -C $repo commit --only -m $msg -- $hbRel 2>&1 | ForEach-Object { Log ("commit: " + $_) }
        if ($LASTEXITCODE -ne 0) { Log 'heartbeat commit FAILED - continuing to check for other pending work to push' }
    } else {
        Log 'no heartbeat change - nothing new to commit, still checking for pending work to push'
    }

    # 4) Push whatever is now ahead of origin/main -- the heartbeat commit (if
    #    any, from step 3) AND any other work this worktree was already carrying
    #    (v2.0: pushing pre-existing committed work is now the intended behavior,
    #    not a side effect -- Gabriel ratified 2026-08-23, relying on the existing
    #    pre-push hook suite as the safety net, same gate every manual push
    #    already goes through; no additional review/marker gate added). Checked
    #    explicitly first so a no-op day logs cleanly instead of a wasted push
    #    attempt. NO rebase/reset fallback here ever. v3.2 (OI-353): if the remote
    #    moved during the ~11-min pre-push gate (a lost race -- two consecutive
    #    daily runs, 09-22 and 09-23, died exactly this way), re-run the SAME
    #    merge-based reconcile once and push once more. Bounded to ONE retry: a
    #    second loss, a non-race failure, or a reconcile that is not clean fails
    #    loud as before and waits for the next run or a human.
    $ahead = git -C $repo log 'origin/main..HEAD' --oneline
    if (-not $ahead) { Log 'nothing ahead of origin/main - nothing to push'; Write-BackupPushOk; exit $pubExit }
    $aheadCount = ($ahead | Measure-Object).Count
    Log ("pushing " + $aheadCount + " commit(s) ahead of origin/main")
    $pushExit = Invoke-BackupPush $repo
    if ($pushExit -ne 0) {
        Log 'backup push FAILED - pending main work NOT on GitHub (heartbeat unaffected: published above); needs a session to reconcile'
        Write-BackupPushFailed 'git push origin main failed'
    } else {
        Log 'OK - pushed'
        Write-BackupPushOk
    }
    exit $pubExit
}
catch {
    Log ('ERROR (backup step, fail-open): ' + $_.Exception.Message)
    Write-BackupPushFailed ('unhandled error: ' + $_.Exception.Message)
    exit $pubExit
}
