---
name: command-center-gate-vs-gate-ci-divergence
description: "oxford-command-center's `npm run gate` and `npm run gate:ci` are NOT equivalent — gate:ci runs a production vite build + bundle check that gate skips entirely, so local `gate` runs can pass while CI's `gate:ci` fails"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 191a820d-64bc-4dd5-8c97-334b7d0f13ea
---

`package.json`'s two gate scripts diverge, not just in DB-dependent steps:

```
"gate":    "npm run governance && npm run typecheck && npm run lint && npm run test && npm run reconcile && npm run warehouse:verify && npm run warehouse:drift"
"gate:ci": "npm run typecheck && npm run lint && npm run test && npm run build && npm run check:bundle"
```

The obvious difference is `gate` needs a live DB/workbook (`reconcile`/`warehouse:verify`/`warehouse:drift`) that isolated worktrees don't have — so the established pattern all session has been "run `gate` minus the DB steps, document the gap as pre-existing/environment-only." That reasoning is wrong in one respect: `gate:ci` doesn't just drop those three steps, it **substitutes `npm run build` + `npm run check:bundle`** — a real production `vite build`, which `gate` never runs at all.

**Why: production build passed through a different, stricter code path.** `vite-plugin-pwa`'s CSS asset processing failed with "Unterminated string" on apostrophes inside `/* */` comments in `src/tokens/theme.css` (e.g. `warm's --text-on-accent`, `theme's near-white surfaces`) — a genuine build-breaking bug that `npm run typecheck`, `npm run lint`, and the full `npm run test` suite (Vitest, jsdom, PostCSS-via-Tailwind at dev/test time) never touch, because none of them run the same CSS parser the production build's PWA plugin does. Confirmed reproducible locally with `npm run build` alone once informed to try it — CI's failure (`gate` check on the PR) was the first signal, not any local command.

**How to apply going forward:** on this repo, before opening/updating a PR, run `npm run gate:ci` locally (not `npm run gate` minus the DB steps) — or at minimum add a bare `npm run build` to whatever "local gate substitute" checklist gets used for worktrees without DB access. Never write CSS comments (or any generated-content strings) containing an apostrophe/contraction on this repo without testing a real build first; this bug class won't surface in typecheck/lint/test.

Related: [Command Center CRLF Hazard](reference_command_center_crlf_hazard.md) — another category of "passes locally, breaks in a way normal dev commands don't catch" gotcha specific to this repo's build tooling.
