# oxfordra.net SEO follow-ups — implementation plan (2026-09-21)

> **For agentic workers:** execute task-by-task; each code task is TDD (test first, watched to fail), in a worktree off `origin/main`, PR only. **Invariant 2:** edits need Gabriel's in-turn go-ahead per PR, and no production deploy without a separate per-deploy confirmation. Merged ≠ live: verify the *served* asset after any confirmed deploy.

**Goal:** finish the 2026-09-21 Google + AI-platform SEO review: make the site and the web's copies of the firm's facts agree, give AI crawlers an explicit policy, and turn one-off audit work into a monthly probe.

**Done already (PR [#84](https://github.com/ZeOoba/Website/pull/84), ready for review, CI green):** finding 3 (one Organization entity, `@id`-linked Article/Service, WebSite node, founder/legalName/contactPoint/knowsAbout) and finding 4 (sitemap `lastmod` stamped by the LoopNet sync; sync-task SKILL.md now stages `sitemap.xml`). Finding 6 (privacy/terms canonical) was a **false positive** (attribute-order regex) — retracted, nothing to build.

> **SUPERSEDED IN PART (Gabriel, 2026-09-23, PR #85 session):** the markets decision below is reversed — the site keeps **"three core markets" (Maryland, Columbus OH, Kansas City MO)**, matching the hero stat, ~10 pages, `llms.txt`, `scripts/meta.md` and the chat KB. **Do NOT execute W1**, do **not** add test `M-1` (it would ban "three core markets" and revert PR #85), and W6's claim-string check must assert **"three core markets"**, not "two core markets". Also per 2026-09-23: no numeric portfolio LTV is public (site copy says "conservative leverage"). All other 2026-09-21 decisions stand.

**Decisions locked (Gabriel, 2026-09-21):** founder-only named-person markup · markets = ~~two core (Maryland, Columbus) + a Kansas City holding~~ **→ superseded 2026-09-23: three core markets** · AI crawlers = **explicit allow, all bots** · SEO probe = **monthly** · CWV = **local Lighthouse CLI** · Search Console/Bing = **neither / unsure → start with verification**.

## Sequencing and ownership

| # | Workstream | Owner | Blocked by | Deploy? |
|---|---|---|---|---|
| W0 | Merge #84, confirmed deploy, verify served JSON-LD | Gabriel confirms; Claude verifies | — | **yes (per-deploy confirm)** |
| W1 | Markets claim PR (two core + KC) | Claude | #84 merged (both touch index/about JSON-LD) | with W0 batch or later |
| W2 | robots.txt AI-crawler policy PR | Claude | none (independent; can ship with W1) | with W1 |
| W3 | Off-site entity copy pack + profile updates | Claude drafts; **Gabriel logs in and pastes** | W1 wording final | no |
| W4 | Search Console + Bing verify, sitemap submit, reindex, IndexNow | Gabriel (DNS TXT/login); Claude prepares | W0 deployed | no |
| W5 | Local Lighthouse baseline (mobile+desktop) | Claude | feasibility check (needs Chrome path) | no |
| W6 | Monthly SEO probe (script + scheduled task) | Claude | W1 merged (probe asserts the new claim) | no |
| W7 | `website-perfection` skill v1.2 + memory/event-log persist | Claude | W1–W6 lessons | no |

Critical path: **#84 → W0 → W1+W2 → (deploy) → W4/W3 → W6.** W5 and W7 run in parallel with anything.

## Pre-flight failure analysis (top failure modes, per CLAUDE.md L3 rule)
1. **Wrong target / partial claim rewrite** — "three core markets" appears in visible copy, JSON-LD, `llms.txt`, `scripts/meta.md` (feeds the chat bot) and pinned tests. Changing only some re-creates the contradiction. → W1 starts with an exhaustive grep and ends with a test that greps the whole tree.
2. **Stale-data loop** — fixing the site while LoopNet/Crunchbase/realty.com still say "600,000+ SF, Indianapolis" keeps AI answers wrong. → W3 is not optional; W0's deploy alone does not fix AI answers.
3. **Merge conflicts with the weekly LoopNet sync branch / other worktrees** — `available-space.html`, `listings.js`, `sitemap.xml`. → rebase on `origin/main` immediately before each PR; W1 must not touch listings files.
4. **Hook/gate fail-closed** — the site-write gate needs the per-session override token; empty replacement strings are blocked (use non-empty replacements). → recorded in the memory entry (W7).

## W1 — Markets claim: "two core markets + Kansas City holding" — **CANCELLED 2026-09-23 (Gabriel kept "three core markets"; see banner above). Do not execute.**

**Files (verify by grep first, do not trust this list):** `index.html`, `about.html`, `portfolio.html`, `markets/index.html`, `llms.txt`, `scripts/meta.md`, JSON-LD Organization `description` + `areaServed` (both nodes — E-1 forces them identical), `tests/site/seo.test.mjs` / `seo-entity.test.mjs`, `sitemap.xml` lastmod for changed pages, and `netlify/edge-functions/knowledge-base.json` (regenerate on LF/CI, not the CRLF working copy).

- [ ] **Step 1 — Inventory (read code, not memory):** `git grep -n -i -E "three core|3 core|core markets|Kansas City" origin/main -- '*.html' llms.txt scripts/meta.md`. Record every hit with its intended new wording. Confirm what About's "2024 Expanded into Kansas City market" timeline line should say (Gabriel review).
- [ ] **Step 2 — Failing test first:** new test `M-1`: no page/`llms.txt`/`meta.md` contains "three core markets" / "3 Core Markets"; Organization `description` matches the canonical sentence; the stat strip says two core markets. Watch it fail on current main.
- [ ] **Step 3 — Edit** with the wording below; keep facts (500,000+ SF, 140+ tenants, 26 buildings = 12 MD + 13 Columbus + 1 KC) untouched.
  - Canonical sentence (proposal, Gabriel approves in PR): *"Private industrial real estate investment firm specializing in value-add shallow-bay flex properties, with two core markets — Maryland and Columbus, OH — and a Kansas City, MO holding."*
  - Stat strip: "2 Core Markets" + KC note where the layout allows; do **not** invent a Kansas City market page.
- [ ] **Step 4 — Gate:** `npm run verify` (CI runs `csp-smoke`), site-qc-reviewer (read-only) + independent code review, local screenshot at 375/768/1024/1440 for the stat strip.
- [ ] **Step 5 — PR**, note that `dateModified`/Article dates are unchanged (no guide content changed) and lastmod bumped only for pages whose visible copy changed.

**Rollback:** revert the PR; `llms.txt` and `meta.md` revert with it. **Confidence:** high on mechanics, medium on wording (claim = Gabriel's call).

## W2 — robots.txt: explicit allow for AI crawlers

- [ ] Test `R-1`: `robots.txt` has an explicit `User-agent` + `Allow: /` stanza for each of: OAI-SearchBot, ChatGPT-User, GPTBot, PerplexityBot, ClaudeBot, Claude-User, Google-Extended, CCBot, Applebot-Extended; keeps `User-agent: *` and the `Sitemap:` line; no `Disallow: /` anywhere. Fail first.
- [ ] Verify each bot name against the operator's current documentation (context7/WebFetch) **before** writing — names change; do not rely on memory.
- [ ] Edit `robots.txt`; `npm run verify`; after deploy `curl -A "<UA>"` each bot against `/`, `/about`, `/robots.txt` (already 200 today; this proves policy did not regress).
- Note (do not oversell): Google-Extended does not govern AI Overviews (Googlebot does); explicit `Allow` is documentation, not a ranking signal. **Rollback:** revert.

## W3 — Off-site entity consistency (biggest AI-platform lever)

Evidence: search snapshots returned "600,000+ SF", "Indianapolis", "30-day closings", "four core markets" from the old site; LoopNet company profile (linked in our own `sameAs`) still says 600K+/four markets; a duplicate LoopNet "Baltimore, MD" profile exists; legacy `www…/portfolio-1` and `/tenants` still indexed.

- [ ] **Step 1 — Fact sheet (Claude):** one canonical block (name, legal name, HQ address, phone, email, founded, 500,000+ SF, 140+ tenants, markets per W1, deal size, all-cash 30–45 days, buy box). Source = the live site after W1 + `Notion 3706ecd8` freshness canon. **No invented figures.**
- [ ] **Step 2 — Profile inventory (Claude, read-only):** fetch each of LoopNet (Potomac + Baltimore duplicate), Crunchbase, LinkedIn, realty.com, Nestfully; record current text + which fields are wrong.
- [ ] **Step 3 — Copy pack (Claude → Gabriel):** per-platform paste-ready text, plus the LoopNet duplicate-merge request text. Delivered as a single doc/artifact.
- [ ] **Step 4 — Execute (Gabriel):** logins/edits are yours (I do not enter credentials or submit account forms). Report back done/not done per platform.
- [ ] **Step 5 — Re-measure (Claude):** repeat the three search queries + the AI-extraction fetch 2–4 weeks after; success = no result string contains 600,000+/Indianapolis. **Confidence:** medium (search/AI caches lag; not fully in our control).

## W4 — Search Console + Bing (setup, since neither is verified)

- [ ] **Step 1 (Gabriel):** add `https://oxfordra.net/` as a **Domain** property in Google Search Console via DNS TXT in Netlify DNS; do the same in Bing Webmaster Tools (import from GSC is fastest). I never enter credentials or edit DNS on my own.
- [ ] **Step 2:** submit `sitemap.xml` in both; request indexing for `/`, `/about`, `/sell-your-building`, the four guides.
- [ ] **Step 3:** URL-inspect `www.oxfordra.net/portfolio-1` and `/tenants`; confirm they 301 and request recrawl so the stale titles drop.
- [ ] **Step 4:** enable IndexNow (key file in site root → new allowlist entry in `build-dist.mjs` + test) **only if** Bing shows slow pickup; otherwise skip (YAGNI).
- [ ] **Step 5:** once verified, feed GSC data (Performance, Indexing, CWV) into the W6 probe report.

## W5 — Local Lighthouse baseline

- [ ] **Step 0 — Feasibility:** confirm a Chrome/Chromium binary is usable (`CHROME_PATH`); Playwright's browser is not installed here. If none, fall back to the Browser-pane tools for lab-approximate checks and say so.
- [ ] **Step 1:** `npx lighthouse` on live `/` , `/sell-your-building`, `/for-brokers`, one guide — mobile + desktop, 3 runs, median; save JSON to `Claude_Workspace/…/outputs/` with `YYYY-MM-DD_` naming.
- [ ] **Step 2:** rank any regressions vs the skill's targets (LCP ≤ 2.5s, CLS 0, INP ≤ 200ms); each becomes its own finding. No fixes without a finding + test.

## W6 — Monthly SEO probe (scheduled)

Productize the review's crawl (`crawl.py`, scratchpad) as `scripts/seo-probe.mjs` (Node, no deps) in the site repo.

- [ ] **Test first:** unit tests on pure functions (attribute-order-agnostic tag reader, JSON-LD flattener, claim checker) with fixtures — **the attribute-order false positive in this review is the regression test.**
- [ ] **Checks:** all sitemap URLs 200; canonical == `<loc>`; title/description lengths; H1 count; JSON-LD parses + Org core identical across pages + `@id` links resolve; sitemap `lastmod` ≥ last content change; `.html`→clean 301s; 404 real; 10-UA crawler fetch parity; **claim strings** ("500,000+ SF", "three core markets" [was "two core markets" — superseded 2026-09-23], "30–45 day", and no numeric LTV) consistent across pages/`llms.txt`; **off-site drift**: three fixed search queries flagged if they return "600,000+" / "Indianapolis".
- [ ] **Output:** JSON + short markdown; email to `ggoldberg@oxfordra.net` ONLY via Outlook COM, **only on findings** (silent when clean).
- [ ] **Register (monthly, decided):** `register-scheduled-task` v2.x → **CC/MCP fleet** (repo access), supervised `create_scheduled_task` only — never registry splice. Cron: first Monday, **after** the LoopNet sync slot (read the sync task's actual cron at registration; do not trust the 7:30 vs 10:40 discrepancy seen in notes). Run the registration QC gate + fire-time sanity check; run once manually first.
- [ ] Read-only; no writes to the site; does not depend on Cowork.

## W7 — Skill + knowledge capture

- [ ] `website-perfection` → **v1.2** (in an `ora-skills` worktree; single-writer): add dimension **H. Off-site entity consistency**, **I. AI-crawler policy**, the attribute-order-agnostic crawl rule, "PageSpeed keyless quota → local Lighthouse", and the worktree/gate recipe below. Update its Live-state baseline (§3) after W0/W1 deploy.
- [ ] **Memory (one file):** *website-canonical worktree gotchas* — junction `node_modules` from the main checkout (`cmd //c mklink /J`), revert the regenerated `knowledge-base.json` (CRLF/timestamp noise) before committing, `csp-smoke` needs `playwright` (absent locally → CI is the gate), site write gate needs the per-session override token and blocks **empty** replacement strings, multi-line `Edit` works on the CRLF working tree, and `preflight-shared-checkout` reports CONTESTED for *untracked* task dirs (check mtime + claims before proceeding).
- [ ] `event_log.md` via `python ~/.claude/maintenance/append-event-log.py` (never hand-edit). Reporting-only task-hygiene pass at session end.

## Workflow optimizations (mapped)

| Tag | Item | Where |
|---|---|---|
| skill gap | off-site entity + AI-crawler dimensions missing from `website-perfection` | W7 |
| automation | monthly live-vs-repo SEO probe | W6 |
| friction | PageSpeed keyless quota exhausted → local Lighthouse | W5 |
| knowledge | worktree/gate gotchas + attribute-order lesson | W7 |

## Definition of done
PR #84 merged and **served** JSON-LD verified on oxfordra.net · W1/W2 merged and verified live · off-site profiles updated and re-measured clean · GSC/Bing verified with sitemap submitted · Lighthouse baseline stored · probe registered and one manual run clean · skill v1.2 + memory + event-log persisted.
