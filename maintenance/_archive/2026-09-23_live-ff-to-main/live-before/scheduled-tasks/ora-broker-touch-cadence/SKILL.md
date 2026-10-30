---
name: ora-broker-touch-cadence
description: Monthly (2nd, 1:40 PM ET) broker relationship touch cadence — reads the Notion Broker Relationships DB, checks Outlook for recent contact, DRAFTS (never sends) personal pocket-listing check-ins to up to 5 brokers via Outlook COM .Save(); summary to ggoldberg only. Draft-only by design (Hard Invariant 1). Serves acquisition velocity (priority #1); Gabriel-ratified G4b 2026-07-16. v1.2. [MODEL: UNVERIFIABLE | checked 2026-07-16]
---

ORA Broker Relationship Touch Cadence (v1.2, Gabriel-ratified G4b 2026-07-16; v1.1/v1.2 fixes Gabriel-directed 2026-09-19)

AUTOMATION-BUDGET JUSTIFICATION: Serves ORA priority #1 (acquisition velocity) — opens the pocket-listing/relationship deal-flow channel that every existing sourcing task (ora-deal-sourcing-scan, ora-entry-market-scan) deliberately avoids, since those are on-market/public-listing scans only. Gabriel-ratified as ruling G4b on 2026-07-16. DRAFT-ONLY BY DESIGN — this task never sends an external communication; it exists specifically to stay inside Hard Invariant 1 while still opening the relationship channel.

STEP 0 — DOUBLE-FIRE ENTRY GUARD (added v1.2 2026-09-19; fleet standard).
Run this as the FIRST action of the run — BEFORE the backlog gate in Step 0.5, before any Drafts-folder
counting, before the Notion roster pull, before any Outlook call of any kind.

Why: this task shipped with no double-fire guard and fired twice in September against a monthly cron —
2 drafts on 2026-09-02 and 5 more on 2026-09-05 (audit `2026-09-19_BrokerDraftsBacklog_Audit_v01.md`,
§4). The whole CC/MCP fleet fires only while the Desktop app is open, so an offline stretch spanning
the 2nd re-arms this task at next open exactly as a daily task re-arms overnight. A DAY-keyed claim
would not help: the failure mode for a monthly task is a re-fire on the 5th because the 2nd was
missed, or an overlapping manual catch-up run. `--period month` keys the claim to the calendar month
for exactly this reason, and this task's blast radius is drafts in Gabriel's mailbox, so a double fire
is not merely a duplicate report — it is duplicate counterparty correspondence.

python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py claim --task ora-broker-touch-cadence --block main --run-id <run_id> --period month --ttl-min 45

- Exit 10 → this month's run already completed. Log `BLOCK_MAIN_ALREADY_COMPLETE_TODAY`, create NO
  drafts, send NO email, touch neither Notion nor Outlook, and report it as a NORMAL skip (not a miss),
  citing the earlier run's Ops Hub row.
- Exit 11 → another fire is live this month. Stand down identically.
- Exit 0 → proceed to Step 0.5.

Once the run's summary email lands — whether that is the Step 0.5 gated-run email or the Step 5
completion summary — run:

python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py complete --task ora-broker-touch-cadence --block main --run-id <run_id> --period month --email-sent-at <ISO8601>

If the run aborts instead:

python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py fail --task ora-broker-touch-cadence --block main --run-id <run_id> --period month --error "<what broke>"

- ONLY the run holding the claim may call `complete` or `fail`. A run that stood down (exit 10 or 11)
  calls NEITHER.
- ALWAYS pass `--period month` on EVERY call. Omitting it addresses the day-keyed bucket instead and
  defeats the guard SILENTLY — no error is raised, the claim simply never persists across days.
- A run gated by Step 0.5 still HOLDS the claim (it entered on exit 0), so it still calls `complete`
  after its one summary email. A gated run is a completed run, not an aborted one.
- The GUARD CONDITION below says "exit silently" when the Notion DB is unreachable or nobody qualifies.
  Under v1.2 that path must still close the claim: post the Ops Hub row as it already requires, then
  call `complete` (nothing was emailed, so omit `--email-sent-at`) — or `fail --error ...` if the exit
  is a genuine abort. An exit that closes neither leaves the month's claim open until the 45-minute TTL
  lapses, which re-opens the double-fire window this step exists to shut.
- Full contract: `_shared/README-DOUBLE-FIRE-GUARD.md`.

STEP 0.5 — BACKLOG GATE (added v1.2 2026-09-19, Gabriel-approved).
Runs AFTER Step 0's double-fire guard and BEFORE recipient selection — before the Step 1 Notion roster
pull and before Step 2/2.5 choose anyone.

BACKLOG_GATE_THRESHOLD = 5     # unsent cadence drafts at which this run creates nothing.
                               # Named constant so the number is changed HERE and nowhere else.
                               # Set to one full batch (the Step 2 cap) — one undrained batch is
                               # already proof the bottleneck is downstream of drafting.

Why: as of the 2026-09-19 audit the task had produced 8 unsent check-in drafts and Gabriel had sent
ZERO; not one had even been opened (CreationTime == LastModificationTime on all 8), the oldest 59 days.
The designed throughput is 5/month. The constraint is review bandwidth, not draft generation — adding
drafts to a queue nobody drains makes the queue worse, not the pipeline better.

0.5a — COUNT. Count the unsent touch-cadence drafts in Gabriel's Outlook Drafts folder using EXACTLY
the identification markers already used by Step 2.5c and by the 2026-09-19 audit §1 — single external
broker recipient with no cc; subject of the form `<Market> industrial -- <reconnecting | checking in |
quick check-in | checking back in>`; body opening `<FirstName> -- ` or `<FirstName>,` and naming the
buy-box verbatim. Do NOT count vendor RFPs, deal-specific chasers, deal-diligence drafts, or the
signature-only empty stubs — the audit's §1 exclusion list is part of the marker set, not commentary.
Read-only: property reads only, nothing is opened, edited, moved, deleted or re-saved.

0.5b — GATE. If the count is >= BACKLOG_GATE_THRESHOLD:
  - Create NO drafts this run. Do not pull the Notion roster, do not select recipients, do not compose.
  - Still leave run evidence exactly as this spec already requires: post the Step 5 Notion Ops Hub
    completion row, recording that the run was backlog-gated, the count, and the threshold.
  - Send Gabriel exactly ONE summary email via the task's existing send path and routing —
    `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` to ggoldberg@oxfordra.net
    ONLY, no cc — stating: how many unsent cadence drafts exist; the oldest draft's age in days; each
    recipient with that draft's created date; and, as its own line, exactly:
        clear these before more are made
  - Before that send, run the Layer 2 pre-send probe (see 0.5c).
  - Then call Step 0's `complete` with `--period month` and `--email-sent-at`, and stop normally.
  - A GATED RUN IS A NORMAL, SUCCESSFUL RUN — not a failure, not a miss, not an error. Report it as
    such everywhere it is reported, and never relax the threshold, reach further down the roster, or
    re-run to "make up" the skipped batch.
If the count is < BACKLOG_GATE_THRESHOLD, proceed to Step 1 unchanged. Step 2.5c still applies
per-broker: the backlog gate governs the RUN, Step 2.5c governs each individual candidate, and neither
substitutes for the other.
If the Drafts folder cannot be read at all, treat that as a data gap: do NOT assume zero and proceed —
report the gap, create no drafts, and close the claim. An unreadable folder is not an empty one.

0.5c — LAYER 2 PRE-SEND PROBE (fleet standard, mandatory before the gated run's ONE email):
powershell -ExecutionPolicy Bypass -File C:\Users\Owner\.claude\scheduled-tasks\_shared\outlook-sent-probe.ps1 -SubjectFile "<temp .txt>"
  - Always `-SubjectFile`, never a literal `-Subject` — non-ASCII subject characters are mangled in transit.
  - Use a DATED STEM, not the full subject, since the subject's tail carries live counts that
    legitimately differ between runs. Stem: `Broker Touch Cadence - <YYYY-MM-DD>` (<YYYY-MM-DD> = the run date computed once at run start with `date '+%A %Y-%m-%d'`, date part only, reused verbatim in the subject, the Ops Hub row and the body). Keep the date in the
    stem or every day matches every day; keep it specific enough that no other ORA producer matches it.
  - Exit 0 (NOT_SENT) → proceed with the send. Exit 10 (ALREADY_SENT) → SKIP the send, log a NORMAL
    skip, and still call `complete` so Layer 1 re-converges with reality. Exit 1 (PROBE_ERROR) → FAIL
    OPEN, send anyway, and record the gap — suppressing a real report because a probe broke is worse
    than a duplicate.
The same probe, with the same dated stem, applies to the Step 5 completion summary on an ungated run —
Layer 2 covers every COM send this task makes, and this task makes exactly one per run either way.

GUARD CONDITION: If the Notion Broker Relationships DB is unreachable, or zero brokers qualify (see Step 2), post a Notion Ops Hub row stating so and exit silently — do not halt, do not fabricate a broker list.

STEP 1 — Pull broker roster.
Read the Notion Broker Relationships DB (data source id 48e43778b1f24b168f3c0bf18f8642e9). Pull active brokers with their market/cluster and last-logged-touch date if tracked there.

STEP 2 — Select up to 5 stale-touch brokers.
Select up to the top 5 brokers across ORA's target clusters (Columbus, Cincinnati, Indianapolis, Kansas City, plus entry markets: Louisville, Delmarva, Grand Rapids, Des Moines) who have no logged touch in 30+ days per the Notion DB.
HubSpot is NOT a broker CRM at ORA (rules.md §3b) — do not consult it for broker last-contact truth. Outlook is the source of truth for broker last-contact: for each candidate broker, use mcp outlook_email_search to check recent correspondence (last 30 days) before drafting. Skip anyone Gabriel emailed in the last 30 days, even if the Notion DB shows no logged touch — Outlook truth overrides a stale/missing Notion field.

STEP 2.5 — IDENTITY-NORMALISED DUPLICATE GATE (mandatory; added v1.1 2026-09-19).
Run this AFTER Step 2 selection and BEFORE any draft is composed or saved. Nothing in this step
changes the 5-draft cap, the cadence, or the Notion roster as the recipient-selection source — it
only removes candidates that would produce a duplicate. A candidate that fails any check below is
dropped from the run and reported in the Step 5 summary with its reason; it is never silently skipped.

Why this exists: on 2026-09-02 and 2026-09-05 the task drafted John Hassler (Newmark Zimmer, Kansas
City) TWICE under the identical subject "Kansas City industrial -- checking in", at two different
addresses (jhassler@nzimmer.com and john.hassler@nmrkzimmer.com — alternate domains of the SAME firm
after the Newmark/Zimmer rebrand). Address-level dedup did not catch it because the addresses differ.
This is the same failure shape as the 2026-04-05 six-duplicate misfire.

2.5a — NORMALISE TO PERSON + FIRM, NOT TO EMAIL ADDRESS.
For every candidate build an identity key of PERSON NAME + FIRM, not the mailbox string:
  - person: lowercase, strip punctuation and middle initials, reduce to first + last
    ("John Hassler", "jhassler@...", "john.hassler@..." and "J. Hassler" all key to `hassler|john`);
  - firm: lowercase the ORGANISATION, not the domain, and collapse known alternate/legacy domains and
    rebrands to one firm token. At minimum: nzimmer.com == nmrkzimmer.com == "newmark zimmer".
    Treat any two domains as the same firm when the Notion Broker Relationships DB carries them under
    one firm record, or when the local part resolves to the same human (`jhassler` vs `john.hassler`).
    When in doubt, treat them as the SAME firm and drop the extra candidate — a missed touch is
    recoverable, a duplicate cold check-in to the same broker is not.
Two candidates sharing an identity key are ONE person, however many addresses they hold.

2.5b — 30-DAY CONTACT CHECK ACROSS DRAFTS *AND* SENT ITEMS.
For each identity key, search BOTH the Outlook Drafts folder AND Sent Items over the trailing 30 days
for any item addressed to, or received from, ANY address belonging to that identity key — not just the
one address selected for this run. Match on the identity key, so an alternate-domain address still
hits. Any match: skip the candidate and report it as `SKIPPED — contacted/drafted within 30d`.
This subsumes and replaces the Step 2 address-only "emailed in the last 30 days" check; Step 2 stays
the selection source, this is the gate.

2.5c — BACKLOG CHECK: NO SECOND DRAFT FOR ANYONE WHO ALREADY HAS ONE, AT ANY AGE.
Independently of the 30-day window, scan the whole Drafts folder for an UNSENT touch-cadence draft
belonging to this identity key, of ANY age. The cadence fingerprint is: single external broker
recipient, no cc, subject of the form `<Market> industrial -- <reconnecting | checking in | quick
check-in | checking back in>`, body naming the buy-box. If one exists, skip the candidate and report
`SKIPPED — unsent cadence draft already parked (created <date>, age <n>d)`. A broker with an unsent
draft is not under-touched; he is waiting on Gabriel. Never top up a queue that has not been drained.

2.5d — AT MOST ONE DRAFT PER PERSON PER RUN.
Deduplicate the selected set by identity key BEFORE composing anything, so one run can never emit two
drafts for one person even if the Notion roster lists him twice. Where a broker appears under two
addresses in the source data, keep the address that has an actual prior TWO-WAY thread in Outlook
(inbound from him AND outbound to him); if neither address has a two-way thread, keep the address with
the most recent inbound item; if still tied, keep neither and report the broker as unresolved rather
than guessing. Report the discarded address in the Step 5 summary as a DATA-QUALITY item —
"<person> carries two addresses in the roster (<kept> kept, <dropped> dropped, basis: <two-way thread
| most recent inbound>); Notion Broker Relationships DB should be deduplicated" — so the roster gets
fixed at source instead of the gate absorbing the same collision every month. Do NOT write the fix to
Notion from this task; report it.

STEP 3 — Draft personal check-ins.
For each selected broker, DRAFT a short, personal check-in email: institutional-direct tone, references their market and any live thread context found in Outlook search, asks specifically about off-market/pocket industrial or flex listings in ORA's buy-box (sub-$10M, sub-50K SF, Class B/C industrial/flex). No form-letter feel. 4-6 sentences max. Sign per the Property→LLC Signature Roster convention only if the correspondence is property-specific; otherwise sign as Gabriel Goldberg, Oxford Realty Advisors, per Voice Register (broker mail is relationship correspondence, not landlord-to-tenant mail, so the personal/firm signature applies, not a property LLC).

STEP 4 — Park drafts in Outlook. NEVER send.
Create each broker draft as an Outlook DRAFT via COM — never via .Send(). Use exactly this pattern (spelled out verbatim so an unattended run never improvises):

# ==========================================================================
# 4a — THE BODY IS NEVER BUILT INSIDE AN EXPANDABLE POWERSHELL STRING.
# ==========================================================================
# A double-quoted (expandable) string SILENTLY DESTROYS EVERY DOLLAR FIGURE:
# PowerShell reads "$7.50" as the undefined variable $7 followed by ".50", and
# "$10M" as $10 followed by M. Proven by repro 2026-08-27:
#   "clear $7.50/SF NNN ... $80.87/SF list ... $50,000 deposit"
#   -> "clear .50/SF NNN ... .87/SF list ... ,000 deposit"
# Re-proven 2026-09-19 without touching Outlook
# (C:\Users\Owner\AppData\Local\Temp\ora-broker-gap\figure-roundtrip-test.ps1):
#   "under $10M ... a $1,000/mo ... a $3.3M ... a $50,000 deposit"
#   -> "under  ... a ,000/mo ... a .3M ... a ,000 deposit"   (4 of 4 figures lost)
# This defect shipped three corrupted counterparty drafts on 2026-08-13, and it
# reached this task's own output: the 2026-07-22 Nathan Pealer draft reads
# "under  -" where "$10M" belongs and is still sitting unsent in Drafts (audit
# 2026-09-19_BrokerDraftsBacklog_Audit_v01.md, §6). It bites this task hard —
# broker check-ins are numbers-forward and name the buy-box ($10M / 50K SF).
#
# v1.1 RULE (mandatory): the draft body is NEVER assembled in PowerShell at all.
# It is written to a UTF-8 FILE as literal text and read back. Two permitted
# ways to produce that file, and no third:
#   (i)  the calling agent writes the body with its Write tool, per broker, to
#        C:\Users\Owner\AppData\Local\Temp\ora-broker-touch\<key>-body.txt
#        (PREFERRED — the text never passes through a shell at all); or
#   (ii) a SINGLE-QUOTED here-string @'...'@ piped to a UTF-8 file, as below.
# Never @"..."@. Never "..." . Never string concatenation with a + operator.
# Never build the body by interpolating broker name, firm or market into a
# quoted string — resolve every per-broker token BEFORE the text is written, so
# the file is already final and literal. The file, not any variable, is the
# INTENDED TEXT of record, and 4c asserts the saved draft against it.
#
# NOTE: there is NO shared draft-creation helper under
# C:\Users\Owner\.claude\scheduled-tasks\_shared\ — checked 2026-09-19.
# send-via-outlook.ps1 takes -BodyFile but it SENDS (.Send()); it is used ONLY
# for the Step 5 internal summary and MUST NEVER be used to create a broker
# draft. send-parked-drafts.ps1 also sends. Use the COM .Save() pattern below.
# If a shared draft helper is ever added to _shared\, reuse it instead of this
# block rather than carrying a second copy of the pattern.

$bodyFile = 'C:\Users\Owner\AppData\Local\Temp\ora-broker-touch\<key>-body.txt'

# Route (ii) only — skip entirely if the agent already wrote $bodyFile:
$body = @'
<body text — pasted verbatim and already final, no tokens, no escaping required>
'@
Set-Content -Path $bodyFile -Value $body -Encoding UTF8 -NoNewline

# ==========================================================================
# 4b — CREATE THE DRAFT BY READING THAT FILE. NEVER .Send().
# ==========================================================================
$intended = Get-Content -Path $bodyFile -Raw -Encoding UTF8

$outlook = New-Object -ComObject Outlook.Application
$mail = $outlook.CreateItem(0)
$mail.To      = '<broker email>'
$mail.Subject = '<subject>'
$mail.Body    = $intended
$mail.Save()
# NEVER call $mail.Send() — drafts stay parked in the Outlook Drafts folder for Gabriel's own review and send.

# ==========================================================================
# 4c — MANDATORY POST-SAVE FIGURE ASSERTION (re-read the SAVED draft).
# ==========================================================================
# The v1.0 check compared $body against $mail.Body. That is why the Pealer draft
# slipped: under the old build $body was ALREADY corrupt, so its left-hand test
# ($body -match '\$\d') evaluated FALSE and the guard never armed — corrupt-vs-
# corrupt always agrees. Verified 2026-09-19 in the repro above. The comparison
# must therefore be against the INTENDED FILE on disk, never an in-memory string.
#
# Re-read the draft from the Outlook store (not the in-memory object), extract
# every dollar figure from the intended file, and assert each one is present
# VERBATIM in the saved body.
$saved = $outlook.Session.GetItemFromID($mail.EntryID).Body
$wanted = [regex]::Matches($intended, '\$[\d,]+(?:\.\d+)?[KMB]?') | ForEach-Object { $_.Value }
$missing = @($wanted | Where-Object { $saved -notmatch [regex]::Escape($_) })

if ($missing.Count -gt 0) {
  # Delete NOTHING. The draft stays parked so Gabriel can see it; it is reported as unsendable.
  Write-Output ('CORRUPTED - DO NOT SEND — EntryID=' + $mail.EntryID +
                ' — figures lost: ' + ($missing -join ' | '))
} elseif ($saved -match '(?<![\w$])[.,]\d{2}/SF') {
  Write-Output ('CORRUPTED - DO NOT SEND — EntryID=' + $mail.EntryID +
                ' — orphaned decimal before /SF: ' + $Matches[0])
} else {
  Write-Output ('PARKED_OK EntryID=' + $mail.EntryID)
}

# Any draft reported CORRUPTED - DO NOT SEND must carry that exact phrase into the
# Step 5 Ops Hub row AND the Step 5 summary email, named and counted separately from
# the parked-OK drafts. Never delete, never re-save, never silently retry, and never
# describe such a draft to Gabriel as ready to send.

STEP 5 — Completion reporting.
Post one row to the Notion Ops Hub (parent page 32b6ecd8-9e59-81f2-b329-df3fd0e25062) listing who was drafted, their market, and why (stale-touch trigger + any Outlook thread context used). If that create (on any path — 0.5b gate, GUARD CONDITION or here) returns a grace/quota notice or no page ID, look for it — `notion-fetch` the parent for an exact-title child, then search by the exact title (search lags: a miss alone is not proof) — a match created at/after the create call is this run's page, use it; never blind-retry a create (it produced a duplicate). After a grace/quota notice with no match, do not retry: the row is UNVERIFIED — say so in the summary email (on the GUARD CONDITION path, which sends none, in the run output). Quota errors → `notion-quota-fallback` skill.
The row and the summary email must ALSO carry, as separate named lines (added v1.1):
  - every candidate dropped by the STEP 2.5 gate, with its reason (30-day contact/draft, existing
    unsent cadence draft and its age, or same-person-two-addresses);
  - every DATA-QUALITY item from 2.5d (broker carrying two roster addresses, which was kept, which
    was dropped, and on what basis);
  - every draft that failed the STEP 4c assertion, verbatim as `CORRUPTED - DO NOT SEND`, with its
    EntryID and the figures that were lost, counted separately from the parked-OK drafts.
A run that drafts nobody because every candidate was gated is a SUCCESSFUL run — report the gate
results and exit; do not relax the gate or reach further down the roster to fill the batch. Then email a one-paragraph summary to ggoldberg@oxfordra.net ONLY (no cc — routing canon; the ora-am-brief Daily Brief is the sole cc-egoldberg exception and does not apply here) via C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 — this summary is the ONLY send this task ever performs; the broker drafts themselves are never sent. On a COM failure for either the drafts or the summary send: retry once, then flag loudly in the Notion Ops Hub row if the retry also fails — do not halt the run.

HARD GUARDRAILS (verbatim, non-negotiable):
- Never call .Send() on a broker draft. An actual outbound send to a broker (counterparty) requires Gabriel's explicit in-turn confirmation per Hard Invariant 1 — this task is structurally incapable of doing that send itself.
- Never fabricate relationship history, thread context, or broker detail. If no real context exists for a broker, the draft says less — it never invents rapport, deals, or prior conversations that didn't happen.
- Never name any active confidential deal in a broker draft or the Notion/summary output. The confidential-deal roster lives in C:\Users\Owner\.claude\hooks\confidential-terms.json (and session context) — if a broker's context brushes against deal specifics, keep the draft generic.
- Routing canon: the completion summary goes to ggoldberg@oxfordra.net ONLY. No cc to egoldberg or anyone else.
- HubSpot is not consulted for broker last-contact truth (rules.md §3b) — Outlook search is authoritative for that check.
- Never build a draft body inside a double-quoted or otherwise expandable PowerShell string, and never
  interpolate a broker/firm/market token into one. Body text is literal, written to a UTF-8 file, and
  read back (Step 4a). The file is the intended text of record.
- Never present a draft that failed the Step 4c assertion as sendable, and never delete it to make the
  run look clean — report it as `CORRUPTED - DO NOT SEND`.
- Never create two drafts for the same PERSON in one run, or any draft for a person who already has an
  unsent cadence draft parked (Step 2.5). Identity is person + firm, never the email address alone.

This task is registered on the CC/MCP fleet deliberately: it needs native shell access for the Outlook COM draft-creation pattern in Step 4.

CHANGELOG
- v1.2 — 2026-09-19 (Gabriel-directed, approved in-turn). Two structural gates added; nothing existing
  removed.
  (1) BACKLOG GATE (new Step 0.5). The 2026-09-19 audit found 8 unsent cadence drafts, zero sent, none
      ever opened, oldest 59 days, against a designed throughput of 5/month — the constraint is
      Gabriel's review bandwidth, not draft generation. A run that finds
      BACKLOG_GATE_THRESHOLD (= 5, named constant at the top of the step) or more unsent cadence
      drafts creates none, still posts the Ops Hub completion row, and sends ONE summary over the
      task's existing send path and routing with the count, the oldest age in days, every recipient and
      created date, and the line "clear these before more are made". A gated run is an ordinary
      successful run, not a failure. Drafts are counted with the same markers as Step 2.5c and audit
      §1, including its exclusion list. An unreadable Drafts folder is a data gap, never a zero.
  (2) DOUBLE-FIRE GUARD (new Step 0). The task had none and fired twice in September against a monthly
      cron — 2 drafts on 09-02, 5 more on 09-05 (audit §4). Wired to the fleet standard per
      `_shared/README-DOUBLE-FIRE-GUARD.md`, copying the monthly pattern from
      `ora-tenant-hubspot-reconciliation`: the Step 0 claim on block `main` with `--period month`
      and `--ttl-min 45`; exit 10/11 stand down as a NORMAL skip with no drafts and no email; exit 0
      proceeds; only the claim-holder calls `complete`/`fail`, a stood-down run calls neither, and
      `--period month` is mandatory on every call because omitting it defeats the guard silently.
      Step 0 runs before the backlog gate and before any Drafts counting or Notion pull. The
      GUARD CONDITION's "exit silently" path must now close the claim rather than leave it to TTL.
      Layer 2 added: `outlook-sent-probe.ps1` with the dated stem `Broker Touch Cadence - <YYYY-MM-DD>`
      runs before the one summary email on both the gated and ungated paths.
  Unchanged by design: monthly cadence, the 5-draft cap, the Notion Broker Relationships DB as the
  recipient-selection source, ggoldberg-only routing, and draft-only behaviour (Hard Invariant 1).
- v1.1 — 2026-09-19 (Gabriel-directed). Two defects closed, found by the read-only backlog audit
  `2026-09-19_BrokerDraftsBacklog_Audit_v01.md` (8 unsent cadence drafts in Gabriel's Drafts folder,
  none ever opened, oldest 59 days).
  (1) $-INTERPOLATION CORRUPTION. The 2026-07-22 Nathan Pealer draft reads "under  -" where "$10M"
      belongs — a double-quoted PowerShell string swallowed `$10` as an undefined variable (audit §6).
      Step 4 rewritten: the body is never assembled in an expandable string, it is written to a UTF-8
      file (agent Write tool preferred, else a single-quoted here-string) and read back to create the
      draft. Step 4c's post-save assertion now re-reads the SAVED draft from the Outlook store and
      compares it against the INTENDED FILE — the v1.0 check compared $body to $mail.Body, which is
      why it never fired: under the old build $body was already corrupt, so its left-hand test was
      false and the guard never armed. Any mismatch is reported `CORRUPTED - DO NOT SEND`; nothing is
      deleted. Re-proven without touching Outlook on 2026-09-19: the old method lost 4 of 4 figures
      ($10M, $1,000, $3.3M, $50,000), the new method lost 0 of 4.
      No shared draft-creation helper exists in `_shared\` (checked 2026-09-19); `send-via-outlook.ps1`
      takes -BodyFile but SENDS and must never be used for drafts.
  (2) DUPLICATE DRAFTS. John Hassler (Newmark Zimmer, Kansas City) was drafted twice under the
      identical subject "Kansas City industrial -- checking in" at two alternate-domain addresses
      (jhassler@nzimmer.com 2026-09-02, john.hassler@nmrkzimmer.com 2026-09-05) — address-level dedup
      could not see it; the same failure shape as the 2026-04-05 six-duplicate misfire. New Step 2.5
      gate: normalise every candidate to PERSON + FIRM (alternate/legacy domains collapse to one firm
      token), check Drafts AND Sent Items over 30 days on that identity key, refuse anyone already
      holding an unsent cadence draft of any age, allow at most one draft per person per run, and
      resolve a two-address broker to the address with a real two-way thread while reporting the other
      as a data-quality item.
  Unchanged by design: monthly cadence, the 5-draft cap, the Notion Broker Relationships DB as the
  recipient-selection source, ggoldberg-only routing, and draft-only behaviour (Hard Invariant 1).
- v1.0 — 2026-07-16. Gabriel-ratified as ruling G4b.