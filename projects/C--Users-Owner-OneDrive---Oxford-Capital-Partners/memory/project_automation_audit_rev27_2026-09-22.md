---
name: project-automation-audit-rev27-2026-09-22
description: ORA Setup Audit Revision 27 (2026-09-22) — 18-section architecture pass, investigation only; no comps/listings store, ~48% of fleet is self-maintenance, 4 never-fired tasks; remediation plan pending Gabriel
metadata:
  type: project
---

Revision 27 of the "ORA Automation Audit" artifact (https://claude.ai/artifact/JBgJjqcCckM3pUeEp2vtQE, Version 28), run on Gabriel's pasted 18-section "full system audit" brief. Five read-only threads, all completed. **Nothing executed.** Chains [[project-automation-audit-rev26-2026-09-22]].

Before trusting the artifact's claims:
- **Subagent sizes can predate same-day fixes.** Thread 1 reported MEMORY.md at 22,411B. R26-3 had already cut it to 19,807B earlier that day; the parent session re-measured it. Re-measure gate numbers in the parent before publishing.
- **Findings R27-1 through R27-9** are in the artifact band. The top strategic item is R27-1: the `oxford-command-center` warehouse has no comps, listings, owners or brokers tables. The top operational item is R27-2: 4 tasks have never fired (county-sales-monitor, passed-deal-tracker, exit-cap-spotcheck, gis-endpoint-liveping).
- **R27-4 is unverified.** The roster says daily and live says Friday-only for ora-memory-commit-sweep and ora-pm-ledger. Check before the 09-28 resume.
- The remediation plan is a separate deliverable. Execution is pending Gabriel's approval, phase by phase.
