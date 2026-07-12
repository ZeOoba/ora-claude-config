---
name: ora-cc-schematic-refresh
description: Daily refresh of the interactive "Claude Code — System Schematic" artifact with fresh live-health-check data (fleet status, governor/doctrine/memory probes, repo states) — republishes in place, no email, silent unless something material changed. v1.0 2026-07-12. [MODEL: claude-sonnet-5 | checked 2026-07-12]
---

ORA Claude Code Schematic Refresh — daily interactive-artifact updater (CC/MCP fleet). Read-only diagnostics + one file edit + one republish. No email under any circumstance.

PURPOSE: keep the "Claude Code — System Schematic" artifact (published at https://claude.ai/code/artifact/4ad3530d-f84f-4def-a472-d16ef107e74c) current with a fresh live-health-check snapshot every day, WITHOUT regenerating the whole page from scratch.

DURABLE SOURCE: C:\Users\Owner\.claude\artifacts\claude-code-schematic.html — Read it first. Make TARGETED Edit calls, not a full rewrite. Leave the static structural sections (Entry surfaces, Governance, Hook lifecycle, Skills & Plugins, Subagents, MCP Connectors, Scheduled fleet roster, Memory, Downstream systems) untouched UNLESS something structurally real changed (e.g. settings.json's enabledPlugins list, a hook script added/removed/renamed in ~/.claude/hooks/) — verify against the live source before touching a structural section; don't assume drift you haven't confirmed.

STEPS EACH RUN:
1. Re-run the same diagnostics the "Live health check" section already documents:
   - `python C:\Users\Owner\.claude\maintenance\fleet-status.py` (dual-fleet health — this is the canonical health check per memory/00_system_of_record.md; never hand-count fleet numbers)
   - `python C:\Users\Owner\.claude\maintenance\governor-drift-probe.py`
   - `python C:\Users\Owner\.claude\maintenance\doctrine-integrity-probe.py`
   - `python C:\Users\Owner\.claude\maintenance\memory-integrity-probe.py`
   - `python C:\Users\Owner\.claude\hooks\tests\test-confidentiality-guard.py` (run from that directory)
   - `git status --short --branch` + `git log --oneline -3` in `C:\Users\Owner\oxford-command-center` and in `C:\Users\Owner\ora-pm`
2. Update ONLY the "Live health check" section's node data, the top stat-strip numbers, the title-block revision date (bump the REV date/letter), and the footer note, reflecting TODAY'S actual observed results. Never invent a number or verdict you didn't observe this run. If a probe/tool errors, is missing, or is unreachable, say so plainly in that node ("probe unavailable this run — see raw output: ...") rather than guessing or silently reusing yesterday's number.
3. Republish via the Artifact tool, passing BOTH `url: "https://claude.ai/code/artifact/4ad3530d-f84f-4def-a472-d16ef107e74c"` AND `file_path: "C:\Users\Owner\.claude\artifacts\claude-code-schematic.html"`, so the EXISTING link updates in place. Never omit `url` — that mints a new artifact and orphans the existing one Gabriel already has bookmarked. Keep the same favicon (🧭) and title.
4. Log to `memory/event_log.md` via `python C:\Users\Owner\.claude\maintenance\append-event-log.py --entry-file <path>` (never pipe via stdin — known Windows UTF-8 mangling) ONLY if something materially changed since the prior run: a new doctrine/governor warning, a new fleet collision, a repo going from clean to dirty (or the reverse), a probe that started failing that wasn't before, or a scheduled task's enabled/disabled state flipping. Stay completely silent (no log entry) on an unremarkable day where nothing but routine numbers ticked.
5. No email under any circumstance for this task — it is a passive dashboard refresh, never an alert path.

GUARDRAILS:
- Never touch confidential-terms.json, CLAUDE.md, governor constants (DSCR 1.25x / LTV 40%), or any scheduled-task registry as part of this task — this task only edits the one HTML file and (conditionally) appends to event_log.md.
- `C:\Users\Owner\.claude\artifacts\` is already gitignored (`.gitignore` line 12) — do not try to commit this file or add it to git.
- If the Artifact tool errors, or a probe script referenced above is missing/renamed, STOP and note the gap plainly in the artifact's "Live health check" section (e.g. "fleet-status.py not found this run — entry skipped, needs a human look") rather than fabricating a result. Never fabricate firm/system data (Hard Invariant 7).
- This task never sends anything to an external surface and never mutates financial/governor code — no confirmation gate applies, but if you ever find yourself about to do something beyond "read diagnostics, edit one file, republish, optionally log", stop and flag it rather than improvising.

[MODEL: claude-sonnet-5 | checked 2026-07-12]