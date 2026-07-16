# Reusable Command-Center self-audit pipeline

The autonomous audit→improve run that produced PR #28 is packaged here as reusable named workflows.
This is the **recurring re-audit mechanism** of the data-flywheel (the "learn from my data" goal): run
it on a cadence against a fresh worktree to keep the command center continuously audited and improving.

## Workflows
- **`cc-audit-army`** — Phase 1. 9-dimension read-only audit → mechanical verify → root-cause dedup →
  ranked Audit Report. Returns `{ mode, worktree, summary, reportMarkdown, ranked, confirmedFindings, counts, coverageNotes }`
  (`counts.unverified` > 0 means a verifier agent died and those candidates were dropped, not refuted — re-run to verify them).
- **`cc-eval-plan-premortem`** — Phases 2–4. Evaluation vs goals + master-plan matrix → extended
  tiered plan + design-only data-flywheel → adversarial pre-mortem → hardened plan + a
  pressure-tested Tier-A selection. Reads the audit artifacts from `<worktree>/_run/`.

Both take the target via `args.worktree` (default `C:/Users/Owner/oxford-command-center`).

## Generic mode — auditing any repo (2026-07-16)
`cc-audit-army` also runs against **any** repo: additionally pass `args.brief` (1–3 operator sentences —
what the repo is + audit intent). A Phase-0 **Orient** scout then reads the target repo and derives the
ground truth + per-dimension focus paths that are baked in for the command center; the 9-lens → dedup →
verify → rank engine is unchanged. Without `args.brief`, cc mode runs (curated ground truth + baked
focus paths + the baseline-refresh scout below). A malformed `args.brief` (empty/non-string) throws
rather than silently degrading to cc ground truth against a foreign repo. Regression + generic-mode
tests live in `_tests/` (`node _tests/test.mjs` — mock-DSL harness; `cc-mode-prompts.snapshot.json`
byte-pins the cc-mode prompts — changing cc prompt content requires deliberately re-snapshotting via
`node _tests/test.mjs snapshot` and noting it here + in the event log).

    Workflow({ name: 'cc-audit-army', args: {
      worktree: 'C:/Users/Owner/ora-pm',
      brief: 'ORA property-management app: React + Supabase tenant portal. Audit before Phase-2 UX push.',
    } })

Caveats: still claim an isolated worktree first (single-writer rule applies to every repo);
`cc-eval-plan-premortem` stays command-center-specific (F1–F13 matrix, master plan) — do **not** chain
it after a generic-mode audit; the generic Rank phase still orders by the ORA goal hierarchy.

### Model-floor override
Optionally pass `args.forceModel` (e.g. `'opus'`) to pin **every** dispatch — Orient, all 9 dimensions,
Dedup, Verify, Rank — to one model, overriding each dimension's individual default (4 of 9 default to
sonnet). No-op when omitted. Use this to honor a standing per-repo model-tier rule — e.g.
[feedback_website_model_tier.md](../projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/feedback_website_model_tier.md)
requires opus-only for all website-canonical work, never sonnet/haiku:

    Workflow({ name: 'cc-audit-army', args: {
      worktree: 'C:/Users/Owner/website-canonical',
      brief: 'ORA public marketing site: Next.js on Netlify, deployed via oxfordra.net.',
      forceModel: 'opus',
    } })

### CC-mode baseline refresh (2026-07-16)
cc mode no longer audits against a frozen ground truth. The baked `BASELINE = origin/main @ 823574d`
sha + fixed ALREADY-DONE list rotted as main advanced (192 commits behind by 2026-07-16), telling
auditors a stale sha was "the authoritative current state" and producing re-reported non-gaps. A
Phase-0 **cc-refresh** scout (fail-closed like Orient; honors `forceModel`) now re-derives per run:
(1) the worktree HEAD as the baseline, and (2) an "ALREADY-DONE — NEWER" line from CHANGELOG / specs /
`git log 823574d..HEAD`, including corrections to curated claims that have since changed (e.g. later
ruleset ratification). The curated knowledge (delta-only framing, governor-surface intent) and the
baked per-dimension focus paths stay. `cc-mode-prompts.snapshot.json` was deliberately re-snapshotted
the same day to pin the new 13-call cc pipeline (was 12).

## How to run (recurring self-audit)
1. Claim a clean isolated worktree off `origin/main` (single-writer rule):
   `git -C C:/Users/Owner/oxford-command-center worktree add <wt> -b audit-<date> origin/main`
2. Audit:    `Workflow({ name: 'cc-audit-army', args: { worktree: '<wt>' } })`
   - Persist `reportMarkdown` → `<wt>/_run/AUDIT-REPORT.md` and `confirmedFindings` →
     `<wt>/_run/confirmed-findings.json` (the eval phase reads these paths).
3. Eval/plan: `Workflow({ name: 'cc-eval-plan-premortem', args: { worktree: '<wt>' } })`
4. Self-gate, implement the ≤2 Tier-A items, push a DRAFT PR, file the rest to the
   ratification backlog. (See the autonomous prompt: `~/.claude/prompts/command-center-autonomous-review-v2.md`.)

## Guardrails (carried in every agent prompt)
Read-only audit agents · opus floor for financial/governor/confidential lanes · file:line + verbatim
excerpt required on every finding · delta-only vs the ratified master plan · already-done excluded ·
confidential terms redacted · the **pre-push confidentiality hook** (`scripts/prepush-confidential-scan.mjs`,
installed via `npm run hooks:install`) gates every push fail-closed.

## Standing recommendation (worktree-per-session — systematization #4)
The shared `oxford-command-center` checkout is single-writer; two sessions collided on it again during
this run. Always claim an isolated worktree before touching the repo (step 1). A future hardening is a
launch/pre-commit guard that refuses to operate on the shared `main` working tree when another writer's
uncommitted work is present — tracked as a recommendation, not yet built.
