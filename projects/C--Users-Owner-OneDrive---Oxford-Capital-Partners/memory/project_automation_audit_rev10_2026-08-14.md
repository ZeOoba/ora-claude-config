---
name: project-automation-audit-rev10-2026-08-14
description: "Rev 10 of the ORA Automation Audit — first unattended scheduled run; 3 new findings (stale skill mirror, eval-harness dirties ora-skills daily, 3 zero-plugin marketplaces), 3 closures, 3 corrected numbers. Nothing executed."
metadata: 
  node_type: memory
  type: project
  originSessionId: 45d2365e-19e9-49c5-b25f-261bcb840fcf
  modified: 2026-08-14T23:28:47.346Z
---

Revision 10 of the **ORA Automation Audit** artifact — https://claude.ai/code/artifact/8b29049b-d7a0-4394-a602-d51e52fd21e7 — published 2026-08-14 by the monthly `ora-claude-setup-audit` scheduled task (CC fleet, `0 10 1 * *`). **First unattended run** of `ora-setup-audit`; the two prior invocations (Rev 8, Rev 9) were Gabriel-invoked the same day. Full findings live in the artifact — this file records only what a future session needs before trusting it.

**Three things to know before reading Rev 10 at face value:**

1. **The run loaded a stale copy of its own skill.** Three copies of `ora-setup-audit/SKILL.md` exist: canonical repo `~/ora-skills/ora-setup-audit/SKILL.md` (v1.3, md5 `676b56aa`, 08-14 08:34), local mirror `~/.claude/skills/ora-setup-audit/SKILL.md` (v1.2, md5 `7c4ee88b`, 08-13 20:48), and the store/Cowork copy (`anthropic-skills:ora-setup-audit`, v1.3). **The harness handed the scheduled task the v1.2 mirror** — verifiable because the invoked skill text's Changelog terminates at v1.2 and contains no Step 4a. Step 4a (the 4-entry rev-band cap + `~/.claude/artifacts/ora-automation-audit.html` durable-source workflow) exists only in v1.3. Applied it anyway, canonical-beats-mirror. `ora-skill-store-drift-check` is the intended detector but last fired 2026-08-10, before the divergence existed. See [[reference_skill_description_registry_file_desync]] — same two-stores class, different pair.
2. **Rev 10 measured only what it says it measured.** Live this pass: plugins/marketplaces/cache (disk), connectors, both fleet registries via `fleet-status.py`, ora-skills git + word counts, the four token-bloat gates. **Carried forward unverified:** Rev 9's 49-zero-count-skill breakdown and top-25 usage ranking (hours old), Rev 7's memory-orphan count. Hook suites were not re-run.
3. **The durable source is now the working copy, not the published artifact.** `~/.claude/artifacts/ora-automation-audit.html` (+ `ora-automation-audit-history.md` for rolled-off rev-bands) — edit that and republish with `url:`, don't WebFetch the published page to continue it.

**Open, pending Gabriel's call** (nothing was executed — unattended run, so "explicitly asked to fix it now" can never be true):
- **R10-1 `fix`** — re-sync the local `~/.claude/skills/ora-setup-audit` mirror to v1.3, or decide the mirror shouldn't exist.
- **R10-2 `fix`** — `ora-acquisition-underwriting-eval-harness` (CC, `14 12 * * *`, registered 08-14) writes a run JSON + `summary.csv` row into the **git-tracked** `acquisition-underwriting-eval-harness/runs/` on every daily fire. `ora-skills` is a declared single-writer checkout, so this produces a daily false positive against the "uncommitted work that isn't yours → STOP" protocol, plus ~365 committed JSONs/yr. Fix: gitignore `runs/`, or redirect to `maintenance/_state/`. One day old — cheap now.
- **R10-3 `ask`** — 3 marketplaces registered with zero installed plugins (`anthropic-agent-skills` 15MB, `karpathy-skills` 1MB, `obsidian-skills` 1MB). `karpathy-skills` was removed from `enabledPlugins`/`extraKnownMarketplaces` per `event_log.md` but **remains in `known_marketplaces.json` with a live installLocation** — the exact failure mode behind the 1.8GB re-clone. Fix is `claude plugin marketplace remove`, not archival.
- **R10-4 `ask`** — no efficacy check registered for the `ora-psa-drift-watch` retime (first-ever fire Wed 2026-08-19), unlike `ora-pm-ledger-retime-efficacy-check`.
- **R10-11 `ask`** — MEMORY.md was 21,264 B vs the 21.5KB WARN gate (~752 B headroom) **at read**; writing this file's own required index pointer took it to **21,811 B and tripped the WARN**. HARD ceiling is 24,400 B so there is runway, but the audit's mandated one-pointer-per-revision output is now itself the growth driver — same self-referential shape as Rev 8's rev-band finding. Levers: archival-with-ref-repair or splitting the index, never deleting live pointers ([[reference_memory_index_size_gate_is_a_runway_marker]]).
- **R10-12 `ask`** — `capex-budgeting` unpublish contradiction, carried unresolved from Rev 9.
- **Flagged, uninvestigated:** `anthropic-skills:insurance-renewal-review` (v1.0, 08-13) is live in the catalog but exists in **neither** `~/ora-skills` nor `~/.claude/skills` — store-only, no repo copy to rebuild from.

**Closed with evidence this pass:** the `chrome-devtools-plugins` 1.8GB re-clone (gone from `known_marketplaces.json` and disk; total plugin footprint now **29MB**) · `lease-renewal-pipeline` silent third comms path (v1.1 08-14 routes to `document-assembly`, cites Rev 8) · the `blocklist.json`/`enabledPlugins` `code-review` contradiction · Rev 9's "orphaned `ora-operations-extensions:` registration" — resolved as **stale telemetry**, `lastUsedAt` 2026-06-22, same class as the split-count finding (`claude-code-setup:claude-automation-recommender` is a second instance). **Never read `skillUsage` keys as a live plugin roster.**

**Numbers corrected downward against fresh reads:** CLAUDE.md 1,781 → **1,706 words** (back inside the do-not-trim 1694–1755 band — [[reference_claude_md_word_budget_is_a_floor]]; the flagged KPI was wrong) · System Schematic 147KB → **124.9KB** (the 08-14 per-entry-length fix worked) · fleet 55 → **60 tasks** (cc 32 / lams 28, all enabled), **0 collisions, 0 missed cycles, 0 expired one-time fires**, throttle skips 18/24h vs 178/24h on 08-09. `ora-psa-drift-watch` reads NEVER-RUN but `createdAt` is 2026-08-13 — after the last Wednesday elapsed, so Rev 7's collision cost no run.

Related: [[project_automation_audit_rev9_2026-08-14]] · [[project_automation_audit_rev8_2026-08-14]] · [[reference_plugin_cleanup_scope_cache_vs_marketplaces]]

---

## Outcomes — remediation executed 2026-08-14 (same day, Gabriel-approved plan)

Plan: `~/.claude/docs/superpowers/plans/2026-08-14-rev10-remediation.md`. Executed via subagent fan-out (ALPHA/BRAVO/CHARLIE/ECHO/DELTA, Sonnet, Fable integrator). Three concurrent sessions were working the same repo the same afternoon; two findings were fixed convergently by them, not by this plan — attribution below is honest, not claimed.

- **R10-1 FIXED** — mirror synced to repo v1.3, md5 `676b56aa` both sides; commit `16ef868` (NOTE: sits on `feat/model-canary-probe-step25`, the ~/.claude checkout's current branch — branch-switching a 20+-dirty-file shared tree is forbidden, so it rides there; working-tree content is what the harness loads, live-confirmed by the session skill listing serving v1.3).
- **R10-2 FIXED (upstream, convergently)** — origin commit `dbabb7d` "gitignore runs/ output (Rev 10 R10-2)" + PR #40 chain landed the same fix bigger (runs/ fully untracked, goldens in `golden_set/`) while this plan's ALPHA built the same thing; ALPHA's redundant commit was dropped, not merged. Local checkout reconciliation belongs to the token-splits session (3 unpushed commits at 18:45 ET). Live-fire verify: 08-20 efficacy task, assert 3 (with a WARN branch for unreconciled local checkout).
- **R10-3 FIXED** — `obsidian-skills` + `anthropic-agent-skills` removed via `claude plugin marketplace remove` (BRAVO); `karpathy-skills` was ALREADY gone at BRAVO's start though present in an 18:37 grep — a concurrent actor removed it in the gap. End-state verified: known_marketplaces.json = 2 entries, marketplaces/ = 2 dirs, extraKnownMarketplaces = 1 pin (claude-plugins-official only), plugin list unchanged. Task 7 (guard-token settings edit) cancelled — nothing to edit.
- **R10-4 FIXED** — `ora-rev10-remediation-efficacy-check` registered one-time 2026-08-20T14:30 ET, CC fleet, report-only, 4 asserts (psa-drift-watch first fire · marketplace re-clone watch · runs/ hygiene · mirror md5 parity). Registry-verified; [MODEL:] exempt (one-time CC).
- **R10-11 FIXED** — MEMORY.md compacted by DELTA this pass (before/after bytes recorded in DELTA's report; method: prose compression only, zero links dropped, probe no-worse).
- **R10-12 STILL OPEN, GABRIEL-ONLY** — capex-budgeting store contradiction; also independently flagged by the Rev 9 remediation session the same day.
- **Insurance-renewal-review BACKFILLED** — commit `726bd69` on origin/main; source: LAMS skills-plugin cache copy (byte-verified); the Cowork export in the 2026-08-14_rev10-skill-packages handoff folder matches; the double-frontmatter quirk is faithful to the installed source, preserved verbatim.
- **Rev 9 size recs NO_CHANGE_NEEDED (for this plan)** — executed concurrently by the "Skills evaluation and optimization" session (commits `899b10b`/`cc7c60a`/`6119993`/`de0ac95`, later reconciled to main) — plan Task 3 descoped on discovery, nothing duplicated.
- **Packaging (Task 8b)** — 4 .skill packages (register-scheduled-task, daily-brief, package-and-stage-skill, lease-addendum) staged to the handoff folder for Gabriel's Save-skill clicks (ECHO's report has paths/hashes).
- **Foreign-branch flag** — `chore/eval-harness-gitignore-runs-2026-08-14` (ALPHA's conflict warning) turned out to be the already-merged `dbabb7d` branch; no regression risk remains.
