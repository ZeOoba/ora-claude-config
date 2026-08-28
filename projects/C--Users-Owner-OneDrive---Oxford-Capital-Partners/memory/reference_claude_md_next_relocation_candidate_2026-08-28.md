---
name: reference_claude_md_next_relocation_candidate_2026-08-28
description: "Pre-picked next candidate to relocate out of CLAUDE.md when headroom tightens again against the 1,850-word FAIL gate — so the next pass doesn't scramble to find one"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f586e192-8cc3-4721-ac32-be5f5df8d775
  modified: 2026-08-28T17:40:12.755Z
---

**Standing minimum-headroom policy (Gabriel-directed, 2026-08-28):** rather than reacting each time CLAUDE.md nears its FAIL gate, keep one pre-picked relocation candidate on record here, and refresh it whenever the current one gets used.

**Used 2026-08-28:** the Engineering OS section's `Shared-checkout = SINGLE-WRITER` bullet — verified live via the pre-push doctrine probe at 1,848/1,850 words (2 words of headroom; an earlier same-session `wc -w` reading of 1,712 was a tool-counting artifact, not the real number — trust the probe's `len(text.split())`, not `wc -w`, if the two ever disagree again). Its procedural detail (worktree-claim + never-force-a-contaminated-tree) moved to [[rules]] §14, which already covered the adjacent fetch/`-sb`/staged-index discipline — CLAUDE.md now carries a one-line pointer. Net: 1,848 → 1,793 words, 55 freed, [[rules]] §14 gained the merged detail.

**Next candidate, pre-picked:** the same section's `Calibrate:` bullet (line ~76) already points to `tech.md §3f` for "Bypass/check detail" — but the 8-item guard-script list (`doctrine-integrity-probe.py · governor-drift-probe.py · git-prepush-doctrine-gate.py · eos-telemetry · eos-plan-gate · eos-claude-md-guard · commit-provenance-guard.py · commit-provenance-recorder.py`) still sits inline in CLAUDE.md itself. That roster is exactly the kind of enumerable detail `tech.md §3f` already exists to hold — move the list there, leave `Guards: roster in tech.md §3f (all fail open).` Estimated savings: ~25-30 words.

**How to apply:** when a session sees WARN-or-tighter headroom, don't invent a new candidate from scratch — pull this one, verify it's still accurate (guard names may have changed), execute the same move-and-pointer pattern, then update this file's "Used" section and pick the next candidate before closing out.
