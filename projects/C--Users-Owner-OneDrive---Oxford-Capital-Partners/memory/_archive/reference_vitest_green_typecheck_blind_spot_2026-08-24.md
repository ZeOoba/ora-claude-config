> **ARCHIVED 2026-08-24 — duplicate.** Superseded by
> [vitest green is not a typecheck](../reference_vitest_green_is_not_a_typecheck_mjs_dmts_drift.md),
> written 2 minutes earlier by a parallel session on the same lesson. All inbound refs were
> repointed there. NOTE: the `ec4027d` claim below ("3 MORE exports the first three fix attempts
> all missed") is FALSE — `ec4027d` re-added the same three declarations `8c0760f` had already
> landed; `main` declares 7 of 7. Kept verbatim as the audit trail, not as fact.

---

---
name: reference-vitest-green-typecheck-blind-spot
description: "A green vitest run on oxford-command-center is NOT evidence of a passing typecheck -- vitest transpiles without typechecking, so a hand-maintained .d.mts declaration file can drift from its .mjs implementation and every commit's own local test run stays green while `npm run typecheck` is red on main. Recurred at least twice in one week (install-git-hooks.mjs, then prepush-confidential-scan.mjs)."
metadata: 
  node_type: memory
  type: reference
  modified: 2026-08-24T16:26:57.392Z
  originSessionId: db26e2f7-e9ce-40b8-a547-579adc17457b
---

**What happened.** Twice in the week of 2026-08-17 to 2026-08-24, a commit added new
exports to a hand-maintained `.mjs` script in `oxford-command-center/scripts/` (
`install-git-hooks.mjs`, then `prepush-confidential-scan.mjs`) without updating the
sibling hand-written `.d.mts` declaration file beside it. Each time, `npm run typecheck`
went red on `main` (TS2724/TS2305 "no exported member", plus a cascaded TS2578 unused
`@ts-expect-error`) while the introducing commit's own `vitest` run passed clean --
vitest transpiles TypeScript/JSDoc types away before running, so it never sees a type
error. See commits `cafd63c`/`dcdc523` (install-git-hooks) and `8048e7b`/`66b2ebf`/
`8c0760f`/`ec4027d` (prepush-confidential-scan, the last one catching 3 MORE exports the
first three fix attempts all missed) in `oxford-command-center`.

**Why:** `.d.mts` files are hand-maintained, not generated from the `.mjs` source, so
nothing forces them to move together -- and the test suite that runs on every commit
(vitest) is structurally blind to the exact class of defect (type declaration drift)
that this pattern produces. "3762 tests passed" (or any large green count) says nothing
about typecheck status in this repo; they are two independent gates.

**How to apply:** never treat a green `npm test`/`vitest` run in `oxford-command-center`
as evidence that `npm run typecheck` also passes -- run typecheck explicitly (or confirm
CI's separate typecheck job is green) before claiming a change is clean, especially after
touching any `.mjs` file that has a sibling `.d.mts`. The standing fix under discussion is
converting the hand-declared `.mjs`/`.d.mts` script pairs to native `.ts` so the compiler
generates the declarations itself, removing the drift vector entirely rather than
patching each instance after the fact -- see
[[project_ccm_mjs_dmts_parity_and_branch_protection_gap_2026-08-24]] for the concrete
scripts and open design question. Related duplicate-session angle (three independent fix
commits landed for the same defect): [[reference_concurrent_session_duplicate_hardening_work]].
