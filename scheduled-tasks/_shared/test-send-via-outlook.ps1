<#
.SYNOPSIS
    Tests for send-via-outlook.ps1's -Attachment parameter and its backward
    compatibility with every pre-existing calling convention.

.DESCRIPTION
    Every case runs the real script as a CHILD PROCESS with -WhatIf, so the
    Outlook COM call is never reached and no mail is ever sent. The script's
    audit log is redirected to a temp file via ORA_SEND_LOG_PATH, which the
    script honours ONLY under -WhatIf -- a real send always writes the
    canonical log, so tests can never blind the audit trail.

    Run:  powershell -NoProfile -File test-send-via-outlook.ps1
    Exit: 0 = all passed, 1 = at least one failure.
#>

$ErrorActionPreference = "Stop"
$script:Pass = 0
$script:Fail = 0

$Target = Join-Path $PSScriptRoot "send-via-outlook.ps1"
if (-not (Test-Path $Target)) { Write-Host "FATAL: $Target not found"; exit 1 }

$Work = Join-Path ([System.IO.Path]::GetTempPath()) ("send-test-" + [guid]::NewGuid().ToString("N").Substring(0,8))
New-Item -ItemType Directory -Path $Work -Force | Out-Null
$LogFile = Join-Path $Work "send-log.txt"

# --- fixtures ---
$FileA = Join-Path $Work "report.ics"
$FileB = Join-Path $Work "second file.txt"   # space in name on purpose
$SubDir = Join-Path $Work "adir"
Set-Content -Path $FileA -Value "BEGIN:VCALENDAR" -Encoding UTF8
Set-Content -Path $FileB -Value "hello" -Encoding UTF8
New-Item -ItemType Directory -Path $SubDir -Force | Out-Null
$Big = Join-Path $Work "big.bin"
[System.IO.File]::WriteAllBytes($Big, (New-Object byte[] (21MB)))

function Invoke-Case {
    param([string[]]$ScriptArgs)
    if (Test-Path $LogFile) { Remove-Item $LogFile -Force }
    $env:ORA_SEND_LOG_PATH = $LogFile
    $all = @("-NoProfile", "-File", $Target) + $ScriptArgs + @("-WhatIf")
    # stderr merged so an ERROR line is visible in $out as well as the log.
    # EAP must drop to Continue for this call: with the script-scoped "Stop", a
    # child's stderr captured via 2>&1 becomes a TERMINATING error and kills the
    # harness on the first ERROR-path case -- the same trap send-via-outlook.ps1
    # itself documents around its check_external_send.py invocation.
    $prevEAP = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        # -Width prevents Out-String from wrapping to the console's column width
        # (default 80), which otherwise splits a long PowerShell error message
        # mid-word across a newline -- e.g. "for parameter" became "for \nparameter",
        # silently breaking any -like/-match check against the message text
        # (found in adversarial-fix follow-up, 2026-09-18).
        $out = & powershell @all 2>&1 | Out-String -Width 4096
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prevEAP }
    $log = if (Test-Path $LogFile) { Get-Content $LogFile -Raw } else { "" }
    Remove-Item Env:\ORA_SEND_LOG_PATH -ErrorAction SilentlyContinue
    return @{ Code = $code; Log = $log; Out = $out }
}

function Assert-Case {
    param(
        [string]$Name,
        [string[]]$ScriptArgs,
        [int]$ExpectCode,
        [string[]]$LogMustContain = @(),
        [string[]]$LogMustNotContain = @()
    )
    $r = Invoke-Case -ScriptArgs $ScriptArgs
    $problems = @()
    if ($r.Code -ne $ExpectCode) { $problems += "exit $($r.Code), expected $ExpectCode" }
    foreach ($needle in $LogMustContain) {
        if ($r.Log -notlike "*$needle*") { $problems += "log missing '$needle'" }
    }
    foreach ($needle in $LogMustNotContain) {
        if ($r.Log -like "*$needle*") { $problems += "log unexpectedly contains '$needle'" }
    }
    if ($problems.Count -eq 0) {
        Write-Host ("  PASS  " + $Name)
        $script:Pass++
    } else {
        Write-Host ("  FAIL  " + $Name + " -- " + ($problems -join "; "))
        $trimmed = ($r.Log -replace "`r?`n", " | ")
        if ($trimmed.Length -gt 300) { $trimmed = $trimmed.Substring(0, 300) + "..." }
        Write-Host ("        log: " + $trimmed)
        $script:Fail++
    }
}

$To = "ggoldberg@oxfordra.net"

Write-Host "`nBackward compatibility (no -Attachment: behaviour must be unchanged)"
Assert-Case -Name "plain -Body send still dry-runs clean" `
    -ScriptArgs @("-To", $To, "-Subject", "Plain", "-Body", "hello") `
    -ExpectCode 0 -LogMustContain @("DRY RUN: would send", "cc=none") -LogMustNotContain @("attachments=")

Assert-Case -Name "-BodyFile still works" `
    -ScriptArgs @("-To", $To, "-Subject", "FromFile", "-BodyFile", $FileB) `
    -ExpectCode 0 -LogMustContain @("DRY RUN: would send") -LogMustNotContain @("attachments=")

Assert-Case -Name "missing -Body and -BodyFile still exit 1" `
    -ScriptArgs @("-To", $To, "-Subject", "NoBody") `
    -ExpectCode 1 -LogMustContain @("Must provide either")

Assert-Case -Name "missing BodyFile still exit 1" `
    -ScriptArgs @("-To", $To, "-Subject", "Gone", "-BodyFile", (Join-Path $Work "nope.html")) `
    -ExpectCode 1 -LogMustContain @("BodyFile not found")

Assert-Case -Name "-Body and -BodyFile together still exit 1" `
    -ScriptArgs @("-To", $To, "-Subject", "Both", "-Body", "x", "-BodyFile", $FileB) `
    -ExpectCode 1 -LogMustContain @("mutually exclusive")

Write-Host "`nAttachment: happy paths"
Assert-Case -Name "single attachment is accepted and logged" `
    -ScriptArgs @("-To", $To, "-Subject", "One", "-Body", "x", "-Attachment", $FileA) `
    -ExpectCode 0 -LogMustContain @("DRY RUN: would send", "attachments=1", "report.ics")

# Multiple attachments travel as ONE '|'-delimited token: under `powershell -File`
# a [string[]] parameter cannot receive a real multi-element array (verified).
Assert-Case -Name "two attachments via the '|' form, one name containing a space" `
    -ScriptArgs @("-To", $To, "-Subject", "Two", "-Body", "x", "-Attachment", "$FileA|$FileB") `
    -ExpectCode 0 -LogMustContain @("attachments=2", "report.ics", "second file.txt")

# These two assert on the PowerShell BINDER's own error text/id, not just exit 1 +
# no DRY RUN -- a looser assertion here previously passed identically whether or
# not PositionalBinding=$false was even present (caught in adversarial review,
# 2026-09-18: reverting that setting kept both cases green under the old
# assertions, because "-Body and -BodyFile are mutually exclusive" ALSO exits 1
# with no DRY RUN line -- the wrong mechanism, same exit code). A regression that
# silently removes PositionalBinding=$false must fail these tests.
$stray = Invoke-Case -ScriptArgs @("-To", $To, "-Subject", "Space", "-Body", "x", "-Attachment", $FileA, $FileB)
if ($stray.Code -eq 1 -and $stray.Out -like "*PositionalParameterNotFound*") {
    Write-Host "  PASS  space-separated attachments rejected BY THE BINDER (PositionalParameterNotFound), not a silent misbind"; $script:Pass++
} else {
    Write-Host "  FAIL  space-separated attachments -- expected PositionalParameterNotFound, got exit $($stray.Code): $($stray.Out.Substring(0, [Math]::Min(150, $stray.Out.Length)))"
    $script:Fail++
}

$posTok = Invoke-Case -ScriptArgs @("-To", $To, "-Subject", "Pos", "-Body", "x", "stray-token")
if ($posTok.Code -eq 1 -and $posTok.Out -like "*PositionalParameterNotFound*" -and $posTok.Out -like "*stray-token*") {
    Write-Host "  PASS  stray positional argument rejected BY THE BINDER, naming the offending token"; $script:Pass++
} else {
    Write-Host "  FAIL  stray positional argument -- expected PositionalParameterNotFound naming 'stray-token', got exit $($posTok.Code): $($posTok.Out.Substring(0, [Math]::Min(150, $posTok.Out.Length)))"
    $script:Fail++
}

Write-Host "`nAttachment: the path must be resolved, not passed through"
Push-Location $Work
$rel = Invoke-Case -ScriptArgs @("-To", $To, "-Subject", "Rel", "-Body", "x", "-Attachment", ".\report.ics")
Pop-Location
if ($rel.Code -eq 0 -and $rel.Log -like "*$FileA*") {
    Write-Host "  PASS  relative path resolved to an absolute path before the COM call"; $script:Pass++
} else {
    Write-Host "  FAIL  relative path not resolved (exit $($rel.Code)); Outlook COM resolves relative paths against ITS cwd, not the caller's"
    $script:Fail++
}

Write-Host "`nAttachment: rejections (must fail closed, never send a mail promising a missing file)"
Assert-Case -Name "missing attachment file exits 1" `
    -ScriptArgs @("-To", $To, "-Subject", "Missing", "-Body", "x", "-Attachment", (Join-Path $Work "absent.ics")) `
    -ExpectCode 1 -LogMustContain @("Attachment not found") -LogMustNotContain @("DRY RUN: would send")

Assert-Case -Name "a directory is not a valid attachment" `
    -ScriptArgs @("-To", $To, "-Subject", "Dir", "-Body", "x", "-Attachment", $SubDir) `
    -ExpectCode 1 -LogMustContain @("not a file") -LogMustNotContain @("DRY RUN: would send")

# -Attachment "" as a bare CLI token to an EXTERNAL process never reaches this
# script's own IsNullOrWhiteSpace check at all: Windows process-argument
# marshaling drops an empty-string argv element before the child starts, so
# PowerShell's own parameter binder rejects it first, with NO script-log line
# (verified identically for a splatted array and a directly typed invocation --
# not a harness artifact). Still fail-closed (exit 1, no send), just at a
# different layer than the in-script check. Assert on THAT mechanism, not on a
# log line this path structurally cannot produce.
$emptyBinder = Invoke-Case -ScriptArgs @("-To", $To, "-Subject", "Empty", "-Body", "x", "-Attachment", "")
if ($emptyBinder.Code -eq 1 -and $emptyBinder.Out -like "*Missing an argument for parameter*Attachment*" -and $emptyBinder.Log -eq "") {
    Write-Host "  PASS  a bare empty-string attachment is rejected by PowerShell's own binder (exit 1, no send)"; $script:Pass++
} else {
    Write-Host "  FAIL  bare empty-string attachment -- expected a binder MissingArgument error with no log line, got exit $($emptyBinder.Code)"
    $script:Fail++
}

# The in-script empty/whitespace check IS reachable -- via an element that
# survives the OS argument boundary as part of a non-empty string and only
# becomes empty after THIS script's own -split '\|'. This is the case that
# actually exercises the IsNullOrWhiteSpace branch end-to-end.
Assert-Case -Name "an empty element from '||' hits the in-script empty check" `
    -ScriptArgs @("-To", $To, "-Subject", "Empty2", "-Body", "x", "-Attachment", "$FileA||") `
    -ExpectCode 1 -LogMustContain @("Attachment path is empty") -LogMustNotContain @("DRY RUN: would send")

# $null (in-process only -- powershell -File cannot pass a literal $null on the
# command line, so this needs -Command in a FRESH CHILD PROCESS, never an
# in-process `&` call: the target ends in `exit N`, and `exit` inside a directly
# invoked script terminates the calling host process, which would kill this test
# runner). $null -split anything returns an EMPTY array in PowerShell, not $null,
# so without an explicit guard -Attachment $null looked identical to -Attachment
# never having been passed at all (found in adversarial review, 2026-09-18).
# Both null probes below run as a nested -Command process whose stderr is merged
# via 2>&1 -- under this script's OWN top-level $ErrorActionPreference="Stop",
# that turns the child's Write-Error output into a TERMINATING error and kills
# the whole harness (this is the exact trap send-via-outlook.ps1's own comments
# document around its check_external_send.py call; hit here directly the first
# time this was written, without the guard, 2026-09-18). EAP must drop to
# Continue for the call, same as Invoke-Case does.
$prevEAP2 = $ErrorActionPreference
$ErrorActionPreference = "Continue"

$nullCmd = "& '$Target' -To '$To' -Subject 'Null' -Body 'x' -Attachment `$null -WhatIf | Out-Null; exit `$LASTEXITCODE"
& powershell -NoProfile -Command $nullCmd 2>&1 | Out-Null
if ($LASTEXITCODE -eq 1) {
    Write-Host "  PASS  -Attachment `$null (in-process) is rejected, not silently treated as absent"; $script:Pass++
} else {
    Write-Host "  FAIL  -Attachment `$null exited $LASTEXITCODE, expected 1"; $script:Fail++
}

# Narrower case: a real array with a NULL ELEMENT inside it, not the whole
# parameter being null. Windows PowerShell 5.1's @($nullTypedParam) quirk only
# fires for the whole-parameter case, so this exercises the separate per-element
# guard inside the loop.
$nullElemCmd = "& '$Target' -To '$To' -Subject 'NullElem' -Body 'x' -Attachment @('$FileA', `$null) -WhatIf | Out-Null; exit `$LASTEXITCODE"
& powershell -NoProfile -Command $nullElemCmd 2>&1 | Out-Null
if ($LASTEXITCODE -eq 1) {
    Write-Host "  PASS  a null ELEMENT inside an in-process array is rejected"; $script:Pass++
} else {
    Write-Host "  FAIL  null element inside an array exited $LASTEXITCODE, expected 1"; $script:Fail++
}

$ErrorActionPreference = $prevEAP2

Assert-Case -Name "oversize attachment exits 1 with a size message" `
    -ScriptArgs @("-To", $To, "-Subject", "Big", "-Body", "x", "-Attachment", $Big) `
    -ExpectCode 1 -LogMustContain @("exceeds") -LogMustNotContain @("DRY RUN: would send")

Assert-Case -Name "one bad attachment rejects the whole send" `
    -ScriptArgs @("-To", $To, "-Subject", "Mixed", "-Body", "x", "-Attachment", "$FileA|$(Join-Path $Work 'absent.ics')") `
    -ExpectCode 1 -LogMustContain @("Attachment not found") -LogMustNotContain @("DRY RUN: would send")

Write-Host "`nAttachment x outbound gate (fail-closed: no files on an external send)"
Assert-Case -Name "external recipient + attachment is refused (exit 5)" `
    -ScriptArgs @("-To", "outsider@example.com", "-Subject", "Ext", "-Body", "x", "-Attachment", $FileA) `
    -ExpectCode 5 -LogMustContain @("ATTACHMENT-CHECK") -LogMustNotContain @("DRY RUN: would send")

Assert-Case -Name "internal send with attachment is NOT blocked by that rule" `
    -ScriptArgs @("-To", "$To;egoldberg@oxfordra.net", "-Subject", "Int", "-Body", "x", "-Attachment", $FileA) `
    -ExpectCode 0 -LogMustContain @("DRY RUN: would send", "attachments=1")

Write-Host "`nAudit-log integrity"
$env:ORA_SEND_LOG_PATH = $LogFile
$canonicalBefore = "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-log.txt"
$sizeBefore = if (Test-Path $canonicalBefore) { (Get-Item $canonicalBefore).Length } else { 0 }
& powershell -NoProfile -File $Target -To $To -Subject "LogRedirect" -Body "x" -WhatIf | Out-Null
$sizeAfter = if (Test-Path $canonicalBefore) { (Get-Item $canonicalBefore).Length } else { 0 }
Remove-Item Env:\ORA_SEND_LOG_PATH -ErrorAction SilentlyContinue
if ($sizeBefore -eq $sizeAfter) {
    Write-Host "  PASS  -WhatIf + ORA_SEND_LOG_PATH did not touch the canonical send log"; $script:Pass++
} else {
    Write-Host "  FAIL  canonical send log grew during a redirected dry run"; $script:Fail++
}

Remove-Item $Work -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "`n$script:Pass passed, $script:Fail failed"
if ($script:Fail -gt 0) { exit 1 }
exit 0
