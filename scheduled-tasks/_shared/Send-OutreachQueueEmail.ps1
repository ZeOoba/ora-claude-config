<#
.SYNOPSIS
    One-shot send wrapper for the weekly Owner-Outreach Queue refresh (ORA Phase 1).
.DESCRIPTION
    Builds the email body INTERNALLY from short scalar args, writes it to a temp
    BodyFile, and forwards to the canonical send path send-via-outlook.ps1.
    Designed to be invoked NON-INTERACTIVELY (powershell -File ...) so that no
    multi-line here-string ever crosses an interactive REPL boundary -- this
    eliminates the '>>' continuation-buffering quirk seen 2026-06-15.
    Routing canon: ggoldberg@oxfordra.net ONLY, never cc. No -Cc is exposed.
.NOTES
    Exit codes mirror send-via-outlook.ps1: 0 = sent OK, 1 = usage, 2 = COM fail.
    -DryRun writes/validates the body and prints stats but does NOT send.
#>
[CmdletBinding()]
param(
    [string]$Subject,
    [string]$AlertLine,
    [int]$Promoted,
    [string]$Tier0Coverage,
    [string]$Funnel,
    [string]$Freshness,
    [string]$Master,
    [string]$WorkbookPath,
    [int]$ExitCode = 0,
    [string]$To = "ggoldberg@oxfordra.net",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$shared = Split-Path -Parent $MyInvocation.MyCommand.Definition
$sender = Join-Path $shared "send-via-outlook.ps1"
if (-not (Test-Path $sender)) { Write-Error "Sender not found: $sender"; exit 1 }

# --- Build HTML body internally (no shell quoting of multi-line content) ---
$esc = { param($s) if ($null -eq $s) { "" } else { [System.Net.WebUtility]::HtmlEncode([string]$s) } }
if ($AlertLine) {
    if (-not $Subject) { $Subject = "ORA Owner-Outreach Queue -- Phase 1 -- ALERT" }
    $html = "<p><b>ALERT - queue refresh did NOT write.</b> The script refused (fail-loud guard). No queue or numbers fabricated.</p>" +
            "<p><b>FATAL line:</b><br><code>" + (& $esc $AlertLine) + "</code></p>"
} else {
    if (-not $Subject) { $Subject = "ORA Owner-Outreach Queue -- Phase 1" }
    $html = "<p>Weekly Phase-1 Owner-Outreach Queue regenerated from the off-market master.</p>" +
            "<table border='0' cellpadding='4'>" +
            "<tr><td><b>PROMOTED (queue rows)</b></td><td>$Promoted</td></tr>" +
            "<tr><td><b>Tier-0 mailing coverage</b></td><td>" + (& $esc $Tier0Coverage) + "</td></tr>" +
            "<tr><td><b>Promotion funnel</b></td><td>" + (& $esc $Funnel) + "</td></tr>" +
            "<tr><td><b>Master freshness</b></td><td>" + (& $esc $Freshness) + "</td></tr>" +
            "</table>" +
            "<p><b>Source master:</b> " + (& $esc $Master) + "</p>" +
            "<p><b>Queue workbook written to:</b><br>" + (& $esc $WorkbookPath) + "</p>" +
            "<p>Script exit code $ExitCode.</p>"
}

$tmp = Join-Path $env:TEMP ("ora_outreach_body_{0}.html" -f ([guid]::NewGuid().ToString("N")))
$html | Out-File -Encoding UTF8 -FilePath $tmp
try {
    if ($DryRun) {
        $bytes = (Get-Item $tmp).Length
        Write-Output "DRYRUN ok to=$To bytes=$bytes subject=`"$Subject`" body=$tmp (not sent)"
        exit 0
    }
    & $sender -To $To -Subject $Subject -BodyFile $tmp -BodyFormat "html"
    $code = $LASTEXITCODE
    Write-Output ("SENDEXIT=" + $code)
    exit $code
}
finally {
    Remove-Item $tmp -ErrorAction SilentlyContinue
}
