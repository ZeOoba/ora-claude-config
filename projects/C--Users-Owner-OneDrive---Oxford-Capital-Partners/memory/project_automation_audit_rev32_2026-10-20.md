---
name: project-automation-audit-rev32-2026-10-20
description: R32 (2026-10-20) ora-setup-audit full pass, investigation only; fleet 26/95 enabled (six recurring added since R31), backup push healthy again, Fable retired from dispatch but still used, Acquirepad/Zeno/setup-audit plugin are asks
metadata:
  type: project
---

Published as Revision 32 of the ORA Automation Audit artifact (same URL https://claude.ai/artifact/JBgJjqcCckM3pUeEp2vtQE, version 40). Chains [[project-automation-audit-rev31-2026-10-13]]. Triggered by a Gabriel question about the Claude directory, then "run the full audit" when a Yardi Matrix login failed. Nothing was executed except the append-only MCP ledger (scan + dc), the artifact, its history file and this memory file. R32 rolled Revision 27 and its folded-in Fleet Operations callout into `~/.claude/artifacts/ora-automation-audit-history.md` (byte-checked); snapshot and splice script in `~/.claude/artifacts/archive/2026-10-20_pre-r32/`.

**Verdict:** nothing delete-grade. Lint 84 skills / 0 findings, mirror exit 0. CLAUDE.md 1,849/1,850 words, MEMORY.md 20,870B before this entry.

**Before trusting the artifact:**
- Fleet is 26 of 95 enabled (CC 25 = 22 recurring + 3 one-time, LAMS 1). Six recurring added since R31's "keep the lean 19" decision: `ora-cowork-settings-quarterly-review`, `ora-doc-index-rebuild-monthly`, `ora-full-gate-weekly`, `ora-quarterly-estimate-check`, `ora-rep-hours-monthly`, `ora-site-seo-crawl-weekly`, plus one-time `ora-ltv-register-resume-2026-10-23`. Who enabled them was not traced.
- R31-4 (backup push) is CLOSED: `backup-push-ok.json` 10-20 11:28. `fleet-heartbeat.json` content is still ts 09-25 / cc 3.
- `ora-full-gate-weekly` fails (`failingStages ["test"]`, never clean); cause unread.
- Fable was retired from dispatch 2026-10-05 (spec 7.1 line 202) yet 6 Fable runs on 10-13 (property-financials branch); dispatch must pin a model.
- Thread 3's "three skill mirrors drift" is WITHDRAWN: CRLF-only (repo side CRLF, local LF; normalized equal).
- Skip counter reads 6 all-time vs R31's 56; unreconciled, no trend. `security-auditor` Fable runs read 1 (report) vs 17 (parse): unverified.
- Not done: hooks/permissions re-audit, router-hook cost, GH Actions and Task Scheduler checks, Cowork-surface evidence beyond list calls and DC counters, tracker size, wake catch-up kill cause. Yardi Matrix trial did not run (connection never completed).

**Pending Gabriel's call:** (1) were the six added tasks ratified, and what is the steady state now; (2) Acquirepad (connected, zero references anywhere, dropped out of the session mid-audit), Zeno QuickBooks Desktop plugin (zero references) and the account "Audit Claude Code configuration" plugin (overlaps `ora-setup-audit`): keep, wire in or disable; (3) health-guard chain stays dark by R31 choice, but session-context still describes it live; (4) retention rule for `artifacts/archive/` (1.3MB) and a rollover for the 355KB history file; (5) the three ratified LAMS retirements and the `deal-folder-intake` Cowork check still need a native Cowork session.

**Plugin tie-break decision (Gabriel, 2026-10-20 "proceed with recommendation"):** `ora-setup-audit` stays the sole route; the account plugin `setup-audit:setup-audit` is a quarterly read-only docs-diff complement (`focus=security,cost`, `mode=audit`; its `decisions.yaml` suppression file is created by the first run). Not scheduled, to respect the lean fleet; register via `register-scheduled-task` only if Gabriel asks. The one-line CLAUDE.md tie-break is LIVE as of 2026-10-20, applied in place on Gabriel's in-turn confirmation (allow-config-write token minted, then archived to `hooks/sessions/<session>/overrides-used/`); word count unchanged at 1,849 by dropping the "Spec §7 points here" sentence, relocated to `reference_engineering_os_done_bar.md`. UNCOMMITTED in the shared checkout. The drafting worktree `C:\Users\Owner\ora-claude-config-worktrees\claude-md-setup-audit-tiebreak` (branch `fix/claude-md-setup-audit-tiebreak`, byte-identical to live, never committed) is now redundant and can be removed.

**Why:** the audit continues one artifact as numbered revisions so closed findings are not re-litigated. **How to apply:** read the R32 band and this file's corrections before quoting any R31 number.
