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
function Reg($tasks) {
    $p = Join-Path $env:TEMP ("deadman-test-" + [guid]::NewGuid() + '.json')
    (@{ scheduledTasks = $tasks } | ConvertTo-Json -Depth 5) | Set-Content -Path $p -Encoding utf8
    return $p
}
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
$res = Invoke-PyBounded $py @('-c', 'print(\"hi\"); raise SystemExit(1)') 20
Expect 'normal child returns output and exit code'        (($res.TimedOut -eq $false) -and ($res.Rc -eq 1) -and ($res.Out -match 'hi'))

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
                                    $n.Value -cmatch '^START\b' }
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
                                   $n.Left.Extent.Text -eq '$rc' }
Expect 'main body assigns $rc from Resolve-ProbeRc' (($rcAssign.Count -ge 1) -and
    (@($rcAssign | Where-Object { @(Cmds $_ 'Resolve-ProbeRc').Count -eq 0 }).Count -eq 0))
$gpv = @(Cmds $ast 'Get-PublishVerdict' | Where-Object { -not (InsideFunction $_ 'Get-PublishVerdict') })
$vOkIfs = AllOf $ast { param($n) $n -is [System.Management.Automation.Language.IfStatementAst] -and
                                 $n.Clauses[0].Item1.Extent.Text -match '^\$v\.Ok$' }
Expect 'main body calls Get-PublishVerdict and branches on its .Ok' (($gpv.Count -ge 1) -and ($vOkIfs.Count -ge 1))

if ($fail -gt 0) { Write-Output "FAILED: $fail"; exit 1 }
Write-Output 'ALL PASS'; exit 0
