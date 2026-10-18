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

$r = Invoke-Send -Log (New-TestLog) -Sim "" -ScriptArgs (@("-To", $To, "-Subject", "K0 keyed dry run", "-Body", "x") + $Keyed)
$k0 = "ora-test-task/2026-10-18/" + (Get-TestSubjectHash "K0 keyed dry run")
Check "K0 keyed dry run logs the full dedup key and writes no SEND-INTENT" ($r.Code -eq 0 -and $r.Log -like "*key=$k0*" -and (Get-Count $r.Log 'SEND-INTENT') -eq 0) $r

Complete-Suite
