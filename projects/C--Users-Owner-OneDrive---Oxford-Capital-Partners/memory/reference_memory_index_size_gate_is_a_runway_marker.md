---
name: reference-memory-index-size-gate-is-a-runway-marker
description: "MEMORY.md's size WARN is a runway marker below the real Read-tool limit, not a target size — the harness's 'compact to under 17.1KB' nag must not be obeyed by deleting pointers. Splitting is UNBLOCKED since 2026-08-03 and used twice; sub-indexes are size-gated too since 2026-08-16 and must be committed with the root index"
metadata: 
  node_type: memory
  type: reference
  originSessionId: a3a82fa0-28ad-4f86-8e87-44ddc824a30d
  modified: 2026-08-16T19:23:00.058Z
---

**The trap:** after any MEMORY.md edit the harness prints *"The memory index at MEMORY.md is NN.NKB, approaching the 24.4KB read limit. Compact it to under 17.1KB now: keep one line per entry, move detail into topic files, and merge or drop stale entries."* Read literally, that instructs you to **drop live pointers**. For the current corpus it is unsatisfiable without destroying the index. Do not obey it mechanically.

**Measured 2026-07-31** against the live 176-file corpus (182 links, MEMORY.md = 20,455 bytes):

- Stripping **every** hook (the prose after each link), leaving only bullets, links and titles, floors the file at **15,183 bytes** — only 1,917 below the old 17,100 WARN. Satisfying 17.1KB therefore permitted roughly **10 characters of description per entry** across 182 entries. The hook is precisely what recall reads to judge relevance, so at that length the index degrades into a list of filenames.
- The only other route to 17.1KB was deleting **~30 entries — 17% of all memories** (measured mean 112.4 bytes/entry).
- **40% of the file (8,182 bytes) is link targets alone** — the `(filename.md)` paths. Irreducible while the pointers stay.
- The usual escape hatch does not work unaided: all 10 CLOSED/superseded archive candidates were checked file-by-file and **every one has inbound refs from other LIVE memory files** (not just `event_log.md`). Archiving orphans real pointers unless those files are repaired in the same pass.

**What changed.** `maintenance/memory-integrity-probe.py`'s `MEMORY_WARN_BYTES` was recalibrated **17100 → 21500** on Gabriel's in-turn direction (2026-07-31), with the measurements recorded in a calibration comment above the constant, and the WARN text rewritten to name the real levers (archival-with-ref-repair, or splitting) instead of saying "compact". `MEMORY_HARD_BYTES = 24400` is a **real** constraint — past it the index no longer fits in one Read call and index maintenance itself becomes unreliable — and must not be raised.

**What did NOT change, and cannot be fixed here:** the nag quoted above is emitted by the **Claude Code harness itself**, not by any ORA hook (`settings.json` wires only `memory-index-guard.py` and `memory-orphan-link-guard.py`; neither checks size). The probe's 17100/24400 constants were evidently copied from that harness message by an earlier session. **The harness will keep printing "compact to under 17.1KB" no matter what the probe says.** Treat it as advisory and wrong for this corpus; this file is the standing answer.

**The two levers:**

1. **Archive with inbound-ref repair** — move dead entries to `_archive/` (the probe's check-1 glob is non-recursive, so archived files correctly leave the reconciliation set) *and* fix every inbound `[[link]]`/markdown ref in other memory files.
2. **Split the index** — ~~currently blocked~~ **UNBLOCKED and used twice.** Check 1 was amended **2026-08-03** to follow sub-indexes: `collect_indexed_links()` unions `MEMORY.md`'s links with those of each `INDEX_*.md` **that MEMORY.md itself links**. Deliberately ONE level, no chaining, and a stray `INDEX_*.md` the root index doesn't adopt grants no coverage — it keeps reporting as an unlisted file. A linked-but-missing sub-index stays an ordinary orphan. The probe's own docstring cites *this memory by name* as the thing it was unblocking.

**Splits executed:** `INDEX_reference.md` (2026-08-03, Reference section) · `INDEX_projects_system.md` (2026-08-16, Projects & system — 9,093 B / 46 entries, the largest section by more than the next two combined; root index 22,688 → 16,936 B, headroom to HARD ~1,700 → ~7,464 B). Probe green after each: `267 files indexed, 267 present`. **Splitting rule learned:** the sub-index is NOT auto-loaded, so anything that must be seen *without* opening a file stays in the root — navigational anchors, OPEN/BLOCKED and PENDING items, standing ⛔/⚠️ operational constraints, open governor items, and the newest entry in any series.

**⚠️ Commit coupling — the sharp edge.** `head_orphans()` reads each followed sub-index from **git HEAD, not disk**, precisely so an uncommitted sub-index can't vouch for pointers no other reader can resolve. So `MEMORY.md` and any sub-index it adopts **must land in the same commit**. Committing the root index alone, while the sub-index is untracked, makes the sub-index an orphan pointer and everything it lists unreachable to a clone — a real FAIL. Both uncommitted together is safe (HEAD stays internally consistent).

**The split moved the bound rather than removing it — found and CLOSED the same day.** Check 0 used to stat `MEMORY.md` alone, so the very files absorbing the growth were themselves ungated: `INDEX_reference.md` had reached **18,361 B, larger than the 16,936 B root it was split out of**, ~6 KB from the same ceiling, with nothing that would ever warn. Same unbounded-growth defect class the Automation Audit found in the System Schematic and in its own rev-log — **the fix for a bounded artifact created an unbounded child.** Fixed in `8d5b7d9` (2026-08-16): check 0 now stats `MEMORY.md` **and every sub-index it adopts**, on the same constants and the same severities — a sub-index past HARD is exactly as unreadable as the root, so demoting it to a warning would rebuild the blind spot one level down. Collection (`sized_index_files()`) and threshold arithmetic (`size_gate()`) were split so both are testable; tests 29/29, with the gate verified to actually fire by lowering the constants against the live corpus. **Measured 2026-08-16 (all under WARN, so the gate is silent by design, not absent):** `MEMORY.md` 17,388 B · `INDEX_reference.md` 18,361 B · `INDEX_projects_system.md` 7,856 B. `INDEX_reference.md` is the one to watch — largest of the three and the next likely to breach.

**The meta-lesson, which is why that commit called the stale wording out instead of quietly deleting it:** the calibration comment above the constants still said splitting was blocked ~2 weeks after check 1 was amended, and it misbriefed a whole archival task on 2026-08-16. Text sitting next to a constant is read as current. Same failure mode as [[feedback_prompt_current_state_prose]].

Same failure class as [[reference_claude_md_word_budget_is_a_floor]] — a WARN sitting at or below the honest floor reads as "approaching a limit" and drives trimming that cuts load-bearing content; its ratified point 4 (recalibrate the constant, don't shrink the file to satisfy a marker) is what this change implements. See also [[feedback_verify_before_repeating_session_claims]]: a threshold printed next to a count is not self-explanatory.
