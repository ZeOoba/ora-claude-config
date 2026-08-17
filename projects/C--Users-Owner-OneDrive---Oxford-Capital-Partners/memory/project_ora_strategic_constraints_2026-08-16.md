---
name: ora-strategic-constraints-2026-08-16
description: "Gabriel's ratified answers (2026-08-16) on ORA's binding constraints, income levers, funnel leaks, autonomy posture, and headcount plan — the frame for prioritizing any Claude build"
metadata: 
  node_type: memory
  type: project
  originSessionId: 04649f52-2fab-4ed0-82ed-62ce390a746b
  modified: 2026-08-16T19:24:57.221Z
---

Ten-question discovery, answered by Gabriel 2026-08-16. Use this as the prioritization frame for any proposed skill, automation, or system build — it is the "why" that CLAUDE.md's invariants and buy-box do not encode.

**Binding constraints (both, not one):** deal flow / sourcing AND ops / asset-management capacity. Capital and personal will are not the limit.

**Income levers:** property-level NOI (rent growth, CAM recovery, escalation enforcement, lease-up) AND equity value / AUM compounding toward $700–800M. NOT fee capture, NOT third-party AUM — ORA stays a family-office principal, not a fee manager.

**90-day success, in Gabriel's stated priority order:**
1. More deals under LOI
2. Hours returned to Gabriel
3. Institutional-grade output quality
4. Quantified expense reduction

**Actual weekly time sinks:** deal screening & underwriting · tenant/PM/property ops · data wrangling & reconciliation. (Documents/correspondence is NOT a top sink.)

**Funnel leaks that hurt most:** (a) deals never sourced at all — they trade off-market or through brokers who don't call; (b) LOI submitted, lost on price/terms. Both, not middle-funnel queue death.

**PM structure:** third-party PM firms, PLUS self-managed single-tenant properties where the tenant carries most work/expense directly. Data quality therefore varies by property class — see [[reference_ora_pm_critical_dates_feed_unreliable_2026-08-04]].

**Off-market outreach capacity:** Gabriel would work 200 qualified leads/month via automated outreach sequences AND by making calls himself on warm responses. Lead-gen alone is not sufficient — the sequencing layer is the actual unlock.

**Headcount:** stay lean — automation instead of hiring. The system IS the next employee. No analyst, no sourcing hire, no VA planned.

**Autonomy posture:** act on internal, draft on external. Full autonomy on data pulls, reconciliation, models, screens, Notion/workbook writes, internal reports; anything leaving the building stops for approval. He explicitly did NOT elect pre-approved routine external sends. **Tension RESOLVED same day — Gabriel ratified a narrow Invariant 1 carve-out (2026-08-16):** for COLD OFF-MARKET OWNER OUTREACH ONLY, Gabriel approves the letter/email template and the targeting rules ONCE; the engine then sends against that ratified template autonomously and routes only replies to Gabriel. Every other external class — brokers, lenders, tenants, counsel, LP/investor, government — stays draft-only under the standing invariant. **Not yet reflected in CLAUDE.md Invariant 1** (blast-radius file, contended checkout) — the amendment and an `event_log.md` entry are outstanding and must be made under a supervised edit, not ad hoc.

**Outreach send-channel ruling (2026-08-16, after P1 planning):** P1 found the ratified carve-out is **physically unrealizable at 200/mo as specified** — county records carry zero email addresses, the sole send path (`send-via-outlook.ps1`) uses session-scoped single-use tokens that structurally forbid recurring autonomous external sends, and cold email risks the firm's single operating domain. "The engine sends" is only literal with a print-mail vendor; otherwise Gabriel is hand-addressing ~50 letters/week. **Gabriel ruled: fix the existing pipeline first, decide volume later.** Scope = P1 Phase 0 — revive the loop, seed the missing `mail-log.csv` (the 21-day cadence gate is currently blind), enforce DNC at render time (set in Notion but never read — grep-verified), refresh the master frozen at vintage 2026-06-10. Print-mail vendor and the 200/mo target are DEFERRED, not rejected.

**Output trust:** Gabriel rewrites, distrusts, or redoes by hand ALL FOUR output classes — underwriting models/IC memos, portfolio/ops reporting, correspondence/documents, research/market intel. Diagnosis: the gap is verification and sourcing discipline, not generation. Related: [[feedback_verified_null_vs_inferred_null]], [[feedback_refute_pass_proactive_default]], [[feedback_artifact_citation_requirement]].
