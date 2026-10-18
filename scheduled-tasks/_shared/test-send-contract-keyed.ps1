<#
.SYNOPSIS
    R-05 send contract, CONTRACT mode (-DedupTaskId + -DedupPeriodKey): argument validation,
    dedup in send-log.txt before Send(), the single internal retry, -ForceResend, concurrency.
.DESCRIPTION
    Child-process cases only, all under -WhatIf (see send-contract-harness.ps1). No mail is sent.
    Run:  powershell -NoProfile -ExecutionPolicy Bypass -File test-send-contract-keyed.ps1
    Exit: 0 = all passed, 1 = at least one failure.
#>
. (Join-Path $PSScriptRoot "send-contract-harness.ps1")

Write-Host "`nR-05 contract mode: argument validation and dry run"
$r = Invoke-Send -Log (New-TestLog) -Sim "" -ScriptArgs @("-To", $To, "-Subject", "K1", "-Body", "x", "-DedupTaskId", "ora-test-task")
Check "K1 -DedupTaskId without -DedupPeriodKey is a usage error" ($r.Code -eq 1 -and $r.Log -like "*must be passed together*") $r

$r = Invoke-Send -Log (New-TestLog) -Sim "" -ScriptArgs @("-To", $To, "-Subject", "K2", "-Body", "x", "-DedupTaskId", "Bad Id!", "-DedupPeriodKey", "2026-10-18")
Check "K2 malformed task id is a usage error" ($r.Code -eq 1 -and $r.Log -like "*is not a task id*") $r

$r = Invoke-Send -Log (New-TestLog) -Sim "" -ScriptArgs @("-To", $To, "-Subject", "K3", "-Body", "x", "-DedupTaskId", "ora-test-task", "-DedupPeriodKey", "x")
Check "K3 malformed period key is a usage error" ($r.Code -eq 1 -and $r.Log -like "*is not a period key*") $r

$r = Invoke-Send -Log (New-TestLog) -Sim "" -ScriptArgs @("-To", $To, "-Subject", "K4", "-Body", "x", "-DedupTaskId", "ora-test`n", "-DedupPeriodKey", "2026-10-18")
Check "K4 task id with a trailing newline is a usage error (dedup key cannot split a record)" ($r.Code -eq 1 -and $r.Log -like "*is not a task id*" -and (Get-Count $r.Log 'DRY RUN') -eq 0) $r

$r = Invoke-Send -Log (New-TestLog) -Sim "" -ScriptArgs @("-To", $To, "-Subject", "K5", "-Body", "x", "-DedupTaskId", "ora-test-task", "-DedupPeriodKey", "2026-10-18`n")
Check "K5 period key with a trailing newline is a usage error" ($r.Code -eq 1 -and $r.Log -like "*is not a period key*" -and (Get-Count $r.Log 'DRY RUN') -eq 0) $r

$r = Invoke-Send -Log (New-TestLog) -Sim "" -ScriptArgs @("-To", $To, "-Subject", "K6", "-Body", "x", "-DedupTaskId", "", "-DedupPeriodKey", "2026-10-18")
Check "K6 (-File path) an empty -DedupTaskId is a usage error" ($r.Code -eq 1 -and $r.Log -notlike "*DRY RUN*") $r

$r = Invoke-Send -Log (New-TestLog) -Sim "" -ScriptArgs @("-To", $To, "-Subject", "K7", "-Body", "x", "-DedupTaskId", "ora-test-task", "-DedupPeriodKey", "  ")
Check "K7 a passed but whitespace -DedupPeriodKey is a usage error" ($r.Code -eq 1 -and $r.Log -like "*must not be empty*" -and $r.Log -notlike "*DRY RUN*") $r

# K8-K10: IN-PROCESS empty/null values. Through -File, PowerShell 5.1 drops empty-string
# native arguments (so K6 fails at the binder either way); only an in-process call reaches
# the script with a BOUND empty value, which is the case ContainsKey exists for.
function Invoke-InProc {
    param([string]$Expr)
    $log = New-TestLog
    Set-Seams -Log $log -Sim ""
    $prevEAP = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $cmd = "& '$Target' -To '$To' -Subject 'InProc' -Body 'x' $Expr -WhatIf | Out-Null; exit `$LASTEXITCODE"
        & powershell -NoProfile -ExecutionPolicy Bypass -Command $cmd 2>&1 | Out-Null
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prevEAP; Clear-Seams }
    $text = if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log -Raw -Encoding UTF8 } else { "" }
    return @{ Code = $code; Log = $text; Out = "" }
}
$r = Invoke-InProc "-DedupTaskId '' -DedupPeriodKey ''"
Check "K8 in-process empty/empty keys exit 1, not silent legacy mode" ($r.Code -eq 1 -and $r.Log -like "*must not be empty*" -and $r.Log -notlike "*DRY RUN*") $r
$r = Invoke-InProc "-DedupTaskId `$null -DedupPeriodKey `$null"
Check "K9 in-process null/null keys exit 1, not silent legacy mode" ($r.Code -eq 1 -and $r.Log -like "*must not be empty*" -and $r.Log -notlike "*DRY RUN*") $r
$r = Invoke-InProc "-DedupTaskId 'ora-test-task' -DedupPeriodKey ''"
Check "K10 in-process valid task id + empty period key exits 1" ($r.Code -eq 1 -and $r.Log -like "*must not be empty*" -and $r.Log -notlike "*DRY RUN*") $r

$r = Invoke-Send -Log (New-TestLog) -Sim "" -ScriptArgs (@("-To", $To, "-Subject", "K0 keyed dry run", "-Body", "x") + $Keyed)
$k0 = "ora-test-task/2026-10-18/" + (Get-TestSubjectHash "K0 keyed dry run")
Check "K0 keyed dry run logs the full dedup key and writes no SEND-INTENT" ($r.Code -eq 0 -and $r.Log -like "*key=$k0*" -and (Get-Count $r.Log 'SEND-INTENT') -eq 0) $r

Complete-Suite
