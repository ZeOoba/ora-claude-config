---
name: next-action-date-stamping-already-wired
description: "The three deal-touching skills already stamp Next Action Date (wired 2026-08-12, commit 0f5c23a, live at runtime) — a flat 3/9 coverage count is NOT evidence of non-adoption"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 4b640096-02c2-4f5a-8381-f8096c5ed250
  modified: 2026-08-17T14:12:07.192Z
---

`Next Action Date` stamping is **already wired and live** in all three deal-touching skills. Do not propose, plan, or build it again.

- Commit `0f5c23a` (2026-08-12), `feat(pipeline-stamping): wire Next Action Date into the deal-touching skills`, one day after the tracker gained the field.
- `acquisition-underwriting` → PIPELINE & LOGGING (stamp only when the verdict carries a date) · `loi-generation` → Phase 6 step 5 (normally the seller-response deadline; deliberately kept distinct from `LOI Expiration Date`) · `deal-execution` → NOTION PIPELINE STAMPING (called out as the highest-value stamper; carries the NEAREST dated obligation, not the furthest).
- `exception-detection` is a **consumer**, not a stamper, and is explicitly instructed not to backfill (Hard Invariant 7).
- Verified 2026-08-17: the runtime bundle at `AppData/Roaming/Claude/local-agent-mode-sessions/skills-plugin/583f08bc-…/a6ad2c61-…/skills/` is **byte-identical** to the `ora-skills` repo copy for all four files. No repo-vs-live drift on this class. Note these three skills are NOT in `~/.claude/skills` — that mirror holds only 6 ORA-authored skills; the rest are served from the LAMS skills-plugin bundle, so grepping `~/.claude/skills` alone returns a false "no live copy."

**Why:** on 2026-08-17 the Deal Command Board reported `Next Action Date` coverage flat at 3 of 9 open rows — identical to the 3-of-9 measured when the field was added on 08-11 — and I read that as "no skill has adopted the stamp" and recommended wiring it. The wiring already existed. The coverage number does not measure adoption; it measures how many open rows have been TOUCHED by a deal-touching skill since the wiring date. Eight of the nine open rows were last active 07-09 to 07-24, all pre-wiring; exactly one (754 Old State Route 74, 08-12) has seen a run since, and its NULL is correct behavior — the Feasibility Period / §31 Parking Contingency dates were still to be diaried off the executed PSA, with the Effective Date itself in conflict (Aug 10 vs Aug 11), so the date was genuinely underdetermined and the skill's own anti-fabrication rule says leave it NULL.

**How to apply:** a flat or low coverage count on a recently-added Notion field is not evidence the writers are missing. Before recommending a stamping retrofit, (1) grep the candidate skills for the field name, (2) check the wiring commit date, and (3) compute the real denominator — rows whose activity date is ON OR AFTER the wiring date. A field cannot populate on records nobody has worked. This is the same trap as [[feedback_absence_claims_need_verification_before_building]] (absence usually means built-but-disconnected, or here, built-and-connected-but-unexercised) and the metric-denominator error in [[reference_hookify_noop_hooks_every_tool_call]] (bucket by the event's own date, not by a file's mtime). Related: [[feedback_verified_null_vs_inferred_null]] — 3/9 with an unstated denominator is an inferred null dressed as a measurement.
