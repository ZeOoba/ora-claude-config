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
- **ora-pm:** gate `vitest run` + build → deploy `npx wrangler pages deploy dist --project-name ora-pm` (**MANUAL** — no git auto-deploy) → post-verify: hit `/api` health → rollback: redeploy prior; crons run via the Windows Task.

## After
1. **After ANY push in the chain** — `python ~/.claude/maintenance/verify-push.py [--branch NAME]`; exit 0 required. A push's own exit code is not evidence (a pipe masked a real failure once, producing a false "push succeeded"); this re-derives local HEAD vs the remote tip. Paste its output. Exits: 0 match · 1 diverged · 3 detached · 4 no upstream · 5 remote unreachable · 6 branch not on remote — 5 means **nothing was verified**, not "in sync".
2. Append the release (target, what shipped, verification result) to `memory/event_log.md`.
