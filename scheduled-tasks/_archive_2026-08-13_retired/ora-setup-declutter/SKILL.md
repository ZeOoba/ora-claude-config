---
name: ora-setup-declutter
description: Monthly wrapper — invokes the setup-declutter skill (read-only skills/plugins/connectors/routines bloat audit) and posts its ranked table to the Notion Operations Hub. Never deletes, disables, or archives anything itself. [MODEL: claude-sonnet-5 | set 2026-08-13]
---

Monthly ORA setup-bloat audit (CC/MCP fleet). This task is a THIN WRAPPER — it does not contain any audit logic of its own.

1. Invoke the `setup-declutter` skill (via the Skill tool, skill name `setup-declutter`, found at C:\Users\Owner\.claude\skills\setup-declutter\SKILL.md) exactly as written. Do not re-derive, duplicate, or "improve" its detection logic in this task — let it run its own method across all four customization types (skills, plugins, MCP connectors, scheduled-task routines) unmodified.

2. Capture setup-declutter's full ranked output table: item · type · verdict (KEEP / INVESTIGATE / PRUNE-CANDIDATE) · evidence checked · why. PRUNE-CANDIDATEs are listed first per its own Output convention.

3. Post that table as a new child page under the Notion Operations Hub (parent_id 32b6ecd8-9e59-81f2-b329-df3fd0e25062), titled "Setup Declutter Audit — {ISO DATE of this run}", via notion-create-pages. Reproduce setup-declutter's table faithfully — do not add, drop, or reword findings. Include its closing line verbatim ("Nothing above was changed. Removal requires your call and follows Hard Invariant 6 (archive to /archive/, never delete).").

4. If setup-declutter marks any category UNCHECKED (its own convention for an unreadable evidence source, e.g. the live scheduled-task registry being unreachable), surface that prominently at the TOP of the Notion page, not buried in the table — an unchecked category is a data-quality gap, not a clean result.

5. This task's ONLY output is the Notion page. Do not send an email. Do not modify, disable, retire, or archive anything — that is Gabriel's explicit follow-up decision per Hard Invariant 6, never automatic here.

6. Never fabricate a finding, a verdict, or evidence setup-declutter did not itself produce. If the Skill tool invocation fails outright, report that failure on the Notion page instead of silently skipping the run.