---
name: feedback-config-write-guard-no-fast-path
description: "Don't add a low-risk/single-line fast-path to config-write-guard.py — investigated 2026-08-14, correctly declined; single-line edits to settings.json/hooks/CLAUDE.md are not a safe risk proxy and the manual token-mint step is deliberate"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 18229ac6-a66a-4058-8086-5b21d2f6f06a
  modified: 2026-08-14T18:27:02.441Z
---

**Rule:** never propose or build a "fast path" / size-based exemption for
`hooks/config-write-guard.py` (the PreToolUse governance-layer write gate on
`hooks/**`, `settings.json`, `settings.local.json`, `CLAUDE.md`, scheduled-task
registries). Flagged as friction in a 2026-08-14 session after minting a token
by hand to flip one `enabledPlugins` boolean — investigated before building
anything, and correctly declined.

**Why:** the gate's own docstring (2026-07-18, "Plan 5" hardening) states the
loudness is the point — before it existed, hooks/**, settings.json, and
CLAUDE.md had no hard write-gate at all. "Single-line" is not a safe risk
proxy inside these files: `"disableAllHooks": true` or deleting one hook's
`matcher` are also single-line edits with catastrophic blast radius. The
codebase has already been burned once by narrowing a matcher in this same
file (the 2026-08-03 regression referenced in `config-write-guard.py`'s own
comments, where a boundary "fix" un-flagged real composite writers). The
manual token-mint step (mkdir + Write, ~2 tool calls) is also deliberate per
`hooks/lib/override_tokens.py`'s docstring — "It may be created ONLY after
Gabriel's explicit in-turn confirmation... Scheduled/headless sessions must
NEVER self-create one." A one-shot mint helper would blur that human-in-the-
loop boundary.

**How to apply:** if a future session (mine or another) flags this same
friction, point here instead of re-investigating from scratch. The correct
response to "this gate is annoying for a small edit" is to confirm the edit
really is small in *effect*, not just line count, then pay the manual-token
cost — not to weaken the gate. Analogous ratified precedent for narrow,
deliberate (not blanket) carve-outs on blast-radius gates:
[[feedback-auto-review-blast-radius-gate]] (Gabriel scoped that one gate's
scope explicitly in-turn; nothing here has been so scoped).
