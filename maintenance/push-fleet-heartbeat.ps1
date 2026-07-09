# ORA Fleet Heartbeat Push -- local pulse leg of the EXTERNAL cross-fleet dead-man (v1.0 2026-07-09)
# ----------------------------------------------------------------------------------
# WHY: Task 6 (DEADMAN_APPROACH=GITHUB-ACTION, Gabriel-ratified 2026-07-09). The
# GitHub Action .github/workflows/fleet-deadman.yml checks the COMMITTED copy of
# maintenance/_state/fleet-heartbeat.json daily at 13:00 UTC and alarms if it is
# >24h stale. Something on THIS machine must therefore refresh + push the heartbeat
# daily. No automated ~/.claude push existed when this was built (verified
# 2026-07-09: commits to ZeOoba/ora-claude-config are manual/per-session) -- this
# script IS that missing pulse, deliberately narrow:
#   1) run maintenance/emit-fleet-heartbeat.py (fresh counts + hashes)
#   2) commit ONLY maintenance/_state/fleet-heartbeat.json (git commit --only --
#      never add -A; another session's staged/dirty work must never ride along)
#   3) git push origin main
# Runs from WINDOWS Task Scheduler (outside both Claude fleets, like
# fleet-deadman.ps1) so it keeps pulsing even if the fleets are dark -- and when
# the whole MACHINE is dark, the pulse stops and the GitHub Action alarms. That
# is the dead-man working as designed.
#
# Fail-OPEN: any internal error -> log + exit 0 (never block; a missed pulse is
# exactly what the external monitor exists to catch). ASCII-only (PS 5.1 reads
# non-BOM as ANSI).
#
# Install (run once -- NOT auto-installed; needs Gabriel's ratification, choose
# 07:30 local so both winter and summer land before the 13:00 UTC check):
#   schtasks /Create /TN "ORA Fleet Heartbeat Push" /SC DAILY /ST 07:30 /F `
#     /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"C:\Users\Owner\.claude\maintenance\push-fleet-heartbeat.ps1\""

$repo    = Join-Path $env:USERPROFILE '.claude'
$hbRel   = 'maintenance/_state/fleet-heartbeat.json'
$emitter = Join-Path $repo 'maintenance\emit-fleet-heartbeat.py'
$log     = Join-Path $repo 'maintenance\push-fleet-heartbeat.log'

function Log($m) { "$([DateTime]::UtcNow.ToString('s'))Z  $m" | Out-File -FilePath $log -Append -Encoding utf8 }

try {
    # 1) Refresh the heartbeat (full interpreter path first -- scheduled sessions
    #    may not have python on PATH; bare python as fallback).
    $py = 'C:\Users\Owner\AppData\Local\Programs\Python\Python313\python.exe'
    if (-not (Test-Path $py)) { $py = 'python' }
    & $py $emitter 2>&1 | ForEach-Object { Log ("emit: " + $_) }
    if ($LASTEXITCODE -ne 0) { Log 'emit FAILED - pushing the previous heartbeat unchanged (Action will alarm if this persists)' }

    # 2) Commit ONLY the heartbeat path. --only scopes the commit to the pathspec
    #    even if other work is staged (shared single-writer checkout: other
    #    sessions' hunks must never ride along).
    $changed = git -C $repo status --porcelain -- $hbRel
    if (-not $changed) { Log 'no heartbeat change - nothing to commit'; exit 0 }
    git -C $repo add -- $hbRel 2>&1 | ForEach-Object { Log ("add: " + $_) }
    $msg = 'chore(deadman): fleet-heartbeat refresh ' + [DateTime]::UtcNow.ToString('yyyy-MM-dd')
    git -C $repo commit --only -m $msg -- $hbRel 2>&1 | ForEach-Object { Log ("commit: " + $_) }
    if ($LASTEXITCODE -ne 0) { Log 'commit FAILED (fail-open, no push)'; exit 0 }

    # 3) Push. NO rebase/reset fallback here ever -- this is a shared dirty
    #    checkout (single-writer doctrine). If the remote is ahead, log and let
    #    the next manual session reconcile; the commit is safe locally.
    git -C $repo push origin main 2>&1 | ForEach-Object { Log ("push: " + $_) }
    if ($LASTEXITCODE -ne 0) { Log 'push FAILED - heartbeat NOT on GitHub; Action alarms if stale >24h (by design)' }
    else { Log 'OK - heartbeat pushed' }
    exit 0
}
catch {
    Log ('ERROR (fail-open): ' + $_.Exception.Message)
    exit 0
}
