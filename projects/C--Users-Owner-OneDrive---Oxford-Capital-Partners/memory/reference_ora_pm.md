---
name: reference-ora-pm
description: ORA PM app (ZeOoba/ora-pm) — BETA status (not live, no tenant paying through it yet), empty-payments-table + N+1 delinquency-check timeout findings (2026-08-17), local path & oxford-perfection disambiguation, Supabase magic-link redirect whitelist, UX-overhaul roadmap status (Phase 1+2a shipped+pushed, Stripe ACH payments built beyond original scope), 2026-07-16 audit findings pointer, 2026-07-18 test-suite status, and the wrangler pages deploy --branch gotcha (2026-08-04)
metadata: 
  node_type: memory
  type: reference
  originSessionId: 6c6059fc-f17f-4580-94d9-40b005f38973
  modified: 2026-08-17T15:53:13.371Z
---

## ORA PM — ZeOoba/ora-pm

**Repo:** `ZeOoba/ora-pm`
**Production URL:** `https://ora-pm.pages.dev` (Cloudflare Pages)

## ⛔ STATUS: BETA — not live (Gabriel, 2026-08-17)

**No tenant currently pays rent through ora-pm.** Gabriel confirmed 2026-08-17: this is intentionally pre-launch, being built out for a *future* switch to tenants paying through this software. Real rent collection today happens outside ora-pm entirely (PM company / other channel — the ORA Master Workbook remains the firm's source of record for cash per `CLAUDE.md`).

**Consequence — the daily `delinquency-check` cron digest is not a real signal yet.** Confirmed 2026-08-17: the `payments` table is **completely empty** (`Content-Range: */0`, zero rows, ever) while `charges` has 108 rows going back to a 2026-06-04 backfill. Since `ar_ledger.balance = total_charged − total_paid` ([0010_ar_ledger_property_name.sql:34](file:///C:/Users/Owner/ora-pm/supabase/migrations/0010_ar_ledger_property_name.sql)) and `total_paid` is structurally zero for every lease, every "N Delinquent Tenants" email sent to date (25 on 08-11/08-13/08-14, etc. — see `ping-crons-cron.log`) is gross-billed-since-inception, not real delinquency. Treat every past and current ora-pm delinquency digest as **not meaningful** until Gabriel wires real payment recording (manual entry via `server/routes/payments.ts` and/or the Stripe ACH webhook in `server/routes/webhook.ts`, both already built) and tenants actually start paying through the app. Don't alarm on these numbers or forward them as real AR exceptions in the interim — this supersedes [[reference_delinquency_report_collection_status_blindspot]] in severity (that note assumed some real signal underneath the noise; this one has none yet).

**N+1 timeout bug found the same day — FIXED 2026-08-17, committed not pushed.** `delinquency-check`'s handler did up to 2 sequential Supabase round-trips per AR-ledger row in a `for` loop (no batching). Live-tailed via `wrangler pages deployment tail` 2026-08-17: with 68 positive-balance rows (up from 25 on 08-14, driven by the 08-01 monthly rent-charge batch landing on zero payments) the endpoint reliably exceeded its 240s client timeout — Cloudflare's own log showed the invocation status `Canceled`, still running, no error thrown.

**Fix:** commit `16bd0a1` on local `main` (`fix(cron): batch delinquency-check queries to stay under the cron timeout`) — batches the two existence-checks into 2 bulk `.in()` queries via the file's existing `fetchChunked`/`BULK_QUERY_CHUNK_SIZE` helper (same pattern already used by `monthly-billing` in the same file), leaving the per-row late-fee INSERT untouched. Followed `/debug` (failing regression test first, confirmed 10-calls-pre-fix → ≤2-calls-post-fix; full suite run — caught and correctly resolved an OI-042 raw-error-passthrough tripwire hit by extending `cron.ts`'s existing allowlist under its already-documented operator-only-endpoint rationale; independent code review returned "Ready to merge, Yes" with one Important note addressed inline — the fix also changes error handling from silent-skip-on-query-failure to fail-closed, now called out explicitly in a code comment). 465/465 tests pass, `tsc --noEmit` clean.

**⛔ Not pushed to `origin/main` as of 2026-08-17** — local `main` is 1 commit ahead. Per the deploy gotcha above, this also means it is NOT live at `ora-pm.pages.dev` yet (deploy requires an explicit `wrangler pages deploy` from `main`, separate step). Doesn't matter for now since `ora-pm-daily-crons` is paused (see below) and the app is beta, but push/deploy before re-enabling the cron.

## Deploy gotcha — `wrangler pages deploy` needs `main` checked out, or it silently ships a preview (2026-08-04)

This project has **no Git auto-deploy** (`tech.md` §11) — `wrangler pages deploy` is the only path to prod, and Cloudflare Pages tags each deploy with whatever git branch is checked out **locally** at deploy time, not any server-side branch state. Confirmed live 2026-08-04 (OI-047): running `npx wrangler pages deploy dist --project-name ora-pm` from a feature-branch worktree produced a **branch preview alias** (`https://<hash>.ora-pm.pages.dev`, `Environment: Preview`, `Branch: fix/oi-047-...`) — `ora-pm.pages.dev` (what tenants and `ping-crons.ps1` actually hit) was untouched. No error, no warning that it wasn't prod.

**The fix, and the only reliable way to ship:** check out `main` locally (`git pull origin main` after merging), build, deploy from there — `wrangler pages deployment list --project-name ora-pm` will show `Environment: Production` / `Branch: main` for that deploy. Verify with that command after every deploy meant for prod; don't infer production status from the deploy command's own success output.

**Every prior merged OI-0xx fix in this repo followed this pattern already** (PR → merge to `main` → deploy from `main`) — this note exists because the deploy step of a plan/task brief hadn't spelled it out explicitly, so it's easy to skip when working from an isolated feature-branch worktree, which is now the default workflow for ora-pm changes.

## Supabase Magic Link Auth — Site URL + Redirect URL Whitelist

**Hosted Supabase project (prod):** ref `tvfarkddtbtdrpvvehth` (`https://tvfarkddtbtdrpvvehth.supabase.co`), org **Oxford Realty Advisors**, project name **ora-pm**, branch `main`/PRODUCTION. Dashboard → Authentication → **URL Configuration**. (The `supabase/config.toml` in the repo only governs the LOCAL `supabase start` stack — NOT this hosted project.)

Admin login: `emailRedirectTo: window.location.origin`. Tenant portal login: `window.location.origin + '/portal'`.

**Current correct config (set 2026-06-07):**
- **Site URL:** `https://ora-pm.pages.dev`  ← MUST be the prod URL, NOT localhost.
- **Redirect URLs:** `https://ora-pm.pages.dev`, `https://ora-pm.pages.dev/**` (the `/**` covers the `/portal` path), `http://localhost:5173`.

**Mechanism / why it matters:** Supabase **silently** rejects any `emailRedirectTo` not on the Redirect-URLs allow-list and falls back to the **Site URL**. Allow-list entries are EXACT-match unless a wildcard is used — a bare `https://ora-pm.pages.dev` does NOT cover `…/portal`; use `/**`.

**2026-06-07 bug (fixed):** Site URL was the stale dev default `http://localhost:3000`, so magic links redirected to `localhost:3000` (ERR_CONNECTION_REFUSED) — even though the app code was correct and `https://ora-pm.pages.dev` was already in the allow-list. Root cause was the Site URL, plus the `/portal` path not being wildcarded. Fixed via the dashboard.
**Operational note:** a magic link bakes in its `redirect_to` at generation time — after any URL-config change, request a FRESH link and initiate login FROM the prod site (not a stale email or a localhost tab).

**Before any NEW deploy target** (new Cloudflare preview URL / custom domain): add it to Redirect URLs first.

## Local repo path & disambiguation (2026-06-05)

**Local path:** `C:\Users\Owner\ora-pm` (git, remote `github.com/ZeOoba/ora-pm`). The REAL property-management app (admin pages under `src/pages/` + tenant portal under `src/portal/`). Stack: React 19 · Vite 6 · TS · Tailwind v4 · React Router 6 · TanStack Query · Zod · Supabase (auth/DB/storage) · Hono on Cloudflare Pages Functions · Stripe ACH. Data model in `src/types.ts` + `supabase/migrations/`.

**Do NOT confuse with** `C:\Users\Owner\oxford-perfection` — that's the website + tooling + Brain-spec workspace (static-site folders v3/master-preview/deploy, PowerShell diagnostics, PowerBI kit). Its build-prompt markdown describes a *separate* "oxford-command-center" React Brain, NOT ora-pm. On 2026-06-05 a subagent exploring oxford-perfection misread those specs as ora-pm's code — always verify `package.json` name = `ora-pm` + remote ZeOoba/ora-pm before acting.

## UX Overhaul — roadmap status (updated 2026-07-16, verified against actual repo state)

Spec: `docs/superpowers/specs/2026-06-05-ora-pm-ux-overhaul-design.md` (benchmarked vs AppFolio/Yardi Breeze). Each phase = own plan + review gate. **Correction:** the original entry here (written 2026-06-05) claimed Phase 1 was "shipped to local main, 13 commits, not pushed" and Phase 2a was "NEXT" — both stale. Verified 2026-07-16: `main` has zero divergence from `origin/main` (`git status` clean, `git log --oneline origin/main..HEAD` empty) — every phase below is merged AND pushed.
1. **Design system — SHIPPED + PUSHED.** Plan: `docs/superpowers/plans/2026-06-05-ora-pm-phase1-design-system.md`. Tailwind v4 `@theme` brand tokens (navy #1B2A4A / gold #C9A96E / parchment), self-hosted EB Garamond/DM Sans/IBM Plex Mono via `@fontsource`, `src/components/ui/` primitives (Badge/Card/Button/KpiStat/EmptyState — pure-fn class logic in `*-variants.ts`/`badge-tone.ts` + Vitest tests), restyled form system + admin/portal shells + PageHeader, unauthenticated `/styleguide` route. Confirmed present on disk 2026-07-16 (all files exist, StyleGuide.tsx + `/styleguide` route wired). NOTE: `card.ts`/`Card.tsx` case-collide on Windows — keep logic files distinctly named (`card-variants.ts`).
2. **Lease + contact upload-parse — SHIPPED + PUSHED** (commit `926f331`, "Phase 2a lease intake — AI extraction with confidentiality guard (#2)"). Plan: `docs/superpowers/plans/2026-06-05-ora-pm-phase2a-lease-intake.md`. Confirmed wired: `server/routes/intake.ts` calls `parseTerms`/`containsConfidentialTerm` from `server/lib/confidentiality.ts` before any Anthropic egress.
3. **Functional polish (as originally scoped) — NOT built.** No plan doc exists for it (no `*phase3*` file under `docs/superpowers/`), and no code signals for the originally-scoped items (⌘K search, saved filters, tabbed tenant detail, document library) — grepped 2026-07-16, zero hits.
4. **Unplanned, since built instead: full Stripe ACH payment system** — webhook handlers (signature verification, idempotency, dispute/refund events), autopay billing cron, portal Pay Now (Stripe Financial Connections), payment history, account/MFA page. Not part of the original 3-phase spec; substantial commit volume (15+ commits). Also shipped: a separate `docs/superpowers/plans/2026-06-05-ora-pm-production-hardening.md` plan (JWT + domain auth, Zod validation, sanitized error responses, rate limiting, CRON_SECRET, CI auto-deploy on `main` push) — also done.

**2026-07-05 incident:** an "object-DB wipe" lost some local commits; a dedicated recovery branch (`recovery/2026-07-05-object-db-loss`) recovered unpushed 2026-06-07 auth-hardening work (merged as `8418c44`). This is very likely also what reconciled the "13 unpushed Phase-1 commits" this memory previously described — the recovery process merged with `origin/main`, which already had them. Whether Phase 1 was pushed before or during that recovery is not reconstructed here; what's confirmed is the CURRENT state below.

**Repo state (verified 2026-07-16):** local `main` (`8418c44`) exactly matches `origin/main`; working tree clean; 110 commits total, spanning 2026-06-04–2026-07-08. No uncommitted or unpushed work of any kind. See [[projects]].

**2026-07-16 cc-audit-army audit** (generic-mode, 33 confirmed findings: 3 critical/4 high/14 medium/12 low) — report: `Claude_Workspace/02_Outputs/2026-07-16_ora-pm_AuditReport_v01.md`. Criticals: an `ar_ledger` SQL view cartesian-fan-out corrupting AR balances past month two (feeds the late-fee cron), PortalDashboard dividing already-dollar values by 100 (tenants see 1/100th of balance owed), and real (declassified E. Fulton) deal terms committed in git-tracked `.env.example` — remediated same day: `.dev.vars` created locally with the real value (properly gitignored), `.env.example` line 8 needs a manual one-line placeholder swap (blocked for Claude by a machine-wide `.env`-pattern edit hook), and a git-history purge procedure was prepared but not run (Gabriel's call — the deal is declassified, so this is hygiene, not an active-invariant breach). Production secrets were confirmed already correctly provisioned via `wrangler pages secret put` — the leak never reached the live deployment.

## Test-suite status (verified 2026-07-18)

A task was raised to fix `npm test` pollution allegedly caused by a stray untracked `node_modules.bak_local/` directory (a local Stripe-package backup whose name didn't match `vitest.config.ts`'s `configDefaults.exclude` glob, so ~49 bundled `@stripe/*` vendor tests were being collected alongside the real suite). On investigation the directory did not exist — not at the repo root, not found anywhere under the user profile via search, and absent from `git status`. `npx vitest run` confirmed a clean run: exactly the repo's own 32 test files, 178 tests, all passing, no vendor-test noise. `vitest.config.ts` was left unmodified — no `test.exclude` entry was needed.

**Why noted:** the directory must have been removed or moved out-of-band (untracked, so no commit trail) sometime before 2026-07-18 — the symptom had already self-resolved. If a similar "stray node_modules.bak* pollutes vitest" report recurs, check for the directory's actual presence first rather than assuming the prior fix regressed.

**2026-07-18 portal Charge/Lease type-drift fix — SHIPPED + PUSHED** (commit `f47bbe0`, "fix(portal): derive Charge/Lease types from schema, fix always-empty open-charges list"; `origin/main` confirmed at `f47bbe0` post-push). Root-caused the 2026-07-16 audit finding #7 fully: `portal-api.ts`'s hand-rolled `Charge`/`Lease` interfaces diverged from the schema on three fields (`charge_type` vs real `type`, a `status` column that doesn't exist on `charges` at all, `monthly_rent` vs real `base_rent_monthly`). The bogus `status` field meant the Pay Now `openCharges` list was always empty in production — the flagged `.charge_type.replace()` crash was actually unreachable dead code gated behind that empty list. Fix derives `Charge`/`Lease` in `portal-api.ts` from the schema-accurate `src/types.ts`, and removes the `status==='open'` filter (every returned charge is now treated as payable — Gabriel's explicit 2026-07-18 ruling, since there's no per-charge paid/open tracking in the schema to filter on). This also newly exposed a real bug — a tenant with 2+ simultaneous active leases could combine charges from both into one ACH payment, misattributing the full amount to a single `lease_id` — closed with `singleLeaseId()` in `src/portal/lib/charges.ts` (fail-closed: blocks payment across leases). 4 new regression tests added (`tests/lib/portal-types.test.ts`, `tests/lib/portal-charges.test.ts`, `tests/components/portal-charge-field-drift.test.ts`); full gate (`tsc --noEmit` + `vitest run`) green at 32 files/178 tests; adversarial REFUTE pass run (caught the multi-lease issue above before ship). The earlier "someone's active WIP, left untouched" note in this file (written mid-fix, before the commit landed) is superseded — this is now done, not pending.
