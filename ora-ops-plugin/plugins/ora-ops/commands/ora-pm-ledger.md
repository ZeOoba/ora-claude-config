---
description: ORA Evening Ledger — runs the Notion daily digest, weekday outbox QC sweep, and EOD action ledger by following the authoritative on-disk SKILL.md. Paste as a Claude Desktop scheduled-task prompt (daily 18:00 / 06:00 PM ET) or run interactively.
disable-model-invocation: true
---

Run the ORA Evening Ledger. Open and follow this skill file EXACTLY:
C:\Users\Owner\.claude\scheduled-tasks\ora-pm-ledger\SKILL.md
Execute the three blocks in order (A Notion Daily Digest → B Outbox QC Sweep [weekdays] → C EOD Action Ledger), branching by ET day-of-week per the file. Use the send paths/recipients in the file (ALL blocks → ggoldberg@oxfordra.net only per routing canon; send-via-outlook.ps1 — the SOLE send path, Composio removed 2026-06-11). Block C's autonomy is bounded by its HARD GUARDRAILS in the file: no counterparty send, no production deploy, no money movement, no system-of-record mutation. Do NOT modify settings.json, ~/.claude config, hooks, or memory files.
