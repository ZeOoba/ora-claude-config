---
name: setup-declutter
description: On-demand, read-only audit of Gabriel's Claude Code / Cowork setup — skills, plugins, MCP connectors, and scheduled-task routines — to surface pruning CANDIDATES with evidence. Never deletes or disables anything itself. Use when Gabriel asks to prune, declutter, clean up, find unused skills/plugins/connectors/routines, reduce bloat, or audit the setup for what can be removed. Distinct from fleet-advisory-remediation (scheduled-task registry hygiene only) and consolidate-memory (memory files only) — this spans all four customization types in one pass. No invocation telemetry exists on disk anywhere in ~/.claude (confirmed 2026-08-13) — every finding is inferred evidence, never a hard usage count. Treat rarity as neutral, not as bloat.
---

# Setup Declutter (on-demand customization prune-scout)

Read-only advisory pass across four customization types — skills, plugins, MCP connectors, scheduled-task routines. Produces a ranked KEEP / INVESTIGATE / PRUNE-CANDIDATE report with evidence. Never deletes, disables, or archives anything itself — Hard Invariant 6 requires archive-not-delete and Gabriel's explicit call on every removal.

## Why this is evidence-inferred, not usage-metered

No file, log, or telemetry anywhere in `~/.claude` records per-skill/plugin/connector invocation counts (confirmed by direct search 2026-08-13 — the one place a usage number ever surfaced was a manually-read Cowork skill-store UI figure at unpublish time, not a queryable file). Every finding below is INFERRED from indirect signals. Treat low apparent frequency as neutral: some of the most important items in this setup exist for rare, high-stakes events — a once-a-year ratification, a credential rotation on a multi-year cycle, a compliance gate that only fires when a specific bad thing happens. The question this skill answers is never "how often does this run" — it's "is there still a reason this needs to exist," which requires reading what it does, not just when it last fired.

## Never flag (skip outright)

- Anything named in `CLAUDE.md` (skill tie-breaks, Hard Invariants, routing canon) — referenced there means load-bearing regardless of frequency.
- Anything gating a Hard Invariant, a financial governor (DSCR/LTV constants), or a compliance/legal function.
- Anything with a documented multi-year recurrence (e.g. a credential-rotation skill) — rarity by design, not by neglect.

## Method

1. **Skills** — enumerate personal (`~/.claude/skills/`), plugin-provided, and Cowork-hosted (`anthropic-skills:*`, from the live skill listing at invocation time) skills. For each, gather:
   - Does `CLAUDE.md` or its skill-tie-break section reference it? → KEEP, stop here.
   - Last `git log` touching its SKILL.md (for repo-backed skills) — recent edits signal active maintenance, not the same thing as usage but worth noting.
   - Mentions in `event_log.md` / memory files — any evidence it was ever actually invoked or its output used downstream.
   - Is it explicitly superseded/subsumed by name in another skill's own description (CLAUDE.md already documents several supersessions, e.g. `acquisition-underwriting` subsuming `deal-screen`/`cap-rate-snapshot`/`market-comp-analyzer`) — if the subsumed skill is STILL separately installed, that's a direct PRUNE-CANDIDATE, not just INVESTIGATE.
   - Zero hits across all of the above → PRUNE-CANDIDATE, but state explicitly what was checked and came back empty, so the absence itself is verifiable rather than asserted.
2. **Plugins** — read `installed_plugins.json` + `known_marketplaces.json`. For each installed plugin, roll up the skill-level findings for everything it ships: a plugin whose every skill is KEEP is KEEP; a plugin whose every skill is PRUNE-CANDIDATE is itself a PRUNE-CANDIDATE. Cross-check `ora-weekly-hygiene` Block H's duplicate-plugin-entry logic if its last output is readable rather than re-deriving that check — cite it.
3. **MCP connectors** — enumerate configured servers. Cross-check against `CLAUDE.md`'s "Tools & data" hierarchy (Notion, HubSpot, M365, Netlify are named there — KEEP). For anything installed but not named in that canonical list, check `mcp-needs-auth-cache.json` timestamps and any event_log/memory mentions of real use. Absence of both → PRUNE-CANDIDATE.
4. **Routines (scheduled tasks)** — pull the live registry via `list_scheduled_tasks` (both fleets — CC/MCP and LAMS/Cowork); never answer from memory, per the standing fleet rule. Cross-reference retired-but-still-registered or duplicate entries already surfaced by `ora-weekly-hygiene` / `ora-task-integrity-guard` / `fleet-advisory-remediation` rather than re-running that logic — cite their last output. Flag only NEW candidates those mechanisms wouldn't already catch (e.g. an enabled task with a thinning run history that hasn't yet tripped `automation-health-monitor`'s missed-run threshold).

## Output

One ranked table: **item · type · verdict (KEEP / INVESTIGATE / PRUNE-CANDIDATE) · evidence checked · why**. PRUNE-CANDIDATEs first. Close with: *"Nothing above was changed. Removal requires your call and follows Hard Invariant 6 (archive to `/archive/`, never delete)."*

## Rules

- Read-only. Never edit, disable, retire, or delete anything — that is a separate, explicitly-approved follow-up action, not part of this pass.
- If a category's evidence source is unreadable (e.g. the live scheduled-task registry can't be reached), say so and mark that category UNCHECKED rather than silently skipping it or guessing.
- Be concise — one line of evidence per verdict, not a narrative.
