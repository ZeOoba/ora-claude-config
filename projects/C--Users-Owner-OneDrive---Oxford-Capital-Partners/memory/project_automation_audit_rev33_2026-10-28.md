---
name: project-automation-audit-rev33-2026-10-28
description: R33 (2026-10-28) ora-setup-audit full pass, investigation only; fleet 25/94, full-gate recovered, ora-prepush-gate-sweep failing, mirror check now exit 1 (stale ora-skills checkout), land vs merge-ready collision, 109 worktrees
metadata:
  type: project
---

Published as Revision 33 of the ORA Automation Audit artifact (same URL https://claude.ai/artifact/JBgJjqcCckM3pUeEp2vtQE, version 41). Chains [[project-automation-audit-rev32-2026-10-20]]. Gabriel invoked `/ora-setup-audit`. Nothing was executed except the append-only MCP ledger (scan 0 records, dc snapshot), the artifact, its history file (Revision 29 band appended, byte-checked), a snapshot in `~/.claude/artifacts/archive/2026-10-28_pre-r33/` and this file.

**Verdict:** nothing delete-grade. CLAUDE.md 1,849/1,850 words, MEMORY.md 20,855B before this entry (645B under WARN).

**Before trusting the artifact:**
- The mirror drift (`adversarial-merge-gate`, `county-parcel-screen`, exit 1) is probably a stale checkout: `~/ora-skills` is 20 behind origin/main, files not diffed. Every local skill size figure in R33 predates 17 commits (origin has 88 skills; `acquisition-underwriting` 13,488w there vs 10,934w local).
- Which task left the registry since R32 was not identified; the baseline, roster and session-context fleet block are all 10-08 and say 14 recurring (live 22).
- `ora-prepush-gate-sweep` failure (5 tests, 2 consecutive) was read from `_state`, tests not run; next run Thu 10-29.
- Fable counts use file mtime; the four 10-13 hard-tier calls are inferred from branch names.
- R33 band is 12,091 chars, about 90 over the soft cap.

**Pending Gabriel's call:** keep-lean-fleet intent vs the 8 recurring tasks outside the baseline; health chain still OFF since 09-14; `ora-pm-monthly-billing` first slot Sun 11-01 11:10 (app must be open); pull ora-skills (dirty `target-markets.json`, single-writer); `land` vs `merge-ready` tie-break; Context7 connected twice; schematic task OFF (44 days stale); 109 worktrees prune; archive retention (keep last two); heartbeat log rotation (~40 days to 1 MiB).

**Why:** the audit series keeps finding self-monitoring state drifting from live state (session-context, roster, baseline). **How to apply:** re-measure fleet and mirror state live before repeating R33 numbers.
