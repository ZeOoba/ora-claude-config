---
name: repo-architecture
description: Use when working in, or asking how to navigate, any of Gabriel's 7 most-active GitHub repos (ora-skills, ~/.claude/ora-claude-config, oxford-command-center, Website/website-canonical, AAOS, ora-county-sales-monitor, ora-pm) - purpose, layout, data flow, deploy path, gotchas, and which files to read first. Point-in-time snapshot; verify counts and paths against the repo.
---

# Repo architecture map (v1.0.4)

Selected by `pushedAt` (gh repo list). Local checkouts under `C:\Users\Owner`. All private except none. Counts drift - verify before quoting. Facts marked (unverified) were not checked against source.

Cross-repo rules that apply everywhere: shared checkouts are single-writer (fetch first, stage explicit paths, never `git add -A`, use a worktree); oxfordra.net deploys need in-turn confirmation; confidential deals never appear in external surfaces.

## 1. ora-skills  (`ora-skills/`, ZeOoba/ora-skills)
**Purpose:** source of truth for ORA custom Claude Code/Cowork skills (~75 flat skill dirs, each with `SKILL.md` + optional references/scripts/templates/tests).
**Layout:** `tools/` (packaging, drift, mirror sync, CI gates, hooks/), the shared buy-box data file at repo root (version-bump gated), `_archive/` (retired, most tracked files), `_staging/` (gitignored drift ledgers), `.github/workflows/`.
**Mechanics:** frontmatter `name`+`description` does routing; no code path between skills. `tools/package_skills.py` zips to `.skill` (manual Cowork import); shared files injected via `SHARED_ROOT_DEPS`; hooks mirror to AppData cache (additive, repo wins).
**CI:** `tools-tests.yml`, `skill-gates.yml`, `claude-ci-fix.yml`; stdlib unittest via `bash tools/run_suite.sh`.
**Gotchas:** pre-commit blocks on a missing buy-box data-file version bump or bad frontmatter; new `test_*.py` under a skill is gated automatically (opt out only via a top-level `CI_EXCLUDE = "<reason>"`); CI `suite-continuity` fails when a suite present at the PR base disappears, unless (a) a file added in base..HEAD under `_archive/` (any depth) has a path ending `<skill>/<rest>` or `<skill>_retired-YYYY-MM-DD/<rest>` (path-only match) or (b) any commit in base..HEAD has a line starting `Suite-Removed: <path>` (recommended: `git mv <skill> _archive/<skill>_retired-YYYY-MM-DD` plus a trailer on the removing commit; the gate is looser); Cowork sandboxes can't do git writes (index.lock) - use Code; keep descriptions short; no tenant PII; red `tools-tests` can be an Actions billing block, not a failure.
**Read first:** `README.md`, `tools/skill_ci_gates.py`, `tools/hooks/pre-commit`.

## 2. ~/.claude  (ZeOoba/ora-claude-config)
**Purpose:** config/backup mirror of the live Claude Code setup (hooks, scheduled-task specs, memory, agents, commands). Not an app; nothing deploys from it.
**Layout:** `CLAUDE.md`, `settings.json`; `hooks/` (~36 guards, `lib/`, `tests/`); `maintenance/` (~91 probes/engines, `_state/`); `scheduled-tasks/<id>/SKILL.md` (CC/MCP fleet); `projects/.../memory/`; `docs/`; `_proposed/`; `skills/ agents/ commands/ workflows/`.
**Guards:** `hooks/pretooluse-dispatcher.py` runs an Edit/Write chain (~11) and a Bash chain (~12); first exit 2 blocks; missing guard fails closed. Self-check: `python hooks/pretooluse-dispatcher.py --selfcheck`. Three native pre-push gates (doctrine drift, hook tests, confidential-diff scan).
**Single-writer:** run `maintenance/preflight-shared-checkout.py --repo --paths --since <sha>` (0=go) before editing shared files; claims in `hooks/active-work/` via `hooks/lib/claim_work.py`.
**Backup scope:** `.gitignore` default-deny `/*` with explicit opt-ins; excludes credentials, `confidential-terms.json`, overrides, transcripts, caches. New top-level dirs only after `maintenance/scrub-before-optin.py`.
**Gotchas:** hardcoded `C:\Users\Owner` paths; register tasks only via MCP tools; Cowork-fleet specs live in OneDrive, not here; README counts point-in-time.
**Read first:** `README.md`, `hooks/pretooluse-dispatcher.py`, `maintenance/preflight-shared-checkout.py`.

## 3. oxford-command-center  ("The Brain")
**Purpose:** local-first portfolio/investment dashboard reconciling the master workbook with Notion, HubSpot, M365, QuickBooks CSVs, FRED. Read-only static mirror on Cloudflare Pages behind Access.
**Stack:** TypeScript; React 19/Vite/TanStack Query client; Hono on 127.0.0.1:8911; ExcelJS; SQLite warehouse; Zod contracts; Vitest/Playwright.
**Layout:** `src/` (contracts, analytics, modules), `server/` (workbook, warehouse, ai, sources), `scripts/` (gates, reconcile, importers, bake), `functions/` (CF edge), `architecture/` (lock docs, ownership.json, status.json), `config/` (ratified rulesets), `data/` (gitignored runtime).
**Data flow:** Spine A = workbook -> parseWorkbook -> Zod PortfolioSnapshot -> reconcile -> REST/SSE -> UI. Spine B = P&L files -> `warehouse/ingest.ts` -> SQLite (34 numbered migrations, architect-owned) -> metrics/engines -> `/api/warehouse/*`. Mirror: `bake-mirror.ts` -> `public/snapshot.json` (confidential redacted) -> hourly Pages deploy. Spine A and B NOI are independent; never compare without basis-matching (`reconcile:noi-crosscheck`).
**Gates:** `npm run gate` (11 steps), `gate:ci`; `check:refute` requires a Refute-Reviewed trailer; pre-push confidentiality scan.
**Financial-decision code** (capital-allocation verdict, acquisition engine, debt scoring, `intel-config.ts` incl. hurdle) needs the adversarial refute workflow; `config/*.json` never silently edited.
**Gotchas:** never touch `data/overlay.json`, `finance.sqlite`, `confidential-terms.json`; no DDL on the live DB; hooks block `git add -A`; check `status.json` before touching shared infra; CLAUDE.md merge-history table is stale; use `dev:server:once`; importers follow `scripts/import-insurance-data.ts` (oxford-command-center repo; see xlsx-warehouse-importer skill).
**Read first:** `CLAUDE.md`, `architecture/system-overview.md`, `scripts/import-insurance-data.ts` (all paths in this section are in the oxford-command-center repo).

## 4. Website / website-canonical  (oxfordra.net)
**Purpose:** static multi-page site on Netlify; Netlify Functions for forms/broker OM scoring; edge function `/api/chat` (Anthropic).
**Build:** `npm run build` = `build-listings --check` -> `build-kb` -> `build-dist` (allowlist copy to gitignored `dist/`; fails on unclassified root file, leaks, <14 HTML pages). Netlify Node 20.
**Config:** headers/redirects live in `_headers`/`_redirects` (not netlify.toml). CSP is hash-based (~21 inline scripts, no script `unsafe-inline`).
**Deploy:** treat a merge to `main` as a deploy and the standing rule is per-deploy confirmation (Invariant 2). Netlify Git integration is not visible in-repo (confirm in dashboard). `netlify-guard.js` blocks indirect `--prod`. Use `netlify deploy --build`, never `--dir=.`. Afterward `node scripts/verify-live-csp.mjs`.
**QC:** `npm run verify` (build, jsonld, unit, site, shim, functions); mutation, chat eval, Lighthouse separate.
**Gotchas:** editing any inline `<script>` requires `node scripts/csp-hashes.mjs --write`; new third-party origin needs a `_headers` entry; new root files must be classified in `build-dist.mjs` (website repo `scripts/`); `submission-created` webhooks gate on `form_name`.
**Read first:** `README.md`, `scripts/build-dist.mjs`, `_headers` (all paths in this section are in the website repo).

## 5. AAOS  (Agent-to-Agent Operating Substrate)
**Purpose:** filesystem task queue + handoff protocol between local Claude Code and cloud Cowork. No server/DB; atomic write-rename, exclusive-create locks, lease TTLs, fail-closed conflicts.
**Layout:** `tools/` (~13 CLI scripts + `_aaos_common.py`), `schemas/` (5 JSON Schemas), `agent-registry.json`, `docs/` (spec, ADRs 0001-0006), `templates/`, `tests/`.
**Data flow:** runtime state lives outside git in a OneDrive "seam" folder (`DEFAULT_SEAM_ROOT`, override `--seam-root`): tasks/locks/handoffs/events (NDJSON). Lease = lock, atomic rewrite, event emit as commit point. Heartbeat chain derive -> project-notion -> publish-notion (only network call, needs `NOTION_TOKEN`).
**Run:** `python tools/<name>.py`; tests `python -m unittest discover -s tests -p "test_*.py"`; CI on Python 3.11/3.13 with temp-dir seam.
**Gotchas:** exit codes 3 conflict / 4 lease lost / 5 event-commit failure; hyphenated script names need `tests/_tool_loader.py`; README stale (says no requirements.txt; test counts disagree); Cowork side unconfirmed live; heartbeat chain has no scheduled caller; stray `.py` in `docs/adr/`.
**Read first:** `README.md`, `docs/AAOS-SPEC.md`, `tools/_aaos_common.py`.

## 6. ora-county-sales-monitor  (Notion Worker)
**Purpose:** hosted county-sales-monitor skill (v0.5): recorded industrial sales <150K SF for Franklin OH, Baltimore Co MD, Polk IA into two Notion-managed DBs (Comps, Coverage).
**Runtime:** `@notionhq/workers`; two incremental syncs on 7d schedule, one county per execute chain; upsert key `County|Parcel|SaleDate|Price`; 4 req/s pacer; 365-day trailing window; Node 22+.
**Layout:** `src/index.ts` (syncs, regroup, pull memo), `src/rules.ts` (pure doctrine), `src/counties/{franklin,baltimore,polk}.ts`, `src/http.ts`, `src/transfer*.ts`, `test/`, `docs/`. Don't edit `.agents/` or `.claude/skills/`.
**Adapters:** Franklin = ArcGIS + Auditor Transfer zip via Range requests (no grantor); Baltimore = MdProperty + bcgis join; Polk = assessor CSV + inventory CSV. Tier C counties are static NO-PUBLIC-PRICE rows.
**Deploy:** supervised `ntn workers deploy`, then `ntn workers sync trigger <key> --preview`. No email from the worker; a separate digest task reads the DBs. No CI found.
**Gotchas:** never rename a county label or change `transactionKey` format (duplicates all rows); schema.properties changes migrate/can drop data; degraded Franklin pull emits no comps (coverage WARN); Baltimore TRADATE lags 4+ months; doctrine changes go to the skill first, then `rules.ts`. Code-level claims are README/AGENTS-derived (unverified against source).
**Read first:** `AGENTS.md`, `src/index.ts`, `src/rules.ts`.

## 7. ora-pm  (Property Manager)
**Purpose:** admin console (properties, units, tenants, leases, billing, AR, CAM, renewals, insurance, QuickBooks IIF) plus tenant portal (rent via Stripe ACH, documents, COI upload).
**Stack:** Vite/React 19/react-router/TanStack Query/Tailwind 4; Hono on Cloudflare Pages Functions; Supabase Postgres (Auth, RLS, Storage); Zod; Vitest + pg-mem; Anthropic for lease extraction.
**Layout:** `functions/api/[[route]].ts`, `server/` (routes, middleware, lib, db), `src/` (+ `src/portal/`), `supabase/migrations/` (0001-0013, schema source of truth), `scripts/`, `tests/`, `evals/`.
**Auth:** Supabase JWT; admin via `ADMIN_EMAILS` allowlist (admin email matching a tenant row is rejected); Stripe webhooks mounted before CORS for raw body.
**CI/deploy:** `ci.yml` typechecks/tests, and on `main` builds + `wrangler pages deploy` (Cloudflare Git integration deliberately off). `db-migrate.yml` manual (dry-run default). Cron backups (`delinquency-backup`, `monthly-billing-backup`) re-fire idempotent endpoints; primary schedulers are laptop fleet tasks.
**Gotchas:** wrangler.toml scheduler comments are stale; confidentiality guard scans filenames only; no tenant MFA self-recovery; `.env`/`.dev.vars`/`.db-password.local` exist in the tree (gitignore status unverified).
**Read first:** `README.md`, `server/index.ts`, `server/routes/cron.ts`.

## Changelog
- v1.0.4 (2026-11-05): corrected the suite-continuity description (path-only archive match at any depth; Suite-Removed line accepted from any commit in the range). Wording only; NO change to scored or governor constants.
- v1.0.3 (2026-11-05): documented the CI suite-continuity gate and its archive and `Suite-Removed` allowances in the ora-skills gotcha line. Wording only; NO change to scored or governor constants.
- v1.0.2 (2026-11-05): ora-skills suite gating is now auto-discovered (CI_EXCLUDE marker); updated the gotcha line. Wording only; NO change to scored or governor constants.
- v1.0.1 (2026-10-29): Marked which repo the `scripts/` paths in sections 3 and 4 belong to. This was a reference-path clarification only (wording; no change to procedures, scored or governor constants): NO change to scored or governor constants.
- v1.0 (2026-10-13): initial map of the 7 most recently pushed repos, built from read-only per-repo surveys.
