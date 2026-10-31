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
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$LogPath = "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-log.txt"
# Tests redirect the audit log, but ONLY under -WhatIf. A real send always writes
# the canonical log, so this can never be used to blind the audit trail.
if ($WhatIf -and $env:ORA_SEND_LOG_PATH) { $LogPath = $env:ORA_SEND_LOG_PATH }

# Cap chosen to fail FAST with a readable message rather than let Exchange reject
# the message with an opaque COM HRESULT (typical Exchange ceiling is 25 MB).
$MaxAttachmentBytes = 20MB

function Write-Log {
    param([string]$Level, [string]$Message)
    $ts = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
    $line = "$ts [$Level] $Message"
    try { Add-Content -Path $LogPath -Value $line -Encoding UTF8 } catch {}
    # -ErrorAction Continue overrides the script-scoped $ErrorActionPreference="Stop" for this
    # call only; without it, Write-Error terminates the script before the caller's `exit N`
    # line runs (bug found 2026-07-07: every ERROR path was silently collapsing to exit code 1).
    if ($Level -eq "ERROR") { Write-Error $Message -ErrorAction Continue } else { Write-Output $line }
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

# --- Validate attachments (2026-09-18) ---
# Fail-closed by design: a message whose body promises an attachment must never
# go out without it, so ANY bad entry rejects the whole send before Outlook is
# touched. Same exit code as the other argument faults above (1) -- the exit
# contract (0 sent / 1 bad args / 2 COM / 3 wizard / 4 timeout / 5 outbound
# refused) is deliberately NOT widened, so no existing caller changes meaning.
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
$existingOutlook = Get-Process OUTLOOK -ErrorAction SilentlyContinue
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

if ($WhatIf) {
    $ccLog = if ($Cc) { $Cc } else { "none" }
    Write-Log "OK" "DRY RUN: would send to=$To cc=$ccLog subject=`"$Subject`"$AttachLog (no Outlook COM call made)"
    exit 0
}

function Invoke-OutlookSend {
    # $AttachJoined is a '|'-delimited string of ALREADY-RESOLVED absolute paths,
    # not an array: an array passed as the last -ArgumentList element is splatted
    # into the remaining job parameters by PowerShell, which would silently drop
    # or misbind attachments. '|' cannot occur in a Windows filename.
    param($To, $Cc, $Subject, $Body, $BodyFormat, $AttachJoined)
    $job = Start-Job -ScriptBlock {
        param($To, $Cc, $Subject, $Body, $BodyFormat, $AttachJoined)
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
        $Mail.Send()
    } -ArgumentList $To, $Cc, $Subject, $Body, $BodyFormat, $AttachJoined

    if (Wait-Job $job -Timeout 15) {
        $errVar = $null
        Receive-Job $job -ErrorVariable errVar -ErrorAction SilentlyContinue | Out-Null
        Remove-Job $job -Force
        if ($errVar) { return @{ Success = $false; Error = $errVar[0] } }
        return @{ Success = $true }
    } else {
        Stop-Job $job; Remove-Job $job -Force
        return @{ Success = $false; Timeout = $true }
    }
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

# After a timeout the killed job may already have queued the message. Before any retry, look for the
# same subject in Sent Items / Outbox (last 10 min) so a retry cannot double-send.
function Test-AlreadyQueued {
    param($Subject)
    $j = Start-Job -ScriptBlock {
        param($Subject)
        $o = New-Object -ComObject Outlook.Application
        $since = (Get-Date).AddMinutes(-10)
        $q = $Subject.Replace("'", "''")
        foreach ($fid in 5, 4) {   # 5 = Sent Items, 4 = Outbox
            $items = $o.Session.GetDefaultFolder($fid).Items.Restrict("[Subject] = '$q'")
            foreach ($it in $items) { if ($it.CreationTime -ge $since) { return 'found' } }
        }
        'none'
    } -ArgumentList $Subject
    if (Wait-Job $j -Timeout 20) {
        $r = Receive-Job $j -ErrorAction SilentlyContinue
        Remove-Job $j -Force
        return ($r -eq 'found')
    }
    Stop-Job $j; Remove-Job $j -Force
    return $false
}

Ensure-OutlookReady
$attempt = Invoke-OutlookSend -To $To -Cc $Cc -Subject $Subject -Body $Body -BodyFormat $BodyFormat -AttachJoined $AttachJoined

if ($attempt.Timeout) {
    Write-Log "ERROR" "TIMEOUT: COM call exceeded 15s (Outlook likely blocked)"
    if (Test-AlreadyQueued $Subject) {
        $bytes = [System.Text.Encoding]::UTF8.GetByteCount($Body)
        $ccLog = if ($Cc) { $Cc } else { "none" }
        Write-Log "OK" "Sent to=$To cc=$ccLog subject=`"$Subject`" bytes=$bytes format=$BodyFormat$AttachLog (verified in Sent Items/Outbox after timeout; no retry)"
        exit 0
    }
    Start-Sleep -Seconds 10
    $retry = Invoke-OutlookSend -To $To -Cc $Cc -Subject $Subject -Body $Body -BodyFormat $BodyFormat -AttachJoined $AttachJoined
    if ($retry.Success) {
        $bytes = [System.Text.Encoding]::UTF8.GetByteCount($Body)
        $ccLog = if ($Cc) { $Cc } else { "none" }
        Write-Log "OK" "Sent to=$To cc=$ccLog subject=`"$Subject`" bytes=$bytes format=$BodyFormat$AttachLog (after timeout retry)"
        exit 0
    }
    Write-Log "ERROR" "TIMEOUT/FAIL on retry after cold-start guard (Outlook blocked, likely a modal dialog)"
    exit 4
}
elseif (-not $attempt.Success) {
    $hresult = $attempt.Error.Exception.HResult
    if ($hresult -eq 0x80010001) {
        # RPC_E_CALL_REJECTED - one bounded retry after a short cooldown
        Start-Sleep -Seconds 5
        $retry = Invoke-OutlookSend -To $To -Cc $Cc -Subject $Subject -Body $Body -BodyFormat $BodyFormat -AttachJoined $AttachJoined
        if ($retry.Timeout) {
            Write-Log "ERROR" "TIMEOUT on retry: COM call exceeded 15s (Outlook likely blocked)"
            exit 4
        } elseif (-not $retry.Success) {
            Write-Log "ERROR" ("Outlook COM failed (retry exhausted, HRESULT=0x{0:X8}): {1}" -f $retry.Error.Exception.HResult, $retry.Error.Exception.Message)
            exit 2
        } else {
            $bytes = [System.Text.Encoding]::UTF8.GetByteCount($Body)
            $ccLog = if ($Cc) { $Cc } else { "none" }
            Write-Log "OK" "Sent to=$To cc=$ccLog subject=`"$Subject`" bytes=$bytes format=$BodyFormat$AttachLog (after 1 retry)"
            exit 0
        }
    } else {
        Write-Log "ERROR" ("Outlook COM failed (HRESULT=0x{0:X8}): {1}" -f $hresult, $attempt.Error.Exception.Message)
        exit 2
    }
}
else {
    $bytes = [System.Text.Encoding]::UTF8.GetByteCount($Body)
    $ccLog = if ($Cc) { $Cc } else { "none" }
    Write-Log "OK" "Sent to=$To cc=$ccLog subject=`"$Subject`" bytes=$bytes format=$BodyFormat$AttachLog"
    exit 0
}
