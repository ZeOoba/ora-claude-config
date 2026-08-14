---
name: project-oxfordra-desktop-perf-98-not-100-2026-08-13
description: oxfordra.net desktop PageSpeed Performance is 98/100, not 100 — diagnosed as scoring-curve residue, not a fixable defect
metadata:
  type: project
  originSessionId: 9ee648fb-0064-481f-91e1-a91cf2f7ed7b
  modified: 2026-08-13T20:08:41.584Z
---

Desktop PSI: Performance 98, all other categories 100. Lab metrics are all green — FCP 0.3s, LCP 0.4s, TBT 10ms, CLS 0.027, SI 1.5s.

**Root cause: Lighthouse's log-normal scoring curve, not a code defect.** No lab metric is literally zero (CLS 0.027, TBT 10ms), and the weighted geometric mean of near-perfect-but-nonzero metrics rounds to 98, not 100. A literal 100/100 desktop score is not realistically achievable on a page with any real images/JS — this is expected, not a regression.

**Diagnostics shown are non-scoring advisories at this level, not levers:**
- GTM/gtag "unused JS" (86.9 KiB, ~20ms est. savings) — already litigated in [[project-oxfordra-lcp-render-delay-2026-08-12]]; Gabriel ruled 2026-08-13 to keep the 3s gtag fallback as-is. 20ms is far below what would move the score even if removed.
- "Avoid non-composited animations" (21 elements) — traced to `website-canonical/styles.css`: several `transition:max-height`, `transition:height`, `transition:box-shadow`, `transition:border-color`, `transition:color`, plus a few `transition:all var(...)` shorthand rules. Chrome's audit flags `transition:all` even when only transform/opacity actually change, because it can't statically prove otherwise — likely explains most of the 21. Diagnostic-only; doesn't carry direct Performance-category weight, and TBT is already 10ms so little/no headroom here.
- "Avoid long main-thread tasks" (1 task) — singular, consistent with TBT 10ms; not score-moving.

**Unresolved:** the LCP-breakdown Insight panel showed "Est savings 1,020 ms" with resource load delay ~780ms / duration ~2,400ms for the hero image — inconsistent with the lab LCP of 0.4s. Likely CrUX **field data** (real users, real networks) shown alongside the lab trace, not the lab number itself — same lab-vs-field gap already documented for mobile in [[project-oxfordra-lcp-render-delay-2026-08-12]]. Not confirmed — the screenshot didn't show a field-vs-lab toggle. If re-investigating, check whether the report has a "Discover what your real users are experiencing" field section separate from the lab gauge.

Also unresolved: which element drives the 0.027 CLS — screenshot's "Layout shift culprits" section was collapsed. Would need to expand it in a live report to name the element.

**Recommendation:** no code change justified to chase 98→100 on desktop; diminishing returns confirmed. If ever revisited, start with the CLS culprit (only nonzero-but-scored lever) — not the animation/JS diagnostics, which are cosmetic-only at these levels.

**PSI channel is currently unusable for a live re-check (2026-08-13):** pagespeed.web.dev UI hangs at "Running analysis / data loading" indefinitely (confirmed via network trace — the `batchexecute` kickoff request fires and is accepted, then zero follow-up polling); the anonymous `googleapis.com/pagespeedonline/v5` API returns 429 (daily quota exhausted). Matches the gotcha already logged for the mobile investigation — don't keep retrying either channel same-day; wait or use a local Lighthouse harness.

**Best Practices score is BIMODAL (100 vs 79), not a regression — root-caused 2026-08-13.** Same page, two different PSI runs same day: one scored Best Practices 100, another scored 79 flagging "Uses third-party cookies" + "Issues logged in DevTools Issues panel." Root cause: the ONLY external script on the page is `googletagmanager.com/gtag/js` (GA4), deliberately deferred to fire on first interaction/pagehide/**3s fallback** (ruling in [[project-oxfordra-lcp-render-delay-2026-08-12]] — keep as-is). Whether a given Lighthouse trace window happens to run past the 3s mark determines whether it catches gtag setting its cookies. Fast trace finishing <3s → no cookies flagged → 100. Trace extending past 3s → cookies caught → 79. Chat widget (`assets/chat.js`) ruled out — self-hosted, no external calls. Not actionable/not a defect; do not re-investigate as a mystery regression.

**Regional PSI variance also observed:** "Insights for [region]" panel showed different Performance scores by test location (e.g. 96 vs. 99 for US East), with "Document request latency" / "Reduce initial server response time" flagged red in the slower region even at a 99 aggregate score. This is Netlify-edge-to-PSI-test-node latency, not a code issue — not actionable without a hosting/CDN change.
