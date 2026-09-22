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

# --- static checks on the script text
$src = Get-Content -Raw -Path $target
$calls = $ast.FindAll({ $args[0] -is [System.Management.Automation.Language.CommandAst] -and
                        $args[0].GetCommandName() -eq 'Test-BoundedPause' }, $true)
Expect 'every Test-BoundedPause call passes a fleet label' (($calls.Count -gt 0) -and
    (@($calls | Where-Object { $_.CommandElements.Count -lt 3 }).Count -eq 0))
# START must NOT go to fleet-deadman.log: state-freshness-probe judges that file by mtime,
# so a START written there on every killed run would keep a dead dead-man looking fresh.
Expect 'START is not written to the main verdict log'    (($src -notmatch "(?m)^\s*Log\s*\(\s*'START") -and ($src -match "LogStart\s*\(\s*'START"))
$hb = Get-Content -Raw -Path (Join-Path $PSScriptRoot 'push-fleet-heartbeat.ps1')
Expect 'heartbeat START is not written to its main log'  (($hb -notmatch "(?m)^\s*Log\s*\(\s*'START") -and ($hb -match "LogStart\s*\(\s*'START"))

if ($fail -gt 0) { Write-Output "FAILED: $fail"; exit 1 }
Write-Output 'ALL PASS'; exit 0
