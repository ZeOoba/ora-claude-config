---
name: reference_agent_vs_host_session_id_namespaces
description: "A session has TWO ids in disjoint namespaces — a claim/mirror id that list_sessions will never resolve, and a host id that only list_sessions/send_message speak. Look claim ids up in session-state.d, not list_sessions."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 21c98da5-56d2-49aa-bbe9-6626591e6fdd
  modified: 2026-08-09T15:27:47.715Z
---

Every session carries **two different ids**, and confusing them makes live sessions look like phantoms.

| | env var | shape | who speaks it |
|---|---|---|---|
| **agent id** | `CLAUDE_CODE_SESSION_ID` | `21c98da5-56d2-49aa-bbe9-6626591e6fdd` | claim files (`hooks/active-work/*.json`), the fleet-session mirror (`obsidian-fleet-mirror/session-state.d/<id>.json`, its `_sid`), `session_liveness.py`, `override_tokens.py`, both pre-push gates, `allocate-oi-id.py`, the scratchpad path |
| **host id** | `CLAUDE_CODE_HOST_SESSION_ID` | `local_c689f07f-d45a-473e-94d9-3f418c47e5cd` | `list_sessions`, `send_message`, handoff notes written by hand |

**They never match, by construction — not by bug.** A claim id searched against `list_sessions` returns
nothing at any limit, including `include_archived`. That is the expected result, NOT evidence the session
is dead, phantom, or that the claim protocol is broken. (`list_sessions` also always excludes the *current*
session, which compounds the illusion.)

**To resolve a claim-holder id:** look for `obsidian-fleet-mirror/session-state.d/<agent-id>*.json`. That
file carries `status`, `started`, `lastAt`, `lastTool` and recent activity. It is the lookup table;
`list_sessions` is not.

**To message a claim holder:** as of 2026-08-09 claim files also record `host_session_id`, and both
`claim_work.py list` and the SessionStart broadcast print it (`(message it at local_…)`) — paste that into
`send_message`. Claims written before that date have no host id and their owner still cannot be contacted
directly; fall back to the mirror to at least confirm the session is alive. See [[open-items-tracker]]
`#OI-108` for the fix and its accepted residual.

**Do not "fix" this by flipping `own_session_id()` to prefer the host id.** The agent id is the ownership
identity for renew/release/collision matching AND the join key to the agent-id-keyed fleet mirror; swapping
it desynchronizes `session_liveness.py`. Record both, never substitute.

Related: [[reference_concurrent_session_duplicate_hardening_work]], [[feedback_verify_before_repeating_session_claims]].
