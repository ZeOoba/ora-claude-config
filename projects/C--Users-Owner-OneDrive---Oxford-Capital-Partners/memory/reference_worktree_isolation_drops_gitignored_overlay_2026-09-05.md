---
name: reference-worktree-isolation-drops-gitignored-overlay-2026-09-05
description: v1.7 worktree isolation copies only .env, so gitignored data/overlay.json is absent and the extract silently zeroes 4 enrichment sections at exit 0 — both snapshot tasks refuse on the shrink guard until fixed. Also records a SECOND vector no guard catches: an m365-tasks fetch failure partially shrinks tasks 115->59 and would auto-push once the overlay bug is fixed.
metadata:
  type: reference
---

**Both ORA snapshot tasks (`ora-cc-snapshot-refresh`, `ora-lease-snapshot-refresh`) now refuse to commit on every run.** Discovered 2026-09-05 by `ora-cc-snapshot-refresh` (run `20260905T200425Z-febe`); first CC fire under the v1.7 Worktree isolation section added 2026-09-02.

**Mechanism.** `data/overlay.json` is gitignored (`.gitignore:16`) and lives only in the live `oxford-command-center` checkout (~29KB: `tenantArrears` 44, `dealComps` 2, `renewalStages` 1). The v1.7 procedure copies **only `.env`** into the fresh worktree, and `git worktree add` brings tracked files only — so the overlay is simply absent there. `npm run extract` then falls through to `loadOverlay()` → `EMPTY_OVERLAY` → `applyOverlay()` nulls `arBalances` (44→0), `tenantArrears` (44→0), `dealComps` (2→0), `renewalStages` (1→0) — and **exits 0 reporting a clean run** ("No lease drift", 0 data-quality flags, all 5 hardcoded list sections flat).

**Why the script's own guard misses it.** `scripts/extract-workbook.ts:38-61` was written for exactly this hazard but is wrapped in `if (existsSync(rawOverlayPath))` — it defends against an overlay that is *present but corrupt/wrong-shaped*, never against a *missing* one. `quickbooks` survives only because of its separate server-attached carry-forward step added after the 2026-08-17 incident; the four overlay-backed sections have no equivalent.

**What caught it.** Only the **generic non-list section-shrink check** (added 2026-08-24, OI-137). The hardcoded 5-key list loop would have missed all four — see [[reference_cc_snapshot_shrink_guard_covers_lists_only]]. Same failure class as the 2026-08-09 Notion-deals seed placeholder and the 2026-08-17 quickbooks nulling: a CLI writer silently degrading a section it does not own, at exit 0.

**Do NOT** read the refusal as workbook corruption or data loss — source data is intact in `data/overlay.json`, and the live checkout's `portfolio.json` is untouched and correct. **Do NOT** rebuild the AR pipeline (see [[reference_ar_subsystem_exists_but_dark_2026-08-16]] — 3 sessions nearly did).

**RESOLVED 2026-09-05 — Gabriel ruled C (both halves).**

- **Code half:** [PR #311](https://github.com/ZeOoba/oxford-command-center/pull/311) adds `evaluateOverlayPrecondition()` to `server/overlay.ts` — refuses on missing / unparseable / wrong-top-level-shape, and all three CLI writers (`extract-workbook.ts`, `lease-snapshot-drift-check.ts`, `ar-import-headless.ts`) now share it instead of three copy-pasted blocks. `{}` stays allowed as the deliberate bootstrap escape hatch. Verified E2E against the live workbook: overlay present -> exit 0, 44/44/2/1 preserved, zero shrinks; overlay absent -> exit 1, snapshot unwritten. typecheck + lint clean, 276 files / 3834 tests pass.
- **Spec half:** both `scheduled-tasks/ora-cc-snapshot-refresh/SKILL.md` and `.../ora-lease-snapshot-refresh/SKILL.md` now copy `data/overlay.json` alongside `.env` (changelog v1.8 / v1.9). These edits are LIVE on disk, which is the store the scheduler reads — see [[reference_skill_description_registry_file_desync]].

**Review round (independent opus reviewer, 2026-09-05) found the first commit incomplete — fixed in `c232700`.** The missing-file message told operators to *"create the file containing `{}`"*, and `{}` merges exactly like `EMPTY_OVERLAY` — the printed remedy re-armed the failure. Reachable with no operator error at all: one server-side `saveOverlay()` in a fresh checkout writes a near-empty overlay. `evaluateOverlayPrecondition` now takes `{expectEnriched}`; the two snapshot writers refuse an overlay with no enrichment in any domain, `ar-import-headless`/`migrate-lease-overlay-ids` deliberately do NOT (an empty overlay is legitimate on a first AR sweep). Bootstrap moved to `ALLOW_EMPTY_OVERLAY=1`. Also: a 4th inline copy survived in `migrate-lease-overlay-ids.ts` (now wired in), ar-import appended a rationale that was false for the missing case, and `extract-workbook.ts` lacked the `process.argv[1]` entrypoint guard its siblings have. Added source-level tests pinning the call-site guard SHAPE — the original defect was the shape, not the predicate, so a revert to `if (existsSync(path))` would have kept all behavioral tests green.

**⚠ `refute-required` CI gate BLOCKS the merge.** `server/overlay.ts` is enumerated financial-decision source (`scripts/check-refute-required.ts:111`), and `architecture/coding-standards.md:120` forbids `Refute-Skip:` for "the financial overlay" specifically — so the PR needs a real `Refute-Reviewed: wf_<runId>` trailer. `hasRefuteApproval` scans `git log base..HEAD`, so a LATER commit carrying the trailer satisfies it — no amend needed. Awaiting Gabriel's call on running the billed workflow.

**⚠ Git-backup of the spec half is BLOCKED, deliberately not forced.** `~/.claude` `origin/main` does **not** contain the Worktree isolation section at all — v1.7 lives only on the unpushed branch `feat/model-canary-probe-step25` (commit `8d0fe2a`, ahead 7 / behind 26), which is another session's WIP. There is no clean base on `main` to commit the amendment onto, and branching off that HEAD would publish their 7 commits. Left uncommitted per rules.md §14 (report, never force-resolve). The runtime files are correct regardless; only the git backup is outstanding, and it unblocks when that branch lands.

**Superseded plan** (kept for the reasoning):
**Fix pending Gabriel's ruling** (Notion `3d26ecd8-9e59-812f-baf5-f73ed8c66622`, emailed 2026-09-05 16:10 ET): **A** copy `overlay.json` into the worktree alongside `.env` in both specs · **B** add an `else` to the `existsSync` guard exiting 1 on a missing overlay · **C** both — recommended, since B is what would have turned this into an honest exit 1 instead of a false clean bill.

---


## CLOSED 2026-09-06 — both PRs merged to main

**[PR #312](https://github.com/ZeOoba/oxford-command-center/pull/312) merged `ac590d6`, [PR #311](https://github.com/ZeOoba/oxford-command-center/pull/311) merged `a7ff5ee`** — in that order deliberately, because #311 removes the missing-overlay refusal that had been accidentally masking #312's silent `tasks` loss. Verified present on `origin/main` after merge (a merged PR is not proof the code landed — [[project_automation_audit_rev22_2026-09-05]]).

**The mandatory refute pass (5 lenses each) found BOTH PRs incomplete.** Neither was ready when its CI went green:
- **#311** — `hasNoEnrichment` judged the RAW parse while `loadOverlay` applies per-entry Zod coercion, so `{"dealComps":{"d1":{"bogus":true}}}`, `{"tenantArrears":{"x":"oops"}}`, `{"tasks":{"a":1}}` and `{"tenantArrears":0}` passed the guard and still merged as `EMPTY_OVERLAY` — **the same silent zeroing, through the loader instead of a missing file.** Fixed by extracting `parseOverlayRaw()` so the guard judges the loader's OUTPUT; guard and loader now agree by construction. Also: the missing-file message prescribed `ALLOW_EMPTY_OVERLAY=1`, which that branch never consults — a dead remedy that a test *pinned* by asserting only on the string.
- **#312** — both auto-pushing CLI writers gated only on the FLAG, which is deliberately `null` for `not-configured`. A `GRAPH_CLIENT_SECRET` rotation would still have written `tasks` 115→59 at exit 0. Fixed with `requireLiveM365Source()` on both writers + the missing `console.warn`.
- **Fifth writer:** `server/brain.ts` `persist()` also merges a fail-open `EMPTY_OVERLAY` on every UI write-back; it now carries the same gate (decline the mirror, keep serving).

**Reusable lessons.**
1. **A guard must judge what the consumer actually produces, not its input.** Two checks over the same data kept in sync by hand is the defect, not the symptom — same class as the by-name write-clock filter and the hardcoded-list shrink guard.
2. **A partial mock factory silently returns `undefined` for omitted exports.** `brain.test.ts` mocked `server/overlay`; adding two imports to `brain.ts` broke 21 tests at once. Suspect the mock before the environment — my first fix (bootstrapping the sandbox overlay in `tests/setup.ts`) addressed the wrong cause and would have set `ALLOW_EMPTY_OVERLAY=1` suite-wide, masking this branch's own refusal tests.
3. **Duplicate-session work again:** session `24f0b4f7` independently redid the #312 refute fixes while I was merging them, and still holds worktree `ora-cc-worktrees/m365-fixes` on `fix/m365-refute-fixes` — leave it alone. Its claim lists two things NOT in main and worth a follow-up: `bake-mirror.ts` still only WARNS (so the daily brief can email "None due" and not resend, since `shouldSendBrief` keys on `lastBriefDate`), and the **partial-shrink residual is still open** — `tasks` is not one of the shrink guard's five keys, so a 200-response under the >10-list / >50-per-list / >100-total caps stays invisible.

## SECOND, INDEPENDENT degradation vector found on the next run — `tasks` 115 → 59, caught by NO guard

`ora-lease-snapshot-refresh` (run `20260905T201214Z-c489`, 2026-09-05 ~20:12 UTC) reproduced the overlay drop above exactly (same 4 sections → 0) **and** surfaced a separate one on the same fire. Its stdout carried `[m365-tasks] live fetch failed, skipping` — and the `tasks` section went **115 → 59**, losing 56 M365 To-Do rows.

**No guard catches this.** The section-shrink guard has two halves and `tasks` falls between them: it is not one of the 5 hardcoded list keys (`leases`/`deals`/`counterparties`/`properties`/`loans`), and the generic non-list check only fires on `populated -> empty/null` — a *partial* shrink to a still-non-empty 59 is invisible to it. That is the guard's own disclosed KNOWN RESIDUAL, now instantiated with a real 56-row loss.

**Why this matters more than the overlay bug.** The overlay drop is loud — it zeroes four sections completely, so the generic check refuses and a human is asked. The m365 drop is silent: had the overlay been present (i.e. once fix A/B/C lands), this run would have read `MATERIAL: yes`, passed both guard halves, and **auto-committed and auto-pushed** a snapshot missing 56 tasks to `origin/main` at exit 0, with no Notion post and no email (Exit 0 routing suppresses both). Fixing the overlay bug alone therefore *unmasks* this one.

**Implication for the pending ruling:** option B (exit 1 on a missing/degraded upstream) is the shape that generalizes — a per-source degradation gate, not another bespoke section check. `[m365-tasks] live fetch failed, skipping` should be an error-severity `dataQuality` flag like the 2026-08-09 Notion-deals degradation already is, not a `skipping` log line at exit 0. The stdout degradation scan in both task specs greps only for the `[notion-deals]` strings and so misses this too.

Also observed same run (live Notion, not a defect — logged so it is not re-investigated): deal `Fairground Village Center` stage moved `Closed` -> `Closing`.

**STATUS: FIXED, awaiting merge — [PR #312](https://github.com/ZeOoba/oxford-command-center/pull/312)** (2026-09-05, Gabriel ruled "option C plus the m365 degradation gate"). `loadM365Tasks()` now returns `{tasks, degraded}` with a reason instead of a bare `[]`, mirroring notion-deals' `DealsDegradation`: `not-configured` raises no flag, `token-failed`/`fetch-failed`/`empty-result` raise an error-severity flag that `evaluateReconciliationGate` already refuses on. Also fixed a latent crash — `getGraphToken()` throws (graph-auth.ts:47) and was called OUTSIDE the try at m365-tasks.ts:62, so a token-endpoint hiccup crashed both CLI writers to Exit 3. Live A/B on the real workbook: baseline Exit 0 with tasks 115->59, with fix Exit 1 and portfolio.json unmodified.

**The bake-mirror asymmetry is deliberate, do not "fix" it:** three of the four `portfolio.json` writers refuse on an m365 degradation; `scripts/bake-mirror.ts` only WARNS. A degraded m365 load OMITS rows, whereas the deals degradation bake-mirror refuses on ASSERTS FALSEHOOD (seed placeholders presented as live). Refusing there would turn a transient Graph blip into an hourly external deploy outage.

**Options A and B (the overlay fix) were NOT done by this session** — session 3dec2867 claimed them 11 minutes earlier under slug `oxford-command-center-data`, covering extract-workbook/lease-snapshot-drift-check/ar-import-headless/server/overlay.ts plus both task SKILL.mds. Deliberately not duplicated; see [[feedback_check_active_claims_before_optimization_queue_work_2026-08-13]].
