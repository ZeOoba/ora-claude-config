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
  - **gate:** the PR's CI run is green on the merge ref.
  - **deploy:** merge to `main`. `ci.yml` has **no concurrency group** — first check for an in-flight `main` push run (`gh run list -R ZeOoba/ora-pm -b main -e push`) and wait for it to finish, or two deploys race and the older build can land last.
  - **post-verify (all four):** (1) the post-merge push run's "Deploy to Cloudflare Pages" step succeeded; (2) the served bundle at `ora-pm.pages.dev` (`/assets/index-*.js`, resolved from `/`) changed AND contains a string unique to the change; (3) `/api/health` returns 200; (4) `origin/main` tip equals the merge commit. A health hit alone proves nothing — `/api/health` is unauthenticated but every other `/api` route is behind admin auth, so an unauthenticated probe of a new route returns 401 whether or not it exists.
  - **rollback:** revert the merge commit on `main` (CI redeploys).
  - **crons** do not ride the deploy: CC fleet `ora-pm-daily-crons` + `ora-pm-monthly-billing`, with off-host GitHub Actions backup workflows (`delinquency-backup.yml`, `monthly-billing-backup.yml`) — each backup's live/pending status is the task SKILL.md's `offhost-backup:` frontmatter, not this file. The Windows Task "ORA PM Crons" is retired (disabled 2026-08-16, OI-162) — do not re-enable.

## After
1. **After ANY push in the chain** — `python ~/.claude/maintenance/verify-push.py [--branch NAME]`; exit 0 required. A push's own exit code is not evidence (a pipe masked a real failure once, producing a false "push succeeded"); this re-derives local HEAD vs the remote tip. Paste its output. Exits: 0 match · 1 diverged · 3 detached · 4 no upstream · 5 remote unreachable · 6 branch not on remote — 5 means **nothing was verified**, not "in sync".
2. Append the release (target, what shipped, verification result) to `memory/event_log.md`.
