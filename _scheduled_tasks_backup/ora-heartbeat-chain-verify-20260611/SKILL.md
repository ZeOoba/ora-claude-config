---
name: ora-heartbeat-chain-verify-20260611
description: One-time verification (2026-06-11 06:50 ET) that the restored ora-cowork-heartbeat actually fired its first 05:50 ET slot and updated the Notion page. Silent on success; auto-sends a short alert to ggoldberg only on failure (meta-failure exemption). Self-retires after firing.
---

One-time chain verification for the restored Cowork heartbeat (registered 2026-06-10 during the system audit; first scheduled fire was 05:50 ET today, 2026-06-11).

STEP 1 — Call the Notion fetch tool on page ID `35c6ecd8-9e59-81d5-8d2c-d08002458b78` (Cowork Heartbeat — 2x/day signal). Read the `Last heartbeat: <timestamp>` line.

STEP 2 — Evaluate: PASS if the timestamp is ≥ 2026-06-11T09:45:00Z (i.e., this morning's 05:50 ET fire, allowing jitter). FAIL if older (the page previously read 2026-05-31T20:42:42Z — if it still does, the task did not fire or stalled on a permission prompt).

STEP 3 — On PASS: print exactly one chat line `HB-CHAIN ✅ first restored fire verified <timestamp>` and stop. No email, no Notion writes.

STEP 4 — On FAIL: this is a monitoring meta-failure (the restored dead-man's-switch failed its first fire), so auto-send is permitted. Send ONE short email via Outlook COM using Desktop Commander with the full interpreter path:
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1"
(inspect the script's parameters first with a quick read if needed). To: ggoldberg@oxfordra.net ONLY (per 2026-05-15 routing directive — never cc egoldberg). Subject: "⚠️ ora-cowork-heartbeat first fire FAILED — 2026-06-11". Body: the stale timestamp found, the expected threshold, and the two most likely causes: (a) LAMS task stalled on un-pre-approved Notion tool permission — fix: open Cowork → Scheduled → ora-cowork-heartbeat → Run now and approve tools; (b) Cowork app was closed at 05:50 — heartbeat catch-up will run on next app launch; re-check then. If the COM script errors, print the failure loudly in chat instead. Tag body: AUTO-SENT — meta-failure path.

STEP 5 — Nothing else. Do not modify any task, page, or file.