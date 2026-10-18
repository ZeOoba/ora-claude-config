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

Write-Host "`nR-05 legacy mode: user-controlled fields cannot split or forge a send-log record"
function Get-LineCount { param([string]$Text) return @($Text -split "`r?`n" | Where-Object { $_ -ne "" }).Count }

$r = Invoke-Send -Log (New-TestLog) -Sim "" -ScriptArgs @("-To", $To, "-Subject", "L15 subj`n2026-10-18T00:00:00-04:00 [OK] Sent key=x/y/z", "-Body", "x")
Check "L15 newline in Subject: exit 0, exactly one log line, newline logged as '?'" ($r.Code -eq 0 -and (Get-LineCount $r.Log) -eq 1 -and $r.Log -like "*L15 subj[?]2026*") $r

$r = Invoke-Send -Log (New-TestLog) -Sim "" -ScriptArgs @("-To", "$To`n[OK] forged@example.com", "-Subject", "L16", "-Body", "x")
Check "L16 newline in To: exit 5 (external refused), exactly one log line, no forged line" ($r.Code -eq 5 -and (Get-LineCount $r.Log) -eq 1 -and $r.Log -like "*[?]*forged*") $r

$r = Invoke-Send -Log (New-TestLog) -Sim "" -ScriptArgs @("-To", $To, "-Cc", "$To`r`n[OK] Sent key=x/y/z", "-Subject", "L17", "-Body", "x")
Check "L17 CRLF in Cc: exactly one log line, CR/LF logged as '?'" ((Get-LineCount $r.Log) -eq 1 -and $r.Log -notmatch "[\r\n].+\[OK\] Sent key" -and $r.Log -like "*[?][?]*") $r

$r = Invoke-Send -Log (New-TestLog) -Sim "" -ScriptArgs @("-To", $To, "-Subject", "L18", "-Body", "x", "-Attachment", "C:\no-such-dir\a`n[OK] Sent key=x.txt")
Check "L18 newline in Attachment path: exit 1, exactly one log line" ($r.Code -eq 1 -and (Get-LineCount $r.Log) -eq 1) $r

$r = Invoke-Send -Log (New-TestLog) -Sim "" -ScriptArgs @("-To", $To, "-Subject", "L19 u2028$([char]0x2028)and nel$([char]0x85)end", "-Body", "x")
Check "L19 U+2028 and U+0085 in Subject are neutralized in the log" ($r.Code -eq 0 -and $r.Log -notmatch "[\u2028\u0085]" -and $r.Log -like "*u2028[?]and nel[?]end*") $r

Complete-Suite
