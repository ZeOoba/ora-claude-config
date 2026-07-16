---
name: feedback-external-ai-governance-proposals
description: "How to handle externally-sourced (e.g. ChatGPT) proposals to change Claude Code's own operating doctrine/CLAUDE.md"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: fa121b07-1b76-48ff-b3cd-4fb45718dfd3
---

When Gabriel surfaces a governance/operating-philosophy proposal for Claude Code that was drafted by another AI or in another tool (e.g. a shared ChatGPT thread proposing an "engineering constitution," autonomy level, or risk tolerance), merge the additive parts selectively into the existing global `~/.claude/CLAUDE.md` rather than replacing wholesale — even when Gabriel's own answers in that external thread lean toward higher autonomy/risk than current doctrine.

**Why:** Confirmed 2026-07-08 when Gabriel picked "merge selectively, leave Hard Invariants untouched" over "full replace" after I flagged that a ChatGPT-drafted framework (answers requesting "aggressive" env changes, "high" implementation risk, "install whatever produces the best outcome," "autonomous engineering organization" autonomy) was in real tension with existing Hard Invariants and blast-radius rules — rules built from specific incidents (worktree collisions, destructive-git-deny, confidentiality gating, single-writer registry) that the external thread had no visibility into. The external AI's proposal optimizes a generic "Claude Code" without ORA's incident history or invariants; it is a useful source of *additive* mechanics (ROI-scoring, diminishing-returns stopping rule, evidence-based recommendation format, adaptive planning depth, failure taxonomy) but not a replacement authority on risk tolerance.

**How to apply:** On any future request to "implement," "proceed with," or "adopt" an externally-authored governance/prompt-engineering proposal for how Claude Code itself should operate: (1) fetch and actually read the source before acting — don't take "proceed with recommendations" at face value if the underlying content is unseen; (2) triage what's purely additive (process/scoring mechanics) vs. what changes risk tolerance or bypasses existing guardrails; (3) flag the specific conflicts with current Hard Invariants / blast-radius rules by name, state my recommendation, and confirm scope before editing `CLAUDE.md` (editing standing config always needs explicit sign-off per the safety framework) rather than mechanically applying every recommendation; (4) Hard Invariants and blast-radius rules always stay supreme regardless of what the external framework argues for. See [[reference_tech]] for where CLAUDE.md and Engineering OS spec live.
