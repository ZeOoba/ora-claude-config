---
name: oxfordra-deploy-canon
description: Correct oxfordra.net deploy path (netlify-cli from website-canonical working tree) — the deploy-site skill / build-and-deploy.js / oxford-site copies are pre-redesign and DESTRUCTIVE
metadata: 
  node_type: memory
  type: reference
  originSessionId: ac8cd07a-65a5-4241-b6a5-8fc60c23a6ad
---

Verified 2026-07-09 while shipping fix/mobile-nav-overflow:

**Correct deploy path:** `npx netlify-cli deploy --cwd <repo> --dir <repo> --site 95ac0a0f-a84d-4400-b919-b8d7a8526646` from `C:/Users/Owner/website-canonical` (netlify.toml publish=".", `_headers`/`_redirects` in-tree, functions + edge function bundled). Omit `--prod` for a draft/preview URL (passes ora-autonomy-gate); `--prod` requires the §10 sentinel after Gabriel's per-deploy confirmation (Hard Invariant 2). Keep site-tree command strings free of `>` and other write-indicator substrings — including inside commit messages (`-F <file>` from scratchpad, never heredoc with `Co-Authored-By: <…>`); see [[autonomy-gate-blocks-writes-not-reads]].

**FIXED 2026-07-10.** The `deploy-site` skill's real source is `C:\Users\Owner\ora-skills\deploy-site\SKILL.md` (packaged into the Cowork-installed copy at an AppData runtime cache — editing the AppData copy directly does not stick; edit the ora-skills source and repackage via `package-and-stage-skill` if the Cowork install needs to pick it up). It now points at the netlify-cli-from-website-canonical procedure above, with a mandatory draft-then-ask-then-sentinel-then-prod sequence. `Claude_Workspace/01_Workspace/oxford-site/build-and-deploy.js` (the dangerous script the old skill invoked) now hard-stops on load (`process.exit(1)` unless `I_UNDERSTAND_THIS_IS_DEPRECATED=1`) — kept in place per the never-delete rule, not removed. Both edits required the `allow-website-change` sentinel (file path contains the `oxford-site` marker); created/removed same-session on Gabriel's live "fix this" naming this exact risk.

**Do NOT use (all pre-redesign, would corrupt the live BEM/SVG site if the guard is ever bypassed):**
- `build-and-deploy.js` — fetches the LIVE site, applies April-era regex "punch list" (hyphenated nav classes, PNG logo, /properties/* pages, an old CSP), and its `--deploy` goes straight to `--prod` with no preview.
- `C:/Users/Owner/oxford-site/` — stale April deploy copy, 5 of 13 pages.
- `oxford-site/.claude/CLAUDE.md` — points at the dead `(1)`-suffix OneDrive scope; its file map and "CSP in netlify.toml" claim are wrong (CSP lives in `_headers`). Not yet corrected — low-traffic file, flag if anyone actually reads it for guidance.

**Auth:** `netlify-token.dat` (Apr 25) is DEAD — API returns 401. CLI re-authed via `netlify login` OAuth on LAPTOP-CSHSCBE6 2026-07-09 (Gabriel clicked Authorize). For unattended/scheduled deploys, a fresh PAT must be minted at app.netlify.com and saved into `~/.claude/scheduled-tasks/_shared/netlify-token.dat` by Gabriel directly (file is UTF-16 — decode with python, not `cat`). Netlify projects: prod = `snazzy-frangipane-de3841` (oxfordra.net), plus separate `oxford-redesign-preview`.

**Publish-dir exposure — RESOLVED, merged + live 2026-07-10.** `fix/publish-dist-exclude-internal` merged as **PR #10** (16:41:49Z) and `chore/pin-netlify-cli` merged as **PR #11** (16:47:35Z) — both superseded the "awaiting merge" language below. `netlify.toml` on `main` now reads `publish = "dist"`, built by `scripts/build-dist.mjs` (fully-enumerated allowlist; unclassified root entries fail the build) — confirmed by direct read 2026-07-10. root-dir/`evals`/`scripts`/`netlify` source exposure is closed.

**⚠ Deploy-command change (now in effect):** the canonical command DROPS `--dir` — plain `npx netlify-cli deploy --cwd <repo> --site 95ac0a0f-a84d-4400-b919-b8d7a8526646` (CLI ≥ v17 runs the build automatically, assembling dist/). Passing `--dir <repo>` would bypass the build and re-publish the whole repo root — the exact leak this fixed. Same for `--prod`.

**⚠⚠ CRITICAL, newly confirmed 2026-07-10: merging a PR to `main` on GitHub IS a production deploy — no separate netlify-cli/manual step required.** Netlify's GitHub integration auto-builds and auto-publishes on push to `main` (site `snazzy-frangipane-de3841` / `95ac0a0f-a84d-4400-b919-b8d7a8526646`). Verified via the Netlify deploy record for PR #15's squash-merge (commit `966a8c8`): `context: "production"`, `url: "https://oxfordra.net"`, `deploy_source: "api"`, `manual_deploy: false`, published 13 seconds after the GitHub merge event. **This means Hard Invariant 2's "explicit per-deploy permission" gate has to be satisfied BEFORE merging any PR to `main` on this repo — the merge itself ships to production, regardless of whether anyone ever runs `netlify-cli deploy --prod`.** The draft/preview-then-ask-then-prod sequence described above only holds if the PR is merged after that confirmation, not before. Treat "merge this PR" on website-canonical as equivalent to "deploy to production" for gate purposes.

**Follow-up systematization, 2026-07-10 (built same day as the exposure fix):**
- **Weekly exposure probe:** scheduled task `ora-site-exposure-probe` (CC/MCP fleet, Wed 09:26 AM ET) curl-matrix-checks the internal paths above 404 + the `_headers` security-header set on prod; ggoldberg-only alarm email, silent when clean. Now that PR #10 is live, expect this to run clean — a future alarm would be a real regression, not the previously-expected known-open state.
- **netlify-cli pin:** shipped via PR #11 (above) — `npx netlify-cli` now resolves the local `node_modules` install instead of the npx cache.
- **Chat-eval draft gate:** `ora-skills/deploy-site/SKILL.md` (pushed to `ora-skills` main, 2 commits) adds a mandatory step: `node scripts/eval-chat.mjs --base=<draft-url>` runs after every draft deploy and blocks the prod-confirmation ask on a nonzero exit (below 95% overall or any Refusal-category miss).

**PR #11 briefly broke the build (2026-07-10, ~16:47–17:27Z):** it added root `package.json`/`package-lock.json` without updating `build-dist.mjs`'s `EXPECTED_EXCLUSIONS`, so the allowlist guard failed the build (exit 2) for ~40 min. Fixed by **PR #12** (`fix/build-dist-classify-package-files`, merged 17:27:16Z, squash commit `1bbfca2`) — classified all three (`package.json`, `package-lock.json`, `node_modules`) as excluded. A separate branch/worktree may still exist locally with the same pre-squash commit (different SHA, identical diff) — that content is **already shipped**; don't re-merge it as if it were still outstanding, and don't be confused when `git merge-base --is-ancestor` on the pre-squash SHA returns false against `main` (expected for any squash-merged branch).
Full detail: `event_log.md` 2026-07-10 "Publish-dir-exposure follow-up: 3 systematization candidates implemented".
