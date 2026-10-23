# Shared harness for test-send-contract-legacy.ps1 and test-send-contract-keyed.ps1.
# Dot-sourced only. It is not named test-*.ps1, so no runner executes it on its own.
#
# Every case runs send-via-outlook.ps1 as a CHILD PROCESS with -WhatIf. With
# ORA_SEND_SIMULATE set, the send job runs a scripted fake instead of Outlook COM;
# without it, the script stops at its DRY RUN line. Either way no Outlook object is
# created and no mail can leave. ORA_SEND_LOG_PATH points each case at its own temp
# log, and ORA_SEND_SKIP_PREFLIGHT=1 makes the result independent of whether a real
# Outlook is open, busy or on a wizard. All of these seams are honored ONLY under -WhatIf.
$ErrorActionPreference = "Stop"
$script:Pass = 0
$script:Fail = 0
$Target = Join-Path $PSScriptRoot "send-via-outlook.ps1"
if (-not (Test-Path $Target)) { Write-Host "FATAL: $Target not found"; exit 1 }
$Work = Join-Path ([System.IO.Path]::GetTempPath()) ("send-contract-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Path $Work -Force | Out-Null
$To = "ggoldberg@oxfordra.net"
$Keyed = @("-DedupTaskId", "ora-test-task", "-DedupPeriodKey", "2026-10-18")
# Each suite run gets its own dedup lock name, so a suite never contends with a real fire's production lock.
$script:MutexSuffix = [guid]::NewGuid().ToString("N").Substring(0, 12)
$script:SeamVars = @("ORA_SEND_LOG_PATH", "ORA_SEND_SKIP_PREFLIGHT", "ORA_SEND_FORCE_PREFLIGHT_STUCK", "ORA_SEND_SIMULATE", "ORA_SEND_TIMEOUT_SEC", "ORA_SEND_RETRY_DELAY_SEC", "ORA_SEND_GATE_PAUSE_MS", "ORA_SEND_LOCK_WAIT_MS", "ORA_SEND_MUTEX_SUFFIX")

function Get-TestSubjectHash {
    # Must stay byte-identical in behavior to Get-SubjectHash in send-via-outlook.ps1.
    param([string]$Text)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { $bytes = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Text)) } finally { $sha.Dispose() }
    return (-join ($bytes | ForEach-Object { $_.ToString('x2') })).Substring(0, 16)
}

function New-TestLog {
    param([string[]]$Seed = @())
    $p = Join-Path $Work ("log-" + [guid]::NewGuid().ToString("N").Substring(0, 8) + ".txt")
    if ($Seed.Count -gt 0) { Set-Content -LiteralPath $p -Value $Seed -Encoding UTF8 }
    return $p
}

function Get-Stamp {
    param([int]$MinutesAgo)
    return (Get-Date).AddMinutes(-$MinutesAgo).ToString("yyyy-MM-ddTHH:mm:sszzz")
}

function Set-Seams {
    param([string]$Log, [string]$Sim)
    [Environment]::SetEnvironmentVariable("ORA_SEND_LOG_PATH", $Log)
    [Environment]::SetEnvironmentVariable("ORA_SEND_SKIP_PREFLIGHT", "1")
    [Environment]::SetEnvironmentVariable("ORA_SEND_SIMULATE", $(if ($Sim) { $Sim } else { $null }))
    [Environment]::SetEnvironmentVariable("ORA_SEND_TIMEOUT_SEC", "6")
    [Environment]::SetEnvironmentVariable("ORA_SEND_RETRY_DELAY_SEC", "0")
    [Environment]::SetEnvironmentVariable("ORA_SEND_MUTEX_SUFFIX", $script:MutexSuffix)
}

function Clear-Seams {
    foreach ($v in $script:SeamVars) { [Environment]::SetEnvironmentVariable($v, $null) }
}

function Invoke-Send {
    param([string]$Log, [string]$Sim, [string[]]$ScriptArgs, [switch]$OutlookStuck)
    Set-Seams -Log $Log -Sim $Sim
    # -OutlookStuck: the preflight behaves as if Outlook were busy/on a wizard (exit 3 unless the run is suppressed first).
    if ($OutlookStuck) { [Environment]::SetEnvironmentVariable("ORA_SEND_FORCE_PREFLIGHT_STUCK", "1") }
    # EAP must drop to Continue: with "Stop", a child's stderr captured via 2>&1 becomes a
    # terminating error and kills the harness on the first ERROR-path case (the same trap
    # send-via-outlook.ps1 documents around its check_external_send.py call).
    $prevEAP = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $all = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $Target) + $ScriptArgs + @("-WhatIf")
        $out = & powershell @all 2>&1 | Out-String -Width 4096
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEAP
        Clear-Seams
    }
    # A case may deliberately hold the log locked (fail-closed tests); an unreadable log reads as "".
    $text = ""
    try { if (Test-Path -LiteralPath $Log) { $text = Get-Content -LiteralPath $Log -Raw -Encoding UTF8 } } catch { $text = "" }
    return @{ Code = $code; Log = $text; Out = $out }
}

function Get-Count {
    param([string]$Text, [string]$Pattern)
    return ([regex]::Matches([string]$Text, $Pattern)).Count
}

function Check {
    param([string]$Name, [bool]$Cond, $Result = $null)
    if ($Cond) { Write-Host ("  PASS  " + $Name); $script:Pass++; return }
    $detail = ""
    if ($Result) {
        $flat = ([string]$Result.Log -replace "`r?`n", " | ")
        if ($flat.Length -gt 400) { $flat = $flat.Substring(0, 400) + "..." }
        $detail = " -- exit $($Result.Code); log: $flat"
    }
    Write-Host ("  FAIL  " + $Name + $detail)
    $script:Fail++
}

function Complete-Suite {
    Remove-Item $Work -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "`n$script:Pass passed, $script:Fail failed"
    if ($script:Fail -gt 0) { exit 1 }
    exit 0
}
