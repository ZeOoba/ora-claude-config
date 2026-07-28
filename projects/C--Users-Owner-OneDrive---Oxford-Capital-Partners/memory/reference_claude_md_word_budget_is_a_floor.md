---
name: reference-claude-md-word-budget-is-a-floor
description: "CLAUDE.md's 1700-word probe WARN is a consolidation FLOOR marker, not a ceiling being approached — trimming toward it cuts load-bearing doctrine; the real gate is FAIL at 1850"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 5e4a9dbe-c799-4e0e-b709-059286471562
  modified: 2026-07-28T17:10:10.466Z
---

**The trap:** `doctrine-integrity-probe.py` prints `CLAUDE.md size: NNNN words (warn > 1700, fail > 1850)` on every pre-push. At ~1694 words this reads as "nearly at the limit — trim it." **That reading is backwards and acting on it damages doctrine.**

**What the numbers actually mean** (rationale lives in the calibration comment at `maintenance/doctrine-integrity-probe.py` ~line 234, and in the now-archived `_archive/project_claude-md-formal-audit_closed_2026-07-21.md` Phase 2 entry):

- **WARN 1700 = the consolidation FLOOR.** Two independent full-file consolidation passes — each probe-verified at 0 cross-file duplication with every skill/file ref still `[OK]` — both bottomed out at **~1700–1755 words as the honest floor for CLAUDE.md's legitimate scope**. Below that you are cutting Hard Invariants or skill-routing rules that fixed real bugs. WARN sits at the floor so the weekly report nudges *before* the gate bites, not because the file is too big.
- **FAIL 1850 = the real gate,** set ~95 words above the true count **on purpose** as a **one-in-one-out forcing function**: additions get a small buffer, but anything past it demands an equivalent trim in the SAME change. It operationalizes CLAUDE.md's own "adding a rule means moving one down a layer" principle into a measurable gate.
- Both were **recalibrated 2026-07-08** (warn 1450→1700, fail 1590→1850). The old 1590 was a stale point-in-time snapshot of pre-trim v1, never a principled ceiling.

**Consequences for anyone asked to "trim CLAUDE.md":**

1. **Check the live count first** (`python maintenance/doctrine-integrity-probe.py`) and compare to **1850**, not 1700. In the 1694–1755 band the correct answer is usually **"don't"** — Gabriel ruled exactly that on 2026-07-28 when the 1694/warn-1700 line was misread as approaching a limit.
2. **Cross-file duplication is already 0** (`>= 12`-word shared runs). The cheap redundancy was harvested in the prior passes — there is no free text left to reclaim, only phrasing compression with real semantic risk in a file that IS the operating prompt.
3. **A genuine reduction is relocation, not deletion** — move a whole rule down a layer (`tech.md` / `rules.md` / `standards.md`) and leave a pointer. Deleting to hit a number is how invariants quietly disappear.
4. If the WARN line itself is the irritant, the honest fix is **recalibrating WORD_BUDGET_WARN upward**, not shrinking the file to satisfy a marker. That edits a guard constant — needs deliberate sign-off.

**Why this was easy to get wrong:** the rationale was recorded only in an archived audit file that MEMORY.md does not link, so it was undiscoverable without a targeted grep — a live instance of the "one fact, one home" failure the doctrine warns about. See [[feedback_verify_before_repeating_session_claims]]: a threshold printed next to a count is not self-explanatory; read the calibration before acting on it.
