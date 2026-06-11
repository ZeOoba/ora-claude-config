# /plan

Structure any multi-step problem before executing. For multi-step **coding** work this maps onto **superpowers:writing-plans** (bite-sized TDD tasks); for ops/docs use the structure below.

## Trigger
Any task with >3 steps or any irreversible action.

## Output structure
1. **Objective** — one sentence: what does success look like?
2. **Constraints** — what must be preserved/avoided (hard guardrails: no website, no business-OneDrive writes, no email/money without permission; no confidential data on external surfaces).
3. **Steps** — ordered; each: what happens · what could go wrong · how to verify.
4. **Risk assessment** — reversible or not? blast radius if step N fails? confirmation required?
5. **File inventory** — to create / to modify / **must not be touched**.

## Rules
- Never skip step 4 for financial models or external communications.
- Always show the file inventory before writing anything.
- Flag CONFIDENTIAL if any step involves a `confidential-terms.json` term.
- For coding plans, hand the result to **superpowers:writing-plans** so tasks are TDD-shaped.
