---
name: claude-setup-audit
description: Formal investigation of Gabriel's Claude Code/Cowork setup — skills, plugins, MCP connectors, hooks, and the dual scheduled-task fleet — scored for accuracy, performance, and token spend, with a keep/fix/combine/delete call on each finding. Use when Gabriel asks to audit, refine, optimize, or investigate his Claude Code setup, wants to reduce token spend, asks what's redundant or safe to remove, wants to prune/declutter/clean up unused skills/plugins/connectors/routines, or references "the artifact" meaning the System Schematic or the Automation Audit. Continues the existing "ORA Automation Audit" artifact as a new revision rather than starting fresh — check for it first via Artifact action:list before assuming none exists. THE canonical skill for this class of request — see Changelog before building a parallel one. v1.1
license: ORA Internal
---

# Claude Setup Audit

Formal, evidence-grounded audit of the Claude Code/Cowork environment itself — not a codebase, the harness. Produces the same keep/fix/combine/delete verdict format the "ORA Automation Audit" artifact has used since its first revision, continued in place rather than replaced.

## Guardrails (apply to every thread below)

- **Never flag (skip outright):** anything named in `CLAUDE.md` (skill tie-breaks, Hard Invariants, routing canon) — referenced there means load-bearing regardless of frequency; anything gating a Hard Invariant, a financial governor (DSCR/LTV constants), or a compliance/legal function; anything with a documented multi-year recurrence (e.g. a credential-rotation skill) — rarity by design, not by neglect.
- **Rarity is neutral, not evidence of bloat.** No file, log, or telemetry anywhere in `~/.claude` records per-skill/plugin/connector invocation counts — confirmed 2026-08-13 by direct forensics: `~/.claude.json#skillUsage` AND `claude-markdown-health-check`'s Phase 7 JSONL signal (`~/.claude/projects/**/*.jsonl`) are BOTH structurally CC/MCP-surface-only (sampled 25 CC + 25 LAMS sessions: 14/25 CC sessions had a matching transcript file, 0/25 LAMS sessions did — LAMS/Cowork tasks execute in a separate VM/cloud sandbox whose transcripts never sync locally). Treat the two as the SAME blind spot restated, never as independent or corroborating signals. Every prune verdict here is evidence-INFERRED (CLAUDE.md references, event_log/memory mentions, task-folder presence on either fleet registry, explicit supersession language in another skill's own description), never a hard usage count — state what was checked and came back empty so the absence is verifiable, not asserted. The question is never "how often does this run" — it's "is there still a reason this needs to exist."

## Scope

Four independent read-only threads, each cheap to verify and each prone to going stale between audits because nothing else in the environment checks them together:
1. **Plugins & connectors** — `settings.json` (`enabledPlugins`, `skillOverrides`), `plugins/installed_plugins.json`, `plugins/cache/`, `plugins/marketplaces/` (a SEPARATE tree from cache — see `reference_plugin_cleanup_scope_cache_vs_marketplaces.md`, a prior cleanup missed it), `blocklist.json`, `confidential-repos.json`, and any MCP connector config. Cross-check against known-dead connectors in memory (Rube, Composio, QuickBooks Online MCP) to confirm none have crept back.
   **Usage method (no telemetry exists for this category — see Guardrails):** for each installed plugin, roll up its bundled skills' findings from thread 3 — a plugin whose every skill is `keep` is `keep`; a plugin whose every skill is a delete-candidate is itself a delete-candidate. For each MCP connector, cross-check against CLAUDE.md's "Tools & data" hierarchy (Notion/HubSpot/M365/Netlify are named there — `keep` by construction); for anything installed but not named there, check `mcp-needs-auth-cache.json` timestamps and any event_log/memory mentions of real use — zero on both is a `delete`-candidate, not a confirmed-unused.
2. **Scheduled-task fleet** — both registries live (CC/MCP + LAMS/Cowork), via `fleet-status.py` or direct registry reads. Look for: same-time collisions, duplicate-purpose task pairs, missed-cycle tasks (and whether they're throttled-and-retrying vs. gone silent — two different bug classes, don't conflate them), and throttle-skip trend direction (climbing vs. stabilizing).
3. **Skill catalog redundancy** — every `SKILL.md` in `~/ora-skills` (git status/log first — single-writer repo, read-only here so no claim needed) plus any local `~/.claude/skills`. Pairwise-check for overlapping trigger descriptions, and verify every apparent overlap against CLAUDE.md's own "Skill tie-breaks" section before flagging it — most are already resolved there or self-resolve via one skill's description explicitly chaining/deferring to another. Only a genuine, unresolved collision (a frontmatter trigger that contradicts a ratified tie-break) is a real finding. Also flag outsized skills (word count) that are both large AND high-frequency, since that combination is the actual token cost, not size alone.
4. **Token-bloat sources** — CLAUDE.md word count vs. its WARN/FAIL gate, MEMORY.md size vs. its gate, and — the check most likely to find something real — whether any self-monitoring artifact this environment produces (the System Schematic, or any future dashboard-style scheduled-task output) has an unbounded growth pattern: an ever-appending log with no cap, duplicated content, or no rollover step. A monitoring tool that becomes the token-spend problem it was built to catch is the single highest-value class of finding here (see the 2026-08-13 schematic rev-log fix, `~/.claude/scheduled-tasks/ora-cc-schematic-refresh/SKILL.md`, for the pattern to check other scheduled-task-authored artifacts against).

## Triggers

"Audit my setup", "optimize my Claude Code environment", "what's safe to remove", "reduce token spend", "refine my skills/plugins/scheduled tasks", or a reference to reviewing "the artifact" (System Schematic and/or Automation Audit) for setup health.

## Inputs

- `Artifact action:list` — find the current "ORA Automation Audit" artifact URL before doing anything else. This skill CONTINUES that artifact as a new numbered revision; it does not create a parallel one. If genuinely none exists (first-ever run), create it using the same masthead/kpi-grid/chip-table conventions this file's reference implementation established.
- The "Claude Code — System Schematic" artifact, if it exists, as a secondary live-status cross-check — but verify its claims against a direct file read before repeating them; its own prose has been wrong before (a transient plugin-flip incident got narrated as current state in one past revision).
- Direct reads of `settings.json`, both scheduled-task registries, `~/ora-skills`, and `~/.claude/maintenance/_state/` — ground truth beats any artifact's prose, always.

## Standard Workflow

1. **Locate continuity.** `Artifact action:list`, find the Automation Audit (or equivalent) URL. Read its most recent revision to know what's already been ruled on — don't re-litigate a closed finding without new evidence.
2. **Run the four threads.** Independent and parallelizable (spawn one Agent per thread if the session supports it) — they don't depend on each other. Each thread reports specific, named, file-and-line-cited findings, not impressions.
3. **Cross-verify claims that conflict.** When a source artifact's narrative disagrees with a live read (settings.json says X, the Schematic's prose says Y), the live read wins — say so explicitly rather than silently picking one.
4. **Synthesize into the artifact's existing format:** a new `rev-band` at the top (bump the revision number), updated/added KPI tiles for anything freshly measured, new sections per finding with a `keep`/`fix`/`combine`/`delete`/`ask`/`dead` chip verdict and cited evidence, and a footer note summarizing what changed. Findings that need Gabriel's call (ambiguous scope, a config file with contradictory state, anything touching a single-writer registry) get `ask`, not a unilateral edit.
5. **Do not execute fixes in the same pass unless explicitly asked to.** This skill's job is the investigation and the verdict table; executing `delete`/`fix`/`combine` calls against shared-checkout files (settings.json, scheduled-task registries, `~/ora-skills`) needs the single-writer claim protocol and, for anything hitting the blast-radius list (hooks/, registries, CLAUDE.md, governor code), Gabriel's explicit sign-off — keep investigation and remediation as separately confirmable steps, matching how the 2026-08-05 cleanup was ratified separately from the audit that found it.
6. **Publish via `Artifact`, passing `url:`** to update the existing artifact in place — never omit it, that orphans the link Gabriel already has.
7. **Memory:** one project-memory entry per audit revision (findings + what's pending Gabriel's call), pointed from `MEMORY.md`. Don't duplicate the artifact's content into memory — the memory entry is a pointer plus the two-or-three things a future session needs to know before trusting the artifact's claims at face value.

## Outputs

- Updated Automation Audit artifact (same URL, new revision).
- One project-memory pointer entry.
- Optionally, a short remediation plan (separate deliverable) for any `fix`/`delete`/`combine`-tagged finding Gabriel wants actioned — this skill produces the verdict, not necessarily the execution.

## Non-goals

Does not execute registry writes, plugin uninstalls, or skill deletions itself (see step 5). Does not replace `fleet-advisory-remediation` (which triages a pasted advisory into mechanical fixes) or `orphaned-task-forensics` (which root-causes a specific stale-producer symptom) — this skill is the periodic, broad, evidence-gathering pass those two operate on top of. Does not re-derive `~/.claude/maintenance/setup-self-audit.py`'s dark-task/frontmatter-regression/secret-scan/connector-reauth checks (already live, wired into `ora-health-guard`) — cite its last output for those specific findings rather than re-running the same logic.

## Changelog

- **v1.1 (2026-08-13):** Consolidated with `setup-declutter` (~/.claude/skills/setup-declutter, built the same session, never merged to `~/.claude` main or pushed here — an untracked, orphaned duplicate of this skill's scope). Folded in its Guardrails (never-flag allowlist, rarity-is-neutral framing, evidence-honesty statement) and its MCP-connector usage method into thread 1. `setup-declutter` is archived, not deleted, at `~/.claude/skills/_archive_2026-08-13_retired/setup-declutter/`. This is the fourth independent build of "audit/prune my Claude Code setup" (after a retired `ora-setup-audit` scheduled task in June and two comprehensive manual reviews in July) — logged to `event_log.md` 2026-08-13 so a fifth doesn't happen.
- **v1.0 (2026-08-13):** Initial build, closing the gap that Rev 7 of the "ORA Automation Audit" artifact was a one-off investigation with no skill to live in.
