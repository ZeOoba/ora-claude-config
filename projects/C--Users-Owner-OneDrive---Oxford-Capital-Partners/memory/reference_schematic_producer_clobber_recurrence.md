---
name: reference_schematic_producer_clobber_recurrence
description: "Claude Code System Schematic artifact has clobbered twice (07-18, 07-23) — ad-hoc fleet-only rechecks edit the published artifact directly without touching the durable source file"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f541d0e4-0957-49c7-8ce7-0321ddaa3f63
  modified: 2026-07-23T18:41:26.620Z
---

The "Claude Code — System Schematic" artifact (published at `https://claude.ai/code/artifact/4ad3530d-f84f-4def-a472-d16ef107e74c`) has a recurring divergence pattern between two copies of the same content:

- **Durable source**: `C:\Users\Owner\.claude\artifacts\claude-code-schematic.html` — owned by the scheduled task [[ora-cc-schematic-refresh]] (2×/week, Mon+Thu 14:15 ET).
- **Published artifact**: the live claude.ai page, editable in place by any session that calls the Artifact tool with matching `url`.

**Twice now** an ad-hoc interactive session did a "quick fleet-status recheck" and republished straight to the artifact URL without ever touching or even knowing about the durable source file — advancing the artifact 1-3 revisions ahead of the source. First occurrence: 2026-07-18 (source rev-16 vs published rev-17c, 3-way merge needed). Second: 2026-07-23 (source at 07-20a, artifact at 07-21b after three ad-hoc revs 07-20b/07-21a/07-21b).

**Why it hasn't caused data loss:** the scheduled task's SKILL.md carries a mandatory producer-clobber pre-check — before editing, it WebFetches the live artifact, compares REV markers against the source file, and if the artifact is ahead, pulls the artifact's content into the source before applying that run's edits. This has self-healed both occurrences with zero lost revisions.

**Why it's not being escalated to a hard gate:** the drift is fully self-healing via the existing pre-check, non-destructive, and low-frequency (2 occurrences over ~2 weeks of ad-hoc usage). Adding a PreToolUse guard or registry-level lock for a single cosmetic dashboard artifact would be disproportionate machinery for a problem the read-before-write check already absorbs — the actual gap is discoverability, not enforcement.

**The actual fix applied (2026-07-23):** documenting the pattern here (auto-loaded via MEMORY.md) so any future interactive "fleet recheck" session on this artifact knows two things before republishing:
1. The durable source file exists at the path above and should be edited (via targeted Edit calls, not full rewrite) alongside any republish — not skipped just because "it's just a quick recheck."
2. If skipping the source edit anyway (e.g., a genuinely narrow one-off), that's fine — [[ora-cc-schematic-refresh]]'s pre-check will absorb it next scheduled run. No corrective action is required in the moment; this note exists so nobody spends time investigating the divergence as a novel bug if it recurs a third time.

**If a third occurrence happens:** don't re-investigate from scratch — it's the same known pattern; the pre-check will absorb it exactly as it did the first two times. But a third occurrence would mean this memory note alone didn't close the gap, and cataloging the same drift indefinitely without changing anything is not itself a fix — at that point, actually decide (with Gabriel) whether ad-hoc fleet-only rechecks against this artifact should be retired in favor of routing through [[ora-cc-schematic-refresh]] exclusively, rather than writing a third reference note.
