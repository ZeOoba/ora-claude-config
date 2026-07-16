---
name: feedback-verify-probe-findings-before-acting
description: A probe/lint/diagnostic finding is a hypothesis, not a verdict — verify the flagged artifact before acting on it, since the defect can be in the probe
metadata:
  type: feedback
  originSessionId: 55af5efd-32ba-4fd7-bfe5-692cf8cedbc0
---

A probe, lint, or diagnostic tool's finding names a *symptom location*, not necessarily the *defect location*. Verify the flagged artifact directly before fixing it — the tool itself can be the bug.

**Why:** 2026-07-15, `memory-integrity-probe.py` flagged `reference_newyorkfed_api_403_hosted_fetch.md` as linking a "retired/archived doc." Reading the flagged file showed the link target (`feedback_webfetch_markdown_false_negatives.md`) was live, present, and indexed in MEMORY.md — not retired at all. The actual defect was in the probe: `RETIRED_DOCS` carried a bare `"feedback_"` prefix meant only for 7 specific archived `feedback_*_merged-into-rules_2026-06-03.md` docs, but it also matched every live `feedback_*` file under the current naming scheme. Fixing the *named* file (repointing or deleting a perfectly valid cross-link) would have been the wrong action — chasing the symptom instead of the cause. Fixing the probe (add a presence guard: skip the retired-prefix match if the link target still exists as a live root file) was the correct, general fix, plus it prevented a live cross-link from being destroyed. This generalizes past this one probe: any automated checker (doctrine-integrity, governor-drift, fleet-status, memory-integrity, hook regression suites) can itself carry a bug, and its finding text describes where the checker looked, not necessarily what's wrong.

**How to apply:** before editing whatever a probe/lint/test names as broken, read that artifact directly and confirm the described defect is actually present. If the artifact looks correct on inspection, suspect the checker next — read its matching logic, not just its output — before touching the named file. This is a generalization of [[feedback_verify_subagent_safe_claims]] (verify a workflow's "safe" claim before executing) and [[feedback_verify_registry_mutation_claims]] (a logged mutation isn't confirmed without a re-check) to the automated-tooling case: treat any tool's output as a claim to verify, not a fact to act on, whenever the fix would be destructive, non-obvious, or surprising given what the artifact actually contains.
