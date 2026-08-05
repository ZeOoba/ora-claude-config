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

Write-Output ""
if ($script:failures.Count -gt 0) {
    Write-Output "$($script:failures.Count) FAILED: $($script:failures -join '; ')"
    exit 1
}
Write-Output "ALL PASS - stuck-session-watchdog decision logic correct"
exit 0
