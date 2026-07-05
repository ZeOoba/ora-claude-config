#Requires -Version 5.1
<#
WHY THIS SCRIPT EXISTS
  Brings up the local dev environment for the "oxford-command-center" project on the
  pinned profile C:\Users\Owner and verifies Claude Code runs there. It is verify-first
  and idempotent: every step probes current state before acting and skips work that is
  already satisfied, so re-running on a healthy box is a fast no-op.
  It is LOUD, not fire-and-forget: unlike maintenance/ora-nightly-disk.ps1 and
  hooks/ram-guard.ps1 (which blanket-set SilentlyContinue because a missed cleanup is
  harmless), a broken dev setup is not harmless, so every step wraps its own try/catch
  and records a PASS/WARN/FAIL row instead of silently swallowing errors.
  Guardrails: it never overwrites or reformats any config (in particular the committed
  .claude\settings.json is read-only -- hash-checked before and after this run), never
  deletes anything, never kills a process it did not launch, never installs/upgrades/
  touches Claude Code (verify-only), never starts the dev server unless -StartDevServer
  is passed (and always stops what it launched), and never disables TLS verification or
  changes the execution policy.
  It exits non-zero ONLY when a hard prerequisite is unmet: Node >=20 unresolved after
  an install attempt, the project directory/package.json is absent, or the committed
  .claude\settings.json is corrupt or was mutated during the run. Everything else
  (winget missing, non-admin long-paths, proxy/TLS posture, occupied ports, missing
  Claude auth, multiple Node/Git/Claude installs) is a WARN with an exact remediation
  string, and the run still exits 0.
  This is the DEV-PROJECT bring-up subset only. Full machine migration (Python for
  hooks, gh CLI, netlify CLI, Outlook COM, secrets, OneDrive hydration) is covered by
  docs/MIGRATION_RUNBOOK.md -- see that doc rather than duplicating it here.
  HOW TO RUN: invoke as a script, e.g.
    powershell -ExecutionPolicy Bypass -File maintenance\setup-desktop-windows.ps1
  Do NOT dot-source or Import it -- it ends with exit 0/1, which would terminate the
  caller's shell if dot-sourced.
#>
param(
    [string]$ProjectPath = 'C:\Users\Owner\oxford-command-center',
    [string]$LogPath = '',
    [switch]$SkipInstall,
    [switch]$WhatIfInstall,
    [switch]$StartDevServer,
    [int]$BrainPort = 8911,
    [int]$WebPort = 5273,
    [int]$HealthTimeoutSec = 60
)

if ([string]::IsNullOrEmpty($LogPath)) {
    $LogPath = Join-Path $PSScriptRoot 'setup-desktop-windows.log'
}

$script:Results = New-Object System.Collections.ArrayList
$script:HardFailCount = 0
$script:IsAdmin = $false
$script:WingetAvailable = $false
$script:NodeMajor = $null
$script:SettingsHashBefore = ''
$script:SettingsPath = Join-Path $ProjectPath '.claude\settings.json'
$script:PkgScripts = @()
$script:HasDevScript = $false
$script:HasGateScript = $false
$script:HasEnsureDepsScript = $false
$script:GateAlreadyRan = $false
$script:BrainPortBusy = $false
$script:WebPortBusy = $false

# ---------------------------------------------------------------------------
# Small named functions (house style: maintenance/ora-nightly-disk.ps1, eos-health-report.ps1)
# ---------------------------------------------------------------------------

function Log {
    param([string]$Level, [string]$Msg)
    $line = "{0}  [{1}] {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Msg
    try {
        Add-Content -LiteralPath $LogPath -Value $line -ErrorAction Stop
    } catch {
        # Logging must never abort the run; fall back to console only. Announce the
        # fallback ONCE so a silently-dropped log is not mistaken for a clean run.
        if (-not $script:LogWriteFailed) {
            $script:LogWriteFailed = $true
            Write-Host ("[WARN] log write to {0} failed -- continuing console-only for the rest of this run ({1})" -f $LogPath, $_.Exception.Message) -ForegroundColor Yellow
        }
    }
    $color = 'Gray'
    if ($Level -eq 'PASS') { $color = 'Green' }
    elseif ($Level -eq 'WARN') { $color = 'Yellow' }
    elseif ($Level -eq 'FAIL') { $color = 'Red' }
    Write-Host $line -ForegroundColor $color
}

function Add-Result {
    param(
        [string]$Step,
        [string]$Status,
        [string]$Detail,
        [bool]$Hard = $false
    )
    $row = [pscustomobject]@{ Step = $Step; Status = $Status; Detail = $Detail }
    [void]$script:Results.Add($row)
    if ($Status -eq 'FAIL' -and $Hard) { $script:HardFailCount++ }
    Log $Status ("{0}: {1}" -f $Step, $Detail)
}

function Invoke-Native {
    # Route EVERY external command through here and judge success by the integer
    # $LASTEXITCODE -- never $? (which is $true even when a piped native command
    # exits non-zero) and never a bare try/catch (npm/git/winget signal via exit
    # code, not exceptions). Parameter is named CmdArgs, NOT Args, to avoid
    # colliding with the automatic $args variable.
    param([string]$Exe, [string[]]$CmdArgs = @())
    try {
        $out = & $Exe @CmdArgs 2>&1 | Out-String
        $code = $LASTEXITCODE
        if ($null -eq $code) { $code = 0 }
    } catch {
        $out = $_.Exception.Message
        $code = -1
    }
    [pscustomobject]@{ Ok = ($code -eq 0); Code = $code; Out = $out }
}

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($id)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Update-SessionPath {
    # In-process PATH rebuild from the Machine + User registry hives after an install,
    # so later probes in THIS shell resolve a freshly installed tool. Never persists a
    # registry PATH edit; a new shell or reboot is the guaranteed fallback.
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ($null -eq $machine) { $machine = '' }
    if ($null -eq $user) { $user = '' }
    $rebuilt = $machine + ';' + $user
    # Preserve process-only PATH entries inherited from the launching shell (portable
    # toolchains / fnm / volta shims) that are absent from the registry hives, so a
    # rebuild never un-resolves a tool that was already on PATH at script start. Dedup
    # keeps the value from growing across the several calls to this function.
    $seen = @{}
    foreach ($e in ($rebuilt -split ';')) {
        if ($e -ne '') { $seen[$e.TrimEnd('\').ToLowerInvariant()] = $true }
    }
    $extra = @()
    foreach ($e in ($env:Path -split ';')) {
        if ($e -ne '') {
            $k = $e.TrimEnd('\').ToLowerInvariant()
            if (-not $seen.ContainsKey($k)) { $seen[$k] = $true; $extra += $e }
        }
    }
    if ($extra.Count -gt 0) { $rebuilt = $rebuilt + ';' + ($extra -join ';') }
    $env:Path = $rebuilt
}

function Get-NodeMajor {
    # Returns the parsed [version] of node (numeric compare, never string sort),
    # or $null if node is absent/unreadable.
    $r = Invoke-Native -Exe 'node' -CmdArgs @('-v')
    if ($r.Ok -and $r.Out -match 'v(\d+\.\d+\.\d+)') {
        return [version]$Matches[1]
    }
    return $null
}

function Install-Tool {
    param([string]$Id, [string]$Scope)
    if (-not $script:WingetAvailable -or $SkipInstall) { return $false }
    $baseArgs = @('install', '--id', $Id, '-e', '--source', 'winget', '--silent',
        '--disable-interactivity', '--accept-package-agreements', '--accept-source-agreements')
    if ($WhatIfInstall) {
        $cmdLine = "winget " + (($baseArgs + @('--scope', $Scope)) -join ' ')
        Log 'INFO' ("WHATIF: would run: {0}" -f $cmdLine)
        return $false
    }
    $r = Invoke-Native -Exe 'winget' -CmdArgs ($baseArgs + @('--scope', $Scope))
    # winget -1978335189 = "no applicable upgrade / already installed" = success.
    $success = ($r.Code -eq 0) -or ($r.Code -eq -1978335189)
    if (-not $success -and $Scope -eq 'machine') {
        Log 'WARN' ("machine-scope install of {0} failed (code {1}) -- retrying with --scope user" -f $Id, $r.Code)
        $r2 = Invoke-Native -Exe 'winget' -CmdArgs ($baseArgs + @('--scope', 'user'))
        $success = ($r2.Code -eq 0) -or ($r2.Code -eq -1978335189)
        $r = $r2
    }
    if ($success) {
        Log 'INFO' ("winget install {0} -> code {1} (0 or -1978335189 = already-satisfied, both success)" -f $Id, $r.Code)
    } else {
        Log 'WARN' ("winget install {0} failed -> code {1}: {2}" -f $Id, $r.Code, $r.Out)
    }
    return $success
}

function Test-SettingsJson {
    # READ-ONLY validation of the committed .claude\settings.json: Get-Content +
    # ConvertFrom-Json (discard) + conflict-marker scan + SHA256. NEVER writes,
    # reformats, or round-trips this path.
    param([string]$Path)
    $result = [pscustomobject]@{ Exists = $false; Valid = $false; Hash = ''; Reason = '' }
    if (-not (Test-Path -LiteralPath $Path)) {
        $claudeDir = Split-Path -Parent $Path
        if (Test-Path -LiteralPath $claudeDir -PathType Leaf) {
            $result.Reason = ('.claude exists but is a FILE not a directory ({0}) -- settings.json cannot exist under it' -f $claudeDir)
        } elseif (-not (Test-Path -LiteralPath $claudeDir -PathType Container)) {
            $result.Reason = ('.claude directory missing ({0})' -f $claudeDir)
        } else {
            $result.Reason = 'settings.json missing but .claude directory is present'
        }
        return $result
    }
    $result.Exists = $true
    try {
        $result.Hash = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
    } catch {
        $result.Reason = "hash failed: $($_.Exception.Message)"
        return $result
    }
    $conflict = Select-String -LiteralPath $Path -Pattern '^(<<<<<<<|=======|>>>>>>>)' -ErrorAction SilentlyContinue
    if ($conflict) {
        $result.Reason = 'unresolved merge conflict markers present'
        return $result
    }
    try {
        $raw = Get-Content -LiteralPath $Path -Raw
        $null = $raw | ConvertFrom-Json
        $result.Valid = $true
    } catch {
        $result.Reason = "JSON parse error: $($_.Exception.Message)"
    }
    return $result
}

function Test-DevHealth {
    # A port is "answering" if ANY HTTP response comes back -- including a 4xx/5xx,
    # which still proves a server is listening. Only a connection failure (no
    # Response object) counts as down.
    param([int]$Port)
    try {
        $resp = Invoke-WebRequest -Uri ("http://localhost:{0}/" -f $Port) -UseBasicParsing -TimeoutSec 3
        return ($null -ne $resp)
    } catch {
        if ($_.Exception.Response) { return $true }
        return $false
    }
}

function Stop-LaunchedDev {
    # Stops ONLY the process tree this script itself launched (root PID captured from
    # Start-Process), via taskkill /T which walks descendants by parentage. Never
    # targets a PID the script did not launch.
    param([int]$LaunchedPid, [int[]]$Ports)
    try {
        $kill = Invoke-Native -Exe 'taskkill' -CmdArgs @('/PID', ([string]$LaunchedPid), '/T', '/F')
        if (-not $kill.Ok) {
            # taskkill may report the tree already gone; fall back to the root PID only.
            Stop-Process -Id $LaunchedPid -Force -ErrorAction SilentlyContinue
        }
    } catch {
        Log 'WARN' ("Stop-LaunchedDev error: {0}" -f $_.Exception.Message)
    }
    Start-Sleep -Seconds 2
    foreach ($p in $Ports) {
        $still = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
        if ($still) {
            $orphanPid = $still[0].OwningProcess
            $orphanName = 'unknown'
            $op = Get-Process -Id $orphanPid -ErrorAction SilentlyContinue
            if ($op) { $orphanName = $op.ProcessName }
            Log 'WARN' ("port {0} still listening after stop attempt -- possible orphan PID {1} ({2}). Diagnose: tasklist /PID {1} -- if it is a stray node/cmd from this run, stop it: taskkill /PID {1} /T /F" -f $p, $orphanPid, $orphanName)
        }
    }
}

# ---------------------------------------------------------------------------
# STEP 0: preamble -- elevation, PS version, execution policy, memory, disk
# ---------------------------------------------------------------------------
$script:IsAdmin = Test-IsAdmin
Log 'INFO' ("START setup-desktop-windows.ps1 -- IsAdmin={0} PSVersion={1} Edition={2}" -f `
    $script:IsAdmin, $PSVersionTable.PSVersion.ToString(), $PSVersionTable.PSEdition)
Add-Result -Step 'Preamble/Elevation' -Status 'INFO' -Detail ("IsAdmin={0}" -f $script:IsAdmin)

try {
    $execPolicies = (Get-ExecutionPolicy -List | Out-String) -replace "`r?`n", ' | '
    Add-Result -Step 'Preamble/ExecutionPolicy' -Status 'INFO' -Detail $execPolicies.Trim()
} catch {
    Add-Result -Step 'Preamble/ExecutionPolicy' -Status 'WARN' -Detail $_.Exception.Message
}

try {
    $freeMemMB = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1KB)
    Add-Result -Step 'Preamble/FreeMemory' -Status 'INFO' -Detail ("{0} MB free" -f $freeMemMB)
} catch {
    Add-Result -Step 'Preamble/FreeMemory' -Status 'WARN' -Detail $_.Exception.Message
}

try {
    $qualifier = Split-Path -Path $ProjectPath -Qualifier
    $driveLetter = $qualifier.TrimEnd(':')
    $drive = Get-PSDrive -Name $driveLetter -ErrorAction Stop
    $freeGB = [math]::Round($drive.Free / 1GB, 1)
    if ($freeGB -lt 3) {
        Add-Result -Step 'Preamble/DiskFree' -Status 'WARN' -Detail ("only {0} GB free on {1} -- ENOSPC risk during npm install; see maintenance/ora-nightly-disk.ps1" -f $freeGB, $qualifier)
    } else {
        Add-Result -Step 'Preamble/DiskFree' -Status 'PASS' -Detail ("{0} GB free on {1}" -f $freeGB, $qualifier)
    }
} catch {
    Add-Result -Step 'Preamble/DiskFree' -Status 'WARN' -Detail $_.Exception.Message
}

# ---------------------------------------------------------------------------
# STEP 1: winget detect (never a hard fail on its own)
# ---------------------------------------------------------------------------
try {
    $wingetCmd = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $wingetCmd) {
        $candidate = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\winget.exe'
        if (Test-Path -LiteralPath $candidate) {
            Update-SessionPath
            $wingetCmd = Get-Command winget -ErrorAction SilentlyContinue
        }
    }
    if ($wingetCmd) {
        $script:WingetAvailable = $true
        Add-Result -Step 'Winget' -Status 'PASS' -Detail ("found at {0}" -f $wingetCmd.Source)
    } else {
        $script:WingetAvailable = $false
        Add-Result -Step 'Winget' -Status 'WARN' -Detail 'winget not found -- install steps degrade to verify-only + manual instructions. Install "App Installer" from the Microsoft Store, or see github.com/microsoft/winget-cli/releases and docs/MIGRATION_RUNBOOK.md section B1.'
    }
} catch {
    $script:WingetAvailable = $false
    Add-Result -Step 'Winget' -Status 'WARN' -Detail $_.Exception.Message
}

# ---------------------------------------------------------------------------
# STEP 2: Node -- three-way (skip>=20 / install-if-absent / warn-if-old, never silent-upgrade)
# ---------------------------------------------------------------------------
try {
    $nodeCmd = Get-Command node -ErrorAction SilentlyContinue
    if ($nodeCmd) { $script:NodeMajor = Get-NodeMajor }

    if ($script:NodeMajor -and $script:NodeMajor -ge [version]'20.0.0') {
        Add-Result -Step 'Node' -Status 'PASS' -Detail ("Node v{0} satisfies >=20 -- skipping install" -f $script:NodeMajor)
    }
    elseif (-not $nodeCmd) {
        if (-not $SkipInstall -and $script:WingetAvailable) {
            $holder = Get-Process -Name 'node' -ErrorAction SilentlyContinue
            if ($holder) {
                Add-Result -Step 'Node' -Status 'WARN' -Detail 'node.exe is not on PATH but a node process is already running -- skipping install to avoid touching a locked binary. Investigate, then re-run.'
            } else {
                $scope = 'user'
                if ($script:IsAdmin) { $scope = 'machine' }
                $installed = Install-Tool -Id 'OpenJS.NodeJS.LTS' -Scope $scope
                if ($installed) { Update-SessionPath }
                $script:NodeMajor = Get-NodeMajor
                if ($script:NodeMajor -and $script:NodeMajor -ge [version]'20.0.0') {
                    Add-Result -Step 'Node' -Status 'PASS' -Detail ("installed Node v{0} via winget" -f $script:NodeMajor)
                } else {
                    Add-Result -Step 'Node' -Status 'FAIL' -Detail 'Node still unresolved after install attempt -- it may need a new shell or reboot; re-run this script (idempotent). Manual: winget install --id OpenJS.NodeJS.LTS -e'
                }
            }
        } else {
            Add-Result -Step 'Node' -Status 'FAIL' -Detail 'Node not found and cannot auto-install (SkipInstall set, or winget unavailable). Manual: winget install --id OpenJS.NodeJS.LTS -e, or see docs/MIGRATION_RUNBOOK.md section B1.'
        }
    }
    else {
        Add-Result -Step 'Node' -Status 'WARN' -Detail ("Node v{0} present but below 20 -- NOT auto-upgrading (it may be pinned for another app). Manual: winget install --id OpenJS.NodeJS.LTS -e" -f $script:NodeMajor)
    }

    $nodeSources = @(Get-Command node -All -ErrorAction SilentlyContinue)
    if ($nodeSources.Count -gt 1) {
        $list = ($nodeSources | ForEach-Object { $_.Source }) -join ', '
        Add-Result -Step 'Node/Shadowing' -Status 'WARN' -Detail ("multiple node on PATH -- winner: {0}; all: {1}" -f $nodeSources[0].Source, $list)
    }

    $npmCheck = Invoke-Native -Exe 'npm' -CmdArgs @('-v')
    if ($npmCheck.Ok -and $npmCheck.Out.Trim() -match '^\d+\.\d+\.\d+') {
        Add-Result -Step 'npm' -Status 'PASS' -Detail ("npm v{0}" -f $npmCheck.Out.Trim())
    } else {
        Add-Result -Step 'npm' -Status 'WARN' -Detail ("npm -v did not return a clean version: {0}" -f $npmCheck.Out.Trim())
    }

    $archCheck = Invoke-Native -Exe 'node' -CmdArgs @('-p', 'process.arch')
    if ($archCheck.Ok -and (@('x64', 'arm64') -contains $archCheck.Out.Trim())) {
        Add-Result -Step 'Node/Arch' -Status 'PASS' -Detail $archCheck.Out.Trim()
    } else {
        Add-Result -Step 'Node/Arch' -Status 'WARN' -Detail ("unexpected or unreadable arch: {0}" -f $archCheck.Out.Trim())
    }
# The dedicated Node hard-fail gate below is the single source of truth for whether
# Node forces a non-zero exit, so an unexpected error in the probing above is reported
# as a WARN here (not a FAIL) to avoid a FAIL row that would not drive the exit code.
} catch {
    Add-Result -Step 'Node' -Status 'WARN' -Detail ("unexpected error during Node checks: {0}" -f $_.Exception.Message)
}

# Single Node hard-fail gate (runs whether or not the try above threw): Node<20 that
# could not be resolved is the only Node condition that forces a non-zero exit. This is
# the SOLE place Node increments HardFailCount, so a failure is never double-counted.
if (-not $script:NodeMajor -or $script:NodeMajor -lt [version]'20.0.0') {
    $script:HardFailCount++
}

# ---------------------------------------------------------------------------
# STEP 3: Git -- detect by binary, not winget list (misses GitHub Desktop/scoop/WSL/MSI)
# ---------------------------------------------------------------------------
try {
    $gitCmd = Get-Command git -ErrorAction SilentlyContinue
    $gitOk = $false
    $gitVerStr = ''
    if ($gitCmd) {
        $r = Invoke-Native -Exe 'git' -CmdArgs @('--version')
        if ($r.Ok -and $r.Out -match '(\d+\.\d+\.\d+)') {
            $gitVerStr = $Matches[1]
            if ([version]$gitVerStr -ge [version]'2.40.0') { $gitOk = $true }
        }
    }
    if ($gitOk) {
        Add-Result -Step 'Git' -Status 'PASS' -Detail ("git {0} satisfies >=2.40" -f $gitVerStr)
    } else {
        if (-not $SkipInstall -and $script:WingetAvailable) {
            $scope = 'user'
            if ($script:IsAdmin) { $scope = 'machine' }
            $installed = Install-Tool -Id 'Git.Git' -Scope $scope
            if ($installed) { Update-SessionPath }
            $gitCmd2 = Get-Command git -ErrorAction SilentlyContinue
            $r2 = $null
            if ($gitCmd2) { $r2 = Invoke-Native -Exe 'git' -CmdArgs @('--version') }
            if ($r2 -and $r2.Ok -and $r2.Out -match '(\d+\.\d+\.\d+)') {
                Add-Result -Step 'Git' -Status 'PASS' -Detail ("installed git {0} via winget" -f $Matches[1])
            } else {
                Add-Result -Step 'Git' -Status 'WARN' -Detail 'git still unresolved after install attempt -- it may need a new shell or reboot; re-run this script (idempotent). Manual: winget install --id Git.Git -e'
            }
        } else {
            $detail = 'Manual: winget install --id Git.Git -e (git core.longpaths/GCM support needs >=2.40)'
            if (-not $gitCmd) { $detail = 'git not found. ' + $detail } else { $detail = ("git {0} is older than 2.40. " -f $gitVerStr) + $detail }
            Add-Result -Step 'Git' -Status 'WARN' -Detail $detail
        }
    }

    $gitSources = @(Get-Command git -All -ErrorAction SilentlyContinue)
    if ($gitSources.Count -gt 1) {
        $list = ($gitSources | ForEach-Object { $_.Source }) -join ', '
        Add-Result -Step 'Git/Shadowing' -Status 'WARN' -Detail ("multiple git on PATH -- winner: {0}; all: {1}" -f $gitSources[0].Source, $list)
    }
} catch {
    Add-Result -Step 'Git' -Status 'WARN' -Detail $_.Exception.Message
}

# ---------------------------------------------------------------------------
# STEP 4: refresh PATH once more before anything that depends on git/node below
# (Update-SessionPath is also called inline right after every install above.)
# ---------------------------------------------------------------------------
Update-SessionPath

# ---------------------------------------------------------------------------
# STEP 5: git config hygiene -- read-before-write, --global (not --system, avoids admin)
# ---------------------------------------------------------------------------
try {
    if (Get-Command git -ErrorAction SilentlyContinue) {
        $lp = Invoke-Native -Exe 'git' -CmdArgs @('config', '--get', 'core.longpaths')
        $lpVal = $lp.Out.Trim()
        if ($lpVal -ne 'true') {
            if ($SkipInstall) {
                Add-Result -Step 'Git/LongPaths(config)' -Status 'INFO' -Detail 'would set git config --global core.longpaths true -- skipped under -SkipInstall (no-write)'
            } else {
                $setLp = Invoke-Native -Exe 'git' -CmdArgs @('config', '--global', 'core.longpaths', 'true')
                if ($setLp.Ok) {
                    Add-Result -Step 'Git/LongPaths(config)' -Status 'PASS' -Detail 'set git config --global core.longpaths true'
                } else {
                    Add-Result -Step 'Git/LongPaths(config)' -Status 'WARN' -Detail ("failed to set core.longpaths: {0}" -f $setLp.Out.Trim())
                }
            }
        } else {
            Add-Result -Step 'Git/LongPaths(config)' -Status 'PASS' -Detail 'core.longpaths already true -- unchanged'
        }

        try {
            $lpe = Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -ErrorAction SilentlyContinue
            $lpeVal = 0
            if ($lpe) { $lpeVal = $lpe.LongPathsEnabled }
            if ($lpeVal -ne 1) {
                if ($SkipInstall) {
                    Add-Result -Step 'Git/LongPaths(registry)' -Status 'INFO' -Detail 'would set HKLM LongPathsEnabled=1 (when elevated) -- skipped under -SkipInstall (no-write)'
                } elseif ($script:IsAdmin) {
                    New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -Value 1 -PropertyType DWord -Force | Out-Null
                    Add-Result -Step 'Git/LongPaths(registry)' -Status 'WARN' -Detail 'set HKLM LongPathsEnabled=1 -- a reboot may be needed for it to fully apply'
                } else {
                    Add-Result -Step 'Git/LongPaths(registry)' -Status 'WARN' -Detail 'HKLM LongPathsEnabled is not 1 and this run is non-admin. Elevated fix: New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1 -PropertyType DWord -Force'
                }
            } else {
                Add-Result -Step 'Git/LongPaths(registry)' -Status 'PASS' -Detail 'HKLM LongPathsEnabled already 1'
            }
        } catch {
            Add-Result -Step 'Git/LongPaths(registry)' -Status 'WARN' -Detail $_.Exception.Message
        }

        $acrlf = Invoke-Native -Exe 'git' -CmdArgs @('config', '--get', 'core.autocrlf')
        $acrlfVal = $acrlf.Out.Trim()
        if ([string]::IsNullOrEmpty($acrlfVal) -or $acrlfVal -eq 'true') {
            if ($SkipInstall) {
                Add-Result -Step 'Git/Autocrlf' -Status 'INFO' -Detail ("would set core.autocrlf false (currently '{0}') -- skipped under -SkipInstall (no-write)" -f $acrlfVal)
            } else {
                $setA = Invoke-Native -Exe 'git' -CmdArgs @('config', '--global', 'core.autocrlf', 'false')
                if ($setA.Ok) {
                    Add-Result -Step 'Git/Autocrlf' -Status 'PASS' -Detail ("set core.autocrlf false (was '{0}')" -f $acrlfVal)
                } else {
                    Add-Result -Step 'Git/Autocrlf' -Status 'WARN' -Detail ("failed to set core.autocrlf: {0}" -f $setA.Out.Trim())
                }
            }
        } else {
            Add-Result -Step 'Git/Autocrlf' -Status 'PASS' -Detail ("core.autocrlf already explicit ('{0}') -- left unchanged" -f $acrlfVal)
        }

        $chSys = Invoke-Native -Exe 'git' -CmdArgs @('config', '--system', '--get', 'credential.helper')
        $chGlob = Invoke-Native -Exe 'git' -CmdArgs @('config', '--global', '--get', 'credential.helper')
        $chVal = $chSys.Out.Trim()
        if ([string]::IsNullOrEmpty($chVal)) { $chVal = $chGlob.Out.Trim() }
        if ([string]::IsNullOrEmpty($chVal)) {
            $gcmCandidates = @(
                (Join-Path $env:ProgramFiles 'Git\mingw64\bin\git-credential-manager.exe'),
                (Join-Path $env:ProgramFiles 'Git\mingw64\libexec\git-core\git-credential-manager-core.exe')
            )
            $gcmFound = $gcmCandidates | Where-Object { Test-Path -LiteralPath $_ }
            if ($gcmFound) {
                if ($SkipInstall) {
                    Add-Result -Step 'Git/CredentialHelper' -Status 'INFO' -Detail 'would set credential.helper manager (GCM binary found) -- skipped under -SkipInstall (no-write)'
                } else {
                    $setC = Invoke-Native -Exe 'git' -CmdArgs @('config', '--global', 'credential.helper', 'manager')
                    if ($setC.Ok) {
                        Add-Result -Step 'Git/CredentialHelper' -Status 'PASS' -Detail 'set credential.helper manager (GCM binary found on disk)'
                    } else {
                        Add-Result -Step 'Git/CredentialHelper' -Status 'WARN' -Detail ("failed to set credential.helper: {0}" -f $setC.Out.Trim())
                    }
                }
            } else {
                Add-Result -Step 'Git/CredentialHelper' -Status 'WARN' -Detail 'no credential.helper configured and no git-credential-manager binary found -- the private ZeOoba clone will prompt or fail. See docs/MIGRATION_RUNBOOK.md auth section. Never embed a PAT.'
            }
        } else {
            Add-Result -Step 'Git/CredentialHelper' -Status 'PASS' -Detail ("credential.helper already set: {0}" -f $chVal)
        }
    } else {
        Add-Result -Step 'Git/ConfigHygiene' -Status 'WARN' -Detail 'git not available -- skipped core.longpaths/autocrlf/credential.helper checks'
    }
} catch {
    Add-Result -Step 'Git/ConfigHygiene' -Status 'WARN' -Detail $_.Exception.Message
}

# ---------------------------------------------------------------------------
# STEP 6: project locate (HARD prereq: dir + package.json must both exist)
# ---------------------------------------------------------------------------
try {
    $pkgPathCheck = Join-Path $ProjectPath 'package.json'
    if (-not (Test-Path -LiteralPath $ProjectPath) -or -not (Test-Path -LiteralPath $pkgPathCheck)) {
        Add-Result -Step 'ProjectLocate' -Status 'FAIL' -Detail ("project not found at '{0}' (or package.json missing there). Manual: git clone https://github.com/ZeOoba/oxford-command-center.git `"{0}`" -- see docs/MIGRATION_RUNBOOK.md section B1. Not auto-cloning." -f $ProjectPath) -Hard $true
    } else {
        $resolved = (Resolve-Path -LiteralPath $ProjectPath).Path
        Add-Result -Step 'ProjectLocate' -Status 'PASS' -Detail ("found at {0}" -f $resolved)
        if ($resolved -match 'OneDrive') {
            Add-Result -Step 'ProjectLocate/OneDrive' -Status 'WARN' -Detail 'project path is under a OneDrive-synced folder -- dehydration can corrupt node_modules mid-session. Prefer a plain-profile path outside OneDrive, or mark it "Always keep on this device".'
        }
        if (Get-Command git -ErrorAction SilentlyContinue) {
            $wt = Invoke-Native -Exe 'git' -CmdArgs @('-C', $resolved, 'rev-parse', '--is-inside-work-tree')
            if (-not ($wt.Ok -and $wt.Out.Trim() -eq 'true')) {
                Add-Result -Step 'ProjectLocate/GitWorkTree' -Status 'WARN' -Detail 'directory is present but is not a git work tree -- not cloning into it or deleting it'
            } else {
                $origin = Invoke-Native -Exe 'git' -CmdArgs @('-C', $resolved, 'remote', 'get-url', 'origin')
                if ($origin.Ok -and $origin.Out -notmatch 'ZeOoba') {
                    Add-Result -Step 'ProjectLocate/Origin' -Status 'WARN' -Detail ("origin does not match the expected ZeOoba owner: {0}" -f $origin.Out.Trim())
                } elseif ($origin.Ok) {
                    Add-Result -Step 'ProjectLocate/Origin' -Status 'PASS' -Detail 'origin matches expected owner'
                }
            }
        }
    }
} catch {
    Add-Result -Step 'ProjectLocate' -Status 'FAIL' -Detail $_.Exception.Message -Hard $true
}

# ---------------------------------------------------------------------------
# STEP 7: .claude\settings.json READ-ONLY guard (invariant: never overwrite a config)
# ---------------------------------------------------------------------------
try {
    $chk = Test-SettingsJson -Path $script:SettingsPath
    if (-not $chk.Exists) {
        Add-Result -Step 'SettingsJson' -Status 'WARN' -Detail ("not found ({0}) at {1}. Restore with: git -C {2} checkout -- .claude/settings.json (cwd-safe; never synthesized by this script)" -f $chk.Reason, $script:SettingsPath, $ProjectPath)
    } elseif (-not $chk.Valid) {
        Add-Result -Step 'SettingsJson' -Status 'FAIL' -Detail ("present but invalid: {0}" -f $chk.Reason) -Hard $true
    } else {
        $script:SettingsHashBefore = $chk.Hash
        Add-Result -Step 'SettingsJson' -Status 'PASS' -Detail ("valid JSON, no conflict markers, sha256 {0}..." -f $chk.Hash.Substring(0, 12))
    }
} catch {
    Add-Result -Step 'SettingsJson' -Status 'FAIL' -Detail $_.Exception.Message -Hard $true
}

# ---------------------------------------------------------------------------
# STEP 8: package.json parse -- read engines.node, discover which scripts exist
# ---------------------------------------------------------------------------
try {
    $pkgPath = Join-Path $ProjectPath 'package.json'
    if (Test-Path -LiteralPath $pkgPath) {
        $pkgRaw = Get-Content -LiteralPath $pkgPath -Raw
        $pkgObj = $pkgRaw | ConvertFrom-Json
        if ($pkgObj.engines -and $pkgObj.engines.node) {
            Add-Result -Step 'PackageJson/Engines' -Status 'INFO' -Detail ("engines.node = {0} (this script's floor is >=20)" -f $pkgObj.engines.node)
        } else {
            Add-Result -Step 'PackageJson/Engines' -Status 'INFO' -Detail 'no engines.node field declared in package.json'
        }
        if ($pkgObj.scripts) {
            $script:PkgScripts = @($pkgObj.scripts.PSObject.Properties.Name)
        }
        $script:HasDevScript = $script:PkgScripts -contains 'dev'
        $script:HasGateScript = $script:PkgScripts -contains 'gate'
        $script:HasEnsureDepsScript = $script:PkgScripts -contains 'ensure-deps'
        Add-Result -Step 'PackageJson/Scripts' -Status 'PASS' -Detail ("scripts detected: {0}" -f ($script:PkgScripts -join ', '))
    } else {
        # Project/package.json absence is already the hard fail recorded in ProjectLocate;
        # record a plain (non-Hard) FAIL row here to avoid double-counting the same fault.
        Add-Result -Step 'PackageJson/Parse' -Status 'FAIL' -Detail 'package.json missing (already reported as a hard failure in ProjectLocate)'
    }
} catch {
    Add-Result -Step 'PackageJson/Parse' -Status 'FAIL' -Detail $_.Exception.Message -Hard $true
}

# ---------------------------------------------------------------------------
# STEP 9: dependencies -- gate the skip on "npm ls" exit code, not folder presence
# ---------------------------------------------------------------------------
try {
    if ($SkipInstall) {
        Add-Result -Step 'Deps' -Status 'WARN' -Detail 'SkipInstall set -- dependency install/verification skipped (verify-only mode)'
    } elseif (-not (Test-Path -LiteralPath $ProjectPath)) {
        Add-Result -Step 'Deps' -Status 'WARN' -Detail 'project path missing -- skipped'
    } else {
        Push-Location -LiteralPath $ProjectPath
        try {
            $lsCheck = Invoke-Native -Exe 'npm' -CmdArgs @('ls', '--depth=0')
            if ($lsCheck.Ok) {
                Add-Result -Step 'Deps' -Status 'PASS' -Detail 'node_modules is consistent (npm ls --depth=0 exit 0) -- skipping install'
            } else {
                if ($script:HasGateScript) {
                    $gate = Invoke-Native -Exe 'npm' -CmdArgs @('run', 'gate')
                    if ($gate.Ok) {
                        $script:GateAlreadyRan = $true
                        Add-Result -Step 'Deps' -Status 'PASS' -Detail 'npm run gate self-healed dependencies via ensure-deps.mjs'
                    } else {
                        $tail = $gate.Out
                        if ($tail.Length -gt 400) { $tail = $tail.Substring(0, 400) }
                        Add-Result -Step 'Deps' -Status 'WARN' -Detail ("npm run gate failed (code {0}): {1}" -f $gate.Code, $tail)
                    }
                } else {
                    $lockPath = Join-Path $ProjectPath 'package-lock.json'
                    $argList = @('install')
                    if (Test-Path -LiteralPath $lockPath) { $argList = @('ci') }
                    $installResult = Invoke-Native -Exe 'npm' -CmdArgs $argList
                    $which = "npm $($argList -join ' ')"
                    if (-not $installResult.Ok -and $argList[0] -eq 'ci' -and $installResult.Out -match 'EUSAGE') {
                        Add-Result -Step 'Deps/npmCi' -Status 'WARN' -Detail 'npm ci returned EUSAGE (lockfile mismatch) -- falling back to npm install'
                        $argList = @('install')
                        $installResult = Invoke-Native -Exe 'npm' -CmdArgs $argList
                        $which = 'npm install (fallback from npm ci EUSAGE)'
                    }
                    if (-not $installResult.Ok -and $installResult.Out -match 'EPERM|EBUSY') {
                        Add-Result -Step 'Deps/Retry' -Status 'WARN' -Detail 'EPERM/EBUSY detected (likely a Defender file lock) -- retrying once'
                        Start-Sleep -Seconds 2
                        $installResult = Invoke-Native -Exe 'npm' -CmdArgs $argList
                    }
                    if ($installResult.Ok) {
                        Add-Result -Step 'Deps' -Status 'PASS' -Detail ("{0} succeeded" -f $which)
                    } else {
                        $detail = ("{0} failed (code {1})" -f $which, $installResult.Code)
                        if ($installResult.Out -match 'SELF_SIGNED_CERT_IN_CHAIN|UNABLE_TO_GET_ISSUER_CERT_LOCALLY') {
                            $detail += ' -- TLS interception suspected. Set NODE_EXTRA_CA_CERTS (or npm cafile) to the corporate root PEM. NEVER set strict-ssl false. See docs/MIGRATION_RUNBOOK.md.'
                        } elseif ($installResult.Out -match 'EPERM|EBUSY') {
                            $detail += ' -- possible Defender file lock persisted after retry. Consider an Add-MpPreference -ExclusionPath for the project (requires admin).'
                        } elseif ($installResult.Out -match 'ETIMEDOUT|ECONNREFUSED|ECONNRESET|ENOTFOUND|EAI_AGAIN|EPROTO') {
                            $detail += ' -- registry unreachable (proxy/network/DNS). Check npm config get registry/proxy/https-proxy; behind a corporate proxy set https-proxy; try npm cache verify. NEVER set strict-ssl false. See docs/MIGRATION_RUNBOOK.md.'
                        } elseif ($installResult.Out -match 'ENOSPC') {
                            $detail += ' -- out of disk space during install (see the Preamble/DiskFree row and maintenance/ora-nightly-disk.ps1).'
                        }
                        $npmTail = $installResult.Out
                        if ($null -ne $npmTail -and $npmTail.Length -gt 400) { $npmTail = $npmTail.Substring($npmTail.Length - 400) }
                        $detail += (' | npm output tail: ' + $npmTail)
                        Add-Result -Step 'Deps' -Status 'WARN' -Detail $detail
                    }
                }
            }
        } finally {
            Pop-Location
        }
    }
} catch {
    Add-Result -Step 'Deps' -Status 'WARN' -Detail $_.Exception.Message
}

# ---------------------------------------------------------------------------
# STEP 10: gate smoke test (exercises ensure-deps.mjs end-to-end if not already run)
# ---------------------------------------------------------------------------
try {
    if ($SkipInstall) {
        Add-Result -Step 'GateSmokeTest' -Status 'WARN' -Detail 'SkipInstall set -- gate smoke test skipped'
    } elseif (-not $script:HasGateScript) {
        Add-Result -Step 'GateSmokeTest' -Status 'INFO' -Detail 'no gate script in package.json -- skipped'
    } elseif ($script:GateAlreadyRan) {
        Add-Result -Step 'GateSmokeTest' -Status 'PASS' -Detail 'already run as part of the Deps step'
    } elseif (-not (Test-Path -LiteralPath $ProjectPath)) {
        Add-Result -Step 'GateSmokeTest' -Status 'WARN' -Detail 'project path missing -- skipped'
    } else {
        Push-Location -LiteralPath $ProjectPath
        try {
            $gate2 = Invoke-Native -Exe 'npm' -CmdArgs @('run', 'gate')
            if ($gate2.Ok) {
                Add-Result -Step 'GateSmokeTest' -Status 'PASS' -Detail 'npm run gate exited 0'
            } else {
                Add-Result -Step 'GateSmokeTest' -Status 'WARN' -Detail ("npm run gate failed (code {0})" -f $gate2.Code)
            }
        } finally {
            Pop-Location
        }
    }
} catch {
    Add-Result -Step 'GateSmokeTest' -Status 'WARN' -Detail $_.Exception.Message
}

# ---------------------------------------------------------------------------
# STEP 11: port pre-flight (report-only -- never kill a foreign holder)
# ---------------------------------------------------------------------------
try {
    $portTargets = @(
        [pscustomobject]@{ Port = $BrainPort; Name = 'Brain' },
        [pscustomobject]@{ Port = $WebPort; Name = 'Web' }
    )
    foreach ($pt in $portTargets) {
        $conns = Get-NetTCPConnection -LocalPort $pt.Port -State Listen -ErrorAction SilentlyContinue
        if ($conns) {
            $owningPid = $conns[0].OwningProcess
            $proc = Get-Process -Id $owningPid -ErrorAction SilentlyContinue
            $pname = 'unknown'
            if ($proc) { $pname = $proc.ProcessName }
            Add-Result -Step ("Port/{0}" -f $pt.Name) -Status 'WARN' -Detail ("port {0} already listening -- PID {1} ({2}). Not killed; -StartDevServer will skip this port." -f $pt.Port, $owningPid, $pname)
            if ($pt.Name -eq 'Brain') { $script:BrainPortBusy = $true } else { $script:WebPortBusy = $true }
        } else {
            Add-Result -Step ("Port/{0}" -f $pt.Name) -Status 'PASS' -Detail ("port {0} free" -f $pt.Port)
        }
    }
} catch {
    Add-Result -Step 'Port' -Status 'WARN' -Detail $_.Exception.Message
}

# ---------------------------------------------------------------------------
# STEP 12: Claude Code -- VERIFY ONLY, never install/upgrade/touch
# ---------------------------------------------------------------------------
try {
    $claudeCmd = Get-Command claude -ErrorAction SilentlyContinue
    $binPath = $null
    if ($claudeCmd) {
        $binPath = $claudeCmd.Source
    } else {
        $nativeCandidate = Join-Path $env:USERPROFILE '.local\bin\claude.exe'
        $npmPrefixResult = Invoke-Native -Exe 'npm' -CmdArgs @('config', 'get', 'prefix')
        $npmShimCandidate = $null
        if ($npmPrefixResult.Ok) {
            $npmShimCandidate = Join-Path $npmPrefixResult.Out.Trim() 'claude.cmd'
        }
        if (Test-Path -LiteralPath $nativeCandidate) {
            $binPath = $nativeCandidate
        } elseif ($npmShimCandidate -and (Test-Path -LiteralPath $npmShimCandidate)) {
            $binPath = $npmShimCandidate
        }
        if ($binPath) {
            Update-SessionPath
            $claudeCmd2 = Get-Command claude -ErrorAction SilentlyContinue
            if ($claudeCmd2) { $binPath = $claudeCmd2.Source }
        }
    }

    if (-not $binPath) {
        Add-Result -Step 'ClaudeCode' -Status 'WARN' -Detail 'claude not found on PATH or in known install locations (~/.local/bin, npm prefix). It is documented as already installed on this box -- verify manually; this script never installs it.'
    } else {
        Add-Result -Step 'ClaudeCode' -Status 'PASS' -Detail ("resolved at {0}" -f $binPath)

        $isShim = $binPath -match '\.(cmd|ps1)$'
        if ($isShim -and -not (Get-Command node -ErrorAction SilentlyContinue)) {
            Add-Result -Step 'ClaudeCode/ShimNeedsNode' -Status 'WARN' -Detail 'claude resolves to an npm shim (.cmd/.ps1) but node is not on PATH -- the shim cannot run until Node is resolved (already the Node hard failure above)'
        } elseif ($isShim -and $script:NodeMajor -and $script:NodeMajor -lt [version]'20.0.0') {
            Add-Result -Step 'ClaudeCode/ShimNeedsNode' -Status 'WARN' -Detail 'claude resolves to an npm shim and Node is below 20 -- the shim may still run, but this also blocks npm run dev'
        }

        $whereOut = Invoke-Native -Exe 'where.exe' -CmdArgs @('claude')
        if ($whereOut.Ok) {
            $claudeSources = @($whereOut.Out -split "`r?`n" | Where-Object { $_ -ne '' })
            if ($claudeSources.Count -gt 1) {
                Add-Result -Step 'ClaudeCode/Shadowing' -Status 'WARN' -Detail ("multiple claude resolutions on PATH: {0}" -f ($claudeSources -join ', '))
            }
        }

        $job = Start-Job -ScriptBlock { param($exe) & $exe --version 2>&1 } -ArgumentList $binPath
        $done = Wait-Job -Job $job -Timeout 20
        if (-not $done) {
            Stop-Job -Job $job -ErrorAction SilentlyContinue
            Add-Result -Step 'ClaudeCode/Version' -Status 'WARN' -Detail 'claude --version did not return within 20s (auto-updater/EDR/proxy can hang it) -- re-run, or check manually'
        } else {
            $verOut = (Receive-Job -Job $job | Out-String).Trim()
            if ($verOut -match '(\d+\.\d+\.\d+)') {
                Add-Result -Step 'ClaudeCode/Version' -Status 'PASS' -Detail ("version {0}" -f $Matches[1])
            } else {
                Add-Result -Step 'ClaudeCode/Version' -Status 'WARN' -Detail ("unexpected output: {0}" -f $verOut)
            }
        }
        Remove-Job -Job $job -Force -ErrorAction SilentlyContinue

        $claudeJsonPath = Join-Path $env:USERPROFILE '.claude.json'
        if (-not (Test-Path -LiteralPath $claudeJsonPath)) {
            Add-Result -Step 'ClaudeCode/Auth' -Status 'WARN' -Detail ("{0} not found -- Claude Code may be unauthenticated. Run 'claude' once interactively to log in (never run 'claude doctor' from this script -- interactive TUI)." -f $claudeJsonPath)
        } else {
            Add-Result -Step 'ClaudeCode/Auth' -Status 'PASS' -Detail 'auth state file present'
        }
    }
} catch {
    Add-Result -Step 'ClaudeCode' -Status 'WARN' -Detail $_.Exception.Message
}

# Re-verify settings.json is byte-identical to Step 7 -- proves this run mutated nothing.
# Done outside the Claude try/catch so a Claude WARN can never skip this integrity check.
try {
    if ($script:SettingsHashBefore -ne '') {
        $chkAfter = Test-SettingsJson -Path $script:SettingsPath
        if ($chkAfter.Hash -eq $script:SettingsHashBefore) {
            Add-Result -Step 'SettingsJson/Unmutated' -Status 'PASS' -Detail 'sha256 hash unchanged since Step 7 -- this run mutated nothing'
        } else {
            Add-Result -Step 'SettingsJson/Unmutated' -Status 'FAIL' -Detail 'sha256 hash CHANGED since Step 7 -- something modified .claude/settings.json during this run' -Hard $true
        }
    }
} catch {
    Add-Result -Step 'SettingsJson/Unmutated' -Status 'WARN' -Detail $_.Exception.Message
}

# ---------------------------------------------------------------------------
# STEP 13: optional dev health check -- ONLY under -StartDevServer, ALWAYS stopped after
# ---------------------------------------------------------------------------
try {
    if (-not $StartDevServer) {
        Add-Result -Step 'DevHealth' -Status 'INFO' -Detail '-StartDevServer not set -- dev server not started (this is the default)'
    } elseif (-not $script:HasDevScript) {
        Add-Result -Step 'DevHealth' -Status 'WARN' -Detail 'no dev script in package.json -- cannot start'
    } elseif (-not (Test-Path -LiteralPath $ProjectPath)) {
        Add-Result -Step 'DevHealth' -Status 'WARN' -Detail 'project path missing -- cannot start'
    } elseif ($script:BrainPortBusy -or $script:WebPortBusy) {
        Add-Result -Step 'DevHealth' -Status 'WARN' -Detail 'skipped -- one or both ports are already occupied by a foreign process (see Port rows above)'
    } else {
        $proc = $null
        try {
            $stdoutLog = Join-Path $env:TEMP 'ora-dev-stdout.log'
            $stderrLog = Join-Path $env:TEMP 'ora-dev-stderr.log'
            Push-Location -LiteralPath $ProjectPath
            try {
                # Launch via cmd.exe so a redirected (UseShellExecute=false) Start-Process
                # can resolve the npm.cmd batch shim; a bare -FilePath 'npm' would fail to
                # start when output is redirected. The captured root PID is cmd.exe; its
                # descendant node processes are stopped as a tree in the finally block.
                $proc = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', 'npm', 'run', 'dev' -PassThru -WindowStyle Hidden `
                    -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog
            } finally {
                Pop-Location
            }
            $deadline = (Get-Date).AddSeconds($HealthTimeoutSec)
            $brainUp = $false
            $webUp = $false
            while ((Get-Date) -lt $deadline -and -not ($brainUp -and $webUp) -and -not $proc.HasExited) {
                if (-not $brainUp) { $brainUp = Test-DevHealth -Port $BrainPort }
                if (-not $webUp) { $webUp = Test-DevHealth -Port $WebPort }
                if (-not ($brainUp -and $webUp)) { Start-Sleep -Seconds 2 }
            }
            if ($brainUp -and $webUp) {
                Add-Result -Step 'DevHealth' -Status 'PASS' -Detail ("Brain :{0} and Web :{1} both responded within {2}s" -f $BrainPort, $WebPort, $HealthTimeoutSec)
            } else {
                $stderrTail = ''
                if (Test-Path -LiteralPath $stderrLog) { $stderrTail = (Get-Content -LiteralPath $stderrLog -Tail 20 | Out-String) }
                $devReason = ("timed out after {0}s" -f $HealthTimeoutSec)
                if ($proc.HasExited) { $devReason = 'dev process exited early before both ports came up' }
                Add-Result -Step 'DevHealth' -Status 'WARN' -Detail ("{0} -- Brain up={1} Web up={2}. stderr tail written to log." -f $devReason, $brainUp, $webUp)
                Log 'WARN' ("dev stderr tail: {0}" -f $stderrTail)
            }
        } finally {
            if ($proc) { Stop-LaunchedDev -LaunchedPid $proc.Id -Ports @($BrainPort, $WebPort) }
        }
    }
} catch {
    Add-Result -Step 'DevHealth' -Status 'WARN' -Detail $_.Exception.Message
}

# ---------------------------------------------------------------------------
# STEP 14: summary table + exit code
# ---------------------------------------------------------------------------
Log 'INFO' '===== SUMMARY ====='
$tableString = $script:Results | Format-Table -Property Step, Status, Detail -AutoSize -Wrap | Out-String
Write-Host $tableString
try { Add-Content -LiteralPath $LogPath -Value $tableString -ErrorAction Stop } catch { }

$passCount = @($script:Results | Where-Object { $_.Status -eq 'PASS' }).Count
$warnCount = @($script:Results | Where-Object { $_.Status -eq 'WARN' }).Count
$failCount = @($script:Results | Where-Object { $_.Status -eq 'FAIL' }).Count
$infoCount = @($script:Results | Where-Object { $_.Status -eq 'INFO' }).Count
Log 'INFO' ("Tally: PASS={0} WARN={1} FAIL={2} INFO={3} HardFailCount={4}" -f $passCount, $warnCount, $failCount, $infoCount, $script:HardFailCount)

if ($script:HardFailCount -gt 0) {
    Log 'FAIL' 'DONE -- exiting 1 (a hard prerequisite is unmet; see FAIL rows above)'
    exit 1
} else {
    Log 'PASS' 'DONE -- exiting 0'
    exit 0
}
