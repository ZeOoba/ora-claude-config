---
name: feedback-artifact-citation-requirement
description: Governance/audit artifacts asserting Resolved/Closed/Fully-closed-out without a citation is a recurring pattern — require evidence pointer going forward
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5900e68d-2914-4c15-9f60-65efc5d0a2c2
---

Governance-style artifacts (system schematics, closeout reviews, setup audits) that assert "Resolved," "Closed," or "Fully closed out" without an adjacent citation (task ID, event_log line, or command output) are a recurring defect, not a one-off. On 2026-07-18, three independently-authored, most-recently-updated artifacts (`schematic-working`, `review-v02-working.md`, `Claude Code Setup Audit — 2026-07-09`) were deep-reviewed and all three contained this exact failure mode — including one case where a closeout claim ("the task itself was retired rather than fired") was directly contradicted by live scheduled-task registry state.

**Why:** this is the same pattern already named three separate times in memory — [[feedback_verify_before_repeating_session_claims]], [[feedback_refute_pass_proactive_default]], and [[feedback_verify_registry_mutation_claims]] — but those apply to session claims and registry mutations specifically. This entry extends the pattern to published artifacts, where the failure is more consequential: an artifact is a durable, Gabriel-facing record that gets trusted at face value on a later read, unlike an in-session claim that gets scrutinized in the moment.

**How to apply:** before publishing or updating any governance/audit-style artifact, every Resolved/Closed/Fully-closed-out claim must carry a citation (file path, task ID, event_log line, or command output) in the same sentence or an adjacent one. Claude.ai artifacts are not hook-enforceable (no PreToolUse gate can catch this), so the fix is procedural: stamp a one-line citation-requirement rule near the top of each such artifact itself, and treat "asserted without citation" as equivalent to "unverified" when reviewing one. When in doubt, re-verify against a live source (registry, memory primary file, or a direct tool call) rather than trusting the artifact's own prior-revision text — a prior revision's claim is not ground truth.
