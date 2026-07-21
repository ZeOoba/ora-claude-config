---
name: feedback_shared_checkout_guard_session_attribution_unreliable
description: "shared-checkout-guard's \"session X is open right now (working)\" attribution can name a session with no trace in any registry — verify via list_sessions + session-env mtime before treating it as a live blocker"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0d9560cc-b5e5-4b44-bd5c-e7af834db249
  modified: 2026-07-21T16:37:20.494Z
---

On 2026-07-19, editing `~/.claude/projects/.../memory/MEMORY.md` (a covered path in `shared-checkout-guard.py`'s `DEFAULT_REPOS`), the guard twice fired a warning naming session `eda91426-76a8-493b-9111-eb4250c3f6c7` as "open right now (working)" — before and after the edit, unchanged. Direct verification found no evidence this session was live:
- Not present in `list_sessions` (active or `include_archived: true`).
- Its `session-env` directory existed but was empty and untouched for ~4 hours at check time.
- The actual uncommitted `MEMORY.md` diff the guard was reacting to had an mtime (2026-07-18 17:42) that predated the session-env directory's own creation (2026-07-19 11:23) — the flagged session couldn't have produced the WIP it was being blamed for.
- `git status --short` on `~/.claude` returned an identical 27-entry file set before and after the edit, with no changes attributable to another actor during the check window.

Proceeded with the edit given this evidence; no conflict materialized.

**Why:** the guard's session-attribution heuristic (whatever produces the "session X is open" name) is not the same signal as `list_sessions`/session-env activity, and can name a stale or already-terminated session. This is the same category as [[feedback_verify_wip_settled_via_mtime]] (isRunning isn't per-file) and [[feedback_verify_probe_findings_before_acting]] (a probe finding is a hypothesis, not a verdict) — a hook's claim of "this session is doing it" needs the same ground-truthing as a claim of "this file changed."

**How to apply:** when `shared-checkout-guard.py` (or any hook) names a specific session ID as the source of contention on a shared `~/.claude` path, don't take the attribution at face value even if it repeats unchanged across calls. Cross-check: (1) `list_sessions`/`get_session` for that ID, (2) the named session's `session-env/<id>/` directory mtime relative to now, (3) the actual conflicted file's own mtime relative to the named session's start time. If none of the three corroborate a live actor, the attribution is likely stale and it's reasonable to proceed with an additive, targeted edit rather than isolating/waiting indefinitely. This doesn't relax the underlying single-writer doctrine ([[reference_concurrent_session_duplicate_hardening_work]]) — it's specifically about not trusting an unverified session-ID label from the guard itself.

**Third instance (2026-07-21):** the guard named session `a039bb1f-a6df-44e4-9ba4-b2a8f160a2a9` as the source of ~30 uncommitted changes in `~/.claude` (including a genuine `event_log.md` content-loss incident — 6 entries missing vs. HEAD, restored separately). `get_session`/`list_sessions` didn't even return this ID (not `local_`-prefixed, so outside that tool's registry) — had to find it by grepping `session-env/` and `projects/<project>/*.jsonl` for the short ID directly. Once found: it's the `ora-aaos-expire-leases` scheduled-task run, transcript is a single turn (one `Bash` call to `AAOS\tools\expire-leases.py`), last activity 09:47 ET — ~2h48m stale at check time, not live. The script itself has zero references to `event_log.md` or the memory directory. Conclusively not the culprit for the file-content loss it was blamed for. Reinforces: verify via the session's actual transcript content (what tools did it call, on what files), not just recency — a session can be both "idle, not actually running" AND "provably never touched the flagged file," two independent reasons the attribution can be wrong.
