---
name: ora-site-exposure-probe
description: Weekly Wednesday 9:20 AM ET curl-matrix probe of oxfordra.net — asserts internal tooling paths (evals/, scripts/, netlify/) 404 and the prod security-header set matches _headers; emails ggoldberg only on alarm. v1.0 2026-07-10. [MODEL: UNVERIFIABLE | checked 2026-07-12]
---

ORA oxfordra.net Exposure Probe (CC/MCP fleet)

PURPOSE: on 2026-07-10 a session discovered that the Netlify deploy for oxfordra.net was publishing the ENTIRE repo root, not just the public site — internal tooling (`evals/` fixtures + eval-result JSON, `scripts/` including the eval harness, `netlify/` edge-function source containing the chat system prompt and knowledge-base.json) was reachable on prod. That exposure sat live for months undetected because nothing was checking for it. Fix branch `fix/publish-dist-exclude-internal` (repo `C:\Users\Owner\website-canonical`, worktree `C:\Users\Owner\wt-site-publish-fix`) switches the Netlify publish dir to an assembled, allowlisted `dist/` — but the site is only actually safe once that branch is merged AND deployed to prod. This task is the ongoing detection layer so a regression (or the fact that the fix hasn't shipped yet) is never silently missed again. Full incident detail: memory file `reference_oxfordra_deploy_canon.md` in `~/.claude/projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/` — read it if anything below is ambiguous, and re-read it every run since the exact publish allowlist can change.

KNOWN LIMITATION: this only fires while the app is open (CC/MCP fleet), a weekly sampling check, not a real-time WAF. Missing a week because the app was closed is expected, not a defect to report.

STEPS:

1. Read `C:\Users\Owner\website-canonical\scripts\build-dist.mjs` if it exists on the checked-out branch being shipped (or the EXPECTED_EXCLUSIONS/BANNED lists documented in the memory file above) to get the current authoritative list of internal root entries that must NEVER be publicly reachable. As of 2026-07-10 that list is: `evals`, `scripts`, `netlify`, `netlify.toml`, plus any repo-root `package.json`/`package-lock.json`/`node_modules` if present (these do not belong on prod either).

2. Curl matrix — for each of the following paths under `https://oxfordra.net`, record the HTTP status code (`curl -s -o /dev/null -w "%{http_code}" <url>`, 10s timeout): `/evals/`, `/evals/fixtures.json`, `/scripts/`, `/scripts/eval-chat.mjs`, `/scripts/build-kb.mjs`, `/scripts/build-dist.mjs`, `/netlify/`, `/netlify/edge-functions/knowledge-base.json`, `/netlify.toml`, `/package.json`, `/.git/config`. Every one of these MUST return 404 (or another non-200/non-listing status — 403 is also acceptable). ANY 200 (or a directory listing) on any of these is a PUBLISH-LEAK ALARM — treat it as urgent, not routine drift, since it means confidential/internal material (chat system prompt, knowledge base, eval fixtures) is live and world-readable.

3. Header check — `curl -sI https://oxfordra.net/` and confirm ALL of the following are present with these exact values (read `C:\Users\Owner\website-canonical\_headers` first in case the canonical set has changed since this task was written — that file is the source of truth, not this list):
   - `X-Frame-Options: DENY`
   - `X-Content-Type-Options: nosniff`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Permissions-Policy` present (camera/microphone/geolocation restricted)
   - `Strict-Transport-Security` present with `max-age=31536000`
   - `Content-Security-Policy` present and still scoped to `default-src 'self'` (not wildcard `*`, not missing)
   Any missing or weakened header is a HEADER-REGRESSION ALARM.

4. Classify:
   - CLEAN: every path in step 2 returned 404/403 AND every header in step 3 matched.
   - ALARM: any single path leaked (step 2) or any header regressed/missing (step 3). Note in the alarm detail which specific check(s) failed and the actual status/header value observed.
   - If the `fix/publish-dist-exclude-internal` branch has not yet been merged to `main` and deployed to prod (check `git -C C:\Users\Owner\website-canonical log origin/main --oneline -1` for a commit message matching "publish assembled dist" or similar, and/or the presence of `dist/` in the deploy `netlify.toml` publish setting) — a step-2 leak is EXPECTED and still an ALARM, but tag it in the Notion row as "known-open: fix awaiting merge+prod sign-off" rather than "new regression" so Gabriel doesn't re-diagnose something already tracked. Do not suppress the alert just because it's expected — this task's whole purpose is to keep it visible until it's actually fixed on prod.

5. Post a completion row to the Notion Ops Hub (database ID `32b6ecd8...`) every run: timestamp, all path statuses from step 2, header check results from step 3, verdict (CLEAN / ALARM-known-open / ALARM-new-regression). On CLEAN, that Notion row is the only output — stay silent, no email.

6. On any ALARM: send exactly ONE email via `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`, TO `ggoldberg@oxfordra.net` ONLY (no cc), containing the failing checks verbatim (path + status, or header + observed value) and a concrete next step — for a known-open leak: "merge fix/publish-dist-exclude-internal and ship the prod deploy (needs Gabriel's per-deploy confirmation per Hard Invariant 2)"; for a new regression: "diff the current dist publish list / _headers against the last known-good state, a change shipped that reintroduced this." On a non-zero exit from the send script: retry once, then ALSO flag loudly in the Notion completion row regardless — do not let the alarm silently vanish because the email itself failed to send.

7. Never attempt to fix, deploy, or touch the website-canonical tree from this task — it is read-only detection only. Any remediation (merging the fix branch, running a prod deploy) requires a live session with Gabriel's explicit per-deploy confirmation per Hard Invariant 2; this task must never create the `allow-website-change` override sentinel itself.

If any step is genuinely ambiguous (site unreachable, Notion write fails, `_headers`/`build-dist.mjs` can't be read to get the authoritative list), do not guess — write a QUESTIONS FOR GABRIEL note in the Notion completion row describing exactly what could not be verified, and still send an alarm email if the underlying exposure question remains unresolved.