---
name: oxfordra.net — 10-item improvement punchlist
description: Prioritized code-quality, perf, a11y, SEO punchlist for oxfordra.net home page + site-wide; ready for execution in a new session
type: project
originSessionId: 3affbb4e-638a-4c40-9100-55a820ab8f1f
---
# oxfordra.net — 10-Item Improvement Punchlist (2026-04-20)

## Context

Static HTML/CSS/vanilla-JS site. Source of truth: `C:\Users\Owner\oxford-site-v2\deploy\`.
Netlify site: `snazzy-frangipane-de3841.netlify.app` (custom domain: oxfordra.net).
Most recent draft preview baseline: https://69e65e3f2e96b93a32779952--snazzy-frangipane-de3841.netlify.app

## 2026-04-20 — Punchlist executed, then hotfixed

All 10 items executed and deployed as draft `69e663b65d3df706b123c7cc`. User reported broken layout. Root cause: item #6 (tightened CSP, removed `'unsafe-inline'` from script-src) broke the `<link rel="preload" onload="this.rel='stylesheet'">` pattern — inline `onload` requires `'unsafe-inline'` or `'unsafe-hashes'`. styles.css never loaded; only inline `<style>` block applied. Fix: replaced preload+onload with plain `<link rel="stylesheet">` across all HTML files, bumped `?v=12`. Final draft: `69e66d3869b14c0a7657332f--snazzy-frangipane-de3841.netlify.app`. Verified: `.featured-card` navy bg applied, 3-col metric grid, footer styled.

**Lesson saved to** [feedback_csp_preload_onload.md](feedback_csp_preload_onload.md).

Brand: EB Garamond display, DM Sans UI, IBM Plex Mono numerics. Oxford Navy #1B2A4A, Gold #C9A96E, Parchment #F5F0E8. Target PageSpeed 100/100 mobile+desktop.

**User directive:** Produce a new Netlify *draft* preview after all 10 fixes. **Do NOT run `netlify deploy --prod`. Do NOT touch the live site.** Draft only, via `cd C:/Users/Owner/oxford-site-v2/deploy && npx netlify-cli deploy --dir=. --message="..."`.

## Recently-completed baseline (already live on draft)

Home page "Featured Acquisitions" section in [index.html:347–440]:
- Sepich card: 6 metric tiles (2×3 grid) — $42 Basis/SF, 2.0× NOI, 100% Occupancy, ~2.6× Equity Multiple, $12M Value, 38 Days LOI
- 3540 card: rear-view `.ba-slider` (front slider dropped) + 6 tiles — ~12% Going-In Cap, ~2× Value Created, 10-Yr Global Tenant, $1.3M Acquisition, ~$1.0M Renovation, 36,000 SF
- Both cards use flex-column + `margin-top:auto` on metric grids to align tiles to bottom → equal card heights
- Reference implementation of `.ba-slider` markup lives in [track-record.html:172-187]; CSS/JS in `styles.css`/`script.js` (both minified, single-line)

## The 10 Updates (execute in this order)

### P0 — Ship blockers

**1. Add HSTS header**
- File: `C:\Users\Owner\oxford-site-v2\deploy\_headers`
- In the `/*` block, add: `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`

**2. Optimize OG image**
- File: `C:\Users\Owner\oxford-site-v2\deploy\images\og-image.png` (184 KB)
- Convert to WebP (~50 KB target). Update `<meta property="og:image">` in every HTML file if path changes. Social scrapers prefer PNG/JPG for compatibility — safer move: compress PNG to <100 KB *and* add a WebP variant alongside. Verify dimensions are exactly 1200×630.

**3. Extract inline styles from Featured Acquisitions**
- File: `C:\Users\Owner\oxford-site-v2\deploy\index.html` lines ~356–410
- Today uses 50+ inline `style=""` attributes on card containers, metric tiles, and grid wrappers.
- Create CSS classes in `styles.css`: `.featured-card` (border-radius, overflow, background, border, flex-column), `.featured-card__body` (padding:28px, flex column, flex:1), `.metric-tile-grid` (display:grid, grid-template-columns:repeat(3,1fr), gap:20px 16px, margin-top:auto), `.metric-tile__value` (font-mono, 22px, gold, line-height:1.1), `.metric-tile__label` (11px uppercase, letter-spacing:.1em, rgba white .55, margin-top:6px).
- Replace inline styles with these classes in index.html. Verify visual output matches current draft.

### P1 — High impact

**4. `.ba-slider` keyboard a11y gaps**
- File: `script.js` — find the `.ba-slider` keydown handler.
- Currently handles ←/→/↑/↓ only. Add: **Home** key → snap handle to 0% (full "before"), **End** key → snap to 100% (full "after"), **PageUp/PageDown** → ±10% jumps.
- Add `aria-valuetext` attribute to `.ba-slider__handle` that updates with the handle position (e.g., `"50% — before and after equally visible"`).
- Verify `:focus-visible` outline on the handle circle renders a visible gold ring in Chrome, Firefox, and Safari. If `styles.css` only has `:focus` (not `:focus-visible`), add `:focus-visible` rule.
- Apply to *all* `.ba-slider` instances (home page rear slider + track-record.html front+rear).

**5. AVIF rollout across all large images**
- Currently: only 3 AVIFs exist (hero + 2 headshots per prior review). 40+ images are still JPG+WebP only.
- For every image >50 KB in `C:\Users\Owner\oxford-site-v2\deploy\images\`, generate an AVIF variant. Use `ffmpeg` (`ffmpeg -i input.jpg -c:v libaom-av1 -crf 30 -still-picture 1 output.avif`) or `sharp-cli` if available.
- In every HTML file, for every `<picture>` element, add `<source type="image/avif" srcset="/images/foo.avif">` as the FIRST source (before the WebP source).
- Priority files: track-record.html, portfolio.html, index.html, about.html.

**6. Tighten CSP**
- File: `_headers` — currently `script-src 'self' 'unsafe-inline'` and likely similar for styles.
- Compute SHA-256 hashes of the inline `<style>` block in index.html (the critical-CSS block ~lines 58–75) and any inline `<script>` blocks.
- Replace `'unsafe-inline'` with `'sha256-<hash>'` entries. If too many inline styles to hash cleanly, at minimum remove `'unsafe-inline'` from `script-src` (Step 3 already removes most inline JS).
- Verify no CSP violations in browser console on the draft preview before accepting.

**7. Preload IBM Plex Mono**
- IBM Plex Mono is used for every metric tile numeric. Currently loaded via CSS only → FOUT risk on the most visible brand element.
- Find the woff2 file path for IBM Plex Mono in `/fonts/` (or wherever `styles.css` references it).
- In every HTML file's `<head>`, add: `<link rel="preload" as="font" href="/fonts/ibm-plex-mono-<variant>.woff2" type="font/woff2" crossorigin>` BEFORE the main stylesheet link.
- Also add a `Link` preload header in `_headers` under the `/` and `/index.html` blocks alongside the existing EB Garamond / DM Sans preloads.

### P2 — Polish

**8. Testimonial carousel autoplay — pause when offscreen**
- File: `script.js` — find the testimonial carousel `setInterval` (~8000ms autoplay).
- Wrap the interval in an IntersectionObserver: start interval on `isIntersecting:true`, clear on `isIntersecting:false`.
- Also pause on `document.visibilityState === 'hidden'` via `visibilitychange` listener.

**9. Stat counter IntersectionObserver — widen rootMargin**
- File: `script.js` — find `.hero__stat-value` (or similar) counter animation.
- Currently `rootMargin: '-48px'` may fire before fully in view on slow connections.
- Change to `rootMargin: '-96px'` OR simpler: `threshold: 0.5`.

**10. Deep-link anchor on Featured Acquisitions**
- File: `index.html` — `<h2>Featured Acquisitions</h2>` in the Featured Results section.
- Add `id="featured-acquisitions"` to the h2 (or its parent section if section-level anchor preferred).
- Test `/index.html#featured-acquisitions` scrolls to the section.

## Verification checklist before creating the draft preview

- [ ] `.ba-slider` drag, touch, mouse, keyboard (←/→/↑/↓/Home/End/PgUp/PgDn) all work on home and track-record pages
- [ ] Card heights on home "Featured Acquisitions" match visually on desktop and tablet
- [ ] All 6 metric tiles render per card on mobile (stacks cleanly at ≤640px)
- [ ] No CSP violations in DevTools console
- [ ] No 404s in DevTools network tab (esp. new AVIF files and preloaded font)
- [ ] Lighthouse Performance + Accessibility both ≥95 on the draft URL

## Deploy command

```
cd "C:/Users/Owner/oxford-site-v2/deploy" && npx netlify-cli deploy --dir=. --message="Preview v3: 10-item improvement punchlist (HSTS, OG, CSS extract, a11y, AVIF, CSP, font preload, carousel, deep link)"
```

**Do NOT add `--prod` flag. Draft only.**
