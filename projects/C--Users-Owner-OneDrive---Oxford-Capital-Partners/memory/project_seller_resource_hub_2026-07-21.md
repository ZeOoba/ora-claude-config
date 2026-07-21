---
name: project-seller-resource-hub
description: "Seller-intent resource hub (4 guides) — MERGED & LIVE 2026-07-21 via PR #45 (github.com/ZeOoba/Website/pull/45), merged by ZeOoba 17:59 UTC; production verified"
metadata: 
  node_type: memory
  type: project
  originSessionId: 662eac5c-eead-40dd-9b28-0bdff8f6bf11
  modified: 2026-07-21T18:04:48.903Z
---

Second half of the top-of-funnel content gap identified alongside the sell-your-building page (see [[project_sell_your_building_page_shelved_2026-07-20]]) — the site had zero blog/insights/resources content, ceding "sell my industrial building [metro]" search intent to national cash-buyer aggregators and institutional peers.

**CLOSED 2026-07-21**: shipped as 4 guides (1031 exchange, how industrial buildings are valued, sale-document checklist, selling without a broker) + a `/resources/` hub index, forked from post-PR#43 main `6d62546`. PR #45 opened and merged same-day by ZeOoba (17:59:39 UTC) — merged faster than the fourth-pass SEO audit (run same afternoon) could catch it; that audit's "zero resources content" Critical finding was already stale by the time it was read. Confirmed live in production via direct curl: `/resources/` and `/resources/1031-exchange-industrial-property-guide.html` both 200; `sitemap.xml` carries 6 resources-related entries.

**Architecture** (same pattern as the sell-your-building page): each article + the hub index has its own indexable URL and a `sitemap.xml` entry, but none are in the primary site nav — discovery is via a link/button from `for-brokers.html` and `sell-your-building.html`.

**Why not in nav**: consistent with the [[project_sell_your_building_page_shelved_2026-07-20]] pattern — these are targeted seller-conversion pages, not general-browsing content; Gabriel ratified 2026-07-21 that /sell-your-building itself also stays out of primary nav (same reasoning extends here).

**How to apply**: this closes the D+ Content Strategy dimension's binding-constraint item from the 07-21 fourth-pass audit. Before trusting any future audit's "content gap" finding, verify against `git log`/live production first — this file is proof an audit can be stale within hours on a fast-moving repo.
