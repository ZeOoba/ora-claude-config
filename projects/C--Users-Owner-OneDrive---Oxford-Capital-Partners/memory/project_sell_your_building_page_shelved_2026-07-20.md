---
name: project-sell-your-building-page-shelved
description: "Owner lead-gen page (sell-your-building.html) — shelved 2026-07-20, RESTORED + MERGED + LIVE via PR #43; nav-hidden placement RATIFIED by Gabriel 2026-07-21"
metadata: 
  node_type: memory
  type: project
  originSessionId: da248f6b-1229-46b7-8ba2-049922193bcc
  modified: 2026-07-21T18:05:25.149Z
---

**Nav placement RATIFIED 2026-07-21** (in response to the fourth-pass SEO audit flagging it as a "now-questionable orphan"): Gabriel confirmed it stays out of primary nav, for-brokers.html CTA remains the sole on-site discovery path. Reasoning: it's a targeted seller-conversion landing page for the owner-outreach motion, not general-browsing content — surfacing it in primary nav would put a seller CTA in front of the tenant/broker audience the main nav serves. This decision also extends to [[project_seller_resource_hub_2026-07-21]]'s hub/guides, same rationale.

**STATUS 2026-07-21: MERGED AND LIVE.** PR [#43](https://github.com/ZeOoba/Website/pull/43) (`feature/sell-your-building-hidden-page`, website-canonical) merged (squash, `6d62546`) to `main` 2026-07-21T17:17:18Z on Gabriel's explicit in-turn confirmation — deployed to oxfordra.net. `/sell-your-building` is live, hidden from primary nav, reachable via the for-brokers.html CTA. Branch and worktree cleaned up post-merge.

**What changed vs the original 2026-07-18 build:** only two files from the old 22-file patch were still relevant (`sell-your-building.html`, `netlify/functions/owner-lead-notify.js`) — main had moved on since 2026-07-18 and superseded the rest (llms.txt now exists via a later PR, FAQ schema landed separately, nav/sitemap/edge-function wiring were re-done from scratch against current `main` rather than reapplied). **New information architecture, decided this session:** the page keeps its own indexable `/sell-your-building` URL and a `sitemap.xml` entry (preserves the SEO-capture rationale), but is deliberately **not** in the primary site nav on any page — discoverable only via a new "Own a Building?" CTA section added to `for-brokers.html`. This pattern (indexable own-URL page/article, hidden from nav, surfaced via a button) is the template Gabriel wants applied to the seller-intent resource hub too (see `open-items-tracker.md`).

**Both previously-open issues resolved in PR #43:**
1. Indiana factual error fixed — "continues to hold... in Maryland, Ohio, Missouri, and Indiana" corrected to Maryland/Ohio/Missouri only (Indiana is acquire-target, not current-holding). Other Indiana mentions on the page (buy-box market list, schema `areaServed`, FAQ) correctly describe acquisition markets and were left as-is.
2. Dual-notify routing confirmed by Gabriel 2026-07-21 (`ggoldberg@` + `egoldberg@` on every owner-lead form submission, treated as transactional not scheduled-automation) — implemented as originally built, no change needed.
3. (New, not in original review) Added the missing `tests/functions/owner-lead-notify.test.js`, modeled on sibling `tenant-application-processor.test.js`. `node --test` 5/5 pass; `node scripts/build-dist.mjs` clean.

**Original patch** (`Claude_Workspace/01_Workspace/outputs/2026-07-20_staged-skills/2026-07-18_sell-your-building-page_full-patch.patch`) stays archived for reference but is now superseded by PR #43's branch — don't reapply it going forward, PR #43 is the current source of truth.

**Next step:** Gabriel review of the for-brokers.html CTA placement/copy and the full sell-your-building page, then merge decision. Merging this PR deploys to production per [[reference_oxfordra_deploy_canon]] — needs Invariant 2's per-deploy confirmation at that point, separate from this restoration work.
