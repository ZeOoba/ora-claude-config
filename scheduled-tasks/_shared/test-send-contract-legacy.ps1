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

Write-Host "`nR-05 legacy mode: exit 4 / exit 6 split (simulated send job)"
$L = @("-To", $To, "-Body", "x")
$r = Invoke-Send -Log (New-TestLog) -Sim "ok" -ScriptArgs ($L + @("-Subject", "L1 ok"))
Check "L1 simulated send returns -> exit 0, [OK] Sent with shash, no key" ($r.Code -eq 0 -and $r.Log -match '\[OK\] Sent to=' -and $r.Log -like "*shash=*" -and $r.Log -notlike "*key=*") $r

$r = Invoke-Send -Log (New-TestLog) -Sim "hang-before-send" -ScriptArgs ($L + @("-Subject", "L2 hang before"))
Check "L2 timeout before Send() -> exit 4 with retry-safe wording" ($r.Code -eq 4 -and $r.Log -match 'TIMEOUT: COM call exceeded 6s before Send\(\) was invoked' -and $r.Log -notmatch '\[OK\] Sent') $r

$log3 = New-TestLog
$r = Invoke-Send -Log $log3 -Sim "hang-after-send" -ScriptArgs ($L + @("-Subject", "L3 hang after"))
Check "L3 timeout after Send() was invoked -> exit 6 SEND-STATE-UNKNOWN (the M19 case)" ($r.Code -eq 6 -and $r.Log -match 'SEND-STATE-UNKNOWN: COM call exceeded the timeout after Send\(\) was invoked') $r

$r = Invoke-Send -Log (New-TestLog) -Sim "throw-before-send" -ScriptArgs ($L + @("-Subject", "L4 throw before"))
Check "L4 COM failure before Send() -> exit 2, not invoked" ($r.Code -eq 2 -and $r.Log -match 'Outlook COM failed \(HRESULT=0x80004005\)' -and $r.Log -match 'Send\(\) was not invoked') $r

$r = Invoke-Send -Log (New-TestLog) -Sim "throw-at-send" -ScriptArgs ($L + @("-Subject", "L5 throw at send"))
Check "L5 Send() itself threw -> exit 6, never 2" ($r.Code -eq 6 -and $r.Log -match 'SEND-STATE-UNKNOWN: Send\(\) threw \(error-at-send 0x80004005\)') $r

$r = Invoke-Send -Log (New-TestLog) -Sim "returned-late" -ScriptArgs ($L + @("-Subject", "L6 returned late"))
Check "L6 Send() returned but the job overran the timeout -> exit 0, not 6" ($r.Code -eq 0 -and $r.Log -match '\[OK\] Sent to=') $r

$r = Invoke-Send -Log (New-TestLog) -Sim "reject-at-send,ok" -ScriptArgs ($L + @("-Subject", "L7 rejected then ok"))
Check "L7 RPC_E_CALL_REJECTED keeps its one internal retry" ($r.Code -eq 0 -and $r.Log -match 'retrying once' -and $r.Log -match '\(after 1 retry\)') $r

$r = Invoke-Send -Log (New-TestLog) -Sim "bogus" -ScriptArgs ($L + @("-Subject", "L12 bogus sim"))
Check "L12 an unknown simulation step is a usage error (never falls through to real COM)" ($r.Code -eq 1 -and $r.Log -match "ORA_SEND_SIMULATE step 'bogus'") $r

# Uninterruptible block (a .NET call Stop-Job cannot cut short) past the timeout. The stop lands
# once the call returns, at the next pipeline boundary (Mark 'invoked'), so Send() is never
# reached and exit 4 is truthful.
$r = Invoke-Send -Log (New-TestLog) -Sim "block-before-send" -ScriptArgs ($L + @("-Subject", "L24 blocked past timeout"))
Check "L24 uninterruptible block past the timeout, stop lands before invoke -> exit 4, nothing sent" ($r.Code -eq 4 -and $r.Log -match 'TIMEOUT: COM call exceeded 6s before Send\(\)' -and $r.Log -notmatch '\[OK\] Sent') $r

# The ordering guard. One uninterruptible call blocks past the timeout and then writes 'invoked'
# itself, i.e. a blocked call that proceeds into Send() while the stop is in transit. Only a
# marker read made AFTER Stop-Job returns sees it. Reading the markers before Stop-Job would
# return exit 4 here (verified by mutation, see the task report), so this case can fail.
$r = Invoke-Send -Log (New-TestLog) -Sim "invoke-during-stop" -ScriptArgs ($L + @("-Subject", "L25 invoked during stop"))
Check "L25 'invoked' lands while the stop is pending -> exit 6, never 4 (markers read after Stop-Job)" ($r.Code -eq 6 -and $r.Log -match 'SEND-STATE-UNKNOWN: COM call exceeded the timeout after Send\(\) was invoked' -and $r.Log -notmatch 'before Send\(\) was invoked') $r

# A simulated run writes a real-looking '[OK] Sent' line, so it must refuse to run without a
# redirected log. Tested on a COPY of the script whose canonical path is pointed at scratch, so
# a regression here can never write a fake delivery into the live send-log.
$copy = Join-Path $Work "send-copy.ps1"
$copyLog = Join-Path $Work "copy-canonical-log.txt"
$src0 = Get-Content -LiteralPath $Target -Raw -Encoding UTF8
$canon = [regex]::Match($src0, '(?m)^\$LogPath = "[^"\r\n]*send-log\.txt"')
if ($canon.Success) { [System.IO.File]::WriteAllText($copy, $src0.Replace($canon.Value, '$LogPath = "' + $copyLog + '"'), (New-Object System.Text.UTF8Encoding($false))) }
Check "L26a test copy of the script has its canonical log redirected to scratch" ($canon.Success -and (Select-String -LiteralPath $copy -SimpleMatch $copyLog -Quiet))
if ($canon.Success) {
    $prevEAP = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        [Environment]::SetEnvironmentVariable("ORA_SEND_SIMULATE", "ok")
        [Environment]::SetEnvironmentVariable("ORA_SEND_SKIP_PREFLIGHT", "1")
        $out26 = & powershell -NoProfile -ExecutionPolicy Bypass -File $copy -To $To -Subject "L26 sim no log" -Body x -WhatIf 2>&1 | Out-String -Width 4096
        $code26 = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prevEAP; Clear-Seams }
    Check "L26b ORA_SEND_SIMULATE without ORA_SEND_LOG_PATH is refused (exit 1) and writes no log line" ($code26 -eq 1 -and $out26 -match 'requires ORA_SEND_LOG_PATH' -and -not (Test-Path -LiteralPath $copyLog))
}

# --- In-process: the pure classifier and the marker reader, extracted from the script text.
# Child-process cases above prove the wiring; these prove the exit-4 guarantee exhaustively:
# exit 4 may ONLY come back when no marker shows Send() ran or might have run.
Write-Host "`nR-05 legacy mode: classifier (in-process, exhaustive)"
$src = Get-Content -LiteralPath $Target -Raw -Encoding UTF8
$m = [regex]::Match($src, '(?s)\$RPC_E_CALL_REJECTED = .*?# --- end R-05 helpers ---')
$haveClassifier = $m.Success -and $src -match 'function Resolve-SendOutcome' -and $src -match 'function Read-SendPhases'
if ($haveClassifier) { Invoke-Expression $m.Value }
Check "L20 classifier and marker reader are present in the script" $haveClassifier

if ($haveClassifier) {
    function Code { param([bool]$T, [bool]$E, [string[]]$P) return (Resolve-SendOutcome -TimedOut $T -JobErrored $E -Phases $P).Code }
    $bk = 'error-before 0x80004005'; $ak = 'error-at-send 0x80004005'; $ar = 'error-at-send 0x80010001'
    Check "L21a no timeout, no error -> 0" ((Code $false $false @()) -eq 0)
    Check "L21b timeout with no markers (job never started) -> 4" ((Code $true $false @()) -eq 4)
    Check "L21c timeout after 'started' only -> 4" ((Code $true $false @('started')) -eq 4)
    Check "L21d timeout after 'invoked' -> 6" ((Code $true $false @('started', 'invoked')) -eq 6)
    Check "L21e timeout after 'returned' -> 0" ((Code $true $false @('started', 'invoked', 'returned')) -eq 0)
    Check "L21f unreadable marker file on timeout -> 6, never 4" ((Code $true $false @('unreadable')) -eq 6)
    Check "L21g unreadable marker file on job error -> 6, never 2" ((Code $false $true @('unreadable')) -eq 6)
    Check "L21h job error after 'invoked' with no 'returned' -> 6" ((Code $false $true @('started', 'invoked')) -eq 6)
    Check "L21i job error before Send() -> 2 with the HRESULT" ((Resolve-SendOutcome -TimedOut $false -JobErrored $true -Phases @('started', $bk)).HResult -eq [Convert]::ToInt32('80004005', 16) -and (Code $false $true @('started', $bk)) -eq 2)
    Check "L21j Send() threw RPC_E_CALL_REJECTED -> 2 (retry-safe)" ((Code $false $true @('started', 'invoked', $ar)) -eq 2)
    Check "L21k Send() threw anything else -> 6" ((Code $false $true @('started', 'invoked', $ak)) -eq 6)
    Check "L21l job error with no markers at all -> 2" ((Code $false $true @()) -eq 2)

    $tokens = @('started', 'invoked', $bk, $ak, $ar, 'returned', 'unreadable')
    $bad = @()
    $n = 0
    foreach ($t in @($false, $true)) { foreach ($e in @($false, $true)) {
        for ($mask = 0; $mask -lt (1 -shl $tokens.Count); $mask++) {
            $ph = @(for ($i = 0; $i -lt $tokens.Count; $i++) { if ($mask -band (1 -shl $i)) { $tokens[$i] } })
            $c = Code $t $e $ph
            $n++
            $ranOrMight = ($ph -contains 'invoked') -or ($ph -contains 'unreadable') -or ($ph -contains 'returned') -or ($ph -contains $ak) -or ($ph -contains $ar)
            if ($c -eq 4 -and $ranOrMight) { $bad += "exit4 but ran/might-have-run: T=$t E=$e [$($ph -join ',')]" }
            if ($c -eq 4 -and -not $t) { $bad += "exit4 without a timeout: T=$t E=$e [$($ph -join ',')]" }
            if ($c -eq 2 -and (($ph -contains 'invoked') -and ($ph -notcontains $ar) -and ($ph -notcontains 'returned'))) { $bad += "exit2 although invoked: T=$t E=$e [$($ph -join ',')]" }
        }
    } }
    Check "L22 exhaustive ($n combos): exit 4 never when Send() ran/might have; exit 2 never after invoke except REJECTED" ($bad.Count -eq 0 -and $n -eq 512)
    if ($bad.Count -gt 0) { $bad | Select-Object -First 5 | ForEach-Object { Write-Host "        $_" } }

    $mf = Join-Path $Work "markers.status"
    Check "L23a Read-SendPhases: a missing file is NOT proof of no markers -> 'unreadable'" ((@(Read-SendPhases -Path $mf) -join ',') -eq 'unreadable')
    [System.IO.File]::AppendAllText($mf, "started`ninvoked`n")
    Check "L23b Read-SendPhases: reads appended phases" ((@(Read-SendPhases -Path $mf) -join ',') -eq 'started,invoked')
    $fs = [System.IO.File]::Open($mf, 'Open', 'Read', 'None')
    try { $locked = @(Read-SendPhases -Path $mf) } finally { $fs.Dispose() }
    Check "L23c Read-SendPhases: a locked (unreadable) file -> 'unreadable', not an empty list" ($locked.Count -eq 1 -and $locked[0] -eq 'unreadable')
    Check "L23d unreadable markers can never resolve to exit 4" ((Code $true $false $locked) -eq 6)
}

Complete-Suite
