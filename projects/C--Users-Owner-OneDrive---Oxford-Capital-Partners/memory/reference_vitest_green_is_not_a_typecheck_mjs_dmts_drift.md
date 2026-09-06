---
name: vitest-green-is-not-a-typecheck-mjs-dmts-drift
description: "A green vitest run proves nothing about types — vitest transpiles without typechecking, so a `.mjs` whose hand-maintained `.d.mts` has drifted passes the whole suite while `npm run typecheck` fails. Broke oxford-command-center's main TWICE in one week, on two different files."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 17b5a493-b800-4a3f-bf2b-870ac5127c7d
  modified: 2026-08-24T17:22:48.230Z
---

On `oxford-command-center`, `scripts/*.mjs` files carry a **hand-maintained** sibling `.d.mts` declaration file. Nothing enforces that the two stay in sync. When a function is added to the `.mjs` and not to the `.d.mts`, any `.ts` test importing it fails `tsc` — while vitest passes, because **vitest transpiles without typechecking**.

## The observable shape

3762/3762 tests pass. `npm run typecheck` exits 2:

```
TS2724  no exported member 'scanDiffForConfidentialFlag'. Did you mean 'scanDiffForConfidential'?
TS2305  no exported member 'isRegisteredConfidentialRepo'
TS2305  no exported member 'currentRepoName'
TS2578  Unused '@ts-expect-error' directive
```

**The TS2578 is a consequence, not a second bug.** A `@ts-expect-error` over a deliberate bad-input call is reported *unused* precisely BECAUSE the callee is undeclared — an untyped import raises no error to suppress. Adding the declaration makes the directive correct again. Do not "fix" TS2578 by deleting the directive; that hides the real defect and removes a genuine test assertion.

## It is systemic, not a one-off

Two independent breaks reached `main` in the same week (2026-08-24):
- `prepush-confidential-scan.mjs` — 3 functions added by `ead629d`, declarations missing. Fixed by PR #295 (`8c0760f`).
- `install-git-hooks.mjs` — same class, fixed separately on branch `fix-main-typecheck`.

Both landed on `main` via **direct pushes that bypassed PR CI**, so the gate that would have caught them never ran.

Commits: `cafd63c` / `dcdc523` (install-git-hooks), `8048e7b` / `66b2ebf` / `8c0760f` (prepush-confidential-scan, PR #295).

**Four sessions worked this one defect.** `8c0760f` (PR #295) fixed `prepush-confidential-scan.d.mts`; `ec4027d` on branch `claude/quizzical-wozniak-220980` independently added the **identical** three declarations plus the same `ConfidentialFlagHit` interface, and never reached `main`.

⚠️ **A false claim about this propagated through three files before it was caught:** that `ec4027d` "found 3 MORE exports the first three fix attempts all missed," i.e. that the earlier fix was partial. It was not. Verified 2026-08-24 against `origin/main`: the `.d.mts` declares **7** exported functions against **7** in the `.mjs` — matched, so `8c0760f` was complete, and `ec4027d`'s diff adds the same three names. It is duplicate rediscovery, not extra coverage. Do not cite it as evidence of a partial fix. The originating entry was archived to `_archive/` 2026-08-24 as a duplicate of this one.

Open work on the durable fix (convert the `.mjs`/`.d.mts` pairs to native `.ts` so declarations are generated, plus the branch-protection gap that let these reach `main` unreviewed): [[project_ccm_mjs_dmts_parity_and_branch_protection_gap_2026-08-24]]. Duplicate-session angle: [[reference_concurrent_session_duplicate_hardening_work]]. Survey at `8c0760f`: `install-git-hooks.mjs` and `prepush-confidential-scan.mjs` have a `.d.mts`; `ensure-deps.mjs` and `prepush-noi-crosscheck.mjs` do not (harmless only until a `.ts` test imports them).

## How to apply

- **Never cite a passing vitest run as evidence that a change typechecks.** Run `npx tsc --noEmit -p tsconfig.json` separately, or `npm run gate:ci`, which includes the typecheck step. Running a hand-picked subset of test files is weaker still — it cannot see a failure in a file you did not select.
- Touching any `scripts/*.mjs` export surface → update the sibling `.d.mts` in the same commit.
- The durable fix is to stop hand-maintaining the pair (convert these scripts to TypeScript, or generate declarations). Two breaks in one week is the argument; recorded as an open recommendation, not done.

**Why this kept happening:** [gate vs gate:ci divergence](feedback_command_center_gate_vs_gate_ci_divergence.md) already says to run `gate:ci` locally rather than a hand-assembled substitute — and following it would have caught this too. That entry frames the risk as *build*-vs-test; this one is *typecheck*-vs-test. Same root habit, different step of the pipeline.

Related: [Command Center CRLF Hazard](reference_command_center_crlf_hazard.md) · [verified null vs inferred null](feedback_verified_null_vs_inferred_null.md) — a green that could mean "didn't look" is the same failure class. [[feedback_refute_pass_proactive_default]]
