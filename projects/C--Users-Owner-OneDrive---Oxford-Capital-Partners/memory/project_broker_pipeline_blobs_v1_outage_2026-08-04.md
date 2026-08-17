---
name: project-broker-pipeline-blobs-v1-outage-2026-08-04
description: "oxfordra.net broker OM intake is BROKEN in production — legacy V1 functions can't auto-provision Netlify Blobs; no data lost, fix still open as of 2026-08-04"
metadata: 
  node_type: memory
  type: project
  originSessionId: 820589ed-6e68-4c48-93e7-3a609bab281e
  modified: 2026-08-16T20:14:35.817Z
---

**STATUS 2026-08-16: FULLY RESOLVED — VERIFIED END-TO-END WITH A REAL SUBMISSION.** A synthetic OM submitted through the live front door scored in **13 seconds** (20:13:05 submit → 20:13:18 "Deal Score Ready — 75/100" email to Gabriel+Eric). Gates PASS/PASS. Every stage produced its artifact: intake form, SharePoint filing, submission email, ledger form, score email.

**TWO fixes were required, in sequence — PR [#72](https://github.com/ZeOoba/Website/pull/72) alone was NOT enough:**
1. **#72** — V2 migration (Blobs auto-provisioning excludes legacy V1).
2. **#73** (`57ba84f`) — `broker-extraction.js` → `.mjs`. #72 REGRESSED this: under V1 Netlify shipped `node_modules` beside the function so `require('xlsx')` resolved; V2 bundles instead and xlsx/mammoth fell through → `Cannot find module 'xlsx'`, silent death at module load. Diagnosed from the live Netlify function log after bundle-size analysis (373KB shipped vs 3.1MB bundled locally) predicted it. Post-fix artifact is 1,585KB.

**Guard now in place:** `tests/functions/esm-cjs-bundling-contract.test.js` walks the ESM import graph from every `.mjs` function and fails if any reachable CommonJS module requires a bare package. Verified bidirectionally (fails on the pre-fix tree naming xlsx+mammoth). **This failure class cost TWO production round-trips and was invisible to all 130 local tests both times.**

**Key operational lesson:** a Netlify **background** function returns 202 *before* loading its module, so a module-load crash is unobservable from outside — no status code, no log, no artifact. Persistent `{"status":"pending"}` is the only symptom. Outside-in probes of `broker-score-status` do NOT cover the scorer.

**Also found:** reCAPTCHA is NOT enforced (`broker-upload-session.js` TODO, Gabriel-approved 2026-07-19 — Enterprise widget rejects real users with "Invalid site key", root cause still unknown). The rate-limit/daily-cap is now the ONLY backstop on paid Claude calls. **Do NOT blind-restore the enforcement line — it would 403 every real broker.** Verify the widget by screenshot first.

**Minor open (cosmetic):** `runScoring` reuses the `broker-network-ledger` form for its score entry, so each scored submission also generates a second, blank-looking form email.

---

**Superseded status line, 2026-08-16 (earlier in the same session): RESOLVED IN PRODUCTION.** PR [#72](https://github.com/ZeOoba/Website/pull/72) merged (squash `76a9d34`) and verified live on oxfordra.net. Path (b) chosen: V2 migration, no new credential.

Prod probe results (outside-in, the only trustworthy check here): unknown id → `200 {"status":"pending"}` (proves `getStore()` resolves); POST → `405`; missing id → `400`; forged token → `401` with no stack-trace leak; empty body → `401` not `400` (V1 semantics deliberately preserved); `broker-upload-session` (untouched V1) → `422`; homepage and `/for-brokers` → `200`. Content on main independently verified: all three functions `.mjs`, ESM store import, no orphaned V1 files. Full suite 126/126.

**Severity was overstated in the original note below.** OM intake is NOT dead: `broker-finalize` catches the Blobs failure AFTER filing to SharePoint and emailing Gabriel/Eric, so a submitting broker still reaches ORA. What was dead is the AI SCORING/triage layer and the broker-facing score. Lost automated triage, not lost deal flow.

**NEW second defect, found only by the outside-in probe (2026-08-16).** Migrating to V2 was necessary but not sufficient. `broker-score-store` was CommonJS; reached from an ESM (V2) entry, esbuild inlines the module but leaves its `require('@netlify/blobs')` as an unresolvable runtime call → `Cannot find module '@netlify/blobs'`, a 502 with a leaked stack trace (strictly WORSE than main). Fix: make the Blobs chain ESM (`broker-score-store.mjs`, `broker-scoring-run.mjs`) so esbuild bundles the dependency. **`external_node_modules = ["@netlify/blobs"]` was tried first and DID NOT WORK** — do not retry it. All 126 local tests passed through BOTH defects; only a real request against the deployed bundle caught either. This is the second same-day instance of local-green/prod-broken on this pipeline — the standing argument for out-of-band probes.

**Not yet verified even after merge:** the full scoring path (Graph download → LLM extraction → scoring engine → follow-up email). That needs a real OM submission; the probe only exercises transport + store.

---

**Original note, 2026-08-04 (severity since corrected above):** still broken in production. `/api/broker-score-status` returns 502 `MissingBlobsEnvironmentError` thrown at `getStore()` in `netlify/functions/_shared/broker-score-store.js:20`.

**Root cause.** All 7 oxfordra.net Netlify functions use the **legacy V1 signature** (`exports.handler = async (event, context)`, `event.httpMethod`, returning `{statusCode, body}`). Netlify's own coding-context doc states Blobs auto-provisioning does not cover V1 — they "require manual siteID/token configuration." Three functions call Blobs through that one shared module: `broker-finalize`, `broker-score-background`, `broker-score-status`. `broker-upload-session` does NOT (no blobs import), which is why step 1 of the pipeline still works.

**Not the whole story before this:** [PR #64](https://github.com/ZeOoba/Website/pull/64) (merged 2026-08-04) fixed two real, separate defects — a missing `_redirects` mapping for `/api/broker-score-status`, and an `ERR_REQUIRE_ESM` crash from `@netlify/blobs` 10.1.0 (bumped to 10.7.9). Those were genuine, but the ESM crash was *masking* this Blobs issue: a module-load crash meant `getStore()` was never reached. Fixing it revealed the deeper problem. Don't read PR #64 as "the broker pipeline is fixed."

**Zero data lost — verified, not assumed.** SharePoint `sites/WebsiteSubmissions/Shared Documents/Broker Submissions/` holds exactly 5 folders, all Oxford's own test runs (07-14 ×4, plus `2026-07-18_Oxford-Realty_7f06ce0e` at 17:39:43 which timestamp-matches the `broker-submission-intake` / `broker-network-ledger` entries — the ship-day verification run). No real broker has submitted since the feature went live. Because `broker-upload-session` creates the SharePoint folder *before* `broker-finalize` runs, any real attempt would have left a folder; there are none.

**The systemic lesson (bigger than this bug).** The `pipeline-failures` Netlify form — the failure log every function writes to — went silent after 2026-07-13 and stayed silent through the whole outage. A module-load crash happens before the handler's `catch` block exists, so the error reporting could never report its own outage. Client-side, `pollForScore()` in `broker-upload.js` wraps its fetch in a bare `.catch()` that retries for 2 minutes then degrades to a friendly "our team will review it directly" message. Both layers fail invisibly by construction. Any future health check for this pipeline must probe from *outside* (a real request against the live endpoint), never rely on the pipeline reporting itself. See [[feedback_verified_null_vs_inferred_null]] — a silent zero here meant "couldn't look," not "nothing wrong."

**Env vars VERIFIED 2026-08-04 (Netlify dashboard, read directly).** 15 exist: `ALERT_TO`, `ANTHROPIC_API_KEY`, `CHAT_MODEL`, `CHAT_RATE_LIMIT_PER_10MIN`, `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET`, `GRAPH_DRIVE_ID`, `GRAPH_SEND_FROM`, `GRAPH_SITE_ID`, `GRAPH_TENANT_ID`, `INTAKE_TOKEN_SECRET`, `NETLIFY_DATABASE_URL`, `NETLIFY_DATABASE_URL_UNPOOLED`, `NETLIFY_WEBHOOK_SECRET`, `RECAPTCHA_SECRET_KEY`. **There is NO `NETLIFY_SITE_ID` and NO Netlify API/auth token** — so fix path (a) is not a config-only change; it requires provisioning a brand-new Netlify PAT as a secret. ⚠️ `GRAPH_SITE_ID` is the **SharePoint** site id, NOT Netlify's — do not wire it into `getStore()`. Netlify site id is `95ac0a0f-a84d-4400-b919-b8d7a8526646` (project `snazzy-frangipane-de3841`).

**Open, needs Gabriel.** Three fix paths: (a) manual `siteID`/`token` on `getStore()` — smallest diff but needs a NEW Netlify PAT provisioned and rotated forever after; (b) migrate the three Blobs functions to the V2 signature so Blobs auto-provisions with **no secret at all** — larger change to live intake code, needs its own test pass, but adds no credential; (c) drop Blobs and use the **Neon Postgres already provisioned on this project** (`NETLIFY_DATABASE_URL`, created by the Neon extension — see the dashboard's Database nav item) — the store module is only ~7 small JSON-by-key functions with manual TTL, so this is tractable, though it's a database for a key-value need. **(b) looks best on the secret-management axis** — it's the only one that adds no new credential. Not decided; Gabriel's call.

**Inconclusive, do not treat as verified:** the dashboard's Blobs page rendered only a heading and description with no store list and no explicit empty state. That is consistent with "no store was ever created" (writes always failed) but is NOT proof — the list may simply not have rendered. Don't cite it either way.

Related: [[projects]] · [[rules]] (invariant 2 gates every write to this repo)
