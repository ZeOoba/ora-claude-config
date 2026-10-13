# Unit tests for push-fleet-heartbeat.ps1's backup-push race handling (OI-353, added 2026-09-23).
# Loads ONLY the function definitions via the PowerShell AST -- the script's main body (which
# publishes the heartbeat and pushes to GitHub) never runs. Git behaviour is exercised against
# throwaway repos under $env:TEMP with a local bare "origin"; nothing touches a real remote.
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File test-push-fleet-heartbeat-ps1.ps1   (exit 0 = all pass)
$ErrorActionPreference = 'Stop'
$target = Join-Path $PSScriptRoot 'push-fleet-heartbeat.ps1'
$ast = [System.Management.Automation.Language.Parser]::ParseFile($target, [ref]$null, [ref]$null)
$fns = $ast.FindAll({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true)
foreach ($f in $fns) { . ([scriptblock]::Create($f.Extent.Text)) }
# The script itself runs under the default 'Continue' (git writes progress to stderr), so the
# functions under test must too -- 'Stop' would turn git's stderr chatter into exceptions.
$ErrorActionPreference = 'Continue'
# Log is defined in the script against a $log path; capture into memory instead.
$script:logLines = @()
function Log($m) { $script:logLines += $m }

$fail = 0
function Expect($label, $cond) {
    if ($cond) { Write-Output "  PASS $label" } else { Write-Output "  FAIL $label"; $script:fail++ }
}
function Has($name) { $null -ne (Get-Command $name -CommandType Function -ErrorAction SilentlyContinue) }

$roots = @()
function G($dir) { $ErrorActionPreference = 'Continue'; git -C $dir @args 2>&1 | Out-Null }
function NewRace([switch]$failingPrePush) {
    $ErrorActionPreference = 'Continue'
    $root = Join-Path $env:TEMP ('hb-race-' + [guid]::NewGuid())
    $script:roots += $root
    $bare = Join-Path $root 'origin.git'; $a = Join-Path $root 'a'; $b = Join-Path $root 'b'
    New-Item -ItemType Directory -Path $root | Out-Null
    $nh = Join-Path $root 'nohooks'; New-Item -ItemType Directory -Path $nh | Out-Null
    git init -q --bare -b main $bare 2>&1 | Out-Null
    git clone -q $bare $a 2>&1 | Out-Null
    foreach ($d in @($a)) { G $d config user.email t@t; G $d config user.name t; G $d config core.hooksPath $nh }
    Set-Content (Join-Path $a 'hb.json') '1'; Set-Content (Join-Path $a 'other.txt') 'x'
    G $a add -A; G $a commit -q -m init; G $a push -q origin main
    git clone -q $bare $b 2>&1 | Out-Null
    G $b config user.email t@t; G $b config user.name t; G $b config core.hooksPath $nh
    $counter = Join-Path $root 'prepush-runs.txt'
    if ($failingPrePush) {
        $hook = Join-Path $nh 'pre-push'
        [IO.File]::WriteAllText($hook, "#!/bin/sh`necho run >> '" + ($counter.Replace([string][char]92, '/')) + "'`nexit 1`n")
    }
    return @{ a = $a; b = $b; counter = $counter }
}

try {
# --- classifier: which push failures are a lost race (worth one reconcile + retry)
Expect 'Test-PushRaceRejection exists' (Has 'Test-PushRaceRejection')
if (Has 'Test-PushRaceRejection') {
    Expect 'cannot-lock-ref (the 09-22/09-23 incident) is a race' (Test-PushRaceRejection @(
        " ! [remote rejected] main -> main (cannot lock ref 'refs/heads/main': is at 6351579 but expected 032b9fa)"))
    Expect 'fetch-first rejection is a race' (Test-PushRaceRejection @(' ! [rejected]        main -> main (fetch first)'))
    Expect 'non-fast-forward rejection is a race' (Test-PushRaceRejection @(' ! [rejected]        main -> main (non-fast-forward)'))
    Expect 'pre-push hook failure is NOT a race' (-not (Test-PushRaceRejection @('error: failed to push some refs', 'hook-tests-gate: 130 pass, 4 fail')))
    Expect 'auth failure is NOT a race' (-not (Test-PushRaceRejection @('remote: Permission denied', 'fatal: unable to access')))
    Expect 'empty output is NOT a race' (-not (Test-PushRaceRejection @()))
}

# --- reconcile: the step-1 logic, now callable again before the retry push
Expect 'Invoke-MainReconcile exists' (Has 'Invoke-MainReconcile')
if (Has 'Invoke-MainReconcile') {
    # remote moved, local has nothing new -> ff
    $r = NewRace
    Set-Content (Join-Path $r.b 'other.txt') 'y'; G $r.b commit -qam remote; G $r.b push -q origin main
    G $r.a fetch -q origin
    Expect 'ff case returns ok' ((Invoke-MainReconcile $r.a) -eq 'ok')
    Expect 'ff case lands on origin/main' ((git -C $r.a rev-parse HEAD) -eq (git -C $r.a rev-parse origin/main))

    # the incident shape: local heartbeat commit + remote moved on another file -> clean merge, then push works
    $r = NewRace
    Set-Content (Join-Path $r.a 'hb.json') '2'; G $r.a commit -qam hb
    Set-Content (Join-Path $r.b 'other.txt') 'y'; G $r.b commit -qam remote; G $r.b push -q origin main
    Expect 'diverged, disjoint files returns ok' ((Invoke-MainReconcile $r.a) -eq 'ok')
    git -C $r.a merge-base --is-ancestor origin/main HEAD 2>&1 | Out-Null
    Expect 'after reconcile, HEAD contains origin/main' ($LASTEXITCODE -eq 0)
    git -C $r.a push -q origin main 2>&1 | Out-Null
    Expect 'after reconcile, the retry push succeeds' ($LASTEXITCODE -eq 0)
    Expect 'reconcile never rebases: local hb commit keeps its sha' ((git -C $r.a log --format=%s origin/main) -contains 'hb')

    # real conflict -> 'conflict', tree left clean, HEAD unchanged
    $r = NewRace
    Set-Content (Join-Path $r.a 'hb.json') 'L'; G $r.a commit -qam local
    Set-Content (Join-Path $r.b 'hb.json') 'R'; G $r.b commit -qam remote; G $r.b push -q origin main
    $before = git -C $r.a rev-parse HEAD
    Expect 'conflict returns conflict' ((Invoke-MainReconcile $r.a) -eq 'conflict')
    Expect 'conflict leaves HEAD unchanged' ((git -C $r.a rev-parse HEAD) -eq $before)
    Expect 'conflict leaves the tree clean' (-not (git -C $r.a status --porcelain))
    # merge refused by a local change it would overwrite -> 'merge-failed' (not 'conflict')
    $r = NewRace
    Set-Content (Join-Path $r.a 'hb.json') '2'; G $r.a commit -qam hb
    Set-Content (Join-Path $r.b 'other.txt') 'y'; G $r.b commit -qam remote; G $r.b push -q origin main
    Set-Content (Join-Path $r.a 'other.txt') 'dirty-local'
    $before = git -C $r.a rev-parse HEAD
    Expect 'blocked merge returns merge-failed' ((Invoke-MainReconcile $r.a) -eq 'merge-failed')
    Expect 'blocked merge leaves HEAD unchanged' ((git -C $r.a rev-parse HEAD) -eq $before)

    # unreachable origin -> 'fetch-failed', never a stale 'ok'
    $r = NewRace
    G $r.a remote set-url origin (Join-Path $r.a 'no-such-remote.git')
    Expect 'failed fetch returns fetch-failed' ((Invoke-MainReconcile $r.a) -eq 'fetch-failed')
}

# --- Invoke-BackupPush: run the real push/retry path against the temp origin
Expect 'Invoke-BackupPush exists' (Has 'Invoke-BackupPush')
if (Has 'Invoke-BackupPush') {
    # lost race (the incident): remote moved on another file after our last fetch -> one retry lands it
    $r = NewRace
    Set-Content (Join-Path $r.a 'hb.json') '2'; G $r.a commit -qam hb
    Set-Content (Join-Path $r.b 'other.txt') 'y'; G $r.b commit -qam remote; G $r.b push -q origin main
    $script:logLines = @()
    $rc = Invoke-BackupPush $r.a
    Expect ('race: retry push succeeds (rc=' + $rc + ')') ($rc -eq 0)
    G $r.b fetch -q origin
    Expect 'race: the hb commit is on origin' ((git -C $r.b log --format=%s origin/main) -contains 'hb')
    Expect 'race: log says it retried' (@($script:logLines | Where-Object { $_ -match 'lost a race' }).Count -eq 1)
    Expect 'race: push output streamed to the log' (@($script:logLines | Where-Object { $_ -match '^push: ' }).Count -ge 1)

    # a failing pre-push gate is NOT a race: exactly one gate run, no retry
    $r = NewRace -failingPrePush
    Set-Content (Join-Path $r.a 'hb.json') '2'; G $r.a commit -qam hb
    $script:logLines = @()
    $rc = Invoke-BackupPush $r.a
    $runs = @(Get-Content $r.counter -ErrorAction SilentlyContinue).Count
    Expect ('gate failure: nonzero rc (rc=' + $rc + ')') ($rc -ne 0)
    Expect ('gate failure: gate ran exactly once (' + $runs + ')') ($runs -eq 1)
    Expect 'gate failure: no retry logged' (@($script:logLines | Where-Object { $_ -match 'lost a race' }).Count -eq 0)

    # lost race whose reconcile hits a real conflict: no retry push, tree untouched
    $r = NewRace
    Set-Content (Join-Path $r.a 'hb.json') 'L'; G $r.a commit -qam local
    Set-Content (Join-Path $r.b 'hb.json') 'R'; G $r.b commit -qam remote; G $r.b push -q origin main
    $before = git -C $r.a rev-parse HEAD
    $script:logLines = @()
    $rc = Invoke-BackupPush $r.a
    Expect 'race+conflict: nonzero rc' ($rc -ne 0)
    Expect 'race+conflict: no retry push attempted' (@($script:logLines | Where-Object { $_ -match '^push-retry: ' }).Count -eq 0)
    Expect 'race+conflict: HEAD unchanged, tree clean' (((git -C $r.a rev-parse HEAD) -eq $before) -and -not (git -C $r.a status --porcelain))
}

# --- self-heal: a heartbeat file left staged/modified by a KILLED run (0xC000013A between
#     `git add` and `git commit --only`) must not wedge the step-1 reconcile forever. The 2026-10-07
#     incident: git refused every merge because the staged hb.json would be overwritten, so no
#     later run ever reached the emit/commit/push steps.
Expect 'Clear-StaleHeartbeatState exists' (Has 'Clear-StaleHeartbeatState')
if (Has 'Clear-StaleHeartbeatState') {
    function Age($path, $minutes) { (Get-Item -LiteralPath $path).LastWriteTime = (Get-Date).AddMinutes(-$minutes) }

    # the incident shape: stale staged hb + remote moved hb
    $r = NewRace
    Set-Content (Join-Path $r.b 'hb.json') 'remote-hb'; G $r.b commit -qam remote; G $r.b push -q origin main
    Set-Content (Join-Path $r.a 'hb.json') 'killed-run'; G $r.a add -- hb.json
    Age (Join-Path $r.a 'hb.json') 2880
    $before = git -C $r.a rev-parse HEAD
    Expect 'repro: a staged stale hb blocks the step-1 reconcile' ((Invoke-MainReconcile $r.a) -ne 'ok')
    $script:logLines = @()
    Expect 'stale staged hb is cleared' ((Clear-StaleHeartbeatState $r.a 'hb.json') -eq 'cleared')
    Expect 'cleared: HEAD unchanged' ((git -C $r.a rev-parse HEAD) -eq $before)
    Expect 'cleared: tree clean' (-not (git -C $r.a status --porcelain))
    Expect 'cleared: content is the committed one' ((Get-Content (Join-Path $r.a 'hb.json')) -eq '1')
    Expect 'cleared: the discard is logged' (@($script:logLines | Where-Object { $_ -match 'stale heartbeat' }).Count -ge 1)
    Expect 'after clearing, the step-1 reconcile succeeds' ((Invoke-MainReconcile $r.a) -eq 'ok')

    # an unstaged (half-written) stale modification is cleared too
    $r = NewRace
    Set-Content (Join-Path $r.a 'hb.json') 'half-written'; Age (Join-Path $r.a 'hb.json') 120
    Expect 'stale unstaged hb is cleared' ((Clear-StaleHeartbeatState $r.a 'hb.json') -eq 'cleared')
    Expect 'unstaged cleared: tree clean' (-not (git -C $r.a status --porcelain))

    # a FRESH change may belong to a sibling run that is mid-flight (daily task + guard script 3): leave it
    $r = NewRace
    Set-Content (Join-Path $r.a 'hb.json') 'in-flight'; G $r.a add -- hb.json
    Expect 'fresh dirty hb is left alone' ((Clear-StaleHeartbeatState $r.a 'hb.json') -eq 'fresh')
    Expect 'fresh: still staged with its content' (((@(git -C $r.a diff --cached --name-only)) -contains 'hb.json') -and ((Get-Content (Join-Path $r.a 'hb.json')) -eq 'in-flight'))

    # scope: ONLY the heartbeat path is touched
    $r = NewRace
    Set-Content (Join-Path $r.a 'hb.json') 'stale'; Age (Join-Path $r.a 'hb.json') 300
    Set-Content (Join-Path $r.a 'other.txt') 'someone-elses-wip'; G $r.a add -- other.txt
    Set-Content (Join-Path $r.a 'untracked.txt') 'u'
    [void](Clear-StaleHeartbeatState $r.a 'hb.json')
    $st = @(git -C $r.a status --porcelain)
    Expect 'scope: other staged work survives' ($st -contains 'M  other.txt')
    Expect 'scope: untracked file survives' ($st -contains '?? untracked.txt')
    Expect 'scope: hb.json no longer listed' (-not ($st -match 'hb\.json'))
    Expect 'scope: other.txt content intact' ((Get-Content (Join-Path $r.a 'other.txt')) -eq 'someone-elses-wip')

    # clean tree: no-op, silent
    $r = NewRace
    $script:logLines = @()
    Expect 'clean tree returns clean' ((Clear-StaleHeartbeatState $r.a 'hb.json') -eq 'clean')
    Expect 'clean tree logs nothing' (@($script:logLines).Count -eq 0)

    # a heartbeat path that was never committed must NOT be deleted
    $r = NewRace
    Set-Content (Join-Path $r.a 'newhb.json') 'x'; Age (Join-Path $r.a 'newhb.json') 300
    $rc = Clear-StaleHeartbeatState $r.a 'newhb.json'
    Expect 'untracked hb is never deleted' ((Test-Path (Join-Path $r.a 'newhb.json')) -and ($rc -ne 'cleared'))

    # a heartbeat path staged as a NEW file (absent from HEAD) must not be deleted either
    $r = NewRace
    Set-Content (Join-Path $r.a 'newhb.json') 'x'; G $r.a add -- newhb.json; Age (Join-Path $r.a 'newhb.json') 300
    $rc = Clear-StaleHeartbeatState $r.a 'newhb.json'
    Expect 'staged-new hb (not in HEAD) is never deleted' ((Test-Path (Join-Path $r.a 'newhb.json')) -and ($rc -ne 'cleared'))

    # an unmerged (conflicted) hb is left for a human, with its conflict state intact
    $r = NewRace
    Set-Content (Join-Path $r.a 'hb.json') 'L'; G $r.a commit -qam local
    Set-Content (Join-Path $r.b 'hb.json') 'R'; G $r.b commit -qam remote; G $r.b push -q origin main
    G $r.a fetch -q origin; G $r.a merge origin/main
    Age (Join-Path $r.a 'hb.json') 300
    Expect 'repro: the merge left hb unmerged' ([bool](@(git -C $r.a status --porcelain) -match '^UU hb\.json'))
    Expect 'unmerged hb returns restore-failed' ((Clear-StaleHeartbeatState $r.a 'hb.json') -eq 'restore-failed')
    Expect 'unmerged state is kept' ([bool](@(git -C $r.a status --porcelain) -match '^UU hb\.json'))

    # fail-open: a bad repo path must not throw
    $threw = $false
    try { [void](Clear-StaleHeartbeatState (Join-Path $env:TEMP 'no-such-repo-xyz') 'hb.json') } catch { $threw = $true }
    Expect 'bad repo path does not throw' (-not $threw)
}

# --- main-body wiring: step 1 uses the function, step 4 retries exactly once through it
$calls = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.CommandAst] -and
    $n.GetCommandName() -eq 'Invoke-MainReconcile' }, $true))
Expect ('Invoke-MainReconcile called twice: step 1 + inside Invoke-BackupPush (' + $calls.Count + ')') ($calls.Count -eq 2)
$pushes = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.CommandAst] -and
    $n.GetCommandName() -eq 'git' -and $n.Extent.Text -match '\bpush\s+origin\s+main\b' }, $true))
Expect ('exactly two push commands: first try + one bounded retry (' + $pushes.Count + ')') ($pushes.Count -eq 2)
$raceCalls = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.CommandAst] -and
    $n.GetCommandName() -eq 'Test-PushRaceRejection' }, $true))
Expect 'main body gates the retry on Test-PushRaceRejection' ($raceCalls.Count -ge 1)
$src = Get-Content -Raw $target
Expect 'no rebase anywhere in the script body (merge-only doctrine)' ($src -notmatch '(?m)^[^#\r\n]*\bgit\b[^#\r\n]*\brebase\b')
Expect 'never --no-verify' ($src -notmatch '--no-verify')

# --- self-heal wiring: called once, in the MAIN body (not inside a function), before the step-1 reconcile
function InFn($n) { for ($p = $n.Parent; $p; $p = $p.Parent) { if ($p -is [System.Management.Automation.Language.FunctionDefinitionAst]) { return $true } }; return $false }
$clr = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.CommandAst] -and
    $n.GetCommandName() -eq 'Clear-StaleHeartbeatState' }, $true))
Expect ('Clear-StaleHeartbeatState called exactly once (' + $clr.Count + ')') ($clr.Count -eq 1)
$step1 = @($calls | Where-Object { -not (InFn $_) })
Expect 'exactly one step-1 Invoke-MainReconcile in the main body' ($step1.Count -eq 1)
Expect 'self-heal sits in the main body, before the step-1 reconcile' (($clr.Count -eq 1) -and ($step1.Count -eq 1) -and
    (-not (InFn $clr[0])) -and ($clr[0].Extent.StartOffset -lt $step1[0].Extent.StartOffset))
# blast-radius limits: the heal is a pathspec-scoped restore, never a broad discard
Expect 'no reset --hard, clean -f, stash or broad checkout in the script' ($src -notmatch '(?m)^[^#\r\n]*\bgit\b[^#\r\n]*(\breset\s+--hard\b|\bclean\s+-[a-z]*f|\bstash\b|\bcheckout\s+(--\s+)?\.(\s|$))')
$restores = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.CommandAst] -and
    $n.GetCommandName() -eq 'git' -and $n.Extent.Text -match '\brestore\b' }, $true))
Expect ('exactly one git restore, and it is pathspec-scoped (' + $restores.Count + ')') (($restores.Count -eq 1) -and ($restores[0].Extent.Text -match '\s--\s+\$\w+'))
}
finally {
    foreach ($d in $roots) {
        Remove-Item -Recurse -Force $d -ErrorAction SilentlyContinue
        if (Test-Path $d) { Write-Output "  NOTE temp repo not removed (AV lock?): $d" }
    }
}
if ($fail) { Write-Output "FAILED: $fail check(s)"; exit 1 }
Write-Output 'ALL PASS'
exit 0
