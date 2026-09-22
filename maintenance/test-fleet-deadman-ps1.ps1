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

if ($fail -gt 0) { Write-Output "FAILED: $fail"; exit 1 }
Write-Output 'ALL PASS'; exit 0
