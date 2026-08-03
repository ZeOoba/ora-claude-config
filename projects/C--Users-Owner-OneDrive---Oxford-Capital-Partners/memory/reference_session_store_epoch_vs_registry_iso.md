---
name: reference_session_store_epoch_vs_registry_iso
description: "Session metadata stores timestamps as epoch MILLISECONDS while the scheduled-task registry stores ISO-8601 strings — in the same tree; the MCP tools render both as ISO, hiding the split."
metadata: 
  node_type: memory
  type: reference
  originSessionId: d7d856aa-b765-41b5-a18a-fce7b502ab07
  modified: 2026-08-03T20:35:06.652Z
---

Two files under the CC/MCP store disagree on timestamp encoding, and nothing warns you:

- **Session metadata** (`…\claude-code-sessions\<guid>\<guid>\local_<id>.json`) — `createdAt`, `lastActivityAt` are **epoch milliseconds as integers** (e.g. `1785351608517`).
- **Scheduled-task registry** (`scheduled-tasks.json`, same directory) — `lastRunAt` is an **ISO-8601 Z string** (e.g. `"2026-08-03T15:29:29.926Z"`).

**The trap:** `list_scheduled_tasks` and `get_session` both render these as ISO. Anyone who has only ever read through the MCP tools will write a parser that assumes ISO, and it will be right for the registry and wrong for the session store. A string-only parser does not raise on an int — it returns `None`, and whatever check depended on that timestamp silently becomes a no-op.

Confirmed live 2026-08-03 while building `maintenance/dangling-mutation-probe.py`: an ISO-only parser made the probe's 14-day lookback filter degrade to "scan all history" (192 → all 373 sessions) and made live-session exclusion never fire once (`live_excluded=0`), which in turn produced a false LOST_WRITE against a session that was simply mid-flight. Neither failure produced an error. Fix: parse both — an int/float is epoch (`>1e11` ⇒ milliseconds), a str is ISO.

**Related time hazard, same probe:** `lastActivityAt` stops advancing while a session is BLOCKED on one long tool call (a gated `git push` running the full pre-push suite, a long agent dispatch). A short liveness window therefore ages a still-running session out and reports its in-flight call as dead. Consecutive runs minutes apart disagreed (exit 1, then exit 0) purely from sessions crossing a 20-minute boundary — the window is now 120 min.

See [[reference_scheduled_task_model_standard]] for the incident that motivated the probe, and [[reference_scheduler_lastrunat_stamped_at_dispatch]] for a separate `lastRunAt` semantics trap (stamped at dispatch, not completion) — the two are independent, and both bite anything reasoning about "when did this task last actually run".
