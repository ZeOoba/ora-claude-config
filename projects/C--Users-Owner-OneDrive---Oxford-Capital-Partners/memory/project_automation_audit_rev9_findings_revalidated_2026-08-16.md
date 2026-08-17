---
name: project-automation-audit-rev9-findings-revalidated-2026-08-16
description: "Re-verification of Revision 9's skill-size/data-quality findings against live ground truth on 2026-08-16, plus a live multi-session collision found on the Automation Audit artifact mid-check"
metadata: 
  node_type: memory
  type: project
  originSessionId: 81ed9931-4db5-4adf-be23-cbe47979ac6b
  modified: 2026-08-17T01:50:05.845Z
---

Gabriel handed a "Investigate the below" table reproducing **Revision 9's** (2026-08-14) skill-size and data-quality findings verbatim, for validation. Direct re-check against live ground truth (git log, `wc -w`, `.claude.json#skillUsage`, `settings.json`) found:

1. **register-scheduled-task split — ALREADY EXECUTED, closed.** Commit `6119993` ("move incident-narrative asides to `references/incident-history.md`") landed same-day as Rev9's measurement. Current `SKILL.md` is 2,028w (was 2,885w); `references/incident-history.md` (675w) already holds the cross-fleet-registry background + 2026-06-09 incident narrative the table proposed extracting. No action needed.
2. **daily-brief — still open, number stale.** No `references/` split exists. Actual current size 4,113w, not 4,681w (an 08-15 remediation commit `f35a77c` trimmed it since Rev9). Still top split priority (7x/week unattended `ora-am-brief` cost).
3. **package-and-stage-skill — still open, priority was backwards.** No split exists; file has GROWN to 6,838w (not 4,806w) via 4 commits dated 2026-08-15–08-16 (`7e19319`, `06f1355`, `e9180a0`, `0661c8a`), landing at v1.19. (Corrected 2026-08-16: an earlier pass over-claimed "5 commits, v1.15→v1.19" — the 5th candidate commit, `899b10b`, is same-day as Rev9 with no finer timestamp, so its starting version can't be confirmed against Rev9's snapshot; not asserted.) Now the largest of the three by a wide margin and fastest-growing — should be elevated priority, not deferred as "not urgent."
4. **systematic-debugging + debug — unchanged, genuinely still open.** Live merged counts today: 74 (was 72), 68 (was 66) — proportional growth. No evidence the recommended plugin-cache re-read for instruction overlap has ever been done. Carry forward as "confirm, don't fix" ask.
5. **4 unprotected skills** (evidence-dossier-drafting, file-reconciliation, conversation-archival, explain-usage) — no new evidence either way, unchanged since Rev9, still Gabriel's call.
6. **capex-budgeting + ora-operations-extensions — ALREADY CLOSED as false findings in Revision 12** (2026-08-16, hours before this check). capex-budgeting was never republished (Rev5's record was right; the contradiction came from misreading an `ora-skills` commit date as store state). The "orphaned" `ora-operations-extensions:` registration is a category error — `@inline` cloud-store plugins never appear in `enabledPlugins`, so absence there was never evidence of anything. The pasted table reproduces Rev9's original framing without reflecting Rev12's resolution.

**⛔ CRITICAL — live multi-session collision found mid-check, publish deliberately withheld.** While investigating, `~/.claude/artifacts/ora-automation-audit.html`'s masthead changed mid-session to claim "Revision 14 · independent re-verification pass ... both Revision 11 findings reconfirmed" — but no Revision 14 rev-band div exists in the body. Instead the body shows an in-progress "R13-VERIFICATION, same day" block being appended live inside Revision 13's own div, itself answering a **different** "Investigate the below" table (R13-1 through R13-6: FRED MCP connector, skill-mirror drift, MEMORY.md ceiling, CLAUDE.md word count, collision retimes) — no overlap with the findings above. This means Gabriel dispatched at least two concurrent "Investigate the below" sessions against two different stale tables pulled from the same artifact, both racing to publish to the same URL. This is NOT one of the 3 concurrent claims disclosed at this session's start.

**Why:** artifact continuation (`Artifact url:` update) is inherently single-writer; two sessions mid-write on the same durable HTML risk clobbering each other's just-landed rev-bands.
**How to apply:** before touching `ora-automation-audit.html` or the published artifact again, re-read fresh and check the masthead Revision number + inline rev-band count against what's recorded here. If it has moved further, treat the six verdicts above as validated input for whichever session lands next to fold in — do not re-derive them, and do not force-publish over an artifact whose masthead and body disagree on current revision.
