---
name: feedback-refute-pass-proactive-default
description: "Run the mandatory adversarial refute pass on financial-decision code proactively, before presenting it as done — don't wait to be asked"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 909eeb4c-d321-40d2-a4e2-c592aa9f393d
---

Run the mandatory adversarial refute pass (`refute-financial-change` workflow or equivalent) on any change to financial-decision code — engine math, scoring, benchmarking, NOI, or anything feeding capital-allocation — **proactively, before presenting the work as done or asking for review**. Do not wait for Gabriel to notice a failing `refute-required` CI check and tell me to run it.

**Why:** Engineering OS already states this as mandatory doctrine ("financial-decision code ... ALSO gets a MANDATORY adversarial REFUTE pass"), but on 2026-07-14 I shipped and opened a PR (oxford-command-center #210, RCT v03 engine change) without running it, and only did so after Gabriel pointed at the failing CI check. When run, it caught two real, critical/high-severity defects on the first pass: `basisFullCreditDiscount` left below the recalibrated vintage floors (collapsed the Basis scorecard into a step function — a marginal-clear deal and an exceptional deal scored identically), and a client/server divisor mismatch (`low` vs `mid`) that could show a contradicting pass/fail badge for the same deal. A green `npm run gate` did not catch either — both required a hostile, break-it reviewer pass. Gabriel's response to seeing this ("do that by default going forward") confirms the proactive timing, not just the requirement.

**How to apply:** On [[claude-md]]-governed surfaces (Code), the moment a diff touches engine math / scoring / benchmarking / NOI / capital-allocation code, run the refute pass as part of finishing the change — before declaring gate-green, before opening or updating a PR, before telling Gabriel it's ready. Model choice: default to the workflow's own committed default (Fable, per the CLAUDE.md invariant "confidential/financial/governor code never below Fable" and the hardcoded model in `.claude/workflows/refute-financial-change.js`). Gabriel's one-time "use sonnet 5, not fable" instruction on 2026-07-14 was scoped to that specific dispatch (in-turn instruction, not a restated doctrine change) — do not silently generalize it into a permanent model-tier override; ask again if unsure, don't assume.

Related: [[feedback_website_model_tier]] (a similar per-scope model-tier override, different domain — same pattern of "don't over-generalize an in-turn model instruction").
