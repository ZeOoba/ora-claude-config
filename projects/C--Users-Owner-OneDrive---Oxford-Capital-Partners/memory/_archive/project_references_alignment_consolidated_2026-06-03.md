---
name: project_references_alignment
description: ORA reference-library 00_Governance relocation — done vs. open governance decisions
metadata: 
  node_type: memory
  type: project
  originSessionId: e59c389d-4fd4-49b1-a853-f127b7bb86b4
---

The ORA reference library (Voice Register, Standard-Positions, File-Naming Standard) was relocated to the canonical home `Claude_Workspace/00_Governance/References/` (away from `/References/`).

**Done & verified 2026-05-31 (Claude Code):** 6 skill files' File-Naming Standard citations repointed to `00_Governance/` (8 occurrences, verified 0 old / 8 new); `ora-skill-text-audit` scheduled-task citation fixed; Standards file + `_README.md` corrected from the actual Style Guide read. Return handoff written to `00_Governance/References/20260531_Handoff_ClaudeCode-to-Cowork_References-Alignment-Status_v01.md`.

**OPEN — pending Gabriel + Eric (not doable from Code):**
1. **Schema discrepancy:** Style Guide §3.1 = subject-first `ORA_[Subject]_[DocType]_[YYYYMMDD]_v[N][_State]`, but the Standards file + observed practice use date-first `YYYYMMDD_[Property]_[DocType]_v##`. One is stale — must decide canonical.
2. **DocType vocabulary:** Style Guide names only 5 illustrative tokens (ICMemo·LOI·PSA·RentRoll·Deck); no enumerated controlled vocabulary exists. Must define/ratify — do NOT invent.
3. **Naming Standard v1.1 ratification** with Eric: unconfirmed (Notion was down 2026-05-31); check Notion page 35e6ecd8-9e59-8129-af9d-c69b04a3cce2 / Ops Hub decision log.

**Cowork-only:** the CLAUDE.md memory citations for Voice + Standard-Positions still point to the old `/References/` path — must be fixed in the Cowork memory editor (no editable on-disk source). See [[reference_skill_source_paths]].
