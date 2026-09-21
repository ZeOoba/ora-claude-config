# Tests for stuck-session-watchdog-lib.ps1's Get-KillCandidates (TDD, 2026-07-15).
# Pure PowerShell against synthetic fixtures -- never touches a real process. Same
# PASS/FAIL-and-exit-code convention as the Python test suites in this codebase.

. (Join-Path $PSScriptRoot 'stuck-session-watchdog-lib.ps1')

$script:failures = @()

function Check($label, [bool]$cond) {
    if ($cond) { Write-Output "PASS  $label" }
    else { Write-Output "FAIL  $label"; $script:failures += $label }
}

function LongCmd($extra) {
    # Simulate a real scheduled-task command line: long, with --allowedTools etc.
    # Base padding alone exceeds the 200-char floor; $extra appends flags like --resume=.
    ("claude.exe --output-format stream-json --allowedTools Task,Glob,Grep,Read,Edit,Write," +
     "TaskCreate,TaskUpdate,TaskGet,TaskList,TaskStop,WebSearch,Skill,AskUserQuestion,ToolSearch " +
     "--disallowedTools Bash,NotebookEdit,REPL,JavaScript,WebFetch --setting-sources=user " +
     "--permission-mode bypassPermissions " + $extra)
}

$Now = Get-Date '2026-07-15T14:00:00'

# 1. THE POINT: a scheduled-task session (no --resume, long cmdline) past the threshold -> candidate.
$procs = @(
    [PSCustomObject]@{ ProcessId = 111; CommandLine = LongCmd ''; CreationDate = $Now.AddMinutes(-100) }
)
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90
Check "stuck scheduled-task session past threshold -> candidate" ($result.Count -eq 1 -and $result[0].ProcessId -eq 111)

# 2. Same shape but UNDER the threshold -> not a candidate.
$procs = @(
    [PSCustomObject]@{ ProcessId = 222; CommandLine = LongCmd ''; CreationDate = $Now.AddMinutes(-30) }
)
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90
Check "young scheduled-task session -> not a candidate" ($result.Count -eq 0)

# 3. HARD SAFETY LINE: an interactive resumed session, even VERY old, is NEVER a candidate.
$procs = @(
    [PSCustomObject]@{ ProcessId = 333; CommandLine = (LongCmd '--resume=de576307-980f-43fd-b5c4-4e7b76c361e2'); CreationDate = $Now.AddMinutes(-1000) }
)
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90
Check "resumed interactive session, 1000 min old -> NEVER a candidate" ($result.Count -eq 0)

# 4. The bare desktop-app shell (short cmdline, no flags) -> never a candidate, any age.
$procs = @(
    [PSCustomObject]@{ ProcessId = 444; CommandLine = 'C:\Users\Owner\AppData\Roaming\Claude\claude-code\2.1.209\claude.exe'; CreationDate = $Now.AddMinutes(-2000) }
)
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90
Check "bare desktop-app shell -> never a candidate" ($result.Count -eq 0)

# 5. Boundary: age exactly AT the threshold -> NOT yet a candidate (strictly-greater-than).
$procs = @(
    [PSCustomObject]@{ ProcessId = 555; CommandLine = LongCmd ''; CreationDate = $Now.AddMinutes(-90) }
)
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90
Check "age exactly at threshold -> not yet a candidate" ($result.Count -eq 0)

# 6. Boundary: one minute past the threshold -> a candidate.
$procs = @(
    [PSCustomObject]@{ ProcessId = 666; CommandLine = LongCmd ''; CreationDate = $Now.AddMinutes(-91) }
)
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90
Check "one minute past threshold -> candidate" ($result.Count -eq 1)

# 7. Mixed batch: only the genuine stuck scheduled-task sessions come back, nothing else.
$procs = @(
    [PSCustomObject]@{ ProcessId = 1; CommandLine = 'C:\Users\Owner\AppData\Roaming\Claude\claude-code\2.1.209\claude.exe'; CreationDate = $Now.AddMinutes(-5000) }  # desktop app
    [PSCustomObject]@{ ProcessId = 2; CommandLine = (LongCmd '--resume=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'); CreationDate = $Now.AddMinutes(-500) }  # interactive, old
    [PSCustomObject]@{ ProcessId = 3; CommandLine = LongCmd ''; CreationDate = $Now.AddMinutes(-10) }   # scheduled task, young
    [PSCustomObject]@{ ProcessId = 4; CommandLine = LongCmd ''; CreationDate = $Now.AddMinutes(-95) }   # scheduled task, STUCK
    [PSCustomObject]@{ ProcessId = 5; CommandLine = LongCmd ''; CreationDate = $Now.AddMinutes(-200) }  # scheduled task, STUCK
)
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90
$ids = $result.ProcessId | Sort-Object
Check "mixed batch: exactly PIDs 4,5 flagged" (($ids -join ',') -eq '4,5')

# 8. Null/missing CommandLine (defensive -- a malformed CIM record) -> skipped, not an error.
$procs = @(
    [PSCustomObject]@{ ProcessId = 777; CommandLine = $null; CreationDate = $Now.AddMinutes(-500) }
)
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90
Check "null CommandLine -> skipped, no crash" ($result.Count -eq 0)

# 9. Empty process list -> empty result, no error.
$result = Get-KillCandidates -Procs @() -Now $Now -ThresholdMinutes 90
Check "empty process list -> empty result" ($result.Count -eq 0)

# ---------------------------------------------------------------------------
# 10-15 added 2026-08-05. THE BUG THIS SUITE MISSED FOR THREE WEEKS.
# Electron runs its OWN child processes (renderer, GPU, utility) as claude.exe
# too. They have long command lines, carry no --resume=, and are long-lived BY
# DESIGN -- so exclusions 1 and 2 let every one of them through and the watchdog
# culled them every ~2h. Forensics 2026-08-05 over stuck-session-watchdog.log,
# cross-referenced against the app's own [process-memory] PID->role telemetry:
#   391 electron_utility, 155 electron_renderer, 88 electron_gpu, 4 electron_main
# killed. The renderer is the process the scheduler needs to attach a dispatch:
# with one present, 74 of 76 dispatches confirmed; with none, 0 of 53 did. This
# watchdog was the single largest cause of the fleet's phantom-dispatch rate.
# Command lines below are copied from the LIVE process table, not invented.
# ---------------------------------------------------------------------------
$pkg = '"C:\Program Files\WindowsApps\Claude_1.25927.0.0_x64__pzs8sxrjxfjjc\Claude.exe"'
function ElectronChild($type) {
    # Real shape: quoted package path + --type= + the usual mojo/field-trial handles.
    ("$pkg --type=$type --user-data-dir=""C:\Users\Owner\AppData\Roaming\Claude"" " +
     "--field-trial-handle=2308,i,10743404793281416549,7166071214620440086,262144 " +
     "--variations-seed-version --mojo-platform-channel-handle=2312 /prefetch:1")
}

# 10. THE REGRESSION: the renderer. Long-lived, long cmdline, no --resume.
$procs = @(
    [PSCustomObject]@{ ProcessId = 8324; CommandLine = (ElectronChild 'renderer'); CreationDate = $Now.AddMinutes(-600) }
)
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90
Check "electron RENDERER, 10h old -> NEVER a candidate (killing it kills the fleet)" ($result.Count -eq 0)

# 11. GPU process.
$procs = @(
    [PSCustomObject]@{ ProcessId = 24852; CommandLine = (ElectronChild 'gpu-process'); CreationDate = $Now.AddMinutes(-600) }
)
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90
Check "electron GPU process -> never a candidate" ($result.Count -eq 0)

# 12. Utility processes (the largest killed cohort, 391).
$procs = @(
    [PSCustomObject]@{ ProcessId = 38588; CommandLine = (ElectronChild 'utility'); CreationDate = $Now.AddMinutes(-600) }
)
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90
Check "electron UTILITY process -> never a candidate" ($result.Count -eq 0)

# 13. Second net: a desktop-app process from the WindowsApps package with NO --type=
#     (belt-and-braces -- if Electron ever drops the flag, the package path still holds).
$procs = @(
    [PSCustomObject]@{ ProcessId = 9999; CommandLine = ($pkg + ' --some-future-flag ' + (LongCmd '')); CreationDate = $Now.AddMinutes(-600) }
)
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90
Check "any WindowsApps\Claude_ package process -> never a candidate" ($result.Count -eq 0)

# 14. THE FIX MUST NOT NEUTER THE WATCHDOG: a real stuck CLI task session, full
#     path as it actually appears live, still gets flagged.
$realSession = ('C:\Users\Owner\AppData\Roaming\Claude\claude-code\2.1.221\claude.exe ' + (LongCmd ''))
$procs = @(
    [PSCustomObject]@{ ProcessId = 34012; CommandLine = $realSession; CreationDate = $Now.AddMinutes(-120) }
)
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90
Check "real stuck claude-code task session STILL a candidate (fix must not neuter)" ($result.Count -eq 1 -and $result[0].ProcessId -eq 34012)

# 15. Realistic mixed batch: app internals + a resumed conversation + one genuine
#     stuck session. Exactly one kill.
$procs = @(
    [PSCustomObject]@{ ProcessId = 8324;  CommandLine = (ElectronChild 'renderer');    CreationDate = $Now.AddMinutes(-600) }
    [PSCustomObject]@{ ProcessId = 24852; CommandLine = (ElectronChild 'gpu-process'); CreationDate = $Now.AddMinutes(-600) }
    [PSCustomObject]@{ ProcessId = 38588; CommandLine = (ElectronChild 'utility');     CreationDate = $Now.AddMinutes(-600) }
    [PSCustomObject]@{ ProcessId = 40632; CommandLine = ($realSession + ' --resume=de576307-980f-43fd-b5c4-4e7b76c361e2'); CreationDate = $Now.AddMinutes(-900) }
    [PSCustomObject]@{ ProcessId = 34012; CommandLine = $realSession; CreationDate = $Now.AddMinutes(-120) }
)
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90
Check "live-shaped batch: ONLY the stuck task session (34012) is flagged" (($result.ProcessId -join ',') -eq '34012')

# ---------------------------------------------------------------------------
# 16-34 added 2026-09-21. THE SECOND BUG: interactive Code-tab sessions.
# Desktop-launched sessions (interactive AND scheduled) are ALL claude.exe children of the
# desktop app with identical flags (stream-json, --permission-prompt-tool stdio, an
# --allowedTools list); a FRESH interactive session carries no --resume=, so the flag
# exclusions passed it straight to the age test. Live evidence: a -WhatIf run flagged a
# 112-min-old interactive session (PID 12928) under the old rules, and the 14:05 run on
# 2026-09-21 killed a 114.5-min-old session (its kind cannot be verified after the fact).
# Whether this watchdog also kills the Mirror Deploy task is NOT established.
# Command-line flags CANNOT separate the two, so the
# discriminator is the session's own identity: ~/.claude/sessions/<pid>.json ->
# hostSessionId -> Desktop session record, whose `scheduledTaskId` exists ONLY on scheduled
# sessions. Get-KillCandidates takes that as -SessionInfo (pid -> {Resolved, ScheduledTaskId,
# ScheduledRunContinued}); anything not positively identified as a scheduled session is
# spared (fail SAFE).
# ---------------------------------------------------------------------------
function Info($resolved, $taskId, $continued = $false) {
    [PSCustomObject]@{ Resolved = $resolved; ScheduledTaskId = $taskId; ScheduledRunContinued = $continued }
}
$fresh = ('C:\Users\Owner\AppData\Roaming\Claude\claude-code\2.1.275\claude.exe ' + (LongCmd '--permission-prompt-tool stdio --input-format stream-json'))

# 16. THE REGRESSION: a fresh interactive session (no --resume=), 114 min old -> NEVER a candidate.
$procs = @([PSCustomObject]@{ ProcessId = 12928; CommandLine = $fresh; CreationDate = $Now.AddMinutes(-114) })
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90 -SessionInfo @{ 12928 = (Info $true $null) }
Check "fresh INTERACTIVE session, 114 min -> never a candidate" ($result.Count -eq 0)

# 17. THE FIX MUST NOT NEUTER THE WATCHDOG: a resolved scheduled-task session past the threshold is still flagged.
$procs = @([PSCustomObject]@{ ProcessId = 900; CommandLine = $fresh; CreationDate = $Now.AddMinutes(-120) })
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90 -SessionInfo @{ 900 = (Info $true 'ora-am-brief') }
Check "resolved SCHEDULED session past threshold -> still a candidate" ($result.Count -eq 1 -and $result[0].ProcessId -eq 900)

# 18. A scheduled session the user took over (scheduledRunContinued) is interactive now -> spared.
$procs = @([PSCustomObject]@{ ProcessId = 901; CommandLine = $fresh; CreationDate = $Now.AddMinutes(-300) })
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90 -SessionInfo @{ 901 = (Info $true 'ora-am-brief' $true) }
Check "scheduled session CONTINUED by the user -> never a candidate" ($result.Count -eq 0)

# 19. Unresolvable (no registry / PID reuse / no host record) -> spared, and it must be REPORTED, not silent.
$procs = @([PSCustomObject]@{ ProcessId = 902; CommandLine = $fresh; CreationDate = $Now.AddMinutes(-300) })
$skipped = New-Object System.Collections.ArrayList
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90 -SessionInfo @{ 902 = (Info $false $null) } -Skipped $skipped
Check "UNRESOLVED session -> never a candidate (fail safe)" ($result.Count -eq 0)
Check "unresolved session is reported in -Skipped as 'unresolved'" ($skipped.Count -eq 1 -and $skipped[0].ProcessId -eq 902 -and $skipped[0].Reason -eq 'unresolved')

# 20. A PID with no entry in the map at all is treated as unresolved, not as "no info -> legacy kill".
$procs = @([PSCustomObject]@{ ProcessId = 903; CommandLine = $fresh; CreationDate = $Now.AddMinutes(-300) })
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90 -SessionInfo @{}
Check "PID absent from -SessionInfo map -> never a candidate" ($result.Count -eq 0)

# 21. Skipped-interactive is reported with reason 'interactive'; young sessions are not reported at all.
$procs = @(
    [PSCustomObject]@{ ProcessId = 12928; CommandLine = $fresh; CreationDate = $Now.AddMinutes(-114) }
    [PSCustomObject]@{ ProcessId = 27184; CommandLine = $fresh; CreationDate = $Now.AddMinutes(-1) }
)
$skipped = New-Object System.Collections.ArrayList
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90 -SessionInfo @{ 12928 = (Info $true $null); 27184 = (Info $true $null) } -Skipped $skipped
Check "interactive skip reported as 'interactive' (old one only)" ($skipped.Count -eq 1 -and $skipped[0].ProcessId -eq 12928 -and $skipped[0].Reason -eq 'interactive')

# 22. Live-shaped mixed batch WITH session info: exactly the stuck scheduled session dies.
$procs = @(
    [PSCustomObject]@{ ProcessId = 8324;  CommandLine = (ElectronChild 'renderer'); CreationDate = $Now.AddMinutes(-600) }   # app internals
    [PSCustomObject]@{ ProcessId = 40632; CommandLine = ($fresh + ' --resume=de576307-980f-43fd-b5c4-4e7b76c361e2'); CreationDate = $Now.AddMinutes(-900) }  # resumed
    [PSCustomObject]@{ ProcessId = 12928; CommandLine = $fresh; CreationDate = $Now.AddMinutes(-114) }   # fresh interactive
    [PSCustomObject]@{ ProcessId = 903;   CommandLine = $fresh; CreationDate = $Now.AddMinutes(-200) }   # unresolvable
    [PSCustomObject]@{ ProcessId = 900;   CommandLine = $fresh; CreationDate = $Now.AddMinutes(-120) }   # STUCK scheduled
)
$map = @{ 40632 = (Info $true 'x'); 12928 = (Info $true $null); 900 = (Info $true 'ora-am-brief') }
$result = Get-KillCandidates -Procs $procs -Now $Now -ThresholdMinutes 90 -SessionInfo $map
Check "mixed batch with session info: ONLY the stuck scheduled session (900)" (($result.ProcessId -join ',') -eq '900')

# --- Get-SessionInfoMap: the I/O half, tested against a temp-dir fixture, never a real process ---
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("wd-test-" + [guid]::NewGuid().ToString('N'))
$sessDir = Join-Path $tmp 'sessions'
$hostDir = Join-Path $tmp 'host\acct1\org1'
New-Item -ItemType Directory -Path $sessDir, $hostDir -Force | Out-Null
function WriteJson($path, $obj) { $obj | ConvertTo-Json -Compress | Set-Content -LiteralPath $path -Encoding utf8 }
$created = $Now.AddMinutes(-100)
$ps = $created.ToFileTimeUtc().ToString()
# 1001 = scheduled, 1002 = interactive, 1003 = PID reuse (procStart wrong), 1004 = no host record,
# 1005 = no registry file, 1006 = malformed registry JSON, 1007 = scheduled but continued by the user
WriteJson (Join-Path $sessDir '1001.json') @{ pid = 1001; procStart = $ps; hostSessionId = 'local_aaa' }
WriteJson (Join-Path $hostDir 'local_aaa.json') @{ sessionId = 'local_aaa'; scheduledTaskId = 'ora-am-brief' }
WriteJson (Join-Path $sessDir '1002.json') @{ pid = 1002; procStart = $ps; hostSessionId = 'local_bbb' }
WriteJson (Join-Path $hostDir 'local_bbb.json') @{ sessionId = 'local_bbb'; title = 'a chat' }
WriteJson (Join-Path $sessDir '1003.json') @{ pid = 1003; procStart = $created.AddHours(-5).ToFileTimeUtc().ToString(); hostSessionId = 'local_bbb' }
WriteJson (Join-Path $sessDir '1004.json') @{ pid = 1004; procStart = $ps; hostSessionId = 'local_missing' }
'{ not json' | Set-Content -LiteralPath (Join-Path $sessDir '1006.json')
WriteJson (Join-Path $sessDir '1007.json') @{ pid = 1007; procStart = $ps; hostSessionId = 'local_ccc' }
WriteJson (Join-Path $hostDir 'local_ccc.json') @{ sessionId = 'local_ccc'; scheduledTaskId = 'ora-am-brief'; scheduledRunContinued = $true }
# 1008/1009 pin the PID-reuse tolerance (5 s): 4 s off still resolves, 6 s off is a mismatch.
# 1010 = registry present but no hostSessionId.
WriteJson (Join-Path $sessDir '1008.json') @{ pid = 1008; procStart = $created.AddSeconds(4).ToFileTimeUtc().ToString(); hostSessionId = 'local_bbb' }
WriteJson (Join-Path $sessDir '1009.json') @{ pid = 1009; procStart = $created.AddSeconds(6).ToFileTimeUtc().ToString(); hostSessionId = 'local_bbb' }
WriteJson (Join-Path $sessDir '1010.json') @{ pid = 1010; procStart = $ps }
$procs = 1001..1010 | ForEach-Object { [PSCustomObject]@{ ProcessId = $_; CommandLine = $fresh; CreationDate = $created } }
$map = Get-SessionInfoMap -Procs $procs -SessionsDir $sessDir -HostSessionsRoot (Join-Path $tmp 'host')
Check "map: scheduled session resolves with its task id" ($map[1001].Resolved -and $map[1001].ScheduledTaskId -eq 'ora-am-brief')
Check "map: interactive session resolves with NO task id" ($map[1002].Resolved -and -not $map[1002].ScheduledTaskId)
Check "map: procStart mismatch (PID reuse) -> unresolved" (-not $map[1003].Resolved)
Check "map: missing host record -> unresolved" (-not $map[1004].Resolved)
Check "map: missing registry file -> unresolved" (-not $map[1005].Resolved)
Check "map: malformed registry JSON -> unresolved, no crash" (-not $map[1006].Resolved)
Check "map: scheduled-but-continued carries ScheduledRunContinued" ($map[1007].Resolved -and $map[1007].ScheduledRunContinued)
Check "map: procStart 4 s off (inside the 5 s tolerance) -> still resolves" ($map[1008].Resolved)
Check "map: procStart 6 s off (outside the 5 s tolerance) -> unresolved" (-not $map[1009].Resolved)
Check "map: registry without hostSessionId -> unresolved" (-not $map[1010].Resolved)
# End-to-end: fixture map through the decision function -> only 1001 is killable.
$result = Get-KillCandidates -Procs ($procs | ForEach-Object { $_.CreationDate = $Now.AddMinutes(-100); $_ }) -Now $Now -ThresholdMinutes 90 -SessionInfo $map
Check "end-to-end fixture: ONLY the scheduled, un-continued, resolved session (1001) is a candidate" (($result.ProcessId -join ',') -eq '1001')
Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue

Write-Output ""
if ($script:failures.Count -gt 0) {
    Write-Output "$($script:failures.Count) FAILED: $($script:failures -join '; ')"
    exit 1
}
Write-Output "ALL PASS - stuck-session-watchdog decision logic correct"
exit 0
