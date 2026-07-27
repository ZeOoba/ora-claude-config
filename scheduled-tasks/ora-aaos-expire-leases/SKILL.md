---
name: ora-aaos-expire-leases
description: AAOS lease-expiry sweep (CC/MCP fleet, filesystem/git tool) — reclaims stale locks past expiry+5min grace in the ora-ops seam queue; silent on a clean run, emails ggoldberg only on failure or DeadAgent escalation. v1.1 2026-07-16: cadence halved 6×→3×/day (07:12 / 13:12 / 19:12 ET) per Fleet Ledger v2 ruling C2. v1.0 2026-07-10. Retimed 07:12/13:12/19:12 -> 07:20/13:20/19:20 ET on 2026-07-27 (thin-the-AM-window pass): a minor +8min uniform offset, ruling C2's 3x/day cadence intent unchanged, adding clearance from ora-task-integrity-guard's fixed 07:05 slot and the same-day ora-lease-snapshot-refresh retime to 07:40. [MODEL: UNVERIFIABLE | checked 2026-07-12]
---

Run the AAOS lease-expiry sweep:

    python "C:\Users\Owner\AAOS\tools\expire-leases.py" --project ora-ops

This sweeps `Claude_Workspace - Oxford Capital Partners\Claude_Workspace\AAOS\projects\ora-ops\locks\` (the seam root defaults to `Claude_Workspace\AAOS\` — do NOT pass `--seam-root` unless Gabriel has told you the seam moved) for stale leases — past their `expires` timestamp plus the 5-minute clock-skew grace, per ADR-0003 — and reclaims them.

Guard conditions — read the tool's exit code before doing anything else:
- Exit 0: normal. This includes "no locks directory; nothing to sweep" (empty queue) and ordinary ExpiredLapsed reclaims. Do NOT email, do NOT post anywhere. A clean run is silent.
- Exit 2 (USAGE ERROR — seam unreachable/OneDrive sync issue) or exit 5 (EVENT COMMIT FAILURE): retry the exact same command once. If it fails again, send exactly one email via `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` to ggoldberg@oxfordra.net ONLY — subject "AAOS expire-leases FAILED", body = the tool's stderr verbatim (quote it exactly, do not paraphrase or summarize away detail).
- Exit 1 (VALIDATION FAILED) or stdout containing "ESCALATED:" with classification DeadAgent: send exactly one email to ggoldberg@oxfordra.net — subject "AAOS expire-leases: escalation", body = the relevant stdout lines verbatim. This is routine-but-noteworthy, not necessarily a crisis — do not use alarm language beyond the facts.
- Never hand-edit any file under `Claude_Workspace\AAOS\`. Never fabricate or embellish what the tool reported — quote its actual output.
- Do nothing else: no scheduled-task registry changes, no git operations, no other files touched. This task's entire job is one command and, conditionally, one email.

Background if you need it: `C:\Users\Owner\AAOS\docs\OPERATIONS.md` §2 (manual lock-break procedure this automates) and §5 scenario 1.