---
name: reference-rev10-efficacy-2026-08-20
description: One-time efficacy check of the Automation Audit Rev 10 remediation (2026-08-14) — 3 PASS, 1 FAIL (psa-drift-watch never fired, confounded by the 08-17 bounded fleet pause)
metadata:
  type: reference
---

# Rev 10 Remediation — Efficacy Check (run 2026-08-21 ~17:15 ET)

Scheduled task `ora-rev10-remediation-efficacy-check`, report-only. Plan: `~/.claude/docs/superpowers/plans/2026-08-14-rev10-remediation.md`. Artifact: https://claude.ai/code/artifact/8b29049b-d7a0-4394-a602-d51e52fd21e7. No fixes, no emails, no writes beyond this file + the MEMORY.md pointer. Findings route to the next `ora-setup-audit` revision.

**Result: 3 PASS / 1 FAIL.**

## 1. PSA-drift-watch retime efficacy (R10-4) — ⚠️ FAIL (but see attribution)

Evidence — `list_scheduled_tasks` (CC/MCP registry, MCP tool, not the JSON), entry `ora-psa-drift-watch`, verbatim:
`"cronExpression": "45 13 * * 3"`, `"enabled": false`, **no `lastRunAt` key present at all** (and no `nextRunAt`).

Per the assert's stated rule, absent `lastRunAt` = FAIL. The retime itself landed correctly — the cron reads `45 13 * * 3`, the Rev 7 collision fix. What did not happen is the fire.

**Attribution (do not read this FAIL as "the retime silently never took"):** the task's first-ever scheduled fire would have been Wednesday **2026-08-19 13:45 ET**, which falls inside the bounded pause. Evidence — registry entry `ora-routine-pause-resume-08-21`, verbatim description: *"One-time resume — re-enables the 35 CC/MCP recurring tasks paused 2026-08-17 at Gabriel's request (\"pause all routines until Friday 5pm\")"*. A disabled task cannot fire. So the null here is **explained**, not mysterious — but it is also **unverified as fixed**: the retime has still never been exercised, and the next natural fire is Wednesday 2026-08-27 13:45 ET. Re-check then before calling R10-4 closed.

Sibling one-time `ora-psa-drift-watch-retime-efficacy-check` did fire today (`lastRunAt: 2026-08-21T21:10:51.698Z`), i.e. ~4 min before this run; its own finding is not restated here.

## 2. Marketplace re-clone watch (R10-3) — ✅ PASS

`known_marketplaces.json` holds exactly 2 entries, verbatim keys: `superpowers-marketplace` (obra/superpowers-marketplace, lastUpdated 2026-04-15T18:28:45.496Z) and `claude-plugins-official` (anthropics/claude-plugins-official, lastUpdated 2026-07-17T18:07:27.067Z).

`~/.claude/plugins/marketplaces/` directory listing, verbatim: `claude-plugins-official`, `superpowers-marketplace`. No `karpathy-skills`, no `obsidian-skills`, no `anthropic-agent-skills`. No re-clone — the 2026-08-13/14 chrome-devtools-class reversal has not recurred in the 7 days since.

## 3. Eval-harness `runs/` hygiene under live fire (R10-2) — ✅ PASS

`git -C C:/Users/Owner/ora-skills status --porcelain acquisition-underwriting-eval-harness/runs/` → **empty output, exit 0**. Clean.

Reconciliation confirmed, so this is a real PASS and not the WARN branch: `git merge-base --is-ancestor dbabb7d HEAD` → **exit 0**. `dbabb7da6114df885071b679ee8e9c6e22717525` = *"chore(acquisition-underwriting-eval-harness): gitignore runs/ output (Rev 10 R10-2)"*, 2026-08-14. Local HEAD `c31fa66d579d5578d577735cafe2b1f7dcb55668` 2026-08-21 *"docs(package-and-stage-skill): v1.22…"*. The 2026-08-14 unpushed-token-split-commits situation has since reconciled.

## 4. ora-setup-audit mirror parity (R10-1) — ✅ PASS

`md5sum` of both copies, verbatim:
- `ec81f3f63012dcd45a1ebc07bc0fbd62 *C:/Users/Owner/ora-skills/ora-setup-audit/SKILL.md`
- `ec81f3f63012dcd45a1ebc07bc0fbd62 *C:/Users/Owner/.claude/skills/ora-setup-audit/SKILL.md`

Identical. The repo-moved/mirror-stale defect that made the 2026-08-14 scheduled audit load a v1.2 skill missing its own rev-band cap has not recurred.

## Incidental observation — NOT one of the four asserts, unverified, report-only

At read time (~2026-08-21T21:15Z, ~9 min after `ora-routine-pause-resume-08-21` shows `lastRunAt: 2026-08-21T21:05:54.008Z`), the CC/MCP registry showed **only 2 recurring tasks with `enabled: true`** — `ora-master-workbook-ingest` and `ora-financial-code-integrity-sweep` — with every other recurring task still `enabled: false`. The resume was specced to re-enable 35.

This may be a genuine incomplete resume, or a stale/cached registry read taken too soon after the resume wrote. **This check did not verify which**, and took no corrective action. Flagging for the next `ora-setup-audit` revision and for whoever owns the resume chain — re-read `list_scheduled_tasks` before acting on it. Related: [[project_automation_audit_rev17_2026-08-21]], which audited the same 08-17 pause/resume scripts.

Related: [[reference_next_action_date_stamping_already_wired_2026-08-12]] on flat-count denominators, and the general rule that a null which could mean "couldn't look" is a failure, not a pass — see [[feedback_verified_null_vs_inferred_null]].
