---
name: provenance-claim-mechanism-already-exists
description: "Don't build a new \"declare I'm holding this file\" claim-file+TTL mechanism — commit-provenance-recorder's touched-files.txt + session_liveness + ttl_h() already is one."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 53f57fbe-7aee-490a-98aa-61f29d5c9aea
  modified: 2026-07-24T16:26:04.189Z
---

Investigated 2026-07-24, in response to a "add declarable deferral (claim file +
TTL)" proposal — a mechanism a session could use to signal "I'm deliberately holding
these paths uncommitted, don't sweep me" before a foreign janitor commit lands.

**Finding: this already exists and works as designed.** `commit-provenance-recorder.py`
(PostToolUse) writes every session's touched paths, each with its own timestamp, to
`hooks/sessions/<sid>/touched-files.txt`. `commit-provenance-guard.py` (PreToolUse)
reads that file for every OTHER live session, gated on `session_liveness.py`
affirmatively reporting the session open AND the touch being within `ttl_h()`. That
*is* a claim-file-with-TTL, fail-open by construction (missing/stale/unreadable data
→ allow, never block) — exactly the shape the proposal asked for, ratified doctrine
per [[feedback_fail_open_over_mutex_for_fleet_gates]].

The 2026-07-24 incident this proposal was responding to was **not** a missing
declaration mechanism. Per the durable record in `event_log.md` (2026-07-24, the
`44efc61` entry and its confirmation), every precondition for the EXISTING mechanism
to fire was met — recorder healthy, liveness healthy, touch well within TTL, no
override sentinel — and it still didn't block, because a separate, specific bug
(`candidate_paths()`'s compound-`git add`-command blind spot) meant the guard never
got as far as consulting the touched-set at all. See
[[reference_commit_provenance_guard]] and event_log 2026-07-24 for the confirmed root
cause and the fix (`485a62d`).

**Do not build a second, parallel claim mechanism.** Two independent systems
answering "is this file spoken for" is a worse failure mode than the one being
solved — they can drift out of sync, and a future reader has to know which one is
authoritative. The correct fix for a claim mechanism that isn't firing is to fix why
it isn't firing (done), not to add a redundant one next to it.

If a genuine gap in the EXISTING mechanism is found later (e.g., a session that wants
to hold a claim past `ttl_h()`, or a way to declare intent before the first
`Edit`/`Write` touch is recorded), extend `commit-provenance-recorder.py` /
`commit_provenance.py`'s existing contract rather than adding a new file format.

Related: [[reference_commit_provenance_guard]] · [[feedback_fail_open_over_mutex_for_fleet_gates]] · [[feedback_positive_attribution_over_mtime]].
