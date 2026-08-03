---
name: reference-memory-index-size-gate-is-a-runway-marker
description: "MEMORY.md's size WARN is a runway marker below the real Read-tool limit, not a target size — the harness's own 'compact to under 17.1KB' nag is unsatisfiable for this corpus and must not be obeyed by deleting pointers"
metadata: 
  node_type: memory
  type: reference
  originSessionId: a3a82fa0-28ad-4f86-8e87-44ddc824a30d
  modified: 2026-07-31T13:51:23.318Z
---

**The trap:** after any MEMORY.md edit the harness prints *"The memory index at MEMORY.md is NN.NKB, approaching the 24.4KB read limit. Compact it to under 17.1KB now: keep one line per entry, move detail into topic files, and merge or drop stale entries."* Read literally, that instructs you to **drop live pointers**. For the current corpus it is unsatisfiable without destroying the index. Do not obey it mechanically.

**Measured 2026-07-31** against the live 176-file corpus (182 links, MEMORY.md = 20,455 bytes):

- Stripping **every** hook (the prose after each link), leaving only bullets, links and titles, floors the file at **15,183 bytes** — only 1,917 below the old 17,100 WARN. Satisfying 17.1KB therefore permitted roughly **10 characters of description per entry** across 182 entries. The hook is precisely what recall reads to judge relevance, so at that length the index degrades into a list of filenames.
- The only other route to 17.1KB was deleting **~30 entries — 17% of all memories** (measured mean 112.4 bytes/entry).
- **40% of the file (8,182 bytes) is link targets alone** — the `(filename.md)` paths. Irreducible while the pointers stay.
- The usual escape hatch does not work unaided: all 10 CLOSED/superseded archive candidates were checked file-by-file and **every one has inbound refs from other LIVE memory files** (not just `event_log.md`). Archiving orphans real pointers unless those files are repaired in the same pass.

**What changed.** `maintenance/memory-integrity-probe.py`'s `MEMORY_WARN_BYTES` was recalibrated **17100 → 21500** on Gabriel's in-turn direction (2026-07-31), with the measurements recorded in a calibration comment above the constant, and the WARN text rewritten to name the real levers (archival-with-ref-repair, or splitting) instead of saying "compact". `MEMORY_HARD_BYTES = 24400` is a **real** constraint — past it the index no longer fits in one Read call and index maintenance itself becomes unreliable — and must not be raised.

**What did NOT change, and cannot be fixed here:** the nag quoted above is emitted by the **Claude Code harness itself**, not by any ORA hook (`settings.json` wires only `memory-index-guard.py` and `memory-orphan-link-guard.py`; neither checks size). The probe's 17100/24400 constants were evidently copied from that harness message by an earlier session. **The harness will keep printing "compact to under 17.1KB" no matter what the probe says.** Treat it as advisory and wrong for this corpus; this file is the standing answer.

**The real constraint is still coming.** Headroom to the 24.4KB hard limit is ~2,900 bytes at the new WARN and ~3,900 bytes today — roughly **35 more memories**. The corpus grows monotonically (~112 bytes of index per new memory) while HARD does not scale, so a structural decision is genuinely approaching. Two levers, both real work:

1. **Archive with inbound-ref repair** — move dead entries to `_archive/` (the probe's check-1 glob is non-recursive, so archived files correctly leave the reconciliation set) *and* fix every inbound `[[link]]`/markdown ref in other memory files.
2. **Split the index** — currently **blocked**: check 1 requires every top-level `*.md` to be linked from `MEMORY.md` *itself*, so a sub-index would leave every file it lists reported as "unlisted file". Amending check 1 to follow sub-indexes is the structural fix and needs its own sign-off + tests.

Same failure class as [[reference_claude_md_word_budget_is_a_floor]] — a WARN sitting at or below the honest floor reads as "approaching a limit" and drives trimming that cuts load-bearing content; its ratified point 4 (recalibrate the constant, don't shrink the file to satisfy a marker) is what this change implements. See also [[feedback_verify_before_repeating_session_claims]]: a threshold printed next to a count is not self-explanatory.
