---
name: override-token-duplicate-key-silent-refusal
description: "config-write-guard's allow-config-write override token silently refuses to grant ANYTHING if the token file has been appended to more than once — a duplicate key across two blocks reads as ambiguous. Always overwrite the token file fresh, never append."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 79c92b15-49f5-46e8-b85d-01b789e04218
  modified: 2026-08-09T12:59:02.870Z
---

**`hooks/lib/override_tokens.py`'s `parse_token()` refuses the whole token file, with no distinguishing error, if it contains a duplicate key.** The block message for config-write-guard (and any other tier using this shared contract) tells you to "write this override token and retry" with `scope:` / `session:` / `reason:` lines — but if you `>>`-append a second grant to an already-existing token file (e.g. re-approving a second live edit in the same session, as happened 2026-08-09 mid-merge of the worktree.baseRef drift check), the file now has two `scope:` lines, two `session:` lines, two `reason:` lines. `parse_token()` hits `if key in fields: return None` on the first duplicate and returns `None` — `token_grants()` then reports "no valid token" with **exactly the same block message as before any token existed at all**. There is no "duplicate key" diagnostic surfaced anywhere; it looks identical to having never written the token.

**Fix:** always **overwrite** the override token file fresh (Write tool, full content replace) for each grant — never append, even when re-approving a second action in the same session under the same tier. One block, one grant, every time.

See also: [config-write-guard blast radius](tech.md) · [config-write-guard vs eos-review-gate deadlock](reference_config_write_guard_blocks_eos_review_gate.md) · [config-write quote-split gap](reference_config_write_guard_quote_split_gap.md) (same "gate silently refuses with an identical-looking message" failure shape, different root cause).
