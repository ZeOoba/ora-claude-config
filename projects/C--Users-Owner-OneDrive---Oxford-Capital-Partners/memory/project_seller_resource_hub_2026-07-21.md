---
name: project-seller-resource-hub
description: "Seller-intent resource hub (3-4 SEO articles) — kicked off 2026-07-21 in background worktree wt-seller-resource-hub, branch feature/seller-resource-hub; scoping + drafting in progress"
metadata: 
  node_type: memory
  type: project
  originSessionId: 662eac5c-eead-40dd-9b28-0bdff8f6bf11
  modified: 2026-07-21T17:20:45.076Z
---

Second half of the top-of-funnel content gap identified alongside the sell-your-building page (see [[project_sell_your_building_page_shelved_2026-07-20]]) — the site has zero blog/insights/resources content, ceding "sell my industrial building [metro]" search intent to national cash-buyer aggregators and institutional peers.

**Kicked off 2026-07-21**: an opus background agent is scoping 3-4 real, keyword-researched article topics and drafting genuinely publishable content (no fabricated stats — external claims must carry a verified, dated citation) in an isolated worktree at `C:/Users/Owner/wt-seller-resource-hub` (branch `feature/seller-resource-hub`, forked from post-PR#43 main `6d62546`).

**Architecture** (same pattern as the sell-your-building page): each article + a hub index page get their own indexable URL and a `sitemap.xml` entry, but none go into the primary site nav — discovery is via a link/button from `for-brokers.html` and/or `sell-your-building.html`.

**Guardrails given to the agent**: current property holdings are MD/OH/MO only (IN/WI/TN/KS are target/expansion markets, not holdings — the same factual error just fixed on sell-your-building.html); no confidential deal data; no personalized financial/tax advice, education only; stop after opening a PR — explicitly told not to merge or deploy, that needs Gabriel's separate in-turn confirmation.

**How to apply**: when this agent's PR lands, review scoped-vs-drafted article count (it was told quality over hitting 4 if time-constrained), verify the citation guardrail was actually followed (spot-check any external stat claims), and confirm the hidden-from-nav / sitemap-included pattern was applied correctly before merging — same review bar as PR #43.
