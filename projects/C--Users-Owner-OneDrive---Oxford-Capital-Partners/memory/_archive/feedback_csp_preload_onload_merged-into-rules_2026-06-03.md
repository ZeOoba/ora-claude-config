---
name: CSP blocks inline onload handlers — don't use preload+onload stylesheet pattern
description: The `<link rel="preload" onload="this.rel='stylesheet'">` CSS loading trick silently breaks under our tightened CSP; use plain stylesheet link
type: feedback
originSessionId: 97803a40-54bf-4c24-ab8e-724766c8aa5a
---
Do NOT use the `<link rel="preload" as="style" href="..." onload="this.onload=null;this.rel='stylesheet'">` pattern on oxfordra.net. Use plain `<link rel="stylesheet" href="...">` instead.

**Why:** On 2026-04-20, executing the 10-item punchlist (item #6 tightened CSP to remove `'unsafe-inline'` from script-src and added SHA-256 hashes for inline `<script>` blocks). Inline event handlers (the `onload=` attribute) also require `'unsafe-inline'` or `'unsafe-hashes'` + matching hash — neither of which we have. Result: the preload never swapped to a stylesheet, styles.css never loaded, only the ~83-rule inline `<style>` critical-CSS block applied. Home page rendered with broken Featured Acquisitions cards (metric tiles as inline vertical text, no card background), unstyled ba-slider, and unstyled footer. User reported "It looks terrible." Fix: replaced preload+onload with plain stylesheet link across all pages (index, contact, about, track-record, tenant-resources, portfolio, tenant-application, for-brokers, 404, available-space, privacy, terms), bumped `?v=12`. Verified via chrome-devtools evaluate_script: `.featured-card` bg = rgb(20,31,51), `.metric-tile-grid` cols = "163.328px 163.328px 163.328px", footer bg = rgb(27,42,74).

**How to apply:** When tightening CSP on a static site, audit for `onload=` / `onerror=` / any `on*=` inline event handlers — they will silently fail. The FOUC savings from preload+swap aren't worth the fragility. If FOUC avoidance is critical, either (a) inline the full stylesheet, or (b) add `'unsafe-hashes' 'sha256-<hash-of-onload-value>'` to CSP, or (c) move the swap logic into an external hashed script.
