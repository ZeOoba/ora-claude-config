---
name: reference_insurance_9620_state350_and_deductible_ladder_2026-08-17
description: "9620 State 350's Hartford carrier switch has 3 open items (broker of record, GL transition, short-rate return); the deductible-ladder \"47% short\" finding was wrong and is now corrected in insurance-renewal-review v2.0"
metadata: 
  node_type: memory
  type: reference
  originSessionId: c326cc6c-2262-4af1-a3fb-5bf6f1228512
  modified: 2026-08-17T20:36:47.898Z
---

**9620 E State Route 350 (Raytown MO), confirmed 2026-08-17:** Westchester property policy cancelled mid-term 05/28/2026 (Gabriel signed 06/01/2026); replaced by bound Hartford Spectrum BOP (37 SBA CB6KKB), anniversary now 05/28 (was 10/18). Combined premium $18,885 (was $30,185); rate/$100 TIV 0.699→0.437 — no longer the worst-priced asset (3883 Livingston now is). **Three items OPEN, unresolved:** (a) broker of record unconfirmed — 3 agencies (XPT Partners, Foundation Insurance Group, KNABE) touched this property in 8 weeks, none named as servicing it going forward; (b) GL-side transition undocumented — signed cancellation covers only the property policy, no cancellation notice for the companion GL policy despite Hartford's BOP bundling GL; (c) short-rate return premium unknown — ACORD 35 calc section left blank. Full detail: Cowork memory `insurance_9620_state350.md`.

**Deductible-ladder correction:** Erie's quote tab header `"Option 1 - GL limits $2m/4m"` means every quoted tier assumes GL rebased to $2M/$4M, not held at current limits. An earlier draft compared a bound outcome to the raw quote without noticing this and wrongly concluded the credit "came in 47% short" — wrong on both arithmetic base and causal claim. Corrected: 3034 Westerville Rd quoted $7,237, bound a year later at $7,522 (1.4% above raw quote, under the 5.02%-exposure-adjusted ~$7,600) — the quote held. Four properties currently ABOVE $2M/$4M GL (Fairground Village Center, Muirkirk both $5m/5m; 3540 Fifth Ave, 1900 N Broadway both $3m/3m) would cut liability limits, not just trade retention, if they took a quoted credit at face value. Now documented as [[insurance-renewal-review]] v2.0 Step 8 ([PR #47](https://github.com/ZeOoba/ora-skills/pull/47)).

**Scheduler flag:** a weekly "Insurance tracker reconciliation (ORA)" task was registered 2026-08-17 on the **CCR fleet** via `create_trigger` (not LAMS/Cowork) — canonical `create_scheduled_task` was unreachable from that cloud session, Gabriel authorized the deviation in-turn. Trigger `trig_01LK3badqJ5wa7FyCtEE2z5W`, cron `0 13 * * 1`, next run 2026-08-24. Won't show up in `automation-health-monitor`'s dual-fleet sweep until that skill checks the CCR/`create_trigger` registry too, or the task is re-registered on the correct fleet. Flagged, not fixed — don't re-register without deliberate review.

Full session record: `event_log.md` 2026-08-17 entry.
