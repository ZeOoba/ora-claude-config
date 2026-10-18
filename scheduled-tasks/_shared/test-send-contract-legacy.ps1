<#
.SYNOPSIS
    R-05 send contract, LEGACY mode (no -DedupTaskId/-DedupPeriodKey): the exit 4 / exit 6
    split, the RPC_E_CALL_REJECTED retry, and the 60-minute same-subject quarantine.
.DESCRIPTION
    Child-process cases only, all under -WhatIf (see send-contract-harness.ps1). No mail is sent.
    Run:  powershell -NoProfile -ExecutionPolicy Bypass -File test-send-contract-legacy.ps1
    Exit: 0 = all passed, 1 = at least one failure.
#>
. (Join-Path $PSScriptRoot "send-contract-harness.ps1")

Write-Host "`nR-05 legacy mode: subject hash and dry run"
$subj13 = "Hash check " + [char]0x2014 + " ok " + [char]0x2705
$r = Invoke-Send -Log (New-TestLog) -Sim "" -ScriptArgs @("-To", $To, "-Subject", $subj13, "-Body", "x")
Check "L13 non-ASCII subject reaches the script intact (shash matches the caller's hash)" ($r.Code -eq 0 -and $r.Log -like "*shash=$(Get-TestSubjectHash $subj13)*") $r

$r = Invoke-Send -Log (New-TestLog) -Sim "" -ScriptArgs @("-To", $To, "-Subject", "L14 plain dry run", "-Body", "x")
Check "L14 legacy dry run logs shash, no key, no SEND-INTENT" ($r.Code -eq 0 -and $r.Log -like "*DRY RUN: would send*" -and $r.Log -like "*shash=*" -and $r.Log -notlike "*key=*" -and (Get-Count $r.Log 'SEND-INTENT') -eq 0) $r

Complete-Suite
