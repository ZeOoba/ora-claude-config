---
name: ora-deal-aging-sla
description: Weekday counterparty-aging SLA — computes days-since-last-outbound per open deal ask (broker/counsel/lender) via live Outlook search; drafts (never sends) a nudge past ratified per-class thresholds (broker 5bd/counsel 7bd/lender 7bd, ratified 2026-07-18). Also reports Notion-vs-Outlook posture mismatches (STEP 3b) and drafted-but-unshipped LOIs past their own stated expiration (STEP 3c) as first-class findings. Draft-only, Hard Invariant 1. v1.4. [MODEL: claude-opus-5 observed | checked 2026-08-12 via live-run transcript canary]
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

# ORA Counterparty-Aging SLA (v1.4)

STATUS: Thresholds ratified by Gabriel 2026-07-18 (see STEP 4) — unchanged in v1.4. Plan 3 of the 2026-07 setup-improvement effort.

CHANGELOG — v1.4 (2026-08-05, Gabriel-directed, skill-library-audit correction pass): new STEP 3c closes a real, confirmed coverage gap the audit surfaced — a drafted-but-never-sent LOI (STEP 2's internal-gate exclusion) had no aging check at all, and 470 McCormick Blvd's LOI FINAL v2 sat unshipped 21 days past its own 6/17/2026 expiration before being killed 07-08 with nothing in the fleet watching that clock. STEP 1's pull now includes `LOI Status`/`LOI Expiration Date`; `loi-generation` v1.5 (companion commit, `ora-skills`) now writes the offer expiration into that dedicated Notion date column instead of only `Next Action` prose, closing the same embedded-arithmetic gap STEP 3b was hardened against 2026-08-03. Report-only — STEP 3c never runs an Outlook search or drafts a nudge, since a document that never shipped has no counterparty thread to check.

CHANGELOG — v1.3 (2026-08-03, per Gabriel): closes two defects the 2026-08-03 run surfaced. (1) STEP 1 prescribed `notion-query-data-sources` SQL mode as the only mechanism, so every run that hit the tool's entitlement gate had to rediscover a recovery by hand; STEP 1 now carries a mandatory three-rung fallback ladder led by view mode against the tracker's *unfiltered* Default view — measured working in the same session, seconds after SQL mode was gated — plus the three hazards that rung brings (filtered-view silent partial pulls, spilled oversized results, cursor pagination). (2) New STEP 3b mismatch class for **embedded arithmetic**: a hardcoded aging anchor living in `Next Action` prose, which on 08-03 had rotted into a false 7-business-day counsel breach on 754 Old State Route 74. Per Gabriel's ruling that day, an aging anchor belongs in a computed field or nowhere — STEP 3 now recomputes unconditionally and never reads a figure out of prose. STEP 3 additionally requires the mirrored `sender:<domain>` search, without which an inbound counterparty reply is invisible to a recipient-only search (the miss that would have left 754 reported as a live counsel ask after seller's counsel had already answered).

CHANGELOG — v1.2 (2026-07-28, per Gabriel): closes a defect the task committed against itself on two consecutive runs. STEP 3b(b)'s recipient-domain search was conditional on a counterparty domain already being present, so a row whose tracker contact fields were null was reported as an *unverifiable exclusion* rather than checked — while the broker's identity sat in the deal folder. New STEP 3b(b-i) makes a three-rung escalation ladder mandatory (tracker fields → deal-folder LOI letterhead / OM contact page → surname search), forbids guessing a domain from a firm name, bars `[UNVERIFIABLE]` as a verdict until every rung is climbed and reported, and restates that free-text address search is relevance-ranked so its silence is never evidence of absence. Guardrails additionally clarify that the standing "never edit the Notion field" rule is scoped to posture/clock fields and does not bar backfilling a missing counterparty contact from a primary source on Gabriel's instruction.

CHANGELOG — v1.1 (2026-07-24, per Gabriel): STEP 1's data-source id corrected from the undashed to the dashed UUID (the undashed form never resolved — every run before this date failed its first query). New STEP 3b makes Notion-vs-Outlook posture mismatch a first-class reported finding and, more importantly, requires falsifying STEP 2's internal-gate exclusions against the live thread before trusting them.

AUTOMATION-BUDGET JUSTIFICATION: Closes a real, already-realized gap. On 2026-07-13 the ORA Monday Sync flagged 754 Old State Route 74 (Cincinnati) as "31 days stale" on a PSA draft awaiting counsel — a stall that reached 36-38 days before a weekly board caught it by chance, not by design. Deal-command-board (weekly, Monday) tracks days-in-STAGE against Notion timestamps; it does not track days-since-last-OUTBOUND-TOUCH against the actual counterparty thread, and it only runs once a week. This task is the daily (weekday) counterpart, keyed on the live Outlook thread rather than a Notion date field that can go stale exactly when work is happening off-Notion.

## STEP 0 — DOUBLE-FIRE ENTRY GUARD (added 2026-08-09; run before STEP 1)

**This task has double-sent twice.** On **2026-07-20** it emailed at 11:02 and again at 23:31. On **2026-08-09**, during the overnight-offline catch-up burst (`ora-health-guard` woke 219 min late), it emailed at **08:59:11** and again at **09:20:09** — two summaries of the same date, seven minutes apart in content and twenty-one in delivery, with different headline text because STEP 7 lets the run compose it. Nothing stood it down. Each fire also posts its own dated child page, so a double-fire leaves two `Deal Aging SLA — {DATE}` pages under the Ops Hub.

Run this as the first action of the run:

```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py claim --task ora-deal-aging-sla --block main --run-id <run_id> --ttl-min 30
```

- **Exit 10** → today's run already completed. Log `BLOCK_MAIN_ALREADY_COMPLETE_TODAY`, **exit without drafting, posting, or emailing**, and report it as a NORMAL skip (not a miss) citing the earlier run's Notion page.
- **Exit 11** → another fire is live. Stand down identically.
- **Exit 0** → proceed to STEP 1.

Once STEP 7 lands, run the full command (a short form exits 2 and nothing is recorded):

```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py complete --task ora-deal-aging-sla --block main --run-id <run_id> --notion-page-id <STEP 7 page id> --email-sent-at <ISO8601>
```

If the run aborts instead, record that rather than leaving the claim dangling:

```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py fail --task ora-deal-aging-sla --block main --run-id <run_id> --error "<what broke>"
```

**Only the run that holds the claim may call `complete` or `fail`.** A run that stood down at STEP 0 (exit 10 or 11) calls NEITHER — it did not claim anything, and calling `fail` would release the live run's claim. A non-owner is refused with exit 12 and nothing is written. Full contract: `_shared/README-DOUBLE-FIRE-GUARD.md`. **Do not "fix" a double-fire by retiming this task's cron** — the burst is documented fleet-wide behavior; the guard belongs here.

The nudge **drafts** are exempt from the concern (they are drafts, never sends, per Hard Invariant 1), but a duplicate run still creates duplicate drafts, so the guard covers the whole run rather than the send alone.

GUARD CONDITION: If the Notion Acquisition Pipeline Tracker is unreachable, or zero deals have a qualifying open outbound ask (see STEP 2), still post STEP 7's dated child page (stating the guard condition triggered) and exit — do not halt, do not fabricate a deal list or an aging number. **A zero-qualifying-ask run is not an early exit from STEP 3b(b):** run the posture check on the internal-gate exclusions first, because "nothing qualifies" is itself frequently a stale-tracker artifact, and report any mismatches on the page before exiting.

---

## STEP 1 — Pull active pipeline deals

Query the Notion Acquisition Pipeline Tracker (data source `collection://bcfe4a03-7e61-4ac1-a0bb-c44174fa138b`) via `notion-query-data-sources` (SQL mode). Pull: Deal Name, Address, Stage, Next Action, Deal Owner, Broker / Source, Key Attorney, Lender, Last Updated, `date:Last Activity:start`, `date:Target Close Date:start`, **`LOI Status`, `date:LOI Expiration Date:start`** (added 2026-08-05, v1.4, for STEP 3c), **`date:Next Action Date:start`** (added 2026-08-11, for the missed-commitment check below), **`Listing Ask (Verified)`, `date:Listing Ask Verified On:start`, `Listing Ask Source`, `Total SF`** (added 2026-08-12, for STEP 3e — these three ask fields are written by `ora-deal-sourcing-scan` STEP 5B and exist on the tracker as of 2026-08-12; a run that omits them from the pull makes STEP 3e silently return zero, which would read as "no contradictions" when it really means "did not look").

**SQL mode is ENTITLEMENT-GATED and fails nondeterministically — the view-mode fallback below is mandatory, not optional (added 2026-08-03 after the gate fired again).** `notion-query-data-sources` in SQL mode returns `validation_error` / `entitlement_required` (*"Your workspace has reached the usage limit for Query Data Source… upgrade to Business"*, `source: mcp_tool_upsell`) once the quota is drawn down. **This is a gate on the MCP tool's tier, NOT a Notion plan limit and NOT a workspace data allowance — never recommend a Notion upgrade to fix it, and never retry the same SQL call in a loop, which just burns the same quota.** It is quota-based and therefore nondeterministic: it passes some runs and fails others depending on what else drew from the quota that day (`ora-pm-ledger` DEFECT 2 measured the same gate from the other side on 2026-07-16). On an entitlement error, do NOT halt and do NOT treat it as a guard condition — walk this ladder:

1. **View mode against the tracker's unfiltered Default view** — `{"mode":"view","view_url":"https://www.notion.so/46c8a5c68b374c53a10d0f55c97613e5?v=51ae740498f94cb58e761522f0d84035","page_size":100}`. **Measured 2026-08-03: this returned all 18 rows seconds after SQL mode returned `entitlement_required` in the same session** — view mode is not drawing on the exhausted quota. (`ora-pm-ledger`'s DEFECT 2 note claims SQL *and* view mode both require Business + Notion AI; that claim is contradicted by direct observation and should not be relied on to skip this rung.)
2. **`notion-search` scoped to the data source** — never entitlement-gated, but recall is ranked/semantic and therefore best-effort: it can miss rows, so a pull built this way MUST be labelled best-effort and can NOT satisfy the full-pull requirement below on its own.
3. **Nothing worked ⇒ the STEP 7 guard condition fires** — post the dated page stating the tracker was unreachable. Never a silent pass, never a fabricated deal list.

**Three hazards specific to the view-mode rung — all three will bite:**

- **VERIFY THE VIEW IS UNFILTERED BEFORE TRUSTING ITS ROWS — and identify it by UUID, never by name.** View mode executes that view's *own* filters, and a filtered view hands back a silently partial pull wearing the disguise of a successful query. **This database contains duplicate-named views where one copy is filtered and the other is not** — there are two views named `Pipeline Board` and two named `Closing Timeline`; in both pairs the emoji-prefixed copy (`🗂️`/`📅`) is unfiltered while the plain-named copy carries an `advancedFilter`. Selecting a view by name is therefore a coin flip. The four views that DO filter, by UUID, verified 2026-08-03: `33c6ecd8-9e59-8151-93ad-000cc92fe0cc` (Pipeline Board — excludes `Passed`) · `33c6ecd8-9e59-8156-8659-000cc1e630de` (Closing Timeline — excludes `Passed`) · `33c6ecd8-9e59-8135-afb1-000ca16f0ac9` (IC Checklist — excludes `Passed` + `Closed Won`) · `3976ecd8-9e59-81e3-b0e4-000c82686425` (Stale Deal Watch — excludes three stages **and** filters `Last Activity` on-or-before a hardcoded `2026-07-10`, so it silently rots as well). The **Default view** (`51ae7404-98f9-4cb5-8e76-1522f0d84035`) is unfiltered and displays all 30 properties. Do not take this list on faith either — `notion-fetch` database `46c8a5c6-8b37-4c53-a10d-0f55c97613e5` and confirm the view you are about to use has **no `advancedFilter` key**, since anyone can add one to any view at any time.
- **The result will exceed the tool's inline output limit and be spilled to a file.** 18 rows of this tracker is ~57KB (the `Next Action` fields are long-form prose). The tool returns a path under `…/tool-results/` instead of inline JSON. Parse that file (`json.load`, `PYTHONIOENCODING=utf-8` — em-dashes in deal names hit the cp1252 stdout gotcha); do not treat the truncation notice as a failed query.
- **View mode paginates on `start_cursor`/`next_cursor`, not `offset`.** `page_size` maxes at 100. Page until `has_more` is `false` and say so in the run record — the full-pull requirement below is unchanged by which rung produced the rows.

**The DASHED UUID above is required — do not "tidy" the dashes out.** `notion-query-data-sources` rejects the undashed form (`collection://bcfe4a037e61…c44174fa138b`, elided here on purpose so a mechanical sweep for undashed ids does not false-positive on this warning) with a `validation_error` / `sql_invalid` reading *"table \"collection://…\" was not exposed for this request"* — which looks like a permissions or sharing problem and sends you debugging the wrong thing entirely. This SKILL.md carried the undashed id from authoring until 2026-07-24, so every run before that date failed its first query and recovered by hand. If the id ever stops resolving, `notion-fetch` the database id `46c8a5c6-8b37-4c53-a10d-0f55c97613e5` and read the dashed URL out of the `<data-source url="...">` tag rather than guessing at the format.

Exclude the same closed/dead stages `ora-deal-command-board` excludes, so the two boards never silently diverge on what counts as "open": Stage NOT IN ('Closed Won', 'Passed', 'Killed', 'Killed — Reneg Only', 'Killed — Note/Short-Sale in Discussion'). Bare `'Killed'` is deliberate and must not be "tidied" out as redundant with the two `Killed —` variants: it is a distinct stage value, and its absence let E Fulton (Stage `Killed`, retired 2026-07-26, no open action) pass the filter into the 2026-07-27 run. Added 2026-07-27; mirrored the same day in `ora-deal-command-board` STEP 1, and extended 2026-08-03 (Gabriel-ratified) to `ora-health-guard` block 4d, which had been carrying only three of the five values. **All FOUR sites must stay identical (`ora-weekly-hygiene` check C made explicit the same day, as the inclusion complement) — any change is made in all four SKILL.mds in the same session.** The two `Killed —` values are defensive, not observed: verified 2026-08-03 that the tracker's `Stage` select offers only the nine canonical options and no row carries either variant, so all three filters return identical rows today. Keep them anyway, for the same reason bare `'Killed'` is kept — and match on the em-dash (`—`), since a hyphen silently fails the string comparison. This must be a full, unpaginated pull (page on `has_more`/`next_cursor` until exhausted) — a partial pull that silently drops a stalled deal is worse than no run at all.

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

**The anchor is always the thread's `sentDateTime` — never a date quoted in `Next Action`.** If the tracker text names an anchor date or an elapsed-day count, treat it as a hint about where to search and nothing more, then recompute from scratch and report any disagreement per STEP 3b's embedded-arithmetic mismatch class. **Also check for an inbound reply before concluding the ask is still live:** a `recipient:<domain>` search matches only mail ORA *sent*, so a counterparty's answer will not appear in it. Run the mirrored `sender:<domain>` search too. On 2026-08-03 that is precisely what flipped 754 — seller's counsel had returned the revised PSA 2.5 hours after ORA's own chase on the same day, so the open ask had moved to ORA's court and no nudge was warranted.

If no qualifying outbound message is found at all, do not fabricate a stale-since date — flag the deal as `[NO OUTBOUND FOUND — VERIFY MANUALLY]` in the summary rather than silently treating it as either 0 days or infinitely stale.

## STEP 3b — Posture mismatch is a FIRST-CLASS finding, not prose (added 2026-07-24)

STEP 2 classifies each deal off the tracker's own `Next Action` / `Stage` / `PSA Status` / `LOI Status` text. That text is exactly the thing that goes stale when work happens off-Notion — which is this task's whole reason to exist. So the tracker's claim about *whose court the ask sits in* must itself be treated as a claim to be checked, not as ground truth.

**(a) For every deal that qualified in STEP 2:** while you have the thread open from STEP 3, compare what the tracker asserts against what the thread shows, and record any disagreement as its own structured row in the STEP 7 output — one row per mismatch, never folded into the aging number or buried in narrative prose.

**(b) For every non-PARKED deal that STEP 2 excluded as an internal gate:** if its tracker text makes an Outlook-falsifiable claim that a document has NOT gone out — "not sent", "awaiting Gabriel's review/sign-off", "staged for review", "pending approval" — run the STEP 3 recipient-domain search anyway. This is cheap (one search) and it is the single highest-value check in the task. **If the document did in fact go out, the deal re-enters STEP 2 as a genuine open ask of the matching class and is aged normally from that outbound** — do not leave it excluded on the strength of a tracker field the thread just contradicted.

**(b-i) A missing tracker contact does NOT excuse you from the check — derive the domain from the deal folder (added 2026-07-28 after two consecutive runs failed this way).** Earlier wording made the (b) search conditional on "whenever a counterparty domain is available from Broker / Source, Key Attorney, Lender, or the deal file." That conditional was read as permission to stop when the tracker's own fields were null, and on both the 2026-07-27 and 2026-07-28 runs 1333 Research Road was reported as an *unverifiable exclusion* on exactly that basis — while the broker's name sat in the deal folder the entire time. The escalation ladder is now mandatory, in order:

1. `Broker / Source`, `Key Attorney`, `Lender` on the tracker row.
2. **The deal folder** under `OneDrive…/Business/Investment Candidates -- <year>/<deal>/` — the two reliable places a counterparty identity is recorded are the **LOI letterhead addressee block** (`LOI <deal> …docx` — carries name, firm, and mailing address) and the **OM contact page** (usually the final page — carries the full listing team with direct emails and phone numbers, and distinguishes the deal contact from a compliance-only "Broker of Record").
3. A name-only free-text Outlook search on the counterparty's **surname** (`recipient:<surname>`), which resolves the address even when the domain is unguessable.

**Never guess a domain from the firm's name.** 1333 Research Road's broker is at Coldwell Banker *King Thompson*; his address is `@kingthompson.com`, and a guessed `@coldwellbanker.com` would have returned nothing and manufactured a second false "no correspondence" finding on top of the first.

**`[UNVERIFIABLE]` is a terminal verdict only after all three rungs come up empty, and the report must say which rungs were actually climbed.** A row reported as unverifiable when the contact was sitting in the deal folder is an inferred null dressed up as a verified one — the precise failure this task exists to catch in the tracker, reproduced inside the task itself.

**Free-text address search is relevance-ranked, not literal — never read its silence as absence.** A bare `1333 Research Road` query returns ORA's own Daily Brief and Monday Sync digests ranked above the actual broker thread, because those digests mention the address too. STEP 3 already warns about this for aging computation; the warning applies with equal force here, and on 2026-07-28 it was applied to the aging path but skipped on this one.

A mismatch is any of:
- **Tracker behind the thread** — the field says a document was not yet sent (or is awaiting internal review) but Outlook shows it reached the counterparty. *Real case, 2026-07-24 run:* 754 Old State Route 74's `Next Action`, stamped 07-21 PM, read "NOT sent to Patterson — awaiting Gabriel's review/sign-off first", while Eric had sent the PSA with modifications to `kmklaw.com` on 07-23. Under the pre-3b doctrine that deal was an internal-gate exclusion; the check is what correctly reclassified it to a live counsel ask (1 business day, comfortably inside SLA).
- **Tracker ahead of the thread** — the field claims something was sent or asked that no outbound in the thread supports. Apply the STEP 3 recipient-domain fallback in full before asserting this: a thread you failed to find is NOT evidence that a document was never sent, and this is the direction in which a wrong call is most damaging (it invites a nudge for a turn that already happened).
- **Stage/status contradiction** — e.g. `PSA Status = Not Started` against a live PSA redline thread, or `LOI Status = Submitted` on a deal the broker has already reported as awarded elsewhere.

- **Embedded arithmetic — a hardcoded clock anchor sitting in a prose field (added 2026-08-03, third consecutive run surfacing it).** `Next Action` sometimes carries not just a posture claim but a *computed* one: a named anchor date, an elapsed-day count, and a verdict against the threshold — e.g. 754 Old State Route 74's 07-24 note, *"Counterparty-aging clock runs from 2026-07-23 (counsel class, 7-business-day threshold; 1 bd elapsed as of 07-24 — inside SLA)."* Arithmetic baked into prose is correct only at the instant it is written and rots the moment anyone sends mail. On 2026-08-03 that 07-23 anchor had drifted to **exactly 7 business days — sitting precisely on the ratified counsel threshold** — while the live thread showed the real last outbound was 07-31 (1 bd) *and* that seller's counsel had already answered. A reader taking the field literally would have manufactured a breach on a deal that was not merely inside SLA but no longer an outbound-aging item at all.

  **The standing rule, per Gabriel 2026-08-03: an aging anchor belongs in a computed field or nowhere.** Therefore: (i) **never** read an anchor, an elapsed count, or a threshold verdict out of `Next Action` — STEP 3 recomputes every figure from the live thread, always, and a prose figure is at most a hint about where to look; (ii) when a prose figure disagrees with the recomputed one, report it as its own mismatch row; and (iii) do **not** rewrite the field to correct the arithmetic — that is a posture-field write, still barred by the guardrails below.

Report each mismatch as: deal · field · what the tracker asserts (with its stamp date) · what the thread shows (with the message date) · which of the two is newer · whether it changed the deal's STEP 2 classification. **Never edit the Notion field to reconcile it** — see the guardrails; the row is the handoff to Gabriel and to the weekly `ora-deal-command-board`.

Why this is first-class output and not a footnote: on a zero-breach run the mismatch is usually the *only* actionable finding, and it is more actionable than the aging figure. When the pipeline runs ahead of the tracker, this task computes its own number off the correct live thread and looks clean — while every downstream weekly board still reads the stale field and will draw the wrong conclusion. Both of this task's genuinely useful outputs to date surfaced on zero-breach runs.

## STEP 3c — Drafted-but-unshipped LOI expiration check (added 2026-08-05, v1.4)

**Why this exists and why it is separate from STEP 2/3.** STEP 2 only ages an ask that is already outbound — waiting on a counterparty. A drafted LOI that Gabriel/Eric has not yet approved to send is deliberately excluded there as an internal gate (STEP 2: "Do NOT flag: deals awaiting Gabriel's own decision"), so it gets zero aging coverage today. Real case that motivated this: 470 McCormick Blvd's "LOI FINAL v2" carried a 6/17/2026 offer-expiration date, sat in Drafts unshipped, and lapsed 21 days before Gabriel killed the deal 2026-07-08 — nothing in the fleet was watching that clock (skill-library-audit correction pass, 2026-08-05). `loi-generation` v1.5 now writes the offer's expiration into the tracker's dedicated `LOI Expiration Date` column (added 2026-08-05) at draft time — this step is what reads it.

**Run this for every pulled deal, independent of STEP 2's classification** (a drafted LOI is explicitly excluded from STEP 2, so folding this into STEP 2 would silently drop it again):

1. Flag a deal if **all** of: `LOI Status = 'Drafting'` · Stage is not in the closed/dead exclusion list (STEP 1) · `LOI Expiration Date` is populated and is on or before today (ET).
2. **`LOI Status = 'Submitted'` or `'Executed'` past its expiration is NOT this check's concern** — an LOI that actually went out and lapsed unanswered is a live counterparty ask and is already covered by STEP 2/3's broker-class aging (5 business days) once it reaches the thread. Do not double-flag it here.
3. **A null `LOI Expiration Date` is not a flag.** Most rows predate the 2026-08-05 field, and not every deal runs through `loi-generation`. A null here means "no data," not "no defect" (verified-null-vs-inferred-null convention) — report it under a separate `[NO EXPIRATION DATA — legacy or off-skill draft]` count in the summary, never silently folded into either the flagged or clean tally.
4. **Report-only. Do not draft a nudge and do not run an Outlook search for this class.** There is no counterparty thread to check — by definition the document never went out — so STEP 5/6 do not apply here. The action this surfaces is internal (send it now with a fresh expiration, or kill/re-draft), not a counterparty follow-up.
5. Report each flagged deal as: deal name · address · `LOI Expiration Date` · days past expiration · Stage · Deal Owner. Add to STEP 7's completion page as its own titled section, "Drafted LOIs past expiration," distinct from the STEP 3b mismatch section.

## STEP 3d — Missed self-imposed commitment check (added 2026-08-11)

This is the signal the task could not previously produce at all. STEPS 3/3b/3c all age a deal against *elapsed time* or an *external* date (last outbound, LOI expiration). None of them can tell "quiet by design" from "we set ourselves a date and blew through it" — and the second is a different, more embarrassing failure, because the commitment was ORA's own.

1. Resolve each deal's next-action date by the chain in `ora-deal-command-board` STEP 2b: `date:Next Action Date:start` → an explicit ISO date parsed from `Next Action` prose → null. Keep the two sites in sync, as with the stage-exclusion list.
2. Flag a deal when its resolved next-action date is **in the past** AND `date:Last Activity:start` is **on or before** that date — the date came due and nothing was logged against it since. If `Last Activity` post-dates it, the commitment was acted on; do not flag.
3. **The PARKED exclusion still applies, but resolves differently here.** A parked deal with a past-due re-check date is reported as **"re-check due"**, not as an SLA breach — Gabriel's park instructions routinely carry an explicit revisit date (e.g. 5515 Catfish Court, parked 2026-07-24 "Revisit 2026-08-14"), and that date coming due is the park working as designed, not a lapse.
4. Where the date came from prose rather than the column, say so on the row — a flag resting on a parsed string is weaker evidence than one resting on a stamped field.
5. `DATE DIVERGENCE` rows (column and prose disagree) are reported as divergence and **never** flagged as missed on the strength of whichever date is older. Report both; let a human resolve which was meant.

Report as its own titled section in STEP 7, "Missed self-imposed dates," distinct from the 3b mismatch and 3c expiration sections.

**The tracker's own `⏰ Action Overdue` formula column is NOT this check, and never has been (confirmed 2026-08-13).** The 2026-08-13 run correctly caught 4484 Robertson Road's blown 2026-08-12 call date via STEP 3d above — but a separate glance at the tracker's `⏰ Action Overdue` formula that same day found it gave no usable signal for that row, and a repo-wide grep across every `scheduled-tasks/*/SKILL.md` and `ora-skills/*/SKILL.md` turned up **zero** references to that column by name — nothing in the fleet has ever read it. The column is also structurally unreadable by any automated consumer regardless of formula correctness: the data source schema marks it `notAvailableInQuerySql`, and both SQL mode and view-mode `notion-query-data-sources` calls return an unresolved `formulaResult://…` placeholder instead of a value (verified directly against the 4484 Robertson row, 2026-08-13) — `notion-fetch` does the same. **Do not point any future automation at `⏰ Action Overdue` expecting it to be queryable, and do not treat a blank/wrong-looking cell on the Pipeline Board as evidence a standing check missed something — STEP 3d above is the actual enforced mechanism.** Whether the formula's own logic is correct for a human looking at the rendered board is unverified either way (no browser session with Notion auth was available to check) — this note is only about its unfitness as an automation signal, not a claim about its display correctness.

## STEP 3e — Verified-ask contradiction check (added 2026-08-12)

**Why this is its own step and not a fourth STEP 3b class.** STEP 3b is defined as *the tracker's claim vs the live Outlook thread*. This check never opens Outlook — both sides of the comparison sit inside the same tracker row: a **stamped field** against the row's own **prose**. Folding it into 3b would blur what 3b means, and the skill's own history says otherwise anyway — 3c and 3d were each added as separate steps with their own report sections rather than as new 3b classes. Same pattern here.

**The gap it closes.** On 2026-08-11 `ora-deal-sourcing-scan` verified 4484 Robertson Road's published ask at $2,950,000 off the live listing detail page and emailed it. Thirty-six minutes later the tracker row was re-stamped still recording the ask as "NOT YET KNOWN — verified null" and still instructing the deal owner to ask the broker for a price on a call the next morning. This run's 3b/3c/3d checks were all clean and this task reported it only as an out-of-class finding, by hand. As of 2026-08-12 the scan writes `Listing Ask (Verified)` / `Listing Ask Verified On` / `Listing Ask Source` (its STEP 5B), so the contradiction is now mechanically detectable and must not depend on a human noticing.

**Run for every pulled deal, independent of STEP 2's classification** — a deal in an internal gate or PARKED is exactly where this rots unnoticed.

1. **Flag** a deal when `Listing Ask (Verified)` is populated AND its `Next Action` prose still treats the price as unknown or still instructs someone to obtain it. Treat as price-unknown language, case-insensitively: "not yet known", "verified null", "price unknown", "pending an OM", "awaiting OM", "asking price for sale", "ask the broker", "what are you guiding", "request price", "pending price", "TBD". Match on intent, not on this exact list — the list is illustrative, not exhaustive.
2. **Do NOT flag** when the prose already reflects the number (it quotes the ask, or is written as a response to it). The check exists to catch a row that has not caught up, not to nag about phrasing.
3. **NEVER recompute a basis floor here, and never mirror the RCT table into this task.** The per-market replacement-cost floors live in `acquisition-underwriting` (authoritative) and are already mirrored once, in `ora-deal-sourcing-scan`, which carries its own drift warning about that mirror. A third copy is a third thing to rot, and this is a counterparty-clock task with no replacement-cost competence. The contradiction is fully detectable without a floor: a populated field against price-unknown prose is a contradiction on its face.
4. **Safe arithmetic only.** If `Total SF` is populated you MAY report `Listing Ask (Verified) / Total SF` as a marketed $/SF for context — that is two tracker fields divided, no benchmark involved. If the sourcing scan recorded a gate verdict (e.g. FAIL-BASIS) cite it *as the scan's verdict, attributed*, and never restate it as this task's own finding.
5. **Stale-ask context, not a defect.** If `date:Listing Ask Verified On:start` is materially older than `date:Last Activity:start`, say so on the row — the ask may itself have moved since it was read. This is reported as context; it is never a flag on its own.
6. **A null `Listing Ask (Verified)` is not a flag.** Most rows predate the 2026-08-12 fields and not every pipeline deal is on-market or picked up by the scan. Report the count separately as `[NO VERIFIED ASK — not on-market, or not yet scanned]`, never folded into either the flagged or the clean tally. Same verified-null-vs-inferred-null convention as STEP 3c.
7. **Report-only, and do not reconcile.** Never edit `Next Action` to absorb the number — that is a posture-field write, still barred by the guardrails, and rewriting it destroys the evidence that the two systems diverged. The row is the handoff.

Report each flagged deal as: deal name · `Listing Ask (Verified)` · marketed $/SF if computable · `Listing Ask Verified On` · what the prose still asserts · `Listing Ask Source`. Its own titled STEP 7 section, "Verified ask vs stale price posture," distinct from the 3b, 3c and 3d sections.

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

Post a NEW DATED CHILD PAGE under the Notion Ops Hub parent page (`32b6ecd8-9e59-81f2-b329-df3fd0e25062`), titled exactly `"Deal Aging SLA — {YYYY-MM-DD}"` (today's date) — a distinct page created fresh each run, never an appended row/block inside an existing page's body (an append isn't reliably freshness-checkable by a downstream contract-verification pass; a new titled child page is — this is the standard pattern for every task that posts a completion record to the Ops Hub, see `ora-deal-command-board` STEP 6). Its content lists: deals scanned, deals with a qualifying open ask, deals breaching by class, deals suppressed for confidentiality, deals flagged `[NO OUTBOUND FOUND — VERIFY MANUALLY]`, how many nudges were drafted, and — as its own titled section with one row per finding, not as prose — every **posture mismatch** from STEP 3b, including any deal whose STEP 2 classification the check changed. When there are zero breaches but one or more mismatches, the mismatch section is the substance of the report and the summary email must lead with it rather than with the "0 breaches" headline. Also add STEP 3c's **"Drafted LOIs past expiration"** section (one row per flagged deal, plus the `[NO EXPIRATION DATA]` count) — on a run with zero breaches, zero mismatches, and one or more STEP 3c flags, that section becomes the substance of the report instead. Also add STEP 3e's **"Verified ask vs stale price posture"** section (one row per flagged deal, plus the `[NO VERIFIED ASK]` count). **Escalation order when the run is otherwise quiet:** a STEP 3e flag outranks 3c and 3d for the headline, because a deal owner walking into a broker call believing the price is unknown when the firm has already verified it is a live, dated exposure rather than a backlog item — if breaches and 3b mismatches are both zero, lead the email with 3e. Then email a one-paragraph summary to `ggoldberg@oxfordra.net` ONLY (no cc — routing canon) via `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`.

**PRE-SEND SENT-ITEMS PROBE (mandatory, immediately before that send).** Layer 2 of the STEP 0 guard:

```
powershell -ExecutionPolicy Bypass -File C:\Users\Owner\.claude\scheduled-tasks\_shared\outlook-sent-probe.ps1 -SubjectFile "<temp .txt containing exactly: Deal Aging SLA - {YYYY-MM-DD}>"
```

Probe the **dated stem** `Deal Aging SLA - {YYYY-MM-DD}` and nothing more. The headline this step composes is run-specific and the leading tag is inconsistent — on 2026-08-09 the two sends were `Deal Aging SLA - 2026-08-09: 0 breaches - Patterson returned…` and `[ORA] Deal Aging SLA - 2026-08-09 - 0 breaches, 1 posture mismatch…`. The stem matches both (matching is substring and normalization-tolerant); the full subject would match neither. Exit 10 → do NOT send, log `MAIN_EMAIL_ALREADY_IN_SENT_ITEMS`, record a NORMAL skip, and still call `block-sentinel.py complete` so the state file re-converges. Exit 1 → fail open: send, and record the probe gap on the Notion page. On a COM failure for either the drafts or the summary send: retry once, then flag loudly in the Notion Ops Hub page if the retry also fails — do not halt the run.

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
- **Never report a row as `[UNVERIFIABLE]` without climbing the full STEP 3b(b-i) ladder** (tracker fields → deal-folder LOI letterhead / OM contact page → surname search), and name in the report which rungs you climbed. An unverifiable verdict reached by not looking is a fabricated null.
- **The "never edit the Notion field" rule is scoped to posture and clock fields — it is NOT a bar on backfilling a missing counterparty contact.** Never touch `Next Action`, `Stage`, `PSA Status`, `LOI Status`, `Last Activity`, or `Last Updated`: editing those destroys the divergence evidence and resets the very staleness clock this task measures. `Broker / Source`, `Key Attorney`, and `Lender` are different in kind — they are identity, not posture, and a null there disables the check rather than recording a state. Backfilling one from a primary source (deal-folder LOI/OM, or a verified Outlook address) resets no clock and erases no evidence. Still: **only on Gabriel's instruction, never fabricated, and always stamped with the source document and the date** — Hard Invariant 7 binds here regardless of who asked. Worked precedent: 2026-07-28, `Broker / Source` backfilled on 1333 Research Road and 5515 Catfish Court at Gabriel's in-turn direction, each stamped with its source and with the correspondence-history caveat recorded in the field itself.