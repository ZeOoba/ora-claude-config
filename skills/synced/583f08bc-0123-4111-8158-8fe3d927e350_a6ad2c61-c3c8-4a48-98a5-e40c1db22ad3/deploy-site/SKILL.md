---
name: deploy-site
description: Build and deploy the oxfordra.net website to Netlify. Use when making site changes or deploying updates.
user-invocable: true
allowed-tools: Read Glob Grep Edit Write Bash WebFetch mcp__Claude_Browser__preview_start mcp__Claude_Browser__computer mcp__a66aaa4a-ffcd-4066-b2af-79c4ce807809__netlify-deploy-services-reader mcp__a66aaa4a-ffcd-4066-b2af-79c4ce807809__netlify-deploy-services-updater
---

## Instructions

Deploy the Oxford RA website (oxfordra.net) from its canonical git repo.
Hard Invariant 2 applies: never build/edit/deploy without explicit per-deploy
permission from Gabriel, given live and naming exactly what will change.

**Canonical source is the git repo, not a build script.** The repo at
`C:\Users\Owner\website-canonical` (git `ZeOoba/Website`, `= OXFORDRA_REPO`)
IS the deploy tree — static HTML/CSS/JS, no build step, `netlify.toml` sets
`publish = "."`. There is no "oxford-site" staging copy to sync from; any
folder named `oxford-site` you find elsewhere (including
`Claude_Workspace/.../oxford-site/build-and-deploy.js`) is a pre-redesign
relic — it fetches the LIVE site and rewrites it with April-era regex
patches (hyphenated nav classes, PNG logo assumptions) that predate the
BEM/inline-SVG redesign now in `website-canonical`. Running it would
corrupt the current site. Do not use it; do not "sync" from it.

1. `git -C "C:/Users/Owner/website-canonical" status` — confirm the tree is
   clean and you know which branch/commit is being shipped.
2. Make/verify the edits on a feature branch, commit, push (push is
   invariant-safe — it doesn't touch the live site or reach prod).
3. Ensure Node.js is on PATH: `export PATH="/c/Program Files/nodejs:$PATH"`.
4. **Draft deploy (default, no gate trip):**
   `npx -y netlify-cli deploy --cwd "C:/Users/Owner/website-canonical" --dir "C:/Users/Owner/website-canonical" --site 95ac0a0f-a84d-4400-b919-b8d7a8526646 --message "<branch@sha>"`
   Returns a `*.netlify.app` preview URL. Verify the change there —
   Claude_Browser or a manual click-through — before going further.
5. **Chat-regression gate (mandatory, every draft — no exceptions for
   "just a CSS fix"):**
   `node scripts/eval-chat.mjs --base=<draft-url>` from
   `C:/Users/Owner/website-canonical`, where `<draft-url>` is the
   `*.netlify.app` URL from step 4. This runs every fixture in
   `evals/fixtures.json` against the draft's `/api/chat` endpoint and
   writes `evals/results-<timestamp>.json`. Acceptance is the script's own
   exit code (0 = pass: ≥95% overall AND 100% on every `Refusal*`
   category) — trust the exit code, don't eyeball the printed
   percentages. On a nonzero exit: STOP. Do not proceed to step 6. Report
   the failing case IDs/categories from the `[acceptance]` summary line,
   then either fix the regression on the branch and redeploy a fresh
   draft (back to step 4), or surface the failure to Gabriel and wait —
   never ask for prod confirmation on a draft that failed its own
   regression gate, even if the failure looks unrelated to what the
   branch changed.
6. **Ask Gabriel explicitly**, naming the branch/commit, the eval-gate
   result (pass, with the pct), and exactly what will change on prod. Do
   not proceed without that confirmation, live, in this turn.
7. Only after confirmation: create the 60-minute override sentinel at
   `~/.claude/hooks/overrides/allow-website-change` (never self-create this
   in a scheduled/headless session — flag and stop instead), then run the
   same command with `--prod` appended. Delete the sentinel immediately
   after the deploy completes.
8. Post-verify: `curl -s -o /dev/null -w "%{http_code}" https://oxfordra.net/`
   expect 200; spot-check the changed page(s) in Chrome. If the change
   touched chat behavior, also run
   `node scripts/eval-chat.mjs` (no `--base`, defaults to prod) once the
   deploy is live, as a second confirmation the regression gate result
   still holds against prod itself.
9. Append the release to `memory/event_log.md` (target, what shipped,
   eval-gate result, verification result).

If the Netlify CLI reports 401/"could not retrieve project", the stored
token is stale — `npx netlify-cli login` (interactive OAuth; the user
approves in a browser tab) re-seeds it. Site ID `95ac0a0f-a84d-4400-b919-b8d7a8526646`
(prod name `snazzy-frangipane-de3841`) is fixed; never create a new site.

Full canon + gotchas: `memory/reference_oxfordra_deploy_canon.md` in the
ORA memory index.
