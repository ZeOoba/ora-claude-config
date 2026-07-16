---
name: reference-ora-pm
description: ORA PM app (ZeOoba/ora-pm) — local path & oxford-perfection disambiguation, Supabase magic-link redirect whitelist, and the 3-phase UX overhaul (Phase 1 design system shipped to local main 2026-06-05)
metadata: 
  node_type: memory
  type: reference
  originSessionId: 6c6059fc-f17f-4580-94d9-40b005f38973
---

## ORA PM — ZeOoba/ora-pm

**Repo:** `ZeOoba/ora-pm`
**Production URL:** `https://ora-pm.pages.dev` (Cloudflare Pages)

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

## UX Overhaul — 3-phase program (2026-06-05)

Spec: `docs/superpowers/specs/2026-06-05-ora-pm-ux-overhaul-design.md` (benchmarked vs AppFolio/Yardi Breeze). Each phase = own plan + review gate.
1. **Design system — SHIPPED to local `main` 2026-06-05** (13 commits, not pushed). Tailwind v4 `@theme` brand tokens (navy #1B2A4A / gold #C9A96E / parchment), self-hosted EB Garamond/DM Sans/IBM Plex Mono via `@fontsource`, `src/components/ui/` primitives (Badge/Card/Button/KpiStat/EmptyState — pure-fn class logic in `*-variants.ts`/`badge-tone.ts` + Vitest tests), restyled form system + admin/portal shells + PageHeader, unauthenticated `/styleguide` route. Plan: `docs/superpowers/plans/2026-06-05-ora-pm-phase1-design-system.md`. 128/128 tests green. NOTE: `card.ts`/`Card.tsx` case-collide on Windows — keep logic files distinctly named (`card-variants.ts`).
2. **Lease + contact upload-parse — NEXT.** Drop a lease PDF → Cloudflare Worker calls Anthropic API (`claude-opus-4-8`) → extracted fields land in LeaseForm for review-and-confirm → save lease + store PDF in existing `lease_documents`. New `tenant_contacts` table (billing/emergency/authorized_signer/guarantor). **Fail-closed confidentiality denylist guard** before any Anthropic egress — managed-tenant leases only; E. Fulton/acquisition docs blocked. Needs `ANTHROPIC_API_KEY` as Cloudflare secret (server-side only).
3. **Functional polish** — dashboard KPI widgets, per-page quick actions, saved filters, ⌘K search, tabbed tenant detail (Yardi "Other Info"), document library.

**Repo state:** local `main` is 13 commits ahead of `origin/main` (Phase 1, **unpushed** — push/deploy gated on Gabriel; the production-hardening plan wired auto-deploy on `main` push). See [[projects]].
