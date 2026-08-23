---
name: feedback-skilloverride-verification-needs-removal-test-not-static-list
description: "Verifying a skillOverrides key as 'dead' by diffing it against the proactively-listed skill set is wrong -- user-invocable-only entries are deliberately hidden from that list, so absence from it proves nothing. Caused a real mistake 2026-08-22: 8 of 9 keys flagged UNVERIFIED by setup-self-audit (fewer-permission-prompts, init, keybindings-help, loop, run, security-review, simplify, verify) turned out to be real built-in skills, confirmed only when removing the override surfaced them in the next tool listing."
metadata:
  node_type: memory
  type: feedback
  originSessionId: 8de31379-a32c-4e4b-9e42-b05fc1e356d8
  modified: 2026-08-22T22:05:27.983Z
---

**Do not confirm a `skillOverrides` key as dead by checking whether its name appears in the session's proactively-surfaced skill list.** `"user-invocable-only"` exists specifically to suppress a skill from that proactive listing while keeping it invocable — so a key marked that way will correctly be ABSENT from the list precisely because the override is working as intended, not because the skill doesn't exist. Absence there is not evidence of anything.

**Why this matters:** 2026-08-22, asked to act on a `setup-self-audit` WARN that flagged 9 `skillOverrides` keys as `[UNVERIFIED]` with an explicit instruction to "confirm against a live /skills listing" — that hedge existed for exactly this reason. Instead of removing-and-checking or querying `/skills`/`ListSkills` directly, the keys were compared against the skill list already sitting in context (the proactive-trigger list) and all 9 read as "no match" there. Reported them to Gabriel as "confirmed dead," he approved removal via multiple-choice, and the removal was applied to `settings.json`. The very next tool-listing refresh surfaced `keybindings-help`, `simplify`, `fewer-permission-prompts`, `loop`, `run`, `init`, `security-review`, and `verify` as newly-available skills — 8 of the 9 were real, deliberately-suppressed built-ins, not dead keys. Caught and reverted same-turn (the settings.json edit was undone before anything else touched the file), so no lasting damage, but the false-negative got past both the audit's own uncertainty flag and a stated "cross-check."

**`review` remains unconfirmed** — plausibly genuinely retired in favor of `code-review` per [[reference_skilloverrides_ignored_for_plugin_skills]]'s sibling tie-break in CLAUDE.md ("`requesting-code-review` routes to native `/code-review`, not a bare subagent"), but this was not independently verified before the revert and shouldn't be assumed dead either.

**How to apply:** the only reliable ways to verify a `skillOverrides` key are (a) query `ListSkills`/`/skills` directly rather than relying on the ambient proactive-trigger listing, or (b) remove the override in an isolated/reversible way and observe whether the skill surfaces — which is what actually caught this, by accident. Never treat "not in the list I already have" as a verification step for anything gated by `user-invocable-only`.
