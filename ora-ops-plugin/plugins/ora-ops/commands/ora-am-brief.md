---
description: ORA Morning Brief — runs the daily 9-section brief, inbox pre-brief, and cash snapshot by following the authoritative on-disk SKILL.md. Paste as a Claude Desktop scheduled-task prompt (daily 06:10 ET) or run interactively.
disable-model-invocation: true
---

Run the ORA Morning Brief. Open and follow this skill file EXACTLY as written — it is the authoritative, self-contained spec; do not improvise:
C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-am-brief\SKILL.md
Execute all applicable blocks in order (A Rate Prefetch → B Daily Brief 9-section report → C Inbox Pre-Brief → D Cash Snapshot), branching by today's ET day-of-week per the file's cadence table. Use the recipients, Notion page IDs, and Outlook send path named in the file (send-via-outlook.ps1 — the SOLE send path; Composio removed 2026-06-11, no fallback exists). Daily Brief → ggoldberg + egoldberg; Inbox/Cash → ggoldberg only. Do NOT email anyone not named in the file. Do NOT modify settings.json, ~/.claude config, hooks, or any memory file.
