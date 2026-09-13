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
- **ora-pm:** gate `npm run typecheck && npm test && npm run build` (mirrors `.github/workflows/ci.yml`'s `ci` job) → deploy is **automatic on merge to `main`** — the same CI job's last step runs `npx wrangler pages deploy` (there is no separate manual deploy path; verify against `ci.yml` before trusting this line) → post-verify: the post-merge CI check below, then hit `/api` health → rollback: redeploy prior; crons run via the Windows Task.

## After
1. **After ANY push in the chain** — `python ~/.claude/maintenance/verify-push.py [--branch NAME]`; exit 0 required. A push's own exit code is not evidence (a pipe masked a real failure once, producing a false "push succeeded"); this re-derives local HEAD vs the remote tip. Paste its output. Exits: 0 match · 1 diverged · 3 detached · 4 no upstream · 5 remote unreachable · 6 branch not on remote — 5 means **nothing was verified**, not "in sync".
2. **After ANY merge to `main` on a target whose deploy runs inside CI** (currently: ora-pm's `ci.yml`) — a merged PR / green PR check is not a live deploy (Engineering OS: "a bot status check is never a review verdict"). Pull the newest workflow run on `main` and check it, not the PR: `gh run list --repo <owner/repo> --workflow=ci.yml --branch main --limit 1 --json databaseId,headSha,status,conclusion`.
   - **Tip check** — `headSha` must equal the merge commit just pushed; a stale prior run proves nothing about this merge. If `status` isn't `completed` yet, poll (`gh run watch <databaseId>`) rather than reading a partial result.
   - **Deploy step** — `gh run view <databaseId> --repo <owner/repo> --json jobs -q '.jobs[].steps[] | select(.name | test("Deploy"))'` must show `conclusion: success`. The gate steps (typecheck/test/build) passing does not imply the deploy step ran or succeeded — it can be skipped (wrong ref/event) or fail after a green build.
   - Only after both hold, run the target's own post-verify (health check, curl, etc.) above.
3. Append the release (target, what shipped, verification result) to `memory/event_log.md`.
