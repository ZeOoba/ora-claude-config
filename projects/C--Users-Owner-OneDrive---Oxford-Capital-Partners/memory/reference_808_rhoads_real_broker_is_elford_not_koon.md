---
name: reference-808-rhoads-real-broker-is-elford-not-koon
description: "808 Rhoads Ave live correspondence runs through Elford Realty, not the Koon/Menninger listing contacts on the Notion tracker — a recipient-domain search on the tracker's own field returns zero"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3250b056-2da6-4a7e-8f84-deac7b3f343a
  modified: 2026-08-28T13:50:08.833Z
---

**808 Rhoads Avenue (Columbus, OH 43205): the tracker's `Broker / Source` field names only the LISTING side and will silently defeat a recipient-domain search.**

The Notion Acquisition Pipeline Tracker row lists James Koon (Koon Property Group, jkoon@koonpropertygroup.com) and Joe Menninger (NAI Ohio Equities, jmenninger@ohioequities.com). Verified 2026-08-13: `recipient:koonpropertygroup.com` returns **zero** ORA outbound mail, ever. `recipient:ohioequities.com` returns only unrelated Zettler Rd / E Livingston leasing threads with Matthew Osowski.

**The entire live 808 Rhoads correspondence runs through `elfordrealty.com`** — Lauren Alexander (lalexander@) and Jackie Delay (jdelay@), ORA's cooperating/buy-side broker, who appear nowhere on the tracker row. Threads: "In Contract - 808 Rhoads Ave" and "808 Rhoads DD" (2026-06-22 → 2026-06-26).

**Why it matters:** this is the failure mode [[reference-catfish-court-broker-correspondence-claim-false]] records from the other direction. STEP 3b(b-i) rung 1 of `ora-deal-aging-sla` reads the tracker's contact fields — here it comes up empty and would hand back an inferred null. The 2026-08-13 run only reached the real thread because a concurrent session's Outlook draft happened to name "Lauren." Rung 2 (deal folder) or a surname search is mandatory on this deal.

**Deal-state facts recovered from that thread, absent from the tracker as of 2026-08-13:**
- 2026-06-23 — broker relayed **seller needs ~$3.5M**, vs. the tracker's planned $80/SF (~$2.86M) LOI. ~22% gap.
- 2026-06-26 — **"Rhoads is officially out of contract. Please let us know if you have any further interest."** The competing buyer terminated.
- 2026-06-26 — **"Keep us posted if you'd like to pursue it around $80/SF."**
- ORA's last outbound: 2026-06-26. The ball has been on ORA's side since.

Detail and evidence: Notion Ops Hub page "Deal Aging SLA — 2026-08-13". Backfilling `Broker / Source` with the Elford contact is permitted (identity, not posture) but needs Gabriel's in-turn instruction, stamped with source and date.

**RECURRED 2026-08-28, 15 days later — the tracker field is still uncorrected.** A same-day `ora-deal-aging-sla` run found a never-sent 2026-08-13 draft addressed to jkoon@koonpropertygroup.com and initially misread it as a real outbound (isDraft was not checked first — a new lesson: always verify `isDraft` on a search-result message before treating it as a sent anchor, since Outlook search returns drafts alongside sent/received mail with no visual distinction in the summary). Once corrected, the true last SENT outbound to Elford Realty (lalexander@elfordrealty.com) was 2026-06-26 — roughly 45 business days stale as of 2026-08-28, the worst aging figure across that entire run. A second, correctly-addressed, well-written follow-up draft to Lauren Alexander (cc Jackie Delay, dated 2026-08-13) already exists in Drafts and has also never been sent — recommended to Gabriel for review/send rather than duplicating it. Evidence: Notion Ops Hub page "Deal Aging SLA — 2026-08-28" (corrected mid-run; the page's edit history shows the original wrong finding). If this recurs a third time, the `Broker / Source` backfill should stop waiting for a fresh in-turn instruction each time and be raised as a standing ask.

**RESOLVED 2026-09-06 (third recurrence → standing write).** Gabriel ratified in-turn ("Fix this") on the 2026-09-03 nudge's systematization candidates. `Broker / Source` on the 808 Rhoads row now carries Elford (Alexander/Delay) as LIVE THREAD with Koon/Menninger retained as LISTING SIDE, stamped `[backfilled 2026-09-06 by ora-stale-pipeline-nudge …]`. Rule generalised in ora-stale-pipeline-nudge SKILL.md v2.4 → STANDING WRITES: identity-only append of a sweep-proven live counterparty onto a row no longer waits for a per-run instruction. Same run: the 08-13 Elford draft was repaired in place (figures restored, REPAIRED_OK) and a sanctioned send path now exists — `_shared\send-parked-drafts.ps1` (list by default; `-EntryId` + `-Confirm SEND`; figure gate). Send itself remains Gabriel's in-turn act.
