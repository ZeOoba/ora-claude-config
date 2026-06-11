# /refactor — Lane L4 (restructure, no behavior change)

## Precondition
- Read the file first; define the ONE concern (performance / clarity / duplication / size).
- **Coverage check:** if the target lacks tests, decide cheaply whether characterization-test cost is worth it; if not, reroute as `/build` (L3) and say so.

## Chain
1. **Characterization tests first** (**superpowers:test-driven-development**) — capture current behavior; watch them pass on the unchanged code.
2. **superpowers:using-git-worktrees** for anything multi-file.
3. Refactor — one concern, no speculative changes, no feature additions.
4. Keep tests green; **superpowers:verification-before-completion**.
5. **superpowers:requesting-code-review** (LOCAL).

## Honest guarantee
Behavior preserved **within the captured suite + named invariants**. NOT guaranteed: performance, memory, timing, error text. State explicitly what changed and what did NOT, and the verification method.

## Common ORA targets
Skills (dedupe sections, standardize Output Format, fix stale paths) · settings.json hooks (simplify pipelines, remove dead hooks) · oxfordra.net CSS/HTML **(read-only unless explicit permission — hard guardrail)** · financial models (named assumption cells, remove dead branches).
