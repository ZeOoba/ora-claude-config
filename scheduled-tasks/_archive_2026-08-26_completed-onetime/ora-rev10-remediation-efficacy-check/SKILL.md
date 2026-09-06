---
name: ora-rev10-remediation-efficacy-check
description: One-time efficacy check for the 2026-08-14 Automation Audit Rev 10 remediation: verifies ora-psa-drift-watch's first fire, no marketplace re-clone, eval-harness runs/ hygiene, and ora-setup-audit mirror parity. Report-only.
---

One-time efficacy check for the Automation Audit Rev 10 remediation executed 2026-08-14 (plan: C:\Users\Owner\.claude\docs\superpowers\plans\2026-08-14-rev10-remediation.md; artifact: https://claude.ai/code/artifact/8b29049b-d7a0-4394-a602-d51e52fd21e7). This is an unattended, REPORT-ONLY run: no emails, no fixes, no registry writes, no git writes. Never fabricate — every assert below states its exact evidence source; if a source is unreadable, report UNVERIFIABLE for that assert, not a guess.

Run these four asserts and report PASS/WARN/FAIL for each:

1. PSA-DRIFT-WATCH RETIME EFFICACY (audit finding R10-4): read the CC scheduled-task registry via the list_scheduled_tasks MCP tool (never the JSON directly). Assert `ora-psa-drift-watch` shows a lastRunAt on or after 2026-08-19 (its first-ever scheduled fire after the Rev 7 collision retime; cron 45 13 * * 3). No lastRunAt = FAIL (the retime silently never took).

2. MARKETPLACE RE-CLONE WATCH (R10-3): assert `C:\Users\Owner\.claude\plugins\known_marketplaces.json` contains exactly 2 entries (superpowers-marketplace, claude-plugins-official) and `C:\Users\Owner\.claude\plugins\marketplaces\` contains no directory named karpathy-skills, obsidian-skills, or anthropic-agent-skills. Any reappearance = FAIL — this exact reversal happened within hours once before (the 1.8GB chrome-devtools re-clone, 2026-08-13/14).

3. EVAL-HARNESS RUNS/ HYGIENE UNDER LIVE FIRE (R10-2): run `git -C C:/Users/Owner/ora-skills status --porcelain acquisition-underwriting-eval-harness/runs/`. Empty output = PASS. Non-empty output: check whether `git -C C:/Users/Owner/ora-skills merge-base --is-ancestor dbabb7d HEAD` succeeds (exit 0). If dbabb7d (the runs/ gitignore commit, merged to origin/main 2026-08-14 via the PR #40 chain) is NOT yet in the local checkout's history, report WARN "local checkout not yet reconciled with origin — dirt expected, not a regression" (the local main had 3 unpushed token-split commits from another session as of 2026-08-14 18:45 ET and its reconciliation is that session's work, not yours). If dbabb7d IS an ancestor and runs/ is still dirty = FAIL.

4. ORA-SETUP-AUDIT MIRROR PARITY (R10-1): assert `md5sum C:/Users/Owner/ora-skills/ora-setup-audit/SKILL.md C:/Users/Owner/.claude/skills/ora-setup-audit/SKILL.md` returns two identical hashes. Different hashes = FAIL (the repo copy moved and the mirror went stale again — the exact defect that made the 2026-08-14 scheduled audit run load a v1.2 skill missing its own rev-band cap).

OUTPUT: write the results to a new memory file C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\reference_rev10_efficacy_2026-08-20.md (frontmatter type: reference; one line per assert with the verbatim evidence), and add one pointer line for it to MEMORY.md under the Reference section. If ANY assert is FAIL, prefix the MEMORY.md pointer line with ⚠️ and state the failing assert in the pointer text so it is loud. Do not email. Do not attempt any fix — findings route to the next ora-setup-audit revision.