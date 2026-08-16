---
name: reference-hookify-noop-hooks-every-tool-call
description: "hookify ran no-op pre/post hooks on every tool call until 2026-08-13, when it stopped — it is NOT currently firing; and the method error that hid that (bucketing transcripts by file mtime instead of event timestamp)"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 76023481-9a6c-40ff-b91f-8bd263f287d8
  modified: 2026-08-16T21:12:34.936Z
---

**Status: HISTORICAL. hookify is not firing as of 2026-08-13.** Do not go looking for a toggle to disable — there is nothing to turn off. This note is kept for the method lesson, which is the durable part.

## What was true, until 2026-08-13

The `claude-plugins-official` **hookify** plugin registered `hooks/pretooluse.py` and `hooks/posttooluse.py` against **every tool**, with no rules to evaluate: `core/config_loader.py:210` globs `.claude/hookify.*.local.md`, and no such file exists anywhere under `~/.claude` (only the plugin's own `examples/`). Each invocation loaded an empty ruleset and returned `{}` — confirmed by the recorded `stdout: "{}"`. `pluginUsage` shows **225,556 lifetime invocations**.

Last recorded run: **2026-08-13T07:49:58Z** (`PostToolUse:Read`, 1,925 ms). Zero Read-event hook attachments on 08-14, 08-15, or 08-16, across the newest 60 transcripts. Since hookify was the *only* source of Read-event hooks — no hook in `~/.claude/settings.json` matches `Read` — Read-event hook runs are a clean liveness proxy for it. That count is now zero.

## ⛔ The method error — this is the reusable part

The stale finding survived because hook timings were bucketed by **transcript file mtime**, not by each event's own `timestamp`. **A resumed session's `.jsonl` is touched today but contains lines from days earlier.** So selecting "the 50 most recently modified transcripts" and calling it a 2-day window silently pulled in week-old events, and hookify's pre-08-13 runs were reported as current activity.

**Rule: when aggregating anything from transcripts — hook durations, tool counts, denials — bucket by the event's own `timestamp` field. File mtime selects which files to open; it never dates the lines inside them.** Cross-check any "current" claim by confirming the metric is non-zero on today's date specifically.

This is the same family as [[feedback-prompt-current-state-prose]] and [[feedback-findings-decay-recheck-before-writing]]: an aggregate computed across a window that straddles a change reads as a live condition.

## What IS still live

The companion half of OI-176 stands and was measured correctly: the `PreToolUse:Bash` chain runs **153 times on 2026-08-16 alone**, 10 of the 31 configured hooks match `Bash`, each a cold Python start — median 716 ms, p90 2,310 ms. See [[open-items-tracker]] OI-176.

Found and corrected during the `/doctor` pass 2026-08-16; see [[reference-disable-autoupdater-blocks-manual-update]] from the same pass.
