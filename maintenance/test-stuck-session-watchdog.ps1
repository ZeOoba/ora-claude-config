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

Write-Output ""
if ($script:failures.Count -gt 0) {
    Write-Output "$($script:failures.Count) FAILED: $($script:failures -join '; ')"
    exit 1
}
Write-Output "ALL PASS - stuck-session-watchdog decision logic correct"
exit 0
