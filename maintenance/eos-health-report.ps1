<#
.SYNOPSIS
    Weekly Engineering-OS health report: doctrine-integrity drift + lane-compliance,
    emailed to ggoldberg ONLY via the shared Outlook COM sender (routing canon
    re-ratified 2026-06-10: the am-brief Daily Brief is the sole cc-Eric exception).
.PARAMETER DryRun
    Build the report but DO NOT send. Writes the HTML body to %TEMP% and prints both
    sections to stdout. Use to verify content without sending email.
.NOTES
    Deterministic (no LLM). Driven by the "ORA EOS Health" Windows Scheduled Task.
    Scripts: maintenance/doctrine-integrity-probe.py, maintenance/eos-telemetry-rollup.py.
    Sender: scheduled-tasks/_shared/send-via-outlook.ps1 (requires Outlook desktop running).
#>
[CmdletBinding()]
param([switch]$DryRun)

$ErrorActionPreference = "Stop"
$claude = "C:\Users\Owner\.claude"
$probe  = Join-Path $claude "maintenance\doctrine-integrity-probe.py"
$rollup = Join-Path $claude "maintenance\eos-telemetry-rollup.py"
$sender = Join-Path $claude "scheduled-tasks\_shared\send-via-outlook.ps1"
$date   = Get-Date -Format "yyyy-MM-dd"

function Esc([string]$s) { ($s -replace '&','&amp;' -replace '<','&lt;' -replace '>','&gt;') }

# 1. Doctrine integrity (drift)
$probeOut  = (& python $probe 2>&1 | Out-String)
$probeExit = $LASTEXITCODE
# WARN lines never flip the exit code (fail-open guards), so surface their count
# at the headline -- a degraded check must not hide behind "OK".
$warnCount = ([regex]::Matches($probeOut, '\[WARN\]')).Count
$driftStatus = if ($probeExit -eq 0) {
    if ($warnCount -gt 0) { "OK - no drift ($warnCount warning(s))" } else { "OK - no drift" }
} else { "DRIFT DETECTED (exit $probeExit)" }

# 2. Lane-compliance rollup (handles empty/missing telemetry gracefully)
$rollupOut = (& python $rollup 2>&1 | Out-String)

$body = @"
<html><body style="font-family:Segoe UI,Arial,sans-serif;font-size:13px;color:#1B2A4A">
<h2 style="color:#1B2A4A">ORA Engineering OS &mdash; Health $date</h2>
<h3>1. Doctrine integrity &mdash; $driftStatus</h3>
<pre style="background:#F5F0E8;padding:10px;border-radius:6px;white-space:pre-wrap">$(Esc $probeOut)</pre>
<h3>2. Lane compliance (telemetry rollup)</h3>
<pre style="background:#F5F0E8;padding:10px;border-radius:6px;white-space:pre-wrap">$(Esc $rollupOut)</pre>
<p style="color:#888;font-size:11px">Auto-generated weekly by the "ORA EOS Health" task. Drift = doctrine-integrity-probe; compliance = eos-telemetry-rollup. Reply to tune the gates.</p>
</body></html>
"@

$tmp = Join-Path $env:TEMP "eos-health-$date.html"
$body | Out-File -Encoding UTF8 $tmp

if ($DryRun) {
    Write-Output "DRY RUN - email NOT sent. Body written to: $tmp"
    Write-Output "===== 1. DOCTRINE: $driftStatus ====="
    Write-Output $probeOut
    Write-Output "===== 2. COMPLIANCE ROLLUP ====="
    Write-Output $rollupOut
    exit 0
}

& $sender -To "ggoldberg@oxfordra.net" `
    -Subject "[ORA] EOS Health - $date" -BodyFile $tmp -BodyFormat html
exit $LASTEXITCODE
