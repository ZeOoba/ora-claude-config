---
name: ora-loopnet-listings-sync
description: Weekly (Mon 2:30 PM ET) sync of oxfordra.net/available-space to ORA's public LoopNet listings — paced double read of the public company + listing pages in the Browser pane, scripts/sync-listings.mjs diff/guards, opens a PR with Netlify preview on change (NEVER merges or deploys — invariant 2); emails ggoldberg only on alert / needs-input / new PR. v1.1 2026-10-02 (also regenerates portfolio availability badges). [MODEL: claude-sonnet-5-5 | set 2026-10-06]
---

# ora-loopnet-listings-sync — v1.1 (2026-10-02)

Keep https://oxfordra.net/available-space in step with Oxford Realty Advisors' PUBLIC LoopNet listings. You produce a pull request for Gabriel to review. You NEVER merge, NEVER deploy, NEVER touch Netlify (CLAUDE.md hard invariant 2). Each run starts with no memory — everything you need is here or in the repo.

Background + Gabriel's ratified decisions: memory file `C:\Users\Owner\.claude\projects\C--Users-Owner-website-canonical\memory\project_loopnet_available_space_sync.md`. Logic lives in the repo, not here: `scripts/sync-listings.mjs` (diff, guards, standing exclusions: broker Scott Manhoff, city Potomac, every for-sale listing; `pinned` listings; rate-type carry-forward) and `scripts/build-listings.mjs` (regenerates listings.js, static cards, JSON-LD, cache-buster, and the "N suites available" badges on the portfolio cards in portfolio.html). Do not re-implement or second-guess either; if they look wrong, say so in the email and stop.

## Guards (check first, exit quietly if any trips)
1. If an open PR already exists whose head branch starts with `sync/loopnet-` (`gh pr list --repo ZeOoba/Website --state open --json headRefName,url`), do NOT open another. Email a one-line reminder with that PR's URL and stop.
2. If the Browser pane tools (`mcp__Claude_Browser__*`) are not available in this session, email "LoopNet sync could not run: no browser tools in this session" and stop. Never substitute curl/WebFetch — LoopNet returns 403 to non-browser clients, and working around a block is prohibited.

## Step 1 — Read LoopNet (public pages only, paced, twice)
Company page: `https://www.loopnet.com/company/oxford-realty-advisors/dkrft8kl/`
- Open it in the Browser pane. Collect every distinct `a[href*="/Listing/"]` URL inside `<main>` (strip query strings). The trailing number in each URL is the `loopnetId`.
- For EACH listing URL, navigate to it, wait ~3 s, and extract with `javascript_tool`:
  - `title` = document.title. If it contains "for Sale" → record `forSale: true`, no units needed.
  - address / city / state from the title (e.g. "384-398 Morrison Rd, Columbus, OH 43213 - …").
  - `brokers`: search `document.documentElement.innerHTML` for person names in the contact section; at minimum record "Scott Manhoff" if `/manhoff/i` matches anywhere in the HTML.
  - units: every `available-spaces-content[data-fields]` element → JSON.parse the attribute → map FeatureName→Value. `Space` ("1st Floor - 386", "1st Floor, Ste 107-108") → suite = the part after the last " - " or after "Ste ". `Size` ("1,800 SF" or "1,200-2,400 SF") → sf / sfMax (integers). `Rental Rate` → the first "$N.NN /SF/YR" number → rate. `Space Use` → use. LoopNet does not state lease type — omit `rateType`.
  - Sanity: the number of units you extracted must equal N in the page text "All Available Space(s)(N)". If not, treat the read as failed (Step 3 alert) — the visible list hides spaces, the data-fields attribute does not.
- PACING IS MANDATORY: wait at least 20 seconds between page loads. On 2026-09-18 about 25 loads in a few minutes triggered LoopNet's "Access Denied". If ANY page shows "Access Denied" or a block/captcha page: STOP reading immediately, do not retry, do not try another route, go to Step 3 (alert).
- That is read 1. Wait at least 5 minutes, then repeat the whole pass as read 2 (same pacing).
- Write `{ "reads": [read1, read2] }` to a file in your scratchpad directory, each read an array of `{ loopnetId, address, city, state, brokers?, forSale?, units: [{ suite, sf, sfMax?, rate, use? }] }`. Record exactly what the pages say — never fill a gap from memory or from the other read.

## Step 2 — Plan and apply in an isolated worktree
```
cd C:/Users/Owner/website-canonical
git fetch origin
git worktree add ../website-canonical-wt-loopnet-YYYYMMDD -b sync/loopnet-YYYY-MM-DD origin/main
cd ../website-canonical-wt-loopnet-YYYYMMDD
node scripts/sync-listings.mjs <scraped.json> --write
```
`YYYYMMDD`/`YYYY-MM-DD` above and in the commit message below = the run date computed once at run start with `date '+%A %Y-%m-%d'` (date part only; dashes dropped for the worktree folder), reused verbatim. Never work in the main checkout. Exit codes: 0 = no change · 10 = applied · 20 = alert · 1 = error. The script prints a JSON report (`changes`, `needsInput`, `warnings`, `reasons`).

- Exit 0 and `needsInput` empty → remove the worktree (`git worktree remove`), delete the branch, finish silently. No email.
- Exit 10 → run `node scripts/build-listings.mjs --check` and `npm run test:unit` (node_modules: if missing, `cmd //c "mklink /J node_modules ..\website-canonical\node_modules"`). If either fails → Step 3 alert, do not push. If both pass: `git checkout -- netlify/edge-functions/knowledge-base.json` if the build touched it, stage ONLY `data/listings.json listings.js available-space.html portfolio.html sitemap.xml` (build-listings.mjs stamps the /available-space `<lastmod>` in sitemap.xml on every write run, and the /portfolio `<lastmod>` when portfolio.html's badges change; leaving portfolio.html or the sitemap unstaged ships stale badges/lastmod, dirties the worktree, and makes the PR's `Build & verify` fail on a portfolio.html drift), commit `data(listings): LoopNet sync YYYY-MM-DD` with the change list in the body, `git push -u origin <branch>`, then `gh pr create --base main` with a before/after table of `changes`, the `needsInput` and `warnings` lists, and the line "Rate types are carried forward from the site — LoopNet never states lease type; check any large rate move." Then Step 3 (PR email).
- Exit 20 or 1 → Step 3 alert. Leave nothing pushed; remove the worktree and branch.

## Step 3 — Email (only when there is something to say)
Send via the SOLE send path: `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`, TO `ggoldberg@oxfordra.net` ONLY — no cc, no other recipient. On exit 2 or 4 retry once, then state the send failure loudly in your final output; do not halt. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the run summary and in the failure record named above, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.
- PR opened: subject `LoopNet sync — PR ready (N changes)`; body = PR URL, change list, needsInput, warnings, and "Nothing is live until you merge."
- needsInput with no changes: subject `LoopNet sync — input needed`; body = the needsInput lines (e.g. a new LoopNet property needs photo, lat/lng, market, category, description, rate type before it can be added by hand to data/listings.json).
- Alert: subject `LoopNet sync — ALERT, no changes made`; body = the `reasons`, which page failed, and whether LoopNet blocked the read.

## Rules
- Never fabricate a listing, suite, size, rate, or rate type. A gap is a QUESTION FOR GABRIEL in the email, not a guess.
- Never add a new property automatically; never overwrite site-owned fields (name, city, address, photo, lat/lng, description) — the script enforces this, do not hand-edit around it.
- Never edit `_headers`, `_redirects`, `netlify.toml`, `netlify/**`, or anything outside the data/generated files named in Step 2 (`data/listings.json`, `listings.js`, `available-space.html`, `portfolio.html`, `sitemap.xml`). `portfolio.html` is only ever regenerated by `build-listings.mjs`; never hand-edit it, and never touch `data/portfolio.json`. If `build-listings.mjs` fails with "no data/portfolio.json asset claims", a listing exists with no portfolio card: Step 3 alert, do not push.
- Never merge the PR, never run `netlify deploy`, never enable auto-merge.
- If a permission prompt blocks a Browser, git, or gh call and nobody is attending, stop and say exactly which call blocked in your final output — do not look for another route.
- Final output: one paragraph — what LoopNet showed, the script's exit code, what was opened/sent, anything that blocked.