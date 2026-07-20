---
name: ora-deal-aging-sla
description: Weekday counterparty-aging SLA — computes days-since-last-outbound per open deal ask (broker/counsel/lender) via live Outlook search; drafts (never sends) a nudge past ratified per-class thresholds (broker 5bd/counsel 7bd/lender 7bd, ratified 2026-07-18). Draft-only, Hard Invariant 1. v1.0.
output_contract:
  version: 1
  blocks:
    - id: aging-nudge-drafts
      artifact: { type: outlook_draft, folder: Drafts }
      freshness_window_hours: 30
      expected_on: { cron: "20 9 * * 1-5" }
      on_missing_severity: info
    - id: completion-row
      artifact: { type: notion_page, parent_id: 32b6ecd8-9e59-81f2-b329-df3fd0e25062, title_pattern: "Deal Aging SLA — {DATE}" }
      freshness_window_hours: 30
      expected_on: { cron: "20 9 * * 1-5" }
      on_missing_severity: warn
---

# ORA Counterparty-Aging SLA (v1.0, ratified — 2026-07-18)

STATUS: Thresholds ratified by Gabriel 2026-07-18 (see STEP 4). Plan 3 of the 2026-07 setup-improvement effort.

AUTOMATION-BUDGET JUSTIFICATION: Closes a real, already-realized gap. On 2026-07-13 the ORA Monday Sync flagged 754 Old State Route 74 (Cincinnati) as "31 days stale" on a PSA draft awaiting counsel — a stall that reached 36-38 days before a weekly board caught it by chance, not by design. Deal-command-board (weekly, Monday) tracks days-in-STAGE against Notion timestamps; it does not track days-since-last-OUTBOUND-TOUCH against the actual counterparty thread, and it only runs once a week. This task is the daily (weekday) counterpart, keyed on the live Outlook thread rather than a Notion date field that can go stale exactly when work is happening off-Notion.

GUARD CONDITION: If the Notion Acquisition Pipeline Tracker is unreachable, or zero deals have a qualifying open outbound ask (see STEP 2), still post STEP 7's dated child page (stating the guard condition triggered) and exit — do not halt, do not fabricate a deal list or an aging number.

---

## STEP 1 — Pull active pipeline deals

Query the Notion Acquisition Pipeline Tracker (data source `collection://bcfe4a037e614ac1a0bbc44174fa138b`) via `notion-query-data-sources` (SQL mode). Pull: Deal Name, Address, Stage, Next Action, Deal Owner, Broker / Source, Key Attorney, Lender, Last Updated, `date:Last Activity:start`, `date:Target Close Date:start`.

Exclude the same closed/dead stages `ora-deal-command-board` excludes, so the two boards never silently diverge on what counts as "open": Stage NOT IN ('Closed Won', 'Passed', 'Killed — Reneg Only', 'Killed — Note/Short-Sale in Discussion'). This must be a full, unpaginated pull (page on `has_more`/`next_cursor` until exhausted) — a partial pull that silently drops a stalled deal is worse than no run at all.

**PARKED exclusion (mirrors `ora-deal-command-board` STEP 2 verbatim):** skip any deal whose Next Action text contains "PARKED" — nudging a parked deal's broker/counsel would be actively wrong (dry-run evidence: Liberty Office Park's last outbound to its broker is 40 days old, but it is PARKED pending the Cincinnati-cluster go/no-go — a naive age check alone would have wrongly flagged it).

## STEP 2 — Identify deals with a genuine open outbound ask

Not every open-stage deal is waiting on a counterparty. Only flag a deal as having an open ask if its Next Action text (or Stage) describes ORA waiting on an external party's response — an LOI submitted and not yet countered/executed, a PSA draft/redline in the other side's court, or a broker chase for updated seller terms. Do NOT flag: deals awaiting Gabriel's own decision (internal gate, not a counterparty-aging risk); deals where the ask is already resolved against ORA (no live ask to age); PARKED deals.

For each qualifying deal, classify the open ask by counterparty class:
- **broker** — awaiting a broker/seller response to an LOI or counter (use the Broker / Source field for identity/contact).
- **counsel** — awaiting a PSA turn, redline response, or closing-condition confirmation from opposing/seller's counsel (use the Key Attorney field if populated; if null — as it currently is even for a deal with an active counsel ask — fall back to the counterparty names/domains visible in the matched Outlook thread itself, per STEP 3, and flag the missing Key Attorney field as a data-quality gap in the run summary rather than silently guessing).
- **lender** — awaiting a term sheet, commitment letter, or covenant response (use the Lender field).

## STEP 3 — Compute days-since-last-outbound via Outlook

For each deal with a qualifying open ask, use `outlook_email_search` to find the counterparty thread: search by the deal's street address and/or "[Address] PSA"/"[Address] LOI"-style subject terms, and, where a contact email or domain is known, narrow with the `recipient` filter rather than free-text `query` — free-text search on this connector is relevance-ranked, not literal, and returned unrelated daily-brief mail in testing when only a property-name query was used. Prefer recipient filtering whenever a counterparty email/domain is available.

**Mandatory recipient-domain fallback before concluding anything (added 2026-07-20 after a real miss).** The live thread subject often does NOT contain the deal's full street address — a PSA thread may be titled with a truncated or informal property name. So an address-only subject search can silently miss the actual external-counterparty thread and either return only ORA-internal/digest/automated mail or land on a stale leg. Therefore: if the address/subject search returns only ORA-internal exchanges (ggoldberg@/egoldberg@/our own counsel), digest/brief/automated mail, or nothing external, you MUST re-search with a `recipient`-domain filter derived from every counterparty domain available for the deal — the Broker / Source, Key Attorney, and Lender field contacts, plus any counterparty domains named in the deal file — BEFORE flagging `[NO OUTBOUND FOUND — VERIFY MANUALLY]` or computing a stale-since date. Only after the domain-filtered search also comes up empty is a `[NO OUTBOUND FOUND]` flag or an aging figure legitimate. Real defect this prevents (2026-07-18 run): the "754 Old State PSA" thread with the seller's counsel at `kmklaw.com` was missed by a "754 Old State Route 74"-subject search, so the run reported a false 25-business-day counsel breach when the deal was in fact in active same-week negotiation; a `recipient:kmklaw.com` (or `recipient:gerth`) re-search surfaces it immediately.

Within the matched thread, find the most recent message **sent by ORA (ggoldberg@ or egoldberg@) to the external counterparty** (not an internal cc, not a reply from the counterparty, not an ORA-internal exchange with our own counsel about the same deal — testing found Eric Goldberg emailing Phil Collins, ORA's OWN transaction counsel, in the same thread as the Seller's counsel exchange; only the outbound leg to the external party counts). Compute days-since as business days (Mon-Fri; do not count Sat/Sun) from that message's `sentDateTime` to today.

If no qualifying outbound message is found at all, do not fabricate a stale-since date — flag the deal as `[NO OUTBOUND FOUND — VERIFY MANUALLY]` in the summary rather than silently treating it as either 0 days or infinitely stale.

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

Post a NEW DATED CHILD PAGE under the Notion Ops Hub parent page (`32b6ecd8-9e59-81f2-b329-df3fd0e25062`), titled exactly `"Deal Aging SLA — {YYYY-MM-DD}"` (today's date) — a distinct page created fresh each run, never an appended row/block inside an existing page's body (an append isn't reliably freshness-checkable by a downstream contract-verification pass; a new titled child page is — this is the standard pattern for every task that posts a completion record to the Ops Hub, see `ora-deal-command-board` STEP 6). Its content lists: deals scanned, deals with a qualifying open ask, deals breaching by class, deals suppressed for confidentiality, deals flagged `[NO OUTBOUND FOUND — VERIFY MANUALLY]`, and how many nudges were drafted. Then email a one-paragraph summary to `ggoldberg@oxfordra.net` ONLY (no cc — routing canon) via `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`. On a COM failure for either the drafts or the summary send: retry once, then flag loudly in the Notion Ops Hub page if the retry also fails — do not halt the run.

---

## HARD GUARDRAILS (verbatim, non-negotiable)

- **Never call `.Send()` on a nudge draft.** An actual outbound send to a broker, counsel, or lender requires Gabriel's explicit in-turn confirmation per Hard Invariant 1 — this task is structurally incapable of doing that send itself.
- **Never draft a nudge for a confidential active deal** without first running STEP 5.
- **Never fabricate an outbound date, a thread, or a "turn" that didn't happen.** If Outlook search finds nothing, say so (`[NO OUTBOUND FOUND — VERIFY MANUALLY]`) rather than inventing a stale-since date.
- **Thresholds stay parameterized** — never hardcode a bare "5" or "7" inline in the run logic; always read from the named `*_THRESHOLD_BUSINESS_DAYS` variables in STEP 4.
- **Never re-flag a PARKED deal.**
- Routing canon: the completion summary goes to `ggoldberg@oxfordra.net` ONLY. No cc to egoldberg or anyone else.
- This task is read-and-draft only — it never edits Notion's `Last Activity`/`Next Action` fields (that would let a scheduled run's own touch reset the very staleness clock it's supposed to measure).