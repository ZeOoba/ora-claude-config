---
name: project-audit-rev9-remediation-landed-2026-08-14
description: "Rev 9 skill-audit remediation plan executed via subagent-driven-development and landed to ora-skills main (33713aa) — register-scheduled-task/daily-brief token splits, 2 investigations closed (1 false alarm, 1 still needs Gabriel's answer)"
metadata:
  node_type: memory
  type: project
  originSessionId: f6b9d0b7-2ead-4c85-83b4-4e6ae0c83271
  modified: 2026-08-14T22:57:07.031Z
---

Executed the plan at `~/.claude/docs/superpowers/plans/2026-08-14-audit-rev9-skill-remediation.md` (8 tasks) via `superpowers:subagent-driven-development`, fresh subagent per task + task review + final whole-branch review. All landed to `ora-skills` main at `33713aa`.

**Landed (ora-skills main):**
- `register-scheduled-task/SKILL.md`: 2,885w → 1,684w (Changelog → `versions/CHANGELOG-v2.0-v2.8.md`; incident narratives → `references/incident-history.md`). Every operative rule preserved inline.
- `daily-brief/SKILL.md`: 4,681w → ~3,958w (Changelog → `versions/CHANGELOG-v2.0-v2.9.md` only — its 9 sections all execute every run, so nothing else was reference-only; the "WHY THE 1-MATCH BRANCH CHANGED" anti-regression callout was deliberately left inline, not moved).
- `tools/package_skills.py`'s `is_bundled()` docstring corrected (was stale, said only `cowork-settings` uses top-level `versions/`; now several skills do).
- **Neither skill has been re-verified as actually reimported to the live Cowork platform yet** — `pending_reimport.py candidates` doesn't flag them (pre-commit auto-mirror-sync makes that check a false negative for already-installed skills, per `package-and-stage-skill` v1.13 doctrine), and `main.log` shows no Sync-complete cycle for either post-split commit. **Next step: run `package-and-stage-skill` on both before trusting the token savings are live**, same as was needed for `lease-addendum` this session.

**Final whole-branch review (Opus) caught one real defect the two per-task reviewers missed:** the plan's own Task 3 replacement text had silently dropped an operative clause (LAMS OneDrive `"(1)"`-suffix verification instruction) — both task reviewers only checked implementation-vs-plan-text, so a defect in the plan text itself passed both. Fixed in a same-session follow-up commit (`33713aa`) along with 4 Minor consistency items (dangling directional references, a versions-file header gap). Two convention-design recommendations (retention-policy count, verbatim-assertion header convention) were left as recommendations, not actioned — would need a written repo-convention decision before a 4th skill gets this treatment.

**Task 6 investigation — capex-budgeting unpublish contradiction: STILL OPEN, needs Gabriel's direct answer.** New evidence found (neither Rev 9 nor the concurrently-running Rev 10 of the Automation Audit had surfaced this): `event_log.md` lines 792-798 show a 2026-08-13 batch Save-skill click (clearing a PENDING_REIMPORT queue from an unrelated tombstone fix) caused `capex-budgeting` to re-register in the Cowork store as a **new registration** (enabled count 51→52) — 4 days after Gabriel confirmed on 2026-08-09 it was unpublished alongside 5 siblings. Plausible accidental-reimport explanation, not proof of intent. **Question for Gabriel** (full text in `~/ora-skills/.superpowers/sdd/task-6-report.md`): was bringing it back on 2026-08-13 intentional, or should it be unpublished again — and are the other 5 skills from the 2026-08-09 list still correctly unpublished (none were in the 2026-08-12/13 reimport batch, so no similar drift risk, but never independently re-verified against the store either).

**Task 7 investigation — orphaned `ora-operations-extensions:submarket-spatial-analysis` plugin registration: CLOSED, false alarm.** Rev 9 flagged this as possibly orphaned. Real root cause: stale `.claude.json` telemetry (single use, 2026-06-22) from a plugin bundle Gabriel explicitly retired 2026-08-05 (commit `2f4f831`) — the skill itself is not orphaned, it's live today as `anthropic-skills:submarket-spatial-analysis` v1.4. Nothing to fix; note for the next audit revision to cross-reference `_archive/plugins/ora-operations-extensions/README.md` before re-flagging.

**Task 8 — lease-addendum packaging: already done by a concurrent session** (Save-skill click confirmed 2026-08-14 17:51:42 ET for commit `f96aa85`, per `event_log.md`). One new minor finding: the installed copy is 1 commit behind repo HEAD (`2bc0727` landed ~11min after the install click) — flagged for a future drift-check pass, not actioned.

**Concurrency note:** a different session was actively committing to `ora-skills` (`lease-addendum/`, `README.md`, `acquisition-underwriting-eval-harness/`) throughout this entire plan's execution — Task 5's fast-forward correctly failed once main diverged, was resolved via a path-disjoint rebase of this session's own isolated branch (never touched the other session's history), and this held cleanly through the final-review fix wave too.

**How to apply:** Before trusting register-scheduled-task/daily-brief's token savings as live on Cowork, run `package-and-stage-skill` on both first. The capex-budgeting question is the one item that actually needs Gabriel's attention from this session — everything else either landed clean or closed as a non-issue. Full per-task reports: `~/ora-skills/.superpowers/sdd/task-{1..8}-report.md` and `task-final-fixes-report.md`. Progress ledger: `~/ora-skills/.superpowers/sdd/progress.md`.
