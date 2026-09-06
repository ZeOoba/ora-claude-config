---
name: reference_claude_md_next_relocation_candidate_2026-08-28
description: "Pre-picked next candidate to relocate out of CLAUDE.md when headroom tightens again against the 1,850-word FAIL gate — so the next pass doesn't scramble to find one"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f586e192-8cc3-4721-ac32-be5f5df8d775
  modified: 2026-09-06T19:00:02.958Z
---

**Standing minimum-headroom policy (Gabriel-directed, 2026-08-28):** rather than reacting each time CLAUDE.md nears its FAIL gate, keep one pre-picked relocation candidate on record here, and refresh it whenever the current one gets used.

**Used 2026-08-28:** the Engineering OS section's `Shared-checkout = SINGLE-WRITER` bullet — verified live via the pre-push doctrine probe at 1,848/1,850 words (2 words of headroom; an earlier same-session `wc -w` reading of 1,712 was a tool-counting artifact, not the real number — trust the probe's `len(text.split())`, not `wc -w`, if the two ever disagree again). Its procedural detail (worktree-claim + never-force-a-contaminated-tree) moved to [[rules]] §14, which already covered the adjacent fetch/`-sb`/staged-index discipline — CLAUDE.md now carries a one-line pointer. Net: 1,848 → 1,793 words, 55 freed, [[rules]] §14 gained the merged detail.

**⛔ Next candidate, pre-picked — RETRACTED 2026-09-06, DO NOT EXECUTE IT.** The candidate was: move the `Calibrate:` bullet's 8-item guard-script list (`doctrine-integrity-probe.py · governor-drift-probe.py · git-prepush-doctrine-gate.py · eos-telemetry · eos-plan-gate · eos-claude-md-guard · commit-provenance-guard.py · commit-provenance-recorder.py`) into `tech.md §3f`, leaving `Guards: roster in tech.md §3f (all fail open).` for ~25-30 words.

**It would break the doctrine probe.** `tech.md` §3f line 89 — the very section proposed as the destination — states: *"CLAUDE.md's guard-liveness check (`doctrine-integrity-probe.py` Check 11) requires the literal 8 backtick-quoted guard names to stay inline on that line — do not relocate the names themselves out of CLAUDE.md, only their explanatory detail."* §3f already holds the explanatory detail; the names are load-bearing **in CLAUDE.md** and Check 11 reads them there. The 08-28 pick was made without reading its own destination section.

Caught 2026-09-06 when a headroom pass went to execute it (1793 → 1817 after adding the blast-radius merge gate, 33 words to FAIL). Nothing was relocated; the gate bullet landed without paying for itself, which is acceptable at 33 words of headroom but leaves the policy owing a candidate.

**NO VALID CANDIDATE IS CURRENTLY ON RECORD.** The next session that needs headroom must pick one *and verify the destination does not depend on the text staying inline* — the failure mode this file exists to prevent has now happened once. Relocation targets are constrained by at least: Check 11 (the 8 guard names), and any other probe check that greps CLAUDE.md for literal content. Grep `doctrine-integrity-probe.py` for what it asserts about CLAUDE.md before nominating anything.

**How to apply:** when a session sees WARN-or-tighter headroom, don't invent a new candidate from scratch — pull this one, verify it's still accurate (guard names may have changed), execute the same move-and-pointer pattern, then update this file's "Used" section and pick the next candidate before closing out.
