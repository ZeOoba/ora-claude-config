---
name: model-release-checklist
description: "Where hardcoded Claude model IDs live across the CC/MCP + LAMS fleet, oxford-command-center, and memory — and the checklist to run on every new Anthropic model release"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 8e3f40ea-05cc-48c4-9e6b-49cd7ec8ee9e
  modified: 2026-09-02T10:06:09.120Z
---

Current lineup as of 2026-09-02: Fable 5.1 (`claude-fable-5-1`, hardest tier — succeeded Fable 5) · Opus 5 (`claude-opus-5`, standard high-capability) · Sonnet 5 (`claude-sonnet-5`, standard implementation) · Haiku 4.5 (`claude-haiku-4-5-20251001`, mechanical). CLAUDE.md's tier doctrine (Fable/opus/sonnet/haiku by role) is alias-based and needs NO edit on a release — confirmed zero hardcoded model IDs in CLAUDE.md or the 6 `~/.claude/agents/*.md` files (as of the 2026-07-26 check; re-verify if this file hasn't been touched since).

**PRIOR (superseded 2026-09-02):** lineup as of 2026-07-26 had Fable 5 (`claude-fable-5`) in the hardest tier. Detected via ora-model-release-watch's 2026-09-02 scheduled run reading this session's own system-prompt model-lineup statement (`claude-fable-5-1` present, not in the recorded set). Opus 5, Sonnet 5, and Haiku 4.5 IDs are unchanged.

**PRIOR (superseded 2026-07-26):** lineup as of 2026-07-10 had Opus 4.8 (`claude-opus-4-8`) in the high-capability slot. Detected via ora-task-integrity-guard's 2026-07-26 07:14 ET run reading this session's own system-prompt model-lineup statement (`claude-opus-5` present, not in the recorded set) — flagged in-turn by Gabriel same day rather than waiting for this task's next 2026-07-27 11:27 ET scheduled fire. Every `[MODEL: claude-opus-4-8 ...]` CC/MCP observation tag logged before 2026-07-26 (`ora-site-exposure-probe`, `ora-appsec-sweep`) reflects the OLD pin and needs re-observation, not automatic correction — canary method per `reference_scheduled_task_model_standard.md`.

**Where exact IDs live (full sweep 2026-07-10):**

1. `~/.claude/settings.json:2` — top-level default, governs CC/MCP interactive sessions.
2. `memory/reference_scheduled_task_model_standard.md` + MEMORY.md index line — LAMS/Cowork fleet standard, tagged `[MODEL: <id> | set <date>]` per task.
3. CC/MCP scheduled-task fleet is NOT independently pinnable — runs on a server-pinned model outside registry control (`ora-task-integrity-guard/SKILL.md:22`), tagged `[MODEL: UNVERIFIABLE]` across its 11 SKILL.md files. A canary test (`.claude/scheduled-tasks/_canary-model-check-result.txt`) caught one firing on `claude-opus-4-8` instead of the configured `claude-sonnet-5` — matches reported Claude Code issue #48976. Open upstream reliability gap, not a config fix.
4. `C:\Users\Owner\oxford-command-center\server\ai\{agent,comps,narrative}.ts`, `server\warehouse\om-extract.ts`, `server\index.ts`, `.env` (`OM_EXTRACT_MODEL`) — real hardcoded literals in live app code (opus-4-8 for narrative/comps default, haiku-4-5-20251001 for OM extraction). Shared single-writer repo — check `git status`/`git log -1` before touching. Route generation bumps through the claude-api skill's `shared/model-migration.md`, not find-replace — a Sonnet/Opus generation jump can change request shape (thinking params, prefill, effort).
   - **Fixed 2026-07-10:** `server/ai/narrative.ts`'s `DEFAULT_MODEL` const is now `export`ed; the 11 test-file literal assertions of `claude-haiku-4-5-20251001` across `tests/unit/{narrative,lease-narrative,briefing-narrative-contract,briefing-pdf-narrative}.test.ts` now import and reference `DEFAULT_MODEL` instead of duplicating the string. Typecheck clean, all 71 tests in those 4 files pass.
   - **CHANGELOG.md drift claim — corrected 2026-07-10:** re-verified directly; the canonical `CHANGELOG.md` has zero occurrences of any haiku model string (checked `haiku`, `4-5`, `4.5`, `20251001`). The previously-noted "shortened ID missing the -20251001 suffix" is not present in the current file — either already resolved before this check or the original observation was mistaken. No action taken; don't re-flag without re-verifying. (Stale worktree copies under `.claude/worktrees/*/CHANGELOG.md` are branch snapshots, not the source of truth — ignore for drift checks.)
5. `C:\Users\Owner\ora-pm` — **swept 2026-07-10, confirmed it DOES call the Anthropic API directly.** `server/lib/lease-extract.ts` posts to `https://api.anthropic.com/v1/messages`; `server/routes/intake.ts:8` sets `DEFAULT_MODEL = 'claude-opus-4-8'`, overridable via `c.env.INTAKE_MODEL` (documented in `.env.example: INTAKE_MODEL=claude-opus-4-8`). Already alias/env-overridable with no bare hardcode-without-escape-hatch — same safe posture as oxford-command-center's env-overridable defaults. No fix needed, just add to future sweeps. (Route also fail-closes if the confidentiality denylist is unconfigured, before any egress — Hard Invariant 3 pattern.)
6. `ora-skills` — clean, alias-based (`model: sonnet`/`opus` in frontmatter), zero hardcoded IDs found across every SKILL.md and script. No action ever needed here on a release.
7. `.claude/docs/superpowers/specs|plans/*` (engineering-operating-system-design.md and its plan) — doctrine/planning docs reference `claude-opus-4-8` as the dispatch default, self-flagged superseded now that Fable split out as the dedicated hardest tier. Low-priority historical docs, optional annotation only.
8. One genuinely stale ID (`claude-sonnet-4-6`) found only in `memory/_archive/user_ze_retired_2026-04-21.md` — correctly quarantined already, no action.

**Process on every new Claude model release:**
1. Confirm the new model ID via live session info or a `models.list()` call — never trust a cached skill table (the claude-api skill's table lagged Sonnet 5 by over a month).
2. Bump `~/.claude/settings.json` top-level default + `reference_scheduled_task_model_standard.md` (+ MEMORY.md index line) the same day, per existing single-writer/claim-first discipline.
3. Leave CLAUDE.md and ora-skills alone — they're alias-based by design and don't need touching.
4. Sweep `oxford-command-center` and `ora-pm` for hardcoded API-call defaults (both now baselined as of 2026-07-10 — diff against this snapshot rather than re-discovering from scratch); read the claude-api skill's `model-migration.md` before changing request parameters, since intelligence-tier jumps can carry breaking API changes.
5. Re-run the CC/MCP canary check to see if the actual-vs-configured model gap (#48976-pattern) persists.

**Why:** Gabriel asked (2026-07-10) how to understand and revise the whole setup whenever Claude releases new models. Most of the setup is already correctly alias-based (CLAUDE.md, ora-skills, agents/*.md) — only oxford-command-center's live API-call code and the two model-standard pointers (settings.json, scheduled-task-standard memory) need a look each time.
**How to apply:** Before advising a new-model rollout is "done," re-check this list. Before claiming any file has a stale model ID, re-verify current state directly — don't assume this snapshot stays accurate past the next release. See [[reference_scheduled_task_model_standard]].
