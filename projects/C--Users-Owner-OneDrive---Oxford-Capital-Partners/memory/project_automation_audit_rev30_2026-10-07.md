---
name: project-automation-audit-rev30-2026-10-07
description: R30 (2026-10-07) ora-setup-audit pass asked "what can be deleted or is redundant with newer Claude"; investigation plus published 34-action remediation plan; nothing executed; fleet 16/88 enabled, 7 enabled tasks never fired
metadata:
  type: project
---

Published as Revision 30 of the ORA Automation Audit artifact (same URL, version 33) plus a separate plan artifact "ORA Setup Remediation Plan" (https://claude.ai/artifact/PfqhuzESbNWoU48AfvRg7X). Chains [[project-automation-audit-rev29-2026-10-02]]. Gabriel's "implement the revision" was read as publishing this audit revision; the plan's actions were NOT executed.

**Verdict:** no plugin, connector or ORA domain skill is clearly dead. Cleanup candidates are small (orphan plugin cache 109K, duplicate `visualize` server `6f616b42`, three redundant or misfiring hooks, stale memory and repo-doc history). The fleet finding was CORRECTED 2026-10-08: 16 of 86 enabled, and the seven enabled CC tasks that read "never run" are NOT late. The 10-06 model re-pin deleted and recreated them (event_log 2026-10-06), wiping `lastRunAt`; their first slots are still ahead (ora-memory-commit-sweep Fri 10-09 19:00 is first). `fleet-status.py` shows "registered 53d ago" from the first membership-log add, not registry `createdAt` (plan P5-9 fixes the label). Cowork fleet silent 334.5h is expected (off).

**Before trusting the artifact:**
- The 16/88 count and the "six skills listed twice are local duplicates" reading came from single subagent threads and were not independently verified; the second is probably account-store entries (Step 0b detail-page check needed). Re-run `fleet-status.py` before answering decision D1.
- The MCP usage ledger is stale (newest record 09-30), so every MCP verdict is keep/HOLD, none delete.
- The CLAUDE.md relocation candidates must NOT include the eight guard names: the doctrine probe's Check 11 requires them inline.

**D1 SETTLED 2026-10-08, Gabriel: "fleet off" = Cowork (LAMS) fleet only**, already true (1 enabled one-time 2027 task). The 15 enabled CC tasks stay as they are (ora-am-brief must stay enabled). No registry write made. Plan P5-1 is a no-op; P5-2 (trace of the 7 "never run" CC tasks) is DONE, they were recreated 10-06; P5-3 (re-baseline membership, which lists only 1 CC task) stays live and needs Gabriel's go.

**Remediation tranche 1 (2026-10-08):** done = orphan plugin cache + 5 empty data stubs archived, memory index fixes, session-context ora-passed-deal-tracker line corrected, two expired CC one-time tasks retired (registry row then folder archive). Dropped after verification: P2-1 (memory-nag-correction corrects the harness's stale 17.1KB nag), P2-2 (Edit deny rules are cwd-relative), P2-4 (trailing-space deny pattern is deliberate). Held for Gabriel: settings.json and CLAUDE.md edits (guarded), three LAMS retirements (native Cowork session only), P5-3, P5-9. In flight: ora-skills worktree `~/ora-skills-wt-r30` on branch `chore/r30-backup-two-skills` (adds adversarial-merge-gate + branch-catchup, ora-setup-audit v1.18), awaiting independent review before commit.

**Cowork-side report received 2026-10-08 (read-only):** D3 settled (one store entry per skill; only the county-sales-monitor and ora-setup-audit store descriptions are stale), D5 settled (5 Cowork-only skills exist; adversarial-merge-gate, branch-catchup, evidence-dossier-drafting absent from Cowork), D4 narrowed (context7, terminal, mcp-registry, second visualize are Code-only; Claude Docs id 1a59c906 logged 30 calls since 08-28). Cowork logs reach back to 08-28 (about 6 weeks), not 2.

**Tranche 2 (2026-10-08, Gabriel answered all open items):** D2 resolved (ora-passed-deal-tracker ENABLED, tag UNVERIFIABLE|checked 2026-10-08). ora-skills #110 MERGED. Membership re-baselined (2 clean probe runs). event_log rolled over 323KB to 101KB. outreach-ratification.json exists in `Business/Investment Candidates -- 2026/Claude outputs/` (probe roots were the gap, not a lost file). Open PRs awaiting Gabriel: ora-claude-config #310 (fleet-status createdAt label) and #311 (noi-opportunity-scout trim); ora-skills #111 DRAFT (nine description trims, dropped triggers listed); oxford-command-center #452 (CLAUDE.md history collapsed, review approved, needs architect ack). Held: guarded settings.json/CLAUDE.md diffs (published on the plan page; realistic CLAUDE.md saving is ~35 words, not 250), 3 LAMS retirements (native Cowork session prompt issued), tracker rollover (would break #OI-NNN anchors). Watch: ora-cc-snapshot-refresh skipped Mon 10-05, next 10-12. Lesson: guards accept the repo's worktree path convention (`.claude/worktrees/<name>`), not arbitrary worktree folders.

**Pending Gabriel:** merge/review decisions on the five PRs above, the guarded-diff approvals, and the three LAMS retirements via a native Cowork session, the Census key rotation carried from R29-9, and the Revision 29 band (12,426 chars) and stale "description payload" section still to archive.

**Why:** Gabriel asked for a thorough evaluation of what is wasting space or superseded by newer Claude.
**How to apply:** start any follow-up from the plan's decision list, and use the register-scheduled-task path for every registry change.
