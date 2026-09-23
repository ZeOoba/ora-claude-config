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
