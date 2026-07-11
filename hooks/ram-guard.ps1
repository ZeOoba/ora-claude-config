# ORA RAM guard (aggressive) -- called by ram-watchdog.sh once per 60s.
# Tiers:
#   free >= WARN_MB            -> silent
#   CRIT_MB <= free < WARN_MB  -> warn (offer /solo), no action
#   free < CRIT_MB             -> auto-park the MOST-IDLE other session (idle >= MIN_IDLE),
#                                 else fall back to warn.
# Parking = kill that session's GUI child process (~130 MB). The session FILE persists
# and is fully resumable. Never parks the current session or the Electron shell.
# Emits ONLY a JSON object on stdout (or nothing). Always exits 0.

param([string]$CurrentSid = '')
$ErrorActionPreference = 'SilentlyContinue'

$WARN_MB  = 2048   # warn below this many MB free (retuned 2026-07-09 for the 32 GB box:
                   # was 300 on the 5.7 GB machine; ~24 GB working ceiling, so warn at ~2 GB free)
$CRIT_MB  = 1024   # auto-park below this (was 200 on the 5.7 GB machine)
$MIN_IDLE = 900    # a session must be idle this many seconds to be park-eligible.
                   # Raised 300 -> 900 on 2026-06-11: transcript mtime goes stale during a
                   # long-running tool call, so 300s parked ACTIVELY-WORKING scheduled runs
                   # mid-flight (killed the 6/11 setup-audit digest + the 6/09 skill-text run).

if (-not $CurrentSid) { $CurrentSid = $env:CLAUDE_CODE_SESSION_ID }

$free = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1024)
if ($free -ge $WARN_MB) { exit 0 }

function Emit($obj) { [Console]::Out.Write(($obj | ConvertTo-Json -Compress -Depth 6)) }
function WarnObj($mb) {
  @{
    systemMessage      = "Low RAM: $mb MB free. Type /solo to move THIS session to a lean CLI (other sessions keep running), or /heavy."
    hookSpecificOutput = @{ hookEventName = 'PostToolUse'; additionalContext = "System RAM is low ($mb MB free). Proactively tell Gabriel and offer to run /solo or /heavy. Do not run any command without his confirmation." }
  }
}

# Warn tier, or critical-but-can't-identify-self (refuse to park blindly) -> warn only
if ($free -ge $CRIT_MB -or -not $CurrentSid) { Emit (WarnObj $free); exit 0 }

# CRITICAL tier: find the most-idle OTHER session by transcript mtime
$now = [DateTimeOffset]::Now.ToUnixTimeSeconds()
$projects = Join-Path $env:USERPROFILE '.claude\projects'
$cands = @()
Get-CimInstance Win32_Process -Filter "Name='claude.exe'" | ForEach-Object {
  $cl = $_.CommandLine
  if ($cl -and $cl -match 'claude-code' -and $cl -match '--resume ([0-9a-f-]{36})') {
    $sid = $matches[1]
    if ($sid -ne $CurrentSid) {
      $j = Get-ChildItem $projects -Recurse -Filter "$sid.jsonl" -ErrorAction SilentlyContinue | Select-Object -First 1
      if ($j) {
        $idle = $now - ([DateTimeOffset]$j.LastWriteTime).ToUnixTimeSeconds()
        $cands += [PSCustomObject]@{ ProcId = $_.ProcessId; Sid = $sid; Idle = $idle }
      }
    }
  }
}

$victim = $cands | Where-Object { $_.Idle -ge $MIN_IDLE } | Sort-Object Idle -Descending | Select-Object -First 1
if ($victim) {
  $p  = Get-Process -Id $victim.ProcId -ErrorAction SilentlyContinue
  $mb = if ($p) { [math]::Round($p.WorkingSet64 / 1MB) } else { 0 }
  # Tree-kill: Stop-Process only kills the top PID, orphaning any cmd.exe/npx/node
  # MCP-server descendants (confirmed 2026-07-10: 32 orphaned desktop-commander
  # pairs found hanging off parked/idle sessions). taskkill /T recurses.
  & taskkill.exe /PID $victim.ProcId /T /F 2>$null | Out-Null
  $short = $victim.Sid.Substring(0, 8)
  $im    = [math]::Round($victim.Idle / 60)
  Emit @{
    systemMessage      = "RAM critical ($free MB free). Auto-parked idle session $short (idle ${im}m, ~$mb MB freed). It is saved -- reopen it anytime to resume."
    hookSpecificOutput = @{ hookEventName = 'PostToolUse'; additionalContext = "RAM was critical; auto-parked the most-idle background session $short (freed ~$mb MB). Its session file persists and is fully resumable. Briefly tell Gabriel this happened; if RAM is still low, offer /solo for THIS session." }
  }
}
else {
  Emit (WarnObj $free)
}
exit 0
