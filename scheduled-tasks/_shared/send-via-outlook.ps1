<#
.SYNOPSIS
    Send an email via the authenticated desktop Outlook profile (COM automation).

.DESCRIPTION
    Shared helper used by every ORA scheduled task that needs to deliver a report
    to ggoldberg@oxfordra.net. Uses Outlook.Application COM -- no OAuth, no app
    password, no token. Relies on the fact that Outlook desktop is already
    signed into the user's M365 account.

    The email is actually sent (not left as a draft).

.PARAMETER To
    Recipient email address. Accepts comma- or semicolon-separated list for
    multiple (commas are normalized to semicolons before the COM call).

.PARAMETER Subject
    Email subject line. Mutually exclusive with -SubjectFile; one of the two is required.

.PARAMETER SubjectFile
    Path to a UTF-8 text file whose content is the subject (one line; trailing CR/LF trimmed,
    an interior CR/LF is refused). Same flag, same meaning as outlook-sent-probe.ps1, so one
    temp file can feed both the probe and the send. Also the safe way to carry a non-ASCII
    subject (see the emoji example below) because no non-ASCII byte crosses a shell boundary.
    A missing, empty or multi-line file exits 1 and nothing is sent.

.PARAMETER Body
    Email body as a string. Mutually exclusive with -BodyFile.

.PARAMETER BodyFile
    Path to a file containing the email body. Preferred for long reports
    (avoids command-line length limits and quoting issues). Mutually exclusive
    with -Body.

.PARAMETER BodyFormat
    "html" (default) or "text".

.PARAMETER Cc
    Optional CC recipients (comma-separated).

.PARAMETER Attachment
    Optional file path(s) to attach. Accepts one path or several.

    Every path is resolved to an absolute path BEFORE the COM call, because
    Outlook resolves a relative path against its own working directory rather
    than the caller's. Validation is fail-closed: a missing file, a directory,
    an empty string, or a combined size over 20 MB rejects the WHOLE send with
    exit 1 and nothing is sent -- a message whose body promises an attachment
    must never go out without it.

    ATTACHMENTS ARE INTERNAL-ONLY. A send that carries any attachment AND any
    external recipient is refused (exit 5), regardless of outbound-check
    authorization: that check authorizes recipients and has no view of file
    content, and an attachment bypasses every content scan in the fleet. Per
    the ORA routing canon every legitimate automated send is internal-only, so
    this never fires for real automation.

    The resolved paths are recorded in send-log.txt on the OK line, so the
    audit trail says exactly which bytes left the machine.

.PARAMETER DedupTaskId
    R-05 contract mode, always passed together with -DedupPeriodKey: the scheduled task id
    (e.g. ora-am-brief). The dedup key is <task id>/<period key>/<subject hash>. It is checked
    in send-log.txt BEFORE Send() (an already-sent key exits 0 with DEDUP-SKIP; a key whose
    earlier state is unknown exits 6 with DEDUP-BLOCK), and the script then retries exit 2/4
    once itself. A contract-mode caller never retries.

.PARAMETER DedupPeriodKey
    The cycle the send belongs to: the ET date yyyy-MM-dd for daily tasks (take block-sentinel.py's
    etDate, or PowerShell Get-Date -Format yyyy-MM-dd; never a UTC date),
    yyyy-MM monthly, yyyy-Www weekly, or <etDate>-<block> (for example 2026-10-18-slot-12) for multi-fire tasks, built from
    block-sentinel's etDate and block. A bare block such as slot-12 repeats every day and would
    DEDUP-SKIP all later days.
    RETENTION CAVEAT: the dedup record is a send-log line, and the nightly trim
    (maintenance/ora-nightly-disk.ps1) keeps only the last ~500 lines, so a record survives for
    days to a few weeks depending on send volume. A coarse key (yyyy-MM monthly, and to a lesser
    degree yyyy-Www weekly) can age out inside its own period, and a re-fire after that sends
    again. Prefer the ET date or a per-fire key (<etDate>-<block>); use yyyy-MM only where a
    re-fire after the record has aged out cannot happen or is acceptable.

.PARAMETER ForceResend
    Human-directed only: bypasses DEDUP-BLOCK, DEDUP-SKIP and the legacy quarantine after a
    person has checked Sent Items. A scheduled spec must never pass it
    (R-05 Task 6 adds maintenance/_tests/test_send_contract_spec_lint.py, which fails on it).

.EXAMPLE
    # Short message
    .\send-via-outlook.ps1 -To "ggoldberg@oxfordra.net" -Subject "Test" -Body "Hello"

.EXAMPLE
    # Long report from file
    "<h1>Morning Brief</h1>..." | Out-File -Encoding UTF8 $env:TEMP\brief.html
    .\send-via-outlook.ps1 -To "ggoldberg@oxfordra.net" `
        -Subject "[ORA] Morning Brief - 2026-04-17" `
        -BodyFile "$env:TEMP\brief.html" -BodyFormat html

.EXAMPLE
    # Report with a generated calendar file attached (internal recipient only)
    .\send-via-outlook.ps1 -To "ggoldberg@oxfordra.net" `
        -Subject "[ORA] Forward Calendar - week of 2026-09-21" `
        -BodyFile "$env:TEMP\digest.html" -BodyFormat html `
        -Attachment "C:\Users\Owner\.claude\artifacts\ora-forward-calendar\out\ora-forward-calendar.ics"

.EXAMPLE
    # Non-ASCII subject (emoji / em-dash) -- REQUIRED when a task's subject is a
    # parsing contract. Several ORA tasks have subject lines that a DOWNSTREAM task
    # searches for literally: ora-health-guard Block B emits
    # "<U+2705> ORA Connector Pre-Flight <U+2014> <date>" and ora-am-brief Block B
    # locates that mail by matching the leading check-mark. Drop the emoji and the
    # contract silently breaks -- the search returns nothing and the consumer
    # degrades with no error.
    #
    # DO NOT pass such a subject as a literal through a Bash -> PowerShell command
    # line. The characters are mangled en route (the Git-Bash layer re-encodes,
    # and PowerShell -File reads a BOM-less .ps1 as cp1252), and the failure is
    # invisible: the send exits 0 and only the subject is wrong. This bit
    # ora-health-guard on 2026-07-24 -- it sent twice, the first with a plain-ASCII
    # subject that would have failed am-brief's search.
    #
    # Instead, build the string from codepoints inside a written .ps1 file, so no
    # non-ASCII byte ever crosses a shell boundary:
    #
    #     $check = [char]0x2705                      # U+2705 WHITE HEAVY CHECK MARK
    #     $dash  = [char]0x2014                      # U+2014 EM DASH
    #     $subj  = "$check ORA Connector Pre-Flight $dash 2026-07-24 $dash Notion OK"
    #     & '...\send-via-outlook.ps1' -To 'ggoldberg@oxfordra.net' `
    #         -Subject $subj -BodyFile $body -BodyFormat html
    #
    # The file stays pure ASCII, so its encoding is irrelevant. VERIFY after sending
    # -- send-log.txt renders the console's cp1252 view and shows "?" even on a
    # correct send, so it CANNOT confirm this. Read the codepoints back off the
    # Sent Items item instead:
    #
    #     $m.Subject.ToCharArray() | % { "U+{0:X4}" -f [int]$_ }

.NOTES
    Exit codes (R-05 send contract, ratified 2026-10-18; memory rules.md section 2 is the
    caller-facing table, aligned to this contract by R-05 Task 7):
      0 = sent OK (or, with a dedup key, already sent this period: DEDUP-SKIP).
      1 = usage error. Never retried.
      2 = Outlook COM failure BEFORE Send() was invoked, or Send() rejected by the callee with
          RPC_E_CALL_REJECTED (0x80010001, nothing was sent). Retry-safe.
      3 = Outlook stuck on a startup/profile wizard (preflight-detected, no COM attempted). Never retried.
          In contract mode this applies only to a run that could still send: the read-only dedup
          lookup runs first, so a duplicate (key already sent -> DEDUP-SKIP exit 0), a key whose
          state is unknown (exit 6) and an unreadable send-log (exit 6) are decided without
          Outlook ever being consulted.
      4 = COM call timed out BEFORE Send() was invoked (Outlook likely blocked). Retry-safe.
      5 = refused: attachment + external recipient, or external recipient(s) not authorized
          (see OUTBOUND-ACTION CHECK below). NEVER retried.
      6 = send state UNKNOWN: Send() was invoked and did not confirm (timeout, or a throw inside
          Send()), a DEDUP-BLOCK / QUARANTINE refusal of a send whose earlier state is unknown,
          or a fail-closed refusal in contract mode (send-log unreadable, dedup lock or SEND-INTENT
          record unavailable, send markers unreadable). The message MAY have gone out. NEVER
          retried; a human checks Sent Items and, only if it is absent, re-runs with -ForceResend.
          Legacy mode ALSO refuses with exit 6 (QUARANTINE) when the send-log, or an unknown-send
          sidecar marker, exists but cannot be read: a prior unknown send cannot be ruled out.
          If the SEND-STATE-UNKNOWN line itself cannot be appended to the log (lock, ACL, full disk),
          the script writes a sidecar marker <log name>.unknown-<shash> next to the log it is using
          (for the live log: send-log.unknown-<shash>; a stamp and a recipient hash only) and prints
          a stderr line; the legacy 60-minute quarantine honours the marker exactly like a log line.
          If NEITHER the log nor the marker can be written (for example a read-only log in a
          directory that denies new files), legacy mode refuses BEFORE Send() with exit 6
          RECORD-CHANNELS-UNAVAILABLE (nothing sent). The check opens the log the way Write-Log's
          Add-Content does and does not write to it. Residual: a channel that fails AFTER the check
          and before the SEND-STATE-UNKNOWN append (that span includes the Outlook cold-start wait and
          the send timeout, up to a few minutes) is unrecorded; so is a disk that fills in that span.
          -ForceResend skips the check (human-directed).
    With -DedupTaskId + -DedupPeriodKey ("contract mode") the script itself retries exit 2/4
    ONCE, so the caller retries nothing. Without them ("legacy mode") the only internal retry
    is the existing one on RPC_E_CALL_REJECTED, a legacy caller may retry 2/4 once, and the
    same subject to the same To is refused for 60 minutes after a logged SEND-STATE-UNKNOWN.
    All sends are appended to C:\Users\Owner\.claude\scheduled-tasks\_shared\send-log.txt

    OUTBOUND-ACTION CHECK (2026-07-17, OI-007). ora-autonomy-gate.py's PreToolUse Gate 1
    detects an external recipient by parsing the Bash command's literal TEXT -- adversarial
    review proved that is structurally blind to value indirection (a recipient built from a
    PowerShell variable, string concatenation, or a file read never appears as a literal
    email-shaped substring in the command, so Gate 1 never fires: exit 0, zero override
    needed). This script closes that gap at the one point indirection cannot survive: by
    the time $To/$Cc are bound here, PowerShell has ALREADY resolved whatever indirection
    was used to whatever concrete string it evaluates to. So immediately below, once $To/
    $Cc are normalized, every non-@oxfordra.net recipient is checked against a session-
    scoped, content-bound `allow-external-send` token via hooks/lib/check_external_send.py
    (the SAME token contract Gate 1 uses, via hooks/lib/email_send_tier.py -- one shared
    definition, so the two enforcement points cannot silently diverge on what "authorized"
    means). Defense in depth, not a replacement for Gate 1: Gate 1 still runs first and
    catches the common literal case for free; this is the backstop that indirection cannot
    evade. A missing/unresolvable CLAUDE_CODE_SESSION_ID with an external recipient present
    FAILS CLOSED (no session context, no override reachable) -- per the ORA routing canon
    (CLAUDE.md), every legitimate scheduled/automated send is internal-only anyway
    (ggoldberg@/egoldberg@ only), so this can never fail a legitimate automation; it only
    ever gates a genuinely external send, exactly as Gate 1 already does.

    -WhatIf performs every check (including the one above) but stops short of the actual
    Outlook COM call, logging "DRY RUN: would send" and exiting 0 instead. Added so the
    gating logic can be tested end-to-end without ever sending a real email.
#>

# PositionalBinding=$false (2026-09-18): every real caller in the fleet invokes
# this script with NAMED parameters (verified by sweep before this was added), and
# positional binding actively hides mistakes. "-Attachment a b" used to bind 'a'
# and then silently drop 'b' into the next free positional slot -- which is
# $BodyFile -- surfacing as a baffling "-Body and -BodyFile are mutually
# exclusive". With positional binding off, that stray token is a loud parameter
# error instead. No caller changes; a positional call was never used.
[CmdletBinding(PositionalBinding=$false)]
param(
    [Parameter(Mandatory=$true)][string]$To,
    # Exactly one of -Subject / -SubjectFile (checked below, exit 1). Not Mandatory so that
    # -SubjectFile is accepted: the other shared helper (outlook-sent-probe.ps1) takes
    # -SubjectFile and callers pass the same flag to both; before 2026-10-28 this script
    # rejected it as an unknown parameter and the fire died before the send.
    [string]$Subject,
    [string]$SubjectFile,
    [string]$Body,
    [string]$BodyFile,
    [ValidateSet("html","text")][string]$BodyFormat = "html",
    [string]$Cc,
    [string[]]$Attachment,
    # R-05 send contract (ratified 2026-10-18). Names deliberately avoid the -T and -C
    # prefixes: ora-autonomy-gate.py Gate 1 relies on $To being the ONLY parameter that
    # starts with T (so `-T x@y` cannot slip past it), and -C must keep meaning -Cc.
    [string]$DedupTaskId,
    [string]$DedupPeriodKey,
    [switch]$ForceResend,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$LogPath = "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-log.txt"
$CanonicalLogPath = $LogPath
# Tests redirect the audit log, but ONLY under -WhatIf. A real send always writes
# the canonical log, so this can never be used to blind the audit trail.
if ($WhatIf -and $env:ORA_SEND_LOG_PATH) { $LogPath = $env:ORA_SEND_LOG_PATH }
# R-05 test seam: skip the Outlook-process preflight so a dry run does not depend on whether
# a real Outlook happens to be open, busy or on a wizard (2026-10-18: two existing dry-run
# cases exited 3 because the live Outlook was momentarily not Responding). Honored ONLY under
# -WhatIf, like ORA_SEND_LOG_PATH above.
$SkipPreflight = [bool]($WhatIf -and $env:ORA_SEND_SKIP_PREFLIGHT -eq '1')
# Test seam (WhatIf only): make the readiness preflight behave as if Outlook were busy or on a wizard, so the
# ordering of the dedup lookup against the preflight can be tested without a real stuck Outlook.
$ForcePreflightStuck = [bool]($WhatIf -and $env:ORA_SEND_FORCE_PREFLIGHT_STUCK -eq '1')
# R-05 test seams for the send job, honored ONLY under -WhatIf (every line that reads one
# names $WhatIf; maintenance/_tests/test_send_contract_suite.py S1 enforces that).
# ORA_SEND_SIMULATE swaps the Outlook COM objects inside the send job for a scripted fake,
# as a comma list with one step per attempt. It is the only way to exercise the
# timeout/marker classification without Outlook.
$SimRaw     = if ($WhatIf) { [string]$env:ORA_SEND_SIMULATE } else { "" }
$TimeoutRaw = if ($WhatIf) { [string]$env:ORA_SEND_TIMEOUT_SEC } else { "" }
$DelayRaw   = if ($WhatIf) { [string]$env:ORA_SEND_RETRY_DELAY_SEC } else { "" }
# Widens the check-then-intent window inside the dedup gate so the mutex can be tested deterministically.
$GatePauseRaw = if ($WhatIf) { [string]$env:ORA_SEND_GATE_PAUSE_MS } else { "" }
# The dedup lock wait and the lock NAME are test seams too: a suite that holds the lock to prove the
# fail-closed path must neither wait the full 10 s nor ever contend with a real fire's production lock.
$LockWaitRaw = if ($WhatIf) { [string]$env:ORA_SEND_LOCK_WAIT_MS } else { "" }
$MutexSuffixRaw = if ($WhatIf) { [string]$env:ORA_SEND_MUTEX_SUFFIX } else { "" }
$SimPlan = @($SimRaw -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$Simulating = $SimPlan.Count -gt 0
# A simulated run writes a REAL-looking '[OK] Sent' line. It must never land in the canonical
# log, where every '[OK] Sent' reader (and the contract-mode dedup) would count it as a delivery.
# Checked before any Write-Log call, so this refusal cannot touch the canonical log either.
if ($WhatIf -and $Simulating -and -not $env:ORA_SEND_LOG_PATH) {
    [Console]::Error.WriteLine("ORA_SEND_SIMULATE requires ORA_SEND_LOG_PATH: a simulated send must never write the canonical send log")
    exit 1
}
# ...and the redirected log must live under the user's TEMP folder. A simulated '[OK] Sent ... key=' line in the
# canonical log would make a real fire of that key DEDUP-SKIP with exit 0 and no email. "Is it the canonical
# file" cannot be decided from the spelling (UNC \\localhost\C$\..., \\?\ forms, junctions, hard links all
# name the same file), so the rule is positive: only a plain local path under TEMP is accepted. The equality
# check stays as a second, explicit barrier (a scratch copy of this script keeps its fake canonical path in TEMP).
# $LogPath here is the already-redirected value, and a bad mutex-suffix seam value is refused, never ignored.
if ($Simulating) {
    # Drive-rooted only: '~', 'FileSystem::' and relative forms are resolved differently by .NET (the guard) and by
    # the provider (Add-Content), so a guard on one reading could be writing another file.
    $simLogFull = if ($LogPath -cmatch '\A[A-Za-z]:\\') { try { [System.IO.Path]::GetFullPath($LogPath) } catch { $null } } else { $null }
    $simTemp = try { [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()) } catch { $null }
    $simOk = $simLogFull -and $simTemp -and (-not $simLogFull.StartsWith('\\')) -and
        $simLogFull.StartsWith($simTemp, [System.StringComparison]::OrdinalIgnoreCase) -and
        (-not $simLogFull.Equals([System.IO.Path]::GetFullPath($CanonicalLogPath), [System.StringComparison]::OrdinalIgnoreCase))
    if (-not $simOk) {
        [Console]::Error.WriteLine("ORA_SEND_LOG_PATH must be a local path under TEMP and must not be the canonical send log: a simulated send must never write the canonical send log")
        exit 1
    }
    # Reader, writer and guard now all use the one resolved path.
    $LogPath = $simLogFull
    if ($MutexSuffixRaw -and $MutexSuffixRaw -cnotmatch '\A[A-Za-z0-9-]{1,40}\z') {
        [Console]::Error.WriteLine("ORA_SEND_MUTEX_SUFFIX must be 1-40 letters, digits or '-'")
        exit 1
    }
}
$TimeoutSec = 15
$RetryDelaySec = 5
$GatePauseMs = 0
$DedupLockWaitMs = 10000
if ($Simulating) {
    $n = 0
    if ([int]::TryParse($TimeoutRaw, [ref]$n) -and $n -ge 1 -and $n -le 15) { $TimeoutSec = $n }
    if ([int]::TryParse($DelayRaw, [ref]$n) -and $n -ge 0 -and $n -le 10) { $RetryDelaySec = $n }
    if ([int]::TryParse($GatePauseRaw, [ref]$n) -and $n -ge 0 -and $n -le 5000) { $GatePauseMs = $n }
    if ([int]::TryParse($LockWaitRaw, [ref]$n) -and $n -ge 100 -and $n -le 10000) { $DedupLockWaitMs = $n }
}

# Cap chosen to fail FAST with a readable message rather than let Exchange reject
# the message with an opaque COM HRESULT (typical Exchange ceiling is 25 MB).
$MaxAttachmentBytes = 20MB

function Write-Log {
    param([string]$Level, [string]$Message)
    # R-05: this is the single place a log line is built, so every user-controlled field
    # (Subject, To, Cc, attachment paths, dedup values) is neutralized here. Control chars
    # and the Unicode line separators become '?' in the LOGGED text only; the message that
    # is actually sent is never touched. Without this, a newline in a field writes a second
    # record that a later reader (dedup key=, status) would trust.
    $Message = $Message -replace '[\x00-\x1F\x7F\x85\u2028\u2029]', '?'
    # InvariantCulture: the quarantine scan parses this stamp, and a non-Gregorian host culture
    # (th-TH, ar-SA) would otherwise write a year the scan reads as ancient.
    $ts = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz", [System.Globalization.CultureInfo]::InvariantCulture)
    $line = "$ts [$Level] $Message"
    # Add-Content opens the log write-shared only, so ANY concurrent reader (the quarantine scan,
    # a health-guard tail) can make it throw a sharing violation for a few milliseconds. A swallowed
    # error would silently drop the record (a SEND-STATE-UNKNOWN line is the quarantine's only
    # evidence), so retry briefly before giving up.
    # $script:LogWriteOk tells a caller that MUST know (SEND-INTENT) whether the append landed.
    $script:LogWriteOk = $false
    for ($w = 1; $w -le 10; $w++) {
        try { Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8 -ErrorAction Stop; $script:LogWriteOk = $true; break } catch { if ($w -lt 10) { Start-Sleep -Milliseconds ([Math]::Min(20 * $w, 100)) } }
    }
    # -ErrorAction Continue overrides the script-scoped $ErrorActionPreference="Stop" for this
    # call only; without it, Write-Error terminates the script before the caller's `exit N`
    # line runs (bug found 2026-07-07: every ERROR path was silently collapsing to exit code 1).
    if ($Level -eq "ERROR") { Write-Error $Message -ErrorAction Continue } else { Write-Output $line }
}

# --- R-05 helpers (send contract, ratified 2026-10-18) ---
function Get-SubjectHash {
    # First 16 hex chars of SHA-256 over the UTF-8 bytes of the subject EXACTLY as bound.
    # Exact, not normalized: the hash exists to recognize a RETRY of the same call, which
    # re-sends the identical string. Same-day runs whose subjects differ (live counts in the
    # tail) are block-sentinel.py's job, not this one.
    param([string]$Text)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { $bytes = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Text)) } finally { $sha.Dispose() }
    return (-join ($bytes | ForEach-Object { $_.ToString('x2') })).Substring(0, 16)
}
# HRESULT 0x80010001 as the Int32 COM reports (Windows PowerShell 5.1 hex literals are Int32).
$RPC_E_CALL_REJECTED = [Convert]::ToInt32('80010001', 16)

function Read-SendPhases {
    # The send job appends one phase per line. A file we cannot read is NOT "not invoked":
    # it maps to 'unreadable', which Resolve-SendOutcome treats as state unknown.
    param([string]$Path)
    # A marker file we cannot read is never evidence that Send() was not invoked. That covers a
    # sharing violation, access denied, an I/O error AND a missing file: the job writes 'started'
    # before anything else, so a missing file means the write failed or the file was removed
    # (temp cleaner, antivirus), and either way the state is not provable. All map to
    # 'unreadable', which Resolve-SendOutcome turns into exit 6.
    try { return @([System.IO.File]::ReadAllLines($Path) | ForEach-Object { $_.Trim() } | Where-Object { $_ }) }
    catch { return @('unreadable') }
}

function Resolve-SendOutcome {
    # Pure: maps (timed out?, job errored?, phase markers) to the R-05 exit contract.
    # 0 sent; 2 failed BEFORE Send() (or RPC_E_CALL_REJECTED, refused by the callee);
    # 4 timed out BEFORE Send(); 6 Send() was invoked and not confirmed. The ORDER below is
    # load-bearing: 'returned' wins, then any evidence that Send() ran makes the state
    # unknown, and only with no such evidence is a timeout or failure retry-safe.
    param([bool]$TimedOut, [bool]$JobErrored, [string[]]$Phases)
    $p = @($Phases)
    if (-not $TimedOut -and -not $JobErrored) { return @{ Code = 0; State = 'SENT' } }
    if ($p -contains 'returned') { return @{ Code = 0; State = 'SENT' } }
    $atSend = @($p | Where-Object { $_ -like 'error-at-send *' })
    if ($atSend.Count -gt 0) {
        if ($atSend[0] -eq 'error-at-send 0x80010001') {
            return @{ Code = 2; State = 'REJECTED'; HResult = $RPC_E_CALL_REJECTED }
        }
        return @{ Code = 6; State = 'UNKNOWN'; Reason = "Send() threw ($($atSend[0]))" }
    }
    if (($p -contains 'invoked') -or ($p -contains 'unreadable')) {
        $why = if ($p -contains 'unreadable') { 'the send-phase marker file was missing or unreadable' }
               elseif ($TimedOut) { 'COM call exceeded the timeout after Send() was invoked' }
               else { 'the send job ended after Send() was invoked without confirming it returned' }
        return @{ Code = 6; State = 'UNKNOWN'; Reason = $why }
    }
    if ($TimedOut) { return @{ Code = 4; State = 'NOT_INVOKED' } }
    $before = @($p | Where-Object { $_ -like 'error-before 0x*' })
    $hr = $null
    if ($before.Count -gt 0) { $hr = [Convert]::ToInt32($before[0].Substring(15), 16) }
    return @{ Code = 2; State = 'NOT_INVOKED'; HResult = $hr }
}

$QuarantineMinutes = 60

function ConvertTo-RecipientKey {
    # Canonical form of a To value for quarantine comparison: control characters become '?' exactly
    # as Write-Log does (so the logged and the live value compare equal), then the address list
    # is split on ; and ,, trimmed, lower-cased, sorted and joined. Order, spacing and case of
    # the same recipients therefore do not defeat the quarantine.
    param([string]$Text)
    $t = [string]$Text -replace '[\x00-\x1F\x7F\x85\u2028\u2029]', '?'
    $parts = @($t -split '[;,]' | ForEach-Object { $_.Trim().ToLowerInvariant() } | Where-Object { $_ } | Sort-Object)
    return ($parts -join ';')
}

function Read-LogLinesShared {
    # Reads the send-log WITHOUT blocking other writers: FileShare ReadWrite+Delete, so a
    # concurrent Add-Content (whose errors Write-Log swallows) is never lost to our read. A
    # sharing violation from a writer mid-append is retried briefly before it is called unreadable.
    param([string]$Path)
    for ($try = 1; $try -le 4; $try++) {
        $fs = $null; $sr = $null
        try {
            $fs = New-Object System.IO.FileStream($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, ([System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete))
            $sr = New-Object System.IO.StreamReader($fs, [System.Text.Encoding]::UTF8, $true)
            $all = New-Object System.Collections.Generic.List[string]
            while ($null -ne ($l = $sr.ReadLine())) { $all.Add($l) }
            return ,($all.ToArray())
        }
        catch {
            if (-not ($_.Exception -is [System.IO.IOException] -or $_.Exception.InnerException -is [System.IO.IOException])) { throw }
            # New-Object wraps the real exception (MethodInvocationException), so look inside it too.
            $ex = if ($_.Exception.InnerException) { $_.Exception.InnerException } else { $_.Exception }
            if ($ex -is [System.IO.FileNotFoundException] -or $ex -is [System.IO.DirectoryNotFoundException]) { throw }
            if ($try -eq 4) { throw }
            Start-Sleep -Milliseconds 250
        }
        finally {
            if ($sr) { $sr.Dispose() } elseif ($fs) { $fs.Dispose() }
        }
    }
}

function Get-RecipientHash {
    # First 16 hex chars of SHA-256 over the canonical recipient key. The unknown-send sidecar marker
    # carries this and never the address itself.
    param([string]$Recipient)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { $b = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes((ConvertTo-RecipientKey $Recipient))) } finally { $sha.Dispose() }
    return (-join ($b | ForEach-Object { $_.ToString('x2') })).Substring(0, 16)
}

function Get-UnknownMarkerPath {
    # Second channel for SEND-STATE-UNKNOWN (C3): when the log append itself fails, this sidecar
    # file next to the run's OWN log is the quarantine's evidence. Derived from the log path the
    # run uses, so a test log under TEMP never writes next to the live log. For the live
    # send-log.txt it is send-log.unknown-<shash>. The hash is re-validated here: it is the only
    # variable part of the file name, so nothing but 16 lowercase hex can reach the path.
    param([string]$LogFile, [string]$Hash)
    if ($Hash -cnotmatch '\A[0-9a-f]{16}\z') { return $null }
    $dir = [System.IO.Path]::GetDirectoryName($LogFile)
    $stem = [System.IO.Path]::GetFileNameWithoutExtension($LogFile)
    if (-not $dir -or -not $stem) { return $null }
    return (Join-Path $dir ($stem + '.unknown-' + $Hash))
}

function Write-UnknownMarker {
    # Appends "<ISO stamp> rhash=<recipient hash>" (no subject, no address). Returns $true when the line landed.
    param([string]$LogFile, [string]$Hash, [string]$Recipient)
    $mp = Get-UnknownMarkerPath -LogFile $LogFile -Hash $Hash
    if (-not $mp) { return $false }
    $ts = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz", [System.Globalization.CultureInfo]::InvariantCulture)
    $line = "$ts rhash=$(Get-RecipientHash $Recipient)" + [Environment]::NewLine
    for ($w = 1; $w -le 10; $w++) {
        try { [System.IO.File]::AppendAllText($mp, $line, (New-Object System.Text.UTF8Encoding($false))); return $true } catch { if ($w -lt 10) { Start-Sleep -Milliseconds ([Math]::Min(20 * $w, 100)) } }
    }
    return $false
}

function Test-RecordChannelsAvailable {
    # Can an unknown send be recorded AT ALL? True when the run's log accepts an append or, failing that,
    # THIS subject's sidecar marker file can be opened for append. Both false means a SEND-STATE-UNKNOWN
    # would leave no trace and a legacy retry could double-send, so the legacy gate refuses BEFORE Send().
    # The log is opened with the access and sharing Add-Content (Write-Log) uses -- Write access, other
    # writers only (FileShare.Write): a concurrent READER blocks Add-Content, and a probe opened with wider
    # sharing would pass while the real write fails. Nothing is written to either file.
    param([string]$LogFile, [string]$Hash)
    for ($w = 1; $w -le 10; $w++) {
        $fs = $null
        try {
            $fs = New-Object System.IO.FileStream($LogFile, [System.IO.FileMode]::Append, [System.IO.FileAccess]::Write, [System.IO.FileShare]::Write)
            return $true
        } catch { } finally { if ($fs) { $fs.Dispose() } }
        if ($w -lt 10) { Start-Sleep -Milliseconds ([Math]::Min(20 * $w, 100)) }
    }
    $mp = Get-UnknownMarkerPath -LogFile $LogFile -Hash $Hash
    if (-not $mp) { return $false }
    $existed = Test-Path -LiteralPath $mp
    $ms = $null
    try { $ms = New-Object System.IO.FileStream($mp, [System.IO.FileMode]::Append, [System.IO.FileAccess]::Write, ([System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete)) }
    catch { return $false }
    finally { if ($ms) { $ms.Dispose() } }
    # A marker this check just created is empty; remove it so a healthy run leaves nothing behind.
    if (-not $existed) { try { Remove-Item -LiteralPath $mp -Force -ErrorAction Stop } catch { } }
    return $true
}

function Get-UnknownMarkerState {
    # NONE | QUARANTINED | UNREADABLE for the sidecar of this subject hash. A line counts only when it has
    # exactly the shape Write-UnknownMarker writes AND carries this recipient's hash; same absolute
    # 60-minute window as the log scan. A matching line whose stamp cannot be parsed fails CLOSED.
    # A marker that exists but cannot be read fails closed (UNREADABLE); a marker file with only
    # stale lines is cleaned up (best effort).
    param([string]$LogFile, [string]$Hash, [string]$Recipient, [int]$Minutes)
    $mp = Get-UnknownMarkerPath -LogFile $LogFile -Hash $Hash
    if (-not $mp) { return @{ State = 'NONE'; Stamp = $null } }
    try { $lines = Read-LogLinesShared -Path $mp }
    catch [System.IO.FileNotFoundException] { return @{ State = 'NONE'; Stamp = $null } }
    catch [System.IO.DirectoryNotFoundException] { return @{ State = 'NONE'; Stamp = $null } }
    catch { return @{ State = 'UNREADABLE'; Stamp = $null } }
    $rh = Get-RecipientHash $Recipient
    $now = [datetimeoffset]::UtcNow
    $anyFresh = $false
    foreach ($ln in $lines) {
        if ($ln.Length -gt 120 -or $ln -cnotmatch '\A(\S{1,40}) rhash=([0-9a-f]{16})\z') { continue }
        $stamp = $Matches[1]; $lrh = $Matches[2]
        $ts = [datetimeoffset]::MinValue
        if (-not [datetimeoffset]::TryParseExact($stamp, [string[]]@('yyyy-MM-ddTHH:mm:sszzz', 'yyyy-MM-ddTHH:mm:ssK', 'yyyy-MM-ddTHH:mm:ss.FFFFFFFK'), [System.Globalization.CultureInfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::None, [ref]$ts)) {
            if ($lrh -ceq $rh) { return @{ State = 'QUARANTINED'; Stamp = $stamp } }
            continue
        }
        $age = ($now - $ts).TotalMinutes
        if ($age -lt $Minutes -and $age -gt -1440) {
            $anyFresh = $true
            if ($lrh -ceq $rh) { return @{ State = 'QUARANTINED'; Stamp = $stamp } }
        }
    }
    if (-not $anyFresh) {
        # Nothing inside the window for ANY recipient: the marker has expired. Only delete a file whose own
        # write time is also outside the window, so a line appended a moment ago is never lost.
        try {
            $fi = New-Object System.IO.FileInfo($mp)
            if (($now - [datetimeoffset]$fi.LastWriteTimeUtc).TotalMinutes -ge $Minutes) { $fi.Delete() }
        } catch { }
    }
    return @{ State = 'NONE'; Stamp = $null }
}

function Get-QuarantineState {
    # Is there a recent SEND-STATE-UNKNOWN line for THIS subject hash (and recipient)?
    # Returns @{ State = 'NONE' | 'QUARANTINED' | 'UNREADABLE'; Stamp = <line timestamp or $null> }.
    # FAIL CLOSED: a log that exists but cannot be read is UNREADABLE (the caller refuses the
    # send); only a log that does not exist at all means "no history". Log lines are untrusted
    # text, so a line counts only when its WHOLE grammar matches what this script writes:
    #   <stamp> [ERROR] SEND-STATE-UNKNOWN: <reason> [to=<recipient>] shash=<hash>[ key=<k>]
    # The match is on the 16-hex hash at the END of the line and the recipient, never on free
    # text, and uses string operations (no regex over the whole line) so an oversized line
    # costs linear time. The window is absolute time (UTC), so DST and offsets cannot skew it.
    # The unknown-send sidecar marker (Get-UnknownMarkerPath) is a second source, consulted when the log scan
    # finds nothing: a SEND-STATE-UNKNOWN whose log append failed leaves only the marker.
    param([string]$Path, [string]$Hash, [string]$Recipient, [int]$Minutes)
    $none = @{ State = 'NONE'; Stamp = $null }
    if ($Hash -cnotmatch '\A[0-9a-f]{16}\z') { return $none }
    $lr = Get-QuarantineStateFromLog -Path $Path -Hash $Hash -Recipient $Recipient -Minutes $Minutes
    if ($lr.State -ne 'NONE') { return $lr }
    return (Get-UnknownMarkerState -LogFile $Path -Hash $Hash -Recipient $Recipient -Minutes $Minutes)
}

function Get-QuarantineStateFromLog {
    param([string]$Path, [string]$Hash, [string]$Recipient, [int]$Minutes)
    $none = @{ State = 'NONE'; Stamp = $null }
    try { $lines = Read-LogLinesShared -Path $Path }
    catch [System.IO.FileNotFoundException] { return $none }
    catch [System.IO.DirectoryNotFoundException] { return $none }
    catch { return @{ State = 'UNREADABLE'; Stamp = $null } }
    $marker = ' [ERROR] SEND-STATE-UNKNOWN: '
    $tag = " shash=$Hash"
    $now = [datetimeoffset]::UtcNow
    for ($i = $lines.Count - 1; $i -ge 0; $i--) {
        $ln = $lines[$i]
        $mi = $ln.IndexOf($marker, [System.StringComparison]::Ordinal)
        if ($mi -lt 1 -or $mi -gt 40) { continue }
        $stamp = $ln.Substring(0, $mi)
        if ($stamp.IndexOf(' ') -ge 0) { continue }
        $ti = $ln.LastIndexOf($tag, [System.StringComparison]::Ordinal)
        if ($ti -lt $mi + $marker.Length) { continue }
        $rest = $ln.Substring($ti)
        if ($rest.Length -gt 200 -or $rest -cnotmatch ('\A shash=' + $Hash + '( key=[0-9a-z-]+/[0-9A-Za-z_-]+/' + $Hash + ')?\z')) { continue }
        $mid = $ln.Substring($mi + $marker.Length, $ti - ($mi + $marker.Length))
        $ri = $mid.IndexOf(' to=', [System.StringComparison]::Ordinal)
        if ($ri -ge 0) {
            if ((ConvertTo-RecipientKey $mid.Substring($ri + 4)) -ne (ConvertTo-RecipientKey $Recipient)) { continue }
        }
        $ts = [datetimeoffset]::MinValue
        if (-not [datetimeoffset]::TryParseExact($stamp, [string[]]@('yyyy-MM-ddTHH:mm:sszzz', 'yyyy-MM-ddTHH:mm:ssK', 'yyyy-MM-ddTHH:mm:ss.FFFFFFFK'), [System.Globalization.CultureInfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::None, [ref]$ts)) {
            # A line that matches the whole grammar but whose age cannot be established: fail closed.
            return @{ State = 'QUARANTINED'; Stamp = $stamp }
        }
        $age = ($now - $ts).TotalMinutes
        # A stamp up to a day ahead is clock skew (still recent); further ahead is implausible.
        if ($age -lt $Minutes -and $age -gt -1440) { return @{ State = 'QUARANTINED'; Stamp = $stamp } }
    }
    return $none
}
$DedupMutexName = 'ORA-send-via-outlook-dedup'
if ($MutexSuffixRaw -cmatch '\A[A-Za-z0-9-]{1,40}\z') { $DedupMutexName += '-' + $MutexSuffixRaw }   # test seam, WhatIf only

function Get-DedupState {
    # Replays the send-log lines that belong to ONE dedup key and returns
    #   @{ State = 'SENT' | 'UNKNOWN' | 'PROCEED' | 'UNREADABLE'; At = <stamp or $null> }
    # Log lines are untrusted text (a subject or recipient can carry any characters except control
    # characters, which Write-Log strips), so a line counts only when it has the shape THIS script
    # writes: it ends with exactly ` shash=<hash> key=<Key>` (TagLog is always the last field, so a
    # key-looking token inside a subject can never sit there) AND its record type sits at the very
    # start, right after the stamp and level. The tail is compared as a whole string, so period
    # 2026-10-1 never matches 2026-10-18 and task `x` never matches task `ax`.
    # SENT if any line proves a send ([OK] Sent, or [OK] DEDUP-SKIP so the proof survives rotation of
    # the original line); otherwise UNKNOWN if a SEND-STATE-UNKNOWN is unreset or a SEND-INTENT is
    # unresolved; otherwise PROCEED. An existing log that cannot be read is UNREADABLE: the caller
    # fails CLOSED (exit 6), because "no history" cannot be told apart from "history we cannot see".
    # A log that does not exist yet is PROCEED.
    param([string]$Path, [string]$Key)
    try { $lines = Read-LogLinesShared -Path $Path }
    catch [System.IO.FileNotFoundException] { return @{ State = 'PROCEED'; At = $null } }
    catch [System.IO.DirectoryNotFoundException] { return @{ State = 'PROCEED'; At = $null } }
    catch { return @{ State = 'UNREADABLE'; At = $null } }
    $hash = $Key.Substring($Key.LastIndexOf('/') + 1)
    $tail = " shash=$hash key=$Key"
    $head = '\A(\S{1,40}) \[(OK|INFO|WARN|ERROR)\] (Sent to=|DEDUP-SKIP: |SEND-INTENT: |SEND-STATE-UNKNOWN: |FORCE-RESEND: |TIMEOUT: |Outlook COM failed )'
    $open = $false; $unknown = $false; $at = $null
    foreach ($ln in $lines) {
        if (-not $ln.EndsWith($tail, [System.StringComparison]::Ordinal)) { continue }
        $m = [regex]::Match($ln.Substring(0, [Math]::Min($ln.Length, 120)), $head)
        if (-not $m.Success) { continue }
        $stamp = $m.Groups[1].Value; $lvl = $m.Groups[2].Value; $typ = $m.Groups[3].Value
        if ($lvl -ceq 'OK' -and ($typ -ceq 'Sent to=' -or $typ -ceq 'DEDUP-SKIP: ')) { return @{ State = 'SENT'; At = $stamp } }
        if ($lvl -ceq 'WARN' -and $typ -ceq 'FORCE-RESEND: ') { $open = $false; $unknown = $false; continue }
        if ($lvl -ceq 'INFO' -and $typ -ceq 'SEND-INTENT: ') { $open = $true; $at = $stamp; continue }
        if ($lvl -ceq 'ERROR' -and $typ -ceq 'SEND-STATE-UNKNOWN: ') { $unknown = $true; $open = $false; $at = $stamp; continue }
        if (($lvl -ceq 'ERROR' -or $lvl -ceq 'WARN') -and ($typ -ceq 'TIMEOUT: ' -or $typ -ceq 'Outlook COM failed ')) { $open = $false; continue }
    }
    if ($unknown -or $open) { return @{ State = 'UNKNOWN'; At = $at } }
    return @{ State = 'PROCEED'; At = $null }
}

function Enter-DedupGate {
    # Check-then-INTENT under one named mutex, so two concurrent fires with the same key cannot both
    # PROCEED: the second sees the first's open SEND-INTENT and gets UNKNOWN. Fails CLOSED: a lock that
    # is not acquired, a log that cannot be read, or an intent that cannot be written returns
    # UNAVAILABLE and the caller refuses (exit 6). An ABANDONED mutex (holder died) is still ours.
    # Returns @{ State = 'SENT' | 'UNKNOWN' | 'UNAVAILABLE' | 'PROCEED'; At; Reason }.
    param([string]$Key, [switch]$Force)
    $mutex = $null; $owned = $false
    try {
        # No fallback to a Local\ lock: it would silently be a DIFFERENT lock, and two same-key fires
        # could both pass (a Global\ mutex that cannot be opened, e.g. one created at another integrity
        # level, is exactly when the fallback would have engaged). Cannot open it -> fail closed.
        try { $mutex = New-Object System.Threading.Mutex($false, "Global\$DedupMutexName") }
        catch { return @{ State = 'UNAVAILABLE'; At = $null; Reason = "DEDUP-LOCK-UNAVAILABLE: the system-wide dedup lock could not be opened ($($_.Exception.Message)), so concurrent fires cannot be ruled out" } }
        try { $owned = $mutex.WaitOne($DedupLockWaitMs) }
        catch {
            $abandoned = ($_.Exception -is [System.Threading.AbandonedMutexException]) -or ($_.Exception.InnerException -is [System.Threading.AbandonedMutexException])
            if (-not $abandoned) { throw }
            $owned = $true
            Write-Log "WARN" "DEDUP-LOCK-ABANDONED: a previous holder died while holding the dedup lock; continuing under the re-acquired lock$TagLog" | Out-Null
        }
        if (-not $owned) { return @{ State = 'UNAVAILABLE'; At = $null; Reason = "DEDUP-LOCK-TIMEOUT: dedup lock not acquired in $([int]($DedupLockWaitMs / 1000))s, so a concurrent fire with this key cannot be ruled out" } }
        # -ForceResend: no check, but the FORCE-RESEND reset and the intent are written under the SAME lock,
        # so a concurrent keyed fire can never read the reset and proceed before the intent lands.
        if ($Force) {
            Write-Log "WARN" "FORCE-RESEND: dedup and quarantine bypassed by -ForceResend (human-directed re-run only; a scheduled spec must never pass it)$TagLog" | Out-Null
            $state = @{ State = 'PROCEED'; At = $null }
        } else {
            $state = Get-DedupState -Path $LogPath -Key $Key
        }
        if ($state.State -eq 'UNREADABLE') { return @{ State = 'UNAVAILABLE'; At = $null; Reason = "DEDUP-UNAVAILABLE: the send-log could not be read, so a prior send for this key cannot be ruled out" } }
        if ($state.State -eq 'PROCEED') {
            if ($GatePauseMs -gt 0) { Start-Sleep -Milliseconds $GatePauseMs }   # test seam only (simulated runs)
            Write-Log "INFO" "SEND-INTENT: key=$Key subject=`"$Subject`"$TagLog" | Out-Null
            if (-not $script:LogWriteOk) { return @{ State = 'UNAVAILABLE'; At = $null; Reason = "DEDUP-INTENT-UNWRITTEN: could not append SEND-INTENT, and an unrecorded send cannot be deduplicated" } }
        }
        return $state
    } catch {
        return @{ State = 'UNAVAILABLE'; At = $null; Reason = "DEDUP-UNAVAILABLE: $($_.Exception.Message)" }
    } finally {
        if ($owned) { try { $mutex.ReleaseMutex() } catch { } }
        if ($mutex) { $mutex.Dispose() }
    }
}
# --- end R-05 helpers ---

# --- Resolve subject source (-Subject xor -SubjectFile) ---
if ($PSBoundParameters.ContainsKey('Subject') -and $SubjectFile) {
    Write-Log "ERROR" "-Subject and -SubjectFile are mutually exclusive"
    exit 1
}
if ($SubjectFile) {
    if (-not (Test-Path -LiteralPath $SubjectFile -PathType Leaf)) {
        Write-Log "ERROR" "SubjectFile not found: $SubjectFile"
        exit 1
    }
    $Subject = (Get-Content -LiteralPath $SubjectFile -Raw -Encoding UTF8)
    if ($null -eq $Subject) { $Subject = "" }
    $Subject = $Subject.TrimEnd("`r", "`n")
    if ($Subject -match "[`r`n]") {
        Write-Log "ERROR" "SubjectFile must hold a single line: $SubjectFile"
        exit 1
    }
}
if ([string]::IsNullOrWhiteSpace($Subject)) {
    Write-Log "ERROR" "Must provide -Subject or -SubjectFile (non-empty)"
    exit 1
}

# --- Validate body source ---
if (-not $Body -and -not $BodyFile) {
    Write-Log "ERROR" "Must provide either -Body or -BodyFile"
    exit 1
}
if ($Body -and $BodyFile) {
    Write-Log "ERROR" "-Body and -BodyFile are mutually exclusive"
    exit 1
}

if ($BodyFile) {
    if (-not (Test-Path $BodyFile)) {
        Write-Log "ERROR" "BodyFile not found: $BodyFile"
        exit 1
    }
    $Body = Get-Content -Path $BodyFile -Raw -Encoding UTF8
}

# --- Dedup key (R-05). Both flags or neither: a half-keyed call is a caller bug. ---
# "Passed" is decided by ContainsKey, not truthiness, so an explicitly empty value cannot
# silently fall back to legacy mode. Echoed values are stripped of control characters so a
# hostile value cannot split or forge a send-log record.
$HasTaskId = $PSBoundParameters.ContainsKey('DedupTaskId')
$HasPeriodKey = $PSBoundParameters.ContainsKey('DedupPeriodKey')
if ($HasTaskId -ne $HasPeriodKey) {
    Write-Log "ERROR" "-DedupTaskId and -DedupPeriodKey must be passed together (both or neither)"
    exit 1
}
$ContractMode = $HasTaskId
if ($ContractMode) {
    if ([string]::IsNullOrWhiteSpace($DedupTaskId) -or [string]::IsNullOrWhiteSpace($DedupPeriodKey)) {
        Write-Log "ERROR" "-DedupTaskId and -DedupPeriodKey must not be empty when passed"
        exit 1
    }
    # \z, not $: in .NET `$` also matches before a trailing newline.
    if ($DedupTaskId -cnotmatch '^[a-z0-9][a-z0-9-]{1,63}\z') {
        $shown = $DedupTaskId -replace '[\x00-\x1F\x7F\x85\u2028\u2029]', '?'
        Write-Log "ERROR" "-DedupTaskId '$shown' is not a task id (lowercase letters, digits and '-')"
        exit 1
    }
    if ($DedupPeriodKey -cnotmatch '^[0-9A-Za-z][0-9A-Za-z_-]{3,39}\z') {
        $shown = $DedupPeriodKey -replace '[\x00-\x1F\x7F\x85\u2028\u2029]', '?'
        Write-Log "ERROR" "-DedupPeriodKey '$shown' is not a period key (e.g. 2026-10-18, 2026-W42, 2026-10, 2026-10-18-slot-12)"
        exit 1
    }
}
$SubjectHash = Get-SubjectHash $Subject
$DedupKey = if ($ContractMode) { "$DedupTaskId/$DedupPeriodKey/$SubjectHash" } else { $null }
# Appended to every send-path log line so the dedup and quarantine scans can find them.
$TagLog = " shash=$SubjectHash" + $(if ($ContractMode) { " key=$DedupKey" } else { "" })

$ValidSim = @('ok', 'slow-ok', 'hang-before-send', 'throw-before-send', 'hang-after-send', 'throw-at-send', 'reject-at-send', 'returned-late', 'block-before-send', 'invoke-during-stop')
if ($SimRaw.Trim() -and -not $Simulating) {
    Write-Log "ERROR" "ORA_SEND_SIMULATE '$SimRaw' contains no simulation step"
    exit 1
}
foreach ($s in $SimPlan) {
    if ($ValidSim -notcontains $s) {
        Write-Log "ERROR" "ORA_SEND_SIMULATE step '$s' is not one of: $($ValidSim -join ', ')"
        exit 1
    }
}

# --- Validate attachments (2026-09-18) ---
# Fail-closed by design: a message whose body promises an attachment must never
# go out without it, so ANY bad entry rejects the whole send before Outlook is
# touched. Same exit code as the other argument faults above (1) -- attachment
# faults never widen the exit contract (see .NOTES, codes 0-6): this check reuses exit 1.
$ResolvedAttachments = @()
if ($PSBoundParameters.ContainsKey('Attachment')) {
    # Under `powershell -File` -- how the whole fleet invokes this script -- a
    # [string[]] parameter can NEVER receive more than one element: PowerShell
    # binds "-Attachment a b" as one value plus a stray positional, and
    # "-Attachment a,b" as the single literal string "a,b" (both verified
    # empirically 2026-09-18). So MULTIPLE attachments travel as one
    # '|'-delimited token -- unambiguous because '|' is illegal in a Windows
    # filename. An in-process caller passing a real array still works unchanged.
    # In Windows PowerShell 5.1, @($Attachment) on a [string[]]-typed parameter
    # explicitly bound to $null returns $null itself, NOT a 1-element array (it
    # does the opposite -- return a 1-element array -- for an untyped variable
    # holding $null; verified empirically 2026-09-18, this file's own type
    # annotation is what triggers it). `foreach` over $null runs zero iterations
    # silently, so a guard placed INSIDE the loop below would never fire and an
    # in-process caller passing -Attachment $null by mistake would silently
    # degrade to "no attachment sent" instead of erroring. Checked here, before
    # the wrap, so it fires regardless of that quirk.
    if ($null -eq $Attachment) {
        Write-Log "ERROR" "Attachment path is null"
        exit 1
    }
    $AttachmentList = @()
    foreach ($a in @($Attachment)) {
        # Defense in depth for the narrower case the check above does not cover:
        # a real array with one NULL ELEMENT inside it (e.g. -Attachment @($x, $null)
        # from an in-process caller). $null -split anything returns an EMPTY array,
        # not $null, so without this a null element would silently vanish here
        # rather than being rejected.
        if ($null -eq $a) {
            Write-Log "ERROR" "Attachment path is null"
            exit 1
        }
        $AttachmentList += ($a -split '\|')
    }

    $totalBytes = 0
    foreach ($a in $AttachmentList) {
        if ([string]::IsNullOrWhiteSpace($a)) {
            Write-Log "ERROR" "Attachment path is empty"
            exit 1
        }
        # Resolve BEFORE handing anything to COM. Outlook resolves a relative path
        # against ITS OWN working directory, not the caller's -- so a relative path
        # either attaches the wrong file or fails deep inside the COM job where the
        # error surfaces only as a generic HRESULT.
        $resolved = $null
        try { $resolved = (Resolve-Path -LiteralPath $a -ErrorAction Stop).ProviderPath } catch { $resolved = $null }
        if (-not $resolved) {
            Write-Log "ERROR" "Attachment not found: $a"
            exit 1
        }
        if ((Get-Item -LiteralPath $resolved).PSIsContainer) {
            Write-Log "ERROR" "Attachment is not a file (directory): $resolved"
            exit 1
        }
        $totalBytes += (Get-Item -LiteralPath $resolved).Length
        $ResolvedAttachments += $resolved
    }
    if ($totalBytes -gt $MaxAttachmentBytes) {
        Write-Log "ERROR" ("Attachment total {0:N0} bytes exceeds the {1:N0}-byte cap" -f $totalBytes, $MaxAttachmentBytes)
        exit 1
    }
}

# Full resolved paths, not basenames: the audit log should say exactly which bytes
# left the building. '|' is not a legal Windows filename character, so it is also
# the safe delimiter for handing this list to the background job below.
$AttachJoined = ($ResolvedAttachments -join '|')
$AttachLog = if ($ResolvedAttachments.Count -gt 0) {
    " attachments=$($ResolvedAttachments.Count) [$($ResolvedAttachments -join '; ')]"
} else { "" }

# --- Preflight: detect a stuck startup-wizard Outlook before ever touching COM ---
# (root cause 2026-07-07: a headless DCOM-spawned Outlook instance can get stuck on the
# first-run "Welcome to Microsoft Outlook" wizard, which rejects/hangs every COM call.
# 2026-07-08 incident: a "New Profile" wizard title wasn't in this match, so the script
# hung ~2min/call on the blocked COM job instead of fast-failing exit 3 all day -- added
# "New Profile" plus a generic "Profile" catch-all so any future profile-wizard variant
# fast-fails too, since Outlook's normal window title never contains that word.)
# R-05 ordering (dedup before readiness): the dedup lookup is READ-ONLY (no lock, no SEND-INTENT) and happens
# here, before the readiness verdict. A keyed run whose key is already SENT / UNKNOWN / unreadable is a duplicate
# or a fail-closed case: a busy Outlook must not turn it into exit 3, so the stuck verdict is only fatal when the
# lookup says PROCEED. Every other check keeps its original position; the duplicate is ACTED on (DEDUP-SKIP /
# DEDUP-BLOCK / fail closed) right after the recipient and attachment checks, so a refusal (exit 1/5) is never
# masked by a suppression and the single-use external-send authorization is consumed exactly as before for any
# run that can still send. A plain -WhatIf dry run skips the lookup: its DRY RUN line already reports dedup=<state>.
# -ForceResend skips it too (human-directed: it bypasses dedup, so the preflight stays fatal).
$EarlyDedup = $null
if ($ContractMode -and -not $ForceResend -and -not ($WhatIf -and -not $Simulating)) {
    $EarlyDedup = Get-DedupState -Path $LogPath -Key $DedupKey
}
$EarlyResolved = [bool]($EarlyDedup -and $EarlyDedup.State -ne 'PROCEED')
$existingOutlook = if ($SkipPreflight) { $null } else { Get-Process OUTLOOK -ErrorAction SilentlyContinue }
$stuckMsg = $null
if ($ForcePreflightStuck) {
    $stuckMsg = "Outlook stuck on startup wizard (PID=0, title='simulated by ORA_SEND_FORCE_PREFLIGHT_STUCK') - human must dismiss"
} elseif ($existingOutlook) {
    foreach ($proc in $existingOutlook) {
        if ((-not $proc.Responding) -or ($proc.MainWindowTitle -match 'Welcome to Microsoft Outlook|Choose Profile|New Profile|Profile')) {
            $stuckMsg = "Outlook stuck on startup wizard (PID=$($proc.Id), title='$($proc.MainWindowTitle)') - human must dismiss"
            break
        }
    }
}
if ($stuckMsg -and -not $EarlyResolved) {
    Write-Log "ERROR" $stuckMsg
    exit 3
}

# --- Subject-date sanity (2026-07-09): WARN-only, never blocks a send ---
# Frozen-date defect class (e.g. "[ORA Command Center] Daily Brief -- 2026-06-01" sent
# daily for ~5 weeks): an automated producer stamping a stale constant into its subject.
# Any ISO date in the subject >1 day from today logs a WARN line here at the sole send
# chokepoint, so ora-pm-ledger Block B Check I / humans catch the whole class. Non-ISO
# forms ("Week of July 13") are deliberately ignored -- no false noise on legitimate
# forward-dated subjects.
foreach ($m in [regex]::Matches($Subject, '\b20\d{2}-\d{2}-\d{2}\b')) {
    $d = [datetime]::MinValue
    if ([datetime]::TryParseExact($m.Value, 'yyyy-MM-dd', [System.Globalization.CultureInfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::None, [ref]$d)) {
        $drift = [math]::Abs(($d.Date - (Get-Date).Date).TotalDays)
        if ($drift -gt 1) {
            Write-Log "WARN" "SUBJECT-DATE: subject contains $($m.Value) ($([int]$drift)d from send date) - frozen-date defect? subject=`"$Subject`""
        }
    }
}

# --- Send via Outlook COM (job-wrapped, 15s timeout, bounded retry on RPC_E_CALL_REJECTED) ---
# Outlook COM requires semicolon-delimited recipients; normalize commas
# (comma-separated lists fail with "Outlook does not recognize one or more names")
$To = ($To -replace ',', ';')
if ($Cc) { $Cc = ($Cc -replace ',', ';') }

# --- OUTBOUND-ACTION CHECK (2026-07-17, OI-007) -- see .NOTES above for the full rationale.
# $To/$Cc are the FINAL, PowerShell-resolved values at this point -- whatever indirection
# (variable, concatenation, file read) constructed them is already collapsed into a plain
# string, so this check cannot be evaded the way Gate 1's shell-text parsing can.
#
# Classification (adversarial review, 2026-07-17 -- CONFIRMED BUG, fixed here): a plain
# `-notmatch '@oxfordra\.net$'` SUFFIX check misclassified "attacker@evilhost.com@oxfordra.net"
# as INTERNAL, because the whole string ends with the right substring even though it is not
# a clean oxfordra.net address -- a complete, zero-authorization bypass of this entire
# mechanism. Requiring EXACTLY one '@' and an EXACT (not suffix) domain match closes it:
# ambiguous/malformed shapes (0 or 2+ '@' characters) are treated as EXTERNAL, the
# conservative/fail-closed direction, never as a free pass.
function Test-IsInternalRecipient {
    param([string]$Address)
    $atCount = ([regex]::Matches($Address, '@')).Count
    if ($atCount -ne 1) { return $false }
    $domain = $Address.Substring($Address.IndexOf('@') + 1)
    return $domain -ieq 'oxfordra.net'
}

$allRecipients = @($To -split ';') + @($Cc -split ';') |
    ForEach-Object { $_.Trim() } | Where-Object { $_ } | Select-Object -Unique
$externalRecipients = @($allRecipients | Where-Object { -not (Test-IsInternalRecipient $_) })

# R-05 ordering: the early dedup lookup may only skip the stuck verdict for an INTERNAL-only send. An external
# recipient reaches the outbound check below, which consumes a single-use authorization; a run that is stuck and
# already resolved (duplicate / unknown) must not spend one, so it keeps the original exit 3 with the token intact.
if ($stuckMsg -and $EarlyResolved -and $externalRecipients.Count -gt 0) {
    Write-Log "ERROR" $stuckMsg
    exit 3
}

# --- ATTACHMENT x EXTERNAL RECIPIENT (2026-09-18) -- fail-closed, deliberately strict.
# The outbound-action check below authorizes RECIPIENTS. It has no view of file
# CONTENT, and an attachment bypasses every content scan the fleet has: the
# confidentiality hooks inspect commands and page sources, never a file handed
# straight to Outlook. That makes "external recipient + arbitrary file" the one
# path by which an unscanned document could leave the firm under automation --
# precisely what Hard Invariant 3 exists to prevent.
# Per the ORA routing canon every legitimate scheduled/automated send is
# internal-only (ggoldberg@ / egoldberg@), so refusing the COMBINATION costs no
# real automation. It is also strictly more conservative than the status quo,
# where this script could not attach anything at all.
if ($ResolvedAttachments.Count -gt 0 -and $externalRecipients.Count -gt 0) {
    Write-Log "ERROR" "ATTACHMENT-CHECK: refusing to attach $($ResolvedAttachments.Count) file(s) to a send with external recipient(s) [$($externalRecipients -join ', ')] -- this send path is internal-only for attachments"
    exit 5
}

if ($externalRecipients.Count -gt 0) {
    $sessionId = $env:CLAUDE_CODE_SESSION_ID
    if (-not $sessionId) {
        # No session context = no override is reachable at all (mirrors
        # git-prepush-doctrine-gate.py's identical fail-closed rule for a bare-terminal
        # push). Per the ORA routing canon every legitimate scheduled/automated send is
        # internal-only, so this never fires for real automation -- only for a genuine,
        # unauthorized external send attempt with no live session backing it.
        Write-Log "ERROR" "OUTBOUND-CHECK: external recipient(s) [$($externalRecipients -join ', ')] present but no CLAUDE_CODE_SESSION_ID in environment -- no override reachable, refusing to send"
        exit 5
    }
    $checkScript = "C:\Users\Owner\.claude\hooks\lib\check_external_send.py"
    # Recipients travel one-per-line on STDIN, never as a CLI argument (adversarial review,
    # 2026-07-17 -- CONFIRMED BUG, fixed here): PowerShell's native-argument marshaling to
    # an external process silently stripped an embedded double-quote from a --recipients
    # value before python ever saw it, so the value the check authorized could differ from
    # the value that would actually reach $Mail.To below. A pipe is not argument-parsed.
    $recipientsStdin = ($externalRecipients -join "`n")
    # check_external_send.py writes ITS decision to stderr on BOTH the allow and deny path
    # (by design, for logging). With the script-scoped $ErrorActionPreference="Stop", a
    # native command's stderr captured via `2>&1` becomes a terminating ErrorRecord in
    # PowerShell -- so a LEGITIMATE, AUTHORIZED send would have hit the catch block below
    # and been wrongly DENIED, purely because the check logged its own success. Found via
    # -WhatIf testing before this ever reached production. Toggling ErrorActionPreference
    # to Continue for just this call fixes it: stderr text flows into $checkOutput as plain
    # strings, and $LASTEXITCODE (not an exception) is what actually decides allow/deny.
    $prevEAP = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $checkOutput = $recipientsStdin | & python $checkScript --session $sessionId 2>&1
        $checkExitCode = $LASTEXITCODE
    } catch {
        # A validator we cannot run cannot authorize anything -- fail closed exactly like
        # ora-autonomy-gate.py's own broken-module handling (TOKEN_CONTRACT_LOADED=$false).
        # This now only fires for a REAL invocation failure (e.g. python missing entirely).
        Write-Log "ERROR" "OUTBOUND-CHECK: could not run check_external_send.py ($($_.Exception.Message)) -- treating as NOT authorized (fail-closed)"
        exit 5
    } finally {
        $ErrorActionPreference = $prevEAP
    }
    if ($checkExitCode -ne 0) {
        Write-Log "ERROR" "OUTBOUND-CHECK: DENIED for external recipient(s) [$($externalRecipients -join ', ')] -- $($checkOutput -join ' | ')"
        exit 5
    }
    Write-Log "OK" "OUTBOUND-CHECK: authorized external recipient(s) [$($externalRecipients -join ', ')] -- $($checkOutput -join ' | ')"
}

# --- Act on the early dedup lookup (see the Preflight section above). Runs after every argument, attachment and
# outbound-recipient check, and before the dry-run exit and any Outlook work. The authoritative check-then-intent
# under the mutex (Enter-DedupGate) still runs in the send loop for every run that proceeds, so a race between the
# lookup above and the later SEND-INTENT write is closed there. SENT -> exit 0; UNKNOWN -> exit 6; unreadable -> exit 6.
if ($EarlyDedup) {
    if ($EarlyDedup.State -eq 'SENT') {
        Write-Log "OK" "DEDUP-SKIP: key=$DedupKey already sent at $($EarlyDedup.At) -- not re-sending subject=`"$Subject`"$TagLog"
        exit 0
    }
    if ($EarlyDedup.State -eq 'UNKNOWN') {
        Write-Log "ERROR" "DEDUP-BLOCK: key=$DedupKey prior send state UNKNOWN at $($EarlyDedup.At) -- refusing (exit 6). Check Outlook Sent Items by hand; only if the message is absent may a human re-run with -ForceResend.$TagLog"
        exit 6
    }
    if ($EarlyDedup.State -eq 'UNREADABLE') {
        $why = "DEDUP-UNAVAILABLE: the send-log could not be read, so a prior send for this key cannot be ruled out"
        # The exit-3 diagnostic would otherwise be lost: this run was stuck AND unreadable, and exits 6.
        # Console first (the log may be the unwritable thing), then the log when it can be written.
        if ($stuckMsg) {
            [Console]::Error.WriteLine("WARN: $stuckMsg (preflight verdict superseded by the unreadable send-log)")
            Write-Log "WARN" "$stuckMsg (preflight verdict superseded by the unreadable send-log)$TagLog" | Out-Null
        }
        [Console]::Error.WriteLine($why)
        Write-Log "ERROR" "$why -- refusing (exit 6). Check Outlook Sent Items by hand; a human may re-run with -ForceResend once the message is confirmed absent.$TagLog"
        exit 6
    }
}

if ($WhatIf -and -not $Simulating) {
    $ccLog = if ($Cc) { $Cc } else { "none" }
    $dedupLog = if ($ContractMode) { " dedup=" + (Get-DedupState -Path $LogPath -Key $DedupKey).State } else { "" }
    Write-Log "OK" "DRY RUN: would send to=$To cc=$ccLog subject=`"$Subject`"$AttachLog$dedupLog$TagLog (no Outlook COM call made)"
    exit 0
}

function Invoke-OutlookSend {
    # $AttachJoined is a '|'-delimited string of ALREADY-RESOLVED absolute paths, not an
    # array: an array passed as an -ArgumentList element is splatted into the remaining job
    # parameters by PowerShell, which would silently drop or misbind attachments.
    #
    # R-05 (M19): the job appends phase markers to a per-call status file. 'invoked' is on
    # disk BEFORE Send() is called (AppendAllText has written and closed the file), so a
    # Send() that ran can never be reported as "not invoked". Stop-Job cannot recall a
    # message Outlook already accepted. That is why a post-invoke timeout is exit 6, never 4.
    param($To, $Cc, $Subject, $Body, $BodyFormat, $AttachJoined, [string]$SimMode, [int]$TimeoutSec)
    $statusPath = Join-Path ([System.IO.Path]::GetTempPath()) ("ora-send-" + [guid]::NewGuid().ToString("N") + ".status")
    $job = Start-Job -ScriptBlock {
        param($To, $Cc, $Subject, $Body, $BodyFormat, $AttachJoined, $StatusPath, $SimMode)
        $ErrorActionPreference = "Stop"
        function Mark([string]$Phase) { [System.IO.File]::AppendAllText($StatusPath, $Phase + "`n") }
        Mark 'started'
        try {
            if ($SimMode) {
                if ($SimMode -eq 'hang-before-send') { Start-Sleep -Seconds 60 }
                # Uninterruptible: Stop-Job cannot cut a .NET call short. The stop lands once the call
                # returns, at the next pipeline boundary (Mark 'invoked'), so Send() is never reached.
                if ($SimMode -eq 'block-before-send') { [System.Threading.Thread]::Sleep(8000) }
                # The ordering guard: ONE uninterruptible call that blocks past the timeout and then
                # writes 'invoked' itself (what a blocked COM call that proceeds into Send() looks
                # like to the parent). Only a marker read made AFTER Stop-Job returns can see it.
                if ($SimMode -eq 'invoke-during-stop') {
                    Add-Type -TypeDefinition 'public static class OraSimHelper { public static void SleepThenAppend(string path, int ms, string text) { System.Threading.Thread.Sleep(ms); System.IO.File.AppendAllText(path, text); } }'
                    [OraSimHelper]::SleepThenAppend($StatusPath, 8000, "invoked`n")
                }
                if ($SimMode -eq 'throw-before-send') { throw (New-Object System.Runtime.InteropServices.COMException('simulated COM failure before Send()', -2147467259)) }
                if ($SimMode -eq 'slow-ok') { Start-Sleep -Seconds 2 }
            } else {
                $Outlook = New-Object -ComObject Outlook.Application
                $Mail = $Outlook.CreateItem(0)  # 0 = olMailItem
                $Mail.To = $To
                if ($Cc) { $Mail.CC = $Cc }
                $Mail.Subject = $Subject
                if ($BodyFormat -eq "html") { $Mail.HTMLBody = $Body } else { $Mail.Body = $Body }
                if ($AttachJoined) {
                    foreach ($p in ($AttachJoined -split '\|')) {
                        if ($p) { $Mail.Attachments.Add($p) | Out-Null }
                    }
                }
            }
        } catch {
            Mark ('error-before 0x{0:X8}' -f $_.Exception.HResult)
            throw
        }
        Mark 'invoked'
        try {
            if ($SimMode) {
                if ($SimMode -eq 'hang-after-send') { Start-Sleep -Seconds 60 }
                if ($SimMode -eq 'throw-at-send') { throw (New-Object System.Runtime.InteropServices.COMException('simulated failure inside Send()', -2147467259)) }
                if ($SimMode -eq 'reject-at-send') { throw (New-Object System.Runtime.InteropServices.COMException('simulated RPC_E_CALL_REJECTED', -2147418111)) }
            } else {
                $Mail.Send()
            }
        } catch {
            Mark ('error-at-send 0x{0:X8}' -f $_.Exception.HResult)
            throw
        }
        Mark 'returned'
        if ($SimMode -eq 'returned-late') { Start-Sleep -Seconds 60 }
    } -ArgumentList $To, $Cc, $Subject, $Body, $BodyFormat, $AttachJoined, $statusPath, $SimMode

    $completed = [bool](Wait-Job $job -Timeout $TimeoutSec)
    $errVar = $null
    $jobEnded = $false
    if ($completed) {
        Receive-Job $job -ErrorVariable errVar -ErrorAction SilentlyContinue | Out-Null
        # A job that ended Failed/Stopped/Broken without surfacing an error record is still not a send.
        $jobEnded = ($job.State -ne 'Completed')
    } else {
        Stop-Job $job
        # Stop-Job does not interrupt a blocked .NET/COM call: it waits for that call to return
        # (up to PowerShell's own ~120s cap), then the stop lands at the next pipeline boundary.
        # A blocked call that proceeds into Send() therefore leaves 'invoked' on disk, so the
        # markers are read only AFTER Stop-Job returns (case L25 guards this ordering), plus one
        # second of grace for any append in flight.
        Start-Sleep -Milliseconds 1000
    }
    Remove-Job $job -Force
    $phases = Read-SendPhases -Path $statusPath
    Remove-Item -LiteralPath $statusPath -Force -ErrorAction SilentlyContinue
    $outcome = Resolve-SendOutcome -TimedOut (-not $completed) -JobErrored ([bool]$errVar -or $jobEnded) -Phases $phases
    if ($errVar) { $outcome.Message = $errVar[0].Exception.Message }
    return $outcome
}

# --- COLD-START GUARD (2026-09-23) -- root cause of the recurring "TIMEOUT: COM call exceeded 15s".
# When OUTLOOK.EXE is not running, New-Object -ComObject Outlook.Application LAUNCHES Outlook, which
# takes well over the 15s job budget. The job is then killed (Outlook survives, now running), the
# send is lost, and the NEXT send minutes later succeeds -- exactly the "worked earlier, fails now,
# works again" pattern. Evidence: 2026-09-23 timeouts at 16:40:52/16:41:29, OUTLOOK.EXE StartTime
# 16:41:17, next send OK at 16:46. Fix: start Outlook explicitly and wait for COM to answer BEFORE
# the 15s-bounded send. No effect when Outlook is already running.
function Ensure-OutlookReady {
    if (Get-Process OUTLOOK -ErrorAction SilentlyContinue) { return }
    Write-Log "WARN" "OUTLOOK-COLDSTART: no OUTLOOK process; launching and waiting up to 120s for COM"
    try {
        $exe = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\OUTLOOK.EXE' -ErrorAction Stop).'(default)'
        Start-Process -FilePath $exe
    } catch {
        try { Start-Process -FilePath 'outlook.exe' } catch { Write-Log "WARN" "OUTLOOK-COLDSTART: could not launch Outlook ($($_.Exception.Message))" }
    }
    $deadline = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 3
        $p = Get-Process OUTLOOK -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($p -and $p.Responding) {
            $j = Start-Job -ScriptBlock { $o = New-Object -ComObject Outlook.Application; $null = $o.Session.CurrentUser.Name; 'ok' }
            if (Wait-Job $j -Timeout 10) {
                $r = Receive-Job $j -ErrorAction SilentlyContinue
                Remove-Job $j -Force
                if ($r -eq 'ok') { Write-Log "OK" "OUTLOOK-COLDSTART: COM ready"; return }
            } else { Stop-Job $j; Remove-Job $j -Force }
        }
    }
    Write-Log "WARN" "OUTLOOK-COLDSTART: COM not ready after 120s; attempting send anyway"
}

# --- R-05 legacy quarantine. A caller WITHOUT a dedup key may still carry the old "retry once
# on any non-zero exit" text. For 60 minutes after a SEND-STATE-UNKNOWN, refuse an identical
# subject to the same recipient so that retry cannot double-send. Keyed callers get the stronger
# per-period dedup inside the send loop instead. An unreadable send-log fails CLOSED.
if ($ForceResend -and -not $ContractMode) {
    Write-Log "WARN" "FORCE-RESEND: dedup and quarantine bypassed by -ForceResend (human-directed re-run only; a scheduled spec must never pass it)$TagLog"
}
if (-not $ContractMode -and -not $ForceResend) {
    $qs = Get-QuarantineState -Path $LogPath -Hash $SubjectHash -Recipient $To -Minutes $QuarantineMinutes
    if ($qs.State -eq 'UNREADABLE') {
        Write-Log "ERROR" "QUARANTINE: the send-log (or its unknown-send marker) could not be read, so a prior SEND-STATE-UNKNOWN for this subject cannot be ruled out -- refusing (exit 6). Check Outlook Sent Items by hand.$TagLog"
        exit 6
    }
    if ($qs.State -eq 'QUARANTINED') {
        Write-Log "ERROR" "QUARANTINE: an identical subject to this recipient ended SEND-STATE-UNKNOWN at $($qs.Stamp) (within $QuarantineMinutes min) -- refusing (exit 6) so a retry cannot double-send. Check Outlook Sent Items by hand.$TagLog"
        exit 6
    }
    if (-not (Test-RecordChannelsAvailable -LogFile $LogPath -Hash $SubjectHash)) {
        # Neither the send-log nor its sidecar marker can be written: if this send ended SEND-STATE-UNKNOWN
        # nothing would record it and a legacy "retry on non-zero" caller would double-send. Refuse now, nothing sent.
        $why = "RECORD-CHANNELS-UNAVAILABLE: neither the send-log nor its unknown-send sidecar marker can be written, so a send whose state turns out unknown could not be recorded -- refusing before Send() (exit 6, nothing sent). Fix the permissions or space on the send-log directory; a human may re-run with -ForceResend only after checking Outlook Sent Items."
        [Console]::Error.WriteLine($why)
        Write-Log "ERROR" "$why$TagLog"
        exit 6
    }
}

if (-not $Simulating) { Ensure-OutlookReady }
$attemptNo = 0
while ($true) {
    $attemptNo++
    if ($ContractMode) {
        # A -ForceResend caller (human only) passes -Force: no check, but the lock, the FORCE-RESEND
        # reset and the intent all still happen, so a crash stays visible and a concurrent fire is blocked.
        $gate = if ($ForceResend) { Enter-DedupGate -Key $DedupKey -Force } else { Enter-DedupGate -Key $DedupKey }
        if ($gate.State -eq 'SENT') {
            Write-Log "OK" "DEDUP-SKIP: key=$DedupKey already sent at $($gate.At) -- not re-sending subject=`"$Subject`"$TagLog"
            exit 0
        }
        if ($gate.State -eq 'UNKNOWN') {
            Write-Log "ERROR" "DEDUP-BLOCK: key=$DedupKey prior send state UNKNOWN at $($gate.At) -- refusing (exit 6). Check Outlook Sent Items by hand; only if the message is absent may a human re-run with -ForceResend.$TagLog"
            exit 6
        }
        if ($gate.State -ne 'PROCEED') {
            # UNAVAILABLE: fail CLOSED. Always on the console, and in the log when it can be written.
            [Console]::Error.WriteLine($gate.Reason)
            Write-Log "ERROR" "$($gate.Reason) -- refusing (exit 6). Check Outlook Sent Items by hand; a human may re-run with -ForceResend once the message is confirmed absent.$TagLog"
            exit 6
        }
    }
    $sim = $null
    if ($Simulating) { $sim = if ($SimPlan.Count -ge $attemptNo) { $SimPlan[$attemptNo - 1] } else { $SimPlan[-1] } }
    if ($WhatIf -and -not $sim) {
        # Belt and braces: -WhatIf must never reach a real COM send.
        Write-Log "ERROR" "internal: -WhatIf reached the send loop without a simulation step -- refusing"
        exit 1
    }
    $o = Invoke-OutlookSend -To $To -Cc $Cc -Subject $Subject -Body $Body -BodyFormat $BodyFormat -AttachJoined $AttachJoined -SimMode $sim -TimeoutSec $TimeoutSec
    $retryNote = if ($attemptNo -gt 1) { " (after 1 retry)" } else { "" }
    if ($o.Code -eq 0) {
        $bytes = [System.Text.Encoding]::UTF8.GetByteCount($Body)
        $ccLog = if ($Cc) { $Cc } else { "none" }
        Write-Log "OK" "Sent to=$To cc=$ccLog subject=`"$Subject`" bytes=$bytes format=$BodyFormat$AttachLog$retryNote$TagLog"
        exit 0
    }
    if ($o.Code -eq 6) {
        Write-Log "ERROR" "SEND-STATE-UNKNOWN: $($o.Reason) -- the message MAY have been sent. Do NOT retry (exit 6); check Outlook Sent Items by hand. to=$To$TagLog"
        if (-not $script:LogWriteOk) {
            # The log append failed (lock, ACL, full disk), so the legacy quarantine would never see this send.
            # Fail closed through a second channel: a sidecar marker next to this run's log.
            $mk = Write-UnknownMarker -LogFile $LogPath -Hash $SubjectHash -Recipient $To
            $mkMsg = if ($mk) { "recorded in the sidecar marker $(Get-UnknownMarkerPath -LogFile $LogPath -Hash $SubjectHash)" } else { "the sidecar marker could not be written either, so NOTHING records this send" }
            [Console]::Error.WriteLine("SEND-STATE-UNKNOWN could not be written to the send-log; $mkMsg. The message MAY have been sent: do NOT retry, check Outlook Sent Items by hand.")
        }
        exit 6
    }
    if ($o.Code -eq 4) {
        $msg = "TIMEOUT: COM call exceeded ${TimeoutSec}s before Send() was invoked (Outlook likely blocked; retry-safe)"
    } elseif ($o.State -eq 'REJECTED') {
        # Send() WAS called and Outlook refused it (RPC_E_CALL_REJECTED): retry-safe because the
        # callee rejected the call, not because it was never made. Say so in the audit trail.
        $msg = "Outlook COM failed (HRESULT=0x80010001): $($o.Message) -- Send() was rejected by Outlook (RPC_E_CALL_REJECTED; retry-safe)"
    } else {
        $hrText = if ($null -ne $o.HResult) { "0x{0:X8}" -f $o.HResult } else { "n/a" }
        $msg = "Outlook COM failed (HRESULT=$hrText): $($o.Message) -- Send() was not invoked (retry-safe)"
    }
    # Contract mode: the script owns the one retry of 2/4 (Send() never ran, or the callee refused it),
    # so the caller retries nothing. Legacy mode keeps only the pre-R-05 RPC_E_CALL_REJECTED retry.
    # Exit 6 returned above and is never retried.
    $retryable = ($attemptNo -eq 1) -and ($ContractMode -or (($o.Code -eq 2) -and ($o.HResult -eq $RPC_E_CALL_REJECTED)))
    if ($retryable) {
        Write-Log "WARN" "$msg -- retrying once in ${RetryDelaySec}s$TagLog"
        Start-Sleep -Seconds $RetryDelaySec
        continue
    }
    $exhausted = if ($attemptNo -gt 1) { " (retry exhausted)" } else { "" }
    Write-Log "ERROR" "$msg$exhausted$TagLog"
    exit $o.Code
}
