---
name: open-items-tracker
description: "Single canonical open-items / punch-list tracker for the ORA system — one entry per open/residual/TODO item across memory, fleet, and repo state. Other files POINT here; item text lives in exactly one place."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 1624855d-d36d-4c3e-9761-0250482b1d31
  modified: 2026-08-12T22:22:49.954Z
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
| [OI-140](#OI-140) | 2026-08-12 | Hit live while verifying the [OI-136](#OI-136) filing against a `git show HEAD:` extract — the checker reported a defect that existed only in the working tree | **MEDIUM** `maintenance/check-open-items-duplicate-ids.py` **silently ignores its CLI path argument** and always reads the canonical tracker. `main()` does `path = tracker_path()` (line 180) → `TRACKER_PATH_OVERRIDE or DEFAULT_TRACKER_PATH`; **`sys.argv` appears zero times in the file** — no argparse, no positional handling. Passing a nonexistent path still returns a normal clean canonical report, because the `COULD NOT READ %s ... treat as a check failure` branch is unreachable from the CLI. Three things make it read as a working feature: it prints the path it checked, it formats a path into that error branch, and it accepts an argument without complaint. **Tests do not catch it** — `_tests/test_check_open_items_duplicate_ids.py` drives `main()`'s read path by assigning `codc.TRACKER_PATH_OVERRIDE` (a module attribute), so the logic is covered and the entry point never is. **Production caller is unaffected**: `ora-weekly-hygiene` Block N passes no argument. The harm is ad-hoc verification of a worktree copy / candidate edit / `HEAD` extract, which silently returns a verdict about a *different file* — false FAIL (blaming your copy for a live-file defect) or false PASS (your broken copy looks clean because the live one is). A verification tool that answers about an artifact you did not name is the [[feedback_verified_null_vs_inferred_null]] failure in its purest form |
| [OI-139](#OI-139) | 2026-08-12 | `fleet-status.py`'s `find_missed_cycles()` CRON-AWARE GUARD fix (commits `40b6176`/`30d2869`, merged to `main` and pushed as `08e0daa`); Cowork handoff "Health Guard FAIL-Aging Follow-Up" 2026-08-11, `scheduled-tasks/ora-health-guard/SKILL.md` C.1.1 | **LOW — accepted tradeoff, documented, not a defect.** The 2026-08-11 fix that made the missed-cycle detector cron-aware (escalate only past `max(24h, 1.5x own cadence)`, replacing the flat 24h wall that produced 8/13 false positives on 2026-08-10) is pure cadence math with no runtime signal for "was this a genuine catch-up burst." The superseded per-run SKILL.md logic additionally suppressed a `gap ≈ 1x interval` entry only when a late wake was detected *that run*, and otherwise escalated immediately as a likely phantom dispatch or dead task — a signal the code-level threshold structurally cannot see. **Consequence:** a task that misses exactly one slot with the machine fully up (no catch-up excuse available) now surfaces one cycle later than the old per-run logic could have caught it. Deliberate, Gabriel-approved simplification (the 2026-08-11 Cowork handoff spec explicitly specified the 1.5x-cadence rule) — do not re-litigate the threshold on this row alone. **Re-open only if a real single-slot dead-task/phantom-dispatch incident is observed and traced to this specific gap** — do not preemptively bolt an A.0-style runtime signal back into the code threshold without one |
| [OI-138](#OI-138) | 2026-08-12 | hit live while committing two markdown memory files (OI-133 filing); `hooks/eos-review-gate.py` | **MEDIUM — ROUTED to the `hooks-override-auth-eos-gate-msg` workstream (session `e23f4c54`), same file, different defect from the `--record`/config-write-guard message fix.** The gate's BLOCKING path does not apply the pathspec scoping its own `--key --cmd` path does, so it scores *other live sessions' working-tree files* into an unrelated commit. Measured: unscoped `--key` → 3 foreign paths (`hooks/lib/claim_work.py`, `hooks/tests/test-claim-work-lib.py`, `scheduled-tasks/ora-pm-ledger/property_register_snapshot_diff.py`); `--key --cmd '<the pathspec commit>'` → `paths: []`, `key: ""`. **The gate already computes the right answer — the block just doesn't ask it that way.** Using the pathspec form of `git commit` did NOT change the block. Second, and worse — **CONFIRMED, not a guess: the block and `--record` key off DIFFERENT computations, so the gate is unclearable by its own documented procedure.** Both are deterministic and they disagree: the block reported `03b8fb93055b` on two separate attempts minutes apart, while `--key` returned `ef91d37feb7e…` on four consecutive runs. A review recorded via `--record` therefore lands under a key the block never looks for, and **an override is the only exit** — which is exactly how a security gate degrades into a formality. **Why it matters:** in a checkout with 125 dirty files across 15+ sessions this fires on nearly every commit regardless of content, so the gate gets overridden as routine — that is the failure mode, not the inconvenience |
| [OI-136](#OI-136) | 2026-08-12 | `event_log.md` entries committed as `75ab0de`, cross-read against this session's own two declined overrides | **HIGH** `allow-hook-test-failure` normalised: **5 uses across 4 sessions inside 47 minutes** (16:32:04–17:19:23 local, 2026-08-12; `e89ddd24` twice). Every one cites the *same* cause — a load-induced `exit 124` TIMEOUT on `test-eos-review-gate.py` that passes in isolation — i.e. all 5 are [OI-057](#OI-057)/[OI-059](#OI-059), not 5 independent judgement calls. **No protocol was broken**: each token records explicit in-turn authorization, exactly as `rules.md` requires. That is the finding — the control worked as designed and was still worn down, because a gate that false-blocks makes overriding the *rational* move, and the reasons converge to a script ("timeout not assertion, passes standalone"). The security property `allow-hook-test-failure` protects is that a human weighs a **real** test failure; 5-for-5 on one known flake trains the reflex to approve without weighing, so the next genuine failure inherits that reflex. Mitigated indirectly by `c29ec95` (budget 90→240) but **not addressed**: nothing caps, counts, or alerts on override frequency, and nothing distinguishes "5th override this hour for the same flake" from "first override this month for a novel failure". Needs a rate/repeat signal, not a stricter gate |
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
| [OI-078](#OI-078) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **CRITICAL** ora-pm Row Level Security is enabled on only **6 of 23** tables (`charges`, `payments`, `lease_documents`, `lease_amendments`, `tenant_notices`, `insurance_certificates`) while `VITE_SUPABASE_ANON_KEY` ships in the public JS bundle by design. `properties`, `units`, `tenants`, `leases`, `expenses`, `budgets`, `renewals`, `broker_commissions`, `cam_reconciliations`, `correspondence_log`, `journal_entry_exports`, `lease_move_events`, `sent_notifications`, `stripe_webhook_events`, `tenant_sales_reports`, `utility_meters`, `utility_readings` have no `ENABLE ROW LEVEL SECURITY` anywhere in `supabase/migrations/**` (verified this run by direct grep, not taken from the agent). Under stock Supabase grants an RLS-disabled public table is readable AND writable via PostgREST with the bundle-extractable anon key. Distinct from [OI-048](#OI-048), which is about the *API* using the service-role key; this is the direct-database perimeter. **Live exploitability is INFERRED, not verified** — a one-command curl check is in the item |
| [OI-079](#OI-079) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **HIGH** ora-pm's `ar_ledger`, `rent_roll` and `critical_dates` views are created without `WITH (security_invoker = true)` (`0011_appsec_idempotency_and_scale.sql:118-151`, `0004_views_and_rls.sql:33-99`) — grep confirms the string appears nowhere in `supabase/migrations/**`. A view without it runs as its owner and IGNORES the RLS policies on `charges`/`payments`/`leases`/`tenants`, so one `GET /rest/v1/ar_ledger` returns every tenant's balance and payment totals even after [OI-078](#OI-078) is fixed. Cross-tenant financial disclosure in one request |
| [OI-080](#OI-080) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **HIGH** ora-pm tenant portal login permits open self-registration — `src/portal/pages/PortalLogin.tsx:12-15` calls `signInWithOtp` WITHOUT `shouldCreateUser: false` (defaults true), so any submitted email mints a Supabase auth user. [OI-036](#OI-036)'s fix covered only the ADMIN login (`AdminLogin.tsx:22` has the flag plus an explicit OI-036 comment) — one of two login pages was missed. Verified by direct diff of the two files this run. Yields a valid `authenticated` JWT to anyone, which is the credential that escalates OI-078/OI-079 past anon-only hardening; also pre-registering a known tenant address breaks `inviteUserByEmail` onboarding |
| [OI-081](#OI-081) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **HIGH** ora-pm `requireAal2` is a no-op for any tenant who never enrolled MFA — `server/middleware/aal-guard.ts:46` blocks only when `nextLevel === 'aal2' && currentLevel !== 'aal2'`, and `nextLevel` never rises above `aal1` without a verified factor. Enrollment is voluntary (`PortalAccount.tsx:90`); nothing requires it. So for the realistic majority of tenants the only control on `POST /api/stripe/setup-intent` and `POST /api/stripe/payment-intent` (confirms ACH immediately, up to min(balance, $50k)) is possession of a magic-link session. Does NOT contradict [OI-045](#OI-045)'s closure (the gate IS wired and does fail closed) but materially narrows what that closure bought — read alongside it |
| [OI-082](#OI-082) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **MEDIUM** ora-pm `payments` has no idempotency or uniqueness constraint for non-Stripe methods. `0011`'s two partial unique indexes cover `stripe_payment_intent_id` and `(lease_id, autopay_period)` only; `method IN ('check','wire','other')` rows are NULL on both and so fall outside each. `charges` got `idempotency_key TEXT UNIQUE NOT NULL`; `payments` did not. A double-submitted admin form or replayed import writes two identical rows and `ar_ledger`'s `payment_totals` CTE sums both — the tenant's balance silently drops, and that understated balance then feeds the payment-intent cap and the autopay lifetime cap. Same failure class as the two AR bugs already shipped here (cartesian fan-out, divide-by-100): the join was fixed, the write path was not |
| [OI-083](#OI-083) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **MEDIUM** ora-pm `POST /api/portal/insurance` (`server/routes/portal-insurance.ts:13-37`) is the only write route with no Zod schema — it destructures the raw body and inserts it, and writes client-supplied `storage_path` to `document_path` verbatim with no ownership or prefix check (the admin route uses `InsuranceInsertSchema`; this one doesn't). An authenticated tenant can point their COI record at another tenant's storage key, surfacing the wrong document under the wrong tenant in the admin UI. Adjacent to but distinct from [OI-041](#OI-041)'s mass-assignment set, which did not include this file |
| [OI-084](#OI-084) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **MEDIUM** ora-pm COI uploads go browser -> Supabase Storage directly (`src/portal/pages/PortalInsurance.tsx:29-39`), bypassing the API entirely: no MIME/magic-byte check, no size cap, `upsert: true` with an unsanitized `file.name`. The `accept` attribute is the only gate and is client-side. The repo already has a server-side validator doing this correctly for lease intake (`server/routes/intake.ts:86-91`) and an unused client validator (`src/components/ui/file-drop.ts`) — the pattern exists, this path just doesn't use it |
| [OI-085](#OI-085) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **MEDIUM** ora-pm portal "Open Charges" is not open charges — `server/routes/portal.ts:39-60` returns EVERY charge on active leases and `PortalPayNow.tsx:33-39` treats them all as selectable, because `charges` has no paid/open state and no charge<->payment link. Separately the balance card sums `ar_ledger` across ALL the tenant's leases while the charge list covers only ACTIVE ones, so the two figures cannot reconcile by construction. A tenant with 18 months of history sees 36+ "open" charges. The server-side cap (`stripe.ts:168`) prevents actual overpayment, so this is a correctness/trust defect, not a loss — but it is the same balance-display class this repo has shipped twice |
| [OI-086](#OI-086) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (ora-pm @ `a29f8f0`, security-auditor dispatch) | **MEDIUM** ora-pm `CRON_SECRET` gate uses a short-circuiting string compare (`server/middleware/auth.ts:7`) on the route set that includes `POST /api/cron/monthly-billing` — which creates and CONFIRMS off-session ACH PaymentIntents portfolio-wide. The timing side-channel alone is marginal through Cloudflare's edge; what raises this is the combination: a static, never-rotated shared secret passed on a PowerShell command line (`scripts/trigger-billing.ps1:14`, visible in process listings and shell history) as the single factor gating automated debits |
| [OI-088](#OI-088) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (oxford-command-center @ `175e3f9`, security-auditor dispatch) | **MEDIUM** oxford-command-center `ledger_entries` — the money table — is the only one of its siblings with no natural-key uniqueness constraint (`server/warehouse/migrations/001_initial.sql:59-74`): an AUTOINCREMENT surrogate PK and one NON-unique index, so an identical `(import_id, property_id, period, raw_account, amount)` row is insertable twice by a re-run or replay and silently doubles a balance. Contrast `property_tax_assessments`, `insurance_loss_events`, `property_insurance_policies`, `debt_positions`, all of which have one. Also: no FK on `ledger_entries.property_id` -> `property_master(id)` or on `mapping_id` (though `PRAGMA foreign_keys = ON` is set, so declared constraints WOULD be enforced — the enforcement is on, the declarations are missing), `lease_events` (`011`) has no uniqueness at all, and every money column across `001`/`009`/`011` is bare `REAL` with no unit in the name, comment or CHECK. Security-relevant half only — math correctness stays with `ora-financial-code-integrity-sweep`. Note `server/warehouse/migrations/**` is architect-owned |
| [OI-089](#OI-089) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (oxford-command-center @ `175e3f9`, security-auditor dispatch) | **MEDIUM** oxford-command-center `/api/actions/om-extract` (`server/index.ts:358-414`) validates only `file.name.endsWith('.pdf')` plus a 25 MB cap — no `%PDF-` magic-byte check — then feeds the buffer to `pdf-parse` and, with a `dealId`, writes it verbatim into the live OneDrive deal-document tree. Arbitrary non-PDF content can be persisted into business storage under a `.pdf` name. Reach is local-only (see [OI-050](#OI-050)). The filename sanitization and `resolve()`-prefix traversal assertion at `:400-405` are correct and should be preserved as-is |
| [OI-090](#OI-090) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (oxford-command-center @ `175e3f9`, security-auditor dispatch) | **MEDIUM** oxford-command-center has no rate or concurrency limit on `/api/ai` (`server/index.ts:460-493`), `/api/documents/search` (`:447-453`) or `/api/actions/om-extract` (`:358`). Per-request bounds are good (`maxTurns: 8`, `max_tokens: 16000`, 25 MB cap) but nothing bounds concurrent or repeated calls, and each `/api/ai` call spends real Anthropic tokens against the machine's key. OWASP-LLM10 unbounded consumption; combined with [OI-050](#OI-050)'s unauthenticated cross-site write path this is the cheapest denial-of-wallet route in the repo. ora-pm's equivalent gap was closed under OI-038/044; occ has no counterpart |
| [OI-091](#OI-091) | 2026-08-05 | ora-appsec-sweep 2026-08-05 (oxford-command-center @ `175e3f9`, security-auditor dispatch) | **MEDIUM** oxford-command-center `.claude/hooks/file-guard.mjs:144-159` applies its documented fail-open to the HARD-DENY paths, not just the sentinel-overridable architect-owned list: `findRepoRoot` walks up looking for `CLAUDE.md` and `continue`s (unpoliced) if none is found, and skips any target whose owning root is neither ancestor nor descendant of the session root. A worktree or checkout without a root `CLAUDE.md`, or a path form that breaks `relative()` matching (junction, `\\?\`, 8.3 short name, UNC), therefore leaves `data/overlay.json`, `data/warehouse/**`, `.claude/settings.json` and `.claude/hooks/**` unprotected by this hook; the `permissions.deny` globs are path-form-sensitive in the same way. LLM06/excessive-agency: an agent session on an unusual path form can edit its own guardrails. Requires an already-agentic session, so MEDIUM not HIGH. Any fix here is security-gate hook logic: mandatory adversarial REFUTE pass + the old-vs-new differential battery |
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
### OI-019
**Status:** OPEN
**Opened:** 2026-07-19
**Source:** [event_log.md](event_log.md#2026-07-19)
**Description:** Gabriel must add `HUBSPOT_TOKEN` (Private App, `crm.objects.deals.read`) to `oxford-command-center/.env` — PR #221 ready, blocked only on the credential; then re-verify 2146 Enterprise Pkwy lands in acq_candidates.
*(Section added 2026-07-29 during tracker ID-integrity reconciliation — the row predated the section requirement; row is authoritative for detail.)*

### OI-020
**Status:** CLOSED 2026-08-05
**Opened:** 2026-07-19
**Closed:** 2026-08-05
**Source:** [event_log.md](event_log.md#2026-07-19)
**Description:** ora-cowork-heartbeat's LAMS registry entry has no `approvedPermissions` grant — only fix is Gabriel approving the Notion-tool prompt during a live unattended fire in Cowork's Scheduled Tasks UI; GitHub watchdog issue needs manual closure once fixed.
**Resolution (2026-08-05):** the grant is PRESENT and the task is firing. Live LAMS registry read: `approvedPermissions: [{'toolName': 'mcp__…notion-update-page'}]`, `enabled: true`, `lastRunAt 2026-08-05T09:57:51Z` against `lastScheduledFor 09:50` — i.e. it completed an unattended fire that morning. Someone approved it during a live fire without closing this item; it was documented "unresolved 3×" while already fixed.
**Residual (NOT closed by this):** the GitHub watchdog issue still needs manual closure — verify against `ZeOoba/ora-cowork-watchdog`. Separately, `fleet-roster.md` had this task's cron as `50 5,17 * * *` while the live registry said `50 5 * * *`; corrected by re-running `registry-membership-probe.py` the same day.
*(Section added 2026-07-29 during tracker ID-integrity reconciliation.)*

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

### OI-063
**Status:** CLOSED
**Opened:** 2026-08-03
**Closed:** 2026-08-04
**Source:** ora-pm appsec fix plan (subagent-driven-development execution of `plan/appsec-fixes-oi034-048`), Task 9 (OI-041/OI-042 remainder + OI-046 gap closure), commit `afef524` — self-flagged by the implementer, independently confirmed via grep by the task reviewer (not just trusted)
**Description:** OI-042 ("raw Postgres error messages returned to clients") was originally scoped across Tasks 2/7/8/9 by file, but the scoping missed 5 files entirely — no task in the 11-task plan names them, so no branch commit touches them. Confirmed still live: `properties.ts` (3 sites), `expenses.ts` (2), `payments.ts` (1), `portal-auth.ts` (2), `portal-insurance.ts` (1). Task 9 correctly declined to silently expand its own scope to cover these — same discipline as OI-060's filing.
**How to apply:** route each site through `dbError(c, error, publicMsg?)` (`server/lib/api-error.ts`, shipped by Task 7 of the same branch) — mechanical, same pattern as every other file in the branch. Low risk, no schema/logic changes needed, just the error-response swap. Should extend `tests/lib/no-raw-db-errors.test.ts`'s tripwire (same branch, Task 9) to cover these 5 files once fixed, closing the allowlist gap that currently excludes them.
**Evidence (2026-08-04):** a REFUTE pass re-verifying a later commit (`8fb7022`, whose title claimed "dbError sweep") found it had NOT touched any of the 5 self-flagged files despite the title — confirmed still-open via `git diff` (empty on all 5 files) before writing anything. Fixed all 9 sites (TDD — RED test per site asserting a generic message + no leak of the injected raw error text, written before the fix) through `dbError()`, matching the established pattern exactly; `properties.ts`'s single-record 404 lookup kept a plain generic 404 (mirroring `tenants.ts`'s own documented exception, since `dbError()` always 500s). Tripwire allowlist entries for all 5 files removed; the "fully clean" pinned assertion extended to cover them. Fixed on `ora-pm` main, commit `7857646` + merge `a29f8f0`. 402/402 suite green at the time, typecheck clean.
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

<!-- OI-111 deferred (2026-08-14/15): HEAD and origin/main carried mutually contradictory row + detail-section content for this item -- opposite technical conclusions about whether the pre-push hook-test suite has a genuine concurrency-safety defect (HEAD: measured 08-12, closed as a budgeting issue; main: unretracted "38 fail/37 pass, do not fix by overriding"). Deliberately withheld from this merge -- no row, no section -- pending Gabriel's decision, to avoid asserting either contradictory claim as settled. Both full candidate texts are recoverable from this commit's merge parents. Resolved as its own follow-up commit in a dedicated worktree. -->
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
**Status:** OPEN
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
**Closing condition:** a session that collides with an unattended holder gets a refusal that names the
holder as uncontactable and offers a next step that is not `--force`.
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
**Leads, NOT root cause — do not treat these as findings:** (a) two of the three ratios are almost
exactly one quarter (warehouse/workbook = 25.0% Westerville, 25.5% Raytown; Livingston is the
outlier at 8.8%), which would be consistent with a partial period being compared against an
annualised figure — unverified. (b) All three have only **2** committed rows in `import_batches`
(period_start 2025-01-01) versus 3 for most in-tolerance properties. **This correlation does NOT
hold**: `2203-2207-northwood-dr-salisbury-md` also has 2 batches and ties out at 1.06%. Batch count
alone therefore does not explain it — recorded so the next person does not re-derive a rule that
has a live counterexample.
**Which side is wrong is UNKNOWN.** Per `CLAUDE.md` the live Master Workbook is first for firm
figures, which makes the warehouse the more likely suspect, but that is doctrine, not evidence —
nothing here has been traced to a specific parse, period-selection, or ownership-share bug. Do not
"fix" either side until one is proven wrong.
**How to apply:** start from `scripts/reconcile-noi-crosscheck.ts` and the `oxfordNoi` derivation,
and check period selection first (which window each side reports, and whether the warehouse figure
is being annualised). Confirm against a single property end to end — Livingston is the sharpest
signal at 91%. Separately decide whether `gate:ci` should include this step; if it should not, the
local `gate` failing on `main` needs to be visible some other way, because today it is silent.
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

## Closed

| ID | Opened | Closed | Source | One-line |
|----|--------|--------|--------|----------|
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
**Auto-check:** kind=registry_field_equals fleet=lams task_id=ora-cam-reconciliation-annual field=cron expect="0 7 15 1 *"

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

### OI-080
**Status:** OPEN
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
**Status:** OPEN
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
pressure) · [[reference_cc_snapshot_refresh_dq_flag_alert_is_count_not_severity]] carries the supersession note.
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

**Fix options — option 2 APPLIED 2026-08-12 (v1.2); 1 and 4 declined; 3 still open:**
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

### OI-136
**Status:** OPEN
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

**Session handoff note (2026-08-13, session b34ec269):** checked before starting related punch-list work (a wrapper script + a documented polling-claim-loop default were the actual items owned this session) -- confirmed via `hooks/active-work/hooks-override-auth.json` that session `4ead3171` still holds a live claim on this exact fix ("add an override-frequency counter to the pre-push hook-tests gate block message (OI-136 candidate fix 2, Gabriel-directed)") and confirmed via `git log -- hooks/git-prepush-hook-tests-gate.py hooks/lib/override_tokens.py` that nothing has landed for it yet (latest commit there is the unrelated `c29ec95` timeout-budget change). Not duplicated; no code touched.

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
