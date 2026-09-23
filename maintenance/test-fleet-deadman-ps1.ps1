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
$tricky = @('C:\dir\', 'a"b', 'two words', 'x\\"y', '')
$res = Invoke-PyBounded $py (@('-c', 'import sys, json; print(json.dumps(sys.argv[1:]))') + $tricky) 60
$got = try { @($res.Out.Trim() | ConvertFrom-Json) } catch { @('PARSE-FAIL: ' + $res.Out) }
Expect ('arguments round-trip exactly (got=' + ($got -join '|') + ')') ((($got -join '|') -eq ($tricky -join '|')) -and ($got.Count -eq $tricky.Count))

# R4 correctness-F1: a grandchild that inherits the output pipes must not defeat the bound.
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$res = Invoke-PyBounded $py @('-c', 'import subprocess, sys; subprocess.Popen([sys.executable, chr(45)+chr(99), chr(105)+chr(109)+chr(112)+chr(111)+chr(114)+chr(116)+chr(32)+chr(116)+chr(105)+chr(109)+chr(101)+chr(59)+chr(116)+chr(105)+chr(109)+chr(101)+chr(46)+chr(115)+chr(108)+chr(101)+chr(101)+chr(112)+chr(40)+chr(50)+chr(48)+chr(41)]); print(1)') 3
$sw.Stop()
Expect ('pipe-holding grandchild cannot exceed the bound (elapsed=' + [int]$sw.Elapsed.TotalSeconds + 's, TimedOut=' + $res.TimedOut + ')') (($sw.Elapsed.TotalSeconds -lt 12) -and ($res.TimedOut -eq $true))

# R4 test-validity-F1: the phantom-count parse is a helper; stdout loss must not zero the count.
$ph = Get-PhantomSummary @{ TimedOut = $false; Rc = 1; Out = "header`nphantom : 3`n  2026-09-20 10:00 ora-x [never-confirmed]`n" }
Expect 'phantom summary parses count and detail from stdout' (($ph.Rc -eq 1) -and ($ph.Count -eq 3) -and (@($ph.Detail).Count -eq 1))
$ph = Get-PhantomSummary @{ TimedOut = $true; Rc = $null; Out = '' }
Expect 'phantom summary: timeout is exit 2 with count 0'      (($ph.Rc -eq 2) -and ($ph.Count -eq 0))

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

# R3-F3: the pause call must pass the fleet's own label, and those labels must be the
# carve-out table's keys -- a typo'd or wrong property silently disables the carve-out.
$tbpTexts = @($tbp | ForEach-Object { ($_.Extent.Text -replace '\s+', ' ').Trim() })
Expect 'Test-BoundedPause is called exactly as Test-BoundedPause $reg $fleet.Label' (($tbpTexts.Count -ge 1) -and
    (@($tbpTexts | Where-Object { $_ -ne 'Test-BoundedPause $reg $fleet.Label' }).Count -eq 0))
$fleetsAssign = AllOf $ast { param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$fleets' }
$fleetLabels = @($fleetsAssign | ForEach-Object { [regex]::Matches($_.Extent.Text, "Label\s*=\s*'([^']+)'") | ForEach-Object { $_.Groups[1].Value } }) | Sort-Object -Unique
$carveAssign = AllOf $ast { param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$carveOuts' }
$carveTable = if ($carveAssign.Count -eq 1) { & ([scriptblock]::Create($carveAssign[0].Right.Extent.Text)) } else { $null }
$carveKeys = if ($carveTable) { @($carveTable.Keys) | Sort-Object } else { @() }
Expect 'fleet labels are exactly the carve-out keys' (($fleetLabels.Count -gt 0) -and
    ((@($fleetLabels) -join ',') -eq (@($carveKeys) -join ',')))

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
