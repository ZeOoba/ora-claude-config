---
name: canary-model-check-temp
description: RETAINED AS DOCUMENTATION (no delete tool exists on this surface). One-time canary fired 2026-07-08T20:11 UTC from a Sonnet-5 session; self-reported running as claude-opus-4-8[1m] (Opus 4.8, 1M context) — proves CC/MCP scheduled tasks do NOT bind to the creator session's model (matches anthropics/claude-code #48976). Full writeup: event_log.md 2026-07-08 "CC/MCP scheduled-task model-currency investigated". Auto-disabled after firing — inert, safe to ignore.
---

This is a one-time throwaway canary task used to test which model CC/MCP scheduled tasks actually run on. It has no relation to any ORA business process.

Do exactly this and nothing else:
1. Determine your own exact model identity from your system prompt (it states something like "You are powered by the model named X. The exact model ID is Y.").
2. Write a single line to the file C:\Users\Owner\.claude\scheduled-tasks\_canary-model-check-result.txt (create it if it doesn't exist, overwrite if it does) in exactly this format:
   MODEL: <exact-model-id-here> | NAME: <model-name-here>
3. Do not modify any other file. Do not touch any other scheduled task. Do not send any email or Notion write. Stop after writing the file.