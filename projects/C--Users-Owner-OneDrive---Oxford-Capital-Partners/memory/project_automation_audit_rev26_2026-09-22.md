---
name: project-automation-audit-rev26-2026-09-22
description: ORA Setup Audit Revision 26 (2026-09-22) — investigation only; ora-am-brief disabled and outside the 09-28 resume list; store lags repo on governor-facing skills; MEMORY.md past WARN
metadata:
  type: project
---

Revision 26 of the "ORA Automation Audit" artifact (https://claude.ai/artifact/JBgJjqcCckM3pUeEp2vtQE, Version 26). Four command-bounded threads, all completed. **Nothing executed.** Chains [[project-automation-audit-rev25-2026-09-11]].

**Why:** the fleet dark state this week is deliberate (Gabriel paused CC 09-22→09-28; LAMS re-enable of 11 tasks queued as OI-340), but it hid one real defect.

**Pending Gabriel's call:**
- **R26-1 (ask, highest):** `ora-am-brief` is `enabled:false` in the CC registry (last run 2026-09-22T13:34Z). `ora-routine-pause-resume-09-28/SKILL.md` assumes it was "carved out and never paused" and says never touch it, so the resume will NOT re-enable it. No Daily Brief after 09-22 until someone re-enables it.
- **R26-2 (ask):** account store lags the repo: acquisition-underwriting v4.20 vs v4.22, register-scheduled-task v2.21 vs v2.25. No duplicates (Code-surface ListSkills). Re-import is Gabriel-only.
- **R26-3 (fix):** MEMORY.md 22,411B (> 21,500B WARN); INDEX_reference.md 22,857B; 6 dead OI anchors (OI-270/147/050/140/171/188). The Rev 26 pointer line was NOT added: preflight on MEMORY.md returned CONTESTED (dirty, foreign stale owners). Add it once MEMORY.md is reconciled.
- **R26-4 (fix):** register-scheduled-task body grew 5,817→7,609w (+30.8%) v2.21→v2.25. The retention rule bounds only the changelog.

**Remediation, same day (Gabriel: "Re-enable ora-am-brief then fix"):**
- R26-1 done: ora-am-brief `enabled:true`.
- R26-3 done: MEMORY.md 19,807B; INDEX_reference.md 18,194B via the new `INDEX_reference_git_windows.md`.
- R26-4 + R26-8 done: ora-skills `275bb39`, Opus-reviewed. .bak snapshots are in `~/.claude/artifacts/archive/2026-09-22_bak-snapshots/`.
- R26-2 still needs Gabriel's Save-skill click on `ora-skills/_staging/2026-09-22_R26-2_reimport/*.skill`.
- Open: the event_log OI-270 anchor (append-only ledger, left alone); pma-qc cache at v1.2 until `fix/skill-mirror-merge-sync` lands.
- Corrected: isolated-commit has no changelog, so no retention rule was needed.

**How to apply / trust notes:** Thread 2 labelled the 09-22 pause "unplanned stacking"; that was wrong (it was Gabriel's own instruction). Not measured this pass, so do not carry R25's numbers as current: the realized-cost ranking, the daily spec-load aggregate, and the dark-task folder↔registry diff. Minor: pma_qc.py:523 still names vendor-contract-qc; 5 `.html.bak-rev*` artifact backups (~825KB) have no rollover.
