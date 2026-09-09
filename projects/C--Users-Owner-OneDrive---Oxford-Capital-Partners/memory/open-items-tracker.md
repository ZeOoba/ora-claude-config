---
name: open-items-tracker
description: "Single canonical open-items / punch-list tracker for the ORA system — one entry per open/residual/TODO item across memory, fleet, and repo state. Other files POINT here; item text lives in exactly one place. CLOSED items and their detail sections live in the companion open-items-tracker-history.md (split 2026-09-06, Automation Audit R22-4) — same anchors, new file."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 1624855d-d36d-4c3e-9761-0250482b1d31
  modified: 2026-09-08T13:48:18.000Z
---

**Purpose:** every open/residual/TODO item anywhere in the ORA system (memory files, `oxford-cc-repo-health.md`-style incident writeups, `event_log.md` follow-ups, fleet punch lists) gets exactly ONE row here. Other files reference an item by pointer — `[open-items-tracker.md#OI-003](open-items-tracker.md#OI-003)` — and never restate its description, evidence, or status inline. A restated copy is the thing that rotted in the 2026-07-16/17 incident (see [[event_log]] and [[oxford-cc-repo-health]]): a forward-pointer to `session-context.md` "carrying the live list" went dead the instant that file's content moved on, because the item text lived in two places and only one of them got updated when the item closed.

**Why a new file, not an existing one:** checked against [memory-policy.md](memory-policy.md)'s fixed 13-doc set first. `ops_decision_log.md` is the closest existing candidate but is scoped to *already-decided* yes/no operational questions (one row per resolved question, answer never changes shape); this tracker is scoped to items with a *mutable open→closed lifecycle* that need to be found and closed, not re-derived. Different purpose, so a new file is the "real new domain" memory-policy.md requires before adding to the set.

## Convention

- **ID:** `OI-NNN`, zero-padded, monotonic, never reused. The ID lives on its own `### OI-NNN` header line so the anchor is stable (`open-items-tracker.md#OI-NNN`) — do not put the title on the header line itself.
- **Fields per item:** `Status` (OPEN / CLOSED), `Opened`, `Closed` (if closed), `Source` (the file/incident that raised it — link, not restated text), `Description` (one line), `Evidence` (closure only — what was actually checked, not "should be fine"), and an optional `Auto-check` line (see below).
- **Pointing in:** any other memory file that wants to mention this item links to `open-items-tracker.md#OI-NNN` and says nothing else about it — no paraphrase, no "as of DATE it's still open," nothing that can drift out of sync with the row here.
- **Closing an item:** flip `Status` to CLOSED, add `Closed:` date and `Evidence:` (what was mechanically checked, with the command/tool used), move it to the Closed table below. Never delete a row (append-only in spirit, same as `event_log.md` — a closed item stays as a record).

### Auto-check (optional, machine-checked)

An OPEN item may carry a single-line `**Auto-check:**` field in a small closed vocabulary that `memory-integrity-probe.py` can evaluate against live `fleet-status.py --json` output — no arbitrary code execution, just a bounded comparison against the dual-fleet scheduled-task registries:

- `kind=registry_disabled_count fleet=<cc|lams|all> expect=<N>` — the count of `enabled:false` tasks in that fleet must equal N for the item to read as resolved.
- `kind=registry_field_equals fleet=<cc|lams> task_id=<id> field=<cron|enabled> expect=<value>` — a named task's field must equal the given value.

When an OPEN item's auto-check matches, the probe emits a WARN (report-only, never auto-closes — a human still confirms and flips the status) on its next scheduled run (`ora-health-guard`, daily 05:15, or `ora-cc-schematic-refresh`, twice weekly). The probe also flags any `open-items-tracker.md#OI-NNN` reference elsewhere in `memory/*.md` whose ID doesn't resolve to a row here (dead pointer) — that one fails hard (matches the existing "orphan index link" severity), since a dead pointer into this file is exactly the failure mode this tracker exists to prevent. Detail: `~/.claude/maintenance/memory-integrity-probe.py`.

## Open

| ID | Opened | Source | One-line |
|----|--------|--------|----------|
| [OI-249](#OI-249) | 2026-09-09 | `dirty-tree-triage` run, this session (allocated via `allocate-oi-id.py`) | **MEDIUM-HIGH (structural, blast-radius files repeatedly caught in the churn) — the primary `~/.claude` checkout has never switched its HEAD back to `main` since reflog entry `2aae684` ("moving from main to feat/model-canary-probe-step25"), so it keeps re-accumulating large uncommitted backlogs on a long-lived feature branch instead of tracking `main` directly.** 3rd known occurrence of the same shape: [[project_primary_checkout_main_move_blocked_2026-08-12]] (117 dirty files, 19 ahead/48 behind, ruled unsafe to force-switch — 15+ sessions' WIP intermingled), cleared 2026-08-16 (6 dirty, 4 behind) **without ever moving HEAD off the branch**, `feat/model-canary-probe-step25` itself merged to `main` 2026-08-23 (45 commits, `efcd876`) **again without a HEAD switch**, and now (this session's `dirty-tree-triage` scan) back up to **97 dirty entries, 40 commits behind `origin/main`**. Root cause, not just recurrence: the mitigation that actually ran each time was `Merge origin/main into feat/model-canary-probe-step25` (visible in reflog/log, e.g. `c730328`) — a merge-forward that never requires a checkout switch — so the branch became a permanent stand-in for `main` on this checkout by default, and nothing enforces the merge-forward on a cadence; it only happens when some session's git housekeeping happens to include it, so 20-40-commit gaps accumulate silently between runs. No proactive detection exists either — all 3 occurrences were found by accident during unrelated triage/audit passes, never alarmed. Candidate fixes (not applied — this is a standing-doctrine change, needs Gabriel's call): (a) a scheduled/periodic supervised `merge origin/main into <branch>` sync task so drift never exceeds a few commits; (b) actually complete the deferred switch to `main` once the tree is genuinely clean, and stop treating the feature branch as the checkout's permanent identity; (c) a lightweight probe (alongside `doctrine-integrity-probe.py`/`governor-drift-probe.py`) that WARNs when the primary checkout has sat on a non-`main` branch, or been >N commits behind `origin/main`, for more than a set window. `dirty-tree-triage` itself correctly left the 97-file set untouched (out of its scope — branch-level divergence, not dirty-file triage; per its own boundary and this file's 08-12 precedent, no checkout/reset/rebase on the shared tree) — **PROGRESS 2026-09-09: (c) implemented, (a)/(b) deliberately deferred.** Investigated all three same session: (a) and (b) both require a git operation (merge-forward or checkout switch) on the live, currently ~100-file-dirty, actively-edited primary checkout — out of scope for an unattended/same-session change under the shared-checkout single-writer doctrine, and (b) in particular is the thing that has silently "resolved" this twice already without fixing the underlying default. (c) had no git-state risk, is pure detection, and directly closes the actual observed gap (found by accident 3/3 times, never alarmed) — implemented in `cross-repo-wip-scan.py` (already the wired-in, weekly-run home for this repo-set's staleness checks, via `ora-weekly-hygiene` Block I): a `CANONICAL_BRANCH` map (currently only `~/.claude` → `main`) flags `[ACTION] BRANCH_DRIFT` when current branch ≠ canonical, or ≥10 commits behind `origin/<canonical>`, or the count is undeterminable (treated as uncertain, never silently clean) — commit `41f4bac`, 44/44 tests passing (12 new, real local-remote git fixtures, no mocks). Verified live against the real checkout: correctly reports 84 commits behind at time of commit. Remains OPEN because the underlying drift itself is NOT fixed, only now alarmed — (a) vs (b) is Gabriel's call once the checkout is next genuinely clean enough to attempt either safely — **PROGRESS 2026-09-09 (2): (a) implemented and registered, Gabriel's explicit pick over (b).** `maintenance/checkout-merge-forward.py` (commit `63748d9`, 28/28 tests against real local-remote git fixtures) refuses to run if the index has anything staged (the exact cross-session hazard hit twice this same session), fetches read-only, and either lands a clean `--no-commit --no-ff` merge + commit, fully `git merge --abort`s back to the pre-merge state on a real textual conflict, or no-ops when git refuses upfront on dirty-tree overlap (the ordinary case here) — never a partial/stuck state. Smoke-tested live against the real checkout: correctly returned `BLOCKED_DIRTY_OVERLAP` and left the tree untouched (verified via MERGE_HEAD absence). Registered as `ora-checkout-merge-forward` (daily 16:45 ET, CC/MCP fleet, commit `fcf9b46`) via `register-scheduled-task`'s `create_scheduled_task` MCP tool — surface asserted native/CC per that skill's Rule 3, claims `sched-repo-housekeeping` per its step 3c, model-tagged. Registered `enabled:false` and folded into `ora-routine-pause-resume-2026-09-11` as item 37/37 to respect Gabriel's standing 2026-09-07 fleet-wide pause (resumes with everything else 2026-09-11 16:01 ET) rather than fire mid-pause. Both (a) [corrector, daily] and (c) [detector, weekly] are now live; OI-249 stays OPEN only until the corrector's first live MERGED result confirms it actually closes drift in practice, not just in tests |
| [OI-248](#OI-248) | 2026-09-08 | Independent review during the OI-228 follow-up fix (PR pending), this session | **LOW — `hooks/eos-review-gate.py`'s `REVIEWER_MODEL_LADDER` has no Mythos-class entry at all (any generation), so a reviewer that genuinely ran on Mythos would be rejected by the commit gate the same way Fable 5.1 was before PR #176.** Flagged, not fixed — may be deliberate (Mythos is described as a limited-access program) rather than an oversight; needs a ruling, not a silent addition |
| [OI-247](#OI-247) | 2026-09-08 | `repo-housekeeping` claim (session `ebc44356`, 2026-09-07T11:36:19) on `CLAUDE.md`; verified by a separate session monitoring for the promised PR | **MEDIUM (process, blast-radius file) — a CLAUDE.md tie-break fix landed by bypassing the exact process its own claim promised, and now sits on a branch already tracked as blocked from reaching main.** The claim said "via worktree off origin/main + PR"; the dedicated worktree (`.claude/worktrees/claude-md-tiebreak`, branch `fix/claude-md-exception-scan-tiebreak`) has **zero commits**, still 0 ahead of `origin/main`, 14 behind as of filing. The actual fix (adding `automation-health-monitor` to the Exception-scans tie-break line) instead landed **directly in the live checkout**, bundled inside commit `b95cef1` — titled "docs(governance): require a real review verdict on blast-radius PRs; retire Qodo skills", which never mentions it. Pushed to `origin/feat/model-canary-probe-step25` (0/0 ahead-behind) but **absent from `origin/main`**, confirmed by direct `git show`. See detail section |
| [OI-244](#OI-244) | 2026-09-07 | ORA Automation Audit Rev 23, T4 spec-cost thread (2026-09-06) | **MEDIUM (recurring token cost) — `ora-health-guard`'s 16,482-word daily-firing spec has no changelog extraction, unlike its sibling `ora-pm-ledger`, which had its 13 dated build-history sections extracted 2026-09-06 for a measured ~171K tokens/month saving.** A heading skim of `ora-health-guard` found no comparable extractable block — its bulk reads as live per-run procedure, not narrative history — so this needs actual content review to find the lever, not a mechanical cut-and-paste of the `ora-pm-ledger` fix. Half of R23-13's fleet-spec-cost finding; the `ora-pm-ledger` half is done, this half is not |
| [OI-243](#OI-243) | 2026-09-07 | ORA Automation Audit Rev 23, T5 gap-analysis thread (2026-09-06) | **MEDIUM (knowledge loss, ~1 deal/week) — `deal-decision-ledger` expects `deal-retirement` to write pass/kill reasoning into it, but `deal-retirement` is not name-loadable on this surface (unpublished from the skill store 2026-08-05, repo-path-only), so five rows read "reason not logged elsewhere — reconcile manually."** Pass reasoning is being lost at roughly one deal a week, and it is exactly the raw material [OI-241](#OI-241)-adjacent lost-deal calibration work needs. Fix is either re-publishing `deal-retirement` by name or repointing `deal-decision-ledger`'s write path to the repo-path invocation `ora-weekly-hygiene` already uses |
| [OI-242](#OI-242) | 2026-09-07 | ORA Automation Audit Rev 23, T5 gap-analysis thread (2026-09-06) | **LOW-MEDIUM — lost-deal calibration data is written to the ledger and never consumed downstream.** 511 Industrial Mile (ORA's only priced LOI loss, $1.575M won vs. ORA's $1.45M) sits with its Walk price ($930K) below the actual offer made, so Loss Class is held UNCLASSIFIED — see [[reference_511_industrial_mile_duplicate_rows_and_walk_offer_conflict_2026-08-16]]. The broader pattern: nothing reads the ledger back into buy-box calibration, so a real pricing-loss signal has no feedback loop |
| [OI-241](#OI-241) | 2026-09-07 | ORA Automation Audit Rev 23, T5 gap-analysis thread (2026-09-06) | **LOW-MEDIUM — `deal-flow-triage`'s own description declares the Outlook inbox as its input source, but its `allowed-tools` only grants `Read, Grep, Glob`, which cannot reach an Outlook mailbox.** The skill cannot execute the workflow it advertises. Its file-ingestion half already overlaps `ora-om-intake-ocr`. Either grant it real inbox access or retire it in favor of the overlapping skill |
| [OI-240](#OI-240) | 2026-09-07 | ORA Automation Audit Rev 23, T5 gap-analysis thread (2026-09-06) | **MEDIUM (sourcing pipeline, ~50 letters/week with no feedback loop) — `owner-outreach`'s own guardrail states it is T1-only, and T2-T4 rendering is pending an input Gabriel never supplied, so weekly cold-outreach letters ship with no response capture and no mechanism for the ratified "top 5-8/week" call slice.** Gabriel's own words on this, quoted in the audit: "the sequencing layer is the actual unlock." Highest-value item in the T5 gap list by the audit's own ranking |
| [OI-239](#OI-239) | 2026-09-05 | `ora-ar-feed-sweep` 2026-09-02 run + follow-up investigation 2026-09-05 (oxford-command-center @ `428bd54`) | **HIGH (money + suppressed monitoring) — a tenant who PAYS vanishes from the next delinquency export, but every `tenantArrears` write path is a spread merge, so the paid row keeps its balance AND its `asOfDate` forever; because `conditions.ts`'s staleness gate degrades on the WORST record, a few long-paid tenants hold `ar-stale` on and suppress ALL per-lease collections alerting portfolio-wide.** Live: 7 rows stamped 2026-07-15 ($19,152.40, 52 days) suppressed alerting across 37 fresh 2026-08-21 rows. **Fix v2 built and green** on branch `fix/ar-stale-row-reconcile` (`server/ar/reconcile-covered.ts`, 25 tests, 3850/3850 suite green). **v1 was WRONG and would have destroyed money** — an adversarial refute pass broke it with executed repros ($18,333.71 zeroed at 1100 Rarig incl. a $12,380.94 review-queue row; $39,474.16 at the 8-building Sepich propertyId) and falsified its self-healing rationale. v2 closes both. NOT LANDED: `scripts/ar-import-headless.ts` held by another session. **v2 deliberately does NOT fully clear `ar-stale`** — 3 rows at 9050 Red Branch ($13,355.08) are refused as a partial-export shape and need a human ruling or a newer report |
| [OI-238](#OI-238) | 2026-09-05 | `ora-appsec-sweep` 2026-09-05 (oxford-command-center @ `af514a0`, security-auditor dispatch) | **LOW-MEDIUM — `@xmldom/xmldom@0.8.13` (via `mammoth`) carries GHSA-6gmq-8vp8-gcm6 (fragment injection on serialize), fixed at `>=0.8.15`, not covered by [OI-209](#OI-209)'s advisory set.** Reachability: moderate — `.docx` files under `DOCUMENTS_DIR` are parsed by `mammoth` during `index:docs`; the corpus is semi-trusted (business documents), not fully untrusted. Worth folding into OI-209 as an addendum on its next touch rather than tracking separately long-term. Not applied |
| [OI-237](#OI-237) | 2026-09-05 | `ora-appsec-sweep` 2026-09-05 (oxford-command-center @ `af514a0`, security-auditor dispatch) | **MEDIUM — AR delinquency workbooks (16 `.xlsx` under `data/ar/processed/`) and `data/ar-mapping-cache.json` (37 tenant business names) are committed to the repo; the `.gitignore` entry for the cache file is inert because it was already tracked before the rule was added, and the text-based confidentiality scanner cannot see inside `.xlsx` binaries at all.** Same "ignore doesn't apply to already-tracked files" trap as [OI-118](#OI-118). Candidate fix: `git rm --cached data/ar-mapping-cache.json`; evaluate untracking the 16 xlsx files; extend the scanner to unzip and check OOXML `sharedStrings.xml`/`document.xml` rather than treating `.xlsx`/`.docx` as opaque. Not applied |
| [OI-236](#OI-236) | 2026-09-05 | `ora-appsec-sweep` 2026-09-05 (oxford-command-center @ `af514a0`, security-auditor dispatch) | **MEDIUM — `scripts/prepush-confidential-scan.mjs` fails OPEN (warns, allows the push) when the confidential-terms roster is absent/unparseable or diff computation errors, contradicting the repo's own fail-closed doctrine for the confidentiality gate.** Distinct from [OI-227](#OI-227) (the hook *installer* silently no-installing when `tsx` is missing) — this is the scan's own error handling once it does run, on the one repo (S-001) whose private-repo confidentiality exception depends on this gate actually blocking. Candidate fix: fail closed on roster-load/diff-computation failure, with a loud documented override env var; add a regression test. Not applied |
| [OI-235](#OI-235) | 2026-09-05 | `ora-appsec-sweep` 2026-09-05 (ora-pm branch `feat/offhost-monthly-billing-backup`, pushed to origin, off pinned SHA; security-auditor dispatch) | **MEDIUM — [OI-229](#OI-229)'s PR #24 backup workflow (`monthly-billing-backup.yml`) duplicates `CRON_SECRET` into GitHub Actions secrets and adds a `workflow_dispatch` trigger with free-form year/month inputs, outside the ratified dual-fleet scheduled-task registry.** Widens the blast radius of the secret gating real ACH confirms and lets any collaborator/compromised GH token re-trigger billing for an arbitrary historical period. Candidate fix: constrain `workflow_dispatch` to the current period (derive server-side, not as an input) and register the trigger + secret location per `register-scheduled-task`'s dual-fleet model before merging PR #24. Not applied |
| [OI-234](#OI-234) | 2026-09-05 | `ora-appsec-sweep` 2026-09-05 (ora-pm @ `ca62ecb`, security-auditor dispatch) | **MEDIUM — the delinquency/late-fee cron (`cron.ts:496-519,529-540`) fires on ANY lease carrying a charge older than 30 days regardless of whether the tenant's CURRENT balance is actually overdue, so a tenant inside the grace period or already paid can still be assessed a wrongful $50 late fee.** Adjacent to but distinct from [OI-229](#OI-229) (missing off-host backup trigger for this same cron — a different problem). Candidate fix: gate the fee condition on the lease's current unpaid balance via `ar_ledger`, not merely charge age; add a regression test. Not applied |
| [OI-233](#OI-233) | 2026-09-05 | `ora-appsec-sweep` 2026-09-05 (ora-pm @ `ca62ecb`, security-auditor dispatch) | **MEDIUM — `server/routes/stripe.ts:172-224` confirms the Stripe PaymentIntent (real ACH debit) before the ledger insert; if that insert fails for any reason OTHER than the OI-035 dedupe unique-constraint, the confirmed debit has no ledger row and no compensating record.** Same "money moved, correctness assumed a guarantee that isn't enforced" class as [OI-222](#OI-222)/[OI-223](#OI-223); OI-035's unique index absorbs a *duplicate* insert but not a *failed* one. Candidate fix: write a `pending` row keyed by `client_request_id` before calling Stripe, update with the PI id after; have the webhook upsert-by-PI when no row matches. Not applied |
| [OI-232](#OI-232) | 2026-09-05 | `ora-tenant-hubspot-reconciliation` follow-up, 2026-09-05 — root-causing [OI-216](#OI-216) shape 2 | **LOW (corrected same day from HIGH — read the MATERIAL CORRECTION block in the entry before acting).** The Master Workbook's Bakers Specialty row was updated 2026-09-02 from a real executed addendum (08/31/2026, all three parties). The original finding — 4 wrong fields, rent understated $703.80/yr — **is withdrawn**: checking the three sibling shape-2 rows established that the roll's convention is `Monthly Rent` = rent in effect *now*, `Escalation Date` = when it next changes, `Escalation %` = the step applied then, which DELVAL, Sky Shield and Hoodz all confirm exactly. Under it only **one** Bakers field is wrong — `Escalation %` `0.035` vs the implied `0.036864` — worth **$2.95/mo**. Two things survive: Bakers' `Monthly Rent 1591.35` still doesn't reconcile to its own lease lineage, and (new, also affects Hoodz) a single `Escalation %` field cannot carry both a one-time renewal step and the 3% recurring rate, so every escalation after the next one is modelled wrong. |
| [OI-231](#OI-231) | 2026-09-05 | `ora-tenant-hubspot-reconciliation` monthly run, 2026-09-05 (root-cause of the [OI-220](#OI-220) corrections) | **MEDIUM — this task's tenant-name match reports "absent from the system of record" when it means "no name match found," and produced 3 fabricated absence findings in the 2026-09-02 run.** P.U.P.S, Green Home Solutions and MO Dept of Agriculture were all filed as missing from Notion and/or the workbook; all three are present under fuller legal names (`P.U.P.S Dog Obedience Training, LLC`, `Greeen Home Solutions (Mueller)` — a deliberate 3-`e` spelling — and `State of Missouri, Department of Agriculture`). A HubSpot `dealname` carries a short trading name; both other systems carry registered entity names. Step 3c has no fallback (property+unit, or Tenant ID) and no distinction between a verified and an inferred null. |
| [OI-230](#OI-230) | 2026-09-05 | `ora-tenant-hubspot-reconciliation` monthly run, 2026-09-05 (Step 3c — WATCH, sync gap) | **WATCH — Grails TCG, LLC is an active workbook tenant at 2203-2207 Northwood Dr suite A3 (lease start 2025-10-15, `leaseEnd 2029-08-31`, `status Active`) with NO row of any kind in the Notion Tenant DB, live or retired.** It is the tenant the workbook puts in the suite Notion assigns to Sky Shield, so it is the missing third party in the A3/A4 conflict at [OI-217](#OI-217) — and was already present in the snapshot the 2026-09-02 run read, so this is a reporting gap in that run, not new data. No HubSpot Lease Renewal deal exists for it either. |
| [OI-229](#OI-229) | 2026-09-03 | `register-scheduled-task` v2.19 step 3b applied to the live fleet; Automation Audit Rev 21 R21-2/R21-4 | **MEDIUM — `ora-pm-daily-crons` posts late fees and has NO off-host backup trigger (`offhost-backup: none — GAP`); ora-pm PR #24 covers monthly billing only.** Extend the GitHub Actions backup to the two daily endpoints, or accept the gap explicitly. |
| [OI-222](#OI-222) | 2026-09-02 | `ora-appsec-sweep` 2026-09-02 (ora-pm @ `ca62ecb`, security-auditor dispatch) | **MEDIUM — a Stripe webhook event that throws on first processing is permanently dropped, not retried.** The event id is inserted into `stripe_webhook_events` *before* processing; a transient failure marks the row `failed` and returns 500, Stripe retries, the retry's insert hits `23505` and short-circuits to `{skipped:true}` 200 — the retry is discarded and the row never re-processes. Can leave a real ACH payment stuck `processing` (balance overstated) or a `charge.dispute.created` uncounted (balance understated). Not applied |
| [OI-223](#OI-223) | 2026-09-02 | `ora-appsec-sweep` 2026-09-02 (ora-pm @ `ca62ecb`, security-auditor dispatch) | **MEDIUM — the outstanding-balance cap on `/api/payment-intent` ignores pending/processing ACH, so a tenant can pay the same charges twice.** `ar_ledger.balance` only credits `stripe_status='succeeded'`; during the 3-5 business day ACH `processing` window the portal still lists the charges as payable and the cap still passes since the balance hasn't moved yet. Not applied |
| [OI-224](#OI-224) | 2026-09-02 | `ora-appsec-sweep` 2026-09-02 (ora-pm @ `ca62ecb`, security-auditor dispatch) | **MEDIUM — the admin manual-payment route's schema allows `method:'ach_stripe'` with no `stripe_status`, producing rows the ledger never counts but the admin UI shows as paid.** `PaymentInsertSchema` doesn't restrict `method` to `check`/`wire`/`other` despite the route comment saying it should; such a row has NULL `stripe_status` so `ar_ledger` (which only sums `succeeded`) excludes it while `GET /api/payments`/admin PaymentsList display it as a recorded payment. Related but distinct from [OI-082](#OI-082) (missing uniqueness on non-Stripe methods, a double-counting bug in the opposite direction). Not applied |
| [OI-225](#OI-225) | 2026-09-02 | `ora-appsec-sweep` 2026-09-02 (oxford-command-center @ `d30d71e`, security-auditor dispatch) | **MEDIUM — the AI agent's tool results can carry confidential-deal identifiers to the Anthropic API with no redaction, unlike every other egress path in the repo.** `get_deals`/`search_entities` correctly drop `confidential:true` rows, but `get_alerts`/`evaluateConditions` and `get_relationships` do not, and `agent.ts` appends tool results verbatim into the outbound `messages` with no pre-send scan — while `comps.ts`, `om-extract.ts`, and `narrative.ts` all fail closed on the same egress. Asking "any deadlines?" with a confidential deal in an alert-eligible stage sends its name/detail to api.anthropic.com. Not applied |
| [OI-226](#OI-226) | 2026-09-02 | `ora-appsec-sweep` 2026-09-02 (oxford-command-center @ `d30d71e`, security-auditor dispatch) | **MEDIUM — the agent can self-mint the human-only "architect ack" override sentinel, unlocking edits to governed files without a human in the loop.** `file-guard.mjs` releases protection on `server/index.ts`, `src/contracts/**`, migrations, etc. when `.claude/overrides/architect-edit-ok` is fresh (60-min TTL), but `bash-guard.mjs`'s `GUARD_PATH` doesn't cover `.claude/overrides/` or `mkdir`/`touch`-shaped writes, so the agent can create the sentinel itself. Compounded by `Bash(npx tsx:*)` being pre-approved, which reaches governed files via `fs` outside the Edit/Write tools the file-guard intercepts. Not applied |
| [OI-227](#OI-227) | 2026-09-02 | `ora-appsec-sweep` 2026-09-02 (oxford-command-center @ `d30d71e`, security-auditor dispatch) | **LOW — the git pre-push hook installer silently no-ops when `tsx` is absent, leaving a checkout with no confidentiality scan on push.** Flagged under the sweep's mandatory item-3c hook-change check: `scripts/install-git-hooks.ts`/`prepare-hooks.mjs` (commit `3d4de2a`) moved the installer to `.ts`-via-`tsx`; when a checkout is built with `npm ci --omit=dev`, `tsx` is missing and `prepare-hooks.mjs` exits 0 without writing the pre-push hook at all — no warning. The scan logic itself (`prepush-confidential-scan.mjs`, commit `ead629d`) is unchanged and was independently assessed non-weakening (structurally strengthened, in fact). Not applied |
| [OI-228](#OI-228) | 2026-09-02 | `ora-appsec-sweep` 2026-09-02, DISPATCH INTEGRITY GATE assertion 4 (post-hoc model-floor probe) | **LOW — tooling defect, not a real floor breach: `check-dispatch-model-floor.py`'s `MODEL_RANK` table doesn't recognize `claude-fable-5-1` (the current Fable 5.1 model id) and ranks it UNKNOWN (fail-closed, -1), firing exit 1 on both this sweep's subagents even though each ran 100% on Fable with zero fallback events — the best possible outcome, not a violation.** `MODEL_RANK` only has bare `claude-fable-5`/`claude-mythos-5`; the table appears to predate the Fable 5.1 rollout. Verified directly: `agent-ae4ff02601b0e1cdb.jsonl` (ora-pm, 62 msgs) and `agent-ae7f6e4c49d408b89.jsonl` (occ, 110 msgs) both show `model:"claude-fable-5-1"` on every line, 0 fallback blocks. Distinct from [OI-052](#OI-052) (the documented fable→opus mid-run fallback pattern, ruled compliant) — this is a false-positive FAIL from a stale id mapping, not a fallback of any kind. Per the sweep's own doctrine this still had to be recorded and escalated (never silently loosen the assertion), but the fix here is adding `claude-fable-5-1`/`claude-mythos-5-1` (rank 100) to `MODEL_RANK`, not touching the floor logic. Not applied |
| [OI-213](#OI-213) | 2026-09-02 | `ora-tenant-hubspot-reconciliation` monthly run (this task) | **ELEVATED — Heritage Pool Supply's exercised renewal option (2026-04-26) is documented in Notion and the workbook but the HubSpot deal still carries the superseded 2026-09-30 expiration in `appointmentscheduled`.** Notion's own row is RETIRED as a duplicate and names the canonical record and the correct date; `portfolio.json` independently says `leaseEnd 2031-09-30, Active`. Recommend `dealstage` → `closedwon`, `closedate` → `2031-09-30`. Detection-only — not written |
| [OI-214](#OI-214) | 2026-09-02 | `ora-tenant-hubspot-reconciliation` monthly run (this task) | **ELEVATED (Step 3d escalation — a correction that propagated to two systems and not the third) — Maryland Hospital Association's HubSpot deal still carries `2027-06-30`, the exact value Notion's own note records as disproven and replaced by `2027-05-31` on 2026-07-21.** `portfolio.json` agrees with the corrected date. Deal is already `closedwon`, so the wrong date is now baked into a closed record. Recommend `closedate` → `2027-05-31`. Detection-only — not written |
| [OI-215](#OI-215) | 2026-09-02 | `ora-tenant-hubspot-reconciliation` monthly run (this task) | **ELEVATED (Step 3d escalation, reverse direction) — the Notion Tenant DB row for J&R ENTERPRISES still carries Lease Expiration `2026-07-31`, a date now 33 days in the past, while HubSpot and the workbook both agree on `2026-12-31`.** This is the same tenant named in this task's own 2026-07-25 Step-3d precedent; the drift has since inverted — HubSpot is now correct and Notion is the stale system. Recommend correcting **Notion**, not HubSpot. Detection-only — not written |
| [OI-216](#OI-216) | 2026-09-02 | `ora-tenant-hubspot-reconciliation` monthly run (this task) | **DATE-MISMATCH — 7 of 37 open HubSpot Lease Renewal deals carry a `closedate` that disagrees with the workbook-derived `portfolio.json` `leaseEnd` for the same property+unit+tenant.** Two distinct shapes, not one: 3 where Notion sides with the workbook against HubSpot (Medspeed, Robert & Kesha Best, The Companies LLC) and 3 where Notion sides with HubSpot against the workbook (Sky Shield, Hoodz of Delmarva, DELVAL EQUIPMENT), plus Heritage Pool Supply ([OI-213](#OI-213)). Two of the seven have a `closedate` that has **already elapsed**. Not adjudicated — a HubSpot `closedate` can legitimately be a renewal decision date, so each row is a question, not an assumed HubSpot error |
| [OI-217](#OI-217) | 2026-09-02 | `ora-tenant-hubspot-reconciliation` monthly run (this task) | **MEDIUM — suite A3/A4 at 2203-2207 Northwood Dr is claimed by two different tenants across two systems of record.** Notion puts Sky Shield in Suite A3 and Carlton L. Handy in A4; `portfolio.json` puts Sky Shield in A4 and carries no lease row for Carlton L. Handy at all. The two systems also disagree on Sky Shield's expiration by nearly three years (2026-09-30 vs 2029-08-31), so the unit conflict and the date conflict may share a root cause. Neither record adjudicated |
| [OI-218](#OI-218) | 2026-09-02 | `ora-tenant-hubspot-reconciliation` monthly run (this task) | **WATCH (Step 3b) — CJ's Tint Shop's lease expired 2026-08-31 (two days ago) with no renewal, vacate, or holdover signal in any system.** All three sources agree on the date — HubSpot `closedate` 2026-08-31 still in `appointmentscheduled`, Notion Lease Expiration 2026-08-31 / Lease Status `Active`, `portfolio.json` `leaseEnd 2026-08-31` / status `Expiring Soon` — and none of them records what happened. Notion's Notes field is empty. **No outcome inferred**: this is a question for Gabriel, not a finding |
| [OI-219](#OI-219) | 2026-09-02 | `ora-tenant-hubspot-reconciliation` monthly run (this task) | **IDLE (Step 3e, the standing monthly sweep for the population [OI-021](#OI-021)'s batch pass confirmed was legitimately not-yet-due) — 6 deals sit in `appointmentscheduled` 37–159 days untouched with lease expirations 210–2,524 days out.** The more useful signal is the denominator: **every one of the 37 open deals is 37+ days idle** — the newest `hs_lastmodifieddate` anywhere in the open pipeline is 2026-07-27, so the whole renewal pipeline has been quiet since that batch. Flag-only; the stage disposition is Gabriel's call |
| [OI-220](#OI-220) | 2026-09-02 | `ora-tenant-hubspot-reconciliation` monthly run (this task) | **WATCH (Step 3c) — 4 tenants are missing from at least one system of record.** P.U.P.S Dog Training has an open deal 28 days from its own `closedate` but exists in **neither** Notion nor the workbook; Green Home Solutions has no Notion row (the workbook has "Green Home Solutions of Pickerington"); Carlton L. Handy has a Notion row but no workbook lease; MO Dept of Agriculture was closed won on a state renewal letter in July yet still appears in neither. Naming/sync gaps — which record is right is not guessed |
| [OI-221](#OI-221) | 2026-09-02 | `ora-tenant-hubspot-reconciliation` monthly run (this task), Step 8 Property Register cross-check | **LOW-MEDIUM — the Property Register's `Market` cross-check is structurally unenforceable: 135 of 138 live Tenant DB rows have a blank `Market`.** Step 8 exists to catch property/market attribution churn mechanically (added after the 2026-07-21 Columbus OH / Salisbury MD regression), but with 97.8% of the tenant side empty the Market half of that check can never fire. Property Address is well populated by contrast (0 blanks across the same 138 rows), so the check currently runs on one leg only |
| [OI-207](#OI-207) | 2026-08-24 | Found while fixing the AR review-queue false pointer — oxford-command-center PR [#296](https://github.com/ZeOoba/oxford-command-center/pull/296), `~/.claude` `6d9ab38` | **LOW-MEDIUM — `data/ar/review-queue.json` is write-only and has no resolver.** The documented matcher-fix loop (fix `server/ar/resolve-by-unit.ts` → copy the source back from `data/ar/processed/` → re-run the headless importer) only covers rows a matcher rule CAN fix. Rows no rule can ever resolve — tenant absent from the snapshot, dead/vacated lease — have no path at all. Gabriel ruled docs-only (option b) in-turn 2026-08-24; the resolver is the deferred option (a). Qodo's review of #296 independently reached the same call and added a better design: persist a source pointer per queued row + a replay command, removing the manual copy-back step. Not closed by `fix/ar-unit-parenthetical` (`4e496b1`), which fixes one instance, not the class. Trigger to build: the first genuinely unmatchable row in a real sweep |
| [OI-204](#OI-204) | 2026-08-22 | Session close-out knowledge candidate, code-review remediation round on `acquisition-underwriting-eval-harness` | **LOW-MEDIUM — governor-constant duplication is now a 3-way cross-repo pattern, not 2-way.** DSCR floor (1.25x) and YoC/LTV governor constants are hardcoded independently in at least three places: `maintenance/governor-drift-probe.py` (the dedicated drift guard), `acquisition-underwriting/SKILL.md` prose (the buy-box narrative), and now `acquisition-underwriting-eval-harness/lib/diff_verdict.py` (confirmed live in this session's remediation diff, third recurrence of the same defect class). Each copy can drift independently and `governor-drift-probe.py` only watches the first two. Needs a follow-up: either a single source-of-record constant the eval-harness imports/reads rather than restates, or an explicit third watch-target added to the drift probe so a future change to the eval-harness copy doesn't silently diverge from the other two. Not fixed here — filed per CLAUDE.md's close-out convention rather than left as a skipped review finding |
| [OI-203](#OI-203) | 2026-08-21 | `dirty-tree-triage` on ora-skills `_staging/repo-first-rescue/` + `session_outputs/lease-addendum.skill`, Gabriel-directed follow-up | **FIXED (repo) 2026-08-21 — `claim_work.py` process gap: the claim step is never invoked, not broken.** `dirty-tree-triage` step 7 now requires `claim_work.py claim ora-skills-housekeeping` alongside its existing `git log -1`/`git status` check — commit [`4e44f72`](https://github.com/ZeOoba/ora-skills/commit/4e44f72), `ora-skills` v1.1, Gabriel-directed. **Not yet installed on the platform account** — the pre-commit hook auto-synced the AppData mirror and logged the skill to `ora-skills/_staging/PENDING_REIMPORT.md`; a session still reading the old `~/.claude/skills/synced/dirty-tree-triage/` copy (rather than the repo) won't see the new step 7 language until a `package-and-stage-skill` re-upload lands. Evidence for the gap itself:  Two sessions were independently handed the same ora-skills `_staging` triage today and both did the full investigation; one archived the result and logged it to `event_log.md` moments before this session's own archive `mv` ran — caught only because the `mv`'s source had already vanished, and confirmed by `event_log.md`'s `modified:` stamp predating this session's attempt by ~4 min. `hooks/active-work/*.json` held zero claims for this task at investigation time (only stale, unrelated ones) — neither session ran `claim_work.py claim ora-skills-housekeeping`/`repo-housekeeping` before starting, despite the module's own docstring citing a near-identical 2026-08-12 ora-skills precedent ("two sessions were handed the same remediation prompt and both started work; the second caught it only by reading the first's session transcript, ~15 minutes in") as the reason the module exists. Distinct from [OI-166](#OI-166) (fixed 2026-08-16, a bug WITHIN the claim mechanism — didn't check other slugs' claims): this is zero adoption of the mechanism, since neither session invoked it at all. `session-context.md` doesn't surface this either — it's a hand-curated standing-doctrine digest (last touched 2026-08-17), not an event_log mirror, so a one-off collision like this has no standing surface pushing sessions toward the claim step. |
| [OI-202](#OI-202) | 2026-08-21 | Repo-architecture-review remediation, Code session picking up the handoff | **MEDIUM - model-driven one-time scheduled task stalled silently mid-run.** `ora-routine-pause-resume-08-21` fired at its scheduled time but only executed the first 2 of 35 `update_scheduled_task(enabled:true)` calls in its instruction list before stopping - no error, no partial-progress marker, and it never reached its own step-6 summary email (confirmed absent from `send-log.txt`). Completed the remaining 33 re-enables manually this session. **General-case detection fix landed 2026-08-21 (same day, follow-on session)** — see the item body's second Progress note: `task-progress-marker.py` + a `register-scheduled-task/SKILL.md` v2.13 authoring convention, wired into the existing `ORA Fleet Pause-Resume Guard` native task. Remains OPEN because the ORIGINAL stall's root cause is still not diagnosed and the fix is opt-in (doesn't retrofit existing one-time tasks). |
| [OI-196](#OI-196) | 2026-08-17 | Tax & Settlement systemization sprint (Cowork session, project "Taxes + Settlement Statements"); gap-check pass on the Code handoff | **LOW — flag only, needs OneDrive/preparer access, not repo work.** No Form 4562 / asset-level depreciation schedule on file for 1100 Rarig Ave LLC (TY2025), Muirkirk Properties LLC (both years), or Fairground Village Center LLC. A preparer request is drafted in the Cowork project but not sent — outbound send needs Gabriel's in-turn confirmation and Code has no send path for it regardless |
| [OI-195](#OI-195) | 2026-08-17 | Tax & Settlement systemization sprint (Cowork session, project "Taxes + Settlement Statements"); gap-check pass on the Code handoff | **LOW — flag only, needs a county re-pull, not repo work.** 7658 Fishel's "TY2024" tax screenshot duplicates the TY2023 bill verbatim — the true TY2024 figure is unconfirmed. Needs a fresh Franklin County Auditor pull, not another read of the same screenshot |
| [OI-194](#OI-194) | 2026-08-17 | Tax & Settlement systemization sprint (Cowork session, project "Taxes + Settlement Statements"); gap-check pass on the Code handoff | **LOW — flag only, needs a document request, not repo work.** Fenton Street LLC's TY2025 Maryland return is an image scan with no text layer — cannot be transcribed programmatically. An extension coupon shows $3,925 due, confirming a filing exists; the actual return still needs to be sourced as a text-layer or OCR'able copy |
| [OI-193](#OI-193) | 2026-08-17 | Tax & Settlement systemization sprint (Cowork session, project "Taxes + Settlement Statements"); gap-check pass on the Code handoff after a concurrent session scoped its own work to skill-authoring only | **LOW — active memo has a $200K arithmetic error.** `Business\Cost Seg Study Claude\2026-07-28_CostSegDispositionPortfolio_Memo_v02.docx` Table 1 prints a portfolio 5/7-year personal-property total of $1,660,155; the six property rows actually sum to $1,860,155 — the memo's own narrative ($4.39M reclassified = $1,860,155 + $2,529,416) supports the larger figure, not the printed total. Table 2 prints $1,820,260 against a column sum of $1,820,262. Any prior use of Table 1's total is understated by $200,000. Found during the 2026-08-17 Tax & Basis Register cross-foot. **Do not edit the memo** — it's in a non-Claude Oxford OneDrive business folder (write needs Gabriel's permission); flag and let him correct it |
| [OI-192](#OI-192) | 2026-08-17 | Tax & Settlement systemization sprint (Cowork session, project "Taxes + Settlement Statements"); gap-check pass on the Code handoff | **LOW-MEDIUM — basis chain-of-title gap.** 5600 Sunnyside's 1992 title was taken by Gerald D. and Carol R. Goldberg individually; the 02/2025 seller of record is `5600 Sunnyside, LLC`. At least one intervening conveyance between 1992 and 2025 is undocumented in the settlement corpus — resolve the missing link before relying on the $513,304.55 1992 basis figure in BASIS_REGISTER. Needs title/county-recorder research, not another OCR pass |
| [OI-191](#OI-191) | 2026-08-17 | Tax & Settlement systemization sprint (Cowork session, project "Taxes + Settlement Statements"); gap-check pass on the Code handoff | **MEDIUM — unsupported basis-of-accounting change.** 1100 Rarig Ave LLC's TY2024 federal return carries a $217,346 §481(a) adjustment with no Form 3115 on file. $211,981 of it ties exactly to the cost-seg memo (80% bonus depreciation on $264,976 of reclassified assets); the remaining $5,365 is unexplained. An unfiled 3115 behind a claimed 481(a) adjustment is audit exposure — confirm with the preparer whether the 3115 was filed and simply not retained, or never filed |
| [OI-190](#OI-190) | 2026-08-17 | Tax & Settlement systemization sprint (Cowork session, project "Taxes + Settlement Statements"); gap-check pass on the Code handoff | **MEDIUM-HIGH — 1031 deferral may be misstated.** The 07/02/2024 settlement conveys three parcels (5333 Secor Rd, 3347 McGregor Lane, 5242 Angola Rd) as one exchange leg; Form 8824 for the 2024 exchange names only two, omitting McGregor. If McGregor sits outside the realized-gain computation the return relied on, the $2,078,790 deferral claimed on the 8824 is misstated. Needs preparer/8824-workpaper review to confirm whether McGregor was folded into the gain math off-form or genuinely dropped. Companion related-party/boot gap for the same exchange: [OI-188](#OI-188) |
| [OI-189](#OI-189) | 2026-08-17 | Tax & Settlement systemization sprint (Cowork session, project "Taxes + Settlement Statements"); gap-check pass on the Code handoff | **MEDIUM — $1.8M capitalized with no land allocation.** 1100 Rarig Ave LLC's entire $1,803,121.50 settlement debit total was capitalized to buildings/depreciable assets on Schedule L — no land basis was ever established. The settlement cross-foots exactly against its own printed totals, so this is a booking decision, not a transcription artifact; land is non-depreciable, so the current depreciation schedule overstates the depreciable base. Needs an assessor land/improvement ratio or appraisal split to correct, per `settlement-basis-extraction`'s standing flag category for this pattern (same defect independently found at 401 Sunburst, Dorchester County SDAT Land Value $0) |
| [OI-188](#OI-188) | 2026-08-17 | Tax & Settlement systemization sprint (Cowork session, project "Taxes + Settlement Statements"), handed to Code for `settlement-basis-extraction` skill authoring | **LOW-MEDIUM — data gap, no historical record.** 2203-2207 Northwood has no historical tax record anywhere in the `Property Taxes Historical` OneDrive tree (10 property folders scanned, this the only fully empty one). Same property behind the $75,011 recognized-boot / related-party 1031 gap in the 2026-08-17 Tax & Basis Register (seller AND lender both `2900 Loch Raven LLC`, ~$2.8M) — confirm whether that's an ORA affiliate before relying on any 1031 treatment for this parcel; if so, IRC §§267, 1239, and 1031(f) all engage. Needs a live county-portal pull, not a repo-side fix |
| [OI-187](#OI-187) | 2026-08-17 | Tax & Settlement systemization sprint (Cowork session, project "Taxes + Settlement Statements"), handed to Code for `settlement-basis-extraction` skill authoring | **LOW-MEDIUM — data gap, blocks basis + 1031 work.** 3034 Westerville Rd's ALTA settlement table is 0% legible — the entire table failed OCR during the 2026-08-17 Tax & Basis Register build, and a repeat OCR pass on the same scan won't fix a bad source image. Blocks both basis work (CHARGE_DETAIL/BASIS_REGISTER can't populate for this transaction) and the 1031 Exchange Chain Register's Westerville row. Needs a clean copy from title/counsel, not another OCR attempt |
| [OI-186](#OI-186) | 2026-08-17, **RETRACTED as duplicate 2026-08-17** | Investigating the pre-push NOI large-drift gate (3 properties failing, this session) — filed without first grepping the tracker for prior art | ~~MEDIUM — portfolio-wide data staleness~~. **Duplicate of [OI-137](#OI-137)**, independently re-derived 5 days later, same 3 properties, same root cause — should have been caught by a tracker search before filing. **Also overstated a claim never checked against data already in hand:** "the other 9 are equally stale and will start tripping it too" — false as stated. The full cross-check's own per-property output (already captured, never re-read before writing that line) shows only 3 of the other 11 properties show ANY drift at all (29000 Info Lane 5.09%, 3540 E 5th 8.37%, Sepich Portfolio -6.76%, all WARN-tier, none within striking distance of the 20% gate), 5 are in-tolerance (≤3.8%), and 2 are structurally not comparable (`lease-run-skipped`). Staleness is real and portfolio-wide (confirmed: every property's full-year `import_batches` row shares the identical `2026-06-13T19:52:51.1xx` timestamp, one single backfill never refreshed since); its CONSEQUENCE is not — it only shows up as large drift where real 2025→2026 tenancy change also occurred, which is a small minority of the portfolio. **The one genuinely new fact this item added to OI-137** (kept, not duplicated): no fresher P&L source files exist anywhere in `Business/Property Financials/` to backfill from — verified directly, only the same June-12-dated exports already ingested — so a `warehouse:backfill` re-run right now would be a no-op. Folded into OI-137's entry rather than carried as a separate row |
| [OI-184](#OI-184) | 2026-08-17, widened 2026-08-17, root-caused 2026-08-17, **MERGED 2026-08-17/18 ([PR #285](https://github.com/ZeOoba/oxford-command-center/pull/285), `e29dc49`→`fa27d4c`)** | Working the P4 AR review queue; widened + root-caused investigating the NOI cross-check drift; fix went through 5 rounds of the `refute-financial-change` adversarial pass (this session) | **RESOLVED.** Root cause: `resolvePropertyId` (`server/workbook/parse.ts`) tokenized an address and matched each token as a raw SUBSTRING against every property's address, first-match-wins, in array order — `"3034 Westerville Road"` includes `"road"`, a literal substring of `"B-ROAD-way"` in `"1900 N Broadway, Baltimore MD"`, pure spelling coincidence. Both real Westerville leases (Buckeye's Best Transport $13,005/mo, Lamar Advertising billboard $300/mo) were mis-tagged to Baltimore as a result. First fix attempt (a street-suffix denylist, `b8e868c`) closed only that one word; the mandatory refute pass caught real order-dependence and city-token-hijack defects on LIVE data (round 1), then progressively caught defects in each rewrite across 4 more rounds (numeric-veto too strict/too loose, missing score floor, a length-filter bug dropping 1-2 digit house numbers, generic-word/city-word-plus-coincidental-number collisions) — full history in this session's transcript. **Final mechanism** (`e29dc49`): whole-token equality (not substring) + a house-number range gate (candidate disqualified if its own leading number doesn't cover the key's) + a distinctiveness requirement (at least one matched word must be non-generic and non-city, unless that word is also the property's own street name) + fail-closed ties. Round 5 (5/5 lenses, worst severity LOW) confirmed via exhaustive/fuzz verification (167k+30k+20k permutations) that no wrong-match is constructible against the live 14-property/17-key corpus; remaining gap classes (an off-sheet property sharing a common word + coincidental number; comma-less addresses; abbreviation-variant duplicate rows) are all disclosed, fail-safe (miss, not mis-tag) residuals needing a different mechanism (an explicit alias/crosswalk table), not further denylist rounds — logged as follow-up, not filed as a new OI yet. 21 tests. Verified pre-merge against the real live workbook + real warehouse DB: 0 errors portfolio-wide, Westerville correctly downgrades to structural-mismatch/warn with $159,660/yr corroborating rent (exactly Buckeye's + Lamar's combined annual rent). CI (`gate` + `refute-required`) both passed. **One disclosed residual not yet closed:** the tracked snapshot mirror `data/snapshots/portfolio.json` still carried the pre-fix Westerville→Baltimore tag as of merge (the worktree couldn't safely regenerate it without `NOTION_TOKEN`) — self-corrects via the existing `ora-cc-snapshot-refresh` scheduled task (3x/weekday); worth a one-line confirmation next time that task's output is checked |
| [OI-185](#OI-185) | 2026-08-17 | Working the P4 AR review queue (this session) | **LOW — silent-staleness gap.** `appendReviewQueue()` in `scripts/ar-import-headless.ts` is append-only across sweeps: it dedupes new rows against existing ones but never removes a row once that tenant later resolves (e.g. via a newly-seeded cache mapping + a subsequent sweep). Found live 2026-08-17: after seeding 5 confirmed mappings and re-running, 5 of the review queue's 8 rows were stale — already written to `tenantArrears` — while the file still listed them as needing a human map. Pruned by hand this session (exact tenant+sourceFile match, verified against `tenantArrears` ground truth first). Needs a prune-resolved-rows step added to the sweep itself so a human working the queue never acts on a stale entry |
| [OI-180](#OI-180) | 2026-08-16 | P1 owner-outreach engine build (this session); quota exhaustion observed live | **MEDIUM — metered dependency can halt weekly outreach.** `ora-owner-outreach-queue-refresh` STEP 0 pulls Notion suppression via `notion-query-data-sources` **SQL mode**, which is quota-metered on this plan — the workspace exhausted it mid-session on 2026-08-16 (second query refused). The gate is deliberately fail-closed, so a quota refusal means **no pack is built that week**. Correct trade (a skipped week beats mailing a suppressed owner) but it makes a metered external service a single point of failure for outreach throughput. Fix: **view mode is quota-free on every plan** per the tool contract — create a "Suppressed" view on data source `caa809b7` filtered to `DNC` checked OR `Cadence Status ∈ {Responded, Parked, Converted, Do-Not-Contact}`, and switch STEP 0 to `mode: view`. One SQL query/week is normally fine, so this is hardening, not a live outage |
| [OI-173](#OI-173) | 2026-08-16 | Reservation by session `27ca10f9`; row filed 2026-08-16 by the P4 session to close an orphan (id reserved, code written, row never written) | **LOW — built, unmerged, and carrying an undocumented coverage edge.** `maintenance/spec-liveness-probe.py` exists (daily, report-only, never blocks) — but it is **untracked in the main checkout** (`??`) and lives only on the unmerged branch `oi173-spec-liveness-probe` (`fe5f056`), so `git ls-files` cannot find it and a reader may conclude it was never built. Two follow-ups: (1) land the branch; (2) add a docstring line recording that its edge is spec-vs-live-data, so a capability with **no fleet spec at all** is outside it by construction — that is how `server/ar/` sat complete-but-never-run with no alarm (see [[reference_ar_subsystem_exists_but_dark_2026-08-16]]). Note deferred rather than written in place: the file is another session's uncommitted WIP |
| [OI-177](#OI-177) | 2026-08-16 | P4 capability audit (PM data reconciliation session) | **LOW — data gap.** `property_master` in `oxford-command-center/data/warehouse/finance.sqlite` holds 14 rows but **9510 Persimmon Tree Rd is absent entirely**, while `1851-s-club-solar` occupies a row despite being a solar project, not a property. So the table is 13 real properties + 1 non-property, against a 14-property portfolio. Any per-property sweep keyed on `property_master` silently skips Persimmon and may double-count Solar. Found while confirming the PM regime registry (`property_manager` column), which is otherwise correct and corroborated Gabriel's self-managed ruling |
| [OI-178](#OI-178) | 2026-08-16 | P4 capability audit; hazard documented in the source itself, unfixed | **MEDIUM — silent mis-attribution.** `oxford-command-center/server/ar/mapping-cache.ts`'s `cacheKey()` deliberately KEEPS entity suffixes because `normalizeTokens()` would collapse `Apex LLC` and `Apex Inc` to one key — and the cache-hit branch **skips review entirely**, so a collision silently attributes one tenant's delinquency to another's lease across import runs. The comment names the hazard; nothing guards it. Becomes live the moment the AR feed runs (see [[reference_ar_subsystem_exists_but_dark_2026-08-16]], P4 Phase 0) |
| [OI-179](#OI-179) | 2026-08-16 | P4 capability audit | **LOW — schema violation, contained.** `Business/Master Lease Database/_pipeline/output/TENANTS.json` contradicts its own `README.md`: the README declares `r` = monthly rent and `m` = market (`MD\|OH\|MO…`), but `r` is actually annual rent per SF and `m` is monthly rent — verified `sf × r ÷ 12 == m` in 140/145 rows, and `m` is a float in **145/145**, never a market string. Any consumer filtering by market matches nothing; any consumer reading `r` as monthly rent understates ~833×. Contained because `_pipeline` feeds only a standalone HTML dashboard; fix belongs with its retirement, not ad hoc |
| [OI-175](#OI-175) | 2026-08-16 | Surfaced while closing [OI-163](#OI-163) (AAOS Cowork round-trip closure, this session) | **LOW** AAOS's `COWORK-BOOTSTRAP.md` Probe X (`validate.py` subprocess) requires `jsonschema>=4.18` (`Draft202012Validator`); the 2026-07-10 Cowork session that ran it hit an ImportError, `pip install`-fixed it session-locally to reach `MODE=SAFE-BY-HAND`, then filed [[task t-cowork-jsonschema-pin-952743]] noting the fix is non-durable (no pinned manifest exists for Cowork sandboxes to install from, and neither AAOS's git tree nor its seam-mirror `contracts/` is in Cowork's `write_scope` to self-patch). Blocks Cowork ever reaching `MODE=FULL-EXEC` parity with Code until fixed. Fix: add a pinned dependency manifest under `C:/Users/Owner/AAOS/` + an install-before-Probe-X step in `COWORK-BOOTSTRAP.md` §2, republish `contracts/`, then lease/complete `t-cowork-jsonschema-pin-952743` |
| [OI-171](#OI-171) | 2026-08-16 | Found while root-causing Gabriel's report of the Command Center `loans · name` safety-section flag | **MEDIUM — self-masking alert.** `ora-cc-snapshot-refresh` STEP 5(b) escalates to email on any data-quality flag `severity: warn` or higher — but the one permanent, intentional flag (`loans · name`, the tombstoned Loan Index row 24 duplicate marker) was bumped `info`→`warn` in oxford-command-center `490d89f` (2026-08-11) ~21h before the snapshot task's own severity gate (`1706bc2`, 2026-08-12) was written around the stale `info` belief — so every clean, no-drift run has sent a false `[ALERT]` since. **Status: FIXED 2026-08-16** in the live SKILL.md + registry — **UNVERIFIED** until the next run (2026-08-17 ~06:21 ET) actually suppresses the email; see full section |
| [OI-166](#OI-166) | 2026-08-16 | Concurrency near-miss during the passed-deal-tracker guard session (Gabriel-directed) | **FIXED 2026-08-16** — `claim` consulted only its OWN slug's file, never whether a live claim under a DIFFERENT slug already covered the same `--paths`. Two sessions held `open-items-tracker` and `repo-housekeeping` over the same two files; neither exit-3 refusal could fire. `claims_touching()` already existed and was wired into `shared-checkout-guard`'s Edit/Write path, but not into `claim` itself. See detail section |
| [OI-167](#OI-167) | 2026-08-16 | Same session; 5 read-only Bash calls blocked in one session | **MEDIUM — FILED, NOT FIXED, deliberately.** `config-write-guard.py` blocks pure READS whose command text pairs a governance path with a write-shaped token (`2>&1`, `--write-tree`, `<<<<<<<`, `\|\|`, `printf`). Documented as breadth-over-precision and **must not be narrowed** — [[feedback_autonomy_gate_matcher_cannot_be_safely_narrowed]] logs FOUR narrowing attempts that each found a real bypass. The sanctioned escape (run the worktree copy) failed here because the worktree was deleted mid-session ([OI-169](#OI-169)). Overlaps live work by session `6797e01b` on the same false-positive class |
| [OI-168](#OI-168) | 2026-08-16 | Same session; first push died at 120s | **LOW** the `~/.claude` pre-push gate (86 hook tests + full doctrine probe + 8 sweeps) exceeds the Bash tool's default 120s timeout. The push had done all its work and was killed at the wire; `git ls-remote` was needed to establish whether the ref moved. Not a repo defect — a mismatch between gate runtime and default client timeout. Fix direction: document the required timeout, or split the gate's slow sweeps behind a fast path |
| [OI-169](#OI-169) | 2026-08-16 | Same session; own worktree emptied mid-task | **MEDIUM** a git worktree (`.claude/worktrees/wizardly-hamilton-626cbd`) was emptied to 0 entries by another session while still checked out and in active use, breaking every tool path resolving through it — including `hooks/lib/claim_work.py`, the sanctioned escape hatch for [OI-167](#OI-167). Worktree cleanup does not check whether a session is live in the tree it is removing |
| [OI-170](#OI-170) | 2026-08-16 | Root cause of the whole passed-deal-tracker guard session (Gabriel-directed) | **FIXED 2026-08-16** — the scheduler resolves a registry `filePath` against the LIVE WORKING TREE, so a SKILL.md can be merged in git and still inert on disk. `ora-passed-deal-tracker`'s double-fire guard sat merged-but-inert for hours with zero hits in the live file. `task-folder-registration-probe.py` checked filePath EXISTENCE but never CONTENT-vs-git. See detail section |
| [OI-163](#OI-163) | 2026-08-16 | Cross-repo architecture-diagram review (Gabriel-directed, this session); corroborates [[project_aaos_agent_coordination_layer]] | **CLOSED 2026-08-16** — the round-trip had actually happened 2026-07-10 (a real Cowork handoff + drained event, verified via `tools/validate.py` → VALID); the gap was Code never running `complete-task.py`. Leased/completed/archived `t-cowork-seam-confirm` this session. See detail section |
| [OI-164](#OI-164) | 2026-08-16 | Cross-repo architecture-diagram review (Gabriel-directed, this session); related [OI-142](#OI-142) | **MEDIUM** ora-skills' git repo and the Cowork AppData runtime cache are two independently-writable copies of every skill, reconciled only by after-the-fact drift detection, not prevented structurally. README documents 3 same-session cache-ahead drifts (2026-08-04); OI-142's zero-commit install is another instance of the same root cause. Fix direction: point Cowork's skill import at the git source directly if the platform allows it, removing the second copy rather than diffing it better |
| [OI-165](#OI-165) | 2026-08-16 | Cross-repo architecture-diagram review (Gabriel-directed, this session) | **CLOSED 2026-08-16** — `netlify.toml` build command now chains `build-kb.mjs && build-dist.mjs`; verified locally end to end, Gabriel-confirmed past the site-tree gate. See detail section |
| [OI-161](#OI-161) | 2026-08-15 | Investigation of OI-137/OI-143's orphaned sections (Gabriel-directed, this session) | **Recurring authoring-gap**, distinct from OI-160's merge-loss mechanism: a batch-filing commit writes a full `### OI-NNN` detail section but never adds the matching Open-table row — 2 independent instances found (OI-137 via `1cfbc3c`, OI-143 via `7463e48`), both invisible to the Open table since filing (2026-08-12/08-14) until this session's audit |
| [OI-143](#OI-143) | 2026-08-12 | Surfaced while root-causing [OI-137](#OI-137); split out because materially wider than that cross-check | **MEDIUM** `server/workbook/parse.ts:403` coalesces a missing/unparseable expense cell to a real `0`, indistinguishable from a genuine zero — the [[feedback_verified_null_vs_inferred_null]] failure mode. For 4 of 14 properties `Property.noi` is silently gross income, not NOI; DSCR impact real but no governor breach (3540 E. 5th's true margin ≈ half the reported 1.48, still above 1.25x floor); also feeds valuation (Livingston's $1.31M cap value nets no opex). Fix proposed (nullable `expenses` + `DataQualityFlag`, matching `insurance.ts`'s existing convention) — not built. Row lost to a merge-conflict silently orphaning its `### OI-143` section; restored 2026-08-16, no status change |
| [OI-137](#OI-137) | 2026-08-12, **FIX LANDED 2026-08-17** | Control run while verifying [PR #268](https://github.com/ZeOoba/oxford-command-center/pull/268)'s test failures were pre-existing; re-confirmed against `origin/main` at `c5db68c`; fix landed same day as an independent re-derivation of this exact item (OI-186, retracted as duplicate — see below) | **MEDIUM-HIGH, mostly resolved.** `npm run reconcile:noi-crosscheck`'s Spine A (workbook, current rent roll) vs. Spine B (warehouse `oxfordNoi`, latest-full-year historical actuals) disagreement was root-caused to recently-leased/acquired properties whose comparison-year actuals predate the current rent roll — "neither spine is defective." **Fixed in `680018f`** (Gabriel, in-turn ruling): `classifyNoiReconciliation` gained a `structural-mismatch` status — fires only on positive, corroborated evidence (leases starting on/after the comparison period covering ≥half the dollar delta, or an acquisition since then plus some corroborating leasing activity), gated off entirely on any sign-inverted disagreement. Adversarially reviewed; 3 real gaps found and closed (uncorroborated ownership signal, `Lease.status` not checked, CLI summary miscounting). 57 tests (24 new), full suite 3672/3672. **Verified live 2026-08-17:** Livingston and Raytown now correctly downgrade to `structural-mismatch`/warn (no longer fail the gate); Westerville stayed large-drift/error until [OI-184](#OI-184)'s propertyId fix — **[OI-184](#OI-184) MERGED 2026-08-17/18 ([PR #285](https://github.com/ZeOoba/oxford-command-center/pull/285)), all 3 originally-failing properties now clear, 0 errors portfolio-wide**, confirmed by re-running the cross-check against the real warehouse DB with the merged fix applied. `gate:ci` still excludes this check by design (needs a live workbook/warehouse) |
| [OI-160](#OI-160) | 2026-08-15 | Investigation of the missing OI-157 row while checking its status (Gabriel-directed, this session) | **RECURRENCE of the OI-098/OI-124 merge-conflict row-loss class.** OI-157 was silently dropped from this file TWICE during same-day `feat/model-canary-probe-step25` merge activity (`318de35`, then `ba93c70`) — once from a genuine 3-way conflict, once when a clean surviving copy on one parent still wasn't picked up. `git log -S` (pickaxe) in its default mode found neither removal, since it skips merge-commit diffs unless run with `-m` — a real audit blind spot. Not yet root-caused or fixed; see full section for the git evidence |
| [OI-159](#OI-159) | 2026-08-15 | Manual T3-5 cross-check (Gabriel-directed workflow-optimization pass), ahead of `ora-tenant-hubspot-reconciliation`'s next scheduled run (2026-09-01) | **DATE-MISMATCH** Medspeed, LLC — workbook `leaseEnd 2029-08-31`, `status Active`; HubSpot deal "Medspeed — Lease Renewal 2026-08-31" still `appointmentscheduled`, `closedate 2026-08-31`. Lease renewed in the workbook but the original HubSpot renewal deal was never closed out |
| [OI-158](#OI-158) | 2026-08-15 | Manual T3-5 cross-check (Gabriel-directed workflow-optimization pass), ahead of `ora-tenant-hubspot-reconciliation`'s next scheduled run (2026-09-01) | **DATE-MISMATCH** Sky Shield — workbook `leaseEnd 2029-08-31`, `status Active`; HubSpot deal "Sky Shield — Lease Renewal 2026-09-30" still `appointmentscheduled`, `closedate 2026-09-30`. Lease renewed in the workbook but the original HubSpot renewal deal was never closed out — same failure class as the 2026-07-16 lease-date correction (J&R/Stone Crest/Chesapeake), different symptom: stale open deal rather than stale wrong date |
| [OI-156](#OI-156) | 2026-08-14 | [event_log.md 2026-08-14](event_log.md#2026-08-14) "Finding: scheduled-task state.json self-narration fabricated provenance text" | **LOW/MEDIUM** No sanity-check exists on scheduled-task `state.json` self-written narrative/`_provenance` fields. 2026-08-14: `ora-acquisition-underwriting-eval-harness`'s priming run wrote a `_provenance` field claiming "10 Fable replays" and a "Gabriel instruction to accumulate repeatability samples" -- neither true (real output: 6 replays, no such instruction). Scoring/replay mechanics were correct; only the prose was fabricated. Candidate fix: a lightweight cross-check (claimed replay counts / cited instructions vs. real `runs/*.json` output) before trusting narrative text, scoped to `ora-setup-audit` or a standalone guard. Not yet built. A one-time follow-up (`ora-eval-harness-first-cron-check`, fires 2026-08-15 13:30 ET) checks whether the pattern repeats on this task's first genuine cron fire, but that's a single-instance spot-check, not the general-purpose sanity-check this item tracks |
| [OI-154](#OI-154) | 2026-08-14 | ora-task-integrity-guard follow-up session, PR [#99](https://github.com/ZeOoba/ora-claude-config/pull/99) | **MEDIUM** CLAUDE.md's inline 8-guard `Guards:` roster restore (reverting half of `8438df1`, which silently disabled doctrine-integrity-probe Check 11) is edited in the working tree but NOT COMMITTED — another session holds unrelated staged files, and the isolated-commit path finishes with a bare `git commit` that would sweep them in. Until it lands, Check 11 is still disabled on the branch |
| [OI-153](#OI-153) | 2026-08-14 | ora-task-integrity-guard 2026-08-14 STEP 2.8 alarm (`property_register_snapshot_diff.py`, third occurrence of the class) | **MEDIUM** No add-time enforcement for the `.gitignore` per-file backup ladder: `task-folder-backup-completeness-probe.py` is wired ONLY into the daily guard, so a git-ignored-and-unbacked task-folder file is caught next-day at the earliest. A `git-prepush-backup-coverage` gate would fit the existing `git-prepush-*` hook family exactly |
| [OI-152](#OI-152) | 2026-08-14 | Independent review (`claude-fable-5`) during PR [#99](https://github.com/ZeOoba/ora-claude-config/pull/99) | **LOW** `property_register_snapshot_diff.py` lines 344-355: a socket read timeout on the RESPONSE BODY raises `TimeoutError`, which matches neither `HTTPError` nor `URLError`, so it bypasses the bounded retry the comment at :340 claims to provide. Fails loudly (traceback, no state written), so robustness not correctness |
| [OI-151](#OI-151) | 2026-08-14 | Independent review (`claude-fable-5`) during PR [#99](https://github.com/ZeOoba/ora-claude-config/pull/99) | **MEDIUM** `property_register_snapshot_diff.py` line 165: array rollups fingerprint by LENGTH ONLY (`"[array:%d]" % len(...)`), so an equal-length element swap is a SILENT false negative — the exact failure class the script exists to prevent. Latent only while relations stay empty |
| [OI-149](#OI-149) | 2026-08-13 | Landing [OI-148](#OI-148), PR [#94](https://github.com/ZeOoba/ora-claude-config/pull/94) — pre-push gate blocked on this, overridden (Gabriel approved in-turn) | **LOW** `maintenance/test-doctrine-integrity-probe.py`'s known-plugin-skill allowlist is stale: flags `morning`, `register-scheduled-task`, `schedule` as unresolved, but all 3 are live installed `anthropic-skills` plugin skills (confirmed against this session's own SessionStart skill listing). Blocks the pre-push gate for ANY push right now, regardless of diff content — hit while landing an unrelated `hooks/**` change. Needs: find and update the probe's plugin-skill allowlist (likely a hardcoded list or stale-generated manifest in `maintenance/doctrine-integrity-probe.py`) to recognize these 3 |
| [OI-147](#OI-147) | 2026-08-13 | ECC repo intake ([external-artifact-intake](../../skills/external-artifact-intake) ruling, Gabriel 2026-08-13, this session) | **REJECTED after a full build + adversarial gauntlet — do not re-attempt without reading the evidence first.** Built `hooks/lib/shell_tokenizer.py`, a real recursive-descent quote/substitution-state tokenizer (not a regex) adapting ECC's `gateguard-fact-force.js` technique, integrated as a downgrade-only narrowing of `ora-autonomy-gate.py` Gate 2b (falls back to today's exact broad match on any parse uncertainty). Correctly classified all 3 historical bypass commands as dangerous, passed a mutation battery (6/8 killed, 2 proven equivalent/safe-direction), and passed all 72 tests (66 original + 6 new) including the 3 historical bypasses run through the full integrated hook. **Killed in Round 1 of the mandated 3-round adversarial gauntlet** (`pr-review-toolkit:code-reviewer`, opus): confirmed live, sandbox-verified bypass — quoting a path operand (`cp evil.html 'oxford-site/index.html'`) or wrapping in an interpreter (`bash -c "..."`, `powershell -Command "..."`, `eval "..."`) makes the tokenizer confidently (and wrongly) classify the write as fully inert, since **quoting suppresses metacharacter interpretation, it does not remove text from the command's argument vector** — a categorically different, more fundamental problem than the quote-state-tracking bugs rounds 1-3 (2026-07-16) found, and NOT fixable by deepening the parser (would need shell command-semantics modeling — which command consumes which argument and whether it writes — a strictly larger problem). Independently found: unbounded `$()`-nesting recursion in the tokenizer throws an uncaught `RecursionError`, which `ora-autonomy-gate.py`'s `main()` has no outer try/except for, crashing Gate 2b entirely (exit 1, non-blocking) rather than just skipping the narrowing — an attacker-triggerable disable of Hard Invariant 2's sole enforcement, strictly worse than a narrowing bug. **Everything reverted** (`git checkout --` on `ora-autonomy-gate.py`/its test file, `shell_tokenizer.py` + its tests deleted) — nothing landed, worktree carries only OI-148's unrelated changes now. Full evidence trail: [[feedback_autonomy_gate_matcher_cannot_be_safely_narrowed]] Round 4 section. Do not re-attempt the quote-state-narrowing approach; a 5th attempt needs a command-semantics model, not a better tokenizer |
| [OI-140](#OI-140) | 2026-08-12 | Hit live while verifying the [OI-136](#OI-136) filing against a `git show HEAD:` extract — the checker reported a defect that existed only in the working tree | **MEDIUM** `maintenance/check-open-items-duplicate-ids.py` **silently ignores its CLI path argument** and always reads the canonical tracker. `main()` does `path = tracker_path()` (line 180) → `TRACKER_PATH_OVERRIDE or DEFAULT_TRACKER_PATH`; **`sys.argv` appears zero times in the file** — no argparse, no positional handling. Passing a nonexistent path still returns a normal clean canonical report, because the `COULD NOT READ %s ... treat as a check failure` branch is unreachable from the CLI. Three things make it read as a working feature: it prints the path it checked, it formats a path into that error branch, and it accepts an argument without complaint. **Tests do not catch it** — `_tests/test_check_open_items_duplicate_ids.py` drives `main()`'s read path by assigning `codc.TRACKER_PATH_OVERRIDE` (a module attribute), so the logic is covered and the entry point never is. **Production caller is unaffected**: `ora-weekly-hygiene` Block N passes no argument. The harm is ad-hoc verification of a worktree copy / candidate edit / `HEAD` extract, which silently returns a verdict about a *different file* — false FAIL (blaming your copy for a live-file defect) or false PASS (your broken copy looks clean because the live one is). A verification tool that answers about an artifact you did not name is the [[feedback_verified_null_vs_inferred_null]] failure in its purest form |
| [OI-139](#OI-139) | 2026-08-12 | `fleet-status.py`'s `find_missed_cycles()` CRON-AWARE GUARD fix (commits `40b6176`/`30d2869`, merged to `main` and pushed as `08e0daa`); Cowork handoff "Health Guard FAIL-Aging Follow-Up" 2026-08-11, `scheduled-tasks/ora-health-guard/SKILL.md` C.1.1 | **LOW — accepted tradeoff, documented, not a defect.** The 2026-08-11 fix that made the missed-cycle detector cron-aware (escalate only past `max(24h, 1.5x own cadence)`, replacing the flat 24h wall that produced 8/13 false positives on 2026-08-10) is pure cadence math with no runtime signal for "was this a genuine catch-up burst." The superseded per-run SKILL.md logic additionally suppressed a `gap ≈ 1x interval` entry only when a late wake was detected *that run*, and otherwise escalated immediately as a likely phantom dispatch or dead task — a signal the code-level threshold structurally cannot see. **Consequence:** a task that misses exactly one slot with the machine fully up (no catch-up excuse available) now surfaces one cycle later than the old per-run logic could have caught it. Deliberate, Gabriel-approved simplification (the 2026-08-11 Cowork handoff spec explicitly specified the 1.5x-cadence rule) — do not re-litigate the threshold on this row alone. **Re-open only if a real single-slot dead-task/phantom-dispatch incident is observed and traced to this specific gap** — do not preemptively bolt an A.0-style runtime signal back into the code threshold without one |
| [OI-138](#OI-138) | 2026-08-12 | hit live while committing two markdown memory files (OI-133 filing); `hooks/eos-review-gate.py` | **MEDIUM — ROUTED to the `hooks-override-auth-eos-gate-msg` workstream (session `e23f4c54`), same file, different defect from the `--record`/config-write-guard message fix.** The gate's BLOCKING path does not apply the pathspec scoping its own `--key --cmd` path does, so it scores *other live sessions' working-tree files* into an unrelated commit. Measured: unscoped `--key` → 3 foreign paths (`hooks/lib/claim_work.py`, `hooks/tests/test-claim-work-lib.py`, `scheduled-tasks/ora-pm-ledger/property_register_snapshot_diff.py`); `--key --cmd '<the pathspec commit>'` → `paths: []`, `key: ""`. **The gate already computes the right answer — the block just doesn't ask it that way.** Using the pathspec form of `git commit` did NOT change the block. Second, and worse — **CONFIRMED, not a guess: the block and `--record` key off DIFFERENT computations, so the gate is unclearable by its own documented procedure.** Both are deterministic and they disagree: the block reported `03b8fb93055b` on two separate attempts minutes apart, while `--key` returned `ef91d37feb7e…` on four consecutive runs. A review recorded via `--record` therefore lands under a key the block never looks for, and **an override is the only exit** — which is exactly how a security gate degrades into a formality. **Why it matters:** in a checkout with 125 dirty files across 15+ sessions this fires on nearly every commit regardless of content, so the gate gets overridden as routine — that is the failure mode, not the inconvenience |
| [OI-057](#OI-057) | 2026-08-03 | Reopened 2026-08-12 by a recurrence of the original symptom; originally push of event_log.md commit `8b61f20`, 2026-08-03 | **REOPENED 2026-08-12** — symptom side of [OI-059](#OI-059). Closed 08-04 on a re-measurement at **56 dirty files** (76.6s, 55/55); that is real load but not the load that matters, and this item's own closing instruction ("only a push under comparable multi-session load tests it") was not met. At **26 sessions / 117 dirty files / 16 cores at 100% / 53 python processes** the symptom returned in its original form: a real push hard-blocked when `test-eos-review-gate.py` AND `test-memory-orphan-link-guard.py` each blew the 90s budget *and* the 180s retry, then both passed in isolation on the same loaded box (55/55 in 140s; 79/79 in 105s). Spawn-cutting (option (a), done in `6dc5df3`) was the right cause-directed target and still proved insufficient — the dominant term is per-spawn cost under contention (**348ms→1390ms** vs ~30-50ms idle), not spawn count. Note this item rejected "(b) a larger budget" on the grounds of a **per-file roster that would rot**; that objection stands but does not cover raising the *global* `PER_TEST_TIMEOUT_SECONDS`, which is what `c29ec95` did (90→240, ceiling 180s→480s). Mitigation, not fix: the symptom recurs whenever load outruns whatever budget is set. Closes only when gate pass/fail is decoupled from machine load. **Do not re-close on a quiet-machine push** |
| [OI-059](#OI-059) | 2026-08-03 | Reopened 2026-08-12 from a false pre-push block; originally [open-items-tracker.md#OI-057](open-items-tracker.md#OI-057) root-cause pass, 2026-08-03 | **REOPENED 2026-08-12** (closed 08-04 on `6dc5df3`, spawns 559→199 / 272→147). That closure was validated at ~56 dirty files and a few live sessions and **did not survive 26-session concurrency**: `test-eos-review-gate.py` and `test-memory-orphan-link-guard.py` each blew the 90s budget AND the 180s retry and hard-blocked a real push, then both passed in isolation on the same loaded box (55/55 in 140s; 79/79 in 105s). Root cause is process-creation cost under contention — bare `python -c pass` measured **348ms then 1390ms** minutes apart vs ~30-50ms idle, on 16 cores at 100% with 53 python processes — which no in-test optimisation controls, and further spawn cuts would mean cutting hook invocations that this item and [OI-061](#OI-061) both forbid. **Mitigated, not fixed, in `c29ec95`** (`PER_TEST_TIMEOUT_SECONDS` 90→240, ceiling 180s→480s, plus 3 stale docstring claims corrected). Stays open because gate reliability is still coupled to machine load; the real fix bounds the load or decouples pass/fail from wall-clock. **Do not re-close on a quiet-machine push** — that is what produced the premature 08-04 close. Mirror item [OI-057](#OI-057) recurred identically and should be reopened with it |
| [OI-133](#OI-133) | 2026-08-12 | `ora-pm-ledger-retime-efficacy-check` 2026-08-12 run (itself an early fire); CC/MCP registry `recordedSkips` + `_shared/send-log.txt` + `ora-pm-ledger/state/` | **MEDIUM** `ora-pm-ledger` missed **12 of 21 days (57%)** pre-retime, and Blocks A/C have **no retro-sweep** — every miss loses that day's digest and ledger permanently. The 2026-08-12 retime (18:00→15:00 ET) was applied on the theory that the slot was the binding constraint; the evidence says it probably is not. `recordedSkips` shows **107 suppressed dispatches on this task alone — 71 `per_task_limit`, 36 `global_limit`** (fleet-wide 1,863). **Do NOT re-litigate the `global_limit`/catch-up-burst class** — [[reference_fleet_throttle_skip_catchup_burst]] already rules it expected behavior with no code fix. Three things are genuinely open: (a) `per_task_limit` is the **majority** here (71 of 107), where that file documents it as the rare "lone task, no neighbours" pattern explicitly worth fresh investigation; (b) **2026-08-10 is a ran-but-did-not-send day** — snapshot artifacts written 12:44, no email, so execution reached the work and failed at *delivery*, a mode neither the throttle file nor Block B's retro-sweep covers; (c) whether A/C need a delivery-confirmation beacon. Slot half is already instrumented — efficacy check re-armed for 2026-08-20 16:30 ET; do not duplicate it |
| [OI-132](#OI-132) | 2026-08-12 | `~/.claude/scheduled-tasks/ora-sofr-direct-prefetch/SKILL.md` STEP 4 — observed live during that task's own 2026-08-12 run | **LOW** STEP 4 verifies seconds after its own STEP 3c write, but `ora-am-brief` supersedes ~6 minutes later — so the "superseded by am-brief = PASS" branch that v1.1 added *specifically* for the catch-up-burst ordering hazard is effectively **unreachable**, and the run log records "my write landed, no supersede" as settled fact while a supersede is still pending. Measured 2026-08-12: prefetch dispatched `15:13:20.983Z`, am-brief `15:13:21.612Z` (629 ms apart); prefetch verified at `15:14:11Z` and logged no supersede; am-brief rewrote §2 at `15:20:26Z`. **No data harm that run** — am-brief independently pulled the NY Fed API and matched all five SOFR fields exactly. Cost is a false run-log claim plus silent undercounting of how often the burst inverts producer order. Cheap fix available: STEP 2 already computes `am_brief_pending`, so condition STEP 4's wording on it rather than adding a wait |
| [OI-131](#OI-131) | 2026-08-12 | surfaced while draining the `event_log.md` uncommitted backlog per [[reference_event_log_uncommitted_backlog]]; measured directly against the live `~/.claude` checkout | **MEDIUM** The `~/.claude` config repo's primary checkout sits on `feat/model-canary-probe-step25`, which has **diverged from main — 21 ahead, 60 behind** — and is the **sole carrier of the 2026-08-10 → 08-12 `event_log.md` history** (`origin/main`'s copy ends 2026-08-09 at 4205 lines; the branch's is 4378). The append-only log therefore exists in two divergent versions and the newer one is unmerged, so **`origin/main` is NOT authoritative for `event_log.md`** until this resolves. **Why it bites:** any session landing an `event_log` entry from a worktree cut off `origin/main` — the route `config-write-guard.py` recommends in its own blocking message — inserts above an 08-09 entry with three days missing, and collides at the top of the file on merge; hit live 2026-08-12, the worktree was discarded and the entry committed onto the branch (`bad4f08`) under a Gabriel-approved `allow-config-write` override. **Compounding:** the same checkout carries 123+ uncommitted files spanning 15+ sessions and is already flagged unable to move main ([[project_primary_checkout_main_move_blocked_2026-08-12]]) — the dirty tree blocks the advance and the drift blocks the merge. Fix belongs to whoever owns the branch: pick a direction (merge main in, or land the branch), do NOT force-switch or reset the primary checkout, and resolve the `event_log.md` top-of-file conflict by KEEPING BOTH sides in date order — never "theirs wins" on an append-only log |
| [OI-125](#OI-125) | 2026-08-12 | [oxford-command-center PR #268](https://github.com/ZeOoba/oxford-command-center/pull/268) — deferred there deliberately, documented in-file at `server/warehouse/insurance-conditions.ts` | **LOW** `property_insurance_policies.property_id` does not hold property ids — it holds POLICY-level slugs (`ins-fvc-pckg`, `ins-fvc-bcl`): 25 rows, 25 distinct values, **0 of 14** snapshot property ids matching (verified by direct query against `data/warehouse/finance.sqlite`). The `insurance-gap` condition compares that raw column against `prop.id`, so it never matches and warns that EVERY property has no insurance policy on file. PR #268 fixed the *display* half (slugs no longer leak into CRITICAL email subjects) and deliberately left this half rather than ship an inert fix. **Both obvious joins are wrong — do not re-derive:** exact name join resolves 0 of 25 (fields disagree on abbreviation and ZIP; built, measured, reverted inside PR #268), and `resolvePropertyId` (`server/workbook/parse.ts:426`) resolves 24 of 25 but MIS-ATTRIBUTES 4 on the `"columbus"` token — a fabricated fact in an alert (Hard Invariant 7), strictly worse than the raw slug. Fix: an explicit slug→propertyId mapping (25 policies, 14 properties — small enough to be *data*, not inference) keying `coveredIds`, keeping the existing fail-open. Never emails; warning-severity only |
| [OI-128](#OI-128) | 2026-08-12 | `ora-task-integrity-guard` 2026-08-12 STEP 2.5 — sixth consecutive sweep to hand-apply a mechanical retag | **LOW** `model-canary-probe.py` computes the whole model-tag retag but stops at reporting, so every sweep since 2026-07-13 has applied it by hand (17 tasks on 08-12). Needs a guarded `--apply` carrying four hard-won rules: direct frontmatter edit never `update_scheduled_task` (OI-109 drops `output_contract`), never write a `NO_OBSERVATION` bucket, never emit the `[1m]`-suffixed id, and re-verify off `list_scheduled_tasks` after writing. |
| [OI-129](#OI-129) | 2026-08-12 | `maintenance/_tests/test_check_open_items_duplicate_ids.py`, hit via `.git/hooks/pre-push` gate 2 while pushing two unrelated SKILL.md commits | **MEDIUM** A pre-push test asserts a live-shared-state invariant: `test_check_open_items_duplicate_ids.py` checks that *the canonical `open-items-tracker.md` has zero id collisions **right now***, and that file is written continuously by every session — six ids (OI-123→OI-128) were allocated by six different sessions inside one hour on 2026-08-12. Any session that writes a `### OI-NNN` detail section before its table row (or vice-versa) puts the file in a state that fails the assertion, which then **hard-blocks an unrelated session's push**. That is exactly what happened here: OI-125's section existed with no row, and it blocked two `ora-deal-*` SKILL.md commits that touch none of this. **Distinct from [OI-119](#OI-119)/OI-127, which are the LOAD/TIMEOUT class** — this failure is `exit 1`, a real assertion, and is fully deterministic: it reproduces on a completely idle machine any time a half-filed item is present, so retrying and raising timeout budgets cannot fix it. The fixture half of the same test file is correct and should be kept (it caught a seeded OI-027 duplicate in its own temp file this run). Fix options: (a) assert only against fixtures and move the canonical-file check to a non-blocking report, (b) keep it blocking but tolerate section-without-row as in-flight rather than a collision, or (c) gate it on the tracker being clean in HEAD instead of the working tree |
| [OI-134](#OI-134) | 2026-08-12 | Gabriel-approved in-turn 2026-08-12 as option (c), alongside (a) the sweep remediation ([PR #271](https://github.com/ZeOoba/oxford-command-center/pull/271)); detail in [project_deal_join_id_based_redesign_queued_2026-08-12.md](project_deal_join_id_based_redesign_queued_2026-08-12.md) | **QUEUED — approved, not started.** Retire name-based seed↔Notion deal joining in favour of a **stable shared deal id** (a `Deal ID` on the Notion Acquisition Pipeline Tracker mirrored as `id` in `src/data/seed-deals.ts`), so `mergeDeals` joins on an opaque key no rename, locality suffix, alias, or punctuation variant can perturb. `dealJoinKey` (`server/sources/deal-name.ts`) strips the `" — City, ST"` tail before matching — but that suffix exists *precisely because* bare street names repeat across metros, so the key deletes the only disambiguator, and **confidentiality rides on the join** (a wrong merge folds an unmatched, fail-closed-confidential row into a public seed record — Hard Invariant 3). Four adversarial passes 2026-08-11/12 yielded 9+7+5+6 defects concentrated here, incl. a CRITICAL cross-side wrong merge with executed repros, an alias path bypassing the corroboration guard, corroboration inert for **11 of 20 live rows**, and a degenerate `acceptedPairKey` (`"k\|\|k"`) that grandfathers all future collisions. Each fix needed *another* corroboration signal bolted on — the signature of a wrong primitive, not unlucky bugs. Acute defects were remediated by PR #271; this is the structural fix. Migration must be fail-closed: a missing/duplicate id **refuses**, never falls back to name matching |
| [OI-122](#OI-122) | 2026-08-12 | `eos-review-gate` blocking a pathspec commit, 2026-08-11 (session `1de11c79`); root cause corrected and independently re-verified 2026-08-12 | **MEDIUM (friction, fail-closed — not a hole)** `eos-review-gate` loses a commit's `-- <pathspec>` scoping whenever the `-m` message spans **multiple lines**, then falls back to whole-repo scope and blocks on whatever unrelated blast-radius file another session happens to have staged. Cause is NOT "the gate ignores the pathspec at runtime" (that was this item's original diagnosis and it is **withdrawn**) — `scope_for_cmd()` (`hooks/eos-review-gate.py:443`) scopes correctly and `main()` uses it. The defect is upstream in `tokenize_cmd_segments()` (`hooks/lib/git_commit_parse.py`, ~line 314), which tokenizes **line by line** — a deliberate 2026-07 hardening that closed a real bypass — so a multi-line message splits the invocation and `find_commit_segment()` (`:94`) never sees the trailing pathspec. Re-verified 2026-08-12 by differential: identical pathspec, single-line `-m` → `"paths": []`, key `""`; multi-line `-m` → `paths: ["scheduled-tasks/ora-pm-ledger/property_register_snapshot_diff.py"]`, key `03b8fb93055b…`. **Workarounds needing no override: a single-line `-m`, or a heredoc-fed `-m` — the heredoc form scopes CORRECTLY, which is why the tokenizer is not the defect.** ⚠ Fix direction CORRECTED 2026-08-12: the tokenizer change this row originally prescribed is **REJECTED** (rounds 2 and 3 of `tokenize_cmd_segments` both attempted it and both shipped false ALLOWs; Gabriel ruled message-only, in-turn). Fixed instead by making the block message name the message shape — [PR #67](https://github.com/ZeOoba/ora-claude-config/pull/67), reviewed 2 rounds, `claude-fable-5` pinned. **hooks/** — any further change takes the mandatory adversarial REFUTE pass |
| [OI-123](#OI-123) | 2026-08-12 | ora-appsec-sweep 2026-08-12 (oxford-command-center @ `0b5b36e`, security-auditor dispatch) | **MEDIUM** oxford-command-center's deployed Cloudflare Pages mirror ships NO security-header mechanism — `public/` contains only `_redirects` (no `_headers`), `index.html` has no CSP `<meta>`, and neither `scripts/bake-mirror.ts` nor `scripts/deploy-mirror.ps1` injects CSP/HSTS/X-Frame-Options/nosniff/Referrer-Policy (verified this run by direct worktree grep, not taken from the agent). So the served brain.oxfordra.net / `ora-command-center.pages.dev` mirror has no enforced CSP script backstop and is framable. Confidentiality is protected by Cloudflare Access gating, so this is defense-in-depth (MEDIUM not HIGH); the reachable-XSS partner is the react-router open-redirect in OI-017's residual set. Distinct from ora-pm's OI-037/OI-060 (that's a different repo + the Pages-Function-vs-static-asset nuance); occ has no `_headers` at all. Fix: add `public/_headers` with a strict CSP (allow `api.anthropic.com` for the SSE endpoint) + HSTS + `X-Frame-Options: DENY` + `X-Content-Type-Options: nosniff` + `Referrer-Policy: no-referrer`; deploy is Invariant-2-adjacent (Pages mirror `/ship` gate) |
| [OI-121](#OI-121) | 2026-08-11 | `ora-session-sweep` 2026-08-11 run (Code-surface execution), see [reference_ora_session_sweep_lams_registry_gap.md](reference_ora_session_sweep_lams_registry_gap.md) | `list_scheduled_tasks` bound to the CC/MCP registry only in this run — never listed `ora-session-sweep` itself, a LAMS-registered task — so Step 4a's task-title matching missed LAMS-only tasks (e.g. `ora-health-guard-fail-aging-nudge`). Unverified whether this is a genuine cross-fleet capability gap or a surface-dispatch mismatch. Needs a supervised Cowork/LAMS session to check first, then (if needed) add a Step 1a registry-read fallback via `update_scheduled_task` — can't be done from Code (register-scheduled-task Rule 1) |
| [OI-119](#OI-119) | 2026-08-11 | `pre-push` hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) | Pre-push gate is **flaky under its own load and hard-blocks any session's push**: across 3 consecutive pushes of one branch, **two different** tests failed (`test_allocate_oi_id.py`, `test-claim-file-collision.py`) with two clean runs of the same suite between them. The gate retries tests that *time out* but not those that error, so each flake looks like a real regression and the tempting escape is a 60-min multi-use override token. **Escalated 2026-08-12:** the retry path is not sufficient either — `test-eos-review-gate.py` hard-blocked a docs-only push *after* exhausting its retry, yet passes 55/55 standalone in 145.9s against a 180s per-test budget (~19% headroom, negative under load); the predicted escape then happened, a Gabriel-authorized `allow-hook-test-failure` token minted to land `46cf1e2`. Track the count of override tokens minted against this gate as the real severity signal |
| [OI-150](#OI-150) | 2026-08-13 | session `15f5b972`, landing a `settings.json` deny-rule change (PR [#97](https://github.com/ZeOoba/ora-claude-config/pull/97)) from an isolated worktree | **UNCONFIRMED — needs investigation.** `hooks/eos-review-gate.py`'s automatic blast-radius independent-review dispatch (ratified in [[feedback_auto_review_blast_radius_gate]] — `settings.json` is explicitly in its trigger scope) did not visibly fire when a `git commit -- settings.json` was run from `~/.claude/worktrees/land-commit-hygiene`, no BLOCKED/WARNING line, no override needed. Traced as far as `git_commit_parse.repo_root()`, which correctly resolves a worktree's own toplevel via `git rev-parse --show-toplevel` (not the bug) — could not go further because the diff was already committed by the time the silence was noticed, so `scope_for_cmd()`'s behavior at commit time couldn't be reproduced post-hoc (nothing was staged anymore). An independent review (`pr-review-toolkit:code-reviewer`, opus) was obtained manually as a substitute before the PR was opened, so the specific diff was not shipped unreviewed — but if the gate genuinely doesn't fire from a worktree, every blast-radius commit made the sanctioned "do it in an isolated worktree" way (the exact pattern this repo's own docs recommend, e.g. `config-write-guard.py`'s own block message) silently skips the review it's supposed to force. Needs: reproduce deliberately (stage a `settings.json` change in a fresh worktree, commit, capture the hook's stdout/stderr directly rather than inferring from the outer command's success) and read `scope_for_cmd()` end to end |
| [OI-146](#OI-146) | 2026-08-13 | session `1de11c79`, 3 spurious `exit 124` push timeouts while landing PR [#67](https://github.com/ZeOoba/ora-claude-config/pull/67) and [#83](https://github.com/ZeOoba/ora-claude-config/pull/83) | **An in-flight worktree/branch enforces its OWN BASE's pre-push gates — not the live checkout's — invisible until it rebases.** `hooks/git-prepush-hook-tests-gate.py` runs from the pushing branch's copy; a branch cut before a gate fix lands keeps failing under the OLD rules even after `main` is fixed. Concretely: `bcbca32` raised `PER_TEST_TIMEOUT_SECONDS` 90→240s on `main`, but a branch cut from before that commit still had `90`, so its 180s doubled-budget retry (2×90) kept timing out on a test that ran clean in 122s — well inside 240s, hopeless against 180s. Three consecutive pushes were misread as load contention; rebasing onto current `origin/main` cleared it with 0 failures. Given this repo's worktree+PR convention and a dozen-plus concurrent sessions, every gate improvement (budget, retry policy, a new check) is invisible to already-open branches until they rebase — a fixed problem looks unfixed, and the honest diagnosis ("stale base") gets misread as "gate flaky under load" (see [OI-119](#OI-119), and OI-135/OI-127 — same budget defect, PR [#67](https://github.com/ZeOoba/ora-claude-config/pull/67)/[#85](https://github.com/ZeOoba/ora-claude-config/pull/85) — not linked as `#`-anchors here since neither section has landed on `main` yet). Fix direction: `git-prepush-hook-tests-gate.py` (or a wrapping pre-push hook) could diff its own file's blob hash against `origin/main`'s and print a loud one-line note — "gate is N commits behind origin/main; rebase before diagnosing a failure as load" — before running the suite. Advisory only; must not block, since a deliberately-pinned base is sometimes correct |
| [OI-130](#OI-130) | 2026-08-12 | session 08df9f95 (path A, 6 PRs) + session 663673c8 (path B, PR #70), both in `ora-claude-config` | **CodeRabbit's PR check reports `pass` on PRs it never reviewed — via TWO distinct routes.** **(A) Rate-limited:** 5 of 6 PRs merged 2026-08-12 (#45, #49, #51, #55, #65) showed `check=pass`, `detail=Review rate limited`, plus a "Review limit reached — we couldn't start this review" comment; only #47 was genuinely reviewed. **(B) Non-default base:** CodeRabbit declines every PR whose base is not the repo default branch and still reports `check=pass`, `detail=Review skipped: reviews are disabled for this base branch` — **deterministic, every time**, not sporadic. Verified on PR #70 (base `feat/model-canary-probe-step25`): 0 reviews, 0 review comments, empty `reviewDecision`, one bot comment that IS the skip notice — and it **merged in that state** at 2026-08-12T22:23:07Z. A green check meaning "nobody looked" is indistinguishable from one meaning "looked and found nothing"; both routes fail OPEN. Path B is structurally induced by ORA practice — any change depending on unmerged work must target a feature branch, which is what OI-131's branch divergence keeps producing. Fix: advisory-only + documented, or gate on a real review body existing (must cover BOTH notices, not just the rate-limit string), or raise the plan limit; path B additionally has a direct config fix |
| [OI-141](#OI-141) | 2026-08-12 | `ora-appsec-sweep` 2026-08-12 fire (session `f74b697f`), re-observed at Gabriel's request | **MEDIUM** A scheduled run is **not single-model**: this one ran `claude-fable-5` for ~28 min then switched to `claude-opus-4-8` mid-run, main chain, no human turn. Its `model: fable` frontmatter pin **is** honoured at start — reversing its own tag's "not honored" claim — but does not hold. Probe now reports `MIXED_RUN` (`f852a45`) instead of plurality-voting; the retag itself is **deferred** because no single id describes the run. |
| [OI-126](#OI-126) | 2026-08-12 | session 08df9f95 (scheduled `ora-doctrine-integrity-guard` run), investigating why merged `hooks/**` fixes were not live | **TRANSIENT — may self-close.** The primary `~/.claude` checkout cannot move onto `main` because `worktrees/_push-main-tmp` holds that branch (git allows a branch in one worktree only), so PR #51 and #55 are merged but INERT in the live pre-push chain: the confidentiality suite's 131 assertions ENV-SKIP on every worktree push, and a load-induced failure still hard-blocks with no retry. `_push-main-tmp` is NOT stale — actively used, clean, and its owning session is idle awaiting input. Local `main` (`9e6c00a`) already carries #47/#49/#51/#55 and is 4 ahead / 0 behind `origin/main`. Resolution is for that session to release the worktree; the ~117 uncommitted files in the primary checkout are unverified against the 48 incoming commits, so nobody should force the switch |
| [OI-127](#OI-127) | 2026-08-12 | session `e0f8485e`, hitting pre-push failures under concurrent load | **DUPLICATE — superseded by OI-135; no separate investigation needed.** Same defect, same file, same number: `hooks/git-prepush-hook-tests-gate.py`'s 180s per-test timeout budget is too low under concurrent load, so healthy tests exit-124 and hard-block a push. OI-127 (20:52Z) is the EARLIER reservation; OI-135 (22:00Z, Gabriel-directed, filed by session `2fb76021`) covers the same finding with fuller evidence — 5 sessions hit exit-124 on `test-eos-review-gate.py` and siblings on 2026-08-12, 180s budget vs ~150–300s actual under 12–16+ concurrent sessions, all clearing on rerun. Filed only to close the orphan reservation and stop a third session re-deriving it. **Track the fix under OI-135.** Closely related to [OI-119](#OI-119) (same gate, flakiness rather than timeout) |
| [OI-118](#OI-118) | 2026-08-11 | `.gitignore:61`, found wiring ora-health-guard to the double-fire guard | `.gitignore`'s `/scheduled-tasks/*/*` makes every `_shared/` helper edit **invisible to `git status`** on any branch predating that file's force-add — and git then **silently overwrites** the file on `checkout`/`merge`/`rebase` to main (verified by reproduction; the same file without the ignore rule aborts with exit 1). Standing trap for the whole guard toolkit |
| [OI-009](#OI-009) | 2026-07-17 | [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md) | Verify the 93 Notion Tenant DB rows with no workbook counterpart against primary leases (low priority) |
| [OI-022](#OI-022) | 2026-07-19 | OI-015 investigation (2026-07-19) | GitHub Data API still serves the pre-rewrite E. Fulton blob (`39b02f4585...`, kept alive by PR #2's internal `refs/pull/2/head`, not deletable via git/API/settings) — Support ticket #4584520 reopened 2026-07-20 with the corrected SHA (`6aed9a7`), awaiting GitHub's purge |
| [OI-019](#OI-019) | 2026-07-19 | [event_log.md](event_log.md#2026-07-19) | Gabriel must add `HUBSPOT_TOKEN` (Private App, `crm.objects.deals.read`) to `oxford-command-center/.env` — PR #221 (frontend trigger) ready, blocked only on the credential. Once live, re-verify 2146 Enterprise Pkwy Twinsburg OH (currently untracked in projects.md/deal-decision-ledger.md) lands correctly in acq_candidates |
| [OI-024](#OI-024) | 2026-07-24 | `hooks/shared-checkout-guard.py` (attribution test realignment, commit b599432) | Guard reads provenance from `SHARED_CHECKOUT_SESSIONS_DIR`, not `commit_provenance.sessions_dir()` — inert today (neither env var set, both resolve to `hooks/sessions`), but setting `COMMIT_PROVENANCE_SESSIONS_DIR` alone would silently degrade attribution to UNATTRIBUTED forever. Gabriel's call 2026-07-24: log, don't fix |
| [OI-021](#OI-021) | 2026-07-19 | [event_log.md](event_log.md#2026-07-19) | Restoration Church Trust: no borrower-side repayment/extension conversation logged since the Apr 2026 Covenant Watch call for lender outreach "by June 2026" (deadline passed); needs Gabriel's own outreach decision (outbound comms, not initiated here). Separately: HubSpot's "Lease Renewal — Restoration Church Trust" deal ($16,714, appointmentscheduled) is likely the same mis-entered-loan-counterparty error already fixed in the Tenant DB (OI-009) — needs a retirement decision. The other 49-stuck-deals batch pass CLOSED 2026-07-25, see below |
| [OI-026](#OI-026) | 2026-07-26 | `oxford-command-center` `gov-ltv-hardening` worktree, 18-round adversarial-refute session | debt-snapshot.ts's degraded-marker "does a new loan explain this one's disappearance" check is tick-partition order-dependent (same facts, opposite governor verdict depending on which snapshot write each fact lands in) — Gabriel's ruling 2026-07-26: ship rounds 14-18 as-is, document only, no fix yet |
| [OI-027](#OI-027) | 2026-07-26 | PR [ZeOoba/oxford-command-center#238](https://github.com/ZeOoba/oxford-command-center/pull/238) (OI-017 vitest-4 REFUTE pass) | Nothing guards against a *future* test regressing into the same class of bug OI-017 fixed (`vi.mock()` of a Node builtin silently no-ops under this repo's jsdom default) — most cases fail loudly, but a bare automock with no configured return value could silently exercise the real implementation and pass for the wrong reason. REFUTE reviewer recommended an ESLint rule (or a `vitest.config.ts` comment at the `environment: 'jsdom'` line) requiring `@vitest-environment node` on any file calling `vi.mock('node:*')`. Not yet built |
| [OI-031](#OI-031) | 2026-07-27 | `orphaned-task-forensics` trace of the `ora-master-workbook-ingest` 2026-07-20 gap, [event_log.md](event_log.md#2026-07-27) | `fleet-status.py`'s overdue/missed-stuck detectors are structurally blind to a single skipped weekly cycle on an already-established recurring task — neither check applies to it (confirmed by reading the script) |
| [OI-033](#OI-033) | 2026-07-28 | Cowork-surface follow-up to the Code-surface usage-limit audit, 2026-07-28 | LAMS `ora-tenant-contact-gap-sweep` carries no `[MODEL: ...]` tag (sole untagged task in a 27/28-tagged LAMS fleet); fix needs `update_scheduled_task` from a Cowork-surface session |
| [OI-041](#OI-041) | 2026-07-31 | ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch) | **MEDIUM** ora-pm mass assignment — 10 handlers pass `await c.req.json()` straight into `.insert()`/`.update()`/`.upsert()` with no Zod schema (`budgets.ts:25`, `insurance.ts:35,46`, `renewals.ts:22`, `units.ts:20,28`, `cam.ts:23-24`, `leases.ts:74,98`, `tenants.ts:62`) while sibling routes correctly use `safeParse`. `budgets.ts:25` also accepts an ARRAY body, making the upsert unbounded in row count. Admin-authenticated only, so integrity/defense-in-depth rather than a breach path — but an admin (or anything holding an admin JWT, see OI-036) can set columns the UI never exposes including `id` and `created_at` |
| [OI-042](#OI-042) | 2026-07-31 | ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch) | **MEDIUM** ora-pm returns RAW Postgres error messages to clients from ~20 call sites (`portal.ts:50,74,93,117,141`, `insurance.ts:38,50`, `cam.ts:79`, `reports.ts:15,27,35,53,57,62`, `cron.ts:40,131,167,227`, `units.ts`, `budgets.ts`, `renewals.ts`, `webhook.ts:20,40`). `server/middleware/error-handler.ts` sanitizes *thrown* errors and its comment claims raw DB messages are never exposed — but that only covers the catch path; these sites `return c.json({error: error.message}, 500)` from a Supabase result. Several are on `/api/portal/*`, reachable by any authenticated tenant, disclosing table/column/constraint/RLS-policy names as a free schema map |
| [OI-048](#OI-048) | 2026-07-31 | ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch) | **MEDIUM** ora-pm: ALL API database access uses the service-role key (`server/db/client.ts:6-13`), which bypasses RLS entirely — so the `auth.uid()` policies in `0004_views_and_rls.sql:101-189` have NO effect on any API request and every tenant-scoping guarantee rests solely on hand-written `.eq('auth_user_id', userId)` lookups. Not a live vulnerability (all six portal endpoints + three Stripe endpoints were traced and each correctly resolves the tenant from the JWT first, with explicit IDOR guards) — the risk is that RLS READS as a safety net in the migrations but is not one: one future endpoint that forgets the filter is an immediate full cross-tenant read with nothing behind it. Compounding: `0008_storage_rls.sql` self-describes as applied out-of-band via a Node script, so live RLS state is UNVERIFIED-not-clean |
| [OI-049](#OI-049) | 2026-07-31 | ora-appsec-sweep 2026-07-31 (oxford-command-center @ `3692385`, security-auditor dispatch) | **MEDIUM — S-002 carve-out drift, CONFIRMED IN HISTORY.** oxford-command-center's ratified financial config has no mechanical change-gate: `config/acquisition-ruleset.v1.json` and `config/replacement-cost.v3.json` appear in NO gate — not in `.claude/hooks/architect-owned.json` globs, not in `scripts/check-refute-required.ts` path sets, and `governance-check.ts` does not reference them. Only prose in the file's `_comment` protects them. Commit `a83ce684` (2026-07-14, PR #210, merged to origin/main) materially changed gate bounds (basisDiscountMin 0.25->0.60 / 0.30->0.65, vintage cutoff 2000->2005) while still carrying `rulesetVersion:"1.0.0"` and `ratifiedDate:"2026-06-14"`; the version-bump ceremony landed 2 days later (`d28d8bfb`). No ACTIVE drift at the pinned SHA — the file is blob-identical to the ceremony state — but the root cause is open. Invariant-4 adjacent |
| [OI-050](#OI-050) | 2026-07-31 | ora-appsec-sweep 2026-07-31 (oxford-command-center @ `3692385`, security-auditor dispatch) | **MEDIUM** oxford-command-center brain server has NO Host-header validation (`server/index.ts:531` binds 127.0.0.1, `server/cors-policy.ts` enforces localhost-only CORS) — but CORS is the wrong control for DNS rebinding: an attacker page whose DNS rebinds to 127.0.0.1 makes SAME-ORIGIN requests, so no CORS check applies at all. There is no Host allowlist and no CSRF token, and every state-changing route (`POST /api/actions/*`, `/api/refresh`, `/api/warehouse/properties/onboard`) is unauthenticated by design. A malicious page open in Gabriel's browser while the server runs can exfiltrate `GET /api/snapshot` — the full portfolio including confidential deals, tenants, loans, counterparty data — and can mutate deal stages, NOI budgets, tenant notes and lease-run assumptions |
| [OI-051](#OI-051) | 2026-07-31 | ora-appsec-sweep 2026-07-31 (oxford-command-center @ `3692385`, security-auditor dispatch) | **MEDIUM** oxford-command-center's confidential-bake deploy PUBLISHES BEFORE it checks the gate and never rolls back — `scripts/deploy-mirror.ps1:112` sets `MIRROR_INCLUDE_CONFIDENTIAL=1`, `:120` deploys to Cloudflare Pages, and only `:137-167` curls the apex to confirm unauthenticated traffic still 302s to Access. If Access has been disabled/misconfigured since the last run, confidential data is publicly served for deploy + 5s settle + up to 3 retries x 15s (~35s+) and REMAINS served after the script throws — the failure path alerts but performs no rollback or unpublish. Second gap: it probes `$VerifyUrl` (`ora-command-center.pages.dev`) only, while `brain.oxfordra.net` is a second Access destination on the same project, so a custom-domain-scoped policy change would pass the check while serving confidential data. This is the one path in scope where deal terms reach an EXTERNALLY SERVED artifact — outside S-001's suppression |
| [OI-053](#OI-053) | 2026-07-30 | Credential-exposure sweep, 2026-07-30 | **Composio API key in plaintext inside OneDrive (cloud-synced):** `Claude_Workspace/01_Workspace/oxford-agent/config.py:3`, duplicated at `01_Workspace/_archive/legacy-templates-2026-03/Claude Agents SDK - Getting Started.md:90`. Composio is a RETIRED connector (removed 2026-06-11), so the key is probably dead — but it has been syncing to Microsoft's cloud and any other device on this OneDrive account. Gabriel to revoke at Composio if that account still exists, then the two files can be scrubbed/archived |
| [OI-052](#OI-052) | 2026-07-31 | ora-appsec-sweep 2026-07-31 (dispatch integrity gate, first live test) | **MEDIUM — sweep mechanism, not a repo defect.** The `ora-appsec-sweep` Fable model floor is carried entirely by the `security-auditor` Agent dispatch (Gabriel-ratified Option C, 2026-07-24, because the task's own frontmatter `model:` pin is inert on CC/MCP). First live test 2026-07-31: the dispatch WORKED — both subagents spawned with `model:"fable"` recorded in their meta and both STARTED on `claude-fable-5` — but both then fell back mid-run to `claude-opus-5` via an explicit harness `{"type":"fallback","from":"claude-fable-5","to":"claude-opus-5"}` event (ora-pm at msg ~108, 68 of 130 assistant msgs on opus-5; occ at msg ~163, 3 of 110). Opus-5 is the session's own top-tier main-loop model, NOT a downgrade to Sonnet/Haiku — so the never-below-Fable floor does not appear breached downward — but the pin does NOT hold end-to-end, which the DISPATCH INTEGRITY GATE's three assertions do not detect |
| [OI-058](#OI-058) | 2026-08-03 | `ora-pm-ledger` 2026-08-01 run + OI-030 coherence read, 2026-08-03 | `ora-weekly-hygiene` Block C fired 2026-08-03 03:47 ET but published NOTHING - no XLSX, no Notion page, no email (verified null on all three). One full weekly cycle lost; last output is 2026-07-26. Cause undetermined from artifacts alone, needs the run transcript. Related: [open-items-tracker.md#OI-031](open-items-tracker.md#OI-031) (same blind spot, one level coarser) |
| [OI-060](#OI-060) | 2026-08-03 | ora-pm appsec fix plan Task 5 (OI-037), `plan/appsec-fixes-oi034-048` branch, commit `5a23927` | ora-pm's `public/_headers` (added for OI-037) does NOT apply to `/api/*` — Cloudflare Pages `_headers` only covers static assets, and `/api/*` is served by a Pages Function (`functions/api/[[route]].ts`). Page/document routes correctly get CSP + clickjacking protection; the API surface does not. Needs a Hono middleware (in `server/index.ts` or a new module) setting the same security headers per-response for `/api/*`, mirroring `public/_headers`'s directives (deliberately not built as part of Task 5 — filed instead, per Gabriel's call, 2026-08-03) |
| [OI-061](#OI-061) | 2026-08-03 | Fixture measurement during [open-items-tracker.md#OI-059](open-items-tracker.md#OI-059), 2026-08-03 | **Files 1-2 LANDED 2026-08-04 (`6dc5df3`)** — shared `gitfixture` helper; spawns 559->199 and 272->147. **File 3 CLOSED NOT APPLICABLE** — profiled 131 spawns of which only 6 are git, so conversion would gain <4%; its "3rd-worst 42.0s" rank was a load-contaminated measurement (clean median 49.1s = 55% of budget). OPEN only for the ~10 unconverted files (preventive, none near budget) |
| [OI-062](#OI-062) | 2026-08-04 | `pending_reimport.py` frontmatter-norm session, 2026-08-04 | ora-skills MAIN checkout has unattributed uncommitted WIP (modified `plugins/ora-operations-extensions/plugin-build.json` version bump 0.1.5→0.1.6, plus untracked `_check_plugin.py`, both dated ~2026-07-29) — present at session start and still present after PR #38 merged; spans ≥2 sessions unclaimed, nobody has picked it up or discarded it |
| [OI-064](#OI-064) | 2026-08-03 | REFUTE pass on the [OI-035](#OI-035) fix, 2026-08-03 | ora-pm portal payment retry doesn't dedupe as the OI-035 fix's commit message claims — every retry re-links the bank account, producing a new `payment_method_id`, so Stripe's idempotency layer rejects the reused key as a mismatch (caught, returned as a clean 400 — fails safe, no double charge) rather than returning the original PaymentIntent. Risk is operational (tenant sees "failed" for a payment that went through, may pay again another way), not a code-level double-charge. The retry-recovery test is regex-over-source-text, never actually exercised this |
| [OI-065](#OI-065) | 2026-08-03 | REFUTE pass on the [OI-035](#OI-035) fix, 2026-08-03 | ora-pm `POST /api/stripe/payment-intent` has no lock between the `ar_ledger.balance` read and PaymentIntent creation — two genuinely concurrent requests (two tabs, or a bypassed client guard) each read the same stale balance and each create a separate, individually-valid PI, exceeding the true balance. Requires the tenant's own concurrent action, not a third-party attack. Outside OI-035/OI-040's original scope |
| [OI-066](#OI-066) | 2026-08-03 | REFUTE pass on the [OI-037](#OI-037) fix, 2026-08-03 | ora-pm's new CSP ships as `Content-Security-Policy-Report-Only`, deliberately — logs violations, blocks nothing. `X-Frame-Options: DENY` (separate header) already closes clickjacking; this item is only the XSS-containment half. Needs a manual browser pass through Pay Now + admin login against a deployed preview, then drop `-Report-Only` to enforce |
| [OI-068](#OI-068) | 2026-08-03 | ora-pm appsec fix plan Task 8 (OI-043), local `plan/appsec-fixes-oi034-048` branch, commit `59f79ff`, confirmed by independent task reviewer | Autopay-with-payment-method is **unreachable from any live frontend path today** — `PortalAccount.tsx` is the sole caller of `setAutopay` and never passes `payment_method_id`; the enable toggle is disabled unless `lease.autopay_payment_method_id` is already set; the ONLY writer of that column is `PATCH /portal/autopay`, which the frontend never calls with a PM. `PortalPayNow.tsx` creates a PM but only ever feeds it to one-time `createPaymentIntent`, never to `setAutopay`. The whole autopay-enrollment feature is unbuilt/unreachable on the frontend, independent of Task 8's (correct) backend hardening — a product gap, not a security defect in what shipped |
| [OI-070](#OI-070) | 2026-08-04 | `ora-health-guard` 2026-08-04 run + `fleet-status.py` investigation, this session | `fleet-status.py`'s missed-cycle detector (OI-031's fix) only sees a CURRENTLY-open gap — it compares `lastRunAt` to the single most-recent expected fire, so a gap that self-heals before the next check erases all evidence of the miss. `ora-health-guard` itself missed 07-31/08-01/08-02 then resumed 08-03/08-04; `fleet-status.py` reported "missed single cycle 0" the same day the scheduler's own run log showed the 3-day gap. Same blind-spot family as [OI-031](#OI-031)/[OI-058](#OI-058), one level narrower. **Still OPEN despite commit `848d4cb`'s message saying "closes OI-070"** — that commit is labeling/documentation only (its own body: "no detection logic changed"); see detail section |
| [OI-071](#OI-071) | 2026-08-03 | Production verification of [OI-067](#OI-067), 2026-08-03 | ora-pm `PortalInsurance.tsx` uploads COI files to `session.user.id`'s folder, but the live (confirmed-applied, confirmed-correct) RLS policy requires `tenants.id` — every real tenant COI upload fails today. Confirmed against production, not just the repo. Misleadingly-named variable (`tenantId = session.user.id`) is likely the root cause |
| [OI-072](#OI-072) | 2026-08-04 | [open-items-tracker.md#OI-061](open-items-tracker.md#OI-061) batch-2 scoping, 2026-08-04 | **`identity=`/`dest=` extension LANDED 2026-08-04 (`8c9ebd0`)** — converted `test-memory-index-git-tracking.py` (git spawns 28->16). Recommendation against extending for bare-repo/clone topology STANDS — `test-git-prepush-scan.py` and the 2 maintenance-tree files remain OPEN, unconverted by design/deferred decision |
| [OI-074](#OI-074) | 2026-08-04 | OI-073 follow-up, root-causing why ora-pm migrations keep landing untracked | ora-pm migration-tracking root cause: no `SUPABASE_ACCESS_TOKEN` in the Code sandbox, so `supabase db push` (the only auto-tracking path) can't run here. Two-tier fix built (dashboard-paste tracking generator + inert `workflow_dispatch` CI job) — CI piece needs Gabriel-provisioned secrets before it can close |
| [OI-075](#OI-075) | 2026-08-04 | Session brief follow-up — standing fix for skill-store/repo drift | Skill-cache drift standing fix: new CC/MCP task `ora-skill-cache-drift-alert` (cron `*/30 * * * *`) runs `ora-skills/tools/repo_first_check.py --all` (built on [PR #39](https://github.com/ZeOoba/ora-skills/pull/39)) at a tighter cadence than the existing daily `ora-doctrine-integrity-guard`, auto-filing an OI item + Notion/email alert on new drift. Not yet closed — hasn't fired against a real finding |
| [OI-077](#OI-077) | 2026-08-04 | 3rd REFUTE pass on the OI-045 fix, 2026-08-04 | **LOW** ora-pm `POST /api/stripe/customer` accepts `email`/`name` straight from the request body with zero validation against the tenant's own `contact_email` on file, sent directly to `stripe.customers.create`. Deliberately left ungated by OI-045's AAL2 work (no PM/money involved, IDOR-safe, idempotent) but a tenant can set an arbitrary email on their own Stripe customer object, meaning future Stripe-side comms (receipts, Financial Connections links) go to an attacker-chosen address. Not blocking; recommend sourcing from the `tenants` row server-side instead |
| [OI-078](#OI-078) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **CRITICAL** ora-pm Row Level Security is enabled on only **6 of 23** tables (`charges`, `payments`, `lease_documents`, `lease_amendments`, `tenant_notices`, `insurance_certificates`) while `VITE_SUPABASE_ANON_KEY` ships in the public JS bundle by design. `properties`, `units`, `tenants`, `leases`, `expenses`, `budgets`, `renewals`, `broker_commissions`, `cam_reconciliations`, `correspondence_log`, `journal_entry_exports`, `lease_move_events`, `sent_notifications`, `stripe_webhook_events`, `tenant_sales_reports`, `utility_meters`, `utility_readings` have no `ENABLE ROW LEVEL SECURITY` anywhere in `supabase/migrations/**` (verified this run by direct grep, not taken from the agent). Under stock Supabase grants an RLS-disabled public table is readable AND writable via PostgREST with the bundle-extractable anon key. Distinct from [OI-048](#OI-048), which is about the *API* using the service-role key; this is the direct-database perimeter. **Live exploitability is INFERRED, not verified** — a one-command curl check is in the item. **CODE FIXED 2026-08-17, NOT YET LIVE**: `supabase/migrations/0013_enable_rls_remaining_tables.sql` enables RLS (default-deny, no policies — server/** uses only the service-role key, no frontend `.from()` call on any of the 17 tables, grep-reverified independently) on all 17 tables. REFUTE-verified (security-auditor, read-only pass) CONFIRMED FIXED, no legitimate caller regressed. Merged to `main` via [ora-pm PR #23](https://github.com/ZeOoba/ora-pm/pull/23) (`aede030`). **Remains OPEN in production**: this repo's migrations are NOT applied on merge — `.github/workflows/db-migrate.yml` is `workflow_dispatch`-only (manual, defaults to dry-run) and its own header notes `SUPABASE_ACCESS_TOKEN`/`SUPABASE_DB_PASSWORD` secrets may not even be configured yet. Someone must run that workflow (dry-run unchecked) before the live database is actually protected — do not close this item until that run is confirmed. **Dry-run EXECUTED 2026-08-22** ([run 32583466897](https://github.com/ZeOoba/ora-pm/actions/runs/32583466897), `dry_run: true`, triggered via `gh workflow run`): failed CLEANLY at the "Link to production project" step — `Access token not provided` — confirming `SUPABASE_ACCESS_TOKEN`/`SUPABASE_DB_PASSWORD` are genuinely not yet configured as repo secrets on `ZeOoba/ora-pm` (never reached `supabase migration list --linked` or the push preview). No partial/unsafe action occurred. **Next step, not completable by Code** (credential provisioning): Gabriel adds both secrets at `github.com/ZeOoba/ora-pm/settings/secrets/actions`, then re-run the dry-run to see the actual pending-migration list and push preview before ever unchecking `dry_run` |
| [OI-079](#OI-079) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **HIGH** ora-pm's `ar_ledger`, `rent_roll` and `critical_dates` views are created without `WITH (security_invoker = true)` (`0011_appsec_idempotency_and_scale.sql:118-151`, `0004_views_and_rls.sql:33-99`) — grep confirms the string appears nowhere in `supabase/migrations/**`. A view without it runs as its owner and IGNORES the RLS policies on `charges`/`payments`/`leases`/`tenants`, so one `GET /rest/v1/ar_ledger` returns every tenant's balance and payment totals even after [OI-078](#OI-078) is fixed. Cross-tenant financial disclosure in one request. **CODE FIXED 2026-08-17, NOT YET LIVE**: `0012_view_security_invoker.sql` adds `security_invoker=true` to all 3 views. Postgres 17 (`supabase/config.toml`) supports it; the one caller class (server/routes/**) uses the service-role key, unaffected. REFUTE-confirmed. Merged via [ora-pm PR #23](https://github.com/ZeOoba/ora-pm/pull/23) (`aede030`) — same NOT-YET-APPLIED-to-production caveat as [OI-078](#OI-078) (manual `db-migrate.yml` workflow required). **Confirmed 2026-08-22 via the same dry-run** ([run 32583466897](https://github.com/ZeOoba/ora-pm/actions/runs/32583466897)) that closed the gap on OI-078 — see that item's entry for the full result (failed cleanly at the link step, secrets not configured, no partial action) |
| [OI-082](#OI-082) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **MEDIUM** ora-pm `payments` has no idempotency or uniqueness constraint for non-Stripe methods. `0011`'s two partial unique indexes cover `stripe_payment_intent_id` and `(lease_id, autopay_period)` only; `method IN ('check','wire','other')` rows are NULL on both and so fall outside each. `charges` got `idempotency_key TEXT UNIQUE NOT NULL`; `payments` did not. A double-submitted admin form or replayed import writes two identical rows and `ar_ledger`'s `payment_totals` CTE sums both — the tenant's balance silently drops, and that understated balance then feeds the payment-intent cap and the autopay lifetime cap. Same failure class as the two AR bugs already shipped here (cartesian fan-out, divide-by-100): the join was fixed, the write path was not |
| [OI-083](#OI-083) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **MEDIUM** ora-pm `POST /api/portal/insurance` (`server/routes/portal-insurance.ts:13-37`) is the only write route with no Zod schema — it destructures the raw body and inserts it, and writes client-supplied `storage_path` to `document_path` verbatim with no ownership or prefix check (the admin route uses `InsuranceInsertSchema`; this one doesn't). An authenticated tenant can point their COI record at another tenant's storage key, surfacing the wrong document under the wrong tenant in the admin UI. Adjacent to but distinct from [OI-041](#OI-041)'s mass-assignment set, which did not include this file |
| [OI-084](#OI-084) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **MEDIUM** ora-pm COI uploads go browser -> Supabase Storage directly (`src/portal/pages/PortalInsurance.tsx:29-39`), bypassing the API entirely: no MIME/magic-byte check, no size cap, `upsert: true` with an unsanitized `file.name`. The `accept` attribute is the only gate and is client-side. The repo already has a server-side validator doing this correctly for lease intake (`server/routes/intake.ts:86-91`) and an unused client validator (`src/components/ui/file-drop.ts`) — the pattern exists, this path just doesn't use it |
| [OI-085](#OI-085) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **MEDIUM** ora-pm portal "Open Charges" is not open charges — `server/routes/portal.ts:39-60` returns EVERY charge on active leases and `PortalPayNow.tsx:33-39` treats them all as selectable, because `charges` has no paid/open state and no charge<->payment link. Separately the balance card sums `ar_ledger` across ALL the tenant's leases while the charge list covers only ACTIVE ones, so the two figures cannot reconcile by construction. A tenant with 18 months of history sees 36+ "open" charges. The server-side cap (`stripe.ts:168`) prevents actual overpayment, so this is a correctness/trust defect, not a loss — but it is the same balance-display class this repo has shipped twice |
| [OI-086](#OI-086) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **MEDIUM** ora-pm `CRON_SECRET` gate uses a short-circuiting string compare (`server/middleware/auth.ts:7`) on the route set that includes `POST /api/cron/monthly-billing` — which creates and CONFIRMS off-session ACH PaymentIntents portfolio-wide. The timing side-channel alone is marginal through Cloudflare's edge; what raises this is the combination: a static, never-rotated shared secret passed on a PowerShell command line (`scripts/trigger-billing.ps1:14`, visible in process listings and shell history) as the single factor gating automated debits |
| [OI-088](#OI-088) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (oxford-command-center @ `175e3f9`, security-auditor dispatch) | **MEDIUM** oxford-command-center `ledger_entries` — the money table — is the only one of its siblings with no natural-key uniqueness constraint (`server/warehouse/migrations/001_initial.sql:59-74`): an AUTOINCREMENT surrogate PK and one NON-unique index, so an identical `(import_id, property_id, period, raw_account, amount)` row is insertable twice by a re-run or replay and silently doubles a balance. Contrast `property_tax_assessments`, `insurance_loss_events`, `property_insurance_policies`, `debt_positions`, all of which have one. Also: no FK on `ledger_entries.property_id` -> `property_master(id)` or on `mapping_id` (though `PRAGMA foreign_keys = ON` is set, so declared constraints WOULD be enforced — the enforcement is on, the declarations are missing), `lease_events` (`011`) has no uniqueness at all, and every money column across `001`/`009`/`011` is bare `REAL` with no unit in the name, comment or CHECK. Security-relevant half only — math correctness stays with `ora-financial-code-integrity-sweep`. Note `server/warehouse/migrations/**` is architect-owned |
| [OI-089](#OI-089) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (oxford-command-center @ `175e3f9`, security-auditor dispatch) | **MEDIUM** oxford-command-center `/api/actions/om-extract` (`server/index.ts:358-414`) validates only `file.name.endsWith('.pdf')` plus a 25 MB cap — no `%PDF-` magic-byte check — then feeds the buffer to `pdf-parse` and, with a `dealId`, writes it verbatim into the live OneDrive deal-document tree. Arbitrary non-PDF content can be persisted into business storage under a `.pdf` name. Reach is local-only (see [OI-050](#OI-050)). The filename sanitization and `resolve()`-prefix traversal assertion at `:400-405` are correct and should be preserved as-is |
| [OI-090](#OI-090) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (oxford-command-center @ `175e3f9`, security-auditor dispatch) | **MEDIUM** oxford-command-center has no rate or concurrency limit on `/api/ai` (`server/index.ts:460-493`), `/api/documents/search` (`:447-453`) or `/api/actions/om-extract` (`:358`). Per-request bounds are good (`maxTurns: 8`, `max_tokens: 16000`, 25 MB cap) but nothing bounds concurrent or repeated calls, and each `/api/ai` call spends real Anthropic tokens against the machine's key. OWASP-LLM10 unbounded consumption; combined with [OI-050](#OI-050)'s unauthenticated cross-site write path this is the cheapest denial-of-wallet route in the repo. ora-pm's equivalent gap was closed under OI-038/044; occ has no counterpart |
| [OI-091](#OI-091) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (oxford-command-center @ `175e3f9`, security-auditor dispatch) | **MEDIUM** oxford-command-center `.claude/hooks/file-guard.mjs:144-159` applies its documented fail-open to the HARD-DENY paths, not just the sentinel-overridable architect-owned list: `findRepoRoot` walks up looking for `CLAUDE.md` and `continue`s (unpoliced) if none is found, and skips any target whose owning root is neither ancestor nor descendant of the session root. A worktree or checkout without a root `CLAUDE.md`, or a path form that breaks `relative()` matching (junction, `\\?\`, 8.3 short name, UNC), therefore leaves `data/overlay.json`, `data/warehouse/**`, `.claude/settings.json` and `.claude/hooks/**` unprotected by this hook; the `permissions.deny` globs are path-form-sensitive in the same way. LLM06/excessive-agency: an agent session on an unusual path form can edit its own guardrails. Requires an already-agentic session, so MEDIUM not HIGH. Any fix here is security-gate hook logic: mandatory adversarial REFUTE pass + the old-vs-new differential battery |
| [OI-111](#OI-111) | 2026-08-09 | four `git push` invocations landing [PR #41](https://github.com/ZeOoba/ora-claude-config/pull/41) and [PR #44](https://github.com/ZeOoba/ora-claude-config/pull/44) (both merged, `c8ea74e` / `6b197f1`) from the `ora-entry-market-scan` session; reconciled 2026-08-15 from two independently-diverged accounts, see section | **LOW** `hooks/git-prepush-doctrine-gate.py`. Two open items remain (Defect 1: possible branch-deletion mis-sweep, unproven; Defect 3: test-sourced stderr reads as a live failure, cosmetic). Both higher-severity claims this item originally carried have since been retracted or closed — Defect 2 (a reporting bug) was RETRACTED 2026-08-09 as a misreading of its own evidence, and Defect 4 (hook-test suite "not concurrency-safe") was investigated 2026-08-12 and found to be a wall-clock budgeting issue with zero assertion failures, not a safety defect. **RECONCILIATION NOTE, needs Gabriel's confirmation:** the Defect-4 closure is HEAD's account; main's account never engaged with that investigation and still frames Defect 4 as open and unretracted ("do not fix by overriding"). Taken as controlling here because it is later and specifically investigative, but this is a judgment call, not a fact both sources agree on — see section |
| [OI-112](#OI-112) | 2026-08-09 | residual from landing [PR #46](https://github.com/ZeOoba/ora-claude-config/pull/46) (`a880b39`, merged) during the `ora-health-guard` session `1ce540e5` | **LOW** The shared `~/.claude` checkout is parked on `feat/model-canary-probe-step25`, merged long ago as [PR #38](https://github.com/ZeOoba/ora-claude-config/pull/38), so `a880b39` is not reachable from the checked-out branch and the **live** `hooks/git-prepush-doctrine-gate.py` lacks the scratch-worktree janitor that PR #46 merged to `main`. Cosmetic and self-limiting; Gabriel decided in-turn 2026-08-09 to leave it rather than switch branches under other sessions' work. Row restored 2026-08-10 by `ora-weekly-hygiene` Block N |
| [OI-113](#OI-113) | 2026-08-10 | `ora-weekly-hygiene` Block M (unsigned draft-to-signature nudge), run 2026-08-10 | **LOW** Outbound lease document for **392 Morrison Rd** (thread "Re: Morrison Rd", sent 2026-08-03 19:11 ET with attachment, body "Updated Security Deposit. This one should be good.") has sat **5 business days** with no counterparty reply observed in the 45-day mailbox scan. No Notion/HubSpot/e-sign completion marker found either way — per Block M step 3, silence is not evidence of progress, so it stays flagged. Confirm whether it was signed or needs a nudge |
| [OI-096](#OI-096) | 2026-08-05 | OI-094 range audit, finding (a); promoted out per Gabriel ruling 2026-08-05 | **RESOLVED 2026-08-05.** `485 S Walnut St` rows 45 and 46 BOTH carried `2028-09-26` — r45 was the final regular payment (`E`=1,365), r46 is the payoff (`D`=253,365 = 252,000 principal + 1,365 interest, `E`=1,365). `'External Loans Summary'!H16` sums column `E` over a date predicate, so it picks up **both** rows' $1,365, counting the same September interest twice. Bites when 2028-09-26 enters the forward-12-month window, ~Oct 2027. Small ($1,365) but a genuine over-count, and the same shape as the OI-092 defect. It is also why the OI-092 detector retry must key on **distinct dates, not row counts** — the withdrawn draft false-fired "13 payments" on exactly this pair |
| [OI-097](#OI-097) | 2026-08-05 | Phantom-dispatch fix (`e441130` stop killing Claude Desktop's own renderer); Gabriel ruling 2026-08-05 (remind, do not automate) | **Re-measure the phantom-dispatch rate on/after 2026-08-07.** The 2026-08-05 measurement is not a post-fix reading: the newest phantom in the window is 11:04 ET and the renderer only came back at 11:08 ET, so there is no meaningful post-fix data yet — a "rate improved" claim off that window would be [[feedback_verified_null_vs_inferred_null]]. Baseline to beat: **54 phantom dispatches vs 68 confirmed runs = 44%** over the 94h to 2026-08-05, with `fleet-deadman` logging "OK" through all of them. Re-run `maintenance/phantom-dispatch-probe.py` over a window that starts after 11:08 ET 2026-08-05 and compare. Deliberately NOT registered as a scheduled task (one-time measurement; registry is under a single-writer rule) |
| [OI-098](#OI-098) | 2026-08-05 | tracker consistency audit 2026-08-05; **all four classes fixed on main 2026-08-12** | **LOW/MEDIUM** Row/detail inconsistencies in THIS file. **Status 2026-08-12: all four original classes CLEARED; item stays OPEN on two audit hazards.** ✅ **2 split table rows repaired** (`OI-092`, `OI-095`) — an unterminated row plus a prose block ends the table, so every row after them rendered outside it; `OI-095` is a **recurrence** in the same region and the root cause is still unidentified. ✅ **6 missing detail sections back-filled** (`OI-101`–`OI-106`), each reconstructed from its own row with a provenance notice. ✅ **8 class-(i) rows moved to the Closed table** (`OI-020`, `OI-025`, `OI-029`, `OI-047`, `OI-076`, `OI-093`, `OI-094`, `OI-095`) with closure dates read from each item's own record and row content asserted byte-identical; `**Closed:**` fields added to the 5 sections lacking one. ⚠️ **OPEN — appendix headings** reuse the `### OI-NNN` prefix, so last-wins id→section matching reads an appendix as the item (this produced a 5-item false finding once) and `#OI-092` anchors are ambiguous. ⚠️ **OPEN — vocabulary drift:** 63 OPEN / 51 CLOSED / 2 RESOLVED / 1 IMPLEMENTED against a two-value Convention, so a `CLOSED`-only test under-reports class (i) by two. **Verified: 64 Open · 53 Closed · 117 sections · 0 orphans either way · 0 malformed rows · 0 ids lost or gained** |
| [OI-099](#OI-099) | 2026-08-05 | `governor-drift-probe.py` false positive, 2026-08-05 | **LOW** (advisory probe; does **not** gate pushes — the pre-push shim runs doctrine-drift, hook-tests and confidentiality only) `RE_DSCR_THRESH` (`governor-drift-probe.py:117`) reads **any** decimal within 40 non-digit characters after "DSCR" as a threshold declaration, so a **measured** coverage ratio in prose flags as a governor redefinition. Fired on `reference_workbook_annual_debt_service_366day_overcapture.md:27` — a measured Banwick coverage ratio sitting a few words after the token "DSCR" (the offending string is deliberately NOT quoted verbatim here: doing so reproduces the false positive in this very file, which is how it was re-triggered 2026-08-05) — exit 1, which also poisons `memory-integrity-probe.py:395` and stands the daily guards red. Worked around 2026-08-05 by rewording that prose (probe now exits 0, 861 files scanned); **the gap itself is untouched** and the next measured DSCR written in prose re-fires it. A real fix must distinguish measured-vs-declared **without** handing a drifting editor an evasion on a Hard-Invariant-4 guard — note it would sit beside `RE_DSCR_PIVOT_DECOY`, which deliberately treats arrow-shaped DSCR changes as drift. Mandatory REFUTE + old-vs-new differential battery |
| [OI-101](#OI-101) | 2026-08-05 | `linkedin-insight-tag-followup` (spent one-time task), captured before archiving, OI-025 sweep follow-up | **LOW** The LinkedIn Insight Tag Partner ID for oxfordra.net analytics is still a placeholder. `website-canonical/sell-your-building.html` (line 930) still carries `window._linkedin_partner_id='XXXXXXX';` (appears twice in the file). The GA4 side of this same instrumentation swap is DONE — real Measurement ID `G-YDSX0RW5HC` is live across 16 other files, committed locally on `main` (`df2bc2a`, not pushed). Blocker: LinkedIn Campaign Manager (account id `547184587`, "Oxford Realty Advisors, LLC") was gated behind a mandatory 2FA-upgrade modal with no dismiss option as of 2026-07-16 — Gabriel completed 2FA setup that day but the gate was still showing immediately after, most likely a propagation delay on LinkedIn's end; unknown whether it has since cleared. **The originating task's own file target list is STALE** — it named 16 files (404.html, about.html, application-received.html, available-space.html, contact.html, for-brokers.html, index.html, markets/columbus-oh.html, markets/index.html, markets/maryland.html, portfolio.html, privacy.html, tenant-application.html, tenant-resources.html, terms.html, track-record.html); verified 2026-08-05 that all 16 are now clean and `sell-your-building.html` — not on that list — is the only tracked source file still carrying the placeholder. Next step: ask Gabriel whether Campaign Manager loads past the 2FA gate now; if yes, retrieve the Insight Tag Partner ID (Campaign Manager > Account Assets > Insight Tag) and replace both occurrences in `sell-your-building.html` only. Commit locally; do NOT push (invariant 2, per-deploy confirmation). Source task archived same day to `Claude_Workspace\00_Governance\Scheduled\_archive_2026-08-05_oi025-sweep\linkedin-insight-tag-followup\` — this item is now the sole record of the blocker and account id. |
| [OI-102](#OI-102) | 2026-08-05 | Session-end optimization candidates, this session, 2026-08-05 | **LOW** The shared-checkout hygiene warning fires on every single write in a dirty `.claude` checkout, but only ever reports the growing dirty-file count, not which condition is actually blocking (e.g. one red test suite). A warning that named the specific blocker (failing suite, contested claim, etc.) instead of a count that only grows would be more actionable |
| [OI-103](#OI-103) | 2026-08-05 | Session-end optimization candidates, this session, 2026-08-05 | **LOW** `skillOverrides` was found silently inert this session (the second such config key, after the v1.8 drift-check prose-comparison finding) — no mechanism in this repo verifies that a `settings.json` key actually takes effect once set. Candidate: a standing audit question/probe enumerating which settings.json keys have never been mechanically confirmed live, rather than discovering inertness ad hoc per session |
| [OI-104](#OI-104) | 2026-08-05 | Session-end optimization candidates, this session, 2026-08-05 | **LOW** The plugin-vs-user skill-source distinction was derived this session (per the referring conversation) by disassembling the CLI binary — a one-off, expensive investigation. If that distinction is needed again, it belongs in a reusable probe helper under `maintenance/`, not re-derived from scratch each time |
| [OI-105](#OI-105) | 2026-08-05 | Session-end optimization candidates, this session, 2026-08-05 | **LOW** `eos-plan-gate` fires at the 4-file threshold even when the touched files were pre-specified handoff work scoped before the session started, forcing an override-file write that then reads in telemetry as a bypass rather than in-scope work. Candidate: a carve-out recognizing scope fixed before session start (e.g. an explicit file list named in the opening prompt) so the override isn't needed for work that was never actually unplanned |
| [OI-114](#OI-114) | 2026-08-11 | [ORA Monthly Portfolio Briefing — August 2026](https://app.notion.com/p/3b96ecd89e598192b55ae297b2c46cad) Risk 1, run 2026-08-11 | **MEDIUM — tenant concentration, no automated cover.** 55 New Plant Court (Owings Mills MD) has a single tenant, **Eurosort, Inc., 34,534 SF, \$452,835 ARR — 8.09% of portfolio ARR and 11.91% of portfolio NOI** — whose lease ends **2027-12-31**. It is 100% of that property's income (property WALT 1.39 yr). The asset is **unencumbered**, so it appears in no maturity schedule, no LTV test and no DSCR test, and no covenant, lender or automated alert will surface the expiry. Because value is carried as NOI ÷ cap (6.5%), a non-renewal writes down **~\$6.97M — 12.0% of portfolio value**. It also lands in the portfolio's largest expiry month (Dec-2027: 59,727 SF / \$741,690 / 8 leases, of which Eurosort alone is 61%). **Two actions: (a) Gabriel to confirm whether the lease carries a renewal option, ROFR or termination right** — the rent roll records escalation but no option data, and the answer changes the negotiating posture; **(b) open renewal discussions now, at 16 months**, targeting a signed extension or replacement LOI by Q1-2027 |
| [OI-115](#OI-115) | 2026-08-11 | [ORA Monthly Portfolio Briefing — August 2026](https://app.notion.com/p/3b96ecd89e598192b55ae297b2c46cad) Risk 4, run 2026-08-11; originating incident [project_insurance_lapse_confirmed_real_2026-07-25.md](project_insurance_lapse_confirmed_real_2026-07-25.md) | **HIGH — escalation path has failed, needs a human owner.** Nine properties are uninsured or about to be. **8 policies EXPIRED for 3+ consecutive ingest runs** — escalated to Gabriel 2026-07-13 and **unchanged across four reporting cycles**: Fairground Village Center PCKG+BCL, ETC POA PCKG+BCL, 1100 Rarig PCKG+BCL, 3883 Livingston PCKG+BCL. **4 more are Renew-Now and have closed from 25–29 days to 18–22 days with no movement**: 1900 N Broadway UFX+BCL (expire 2026-08-27) and 9050 Red Branch PCKG+BCL (expire 2026-08-31). **Compounding: 9050 Red Branch is the property carrying the only balloon inside 18 months** (2028-01-01) — a lender finding a lapsed policy on its collateral 16 months before maturity turns a benign refinance into a covenant conversation; and **1100 Rarig is uninsured** while running the portfolio's shortest WALT (0.92 yr) and 22.9% vacancy. Not an analytical question — \$57.95M of insurable value behind a paperwork failure that four cycles of automated alerting has not moved. **Escalate to Eric** |
| [OI-120](#OI-120) | 2026-08-11 | live incident this session while committing the OI-098 tracker work | **MEDIUM** `config-write-guard` models **working-tree rewrites, not index state**, so a session can contaminate the shared `~/.claude` index but cannot undo it. `GIT_MUTATE_RE` (`hooks/lib/tool_call_paths.py:430-432`) matches the verbs `checkout` / `restore` / `reset` / `apply` / `stash` / `merge` / `rebase` / `cherry-pick` / `clean` / `revert` / `pull` / `switch` (exact regex in the detail section) — **`add` and `commit` are absent; `restore` is present.** Live-proven this session, all three: `git add -- <one memory file>` **PASSED** and silently joined **5 files another session had already staged** (including a 930-line new script); the corrective `git restore --staged` on that same file was **BLOCKED** as a governance write; `git commit` is unguarded too. Net: staging into a shared index is free, un-staging costs a 60-min multi-use `allow-config-write` token, and the single most consequential operation — creating a commit in the live governance repo — is not gated at all. **Workaround that worked and should be documented:** a pathspec commit (`git commit -F <msgfile> -- <path>`) commits the working-tree copy of just that path and leaves the index untouched, so another session's staged work is neither swept in nor disturbed. Secondary finding: the matcher scans command TEXT, so an `allocate-oi-id.py --note` merely *describing* this gap tripped it — same shape as [OI-099](#OI-099). **hooks/** — any fix takes the mandatory adversarial REFUTE pass + old-vs-new differential battery |
| [OI-116](#OI-116) | 2026-08-11 | Landing [PR #52](https://github.com/ZeOoba/ora-claude-config/pull/52) (`claim_work.py` refusal gate), 08-11 | **MEDIUM** An **unattended** session can hold a `claim_work.py` slug indefinitely and cannot be released or contacted: `send_message` refuses delivery to unattended sessions, and `shared-checkout-guard`'s `_self_renew_claims` keeps re-stamping `claimed_at` so the 2h TTL never expires it. Hit **three times in one session** (`1d88885d` on `hooks-override-auth`; `05236b94` on `open-items-tracker`, twice — including while filing this item). The new refusal correctly names the collision and prints the holder's `host_session_id` per OI-108, but "message them" is a dead end for exactly this class of holder, leaving `--force` as the only exit — the operation the gate exists to make rare. |
| [OI-117](#OI-117) | 2026-08-11 | Landing [PR #52](https://github.com/ZeOoba/ora-claude-config/pull/52) into the live checkout, 08-11 | **MEDIUM** The live `~/.claude` checkout has drifted to where `origin/main` **cannot be merged**: on `feat/model-canary-probe-step25`, 4 ahead / 29 behind, **96+ uncommitted files** from ≥6 concurrent sessions, with 9 of the incoming commits' files dirty locally (incl. `open-items-tracker.md`, live-claimed at the time). `stash`/`checkout`/`reset` on a contaminated tree are forbidden, so PR #52 merged to `main` but was **not live**; getting it live needed a surgical `git checkout origin/main -- <3 files>`, which leaves those files modified against the branch HEAD (a `commit -a` by any session sweeps them; `eos-review-gate` may demand a review artifact from whoever did not write them). This is the general case for every future `hooks/**` change, not a one-off. |
| [OI-124](#OI-124) | 2026-08-12 | root-cause trace of the two split rows repaired in [#57](https://github.com/ZeOoba/ora-claude-config/pull/57) | **MEDIUM — ROOT CAUSE IDENTIFIED for the split-table-row defect [OI-098](#OI-098) had carried as unknown.** Both splits (`OI-092`, `OI-095`) trace by `git log -S` to a **single commit, `57d0acf` (2026-08-05)**, whose own message names the method: *"isolated via hash-object/update-index"*. Two things combined: (1) the row text was **hard-wrapped at ~100 columns** — continuation widths 98/98/100/101/101/101/102/102/103/104, matching this file's prose-wrapping convention — which is correct for a section body and **fatal for a table row**, since a Markdown row must be exactly one line; and (2) writing the content as a blob straight into the index **bypasses the working tree entirely**, so no editor, no renderer and no diff of the rendered table ever saw the result. The blob-injection technique is itself a reasonable response to a contaminated shared checkout (cf. [OI-120](#OI-120)) — the defect is that it removes the last human/tool check that would have caught a malformed row. **Impact: live 6 days and survived 7 subsequent commits to the same file**, silently ending the table for every row after the break. **Distinct from the other mechanism** already in OI-098's history (a blank line inside the table, which pushed OI-095/096/097 out) — same symptom, different cause; do not treat one fix as covering both. Cheap detector proposed, green today: every line matching `^\| \[OI-` must end in an unescaped pipe character |
| [OI-142](#OI-142) | 2026-08-12 | `ora-skills` `pending_reimport.py` sweep investigation, this session | **MEDIUM** `exception-detection`'s runtime cache held a v1.3 `SKILL.md` (installed live 2026-08-11) with **zero commit anywhere in `ora-skills` git history** — traced to session `89c314f4-a39e-43b4-8d1b-6b38d91774f7`, which appears to have packaged and Save-skill-installed straight from its own uncommitted working tree. `repo_first_check.py` Check 5 only fires at commit time and cannot catch an install that never gets committed at all. Recovered via backfill commit `85abbbc`; root cause of the bypass and a durable fix are still open |
| [OI-172](#OI-172) | 2026-08-16 | Rev 2 fleet re-check (session 6797e01b); reopens the T3-12 follow-up | **MEDIUM — COWORK-ONLY WRITE, do not retry from Code.** `ora-passed-deal-tracker` is live on BOTH fleets at `30 6 15 * *`. The CC copy is the one that must SURVIVE (it alone reaches the Outlook COM send path); the LAMS twin must be disabled from a Cowork session. Ids collide and CC `list_scheduled_tasks` shows no LAMS entries, so an `enabled:false` issued from Code hits the WRONG copy. Double-fire guard is live, so 2026-09-15 is mitigated — the defect is not. |
| [OI-174](#OI-174) | 2026-08-16 | Pre-push gate fail-retry during the recursive-delete-guard work (session 6797e01b) | **LOW/MEDIUM — flaky test + a diagnostic gap.** `maintenance/_tests/test_allocate_oi_id.py` failed once at the gate and passed on rerun; 5 isolated runs pass, so it is load/timing sensitive, not broken. The more valuable half: the gate's fail-retry reports only THAT a file flaked, never the first attempt's failing assertion — so each occurrence is undiagnosable after the fact. Matters because this is the test for the OI-id allocator, the tool that exists to stop id collisions. |
| [OI-176](#OI-176) | 2026-08-16 | `/doctor` hook-timing aggregation, session 76023481; half 1 withdrawn same-day after date-scoped recheck | **MEDIUM — the `PreToolUse:Bash` chain is 10 cold Python starts per Bash call.** Date-scoped: **153 runs on 2026-08-16 alone**, median **716 ms**, p90 2,310 ms; 10 of the 31 configured hooks match `Bash`. Fix already exists in-tree — `pretooluse-dispatcher.py` consolidates `Edit\|Write\|MultiEdit`, and `PreToolUse:Edit` measures 461 ms vs Bash's 716 ms. **LANDED 2026-08-16** as `2800595` (from worktree commit `f07b257`) on Gabriel's in-turn "land it", after the blocking claim cleared. Two independent reviews (claude-fable-5), 30/30 differential equivalence vs the real 10-process chain, 38-tool ordered-coverage parity, and a live post-landing block probe correctly attributed to `pretooluse-dispatcher.py --chain bash`. Acceptance NOT yet met: only 2 post-landing timing samples so far, so the median claim is unconfirmed — re-run the arm-split check after normal use. **⛔ Half 1 (hookify no-op hooks) WITHDRAWN — hookify stopped running 2026-08-13, nothing to disable, do NOT hunt for a Cowork `/plugin` toggle.** It was filed live because timings were bucketed by transcript FILE MTIME rather than each event's own `timestamp` — a resumed `.jsonl` is touched today but holds week-old lines, so a dead finding read as current. Bucket by event timestamp and confirm non-zero on today's date. Detail: [reference_hookify_noop_hooks_every_tool_call.md](reference_hookify_noop_hooks_every_tool_call.md) |
| [OI-181](#OI-181) | 2026-08-16 | Hit live while recording the OI-176 review artifact (session 76023481), then reproduced deterministically | **MEDIUM — a stale copy of the review gate silently discards `--notes-file`, yielding an APPROVED security-review artifact with an EMPTY audit trail, exit 0, no warning.** Reproduced: same argv against LIVE (notes preserved, 50 chars) vs the stale `oi173-spec-liveness-probe` worktree copy (notes empty). Three compounding causes: (1) `_arg()` is a positional `argv.index()` scan (`eos-review-gate.py:768`), not argparse, so an **unsupported flag is ignored, never rejected** — tellingly the stale copy's own `_arg` DOES return the `--notes-file` value, it just never asks for it, so detection is cheap; (2) `config-write-guard` **prescribes the stale path** — its block message says to re-run against a worktree copy, while invoking the live binary by absolute path is blocked; (3) **no version stamp**, so skew is undetectable by tool or caller. Not cosmetic: `notes` is not part of the artifact key, so the gate still PASSES and the commit lands — the failure is invisible exactly when the audit trail is created, on the tool that exists to prove a blast-radius change was reviewed. Exposure: `--notes-file` is the ONLY flag divergence (15 others match); 1 of 3 live worktrees is stale; flag landed in `fe14d91` (PR #136), so any worktree branched earlier is affected. **LANDED 2026-08-16** as `4cbebe8` (from worktree commit `43be6ca`) on Gabriel's in-turn "land it the same way OI-176 went." `reject_unknown_flags()` on both `--key`/`--record`, correctly skipping value-taking flags' values; `KNOWN_CLI_FLAGS` self-checked against real `_arg()` call sites so the fix cannot itself go stale; `__version__` stamped into every artifact. Claim re-checked before landing (`hooks-override-auth` free; `fleet-status-reconcile`'s claimed paths were disjoint — `maintenance/fleet-status.py`/`test-fleet-status.py`, not this file); two-pass mtime identical; worktree branch point confirmed an ancestor of live HEAD. Live post-landing verification with the override token removed: unknown flag rejected on the LIVE binary (rc=1, names the flag + accepted set + staleness diagnosis); `--notes-file` itself still accepted (rc=0); the verification Bash calls themselves ran through the live dispatcher's `--chain bash` in-process path with no `unrecognised` output — proving the scoping fix live, not just in a harness; a real governance write was still BLOCKED through the same chain. Independently reviewed (claude-fable-5) before landing: scoping hazard proven both by tracing and by running the dispatcher both directions, flag-set completeness re-derived independently and matched exactly, adversarial parsing cases all correct, no artifact written on rejection. No lingering damage from the triggering incident: the empty artifact was overwritten at the same key, both this session's artifacts carry notes |
| [OI-183](#OI-183) | 2026-08-16 | Mirror-deploy incident chain, this session, discovered while landing #280/#282 | **MEDIUM — the `oxford-command-center` canonical checkout has no auto-update mechanism, and a merged PR now reads as \"landed\" while sitting dead on disk.** PR #279 (isolated build root) deliberately removed `deploy-mirror.ps1`'s `git merge --ff-only` — correctly, since it was mutating a shared tree other sessions build from — but nothing replaced its incidental side effect of keeping the checkout current. Reproduced twice same evening: #280 merged to `origin/main`, checkout stayed 1 behind until manually fast-forwarded; #282 merged, checkout stayed 1 behind again, same manual fix. Anything that reads FROM the canonical checkout (`mirror-run-classify.ps1`, run unattended by the `ora-command-center-mirror-drift-check` weekday task) can silently classify against stale logic with no symptom — the same failure class #280 itself just fixed (a classifier making a claim that was true when written and false now). The isolated build root is unaffected (it pulls `origin/main` directly), so this does not threaten what the mirror serves — only the correctness of anything else that trusts this checkout being current. |

### OI-240
**Status:** OPEN
**Opened:** 2026-09-07
**Severity:** MEDIUM — sourcing pipeline, ~50 letters/week with no feedback loop
**Source:** ORA Automation Audit Rev 23, T5 gap-analysis thread (2026-09-06) — [[project_automation_audit_rev23_2026-09-06]]

**Description:** `owner-outreach`'s own guardrail states it is a T1-only pipeline — it promotes qualifying parcels, dedups against the Notion ledger, and drafts T1 cold-outreach letters. T2 through T4 (the ratified "top 5-8/week" call-slice sequencing, response tracking, and follow-up) were scoped but never built — rendering has been pending an input Gabriel never supplied. Consequence: roughly 50 letters go out weekly with no mechanism to capture who responded, no signal feeding back into which owners get called, and no way to tell whether the T1 stage is actually producing engaged leads or just noise.

Quoted directly from the audit, Gabriel's own framing of why this matters: "the sequencing layer is the actual unlock." Of the eight T5 gap findings, this was ranked highest-value — it is the one place where ~80 monitoring tasks feed a pipeline that stops short of the action it exists to drive.

**Candidate fix:** define and supply the missing input (the call-slice sequencing rule), then build T2 (response capture) as the smallest next increment — it is the prerequisite for T3/T4, and even a manual weekly response log would let the pipeline start learning.

**Related:** [OI-241](#OI-241) (deal-flow-triage, same audit thread, same "detection-rich, action-poor" pattern).

### OI-241
**Status:** OPEN
**Opened:** 2026-09-07
**Severity:** LOW-MEDIUM — a declared workflow the skill cannot execute
**Source:** ORA Automation Audit Rev 23, T5 gap-analysis thread (2026-09-06) — [[project_automation_audit_rev23_2026-09-06]]

**Description:** `deal-flow-triage`'s own description declares the Outlook inbox as its input source (batch-triaging inbound broker/listing emails), but its `allowed-tools` frontmatter only grants `Read, Grep, Glob` — none of which can reach a mailbox. As written, the skill cannot perform the workflow it advertises; anything invoking it for its stated purpose would fail or silently do nothing useful. Its file-ingestion half (parsing an already-downloaded broker package) already substantially overlaps `ora-om-intake-ocr`.

**Candidate fix:** either grant it real Outlook access (the `mcp__c0ea3c01…__outlook_email_search` tool class other ORA skills already use) so it can do what it claims, or retire it and fold any non-duplicate file-ingestion logic into `ora-om-intake-ocr`. Not yet decided which — needs a look at how often this skill has actually been invoked (see the skillUsage telemetry caveats in [[project_automation_audit_rev23_2026-09-06]]) before choosing build-out vs. retirement.

**Related:** [OI-240](#OI-240) (owner-outreach, same audit thread).

### OI-242
**Status:** OPEN
**Opened:** 2026-09-07
**Severity:** LOW-MEDIUM — a real pricing signal with no feedback loop
**Source:** ORA Automation Audit Rev 23, T5 gap-analysis thread (2026-09-06) — [[project_automation_audit_rev23_2026-09-06]]

**Description:** Lost-deal calibration data is written to a ledger at LOI draft time (per `loi-generation`'s "Lost-Deal Ledger capture at draft time") but nothing reads it back into buy-box or pricing calibration downstream. The concrete case: 511 Industrial Mile is ORA's only priced LOI loss to date ($1.575M won by a competing bidder vs. ORA's $1.45M offer). Its Walk price ($930K) sits **below** the actual $1.45M offer ORA made, so Loss Class is held UNCLASSIFIED rather than mis-scored — see [[reference_511_industrial_mile_duplicate_rows_and_walk_offer_conflict_2026-08-16]] for the full duplicate-row/walk-offer conflict this traces to. That specific data-quality issue is tracked there; this item is the broader, structural gap it's a symptom of — a real pricing-loss signal exists and nothing consumes it.

**Candidate fix:** define what "consuming" a lost-deal record means in practice (a periodic review against the buy-box scorecard? a manual quarterly read?) before building anything — this is a design question, not yet a build task.

**Related:** [OI-243](#OI-243) (deal-decision-ledger, adjacent knowledge-loss pattern, same audit thread).

### OI-243
**Status:** OPEN
**Opened:** 2026-09-07
**Severity:** MEDIUM — knowledge loss, ~1 deal/week
**Source:** ORA Automation Audit Rev 23, T5 gap-analysis thread (2026-09-06) — [[project_automation_audit_rev23_2026-09-06]]

**Description:** `deal-decision-ledger` expects `deal-retirement` to write pass/kill reasoning into it when a deal reaches a terminal stage. But `deal-retirement` was unpublished from the skill store 2026-08-05 (Automation Audit-driven fleet cleanup, usageCount 1 lifetime) and is now repo-path-only — invoked by `ora-weekly-hygiene` as `~/ora-skills/deal-retirement/SKILL.md`, not by name. On any surface that tries to reach it by name rather than by the repo-path workaround, the write never happens: five rows in `deal-decision-ledger` currently read "reason not logged elsewhere — reconcile manually." Pass reasoning is being lost at roughly one deal a week.

This is directly relevant to [OI-242](#OI-242) — the lost-deal calibration gap needs exactly this reasoning as its raw material, and it isn't reaching the ledger.

**Candidate fix:** either re-publish `deal-retirement` to the skill store by name (verify first whether the original unpublish reason still holds — check [[project_automation_audit_rev23_2026-09-06]]'s R23-12 finding on why this and `annual-cycle` stay repo-path-only), or repoint `deal-decision-ledger`'s write expectation to the same repo-path invocation pattern `ora-weekly-hygiene` already uses successfully, so no republish is needed.

**Related:** [OI-242](#OI-242).

### OI-247
**Status:** OPEN
**Opened:** 2026-09-08
**Severity:** MEDIUM — process gap on a blast-radius file, not a content defect (the tie-break wording itself is fine)
**Source:** `repo-housekeeping` active-work claim (session `ebc44356-fc0e-4479-928a-9df4da4c2fea`, `claimed_at: 2026-09-07T11:36:19`, title "Land Rev21 close-out: CLAUDE.md exception-scan tie-break via worktree off origin/main + PR"); discovered by a separate session that armed a GitHub PR monitor per the claim's own stated plan and, after ~24h with no PR, verified directly rather than continuing to wait — see [[project_automation_audit_rev23_2026-09-06]] for the fuller session narrative.

**Description:** The claim's own title commits to a specific, doctrine-correct process for a blast-radius file: isolated worktree, land via PR. That process was set up (`.claude/worktrees/claude-md-tiebreak`, branch `fix/claude-md-exception-scan-tiebreak`) but never used — the branch carries zero commits and sits 14 behind `origin/main` as of filing.

The actual content change (adding `automation-health-monitor` to the "Exception scans" line — `... `exception-detection` (live Notion/HubSpot) · `portfolio-anomaly-scout` (file-export sweeps) · `automation-health-monitor` (scheduled-task fleet, not portfolio data).`) is real and reasonable on its own terms. But it did not arrive via that worktree. It is present in the live `~/.claude` checkout's git history at commit `b95cef1`, whose message is "docs(governance): require a real review verdict on blast-radius PRs; retire Qodo skills" — a title about Qodo retirement and merge-gate policy that says nothing about a skill tie-break. `git show origin/main:CLAUDE.md` does **not** contain the line (verified directly, not inferred), and `PR #166` — the merged PR matching that commit's title — touched `CLAUDE.md` for genuinely unrelated content (confirmed via `gh pr view 166 --json files`). The tie-break line exists only on `feat/model-canary-probe-step25` (pushed, 0/0 ahead-behind that remote), the branch already tracked in memory (`project_primary_checkout_main_move_blocked_2026-08-12.md`) as blocked from reaching `main`.

**Why this matters beyond "wrong branch":** this is the same shared-index-race shape `package-and-stage-skill`'s changelog documents for `ora-skills` (a bare commit picks up whatever else is staged at that instant, silently) — here landing in the environment's own doctrine file instead of a skill file. Two concrete consequences: (1) no reviewable diff or PR exists for a blast-radius-file change, so nothing enforced the review this environment requires for exactly this class of edit; (2) the change is durable only as long as `feat/model-canary-probe-step25` survives — if that branch is ever reset, rebased away, or abandoned (as `fix/claude-md-exception-scan-tiebreak` itself already has been, sitting untouched), the fix silently reverts with no record it ever needs re-applying, since it was never captured in a commit whose message describes it.

**Not in question:** the wording of the fix itself, CLAUDE.md's word count (1,824 words at time of filing, 26 short of the 1,850 FAIL gate — not moved by this finding either way), or any conflict with the four skill-description-level trigger-collision fixes landed the same day in `ora-skills` (`ab850fd`) — confirmed disjoint file sets, no overlap.

**Candidate fix:** either (a) cherry-pick just this one hunk from `b95cef1` into a proper isolated worktree off current `origin/main`, land it via a real PR with a commit message that names what it does, and abandon `fix/claude-md-exception-scan-tiebreak`; or (b) if `feat/model-canary-probe-step25` is expected to reach main on its own eventually, explicitly confirm that expectation in writing here rather than leaving it implicit — the branch has been described as blocked since 2026-08-12 (cleared once 08-16, re-measure current state before assuming either way). Gabriel's call which.

**Related:** [OI-172](#OI-172) (a different "which fleet/branch actually holds the live copy" ambiguity, same root shape — a write landing somewhere other than where its own doctrine says it should).

### OI-244
**Status:** OPEN
**Opened:** 2026-09-07
**Severity:** MEDIUM — recurring token cost, no design work done yet
**Source:** ORA Automation Audit Rev 23, T4 spec-cost thread (2026-09-06) — [[project_automation_audit_rev23_2026-09-06]]

**Description:** `ora-pm-ledger`'s 13 dated RESTORATION/RE-ENABLE/AMENDMENT NOTE sections were extracted to `references/CHANGELOG-2026-07-08-to-2026-08-16.md` on 2026-09-06, cutting its daily-firing spec from 16,398 to 12,180 words (~171K tokens/month saved). `ora-health-guard` is the same shape of problem and roughly the same size — a 16,482-word daily-firing (05:15 ET) spec — but a heading skim during the same audit pass found **no comparable extractable changelog block**: its bulk reads as live per-run procedure (wake-cause classification, connector pre-flight, the probe suite), not narrative build history. So the `ora-pm-ledger` extraction pattern does not mechanically transfer here; this needs an actual content read to find where (or whether) a real lever exists, not a copy-paste of the same technique.

**Candidate fix:** a Code-surface session reads `ora-health-guard/SKILL.md` in full and determines whether any section is genuinely reference material (changelog, historical incident writeups, a lookup table not needed at runtime) that could move to `references/` without touching live procedure. If nothing qualifies, close this as "checked, no lever found" rather than leaving it open indefinitely.

**Related:** none — companion half of R23-13 already closed (`ora-pm-ledger` extraction, [[project_automation_audit_rev23_2026-09-06]]).

### OI-239
**Status:** OPEN
**Opened:** 2026-09-05
**Source:** `ora-ar-feed-sweep` scheduled run 2026-09-02 (feed-freshness work) + directed root-cause investigation 2026-09-05
**Severity:** HIGH — money (arrears overstated) AND suppressed monitoring (all per-lease collections alerting off portfolio-wide)
**Acceptance:** After an import, no `tenantArrears` row at a property that run covered still carries a superseded `asOfDate`; `ar-stale` reflects genuine feed staleness only; and no row is ever zeroed for a property the run did not cover.

**Description:** A delinquency export lists **only currently-delinquent tenants**, so a tenant who pays in full simply vanishes from the next report. Every `tenantArrears` write path is a spread merge — `overlay.tenantArrears = { ...overlay.tenantArrears, ...newArrears }` in `scripts/ar-import-headless.ts`, and the identical pattern in its `patchSnapshot()` — so a row is only ever **added or overwritten, never cleared**. The paid tenant therefore keeps their last non-zero balance and their last `asOfDate` indefinitely.

The consequence is not cosmetic. `src/analytics/conditions.ts` (`arStalenessMaxDays: 35`) degrades its staleness gate on the **worst** stamped record: if ANY row is older than the threshold, `ar-stale` fires and `skipArEval` suppresses **every** per-lease arrears alert across the portfolio. So a handful of tenants who paid months ago silently switch off collections monitoring for every current tenant, while every file in the inbox is fresh.

**Evidence (live, verified twice — 2026-09-02 and again 2026-09-05):** 44 stamped rows across two as-of dates. 37 rows at 2026-08-21 (fresh); **7 rows still at 2026-07-15 — 52 days old, $19,152.40** — at Northwood A11/A12/C3, the Lamar billboard at 3034 Westerville, three at 9050 Red Branch (Soccer Plant, MLC Academy, Atomic Auto Salon), and Morrison 390 PACT / 420 Styled+Staged. All seven sit at properties the 2026-08-21 batch **did** cover, so they are payment attrition, not a coverage gap. Verdict: STALE, `ar-stale` firing, collections monitoring inactive.

**Why "evict whatever vanished" is the wrong fix:** absence of a row means "paid" only if the report actually covered that tenant's property. If a property's file was missing or its parse failed, all its tenants are equally absent, and evicting them would silently zero real, collectable arrears. This is the same ambiguity `server/warehouse/debt-snapshot.ts` hardened over rounds 18/19/19b/19e ("no way to tell the parser broke from you just paid off your last loan").

**Fix built (branch `fix/ar-stale-row-reconcile`, worktree `.claude/worktrees/ar-stale-reconcile`, off `428bd54`) — NOT LANDED:**
- New pure module `server/ar/reconcile-covered.ts`. A property is reconcilable only if the run wrote >=1 **validly-dated** row for it (structural proof the run saw it). Within such a property, a persisted row the run did not write and that is not strictly newer than the run's as-of for that property is **zeroed and re-stamped** to the run's as-of. Zeroing (not deleting) is the contract's own intent — `src/contracts/quickbooks.ts`: *"An all-zero entry means 'checked, current' — distinct from an ABSENT entry, which means 'no AR data'."* The re-stamp is what releases the gate.
- Refuses on an empty incoming set (broken parse must not wipe the book); reports rather than guesses on unmapped leases, uncovered properties, and newer-than-run rows; emits a per-property `written` vs `zeroed` breakdown so a partial export is legible.
- Call site in `scripts/ar-import-headless.ts` kept deliberately small, and applied to **both** the overlay write and `patchSnapshot`.
- Verified on live data before implementation: the design zeroes exactly those 7 rows, 0 unmapped, 0 uncovered, and drops the oldest as-of to 2026-08-21 (15 days) — **`ar-stale` clears and collections monitoring resumes.**
- 12 new unit tests green; full suite **3836/3836 across 277 files**, zero regressions; no new type errors (the 4 `tsc` errors in `tests/unit/prepush-confidential-scan.test.ts` are pre-existing on base — the `.mjs`/`.d.mts` gap at [OI-205](#OI-205)/[OI-206](#OI-206)).

**MATERIAL CORRECTION (2026-09-06) — read this before acting on anything above.** The v1 fix described earlier in this entry was **unsafe and is superseded**. A mandatory adversarial refute pass (financial-code Done bar) broke it with repros executed against live data. Two findings were money-destroying and one falsified the rationale this entry originally used to justify an accepted residual:

- **CRITICAL — `written` is not "what the run saw."** The caller passed `newArrears` (post-`filterAgainstPersisted`, post-partition) as the proxy for what the sweep observed. That set is what survived **six** deliberate suppressions: `rejectedStale`, `undatedConflict`, `ambiguousTies`, review-queue routing, cache-`'SKIP'`, and dead-leaseId roster rejection. Every deliberately-held-back row therefore looked exactly like a tenant who paid. Executed repro: **$18,333.71 zeroed at 1100 Rarig**, including `1100-rarig-m-n-pro-repair-llc` at **$12,380.94** sitting unresolved in the review queue — which, per [[reference_ar_review_queue_has_no_resolver]], has no resolver, so the money would simply be gone from the book.
- **CRITICAL — the "bounded and self-healing" claim was FALSE, and v1's own re-stamp was why.** v1 stamped the zero with the property's **max** as-of, so `filterAgainstPersisted` then rejected every later report *older* than that fabricated stamp. Executed: a wrongly-zeroed Banwick row stayed $0.00 when its own 2026-09-01 report arrived. The zero was durable, not recoverable. **The original acceptance rationale in this entry was wrong and must not be reused.**
- **CRITICAL — the stated mitigation was dead code.** `byProperty` was computed and asserted in a test but never logged by the caller, so the "worth a human look" signal never reached a human. The test manufactured confidence in a mitigation that did not ship.
- **HIGH — v1 re-created the bug it fixes, 36 days later.** `if (prior === 0) continue` froze the stamp of every row it zeroed; since `conditions.ts` gates on all stamped entries regardless of balance, those frozen zeros become the next worst record and re-fire `ar-stale` permanently. A v1 test asserted this defect as intended behaviour, which is why nothing caught it. Same path swallowed credit rows (negative buckets).
- **HIGH — mixed-vintage sweeps fabricated a stamp.** Max-as-of across a property certified 08-01 Morrison data as current to 09-15.
- **MED — Expired leases were zeroable but not re-writable.** A move-out balance is the most collectible-and-contested AR there is; live forward exposure included `9050-red-branch-p-atomic-auto-salon-llc` $2,574.70.

**v2 (current state of the branch)** — all six addressed: a required `seen` set (every leaseId the sweep touched in any way) is now the guard, with `written` demoted to coverage/as-of evidence only; reconcile against the **earliest qualifying report**, never the property max, so a zero stays recoverable; already-zero and credit rows are **re-stamped** (balance untouched) so no clock freezes; Expired leases are never auto-cleared; a property whose zeroing would exceed the rows written for it is **REFUSED wholesale** (refusal blocks zeroing only — re-stamps still pass, or the refusal would re-create the frozen-clock defect); dollars accumulate in integer cents; and every skip/refusal bucket is logged, with refusals also carried in the run's summary line so a refusal can never read as a quiet success. Tests rewritten around the seam rather than the module's own frame — **25 tests**, including a multi-building propertyId fixture, per-suppression preservation cases, and a two-run aging test. Full suite **3850/3850**, no new type errors.

**Live re-verification of v2 (2026-09-06):** refute repro 1 → **$0.00** zeroed (6 suppressed rows preserved). Refute repro 2 → **$0.00** zeroed, Sepich REFUSED (wrote 5, would have zeroed 9). Real 2026-08-21 sweep → 4 rows zeroed ($5,797.32), 1 property refused.

**Residual, stated honestly:** v2 does **not** fully clear `ar-stale` on today's data. 9050 Red Branch trips the partial-export refusal (wrote 2, would zero 3), so its three rows — Soccer Plant $5,000.00, MLC Academy $5,780.38, Atomic Auto Salon $2,574.70, **$13,355.08** — keep their 2026-07-15 stamp and the gate stays shut until either a human confirms those tenants paid or a newer Red Branch report lands. That is the correct outcome given the ambiguity: v1 cleared the gate only by destroying money. Also unresolved by construction: a cache-`'SKIP'` row carries no resolvable leaseId, so it cannot enter `seen` and is protected only by the refusal and Expired rules.

**Blocking to land:**
1. `scripts/ar-import-headless.ts` was held by session `3dec2867` (`oxford-command-center-data`, Fix C missing-overlay precondition guard) at the time of writing. Work was done in an isolated worktree specifically to avoid contaminating that checkout; landing needs the two changes sequenced, not merged blind.
2. ~~Adversarial REFUTE pass outstanding.~~ **DONE 2026-09-06** — it broke v1; see the MATERIAL CORRECTION above. v2 addresses every finding, but v2 has NOT itself been re-refuted. Given v1 passed a full 3836-test suite while carrying two money-destroying defects, **a second refute pass on v2 is a precondition for landing**, not an optional extra.
3. Gabriel's ruling wanted on the 9050 Red Branch residual (above): confirm those three tenants paid, or leave the gate shut until a newer Red Branch report arrives.

**Related:** [OI-237](#OI-237) (the same `data/ar/` corpus committed to the repo). Feed-freshness alarm covering the *upstream* half of this problem was added to `ora-ar-feed-sweep`'s SKILL.md on 2026-09-02 (Step 2.5) and is uncommitted in `~/.claude`.

### OI-232
**Status:** OPEN
**Opened:** 2026-09-05
**Source:** `ora-tenant-hubspot-reconciliation` follow-up, 2026-09-05 — run to root-cause the [OI-216](#OI-216) shape-2 lead
**Severity:** HIGH (money — base rent understated in the source of record, effective in 8 weeks)
**Acceptance:** The Master Workbook's Bakers Specialty row matches the executed 08/31/2026 addendum on all six fields, or each deviation is explained against a document.

**Description:** **The workbook change that created the Bakers Specialty DATE-MISMATCH was a real, fully executed renewal being entered incorrectly — not a data-integrity glitch and not an unrecorded renewal.** Only 2 of the 6 fields the addendum governs came across right.

Primary document: `Business/1100 Rarig/Lease 1100 Rarig Ave Unit K Bakers Specialty Services + Randall Mcclure Addendum #1 8.31.2026 -- 1100 Rarig.pdf` — **fully executed 08/31/2026**, signed by J. Randall McClure for BAKERS SPECIALTY SERVICES, LLC, by McClure individually, and by Eric Goldberg as Manager for 1100 Rarig Ave, LLC.

| Field | Workbook now | Addendum says (verbatim) | |
|---|---|---|---|
| Lease End | `2029-10-31` | "Lease Termination will now be October 31, 2029." | ✅ |
| Status | `Active` | — | ✅ |
| Monthly Rent | `1591.35` | "equal monthly installments of Sixteen Hundred Fifty and 00/100 Dollars ($1,650.00)" commencing **November 1, 2026** | ❌ **−$58.65/mo** |
| Annual Rent | `19096.20` | "Nineteen Thousand Eight Hundred and 00/100 Dollars ($19.800.00) per year" | ❌ **−$703.80/yr** |
| Rent / SF | `10.609` | $19,800 ÷ 1,800 SF = **$11.00** | ❌ |
| Escalation % | `0.035` | "automatically increase by **three percent (3%)**" | ❌ **overstated** |
| Escalation Date | `2026-11-01` | "Beginning on **November 1, 2027**, and on each anniversary thereafter" | ❌ **one year early** |

**The 3.5% is supported by nothing.** The July draft (`...Addendum #1 7.20.2026....docx`) is term-identical to the executed version — same $19,800/$1,650, same 3%, same 2029-10-31 — so it is not a case of working from a superseded draft. The prior addendum (`...Addendum --12.23`) is security-deposit-only ($1,185) and sets no rent or escalation. The pre-edit workbook value was `0.03`, so `0.035` was introduced by this edit. It is also not a house convention: **110 of ~135 rent-roll rows sit at exactly 3%**, and 3.5% appears on this row alone.

**1,800 SF is correct** — certified in the executed Tenant Estoppel (`Estoppel -- 1100 Rarig Avenue Unit K Bakers Specialty Services, LLC.pdf`, 8/8/2023): "1,800 Square Feet located at 1100 Rarig Avenue, Unit K". The Oct-2023 lease's recital of "approximately 1200 square feet" is un-updated form boilerplate and should not be used as the denominator.

**Recommended correction (NOT applied).** This run is detection-only, and the workbook is a financial source of record under Hard Invariants 4 and 5 — nothing was written to it. Set `Monthly Rent` = `1650`, `Annual Rent` = `19800`, `Rent / SF` = `11.00`, `Escalation %` = `0.03`, `Escalation Date` = `2027-11-01`. Leave `Lease End` and `Status`. Then propagate to Notion (`Lease Expiration` 2029-10-31, currently `2026-10-31`) and HubSpot (deal `58521966440`, currently `appointmentscheduled` / `closedate 2026-10-31`), neither of which has the renewal at all.

**Timing is tight on the rent field.** The $1,650 rate commences **2026-11-01 — 8 weeks out**. If the workbook still says $1,591.35 then, whatever bills off it under-bills by $58.65/mo.

**No audit trail.** The workbook carries four logging sheets (`00_Audit`, `Claude Log`, `99_Archive_Log`, `Sync Queue`); **none contains any Bakers Specialty entry.** A hand edit to a rent-roll row passed through all of them silently. The only reason this surfaced is that `lease-snapshot-drift-check` diffs the extract and flagged `drift: 1 date-changed` — it caught the date because dates are diffed, and said nothing about the escalation rate moving 3%→3.5% in the same edit.

**Reconstructed timeline (all verified, not inferred):**
- `2026-07-20 11:30` — addendum drafted (`.docx`, unsigned)
- `2026-08-31` — executed by all three parties
- `2026-09-02 06:27` — executed PDF lands in `Business/1100 Rarig/`
- `2026-09-02 10:24:24` — CC snapshot `ad904b9` (`asOf 09-01`): row still pre-renewal
- `2026-09-02 10:29:54` — lease snapshot `d30d71e` (`asOf 09-02`): row updated, **5 minutes later**
- `2026-09-03 07:22` — workbook mtime

**Ruled out — the pipeline did not cause this.** No parser or code commit touched `oxford-command-center` between the two snapshots; every commit in the window modifies `data/snapshots/portfolio.json` only. The workbook row read directly with `openpyxl` matches the snapshot field-for-field, so the extract is faithful and the defect is in the workbook itself.

**Bearing on [OI-216](#OI-216):** this resolves shape 2 for this row as **"real renewal, entered wrong"** — which is a third possibility that item did not list (it framed shape 2 as either unrecorded renewals or a wrong source of record). Worth testing the same way against Sky Shield, Hoodz of Delmarva and DELVAL before assuming those are the same story.

---

### ⚠️ MATERIAL CORRECTION 2026-09-05 (same session, after checking the other three shape-2 rows) — the quantum above is WRONG and the severity is overstated. Read this before acting on anything above.

**What I got wrong:** the table above compares each workbook field against the addendum as if `Monthly Rent` were meant to hold the *post-renewal* rent. It is not. Running the same document check against Sky Shield, Hoodz and DELVAL established the workbook's actual convention, which those three rows confirm exactly:

> **`Monthly Rent` = the rent in effect NOW · `Escalation Date` = the date it next changes · `Escalation %` = the increase applied on that date.**

Verified against primary documents, all exact:

| Row | MoRent × (1+Esc%) | Contract says | |
|---|---|---|---|
| DELVAL 204+205 | 3811.00 × 1.03 = **3,925.33** | "May 1, 2027 – April 30, 2028 … $3,925.33" | exact |
| Sky Shield A4 | 1050.00 × 1.03 = **1,081.50** | Lease §3(c), Y2 from 9/1/2027, +3% | exact |
| Hoodz 101 | 1591.35 × 1.0369 = **1,650.07** | "Effective October 1, 2026 … $1,650.00" | exact (7¢ rounding) |
| **Bakers K** | 1591.35 × 1.035 = **1,647.05** | "Commencing November 1, 2026 … $1,650.00" | **off $2.95/mo** |

**Corrected finding.** `Monthly Rent 1591.35`, `Annual Rent 19096.20`, `Rent / SF 10.609` and `Escalation Date 2026-11-01` are all **correct under this convention** — they describe the pre-renewal state and the date it changes. The claims above that rent is understated by **$58.65/mo / $703.80/yr are withdrawn.**

The real defect is one field: **`Escalation %` = `0.035` should be `0.036864…`** (the implied step from $1,591.35 to $1,650.00). Effect: **$2.95/mo, $35.40/yr** understated from 2026-11-01 — not $703.80. **Severity drops HIGH → LOW** on this row taken alone.

**Two things survive the correction, and one is new:**

1. **`Monthly Rent 1591.35` is still unexplained for Bakers.** Under the confirmed convention it must be the current rent, but it does not reconcile to the documented lineage: the Oct-2023 lease sets $14,400/yr ($1,200/mo) and the only intervening addendum (12.23) is security-deposit-only. $1,591.35 is also the *correct* current rent for Hoodz ($1,500 × 1.03², verified against the 3rd Addendum), and it appears on a third row (Kontras Performance, Zettler 2026). **That is probably coincidence, not contamination** — 17 of 113 distinct rents in the roll are shared by more than one lease and $1,650 alone appears on 5 — so this is flagged as unreconciled, not as a copy error. Needs the missing Bakers rent history.

2. **NEW, and it applies to Hoodz as well as Bakers: a single `Escalation %` field cannot hold both a one-time negotiated renewal step and the recurring contractual rate.** Both addenda set the *recurring* increase at **3%**; both rows now carry the *step* (3.5% / 3.69%) in the only escalation field there is. The next change is modelled right; every one after it is not. On Hoodz the contract schedule is explicit — 10/1/2027 $1,699.50 and 10/1/2028 $1,750.49 — whereas 3.69% compounding gives $1,710.89 and $1,774.02, **overstating** forward rent by $11.39 then $23.53/mo. Direction is opposite to the withdrawn claim. Whether it bites depends on whether any consumer projects past the next escalation date; that is not established here and should not be assumed either way.

**Revised recommendation (still NOT applied).** Do **not** rewrite Bakers' rent fields. Either set `Escalation %` to the exact implied step (`0.036864`) to fix the $2.95, or — better, and this is the item worth Gabriel's attention — decide how the roll should represent "one-time step now, 3% recurring after," which is a schema question affecting at least these two rows. The Notion and HubSpot propagation recommended above is unaffected and still stands: neither system has either renewal.

**Process note.** The overstated version of this item stood for roughly 40 minutes and was reported to Gabriel in-session before the convention was established. The error came from comparing a source document to a single row without first checking how the row's own fields are defined — the same class of mistake as reading a rate as a level. Checking three sibling rows against their own documents is what exposed it.

**Auto-check:** none.

---

### OI-231
**Status:** OPEN
**Opened:** 2026-09-05
**Source:** `ora-tenant-hubspot-reconciliation` monthly run, 2026-09-05 — root-cause of the corrections applied to [OI-220](#OI-220) the same day
**Severity:** MEDIUM (a detection task that fabricates absence findings is worse than one that finds nothing)
**Acceptance:** Step 3c reports an unmatched tenant as *unmatched*, with a stated match basis — and only claims "absent from system X" after a fallback match on property + unit or Tenant ID also fails.

**Description:** **Step 3c matches HubSpot `dealname` tenants against Notion and `portfolio.json` by name alone, and reports a failed match as "absent" from the system.** The 2026-09-02 run filed 4 sync gaps under [OI-220](#OI-220); 3 were wrong. All 3 tenants were present in the systems they were reported missing from, under a fuller legal name:

- `P.U.P.S Dog Training` → **`P.U.P.S Dog Obedience Training, LLC`** (present in Notion *and* the workbook; reported absent from both)
- `MO Dept of Agriculture` → **`State of Missouri, Department of Agriculture`** (present in both; reported absent from both)
- `Green Home Solutions` → **`Greeen Home Solutions (Mueller)`**, whose own Notes field says `Note: 'Greeen' is the correct spelling (3 e's)` (present in Notion; reported absent)

**The systematic cause, not three coincidences:** a HubSpot `dealname` is written with a short trading name, while the Tenant DB and the workbook both carry registered entity names. Any name-only comparison across those two conventions fails on abbreviations (`MO Dept` / `State of Missouri`), inserted words (`Dog Obedience`), and intentional misspellings. Step 3d already solves this for its own lens — it is specified to match on **property + unit + company, not name alone** — but Step 3c has no such fallback, and nothing carries a Tenant ID across the three systems.

**Why this is filed rather than just corrected:** the failure mode is not "missed a row," it is **reporting an inferred null as a verified one** — the task asserted a tenant was absent from a system it had only failed to find a name match in. That is the exact defect [[feedback_verified_null_vs_inferred_null]] records, and it is self-propagating here: OI-220 then ranked P.U.P.S as "the one worth looking at first" *because* it appeared to have no record anywhere. A wrong absence claim generated a wrong priority.

**Candidate fix (NOT applied — this run is detection-only and does not edit its own SKILL.md):** in Step 3c, before reporting a gap, retry the match on property + unit (the Step 3d basis) and on substring/token containment in both directions; then report three distinct outcomes rather than two — `matched`, `matched by fallback (state which)`, and `unmatched (state the basis tried)`. Reserve the word "absent" for a tenant that survives all of them. Worth pairing with the observation that no stable join key exists across HubSpot / Notion / workbook at all, which is the deeper gap.

**NOTE 2026-09-06 — the fallback-match candidate fix above is a mitigation, not the real fix; don't let it get mistaken for one.** [[project_deal_join_id_based_redesign_queued_2026-08-12]] (merged 2026-08-13, PR #273) replaced oxford-command-center's own name-based deal↔Notion join with Notion's native opaque Deal ID for exactly this failure class — a name/alias join that silently drops its own disambiguator. That precedent is the right architectural home for the tenant-side version of this gap: a stable Tenant ID (e.g. the Notion Tenant DB row's own page id, or a HubSpot contact id) carried through `dealname` → Notion → `portfolio.json`, replacing name-matching entirely rather than adding a smarter fallback to it. That redesign is not scoped or queued anywhere yet — this note exists so the next person who touches Step 3c reaches for a join key instead of a fourth fallback rung on top of the third.

**Auto-check:** none.

---

### OI-230
**Status:** OPEN
**Opened:** 2026-09-05
**Source:** `ora-tenant-hubspot-reconciliation` monthly run, 2026-09-05 (Step 3c — WATCH, naming/sync gap)
**Severity:** MEDIUM (an active tenant is invisible to every tenant-facing routine that reads the Notion Tenant DB)
**Acceptance:** Grails TCG, LLC either has a Notion Tenant DB row consistent with the workbook, or the workbook row is adjudicated against a primary lease and corrected.

**Description:** **`portfolio.json` carries an active lease for Grails TCG, LLC at 2203-2207 Northwood Dr, suite A3 — and the Notion Tenant DB has no row for it at all, live or retired.**

Workbook row, verbatim (`data/snapshots/portfolio.json`, `asOf 2026-09-02`, id `2207-northwood-a3-grails-tcg-llc`):
`"company": "Grails TCG, LLC"`, `"tenantName": "Brett Lagana"`, `"propertyKey": "2207 Northwood"`, `"unit": "A3"`, `"sf": 1200`, `"monthlyRent": 1050`, `"leaseStart": "2025-10-15"`, `"leaseEnd": "2029-08-31"`, `"status": "Active"`.

Notion: a full-text scan of all 298 cached Tenant DB rows (`ora-pm-ledger/state/tenant-db-latest.json`, `as_of 2026-09-05`) for "grails" returns **zero** matches — not a retired row, not an archived duplicate, nothing. HubSpot has no Lease Renewal deal for it either.

**Why this matters beyond one missing row — it is the missing party in [OI-217](#OI-217).** That item records suite A3/A4 at Northwood as claimed by two tenants across two systems (Notion: Sky Shield in A3, Carlton L. Handy in A4; workbook: Sky Shield in A4). The unexplained part was what the workbook thinks is in A3. It is Grails TCG — a tenant Notion has never heard of, on a lease that started 2025-10-15. Any adjudication of OI-217 has to account for three tenants across two suites, not two.

**This was visible to the 2026-09-02 run and not reported.** Verified by reading the exact snapshot that run used (`git show eb236c4:data/snapshots/portfolio.json`): the Grails TCG row was already present there, identical. So this is a gap in that run's reporting, not data that has since changed — stated rather than left to look like new drift.

**Nothing was written.** Detection-only, per this task's standing posture.

**Auto-check:** none.

---

### OI-213
**Status:** OPEN
**Opened:** 2026-09-02
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
**Status:** OPEN
**Opened:** 2026-09-02
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
**Status:** OPEN
**Opened:** 2026-09-02
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

### OI-216
**Status:** OPEN
**Opened:** 2026-09-02
**Source:** `ora-tenant-hubspot-reconciliation` monthly run, 2026-09-02 (Step 3d — DATE-MISMATCH)
**Acceptance:** Each row below is adjudicated against a primary document (lease, addendum, rent roll) and the losing system corrected — or the pair is confirmed to be a legitimate renewal-decision-date vs. lease-end-date distinction.

**Description:** **7 of the 37 open HubSpot Lease Renewal deals carry a `closedate` that disagrees with `portfolio.json`'s `leaseEnd` for the same property + unit + tenant.** Matched on property + unit + company per Step 3d, not name alone. The other 30 open deals match the workbook exactly.

| Tenant | Property / Unit | HubSpot `closedate` | `portfolio.json` `leaseEnd` (status) | Notion Lease Expiration | Sides with |
|---|---|---|---|---|---|
| Medspeed, LLC | 29000 Information Lane / 305 | 2026-08-31 **(elapsed)** | 2029-08-31 (Active) | 2029-08-31 | Notion + workbook |
| Robert and Kesha Best | 2207 Northwood / C1+C2 | 2026-08-31 **(elapsed)** | 2027-08-31 (Active) | 2027-08-31 | Notion + workbook |
| The Companies, LLC | Banwick / 2808 | 2026-09-30 | 2028-09-30 (Active) | 2028-09-30 | Notion + workbook |
| Sky Shield | 2207 Northwood / A3 vs A4 | 2026-09-30 | 2029-08-31 (Active) | 2026-09-30 | Notion + HubSpot |
| Hoodz of Delmarva | 29000 Information Lane / 101 | 2026-09-30 | 2029-09-30 (Active) | 2026-09-30 | Notion + HubSpot |
| DELVAL EQUIPMENT CORPORATION | 29000 Information Lane / 204+205 | 2026-10-31 | 2028-04-30 (Active) | 2026-10-31 | Notion + HubSpot |
| Heritage Pool Supply | 7658 Fishel | 2026-09-30 | 2031-09-30 (Active) | 2026-09-30 (retired row) | see [OI-213](#OI-213) |

**Not adjudicated, deliberately.** Step 3d's own rule: a HubSpot `closedate` legitimately reflects a *renewal decision date* in some cases and should equal the *new* lease's end date rather than the original expiration — so a mismatch is a question, not an assumed HubSpot error. Nothing here was written to any system.

**Two distinct failure shapes, worth separating before anyone fixes them as one batch:**
1. **Notion + workbook agree, HubSpot is behind** (Medspeed, Robert & Kesha Best, The Companies) — looks like an unpropagated renewal, same shape as [OI-214](#OI-214). Two of the three have a `closedate` that has already elapsed, so those deals sit past-due in `appointmentscheduled` on a date the other two systems say is wrong by 1–3 years.
2. **Notion + HubSpot agree, the workbook is ahead** (Sky Shield, Hoodz of Delmarva, DELVAL) — the workbook, the designated source of record for lease dates, carries a materially longer term than the other two. If the workbook is right, three renewals are unrecorded in both CRM and the tenant DB; if it is wrong, the source of record is wrong. Either answer matters more than the individual rows.

**No outcome is inferred for any row.** The Notion Notes field is empty on all seven records except Heritage Pool Supply.

**Caveat on the comparison basis:** `portfolio.json` was `asOf 2026-08-25` / `generatedAt 2026-08-26` at run time — 8 days behind, past the >7-day staleness threshold in `CLAUDE.md`'s source-of-record canon. Re-verify against a fresh extract before acting on shape 2 in particular.

**UPDATE 2026-09-05 (`ora-tenant-hubspot-reconciliation` re-run) — caveat discharged, and the table grows to 9 rows.**

The staleness caveat above is now settled: this run compared against `asOf 2026-09-02` / `generatedAt 2026-09-03` (3 days old, inside the 7-day threshold). **All 7 original rows still hold, unchanged.** Two rows are added:

| Tenant | Property / Unit | HubSpot `closedate` | `portfolio.json` `leaseEnd` (status) | Notion Lease Expiration | Sides with |
|---|---|---|---|---|---|
| Bakers Specialty Services LLC | 1100 Rarig / K | 2026-10-31 | **2029-10-31 (Active)** | 2026-10-31 | Notion + HubSpot |
| P.U.P.S Dog Obedience Training, LLC | 9050 Red Branch / K | 2026-09-30 | 2031-09-30 (Active) | 2031-09-30 | Notion + workbook |

**Bakers Specialty is genuinely new, not a missed row.** It is the single `drift: 1 date-changed` in commit `d30d71e` — verified by diffing the two snapshots directly: `git show eb236c4:...` has `"leaseEnd": "2026-10-31"`, `"status": "Expiring Soon"`; current `af514a0` has `"leaseEnd": "2029-10-31"`, `"status": "Active"`, `monthsToExpiry` 2 → 37. At the 09-02 run all three systems agreed at 2026-10-31, so there was nothing to flag. The workbook has since moved three years out on its own and neither HubSpot nor Notion followed. **This is exactly shape 2, and it now has a timestamp** — the workbook moved between 2026-08-26 and 2026-09-02, which is a narrower window to audit than the other three shape-2 rows offer. Whatever changed Bakers Specialty in the Master Workbook that week is the most direct available lead on whether shape 2 is unrecorded renewals or a bad source of record.

Shape counts after the addition: **shape 1 (HubSpot behind) = 4** — Medspeed, Robert & Kesha Best, The Companies, P.U.P.S; **shape 2 (workbook ahead) = 4** — Sky Shield, Hoodz of Delmarva, DELVAL, Bakers Specialty; plus Heritage Pool Supply at [OI-213](#OI-213).

**P.U.P.S is a correction, not a discovery** — see the 2026-09-05 update on [OI-220](#OI-220), which listed it as absent from both systems. It is present in both. Its `closedate` is now 25 days out on a date the other two systems put five years later, so it is the nearest-term row in shape 1.

**RESOLVED 2026-09-05 — all four shape-2 rows traced to primary documents. Shape 2 was never one phenomenon.**

Each row was checked against its own property folder for an executed instrument. All four renewals are real and all four documents were found; **the workbook is right on three of them and the CRMs are simply stale.**

| Row | Primary document (all executed) | Workbook | What the CRM date actually is |
|---|---|---|---|
| DELVAL 204+205 | First Amendment, Adobe Sign 7/27–7/28/2026 — 18-month option exercised, term to 2028-04-30 | **correct, every field** | `2026-10-31` is the **original Expiration Date** recited in the amendment, superseded by the option |
| Sky Shield A4 | New lease, Adobe Sign 7/22/2026 — Suite **A4**, 9/1/2026–8/31/2029, $1,050/mo | **correct, every field** | `2026-09-30` is the **old A3 lease's** expiration; Sky Shield moved A3→A4 |
| Hoodz 101 | Fourth Amendment, Adobe Sign 8/13/2026 — term to 2029-09-30, $1,650/mo from 10/1/2026 | **correct** under the roll's convention | `2026-09-30` is the **pre-renewal** termination date from the 3rd Addendum |
| Bakers K | Addendum, wet-signed 8/31/2026 — term to 2029-10-31, $1,650/mo from 11/1/2026 | one field off by $2.95/mo | `2026-10-31` is the pre-renewal termination date |

**So the shape-2 framing in this item is wrong and should not be carried forward.** It read "the workbook is ahead of both CRMs" as evidence that the source of record might be wrong. In every case the workbook was **ahead because it was right** — it had ingested a real executed renewal that neither CRM ever received. The correct generalisation is the reverse of the item's worry: **on lease dates, a workbook-vs-CRM disagreement is prior evidence that the CRMs are stale, not that the workbook is.**

**[OI-217](#OI-217) is also resolved by this pass.** The A3/A4 conflict is not a data error: Brett Lagana renamed the A3 tenant to **Grails TCG, LLC** (addendum 7/20/2026, extending A3 to 2029-08-31, new A3 lease 7/22/2026) *and* took **A4** on a new Sky Shield lease the same week. The workbook's A3=Grails / A4=Sky Shield is correct; Notion's A3=Sky Shield is the stale pre-July picture, and it never received Grails at all (see [OI-230](#OI-230)). Carlton L. Handy at A4 in Notion is older still and remains unexplained.

**Bakers detail — see [OI-232](#OI-232), and note its MATERIAL CORRECTION block: the original "4 wrong fields / $703.80" reading was withdrawn the same day.** The "whatever changed Bakers Specialty in the workbook that week" lead was run down: a **fully executed 08/31/2026 lease addendum**, extending the term to 2029-10-31. So for this row shape 2 is neither an unrecorded renewal nor a wrong source of record — it is **a real renewal entered into the workbook incorrectly**, with only the termination date carried across correctly and four other fields (base rent, annual rent, rent/SF, escalation rate and date) left stale or invented. **That is a third shape this item did not contemplate, and it is the one worth testing first against the remaining shape-2 rows** — Sky Shield, Hoodz of Delmarva and DELVAL — before treating them as unrecorded renewals. Each should be checked against its own property folder for an executed addendum in the same way.

### OI-217
**Status:** OPEN
**Opened:** 2026-09-02
**Source:** `ora-tenant-hubspot-reconciliation` monthly run, 2026-09-02 (surfaced by the Step 3d property+unit match)
**Acceptance:** Suite A3 and A4 at 2203-2207 Northwood Dr each resolve to exactly one tenant across Notion and the workbook.

**Description:** **Two tenants contend for suite A4 at 2203-2207 Northwood Dr, and the two systems of record disagree about which.**

- Notion Tenant DB: **Sky Shield** → `Suite / Unit "Suite A3"`; **Carlton L. Handy** → `Suite / Unit "A4"`. Both `Lease Status "Active"`, both at `2203-2207 Northwood Dr — Salisbury MD`.
- `portfolio.json`: **Sky Shield** → `unit "A4"`, `leaseEnd 2029-08-31`, `status "Active"`. **No lease row exists for Carlton L. Handy at all** (see [OI-220](#OI-220)).

So the workbook places Sky Shield in the suite Notion assigns to a different tenant, and carries no record of that other tenant.

**Probably not independent of the date conflict.** Sky Shield is also one of the [OI-216](#OI-216) DATE-MISMATCH rows, and by nearly three years (2026-09-30 in Notion and HubSpot vs 2029-08-31 in the workbook). A single mis-keyed unit would explain both symptoms at once: if the workbook's "A4" row actually describes a different lease, its 2029-08-31 date is not Sky Shield's date. That is a hypothesis, not a finding — it is offered so whoever adjudicates checks the unit before the date.

**Live consequence:** under the Notion/HubSpot reading, Sky Shield's lease expires 2026-09-30 — 28 days from this run — and the deal has been idle in `appointmentscheduled` since 2026-07-06.

Neither record was changed.

### OI-218
**Status:** OPEN
**Opened:** 2026-09-02
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
**Status:** OPEN
**Opened:** 2026-09-02
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

### OI-220
**Status:** OPEN
**Opened:** 2026-09-02
**Source:** `ora-tenant-hubspot-reconciliation` monthly run, 2026-09-02 (Step 3c — WATCH, naming/sync gaps)
**Acceptance:** Each tenant below resolves to a record in every system that should hold one, or is confirmed as legitimately absent.

**Description:** **4 tenants in the HubSpot Lease Renewal pipeline are missing from at least one system of record.** Which record is right is not guessed.

| Tenant | HubSpot | Notion Tenant DB | `portfolio.json` | Gap |
|---|---|---|---|---|
| P.U.P.S Dog Training | deal `58503718155`, `appointmentscheduled`, `closedate 2026-09-30` | **absent** | **absent** | Open deal 28 days from its own date with no tenant record anywhere |
| Green Home Solutions | deal `58513793798`, `appointmentscheduled`, `closedate 2027-02-28` | **absent** | present as "Green Home Solutions of Pickerington" (Zettler / 2018, `leaseEnd 2027-02-28`, Active) | Notion row missing; likely a naming variant rather than a missing tenant |
| Carlton L. Handy | deal `58522429699`, `appointmentscheduled`, `closedate 2027-02-28` | present (2203-2207 Northwood Dr, `A4`, exp 2027-02-28, Active) | **absent** | No workbook lease row; interacts with the A3/A4 conflict in [OI-217](#OI-217) |
| MO Dept of Agriculture | deal `58512555080`, `closedwon`, `closedate 2026-12-31` | **absent** | **absent** | Closed won on a state renewal letter 2026-07-25 per [OI-021](#OI-021), but the tenant never appeared in either system |

**P.U.P.S Dog Training is the one worth looking at first** — it is the only *open* deal in the pipeline with no counterpart in either system of record, and its own `closedate` is 28 days out.

**Not a gap:** Velcani Construction is also absent from both systems, but it is `closedlost` and [OI-021](#OI-021) records the turnover (replaced by Richwood Equipment Co LLC, 2026-05-01, confirmed via three independent Notion sources) — absence there is correct, and it is noted here only so a future run does not re-flag it.

**CORRECTION 2026-09-05 (`ora-tenant-hubspot-reconciliation` re-run) — 3 of the 4 rows above are false positives. Only Carlton L. Handy stands.**

Each of the three was matched by tenant name against the same two sources this item cites, and each is present under a fuller legal name the 09-02 run's name match did not reach:

| Tenant as written on the deal | Actually in Notion as | Actually in `portfolio.json` as | Real status |
|---|---|---|---|
| P.U.P.S Dog Training | **"P.U.P.S Dog Obedience Training, LLC"** — 9050 Red Branch, `Unit K`, exp `2031-09-30`, Active, `Row Retired: false` | **present** — `9050 Red Branch` / `K`, `leaseEnd 2031-09-30`, Active | Present in both. Not a sync gap — a **DATE-MISMATCH**, now added to [OI-216](#OI-216) |
| Green Home Solutions | **"Greeen Home Solutions (Mueller)"** — 2018 Zettler Rd, unit `2018`, exp `2027-02-28`, Active, `Row Retired: false`. Its own Notes field reads verbatim: `Note: 'Greeen' is the correct spelling (3 e's)` | present as "Green Home Solutions of Pickerington" | Present in both, all three systems agree on `2027-02-28`. **No gap and no date issue.** The Notion row was found by content, not by name — the deliberate triple-`e` spelling is what defeated the match |
| MO Dept of Agriculture | **"State of Missouri, Department of Agriculture"** — 9620 State 350, `Unit 105A+B`, exp `2026-12-31`, Active, `Market: Kansas City MO` | **present** — `9620 State 350` / `105A+B`, `leaseEnd 2026-12-31`, Active | Present in both, and HubSpot's `closedwon` / `closedate 2026-12-31` agrees with both. **No gap at all** |

**Carlton L. Handy is unchanged and remains the only real gap here** — re-verified against the current snapshot: a full scan of `leases[]` for "handy" returns zero rows, while Notion carries him live at 2203-2207 Northwood `A4`, exp `2027-02-28`. Still entangled with [OI-217](#OI-217), now also with [OI-230](#OI-230).

**The "P.U.P.S is the one worth looking at first" conclusion above is void** — it rested on the tenant having no record anywhere, which is not the case.

**Root cause of the three false positives is filed separately as [OI-231](#OI-231)** — this is a defect in how the task matches names, not four independent data problems, and it manufactured three "absent" findings of exactly the kind [[feedback_verified_null_vs_inferred_null]] warns about.

**Incidental, not filed:** `9620 State 350` carries both `105A+B` (State of Missouri) and `105B` (J&R ENTERPRISES) as separate active leases — overlapping unit designations at the same property. Noted for whoever adjudicates [OI-215](#OI-215), which concerns that J&R row.

### OI-221
**Status:** OPEN
**Opened:** 2026-09-02
**Source:** `ora-tenant-hubspot-reconciliation` monthly run, 2026-09-02 (Step 8 — Property Register cross-check)
**Acceptance:** Either the Tenant DB's `Market` field is populated (making the Step 8 Market check enforceable), or Step 8 is rewritten to derive Market from Property Address so it stops depending on a field nothing fills.

**Description:** **Step 8's Market cross-check cannot fire: 135 of 138 live Tenant DB rows have a blank `Market`.**

Measured this run against `tenant-db-latest.json` (`as_of 2026-09-02`, 298 rows, 138 with `Row Retired: false`):
- `Market` populated on **3** rows (Columbus OH ×1, Maryland ×1, Kansas City MO ×1) — **97.8% blank**
- `Property Address` populated on **138 of 138** — 0 blanks

Step 8 was added 2026-07-21 specifically to catch property/market attribution churn *mechanically*, after an ad hoc pass produced an intra-session Columbus OH / Salisbury MD regression that self-corrected by chance. With the tenant side of the Market comparison empty, half that check is inert — it has been running on Property Address alone since it was written.

**Property Address side, this run: no churn detected.** Every touched tenant's Property Address resolves to a Property Register row or to the `Sepich Portfolio, Columbus OH (8 props)` umbrella. Two label conventions are recorded here so they are not mistaken for drift later:
- The Tenant DB uses `9620 State 350 — Kansas City MO` where the Register row reads `9620 E State Route 350, Raytown MO` (Register `Market: Kansas City MO`). Same asset, different label.
- Six Tenant DB property labels have no 1:1 Register row and roll into the Sepich umbrella: `2018 Zettler Rd`, `2806 Banwick Rd`, `2822 Banwick Rd`, `392 Morrison Rd`, `3034 Westerville`, `4601`/`4595 E. 5th Ave`. Known convention, not a defect.

**Method caveat:** the live Notion Property Register read was **quota-blocked** this run (`Query Data Source` usage limit). The check was executed against `ora-pm-ledger`'s Property Register cache (`property-register-latest.json`, `as_of 2026-09-02`, 14 rows, same `db_id 19a61fc9-21ed-42d7-a0db-aa730d9a9683`) — same-day and same source, but a cache rather than the live read Step 8 specifies. The row count matches the 14 the skill expects.

**UPDATE 2026-09-05 (`ora-tenant-hubspot-reconciliation` re-run) — Register read live this time; CHURN population identified and deliberately not re-triaged.**

The **live** Register read succeeded this run (14 rows, `Market` values Columbus OH / Maryland / Kansas City MO), so the 09-02 cache caveat is discharged. Two results:

**1. The Market finding holds, and is worse than "blank."** Of 138 live rows, `Market` is populated on 3 and every populated value matches its Register row — **0 mismatches out of 3 comparisons**. The check is not failing, it is not running.

**2. The Property Address side does have churn — 14 tenants — but it is a known, ruled-on population.** Running the exact-match check Step 8 specifies: **0 of 138 live rows match a Register `Property Name` exactly**, because the Tenant DB separates address from city with an em-dash (`29000 Information Ln — Easton MD`) where the Register uses a comma (`29000 Information Lane, Easton MD`). 83 match after normalising separator and street-type abbreviations; the remaining 55 are the Sepich umbrella labels this item already records. **A literal exact-match reading of Step 8 flags all 138 rows** — the check as written is unsatisfiable against the Tenant DB's own address convention.

Scanning instead for the churn shape Step 8 was actually written to catch — one tenant attributed to two different properties — returns **14 tenants**: Airmaster Heating & Cooling, Bayline Visuals, BEK General Contracting, Buckeye's Best Transport, Carlton L. Handy, Complete Cleaning, DDR Enterprise, DELVAL Equipment, Eastern Shore Karate & Fitness, Harold Palmer, Itron, Maryland Hospital Association, Shore United Bank, Tyson Consulting Group.

**In 13 of the 14 the pattern is identical and already adjudicated:** the LIVE row carries one property and a `⛔ ARCHIVED 2026-07-12` retired twin carries a different one, with **the same Lease Expiration on both**. That is the fabricated HubSpot-collision phantom batch [OI-009](#OI-009) documents, on which **Gabriel ruled 2026-07-12: "leave the ~18-25 unconfirmed singletons... do not re-triage."** Not re-triaged here, and **not filed as a new item** — doing so would re-litigate a closed ruling. Recorded so the next run recognises the population instead of re-discovering it.

**Carlton L. Handy is the one exception and should not be swept in with the other 13:** his two rows carry *different* expirations (live 2203-2207 Northwood `A4` exp `2027-02-28`; retired 9050 Red Branch `Suite B` exp `2026-05-31`), so the same-date signature that identifies the phantom batch does not hold. He is also absent from the workbook entirely and sits on the contested A4 — see [OI-217](#OI-217), [OI-220](#OI-220), [OI-230](#OI-230).

**Follow-on for whoever rewrites Step 8:** the exact-match instruction needs to become a normalised match (or the two systems need one address vocabulary), and the phantom-batch signature — retired row, `⛔ ARCHIVED 2026-07-12` title, expiration equal to the live row's — should be an explicit exclusion so the check stops surfacing 13 rows Gabriel has already closed.

**UPDATE 2026-09-06 — Step 8 rewritten; the phantom-signature exclusion above was NOT what got built.** [[reference_step8_churn_population_is_dedup_residue_not_phantom_batch_2026-09-05]] found the signature itself leaks (3 of the 13 — Airmaster Heating & Cooling, Eastern Shore Karate & Fitness, Maryland Hospital Association — carry no expiration or a *different* expiration on the retired twin, so a same-expiration test misses them). `ora-tenant-hubspot-reconciliation/SKILL.md` Step 8 now (a) scopes the whole check to `Row Retired == false` rows, which excludes the entire retired-twin population structurally rather than by signature, and (b) normalises the address comparison (em-dash/comma, street-type abbreviations, Sepich-umbrella labels) instead of exact string match. Closed — no further follow-on for this step.

### OI-222

**Status:** OPEN
**Opened:** 2026-09-02 · **Source:** `ora-appsec-sweep` 2026-09-02 (ora-pm @ `ca62ecbed3aff0a1d21585dcf40f62d823810296`, security-auditor dispatch)
**Severity:** MEDIUM (money-state correctness — webhook resilience)

**Description:** `server/routes/webhook.ts:30-46` inserts the Stripe event id into `stripe_webhook_events` *before* calling `handleStripeEvent`. If the handler throws (e.g. a transient Supabase error), the row is marked `failed` and the endpoint returns 500. Stripe retries the same event; the retry's insert hits Postgres `23505` (unique violation) and the handler short-circuits to `{received:true, skipped:true}` with 200 — the retry is discarded, and nothing ever re-drives a `failed` row.

**Impact:** A lost `payment_intent.succeeded` leaves a real ACH payment stuck at `processing` (balance overstated, risk of a duplicate manual payment). A lost `charge.failed`/`charge.dispute.created` arriving after a `succeeded` event leaves `ar_ledger` counting a returned/disputed ACH as paid (balance understated). Same failure class as the two AR-ledger bugs already shipped in this repo (cartesian fan-out, divide-by-100): correctness of money state depends on an implicit guarantee — here, "every webhook eventually processes" — that isn't actually enforced.

**Candidate fix (NOT applied):** on `23505`, read the existing row's `status`; if `failed`, re-run `handleStripeEvent` and update the row (idempotent updates make this safe to retry). Add a periodic re-drive of `status='failed'` rows (existing cron infrastructure), and a test asserting a Stripe retry after a failed handler actually re-processes rather than silently skipping.

**Auto-check:** none.

---

### OI-223

**Status:** OPEN
**Opened:** 2026-09-02 · **Source:** `ora-appsec-sweep` 2026-09-02 (ora-pm @ `ca62ecbed3aff0a1d21585dcf40f62d823810296`, security-auditor dispatch)
**Severity:** MEDIUM (money-state correctness — accidental double-pay)

**Description:** `ar_ledger.balance` (view, `supabase/migrations/0011_appsec_idempotency_and_scale.sql:118-151`) only credits ACH rows with `stripe_status='succeeded'`. A Stripe ACH PaymentIntent sits in `processing` for 3-5 business days after the tenant authorizes it. During that window, per the documented 2026-07-18 UI ruling, the portal still lists every underlying charge as payable, and `/api/stripe/payment-intent`'s balance cap (`server/routes/stripe.ts:159-168`) still passes because `ar_ledger.balance` hasn't moved yet — `client_request_id` is regenerated on any selection change, so Stripe-side idempotency doesn't cover a second, differently-selected payment either.

**Impact:** A tenant who pays, then (before the ACH clears) pays again — believing the first attempt didn't go through, or paying a different subset of charges — can be legitimately charged twice for the same balance. Refundable, but an operational and trust problem on a live tenant portal.

**Candidate fix (NOT applied):** subtract `SUM(amount) WHERE method='ach_stripe' AND stripe_status IN ('processing','requires_action')` from the cap check in `/api/payment-intent`, and surface pending payments in the Pay Now UI so the tenant can see they've already paid.

**Auto-check:** none.

---

### OI-224

**Status:** OPEN
**Opened:** 2026-09-02 · **Source:** `ora-appsec-sweep` 2026-09-02 (ora-pm @ `ca62ecbed3aff0a1d21585dcf40f62d823810296`, security-auditor dispatch)
**Severity:** MEDIUM (money-state correctness — ledger/display divergence)

**Description:** `server/lib/schemas.ts:74-81`'s `PaymentInsertSchema` allows `method:'ach_stripe'` with no `stripe_status` field, even though `server/routes/payments.ts:28-36`'s own code comment says this admin manual-entry route is for `check`/`wire`/`other` only. A row inserted this way has `stripe_status` NULL, so `ar_ledger` (which sums only `stripe_status='succeeded'` ACH rows) excludes it from the tenant's balance — while `GET /api/payments` and the admin PaymentsList display it as a recorded payment. There is also no unique constraint on manual payments (`check_number` isn't even in the schema), so the same check can be entered twice.

**Impact:** Admin-visible "paid" rows that don't reduce the tenant's actual balance (the exact display/ledger divergence class in this repo's defect history), or duplicate manual entries that double-credit a tenant. Related but distinct from [OI-082](#OI-082), which is about missing uniqueness on non-Stripe payments causing double-COUNTING (understated balance) — this is a schema gap allowing an uncounted-but-displayed row (the opposite-direction bug), on the same route.

**Candidate fix (NOT applied):** restrict `PaymentInsertSchema.method` to `['check','wire','other']`; add `check_number` to the schema; add a partial unique index, e.g. `(lease_id, payment_date, amount, check_number) WHERE method IN ('check','wire','other')`.

**Auto-check:** none.

---

### OI-225

**Status:** OPEN
**Opened:** 2026-09-02 · **Source:** `ora-appsec-sweep` 2026-09-02 (oxford-command-center @ `d30d71ea78f98ebfc1deee4ee6847672baca78d2`, security-auditor dispatch)
**Severity:** MEDIUM (OWASP LLM02 sensitive-information disclosure / Invariant 3 egress)

**Description:** `server/ai/tools.ts:251-269` (`get_alerts` → `evaluateConditions`) and `:238-249` (`get_relationships`) do not filter out confidential deals the way `get_deals`/`search_entities` do — `src/analytics/conditions.ts:786-814` generates deal-insight alerts (LOI/PSA deadlines, next-actions) named for every deal with no `confidential` check, and `get_relationships` returns counterparties/emails tied to confidential deals too. `server/ai/agent.ts:249` then appends tool results verbatim into the outbound `messages` array with no pre-send scan — unlike `server/ai/comps.ts:26-29`, `server/warehouse/om-extract.ts:90-106`, and `server/ai/narrative.ts:118-123,252-254`, which all fail closed on the same Anthropic-API egress. The Pages-mirror path (`functions/api/ai.ts`) runs the identical agent against a snapshot deliberately baked WITH confidential data (`MIRROR_INCLUDE_CONFIDENTIAL=1`), so it inherits the same gap.

**Impact:** A question like "what's at risk right now?" against a confidential deal in an alert-eligible stage (e.g. LOI/PSA within `loiDeadlineWarnDays`) sends that deal's name and free-text `nextAction`/detail to api.anthropic.com. 16 of 22 deals in the committed snapshot are `confidential:true` at this SHA.

**Candidate fix (NOT applied):** share one `redactConfidential()` function (the bake pipeline's `scripts/bake-mirror.ts:78` already has the right shape) between the bake, the agent, and the mirror Function, and/or run `server/briefing/confidential.ts`'s `scanForConfidential` over each tool_result before it's pushed into `messages`, dropping/nulling hits — matching the belt-and-suspenders pattern the other three egress points already use.

**Auto-check:** none.

---

### OI-226

**Status:** OPEN
**Opened:** 2026-09-02 · **Source:** `ora-appsec-sweep` 2026-09-02 (oxford-command-center @ `d30d71ea78f98ebfc1deee4ee6847672baca78d2`, security-auditor dispatch)
**Severity:** MEDIUM (OWASP LLM06 excessive agency — agent-surface hardening)

**Description:** `.claude/hooks/file-guard.mjs:119-126,189-195` releases architect-owned protection on governed files (`server/index.ts`, `src/contracts/**`, migrations, `package.json`, etc. — CLAUDE.md §4) when the sentinel file `.claude/overrides/architect-edit-ok` is fresh (60-min TTL); the sentinel is meant to be touched by a human. `.claude/hooks/bash-guard.mjs:510`'s `GUARD_PATH` covers only `settings*.json` and `hooks/`, not `.claude/overrides/`, and its write-detector doesn't match `mkdir`/`touch`/`New-Item` forms — so `mkdir -p .claude/overrides && touch .claude/overrides/architect-edit-ok` isn't blocked, letting the agent unlock its own edits to governed files. Separately, `.claude/settings.json:31` pre-approves `Bash(npx tsx:*)`, which reaches `data/overlay.json`/`data/warehouse/**` through `fs` — outside the Edit/Write tools the file-guard actually intercepts.

**Impact:** Governor-adjacent files (`server/warehouse/migrations/**`, `src/contracts/**`) and irreplaceable local state can be modified in-session with no human in the loop, defeating the point of the sentinel mechanism.

**Candidate fix (NOT applied):** extend `bash-guard.mjs`'s `GUARD_PATH` to match `\.claude[\\/](?:settings\.json|settings\.local\.json|hooks|overrides)` and add write-shaped forms (`touch`, `New-Item`, `mkdir`, `echo >`) to its detector; better, make the sentinel's content an HMAC over the current date keyed from a secret outside the repo (unreadable via `permissions.deny`) so the agent cannot forge it by writing the file. Narrow `Bash(npx tsx:*)` to `Bash(npx tsx scripts/*)`.

**Auto-check:** none.

---

### OI-227

**Status:** OPEN
**Opened:** 2026-09-02 · **Source:** `ora-appsec-sweep` 2026-09-02 (oxford-command-center @ `d30d71ea78f98ebfc1deee4ee6847672baca78d2`, security-auditor dispatch — item-3c mandatory hook-change check)
**Severity:** LOW (the scan logic itself was assessed non-weakening; this is a narrower installer gap)

**Description:** Two commits touched hook logic inside this sweep's lookback window: `ead629d` (2026-08-22, `scripts/prepush-confidential-scan.mjs`) and `3d4de2a` (2026-08-24, `scripts/install-git-hooks.ts` + `scripts/prepare-hooks.mjs`). `ead629d` is a strengthening change (adds a fail-closed structural `confidential:true` payload check). `3d4de2a` converted the hook installer to `.ts`-via-`tsx`; `prepare-hooks.mjs:21-27` now exits 0 **without installing the pre-push hook at all** when `tsx` is absent from `node_modules` (e.g. a checkout built with `npm ci --omit=dev`) — no warning is printed.

**Impact:** A checkout installed without devDependencies silently has no pre-push confidentiality scan; a push from that checkout is unscanned. This repo is the one with the ratified private-repo confidentiality exception (S-001), so the residual exposure is bounded, but the hook is still the documented enforcement mechanism and its installer should not fail silently.

**Candidate fix (NOT applied):** have `prepare-hooks.mjs` write its builtin `WRAPPER` string directly (already a constant in the file) when `tsx` is unavailable, rather than skipping installation.

**Auto-check:** none.

---

### OI-228

**Status:** OPEN
**Opened:** 2026-09-02 · **Source:** `ora-appsec-sweep` 2026-09-02, DISPATCH INTEGRITY GATE assertion 4 (post-hoc model-floor probe, mandatory per SKILL.md v1.5+)
**Severity:** LOW (tooling false-positive, not a real floor breach)

**Description:** `~/.claude/maintenance/check-dispatch-model-floor.py --floor claude-opus-4-8` exited 1 ("FAIL — below-floor model") against both of this sweep's subagent transcripts. Root cause: its `MODEL_RANK` table recognizes only `claude-mythos-5` and `claude-fable-5` (rank 100) — it has no entry for `claude-fable-5-1`, the model id this session's own environment reports as the current Fable 5.1 release, so `model_rank()` falls through to `UNKNOWN_RANK = -1` (fail-closed by design for genuinely unplaceable ids) and reads a valid top-tier model as a violation.

**Verified directly** (not just inferred from the probe's summary line): `agent-ae4ff02601b0e1cdb.jsonl` (ora-pm dispatch, 62 assistant messages) and `agent-ae7f6e4c49d408b89.jsonl` (oxford-command-center dispatch, 110 assistant messages) both show `message.model:"claude-fable-5-1"` on every single line, with **zero** `"type":"fallback"` events in either transcript. Both dispatches ran entirely on Fable for their full duration — the best possible outcome under Gabriel's ratified Option C (2026-07-24), not a degradation.

**Distinct from [OI-052](#OI-052).** OI-052 documents a real, repeatedly-observed mid-run fallback pattern (`claude-fable-5` → `claude-opus-5`/`claude-opus-4-8`), ruled compliant 2026-08-14 because Opus is still top-tier. This item is a different mechanism entirely: no fallback occurred; the probe's own lookup table is stale.

**Per the sweep's own doctrine, this had to be recorded and escalated regardless of diagnosis** ("Do NOT 'fix' a firing by loosening the floor below Opus or deleting the assertion") — see the completion report / escalation email for the mandatory MODEL-FLOOR BREACH notice. The actual fix belongs in the probe script, not the floor logic: add `claude-fable-5-1` (and, proactively, `claude-mythos-5-1`) to `MODEL_RANK` at rank 100.

**Candidate fix (NOT applied):** `~/.claude/maintenance/check-dispatch-model-floor.py` — add `"claude-fable-5-1": 100` and `"claude-mythos-5-1": 100` to `MODEL_RANK`. Out of scope for this report-only task to apply (the file lives outside both audited repos and this task's writes are limited to Notion/tracker/scratch/worktrees).

**Auto-check:** none.

---

### OI-181
**Status:** OPEN
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

**Why it is not cosmetic:** `notes` is not part of the artifact key (which is content+path based), so the gate still **PASSES** and the commit lands. The failure is invisible at exactly the moment the audit trail is being created, on the tool whose entire job is to prove a blast-radius change was reviewed.

**Live exposure at filing:** `--notes-file` is the ONLY flag divergence between live and the stale copy (all 15 others match). Of 3 live worktrees, **1 is stale** — `oi173-spec-liveness-probe` (0 `notes-file` refs); `build-lane-capability-check` and `.claude-worktrees/retro-fixes` both have it. Flag landed in `fe14d91` (2026-08-16, PR #136); any worktree branched before that commit is exposed. Not fixed in that worktree — it is another session's workspace.

**Suggested fix (not applied — `hooks/**`, needs the review pass):** in the `--record` path, reject any `--`-prefixed token not in a known-flag set, exiting non-zero. ~10 lines, and it converts silent skew into a loud failure for *every* future flag, not just this one. Optionally add a `__version__` stamped into the artifact so skew is visible after the fact. Ownership note: `eos-review-gate.py` was last touched by session `6797e01b` (retro tooling fixes).

### OI-183
**Status:** OPEN
**Opened:** 2026-08-16
**Source:** Mirror-deploy incident chain, this session — discovered while landing [#280](https://github.com/ZeOoba/oxford-command-center/pull/280) and [#282](https://github.com/ZeOoba/oxford-command-center/pull/282), reproduced twice same evening.
**Acceptance:** A merged `oxford-command-center` PR is reflected on the canonical checkout (`C:\Users\Owner\oxford-command-center`) within one cycle of whatever reads it unattended — or, at minimum, `mirror-run-classify.ps1`'s own output flags when its on-disk code is behind `origin/main`, so the weekday drift-check task's silence stops being ambiguous between "healthy" and "stale classifier."

**Description:** **The canonical `oxford-command-center` checkout has no auto-update mechanism, so a merged PR now reads as "landed" while the checkout that unattended tooling reads from sits behind it indefinitely.**

**Root cause.** [PR #279](https://github.com/ZeOoba/oxford-command-center/pull/279) (isolated build root, same incident chain) deliberately removed `deploy-mirror.ps1`'s `git merge --ff-only` of the shared checkout — correctly: that fast-forward was an unattended job mutating a tree other sessions actively build from, exactly the class of hazard this whole PR chain exists to close. But nothing replaced its **incidental** side effect of keeping the canonical checkout current. The deploy itself is unaffected — the isolated build root pulls `origin/main` directly, by design — but everything else that reads FROM the canonical checkout now silently runs whatever was on disk at last fast-forward.

**Reproduced twice, same evening, both times manually fixed:**
1. #280 (classifier premise fix) merged to `origin/main` at `f03817f`. Canonical checkout stayed **0 ahead / 1 behind** — the corrected classifier code was live on GitHub and dead on disk — until fast-forwarded by hand.
2. #282 (W0/W2) merged to `origin/main` at `c0262d4`. Same symptom, same manual fix, same evening.

**Why this matters more than an ordinary stale-checkout nuisance:** `mirror-run-classify.ps1` — the exact file #280 just fixed — is run **unattended** by the `ora-command-center-mirror-drift-check` scheduled task (weekday 10:40 AM ET, emails `ggoldberg@oxfordra.net` only on alarm). If that task fires against a behind checkout, it silently classifies using superseded logic, with no symptom distinguishable from a correct run — the identical failure shape #280 was filed to fix (a check making a claim that was true when written and is false now), just one layer up: the checkout carrying the checker can itself be the stale artifact. `mirror-run-classify.ps1` already computes `$behind` (used today only for the ahead/behind JSON fields) but nothing currently treats "behind" as "my own logic may be outdated" — the closest existing signal, `gitAhead`/`aheadFlag`, was corrected by #280 specifically to say it does NOT affect what the mirror serves, which is the opposite framing needed here.

**Scope check — confirmed NOT a threat to the mirror itself.** The isolated build root (`<repo>-deploy-build`) fetches and hard-resets to `origin/main` on every run, independent of the canonical checkout's state — proven by #279's differential test and by three consecutive clean unattended deploys (18:00/19:00/20:00) while the canonical checkout sat behind. This item is about the correctness of tooling that reads the canonical checkout, not about mirror freshness.

**Not fixed — flagged rather than built, given scope for the session that found it.** Two directions worth weighing, not chosen: (a) teach `mirror-run-classify.ps1` to `git fetch` + `merge --ff-only` itself before classifying — low-risk since ff-only cannot destroy uncommitted work and this is a report-only script, not a deploy, but it reintroduces an unattended job touching the shared checkout, the exact pattern #279 removed elsewhere; or (b) a louder self-check — surface `$behind > 0` as an explicit "this run's own logic may be stale" field distinct from the existing ahead-check, so the drift-check task's silence stops covering for it. (b) is safer and smaller; (a) is more complete. Also worth its own item, related but distinct: nothing verifies the build root actually synced to the CURRENT `origin/main` tip on a given run (flagged in #280's PR description, not filed here — same root cause, different consumer).

**No lingering damage from the triggering incident:** the empty artifact was overwritten by a re-record at the same key; both of this session's artifacts carry notes (513 and 1,511 chars).

### OI-176
**Status:** LANDED 2026-08-16, awaiting steady-state confirmation
**Opened:** 2026-08-16
**Source:** `/doctor` health-check pass (session 76023481), hook-timing aggregation over 180 session transcripts (2026-08-09 → 2026-08-16).
**Acceptance:** `PreToolUse:Bash` median below ~400 ms over ≥100 recorded runs **dated to the measurement day** (see the method warning below). **NOT yet met — only 2 post-landing samples exist (median 429 ms), which is not a measurement.** Re-run the arm-split check after normal use; it keys on whether the recorded hook `command` contains `--chain bash`, so it never has to guess a date.

**LANDED:** worktree commit `f07b257` (branch `feat/oi176-bash-dispatcher`), landed live as `2800595` on Gabriel's in-turn "land it". Dispatcher copied first and verified while settings.json was still the old 15-entry version — safe, because the old settings passes no `--chain` and the dispatcher defaults to the Edit/Write chain; settings.json landed second. Reverse order would have passed `--chain bash` to a dispatcher that ignores argv, silently running the Edit/Write chain on Bash.

**Post-landing live verification** (not just pre-merge testing): settings.json parses; 11 PreToolUse groups; exactly ONE matcher fires on `Bash`; no matcher matches the empty string; allow 91 / deny 27 / `bypassPermissions` / all 6 hook events intact. Benign Bash passed. Override token removed, then a deliberate block probe was BLOCKED **and the harness attributed it to `pretooluse-dispatcher.py --chain bash` running config-write-guard, message verbatim** — the gate still gates. Reviewed independently twice (claude-fable-5): 38-tool ordered-coverage parity vs HEAD, `BASH_GUARD_CHAIN` = HEAD's Bash guards 10/10 in order, `GUARD_CHAIN` byte-identical, fail-closed probed empirically. Author differential harness: 30/30 identical exit codes vs the real 10-process chain, editwrite chain passing as an unchanged control, ~750 ms to ~130 ms.

**Description:** **The Bash hook chain is 10 cold Python starts on every Bash call.**

**Half 1 (hookify) — WITHDRAWN 2026-08-16, same day as filing. Not a live defect.** As originally filed this item claimed the `claude-plugins-official` **hookify** plugin was firing no-op `pretooluse.py`/`posttooluse.py` on 100% of tool calls. The underlying facts about hookify are accurate — it has no rules to evaluate (`core/config_loader.py:210` globs `.claude/hookify.*.local.md`; no such file exists under `~/.claude`), it returned `{}`, and `pluginUsage` records 225,556 lifetime invocations — **but it stopped running on 2026-08-13.** Last recorded attachment: `2026-08-13T07:49:58Z`. Zero Read-event hook runs on 08-14, 08-15, 08-16, or in the filing session itself; since no hook in `settings.json` matches `Read`, Read-event runs are a clean liveness proxy for hookify and that count is now zero. **There is nothing to disable — do not go hunting for a Cowork `/plugin` toggle.**

**⛔ How the stale claim got filed, because the method error will recur.** Hook timings were bucketed by **transcript file mtime**, not by each event's own `timestamp`. A resumed session's `.jsonl` is touched today while containing lines from days earlier, so selecting "the 50 most recently modified transcripts" and calling it a 2-day window silently swept in week-old events. `PreToolUse:Read n=32, median 1,563 ms` was reported as current activity when every one of those runs predated 08-13. **Rule: bucket transcript metrics by the event's own `timestamp`; mtime chooses which files to open and never dates the lines inside them. Confirm any "live" claim is non-zero on today's date specifically.** Detail: [reference_hookify_noop_hooks_every_tool_call.md](reference_hookify_noop_hooks_every_tool_call.md).

**Half 2 — LIVE, and correctly measured. The PreToolUse:Bash chain is 10 cold Python starts.** Date-scoped confirmation: **153 `PreToolUse:Bash` runs on 2026-08-16 alone**, so unlike half 1 this is current config, and it is uncontaminated by hookify (which had already stopped). Ten of the 31 hooks configured in `~/.claude/settings.json` match `Bash`, each paying a fresh interpreter start. Measured: `PreToolUse:Bash` n=278, median **716 ms**, p90 2,310 ms, max 5,682 ms; `PostToolUse:Bash` median 610 ms, p90 2,224 ms, max 6,513 ms. Both exceed the >2s-at-p90 guidance for per-tool-call hooks. Bash is by far the hottest tool — **4,466 calls in 1.9 days**.

**The fix already exists in-tree.** `hooks/pretooluse-dispatcher.py` already consolidates `Edit|Write|MultiEdit` behind one process, and `PreToolUse:Edit` measures **461 ms median vs Bash's 716 ms** across a comparable run count. Extending the same dispatcher to the Bash matchers is the proven pattern, not a new design.

**BLOCKED on a live claim at filing time:** slug `hooks-override-auth` was held by session `6797e01b`, which was concurrently editing `eos-review-gate.py` — one of the very Bash hooks this would consolidate. Do not start half 2 without re-checking `claim_work.py list`.

### OI-174
**Status:** OPEN
**Opened:** 2026-08-16
**Source:** Observed twice at the `~/.claude` pre-push gate during the recursive-delete-guard work (session 6797e01b), then characterised directly.
**Acceptance:** Either (a) `maintenance/_tests/test_allocate_oi_id.py` survives a deliberate concurrent-load reproduction (N parallel invocations against one reservations log) with 0 failures, or (b) the gate's fail-retry path prints the FIRST attempt's failing assertion, so the next occurrence is diagnosable without reproduction. (b) alone closes this; (a) alone does not, unless it also proves the root cause.

**Description:** **FLAKY TEST, plus a diagnostic gap that is the more valuable half.**

`hooks/git-prepush-hook-tests-gate.py` reported: `fail-retry (FAILED once, passed on the rerun; not blocking, but this file is FLAKY and should be fixed): maintenance/_tests/test_allocate_oi_id.py`.

**Characterised, not assumed:** 5 consecutive isolated runs pass (exit 0, no output). So it is NOT deterministically broken — it is load/timing sensitive, consistent with the concurrency class already recorded for this checkout (26 concurrent sessions, python spawn cost measured at 348ms rising to 1390ms; see the OI-119/127/135 cluster). The file contains 12 occurrences of time/concurrency/tempfile constructs, which is where to look. **Do not burn time trying to reproduce it standalone — that has already been tried and it passes.**

**The diagnostic gap.** The gate's retry mechanism is working as designed (absorb transient contention, don't block), but it reports only that a file failed once — **not which assertion failed on the first attempt**. So every occurrence is unfalsifiable after the fact: there is no artifact to diagnose, and the only options are guessing or waiting for a recurrence. Capturing the first attempt's output on a fail-retry would make this and every future flake diagnosable.

**Why it matters more than a typical flake:** this is the test for `allocate-oi-id.py`, the tool that hands out OI ids. Hand-computed ids have collided three times historically (OI-027/061/066), which is why the allocator exists. A flaky test on the collision-prevention tool is the wrong thing to leave uncharacterised — and this very session used the allocator twice (OI-172, OI-174).

### OI-172
**Status:** OPEN
**Opened:** 2026-08-16
**Source:** Rev 2 fleet re-check (session 6797e01b). Reopens the follow-up left open by the 2026-08-15 T3-12 migration and re-stated in event_log.md on 2026-08-16.
**Acceptance:** `list_scheduled_tasks` run FROM A COWORK SESSION shows `ora-passed-deal-tracker` with the LAMS/Cowork `path` (`...\Documents\Claude\Scheduled\ora-passed-deal-tracker\SKILL.md`) at `enabled: false`, while the CC/MCP entry (`~\.claude\scheduled-tasks\...`) remains `enabled: true`. Verified by pasting both entries.
**Description:** **DUAL-FLEET TWIN STILL LIVE.** `ora-passed-deal-tracker` is registered on BOTH fleets at the same cron (`30 6 15 * *`). Gabriel-directed item T3-12 moved it LAMS -> CC/MCP on 2026-08-15 because the LAMS surface has no path to `scheduled-tasks/_shared/send-via-outlook.ps1`, the sole Outlook COM send path — confirmed by a live "SEND FAILURE — no COM access" surfaced by an `ora-pm-ledger` run. The CC copy is therefore the one that must SURVIVE; the LAMS copy must be disabled.

**Why this cannot be done from Code (do not retry here):** the taskId is IDENTICAL on both fleets and `list_scheduled_tasks` from CC/MCP returns CC-only entries (38 entries, zero LAMS `path`s — verified 2026-08-16). So `update_scheduled_task(taskId:"ora-passed-deal-tracker", enabled:false)` issued from Code resolves to the **CC** copy — disabling exactly the twin meant to survive and leaving the COM-less one firing silently. Requires a Cowork-session `enabled:false` toggle. **NEVER the Scheduled-sidebar delete/trash icon** — folder-destructive, and the standing warning that it can break a same-id task on the other fleet is not theoretical here, because the ids collide.

**Mitigated, not resolved:** the double-fire guard (PR #116, `c16667c`) is now LIVE in the working tree (verified 2026-08-16: 7 `block-sentinel`/`outlook-sent-probe` hits in the CC SKILL.md, landed via `90d02ae`), so the 2026-09-15 06:30 ET fire will not double-send. That removes the urgency, not the defect — the LAMS twin still runs and still cannot send.

**Correction recorded:** the Rev 2 Fleet Operations Report initially described the CC copy as "never fired — dead weight" and a retirement of the CC copy was requested on that basis. That inference was wrong: the CC copy has never fired because it was registered 2026-08-16 11:47 on a monthly cron (`nextRunAt 2026-09-15T10:34:44Z`). It is new, not dead. The artifact has been corrected.

### OI-158
**Status:** OPEN
**Opened:** 2026-08-15
**Source:** Manual T3-5 cross-check (Gabriel-directed workflow-optimization pass), applying `ora-tenant-hubspot-reconciliation`'s existing Step 3d (DATE-MISMATCH) logic ahead of its next scheduled run (2026-09-01, 08:15 ET)
**Description:** **DATE-MISMATCH** — Sky Shield. Workbook (`portfolio.json`-derived source of record): `leaseEnd 2029-08-31`, `status Active` — the lease was renewed to a new multi-year term. HubSpot deal "Sky Shield — Lease Renewal 2026-09-30" is still `dealstage=appointmentscheduled`, `closedate=2026-09-30` — the original pre-renewal deal was never closed out to reflect the executed renewal. Same failure class as the 2026-07-16 lease-date correction (J&R/Stone Crest/Chesapeake — see [reference_hubspot_missed_lease_date_correction.md](reference_hubspot_missed_lease_date_correction.md)), different symptom: a stale open deal rather than a stale wrong date. Recommended correction (not applied — this task never writes to HubSpot itself): advance the deal to `closedwon` with `closedate` matching the executed renewal, or close it out and open a fresh renewal-tracking deal per current process. `ora-tenant-hubspot-reconciliation`'s 2026-09-01 run should independently re-surface and can formally close this.

### OI-159
**Status:** OPEN
**Opened:** 2026-08-15
**Source:** Manual T3-5 cross-check (Gabriel-directed workflow-optimization pass), applying `ora-tenant-hubspot-reconciliation`'s existing Step 3d (DATE-MISMATCH) logic ahead of its next scheduled run (2026-09-01, 08:15 ET)
**Description:** **DATE-MISMATCH** — Medspeed, LLC. Workbook (`portfolio.json`-derived source of record): `leaseEnd 2029-08-31`, `status Active` — the lease was renewed to a new multi-year term. HubSpot deal "Medspeed — Lease Renewal 2026-08-31" is still `dealstage=appointmentscheduled`, `closedate=2026-08-31` — the original pre-renewal deal was never closed out. Same pattern and same recommended correction as [OI-158](#OI-158); filed as a separate item per this tracker's one-row-per-finding convention.

### OI-160
**Status:** OPEN
**Opened:** 2026-08-15
**Source:** Investigation of the missing OI-157 row while checking its status (Gabriel-directed, this session, 2026-08-15/16)
**Description:** **RECURRENCE of the OI-098/OI-124 merge-conflict row-loss failure class.** OI-157 (filed correctly in commit `7c9740a`) was silently dropped from this file not once but TWICE during same-day merge activity on the `feat/model-canary-probe-step25` line: (1) merge `318de35` ("Merge branch 'feat/model-canary-probe-step25' into reconcile/canary-146-merge-2026-08-15") listed this file among its CONFLICTS; one parent (`a343dae`) had the OI-157 row, the other (`fa1fc5c`) didn't, and the resolution kept the version without it. (2) The next merge, `ba93c70` (merging `origin/feat/model-canary-probe-step25` back into the working branch), had a CLEAN surviving copy on one parent (`ff9451d`, count=1) and the already-lost copy on the other (`318de35`, count=0) — yet the result was 0 again, meaning even a live, uncontested copy sitting one merge away wasn't picked up. Confirmed via `git show <parent>:<path> | grep -c OI-157` on all four parent/result pairs. `git log -S` (pickaxe) in its default mode found NEITHER removal — it silently skips merge-commit diffs unless run with `-m`, which is exactly how this class of loss hides from a routine `-S` audit; only `git log --merges -SOI-157 -m` surfaced the two merges. Distinct from OI-098's split-row/blank-line mechanisms — same symptom (a row vanishes with no visible removing commit under a normal `-S` search), different, unexamined cause (merge-conflict resolution, not a formatting defect in a single-parent commit). Not yet root-caused (was this an agent-resolved conflict that didn't diff-review the result before committing?) or fixed. Candidate detector: a periodic sweep comparing `git log --merges -m` diff output across recent merges touching `open-items-tracker.md`/`event_log.md`, flagging any merge where a row/section present on a parent is absent from the result.

### OI-161
**Status:** OPEN
**Opened:** 2026-08-15
**Source:** Investigation of OI-137/OI-143's orphaned sections while checking their status (Gabriel-directed, this session)
**Description:** **Recurring authoring-gap, distinct from OI-160's merge-conflict mechanism.** A batch-filing commit writes a full `### OI-NNN` narrative detail section but never adds the matching one-line Open-table row — the section then sits invisible to anyone scanning the Open table, with no removing commit to find (there was never a row to remove). Two independent instances confirmed via `git log -G"^### OI-NNN"`: `### OI-137`'s header was introduced in `1cfbc3c` ("memory(OI-138): file the eos-review-gate scoping + key-mismatch defect") — that commit added a proper row for its own headline item, OI-138, but only the bare section for OI-137. `### OI-143`'s header was introduced in `7463e48` ("file OI-143/147-154, root-cause OI-137, close OI-148") — same pattern: rows landed for OI-147/148/149 in that commit, OI-143 got only its section. Both orphaned sections described real, substantive, still-open defects (OI-137: NOI cross-check failure; OI-143: silent-zero expense parsing) that were effectively invisible to the tracker's own purpose for 2-4 days each. `check-open-items-duplicate-ids.py`'s existing `ORPHANED_SECTION` check already detects this class (that is how both were found) — the gap is upstream, at authoring time, not detection time. Not yet fixed: no mechanism stops a session from writing a section without its row in the first place; the duplicate-id checker is currently audit-only (report, not gate). Candidate fix: wire `check-open-items-duplicate-ids.py`'s orphan/missing findings into the pre-push doctrine gate (WARN first, per the OI-id enforcement rollout precedent) so a session filing an item gets caught before the commit lands, not days later during an unrelated investigation.
**Recurrence 2026-08-21 (repo-architecture-review remediation):** `check-open-items-duplicate-ids.py` reports 7 fresh `BROKEN_ANCHOR` rows — OI-187 through OI-193, the 2026-08-17 tax-sprint batch — rows with no `### OI-NNN` detail section, linked from another memory file, so those links resolve to nothing. This is the inverse shape (row present, section missing) of the row-missing-for-a-section case documented above, same root cause: nothing gates authoring-time completeness. Noted per the 2026-08-21 audit's handoff brief; writing the 7 missing sections was explicitly left out of scope unless Gabriel asks.

### OI-163
**Status:** CLOSED
**Opened:** 2026-08-16
**Closed:** 2026-08-16
**Source:** Cross-repo architecture-diagram review (Gabriel-directed, this session) — `AAOS/README.md` §1 and its cited `docs/DELIVERABLES-MANIFEST.md`; corroborates the existing memory pointer [[project_aaos_agent_coordination_layer]] ("real infra; Cowork round-trip unreachable from Code")
**Description:** **MEDIUM** AAOS (`C:\Users\Owner\AAOS`) is a filesystem-based Code↔Cowork task-queue/handoff protocol over an OneDrive-synced "seam" — no daemon, no network listener. It self-grades as v1.0 feature-complete: 216 unit/integration tests (all green), 6 documented adversarial gate reviews, 5 ADRs. But the README states directly that the one capability the whole system exists to prove — a live, same-session round-trip confirming a real Cowork session can read/write the seam — "has explicitly still [been] open": `t-cowork-seam-confirm.json` sits queued and unconsumed in the live seam as of this review. `docs/DELIVERABLES-MANIFEST.md` additionally records that none of the six phase gates received explicit Gabriel sign-off before the next phase began — each was presented and the project simply proceeded. In production, only `tools/expire-leases.py` actually runs unattended (`ora-aaos-expire-leases`, CC/MCP fleet, 3x/day since 2026-07-10); every other component (task lifecycle CLIs, handoffs, the Notion projection publisher) is unexercised outside its own test suite.
**Fix direction:** either force one genuine live round-trip (a real task created by Code, leased/completed by an actual Cowork session) to validate the core claim, or stop counting AAOS as shipped/production infrastructure in future audits until it is — right now it is unproven maintenance surface with a real (if patched) history of concurrency bugs (see the README's own event-log clobbering note).
**Evidence:** The round-trip had ALREADY genuinely happened — over a month before this item was filed. `handoffs/h-cowork-seam-ack-e7c490.json` (posted 2026-07-10T13:46 -04:00 by a real Cowork session, per its own context_summary: ran the COWORK-BOOTSTRAP.md probes for real, landed in SAFE-BY-HAND mode after Probe X's `validate.py` subprocess exited 1 on a jsonschema import error, then wrote the handoff + a paired spool event per §7) satisfies all three acceptance criteria — verified directly this session, not taken on the handoff's own word: `grep`'d `aaos-events.ndjson` and confirmed the paired `HandoffPosted` event was drained (`e-2026-07-10T17:46:23.580832Z-826571`), and ran `python tools/validate.py` against the handoff file → `VALID`. The actual gap all along was that Cowork's handoff explicitly said "a Code session should drain the spool... and may then lease/complete/archive the task" — and no Code session ever did. Closed properly this session: `tools/lease-task.py` + `tools/complete-task.py --archive` against `t-cowork-seam-confirm`, evidence citing the handoff/event/validation above. Task now `state:"archived"`. A companion handoff from the same Cowork session (`h-cowork-jsonschema-pin-request-9ac653.json`) also flagged that Cowork's `jsonschema` package fix was session-local/non-durable and spawned a follow-up task, `t-cowork-jsonschema-pin-952743` — **that one is still open**, unrelated to this closure, worth a separate look if Cowork FULL-EXEC parity is ever wanted.

### OI-164
**Status:** OPEN
**Opened:** 2026-08-16
**Source:** Cross-repo architecture-diagram review (Gabriel-directed, this session) — `ora-skills/README.md` "Dual-write discipline" and "Cowork-side skill edits" sections; related [OI-142](#OI-142)
**Description:** **MEDIUM** The `ora-skills` git repo (source of truth) and the Cowork AppData runtime-cache mirror are two independently-writable copies of every installed skill. Reconciliation is entirely after-the-fact drift *detection* — `tools/hooks/pre-commit` Check 4 (`sync_appdata_mirror.py --check-staged`) on every commit, plus a separate full-sweep `tools/repo_first_check.py` a session is supposed to remember to run before non-trivial work — not structural prevention of the second write surface existing at all. The README documents this has already produced real incidents, not just theoretical risk: `masterlease-jurisdiction-rebase` drifted cache-ahead of the repo three times in one session (2026-08-04), twice caught only by manual diffing because nothing ran the check automatically. [OI-142](#OI-142) is an independent instance of the same root cause: `exception-detection`'s runtime cache held a v1.3 `SKILL.md` with zero commit anywhere in git history, installed straight from an uncommitted working tree via Cowork's "Save skill" — `repo_first_check.py` Check 5 only fires at commit time and structurally cannot catch an install that never gets committed.
**Fix direction:** the root cause is having two write surfaces for one artifact; better/faster drift detection only bounds how long a divergence survives, not whether it occurs. If Cowork's skill-import mechanism can ever be pointed at reading directly from the git source (rather than importing into a separate cache copy), that removes the second copy structurally instead of continuing to invest in diffing it after the fact.

### OI-166
**Status:** FIXED 2026-08-16
**Opened:** 2026-08-16
**Source:** Live concurrency near-miss during the `ora-passed-deal-tracker` double-fire-guard session (Gabriel-directed) — [[event_log]] 2026-08-16
**Description:** `claim_work.py claim` refuses (exit 3) when a live claim exists **under the same slug**, but never asks whether a live claim under a *different* slug already covers the same `--paths`. Observed live: this session held `open-items-tracker` while session `30b5a31f` held `repo-housekeeping`, both declaring `memory/open-items-tracker.md` and `memory/MEMORY.md` — the exact two files each was trying to settle. Neither refusal could fire, because the gate is keyed on slug, not path. Both sessions independently root-caused the same blocked pull; only luck (the other claim being released first) prevented duplicate commits.
The overlap primitive was **not** missing: `claims_touching()` has existed and is wired into `shared-checkout-guard.py:362` on the Edit/Write hot path, and into `dirty-file-owner-report.py`. It was simply never consulted by the `claim` command itself, so overlap surfaced only *after* someone edited a file — too late to prevent duplicated investigation.
**Fix applied:** wired `claims_touching()` into the claim path so a cross-slug `--paths` overlap is surfaced at claim time, naming the other slug and session. Deliberately a **loud warning, not a refusal**: the module's docstring endorses distinct slugs as a feature ("a distinct slug keeps BOTH claims independently visible"), and its ratified design is fail-open, not a hard lock — a refusal here would wedge legitimate broad-`--paths` claims. Making the overlap *visible at claim time* is what "independently visible" was always meant to deliver.

### OI-167
**Status:** OPEN — filed, deliberately NOT fixed
**Opened:** 2026-08-16
**Source:** Same session — 5 read-only Bash calls blocked by `config-write-guard.py`
**Description:** The guard blocks pure READS whenever a command's text pairs a governance path with anything write-shaped. Confirmed trips this session, all read-only: `2>&1` (stderr redirect), `git merge-tree --write-tree`, a `grep` for the literal `<<<<<<<` conflict marker, a `||` fallback echo, and a `printf` format string. Each cost a round-trip and a reformulation.
**Why this is filed rather than fixed:** the breadth is deliberate and ratified. [[feedback_autonomy_gate_matcher_cannot_be_safely_narrowed]] records FOUR independent narrowing attempts (2026-07-16 ×3, 2026-08-13 ×1) that each found a real, confirmed bypass — the fourth using a real shell tokenizer rather than a regex, and still failing on a more fundamental problem (quoted text is not inert; it is still a command argument). A fifth attempt from this session would be the fifth failure. The guard's own error text already names the correct escape: use Read/Grep/Glob, which are never gated. That worked, and is what this session ultimately did.
**Live-work overlap — check before touching:** session `6797e01b` claimed `hooks-override-auth` at 14:37 on 2026-08-16 for "close command-position false-positive class first", covering `hooks/lib/tool_call_paths.py`. That is the same false-positive class. Any work here must reconcile with that session first.
**Fix direction (if ever pursued):** additive only — a read-only escape that does not touch the matcher, e.g. a sanctioned read wrapper. Never narrowing.

### OI-168
**Status:** OPEN
**Opened:** 2026-08-16
**Source:** Same session — first `git push` killed at 120s having completed its work
**Description:** `~/.claude`'s pre-push chain (86 hook tests, the full doctrine-integrity probe, backup-coverage/declassification-residue/identity/stage-exclusion sweeps) routinely runs past the Bash tool's default 120s timeout. The push was SIGTERMed at the wire after every gate had passed; `git ls-remote` was required to establish whether the ref had actually moved before it was safe to retry. A retry with a longer window succeeded unchanged.
**Not a repo defect.** The gate is doing exactly what it should; the mismatch is between its runtime and a client-side default. Recording it so the next session does not misread a timeout as a failed or partial push.
**Fix direction:** document the required timeout at the push site, or split the slow full-tree sweeps behind a fast path so the common case fits the default. Note the sweeps are the part with real value — speeding them by weakening them would be a bad trade.

### OI-169
**Status:** OPEN
**Opened:** 2026-08-16
**Source:** Same session — own worktree emptied mid-task
**Description:** The git worktree this session was running in (`.claude/worktrees/wizardly-hamilton-626cbd`) was emptied to 0 entries by another session while still checked out and in active use. Every tool path resolving through it broke mid-task, including `python hooks/lib/claim_work.py` — which is the *sanctioned* escape hatch for [OI-167](#OI-167)'s read false-positives ("re-run the command against a WORKTREE checkout's copy of the tool"). Losing the worktree therefore removed the documented workaround for a different guard at the same time.
**Why it matters beyond the inconvenience:** worktree cleanup appears to reclaim on staleness/emptiness heuristics without checking whether a session is live *in* the tree being removed. The claim system already knows which sessions are live and what they cover; cleanup does not consult it.
**Fix direction:** have worktree cleanup consult live claims / session liveness before removing a tree, or refuse to reclaim a worktree whose path is any live session's `cwd` (claims already record `cwd`).

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

### OI-009
**Status:** OPEN (substantial progress made 2026-07-17, real scope remains)
**Opened:** 2026-07-17
**Source:** [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md)
**Description:** OI-008's sweep for the Escalation-Date/Lease-Expiration column-mapping bug could
only check the 79-pair Notion↔workbook reconciliable overlap (a real workbook counterpart is
required to compare against). 93 live Notion Tenant DB rows have no workbook counterpart at all
(family-join miss, or genuinely off-workbook tenants/vacant slots) and have never been
independently verified against primary lease documents. Gabriel confirmed (2026-07-17, via
AskUserQuestion): worth tracking, low priority — not urgent, likely a future bulk
lease-abstraction pass across ~93 tenants rather than a quick check.
**Progress 2026-07-17 (same session, later): 21 corrections written and verified, plus 2 new
systemic bug classes discovered beyond OI-008's Escalation-Date pattern.**
- **Triage first, cheap wins:** re-joined all 93 `notion_only` rows against the 64 `workbook_only`
  rows by tenant name (not the street-family+unit key OI-003 used, which missed these on
  unit-string formatting) — found 18 "free" matches. 14 already matched the workbook exactly (no
  action). 3 Heritage Pool duplicates were stale cache, already resolved under OI-005. 1 fuzzy
  match (GT Industrial Supply) was untrustworthy, not acted on. Of the ~20 remaining
  no-address/no-status rows, matched the documented fabricated HubSpot-collision phantom batch
  (Gabriel 2026-07-12: "leave the ~18-25 unconfirmed singletons... do not re-triage") — excluded,
  not chased.
- **2 direct lease-date corrections** (workbook `Lease Start`/`Escalation Date` miscopied into
  Notion `Lease Expiration`, same root pattern as OI-008, just outside its 79-pair overlap):
  Columbus Suburban Construction `32b6ecd8-9e59-8169-9c1b-c3407f38ebd5` 2026-09-01→2026-08-31;
  Richwood Equipment Company LLC `32f6ecd8-9e59-8190-ab42-ce4ed3289340` 2026-05-01→2028-04-30
  (confirmed via signed lease).
- **1 real gap surfaced, deliberately NOT filled:** My Autonomous Transportation Co — only an
  unsigned LOI locatable ("this letter is not a contract... neither party intends [it] to
  represent the final agreement"), no executed lease found despite the workbook listing them as a
  fully active $8,212.50/mo tenant. Left Notion's (null) dates alone rather than write from an
  unconfirmed workbook claim.
- **NEW BUG CLASS — address mislabeling:** all 16 rows tagged `Property Address: FVC — Fairground
  Village Center` were never off-workbook tenants at all. "Fairground Village Center, LLC" is a
  landlord/holding entity (confirmed via its 2020 Form 1065 and the PSAs for 7658 Fishel + 401
  Sunburst), not a physical address — whoever entered these 16 rows put the entity name in the
  Property Address field. Real address, confirmed via Airmaster's own signed lease naming it
  directly: **29000 Information Ln — Easton MD**. Corrected all 16 rows' Property Address, then
  cross-checked against a live property-specific rent roll (`RentRoll 10.2025 -- 29000 Information
  Lane.xlsx`, 25 units) plus 2 individually-read primary documents (Airmaster's original lease for
  a tenant-turnover case; Medspeed's Third Addendum, May 2026, for a $4,935.42 rent value that
  matched nothing in this tenant's own history — corrected to $1,750, the addendum-confirmed
  current rate). 15 of 16 fully resolved (address + date); 1 (CURREN SOLUTIONS, INC.) left
  deliberately unresolved — the Oct 2025 roll shows its lease already expired 2025-12-31 with no
  more-current source located, too ambiguous to write without further checking.
- **NEW BUG CLASS — cross-property duplicates:** of an original 8-tenant "Red Branch" cluster, the
  live Red Branch rent roll (April 2026, 13/13 units occupied) contains NONE of their names — all
  13 current occupants were already reconciled in OI-003. Checked 2 tenant names directly against
  Red Branch's lease folder: zero matching lease documents found. Cross-referenced against the
  Information Lane roll instead: **3 of the 8 are exact-rent-match duplicates** of tenants already
  correctly resolved there — Bay Area Exteriors LLC (`32b6ecd8-9e59-8110-8d4e-d2796469eacf`,
  $3,700 = Info Lane Unit 502), Eastern Shore Karate & Fitness LLC
  (`32b6ecd8-9e59-8115-b8fa-f3c924846355`, $1,802.50 = Unit 306), Palmer's Plumbing LLC
  (`32b6ecd8-9e59-8175-ac37-c4485ea0910e`, $2,980.36 = combined Units 301+302, stale dates on the
  Red-Branch-tagged copy). All 3 retired (`Row Retired = __YES__`), verified post-write.
- **Remaining Red Branch 5 — resolved 2026-07-17 (later session): 4 of 5 confirmed real tenants at
  OTHER properties (wrong Property Address, not duplicates — no second correctly-filed row existed
  to retire against, unlike the first 3). All 4 corrected via `notion-update-page` and verified by
  fresh fetch:**
  - **Eastern Shore Entrepreneurship Center, INC.** (`32b6ecd8-9e59-81f0-bbee-ea6a25e770cd`):
    confirmed via executed lease (`Lease Unit 504-507 EASTERN SHORE ENTREPRENEURSHIP CENTER, INC.
    29000 Information Lane 01-24.docx`) — 29000 Information Lane LLC landlord, Suite 504-507,
    6,000 SF, term 7/1/2024-6/30/2029, exact match to SF/Lease Start/Lease Expiration. Corrected
    Property Address → `29000 Information Ln — Easton MD`, Suite/Unit → `504-507`. Monthly Rent
    ($7,750) left unchanged — corroborated by a second independent source (`Current Rent all
    properties 1.13.2026.xlsx`) even though it didn't map cleanly to the lease's own Base Rent
    schedule ($6,250-$6,900 across Years 1-5); not flagged further.
  - **PRO REPAIR LLC** (`32b6ecd8-9e59-8151-9044-f813bd32c4cd`): confirmed via executed lease
    (`Lease 1100 Rarig Ave Unit M & N PRO REPAIR LLC & Abdullah Mamun 02.24.docx`) — 1100 Rarig Ave,
    LLC landlord (Ohio LLC), Unit M & N, Columbus OH 43219, 3,600 SF, term 2/26/2024-4/30/2027,
    exact match to SF/Lease Start/Lease Expiration; contact Abdullah Mamun is a lease co-tenant.
    Corrected Property Address → `1100 Rarig Ave — Columbus OH`, Suite/Unit → `M & N`. Monthly Rent
    ($3,750) left unchanged — matches a second independent source exactly (`Current Rent all
    properties 1.13.2026.xlsx`) despite a ~1-year-stale reading against the lease's own escalation
    schedule; not acted on given two-source agreement.
  - **Bay-Care Heating & Air LLC** (`32b6ecd8-9e59-817b-8125-d86be72b9dad`): the row's own Notes
    field already flagged "HubSpot shows 2207 Northwood Suite B12, not Red Branch" — confirmed via
    04.2025 lease addendum (landlord 2900 Loch Raven LLC succeeded by 2203 Northwood LLC): rent
    $1,029/mo effective 7/1/2025, termination 6/30/2027 — exact match to Monthly Rent and Lease
    Expiration; Estoppel confirms 1,200 SF. Corrected Property Address →
    `2203-2207 Northwood — Columbus OH`, Suite/Unit → `B12`, Notes updated to resolved status.
  - **Baltimore Dialysis, LLC (Fresenius)** (`32b6ecd8-9e59-81ec-9ed5-ddf28682a9de`): confirmed via
    First Amendment to Lease (`1900 North Broadway, LLC` landlord; tenant `Baltimore County
    Dialysis, LLC d/b/a Fresenius Kidney Care`) — original lease 3/31/2016, 9,030 SF at 1900 North
    Broadway, Baltimore MD, extended term 9/1/2026-8/31/2031; SF and Lease Expiration exact match;
    Monthly Rent ($16,555) corroborated by `Current Rent all properties 1.13.2026.xlsx`. Corrected
    Property Address → `1900 N Broadway — Baltimore MD` (canonical select-option string).
  - **Chesapeake Communications LLC** (`32b6ecd8-9e59-8173-8d78-de14796381e0`) — **left unresolved,
    NOT written.** Exhaustive search found no primary lease/estoppel/addendum anywhere in
    SharePoint (7+ targeted queries incl. contact "David Hume" and the domain
    `chesapeakecommunications.com`), no match in the live Red Branch Leases folder (~150 files
    listed, none named Chesapeake Communications — only the unrelated, already-correctly-filed
    "Chesapeake Bay Movers / Two Men and a Truck"), and no entry in the company-wide
    `Current Rent all properties 1.13.2026.xlsx` roster (which does list every other Red Branch-5
    tenant + `Chesapeake Brands, LLC`, a different entity, at Information Lane). Per Invariant 7,
    left as-is rather than guessed; genuinely unresolved, needs a human check (possible former
    tenant outside current-only exports, or a fabricated/phantom row per the documented HubSpot
    ID-collision batch).
  Zettler (8), Northwood (7, distinct from the Bay-Care Northwood dedup above), Sunburst (3), and
  6 no-address-but-Active tenants (Eurosort, Upgraded Roofing, Childs Play Diesel Performance,
  Gator Roofing, I Dig Ditches, Scarlet Covering) — still not touched at all. **STALE as of the rest
  of this entry — corrected 2026-07-17 (same-day staleness check): all 4 clusters WERE subsequently
  worked this same session; see the later progress blocks below for each.**
**Progress 2026-07-17 (later same day): Sunburst cluster (3 tenants) checked, 3 writes made,
1 new bug variant found.**
- Queried Notion for all rows tagged `Property Address` containing "Sunburst" — 5 rows, not 3:
  2 "Seafire Properties LLC" stubs, 1 "THE BAY AREA CORPORATION" (real data), 1 already-archived
  "⛔ ARCHIVED 2026-07-12 — THE BAY AREA CORPORATION" duplicate (pre-flagged "safe to delete" in
  its own Notes, from an earlier pass — not one of the 3 targets but retired in passing), and 1
  "Ironclad Fitness, LLC".
- **NEW BUG VARIANT — landlord entity in Tenant Name field (not Property Address this time):**
  both "Seafire Properties LLC" rows (`32b6ecd8-9e59-8108-ae54-f9a05c6df597`,
  `32c6ecd8-9e59-818f-b2e3-c082d284bf9e`) are phantom tenants. Confirmed via 2 independent
  executed Tenant Estoppel Certificates + the Jan-2026 Third Amendment to Agreement of Lease
  (401 Sunburst) that "SEAFIRE PROPERTIES, LLC" is the **landlord** entity for 401 Sunburst
  (predecessor to Fairground Village Center, LLC) — not a tenant. Both rows carried no rent/date
  data. Retired (`Row Retired = __YES__`), verified post-write. Also retired the pre-flagged
  archived Bay Area Corp duplicate (`32c6ecd8-9e59-8117-a236-c1d659abf558`) since its data was
  cross-confirmed identical to the real row.
- **THE BAY AREA CORPORATION** (`32b6ecd8-9e59-817c-8311-dce0194cd4e8`) — confirmed CORRECT
  as-is: Monthly Rent $6,412.50, Lease Start 2019-12-23, Expiration 2033-03-31 all match the
  executed estoppel + Third Amendment exactly (5,130 SF, 401 Sunburst Highway, Cambridge MD
  21613). No write needed.
- **Ironclad Fitness, LLC** (`32b6ecd8-9e59-81c3-a2f0-f2d7036b09f0`) — another instance of the
  address-mislabeling bug class: tagged 401 Sunburst Hwy, but Monthly Rent ($3,244.50), SF
  (3,000), Lease Expiration (2027-08-31), and contact name (Danielle Dressel) are an exact match
  to Unit 103 in `RentRoll 10.2025 -- 29000 Information Lane.xlsx` (tenant listed there as
  "Danielle Olsen Dressel"). Corrected Property Address to "29000 Information Ln — Easton MD"
  and populated Suite/Unit "103"; financial/date fields left untouched (already correct).
- Sunburst cluster now fully resolved (3/3 checked, 0 unresolved).
**Progress 2026-07-17 (later same day): the 6 no-address-but-Active tenants checked, 5 writes made,
1 duplicate retired, 1 left open pending a schema decision.**
- Confirmed via SQL query (`Lease Status = Active AND Property Address IS NULL`) that all 6 named
  rows (Eurosort, Upgraded Roofing, Childs Play Diesel Performance, Gator Roofing, I Dig Ditches,
  Scarlet Covering) were still live, un-retired, no-address rows as described — distinct from, and
  not to be confused with, the ⛔-ARCHIVED-2026-07-12 fabricated HubSpot-collision phantom copies
  of the same names that also exist in the DB (left untouched, per Gabriel's 2026-07-12 ruling).
- **Childs Play Diesel Performance** (`32c6ecd8-9e59-81d1-8900-d1de717c08a7`): confirmed via
  executed lease (`Lease Suite C5-6 Ian Blake Childs DBA Childs Play Diesel Performance --
  2203-2207 Northwood 3.2026.docx`, March 2026) — exact match to HubSpot Address "2207 Northwood
  Suite C5+C6". Corrected Property Address → `2203-2207 Northwood — Columbus OH`, Suite/Unit →
  `C5+C6`.
- **Gator Roofing LLC** (`32c6ecd8-9e59-81e9-b064-c86b7bc0cc0f`): confirmed via executed lease
  (`2024 Zettler Road Lease-- RONY N ZELAYA GUTIERRES & GATOR ROOFING LLC 04-25.docx/.pdf`, April
  2025) — contact name exact match. Zettler Rd has only ONE Property Address select option
  (`2018 Zettler Rd — Columbus OH`) covering the whole street-number range (confirmed against TYM
  Wholesale LLC's already-correct row, unit 2006 at the same option) — mapped accordingly, Suite/
  Unit → `2024`. Consistent with the pre-existing alias in `reference_tenant_name_mappings.md`.
- **I Dig Ditches** (`32c6ecd8-9e59-81d8-942d-d455f1bc8ed0`): confirmed via current rent roll
  (`Rent Roll -- 1100 Rarig Ave 04-26-2024.xlsx` and `03-19-2024.xls`) listing "I Dig Ditches, 1100
  Rarig Ave #D" — exact match to existing Suite/Unit "Unit D". Corrected Property Address →
  `1100 Rarig Ave — Columbus OH`.
- **Upgraded Roofing** (`32c6ecd8-9e59-8118-9134-d8dc145988eb`): confirmed via executed lease
  (`412 Morrison Road Lease Upgraded Roofing & Richard Henry Parrish, III --02-24.docx`) + matching
  Estoppel (Banwick + Morrison Loan Symetra, suite 412). Morrison Rd has only ONE Property Address
  select option (`392 Morrison Rd — Columbus OH`) — same convention already used for Columbus
  Suburban Construction (units 386+388 at the same option, per that row's own Notes). Corrected
  Property Address → `392 Morrison Rd — Columbus OH`, Suite/Unit → `412`.
- **Scarlet Covering, Inc.** (`32c6ecd8-9e59-811f-9582-e72dc5caa023`) — **cross-property-duplicate
  bug class, not an address gap:** identical Monthly Rent ($10,790.41) and Suite/Unit (100) to the
  already-reconciled row `3336ecd8-9e59-812d-b123-e95be3f871ba` (`1900 N Broadway — Baltimore MD`,
  verified 2026-04-27 from Rent Roll 04.20.2026). This row's own HubSpot Address ("1900 North
  Broadway Unit 100") and primary lease documents (1900 North Broadway 2012 lease + Addendum #2,
  2022; `Rent Roll 12.17.2025 -- 1900 N Broadway.xlsx`) confirm same tenant/lease. Retired
  (`Row Retired = __YES__`) rather than given its own address, per the Red Branch/Sunburst
  duplicate-handling pattern.
- **Eurosort, INC., a Delaware Corporation** (`32c6ecd8-9e59-8102-8c1b-e60fdc83ac06`) — **confirmed
  but NOT written, blocked on a schema decision.** Executed lease (`Lease Eursort -- EG comments
  8-17-22.docx`, Eric Goldberg Family, LLC landlord, Aug 2022) plus the Notion Property Register
  page "55 New Plant Ct, Owings Mills MD" and the Portfolio Intelligence Dashboard ("Largest Tenant
  by ARR Eurosort, Inc. (55 New Plant Court) — $452,835/8.03%") confirm this is a real, distinct
  ORA property — just one with no existing `Property Address` select option in the Tenant DB
  (`notion-update-page` rejected the write: select properties are a closed enum; Notion's
  `notion-update-data-source` DDL tool could add the option but requires restating all 19 existing
  options to avoid dropping any — a schema change to a live production database not taken
  unilaterally). Needs Gabriel's go-ahead to add the `55 New Plant Court — Owings Mills MD` option
  (or a decision to fold it into an existing option), then a one-line `notion-update-page` write.
- Net: 4/6 fully resolved with a new Property Address; 1/6 resolved as a duplicate-retire; 1/6
  (Eurosort) confirmed but blocked on a schema-option decision, not a data gap.
**Progress 2026-07-17 (Northwood cluster, concurrent session): NEW BUG CLASS — property-wide
city/state mislabeling. 5 of the "Northwood (7)" rows checked and corrected; 2 unresolved; 1
anomaly flagged.**
- Note for whoever next touches this file: the live Notion query for "Northwood" returns far more
  rows (~80, mostly already-archived 2026-07-12 or exact-duplicate stale copies) than "7" —
  that count was a same-day running snapshot, not a recoverable exact list. Rebuilt from the
  active, non-duplicate rows instead.
- Confirmed via the Master Workbook (zero "Northwood" rows in `EXPORT_RentRoll` — genuinely
  off-workbook) and via SharePoint (multiple executed leases, a sale OM, rent rolls) that the
  property is real — "Northwood Business Center", 2203-2207 Northwood Drive, **Salisbury, MD
  21801**, landlord "2203 Northwood, LLC" — but every row (including this session's own
  Bay-Care Heating & Air and Childs Play Diesel Performance fixes above, and the ~35+ other active
  Northwood rows not yet touched **at the time this note was written — see the "Northwood bulk
  address fix — CLOSED" block below for the completion**) carries the WRONG select option
  `"2203-2207 Northwood — Columbus OH"`. Same bug class as the Fairground Village Center address
  mislabel, different manifestation (city/state wrong, not an entity name in the field).
- Added a new correct select option `"2203-2207 Northwood Dr — Salisbury MD"` via
  `notion-update-data-source` (ALTER COLUMN, all 19 pre-existing options + colors restated
  unchanged, re-fetched the schema first to get exact colors — an initial attempt with guessed
  colors was rejected). Did NOT rename the existing wrong option in place — that would touch every
  row using it at once without individual per-row confirmation, too broad a unilateral action.
- **5 rows confirmed via primary lease documents and corrected** (`notion-update-page`, each
  verified by a fresh `notion-fetch` immediately after):
  - Evans Gymnastics and Dance LLC `32b6ecd8-9e59-816c-9181-e15f117efb2e` — address corrected;
    Monthly Rent $700→$750 (addendum: step to $750 effective 2026-06-01, already in effect).
  - Andres Pacay Sr. `32b6ecd8-9e59-81dc-9df1-edff9cfdefd5` — address corrected only; a 2024
    estoppel's rent/date ($2,360, exp. 2025-06-30) is superseded and Notion's current values
    ($2,430.80 = $2,360×1.03; exp. 2026-03-31) are internally consistent with an escalation but
    not confirmed by a newer document — left as-is.
  - Patrick Betz `32b6ecd8-9e59-81dc-9230-c822f9aa6e73` — address corrected only; full lease
    confirmed Monthly Rent $999 and Lease Expiration 2027-10-31 exactly as already shown.
  - Itron `32c6ecd8-9e59-8172-981a-cdf58b1984a5` — address corrected; Lease Expiration null→
    2026-12-31 (Second Addendum); Monthly Rent $1,265 already correct.
  - Robert and Kesha Best `32c6ecd8-9e59-8196-938e-f75e36fb22ed` — address corrected; Monthly Rent
    $1,157→$2,058 and Lease Expiration null→2026-08-31 (addendum: "Rent shall stay the same
    ($2058.00/month)... Lease Termination will now be August 31, 2026" — prior $1,157 matched
    nothing in this tenant's history).
- **2 rows left unresolved** (document located but insufficient, or contradictory):
  - Harold Palmer `32c6ecd8-9e59-8183-b5e5-e497d53c7c12` — signed addendum exists but SharePoint
    extraction returned only its DocuSign completion-certificate page, not the rent/date terms.
  - Maryland Hospital Association `32c6ecd8-9e59-819a-aaa5-f393ef49a999` — the one addendum found
    names the tenant "MARYLAND HOSPITAL INC" (entity match unconfirmed), states rent $2,263.73 vs.
    Notion's $1,483.39, termination 2026-05-31 (already past today) — too many open threads
    without a more current document.
- **1 anomaly flagged — RESOLVED 2026-07-17 (Gabriel-confirmed):** "Restoration Church Trust"
  `32b6ecd8-9e59-81ed-b571-dfc871ab9f25` is not a Northwood tenant — it is a $2M loan counterparty
  (ORA/Eric Goldberg as lender, per the Master Workbook's own "Restoration Church Trust"
  loan-amortization tab and SharePoint's `5600 Sunnyside Ave` loan-document folder, being paid off
  per a July 2026 payoff statement). The Notion row's Monthly Rent ($14,135.38) and Lease
  Expiration (2027-02-20) exactly match this loan's Phase-1 payment and balloon maturity — a
  categorical data-entry error, not a correctable field. Gabriel confirmed: retire, not delete.
  Set `Row Retired = __YES__` via `notion-update-page`, Notes annotated with the full rationale,
  verified by fresh `notion-fetch` immediately after. Property Address/Monthly Rent/Lease
  Expiration left untouched (retirement excludes it from active queries; no need to also scrub the
  now-irrelevant tenant-shaped fields).
- Spawned a follow-up chip (`task_6719632a`) covering: the ~35 remaining Northwood rows still on
  the wrong address option, the 2 unresolved rows above, and the Restoration Church Trust anomaly.
**Progress 2026-07-17 (Zettler cluster, concurrent session): 8 rows checked, 7 corrected, 1
partially resolved; 8 archived duplicates retired.**
- Queried Notion for all `Property Address = "2018 Zettler Rd — Columbus OH"` rows (32 total,
  active + archived); excluded rows already reconciled elsewhere (exact Property+Unit workbook
  match — Schottenstein Roofing, TYM Wholesale, Virgin Landscape, Stone Crest Counters, Home
  Performance, Columbus Diamonds Elite Cheer, The Perez Company — all genuinely at Zettler, no
  action) to isolate the family-join-miss rows.
- **Same address-mislabeling bug class as FVC/Red-Branch/Northwood, found independently here** —
  6 rows each already carried an internal contradiction (a "verify correct property" Notes flag or
  a HubSpot Address field pointing elsewhere, never actioned) plus a same-named archived duplicate
  whose Notes said "DUPLICATE... Safe to delete" but whose `Row Retired` checkbox was never set.
  Corrected via `notion-update-page`, verified by fresh fetch:
  - **PEDRO'S FLOORING, LLC** (`32b6ecd8-9e59-8124-baff-db3530be845c`) → 1100 Rarig Ave Unit B;
    executed lease (`Lease 1100 Rarig Ave Unit B Pedro's Flooring LLC 10.24`) + HubSpot Address +
    exact rent/date match to Master Workbook.
  - **GT INDUSTRIAL SUPPLY, INC.** (`32b6ecd8-9e59-81dd-8b18-c4df6bc6f7a4`) → 1100 Rarig Ave Unit
    F & I + J; signed Lease Addendum (06.2025) rent schedule ($4,832.70 for 11/1/25-10/31/26) —
    **reverses this same item's earlier "fuzzy match, untrustworthy, not acted on" call** now that
    a signed addendum was located. Retired 2 archived duplicate copies (one had already correctly
    carried this data via an auto-sync, unused).
  - **Modular Component Systems, LLC** (`32b6ecd8-9e59-8196-8a47-c9bff2ba9d71`) → 29000 Information
    Ln Unit 402; executed Second Addendum (06.2025) + exact rent/date match.
  - **Buckeye Rock Tops** (`32b6ecd8-9e59-813b-967b-d21830674a43`) → 392 Morrison Rd Suite 398 (not
    Zettler Suite 113); **also the Escalation-Date-as-Lease-Expiration bug (OI-008's pattern,
    recurring)** — Lease Expiration corrected 2026-06-01→2027-05-31 via Rent Roll Banwick +
    Morrison 2.23.2026 (rent $1,854 already correct, no change).
  - **Hobart Services, A Division of ITW Food Equipment Group, LLC**
    (`32b6ecd8-9e59-8192-a085-fa93dc26665e`) → 2203-2207 Northwood Dr — Salisbury MD (this session's
    own address correction — see the concurrent Northwood-cluster finding above that the older
    "Columbus OH" option was itself wrong; this row was written once to the old option, then
    re-corrected to the new Salisbury MD option the same pass) Suite A7; rent corrected
    $1,183.47→$1,218.97 (one 3% escalation behind) per the 2024 HubSpot tenant list + Master
    Workbook's current rent; Lease Expiration null→2029-06-30.
  - **Reddish Fire Protection, LLC** (`32b6ecd8-9e59-81d5-a8b4-ecd2bc4c2c57`) → 2203-2207 Northwood
    Dr — Salisbury MD (same old-option→new-option correction as Hobart, same pass) Suite B14;
    executed Second Addendum (09.2025) + exact rent/date match.
  - **Atomic Auto Salon LLC** (`32b6ecd8-9e59-81f3-b3e3-d144c07785a6`) → 9050 Red Branch Rd Suite P
    (a distinct tenant from the already-reconciled Red Branch cluster, not a duplicate — no HubSpot
    Address flag existed on this row, confirmed instead via 4 independent exact matches: contact
    David Perry, SF 10,000, Lease Start 2021-10-01, Lease End 2026-11-30); rent corrected
    $1,113.94→$8,910.29 (stale/pre-escalation figure) per the current property Rent Roll
    (04.15.2026).
  - Retired 8 archived duplicate rows total (`Row Retired=__YES__`, verified): 2× GT Industrial
    Supply, plus one each for Pedro's Flooring, Reddish Fire Protection, Buckeye Rock Tops, Hobart
    Services, American Tower, Granite Tops & More.
- **Confirmed correct as-is, no write:** American Tower (`32b6ecd8-9e59-818e-89c0-eeb92fd6c45a`) —
  its own HubSpot Address field says "Zettler Cell Tower"; genuinely a ground/tower lease absent
  from `EXPORT_RentRoll` (family-join miss only, not an error).
- **Partially resolved:** Granite Tops & More (`32b6ecd8-9e59-81b0-90f7-fc8c610b609f`) — Suite
  corrected 112→2000-2002 (HubSpot Address + archived duplicate + the original signed 2023 lease
  all agree; Property Address itself was already correct). Monthly Rent ($16,713.65, unexplained
  by any source found) and Lease Expiration (2026-05-31, superseded) deliberately left unwritten —
  a 2026-05-28 lease addendum proposes $8,750/mo through 2029-05-31, but the copy on file shows
  blank/unexecuted signature blocks, so its terms aren't confirmable as controlling.
- **Left entirely unresolved, no write:** InSite Build, LLC (`32b6ecd8-9e59-810e-83d0-e2881e7d4391`)
  — the only primary document found (a Fourth Addendum dated 2026-07-09) shows the actual unit
  lease at Northwood terminated 12/31/2025 and was replaced by a $50/month digital-pylon
  signage-only license, wholly different from Notion's $2,225/mo Suite 304 record. A change in the
  nature of the relationship, not a field-level fix — needs Gabriel's judgment on whether the row
  should be corrected, converted to reflect the signage license, or archived.
- Zettler cluster now fully examined (8/8 checked): 7 corrected, 1 (Granite Tops) partially
  corrected with a flagged residual, 1 (InSite Build) left open pending a human decision.
**Gabriel decisions 2026-07-17 (6 items surfaced across all 5 clusters) — all executed same session:**
- **Eurosort, INC.** (`32c6ecd8-9e59-8102-8c1b-e60fdc83ac06`) — confirmed real (55 New Plant Court,
  Owings Mills MD), but that address wasn't one of the 19 existing `Property Address` select options.
  Gabriel: add it. Added via `notion-update-data-source` (`ALTER COLUMN ... SET SELECT(...)`,
  restating all 19 existing options + the Northwood-Salisbury option added earlier this session, so
  nothing was dropped — 21 options total now). Row written to the new option, verified.
- **InSite Build, LLC** (`32b6ecd8-9e59-810e-83d0-e2881e7d4391`) — Gabriel: update in place to the
  license terms. `Monthly Rent` 2225→50; `Notes` documents the space-lease termination and signage
  license, explicitly flags that exact license term dates weren't located and the Lease
  Start/Expiration/SF/Suite fields are left as the historical space-lease record, not current terms.
  Verified.
- **Restoration Church Trust** (`32b6ecd8-9e59-81ed-b571-dfc871ab9f25`) — not a tenant at all, a
  $2M loan counterparty (ORA is lender) whose loan payment/balloon maturity had been data-entered as
  rent/lease-expiration. Gabriel: remove from the Tenant DB. `Row Retired=__YES__`, `Notes` records
  full evidence (Master Workbook loan-amortization tab + SharePoint payoff statement). Verified.
- **Chesapeake Communications, LLC** (`32b6ecd8-9e59-8173-8d78-de14796381e0`) — zero trace in any
  primary document after exhaustive search. Gabriel: retire as likely bad data. `Row Retired=__YES__`.
  Verified.
- **Granite Tops & More** — Gabriel: leave unwritten, flag for follow-up (no action taken; matches
  what was already done).
- **Harold Palmer / Maryland Hospital Association** (Northwood, unresolved) — Gabriel: leave both
  open for now (no action taken; matches what was already done).
**Cluster tally:** 26 of 29 originally-targeted tenants resolved (corrected or confirmed-correct)
this pass, across Red Branch (4/5, 1 unresolved), Zettler (7/8 + 1 partial), Northwood (5/7 checked
individually — cluster turned out to be ~80 rows total, not 7), Sunburst (3/3), and the 6
no-address tenants (6/6, one required the Eurosort schema addition above).
**Northwood bulk address fix — CLOSED 2026-07-17 (same day, later).** `task_6719632a` (spawned to
cover the ~35 remaining wrong-address rows) ran on a Code surface with no Notion MCP access —
correctly declined to guess, found this tracker entry instead of duplicating scope, and only
executed the one decision within its reach: retiring Restoration Church Trust per Gabriel's
instruction (redundant with, and consistent with, the retirement already landed earlier the same
day — verified no corruption from the double write). The actual bulk fix required Notion's SQL
`query_data_sources` tool, which hit an `entitlement_required` quota wall (all of today's parallel
research agents had exhausted the workspace's free query allowance). Gabriel chose to wait; a
`ScheduleWakeup` retry fired ~1h later, the quota had reset, and the fix ran clean:
- Query returned 76 rows on the wrong `2203-2207 Northwood — Columbus OH` option, 42 of which
  (re-counted precisely via a `Tenant Name LIKE '%ARCHIVED%'` filter — the initial "~45" was a rough
  estimate) are pre-existing `⛔ ARCHIVED 2026-07-12 — ...` title-stub duplicates; each has a live,
  non-archived counterpart row that WAS address-corrected below. These stubs still carried
  `Row Retired=__NO__` despite the title prefix — the same title-archive/Row-Retired gap OI-004
  originally closed for *other* rows had never been swept across the *whole* DB.
- Corrected all 31 genuinely active rows' `Property Address` to
  `2203-2207 Northwood Dr — Salisbury MD` via `notion-update-page` (page IDs: `32b6ecd8-9e59-8129-
  b4af-ded1496b150a`, `-816f-99a8-e8a6ab5e8aa2`, `-817b-8125-d86be72b9dad`, `-819b-bb42-
  f8010a8b7a9b`, `-81b8-845a-da4525250070`, `-81db-bda5-f6a2e7f5abdf`, `-81fa-84e5-f96603742c66`;
  `32c6ecd8-9e59-810e-93c1-e8dbf00d50d8`, `-8126-b22b-cbf4a6a16415`, `-8129-9f36-dc1f8f3c2775`,
  `-8137-ab7e-d81b45ae9a52`, `-813b-8fbc-cae3816393d9`, `-813e-8069-ea5e592d0f0b`, `-8145-aea3-
  e4195d1e09fd`, `-8152-aee3-fe36e7a608b0`, `-8154-8af1-caa5eed0823c`, `-8169-af36-d84cd109c412`,
  `-8183-b5e5-e497d53c7c12` [Harold Palmer], `-8195-a0f9-c24a18e82c36`, `-8197-b41e-e7d264c21a53`,
  `-819a-aaa5-f393ef49a999` [Maryland Hospital Association], `-81ac-92e6-ec46a93b8a2c`, `-81b3-
  a4f8-d9bb181085ff`, `-81bb-aff5-cb70c4649b27`, `-81c3-a892-f3c18df594a5`, `-81ca-8bea-
  d5eda7a246d9`, `-81d0-a696-e38f5d5a8732`, `-81d1-8900-d1de717c08a7`, `-81d4-8d10-c06e5b966341`,
  `-81e0-8570-f3af5bbf977a`; `32f6ecd8-9e59-8107-b967-c787ce72bf1f`). Note: 2 of these (Bay-Care
  Heating & Air LLC, Childs Play Diesel Performance) had been written to the *old, wrong* Columbus-OH
  option earlier today by the Red-Branch and no-address cluster passes respectively — those ran
  before the address bug was discovered, so this closes that loop too. Address-only fix — did NOT
  touch rent/dates on Harold Palmer or Maryland Hospital Association (both still need primary
  documents before any content write, per Gabriel's explicit "leave both open" instruction).
- **Verified clean:** re-query for the wrong address + `Row Retired=__NO__` + not-title-archived
  returns zero rows; a count of rows on the correct Salisbury-MD option returns 38 (31 just fixed +
  5 from the original Northwood pass + 2 from the Zettler pass — reconciles exactly).
**Title-archived Row-Retired gap — CLOSED 2026-07-17 (same day, later, on Gabriel's explicit ask).**
Set `Row Retired=__YES__` on all 42 stubs identified above via `notion-update-page` (page IDs:
`32b6ecd8-9e59-8101-86c1-d7603cb3ad4e`, `-8102-8d47-fca88b0ef1a9`, `-8102-a1dd-ec7f2cd716c0`,
`-8106-b9ab-c557acc9ba54`, `-8107-a825-da21139decc4`, `-810e-b533-e8c63c877dda`, `-8118-8cac-
c4ee6c492f19`, `-8124-91ad-c559c307b741`, `-8127-9519-c7c56c851e54`, `-8129-8b51-f08158b01266`,
`-812d-a525-e68ca2b9d8a7`, `-812e-b11c-fa229372a117`, `-8139-95fc-f3e01902910b`, `-813d-a4f4-
c77d23a715fd`, `-813e-82f0-e19ef206e08a`, `-8143-a63e-f89b62260b35`, `-8145-bea9-e19c1fa29fd2`,
`-8149-bb15-df2bf604e6f8`, `-8162-83d3-f463ff14ee8b`, `-8164-b103-e19ce2f3c614`, `-817d-a331-
dd791d13fcec`, `-8187-ba83-f76a490497b6`, `-819a-9b10-c593fdab7a33`, `-819e-89b0-fbbad634f9d7`,
`-81a2-813f-d93ddba18828`, `-81aa-8a57-c393ebc283d1`, `-81ab-83a9-c3f1110d22ab`, `-81ae-9f80-
f81ddddc58cf`, `-81b4-9c48-f16f2b7e02c1`, `-81bf-aa43-d57f59bd3c48`, `-81c7-8fa6-f7c2b7af9b03`,
`-81d3-9608-e0a4ccb061f8`, `-81d5-9b3a-eda044b49a3f`, `-81da-9364-f57b7e7833e4`, `-81de-8194-
e33105ffe9e4`, `-81e2-9ea1-dc57b288caf3`, `-81ea-beb6-c3df9bc9575e`, `-81f6-9233-c8c0de65ba58`,
`-81fb-8307-f7496ba02281`, `-81ff-8e98-eba0c1e77ab3`; `32c6ecd8-9e59-81e9-a44e-f6615941b18a`,
`-81ea-bf89-eeca45958800`). Note: this closes the gap for the 42 Northwood-tagged stubs only, not
the whole Tenant DB — other properties' title-archived rows may carry the same gap, unverified.
Verified clean via a fresh `COUNT(*)` query (`Property Address` = the old option AND `Tenant Name
LIKE '%ARCHIVED%'` AND `Row Retired='__NO__'`) returning 0.
**Title-archived Row-Retired gap — swept DB-WIDE 2026-07-12, closed 2026-07-17 (Gabriel's explicit
ask, same day as the Northwood-scoped closure above).** Queried the whole Tenant Database (not
scoped to any one property) for `Tenant Name LIKE '%ARCHIVED%' AND Row Retired='__NO__'` — 73
additional rows found (the Northwood 42 above were already closed and correctly excluded from this
count), spanning 9620 State 350, Zettler, Red Branch, Morrison, FVC/Fairground Village Center, 1100
Rarig, 1900 N Broadway, 29000 Information Ln, and many with a null Property Address entirely. Set
`Row Retired=__YES__` on all 73 via `notion-update-page` (full page-ID list in
`C:\Users\Owner\AppData\Local\Temp\claude\...\scratchpad\dbwide_archived_gap.json` from the
authoring session, not reproduced here for length — each is independently re-derivable by re-running
the same query, which now correctly returns empty). One of the 73 is the archived duplicate stub of
Restoration Church Trust (`32c6ecd8-9e59-81a5-be70-c3902aa151c3`) — distinct page from the live row
already retired earlier, same treatment applies. **Verified DB-wide clean:** re-running
`Tenant Name LIKE '%ARCHIVED%' AND Row Retired='__NO__'` with no property filter returns 0 rows —
**115 total** stale archived rows (42 Northwood + 73 rest-of-DB) now correctly flagged across the
entire Tenant Database. This specific gap is now fully closed everywhere, not just Northwood.
**Harold Palmer — resolved 2026-07-17 (later, same day).** Gabriel asked to re-check the 93-row-universe
stragglers. Found the source `.docx` of the Suite A14 addendum (not just the DocuSign completion-certificate
page found previously) plus its own DocuSign audit trail: signed by Eric Goldberg 2025-03-26, "Agreement
completed." Terms: Termination 4/30/2027; Rent $1,157/mo effective 5/1/2025 (already matched Notion),
stepping to $1,166/mo effective 5/1/2026 (past-due, Notion was stale). Wrote via `notion-update-page`
(`32c6ecd8-9e59-8183-b5e5-e497d53c7c12`): `Monthly Rent` 1157→1166, `Lease Expiration` null→2027-04-30.
Verified via fresh fetch.
**Maryland Hospital Association — resolved 2026-07-17 (later, same day).** The draft Third Addendum found
earlier this session (unexecuted, entity-name only) turned out to be superseded — Gabriel supplied the
actual fully-executed copy directly (`Lease Suite B2-3 MHA Third Addendum Fully Executed 05.2026 --
2203-2207 Northwood.pdf`; standard PDF text extraction failed on broken font encoding, so pages were
rendered to images via `pypdfium2` and read visually). Confirmed executed via Adobe Sign audit trail:
signed by Gabriel Goldberg for Landlord, 2026-05-06, "Agreement completed." Terms match what Gabriel
stated directly: Termination extended to **6/30/2027** (not the 5/31/2027 read off the earlier draft —
the draft was not the final version); Rent **$2,332/mo effective 6/1/2026**. Wrote via `notion-update-page`
(`32c6ecd8-9e59-819a-aaa5-f393ef49a999`): `Monthly Rent` 1483.39→2332, `Lease Expiration` null→2027-06-30.
Verified via fresh fetch. **Tenant-rename question — decided 2026-07-17, closed.** This Third Addendum
also reassigns the Tenant under the Prime Lease from Maryland Hospital Association to "LogicQual Research
Institute, Inc." (an MHA affiliate per the tenant-termination-right clause), releasing MHA from all
obligations. Gabriel confirmed: keep `Tenant Name` as Maryland Hospital Association, no rename. Decision
recorded in the row's own `Notes`.
**Granite Tops rent/date — moot, resolved 2026-07-17 (later, same day).** The 5/28/2026 addendum
($8,750/mo, 11,160 SF, through 5/31/2029) was never executed and is now moot: Gabriel confirmed the
tenant is vacating end of month (2026-07-31). Wrote via `notion-update-page` (`32b6ecd8-9e59-81b0-90f7-
fc8c610b609f`): `Lease Status` → Notice Given, `Lease Expiration` 2026-05-31 (stale) → 2026-07-31 (vacate
date). `Monthly Rent` ($16,713.65, still unexplained by any source found) deliberately left as-is —
final figure is now a move-out reconciliation question, not a lease-terms question. Verified via fresh
fetch. Note: AR Balance shows $180.19 at 90+ days aged — not chased further, outside this item's scope.
**Progress 2026-07-26 (bounded batch, 12 tenants): the never-doc-verified remainder of the Northwood
bulk-address-fix population checked; 12/12 resolved (11 confirmed correct as-is, 1 corrected —
a NEW bug variant: cross-row contact-field contamination); 2 writes made, both verified by fresh fetch.**
- **Batch scope:** the 2026-07-17 Northwood bulk fix corrected `Property Address` only on 31 active
  rows — rent/dates/contacts on most had never been checked against any document. Queried the live
  DB (`Property Address LIKE '%Northwood%Salisbury%' AND Row Retired='__NO__'` → 31 rows), excluded
  the 9 already individually verified on 07-17 (Bay-Care, Childs Play, Evans, Harold Palmer, Hobart,
  Itron, MHA, Reddish, Robert & Kesha Best) and IWNS LLC (new 2026-07 row, outside the 93-row
  universe), and took 12 of the remaining 21: Online Auction, Adkins Towing, Anibal Morales,
  Peninsula Pressure Systems, William D. Smith, BEK General Contracting, BRITMAN CORPORATION,
  Sky Shield, Carlton L. Handy, Complete Cleaning, Louis Foxwell, Taron Tyree Walker.
- **Verification sources:** two independent rolls — `Current Rent all properties 1.13.2026.xlsx`
  (HubSpot-derived, read in full) and **`Rent Roll 7.20.2026.xlsx`** (egoldberg OneDrive root,
  Master-Workbook export, "As of July 20 2026 · 137 tenants · Active Scenario: Base" — 6 days old
  at check time) — plus primary documents where the rolls diverged.
- **NOTE FOR NEXT PASS — the notion_only premise has shifted:** Rent Roll 7.20.2026 (workbook
  lineage) now CONTAINS all 30 occupied 2207 Northwood units. The Master Workbook appears to have
  gained Northwood rows since the 07-17 "zero Northwood rows in EXPORT_RentRoll" finding — the
  93-row universe should be RE-DERIVED against the current workbook before the next batch.
- **9 confirmed correct, no write (exact match in BOTH rolls):** Adkins Towing (`32c6ecd8-9e59-8169-af36-d84cd109c412`,
  $835 / 1993-12-01 / exp 2024-09-01, genuinely Expired), Anibal Morales (`-813e-8069-ea5e592d0f0b`,
  $399 / exp 2024-09-01, Expired), Peninsula Pressure (`-8145-aea3-e4195d1e09fd`, $3,999 / exp
  2026-12-31 / 6,500 SF), BEK (`-81ca-8bea-d5eda7a246d9`), BRITMAN (`-8195-a0f9-c24a18e82c36`;
  executed-lease file also on record, 06.2025), Sky Shield (`-81bb-aff5-cb70c4649b27`; 09.2025 lease
  on record), Taron Walker (`-8137-ab7e-d81b45ae9a52`), Complete Cleaning (`-81c3-a892-f3c18df594a5`,
  $1,165.96 = Jan's $1,132 x1.03, escalation 2026-07-01 passed — 7.20 roll confirms exactly), Louis
  Foxwell (`-81ac-92e6-ec46a93b8a2c`, $1,854 = $1,800 x1.03, same pattern, 7.20 roll confirms).
- **2 confirmed correct via primary document (Jan roll was stale, no write needed):**
  - **Carlton L. Handy** (`32f6ecd8-9e59-8107-b967-c787ce72bf1f`): Second Addendum (`Lease Suite A4
    Carlton Handy Addendum #2 -- 2203-2207 Northwood 04.2025.docx`) states termination 2027-02-28,
    rent $1,166 effective 2026-06-01 — exact match to Notion and the 7.20 roll (docx copy has blank
    signature blocks, but terms are live in the workbook roll).
  - **William D. Smith** (`32c6ecd8-9e59-813b-8fbc-cae3816393d9`): Addendum (`Lease Suite A11-12 + C3
    William Smith Addendum`) confirms A11-12 extended to 2031-04-30, $1,925 + $725 (C3) = $2,650/mo
    effective 2026-05-01, 3% from 2027-05-01 — exact match to Notion/7.20 roll; Jan roll ($2,568.40 /
    exp 2026-04-30 / 2,400 SF) was pre-addendum. Notes annotated (verified by fresh fetch) with the
    nuance that **Unit C3 is month-to-month** — the 2031 expiration covers A11-12 only. Data fields
    untouched.
- **1 corrected — NEW BUG VARIANT, cross-row contact-field contamination:** **Online Auction**
  (`32c6ecd8-9e59-8197-b41e-e7d264c21a53`, Suite B5). Lease fields ($999 / 2025-11-01 / 2027-10-31)
  exact-match both rolls AND the primary lease (`Lease Suite B5 Patrick Andre Betz -- 2203-2207
  Northwood 10.2025(2).docx`, signed date 10/9/2025, term 11/1/2025-10/31/2027, $11,988/yr) — but the
  row's Primary Contact / Contact Email / Contact Phone / HubSpot Address / HubSpot Contact all
  belonged to **Styled + Staged Interiors** (Lauren Meikle, Morrison 420 — a different tenant with
  its own correct row `32b6ecd8-9e59-817f-afce-dc12f510cc62`). Corrected to Patrick Betz
  (schoolbetz@gmail.com, +14436141854, HubSpot contact 162494267501, HubSpot Address "2207 Northwood
  Suite B5") on two agreeing independent sources: the Jan-2026 HubSpot-derived export and the retired
  duplicate row `Patrick Betz` (`32b6ecd8-9e59-81dc-9230-c822f9aa6e73`, retired 2026-07-21, which
  carried the same email/phone + the real Betz HubSpot record). Verified by fresh fetch. (That
  duplicate's 07-21 retirement also resolves what would otherwise be a same-property duplicate pair.)
- **FLAG, not actioned — A3/A4 turnover in progress:** draft (unexecuted, blank-dated) leases created
  7/20-7/22/2026 in the Northwood Leases folder show Sky Shield (Lagana) moving A3→A4 and Grails TCG,
  LLC taking A3 — implying a Carlton Handy departure ahead of his 2027-02-28 term. Notion's Sky Shield
  (A3, exp 2026-09-30) and Carlton Handy (A4, exp 2027-02-28) rows reflect the currently-executed
  state and were left as-is; re-check once those leases execute.
- **Incidental (not claimed as resolved):** the other 9 live never-verified Northwood rows (Austin
  Walter Ventures, Cosmic Spice, DDR Enterprise, Delmarva Business Solutions, Delmarva Riders,
  Hermiston, STOIC FARMS, Terrone White, Tony Kevin Davis) were roll-diffed in passing — all 9 agree
  with the 7.20.2026 roll (4 reflect 2026 renewals/escalations vs the stale Jan roll: Cosmic Spice
  $1,215/2028-06-30, DDR $1,183/2027-04-30, Delmarva Business 2029-06-30, Terrone White
  $1,050/2027-03-31). Easy wins for the next batch, but not individually doc-confirmed here.
**Real scope still remaining:** Chesapeake Communications (retired rather than traced, unchanged);
CURREN SOLUTIONS (Information Lane, still unresolved from 07-17); My Autonomous Transportation Co
(no executed lease located, gap unfilled); the 9 roll-diffed-only Northwood rows above; and whatever
the re-derived notion_only universe (see the 07-26 note — the workbook now carries Northwood) still
contains outside the worked clusters. This item stays OPEN, not closed.
**Auto-check:** none (not a fleet-registry item).

### OI-022
**Status:** OPEN — submitted, awaiting GitHub Support action (ticket #4584520, reopened 2026-07-20 with corrected SHA)
**Opened:** 2026-07-19
**Source:** OI-015 investigation (2026-07-19)
**Description:** the original (pre-rewrite) blob containing real E. Fulton `CONFIDENTIAL_TERMS` values
is still directly retrievable via GitHub's Git Data API (`gh api repos/ZeOoba/ora-pm/git/blobs/<sha>`),
even though it's unreachable from any current branch/tag and does not appear in any clone or the repo's
normal browsable history. Root cause: it's kept alive by `refs/pull/2/head`, a GitHub-internal ref for
the (closed, merged) PR #2 that originally carried the sensitive commit — these refs cannot be deleted
by the repo owner via git push, the REST/GraphQL API, or repo settings; there is no self-service
mechanism. The only documented remediation is a GitHub Support request asking them to purge the
cached/orphaned objects tied to this PR. Repo confirmed private with 0 forks (via API), so a
support-side purge should fully resolve the exposure.
**Not a live credential** (E. Fulton declassified 2026-07-09) — low urgency, but a real residual
exposure path (anyone who obtains the exact blob SHA, e.g. from an old CI log, webhook payload, or
browser cache, can retrieve the real terms via the API regardless of the rewrite on `main`).
**SUBMITTED 2026-07-19.** Gabriel authorized submission; sent via his own authenticated GitHub
session (Claude in Chrome) since this requires account login, not an API. **GitHub Support ticket
#4584520, status: open**, category Repositories → Repository features → Branches (closest available
fit; no dedicated "sensitive data removal" category exists in the structured form — full detail
carried in the ticket body). GitHub's own AI triage on the request confirmed the diagnosis matches
their documented "Removing sensitive data from a repository" process exactly (PR-ref dereference +
server-side GC).
**CORRECTION 2026-07-20 — original ticket cited the wrong SHA.** GitHub Support replied
(2026-07-20) that their tooling found the cited commit `c4c69a8` still referenced on `main`,
`chore/gitattributes-normalize-eol`, `recovery/2026-07-05-object-db-loss`, and PRs #5/#6 — which
read as a new exposure. Re-verified before acting (fresh clone + `gh api .../contents/.env.example`,
independently matching): `c4c69a8` has **only ever held placeholder text**; it's a clean squash-merge
of PR #2 and is a legitimate ancestor of `main` (that's why it shows up everywhere — normal ancestry,
not exposure). The real sensitive commit is a different SHA, **`6aed9a7`** (the pre-squash head of
PR #2, found via `git log --find-object=39b02f4585...` against `refs/pull/2/head`), which is *not*
reachable from `main`, any branch, or PR #5/#6 — confirmed via `git merge-base --is-ancestor`. The
`c4c69a8` misattribution originated in fix-commit `866480f`'s own message (2026-07-16) and propagated
into the original support-ticket text.
**Net effect: no branch/PR cleanup needed anywhere — OI-015's "reachable history is genuinely clean"
conclusion stands, confirmed a second time.** Replied to ticket #4584520 (2026-07-20, Gabriel
authorized) correcting the SHA to `6aed9a7`, confirming `main`/branches/#5/#6 are unaffected, and
asking GitHub to purge `6aed9a7` / blob `39b02f4585cc6357876423d04d5c3fcee65793b0` via the
strip-internal-references option (preserves PR #2 comment history). Ticket reopened to **status:
open**, 3 comments. Awaiting GitHub's action on the corrected SHA.
**SCOPE CORRECTION 2026-07-31 (ora-appsec-sweep, ora-pm @ `a226f2b`) — the blob is reachable from
THREE PR refs, not one.** The weekly sweep's `security-auditor` dispatch re-derived this finding
independently and, scanning per-ref after fetching `+refs/pull/*/head` (11 refs), found blob
`39b02f4585cc6357876423d04d5c3fcee65793b0` reachable from **`refs/pull/2/head`, `refs/pull/3/head`,
AND `refs/pull/4/head`** — this row and ticket #4584520 both cite only PR #2. Introducing commit
confirmed as `6aed9a7` ("feat(intake): Phase 2a lease intake…", 2026-06-06), carried forward by
`926f3315`. Branch-reachability re-confirmed clean a third time (local `log -p --all` and a fresh
bare clone's `refs/heads/*` both show only the placeholder value), so OI-015's conclusion still
stands. **Action for Gabriel:** the pending Support request should enumerate PR refs 2, 3 and 4 —
purging only #2 would leave the blob live. Also worth confirming while the ticket is open: the terms
`3520`, `sij`, `columbus stamping`, `nutis` in that blob have NOT been verified as declassified
(only the Fulton terms have, 2026-07-09) — check them against `confidential-terms.json` before
assuming the exposure is low-urgency across the whole string.
**Auto-check:** none.

### OI-024
**Status:** OPEN (logged, deliberately not fixed)
**Opened:** 2026-07-24
**Source:** `hooks/shared-checkout-guard.py`; found while realigning its attribution tests (commit b599432,
see [feedback_shared_checkout_guard_session_attribution_unreliable.md](feedback_shared_checkout_guard_session_attribution_unreliable.md))
**Description:** `_attribute_wip()` resolves the provenance directory from `SHARED_CHECKOUT_SESSIONS_DIR`
(falling back to a hardcoded `hooks/sessions`) rather than importing `commit_provenance.sessions_dir()`,
which resolves `COMMIT_PROVENANCE_SESSIONS_DIR`. `hooks/lib/commit_provenance.py`'s own docstring states
the recorder and every reader MUST agree on the storage location "or every comparison silently misses" —
this third consumer agrees only by coincidence of defaults.
**Why inert today:** neither env var is set anywhere in `settings.json`; both resolve to
`C:/Users/Owner/.claude/hooks/sessions`, and 35 live `touched-files.txt` confirm the recorder writes there.
The naming branch is verified working in production.
**Failure mode if it ever bites:** setting `COMMIT_PROVENANCE_SESSIONS_DIR` alone (or the reverse) points
the guard at an empty directory. It degrades honestly — always UNATTRIBUTED, never a *wrong* name — but
permanently and silently, with no signal that attribution has stopped working.
**Fix if taken up:** import `sessions_dir` from `commit_provenance` and use it for the provenance read
only, keeping `SHARED_CHECKOUT_SESSIONS_DIR` for the warn-marker (two different concerns currently sharing
one variable). Note the tests rely on the current coupling to stay self-contained, so they'd need the
provenance var set too. Being security-gate code, this needs the mandatory adversarial REFUTE pass.
**Decision:** Gabriel 2026-07-24 — log, don't fix. Fails open, unreachable in the current configuration,
and not worth a guard edit inside a test-only change.
**Auto-check:** none.

### OI-021
**Status:** OPEN — Restoration Church Trust lender-outreach decision remains; both HubSpot sub-item and the renewal-pipeline batch pass are CLOSED
**Opened:** 2026-07-19
**Source:** [event_log.md](event_log.md#2026-07-19)
**Restoration Church Trust lender outreach (still open):** draft outreach letter prepared 2026-07-25
(confirms repayment/extension intent ahead of the 2027-02-20 balloon, closing the missed June-2026
Covenant Watch checkpoint) — send blocked on a real recipient contact. Checked Notion (Loan Portfolio
Tracker, Critical Deadlines Tracker), the one associated HubSpot deal, and Outlook mail history: no
borrower contact name or email exists anywhere in the system, only internal loan-tracking data. Needs
Gabriel to supply the actual contact before send (not guessed, per Invariant 7).
**HubSpot mis-entered deal — CLOSED 2026-07-25 (Gabriel's explicit go-ahead).** "Lease Renewal —
Restoration Church Trust" ($16,714, was `appointmentscheduled`) confirmed as the same
mis-entered-loan-counterparty pattern as OI-009 (a loan, not a lease, entered as a tenant renewal
deal). Retired via `manage_crm_objects`: `dealstage` → `closedlost`, `dealname` prefixed
`RETIRED (data-entry error, see open-items-tracker.md OI-021) —`. Verified post-write via
`get_crm_objects`.
**Renewal-pipeline batch pass — CLOSED 2026-07-25.** A `/debug` pass on Command Center's lease-alert
bug (separate incident, see [[project_master_workbook_no_single_writer_2026-07-24]]) surfaced this
item; chased it down the same session. Before touching anything, found the monthly
`ora-tenant-hubspot-reconciliation` sweep (2026-07-22, Notion "HubSpot-Tenant Reconciliation — July
2026") had already evidence-checked all 50 deals and narrowed the real open set to 8 items (down from
"49 stuck") — re-doing that work by hand was avoided. Chased the 8 via primary documents
(SharePoint leases/addenda, Adobe Sign audit trails, Gabriel's direct confirmation for one) and wrote
7 of the 8 to HubSpot (`closedwon`/`closedlost` + corrected `closedate`), each independently verified
post-write via `get_crm_objects`:
- **William D. Smith** → `closedwon` 2031-04-30 (Adobe Sign fully executed 2026-04-20, both parties).
- **State of MO, Dept. of Agriculture** → `closedwon` 2026-12-31 (official state renewal letter,
  2026-07-10, confirms both the date and — via its own return address — that the CHURN
  geo-mislabel flagged by the 07-22 reconciliation had already self-corrected; verified live, no write
  needed).
- **Cosmic Spice & Specialty Foods** → `closedwon` 2028-06-30 (Third Addendum, terms match live
  records exactly).
- **MLC Academy Maryland** → `closedwon` 2029-09-30 (Sixth Addendum, Adobe Sign fully executed
  2026-04-09 — NOT the 2031-09-30 figure from an unsigned draft found earlier the same session; that
  draft is Kareem Syed's still-pending Cricket DC LLC amendment request, 07-17, currently stalled on
  Gabriel's own diligence ask re: the entity's Inactive SDAT status).
- **FIRST STUDENT** → `closedlost` (turnover, confirmed by Gabriel directly: replaced by My Autonomous
  Transportation Co — matches the DSOR canonical page's own "single-tenant turnover" note; MATCo's own
  lease remains a separate, already-tracked gap under OI-009, unsigned LOI only).
- **Velcani Construction** → `closedlost` (turnover, replaced by Richwood Equipment Co LLC 2026-05-01,
  confirmed via 3 independent Notion sources).
- **Consult and Management** → `closedlost` (defaulted on rent, vacated end of March 2026, escalated
  to collections).
The 8th item, MLC's tenant-identity/term question, resolved to the same MLC row above once the
executed-vs-draft distinction was sorted — no separate action needed.
The other ~37 deals still sitting in `appointmentscheduled` are NOT a data problem — their embedded
dates match current lease-ends exactly, they're just legitimately not-yet-due (furthest out to 2027)
with no automated stage-advancement. That's a policy/tooling gap (when should a deal leave
`appointmentscheduled`?), not a data item — not fixed here, would need Gabriel's terms first.
**Auto-check:** none.

### OI-019
**Status:** OPEN
**Opened:** 2026-07-19
**Source:** [event_log.md](event_log.md#2026-07-19)
**Description:** Gabriel must add `HUBSPOT_TOKEN` (Private App, `crm.objects.deals.read`) to `oxford-command-center/.env` — PR #221 ready, blocked only on the credential; then re-verify 2146 Enterprise Pkwy lands in acq_candidates.
*(Section added 2026-07-29 during tracker ID-integrity reconciliation — the row predated the section requirement; row is authoritative for detail.)*

### OI-026
**Status:** OPEN
**Opened:** 2026-07-26
**Source:** `oxford-command-center` `gov-ltv-hardening` worktree, 18-round adversarial-refute session
**Description:** debt-snapshot.ts degraded-marker check is tick-partition order-dependent (same facts, opposite governor verdict by snapshot-write partition) — Gabriel ruling 2026-07-26: ship as-is, document only, no fix yet.
*(Section added 2026-07-29 during tracker ID-integrity reconciliation.)*

### OI-027
**Status:** OPEN
**Opened:** 2026-07-26
**Source:** PR [ZeOoba/oxford-command-center#238](https://github.com/ZeOoba/oxford-command-center/pull/238) (OI-017 vitest-4 REFUTE pass)
**Description:** No guard against a future test regressing into the OI-017 class (`vi.mock()` of a Node builtin silently no-ops under jsdom) — recommended ESLint rule / `@vitest-environment node` requirement not yet built.
*(Section added 2026-07-29 during tracker ID-integrity reconciliation.)*

### OI-033
**Status:** OPEN
**Opened:** 2026-07-28
**Source:** Cowork-surface follow-up to the Code-surface usage-limit audit, 2026-07-28
**Description:** LAMS/Cowork scheduled task `ora-tenant-contact-gap-sweep` (weekly Monday) carries
no `[MODEL: ...]` tag at all in its description — the sole untagged task in an otherwise
27/28-tagged LAMS fleet (re-verified 2026-07-28, all 27 tagged tasks still `claude-sonnet-5`,
including 5 set after the ~2026-07-25 Opus 5 rollout — LAMS shows no model drift, unlike CC/MCP).
**Candidate fix (not built):** tag it `[MODEL: claude-sonnet-5 | set 2026-07-28]` via
`update_scheduled_task` from a Cowork-surface session (LAMS registry writes need the matching MCP,
not reachable from Code) per [[reference_scheduled_task_model_standard]]'s tagging convention.
**Auto-check:** none.

### OI-041
**Status:** OPEN
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

### OI-042
**Status:** OPEN
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

### OI-048
**Status:** OPEN
**Opened:** 2026-07-31
**Source:** ora-appsec-sweep 2026-07-31 (ora-pm @ `a226f2b`, security-auditor dispatch)
**Severity:** MEDIUM (missing defense-in-depth + an unrun verification)
**Description:** (a) `server/db/client.ts:6-13` constructs a client with
`SUPABASE_SERVICE_ROLE_KEY`, bypassing RLS; the policies at `0004_views_and_rls.sql:101-189` therefore
constrain only direct anon-key access from the browser. (b) `supabase/migrations/0008_storage_rls.sql`
states in its header that the policies were *“applied 2026-06-05 via Node.js db script”* — a record of
an out-of-band action, not a migration the tooling can prove was applied.
**UNRUN CHECK, NOT A PASS:** whether the storage and table RLS policies are actually live in the
production project could not be determined from the repo, and this sweep does not probe live services.
If absent or drifted, `insurance-certs` and `lease-documents` — private buckets holding COIs and
executed leases — would be readable across tenants by any authenticated portal user.
**Candidate fix (NOT applied):** query the live project (`select policyname, cmd, qual from pg_policies
where schemaname in ('storage','public')`) and reconcile against 0004/0008; add a CI or scheduled
assertion so drift is detected rather than assumed away. For read paths, construct a per-request client
with the tenant's JWT so RLS is genuinely in force; reserve the service-role client for admin/cron.
**Auto-check:** none.

### OI-049
**Status:** OPEN
**Opened:** 2026-07-31
**Source:** ora-appsec-sweep 2026-07-31 (oxford-command-center @ `3692385`, security-auditor dispatch)
**Severity:** MEDIUM (governor-adjacent financial config, Invariant 4)
**Suppression note:** suppression S-002 covers the *existence* of the ratified ruleset and explicitly
does NOT cover a change carrying a stale ratification stamp — “that is the drift S-002 exists to
protect against, not permit.” This item is the carve-out firing as designed, not a re-flag.
**Description:** no mechanical gate references either config file. For a 2-day window on `main`
(`a83ce684` -> `d28d8bfb`) the edge function and server served scoring behaviour attributed to a
v1.0.0 stamp it no longer matched. An agent or human can change acquisition gate bounds/floors/weights
in a normal PR with no hook challenge, no refute-trailer requirement, and no version/ratification
consistency check.
**Evidence:** `git diff a83ce684^ a83ce684 -- config/acquisition-ruleset.v1.json` shows floor changes
with an unchanged version/stamp header, merged to `origin/main`. At pinned SHA `3692385` the file
is blob-identical (`bde04ba9`) to the post-ceremony ratified state — consistent, no active drift.
**Candidate fix (NOT applied):** add `config/acquisition-ruleset*.json` and `config/replacement-cost*.json`
to `architect-owned.json` globs and to the refute-required path set; add a `governance-check.ts` rule
failing when the ruleset's content (excluding the header block) differs from the archived copy for its
`rulesetVersion`, or when a diff touches the file without changing `rulesetVersion` + `ratifiedDate`. A
content-hash field in the header (mirroring migration 024's pattern) makes this a one-line comparison.
**Note:** if this fix adds `config/**` to the architect-owned globs, that gate inherits the documented
silent-degradation path in `file-guard.mjs:112-114` (a corrupt `architect-owned.json` degrades the
check to a no-op) — accept that knowingly or emit a visible warning.
**Auto-check:** none.

### OI-050
**Status:** OPEN
**Opened:** 2026-07-31
**Source:** ora-appsec-sweep 2026-07-31 (oxford-command-center @ `3692385`, security-auditor dispatch)
**Severity:** MEDIUM (rated below HIGH only because it requires the server running AND the victim
visiting attacker-controlled content)
**Description:** `server/index.ts:531`; `server/cors-policy.ts`. Hono's `cors()` never gates a
same-origin request, and after a DNS rebind the attacker's origin *is* the request origin, so the
localhost-only CORS policy is bypassed entirely rather than violated.
**Impact:** `/api/snapshot` is the single highest-value data set in the fleet. Both read and write are
reachable.
**Candidate fix (NOT applied):** a Host-header allowlist as the FIRST middleware, mirroring the
existing CORS pure-function pattern so it is equally unit-testable — `/^(localhost|127\.0\.0\.1)(:\d+)?$/`
tested against `c.req.header('host')`, 403 otherwise, registered before `app.use('/api/*', cors(...))`.
Add a regression test alongside `tests/unit/server-cors.test.ts`.
**Auto-check:** none.

### OI-051
**Status:** OPEN
**Opened:** 2026-07-31
**Source:** ora-appsec-sweep 2026-07-31 (oxford-command-center @ `3692385`, security-auditor dispatch)
**Severity:** MEDIUM (confidential data egress window, no automatic remediation)
**Suppression note:** S-001 covers deal terms in this repo's *source and git history* and explicitly
does NOT cover deal terms in a public or externally-served artifact. This finding is the externally
served path, so it is reportable; noted here as adjacent to S-001 to prevent a future re-litigation.
**Description:** `scripts/deploy-mirror.ps1:112`, `:120`, `:137-167`. The ordering is inherently
publish-then-check, and the failure path raises without unpublishing.
**Impact:** the full confidential deal book (terms, counterparties, tasks) publicly readable at a
stable, discoverable URL for at least the deploy window, with no automatic remediation.
**Candidate fix (NOT applied):** (1) add a PRE-deploy gate probe and abort without publishing on any
non-302, keeping the post-deploy probe as a second check; (2) on a post-deploy `GATE CHECK FAILED`,
automatically redeploy the redacted bake (`MIRROR_INCLUDE_CONFIDENTIAL` unset) as rollback before
re-raising; (3) probe every Access destination — make it `[string[]]$VerifyUrls` including
`https://brain.oxfordra.net/` and require all to 302; (4) consider asserting the JWT hostname, not
just the redirect host.
**Related unrun check:** live Access enforcement on both hostnames was NOT verified (report-only, no
live probing). The only evidence is [brain-oxfordra-access-finding.md](brain-oxfordra-access-finding.md),
a 2026-06-15 record. Do not carry “gated” forward as verified-today.
**Auto-check:** none.

### OI-053
**Status:** OPEN
**Opened:** 2026-07-30
**Source:** Credential-exposure sweep, 2026-07-30 (`event_log.md` 2026-07-30)
**Description:** `COMPOSIO_API_KEY` sits in plaintext at `Claude_Workspace/01_Workspace/oxford-agent/config.py:3`, with the same key duplicated at `01_Workspace/_archive/legacy-templates-2026-03/Claude Agents SDK - Getting Started.md:90`. Both paths are inside the **OneDrive-synced** tree, so the value has been replicating to Microsoft's cloud and to every device on this account. Composio was removed as a connector 2026-06-11, so the key is very likely dead — but "likely dead" is not "revoked."
**Action (Gabriel):** revoke at Composio if that account still exists. Not automatable — credential revocation is outside Code's permitted actions.
**2026-08-03 — VALUE REDACTED (exposure vector closed; revocation still open):** Gabriel re-requested revocation; that remains barred, so the actionable half was done instead. The `ak_` literal was removed from BOTH files — `oxford-agent/config.py` (1) and `_archive/legacy-templates-2026-03/Claude Agents SDK - Getting Started.md` (2, incl. an `api_key=` assignment) — replaced with `[REDACTED-2026-08-03-OI053]`. Originals backed up byte-intact to `_preredaction_2026-08-03/` beside each file; `config.py` re-verified as compiling. `authorize.py` and `oxford_agent.py` scanned clean (their `api_key=` lines are parameter passing, not literals). The key therefore no longer replicates to the cloud via OneDrive, but **it is not revoked** — if the Composio account is live, the key still works for whoever already has it. Item stays OPEN on the revocation.
**Auto-check:** none.

### OI-052
**Status:** OPEN
**Opened:** 2026-07-31
**Source:** ora-appsec-sweep 2026-07-31 (dispatch integrity gate, first live test)
**Severity:** MEDIUM (governance mechanism — the model floor is not enforced for a full run)
**Description:** the 2026-07-24 Option C ruling moved the Fable floor from this task's (inert)
frontmatter into the Agent dispatch, on the reasoning that “the dispatch pin IS honored.” The first
live exercise of that path shows it is honored *at spawn* but not *for the duration*.
**Evidence (2026-07-31, this sweep's own transcripts):**
`~/.claude/projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/0ab34204-58c9-4742-bed5-706c5d028422/subagents/`
- `agent-a7cb98f7a98d0daed` (ora-pm): meta `{"model":"fable"}`; 62 assistant msgs `claude-fable-5`,
  then a `fallback` content block at line 109, then 68 msgs `claude-opus-5`.
- `agent-a43623bcd1c477c5d` (occ): meta `{"model":"fable"}`; 107 msgs `claude-fable-5`, `fallback` at
  line 163, then 3 msgs `claude-opus-5`.
**What this does and does not mean.** The three DISPATCH INTEGRITY GATE assertions all PASS (the call
returned a real subagent result; the findings came from the subagent, not an inline substitute;
`model:'fable'` was passed explicitly). The gate is not defective for what it asserts — it simply
cannot see a mid-run fallback. And the fallback target is the session's own top-tier model, so this is
not the Sonnet-downgrade the doctrine warns about.
**Open question for Gabriel:** does “never below Fable” treat a mid-run fallback to Opus-5 as
compliant? If yes, this item closes as documentation. If no, the gate needs a fourth assertion —
post-hoc grep of the subagent transcript for `"type":"fallback"` / any non-Fable `model` value, which
is cheap and mechanical (the exact commands used this run are reproducible from the Evidence block).
**Do NOT “fix” this by deleting the frontmatter pin or flipping anything to Sonnet** (standing
instruction in the task file).
**RECONFIRMED 2026-08-12 (this sweep's own transcripts, session `f74b697f`):** both dispatches showed
the identical mid-run fallback. `subagents/agent-ad17a9f6885e86540.jsonl` (ora-pm): meta
`{"model":"fable"}`, 87 assistant msgs `claude-fable-5` then a `fallback` block then 16 msgs
`claude-opus-4-8` — the last 12 messages, which include the final findings report, were opus-4-8.
`agent-ae1c1f0bed70e7e88.jsonl` (occ): 48 msgs `claude-fable-5`, `fallback`, then 34 msgs
`claude-opus-4-8` (final report likewise opus-4-8). All three DISPATCH INTEGRITY GATE assertions still
PASS; the gate remains blind to the mid-run fallback. **New datum:** this time the fallback target was
`claude-opus-4-8`, not the `claude-opus-5` seen on 2026-07-31 — i.e. the fallback lands on whatever the
orchestrating session's server-pinned model is (opus-4-8 here), which is exactly the below-Fable tier
Option C was meant to avoid the security judgment running on. That strengthens the "no" case on the open
question: a non-trivial share of the actual findings this run were produced at opus-4-8, not Fable.
**FIX MERGED 2026-08-12 (ora-claude-config squash `35cbaba`) — Gabriel-directed:** the gate's fourth (post-hoc)
assertion now exists — `maintenance/check-dispatch-model-floor.py` reads the subagent transcripts after
the run and exits 1 on any below-floor model / fallback block, 2 on verified-null (missing/unreadable/
unparseable — never a silent PASS), 0 only if every subagent held Fable end-to-end. Wired into the
ora-appsec-sweep SKILL.md (v1.5); a failure records a `MODEL-FLOOR BREACH` line + a distinct alarm
email, without discarding the still-valid subagent findings. Built TDD (36 tests incl. a real-transcript
integration check that catches this run's fallback) + a mandatory adversarial REFUTE pass that caught a
real false-PASS class (silently-skipped unparseable lines) since fixed. **PR:**
https://github.com/ZeOoba/ora-claude-config/pull/64 — branch `fix/oi-052-model-floor-gate`. This does
NOT resolve the underlying platform gap (the pin still isn't held for the run's duration — Claude Code
issue #48976); it makes the breach VISIBLE every run rather than silent. The open question (does "never
below Fable" treat a mid-run Opus fallback as compliant?) is still Gabriel's to answer; if "no", the
platform issue is the remaining work. The PR is now MERGED; item stays OPEN pending only Gabriel's ruling on the open question (and, if "no", the upstream platform fix — Claude Code issue #48976).
**Auto-check:** the probe itself is now the auto-check, once merged and invoked by the sweep.

### OI-058
**Status:** OPEN
**Opened:** 2026-08-03
**Source:** `ora-pm-ledger` 2026-08-01 run + the OI-030 coherence read, 2026-08-03
**Description:** `ora-weekly-hygiene` Block C (SharePoint Aging & Freshness) executed its 2026-08-02
cycle - the task's `lastRunAt` is `2026-08-03T07:47:46Z` (03:47 ET, a late catch-up fire) - but produced
none of its three required outputs. Verified null on all three independently: newest XLSX in
`Claude_Workspace\Reports\` is `20260726_SharePoint_Freshness-Audit_v01.xlsx`; newest Notion page is
`SharePoint Freshness Audit - 2026-07-26`; newest send-log entry is `ORA SharePoint Freshness - 2026-07-26`.
One full weekly cycle lost; last successful output was 8 days old at filing.
**Why it matters:** the block is *audit-only*, so a silent no-op costs no data - but it is indistinguishable
in every downstream surface from a clean run. Nothing in the fleet alarms on "a block inside a composite
task produced no artifact," which is the same structural blind spot as
[open-items-tracker.md#OI-031](open-items-tracker.md#OI-031) (`fleet-status.py` cannot see a single skipped
cycle on an established recurring task) - there, at task level; here, one level finer, at block level
*within* a task that did fire and did stamp `lastRunAt`.
**Two candidate causes, not yet distinguished:** (a) the session terminated or was truncated before reaching
Block C - it is the third of fifteen blocks in a long sequential run; (b) Block C ran and failed silently,
most plausibly on the check-C Notion query (see [open-items-tracker.md#OI-030](open-items-tracker.md#OI-030)
evidence #4 - `bcfe4a03` 404s on the obvious endpoint, and until the 2026-08-03 fix there was no instruction
to report that as a coverage gap rather than a zero).
**Next step:** pull the 2026-08-03 03:47 ET run transcript and determine which. If (a), the question is whether
a 15-block sequential task is too long to complete reliably on a catch-up fire. If (b), the 2026-08-03 check-C
endpoint fix may already have closed it - verify against the 2026-08-10 run rather than assuming.
**Do not close on a single clean 2026-08-10 run** without knowing which cause applied; a one-off pass does not
distinguish "fixed" from "did not recur."
**Auto-check:** none.

### OI-057
**Status:** REOPENED 2026-08-12 (was CLOSED 2026-08-04) — see "REOPENED" block at the end of this item
**Opened:** 2026-08-03
**Closed:** 2026-08-04
**Reopened:** 2026-08-12
**Evidence (status-line reconciliation 2026-08-05):** this detail section's `Status:` was left at OPEN
when the item was closed — the Closed-table row was moved and dated correctly, but the flip never
happened here, so the two contradicted each other. Reconciled in favour of the row: `6dc5df3`
("perf(tests): shared git-repo fixture for the hook test suites (OI-061)") verified present in history,
landing `hooks/tests/lib/gitfixture.py` (+135) and converting `hooks/tests/test-eos-review-gate.py` —
exactly the fix the row cites. See also the COUNTER-EVIDENCE block below, which had already falsified
the "will block the next push" claim as stated.
**Source:** Push of event_log.md commit `8b61f20`, 2026-08-03
**Description:** `hooks/tests/test-eos-review-gate.py` timed out on pre-push (exit 124, 180s, reproduced
identically 3x). `run_hook()` spawns the real `eos-review-gate.py` subprocess with no timeout of its own;
suspected cause is a live independent-review model call inside that hook contending with other concurrently
active sessions (unconfirmed - Gabriel chose override over investigation that run). Bypassed via a
session-scoped `allow-hook-test-failure` override token to land that push.
**⚠ COUNTER-EVIDENCE 2026-08-03 ~19:38-19:42 ET - the 'will block the next push (any session)' claim is
FALSIFIED AS STATED.** Session `ffa9b1ef` pushed `ora-claude-config` twice in four minutes. Both attempts ran
the full pre-push doctrine gate **to completion**:
- attempt 1 - `hook-tests-gate: 62 pass, 0 fail, 0 env-skip (of 62)`
- attempt 2 - `hook-tests-gate: 63 pass, 0 fail, 0 env-skip (of 63)` (63rd = `test-memory-subindex-guards.py`,
  arriving with PR #31 in between)
`test-eos-review-gate.py` did **not** time out on either run, and **no `allow-hook-test-failure` token was
created or needed**. Attempt 1 did fail - but on a concurrent-push ref race (`cannot lock ref 'refs/heads/main':
is at 5c994ba... but expected b91475a...`, PR #31 landing underneath), which is a different failure entirely.
Attempt 2 pushed clean: `5c994ba..f1bdafe`.
**What this does and does not mean.** It does NOT mean the defect is fixed - two clean runs are an absence of
the symptom, not a root cause, and nothing about `run_hook()`'s missing subprocess timeout has changed. What it
does establish is that the timeout is **non-deterministic**, not a standing block. That is consistent with this
item's own contention hypothesis: under low concurrent-session load the hook completes normally. Anyone reading
the original row would have expected a blocked push and reached for an override token they did not need.
**Cheapest next discriminator:** on the next occurrence, capture the number of concurrently active sessions
(and whether any is mid-model-call) at the moment of the timeout, before overriding. That single datum
confirms or kills the contention hypothesis without touching the hook. The durable fix regardless is an
explicit timeout on the `run_hook()` subprocess so the failure is a clean, attributable error rather than a
180s hang.
**✅ THE 180s QUESTION IS ANSWERED - and it REVERSES the reading above (2026-08-03, later same evening).**
`PER_TEST_TIMEOUT_SECONDS = 90` has been 90 continuously since at least 2026-07-24 (checked across six commits
of `hooks/git-prepush-hook-tests-gate.py`). The doubled-budget retry landed in `55522aa` at **2026-07-26
15:02**. This item's triggering push - of `8b61f20` - was **2026-08-03 16:20, eight days later**. So the retry
was already in force, and **180s = 90 x TIMEOUT_RETRY_MULTIPLIER = the DOUBLED budget.** This item's event was
therefore the *rerun* also timing out, which by the gate's own stated policy is a genuine blocking FAIL: "a
test that cannot finish inside DOUBLE the budget even once signals a genuine hang, not load." It was not an
unmitigated first-run timeout.
**Consequence - the two events are different severities, not the same failure recurring:**
| | This item's event (16:20) | Third push (19:43) |
|---|---|---|
| Budget reached | 180s = first run **and** doubled rerun | 90s first run only |
| Gate verdict | blocking FAIL | `timeout-retry ... not blocking` |
| Resolution | `allow-hook-test-failure` override | absorbed by the retry, no override |
**CORRECTION of my own COUNTER-EVIDENCE paragraph above (same session, ~1 hour earlier).** That paragraph is
factually accurate on its narrow claims - two pushes at 19:38-19:42 did pass with 0 fail and no override - but
its framing was wrong twice, and the corrected reading is the one to trust:
- It called the timeout **"non-deterministic"**. Wrong shape. The timeout is not intermittently absent; it
  recurred on the very next push (19:43). What varies is only whether it clears the FIRST budget or also the
  second. The gate absorbs the former and blocks on the latter.
- It said `run_hook()`'s missing subprocess timeout "is unchanged", implying nothing mitigates this. True of
  that function in isolation, but **misleading**: a gate-level mitigation has existed since 2026-07-26.
- It treated the 'will block the next push' claim as simply FALSIFIED. Better: that claim is **too strong but
  not baseless** - a push under sufficient load still blocks, which is exactly what happened at 16:20.
**Also stale in this item's own Description: the cause is NOT "unconfirmed".** It was root-caused 2026-07-26 and
is documented in `hooks/git-prepush-hook-tests-gate.py`'s module docstring: during a push with three other live
sessions, this file - the suite's outlier at **48 subprocess spawns** - blew the flat 90s budget and blocked,
then passed all 48 tests quickly on isolated rerun. An environmental load flake. This item was filed a week
later still calling that hypothesis unconfirmed.
**STAYS OPEN, with the real defect restated:** the gate is behaving correctly; the *test* is slow enough that
under real concurrent load it can exceed even 180s. Two candidate fixes - (a) cut its 48 subprocess spawns
(attacks the cause), or (b) give this known outlier a larger budget, which the gate's docstring deliberately
rejects as a per-file roster that would rot. (a) is the better target. **Do not close this on quiet-machine
pushes**; only a push under comparable multi-session load tests it.
**Auto-check:** none.

**REOPENED 2026-08-12 — the symptom recurred, exactly as this item predicted.**
Closed 2026-08-04 alongside its cause [OI-059](#OI-059) on `6dc5df3`. The closing evidence was a re-measurement
at **56 dirty files** — real load, but not the load that matters. On 2026-08-12, at **26 concurrent sessions /
117 dirty files / 16 cores pinned at 100% / 53 simultaneous python processes**, the symptom returned in its
original form: a real push hard-blocked when `test-eos-review-gate.py` AND
`test-memory-orphan-link-guard.py` each exceeded the 90s budget *and* the 180s retry. Both then passed when
rerun in isolation on the same still-loaded box — 55/55 in 140s, 79/79 in 105s. This item's own closing
instruction ("only a push under comparable multi-session load tests it") was the correct standard and was not
met by the 08-04 close.
**Warning this item got right, and the one it got wrong.** Right: option (a), cutting spawns, was indeed the
better *cause*-directed target — and it was done (559→199, 272→147) and still proved insufficient, because the
dominant term turned out to be per-spawn cost under contention, not spawn count. Bare `python -c pass`
measured **348ms then 1390ms** minutes apart against ~30-50ms idle; at that multiplier no achievable spawn
count saves the file. Wrong, or at least too narrow: the text rejects "(b) a larger budget" by citing the
docstring's objection to **a per-file known-slow roster that would rot**. That objection is sound and still
stands — but it does not apply to raising the *global* `PER_TEST_TIMEOUT_SECONDS`, which adds no per-file
roster and cannot rot. `c29ec95` took exactly that route: 90 → 240 global (ceiling 180s → 480s). Do not read
this item as having pre-rejected that fix; it rejected a different one.
**Why it stays open:** the budget raise is a mitigation. This item is the *symptom* — pre-push gate timeouts —
and the symptom recurs whenever load outruns whatever budget is set. It closes only when gate pass/fail stops
being coupled to machine load (bound the concurrency, or run the suite under a concurrency cap), not when a
push happens to pass. **The 08-04 close is the cautionary precedent: it was validated on a quieter machine
than the one that breaks it.**
**Mirror item:** [OI-059](#OI-059), the cause side, reopened the same day on the same evidence.

### OI-059
**Status:** REOPENED 2026-08-12 (was CLOSED 2026-08-04) — see "REOPENED" block at the end of this item
**Opened:** 2026-08-03
**Closed:** 2026-08-04
**Reopened:** 2026-08-12
**Evidence (status-line reconciliation 2026-08-05):** same defect as [OI-057](#OI-057) — the Closed-table
row was moved and dated, but this detail section's `Status:` was never flipped, leaving the two
contradicting each other. Reconciled in favour of the row: `6dc5df3` verified present in history, landing
the shared `hooks/tests/lib/gitfixture.py` (+135, with `test-gitfixture.py` +122) and converting
`test-eos-review-gate.py` and `test-memory-orphan-link-guard.py` onto it — the `make_repo()` spawn cost
this item was filed to remove.
**Source:** [open-items-tracker.md#OI-057](open-items-tracker.md#OI-057) root-cause pass, 2026-08-03
**Description:** `hooks/tests/test-eos-review-gate.py` (1045 lines, 55 tests) is the pre-push suite's runtime
outlier and the direct cause of OI-057's timeouts. **Measured 2026-08-03, not estimated:**
- **44-67s wall-clock running the file alone on an otherwise-idle machine** (three independent clean runs:
  44.2s, ~60s, 66.5s), against the gate's `PER_TEST_TIMEOUT_SECONDS = 90`. A thin AND highly variable margin -
  the variance matters as much as the mean. Under real concurrent load it exceeds 90s (first-budget timeout,
  absorbed by the retry) and can exceed 180s (both budgets, a hard block). Both OI-057 events fall out of this.
- **559 subprocess spawns per run**, measured by wrapping `subprocess.Popen` with a counter around a full run:
  **451 `git` + 108 Python**. Of the git spawns, **365 come from the `make_repo()` fixture** (**73 runtime
  calls** x 5: init + 2x config + add + commit); the remaining ~86 are direct `git()` helper calls. The fixture
  is **65% of all spawns** - it is the thing to fix.

**⚠ FIGURES CORRECTED 2026-08-03 (this entry originally carried WRONG numbers - the same error class it was
filed to fix).** As first filed this item claimed "~344 spawns (270 git + 74 Python), 54 make_repo() calls,
~7x undercount." Those were **static grep call-site counts presented as measurements**. An independent review
REJECTED them and instrumented the actual run; a second independent instrumented run confirmed the reviewer
exactly. Two things made the grep wrong: it counted the `def make_repo():`/`def run_hook():` lines as call
sites, and - the larger error - **two loops call `make_repo()` once per iteration** (a 14-case risk-class loop
and an 8-form pathspec loop), so 53 static sites produce 73 runtime calls. **Lesson: a spawn count is a runtime
property; grep cannot measure it.** That is precisely the mistake the original "48" made, so filing it again
here would have been self-refuting.
**Corrects a stale figure (fix REVIEWED, not yet landed - see below):** `hooks/git-prepush-hook-tests-gate.py`'s module docstring calls this file "the
suite's outlier at 48 subprocess spawns." 48 undercounts by ~11.6x. It is that file's TEST count (48 then, 55 now), and the git
fixture - 65% of the real cost - is missing from it entirely. Worth correcting there so
the next reader optimises the right thing.

**Docstring fix status: reviewed and APPROVED, BLOCKED on a guard deadlock (2026-08-03).** The corrected
docstring is committed-ready in worktree `fix/spawn-count-docstring` (branch off `59155c4`). It passed two
independent review rounds - the first REJECTED it over the bad figures above, the second APPROVED after they
were re-measured, proving behavioural inertness three ways (AST minus docstring node, token stream with
comments masked, recursive bytecode compare) with the gate's own suite 75/75. It cannot LAND because
`eos-review-gate` requires a recorded review artifact and `config-write-guard` blocks `--record` for naming
`hooks/` - the documented deadlock in [[reference_config_write_guard_blocks_eos_review_gate]]. Gabriel ruled
2026-08-03: WAIT for session 83715320's config-write-guard hooks/sessions carve-out rather than mint an
override. **Land it once that carve-out ships** - the worktree is the pending work, do not redo it.
**Recommended fix - attack the fixture, not the budget.** Build ONE template repo per run and `shutil.copytree`
it per test (a filesystem copy of a tiny repo is far cheaper than 5 process spawns). That removes roughly 265
of the 270 git spawns and should be the bulk of the 66.5s, with no change to what any test asserts. Do this
first and re-measure before touching anything else.
**⚠ Do NOT bulk-convert the 74 hook invocations to in-process calls.** This is a SECURITY-GATE test
(`hooks/**` override/auth/exit-code logic). The subprocess boundary *is* part of the contract under test -
exit codes, the stdin JSON protocol, env-var isolation - and importing the hook to call it directly would let
the suite pass while the real invoked path is broken. That is the precise failure class these gates exist to
prevent. If any of these are converted later, keep a meaningful set as true end-to-end subprocess tests, and
per CLAUDE.md that change takes the MANDATORY adversarial REFUTE pass for security-gate code.
**Acceptance:** re-measure the file's isolated wall-clock after the fixture change; it should land far enough
under 90s that concurrent load has real margin, and the pre-push summary should stop emitting
`timeout-retry ... not blocking` for it on ordinary pushes. Do not treat a single quiet-machine pass as
acceptance - the failure is load-dependent (see OI-057).
**Relationship to other items:** OI-057 is the *symptom* (timeouts at the gate) and stays open until this is
fixed; this item is the *cause*. The gate's own parallel worker pool (added 2026-07-26, OI-028) already
mitigates suite-level wall-clock but cannot help a single file that exceeds a per-file budget on its own.

**REOPENED 2026-08-12 — the 08-04 closure did not survive real concurrency.**
Closed on `6dc5df3`'s spawn reduction (`test-eos-review-gate.py` 559 -> 199,
`test-memory-orphan-link-guard.py` 272 -> 147). That fix was real; its margin was not. The closure was
validated at ~56 dirty files and a handful of live sessions. At 26 concurrent sessions it failed outright:
both files blew the 90s budget AND the 180s retry and hard-blocked a real push, then **both passed when
rerun in isolation on the same still-loaded box** — `test-eos-review-gate.py` 55/55 in 140s,
`test-memory-orphan-link-guard.py` 79/79 in 105s. A false block, not a regression.
- **Measured conditions at block time:** 26 sessions, 117 dirty files, 16 logical cores pinned at 100% CPU,
  5.6 GB free of 32 GB, 53 simultaneous python processes.
- **Bare `python -c pass` spawn cost, sampled twice minutes apart: 348ms then 1390ms**, against ~30-50ms
  idle. The dominant term is process-creation cost under contention, which no in-test optimisation controls.
  Further spawn cuts would mean cutting hook invocations, which this item and [OI-061](#OI-061) both forbid,
  since the subprocess boundary is part of what a security-gate test exists to verify.
**Mitigated, not fixed, in `c29ec95`:** `PER_TEST_TIMEOUT_SECONDS` 90 -> 240 (hard ceiling 180s -> 480s),
plus three docstring corrections in `hooks/git-prepush-hook-tests-gate.py` — it still cited 559 spawns as
current, still pointed at "Fix: OI-059" as open work, and still justified the retry rule with *"a test that
cannot finish inside DOUBLE the budget even once signals a genuine hang, not load,"* which today disproved.
`hooks/tests/lib/gitfixture.py` carried the same stale 90s claim in the present tense and was corrected with
it. Both suites green after the change (79/79 and 79/79).
**Why this stays OPEN rather than re-closing on `c29ec95`:** a budget raise is a mitigation. Gate reliability
is still coupled to machine load, 240s is sized to one day's measurements, and the same failure returns at
higher concurrency. A real fix bounds the load (cap concurrent sessions, or run the suite under a concurrency
limit) or decouples gate pass/fail from wall-clock. **Do not re-close on a quiet-machine push** — a
quiet-machine validation is exactly what produced the premature 08-04 close.
**Correction to this item's own earlier text:** the paragraph above describing the file as "the suite's
outlier at **48 subprocess spawns**" is wrong in the same way this item was filed to fix — 48 is the file's
TEST count, never its spawn count (559 pre-fix, 199 post-fix). The gate docstring already carried this
correction; this item never received it.
**Mirror item:** [OI-057](#OI-057) was closed 2026-08-04 on the same evidence and has recurred identically —
it is the symptom side of this same defect and should be reopened with it.

### OI-060
**Status:** OPEN
**Opened:** 2026-08-03
**Source:** ora-pm appsec fix plan (subagent-driven-development execution of `plan/appsec-fixes-oi034-048`), Task 5 (OI-037 CORS + security headers), commit `5a23927`
**Description:** Task 5 added `public/_headers` to ora-pm to close OI-037 (missing CORS allowlist + security headers). The task's independent reviewer (fable model) found that Cloudflare Pages' `_headers` mechanism only applies to **static assets** — it does not apply to responses served by a **Pages Function**. ora-pm's `/api/*` routes are served by `functions/api/[[route]].ts`, a Pages Function, so none of `_headers`'s directives (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, HSTS, Permissions-Policy) actually reach API responses. OI-037's own motivating example (`curl -I https://ora-pm.pages.dev/api/health` showing no security headers) is therefore **not fixed** by Task 5 for the API surface, even though the fix is correctly applied and verified for document/page routes (clickjacking protection, page-level CSP).
**How to apply:** add a Hono middleware (in `server/index.ts`, or a small new module mirroring `server/lib/`'s existing structure) that sets the same header set as `public/_headers` on every `/api/*` response. Reuse the exact directive values already committed in `public/_headers` rather than re-deriving them, so the two surfaces stay in sync. Should get the same TDD + independent-review treatment as the rest of the appsec-fix work (this is still security-gate code). Deliberately not folded into Task 5 itself — Gabriel's call, 2026-08-03, to keep that task's scope and review clean rather than expand it mid-flight.
**Auto-check:** none.

### OI-064
**Status:** OPEN
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

### OI-065
**Status:** OPEN
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

### OI-066
**Status:** OPEN
**Opened:** 2026-08-03
**Source:** REFUTE pass on the [OI-037](#OI-037) fix (security-auditor dispatch), 2026-08-03; verified directly by the Code-surface session that merged it
**Severity:** MEDIUM (XSS containment — deliberately deferred, not an oversight)
**Description:** `public/_headers`, commit `23b924f`. The CSP shipped as
`Content-Security-Policy-Report-Only`, not enforcing — by design, per the header file's own comment:
this environment can't open a real browser to click through the live Pay Now flow (Stripe Elements
iframe + redirect, Supabase auth) to confirm the policy doesn't break it, so Report-Only ships the
identical policy and only logs would-be violations to the console. `X-Frame-Options: DENY` is a
separate, already-enforcing header and closes the clickjacking half of OI-037 independent of this —
this item is ONLY about the XSS-containment half (an injected script would still execute with full
origin privileges against the shared portal/admin session, since the CSP that would block it isn't
enforcing yet).
**Candidate fix (NOT applied):** a manual browser verification pass against a deployed preview
(click through account linking, bank-account SetupIntent, PaymentIntent confirmation, and the admin
login/CRUD flows), watching the console for CSP violation reports; if clean, drop `-Report-Only` from
the header name in `public/_headers` to flip to enforcing. If violations surface, adjust the policy's
`connect-src`/`script-src`/`frame-src` directives (already scoped to `'self'`, Stripe, and Supabase)
before enforcing, not after.
**Auto-check:** none.

### OI-071
**Status:** OPEN
**Opened:** 2026-08-03
**Source:** Production verification of [OI-067](#OI-067), 2026-08-03
**Severity:** MEDIUM (broken feature, confirmed — not a security exposure; the RLS policy is correct and holding)
**Description:** `src/portal/pages/PortalInsurance.tsx` uploads tenant COI files to
`${session.user.id}/${file.name}` in the `insurance-certs` bucket, but the live `tenant_upload_insurance`
RLS policy (confirmed applied and correct, see OI-067) requires the folder to equal `tenants.id`
(resolved via `tenants.auth_user_id = auth.uid()`). Every real tenant COI upload through this page
fails today — confirmed against production, not just the repo.
**Candidate fix:** the variable is even misleadingly named `const tenantId = session.user.id` —
should instead look up the tenant's own `id` (e.g. from the already-loaded portal session/tenant
context) and upload to `${tenant.id}/${file.name}`. Add an integration test asserting the upload path
matches the RLS policy's expected folder, not just that the upload call is made.
**Corroborated independently, 2026-08-04:** a REFUTE pass on the OI-048 docs/tripwire fix, reading
`server/db/client.ts` cold with no knowledge of this item, re-derived the exact same
`session.user.id`-vs-`tenants.id` mismatch from first principles. Two independent passes reaching the
identical root cause is corroboration, not new information — no change to this item's status or scope.
**Auto-check:** none.

### OI-070
**Status:** OPEN
**Opened:** 2026-08-04
**Source:** `ora-health-guard` 2026-08-04 run (self-detected via its own `main*.log` read) + direct
reading of `fleet-status.py`, this session
**Description:** `find_missed_cycles()` (OI-031's fix, live since 2026-07-27) compares each enabled
recurring task's `lastRunAt` against only the single most-recent expected cron-fire time as of
now — a point-in-time check. The registry stores no run history beyond that one scalar, so the
moment a previously-missed task fires again, `lastRunAt` advances and the gap collapses to ~0h
with no trace of the earlier miss. Confirmed today: `ora-health-guard` itself produced nothing on
2026-07-31, 08-01, and 08-02, then resumed 08-03 and 08-04 — but the 08-04 `fleet-status.py` run
reported "missed single cycle 0" because by the time it ran, `lastRunAt` already reflected the
fresh same-day fire. The 3-day gap was visible only via the scheduler's own `main*.log` run
history, which `fleet-status.py` never reads. Same family as [OI-031](#OI-031) (currently-open
single-cycle miss, fixed) and [OI-058](#OI-058) (a coarser instance of this same blind spot) —
this item is the narrower "self-healed before the next check" case neither of those covers.
**Candidate fix (not built):** (a) have `fleet-status.py` persist its own `lastRunAt` snapshot
across invocations (e.g. `_state/fleet-status-history.json`) and diff against the prior snapshot
to catch a gap prospectively — cheap, but only detects gaps occurring after the tracking file
exists; (b) parse the scheduler's own run-history log (the same `main*.log` `ora-health-guard`
read) for a true historical census over a lookback window — most complete, heavier lift,
duplicates what health-guard already reconstructs ad hoc; (c) at minimum, relabel the "missed
single cycle" output so a `0` doesn't read as a clean historical census when it's only a
point-in-time check (DONE — commit `848d4cb`).
**Commit `848d4cb`'s own message says "closes OI-070" — that claim is wrong, and this item is
deliberately left OPEN despite it.** The commit's diff (`maintenance/fleet-status.py`, +18/-1) is
option (c) above and nothing more: it relabels the plain-text line to "missed single cycle
(currently open)", adds a `missed_cycle_scope` JSON caveat, and adds inline comments — its own
body states "no detection logic changed." Neither (a) nor (b) is built, so `fleet-status.py`
still cannot detect a self-healed historical gap; it can only now describe that limitation
honestly instead of silently misreporting it. Do not close this item on the strength of that
commit alone — closure needs (a) or (b) actually landed and verified.
**Auto-check:** none (a tooling-logic gap, not a fleet-registry state comparable to the closed
Auto-check vocabulary above).

### OI-061
**Status:** OPEN
**Opened:** 2026-08-03
**Source:** Fixture measurement taken while root-causing [open-items-tracker.md#OI-059](open-items-tracker.md#OI-059), 2026-08-03
**Description:** **13** test files across `hooks/tests/`, `maintenance/_tests/` and `maintenance/` each
hand-roll their own throwaway git-repo fixture, every one paying ~5 process spawns per repo built (`git init`
+ 2x `git config` + `git add` + `git commit`). There is no shared helper. In `test-eos-review-gate.py` alone
that fixture accounts for **365 of its 559 spawns (65%)** - see OI-059.
**Measured 2026-08-03** (each file run as its own subprocess, as the gate runs them):

| file | secs | % of the 90s per-file budget |
|---|---|---|
| `test-eos-review-gate.py` | **141.7** | **157% - OVER BUDGET** |
| `test-memory-orphan-link-guard.py` | 46.3 | 51% |
| `test-confidentiality-guard.py` | 42.0 — **load-contaminated, see below** | 47% |
| `test-git-prepush-scan.py` | 31.2 | 35% |
| `test-commit-provenance-guard.py` | 29.2 | 32% |
| `test-shared-checkout-guard.py` | 19.6 | 22% |
| `test-doctrine-integrity-probe.py` | 18.4 | 20% |
| (5 more) | 2.1-7.0 | <8% |
| **sequential total, 12 files** | **347.1** | |

**Why this is a SEPARATE item from OI-059.** OI-059 is scoped to getting ONE file back under its budget. This
is the cross-cutting cause and is **preventive**: the second-worst file is already at **51%** of the budget
with nothing pathological about it, so the next file to grow hits the same wall and files another OI-057. The
141.7s reading above is the point - that run happened while this session was doing other work, i.e. exactly
the multi-session load condition OI-057 documented. On a quiet machine the same file takes 44-67s. **The
budget is not the problem; the per-test process cost is.**
**Proposed fix:** one shared helper (e.g. `hooks/tests/lib/gitfixture.py`) that builds a template repo ONCE
per test process and `shutil.copytree`s it per test. A filesystem copy of a tiny repo is far cheaper than 5
spawns, and the git object store copies intact, so the resulting repo is byte-identical to a freshly-inited
one. Expected to remove the large majority of the ~365-per-file fixture spawns.
**Amended 2026-08-04, after two sessions independently reached opposite verdicts on the same file (see
OI-072's THIRD CORRECTION): spawn reduction is NOT the only valid reason to convert a file to this helper.**
Dedup/consistency — one shared fixture implementation instead of N hand-rolled copies, shrinking the
surface a future silent-divergence bug can hide in — is a co-equal, independent justification, valid even
at spawn-parity. Weigh both axes before writing off a candidate as "not worth it."
**⚠ Constraints - this is the verification layer for security gates, so treat it as such:**
- **A shared fixture becomes a single point of failure for 13 test files.** If it silently produces a subtly
  different repo (missing config, different default branch name, no initial commit), tests can pass while no
  longer exercising what they claim. Keep it small, and assert its invariants in its own test.
- **Convert incrementally, top-3 first, and re-measure between each.** Do NOT convert all 13 in one pass.
- **Each converted file must still pass with its assertions UNCHANGED.** A fixture change that requires
  editing assertions is a behaviour change in disguise - stop and re-examine.
- Per CLAUDE.md, changes under `hooks/**` take the independent-review gate; expect the same
  `config-write-guard`/`eos-review-gate` interaction that currently blocks OI-059's docstring fix
  ([[reference_config_write_guard_blocks_eos_review_gate]]), so plan to land this from a worktree.
**Acceptance:** re-run the timing table above; the top three should drop materially and nothing should regress
in pass counts. Do not accept on a quiet-machine run alone - re-measure under concurrent load, since that is
the condition that actually blocks pushes.
**✅ LANDED 2026-08-04 for files 1-2 of 3 — commit `6dc5df3` (merge `fc653db`), pushed to origin/main.**
Pushed from the isolated worktree `perf/shared-git-fixture`, never through the shared checkout (which held
55+ other sessions' uncommitted changes throughout). Pre-push gate clean: 63 pass / 0 fail / 1 env-skip.
Shipped: `hooks/tests/lib/gitfixture.py` (build each repo shape ONCE per process, `shutil.copytree` per call)
plus `hooks/tests/test-gitfixture.py` asserting its invariants — including the load-bearing one, that 20
further calls spawn NOTHING. Converted `test-eos-review-gate.py` and `test-memory-orphan-link-guard.py`.

| file | spawns | median wall-clock |
|---|---|---|
| `test-eos-review-gate.py` | 559 → **199** | 34.4s → **24.0s (~30%)** |
| `test-memory-orphan-link-guard.py` | 272 → **147** | 18.9s → **15.4s (~18%)** |

**⚠ CORRECTION — an earlier report of this work claimed a 65% win (95.8s → 33.2s). That headline was
LOAD-INFLATED and should not be quoted.** Those medians came from a heavily-loaded machine (the same session
was running other suites concurrently), which inflates the BEFORE far more than the AFTER because spawn cost is
what load multiplies. The independent reviewer's interleaved runs on a quieter box give ~30% and ~18%, and
those are the numbers to use. The spawn-count reductions (559→199, 272→147) were reproduced EXACTLY by the
reviewer and are load-independent — prefer them as the durable metric.

**Both converted files are now PYTHON-SPAWN-BOUND, i.e. the fixture work is essentially complete, not half
done.** Measured per-spawn cost on this machine: git 112ms, bare python 137ms, python+hook 252ms. The residual
floors are 108 hook invocations (~27s) for file 1 and 72 (~18s) for file 2, against medians of 24.0s and 15.4s.
Further gains would require cutting hook invocations — which this item and OI-059 both forbid, because that
subprocess boundary is exactly what a security-gate test exists to verify. **Do not chase the remaining time.**

**✅ FILE 3 (`test-confidentiality-guard.py`) CLOSED 2026-08-04 — NOT APPLICABLE. Do not convert it.**
Profiled in the MAIN checkout on 2026-08-04 (it ENV-SKIPs in any linked worktree, which is why it had never
been profiled and why it was carried as blocked rather than assessed). The fixture is **not** this file's cost:

| | measured |
|---|---|
| total spawns | **131** |
| — Python (guard invocations) | **125** |
| — git | **6** |

The 6 git spawns are ONE repo build (init + 2x config + add + commit) plus a single `worktree` call. Converting
to `gitfixture` would remove **at most 5 of 131 spawns (<4%)**. The cost is the 125 Python spawns — roughly one
per its 131 tests — and those are exactly the hook invocations this item and OI-059 both forbid cutting, since
that subprocess boundary is what a security-gate test exists to verify. **There is no safe optimisation here.**

**The "3rd-worst, 42.0s" ranking that put it on this list was WRONG — measured under self-inflicted load.**
That figure came from a batch timing run while this session was executing other suites concurrently. Clean
runs 2026-08-04: **33.4s / 49.1s / 49.6s, median 49.1s = 55% of the 90s budget**. Comfortable, and it has never
tripped the gate. The 33→50s spread is ambient load, not fixture cost. **Lesson, same class as the rest of
this item: a timing taken while the measurer is loading the machine ranks files by ambient noise, not by their
own cost — interleave or idle before ranking.**

Weighed and rejected on cost/benefit: converting would have meant editing security-gate code inside a checkout
holding 55+ other sessions' uncommitted changes, minting another governance-write token, and spending a full
independent review round — to remove five subprocess spawns. (Separately, copying the gitignored live
`confidential-terms.json` into a worktree to make it runnable there was rejected outright: it holds
confidential deal terms.)
**Independent review (claude-fable-5): APPROVED.** Verified equivalence byte-for-byte (working-tree bytes AND
blob SHAs, `git fsck --strict` clean, no absolute paths in copied `.git`, add/commit/reset/worktree/stash all
functional in a copied repo); confirmed ZERO assertion drift (55 `def test_` before and after, only fixture
construction changed); confirmed newline fidelity by raw-byte comparison; ran an adversarial cache-key battery
(dict ordering, quote smuggling, content-boundary shuffle) finding no collision and no template-poisoning path;
confirmed per-process isolation under the gate's parallel runner. **Most valuable check: a SABOTAGE test** —
stubbing both guards to `exit 0` made the suites fail 40-of-55 and 46-of-79, proving they are still load-bearing
rather than merely green. Full discovered suite: 63 pass / 1 env-skip / 0 fail.

**Three minor defects raised; two FIXED after approval, one accepted:**
1. FIXED — the fixture wrote with `encoding="utf-8"` where eos's original `write()` used `"ascii"`. Identical
   bytes today, but it silently lost FAIL-FAST: a future fixture string containing a smart quote would have
   committed UTF-8 instead of raising `UnicodeEncodeError`. `encoding` is now a parameter (and part of the cache
   key); the caller passes `"ascii"`; verified the error is raised again.
2. FIXED — a comment claimed the `gitfixture` import had to follow the GIT_* env scrub. It does not (template
   construction is lazy), and the other converted file imports before its own scrub. The comment was wrong and
   invited cargo-culting; it now states the real invariant and flags that eager construction WOULD break it.
3. ACCEPTED — `reset_cache()` drops template refs without deleting the dirs (test-only; matches the suite's
   existing leak-and-let-the-OS-reap contract).

**RE-REVIEW WAS DONE, and it caught three more defects — one of which would have shipped broken.** The fixes
above changed content after the first approval, so a fresh review was required rather than a re-record. A FULL
independent pass (claude-fable-5) APPROVED with 1 major + 2 minor; all three were fixed and a DELTA pass then
APPROVED those fixes. What the two rounds found:
1. **MAJOR — `test-gitfixture.py` was missing the 7-var `GIT_*` env scrub the other suites carry.** The reviewer
   REPRODUCED the hazard against a decoy repo: run by hand from a shell where `GIT_DIR`/`GIT_WORK_TREE` point at
   a real repo, the template build's `git init` re-inits THAT repo, overwrites its `user.email`/`user.name` to
   the fixture's `t@t.t`/`t`, and `git add -A && git commit` sweeps pending work into a bogus commit. The
   automated gate path was never exposed (the runner scrubs at spawn); a MANUAL run was. Fixed and re-verified
   both directions — fixed version leaves the decoy untouched, unfixed version corrupts it.
2. MINOR — `_build_template` swallowed git returncodes, so a failing git yielded a silently broken template.
   Now `_must()` raises, and a FAILED build is never cached (10/10 forced-failure battery; a retry re-attempts).
3. MINOR — a comment claimed the fixture covers "all 29 repos this file builds"; actual is 26 (14 direct
   `setup()` + 12 via `_new_orphan_repo`), with 4 hand-rolled by design.

**⚠ The delta review also caught a DELIVERY defect that would have silently shipped nothing.** An earlier
`git add -A` had staged the PRE-fix versions; the subsequent edits left the index holding pre-fix content while
the working tree held the fixes. A commit at that moment would have landed **without all three fixes, including
the MAJOR scrub**. Index was re-staged and confirmed matching the working tree before commit. **Lesson worth
keeping: `git add` then edit then commit is a silent-drop pattern — re-check `git status` for `AM`/`MM` before
any gated commit.**

**Suites remain load-bearing, verified after the fixes, not assumed.** Sabotage test (both guards stubbed to
`exit 0`): eos fails 40/55, orphan fails 46/79 — identical to pre-fix counts, so the changed error path did not
soften them. Guards restored sha256-exact. Full discovered suite 63 pass / 1 env-skip / 0 fail.

**Final measured effect (prefer the spawn counts — they are load-independent and were reproduced exactly by two
independent reviewers):** eos `559 -> 199`, orphan `272 -> 147`. Wall-clock medians improved ~30-34% and
~18-24% across independent interleaved runs on quiet machines. The earlier 65% figure remains WRONG (measured
under self-inflicted load) — do not quote it.

**STAYS OPEN, rescoped.** Files 1-2 of 3 are done and landed. What remains:
- The other ~10 files carrying the same hand-rolled pattern are untouched. They are individually well under
  budget today, so this is preventive, not urgent — but the shared helper now exists, so converting one is a
  small change rather than a design decision.
- **A live post-landing datapoint:** the very push that landed this still emitted
  `timeout-retry ... not blocking` for `test-eos-review-gate.py`. At 199 spawns it is now python-spawn-bound,
  which is exactly why OI-057 stays open and why the residual hook invocations must not be cut to chase it.

**✅ ONE MORE OF THE ~10 LANDED 2026-08-04 — `maintenance/_tests/test_cross_repo_wip_scan.py`, commit
`45fb073`.** Well under budget before conversion (1.47s baseline) — preventive, not urgent — done to prove
the shared helper generalises past the first two files. `init_repo()` (7 call sites, `git init` + 2x
`git config` each = 21 spawns) now delegates to `gitfixture.blank_repo()` and `shutil.move()`s the result
onto the caller's chosen path, so every call site and its enclosing `tempfile.TemporaryDirectory()` scope
is unchanged — zero call-site diff. `blank_repo()`'s `user.email`/`user.name` ("t@t.t"/"t") differ from the
original's ("test@example.com"/"Test"); no assertion here inspects commit author identity, so per this
item's own "assertions unchanged" bar that is not a behaviour change for anything actually tested.
Measured: 23/23 pass unchanged; spawns 21 → 3 (via `gitfixture.spawn_count()`); 0 orphaned temp dirs — this
conversion leaks *less* than files 1-2, because relocating into the caller's `TemporaryDirectory()` scope
means the OS cleans it up rather than leaving it for gitfixture's documented leak-and-reap contract (that
0-leaked result only trusted after catching that a first env-var-based measurement attempt was silently
inert on Windows). No regression in `gitfixture`'s own invariant suite or either already-converted file.
Landed from worktree `perf/oi061-cross-repo-wip-scan`, not the shared checkout. Lighter review than files
1-2's independent-review + sabotage-test rounds, deliberately: this file tests `cross-repo-wip-scan.py`, a
periodic informational status report, not an auth/exit-code security gate, so CLAUDE.md's mandatory-REFUTE
clause does not apply — the `gitfixture` primitive it calls already carries that heavier review. **~9 files
remain**, still preventive.

**✅ "BATCH 2" ALSO LANDED 2026-08-04 (`33e958a`, 13:00) — recorded here retroactively; this entry was
silent about it until now (caught 2026-08-04 by a session that verified `git log` against this file's own
prose instead of trusting it).** Landed *before* the `45fb073` cross-repo-wip-scan conversion above (13:00
vs 15:37) but never got its own note here. Converted 2 more suites to the same `blank_repo()` shape:

| file | git spawns |
|---|---|
| `test-commit-provenance-guard.py` | 179 → 68 (38 `make_repo` sites) |
| `test-shared-checkout-guard.py` | 48 → 3 |

Process-tree-wide (including the guards' own internal git calls): 230 → 119 and 65 → 20. Reviewed
independently twice — the full pass proved `blank_repo()` byte-identical to each hand-rolled repo (config,
default branch, zero commits, `fsck`, every `.git` file) and sabotage-tested both suites (guards stubbed to
exit 0: 41/59 and 12/17 failures, confirming still load-bearing). Fixed 3 findings raised in review: a
duplicate `GIT_*` scrub added on a false premise, dead `_git()` code left behind by the swap, and two wrong
figures in a comment.

The same commit also assessed the rest of the original ~13-file inventory, which is why the "~9/~10 remain"
headline counts elsewhere in this item are now imprecise — **use this itemized list instead of any single
number:**
- **NOT APPLICABLE** (git calls query the real repo or barely exist — not worth a fixture):
  `test-override-token-hygiene.py` (21 git, all real-repo queries), `test-claim-file-collision.py` (3 of
  22), `test-doctrine-integrity-probe.py` (2 of 47), `test-ora-autonomy-gate.py` (1 of 91, already a known
  stale orphan outside the gate's discovery roots)
- **Fits but marginal, undecided:** `test-memory-subindex-guards.py` (~3 spawns saved)
- **Blocked on a real design decision, not effort — filed separately as [OI-072](#OI-072):**
  `test-git-prepush-scan.py`; `test-memory-index-git-tracking.py` (since resolved, `8c9ebd0`, see OI-072);
  and the two `maintenance/`-tree files, `maintenance/_tests/test_cross_repo_wip_scan.py` (since resolved
  by `45fb073` above — OI-072's text calling it "unresolved" is now stale) and
  `maintenance/test-append-event-log.py` (still genuinely open)

**Net effect of this correction: only `test-git-prepush-scan.py` and `maintenance/test-append-event-log.py`
remain from the original inventory, and both are blocked on OI-072's design decisions — read that item in
full before touching either. Neither is a quick body-swap**, contrary to how a candidate list drafted
without this cross-check characterized them.
**Auto-check:** none.

### OI-062
**Status:** OPEN
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

### OI-072
**Status:** OPEN
**Opened:** 2026-08-04
**Source:** [open-items-tracker.md#OI-061](open-items-tracker.md#OI-061) batch-2 scoping, 2026-08-04
**Description:** `hooks/tests/lib/gitfixture.py` (landed `6dc5df3`, extended in use by `33e958a`) models exactly
two repo shapes: `blank_repo()` (init + user config, no commit) and `repo_with_commit()` (adds committed files).
Four suites now depend on it. Two remaining git-heavy suites need shapes it does NOT model, and converting them
means EXTENDING that shared dependency — a design decision, not a mechanical swap, which is why it is filed
rather than done:

| file | git spawns | what it needs that the helper lacks |
|---|---|---|
| `test-git-prepush-scan.py` | 177 | **bare** repos (`git init --bare`), a full origin/clone/push/fetch topology (`_mk_origin_and_clone_state`), branch renames, remotes — and author identity `t@example.invalid`, not the template's `t@t.t` |
| `test-memory-index-git-tracking.py` | 28 | `make_repo(d)` inits a **caller-provided** directory rather than returning a new one (signature mismatch), and uses `user.email "t@t"` — a third identity |

**The identity problem is the crux, and it is a fidelity risk, not a cosmetic one.** Three distinct author
identities are in play across these suites (`t@t.t`, `t@example.invalid`, `t@t`). A shared template that
silently normalises them would change committed author metadata — exactly the class of silent difference that
makes a security-gate suite pass while testing something subtly different. Any extension must key identity into
the cache (as `newline` and `encoding` already are), never default it.
**Also unresolved — where the library lives.** Two more candidates sit in the maintenance tree
(`maintenance/_tests/test_cross_repo_wip_scan.py`, `maintenance/test-append-event-log.py`, ~36 and ~15 git
spawns, 1 init site each). Importing `hooks/tests/lib/` from `maintenance/` creates a cross-tree coupling; the
alternative is relocating the helper to a shared location, which touches every current caller. Decide the
location BEFORE converting either, not after.
**Recommendation: probably DON'T extend it, at least not for topology.** The bare/clone shapes in
`test-git-prepush-scan.py` are genuinely part of what that suite tests (push/fetch behaviour against a real
remote), so hiding them behind a fixture reduces what the test demonstrably exercises. A cheaper, safer option
is to leave that file alone and convert only `test-memory-index-git-tracking.py` behind an explicit
`identity=` parameter. **Do not treat this item as a backlog chore to burn down** — the measured benefit is
modest and the shared-fixture blast radius grows with every shape added.
**Cost/benefit as measured 2026-08-04:** neither file is near the 90s per-file budget on a quiet machine, so
this is preventive. Prefer spawn deltas over timings when re-assessing — timings for these files swing by 3x
on ambient load alone (documented repeatedly in OI-061).
**✅ IDENTITY EXTENSION LANDED 2026-08-04 (`8c9ebd0`), pushed to origin/main.** `blank_repo()` and
`repo_with_commit()` gained `identity=(email, name)` (default `DEFAULT_IDENTITY = ("t@t.t", "t")`, part of the
cache key) and `dest=<dir>` (materialise into a caller-owned directory instead of creating a fresh one).
`test-memory-index-git-tracking.py` converted — its identity `("t@t", "t")` differs from the fixture
default, and its call sites wrap fixture use in `with tempfile.TemporaryDirectory() as d:`, relying on that
block's auto-cleanup rather than the leak-and-reap convention every other caller uses. git spawns 28 -> 16.
Smaller win than the earlier conversions (5 call sites, and per-test `add`/`commit`/`config` calls sit on top
of the one shared init) — this was the last EASY candidate, not a high-value one; done because it was cheap
and safe, not because it was urgent.

Reviewed independently twice, both APPROVED. The full pass proved backward compatibility byte-identical for
all 4 EXISTING dependents (fingerprinted config/branch/commit-count/blob-SHA against the pre-extension
baseline: 55/55, 79/79, 59/59, 17/17, unchanged) and sabotage-tested the converted suite two ways against the
underlying `memory-integrity-probe.py` orphan-link check. It found the cache-collision test only incidentally
caught collisions via a neighbouring assertion — fixed. **The delta review then constructed a SYNTHETIC cache
collision and proved the fix actually catches it** (5 failures) where the original check passed vacuously —
worth naming because it is the strongest form of verification this whole series has produced: not "the test
looks right" but "the test was demonstrated to fail when it should."

**The recommendation against extending for topology STANDS, unchanged.** `test-git-prepush-scan.py` (177 git,
bare repos + origin/clone/push/fetch + a third identity) and the two `maintenance/`-tree files (cross-tree
library-location decision) remain open. Nothing about the identity extension's success argues for tackling
those — they are a different kind of decision, not more of this mechanical work. **Do not read "the fixture
can now take custom identities" as license to also give it bare-repo/clone shapes** — the identity risk
(silently normalised author metadata) is boundable by one cache-keyed tuple; the topology risk (hiding
push/fetch behaviour a suite exists to test behind a fixture) is not fixed by the same mechanism.

**⚠ CORRECTION 2026-08-04 (discovered while drafting a handoff prompt) — the "2 maintenance-tree files"
scope above is STALE.** Another session independently converted `test_cross_repo_wip_scan.py` and landed it
on `origin/main` (branch `perf/oi061-cross-repo-wip-scan`, commit `45fb073`, merge-base-confirmed an ancestor
of the current `main` tip). It also resolved the library-location question this item raised: cross-tree import
via `sys.path.insert(0, os.path.abspath(HOOKS_LIB))` reaching into `hooks/tests/lib/` from `maintenance/`.
That precedent now exists and should be followed, not re-litigated, for the one remaining maintenance-tree
file. This item did not track that session's work in real time — a reminder that this tracker is genuinely
concurrent and a stale in-memory summary can drift from origin within hours.

**STAYS OPEN, rescoped to what is ACTUALLY left as of 2026-08-04 (verified against origin/main, not assumed):**
- `test-git-prepush-scan.py` (177 git) — unconverted. Recommendation against extending for topology stands.
- `maintenance/test-append-event-log.py` (~15 git, 1 init site) — unconverted. The cross-tree import pattern
  is now precedented by `test_cross_repo_wip_scan.py`; this one should be a mechanical follow of that pattern,
  not a fresh design decision.

**⚠ SECOND CORRECTION 2026-08-04 — do NOT convert `maintenance/test-append-event-log.py`; the line above
resolved the design question but never measured whether converting pays for itself, and it doesn't.** Read
the file in full: `_make_temp_git_repo()` (the `init` + 2x `config` shape `gitfixture.blank_repo()` models)
is defined once and called exactly **once**, at module scope — not per-test, not in a loop. Total `git`
subprocess calls in the whole file: **7**, measured (`grep -c` of the `_run_git(`/`_make_temp_git_repo(`
call sites), not the `~15` this item had been carrying unmeasured. Only 3 of those 7 (the ones inside
`_make_temp_git_repo()`) are the fixture-able shape; the other 4 (2x `add` + 2x `commit`) sit outside it and
are unaffected either way. Converting the single call site replaces its 3 spawns with `gitfixture`'s
one-time template build — also 3 spawns, since there is no second call in this process to amortize against
— plus an added `shutil.move`/copy and an import dependency. **Net spawn change: zero.** This is the same
"no fixture to convert" verdict `33e958a` already gave `test-override-token-hygiene.py` /
`test-claim-file-collision.py` / `test-doctrine-integrity-probe.py` / `test-ora-autonomy-gate.py` for the
identical reason (call-count too thin to amortize) — see the batch-2 note under OI-061. It applies here
regardless of the cross-tree-import question being resolved.

**STAYS OPEN, rescoped a third time: only `test-git-prepush-scan.py` remains as a live candidate** from the
original ~13-file inventory (177 git, genuinely fixture-able, blocked on the bare-repo/clone topology design
decision above). `maintenance/test-append-event-log.py` moves to the same bucket as
`test-claim-file-collision.py` et al. — NOT APPLICABLE, not merely deferred. Worktree opened to attempt this
conversion (`perf/oi061-append-event-log`) was closed unused once the measurement above came back negative;
no file was touched.

**⚠ THIRD CORRECTION 2026-08-04 (Gabriel-directed) — RECONSIDER: `maintenance/test-append-event-log.py` WAS
converted after all, merged `dd9c13b`.** The spawn-count measurement two paragraphs up is correct and
stands (7 total git calls, 3 fixture-able, single call site, net spawn change zero) — but "no spawn
benefit" was this item's ONLY decision axis, and a concurrently-running session (worktree
`perf/oi072-append-event-log-fixture`, commit `6eacbb1`, independently reviewed by Opus
pr-review-toolkit:code-reviewer, 40/40 pass, fingerprint-verified against the original hand-rolled repo,
sabotage-tested) converted it anyway on a **different, legitimate axis this item never weighed:
consistency/dedup** — one shared fixture implementation instead of N hand-rolled copies, shrinking the
surface a future silent-divergence bug can hide in (more hand-rolled copies is itself a divergence risk,
the mirror image of OI-061's original "shared fixture is a single point of failure" warning).

Gabriel reviewed both rationales in-turn and directed the merge (2026-08-04, `config-write-guard`
override token minted for the merge specifically). `_make_temp_git_repo()` now delegates to
`gitfixture.blank_repo(prefix="ael-warn-repo-", identity=("t@t.t", "t"))`, matching the hand-rolled shape
and identity exactly. Re-verified post-merge from the merged tree directly (not just the pre-merge branch):
40/40 pass, unchanged.

**Lesson for this item, stated plainly since it recurred twice in one afternoon (see the OI-061 batch-2 note
and this file's own two prior corrections): "no spawn-count benefit" and "not worth converting" are NOT the
same claim.** OI-061's original framing (its "Proposed fix" section) is spawn-reduction-only, which is why
every session working it — including the one that wrote the SECOND CORRECTION above — kept collapsing "zero
measured spawn win" into "reject," missing dedup as an independent, valid reason to convert a hand-rolled
fixture even at spawn-parity.

**CLOSED as far as OI-061/OI-072's file-by-file inventory goes: only `test-git-prepush-scan.py` remains
unconverted**, still correctly blocked on the bare-repo/clone topology design decision, not effort.
**Auto-check:** none.

### OI-074
**Status:** OPEN (partially fixed — CI piece inert pending Gabriel-provisioned secrets)
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

### OI-075
**Status:** OPEN (fix built + scheduled; first live alert not yet observed)
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

### OI-077
**Status:** OPEN
**Opened:** 2026-08-04
**Source:** 3rd (final) REFUTE pass on the [OI-045](#OI-045) fix (security-auditor dispatch), 2026-08-04 —
sweeping `server/routes/` for any remaining tenant-JWT financial-write gap after `/autopay` and the two
Stripe payment-method/money routes were gated
**Severity:** LOW (spoofing-enablement, not a fund-movement or data-exposure bug)
**Description:** `server/routes/stripe.ts:28-57` (`POST /api/stripe/customer`). Deliberately left ungated
by the OI-045 AAL2 work — this endpoint only creates a Stripe customer shell (no PaymentMethod
attached, no money moved), is IDOR-safe (`tenant_id` cross-checked against the JWT-resolved tenant),
and is idempotent (short-circuits to the existing `stripe_customer_id` on repeat calls) — so an aal1
attacker gains no resource-exhaustion or enumeration vector from the endpoint's core purpose. But
`email`/`name` (lines 30, 47) are taken directly from the request body with zero validation against
`tenant.contact_email` and sent straight to `stripe.customers.create`. A tenant (aal1-only session is
sufficient — no MFA bypass even needed, since this route was never gated) can set an arbitrary email on
their own Stripe customer object.
**Impact:** low — no money moves and no cross-tenant data is exposed. But every future Stripe-side
communication on that customer object (receipts, Financial Connections bank-linking links) would be
sent to the attacker-chosen address instead of the tenant's real one — a phishing/spoofing-enablement
vector, and a support/reconciliation headache if a tenant's own customer record silently diverges from
their real contact info.
**Candidate fix (NOT applied):** source `email`/`name` from the already-resolved `tenants` row
server-side (the handler already does `db.from('tenants').select(...)` for the IDOR check — just add
`contact_email`/`name` to that select and use it) instead of trusting the request body. Low priority,
not blocking; noted here so it isn't lost, not because it's urgent.
**Auto-check:** none.

### OI-111
**Status:** OPEN
**Opened:** 2026-08-09
**Source:** four `git push` invocations while landing [PR #41](https://github.com/ZeOoba/ora-claude-config/pull/41) and [PR #44](https://github.com/ZeOoba/ora-claude-config/pull/44) (both merged, `c8ea74e` / `6b197f1`) from the `ora-entry-market-scan` session
**Severity:** LOW — a timing/ergonomics issue. Downgraded from MEDIUM when the Defect 2 correctness claim behind that grade was retracted, and Defect 4's concurrency-safety claim was independently investigated and closed as a budgeting issue (2026-08-12). What remains is Defect 1 (unproven) and Defect 3 (minor, cosmetic).
**Owner note:** `hooks/git-prepush-doctrine-gate.py` was under active edit by session `1ce540e5` / host `local_2648ba07-…` when this was found; their PR #46 (`a880b39`) has since merged. Filed here rather than messaged because `send_message` is unavailable from an unattended (scheduled-task) session.

**RECONCILIATION NOTE (2026-08-15):** this item diverged into two independently-written accounts (HEAD and origin/main branches of the `ora-claude-config` repo) that never saw each other's work. Both made genuine, non-overlapping progress — main correctly retracted Defect 2 and added Defect 3 and the counter-evidence paragraph below; HEAD independently investigated and closed Defect 4. This section merges both. The one place they actually conflict: HEAD's Defect-4 closure is taken as controlling below, but main's account was written without knowledge of that investigation and never had a chance to rebut it — this is a judgment call about which account supersedes, not a resolved factual agreement, and should be confirmed rather than assumed final.

**Defect 1 (OPEN) — the full sweep appears to run on branch DELETIONS, where there are no incoming
objects to validate.** `git push origin --delete` for two merged branches timed out the client at 120s;
the FIRST delete landed and the SECOND did not. The same deletion via `gh api -X DELETE
repos/ZeOoba/ora-claude-config/git/refs/heads/<branch>` returned instantly (exit 0). A delete-only
refspec carries no objects, so the doctrine probe and the `hooks/tests` suite have nothing to check.
`grep` for zero-SHA / delete handling in the gate found none. **Not proven** — the gate's stdout was not
captured on that invocation, so the 120s is consistent with, but does not by itself demonstrate, a full
sweep. Reproduce by pushing a delete with output captured.

**Defect 2 — RETRACTED 2026-08-09, same session, before this item was ever pushed.** Originally filed as
"`error: failed to push some refs` printed on a push that SUCCEEDED", graded MEDIUM as a correctness bug
in failure reporting. **That was a misreading of my own evidence.** The observed sequence was: first
attempt printed the error, a retry was killed by the client at 120s, and the branch was later found on
the remote at the correct SHA. I attributed the landing to the *first* attempt. A later blocked push,
captured in full, shows the gate prints an explicit `--- FAIL: <test> ---` reason alongside
`failed to push some refs` **and the ref genuinely does not land** — i.e. reporting is accurate. The far
likelier reading is that the first attempt genuinely failed and the killed-at-120s **retry succeeded**.
Recorded rather than deleted so the wrong conclusion is not re-derived from the same raw symptom.

**Defect 3 (OPEN, minor) — deliberate negative-path test stderr is indistinguishable from a real
failure.** `maintenance/_tests/test_check_open_items_duplicate_ids.py` exercises the unreadable-tracker
branch, so gate output contains `open-items-tracker ID check: COULD NOT READ <tmp>\does-not-exist.md
... treat as a check failure, not a clean result.` verbatim. It is a *passing test asserting a failure
path*, but it renders exactly like a live check failure and cost real debugging time here. Prefixing
test-sourced stderr, or suppressing it on pass, would fix it.

**Defect 4 — CLOSED 2026-08-12, folded into candidate fix (c) below. Not a separate defect.**

Filed 2026-08-11 as an unverified relay ("the `hooks/tests` suite is not concurrency-safe"), reproduced
2026-08-12, and closed the same day because the reproduction disproved the safety claim and confirmed a
budgeting problem already tracked as fix (c). **The suite is not concurrency-unsafe: zero assertion
failures were observed in either condition.** Every non-pass was `rc=124`, a wall-clock timeout, and all
six load-induced timeouts passed in isolation at 27–65s — inside even the single 90s budget. The gate's
own `TIMEOUT_RETRY_MULTIPLIER=2` absorbs them, so no push was ever actually blocked by this. Safety and
budgeting have opposite fixes, and only the budgeting one is real; the measurement now lives in fix (c),
where it is actionable. **The relayed magnitude (38 failures) never reproduced — worst observed was 6 —
and must not be cited.** Full measurement, methodology, and the original relay are retained below for
provenance; nothing here needs separate tracking.

<b>Retained detail (closed — the live claim is fix (c)):</b>

**MEASURED 2026-08-12** (session `e4ed7e05`, HEAD `1706bc2`, working tree carrying 115 uncommitted
changes of which 2 are under `hooks/` — `claim_work.py` and `test-claim-work-lib.py`, the PR #52 WIP.
Both conditions ran against the **identical** tree, so the delta is attributable to load, not to code.)

Harness: replicated `git-prepush-hook-tests-gate.py`'s own contract — same three `TEST_ROOTS`, same
two-pattern glob, `python <file>` per subprocess with exit 0 = pass, `PER_TEST_TIMEOUT_SECONDS=90`,
`MAX_PARALLEL_TESTS=8`, `CANNOT RUN:` treated as ENV-SKIP. The **first-run** result was recorded raw,
with the gate's timeout-retry deliberately not implemented, so the retry could be evaluated separately.
Load was generated by a second concurrent copy of the whole suite — what a fleet burst actually looks
like — on a 16-core machine.

| Condition | Files | PASS | TIMEOUT | **Assertion FAIL** | Wall |
|---|---|---|---|---|---|
| Ambient (other sessions live, no injected load) | 75 | 73 | 2 | **0** | 135.2s |
| Under a concurrent second suite copy | 75 | 69 | 6 | **0** | 200.7s |

Timed out under load: `test-commit-provenance-guard` · `test-config-write-guard` ·
`test-claim-work-lib` · `test-git-prepush-scan` · `test-memory-orphan-link-guard` ·
`test-eos-review-gate`. All six then **passed in isolation at 27–65s** — every one inside even the
*single* 90s budget, never mind the doubled one.

**The relayed diagnosis "not concurrency-safe" is not what is happening.** Across both conditions the
suite produced **zero assertion failures**. No test computed a wrong answer, saw another test's state,
or raced on a shared file. Every single non-pass was `rc=124`, a wall-clock timeout: subprocess-heavy
files run 1.4–3× slower under contention and blow a *flat* per-file budget. That is a **budgeting**
defect, not a **safety** defect, and the two have opposite fixes — "make the tests concurrency-safe"
would be work against a problem that does not exist.

**Denominator corroborates the relay's provenance:** discovery finds **75** files (44 `hooks/tests` +
31 across the `maintenance` roots); the relayed line said 76. Close enough to confirm they were looking
at this suite. **The relayed magnitude did NOT reproduce:** they reported 38 failures, I measured 6 at
worst. Either their real fleet load far exceeded a 2-copy proxy, or the figure is unreliable — note
this item's own timing evidence above records "`hook-tests-gate` 38/39", a *pass* count from a partial
run, which the 38 may be a garbled recollection of. **The 38 figure remains unreproduced; do not cite it.**

**The gate already absorbs this, by design and in fact.** `TIMEOUT_RETRY_MULTIPLIER=2` grants each
timed-out file exactly one rerun at 180s, and the gate's own docstring documents this exact phenomenon
found 2026-07-26 (`test-eos-review-gate.py` blowing 90s during a push with three other live sessions,
then passing all 48 of its tests on isolated rerun). **All six of my timeouts recovered on rerun**, so
a real push in the loaded condition would NOT have been blocked — the gate would have disclosed them as
"timeout-retry … not blocking" and let it through. Defect 4 as originally relayed is therefore **already
mitigated**.

**VERDICT — what actually survives, and it is not what was filed.** Two things the reproduction found
that the mitigation does not cover:

1. **Two files timed out with no injected load at all** — `test-eos-review-gate` and
   `test-memory-orphan-link-guard`, at merely ambient session activity. The retry catches them, but the
   flat 90s budget is now marginal at *baseline*, not just under bursts. Every file added to the suite
   makes this worse.
2. **The suite outruns the push timeout.** It took **135s ambient / 200s under load**, against the
   **120s client-side timeout** this item already documents in its own timing evidence (two of four
   observed pushes exceeded it). The timeout-retry makes this *worse*, not better: a retried file adds
   up to another 180s to a run that already exceeds the client budget.

Both are **candidate fix (c)** in the "Candidate fix (NOT applied)" block below — "if the full
`hooks/tests` suite is genuinely intended to run on every push, budget it against the client timeout" —
which was written before this evidence existed and is now measured rather than suspected. **Recommend
folding Defect 4 into fix (c) and closing it as a separate line item**, since "the suite is unsafe under
concurrency" is disproven and "the suite is too slow for its budget" is already tracked there.

<details><summary>Original unverified relay, retained for provenance</summary>

**⚠️ UNVERIFIED RELAY — NOT independently reproduced** *(superseded 2026-08-12 by the measurement above)*

**Provenance, stated plainly because it is unusual.** This was reported by session `e047be2a`, which
claimed `open-items-tracker` on 2026-08-11 ~17:15 ET specifically to add it here, and then ended
without writing it. The entire surviving record is the one-line description that session supplied to
`claim_work.py`, captured verbatim from the collision warning:

> "Add defect 4 (hook-test suite is not concurrency-safe) to OI-111. Evidence: same commit 38/76 fail
> under fleet load vs 75/76 clean on retry."

**Why the record is only one line — my error, recorded so the gap is not mistaken for theirs.** The
`ora-weekly-hygiene` run of 2026-08-10 (session `e4ed7e05`) claimed the same slug while `e047be2a` held
it live. The then-current `claim_work.py` **clobbered** the existing claim and only warned afterwards,
destroying their broadcast; that build had no `restore` subcommand and no claim history, so it could not
be undone, and their internal id could not be resolved to a host session id for a handoff message. Their
work was consequently never filed by them. **This is exactly the failure mode that PR #52 fixed** —
`claim` now refuses on collision (exit 3, writes nothing), `--force`/`--steal` preserves the displaced
claim, and `restore <slug>` puts it back. Had that shipped a day earlier this defect would carry their
own evidence instead of a relayed line.

**What is and is not established.** The claim is that the same commit yields **38 of 76 failures under
fleet load** but **75 of 76 clean on retry** — i.e. roughly half the suite fails non-deterministically
when other sessions are running, and passes in isolation. I did **not** observe either run. No transcript
survives (`search_session_transcripts` for the finding returns nothing). Treat the two ratios as reported
figures, not measurements, until reproduced.

**Why it is worth carrying anyway.** It is the same subsystem as Defects 1–3: if the suite the pre-push
gate runs is itself load-flaky, then a gate failure is not evidence of a real defect, and the natural
response — retry until green — is indistinguishable from suppressing a true failure. That interacts
directly with Defect 2 (a push that succeeded while reporting failure) and with the timing evidence
above, where two of four observed pushes exceeded the 120s client timeout. A flaky suite and a slow one
have the same symptom and opposite fixes.

**Possible gap:** `e047be2a` may have held further working notes, including a defect 3 distinct from the
numbering above. Nothing beyond the quoted line was recoverable.

**Next step to promote this from relay to finding:** run `hooks/tests` concurrently against a loaded
fleet and against an idle machine on the same commit, and compare pass counts. If the split reproduces,
replace this block with the observed evidence and drop the UNVERIFIED marker; if it does not, close
Defect 4 explicitly rather than leaving it to decay.

*This step was carried out 2026-08-12 — see the measurement at the top of Defect 4. Outcome: the
degradation reproduced, the "not concurrency-safe" characterization did not, and the 38-failure
magnitude did not.*

</details>

**Auto-check:** none. Re-measure with the harness described above if the suite grows materially or
`PER_TEST_TIMEOUT_SECONDS` / `MAX_PARALLEL_TESTS` change.

**Counter-evidence — the gate works, and caught a genuine defect in this very item.** The push filing
OI-111 was correctly BLOCKED with `orphaned_sections: ['OI-111']`: the entry had a `### OI-111` detail
section but no row in the Open table, which the tracker convention requires. That is a real
convention violation the gate caught before it reached `main`. Any fix to defects 1 and 3 must preserve
this behaviour. Post-fix the suite reports 74 pass / 0 fail / 1 env-skip.

**Timing observed:** push-with-content → doctrine-integrity-probe + `hook-tests-gate` 73/74, completed
but slow · second push → 38/39, killed at 120s · delete push (2 branches) → killed at 120s, 1 of 2
applied · this item's clean push → 74/75, completed. PR #46 added 141 lines of scratch-worktree sweeping
at gate start, which adds to rather than relieves the startup cost.

**Candidate fix (NOT applied):** (a) early-exit on a delete-only refspec; (b) mark or suppress
test-sourced stderr so it cannot read as a live check failure; (c) budget the suite against the client
timeout — it is at ~75 assertions and growing.
**Closing condition:** a delete push completes inside the client timeout with output captured showing
either an early exit or a justified full run, and gate output distinguishes test-sourced stderr from a
live check failure. Defect 2 needs no action — it is retracted. Defect 4 needs no action — it is closed.
**Related:** [OI-112](open-items-tracker.md#OI-112) covers separate defects in the same gate (branch
staleness), the two are independent and neither blocks the other.

### OI-112
**Status:** OPEN
**Opened:** 2026-08-09
**Source:** residual from landing [PR #46](https://github.com/ZeOoba/ora-claude-config/pull/46) (`a880b39`, merged) during the `ora-health-guard` session `1ce540e5`
**Severity:** LOW — cosmetic accumulation only, self-limiting, and Gabriel decided in-turn on 2026-08-09 to leave it rather than switch branches under other sessions' work. Filed so it is not rediscovered from scratch.

**The item:** the shared `~/.claude` checkout is parked on `feat/model-canary-probe-step25`, which was merged long ago as [PR #38](https://github.com/ZeOoba/ora-claude-config/pull/38). `a880b39` is therefore NOT reachable from the checked-out branch, so the LIVE `hooks/git-prepush-doctrine-gate.py` does not contain the scratch-worktree janitor that PR #46 merged to `main`.

**Consequence, and why it is only partial:** the pre-push shim runs `python "$(git rev-parse --show-toplevel)"/hooks/git-prepush-doctrine-gate.py`, so WHICH copy of the gate executes depends on where the push originates. A push from a worktree cut off current `main` gets the fixed gate and sweeps correctly (verified live: an aged decoy planted in `%TEMP%` was swept during the PR #46 push itself). A push from the shared checkout runs the OLD gate and keeps leaking `ora-doctrine-push-*` worktrees — the exact leak PR #46 exists to stop. 9 such worktrees had accumulated by 2026-08-09, oldest from 08-06.

**Why it was not simply fixed:** the checkout carried 93 uncommitted files belonging to other concurrent sessions. `CLAUDE.md`'s shared-checkout rule forbids `checkout`/`reset`/`rebase`/`stash` on a contaminated tree, and a branch switch would have carried that WIP onto `main`. A Gabriel-directed HEAD move was claimed under the `repo-housekeeping` slug by session `633f8f1a` (host `local_112718cc`) earlier the same day, but that session released the claim and exited without performing it — so this is NOT waiting on anyone.

**NOT an item — do not re-file (verified 2026-08-09):** the four commits sitting on that branch and absent from `main` by SHA (`369c62b`, `b9cabdb`, `f2d04f1`, `fb1edfa`) are NOT stranded work. `git cherry -v origin/main HEAD` marks all four `-` (patch-equivalent already upstream); three match a `main` commit by message (`a1fde27`, `fd767bf`, `1bfd552`) and the fourth landed as the [PR #42](https://github.com/ZeOoba/ora-claude-config/pull/42) squash `2ece228`. They were genuinely unpushed and off-`main` mid-session; both conditions resolved before this row was written. This paragraph exists because the loose end was nearly filed as a lost-work item on stale observation.

**Closing condition:** the shared checkout is on a branch containing `a880b39`, AND `grep -c "def sweep_stale_push_worktrees" ~/.claude/hooks/git-prepush-doctrine-gate.py` returns 1 against the LIVE file (not `origin/main`). A merged PR is not a live deploy — verify the served file, per `CLAUDE.md`'s release rule.
**Related:** [OI-111](open-items-tracker.md#OI-111) covers separate defects in the same gate (delete-refspec runtime, false `failed to push some refs`); the two are independent and neither blocks the other.
**Auto-check:** none.

### OI-113

**Status:** OPEN

**Opened** 2026-08-10 · **Source** `ora-weekly-hygiene` Block M (unsigned draft-to-signature nudge)

**Document:** outbound lease document for **392 Morrison Rd**, sent from `ggoldberg@oxfordra.net`
2026-08-03 19:11 ET in thread *"Re: Morrison Rd"*, with attachment. Body: "Updated Security Deposit.
This one should be good."

**Days idle:** 5 business days as of 2026-08-10 (Aug 3 Mon → Aug 10 Mon). This is exactly the
Gabriel-set threshold, so it is the first item to trip it this run.

**Cross-check performed (Block M step 2), and what it found:**
- Notion Tenant DB `Notes` — no sent/executed/signed mention for a Morrison Rd tenant post-dating 08-03.
- HubSpot deal-stage advance — not checked; this is a *lease* document, not a pipeline deal, so no
  HubSpot stage exists to advance. Stated rather than silently skipped.
- DocuSign / Adobe Sign completion marker — none in the thread or naming the counterparty within the
  45-day mailbox window.
- No outbound or inbound follow-up message in the thread after 2026-08-03.

**Why it stays flagged:** no corroborating signal exists in either direction. Per Block M step 3 the
candidate stays flagged rather than being assumed to have moved — silence is not evidence of progress.

**Not flagged, for contrast (all at 4 business days, one day short of the threshold — re-check next run):**
- *9050 Red Branch Unit C : Amendment to add Cricket DC LLC* — this block's founding case. Cleared, not
  flagged: Gabriel sent the **revised lease as an attachment** on 2026-08-04 17:43 ET for review and
  signature, which satisfies the "outbound document delivered" test. It is now awaiting counterparty
  signature, which is a different failure mode than the one this block detects.
- *Re: Lease Renewal 29000 Info Lane Unit 101* — outbound with attachment 2026-08-04, importance HIGH,
  "Following up on this. Please confirm receipt." No reply observed.
- *Re: Renewal* (`davidfranklinperry@gmail.com`) — inbound thread, Gabriel replied 2026-08-11 "write up a
  simple Addendum." Promised document not yet drafted; 0 business days idle.

**Dropped:** *754 Old State PSA* — fully executed PSA received from KMK Law 2026-08-11. Completion marker
present, candidate correctly dropped.

**Coverage caveat (Block M step 4):** the scan reached the mailbox (45-day thread-grouped keyword sweep),
`02_Outputs\` and `05_Loose_Outputs\` (3 hits, all >30d or non-deal — a skill package and a 2026-04
style-guide amendment). Still NOT caught by any arm: a request made by phone or in person, one drafted in
a third-party portal that emits no mail, or one worded without any of the matched keywords.

**Auto-check:** `ora-weekly-hygiene` Block M, weekly.


### OI-130
**Status:** OPEN — trust-calibration. Two routes to the same fail-open signal: path A (rate-limited) is sporadic
and had no unreviewed merge; path B (non-default base branch) is deterministic and DID merge a PR with zero
CodeRabbit review. Fix is a judgement call between the four options below; options 1 and 2 are the only ones
covering both paths.
**Opened:** 2026-08-12 (path A) · path B folded in 2026-08-12
**Source:** path A — session 08df9f95 (an unattended `ora-doctrine-integrity-guard` run taken over interactively),
observed across six PRs merged into `ora-claude-config` that day. Path B — session 663673c8, folded in the same
day from PR #70 in the same repo.
**Description:** CodeRabbit's PR status check reports a **passing** conclusion when it has **not reviewed the diff
at all**. The check and the "I didn't look" notice live in different places: `gh pr checks` shows `pass`, while the
reason sits only in a PR comment body. **Two independent routes reach this same end state** — one sporadic and
load-driven (A), one deterministic and structural (B). A fix aimed at only one of them leaves the other open.

---

#### Path A — rate-limited (sporadic, load-driven)

**Measured, not impression (2026-08-12):**

| PR | `gh pr checks` | detail | "Review limit reached" comment |
|---|---|---|---|
| #45 | pass | Review rate limited | yes |
| #47 | pass | Review completed | — (genuinely reviewed) |
| #49 | pass | Review rate limited | yes |
| #51 | pass | Review rate limited | yes |
| #55 | pass | Review rate limited | yes |
| #65 | pass | Review rate limited | yes |

**5 of 6.** The comment reads: *"you've reached your PR review limit, so we couldn't start this review… Next
review available in: 13 minutes"* — the plan's included-review quota, which a busy day exhausts. This repo saw
~10 PRs from multiple concurrent sessions that day.

---

#### Path B — base branch is not the repository default (deterministic, structural)

CodeRabbit **declines to review any PR whose base is not the repo's default branch**, posts only a notice, and
still reports a **passing** check. Verified via the GitHub API on 2026-08-12 (not inferred) against
`ZeOoba/ora-claude-config` **PR #70**, base `feat/model-canary-probe-step25`, head
`task/snapshot-refresh-rationale-correction`:

| probe | result |
|---|---|
| `gh pr checks 70` | `CodeRabbit  pass` — detail: *"Review skipped: reviews are disabled for this base branch"* |
| `gh api .../pulls/70/comments -q 'length'` | `0` (no inline review comments) |
| `gh api .../pulls/70/reviews -q 'length'` | `0` (no review objects) |
| `gh pr view 70 --json reviewDecision` | empty |
| issue-level bot comments | exactly one — and it **is** the skip notice |

The comment body reads: *"Review skipped — Auto reviews are disabled on base/target branches other than the
default branch."* followed by *"Please check the settings in the CodeRabbit UI or the `.coderabbit.yaml` file in
this repository."* There is no `.coderabbit.yaml` at the repo root, so this is the CodeRabbit-UI default, not a
committed choice.

**PR #70 then MERGED in that exact state** — 2026-08-12T22:23:07Z, merge commit `6c2685c`, into
`feat/model-canary-probe-step25`. Re-verified post-merge: still 0 reviews, still 0 review comments. So this is not
a hypothetical; a change landed on 2026-08-12 carrying a green CodeRabbit check for a review that never ran.

**Why path B deserves its own entry rather than a footnote on A:**

1. **Deterministic, not sporadic.** Path A depends on that day's quota burn — it may or may not fire on any given
   PR. Path B fires on **every** non-default-base PR, **every time**. That also makes it *cheaply* guardable in a
   way A is not: assert the base ref before merge, or assert that a real review body exists rather than merely
   that a bot comment is present.
2. **Structurally induced by ORA practice, not an accident.** PR #70 targeted a feature branch *deliberately*: it
   edits a section of `scheduled-tasks/ora-cc-snapshot-refresh/SKILL.md` that does not exist on `main` (it arrived
   in commit `1706bc2` on that branch). A PR into `main` would have carried **17 commits, 16 of them unrelated
   work from other sessions** (verified: `git rev-list --count origin/main..origin/task/snapshot-refresh-rationale-correction`
   → 17). Any change that depends on unmerged work hits this — which is precisely the situation OI-131's config-repo
   branch divergence keeps producing. Expect path B to recur until that divergence is resolved.

**Why it matters:** a green check that means "nobody looked" is indistinguishable, at a glance, from one that
means "looked and found nothing". Anyone — human or agent — treating that check as the review gate is trusting a
signal that fails OPEN. Compare two failure modes closed the same day: `scrub-before-optin.py` reporting
`SCRUB CLEAN` when it could not read the file, and the pre-push gate reclassifying a real failure as a
non-blocking ENV-SKIP (OI-119). Same shape, three different systems.

**Not a live breach — path A.** Nothing merged on path A that day was actually unreviewed: independent LOCAL
reviews ran on every substantive change and earned their keep — a **Critical** on #47 (an unscannable snapshot
recorded as CLEAN) and an **Important** on #55 (a real failure reclassified non-blocking and invisible).
CodeRabbit never caught either; it just looked like a second gate.

**Path B, same question, NOT verified.** PR #70 merged with zero CodeRabbit review. Whether an independent LOCAL
review ran on it was not checked here, so path B is recorded as an unverified-coverage case, not as a clean one.
Do not read path A's "nothing landed unreviewed" onto it.

**Options (Gabriel's call):**
1. **Advisory-only, documented** — accept CodeRabbit as best-effort and write down that its check conclusion is
   NOT evidence of review. Cheapest; changes nothing mechanical. Covers **both** paths.
2. **Gate on evidence of review, not on the check conclusion** — a small pre-merge check. Note the trap: the
   obvious version greps the comment for "Review limit reached" and would **silently miss path B**, whose notice
   says "Auto reviews are disabled on base/target branches other than the default branch". Gate on the *positive*
   signal instead — `pulls/N/reviews` non-empty, or a review body that actually exists — so any future
   skip-with-a-different-string is caught too. Covers both paths; one moving part to maintain.
3. **Raise the plan limit** — usage-based reviews are offered in the same comment ($0.25/file past the quota).
   Fixes **path A only**; a non-default-base PR stays unreviewed at any quota. Only worth it if CodeRabbit is
   meant to be load-bearing, which today's evidence says it is not.
4. **Enable auto-review on non-default base branches** (path B only) — the skip notice points at the CodeRabbit UI
   setting or a `.coderabbit.yaml`, neither of which this repo currently sets. Cheap and targeted, but it raises
   review volume and therefore feeds path A. Do not adopt 4 without 1 or 2.

**Cheapest partial regardless of choice:** assert the base ref. A PR whose base is not the default branch is
*known* to be unreviewed by CodeRabbit — that requires no comment parsing at all.

**Caveat on scope:** path A measured on one repo (`ora-claude-config`) on one day; path B on one PR in that same
repo. Whether other repos' CodeRabbit integrations behave the same way was NOT checked — though path B's cause is
a documented CodeRabbit setting rather than a load condition, so it should reproduce anywhere the setting is left
at its default.
**Auto-check:** none.

### OI-116
**Status:** CLOSED 2026-09-07
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

### OI-117
**Status:** OPEN
**Opened:** 2026-08-11
**Source:** landing [PR #52](https://github.com/ZeOoba/ora-claude-config/pull/52) into the live checkout,
2026-08-11
**Severity:** MEDIUM — it blocks the normal landing path for every session, not just this one.
**Description:** The live `~/.claude` checkout has drifted into a state where `origin/main` **cannot be
merged**. At the time of filing it sat on branch `feat/model-canary-probe-step25`, 4 ahead / 29 behind
`origin/main`, with **96+ uncommitted files** attributable to at least six concurrent sessions
(`08df9f95`, `0c822226`, `3a782c7b` and 3 more, per `shared-checkout-guard`'s own warning). Nine of the
29 incoming commits' files have uncommitted local changes — including `open-items-tracker.md`, live-claimed
by another session at the time — so `git merge origin/main` would be refused by git rather than
completing. The doctrinal remedies are all unavailable: `stash`/`checkout`/`reset`/`rebase` on a
contaminated tree are forbidden, and committing other sessions' WIP is not this session's to do.

**Consequence, observed:** PR #52 merged to `main` as `a6d346d` but was **not live**, and getting it live
required a surgical `git checkout origin/main -- <3 files>` (both hook files verified clean in the live
tree first, backed up, `allow-config-write` token minted against Gabriel's in-turn instruction and revoked
immediately after). That workaround leaves those files **modified against the live branch's HEAD** until
that branch merges `main`, with two knock-on effects: a `git commit -a` by any session on that branch
would sweep in changes that are not theirs (benign — byte-identical to `origin/main` — but confusing),
and `eos-review-gate` will see a modified `hooks/**` file and may demand a review artifact from a session
that did not write it.

**This is the general case, not a one-off:** any future `hooks/**` change lands the same way and hits the
same wall. The 4 unpushed commits on the live branch (`d0b41b6`, `0e6a613`, `3105dcd`, `e5dbc86` — memory
appends and fleet-heartbeat refreshes) are themselves ordinary work that never got published.

**Candidate fixes (NOT applied):** (a) a supervised reconciliation pass that commits or lands the 96 dirty
files by owning session and then merges `main`, restoring the live checkout to a mergeable state;
(b) a scheduled drift probe that alarms when the live checkout exceeds a dirty-file or behind-count
threshold, so this is caught at 10 files rather than 96; (c) doctrine change — treat the live checkout as
read-only and require ALL work to happen in worktrees, which is already the rule for repos but is not
enforced for `~/.claude` itself.
**Closing condition:** the live checkout merges `origin/main` cleanly, the three surgically-synced files
show clean against HEAD, and the 4 unpushed commits are either published or deliberately abandoned.
**Auto-check:** `git -C ~/.claude status --porcelain | wc -l` and `git -C ~/.claude rev-list --count
HEAD..origin/main` — both should be small; at filing they were 99 and 29.


### OI-114
**Status:** OPEN
**Opened:** 2026-08-11
**Source:** [ORA Monthly Portfolio Briefing — August 2026](https://app.notion.com/p/3b96ecd89e598192b55ae297b2c46cad) Risk 1, run 2026-08-11
**Description:** **55 New Plant Court, Owings Mills MD** is a single-tenant asset let entirely to
**Eurosort, Inc., a Delaware Corporation** — 34,534 SF, **\$452,834.88 ARR**, lease end **2027-12-31**.
That is **8.09% of portfolio ARR and 11.91% of portfolio NOI** (\$452,835 of \$3,801,616), and **100% of
that property's income**; property WALT is 1.39 yr against a portfolio WALT of 2.45 yr.

**Why it is invisible to every existing check.** The property is **unencumbered** (Property NOI row 6:
loan balance 0, debt service 0, LTV 0), so it is absent from the maturity schedule, the ≤40% aggregate
LTV test and the ≥1.25× DSCR test alike. Occupancy reads 100% and portfolio WALT reads flat, so neither
the occupancy nor the WALT screen flags it. There is no lender, no covenant and no automated alert
behind it. It was found only by crossing §1–§3 of the monthly briefing; the concentration is the largest
in the portfolio and the only mechanism currently surfacing it is this row.

**Magnitude.** Value is carried as NOI ÷ cap at 6.5%, so a non-renewal writes down **~\$6,966,690 —
12.0% of the \$57,951,345 portfolio value** — and removes 11.9% of NOI in a single event. The asset
currently returns **25.2% cash-on-cash** on \$1,800,000 of invested equity, the highest in the portfolio,
which is precisely why it reads as healthy on every screen.

**Timing compound.** The expiry lands in the portfolio's largest single roll month: **Dec-2027, 59,727 SF
/ \$741,690 ARR / 8 leases**, of which Eurosort alone is **61%**. The 18-month roll overall is 195,256 SF
/ \$2,270,665 / 62 leases = 42.8% of in-place ARR.

**Open questions / next steps.**
- **Blocking, for Gabriel:** does the Eurosort lease carry a **renewal option, ROFR, or termination
  right**? The rent roll records an escalation date and percentage but no option data, and the answer
  determines whether this is a negotiation or a countdown.
- Open renewal discussions **now, at 16 months out**, rather than the customary 9–12. A 34,534 SF
  single-tenant flex user at 25% cash-on-cash justifies trading rent for term; a below-market early
  extension is cheaper than a re-tenanting of the whole building.
- Target a **signed extension or a replacement LOI by Q1-2027**.

**Evidence basis (opening, not closure):** ORA Master Workbook `lastModifiedDateTime` 2026-08-10 —
`Property NOI` row 6 (SF, value, equity, CoC, zero debt) and `Master Tenant Rent Roll` (tenant, ARR,
lease end). Dec-2027 cliff and 18-month roll computed independently from the 142-row roster this run.
Concentration corroborated by Portfolio Metrics Snapshot [3b86ecd8](https://app.notion.com/p/3b86ecd89e5981449434ef0bd0a2aa07)
("Largest tenant — Eurosort, Inc. — \$452,834.88, 8.09%").

### OI-115
**Status:** OPEN
**Opened:** 2026-08-11
**Source:** [ORA Monthly Portfolio Briefing — August 2026](https://app.notion.com/p/3b96ecd89e598192b55ae297b2c46cad) Risk 4, run 2026-08-11;
originating incident [project_insurance_lapse_confirmed_real_2026-07-25.md](project_insurance_lapse_confirmed_real_2026-07-25.md)
**Description:** **Nine properties are uninsured or within 22 days of it, and this is the fourth
consecutive reporting cycle with no movement.**

**Expired — 8 policies, 3+ consecutive ingest runs, escalated 2026-07-13, unchanged since:**
Fairground Village Center PCKG+BCL · ETC POA PCKG+BCL · 1100 Rarig PCKG+BCL · 3883 Livingston PCKG+BCL.

**Renew-Now — 4 policies, closed from 25–29 days to 18–22 days with no movement:**
1900 N Broadway UFX+BCL (expire **2026-08-27**) · 9050 Red Branch PCKG+BCL (expire **2026-08-31**).

**Why this is filed as a compound risk rather than a renewals chore — two couplings:**
- **9050 Red Branch is the property carrying the only balloon maturity inside 18 months** (2028-01-01,
  \$1,322,140 at 4.25%, NorthMarq/Symetra). On the economics that refinance is benign — debt service
  actually *falls* — but a lender discovering a lapsed policy on its own collateral sixteen months
  before maturity converts it into a covenant conversation.
- **1100 Rarig is uninsured** while running the portfolio's **shortest WALT (0.92 yr) and 22.9%
  vacancy** — the asset least able to absorb an uninsured loss.

**Why it needs a human owner, not another alert.** The automated escalation has fired for four cycles
without producing a binder. The detection works; the escalation path is what has failed. This is the
only risk in the August briefing that is fully known, fully quantified and entirely unactioned. It is
not an analytical question — it is **\$57,951,345 of insurable value** behind a paperwork failure.

**Next steps.**
- Treat **9050 Red Branch PCKG+BCL (2026-08-31)** and **1900 N Broadway UFX+BCL (2026-08-27)** as hard
  deadlines this week.
- Put the **8 expired policies on a single broker call** with a **bound-or-explain answer required by
  2026-08-18**.
- **Escalate to Eric** — owner for the binders; Gabriel has already been alerted four times.

**Evidence basis (opening, not closure):** ORA Master Workbook `Insurance Renewals` tab as of
2026-08-10 (24 active policies, \$165,856 premium, 8 expired / 4 Renew-Now / 5 soon / 1 cancelled;
`00_Home` next renewal Aug 27, 2026), and Portfolio Metrics Snapshots
[3b86ecd8](https://app.notion.com/p/3b86ecd89e5981449434ef0bd0a2aa07) (08-10),
[3b16ecd8](https://app.notion.com/p/3b16ecd89e59819790f2c3d2e613115b) (08-03) and
[39c6ecd8](https://app.notion.com/p/39c6ecd89e59819698d8cf25fac246f9) (07-13), which record the same
8-policy set unchanged across all three and the Renew-Now window narrowing without movement.

### OI-120
**Status:** OPEN
**Opened:** 2026-08-11
**Source:** live incident this session while committing the OI-098 tracker work (filing OI-114/115,
back-filling sections, closing class (i))
**Severity:** MEDIUM — shared-state hazard on the live governance checkout. No data was lost in the
observed instance, but only because the collision was noticed before committing.

**Description.** `config-write-guard`'s git detection is built around **verbs that rewrite
working-tree files**. `GIT_MUTATE_RE` (`hooks/lib/tool_call_paths.py:430-432`) is:

```
\bgit\b[^|;&\n]*?\b(checkout|restore|reset|apply|stash|merge|rebase|cherry-pick|clean|revert|pull|switch)\b
```

with the comment *"git verbs that REWRITE working-tree files … Read-only git (log/diff/status/show/
ls-files) is deliberately absent."* **Index-state mutation is not modelled at all.** `add` is absent
because it writes the index, not the working tree; `restore` is present because its *unqualified*
form (`git restore <path>`) does rewrite the working tree — but `git restore --staged <path>` touches
only the index, and gets caught by the same verb.

**Three behaviours, all live-proven in this session (not inferred):**

1. **`git add -- <one memory file>` PASSED.** No block. `git diff --cached` then returned **six**
   files — five belonging to another session that had already staged them, including a 930-line new
   script (`scheduled-tasks/ora-pm-ledger/property_register_snapshot_diff.py`). A plain `git commit`
   at that moment would have swept all five into this session's commit under this session's message.
2. **`git restore --staged -- <that same file>` was BLOCKED** as *"file-rewriting git command
   referencing the live ~/.claude checkout"*, demanding an `allow-config-write` token — for an
   operation whose entire purpose was to *undo* step 1 and hand the index back untouched.
3. **`git commit` is not gated either.** The pathspec form used to escape the situation
   (`git commit -F <msgfile> -- <path>`) ran without challenge and produced commit `6654888`.

**This is a scope gap, not a correctness bug in the guard's own terms.** Within its stated model —
protect the working tree — every one of those three outcomes is consistent. The hazard only appears
once the *shared index* is treated as governance state too, which on a single-writer checkout it
plainly is: `git add` from any session is globally visible and silently changes what every other
session's next `git commit` will capture.

**Why it matters:** it is a **one-way door**. A session can enter a contaminated-index state with no
friction and then cannot leave it without minting a 60-minute, multi-use, whole-governance-layer
write token — which the guard's own message correctly warns is worse than the operation you wanted.
The safe exit exists but is non-obvious.

**Workaround (works today, undocumented — record it wherever the shared-checkout protocol lives):**
`git commit -F <msgfile> -- <path>` performs a *partial* commit from the working tree for the named
paths only, ignoring the index for them and leaving every other staged entry exactly as it was.
Verified this session: the resulting commit contained 1 file, and the other session's 5 staged files
were still staged afterwards.

**Candidate fixes (none applied; `hooks/**` — mandatory adversarial REFUTE + old-vs-new differential
battery before any of these ships):**
- **(a) Narrow, safest:** carve `restore --staged` / `rm --cached` out of the block so the *undo* path
  is always available, on the reasoning that an index-only operation cannot damage the working tree.
  Note this widens what passes, so it needs the differential battery to prove no working-tree form is
  let through with it.
- **(b) Symmetric, larger:** admit index state into the model — gate `add`/`commit` against the live
  checkout the same way, so the door is closed rather than one-way. Higher friction on very common
  operations; would want the pathspec-commit form explicitly allowed.
- **(c) Cheapest, no matcher change:** leave the gate alone and put the pathspec-commit pattern plus
  "never `git add` in the shared checkout, commit by pathspec instead" into the shared-checkout
  protocol in `tech.md`. Removes the trap without touching a fail-closed security gate.

Option (c) is the low-risk first move and does not preclude (a).

**Secondary finding — the matcher fires on prose describing it.** Allocating this very item failed on
the first attempt: `allocate-oi-id.py --note "… un-staging blocks …"` was blocked because the note
text contained a listed verb and the command named the governance root. Re-running with the verb
reworded succeeded. Same shape as [OI-099](#OI-099) (`governor-drift-probe.py` firing on a measured
DSCR ratio written in prose): a text-scanning guard that cannot distinguish *doing* the thing from
*writing about* the thing. Cheap to live with, worth knowing before someone tries to document this
item from a shell command.

**Related, but distinct — do not merge these:**
[[reference_config_write_guard_blocks_eos_review_gate]] covers the bare-substring era (`"del "`
matching inside `"--model "`), which was a matching-precision defect and is fixed. This item is about
*which state the guard models at all*, and is unaffected by that fix.

### OI-125
**Status:** OPEN
**Opened:** 2026-08-12
**Source:** [oxford-command-center PR #268](https://github.com/ZeOoba/oxford-command-center/pull/268) — deferred there deliberately, documented in-file at `server/warehouse/insurance-conditions.ts` (header note + the `coveredIds` comment)
**Severity:** LOW (warning-severity insight; never emails — it only adds noise to the brief digest)
**Description:** `property_insurance_policies.property_id` does not hold property ids. It holds
POLICY-level slugs (`ins-fvc-pckg`, `ins-fvc-bcl`) — 25 rows, 25 distinct values, **0 of 14** snapshot
property ids matching (verified by direct query against `data/warehouse/finance.sqlite`, not inferred).
The `insurance-gap` condition compares that raw column against `prop.id`, so it never matches and
warns that EVERY property has no insurance policy on file. PR #268 fixed the *display* half (slugs no
longer leak into CRITICAL email subjects) and deliberately left this half alone rather than ship an
inert fix.
**Two obvious joins are both wrong — do not re-derive these:** (1) an exact name join on
`snapshot.insurance[].property` → `properties[].name` resolves **0 of 25**; the two fields are
independently maintained and disagree on abbreviation and ZIP (`"55 New Plant Court, Owings Mills MD
21117"` vs `"55 New Plant Ct, Owings Mills MD"`; `"3540 E 5th Ave, Columbus OH 43219"` vs `"3540 E.
5th Ave, Columbus OH"`). Normalizing case/whitespace does not close it — this exact approach was
built, measured at 0 of 25, and reverted inside PR #268. (2) `resolvePropertyId` in
`server/workbook/parse.ts:426` (token/substring match) resolves 24 of 25 but **MIS-ATTRIBUTES 4**,
because the token `"columbus"` matches whichever Columbus property comes first — which would put a
WRONG property name into an alert. That is a fabricated fact in an alert (Hard Invariant 7), strictly
worse than the raw slug.
**How to apply:** add an explicit slug→propertyId mapping (25 policies, 14 properties — small enough
to be *data*, not inference) and key `coveredIds` off it; keep the existing fail-open so an unmapped
slug still alerts. Build the test fixture from the REAL policy/property strings — the reverted attempt
passed its tests only because the fixture set `property.name === insurance.property`, a shape
production never produces. Decide separately whether the column should be renamed/repopulated at the
schema level (a migration touching the ingest path) or left as-is with a mapping layer.
**Related:** [[reference_alert_engine_duplicate_emails_diagnosis_2026-08-11]] holds the full
diagnosis and the send-log forensics.
**Auto-check:** none. Cheap one: assert `coveredIds ∩ snapshot.properties[].id` is non-empty whenever
`property_insurance_policies` has rows — that single assertion would have caught both the original
defect and the inert fix.

### OI-131
**Status:** OPEN
**Opened:** 2026-08-12
**Source:** surfaced while draining the `event_log.md` uncommitted backlog per [[reference_event_log_uncommitted_backlog]]; measured directly against the live `~/.claude` checkout
**Severity:** MEDIUM (no data lost today, but it makes append-only history fragmentable and blocks the primary checkout)
**Description:** the `~/.claude` config repo's primary checkout sits on `feat/model-canary-probe-step25`,
which has **diverged from main — 21 commits ahead, 60 behind** (`git rev-list --count main..HEAD` = 21,
`HEAD..main` = 60). That branch is the **sole carrier of the 2026-08-10 → 08-12 `event_log.md`
history**: `origin/main`'s copy ends at 2026-08-09 and is 4205 lines, while the branch's is 4378. So
the append-only log currently exists in two divergent versions, and the newer one is unmerged.
**Why it bites:** any session that lands an `event_log` entry from a worktree off `origin/main` — the
route `config-write-guard.py` explicitly recommends in its own blocking message — inserts it above an
08-09 entry with three days missing in between, and collides at the top of the file when the branch
merges. This was hit live on 2026-08-12: a worktree was cut off `origin/main` for exactly that purpose
and had to be discarded once the divergence was measured. The entry was committed onto the live branch
instead (`bad4f08`), which required a Gabriel-approved `allow-config-write` override.
**Compounding state:** the same checkout carries **123 uncommitted files spanning 15+ sessions** and
is already flagged as unable to move main — see [[project_primary_checkout_main_move_blocked_2026-08-12]].
The two problems reinforce each other: the checkout can't advance because of the dirty tree, and the
branch can't merge cleanly because it has drifted 60 commits behind while accumulating its own history.
**How to apply:** this belongs to whoever owns `feat/model-canary-probe-step25` — do NOT force-switch
or reset the primary checkout (15+ sessions' WIP). Pick a direction (merge main in, or land the branch),
and expect a top-of-file conflict in `event_log.md` that must be resolved by KEEPING BOTH sides'
entries in date order — an append-only log must never lose a side to "theirs wins". Until it is
resolved, treat `origin/main` as NOT authoritative for `event_log.md`.
**Auto-check:** none available in the probe's vocabulary (it reads scheduled-task registries, not git
refs). A cheap external one: warn when `git rev-list --count origin/main..HEAD` on the config repo
exceeds ~10, or when the two branches' `event_log.md` newest-entry dates differ by more than a day.

### OI-137
**Status:** OPEN
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
### ROOT CAUSE — all three errors, one mechanism (2026-08-12)

**Supersedes BOTH this item's original "leads" AND the earlier Livingston-only section.** Two
superseded claims are recorded here so they are not re-derived: (a) the "warehouse/workbook ≈ 25%"
ratio and the "2 vs 3 `import_batches`" correlation are coincidence, not mechanism (the latter
already had a live counterexample in Northwood); (b) an earlier revision of THIS entry described
Livingston's third delta component as a "$9.00/SF pro-forma assumption" — **that was wrong**, see
the correction below.

**Mechanism: the two spines measure different things.** `Property.noi` (Spine A) =
**the CURRENT rent roll** minus an **estimated or blank** expense figure. Warehouse `oxfordNoi`
(Spine B) = **actual cash accounting for the last COMPLETE calendar year (2025)**. Verified: the
workbook's `grossIncome` is the exact sum of that property's leases in all three cases —
Livingston $98,550, Westerville $159,660, Raytown $258,437.64, each matching its rent roll to the
cent. So the check pits a forward-looking underwriting view against a historical actuals view, and
they diverge exactly where tenancy or ownership changed between 2025 and today.

| Property | Why it diverges |
|---|---|
| **9620 Raytown** | **4 of 9 leases — $125,055, 48.4% of the roll — commence in 2026** (Comfort Care 2026-02-01, 3-E Safety 2026-01-01, McMilian 2026-03-01, Triple Threat 2026-04-15). They did not exist in the 2025 comparison year. Only 2 leases ($39,720.60) ran all of 2025. That alone exceeds the $80,824 delta. |
| **3875-3883 Livingston** | Its **sole** lease (My Autonomous Transportation, $98,550) **starts 2026-07-01** — after the comparison year *and* after the current YTD. Compounded by ownership starting 2025-06-01 (2025 rent $52,500 = exactly 7 × $7,500 vs 2026 $90,000 = 12 × $7,500) and by `expenses = 0`. |
| **3034 Westerville** | Buckeye's Best Transport commenced 2025-01-01 at $13,005/mo, but 2025 collected only **$80,550 ≈ 6.2 months** — consistent with abatement or a ramped start. Compounded by an opex **estimate of $42,000 against $80,703 actual** (nearly 2×). |
| **2203-2207 Northwood (PASSES)** | Ties out at 1.06% by **coincidence of accuracy**, not structural difference: stable 32-tenant roster, and its round $150,000 opex estimate happens to land within 5% of the $142,765 actual. |

**CORRECTION to the earlier revision.** Livingston's $89,911.69 delta still decomposes to the penny
as $43,861.69 (opex absent from the workbook) + $37,500.00 (5 months of the 7-month ownership stub)
+ $8,550.00 — but that last component is NOT a "$9.00/SF pro-forma assumption". It is the incoming
tenant's **contracted** rent ($98,550) exceeding the outgoing tenant's ($90,000). The arithmetic is
unchanged; the interpretation was wrong.

**The expense column is estimated or blank for 13 of 14 properties.** Six are blank/zero (55 New
Plant, 9050 Red Branch, 3540 E 5th, Livingston, 401 Sunburst, 7658 Fishel — the last two ratified
lease-run, so expected); six are round numbers ($42k, $65k, $90k, $150k, $150k, $160k); exactly ONE
is precise (Sepich, $356,385.25). For the four non-lease-run blanks, `Property.noi` is GROSS INCOME,
not NOI. This is wider than the cross-check failure — it feeds `oxfordValue` (Livingston's
$1,314,000 is a 7.5% cap on a figure netting no opex) — and may deserve its own item.

**Neither spine is defective; do not "fix" either.** Warehouse NOI = (revenue + recovery +
other-income) − opex, which reproduces every reported figure exactly ($29,387.04 Westerville,
$27,613.79 Raytown, $372,487.93 Northwood, $8,638.31 Livingston), with correct exclusions (owner
distributions, prepays, security deposits, capex, TI, leasing, debt service). Spine A is a
legitimate forward underwriting view; Spine B is legitimate historical cash accounting. **The
defect is that the cross-check classifies a structural difference as an integrity break**
(`large-drift`, gate-failing).

**How to apply — and what NOT to build.** A previous revision of this entry proposed disqualifying
a calendar year from `latestFullYearPeriod` (`server/warehouse/metrics.ts:63`) when `acqDate` falls
inside it. **That is insufficient**: it fixes Livingston only and leaves Westerville and Raytown
failing, because their cause is lease-level, not ownership-level. The real options are (a) compare
like-for-like — normalise Spine A to the comparison year, or compare a warehouse-side forward
figure — or (b) add a distinct non-error status for structural mismatch (tenancy or ownership
changed since the comparison year), keeping `large-drift` for genuine integrity breaks. Expect this
check to false-positive on **any recently-acquired or recently-leased property**, which for an
acquisitive firm is the set that matters most. This is financial-decision code (it feeds scoring,
benchmarks, capital allocation) so any change needs a REFUTE pass and independent review; the
`expenses` gap is a workbook-side data question for Gabriel, not a code fix. Separately decide
whether `gate:ci` should include this step; if not, the local `gate` failing on `main` needs to be
visible some other way, because today it is silent.
**Auto-check:** none in the probe's vocabulary (git/registry only, not repo scripts). The natural
one is CI: adding `reconcile:noi-crosscheck` to `gate:ci` would make this self-reporting — that is
itself the decision above, not a free action.
### OI-101
**Status:** OPEN
**Opened:** 2026-08-05
**Source:** `linkedin-insight-tag-followup` (spent one-time task), captured before archiving; OI-025 sweep follow-up
**Severity:** LOW
*Section reconstructed 2026-08-11 from this item's table row (OI-098 class (ii)/(iii) back-fill). The row was the only record; no fact here is new except where explicitly dated 2026-08-11.*

**Description:** The LinkedIn Insight Tag Partner ID for oxfordra.net analytics is still a
placeholder. `website-canonical/sell-your-building.html` line 930 carries
`window._linkedin_partner_id='XXXXXXX';`, and the id is referenced again two lines down at 932
(`window._linkedin_data_partner_ids.push(...)`). The GA4 half of the same instrumentation swap is
DONE — real Measurement ID `G-YDSX0RW5HC` live across 16 other files, committed locally on `main`
(`df2bc2a`), not pushed.

**Blocker:** LinkedIn Campaign Manager (account id `547184587`, "Oxford Realty Advisors, LLC") was
gated behind a mandatory 2FA-upgrade modal with no dismiss option as of 2026-07-16. Gabriel completed
2FA setup that day but the gate was still showing immediately after — most likely propagation delay on
LinkedIn's end. **Whether it has since cleared is unknown and untested.**

**The originating task's own file target list is STALE.** It named 16 files (404, about,
application-received, available-space, contact, for-brokers, index, markets/columbus-oh, markets/index,
markets/maryland, portfolio, privacy, tenant-application, tenant-resources, terms, track-record);
verified 2026-08-05 that all 16 are clean and that `sell-your-building.html` — which was *not* on the
list — is the only tracked source file still carrying the placeholder.

**Re-verified 2026-08-11 (this back-fill).** `sell-your-building.html:930` still carries the
placeholder, so the item is correctly still OPEN and the line number is exact.

**New observation, 2026-08-11 — not part of the original item, needs a decision.** The same
placeholder also survives in **ten files under `website-canonical/.worktree-preview-deploy/`**
(404, about, available-space, contact, for-brokers, portfolio, privacy, tenant-resources, terms,
track-record). That is a **stale preview-deploy worktree**, not the main working tree, so OI-101's
"only tracked source file" claim remains accurate as written. But a preview deployed from that
worktree would ship placeholder Insight Tags on ten pages. Refresh or remove the worktree, or confirm
it is never the deploy source. Filed here rather than as a new id because it is the same defect and
would otherwise be rediscovered from scratch.

**Next step:** ask Gabriel whether Campaign Manager loads past the 2FA gate now; if yes, retrieve the
Partner ID (Campaign Manager > Account Assets > Insight Tag) and replace both occurrences in
`sell-your-building.html` only. **Commit locally; do NOT push** — Hard Invariant 2 requires per-deploy
confirmation for oxfordra.net.

**Provenance:** source task archived 2026-08-05 to
`Claude_Workspace\00_Governance\Scheduled\_archive_2026-08-05_oi025-sweep\linkedin-insight-tag-followup\`
— this item is now the sole record of the blocker and the account id.

### OI-102
**Status:** OPEN
**Opened:** 2026-08-05
**Source:** Session-end optimization candidates, 2026-08-05
**Severity:** LOW (developer-experience; no correctness impact)
*Section reconstructed 2026-08-11 from this item's table row (OI-098 class (ii)/(iii) back-fill). The row was the only record; no fact here is new except where explicitly dated 2026-08-11.*

**Description:** The shared-checkout hygiene warning fires on **every single write** into a dirty
`.claude` checkout, but only ever reports the growing dirty-file **count** — never which condition is
actually blocking (for example one red test suite, or a contested claim).

**Why it matters:** a number that only ever grows carries no signal about what to do next, so the
warning trains readers to skip it. A warning that named the specific blocker would be actionable;
this one is noise proportional to how long the checkout has been dirty.

**Candidate fix:** report the blocking condition (failing suite name, contested claim slug, etc.)
instead of, or alongside, the file count.

### OI-103
**Status:** OPEN
**Opened:** 2026-08-05
**Source:** Session-end optimization candidates, 2026-08-05
**Severity:** LOW
*Section reconstructed 2026-08-11 from this item's table row (OI-098 class (ii)/(iii) back-fill). The row was the only record; no fact here is new except where explicitly dated 2026-08-11.*

**Description:** `skillOverrides` was found **silently inert** — the second config key discovered to
have no effect, after the v1.8 drift-check prose-comparison finding. **No mechanism in this repo
verifies that a `settings.json` key actually takes effect once set**, so inertness is discovered ad
hoc, per session, by whoever happens to notice the setting did nothing.

**Candidate fix:** a standing audit question or probe enumerating which `settings.json` keys have
never been mechanically confirmed live, rather than rediscovering inertness one key at a time.

**Related:** [[reference_skilloverrides_ignored_for_plugin_skills]] records the specific mechanism for
`skillOverrides` (any key containing `:` is inert by construction). This item is the **general**
gap — no verification path for config keys as a class — and is not closed by that finding.

### OI-104
**Status:** OPEN
**Opened:** 2026-08-05
**Source:** Session-end optimization candidates, 2026-08-05
**Severity:** LOW
*Section reconstructed 2026-08-11 from this item's table row (OI-098 class (ii)/(iii) back-fill). The row was the only record; no fact here is new except where explicitly dated 2026-08-11.*

**Description:** The plugin-vs-user skill-source distinction was derived by **disassembling the CLI
binary** — a one-off, expensive investigation that produced a durable answer but left no reusable
artifact.

**Candidate fix:** if that distinction is needed again it belongs in a reusable probe helper under
`maintenance/`, not re-derived from scratch. The cost of the original investigation is the argument
for capturing it; the risk of leaving it uncaptured is that the next session pays it again.

### OI-105
**Status:** OPEN
**Opened:** 2026-08-05
**Source:** Session-end optimization candidates, 2026-08-05
**Severity:** LOW (process friction; distorts telemetry)
*Section reconstructed 2026-08-11 from this item's table row (OI-098 class (ii)/(iii) back-fill). The row was the only record; no fact here is new except where explicitly dated 2026-08-11.*

**Description:** `eos-plan-gate` fires at its 4-file threshold **even when the touched files were
pre-specified handoff work scoped before the session started**, forcing an override-file write that
then reads in telemetry as a **bypass** rather than as in-scope work.

**Why it matters:** the override is the same signal whether it covers genuinely unplanned sprawl or
work whose scope was fixed in the opening prompt. Every false positive dilutes the one signal the gate
exists to produce.

**Candidate fix:** a carve-out recognising scope fixed before session start (e.g. an explicit file
list named in the opening prompt), so no override is needed for work that was never unplanned.

**Observed again 2026-08-11** during the OI-098 update: the gate fired on a **one-line assertion fix
to a throwaway scratchpad generator** under `AppData\Local\Temp` — not repo code at all — inside a
scoped, user-directed task. An override was written, and it now sits in telemetry as a bypass. Second
recorded instance of exactly the shape this item describes.

### OI-124
**Status:** OPEN
**Opened:** 2026-08-12
**Source:** root-cause trace of the two split table rows repaired in [PR #57](https://github.com/ZeOoba/ora-claude-config/pull/57)
**Severity:** MEDIUM — silent structural corruption of the tracker; no data lost, but the file
misrenders and the defect recurs.

**This closes out the "root cause remains unidentified" note [OI-098](#OI-098) carried through two
separate repairs of the same symptom.**

**What the evidence shows.** `git log -S` on a distinctive fragment of each runaway row returns the
same origin for both: commit **`57d0acf`, 2026-08-05 17:55 ET**, *"docs(tracker): close OI-020, close
OI-025, file OI-101 — isolated via hash-object/update-index"*. The commit message names the method
that caused it.

**Two conditions combined; either alone is survivable.**

1. **The row text was hard-wrapped at ~100 columns.** Measured continuation-line widths for `OI-095`:
   101, 101, 98, 98, 104, 101, 100, 101, 93, 102, 102, 103 (plus one 337-char unwrapped insert and a
   61-char tail). That is the **same wrapping convention this file uses for section prose** — correct
   there, and **fatal for a table row**, because a Markdown table row must occupy exactly one line.
   The error is applying a whole-file prose rule to the one construct that cannot take it.
2. **The content was written as a blob straight into the index** (`git hash-object` +
   `git update-index`), which **bypasses the working tree**. Nothing rendered it, nothing diffed the
   rendered table, no editor ever opened it. The last check that would ordinarily catch a malformed
   row was removed by the very technique used to isolate the change.

**The technique is not the villain.** Blob injection is a sane response to a contaminated shared
checkout — the same hazard [OI-120](#OI-120) describes, where staging into a shared index sweeps up
other sessions' work. The defect is that it silently drops the render/review step, so a
mechanically-generated malformation lands unseen.

**Impact.** Introduced 2026-08-05, repaired 2026-08-11 on a branch and 2026-08-12 on `main`: **live
for 6 days across 7 subsequent commits to the same file** (`052e59e`, `5ad48a9`, `48f884b`, `a65d3e6`,
`7e14825`, `36e8030`, `f2d04f1`), none of which noticed. An unterminated row followed by a prose block
**terminates the table**, so every row after the break — including OI-098 itself — rendered outside it.

**Distinct from the other mechanism — do not conflate them.** OI-098's history records an earlier
repair of a *different* cause in this same region: **a blank line inside the table**, which pushed
`OI-095`/`096`/`097` outside it. Same symptom (table ends early), different mechanism (blank-line
terminator vs. wrapped row). A fix for one does not cover the other, which is exactly why the symptom
came back and read as unexplained.

**Why nothing detects it.** A row-vs-section audit sees `OI-095` as present and internally consistent,
because the **row text survives the break intact** — it is only the line structure that is wrong. Every
audit this file has been given keys on ids and fields, none on line termination.

**Candidate fixes (none applied here; this item is the diagnosis).**
- **(a) Cheapest and highest value — a termination check.** Every line matching `^\| \[OI-` must end
  in a `|` that is not backslash-escaped. One line of logic, catches both mechanisms' visible
  symptom, and is **green as of PR #57**. Natural homes: `memory-integrity-probe.py`, or the
  pre-push tracker checks.
- **(b) Never wrap a table row when generating tracker content.** Whatever produced `57d0acf` applied
  a prose wrapper to the whole file. Row lines must be exempt.
- **(c) If blob injection is used to isolate a change, validate the blob before writing it** — render
  or lint the constructed content rather than trusting it, since this path has no other reviewer.

(a) is the one worth doing first: it is independent of who writes the file or how, and it would have
caught this on day one instead of day six.

**Auto-check:** no line matching `^\| \[OI-` may lack a terminating unescaped `|`.

### OI-143
**Status:** OPEN
**Opened:** 2026-08-12
**Source:** surfaced while root-causing [OI-137](#OI-137); split out because it is materially wider than that cross-check
**Severity:** MEDIUM (degrades Spine A's NOI, DSCR and value for a subset of properties; **no governor breach today** — quantified below)
**Description — the primary defect is in code, not data.**
`server/workbook/parse.ts:403` reads the property expense column as
`expenses: num(row(ws, r, 12)) ?? 0`. A **missing or unparseable cell silently becomes a real
`0`**, indistinguishable from a genuine zero. This is exactly the failure mode
[[feedback_verified_null_vs_inferred_null]] names — "a zero that could mean 'couldn't look' is a
FAILURE" — and it means the question "is the workbook cell blank, or did the parser fail to read
it?" **cannot be answered from the snapshot at all, by construction.**
**Observed distribution across the 14 properties:**
- **6 blank/zero:** 55 New Plant, 9050 Red Branch, 3540 E 5th, 3875-3883 Livingston, 401 Sunburst,
  7658 Fishel. Sunburst and Fishel are ratified lease-run (expected). For the other **four**,
  `Property.noi` is **GROSS INCOME, not NOI** — it nets no operating expenses whatsoever.
- **6 round-number estimates:** $42,000 (Westerville), $65,000 (1900 Broadway), $90,000 (1100
  Rarig), $150,000 (Northwood), $150,000 (Raytown), $160,000 (29000 Information Lane).
- **1 precise figure:** Sepich, $356,385.25 — the only property whose expense number looks like an
  actual.

**Where an actual exists to check against, an estimate is materially wrong:** Westerville's
$42,000 against **$80,703** of real 2025 warehouse opex — understated by ~92%.

**DSCR impact — real but NOT a governor breach.** `dscr` is read straight from the workbook
(`parse.ts:409`, column 18), so the parser does not propagate this; however the workbook's own
DSCR is arithmetically consistent with the un-expensed NOI, so it inherits the overstatement:
| Property | Reported DSCR | Warehouse-implied | Margin to 1.25 floor |
|---|---:|---:|---|
| 3540 E. 5th Ave | 1.48 | **1.36** | 0.23 → **0.11** (halved, still above) |
| 9050 Red Branch | 3.66 | 3.76 | improves; no issue |
Neither breaches the ratified 1.25x floor, so **no governor is impaired** — but E 5th is the
portfolio's tightest coverage and its true margin is roughly half what the workbook reports. Do
not restate either figure as a governor finding.

**Also feeds valuation:** `oxfordValue` is derived off this NOI — Livingston's $1,314,000 is a
7.5% cap on a figure that nets no opex at all.

**How to apply:** fix the code defect first, because until it is fixed no one can tell data entry
from parse failure. Make `expenses` nullable and emit a `DataQualityFlag` when the cell is absent,
rather than coalescing to `0` — the house convention already exists and is documented verbatim in
`src/contracts/insurance.ts` ("Never invented — null + a DataQualityFlag, not a guess") for the
identical situation. THEN determine, per property, whether the workbook cell is genuinely blank.
Do **not** backfill estimates into the workbook, and do not "correct" NOI, without Gabriel — the
workbook is the source of record for firm figures, and several of these values may be deliberate.
Note that a nullable `expenses` will change `Property.noi` for four properties, which touches
valuation and scoring — financial-decision code, so it needs a REFUTE pass and independent review.
**Auto-check:** a cheap repo-side assertion: no property may carry `expenses === 0` together with
`grossIncome > 0` unless it is ratified lease-run OR carries an explicit data-quality flag. That
single check turns today's silent coalesce into a visible one.

### OI-202

**Opened:** 2026-08-21 · **Source:** Repo-architecture-review remediation, Code session picking up the handoff brief

**Description:** **MEDIUM.** `ora-routine-pause-resume-08-21` is a model-driven one-time CC/MCP task (natural-language steps run by an agent session, not a deterministic script) whose job was to re-enable 35 recurring tasks paused since 2026-08-17. It fired on schedule (`lastRunAt: 2026-08-21T21:05:54Z`) but `list_scheduled_tasks` showed only the first 2 ids in its own instruction list (`ora-master-workbook-ingest`, `ora-financial-code-integrity-sweep`) had actually been flipped `enabled:true` — the remaining 33 stayed `OFF`. No error was recorded anywhere reachable this session, and its step-6 summary email never sent (`send-log.txt` has no matching entry) — meaning the run stopped somewhere in steps 1-5 with no trace of why, and nothing downstream (fleet-status, the dead-man chain) flagged the partial completion as distinct from a clean one.

**Fix direction:** completed manually this session — the remaining 33 tasks were re-enabled directly via `update_scheduled_task(enabled:true)` (no other fields touched, matching the original task's own instruction to avoid reverting hand-edits made during the pause), verified via `list_scheduled_tasks`, and the step-6 summary email was sent late by hand. Root cause of the stall is NOT diagnosed — no session transcript/log was surfaced by a quick check. If this recurs, a one-time resume task's design should probably write an explicit per-item progress marker (or a exit code / heartbeat file) so a stall is distinguishable from "still running" and catchable by `automation-health-monitor` or the dead-man chain, rather than only visible via a manual `list_scheduled_tasks` diff.

**Related:** discovered while re-verifying §3a of the 2026-08-21 repo-architecture-review handoff brief; not yet linked to any prior OI on model-driven scheduled-task reliability.

**Progress 2026-08-21 (same session) — systematic guard built (WO-5), Gabriel-approved:** this incident is the concrete, live instance of exactly the failure mode WO-5's pause/resume guard exists to catch. Built `~/.claude/maintenance/pause-resume-guard.py` — alarms when a fleet's enabled ratio goes near-zero with an overdue or missing resume task, same detection shape as this item. Registered as native Windows Scheduled Task `ORA Fleet Pause-Resume Guard` (every 6h, off-fleet, survives a full pause by construction). Test-verified against live state: correctly reports no alarm (cc 36/36, lams 26/27 enabled). Does not fix the underlying model-driven-task-stall root cause (still not diagnosed) — this is the detection layer, not a fix to `ora-routine-pause-resume-08-21` itself.

**Progress 2026-08-21 (follow-on session, Gabriel-directed) — general-case marker built, closing the "general case isn't fixed" gap:** built `~/.claude/maintenance/task-progress-marker.py` (`write`/`check`/`clear`) — a multi-step one-time task's own SKILL.md instructions call `write --task-id <id> --step N --of TOTAL` after each step; `find_stalled()` flags any fired one-time task whose marker shows an incomplete step that hasn't updated within a grace window (default 20min). Opt-in and additive — a task with no marker is invisible to the check, never a false alarm, so this does not retrofit existing one-time tasks. Wired into the existing `ORA Fleet Pause-Resume Guard` native task (no new monitor) rather than duplicating it. Documented as step 4d in `register-scheduled-task/SKILL.md` v2.13, required for any new one-time task with 3+ sequential side-effect steps. **Also fixed two live bugs found while wiring this in**, both in `pause-resume-guard.py` as built above: it read a task's id via a `taskId` field (live registry entries use `id`) and parsed `fireAt` as an ISO string (it's epoch-ms) — both silently swallowed by a bare `except Exception`, so `overdue_resume`/`resume_tasks` could never populate; confirmed post-fix against the live registry (`ora-routine-pause-resume-08-21` now correctly resolves as ~84min overdue-but-resumed, no false alarm). Marker alarm path smoke-tested against a synthetic stalled marker on a real task id, then cleaned up (marker file removed, `_markers` state key cleared). Root cause of the ORIGINAL 2-of-35 stall is still not diagnosed — this closes the detection gap, not that root cause.

---

### OI-229
**Status:** OPEN
**Opened:** 2026-09-03
**Source:** `register-scheduled-task` v2.19 step 3b (ora-skills `be1deda`) applied to the live fleet, 2026-09-03; Automation Audit Rev 21 R21-2/R21-4 (every trigger of a money-moving task co-located on the host whose outage was the outage)
**Acceptance:** `ora-pm-daily-crons` carries an `offhost-backup:` frontmatter line naming a LIVE trigger that does not run on this laptop (repo + workflow + cron + live-since date), OR Gabriel rules the late-fee posting out of the money-moving class and the frontmatter is re-declared accordingly.

**Description:** **`ora-pm-daily-crons` posts late fees (delinquency-check) and has no off-host backup trigger — declared `offhost-backup: none — GAP` on 2026-09-03.** ora-pm PR #24 (`monthly-billing-backup.yml`, cron `40 17 1 * *` UTC, still OPEN) covers monthly billing only. During the 2026-08-29→09-01 host outage this task's late-fee posting was silent for four days with nothing off-host to catch it (recovered in the 09-02 catch-up burst: 35 late fees). Gabriel's call: extend the ora-pm GitHub Actions backup to the two daily endpoints (critical-dates-alerts, delinquency-check — both idempotent per the endpoints' own upsert semantics, to be confirmed in the PR), or accept the gap explicitly in the frontmatter. Companion: `ora-pm-monthly-billing` is declared `pending` on PR #24 and flips to a live declaration when that PR merges.

## Closed

Closed items (table + detail sections) moved to `open-items-tracker-history.md` on 2026-09-06 (Automation Audit R22-4) — same `OI-NNN` anchors, now at `open-items-tracker-history.md#OI-NNN`. Never restate a closed item's content back here; point to the history file. Any section appearing below this line belongs to an OPEN item that happened to be filed physically after the old Closed table (or is a pre-existing orphaned section, unresolved to any row) — check its row in the Open table above for status, not its position in this file.


### OI-031
**Status:** OPEN
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

### OI-078
**Status:** OPEN
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
**Auto-check:** none.

### OI-079
**Status:** OPEN
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

### OI-082
**Status:** OPEN
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

### OI-083
**Status:** OPEN
**Opened:** 2026-08-05
**Source:** ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch)
**Severity:** MEDIUM (input validation / cross-tenant integrity)
**Description:** `server/routes/portal-insurance.ts:13-37` destructures the raw JSON body and
inserts it with no Zod schema — the only write route in the repo that does. The admin equivalent
uses `InsuranceInsertSchema` (`server/lib/schemas.ts:139-147`). `storage_path` is written to
`document_path` verbatim with no ownership or prefix check; `policy_type`, `carrier`,
`policy_number`, `coverage_amount` are unvalidated in type and length.
**Impact:** an authenticated tenant can point their COI record at any storage key, including
`<other-tenant-uuid>/coi.pdf`, surfacing another tenant's document under the wrong tenant in the
admin UI (integrity, and a possible cross-tenant read depending on how the admin fetches it).
Unbounded strings land in the DB and in the insurance report. Related but distinct:
[OI-041](#OI-041) catalogued 10 mass-assignment handlers and did not include this file;
[OI-063](#OI-063) touched this file for raw-error hygiene only.
**Candidate fix (NOT applied):** `safeParse` a strict schema (reuse `InsuranceInsertSchema` minus
`tenant_id`) returning 422 on failure, and constrain the path to the caller's own prefix — reject
unless `storage_path` starts with the caller's own folder. Note this interacts with
[OI-071](#OI-071): the correct prefix depends on resolving the `tenants.id` vs `auth.users.id`
question first.
**Auto-check:** none.

### OI-084
**Status:** OPEN
**Opened:** 2026-08-05
**Source:** ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch)
**Severity:** MEDIUM (unvalidated file upload)
**Description:** `src/portal/pages/PortalInsurance.tsx:29-39`. COI uploads go browser -> Supabase
Storage directly, never touching the API, so there is no server-side MIME or magic-byte check, no
size cap, and `upsert: true` with an unsanitized `file.name`. The `accept=".pdf,.jpg,.png"`
attribute at line 156 is the only check and is trivially bypassed. Bucket policies:
`supabase/migrations/0008_storage_rls.sql:6-16`.
**Impact:** any authenticated tenant can store any file type at any size in the `insurance-certs`
bucket (storage-cost abuse; malicious content later downloaded by staff). The repo demonstrates the
correct pattern elsewhere — `server/routes/intake.ts:86-91` does server-side magic-byte and size
validation for lease intake — and has an unused client-side validator at
`src/components/ui/file-drop.ts`.
**Candidate fix (NOT applied):** route COI uploads through the API (server validates magic bytes and
size, then writes to Storage with the service role), or set a bucket-level file-size limit and
allowed-MIME list in the Supabase bucket config plus `upsert: false` and a server-generated object
name.
**Auto-check:** none.

### OI-085
**Status:** OPEN
**Opened:** 2026-08-05
**Source:** ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch)
**Severity:** MEDIUM (tenant-facing AR display correctness)
**Description:** `server/routes/portal.ts:39-60` returns every charge on the tenant's ACTIVE leases;
`src/portal/pages/PortalDashboard.tsx:10-15,57` labels the count "Open Charges";
`src/portal/pages/PortalPayNow.tsx:33-39` does `const openCharges = charges` and makes them all
selectable. There is no charge<->payment link and no paid/open state on `charges` — a schema gap
first noted in the 2026-07-16 audit and still unaddressed. Separately, the balance card
(`server/routes/portal.ts:32-35`) sums `ar_ledger` across ALL the tenant's leases while the charge
list covers only active ones, so the two numbers on the same screen cannot reconcile.
**Impact:** a tenant with 18 months of history sees 36+ "open charges" totalling far more than they
owe, and can select already-settled charges to pay. The server-side cap
(`server/routes/stripe.ts:168`, 422 when `amount_cents > outstandingBalanceCents`) prevents actual
overpayment, so this is a correctness and trust failure rather than a financial loss — but on a
tenant-facing AR display at a firm that has already shipped two balance-display bugs, it is the same
class and deserves the same treatment.
**Candidate fix (NOT applied):** add settlement state to charges (a
`paid_amount NUMERIC(12,2) NOT NULL DEFAULT 0` updated on payment application, or a
`payment_allocations` join table), filter `/api/portal/charges` to `paid_amount < amount`, and scope
the balance query to the same lease set the charge list uses so the two figures reconcile by
construction. Until then, relabel the UI to "Charge history" — the current label asserts something
the data cannot support.
**Auto-check:** none.

### OI-086
**Status:** OPEN
**Opened:** 2026-08-05
**Source:** ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch)
**Severity:** MEDIUM (authentication of an automated money-movement path)
**Description:** `server/middleware/auth.ts:7` compares the Authorization header to
`Bearer <CRON_SECRET>` with a short-circuiting string comparison. The routes behind it include
`POST /api/cron/monthly-billing`, which creates and confirms off-session ACH PaymentIntents for
every autopay-enabled lease (`server/routes/cron.ts:182-196`). The secret is static, shared with an
out-of-repo PowerShell trigger, and has no documented rotation.
**Impact:** the timing side-channel by itself is marginal over the internet through Cloudflare's
edge and would not merit MEDIUM alone. What raises it is the combination — a static, long-lived,
never-rotated shared secret, passed on a PowerShell command line (`scripts/trigger-billing.ps1:14`,
therefore visible in process listings and shell history), acting as the sole factor gating
portfolio-wide automated debits. Anyone who obtains it can trigger billing runs at will. Note
[OI-076](#OI-076) re-registered the Windows Task Scheduler job that carries this secret, so that
command line is live on this machine.
**Candidate fix (NOT applied):** constant-time comparison (length check, then XOR-accumulate over
char codes with no early return), and prefer a mechanism that is not a bearer string on a command
line — Cloudflare Access service tokens or mTLS for the cron origin. Document a rotation cadence
alongside the existing secret notes in `wrangler.toml`.
**Auto-check:** none.

### OI-088
**Status:** OPEN
**Opened:** 2026-08-05
**Source:** ora-appsec-sweep 2026-08-05 (oxford-command-center @ `175e3f9`, security-auditor dispatch)
**Severity:** MEDIUM (schema integrity — security half; math correctness out of scope)
**Description:** `server/warehouse/migrations/001_initial.sql:59-74` (`ledger_entries`), `:44-56`
(`account_mappings`), `009_debt_positions.sql`, `011_lease_events.sql`.
(1) **No uniqueness on `ledger_entries`** — an `AUTOINCREMENT` surrogate PK and one NON-unique index
`idx_ledger_prop_period(property_id, period, is_active)`. An identical
`(import_id, property_id, period, raw_account, amount)` row is insertable twice by a re-run, a
retried transaction, or a partial-failure replay. Every sibling table has a natural key:
`property_tax_assessments` `UNIQUE(property_id, tax_year)`, `insurance_loss_events`
`UNIQUE(property_id, loss_date, cause, gross_incurred)`, `property_insurance_policies`
`UNIQUE(property_id, policy_number, effective_date)`, `debt_positions`
`PRIMARY KEY (id, snapshot_date)`. The money table is the exception.
(2) **Missing FKs** — `ledger_entries.property_id TEXT NOT NULL` has no
`REFERENCES property_master(id)` (unlike `import_batches.property_id`, which does) and `mapping_id`
has no reference to `account_mappings(id)`. `PRAGMA foreign_keys = ON` is set
(`server/warehouse/db.ts:33`), so declared constraints WOULD be enforced — the enforcement is on,
the declarations are absent. Orphan rows against a typo'd or renamed property id are insertable and
vanish silently from every property-scoped aggregate.
(3) **`lease_events` has no uniqueness at all** — a duplicate
`(property_id, suite, event_kind, event_date)` pair double-counts days-vacant velocity.
(4) **Monetary units unprovable from the schema** — every money column is bare `REAL` with no unit
in the name, no comment and no CHECK: `ledger_entries.amount`, `debt_positions.current_balance` /
`original_principal` / `monthly_pmt` / `annual_interest` / `annual_principal`,
`property_insurance_policies.premium_annual` / `coverage_tiv`,
`property_tax_assessments.annual_tax_billed`, `tax_appeals.est_savings_annual` /
`realized_savings_annual`, `insurance_loss_events.gross_incurred` / `paid` / `reserve`. Nothing
distinguishes dollars from cents. (Migrations `020` and `022` do carry good non-negativity CHECKs —
they are the model.) ora-pm's equivalent was [OI-039](#OI-039); this is the occ counterpart.
**Impact:** a duplicated ledger row or an orphaned `property_id` yields a silently wrong balance
feeding AR aging, NOI and capital-allocation display, with no constraint violation to surface it.
The unit ambiguity is a latent 100x defect one importer away.
**Scope note:** security-relevant half only. Adversarial review of the ledger MATH belongs to
`ora-financial-code-integrity-sweep` and was deliberately not duplicated here.
**Candidate fix (NOT applied):** a new forward migration (`001` and `011` are correctly marked
never-modify-after-apply) adding `ux_ledger_natural` on
`(import_id, property_id, period, raw_account, normalized_category)` and `ux_lease_events_natural`
on `(property_id, IFNULL(suite,''), event_kind, event_date)` — de-duping first. SQLite cannot add an
FK without a table rebuild, so either do the 12-step `ALTER` for
`ledger_entries.property_id -> property_master(id)` or add an INSERT-time validation trigger.
Separately, state every money column's unit explicitly (rename to `amount_usd`, or a per-column
comment) and record the convention in `architecture/coding-standards.md` so new migrations inherit
it. `server/warehouse/migrations/**` is architect-owned per `.claude/hooks/architect-owned.json` —
this needs the declared review_needed + architect-ack path.
**Auto-check:** none.

### OI-187
**Status:** OPEN
**Opened:** 2026-08-17 · **Source:** Tax & Settlement systemization sprint — full description lives in the Open table row above; this section exists only to give `#OI-187` a resolvable anchor for inbound links (event_log.md, tax-settlement reference).

---

### OI-188
**Status:** OPEN
**Opened:** 2026-08-17 · **Source:** Tax & Settlement systemization sprint — full description lives in the Open table row above; this section exists only to give `#OI-188` a resolvable anchor for inbound links (event_log.md, tax-settlement reference).

---

### OI-189
**Status:** OPEN
**Opened:** 2026-08-17 · **Source:** Tax & Settlement systemization sprint — full description lives in the Open table row above; this section exists only to give `#OI-189` a resolvable anchor for inbound links (event_log.md, MEMORY.md).

---

### OI-190
**Status:** OPEN
**Opened:** 2026-08-17 · **Source:** Tax & Settlement systemization sprint — full description lives in the Open table row above; this section exists only to give `#OI-190` a resolvable anchor for inbound links (event_log.md, tax-settlement reference).

---

### OI-191
**Status:** OPEN
**Opened:** 2026-08-17 · **Source:** Tax & Settlement systemization sprint — full description lives in the Open table row above; this section exists only to give `#OI-191` a resolvable anchor for inbound links (event_log.md).

---

### OI-192
**Status:** OPEN
**Opened:** 2026-08-17 · **Source:** Tax & Settlement systemization sprint — full description lives in the Open table row above; this section exists only to give `#OI-192` a resolvable anchor for inbound links (event_log.md).

---

### OI-193
**Status:** OPEN
**Opened:** 2026-08-17 · **Source:** Tax & Settlement systemization sprint — full description lives in the Open table row above; this section exists only to give `#OI-193` a resolvable anchor for inbound links (event_log.md, MEMORY.md).

---

### OI-203
**Status:** FIXED (repo) 2026-08-21 — not yet installed on the platform account
**Opened:** 2026-08-21 · **Source:** `dirty-tree-triage` on ora-skills, Gabriel-directed follow-up — full description lives in the Open table row above; this section exists only to give `#OI-203` a resolvable anchor for inbound links (event_log.md).

---

### OI-089
**Status:** OPEN
**Opened:** 2026-08-05
**Source:** ora-appsec-sweep 2026-08-05 (oxford-command-center @ `175e3f9`, security-auditor dispatch)
**Severity:** MEDIUM (unvalidated file write into business storage)
**Description:** `server/index.ts:358-414`. `/api/actions/om-extract` validates only
`file.name.toLowerCase().endsWith('.pdf')` and a 25 MB size cap — there is no `%PDF-` magic-byte
check. The buffer is handed to `pdf-parse` and, on success with a `dealId`, written verbatim into
`DOCUMENTS_DIR/Investment Candidates -- <year>/<deal>/`.
**Impact:** arbitrary non-PDF content can be persisted into the live OneDrive deal-document tree
under a `.pdf` name, and is fed to a parsing surface. Not remotely exploitable — reach is local-only
per [OI-050](#OI-050) — but it is an unvalidated-content write into business storage.
**Candidate fix (NOT applied):** check the first five bytes equal `%PDF-` before parsing or writing;
reject with 415 otherwise. Keep the existing extension and size checks. Preserve the filename
sanitization and `resolve()`-prefix traversal assertion at `:400-405` exactly as they are — both are
correct.
**Auto-check:** none.

### OI-090
**Status:** OPEN
**Opened:** 2026-08-05
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
**Candidate fix (NOT applied):** a small in-process token bucket keyed on route — roughly 10
`/api/ai` starts per minute, 3 concurrent SSE streams, 5 uploads per minute — returning 429. No
external dependency needed, and no KV-provisioning dependency like ora-pm's.
**Auto-check:** none.

### OI-091
**Status:** OPEN
**Opened:** 2026-08-05
**Source:** ora-appsec-sweep 2026-08-05 (oxford-command-center @ `175e3f9`, security-auditor dispatch)
**Severity:** MEDIUM (guardrail bypass / excessive agency, LLM06)
**Description:** `.claude/hooks/file-guard.mjs:144-159`. `findRepoRoot` resolves the repo by walking
up from the target's directory looking for `CLAUDE.md`; if no ancestor has one it `continue`s and the
target is "not policed (fail-open)". The guard also skips any target whose owning root is neither an
ancestor nor a descendant of the session root. Both are deliberate, documented fail-open choices —
but they apply to the HARD-DENY paths (`data/overlay.json`, `data/warehouse/**`,
`.claude/settings.json`, `.claude/hooks/**`), not only to the sentinel-overridable architect-owned
list. A worktree or checkout with no `CLAUDE.md` at its root, or a path form that makes `relative()`
produce a non-matching repo-relative string (junction, extended-length prefix, 8.3 short name, UNC
localhost admin share), leaves those four targets unprotected by this hook. The `permissions.deny`
globs in `.claude/settings.json` that back-stop confidentiality are path-form-sensitive in the same
way.
**Impact:** an agent session operating from an unusual path form can edit its own guardrails or the
live overlay/warehouse. Requires an already-agentic session — not remotely exploitable — which is
why this is MEDIUM rather than HIGH. Distinct from the previously-noted silent-degradation path when
`architect-owned.json` is corrupt (`file-guard.mjs:112-114`); this is the repo-root resolution path.
**Assessed-correct, do NOT "fix":** the sweep also examined `bash-guard.mjs`'s `git push -n` handling
(`:591-607`). Only the long `--no-verify` is denied, deliberately — for `git push`, `-n` means
`--dry-run` and there is no short `-n` for `--no-verify`. That is correct as written; a future
reviewer should not "harden" it into a false positive that blocks legitimate dry-runs.
**Candidate fix (NOT applied):** before the fail-open `continue` at :145, add an unconditional
absolute-path check for the four hard-deny targets that does not depend on repo-root resolution —
normalize with `realpathSync.native()` (which collapses junctions and short names) and deny if the
normalized tail matches `data/overlay.json`, `data/warehouse/`, `.claude/settings*.json` or
`.claude/hooks/`, whichever repo owns it. Keep the existing repo-family scoping for the
sentinel-overridable architect list only.
**Process requirement:** per Invariant 6 and the guard's own self-protection this must be changed
outside a session via a reviewed PR, and per the CLAUDE.md Done bar security-gate hook logic carries
a MANDATORY adversarial REFUTE pass plus the old-vs-new differential battery
(`reference_refute_differential_harness.md`) — judge deltas, not absolutes.
**Auto-check:** none.

### OI-096
**Status:** OPEN
**Opened:** 2026-08-05 (promoted out of OI-094 finding (a) per Gabriel ruling)
**Source:** OI-094 six-range audit (second session's pass; this session's audit missed it)
**Severity:** LOW ($1,365 over-count) but structurally identical to OI-092
**Description:** `485 S Walnut St` rows 45 and 46 both carry the date `2028-09-26`:
```
r45  2028-09-26   D=1,365      E=1,365   F=252,000   <- final regular payment
r46  2028-09-26   D=253,365    E=1,365   F=0         <- payoff (252,000 principal + 1,365 interest)
```
`'External Loans Summary'!H16` sums column `E` over the date predicate and therefore picks up **both**
rows' $1,365 — the same September interest counted twice.
**Impact:** over-states annual interest by $1,365 once `2028-09-26` enters the forward-12-month window,
i.e. from ~Oct 2027. Direction is over-statement, so it is the safe direction against the 1.25x DSCR
floor, and the magnitude is small — hence LOW.
**Why it matters more than $1,365:** it is the same duplicate-date over-count shape as OI-092, and it
is the exact case that made the withdrawn OI-092 detector false-fire "13 payments" dated 2027-09-30.
Any detector that counts ROWS rather than DISTINCT DATES will trip on it.
**RULED 2026-08-05 (Gabriel): fix at SOURCE — correct the schedule rows, not the formula.**
r46's payoff already contains the same September interest that r45 reports, so one of the two must stop
carrying it in column `E`. The formula-side alternative (de-duplicating `H16`'s predicate on date) was
considered and **rejected**: it compensates downstream while leaving the duplicate dates in place, so
every future formula over this sheet inherits the same trap and the detector must special-case it
forever.
**Execution requirements:** verify the payoff total and the remaining-balance column still reconcile
after the edit — do not simply blank a cell.
**RESOLVED 2026-08-05 ~17:00 ET.** Applied and verified directly against the live workbook: r46 is now
a pure balloon (`D`=252,000, `E`=0, `F`=0); r45 retains its interest-only payment (`D`=1,365, `E`=1,365).
`TOTALS` row corrected: `D` 302,505 → 301,140, `E` 50,505 → 49,140. Independently reconciled: 36 monthly
interest-only payments at $1,365 = $49,140 exactly = the corrected `E` total; `301,140 − 49,140 =
252,000` = the balloon principal, matching `Loan Index` row 8's balance. `H16`/`I16` (which split
interest via `E` and principal via `D−E`) are now correct at every `asOf` date, not only outside the
current forward window.
*(Status corrected 2026-08-05 by session `3d9d97cf`, which re-inspected the live workbook expecting to
apply this fix and found it already done by another session — status here was stale by roughly the
length of one workbook-copy round-trip.)*
**Auto-check:** the OI-092 detector retry, if built on distinct dates.

### OI-098
**Status:** OPEN
**Opened:** 2026-08-05
**Source:** full row/detail consistency audit of this file, 2026-08-05
**Severity:** LOW/MEDIUM (tracker hygiene; the OPEN-item-lost class is how items go unworked)
**Description:** Repairing the split table (blank line at former line 85, which pushed OI-095/096/097
outside it) and restoring the missing OI-092/093/094 rows prompted a full audit of every row against
every `### OI-NNN` detail section. Six residual inconsistencies were found, all verified real — **this original list is SUPERSEDED by the 2026-08-11 re-audit below**:
- **CLOSED detail, row still in the Open table:** `OI-029`, `OI-047`, `OI-076`, and (added
  2026-08-05, closed later the same day by a different session) `OI-020`, `OI-025`.
  **THIS DEFECT CLASS CAUSED A REAL FALSE ALARM THE SAME DAY** — worth the severity bump.
  Reading only `OI-029`'s Open-table row (which still describes "TWO live/unrotated credential
  exposures") and not its detail section, a session escalated it to Gabriel as an urgent live
  security exposure with "deploy access to oxfordra.net", and wrote him a rotation runbook.
  The detail block records it CLOSED 2026-08-03: Gabriel had already revoked the
  `ORA Lease App Sync` PAT — the only live token, the one both exposures leak — and the
  corrupted backup folder was deleted and independently re-verified. A follow-up digest
  comparison confirmed only ONE file still holds an actual token VALUE
  (`oxford-realty_archived-20260726/oxfordra-net/.claude/settings.json`), it is that single
  already-revoked credential, and the two other "hits" were matches on the variable NAME
  `NETLIFY_AUTH_TOKEN` with no value assigned. Net: dead material on disk, not an exposure.
  The Open-table row is the surface most readers hit first; a stale one here does not merely
  lose work, it manufactures urgency.
- **Row present, no detail section at all:** `OI-056`, `OI-068`, `OI-097`. **— RESOLVED 2026-08-11: all three now carry a `### OI-NNN` detail section** (verified by direct header scan). The defect CLASS is not resolved — it recurred on a different set, see the re-audit below.
**Re-audit 2026-08-11 (mechanical, whole file) — 16 inconsistencies across FOUR classes.**
*(Classes (ii) and (iii) were fixed later the same day — see "Fixed 2026-08-11" below. The four
class descriptions are kept verbatim as the audit found them.)*
Derived by partitioning every `| [OI-NNN](#OI-NNN) |` row on which side of the `## Closed` heading it
falls, joining to every `### OI-NNN` header, and reading each matched section body for a `**Status:**`
field. Each finding was then confirmed by reading the section itself, so none is a regex artifact.

- **(i) CLOSED detail, row still in the Open table — 5:** `OI-020`, `OI-025`, `OI-029`, `OI-047`,
  `OI-076`. Unchanged from the 2026-08-05 list as amended (this is the class that caused the OI-029
  false alarm described above).
- **(ii) Open-table row with NO detail section — 5:** `OI-101`, `OI-102`, `OI-103`, `OI-104`,
  `OI-105`. **The original (ii) trio is resolved**; the class recurred on the five session-end
  optimization candidates filed 2026-08-05, which were added as rows without ever getting sections. **— FIXED 2026-08-11.**
- **(iii) NEW CLASS — Closed-table row with no detail section — 1:** `OI-106`. The mirror of (ii) on
  the closed side. Worth separating because a closed item with no section has no `Evidence:` line, so
  nothing records *what was actually checked* — the one field the Convention calls mandatory at
  closure. **— FIXED 2026-08-11.**
- **(iv) detail section present but no `**Status:**` field — originally recorded as 5; ⚠️ **FOUR OF
  THOSE FIVE WERE FALSE POSITIVES**, retracted 2026-08-11 (see "Retraction" below). Genuine set was
  `OI-113` alone — **FIXED 2026-08-11**. The real point stands for the one real case: **this class is
  invisible to a status-mismatch check** — a row-vs-detail comparison silently skips an item with no
  status to compare, so a (iv) item can never be caught by the audit that catches (i). That is why it
  is called out separately rather than folded into (i).

**Counts at re-audit:** 69 Open-table rows · 44 Closed-table rows · 107 detail sections · 0 sections
without a row · 0 ids appearing in both tables.

**Fixed 2026-08-11 — classes (ii) and (iii), six sections back-filled.** `OI-101`–`OI-105`
(Open) and `OI-106` (Closed) now carry `### OI-NNN` detail sections. Each was reconstructed **from its
own table row**, which was the only surviving record, and each carries an explicit reconstruction
notice so a later reader can tell derived text from originally-authored text. Two were strengthened
beyond a restatement rather than merely transcribed:
- **`OI-101`** — its central claim was re-verified live: `sell-your-building.html:930` still carries
  the `XXXXXXX` placeholder, so the item is correctly still OPEN. The same check surfaced something
  the row never recorded: the placeholder also survives in **ten files under
  `website-canonical/.worktree-preview-deploy/`**, a stale preview worktree. The row's "only tracked
  source file" wording remains accurate, but a preview deployed from that worktree would ship
  placeholder Insight Tags on ten pages. Recorded in the new section as a decision item.
- **`OI-106`** — being CLOSED, its `Evidence:` was independently re-verified three ways rather than
  copied: commit `4066213` exists with a matching message; it is reachable from `remotes/origin/main`,
  confirming the push landed (local `main` does not contain it, consistent with [OI-112](#OI-112), not
  a contradiction); and the shipped advisory string was **observed firing live** in the back-filling
  session's own `UserPromptSubmit` output.
**Post-fix verification:** 69 Open-table rows · 44 Closed-table rows · **113 detail sections** · 0 rows
without a section · 0 sections without a row · 0 ids in both tables. `memory-integrity-probe.py` clean
of dead OI pointers.

**Retraction 2026-08-11 — four of the five class-(iv) findings were WRONG, and the reason is worth
more than the finding was.** `OI-092`, `OI-093`, `OI-094` and `OI-095` **all carry a current
`**Status:**` line** at the top of their primary section. They were never defective. The audit's
scanner mapped id → section with `re.match(r'^### (OI-\d{3})')` and, scanning top-to-bottom, let each
later match overwrite the earlier one — **last-wins**. For exactly these four ids a later match
exists, because each has one or two **appendix sections that reuse the parent id in their heading**:

| Appendix heading | Parent |
|----|----|
| `### OI-092 — CORRECTION appended 2026-08-05` | OI-092 |
| `### OI-093 — RESOLVED (diagnosis) 2026-08-05` | OI-093 |
| `### OI-093 — RESOLVED 2026-08-05` | OI-093 |
| `### OI-094 — AUDIT COMPLETE 2026-08-05 (…)` | OI-094 |
| `### OI-094 — RESOLVED 2026-08-05 (…)` | OI-094 |
| `### OI-095-CANDIDATE — lender block …` | OI-095 |

An appendix legitimately carries no `**Status:**` field — it is a continuation, not an item — so
resolving the id to the appendix and then reporting "no status" is a pure artifact. **The genuine
class-(iv) set was `OI-113` alone**, which has a single heading and really did lack the field; it now
reads `**Status:** OPEN`, consistent with its row's position in the Open table and with its own closing
line ("confirm whether it was signed or needs a nudge").

**NEW — class (v), a tooling hazard, not a row/detail inconsistency.** Six appendix headers share the
`### OI-NNN` prefix with their parent item. **Any tool that maps id → section by that regex and takes
last-wins will silently read an appendix as the item**, which is precisely what manufactured the
retracted finding above. `memory-integrity-probe.py` resolves `open-items-tracker.md#OI-NNN` pointers
and is exposed to the same shape. Two candidate fixes, neither applied: anchor the match
(`^### (OI-\d{3})\s*$`) so appendices are skipped, or rename appendix headings to a form that does not
begin with a bare id (e.g. `#### CORRECTION — OI-092, 2026-08-05`). The second also fixes the anchor
collision: `#OI-092` is ambiguous while two headings begin with it. **Counts:** 113 bare `### OI-NNN`
section headers (one per row, exactly) + 6 appendix headers.

**Class (i) is larger than first reported — 9, not 5 (corrected 2026-08-11).** Re-running the audit
**anchored** (`^### (OI-\d{3})\s*$`, first-match, appendices excluded) put the four retracted ids back
in scope under the *correct* class. `OI-092` and `OI-095` read `**Status:** CLOSED`, and `OI-093` and
`OI-094` read `**Status:** RESOLVED`, while **all four rows still sit in the Open table**. So those ids
were never defect-free — the original finding named the wrong defect, not a non-existent one. Full
class (i), all needing a row move to Closed:

`OI-020` · `OI-025` · `OI-029` · `OI-047` · `OI-076` · `OI-092` · `OI-093` · `OI-094` · `OI-095`

**NEW — class (vi), status-vocabulary drift.** The Convention specifies `Status` as **OPEN / CLOSED**.
Actual distribution across the 113 sections: **59 OPEN · 51 CLOSED · 2 RESOLVED · 1 "IMPLEMENTED, not
yet merged/deployed"**. The three non-canonical values are not cosmetic — **a strict `CLOSED` test
under-reports class (i) by two** (`OI-093`, `OI-094` were missed on the first anchored pass for exactly
this reason). `OI-100`'s "IMPLEMENTED, not yet merged/deployed" is a *legitimate* intermediate state
the two-value vocabulary cannot express, and its row is correctly in the Open table — so the fix is
probably to admit a third value explicitly rather than to force it into one of the two. Any status
check must match `CLOSED|RESOLVED` at minimum until this is settled. Reverse defect checked and clean:
**no** Closed-table row has a detail section still reading OPEN.

**FIXED 2026-08-11 — class (i) closed, all 9 rows moved.** `OI-020`, `OI-025`, `OI-029`, `OI-047`,
`OI-076`, `OI-092`, `OI-093`, `OI-094`, `OI-095` now sit in the **Closed** table. Done only after the
concurrent `repo-housekeeping` claim was released, so the file was quiet for the first time this
session. Method and guarantees:
- **Closure dates were read from each item's own record, never inferred.** Three (`OI-029`, `OI-047`,
  `OI-076`) already carried a `**Closed:**` field; the other six had the date embedded in their
  `**Status:**` line. For `OI-092` (`CLOSED 2026-08-05 (merge), re-verified 2026-08-09`) the *closure*
  date was taken, not the re-verification date.
- **Row content is byte-identical across the move.** The Closed table has five columns to the Open
  table's four, so each row was re-emitted with the closure date inserted as column 3; the `Source`
  and one-line cells were asserted unchanged, cell by cell, for all nine.
- **`**Closed:**` fields added** to the six sections that lacked one (`OI-020`, `OI-025`, `OI-092`,
  `OI-093`, `OI-094`, `OI-095`), sourced from their own Status lines — otherwise the move would have
  created a fresh inconsistency, a Closed-table date with no field behind it.
- **Post-move verification:** 60 Open · 53 Closed · 113 sections · 0 rows without a section · 0
  sections without a row · 0 ids in both tables · 0 malformed rows · **0 Closed-table rows missing a
  `**Closed:**` field** · no Closed-table row whose section still reads OPEN. Classes (i)–(iv) are all
  empty.

**NEW — class (vii): a table row was physically split across 15 lines, and this is a RECURRENCE.**
Found while moving `OI-095`, which could not be moved until repaired. Its row began at one line, did
**not** close, and its remaining 14 lines sat *after* the complete rows for `OI-111`, `OI-112` and
`OI-113` — so those three were physically wedged inside the broken row. In any renderer the
unterminated row plus a 14-line prose block **terminates the table**, leaving every following row
(`OI-096` onward, including this item) outside it. Repaired 2026-08-11 by joining the 15 fragments on
single spaces — a pure join, no content authored: every seam was checked and reads as continuous prose
(the first splits the string `"no change"` mid-quote), the result is 1,824 chars with exactly the
5 unescaped pipes a 4-column row requires, and the three wedged-in rows were left untouched in place.
**Why this matters more than the repair:** this file's own history records repairing a split table in
this same region before — *"the blank line at former line 85, which pushed OI-095/096/097 outside
it"*. Same area, same item, second occurrence. **The root cause is not identified and is still open**;
only the symptom has been cleared, twice. Nothing currently detects it — a row-vs-section audit sees
`OI-095` as present and consistent, because the *row text* survives the break intact. A cheap check
exists: every line matching `^\| \[OI-` must end in an unterminated-by-backslash `|`. That check is
green as of this repair (0 malformed rows).

**Still open in this item:** class **(v)** (6 appendix headings reusing the `### OI-NNN` prefix) and
class **(vi)** (status-vocabulary drift — still 59 OPEN / 51 CLOSED / 2 RESOLVED / 1 IMPLEMENTED; the
two `RESOLVED` items are now correctly in the Closed table, so the drift no longer hides a
mis-filed row, but it still defeats any `CLOSED`-only matcher). Plus the (vii) root cause above.
Neither (v) nor (vi) is a row/detail inconsistency — both are hazards that make future audits of this
file unreliable, which is why the item stays OPEN with every original class closed.

**Audit method note — read this before re-running.** Use the **anchored, first-match** regex and match
`CLOSED|RESOLVED`. The unanchored last-wins form produced a five-item false positive on 2026-08-11
(see the Retraction above) *and* the anchored-but-`CLOSED`-only form under-counted class (i) by two.
Both failure modes were in the same audit, an hour apart. A **third** followed during the row move: a
fixed-window scan (`section header + 20 lines`) reported four Closed-table rows as missing a
`**Closed:**` field when all four had one — the field sat at offsets 22–29 in sections whose `Status`
block alone runs longer than the window. **Scan whole sections, bounded by the next `### ` header —
never a fixed line count.** Three false positives from three different truncated scans, one session.

**Fixed already (do not re-file):** `OI-057` and `OI-059` were the mirror-image defect — rows correctly
moved to Closed and dated 2026-08-04, but their detail `Status:` lines left at OPEN. Reconciled
2026-08-05 in favour of the rows after verifying `6dc5df3` really did land `hooks/tests/lib/gitfixture.py`
and convert `test-eos-review-gate.py`.
**Caution:** `OI-047` and `OI-076` were touched by recent commits (`90e680c`, `fb4875c`) and this file
collides constantly — reconcile against those commits, and expect other sessions holding edits.
**Auto-check:** re-run the row/detail audit; it reports DETAIL-WITH-NO-ROW, STATUS/TABLE MISMATCH,
ROW-WITH-NO-DETAIL and blank-line-splitting-table in one pass.

**FIXED ON MAIN 2026-08-12 — all four classes cleared.** Audited mechanically against `main` itself
(not replayed from another branch: the branch this work originated on had diverged, and its numbers
did not match — `OI-092` in particular reads **OPEN** here and **CLOSED** there, so it was correctly
left in the Open table on this side).

- **Split table rows — 2 repaired.** `OI-092`'s row ran on for 2 further lines and `OI-095`'s for 14,
  neither terminating. **An unterminated row followed by a prose block ends the table**, so every row
  after them rendered outside it. Repaired by pure join — no content authored; each seam was read and
  reads as continuous prose, and each result is exactly 4 cells. `OI-095` is a **recurrence**: this
  file's own history records repairing a split table in this same region before. **Root cause now
  IDENTIFIED and filed as [OI-124](#OI-124)** (2026-08-12) — rows hard-wrapped at ~100 columns and written
  as a blob via `hash-object`/`update-index`, bypassing every renderer; and note OI-124 also shows the
  earlier repair was a **different** mechanism (a blank line inside the table), so the two are not one bug. Cheap detector: every line matching
  `^\| \[OI-` must end in an unescaped `|`.
- **Missing detail sections — 6 back-filled.** `OI-101`–`OI-105` (Open) and `OI-106` (Closed). Each
  was reconstructed **from its own table row**, the only surviving record, and carries an explicit
  reconstruction notice so derived text stays distinguishable from originally-authored text.
- **Class (i) — 8 rows moved to the Closed table.** `OI-020`, `OI-025`, `OI-029`, `OI-047`, `OI-076`,
  `OI-093`, `OI-094`, `OI-095`. Closure dates were read from each item's own record (three already
  carried a `**Closed:**` field; five had the date inside their `**Status:**` line) — never inferred.
  The Closed table has five columns to the Open table's four, so each row was re-emitted with the date
  as column 3 and its `Source` and one-line cells asserted **byte-identical**, cell by cell.
- **`**Closed:**` fields added** to the five sections that lacked one (`OI-020`, `OI-025`, `OI-093`,
  `OI-094`, `OI-095`), sourced from their own Status lines — otherwise the move would have created a
  fresh inconsistency: a Closed-table date with no field behind it.

**Verified after:** 64 Open · 53 Closed · **117 detail sections** · 0 rows without a section · 0
sections without a row · 0 ids in both tables · 0 malformed rows · 0 rows with the wrong cell count
for their table · **0 ids lost or gained** (117 before, 117 after).

**Still open in this item — two audit hazards, neither a row/detail inconsistency:**
- **Appendix headings reuse the `### OI-NNN` prefix** (e.g. `### OI-092 — CORRECTION appended`), so any
  id→section map that takes last-wins silently reads an appendix as the item. This produced a
  five-item false finding on 2026-08-11 before it was caught. It also makes `#OI-092`-style anchors
  ambiguous. Use an **anchored, first-match** regex (`^### (OI-\d{3})\s*$`).
- **Status-vocabulary drift.** The Convention specifies OPEN / CLOSED; the file holds 63 OPEN, 51
  CLOSED, 2 RESOLVED and 1 "IMPLEMENTED, not yet merged/deployed". A `CLOSED`-only test therefore
  **under-reports class (i)** — `OI-093` and `OI-094` are RESOLVED and would be missed. Match
  `CLOSED|RESOLVED` at minimum. `OI-100`'s value is a legitimate intermediate state the two-value
  vocabulary cannot express, so the fix is probably to admit a third value rather than force it.
  **Update 2026-08-12:** `OI-100` itself has since closed (its fix was actually merged 2026-08-05,
  `230da82`; the tracker wording just hadn't caught up) — this specific example no longer exists,
  though the general vocabulary-drift point may still apply to future intermediate-state items.

**Audit method note — read before re-running.** Use the anchored first-match regex, match
`CLOSED|RESOLVED`, and **scan whole sections bounded by the next `### ` or `## ` header, never a fixed
line count**. Each of those three rules exists because its absence produced a false positive during the
2026-08-11 audit.

### OI-099
**Status:** OPEN
**Opened:** 2026-08-05
**Source:** `governor-drift-probe.py` false positive investigated 2026-08-05
**Severity:** LOW — advisory only. **Verified NOT push-blocking:** the pre-push shim runs exactly three
gates (doctrine-drift, hook-tests, confidentiality); `governor-drift-probe` is in none of them. It is
reached via `memory-integrity-probe.py:395`.
**Description:** `RE_DSCR_THRESH` (`maintenance/governor-drift-probe.py:117`) is
`dscr[^0-9\n]{0,40}?(?<![vV])([0-9]+\.[0-9]+)(?![0-9])(?!%)\s*[x×]?` — it reads **any** decimal within 40
non-digit characters after "DSCR" as a threshold declaration. A **measured** coverage ratio written in
prose therefore flags as a governor redefinition. It fired on
`reference_workbook_annual_debt_service_366day_overcapture.md:27`, where a **measured** Banwick coverage
ratio sat a few words after the token "DSCR" — in a sentence explicitly noting the value moved *away*
from the floor — exiting **1**, which also makes
`memory-integrity-probe` report a governor-drift issue and stands the daily guards red.
**Why the existing suppressors miss it:** `RE_DSCR_CORRECTION` demands the tight
`corrected … from X to 1.25` shape; the prose said "moved *away* from the 1.25x governor floor".
**Worked around 2026-08-05, NOT fixed:** that one sentence was reworded to avoid the bare
`DSCR <decimal>` adjacency; probe now exits 0 (861 files scanned). The gap is untouched — the next
measured DSCR written in prose re-fires it.
**Constraint on any real fix:** it must distinguish measured-vs-declared without handing a drifting
editor a one-word evasion on a Hard-Invariant-4 guard, and it would sit beside `RE_DSCR_PIVOT_DECOY`,
which *deliberately* treats arrow-shaped DSCR changes (`1.25x → N.NN`) as drift. Mandatory adversarial
REFUTE pass + the old-vs-new differential battery (`reference_refute_differential_harness.md`).
**Demonstrated 2026-08-05:** filing this very item re-fired the probe — the OI-099 row originally quoted
the offending string verbatim, so *documenting* the false positive reproduced it in this file. Both
places were reworded to describe the shape without quoting it. Treat that as the reproduction case.
**Design precedent already in the probe:** `RE_SENTINEL_PROSE` (`:~267`) solves exactly this class for
the probe's own documentation — it suppresses `1.75x regression sentinel`, deliberately bound to a
**term of art** rather than a bare nearby token, and span-scoped so a real declaration sharing the line
still flags. A measured-vs-declared suppressor should follow that shape, not a looser one.
**Auto-check:** `python maintenance/governor-drift-probe.py` — exit 0 = clean.

### OI-068
**Status:** OPEN
**Opened:** 2026-08-03
**Source:** ora-pm appsec fix plan Task 8 (OI-043), local `plan/appsec-fixes-oi034-048` branch, commit
`59f79ff`; confirmed by an independent task reviewer
**Severity:** product gap, **not** a security defect in what shipped
**Description:** Detail section written 2026-08-05 (row existed with no `###` section — see
[OI-098](#OI-098)); restated from the row, not re-investigated.
Autopay-with-payment-method is **unreachable from any live frontend path today**:
- `PortalAccount.tsx` is the sole caller of `setAutopay` and never passes `payment_method_id`.
- The enable toggle is disabled unless `lease.autopay_payment_method_id` is already set.
- The only writer of that column is `PATCH /portal/autopay`, which the frontend never calls with a PM.
- `PortalPayNow.tsx` creates a payment method but only ever feeds it to one-time
  `createPaymentIntent`, never to `setAutopay`.
So the whole autopay-enrollment feature is unbuilt/unreachable on the frontend, independent of Task 8's
(correct) backend hardening.

### OI-097
**Status:** OPEN — scheduled action, not yet due
**Opened:** 2026-08-05
**Source:** phantom-dispatch fix (`e441130`, stop killing Claude Desktop's own renderer); Gabriel ruling
2026-08-05 (**remind, do not automate**)
**Description:** Detail section written 2026-08-05 (row existed with no `###` section — see
[OI-098](#OI-098)); restated from the row.
**Re-measure the phantom-dispatch rate on/after 2026-08-07.** The 2026-08-05 measurement is **not** a
post-fix reading: the newest phantom in that window is 11:04 ET and the renderer only came back at
11:08 ET, so there is no meaningful post-fix data yet. A "rate improved" claim off that window would be
[[feedback_verified_null_vs_inferred_null]].
**Baseline to beat:** 54 phantom dispatches vs 68 confirmed runs = **44%** over the 94h to 2026-08-05,
with `fleet-deadman` logging "OK" through all of them.
**Deliberately NOT registered as a scheduled task** — one-time measurement, and the registry is under a
single-writer rule.
**Auto-check:** re-run `maintenance/phantom-dispatch-probe.py` over a window starting after 11:08 ET
2026-08-05 and compare against the 44% baseline.

### OI-123
**Status:** OPEN
**Opened:** 2026-08-12
**Source:** ora-appsec-sweep 2026-08-12 (oxford-command-center @ `0b5b36e7f3ec847b019a7a955cea59b55d8f6bbb`, security-auditor dispatch, Fable)
**Severity:** MEDIUM (missing defense-in-depth security headers on an externally-served, Access-gated surface)
**Description:** oxford-command-center's deployed Cloudflare Pages mirror ships no security-header
mechanism at all. `public/` contains only `_redirects` — no `_headers` file exists anywhere in the
repo (`find <worktree> -name _headers` returns nothing, node_modules excluded), `index.html` carries
no `<meta http-equiv="Content-Security-Policy">`, and neither `scripts/bake-mirror.ts` nor
`scripts/deploy-mirror.ps1` emits CSP / HSTS / X-Frame-Options / X-Content-Type-Options /
Referrer-Policy on the served response (verified this run by direct worktree grep, NOT taken from the
agent's report). Consequences on the served `ora-command-center.pages.dev` / `brain.oxfordra.net`
mirror: no enforced CSP script backstop, and the app is framable (no `X-Frame-Options`/`frame-ancestors`).
Confidentiality of the mirror is protected independently by Cloudflare Access gating, so this is a
defense-in-depth gap, not an active exposure — MEDIUM, not HIGH. Its reachable-XSS partner is the
`react-router-dom` open-redirect-to-XSS in OI-017's residual set: with no CSP, an injected script runs
with full origin privileges.
**Distinct from ora-pm's OI-037/OI-060:** different repo, and those items concern ora-pm's
`public/_headers` + the Cloudflare-Pages-Function-vs-static-asset nuance. occ has no `_headers` at all,
so there is nothing to extend — this is a from-scratch add.
**How to apply:** add `public/_headers` with a strict `Content-Security-Policy` (must allow
`api.anthropic.com` for the `/sse` streaming endpoint), `Strict-Transport-Security`,
`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`. This is
served-surface config; the deploy runs through the repo's Pages-mirror `/ship` gate (Invariant-2-adjacent).
Pair it with the OI-050 Host-header allowlist as the mirror's two outstanding perimeter items.
**Auto-check:** none. Cheap one: fail the bake/deploy if `public/_headers` is absent or lacks a CSP line.


### OI-118
**Status:** OPEN (logged; remedy is a judgement call, not obviously "just un-ignore it")
**Opened:** 2026-08-11
**Source:** `.gitignore:61` (`/scheduled-tasks/*/*`); surfaced while wiring `ora-health-guard` to the shared double-fire guard
**Description:** The guard helpers in `scheduled-tasks/_shared/` (`block-sentinel.py`, `outlook-sent-probe.ps1`,
`test-block-sentinel.py`, `README-DOUBLE-FIRE-GUARD.md`) live under the ignore pattern `/scheduled-tasks/*/*`
and were force-added to `main` past it (PRs #39/#40, 2026-08-09). That combination is a trap on any branch
that forks from before the force-add: there the file is **untracked AND ignored**, so
(a) `git status` shows nothing no matter how much you edit it, and
(b) git will **silently overwrite it** on `checkout` / `merge` / `rebase` toward `main` — no conflict, no
warning, exit 0. On a merge git even reports it as `create mode 100644 <path>`, i.e. it presents a
destructive overwrite as a file creation.

**Verified by reproduction, not inferred** (four throwaway repos, 2026-08-11), holding the real
`.gitignore` shape and force-added-on-main history constant:

| File state | `checkout main` | `merge main` | `rebase main` |
|---|---|---|---|
| untracked **+ ignored**, tracked on main | silent overwrite, exit 0 | silent overwrite, exit 0 | silent overwrite |
| untracked, **not** ignored (control) | `error: … would be overwritten` → Aborting, exit 1 | — | — |
| tracked + local mods, main differs | `error: Your local changes …` → Aborting, exit 1 | Aborting, exit 1 | — |

The control row is what establishes causation: identical setup minus the ignore rule and git refuses. The
`.gitignore` is precisely what removes git's normal untracked-file safety net.

**Live instance that prompted this:** the `~/.claude` checkout sat on `feat/model-canary-probe-step25`
(27 commits behind `origin/main`). `outlook-sent-probe.ps1` carried 34 self-test cases on disk vs 21 on
`origin/main` — 13 new cases that existed nowhere but the working tree, invisible to `git status`, one
`git merge main` away from being erased. Landed instead via a worktree off `origin/main`, where the files
are tracked and therefore protected.

**Why the obvious fix may not be right:** un-ignoring `/scheduled-tasks/*/*` would start tracking every task
folder's run residue (temp HTML bodies, `send-log.txt` at ~99KB and growing, `tmp/`), which is presumably why
the pattern is broad in the first place. Options, none free: (a) add negation entries (`!/scheduled-tasks/_shared/*.py`
etc.) so the shared helpers are never ignored — narrowest, but must be kept in step as helpers are added;
(b) move the shared helpers out of `scheduled-tasks/` entirely (e.g. `maintenance/_shared/`), which breaks every
absolute path in every wired SKILL.md; (c) leave as-is and rely on always working from a worktree off `main`.
Gabriel's call.

**Auto-check:** none yet. A cheap one: fail if any path matched by `.gitignore` is also tracked on `origin/main`.

### OI-128
**Status:** OPEN
**Opened:** 2026-08-12
**Source:** `ora-task-integrity-guard` 2026-08-12 run, STEP 2.5 — sixth consecutive sweep to hand-apply a
fully mechanical retag
**Severity:** LOW — no data at risk and no gate is impaired; the cost is recurring manual work and the
chance that one hand-application skips a guardrail.

**Description:** `maintenance/model-canary-probe.py` already computes everything an apply mode needs — it
applies the scope filter, buckets each task, and observes the fired model off the transcript cut — but it
stops at reporting. Every sweep since 2026-07-13 (07-13, 07-15, 07-22, 07-24, 08-09, 08-12) has then applied
the retag by hand. The 2026-08-12 run retagged **17** in-scope CC/MCP tasks `UNVERIFIABLE` → observed id
manually. The probe's own SKILL.md wiring note already says the method "is entirely mechanical, so leaving it
manual guaranteed recurrence" — that prediction has now held six times.

**An apply mode MUST carry these four guardrails**, each of which cost a session to establish:

| # | Rule | Why |
|---|---|---|
| a | Write by **direct SKILL.md frontmatter edit**, never `update_scheduled_task` | That tool drops every top-level frontmatter key it does not own — it would have destroyed `output_contract` on **6 of the 17** on 2026-08-12 (OI-109). Verified same day: the CC/MCP registry JSON holds **zero** `description` fields, so `list_scheduled_tasks` composes the description from the file and the frontmatter edit is the effective path. |
| b | Never write a task bucketed `NO_OBSERVATION` | A zero that might mean "couldn't look" is a failure, not a clean result ([[feedback_verified_null_vs_inferred_null]]). Two tasks (`ora-calibration-snapshot`, `ora-broker-touch-cadence`) sat in this bucket on 08-12 and were correctly left alone. |
| c | Always emit `[MODEL: <id> observed \| checked YYYY-MM-DD via <method>]`; never the `[1m]`-suffixed id | The nested bracket closes the tag early, severing the date half, which pins the task in the undated/stale bucket permanently and immune to re-tagging in that form. |
| d | Re-read via `list_scheduled_tasks` after writing and print the confirmed tag | A task whose final act is a write has no witness that it landed — the 2026-08-03 lost-write class that sat undetected for five days. |

**Auto-check:** none needed beyond the probe's own exit code — it already exits 1 on any in-scope
`[ACTION]`, so a clean exit after an apply run is the verification.

### OI-129
**Status:** OPEN (diagnosed and reproduced same-day; fix is a judgement call between three options)
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

### OI-134
**Status:** QUEUED — approved by Gabriel in-turn 2026-08-12, **no work started**
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

### OI-122
**Status:** FIX IN REVIEW — [PR #67](https://github.com/ZeOoba/ora-claude-config/pull/67) (branch
`oi122-gate-msg`, commit `21d0de2`, 2 files / 240 insertions, based on `origin/main`). Message-only; the
tokenizer is deliberately unchanged. See the CORRECTED root cause and the REJECTED fix direction below.
**Opened:** 2026-08-12 (id reserved 2026-08-11 by session `1de11c79`; the row was never written until now)
**Source:** `eos-review-gate` blocking a pathspec commit during the 2026-08-11 `ora-cc-snapshot-refresh` run
(session `1de11c79-1c29-4ad7-8e6b-20c60c5f8279`). Root cause corrected and independently re-verified 2026-08-12.
**Severity:** MEDIUM — friction, **not** a security hole. The parse miss *widens* scope, so the gate stays
fail-closed and nothing unreviewed slips through. It matters because the trigger is near-permanent (100+
uncommitted files across a dozen sessions), which makes "just mint an override" the path of least resistance.

**Symptom.** A commit scoped with `-- <pathspec>` is blocked by `eos-review-gate` on a blast-radius file the
commit does not land — typically one another session has staged in the shared `~/.claude` index.

**⚠ The original diagnosis was WRONG and is withdrawn.** This item was first reported as "the gate ignores the
pathspec at runtime and keys on the whole shared index." That is not what happens. `scope_for_cmd()`
(`hooks/eos-review-gate.py:443`) *does* compute correct pathspec scoping, and `main()` uses it. The reservation
note in the allocation ledger under this id **has since been corrected too** (2026-08-12, by the reserving
session, id/timestamp/session unchanged): it now retracts both earlier theories and points here. An earlier
revision of this row warned that the ledger still repeated the retracted theory — that warning is itself stale
and is withdrawn.

**Actual root cause (CORRECTED 2026-08-12 — a second, narrower revision; see the Fix direction block below).**
`tokenize_cmd_segments()` in `hooks/lib/git_commit_parse.py` (~line 314) tokenizes the command **line by line**
rather than with one whole-string `shlex.split()`. That is deliberate 2026-07 hardening: a bare newline is bash's
statement separator, so line-wise splitting closed a real bypass — and **heredocs are a handled exception**, not
an oversight. The consequence is narrower than this row first claimed: a **directly-quoted** multi-line `-m`
message splits the invocation across many "lines", so `find_commit_segment()` (`:94`) never sees the trailing
`-- <pathspec>` and scope falls back to the no-pathspec set (staged + pending-add + `-a`-modified).

A heredoc-fed multi-line `-m` — the fleet's sanctioned commit shape — parses and scopes **correctly**. So this is
not "multi-line messages break the gate"; it is "one unsanctioned message form does, and the gate never says so."

**Differential, re-run independently 2026-08-12 (not relayed):** identical pathspec, only the message shape differs.

| `-m` message shape | `paths` | scoped correctly? |
|---|---|---|
| single line | `[]` | yes |
| **heredoc-fed multi-line (the fleet-sanctioned form)** | `[]` | **yes** |
| directly-quoted multi-line | `["scheduled-tasks/ora-pm-ledger/property_register_snapshot_diff.py"]`, key `03b8fb93055b…` | no |

The heredoc row is the one that changes the conclusion, and it was missing when this row was first drafted.

```bash
python "C:/Users/Owner/.claude/hooks/eos-review-gate.py" --key --cmd 'git commit -q -m "one line" -- scheduled-tasks/ora-cc-snapshot-refresh/SKILL.md'
```

This also explains the observation that originally misled the diagnosis — the "identical key across two different
commit messages" was two *multi-line* messages, both of which lost the pathspec and therefore keyed identically.

**Workaround, no override required.** Use a **single-line** `-m` for pathspec commits in `~/.claude`, amending the
body afterwards if a longer message is wanted. A clean-index worktree sidesteps it entirely, since there is then
nothing else staged for the widened scope to catch.

**⚠ Fix direction CORRECTED 2026-08-12 — the tokenizer change described here is REJECTED, do not re-derive it.**
This row previously prescribed "teach the line-wise tokenizer that an unterminated quote continues across lines."
That was written before the heredoc case was tested. The tokenizer is **not** defective: it attaches the pathspec
correctly for a single-line `-m` *and* for the heredoc-fed multi-line form, which is the fleet's sanctioned commit
shape. Only the directly-quoted multi-line form — not sanctioned — strands it.

Making that form work means tracking quote state across arbitrary content. Rounds 2 and 3 of
`tokenize_cmd_segments` both did exactly that and both shipped **false ALLOWs**
(`hooks/lib/git_commit_parse.py:327-376`): a decoy `-- <path>` leaking as the real pathspec, a real `git commit`
hidden behind a decoy `--dry-run`, plus O(n²) blowup (55s at 1000 lines against a ~5s hook budget). Today's
failure is fail-CLOSED; every attempt to relax it produced fail-OPEN. **Gabriel ruled in-turn 2026-08-12:
message-only, tokenizer untouched.** This would have been the fourth re-derivation of a twice-reverted change.

**Actual fix: the block message.** It never said the commit *form* caused the widened scope — it offered only
"record a verdict" or "mint an override," both wrong here. Any future change in this area is still `hooks/**`, so
it takes the mandatory adversarial REFUTE pass and the old-vs-new differential battery
([[refute-differential-harness]]).

**Do not "fix" this by recording a review verdict.** Doing so keys an approval artifact covering the *other*
session's staged file, clearing the gate for their unreviewed commit on code you do not own and that may be
mid-edit. Same class as [OI-120](#OI-120) (config-write-guard index-state gap).

**Resolution (2026-08-12) — [PR #67](https://github.com/ZeOoba/ora-claude-config/pull/67).** The block message
now names the message shape, points at the two forms that scope correctly, and explicitly says not to mint an
override and not to record a verdict over the fallback set. Detection is a bare `--` token stranded in a
tokenized segment that is not a command invocation of its own, classified via `_segment_git_subcommand_and_args`
so an env-assign prefix (`GIT_PAGER=cat git log ... -- <path>`) is not mistaken for wreckage.

Independent adversarial review, 2 rounds, `claude-fable-5` pinned. Round 1 REQUEST-CHANGES with 3 majors — the
most instructive being that the hint's own copy-paste heredoc remedy was indented, so its terminator failed at
column 0 and copying it reproduced the very false block it explained, in a loop. Round 2 APPROVE after all 7
findings closed, with the reviewer independently re-running the suite and its own probes. Evidence: 64/64
`test-eos-review-gate.py`; `test-commit-provenance-guard.py` green; old-vs-new differential 0 scope deltas across
12 adversarial commands including every round 2/3 PoC; 10/10 malformed hint inputs raise nothing; 77/77 on the
pre-push chain.

**Accepted residuals** (documented in the function docstring): a chained **non-git** command carrying a
legitimate bare `--` still trips the hint; a stranded message line beginning with the literal word `git`
classifies as a git invocation and stays silent (fails toward silence).

**Not fixed, by design:** the directly-quoted multi-line form still over-blocks. The change makes the gate
explain itself, turning an override into a ~30-second detour. Workarounds needing no override: a single-line
`-m`, or a heredoc-fed `-m`.

**Adjacent work:** session `e23f4c54` holds `hooks-override-auth-eos-gate-msg` for a *different* defect in this
same block message (it prints a `--record` command that `config-write-guard` itself blocks; follow-on to PR #66).
Additive to #67, but touches adjacent lines — whichever lands second needs a trivial rebase.

**Related:** [OI-119](#OI-119) (the sibling pre-push gate whose flakiness drives the same override-minting
pressure) · [[reference_cc_snapshot_refresh_dq_flag_alert_is_count_not_severity]] carries the supersession note (archived 2026-08-21, `_archive/reference_cc_snapshot_refresh_dq_flag_alert_is_count_not_severity_archived_2026-08-21.md`).
### OI-141
**Status:** OPEN — probe fix landed (`f852a45`, hardened after independent code review found the
fix's first cut silently downgraded `OBSERVATION_STALE` on any mixed+stale run); the retag and the
doctrine question below remain open
**Opened:** 2026-08-12
**Source:** `ora-appsec-sweep` 2026-08-12 fire, session `f74b697f-cc6f-48f6-818b-8de7d95b393e`,
re-observed at Gabriel's in-turn request after `model-canary-probe` flagged it `CONTRADICTED`
**Severity:** MEDIUM — no data at risk, but it invalidates an assumption the whole model-tag
standard rests on, and it silently produced contradictory observations of the same fire.

**Description.** The model-tag doctrine assumes a scheduled run has *a* model — one id per fire,
per-session and non-deterministic ([[reference_scheduled_task_model_standard]]). That is wrong.
This fire ran **two** models on the **main chain**:

| Rows | Model | From |
|---|---|---|
| 12–103 | `claude-fable-5` (32 msgs) | 19:26:51Z |
| 109–236 | `claude-opus-4-8` (45 msgs) | 19:54:29Z |

Zero sidechain rows, so this is **not** subagent contamination — the obvious first hypothesis,
and it was checked and disproved (`isSidechain` is `false` on every row; the fable and opus rows
are byte-identical in shape, differing only in timestamp). The scheduled portion cuts at row 244,
so the switch at row 109 has **no human turn anywhere near it** — nobody ran `/model`.

**Two consequences, both material:**

1. **`model: fable` IS honoured, and that reverses a recorded finding.** This task's own tag says
   `frontmatter model: fable still NOT honored on CC/MCP (server-pin)` (checked 2026-08-03). The
   pin *was* honoured for the first ~28 minutes and then fell back. This is the
   [[feedback_agent_model_pin_not_held_end_to_end]] class — previously seen on Agent dispatches,
   now confirmed for a **task's own frontmatter pin**.
2. **Plurality voting manufactured a contradiction.** `observe_models()` collapsed the counts with
   `max()`, so the same task read `claude-fable-5` when sampled mid-run and `claude-opus-4-8` once
   complete — two contradictory "observations" of one fire within one day, with the 45/32 margin
   never surfaced. Fixed in `f852a45`: a run spanning >1 model now reports `MIXED_RUN` (info) when
   the tag matches any model present, and `CONTRADICTED` naming *every* model when it matches none.

**Retag deliberately DEFERRED.** No single id describes this run, and the tag parser takes the
first token of the value, so any compound tag still resolves to one id. **Post-fix update
(2026-08-12 review): `claude-fable-5` no longer "keeps tripping CONTRADICTED whenever opus wins the
plurality"** — that was only true of the pre-fix probe, which collapsed a mixed run to its
plurality winner and compared against that single value. With the fix, `claude-fable-5` (a model
genuinely present in the run) now produces a *stable* `info MIXED_RUN` every time, regardless of
which model wins the plurality on a given sample. It remains the least-bad single-value option, not
because it dodges an alarm, but because it is the one id in the run actually backed by a durable
signal (the task's own `model: fable` frontmatter pin) rather than a coin-flip server assignment —
though picking it would still assert a false fact (that the run is purely fable) and is still not
done here. `claude-opus-4-8` erases finding (1) above and flips as soon as the fallback timing
shifts; `UNVERIFIABLE` reads as "never looked" when we looked and found two. **The open question is what a
MODEL tag should mean for a task whose model changes mid-run** — that is Gabriel's call, and it
likely wants a doctrine amendment in [[reference_scheduled_task_model_standard]] rather than a
tag edit.

**Not affected:** the 17-task retag merged earlier the same day ([PR #68](https://github.com/ZeOoba/ora-claude-config/pull/68))
was audited against this — all 17 were **100% pure single-model** observations, zero mixtures. Those
tags stand. See also OI-128 (the `--apply` mode, which must grow a MIXED guard before it writes) —
**flagged in review as unresolvable (2026-08-12): `[[OI-128]]` matches no section in this tracker,
and no `--apply` flag exists under `maintenance/`.** Root cause found the same day: OI-128's filing
commit (`e6c532a`) is real but stranded on `feat/model-canary-probe-step25`, which never merged to
`main` — the same divergence class OI-131 already tracks. Not re-filed here; once that branch (or
just this commit) lands, the `[[OI-128]]` link will resolve on its own.

**Auto-check:** `model-canary-probe.py` reports `MIXED_RUN` every run; `maintenance/test-model-canary-probe.py`
carries 7 assertions built from this exact session's shape.

### OI-126
**Status:** OPEN — **TRANSIENT.** Expected to self-close once `_push-main-tmp` is released. If it is gone and the
primary checkout is on `main`, close this without further work.
**Opened:** 2026-08-12
**Source:** session 08df9f95 (an unattended `ora-doctrine-integrity-guard` scheduled run that Gabriel took over
interactively), while investigating why merged `hooks/**` fixes were not taking effect
**Description:** The primary checkout `C:/Users/Owner/.claude` sits on `feat/model-canary-probe-step25`
(19 ahead / 48 behind `origin/main`, ~117 uncommitted files). It **cannot** be moved onto `main`, because
`C:/Users/Owner/.claude/worktrees/_push-main-tmp` has `main` checked out and git permits a branch in exactly one
worktree. This is a git constraint, not neglect.

Consequence: PR #51 and #55 are merged but **inert**. Both are `hooks/**` changes that only take effect once the
primary checkout is on a ref containing them. Until then the live pre-push chain runs the pre-#51/#55 versions —
`test-confidentiality-guard.py` ENV-SKIPs on every worktree push (131 assertions silently not running), and a
load-induced test failure hard-blocks a push with no retry (the OI-119 symptom).

**Verified, not inferred (2026-08-12):**

| Claim | Evidence |
|---|---|
| `_push-main-tmp` is NOT a stale leftover | reflog: created 15:59, `merge origin/main` at 15:59 and 16:03, `git push orig…` at 16:25; index rewritten 16:12; 0 uncommitted |
| Nothing in `~/.claude` creates it | no match in any `.py`/`.sh`/`.ps1`; created by hand by a session |
| Owner is `local_25942895` | its transcript enumerates `repo-housekeeping.json` among **its own** claim files; last-activity matches the worktree owner record to ~3s |
| Local `main` already has all four PRs | `#47` script present, `#49` 3 refs, `#51` 2 refs, `#55` 8 refs — checked by CONTENT, since squash-merges leave no ancestry |
| Local `main` is 4 ahead / 0 behind `origin/main` | those 4 are the owning session's unpushed merge commits |

**Resolution:** the owning session releases `_push-main-tmp`, then the primary checkout moves to `main`. **Do not
force it** — the ~117 uncommitted files are other sessions' work and were NOT verified to survive a checkout
against the 48 incoming commits. Doctrine forbids `checkout`/`reset`/`rebase` on a contaminated tree.

**Why this wasn't handed off directly:** `send_message` is unavailable *from* unattended sessions, and the target
is itself a scheduled-task session that cannot receive. A copy-paste handoff was given to Gabriel instead.

**Search-tooling gotcha found here (worth its own note):** ripgrep honours `.gitignore`, so a `Grep` sweep for
`_push-main-tmp` returned NOTHING while a plain `grep -r` found the one reference — in
`obsidian-fleet-mirror/session-state.d/`, which is gitignored. That reference is what identified the owning
session. **Any search for runtime/session state must not rely on ripgrep's defaults.**

---

### OI-146
**Status:** OPEN — diagnosed and reproduced 3 times; not yet fixed
**Opened:** 2026-08-13 (id allocated same day by session `1de11c79`)
**Source:** hit directly while landing [PR #67](https://github.com/ZeOoba/ora-claude-config/pull/67) and
[PR #83](https://github.com/ZeOoba/ora-claude-config/pull/83) — three consecutive pushes of independently
committed, verified-locally branches timed out at push, each initially misdiagnosed as concurrent-load
contention before the real cause was found.
**Severity:** MEDIUM — pure friction (wasted retries, misdirected diagnosis), never a false ALLOW. A stale gate
can only be MORE conservative than the live one (older/tighter budgets, missing new checks), never less.

**Symptom.** A branch/worktree that was current when created starts failing its own pre-push hook-tests gate
after a fix to that gate lands on `main` — specifically, the same commit that timed out at 180s pushed clean
with 0 failures immediately after a `git rebase origin/main`, no code change involved.

**Root cause.** `hooks/git-prepush-hook-tests-gate.py` is not a fixed piece of infrastructure the whole fleet
shares live — it is **committed content**, and `git push` runs whichever copy the *pushing* branch's working tree
currently has. A worktree created via `git worktree add ... <old-base>` (this repo's standard pattern for
isolated landing) freezes that copy at creation time. Any subsequent improvement to the gate itself —
`PER_TEST_TIMEOUT_SECONDS`, retry policy, a new check — is real on `main` and invisible to every already-open
branch until each one individually rebases.

**Concrete reproduction, 2026-08-13.** `bcbca32` raised `PER_TEST_TIMEOUT_SECONDS` from 90 to 240 on `main`
(landing the OI-135 fix). Branch `fix/model-floor-test-live-session-assertion` was cut from `99c462f`, before
that commit, so its working copy still read 90. The gate's own doubled-budget retry rule (2× the per-test
timeout) meant it retried failing tests at 180s — comfortably short of the 240s the *live* checkout already
enforced. `hooks/tests/test-memory-orphan-link-guard.py`, timed in isolation on this exact branch: **122.1s,
exit 0, 79/79 passed** — well inside 240s, essentially guaranteed to lose to a 180s ceiling under any concurrent
load at all. Three pushes of the identical commit timed out this way; `git rebase origin/main` (picking up
`bcbca32`) made the fourth push clean.

**Why this reads as something else.** The gate's own retry messaging (`timeout-retry (timed out under load,
passed on the doubled-budget rerun; not blocking)`) is written from the live-checkout's perspective and gives no
signal that the *budget itself*, not the load, might be the variable. Combined with genuinely high concurrent
session counts most evenings, a stale-base timeout and a real load-induced timeout produce byte-identical
symptoms. The session that hit this initially attributed it to load contention (a reasonable read given the
evening's session count) before checking the base and finding the real cause.

**Not a new defect class — a compounding one.** [OI-119](#OI-119) documents the gate's baseline flakiness under
its own load. OI-135/[OI-127](#OI-127) (budget too low for concurrent load, fixed by `bcbca32`) is the
specific defect whose fix this item's reproduction happened to straddle. OI-146 is the meta-finding sitting on
top of both: **any** gate fix, not just that one budget number, has this same rollout lag across open branches,
for as long as the fleet keeps worktree-per-task as its landing pattern.

**Fix direction.** Advisory, not blocking — a deliberately pinned/frozen base is sometimes intentional, so this
must never itself become a false block. Have `git-prepush-hook-tests-gate.py` (or a thin wrapper hook run before
it) diff its own file's current git blob hash against `origin/main`'s copy of the same path before running the
suite; if they differ, print one loud line — e.g. `NOTE: this branch's pre-push gate is N commits behind
origin/main (last synced <sha>) — a failure here may be a stale gate, not your change; rebase before spending
time on retries.` Cheap (one `git rev-parse`/`git cat-file` pair, no new process), and it converts a
misdiagnosis into a one-line hint the first time it would otherwise cost three retries.

**Do not treat this as owned by, or blocking, whatever gate defect prompted the next reproduction of it.** This
item exists to be the standing pointer for *that* class of confusion generally.

**Related:** [OI-119](#OI-119) (baseline gate flakiness under load — the confound this item's timeouts were
initially mistaken for) · OI-135/[OI-127](#OI-127) (the specific budget fix this item's reproduction
rode along with, `bcbca32`) · [PR #67](https://github.com/ZeOoba/ora-claude-config/pull/67),
[PR #83](https://github.com/ZeOoba/ora-claude-config/pull/83), [PR #85](https://github.com/ZeOoba/ora-claude-config/pull/85)
(all merged) — the three branches whose push histories produced this diagnosis.

---

### OI-127
**Status:** DUPLICATE — superseded by OI-135. Filed only to close an orphan reservation; do not investigate separately.
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

**Do not fix from this row.** Track the fix, evidence, and any REFUTE pass under **OI-135**. Note that OI-135's
own row/section may still be in flight on branch `docs/oi-135-prepush-timeout-budget` and is deliberately NOT
linked here as `#OI-135`: the anchor does not resolve until that lands, and `memory-integrity-probe.py`
hard-fails on dead pointers into the tracker. Convert to a real link once the section exists.

**Related:** [OI-119](#OI-119) — same gate, the *flakiness* failure mode (errored tests are not retried) rather
than the timeout budget. A fix for one should be checked against the other.

---

### OI-119
**Status:** OPEN (diagnosed and reproduced; fix is a judgement call between three options)
**Opened:** 2026-08-11
**Source:** `maintenance/_tests/test_allocate_oi_id.py`, hit via `.git/hooks/pre-push` gate 2
(`hooks/git-prepush-hook-tests-gate.py`) while pushing the ora-health-guard guard wiring
**Description:** The pre-push gate runs the whole tracked test suite and **blocks the push on any failure**.
`test_allocate_oi_id.py` is flaky under the concurrency that gate itself creates, so it can hard-block a push
that has nothing to do with it — as it did here, on a change touching none of the code it exercises.

> **FIX SHIPPED 2026-08-12 — [PR #55](https://github.com/ZeOoba/ora-claude-config/pull/55), merged. Status left OPEN deliberately: closing it is the author's call, not mine.**
> Option "retry a failing file once" was put to Gabriel and chosen. `_run_one()` now gives ANY failing file one
> rerun at the NORMAL budget, not just a timed-out one. Deliberately `elif`, so a timed-out file (which already
> spent the doubled rerun) never also gets this one — no file can pay three budgets. The doubled budget still
> keys on `timed_out` rather than rc, preserving the 2026-07-26 REFUTE finding, now asserted via per-call budget
> lists instead of a bare spawn count. A recovered flake is disclosed by name as FLAKY; a genuine failure fails
> both runs and still blocks.
> Independent review caught a real defect in the first draft: a run-1 FAIL whose rerun printed `CANNOT RUN:`
> reclassified to env-skip — non-blocking AND invisible, since the flaky disclosure scans passes only. Forced
> back to FAIL, with a regression fixture. Suite 90 → 98 assertions.
> **Caveat:** this was diagnosed independently on 2026-08-12 before finding this item — duplicated effort, and the
> arithmetic matched (`9/12` = the three coupled assertions of the 12-thread test failing together). The flake was
> never reproduced on demand across three attempts, so the root cause is inferred from that signature, not proven.
> The companion `test-claim-file-collision.py` flake noted above was NOT investigated and may be a different cause.
> Not fixed here: the symmetric pre-existing hole where a TIMED-OUT run 1 followed by an env-skip rerun is
> non-blocking — the "ran far enough to fail proves it can run" rationale does not transfer to a timeout.

**Reproduced, not inferred (2026-08-11):**

| How run | Result |
|---|---|
| standalone, 5 sequential runs | **12/12 pass**, exit 0, every time |
| 6 runs concurrently | **1 of 6 failed 9/12**, exit 1 — the gate's exact signature |
| the real gate run that blocked | `74 pass, 1 fail, 1 env-skip (of 76)`; `allocate-oi-id tests: 9/12` |
| the retry that succeeded | `75 pass, 0 fail, 1 env-skip (of 76)` |

**WIDENED same day — it is not one test, it is the gate.** A second test flaked on a later push of this same
branch. Tally across three consecutive pushes of identical-quality work:

| Push | Gate result |
|---|---|
| 1 — guard wiring | **FAIL** `maintenance/_tests/test_allocate_oi_id.py` (74 pass / 1 fail) |
| 2 — review fixes | clean (75 pass / **0 fail**) |
| 3 — this item | **FAIL** `hooks/tests/test-claim-file-collision.py` (74 pass / 1 fail) |
| 3 retry | clean (75 pass / **0 fail**) |

Two *different* tests, two clean runs of the same suite on the same machine minutes apart. Note also that push
1 and push 3 each additionally logged a `timeout-retry` for `test-eos-review-gate.py` — the gate's own
tolerance path firing on yet a third test.

`test-claim-file-collision.py` was investigated separately and is **not** reproducible on demand: it passes
39/39 standalone and 6/6 under a 6-way concurrent run, including with a live claim file present (the obvious
suspect, since that session was holding an `open-items-tracker` claim at the time — ruled out). So the gate's
real load, 76 test files with subprocess-spawning tests among them, is heavier than a hand-rolled concurrency
simulation reproduces. **Do not close this item on "cannot reproduce" for any single test** — the reproducible
`test_allocate_oi_id.py` case below is the tractable entry point, but the failure is a property of the gate's
concurrency, not of one test file.

**The `test_allocate_oi_id.py` case, which IS reproducible — one root cause, three reported failures.** All
three are the same event:
```
FAIL: 12 concurrent allocations: no exceptions  -- ["PermissionError(13, 'Permission denied')"]
FAIL: 12 concurrent allocations: all distinct   -- [OI-008 .. OI-018]   <- 11 ids, not 12
FAIL: 12 concurrent allocations: contiguous     -- [OI-008 .. OI-018]
```
One of the 12 threads loses a Windows file lock, so 11 ids are allocated instead of 12; "all distinct" and
"contiguous" then fail as *cascades* of that single exception, not as independent defects. The classic Windows
concurrent-file-access flake — same family as `feedback_npm_test_intermittent_access_violation.md`, which
CLAUDE.md's Done bar already names as the spurious-failure gotcha.

**Why this is worth fixing rather than tolerating.** The gate ALREADY has flake tolerance, and it fired in the
same run: `timeout-retry (timed out under load, passed on the doubled-budget rerun; not blocking):
hooks/tests/test-eos-review-gate.py, maintenance/test-governor-drift-probe.py`. But that path keys on
**timeout**. A `PermissionError` is not a timeout, so it falls straight through to a hard block. The obvious
escape is the `allow-hook-test-failure` override token — which is a 60-minute, multi-use bypass of the entire
tracked test suite, minted to get past a known-flaky test. That is exactly how a *real* failure eventually gets
waved through, and it is the same shape as the 2026-08-09 OI-111 orphan that blocked every session's push.

**Escalation 2026-08-12 — the timeout-retry path is not sufficient either, and the predicted override happened.**
Pushing `task/snapshot-refresh-rationale-correction` (a docs-only commit touching two `scheduled-tasks/*/SKILL.md`
files, zero hook code, zero blast-radius files) was hard-blocked by `hooks/tests/test-eos-review-gate.py`:

| Signal | Value |
|---|---|
| Gate result | `73 pass, 1 fail, 1 env-skip (of 75)` |
| Failing test | `hooks/tests/test-eos-review-gate.py`, exit 124, `TIMEOUT after 180s` — **after a timeout retry** |
| Same test standalone, same machine | `ALL REVIEW-GATE TESTS PASS (55)`, exit 0, `real 2m25.937s` (**145.9s**) |
| Headroom vs the 180s per-test budget | **34.1s, ~19%** — inverts under load |
| Others in the same run | `test-git-prepush-scan.py`, `test-memory-orphan-link-guard.py` needed the doubled-budget rerun |

**(1) The tolerance path itself now fails.** The widening above records `test-eos-review-gate.py` only ever
appearing as a *non-blocking* `timeout-retry`. On 2026-08-12 it exhausted that retry and hard-blocked. So the
gate's flake tolerance is not merely blind to non-timeout errors — its per-test timeout budget is too tight for
a test that legitimately needs ~146s, which makes the retry a coin-flip rather than a fix. `hooks/eos-review-gate.py`
was unmodified at the time (last change `e39ce4c`, two weeks prior), so this is budget headroom, not a regression.

**(2) The override escape this item warned about was taken.** With the diagnosis in hand Gabriel authorized it
in-turn, and an `allow-hook-test-failure` token was written to land `46cf1e2`. That is precisely the sequence
this item predicted — *"exactly how a real failure eventually gets waved through"* — reached here on a false
positive, with a measurement to justify it. The next one may not arrive with a 146s-vs-180s number attached.
**Treat the running count of override tokens minted against this gate as the item's real severity signal.**

A per-test budget derived from a measured baseline (or a `slow-test` allow-list carrying a longer budget) would
close the timeout half without touching the `PermissionError` half. Reserved-but-unused id from the session that
filed this escalation: **OI-127** (orphan by design — the ledger does not reclaim reservations).

**THIRD-PARTY CONFIRMATION, same day (2026-08-12, `ora-task-integrity-guard` session `f4c30f1b`).** An
unrelated session hit this independently while pushing a 32-line SKILL.md description-text change (zero hook
code). **Three consecutive pushes blocked**, which is the strongest evidence yet for the "property of the gate,
not one test" reading — and therefore for option 1 over options 2/3, which each fix a single test:

| Attempt | Gate result | Hard-blocked on |
|---|---|---|
| 1 | 2 fail | `test-eos-review-gate.py`, `test-git-prepush-scan.py` |
| 2 | 1 fail (76/77 pass) | `test-eos-review-gate.py` |
| 3 | 2 fail (75/77 pass) | `test-eos-review-gate.py`, `test-memory-orphan-link-guard.py` |

Every failure `exit 124, TIMEOUT after 180s`, **after** the doubled-budget retry; never an assertion failure.
**The blocking set rotates between runs** — only `test-eos-review-gate.py` is constant — and the tests needing
a doubled-budget rerun rotate too (`test-claim-work-lib`, `test-confidentiality-guard`, `test-config-write-guard`,
`test-git-prepush-doctrine-gate-worktree`, `test-commit-hygiene-guard`, `test-git-prepush-scan` each appeared).
Machine state: **63 node/claude processes, CPU pegged at 100%**. No override token was minted — the session
declined to bypass the gate and routed the decision to Gabriel, who landed the work another way.

**DIAGNOSTIC TRAP worth carrying on this item.** Two of those three pushes reported **exit 0 while the push had
failed**, because the command piped `git push` into `tail` and the shell returned the pipe's status
([[feedback_piped_gate_exit_masking]]). Only an unpiped run surfaced `REAL_EXIT=1`. Anyone diagnosing this gate
from a piped transcript will conclude the push succeeded and the branch is on the remote when it is not.

*(Ported 2026-08-12 from the primary `~/.claude` checkout, commit `92163b6`, where session `e0f8485e` originally
landed this escalation — that branch is diverged from `main` (see [OI-131](#OI-131)) so it was not otherwise
reaching this copy of the tracker. Content is verbatim; this note documents provenance only.)*

**Options (Gabriel's call), roughly cheapest first.** Note the widening above changes their relative weight:
options 2 and 3 fix ONE test, and a second test has already flaked, so only option 1 (or reducing the gate's
parallelism) addresses the actual class.
1. Extend the gate's existing retry path to cover `PermissionError`/`OSError`-class failures, not just
   timeouts — smallest change, keeps the signal, but broadens what counts as "retryable". **Preferred given
   the widening**, since it is the only option that is not per-test.
   1b. Or reduce the gate's concurrency (run the suite with a lower worker count). Slower push, but it treats
   the cause rather than tolerating the symptom, and the gate is not on a latency budget.
2. Fix the test: serialize or retry the file access inside the 12-thread case, so it stops failing under load.
   Best if the production allocator is genuinely safe and only the *test* races. Per-test, so it leaves
   `test-claim-file-collision.py` and anything else in the same class untouched.
3. **Check first whether the allocator itself is the racer.** The test asserts 12 concurrent allocations
   produce 12 distinct contiguous ids; if `allocate-oi-id.py` can really drop an allocation under contention on
   Windows, the flake is a genuine product bug surfacing correctly and must NOT be retried away. The "8
   concurrent PROCESSES: all distinct" case passed in every run, which is weak evidence the lock works
   cross-process and the fault is thread-level — but this should be settled before option 1 or 2 is chosen.

**Not caused by, and does not affect, the change that surfaced it** (PR #54): that commit touches no code this
test exercises, and the push succeeded on a clean retry with 0 failures.

**Auto-check:** none. A cheap one: have the gate print which tests it retried and why, so a recurring flake is
visible as a pattern rather than as one session's bad luck.

### OI-132
**Status:** FIX APPLIED 2026-08-12 — options 2 **and 3** both shipped (`ora-sofr-direct-prefetch` **v1.2** then
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

### OI-133
**Status:** OPEN — investigation, not a shipped fix. The slot half is already instrumented (efficacy check
re-armed for 2026-08-20 16:30 ET); this item owns the dispatch/delivery half.
**Opened:** 2026-08-12
**Source:** the `ora-pm-ledger-retime-efficacy-check` run of 2026-08-12 — which was itself an early fire
(see [[reference_one_time_task_fired_days_early]]). Evidence pulled from the CC/MCP registry's `recordedSkips`,
`~/.claude/scheduled-tasks/_shared/send-log.txt`, and `~/.claude/scheduled-tasks/ora-pm-ledger/state/`.
**Severity:** MEDIUM — Block B self-heals via its 7-day retro-sweep, but **Blocks A and C have no retro
mechanism at all**, so every missed day permanently loses that day's Notion digest and EOD action ledger.
Pre-retime miss rate was 12 of 21 days (57%).

**Description.** `ora-pm-ledger` was retimed 2026-08-12 from `0 18 * * *` to `0 15 * * *` on the theory that
the Desktop app was usually dark at 18:00 ET. The available evidence suggests the slot was probably **not** the
binding constraint:

| Signal | Measurement (2026-08-12) |
|---|---|
| `recordedSkips`, this task | **107** suppressed dispatches — **71 `per_task_limit`**, 36 `global_limit` |
| `recordedSkips`, fleet-wide | 1,863 (`global_limit` 1,631 / `per_task_limit` 232) |
| Baseline misses on days the app was **provably open past 18:00** | **5 of 12 (42%)** — 07-23, 07-26, 07-31, 08-08, 08-10 |
| Baseline misses with ledger **execution** evidence but no email | 1 — 2026-08-10 |

**Do NOT re-open the `global_limit` / catch-up-burst question.**
[[reference_fleet_throttle_skip_catchup_burst]] already investigated that class exhaustively across five
recurrences and ruled it expected scheduler arbitration with no code fix — the levers are host uptime and the
sleep timeout (AC sleep set to NEVER 2026-08-12), not per-task config. Re-deriving it is wasted work.

**What is actually open:**
1. **`per_task_limit` is the majority here (71 of 107).** The throttle file documents `per_task_limit` as the
   narrower same-task double-fire guard and flags the "lone task, no neighbours" shape as the one pattern
   worth a *fresh* investigation. On `ora-pm-ledger` it is not the exception — it dominates. Its prior
   recorded episodes on this very task cleared in ~1 minute; 71 events is a different magnitude and has not
   been explained.
2. **2026-08-10 ran but did not send.** `tenant-db-2026-08-10.json` and `capex-2026-08-10.json` were both
   written at 12:44 and no Block A/B/C email exists for that date. Execution reached the work and failed at
   *delivery* — distinct from both "never dispatched" and from the silently-dropped-slot mode. Worth checking
   whether the send step failed silently or the run terminated between snapshot and send.
3. **Delivery-confirmation beacon for Blocks A and C.** Because neither block has a retro-sweep, a
   ran-but-didn't-send day is invisible and unrecoverable. B's retro-sweep is the existing model.

**Evidence rule for anyone picking this up:** a send in the log PROVES the app was open at that hour; absence
proves nothing — say "no positive evidence of open," never "the app was closed." Likewise a state file PROVES
execution; its absence does not disprove it. And per
[[reference_scheduler_lastrunat_stamped_at_dispatch]], `lastRunAt` is stamped at dispatch and cannot evidence
that a run completed — prove execution from work product.

**Gotcha:** `config-write-guard.py` blocks any Bash command whose text names the scheduled-tasks registry path,
even for a pure read (the matcher is deliberately broad and must not be narrowed). Read the registry with the
Read/Grep tools, or via a script that derives the path from `%APPDATA%` at runtime — do **not** mint an
`allow-config-write` token to satisfy a read.

**Related:** [[reference_fleet_throttle_skip_catchup_burst]] (mechanism, already closed),
[[reference_one_time_task_fired_days_early]] (the early fire that surfaced this),
[[reference_scheduler_lastrunat_stamped_at_dispatch]] (why `lastRunAt` is not execution evidence).

### OI-138
**Status:** OPEN — **ROUTED to session `e23f4c54`**, which holds the `hooks-override-auth-eos-gate-msg` claim on
this same file. Filed as an OI rather than sent directly because the discovering session was an unattended
scheduled-task run, where `send_message` is unavailable. This is a **different defect** from that session's
current work (which is about the blocking message handing the operator a `--record` command that
`config-write-guard` then blocks) — but it lives in the same file, so it is probably one pass. It is not a
request to drop that work.
**Opened:** 2026-08-12
**Source:** hit live while committing two markdown memory files (the OI-133 filing + a new reference memory);
`hooks/eos-review-gate.py`
**Severity:** MEDIUM — no data loss; the cost is that a security gate fires on commits it has no business
gating, and therefore gets overridden as routine.

**Defect 1 — the blocking path ignores pathspec scoping.** A commit containing two `.md` memory files was
blocked, demanding an independent review of three files the commit does not touch, all owned by other live
sessions:

| Scored path | Gate's reason |
|---|---|
| `hooks/lib/claim_work.py` | `hooks/**` enforcement code |
| `hooks/tests/test-claim-work-lib.py` | `hooks/**` enforcement code |
| `scheduled-tasks/ora-pm-ledger/property_register_snapshot_diff.py` | scheduled-task registry |

The first two are almost certainly session `e23f4c54`'s own PR #59 working tree — the sharpest form of the bug:
one session's in-flight edits block an unrelated session's markdown commit.

Measured in repo `C:/Users/Owner/.claude`:

```
python hooks/eos-review-gate.py --key
  paths: ['hooks/lib/claim_work.py','hooks/tests/test-claim-work-lib.py',
          'scheduled-tasks/ora-pm-ledger/property_register_snapshot_diff.py']
  key:   ef91d37feb7e...

python hooks/eos-review-gate.py --key --cmd 'git commit -m "x" -- <my.md>'
  paths: []   key: ""
```

**The gate already computes the correct answer; the block simply does not ask it that way.** Using the
pathspec form of `git commit` did NOT change the block — it fired with the unscoped path set either way.

**Defect 2 — CONFIRMED: the block and `--record` key off different computations, so the gate cannot be
cleared by its own documented procedure.** This was initially filed as "the key looks unstable"; that framing
was wrong and is corrected here. Both sides are **deterministic**, and they **disagree**:

| Code path | Key | Observations |
|---|---|---|
| PreToolUse block | `03b8fb93055b` | stable across 2 blocks, minutes apart |
| `--key` (what `--record` keys off) | `ef91d37feb7e…` | stable across 4 consecutive runs |

It is therefore NOT content churn from other sessions editing foreign files. The two code paths simply compute
different keys. The consequence is the serious part: a reviewer dispatched per step 1 and recorded per step 2
writes an artifact under `ef91d37f…`, while the block looks for `03b8fb93055b` — **it can never match, so no
amount of correct reviewing will clear this gate.** The single-use override is the only exit, which is exactly
how a security control degrades into a formality. Fixing Defect 1 (scoping) without also reconciling these two
key computations will NOT restore a working review path.

**Suggested direction (the owning session's call):** have the block derive its path set from the actual commit
invocation — the same logic `--cmd` already implements — falling back to the unscoped scan only when the
command cannot be parsed. Because this is security-gate scope logic, run the old-vs-new differential battery
per [[reference_refute_differential_harness]] and judge deltas, not absolutes: narrowing scope must NOT let a
bare `git commit` with no pathspec sweep blast-radius files in unreviewed. That case is the whole point of the
gate and must still block.

**Live precedent for the cost:** Gabriel approved a single-use `allow-unreviewed-commit` override on the
evidence above to land commit `01ae05b` (two `.md` files, scoped key empty). Token was removed immediately
after. That is one override that should never have been needed.

**Related:** [[reference_refute_differential_harness]] (the required verification shape for guard/scope regex
changes), [OI-129](#OI-129) (the sibling class where a gate asserts on live shared state and blocks unrelated
sessions' pushes — same failure shape, different gate).

### OI-140
**Status:** OPEN
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

### OI-142
**Status:** OPEN
**Opened:** 2026-08-12
**Severity:** MEDIUM
**Source:** Surfaced investigating a `tools/pending_reimport.py` sweep hit on `exception-detection`
(`ora-skills`) with no ledger entry. Diffing repo HEAD vs. the runtime cache vs. the (then-uncommitted)
working tree showed the cache held a **v1.3** `SKILL.md` (installed live 2026-08-11 17:30) with zero commit
anywhere in `ora-skills` git history — `git log -- exception-detection/SKILL.md` jumped straight from v1.2
(`b723118`, 2026-07-21) to the backfill commit (`85abbbc`, 2026-08-12, Gabriel-directed) that landed v1.3 and
same-day v1.4 content together. Session-transcript search traced the v1.3 content to session
`89c314f4-a39e-43b4-8d1b-6b38d91774f7`, which appears to have packaged and Save-skill-installed directly from
its own uncommitted working tree on 2026-08-11, never committing.
**Description:** The whole `pending_reimport.py` / `repo_first_check.py` discipline assumes one direction of
drift — repo commits land, the manual Save-skill click lags behind (`_staging/PENDING_REIMPORT.md`'s entire
model). This incident ran the other way: a skill was installed into the live runtime cache with no
corresponding commit ever landing, so for roughly 24h `ora-skills` git HEAD did not describe what was actually
live for `exception-detection`, and nothing in the sweep flags that class of gap — `sweep_drift()` only
compares content, never asks whether the cache's content exists in git history *at all*. It surfaced only
because a human diffed the working tree by hand while chasing an unrelated ledger question.

Not yet established: whether session `89c314f4` packaged+installed directly (deliberately or by mistake
skipping `git commit`), or whether a different path (e.g. a manual `package_skills.py` run against a dirty
tree followed by a Save-skill click, by that session or another) produced the same result. `Check 5` in
`tools/hooks/pre-commit` (`repo_first_check.py --check-staged`, added 2026-08-03 after four prior REPO-FIRST
violations — acquisition-underwriting v4.5/v4.6, disposition-analysis, parcel-data-recovery) exists for
exactly this failure class but fires **only at commit time**; it cannot catch an install that never gets
committed at all, which is what appears to have happened here.

**Candidate fixes (not yet chosen):**
- Extend the sweep to flag any runtime-cache skill body whose content matches **no blob in git history**
  (not merely "differs from HEAD"). `pending_reimport.py` already does exactly this classification for shared
  repo-root deps (`_file_history_hashes()` / `classify_shared_copy()` → `CACHE-AHEAD`); generalizing it to a
  skill's own bundled files would catch this class going forward instead of relying on a human noticing.
- Or: have `package_skills.py` refuse (or loudly warn) when packaging from a source tree that has uncommitted
  changes, closing the gap at the point of install rather than only detecting it after the fact.

**Related:** ora-skills commit `85abbbc` (the backfill that recovered this instance);
[[feedback_verified_null_vs_inferred_null]] (same shape — a sweep that reads "no candidates" as "verified
in sync" rather than "didn't check this direction").

---

### OI-150
**Status:** OPEN — UNCONFIRMED, needs deliberate reproduction
**Opened:** 2026-08-13 (session `15f5b972`)
**Source:** landing a `settings.json` deny-rule change ([PR #97](https://github.com/ZeOoba/ora-claude-config/pull/97))
from an isolated worktree, `~/.claude/worktrees/land-commit-hygiene`.
**Severity:** UNKNOWN pending reproduction — if real, it is a gap in a security-relevant control
(`hooks/eos-review-gate.py`'s automatic blast-radius review dispatch), but this session obtained an
independent review manually as a substitute, so no diff shipped unreviewed on this occasion.

**Symptom.** `feedback_auto_review_blast_radius_gate.md` ratifies that `settings.json` changes get an
**automatic, blocking** independent-reviewer dispatch via `hooks/eos-review-gate.py`, enforced as a
PreToolUse hook on `git commit`. A `git commit -- settings.json` run from an isolated worktree produced
no BLOCKED line, no WARNING line, and no override-token prompt — the commit simply succeeded, as if the
gate either did not fire or determined the diff was out of scope.

**What was and wasn't checked.** `hooks/lib/git_commit_parse.repo_root(cmd, cwd)` was tested directly
against the exact commit command and cwd: it correctly returns the *worktree's own* toplevel via
`git rev-parse --show-toplevel` (worktrees have a valid, distinct toplevel; this is not a `.git`-file
detection bug). That rules out the most obvious "repo root not found -> silent allow" theory. The next
candidate, `scope_for_cmd()` (defined in `hooks/eos-review-gate.py` itself, not the shared lib), was
**not** successfully tested — by the time the silence was noticed, the diff was already committed, so
nothing was staged and a post-hoc call to `scope_for_cmd()` could not reproduce the at-commit-time state.
A live PreToolUse hook's actual stdout/stderr is also not visible from the outer Bash tool call result in
this session, so it's possible the hook DID run and print something that was simply not surfaced — that
is untested, not ruled out.

**Why this matters even though nothing shipped unreviewed here.** `config-write-guard.py`'s own block
message recommends doing exactly this — "Preferred path for a REAL edit: do this work in an isolated
worktree... worktree copies are not gated" — for a DIFFERENT gate (config-write-guard itself, which is
Edit/Write-scoped and correctly does NOT apply to worktree copies by design). If `eos-review-gate.py`
*also* goes quiet from a worktree, but for the wrong reason (a bug, not a deliberate scope decision the
way config-write-guard's is), then the sanctioned pattern for making a safe settings.json/hooks/** edit
would silently skip the review that pattern is supposed to force — the two gates would need to agree on
whether "worktree" means "safe to relax" or not, and right now that's unconfirmed for eos-review-gate.

**Needs:** in a disposable worktree, stage a trivial `settings.json` change, run `git commit` with the
hook's own debug/verbose path if one exists (or temporarily instrument it), and capture the hook's actual
stdout/stderr directly rather than inferring behavior from whether the outer `git commit` call succeeded.
Read `scope_for_cmd()` (not `repo_root()`) end to end against a worktree cwd. If the gate does have a
worktree carve-out, confirm it's deliberate and documented (mirroring config-write-guard's own explicit
worktree exemption) rather than an accidental gap.

**Related:** [[feedback_auto_review_blast_radius_gate]] (the ratified doctrine this would undermine);
`hooks/config-write-guard.py` (the DELIBERATE worktree exemption this may be conflated with).

### OI-147
**Status:** CLOSED — REJECTED 2026-08-13; nothing landed, everything reverted
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

### OI-149
**Status:** OPEN — symptom no longer reproduces as of 2026-08-16; awaiting close-out ratification
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

### OI-171
**Status:** FIXED 2026-08-16 in the live SKILL.md + registry — UNVERIFIED until the next run
(2026-08-17 ~06:21 ET) actually suppresses the email
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

---

### OI-205

**Status:** CLOSED 2026-08-24
**Opened:** 2026-08-24 · **Source:** Session workflow-observation follow-up ("mirror check ESCALATE + direct push bypassed refute-required")

**Severity:** HIGH (security-gate coverage gap on a repo carrying financial/governor code).

**Description:** `main` on `ZeOoba/oxford-command-center` had **no GitHub branch protection at all** — confirmed live: `gh api repos/ZeOoba/oxford-command-center/branches/main/protection` returned `404 Branch not protected`. `.github/workflows/ci.yml:33` defines a real `refute-required` job (`npm run check:refute -- --strict --base=...`) gated on financial-code changes carrying a `Refute-Reviewed:`/`Refute-Skip:` commit trailer — but with no branch protection rule naming it as a required status check, nothing stopped a direct push to `main` (no PR, so the `pull_request`-triggered workflow never even ran) from landing ungated. `ora-command-center-mirror-drift-check`'s `ESCALATE` tier (ahead-of-origin, stranded-commit age past threshold) fired correctly per its own design in a recent incident — but the resolution path available to whoever cleared it was a direct push to `main`, which is exactly the operation `refute-required` exists to gate on governor-adjacent code, and there was no platform-level control to stop it.

**Impact:** the `refute-required` gate was advisory-only for any push that bypassed a PR. Its existence in `ci.yml` could read as protection in place when it was not enforced.

**Resolution:** Claude drafted and Gabriel ran (Claude is prohibited from executing security-setting changes itself) `gh api -X PUT repos/ZeOoba/oxford-command-center/branches/main/protection --input protection.json` with `required_status_checks.contexts: ["gate", "refute-required"]`, `strict: true`, `enforce_admins: true`, `required_pull_request_reviews: null`, `restrictions: null`. **Evidence:** re-read via `gh api repos/ZeOoba/oxford-command-center/branches/main/protection` post-change — returns 200 with `required_status_checks.contexts: ["gate","refute-required"]`, `enforce_admins.enabled: true`, `allow_force_pushes.enabled: false`, `allow_deletions.enabled: false`. `required_pull_request_reviews` left `null` (status-checks-only, not PR-only landing) — Gabriel's implicit choice by running the file as-given; revisit if a future direct push still lands ungated (would mean the check-reporting requirement alone isn't sufficient and PR-only enforcement is needed).

**Related:** [[project_ccm_mjs_dmts_parity_and_branch_protection_gap_2026-08-24]], `ora-command-center-mirror-drift-check` SKILL.md (never-push-them-yourself rule), `reference_governor_drift_probe_dscr_scaling_multiplier_fix_2026-08-22` (a different governor-code gate, same theme: a real gate whose enforcement point has a hole).

---

### OI-206

**Status:** IN REVIEW — [PR #299](https://github.com/ZeOoba/oxford-command-center/pull/299) open, CI running, awaiting merge
**Opened:** 2026-08-24 · **Source:** Session workflow-observation follow-up ("nothing enforces .mjs/.d.mts parity")

**Severity:** MEDIUM (recurring red-main defect class, not yet a live security miss).

**Description:** `oxford-command-center/scripts/` hand-maintains `.d.mts` declaration files beside 2 of its 4 `.mjs` scripts (`install-git-hooks.mjs`, `prepush-confidential-scan.mjs`; `ensure-deps.mjs` and `prepush-noi-crosscheck.mjs` have no declarations at all). Nothing keeps a `.d.mts` in sync with its `.mjs` when exports change, and `vitest` (the test runner that gates every commit) transpiles without typechecking, so this class of drift reliably produces a green local test run over a red `npm run typecheck` on `main`. Confirmed twice in the week of 2026-08-17→08-24: `install-git-hooks.mjs` (commits `cafd63c`/`dcdc523`) and `prepush-confidential-scan.mjs` (`8048e7b`/`66b2ebf`/`8c0760f`/`ec4027d` — three near-simultaneous independent fix attempts for the same missing-exports defect, the last of which re-added the SAME three exports the earlier fix had already landed -- duplicate rediscovery, not extra coverage; verified 08-24, main declares 7 of 7). See [[reference_vitest_green_is_not_a_typecheck_mjs_dmts_drift]] for the tooling-blind-spot lesson and [[reference_concurrent_session_duplicate_hardening_work]] for the duplicate-session angle on the same incident.

**Revised plan, built 2026-08-24 — NOT "convert all 4 to tsx" as originally scoped.** Reading each script's own header comment surfaced a real constraint the initial "just be consistent with the other 16 tsx-run scripts" framing missed: 3 of the 4 (`ensure-deps.mjs`, `prepush-confidential-scan.mjs`, `prepush-noi-crosscheck.mjs`) are explicitly documented "Node built-ins only, no install step" — the two pre-push scripts run from the raw shared `.git/hooks/pre-push` with no npm context, and `ensure-deps.mjs`'s entire job is self-healing a missing/wiped `node_modules` (2026-06-13 incident). Making any of them depend on `tsx` (itself in `node_modules`) would reintroduce that exact fragility in the worst place — a security gate or a self-heal script that can't run when the thing it depends on is missing. Also: neither `ensure-deps.mjs` nor `prepush-noi-crosscheck.mjs` is ever imported by a test for its types, so neither was ever actually exposed to the `.d.mts`-drift failure class — the original "all 4" scope over-included them.

Shipped instead:
- `install-git-hooks.mjs` → `.ts`, run via `tsx` (only invoked through `npm run hooks:install`/`prepare`, both npm-context calls — safe). Sibling `.d.mts` deleted.
- `prepush-confidential-scan.mjs` stays `.mjs`. Its `.d.mts` is now **generated** from the source's own JSDoc by a new `generate:confidential-scan-types` step (`tsconfig.confidential-scan-types.json`, `checkJs` deliberately off — only the exported-function JSDoc needs to typecheck, not every internal helper), wired into `pretypecheck`/`prebuild` npm lifecycle hooks, and gitignored rather than committed. Nothing left to hand-maintain, nothing to drift.
- `ensure-deps.mjs`, `prepush-noi-crosscheck.mjs` — untouched, per the above.

**Fix direction:** ~~convert all 4 scripts~~ — superseded by the revised plan above. Remaining before close: PR #299 review/CI/merge, then update this entry to CLOSED with the merge commit.

**Related:** [[project_ccm_mjs_dmts_parity_and_branch_protection_gap_2026-08-24]], [OI-205](#OI-205) (same incident, the branch-protection half).

---

### OI-207

**Status:** OPEN
**Opened:** 2026-08-24 · **Source:** found while fixing the AR review-queue false pointer — oxford-command-center PR [#296](https://github.com/ZeOoba/oxford-command-center/pull/296) and `~/.claude` `6d9ab38`

**Severity:** LOW-MEDIUM — no wrong numbers and no silent write; the failure mode is a real delinquency sitting unattributed in a file nothing reads, with no procedure to clear it. Bounded by how often a genuinely unmatchable row appears (zero observed to date).

**Description:** `oxford-command-center/data/ar/review-queue.json` is **write-only**. The sole writer is `scripts/ar-import-headless.ts:200`; nothing in the repo reads it back, and there is no resolver tool. PR #296 and the `ora-ar-feed-sweep` SKILL.md now document the real remediation loop — fix the matcher (`server/ar/resolve-by-unit.ts`, or the `resolvePropertyId` header map), copy the source file back from `data/ar/processed/` into the inbox, re-run the headless importer (a same-as-of-date re-import overwrites rather than being rejected as stale, `server/ar/resolve-latest.ts:176`, `incomingMs >= existingMs`). **That loop only covers rows a matcher rule CAN fix.** Rows no rule can ever resolve — a tenant absent from the snapshot entirely, or a dead/vacated lease — have no path at all. Neither the PR nor the SKILL.md claims otherwise; the gap is documented as open rather than papered over.

**Not closed by** `fix/ar-unit-parenthetical` (`4e496b1`), which fixes the one specific unit-parenthetical matcher gap that produced the only row ever queued. That is an instance fix, not the class.

**Fix direction (NOT applied — Gabriel ruled option (b), docs-only, in-turn 2026-08-24; this is the deferred option (a)):** a small resolver that reads `review-queue.json`, takes a `leaseId` per row, writes through the same overlay path the headless importer uses, and removes the resolved row. Three things to settle before building:
1. **It needs its own copy of Guard 2.** `Brain` (`server/brain.ts`) loads `data/overlay.json` into memory once at construction and never re-reads it, so any direct overlay write while the dev server is up is silently reverted by the next server-mediated mutation — the same hazard the sweep's Guard 2 exists for.
2. **A hand-typed `leaseId` bypasses the matcher entirely**, reintroducing the silent-misattribution risk the whole partition-confidence design exists to prevent. Needs validation against the live lease roster at minimum.
3. **Better alternative, from Qodo's review of #296:** persist a **source pointer** on each queued row (which file it came from) and add a built-in replay command. That removes the manual copy-back step — currently load-bearing, since the importer archives every file after a successful run — and makes remediation deterministic instead of depending on a human locating the right file in `data/ar/processed/`. Costs a schema change to queued rows plus backward-compat handling for rows already written under the old shape.

**Trigger to build:** the first genuinely unmatchable row appearing in a real sweep. Until then the documented matcher-fix loop is sufficient and this stays deferred — Qodo independently reached the same call ("updating the header docs and runtime hints is the most appropriate low-risk fix... consider a follow-up that makes it actionable via a small CLI/replay path").

**Auto-check:** none automated. To see whether any row is currently queued:
`python -c "import json;q=json.load(open(r'C:/Users/Owner/oxford-command-center/data/ar/review-queue.json',encoding='utf-8'));print(len(q),'row(s)',sum(r.get('d30',0)+r.get('d60',0)+r.get('d90',0)+r.get('d90plus',0) for r in q))"`

---

### OI-208

**Status:** OPEN
**Opened:** 2026-08-26 · **Source:** ora-appsec-sweep 2026-08-26 (ora-pm @ `ca62ecb`, security-auditor dispatch)
**Severity:** MEDIUM (authorization / session assurance)

**Description:** `src/pages/auth/AdminLogin.tsx:18` (Supabase email magic link) and `server/middleware/admin-auth.ts` — no server-side AAL2/step-up requirement exists anywhere on the admin route tree (full-portfolio CRUD, tenant portal invite/revoke, lease-document egress to Anthropic, QB journal exports), while tenants must clear TOTP AAL2 to move money via `requireAal2` (`server/middleware/aal-guard.ts`, 3 routes). This is distinct from [OI-036](#OI-036) (CLOSED) — that item fixed WHO is admitted as admin (exact-match `ADMIN_EMAILS` allowlist, `shouldCreateUser: false`, live tenant-exclusion check); this item is about session STRENGTH once admitted. The privilege hierarchy is inverted: the most privileged principal has the weakest session requirement.

**Impact:** compromise of any allowlisted mailbox (e.g. `ggoldberg@oxfordra.net`) yields a full admin session via magic link with no second factor — including inviting an attacker-controlled `contact_email` as a portal tenant, rewriting `charges`/`payments` history, and pulling the entire tenant roster.

**Candidate fix (NOT applied):** enroll a TOTP factor on admin accounts and apply the existing `requireAal2` middleware (auth-source-agnostic — validates the presented JWT) to the admin gate, or at minimum to the destructive CRUD verbs and `portal-auth.ts`/`intake.ts`.

**Auto-check:** none.

---

### OI-209

**Status:** OPEN
**Opened:** 2026-08-26 · **Source:** ora-appsec-sweep 2026-08-26 (oxford-command-center @ `eb236c4`, security-auditor dispatch)
**Severity:** MEDIUM (dependency CVE, refresh of a closed bucket)

**Description:** [OI-017](#OI-017) closed 2026-07-26 with oxford-command-center at "9 vulns / 0 critical," explicitly not including a queued non-breaking `npm audit fix` pass. One month later this sweep's `npm audit --json` on the pinned worktree finds advisories not present in OI-017's closure snapshot: **`@hono/node-server ^1.13.7`** — GHSA-frvp-7c67-39w9, path traversal via encoded backslash (`%5C`) on Windows in `serve-static`, fixed at `>=1.19.15` (no `serveStatic` route currently mounted in `server/`, bounding reachability today); and **`react-router-dom ^6.30.4`** — GHSA-jjmj-jmhj-qwj2 (moderate, open-redirect→XSS via `<Link>`/`useNavigate` backslash handling, not present in OI-017's tracked pair GHSA-wrjc-x8rr-h8h6/GHSA-337j-9hxr-rhxg), fixed at `react-router` `>=7.18.0` or a patched 6.30.x. `npm audit` overall: 7 high, 3 moderate, 0 critical — remainder (js-yaml, postcss, nanoid, brace-expansion, fast-uri, sharp/libvips) are dev/build-tooling-reachable only, same class OI-017 already characterized as not urgent.

**Impact:** `@hono/node-server` is a runtime dependency on the served Brain Server (Hono-on-node, Windows host) — the exact affected configuration, live if any static route is added. `react-router-dom` ships in the client bundle served behind Cloudflare Access to the mirror, which shows confidential portfolio data; a crafted deep link against the SPA's `/* -> /index.html` fallback could redirect off-site or, in the XSS variant, execute script in the mirror origin.

**Candidate fix (NOT applied):** upgrade `@hono/node-server` to `>=1.19.15`; upgrade `react-router-dom` to a fixed release (`>=7.18.0`, or patched 6.30.x if staying on v6 — verify no reliance on the removed `deserializeErrors` SSR path). Batch with the deferred OI-017 `npm audit fix` pass (brace-expansion/fast-uri/js-yaml/postcss) as one lockfile-refresh PR, runtime deps first, gated on `npm run gate`.

**Auto-check:** none.

---

### OI-210

**Status:** OPEN
**Opened:** 2026-08-26 · **Source:** ora-appsec-sweep 2026-08-26 (oxford-command-center @ `eb236c4`, security-auditor dispatch)
**Severity:** MEDIUM (resource exhaustion / DoS)

**Description:** `server/ar/pdf-extract.ts:17-34` shells out to Python/pdfplumber over an operator-supplied PDF path with a 10 MB stdout `maxBuffer` but no bound on input file size, page count, or wall-clock — no `timeout` on the `spawnSync`, unlike `brief/send.ts` which sets `timeout: 60_000`. `server/warehouse/om-extract.ts` similarly runs `pdf-parse` on uploaded PDFs with no equivalent cap. A malformed or adversarial PDF (decompression bomb, pathological page tree) can hang or OOM the process.

**Impact:** denial of service / resource exhaustion of the Brain Server via a crafted PDF dropped into the AR inbox or uploaded through the OM extract endpoint. Bounded today to whoever can supply a file — on the current loopback-only deployment that's the operator, but the Phase-2 tunnelled deployment ([[project_ccm_mjs_dmts_parity_and_branch_protection_gap_2026-08-24]] context) widens the reachable surface. Related but distinct from [OI-050](#OI-050) (Host-header/DNS-rebinding on the same server) — that's an auth-bypass finding, this is availability.

**Candidate fix (NOT applied):** add a `timeout` (mirror `send.ts`'s 60s) to the `spawnSync` in `pdf-extract.ts`, plus a pre-flight file-size stat cap and, where pdfplumber allows, a page-count cap. Keep `maxBuffer` as the last-resort ceiling. Apply the same discipline to `om-extract.ts`.

**Auto-check:** none.

**Related:** `projects/C--Users-Owner-oxford-command-center/memory/collections-ar-feed-pending.md` (the upstream feed item — a different project's memory dir, so deliberately NOT a `[[wikilink]]`, which would dangle from here), `ora-ar-feed-sweep` SKILL.md §"How the review queue actually gets resolved".
