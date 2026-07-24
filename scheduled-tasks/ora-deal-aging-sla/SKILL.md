---
name: ora-deal-aging-sla
description: Weekday counterparty-aging SLA — computes days-since-last-outbound per open deal ask (broker/counsel/lender) via live Outlook search; drafts (never sends) a nudge past ratified per-class thresholds (broker 5bd/counsel 7bd/lender 7bd, ratified 2026-07-18). Also reports Notion-vs-Outlook posture mismatches as first-class findings (STEP 3b). Draft-only, Hard Invariant 1. v1.1. [MODEL: UNVERIFIABLE | checked 2026-07-21]
output_contract:
  version: 1
  blocks:
    - id: aging-nudge-drafts
      artifact: { type: outlook_draft, folder: Drafts }
      freshness_window_hours: 30
      expected_on: { cron: "25 9 * * 1-5" }
      on_missing_severity: info
    - id: completion-row
      artifact: { type: notion_page, parent_id: 32b6ecd8-9e59-81f2-b329-df3fd0e25062, title_pattern: "Deal Aging SLA — {DATE}" }
      freshness_window_hours: 30
      expected_on: { cron: "25 9 * * 1-5" }
      on_missing_severity: warn
---

# ORA Counterparty-Aging SLA (v1.1)

STATUS: Thresholds ratified by Gabriel 2026-07-18 (see STEP 4) — unchanged in v1.1. Plan 3 of the 2026-07 setup-improvement effort.

CHANGELOG — v1.1 (2026-07-24, per Gabriel): STEP 1's data-source id corrected from the undashed to the dashed UUID (the undashed form never resolved — every run before this date failed its first query). New STEP 3b makes Notion-vs-Outlook posture mismatch a first-class reported finding and, more importantly, requires falsifying STEP 2's internal-gate exclusions against the live thread before trusting them.

AUTOMATION-BUDGET JUSTIFICATION: Closes a real, already-realized gap. On 2026-07-13 the ORA Monday Sync flagged 754 Old State Route 74 (Cincinnati) as "31 days stale" on a PSA draft awaiting counsel — a stall that reached 36-38 days before a weekly board caught it by chance, not by design. Deal-command-board (weekly, Monday) tracks days-in-STAGE against Notion timestamps; it does not track days-since-last-OUTBOUND-TOUCH against the actual counterparty thread, and it only runs once a week. This task is the daily (weekday) counterpart, keyed on the live Outlook thread rather than a Notion date field that can go stale exactly when work is happening off-Notion.

GUARD CONDITION: If the Notion Acquisition Pipeline Tracker is unreachable, or zero deals have a qualifying open outbound ask (see STEP 2), still post STEP 7's dated child page (stating the guard condition triggered) and exit — do not halt, do not fabricate a deal list or an aging number. **A zero-qualifying-ask run is not an early exit from STEP 3b(b):** run the posture check on the internal-gate exclusions first, because "nothing qualifies" is itself frequently a stale-tracker artifact, and report any mismatches on the page before exiting.

---

## STEP 1 — Pull active pipeline deals

Query the Notion Acquisition Pipeline Tracker (data source `collection://bcfe4a03-7e61-4ac1-a0bb-c44174fa138b`) via `notion-query-data-sources` (SQL mode). Pull: Deal Name, Address, Stage, Next Action, Deal Owner, Broker / Source, Key Attorney, Lender, Last Updated, `date:Last Activity:start`, `date:Target Close Date:start`.

**The DASHED UUID above is required — do not "tidy" the dashes out.** `notion-query-data-sources` rejects the undashed form (`collection://bcfe4a037e61…c44174fa138b`, elided here on purpose so a mechanical sweep for undashed ids does not false-positive on this warning) with a `validation_error` / `sql_invalid` reading *"table \"collection://…\" was not exposed for this request"* — which looks like a permissions or sharing problem and sends you debugging the wrong thing entirely. This SKILL.md carried the undashed id from authoring until 2026-07-24, so every run before that date failed its first query and recovered by hand. If the id ever stops resolving, `notion-fetch` the database id `46c8a5c6-8b37-4c53-a10d-0f55c97613e5` and read the dashed URL out of the `<data-source url="...">` tag rather than guessing at the format.

Exclude the same closed/dead stages `ora-deal-command-board` excludes, so the two boards never silently diverge on what counts as "open": Stage NOT IN ('Closed Won', 'Passed', 'Killed — Reneg Only', 'Killed — Note/Short-Sale in Discussion'). This must be a full, unpaginated pull (page on `has_more`/`next_cursor` until exhausted) — a partial pull that silently drops a stalled deal is worse than no run at all.

**PARKED exclusion (mirrors `ora-deal-command-board` STEP 2 verbatim):** skip any deal whose Next Action text contains "PARKED" — nudging a parked deal's broker/counsel would be actively wrong (dry-run evidence: Liberty Office Park's last outbound to its broker is 40 days old, but it is PARKED pending the Cincinnati-cluster go/no-go — a naive age check alone would have wrongly flagged it).

## STEP 2 — Identify deals with a genuine open outbound ask

Not every open-stage deal is waiting on a counterparty. Only flag a deal as having an open ask if its Next Action text (or Stage) describes ORA waiting on an external party's response — an LOI submitted and not yet countered/executed, a PSA draft/redline in the other side's court, or a broker chase for updated seller terms. Do NOT flag: deals awaiting Gabriel's own decision (internal gate, not a counterparty-aging risk — but see STEP 3b(b), which requires falsifying that call against the live thread before it sticks); deals where the ask is already resolved against ORA (no live ask to age); PARKED deals.

**Worked example of "already resolved against ORA" (2026-07-24 run):** 511 Industrial Mile Road shows `LOI Status = Submitted` with an LOI outstanding since 2026-05-15 and never formally countered or executed — on age alone, the single most breach-looking row in the pipeline. But the broker confirmed on 07-17 that the property went under contract to a competing buyer at full ask; ORA's $1.45M bid lost. The deal is kept at Stage `Candidate` per Gabriel purely to monitor for fallout. There is no live ask to age and no one to nudge: a follow-up would chase a decision already made against us. Distinguish this from a genuinely unanswered LOI, where the counterparty still owes a response — the test is whether an answer is still owed, not whether the tracker's status field still reads "Submitted".

For each qualifying deal, classify the open ask by counterparty class:
- **broker** — awaiting a broker/seller response to an LOI or counter (use the Broker / Source field for identity/contact).
- **counsel** — awaiting a PSA turn, redline response, or closing-condition confirmation from opposing/seller's counsel (use the Key Attorney field if populated; if null — as it currently is even for a deal with an active counsel ask — fall back to the counterparty names/domains visible in the matched Outlook thread itself, per STEP 3, and flag the missing Key Attorney field as a data-quality gap in the run summary rather than silently guessing).
- **lender** — awaiting a term sheet, commitment letter, or covenant response (use the Lender field).

## STEP 3 — Compute days-since-last-outbound via Outlook

For each deal with a qualifying open ask, use `outlook_email_search` to find the counterparty thread: search by the deal's street address and/or "[Address] PSA"/"[Address] LOI"-style subject terms, and, where a contact email or domain is known, narrow with the `recipient` filter rather than free-text `query` — free-text search on this connector is relevance-ranked, not literal, and returned unrelated daily-brief mail in testing when only a property-name query was used. Prefer recipient filtering whenever a counterparty email/domain is available.

**Mandatory recipient-domain fallback before concluding anything (added 2026-07-20 after a real miss).** The live thread subject often does NOT contain the deal's full street address — a PSA thread may be titled with a truncated or informal property name. So an address-only subject search can silently miss the actual external-counterparty thread and either return only ORA-internal/digest/automated mail or land on a stale leg. Therefore: if the address/subject search returns only ORA-internal exchanges (ggoldberg@/egoldberg@/our own counsel), digest/brief/automated mail, or nothing external, you MUST re-search with a `recipient`-domain filter derived from every counterparty domain available for the deal — the Broker / Source, Key Attorney, and Lender field contacts, plus any counterparty domains named in the deal file — BEFORE flagging `[NO OUTBOUND FOUND — VERIFY MANUALLY]` or computing a stale-since date. Only after the domain-filtered search also comes up empty is a `[NO OUTBOUND FOUND]` flag or an aging figure legitimate. Real defect this prevents (2026-07-18 run): the "754 Old State PSA" thread with the seller's counsel at `kmklaw.com` was missed by a "754 Old State Route 74"-subject search, so the run reported a false 25-business-day counsel breach when the deal was in fact in active same-week negotiation; a `recipient:kmklaw.com` (or `recipient:gerth`) re-search surfaces it immediately.

Within the matched thread, find the most recent message **sent by ORA (ggoldberg@ or egoldberg@) to the external counterparty** (not an internal cc, not a reply from the counterparty, not an ORA-internal exchange with our own counsel about the same deal — testing found Eric Goldberg emailing Phil Collins, ORA's OWN transaction counsel, in the same thread as the Seller's counsel exchange; only the outbound leg to the external party counts). Compute days-since as business days (Mon-Fri; do not count Sat/Sun) from that message's `sentDateTime` to today.

If no qualifying outbound message is found at all, do not fabricate a stale-since date — flag the deal as `[NO OUTBOUND FOUND — VERIFY MANUALLY]` in the summary rather than silently treating it as either 0 days or infinitely stale.

## STEP 3b — Posture mismatch is a FIRST-CLASS finding, not prose (added 2026-07-24)

STEP 2 classifies each deal off the tracker's own `Next Action` / `Stage` / `PSA Status` / `LOI Status` text. That text is exactly the thing that goes stale when work happens off-Notion — which is this task's whole reason to exist. So the tracker's claim about *whose court the ask sits in* must itself be treated as a claim to be checked, not as ground truth.

**(a) For every deal that qualified in STEP 2:** while you have the thread open from STEP 3, compare what the tracker asserts against what the thread shows, and record any disagreement as its own structured row in the STEP 7 output — one row per mismatch, never folded into the aging number or buried in narrative prose.

**(b) For every non-PARKED deal that STEP 2 excluded as an internal gate:** if its tracker text makes an Outlook-falsifiable claim that a document has NOT gone out — "not sent", "awaiting Gabriel's review/sign-off", "staged for review", "pending approval" — run the STEP 3 recipient-domain search anyway, whenever a counterparty domain is available from Broker / Source, Key Attorney, Lender, or the deal file. This is cheap (one search) and it is the single highest-value check in the task. **If the document did in fact go out, the deal re-enters STEP 2 as a genuine open ask of the matching class and is aged normally from that outbound** — do not leave it excluded on the strength of a tracker field the thread just contradicted.

A mismatch is any of:
- **Tracker behind the thread** — the field says a document was not yet sent (or is awaiting internal review) but Outlook shows it reached the counterparty. *Real case, 2026-07-24 run:* 754 Old State Route 74's `Next Action`, stamped 07-21 PM, read "NOT sent to Patterson — awaiting Gabriel's review/sign-off first", while Eric had sent the PSA with modifications to `kmklaw.com` on 07-23. Under the pre-3b doctrine that deal was an internal-gate exclusion; the check is what correctly reclassified it to a live counsel ask (1 business day, comfortably inside SLA).
- **Tracker ahead of the thread** — the field claims something was sent or asked that no outbound in the thread supports. Apply the STEP 3 recipient-domain fallback in full before asserting this: a thread you failed to find is NOT evidence that a document was never sent, and this is the direction in which a wrong call is most damaging (it invites a nudge for a turn that already happened).
- **Stage/status contradiction** — e.g. `PSA Status = Not Started` against a live PSA redline thread, or `LOI Status = Submitted` on a deal the broker has already reported as awarded elsewhere.

Report each mismatch as: deal · field · what the tracker asserts (with its stamp date) · what the thread shows (with the message date) · which of the two is newer · whether it changed the deal's STEP 2 classification. **Never edit the Notion field to reconcile it** — see the guardrails; the row is the handoff to Gabriel and to the weekly `ora-deal-command-board`.

Why this is first-class output and not a footnote: on a zero-breach run the mismatch is usually the *only* actionable finding, and it is more actionable than the aging figure. When the pipeline runs ahead of the tracker, this task computes its own number off the correct live thread and looks clean — while every downstream weekly board still reads the stale field and will draw the wrong conclusion. Both of this task's genuinely useful outputs to date surfaced on zero-breach runs.

## STEP 4 — Per-class thresholds (PARAMETERIZED — do not hardcode inline)

Ratified by Gabriel, 2026-07-18 — confirmed as proposed, no amendment:

```
BROKER_FOLLOWUP_THRESHOLD_BUSINESS_DAYS = 5   # [RATIFIED — Gabriel, 2026-07-18]
COUNSEL_TURN_THRESHOLD_BUSINESS_DAYS    = 7   # [RATIFIED — Gabriel, 2026-07-18]
LENDER_RESPONSE_THRESHOLD_BUSINESS_DAYS = 7   # [RATIFIED — Gabriel, 2026-07-18]
```

Still parameterized, not hardcoded inline — a future re-ratification only ever touches these three values. A deal breaches its SLA when days-since-last-outbound (STEP 3) exceeds the threshold matching its counterparty class (STEP 2). Only breaching deals proceed to STEP 6 (drafting); deals under threshold are reported in the summary as on-watch but do not get a nudge drafted.

## STEP 5 — Mandatory confidentiality check (run BEFORE drafting any nudge text)

Before drafting any nudge for a breaching deal, check that deal's address/name/next-action text against the active confidential-deals roster in `C:\Users\Owner\.claude\hooks\confidential-terms.json`, using the file's own matching semantics: `always` terms hit on any substring occurrence; `context` terms hit only in combination with a `context_requires_any` term on the same text. This is the same roster and matching logic the confidentiality-guard hook enforces elsewhere (CLAUDE.md Hard Invariant 3) — apply it manually since a scheduled-task run is not necessarily hook-mediated the same way an interactive edit is.

- If the deal matches an entry with `active: true`: **do not draft the nudge at all.** A drafted email sits in an Outlook mail client — an externally-visible surface for this purpose even though nothing is sent. Flag the deal in the summary as `[CONFIDENTIAL — DRAFT SUPPRESSED]`, naming only that it was suppressed, not the deal's terms.
- If the deal matches an entry with `active: false` (declassified, e.g. E Fulton per the 2026-07-09 declassification): proceed normally, but note in the summary that the match was against an inactive/declassified entry.
- If a deal both breaches its SLA and would require the nudge to reference deal-specific pricing/structure terms overlapping the `context` term list, redact those specifics from the draft even for a non-active deal — a follow-up nudge almost never needs to restate internal pricing logic anyway.

## STEP 6 — Draft-only nudge via Outlook COM. NEVER auto-send.

**Outbound counterparty communication — DRAFT ONLY.** Per Hard Invariant 1, nothing this task produces is ever sent without Gabriel's explicit in-turn confirmation; a scheduled run stops at a drafted, reviewable nudge sitting in the Outlook Drafts folder — never at a sent message.

For each breaching, non-suppressed deal, draft a short nudge using the tone/posture conventions from `communication-intelligence`:
- **broker class** — Module 4 "Informal / Follow-Up Email" format: 3-5 sentences, conversational but professional, no formal salutation required. Reference the property and ask for a status update per Module 3's "Deal Outreach to Broker" posture (do not disclose current pipeline or other targets).
- **counsel class** — Module 2's "Routine / informational" posture: professional, neutral, efficient; cite the specific open item (e.g. "the redline sent on [date]") rather than a generic chase, using whatever thread context STEP 3 actually found — never fabricate a turn or a document that wasn't really sent.
- **lender class** — same professional/neutral posture, referencing the specific term sheet/covenant item outstanding.

Sign as "Gabriel Goldberg, Oxford Realty Advisors" per the Module 2 standard signature block (deal-side relationship correspondence, not landlord-to-tenant mail — the Property→LLC signature roster does not apply here).

Create each nudge as an Outlook DRAFT via COM — never via `.Send()`. Use exactly this pattern:

```powershell
$outlook = New-Object -ComObject Outlook.Application
$mail = $outlook.CreateItem(0)
$mail.To = "<counterparty email>"
$mail.Subject = "<subject>"
$mail.Body = "<body text>"
$mail.Save()
# NEVER call $mail.Send() — drafts stay parked in the Outlook Drafts folder for Gabriel's own review and send.
```

## STEP 7 — Completion reporting

Post a NEW DATED CHILD PAGE under the Notion Ops Hub parent page (`32b6ecd8-9e59-81f2-b329-df3fd0e25062`), titled exactly `"Deal Aging SLA — {YYYY-MM-DD}"` (today's date) — a distinct page created fresh each run, never an appended row/block inside an existing page's body (an append isn't reliably freshness-checkable by a downstream contract-verification pass; a new titled child page is — this is the standard pattern for every task that posts a completion record to the Ops Hub, see `ora-deal-command-board` STEP 6). Its content lists: deals scanned, deals with a qualifying open ask, deals breaching by class, deals suppressed for confidentiality, deals flagged `[NO OUTBOUND FOUND — VERIFY MANUALLY]`, how many nudges were drafted, and — as its own titled section with one row per finding, not as prose — every **posture mismatch** from STEP 3b, including any deal whose STEP 2 classification the check changed. When there are zero breaches but one or more mismatches, the mismatch section is the substance of the report and the summary email must lead with it rather than with the "0 breaches" headline. Then email a one-paragraph summary to `ggoldberg@oxfordra.net` ONLY (no cc — routing canon) via `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`. On a COM failure for either the drafts or the summary send: retry once, then flag loudly in the Notion Ops Hub page if the retry also fails — do not halt the run.

---

## HARD GUARDRAILS (verbatim, non-negotiable)

- **Never call `.Send()` on a nudge draft.** An actual outbound send to a broker, counsel, or lender requires Gabriel's explicit in-turn confirmation per Hard Invariant 1 — this task is structurally incapable of doing that send itself.
- **Never draft a nudge for a confidential active deal** without first running STEP 5.
- **Never fabricate an outbound date, a thread, or a "turn" that didn't happen.** If Outlook search finds nothing, say so (`[NO OUTBOUND FOUND — VERIFY MANUALLY]`) rather than inventing a stale-since date.
- **Thresholds stay parameterized** — never hardcode a bare "5" or "7" inline in the run logic; always read from the named `*_THRESHOLD_BUSINESS_DAYS` variables in STEP 4.
- **Never re-flag a PARKED deal.**
- Routing canon: the completion summary goes to `ggoldberg@oxfordra.net` ONLY. No cc to egoldberg or anyone else.
- This task is read-and-draft only — it never edits Notion's `Last Activity`/`Next Action` fields (that would let a scheduled run's own touch reset the very staleness clock it's supposed to measure). **This holds for STEP 3b mismatches too:** a mismatch is REPORTED, never silently reconciled. Correcting the field would destroy the only evidence that the tracker and the live thread had diverged, and would reset the clock on exactly the deal that needed the divergence surfaced.
- **Never treat the tracker's posture text as ground truth over the live thread.** STEP 2's classification is a hypothesis drawn from a field that can be days stale; STEP 3b(b) exists to falsify it. An internal-gate exclusion whose tracker text claims a document is unsent is not settled until a recipient-domain search agrees.