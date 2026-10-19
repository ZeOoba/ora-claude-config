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
    Email subject line.

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
    Exit codes: 0 = sent OK, 1 = usage error, 2 = Outlook COM failure,
    3 = Outlook stuck on startup wizard (preflight-detected, no COM attempted),
    4 = COM call timed out (>15s, Outlook likely blocked), 5 = external recipient(s) not
    authorized (see OUTBOUND-ACTION CHECK below).
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
    [Parameter(Mandatory=$true)][string]$Subject,
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
# Tests redirect the audit log, but ONLY under -WhatIf. A real send always writes
# the canonical log, so this can never be used to blind the audit trail.
if ($WhatIf -and $env:ORA_SEND_LOG_PATH) { $LogPath = $env:ORA_SEND_LOG_PATH }
# R-05 test seam: skip the Outlook-process preflight so a dry run does not depend on whether
# a real Outlook happens to be open, busy or on a wizard (2026-10-18: two existing dry-run
# cases exited 3 because the live Outlook was momentarily not Responding). Honored ONLY under
# -WhatIf, like ORA_SEND_LOG_PATH above.
$SkipPreflight = [bool]($WhatIf -and $env:ORA_SEND_SKIP_PREFLIGHT -eq '1')
# R-05 test seams for the send job, honored ONLY under -WhatIf (every line that reads one
# names $WhatIf; maintenance/_tests/test_send_contract_suite.py S1 enforces that).
# ORA_SEND_SIMULATE swaps the Outlook COM objects inside the send job for a scripted fake,
# as a comma list with one step per attempt. It is the only way to exercise the
# timeout/marker classification without Outlook.
$SimRaw     = if ($WhatIf) { [string]$env:ORA_SEND_SIMULATE } else { "" }
$TimeoutRaw = if ($WhatIf) { [string]$env:ORA_SEND_TIMEOUT_SEC } else { "" }
$DelayRaw   = if ($WhatIf) { [string]$env:ORA_SEND_RETRY_DELAY_SEC } else { "" }
$SimPlan = @($SimRaw -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$Simulating = $SimPlan.Count -gt 0
# A simulated run writes a REAL-looking '[OK] Sent' line. It must never land in the canonical
# log, where every '[OK] Sent' reader (and the contract-mode dedup) would count it as a delivery.
# Checked before any Write-Log call, so this refusal cannot touch the canonical log either.
if ($Simulating -and -not $env:ORA_SEND_LOG_PATH) {
    [Console]::Error.WriteLine("ORA_SEND_SIMULATE requires ORA_SEND_LOG_PATH: a simulated send must never write the canonical send log")
    exit 1
}
$TimeoutSec = 15
$RetryDelaySec = 5
if ($Simulating) {
    $n = 0
    if ([int]::TryParse($TimeoutRaw, [ref]$n) -and $n -ge 1 -and $n -le 15) { $TimeoutSec = $n }
    if ([int]::TryParse($DelayRaw, [ref]$n) -and $n -ge 0 -and $n -le 10) { $RetryDelaySec = $n }
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
    for ($w = 1; $w -le 10; $w++) {
        try { Add-Content -Path $LogPath -Value $line -Encoding UTF8 -ErrorAction Stop; break } catch { if ($w -lt 10) { Start-Sleep -Milliseconds ([Math]::Min(20 * $w, 100)) } }
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
    param([string]$Path, [string]$Hash, [string]$Recipient, [int]$Minutes)
    $none = @{ State = 'NONE'; Stamp = $null }
    if ($Hash -cnotmatch '\A[0-9a-f]{16}\z') { return $none }
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
# --- end R-05 helpers ---

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
# touched. Same exit code as the other argument faults above (1) -- the exit
# contract (see .NOTES) is deliberately NOT widened by this check: it reuses exit 1.
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
$existingOutlook = if ($SkipPreflight) { $null } else { Get-Process OUTLOOK -ErrorAction SilentlyContinue }
if ($existingOutlook) {
    foreach ($proc in $existingOutlook) {
        if ((-not $proc.Responding) -or ($proc.MainWindowTitle -match 'Welcome to Microsoft Outlook|Choose Profile|New Profile|Profile')) {
            Write-Log "ERROR" "Outlook stuck on startup wizard (PID=$($proc.Id), title='$($proc.MainWindowTitle)') - human must dismiss"
            exit 3
        }
    }
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

if ($WhatIf -and -not $Simulating) {
    $ccLog = if ($Cc) { $Cc } else { "none" }
    Write-Log "OK" "DRY RUN: would send to=$To cc=$ccLog subject=`"$Subject`"$AttachLog$TagLog (no Outlook COM call made)"
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
if ($ForceResend) {
    Write-Log "WARN" "FORCE-RESEND: dedup and quarantine bypassed by -ForceResend (human-directed re-run only; a scheduled spec must never pass it)$TagLog"
}
if (-not $ContractMode -and -not $ForceResend) {
    $qs = Get-QuarantineState -Path $LogPath -Hash $SubjectHash -Recipient $To -Minutes $QuarantineMinutes
    if ($qs.State -eq 'UNREADABLE') {
        Write-Log "ERROR" "QUARANTINE: the send-log could not be read, so a prior SEND-STATE-UNKNOWN for this subject cannot be ruled out -- refusing (exit 6). Check Outlook Sent Items by hand.$TagLog"
        exit 6
    }
    if ($qs.State -eq 'QUARANTINED') {
        Write-Log "ERROR" "QUARANTINE: an identical subject to this recipient ended SEND-STATE-UNKNOWN at $($qs.Stamp) (within $QuarantineMinutes min) -- refusing (exit 6) so a retry cannot double-send. Check Outlook Sent Items by hand.$TagLog"
        exit 6
    }
}

if (-not $Simulating) { Ensure-OutlookReady }
$attemptNo = 0
while ($true) {
    $attemptNo++
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
    $retryable = ($attemptNo -eq 1) -and (($o.Code -eq 2) -and ($o.HResult -eq $RPC_E_CALL_REJECTED))
    if ($retryable) {
        Write-Log "WARN" "$msg -- retrying once in ${RetryDelaySec}s$TagLog"
        Start-Sleep -Seconds $RetryDelaySec
        continue
    }
    $exhausted = if ($attemptNo -gt 1) { " (retry exhausted)" } else { "" }
    Write-Log "ERROR" "$msg$exhausted$TagLog"
    exit $o.Code
}
