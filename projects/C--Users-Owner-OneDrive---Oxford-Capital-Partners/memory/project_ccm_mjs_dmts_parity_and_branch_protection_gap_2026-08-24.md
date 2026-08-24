---
name: project_ccm_mjs_dmts_parity_and_branch_protection_gap_2026-08-24
description: "oxford-command-center: (1) no enforcement of .mjs/.d.mts export parity caused 2 red-typecheck breaks in a week, 3 duplicate fix commits — fix built and in review as PR #299 (OI-206); (2) main had zero GitHub branch protection so refute-required was bypassable by a direct push — Gabriel enabled it 2026-08-24, CLOSED (OI-205)."
metadata: 
  node_type: memory
  type: project
  modified: 2026-08-24T17:46:19.473Z
  originSessionId: db26e2f7-e9ce-40b8-a547-579adc17457b
---

# oxford-command-center: two flagged gaps, 2026-08-24 — both actioned

Two workflow observations from the same incident window. OI-205 needed a GitHub security
setting only Gabriel could change; OI-206 needed a design decision before it was
mechanical. Both resolved same-session once Gabriel confirmed the approach.

## OI-206 — `.mjs`/`.d.mts` parity has no enforcement — IN REVIEW, [PR #299](https://github.com/ZeOoba/oxford-command-center/pull/299)

`scripts/` hand-maintained `.d.mts` beside only 2 of 4 `.mjs` scripts
(`install-git-hooks.mjs`, `prepush-confidential-scan.mjs`; `ensure-deps.mjs` and
`prepush-noi-crosscheck.mjs` have none). Two real breaks in the week of 2026-08-17 to
08-24, the second triggering 3 near-simultaneous duplicate fix commits from different
sessions (`66b2ebf`, `8048e7b`, `8c0760f`). Root cause and lesson:
[[reference_vitest_green_is_not_a_typecheck_mjs_dmts_drift]]; duplicate-session angle:
[[reference_concurrent_session_duplicate_hardening_work]] (2026-08-24 entry).

**Built plan diverged from the original "convert all 4 to tsx" recommendation** — reading
each script's own header comment surfaced a real constraint the initial "just match the
other 16 tsx-run scripts" framing missed: 3 of the 4 are explicitly "Node built-ins only,
no install step" (the two pre-push scripts run from the raw shared `.git/hooks/pre-push`
with no npm context; `ensure-deps.mjs` self-heals a missing/wiped `node_modules`, so it
can't itself depend on something living in `node_modules`). Shipped instead:
`install-git-hooks.mjs` → `.ts` via `tsx` (safe — only ever invoked through npm-context
calls); `prepush-confidential-scan.mjs` stays `.mjs`, its `.d.mts` now GENERATED from the
source's own JSDoc on every `pretypecheck`/`prebuild` and gitignored rather than
hand-maintained; `ensure-deps.mjs`/`prepush-noi-crosscheck.mjs` untouched (neither was
ever imported by a test for its types, so neither was actually exposed to this drift
class — the original scope over-included them).

**Review round:** PR #299's own bots (CodeRabbit, Qodo) caught 2 real gaps this session's
first pass missed — `npm run build` didn't run the type-generation step (only
`typecheck` did), and `prepare` would hard-fail an `npm install --omit=dev` since `tsx`
is a devDependency. Both fixed (prebuild/pretypecheck hooks; a new
`scripts/prepare-hooks.mjs` that checks tsx is present before invoking it, skipping
gracefully otherwise). One bot finding (".gitignore needs a single-writer claim") was
verified NOT real — no such mechanism exists anywhere in this repo's governance
schema — and rejected with the evidence in the PR thread reply rather than silently
complied with. `package.json` IS on `architecture/ownership.json`'s `architect_owned_files`
list, though, and that finding was real — added a `convert-scripts-mjs-to-ts` entry to
`architecture/status.json` declaring `review_needed: true`, matching this repo's own
established convention.

**Remaining:** CI on PR #299, then merge (holding for Gabriel's go-ahead per the
same-as-branch-protection posture — merging into `main` is a shared-state action).

## OI-205 — `main` had zero GitHub branch protection — CLOSED 2026-08-24

`gh api repos/ZeOoba/oxford-command-center/branches/main/protection` → `404 Branch not
protected`, confirmed live 2026-08-24. `.github/workflows/ci.yml:33` defines a real
`refute-required` job gated on financial-code changes, but nothing tells GitHub to
require it before a merge — and since it's a `pull_request`-triggered workflow, a direct
push to `main` (no PR) never even runs it. This is why the mirror-check's `ESCALATE`
tier (ahead-of-origin, stranded commits past the age threshold —
`ora-command-center-mirror-drift-check` SKILL.md) fired correctly on a recent incident,
but the resolution — a direct push to `main` — sailed past `refute-required` with
nothing to stop it. The gate exists in code; it is not enforced at the platform level.

**Why Claude did not fix this itself:** "Modifying system or security settings" is on the
hard-prohibited action list regardless of how the request is framed or who explicitly
authorizes it — GitHub branch protection is exactly that. Claude drafted `protection.json`
and the exact `gh api -X PUT .../branches/main/protection` command; Gabriel ran it
himself. **Resolution, verified live:** `gh api repos/ZeOoba/oxford-command-center/branches/main/protection`
now returns 200 with `required_status_checks.contexts: ["gate","refute-required"]`,
`enforce_admins.enabled: true`, `allow_force_pushes.enabled: false`,
`allow_deletions.enabled: false`. `required_pull_request_reviews` was left `null`
(status-checks-only enforcement, not hard PR-only landing) — Gabriel's implicit choice by
running the file as drafted; revisit if a future direct push still lands ungated, since
that would mean the check-reporting requirement alone isn't sufficient. Full evidence in
[open-items-tracker.md#OI-205](open-items-tracker.md#OI-205).

Related: [OI-205](open-items-tracker.md#OI-205), [OI-206](open-items-tracker.md#OI-206),
[[reference_vitest_green_is_not_a_typecheck_mjs_dmts_drift]],
[[reference_concurrent_session_duplicate_hardening_work]],
`ora-command-center-mirror-drift-check` SKILL.md (never-push-them-yourself rule — this
finding is why that rule exists).
