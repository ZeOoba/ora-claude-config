#!/usr/bin/env node
/**
 * site-live-check.mjs — post-merge live verification for oxfordra.net (or a Netlify deploy preview).
 *
 * Merging to main on website-canonical deploys production, and a green CI does not prove the
 * LIVE site: redirects, headers, the sitemap and client-side behaviour only exist on Netlify.
 * This runs the checks that were done by hand after PR #127 / #130, in one command.
 *
 *   node ~/.claude/maintenance/site-live-check.mjs [--origin https://oxfordra.net]
 *        [--expect-redirect /properties=/portfolio ...] [--map /portfolio?view=map] [--asset portfolio.js?v=6]
 *
 *   --origin           site to check (default https://oxfordra.net; a deploy-preview URL works too)
 *   --expect-redirect  FROM=TO, repeatable: FROM must 301/308 to TO
 *   --asset            repeatable: path that must return 200 (immutable assets: also checks cache-control)
 *   --map              path of a Leaflet map page: loaded at 1x1 then grown, must frame (zoom >= 5) with
 *                      no CSP violations (needs Playwright from the website-canonical node_modules)
 *
 * Checks (every sitemap URL, not a sample):
 *   1  sitemap.xml parses; every <loc> returns 200 and has a self-referencing canonical, no noindex
 *   2  <loc>.html 301s to the clean URL (forced redirects) for every non-root sitemap URL
 *   3  security headers (CSP, X-Frame-Options, HSTS, nosniff) on the home page and 3 sitemap URLs
 *   4  each --expect-redirect, each --asset, and an unknown path returns 404
 * Exit 0 = all pass; 1 = any failure. Read-only: GET/HEAD requests only (plus one headless browser for --map).
 */
import { createRequire } from 'node:module';

const args = process.argv.slice(2);
const opt = (name) => { const out = []; args.forEach((a, i) => { if (a === name && args[i + 1]) out.push(args[i + 1]); }); return out; };
const origin = (opt('--origin')[0] || 'https://oxfordra.net').replace(/\/$/, '');
// Git Bash on Windows rewrites an argument that starts with "/" into "C:/Program Files/Git/...".
// Undo that, and accept paths with or without the leading slash (also: MSYS_NO_PATHCONV=1).
const norm = (p) => '/' + String(p).replace(/^[A-Za-z]:[\\/]Program Files[\\/]Git/i, '').replace(/^\/+/, '');
const redirects = opt('--expect-redirect').map((s) => s.replace(/^[A-Za-z]:[\\/]Program Files[\\/]Git/i, '').split('=').map(norm));
const assets = opt('--asset').map(norm);
const mapPath = opt('--map').map(norm)[0];

const results = [];
const check = (name, ok, detail = '') => { results.push({ name, ok, detail }); };
const get = async (target, init) => {
  const url = target.startsWith('http') ? target : origin + target;
  try { return await fetch(url, { redirect: 'manual', ...init }); } catch (e) { throw new Error(`GET ${url} failed: ${e.cause?.code || e.message}`); }
};

const sitemapRes = await get('/sitemap.xml');
const sitemap = await sitemapRes.text();
const locs = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
check('sitemap.xml loads and lists URLs', sitemapRes.status === 200 && locs.length > 0, `${sitemapRes.status}, ${locs.length} urls`);
const path = (u) => new URL(u).pathname;
// A preview's sitemap still names the production origin; check the same paths on the chosen origin.
const paths = locs.map(path);

// 1 + 2: every URL, concurrently in small batches.
async function pool(items, size, fn) { const out = []; for (let i = 0; i < items.length; i += size) out.push(...await Promise.all(items.slice(i, i + size).map(fn))); return out; }
const pageRows = await pool(paths, 6, async (p) => {
  const res = await get(p);
  const html = res.status === 200 ? await res.text() : '';
  const canonical = (html.match(/<link[^>]*rel="canonical"[^>]*>/i) || [''])[0].match(/href="([^"]+)"/i)?.[1];
  const robots = (html.match(/<meta[^>]*name="robots"[^>]*>/i) || [''])[0];
  const x = (res.headers.get('x-robots-tag') || '') + robots;
  let htmlRedirect = 'n/a';
  if (p !== '/' && !p.endsWith('/')) { // directory index pages (/markets/) have no .html twin
    const r2 = await get(p.replace(/\/$/, '') + '.html');
    const loc = r2.headers.get('location') || '';
    htmlRedirect = (r2.status === 301 || r2.status === 308) && path(loc.startsWith('http') ? loc : origin + loc).replace(/\/$/, '') === p.replace(/\/$/, '') ? 'ok' : `${r2.status} ${loc}`;
  }
  return { p, status: res.status, canonical, noindex: /noindex/i.test(x) && !origin.includes('deploy-preview'), htmlRedirect };
});
const bad200 = pageRows.filter((r) => r.status !== 200);
check(`every sitemap URL returns 200 (${paths.length})`, bad200.length === 0, bad200.map((r) => `${r.p}=${r.status}`).join(', '));
const badCanon = pageRows.filter((r) => r.status === 200 && (!r.canonical || path(r.canonical).replace(/\/$/, '') !== r.p.replace(/\/$/, '')));
check('every page has a self-referencing canonical', badCanon.length === 0, badCanon.map((r) => `${r.p} -> ${r.canonical}`).join(', '));
const noidx = pageRows.filter((r) => r.noindex);
check('no sitemap page is noindex', noidx.length === 0, noidx.map((r) => r.p).join(', '));
const badHtml = pageRows.filter((r) => r.htmlRedirect !== 'ok' && r.htmlRedirect !== 'n/a');
check('every <url>.html forced-301s to the clean URL', badHtml.length === 0, badHtml.map((r) => `${r.p}.html: ${r.htmlRedirect}`).join(', '));

// 3: security headers
const REQUIRED = ['content-security-policy', 'x-frame-options', 'strict-transport-security', 'x-content-type-options'];
for (const p of ['/', ...paths.filter((x) => x !== '/').slice(0, 3)]) {
  const res = await get(p);
  const missing = REQUIRED.filter((h) => !res.headers.get(h));
  check(`security headers on ${p}`, missing.length === 0, missing.join(', '));
}

// 4: explicit redirects, assets, 404
for (const [from, to] of redirects) {
  const res = await get(from);
  const loc = res.headers.get('location') || '';
  check(`${from} redirects to ${to}`, (res.status === 301 || res.status === 308) && path(loc.startsWith('http') ? loc : origin + loc) === to, `${res.status} ${loc}`);
}
for (const a of assets) {
  const res = await get(a);
  const cc = res.headers.get('cache-control') || '';
  check(`asset ${a} returns 200`, res.status === 200, `${res.status} ${cc}`);
}
const nf = await get('/definitely-not-a-page-' + Date.now());
check('an unknown path returns 404', nf.status === 404, String(nf.status));

// --map: framing when the container has no size at first fit, then gets one (the PR #130 bug).
if (mapPath) {
  try {
    const require = createRequire('C:/Users/Owner/website-canonical/package.json');
    const { chromium } = require('playwright');
    const browser = await chromium.launch();
    const ctx = await browser.newContext({ viewport: { width: 1, height: 1 } });
    const page = await ctx.newPage();
    const viol = [];
    page.on('console', (m) => { if (/Content Security Policy/i.test(m.text())) viol.push(m.text().slice(0, 100)); });
    await page.goto(origin + mapPath, { waitUntil: 'load' });
    await page.waitForFunction(() => window.L && document.querySelectorAll('.leaflet-marker-icon').length > 0, null, { timeout: 20000 });
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.waitForTimeout(2500);
    const info = await page.evaluate(() => ({
      zoom: Math.max(...[...document.querySelectorAll('img.leaflet-tile')].map((i) => Number((i.src.match(/\/(\d+)\/\d+\/\d+\.png/) || [])[1])).filter((n) => !Number.isNaN(n))),
      spread: new Set([...document.querySelectorAll('.leaflet-marker-icon')].map((p) => { const b = p.getBoundingClientRect(); return Math.round(b.x) + ',' + Math.round(b.y); })).size,
      pins: document.querySelectorAll('.leaflet-marker-icon').length,
    }));
    await browser.close();
    check(`map ${mapPath} frames the data after a late resize (zoom >= 5, pins spread)`, info.zoom >= 5 && info.spread >= 5, JSON.stringify(info));
    check('map loads with no CSP violations', viol.length === 0, viol.join(' | '));
  } catch (e) {
    check(`map ${mapPath} browser check ran`, false, e.message.split('\n')[0]);
  }
}

const w = Math.max(...results.map((r) => r.name.length));
for (const r of results) console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.name.padEnd(w)}  ${r.ok ? '' : r.detail}`);
const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} passed against ${origin}`);
process.exit(failed ? 1 : 0);
