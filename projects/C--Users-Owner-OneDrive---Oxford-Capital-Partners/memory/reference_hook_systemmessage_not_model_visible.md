---
name: reference-hook-systemmessage-not-model-visible
description: "A PreToolUse hook's `systemMessage` reaches the USER only — never the model. shared-checkout-guard fired ~168 times over 7 days while the agent it steers received nothing. Fixed 2026-07-16 via hookSpecificOutput.additionalContext. Check delivery, not just firing, when a guard 'exists but never helps'."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 0888c827-119f-4877-98ae-23ac7c404a27
---

**The contract** (verified against the official PreToolUse hooks reference, 2026-07-16):

| Channel | Reaches the USER | Reaches CLAUDE (the model) | Blocks? |
|---|---|---|---|
| `systemMessage` | ✅ transcript warning | ❌ **never** | no |
| `hookSpecificOutput.additionalContext` | ❌ | ✅ **yes** (wrapped in a system reminder) | **no** |
| `permissionDecision: "deny"` + reason | ✅ | ❌ (documented user-only) | yes |
| `permissionDecision: "ask"` + reason | dialog only | ✅ | prompts |
| exit 2 + **stderr** | ✅ | ✅ | **yes — blocks** |
| exit 0 + stderr | ❌ (debug log) | ❌ | no |

**`additionalContext` is the ONLY field that is both model-visible and non-blocking.**
`permissionDecision: "allow"` + `additionalContext` = warn the model without gating.
⚠ The docs self-contradict on whether deny's reason reaches Claude (a walkthrough says yes;
the field-visibility table says user-only). Trust the table; verify empirically if load-bearing.

**The incident.** `hooks/shared-checkout-guard.py` (shipped 2026-07-09) warns when you edit a
shared checkout holding another session's uncommitted WIP, and even names the live colliding
session. It emitted ONLY `systemMessage` + stderr, and exits 0 by design. So: it fired correctly
**~168 times across sessions for 7 days while the agent it exists to steer never received a single
warning.** Found 2026-07-16 when a session hit two shared-file collisions in one hour, caught both
by *manual* mtime inspection, and got no hook warning. Reproduced directly: the guard's marker was
written at 20:08:43 on an Edit; zero warning surfaced. Fixed by adding
`hookSpecificOutput.additionalContext` (13/13 guard tests green, 18/18 hook test files green).
**Verified end-to-end: the warning landed in the agent's context on the very Edit that applied the
fix.**

**How to apply.**
1. **A guard "existing" and being **registered** proves nothing about whether its output reaches
   anyone.** Firing ≠ delivery. When a guard seems to exist but never helps, test the CHANNEL —
   feed it a real payload and check what actually surfaces, don't just confirm it runs.
2. Writing a new warn-only PreToolUse hook? Use `permissionDecision: "allow"` +
   `additionalContext`. `systemMessage` alone is write-only memory as far as the agent is
   concerned. Keep both if the user should see it too.
3. Sweep done 2026-07-16: this was the ONLY hook with the defect. `ora-autonomy-gate`,
   `registry-write-guard`, `confidentiality-guard` all reach the model via exit 2 + stderr
   (blocking denies) and are fine; `eos-plan-gate`'s message is confirmed model-visible.

Related: [[project_tenant_db_no_sync_rootcause]] (the session that surfaced it) ·
[[reference_ripgrep_scheduled_tasks_false_negative]] (same session, same shape: a mechanism that
silently returns nothing rather than failing loudly) · [[rules]] §10.
