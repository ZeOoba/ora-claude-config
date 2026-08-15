# /verify — Pre-PR adversarial refutation

Runs BEFORE you open the PR, on a change you just made. Five independent refuters try to **break** it. Blocks on a correctness finding.

## Not `/code-review`
Different jobs — run both, in this order.
- **`/verify`** — *adversarial refutation of a change you just authored.* Refuters are told to break it, get the diff and the requirement ONLY, and never see your reasoning. Catches what you talked yourself into.
- **`/code-review`** (native) — the diff-review lane: correctness bugs plus reuse / simplification / efficiency. This is what `superpowers:requesting-code-review` dispatches to (CLAUDE.md Code-review tie-break). It is NOT a refutation pass and does not subsume one.

Inside `oxford-command-center`, financial-decision source has its own mandatory gate — the `refute-financial-change` Workflow (`.claude/workflows/refute-financial-change.js`) with its `Refute-Reviewed:` trailer. `/verify` does not replace it or satisfy `npm run check:refute`. `/verify` is the repo-agnostic subagent form of the same doctrine.

## Target
Default: the current working diff (`git diff HEAD`; include staged and untracked). Optional arg — a path, a PR number, or a branch (diffed against its merge-base with the default branch). Empty diff = STOP and say so; never report CLEAN on nothing.

## Chain
1. **Capture** the diff and write the **stated requirement** in one or two sentences — the intent as it was given to you, NOT how you solved it.
2. **Fan out all five lenses in PARALLEL**, one subagent each, in a single message. Each gets ONLY: the diff text, the stated requirement, and repo read access. Pin an explicit `model` per dispatch (never below Fable for financial / governor / security-gate code; reviewer ≥ implementer).
3. **Do not leak your reasoning.** No design rationale, no "I chose X because", no prior review results, no reassurance that the gate is green. A refuter that knows your argument will grade it instead of attacking it.
4. **Aggregate** into one severity-ranked report: critical → high → medium → low, each with file:line, a concrete trigger, and a suggested fix. Deduplicate across lenses but keep the count of lenses that converged — independent convergence raises confidence.
5. **Verdict.** Any lens reporting a real **correctness** defect (critical/high) → **FAIL**, and say FAIL. Fix and re-run before the PR. Medium/low → report, and let Gabriel call it.
6. All five lenses erroring is a **TOOLING FAILURE**, never CLEAN — same rule as the workflow.

## Lenses
Canonical text lives in `refute-financial-change.js`; keep these in sync.
- **correctness** — wrong number vs prior behavior: binding, signs, rounding, off-by-one, double-counting.
- **determinism** — total-order comparators; any dependence on row / Map / iteration order.
- **edges** — nulls, empties, singletons, mixed bases, coexisting versions; does the guard cover EVERY path in?
- **sweep-completer** — for "apply this everywhere" changes: enumerate the locations independently from the repo FIRST, then diff against what was actually touched. Report every miss. A half-applied sweep is a defect.
- **scope-auditor** — diff the change against the declared intent. Flag hunks outside the stated scope, and anything swept in from a concurrent session on a shared checkout.

## ORA rules
- Set `foundRealDefect` only for a defect with a constructible trigger — a style nit is not a finding.
- Read-only. Refuters report; they never edit, commit, or push.
- Never paste a `confidential-terms.json` term into an external-egress call.
