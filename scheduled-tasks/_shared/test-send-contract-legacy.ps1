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

Write-Host "`nR-05 legacy mode: 60-minute quarantine after a state-unknown send"
$r = Invoke-Send -Log $log3 -Sim "ok" -ScriptArgs ($L + @("-Subject", "L3 hang after"))
Check "L8 a retry of the SAME subject after exit 6 is refused (exit 6 QUARANTINE), nothing sent" ($r.Code -eq 6 -and $r.Log -match 'QUARANTINE:' -and $r.Log -notmatch '\[OK\] Sent') $r

$r = Invoke-Send -Log $log3 -Sim "ok" -ScriptArgs ($L + @("-Subject", "L9 different subject"))
Check "L9 the quarantine is per subject: a different subject still sends" ($r.Code -eq 0 -and (Get-Count $r.Log '\[OK\] Sent to=') -eq 1) $r

$h10 = Get-TestSubjectHash "L10 old unknown"
$seed10 = @("$(Get-Stamp 61) [ERROR] SEND-STATE-UNKNOWN: seeded -- the message MAY have been sent. shash=$h10")
$r = Invoke-Send -Log (New-TestLog -Seed $seed10) -Sim "ok" -ScriptArgs ($L + @("-Subject", "L10 old unknown"))
Check "L10 the quarantine expires after 60 minutes" ($r.Code -eq 0 -and $r.Log -match '\[OK\] Sent to=') $r

$h11 = Get-TestSubjectHash "L11 recent unknown"
$seed11 = @("$(Get-Stamp 10) [ERROR] SEND-STATE-UNKNOWN: seeded -- the message MAY have been sent. shash=$h11")
$log11 = New-TestLog -Seed $seed11
$r = Invoke-Send -Log $log11 -Sim "ok" -ScriptArgs ($L + @("-Subject", "L11 recent unknown"))
Check "L11 a 10-minute-old unknown quarantines the subject" ($r.Code -eq 6 -and $r.Log -match 'QUARANTINE:') $r

$r = Invoke-Send -Log $log11 -Sim "ok" -ScriptArgs ($L + @("-Subject", "L11 recent unknown", "-ForceResend"))
Check "L30 -ForceResend bypasses the quarantine and logs FORCE-RESEND" ($r.Code -eq 0 -and $r.Log -match 'FORCE-RESEND:' -and $r.Log -match '\[OK\] Sent to=') $r

# The exit-6 line written by the script itself must carry the recipient, so a legacy retry is
# refused for the SAME recipient only.
$logRcpt = New-TestLog
$r = Invoke-Send -Log $logRcpt -Sim "hang-after-send" -ScriptArgs ($L + @("-Subject", "L31 per recipient"))
Check "L31a exit 6 line records the recipient and subject hash" ($r.Code -eq 6 -and $r.Log -match "SEND-STATE-UNKNOWN: .* to=$([regex]::Escape($To)) shash=$(Get-TestSubjectHash 'L31 per recipient')\s*$") $r
$r = Invoke-Send -Log $logRcpt -Sim "ok" -ScriptArgs @("-To", "other@oxfordra.net", "-Body", "x", "-Subject", "L31 per recipient")
Check "L31b same subject to a DIFFERENT recipient is not quarantined" ($r.Code -eq 0 -and $r.Log -match '\[OK\] Sent to=other@oxfordra.net') $r
$r = Invoke-Send -Log $logRcpt -Sim "ok" -ScriptArgs @("-To", $To.ToUpper(), "-Body", "x", "-Subject", "L31 per recipient")
Check "L31c same subject, same recipient (case differs) IS quarantined" ($r.Code -eq 6 -and $r.Log -match 'QUARANTINE:') $r

# A keyed (contract) caller's exit-6 line ends with ' key=task/period/hash'; a legacy caller of the
# same subject and recipient must still be refused.
$h32 = Get-TestSubjectHash "L32 keyed unknown"
$seed32 = @("$(Get-Stamp 5) [ERROR] SEND-STATE-UNKNOWN: seeded -- x. to=$To shash=$h32 key=ora-test-task/2026-10-18/$h32")
$r = Invoke-Send -Log (New-TestLog -Seed $seed32) -Sim "ok" -ScriptArgs ($L + @("-Subject", "L32 keyed unknown"))
Check "L32 a keyed-format unknown line also quarantines a legacy retry" ($r.Code -eq 6 -and $r.Log -match 'QUARANTINE:') $r

Write-Host "`nR-05 legacy mode: forged, partial and oversized log lines"
$h33 = Get-TestSubjectHash "L33 forged"
$ts5 = Get-Stamp 5
$forged = @(
    "$ts5 [INFO] note SEND-STATE-UNKNOWN: pretend shash=$h33",
    "$ts5 [ERROR] SEND-STATE-UNKNOWN: shash=$h33 trailing text",
    "$ts5 [ERROR] SEND-STATE-UNKNOWN: truncated line with no tag",
    "garbage $ts5 [ERROR] SEND-STATE-UNKNOWN: junk shash=$h33",
    "$ts5 [ERROR] SEND-STATE-UNKNOWN: upper shash=$($h33.ToUpper())",
    "$ts5 [ERROR] SEND-STATE-UNKNOWN: short shash=$($h33.Substring(0,15))",
    "$ts5 [OK] Sent to=$To subject=`"SEND-STATE-UNKNOWN: x shash=$h33`" shash=$h33"
)
$r = Invoke-Send -Log (New-TestLog -Seed $forged) -Sim "ok" -ScriptArgs ($L + @("-Subject", "L33 forged"))
Check "L33 forged and partial lines (wrong level, wrong position, trailing text, wrong case, short hash, [OK] line) never quarantine" ($r.Code -eq 0 -and $r.Log -match '\[OK\] Sent to=') $r

$h34 = Get-TestSubjectHash "L34 oversize"
$seed34 = @(("$(Get-Stamp 5) [ERROR] SEND-STATE-UNKNOWN: " + ("A" * 2000000) + " shash=0000000000000000"), "$(Get-Stamp 4) [ERROR] SEND-STATE-UNKNOWN: real. to=$To shash=$h34")
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$r = Invoke-Send -Log (New-TestLog -Seed $seed34) -Sim "ok" -ScriptArgs ($L + @("-Subject", "L34 oversize"))
Check "L34 a 2 MB line in the log neither hangs the scan nor hides a genuine unknown line" ($r.Code -eq 6 -and $r.Log -match 'QUARANTINE:' -and $sw.Elapsed.TotalSeconds -lt 60) $r

$h35 = Get-TestSubjectHash "L35 bad stamp"
$seed35 = @("2026-13-45T99:99:99+00:00 [ERROR] SEND-STATE-UNKNOWN: unparseable stamp. shash=$h35")
$r = Invoke-Send -Log (New-TestLog -Seed $seed35) -Sim "ok" -ScriptArgs ($L + @("-Subject", "L35 bad stamp"))
Check "L35 a matching unknown line with an unparseable timestamp fails CLOSED (quarantine)" ($r.Code -eq 6 -and $r.Log -match 'QUARANTINE:') $r

Write-Host "`nR-05 legacy mode: unreadable send-log fails closed"
$lockLog = New-TestLog -Seed @("$(Get-Stamp 400) [INFO] seed")
$fs = [System.IO.File]::Open($lockLog, 'Open', 'Read', 'None')
try {
    Set-Seams -Log $lockLog -Sim "ok"
    $prevEAP = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $out = & powershell -NoProfile -ExecutionPolicy Bypass -File $Target -To $To -Body x -Subject "L36 locked log" -WhatIf 2>&1 | Out-String -Width 4096
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prevEAP; Clear-Seams }
} finally { $fs.Dispose() }
Check "L36 a send-log that cannot be read refuses the send (exit 6), nothing sent" ($code -eq 6 -and $out -match 'QUARANTINE: .*could not be read' -and $out -notmatch '\[OK\] Sent') ([pscustomobject]@{ Code = $code; Log = $out })

Write-Host "`nR-05 legacy mode: quarantine helper (in-process)"
$haveQ = $haveClassifier -and ((Get-Content -LiteralPath $Target -Raw -Encoding UTF8) -match 'function Get-QuarantineState')
Check "L37 Get-QuarantineState is present in the script helpers" $haveQ
if ($haveQ) {
    $hh = Get-TestSubjectHash "L38"
    function QS { param([string[]]$Lines, [string]$Rcpt = $To, [int]$Min = 60)
        $f = New-TestLog -Seed $Lines
        return (Get-QuarantineState -Path $f -Hash $hh -Recipient $Rcpt -Minutes $Min).State
    }
    function Ln { param([string]$Stamp, [string]$Mid = "x.", [string]$Tail = "shash=$hh") return "$Stamp [ERROR] SEND-STATE-UNKNOWN: $Mid $Tail" }
    $utcNow = [datetimeoffset]::UtcNow
    function Fmt { param([datetimeoffset]$T, [string]$Off) $sg = if ($Off.StartsWith("-")) { -1 } else { 1 }; $ts = [timespan]::Parse($Off.Substring(1)); return $T.ToOffset([timespan]::FromTicks($sg * $ts.Ticks)).ToString("yyyy-MM-ddTHH:mm:sszzz") }
    Check "L38a missing log file -> NONE (no history, nothing to quarantine)" ((Get-QuarantineState -Path (Join-Path $Work "nope.txt") -Hash $hh -Recipient $To -Minutes 60).State -eq 'NONE')
    Check "L38b empty log -> NONE" ((QS @()) -eq 'NONE')
    $dirPath = Join-Path $Work "adir"; New-Item -ItemType Directory -Path $dirPath -Force | Out-Null
    Check "L38c a path that cannot be read as a file (directory) -> UNREADABLE" ((Get-QuarantineState -Path $dirPath -Hash $hh -Recipient $To -Minutes 60).State -eq 'UNREADABLE')
    $lf = New-TestLog -Seed @("x"); $lfs = [System.IO.File]::Open($lf, 'Open', 'Read', 'None')
    try { $lst = (Get-QuarantineState -Path $lf -Hash $hh -Recipient $To -Minutes 60).State } finally { $lfs.Dispose() }
    Check "L38d a locked log -> UNREADABLE" ($lst -eq 'UNREADABLE')
    Check "L38e 59m50s old -> QUARANTINED, 60m10s old -> NONE (boundary)" ((QS @(Ln (Fmt $utcNow.AddSeconds(-3590) "+00:00"))) -eq 'QUARANTINED' -and (QS @(Ln (Fmt $utcNow.AddSeconds(-3610) "+00:00"))) -eq 'NONE')
    # Offsets / DST: the window is absolute time. 30 min ago written with any offset quarantines;
    # 90 min ago written with any offset (incl. a DST-style +/-1h shift) does not.
    $okOff = $true
    foreach ($off in @("-12:00", "-05:00", "-04:00", "+00:00", "+01:00", "+05:30", "+14:00")) {
        if ((QS @(Ln (Fmt $utcNow.AddMinutes(-30) $off))) -ne 'QUARANTINED') { $okOff = $false; Write-Host "        30m ago at $off not quarantined" }
        if ((QS @(Ln (Fmt $utcNow.AddMinutes(-90) $off))) -ne 'NONE') { $okOff = $false; Write-Host "        90m ago at $off wrongly quarantined" }
        if ((QS @(Ln (Fmt $utcNow.AddMinutes(-59) $off))) -ne 'QUARANTINED') { $okOff = $false; Write-Host "        59m ago at $off not quarantined" }
    }
    Check "L38f the 60-minute window is absolute time across UTC offsets (no local-time or DST skew)" $okOff
    Check "L38g a stamp a few minutes in the FUTURE (clock skew) quarantines" ((QS @(Ln (Fmt $utcNow.AddMinutes(5) "+00:00"))) -eq 'QUARANTINED')
    Check "L38h a stamp days in the future (implausible/forged) is ignored" ((QS @(Ln (Fmt $utcNow.AddDays(3) "+00:00"))) -eq 'NONE')
    Check "L38i a different recipient is not quarantined; the same recipient is" ((QS @(Ln (Fmt $utcNow.AddMinutes(-5) "+00:00") "msg. to=a@oxfordra.net") "b@oxfordra.net") -eq 'NONE' -and (QS @(Ln (Fmt $utcNow.AddMinutes(-5) "+00:00") "msg. to=a@oxfordra.net") "A@oxfordra.net") -eq 'QUARANTINED')
    Check "L38j a To that itself contains ' to=' / 'shash=' text is compared whole (identical retry quarantined, a different recipient is not)" ((QS @(Ln (Fmt $utcNow.AddMinutes(-5) "+00:00") "msg. to=g@oxfordra.net to=a@oxfordra.net") "g@oxfordra.net to=a@oxfordra.net") -eq 'QUARANTINED' -and (QS @(Ln (Fmt $utcNow.AddMinutes(-5) "+00:00") "msg. to=g@oxfordra.net to=a@oxfordra.net") "a@oxfordra.net") -eq 'NONE')
    Check "L38k an empty hash never matches" ((Get-QuarantineState -Path (New-TestLog -Seed @(Ln (Fmt $utcNow.AddMinutes(-5) "+00:00") "x." "shash=")) -Hash "" -Recipient $To -Minutes 60).State -eq 'NONE')
}

Write-Host "`nR-05 legacy mode: review fixes (control chars in To, share modes, recipient sets, stamp formats)"
$logTab = New-TestLog
$toTab = "$To`t"
$r = Invoke-Send -Log $logTab -Sim "hang-after-send" -ScriptArgs @("-To", $toTab, "-Body", "x", "-Subject", "L39 tab in To")
$r2 = Invoke-Send -Log $logTab -Sim "ok" -ScriptArgs @("-To", $toTab, "-Body", "x", "-Subject", "L39 tab in To")
Check "L39 a To with a control character (logged as '?') is still quarantined on an identical retry" ($r.Code -eq 6 -and $r2.Code -eq 6 -and $r2.Log -match 'QUARANTINE:' -and $r2.Log -notmatch '\[OK\] Sent') $r2

if ($haveQ) {
    $srcAll0 = Get-Content -LiteralPath $Target -Raw -Encoding UTF8
    $now2 = [datetimeoffset]::UtcNow
    $hz = Get-TestSubjectHash "L40"
    function QS2 { param([string[]]$Lines, [string]$Rcpt = $To)
        return (Get-QuarantineState -Path (New-TestLog -Seed $Lines) -Hash $hz -Recipient $Rcpt -Minutes 60).State
    }
    function Ln2 { param([string]$Stamp, [string]$Mid = "x.") return "$Stamp [ERROR] SEND-STATE-UNKNOWN: $Mid shash=$hz" }
    Check "L40a a writer holding the log open for append (share ReadWrite) does not make it UNREADABLE" $(
        $f = New-TestLog -Seed @(Ln2 $now2.AddMinutes(-5).ToString("yyyy-MM-ddTHH:mm:sszzz", [System.Globalization.CultureInfo]::InvariantCulture))
        $w = New-Object System.IO.FileStream($f, [System.IO.FileMode]::Append, [System.IO.FileAccess]::Write, [System.IO.FileShare]::ReadWrite)
        try { (Get-QuarantineState -Path $f -Hash $hz -Recipient $To -Minutes 60).State -eq 'QUARANTINED' } finally { $w.Dispose() })
    $wl = [regex]::Match($srcAll0, '(?s)function Write-Log [{].*?[\r\n]+[}]')
    Invoke-Expression $wl.Value
    $f40 = New-TestLog -Seed @("x")
    $LogPath = $f40
    $job = Start-Job -ScriptBlock { param($helpers, $f, $h)
        Invoke-Expression $helpers
        $end = (Get-Date).AddSeconds(5)
        while ((Get-Date) -lt $end) { $null = Get-QuarantineState -Path $f -Hash $h -Recipient "ggoldberg@oxfordra.net" -Minutes 60; Start-Sleep -Milliseconds 60 }
    } -ArgumentList $m.Value, $f40, $hz
    $n40 = 0
    while ($job.State -eq 'Running' -and $n40 -lt 300) { $null = Write-Log "INFO" "concurrent $n40"; $n40++ }
    $null = Wait-Job $job -Timeout 30; Remove-Job $job -Force
    $got = @(Get-Content -LiteralPath $f40 | Where-Object { $_ -like '*concurrent *' }).Count
    Check "L40b Write-Log loses no line while a scan is reading continuously ($got of $n40 written)" ($wl.Success -and $got -eq $n40 -and $n40 -gt 20)
    Check "L40c the scan itself leaves the log byte-identical" $(
        $f = New-TestLog -Seed @(Ln2 $now2.AddMinutes(-5).ToString("yyyy-MM-ddTHH:mm:sszzz", [System.Globalization.CultureInfo]::InvariantCulture))
        $before = (Get-FileHash -LiteralPath $f).Hash; $null = Get-QuarantineState -Path $f -Hash $hz -Recipient $To -Minutes 60
        $before -eq (Get-FileHash -LiteralPath $f).Hash)
    Check "L41a multi-address To: order and spacing of the same recipients still quarantine" ((QS2 @(Ln2 $now2.AddMinutes(-5).ToString("yyyy-MM-ddTHH:mm:sszzz", [System.Globalization.CultureInfo]::InvariantCulture) "m. to=b@oxfordra.net; a@oxfordra.net") "a@oxfordra.net;b@oxfordra.net") -eq 'QUARANTINED')
    Check "L41b a different recipient SET is not quarantined" ((QS2 @(Ln2 $now2.AddMinutes(-5).ToString("yyyy-MM-ddTHH:mm:sszzz", [System.Globalization.CultureInfo]::InvariantCulture) "m. to=b@oxfordra.net; a@oxfordra.net") "a@oxfordra.net;c@oxfordra.net") -eq 'NONE')
    Check "L42a a 'Z' stamp is parsed (recent -> quarantined, old -> not)" ((QS2 @(Ln2 $now2.AddMinutes(-5).UtcDateTime.ToString("yyyy-MM-ddTHH:mm:ss") + "Z")) -eq 'QUARANTINED' -and (QS2 @(Ln2 $now2.AddDays(-3).UtcDateTime.ToString("yyyy-MM-ddTHH:mm:ss") + "Z")) -eq 'NONE')
    Check "L42b a fractional-seconds stamp is parsed (old -> not quarantined)" ((QS2 @(Ln2 $now2.AddDays(-3).ToString("yyyy-MM-ddTHH:mm:ss.fffzzz", [System.Globalization.CultureInfo]::InvariantCulture))) -eq 'NONE')
    $srcAll = Get-Content -LiteralPath $Target -Raw -Encoding UTF8
    Check "L42c Write-Log stamps with InvariantCulture (no non-Gregorian year in the log)" ($srcAll -match 'ToString\("yyyy-MM-ddTHH:mm:sszzz", \[System\.Globalization\.CultureInfo\]::InvariantCulture\)')
}

Complete-Suite
