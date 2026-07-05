# desktop-push-data.ps1 -- Windows-side push of the two data corpora to the
# ORA Linux server. ALTERNATIVE to the server-side rclone pull
# (server/rclone-sync.sh) for the no-rclone option. PowerShell 5.1
# compatible. ASCII only.
#
# Pushes (top-level files only; both corpora are flat):
#   %USERPROFILE%\OneDrive - Oxford Capital Partners (1)\eric spreadsheets\*
#     -> server:~/ora-data/eric-spreadsheets/
#   %USERPROFILE%\OneDrive - Oxford Capital Partners (1)\Property Financials\*
#     -> server:~/ora-data/property-financials/
#
# Transport is scp (the OpenSSH client built into Windows 10+). robocopy
# cannot target a Linux ssh host directly, so it is not used here; if you
# later mount the server over SMB/NFS, robocopy /MIR is the equivalent.
#
# REQUIREMENTS:
#   - OneDrive files HYDRATED ("Always keep on this device") -- scp cannot
#     read cloud placeholders.
#   - ssh key or password auth to the server already working.
#
# Direction: desktop -> server only. The server copies are replicas; never
# edit ~/ora-data on the server. Do NOT run this while the hourly
# server-side rclone timer (ora-data-sync.timer) is enabled -- pick ONE
# transport, otherwise the rclone sync will delete files it did not put there.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File desktop-push-data.ps1 `
#     -ServerHost 192.168.1.50 -ServerUser gabriel [-DryRun]

param(
    [Parameter(Mandatory = $true)][string]$ServerHost,
    [Parameter(Mandatory = $true)][string]$ServerUser,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$OneDriveRoot = Join-Path $env:USERPROFILE "OneDrive - Oxford Capital Partners (1)"
$Pushes = @(
    @{ Source = (Join-Path $OneDriveRoot "eric spreadsheets");   Dest = "ora-data/eric-spreadsheets" },
    @{ Source = (Join-Path $OneDriveRoot "Property Financials"); Dest = "ora-data/property-financials" }
)

$Ssh = Get-Command ssh -ErrorAction SilentlyContinue
$Scp = Get-Command scp -ErrorAction SilentlyContinue
if (-not $Ssh -or -not $Scp) {
    Write-Host "ERROR: ssh/scp not found. Install 'OpenSSH Client' (Settings > Optional features)."
    exit 1
}

foreach ($Push in $Pushes) {
    if (-not (Test-Path -LiteralPath $Push.Source)) {
        Write-Host ("ERROR: source missing: " + $Push.Source)
        Write-Host "Is OneDrive signed in and hydrated on this machine?"
        exit 1
    }
}

$Remote = "$ServerUser@$ServerHost"
Write-Host ("Target: " + $Remote)

if (-not $DryRun) {
    & ssh $Remote "mkdir -p ora-data/eric-spreadsheets ora-data/property-financials"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: ssh mkdir failed (check host/user/key)."
        exit 1
    }
}

$Failed = 0
foreach ($Push in $Pushes) {
    $Files = @(Get-ChildItem -LiteralPath $Push.Source -File | Where-Object { $_.Name -notlike "~*" })
    Write-Host ""
    Write-Host ($Push.Source + "  ->  " + $Remote + ":" + $Push.Dest + "/  (" + $Files.Count + " files)")
    if ($Files.Count -eq 0) {
        Write-Host "  WARN: no files found (placeholders not hydrated?)"
        continue
    }
    if ($DryRun) {
        foreach ($File in $Files) { Write-Host ("  would push: " + $File.Name) }
        continue
    }
    # One scp invocation per corpus: all file paths, then the remote dest.
    $ScpArgs = @()
    foreach ($File in $Files) { $ScpArgs += $File.FullName }
    $ScpArgs += ($Remote + ":" + $Push.Dest + "/")
    & scp @ScpArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host ("  ERROR: scp failed for " + $Push.Source)
        $Failed = 1
    }
}

Write-Host ""
if ($DryRun) {
    Write-Host "Dry run complete -- nothing was copied."
    exit 0
}
if ($Failed -ne 0) {
    Write-Host "desktop-push-data: FAILED (see errors above)."
    exit 1
}
Write-Host "desktop-push-data: done. On the server run: bash ~/.claude/server/verify-setup.sh"
exit 0
