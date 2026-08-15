---
name: project-oxfordra-lcp-render-delay-2026-08-12
description: oxfordra.net LCP render-delay investigation — forced-reflow defect FIXED and live; the expensive first Layout is the open residual
metadata: 
  node_type: memory
  type: project
  originSessionId: de0e4e1d-495b-4165-8dd0-be775c34ba37
  modified: 2026-08-13T04:06:35.574Z
---

PSI mobile (96/100, 2026-08-12) flagged a 1,890 ms LCP **render delay** (75% of LCP) plus a forced-reflow insight. Trace analysis: the hero AVIF (17 KB, preloaded, `fetchpriority=high`) downloaded early but waited on **two full-document synchronous layouts** scheduled into the pre-paint window.

**FIXED and live on prod** ([PR #66](https://github.com/ZeOoba/Website/pull/66), merged `8b9aedc`, deployed 2026-08-13, `script.js?v=12`). Both geometry reads deferred past `load` (idle, 2 s):
1. `script.js` `requestAnimationFrame(a)` ×2 at DOMContentLoaded reading `window.pageYOffset` (nav scrolled-state + scrollspy) — this was PSI's `script.js:1:9404` attribution.
2. `index.html` scroll-progress `measure()` reading `scrollHeight`/`clientHeight` in a 1 s-timeout `requestIdleCallback`.

Verified: forced-reflow attribution present 3/3 prod runs before, **NONE 3/3 after**. Metric gain is small — local n=5 gave LCP 1,833→1,731 ms, within run-to-run spread; on the live deployment at n=3 it was indistinguishable from noise.

**OPEN RESIDUAL — the real bottleneck.** A *single* initial full-document `Layout` costs ~1,000 ms at 8× CPU throttle on the deployed page for only **390 DOM elements / 594 layout objects** (~40–125 ms real CPU). It gates FCP, and LCP follows it. Not root-caused: a leave-one-out `<section>` bisect was inconclusive because measurement noise (±100 ms) exceeded the signal on a contended machine. **Re-run the bisect on a quiet machine** — this is where the remaining mobile headroom is, not in the JS.

**Tested and REJECTED (do not re-propose):**
- Render-blocking `styles.css` instead of the `media=print`→`all` swap: FCP +900 ms, LCP +1,000 ms. The async-CSS pattern is earning its keep.
- Deferring the 4 s announcement-bar rotator to fix Speed Index: no effect (SI 1,885→1,943). The rotator is NOT the SI driver.

**GTM/GA4 67 KiB unused JS:** Gabriel ruled 2026-08-13 — **keep the 3 s fallback as-is**. gtag.js already loads on first interaction / pagehide / 3 s; dropping the timer would silently lose pageviews for non-interacting visitors (most broker bounces) to remove an unscored diagnostic.

**Measurement gotchas (cost real time here):**
- The PSI API without a key has a shared anonymous **daily** quota that is routinely already exhausted — `429 "Queries per day"`. Do not plan a before/after around it. The pagespeed.web.dev UI in the in-app browser pane also hung (query string dropped on navigate).
- Use a local Lighthouse harness instead: copy the site to scratchpad, serve it, and A/B **interleaved** with n≥5 medians. A localhost harness has no network latency, so it *overstates* main-thread fixes — the same patch measured −13% LCP locally and ~0 against the live deployment.
- This machine's contention swings Lighthouse scores 53→95 on identical content. Never compare runs taken at different times; interleave arms.

See also [[reference-oxfordra-lighthouse-csp-fix-2026-07-21]], [[project-oxfordra-seo-audit-2026-07]].
