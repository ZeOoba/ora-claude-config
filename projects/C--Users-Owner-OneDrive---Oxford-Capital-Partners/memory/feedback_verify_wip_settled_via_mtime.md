---
name: feedback-verify-wip-settled-via-mtime
description: "2026-07-17: a session's isRunning:true (or the mere presence of uncommitted changes) is not proof a file is still actively being edited -- compare file mtimes across two checks spaced ~15+ min apart before treating dirty-but-uncommitted content as abandoned/stale/safe-to-commit-on-their-behalf, or as still-in-flight. Used repeatedly during a multi-hour merge that kept colliding with concurrent memory-file edits."
metadata:
  type: feedback
  originSessionId: 41bfc8fa-2412-44b6-a527-f9a4631e86f5
---

**The pattern.** Waiting to merge a branch into `main`, repeatedly blocked by other sessions'
uncommitted changes to shared memory files (`open-items-tracker.md`, `event_log.md`, `MEMORY.md`).
`git status --short` alone can't distinguish "someone is mid-edit right now" from "someone finished
20 minutes ago and moved to something else, just never ran `git commit`." Both look identical as a
single snapshot.

**The check that actually discriminates:** compare the file's `mtime` (`ls -la --time-style=full-iso`)
across two checks separated by a real interval (the same ~15-30 min cadence used for the merge-wait
loop itself). If the mtime is IDENTICAL between two checks that far apart, the content has genuinely
settled — nobody touched it in the intervening window, regardless of what `isRunning` says for any
session. If the mtime moved, it's still live, even if every currently-listed session shows
`isRunning:false` (a session can go idle between tool calls and still be "working" in the sense that
matters here).

**Why this beat the naive signals:**
- `mcp__ccd_session_mgmt__list_sessions`'s `isRunning` flag is per-session-right-now, not
  per-file — a session can be `isRunning:true` on something else entirely while the file you care
  about hasn't moved in an hour, and a session can flip to `isRunning:false` between polls while
  still mid-task.
- Diff size trending toward a stable number (not just "still nonzero") was a secondary corroborating
  signal, but diff size can plateau mid-edit too (e.g. between two bursts) — mtime is the harder
  fact.
- A single stale-looking snapshot is not enough either: one check early in this same session found a
  4-line diff that looked "probably done," but the very next check (minutes later) found it had
  actually already been committed by its owner — the safest move was still to verify fresh each time,
  not to shortcut based on one prior read.

**How it changed the actual decision:** only committed another session's WIP on its behalf (with
explicit user authorization to do so generally) once mtime had been confirmed identical across two
checks spanning a full wait interval — not on the first sighting of "looks stale," and not purely
because no session currently showed `isRunning:true`.

**Not (yet) worth building:** an automated stability-detector or polling script. This was a
one-off manual pattern applied by hand across ~2 hours of a single merge wait; if this recurs often
enough to be worth codifying into a hook or maintenance script, that's a systematization candidate,
not something to build reactively here.

Related: [[reference_concurrent_session_duplicate_hardening_work]] (the collision-discovery side of
this same multi-session-editing problem; this file is the companion tactical technique for judging
whether a discovered collision is still live once you've found it).
