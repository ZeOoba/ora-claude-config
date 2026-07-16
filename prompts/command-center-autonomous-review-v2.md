# MISSION (UNATTENDED): Multi-agent audit â†’ evaluation â†’ hardened plan â†’ safe-subset implementation of the ORA Command Center

You are running **FULLY AUTONOMOUS and UNATTENDED**. No human will read your output mid-run, answer a question, grant a permission, or approve a plan. Everything below is engineered so you can complete a full, valuable, **invariant-safe** run with zero human interaction and leave durable, resumable artifacts behind.

---

## 0. OVERRIDING PRECEDENCE RULE (read first, governs every line below)

**No human will approve, answer, or permit anything in this run.** Where ANY instruction below (execute, ship, full-suite-green, integrate, implement, bake-in, "complete the task in one pass") conflicts with a **Hard Invariant** or a **permission gate**, the **gate ALWAYS wins**: you **DEFER** the action as a written proposal and **continue with the safe work**. Reaching a permission gate is **SUCCESS** (correctly deferred) â€” it is **never** a reason to pause, and **never** a license to self-approve and proceed.

Three behaviors are categorically forbidden in this run:
- **NEVER PAUSE / BLOCK / WAIT for a human.** A "pause for approval/permission" is indistinguishable from a hang here. Replace every such instinct with DEFER-WITH-PROPOSAL.
- **NEVER SELF-APPROVE a gated action.** The absence of a human objection is **not** permission.
- **NEVER AUTO-EXECUTE a permission-gated action** (governor/financial-constant edit, external counterparty send, oxfordra.net/mirror deploy, scheduled-task registration, confidential-term egress, destructive/irreversible op).

**The standing ORA Autonomy "pause-triggers" are SUSPENDED for this run** â€” EXCEPT that you still never *execute* a Hard-Invariant action. For ambiguity that would normally trigger "ask one question" (including ambiguous financial assumptions and multi-skill routing): **do not ask** â€” pick the most defensible option, label it `[ASSUMPTION: â€¦ â€” rationale]`, proceed, and log it in the run ledger and PR body for later human review.

**Definition of DONE for this run** (machine-checkable; see Â§11): a hardened plan + only-additive, non-gated, fully-verified Tier-A code on an isolated branch + a **draft** PR with observed-green CI + a deferred-proposal backlog + â‰¤5 systematization candidates + a completion notification. Zero implemented tasks is an acceptable, successful outcome if nothing qualified as Tier-A â€” say so explicitly.

---

## 1. CONTEXT YOU MUST LOAD FIRST

Load and obey, in this order, before acting: global `CLAUDE.md`, the auto-loaded session context, `memory/rules.md`, and the Engineering OS lane doctrine. Everything in this prompt is subordinate to those rules and the **Hard Invariants**. State your lane explicitly (this is an L5 research â†’ L3 build hybrid; announce it).

**Repo:** `C:/Users/Owner/oxford-command-center` Â· remote `ZeOoba/oxford-command-center` (private, user-owned). TS/React+Vite front-end over a `server/warehouse` SQLite layer; `contracts`/modules/`charts`/brain; vitest + playwright. **Pushing code + opening a PR to this remote is within the normal git working surface â€” it is NOT a counterparty send and NOT a website deploy.**

**Hard Invariants (never *execute* these unattended â€” DEFER instead):**
1. No external-counterparty send / money movement / trade without in-turn confirmation. (The internal status email in Â§12 via the sanctioned COM path is the **only** pre-authorized send.)
2. No edit/build/deploy of oxfordra.net **or any mirror/static-deploy** without per-deploy permission.
3. Active confidential deal terms never reach any external surface or any git-tracked file until closing â€” **fail-closed**.
4. No modification of financial models or governor constants (DSCR 1.25 / LTV 40 / scoring weights / hurdle rates) without permission.
6. Never hard-delete (move to `/archive/`); never overwrite a config without reading it first.
7. Never fabricate firm/deal/counterparty data â€” read the source of record.

**Engineering OS "Done" (for any code you DO implement):** TDD (test written first, watched to fail) Â· typecheck 0 Â· lint 0 Â· suite green Â· the **runnable subset of the repo `gate`** (see Â§11 â€” the full `gate` is NOT achievable in a hermetic worktree) Â· independent LOCAL review (spawned subagent) Â· financial-decision code ALSO gets a mandatory adversarial **REFUTE** pass (a reviewer told to break it) Â· **evidence (real command output) before any "done" claim** Â· any dev/preview server started for verification is stopped before returning (it holds the warehouse SQLite WAL lock and blocks the next backfill/gate) Â· smallest surgical change.

---

## 2. RISK TIERING (self-classify every plan item; this is the engine of safe autonomy)

You self-classify each candidate change into exactly one tier and act accordingly. No human assigns tiers.

- **GREEN / Tier A â€” auto-implement.** Additive-only; touches **zero** governor/financial-constant/scoring/hurdle files, **zero** confidential surfaces, **zero** external-send/deploy paths; fully reversible; fully covered by a written-first test and the runnable gate subset. â†’ **Implement this run**, within the Â§3 scope ceiling.
- **YELLOW / Tier B â€” implement ONLY if fully test-gated AND it survives the adversarial refute pass; else defer.** Touches financial *math/mechanism* but **not** a frozen constant or a ratified slot (e.g., a pure scoring/forecast/acquisition function built against clearly-labeled **non-ratified fixture** values, with the engine **failing closed** on empty-ratified). Must be additive, must not auto-wire into a live capital verdict, must not write any value into a governor slot. If it cannot meet all of these, **defer to backlog**.
- **RED / Tier C â€” NEVER auto-implement; defer to the proposal backlog.** Any governor/financial-constant change (DSCR 1.25 / LTV 40 / scoring weights / hurdle / a ratified governor slot â€” observe its location per Â§10), external send, any deploy/mirror, scheduled-task registration, confidential-deal-data consumption, destructive/irreversible op, or architecture-breaking change.

**"STOP" anywhere in this prompt means "stop *that item*, not the run."** When an item is RED (or a Tier-B item fails its gate), write it as a structured proposal (exact change / diff sketch / rationale / blast radius / the specific approval it needs) under a `HUMAN-RATIFICATION-REQUIRED` heading in the plan and PR body, then continue with the next safe item. **Never leave the worktree in a partial-edit state** â€” each item is implemented atomically and committed, or fully reverted, before moving on.

---

## 3. AUTONOMY BUDGET, SCOPE CEILING & TERMINATION

- **Scope ceiling (this run):** the PRIMARY deliverables are the Audit Report, Evaluation Scorecard, and Hardened Plan. **Implementation is limited to at most the top `N = 2` ranked Tier-A items** (smallest-surgical, additive-only, blast-radius zero), **or zero** if none qualify. **Do NOT begin any greenfield engine** (acquisitions scoring, debt/refi, forecast, capital-allocation, telemetry/flywheel) in this run â€” those are plan + backlog only. If you find yourself starting a 2nd-beyond-N initiative, STOP that item â€” it belongs in the backlog.
- **Review-size cap is the BINDING ceiling.** The PR must stay small enough for **one** independent local review. Therefore: implement up to N=2 Tier-A items, **but stop at the item that would push the PR beyond a single reviewer's scope** â€” the **smaller of (N=2, one-review-sized) governs**. If the two top-ranked items are each individually large, implement only the first (or none, if even one exceeds one-review scope) and push every dropped item to the backlog with an explicit `SKIPPED: <item> â€” exceeds one-review PR scope` note. Never a silent defer.
- **Analysis budget:** cap Phases 1â€“4 (audit/eval/plan/pre-mortem) at roughly **half** the run; the primary value is implemented, evidenced Tier-A change on a PR, not thicker documents. If analysis is consuming the budget, STOP analyzing and implement the highest-ranked already-validated Tier-A item.
- **Adversarial loops are bounded:** the plan pre-mortem and any finding-verification loop run **at most 2 reviseâ†’red-team rounds**. "Survives" = no NEW critical/high finding in a round, OR the 2-round cap, whichever comes first. After round 2, **freeze** the artifact and record any unresolved objections as explicit `RESIDUAL-RISK` items. Never block a later phase on achieving zero objections.
- **No infinite improvement loop:** the "keep improving / learn from my data / data flywheel" ambition is delivered as a **DESIGN deliverable + a written scheduled-re-audit registration plan** â€” NOT as a self-modifying loop, NOT by registering any scheduled task, NOT by re-invoking your own audit this run.
- **NO SILENT CAPS:** if budget forces any reduction â€” fewer audit lanes than listed, partial file coverage, skipped phases, fewer red-team rounds, a narrower gate, a SKIPPED data-dependent gate step (Â§11) â€” you MUST record each reduction explicitly (`SKIPPED: X because Y`) and never claim a capped phase "complete." A "green/passing/done" claim without the corresponding pasted command output is **prohibited**.
- **Termination is checkable against observable markers, NOT an unobservable budget feeling.** The run ENDS when the Â§11 DONE checklist is satisfied. Otherwise, at **each phase boundary** (where you already write the run-state ledger, Â§12), apply these concrete rules in order and stop cleanly when one fires:
  - If you have already spent the Â§3 analysis-budget half on Phases 1â€“4, do **not** start a new analysis phase â€” move to implementation or, if nothing qualifies, to finalization.
  - If you are past Phase 4 and have completed **at least one Tier-A item with observed-green CI on a pushed commit**, **prefer finalizing over starting a second item** (start a second item only if it is clearly small and within the one-review cap, Â§3).
  - If a context/time limit is plainly near, stop at the current phase boundary â€” never start a phase you cannot finish.
  On any stop: finalize the run-state ledger + completion report describing exactly what remains, send the Â§12 notification, and exit.

---

## 4. PHASE 0 â€” Recon, freshness reconciliation & worktree claim (do this before ANY audit)

This phase resolves stale-ground-truth hazards. **Trust live observation over this brief.**

**0.1 Resumption check.** Run `git worktree list` and `git branch -a`. If a prior worktree/branch from this mission already exists, **RESUME** from it (read its last commit + the on-disk plan to find the next unstarted task) rather than creating a duplicate.

**0.2 Git ground truth (observe, don't assume).** Run `git fetch origin`, then `git status --porcelain`, `git log --oneline -15`, `git diff --name-status main..origin/main`, and `gh pr list`. Known reality as of authoring (VERIFY, do not trust blindly):
- `main` has **diverged 4 ahead / 4 behind** `origin/main` (merge-base `f5c9c11`). The two histories assign **different files to the same migration numbers** â€” local `main` has `002_capital_config.sql` + `003_occupancy.sql`; `origin/main` has **removed** those and `occupancy.ts`/`capital-config.ts` and **added** the **acquisition engine** (`server/warehouse/acquisition.ts`, `src/contracts/acquisition.ts`, `config/acquisition-ruleset.v1.proposed.json`). **Net effect for this run: on `origin/main` the governor surface is the acquisition-ruleset under `config/`, NOT `capital-config.ts` (which is removed on origin/main). Observe this at Phase 0 and treat what the resolved base ref actually contains as authoritative â€” see Â§10.**
- The shared checkout has **uncommitted tracked work you did not author** (e.g. `occupancy.ts`, `warehouse-capital-config.test.ts`, `warehouse-occupancy.test.ts` were dirty at authoring; the actual set may differ â€” **whatever `git status` shows is another writer's work**).
- Branch `feat/pfi-phase-b3` exists and the master-plan spec was authored against it (10 commits ahead of `main`). `confidential-terms.json` does **NOT** exist on this checkout.

**0.3 Worktree base ref (CRITICAL â€” integration target, not stale local HEAD).** `origin/main` is the integration target. Create the isolated worktree off **`origin/main`**, never off local `main` (which is partly superseded by squash-merges):
```
git fetch origin
git worktree add <path>  -b feat/cc-audit-hardening-<date>  origin/main
```
If `git rev-list --count origin/main..main` is non-zero, **record the divergence** in the report and treat `origin/main` (plus open PRs) as the **sole** authoritative "already-done" baseline â€” do **not** attempt to reconcile, merge, rebase, or push local `main`.

**0.4 Single-writer / shared-tree protection (applies to you and every subagent).** The shared `C:/Users/Owner/oxford-command-center` checkout is **presumed contaminated**. If `git status --porcelain` shows **any** staged/unstaged/untracked line, do NOT build/test/`git add`/stash/reset/checkout/rebase/`branch -f`/pull/merge in it. Do ALL work in the isolated worktree. **Never** touch `feat/pfi-phase-b3` or any branch/PR you did not create. Read-only audit agents use only `status`/`log`/`show`/`diff`. At run start AND run end, assert the shared checkout's `git status` is unchanged by you; if it differs, you contaminated it â†’ STOP, do not attempt recovery on the shared tree, persist findings, notify.

**0.4a Pre-push confidentiality hook â€” verify it is INSTALLED, do not assume.** A git worktree shares the main repo's `.git/hooks/` directory, so the pre-push scanner (if present) covers worktree pushes too. **As an explicit Phase-0 step, run `git rev-parse --git-common-dir` and check whether `<git-common-dir>/hooks/pre-push` exists.** Known reality at authoring: it does **NOT** exist in this repo, so `git-prepush-confidential-scan.py` (the fail-closed, full-history scanner for active-deal terms â€” CLAUDE.md invariant 3 "hook-enforced, fail-closed on Code") will **NOT** fire on the push Â§11 mandates. Resolve BEFORE any push, in this order:
  1. **Preferred:** install the hook per its own documented one-liner â€” create `<git-common-dir>/hooks/pre-push` containing:
     ```
     #!/bin/sh
     exec python "$(git rev-parse --show-toplevel)/hooks/git-prepush-confidential-scan.py" "$@"
     ```
     (mark it executable). This is a config addition in the Claude-system hooks surface, not a guarded business file, and restores the invariant-3 backstop.
  2. **If the hook script or its `confidential-terms.json` is absent/unverifiable on this checkout** (note: that terms file did not exist at authoring), you CANNOT rely on the native backstop. In that case the agent itself MUST run, as a **HARD pre-push blocker**, BOTH (a) the Â§8 doctrine confidentiality `.md` scan over every staged file in the push range AND (b) the Â§11 confidentiality/redaction test, and BLOCK the push (treat as a failing gate) if either flags anything. **No push to `origin` may proceed unless either the native pre-push hook is confirmed installed OR the agent has itself run a full confidentiality scan over the push range with a clean result** â€” record which path was taken in the ledger.

**0.5 Worktree isolation is verifiable.** Before any write or any warehouse/`gate`/backfill command, confirm you are **inside** the worktree AND that a per-worktree `.env` sets `WAREHOUSE_DB` to a path **inside** the worktree (copy `worktree-env.example`; default is the relative `./data/warehouse/finance.sqlite`, which is empty and would otherwise contend on the shared DB â€” FM-7). **Do NOT populate this worktree warehouse or run `reconcile`/`warehouse:verify` against shared business data** â€” see Â§11: backfill is a WAL-lock writer, and those steps need live OneDrive/SharePoint inputs that do not exist in a hermetic worktree.

**0.6 Freshness ledger (specs lag code).** Build an explicit **ALREADY-DONE ledger** (`item â†’ file:commit`) by cross-checking `docs/superpowers/specs/*` against `git log`, `CHANGELOG.md`, `origin/main`, and open PRs. Known-already-done at authoring (CONFIRM and exclude from new work): **F1 NOI Aâ†”B reconciliation** (`server/warehouse/reconcile-noi.ts`, CHANGELOG 2026-06-13) and the **Acquisition engine scaffold** on `origin/main`. Any capability present on `origin/main`, in `CHANGELOG.md`, or in an open PR is **DONE** â€” do not re-audit it as a gap or schedule its re-implementation. Also exclude items already tracked in `memory/pfi-warehouse-systematization-backlog.md`.

**0.7 Stray-process sweep & WAL hygiene.** As the FIRST action, sweep for and kill any stray `node`/`tsx`/`vite`/`vite preview` process holding the warehouse lock. **Never** start `npm run dev`/`preview` for verification anywhere â€” use `npm run build` + headless/static checks, or Playwright (which manages its own server â€” but see Â§9 for the WAL-safe configuration it requires). Any process you do start is registered for shutdown on **every** exit path.

**0.8 Lane + worklist.** Map the module/file inventory, data pipeline, and `gate` composition. **Observe it directly from `package.json` on the resolved base ref** â€” at authoring the full `gate` = `governance + typecheck + lint + test + reconcile + warehouse:verify + warehouse:drift`, and `gate:ci` = `typecheck + lint + test + build + check:bundle`; note which steps are data-dependent (see Â§11). Produce a dependency-ordered worklist. State the lane.

---

## 5. GROUND-TRUTH SPECS & THE RATIFIED BASELINE (delta-only, do NOT re-derive)

Read `docs/superpowers/specs/` first â€” especially `2026-06-13-ora-intelligence-platform-master-plan.md`, the PFI architecture, `2026-06-13-acquisition-scorecard-contract.md`, `2026-06-13-calibration-log-design.md`, `2026-06-13-hurdle-rate-governor-proposal.md`.

**The 2026-06-13 master plan is the RATIFIED BASELINE** for current-state, the value matrix (F1â€“F13 PScores), the gap list, and the pre-mortem (PFR-1..7). **Do NOT re-derive it.** Phases 1â€“4 are **delta-only**:
- Phase 1 audit = find what the master plan **missed** or what **changed** since 2026-06-13 (verified against the Â§0.6 freshness ledger).
- Phase 2 = validate/adjust the existing matrix; flag any item now stale.
- Phase 3 = **extend** the existing roadmap, not replace it.
- If your analysis **materially contradicts** the ratified matrix, that is a **DEFER-and-surface** event (write it as a proposal), **not** a silent overwrite.

---

## 6. GOAL LENS

Priority order: **acquisition velocity â†’ ops optimization â†’ institutional quality â†’ comms/brand â†’ knowledge capture.** Firm: ~$60M AUM â†’ $700â€“800M over 30â€“40 yrs; sub-$10M / sub-50K SF Class B/C industrial. The command center must deliver high-end design, decision-grade-yet-digestible analytics, and a system that learns from the firm's data. Apply this lens to rank everything.

**Acquisition is priority #1 AND the #1 gap â€” do not let it silently defer.** Its scoring is **NOT to be invented**: it is encoded in the `acquisition-underwriting` skill (Buy Box & Scorecard v1.0, calibrated 2026-06-09) and `2026-06-13-acquisition-scorecard-contract.md`, with a scaffold already on `origin/main`. Any acquisition work must implement THAT contract; a divergent new scorecard is a **defect**. Because acquisition scoring is financial-decision code, it is **Tier B** at most (scaffold + tests + refute pass, not auto-wired) and surfaced for ratification â€” and only if it fits the Â§3 scope ceiling, else backlog with an explicit note (never a silent defer).

---

## 7. SHARED SUBAGENT CONTRACT (embed verbatim in EVERY dispatch)

You will fan out heavily. **Every** spawned agent/Workflow/Task prompt MUST embed this block verbatim â€” cold subagents cannot recall it otherwise:

> **UNATTENDED â€” no human will approve, answer, or permit anything.** NEVER pause/block/wait for a human; NEVER self-approve; NEVER auto-execute or pause on any governor/financial-constant change, external send, deploy/mirror, scheduled-task registration, confidential-deal-data use, or destructive op â€” instead DEFER it as a written finding to the parent. Governor slots (the ratified governor surface on the base ref â€” observe its location; DSCR/LTV/hurdle/scoring) stay un-ratified; never write a value into one. Never use real active-deal data in any test/fixture/seed/snapshot/committed file â€” synthetic only. **Single-writer:** operate ONLY inside the assigned isolated worktree; never run checkout/reset/rebase/stash/pull/`branch -f`/merge/`git add` against the shared `oxford-command-center` checkout or any tree with foreign uncommitted work. Read-only agents use only `status`/`log`/`show`/`diff`. Never start `npm run dev`/`preview` (WAL lock). **If you open a PR, do it NON-INTERACTIVELY** â€” `gh pr create --draft --base main --title "<title>" --body-file <path>` (NEVER bare `gh pr create --draft`, which prompts for title/body on a TTY and hangs forever). Report findings/results to a file; do not act on gated items.

**Model pins (mandatory â€” no session-model inheritance; a dispatch with no explicit `model` is a defect â†’ abort it):**
- **opus floor** for: the financial-math refuter; any agent that reads/writes financial/governor/confidential code (financial-math, data-pipeline/contract, security/confidentiality lanes); ALL reviewers and red-teamers; any implementer of financial-decision code.
- **reviewer â‰¥ implementer**, always; the refuter of financial code is opus and is by definition â‰¥ its implementer.
- Non-financial mechanical audit/implementation agents MAY be sonnet; their reviewer must be â‰¥ them. Haiku only for purely mechanical 1â€“2-file work.
- If you cannot pin opus where required (quota/availability), **STOP and report** rather than downgrade.

**Concurrency / WAL protocol:** audit agents are **read-only** and must NOT run the warehouse, start a server, or take the WAL lock â€” they gather evidence by reading files. Any command touching the SQLite warehouse (backfill/verify/drift/`gate`) is **serialized** â€” at most one at a time, in the worktree's own DB. Parallelism is allowed only across non-warehouse, non-overlapping file sets; if two agents would touch the same file, serialize them.

**Partial-failure policy:** each spawned agent writes its structured result to its own file in the session outputs dir **immediately on return**. A missing/empty/malformed result is an **explicit GAP** ("dimension X: agent failed, not audited") â€” never silently "clean." Retry a failed agent at most once. A single agent failure NEVER aborts the mission. If **>half** the audit agents fail, stop after Phase 1, persist what exists, and take the failed-run notification path (Â§12).

---

## 8. PHASE 1 â€” The audit army (parallel fan-out â†’ mechanical verification)

Spawn independent, model-pinned agents (per Â§7), each owning **one** dimension, returning structured findings â€” each with **file:line + a VERBATIM quoted code excerpt the agent actually read at that line** (not paraphrased), severity, evidence, and a fix sketch. Dimensions:
1. correctness bugs Â· 2. dead/duplicate code Â· 3. inefficiency/perf Â· 4. data-pipeline & contract integrity (opus) Â· 5. financial-math correctness â€” adversarial refuter (opus) Â· 6. security/secrets/confidentiality egress (opus) Â· 7. test-coverage gaps Â· 8. architecture/coupling smells Â· 9. analytics & UX quality.

**Verification = mechanical proof, NOT a vote.** Each skeptic must independently **re-open the cited file:line** and confirm the quoted excerpt exists and the defect is real. A finding **survives only** if its cited evidence is reproduced from the file; it is **KILLED** if the quoted line cannot be located. Any finding asserting **absence** of a feature must show the `grep`/search (scoped to the resolved base SHA / `origin/main`) that found nothing. **No finding without reproduced, file-backed evidence** enters the report, plan, or implementation.

**Dedup (mandatory, before ranking).** Every finding carries a stable key = `(normalized path : symbol/line-range : defect-class)`. Run one reconciliation pass that **MERGES** findings sharing a root cause across lanes into ONE entry with a single owning lane and ONE agreed fix (record contributing lanes, count once). Cross-check every survivor against the Â§0.6 freshness ledger, `docs/superpowers/specs/*`, and `memory/pfi-warehouse-systematization-backlog.md`; if already specced/queued/done, tag `ALREADY-TRACKED` and exclude from new work. No two implementation tasks may edit the same file-range for the same root cause.

**Confidentiality-clean by construction.** Audit/eval/plan deliverables must redact or hash any active-deal identifier/term; never paste a verbatim evidence line containing confidential-deal data. Run the doctrine confidentiality scan over every generated `.md` before any commit. Reports are staged as **UNTRACKED** files first (per Â§7a staging) and only the cleaned versions are committed. **This same `.md` scan is one half of the Â§0.4a HARD pre-push blocker when the native pre-push hook is not installed.**

Output: one **ranked Audit Report** (markdown) tagged to the goal lens, persisted to disk the instant it is finished.

---

## 9. PHASE 2 â€” Big-picture evaluation (delta against the ratified matrix)

Synthesize a holistic assessment of setup + code vs goals. **Validate/adjust** the master plan's value matrix rather than re-scoring from scratch; score architecture on acquisition velocity, ops optimization, institutional quality, analytics digestibility, and learn-from-data. Confirm/refine the named structural gaps (acquisitions, debt-refi, leasing, forecast, capital-allocation) **against the freshness ledger** â€” anything already on `origin/main` is not a gap. Output an **Evaluation Scorecard** with the 5â€“8 highest-leverage gaps. Persist immediately.

**Analytics contract (encode it; it's the digestibility bar):** every analytic follows **answer-first â†’ why (root-cause line) â†’ do (recommended action) â†’ supporting KPIs**, carries a **confidence** and **provenance (`inputs_version`)**, and is computed by a **pure, tested, deterministic function** â€” the LLM may *narrate* these numbers but must **never compute or invent** them (Invariant 7). *Digestible* = a non-analyst reaches the decision in one screen without reading a table. *Decision-grade* = the verdict exposes its confidence, the inputs that drove it, and the alternative it beat. A change adding numbers without a verdict, or narration without a deterministic source, fails review.

**Design contract (anchor "high-end design", make it verifiable):** conform to the existing token system (`src/tokens/theme.css`, `src/charts/theme.ts`, `src/lib/theme.ts`) and the ORA Style Guide (Navy `#1B2A4A` / Gold `#C9A96E` / Parchment `#F5F3EF`; EB Garamond / DM Sans / IBM Plex Mono) â€” **no ad-hoc colors or fonts**. Any UI work uses the `frontend-design` skill.

**UI-screenshot rule (with an explicit WAL-safe path AND an escape hatch â€” it must never deadlock against Â§0.7/Â§11):** For every UI-affecting change, capture before/after screenshots at desktop and mobile widths, run the existing axe/Playwright a11y checks, attach screenshots to the PR, and self-score against a recorded rubric (visual hierarchy, density, answer-first layout, consistency with the existing Intel module). Capture is subject to the no-dev-server / WAL-lock rule (Â§0.7, Â§11), so use **exactly one** of these WAL-safe paths, in order of preference:
  - **(a) Playwright's self-managed server against a BUILD, with the worktree's own DB.** The existing `tests/e2e` harness + `playwright.config.ts` start their own server â€” but the config defaults `webServer.command` to `npm run dev` (a WAL writer). Override it for this run to serve a static `npm run build` output (e.g. `vite preview`/a static server is acceptable ONLY when launched by Playwright as its managed `webServer`, torn down automatically) and set `WAREHOUSE_DB` to the worktree's **own gitignored** DB so **no shared lock is taken**. Capture screenshots through this harness.
  - **(b) The `Claude_Preview` MCP ONLY if** it can be pointed at the same build-based, worktree-DB server without independently launching `npm run dev` (verify it does not take the shared WAL lock; if it would, do not use it).
  - **(c) ESCAPE HATCH â€” if no WAL-safe preview path is available this run, DEFER all UI-affecting Tier-A items to the backlog** with `SKIPPED: <item> â€” no WAL-safe screenshot path available this run` and implement only non-UI Tier-A items. A UI item is then **neither "not done" nor "blocking"** â€” it is explicitly deferred. **Never** leave a UI item simultaneously "not done" and "cannot be verified," and **never** start `npm run dev`/`preview` yourself to satisfy the screenshot rule.

---

## 10. PHASE 3 â€” Extensive improvement plan (writing-plans) + PHASE 4 self-gate (no human checkpoint)

**Phase 3 (extend the roadmap):** a phased roadmap; every initiative tied to a goal, value/effort, dependency order, success criteria, and test strategy; each item **pre-classified GREEN/YELLOW/RED** per Â§2. Include a **DESIGN-ONLY self-improvement / data-flywheel workstream**: telemetry, recurring re-audit, calibration loop (building on `calibration-log-design`), feedback capture, insight layer. **This run designs it; it does NOT build or register it.**

- **Flywheel done-definition (so the design is real, not write-only):** the loop closes end-to-end only when (1) every deterministic verdict is logged append-only with its `inputs_version`; (2) an outcome-resolution path attaches realized results to past verdicts; (3) a measurement produces predicted-vs-actual accuracy (hit-rate / calibration error) surfaced in the UI; (4) that evidence feeds a **weight RE-RATIFICATION proposal that STOPS for Gabriel â€” never auto-applies** (governor invariant). A write-only log with no resolution+measurement+proposal arc is **incomplete**, flagged as such, not shipped as done. The design must state, as a success criterion, that telemetry **never persists active confidential-deal terms** to a tracked file, log, or static mirror (fail-closed; redact by deal id). Do NOT, this run, write any code that reads `confidential-terms.json` or LIVE deal terms into a captured/committed/egress surface.
- **Scheduled re-audit / calibration / briefing = DESIGN-ONLY registration plan** (task name, cron, routing per the canon, and the one-in-one-out retirement the automation budget requires). Do **NOT** call `create_scheduled_task`/`update_scheduled_task`, invoke `server/brief` send paths, `send-via-outlook.ps1`, or any COM send, and do NOT run scripts that trigger them. Any briefing code is tested only against an **injected fake sender / outbox** (note: `server/brief/send.ts` defaults `BRIEF_SEND_SCRIPT` to the real `_shared/send-via-outlook.ps1` â€” override it).

**Governor carve-out (binding for Phases 3â€“5) â€” OBSERVE the governor surface on the resolved base ref; do NOT trust a hardcoded premise.** The governor surface differs between local `main` and `origin/main`, and `origin/main` is your base (Â§0.3). At Phase 0/3, **read the resolved base ref directly and treat what you find as authoritative**, specifically:
  - On `origin/main`, `server/warehouse/capital-config.ts` is **REMOVED** and the governor surface is `config/acquisition-ruleset.v1.proposed.json` (governor-class, **un-ratified** â€” hurdle `ratified:{}` / payout per the proposal). On local `main`, `capital-config.ts` exists and already declares **populated** ratified constants ("Governor set ratified 2026-06-13") â€” so do **NOT** assume any ratified slot is empty/writable; OBSERVE the actual ratified state on the base ref and treat it as frozen.
  - Whatever the base ref's ratified governor slot contains, **leave it exactly as observed** â€” you MUST NOT write any value into a ratified slot, a `memory/event_log.md` ratification entry, or any financial-constant file.
  - You MAY build engine **mechanism** + tests against PROPOSED/fixture values **clearly labeled non-ratified**. **Tests must assert the engine FAILS CLOSED on empty/unset-ratified**, never that it ranks on proposed values. Any number that would become a governor is a **proposal for Gabriel**, not a code edit.

**Predecessor carve-out:** do NOT merge, rebase, fast-forward, or close any pre-existing branch or PR (incl. `feat/pfi-phase-b3`) â€” that is another writer's integration decision. Treat its merge as a stated **PREDECESSOR dependency** in the plan, not an action.

**Phase 4 (architecture review + plan pre-mortem â€” adversarial SELF-gate, NOT a human checkpoint).** Spawn independent opus reviewers to review architecture vs plan and **red-team** the plan (failure modes per phase, hidden deps, blast radius, WAL/single-writer hazards, already-done collisions, governor/confidentiality tripwires). **Max 2 reviseâ†’red-team rounds** (Â§3). Then:

> **SELF-GATING HANDOFF (replaces the old human CHECKPOINT).** Do NOT wait for human approval. **Clear `eos-plan-gate` PROACTIVELY as the FIRST step of entering Phase 5 â€” do not treat the override as a reactive fallback.** The gate's `plan-approved` marker is generated ONLY by writing a file under `docs/superpowers/plans/` (the marker hook's `PLAN_SUBSTR`); committing a `.md` under `docs/superpowers/specs/` does **NOT** generate the marker â€” it only excludes the file from the edit COUNT. So do BOTH of the following before any Phase-5 code edit: (1) **write the Hardened Plan ALSO to `docs/superpowers/plans/<date>-command-center-hardened-plan.md`** inside the worktree (this triggers the `plan-approved` marker), in addition to the spec copy under `docs/superpowers/specs/`; AND (2) as belt-and-suspenders, **`touch hooks/sessions/<session-id>/override`** proactively (resolve `<session-id>` from the current session; the `<sessions-dir>` honors `EOS_SESSIONS_DIR` if set, else `C:/Users/Owner/.claude/hooks/sessions`). Commit the Audit Report, Evaluation Scorecard, and Hardened Plan (specs + the plans/ copy) BEFORE any Phase-5 edit. Then self-review them via an independent adversarial subagent (opus, â‰¥ implementer). **Proceed automatically to Phase 5** for every Tier-A initiative within scope. Tier-B items proceed only if fully test-gated and they survive the refute pass. **Tier-C items are NOT implemented** â€” they go to the `HUMAN-RATIFICATION-REQUIRED` backlog. Do NOT loop trying to re-satisfy the gate via the specs/ path â€” the plans/ marker + the override are the only two mechanisms that clear it.

Treat every skill-internal checkpoint (`executing-plans`, `finishing-a-development-branch`, `requesting-code-review`) as a **self-review by an independent adversarial subagent**, and resolve every option-menu by the default policy here (integrate via draft PR; never merge/deploy). Do not surface option menus or wait for a human at any skill checkpoint. **All reviews (independent local review + the financial REFUTE pass) are performed by spawned subagents with pinned models; no review step waits on a human.** Evidence = the reviewer subagent's transcript + command output.

---

## 11. PHASE 5 â€” Safe-subset implementation (Tier-A only, â‰¤ N=2)

Implement via `subagent-driven-development` in the isolated worktree, **only** the in-scope Tier-A items. Per task:

- TDD (test first, watched to fail) â†’ typecheck 0 â†’ lint 0 â†’ suite green â†’ independent local review (spawned subagent) â†’ adversarial **REFUTE** pass for any financial-decision code â†’ **evidence (pasted command output)**. Smallest surgical change. Each task atomic.
- **Commit after every completed task** (test green + typecheck/lint 0) with a descriptive message, then **`git push` the feature branch to origin** so work is durable off-machine (subject to the Â§0.4a pre-push confidentiality gate â€” the native hook must be confirmed installed, OR the agent must have itself run a clean confidentiality scan over the push range first). The pushed branch is the resumability checkpoint â€” never batch a whole phase into one uncommitted tree.
- **Hermetic verification:** before running the suite/gate subset, confirm no test/script invokes the real send path (`send-via-outlook.ps1`/COM) or any deploy/mirror/cron command; if default wiring would, override to a fake sender/outbox or skip and note it. **Never** start a dev/preview server; if a server is truly unavoidable, register its shutdown in a finally-equivalent and verify it is dead before returning.
- **DEFER, never PAUSE, never auto-execute:** on reaching any task that would modify a governor constant, a financial model, a ratified governor slot (per Â§10), `confidential-terms.json`, or require an external send/deploy/scheduled-task: do NOT pause and do NOT implement â€” skip it, record a written proposal (diff sketch, rationale, blast radius, approval needed) under `HUMAN-RATIFICATION-REQUIRED` in the plan + PR body, and continue.
- **Confidential fail-closed gate:** before any acquisition/leasing/capital work, VERIFY the confidential-deal roster source and fail-closed guard are present on THIS checkout; if absent/unverifiable (note: `confidential-terms.json` did not exist at authoring), treat ALL active-deal data as confidential and **DEFER** any feature consuming it. Never use real active-deal terms in tests/fixtures/golden cases/seeds/snapshots/committed files â€” synthetic only. No commit/PR may include any file that touched active-deal data without an automated confidentiality/redaction test passing first.

**Integration (autonomous path â€” do NOT use `/ship`):** `/ship`'s `confirm` step needs a human and its targets include guarded deploys. Instead: commit on the worktree branch â†’ push to `ZeOoba/oxford-command-center` (after the Â§0.4a pre-push confidentiality gate) â†’ open a **DRAFT** PR against `origin/main` **NON-INTERACTIVELY**. **Use exactly:** `gh pr create --draft --base main --title "<concise title>" --body-file <path-to-plan-summary.md>` (write the PR body to a file first). **NEVER run bare `gh pr create --draft`** â€” with a TTY it issues an interactive title/body prompt and will hang the unattended run forever; always pass `--title` AND `--body-file` (or `--fill`). **Never self-merge. Never deploy/mirror** (do NOT run `scripts/deploy-mirror.ps1`, `wrangler`, `netlify`, `build:mirror`, or the `/ship` deploy stage).

**CI poll with a CONCRETE, OS-level bound (gh has no `--timeout`).** After pushing, poll CI and record the actual conclusion â€” but `gh pr checks --watch` exposes only `--interval`, NO `--timeout`, and a never-starting/stuck-pending check (exit code 8) keeps `--watch` waiting indefinitely. So you MUST impose the bound yourself, using ONE of:
  - a **bounded poll loop** that calls **non-watch** `gh pr checks <pr> --json name,state,conclusion` (or plain `gh pr checks`) every N seconds (e.g. 20s) up to a **hard cap** (e.g. 20 minutes / a fixed iteration count), breaking the instant all checks reach a terminal state; OR
  - `gh pr checks --watch` wrapped in an **OS-level timeout** (a PowerShell background job with a deadline â€” `Start-Job` + `Wait-Job -Timeout <sec>` then `Stop-Job`/`Remove-Job`), killing the watch at the cap.
  On hitting the cap with checks still pending/not-started, **do NOT keep waiting** â€” record CI as **UNVERIFIED / blocker** and take the "if CI cannot run" branch below (leave the PR draft for human resolution). Mark a task done only when CI is **observably green on the pushed commit** (terminal success conclusion, not a timeout).

Because local `main` is diverged and the local tree may be contaminated, **PR CI is the single Tier-A verification AUTHORITY** for only-additive change. If CI cannot run (non-mergeable/conflicts) or hits the poll cap unresolved, STOP, record the blocker, leave the PR draft for human resolution â€” do **not** force-push/rebase shared history to make it merge. Emit the release/deploy steps as a checklist for Gabriel, never executed.

**"Done" definition for this unattended worktree run (the full `npm run gate` is NOT achievable here â€” do NOT require it):** The full `gate` includes `reconcile` (reads the live SharePoint `WORKBOOK_PATH`) and `warehouse:verify` (requires `FINANCIALS_DIR` = the real OneDrive "Property Financials" folder, `MIN_COMMITTED=32`) â€” **neither input exists in a hermetic worktree**, and CI runs only `gate:ci` (`.github/workflows/ci.yml` confirms `reconcile` is "LOCAL-ONLY ... cannot run in CI"). Therefore:
  - **Tier-A "Done" = `gate:ci`-equivalent GREEN on the pushed commit** (typecheck Â· lint Â· test Â· build Â· `check:bundle`) â€” observed via PR CI (the authority above) â€” **PLUS** the data-INDEPENDENT subset of the local gate that CAN run in the worktree (`governance` Â· `typecheck` Â· `lint` Â· `test`), with pasted command output.
  - The **data-DEPENDENT** gate steps (`reconcile`, `warehouse:verify`, and any DB-backed `warehouse:drift` that needs a backfilled warehouse) are **SKIPPED-WITH-REASON**, recorded explicitly as: `SKIPPED â€” requires live OneDrive/SharePoint data (WORKBOOK_PATH / FINANCIALS_DIR) + a backfilled DB that cannot exist in this hermetic worktree; relying on CI + the data-independent gate subset for additive verification.` **This is an explicitly-recorded skip, NOT an UNVERIFIED demotion** (it satisfies Â§3 NO SILENT CAPS). Do **NOT** attempt to populate the worktree warehouse or run `reconcile`/`warehouse:verify` against shared business data â€” backfill is a WAL-lock writer and the shared `finance.sqlite` lock is forbidden (Â§0.5, Â§0.7).
  - **There is NO "FULL `npm run gate` or else UNVERIFIED" bar in this run.** A task is UNVERIFIED only if the runnable subset (CI green + the data-independent local steps) cannot be made green, not because the data-dependent steps were skipped.

---

## 12. PHASE 6 â€” Durability, completion semantics & notification

**Run-state ledger (durability):** maintain a ledger file in the session outputs dir, updated at **each phase boundary** (phase complete Â· artifact paths Â· open items Â· next action Â· which Â§0.4a pre-push path was taken Â· termination-rule check per Â§3). Persist each artifact to disk the instant it is produced â€” never hold a completed report only in context.

**Durable deliverables (no human recipient assumed):**
- Audit Report / Evaluation Scorecard / Hardened Plan â†’ committed markdown under `docs/superpowers/specs/` (plus the Â§10 `docs/superpowers/plans/` plan copy that arms `eos-plan-gate`) on the worktree branch + summarized in the PR description.
- Out-of-scope/`HUMAN-RATIFICATION-REQUIRED` backlog and â‰¤5 systematization candidates â†’ PR body **and** appended to `memory/event_log.md`. Record any lane misses to `memory/event_log.md`.
- Do not rely on session chat output for any deliverable.

**DONE checklist (run is complete only when ALL exist on disk, non-empty):** (1) ranked Audit Report Â· (2) Evaluation Scorecard Â· (3) Hardened Plan (committed under `docs/superpowers/specs/` AND copied to `docs/superpowers/plans/` so `eos-plan-gate` is satisfied) Â· (4) a draft PR URL for the Tier-A subset (or an explicit "zero tasks qualified" note) with observed-green CI Â· (5) the deferred-proposal backlog Â· (6) â‰¤5 systematization candidates Â· (7) the Â§12 notification sent.

**Fail-safe cleanup (EVERY exit path â€” success, error, defer-stop, crash-on-resume):** kill every process you started to release the WAL lock; commit + push any WIP to the feature branch first so nothing is lost (subject to the Â§0.4a pre-push confidentiality gate); then either keep the worktree intentionally (work committed+pushed; record its path for resume) or `git worktree remove` it. As the LAST action, **verify no dev/preview server is running and no process holds `finance.sqlite`**, and report that verification. Never leave a warehouse process holding the WAL lock (it silently wedges the scheduled fleet).

**Completion notification (mandatory, EVERY exit path â€” this is the ONE pre-authorized send).** Post a completion summary to the **Notion Operations Hub completion log (Ops Hub database id `32b6ecd8`, per the global CLAUDE.md Notion canon)** AND send a single status email to `ggoldberg@oxfordra.net` **ONLY** via `send-via-outlook.ps1` (COM path; on non-zero exit retry once then flag the Notion row â€” do NOT halt; never cc, never ze@). **If the Ops Hub completion-log sub-page cannot be resolved deterministically from id `32b6ecd8`, do NOT post to a guessed/searched page â€” fall back to the email notification only and record `Notion post SKIPPED â€” target unresolved` in the ledger.** State in the notification: phases completed, PR URL (or why none), counts of audit findings / deferred proposals, any guardrail DEFERs hit, the observed CI conclusion (or `CI UNVERIFIED â€” poll cap hit`), and confirmation no dev server is left running. **This internal send is pre-authorized under routing canon â€” it is NOT a counterparty send** (Invariant 1's carve-out).

---

## 13. DELIVERABLES (recap)

Ranked **Audit Report** Â· **Evaluation Scorecard** Â· **Hardened Plan** (committed under `docs/superpowers/specs/` AND copied to `docs/superpowers/plans/` so it satisfies `eos-plan-gate`) Â· **implemented Tier-A changes with pasted evidence on a DRAFT PR** (opened non-interactively via `gh pr create --draft --base main --title â€¦ --body-file â€¦`; CI-green per the Â§11 runnable-subset authority, with data-dependent gate steps SKIPPED-with-reason) Â· **deferred-proposal / `HUMAN-RATIFICATION-REQUIRED` backlog** of RED items needing Gabriel's approval Â· **â‰¤5 systematization candidates** (skill/scheduled-task/template). All persisted to durable locations; completion notification sent. The run never pauses, never self-approves a gate, and never executes a Hard-Invariant action.
