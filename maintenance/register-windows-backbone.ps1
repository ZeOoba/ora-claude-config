# ORA Windows-Backbone Task Restore -- one-command re-registration after machine loss/migration
# ------------------------------------------------------------------------------------------------
# WHY (v1.0 2026-07-29, systematization candidate from the Phase 3-5 migration): the six Windows
# Task Scheduler jobs are the app-INDEPENDENT automation backbone (dead-man, heartbeat push,
# watchdog, mirrors, disk hygiene), but their registration specs lived only in scattered script
# headers -- and the 2026-07 machine migration silently lost TWO of them (ClaudeFleetMirror,
# re-registered 2026-07-16; ORA Nightly Disk Clean, not noticed until 2026-07-29). This script
# makes the next migration a one-command restore, and setup-self-audit's windows-tasks check
# (added 2026-07-29) is the standing tripwire that tells you to run it.
#
# MODES
#   -Export   snapshot every PRESENT backbone task's FULL definition (triggers, settings,
#             actions) to maintenance\windows-task-xml\<name>.xml -- git-tracked, so the
#             definitions ride the ora-claude-config backup off-machine. Run after ANY
#             deliberate task change so the snapshot stays current.
#   (default) verify-first restore: for each backbone task -- PRESENT -> OK (never touched);
#             MISSING + XML snapshot exists -> Register-ScheduledTask -Xml (exact restore);
#             MISSING + no XML -> FAIL loudly with the owning script's header to consult.
#   -DryRun   with default mode: report what WOULD be restored, register nothing.
#
# Fail-open per maintenance conventions: per-task errors are reported and the script continues;
# exit 0 = all present/restored, exit 1 = at least one missing/failed. ASCII-only (PS 5.1).
# Task list is the SAME set setup-self-audit.py's WINDOWS_TASKS checks -- keep the two in sync.

param([switch]$Export, [switch]$DryRun)

$XmlDir = Join-Path $PSScriptRoot 'windows-task-xml'
$Backbone = @(
    'ORA Fleet Dead-Man',
    'ORA Fleet Heartbeat Push',
    'ORA Stuck-Session Watchdog',
    'ORA Command Center - Mirror Deploy',
    'ClaudeFleetMirror',
    'ORA Nightly Disk Clean',
    # Added 2026-08-04 (OI-076): both found missing this scan set. ORA PM
    # Crons was unregistered on this machine ~6 weeks (same migration-loss
    # class as ClaudeFleetMirror above); ORA Claude Desktop Wake-and-Launch
    # keeps Claude Desktop running, which both Claude fleets depend on to
    # fire at all. Kept in sync with setup-self-audit.py's WINDOWS_TASKS.
    'ORA PM Crons',
    'ORA Claude Desktop Wake-and-Launch'
)

if (-not (Test-Path $XmlDir)) { New-Item -ItemType Directory -Path $XmlDir | Out-Null }
$fail = 0

if ($Export) {
    foreach ($name in $Backbone) {
        $t = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
        if (-not $t) { Write-Output ("SKIP    {0} -- not registered, nothing to export" -f $name); $fail = 1; continue }
        try {
            $xml = Export-ScheduledTask -TaskName $name
            $dest = Join-Path $XmlDir ($name + '.xml')
            # Export-ScheduledTask emits UTF-16; write UTF-8 for clean git diffs.
            [IO.File]::WriteAllText($dest, $xml, (New-Object Text.UTF8Encoding $false))
            Write-Output ("EXPORT  {0} -> {1}" -f $name, $dest)
        } catch { Write-Output ("ERROR   {0} export failed: {1}" -f $name, $_.Exception.Message); $fail = 1 }
    }
    exit $fail
}

foreach ($name in $Backbone) {
    $t = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($t) { Write-Output ("OK      {0} (state {1})" -f $name, $t.State); continue }
    $src = Join-Path $XmlDir ($name + '.xml')
    if (-not (Test-Path $src)) {
        Write-Output ("FAIL    {0} MISSING and no XML snapshot at {1} -- register manually per the owning script's header, then run -Export" -f $name, $src)
        $fail = 1; continue
    }
    if ($DryRun) { Write-Output ("WOULD-RESTORE {0} from {1}" -f $name, $src); continue }
    try {
        Register-ScheduledTask -TaskName $name -Xml (Get-Content $src -Raw) | Out-Null
        $t2 = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
        if ($t2) { Write-Output ("RESTORED {0} (state {1})" -f $name, $t2.State) }
        else     { Write-Output ("ERROR   {0} registration reported success but task not found" -f $name); $fail = 1 }
    } catch { Write-Output ("ERROR   {0} restore failed: {1}" -f $name, $_.Exception.Message); $fail = 1 }
}
exit $fail
