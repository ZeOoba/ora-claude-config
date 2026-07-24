<#
.SYNOPSIS
    Generic one-shot send wrapper for ANY ORA scheduled-task report email.
.DESCRIPTION
    Thin, robust entry point over the canonical sender send-via-outlook.ps1.
    Accepts the body as a FILE (-BodyFile, preferred) or an inline string
    (-BodyHtml). Designed to be invoked NON-INTERACTIVELY (powershell -File ...)
    so no multi-line here-string is ever typed into a persistent interactive
    REPL -- that left the session in '>>' continuation and silently buffered the
    send (observed 2026-06-15, ora-owner-outreach-queue-refresh).

    Canonical send pattern for the fleet:
      1. Build the HTML body and write it to a file with Desktop Commander
         write_file (a DIRECT file write -- never type a here-string into
         interact_with_process).
      2. Invoke THIS script one-shot via start_process:
         powershell -NoProfile -ExecutionPolicy Bypass -File Send-OraReport.ps1 ...
      3. Read the printed SENDEXIT=<code> and the script's exit code.

    Routing canon: -To defaults to ggoldberg@oxfordra.net. -Cc is the documented
    exception ONLY (e.g. egoldberg@oxfordra.net for the Daily Brief). Never ze@.
.NOTES
    Exit codes mirror send-via-outlook.ps1: 0 = sent OK, 1 = usage, 2 = COM fail.
    -DryRun validates the body and prints stats but does NOT send.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Subject,
    [string]$BodyFile,
    [string]$BodyHtml,
    [string]$To = "ggoldberg@oxfordra.net",
    [string]$Cc,
    [ValidateSet("html","text")][string]$BodyFormat = "html",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$shared = Split-Path -Parent $MyInvocation.MyCommand.Definition
$sender = Join-Path $shared "send-via-outlook.ps1"
if (-not (Test-Path $sender)) { Write-Error "Sender not found: $sender"; exit 1 }

# --- Resolve body source (exactly one of BodyFile / BodyHtml) ---
if ($BodyFile -and $BodyHtml) { Write-Error "-BodyFile and -BodyHtml are mutually exclusive"; exit 1 }
if (-not $BodyFile -and -not $BodyHtml) { Write-Error "Provide -BodyFile or -BodyHtml"; exit 1 }

$tmpCreated = $false
if ($BodyHtml) {
    $BodyFile = Join-Path $env:TEMP ("ora_report_body_{0}.html" -f ([guid]::NewGuid().ToString("N")))
    $BodyHtml | Out-File -Encoding UTF8 -FilePath $BodyFile
    $tmpCreated = $true
}
if (-not (Test-Path $BodyFile)) { Write-Error "BodyFile not found: $BodyFile"; exit 1 }

try {
    if ($DryRun) {
        $bytes = (Get-Item $BodyFile).Length
        $ccDisp = if ($Cc) { $Cc } else { "(none)" }
        Write-Output "DRYRUN ok to=$To cc=$ccDisp bytes=$bytes format=$BodyFormat subject=`"$Subject`" body=$BodyFile (not sent)"
        exit 0
    }
    if ($Cc) {
        & $sender -To $To -Cc $Cc -Subject $Subject -BodyFile $BodyFile -BodyFormat $BodyFormat
    } else {
        & $sender -To $To -Subject $Subject -BodyFile $BodyFile -BodyFormat $BodyFormat
    }
    $code = $LASTEXITCODE
    Write-Output ("SENDEXIT=" + $code)
    exit $code
}
finally {
    if ($tmpCreated) { Remove-Item $BodyFile -ErrorAction SilentlyContinue }
}
