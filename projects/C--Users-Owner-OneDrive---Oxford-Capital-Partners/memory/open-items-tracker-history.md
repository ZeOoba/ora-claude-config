---
name: open-items-tracker-history
description: "Companion to open-items-tracker.md — permanent archive of CLOSED items (table + detail sections), split out 2026-09-06 per Automation Audit R22-4 when the live tracker hit 901KB with no archive-out path. Same OI-NNN anchors as before, now at open-items-tracker-history.md#OI-NNN."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 8b8f8541-fc77-4ecd-ac4d-3074dc440ad1
  modified: 2026-09-12T22:03:03.510Z
---

> **Companion file to [open-items-tracker.md](open-items-tracker.md).** Holds every CLOSED item's table row and `### OI-NNN` detail section, split out 2026-09-06 (Automation Audit R22-4) when the live tracker reached 901,718B with no archive-out path for closed material. Append-only, same rules as `event_log.md` and this repo's other `*-history.md` companions — never edit or remove an entry once archived (Invariant 6). Anchors are unchanged in form: a reference that used to read `open-items-tracker.md#OI-NNN` for a CLOSED item now reads `open-items-tracker-history.md#OI-NNN`.

## Closed

Table and detail sections below, in the order they sat in the original file at split time (not re-sorted by id) — a detail section can precede or follow the table depending on when it was originally filed, since the source file's own convention only ever required moving the table ROW on closure, not its section.

### OI-288
**Status:** CLOSED
**Opened:** 2026-09-12
**Closed:** 2026-09-30
**See:** the `## Closed` table above; full write-up also in [[reference_notion_free_block_quota_exhausted_2026-09-12]].

### OI-157
**Status:** CLOSED
**Opened:** 2026-08-15
**Closed:** 2026-08-15
**Source:** [project_automation_audit_rev10_2026-08-14.md](project_automation_audit_rev10_2026-08-14.md) R10-12; investigated in `~/ora-skills/.superpowers/sdd/task-6-report.md`; ruling made in-session 2026-08-15; row lost to merge-conflict resolution and re-filed 2026-08-15/16 (this session) — see [OI-160](#OI-160)
**Description:** `capex-budgeting` was accidentally republished to the Cowork skill store 2026-08-13 (a batch Save-skill click clearing an unrelated PENDING_REIMPORT queue caused a new registration, `main.log` enabled count 51→52) — 4 days after Gabriel confirmed it unpublished 2026-08-09 alongside 5 sibling skills (`annual-cycle`, `cash-position-monitor`, `deal-retirement`, `investor-relations`, `vendor-management`, all confirmed still absent from the live catalog, consistent with remaining correctly unpublished). Gabriel ruled 2026-08-15: accidental, unpublish it again.
**Evidence:** Filed in commit `7c9740a` (2026-08-15 14:43:31 -0400). Per `event_log.md` (2026-08-15): Gabriel first toggled Share off via the claude.ai Skills page (verified persisted after navigating away and back), then — noting capex-budgeting still appeared in the account's "your skills" search unlike the fully-removed 5 siblings — escalated via the overflow menu's **Remove** action ("Remove skill? You can always add this skill again later by re-uploading it" — confirmed reversible, not destructive data loss). Confirmed removal via a follow-up search: "capex-budgeting" → "No skills match your search", matching the other 5 unpublish-siblings exactly. The tracker row itself was independently confirmed lost from this file during two same-day merges before it could ever be formally closed (see [OI-160](#OI-160)) — re-filed directly as CLOSED now that the underlying real-world action is independently verified done.

### OI-162
**Status:** CLOSED 2026-08-21 — daily half FIXED 2026-08-16, monthly half registered 2026-08-21, both live
**Opened:** 2026-08-16
**Source:** Cross-repo architecture-diagram review (Gabriel-directed, this session) — `ora-pm/README.md` "Architecture" diagram + "Setup & Run" section
**Description:** **MEDIUM** ora-pm's three cron jobs (`monthly-billing`, `critical-dates-alerts`, `delinquency-check`) have no native Cloudflare Pages trigger, so they're driven by two standalone Windows Task Scheduler entries — `scripts/trigger-billing.ps1` (1st of month) and a separate "ORA PM Crons" task running `C:\Users\Owner\ora-pm-cron\ping-crons.ps1` (daily 9am). The README states plainly this second task is "not part of the ORA fleet/`create_scheduled_task` registry." `automation-health-monitor`'s own trigger description scopes it to "the live dual-fleet scheduled-task registries (CC/MCP + LAMS/Cowork)" via `list_scheduled_tasks` — neither of these two ora-pm tasks lives in either registry, so they are structurally invisible to the one system that exists to catch a silently-stopped automation. Stakes are non-trivial: `monthly-billing` confirms off-session ACH PaymentIntents portfolio-wide, and since OI-047 removed direct email from the Worker, `ping-crons.ps1` is the *sole* delivery path (via Outlook COM) for the critical-dates and delinquency digests — if that task stops firing, both the money-movement job and the human-visible alerting for it go dark with no monitoring signal.
**Fix direction:** register both tasks through `register-scheduled-task`/`create_scheduled_task` so they land in an audited registry, or (if that path can't reach a non-ORA-fleet Windows box) build an ora-pm-specific equivalent of `automation-health-monitor` that checks these two tasks' last-run evidence directly.
**Progress 2026-08-16 (this session):** Registered `ora-pm-daily-crons` in the CC/MCP fleet (`0 9 * * *`, invokes the existing `ping-crons.ps1` verbatim rather than re-implementing it) and disabled the standalone "ORA PM Crons" Windows task so there is exactly one trigger, not two racing at 9am. Verified via `list_scheduled_tasks` (`cronExpression: "0 9 * * *"`, `nextRunAt: 2026-08-17T13:06:31Z`, ~20h out — passes the step-4c sanity check). **Two things surfaced doing this, both still open, full detail in [event_log.md 2026-08-16](event_log.md#2026-08-16):**
1. **The old "ORA PM Crons" task had already been failing since 2026-08-15** — `cron.log`'s last real entry is 08-14; today's `LastRunTime` shows a non-9am timestamp with `LastTaskResult 0x8007042B` and zero log output, meaning it errored before its own logging code ran. `ping-crons.ps1 -SelfTest` passes 12/12 interactively, so this is an execution-context failure (Interactive-logon principal), not a script-logic bug. Root cause not diagnosed. Two days of alert/delinquency pings were silently missed — the new fleet task should fix reliability going forward (fleet tasks already run unattended reliably elsewhere), but the miss itself is not backfilled.
2. **`trigger-billing.ps1` (monthly ACH billing) has no scheduler trigger anywhere on this machine at all** — not a fleet-visibility gap but an apparent total absence of automation, contradicting the README's "Setup & Run" table. `ORA_PM_CRON_SECRET` is unset at both Machine and User env scope. Unverified whether Gabriel runs this by hand monthly or it simply hasn't been running. **Deliberately NOT registered as a new fleet cron** — creating new unattended ACH-charging automation is a bigger decision than fixing visibility for something already running, and needs Gabriel's explicit confirmation first (how it's been triggered to date, and whether to automate it now). This is why OI-162 stays OPEN rather than closing.

**Progress 2026-08-16 (later same session) — monthly-billing batching fix, five adversarial review rounds:** Gabriel confirmed billing has genuinely never run (verified directly against the `charges` table — 0 of 59 rows were rent/CAM, only opening-balance seed + late fees). First real trigger (August, current month only per Gabriel's call) hit Cloudflare Workers' subrequest limit — 49 of 139 leases billed, 90 got nothing (clean failure, no duplicates). Gabriel approved building the batching fix. Full five-round history: [event_log.md 2026-08-16 "OI-162 monthly-billing batching fix"](event_log.md#2026-08-16) — rounds 1-3 fixed the original O(leases) subrequest bug and its first relocation into the autopay debit loop; **round 4 found and fixed a genuine convergence/deadlock bug** (batch-limiting before computing which leases needed a debit let already-paid leases starve leases that actually owed money, reproduced empirically); round 5 confirmed round 4 converges and found the same failure *class* recurring via deterministically-failing Stripe calls (mitigated client-side — the drain loop now breaks loudly instead of silently exhausting its retry budget — not fixed server-side; needs failure-aware lease ordering as a future item) plus a charges-bulk-failure gap (autopay was still running against known-bad charge data). 464/464 tests pass, typecheck/lint clean. **Not deployed** — held for Gabriel per standing commit convention. **OI-162 daily half CLOSED; monthly-billing automation decision (register vs. hand-trigger) still OPEN**, and now a code-readiness question too, not just a scheduling one.

**Progress 2026-08-21 (repo-architecture-review remediation session) — monthly trigger registered, CLOSED:** by action time the batching fix (`fa67f21`) had already been pushed to `origin/main` and deployed — `gh run view` on the 2026-08-16 CI run confirmed the "Deploy to Cloudflare Pages" step succeeded, so the "Not deployed" note above was stale by 5 days when this session picked it up. Gabriel approved registering the trigger. Discovered `CRON_SECRET` already existed as a Cloudflare Pages encrypted secret with no known local consumer for the billing path (`ORA_PM_CRON_SECRET` unset) — rotated it, assuming nothing depended on the old value. **Near-miss, caught same-session:** `cronAuthMiddleware` guards ALL `/api/cron/*` routes with one shared `CRON_SECRET`, and `ora-pm-daily-crons` (live, working) reads the SAME secret from a different file, `C:\Users\Owner\ora-pm-cron\cron-secret.txt` — the rotation would have broken tomorrow's 9:40 AM daily cron had it not been caught. Fixed in the same pass: `cron-secret.txt` updated to the new value before the daily cron's next scheduled fire, no gap. Registered `ora-pm-monthly-billing` (CC/MCP, `10 11 1 * *`, next fire Tue Sep 1) via `create_scheduled_task`, invoking the existing `trigger-billing.ps1` unmodified. Not test-fired — no dry-run mode exists and it would charge real tenants; first real exercise is the Sep 1 run. **OI-162 fully CLOSED.**

### OI-015
**Status:** CLOSED — verified clean, no purge needed
**Opened:** 2026-07-18
**Closed:** 2026-07-19
**Source:** ora-appsec-sweep first run (2026-07-18, manual + supervised); Notion Ops Hub row `3a26ecd8-9e59-81e4-85d4-d08d0d5d920b`
**Original finding (superseded, see Evidence below):** the sweep + fix-commit `866480f`'s own note
both claimed real E. Fulton `CONFIDENTIAL_TERMS` tokens (committed to `.env.example` at `c4c69a8`,
2026-06-06) were "still in git history ... on the remote until a separate history purge is run."
**Evidence (2026-07-19):** a completely fresh clone directly from `github.com/ZeOoba/ora-pm` (bypassing
any local object cache) shows commit `c4c69a8` already contains only placeholders
(`example-term,another-example,third-example`), and `git log -p --all` across every reachable commit
and branch in that fresh clone returns zero matches for any real term variant. **The reachable,
clonable, browsable history is genuinely clean — no history rewrite/force-push was needed or performed.**
The original finding was based on a stale signal: a local dangling/unreachable blob
(`39b02f4585cc6357876423d04d5c3fcee65793b0`) that was mistaken for "still in history" — it was never
part of any current ref and has since been pruned locally. **No purge action was taken; none was needed.**
**Residual (tracked separately, see OI-022):** that same blob IS still directly retrievable via GitHub's
Git Data API (confirmed: `gh api repos/ZeOoba/ora-pm/git/blobs/39b02f45...` returns its content), because
it's kept alive server-side by `refs/pull/2/head` (PR #2's GitHub-managed ref, which cannot be deleted
via git push, the repo API, or repo settings — this is a documented GitHub platform limitation, not a
per-repo config issue). This is a distinct problem from "is it in the history anyone would ever see" —
it requires a GitHub Support request, not a git operation. Spun off as OI-022.
**Auto-check:** none.

### OI-016
**Status:** CLOSED
**Opened:** 2026-07-18
**Closed:** 2026-07-19
**Source:** ora-appsec-sweep first run (2026-07-18); Notion Ops Hub row `3a26ecd8-9e59-81e4-85d4-d08d0d5d920b`
**Description:** ora-pm (pinned SHA `f47bbe0`) depended directly on `hono` <=4.12.24, which carried HIGH
advisories: path-traversal via encoded backslash `%5C` on Windows (not reachable — the app runs on the
Cloudflare Workers Linux edge), CORS middleware reflecting any Origin with credentials when `origin`
defaults to wildcard, and AWS-Lambda-adapter Set-Cookie merging. Effective severity MEDIUM: portal auth
is Bearer-token (Authorization header), not cookie-based, which limits the CORS-credential vector.
**Evidence:** `hono` bumped 4.12.23→4.12.31, commit `c300867` on `main` (landed by Gabriel directly).
Verified via `npm audit` — the finding no longer appears.
**Auto-check:** none.

### OI-017
**Status:** CLOSED
**Opened:** 2026-07-18
**Source:** ora-appsec-sweep first run (2026-07-18); Notion Ops Hub row `3a26ecd8-9e59-81e4-85d4-d08d0d5d920b`
**Description:** Build/test/deploy toolchain CVEs in both repos, none reachable from a production, tenant,
or public request path. ora-pm (SHA `f47bbe0`): vitest CRITICAL (UI-server arbitrary file read/exec — only
when the Vitest UI server is listening, i.e. local dev/test), plus vite/esbuild/wrangler/ws/undici
HIGH/MOD. oxford-command-center (SHA `306a67f`): concurrently→shell-quote CRITICAL (dev script runner),
vitest CRITICAL, @huggingface/transformers→onnxruntime-node→adm-zip HIGH (crafted-ZIP 4GB DoS; only the
localhost-only brain server, reachable only on untrusted ZIP input), exceljs→uuid MOD. All fixes are
semver-major. Effective operational risk LOW; tracked for a batched toolchain-bump pass, not urgent.
**Progress 2026-07-19:** rather than the flagged semver-major top-level bumps, used targeted `overrides`
on the specific vulnerable transitive packages only (adm-zip/uuid/esbuild in oxford-command-center,
esbuild/undici/ws in ora-pm) — resolves 11 of 13 originally-flagged CVE instances with zero top-level
version changes. Both verified: full `gate:ci` green in oxford-command-center (typecheck/lint/test/
build/bundle-budget); `tsc --noEmit` clean + 185/185 tests in ora-pm. PRs: `ZeOoba/oxford-command-center#220`,
`ZeOoba/ora-pm#5` (neither merged yet — pending review).
**Residual, not fixed:** in both repos, `vitest@2.x`'s own internally-bundled `vite@5.x` (via `vite-node`)
still carries 3 CVEs (path traversal, NTLM hash disclosure on Windows, `fs.deny` bypass on Windows). A
scoped override forcing `vite@6.x` under `vitest` specifically was attempted in both repos and rejected
by npm as an invalid tree — `vitest@2.x` doesn't tolerate `vite@6.x` internally. The only real fix is
`vitest` 2.x→4.1.10 (semver-major), which needs its own dedicated cross-repo compatibility pass. Still
dev-server-only, never reachable from production — kept LOW effective severity, still not urgent.
**Progress 2026-07-19 (later): ora-pm side FULLY resolved.** Bumped `vitest` 2.x→4.1.10 (added to PR #5) —
clean migration, no config changes needed, `tsc --noEmit` clean, 185/185 tests unchanged, `npm audit`
now 0 vulnerabilities (was 9 at OI-017's opening). **oxford-command-center side attempted, reverted.**
The same bump surfaced a systemic incompatibility, not contained to one file: 24 of 41 tests in
`tests/unit/governance-check.test.ts` failed across nearly every describe block, tracing to
`vi.mock('node:fs')` automocking no longer producing usable mock functions under vitest 4. An explicit
factory-function mock fixed the crash but surfaced a second-order issue — mocks set via a helper
function (vs. inline in the test body) silently failed to reach the module under test. Given this
repo's 2828 tests cover live financial-data reconciliation (NOI, capital allocation, warehouse sync),
reverted rather than force an incompletely-understood mocking regression through; PR #220 stays scoped
to its original, already-verified overrides-only fix. oxford-command-center's 3 residual CVEs need a
dedicated vitest-4 migration pass across the whole test suite's mocking patterns — real follow-up work,
not a drive-by fix. ora-pm: fully closed (0 vulnerabilities). oxford-command-center: 3 residual, LOW
effective severity, not urgent.
**Refresh 2026-07-22 (ora-appsec-sweep weekly, SHAs ora-pm `1b304e8` / occ `85d3151`):** re-verified via
`npm audit`. **ora-pm no longer 0-vulns** — 2 new HIGH surfaced: `wrangler@3.114.17`→`sharp@0.33.5`→
libvips (CVE-2026-33327/33328/35590/35591), published after the 07-19 close. Fix requires `wrangler`
>4.16.1 (semver-major); sharp is not directly overridable to a patched libvips. Deploy/build tooling
only — never in the Cloudflare Workers request path. Not urgent, batch with the next wrangler bump.
**occ residual confirmed still open (9 advisories total: 1 CRIT / 6 HIGH / 2 MOD):** the vitest→vite
chain (vitest CRITICAL UI-server file-read/exec + vite path-traversal / NTLM-disclosure / `fs.deny`-bypass
HIGH) is the same vitest-4 migration blocker documented above; plus js-yaml / brace-expansion / fast-uri
HIGH (transitive, DoS/host-confusion, `fixAvailable`) and `@huggingface/transformers`→sharp/libvips HIGH
(**no fix available yet** — monitor). All bounded by occ's localhost-only (`127.0.0.1`) bind; none
tenant- or network-reachable. No new OI opened — same repo+check bucket as this item.
**Progress 2026-07-26: ora-pm wrangler/sharp side RESOLVED — PR `ZeOoba/ora-pm#7` open, awaiting
Gabriel's merge.** On arrival, verified reality first: PR #5 (overrides + vitest 4.1.10) and #6
(undici 7.28.0 downgrade) both already MERGED, main at `809fbe3`, tree clean — the wrangler bump was
genuinely new work, done in an isolated worktree (`../ora-pm-oi017-wrangler`, branch
`fix/oi-017-wrangler-bump`), main checkout untouched. Bumped `wrangler` ^3.78.0 (3.114.17) →
^4.114.0; miniflare 4 pulls **sharp 0.35.2** (patched — advisory range <0.35.0), clearing all 4
libvips CVEs (2026-33327/33328/35590/35591). Two knock-ons handled: `@cloudflare/workers-types`
^4→^5.20260722.1 (wrangler 4 peerOptional hard-fails npm resolution on v4; typecheck clean against
v5) and the `esbuild ^0.25.0` override REMOVED — it existed solely to lift wrangler 3's pinned
esbuild 0.17.19 past its CVE (#5's fix); wrangler 4 pins its own 0.28.1 and vite resolves 0.25.12,
so no consumer <0.25 remains (verified via `npm ls esbuild`). undici/ws overrides kept as-is
(deploy-safe pin from #6; miniflare 4 resolves undici 7.29.0 / ws 8.21.1 under them).
**Audit evidence:** baseline at `809fbe3` was actually **5 vulns (3 HIGH / 2 MOD)**, not the sweep's
2 — two NEW advisories published since 07-22: postcss ≤8.5.17 HIGH (GHSA-r28c-9q8g-f849, vite
transitive) and react-router 6.0.0–7.17.0 MOD ×2 (GHSA-wrjc-x8rr-h8h6 open redirect +
GHSA-337j-9hxr-rhxg SSR hydration). postcss fixed in the same PR via in-range lockfile refresh
8.5.15→8.5.23 (no package.json change). **After: 2 MOD** (react-router only).
**Verification (all in the worktree, wrangler 4 tree):** `tsc --noEmit` clean · 185/185 tests
(32 files, vitest 4.1.10 — matches last known-good) · vite production build green · `npx wrangler
pages functions build` compiles the `functions/` worker under 4.114.0 (closest local proxy for the
CI `pages deploy` step, chosen deliberately given #6's undici-broke-deploy history). `wrangler.toml`
needs no changes. Flagged in the PR: first wrangler-4 deploy fires on merge (CI deploys main to
Cloudflare Pages) — watch that Actions step.
**Residuals, item stays OPEN:** (1) react-router 6.x MOD ×2 — prod dependency of the tenant portal,
real fix is semver-major 6→7, needs its own pass (SSR-hydration advisory not applicable, app is
client-rendered; open redirect is the live one, MOD); (2) oxford-command-center's 9 advisories —
unchanged, still blocked on the dedicated vitest-4 mocking-migration pass documented above, NOT
touched this session (out of scope).
**Progress 2026-07-26 (later): occ vitest-4 blocker ROOT-CAUSED and fixed in a branch — ready to ship
pending REFUTE pass, deliberately NOT merged.** L5 investigation in isolated worktree
`../oxford-command-center-oi017-vitest4-investigation`, branch `investigate/oi017-vitest4-migration`
(PUSHED to origin, commit `a7a5ad7` on base `ac34d88`). The 07-19 "systemic mocking regression" was
neither systemic nor a mocking regression: under vitest 4, `vi.mock()` of Node builtins (`node:fs`)
is a **silent no-op in the jsdom environment** (this repo's global default) — the module under test
receives the REAL fs, so mocks never intercept. Isolated by controlled experiment: same test, same
setup file, both pools (forks/threads) — `--environment=node` works (both `fs` and `node:fs`
namespaces become mocks), jsdom never does; even `{ spy: true }` and factory variants no-op under
jsdom. This retroactively explains BOTH 07-19 symptoms: "automock produces unusable mock functions"
(the exports were the real, un-mockable fs functions → `mockReturnValue is not a function`) and
"helper-set mocks silently not reaching the module under test" (they were set on mock objects the
real-fs-importing module never saw — never a hoisting/helper-timing issue). Entire fix: bump
vitest+@vitest/coverage-v8 to 4.1.10 and add `// @vitest-environment node` to
`tests/unit/governance-check.test.ts` (a pure Node-script test where jsdom was wrong anyway) —
zero mock restructuring, 5 lines + deps. governance-check.test.ts is the ONLY builtin-mocking test
file in the repo (verified by grep; the other 13 `vi.mock` users mock local modules and are
unaffected). **Evidence:** baseline 41/41 green under v2 at `ac34d88` → 41/41 fail under 4.1.10
unpatched (same TypeError as 07-19) → 41/41 green with pragma; **full suite 244 files / 3101 tests
green** (suite grew from 2828 since 07-19); tsc clean · eslint clean · check:dev-css clean · vite
build green · bundle budget green. Two failures appeared once under a concurrent-load gate run
(capital-allocation-api `beforeAll` 10s import timeout; bash-guard perf assertion 2009 ms vs 2000 ms
— a 9 ms miss) and both re-ran green in isolation: load flakes, not vitest-4 regressions.
**Security effect:** `npm audit` in the branch: vitest CRITICAL + all 3 vitest→vite HIGHs GONE, 0
criticals remain. Remaining 9 advisories are UNRELATED chains: brace-expansion/fast-uri/js-yaml/
postcss (all `fixAvailable` via plain `npm audit fix`), react-router MOD ×2 + @hono/node-server MOD
(semver-major), sharp/libvips HIGH (no fix — monitor). **Decision: small, well-understood,
safely-shippable — but per doctrine this is financial-decision-repo test infrastructure, so it needs
the mandatory adversarial REFUTE pass before merge; not merged by the investigating session. Next
step: REFUTE pass on branch `investigate/oi017-vitest4-migration`, then PR + merge, then a plain
`npm audit fix` pass for the 4 non-breaking advisories.** Item stays OPEN.
**Progress 2026-07-26 (later still): ora-pm react-router residual RESOLVED-pending-merge — PR
`ZeOoba/ora-pm#9` open, awaiting Gabriel's merge. DECISION: proceed now, but to v8.3.0, not v7.**
L5 investigation in isolated worktree (`../ora-pm-oi017-rr7-investigation`, branch
`investigate/oi017-react-router-7`, base `92b4b45` = merged #7; main untouched). Baseline
re-verified first: tsc clean, 185/185, `npm audit` 2 MOD. Why not v7 (every option tested
empirically in the worktree, not guessed): HEAD's lockfile already resolves ^6.26.0 to **6.30.4**
(latest 6.x) — still flagged, no in-range escape; the 2 MOD advisories are patched only at ≥7.17.1;
but react-router ≥7.12.0 carries **GHSA-qwww-vcr4-c8h2** (HIGH, RSC-mode CSRF, published 07-24,
patched ONLY in react-router@8.3.0 per the GitHub advisory API — and never in any react-router-dom
release, since that package was removed in v8). Installing react-router-dom@7.18.1 was tried:
audit trades 2 MOD for 2 HIGH. v8.3.0 is the only 0-findings endpoint. The HIGH is inapplicable
here ("only affects... unstable RSC APIs" — ora-pm has no RSC/SSR/loaders/actions), but the
dashboard fix and the real fix coincide at v8. Migration cost trivial by construction (context7
v7/v8 upgrade docs + code recon): no `future` flags anywhere, all `Link`/`navigate` targets
absolute (v7_relativeSplatPath flip has nothing to bite), so the whole diff is imports —
`'react-router-dom'`→`'react-router'` in 20 files + `RouterProvider` from `'react-router/dom'`
(22 files, 39+/53−, zero behavior lines). **Evidence on the final tree:** tsc clean · 185/185
(vitest 4.1.10) · vite prod build green · `wrangler pages functions build` compiles (functions/
has zero react-router usage) · `npm audit` **0 vulnerabilities** · browser smoke on the built app:
`/login` renders identical to the v6 baseline, zero console errors. Worktree removed after push;
branch lives locally + on origin; PR #9 notes the first v8 deploy fires on merge (watch the Pages
Action, per #7 precedent).
**NEW DEFECT FOUND (separate follow-up, NOT caused by the bump): the tenant portal is blank in
PRODUCTION today.** `https://ora-pm.pages.dev/portal/login` renders an empty `#root` — reproduced
identically on v6 local build, v8 local build, and live prod (admin `/login` renders fine, so not
env-specific). Root cause: descendant `<Routes>` in `src/portal/PortalRouter.tsx` use absolute
`/portal/...` paths that can never match the splat remainder under the `/portal/*` parent, so the
subtree renders null with no console error; the 185-test suite never renders the router, so nothing
caught it. Spawned as its own task chip (fix relative paths + add a router-rendering test).
Tenant-payment revenue path — high priority. Item stays OPEN: ora-pm PR #9 unmerged; portal
blank-render defect open; occ side per the block above.
**Progress 2026-07-26 (REFUTE pass): occ vitest-4 fix CONFIRMED SAFE — PR
`ZeOoba/oxford-command-center#238` open, awaiting Gabriel's merge.** Independent adversarial REFUTE
pass (reviewer did not write the fix) actively tried to break `investigate/oi017-vitest4-migration`
and failed on every axis. (1) **Rebased** onto current main `f511d5f` (clean, `a7a5ad7`→`99a63e9`;
main had grown 19 new brain/anomaly-floor tests written under vitest 2) and re-ran everything fresh:
**245 files / 3120 tests, 3119 green**; sole failure was bash-guard's wall-clock perf assertion
(3464 ms vs 2000 ms) — the same pre-existing load flake `f511d5f`'s own commit message documents
under vitest 2; 68/68 green in isolation, exit 0. typecheck 0 · lint 0 · vite build green · bundle
budget green (entry 92.5 kB < 250 kB). (2) **jsdom-masking refuted:** `scripts/governance-check.ts`
imports only `node:fs`+`node:path`, zero DOM references in 481 lines; the pragma matches the ~45
test files already carrying `@vitest-environment node`. (3) **Other-mock spot-check refuted:**
governance-check is the ONLY builtin-mocking file; the two jsdom-default local-module mockers were
positively verified to still INTERCEPT, not merely pass (`brain.test.ts` injects `parseError`
through the mocked parse module + asserts mock-captured overlay writes; `topbar.test.tsx` asserts
`data-testid` markers that exist only in the mock components). (4) **Audit re-verified fresh, not
trusted:** branch = 9 vulns (3 MOD / 6 HIGH), **0 critical**, no vitest/vite chain; main baseline
re-run same day = 30 vulns incl. 1 CRITICAL + the vitest/vite advisories. **Residual flagged in the
PR (not blocking):** the pragma fixes the file, not the class — a future bare-automock of a Node
builtin under jsdom could silently run real fs and pass for the wrong reason (configured mocks fail
loudly with the TypeError); recommended follow-up: ESLint rule or vitest.config comment requiring
the node pragma for `vi.mock('node:*')` files. **Mechanics:** force-push of the rebased branch is
guard-denied (destructive-git hard deny), so the rebased state was pushed as new branch
`oi017-vitest4-migration-rebased` (original branch preserved on origin); PR #238 targets main from
it. NOT merged — financial-decision repo, Gabriel merges. After merge: the plain `npm audit fix`
pass for the 4 fixAvailable advisories (brace-expansion/fast-uri/js-yaml/postcss) remains queued
per the 07-26 investigation block.
**CLOSED-OUT 2026-07-26 (both PRs merged same day, Gabriel):** `ZeOoba/ora-pm#9` merged (`68fe84d`) —
deploy verified (production confirmed serving `68fe84d` via `wrangler pages deployment list`, `/api`
401 auth-gated, admin `/login` 200, no regression); ora-pm side of OI-017 is now fully clear, **0
vulnerabilities**. `ZeOoba/oxford-command-center#238` merged (`e7446cc`) — no auto-deploy exists for
this repo (verified: `ci.yml`/`full-gate-selfhosted.yml`/`order-fragility.yml` are gate/canary jobs
only, no deploy step; the brain mirror ships only via a separate manual `scripts/deploy-mirror.ps1`
run per the `/ship` doctrine), so this merge is main-only, nothing went live. **Item's original CVE
scope is now resolved: the vitest/vite CRITICAL+HIGH chain that blocked this item since 07-18 is
gone in both repos.** Two things remain, deliberately NOT rolled into this item's closure: (1) occ's
queued non-breaking `npm audit fix` pass (4 advisories: brace-expansion/fast-uri/js-yaml/postcss) —
trivial but still real financial-repo code, needs its own small PR+gate, not done unprompted this
session; (2) the ora-pm blank tenant-portal defect — tracked as its own task chip, already running
in a separate Gabriel-directed session, not part of this CVE item's scope to begin with.
**Closed:** 2026-07-26
**Evidence:** `npm audit` on ora-pm main (post-#9) = 0 vulnerabilities; `npm audit` on oxford-command-center
main (post-#238) = 9 vulns / 0 critical (down from 30 incl. 1 CRITICAL pre-merge), with the vitest/vite
chain that opened this item entirely gone. Both PRs confirmed MERGED via `gh pr view --json state`;
ora-pm deploy confirmed live via `wrangler pages deployment list` + a 401/200 health check.
**Auto-check:** none.

### OI-025
**Status:** CLOSED 2026-08-05 — full population audited (99/99, 0 unreadable)
**Resolution (2026-08-05):** the bounded sweep was completed. All 99 top-level folders in
`Claude_Workspace\00_Governance\Scheduled\` classified against the live fleet roster:
**34 DEAD-CONFIRMED archived**, 58 LIVE, 7 AMBIGUOUS left in place, 0 unreadable.
The method rule held throughout — absence from the roster was NEVER sufficient on its own
(many legitimate specs were simply never registered); every archived folder carried a second
documentary signal: 13 pinned to the dead Composio connector, 17 spent one-time diagnostics,
1 self-declared RETIRED, 3 absorbed into a live successor per that successor's own dated spec.
All 34 were re-checked against the live roster immediately before moving (0 hits), and moved —
never deleted — to `_archive_2026-08-05_oi025-sweep\`, whose README carries the per-folder evidence.
**The 7 AMBIGUOUS are now resolved to verdicts** (separate research pass, same day):
ARCHIVE — `ora-dashboard-refresh` (its entire project root `C:\Users\Owner\oxford-perfection` no
longer exists, so it cannot fire; its Cloudflare Pages target is served by a live successor,
`deploy-mirror.ps1` via a native Windows Scheduled Task, whose confidentiality control is
flag-based rather than the archived spec's obsolete Fulton-name gate) · `ora-email-queue-am` /
`-pm` (full-disk search confirms the parent spec they delegate to exists NOWHERE; both also
still name egoldberg, violating routing canon) · `ora-annual-budget-kickoff` (`_REGISTRY.md:79`
Gabriel-ratified-unneeded 2026-06-11) · `ora-cash-position-snapshot` (Composio-pinned AND
absorbed as Block D of live `ora-am-brief`, verified at `ora-am-brief\SKILL.md:44/71/290/294`).
NEEDS-GABRIEL — `ora-lease-expiration-action-list` (genuinely ADDITIVE, not redundant: the live
`ora-lease-expiration-brief` reads the Notion Tenant DB and buckets by horizon, but produces no
revenue-at-risk ranking, WALT, concentration flag, or outreach-gap list; registering both would
send two weekly lease emails) · `linkedin-insight-tag-followup` (the task is spent, but its
UNDERLYING item is still live — the placeholder `window._linkedin_partner_id='XXXXXXX';` survives
at `website-canonical\sell-your-building.html:930`; capture as a website backlog item before
archiving the reminder).
*(Original status line, retained: OPEN — one instance confirmed and remediated; full population unaudited)*
**Opened:** 2026-07-25
**Closed:** 2026-08-05
**Source:** shared-checkout investigation, this session (Gabriel asked to investigate the dirty-`~/.claude`-checkout flag raised at the end of the prior turn)
**Description:** while porting two skill-spec changes (HubSpot idle-deal flag + tracker-output redirect) into `ora-tenant-hubspot-reconciliation`, discovered the edit had first landed on `C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\00_Governance\Scheduled\ora-tenant-hubspot-reconciliation\SKILL.md` — a path that is NOT one of the two documented live registry locations (`tech.md` §3: CC/MCP = `~\.claude\scheduled-tasks\`, LAMS = `OneDrive…\Documents\Claude\Scheduled\`). Confirmed via `list_scheduled_tasks` that the task's real registered `path` is the CC/MCP copy; the Claude_Workspace copy drives nothing. Listing that directory found **100+ task folders** — active-looking names matching live CC registry tasks (`ora-am-brief`, `ora-weekly-hygiene`, `ora-health-guard`, `ora-pm-ledger`, etc.), clearly one-off/completed check-* and investigate-* folders, and four pre-existing `_archive_2026-0[6-7]-*` subfolders already inside this same directory — i.e. someone has been using this location as a working/archival area for some time, but no memory file documents its relationship to the two-fleet doctrine.
**Action taken 2026-07-25:** archived the confirmed-orphaned `ora-tenant-hubspot-reconciliation` folder to a new `_archive_2026-07-25_orphans\` subfolder in place (moved, not deleted, matching the directory's own existing convention). Did NOT touch or audit the other 100+ folders — that's a materially larger task than this session's scope (a single-skill investigation), and several of the plausible-looking "live" names need a careful diff-against-canonical pass, not a bulk move.
**Action taken 2026-07-26 (batch 1 of the recommended bounded sweep):** re-verified the live CC/MCP roster directly via `list_scheduled_tasks` (27 entries incl. 2 pending one-time) rather than trusting a pasted snapshot. Audited 10 NOT-yet-audited folders, all with names that don't match either fleet's live roster:
- **Archived to new `_archive_2026-07-26_orphans\`** (all (a) STALE ORPHAN — each folder's SKILL.md self-describes as a one-time/self-disabling diagnostic or reconnaissance task, none appear in the live CC/MCP registry, and the underlying subject matter is independently confirmed resolved elsewhere): `canary-model-check-temp` (one-time model-ID canary, result already consumed), `check-appsec-sweep-beacon-pickup` (one-time LAMS-fleet SKILL.md-edit-pickup check, dated 2026-07-20/21), `check-code-audit-image-pass` (one-time check-in on a since-concluded concurrent website-image session), `check-dirty-files-session-pr` (self-described "PAUSED — event overtaken... retire fully"; also independently confirmed as a "resolved/completed one-time task" and archived under the *separate* `~/.claude/scheduled-tasks/` canonical location per `event_log.md` line ~41, same date), `check-shared-checkout-settled-140pm` (one-time 2026-07-24 checkout-settlement check tied to the now-CLOSED `project_config_corruption_recurrence_closed_2026-07-25.md` thread; also independently archived under the canonical `~/.claude/scheduled-tasks/` location per the same `event_log.md` line), `continue-cc-setup-optimization-batch-2c-3` (one-time continuation of Batches 2c/3 of the `spicy-crunching-starlight.md` plan; confirmed shipped — `registry-write-guard` and `connector-drift-probe.py` both exist and are documented live in `tech.md` §3b / the connector-roster markers), `investigate-plan-gate-worktree` (one-time reconnaissance of the `plan-gate-and-site-markers` worktree; confirmed the worktree no longer exists on disk — already torn down), `heartbeat-beacon-recovery-check` and `heartbeat-check-backup-verify` (one-time 2026-07-17 Cowork-heartbeat diagnostics; both independently confirmed already deleted from the registry and archived under the canonical `~/.claude/scheduled-tasks/_archive_2026-07-18_retired/` location per `event_log.md` line ~854 — these Claude_Workspace copies were leftover duplicates never cleaned up here).
- **Flagged (c) AMBIGUOUS — left untouched, needs Gabriel's call:** `linkedin-insight-tag-followup` — a one-time reminder task (name matches no live-fleet entry, so not a canonical-copy question) whose underlying subject — retrieving the real LinkedIn Insight Tag Partner ID for oxfordra.net, blocked on a LinkedIn Campaign Manager 2FA propagation gate — is confirmed STILL open per `event_log.md` ("LinkedIn Insight partner ID is still the placeholder `XXXXXXX` across all 16 analytics snippets") and is NOT tracked anywhere else in this tracker. This folder may be the only remaining pointer to that open item; recommend Gabriel decide whether to (i) fold it into a proper OI/tracker entry and then archive this folder, or (ii) leave the folder as the tracking mechanism for now. Not archived.
- **No (b) legitimate-secondary-copy cases in this batch** — none of the 10 audited names matched a live registry task.
**Incidental finding 2026-07-26 (not part of this batch, flagged not acted on):** the previously-archived `ora-tenant-hubspot-reconciliation` folder (see 2026-07-25 action above) has **reappeared at the top level** of this same directory, with content that hashes differently from (and is larger than) the archived copy in `_archive_2026-07-25_orphans\` — most likely a OneDrive Files-on-Demand sync artifact from this canonical (egoldberg-account-syncing) checkout catching up after the prior move, consistent with the documented [Memory Scope Fragmentation](reference_memory_scope_fragmentation.md) pattern, but not confirmed. Per this task's explicit instruction, did NOT re-touch or re-archive it this pass. Flagging for a follow-up session to (a) confirm whether this is a transient sync artifact that will self-resolve, or a genuine re-write from another account/session, and (b) reconcile which content (archived 7,028-byte copy vs. reappeared 11,656-byte copy) is actually current before taking any action.
**Action taken 2026-07-26 (batch 2 of the recommended bounded sweep):** cross-referenced the legacy `_REGISTRY.md` in this same directory (a periodic manual snapshot, last updated 2026-07-09, explicitly self-described as non-authoritative) against the live directory listing to surface candidates beyond the two batch-1 named recommendations, then re-verified the live CC/MCP roster fresh via `list_scheduled_tasks` (30 entries incl. one-time) before classifying. Audited 12 folders total:
- **Archived to `_archive_2026-07-26_orphans\`** (all (a) STALE ORPHAN, each verified by reading its own SKILL.md, not name-pattern alone):
  - `ora-setup-review-closeout-recheck` and `ora-uw-northridge-brockton-full` — the two batch-1-recommended candidates; both self-describe as one-time tasks tied to a single 2026-07-17 chip-claim/underwriting event, independently confirmed already-retired/deleted-from-registry per `event_log.md` line ~854.
  - `loopnet-autoreply` — recurring 3x/daily task pinned entirely to `mcp__composio-ora__OUTLOOK_REPLY_EMAIL`; Composio-ora is fully removed (confirmed 2026-06-11 per `tech.md` §4) and this task is on `_REGISTRY.md`'s own "4 inbox sweeps" retired list.
  - `ora-setup-audit`, `ora-dormant-thread-revival`, `ora-weekly-tooling-intel-sweep` — each self-describes `RETIRED 2026-06-16 (strategic audit kill list)` directly in its own SKILL.md frontmatter, not just an external doc's claim.
  - `zapier-trial-cancel`, `zapier-trial-reminder` — one-time May 2026 Zapier-trial decision tasks pinned to the since-removed Composio/Rube routing; Zapier itself fully retired 2026-07-16 (`tech.md` §4).
  - `hard-delete-zapier-trial-reminder`, `hard-delete-composio-may10-checkpoint` — self-describe `[ONE-TIME 2026-05-31]` / `[ONE-TIME 2026-05-10]`, both already-fired self-archiving cleanup tasks for the two Zapier items above.
- **Flagged (c) AMBIGUOUS — left untouched, needs Gabriel's call (new finding, not a simple stale-orphan case):** `ora-annual-budget-kickoff` and `ora-cash-position-snapshot`. `_REGISTRY.md` lists both among its "4 Gabriel-ratified-unneeded (2026-06-11)" retirements — but unlike the three `RETIRED 2026-06-16` folders above, NEITHER folder's own SKILL.md says it's retired, and the newer `ora-operations-extensions` plugin's `annual-cycle` and `cash-position-monitor` skills explicitly claim to "power" scheduled tasks of these exact names. Neither task appears in the current live CC/MCP roster or either fleet's pending-one-time list, so if the newer skills' claim is accurate, this is a live registration GAP (a designed seasonal/recurring task never re-registered after the 2026-06-11 retirement), not a stale-folder cleanup — archiving would risk deleting the only surviving spec for a task Gabriel may want live. Needs a decision: were these two deliberately superseded by the ora-operations-extensions build, or should they be re-registered?
- **No (b) legitimate-secondary-copy cases in this batch** — none of the 12 audited names matched a live registry task.
**Running total:** 23 of ~100+ folders audited across 3 passes (1 on 2026-07-25; 10 on 2026-07-26 batch 1, 9 archived + 1 flagged; 12 on 2026-07-26 batch 2, 10 archived + 2 flagged); 20 folders now archived total (1 + 9 + 10) across `_archive_2026-07-25_orphans\` and `_archive_2026-07-26_orphans\`; 3 flagged (c) AMBIGUOUS and left in place (`linkedin-insight-tag-followup`, `ora-annual-budget-kickoff`, `ora-cash-position-snapshot`). 89 folders remain at top level (86 genuinely unaudited + the 3 ambiguous ones above). Further bounded batches (5-10/pass) remain — do NOT close this item until the full population is classified.
**Not yet done:** the remaining 86 unaudited folders (including all names that DO match a live registry task — `ora-am-brief`, `ora-pm-ledger`, `ora-health-guard`, etc. — which need the more careful (b)-vs-(c) diff-against-canonical treatment both passes so far deliberately deferred) still need classification. Recommend continuing the bounded sweep (5-10 folders/pass, mirroring `ora-weekly-hygiene` Block F's pattern), and prioritizing the still-unresolved `ora-pm-ledger` question specifically: a same-named folder was archived as an orphan in `_archive_2026-07-12_orphans\` yet a new `ora-pm-ledger` folder reappeared at top level the very next day (2026-07-13) — the same reappearance pattern observed for `ora-tenant-hubspot-reconciliation` above — which should be treated as (c) AMBIGUOUS, not re-archived on autopilot, until that recurrence pattern itself is understood.
**Auto-check:** none.

### OI-030
**Status:** CLOSED
**Opened:** 2026-07-26
**Closed:** 2026-08-03
**Source:** `ora-weekly-hygiene` Sunday run + 3 concurrent sessions, 2026-07-26 (see [event_log.md](event_log.md) 2026-07-26)
**Description:** `ora-weekly-hygiene/SKILL.md` Block C absorbed edits from four concurrent sessions in
a single day, including a Gabriel ruling (`caf154b`) that overrode an earlier same-day repoint:
check G was repointed to the `egoldberg` Graph drive, then formally DROPPED hours later, leaving
text that argued for a check the file struck through (dangling ref fixed in `9870bb4`, but only
that one symptom). Other same-day edits: Check B respec, frozen-snapshot RED override, real
folder names, Block N added, `781bf95` consolidating several idle sessions' WIP. Each change is
individually sound and the block is coherent as far as incremental patching can verify - the risk
is the kind only a full read catches: two locally-correct passages that disagree globally, exactly
the failure mode the check-G ruling itself was.
**Evidence (2026-08-03):** full read of Block C (lines 169-243) performed; **Gabriel ruled the item satisfied 2026-08-03.** The predicted
failure mode was REAL and present in four places, each a locally-correct passage contradicting the block globally:
1. **CONSTRAINTS guarded a forbidden tool.** The block's only error-handling clause covered SharePoint MCP
   auth/throttle errors, which SCOPE section 1 forbids the block from calling at all - while check C's Notion query
   and the local enumeration, which can fail, had no error path. Same dangling-reference class as check G;
   `9870bb4` fixed one symptom, this was another.
2. **Check A enforced a schema the firm does not use.** It flagged anything not matching
   `YYYYMMDD_[Topic]_[DocType]_[v##]`, which matches NONE of CLAUDE.md's three ratified schemas - so it
   flagged conformant session outputs as violations. The block's own XLSX followed the local rule and
   therefore breached firm canon.
3. **Check D had no frozen-snapshot carve-out.** SCOPE section 4's suppression was scoped only to the action count
   and Summary sheet, so D's "top 20" ran unfiltered against `01_Workspace/oxford-site/` (a frozen copy of
   the website repo) and would be dominated by files the block elsewhere declares need no action.
4. **Check C would likely return a silent zero.** `bcfe4a03` is the Acquisition Pipeline *data-source* id; it
   404s on `/v1/databases/{id}` and 400s at Notion-Version 2022-06-28 (multi-source DB). The same trap cost
   `ora-pm-ledger` a two-week false coverage gap. Block C carried no endpoint guidance.
Two lesser findings: SCOPE section 1's global "aging from mtime" contradicted check C's new deal-activity basis (no
carve-out stated); and line 183's standing "re-list the tree root before trusting this list" instruction remains
unmet going into the 2026-08-10 fire.
**Fix:** all six corrected in `scheduled-tasks/ora-weekly-hygiene/SKILL.md` (+39/-4). Structure re-verified after
edit: 14 block headings intact, checks A-F all present, and every surviving `sharepoint_search` mention is now a
prohibition or historical provenance, not a live instruction.
**Scope of the closure - recorded, not disputed:** the read was owed before the 2026-08-02 fire. That fire ran
late (2026-08-03 03:47 ET, catch-up) and the read happened after it; Block C published nothing on that run, so no
un-read output reached anyone (see [open-items-tracker.md#OI-058](open-items-tracker.md#OI-058)). The read was
agent-performed with Gabriel adjudicating three substantive rulings (check-A schema, check-D scope, commit
handling) rather than a line-by-line human pass. Gabriel accepted this as satisfying the item.
**Fixes were NOT committed at closure time.** The `.claude` checkout held 55 uncommitted changes across 8
sessions; committing was deliberately deferred rather than co-mingle another session's hunks. The edits are on
disk and take effect on the 2026-08-10 fire regardless of commit state - **verify they are committed before
treating this as durable.**
**Auto-check:** none.
### OI-020
**Status:** CLOSED 2026-08-05
**Opened:** 2026-07-19
**Closed:** 2026-08-05
**Source:** [event_log.md](event_log.md#2026-07-19)
**Description:** ora-cowork-heartbeat's LAMS registry entry has no `approvedPermissions` grant — only fix is Gabriel approving the Notion-tool prompt during a live unattended fire in Cowork's Scheduled Tasks UI; GitHub watchdog issue needs manual closure once fixed.
**Resolution (2026-08-05):** the grant is PRESENT and the task is firing. Live LAMS registry read: `approvedPermissions: [{'toolName': 'mcp__…notion-update-page'}]`, `enabled: true`, `lastRunAt 2026-08-05T09:57:51Z` against `lastScheduledFor 09:50` — i.e. it completed an unattended fire that morning. Someone approved it during a live fire without closing this item; it was documented "unresolved 3×" while already fixed.
**Residual (NOT closed by this):** the GitHub watchdog issue still needs manual closure — verify against `ZeOoba/ora-cowork-watchdog`. Separately, `fleet-roster.md` had this task's cron as `50 5,17 * * *` while the live registry said `50 5 * * *`; corrected by re-running `registry-membership-probe.py` the same day.
*(Section added 2026-07-29 during tracker ID-integrity reconciliation.)*

### OI-029
**Status:** CLOSED
**Opened:** 2026-07-26
**Closed:** 2026-08-03
**Source:** Repo-sweep session, 2026-07-26
**Description:** Two live/unrotated credential exposures: plaintext `NETLIFY_AUTH_TOKEN` in archived `oxford-realty/oxfordra-net` git history, and a non-redacted Netlify MCP proxy token in a `.git-corrupted-20260716/` backup folder — Gabriel must rotate both, then the backup folder needs secure deletion.
*(Section added 2026-07-29 during tracker ID-integrity reconciliation. The four paragraphs below record the 2026-08-03 close-out chronologically; they previously appeared out of order — de-sync, then revoke, then a summary claiming both — which read as self-contradictory. Consolidated here 2026-08-03, no facts changed, one independent re-verification added.)*

**Timeline:**
1. **CORRUPTED FOLDER DE-SYNCED** (`eccc6b7`) — the `.git-corrupted-20260716` backup was MOVED out of the OneDrive-synced tree to `~/archive/desynced-2026-08-03/20260726_oxford-site_git-corrupted-20260716` (263 MB, byte-intact; the git dir is genuinely unreadable so selective scrubbing was impossible). This stopped the plaintext token replicating to Microsoft's cloud and other devices — the live half of that exposure leg — but left rotation and final deletion open.
2. **EXPOSED PAT REVOKED** (`a09280e`, Gabriel, screenshot-confirmed) — the `ORA Lease App Sync` PAT (No Expiry, created Apr 25 — the only live token, and the one both exposures leak) was deleted from the Netlify account. The 4 remaining PATs are all `Expired` and cannot authenticate. This killed the plaintext material in both the archived `oxfordra-net` git history (`4b7a3bb`) and the de-synced backup folder — both now reference a dead credential.
3. **NEW FINDING, same screenshot** — Netlify's *Authorized applications* panel (never previously in frame) showed a live **Zapier OAuth grant, authorized Apr 5**. Verified unused before flagging: not a live MCP server, a stale `claude.ai Zapier` entry in `mcp-needs-auth-cache.json`, and a retired `hard-delete-zapier-trial-reminder` task records the trial as intended-for-teardown. Flagged for revocation; `Netlify CLI` and `Netlify MCP` explicitly kept (both in active use).
4. **FOLDER DELETED, Zapier revoked** (Gabriel) — the de-synced backup folder was deleted outright (not left in archive). **Independently re-verified 2026-08-03 by a separate session:** `~/archive/desynced-2026-08-03/` does not exist at all — no such directory, and no `README-WHY-THIS-IS-HERE.md` anywhere under `~/archive` or the original synced path. Folder-deletion leg confirmed from the filesystem, not just from report. The Zapier grant revocation is **account-side and was not independently verified from Code** (Netlify's OAuth-grants list is a web-UI-only surface with no exposed read endpoint — confirmed by attempting `netlify-user-services-reader get-user`, which does not cover it) — this leg rests on Gabriel's report only.

**Net position:** PAT revocation and folder deletion are each corroborated by two independent means (Gabriel's account-side action + a separate filesystem/screenshot check). The Zapier leg rests on a single, unverifiable-from-Code report. Closing on that basis — flag if the Zapier grant should be re-checked at the next credential sweep.

**2026-07-30 SCANNER CORRECTION (read this before trusting any earlier "clean" result here):** the whole-history scans that reported this repo clean were run with `hooks/lib/secret_patterns.py` BEFORE its word-boundary fix — `\b(?:SECRET|TOKEN)\b` cannot match inside `NETLIFY_AUTH_TOKEN` because `_` is a word character, and there was no `nfp_` pattern at all. The scanner was structurally blind to THIS ITEM'S OWN credential type. Commit `4b7a3bb` was only found by a targeted grep. Fixed and merged 2026-07-30 (`f809c73`, 4 adversarial REFUTE passes); the re-scan with working patterns is what actually cleared the other 1,377 commits. Treat any pre-fix "0 findings" as unearned.

**2026-07-30 investigation (still OPEN — Netlify rotation is Gabriel's, not automatable):** `oxford-realty/oxfordra-net`'s archived repo has 1 local commit, NO remote configured — exposure is disk-local, not live on GitHub. The `.git-corrupted-20260716` backup folder is unreadable by git (`fsck`/`log` both fail) but sits inside the **OneDrive-synced** Claude_Workspace tree — raw bytes likely still plaintext and have been syncing to the cloud since mid-July, a bigger exposure surface than the original note implied. Neither Netlify token rotation nor the backup folder's secure deletion can be performed by Code (credential-generation + permanent-deletion are both outside its permitted actions) — runbook handed to Gabriel directly. Unrelated but adjacent: the orphaned `~/.secrets/anthropic-key.dat`/`netlify-token.dat` pair (zero consumers, separate from this item's tokens) was archived-and-retired same day per Gabriel's ruling — see `tech.md` §7.

### OI-032
**Status:** CLOSED
**Opened:** 2026-07-28
**Closed:** 2026-07-28
**Source:** Code-surface usage-limit audit, handed to Cowork for cross-surface follow-up, 2026-07-28
**Description:** `searchfit-seo` is installed TWICE in Cowork's plugin registry
(`...\583f08bc.../rpm\manifest.json`) — `plugin_01814pKq2AozUbEdjvGZw5os` (installed 2026-07-08,
marketplace "My Uploads") and `plugin_016u9h5nGGKuX18riDTJ7otg` (installed 2026-07-24, marketplace
"knowledge-work-plugins", displayName "SearchFit SEO"). Both show `installationPreference:
"available"`, doubling every searchfit-seo skill/agent in the listing. Not in active use per
Gabriel (2026-07-28 usage-limit audit). No supported tool exists to uninstall from either surface —
Cowork's manifest.json has no enable/disable boolean (unlike Code's `skillOverrides`), and hand-
editing it blind was correctly declined as an unverified-schema write.
**Evidence:** Gabriel confirmed (in-turn, 2026-07-28) he uninstalled both `searchfit-seo` entries
manually via Settings → Capabilities, per the candidate fix below. Not independently re-verified
against the live manifest.json (no tool access to that surface from Code) — trust the direct report.

### OI-034
**Status:** CLOSED
**Opened:** 2026-07-31
**Closed:** 2026-08-03
**Source:** ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch)
**Severity:** HIGH (financial, real-money)
**Description:** `server/routes/cron.ts:71-107`. The charge-insert loop is correctly idempotent
(`charges.idempotency_key` UNIQUE, a `23505` counted as `skipped`). The autopay PaymentIntent path
immediately below is **not**: it re-queries every charge with a `due_date` in the period, sums it, and
calls `stripe.paymentIntents.create({...})` with no `idempotencyKey` option and no check for an
existing payment for that lease/period, then inserts a second `payments` row. Two aggravators: the sum
is over *all* charges due in the period regardless of whether the tenant already paid manually; and
`errors++` on a Stripe failure still returns HTTP 200, so a caller retrying on failure re-enters the
loop for every lease, not just the failed one.
**Repro (not executed — static):** `POST /api/cron/monthly-billing?year=2026&month=7` twice with
`CRON_SECRET`. Run 2: all charge inserts return `23505` -> `skipped`, then the autopay block re-runs
unchanged, creating PI #2 confirmed `off_session` and a second `payments` row. Net: two ACH debits,
`ar_ledger.total_paid` double-counted once both settle.
**Candidate fix (NOT applied — this sweep is report-only):** pass a deterministic Stripe idempotency
key (`autopay:${lease.id}:${periodStartStr}`); add a DB-level precondition (partial unique index on
autopay payments per lease/period — prefer the index, a pre-check alone is racy); and compute
`totalAmount` as *outstanding* (charges minus settled payments), not gross charges.
**Note:** financial-decision code — per CLAUDE.md the fix requires a mandatory adversarial REFUTE pass.
Related: [OI-035](#OI-035) is the enforcement layer that would have caught this.
**Evidence:** Fixed on `ora-pm` main, commit `3e600e4` (merge of `fix/oi-034-autopay-idempotency`,
isolated from the broader in-progress `plan/appsec-fixes-oi034-048` branch). Deterministic Stripe
`idempotencyKey`, `autopay_period` DB-unique-constrained pre-check, `23505`-as-skip on both charges
and payments inserts. A REFUTE pass (security-auditor dispatch) on the first draft of this fix found
a second, real gap: the debit cap compared a period-scoped charge total against `ar_ledger`'s
LIFETIME balance, so a tenant with old arrears who fully paid the current period manually could
still be auto-debited for the arrears via ACH. Fixed via TDD (failing test written first,
confirmed it failed pre-fix, then a period-scoped payments lookup replaced the lifetime-balance
comparison as the primary collection amount, keeping the lifetime balance only as a safety
ceiling). 244/244 suite green, typecheck clean, verified on `main` post-merge before push.
**Auto-check:** none.

### OI-035
**Status:** CLOSED
**Opened:** 2026-07-31
**Closed:** 2026-08-03
**Source:** ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch)
**Severity:** HIGH (financial, ledger integrity)
**Description:** schema `supabase/migrations/0002_financial_tables.sql:26-40`; writers
`server/routes/stripe.ts:138-147` and `server/routes/cron.ts:94-102`. `payments` carries a
**non-unique** partial index on `stripe_payment_intent_id` (line 40) and no unique constraint
anywhere. `POST /api/stripe/payment-intent` creates the PI and *then* inserts the payments row as two
non-atomic steps; a client retry after a network timeout (the Stripe call having already succeeded)
produces a second PI *and* a second row.
**Impact:** `ar_ledger.total_paid` over-counts, understating the tenant's true balance; the
delinquency check then skips a genuinely delinquent tenant. This is the same underlying failure mode
as the original cartesian fan-out, expressed at the row-creation layer instead of the join layer.
**Candidate fix (NOT applied):** `CREATE UNIQUE INDEX payments_stripe_pi_unique ON
payments(stripe_payment_intent_id) WHERE stripe_payment_intent_id IS NOT NULL;` then handle `23505`
in both writers as “already recorded” rather than 500; plus an `idempotencyKey` on the
`/payment-intent` Stripe call. Financial-decision code — mandatory adversarial REFUTE pass on the fix.
**Evidence:** Fixed on `ora-pm` main, commit `d99a412` (merge of `fix/oi-035-payment-idempotency`,
isolated the same way as OI-034, from the broader `plan/appsec-fixes-oi034-048` branch). DB unique
index `payments_stripe_pi_uniq` (migration 0011, landed with the OI-034 merge) + a UUID-validated
`client_request_id` echoed into Stripe's idempotencyKey + `23505`-on-insert now returns a clean
`200 {deduped:true}`. Bundled in the same reviewed/tested commit as OI-040 and the OI-038a IP-fallback
slice — cherry-picked as one cohesive unit rather than split apart, to avoid re-deriving tested logic.
A REFUTE pass (security-auditor dispatch) found no exploitable double-charge or cross-tenant leak, but
two real gaps outside this fix's original scope, filed as follow-ups rather than blocking (Gabriel's
call, 2026-08-03): [OI-064](#OI-064) (retry-recovery UX doesn't work as the commit describes for the
bank-linking flow) and [OI-065](#OI-065) (concurrent-request race on the balance check). 260/260 suite
green, typecheck clean, verified on `main` post-merge before push.
**Auto-check:** none.

### OI-036
**Status:** CLOSED
**Opened:** 2026-07-31
**Closed:** 2026-08-03
**Source:** ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch)
**Severity:** MEDIUM (authorization)
**Description:** `server/middleware/admin-auth.ts:30-32`; `src/pages/auth/AdminLogin.tsx:18-21`. The
only authorization check for the entire admin API is an email-domain suffix test. No role table, no
admin allowlist, no separation between admin and tenant audiences (one Supabase auth project). The
client-side `email.endsWith('@oxfordra.net')` at line 12 is cosmetic and bypassable by calling
Supabase directly. `signInWithOtp` without `shouldCreateUser: false` mints a new auth user for any
address entered.
**Impact:** full admin API — every tenant's PII, all lease economics, all AR, plus `inviteUserByEmail`
/ `deleteUser` on the auth project. Related edge: `tenants.contact_email` drives `inviteUserByEmail`,
so a portal tenant invited at an `@oxfordra.net` address would pass the same domain test and become a
full admin.
**Candidate fix (NOT applied):** explicit two-principal allowlist from an env binding, failing CLOSED
when unconfigured (503); `shouldCreateUser: false` on the admin OTP call; a guard in `portal-auth.ts`
refusing to invite a tenant whose `contact_email` is in the admin domain.
**Evidence:** Fixed on `ora-pm` main, commit `18d8f6d` (merge of `fix/oi-036-admin-auth`, isolated the
same way as prior appsec merges). Exact-match `ADMIN_EMAILS` env-binding allowlist (case-insensitive,
comma-separated), fail-closed 503 when unset/empty; a live `tenants.auth_user_id` exclusion check
rejects any authenticated user who is also a tenant regardless of when they were invited (subsumes the
originally-proposed invite-time guard in `portal-auth.ts` — catches it at request time instead, which
also covers tenants invited before this fix shipped); `shouldCreateUser: false` stops admin
self-provisioning. Also folded in a self-found review fix: the tenant-exclusion query's `error` was
never checked, silently letting requests through on a query failure — now fails closed (500).
REFUTE pass (security-auditor dispatch) traced every branch of the middleware, the app-level error
handler, and `portal-auth.ts`'s own defense-in-depth gate; confirmed exact-match (not substring),
server-verified email (not client-supplied via `supabase.auth.getUser`), no TOCTOU window (live
per-request lookups, no caching). One non-blocking suggestion (an explicit substring/prefix-email
regression test) left as a code-quality nice-to-have, not filed separately. 266/266 suite green,
typecheck clean, verified on `main` post-merge before push.
**OPERATIONAL NOTE for Gabriel:** production needs `ADMIN_EMAILS` set in the Cloudflare env config or
the entire admin API 503s for everyone, Gabriel included, until it's configured.
**Auto-check:** none.

### OI-037
**Status:** CLOSED
**Opened:** 2026-07-31
**Closed:** 2026-08-04
**Source:** ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch)
**Severity:** MEDIUM (defense-in-depth / clickjacking)
**Description:** (a) `server/index.ts:47` — `app.use('/api/*', cors())`; Hono's no-arg `cors()`
defaults to `origin: '*'`, applied to every `/api/*` path including the admin CRUD surface. Bounded
today because auth is an `Authorization: Bearer` header and Supabase stores the JWT in `localStorage`
(not a cookie), so a foreign origin cannot silently attach credentials — but it removes the layer that
would contain any future token-in-cookie change or a token leak. (b) No `_headers`, no `public/`, no
header block in `wrangler.toml`, no `<meta http-equiv>` in `index.html` — so no CSP, HSTS,
X-Frame-Options, or Referrer-Policy.
**Impact:** `/portal/pay` is framable, so a clickjacking overlay can drive a tenant into initiating an
ACH debit. No CSP means an injected script executes with full origin privileges against a session
shared by the portal and the admin app.
**Candidate fix (NOT applied):** restrict CORS to the known origins with explicit `allowHeaders`; add
`public/_headers` with X-Frame-Options DENY, nosniff, Referrer-Policy, HSTS and a CSP allowing only
self + `js.stripe.com` + the Supabase/Stripe API origins, `frame-ancestors 'none'`.
**Verification caveat:** the served response headers were NOT fetched (report-only, no live probing).
A merged config is not a live header — verify against the served response before closing.
**Progress (2026-08-03):** code fix merged to `ora-pm` main, commit `23b924f` (CORS exact-match
allowlist + `public/_headers`). REFUTE pass (security-auditor dispatch) confirmed the CORS allowlist
is exact-match with no prefix/substring bypass, credentials never combined with a wildcard origin,
both allow/deny directions tested. Confirmed directly: `X-Frame-Options: DENY` ships as a real,
enforcing header — the clickjacking half of this finding IS closed as of this commit, independent of
deploy verification, since it's a static header value not runtime-probed browser behavior. The CSP
half ships `Content-Security-Policy-Report-Only` (deliberately, per the commit's own rationale — this
environment can't browser-test the live Stripe Elements + Supabase auth flow) — it logs violations
only and does not yet block anything; flipping it to enforcing needs a manual browser pass against a
deployed preview, then dropping `-Report-Only` from the header name. Filed as
[OI-066](#OI-066) rather than silently expanding this item's scope.
**Closure evidence (2026-08-04):** the item's own verification caveat is now satisfied — fetched
`https://ora-pm.pages.dev` live (Claude-in-Chrome, in-page `fetch` with `credentials:'omit'`, not
simulated): `x-frame-options: DENY` confirmed present and enforcing on the real served response;
`content-security-policy-report-only` confirmed present with exactly the expected policy
(`default-src 'self'; script-src 'self' https://js.stripe.com; connect-src 'self' https://api.stripe.com
https://*.supabase.co; frame-src https://js.stripe.com; frame-ancestors 'none'; base-uri 'self';
form-action 'self'`); enforcing `content-security-policy` correctly absent (Report-Only by design, per
OI-066). This item's scope (clickjacking protection + CORS allowlist, live and confirmed) is closed;
CSP-enforcement flip remains OI-066's separate job.
**Auto-check:** none.

### OI-038
**Status:** CLOSED
**Opened:** 2026-07-31
**Closed:** 2026-08-03
**Source:** ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch)
**Severity:** MEDIUM (abuse / cost, OWASP LLM10)
**Description:** `server/lib/rate-limit.ts:1-26`, applied only at `server/routes/stripe.ts:87-94`.
The limiter is a module-scope `Map` in a Workers isolate — not shared state, so the 5-per-minute cap
on PaymentIntent creation is not enforceable in practice. Line 87 falls back to the
attacker-controlled `X-Forwarded-For` when `CF-Connecting-IP` is absent. Separately
`server/routes/intake.ts:9,38-43,47-48`: per-request controls are good (10 MB cap enforced
server-side, `%PDF` magic-byte check, `max_tokens: 1024`) but there is no *rate* limit, no per-day
request or spend budget, no concurrency cap, and `INTAKE_MODEL` is an env-controlled model override
with no allowlist.
**Impact:** an authenticated tenant can drive high-volume Stripe API calls (cost, Stripe-side
rate-limit exhaustion affecting legitimate payments) and generate `payments` rows at will. An
admin-authenticated caller can loop 10 MB PDFs against the Anthropic API without bound — direct
billing exposure and API-key rate-limit exhaustion that breaks legitimate intake.
**Candidate fix (NOT applied):** move the counter to durable shared state (Cloudflare KV, a Durable
Object, or a `rate_limits` table) keyed on `tenantUserId` rather than IP; apply it to the intake route
at a much lower ceiling (~10/hour/admin) plus a daily counter; constrain `INTAKE_MODEL` to an
allowlist. Cloudflare native Rate Limiting rules are the cheapest correct option.
**Partial progress (2026-08-03):** the `X-Forwarded-For` IP-spoofing slice specifically (line 87) is
fixed on `main`, commit `d99a412` — `CF-Connecting-IP ?? tenantUserId` replaces the spoofable fallback,
verified safe since this route is authenticated-only (no path reaches it without a real `tenantUserId`
from `tenantAuthMiddleware`). The durable-shared-state redesign, the intake-route limits, and the
`INTAKE_MODEL` allowlist are all still unaddressed — remains OPEN. (A separate live session appears to
be continuing work on the shared-state piece as of this note — check for newer progress before
re-doing it.)
**Evidence:** Fixed on `ora-pm` main, commit `63eb548` (merge of `fix/oi-038-044-ratelimit-pdfscan`).
`checkRateLimit` is now KV-backed (`RATE_LIMIT_KV`, cross-isolate, fixed-window) with the old
per-isolate `Map` kept only as a same-isolate fast path in front of it; wired into payment-intent
(existing 5/min, unchanged), `/api/intake/lease` (new, 10/day/admin), admin mutation routes (new,
120/min/admin), and `/api/cron/*` (new, 10/hour/endpoint, sized to absorb a legitimate fleet
catch-up burst). `INTAKE_MODEL` constrained to an allowlist, falling back to the default model on a
non-allowlisted value rather than rejecting. REFUTE pass (security-auditor dispatch) confirmed the
"degrades to memory-only when unbound" claim is code-correct, and separately caught that the
`wrangler.toml` KV binding shipped with a placeholder namespace id that would likely fail the entire
deploy — fixed by commenting out the binding until a real namespace is provisioned.
**OPERATIONAL NOTE for Gabriel:** production is running on the memory-only fallback (weaker,
per-isolate) until the KV binding is provisioned and uncommented — `wrangler kv namespace create
RATE_LIMIT_KV`, paste the id into `wrangler.toml`, uncomment the `[[kv_namespaces]]` block.
**Auto-check:** none.

### OI-039
**Status:** CLOSED
**Opened:** 2026-07-31
**Closed:** 2026-08-04
**Source:** ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch)
**Severity:** MEDIUM (latent correctness precondition)
**Description:** every money column is bare `NUMERIC` — no `(12,2)` scale, no `COMMENT ON COLUMN`, no
unit suffix in the name — while `server/routes/stripe.ts:96` uses `amount_cents` at the API boundary.
**Balance path traced clean this run** (recorded so it is not re-derived): DB `ar_ledger.balance` ->
`server/routes/portal.ts:24-27` -> `PortalDashboard.tsx:10,31` `formatCurrency` = **exactly zero unit
conversions**, which is correct (dollars at every hop). The payment path likewise has every `*100`
matched by exactly one `/100`. The 2026-07-18 fix is holding and is guarded by
`tests/components/portal-dashboard-no-cents-division.test.ts`.
**Candidate fix (as originally filed):** `ALTER COLUMN amount TYPE NUMERIC(12,2)` on `charges` and
`payments` plus `COMMENT ON COLUMN ... IS 'US dollars, 2dp. NOT cents.'`.
**Evidence (2026-08-04):** applied migration `0011_appsec_idempotency_and_scale.sql` directly against
production (Supabase SQL Editor, Gabriel executed the DDL in-turn after reviewing it; all 3 of the
migration's own documented pre-flight checks run first and clean — 0 duplicate PaymentIntents, 0
backfill-key collisions, 0 sub-cent-precision rows across all 10 target columns). Post-apply, all 10
money columns (`charges.amount`, `payments.amount`, `expenses.amount`,
`cam_reconciliations.{total_property_recoverable_expenses,estimated_cam_paid,actual_cam_owed,
true_up_amount}`, `budgets.budgeted_amount`, `tenant_sales_reports.{reported_sales,
percentage_rent_owed}`) confirmed live at `NUMERIC(12,2) NOT NULL` via
`information_schema.columns`. `ar_ledger` view (dropped/recreated inside the same migration to release
the column dependency) confirmed resolving cleanly post-apply (139 leases, aggregates compute without
error). Same session also discovered and closed a broader latent gap: production's migration tracker
(`supabase_migrations.schema_migrations`) was stalled at version 0007, which had made 0009/0010 look
unapplied — they were in fact already live (applied out-of-band, untracked; confirmed via
`pg_get_viewdef('ar_ledger')` matching 0010's definition verbatim before 0011 ran). See
[OI-073](#OI-073) for that tracking-gap finding, filed separately.
**Auto-check:** none.

### OI-040
**Status:** CLOSED
**Opened:** 2026-07-31
**Closed:** 2026-08-03
**Source:** ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch)
**Severity:** MEDIUM (financial)
**Description:** `server/routes/stripe.ts:96-101`. Validation is integer + `>= 50`; no maximum, no
relation to the lease's outstanding balance. `GET /api/portal/charges` has no paid/open discriminator
(`portal.ts:44-51`, `PortalPayNow.tsx:21-24` — both acknowledge the limitation in-code).
**Impact:** `amount_cents: 100000000` is accepted; and the normal UI flow lets a tenant pay the same
charge twice with no warning. Both create dispute/reversal exposure and pollute `ar_ledger` with
credit balances the system cannot represent (cf. the `cam.ts:103-107` credit limitation).
**Candidate fix (NOT applied):** compute the outstanding balance server-side from `ar_ledger` and
reject `amount_cents > Math.round(balance * 100)` with a 422, plus an absolute sanity ceiling. Longer
term close the schema gap: a `payment_allocations(payment_id, charge_id, amount)` table so a charge
has a provable settled state — this one change retires this item, the `portal.ts` limitation and the
`cam.ts` credit limitation together instead of patching each symptom separately.
**Evidence:** Fixed on `ora-pm` main, commit `d99a412` (same merge as OI-035, bundled in one
reviewed/tested commit). `MAX_PAYMENT_CENTS` ($50,000) hard ceiling (422) then reject against the
lease's `ar_ledger.balance` (422 for amount > balance, or "No balance due" for <= 0); boundary
(amount == balance) allowed; a failed balance-lookup never falls through to a blind charge — verified
directly by reading the code, not just trusting the commit message. The "no paid/open discriminator"
UI residual (`portal.ts`/`PortalPayNow.tsx`, still shows settled charges as selectable) is no longer a
money-safety gap since the balance cap now backstops it — an already-paid charge's outstanding balance
is $0, so re-selecting it fails the amount check. The `payment_allocations` schema redesign remains a
longer-term nice-to-have, not required to close this item. REFUTE pass on the same commit: see
[OI-035](#OI-035)'s Evidence.
**Auto-check:** none.

### OI-043
**Status:** CLOSED
**Opened:** 2026-07-31
**Closed:** 2026-08-03
**Source:** ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch)
**Severity:** MEDIUM (authorization, mitigated by a third party)
**Description:** `server/routes/portal.ts:124`, `:136-140`. Lease ownership IS verified (`:133-134`);
payment-method ownership is not. Consumed off-session at `server/routes/cron.ts:87`.
**Impact:** bounded — Stripe rejects a PaymentIntent whose `payment_method` is attached to a different
customer, so the realistic outcome is broken autopay, not a cross-tenant debit. Recorded because the
only thing standing between the two outcomes is Stripe's own behaviour, and the failure mode is
silent (counted as `errors++` in an HTTP 200).
**Candidate fix (NOT applied):** before persisting, `stripe.paymentMethods.retrieve(payment_method_id)`
and reject unless `pm.customer === tenant.stripe_customer_id`.
**Evidence:** Fixed on `ora-pm` main, commit `df196ee` (merge of `fix/oi-043-042-portal-autopay`) —
implemented exactly as the candidate fix specified, plus a bank-account-type check. REFUTE pass
(security-auditor dispatch) traced the ownership check, type check, format validation, and every
error-handling path (both a local catch and the global error-handler middleware fail closed on any
Stripe API error) — no bypass found. One coverage gap (an already-correctly-handled orphaned-PM edge
case was unpinned by any test) fixed directly with an added test rather than filed separately.
322/322 suite green, typecheck clean. Note: [OI-068](#OI-068) (filed by the branch's own task
reviewer) found the autopay-with-payment-method enrollment flow this fix protects is currently
unreachable from any live frontend path — this fix is still correct and worth having as defense in
depth (the API is directly callable regardless of frontend state), but the practical exposure today
is close to zero until that frontend gap is also closed.
**Auto-check:** none.

### OI-044
**Status:** CLOSED
**Opened:** 2026-07-31
**Closed:** 2026-08-03
**Source:** ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch)
**Severity:** MEDIUM (third-party data egress)
**Description:** `server/routes/intake.ts:17-30`; `server/lib/confidentiality.ts:8-11`. The guard
checks the filename before egress and the returned string fields after, but never the document body.
**Why MEDIUM and not HIGH:** the four compensating controls are genuine — the endpoint is admin-gated,
structurally bound to an existing managed `tenant_id`+`unit_id`, the denylist fails CLOSED when
unconfigured (503 rather than proceed — the correct direction), and there is a UI attestation.
**Residual:** control (3) is an argument about intent, not an enforced constraint — nothing stops an
admin creating a placeholder tenant/unit for an acquisition target.
**Candidate fix (NOT applied):** until Phase 2b adds Worker-side PDF text extraction, add the cheap
enforceable check — reject when the resolved `tenant_id`'s name or the `unit_id`'s property name hits
the denylist. That converts “structurally a managed lease” from an assumption into a test.
**Evidence:** Fixed on `ora-pm` main, commit `63eb548` (merge of `fix/oi-038-044-ratelimit-pdfscan`) —
the Phase 2b work this item was waiting on landed. `server/lib/pdf-extract.ts` wraps `unpdf` to
extract the PDF's actual text pre-egress and run it through the same denylist; a match blocks with a
422 before `extractLease` is ever called (verified by test — no egress for a blocked document).
`tenant_id`/`unit_id` are now existence-checked against the DB (404 if either doesn't exist), not
just presence-checked as before — directly closes this item's own residual note about a placeholder
tenant/unit. A REFUTE pass (security-auditor dispatch) then found the initial implementation's
handling of image-only/scanned PDFs (no extractable text, so the new check can't run) deliberately
FAILED OPEN — proceeded with extraction and egressed the document before ever surfacing a warning,
which doesn't actually compensate the way the four originally-cited controls were assumed to (this
item's own "Residual" line above already anticipated exactly this: "an argument about intent, not an
enforced constraint"). Fixed via TDD (failing test written first) to BLOCK scanned/image PDFs with a
422 instead, mirroring the route's existing manual-entry fallback UX. 297/297 suite green, typecheck
clean, verified on `main` post-merge before push.
**Auto-check:** none.

### OI-045
**Status:** CLOSED
**Opened:** 2026-07-31
**Closed:** 2026-08-04
**Source:** ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch)
**Severity:** MEDIUM (security control that misrepresents its own state) — escalated to CRITICAL
mid-fix, see Evidence.
**Description:** `src/portal/pages/PortalAccount.tsx:33-35`, `:87-93`. The enroll call's return value
is discarded; no challenge/verify flow exists anywhere in the codebase.
**Impact:** tenants may believe an account authorizing ACH debits is MFA-protected when it is not.
This is worse than having no MFA button at all, because it is an affirmative false assurance.
**Candidate fix (NOT applied):** either implement the full enroll -> display QR/secret -> challenge ->
verify flow, or remove the button and the copy until it is built. Do not ship a control that
misrepresents its own state.
**Evidence (2026-08-04):** the enroll->challenge->verify UI flow itself was already fixed by an earlier
commit (real QR/secret rendering, real `mfa.verify()` gate, orphaned-unverified-factor cleanup on
enroll) — a REFUTE pass on THAT fix found the resulting AAL2 (step-up) enforcement was **client-side
only**: `src/portal/PortalApp.tsx` gates which React component renders, but nothing on the server ever
checked whether the current session had completed the MFA challenge. PoC: `PATCH /api/portal/autopay`
had no AAL check anywhere in its chain — any tenant (or attacker holding a stolen/leaked bearer JWT,
e.g. via XSS or a synced session) with a valid but un-stepped-up (aal1) JWT could enable ACH autopay
directly via the API, bypassing MFA entirely. Escalated from MEDIUM to CRITICAL on this finding.
Fixed via `server/middleware/aal-guard.ts` (`requireAal2`): calls the documented server-side/stateless
form of `auth.mfa.getAuthenticatorAssuranceLevel(jwt)` (a real Supabase network round-trip, not a
locally-decoded claim), fails closed on any error, mirrors `mfa-guard.ts`'s existing pure decision
logic. A SECOND REFUTE pass on that fix found the scope was still too narrow: `POST
/api/stripe/setup-intent` (attaches a `us_bank_account` PaymentMethod to the tenant's Stripe customer)
and `POST /api/stripe/payment-intent` (CONFIRMS and charges immediately — the single most sensitive
path, moves real money) were both still completely ungated, independent of `/autopay`. Both gated. A
THIRD REFUTE pass swept the rest of `server/routes/` for any other tenant-JWT-reachable
financial-write path — none found; confirmed complete. End-to-end integration tests (not just
middleware-unit tests) prove the real middleware is wired onto the real routes against the real app,
asserting the underlying Stripe API call is never reached when the gate blocks, not just that the HTTP
status is 403. `POST /api/stripe/customer` (customer-shell creation, no PM/money involved, IDOR-safe,
idempotent) deliberately left ungated — one low-severity follow-up surfaced there (unvalidated
email/name from the request body reaching `stripe.customers.create`), filed as [OI-077](#OI-077).
Fixed on `ora-pm` main, commits `03487cd` + merge `a29f8f0`. 426/426 suite green (448/448 after
merging concurrent `main` work), typecheck clean.
**Auto-check:** none.

### OI-046
**Status:** CLOSED
**Opened:** 2026-07-31
**Closed:** 2026-08-03
**Source:** ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch)
**Severity:** MEDIUM (financial, concurrency)
**Description:** `server/routes/cam.ts:84-138`; nullable unique column at
`supabase/migrations/0002_financial_tables.sql:17`. Same failure class as [OI-034](#OI-034) /
[OI-035](#OI-035): the ledger is a sum over rows and a duplicate row is a silent, wrong balance.
**Candidate fix (NOT applied):** make the status transition itself the concurrency control —
`.update({status:'billed'}).eq('id', id).eq('status','draft').select().single()` and proceed only if a
row was returned; and give the CAM charge a deterministic key
(`cam_true_up:${r.lease_id}:${r.reconciliation_year}`). Financial-decision code — REFUTE pass on the fix.
**Evidence:** Fixed on `ora-pm` main, commit `81b5626` (merge of `fix/oi-046-cam-race`) — implemented
exactly as the candidate fix specified: insert-first (idempotency-keyed
`cam_true_up:<lease_id>:<year>`, backed by the DB unique constraint), conditional-update-second
(`.eq('status','draft')`) for both the positive and negative true-up branches. REFUTE pass
(security-auditor dispatch) traced two genuinely concurrent approve requests through the actual code:
the second insert hits the unique-constraint violation (Postgres enforces this atomically, not
app-level locking), takes the no-op branch, and its conditional update correctly matches zero rows —
no double-post survives. One real MEDIUM finding, filed separately rather than blocking this merge
(Gabriel's call, 2026-08-03): the idempotency key has no amount/version component, so a legitimate
recalculation of an already-billed CAM true-up collides with the OLD charge's key and is silently
dropped as a "duplicate" — filed as [OI-069](#OI-069). 311/311 suite green, typecheck clean.
**Auto-check:** none.

### OI-047
**Status:** CLOSED
**Opened:** 2026-07-31
**Closed:** 2026-08-04
**Source:** ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch)
**Severity:** MEDIUM (send-path canon / routing)
**Description:** `server/routes/cron.ts:118`, `:184-200`, `:219`, `:297-311`. Both scheduled jobs POST
to the Resend API with a two-recipient list including `egoldberg@`, which the routing canon does not
cover for this job.
**Done correctly and worth preserving:** the send is non-fatal on network failure (`:201-204`,
`:313-316`), and dedup rows are written *before* the send (`:165-167`) so a failure retries cleanly
rather than re-sending. Those are the right calls — a fix must not regress them.
**RULING (Gabriel, 2026-08-04): option (b).** Trim `RECIPIENTS` to `ggoldberg@` only; the Resend call
in the Worker is removed, and the ORA scheduler performs the actual send via Outlook COM
(`_shared/send-via-outlook.ps1`) instead. Brings ora-pm in line with the standing send-path canon and
closes the second-egress-path risk (a leaked Resend key today could send/exfiltrate tenant data
through a channel outside the audited chain). Option (a) — ratify Resend as a documented exception —
was declined.
**CLOSED 2026-08-04.** Implemented per `ora-pm/docs/superpowers/plans/2026-08-04-ora-pm-oi047-outlook-com-handoff.md` (branch `fix/oi-047-outlook-com-handoff`, PR [#20](https://github.com/ZeOoba/ora-pm/pull/20), merge `5bbb262`). Both Resend `fetch()` calls removed from `server/routes/cron.ts`; `RECIPIENTS` trimmed to `['ggoldberg@oxfordra.net']`; both handlers now return `email: {subject, body} | null` instead of sending. The actual send moved to `C:\Users\Owner\ora-pm-cron\ping-crons.ps1` (the real live trigger — a standalone Windows Task Scheduler task, not the Claude fleet registry; confirmed during design that the original brief's "ORA fleet scheduler" assumption was wrong — Gabriel ruled to extend this script rather than migrate the trigger, to avoid regressing its Desktop-independent reliability), which sends via the canonical `_shared\send-via-outlook.ps1`.

**Preserved-behavior verification:**
- Dedup-before-send: `tests/routes/cron-alerts.test.ts` asserts the dedup/late-fee write resolves (and, on failure, returns 500 with no `email` field at all) before any digest content is built or returned.
- Non-fatal-on-send-failure: `ping-crons.ps1 -SelfTest` (12 assertions, all passing) exercises `Invoke-CronEmailSend`'s exit-code handling — success, retry-once on exit 2/4, no-retry on exit 1/3/5, and a regression check for a real bug the whole-branch review caught (the default sender was letting `send-via-outlook.ps1`'s own stdout leak into the captured exit code, so every successful send logged as `SEND FAILED` — fixed by discarding that output stream before returning `$LASTEXITCODE`). A send failure only ever logs to `cron.log`; it never re-POSTs the cron endpoint (which would risk re-running delinquency-check's late-fee posting) or touches dedup state.
- No remaining Resend egress: `grep -rn "resend|Resend" server/ --include="*.ts"` returns only explanatory-prose matches (zero live calls); full test suite green (typecheck + `vitest run` 49 files/394 tests + build).

**Whole-branch review also caught and fixed (before deploy):** UTF-8 mojibake on the Worker-to-PowerShell response boundary (Hono's `c.json()` omits a charset; Windows PowerShell 5.1 then mis-decodes non-ASCII — same defect class `send-via-outlook.ps1`'s own header already documents from a 2026-07-24 incident); tenant PII/balances that would have landed in unrotated plaintext `cron.log` (now redacted to counts + subject only); and several stale docs (`README.md`, a `cron.ts` comment) still claiming Resend or "the ORA fleet scheduler" as the trigger.

**Real send confirmed — twice, through the actual live trigger, not synthetic:** `critical-dates-alerts` sent "[ORA PM] 10 Critical Dates — 2026-08-04" (2026-08-04 18:06:16 ET) and `delinquency-check` sent "[ORA PM] 24 Delinquent Tenants — 2026-08-04" (18:13:11 ET) — both confirmed in `send-log.txt` with correctly-rendered em-dashes (UTF-8 fix verified in real production traffic, not just a local test).

**Discovered along the way, filed separately as [OI-076](#OI-076):** the "ORA PM Crons" Windows Task Scheduler task that actually triggers these two endpoints had been unregistered on this machine since (at latest) the 2026-07-09 machine migration — `cron.log`'s last entry before this session was 2026-06-24. Re-registered and verified live; the runs above also cleared 6 weeks of backlog (10 critical-date alerts, 24 delinquent tenants, 7 late fees posted total across the catch-up runs — idempotency-protected, no duplicates). Also found and fixed in the process: `ping-crons.ps1`'s 90s client-side timeout was too tight for `delinquency-check`'s real backlog-clearing runtime (~93s measured) — bumped to 240s.

**Follow-up (not required to close this item — Gabriel to action):** revoke `RESEND_API_KEY` at Resend's dashboard directly (the code path is gone, but the live credential itself still works if called against Resend's API from outside this system entirely). Once confirmed revoked, delete the now-orphaned wrangler secrets (`wrangler pages secret delete RESEND_API_KEY` / `RESEND_FROM_EMAIL`).
**Auto-check:** none.

### OI-054
**Status:** CLOSED — **FALSE FINDING (reporting error, mine)**
**Opened:** 2026-07-30
**Closed:** 2026-08-03
**Source:** Credential-exposure sweep, 2026-07-30
**Description (as filed):** A FRED API key is hardcoded into three `api_key=` request URLs at `Claude_Workspace/00_Governance/Scheduled/_archive_2026-06-09_retired/ora-debt-maturity-snapshot/SKILL.md:16-18` (OneDrive-synced).
**Evidence (2026-08-03):** read the actual values before redacting them. All three read literally `ROTATED-DEAD-FRED-KEY-REDACTED-20260724` — an already-neutralized marker, rotated and redacted 2026-07-24, six days BEFORE the sweep that flagged them. There is no credential in this file and never was one at the time of filing.
**Root cause of the error:** the sweep matched on credential SHAPE (`api_key=` + 16+ chars) and I filed the item without reading the matched VALUE — the marker string is long and hyphenated, so it satisfies the pattern. The hash-comparison I ran the same day actually reported "0 distinct FRED keys" in this file, which contradicted the filing; I read that as "not the live key" rather than "not a key at all." **Lesson: a shape match is a candidate, not a finding — confirm the value before opening an exposure item.** Related: [[feedback_verified_null_vs_inferred_null]].
**Auto-check:** none.

### OI-055
**Status:** CLOSED (redacted 2026-08-03; searchapi revocation optional — see Evidence)
**Opened:** 2026-07-30
**Closed:** 2026-08-03
**Source:** Credential-exposure sweep, 2026-07-30
**Evidence (2026-08-03):** Gabriel ruled backup-then-redact. Applied to all 3 `.claude.json.bak-*` files in `~/archive/root-cleanup-2026-07-09/config-backups/`: **4 values** replaced with `[REDACTED-2026-08-03-OI054-055]` (3 searchapi tokens + 1 `FRED_API_KEY` env value found during the pass). Originals copied byte-intact to `config-backups/_preredaction_2026-08-03/` first, so this is reversible; all three redacted files re-verified as still-parsing JSON. The searchapi connector was removed 2026-06-02, so the token is almost certainly dead — revoking it at searchapi.io remains optional and is Gabriel's call. **The two local dev PEM keys** (`~/archive/ai-tool-cleanup-2026-07-09/.android/adbkey`, `.ollama/id_ed25519`) were deliberately LEFT AS-IS: they back no external account, redacting a private key file corrupts it for no security gain, and both are disk-local and untracked.
**Description:** Residual credentials in local archive trees: (1) a `searchapi.io` MCP token embedded in a URL across three `.claude.json` backups under `~/archive/root-cleanup-2026-07-09/config-backups/` — the searchapi connector was removed 2026-06-02; (2) two local dev private keys, `~/archive/ai-tool-cleanup-2026-07-09/.android/adbkey` (ADB) and `.ollama/id_ed25519`. All are disk-local and none is git-tracked (verified).
**Severity:** LOW. Revoke the searchapi token if that account is still live; the PEM keys back no external account and can simply stay archived.
**Auto-check:** none.

### OI-063
**Status:** CLOSED
**Opened:** 2026-08-03
**Closed:** 2026-08-04
**Source:** ora-pm appsec fix plan (subagent-driven-development execution of `plan/appsec-fixes-oi034-048`), Task 9 (OI-041/OI-042 remainder + OI-046 gap closure), commit `afef524` — self-flagged by the implementer, independently confirmed via grep by the task reviewer (not just trusted)
**Description:** OI-042 ("raw Postgres error messages returned to clients") was originally scoped across Tasks 2/7/8/9 by file, but the scoping missed 5 files entirely — no task in the 11-task plan names them, so no branch commit touches them. Confirmed still live: `properties.ts` (3 sites), `expenses.ts` (2), `payments.ts` (1), `portal-auth.ts` (2), `portal-insurance.ts` (1). Task 9 correctly declined to silently expand its own scope to cover these — same discipline as OI-060's filing.
**How to apply:** route each site through `dbError(c, error, publicMsg?)` (`server/lib/api-error.ts`, shipped by Task 7 of the same branch) — mechanical, same pattern as every other file in the branch. Low risk, no schema/logic changes needed, just the error-response swap. Should extend `tests/lib/no-raw-db-errors.test.ts`'s tripwire (same branch, Task 9) to cover these 5 files once fixed, closing the allowlist gap that currently excludes them.
**Evidence (2026-08-04):** a REFUTE pass re-verifying a later commit (`8fb7022`, whose title claimed "dbError sweep") found it had NOT touched any of the 5 self-flagged files despite the title — confirmed still-open via `git diff` (empty on all 5 files) before writing anything. Fixed all 9 sites (TDD — RED test per site asserting a generic message + no leak of the injected raw error text, written before the fix) through `dbError()`, matching the established pattern exactly; `properties.ts`'s single-record 404 lookup kept a plain generic 404 (mirroring `tenants.ts`'s own documented exception, since `dbError()` always 500s). Tripwire allowlist entries for all 5 files removed; the "fully clean" pinned assertion extended to cover them. Fixed on `ora-pm` main, commit `7857646` + merge `a29f8f0`. 402/402 suite green at the time, typecheck clean.
**Auto-check:** none.

### OI-069
**Status:** CLOSED
**Opened:** 2026-08-03
**Closed:** 2026-08-04
**Source:** REFUTE pass on the [OI-046](#OI-046) fix (security-auditor dispatch), 2026-08-03; verified directly by the Code-surface session that merged it
**Severity:** MEDIUM (financial correctness — silent under-billing, not exploitable by an outside party)
**Description:** `server/routes/cam.ts` (OI-046's fix, commit `81b5626`). The new insert-first
idempotency key is `cam_true_up:<lease_id>:<year>` — scoped only to lease+year, no amount or
recalculation-version component. `POST /calculate` upserts on `(lease_id, reconciliation_year)` and
unconditionally resets `status` to `draft` even if the reconciliation was already `billed` (this reset
behavior predates OI-046's fix). Scenario: a CAM recon bills at $500, ops later corrects and re-runs
`/calculate` for the same lease/year at $700, the recon flips back to `draft`, an admin re-approves.
The new charge insert (amount $700, same idempotency key as the old $500 charge) collides on the
unique constraint from the OLD charge — indistinguishable at the DB layer from "concurrent duplicate,"
so it's treated as a no-op. Status still flips to `billed` and the handler returns `{success:true,
true_up_amount:700}`, but the tenant's ledger still only shows the stale $500 charge — the $200
correction is silently dropped, with a success response implying it went through.
**Candidate fix (NOT applied):** either (a) key `idempotency_key` off a recalculation version/hash
(e.g. include the computed amount, or a monotonic recalc counter) instead of just lease+year, or (b)
have `/calculate` refuse to silently reset an already-`billed` recon to `draft` without an explicit
"supersede"/override flag that a human consciously sets. Either way, add a test for the
recalculate-then-reapprove path — not covered by OI-046's test suite (verified: only sequential
re-approval and a directly-injected constraint violation are tested, not this scenario).
**Evidence (2026-08-04):** a later commit (`8fb7022`) claimed "OI-046 gap closure" in its title, but
`git diff` against `cam.ts` confirmed it was empty — that commit's "charges idempotency-key default"
was an unrelated fix in `charges.ts` (OI-039's NOT NULL backfill), not this item; verified directly
rather than assuming from the commit message alone. Fixed via approach (b): `/calculate`'s update is
now atomically conditional (`.eq('lease_id',x).eq('reconciliation_year',y).eq('status','draft')`) — the
same "conditional update IS the concurrency control" idiom OI-046 already established on
`/:id/approve`, applied here instead of a separate check-then-act pre-check (a first REFUTE pass on an
earlier version of this fix found a check-then-act pre-check still raced against a concurrent
`/:id/approve`: a real TOCTOU window, not theoretical, closed by making the write itself the guard).
Zero rows matched falls through to an insert (first-ever calculation); an insert conflict means a row
already exists, read once to distinguish "won a first-time-calc race" (retry the update) from
"already billed/collected" (409, reject). Allow-list (`status='draft'`), not a deny-list against
`'billed'` — a second REFUTE pass found the original deny-list would have silently reopened a
`'collected'` reconciliation too (a third legal status per the DB's own CHECK constraint, currently
unreachable but latent); fixed and pinned with a regression test. Financial-decision code: 2 REFUTE
passes (security-auditor dispatch). Fixed on `ora-pm` main, commit `f0b6780` + merge `a29f8f0`.
409/409 suite green at the time, typecheck clean.
**Auto-check:** none.

### OI-067
**Status:** CLOSED (verification done; underlying fix filed separately as [OI-071](#OI-071))
**Opened:** 2026-08-03
**Closed:** 2026-08-03
**Source:** ora-pm appsec fix plan Task 11 (OI-048), local `plan/appsec-fixes-oi034-048` branch, commit `9aa7f30`
**Severity:** HIGH (was: status UNKNOWN, needed urgent human production verification)
**Description:** see the Open-table one-liner above (unchanged) for the original finding —
`PortalInsurance.tsx` uploads keyed by `session.user.id`, but the `tenant_upload_insurance` RLS policy
checks the folder against `tenants.id`, a structurally different UUID. Two live consequences couldn't
be distinguished from the repo alone: (a) uploads silently failing (broken feature), or (b) a
more-permissive out-of-band policy exists that isn't in the migrations.
**Evidence — verified directly against production, 2026-08-03 (Gabriel signed into the Supabase
dashboard; ran `scripts/verify-rls.sql` in the live SQL Editor, not simulated):** Production database
was found PAUSED (Supabase free-tier auto-pause, unrelated to this finding) — Gabriel resumed it
in-turn before this verification could run. All three parts of the script pass cleanly: **Part 1** —
all 6 expected tables (`charges`, `payments`, `lease_documents`, `lease_amendments`, `tenant_notices`,
`insurance_certificates`) have `rowsecurity = true`. **Part 2** — all 10 expected policies exist,
including all 3 `storage.objects` policies from the out-of-band 0008 migration
(`tenant_upload_insurance`, `tenant_read_insurance`, `tenant_read_lease_docs`) — confirmed live, and
the `tenant_upload_insurance` `with_check` expression text matches the migration file exactly. **Part
3** — zero undocumented policies (`0 rows`). This **rules out scenario (b)**: the policy is exactly as
documented, not more permissive. **Scenario (a) is confirmed**: since the policy correctly requires
the storage folder to equal `tenants.id` (via a `tenants.auth_user_id = auth.uid()` join) and the
client code uploads to `session.user.id` instead, every real COI upload through this page fails RLS
today — a broken feature, not a data exposure.
**Bonus finding, out of this item's original scope:** while in the dashboard, Supabase's own Security
Advisor surfaced a live CRITICAL flag — `public.units` has RLS disabled entirely. Confirmed directly
(`rowsecurity = false`). Not investigated further (unclear whether `units` is ever queried
client-side with the anon key, the same way `tenants` also shows `false` but is server-only-accessed
per [OI-048](#OI-048)'s finding that all API routes use the service-role key) — flag for Gabriel to
triage, not filed as its own OI item pending that check.
**Auto-check:** none.

### OI-073
**Status:** CLOSED
**Opened:** 2026-08-04
**Closed:** 2026-08-04
**Source:** Applying migrations 0009-0011 to ora-pm production, 2026-08-04
**Severity:** MEDIUM (tooling blind spot, not a live defect)
**Description:** ora-pm's production `supabase_migrations.schema_migrations` tracking table is stalled at
version 0007 and has been for some time — but this does NOT mean migrations after 0007 were never applied.
While applying 0009 (`ar_ledger` cartesian-fan-out fix), the `CREATE OR REPLACE VIEW` failed with
`42P16: cannot drop columns from view` — because production's live `ar_ledger` already carried
`property_name` (0010's addition). `pg_get_viewdef('ar_ledger'::regclass, true)` confirmed the live view is
byte-for-byte 0010's CTE-based definition. So 0009 and 0010 were both already applied to production, out of
band, sometime before this session, without ever being recorded in the tracking table. 0011 was genuinely
absent (confirmed via `pg_indexes`/`information_schema.columns` before applying) and has now been applied —
see [OI-039](#OI-039)'s Evidence. `0008_storage_rls.sql` has the same self-described out-of-band-via-Node-script
history (see [OI-048](#OI-048)'s Compounding note), so this is at least the second migration to land this way.
**Why this matters:** the tracking table is the thing anyone (including a future session, or `supabase db
push`) would consult to answer "is migration N live in prod?" — and for at least 3 of the last 4 migrations,
the honest answer was "check the actual schema, not the tracker." A future automated migration run that
trusts the tracker could attempt to re-apply 0008/0009/0010, which would fail loudly (as 0009 just did) rather
than silently — so the immediate blast radius is low — but the root cause (whatever process applies migrations
out-of-band never writes the tracking row) is still live and will produce the same confusion on the next
migration.
**Evidence (2026-08-04):** Gabriel ruled "backfill now." Confirmed table structure first
(`information_schema.columns`: `version text NOT NULL`, `name text`, `statements text[]`) and the existing
naming convention (`name` = filename slug minus version prefix/extension, e.g. `0007` -> `stripe_webhook_events_fix`).
Ran `INSERT INTO supabase_migrations.schema_migrations (version, name) VALUES ('0008','storage_rls'),
('0009','fix_ar_ledger_view'), ('0010','ar_ledger_property_name'), ('0011','appsec_idempotency_and_scale');`
— succeeded. Re-queried: tracker now shows 11 rows, 0001 through 0011 contiguous, matching the actual live
schema for the first time. `statements` left NULL for the backfilled rows (nullable column; these were applied
outside the CLI's normal statement-splitting path, so there is nothing authentic to populate it with).
**Residual, not closed by this backfill:** the root cause — whatever process applies migrations out-of-band
never writing the tracking row — is unidentified and still live. The next migration applied the same
undocumented way will reopen this same gap. Gabriel has not yet named or changed that process.
**Root cause identified + fixed 2026-08-04 — see [OI-074](#OI-074):** the actor is any Code session applying
a production migration; the process is manual application via Claude-in-Chrome → Supabase Dashboard SQL
editor (or an ad-hoc Node script) because the Code sandbox has no `SUPABASE_ACCESS_TOKEN` configured, so
`supabase db push`/`migration up` — the only commands that auto-write the tracking row — cannot run here.
**Auto-check:** none.

### OI-076
**Status:** CLOSED
**Opened:** 2026-08-04
**Closed:** 2026-08-04
**Source:** OI-047 final whole-branch review, 2026-08-04
**Severity:** MEDIUM (operational — real financial/notification impact, not just tooling)
**Description:** ora-pm's `critical-dates-alerts`/`delinquency-check` cron endpoints are triggered by a standalone Windows Task Scheduler task, "ORA PM Crons" (Interactive logon, daily 9:00 AM, runs `C:\Users\Owner\ora-pm-cron\ping-crons.ps1` — NOT the Claude dual-fleet `create_scheduled_task` registry, so it's invisible to `fleet-status.py`/`registry-membership-probe.py`). `Get-ScheduledTask -TaskName 'ORA PM Crons'` returned nothing — the task did not exist on this machine. `cron.log`'s last entry was 2026-06-24T09:00:03 (a DNS-resolution error), six weeks before this discovery. Root cause: scheduled-task registrations are OS-level, not files — the 2026-07-09 machine migration to LAPTOP-CSHSCBE6 (per session context: "both fleets already live here") copied the `ora-pm-cron` folder and script but never re-ran `register-task.ps1` on the new machine, so the registration itself was silently lost while the file evidence of it (the script, the log, the register script) looked completely intact.
**Real impact:** critical-date alerts (lease expirations, insurance, etc.) and — more materially — late-fee posting on overdue tenant balances did not run for ~6 weeks.
**Fix:** re-ran `register-task.ps1`; confirmed via `Get-ScheduledTaskInfo` (`State: Ready`, `NextRunTime` set to the next 9:00 AM). Corrected `register-task.ps1`'s own header comment, which claimed S4U logon while the code actually registers `-LogonType Interactive` (cosmetic, but worth fixing while already re-registering), and added a note there so a future machine migration checks `NextRunTime`, not just that the folder exists.
**Backlog cleared same-day, real production runs (not synthetic tests):** `critical-dates-alerts` — 10 new alerts, sent. `delinquency-check` — 24 delinquent tenants, 7 late fees posted total across two runs (idempotency-key protected — the second run's figures reflect fees the first run's client-side timeout prevented it from confirming, not duplicate postings), sent.
**Residual, not closed by this item:** whether any OTHER host-level scheduled task (outside both Claude fleets AND this one) has a similar migration-survival gap is unchecked — this item covers `ora-pm-cron` only, discovered incidentally during OI-047's final review, not from a systematic audit of non-Claude Windows Task Scheduler entries on this host.
**Auto-check:** none.

### OI-106
**Status:** CLOSED
**Opened:** 2026-08-09
**Closed:** 2026-08-09
**Source:** L5 research triage of [[reference_concurrent_session_duplicate_hardening_work]]'s
2026-08-05 entry (three same-day duplicate-investigation near-collisions)
*Section reconstructed 2026-08-11 from this item's table row (OI-098 class (ii)/(iii) back-fill). The row was the only record; no fact here is new except where explicitly dated 2026-08-11.*

**Description:** `engineering-router.py` now appends a fail-open, ASCII-only advisory — *"N other
session(s) active -- check list_sessions/event_log.md before duplicating investigation or analysis
work"* — to any prompt that already fires a lane suggestion, using the existing
`session_liveness.other_active_sessions()` reader.

**Why the router and not `claim_work.py`:** the collision shape here is one that
`claim_work.py`'s four fixed slugs **structurally cannot catch** — no file was ever in contention
until the duplicate work had already been done. Task start, where the router runs, is the only point
where the warning can still change the outcome.

**Rejected in the same triage (do not re-propose without new evidence):**
- broadening `claim_work.py`'s file-claim model — nothing was ever claimable in the two triggering
  incidents;
- a pre-commit `git status` hook — redundant with `shared-checkout-guard.py`, which already caught
  the third incident live.

**Evidence (as recorded at closure):** built in an isolated worktree; `eos-review-gate` blocked the
first commit as designed; independent review (pinned `claude-fable-5`) found 2 Important defects — a
misleading test comment, and a missing `isinstance(sid, str)` guard that would have let a payload with
no `session_id` count itself as an "other" session — both fixed pre-merge. 37/37 `hooks/tests` green
pre- and post-merge. Merged to `main` @ `4066213` (Gabriel confirmed in-turn), pushed to the backup
remote `ZeOoba/ora-claude-config`.

**Evidence re-verified 2026-08-11 (this back-fill), three ways:**
1. commit `4066213` exists, message *"Merge claude/engineering-router-session-advisory:
   concurrent-session advisory in engineering-router.py"* — matches the recorded description;
2. it is reachable from `remotes/origin/main`, confirming the push to the backup remote landed
   (local `main` does not contain it, which is consistent with [OI-112](#OI-112) — the shared checkout
   is parked on another branch — and is not a contradiction);
3. the advisory string is present in `hooks/engineering-router.py`, and **was directly observed
   firing** in this session's own `UserPromptSubmit` hook output ("10 other session(s) active").
   First-hand confirmation the shipped behaviour is live, not merely merged.

### OI-197

**Status:** CLOSED 2026-08-21 — both fixes built
**Opened:** 2026-08-21 · **Source:** Cross-repo architecture-diagram review (`repo-architecture-review`, Gabriel-directed)

**Description:** **MEDIUM - circular monitoring dependency across scheduler substrates.** ORA's automation now runs on FIVE distinct substrates: the cc/MCP fleet, the lams/Cowork fleet, Windows Task Scheduler (7 live ORA-owned tasks), GitHub Actions cron (2 workflows in `ora-cowork-watchdog`), and a systemd timer asserted in `ora-cowork-watchdog`'s README (see [OI-198](#OI-198)). `automation-health-monitor` enumerates two of the five. The specific structural defect: the off-fleet Windows task `ORA Command Center - Mirror Deploy` (hourly, registered 2026-07-08, runs `oxford-command-center/scripts/deploy-mirror.ps1`) has its failure classification performed by `ora-command-center-mirror-drift-check` - a cc-FLEET task (`40 10 * * 1-5`). The monitor for the off-fleet automation lives on the fleet, so any fleet pause blinds the watcher for precisely the automation that keeps running through the pause.

**Evidence (all 2026-08-21):**
- `fleet-status.py`: every task in BOTH registries shows `EN=OFF`; latest LAST RUN across the fleet is `2026-08-17T18:23:46`; "of which last 24h 0". `ora-routine-pause-resume-08-21` and `ora-lams-routine-resume-08-21` (one-time `@2026-08-21`) both show `NEVER`.
- `~/.claude/scheduled-tasks/_shared/send-log.txt`: `2026-08-20T12:07:34-04:00 [OK] Sent ... subject="[ORA Command Center] Mirror deploy FAILED"`.
- `Get-ScheduledTaskInfo 'ORA Command Center - Mirror Deploy'`: `LastRunTime 8/21/2026 4:00 PM`, `LastTaskResult 3221225786` (0xC000013A, terminated).
- `oxford-command-center/data/_state/mirror-deploy-beacon.json`: `status:"running"`, `finishedAt:null`, `startedAt:2026-08-21T16:00:02`, `pid:35692`; `Get-Process -Id 35692` returns nothing.
- `scripts/lib/deploy-beacon.ps1:12` documents this exact shape as the intended alarm signal ("absence of the finish record IS the signal") - the design is correct; only its consumer is offline.

**Not a silent failure:** `deploy-mirror.ps1` sends its own Outlook COM failure alert independently of the fleet, and that path demonstrably worked on 2026-08-20. What is lost is the redundant classifier, and the general property that a fleet pause silently narrows monitoring coverage on the surviving substrates.

**Fix direction:** either (a) move the mirror-deploy classifier off the fleet (GitHub Actions, alongside the existing `ora-cowork-watchdog` off-box pattern, which was built for exactly this reason), or (b) have `automation-health-monitor` enumerate all five substrates rather than the two fleet registries. Registering NEW unattended automation is a Gabriel decision, not an audit consequence - surfaced as a choice, not flipped on.

**Progress 2026-08-21 (repo-architecture-review remediation) — fix (b) built as WO-4:** `automation-health-monitor` v1.6 adds a read-only Step 1.75 enumerating the Windows Task Scheduler and GitHub Actions substrates (`ora-skills` commit `1aec229`). This restores VISIBILITY across all five substrates during a normal run, but does **not** fix the structural circularity itself — during a full fleet pause, `automation-health-monitor` is itself a fleet task and goes dark along with the classifier it's now also watching, so the pause-blind-spot this item exists for is unchanged. **Fix (a) — moving the mirror-deploy classifier off-fleet onto GitHub Actions — remains open and is the one that actually survives a pause; still Gabriel's call**, not built or auto-registered here.

**Progress 2026-08-21 (later same session) — fix (a) built, closes the circularity:** Gabriel confirmed building it. Scoped to native Windows Task Scheduler rather than GitHub Actions (the originally-proposed substrate) — a GitHub Actions layer needs a Notion beacon written by a native script, which needs a Notion integration token provisioned for that script, which is its own decision not rushed the same day `CRON_SECRET` was rotated (see [OI-162](#OI-162)'s near-miss). A purely native task already fully solves THIS item's specific circularity (a fleet pause doesn't affect native Windows tasks at all), so the GitHub Actions/Notion layer is deferred as a nice-to-have third layer, not a blocking gap.

Built: `oxford-command-center/scripts/mirror-classify-offfleet.ps1` (runs the same tested `mirror-run-classify.ps1` the fleet task uses, alarms on `ALARM_*` verdicts / `aheadFlag` ESCALATE / stale `LastRunTime` during business hours, alerts via the same standalone Outlook COM path `deploy-mirror.ps1` already proves works outside any Claude session) + `register-mirror-classify-offfleet-task.ps1` (weekday 10:40 AM ET, matching the fleet task's cadence). Registered as native task `ORA Mirror Deploy Classifier`, commit `ff31042`, pushed. Test-verified against a real in-flight deploy: correctly returned `RUN_IN_PROGRESS` with no false alarm.

**Bonus finding, not fixed here:** that test run took ~5 minutes. `mirror-run-classify.ps1` itself (shared, pre-existing, tested production code used by both the fleet task and this new one) is slower than a periodic check should need — likely a `Get-WinEvent` query without an efficient filter. Worth a look separately; `ExecutionTimeLimit` on the new task is set generously (15 min) so a slow run doesn't self-terminate, not as an endorsement of the runtime.

**OI-197 CLOSED — both the visibility gap (b) and the structural circularity (a) are fixed.**

**Related:** [OI-121](#OI-121) (fleet enumeration bound to one registry), [OI-162](#OI-162) (the ora-pm off-fleet migration that established the on-fleet-is-better precedent), [OI-198](#OI-198).

---

### OI-198

**Status:** CLOSED 2026-08-21
**Opened:** 2026-08-21 · **Source:** Cross-repo architecture-diagram review (`repo-architecture-review`, Gabriel-directed)

**Resolution:** Corrected via the GitHub Contents API (no local clone of this repo exists by design — `gh api repos/ZeOoba/ora-cowork-watchdog/contents/README.md` PUT, commit `edde3087`). The Dependencies section now states the producer still runs as a LAMS/Cowork scheduled task (`ora-cowork-heartbeat`, `50 5 * * *`) as of 2026-08-21, and reframes the systemd-timer path as an unbuilt V2 intention rather than a described dependency. Also added a `<!-- diagram-verified: 2026-08-21 -->` stamp (WO-3). Byte-level verified post-push (UTF-8 em-dashes intact, no encoding corruption from the base64 round-trip). Whether an ORA Linux server exists anywhere else was NOT verified either way — not asserted in the fix, left open for OI-197 if it ever surfaces as a real sixth substrate.

**Description:** **LOW-MEDIUM - dead path documented as live.** `ora-cowork-watchdog/README.md`, Dependencies section, states as fact: "per an in-code comment this producer is moving from a desktop LAMS scheduled task to a systemd timer on the ORA Linux server (`ora-claude-config/server/heartbeat.py`), and this watchdog intentionally stays on GitHub Actions as the off-box monitor rather than moving onto the server it watches."

**Evidence (2026-08-21):** `Test-Path 'C:\Users\Owner\.claude\server\heartbeat.py'` -> `False`. `gh api repos/ZeOoba/ora-claude-config/contents/server` -> `404 Not Found`. `ora-claude-config`'s own README section 3 directory table lists no `server/` entry. `fleet-status.py` still shows `ora-cowork-heartbeat` on the `lams` fleet (`50 5 * * *`, last run `2026-08-17T13:45:22`) - i.e. the producer never left the desktop scheduler.

**Why it matters:** this is the producer end of the dead-man chain (`ora-cowork-heartbeat` -> Notion page `35c6ecd8...` -> GitHub watchdog). A README that describes the producer as migrating to an unbuilt Linux/systemd path invites a future session to go looking for a server that does not exist, or to assume the migration is done and stop maintaining the LAMS task.

**Fix direction:** correct the README to describe the producer as it actually runs today, and if the systemd migration is still intended, record it as a V2 intention rather than a described dependency. If an ORA Linux server does exist and hosts the producer somewhere else, that location needs documenting - it would be a sixth scheduler substrate (see [OI-197](#OI-197)).

---

### OI-199

**Status:** CLOSED 2026-08-21 (archived on GitHub, Gabriel's call)
**Opened:** 2026-08-21 · **Source:** Cross-repo architecture-diagram review (`repo-architecture-review`, Gabriel-directed)

**Resolution:** Gabriel chose (a) - dormant, archive. `gh repo archive ZeOoba/Internal-Accounting-App --yes` run; `gh repo view --json isArchived` confirms `true`. QuickBooks Desktop remains the source of record for internal accounting; `gh repo list --json isArchived` is now self-documenting for this repo, closing the audit-coverage hole legitimately rather than leaving it silently unscanned.

**Description:** **LOW (dormant) - permanent audit coverage hole.** Of the 10 repos under `ZeOoba`, `Internal-Accounting-App` is the only one with no README, no architecture diagram, and no local clone. `gh api repos/ZeOoba/Internal-Accounting-App/readme` returns `404`; `C:\Users\Owner\Internal-Accounting-App` does not exist. Last updated `2026-06-04T03:22:43Z`.

**Why it matters:** its GitHub description states the intent plainly - replace QuickBooks Enterprise for a 2-person company with ~20 LLCs and automate internal accounting, bookkeeping, and financial reporting. That is the highest financial-consequence domain in the portfolio, and it is the single repo `repo-architecture-review` cannot see anything about. Every future run of this skill is structurally blind here, and will silently report "9 repos reviewed" as though that were complete.

**Fix direction:** a binary decision, not a code change. Either (a) it is dormant/abandoned -> archive the repo on GitHub, which makes `gh repo list --json isArchived` self-documenting and removes it from this skill's scope legitimately; or (b) it is still live intent -> clone it locally and give it a README with a data-flow diagram, at which point it enters the audit surface normally. QuickBooks Desktop remains the source of record either way (User Preferences, Tools & data).

---

### OI-200

**Status:** CLOSED 2026-08-21 (both halves resolved)
**Opened:** 2026-08-21 · **Source:** Cross-repo architecture-diagram review (`repo-architecture-review`, Gabriel-directed)

**Resolution:** (1) Primary's unpushed commits: by the time this was actioned the primary had grown from 2 to 5 commits ahead (3 more landed same-day: an AR ingestion, a snapshot regen, an insurance/warehouse fix — all Gabriel-authored/co-authored, sequential on `main`, working tree clean). The tax-recapture commit (`07bd362`) was verified before push — Gabriel's own sourced data correction (Talbot County Citizen Self Service portal + MLS/APN cross-match for Howard County jurisdiction), arithmetic re-checked ($5,564.00+$6,048.64+$8,239.00+$8,956.64=$28,808.28, exact). Pushed `git push origin main` (`58da3a4..9da7c8c`, fast-forward); the `prepush-noi-crosscheck` gate passed. The tax recapture will be live in the next mirror-deploy cycle. (2) `oxford-command-center-1`: confirmed clean (`git status --porcelain` empty, HEAD `58da3a4` = `origin/main`, no unique content), moved to `C:\Users\Owner\_archive-non-onedrive\oxford-command-center-1-stray-clone-20260821\` per the archive-not-delete convention (matches the existing `onedrive-stale-ora-pm-clone-20260709` precedent in that same folder). `-deploy-build` untouched (intentional, `Sync-DeployBuildRoot`-managed). WO-2 (below) adds stray-clone discovery to `dirty-tree-triage` so this class is caught by tooling next time.

**Description:** **LOW-MEDIUM - stray third writable clone of the financial repo.** Three separate working copies of `ZeOoba/oxford-command-center` now sit on `C:\Users\Owner`:

| Path | Created | HEAD | Branch | State |
|---|---|---|---|---|
| `oxford-command-center` | (primary) | `07bd362` | `main`, ahead 2 | dirty (`M data/snapshots/portfolio.json`, `?? data/ar/inbox/`) |
| `oxford-command-center-1` | 2026-08-20 13:34 | `58da3a4` | `main` | clean, referenced by nothing |
| `oxford-command-center-deploy-build` | 2026-08-16 15:54 | `58da3a4` | detached HEAD | managed by `Sync-DeployBuildRoot` (intentional) |

**Evidence (2026-08-21):** `Select-String` across `oxford-command-center/scripts/*.ps1` and `~/.claude/maintenance/*.{ps1,py}` for `oxford-command-center-1` returns zero hits, while `-deploy-build` is explicitly created and isolated by `scripts/lib/deploy-buildroot.ps1` (`Get-DeployBuildRoot` / `Assert-BuildRootIsolated`). The `-1` suffix is the shape a re-`git clone` into an occupied path produces.

**Two distinct problems:**
1. `-1` is an unowned writable copy of a repo whose `config/` holds ratified scorecard rulesets and whose `data/` holds the warehouse - editing it produces work that can never merge and never deploys. `dirty-tree-triage`'s roster (`~/.claude`, `ora-skills`, `website-canonical`, `oxford-command-center`) does not cover it.
2. The primary clone holds 2 commits not on `origin/main` - `0e60d02` (merge) and `07bd362` ("fix(taxes): recapture 29000 Info Lane 2025 Talbot Lot 4 bill, confirm 9050 Red Branch jurisdiction", 2026-08-17). `deploy-mirror.ps1` correctly builds from `origin/main` via `Sync-DeployBuildRoot -Ref 'origin/main'` (the 2026-07-09 stale-checkout incident is genuinely fixed), which means that tax recapture has been absent from every mirror deploy for four days and will stay absent until it is pushed.

**Fix direction:** push or discard the primary's 2 commits (normal `dirty-tree-triage` lane), then delete or `_archive/`-move `-1` once confirmed it holds nothing unique (`git -C oxford-command-center-1 status --porcelain` was empty at audit time, so it likely holds nothing). Add `-1`-style stray clones to `dirty-tree-triage`'s discovery so this is found by tooling next time, not by an audit.

---

### OI-201

**Status:** CLOSED 2026-08-21
**Opened:** 2026-08-21 · **Source:** Cross-repo architecture-diagram review (`repo-architecture-review`, Gabriel-directed)

**Resolution:** All three errors fixed in `ora-pm` commit `c311da7` (`docs(readme): fix stale scheduler/deploy sections`). Mermaid + prose now name `ora-pm-monthly-billing` and `ora-pm-daily-crons` on the CC/MCP fleet instead of Windows Task Scheduler. Deploy section corrected to `.github/workflows/ci.yml` → `wrangler pages deploy`; **the Pages Git-integration question raised in this item was checked, not just doc-fixed** — `wrangler pages project list` shows `Git Provider: No`, confirming a single deploy path, no race. Monthly-billing is no longer describable as untriggered — see [OI-162](#OI-162) (closed same session, trigger registered). Added a `<!-- diagram-verified: 2026-08-21 -->` stamp (WO-3). Landed via a merge with a genuine concurrent fork on `main` (`517a759`/`aede030`, the OI-078/079/080/081 RLS/MFA fix, merged via PR #23 outside this session) — reconciled with `git merge` (clean, no conflicts), 471/471 tests pass, typecheck clean, pushed and CI-deployed (`ca62ecb`).

**Description:** **MEDIUM - stale architecture diagram on a money-moving path.** `ora-pm/README.md` is the input this skill (and any future session) reads to understand how ora-pm's billing actually fires, and it is wrong in three places, all on the cron/billing path:

1. **The diagram's scheduler node still reads** `Windows Task Scheduler (two separate tasks, no ORA fleet involved)` and names `ping-crons.ps1` as the daily driver. Since [OI-162](#OI-162) (2026-08-16) the daily half runs as `ora-pm-daily-crons` on the cc fleet (`40 9 * * *`, last run `2026-08-17T14:20:18`) and the standalone "ORA PM Crons" Windows task is `Disabled` (confirmed `Get-ScheduledTask`, 2026-08-21, `LastTaskResult 2147943467`).
2. **The prose asserts** `scripts/trigger-billing.ps1` "POSTs to `/api/cron/monthly-billing` on the 1st of the month." No such trigger exists anywhere: no matching Windows Task Scheduler entry (full non-Microsoft task enumeration, 2026-08-21) and no `monthly-billing` task in either fleet registry (`fleet-status.py`). This is the still-open half of [OI-162](#OI-162), restated here only because the README presents it as working. **Next billing date is 2026-09-01, 11 days out.**
3. **The deploy section** describes Cloudflare Pages building from the Git integration with `npm run build`. `.github/workflows/ci.yml` actually runs typecheck -> test -> build -> `npx wrangler pages deploy ./dist --project-name ora-pm` on push to `main`. (The gate itself is fine - tests DO run before deploy, unlike the README's implied path. Worth confirming the Pages Git integration is disconnected, or two deploy paths race.)

**Why it matters as an architecture finding rather than a doc nit:** `repo-architecture-review` exists because ORA repos keep their diagrams current as a maintenance norm, and reads them instead of re-deriving structure. A diagram that misstates which scheduler fires a billing run is the failure mode that premise cannot survive. The 2026-08-16 remediation changed the system and did not change the picture of it.

**Fix direction:** update the mermaid scheduler node and the "Cron jobs have no native Cloudflare Pages trigger" paragraph to current reality, and mark monthly-billing explicitly as UNTRIGGERED rather than describing a schedule it does not have. Normal lane triage - `/build` or a docs-scoped commit in `ora-pm`; no gate implications.

**Related:** [OI-162](#OI-162) (parent, monthly half still open), [OI-076](#OI-076), [OI-047](#OI-047).
| [OI-288](#OI-288) | 2026-09-12 | 2026-09-30 | `ora-am-brief` Block B, 2026-09-12 run — `notion-create-pages` against Ops Hub (page `32b6ecd8`) | **CLOSED 2026-09-30** — Gabriel upgraded the Notion workspace to Plus (stated in chat 2026-09-30). Live-verified the same day: `notion-create-pages` succeeded, creating a private draft page (`3eb6ecd8-9e59-8161-838b-fffb56dc4235`, titled "OI-288 block-cap verification 2026-09-30 (safe to delete)"), the exact call the free-plan cap refused. Per this row's own 2026-09-18 correction a paid plan removes the cap; the degraded-mode state file was already `active:false`. NOT mechanically checked: that the paid plan survives its first billing cycle (`ora-notion-trial-expiry-reminder` fired 2026-09-29 and is spent). History below is unchanged. **HIGH (fleet-wide Notion write outage, distinct from the already-debunked "query quota" gate) — the ORA Notion workspace has exhausted its FREE-PLAN block-count allowance, so EVERY `notion-create-pages` call fails with `"Your workspace has used all of its free blocks. Upgrade your plan to create more content."`, not just this task's.** Confirmed distinct from [[reference_tenant_db_cache_and_notion_quota_myth]]'s finding (that one is an `entitlement_required` gate on `notion-query-data-sources` SQL mode, and a plan upgrade fixes nothing there) — this is a genuine content-storage ceiling on `notion-create-pages`/`notion-create-database` block creation, and a plan upgrade (or freeing existing blocks) is the actual fix. Retried once per `daily-brief`'s own publication guard; failed identically both times, so this is not transient. Blast radius: every scheduled task that posts a Notion page — `ora-am-brief` Blocks B/C/D, `ora-pm-ledger`, `automation-health-monitor`, `ora-master-workbook-ingest`'s dashboard refresh, and more — will hit the same wall the next time each runs, though most have an email-fallback publication guard (as `ora-am-brief` demonstrated live today: brief delivered via Outlook COM instead, subject "ORA Daily Brief PUBLICATION FAILED - 2026-09-12"). `notion-update-page`/`notion-search`/`notion-fetch` (updates to EXISTING pages, reads) are unaffected — only NEW block/page creation is blocked. **CORRECTED 2026-09-18 (verbatim, notion.com/help/understanding-block-usage):** deleting/archiving/emptying trash does NOT free blocks — the count is cumulative blocks ever created since signup, not current live content; Notion’s own FAQ: “No, deleting content does not reduce your block count or free up additional blocks. Once your workspace has created 1,000 blocks, it will experience restrictions — regardless of subsequent deletions.” The ONLY fix is upgrading to a paid plan (Plus $10/seat/mo removes the cap entirely). Confirmed broader-scope 2026-09-18: blocks core ora-am-brief deliverables, not just this row’s Rate History log; see [[reference_notion_free_block_quota_exhausted_2026-09-12]] for the full writeup and dark-producer inventory. **MITIGATED 2026-09-18 (not closed — see caveat):** Gabriel started a 14-day Notion paid-plan trial; live-verified same session, notion-create-pages succeeded creating a test page under Ops Hub (3df6ecd8-9e59-81f4-a31e-e56de97ae737). Workspace confirmed to have exactly 2 human members (Gabriel + Eric Goldberg) via notion-get-users, matching the free-plan 2+-owner trigger. **Do not close this item** — the trial expires ~2026-10-02 (14 days from 2026-09-18; unconfirmed exact date, check Notion billing) and the cap returns fleet-wide if not converted to a paid tier before then. notion-publish-degraded.json set to active:false with a trial_expiry_risk flag for the next session to re-check before that date |

---


| ID | Opened | Closed | Source | One-line |
|----|--------|--------|--------|----------|
| [OI-188](#OI-188) | 2026-08-17 | 2026-09-21 | Tax & Settlement systemization sprint (Cowork session, project "Taxes + Settlement Statements"), handed to Code for `settlement-basis-extraction` skill authoring | **CLOSED 2026-09-21 (folded into [OI-335](open-items-tracker.md#OI-335) by Gabriel's decision)** — one owner for the 2900 Loch Raven related-party question. The county is Wicomico (Salisbury MD), not Baltimore City; the missing historical tax record for 2203-2207 Northwood (10 property folders scanned, this the only empty one) moved into OI-335 as a sub-item needing a live county-portal pull. |
| [OI-192](#OI-192) | 2026-08-17 | 2026-09-21 | Tax & Settlement systemization sprint (Cowork session, project "Taxes + Settlement Statements"); gap-check pass on the Code handoff | **CLOSED 2026-09-21** — chain of title documented, not a break: `5600 Sunnyside Ave\Deed of Conversion -- GDG & CRG to 5600 Sunnyside Ave LLC 05-2014.pdf`, a no-consideration deed dated 05/12/2014, recorded 05/27/2014 in Prince George's County (exempt under Tax-Property §12-108(bb)), from Gerald D. and Carol R. Goldberg to 5600 Sunnyside, LLC, reciting the 1992 deed (Liber 8347 Folio 157). Residual (tax character of the 2014 conversion; partnership or disregarded before the 02/2025 sale) moved to [OI-336](open-items-tracker.md#OI-336) #27. |
| [OI-187](#OI-187) | 2026-08-17 | 2026-09-21 | Tax & Settlement systemization sprint (Cowork session, project "Taxes + Settlement Statements"), handed to Code for `settlement-basis-extraction` skill authoring | **CLOSED 2026-09-21** — resolved from the Corporate and Settlement folder, not a cleaner scan: `3034 Westerville Rd\` holds a text-layer ALTA statement and the signed scan. Contract price $1,652,400.00 (borrower 5242 Angola Road, LLC; seller Able Roofing LLC; settled 09/19/2024), earnest deposit $100,000.00, "Acquisition Funding from IPX 1031" $1,559,267.54, no loan, borrower total $1,659,267.54; buyer-paid capitalizable charges about $6,383.25, indicated cost near $1,658,783.25 [derived]; 1031 replacement property, so tax basis is carryover. Fact base `3034-westerville.json` updated. The 3034 fields feed OI-190 (Form 8824 and the three-parcel exchange), which stays open. |
| [OI-317](#OI-317) | 2026-09-18 | 2026-09-18 | `ora-vacancy-aging-report` weekly run, 2026-09-18 (STEP 4 property→PM mapping) | **CLOSED 2026-09-18 (same day)** — Gabriel supplied the missing contacts in chat; recorded in [memory/people.md](people.md) PM/leasing-side table and cross-checked against the task's own STEP 4 mapping (found already independently updated by a concurrent session with matching PM names — see detail). *Original finding:* **LOW — that day's run found 4 vacancy/coming-vacancy rows across 3 properties (29000 Information Lane, 9050 Red Branch Rd, 9620 State 350) with no PM/leasing contact in STEP 4's mapping**, each routed to "PM NOT ON FILE — confirm with Gabriel" in the sent report. No further action — contacts now on file: Civita Peters (PM) + Trent Spicer-Davis (leasing) for 29000 Information Lane; Steve Seh (PM) + Heather Applegarth (leasing/accounting) for 9050 Red Branch Rd; Garrett Alejos (PM) + Wyatt Palmer (leasing) for 9620 State 350 |
| [OI-293](#OI-293) | 2026-09-13 | 2026-09-13 | [PR #197](https://github.com/ZeOoba/ora-claude-config/pull/197) body, verified live via `gh pr view` this session | **FIXED 2026-09-13** — [PR #193](https://github.com/ZeOoba/ora-claude-config/pull/193) merged 12:59:38Z (by `ZeOoba`); [PR #197](https://github.com/ZeOoba/ora-claude-config/pull/197) closed 12:59:34Z as superseded — its own fix plus one further fix (unexpanded `~` paths under PowerShell 5.1) landed inside #193's branch instead. Verified via `gh pr view 197/193 --json state,mergedAt,closedAt`. Original finding: **LOW (process gate, not a defect) — [PR #197](https://github.com/ZeOoba/ora-claude-config/pull/197) (`preflight-shared-checkout.py` path-containment fix) is stacked on [PR #193](https://github.com/ZeOoba/ora-claude-config/pull/193) (OI-249 checkout-corrector port to `main`) and cannot merge before it; #197's own body also states "do not merge without Gabriel's go" even once #193 lands.** Both PRs confirmed OPEN/MERGEABLE via `gh pr view` this session. |
| [OI-234](#OI-234) | 2026-09-05 | 2026-09-12 | `ora-appsec-sweep` 2026-09-05 (ora-pm @ `ca62ecb`, security-auditor dispatch) | **FIXED 2026-09-12** — [ora-pm PR #27](https://github.com/ZeOoba/ora-pm/pull/27) merged `9013b40` (23:30Z) and deployed (CI run success incl. `Deploy to Cloudflare Pages`). Gabriel ruled "Oldest-first": fee iff `ar_ledger.balance − Σ charges due in the last 30 days > $0.005`. Fails closed on a PostgREST row-cap page; combined with OI-278's payments-feed guard (which currently suppresses ALL fees — payments table empty). Adversarial refute pass run pre-merge; merge with #26 verified by tests only. Original finding: **MEDIUM — the delinquency/late-fee cron (`cron.ts:496-519,529-540`) fires on ANY lease carrying a charge older than 30 days regardless of whether the tenant's CURRENT balance is actually overdue, so a tenant inside the grace period or already paid can still be assessed a wrongful $50 late fee.** Adjacent to but distinct from [OI-229](#OI-229) (missing off-host backup trigger for this same cron — a different problem). Candidate fix: gate the fee condition on the lease's current unpaid balance via `ar_ledger`, not merely charge age; add a regression test. Not applied |
| [OI-229](#OI-229) | 2026-09-03 | 2026-09-12 | `register-scheduled-task` v2.19 step 3b applied to the live fleet; Automation Audit Rev 21 R21-2/R21-4 | **MEDIUM — `ora-pm-daily-crons` posts late fees and has NO off-host backup trigger (`offhost-backup: none — GAP`); ora-pm PR #24 covers monthly billing only.** **RESOLVED 2026-09-12:** secret set, PR #25 merged, first run success ([run 34725864211](https://github.com/ZeOoba/ora-pm/actions/runs/34725864211)); frontmatter `live since 2026-09-12`. Earlier 09-12 note: fix built in [ora-pm PR #25](https://github.com/ZeOoba/ora-pm/pull/25) (delinquency-check only) — NOT live: repo secret `ORA_PM_CRON_SECRET` missing (also leaves PR #24's backup dormant). Close on secret set + merge + one successful run. |
| [OI-222](#OI-222) | 2026-09-02 | 2026-09-13 | `ora-appsec-sweep` 2026-09-02 (ora-pm @ `ca62ecb`, security-auditor dispatch) | **FIXED 2026-09-13** — [ora-pm PR #31](https://github.com/ZeOoba/ora-pm/pull/31) merged `253f2925`. On `23505`, the handler now reads the existing row's status and only skips a genuinely `processed` duplicate; a `failed` row is re-driven through `handleStripeEvent`. Independent adversarial REFUTE pass (cold read, no knowledge of the implementation) confirmed no double-processing risk — every downstream write in `stripe-events.ts` is an idempotent per-payment-intent update — and no scope creep into the migration/RLS. Original finding: **MEDIUM — a Stripe webhook event that throws on first processing is permanently dropped, not retried.** The event id is inserted into `stripe_webhook_events` *before* processing; a transient failure marks the row `failed` and returns 500, Stripe retries, the retry's insert hits `23505` and short-circuits to `{skipped:true}` 200 — the retry is discarded and the row never re-processes. |
| [OI-213](#OI-213) | 2026-09-02 | 2026-09-18 | `ora-tenant-hubspot-reconciliation` monthly run (this task) | **CLOSED 2026-09-18** — acceptance met; HubSpot now reflects the exercised renewal. Applied earlier the same day by another session (`hs_lastmodifieddate` 2026-09-18T16:41:37Z), read-back verified this session. *Original finding:* **ELEVATED — Heritage Pool Supply's exercised renewal option (2026-04-26) is documented in Notion and the workbook but the HubSpot deal still carries the superseded 2026-09-30 expiration in `appointmentscheduled`.** Notion's own row is RETIRED as a duplicate and names the canonical record and the correct date; `portfolio.json` independently says `leaseEnd 2031-09-30, Active`. Recommend `dealstage` → `closedwon`, `closedate` → `2031-09-30`. Detection-only — not written |
| [OI-214](#OI-214) | 2026-09-02 | 2026-09-18 | `ora-tenant-hubspot-reconciliation` monthly run (this task) | **CLOSED 2026-09-18** — acceptance met; `closedate` corrected to the rent-roll-confirmed 2027-05-31, applied and read-back verified this session. *Original finding:* **ELEVATED (Step 3d escalation — a correction that propagated to two systems and not the third) — Maryland Hospital Association's HubSpot deal still carries `2027-06-30`, the exact value Notion's own note records as disproven and replaced by `2027-05-31` on 2026-07-21.** `portfolio.json` agrees with the corrected date. Deal is already `closedwon`, so the wrong date is now baked into a closed record. Recommend `closedate` → `2027-05-31`. Detection-only — not written |
| [OI-215](#OI-215) | 2026-09-02 | 2026-09-18 | `ora-tenant-hubspot-reconciliation` monthly run (this task) | **CLOSED 2026-09-18** — acceptance met; the canonical Notion row now carries 2026-12-31, consistent with HubSpot and the workbook. Applied earlier the same day by another session, read-back verified this session. *Original finding:* **ELEVATED (Step 3d escalation, reverse direction) — the Notion Tenant DB row for J&R ENTERPRISES still carries Lease Expiration `2026-07-31`, a date now 33 days in the past, while HubSpot and the workbook both agree on `2026-12-31`.** This is the same tenant named in this task's own 2026-07-25 Step-3d precedent; the drift has since inverted — HubSpot is now correct and Notion is the stale system. Recommend correcting **Notion**, not HubSpot. Detection-only — not written |
| [OI-218](#OI-218) | 2026-09-02 | 2026-09-18 | `ora-tenant-hubspot-reconciliation` monthly run (this task) | **CLOSED 2026-09-18** — CJ's Tint Shop vacated at expiration; unit 105 re-let to Capital Property Recovery 2026-09-10 (live workbook + Gabriel); HubSpot deal `closedlost`, Notion row retired. Evidence in the detail section. *Original finding:* **WATCH (Step 3b) — CJ's Tint Shop's lease expired 2026-08-31 (two days ago) with no renewal, vacate, or holdover signal in any system.** All three sources agree on the date — HubSpot `closedate` 2026-08-31 still in `appointmentscheduled`, Notion Lease Expiration 2026-08-31 / Lease Status `Active`, `portfolio.json` `leaseEnd 2026-08-31` / status `Expiring Soon` — and none of them records what happened. Notion's Notes field is empty. **No outcome inferred**: this is a question for Gabriel, not a finding |
| [OI-219](#OI-219) | 2026-09-02 | 2026-09-18 | `ora-tenant-hubspot-reconciliation` monthly run (this task) | **CLOSED 2026-09-18** — stage-advance rule ratified by Gabriel and carried by the new weekly task `ora-renewal-hubspot-reconcile` (first run clean). Step 3e will re-raise unless amended — see detail. *Original finding:* **IDLE (Step 3e, the standing monthly sweep for the population [OI-021](#OI-021)'s batch pass confirmed was legitimately not-yet-due) — 6 deals sit in `appointmentscheduled` 37–159 days untouched with lease expirations 210–2,524 days out.** The more useful signal is the denominator: **every one of the 37 open deals is 37+ days idle** — the newest `hs_lastmodifieddate` anywhere in the open pipeline is 2026-07-27, so the whole renewal pipeline has been quiet since that batch. Flag-only; the stage disposition is Gabriel's call |
| [OI-166](#OI-166) | 2026-08-16 | 2026-08-16 | Concurrency near-miss during the passed-deal-tracker guard session (Gabriel-directed) | **FIXED 2026-08-16** — `claim` consulted only its OWN slug's file, never whether a live claim under a DIFFERENT slug already covered the same `--paths`. Two sessions held `open-items-tracker` and `repo-housekeeping` over the same two files; neither exit-3 refusal could fire. `claims_touching()` already existed and was wired into `shared-checkout-guard`'s Edit/Write path, but not into `claim` itself. See detail section |
| [OI-170](#OI-170) | 2026-08-16 | 2026-08-16 | Root cause of the whole passed-deal-tracker guard session (Gabriel-directed) | **FIXED 2026-08-16** — the scheduler resolves a registry `filePath` against the LIVE WORKING TREE, so a SKILL.md can be merged in git and still inert on disk. `ora-passed-deal-tracker`'s double-fire guard sat merged-but-inert for hours with zero hits in the live file. `task-folder-registration-probe.py` checked filePath EXISTENCE but never CONTENT-vs-git. See detail section |
| [OI-163](#OI-163) | 2026-08-16 | 2026-08-16 | Cross-repo architecture-diagram review (Gabriel-directed, this session); corroborates [[project_aaos_agent_coordination_layer]] | **CLOSED 2026-08-16** — the round-trip had actually happened 2026-07-10 (a real Cowork handoff + drained event, verified via `tools/validate.py` → VALID); the gap was Code never running `complete-task.py`. Leased/completed/archived `t-cowork-seam-confirm` this session. See detail section |
| [OI-165](#OI-165) | 2026-08-16 | 2026-08-16 | Cross-repo architecture-diagram review (Gabriel-directed, this session) | **CLOSED 2026-08-16** — `netlify.toml` build command now chains `build-kb.mjs && build-dist.mjs`; verified locally end to end, Gabriel-confirmed past the site-tree gate. See detail section |
| [OI-050](#OI-050) | 2026-07-31 | 2026-09-13 | ora-appsec-sweep 2026-07-31 (oxford-command-center @ `3692385`, security-auditor dispatch) | **FIXED 2026-09-13** — [oxford-command-center PR #327](https://github.com/ZeOoba/oxford-command-center/pull/327) merged `304bcbb0`. Original finding: **MEDIUM** oxford-command-center brain server has NO Host-header validation (`server/index.ts:531` binds 127.0.0.1, `server/cors-policy.ts` enforces localhost-only CORS) — but CORS is the wrong control for DNS rebinding: an attacker page whose DNS rebinds to 127.0.0.1 makes SAME-ORIGIN requests, so no CORS check applies at all. There is no Host allowlist and no CSRF token, and every state-changing route (`POST /api/actions/*`, `/api/refresh`, `/api/warehouse/properties/onboard`) is unauthenticated by design. A malicious page open in Gabriel's browser while the server runs can exfiltrate `GET /api/snapshot` — the full portfolio including confidential deals, tenants, loans, counterparty data — and can mutate deal stages, NOI budgets, tenant notes and lease-run assumptions |
| [OI-071](#OI-071) | 2026-08-03 | 2026-09-13 | Production verification of [OI-067](#OI-067), 2026-08-03 | **FIXED 2026-09-13** — [ora-pm PR #31](https://github.com/ZeOoba/ora-pm/pull/31) merged `253f2925`. `PortalInsurance.tsx` now resolves `tenants.id` via `GET /api/portal/me` (same pattern as `PortalPayNow`/`PortalDashboard`) instead of `session.user.id`, with a loading/error guard. Original finding: ora-pm `PortalInsurance.tsx` uploads COI files to `session.user.id`'s folder, but the live (confirmed-applied, confirmed-correct) RLS policy requires `tenants.id` — every real tenant COI upload fails today. Confirmed against production, not just the repo. Misleadingly-named variable (`tenantId = session.user.id`) is likely the root cause |
| [OI-078](#OI-078) | 2026-08-05 | 2026-09-18 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **CRITICAL, CONFIRMED CLOSED 2026-09-18** — dispatched `DB Migrate (manual)` as a read-only dry-run against production ([run 35388593228](https://github.com/ZeOoba/ora-pm/actions/runs/35388593228)) — `supabase migration list --linked` shows all 17 migrations 0001-0017 with LOCAL==REMOTE, including `0013_enable_rls_remaining_tables.sql` (this item's own fix); `supabase db push --dry-run` reports "Remote database is up to date." RLS is live in production. Original finding: ora-pm Row Level Security was enabled on only 6 of 23 tables while `VITE_SUPABASE_ANON_KEY` ships in the public JS bundle by design — the other 17 tables had no `ENABLE ROW LEVEL SECURITY` statement in any migration, so an RLS-disabled public table was readable and writable via PostgREST with the bundle-extractable anon key. Code fixed 2026-08-17 ([ora-pm PR #23](https://github.com/ZeOoba/ora-pm/pull/23)), but production migrations sat unapplied for weeks pending `SUPABASE_ACCESS_TOKEN`/`SUPABASE_DB_PASSWORD` repo secrets — those were confirmed set 2026-09-16, and this session's dry-run confirmed the migration is now live. See detail section for the full multi-week evidence trail |
| [OI-090](#OI-090) | 2026-08-05 | 2026-09-13 | ora-appsec-sweep 2026-08-05 (oxford-command-center @ `175e3f9`, security-auditor dispatch) | **FIXED 2026-09-13** — [oxford-command-center PR #328](https://github.com/ZeOoba/oxford-command-center/pull/328) merged `b34add2d`. Original finding: **MEDIUM** oxford-command-center has no rate or concurrency limit on `/api/ai` (`server/index.ts:460-493`), `/api/documents/search` (`:447-453`) or `/api/actions/om-extract` (`:358`). Per-request bounds are good (`maxTurns: 8`, `max_tokens: 16000`, 25 MB cap) but nothing bounds concurrent or repeated calls, and each `/api/ai` call spends real Anthropic tokens against the machine's key. OWASP-LLM10 unbounded consumption; combined with [OI-050](#OI-050)'s unauthenticated cross-site write path this is the cheapest denial-of-wallet route in the repo. ora-pm's equivalent gap was closed under OI-038/044; occ has no counterpart |
| [OI-181](#OI-181) | 2026-08-16 | 2026-08-16 | Hit live while recording the OI-176 review artifact (session 76023481), then reproduced deterministically | **MEDIUM, LANDED 2026-08-16** — a stale copy of the review gate silently discarded `--notes-file`, yielding an APPROVED security-review artifact with an EMPTY audit trail, exit 0, no warning. Fixed as `4cbebe8` (from worktree commit `43be6ca`) on Gabriel's in-turn "land it the same way OI-176 went" — `reject_unknown_flags()` on both `--key`/`--record`, `__version__` stamped into every artifact. Live post-landing verification with the override token removed confirmed the fix live, not just in a harness; independently reviewed (claude-fable-5) before landing. No lingering damage from the triggering incident. See detail section |
| [OI-127](#OI-127) | 2026-08-12 | 2026-09-18 | session `e0f8485e`, hitting pre-push failures under concurrent load | **CLOSED 2026-09-18 — duplicate of OI-135, same fix — see OI-135 for the live item.** Original text: DUPLICATE — superseded by OI-135; no separate investigation needed. Same defect, same file, same number: `hooks/git-prepush-hook-tests-gate.py`'s 180s per-test timeout budget is too low under concurrent load, so healthy tests exit-124 and hard-block a push. OI-127 (20:52Z) is the EARLIER reservation; OI-135 (22:00Z, Gabriel-directed, filed by session `2fb76021`) covers the same finding with fuller evidence. Filed only to close the orphan reservation and stop a third session re-deriving it. **duplicate/orphan-reservation closure — see OI-127's own text; OI-135 (the item it points to) is already closed elsewhere in the tracker history.** |
| [OI-079](#OI-079) | 2026-08-05 | 2026-09-18 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **CLOSED 2026-09-18** — **HIGH** ora-pm's `ar_ledger`, `rent_roll` and `critical_dates` views are created without `WITH (security_invoker = true)` (`0011_appsec_idempotency_and_scale.sql:118-151`, `0004_views_and_rls.sql:33-99`) — grep confirms the string appears nowhere in `supabase/migrations/**`. A view without it runs as its owner and IGNORES the RLS policies on `charges`/`payments`/`leases`/`tenants`, so one `GET /rest/v1/ar_ledger` returns every tenant's balance and payment totals even after [OI-078](#OI-078) is fixed. Cross-tenant financial disclosure in one request. **CODE FIXED 2026-08-17, NOT YET LIVE**: `0012_view_security_invoker.sql` adds `security_invoker=true` to all 3 views. Postgres 17 (`supabase/config.toml`) supports it; the one caller class (server/routes/**) uses the service-role key, unaffected. REFUTE-confirmed. Merged via [ora-pm PR #23](https://github.com/ZeOoba/ora-pm/pull/23) (`aede030`) — same NOT-YET-APPLIED-to-production caveat as [OI-078](#OI-078) (manual `db-migrate.yml` workflow required). **Confirmed 2026-08-22 via the same dry-run** ([run 32583466897](https://github.com/ZeOoba/ora-pm/actions/runs/32583466897)) that closed the gap on OI-078 — see that item's entry for the full result (failed cleanly at the link step, secrets not configured, no partial action) |
| [OI-171](#OI-171) | 2026-08-16 | 2026-09-19 | Found while root-causing Gabriel's report of the Command Center `loans · name` safety-section flag | **CLOSED 2026-09-19** — **MEDIUM — self-masking alert.** `ora-cc-snapshot-refresh` STEP 5(b) escalates to email on any data-quality flag `severity: warn` or higher — but the one permanent, intentional flag (`loans · name`, the tombstoned Loan Index row 24 duplicate marker) was bumped `info`→`warn` in oxford-command-center `490d89f` (2026-08-11) ~21h before the snapshot task's own severity gate (`1706bc2`, 2026-08-12) was written around the stale `info` belief — so every clean, no-drift run has sent a false `[ALERT]` since. **Status: FIXED 2026-08-16** in the live SKILL.md + registry — **UNVERIFIED** until the next run (2026-08-17 ~06:21 ET) actually suppresses the email; see full section |
| [OI-318](#OI-318) | 2026-09-18 | 2026-09-19 | Code session, `ora-skills` `market-status.md` counterparty-redaction review (branch `claude/beautiful-noyce-3e6e7f`) | **CLOSED 2026-09-19 — accepted risk, history left alone per Gabriel.** Working copy redacted (commit `ff48473` on `origin/main`, per Gabriel's explicit instruction) but the original counterparty/locale-identifying text (Clermont "754 Old SR 74" seller, Butler "Liberty Office Park" seller) is still live in git history at `ec9c626` on `ora-skills`' public GitHub remote (`ZeOoba/ora-skills`), reachable from `main` and most other branches. Gabriel explicitly said "leave history alone" for this pass — open question is whether that stands or whether a history rewrite (filter-repo + force-push across every affected branch, or repo delete/recreate) is warranted given the public remote |
| [OI-287](#OI-287) | 2026-09-12 | 2026-09-12 | `ora-ground-truth-auditor` 2026-09-12 digest | CLOSED on arrival — `session-context-xref-probe.py` omitted `maintenance/_state` from its search roots (false `[XREF-MISSING]`); fixed same day via `xref-extra-roots.json`. Row restored 2026-09-13; section was orphaned |
| [OI-348](#OI-348) | 2026-09-22 | 2026-09-22 | oxford-command-center PR [#357](https://github.com/ZeOoba/oxford-command-center/pull/357) review (2026-09-14 ora-financial-code-integrity-sweep remediation) | CLOSED on arrival — PR #357's AR dead-lease guard widening made the AR collections-alert staleness gate all-or-nothing (one stale lease could blind portfolio-wide alerting ~2026-09-25); fixed same-window via PRs [#360](https://github.com/ZeOoba/oxford-command-center/pull/360)/[#361](https://github.com/ZeOoba/oxford-command-center/pull/361) making the gate per-lease. Row was never written until now (checker ORPHANED_SECTION cleanup, this session); section was orphaned |
| [OI-136](#OI-136) | 2026-08-12 | 2026-08-28 | `event_log.md` entries committed as `75ab0de`, cross-read against this session's own two declined overrides | CLOSED — row flipped, stale for 15 days. `allow-hook-test-failure` normalised (5 uses across 4 sessions in 47 min, 2026-08-12), but the finding was **ALREADY CLOSED as of `b1cbd0d` (2026-08-13)** — `git-prepush-hook-tests-gate.py`'s `record_override_use()`/`override_frequency()` already log every override and surface a repeat-use warning to the next approver, exactly this item's ask. Re-verified live this session: `test-git-prepush-hook-tests-gate.py` → 146/146 pass (was 129/129 at last check), `record_override_use`/`override_frequency` confirmed wired. No new work needed |
| [OI-080](#OI-080) | 2026-08-05 | 2026-08-28 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | CLOSED — row flipped, stale for 11 days. ora-pm tenant portal login's open self-registration gap (`PortalLogin.tsx` missing `shouldCreateUser: false`) fixed 2026-08-17 via [ora-pm PR #23](https://github.com/ZeOoba/ora-pm/pull/23) (`aede030`), REFUTE-confirmed, 470/470 tests pass. Re-verified live this session: `shouldCreateUser: false` confirmed present in the current file; CI run for the merge completed SUCCESS 2026-08-17 |
| [OI-081](#OI-081) | 2026-08-05 | 2026-08-28 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | CLOSED — row flipped, stale for 11 days. ora-pm's `requireAal2` MFA gate was a no-op for never-enrolled tenants; fixed 2026-08-17 via [ora-pm PR #23](https://github.com/ZeOoba/ora-pm/pull/23) (`aede030`) to block outright on `currentLevel !== 'aal2'`, incl. a regression fix for a silent autopay-toggle rejection. Re-verified live this session: `aal-guard.ts`'s OI-081 fix confirmed present; CI run for the merge completed SUCCESS 2026-08-17 |
| [OI-211](#OI-211) | 2026-08-28 | 2026-08-28 | `ora-doctrine-integrity-guard` scheduled run, `spec-liveness-probe.py` `[DRIFT]` finding; resolved by reading the `ora-cc-snapshot-refresh` 08-17/08-24 run transcripts + `oxford-command-center` git/PR history | CLOSED — root cause confirmed and fix already live. Original filing wrongly implied the weekly task might not be firing (it is, on cadence — registry confirmed). The real blocker was a NEW reconciliation gate (landed `ead629d`, 2026-08-22) correctly refusing the 08-24 write over 2 Sepich-portfolio leases (`4595`/`4601 E. 5th Ave`) missing from `RENT_ROLL_PROPERTY_ALIASES` — 1.45% unresolved rent over the gate's 1% threshold. The 08-24 `ora-cc-snapshot-refresh` session correctly alerted (email + Notion, not silent), root-caused it, and built/tested a full worktree fix (PR [#289](https://github.com/ZeOoba/oxford-command-center/pull/289)); a parallel Gabriel-directed session landed the byte-identical fix directly to main first (`1c7d17b`, backed by stronger tax-parcel/DD evidence), so #289 was correctly closed as superseded rather than double-landed. **Verified live 2026-08-28:** current HEAD (`4fe838f`) shows 0 unresolved leases, 0.00% unresolved rent — the gate is clear and the weekly extract should commit cleanly on its next fire (08-31). One residual noted by the 08-24 session, not filed separately: the landed tests cover Sepich-alone and 3540-alone but not the both-E.-5th-Ave-rows-present-simultaneously configuration that actually runs in production — minor test-coverage gap, not a live defect. Companion finding re-diagnosed, not closed: [OI-212](#OI-212) (now CLOSED, see below) |
| [OI-212](#OI-212) | 2026-08-28, RE-DIAGNOSED same day | 2026-09-03 | `ora-doctrine-integrity-guard` scheduled run, `spec-liveness-probe.py` `[DRIFT]` finding; closed via `ora-cc-snapshot-refresh/SKILL.md` v1.5 (2026-08-28) + `spec-liveness-probe.py` `PINNED_FLAGS` retirement (2026-09-03) | CLOSED — row flipped, stale for 6 days. `ora-cc-snapshot-refresh/SKILL.md` v1.5 (2026-08-28, Gabriel-directed, in-turn) retired the RATIFIED-TOMBSTONE ALLOWLIST this item was investigating — the go-ahead this row says it was waiting on was given and implemented THE SAME DAY the row was last edited, but the row itself was never flipped to CLOSED. **Re-verified live 2026-09-03:** the SKILL.md explicitly states "No allowlist is currently active," and STEP 5 independently handles a recurrence (a reappearing `loans · name` "DUPLICATE OF ROW" flag is NOT allowlisted, it emails) regardless of this doctrine probe. Residual noise closed same day: `spec-liveness-probe.py`'s own `PINNED_FLAGS` entry for this flag kept matching the v1.5 retirement changelog and recurrence-warning text as if it were a live claim (no way to tell documentation from an active pin), producing permanent unfixable `[DRIFT]` against an already-fixed file — retired to `[]` (with rationale + re-pin instructions in its own comment), matching-algorithm test coverage moved to a synthetic fixture in `test-spec-liveness-probe.py` (14/14 pass), live probe now reports 0 findings. Detail: `event_log.md` 2026-09-03 |
| [OI-197](#OI-197) | 2026-08-21 | 2026-08-21 | Cross-repo architecture-diagram review; closed by repo-architecture-review remediation | CLOSED — both fixes built. (b) `automation-health-monitor` v1.6 enumerates all 5 substrates (visibility). (a) native `ORA Mirror Deploy Classifier` task, off-fleet, survives a full pause by construction — scoped to the existing Outlook COM alert path, no new Notion token rushed the same day CRON_SECRET rotated |
| [OI-201](#OI-201) | 2026-08-21 | 2026-08-21 | Cross-repo architecture-diagram review; closed by repo-architecture-review remediation | CLOSED — `ora-pm` README fixed (`c311da7`): scheduler diagram/prose now name the CC/MCP fleet tasks, deploy section corrected, Pages Git-integration question checked (`Git Provider: No`, no race). Merged with a concurrent RLS/MFA fork on `main`, 471/471 tests pass, deployed |
| [OI-200](#OI-200) | 2026-08-21 | 2026-08-21 | Cross-repo architecture-diagram review; closed by repo-architecture-review remediation | CLOSED — tax-recapture commit pushed (`58da3a4..9da7c8c`, verified sourced + arithmetic checked), stray `oxford-command-center-1` clone archived to `_archive-non-onedrive/` |
| [OI-198](#OI-198) | 2026-08-21 | 2026-08-21 | Cross-repo architecture-diagram review; closed by repo-architecture-review remediation | CLOSED — `ora-cowork-watchdog` README corrected via Contents API (no local clone exists); systemd-producer claim reframed as an unbuilt V2 intention, byte-verified post-push |
| [OI-162](#OI-162) | 2026-08-16 | 2026-08-21 | Cross-repo architecture-diagram review; closed by repo-architecture-review remediation | CLOSED — both halves live. Daily half fixed 08-16 (`ora-pm-daily-crons`). Monthly half: batching fix was already deployed by action time (stale "Not deployed" note); registered `ora-pm-monthly-billing` (CC/MCP, 1st @ 11:10 AM ET, next fire Sep 1). Caught and fixed a near-miss same-session — rotating `CRON_SECRET` would have broken the daily cron too (shared secret, separate consumer file); fixed before its next fire |
| [OI-199](#OI-199) | 2026-08-21 | 2026-08-21 | Cross-repo architecture-diagram review (`repo-architecture-review`, Gabriel-directed) | CLOSED — archived. Internal-Accounting-App was the only ORA repo with no README/diagram/local clone; Gabriel ruled dormant, `gh repo archive ZeOoba/Internal-Accounting-App --yes` run and confirmed (`isArchived:true`). QuickBooks Desktop remains source of record; audit-coverage hole closed legitimately rather than left silently unscanned |
| [OI-157](#OI-157) | 2026-08-15 | 2026-08-15 | Filed `7c9740a`; row lost to merge-conflict resolution, re-filed 2026-08-15/16 (this session) — see [OI-160](#OI-160) | RESOLVED — `capex-budgeting` was accidentally republished 2026-08-13 (batch Save-skill click side effect), Gabriel ruled it accidental and unpublished it again via the claude.ai Skills page, escalated to Remove after Share-off left it still visible, confirmed removed via search ("No skills match your search"), matching the other 5 2026-08-09 unpublish-siblings |
| [OI-148](#OI-148) | 2026-08-13 | 2026-08-13 | ECC repo intake ([external-artifact-intake](../../skills/external-artifact-intake) ruling, Gabriel 2026-08-13); merged as PR [#94](https://github.com/ZeOoba/ora-claude-config/pull/94), `25ac9ec` | LANDED on `main`. `hooks/lint-config-guard.py` — fail-closed guard (pattern: ECC's `config-protection.js`, adapted to this codebase's own override-token contract) blocking silent edits to EXISTING `eslint.config.js`/`tsconfig.json`/`tsconfig.node.json`/`functions/tsconfig.json`/`vitest.config.ts`/`.prettierrc.json` in `oxford-command-center` (scope ratified: occ only). 3 rounds of independent adversarial review (`pr-review-toolkit:code-reviewer`, opus) found and fixed: a settings.json routing gap (`move_file`/`write_pdf` unrouted), wrong integration pattern (moved into `pretooluse-dispatcher.py`'s `GUARD_CHAIN`), a LIVE sandbox-confirmed shell quote-split bypass (`ts''config.json`, fixed via ported `_dequote`/`_decaret`/`_shell_variants`), and a whole-command worktree exemption narrowed to token-scoped (ported `_blank_exempt`). `eos-review-gate` verdict recorded (approved, `claude-opus-4-8`). **Evidence:** 26/26 own tests pass; shared `test-write-guard-coverage.py` meta-test green (4th `GuardSpec` added, 16/16 shapes routed, no double-routing); cherry-picked cleanly onto a fresh `origin/main`-based branch and re-verified there (not just the dev branch) before pushing. Pushed under a Gabriel-approved `allow-hook-test-failure` override — the pre-push block was [OI-149](#OI-149) (unrelated stale probe allowlist), not this diff. **Documented, not fixed — explicit follow-up, not silently expanded scope:** `package.json`'s own `lint`/`typecheck` script strings (`--max-warnings 0` etc.) achieve the same threat model with a smaller diff and are out of the ratified 6-file scope; needs its own scoping decision from Gabriel. Companion item [OI-147](#OI-147) (same intake, Gate 2b hardening) was rejected after a full build + adversarial gauntlet — see that row and [[feedback_autonomy_gate_matcher_cannot_be_safely_narrowed]] Round 4 |
| [OI-087](#OI-087) | 2026-08-05 | 2026-08-12 | ora-appsec-sweep 2026-08-05 (both repos, security-auditor dispatch); fixed via `hono@^4.12.34` bump, both PRs merged 2026-08-12 | RESOLVED — `hono` raised to `^4.12.34` (lockfile 4.13.1) in both repos, clearing the CORS ReDoS GHSA-8j4g-w8fx-2239 (and 3 other `<4.12.34` hono advisories in occ). PRs: ora-pm [#21](https://github.com/ZeOoba/ora-pm/pull/21) squash `caa5849`, oxford-command-center [#270](https://github.com/ZeOoba/oxford-command-center/pull/270) squash `4187b78`. Each verified pre-merge: hono cleared from `npm audit`, typecheck 0, lint 0, tests green (ora-pm 427; occ 3354); occ CI gate + refute-required + CodeRabbit all green. Floor raised in package.json (not just the lockfile) so a reinstall can't regress. Pre-existing dev-only advisories (nanoid on ora-pm; react-router/sharp/etc. on occ) are [OI-017](#OI-017)'s, untouched |
| [OI-100](#OI-100) | 2026-08-05 | 2026-08-12 | Gabriel ruling 2026-08-05 (rescope approved); design pass that session | CLOSED — MERGED AND LIVE. Fix commit `9ad6146` (pre-push doctrine gate validates the pushed commit, not the working tree) merged to `origin/main` via `230da82` on 2026-08-05; independent review + adversarial REFUTE both APPROVED, 14/14 new tests + 37/37 existing + full probe suite green. Tracker wording lagged the actual merge by a week (see detail section); verified 2026-08-12 that `9ad6146` is an `origin/main` ancestor and the live `hooks/git-prepush-doctrine-gate.py` matches it exactly — closing now that the wording matches reality |
| [OI-110](#OI-110) | 2026-08-09 | 2026-08-09 | Process-gap pair found by session `1d88885d`'s `hooks-override-auth` claim, 08-09 | CLOSED - both gaps closed by a NEW hook, `hooks/commit-hygiene-guard.py` (warn-only PreToolUse/Bash), commit `399be31`, merged `a7b48d5`, published `bbb4ec3`. Branch identity is now stated on every `git commit` and escalated when the branch changed since this session's last commit in that repo; the companion memory-stamp gap is caught by diffing `modified:` between HEAD and the version git will actually commit. `shared-checkout-guard.py` was deliberately NOT modified - see the Evidence note on why it structurally cannot carry this check. |
| [OI-107](#OI-107) | 2026-08-09 | 2026-08-09 | [event_log.md](event_log.md#2026-08-09) — guard.ps1 mtime-revert pause | CLOSED — the pause is lifted because its reason is gone. The canonical-is-authoritative engine landed on `main` (`1af60c3`, hardened by `2e29fa7` after independent review + adversarial REFUTE) with `maintenance/task-integrity-lib.ps1`; `guard.ps1` now contains **zero** `LastWriteTime` references — mtime is out of the decision path entirely — and loads the new decision core. Both `ora-task-integrity-guard` and `ora-health-guard` are `enabled:true` again with live next-run times (2026-08-10T11:14:19Z and 09:24:39Z), verified via `list_scheduled_tasks`, not a registry read. The four 2026-08-09 model retags survived the whole episode intact (`ora-skill-cache-drift-alert`, `ora-cc-schematic-refresh`, `ora-am-brief`, `ora-lease-snapshot-refresh` all still read `checked 2026-08-09`), so no write was lost. This item's `Auto-check` fired correctly and is what surfaced the closure |
| [OI-108](#OI-108) | 2026-08-09 | 2026-08-09 | Investigation of two "untraceable" claim-holder sessions | Both defects fixed and merged to `main` as `8fca11d` (branch `fix/claim-host-session-id`, commit `369c62b`). `host_session_id` is now recorded ALONGSIDE the agent id and normalized at one reader choke point (`_clean_host_session_id`), so a claim can be turned into a `send_message` target; `--paths` uses `action="extend"` so a repeated flag accumulates instead of silently keeping only the last value. **Evidence:** full `hooks/tests` **44/44 on main post-merge, 0 failures** (incl. `test-confidentiality-guard` 131/131, which cannot run in a worktree); `test-claim-work-lib` 85/85 (was 55), `test-active-work-broadcast` 42/42 (was 23). Independent review, `claude-fable-5`, 2 rounds: R1 CHANGES REQUIRED (2 Important + 3 Minor), R2 APPROVED WITH NITS after all five were closed; reviewer mutation-tested both fixes to confirm the new tests BIND (gutted normalizer -> 9+7 failures; renew re-reads env -> exactly the 2 new assertions). Review artifact recorded against `eos-review-gate` before the commit landed. **Accepted residual, not a defect:** no `local_<uuid>` shape check, so renderable-but-wrong printable-ASCII tokens pass -- strictly less expressive than the adjacent, already-unsanitized `description` field, and hard-coding a format observed once would risk silently rejecting a legitimate future target (the very bug this closes) |
| [OI-037](#OI-037) | 2026-07-31 | 2026-08-04 | ora-appsec-sweep 2026-07-31; fixed `ora-pm` commit `23b924f`; verified live 2026-08-04 (in-page fetch against `ora-pm.pages.dev`) | CORS exact-match allowlist + security headers. `X-Frame-Options: DENY` and `Content-Security-Policy-Report-Only` (exact expected policy) confirmed present on the real served response, not just the merged config — closes this item's own standing verification caveat. CSP-enforcement flip remains OI-066's separate job |
| [OI-039](#OI-039) | 2026-07-31 | 2026-08-04 | ora-appsec-sweep 2026-07-31; fixed `ora-pm` migration `0011_appsec_idempotency_and_scale.sql`, applied to production 2026-08-04 | All 10 money columns retyped `NUMERIC(12,2) NOT NULL` with unit `COMMENT ON COLUMN`s; `charges.idempotency_key` backfilled + `NOT NULL`; `payments.stripe_payment_intent_id` unique index + `autopay_period` dedup column added. All 3 of the migration's own pre-flight checks ran clean against prod first (0 dupes, 0 backfill collisions, 0 sub-cent rows/10 cols). Verified post-apply via `information_schema.columns` + `ar_ledger` resolving cleanly. Bonus finding: migration tracker was stalled at 0007, masking that 0009/0010 were already live untracked — see [OI-073](#OI-073) |
| [OI-073](#OI-073) | 2026-08-04 | 2026-08-04 | Applying migrations 0009-0011 to ora-pm production, 2026-08-04 | `supabase_migrations.schema_migrations` backfilled with rows for 0008-0011 (Gabriel: "backfill now") — tracker now shows 11 contiguous rows matching the live schema for the first time. Root cause was left unidentified at this item's own closure — since root-caused and fixed as [OI-074](#OI-074) (no `SUPABASE_ACCESS_TOKEN` in the Code sandbox; two-tier fix built) |
| [OI-067](#OI-067) | 2026-08-03 | 2026-08-03 | ora-pm appsec fix plan Task 11 (OI-048), commit `9aa7f30`; verified against production 2026-08-03 (Gabriel signed into Supabase, ran verify-rls.sql live) | Status resolved: production DB was found paused (unrelated, resumed in-turn), all 3 parts of verify-rls.sql pass cleanly — the RLS policy IS live and IS exactly as documented (rules out the "more-permissive out-of-band policy" scenario). Confirmed instead: every real COI upload fails today because the client code uploads to the wrong path. Underlying fix filed as [OI-071](#OI-071). Bonus finding flagged, not filed: Security Advisor shows `public.units` has RLS disabled (CRITICAL), confirmed `rowsecurity=false`, needs Gabriel's triage on client-exposure |
| [OI-045](#OI-045) | 2026-07-31 | 2026-08-04 | ora-appsec-sweep 2026-07-31; fixed `ora-pm` commit `03487cd` + merge `a29f8f0` | MFA enroll->verify UI flow fixed earlier; this closure covers the AAL2 (step-up) enforcement REFUTE found was client-side-only. 3 REFUTE passes: pass 1 built `requireAal2` (real server-side Supabase call, fails closed) and wired it to `PATCH /api/portal/autopay`; pass 2 found `POST /api/stripe/setup-intent` (attaches a bank account) and `POST /api/stripe/payment-intent` (confirms/charges immediately — moves real money) both still ungated, independent of `/autopay`; pass 3 swept the rest of `server/routes/` and confirmed complete. Escalated MEDIUM->CRITICAL mid-fix. End-to-end integration tests assert the underlying Stripe call is never reached when blocked. One low-severity follow-up filed as [OI-077](#OI-077) |
| [OI-063](#OI-063) | 2026-08-03 | 2026-08-04 | ora-pm appsec fix plan Task 9, commit `afef524`; fixed `ora-pm` commit `7857646` + merge `a29f8f0` | The 5 self-flagged files (properties/expenses/payments/portal-auth/portal-insurance) were confirmed STILL leaking raw errors after a later commit's title claimed "dbError sweep" (verified via `git diff`, not trusted from the message). All 9 sites now route through `dbError()`; single-record 404 lookups keep a plain generic 404 (dbError always 500s), mirroring `tenants.ts`'s precedent. Tripwire allowlist fully closed |
| [OI-069](#OI-069) | 2026-08-03 | 2026-08-04 | REFUTE pass on the OI-046 fix, 2026-08-03; fixed `ora-pm` commit `f0b6780` + merge `a29f8f0` | CAM recalculation could silently reopen and under-bill an already-billed reconciliation. A commit titled "OI-046 gap closure" was confirmed (via empty `git diff` on `cam.ts`) to be unrelated. 2 REFUTE passes: pass 1 found a check-then-act pre-check version still raced against a concurrent approve (real TOCTOU); fixed via making the write itself atomically conditional (`status='draft'` guard). Pass 2 found the guard was a deny-list against `'billed'` that would've silently reopened a `'collected'` row too (3rd legal status, currently unreachable but latent) — fixed to an allow-list |
| [OI-034](#OI-034) | 2026-07-31 | 2026-08-03 | ora-appsec-sweep 2026-07-31; fixed `ora-pm` commit `3e600e4` | Autopay double-debit-on-re-run + arrears-sweep gap both closed — deterministic Stripe idempotencyKey + DB-unique autopay_period guard, plus a REFUTE-caught follow-up fix scoping the debit cap to the current period (not lifetime AR balance). TDD, 244/244 green, typecheck clean |
| [OI-036](#OI-036) | 2026-07-31 | 2026-08-03 | ora-appsec-sweep 2026-07-31; fixed `ora-pm` commit `18d8f6d` | Bare @oxfordra.net domain-suffix admin check replaced with an exact-match ADMIN_EMAILS allowlist, fail-closed 503 when unset; live tenant-exclusion check blocks a tenant with an admin-domain email from becoming admin; shouldCreateUser:false stops self-provisioning. REFUTE pass: no bypass found. Needs ADMIN_EMAILS actually set in prod or the whole admin API 503s. 266/266 green |
| [OI-043](#OI-043) | 2026-07-31 | 2026-08-03 | ora-appsec-sweep 2026-07-31; fixed `ora-pm` commit `df196ee` | Autopay payment-method ownership now verified against the tenant's own Stripe customer + bank-account type, before ever persisting. REFUTE pass: no bypass found; added one regression test for an already-correct orphaned-PM edge case. Note OI-068: the flow this protects is currently unreachable from any live frontend, so practical exposure is near zero — still correct defense in depth |
| [OI-046](#OI-046) | 2026-07-31 | 2026-08-03 | ora-appsec-sweep 2026-07-31; fixed `ora-pm` commit `81b5626` | CAM approval TOCTOU race closed — insert-first idempotency-keyed charge (DB unique constraint), conditional-update-second on status. REFUTE pass traced two concurrent requests through the actual code: no double-post survives. Found a separate MEDIUM under-billing gap (recalculation collides with old charge's key), filed as OI-069 rather than blocking. 311/311 green |
| [OI-038](#OI-038) | 2026-07-31 | 2026-08-03 | ora-appsec-sweep 2026-07-31; fixed `ora-pm` commit `63eb548` | Rate limiting moved from a bypassable per-isolate in-memory Map to a KV-backed cross-isolate counter, wired into payment-intent/intake/admin-mutations/cron; INTAKE_MODEL allowlisted. Needs the KV namespace actually provisioned in prod (binding shipped commented-out — REFUTE caught the placeholder id would fail the whole deploy) or it runs on the weaker memory-only fallback |
| [OI-044](#OI-044) | 2026-07-31 | 2026-08-03 | ora-appsec-sweep 2026-07-31; fixed `ora-pm` commit `63eb548` (same merge as OI-038) | PDF TEXT content now scanned pre-egress against the confidentiality denylist (not just filename), blocking before any Anthropic API call; tenant_id/unit_id existence-checked. REFUTE pass caught the initial fail-open behavior for scanned/image PDFs (egressed before the warning even surfaced) — fixed via TDD to block instead, matching this item's own pre-existing "Residual" note that the intent-based controls weren't enforced |
| [OI-035](#OI-035) | 2026-07-31 | 2026-08-03 | ora-appsec-sweep 2026-07-31; fixed `ora-pm` commit `d99a412` | Payment-intent double-charge-on-retry closed — DB unique index + client_request_id echoed into Stripe's idempotencyKey + 23505-as-200-dedup. Bundled with OI-040 in one reviewed/tested commit. REFUTE pass found no exploit, filed 2 narrower follow-ups ([OI-064](#OI-064), [OI-065](#OI-065)) rather than blocking. 260/260 green |
| [OI-040](#OI-040) | 2026-07-31 | 2026-08-03 | ora-appsec-sweep 2026-07-31; fixed `ora-pm` commit `d99a412` (same merge as OI-035) | $50k hard ceiling + reject-over-outstanding-balance on payment amount, boundary allowed, query failure never falls through to a blind charge. The "no paid/open discriminator" UI residual is no longer a money-safety gap since the balance cap backstops it |
| [OI-030](#OI-030) | 2026-07-26 | 2026-08-03 | `ora-weekly-hygiene` Sunday run + 3 concurrent sessions, 2026-07-26 | Block C full coherence read done (Gabriel ruled satisfied 2026-08-03) - 4 real global-contradiction defects found and fixed (+39/-4): dead SharePoint-MCP error clause, check A enforcing a non-canonical naming schema, check D missing the frozen-snapshot carve-out, check C's data-source-id 404 trap. Read was post-deadline and agent-performed; fixes uncommitted at closure (55-file dirty tree) - see entry |
| [OI-054](#OI-054) | 2026-07-30 | 2026-08-03 | Credential-exposure sweep, 2026-07-30 | **FALSE FINDING (reporting error).** The three flagged `api_key=` values read literally `ROTATED-DEAD-FRED-KEY-REDACTED-20260724` — already neutralized 6 days BEFORE the sweep. Filed on shape match without reading the value; a same-day hash check had already reported 0 keys in the file and I misread it as "not the live key" rather than "not a key" |
| [OI-055](#OI-055) | 2026-07-30 | 2026-08-03 | Credential-exposure sweep, 2026-07-30 | Backup-then-redact applied (Gabriel ruling): 4 values in 3 `.claude.json.bak-*` files replaced with a dated marker, originals preserved byte-intact in `_preredaction_2026-08-03/`, JSON re-verified. searchapi connector removed 2026-06-02 so revocation is optional/Gabriel's. The 2 local dev PEM keys left as-is by design (no external account; redaction would corrupt them for no gain) |
| [OI-056](#OI-056) | 2026-08-03 | 2026-08-03 | `doctrine-integrity-probe.py` pre-push run, 2026-08-03; resolved by commits `edc9fa1` + `7596feb` | Not 3 instances of one defect as first logged — only 2 were the same bug. `ratify-hurdle-rate`/`tenant-email` SKILL.md genuinely said "Principal" against canon and are now fixed to "VP Acquisitions" (`edc9fa1`). The third, `document-assembly/SKILL.md:180`, was never a defect: Gabriel ruled that "Member / Principal" there states the LLC-execution capacity Gabriel binds under, a distinct concept from his firm operating title — left unchanged with an in-file note as a documented Check-13 false positive (`7596feb`). Separately recorded, not this item: 21 live "Landlord - *" Outlook signatures carry the same "Principal" execution-capacity language and are outside the probe's scan scope |
| [OI-032](#OI-032) | 2026-07-28 | 2026-07-28 | Code-surface usage-limit audit → Cowork follow-up, 2026-07-28 | Duplicate `searchfit-seo` plugin installs in Cowork's registry — Gabriel confirmed (in-turn, 2026-07-28) both uninstalled manually via Settings → Capabilities; not independently re-verifiable from Code |
| [OI-028](#OI-028) | 2026-07-26 | 2026-07-26 | `hooks/git-prepush-hook-tests-gate.py` GIT_TRACE root-cause + fix, commit `0d4b974` | Root cause: NOT the network push (0.54s) — the pre-push hook-tests gate ran ~54 tracked test files SEQUENTIALLY, 137s wall-clock, measured directly. Parallelized (bounded ThreadPoolExecutor, 8 workers) → 137s to ~38-42s across 4 runs, 0 failures. TDD + adversarial REFUTE review (1 real finding fixed: a load-sensitive wall-clock test assertion, replaced with a structural sweep-line overlap proof); re-review NOT REFUTED. Built in isolated worktree, Gabriel-confirmed merge |
| [OI-023](#OI-023) | 2026-07-21 | 2026-07-22 | oxford-command-center `parse.ts`/`conditions.ts` (ora-pm-ledger 2026-07-21 divergence audit) | Snapshot provenance `asOf` now reads the workbook's own dateline (PR #231) — meta 2026-07-17 / cash 2026-07-10 live-verified; `?? s.meta.asOf` fallback audit: all alerting paths pass explicit run dates, last omitting caller wired |
| [OI-018](#OI-018) | 2026-07-18 | 2026-07-19 | ora-appsec-sweep first run — supervised re-run (2026-07-18) | ora-pm HIGH IDOR on `/api/stripe/{customer,setup-intent,payment-intent}` RESOLVED — session-ownership guards (portal.ts/autopay pattern) landed in `c705531`, 185/185 green, adversarial refute pass run |
| [OI-013](#OI-013) | 2026-07-17 | 2026-07-17 | [reference_onedrive_business_scope.md](reference_onedrive_business_scope.md) | Second `oxford-site` git clone was a known, already-repaired legacy checkout (Gabriel, 2026-07-16) — not a live risk; leaked deploy token already purged + rotated same day |
| [OI-012](#OI-012) | 2026-07-17 | 2026-07-17 | ora-deal-command-board SKILL.md STEP 2 | Stamp `Last Activity` from deal-touching skills so the board's stall flag is authoritative — field+board+3 skills stamped, Save-skill reimport of all 3 confirmed by Gabriel, PENDING_REIMPORT.md cleared |
| [OI-011](#OI-011) | 2026-07-17 | 2026-07-17 | [project_bash_guard_indirection_gap.md](project_bash_guard_indirection_gap.md) | bash-guard.mjs: core.hooksPath read/write + cp guard-path source/dest false positives fixed |
| [OI-010](#OI-010) | 2026-07-17 | 2026-07-17 | [project_bash_guard_indirection_gap.md](project_bash_guard_indirection_gap.md) | bash-guard.mjs: closed git-alias/wrapper-script indirection across all 7 blocked command classes |
| [OI-007](#OI-007) | 2026-07-17 | 2026-07-17 | [project_autonomy_gate_indirection_ceiling_followup.md](project_autonomy_gate_indirection_ceiling_followup.md) | Enforce Gate 1/2a at the actual outbound action — value-indirection defeats shell-text detection |
| [OI-001](#OI-001) | 2026-07-08 | 2026-07-16 | [oxford-cc-repo-health.md](oxford-cc-repo-health.md) | Purge 2 dangling disabled LAMS scheduled-task entries |
| [OI-002](#OI-002) | 2026-07-08 | 2026-07-16 | [oxford-cc-repo-health.md](oxford-cc-repo-health.md) | Decide `ora-cam-reconciliation-annual` year-round vs. seasonal timing |
| [OI-004](#OI-004) | 2026-07-16 | 2026-07-17 | [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md) | Add a real `Archived` property to the Tenant DB schema (blocked OI-003) |
| [OI-003](#OI-003) | 2026-07-16 | 2026-07-17 | [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md) | Build the Notion Tenant DB workbook mirror (`EXPORT_RentRoll` → Notion) |
| [OI-005](#OI-005) | 2026-07-16 | 2026-07-17 | [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md) | Dedup 2 stale Notion Heritage Pool Supply rows against the correct SRS row |
| [OI-006](#OI-006) | 2026-07-16 | 2026-07-17 | [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md) | Confirm 4 tenant turnovers + Soldier Trucking property conflict against executed leases |
| [OI-008](#OI-008) | 2026-07-17 | 2026-07-17 | [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md) | Sweep the Tenant DB for the Escalation-Date/Lease-Expiration column-mapping bug beyond the 7 rows already checked |
| [OI-014](#OI-014) | 2026-07-17 | 2026-07-17 | [reference_onedrive_business_scope.md](reference_onedrive_business_scope.md) | Confirm no ora-pm git clone inside any OneDrive sync root (real repo at C:\Users\Owner\ora-pm) |
| [OI-015](#OI-015) | 2026-07-18 | 2026-07-19 | ora-appsec-sweep first run (2026-07-18); Notion Ops Hub row `3a26ecd8-9e59-81e4-85d4-d08d0d5d920b` | Reachable/clonable ora-pm git history confirmed genuinely clean of real E. Fulton terms — no history rewrite needed; residual (a dangling blob still served via GitHub's Data API) spun off as OI-022 |
| [OI-017](#OI-017) | 2026-07-18 | 2026-07-26 | ora-appsec-sweep first run (2026-07-18) | ora-pm + oxford-command-center toolchain CVEs — both repos' vitest/vite CRITICAL+HIGH chain cleared (ora-pm 0 vulns; occ 30→9, 0 critical); wrangler/sharp and react-router (v8.3.0) also resolved on ora-pm. Residual npm-audit-fix pass on occ and the unrelated blank-tenant-portal defect tracked separately, not part of this item |
| [OI-016](#OI-016) | 2026-07-18 | 2026-07-19 | ora-appsec-sweep first run (2026-07-18) | ora-pm: `hono` bumped 4.12.23→4.12.31 (commit `c300867`), resolved HIGH CORS/Set-Cookie/path-traversal advisories; verified via `npm audit` |
| [OI-106](#OI-106) | 2026-08-09 | 2026-08-09 | L5 research triage of [[reference_concurrent_session_duplicate_hardening_work]]'s 2026-08-05 entry (three same-day duplicate-investigation near-collisions) | `engineering-router.py` now appends a fail-open, ASCII-only advisory ("N other session(s) active -- check list_sessions/event_log.md before duplicating investigation or analysis work") to any prompt that already fires a lane suggestion, using the existing `session_liveness.other_active_sessions()` reader — the correct trigger point (task start) for a collision shape claim_work.py's four fixed slugs structurally can't catch (no file was ever in contention until the duplicate work was already done). Built in an isolated worktree, `eos-review-gate` blocked the first commit as designed; independent review (pinned `claude-fable-5`) found 2 Important defects (a misleading test comment; a missing `isinstance(sid, str)` guard that would have let a payload with no `session_id` count itself as an "other" session) — both fixed pre-merge. 37/37 `hooks/tests` green pre- and post-merge. Merged `main` @ `4066213` (Gabriel confirmed in-turn), pushed to the backup remote `ZeOoba/ora-claude-config`. Rejected as part of the same triage: broadening `claim_work.py`'s file-claim model (nothing was ever claimable in the two triggering incidents) and a pre-commit `git status` hook (redundant with `shared-checkout-guard.py`, which already caught the third incident live) |
| [OI-020](#OI-020) | 2026-07-19 | 2026-08-05 | [event_log.md](event_log.md#2026-07-19) | ora-cowork-heartbeat: LAMS registry entry has no `approvedPermissions` grant (root cause, 3x documented since 07-16). No MCP tool on either surface can write this — only fix is Gabriel manually approving the Notion-tool prompt during a live unattended fire in Cowork's own Scheduled Tasks UI (a manual "Run Now" doesn't count). GitHub watchdog issue open, needs manual closure once genuinely fixed |
| [OI-025](#OI-025) | 2026-07-25 | 2026-08-05 | shared-checkout investigation, this session | `Claude_Workspace\00_Governance\Scheduled\` holds 100+ scheduled-task folders (incl. several `_archive_*` subfolders already in that same directory) whose live/dead status vs. the two documented fleet registries is unverified — one instance (`ora-tenant-hubspot-reconciliation`) was confirmed orphaned and archived this session; the rest (including apparent name-collisions with live CC tasks like `ora-am-brief`, `ora-weekly-hygiene`, `ora-health-guard`) are unaudited |
| [OI-029](#OI-029) | 2026-07-26 | 2026-08-03 | Repo-sweep session, 2026-07-26 | TWO live/unrotated credential exposures found: (1) `oxford-realty/oxfordra-net` git history has a plaintext `NETLIFY_AUTH_TOKEN` from an April WSL experiment (repo now archived to `archive/oxford-realty_archived-20260726/`, history NOT scrubbed); (2) Claude_Workspace `oxford-site` duplicate has a non-redacted Netlify MCP proxy token in a `.git-corrupted-20260716/` backup folder on disk — needs Gabriel to rotate BOTH tokens, then this folder specifically needs secure deletion (not mere archiving — never verified as-touched by this session per the ORA autonomy gate's oxfordra.net-path block on 2026-07-26, so the whole `Claude_Workspace/01_Workspace/oxford-site` duplicate is also still un-archived) |
| [OI-047](#OI-047) | 2026-07-31 | 2026-08-04 | ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch) | **MEDIUM — CLOSED 2026-08-04.** ora-pm's two cron jobs (`critical-dates-alerts`, `delinquency-check`) no longer call Resend; `RECIPIENTS` trimmed to `ggoldberg@oxfordra.net` only; the Worker now returns `email: {subject, body} \| null` and `C:\Users\Owner\ora-pm-cron\ping-crons.ps1` (the real live trigger — a standalone Windows Task Scheduler task, not the Claude fleet registry) sends it via Outlook COM. Dedup-before-send and non-fatal-on-send-failure both preserved, covered by tests + a 12-assertion PowerShell self-test. Deployed to production (PR #20, merge `5bbb262`) and verified with two REAL sends through the live trigger. See detail section for full evidence, including a separately-filed finding ([OI-076](#OI-076)) discovered along the way |
| [OI-076](#OI-076) | 2026-08-04 | 2026-08-04 | OI-047 final whole-branch review, 2026-08-04 | ora-pm's "ORA PM Crons" Windows Task Scheduler task (drives `critical-dates-alerts`/`delinquency-check` daily) was unregistered on this machine — `cron.log`'s last entry was 2026-06-24, ~6 weeks dead, likely lost in the 2026-07-09 machine migration to LAPTOP-CSHSCBE6 (task registrations are OS-level, don't travel with a file/repo copy). Re-registered and confirmed live (`NextRunTime` set); real backlog cleared same-day (10 critical-date alerts, 24 delinquent tenants / 7 late fees posted across the catch-up runs) |
| [OI-092](#OI-092) | 2026-08-05 | 2026-08-05 | `ora-lease-snapshot-refresh` run 2026-08-05; handoff session `3d9d97cf` | **MEDIUM** `External Loans Summary` computed next-12-month interest/principal over the half-open 366-day span `[TODAY(), TODAY()+366)`, capturing **13 payments instead of 12** whenever `TODAY()` landed on a loan's payment day-of-month — inflating annual debt service by one payment and depressing DSCR. **Workbook RESOLVED** (Gabriel's own edit 2026-08-05): window re-anchored to `(Assumptions!$B$30, EDATE(Assumptions!$B$30,12)]` with `B30 = EOMONTH(TODAY(),0)`, making the payment-day coincidence structurally impossible; zero `TODAY()+366` remain. Warehouse `debt_positions` was clean (all 8 snapshot dates fell on non-payment days); the one contaminated artifact, `data/snapshots/portfolio.json` from `61cc346`, was re-baked as `51d4039` (local only, **not pushed**). **Detector WITHDRAWN before shipping** (first attempt, `debt-service-window.ts`) — code review + REFUTE both found it cannot detect the defect it was built for (it counts schedule rows against its own correctly-computed window, never reading the `External Loans Summary` formula; reverting `H9` to the buggy form leaves its output byte-identical). **Retry BUILT, REVIEWED, REFUTEd, PR OPENED 2026-08-05** — `server/workbook/debt-service-crosscheck.ts` (`feat` `f66541b`), cross-checks the workbook's cached H/I against an independent full-schedule recomputation (keyed on distinct dates, not row counts, per [OI-096](#OI-096)). Independent code review found 3 critical findings incl. one reopening the exact OI-095 false-positive class, fixed (`f8bd519`); an adversarial REFUTE pass on the fix found 6 more (lender classification bypassable via `-ABS(...)` wrapping, a self-referential coverage floor, exact-equality duplicate-date matching, a principal-reconciliation blind spot on the window's leading row, 2 minor), fixed (`5d8d293`). **Then, while updating this tracker entry, found the fix's `isLender` exemption itself encoded OI-095's FIRST, SUPERSEDED ruling** — removed (`6098e42`); see [OI-095](#OI-095)'s "final basis: INCLUDE the balloon". Detector now applies the principal-reconciliation check uniformly to every loan, no borrower/lender distinction. 34 unit tests incl. 5 fixture-driven end-to-end through a real ExcelJS workbook (orchestrator itself had zero coverage before this — every REFUTE finding lived there); live-verified after each round — exactly 2 flags against the current workbook (1 tombstone-skip info flag, 1 true positive on 485 Walnut awaiting an Excel recalc+save), zero false positives. **PR:** https://github.com/ZeOoba/oxford-command-center/pull/261 — **MERGED 2026-08-05T22:13:45Z, commit `59d1995`, main.** Independent Code-surface session ran its own adversarial review before merge and found one further gap the REFUTE pass above missed: an unresolvable "Remaining Balance" header on a schedule sheet let the principal-reconciliation check (the one check that can see a balloon parked outside the Principal column) silently no-op with zero diagnostic — same failure class as the other blind-spot findings. Fixed with a failing test first (TDD), 34/34 green, folded into the same PR before merge. Verified 2026-08-09: 34/34 tests still green on current `main`; the duplicate worktree/branch `fix/oi-092-debt-service-detector` (PR #262) was closed unmerged the same day, superseded by #261. **Follow-up, 2026-08-09:** two non-blocking coverage gaps from the pre-merge independent review (the `rows: []` early-return path, and the duplicate-payment-date negative case — two same-date rows with genuinely different amounts, which must stay silent) were pinned with dedicated tests, no production logic changed. 36/36 green, `tsc`/`eslint` clean, isolated worktree `occ-wt-oi092-test-coverage` off `origin/main` (which had moved to `1ece592`/#263 by then — unrelated). **PR:** https://github.com/ZeOoba/oxford-command-center/pull/264 (branch `test/oi092-cheap-coverage`) — **MERGED 2026-08-09T14:49:15Z, squash commit `127f3d3`, main.** CI green (gate, refute-required, CodeRabbit) before merge; worktree removed, local + remote branch deleted. **Do NOT build the ">2 decimal places" detector** — fires on 6 of 11 loans, every one correct. **Residual:** (a) workbook `Claude Log` has no entry for the 08-05 edit (last row Turn 147, 08-03); (b) `SCHEDULE_SOURCES` (withdrawn draft only, not the shipped detector) hardcoded each schedule's range — moot, the shipped version derives ranges from the live formula |
| [OI-093](#OI-093) | 2026-08-05 | 2026-08-05 | surfaced by the OI-092 `portfolio.json` re-bake (`51d4039`) | **RESOLVED 2026-08-05 — journal sheet recreated, verified end-to-end (0 unintended changes elsewhere), see full entry for caveat on cached formula values.** Was **MEDIUM** (silent history split in the debt warehouse): the internal 2203-2207 Northwood loan had parsed with **no journal sheet**, changing its snapshot id from `internal-2203-2207-northwood` to `internal-2203-2207-northwood-no-journal-sheet`. `debt_positions` keys `ON CONFLICT(id, snapshot_date)`, so every future snapshot lands under a NEW key — silently orphaning the loan's prior history rather than continuing it; `monthsToMaturity` also went null → 105. **Diagnosed 2026-08-05:** full 50-sheet enumeration confirms **no Northwood journal sheet exists in any spelling**, so the parser's `⚠ NO JOURNAL SHEET` marker is **correct and reporting a real accounting gap**, not a parser defect — aliasing the id would hide a genuinely missing record. **Provenance problem:** workbook `Claude Log` Turn 144 (2026-08-03) states the sheet *was created* during the EXTERNAL→INTERNAL reclassification, and it is not there. **Gabriel ruled 2026-08-05:** create the journal sheet — but **chase the provenance first**, since "never completed" vs "created then removed" implies different things about the rest of that reclassification |
| [OI-094](#OI-094) | 2026-08-05 | 2026-08-05 | adversarial REFUTE pass on the OI-092 detector; independently re-verified against the live workbook | **MEDIUM now, HIGH from ~mid-2030** (understates annual debt service by $3.35M when it bites) — needs Gabriel's ruling to execute (workbook edit, Hard Invariant 4). `'External Loans Summary'!H9`/`I9` sum the Banwick-Morrison schedule over `B11:B70`, but the schedule's **final payment is row 71** and it carries the balloon (r71: 2031-06-05, principal 3,333,953.68, total $3,349,289.87 — matching Symetra loan 11153's documented balloon to within rounding). `K9` maturity = 2031-06-05, the very row the range stops one short of. **Audit COMPLETE 2026-08-05, all six ranges checked** (scanning 40 rows past each range end): Banwick is the **only** truncated range; 3540 E Fifth Ave, 9050 Red Branch, 29000 Information Ln, Restoration Church Trust and 485 S Walnut St all end on their final payment row. Reproduced exactly by a second independent audit (session `3d9d97cf`). **Gabriel ruled: consolidated fix** — one workbook session covering (1) extend the Banwick ranges to row 71, and (2) the February pair fix: six cells to `EOMONTH(Assumptions!$B$30,12)` **and** `B30` constrained to month-end. Both edits are required together — a 1,080-case simulation (120 month-ends × 9 pay-days) shows `EDATE` right-edge → 9 under-capture deviations, `EOMONTH` → 0, but `EOMONTH` under manual override (`B32` non-month-end) → **1,428 deviations**. Two findings this audit surfaced were **promoted out** so closing OI-094 on the range fix cannot silently close them: → [OI-095](#OI-095), [OI-096](#OI-096) |
| [OI-095](#OI-095) | 2026-08-05 | 2026-08-05 | OI-094 range audit, finding (b); promoted out per Gabriel ruling 2026-08-05 | **CLOSED 2026-08-05 — final basis: INCLUDE the balloon.** Superseded this session's earlier "no change" reading. `I15` now -$978,763.425 (was ~0); `J15` -$1,022,692.32. Gabriel confirmed 2026-08-05 he authorized the Turn 149 reversal; root cause was `I14`/`I15`/`I16` computing three different bases under one header, now made consistently forward-looking — see full entry. Historical framing below retained for context, superseded, not authoritative. Restoration Church Trust's balloon rows carry their amount in column `C` only, with `D`/`E` originally empty, so `'External Loans Summary'!H15`/`I15` (which sum `D`/`E`) exclude the $1,945,102.73 balloon / $972,551.37 Oxford share due 2027-02-20 from next-12-month principal return. **This paragraph is HISTORICAL — superseded same-day by Turn 149 and Gabriel's confirmation, see the CLOSED status above. Retained so the reasoning trail is visible, not as current guidance.** At the time, Gabriel ruled this was intended modelling (`C` = total payment, `D`/`E` = itemized split that balloon rows legitimately do not carry) and that `3540 E Fifth Ave`'s captured balloon vs RCT's excluded one was a principled borrower/lender asymmetry. Turn 149 found a different, more precise root cause — the three lender rows (`I14`/`I15`/`I16`) computed principal on three inconsistent bases, not one deliberate design choice — and fixed all three to a consistent forward-looking basis. RCT's balloon is now included. **Detector constraint SUPERSEDED:** the OI-092 detector retry must NOT be built to treat balloon-excluded lender principal as correct — RCT's current behavior (balloon INCLUDED, forward basis) is what the detector should expect on all three lender rows |
| [OI-031](#OI-031) | 2026-07-27 | 2026-09-19 | `orphaned-task-forensics` trace of the `ora-master-workbook-ingest` 2026-07-20 gap, [event_log.md](event_log.md#2026-07-27) | **CLOSED 2026-09-19 (verified) — fleet-status.py (~L326-361) has the missed-cycle detector; maintenance/_tests/test_fleet_status_missed_cycle.py exists. OI-058/070 stay open on their own terms.** Prior row text: `fleet-status.py`'s overdue/missed-stuck detectors are structurally blind to a single skipped weekly cycle on an already-established recurring task — neither check applies to it (confirmed by reading the script) |
| [OI-062](#OI-062) | 2026-08-04 | 2026-09-19 | `pending_reimport.py` frontmatter-norm session, 2026-08-04 | **CLOSED 2026-09-19 (verified) — ora-skills plugin-build.json no longer modified and _check_plugin.py gone; only unrelated untracked _archive dirs remain.** Prior row text: ora-skills MAIN checkout has unattributed uncommitted WIP (modified `plugins/ora-operations-extensions/plugin-build.json` version bump 0.1.5→0.1.6, plus untracked `_check_plugin.py`, both dated ~2026-07-29) — present at session start and still present after PR #38 merged; spans ≥2 sessions unclaimed, nobody has picked it up or discarded it |
| [OI-074](#OI-074) | 2026-08-04 | 2026-09-19 | OI-073 follow-up, root-causing why ora-pm migrations keep landing untracked | **CLOSED 2026-09-19 (verified) — SUPABASE_ACCESS_TOKEN and SUPABASE_DB_PASSWORD provisioned 2026-09-16; db-migrate.yml runs on 09-17 and 09-18 succeeded.** Prior row text: ora-pm migration-tracking root cause: no `SUPABASE_ACCESS_TOKEN` in the Code sandbox, so `supabase db push` (the only auto-tracking path) can't run here. Two-tier fix built (dashboard-paste tracking generator + inert `workflow_dispatch` CI job) — CI piece needs Gabriel-provisioned secrets before it can close |
| [OI-075](#OI-075) | 2026-08-04 | 2026-09-19 | Session brief follow-up — standing fix for skill-store/repo drift | **CLOSED 2026-09-19 (verified) — Superseded: ora-skill-cache-drift-alert retired 2026-08-09; ora-doctrine-integrity-guard engine 4 replaced it; PR #39 merged.** Prior row text: Skill-cache drift standing fix: new CC/MCP task `ora-skill-cache-drift-alert` (cron `*/30 * * * *`) runs `ora-skills/tools/repo_first_check.py --all` (built on [PR #39](https://github.com/ZeOoba/ora-skills/pull/39)) at a tighter cadence than the existing daily `ora-doctrine-integrity-guard`, auto-filing an OI item + Notion/email alert on new drift. Not yet closed — hasn't fired against a real finding |
| [OI-116](#OI-116) | 2026-08-11 | 2026-09-19 | Landing [PR #52](https://github.com/ZeOoba/ora-claude-config/pull/52) (`claim_work.py` refusal gate), 08-11 | **CLOSED 2026-09-19 (verified) — origin/main claim_work.py has is_sched_slug (L171) and _effective_ttl (L176); ora-skills bc42852 'v2.21 sched- carrier (OI-116)'. Section already said CLOSED 2026-09-07.** Prior row text: **MEDIUM** An **unattended** session can hold a `claim_work.py` slug indefinitely and cannot be released or contacted: `send_message` refuses delivery to unattended sessions, and `shared-checkout-guard`'s `_self_renew_claims` keeps re-stamping `claimed_at` so the 2h TTL never expires it. Hit **three times in one session** (`1d88885d` on `hooks-override-auth`; `05236b94` on `open-items-tracker`, twice — including while filing this item). The new refusal correctly names the collision and prints the holder's `host_session_id` per OI-108, but "message them" is a dead end for exactly this class of holder, leaving `--force` as the only exit — the operation the gate exists to make rare. |
| [OI-129](#OI-129) | 2026-08-12 | 2026-09-19 | `maintenance/_tests/test_check_open_items_duplicate_ids.py`, hit via `.git/hooks/pre-push` gate 2 while pushing two unrelated SKILL.md commits | **CLOSED 2026-09-19 (verified) — Main test file now treats orphaned/missing sections as advisory only (L186-190, 296-302); duplicates still fail.** Prior row text: **MEDIUM** A pre-push test asserts a live-shared-state invariant: `test_check_open_items_duplicate_ids.py` checks that *the canonical `open-items-tracker.md` has zero id collisions **right now***, and that file is written continuously by every session — six ids (OI-123→OI-128) were allocated by six different sessions inside one hour on 2026-08-12. Any session that writes a `### OI-NNN` detail section before its table row (or vice-versa) puts the file in a state that fails the assertion, which then **hard-blocks an unrelated session's push**. That is exactly what happened here: OI-125's section existed with no row, and it blocked two `ora-deal-*` SKILL.md commits that touch none of this. **Distinct from [OI-119](#OI-119)/OI-127, which are the LOAD/TIMEOUT class** — this failure is `exit 1`, a real assertion, and is fully deterministic: it reproduces on a completely idle machine any time a half-filed item is present, so retrying and raising timeout budgets cannot fix it. The fixture half of the same test file is correct and should be kept (it caught a seeded OI-027 duplicate in its own temp file this run). Fix options: (a) assert only against fixtures and move the canonical-file check to a non-blocking report, (b) keep it blocking but tolerate section-without-row as in-flight rather than a collision, or (c) gate it on the tracker being clean in HEAD instead of the working tree |
| [OI-132](#OI-132) | 2026-08-12 | 2026-09-19 | `~/.claude/scheduled-tasks/ora-sofr-direct-prefetch/SKILL.md` STEP 4 — observed live during that task's own 2026-08-12 run | **CLOSED 2026-09-19 (verified) — Commits 96a97d3 and 4ae999c (v1.2/v1.3) on origin/main; STEP 4 keys on am_brief_pending with a supersede-status log.** Prior row text: **LOW** STEP 4 verifies seconds after its own STEP 3c write, but `ora-am-brief` supersedes ~6 minutes later — so the "superseded by am-brief = PASS" branch that v1.1 added *specifically* for the catch-up-burst ordering hazard is effectively **unreachable**, and the run log records "my write landed, no supersede" as settled fact while a supersede is still pending. Measured 2026-08-12: prefetch dispatched `15:13:20.983Z`, am-brief `15:13:21.612Z` (629 ms apart); prefetch verified at `15:14:11Z` and logged no supersede; am-brief rewrote §2 at `15:20:26Z`. **No data harm that run** — am-brief independently pulled the NY Fed API and matched all five SOFR fields exactly. Cost is a false run-log claim plus silent undercounting of how often the burst inverts producer order. Cheap fix available: STEP 2 already computes `am_brief_pending`, so condition STEP 4's wording on it rather than adding a wait |
| [OI-134](#OI-134) | 2026-08-12 | 2026-09-19 | Gabriel-approved in-turn 2026-08-12 as option (c), alongside (a) the sweep remediation ([PR #271](https://github.com/ZeOoba/oxford-command-center/pull/271)); detail in [project_deal_join_id_based_redesign_queued_2026-08-12.md](project_deal_join_id_based_redesign_queued_2026-08-12.md) | **CLOSED 2026-09-19 (verified) — oxford-command-center #273 (6e7c5bd) on main; joins on notionDealId, dealJoinKey now only a detection-only migration tripwire.** Prior row text: **QUEUED — approved, not started.** Retire name-based seed↔Notion deal joining in favour of a **stable shared deal id** (a `Deal ID` on the Notion Acquisition Pipeline Tracker mirrored as `id` in `src/data/seed-deals.ts`), so `mergeDeals` joins on an opaque key no rename, locality suffix, alias, or punctuation variant can perturb. `dealJoinKey` (`server/sources/deal-name.ts`) strips the `" — City, ST"` tail before matching — but that suffix exists *precisely because* bare street names repeat across metros, so the key deletes the only disambiguator, and **confidentiality rides on the join** (a wrong merge folds an unmatched, fail-closed-confidential row into a public seed record — Hard Invariant 3). Four adversarial passes 2026-08-11/12 yielded 9+7+5+6 defects concentrated here, incl. a CRITICAL cross-side wrong merge with executed repros, an alias path bypassing the corroboration guard, corroboration inert for **11 of 20 live rows**, and a degenerate `acceptedPairKey` (`"k\|\|k"`) that grandfathers all future collisions. Each fix needed *another* corroboration signal bolted on — the signature of a wrong primitive, not unlucky bugs. Acute defects were remediated by PR #271; this is the structural fix. Migration must be fail-closed: a missing/duplicate id **refuses**, never falls back to name matching |
| [OI-137](#OI-137) | 2026-08-12, **FIX LANDED 2026-08-17** | 2026-09-19 | Control run while verifying [PR #268](https://github.com/ZeOoba/oxford-command-center/pull/268)'s test failures were pre-existing; re-confirmed against `origin/main` at `c5db68c`; fix landed same day as an independent re-derivation of this exact item (OI-186, retracted as duplicate — see below) | **CLOSED 2026-09-19 (verified) — 680018f (structural-mismatch status) and #285 on main. The gate:ci exclusion is by design, tracked as OI-254. Live cross-check not re-run.** Prior row text: **MEDIUM-HIGH, mostly resolved.** `npm run reconcile:noi-crosscheck`'s Spine A (workbook, current rent roll) vs. Spine B (warehouse `oxfordNoi`, latest-full-year historical actuals) disagreement was root-caused to recently-leased/acquired properties whose comparison-year actuals predate the current rent roll — "neither spine is defective." **Fixed in `680018f`** (Gabriel, in-turn ruling): `classifyNoiReconciliation` gained a `structural-mismatch` status — fires only on positive, corroborated evidence (leases starting on/after the comparison period covering ≥half the dollar delta, or an acquisition since then plus some corroborating leasing activity), gated off entirely on any sign-inverted disagreement. Adversarially reviewed; 3 real gaps found and closed (uncorroborated ownership signal, `Lease.status` not checked, CLI summary miscounting). 57 tests (24 new), full suite 3672/3672. **Verified live 2026-08-17:** Livingston and Raytown now correctly downgrade to `structural-mismatch`/warn (no longer fail the gate); Westerville stayed large-drift/error until [OI-184](#OI-184)'s propertyId fix — **[OI-184](#OI-184) MERGED 2026-08-17/18 ([PR #285](https://github.com/ZeOoba/oxford-command-center/pull/285)), all 3 originally-failing properties now clear, 0 errors portfolio-wide**, confirmed by re-running the cross-check against the real warehouse DB with the merged fix applied. `gate:ci` still excludes this check by design (needs a live workbook/warehouse) |
| [OI-139](#OI-139) | 2026-08-12 | 2026-09-19 | `fleet-status.py`'s `find_missed_cycles()` CRON-AWARE GUARD fix (commits `40b6176`/`30d2869`, merged to `main` and pushed as `08e0daa`); Cowork handoff "Health Guard FAIL-Aging Follow-Up" 2026-08-11, `scheduled-tasks/ora-health-guard/SKILL.md` C.1.1 | **CLOSED 2026-09-19 (verified) — Accepted-tradeoff design on main (MISSED_CYCLE_INTERVAL_MULTIPLE = 1.5, commit 08e0daa); no open work.** Prior row text: **LOW — accepted tradeoff, documented, not a defect.** The 2026-08-11 fix that made the missed-cycle detector cron-aware (escalate only past `max(24h, 1.5x own cadence)`, replacing the flat 24h wall that produced 8/13 false positives on 2026-08-10) is pure cadence math with no runtime signal for "was this a genuine catch-up burst." The superseded per-run SKILL.md logic additionally suppressed a `gap ≈ 1x interval` entry only when a late wake was detected *that run*, and otherwise escalated immediately as a likely phantom dispatch or dead task — a signal the code-level threshold structurally cannot see. **Consequence:** a task that misses exactly one slot with the machine fully up (no catch-up excuse available) now surfaces one cycle later than the old per-run logic could have caught it. Deliberate, Gabriel-approved simplification (the 2026-08-11 Cowork handoff spec explicitly specified the 1.5x-cadence rule) — do not re-litigate the threshold on this row alone. **Re-open only if a real single-slot dead-task/phantom-dispatch incident is observed and traced to this specific gap** — do not preemptively bolt an A.0-style runtime signal back into the code threshold without one |
| [OI-140](#OI-140) | 2026-08-12 | 2026-09-19 | Hit live while verifying the [OI-136](#OI-136) filing against a `git show HEAD:` extract — the checker reported a defect that existed only in the working tree | **CLOSED 2026-09-19 (verified) — check-open-items-duplicate-ids.py on main now rejects any CLI argument with exit 2.** Prior row text: **MEDIUM** `maintenance/check-open-items-duplicate-ids.py` **silently ignores its CLI path argument** and always reads the canonical tracker. `main()` does `path = tracker_path()` (line 180) → `TRACKER_PATH_OVERRIDE or DEFAULT_TRACKER_PATH`; **`sys.argv` appears zero times in the file** — no argparse, no positional handling. Passing a nonexistent path still returns a normal clean canonical report, because the `COULD NOT READ %s ... treat as a check failure` branch is unreachable from the CLI. Three things make it read as a working feature: it prints the path it checked, it formats a path into that error branch, and it accepts an argument without complaint. **Tests do not catch it** — `_tests/test_check_open_items_duplicate_ids.py` drives `main()`'s read path by assigning `codc.TRACKER_PATH_OVERRIDE` (a module attribute), so the logic is covered and the entry point never is. **Production caller is unaffected**: `ora-weekly-hygiene` Block N passes no argument. The harm is ad-hoc verification of a worktree copy / candidate edit / `HEAD` extract, which silently returns a verdict about a *different file* — false FAIL (blaming your copy for a live-file defect) or false PASS (your broken copy looks clean because the live one is). A verification tool that answers about an artifact you did not name is the [[feedback_verified_null_vs_inferred_null]] failure in its purest form |
| [OI-147](#OI-147) | 2026-08-13 | 2026-09-19 | ECC repo intake ([external-artifact-intake](../../skills/external-artifact-intake) ruling, Gabriel 2026-08-13, this session) | **CLOSED 2026-09-19 (verified) — Section already CLOSED (REJECTED); shell_tokenizer.py does not exist on main or in the tree.** Prior row text: **REJECTED after a full build + adversarial gauntlet — do not re-attempt without reading the evidence first.** Built `hooks/lib/shell_tokenizer.py`, a real recursive-descent quote/substitution-state tokenizer (not a regex) adapting ECC's `gateguard-fact-force.js` technique, integrated as a downgrade-only narrowing of `ora-autonomy-gate.py` Gate 2b (falls back to today's exact broad match on any parse uncertainty). Correctly classified all 3 historical bypass commands as dangerous, passed a mutation battery (6/8 killed, 2 proven equivalent/safe-direction), and passed all 72 tests (66 original + 6 new) including the 3 historical bypasses run through the full integrated hook. **Killed in Round 1 of the mandated 3-round adversarial gauntlet** (`pr-review-toolkit:code-reviewer`, opus): confirmed live, sandbox-verified bypass — quoting a path operand (`cp evil.html 'oxford-site/index.html'`) or wrapping in an interpreter (`bash -c "..."`, `powershell -Command "..."`, `eval "..."`) makes the tokenizer confidently (and wrongly) classify the write as fully inert, since **quoting suppresses metacharacter interpretation, it does not remove text from the command's argument vector** — a categorically different, more fundamental problem than the quote-state-tracking bugs rounds 1-3 (2026-07-16) found, and NOT fixable by deepening the parser (would need shell command-semantics modeling — which command consumes which argument and whether it writes — a strictly larger problem). Independently found: unbounded `$()`-nesting recursion in the tokenizer throws an uncaught `RecursionError`, which `ora-autonomy-gate.py`'s `main()` has no outer try/except for, crashing Gate 2b entirely (exit 1, non-blocking) rather than just skipping the narrowing — an attacker-triggerable disable of Hard Invariant 2's sole enforcement, strictly worse than a narrowing bug. **Everything reverted** (`git checkout --` on `ora-autonomy-gate.py`/its test file, `shell_tokenizer.py` + its tests deleted) — nothing landed, worktree carries only OI-148's unrelated changes now. Full evidence trail: [[feedback_autonomy_gate_matcher_cannot_be_safely_narrowed]] Round 4 section. Do not re-attempt the quote-state-narrowing approach; a 5th attempt needs a command-semantics model, not a better tokenizer |
| [OI-149](#OI-149) | 2026-08-13 | 2026-09-19 | Landing [OI-148](#OI-148), PR [#94](https://github.com/ZeOoba/ora-claude-config/pull/94) — pre-push gate blocked on this, overridden (Gabriel approved in-turn) | **CLOSED 2026-09-19 (verified) — Allowlist on main (doctrine-integrity-probe.py ~L346) repopulated for morning and schedule 2026-08-14; probe not re-run. PR #99 follow-ups merged into a feature branch, reaching main by other routes.** Prior row text: **LOW** `maintenance/test-doctrine-integrity-probe.py`'s known-plugin-skill allowlist is stale: flags `morning`, `register-scheduled-task`, `schedule` as unresolved, but all 3 are live installed `anthropic-skills` plugin skills (confirmed against this session's own SessionStart skill listing). Blocks the pre-push gate for ANY push right now, regardless of diff content — hit while landing an unrelated `hooks/**` change. Needs: find and update the probe's plugin-skill allowlist (likely a hardcoded list or stale-generated manifest in `maintenance/doctrine-integrity-probe.py`) to recognize these 3 |
| [OI-151](#OI-151) | 2026-08-14 | 2026-09-19 | Independent review (`claude-fable-5`) during PR [#99](https://github.com/ZeOoba/ora-claude-config/pull/99) | **CLOSED 2026-09-19 (verified) — On main the array fingerprint is [array:%d:%s] with a digest.** Prior row text: **MEDIUM** `property_register_snapshot_diff.py` line 165: array rollups fingerprint by LENGTH ONLY (`"[array:%d]" % len(...)`), so an equal-length element swap is a SILENT false negative — the exact failure class the script exists to prevent. Latent only while relations stay empty |
| [OI-152](#OI-152) | 2026-08-14 | 2026-09-19 | Independent review (`claude-fable-5`) during PR [#99](https://github.com/ZeOoba/ora-claude-config/pull/99) | **CLOSED 2026-09-19 (verified) — On main the retry catches TimeoutError, with a comment citing OI-152.** Prior row text: **LOW** `property_register_snapshot_diff.py` lines 344-355: a socket read timeout on the RESPONSE BODY raises `TimeoutError`, which matches neither `HTTPError` nor `URLError`, so it bypasses the bounded retry the comment at :340 claims to provide. Fails loudly (traceback, no state written), so robustness not correctness |
| [OI-154](#OI-154) | 2026-08-14 | 2026-09-19 | ora-task-integrity-guard follow-up session, PR [#99](https://github.com/ZeOoba/ora-claude-config/pull/99) | **CLOSED 2026-09-19 (verified) — The 8-guard roster line is committed in CLAUDE.md on origin/main and matches the working tree.** Prior row text: **MEDIUM** CLAUDE.md's inline 8-guard `Guards:` roster restore (reverting half of `8438df1`, which silently disabled doctrine-integrity-probe Check 11) is edited in the working tree but NOT COMMITTED — another session holds unrelated staged files, and the isolated-commit path finishes with a bare `git commit` that would sweep them in. Until it lands, Check 11 is still disabled on the branch |
| [OI-158](#OI-158) | 2026-08-15 | 2026-09-19 | Manual T3-5 cross-check (Gabriel-directed workflow-optimization pass), ahead of `ora-tenant-hubspot-reconciliation`'s next scheduled run (2026-09-01) | **CLOSED 2026-09-19 (verified) — Live HubSpot: deal 'Sky Shield - Lease Renewal 2026-09-30' is closedwon, close date 2029-08-31, modified 2026-09-18.** Prior row text: **DATE-MISMATCH** Sky Shield — workbook `leaseEnd 2029-08-31`, `status Active`; HubSpot deal "Sky Shield — Lease Renewal 2026-09-30" still `appointmentscheduled`, `closedate 2026-09-30`. Lease renewed in the workbook but the original HubSpot renewal deal was never closed out — same failure class as the 2026-07-16 lease-date correction (J&R/Stone Crest/Chesapeake), different symptom: stale open deal rather than stale wrong date |
| [OI-159](#OI-159) | 2026-08-15 | 2026-09-19 | Manual T3-5 cross-check (Gabriel-directed workflow-optimization pass), ahead of `ora-tenant-hubspot-reconciliation`'s next scheduled run (2026-09-01) | **CLOSED 2026-09-19 (verified) — Live HubSpot: deal 'Medspeed - Lease Renewal 2026-08-31' is closedwon, close date 2029-08-31.** Prior row text: **DATE-MISMATCH** Medspeed, LLC — workbook `leaseEnd 2029-08-31`, `status Active`; HubSpot deal "Medspeed — Lease Renewal 2026-08-31" still `appointmentscheduled`, `closedate 2026-08-31`. Lease renewed in the workbook but the original HubSpot renewal deal was never closed out |
| [OI-172](#OI-172) | 2026-08-16 | 2026-09-19 | Rev 2 fleet re-check (session 6797e01b); reopens the T3-12 follow-up | **CLOSED 2026-09-19 (verified) — fleet-roster.md (generated 2026-09-14 from live registries) lists ora-passed-deal-tracker on the CC fleet only.** Prior row text: **MEDIUM — COWORK-ONLY WRITE, do not retry from Code.** `ora-passed-deal-tracker` is live on BOTH fleets at `30 6 15 * *`. The CC copy is the one that must SURVIVE (it alone reaches the Outlook COM send path); the LAMS twin must be disabled from a Cowork session. Ids collide and CC `list_scheduled_tasks` shows no LAMS entries, so an `enabled:false` issued from Code hits the WRONG copy. Double-fire guard is live, so 2026-09-15 is mitigated — the defect is not. |
| [OI-041](#OI-041) | 2026-07-31 | 2026-09-19 | ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch) | **CLOSED 2026-09-19 (verified) — On ora-pm origin/main every flagged route does safeParse after req.json() (budgets, insurance, renewals, units, cam, leases, tenants).** Prior row text: **MEDIUM** ora-pm mass assignment — 10 handlers pass `await c.req.json()` straight into `.insert()`/`.update()`/`.upsert()` with no Zod schema (`budgets.ts:25`, `insurance.ts:35,46`, `renewals.ts:22`, `units.ts:20,28`, `cam.ts:23-24`, `leases.ts:74,98`, `tenants.ts:62`) while sibling routes correctly use `safeParse`. `budgets.ts:25` also accepts an ARRAY body, making the upsert unbounded in row count. Admin-authenticated only, so integrity/defense-in-depth rather than a breach path — but an admin (or anything holding an admin JWT, see OI-036) can set columns the UI never exposes including `id` and `created_at` |
| [OI-042](#OI-042) | 2026-07-31 | 2026-09-19 | ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch) | **CLOSED 2026-09-19 (verified) — Portal and route sites return 'DB error'; OI-063 sweep merged. Two error.message leaks remain at cron.ts:690-691, reachable with the cron secret only, not by tenants.** Prior row text: **MEDIUM** ora-pm returns RAW Postgres error messages to clients from ~20 call sites (`portal.ts:50,74,93,117,141`, `insurance.ts:38,50`, `cam.ts:79`, `reports.ts:15,27,35,53,57,62`, `cron.ts:40,131,167,227`, `units.ts`, `budgets.ts`, `renewals.ts`, `webhook.ts:20,40`). `server/middleware/error-handler.ts` sanitizes *thrown* errors and its comment claims raw DB messages are never exposed — but that only covers the catch path; these sites `return c.json({error: error.message}, 500)` from a Supabase result. Several are on `/api/portal/*`, reachable by any authenticated tenant, disclosing table/column/constraint/RLS-policy names as a free schema map |
| [OI-064](#OI-064) | 2026-08-03 | 2026-09-19 | REFUTE pass on the [OI-035](#OI-035) fix, 2026-08-03 | **CLOSED 2026-09-19 (verified) — ora-pm PR #39 (fix/oi-064-paynow-retry-idempotency) merged; stripe.ts has a resume path with an idempotency window.** Prior row text: ora-pm portal payment retry doesn't dedupe as the OI-035 fix's commit message claims — every retry re-links the bank account, producing a new `payment_method_id`, so Stripe's idempotency layer rejects the reused key as a mismatch (caught, returned as a clean 400 — fails safe, no double charge) rather than returning the original PaymentIntent. Risk is operational (tenant sees "failed" for a payment that went through, may pay again another way), not a code-level double-charge. The retry-recovery test is regex-over-source-text, never actually exercised this |
| [OI-065](#OI-065) | 2026-08-03 | 2026-09-19 | REFUTE pass on the [OI-035](#OI-035) fix, 2026-08-03 | **CLOSED 2026-09-19 (verified) — ora-pm PR #41 merged; stripe.ts uses reserve_payment_intent RPC under pg_advisory_xact_lock.** Prior row text: ora-pm `POST /api/stripe/payment-intent` has no lock between the `ar_ledger.balance` read and PaymentIntent creation — two genuinely concurrent requests (two tabs, or a bypassed client guard) each read the same stale balance and each create a separate, individually-valid PI, exceeding the true balance. Requires the tenant's own concurrent action, not a third-party attack. Outside OI-035/OI-040's original scope |
| [OI-082](#OI-082) | 2026-08-05 | 2026-09-19 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **CLOSED 2026-09-19 (verified) — ora-pm PR #38 merged; migration 0015_payments_idempotency_key.sql adds payments_idempotency_key_uniq. Production application not separately confirmed; db-migrate runs of 09-17/18 succeeded.** Prior row text: **MEDIUM** ora-pm `payments` has no idempotency or uniqueness constraint for non-Stripe methods. `0011`'s two partial unique indexes cover `stripe_payment_intent_id` and `(lease_id, autopay_period)` only; `method IN ('check','wire','other')` rows are NULL on both and so fall outside each. `charges` got `idempotency_key TEXT UNIQUE NOT NULL`; `payments` did not. A double-submitted admin form or replayed import writes two identical rows and `ar_ledger`'s `payment_totals` CTE sums both — the tenant's balance silently drops, and that understated balance then feeds the payment-intent cap and the autopay lifetime cap. Same failure class as the two AR bugs already shipped here (cartesian fan-out, divide-by-100): the join was fixed, the write path was not |
| [OI-224](#OI-224) | 2026-09-02 | 2026-09-19 | `ora-appsec-sweep` 2026-09-02 (ora-pm @ `ca62ecb`, security-auditor dispatch) | **CLOSED 2026-09-19 (verified) — origin/main server/lib/schemas.ts has method: z.enum(['check','wire','other']); ach_stripe not accepted.** Prior row text: **MEDIUM — the admin manual-payment route's schema allows `method:'ach_stripe'` with no `stripe_status`, producing rows the ledger never counts but the admin UI shows as paid.** `PaymentInsertSchema` doesn't restrict `method` to `check`/`wire`/`other` despite the route comment saying it should; such a row has NULL `stripe_status` so `ar_ledger` (which only sums `succeeded`) excludes it while `GET /api/payments`/admin PaymentsList display it as a recorded payment. Related but distinct from [OI-082](#OI-082) (missing uniqueness on non-Stripe methods, a double-counting bug in the opposite direction). Not applied |
| [OI-225](#OI-225) | 2026-09-02 | 2026-09-19 | `ora-appsec-sweep` 2026-09-02 (oxford-command-center @ `d30d71e`, security-auditor dispatch) | **CLOSED 2026-09-19 (verified) — origin/main server/ai/tools.ts has confidentialScope keyed on the confidential flag; agent.ts has a pre-send scan tagged OI-225.** Prior row text: **MEDIUM — the AI agent's tool results can carry confidential-deal identifiers to the Anthropic API with no redaction, unlike every other egress path in the repo.** `get_deals`/`search_entities` correctly drop `confidential:true` rows, but `get_alerts`/`evaluateConditions` and `get_relationships` do not, and `agent.ts` appends tool results verbatim into the outbound `messages` with no pre-send scan — while `comps.ts`, `om-extract.ts`, and `narrative.ts` all fail closed on the same egress. Asking "any deadlines?" with a confidential deal in an alert-eligible stage sends its name/detail to api.anthropic.com. Not applied |
| [OI-228](#OI-228) | 2026-09-02 | 2026-09-19 | `ora-appsec-sweep` 2026-09-02, DISPATCH INTEGRITY GATE assertion 4 (post-hoc model-floor probe) | **CLOSED 2026-09-19 (verified) — origin/main check-dispatch-model-floor.py has commit 1b445cb adding claude-mythos-5-1; section said CLOSED 2026-09-08 (PRs #176/#177). Live ~/.claude checkout is behind origin/main.** Prior row text: **LOW — tooling defect, not a real floor breach: `check-dispatch-model-floor.py`'s `MODEL_RANK` table doesn't recognize `claude-fable-5-1` (the current Fable 5.1 model id) and ranks it UNKNOWN (fail-closed, -1), firing exit 1 on both this sweep's subagents even though each ran 100% on Fable with zero fallback events — the best possible outcome, not a violation.** `MODEL_RANK` only has bare `claude-fable-5`/`claude-mythos-5`; the table appears to predate the Fable 5.1 rollout. Verified directly: `agent-ae4ff02601b0e1cdb.jsonl` (ora-pm, 62 msgs) and `agent-ae7f6e4c49d408b89.jsonl` (occ, 110 msgs) both show `model:"claude-fable-5-1"` on every line, 0 fallback blocks. Distinct from [OI-052](#OI-052) (the documented fable→opus mid-run fallback pattern, ruled compliant) — this is a false-positive FAIL from a stale id mapping, not a fallback of any kind. Per the sweep's own doctrine this still had to be recorded and escalated (never silently loosen the assertion), but the fix here is adding `claude-fable-5-1`/`claude-mythos-5-1` (rank 100) to `MODEL_RANK`, not touching the floor logic. Not applied |
| [OI-233](#OI-233) | 2026-09-05 | 2026-09-19 | `ora-appsec-sweep` 2026-09-05 (ora-pm @ `ca62ecb`, security-auditor dispatch) | **CLOSED 2026-09-19 (verified) — ora-pm PR #41 merged; stripe.ts calls reserve_payment_intent() (migration 0014) and inserts a pending row keyed by client_request_id before Stripe.** Prior row text: **MEDIUM — `server/routes/stripe.ts:172-224` confirms the Stripe PaymentIntent (real ACH debit) before the ledger insert; if that insert fails for any reason OTHER than the OI-035 dedupe unique-constraint, the confirmed debit has no ledger row and no compensating record.** Same "money moved, correctness assumed a guarantee that isn't enforced" class as [OI-222](#OI-222)/[OI-223](#OI-223); OI-035's unique index absorbs a *duplicate* insert but not a *failed* one. Candidate fix: write a `pending` row keyed by `client_request_id` before calling Stripe, update with the PI id after; have the webhook upsert-by-PI when no row matches. Not applied |
| [OI-255](#OI-255) | 2026-09-10 | 2026-09-19 | Cross-repo architecture-diagram review (Gabriel-directed, this session) | **CLOSED 2026-09-19 (verified) — ora-pm PR #40 merged; package.json has lint (--max-warnings 0) and check:refute; ci.yml runs both ahead of deploy steps.** Prior row text: **HIGH (gate strength inverted against blast radius).** `ora-pm` is the only ORA repo that debits real bank accounts (Stripe ACH autopay, late-fee posting) and carries the weakest gate of the three application repos: `package.json` has `"lint": "tsc --noEmit"` — there is no linter, `lint` is an alias for `typecheck` — no `gate`/`check:refute`/reconcile script of any kind, and `.github/workflows/ci.yml` runs typecheck → test → build → `wrangler pages deploy` **on every push to `main`**. `oxford-command-center`, which only READS money, runs `eslint . --max-warnings 0` plus a `refute-required` PR job enforcing a Refute-Reviewed trailer on financial-decision diffs. Nothing equivalent guards `server/lib/billing.ts`, `server/routes/cron.ts`, `server/routes/stripe.ts` or `server/lib/cam.ts`. Fix direction: add ESLint and stop aliasing `lint`; port `scripts/check-refute-required.ts` scoped to those four paths and make the deploy step depend on it |
| [OI-259](#OI-259) | 2026-09-10 | 2026-09-19 | Cross-repo architecture-diagram review (Gabriel-directed, this session); overlaps [OI-175](#OI-175) | **CLOSED 2026-09-19 (verified) — AAOS PR #4 merged (cc8fbc6); .github/workflows/ci.yml on origin/main and check-contract-drift.py referenced in ora-aaos-publish-contracts SKILL. Green CI run not separately confirmed.** Prior row text: **MEDIUM (unguarded correctness on the agent-coordination substrate).** `C:\Users\Owner\AAOS` has 216 tests and **no CI at all** — `.github/workflows` does not exist, so `python -m unittest discover -s tests` runs only when a human types it. AAOS owns the lease/lock discipline that stops two agents clobbering each other's task state, and its one documented Critical bug (two near-simultaneous appends to `aaos-events.ndjson` silently clobbering each other, `docs/GATE3-REVIEW.md`) is guarded by those tests alone. Compounding asymmetry: `tools/publish-contracts.py` runs 1x/day (weekdays 09:15 ET) as `ora-aaos-publish-contracts`, but `tools/check-contract-drift.py` — the script written to prove that publish worked — is referenced by **nothing** (0 hits across `~/.claude/scheduled-tasks/` and any CI). Fix direction: one GitHub Actions workflow (`pip install jsonschema` + `unittest discover`, ~31s, no secrets, no data access) on push/PR, plus `check-contract-drift.py` as a second step on the existing publish task. Closes OI-175's jsonschema pin as a side effect |
| [OI-263](#OI-263) | 2026-09-10 | 2026-09-19 | Surfaced by [OI-259](#OI-259)'s new CI workflow on its FIRST run ([ZeOoba/AAOS PR #4](https://github.com/ZeOoba/AAOS/pull/4), run 34514715973) — green locally, red on every runner | **CLOSED 2026-09-19 (verified) — AAOS tests/test_queue_scripts.py derives the in-scope artifact under REPO_ROOT (L523-538); PR #4 merged. Green CI run not separately confirmed.** Prior row text: **MEDIUM (false-confidence test coverage on the colonization guard).** 9 AAOS tests in `tests/test_queue_scripts.py` (`PostHandoffHappyPath/Idempotency/Blocker` classes) assert that a handoff artifact is IN write-scope, but `make_in_scope_artifact` (`tests/test_queue_scripts.py:522,528`) creates it under `REPO_ROOT` while the production `agent-registry.json:18` declares `claude-code`'s scope as the literal absolute `"C:/Users/Owner/AAOS/**"`. They pass ONLY because the operating machine's checkout happens to sit at that exact path — **they validate Gabriel's directory layout, not `match_write_scope()`'s logic**, and would break identically if the repo were ever moved or cloned elsewhere. On CI both matrix legs fail 9/226 with `WRITE-SCOPE VIOLATION: path '/home/runner/work/AAOS/AAOS/aaos-artifacts-*/evidence.txt' is outside agent 'claude-code's declared write_scope`. No seam exists to fix it cheaply: `tools/post-handoff.py:26` states outright "There is no `--registry` override here", and `_aaos_common.registry_path()` hard-returns `REPO_ROOT / "agent-registry.json"`. **Blocks OI-259** — PR #4 is deliberately held unmerged rather than landing a red-on-arrival CI. Fix direction (needs its own review — this touches the colonization guard's inputs): add a `--registry` override to `post-handoff.py` mirroring `validate.py`'s existing one, and have the test base write a temp registry whose `write_scope` is derived from `REPO_ROOT` at runtime |
| [OI-264](#OI-264) | 2026-09-10 | 2026-09-19 | Surfaced by [OI-259](#OI-259)'s CI on [ZeOoba/AAOS PR #4](https://github.com/ZeOoba/AAOS/pull/4) (run 34518125534, 3.11 leg; 3.13 leg passed the SAME run) | **CLOSED 2026-09-19 (verified) — AAOS acquire_lease writes a staged sidecar and links it with _exclusive_link, so the lock is never empty. Race test not re-run.** Prior row text: **MEDIUM-HIGH (real concurrency defect in the lock protocol — the one thing AAOS exists to get right).** `_aaos_common.acquire_lease()` creates the lock with exclusive-create and writes its JSON content as a SEPARATE step. A second writer that opens the lock inside that window reads a zero-byte file and `load_json` raises `CorruptStateError: unparseable JSON at …/locks/t-race-8.lock: Expecting value: line 1 column 1 (char 0)` — instead of the clean `denied` the protocol promises. `tests/test_aaos_common.py::AcquireLeaseRaceTests::test_genuine_race_exactly_one_acquired_never_two` therefore observes `['acquired']` where it asserts `['acquired', 'denied']`, and `Scenario03TwoWritersRaceTests` fails with it. **Intermittent, not deterministic** — passed on the 3.13 leg of the same run, and reproduced once locally under heavy load (13 concurrent sessions) while passing in isolation and on two subsequent full runs, so this is a genuine timing window, not a platform-only artifact. The consequence is worse than a flaky test: a real contended lease raises a corruption error rather than denying, and `CorruptStateError` is the signal AAOS reserves for genuinely damaged state — so a routine race would read as data corruption and could trigger the wrong operator response. Also directly on the Cowork sandbox path (`docs/COWORK-BOOTSTRAP.md` contemplates Linux sandboxes). Fix direction — **the reader side, not the writer**: an existing-but-empty/unparseable lock inside the settle window means "held by a writer mid-create", i.e. deny/retry, not corrupt. That is a semantic change to the lease protocol and needs its own adversarial REFUTE pass (Engineering OS done-bar), NOT a CI-unblocking patch. **Do not fix by skipping or weakening the race test** |
| [OI-310](#OI-310) | 2026-09-17 | 2026-09-19 | `/code-review` (high effort, 8-angle + verify) on [ora-pm PR #42](https://github.com/ZeOoba/ora-pm/pull/42) (OI-278 void fix), this session | **CLOSED 2026-09-19 (verified) — ora-pm PR #43 merged 2026-09-18; DELETE handler selects source, voided_at; push CI at 5e822e3 succeeded. Deferred follow-ups (atomic delete, DB-level guard) filed as a new item.** Prior row text: **LOW-MEDIUM (latent audit-trail gap, PLAUSIBLE — not currently reachable) — `server/routes/charges.ts` DELETE `/:id` blocks deleting `source='auto'` charges but never checks `voided_at`, even though migration 0016's whole premise (this same PR) is "void, never delete" for an audit trail.** The route's own comment defers enforcement to a future manual-void action that doesn't exist yet — today the only `voided_at` writer (migration 0017) is scoped to `source='auto'` rows, which DELETE already refuses on the separate `source` check, so the two conditions never currently overlap. Once any future manual-void feature sets `voided_at` on a `source='manual'` charge, this route will still hard-delete it on request, destroying the audit record the void mechanism exists to guarantee. Fix direction: add a `voided_at IS NOT NULL` guard to the DELETE handler (400, mirroring the existing `source==='auto'` rejection), landed before or alongside whatever ships the manual-void endpoint. **PR OPEN 2026-09-18 (excess-usage sweep): [ora-pm PR #43](https://github.com/ZeOoba/ora-pm/pull/43)** — guard + 4 tests (the 2 guard tests fail against the unpatched route, the 2 controls pass either way); 433 tests/44 files green, typecheck clean. **Adversarial REFUTE pass run (Fable tier) after CI's `check:refute` gate blocked the first push** — guard CONFIRMED correct + fail-closed, no other app-layer charge-delete path exists; 1 finding fixed (missing fail-closed test), **2 deferred and recorded on the PR: (a) read-then-delete TOCTOU needs the atomic conditional `.delete().is('voided_at',null)` form, (b) no BEFORE DELETE trigger / DELETE RLS policy, so a service-role or dashboard DELETE bypasses the app guard entirely.** Neither reachable today; **both should land before any manual-void endpoint ships.** MERGED 2026-09-18. **REGRESSION FOUND AND FIXED SAME DAY:** the gate blocked the very first real push to main that ran it ([run 35388439275](https://github.com/ZeOoba/ora-pm/actions/runs/35388439275), the #44 merge commit itself) — this repo's `supabase migration list --linked` wraps versions in backticks (`` `0016` ``), which the parser's `/^\d+$/` test rejected, so it parsed zero rows and tripped its own fail-closed path on fully-applied, legitimate output. The gate did what it was designed to do (fail closed, explain why); the parser itself was wrong. Fixed in [ora-pm PR #46](https://github.com/ZeOoba/ora-pm/pull/46) — strips backticks before matching, adds a regression fixture built from verbatim captured production output. 817 tests/80 files green, typecheck+lint clean. **`main`'s deploy path is blocked until #46 merges** — needs priority review |
| [OI-312](#OI-312) | 2026-09-17 | 2026-09-19 | Materialized live during [ora-pm PR #42](https://github.com/ZeOoba/ora-pm/pull/42)'s merge, this session — caught and hand-closed for this one release before it became an outage | **CLOSED 2026-09-19 (verified) — ora-pm PRs #44 and #46 merged; ci.yml L136 runs check-migrations-applied.mjs; push CI at 664f026 and 5e822e3 succeeded.** Prior row text: **HIGH (deploy-ordering race, confirmed unmitigated) — `ora-pm`'s `.github/workflows/ci.yml` has NO step coupling the app deploy to migration-apply order.** `supabase/migrations/0016_charges_void.sql`'s own header says the app must deploy AFTER 0016 is live (its `.is('voided_at', null)` filters 42703 against the old schema otherwise), but `ci.yml`'s `push`-to-`main` job goes straight from `Check commit is still the tip of main` to `Deploy to Cloudflare Pages` with no migration check in between; `db-migrate.yml` is `workflow_dispatch`-only, deliberately decoupled. Confirmed by reading the live `ci.yml` on `main` (2026-09-17): the "Deploy to Cloudflare Pages" step's only gates are the tip-check and the Cloudflare-env check, nothing DB-related. This is exactly what almost happened on PR #42's merge — caught only because this session was watching CI live and asked Gabriel to confirm before the deploy step ran; nothing would have caught it on an unattended merge. Fix direction: add a "Check migrations are applied" step to `ci.yml`, gated the same way as "Check Cloudflare Pages production env" (after the tip-check, before Deploy), running `supabase migration list --linked` (reusing `db-migrate.yml`'s existing `SUPABASE_ACCESS_TOKEN`/`SUPABASE_DB_PASSWORD` secrets) and failing the job if any local migration file has no matching remote entry — forcing a human to run `DB Migrate (manual)` first rather than racing it. **PR OPEN 2026-09-18 (excess-usage sweep): [ora-pm PR #44](https://github.com/ZeOoba/ora-pm/pull/44)** — `scripts/check-migrations-applied.mjs` + gate step, plus the `supabase/setup-cli`/`link` steps the ci job lacked (without them the gate would ENOENT and block every deploy); fails closed on pending/CLI-error/missing-secret/unparseable output; 814 tests/80 files green, typecheck+lint clean. **Both required secrets confirmed present on the repo as of 2026-09-16**, so the gate can actually run. NOT merged — the gate is push-to-main-only, so its first real merge is its live test |
| [OI-184](#OI-184) | 2026-08-17, widened 2026-08-17, root-caused 2026-08-17, **MERGED 2026-08-17/18 ([PR #285](https://github.com/ZeOoba/oxford-command-center/pull/285), `e29dc49`→`fa27d4c`)** | 2026-09-19 | Working the P4 AR review queue; widened + root-caused investigating the NOI cross-check drift; fix went through 5 rounds of the `refute-financial-change` adversarial pass (this session) | **CLOSED 2026-09-19 (verified) — PR #285 present on oxford-command-center origin/main. Not deploy-verified.** Prior row text: **RESOLVED.** Root cause: `resolvePropertyId` (`server/workbook/parse.ts`) tokenized an address and matched each token as a raw SUBSTRING against every property's address, first-match-wins, in array order — `"3034 Westerville Road"` includes `"road"`, a literal substring of `"B-ROAD-way"` in `"1900 N Broadway, Baltimore MD"`, pure spelling coincidence. Both real Westerville leases (Buckeye's Best Transport $13,005/mo, Lamar Advertising billboard $300/mo) were mis-tagged to Baltimore as a result. First fix attempt (a street-suffix denylist, `b8e868c`) closed only that one word; the mandatory refute pass caught real order-dependence and city-token-hijack defects on LIVE data (round 1), then progressively caught defects in each rewrite across 4 more rounds (numeric-veto too strict/too loose, missing score floor, a length-filter bug dropping 1-2 digit house numbers, generic-word/city-word-plus-coincidental-number collisions) — full history in this session's transcript. **Final mechanism** (`e29dc49`): whole-token equality (not substring) + a house-number range gate (candidate disqualified if its own leading number doesn't cover the key's) + a distinctiveness requirement (at least one matched word must be non-generic and non-city, unless that word is also the property's own street name) + fail-closed ties. Round 5 (5/5 lenses, worst severity LOW) confirmed via exhaustive/fuzz verification (167k+30k+20k permutations) that no wrong-match is constructible against the live 14-property/17-key corpus; remaining gap classes (an off-sheet property sharing a common word + coincidental number; comma-less addresses; abbreviation-variant duplicate rows) are all disclosed, fail-safe (miss, not mis-tag) residuals needing a different mechanism (an explicit alias/crosswalk table), not further denylist rounds — logged as follow-up, not filed as a new OI yet. 21 tests. Verified pre-merge against the real live workbook + real warehouse DB: 0 errors portfolio-wide, Westerville correctly downgrades to structural-mismatch/warn with $159,660/yr corroborating rent (exactly Buckeye's + Lamar's combined annual rent). CI (`gate` + `refute-required`) both passed. **One disclosed residual not yet closed:** the tracked snapshot mirror `data/snapshots/portfolio.json` still carried the pre-fix Westerville→Baltimore tag as of merge (the worktree couldn't safely regenerate it without `NOTION_TOKEN`) — self-corrects via the existing `ora-cc-snapshot-refresh` scheduled task (3x/weekday); worth a one-line confirmation next time that task's output is checked |
| [OI-186](#OI-186) | 2026-08-17, **RETRACTED as duplicate 2026-08-17** | 2026-09-19 | Investigating the pre-push NOI large-drift gate (3 properties failing, this session) — filed without first grepping the tracker for prior art | **CLOSED 2026-09-19 (verified) — Retracted as a duplicate of OI-137 (row already said so).** Prior row text: ~~MEDIUM — portfolio-wide data staleness~~. **Duplicate of [OI-137](#OI-137)**, independently re-derived 5 days later, same 3 properties, same root cause — should have been caught by a tracker search before filing. **Also overstated a claim never checked against data already in hand:** "the other 9 are equally stale and will start tripping it too" — false as stated. The full cross-check's own per-property output (already captured, never re-read before writing that line) shows only 3 of the other 11 properties show ANY drift at all (29000 Info Lane 5.09%, 3540 E 5th 8.37%, Sepich Portfolio -6.76%, all WARN-tier, none within striking distance of the 20% gate), 5 are in-tolerance (≤3.8%), and 2 are structurally not comparable (`lease-run-skipped`). Staleness is real and portfolio-wide (confirmed: every property's full-year `import_batches` row shares the identical `2026-06-13T19:52:51.1xx` timestamp, one single backfill never refreshed since); its CONSEQUENCE is not — it only shows up as large drift where real 2025→2026 tenancy change also occurred, which is a small minority of the portfolio. **The one genuinely new fact this item added to OI-137** (kept, not duplicated): no fresher P&L source files exist anywhere in `Business/Property Financials/` to backfill from — verified directly, only the same June-12-dated exports already ingested — so a `warehouse:backfill` re-run right now would be a no-op. Folded into OI-137's entry rather than carried as a separate row |
| [OI-271](#OI-271) | 2026-09-11 | 2026-09-19 | `dirty-tree-triage` follow-up — independent review (claude-opus-5) of `CLAUDE.md` commit `b777625` | **CLOSED 2026-09-19 (verified) — Tracker recorded CLOSED 2026-09-11 (commit 607a2d0); not re-verified.** Prior row text: **LOW (doc contradiction, no automated behavior affected).** `rules.md` §2 line 32 ("On non-zero COM exit: retry once … do NOT halt") now directly contradicts its own exit-code table two lines below (exit 1/3 = do NOT retry) — harmless while `CLAUDE.md` inlined the same split for a reader to reconcile against, live now that `CLAUDE.md` points straight at §2 instead. Documentation-only; `send-via-outlook.ps1`'s actual exit-code handling is unaffected. See detail section below |
### OI-317
**Status:** CLOSED 2026-09-18 (same day as opened)
**See:** the `## Closed` table above — the row's own one-line cell is the full write-up; not restated here per this file's own text-lives-in-one-place rule.

### OI-293
**Status:** CLOSED 2026-09-13
**See:** the `## Closed` table above — the row's own one-line cell is the full write-up; not restated here per this file's own text-lives-in-one-place rule. This stub exists only to give `open-items-tracker-history.md#OI-293` a working anchor.

### OI-213
**Status:** CLOSED
**Opened:** 2026-09-02
**Closed:** 2026-09-18
**Evidence:** Acceptance met — the HubSpot deal reflects the exercised renewal term. HubSpot deal `58514721860` read-back 2026-09-18 (this session) returns `dealstage closedwon` / `closedate 2031-09-30T00:00:00Z`, `hs_lastmodifieddate` **2026-09-18T16:41:37Z** — i.e. applied earlier the same day by a different session, NOT by this one; this session only verified it. That matches the recommended correction exactly (`dealstage` → `closedwon`, `closedate` → `2031-09-30`). Independently corroborated against the workbook-derived snapshot re-read the same session: `propertyKey "7658 Fishel"`, `leaseEnd "2031-09-30"`, `status "Active"`. The secondary observation stands and was honored — the correction is keyed to the canonical ORA-T-3 record, not the retired duplicate Notion row.
**Source:** `ora-tenant-hubspot-reconciliation` monthly run, 2026-09-02 (Step 3a — ELEVATED)
**Acceptance:** The HubSpot deal for Heritage Pool Supply reflects the exercised renewal term, or Gabriel rules that it should not.

**Description:** **HubSpot deal `58514721860` ("Heritage Pool Supply — Lease Renewal 2026-09-30") sits in `appointmentscheduled` with `closedate 2026-09-30` — an expiration both other systems of record document as superseded by an exercised renewal option.**

Quoted Notion evidence (Tenant DB row "Heritage Pool Supply", `Row Retired: true`, Notes field verbatim):

> "Duplicate of SRS Distribution / Heritage Pool Supply (ORA-T-3) - retired 2026-07-29 per lease-abstraction-pipeline targeted-fix reconciliation (Single Tenant Property Lease Terms batch). ORA-T-3 is canonical: more complete record (Lease Extension/Amendment Log, renewal terms, current expiration 2031-09-30 reflecting the exercised 1st Renewal Term). This row's Lease Expiration (2026-09-30) was stale - did not reflect the 2026-04-26 renewal exercise."

Independent corroboration from the workbook-derived snapshot (`oxford-command-center/data/snapshots/portfolio.json`, `asOf 2026-08-25`): `propertyKey "7658 Fishel"`, `leaseEnd "2031-09-30"`, `status "Active"`.

Both non-HubSpot systems agree on 2031-09-30 and Notion names the instrument (1st Renewal Term, exercised 2026-04-26) — this clears the evidence bar this task holds to (quote the note, never infer from pattern).

**Recommended correction (NOT applied — this task is detection-only and never writes to HubSpot):** `dealstage` → `closedwon`, `closedate` → `2031-09-30`.

**Secondary observation:** the HubSpot deal matches a Notion row that is itself retired as a duplicate; the canonical row is ORA-T-3 (SRS Distribution / Heritage Pool Supply). Any correction should be keyed to ORA-T-3, not the retired row.

### OI-214
**Status:** CLOSED
**Opened:** 2026-09-02
**Closed:** 2026-09-18
**Evidence:** Acceptance met — `closedate` now matches the rent-roll-confirmed 2027-05-31. **Applied by this session** via `manage_crm_objects` on deal `58522276169` at 2026-09-18T19:19:31Z; read-back confirms `closedate 2027-05-31T00:00:00Z` with `dealstage` left unchanged at `closedwon`, per this item's own "do not reopen the stage" instruction. Pre-write verification against the workbook-derived snapshot: `propertyKey "2207 Northwood"`, `unit "B2+B3"`, `leaseEnd "2027-05-31"`, `status "Active"` — so Notion, the workbook and now HubSpot all agree, and the 2026-07-21 correction that had reached only two of three systems has finally propagated to the third.
**Source:** `ora-tenant-hubspot-reconciliation` monthly run, 2026-09-02 (Step 3d, escalated to ELEVATED per the skill's "fix silently failed to propagate" clause)
**Acceptance:** The Maryland Hospital Association deal's `closedate` matches the rent-roll-confirmed 2027-05-31, or Gabriel rules the 2027-06-30 figure is right and Notion/the workbook are wrong.

**Description:** **HubSpot deal `58522276169` ("Maryland Hospital Assoc — Lease Renewal 2026-05-31", `closedwon`) carries `closedate 2027-06-30` — the exact value Notion's own correction note records as disproven and replaced six weeks ago.**

Quoted Notion evidence (Tenant DB row "Maryland Hospital Association", Notes field verbatim):

> "Lease Expiration and Escalation Date corrected 2026-07-21 per Rent Roll 7.20.2026.xlsx (was 2027-06-30/2026-05-01, rent roll shows 2027-05-31/2027-06-01)."

Notion Lease Expiration now reads `2027-05-31`. `portfolio.json` independently agrees: `propertyKey "2207 Northwood"`, `unit "B2+B3"`, `leaseEnd "2027-05-31"`, `status "Active"`.

**Why this is escalated rather than an ordinary DATE-MISMATCH:** the note does not merely disagree with HubSpot — it names `2027-06-30` as the specific wrong value it replaced. The 2026-07-21 correction reached Notion and the workbook and did not reach HubSpot. That is the "a fix silently failed to propagate" case Step 3d escalates by design, and it is the same failure shape as the 2026-07-25 Stone Crest / Chesapeake precedent that created Step 3d in the first place.

**Compounding factor:** the deal was moved to `closedwon` on 2026-07-21 — the same day as the Notion correction — by the [OI-021](#OI-021) batch pass. The wrong date is therefore frozen inside a closed record rather than sitting on an open one, so nothing in the normal renewal workflow will surface it again.

**Recommended correction (NOT applied):** `closedate` → `2027-05-31`. Do not reopen the stage; the renewal itself is not in question.

### OI-215
**Status:** CLOSED
**Opened:** 2026-09-02
**Closed:** 2026-09-18
**Evidence:** Acceptance met — the Notion Tenant DB row is now consistent with the workbook. Canonical row `32c6ecd8-9e59-8108-a136-f8050119cf21` (`Tenant Name` "J&R ENTERPRISES", `Suite / Unit` "Unit 105B", `Row Retired` NO, `Lease Status` Active, $1,105/mo, Jeff Menke) read-back 2026-09-18 (this session) returns `Lease Expiration 2026-12-31`, and its Notes field carries an appended line: "2026-09-18: synced to Master Workbook rent roll (as of 2026-09-18) — Lease Expiration." Applied earlier the same day by a different session, NOT by this one. HubSpot needed no change and received none — deal `58524287555` still reads `closedate 2026-12-31` / `appointmentscheduled`, `hs_lastmodifieddate` 2026-07-27, untouched. Workbook agrees (`9620 State 350` / `105B` / Jeff Menke / `leaseEnd 2026-12-31` / Active). **Incidental, verified not a defect:** a second row `32b6ecd8-9e59-819a-9b10-c593fdab7a33` ("⛔ ARCHIVED 2026-07-12 — J&R ENTERPRISES", Suite B1, `Lease Expiration 2026-04-30`) still exists and is correctly `Row Retired = YES`. The reusable lesson above is unaffected by this closure and still applies to any field back-filled from a snapshot.
**Source:** `ora-tenant-hubspot-reconciliation` monthly run, 2026-09-02 (Step 3d escalation, direction reversed)
**Acceptance:** The Notion Tenant DB row for J&R ENTERPRISES carries a lease expiration consistent with the workbook, or the discrepancy is adjudicated against a primary document.

**Description:** **The Notion Tenant DB row for J&R ENTERPRISES still carries `Lease Expiration 2026-07-31` — a date 33 days in the past — while HubSpot and the workbook both say `2026-12-31`.**

This is the third tenant named in this task's own 2026-07-25 Step-3d precedent (alongside STONE CREST COUNTERS and Chesapeake Brands). At that time the defect ran the other way: Notion had been corrected and HubSpot still carried the disproven date. It has since inverted.

Current three-way state:
- HubSpot deal `58524287555` — `closedate 2026-12-31`, `appointmentscheduled`; the dealname itself reads "(orig. exp. 2026-07-31 → term thru 2026-12-31)"
- `portfolio.json` — `propertyKey "9620 State 350"`, `unit "105B"`, `leaseEnd "2026-12-31"`, `status "Active"`
- Notion Tenant DB — `Lease Expiration 2026-07-31`, `Lease Status "Active"`

Quoted Notion evidence (Notes field verbatim):

> "Lease Expiration was missing entirely (null). Filled 2026-07-16 per Master Workbook / oxford-command-center portfolio.json snapshot (same unit 105B, same tenant contact Jeff Menke, same $1,105/mo rent — confirmed same lease); portfolio.json also flags this lease status 'Expiring Soon'."

The note documents Notion being filled *from* `portfolio.json` on 2026-07-16, when that snapshot said 2026-07-31. The snapshot has since moved to 2026-12-31 and Notion did not follow. A row that was correct at write time silently became a stale expired date.

**Recommended correction (NOT applied — this task never writes to Notion either):** set Notion `Lease Expiration` → `2026-12-31`. **No HubSpot change** — HubSpot is the correct system here.

**Reusable lesson worth more than the row fix:** a Notion field back-filled *from* a snapshot inherits that snapshot's point-in-time value with no link back to it, so it cannot self-correct when the source moves. The 2026-07-16 remediation created three such copies; two (STONE CREST, Chesapeake) have since converged, this one has not.

### OI-218
**Status:** CLOSED
**Opened:** 2026-09-02
**Closed:** 2026-09-18
**Evidence:** Acceptance met — outcome recorded and the deal advanced. (1) Live Master Workbook `Master Tenant Rent Roll` (as of 2026-09-18, read-only COM attach): CJ's Tint Shop is no longer on the roster; 29000 Information Lane unit 105 is leased to CAPITAL PROPERTY RECOVERY, LLC, Lease Start 2026-09-10, Lease End 2029-09-30, $1,700/mo (prior tenant paid $1,850). (2) Gabriel confirmed the vacate in-session 2026-09-18. (3) HubSpot deal `58521500852` moved `appointmentscheduled` → `closedlost` via `manage_crm_objects` with a NOTE citing the workbook row; verified by a follow-up `search_crm_objects` (deal absent from the open set). (4) Notion Tenant DB row `32c6ecd8…9460` set `Row Retired = YES` / `Lease Status = Vacant`, read-back verified; new Capital Property Recovery row created. Outcome = **vacated at expiration, unit backfilled in 10 days**. Detail: [[reference_hubspot_lease_renewal_pipeline_stalled_2026-08-23]], `event_log.md` 2026-09-18.
**Source:** `ora-tenant-hubspot-reconciliation` monthly run, 2026-09-02 (Step 3b — WATCH, stale open deal with no corroborating signal)
**Acceptance:** Gabriel records what actually happened at CJ's Tint Shop (renewed / vacated / holdover) and the deal is advanced accordingly.

**Description:** **CJ's Tint Shop's lease expired 2026-08-31 — two days before this run — and no system records a renewal, a vacate, or a holdover.**

Unusually, all three sources agree on the date, and all three are silent about the outcome:
- HubSpot deal `58521500852` — `closedate 2026-08-31`, still `appointmentscheduled`, `hs_lastmodifieddate 2026-03-27` (159 days idle; never touched since the original bulk import)
- Notion Tenant DB — `Lease Expiration 2026-08-31`, `Lease Status "Active"`, `Property Address "29000 Information Ln — Easton MD"`, `Suite / Unit "Unit 105"`, **Notes field empty**
- `portfolio.json` — `propertyKey "29000 Information Lane"`, `unit "105"`, `leaseEnd "2026-08-31"`, `status "Expiring Soon"`

This is the cleanest Step 3b case in the sweep: the date is not in dispute, the term has run out, and there is genuinely no evidence either way. **No outcome is inferred** — per this task's standing rule, silence in Notion is not evidence of a vacate, a renewal, or a holdover.

It is also the only deal in the pipeline whose `closedate` has elapsed *and* whose lease genuinely ended on that date; the two other elapsed-`closedate` deals (Medspeed, Robert & Kesha Best, both under [OI-216](#OI-216)) have later true expirations in the other two systems.

### OI-219
**Status:** CLOSED
**Opened:** 2026-09-02
**Closed:** 2026-09-18
**Evidence:** Acceptance branch 1 met — a rule now exists for when a Lease Renewal deal leaves `appointmentscheduled`. Gabriel ratified it in-session 2026-09-18: closed-won = executed doc or workbook Lease End beyond the deal's target date; closed-lost = workbook `Notice to Vacate = Yes` or unit re-let; otherwise the deal stays parked, and anything inside 120 days is listed as UPCOMING. The rule is carried by the new weekly CC/MCP task `ora-renewal-hubspot-reconcile` (cron `20 10 * * 1`, registered via `create_scheduled_task` 2026-09-18); its first run (`run_scheduled_task`, session `local_8d6c9a45…`) completed `done (success)` — workbook read via the locked-file COM fallback, 21 open deals all tied to the workbook, 0 writes. Of the six deals tabled below, The Companies, LLC is now `closedlost` (notice given); the other five are genuinely not-yet-due and correctly parked. **Follow-up, not filed as a new item:** `ora-tenant-hubspot-reconciliation` Step 3e will re-raise this same IDLE finding on its next monthly run unless Step 3e is amended to defer to the weekly actuator — that spec was NOT edited here (task is paused until 2026-09-21; changing a detection task's scope is Gabriel's call).
**Source:** `ora-tenant-hubspot-reconciliation` monthly run, 2026-09-02 (Step 3e — IDLE, the standing monthly sweep)
**Acceptance:** A rule exists for when a not-yet-due Lease Renewal deal leaves `appointmentscheduled` — or Gabriel confirms parking them there indefinitely is intended and this check is retired.

**Description:** **6 deals meet the Gabriel-set IDLE threshold (30+ days since last modification AND lease expiration 183+ days out).** This is the recurring sweep for the ~37-deal population [OI-021](#OI-021)'s 2026-07-25 batch pass confirmed was legitimately not-yet-due — not a re-litigation of the 8 real items that pass already resolved.

| Deal | Idle (days) | Lease expiration | Days out |
|---|---:|---|---:|
| I.M.H LLC | 126 | 2033-07-31 | 2,524 |
| The Companies, LLC | 159 | 2028-09-30 | 759 |
| STONE CREST COUNTERS LLC | 37 | 2028-07-31 | 698 |
| Terrone T. White | 48 | 2027-03-31 | 210 |
| I Dig Ditches | 47 | 2027-03-31 | 210 |
| Chesapeake Brands, LLC | 37 | 2027-03-31 | 210 |

Two further deals meet the same threshold but are filed under [OI-216](#OI-216) instead, because they carry a date defect on top of being idle: Medspeed (107 days idle, 2029-08-31) and Robert & Kesha Best (159 days idle, 2027-08-31).

**Flag-only, never auto-advanced** — matches this task's detection-only posture and Hard Invariant 1. The stage change (advance, close-lost, or re-scope) is Gabriel's call.

**The denominator is the more useful finding.** The 183-day leg is doing all the filtering: **every one of the 37 open deals is 37+ days idle**, because the newest `hs_lastmodifieddate` anywhere in the open pipeline is 2026-07-27. The entire Lease Renewal pipeline has had no activity in over five weeks. That is consistent with [reference_hubspot_lease_renewal_pipeline_stalled_2026-08-23.md](reference_hubspot_lease_renewal_pipeline_stalled_2026-08-23.md) and this run is a second, independent observation of it.

### OI-222
**Status:** CLOSED
**Opened:** 2026-09-02 · **Closed:** 2026-09-13 · **Source:** `ora-appsec-sweep` 2026-09-02 (ora-pm @ `ca62ecbed3aff0a1d21585dcf40f62d823810296`, security-auditor dispatch)
**Severity:** MEDIUM (money-state correctness — webhook resilience)
**Evidence:** [ora-pm PR #31](https://github.com/ZeOoba/ora-pm/pull/31) merged `253f2925` 2026-09-13. TDD (RED confirmed before fix); on `23505` the handler now `SELECT`s the existing row's status and re-drives `handleStripeEvent` for any non-`processed` row instead of unconditionally skipping. Full suite 479/479 passing, typecheck/build clean, re-verified after a rebase onto current `origin/main`. Independent adversarial REFUTE pass (Fable-tier security-auditor, cold read, no knowledge of the implementation) checked specifically for double-processing risk from concurrent retries — confirmed benign, every write in `server/lib/stripe-events.ts` is an idempotent per-payment-intent update — and found no scope creep or regression. Residual, not introduced by this fix: no `'pending'` status exists on `stripe_webhook_events` (only `processed`/`failed`, defaulting to `processed`), so a process crash mid-handler before the `failed` update runs can still strand a row at `processed`; closing that needs a schema migration and was left as a follow-up, not silently expanded into this fix's scope.

**Description:** `server/routes/webhook.ts:30-46` inserts the Stripe event id into `stripe_webhook_events` *before* calling `handleStripeEvent`. If the handler throws (e.g. a transient Supabase error), the row is marked `failed` and the endpoint returns 500. Stripe retries the same event; the retry's insert hits Postgres `23505` (unique violation) and the handler short-circuits to `{received:true, skipped:true}` with 200 — the retry is discarded, and nothing ever re-drives a `failed` row.

**Impact:** A lost `payment_intent.succeeded` leaves a real ACH payment stuck at `processing` (balance overstated, risk of a duplicate manual payment). A lost `charge.failed`/`charge.dispute.created` arriving after a `succeeded` event leaves `ar_ledger` counting a returned/disputed ACH as paid (balance understated). Same failure class as the two AR-ledger bugs already shipped in this repo (cartesian fan-out, divide-by-100): correctness of money state depends on an implicit guarantee — here, "every webhook eventually processes" — that isn't actually enforced.

**Candidate fix (NOT applied):** on `23505`, read the existing row's `status`; if `failed`, re-run `handleStripeEvent` and update the row (idempotent updates make this safe to retry). Add a periodic re-drive of `status='failed'` rows (existing cron infrastructure), and a test asserting a Stripe retry after a failed handler actually re-processes rather than silently skipping.

**Auto-check:** none.

### OI-181
**Status:** CLOSED 2026-08-16 (LANDED)
**Opened:** 2026-08-16
**Source:** Hit live while recording the OI-176 review artifact (session 76023481), then reproduced deterministically.
**Acceptance:** Running any `eos-review-gate.py --record` copy with a flag that copy does not support **fails loudly** (non-zero exit, explicit message) instead of recording. Proven by running the repro against a deliberately stale copy and observing a non-zero exit rather than `notes: ""`.

**Description:** **A stale copy of the review gate silently discards `--notes-file`, producing an approved security-review artifact with an EMPTY audit trail, exit 0, no warning.**

**Reproduced** (no artifacts written; exercises each copy's own notes-resolution path). Same argv — `--record --verdict approved --model claude-fable-5 --notes-file <tmp>` — against two copies:
- LIVE `hooks/eos-review-gate.py`: `_resolve_notes` present, **notes preserved, 50 chars**.
- STALE `.claude/worktrees/oi173-spec-liveness-probe/hooks/eos-review-gate.py`: no `_resolve_notes`, **notes `''` — silently empty, exit 0**.

**Three compounding causes, none sufficient alone:**
1. **`_arg()` cannot detect an unsupported flag.** It is a positional `argv.index()` scan (`hooks/eos-review-gate.py:768`), not argparse, so an unknown flag is ignored rather than rejected. Telling detail from the repro: the stale copy's own `_arg(argv, "--notes-file")` **does** return the path — the value is right there in argv; the stale code simply never asks for it. Detection is therefore cheap.
2. **`config-write-guard` actively routes callers to the stale copy.** Its block message prescribes *"re-run the command against a WORKTREE checkout's copy of the tool (worktree paths are exempt, and the tool still writes to the live tree)."* So the recommended workaround is precisely the path that can be stale — and invoking the LIVE binary by absolute path is blocked, because a governance path plus a write-shaped command trips the matcher.
3. **No version stamp.** `eos-review-gate.py` has no `__version__`/`VERSION` constant, so neither the tool nor the caller can detect skew, and the artifact does not record which tool version wrote it.

**Why it is not cosmetic:** `notes` is not part of the artifact key, so the gate still **PASSES** and the commit lands. The failure is invisible at exactly the moment the audit trail is being created, on the tool whose entire job is to prove a blast-radius change was reviewed.

**Live exposure at filing:** `--notes-file` is the ONLY flag divergence between live and the stale copy (all 15 others match). Of 3 live worktrees, **1 is stale** — `oi173-spec-liveness-probe` (0 `notes-file` refs); `build-lane-capability-check` and `.claude-worktrees/retro-fixes` both have it. Flag landed in `fe14d91` (2026-08-16, PR #136); any worktree branched before that commit is exposed. Not fixed in that worktree — it is another session's workspace.

**Suggested fix (not applied — `hooks/**`, needs the review pass):** in the `--record` path, reject any `--`-prefixed token not in a known-flag set, exiting non-zero. ~10 lines, and it converts silent skew into a loud failure for *every* future flag, not just this one. Optionally add a `__version__` stamped into the artifact so skew is visible after the fact. Ownership note: `eos-review-gate.py` was last touched by session `6797e01b` (retro tooling fixes).

**Closure evidence (2026-08-16):** **LANDED** as `4cbebe8` (from worktree commit `43be6ca`) on Gabriel's in-turn "land it the same way OI-176 went." `reject_unknown_flags()` on both `--key`/`--record`, correctly skipping value-taking flags' values; `KNOWN_CLI_FLAGS` self-checked against real `_arg()` call sites so the fix cannot itself go stale; `__version__` stamped into every artifact. Claim re-checked before landing (`hooks-override-auth` free; `fleet-status-reconcile`'s claimed paths were disjoint — `maintenance/fleet-status.py`/`test-fleet-status.py`, not this file); two-pass mtime identical; worktree branch point confirmed an ancestor of live HEAD. Live post-landing verification with the override token removed: unknown flag rejected on the LIVE binary (rc=1, names the flag + accepted set + staleness diagnosis); `--notes-file` itself still accepted (rc=0); the verification Bash calls themselves ran through the live dispatcher's `--chain bash` in-process path with no `unrecognised` output — proving the scoping fix live, not just in a harness; a real governance write was still BLOCKED through the same chain. Independently reviewed (claude-fable-5) before landing: scoping hazard proven both by tracing and by running the dispatcher both directions, flag-set completeness re-derived independently and matched exactly, adversarial parsing cases all correct, no artifact written on rejection. No lingering damage from the triggering incident: the empty artifact was overwritten at the same key, both this session's artifacts carry notes.

### OI-163
**Status:** CLOSED
**Opened:** 2026-08-16
**Closed:** 2026-08-16
**Source:** Cross-repo architecture-diagram review (Gabriel-directed, this session) — `AAOS/README.md` §1 and its cited `docs/DELIVERABLES-MANIFEST.md`; corroborates the existing memory pointer [[project_aaos_agent_coordination_layer]] ("real infra; Cowork round-trip unreachable from Code")
**Description:** **MEDIUM** AAOS (`C:\Users\Owner\AAOS`) is a filesystem-based Code↔Cowork task-queue/handoff protocol over an OneDrive-synced "seam" — no daemon, no network listener. It self-grades as v1.0 feature-complete: 216 unit/integration tests (all green), 6 documented adversarial gate reviews, 5 ADRs. But the README states directly that the one capability the whole system exists to prove — a live, same-session round-trip confirming a real Cowork session can read/write the seam — "has explicitly still [been] open": `t-cowork-seam-confirm.json` sits queued and unconsumed in the live seam as of this review. `docs/DELIVERABLES-MANIFEST.md` additionally records that none of the six phase gates received explicit Gabriel sign-off before the next phase began — each was presented and the project simply proceeded. In production, only `tools/expire-leases.py` actually runs unattended (`ora-aaos-expire-leases`, CC/MCP fleet, 3x/day since 2026-07-10); every other component (task lifecycle CLIs, handoffs, the Notion projection publisher) is unexercised outside its own test suite.
**Fix direction:** either force one genuine live round-trip (a real task created by Code, leased/completed by an actual Cowork session) to validate the core claim, or stop counting AAOS as shipped/production infrastructure in future audits until it is — right now it is unproven maintenance surface with a real (if patched) history of concurrency bugs (see the README's own event-log clobbering note).
**Evidence:** The round-trip had ALREADY genuinely happened — over a month before this item was filed. `handoffs/h-cowork-seam-ack-e7c490.json` (posted 2026-07-10T13:46 -04:00 by a real Cowork session, per its own context_summary: ran the COWORK-BOOTSTRAP.md probes for real, landed in SAFE-BY-HAND mode after Probe X's `validate.py` subprocess exited 1 on a jsonschema import error, then wrote the handoff + a paired spool event per §7) satisfies all three acceptance criteria — verified directly this session, not taken on the handoff's own word: `grep`'d `aaos-events.ndjson` and confirmed the paired `HandoffPosted` event was drained (`e-2026-07-10T17:46:23.580832Z-826571`), and ran `python tools/validate.py` against the handoff file → `VALID`. The actual gap all along was that Cowork's handoff explicitly said "a Code session should drain the spool... and may then lease/complete/archive the task" — and no Code session ever did. Closed properly this session: `tools/lease-task.py` + `tools/complete-task.py --archive` against `t-cowork-seam-confirm`, evidence citing the handoff/event/validation above. Task now `state:"archived"`. A companion handoff from the same Cowork session (`h-cowork-jsonschema-pin-request-9ac653.json`) also flagged that Cowork's `jsonschema` package fix was session-local/non-durable and spawned a follow-up task, `t-cowork-jsonschema-pin-952743` — **that one is still open**, unrelated to this closure, worth a separate look if Cowork FULL-EXEC parity is ever wanted.

### OI-166
**Status:** FIXED 2026-08-16
**Opened:** 2026-08-16
**Source:** Live concurrency near-miss during the `ora-passed-deal-tracker` double-fire-guard session (Gabriel-directed) — [[event_log]] 2026-08-16
**Description:** `claim_work.py claim` refuses (exit 3) when a live claim exists **under the same slug**, but never asks whether a live claim under a *different* slug already covers the same `--paths`. Observed live: this session held `open-items-tracker` while session `30b5a31f` held `repo-housekeeping`, both declaring `memory/open-items-tracker.md` and `memory/MEMORY.md` — the exact two files each was trying to settle. Neither refusal could fire, because the gate is keyed on slug, not path. Both sessions independently root-caused the same blocked pull; only luck (the other claim being released first) prevented duplicate commits.
The overlap primitive was **not** missing: `claims_touching()` has existed and is wired into `shared-checkout-guard.py:362` on the Edit/Write hot path, and into `dirty-file-owner-report.py`. It was simply never consulted by the `claim` command itself, so overlap surfaced only *after* someone edited a file — too late to prevent duplicated investigation.
**Fix applied:** wired `claims_touching()` into the claim path so a cross-slug `--paths` overlap is surfaced at claim time, naming the other slug and session. Deliberately a **loud warning, not a refusal**: the module's docstring endorses distinct slugs as a feature ("a distinct slug keeps BOTH claims independently visible"), and its ratified design is fail-open, not a hard lock — a refusal here would wedge legitimate broad-`--paths` claims. Making the overlap *visible at claim time* is what "independently visible" was always meant to deliver.

### OI-170
**Status:** FIXED 2026-08-16
**Opened:** 2026-08-16
**Source:** Root cause of the entire `ora-passed-deal-tracker` double-fire-guard session (Gabriel-directed) — [[event_log]] 2026-08-16
**Description:** The scheduler resolves a registry entry's `filePath` against the **live working tree**, not git. A SKILL.md can therefore be authored, reviewed, merged via PR, and present on `origin` while the checkout the scheduler actually reads still holds the old content — merged and inert, with nothing detecting it. Confirmed live: `ora-passed-deal-tracker`'s two-layer double-fire guard merged as `b734674` (PR #116, commit `c16667c`) but the primary checkout sat at `588ec1b`, so `grep -cE "block-sentinel|outlook-sent-probe"` against the live file returned **0** while every git-side check said the guard had shipped. It would have stayed inert through the 2026-09-15 06:30 ET dual-fleet fire had a human not noticed.
`task-folder-registration-probe.py` was the closest existing guard and could not catch it: its three checks (UNREGISTERED, ORPHANED_REGISTRATION, ARCHIVED_BUT_REGISTERED) all reason about whether the filePath **exists**, never about whether its **content** matches what git says it should be. A merged-but-not-checked-out SKILL.md exists at the right path with the wrong bytes, which is clean by all three.
**Fix applied:** extended `task-folder-registration-probe.py` with a fourth check, STALE_VS_GIT — for every enabled registry entry whose filePath is inside a git repo, compare the on-disk SKILL.md against the committed blob at HEAD and flag a mismatch. Catches this class directly: merged-but-not-pulled, locally-edited-but-uncommitted, and reverted-in-tree.

### OI-165
**Status:** CLOSED
**Opened:** 2026-08-16
**Closed:** 2026-08-16
**Source:** Cross-repo architecture-diagram review (Gabriel-directed, this session) — `website-canonical/README.md` "Build & deploy flow" diagram and accompanying prose
**Description:** **LOW** `scripts/build-kb.mjs` builds the `/api/chat` assistant's `netlify/edge-functions/knowledge-base.json` from `scripts/meta.md` plus 8 public pages, but is deliberately excluded from `netlify.toml`'s build command (`node scripts/build-dist.mjs` only) — the README states this directly: "editing a page does not change what the assistant knows until it is re-run" by hand. There is no CI check, pre-commit hook, or any other mechanism flagging that the committed `knowledge-base.json` has gone stale relative to `scripts/meta.md` or the site pages it's built from — so the chat assistant can silently serve outdated firm facts (leadership, markets, deal parameters, contact info) for an unbounded period after a real content edit, with zero signal that it happened.
**Fix direction:** fold `build-kb.mjs` into the Netlify build command (it's a local, deterministic, no-external-call step — cheap to run on every build) or, if the hand-run cadence is intentional, add a pre-commit/CI check that compares `knowledge-base.json`'s content hash against a hash of `meta.md` + the pages it's built from and fails/warns on mismatch.
**Evidence:** Gabriel confirmed in-turn 2026-08-16 ("Yes, do the website KB build fix"), authorizing the write past Hard Invariant 2's site-tree gate. `netlify.toml`'s `[build] command` changed from `node scripts/build-dist.mjs` to `node scripts/build-kb.mjs && node scripts/build-dist.mjs`. Verified locally by running the new chained command end to end: `build-kb.mjs` regenerated `netlify/edge-functions/knowledge-base.json` (pages=9, chars=37327, only the `generatedAt` timestamp changed vs. the prior committed copy — confirming site content hadn't actually drifted since 08-13, this just closes the future gap) and `build-dist.mjs` completed with its own required-file/leak/HTML-count checks passing (`OK — 40 root entries -> dist/ (18 pages)`, no failures). README's diagram + prose updated to describe the new automated behavior. No deploy performed — that stays a separate confirmation per Hard Invariant 2.

### OI-050
**Status:** CLOSED
**Opened:** 2026-07-31
**Closed:** 2026-09-13
**Source:** ora-appsec-sweep 2026-07-31 (oxford-command-center @ `3692385`, security-auditor dispatch)
**Severity:** MEDIUM (rated below HIGH only because it requires the server running AND the victim
visiting attacker-controlled content)
**Description:** `server/index.ts:531`; `server/cors-policy.ts`. Hono's `cors()` never gates a
same-origin request, and after a DNS rebind the attacker's origin *is* the request origin, so the
localhost-only CORS policy is bypassed entirely rather than violated.
**Impact:** `/api/snapshot` is the single highest-value data set in the fleet. Both read and write are
reachable.
**Evidence:** [oxford-command-center PR #327](https://github.com/ZeOoba/oxford-command-center/pull/327)
merged `304bcbb0` 2026-09-13. New `server/host-guard.ts` mounted on `/api/*` and `/sse` before `cors()`/
`accessAuthz`: exact-match Host allowlist (defeats DNS rebinding), fail-closed Origin check on any
present Origin, and a required `X-ORA-Client` header on every non-GET/HEAD/OPTIONS request (forces a
CORS preflight on any cross-origin write, which the existing origin allowlist then blocks). All 20
mutating `fetch(` sites in `src/**`/`scripts/ar-import.ts` updated to send the header. TDD (RED
confirmed first), full suite 281 files/4023 tests passing, typecheck/lint/build clean, re-verified
after a rebase across 25 intervening upstream commits (zero file collisions; mutating-fetch-site count
re-swept at 20/20 against the rebased tree). Independent adversarial REFUTE pass (Fable-tier
security-auditor, cold read) ran a raw-socket bypass matrix directly against the real
`@hono/node-server` adapter — DNS rebinding, duplicate/case-varied Host headers, `Origin: null`, empty
`X-ORA-Client`, IPv6 loopback, path-encoding tricks — every attempt held; confirmed bind is `127.0.0.1`
only. The REFUTE pass caught the one caller a repo-scoped sweep could not see — the `ora-om-intake-ocr`
scheduled task (LAMS/Cowork fleet, outside this repo) POSTs to `/api/actions/om-extract` with no
`X-ORA-Client` header — fixed in that task's SKILL.md (v1.6) in the same session before merging, so
nothing broke on its next fire.
**Auto-check:** none.

### OI-071
**Status:** CLOSED
**Opened:** 2026-08-03
**Closed:** 2026-09-13
**Source:** Production verification of [OI-067](#OI-067), 2026-08-03
**Severity:** MEDIUM (broken feature, confirmed — not a security exposure; the RLS policy is correct and holding)
**Description:** `src/portal/pages/PortalInsurance.tsx` uploads tenant COI files to
`${session.user.id}/${file.name}` in the `insurance-certs` bucket, but the live `tenant_upload_insurance`
RLS policy (confirmed applied and correct, see OI-067) requires the folder to equal `tenants.id`
(resolved via `tenants.auth_user_id = auth.uid()`). Every real tenant COI upload through this page
fails today — confirmed against production, not just the repo.
**Corroborated independently, 2026-08-04:** a REFUTE pass on the OI-048 docs/tripwire fix, reading
`server/db/client.ts` cold with no knowledge of this item, re-derived the exact same
`session.user.id`-vs-`tenants.id` mismatch from first principles. Two independent passes reaching the
identical root cause is corroboration, not new information — no change to this item's status or scope.
**Evidence:** [ora-pm PR #31](https://github.com/ZeOoba/ora-pm/pull/31) merged `253f2925` 2026-09-13.
`PortalInsurance.tsx` now resolves `tenants.id` via the existing `GET /api/portal/me` (same pattern as
`PortalPayNow.tsx`/`PortalDashboard.tsx`) instead of `session.user.id`, with a loading/error guard so
the upload can't fire before the tenant id is available. New component test added (no jsdom/
testing-library in this repo, so it combines a source-text assertion with a `react-dom/server`-rendered
behavioral check of the loading guard). Full suite 479/479 passing. Independent adversarial REFUTE pass
confirmed: no stuck-loading state on a slow/failed `/me` (TanStack Query retries on focus/remount), no
path for a stale/undefined tenant id to reach `.upload()`, and defense-in-depth still holds even if it
did (server resolves the tenant from the JWT independently; RLS `WITH CHECK` compares against the
caller's own `tenants.id`).
**Auto-check:** none.

### OI-229
**Status:** CLOSED 2026-09-12 — all three close conditions met (see Closure below); moved to history
**Opened:** 2026-09-03
**Source:** `register-scheduled-task` v2.19 step 3b (ora-skills `be1deda`) applied to the live fleet, 2026-09-03; Automation Audit Rev 21 R21-2/R21-4 (every trigger of a money-moving task co-located on the host whose outage was the outage)
**Acceptance:** `ora-pm-daily-crons` carries an `offhost-backup:` frontmatter line naming a LIVE trigger that does not run on this laptop (repo + workflow + cron + live-since date), OR Gabriel rules the late-fee posting out of the money-moving class and the frontmatter is re-declared accordingly.

**Description:** **`ora-pm-daily-crons` posts late fees (delinquency-check) and has no off-host backup trigger — declared `offhost-backup: none — GAP` on 2026-09-03.** ora-pm PR #24 (`monthly-billing-backup.yml`, cron `40 17 1 * *` UTC, still OPEN) covers monthly billing only. During the 2026-08-29→09-01 host outage this task's late-fee posting was silent for four days with nothing off-host to catch it (recovered in the 09-02 catch-up burst: 35 late fees). Gabriel's call: extend the ora-pm GitHub Actions backup to the two daily endpoints (critical-dates-alerts, delinquency-check — both idempotent per the endpoints' own upsert semantics, to be confirmed in the PR), or accept the gap explicitly in the frontmatter. Companion: `ora-pm-monthly-billing` is declared `pending` on PR #24 and flips to a live declaration when that PR merges.

**Update 2026-09-12 — fix built, NOT live; stays OPEN.** [ZeOoba/ora-pm PR #25](https://github.com/ZeOoba/ora-pm/pull/25) adds `.github/workflows/delinquency-backup.yml` (cron `10 16 * * *` UTC) + `scripts/delinquency-backup.sh` (13-case no-network test, CI green, adversarial refute pass: no logic defects). Scope correction to the description above: backs up **delinquency-check ONLY** — `critical-dates-alerts` is NOT double-fire safe (it inserts `sent_notifications` dedup rows before returning a digest only the laptop's Outlook-COM run can send) and is not money-moving. Double-fire safety of delinquency-check confirmed: `charges.idempotency_key TEXT UNIQUE` (`0002_financial_tables.sql:17`) + existing-fee guard. **Blocker found:** repo secret `ORA_PM_CRON_SECRET` does not exist (`gh secret list`, 2026-09-12) — so PR #24's `monthly-billing-backup.yml` has also never run and was wrongly declared `live since 2026-09-03`; both frontmatter lines corrected 2026-09-12 (`pending` / `dormant — secret missing`). **Close only when all three hold:** (1) Gabriel sets `ORA_PM_CRON_SECRET`, (2) PR #25 merged, (3) one real run of `delinquency-backup.yml` concludes `success` — cite the run URL, then flip the frontmatter to `live since <date>`. Adjacent, unchanged: [OI-234](#OI-234) (fee condition is charge age, not current overdue balance) — this backup makes that existing logic more reliable, it does not fix it.

**Closure 2026-09-12 (evidence):** (1) `ORA_PM_CRON_SECRET` set by Gabriel, listed by `gh secret list` at 2026-09-12T23:35:36Z; (2) [PR #25](https://github.com/ZeOoba/ora-pm/pull/25) merged `f756687`, `delinquency-backup.yml` active on main; (3) first real run (manual `workflow_dispatch`) concluded `success`: https://github.com/ZeOoba/ora-pm/actions/runs/34725864211 — self-test ALL PASS, `delinquency-check: HTTP 200 late_fees_posted=0 delinquent_count=68` (0 fees expected: OI-278 payments-feed guard + this month's fees already posted). `ora-pm-daily-crons` frontmatter now `live since 2026-09-12` with that URL. Companion `ora-pm-monthly-billing` moved `dormant` → `pending — awaiting first run` (first scheduled fire 2026-10-01 17:40Z; deliberately not proven by manual dispatch because that endpoint posts charges). Also landed from this item: [OI-234](#OI-234) fixed (PR #27), `register-scheduled-task` v2.24 live-proof rule + `automation-health-monitor` v1.10 backup checks ([ora-skills PR #52](https://github.com/ZeOoba/ora-skills/pull/52)).

### OI-078
**Status:** CLOSED 2026-09-18
**Opened:** 2026-08-05
**Source:** ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch)
**Severity:** CRITICAL (data exposure / authorization)
**Description:** `supabase/migrations/0001_core_entities.sql`, `0002_financial_tables.sql` (no RLS
anywhere in either), `0004_views_and_rls.sql:102-107` (RLS enabled on 6 tables only),
`src/lib/supabase.ts:3-6`, `src/portal/lib/supabase-portal.ts:4-7`. Row Level Security is enabled on
`charges`, `payments`, `lease_documents`, `lease_amendments`, `tenant_notices`,
`insurance_certificates` — and on nothing else. The 17 remaining tables (`properties`, `units`,
`tenants`, `leases`, `expenses`, `budgets`, `renewals`, `broker_commissions`, `cam_reconciliations`,
`correspondence_log`, `journal_entry_exports`, `lease_move_events`, `sent_notifications`,
`stripe_webhook_events`, `tenant_sales_reports`, `utility_meters`, `utility_readings`) have no
`ENABLE ROW LEVEL SECURITY` statement in any migration. `VITE_SUPABASE_URL` and
`VITE_SUPABASE_ANON_KEY` are compiled into the public JS bundle by design. In a stock Supabase
project `anon`/`authenticated` hold default GRANTs on `public` tables, so an RLS-disabled table is
readable and writable straight through PostgREST.
**Impact:** anyone who loads the site can extract the anon key and read the whole portfolio — 14
properties, ~140 tenants, contact PII, `stripe_customer_id`, full lease economics (base rent, CAM,
TI allowances, security deposits, options) — and, absent an explicit `REVOKE`, write to it:
rewriting `leases.base_rent_monthly`, or inserting `payments` rows that zero a tenant's balance in
`ar_ledger`.
**Relationship to [OI-048](#OI-048):** OI-048 records that the API uses the service-role key so RLS
is not the API's control, and that RLS reads as a safety net which is not actually one. This item is
the other half and the more severe one: for 17 tables the net is not merely bypassed by the API, it
does not exist at all on the internet-facing database endpoint. The in-repo rebuttal at
`supabase/migrations/README.md:23-29` and `server/db/client.ts:18-23` — "these policies protect a
code path that doesn't exist yet", true of the app and confirmed by grep — does not apply, because
the attacker brings their own PostgREST client rather than using the app's.
**Verification status (IMPORTANT — inferred, not verified):** the migration-level facts above were
independently re-verified this run by direct grep against the pinned worktree, not taken on the
agent's word. What was NOT verified is whether the live Supabase project actually grants
`anon`/`authenticated` on these tables — this sweep is report-only and does no live probing. Do not
record this as exploited-in-production until someone runs the check. One command settles it:
`curl -s "https://<project-ref>.supabase.co/rest/v1/tenants?select=id,name&limit=1" -H "apikey: <anon key from the deployed bundle>"`
— any row returned confirms it.
**Candidate fix (NOT applied — this sweep is report-only):** enable RLS on every `public` table (no
policies = deny-all for anon/authenticated, service-role API unaffected), or
`REVOKE ALL ON <table> FROM anon, authenticated` for tables that should never be client-reachable.
Then change `tests/db/rls-inventory.test.ts` from a manifest match to a COMPLETENESS check — parse
every `CREATE TABLE` in the migrations and fail on any without a corresponding enable or a
documented exemption. As written that test asserts the claim set hasn't changed, which locks the gap
in rather than catching it. Sequence with [OI-080](#OI-080) and [OI-079](#OI-079): they are one
chain, and fixing any one alone leaves it intact.
**Closure evidence (2026-09-18):** **CODE FIXED 2026-08-17** via `supabase/migrations/0013_enable_rls_remaining_tables.sql` (default-deny, no policies), REFUTE-verified, merged to `main` via [ora-pm PR #23](https://github.com/ZeOoba/ora-pm/pull/23) (`aede030`). Production migrations sat unapplied for weeks pending `SUPABASE_ACCESS_TOKEN`/`SUPABASE_DB_PASSWORD` repo secrets (dry-run executed 2026-08-22 failed cleanly at the credential step). Those secrets were confirmed set on `ZeOoba/ora-pm` 2026-09-16. **CONFIRMED CLOSED 2026-09-18:** dispatched `DB Migrate (manual)` as a read-only dry-run against production ([run 35388593228](https://github.com/ZeOoba/ora-pm/actions/runs/35388593228)) — `supabase migration list --linked` shows all 17 migrations 0001-0017 with LOCAL==REMOTE, including `0013_enable_rls_remaining_tables.sql`; `supabase db push --dry-run` reports "Remote database is up to date." RLS is live in production.
**Auto-check:** none.

### OI-090
**Status:** CLOSED
**Opened:** 2026-08-05
**Closed:** 2026-09-13
**Source:** ora-appsec-sweep 2026-08-05 (oxford-command-center @ `175e3f9`, security-auditor dispatch)
**Severity:** MEDIUM (unbounded consumption, OWASP-LLM10)
**Description:** `server/index.ts:460-493` (`/api/ai`, SSE), `:447-453` (`/api/documents/search`),
`:358` (`/api/actions/om-extract`). Per-request bounds are correct and worth keeping — the agent
loop caps at `maxTurns: 8` (`server/ai/agent.ts:178`) and `max_tokens: 16000` (`:203`), the upload
caps at 25 MB — but nothing bounds CONCURRENT or REPEATED requests. Each `/api/ai` call spends real
Anthropic tokens against the machine's `ANTHROPIC_API_KEY`.
**Impact:** any local process — or a cross-site simple POST per [OI-050](#OI-050) — can drive
unbounded API spend and memory pressure on a workstation with a ~5.7 GB ceiling. Combined with
OI-050 this is the cheapest denial-of-wallet path in the repo. ora-pm's equivalent exposure was
closed under OI-038/044 (KV-backed `checkRateLimit`, per-route ceilings); oxford-command-center has
no counterpart at all.
**Evidence:** [oxford-command-center PR #328](https://github.com/ZeOoba/oxford-command-center/pull/328)
merged `b34add2d` 2026-09-13. New `server/rate-limit.ts` — in-process token bucket
(`createRateLimiter`) + concurrency gate (`createConcurrencyLimiter`), no external/KV dependency.
Mounted per-route (fresh instance each) after the OI-050 boundary/cors/accessAuthz chain:
`/api/ai` 10 starts/min + max 3 concurrent, `/api/actions/om-extract` 5/min,
`/api/documents/search` 90/min (raised from an initial 30/min after REFUTE caught that ordinary
interactive typing — no debounce on the search box — would trip 30). The concurrency gate's slot
tracks the actual SSE response BODY's lifetime via a wrapping `holdUntilSettled` stream, not the
handler function's synchronous return (`streamSSE()` returns before the agent loop finishes, so a
naive release-in-finally would gate nothing); client disconnects forward to the existing
`AbortController` so an abandoned client stops spending tokens.
**Two REFUTE rounds, both real findings, both fixed before merge:**
(1) HIGH — the first cut mounted limiters with `app.use(path, ...)`, method-agnostic in Hono. Three
unauthenticated `HEAD /api/ai` requests permanently exhausted the concurrency gate (Hono discards the
HEAD response body before the wrapped stream is ever read, so release never fires), killing the route
until restart; any wrong-method request also drained the rate bucket for free. Fixed with
method-scoped `app.on(METHOD, path, ...)` mounts plus a defensive HEAD guard in the concurrency
wrapper; independently re-verified with raw-TCP probes against a real `@hono/node-server` instance
(not just in-memory tests) — concurrent load, client-abort, and every throw/no-body exit path all
release correctly, and no path-spelling or method trick routes around it.
(2) MEDIUM — the original 30/min search limit would trip on ordinary typing (fetch per keystroke, no
debounce); raised to 90/min.
**Follow-ups filed, not blocking:** the Cloudflare Pages mirror (`functions/api/ai.ts`) runs the same
agent with no rate bound — OI-090 is closed for the Brain Server/tunnel surface only, not the mirror;
`/api/documents/search`'s 429 still surfaces client-side as a generic "Search unavailable" message
(needs a debounce + distinct 429 branch); a slow reader that never drains its `/api/ai` stream holds a
concurrency slot indefinitely (same-machine-process only, not browser-reachable) — a max-stream-lifetime
timeout would close this; pre-existing (not introduced here) — `stream.onAbort` in the real `/api/ai`
handler is registered after `await c.req.json()`, so a disconnect during body parsing isn't caught.
**Auto-check:** none.

### OI-127
**Status:** CLOSED 2026-09-18 — duplicate of OI-135, same fix — see OI-135 for the live item.
**Opened:** 2026-08-12 (id reserved 2026-08-12T20:52:45Z by session `e0f8485e`; row written 2026-08-12 by session
`1de11c79` during an orphan-reservation sweep, with the reserving session inactive on it and holding no claim)
**Severity:** see OI-135 — this row carries no independent severity assessment.

**Why this row exists.** The id was reserved and the row never written, so `allocate-oi-id.py --report` listed it
as an orphan. Sixty-eight minutes later a different session (`2fb76021`) reserved **OI-135** for the same defect
and filed it with fuller evidence. Leaving OI-127 as a bare reservation invites a third session to re-derive the
same finding a third time; writing it as a full standalone row would put two live items in the tracker for one
defect. Hence a pointer.

**The defect (tracked under OI-135, not here).** `hooks/git-prepush-hook-tests-gate.py` applies a 180s per-test
timeout budget. Under concurrent load that budget is below the real runtime of several suites, so healthy tests
exit-124 and the gate hard-blocks the push. Measured on 2026-08-12: 5 sessions hit exit-124 on
`test-eos-review-gate.py` and siblings, ~150–300s actual against the 180s budget under 12–16+ concurrent
sessions, **all clearing on rerun**.

Independently corroborated the same day: the push of `oi122-gate-msg` (PR #67) emitted
`timeout-retry (timed out under load, passed on the doubled-budget rerun; not blocking)` naming
`test-commit-hygiene-guard.py`, `test-eos-review-gate.py`, and `test-memory-orphan-link-guard.py` — i.e. the
doubled-budget rerun path already exists and works; the first-pass budget is what is mis-set.

**Do not fix from this row.** Track the fix, evidence, and any REFUTE pass under **OI-135**.

**Related:** [OI-119](#OI-119) — same gate, the *flakiness* failure mode (errored tests are not retried) rather
than the timeout budget. A fix for one should be checked against the other.

**Closure evidence (2026-09-18):** duplicate/orphan-reservation closure — see this item's own text above; OI-135 (the item it points to) is already closed elsewhere in the tracker history.

### OI-079
**Status:** CLOSED 2026-09-18
**Opened:** 2026-08-05
**Source:** ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch)
**Severity:** HIGH (cross-tenant data exposure)
**Description:** `supabase/migrations/0011_appsec_idempotency_and_scale.sql:118-151` (`ar_ledger`),
`0004_views_and_rls.sql:33-99` (`rent_roll`, `critical_dates`). None of the three views is created
`WITH (security_invoker = true)` — the string does not appear anywhere in `supabase/migrations/**`
(verified by grep this run). A view without it executes with the view owner's privileges and
therefore ignores the RLS policies on the underlying `charges`/`payments`/`leases`/`tenants`.
**Impact:** one `GET /rest/v1/ar_ledger?select=tenant_name,balance` with the anon key — or with an
`authenticated` JWT minted via [OI-080](#OI-080) — returns every tenant's name, total charged, total
paid, balance and property. `rent_roll` additionally discloses full per-suite rent economics. This
survives a fix to [OI-078](#OI-078), which is why it is filed separately.
**Candidate fix (NOT applied):** `ALTER VIEW ar_ledger SET (security_invoker = true);` (same for
`rent_roll`, `critical_dates`), plus
`REVOKE ALL ON ar_ledger, rent_roll, critical_dates FROM anon, authenticated;`. The service-role API
reads all three (`server/routes/reports.ts:13,24,34`, `cron.ts:160,322`, `stripe.ts:159`) and is
unaffected by either change.
**Auto-check:** none.

**Closed:** 2026-09-18

**Closure evidence (2026-09-19):** `supabase/migrations/0012_view_security_invoker.sql` sets `security_invoker = true` on `ar_ledger`, `rent_roll` and `critical_dates`. `DB Migrate (manual)` dry-run against production ([run 35388593228](https://github.com/ZeOoba/ora-pm/actions/runs/35388593228), 2026-09-18) lists `0012` with LOCAL==REMOTE and reports "Remote database is up to date." The same evidence closed [OI-078](open-items-tracker-history.md#OI-078).

### OI-171
**Status:** CLOSED 2026-09-19
**Opened:** 2026-08-16
**Source:** found while root-causing Gabriel's report of the `loans · name` flag in the Command
Center safety section. That flag itself is correct behavior and was ruled LEAVE-AS-IS in-turn; this
item is the separate defect one layer downstream.
**Severity:** MEDIUM — no wrong numbers, but a permanent false `warn` email is exactly what trains
a reader to ignore the real one. Self-masking alert.

**Defect.** `ora-cc-snapshot-refresh` STEP 5 clause (b) escalated to email on "at least one
data-quality flag of severity `warn` or higher". The single permanent, intentional flag —
`loans · name`, the tombstoned Loan Index row 24 duplicate marker — **is** `warn`. So the gate's own
condition matched it and every clean exit-0/no-drift run still sent `[ALERT]`.

**Why it slipped through.** The v1.1 severity gate (`1706bc2`, 2026-08-12 15:42:50 -0400) was written
around the belief that the permanent flag was `severity: info`. It had already been bumped `info` →
`warn` in `490d89f` (2026-08-11 18:15:14 -0400, oxford-command-center) **~21 hours earlier** — a
deliberate change, because skipping the row removes its balance from aggregate debt and moves
portfolio LTV in the falsely-clearing direction against Hard Invariant 4's 40% ceiling
(`server/workbook/parse.ts:655-658`). Two individually-correct changes; the interaction is the bug.
The stale `info` claim propagated into the SKILL.md body, its frontmatter description, and
`reference_cc_snapshot_refresh_dq_flag_alert_is_count_not_severity.md` (archived 2026-08-21, finding closed — see `_archive/reference_cc_snapshot_refresh_dq_flag_alert_is_count_not_severity_archived_2026-08-21.md`) — all three corrected 2026-08-16.

**Fix (Gabriel ruled in-turn, multiple-choice: "Allowlist the ratified tombstone").** SKILL.md v1.3
adds a RATIFIED-TOMBSTONE ALLOWLIST to the severity gate: clause (b) now escalates only on a
warn-or-higher flag NOT on the allowlist. Exactly one flag is allowlisted and the match requires all
four of `entity=="loans"`, `field=="name"`, `rawValue` exactly `⚠ DUPLICATE OF ROW 22 — DO NOT USE`,
and `issue` containing `Loan Index row 24 is tombstoned`. Any deviation — different row number, a
second tombstone, an altered marker — is NOT allowlisted and DOES email. It suppresses one ruled-on
flag, never a class.

**Explicitly NOT fixed by downgrading the parser back to `info`.** That would re-open the
governor-guard hole `490d89f` closed. Suppression is at the ALERT layer only. Row 24 carries no
balance either way: `C24:G24` are all `='Portfolio Summary — Internal'!#REF!`.

**Auto-check:** none automated. To verify by hand:
`python -c "import json;print([f['severity'] for f in json.load(open(r'C:/Users/Owner/oxford-command-center/data/snapshots/portfolio.json',encoding='utf-8'))['dataQuality']])"`
must print `['warn']`, AND `grep -c "RATIFIED-TOMBSTONE ALLOWLIST" ~/.claude/scheduled-tasks/ora-cc-snapshot-refresh/SKILL.md`
must be ≥ 1. Both true ⇒ gate is correctly configured. Real proof is the 2026-08-17 run posting a
Notion note with **no** email.

**Closed:** 2026-09-19

**Closure evidence (2026-09-19):** (1) `grep -c "RATIFIED-TOMBSTONE ALLOWLIST" ~/.claude/scheduled-tasks/ora-cc-snapshot-refresh/SKILL.md` = 3. (2) `send-log.txt` holds no `[ALERT] ora-cc-snapshot-refresh - data-quality flag count > 0` email after 2026-08-11, across 2026-08-17 to 2026-09-18, while the task kept running and alerting for unrelated causes (08-17, 08-24, 09-02, 09-05, 09-07). (3) `portfolio.json` `dataQuality` now reads `[]`, not the `['warn']` the hand-check expected, so the tombstone flag is no longer emitted at all and there is nothing left to escalate.

### OI-318
**Status:** CLOSED 2026-09-19
**See:** the Closed table above — the row's own one-line cell is the full write-up; not restated here per this file's own text-lives-in-one-place rule.
**Opened:** 2026-09-18
**Closed:** 2026-09-19

**Closure evidence (2026-09-19):** Gabriel ruled "Leave history alone" in-turn (interactive choice). Working-copy redaction stands (`ff48473` on `origin/main`); commit `ec9c626` remains in public history on `ZeOoba/ora-skills`. The detail is address-level (no owner names) for two never-call sellers that are not on the `confidential-terms.json` roster. No rewrite, no force-push.

### OI-031
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN
**Opened:** 2026-07-27
**Source:** `orphaned-task-forensics` trace of the `ora-master-workbook-ingest` 2026-07-20 silent
gap, [event_log.md](event_log.md#2026-07-27)
**Description:** `fleet-status.py`'s missed-cycle detectors are structurally blind to an
already-established recurring task silently skipping a single scheduled fire — confirmed by
reading the script directly (`C:\Users\Owner\.claude\maintenance\fleet-status.py`). "Overdue"
(`never_ran_overdue`) only fires for a RECURRING task that has NEVER fired even once (a
cadence-buffer heuristic meant for brand-new tasks). "Missed/stuck" (`expired_needs_attention`)
applies only to expired ONE-TIME tasks. Throttle-skip tracking catches a task that fired and got
rate-limited, not one that never attempted to fire at all. None of the three checks can detect
"this weekly/monthly task has run before, is still enabled, but silently missed this one cycle" —
exactly the gap that let `ora-master-workbook-ingest`'s 2026-07-20 Monday fire go unnoticed for a
full week despite the fleet's own Monday-afternoon schematic-refresh snapshot reporting "0
overdue, 0 missed/stuck" that same day.
**Candidate fix (not built):** extend `fleet-status.py` with a per-task expected-fire-window
check for tasks that HAVE fired before, comparing `lastRunAt` against the most recent
cron-predicate fire time (mirroring `automation-health-monitor`'s Step 0.5 `expectedFireTime`
walk-backward logic, already implemented for the LAMS fleet) — flagging MISSED/OUT-OF-WINDOW
the same way that step does, rather than only checking never-fired-at-all or expired-one-time
states.
**Auto-check:** none (a tooling-logic gap, not a fleet-registry state comparable to the closed
Auto-check vocabulary above).

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** fleet-status.py (~L326-361) has the missed-cycle detector; maintenance/_tests/test_fleet_status_missed_cycle.py exists. OI-058/070 stay open on their own terms.

### OI-062
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN
**Opened:** 2026-08-04
**Source:** `pending_reimport.py` frontmatter-normalization session, 2026-08-04 (port of PR #35's
YAML-quoting fix into `pending_reimport.py`'s comparator, [PR #38](https://github.com/ZeOoba/ora-skills/pull/38),
merged `33d2579`)
**Description:** At session start, `C:\Users\Owner\ora-skills` (the MAIN checkout, not a
worktree) had two uncommitted changes with no attributable owner: `plugins/ora-operations-extensions/plugin-build.json`
modified (version bump `0.1.5` → `0.1.6`) and an untracked `_check_plugin.py` (112 bytes,
mtime 2026-07-29). Neither relates to any work this session did. Per the repo's single-writer
convention, isolated all of this session's own work into a git worktree (`.claude/worktrees/pending-reimport-frontmatter-norm`)
rather than touch or clean up the stray files, then fast-forwarded the main checkout's `main`
branch after the PR merged — confirmed the two stray changes were still present and untouched
afterward. No `claim_work.py`-style claim was found recorded against either file. Left open
because deleting or committing someone else's possible in-progress change without confirmation
would be the wrong default; needs either the owning session to finish/commit it, or Gabriel to
confirm it's abandoned so it can be discarded.
**Auto-check:** none.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** ora-skills plugin-build.json no longer modified and _check_plugin.py gone; only unrelated untracked _archive dirs remain.

### OI-074
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN (partially fixed — CI piece inert pending Gabriel-provisioned secrets)
**Opened:** 2026-08-04
**Source:** OI-073 follow-up session, root-causing why ora-pm migrations keep landing untracked
**Severity:** MEDIUM (tooling blind spot, not a live defect — same class as OI-073/OI-048)
**Root cause (confirmed by direct testing, not inference):** this Code sandbox has no
`SUPABASE_ACCESS_TOKEN` set (`npx supabase migration list --linked` fails with
`LegacyPlatformAuthRequiredError`) and no `supabase login` session exists — so `supabase db push`/`migration
up`, the only CLI commands that write a row into `supabase_migrations.schema_migrations` as a side effect of
applying a migration, cannot run from here. Raw TCP to the Supabase Postgres pooler on 5432 DOES connect from
this sandbox (contradicting an earlier 2026-08-03 event_log claim of "no network egress at all" — that may
have been a different sandbox/environment, or a stale claim), but CLI auth requires the access token
regardless of TCP reachability. Sessions have therefore applied migrations out-of-band instead — pasting SQL
into the Supabase Dashboard SQL editor via Claude-in-Chrome, or an ad-hoc Node script against the
service-role key (0008's self-documented history) — and neither path touches the tracking table. This is the
process OI-073 left unidentified.
**Fix, two-tier (Gabriel-directed via AskUserQuestion, 2026-08-04):**
1. **Fallback (built, tested, no credentials needed):** `ora-pm/scripts/prepare-migration-for-dashboard.mjs`
   — given a migration file, wraps its SQL together with an idempotent
   `INSERT ... ON CONFLICT (version) DO NOTHING` tracking row in a single `BEGIN;...COMMIT;` block, so a
   human pastes ONE block into the Dashboard SQL editor and apply+track can't be split into two steps to
   forget between. Guards added after an adversarial REFUTE pass (security-auditor agent): refuses to wrap
   SQL containing `CONCURRENTLY`/`VACUUM`/`ALTER SYSTEM`/`CREATE DATABASE` (can't run inside a transaction),
   and refuses unbalanced `/* */` block comments (would silently swallow the appended COMMIT). 21 vitest
   tests incl. a real-subprocess CLI test (caught and fixed a genuine bug: the original `import.meta.url`
   vs. hand-built `file://${argv[1]}` comparison never matches on Windows, silently no-op'ing `main()`).
   404→414/414 suite green, typecheck clean. **Caveat, not yet empirically verified:** the script's
   atomicity claim assumes the Supabase Dashboard SQL editor honors explicit `BEGIN`/`COMMIT` the way
   `psql -f` does — untested against the live editor; probe instructions are in the script's own header
   comment before relying on it for anything touching `charges`/`payments`/`ar_ledger`.
2. **Primary path (built, YAML-validated, NOT yet live-tested — needs Gabriel):** `ora-pm/.github/workflows/db-migrate.yml`,
   a `workflow_dispatch`-only GitHub Actions job that runs the real `supabase db push` (auto-tracking) against
   project ref `tvfarkddtbtdrpvvehth`. Requires two repo secrets Gabriel has not yet added —
   `SUPABASE_ACCESS_TOKEN`, `SUPABASE_DB_PASSWORD` — until then it fails cleanly at the link step. REFUTE
   pass caught and fixed two HIGH findings before this could be considered safe to use: `dry_run` now
   defaults to `true` (a bare "Run workflow" click is always a no-op preview), and the job is gated
   `if: github.ref == 'refs/heads/main'` (workflow_dispatch could otherwise target an unmerged branch and
   push an unreviewed migration straight to prod). Added `timeout-minutes: 10` as defense-in-depth.
**Residual, not closed:** the CI path cannot be exercised until Gabriel adds the two secrets and runs it once
with `dry_run: true`; the dashboard-paste script's core atomicity assumption is unverified against the live
Supabase Studio editor. Full REFUTE report (security-auditor agent, 2026-08-04) available in this session's
transcript — 2 HIGH (fixed), 2 MEDIUM (1 fixed via `timeout-minutes`, 1 residual — atomicity), 3 LOW (fixed:
transaction-unsafe-SQL guard, unbalanced-comment guard; 1 accepted as-is — no static pre-flight-comment
detector added, judged low-value for a script whose whole job is to wrap arbitrary migration SQL verbatim).
**Auto-check:** none.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** SUPABASE_ACCESS_TOKEN and SUPABASE_DB_PASSWORD provisioned 2026-09-16; db-migrate.yml runs on 09-17 and 09-18 succeeded.

### OI-075
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN (fix built + scheduled; first live alert not yet observed)
**Opened:** 2026-08-04
**Source:** Session brief follow-up — standing fix for skill-store/repo drift (2 same-day REVERSE-DIRECTION
reconciles, event_log.md commits `a2b34ad` and `3825ac5`)
**Severity:** MEDIUM (process gap — content itself was recovered both times, but only by manual diffing)
**Description:** Cowork's `save_skill`/`create-skill` writes straight to the AppData runtime skill cache from
outside git — no repo commit, and no Code-side hook can intercept a different app's write (confirmed: grepped
`hooks/` for any save_skill/Cowork interception point, found none). **Correction to the session brief's framing:**
the detector this item asks for was NOT missing — `ora-skills/tools/repo_first_check.py` (merged to main
2026-08-03/04, PR `store-ahead-of-repo-ledger`, commit `1e714eb`) already does exactly this, per-file (not
just SKILL.md), with proper git-ancestry-based CACHE-AHEAD/DIVERGENT/REPO-MISSING classification and a
rescue-copy safety net — built by a concurrent session working the same problem. It was already wired into
two places: the ora-skills pre-commit hook (`--check-staged`, only fires on a commit touching that exact
skill) and `ora-doctrine-integrity-guard`'s **daily** sweep (`--all`, cron `55 12 * * *`, alarms via
email+Notion on any `!! REPO-FIRST` finding). Neither catches drift on a skill nobody is committing to AND
edited same-day — daily is too slow for "3 occurrences in one day."
**Fix:** new CC/MCP scheduled task `ora-skill-cache-drift-alert` (registered via supervised
`create_scheduled_task`, cron `*/30 * * * *`), narrowly scoped to ONLY the `repo_first_check.py --all` sweep
(not the other 3 doctrine-guard engines, so a 30-min cadence stays cheap). On a finding NOT already tracked
by an open item (cross-checks this tracker first, dedup by skill name — avoids re-filing every 30 min for
the same unresolved drift), it allocates a real OI id via `allocate-oi-id.py`, appends an entry to this
tracker (isolated hunk, re-verify-before-write — same discipline as any interactive session), and alerts via
Notion + email (reusing `ora-doctrine-integrity-guard`'s proven STEP 3 alarm mechanism). A clean run is
silent — no Notion, no email, no OI item — matching every other guard in this fleet.
**Residual, not closed:** built and registered but has not yet fired against a real finding (next run within
30 min of registration) — the dedup-cross-check logic and the OI-filing step are unverified against a live
drift event. `ora-doctrine-integrity-guard`'s daily sweep and this task's 30-min sweep will both alarm on the
same finding until the daily guard's own STEP 3 is taught to check this task's already-filed OI items too
(not done this session — flagged, not fixed, to avoid scope creep into a guard another session may still be
actively working: `b5d8615c` was mid-session on "3 systematization items" when this session's `claim_work.py`
call overwrote its `repo-housekeeping` claim broadcast).
**Auto-check:** ~~`ora-skill-cache-drift-alert`, cron `*/30 * * * *`~~ → **`ora-doctrine-integrity-guard` engine 4, cron `55 12 * * *`** (updated 2026-08-09).
**2026-08-09 — the fix built for this item was RETIRED; item stays OPEN with a narrowed residual.**
`ora-skill-cache-drift-alert` is gone from the CC/MCP registry (archived to
`scheduled-tasks/_archive_2026-08-09_retired/`; RATIFIED drop logged in `event_log.md`). It was collapsed
`*/30` → `0 11 * * *` by the 2026-08-05 ORA-wide once/day cadence policy, which erased the only thing it did
that the daily guard didn't — sub-daily detection — leaving it running the identical `repo_first_check.py --all`
sweep ~2h before `ora-doctrine-integrity-guard`. **Sweep coverage is NOT lost** (two live invokers remain: the
`ora-skills` pre-commit hook `--check-staged`, and the daily guard's engine 4). **What IS lost, and is the
residual this item now tracks:** the retired task also filed a durable OI-NNN item on a finding and cross-checked
this tracker to dedup; the daily guard alarms via email + Notion only, so a finding can still be lost to a
scrolled terminal or an unread Notion page. Closing OI-075 would assert a durable-record capability that no
longer exists — so it stays OPEN. The original "not yet fired against a real finding" residual is moot: the task
never fired on a real finding before retirement (its last live sweep, 2026-08-09, returned 50 skills / 0 findings).

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** Superseded: ora-skill-cache-drift-alert retired 2026-08-09; ora-doctrine-integrity-guard engine 4 replaced it; PR #39 merged.

### OI-116
**Status:** CLOSED 2026-09-19
**Prior status:** CLOSED 2026-09-07
**Opened:** 2026-08-11
**Source:** landing [PR #52](https://github.com/ZeOoba/ora-claude-config/pull/52) (`claim_work.py` refusal
gate), 2026-08-11 — hit twice in a single session, then a third time filing this very item
**Severity:** MEDIUM — it removes the only non-destructive response to a claim collision.
**Description:** An **unattended** session (scheduled-task run or dispatched session) can hold a
`claim_work.py` slug indefinitely, and cannot be contacted to release it. Two mechanisms compound:
`mcp__ccd_session_mgmt__send_message` refuses delivery to unattended sessions outright
(`"Session <id> is unattended … messages can't be delivered there"`), and `shared-checkout-guard.py`'s
`_self_renew_claims` re-stamps `claimed_at` on **all** of a session's live claims whenever it edits
anywhere in a claim-relevant repo — so the 2-hour TTL never expires the claim while that session lives.
The holder is therefore neither reachable nor wait-out-able.

**Observed three times on 2026-08-11**, all real, none contrived:
1. `1d88885d` (host `local_fdd428b9`, "Ora deal aging sla") held `hooks-override-auth` while this
   session needed it. `send_message` refused; its claim self-renewed at 15:17:24 while being read.
   Worked around by claiming a distinct slug, `hooks-override-auth-claim-work`, with `--paths`.
2. `05236b94` (host `local_25942895`) held `open-items-tracker` with `--paths` on this very file.
   `send_message` refused again.
3. Filing THIS item hit (2) — the refusal correctly reported an `OVERLAP` verdict on
   `open-items-tracker.md`, and the only paths forward were `--force` or an isolated worktree + PR.

**Why the refusal gate makes this sharper, not worse:** before PR #52 the collision was invisible and
the clobber silent, so this was never felt. Now the collision is named and correctly refused — which is
the improvement — but the recommended response ("message the holder", printed from the claim's
`host_session_id`, the field OI-108 added specifically to make holders contactable) is a dead end for
exactly the class of session most likely to hold a slug unattended for hours. That leaves `--force` as
the only exit, which is the operation the gate exists to make rare.

**Candidate fixes (NOT applied, unevaluated):** (a) record whether the claiming session is unattended
(the runtime knows) and have the refusal say so, replacing the useless "message them" line with the
honest "this holder cannot be contacted — `--force` or use a distinct slug"; (b) scope
`_self_renew_claims` to unattended sessions differently, or cap total renewals, so an unattended claim
can age out even while its session lives; (c) have scheduled-task wrappers `release` on exit.
Note (b) fights `_self_renew_claims`'s own documented rationale — read its docstring before touching it.
**Closing condition (as originally drafted):** a session that collides with an unattended holder gets a
refusal that names the holder as uncontactable and offers a next step that is not `--force`.
**Resolved differently, closed 2026-09-07.** Gabriel ratified a reserved `sched-` slug namespace instead
of options (a)/(b)/(c) above: an unattended claim now gets a 30-minute TTL (vs. 120 default,
`min(caller_ttl, 30)`, never widened) so it ages out before it can block a live person, and the refusal
message states outright that force-takeover is ROUTINE for such a holder — rather than avoiding `--force`,
it makes `--force` the documented, safe, expected response. Implemented in `hooks/lib/claim_work.py`
(`is_sched_slug()`, `_effective_ttl()`; doctrine: `memory/tech.md` §3e; landed via
[PR #171](https://github.com/ZeOoba/ora-claude-config/pull/171), merged). That alone left the fix inert,
though — no scheduled task's own instructions ever claimed under a `sched-` slug, so the shorter TTL and
routine-force-takeover language never reached a live unattended holder. Closed today by adding the
carrier: `register-scheduled-task` v2.21 (ora-skills `bc42852`) adds step 3c + a QC-gate item requiring
any `claim_work.py claim` call in a scheduled task's own instructions to use `sched-<slug>`, not the bare
slug, going forward.
**Auto-check:** none.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** origin/main claim_work.py has is_sched_slug (L171) and _effective_ttl (L176); ora-skills bc42852 'v2.21 sched- carrier (OI-116)'. Section already said CLOSED 2026-09-07.

### OI-129
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN (diagnosed and reproduced same-day; fix is a judgement call between three options)
**Opened:** 2026-08-12
**Source:** `maintenance/_tests/test_check_open_items_duplicate_ids.py`, hit via `.git/hooks/pre-push` gate 2
(`hooks/git-prepush-hook-tests-gate.py`) while pushing two unrelated `ora-deal-*` SKILL.md commits
(`c0517fb`, `2c3d8ce`)
**Severity:** MEDIUM — blocks arbitrary sessions' pushes, but the escape (fix the tracker, or re-run) is cheap
and no data is at risk.

**Description:** The test asserts `canonical open-items-tracker.md has zero id collisions right now`. That is a
global invariant evaluated against a **shared mutable file that every session writes continuously** — and it is
evaluated from inside the *pre-push* gate, so when it trips it blocks whatever push happens to be in flight,
regardless of what that push touches.

**Reproduced, not inferred (2026-08-12):**

| Observation | Value |
|---|---|
| ids allocated in one hour, by six different sessions | OI-123 (19:56Z) → OI-128 (20:53Z) |
| table rows actually filed at that moment | through OI-123 only |
| file state that tripped the assertion | `orphaned_sections: ['OI-125']`, `missing_sections: ['OI-121']` |
| what OI-125 was | section written, table row not yet written; id allocated 20:26Z, ~28 min earlier |
| what it blocked | two SKILL.md commits touching none of this code |
| failure signature | `exit 1` — a real assertion, **not** `exit 124` |

**This is NOT the [OI-119](#OI-119) / OI-127 load-flake class, and must not be closed as a duplicate of it.**
Those are timing failures (`exit 124`, tests exceeding a 180s per-test budget under concurrency) and their fixes
are retries and bigger budgets. This one is **deterministic**: it reproduces on a completely idle machine any
time a half-filed item is sitting in the tracker, and no amount of retrying or budget-raising touches it. The
two classes did co-occur on the same push, which is precisely why they are easy to conflate — the run reported
`test-eos-review-gate.py` (timeout, OI-119's class) and this test (assertion, this item) side by side.

**A section-before-row file state is normal, not corruption.** Writing the detail section first and the table
row second is a perfectly reasonable authoring order, and with six sessions filing concurrently the file is
*routinely* mid-write. The test currently treats that transient as a defect.

**Keep the fixture half — it works.** The same test file correctly caught a seeded duplicate `OI-027` in its own
temp `dirty-tracker.md` during this run. The defect is only in the assertion that reaches out to the live
canonical file.

**Fix options (pick one; not yet decided):**
1. Assert only against fixtures; move the canonical-file check to a **non-blocking** report (matches how the
   doctrine gate reports warnings without blocking).
2. Keep it blocking, but treat `section-without-row` (and `row-without-section`) as **in-flight**, not a
   collision — reserve the block for genuine duplicate ids, which is the actual corruption this guards against.
3. Evaluate the invariant against the tracker **as committed in HEAD** rather than the working tree, so another
   session's uncommitted mid-write cannot block a push.

**Note on the related gap this surfaced:** OI-121 has had a table row since 2026-08-11 22:54Z with no `### OI-121`
detail section — ~22 h, so its own `[OI-121](#OI-121)` self-link resolves to nothing. The checker rates that INFO
("a one-line row is often the whole story"), which is defensible, but the dead self-link is worth a decision.

**Auto-check:** this item IS the auto-check's design. Whichever option is chosen, the acceptance test is: with a
deliberately half-filed item in the tracker, an unrelated `git push` must succeed.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** Main test file now treats orphaned/missing sections as advisory only (L186-190, 296-302); duplicates still fail.

### OI-132
**Status:** CLOSED 2026-09-19
**Prior status:** FIX APPLIED 2026-08-12 — options 2 **and 3** both shipped (`ora-sofr-direct-prefetch` **v1.2** then
**v1.3**). Option 3 adds STEP 4b: a closed-enum `supersede_status` (`NO_PATCH_NEEDED` · `NOT_EXPECTED` ·
`EXPECTED_NOT_YET_OBSERVED` · `OBSERVED` · `FAILED`) appended one line per run to
`maintenance/_state/sofr-supersede-status.log`, on **every** terminating path including no-ops and failures — a
log that recorded only successes would have no denominator and could not produce a rate. Write path verified live
2026-08-12 via Desktop Commander (creates, appends, `Select-String`-countable). Passive telemetry: nothing
consumes it and it raises no alarm. Kept **OPEN**,
because the fix is a wording/branching change that cannot be confirmed until the next catch-up burst puts both
producers in the same window. Nothing observable changes on a normal-cadence day, when `am_brief_pending` is
false and the flat "landed" path is already correct. Close only after a run log shows the EXPECTED wording on a
real burst. Option 3 (a `supersede_status` enum, the only way to *count* the hazard) was deliberately NOT bundled
and remains open below.
**Opened:** 2026-08-12
**Source:** `~/.claude/scheduled-tasks/ora-sofr-direct-prefetch/SKILL.md` STEP 4 — caught by that task's own
2026-08-12 run while it was executing, not by a later audit
**Severity:** LOW — no data loss or wrong figure in the observed case; the cost is a run-log claim that becomes
false minutes after it is written, plus silent undercounting of the ordering hazard v1.1 exists to manage.

**Description:** STEP 4 re-fetches the Rate Snapshot page immediately after STEP 3c's write and classifies the
result three ways: *my write landed* · *superseded by `ora-am-brief` (also a PASS)* · *still stale (FAIL)*. The
supersede branch was added in v1.1 precisely for the catch-up-burst case where both producers backfill together.

But the verify fires **seconds** after the write, while `ora-am-brief` — dispatched in the same burst — is still
mid-run and does not write for several more minutes. So STEP 4 reliably observes "my write landed" and the
supersede branch is, in that scenario, **unreachable by construction**.

**Measured 2026-08-12 (timestamps from the CC registry and the Notion page's own `as of` stamps):**

| Event | Time (UTC) | ET |
|---|---|---|
| `ora-sofr-direct-prefetch` dispatched | `15:13:20.983Z` | 11:13:20 |
| `ora-am-brief` dispatched | `15:13:21.612Z` | 11:13:21 |
| prefetch STEP 2 read the page (saw 08-11 values) | `15:14:11Z`-ish | 11:14 |
| prefetch write landed; STEP 4 verified, logged **"no supersede"** | `15:14:11.040Z` | 11:14:11 |
| `ora-am-brief` rewrote §2, superseding the patch | `15:20:26.837Z` | 11:20:26 |

Gap between the verify and the supersede: **~6 minutes**. The two producers dispatched **629 ms** apart.

**No data harm this run, and that is not luck to rely on.** `ora-am-brief`'s own run note records that it pulled
the NY Fed API independently and "observed an exact match" on all five SOFR fields. The values agreed because
both read the same upstream minutes apart — not because anything reconciled them.

**Do NOT close this as a duplicate of [OI-129](#OI-129).** That item is about a *test* asserting on live mutable
state and blocking pushes. This one is about a *scheduled task* verifying too early to observe the event its
own spec tells it to look for. They share the 2026-08-12 burst as a trigger and nothing else.

**Fix options — 2 APPLIED (v1.2) and 3 APPLIED (v1.3), both 2026-08-12; 1 and 4 declined:**
1. Re-verify after a delay (5–10 min). Correct but expensive — holds a session open purely to watch.
2. **Condition the wording on state STEP 2 already has.** STEP 2 computes `am_brief_pending` (true when Block A's
   `fetched_at` is not today). When it is true, STEP 4 should record *"my write landed as of HH:MM; `ora-am-brief`
   dispatched at <t> and has not yet written — a supersede is EXPECTED and is not a failure"* instead of the flat
   "no supersede". Zero extra cost, no new calls, and it stops the run log asserting something unobserved.
3. Have STEP 4 emit a `supersede_status` enum (`OBSERVED` · `EXPECTED_NOT_YET_OBSERVED` · `NOT_EXPECTED`) so the
   hazard can actually be counted across runs rather than inferred.
4. Accept it and document STEP 4's output as point-in-time only.

**Auto-check:** none today. Option 3 would supply one — a run-over-run count of `EXPECTED_NOT_YET_OBSERVED` is
the only way to know how often the burst inverts producer order, which is currently invisible.

**Related:** [[reference_fleet_throttle_skip_catchup_burst]] (the ordering hazard and its 2026-07-24 / 2026-08-12
recurrences), `reference_scheduler_lastrunat_stamped_at_dispatch` (why the dispatch timestamps above are the
right evidence for ordering but not for execution).

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** Commits 96a97d3 and 4ae999c (v1.2/v1.3) on origin/main; STEP 4 keys on am_brief_pending with a supersede-status log.

### OI-134
**Status:** CLOSED 2026-09-19
**Prior status:** QUEUED — approved by Gabriel in-turn 2026-08-12, **no work started**
**Opened:** 2026-08-12 (approved 2026-08-12 but unfiled here until now: the `open-items-tracker` claim slug was
held by another session, and `claim_work.py` refuses rather than clobbering)
**Source:** Gabriel's in-turn approval of option (c), alongside (a) the sweep remediation
([PR #271](https://github.com/ZeOoba/oxford-command-center/pull/271)). Full design and evidence:
[[deal-join-id-based-redesign-queued]]
**Severity:** structural, confidentiality-adjacent (Hard Invariant 3). The acute defects were remediated by
PR #271 — this is the primitive change that stops the class from regenerating.

**What to build.** Give every deal a **stable id shared by both sides** of the seed↔Notion join and retire name
normalization from the join path entirely. Candidate shape: a `Deal ID` property on the Notion Acquisition
Pipeline Tracker, mirrored as the `id` in `src/data/seed-deals.ts`, so `mergeDeals` joins on an opaque key that
no rename, locality suffix, alias, or punctuation variant can perturb.

**Why — evidence, not preference.** `dealJoinKey` (`server/sources/deal-name.ts`) strips a `" — City, ST"`
locality tail, then lowercases and collapses punctuation. Notion's suffix exists *precisely because* bare street
names repeat across metros, so the key deletes the only disambiguator. Confidentiality rides on this join: a
wrong merge folds an unmatched (fail-closed confidential) row into a public seed record.

Four adversarial passes over 2026-08-11/12 produced **9 + 7 + 5 + 6** defects, with the join subsystem
generating the worst:

| Defect | Detail |
|---|---|
| CRITICAL cross-side wrong merge | 2 lenses, executed repros — one deal's economics published under another's identity and public confidential flag |
| Alias bypass | an alias path skipped the corroboration guard entirely |
| Corroboration inert | **11 of 20 live rows** (10 map to `Other`, 1 null) — `MARKET_MAP` covers 6 metros, the pipeline spans ~10 |
| Degenerate `acceptedPairKey` | colliding names share one key, so a single acceptance grandfathers all future collisions |
| Duplicate seed join keys | one live row merged and "refused" simultaneously |

Every fix bolted on *another* corroboration signal — mapped market, then the locality tail, then literal
equality. That is the signature of a wrong primitive. Three defects shared one shape: a guard stated over a
**mechanism** rather than the **invariant**, which keeps recurring because "same deal" has no ground truth in a name.

**How to apply.**
- Read PR #271's commit bodies first — they record what each guard defends and why, so the redesign preserves
  the invariants instead of rediscovering them.
- Migration must be **fail-closed**: an unmatched row keeps defaulting confidential (Hard Invariant 3), and a
  missing or duplicate id must **refuse** rather than fall back to name matching — otherwise the old class
  returns through the back door.
- Retiring name joining should also retire `NOTION_DEALS_NAME_ALIASES`, `NOTION_DEALS_ACCEPTED_NEAR_DUPES`, and
  `findNearDuplicateNames`' gate-blocking role — check each for other callers before removing.
- **Cheap interim win, independent of the redesign:** extend `MARKET_MAP` past its 6 entries to the metros
  actually in use, shrinking the uncorroborable zone from ~55% to near zero. Needs the live Notion select values.

**Related:** [OI-122](#OI-122) — filed the same day, blocked from filing by the same claim-contention mechanism;
both are cases where a guard keyed on a proxy rather than on the thing it meant to protect.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** oxford-command-center #273 (6e7c5bd) on main; joins on notionDealId, dealJoinKey now only a detection-only migration tripwire.

### OI-137
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN
**Opened:** 2026-08-12
**Source:** surfaced as a control run while verifying [PR #268](https://github.com/ZeOoba/oxford-command-center/pull/268)'s test failures were pre-existing; re-confirmed against `origin/main` at `c5db68c`
**Severity:** MEDIUM-HIGH (Spine A and Spine B materially disagree on NOI for 3 owned properties; NOI feeds valuation, DSCR and the capital-allocation surface)
**Description:** `npm run reconcile:noi-crosscheck` FAILS on `main`: 14 properties checked, **3 errors,
4 warnings**. All three errors are the same shape — the workbook NOI vastly exceeds the warehouse
`oxfordNoi`:
| Property | Workbook NOI | Warehouse oxfordNoi | Drift | Delta |
|---|---|---|---|---|
| 3875-3883 E Livingston Ave, Columbus OH | $98,550 | $8,638 | 91.23% | $89,912 |
| 3034 Westerville Rd, Columbus OH | $117,660 | $29,387 | 75.02% | $88,273 |
| 9620 E State Route 350, Raytown MO | $108,438 | $27,614 | 74.53% | $80,824 |

Combined NOI disagreement across the three: **$259,009**. Not a test flake — reproduced on two
separate runs hours apart, on an unmodified clean checkout, at two different `main` commits.
**Why nobody has noticed:** `npm run gate` includes `reconcile:noi-crosscheck`, but **`gate:ci`
does not** (`gate:ci` = typecheck, lint, check:dev-css, test, reconcile:snapshot, build,
check:bundle). So the LOCAL Done-bar gate has been red on `main` while every PR's CI gate goes
green — including PR #268's, which passed CI the same day this was failing. Any session that runs
the full local gate hits this and may wrongly attribute it to their own branch.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** 680018f (structural-mismatch status) and #285 on main. The gate:ci exclusion is by design, tracked as OI-254. Live cross-check not re-run.

### OI-140
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN
**Opened:** 2026-08-12
**Severity:** MEDIUM
**Source:** Hit live 2026-08-12 while verifying the [OI-136](#OI-136) filing had committed intact. A
`git show HEAD:open-items-tracker.md` extract was checked with this tool; it reported an
`ORPHANED_SECTION OI-137` that does **not** exist in that extract (confirmed: 0 rows, 0 sections for OI-137 in
HEAD) but does exist in the live working tree. The tool had silently answered about a different file.
**Description:** `maintenance/check-open-items-duplicate-ids.py` accepts a path argument on the command line
and **discards it**. `main()` (line 180) does:

    path = tracker_path()          # -> TRACKER_PATH_OVERRIDE or DEFAULT_TRACKER_PATH

`sys.argv` appears **zero times** in the 197-line file — no `argparse`, no positional handling, no error on an
unexpected argument. `TRACKER_PATH_OVERRIDE` (line 73) is documented "test seam only" and is settable only by
importing the module and assigning the attribute, never from a shell.

**Why it reads as a working feature rather than an unimplemented one.** Three signals actively suggest the
argument was honoured:
1. Every report prints the file it checked — but that is `path` from the default, not your argument, and the
   two are easy to conflate when the default is the file you usually mean.
2. There is a fully-formed read-failure branch: `COULD NOT READ %s (%s) -- treat as a check failure, not a
   clean result.` It is **unreachable from the CLI**. Passing a nonexistent path returns a normal, clean,
   canonical report — verified: `check-open-items-duplicate-ids.py <path-that-does-not-exist>` exits with the
   canonical file's verdict.
3. It never rejects the argument, so there is no feedback that it was ignored.

**Why the tests do not catch it.** `maintenance/_tests/test_check_open_items_duplicate_ids.py` covers
`main()`'s file-read path — including the missing-file case — by assigning `codc.TRACKER_PATH_OVERRIDE`
directly (lines ~154-181). That is a module attribute, not the command line. The result is a suite that
genuinely exercises the read logic while leaving the **entry point** untested, so the seam that makes the code
testable is also what conceals that the CLI never reaches it. Worth generalising: a `*_OVERRIDE` test seam
tests the function, never the invocation.

**Blast radius is narrower than it looks — record this so nobody over-fixes.** The production caller,
`ora-weekly-hygiene` Block N, invokes the script with **no argument at all**, so the scheduled weekly check has
always been correct and is unaffected. The harm is confined to ad-hoc/interactive use: validating a worktree
copy, a candidate edit, a `git show HEAD:` extract, or a PR branch's version. In those cases the tool returns a
verdict about an artifact the caller did not name, in **both** directions:
- **False FAIL** — your copy is blamed for a defect that exists only in the live tracker (the case that
  surfaced this; live had a half-filed OI-137 from another session).
- **False PASS** — your genuinely broken copy reports clean because the live tracker happens to be clean. This
  is the dangerous direction, and on a shared checkout with a dozen sessions editing this file, the live
  tracker's state is effectively random with respect to your edit.

This is [[feedback_verified_null_vs_inferred_null]] in a verification tool: a result that looks verified but is
an answer to a question you did not ask. Any session that "confirmed" a tracker copy with this tool has an
unverified copy.

**Candidate fixes (not yet chosen, smallest first):**
- Reject unexpected arguments — two lines, and it converts a silent wrong answer into a loud one. This alone
  removes the hazard even if no path support is ever added.
- Or accept a real positional path (`argparse`, defaulting to the canonical tracker) and add ONE test that
  drives the script through `subprocess` rather than the attribute seam, so the entry point is covered.
- Whichever is chosen, keep `TRACKER_PATH_OVERRIDE` — the seam is fine; the gap is that nothing tests argv.
**Auto-check:** none. Detection today is manual and accidental.
**Related:** [OI-136](#OI-136) (filed in the same session; this defect surfaced while verifying it),
[[feedback_verified_null_vs_inferred_null]], [[feedback_absence_claims_need_verification_before_building]].
**Escalation evidence, 2026-08-12 — five same-day override tokens (the severity signal this item asked to
track).** Filed as OI-135 (allocator-assigned) before checking for a duplicate; folded in here instead of
landing as its own tracker entry, since it is the same gate/class OI-119 already covers and OI-129 explicitly
warns not to re-split. `OI-127` (allocated by session `e0f8485e`, reservation log only, no tracker entry filed
yet) looks like the same near-duplicate — whoever lands it should fold it in here too rather than opening a
third entry.

| Time (local) | Session | Failing test(s) | Push contents |
|---|---|---|---|
| 16:32:04 | `d37e22c1` | `test-eos-review-gate.py`, exit 124 | `feat/model-canary-probe-step25` |
| 16:38:29 | `b0e10e03` | `test-eos-review-gate.py` + 7 siblings, exit 124 | ora-deal-sourcing-scan STEP 5B + ora-deal-aging-sla STEP 3e |
| 16:38:47 | `e0f8485e` | `test-eos-review-gate.py`, exit 124 | `46cf1e2` — doc-only SKILL.md rationale correction, zero blast-radius files |
| 17:03:00 | `e89ddd24` | same gate | health-guard threshold fix + OI-098 tracker-structure merge |
| 17:19:23 | `e89ddd24` | same gate, second push | (as above, retry) |

All five: `exit 124` TIMEOUT, never an assertion — standalone reruns pass clean in 145s–5m08s against the
gate's 180s per-test budget, and every one needed a Gabriel-authorized `allow-hook-test-failure` override to
land. Source: `event_log.md` commit `75ab0de` (2026-08-12). Five tokens against this gate in under an hour,
under 12–16+ concurrent sessions — reinforces **option 1 / 1b** over the per-test options 2/3, since the
failing test varies by run (plain `test-eos-review-gate.py` alone in three of five, seven further siblings
in the fourth) — a budget-vs-load mismatch across the whole suite, not one flaky test.

**Sixth token, and the first IDLE measurement — one file is over budget with zero contention (2026-08-12,
session `e23f4c54`).** `OI-144` was allocator-assigned for this before I read the item; folded in here rather
than filed separately, per OI-129 and the OI-135/OI-127 precedent two paragraphs up. The id stays reserved and
unused.

| Time (local) | Session | Failing test | Push contents |
|---|---|---|---|
| ~19:5x | `e23f4c54` | `test-memory-orphan-link-guard.py`, exit 124 after the retry | `feat/mutation-testing-harness` — two NEW test-infra files, nothing imports them |

Landed via `--no-verify` on Gabriel's explicit in-turn call ([PR #75](https://github.com/ZeOoba/ora-claude-config/pull/75)) rather than a sixth
`allow-hook-test-failure` token — worth noting for the severity tally this item tracks, since a `--no-verify`
push leaves *less* audit trail than the token it avoided: no gate record at all, versus a token with a stated
reason.

**What is new here, and why it sharpens the option-1 choice.** Every prior data point is a run *under* gate
load, framed above as budget-vs-load. This one was measured STANDALONE ON AN OTHERWISE-IDLE MACHINE:

| Measurement | Result |
|---|---|
| `test-memory-orphan-link-guard.py`, standalone, idle | **192.7s, rc=0 (PASSES)** |
| Gate budget (`PER_TEST_TIMEOUT_SECONDS`) | 90s |
| Doubled budget on the timeout retry | 180s |
| `test-mutation-lib.py` (the branch's own new suite), standalone | 2.4s |

So this file **cannot pass the gate at any concurrency** — it exceeds even the doubled retry budget with zero
load, which no amount of reducing worker count (option 1b) will fix. That does not overturn the
budget-vs-load diagnosis for the *other* failures; it adds a second, independent cause sitting underneath it:
at least one file whose idle runtime is already over the retry ceiling. Consequences for the fix:

1. Option 1's new budget must clear the slowest file's IDLE runtime with real headroom, not merely absorb
   contention. 192.7s idle means a 180s ceiling is under water before the first concurrent session starts.
   Whoever picks the number should MEASURE the slowest files idle rather than scaling the old value.
2. Option 1b (lower concurrency) is now insufficient alone, on this file's evidence.
3. A per-file cause, measured — NOT folded into the budget decision, and worth fixing on its own.
   `test-memory-orphan-link-guard.py` invokes the hook **70 times**, each a fresh `sys.executable` spawn, and
   each invocation runs its own `git` subprocesses inside `_git()` (`memory-orphan-link-guard.py:308-318`).
   192.7s / 70 = **~2.75s per invocation**, which accounts for essentially the whole runtime. My first guess
   was wrong and is recorded here so nobody re-checks it: this is NOT the OI-061 shape. That item was about
   per-call REPO CONSTRUCTION and was fixed by the shared `gitfixture` template — which this file already
   imports and uses (line 7, and one `repo_with_commit` call). The remaining cost is hook-invocation count,
   which `gitfixture` does not address. The OI-061 playbook therefore does not transfer; the analogous move
   would be amortizing the 70 spawns (batching cases into fewer hook runs, or exercising the hook in-process
   where a case does not need the subprocess boundary), which is a different piece of work and should be
   scoped as such.

**Not caused by the change that surfaced it:** the branch is `main` plus two new files that nothing imports,
and its own suite runs in 2.4s.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** check-open-items-duplicate-ids.py on main now rejects any CLI argument with exit 2.

### OI-147
**Status:** CLOSED 2026-09-19
**Prior status:** CLOSED — REJECTED 2026-08-13; nothing landed, everything reverted
**Opened:** 2026-08-13
**Source:** ECC repo intake ([external-artifact-intake](../../skills/external-artifact-intake) ruling,
Gabriel 2026-08-13)
**Severity:** n/a — closed as rejected. Recorded so the approach is not re-attempted.
**Auto-check:** none

**Do not re-attempt the quote-state-narrowing approach without reading the evidence first.** A real
recursive-descent tokenizer (`hooks/lib/shell_tokenizer.py`, adapting ECC's `gateguard-fact-force.js`
technique) was built as a downgrade-only narrowing of `ora-autonomy-gate.py` Gate 2b. It classified all
3 historical bypass commands correctly, killed 6/8 mutants (2 proven equivalent), and passed 72 tests.

**Killed in Round 1 of the mandated 3-round adversarial gauntlet** (`pr-review-toolkit:code-reviewer`,
opus), on a sandbox-verified live bypass: quoting a path operand (`cp evil.html 'oxford-site/index.html'`)
or wrapping in an interpreter (`bash -c "..."`, `eval "..."`) makes the tokenizer confidently and wrongly
classify the write as inert — because **quoting suppresses metacharacter interpretation, it does not
remove text from the command's argument vector.** That is categorically different from the quote-state
bugs rounds 1–3 (2026-07-16) found, and is not fixable by deepening the parser: it needs shell
command-semantics modelling (which command consumes which argument, and whether it writes), a strictly
larger problem. Independently found: unbounded `$()`-nesting recursion threw an uncaught `RecursionError`
that `main()` does not catch, crashing Gate 2b entirely rather than skipping the narrowing — an
attacker-triggerable disable of Hard Invariant 2's sole enforcement, strictly worse than a narrowing bug.

A 5th attempt needs a command-semantics model, not a better tokenizer.

**Related:** [[feedback_autonomy_gate_matcher_cannot_be_safely_narrowed]] (Round 4 section — full
evidence trail); [OI-148](#OI-148) (the companion intake item, which did land).

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** Section already CLOSED (REJECTED); shell_tokenizer.py does not exist on main or in the tree.

### OI-149
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN — symptom no longer reproduces as of 2026-08-16; awaiting close-out ratification
**Opened:** 2026-08-13
**Source:** hit while landing [OI-148](#OI-148), PR [#94](https://github.com/ZeOoba/ora-claude-config/pull/94)
— the pre-push gate blocked on this and was overridden (Gabriel approved in-turn)
**Severity:** LOW — pure friction. It blocked pushes indiscriminately, never allowed a bad one.
**Auto-check:** none

**Symptom, as filed 2026-08-13.** `maintenance/test-doctrine-integrity-probe.py`'s known-plugin-skill
allowlist was stale: it flagged `morning`, `register-scheduled-task` and `schedule` as unresolved when
all three are live installed `anthropic-skills` plugin skills. Because the probe gates every push, this
blocked ANY push regardless of diff content — it was hit while landing an unrelated `hooks/**` change.

**Re-check 2026-08-16 (this session, `ora-health-guard` follow-up).** The symptom is gone. Live
`maintenance/doctrine-integrity-probe.py` now resolves all three:
`morning -> (plugin-provided skill; no local skill dir)`,
`register-scheduled-task -> skill dir 'register-scheduled-task' (Code/Cowork surface)`,
`schedule -> (plugin-provided skill; no local skill dir)` — all `[OK]`, probe exit 0
("all referenced commands, local files and skills resolve"). `test-doctrine-integrity-probe.py` also
runs fully green (ALL DOCTRINE-PROBE TESTS PASS).

**Left OPEN deliberately.** The fix was not attributed to a specific commit in this pass, so what
closed it is unverified — and this session's remit was reporting, not close-out. Gabriel's call to
close. Do not re-file this as a new item; re-check the two commands above first.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** Allowlist on main (doctrine-integrity-probe.py ~L346) repopulated for morning and schedule 2026-08-14; probe not re-run. PR #99 follow-ups merged into a feature branch, reaching main by other routes.

### OI-158
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN
**Opened:** 2026-08-15
**Source:** Manual T3-5 cross-check (Gabriel-directed workflow-optimization pass), applying `ora-tenant-hubspot-reconciliation`'s existing Step 3d (DATE-MISMATCH) logic ahead of its next scheduled run (2026-09-01, 08:15 ET)
**Description:** **DATE-MISMATCH** — Sky Shield. Workbook (`portfolio.json`-derived source of record): `leaseEnd 2029-08-31`, `status Active` — the lease was renewed to a new multi-year term. HubSpot deal "Sky Shield — Lease Renewal 2026-09-30" is still `dealstage=appointmentscheduled`, `closedate=2026-09-30` — the original pre-renewal deal was never closed out to reflect the executed renewal. Same failure class as the 2026-07-16 lease-date correction (J&R/Stone Crest/Chesapeake — see [reference_hubspot_missed_lease_date_correction.md](reference_hubspot_missed_lease_date_correction.md)), different symptom: a stale open deal rather than a stale wrong date. Recommended correction (not applied — this task never writes to HubSpot itself): advance the deal to `closedwon` with `closedate` matching the executed renewal, or close it out and open a fresh renewal-tracking deal per current process. `ora-tenant-hubspot-reconciliation`'s 2026-09-01 run should independently re-surface and can formally close this.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** Live HubSpot: deal 'Sky Shield - Lease Renewal 2026-09-30' is closedwon, close date 2029-08-31, modified 2026-09-18.

### OI-159
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN
**Opened:** 2026-08-15
**Source:** Manual T3-5 cross-check (Gabriel-directed workflow-optimization pass), applying `ora-tenant-hubspot-reconciliation`'s existing Step 3d (DATE-MISMATCH) logic ahead of its next scheduled run (2026-09-01, 08:15 ET)
**Description:** **DATE-MISMATCH** — Medspeed, LLC. Workbook (`portfolio.json`-derived source of record): `leaseEnd 2029-08-31`, `status Active` — the lease was renewed to a new multi-year term. HubSpot deal "Medspeed — Lease Renewal 2026-08-31" is still `dealstage=appointmentscheduled`, `closedate=2026-08-31` — the original pre-renewal deal was never closed out. Same pattern and same recommended correction as [OI-158](#OI-158); filed as a separate item per this tracker's one-row-per-finding convention.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** Live HubSpot: deal 'Medspeed - Lease Renewal 2026-08-31' is closedwon, close date 2029-08-31.

### OI-172
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN
**Opened:** 2026-08-16
**Source:** Rev 2 fleet re-check (session 6797e01b). Reopens the follow-up left open by the 2026-08-15 T3-12 migration and re-stated in event_log.md on 2026-08-16.
**Acceptance:** `list_scheduled_tasks` run FROM A COWORK SESSION shows `ora-passed-deal-tracker` with the LAMS/Cowork `path` (`...\Documents\Claude\Scheduled\ora-passed-deal-tracker\SKILL.md`) at `enabled: false`, while the CC/MCP entry (`~\.claude\scheduled-tasks\...`) remains `enabled: true`. Verified by pasting both entries.
**Description:** **DUAL-FLEET TWIN STILL LIVE.** `ora-passed-deal-tracker` is registered on BOTH fleets at the same cron (`30 6 15 * *`). Gabriel-directed item T3-12 moved it LAMS -> CC/MCP on 2026-08-15 because the LAMS surface has no path to `scheduled-tasks/_shared/send-via-outlook.ps1`, the sole Outlook COM send path — confirmed by a live "SEND FAILURE — no COM access" surfaced by an `ora-pm-ledger` run. The CC copy is therefore the one that must SURVIVE; the LAMS copy must be disabled.

**Why this cannot be done from Code (do not retry here):** the taskId is IDENTICAL on both fleets and `list_scheduled_tasks` from CC/MCP returns CC-only entries (38 entries, zero LAMS `path`s — verified 2026-08-16). So `update_scheduled_task(taskId:"ora-passed-deal-tracker", enabled:false)` issued from Code resolves to the **CC** copy — disabling exactly the twin meant to survive and leaving the COM-less one firing silently. Requires a Cowork-session `enabled:false` toggle. **NEVER the Scheduled-sidebar delete/trash icon** — folder-destructive, and the standing warning that it can break a same-id task on the other fleet is not theoretical here, because the ids collide.

**Mitigated, not resolved:** the double-fire guard (PR #116, `c16667c`) is now LIVE in the working tree (verified 2026-08-16: 7 `block-sentinel`/`outlook-sent-probe` hits in the CC SKILL.md, landed via `90d02ae`), so the 2026-09-15 06:30 ET fire will not double-send. That removes the urgency, not the defect — the LAMS twin still runs and still cannot send.

**Correction recorded:** the Rev 2 Fleet Operations Report initially described the CC copy as "never fired — dead weight" and a retirement of the CC copy was requested on that basis. That inference was wrong: the CC copy has never fired because it was registered 2026-08-16 11:47 on a monthly cron (`nextRunAt 2026-09-15T10:34:44Z`). It is new, not dead. The artifact has been corrected.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** fleet-roster.md (generated 2026-09-14 from live registries) lists ora-passed-deal-tracker on the CC fleet only.

### OI-041
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN
**Opened:** 2026-07-31
**Source:** ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch)
**Severity:** MEDIUM (input validation / integrity)
**Description:** unvalidated request bodies written straight to the database at `server/routes/`
`budgets.ts:25`, `insurance.ts:35` and `:46`, `renewals.ts:22`, `units.ts:20` and `:28`,
`cam.ts:23-24`, `leases.ts:74` and `:98`, `tenants.ts:62`. The sibling routes (`charges`, `payments`,
`properties`, `tenants` core, `expenses`, `leases` core) already use `safeParse` correctly — so this
is an incomplete rollout, not a missing pattern. `server/lib/schemas.ts` covers 6 of 13 write routes.
**Impact:** admin-authenticated only. An admin can set columns the UI never exposes (`id`,
`created_at`) and bulk-write unbounded rows via the array body on `budgets`.
**Candidate fix (NOT applied):** extend `server/lib/schemas.ts` to the remaining routes, apply
`safeParse` uniformly, cap array bodies with `.array().max(200)`, and add a test asserting every
mutating handler parses its body.
**Auto-check:** none.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** On ora-pm origin/main every flagged route does safeParse after req.json() (budgets, insurance, renewals, units, cam, leases, tenants).

### OI-042
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN
**Opened:** 2026-07-31
**Source:** ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch)
**Severity:** MEDIUM (information disclosure)
**Description:** the error-handler middleware's sanitization covers only *thrown* errors; every site
listed above *returns* the raw PostgREST/Postgres message from a Supabase result object instead. The
middleware's own comment therefore overstates the guarantee, which is the part most likely to mislead
a future reviewer.
**Impact:** discloses table names, column names, constraint names and RLS policy names to any
authenticated tenant — a free schema map for anyone probing for a missed authorization check.
**Candidate fix (NOT applied):** log server-side, return generic text
(`console.error('[ORA PM] portal/charges', error); return c.json({error:'Unable to load charges'},500)`).
Reserve specific messages for 4xx validation responses the caller can act on. Correct the
error-handler comment so it describes what it actually covers.
**Auto-check:** none.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** Portal and route sites return 'DB error'; OI-063 sweep merged. Two error.message leaks remain at cron.ts:690-691, reachable with the cron secret only, not by tenants.

### OI-064
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN
**Opened:** 2026-08-03
**Source:** REFUTE pass on the [OI-035](#OI-035) fix (security-auditor dispatch), 2026-08-03; verified directly by the Code-surface session that merged it
**Severity:** LOW-MEDIUM (reliability/UX, not a money-safety bug — the code fails safe)
**Description:** `src/portal/pages/PortalPayNow.tsx:74-108` + `server/routes/stripe.ts:155-171`. The
commit that fixed OI-035 claims a client retry after a network timeout "reuses the same
client_request_id ... so Stripe returns the original PaymentIntent." That's not what actually happens
for THIS flow: every Pay-button click re-runs the full bank-account linking sequence
(`createSetupIntent` → `collectBankAccountForSetup` → `confirmUsBankAccountSetup`) before reusing
`clientRequestIdRef.current`, which produces a new `payment_method_id` each time. Stripe's idempotency
layer rejects a reused key paired with different request params as an `IdempotencyError`, which is a
`Stripe.errors.StripeError` subclass and gets caught generically and returned as a plain 400 — so no
double charge occurs, but the retry doesn't dedupe/recover either. Net effect: if attempt 1 actually
succeeded server-side but the client never saw the response (pure network drop), the tenant sees
"payment failed" for a payment that went through, and may reasonably try to pay again through a
different channel (mailing a check) — an operational double-payment, just not a code-level one.
**Test gap (PARTIALLY CLOSED 2026-08-03, `ora-pm` commit `607cf13`):** the regex was unanchored enough
that it would still pass even if the reset logic were deleted. Retroactively found a pre-existing fix
for this on the source branch (`fded57c`, authored between the OI-035 and OI-036 fixes but missed by
the original OI-035 cherry-pick) and brought it over: the regex now requires the reset to immediately
precede `setStep('done')`, verified by deleting the reset line and confirming the test now fails. This
closes the test-anchoring gap specifically — it does NOT touch the underlying retry-recovery behavior
below, which is still real and still open.
**Candidate fix (NOT applied):** either redesign the retry path to not require re-linking the bank
account (persist the first attempt's `payment_method_id` client-side and reuse it on retry, so the
idempotency key AND params both match), or catch the specific `IdempotencyError` server-side and
surface a clearer "check your payment history before retrying" message instead of a generic 400.
**Auto-check:** none.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** ora-pm PR #39 (fix/oi-064-paynow-retry-idempotency) merged; stripe.ts has a resume path with an idempotency window.

### OI-065
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN
**Opened:** 2026-08-03
**Source:** REFUTE pass on the [OI-035](#OI-035) fix (security-auditor dispatch), 2026-08-03
**Severity:** LOW-MEDIUM (financial edge case — requires the tenant's own concurrent action, not a third-party attack)
**Description:** `server/routes/stripe.ts:139-148`. No transactional lock or row lock around the
`ar_ledger.balance` read and the subsequent PaymentIntent creation. Two genuinely distinct requests
(e.g. two open browser tabs, or a fast double-submit that bypasses the client's
`disabled={step==='processing'}` guard via a direct API call) each get their own valid
`client_request_id`, each read the same stale balance, and each create a fully separate, individually
idempotent-and-legitimate PI. The `payments_stripe_pi_uniq` index doesn't catch this — the PI ids
genuinely differ. Outside OI-035/OI-040's original stated scope (which covered retry-dedup and the
absolute/balance ceiling per-request, not cross-request concurrency), but directly adjacent to both.
**Candidate fix (NOT applied):** a Postgres advisory lock or `SELECT ... FOR UPDATE` on the lease's
outstanding-balance row for the duration of the check-then-create sequence; or a lightweight
per-lease mutex (Durable Object) around the whole handler, similar to what OI-038's shared-state
rate-limiting redesign would need anyway.
**Auto-check:** none.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** ora-pm PR #41 merged; stripe.ts uses reserve_payment_intent RPC under pg_advisory_xact_lock.

### OI-082
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN
**Opened:** 2026-08-05
**Source:** ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch)
**Severity:** MEDIUM (financial data integrity)
**Description:** `supabase/migrations/0002_financial_tables.sql:26-40`,
`0011_appsec_idempotency_and_scale.sql:39-53`, insert path `server/routes/payments.ts:28-36`.
`0011` hardened `charges` with `idempotency_key TEXT UNIQUE NOT NULL` but gave `payments` only two
PARTIAL unique indexes, on `stripe_payment_intent_id` and on `(lease_id, autopay_period)`. Rows with
`method IN ('check','wire','other')` are NULL on both columns and so fall outside both indexes.
Nothing prevents a second identical row.
**Impact:** a double-submitted admin form, a retried request, or a re-run import writes a duplicate
payment; `ar_ledger`'s `payment_totals` CTE sums both and the tenant's balance silently drops by the
duplicated amount. That understated balance then propagates: `POST /api/stripe/payment-intent`'s
balance cap (`server/routes/stripe.ts:166-168`) and the autopay lifetime cap
(`server/routes/cron.ts:173-174`) both read it, so under-collection reaches automated billing. Same
class as the two AR defects already shipped in this repo (cartesian fan-out; divide-by-100) — the
read path was fixed, the write path was not. Distinct from [OI-034](#OI-034)/[OI-035](#OI-035),
which addressed Stripe-side idempotency keys rather than the manual-entry methods.
**Candidate fix (NOT applied):** mirror the `charges` treatment —
`ALTER TABLE payments ADD COLUMN idempotency_key TEXT;`, backfill `'legacy:' || id::text`,
`SET NOT NULL`, `CREATE UNIQUE INDEX payments_idempotency_key_uniq ON payments(idempotency_key);` —
and default it in `server/routes/payments.ts` the way `charges.ts:35` does. Run 0011's pre-flight
equivalent first (`SELECT lease_id, payment_date, amount, method, count(*) ... HAVING count(*)>1`):
existing duplicates are a live-data finding in their own right, not a migration obstacle to code
around.
**Auto-check:** none.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** ora-pm PR #38 merged; migration 0015_payments_idempotency_key.sql adds payments_idempotency_key_uniq. Production application not separately confirmed; db-migrate runs of 09-17/18 succeeded.

### OI-224

**Status:** CLOSED 2026-09-19
**Prior status:** OPEN
**Opened:** 2026-09-02 · **Source:** `ora-appsec-sweep` 2026-09-02 (ora-pm @ `ca62ecbed3aff0a1d21585dcf40f62d823810296`, security-auditor dispatch)
**Severity:** MEDIUM (money-state correctness — ledger/display divergence)

**Description:** `server/lib/schemas.ts:74-81`'s `PaymentInsertSchema` allows `method:'ach_stripe'` with no `stripe_status` field, even though `server/routes/payments.ts:28-36`'s own code comment says this admin manual-entry route is for `check`/`wire`/`other` only. A row inserted this way has `stripe_status` NULL, so `ar_ledger` (which sums only `stripe_status='succeeded'` ACH rows) excludes it from the tenant's balance — while `GET /api/payments` and the admin PaymentsList display it as a recorded payment. There is also no unique constraint on manual payments (`check_number` isn't even in the schema), so the same check can be entered twice.

**Impact:** Admin-visible "paid" rows that don't reduce the tenant's actual balance (the exact display/ledger divergence class in this repo's defect history), or duplicate manual entries that double-credit a tenant. Related but distinct from [OI-082](#OI-082), which is about missing uniqueness on non-Stripe payments causing double-COUNTING (understated balance) — this is a schema gap allowing an uncounted-but-displayed row (the opposite-direction bug), on the same route.

**Candidate fix (NOT applied):** restrict `PaymentInsertSchema.method` to `['check','wire','other']`; add `check_number` to the schema; add a partial unique index, e.g. `(lease_id, payment_date, amount, check_number) WHERE method IN ('check','wire','other')`.

**Auto-check:** none.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** origin/main server/lib/schemas.ts has method: z.enum(['check','wire','other']); ach_stripe not accepted.

### OI-225

**Status:** CLOSED 2026-09-19
**Prior status:** OPEN
**Opened:** 2026-09-02 · **Source:** `ora-appsec-sweep` 2026-09-02 (oxford-command-center @ `d30d71ea78f98ebfc1deee4ee6847672baca78d2`, security-auditor dispatch)
**Severity:** MEDIUM (OWASP LLM02 sensitive-information disclosure / Invariant 3 egress)

**Description:** `server/ai/tools.ts:251-269` (`get_alerts` → `evaluateConditions`) and `:238-249` (`get_relationships`) do not filter out confidential deals the way `get_deals`/`search_entities` do — `src/analytics/conditions.ts:786-814` generates deal-insight alerts (LOI/PSA deadlines, next-actions) named for every deal with no `confidential` check, and `get_relationships` returns counterparties/emails tied to confidential deals too. `server/ai/agent.ts:249` then appends tool results verbatim into the outbound `messages` array with no pre-send scan — unlike `server/ai/comps.ts:26-29`, `server/warehouse/om-extract.ts:90-106`, and `server/ai/narrative.ts:118-123,252-254`, which all fail closed on the same Anthropic-API egress. The Pages-mirror path (`functions/api/ai.ts`) runs the identical agent against a snapshot deliberately baked WITH confidential data (`MIRROR_INCLUDE_CONFIDENTIAL=1`), so it inherits the same gap.

**Impact:** A question like "what's at risk right now?" against a confidential deal in an alert-eligible stage (e.g. LOI/PSA within `loiDeadlineWarnDays`) sends that deal's name and free-text `nextAction`/detail to api.anthropic.com. 16 of 22 deals in the committed snapshot are `confidential:true` at this SHA.

**Candidate fix (NOT applied):** share one `redactConfidential()` function (the bake pipeline's `scripts/bake-mirror.ts:78` already has the right shape) between the bake, the agent, and the mirror Function, and/or run `server/briefing/confidential.ts`'s `scanForConfidential` over each tool_result before it's pushed into `messages`, dropping/nulling hits — matching the belt-and-suspenders pattern the other three egress points already use.

**Auto-check:** none.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** origin/main server/ai/tools.ts has confidentialScope keyed on the confidential flag; agent.ts has a pre-send scan tagged OI-225.

### OI-228

**Status:** CLOSED 2026-09-19
**Prior status:** CLOSED 2026-09-08
**Opened:** 2026-09-02 · **Source:** `ora-appsec-sweep` 2026-09-02, DISPATCH INTEGRITY GATE assertion 4 (post-hoc model-floor probe, mandatory per SKILL.md v1.5+)
**Severity:** LOW (tooling false-positive, not a real floor breach)

**Description:** `~/.claude/maintenance/check-dispatch-model-floor.py --floor claude-opus-4-8` exited 1 ("FAIL — below-floor model") against both of this sweep's subagent transcripts. Root cause: its `MODEL_RANK` table recognizes only `claude-mythos-5` and `claude-fable-5` (rank 100) — it has no entry for `claude-fable-5-1`, the model id this session's own environment reports as the current Fable 5.1 release, so `model_rank()` falls through to `UNKNOWN_RANK = -1` (fail-closed by design for genuinely unplaceable ids) and reads a valid top-tier model as a violation.

**Verified directly** (not just inferred from the probe's summary line): `agent-ae4ff02601b0e1cdb.jsonl` (ora-pm dispatch, 62 assistant messages) and `agent-ae7f6e4c49d408b89.jsonl` (oxford-command-center dispatch, 110 assistant messages) both show `message.model:"claude-fable-5-1"` on every single line, with **zero** `"type":"fallback"` events in either transcript. Both dispatches ran entirely on Fable for their full duration — the best possible outcome under Gabriel's ratified Option C (2026-07-24), not a degradation.

**Distinct from [OI-052](#OI-052).** OI-052 documents a real, repeatedly-observed mid-run fallback pattern (`claude-fable-5` → `claude-opus-5`/`claude-opus-4-8`), ruled compliant 2026-08-14 because Opus is still top-tier. This item is a different mechanism entirely: no fallback occurred; the probe's own lookup table is stale.

**Per the sweep's own doctrine, this had to be recorded and escalated regardless of diagnosis** ("Do NOT 'fix' a firing by loosening the floor below Opus or deleting the assertion") — see the completion report / escalation email for the mandatory MODEL-FLOOR BREACH notice. The actual fix belongs in the probe script, not the floor logic: add `claude-fable-5-1` (and, proactively, `claude-mythos-5-1`) to `MODEL_RANK` at rank 100.

**Candidate fix (NOT applied):** `~/.claude/maintenance/check-dispatch-model-floor.py` — add `"claude-fable-5-1": 100` and `"claude-mythos-5-1": 100` to `MODEL_RANK`. Out of scope for this report-only task to apply (the file lives outside both audited repos and this task's writes are limited to Notion/tracker/scratch/worktrees).

**Closed 2026-09-08.** Applied in two parts: `claude-fable-5-1` landed incidentally in [PR #176](https://github.com/ZeOoba/ora-claude-config/pull/176) (the `REVIEWER_MODEL_LADDER` staleness fix that surfaced this item's twin gap); `claude-mythos-5-1` — the half this item explicitly called for and #176 missed — landed in [PR #177](https://github.com/ZeOoba/ora-claude-config/pull/177), independently reviewed (Opus), with a regression test asserting both 5.1-generation ids rank at the floor (`maintenance/_tests/test_check_dispatch_model_floor.py`, 45/45 assertions). **Evidence:** `model_rank("claude-fable-5-1") == 100` and `model_rank("claude-mythos-5-1") == 100`, verified directly post-merge. See also [OI-248](#OI-248), a distinct adjacent gap the same review surfaced (`REVIEWER_MODEL_LADDER` itself has no Mythos entry) — flagged, not closed by this fix.

**Auto-check:** none.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** origin/main check-dispatch-model-floor.py has commit 1b445cb adding claude-mythos-5-1; section said CLOSED 2026-09-08 (PRs #176/#177). Live ~/.claude checkout is behind origin/main.

### OI-255
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN
**Opened:** 2026-09-10
**Severity:** HIGH — the repo with the largest financial blast radius carries the weakest merge gate in the estate
**Source:** Cross-repo architecture-diagram review (Gabriel-directed, this session) — `ora-pm/package.json`, `ora-pm/.github/workflows/ci.yml`, compared against `oxford-command-center/package.json`

**Description:** `ora-pm` is the only ORA repo that moves real money: monthly billing generates charges and fires Stripe ACH autopay debits, and the delinquency cron posts late fees. Its gate, verified against `package.json` this session:

- `"lint": "tsc --noEmit"` — there is no linter configured at all; `lint` is a second name for `typecheck`, so the whole `npm run lint` step is a no-op relative to the step before it. The README states this plainly, which means it was a known shortcut, not an accident.
- No `gate`, no `check:refute`, no reconcile script of any kind exists in the scripts block.
- `.github/workflows/ci.yml` is typecheck -> test -> build -> `npx wrangler pages deploy ./dist --project-name ora-pm`, with the deploy gated only on `github.ref == 'refs/heads/main' && github.event_name == 'push'`. Every push to `main` ships to production.

`oxford-command-center`, which only reads money and never initiates a transfer, runs `eslint . --max-warnings 0` inside `gate:ci` plus a separate `refute-required` PR job that enforces a `Refute-Reviewed` commit trailer on financial-decision diffs. The protection is inversely proportional to the consequence.

The exposure is not theoretical for this file set: `server/routes/cron.ts` alone carries five rounds of subrequest-budget fixes, an `AUTOPAY_BATCH_LIMIT`, and an in-file warning that the limit is "MAX SAFE for this endpoint's subrequest budget, not conservative." That is exactly the class of constant a linter cannot catch but a refute gate is designed to force a second pair of eyes onto.

**Candidate fix:** two independent pieces, either shippable alone. (1) Add ESLint with a real config, stop aliasing `lint`, and add it to `ci.yml` before the test step. (2) Port `oxford-command-center/scripts/check-refute-required.ts` into ora-pm, scoped to `server/lib/billing.ts`, `server/routes/cron.ts`, `server/routes/stripe.ts` and `server/lib/cam.ts`, and make the `Deploy to Cloudflare Pages` step `needs:` it. Per CLAUDE.md's Engineering OS done-bar, changes to those four files should be carrying an adversarial REFUTE pass already; this makes that structural instead of remembered.

**Related:** [OI-233](#OI-233), [OI-234](#OI-234), [OI-235](#OI-235) (all ora-pm financial-path findings from `ora-appsec-sweep` runs that a standing gate would have surfaced earlier), [OI-261](#OI-261) (same repo, secret hygiene).

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** ora-pm PR #40 merged; package.json has lint (--max-warnings 0) and check:refute; ci.yml runs both ahead of deploy steps.

### OI-259
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN
**Opened:** 2026-09-10
**Severity:** MEDIUM — 216 tests guarding a concurrency-critical substrate, with nothing running them
**Source:** Cross-repo architecture-diagram review (Gabriel-directed, this session) — `AAOS/README.md` §2/§6, `ls AAOS/.github/workflows`, grep for `check-contract-drift` across the fleet

**Description:** AAOS is the filesystem task-queue and lease/lock protocol that lets a Claude Code session and a Cowork session coordinate without clobbering each other's state. Two gaps, both verified this session:

- `C:\Users\Owner\AAOS\.github\workflows` **does not exist**. There is no CI of any kind. The 216-test suite (`python -m unittest discover -s tests`, ~31 seconds) runs only when a human types it. AAOS's one documented Critical bug — two near-simultaneous direct appends to `aaos-events.ndjson` silently clobbering each other, recorded in `docs/GATE3-REVIEW.md` and fixed via the spool + `O_EXCL` drain-lock now in `_aaos_common.py` — is regression-guarded by those tests alone.
- `tools/check-contract-drift.py` is referenced by **nothing**: zero hits across `~/.claude/scheduled-tasks/**/SKILL.md` and any CI. Meanwhile `tools/publish-contracts.py` runs once a day (weekdays 09:15 ET) as the registered `ora-aaos-publish-contracts` task. The publisher is automated; the auditor written to prove the publish worked has never been wired to a trigger.

The second gap is the more interesting one, because it is the inverse of the usual failure: normally the detector runs and the fix is manual. Here the fix runs unattended and the detector is dormant, so a publish that silently half-succeeded would look identical to one that worked.

Note the repo also has no dependency manifest — `jsonschema` is the single non-stdlib import and there is no `requirements.txt`, which is the standing problem in [OI-175](#OI-175).

**Candidate fix:** one GitHub Actions workflow: `pip install jsonschema` then `python -m unittest discover -s tests -p "test_*.py"` on push and pull_request. It needs no secrets, no data access, and no self-hosted runner — this is a genuinely 20-minute change with a real safety return. Pinning `jsonschema` in a `requirements.txt` as part of the same change closes OI-175's non-durable pip fix, since the workflow gives that manifest a consumer. Separately, append `check-contract-drift.py` as a second step to the existing `ora-aaos-publish-contracts` scheduled task so publish and verify happen in one pass — an edit to that task's `SKILL.md`, not a new registration.

**Related:** [OI-175](#OI-175) (AAOS jsonschema pin — closed incidentally by this fix), [OI-257](#OI-257) (the AAOS mirror is the estate's best-behaved one; this is what is missing behind it).

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** AAOS PR #4 merged (cc8fbc6); .github/workflows/ci.yml on origin/main and check-contract-drift.py referenced in ora-aaos-publish-contracts SKILL. Green CI run not separately confirmed.

**Update 2026-10-29 (stays CLOSED):** AAOS#33 (merged 2026-10-29) adds a `contracts` job to `ci.yml`: validates agent-registry, examples and templates (`--schema` explicit), publishes to `runner.temp`, runs `check-contract-drift.py`. Verified locally on Python 3.11 and 3.13; the 3.10 leg and any GitHub run are unverified (hosted jobs are not starting: [OI-368](#OI-368)). It proves the publish/audit round trip on that commit, not the live seam. Treat the drift wiring as unproven until the first green GitHub run; reopen if that run fails.

### OI-263
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN — blocks [OI-259](#OI-259)
**Opened:** 2026-09-10
**Severity:** MEDIUM — nine tests that appear to guard the write-scope check actually assert a directory layout
**Source:** Surfaced by [OI-259](#OI-259)'s CI workflow on its first run — [ZeOoba/AAOS PR #4](https://github.com/ZeOoba/AAOS/pull/4), Actions run 34514715973, both matrix legs (3.11 and 3.13)

**Description:** AAOS's `match_write_scope()` is the "colonization guard" — it checks a handoff's artifact paths against the sending agent's declared `write_scope` in `agent-registry.json`, and it is the thing that stops one agent writing artifacts into another's territory. Nine tests exercise the positive path (an artifact that SHOULD be accepted), and all nine are coupled to one machine:

- `tests/test_queue_scripts.py:522` — `PostHandoffTestBase.setUp` does `tempfile.mkdtemp(prefix="aaos-artifacts-", dir=str(REPO_ROOT))`.
- `tests/test_queue_scripts.py:528` — `make_in_scope_artifact()` writes into that directory and returns its absolute path.
- `agent-registry.json:18` — `claude-code`'s `write_scope` is the literal `"C:/Users/Owner/AAOS/**"`.

So "in scope" is true only while `REPO_ROOT == C:/Users/Owner/AAOS`. The helper's name asserts a property the code does not establish; it establishes it by coincidence of where the repo sits.

Verified failure on CI (identical on both legs, 9 of 226):

```
FAIL: test_posts_handoff_with_artifact_manifest (test_queue_scripts.PostHandoffHappyPathTests)
AssertionError: 1 != 0 : VALIDATION FAILED: handoff failed validation:
  ["WRITE-SCOPE VIOLATION: path '/home/runner/work/AAOS/AAOS/aaos-artifacts-py73zpen/evidence.txt'
    is outside agent 'claude-code's declared write_scope"]
```

Also failing: `test_identical_repost_is_noop_exit_0_no_reemit`, `test_write_once_conflict_exits_3`, `test_nonempty_blocker_blocks_task_and_emits_blocked`, `test_blocking_drops_lease_and_archives_live_lock`, `test_blocker_with_lost_lease_exits_4`, and three others in the same base class. Every one fails for the same single reason, and each was previously asserting a DIFFERENT exit code (0, 3, 4) — so the coupling silently converts three distinct assertions into the same validation error, masking whatever those tests were actually meant to prove.

**Why there is no cheap fix.** There is no injection seam:

- `tools/post-handoff.py:26-27` says so explicitly in its own module docstring: *"agent-registry.json — aaos.validate_obj("handoff", registry=None) loads it via aaos.load_registry(). There is no --registry override here"*.
- `tools/_aaos_common.py:268` — `def registry_path() -> Path: return REPO_ROOT / "agent-registry.json"`.

Note `tools/validate.py` DOES accept `--registry`, so the seam exists in the codebase's own idiom; it simply was never extended to `post-handoff.py`.

**Why this matters beyond CI.** Two things, independent of whether AAOS ever gets CI:
1. The nine tests provide false confidence. Nothing in the suite currently proves `match_write_scope()` accepts a genuinely in-scope path for a reason other than the repo's location.
2. It is a latent portability trap. AAOS's own `docs/MIGRATIONS.md` and the ora-claude-config `MIGRATION_RUNBOOK.md` contemplate restoring onto a fresh machine; a restore to any path other than `C:\Users\Owner\AAOS` would fail nine tests for a reason that looks like a real guard violation.

**Candidate fix (NOT applied — needs its own review, this touches the colonization guard's inputs):** add a `--registry <path>` override to `tools/post-handoff.py`, mirroring the one `tools/validate.py` already has, and have `PostHandoffTestBase.setUp` write a temp `agent-registry.json` whose `claude-code` `write_scope` is derived from `REPO_ROOT` at runtime rather than hard-coded. That makes the positive-path assertions test the matcher instead of the filesystem, and leaves the production registry untouched. Deliberately NOT chosen: rewriting `agent-registry.json` to relative scopes (it is a schema-validated contract published to the seam mirror, so changing its shape has blast radius well past the tests), and monkeypatching `aaos.registry_path` from the test base (works, but hides the missing seam rather than closing it).

**Blocking relationship:** [OI-259](#OI-259)'s CI workflow is written, verified, pushed and correct — the workflow itself is not at fault. PR #4 is held unmerged on purpose: landing a CI that is red on arrival trains everyone to ignore it, which is worse than having none. Merge PR #4 once this item is fixed.

**Related:** [OI-259](#OI-259) (the CI that surfaced this — blocked by it), [OI-175](#OI-175) (also rides on PR #4).

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** AAOS tests/test_queue_scripts.py derives the in-scope artifact under REPO_ROOT (L523-538); PR #4 merged. Green CI run not separately confirmed.

### OI-264
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN — blocks the 3.11 leg of [OI-259](#OI-259)'s CI
**Opened:** 2026-09-10
**Severity:** MEDIUM-HIGH — a contended lease can surface as data corruption rather than a clean denial
**Source:** Surfaced by [OI-259](#OI-259)'s CI workflow — [ZeOoba/AAOS PR #4](https://github.com/ZeOoba/AAOS/pull/4), run 34518125534

**Description:** AAOS's entire purpose is that two agents cannot both hold the same task. `acquire_lease()` implements that with the spec's 6-step protocol: stage the lock, exclusive-create it, settle, rescan for conflicts, fail closed on ambiguity. The exclusive-create is atomic — but the lock's JSON *content* is written as a separate step immediately after, and nothing makes create-plus-write atomic together.

A second writer arriving inside that window opens a zero-byte lock file:

```
_aaos_common.CorruptStateError: unparseable JSON at
  /tmp/aaos-test-1cp9nqfb/projects/ora-ops/locks/t-race-8.lock:
  Expecting value: line 1 column 1 (char 0)
```

and the race assertion then observes:

```
FAIL: test_genuine_race_exactly_one_acquired_never_two
  (test_aaos_common.AcquireLeaseRaceTests)
AssertionError: Lists differ: ['acquired'] != ['acquired', 'denied']
```

`tests/test_failure_injection_matrix.py::Scenario03TwoWritersRaceTests` fails alongside it, since its meta-test asserts that coverage passes.

**Evidence it is a timing window, not a platform difference.** The 3.13 leg of the SAME CI run passed while 3.11 failed. Locally it reproduced once during a full-suite run under heavy load (13 concurrent Claude sessions on the machine; that run took 193s against a 14s baseline), then passed in isolation (3.4s) and on two subsequent full runs. So the window is real and narrow, and load — not OS — decides whether it is hit. Windows is not immune; it is merely slower to lose the race.

**Why this is worse than a flaky test.** `CorruptStateError` is the exception AAOS reserves for genuinely damaged state, and `docs/OPERATIONS.md`'s runbook treats it as such. A routine contended lease — the single most expected event in the whole system — can therefore present as corruption, inviting exactly the wrong operator response (inspect/repair state) to a situation whose correct handling is "back off and retry." The protocol's own promise, per `AAOS-SPEC.md` §7, is ACQUIRED / DENIED / CONTESTED; a corruption exception is outside that contract.

It also sits on the Cowork path: `docs/COWORK-BOOTSTRAP.md` contemplates a Cowork sandbox driving these same tools, and a sandbox racing the local session is precisely the scenario the lease discipline was built for.

**Candidate fix (NOT applied — needs its own review):** correct the READER, not the writer. Making create-and-write atomic is not available: the exclusive-create IS the mutual-exclusion primitive, so it cannot be replaced by the repo's atomic write-rename (a rename would clobber a rival's lock and destroy the guarantee). The tractable change is to teach the reader that an existing-but-empty/unparseable lock encountered inside the settle window means "held by a writer mid-create" — deny or retry — while an unparseable lock encountered OUTSIDE that window still means corruption. That is a semantic change to the lease state machine and carries the Engineering OS done-bar's mandatory adversarial REFUTE pass; it is explicitly not a CI-unblocking patch.

**Explicitly rejected:** skipping the race test on POSIX, marking it `expectedFailure`, or loosening its assertion. Every one of those makes CI green by deleting the only evidence of a real defect in the system's core guarantee — the same move refused for [OI-263](#OI-263).

**Related:** [OI-259](#OI-259) (the CI that surfaced this), [OI-263](#OI-263) (the other defect the same CI surfaced), [OI-174](#OI-174) (prior load-sensitive-test flake with the same "passes in isolation, fails under load" signature — worth checking whether that one was also a real window rather than a flake).

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** AAOS acquire_lease writes a staged sidecar and links it with _exclusive_link, so the lock is never empty. Race test not re-run.

### OI-310
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN
**See:** the Closed table above — the row's own one-line cell is the full write-up; not restated here per this file's own text-lives-in-one-place rule. This stub exists only to give `open-items-tracker.md#OI-310` a working anchor.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** ora-pm PR #43 merged 2026-09-18; DELETE handler selects source, voided_at; push CI at 5e822e3 succeeded. Deferred follow-ups (atomic delete, DB-level guard) filed as a new item.

### OI-312
**Status:** CLOSED 2026-09-19
**Prior status:** OPEN
**See:** the Closed table above — the row's own one-line cell is the full write-up; not restated here per this file's own text-lives-in-one-place rule. This stub exists only to give `open-items-tracker.md#OI-312` a working anchor.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** ora-pm PRs #44 and #46 merged; ci.yml L136 runs check-migrations-applied.mjs; push CI at 664f026 and 5e822e3 succeeded.

### OI-271

**Status:** CLOSED 2026-09-19
**Prior status:** CLOSED 2026-09-11
**Opened:** 2026-09-11 · **Source:** `dirty-tree-triage` follow-up — independent review (claude-opus-5) of CLAUDE.md commit `b777625`
**Severity:** LOW (doc contradiction, no automated behavior affected — `rules.md` §2 has always been the operational-detail target, and the exit-code table itself is correct and complete)

**Description:** `rules.md` §2's own bullet on the send path (line 32: "On non-zero COM exit: retry once, then flag loudly … do NOT halt") now directly contradicts the detailed exit-code table two lines below it (line 34: "Exit 1 (usage error) / Exit 3 (stuck wizard): do NOT retry — flag immediately"). This was harmless while CLAUDE.md still inlined the same exit 1/3 split and a reader would reconcile the two; CLAUDE.md's word-budget pass (2026-09-10, ORA Automation Audit R24-4) replaced its own inline copy with a pointer straight to §2, so §2's line 32 is now the first thing a top-down reader hits and it reads as blanket "always retry once," directly opposite the very next bullet's exit 1/3 carve-out.

**Impact:** documentation-only today — no code reads line 32 as an instruction, `send-via-outlook.ps1`'s actual exit-code handling is unaffected. Risk was a future human or session reading only line 32 and retrying a stuck-wizard (exit 3) send, which the table two lines down explicitly says makes the stuck state worse.

**Evidence:** fixed and committed together with landing the settled word-budget-pass insertion itself (`rules.md` commit `607a2d0`, dirty-tree-triage/OI-249 follow-up session) — reworded line 32 to "On non-zero COM exit: see the per-code table below — not every exit code retries — and never route through Composio/Rube/Gmail regardless of exit code," removing the blanket-retry claim. Verified via `git show 607a2d0 -- rules.md`: no remaining contradiction between line 32 and the exit-code table.

**Auto-check:** none.

**Closed:** 2026-09-19
**Closure evidence (2026-09-19, batch verification against live state):** Tracker recorded CLOSED 2026-09-11 (commit 607a2d0); not re-verified.

### OI-028
**Status:** CLOSED (RESOLVED)
**Opened:** 2026-07-26
**Closed:** 2026-07-26
**Source:** `hooks/git-prepush-hook-tests-gate.py` GIT_TRACE root-cause + fix, commit `0d4b974`; repo-housekeeping follow-up session, 2026-07-26 (see [event_log.md](event_log.md) 2026-07-26)
**Description:** A live `git push` from the `~/.claude` checkout appeared to stall for well over two minutes with no visible progress, raising suspicion of a network or Git remote problem.
**Resolution:** `GIT_TRACE`/`GIT_TRACE_PERFORMANCE` on a live `git push` isolated the delay precisely: the pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran ~54 tracked test files SEQUENTIALLY, 137s wall-clock measured directly — the actual network push (`send-pack`) that ran immediately after took 0.54s. It was never the network call. Fix: `run_suite()` now dispatches to a bounded `ThreadPoolExecutor` (8 workers) instead of a for-loop, reassembling results into original discovery order regardless of completion order.
**Evidence:** TDD in an isolated worktree (`worktrees/prepush-gate-parallelize`); real-world result 137s → 38–42s across 4 measured runs, 0 failures. Mandatory adversarial REFUTE pass (hooks/** override/auth logic) via the `security-auditor` subagent found one real defect on the first draft — a new perf test asserted a wall-clock threshold while itself running as one of the ~54 concurrently-gated files on a real push, reintroducing a load-sensitive flake-block risk with no retry path — fixed per the reviewer's own suggestion (structural sweep-line max-overlap proof instead of a timing threshold); re-review returned NOT REFUTED. Landed via `git merge --ff-only` into the live `~/.claude` checkout only after Gabriel's explicit in-turn "Good to merge" confirmation (config-write-guard requires it for any hooks/** write). Tracker closed same day, commit `b0b9ffd`.
**Note:** reproduced once more later 2026-07-26 during a 21-item consolidated commit/push (pre-push gate passed clean in seconds; the push itself then took noticeably longer before `git fetch origin main` confirmed `origin/main` landed) — same standing workaround (verify landing via fetch, not client exit code) applied; not a regression of the fix itself.
**Auto-check:** none.

### OI-023
**Status:** CLOSED
**Opened:** 2026-07-21
**Closed:** 2026-07-22
**Source:** oxford-command-center `server/workbook/parse.ts:457/585/628` + `src/analytics/conditions.ts:199` (raised during the ora-pm-ledger 2026-07-21 rent-roll divergence audit)
**Description:** The Command Center portfolio snapshot wrote `meta.asOf = WORKBOOK_AS_OF` (a June-pinned config constant), so `portfolio.json` / TopBar / module "As of" badges reported `2026-06-01` while the rent-roll data was July-current (137 tenants; the workbook's own header read "As of July 17, 2026"). Latent second concern: the `?? s.meta.asOf` day-count fallback (`conditions.ts:199`, `critical-dates.ts:47`, `renewals.ts:34`, `tenants.ts:118`) would compute lease/balloon/insurance "days out" from the frozen June date (~50d skew) for any caller omitting an explicit run-date reference.
**Resolution:** PR [#231](https://github.com/ZeOoba/oxford-command-center/pull/231) (branch `fix/oi-023-snapshot-asof`, commit `d199287`, isolated worktree). `parse.ts` gained `datelineToIso()` + `sheetDataAsOf()`: `meta.asOf`/`cash.asOf`/`assumptions.asOf` now read each sheet's own cached "As of …" header — per-sheet because the Cash Balances dateline is data-derived (MAX of Cash Data dates) and legitimately differs from the rent roll's TODAY()-cached stamp. Missing dateline → fallback with a `DataQualityFlag` warn (loud, not silent). `parseTasks` monthCol deliberately stays on `WORKBOOK_AS_OF` (test-locked). Day-count audit: every production alerting path already passed an explicit run date; the one omitting caller (`brain.setTenantNote` → `tenantScorecards`, ids-only) now passes `referenceDate()` — and the fallback value itself can no longer freeze, since it tracks the workbook's dateline.
**Evidence:** TDD red→green (`tests/unit/workbook-asof.test.ts`, 9 cases: per-sheet datelines, cached-formula unwrap, loud fallback flags, monthCol isolation; red run showed `expected '2026-07-17', received '2026-06-01'`). Full `npm run gate` exit 0 in the worktree: governance + typecheck 0 (3 tsconfigs) + lint 0 + 241 files / 2,964 tests + reconcile (live workbook via the new parser) + warehouse:verify. Live parse of the real Master Workbook: `meta.asOf 2026-07-17`, `cash.asOf 2026-07-10`, 137 leases, zero degradation flags. Adversarial REFUTE run (mandated, financial-decision-adjacent): caught one real break (brain.test.ts partial config mock missing `referenceDate`) — fixed, 13/13; TODAY()-stamp timing edges documented as accepted in-code/PR. `Refute-Reviewed:` commit trailer present (repo `check:refute` gate). PR merge is Gabriel's; item scope (label decouple + fallback audit) is complete and mechanically verified.

### OI-018
**Status:** CLOSED (RESOLVED)
**Opened:** 2026-07-18
**Closed:** 2026-07-19
**Source:** ora-appsec-sweep — supervised re-run (2026-07-18); Notion Ops Hub row `3a26ecd8-9e59-81be-8060-c83b9405e987`. Re-run re-pinned oxford-command-center at `01e288d` (prior first-run row `3a26ecd8-9e59-81e4-85d4-d08d0d5d920b` pinned the older `306a67f`); net-new finding not in OI-015/016/017.
**Description:** ora-pm (pinned SHA `f47bbe0`) — HIGH broken object-level authorization (IDOR) on the
tenant-facing Stripe router `server/routes/stripe.ts`. All three routes (`POST /api/stripe/customer`,
`/setup-intent`, `/payment-intent`) apply `tenantAuthMiddleware` (authenticates the JWT, sets
`tenantUserId`) but then read `tenant_id` (and `lease_id` on `/payment-intent`) from the request BODY and
use them directly, with NO check that the resource belongs to the authenticated session. The DB client
(`server/db/client.ts` `getDb`) uses `SUPABASE_SERVICE_ROLE_KEY`, so RLS is bypassed — there is no
row-level safety net. `/api/stripe` is also in `index.ts` `ADMIN_EXEMPT`, so no admin gate either.
Impact (attacker = any authenticated portfolio tenant): `/customer` discloses/creates another tenant's
`stripe_customer_id`; `/setup-intent` returns a SetupIntent `client_secret` bound to a victim's Stripe
customer; `/payment-intent` inserts a `payments` row against an arbitrary `lease_id`, corrupting AR
ledger balances. Contrast the correct pattern already used elsewhere: `server/routes/portal.ts` derives
the tenant via `.eq('auth_user_id', userId)`, and the `/portal/autopay` handler has an explicit
"IDOR guard" (`lease.tenant_id !== tenant.id → 404`). The Stripe router is the inconsistent gap.
NOTE: this directly CONTRADICTS the prior first-run's (d)-CLEAN / "no IDOR" claim (Notion row
`3a26ecd8...`) — the prior run appears to have checked only the portal routes and missed the separate
Stripe router.
**Evidence:** RESOLVED 2026-07-19, ora-pm commit `c705531fa7f2e861199477ceb6db21ba6b57fc66` (`main`,
local — not pushed). All 3 endpoints now resolve the authenticated tenant via
`.eq('auth_user_id', tenantUserId)` and 403 a mismatched body `tenant_id` before any Stripe call/DB
write; `/payment-intent` additionally verifies `leases.tenant_id === tenant.id` (404) — exactly the
portal.ts / `/portal/autopay` convention. Router-wide `use('/*', tenantAuthMiddleware)` added. TDD
red-first (5 rejection tests returned 200 pre-fix); 7 new tests; full suite 185/185 (was 178/178),
tsc clean. Independent context-blind adversarial REFUTE pass found no runtime bypass; its 3 hardening
findings (arg-blind test mock, missing route-wiring test, body-id reuse in writes) all landed in the
same commit — regression-detection proven by temporarily reverting one guard (4 tests red).
**Auto-check:** none.

### OI-013
**Status:** CLOSED
**Opened:** 2026-07-17
**Closed:** 2026-07-17
**Source:** [reference_onedrive_business_scope.md](reference_onedrive_business_scope.md) — surfaced incidentally during the OI-014 ora-pm sweep
**Description:** An exhaustive `.git`-marker sweep of all three OneDrive roots (run for OI-014,
scoped to `ora-pm`) also turned up a live git clone at `Claude_Workspace/01_Workspace/oxford-site/.git`
inside the business OneDrive root. CLAUDE.md documents `C:\Users\Owner\oxford-site` as *the*
no-git deploy copy (`website-canonical` is the canonical repo). This second, git-tracked
`oxford-site` sitting inside OneDrive sync scope is a different location than what's documented —
is it a stray clone, an intentional second deploy copy, or leftover from an old workflow?
**Evidence:** Not a mystery — a known, already-resolved legacy artifact. `Claude_Workspace/
01_Workspace/oxford-site` is a pre-`website-canonical` standalone working directory whose `.git`
corrupted via a OneDrive sync issue (isolated to 2026-07-05, per directory mtimes). Gabriel
personally repaired and closed this out **2026-07-16 — a full day before this item was opened**;
the tracker was simply behind, not flagging a live risk. That day's work (2 commits, `git log`
confirms `8c97652` then `9095cb7`, both authored `Gabriel Goldberg <ggoldberg@oxfordra.net>`):
1. Re-initialized git from the intact working tree after confirming it byte-identical against an
   external non-OneDrive backup (`C:\Users\Owner\_archive-non-onedrive\
   oxford-site-workspace-backup-20260716`). Explicitly confirmed this checkout diverges materially
   from `website-canonical` (275 vs 648 files) — not a live parallel source, deliberately left
   unreconciled pending direction.
2. Found a leaked, live Netlify MCP deploy token hardcoded in `run-deploy.bat` during the repair.
   Fully remediated same day per `event_log.md`'s own dedicated "CLOSED" entry: purged from git
   history via a clean re-clone (twice — a forensic-archive copy initially survived the first
   pass), redacted on disk, and the actual token **rotated at Netlify** (revoked under Authorized
   Applications, MCP connector reconnected and verified live).
3. Archived all stale/superseded content into a gitignored `archive/` folder, leaving this
   checkout "a thin config shell... `website-canonical` remains the actively maintained source for
   oxfordra.net" (his own commit message).

Independently re-verified this session, not just taken on the commit messages' word: `git remote
-v` on the live checkout returns empty (no push target, can't accidentally deploy from here);
`.netlify/` directory is empty (no deploy wiring); the redacted token is not recoverable from the
live git object store (`git fsck --unreachable --no-reflogs` empty, no reflog, the commit hash the
redaction message cites doesn't resolve), the corrupted store (`.git-corrupted-20260716`, per its
own recovery-commit analysis its surviving pack held zero commit objects), or the archived
filesystem copy of `run-deploy.bat` (shows `REDACTED`, confirmed via direct grep). Nothing
outstanding — investigated and closed same session it was surfaced.
**Auto-check:** none.

### OI-012
**Status:** CLOSED
**Opened:** 2026-07-17
**Closed:** 2026-07-17
**Source:** ora-deal-command-board SKILL.md STEP 2 (raised during the 2026-07-17 board run)
**Description:** `ora-deal-command-board`'s STALLED flag keyed on Notion's system last-edited
timestamp (`Last Updated`), which both (a) conflated any edit with real deal progress and (b) froze
when deal work happened off-Notion — on 2026-07-17 the 754 Old SR 74 row false-flagged STALLED (36d)
while its PSA was in active negotiation, purely because `Last Updated` hadn't moved since 6/11.
**Already landed this session (NOT the open part):** added a `Last Activity` DATE property to the
Acquisition Pipeline Tracker (`bcfe4a03-...`, via `notion-update-data-source`); backfilled all 7 open
rows; rewrote board STEP 1/STEP 2 to read `Last Activity` with a `Last Updated` → `createdTime`
fallback chain and to tag any row still running on the fallback. **The open part:** the field is only
authoritative once the deal-touching skills stamp `Last Activity = today` when they act on a tracked
row. Update these 5 (Cowork skills — supervised single-writer pass, verify `git log`/`git status` on
`ora-skills` before editing each SKILL.md): `deal-execution` (PSA turns), `loi-generation` (LOI
sent/countered), `acquisition-underwriting` (screen/underwrite), `deal-comparison`, `owner-outreach`.
Same one-line stamp pattern each. Do NOT add the stamp to `ora-deal-command-board` itself — it is
read-only by charter; a board that stamped activity would reset its own stall clock merely by
surfacing a deal. Acceptance: a deal under active off-Notion work does not flag STALLED; a genuinely
dormant deal still flags at 30d; the board never writes `Last Activity`.
**Progress 2026-07-17 (skills pass executed):** Ground truth on which skills actually WRITE the
tracker corrected the original 5-skill list. Edited + committed the source in `ora-skills`
(authoritative repo, single-writer verified clean before start), branch `board-last-activity-stamp`,
commit `643dd9f`, additive only:
- **loi-generation** — stamps `Last Activity=today` when logging "LOI Out".
- **deal-execution** — new standing "NOTION PIPELINE STAMPING" rule covering PSA generation (WF1),
  inbound-PSA/redline review (WF2A), and closing. This was the actual 754 gap: deal-execution
  previously touched the tracker ONLY at closing, so weeks of live PSA turns never bumped the row.
- **acquisition-underwriting** — stamps when it updates an existing tracker row in-place (it
  primarily logs to the Deal Sourcing Log, not the pipeline tracker, so this is its only tracker write).
- **deal-comparison — NOT edited (scope correction):** it is read-only, never writes the tracker;
  inventing a write just to stamp would be scope creep. Dropped from the stamp list.
**Residuals (why still OPEN):** (1) **owner-outreach — RESOLVED 2026-07-17 (source recovered; needs
no stamp).** It had been orphaned (loadable as `anthropic-skills:owner-outreach` but no source in the
repo/workspace/`~/.claude`/git history). Recovered byte-exact from the live runtime store — invoking
the skill surfaced its base dir `AppData/Roaming/Claude/local-agent-mode-sessions/skills-plugin/…/skills/owner-outreach`
(the runtime IS on disk, just under a nested session path an earlier `find` missed) — and committed
to `ora-skills` (`owner-outreach/SKILL.md`, v1.0 2026-07-11, desc 1012/1024, commit `5dda2cd`).
Reading the recovered source settled the stamping question: **owner-outreach writes the Notion Owner
Outreach Queue DB (off-market first-touch), NOT the Acquisition Pipeline Tracker — so the
`Last Activity` stamp does not apply to it, same as deal-comparison.** Repo now matches the runtime,
so it was cleared from `_staging/PENDING_REIMPORT.md` (no reimport needed). **Stamping scope is thus
fully resolved:** only loi-generation / deal-execution / acquisition-underwriting write the tracker
and all three are stamped; deal-comparison and owner-outreach correctly excluded. (2) **Deployment not
complete:** the post-commit hook staged all 3 skills in `_staging/PENDING_REIMPORT.md`; going live in
the Cowork runtime needs `package_skills.py` → present `.skill` → **manual Save-skill click** (GUI,
not headless), then `pending_reimport.py clear <skill>`. Until then the Monday
`ora-skill-store-drift-check` will flag repo↔store drift. (3) ~~Branch `board-last-activity-stamp` is
committed locally, not merged to main or pushed — awaiting Gabriel's review/merge.~~ **Stale —
corrected 2026-07-17 (Code-surface verification):** `git branch -vv` on `ora-skills` shows
`board-last-activity-stamp` at `5dda2cd`, identical to `main`; `git log main..board-last-activity-stamp`
returns zero commits (fully merged); `git log origin/main..main` also returns zero commits and
`git rev-parse origin/main main` return the same SHA (`main` fully pushed). The branch is not a
residual — this note was simply stale by the time of closure. This correction itself committed to
`~/.claude` `main` (commit `8c58559`) and pushed to `origin/main` (`ora-claude-config`, verified via
`git status -sb` showing no ahead/behind and `git ls-remote origin main` matching local HEAD) —
tracker text and remote now consistent, nothing further outstanding on OI-012.
**Progress 2026-07-17 (reimport attempt, blocked):** Re-verified `_staging/PENDING_REIMPORT.md` still
listed all 3 (`acquisition-underwriting`, `deal-execution`, `loi-generation`, pending since
2026-07-17T18:17Z, commit `643dd9f`). Packaged `acquisition-underwriting.skill` successfully via
`package_skills.py` (fresh file confirmed in `_staging/out/`). Then found this machine
(LAPTOP-CSHSCBE6) has **no Claude Desktop app installed** — absent from the computer-use
`request_access` allowlist and from `AppData\Local\Programs`, `AppData\Local\AnthropicClaude`,
`Program Files`, `Program Files (x86)`, and Start Menu shortcuts. Gabriel confirmed (2026-07-17, via
AskUserQuestion): **stop here** — do not guess an alternate app name or assume the Desktop app is on
another device. `deal-execution` and `loi-generation` were NOT packaged (no point building `.skill`
files with the GUI step unreachable). All 3 remain pending; none cleared. **Open part now includes:**
locate which device/session actually hosts the Cowork Claude Desktop app's Save-skill flow before
retrying this residual.
**Closure 2026-07-17 (Cowork session, Desktop app located on the Cowork-hosting machine):**
Re-verified `_staging/PENDING_REIMPORT.md` still listed all 3 skills unchanged (pending since
2026-07-17T18:17Z, commit `643dd9f`) before starting — confirmed no other session had cleared any of
them. Packaged all 3 via `tools/package_skills.py C:\Users\Owner\ora-skills\_staging\out
<skill-name>`, each verified fresh via `get_file_info` immediately after build:
`acquisition-underwriting.skill` (50,017 bytes, 2 entries: SKILL.md + target-markets.json, built
18:42Z), `deal-execution.skill` (42-point QC gate confirmed by the packager, 1 entry: SKILL.md, built
18:45Z), `loi-generation.skill` (2,782,431 bytes, 5 entries incl. the 16-point QC gate and the
condensed LOI template, built 18:46Z). The GUI Save-skill click itself could not be performed by the
agent — computer-use's `request_access` refused control of Claude's own window outright (a hard,
non-overridable guard against an agent operating its own interface/permissions), confirming this
step is manual regardless of session type. Handed off the 3 `.skill` files and import instructions to
Gabriel; Gabriel confirmed all 3 imported ("all done"). On that confirmation, ran
`python tools/pending_reimport.py clear <skill>` for all 3 in sequence — each returned
`pending_reimport: cleared <skill>` — then re-read `_staging/PENDING_REIMPORT.md`: the file no longer
exists (the clear script deletes it once the pending list empties), the definitive zero-pending
state. Stamping scope (loi-generation/deal-execution/acquisition-underwriting) was already committed
at `643dd9f`; only the runtime-cache resync remained, and that is now closed. **Residual outside this
item's scope, not blocking closure — since resolved:** branch `board-last-activity-stamp`'s
merge-to-main-and-push status was flagged as not re-verified this session; separately confirmed later
the same session (`ora-skills` `main` HEAD `5dda2cd` == `origin/main` `5dda2cd` via `git fetch` +
`git rev-parse`) — already merged to main and already pushed, nothing outstanding.
**Auto-check:** none (not a fleet-registry item; closure evidence is the cleared
`pending_reimport.py` runs plus the deleted `PENDING_REIMPORT.md`, both reproducible by re-running
`python tools/pending_reimport.py clear <skill>` — a no-op / "already cleared" result confirms state).

### OI-011
**Status:** CLOSED
**Opened:** 2026-07-17
**Closed:** 2026-07-17
**Source:** [project_bash_guard_indirection_gap.md](project_bash_guard_indirection_gap.md)
**Description:** Found during OI-010's adversarial review, deliberately NOT fixed there to keep that
change scoped to the indirection fix. Both were pre-existing (present before OI-010 touched the
file), false-positive-only (annoyance, not a security gap at the time): (1) `git config --get
core.hooksPath` (a pure read) was denied identically to an actual write — check (d) never
distinguished read from set. (2) `cp .claude/settings.json /tmp/backup.json` (reading FROM the
guard file to back it up) was denied identically to overwriting it — the mv/cp check matched the
guard path anywhere in the segment, not just as the destination, despite its own comment saying
"as an argument (destination)".
**Evidence:** Fixed on `oxford-command-center` `main`, commit `8006a15`. Check (d) now
distinguishes mutation from read: any trailing token after `core.hooksPath`'s position counts as a
value being set (regardless of leading dash — no `--` separator required by real git) UNLESS the
command carries an explicit `--get`/`--get-all`/`--get-regexp`/`--get-urlmatch` flag, where a
trailing token is git's own value-pattern filter, not a value. `--unset`/`--add`/`--replace-all`
and the `-c core.hooksPath=` inline form still always deny. Check (g)'s mv/cp guard now treats `mv`
and `cp` differently: `mv` still denies the guard path in either argument position (source-position
mv removes/neutralizes the file, same severity as `rm`), while `cp` denies only the destination
argument via a new `cpGuardWrite()` helper covering the plain 2-arg form and all 3
`-t`/`--target-directory` shapes (short flag, `=`-attached, space-separated) plus unambiguous
long-option abbreviations. **3 rounds of adversarial review** (mandatory per CLAUDE.md for
`hooks/**` security-gate code) found and fixed 3 real bypasses before landing, each confirmed
against the live hook and then regression-tested: a dash-prefixed `core.hooksPath` value (`git
config core.hooksPath -evilhooks`) defeating the initial read/write classifier; `cp
--target-dir=.claude/hooks/ evil.mjs` (GNU abbreviation) missed by the initial destination-only
detection; `cp --target-directory .claude/hooks/ evil.mjs` (space-separated, real GNU cp behavior)
missed by the round-1 fix. Round 3 found nothing further. 68 tests in `bash-guard.test.ts` (was 64),
full project suite 231 files/2792 tests green, typecheck 0, lint 0. Landed via isolated worktree,
fast-forward merge (matching the OI-010 convention), verified zero collateral impact on the main
checkout.
**Auto-check:** none (not a fleet-registry item; closure evidence is the landed commit above,
externally verifiable via `git log`).

### OI-010
**Status:** CLOSED
**Opened:** 2026-07-17
**Closed:** 2026-07-17
**Source:** [project_bash_guard_indirection_gap.md](project_bash_guard_indirection_gap.md)
**Description:** `oxford-command-center/.claude/hooks/bash-guard.mjs` is a stateless, per-invocation
text scanner with no cross-invocation memory. A two-step disk-persisted indirection — a git alias or
a wrapper script written in step 1, invoked by name in step 2 — defeated all 7 blocked command
classes, whether the two steps were one `&&`-joined command or genuinely separate Bash tool calls.
**Evidence:** Fixed on `oxford-command-center` `main`, commit `60c45ed`. Resolves both indirection
layers into one expanded text every existing check scans: git aliases via `git config --get`
(skipping known builtins), inline `git -c alias.X=value` one-shot overrides, and script content read
through a widened set of invocation forms (sh/bash/zsh/dash/ksh, source/dot, stdin redirection,
direct execution, case-insensitive, quoted paths with spaces) with best-effort positional-parameter
and simple-variable substitution inside that content. Three rounds of independent adversarial review
(3 parallel agents, each personally re-verified) found and fixed real bugs before landing: git global
options (`-c`/`-C`/`--git-dir=`/`-p`/`--no-pager`) breaking alias-candidate detection entirely; an
exponential subprocess-spawn blowup from a plausible chained-alias config (4-8s+ stalls on every
Bash call, fixed via a 16-lookup shared budget); a backtracking-prone lazy regex costing ~10s on a
crafted unterminated-quote payload (fixed via length-bounded `{0,4096}?` matches, applied
consistently including to the pre-existing `sh -c`/`$()`/backtick extraction whose exposure this fix
increased); and a quote-handling bug where substituting a variable inside double quotes left stale
quote characters, hiding the result from the downstream commit-message quote-blanking logic. Proved
several bypasses end-to-end (not just hook-logic-level) before fixing: a git alias genuinely staged
an untracked file via `add -A`; a direct-executable and a variable-built-verb wrapper genuinely
deleted a `data/warehouse` test directory. 59 new/updated tests (regression + adversarial-finding
coverage + timing guards locking in both DoS fixes); full project suite 231 files/2783 tests green,
typecheck 0, lint 0. Landed via isolated worktree, fast-forward merge, verified zero collateral
impact on the main checkout. Accepted, documented limits (same architectural ceiling as OI-007):
arbitrary shell constructs beyond simple literal variable assignment — command substitution,
arithmetic, exported variables, control flow, >3-level nested wrappers, >64KB scripts — are not
resolved, since closing those for real needs the same shift OI-007 used (verify the actual outbound
action/repo state), not another regex. 2 unrelated pre-existing false positives found during review,
deliberately not fixed here to keep scope tight: tracked as [OI-011](#OI-011).
**Auto-check:** none (not a fleet-registry item; closure evidence is the landed commit above,
externally verifiable via `git log`).

### OI-007
**Status:** CLOSED
**Opened:** 2026-07-17
**Closed:** 2026-07-17
**Source:** [project_autonomy_gate_indirection_ceiling_followup.md](project_autonomy_gate_indirection_ceiling_followup.md)
**Description:** `ora-autonomy-gate.py`'s Gate 1 (external email) and Gate 2a (oxfordra.net prod
deploy) could be defeated entirely, no override needed, via value/reference indirection (a
variable/file-sourced recipient, a renamed netlify binary, splitting a deploy across two Bash
calls). Not fixable by another regex — needed enforcement moved to the actual outbound action.
**Evidence:** Two enforcement points built, each checking the value AFTER a shell has already
resolved any indirection, so there is no more text left to obfuscate by the time either runs:
  - **Email side** (`~/.claude`, landed on `main`): `hooks/lib/email_send_tier.py` +
    `hooks/lib/check_external_send.py`, invoked by `send-via-outlook.ps1` itself right before
    Outlook COM. Adversarial review found and fixed 3 real bugs pre-landing (a suffix-match
    domain-classification bypass, a PowerShell CLI-argument quote-stripping bug breaking the
    checked/sent value equivalence, and a BOM-encoding bug in the shared token parser). Verified
    via 6+ `-WhatIf` scenarios against the live script, including the exact indirection trick
    (variable-concatenation-built recipient) that defeated Gate 1 — now correctly denied.
  - **Netlify side** (`website-canonical`, PR [#30](https://github.com/ZeOoba/Website/pull/30),
    MERGED by Gabriel 2026-07-17 — merge commit `b25a70d9`): `scripts/netlify-guard.js` +
    `scripts/patch-netlify-shim.js` (postinstall-patches `node_modules/.bin/netlify*` to route
    through the guard). Adversarial review found and fixed 2 real bugs pre-PR (an exact-array
    argv check that let `--prod=true` and the documented `--prod-if-unlocked` flag bypass
    authorization entirely, and a postinstall patcher that silently exited 0 even when zero
    shims were patched). Verified via the wrapper's own dry-run switch across 9+ scenarios,
    including a real `npm install` proving the postinstall hook re-patches a reverted shim, and
    the same indirection trick (shim path + flag built via shell variable concatenation) —
    still caught. Post-merge, confirmed the live site (`oxfordra.net`) renders correctly and
    unaffected (the PR touches only dev tooling, no site content).
**Auto-check:** none (not a fleet-registry item; closure evidence is the merged PR + landed
commits above, both externally verifiable).

### OI-001
**Status:** CLOSED
**Opened:** 2026-07-08
**Closed:** 2026-07-16
**Source:** [oxford-cc-repo-health.md](oxford-cc-repo-health.md) — 2026-07-05 CC/MCP registry-loss recovery
**Description:** Purge 2 dangling disabled LAMS scheduled-task entries left over from the fleet-recovery near-misses.
**Evidence:** `fleet-status.py` (run 2026-07-16) — zero disabled entries anywhere in the LAMS fleet. The one fleet-wide disabled task (`check-code-audit-image-pass`) is CC/MCP, unrelated to this item. Nothing was left to purge; the entries had already been cleared by an earlier pass that never logged closure here.
**Auto-check:** kind=registry_disabled_count fleet=lams expect=0

### OI-002
**Status:** CLOSED
**Opened:** 2026-07-08
**Closed:** 2026-07-16
**Source:** [oxford-cc-repo-health.md](oxford-cc-repo-health.md) — 2026-07-05 CC/MCP registry-loss recovery
**Description:** Decide whether `ora-cam-reconciliation-annual` should run year-round or seasonally.
**Evidence:** Live LAMS registry cron for `ora-cam-reconciliation-annual` is `0 7 15 1 *` (fires once yearly, Jan 15) — confirms the seasonal decision was made and implemented; nothing further to decide.
**Auto-check:** kind=registry_field_equals fleet=lams task_id=ora-cam-reconciliation-annual field=cron expect="0 7 15 1 *" — **OBSOLETE as of 2026-08-14, do not treat a future failure as a regression.** `ora-cam-reconciliation-annual` was archived 2026-06-11 but stayed registered for 2 months before dropping from the live LAMS registry entirely on 2026-08-14; Gabriel confirmed the annual CAM-reconciliation duty obsolete and declined to re-register it (see [Automation Audit Rev 8 08-14](project_automation_audit_rev8_2026-08-14.md)). The task id no longer exists to check a `cron` field on. Kept for history, not re-run.

---
*Both entries above were discovered already-closed during the 2026-07-16/17 dead-pointer incident (the `oxford-cc-repo-health.md` → `session-context.md` chain had gone stale) rather than closed in the normal course of work — hence identical opened/closed dates and no intermediate history. See [[event_log]] 2026-07-16 for the full incident writeup.*

### OI-004
**Status:** CLOSED
**Opened:** 2026-07-16
**Closed:** 2026-07-17
**Source:** [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md)
**Description:** Add a real `Archived` property to the Notion Tenant DB schema. No native
archive/status field existed — the 2026-07-12 remediation archived rows by title-prefix
(`⛔ ARCHIVED …`) only, so all rows remained live and queryable.
**Evidence:** Added `Row Retired` CHECKBOX property via `notion-update-data-source` (`ALTER
COLUMN`). Both single-word reserved names (`Archived`, `Retired`) failed with `validation_error`
before the two-word name succeeded. Property confirmed live and in active use: 2 Heritage Pool
duplicate rows retired under OI-005 and 1 duplicate `9620 State 350` Unit 110 row retired under
OI-006, all queryable via `"Row Retired" = '__YES__'`.

### OI-003
**Status:** CLOSED
**Opened:** 2026-07-16
**Closed:** 2026-07-17
**Source:** [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md)
**Description:** Build the Notion Tenant DB workbook mirror: `EXPORT_RentRoll` (137 rows, live
formulas, join key Property+Unit) → Notion Tenant DB (172 rows), extending
`ora-master-workbook-ingest`. Spec:
`Claude_Workspace/01_Workspace/outputs/2026-07-16_TenantDB-Workbook-Mirror_Spec_v01.md`.
**Evidence:** Live pull of both sides (`export_rentroll.json`, `notion_tenants_raw.json`) joined
via a street-family bucket key (plain naive property-string normalization produced an implausible
117/148-orphan result on the first attempt — rebuilt with the family-bucket approach, see
[[reference_tenant_db_no_sync_rootcause]]). Result: 23 match, 7 workbook-newer, 0 notion-newer, 49
conflict (mostly a `date:Lease Expiration:start` NULL artifact — Notion's field genuinely empty on
most active rows, not a real mismatch), 64 workbook-only, 93 notion-only. Report posted to Notion
page `3a06ecd8-9e59-81d2-9e71-d630fcc5b448`. Per the spec's own mandate, this run was report-only —
no blind overwrite; the confirmed corrections it surfaced were executed individually under OI-005
and OI-006 once each was checked against its executed lease.

### OI-005
**Status:** CLOSED
**Opened:** 2026-07-16
**Closed:** 2026-07-17
**Source:** [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md)
**Description:** Dedup the two stale Notion `Heritage Pool Supply` rows (both dated 2026-09-30)
against the correct `SRS Distribution / Heritage Pool Supply` row (2031-09-30 — confirmed by
Gabriel 2026-07-16 and matched by the corrected Master Workbook).
**Evidence:** Correct row `32b6ecd8-9e59-8115-9c01-fe0126f3f4b7` left untouched. Two duplicate rows
(`32c6ecd8-9e59-8125-979b-cafe5e648089`, `32b6ecd8-9e59-8161-ab6b-ddc6b708e464`) set to `Row
Retired = __YES__` via `notion-update-page`, verified by fresh SQL query post-write. Separately
flagged (not part of this item's scope): Heritage Pool's `Monthly Rent` ($8,540) vs. its lease
amendment's Year-1 rate ($8,710.80/mo) — **Gabriel ratified $8,540 as correct 2026-07-17**, no
write needed. See [[ops_decision_log]].

### OI-006
**Status:** CLOSED
**Opened:** 2026-07-16
**Closed:** 2026-07-17
**Source:** [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md)
**Description:** Confirm against the executed lease (Invariant 7) before any mirror write touches
them: 4 tenant-turnover rows (Zettler 2016, 9620 State 350 #110, Morrison 390, Banwick 2814) where
Notion still named the predecessor tenant, plus the Soldier Trucking property conflict (Notion:
2018 Zettler Rd unit 301; workbook: 1100 Rarig G&H).
**Evidence:** Read all 5 primary executed lease documents via SharePoint (`read_resource`) —
Soldier Trucking original lease + Second Addendum (DocuSign-executed, Gabriel Goldberg's own
signature 2026-03-30: confirms 1100 Rarig Ave Unit G&H, $3,183/mo, term → 2026-10-31), Columbus
Diamonds Elite Cheer (2016 Zettler Rd, term 2026-05-01→2029-04-30), Triple Threat Kansas City
(9620 E State Rte 350 Unit 110, Raytown MO), Pact Containers LLC (390 Morrison Rd, term
2026-05-05→2029-04-30), AI Thomas LLC d.b.a. AIT Environmental Technology (2814 Banwick Rd, term
2026-06-01→2029-05-31). All 5 confirmed the workbook/audit's claims exactly. `9620 State 350` Unit
110 turned out to carry 2 duplicate stale Notion rows (both "Square Cow Movers/BHIL Enterprises");
handled with the same keep-one/retire-one pattern as OI-005. Wrote 6 `notion-update-page` calls
(4 turnovers + 1 property-conflict correction + 1 duplicate retirement), verified via a fresh SQL
query by page ID post-write — all 6 rows match the intended values exactly. Page IDs: Soldier
Trucking `32b6ecd8-9e59-8192-9427-c1fcc2e803f3`, Zettler 2016
`32f6ecd8-9e59-8192-8c73-f69c14122253`, Morrison 390 `32c6ecd8-9e59-8171-a432-c8a5adbba8c4`,
Banwick 2814 `32f6ecd8-9e59-8106-b4d9-f6da8fb7cec0`, State 350 #110 kept
`32b6ecd8-9e59-8105-8d7e-ea9a94b603f8` / retired `32c6ecd8-9e59-815b-9a67-da8c147292a7`. Noted, not
flagged as an error: Zettler/Morrison/Banwick all lease under landlord entity "Fairground Village
Center, LLC" at the same Potomac, MD address — a consistent multi-property holding entity, not a
data anomaly.

### OI-008
**Status:** CLOSED
**Opened:** 2026-07-17
**Closed:** 2026-07-17
**Source:** [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md)
**Description:** Sweep every live Notion Tenant DB row's `Lease Expiration` against the workbook's
`Escalation Date` column (not just `Lease End`) to find any rows beyond the 7 already checked where
the original March 2026 import miscopied the wrong workbook column.
**Evidence:** Ran a script (`sweep_escalation_bug.py`) joining every non-archived, non-retired
Notion row against `EXPORT_RentRoll` via the same street-family+unit key used throughout this
reconciliation, flagging any pair where `Notion Lease Expiration == WB Escalation Date != WB Lease
End`. This is the full reconciliable overlap (79 joined pairs — matches OI-003's original
match+workbook-newer+conflict count exactly, confirming no join coverage was lost). **Result: 4
hits, all 4 already fixed** under the OI-003–006 follow-on remediation earlier tonight (TYM
Wholesale LLC/Zettler 2006, Pedro Ulate/4595 5th Ave, SAFE CONNECTION ELECTRIC LLC/Banwick 2824,
Randy's Aquarium Service/Banwick 2804) — the sweep ran against a pre-fix data cache, which is why
they still show as hits in the script output; live Notion already carries the corrected values
(verified under OI-003–006's own evidence). **No new instances of this bug exist anywhere the
comparison is possible.** Scope boundary, not a gap in the sweep: 93 live Notion rows have no
workbook counterpart at all (family-join miss or genuinely off-workbook tenants), so this
column-mapping check cannot apply to them — verifying those 93 independently against primary lease
documents would be a much larger, separate undertaking, not implied by this item's description.

### OI-014
**Status:** CLOSED
**Opened:** 2026-07-17
**Closed:** 2026-07-17
**Source:** [reference_onedrive_business_scope.md](reference_onedrive_business_scope.md) — migration Phase B4 unsynced-export check
**Description:** Confirm no `ora-pm` git clone lives inside OneDrive sync scope (business root,
its `(1)`-suffixed twin, and the plain personal OneDrive root) — superseding an earlier depth-4-only
Glob negative, which per [[feedback_verify_negative_glob_results]] isn't sufficient proof on its own.
**Evidence:** Exhaustive `.git`-marker search, no depth cap, hidden entries included, across all
three OneDrive roots, via two independently-implemented tools (Bash `find -name .git`, PowerShell
`Get-ChildItem -Recurse -Force -Filter .git`) — both agreed exactly: zero `ora-pm` hits anywhere.
Two unrelated `.git` markers turned up (an already-archived third ora-skills clone at
`Claude_Workspace/01_Workspace/_archive/2026-07-09_third-ora-skills-clone/skills/.git`, expected
and already resolved; and a **live** `oxford-site` clone at
`Claude_Workspace/01_Workspace/oxford-site/.git`, distinct from the documented no-git deploy copy
at `C:\Users\Owner\oxford-site` — flagged separately, out of this item's ora-pm scope, tracked as
[OI-013](#OI-013)). `Claude_Workspace/00_Governance/Scheduled/ora-pm-ledger`
confirmed NOT a repo (task folder only, no `.git`). Real `ora-pm` repo confirmed live at
`C:\Users\Owner\ora-pm`.
**Auto-check:** none (not a fleet-registry item).

### OI-080
**Status:** CLOSED 2026-08-28 (row flipped; fix landed 2026-08-17 via ora-pm PR #23, re-verified this session: `shouldCreateUser: false` confirmed live in `src/portal/pages/PortalLogin.tsx`, CI run for the merge completed SUCCESS 2026-08-17)
**Opened:** 2026-08-05
**Source:** ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch)
**Severity:** HIGH (authorization / self-provisioning)
**Description:** `src/portal/pages/PortalLogin.tsx:12-15` calls
`portalSupabase.auth.signInWithOtp({ email, options: { emailRedirectTo } })` with no
`shouldCreateUser: false`. That option defaults to **true**, so any email submitted at
`/portal/login` creates a Supabase auth user in the same project that serves admins.
**Why this is not covered by [OI-036](#OI-036):** that item's fix added the flag to the ADMIN login
only. Verified this run by reading both files side by side — `src/pages/auth/AdminLogin.tsx:22` has
`shouldCreateUser: false` with an explicit "OI-036" comment above it; the portal login has no such
option at all. Two login pages, one fixed.
**Impact:** three effects. (1) An attacker self-registers, completes the magic link, and holds a
valid `authenticated` JWT — the credential that turns [OI-078](#OI-078)/[OI-079](#OI-079) from
anon-key-reachable into authenticated-role-reachable, surviving anon-only hardening. (2)
Pre-registering a known tenant contact address (broker and tenant emails are discoverable) makes
`admin.auth.admin.inviteUserByEmail` (`server/routes/portal-auth.ts:38-41`) fail on an
already-registered email, blocking that tenant's onboarding until someone reconciles the auth user
by hand. (3) Unbounded auth-table pollution and ORA-branded magic-link mail to arbitrary addresses.
`tenantAuthMiddleware` (`server/middleware/tenant-auth.ts:21-25`) accepts the JWT as valid; the API
then 404s at the `tenants` lookup, but the JWT remains fully valid for direct PostgREST and Storage.
**Candidate fix (NOT applied):** mirror the admin fix exactly —
`options: { emailRedirectTo: window.location.origin + '/portal', shouldCreateUser: false }`. Tenants
are provisioned only via `POST /api/admin/tenants/:id/invite`, so this is the correct posture. Add a
portal-login test alongside `tests/components/admin-login-shouldcreateuser.test.ts`; that test
existing for one of two login pages is itself the signal this was missed.
**Auto-check:** none.

### OI-081
**Status:** CLOSED 2026-08-28 (row flipped; fix landed 2026-08-17 via ora-pm PR #23, re-verified this session: `aal-guard.ts`'s OI-081 fix confirmed live -- blocks outright on `currentLevel !== 'aal2'` -- CI run for the merge completed SUCCESS 2026-08-17)
**Opened:** 2026-08-05
**Source:** ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch)
**Severity:** HIGH (money-movement control weaker than documented)
**Description:** `server/middleware/aal-guard.ts:46-48` blocks only when
`data.nextLevel === 'aal2' && data.currentLevel !== 'aal2'` (verified verbatim this run). Supabase
raises `nextLevel` to `aal2` only when the user has a **verified factor**; for a tenant who never
enrolled, `nextLevel` stays `aal1` and the guard calls `next()` unconditionally. MFA enrollment is a
voluntary action on the account page (`src/portal/pages/PortalAccount.tsx:90`) and nothing in the
portal requires it. The code comment states this honestly — the gap is that the surrounding OI-045
remediation reads as though AAL2 is the control protecting ACH.
**Impact:** for any tenant without an enrolled factor — realistically most of them — the only thing
between an attacker and an ACH debit is possession of a magic-link session: a forwarded or leaked
sign-in email, a shared AP mailbox (common at industrial tenants), or an XSS chain via the
still-Report-Only CSP ([OI-066](#OI-066)). `POST /api/stripe/setup-intent` then
`POST /api/stripe/payment-intent` (`confirm: true`) moves real money up to
min(outstanding balance, $50,000).
**Relationship to [OI-045](#OI-045):** that closure is not wrong — `requireAal2` is a real
server-side check, it does fail closed on error, and it is wired onto all three sensitive routes,
all re-confirmed here. This item narrows what it actually buys: the gate is only as strong as
enrollment, and enrollment is optional. Read the two together.
**Candidate fix (NOT applied):** either (a) require MFA enrollment before the Pay Now / autopay
surfaces are reachable — 403 with "enroll MFA to authorize bank payments" on `setup-intent`,
`payment-intent` and `PATCH /autopay` whenever `nextLevel !== 'aal2'` — or (b) if enrollment cannot
be mandated, add a step-up email/OTP confirmation on first bank-account attach and on any payment
over a threshold. Either way, correct `aal-guard.ts`'s header comment, which currently overstates
the protection.
**Auto-check:** none.

### OI-087
**Status:** RESOLVED 2026-08-12 (both hono PRs merged — moved to the Closed table)
**Opened:** 2026-08-05
**Source:** ora-appsec-sweep 2026-08-05 (both repos, security-auditor dispatch)
**Severity:** MEDIUM (dependency CVE, both repos)
**Resolution:** `hono` raised to `^4.12.34` (lockfile 4.13.1) in both repos, clearing GHSA-8j4g-w8fx-2239 (and 3 other `<4.12.34` hono advisories in occ). PRs merged 2026-08-12: ora-pm [#21](https://github.com/ZeOoba/ora-pm/pull/21) squash `caa5849`, oxford-command-center [#270](https://github.com/ZeOoba/oxford-command-center/pull/270) squash `4187b78`. Verified pre-merge in each: hono cleared from `npm audit`, typecheck 0, lint 0, tests green (ora-pm 427; occ 3354); occ CI gate + refute-required + CodeRabbit green. Floor raised in package.json (not just the lockfile) so a reinstall can't regress. Pre-existing dev-only advisories (nanoid on ora-pm; react-router/sharp/etc. on occ) remain [OI-017](#OI-017)'s, untouched here.
**Description:** GHSA-8j4g-w8fx-2239 — ReDoS in Hono's CORS middleware via the
`Access-Control-Request-Headers` header, affecting `hono <4.12.34`. Present in both production
codebases, versions read directly from the lockfiles this run: `ora-pm` @ `a29f8f0` resolves `hono`
**4.12.31**; `oxford-command-center` @ `175e3f9` resolves **4.12.28**. Both are runtime dependencies
on served paths — ora-pm mounts `cors()` on `/api/*` (`server/index.ts:71-76`), occ on `/api/*` of
the Brain Server (`server/index.ts:52`) — and CORS preflight is evaluated before any auth or origin
rejection, so the vulnerable code is reachable pre-authentication in both.
**Impact:** CPU exhaustion from crafted preflight headers. On ora-pm, Worker isolate CPU limits
convert this into request failures and billing impact; on occ it hangs the event loop of the process
holding the confidential warehouse. Unauthenticated and trivially scriptable in both.
**Why this is not already tracked:** it is NOT the advisory closed by ora-pm's earlier
4.12.23 -> 4.12.31 bump (that one was satisfied at 4.12.31; this one is not), and core `hono` is not
in [OI-017](#OI-017)'s tracked set, which covers react-router, `@hono/node-server`, sharp/libvips,
brace-expansion, fast-uri, js-yaml and postcss. Those remain OI-017's.
**Candidate fix (NOT applied — report-only; this sweep never runs `npm audit fix`):** bump both
repos to `hono@^4.12.34`. Semver-compatible in both, and the highest-reachability compatible fix
available in either.
**Auto-check:** none.

### OI-092
**Status:** CLOSED 2026-08-05 (merge), re-verified 2026-08-09. Workbook fix + snapshot remediation DONE
(same as before). **The detector's first attempt was WITHDRAWN before shipping** (see the CORRECTION
appended below, and the preserved draft at `docs/superpowers/plans/withdrawn-detector-oi092/`, commit
`0701397`) — **the RETRY was built on the corrected design, independently reviewed twice (including a
post-REFUTE gap found by a separate Code-surface session), and MERGED as PR #261 (`59d1995`,
2026-08-05T22:13:45Z)**. See the table row above for the full build/review/merge citation chain; this
detail section's original "queued, new session" framing is superseded.
*(Status line corrected 2026-08-05: it previously read "detector shipped, awaiting review sign-off",
which contradicted the CORRECTION in this same entry. Corrected again 2026-08-09: the detector shipped
and merged the same day this entry was last touched — "REBUILD... queued... new session" had gone
stale within hours.)*
**Opened:** 2026-08-05
**Closed:** 2026-08-05
**Source:** `ora-lease-snapshot-refresh` run 2026-08-05; handoff session `3d9d97cf`
**Severity:** MEDIUM (financial reporting accuracy — DSCR input; no governor decision affected)
**Description:** `External Loans Summary!H6:I9`, `H15:I15`, `H16` computed next-12-month interest and
principal over `[TODAY(), TODAY()+366)`. That half-open 366-day span captured **13 payments instead of
12** whenever `TODAY()` landed on a loan's payment day-of-month, inflating annual debt service by
exactly one payment and depressing DSCR. Payment days: 3540 E Fifth Ave / 9050 Red Branch Road /
29000 Information Lane on the 1st; Banwick / Morrison on the 5th. Fired ~6 days per loan per year and
self-corrected the next day, so it never presented as a persistent defect.
**Resolved — workbook (Gabriel, 2026-08-05 ~15:14 ET, his own edit, confirmed):** window replaced with
`(Assumptions!$B$30, EDATE(Assumptions!$B$30,12)]` — exactly 12 payments, anchored on
`Assumptions!B30` "Loan As-Of Date" = `EOMONTH(TODAY(),0)`. Month-end anchoring makes the payment-day
coincidence **structurally impossible**, not merely corrected. Verified: `J9` = $275,031.24, matching
Symetra loan 11153's own amortization schedule. Full-workbook sweep confirms zero `TODAY()+366` remain.
**Note this was also a reporting-DEFINITION change:** "next 12 months" now means 12 months from the
month-end close, not from today. That re-anchor moved Restoration Church Trust by two payments
(−58,497.78 → −50,140.95) with no defect involved, and decremented every loan's `monthsToMaturity`
by 1. Do not read those as drift.
**Resolved — downstream:** the warehouse `debt_positions` table was **clean** (all 8 snapshot dates
fell on non-payment days; nothing was ever frozen inflated, nothing backfilled). The one contaminated
artifact was `data/snapshots/portfolio.json` committed in `61cc346`; re-baked and committed as
`51d4039` (oxford-command-center, local only, **not pushed**). Banwick DSCR 2.641 → 2.861 — the bug
*depressed* DSCR, moving it toward the 1.25x floor, so no capital-allocation or governor gate was
ever wrongly cleared.
**Detector (WITHDRAWN, first attempt — historical only, do not build against this):**
`server/workbook/debt-service-window.ts` + 14 unit tests, wired into `parseWorkbook` after
`parseLoans`. Counted amortization-schedule rows in the window and asserted exactly 12; warn-severity
per Gabriel's ruling, with a carve-out so a genuine near-maturity taper does not false-fire. Live probe:
12/12/12/12 for the four borrower loans, 8 for Restoration Church Trust correctly suppressed (matures
2027-02-20, inside the window). Extract reported 0 flags — which is exactly why it was withdrawn: it
could not detect the defect it existed for (see the CORRECTION section below). Superseded 2026-08-05 by
`server/workbook/debt-service-crosscheck.ts`, merged in PR #261 — see the Status line and table row
above for the shipped version.
**Do NOT build the ">2 decimal places" detector** the original handoff proposed — it fires on 6 of 11
loans, every one correct (`9050 Red Branch` carries a legitimate half-cent from its `*0.5` Oxford-share
multiplier; `3883 from Oxford` has no schedule at all, so its "monthly payment" is a synthetic
annual÷12 and always repeats). At error-severity it would block every refresh permanently. (Still true
of the shipped detector — it never uses decimal-place count as a signal.)
**Residual, re-checked 2026-08-09:** (a) the workbook's own `Claude Log` still has no entry for the
08-05 edit — last row is Turn 147 (08-03); still open, not addressed by the detector ship. (b)
`SCHEDULE_SOURCES` hardcoding is now MOOT — it belonged only to the withdrawn draft; the shipped
detector derives each schedule's range from the live `External Loans Summary` formula at cross-check
time, so there is no parallel range to drift out of sync.
**Auto-check:** `npm run extract` — the detector emits a warn-severity `annualDebtService` flag.
**Memory:** `reference_workbook_annual_debt_service_366day_overcapture.md`

### OI-093
**Status:** RESOLVED 2026-08-05. Gabriel confirmed "Northwood is good" (go-ahead to recreate).
Rebuilt `Northwood FROM EGFLLC` in the live workbook, modeled row-for-row on `1100 From Fenton`
(the simplest existing single-balance journal — Turn 144 named `2203 FROM EGFLLC` as its template,
but that sheet has irregular mid-month paydowns Northwood never had; the simpler template is the
better structural match). Matches Turn 147's own recorded specifics exactly: 8 monthly interest-only
periods, 1/1/2026–8/31/2026, constant $2,800,000 balance, 6.99% (`Rate_Northwood_EGFLLC`, already
present in `Assumptions!B21`), Feb=28 days (2026 not a leap year). Wired `Portfolio Summary —
Internal!C10`/`D10` to the new sheet with the same `LOOKUP(2,1/(...))` pattern every other row uses.
**Verification (not skipped):** openpyxl round-trip fidelity tested first on a scratch copy (0
unintended diffs across the full workbook) before any live write. Every write went scratch → diff →
fresh-copy-of-live → diff → live → diff, three full passes. Final end-to-end diff against the
original pre-session snapshot: 50→51 sheets, 30/30 defined names intact, **0 cells removed, 0 cells
changed anywhere else in the workbook**, exactly the 8 intended additions (6 on a new `Claude Log`
Turn 150 entry, 2 on `Portfolio Summary — Internal!C10`/`D10`).
**CAVEAT — not yet live for any automated reader.** Written via openpyxl (file-level), which does
NOT recalculate formulas. The new formulas carry no cached value until Excel opens the file once and
recalculates (automatic on open, or F9). Any tool reading cached values only — not live Excel — will
see the new cells blank/0 until then. Expected once recalculated: annual forward interest exactly
$195,720.00 (matches Turn 147's own quoted figure), Portfolio Summary row 10 balance/original-
principal repopulate and rejoin every portfolio total.
**Opened:** 2026-08-05
**Closed:** 2026-08-05
**Source:** surfaced by the OI-092 `portfolio.json` re-bake (`51d4039`)
**Severity:** MEDIUM (silent history split in the debt warehouse)
**Description:** The internal 2203-2207 Northwood loan now parses with **no journal sheet**, which
changed its snapshot id from `internal-2203-2207-northwood` to
`internal-2203-2207-northwood-no-journal-sheet` and its display name to
`⚠ 2203-2207 Northwood — NO JOURNAL SHEET`. The loan was reclassified from EXTERNAL to INTERNAL on
2026-08-03 (workbook Claude Log Turn 144, register WBC-…), which created the expectation of a journal
sheet that does not exist or is not named as the parser expects.
**Impact:** `debt_positions` keys `ON CONFLICT(id, snapshot_date)`, so the id change makes every
future snapshot land under a NEW key — silently orphaning this loan's prior history under the old id
rather than continuing it. Time-series queries on that loan will show a gap and a restart, not a
rename. `monthsToMaturity` also went null → 105.
**Candidate fix (NOT applied):** either create/rename the Northwood journal sheet to what the parser
expects, or add an explicit id-alias so the reclassified loan keeps its original warehouse key.
Decide which before the next warehouse snapshot run, since each run widens the split.
**Auto-check:** `npm run extract` then grep `portfolio.json` for `no-journal-sheet`.

### OI-094
**Status:** RESOLVED 2026-08-05 — the range fix LANDED. `'External Loans Summary'!H9`/`I9` now read
`Banwick-Morrison!B11:B71` / `D11:D71` / `E11:E71`, capturing the 2031-06-05 balloon row. Verified
directly against the live workbook: `J9` = $275,031.24 and `Loan Index!F9` = $22,919.27, matching
Symetra loan 11153's own amortization schedule. The February pair fix landed in the same consolidated
edit (all window cells on `EOMONTH(Assumptions!$B$30,12)`, `B30` constrained to month-end).
Findings (a) and (b) were promoted out to [OI-096](#OI-096) (OPEN, ruled) and [OI-095](#OI-095)
(CLOSED) and are **not** closed by this resolution.
*(Status line corrected 2026-08-05: it previously read "needs Gabriel's ruling", which was stale — the
ruling was given and the edit applied. Left as-is it would have prompted a redundant re-ask.)*
**Opened:** 2026-08-05
**Closed:** 2026-08-05
**Source:** adversarial REFUTE pass on the OI-092 detector; independently re-verified against the live workbook
**Severity:** MEDIUM now, HIGH from ~mid-2030 (understates annual debt service by $3.35M when it bites)
**Description:** `'External Loans Summary'!H9` and `I9` sum the Banwick-Morrison schedule over
`B11:B70` / `D11:D70` / `E11:E70`. The schedule's **final payment is row 71**, and it carries the
balloon. Verified directly from the workbook (2026-08-05, cached values):
```
r70: B=2031-05-05  D(int)=15,370.91  E(prin)=7,548.36      F(bal)=3,333,953.68
r71: B=2031-06-05  D(int)=15,336.19  E(prin)=3,333,953.68  F(bal)=0        <-- EXCLUDED
```
`K9` (maturity) = `'Banwick-Morrison'!E7` = **2031-06-05** — the very row the SUMPRODUCT range stops
one short of. Row 71's total is $3,349,289.87, matching Symetra loan 11153's documented balloon of
$3,349,289.89 to within rounding.
**Impact:** currently immaterial — the forward window ends 2027-08-31, nowhere near 2031-06-05. It
becomes real around **mid-2030**, when the balloon enters the forward-12-month window and `J9`
silently omits it. The direction is the dangerous one: annual debt service is **understated**, so
**DSCR is overstated** against the governed 1.25x floor. Note this is independent of the OI-092
window fix — correcting the window did not correct the range.
**Also check the other five loans for the same one-short truncation** before ruling; only Banwick was
verified. Ranges in use: 3540 `B9:B92` · 9050 `B11:B158` · 29000 `A9:A69` · Banwick `B11:B70` ·
RCT `B11:B310` · 485 Walnut `B10:B46`.
**Candidate fix (NOT applied):** extend the Banwick ranges to row 71. Do NOT blanket-widen — row 74
of that sheet holds a bare number (276714.48) in col B that would be misread as a date if swept in.
**Auto-check:** none yet — this is precisely what the OI-092 detector redesign should catch.

### OI-092 — CORRECTION appended 2026-08-05
The detector described above (`server/workbook/debt-service-window.ts`) was **withdrawn before
shipping** and its `parse.ts` wiring reverted. Independent code review plus an adversarial REFUTE pass
both found it **cannot detect the defect it was built for**: `countPaymentsInWindow` computes its own
correct window from `asOf` and counts schedule rows against it, never reading the `External Loans
Summary` formula. Reverting `H9` to the buggy `TODAY()+366` leaves its output byte-identical — all
clean — while annual debt service re-inflates to $297,950.51. It tested a property of the schedule
DATA, not of the FORMULA that carried the bug.
Three further confirmed defects in that draft: (a) it counts rows, not distinct dates, and
`485 S Walnut St` rows 45/46 both hold `2028-09-26`, producing a **false "13 payments" flag dated
2027-09-30** — the exact fingerprint of the bug just fixed; (b) the near-maturity carve-out
suppresses any short count whose last read row lands inside the window, so a truncated range, a stale
schedule, or a dropped row all read as clean — it would sit silently on OI-094; (c) the test fixture
built dates with `Date.UTC(y,m,day)`, which **overflows** instead of clamping, so the 29th/30th/31st
payer cases the design rests on were never actually tested.
**Sound and worth keeping from the draft:** `edateMonths` was differentially verified against Excel
EDATE semantics over 1990–2060 (0 mismatches, negative months and leap-Feb clamping both correct).
**Correct design for the retry:** independently recompute annual debt service from the FULL
amortization schedule and compare against the workbook's own `External Loans Summary!J`. That is a
cross-check of two independent computations, so it catches a wrong window (OI-092), a truncated range
(OI-094), and wrong column mapping alike — none of which the count-only shape can see. Must handle
the per-loan `*0.5` Oxford-share multipliers and the lender-row sign convention.
**Residual defect in the CURRENT workbook, latent:** February month-end close in the year before a
leap year (`asOf` 2027-02-28 → end 2028-02-28) captures **11** payments for a month-end-clamped payer,
understating debt service and OVERSTATING DSCR. Recurs 2031-02-28, 2035-02-28. No current loan pays
month-end (pay days: 1, 1, 1, 5, 20, 26), so it is latent — but one acquisition on month-end terms
makes it live. The claim that month-end anchoring makes the coincidence "structurally impossible" is
therefore too strong: it closes the over-capture path, not the under-capture path.

### OI-094 — AUDIT COMPLETE 2026-08-05 (all six ranges checked; Gabriel ruled: consolidated fix)
**Only Banwick is truncated.** Verified by scanning 40 rows past each formula's range end:
| loan | range | dated rows in range | rows past end | verdict |
|---|---|---|---|---|
| 3540 E Fifth Ave | `B9:B92` | 84, last r92 2032-04-01 | none | ok |
| 9050 Red Branch | `B11:B158` | 148, last r158 2028-01-01 | none | ok |
| 29000 Information Ln | `A9:A69` | 61, last r69 2030-12-01 | none | ok |
| **Banwick / Morrison** | `B11:B70` | 60, last r70 2031-05-05 | **r71 2031-06-05, REAL** | **TRUNCATED** |
| Restoration Church Trust | `B11:B310` | 26, last r37 2027-02-20 | none | ok (see below) |
| 485 S Walnut St | `B10:B46` | 37, last r46 2028-09-26 | none | ok (see below) |

**PROMOTED OUT 2026-08-05 (Gabriel ruling) — findings (a) and (b) below now have their own ids so that
closing OI-094 on the Banwick range fix cannot silently close them: (a) → [OI-096](#OI-096) (OPEN),
(b) → [OI-095](#OI-095) (RULED intentional, no change). Text retained here for the audit narrative;
**the live status lives in those entries**, not here.**

**Consolidated fix scope for OI-094 (Gabriel ruling 2026-08-05)** — one workbook session covering BOTH:
1. extend the Banwick ranges to row 71 (the balloon), and
2. the February pair fix — six cells to `EOMONTH(Assumptions!$B$30,12)` **and** `B30` constrained to
   month-end. Folded in here rather than tracked separately, per ruling; supersedes the earlier
   "let the detector cover it" answer, which was given before the 1,080-case simulation existed.

Second independent audit (session `3d9d97cf`, 2026-08-05) reproduced the range table above exactly —
Banwick the only truncated range, other five ending on their final payment row — and independently
found (b). It did **not** find (a); the duplicate-date over-count was caught only by the first pass.

**TWO NEW findings the range audit surfaced — both need Gabriel's read, neither is a range problem:**

(a) **485 S Walnut St double-counts $1,365 from ~Oct 2027.** Rows 45 and 46 BOTH carry `2028-09-26`:
r45 is the final regular payment (`D`=1365 interest, `E`=1365, `F`=252,000 balance); r46 is the payoff
(`D`=253,365 = 252,000 principal + 1,365 interest, `E`=1365, `F`=0). `H16` sums column `E` over the
date predicate, so it picks up **both** rows' 1,365 — the same September interest counted twice. Bites
when 2028-09-26 enters the forward window, around Oct 2027. Small ($1,365) but it is a genuine
over-count, and it is the same "13 payments" shape as OI-092.

(b) **Restoration Church Trust's $1.945M balloon is absent from `I15` (annual principal).** Rows 35/36/37
all carry `2027-02-20`: r35 is the regular payment (`D`=14,604.09 int, `E`=2,109.56 prin), r36 holds the
balloon **in column C** (`C`=1,945,102.73, `D`/`E` empty, `F`=0), r37 holds Oxford's 50% share
(`C`=972,551.37, `D`/`E` empty). Because `H15`/`I15` sum `D`/`E` only, the balloon contributes **zero** —
so the next-12-month principal return understates Oxford's capital coming back by **$972,551**. The
maturity date 2027-02-20 is ALREADY inside the current window (ends 2027-08-31), so this is live NOW,
not latent. May be intentional (C = total payment, D/E = the itemized split that balloons don't carry) —
**needs Gabriel's read before any change.**

**February fix VERIFIED by simulation (1,080 cases: 120 month-ends x 9 pay-days):**
- `EDATE(B30,12)` right edge → **9 deviations**, all under-capture 11, all month-end payers on
  asOf 2027-02-28 / 2031-02-28 / 2035-02-28.
- `EOMONTH(B30,12)` right edge → **0 deviations.**
- BUT under manual override (B32 = an arbitrary non-month-end date) `EOMONTH` is catastrophic —
  **1,428 deviations, over-capturing 13** — while `EDATE` has only 6. So the fix is a PAIR, not one edit:
  the six cells move to `EOMONTH(Assumptions!$B$30,12)` **and** `B30` must be constrained to month-end:
  `=IF(B31="Auto (current month-end)",EOMONTH(TODAY(),0),IF(ISNUMBER(B32),EOMONTH(B32,0),EOMONTH(TODAY(),0)))`
  This is consistent with the sheet's own design intent — B30's label already reads "current month-end"
  and B33's status formula already compares against `EOMONTH(TODAY(),0)`.

### OI-093 — RESOLVED (diagnosis) 2026-08-05
**The Northwood journal sheet does not exist.** Full sheet enumeration of the live workbook (50 sheets)
contains no Northwood sheet of any spelling — the only match for "north" is `Banwick-Morrison` (a false
hit on "Morrison"). Internal-loan journals present: `2203 FROM EGFLLC`, `EGFLLC FROM OXFORD`,
`3883 from Oxford & LAST Non`, `1100 From Fenton`, `Muirkirk to EG(Oxford)+ LASTNON`,
`Muirkirk from Oxford`.
**Note the provenance problem:** the workbook's own `Claude Log` Turn 144 (2026-08-03) states the
Northwood sheet was *created* as part of the EXTERNAL→INTERNAL reclassification. It is not there. Either
that step never completed, or the sheet was created and subsequently removed. The parser's
`⚠ NO JOURNAL SHEET` marker is therefore **correct and is reporting a real gap**, not a parser defect —
so the fix is to create the journal sheet, not to alias the id. Aliasing alone would hide a genuinely
missing accounting record.
**Gabriel ruled 2026-08-05:** create the journal sheet — but **chase the provenance first**. Claude Log
Turn 144 (2026-08-03) claims the sheet was created and it is not there; whether that step never
completed or the sheet was created and later removed implies different things about whether the rest
of that reclassification landed. Establish which before recreating. Do NOT alias.

### OI-095
**Status:** CLOSED 2026-08-05 — final basis: **include the balloon**, superseding this session's earlier
"intentional, no change" reading. **Timeline:** Gabriel first ruled (this session, AskUserQuestion)
that RCT's balloon exclusion from `I15` was intentional modelling. `Claude Log` Turn 149, applied to
the live workbook the same day, did the opposite — populated `RCT!E36` with the $1,945,102.73 balloon,
moving `I15` from ~0 to -$978,763.425 and `J15` from -$50,140.95 to -$1,022,692.32 — on the reasoning
that the entire remaining balance is contractually repaid inside the window, so the exclusion was the
actual defect. Verified against the live formulas 2026-08-05 (session `3d9d97cf`) — a real cell/formula
change, not a stale log entry. **Gabriel confirmed 2026-08-05 he authorized the Turn 149 reversal** —
resolves the conflict; the earlier "intentional, no change" framing does NOT stand. **Correction to the
record, not vindication:** this session's original OI-095 close was accurate to what Gabriel said at
the time, but was superseded within the same day by his own further direction. Do not read the first
ruling as "wrong" in isolation — read the second as current. **Note on the "Residual — RULED" section below:** it explains the surviving 3540-vs-RCT asymmetry
(borrower balloon = obligation, captured; lender balloon = return, now also captured) and that
reasoning is still accurate as a description of the CURRENT state. But do not read it as confirming the
original OI-095 "C=total, D/E=itemized split RCT legitimately lacks" theory — Turn 149's own root cause
was different and more precise: `I14`/`I16` were computing "principal paid to date," not the header's
promised "next 12 months," and `I15` read the wrong column for RCT's balloon specifically. All three
lender rows were fixed to one consistent forward-looking basis; RCT's balloon inclusion is a
consequence of that basis, not a standalone reversal of an isolated design choice.
**Opened:** 2026-08-05 (promoted out of OI-094 finding (b) per Gabriel ruling, so the Banwick fix
closing OI-094 cannot silently close this)
**Closed:** 2026-08-05
**Source:** OI-094 six-range audit; independently corroborated by a second session's audit same day
**Severity:** N/A as ruled — was MEDIUM ($972,551 of next-12-month principal return)
**Description:** `Restoration Church Trust` rows 35/36/37 all carry `2027-02-20`. r35 is the regular
payment with its split in `D`/`E`; r36 holds the full balloon **in column `C`** ($1,945,102.73, `D`/`E`
empty, `F`=0); r37 holds Oxford's 50% share ($972,551.37, `D`/`E` empty).
`'External Loans Summary'!H15`/`I15` sum `D`/`E` only, so the balloon contributes **zero** to the
next-12-month figure. 2027-02-20 is already inside the current forward window.
**Gabriel's ruling (2026-08-05):** intentional. `C` is the total payment; `D`/`E` are the itemized
interest/principal split that balloon rows legitimately do not carry. "Annual debt service" means
recurring P&I only and deliberately excludes principal returned at maturity. **No change to RCT.**
**Residual — RULED 2026-08-05 (Gabriel): both sheets are correct as they stand. Change neither.**
The observation: `3540 E Fifth Ave` row 92 places its balloon principal in column `F` — the column
`I6` sums — so **3540's balloon IS captured** while RCT's is not.
**This asymmetry is principled, not accidental.** 3540 is a **borrower** loan: its balloon is cash
Oxford must pay, so it belongs in annual debt service. RCT is a **lender** loan: its balloon is capital
returning *to* Oxford, so it is not debt service at all. Both treatments follow directly from the
ruling above ("what we must service"), and the direction convention is already used elsewhere
(`src/analytics/conditions.ts` sign handling).
**Do NOT "harmonize" the two sheets.** Seeing them side by side invites exactly that, and it would
either drop a real $2.14M cash obligation from the borrower-side figure or inflate the lender-side
figure with capital that was never an obligation.
*(Provenance note: session `3d9d97cf` first filed this as an accidental inconsistency and recommended
excluding 3540's balloon. That framing was wrong — the borrower/lender distinction was missed. Recorded
so the earlier reasoning is not mistaken for a second, conflicting ruling.)*
**Detector constraint SUPERSEDED 2026-08-05 (Turn 149 + Gabriel confirmation) — do not build to this
sentence.** It previously read "the cross-check must NOT treat balloon-excluded principal on lender
rows as an error." RCT's balloon is now INCLUDED (see OI-095's CLOSED status), so the retry should
expect balloon-inclusive forward-looking principal on ALL lender rows and flag exclusion as the error,
not the reverse. This borrower/lender asymmetry paragraph itself (why 3540 captures its balloon and how
that differs conceptually from a lender row) is still accurate; only the detector's pass/fail direction
on lender rows changed.

### OI-100
**Status:** CLOSED 2026-08-12 — MERGED AND LIVE. Fix commit `9ad6146` (`fix(hooks): pre-push
doctrine gate validates the pushed commit, not the working tree`) merged to `origin/main` via
`230da82` on 2026-08-05. Independent review + adversarial REFUTE pass both APPROVED (both
fable-tier); 14/14 new tests + 37/37 existing gate tests + full probe suite green; TDD red
confirmed via git-stash before the fix landed. Verified 2026-08-12: `9ad6146` is an ancestor
of `origin/main`, and the live `hooks/git-prepush-doctrine-gate.py` matches that commit's
content exactly (materializes and validates the pushed commit, not the working tree) — the
fix is deployed, not merely merged in history. Status wording had drifted stale after
`7e14825` (2026-08-09) restored this section's pre-accidental-sweep-in text without also
picking up the merge that had already happened four days earlier; corrected here.
**Closed:** 2026-08-12 (fix actually merged 2026-08-05; tracker wording lagged)
**Opened:** 2026-08-05
**Source:** Gabriel ruling 2026-08-05 (rescope approved); design/trap investigation this session
**Severity:** MEDIUM (correctness of a fail-closed security gate, plus shared-checkout friction)
**Description:** `hooks/git-prepush-doctrine-gate.py` runs `doctrine-integrity-probe.py` with **no
arguments**, so the probe evaluates the **working tree**. Two consequences:
1. **Friction:** in a shared checkout, one session's half-finished edit blocks *everyone's* push.
2. **False-negative hole (the stronger reason):** commit drift, then fix it uncommitted — the probe
   passes on a clean working tree while the drift is what actually reaches the remote. What is pushed
   is commit content, not the working tree.
**TWO TRAPS — either one silently weakens the gate if the "obvious" fix is taken:**
- **Trap 1 — the path-override route guts the gate.** Passing the probe's positional CLAUDE.md or
  `--session-context=`/`--rules=`/`--terms=` sets `live_mode = argv_path is None` → **False**
  (`doctrine-integrity-probe.py:971`), which disables **seven** coupled blocks (lines 1216, 1467, 1518,
  1524, 1585, 1618, 1641), including backup-root scanning and the `PORTED_CLAUDE_MD_COPIES` checks.
  This is a reduced check set, not a rescope.
- **Trap 2 — a temp worktree alone does not redirect it.** The probe's roots are
  `HOME = Path(os.path.expanduser("~"))` / `CLAUDE_DIR` / `REAL_CLAUDE_MD` (`:93-95`). `expanduser` on
  Windows keys off `USERPROFILE`, so redirecting by environment is platform-sensitive — too fragile to
  hang a fail-closed security gate on.
**Design (agreed direction):** add an **explicit root-override env var** to the probe that does **not**
flip `live_mode`; have the gate materialize the pushed commit via `git worktree add --detach <sha>` and
run the probe in **FULL live mode** against that root. Preserve the existing fail-closed contract: a
probe that cannot be launched still counts as drift, and the gate must keep reading no stdin (the shim
relies on that to hand git's ref payload to the confidentiality scan).
**Done bar:** `hooks/**` + security-gate exit-code logic → TDD, independent local review, and a
**mandatory adversarial REFUTE pass** plus the old-vs-new differential battery. Deliberately left
unimplemented rather than half-landed in a fail-closed gate.
**Auto-check:** a test that commits drift and then reverts it in the working tree only — the gate must
BLOCK (today it allows).

### OI-056
**Status:** CLOSED
**Opened:** 2026-08-03
**Closed:** 2026-08-03
**Source:** `doctrine-integrity-probe.py` pre-push run, 2026-08-03; resolved by `edc9fa1` + `7596feb`
**Description:** Detail section written 2026-08-05 (this row existed in the Closed table with no `###`
section — see [OI-098](#OI-098)); content is restated from the row, not re-investigated.
Logged initially as three instances of one defect; **only two were the same bug.**
`ratify-hurdle-rate` and `tenant-email` SKILL.md genuinely carried "Principal" against canon and were
corrected to "VP Acquisitions" (`edc9fa1`).
**The third was not a defect.** `document-assembly/SKILL.md:180` says "Member / Principal", which Gabriel
ruled states the **LLC-execution capacity** he binds under — a distinct concept from his firm operating
title. Left unchanged, with an in-file note recording it as a documented Check-13 false positive
(`7596feb`).
**Separately recorded, not this item:** 21 live "Landlord - \*" Outlook signatures carry the same
execution-capacity language and sit outside the probe's scan scope.

### OI-094 — RESOLVED 2026-08-05 (workbook edits applied, Claude Log Turn 148)
Four Gabriel-approved edits applied via Excel COM and independently re-verified:
1. Banwick `H9`/`I9` ranges `B11:B70` → `B11:B71` — captures the 2031-06-05 balloon. Proof: at
   `asOf` 2030-06-30 the window now returns 12 payments WITH the balloon; before, 11 and a silent
   $3.35M omission.
2. All 11 window cells `EDATE(B30,12)` → `EOMONTH(B30,12)` (0 deviations vs 9).
3. `Assumptions!B30` manual-override branch wrapped in `EOMONTH(B32,0)` — **mandatory pair with #2**;
   with a non-month-end override, `EOMONTH` over-captures in 1,428/1,428 cases.
4. `485 S Walnut St` r46 → pure balloon (D=252,000, E=0); TOTALS 302,505→301,140, 50,505→49,140.
**No currently-reported figure moved** — all four are future-proofing. Verified unchanged:
195,653.52 / 146,269.26 / 208,344.72 / 275,031.24 / 47,895.08 / −50,140.95 / −16,380; 0 formula-error
cells across 50 sheets. Snapshot re-baked and pushed (`f269986`).
**PROCESS LESSON — the first COM script was not defensive enough for a financial model.**
`FormulaArray` threw on `H15` (longer lender-row formulas) and, with `$ErrorActionPreference='Stop'`,
the script aborted AFTER 8 of 11 edits had been made — leaving the workbook SAVED in a mixed
EDATE/EOMONTH state plus an orphaned `EXCEL.EXE` holding it. No value was ever wrong (EOMONTH and
EDATE agree while B30 is month-end), and it was caught on the next verification pass. **Next time:**
per-cell `try/catch` with a `FormulaArray → Formula2 → Formula` fallback ladder, save only after all
edits are attempted, and a `finally` block that always closes/quits. Also: kill ONLY your own orphaned
PID — Gabriel's interactive Excel was PID 21768 throughout.

### OI-093 — RESOLVED 2026-08-05
Gabriel resolved it in the workbook himself at 16:20: the row is retitled
`⚠ DUPLICATE OF ROW 22 — DO NOT USE` (Loan Index r24, idx 13, balance 0). My earlier "create the
missing journal sheet" recommendation was **wrong** — there was no missing sheet, it was a duplicate
entry. Residual closed in code: `parseLoans` now skips tombstoned rows via the exported
`isTombstonedLoanRow` predicate (`9ab137d`), so a retired row can no longer mint a snapshot id or
claim a `debt_positions` key. Matching is narrow (`DO NOT USE` / `DUPLICATE OF <x>`; bare "duplicate"
is not a marker) and all 13 live loan names are pinned as non-matches. The skip raises an
**info**-severity flag naming the row — deliberately not silent. Live: loans 13 → 12, tombstone id
absent, 1 info flag. Full suite 3,266 pass.

### OI-095-CANDIDATE — lender block "Annual Principal (Next 12 Months)" is semantically inconsistent
Surfaced by the OI-094 audit; **not yet allocated an id, awaiting Gabriel's ruling.**
`I14` (1100 Rarig) and `I16` (485 Walnut) compute `D−E` = principal repaid **to date**; `I15` (RCT)
sums the schedule over the **forward 12-month** window. All three sit under the same
"Annual Principal (Next 12 Months)" header (`I4`). Consequences: (a) RCT's $1,945,102.73 balloon due
**2027-02-20 — already inside the window** — is absent from `I15` because it sits in column C
(Payment Amount) not D/E, so Oxford's 50% share of **$972,551** of principal return is missing;
(b) `I16` will miss Walnut's $252,000 balloon when it enters the window in **Oct 2027**. The RCT sheet
r8 already holds `Balloon Balance at Maturity (Oxford 50%) = -972,551.365`, so the figure exists — it
just doesn't flow. **Careful:** RCT r37 is a 50%-share memo row and `H15`/`I15` already apply `*0.5`;
never let r37 into a D/E sum or it double-counts.

### OI-107
**Status:** CLOSED 2026-08-09 — fix landed (`1af60c3` + `2e29fa7`), both tasks re-enabled and verified
**Closed:** 2026-08-09
**Opened:** 2026-08-09
**Source:** [event_log.md](event_log.md#2026-08-09) — "ora-task-integrity-guard AND ora-health-guard PAUSED one cycle"; originating handoff at `~/.claude/maintenance/_state/guard-handoff-2026-08-09-frontmatter-retags.md`
**Severity:** MEDIUM, time-boxed — the pause itself is the mitigation; the risk is that it is never lifted
**Description:** `ora-task-integrity-guard` (cron `5 7 * * *`) and `ora-health-guard` (cron `15 5 * * *`)
are both `enabled:false` as of 2026-08-09 (Gabriel-directed, in-turn). Crons are preserved; only
`enabled` was flipped, via `update_scheduled_task` — never the Scheduled-sidebar delete.
**Why paused:** the live `guard.ps1` is still the 2026-07-24 mtime-newest-wins engine, which can
silently revert a legitimate canonical SKILL.md edit when a stale mirror's mtime is bumped above
canonical's (the documented OneDrive-sync mechanism; it reverted three live SKILL.mds at
2026-08-09 08:54:47). The replacement decision core is uncommitted WIP in worktree
`fix/guard-content-revert` (owning session `local_e69b7e30`).
**TWO tasks, not one — this is the part that is easy to get wrong:** `ora-health-guard` Block A.1
(its `SKILL.md:73`) invokes the *same* `guard.ps1` by absolute path at 05:25 ET, two hours BEFORE
the 07:14 slot. Disabling only `ora-task-integrity-guard` leaves the old engine running.
**Closing condition:** the guard.ps1 fix lands on `main`, then BOTH are re-enabled:
`update_scheduled_task(taskId:"ora-task-integrity-guard", enabled:true)` and
`update_scheduled_task(taskId:"ora-health-guard", enabled:true)`. Verify with
`list_scheduled_tasks` (a registry/file read is not verification — `register-scheduled-task` Rule 2).
Both already carry dated MODEL tags, so v2.8's re-enable precondition is satisfied as-is.
**Known collateral while paused (accepted, one cycle):** ora-health-guard Block C's probe suite does
not run — memory-integrity, confidentiality self-test, cc-verifier, setup-self-audit, connector-drift,
and the new v1.3 C.1.1 missed-cycle escalation. Governor/doctrine coverage survives via
`ora-doctrine-integrity-guard` (12:55 ET daily). ora-task-integrity-guard STEP 1.5's three producers
also skip: `registry-membership-probe.py`, `emit-fleet-heartbeat.py`, `push-fleet-heartbeat.ps1` —
expect a one-day gap in `_state/registry-membership.log` and the external heartbeat, and expect
`fleet-deadman.ps1` check 4 (Windows Task Scheduler, outside both fleets) to flag the guard as
not-run. That alarm is expected noise, not a real miss.
**Note on the auto-check below:** `memory-integrity-probe.py` is normally run daily by
`ora-health-guard` — which is one of the two tasks paused here — so while this item is open the
auto-check is only evaluated on `ora-cc-schematic-refresh`'s Mon+Thu cadence. It self-resolves the
moment the item does.
**Outcome:** the auto-check above did its job — `memory-integrity-probe.py` flagged the match, which is how the
closure was noticed at all. Worth keeping as a pattern for time-boxed pauses.
**Auto-check:** none (item closed).

### OI-108
**Status:** CLOSED 2026-08-09 — merged to `main` as `8fca11d` after a 2-round independent review
**Closed:** 2026-08-09
**Opened:** 2026-08-09
**Source:** investigation of two claim-holder session ids (`1d24d6a4`, `b09003a0`) that did not resolve against `list_sessions`
**Severity:** LOW/MEDIUM — no data loss; degrades the cross-session collision protocol that exists to prevent duplicated/colliding work
**Defect 1 — two disjoint session-id namespaces, nothing carried both.** `own_session_id()`
(`hooks/lib/claim_work.py:125`) returns `CLAUDE_CODE_SESSION_ID` — the agent id, e.g.
`21c98da5-56d2-49aa-bbe9-6626591e6fdd`. `list_sessions` and `send_message` accept ONLY
`CLAUDE_CODE_HOST_SESSION_ID` — e.g. `local_c689f07f-d45a-473e-94d9-3f418c47e5cd`. Claim files, the
`obsidian-fleet-mirror/session-state.d/` mirror (its `_sid`) and `session_liveness.py` are all agent-id;
`list_sessions`/`send_message`/handoff notes are all host-id. **Verified both directions:** every claim
id checked resolves to a live record under `session-state.d/`, and `local_*` ids appear nowhere in any
machine-written artifact under `~/.claude`. Consequence: a colliding claim could be seen but its owner
could not be messaged — and the ids looked like phantom sessions, which is a misleading failure shape.
**Defect 2 — `--paths` silently dropped all but the last occurrence.** `nargs="*"` without
`action="extend"` makes argparse OVERWRITE on a repeated flag. Observed live: a claim passing
`--paths hooks/lib/claim_work.py --paths hooks/active-work-broadcast.py` recorded ONE path, dropping the
file actually being edited. Silent under-cover of the exact protection defect D1 added 2026-07-26.
**Fix (additive, branch `fix/claim-host-session-id`):** new `own_host_session_id()`; `write_claim()`
records `host_session_id` alongside (never instead of) `session_id`, so ownership matching and the
agent-id-keyed mirror join are untouched; `read_active_claims()` defaults the key so pre-2026-08-09
claim files still read; `renew_claim()` carries it through (a rewrite drops anything not passed);
`list` prints it in full; `active-work-broadcast.py` appends `(message it at <host id>)`, sanitized via
`_sanitize_field` per the R4 threat model. `--paths` becomes `action="extend"`. Fails open: an
unattended session with no host var records `""`, never `"unknown"` (which is a legal agent id and
would read as a real target).
**Evidence so far:** `test-claim-work-lib.py` 71/71 (was 55/55), `test-active-work-broadcast.py` 30/30
(was 23/23), full `hooks/tests` 43/43 — the 44th, `test-confidentiality-guard.py`, cannot run in any
worktree because `hooks/confidential-terms.json` is git-ignored (`.gitignore:138`) and passes 131/131 in
the main checkout. A live end-to-end run confirms a new claim renders the host id and a legacy
host-less claim renders none.
**Caught by the live run, NOT by the unit test:** the first implementation sanitized before testing
emptiness, and `_sanitize_field("")` returns `"(no description)"` — so every legacy claim rendered
`(message it at (no description))`. The test asserted too narrowly (`"host )"`) and passed anyway. Both
the implementation and the assertion were fixed, and the strengthened test was proven to catch the
regression (28/30 with the old implementation restored, 30/30 with the fix).
**Closing condition (MET):** independent review (`claude-fable-5`, 2 rounds, APPROVED WITH NITS), merged to `main` as `8fca11d`, full `hooks/tests` re-run on main post-merge: 44/44, 0 failures.
**Auto-check:** none.

### OI-110
**Status:** CLOSED
**Opened:** 2026-08-09
**Closed:** 2026-08-09
**Source:** Process-gap pair found by session `1d88885d`'s `hooks-override-auth` claim, 2026-08-09 (the incident: a commit landed on another session's feature branch, `feat/model-canary-probe-step25`, and had to be recovered by cherry-picking to main from a temporary worktree)
**Description:** Two commit-time blind spots. (A) BRANCH IDENTITY - the prescribed pre-commit checks (`git status`, `git log -1`) verify dirty state but not WHICH BRANCH will receive the commit, so a concurrent `git checkout` in the shared main checkout between the check and the commit is undetectable. (B) MEMORY STAMP - the harness maintains a memory file's `modified:` frontmatter only when the harness itself writes the file via Edit/Write, so a script/Bash write (python splice, sed, generated file) changes the body and leaves the stamp stale; hit twice in one session (`people.md` rewritten but stamped 2026-08-05; `projects.md` shipped in `570dd6f` stamped 2026-08-03).
**Evidence:** New file `hooks/commit-hygiene-guard.py` + `hooks/tests/test-commit-hygiene-guard.py` + a `settings.json` PreToolUse/Bash registration, landed ATOMICALLY in `399be31` (all three in one commit - a registration reaching the live checkout without the hook file makes `python <missing script>` exit 2, which for PreToolUse blocks every Bash call in every session; verified empirically during review). Merged `a7b48d5`, published `bbb4ec3`. Confirmed on the remote: `git show origin/main:hooks/commit-hygiene-guard.py` resolves, and `git show origin/main:settings.json | grep -c commit-hygiene-guard` = 1.
Tests: 44 in-file assertions, all fire/suppress paired (`python hooks/tests/test-commit-hygiene-guard.py`). The original incident is pinned by `D-A5b` (BRANCH CHANGED fires after a switch), `D-M1` (`cd <repo> && git commit` resolves the right repo) and `D-M2` (`git -C <repoA> commit` from repoB reports repoA's branch, not repoB's). Gap B is pinned by `B1`/`B4`/`B5`, `D-M3a`/`D-M3b` and `F-M5a`-`F-M5d`. Full hook suite at the pre-push gate: 75 pass, 0 fail, 1 env-skip.
Independent review: `pr-review-toolkit:code-reviewer` pinned to `claude-fable-5`, 5 rounds, VERDICT approved, artifact key `925b89d5`. Found 1 critical + 4 majors + 12 minors, all fixed or deliberately accepted with pinning tests. Two of the majors were regressions introduced by earlier fix rounds (a tokenizer that went blind to bare-newline separators; an add-path restriction that created four false negatives and was REVERTED rather than patched).
**Why `shared-checkout-guard.py` was not the fix:** the item as filed names that guard, but it is a PreToolUse hook on `Edit|Write|MultiEdit` and therefore never sees a Bash `git commit` at all - the branch check is structurally unreachable from it. `commit-provenance-guard.py` does run on Bash commits but reasons about WHICH FILES a commit sweeps up, not which branch receives them. Hence a new file rather than a change to either.
**Known residuals (accepted, warn-only - this hook never blocks):** renamed memory files are invisible (`--diff-filter=M` drops `R`); a staged-stale/worktree-fixed inversion is not detected; `git add <narrow-path> && git commit` warns about memory files the commit will not include (deliberately re-accepted after the restriction attempt failed silent, and pinned by test `E-m11a`); a quoted whitespace-free `#`-leading pathspec filename loses its pathspec and over-warns. All fail toward noise or silence, never toward blocking.
**Auto-check:** none.
### OI-136
**Status:** CLOSED 2026-08-28 (row flipped; already fixed as of `b1cbd0d` 2026-08-13, re-verified live this session: `python hooks/tests/test-git-prepush-hook-tests-gate.py` -> 146/146 pass, `record_override_use()`/`override_frequency()` confirmed present and wired)
**Opened:** 2026-08-12
**Severity:** HIGH
**Source:** `event_log.md` entries committed as `75ab0de` ("record 5 pre-push hook-test-failure overrides"),
cross-read against this session's own two *declined* overrides for the identical failure.
**Description:** `allow-hook-test-failure` has been normalised. On 2026-08-12 it was used **5 times across 4
distinct sessions inside a 47-minute window**:

| # | Session | Time (local) | Reason recorded in the token |
|---|---------|--------------|------------------------------|
| 1 | `d37e22c1` | 16:32:04 | sole failure is test-eos-review-gate.py exit 124 TIMEOUT, passes standalone |
| 2 | `b0e10e03` | 16:38:29 | both failures exit 124 TIMEOUT, never an assertion; passes in isolation |
| 3 | `e0f8485e` | 16:38:47 | load-induced timeout, not a defect; 55/55 in 145.9s outside the gate |
| 4 | `e89ddd24` | 17:03:00 | converging load flake across two retries (3 fail → 1 fail) |
| 5 | `e89ddd24` | 17:19:23 | same, second use by the same session |

**The finding is NOT a protocol violation.** Every token carries an explicit in-turn authorization, exactly as
`rules.md` requires; no session self-minted one. The control behaved as designed and was worn down anyway.
Three properties make that happen:
- **One cause, five approvals.** All 5 cite the same underlying failure — the load-induced pre-push timeout now
  reopened as [OI-057](#OI-057)/[OI-059](#OI-059). These were not 5 independent risk judgements; they were the
  same judgement re-approved 5 times because the gate kept re-asking.
- **The reasons converge to a script.** "Timeout not assertion / passes standalone / load flake" appears in all
  five. Once a justification is that reusable, the approval stops being a weighing and becomes a formality.
- **A false-blocking gate makes overriding rational.** When the gate is wrong, the operator who overrides is
  *correct* every time. That is precisely the training signal you do not want attached to a security control.

**Why this matters beyond the flake.** The property `allow-hook-test-failure` exists to protect is that a human
weighs a **real** test failure before it ships. Five-for-five on a known-benign flake trains the reflex to
approve on sight, and the next genuine failure — a real assertion, in `hooks/**`, in override or exit-code
logic — inherits that reflex. The gate's own docstring already warns that "an override normalised is a gate
disabled"; this item is the evidence that it happened.

**Not fixed by `c29ec95`.** Raising `PER_TEST_TIMEOUT_SECONDS` 90→240 removes *today's* trigger, which should
stop the bleeding. It does nothing about the mechanism: **nothing counts, rate-limits, or alerts on override
frequency**, and nothing distinguishes "5th override this hour for the same known flake" from "first override
this month for a novel failure". The `event_log` record is written *after the fact* and per-session, so no
session can see that three others already overrode the same failure in the last six minutes — sessions 2 and 3
were 18 seconds apart and each believed it was making a one-off call.

**Candidate fixes (not yet chosen):**
- A repeat-detector: hash the failing test-file set, and when the same signature is overridden N times in a
  rolling window, escalate the prompt — surface the prior approvals and their reasons rather than blocking.
- A visible counter in the gate's block message ("this failure has been overridden 4 times today by 3
  sessions"), so the approver weighs the pattern, not just the instance.
- Distinguish `exit 124 TIMEOUT` from assertion failures in the override *tier*, so a timeout override is
  cheap/logged and an assertion override stays expensive. Note this is a narrower change than removing the
  block, and does not reintroduce the per-file known-slow roster that OI-057 rightly rejects.
**Do NOT "fix" this by making the override harder to obtain** while the underlying gate still false-blocks —
that just converts a normalised override into a blocked engineer, and the 5 approvals above were each, on their
own merits, the right call.
**Auto-check:** none. Detection today is manual: grep `event_log.md` for "allow-hook-test-failure".
**Related:** [OI-057](#OI-057) and [OI-059](#OI-059) (the defect generating the overrides — both reopened
2026-08-12), `hooks/git-prepush-hook-tests-gate.py` (gate + the "override normalised is a gate disabled" note).

### OI-148
**Status:** CLOSED — LANDED on `main` 2026-08-13 as PR [#94](https://github.com/ZeOoba/ora-claude-config/pull/94), `25ac9ec`
**Opened:** 2026-08-13
**Source:** ECC repo intake ([external-artifact-intake](../../skills/external-artifact-intake) ruling,
Gabriel 2026-08-13)
**Auto-check:** none

`hooks/lint-config-guard.py` — a fail-closed guard (pattern: ECC's `config-protection.js`, adapted to
this codebase's own override-token contract) blocking silent edits to EXISTING `eslint.config.js` /
`tsconfig.json` / `tsconfig.node.json` / `functions/tsconfig.json` / `vitest.config.ts` /
`.prettierrc.json` in `oxford-command-center`. Scope ratified as occ-only.

Three rounds of independent adversarial review found and fixed: a `settings.json` routing gap
(`move_file`/`write_pdf` unrouted), the wrong integration pattern (moved into
`pretooluse-dispatcher.py`'s `GUARD_CHAIN`), a LIVE sandbox-confirmed shell quote-split bypass
(`ts''config.json`, fixed via ported `_dequote`/`_decaret`/`_shell_variants`), and a whole-command
worktree exemption narrowed to token-scoped (ported `_blank_exempt`). `eos-review-gate` verdict
recorded (approved, `claude-opus-4-8`).

**Evidence:** 26/26 own tests pass; shared `test-write-guard-coverage.py` meta-test green (4th
`GuardSpec` added, 16/16 shapes routed, no double-routing); cherry-picked cleanly onto a fresh
`origin/main`-based branch and re-verified there, not just on the dev branch, before pushing. Pushed
under a Gabriel-approved `allow-hook-test-failure` override — the pre-push block was
[OI-149](#OI-149) (an unrelated stale probe allowlist), not this diff.

**Documented, NOT fixed — an explicit follow-up rather than silently expanded scope:** `package.json`'s
own `lint`/`typecheck` script strings (`--max-warnings 0` etc.) achieve the same threat model with a
smaller diff, and are outside the ratified 6-file scope. Needs its own scoping decision from Gabriel.

### OI-287
**Status:** CLOSED — fixed same-session, before the row was ever filed
**Opened:** 2026-09-12 (id allocated by `ora-ground-truth-auditor`'s 2026-09-12 run via `allocate-oi-id.py`, per `maintenance/_state/oi-id-reservations.log`)
**Closed:** 2026-09-12
**Source:** `ora-ground-truth-auditor` 2026-09-12 digest / drafted correction at `maintenance/_state/ground-truth-pending-approval/2026-09-12/cc_ora-doctrine-integrity-guard_2026-09-12T16_55_00.000Z/correction-note.md` — the same root cause was independently diagnosed and fixed in a separate session earlier the same day while resolving an `ora-doctrine-integrity-guard` scheduled-run `[XREF-MISSING]` alarm, before the auditor's run reached its own OI-filing step
**Description:** `session-context-xref-probe.py`'s `search_roots()` omitted `maintenance/_state`, so `session-context.md:20`'s `retire-pending.json` citation raised a false `[XREF-MISSING]` (the file genuinely exists there — the retirement-pending ledger). The line-20 "PAUSED 2026-09-07" bullet was also itself stale per its own "delete once resume fires and block reads 36" instruction — the resume had already completed (manually, per [OI-273](#OI-273)) days earlier.
**Evidence:** Added `maintenance/_state/xref-extra-roots.json` (the probe's own pre-existing, documented extension point for citations outside its built-in search roots — no probe code touched) listing `maintenance/_state`; deleted the stale session-context.md line-20 bullet. Re-ran `session-context-xref-probe.py` -> exit 0, "19 file citation(s) checked", 0 `[XREF-MISSING]` (was 1). Re-ran `doctrine-integrity-probe.py` after the session-context.md edit -> still exit 0, confirming no regression. Logged same-session in `event_log.md` 2026-09-12 ("session-context-xref-probe [XREF-MISSING] false alarm fixed (probe root-coverage gap, not a missing file)"). Filed here CLOSED-on-arrival specifically so the auditor's independently-allocated OI-287 is not duplicated as a live fix task.

| [OI-270](#OI-270) | 2026-09-10 | CI on [ZeOoba/AAOS PR #5](https://github.com/ZeOoba/AAOS/pull/5) (run 34527574215) — surfaced by the CI added in [OI-259](#OI-259), on a **docs-only** commit | **CLOSED 2026-09-18 — fixed and merged.** The append-only event log lost records under concurrent writers: `_read_drain_lock_acquired` treated any lock-read failure as "stale," so a contender could archive a genuinely live drain lock and let two drainers fold the NDJSON from the same snapshot. Fixed and adversarially verified (two independent REFUTE passes, second NOT REFUTED) in [PR #8](https://github.com/ZeOoba/AAOS/pull/8), squash-merged `1b13606`. Full detail in the `### OI-270` section below |

### OI-270
**Status:** CLOSED — fixed and merged
**Opened:** 2026-09-10
**Closed:** 2026-09-18
**Severity:** HIGH — the append-only event log, which is the commit point of every transaction, loses records under concurrent writers
**Source:** CI on [ZeOoba/AAOS PR #5](https://github.com/ZeOoba/AAOS/pull/5), run 34527574215 — found by the CI workflow added in [OI-259](#OI-259)
**Evidence:** [ZeOoba/AAOS PR #8](https://github.com/ZeOoba/AAOS/pull/8) squash-merged to `main` as `1b13606` 2026-09-18T20:31:17Z, branch deleted. CI green on both matrix legs on the merged head ([run 35391689636](https://github.com/ZeOoba/AAOS/actions/runs/35391689636)).

**Description:** `tests/test_event_log_concurrency.py::test_concurrent_writers_lose_zero_events` spawns concurrent writers emitting 240 events, drains the spool to completion, and asserts every one reaches `aaos-events.ndjson`. On PR #5 it failed on **both** matrix legs:

```
test (3.11)  AssertionError: 234 != 240 : expected 240 NDJSON lines, got 234 (6 events lost to the append race)
test (3.13)  AssertionError: 232 != 240 : expected 240 NDJSON lines, got 232 (8 events lost to the append race)
```

`docs/GATE3-REVIEW.md` had recorded this exact failure mode (two near-simultaneous direct appends to `aaos-events.ndjson` silently clobbering each other) as Critical and **fixed** by the spool-file + `O_EXCL` drain-lock mechanism in `_aaos_common.py`; this result said the guarantee did not hold under real contention. `commit_state_change` treats the event write as the commit point of every transaction, so a lost event is lost evidence a transaction happened. Intermittent and contention-dependent (passed 5/5 locally in isolation; CI's real 2-core parallelism exposed it — same signature as [OI-264](#OI-264)). Not caused by the commit that surfaced it (`598ef51` touched only a docs file).

**Root cause.** `_read_drain_lock_acquired` returned `None` on ANY read failure, and `_try_acquire_drain_lock` treated `None` as "stale." Under contention the commonest failure is `FileNotFoundError` — the incumbent released between a contender's failed exclusive-create and its read. The contender then "archived the stale lock" with a path-based `os.replace`, moving whatever sat at the path *by then*: a third drainer's live lock. Two drainers fold the NDJSON from the same snapshot; the later `os.replace` clobbers the earlier fold's lines, whose spool files are already moved to `_drained/`, so no later drain could recover them. Linux-only in practice: `os.replace` there succeeds regardless of open handles, where Windows's steal usually dies on a sharing violation — every recorded occurrence was ubuntu-only for that reason.

**Evidence gathered.** 400-run observe-only repro (8 writers × 30 events) on `ubuntu-latest` ([CI run 35389532700](https://github.com/ZeOoba/AAOS/actions/runs/35389532700), py 3.11 + 3.13): pre-fix 64/200 runs (32%) lost events, every lossy run showed a live-lock steal and zero without one, 475/475 lost events found sitting in `_drained/` (folded, then clobbered) — never in `_corrupt/`, never left pending. Post-fix: 0/200 steals, 0/200 losses, both Pythons.

**Fix.** `_read_drain_lock_acquired`/`_try_acquire_drain_lock`: `FileNotFoundError` on the lock read means released, not stale — archive nothing, retry the create; any other `OSError` means age unknown — fail closed on a fresh lock, fall back to the lock file's own mtime (compared against the real wall clock, never an injected `now`) so a crashed drainer's persistently unreadable lock still unwedges after `_DRAIN_LOCK_STALE_MINUTES`; a pending file vanishing under a held drain lock now warns loudly instead of the prior "benign timing quirk" read. Deterministic forced-interleaving tests added (no reliance on CI's scheduler) plus a tripwire in the existing test: nothing can be legitimately stale in a seconds-long run, so any lock-archive attempt is a proven steal. Scope confined to the event-spool functions — no edit to `acquire_lease`/`archive_lock`/`assert_lease_held` (OI-265/267 territory, both in flight in separate worktrees, confirmed disjoint before starting).

**Adversarial REFUTE pass (Fable tier, independent, mandatory for commit-point code) — two passes, second NOT REFUTED.** First pass found the targeted race genuinely closed (every revert-mutant killed) but caught one flaw the fix itself introduced (mtime fallback compared against the caller's injected `now` instead of the real clock — fixed same day) plus test gaps (fixed same day, mutants re-run and killed) and three pre-existing defects filed separately rather than folded in: [OI-314](open-items-tracker.md#OI-314) (clock-mixing in the `acquired` stamp itself, plus the steal/release of a genuinely-stale lock staying path-based), [OI-315](open-items-tracker.md#OI-315) (`splitlines()` vs U+2028/U+0085), [OI-316](open-items-tracker.md#OI-316) (undelimited event-id concatenation). Second pass (independent, same tier), on the claim narrowed to "agreeing clocks, no crash/no >5min drain ⇒ never a second drainer": NOT REFUTED — 241/241 tests after one more pinning test for a surviving mutant, F2 fix confirmed closed via 3 scenarios incl. real clocks, 16/17 mutants killed cleanly on first re-run, 15 consecutive runs clean on Windows. One residual noted as outside the narrowed claim's premise, same class as [OI-314](open-items-tracker.md#OI-314): the unreadable-lock mtime fallback trusts filesystem mtime, so a >5min clock-skewed seam-root host could still misjudge a fresh-but-unreadable lock.

**Related:** [OI-264](#OI-264) (same "green locally, red under CI contention" signature, in the lock protocol rather than the event log), [OI-259](#OI-259) (the CI that surfaced this), [OI-314](open-items-tracker.md#OI-314)/[OI-315](open-items-tracker.md#OI-315)/[OI-316](open-items-tracker.md#OI-316) (sibling defects filed separately from the REFUTE pass, not fixed here).

### OI-187
**Status:** CLOSED
**Opened:** 2026-08-17
**Closed:** 2026-09-21
**See:** the `## Closed` table above for the write-up and evidence (Corporate folder ALTA statement for 3034 Westerville Rd).

### OI-192
**Status:** CLOSED
**Opened:** 2026-08-17
**Closed:** 2026-09-21
**See:** the `## Closed` table above for the write-up and evidence (2014 deed of conversion); residual moved to [OI-336](open-items-tracker.md#OI-336) #27.

### OI-188
**Status:** CLOSED
**Opened:** 2026-08-17
**Closed:** 2026-09-21
**See:** the `## Closed` table above; the open work continues in [OI-335](open-items-tracker.md#OI-335).

### OI-348
**Status:** CLOSED
**Opened:** 2026-09-22
**Closed:** 2026-09-22
**Source:** oxford-command-center PR [#357](https://github.com/ZeOoba/oxford-command-center/pull/357) review (2026-09-14 ora-financial-code-integrity-sweep remediation, this session) — filed and closed same-day, re-filed directly as CLOSED per the [OI-157](#OI-157) precedent (allocated at filing time via `allocate-oi-id.py`, but the tracker row itself was never written until the fix landed). Moved from `open-items-tracker.md` to this history file 2026-09-22 (checker false-positive cleanup, this session) — a CLOSED item filed after the 2026-09-06 Closed-table split belongs here per that split's own convention, same as [OI-287](#OI-287).
**Severity:** HIGH at filing (imminent portfolio-wide alert blackout), resolved before it ever fired.
**Description:** PR #357 widened the AR dead-lease guard (`server/ar/**`) so a zero-rent-but-Active lease routes to human review instead of auto-refreshing on each PM export re-feed. Two real leases hit this: Evans Gymnastics (Northwood A15, temporary — tenant replaced 2026-10-01, confirmed by Gabriel) and Tyson Consulting Group (29000 Information Lane #202, permanent — Gabriel ruled the $0 rent correct 2026-09-18). Both carry real, aging AR balances ($1,824.01 and $6,063.09) last refreshed 2026-08-21. Once #357 merged, neither record could auto-refresh again, and `src/analytics/conditions.ts`'s AR collections-alert staleness gate (`arStalenessMaxDays: 35`) was ALL-OR-NOTHING — a single stale/unresolvable `tenantArrears` record suppressed per-lease collections alerts for **every** lease in the portfolio, not just the stale one. Without a fix, either record crossing 35 days stale (~2026-09-25) would have blinded all AR alerting portfolio-wide, including unrelated leases with fresh 60+-day-critical delinquencies.
**Fix:** oxford-command-center PR [#360](https://github.com/ZeOoba/oxford-command-center/pull/360) (merged) made the staleness gate per-lease — only the stale lease's own alert is withheld, every other lease evaluates normally on its own fresh record; the aggregate `ar-stale` notice now reports which leases are affected instead of implying a blackout. Follow-up PR [#361](https://github.com/ZeOoba/oxford-command-center/pull/361) (merged) closed the same gap in `renewalSignals()` (`src/analytics/lease-forecast.ts`), which independently asserted freshness-dependent renewal-likelihood claims ("current on rent", a specific at-risk dollar figure) from the same stale records.
**Evidence:** Both PRs adversarially reviewed (independent Fable-pinned pass, not the implementing session) before merge — #360's review included a 2000-random-portfolio differential fuzz test plus 12 hand-built adversarial cases (all-stale, all-fresh, stale-with-$0-total, orphan records, legacy unstamped records) asserting the new alert set is always a superset of the old and no stale-derived alert ever leaks; #361's review independently re-derived the Evans/Tyson-shaped fixtures rather than trusting the implementer's report, and traced `likelihood`'s only downstream consumer (`server/warehouse/capital-allocation.ts:1146`) to confirm a stale-gated `'uncertain'` result is treated as neutral, never worse than a real signal. `npm run test` green on both (5238 and 5250 tests respectively) at merge time. Both leases now correctly route to human review with no downstream alert suppression outside their own row.
**Residual, not part of this item:** a minor reference-date inconsistency between #360's wall-clock `now` and #361's workbook `referenceDate()` basis (can diverge staleness judgment by up to a day at the 35-day boundary) was found during #361's review and documented as a follow-up in that PR's description — not filed as a separate OI, low severity, no live incident.
