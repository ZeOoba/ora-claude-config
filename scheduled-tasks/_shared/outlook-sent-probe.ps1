<#
.SYNOPSIS
    Ask Outlook whether a message with today's subject is ALREADY in Sent Items.

.DESCRIPTION
    Independent SECOND LAYER of the scheduled-task double-fire guard, for blocks
    that send email. Run it immediately BEFORE the COM send.

    block-sentinel.py is the primary guard, but its state file lives under
    Claude_Workspace\_state\ -- which is on OneDrive, and can therefore be lost,
    rolled back, or briefly unavailable to a sync conflict. This probe survives
    that: it asks the mail store itself, which is the actual record of what went
    out. Neither layer is sufficient alone; keep both.

    Background: on 2026-08-09 (Sunday) the machine was offline overnight, the
    fleet fired in a catch-up burst, and ora-am-brief fired twice -- Block B had
    already sent "ORA Daily Brief - Sunday, August 9 2026" to ggoldberg cc
    egoldberg at 09:06 ET when the second fire landed at 09:11 ET. Only a manual
    stand-down prevented a duplicate.

.PARAMETER Subject
    Subject to look for. Matching is NORMALIZED, not literal -- see -MatchMode.

.PARAMETER SubjectFile
    Path to a UTF-8 file containing the subject. PREFER THIS whenever the subject
    contains non-ASCII characters (em-dash, emoji). Passing such a subject as a
    literal through a Bash -> PowerShell command line mangles it silently; the
    sibling send-via-outlook.ps1 documents the same hazard for -Subject.

.PARAMETER OnDate
    Date to scan, "yyyy-MM-dd". Defaults to today in the machine's local time,
    which is ET on this host -- the same clock Outlook stamps SentOn with.

.PARAMETER MatchMode
    Normalized  (default) - fold em/en-dashes to "-", strip non-ASCII, collapse
                whitespace, casefold, strip benign leading automation tags
                ("[ORA]", "[ALERT]", "[ORA Command Center]"), then require the
                probe subject at POSITION 0 of what remains. Replies, forwards
                and manual corrections are rejected outright -- see
                Test-SubjectMatch for why each class is handled the way it is.
    Exact       - ordinal case-insensitive equality after trimming only.

    Normalized is the default on evidence, not taste. ora-am-brief's spec subject
    is written with an em-dash, but the message actually in the store on
    2026-08-09 reads "ORA Daily Brief - Sunday, August 9 2026" with a plain
    hyphen. An Exact match against the spec string would have MISSED the real
    sent item and waved a duplicate through -- the precise failure this probe
    exists to stop.

.PARAMETER Force
    Bypass the Sent-Items check entirely and return "PROCEED" (exit 0). This is the
    Layer-2 counterpart to block-sentinel.py's --force, without which a documented
    manual all-blocks re-run could re-publish Notion but could never re-send the
    email. Only a human-directed in-session re-run may pass it; a scheduled fire
    must never.

.PARAMETER MaxScan
    Safety cap on items examined (default 400). Sent Items is sorted SentOn
    descending, so the scan short-circuits as soon as it walks past OnDate;
    the cap only matters on a pathologically large same-day volume.

.OUTPUTS
    A JSON object on stdout, always.

.NOTES
    Exit codes:
      0  NOT FOUND   -> no matching message today; PROCEED with the send.
      10 FOUND       -> already sent today; SKIP the send and log it.
      1  PROBE ERROR -> could not reach Outlook / Sent Items.
      0  FORCED      -> -Force supplied; check bypassed (human-directed re-run only).

    FAIL-OPEN CONTRACT: on exit 1 the caller PROCEEDS with the send and records
    the gap in its run summary. This probe is a backstop behind block-sentinel.py,
    which has already returned PROCEED by the time we get here; suppressing a real
    brief because a probe broke would be a worse failure than a duplicate. Do not
    "harden" this into fail-closed without changing the primary guard too.

    THIS FILE IS DELIBERATELY ASCII-ONLY. PowerShell reads a BOM-less .ps1 as
    cp1252, so a literal em-dash or smart quote in the SOURCE is mangled before
    the regex ever runs -- the same hazard send-via-outlook.ps1 documents for
    subject lines. The dash/quote character classes below are therefore written
    with \u escapes. An earlier revision used literal characters and the em-dash
    case silently matched nothing; the self-test caught it. Keep it ASCII.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\outlook-sent-probe.ps1 `
        -SubjectFile "$env:TEMP\subj.txt"
    if ($LASTEXITCODE -eq 10) { "already sent -- skip" }

.EXAMPLE
    # Verify the matching logic without touching Outlook:
    powershell -ExecutionPolicy Bypass -File .\outlook-sent-probe.ps1 -SelfTest
#>
[CmdletBinding()]
param(
    [string]$Subject,
    [string]$SubjectFile,
    [string]$OnDate,
    [ValidateSet("Normalized", "Exact")]
    [string]$MatchMode = "Normalized",
    [int]$MaxScan = 400,
    [switch]$Force,
    [switch]$SelfTest
)

$ErrorActionPreference = "Stop"

function ConvertTo-ComparableSubject {
    param([string]$Text, [string]$Mode)
    if ($null -eq $Text) { return "" }
    if ($Mode -eq "Exact") { return $Text.Trim() }
    $s = $Text
    # Dash family -> ASCII hyphen. The spec/store mismatch that motivated this probe.
    $s = $s -replace "[\u2010-\u2015\u2212\uFE58\uFE63\uFF0D]", "-"
    # Quote family -> ASCII, so a smart-quoted subject still matches.
    $s = $s -replace "[\u2018\u2019\u201A\u201B]", "'"
    $s = $s -replace "[\u201C\u201D\u201E\u201F]", '"'
    # Drop anything still non-ASCII (emoji status prefixes, NBSP, etc.).
    $s = $s -replace "[^ -~]", " "
    $s = ($s -replace "\s+", " ").Trim()
    return $s.ToLowerInvariant()
}

function Test-SubjectMatch {
    <#  Pure matching predicate -- the part that actually carries bug risk.
        Kept free of COM so -SelfTest can exercise it.

        A FALSE POSITIVE here suppresses a real report, which is worse than the
        duplicate this probe exists to stop. Two classes are therefore rejected
        outright before matching:

          * Replies and forwards ("Re:", "Fw:", "Fwd:"). A reply carries the stem
            verbatim, so a same-day reply would otherwise read as "already sent".
          * Manual corrections ("[CORRECTION]", "(corrected resend)"). These are a
            real recurring class in the send log -- the 2026-07-13 lease-expiration
            resend, the 2026-07-27 daily brief, the 2026-07-29 health guard. A
            correction sent earlier the same ET day must NOT cancel the scheduled
            send; if anything it is evidence the scheduled one still matters.

        Benign automation prefixes ("[ORA]", "[ALERT]", "[ORA Command Center]") are
        stripped rather than rejected, because the same producer legitimately varies
        them run to run -- ora-deal-aging-sla emitted its two 2026-08-09 subjects
        with and without a leading "[ORA]". After stripping, the stem must appear at
        POSITION 0, so a different producer whose subject merely contains the stem
        somewhere later does not match. #>
    param([string]$Candidate, [string]$Probe, [string]$Mode)

    $rawC = if ($null -eq $Candidate) { "" } else { $Candidate.Trim() }
    if ($Mode -ne "Exact") {
        # Reject-list: replies, forwards, manual corrections.
        if ($rawC -match '^\s*(re|fw|fwd)\s*:') { return $false }
        if ($rawC -match '(?i)\[\s*correction\s*\]') { return $false }
        if ($rawC -match '(?i)\(\s*corrected\s+resend\s*\)') { return $false }
    }

    $c = ConvertTo-ComparableSubject -Text $rawC -Mode $Mode
    $p = ConvertTo-ComparableSubject -Text $Probe -Mode $Mode
    if ([string]::IsNullOrWhiteSpace($p)) { return $false }
    if ($Mode -eq "Exact") { return [string]::Equals($c, $p, "OrdinalIgnoreCase") }

    # Strip benign leading automation tags, then anchor at position 0.
    $stripped = $c
    while ($stripped -match '^\[[^\]]*\]\s*') {
        $stripped = ($stripped -replace '^\[[^\]]*\]\s*', '').Trim()
    }
    return $stripped.StartsWith($p, "OrdinalIgnoreCase")
}

# --------------------------------------------------------------- self-test

if ($SelfTest) {
    $EM = [char]0x2014
    $CHECK = [char]0x2705
    $cases = @(
        # candidate (as it sits in the store)     , probe (as the task builds it)                    , mode        , expected
        @("ORA Daily Brief - Sunday, August 9 2026", "ORA Daily Brief $EM Sunday, August 9 2026"      , "Normalized", $true),
        @("ORA Daily Brief - Sunday, August 9 2026", "ORA Daily Brief"                                , "Normalized", $true),
        @("ORA Daily Brief - Sunday, August 9 2026", "ORA Daily Brief - Monday, August 10 2026"       , "Normalized", $false),
        @("ORA Cash Position - 2026-08-09"         , "ORA Cash Position - 2026-08-09"                 , "Normalized", $true),
        @("ORA Cash Position - 2026-08-09"         , "ORA Cash Position - 2026-08-10"                 , "Normalized", $false),
        @("$CHECK ORA Connector Pre-Flight - 2026-08-09", "ORA Connector Pre-Flight - 2026-08-09"     , "Normalized", $true),
        @("ORA  Daily   Brief - x"                 , "ORA Daily Brief - x"                            , "Normalized", $true),
        @("ora daily brief - x"                    , "ORA Daily Brief - x"                            , "Normalized", $true),
        @("ORA Daily Brief - Sunday, August 9 2026", "ORA Daily Brief $EM Sunday, August 9 2026"      , "Exact"     , $false),
        @("ORA Daily Brief - x"                    , ""                                               , "Normalized", $false),
        # A same-day REPLY carries the stem verbatim. Treating it as "already sent"
        # would suppress the real scheduled brief -- a false positive is worse than
        # the duplicate this probe exists to stop. An earlier revision blessed this
        # as $true; code review caught it.
        @("Re: ORA Daily Brief - Sunday, August 9 2026", "ORA Daily Brief - Sunday, August 9 2026"    , "Normalized", $false),
        @("Fwd: ORA Cash Position - 2026-08-09"        , "ORA Cash Position - 2026-08-09"             , "Normalized", $false),
        # Manual corrections are a real recurring class in the send log; one sent
        # earlier the same day must not cancel the scheduled send.
        @("[CORRECTION] ORA Daily Brief 2026-07-27 - 2 units already re-leased", "ORA Daily Brief"    , "Normalized", $false),
        @("ORA Lease Expiration Brief - 2026-07-13 (corrected resend)", "ORA Lease Expiration Brief - 2026-07-13", "Normalized", $false),
        # ...but a benign automation tag is STRIPPED, not rejected.
        @("[ALERT] ORA Cash Position - 2026-08-09"     , "ORA Cash Position - 2026-08-09"             , "Normalized", $true),
        # The stem must sit at position 0 after tag-stripping: a different producer
        # that merely CONTAINS the stem later in its subject must not match.
        @("Weekly rollup including ORA Cash Position - 2026-08-09", "ORA Cash Position - 2026-08-09"  , "Normalized", $false),
        @("ORA Inbox Pre-Brief - 2026-08-09 - 6 for triage, 1 RED", "ORA Inbox Pre-Brief - 2026-08-09", "Normalized", $true),
        # ora-deal-aging-sla really did double-send on 2026-08-09, and its two subjects
        # differ in BOTH the leading tag and the trailing headline because the spec lets
        # the run compose that text. A dated STEM must match both, or the probe would
        # have waved the 09:20 duplicate through. This is why matching is substring,
        # not prefix: the second subject carries a leading "[ORA]" the first lacks.
        @("Deal Aging SLA - 2026-08-09: 0 breaches - Patterson returned the 754 PSA marked final", "Deal Aging SLA - 2026-08-09", "Normalized", $true),
        @("[ORA] Deal Aging SLA - 2026-08-09 - 0 breaches, 1 posture mismatch (754 PSA now with ORA)", "Deal Aging SLA - 2026-08-09", "Normalized", $true),
        # ...but the stem must still discriminate by DATE, or every day matches every day.
        @("[ORA] Deal Aging SLA - 2026-08-09 - 0 breaches", "Deal Aging SLA - 2026-08-10", "Normalized", $false),
        # A different producer with a confusingly similar name must NOT match. Both of
        # these were in Sent Items on 2026-08-09 within seven minutes of each other.
        @("[ORA Command Center] Daily Brief - 2026-08-09", "ORA Daily Brief - Sunday, August 9 2026", "Normalized", $false)
    )
    $fail = 0; $i = 0
    foreach ($c in $cases) {
        $i++
        $got = Test-SubjectMatch -Candidate $c[0] -Probe $c[1] -Mode $c[2]
        if ($got -ne $c[3]) {
            Write-Host ("  FAIL  case {0}: candidate='{1}' probe='{2}' mode={3} expected={4} got={5}" -f $i, $c[0], $c[1], $c[2], $c[3], $got)
            $fail++
        } else {
            Write-Host ("  PASS  case {0} ({1})" -f $i, $c[2])
        }
    }
    if ($fail -gt 0) { Write-Host "$fail SELF-TEST FAILURE(S)"; exit 1 }
    Write-Host "ALL outlook-sent-probe self-tests passed."
    exit 0
}

# --------------------------------------------------------------- real probe

if ($SubjectFile) {
    if (-not (Test-Path -LiteralPath $SubjectFile)) {
        [Console]::Out.WriteLine((@{ result = "PROBE_ERROR"; error = "SubjectFile not found: $SubjectFile" } | ConvertTo-Json -Compress))
        exit 1
    }
    $Subject = (Get-Content -LiteralPath $SubjectFile -Raw -Encoding UTF8).Trim()
}
if ([string]::IsNullOrWhiteSpace($Subject)) {
    [Console]::Out.WriteLine((@{ result = "PROBE_ERROR"; error = "No -Subject or -SubjectFile supplied" } | ConvertTo-Json -Compress))
    exit 1
}

if ([string]::IsNullOrWhiteSpace($OnDate)) { $target = (Get-Date).Date }
else {
    try { $target = [datetime]::ParseExact($OnDate, "yyyy-MM-dd", $null).Date }
    catch {
        [Console]::Out.WriteLine((@{ result = "PROBE_ERROR"; error = "Bad -OnDate '$OnDate' (want yyyy-MM-dd)" } | ConvertTo-Json -Compress))
        exit 1
    }
}

if ($Force) {
    [Console]::Out.WriteLine((@{
        result = "FORCED"; probeSubject = $Subject; onDate = $target.ToString("yyyy-MM-dd")
        message = "-Force supplied: Sent-Items check bypassed, PROCEED with the send. Only a human-directed manual re-run may pass this; a scheduled fire must never."
    } | ConvertTo-Json -Depth 5 -Compress))
    exit 0
}

$outlook = $null
try {
    try { $outlook = [Runtime.InteropServices.Marshal]::GetActiveObject("Outlook.Application") }
    catch { $outlook = New-Object -ComObject Outlook.Application }

    $olFolderSentMail = 5
    $sent = $outlook.GetNamespace("MAPI").GetDefaultFolder($olFolderSentMail)
    $items = $sent.Items
    $items.Sort("[SentOn]", $true)   # descending -- newest first

    $scanned = 0
    $match = $null
    foreach ($item in $items) {
        $scanned++
        if ($scanned -gt $MaxScan) { break }
        $sentOn = $null
        try { $sentOn = $item.SentOn } catch { continue }
        if ($null -eq $sentOn) { continue }
        # Sorted descending: once we walk past the target day we are done.
        if ($sentOn.Date -lt $target) { break }
        if ($sentOn.Date -ne $target) { continue }
        $subj = $null
        try { $subj = $item.Subject } catch { continue }
        if (Test-SubjectMatch -Candidate $subj -Probe $Subject -Mode $MatchMode) {
            $match = [ordered]@{
                subject = $subj
                sentOn  = $sentOn.ToString("yyyy-MM-ddTHH:mm:ssK")
                to      = $(try { $item.To } catch { $null })
                cc      = $(try { $item.CC } catch { $null })
            }
            break
        }
    }

    if ($null -ne $match) {
        [Console]::Out.WriteLine((@{
            result = "ALREADY_SENT"; probeSubject = $Subject; onDate = $target.ToString("yyyy-MM-dd")
            matchMode = $MatchMode; scanned = $scanned; match = $match
            message = "A message matching this subject is already in Sent Items for $($target.ToString('yyyy-MM-dd')) -- SKIP the send."
        } | ConvertTo-Json -Depth 5 -Compress))
        exit 10
    }

    [Console]::Out.WriteLine((@{
        result = "NOT_SENT"; probeSubject = $Subject; onDate = $target.ToString("yyyy-MM-dd")
        matchMode = $MatchMode; scanned = $scanned
        message = "No matching message in Sent Items for $($target.ToString('yyyy-MM-dd')) -- PROCEED with the send."
    } | ConvertTo-Json -Depth 5 -Compress))
    exit 0
}
catch {
    [Console]::Out.WriteLine((@{
        result = "PROBE_ERROR"; probeSubject = $Subject; error = $_.Exception.Message
        message = "Sent-Items probe failed. FAIL OPEN: proceed with the send and record the gap in the run summary."
    } | ConvertTo-Json -Depth 5 -Compress))
    exit 1
}
finally {
    if ($null -ne $outlook) {
        try { [Runtime.InteropServices.Marshal]::ReleaseComObject($outlook) | Out-Null } catch { }
    }
}
