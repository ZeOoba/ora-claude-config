---
name: reference-808-rhoads-real-broker-is-elford-not-koon
description: "808 Rhoads Ave live correspondence runs through Elford Realty, not the Koon/Menninger listing contacts on the Notion tracker — a recipient-domain search on the tracker's own field returns zero"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3250b056-2da6-4a7e-8f84-deac7b3f343a
  modified: 2026-08-13T15:12:10.283Z
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
