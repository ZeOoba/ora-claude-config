# /ship — Lane L7 (release / deploy)

Target-aware. The confidentiality guard hard-wraps every path. **NEVER deploy without explicit per-deploy permission.**

## Pre-flight (all targets)
1. **superpowers:verification-before-completion** — evidence the build is green.
2. Run the target's gate (below).
3. Run the target's QC sub-agent.
4. **Ask for explicit permission**, naming the target and exactly what will change.

## Targets
- **Brain mirror (`oxford-command-center`):** gate `npm run gate` (typecheck · lint · test · reconcile $0) → deploy `scripts/deploy-mirror.ps1` (redacted, behind Cloudflare Access) → post-verify: curl apex + a `*.pages.dev` hash → expect **302**; confirm **0 confidential terms** in `dist` → rollback: redeploy the previous build.
- **oxfordra.net:** HARD GUARDRAIL — never edit/build/deploy without explicit permission. gate PageSpeed/CSP + **site-qc-reviewer** sub-agent → deploy Netlify MCP → `npx netlify-cli` fallback → post-verify curl 200 + visual → rollback: Netlify "publish previous deploy".
- **ora-pm:** deploys are **AUTOMATIC** — `ZeOoba/ora-pm` `.github/workflows/ci.yml` runs on push to `main` (npm ci → typecheck → test → build → `wrangler pages deploy ./dist --project-name ora-pm`, deploy step gated on `refs/heads/main` + push). Never hand-run `wrangler pages deploy`.
  - **Pre-flight fit:** merging (or pushing) to `main` IS the production deploy, so Pre-flight step 4's permission is granted BEFORE the merge. `main` is unprotected — a direct push deploys with no PR CI gate; don't. ora-pm has no QC sub-agent (skip Pre-flight step 3).
  - **gate:** the PR's CI run is green on the merge ref.
  - **migrations first:** migrations are NOT applied by CI. If the PR adds `supabase/migrations/*.sql`, apply it before merging via `db-migrate.yml` (`workflow_dispatch`, dry run first, then real) and confirm it landed.
  - **deploy:** merge to `main`. Read `ci.yml` for a `concurrency:` key first. **Without one**, two main runs race and an older build can land last — `gh run list -R ZeOoba/ora-pm -b main -e push -s in_progress` and `-s queued` must both be empty before merging. **With one** (ora-pm PR #36 adds serialization + a skip-if-not-tip step), a run whose commit is no longer main's tip skips its deploy — verify on the tip commit's run.
  - **post-verify (all apply):** (1) the push run for `main`'s tip shows "Deploy to Cloudflare Pages" succeeded (log: `Uploading Functions bundle` … `Deployment complete`); (2) behavior shipped — for `src/` changes, the served `/assets/index-*.js` (resolved from `ora-pm.pages.dev/`) changed and contains a string unique to the change; for `server/`/`functions/`-only changes the asset hash does NOT change (log shows `Uploaded 0 files`), so confirm via an authenticated probe or a deliberately observable response instead; (3) `/api/health` returns 200; (4) `origin/main` tip equals the PR's landed commit. A health hit or an unauthenticated 401 proves nothing: `/api/health` is open, admin routes 401 without admin auth, `/api/cron/*` 401 without the cron bearer, `/api/portal/*` 401 without a tenant token — a 401 does not show the route exists (only `/api/webhooks/*` 404s).
  - **rollback:** revert the PR's landed commit(s) on `main` (CI redeploys); for speed, first roll back to the prior deployment in the Cloudflare Pages dashboard (no rebuild), then still revert on `main` so the next push doesn't redeploy the bad code. A revert does NOT roll back schema — if the change shipped a migration, confirm the old code runs against the new schema or write a forward-fix migration.
  - **crons:** schedules live outside CI but their logic ships with every deploy — every trigger POSTs to the live `/api/cron/*`, which posts money (late fees, rent/CAM charges). Don't land a `server/routes/cron.ts` change near a fire time (read crons from `fleet-roster.md` and the backup workflows). Triggers: CC fleet `ora-pm-daily-crons` + `ora-pm-monthly-billing`, with off-host GitHub Actions backup workflows (`delinquency-backup.yml`, `monthly-billing-backup.yml`) — each backup's live/pending status is the task SKILL.md's `offhost-backup:` frontmatter, not this file. The Windows Task "ORA PM Crons" is retired (disabled 2026-08-16, OI-162) — do not re-enable.

## After
1. **After ANY push in the chain** — `python ~/.claude/maintenance/verify-push.py [--branch NAME]`; exit 0 required. A push's own exit code is not evidence (a pipe masked a real failure once, producing a false "push succeeded"); this re-derives local HEAD vs the remote tip. Paste its output. Exits: 0 match · 1 diverged · 3 detached · 4 no upstream · 5 remote unreachable · 6 branch not on remote — 5 means **nothing was verified**, not "in sync".
2. Append the release (target, what shipped, verification result) to `memory/event_log.md`.
