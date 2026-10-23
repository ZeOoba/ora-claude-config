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

Write-Host "`nR-05 contract mode: dedup before Send() and the single internal retry"
$K = @("-To", $To, "-Body", "x") + $Keyed
function Get-TestKey { param([string]$Subj, [string]$Period = "2026-10-18") return "ora-test-task/$Period/" + (Get-TestSubjectHash $Subj) }
function Get-TestTag { param([string]$Subj, [string]$Period = "2026-10-18") return " shash=" + (Get-TestSubjectHash $Subj) + " key=" + (Get-TestKey $Subj $Period) }

$log4 = New-TestLog
$r = Invoke-Send -Log $log4 -Sim "ok" -ScriptArgs ($K + @("-Subject", "K11 keyed ok"))
Check "K11 a keyed send writes SEND-INTENT, then [OK] Sent carrying the key" ($r.Code -eq 0 -and $r.Log -match '\[INFO\] SEND-INTENT: key=ora-test-task/2026-10-18/' -and $r.Log -match '\[OK\] Sent to=.* key=ora-test-task/2026-10-18/' -and $r.Log.IndexOf('SEND-INTENT:') -lt $r.Log.IndexOf('[OK] Sent to=')) $r

$r = Invoke-Send -Log $log4 -Sim "ok" -ScriptArgs ($K + @("-Subject", "K11 keyed ok"))
Check "K12 the same key again -> exit 0 DEDUP-SKIP, still exactly one [OK] Sent" ($r.Code -eq 0 -and $r.Log -match 'DEDUP-SKIP:' -and (Get-Count $r.Log '\[OK\] Sent to=') -eq 1) $r

$r = Invoke-Send -Log $log4 -Sim "ok" -ScriptArgs @("-To", $To, "-Body", "x", "-Subject", "K11 keyed ok", "-DedupTaskId", "ora-test-task", "-DedupPeriodKey", "2026-10-19")
Check "K13 the next period sends again (key reuse across periods)" ($r.Code -eq 0 -and (Get-Count $r.Log '\[OK\] Sent to=') -eq 2) $r

$r = Invoke-Send -Log $log4 -Sim "ok" -ScriptArgs ($K + @("-Subject", "K25 other subject, same period"))
Check "K25 a different subject hash in the same period still sends" ($r.Code -eq 0 -and (Get-Count $r.Log '\[OK\] Sent to=') -eq 3) $r

$log7 = New-TestLog
$r = Invoke-Send -Log $log7 -Sim "hang-after-send" -ScriptArgs ($K + @("-Subject", "K14 keyed unknown"))
Check "K14 a keyed timeout after Send() -> exit 6, not retried (one SEND-INTENT)" ($r.Code -eq 6 -and (Get-Count $r.Log 'SEND-INTENT:') -eq 1 -and $r.Log -match 'SEND-STATE-UNKNOWN:') $r

$r = Invoke-Send -Log $log7 -Sim "ok" -ScriptArgs ($K + @("-Subject", "K14 keyed unknown"))
Check "K15 a later call with that key -> exit 6 DEDUP-BLOCK, nothing sent" ($r.Code -eq 6 -and $r.Log -match 'DEDUP-BLOCK:' -and $r.Log -notmatch '\[OK\] Sent') $r

$r = Invoke-Send -Log $log7 -Sim "ok" -ScriptArgs ($K + @("-Subject", "K14 keyed unknown", "-ForceResend"))
Check "K16 -ForceResend (human only) sends past DEDUP-BLOCK and logs FORCE-RESEND" ($r.Code -eq 0 -and $r.Log -match 'FORCE-RESEND:' -and (Get-Count $r.Log '\[OK\] Sent to=') -eq 1) $r

$r = Invoke-Send -Log $log7 -Sim "ok" -ScriptArgs ($K + @("-Subject", "K14 keyed unknown"))
Check "K26 after the forced resend the key is SENT: next call DEDUP-SKIP" ($r.Code -eq 0 -and $r.Log -match 'DEDUP-SKIP:' -and (Get-Count $r.Log '\[OK\] Sent to=') -eq 1) $r

$r = Invoke-Send -Log (New-TestLog) -Sim "hang-before-send,ok" -ScriptArgs ($K + @("-Subject", "K17 retry ok"))
Check "K17 contract mode retries a pre-Send() timeout once by itself -> exit 0" ($r.Code -eq 0 -and (Get-Count $r.Log 'SEND-INTENT:') -eq 2 -and $r.Log -match '\(after 1 retry\)' -and (Get-Count $r.Log '\[OK\] Sent to=') -eq 1) $r

$log27 = New-TestLog
$r = Invoke-Send -Log $log27 -Sim "hang-before-send,hang-before-send,ok" -ScriptArgs ($K + @("-Subject", "K27 timeout twice"))
Check "K27 two pre-Send() timeouts -> exit 4 (retry exhausted), exactly two intents, nothing sent" ($r.Code -eq 4 -and (Get-Count $r.Log 'SEND-INTENT:') -eq 2 -and $r.Log -match '\(retry exhausted\)' -and $r.Log -notmatch '\[OK\] Sent') $r
$r = Invoke-Send -Log $log27 -Sim "ok" -ScriptArgs ($K + @("-Subject", "K27 timeout twice"))
Check "K28 exit 4 closes the key: a later rerun may send, once" ($r.Code -eq 0 -and (Get-Count $r.Log '\[OK\] Sent to=') -eq 1 -and $r.Log -notmatch 'DEDUP-BLOCK') $r

$r = Invoke-Send -Log (New-TestLog) -Sim "throw-before-send,throw-before-send,ok" -ScriptArgs ($K + @("-Subject", "K18 retry exhausted"))
Check "K18 the internal retry is ONE retry: two failures -> exit 2, no third attempt" ($r.Code -eq 2 -and (Get-Count $r.Log 'SEND-INTENT:') -eq 2 -and $r.Log -match '\(retry exhausted\)' -and $r.Log -notmatch '\[OK\] Sent') $r

$r = Invoke-Send -Log (New-TestLog) -Sim "hang-after-send,ok" -ScriptArgs ($K + @("-Subject", "K19 never retry unknown"))
Check "K19 exit 6 is never retried internally" ($r.Code -eq 6 -and (Get-Count $r.Log 'SEND-INTENT:') -eq 1 -and $r.Log -notmatch '\[OK\] Sent') $r

$r = Invoke-Send -Log (New-TestLog) -Sim "throw-at-send,ok" -ScriptArgs ($K + @("-Subject", "K29 throw inside Send"))
Check "K29 a throw inside Send() is exit 6 and is not retried" ($r.Code -eq 6 -and (Get-Count $r.Log 'SEND-INTENT:') -eq 1 -and $r.Log -notmatch '\[OK\] Sent') $r

$r = Invoke-Send -Log (New-TestLog) -Sim "reject-at-send,ok" -ScriptArgs ($K + @("-Subject", "K30 rejected then ok"))
Check "K30 RPC_E_CALL_REJECTED inside Send() is retried once (callee refused) -> exit 0, one Sent" ($r.Code -eq 0 -and (Get-Count $r.Log 'SEND-INTENT:') -eq 2 -and (Get-Count $r.Log '\[OK\] Sent to=') -eq 1) $r

$t = "K20 stale intent"
$r = Invoke-Send -Log (New-TestLog -Seed @("$(Get-Stamp 5) [INFO] SEND-INTENT: key=$(Get-TestKey $t) subject=`"$t`"$(Get-TestTag $t)")) -Sim "ok" -ScriptArgs ($K + @("-Subject", $t))
Check "K20 an unresolved SEND-INTENT (crashed or concurrent fire) blocks with exit 6" ($r.Code -eq 6 -and $r.Log -match 'DEDUP-BLOCK:' -and $r.Log -notmatch '\[OK\] Sent') $r

$t = "K21 rotated"
$r = Invoke-Send -Log (New-TestLog -Seed @("$(Get-Stamp 30) [OK] DEDUP-SKIP: key=$(Get-TestKey $t) already sent at 2026-10-18T07:00:00-04:00 -- not re-sending subject=`"$t`"$(Get-TestTag $t)")) -Sim "ok" -ScriptArgs ($K + @("-Subject", $t))
Check "K21 a DEDUP-SKIP line alone still proves sent (survives send-log rotation)" ($r.Code -eq 0 -and (Get-Count $r.Log 'DEDUP-SKIP:') -eq 2 -and $r.Log -notmatch '\[OK\] Sent to=') $r

$t = "K22 dry"
$r = Invoke-Send -Log (New-TestLog -Seed @("$(Get-Stamp 30) [OK] Sent to=$To cc=none subject=`"$t`" bytes=1 format=html$(Get-TestTag $t)")) -Sim "" -ScriptArgs ($K + @("-Subject", $t))
Check "K22 a keyed dry run reports dedup=SENT and writes no SEND-INTENT" ($r.Code -eq 0 -and $r.Log -match 'dedup=SENT' -and (Get-Count $r.Log 'SEND-INTENT:') -eq 0) $r

$t = "K23 prefix"
$r = Invoke-Send -Log (New-TestLog -Seed @("$(Get-Stamp 30) [OK] Sent to=$To cc=none subject=`"$t`" bytes=1 format=html$(Get-TestTag $t '2026-10-1')")) -Sim "ok" -ScriptArgs ($K + @("-Subject", $t))
Check "K23 the key match is exact: period 2026-10-1 does not dedup period 2026-10-18" ($r.Code -eq 0 -and (Get-Count $r.Log '\[OK\] Sent to=') -eq 2) $r

# Seeded log lines are untrusted text. A subject can carry ' key=<victim key>' inside an [OK] Sent line;
# only the key at the very END of a line this script wrote (after its own shash) may count.
$t = "K31 victim"
$forgedSubject = "evil key=$(Get-TestKey $t)"
$r = Invoke-Send -Log (New-TestLog -Seed @("$(Get-Stamp 30) [OK] Sent to=$To cc=none subject=`"$forgedSubject`" bytes=1 format=html shash=0123456789abcdef key=ora-test-task/2026-10-18/0123456789abcdef")) -Sim "ok" -ScriptArgs ($K + @("-Subject", $t))
Check "K31 a key token forged inside another line's subject does not dedup" ($r.Code -eq 0 -and (Get-Count $r.Log '\[OK\] Sent to=') -eq 2 -and $r.Log -notmatch 'DEDUP-SKIP') $r

$r = Invoke-Send -Log (New-TestLog -Seed @("$(Get-Stamp 30) [INFO] note [OK] Sent to=$To cc=none subject=`"$t`" bytes=1 format=html$(Get-TestTag $t)")) -Sim "ok" -ScriptArgs ($K + @("-Subject", $t))
Check "K32 a line whose record type is not at its start never proves SENT (seed + one new send)" ($r.Code -eq 0 -and (Get-Count $r.Log '\[OK\] Sent to=') -eq 2 -and $r.Log -notmatch 'DEDUP-SKIP') $r

# Fail CLOSED: the dedup check must never degrade to "proceed" when the log cannot be consulted.
$t = "K33 locked log"
$lockedLog = New-TestLog -Seed @("$(Get-Stamp 90) [OK] Sent to=$To cc=none subject=`"unrelated`" bytes=1 format=html shash=0123456789abcdef")
$before33 = [System.IO.File]::ReadAllText($lockedLog)
$fs33 = New-Object System.IO.FileStream($lockedLog, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
try { $r = Invoke-Send -Log $lockedLog -Sim "ok" -ScriptArgs ($K + @("-Subject", $t)) } finally { $fs33.Dispose() }
Check "K33 an unreadable send-log fails closed: exit 6, nothing sent, log untouched" ($r.Code -eq 6 -and $r.Out -match 'DEDUP-UNAVAILABLE' -and [System.IO.File]::ReadAllText($lockedLog) -eq $before33) $r

$t = "K34 readonly log"
$roLog = New-TestLog -Seed @("$(Get-Stamp 90) [OK] Sent to=$To cc=none subject=`"unrelated`" bytes=1 format=html shash=0123456789abcdef")
$before34 = [System.IO.File]::ReadAllText($roLog)
Set-ItemProperty -LiteralPath $roLog -Name IsReadOnly -Value $true
try { $r = Invoke-Send -Log $roLog -Sim "ok" -ScriptArgs ($K + @("-Subject", $t)) } finally { Set-ItemProperty -LiteralPath $roLog -Name IsReadOnly -Value $false }
Check "K34 SEND-INTENT that cannot be written fails closed: exit 6, nothing sent" ($r.Code -eq 6 -and $r.Out -match 'DEDUP-INTENT-UNWRITTEN' -and [System.IO.File]::ReadAllText($roLog) -eq $before34) $r

# Mutex cases. The cross-process mutex is named, so this test process can hold it.
$mutexName = 'Global\ORA-send-via-outlook-dedup-' + $script:MutexSuffix   # this suite's own lock name (seam), never the production lock
$t = "K35 lock held"
$held = New-Object System.Threading.Mutex($false, $mutexName)
$null = $held.WaitOne(5000)
[Environment]::SetEnvironmentVariable("ORA_SEND_LOCK_WAIT_MS", "1000")
try { $r = Invoke-Send -Log (New-TestLog) -Sim "ok" -ScriptArgs ($K + @("-Subject", $t)) } finally { try { $held.ReleaseMutex() } catch { }; $held.Dispose() }
Check "K35 a dedup lock that cannot be acquired fails closed: exit 6, nothing sent" ($r.Code -eq 6 -and $r.Log -match 'DEDUP-LOCK-TIMEOUT' -and $r.Log -notmatch '\[OK\] Sent' -and (Get-Count $r.Log 'SEND-INTENT:') -eq 0) $r

$t = "K39 forced resend still takes the lock"
$held = New-Object System.Threading.Mutex($false, $mutexName)
$null = $held.WaitOne(5000)
[Environment]::SetEnvironmentVariable("ORA_SEND_LOCK_WAIT_MS", "1000")
try { $r = Invoke-Send -Log (New-TestLog) -Sim "ok" -ScriptArgs ($K + @("-Subject", $t, "-ForceResend")) } finally { try { $held.ReleaseMutex() } catch { }; $held.Dispose() }
Check "K39 -ForceResend takes the dedup lock too: lock held -> exit 6, nothing sent, no FORCE-RESEND reset written" ($r.Code -eq 6 -and $r.Log -notmatch '\[OK\] Sent' -and $r.Log -notmatch 'FORCE-RESEND' -and (Get-Count $r.Log 'SEND-INTENT:') -eq 0) $r

# A Global\ lock that cannot be OPENED (created under a DACL that denies this user) must fail closed, not
# fall back to a different (Local) lock that would let two same-key fires both pass.
$t = "K40 lock access denied"
$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$sec = New-Object System.Security.AccessControl.MutexSecurity
$sec.AddAccessRule((New-Object System.Security.AccessControl.MutexAccessRule($sid, [System.Security.AccessControl.MutexRights]::FullControl, [System.Security.AccessControl.AccessControlType]::Deny)))
$createdNew = $false
$denied = [System.Threading.Mutex]::new($false, $mutexName, [ref]$createdNew, $sec)
try { $r = Invoke-Send -Log (New-TestLog) -Sim "ok" -ScriptArgs ($K + @("-Subject", $t)) } finally { $denied.Dispose() }
Check "K40 a Global lock that cannot be opened fails closed (no Local fallback): exit 6, nothing sent" ($createdNew -and $r.Code -eq 6 -and $r.Out -match 'DEDUP-LOCK-UNAVAILABLE' -and $r.Log -notmatch '\[OK\] Sent') $r

# A holder that dies without releasing leaves an ABANDONED mutex; the next caller must still get through.
$abandonCmd = "`$m = New-Object System.Threading.Mutex(`$false, '$mutexName'); `$null = `$m.WaitOne(5000); exit 0"
# A mutex is only observed as abandoned while another handle to it is still open, so keep one here.
$keeper = New-Object System.Threading.Mutex($false, $mutexName)
$null = & powershell -NoProfile -ExecutionPolicy Bypass -Command $abandonCmd
$t = "K36 abandoned lock"
try { $r = Invoke-Send -Log (New-TestLog) -Sim "ok" -ScriptArgs ($K + @("-Subject", $t)) } finally { $keeper.Dispose() }
Check "K36 an abandoned dedup mutex does not wedge the next caller: sends once" ($r.Code -eq 0 -and $r.Log -match 'DEDUP-LOCK-ABANDONED' -and (Get-Count $r.Log '\[OK\] Sent to=') -eq 1 -and $r.Log -notmatch 'DEDUP-LOCK-TIMEOUT') $r

# Legacy callers (no key) neither write intents nor read keyed state.
$t = "K37 legacy untouched"
$r = Invoke-Send -Log (New-TestLog -Seed @("$(Get-Stamp 5) [INFO] SEND-INTENT: key=$(Get-TestKey $t) subject=`"$t`"$(Get-TestTag $t)")) -Sim "ok" -ScriptArgs @("-To", $To, "-Body", "x", "-Subject", $t)
Check "K37 a legacy (keyless) caller ignores keyed state and writes no SEND-INTENT" ($r.Code -eq 0 -and (Get-Count $r.Log '\[OK\] Sent to=') -eq 1 -and (Get-Count $r.Log 'SEND-INTENT:') -eq 1) $r

# A simulated run must never write the canonical send log: a fake '[OK] Sent ... key=' line there would make a real
# fire of that key DEDUP-SKIP (exit 0, no email). Tested on a COPY whose canonical path points at scratch, so a
# regression can never touch the live log.
$k38dir = Join-Path $Work "k38"; New-Item -ItemType Directory -Path $k38dir -Force | Out-Null
$k38copy = Join-Path $Work "send-copy-k38.ps1"
$k38canon = Join-Path $k38dir "send-log.txt"
$k38src = Get-Content -LiteralPath $Target -Raw -Encoding UTF8
$k38m = [regex]::Match($k38src, '(?m)^\$LogPath = "[^"\r\n]*send-log\.txt"')
if ($k38m.Success) { [System.IO.File]::WriteAllText($k38copy, $k38src.Replace($k38m.Value, '$LogPath = "' + $k38canon + '"'), (New-Object System.Text.UTF8Encoding($false))) }
Check "K38a test copy of the script has its canonical log redirected to scratch" ($k38m.Success -and (Select-String -LiteralPath $k38copy -SimpleMatch $k38canon -Quiet))
if ($k38m.Success) {
    $spellings = @($k38canon.ToUpperInvariant(), ($k38canon -replace '\\', '/'), (Join-Path $k38dir "..\k38\send-log.txt"))
    $i38 = 0
    foreach ($sp in $spellings) {
        $i38++
        $prevEAP = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            Set-Seams -Log $sp -Sim "ok"
            $args38 = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $k38copy) + $K + @("-Subject", "K38 canonical $i38", "-WhatIf")
            $out38 = & powershell @args38 2>&1 | Out-String -Width 4096
            $code38 = $LASTEXITCODE
        } finally { $ErrorActionPreference = $prevEAP; Clear-Seams }
        Check "K38b.$i38 ORA_SEND_LOG_PATH equal to the canonical log ($sp) is refused (exit 1) and nothing is written" ($code38 -eq 1 -and $out38 -match 'must not be the canonical send log' -and -not (Test-Path -LiteralPath $k38canon)) @{ Code = $code38; Log = $out38 }
    }

    # Other NAMES for the same file are not decidable from the spelling, so the rule is positive: a plain local path
    # under TEMP only. UNC/loopback and \\?\ forms, and anything outside TEMP, are refused without being written.
    function Invoke-K38Copy {
        param([string]$LogSpelling, [string]$Subj, [string]$Suffix = $script:MutexSuffix)
        $prev = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            Set-Seams -Log $LogSpelling -Sim "ok"
            [Environment]::SetEnvironmentVariable("ORA_SEND_MUTEX_SUFFIX", $Suffix)
            $a = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $k38copy) + $K + @("-Subject", $Subj, "-WhatIf")
            Push-Location -LiteralPath $Work   # cwd under TEMP: a relative or ~ spelling would otherwise look "under TEMP" to a naive guard
            try { $o = & powershell @a 2>&1 | Out-String -Width 4096 } finally { Pop-Location }
            return @{ Code = $LASTEXITCODE; Log = $o; Out = $o }
        } finally { $ErrorActionPreference = $prev; Clear-Seams }
    }
    $drive = $k38canon.Substring(0, 1)
    $unc = "\\localhost\" + $drive + "`$" + $k38canon.Substring(2)
    $r = Invoke-K38Copy $unc "K38c UNC spelling"
    Check "K38c.1 a loopback-UNC spelling of the canonical log is refused (exit 1), nothing written" ($r.Code -eq 1 -and $r.Out -match 'under TEMP' -and -not (Test-Path -LiteralPath $k38canon)) $r
    $r = Invoke-K38Copy ("\\?\" + $k38canon) "K38c extended-length spelling"
    Check "K38c.2 a \\?\ spelling of the canonical log is refused (exit 1), nothing written" ($r.Code -eq 1 -and $r.Out -match 'under TEMP' -and -not (Test-Path -LiteralPath $k38canon)) $r
    $outside = Join-Path ([Environment]::GetFolderPath("CommonApplicationData")) "k38-outside-temp-must-not-exist.txt"
    $r = Invoke-K38Copy $outside "K38c outside TEMP"
    Check "K38c.3 a log path outside TEMP is refused (exit 1), nothing written" ($r.Code -eq 1 -and $r.Out -match 'under TEMP' -and -not (Test-Path -LiteralPath $outside)) $r
    $wild = $k38canon.Substring(0, $k38canon.Length - 1) + "[t]"
    $r = Invoke-K38Copy $wild "K38c wildcard spelling"
    Check "K38c.4 a wildcard spelling (send-log.tx[t]) writes only the LITERAL file, never the canonical log" ($r.Code -eq 0 -and (Test-Path -LiteralPath $wild) -and -not (Test-Path -LiteralPath $k38canon)) $r
    $r = Invoke-K38Copy ("~\" + (Split-Path -Leaf $Work) + "\k38\send-log.txt") "K38c tilde spelling"
    Check "K38c.6 a '~' spelling (provider home expansion differs from GetFullPath) is refused (exit 1), nothing written" ($r.Code -eq 1 -and $r.Out -match 'under TEMP' -and -not (Test-Path -LiteralPath $k38canon)) $r
    $r = Invoke-K38Copy (Join-Path $Work "k38-suffix.txt") "K38c bad suffix" "bad suffix!"
    Check "K38c.5 an invalid ORA_SEND_MUTEX_SUFFIX is refused (exit 1), not silently replaced by the production lock name" ($r.Code -eq 1 -and $r.Out -match 'MUTEX_SUFFIX' -and -not (Test-Path -LiteralPath (Join-Path $Work "k38-suffix.txt"))) $r
}

Write-Host "`nR-05 contract mode: two concurrent fires with one key"
$log16 = New-TestLog
$argLine = "-NoProfile -ExecutionPolicy Bypass -File `"$Target`" -To $To -Subject `"K24 concurrent`" -Body x -DedupTaskId ora-test-task -DedupPeriodKey 2026-10-18 -WhatIf"
Set-Seams -Log $log16 -Sim "slow-ok"
[Environment]::SetEnvironmentVariable("ORA_SEND_GATE_PAUSE_MS", "4000")   # both fires read PROCEED before either writes its intent, unless the mutex serializes them
try {
    $p1 = Start-Process powershell -ArgumentList $argLine -PassThru -NoNewWindow -RedirectStandardOutput (Join-Path $Work "k16a.out") -RedirectStandardError (Join-Path $Work "k16a.err")
    $p2 = Start-Process powershell -ArgumentList $argLine -PassThru -NoNewWindow -RedirectStandardOutput (Join-Path $Work "k16b.out") -RedirectStandardError (Join-Path $Work "k16b.err")
    $null = $p1.Handle; $null = $p2.Handle   # cache the handles so ExitCode is readable later
    $done = $p1.WaitForExit(90000) -and $p2.WaitForExit(90000)
} finally { Clear-Seams }
$t16 = Get-Content -LiteralPath $log16 -Raw -Encoding UTF8
$codes = @($p1.ExitCode, $p2.ExitCode)
Check "K24 two concurrent keyed fires: exactly one [OK] Sent, one SEND-INTENT, each exit 0 or 6" ($done -and (Get-Count $t16 '\[OK\] Sent to=') -eq 1 -and (Get-Count $t16 'SEND-INTENT:') -eq 1 -and @($codes | Where-Object { $_ -ne 0 -and $_ -ne 6 }).Count -eq 0) @{ Code = ($codes -join ','); Log = $t16 }


# E1-E8: the dedup lookup runs BEFORE the Outlook readiness preflight, so a duplicate is suppressed
# without touching Outlook, while a non-duplicate send still exits 3 when Outlook is not ready.
Write-Host "`nR-05 contract mode: dedup lookup precedes the Outlook readiness preflight"
$t = "E1 dup stuck"
$r = Invoke-Send -Log (New-TestLog -Seed @("$(Get-Stamp 30) [OK] Sent to=$To cc=none subject=`"$t`" bytes=1 format=html$(Get-TestTag $t)")) -Sim "ok" -OutlookStuck -ScriptArgs ($K + @("-Subject", $t))
Check "E1 a duplicate with Outlook not ready is DEDUP-SKIP (exit 0), not exit 3" ($r.Code -eq 0 -and (Get-Count $r.Log 'DEDUP-SKIP:') -eq 1 -and $r.Log -notmatch 'stuck on startup wizard') $r

$t = "E2 fresh stuck"
$r = Invoke-Send -Log (New-TestLog) -Sim "ok" -OutlookStuck -ScriptArgs ($K + @("-Subject", $t))
Check "E2 a NON-duplicate with Outlook not ready still exits 3, no SEND-INTENT written" ($r.Code -eq 3 -and $r.Log -match 'stuck on startup wizard' -and (Get-Count $r.Log 'SEND-INTENT:') -eq 0) $r

$t = "E3 quarantined stuck"
$r = Invoke-Send -Log (New-TestLog -Seed @("$(Get-Stamp 5) [ERROR] SEND-STATE-UNKNOWN: Send() threw -- the message MAY have been sent. to=$To$(Get-TestTag $t)")) -Sim "ok" -OutlookStuck -ScriptArgs ($K + @("-Subject", $t))
Check "E3 a key whose earlier state is unknown still blocks (exit 6 DEDUP-BLOCK) even with Outlook not ready" ($r.Code -eq 6 -and $r.Log -match 'DEDUP-BLOCK:' -and $r.Log -notmatch 'stuck on startup wizard') $r

$t = "E4 locked stuck"
$lockedLog = New-TestLog -Seed @("$(Get-Stamp 90) [OK] Sent to=$To cc=none subject=`"unrelated`" bytes=1 format=html shash=0123456789abcdef")
$before = [System.IO.File]::ReadAllText($lockedLog)
$fs = New-Object System.IO.FileStream($lockedLog, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
try { $r = Invoke-Send -Log $lockedLog -Sim "ok" -OutlookStuck -ScriptArgs ($K + @("-Subject", $t)) } finally { $fs.Dispose() }
Check "E4 an unreadable send-log in contract mode fails closed (exit 6 DEDUP-UNAVAILABLE) before the preflight, log untouched" ($r.Code -eq 6 -and $r.Out -match 'DEDUP-UNAVAILABLE' -and $r.Out -notmatch 'stuck on startup wizard' -and [System.IO.File]::ReadAllText($lockedLog) -eq $before) $r

$t = "E5 force stuck"
$r = Invoke-Send -Log (New-TestLog -Seed @("$(Get-Stamp 30) [OK] Sent to=$To cc=none subject=`"$t`" bytes=1 format=html$(Get-TestTag $t)")) -Sim "ok" -OutlookStuck -ScriptArgs ($K + @("-Subject", $t, "-ForceResend"))
Check "E5 -ForceResend bypasses the early dedup, so a stuck Outlook still exits 3" ($r.Code -eq 3 -and (Get-Count $r.Log 'DEDUP-SKIP:') -eq 0) $r

$t = "E6 other period stuck"
$r = Invoke-Send -Log (New-TestLog -Seed @("$(Get-Stamp 30) [OK] Sent to=$To cc=none subject=`"$t`" bytes=1 format=html$(Get-TestTag $t '2026-10-17')")) -Sim "ok" -OutlookStuck -ScriptArgs ($K + @("-Subject", $t))
Check "E6 a sent record for another period is not a duplicate: exit 3" ($r.Code -eq 3 -and (Get-Count $r.Log 'DEDUP-SKIP:') -eq 0) $r

$t = "E7 legacy stuck"
$r = Invoke-Send -Log (New-TestLog -Seed @("$(Get-Stamp 30) [OK] Sent to=$To cc=none subject=`"$t`" bytes=1 format=html$(Get-TestTag $t)")) -Sim "ok" -OutlookStuck -ScriptArgs @("-To", $To, "-Body", "x", "-Subject", $t)
Check "E7 legacy mode (no key) with Outlook not ready still exits 3" ($r.Code -eq 3) $r

$t = "E8 dup external"
$r = Invoke-Send -Log (New-TestLog -Seed @("$(Get-Stamp 30) [OK] Sent to=$To cc=none subject=`"$t`" bytes=1 format=html$(Get-TestTag $t)")) -Sim "ok" -ScriptArgs (@("-To", "someone@example.com", "-Body", "x", "-Subject", $t) + $Keyed)
Check "E8 a duplicate key sent to an unauthorized external recipient (Outlook ready) is still refused (exit 5), never suppressed as exit 0" ($r.Code -eq 5 -and (Get-Count $r.Log 'DEDUP-SKIP:') -eq 0) $r

$t = "E9 fresh stuck external"
$r = Invoke-Send -Log (New-TestLog) -Sim "ok" -OutlookStuck -ScriptArgs (@("-To", "someone@example.com", "-Body", "x", "-Subject", $t) + $Keyed)
Check "E9 a NON-duplicate to an external recipient with Outlook not ready exits 3 BEFORE the outbound check runs (no authorization consumed)" ($r.Code -eq 3 -and $r.Log -notmatch 'OUTBOUND-CHECK' -and $r.Log -notmatch 'ATTACHMENT-CHECK') $r

$t = "E11 dup stuck external"
$r = Invoke-Send -Log (New-TestLog -Seed @("$(Get-Stamp 30) [OK] Sent to=$To cc=none subject=`"$t`" bytes=1 format=html$(Get-TestTag $t)")) -Sim "ok" -OutlookStuck -ScriptArgs (@("-To", "someone@example.com", "-Body", "x", "-Subject", $t) + $Keyed)
Check "E11 a duplicate to an EXTERNAL recipient with Outlook not ready keeps exit 3 (no outbound check, no authorization consumed)" ($r.Code -eq 3 -and $r.Log -notmatch 'OUTBOUND-CHECK' -and (Get-Count $r.Log 'DEDUP-SKIP:') -eq 0) $r

$t = "E10 stuck in-flight intent"
$r = Invoke-Send -Log (New-TestLog -Seed @("$(Get-Stamp 1) [INFO] SEND-INTENT: key=$(Get-TestKey $t) subject=`"$t`"$(Get-TestTag $t)")) -Sim "ok" -OutlookStuck -ScriptArgs ($K + @("-Subject", $t))
Check "E10 an open SEND-INTENT (a fire in flight) with Outlook not ready blocks with exit 6, never exit 3" ($r.Code -eq 6 -and $r.Log -match 'DEDUP-BLOCK:') $r

Complete-Suite
