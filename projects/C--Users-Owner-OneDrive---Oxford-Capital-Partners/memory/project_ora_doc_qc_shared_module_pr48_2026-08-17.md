---
name: project-ora-doc-qc-shared-module-pr48
description: "PR #48 (ora-skills) unifies pma-qc/listing-agreement-qc/lease-form-qc's document extraction onto one shared module, closing false-clean/garbled-PDF bugs — awaiting Gabriel's review/merge"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4e2a0ec6-c7aa-4824-87a4-dd5aa1cd1187
  modified: 2026-08-18T00:35:13.038Z
---

✅ **MERGED 2026-08-18** — [ora-skills PR #48](https://github.com/ZeOoba/ora-skills/pull/48), merge commit `5f8b65b`, branch `capture/shared-doc-qc-module-retrofit` (worktree removed, local+remote branch deleted). Built via `subagent-driven-development`: 5 tasks, each implementer→reviewer, plus a final whole-branch review round that caught 2 more issues invisible to any single task's reviewer.

**Why:** `listing_qc.py` scored a scanned no-text-layer PDF as CLEAN (0/25) instead of flagging it unreadable — the worst failure mode for a pre-signature QC gate. `lease_qc.py` had the same root cause (no real format detection) manifesting as garbled-PDF-as-text near-total-failure instead of false-clean. Fixed by factoring extraction/OCR-fallback/UNREADABLE-gate/report machinery into one shared `tools/ora_doc_qc.py`, retrofitting all three scanners onto it.

**Non-obvious finding, reusable pattern:** a shared-module change made during ONE task's retrofit (task 1, extraction field narrowing) silently broke a check in a DIFFERENT already-reviewed skill's file (listing-agreement-qc's L24, footer-blindness) — invisible to that skill's own task-scoped reviewer since the regression's cause lived in a sibling task's commit. Only surfaced in the final whole-branch review pass. **When retrofitting multiple consumers onto a newly-shared module, budget for a genuine whole-branch review after per-task reviews, not just as a formality** — this repo's `subagent-driven-development` skill already mandates one; it earned its keep here twice (also caught: `tests/` dirs shipping into packaged `.skill`s for the first time, no exclusion rule existed).

**Also found and fixed along the way (pre-existing production defects in `lease_qc.py`, now live):** T1 (unfilled-token check) was firing a spurious BLOCK on every real lease ever scanned — its regex matched the scanner's own `[[FOOTER]]` marker artifact. F6 (a late-fee-clause check) was silently dead because ORA's own paper uses a non-breaking space the old pipeline never folded.

**Closed out 2026-08-18:** main checkout's stale untracked `pma-qc/`/`tools/ora_doc_qc.py` (the original pre-retrofit Cowork handoff files) archived to `ora-skills/_archive/2026-08-18_superseded_pre_merge_untracked/` (verified byte-identical copy before removal, not deleted outright) so the fast-forward merge could land without an untracked-file collision. Main checkout fast-forwarded `79c61c5`→`5f8b65b`, worktree removed, branch deleted local+remote. Two unrelated `_archive/` untracked dirs sitting alongside were confirmed unrelated and left untouched throughout.

If Gabriel asks about `ora_doc_qc.py`/PM-agreement QC/listing-agreement-qc false-clean/lease-form-qc T1-false-BLOCK, this is the relevant history. Nothing further pending on this project.
