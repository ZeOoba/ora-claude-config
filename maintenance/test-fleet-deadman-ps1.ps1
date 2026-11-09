# Unit tests for fleet-deadman.ps1 helper functions (added 2026-09-22).
# Loads ONLY the function definitions via the PowerShell AST -- the script's main body
# (which writes the log and the desktop alert) never runs.
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File test-fleet-deadman-ps1.ps1   (exit 0 = all pass)
$ErrorActionPreference = 'Stop'
$target = Join-Path $PSScriptRoot 'fleet-deadman.ps1'
$ast = [System.Management.Automation.Language.Parser]::ParseFile($target, [ref]$null, [ref]$null)
$fns = $ast.FindAll({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true)
foreach ($f in $fns) { . ([scriptblock]::Create($f.Extent.Text)) }

$fail = 0
function Expect($label, $cond) {
    if ($cond) { Write-Output "  PASS $label" } else { Write-Output "  FAIL $label"; $script:fail++ }
}
$script:tempFiles = @()
function Reg($tasks) {
    $p = Join-Path $env:TEMP ("deadman-test-" + [guid]::NewGuid() + '.json')
    (@{ scheduledTasks = $tasks } | ConvertTo-Json -Depth 5) | Set-Content -Path $p -Encoding utf8
    $script:tempFiles += $p   # removed in the finally block at the end (merge-gate R3)
    return $p
}
try {
$future = [DateTimeOffset]::UtcNow.AddHours(48).ToUnixTimeMilliseconds()

# --- pause carve-out: ora-am-brief never vetoes a CC pause (mirrors _shared/fleet_pause.py)
$r = Reg @(
    @{ id = 'ora-am-brief'; cronExpression = '0 6 * * *'; enabled = $true },
    @{ id = 'a'; cronExpression = '0 5 * * 1'; enabled = $false },
    @{ id = 'r'; fireAt = $future; enabled = $true })
Expect 'cc pause with ora-am-brief carved out is a pause' ($null -ne (Test-BoundedPause $r 'cc'))
Expect 'carve-out does not apply to lams'                 ($null -eq (Test-BoundedPause $r 'lams'))
$r2 = Reg @(
    @{ id = 'ora-am-brief'; cronExpression = '0 6 * * *'; enabled = $true },
    @{ id = 'a'; cronExpression = '0 5 * * 1'; enabled = $true },
    @{ id = 'r'; fireAt = $future; enabled = $true })
Expect 'another enabled recurring task still means live'  ($null -eq (Test-BoundedPause $r2 'cc'))

# --- bounded child process: a hang must come back as a timeout, never block the run
$py = 'C:\Users\Owner\AppData\Local\Programs\Python\Python313\python.exe'
$res = Invoke-PyBounded $py @('-c', 'import time; time.sleep(30)') 3
Expect 'hung child returns TimedOut'                      ($res.TimedOut -eq $true)
# 120s = the production bound. A 20s budget false-failed under load (merge-gate R3), and a
# timeout here must be distinguishable from a logic failure, so TimedOut goes in the label.
# R4: the old payload carried quotes that were mangled into a SyntaxError, so "hi" was only
# ever matched on STDERR and stdout capture was never tested. Quote-free payload, and
# stdout / stderr asserted separately.
$res = Invoke-PyBounded $py @('-c', 'import sys; print(123456); sys.stderr.write(chr(81)*3); raise SystemExit(1)') 120
Expect ('normal child: exit code and STDOUT captured (TimedOut=' + $res.TimedOut + ', Rc=' + $res.Rc + ')') (($res.TimedOut -eq $false) -and ($res.Rc -eq 1) -and ($res.Out -match '123456'))
Expect 'normal child: STDERR captured too'                 ($res.Out -match 'QQQ')

# R4 correctness-F2: Windows argv quoting must round-trip trailing backslashes, embedded
# quotes and spaces.
# R5: include arguments that NEED quoting and contain backslashes (a quoted trailing run,
# an interior backslash), each followed by another argument, so a merge would show.
$tricky = @('C:\dir\', 'a"b', 'two words', 'x\\"y', '', 'C:\my dir\', 'next', 'a\b c', 'C:\a b\\', 'tail')
$res = Invoke-PyBounded $py (@('-c', 'import sys, json; print(json.dumps(sys.argv[1:]))') + $tricky) 60
$got = try { @($res.Out.Trim() | ConvertFrom-Json) } catch { @('PARSE-FAIL: ' + $res.Out) }
Expect ('arguments round-trip exactly (got=' + ($got -join '|') + ')') ((($got -join '|') -eq ($tricky -join '|')) -and ($got.Count -eq $tricky.Count))

# R4 correctness-F1: a grandchild that inherits the output pipes must not defeat the bound.
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$res = Invoke-PyBounded $py @('-c', 'import subprocess, sys; subprocess.Popen([sys.executable, chr(45)+chr(99), chr(105)+chr(109)+chr(112)+chr(111)+chr(114)+chr(116)+chr(32)+chr(116)+chr(105)+chr(109)+chr(101)+chr(59)+chr(116)+chr(105)+chr(109)+chr(101)+chr(46)+chr(115)+chr(108)+chr(101)+chr(101)+chr(112)+chr(40)+chr(50)+chr(48)+chr(41)]); print(1)') 3
$sw.Stop()
Expect ('pipe-holding grandchild cannot exceed the bound (elapsed=' + [int]$sw.Elapsed.TotalSeconds + 's, TimedOut=' + $res.TimedOut + ')') (($sw.Elapsed.TotalSeconds -lt 12) -and ($res.TimedOut -eq $true))

# R5: on a timeout of a still-running child, the whole TREE is killed -- a grandchild must
# not survive. The parent records its grandchild's PID, then hangs past the bound.
$pidFile = Join-Path $env:TEMP ('dm-gc-' + [guid]::NewGuid() + '.pid')
$script:tempFiles += $pidFile
# R6: passed with -c, not a freshly written .py -- real-time AV scanning of a new script in
# %TEMP% delayed python startup past the bound (observed: no output at all for 6s), which
# made this check flaky. ConvertTo-WinArg now quotes the embedded quotes correctly.
$gcCode = "import subprocess, sys, time; g = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); open(sys.argv[1], 'w').write(str(g.pid)); time.sleep(60)"
$res = Invoke-PyBounded $py @('-c', $gcCode, $pidFile) 20
Start-Sleep -Milliseconds 1500
$gcPid = if (Test-Path $pidFile) { [int](Get-Content -Raw $pidFile).Trim() } else { 0 }
$alive = if ($gcPid) { [bool](Get-Process -Id $gcPid -ErrorAction SilentlyContinue) } else { $true }
if ($alive -and $gcPid) { Stop-Process -Id $gcPid -Force -ErrorAction SilentlyContinue }   # never leak it
Expect ('timeout kills the grandchild too (TimedOut=' + $res.TimedOut + ', gcPid=' + $gcPid + ', alive=' + $alive + ')') (($res.TimedOut -eq $true) -and ($gcPid -gt 0) -and (-not $alive))

# R4 test-validity-F1: the phantom-count parse is a helper; stdout loss must not zero the count.
$ph = Get-PhantomSummary @{ TimedOut = $false; Rc = 1; Out = "header`nphantom : 3`n  2026-09-20 10:00 ora-x [never-confirmed]`n" }
Expect 'phantom summary parses count and detail from stdout' (($ph.Rc -eq 1) -and ($ph.Count -eq 3) -and (@($ph.Detail).Count -eq 1))
$ph = Get-PhantomSummary @{ TimedOut = $true; Rc = $null; Out = '' }
Expect 'phantom summary: timeout is exit 2 with count 0'      (($ph.Rc -eq 2) -and ($ph.Count -eq 0))

# --- R7: a carve-out task (ora-am-brief) that dies DURING a bounded pause must still alarm.
# The carve-out made the fleet read as paused, which suppressed the only alarm that would
# have caught a dead Daily Brief for up to 14 days.
$old = [DateTime]::UtcNow.AddHours(-40).ToString('o')
$new = [DateTime]::UtcNow.AddHours(-2).ToString('o')
$r4 = Reg @(
    @{ id = 'ora-am-brief'; cronExpression = '0 6 * * *'; enabled = $true; lastRunAt = $old },
    @{ id = 'a'; cronExpression = '0 5 * * 1'; enabled = $false; lastRunAt = $old },
    @{ id = 'r'; fireAt = $future; enabled = $true })
$stale = @(Get-StaleCarveOuts $r4 'cc' 30)
Expect ('stale carve-out task is reported during a pause (' + ($stale -join ',') + ')') (($stale.Count -eq 1) -and ($stale[0] -match '^ora-am-brief'))
$r5 = Reg @(
    @{ id = 'ora-am-brief'; cronExpression = '0 6 * * *'; enabled = $true; lastRunAt = $new },
    @{ id = 'a'; cronExpression = '0 5 * * 1'; enabled = $false; lastRunAt = $old },
    @{ id = 'r'; fireAt = $future; enabled = $true })
Expect 'fresh carve-out task is not reported'            (@(Get-StaleCarveOuts $r5 'cc' 30).Count -eq 0)
$r6 = Reg @(
    @{ id = 'ora-am-brief'; cronExpression = '0 6 * * *'; enabled = $true },
    @{ id = 'r'; fireAt = $future; enabled = $true })
Expect 'carve-out task that never ran is reported'       (@(Get-StaleCarveOuts $r6 'cc' 30).Count -eq 1)
Expect 'no carve-outs on lams -> nothing reported'       (@(Get-StaleCarveOuts $r4 'lams' 30).Count -eq 0)
$r7 = Reg @(
    @{ id = 'ora-am-brief'; cronExpression = '0 6 * * *'; enabled = $false; lastRunAt = $old },
    @{ id = 'r'; fireAt = $future; enabled = $true })
Expect 'a DISABLED carve-out task is not reported (it is paused on purpose)' (@(Get-StaleCarveOuts $r7 'cc' 30).Count -eq 0)
Expect 'a DISABLED carve-out task does not count as enabled' (-not (Test-HasEnabledCarveOut $r7 'cc'))
Expect 'fleet with an enabled carve-out is not fully paused for send-log purposes' (Test-HasEnabledCarveOut $r5 'cc')
Expect 'lams has no enabled carve-out'                   (-not (Test-HasEnabledCarveOut $r5 'lams'))
# R8 (correctness): the taskId fallback in the carve-out helpers must be exercised too.
$r8 = Reg @(
    @{ taskId = 'ora-am-brief'; cronExpression = '0 6 * * *'; enabled = $true; lastRunAt = $old },
    @{ taskId = 'a'; cronExpression = '0 5 * * 1'; enabled = $false; lastRunAt = $old },
    @{ taskId = 'r'; fireAt = $future; enabled = $true })
$st8 = @(Get-StaleCarveOuts $r8 'cc' 30)
Expect ('taskId-keyed stale carve-out is reported (' + ($st8 -join ',') + ')') (($st8.Count -eq 1) -and ($st8[0] -match '^ora-am-brief'))
# R8 (race): one parsed snapshot feeds every check. Helpers accept the parsed task list,
# and give the same answers as when handed the path.
$snap = Get-RegistryTasks $r4
Expect 'helpers accept a pre-parsed snapshot (pause)'      ($null -ne (Test-BoundedPause $snap 'cc'))
Expect 'helpers accept a pre-parsed snapshot (stale)'      (@(Get-StaleCarveOuts $snap 'cc' 30).Count -eq 1)
Expect 'helpers accept a pre-parsed snapshot (enabled)'    (Test-HasEnabledCarveOut $snap 'cc')
$torn = Join-Path $env:TEMP ('deadman-test-' + [guid]::NewGuid() + '.json'); $script:tempFiles += $torn
Set-Content -Path $torn -Value '{"scheduledTasks": [ {"id": "ora-am-br' -Encoding utf8
Expect 'a torn registry file is not read as parseable'     ($null -eq (Get-RegistryTasks $torn))

# --- taskId-keyed registries get the same carve-out as id-keyed ones (parity with fleet_pause.py)
$r3 = Reg @(
    @{ taskId = 'ora-am-brief'; cronExpression = '0 6 * * *'; enabled = $true },
    @{ taskId = 'a'; cronExpression = '0 5 * * 1'; enabled = $false },
    @{ taskId = 'r'; fireAt = $future; enabled = $true })
Expect 'taskId-keyed carve-out is honoured'              ($null -ne (Test-BoundedPause $r3 'cc'))

# --- main-body wiring, extracted so it is testable (merge-gate finding 2026-09-22)
Expect 'probe timeout maps to exit 2 (could not look)'   ((Resolve-ProbeRc @{ TimedOut = $true;  Rc = $null }) -eq 2)
Expect 'probe normal exit passes through'                ((Resolve-ProbeRc @{ TimedOut = $false; Rc = 0 }) -eq 0)
$v = Get-PublishVerdict @{ TimedOut = $true; Rc = $null; Out = '' }
Expect 'publish timeout is a problem, not ok'            (($v.Ok -eq $false) -and ($v.Problem -match 'TIMED OUT'))
$v = Get-PublishVerdict @{ TimedOut = $false; Rc = 0; Out = 'OK' }
Expect 'publish exit 0 is ok'                            (($v.Ok -eq $true) -and ($null -eq $v.Problem))
$v = Get-PublishVerdict @{ TimedOut = $false; Rc = 1; Out = 'stale' }
Expect 'publish exit 1 is a problem'                     (($v.Ok -eq $false) -and ($v.Problem -match 'HEARTBEAT PUBLISH FAILED'))

$v = Get-PublishVerdict @{ TimedOut = $false; Rc = 3; Out = '' }
Expect 'publish unexpected exit is a problem, not ok'    (($v.Ok -eq $false) -and ($v.Problem -match 'unexpected exit 3'))

# --- (6) live branch off-box (push-live-backup.py --check, 2026-11-08)
$v = Get-OffboxVerdict @{ TimedOut = $true; Rc = $null; Out = '' }
Expect 'offbox timeout is a problem, not ok'             (($v.Ok -eq $false) -and ($v.Problem -match 'TIMED OUT'))
$v = Get-OffboxVerdict @{ TimedOut = $false; Rc = 0; Out = "[CONTAINED] 0 pending commit(s)`nRESULT_JSON={}" }
Expect 'offbox exit 0 is ok'                             (($v.Ok -eq $true) -and ($null -eq $v.Problem))
$v = Get-OffboxVerdict @{ TimedOut = $false; Rc = 1; Out = "[NOT_OFFBOX] NOT_OFFBOX: 41 live commit(s)`nRESULT_JSON={}" }
Expect 'offbox exit 1 is a problem carrying the reason'  (($v.Ok -eq $false) -and ($v.Problem -match 'LIVE BRANCH NOT OFF-BOX') -and ($v.Problem -match '41 live commit') -and ($v.Problem -notmatch 'RESULT_JSON'))
$v = Get-OffboxVerdict @{ TimedOut = $false; Rc = 2; Out = '[COULD_NOT_LOOK] fetch failed' }
Expect 'offbox exit 2 is could-not-look, not ok'         (($v.Ok -eq $false) -and ($v.Problem -match 'COULD NOT LOOK'))
$v = Get-OffboxVerdict @{ TimedOut = $false; Rc = 7; Out = '' }
Expect 'offbox unexpected exit is a problem, not ok'     (($v.Ok -eq $false) -and ($v.Problem -match 'unexpected exit 7'))

# --- AST checks on the scripts' main bodies (round-2 merge-gate findings, 2026-09-22) ---
# Regex over source text was defeated by trivial respellings; everything below walks the AST.
$T = [System.Management.Automation.Language.Ast]
function AllOf($root, [scriptblock]$pred) { @($root.FindAll($pred, $true)) }
function Cmds($root, $name) {
    AllOf $root { param($n) $n -is [System.Management.Automation.Language.CommandAst] -and $n.GetCommandName() -eq $name }
}
function InsideFunction($node, $fname) {
    $p = $node.Parent
    while ($p) { if ($p -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $p.Name -eq $fname) { return $true }; $p = $p.Parent }
    return $false
}

# Test-BoundedPause: every call must pass a NON-EMPTY label, positionally or as -label.
$tbp = Cmds $ast 'Test-BoundedPause'
$labelOk = ($tbp.Count -gt 0)
foreach ($c in $tbp) {
    $els = @($c.CommandElements | Select-Object -Skip 1)
    $named = @($els | Where-Object { $_ -is [System.Management.Automation.Language.CommandParameterAst] })
    $lblParam = @($named | Where-Object { $_.ParameterName -eq 'label' })
    if ($lblParam.Count -gt 0) {
        $idx = [array]::IndexOf($els, $lblParam[0])
        $val = if ($lblParam[0].Argument) { $lblParam[0].Argument } elseif ($idx + 1 -lt $els.Count) { $els[$idx + 1] } else { $null }
    } else {
        $positional = @($els | Where-Object { $_ -isnot [System.Management.Automation.Language.CommandParameterAst] })
        # when -reg is named, its value is the element right after it and is not the label
        $regParam = @($named | Where-Object { $_.ParameterName -eq 'reg' })
        if ($regParam.Count -gt 0) { $positional = @($positional | Where-Object { $_ -ne $els[[array]::IndexOf($els, $regParam[0]) + 1] }) ; $val = $positional[0] }
        else { $val = if ($positional.Count -ge 2) { $positional[1] } else { $null } }
    }
    if ($null -eq $val) { $labelOk = $false }
    elseif ($val -is [System.Management.Automation.Language.StringConstantExpressionAst] -and $val.Value -eq '') { $labelOk = $false }
}
Expect 'every Test-BoundedPause call passes a non-empty fleet label' $labelOk

# START must never reach a main verdict log. state-freshness-probe judges those logs by
# mtime, so a START written there by every killed run would keep a dead dead-man fresh.
# Rule: every string literal containing START sits inside a LogStart call, nowhere else.
function StartOnlyViaLogStart($root) {
    $strs = AllOf $root { param($n) ($n -is [System.Management.Automation.Language.StringConstantExpressionAst] -or
                                     $n -is [System.Management.Automation.Language.ExpandableStringExpressionAst]) -and
                                    $n.Value -imatch '\bSTART\b' -and             # any case, any position (R3-F4)
                                    $n.Value -notmatch '\.start\.log$' -and       # the start-log PATH itself
                                    -not ($n.Parent -is [System.Management.Automation.Language.MemberExpressionAst] -and
                                          $n.Parent.Member -eq $n) }             # a .NET member name, e.g. ::Start()
    if ($strs.Count -eq 0) { return $false }
    foreach ($s in $strs) {
        $p = $s.Parent; $ok = $false
        while ($p) { if ($p -is [System.Management.Automation.Language.CommandAst]) { $ok = ($p.GetCommandName() -eq 'LogStart'); break }; $p = $p.Parent }
        if (-not $ok) { return $false }
    }
    return $true
}
# Behavioural: LogStart must write to the start log and leave the main log untouched.
function LogStartIsolated($root) {
    $fn = AllOf $root { param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'LogStart' }
    if ($fn.Count -ne 1) { return $false }
    $main = Join-Path $env:TEMP ('dm-main-' + [guid]::NewGuid() + '.log')
    $st   = Join-Path $env:TEMP ('dm-start-' + [guid]::NewGuid() + '.log')
    $sb = [scriptblock]::Create('param($log, $startLog) ' + $fn[0].Extent.Text + '; LogStart ''START pid=1''')
    & $sb $main $st
    $ok = (-not (Test-Path $main)) -and (Test-Path $st) -and ((Get-Content -Raw $st) -match 'START pid=1')
    Remove-Item $main, $st -ErrorAction SilentlyContinue
    return $ok
}
$hbPath = Join-Path $PSScriptRoot 'push-fleet-heartbeat.ps1'
$hbAst = [System.Management.Automation.Language.Parser]::ParseFile($hbPath, [ref]$null, [ref]$null)
Expect 'START literals only ever go through LogStart (dead-man)'   (StartOnlyViaLogStart $ast)
Expect 'START literals only ever go through LogStart (heartbeat)'  (StartOnlyViaLogStart $hbAst)
Expect 'LogStart writes the start log, never the main log (dead-man)'  (LogStartIsolated $ast)
Expect 'LogStart writes the start log, never the main log (heartbeat)' (LogStartIsolated $hbAst)

# Main-body wiring: the helpers are only worth testing if the main body actually uses them.
$rcAssign = AllOf $ast { param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and
                                   $n.Left.Extent.Text -eq '$rc' -and -not (InsideFunction $n 'Get-PhantomSummary') }
Expect 'main body takes $rc from the phantom summary (which uses Resolve-ProbeRc)' (($rcAssign.Count -ge 1) -and
    (@($rcAssign | Where-Object { $_.Right.Extent.Text -notmatch '^\$ph\.Rc$' }).Count -eq 0))
$phAssign = AllOf $ast { param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and
                                   $n.Left.Extent.Text -eq '$ph' }
Expect 'main body builds $ph with Get-PhantomSummary from the probe result' (($phAssign.Count -eq 1) -and
    ($phAssign[0].Right.Extent.Text -match '^Get-PhantomSummary\s+\$r$'))
# R5: $count and $phantomDetail must come from the summary too -- `$count = 0` or `$r.Count`
# would silently suppress a PHANTOM DISPATCH alarm.
function AssignRhs($root, $lhs) {
    @(AllOf $root { param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and
                               $n.Left.Extent.Text -eq $lhs -and -not (InsideFunction $n 'Get-PhantomSummary') } |
      ForEach-Object { ($_.Operator.ToString()) + ' ' + $_.Right.Extent.Text.Trim() })
}
# Scope to the phantom block: the statement block that assigns $ph (the fleet loop above
# reuses the name $count for an unrelated task count).
$phBlock = if ($phAssign.Count -eq 1) { $b = $phAssign[0].Parent; while ($b -and $b -isnot [System.Management.Automation.Language.StatementBlockAst]) { $b = $b.Parent }; $b } else { $null }
$countRhs = if ($phBlock) { @(AssignRhs $phBlock '$count') } else { @() }
Expect ('phantom block takes $count only from $ph.Count (' + ($countRhs -join ' ; ') + ')') (
    ($countRhs.Count -ge 1) -and (@($countRhs | Where-Object { $_ -notmatch '^Equals \$ph\.Count$' }).Count -eq 0))
$detRhs = @(AssignRhs $ast '$phantomDetail' | Where-Object { $_ -notmatch '^Equals @\(\)$' })
Expect ('main body fills $phantomDetail only from $ph.Detail (' + ($detRhs -join ' ; ') + ')') (
    ($detRhs.Count -ge 1) -and (@($detRhs | Where-Object { $_ -notmatch '\$ph\.Detail' }).Count -eq 0))

# R5: the publish verdict must be computed from the PUBLISH call's result, not the probe's.
$gpvCalls = @(Cmds $ast 'Get-PublishVerdict' | Where-Object { -not (InsideFunction $_ 'Get-PublishVerdict') })
$prRhs = @(AssignRhs $ast '$pr')
Expect ('Get-PublishVerdict is fed $pr, and $pr comes from Invoke-PyBounded on $pub (' + ($prRhs -join ' ; ') + ')') (
    ($gpvCalls.Count -ge 1) -and
    (@($gpvCalls | Where-Object { ((@($_.CommandElements | Select-Object -Skip 1 | ForEach-Object { $_.Extent.Text })) -join ' ') -ne '$pr' }).Count -eq 0) -and
    ($prRhs.Count -eq 1) -and ($prRhs[0] -match '^Equals Invoke-PyBounded \$py @\(\$pub,'))

$gps = AllOf $ast { param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Get-PhantomSummary' }
Expect 'Get-PhantomSummary derives its rc via Resolve-ProbeRc' (($gps.Count -eq 1) -and (@(Cmds $gps[0] 'Resolve-ProbeRc').Count -ge 1))
$gpv = @(Cmds $ast 'Get-PublishVerdict' | Where-Object { -not (InsideFunction $_ 'Get-PublishVerdict') })
$vOkIfs = AllOf $ast { param($n) $n -is [System.Management.Automation.Language.IfStatementAst] -and
                                 $n.Clauses[0].Item1.Extent.Text -match '^\$v\.Ok$' }
Expect 'main body calls Get-PublishVerdict and branches on its .Ok' (($gpv.Count -ge 1) -and ($vOkIfs.Count -ge 1))
# R3-F2: a not-ok verdict must actually land in $problems (else-branch), or a failed
# publish raises no alarm at all.
Expect 'a not-ok publish verdict is appended to $problems' (($vOkIfs.Count -ge 1) -and
    (@($vOkIfs | Where-Object { $_.ElseClause -and ($_.ElseClause.Extent.Text -match '\$problems\s*\+=\s*\$v\.Problem') }).Count -ge 1))

# (6) live off-box: the verdict must come from push-live-backup.py --check's own result and
# a not-ok verdict must land in $problems.
$govCalls = @(Cmds $ast 'Get-OffboxVerdict' | Where-Object { -not (InsideFunction $_ 'Get-OffboxVerdict') })
$lrRhs = @(AssignRhs $ast '$lr')
Expect ('Get-OffboxVerdict is fed $lr, and $lr comes from Invoke-PyBounded on $plb --check (' + ($lrRhs -join ' ; ') + ')') (
    ($govCalls.Count -ge 1) -and
    (@($govCalls | Where-Object { ((@($_.CommandElements | Select-Object -Skip 1 | ForEach-Object { $_.Extent.Text })) -join ' ') -ne '$lr' }).Count -eq 0) -and
    ($lrRhs.Count -eq 1) -and ($lrRhs[0] -match "^Equals Invoke-PyBounded \`$py @\(\`$plb, '--check'"))
$lvIfs = AllOf $ast { param($n) $n -is [System.Management.Automation.Language.IfStatementAst] -and
                                $n.Clauses[0].Item1.Extent.Text -match '^\$lv\.Ok$' }
Expect 'a not-ok off-box verdict is appended to $problems' (($lvIfs.Count -ge 1) -and
    (@($lvIfs | Where-Object { $_.ElseClause -and ($_.ElseClause.Extent.Text -match '\$problems\s*\+=\s*\$lv\.Problem') }).Count -ge 1))
$plbAssign = @(AssignRhs $ast '$plb')
Expect ('$plb points at maintenance\push-live-backup.py (' + ($plbAssign -join ' ; ') + ')') (
    ($plbAssign.Count -eq 1) -and ($plbAssign[0] -match "maintenance\\push-live-backup\.py'"))

# R3-F3: the pause call must pass the fleet's own label, and those labels must be the
# carve-out table's keys -- a typo'd or wrong property silently disables the carve-out.
$tbpTexts = @($tbp | ForEach-Object { ($_.Extent.Text -replace '\s+', ' ').Trim() })
Expect 'Test-BoundedPause is called exactly as Test-BoundedPause $regTasks $fleet.Label' (($tbpTexts.Count -ge 1) -and
    (@($tbpTexts | Where-Object { $_ -ne 'Test-BoundedPause $regTasks $fleet.Label' }).Count -eq 0))
# R8: the fleet loop parses each registry exactly once, and every pause/carve-out check
# reads that one snapshot (no re-read that could see a torn mid-rewrite file).
$loop = AllOf $ast { param($n) $n -is [System.Management.Automation.Language.ForEachStatementAst] -and $n.Variable.Extent.Text -eq '$fleet' }
$loopText = if ($loop.Count -eq 1) { $loop[0].Body.Extent.Text } else { '' }
Expect 'the fleet loop parses the registry exactly once (Get-RegistryTasks)' (
    (@(Cmds $loop[0] 'Get-RegistryTasks').Count -eq 1) -and ($loopText -notmatch 'ConvertFrom-Json'))
# R9 (correctness): an `if` expression unrolls a one-element array, so `$tasks = if (...)
# { $regTasks }` turned a 1-task registry into a bare object whose .Count is empty ("cc= tasks").
$tAssign = if ($loop.Count -eq 1) { AllOf $loop[0] { param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$tasks' } } else { @() }
Expect ('the loop builds $tasks as @($regTasks) (' + (@($tAssign | ForEach-Object { $_.Right.Extent.Text }) -join ' ; ') + ')') (
    ($tAssign.Count -eq 1) -and ($tAssign[0].Right.Extent.Text -eq '@($regTasks)'))
$one = Get-RegistryTasks (Reg @(@{ id = 'solo'; cronExpression = '0 5 * * 1'; enabled = $true }))
Expect 'a 1-task registry counts as 1 through @($regTasks)' (@($one).Count -eq 1)
# R9 (race): an unparseable registry is a PROBLEM, never a fall-back to the file mtime --
# a torn read of a just-rewritten file would otherwise read "0 tasks, last run 0h ago", OK,
# and could even clear an existing FLEET-DOWN alert.
$nullIf = if ($loop.Count -eq 1) { AllOf $loop[0] { param($n) $n -is [System.Management.Automation.Language.IfStatementAst] -and
                                      ($n.Clauses[0].Item1.Extent.Text -replace '\s+', ' ') -eq '$null -eq $regTasks' } } else { @() }
Expect 'an unparseable registry adds a problem and skips the fleet' (($nullIf.Count -eq 1) -and
    ($nullIf[0].Clauses[0].Item2.Extent.Text -match '\$problems\s*\+=') -and ($nullIf[0].Clauses[0].Item2.Extent.Text -match '\bcontinue\b'))
# R9 (test-validity): the one parse must be fed the registry PATH, not e.g. $fleet.Store.
Expect 'the fleet loop parses exactly Get-RegistryTasks $reg' ((@(Cmds $loop[0] 'Get-RegistryTasks' | Where-Object {
    ($_.Extent.Text -replace '\s+', ' ') -eq 'Get-RegistryTasks $reg' }).Count -eq 1))
Expect 'no check in the fleet loop re-reads the registry by path' ($loopText -notmatch '(Test-BoundedPause|Test-HasEnabledCarveOut|Get-StaleCarveOuts)\s+\$reg\b')
$fleetsAssign = AllOf $ast { param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$fleets' }
$fleetLabels = @($fleetsAssign | ForEach-Object { [regex]::Matches($_.Extent.Text, "Label\s*=\s*'([^']+)'") | ForEach-Object { $_.Groups[1].Value } }) | Sort-Object -Unique
$carveAssign = AllOf $ast { param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$carveOuts' }
$carveTable = if ($carveAssign.Count -eq 1) { & ([scriptblock]::Create($carveAssign[0].Right.Extent.Text)) } else { $null }
$carveKeys = if ($carveTable) { @($carveTable.Keys) | Sort-Object } else { @() }
Expect 'fleet labels are exactly the carve-out keys' (($fleetLabels.Count -gt 0) -and
    ((@($fleetLabels) -join ',') -eq (@($carveKeys) -join ',')))

# R7 wiring: the paused branch must check carve-out staleness and turn it into a problem,
# and a fleet with an enabled carve-out must not join $pausedFleets (send-log suppression).
$ifs = AllOf $ast { param($n) $n -is [System.Management.Automation.Language.IfStatementAst] -and
                               $n.Clauses[0].Item1.Extent.Text -match '^\$null -ne \$pauseUntil$' }
$pausedBody = if ($ifs.Count -eq 1) { $ifs[0].Clauses[0].Item2 } else { $null }
Expect 'paused branch calls Get-StaleCarveOuts with the fleet label and threshold' (($null -ne $pausedBody) -and
    (@(Cmds $pausedBody 'Get-StaleCarveOuts' | Where-Object { ($_.Extent.Text -replace '\s+', ' ') -eq 'Get-StaleCarveOuts $regTasks $fleet.Label $ThresholdHours' }).Count -eq 1))
$probAssign = if ($pausedBody) { AllOf $pausedBody { param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and
                                   $n.Left.Extent.Text -eq '$problems' -and $n.Right.Extent.Text -match '\$staleCarve' } } else { @() }
Expect 'paused branch turns stale carve-outs into $problems' ($probAssign.Count -ge 1)
# The problem line must be guarded by exactly `$staleCarve.Count -gt 0` (a neutered guard
# such as `if ($false)` kept the line present but unreachable).
$guardOk = $false
foreach ($pa in $probAssign) {
    $p = $pa.Parent
    while ($p -and $p -isnot [System.Management.Automation.Language.IfStatementAst]) { $p = $p.Parent }
    if ($p -and (($p.Clauses[0].Item1.Extent.Text -replace '\s+', ' ') -eq '$staleCarve.Count -gt 0')) { $guardOk = $true }
}
Expect 'the stale-carve-out problem is guarded by $staleCarve.Count -gt 0' $guardOk
Expect 'fleet joins $pausedFleets only when it has no enabled carve-out' (($null -ne $pausedBody) -and
    ($pausedBody.Extent.Text -match 'if\s*\(\s*-not\s*\(\s*Test-HasEnabledCarveOut\s+\$regTasks\s+\$fleet\.Label\s*\)\s*\)\s*\{\s*\$pausedFleets\s*\+=\s*\$fleet\.Label'))

# R6: each fleet label must point at ITS store, matching fleet_pause.STORES. Swapping the
# two labels passed every other check while applying the CC carve-out to the LAMS registry.
$pairs = @($fleetsAssign | ForEach-Object { [regex]::Matches($_.Extent.Text, "Label\s*=\s*'([^']+)'\s*;\s*Store\s*=\s*'([^']+)'") | ForEach-Object { $_.Groups[1].Value + '=' + $_.Groups[2].Value } }) | Sort-Object
$pyStores = & $py -c "import sys; sys.path.insert(0, r'$(Join-Path $PSScriptRoot '_shared')'); import fleet_pause as f; print(';'.join(sorted(k + '=' + v for k, v in f.STORES.items())))"
Expect ('each fleet label maps to its own store, as in fleet_pause.STORES (ps=' + ($pairs -join ';') + ' py=' + $pyStores + ')') (
    ($pairs.Count -eq 2) -and (($pairs -join ';') -eq ($pyStores -join '').Trim()))

# Parity with _shared/fleet_pause.py PAUSE_CARVE_OUTS ("keep the two lists identical").
$pyOut = & $py -c "import sys; sys.path.insert(0, r'$(Join-Path $PSScriptRoot '_shared')'); import fleet_pause as f; print(';'.join(k + '=' + ','.join(sorted(v)) for k, v in sorted(f.PAUSE_CARVE_OUTS.items())))"
$psOut = if ($carveTable) { (@($carveTable.Keys | Sort-Object) | ForEach-Object { $_ + '=' + ((@($carveTable[$_]) | Sort-Object) -join ',') }) -join ';' } else { '' }
Expect ('PowerShell and Python carve-out lists are identical (py=' + $pyOut + ' ps=' + $psOut + ')') (($pyOut -join '').Trim() -eq $psOut)

# R3-F1: resolve each script's REAL top-level $log / $startLog assignments (not the
# behavioural check's temp paths) and require two different files, the start one *.start.log.
function ResolvedLogPaths($root) {
    $sb = { param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and
                      $n.Left.Extent.Text -in @('$primaryRepo', '$log', '$startLog') -and
                      -not (InsideFunction $n '*') }
    $assigns = @($root.FindAll($sb, $true) | Where-Object {
        $p = $_.Parent; $inFn = $false
        while ($p) { if ($p -is [System.Management.Automation.Language.FunctionDefinitionAst]) { $inFn = $true; break }; $p = $p.Parent }
        -not $inFn } | Sort-Object { $_.Extent.StartOffset })
    $code = ($assigns | ForEach-Object { $_.Extent.Text }) -join "`n"
    $vals = & ([scriptblock]::Create($code + "`n" + '@{ log = $log; start = $startLog }'))
    return $vals
}
foreach ($pair in @(@('dead-man', $ast), @('heartbeat', $hbAst))) {
    $v = ResolvedLogPaths $pair[1]
    Expect ("$($pair[0]): START log is a separate *.start.log file (log=$($v.log) start=$($v.start))") (
        $v.log -and $v.start -and ($v.start -ne $v.log) -and ($v.start -like '*.start.log') -and ($v.log -notlike '*.start.log'))
}

} finally {
    foreach ($t in $script:tempFiles) { Remove-Item -LiteralPath $t -ErrorAction SilentlyContinue }
}

if ($fail -gt 0) { Write-Output "FAILED: $fail"; exit 1 }
Write-Output 'ALL PASS'; exit 0
