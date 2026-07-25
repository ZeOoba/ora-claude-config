---
name: workflow-invocation-gotchas
description: "Two proven Workflow-tool hazards — Workflow({name}) can serve a STALE session-start snapshot of an edited script (use scriptPath after in-session edits), and args passed as a JSON-encoded string silently defeats typeof-object guards (default-worktree fallback)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 506c87f0-3030-45f0-9886-9bd1de4311db
  modified: 2026-07-25T01:02:43.146Z
---

Two hazards proven on the same run (`wf_ae4150f2-651`, cc-audit-army, 2026-07-16):

1. **Stale named resolution.** `Workflow({name: 'cc-audit-army'})` executed a pre-session-edit copy of the script — no project-level shadow copy existed and the live `~/.claude/workflows/cc-audit-army.js` was current, so the name registry served a stale snapshot (predating even an 11:45 edit by another session). The run silently lacked the just-shipped cc-refresh scout.
   **How to apply:** after editing a named workflow, invoke it by `scriptPath` (the live file path) in the same session, not by `name`. Verify which script ran via the persisted `workflows/scripts/<name>-<runid>.js` copy the tool result links.

2. **Stringified args.** Passing `args` as a JSON-encoded string reaches the script as ONE STRING; `typeof args === 'object'` guards then fall back to defaults — the run audited the default shared checkout instead of the passed worktree (read-only contract meant no damage, but it defeated worktree isolation silently).
   **How to apply:** pass `args` as an actual JSON object in the tool call. cc-audit-army and cc-eval-plan-premortem now FAIL CLOSED on non-object args (2026-07-16). Note the contract is per-script: `verified-deal-recon` legitimately takes a PLAIN-STRING args — check the script's own docstring before copying the guard.

**Why:** both failures were silent — the workflow "succeeded" with valid-looking output; only the result's `worktree` field and the journal's missing `cc-refresh` record revealed them. Check `result.worktree`/`result.mode` and the agent roster against expectations after any parameterized run. Related: [[prompt-embedded-current-state-prose]], [[workflows-dir-single-writer-gap]].

**2026-07-24 recurrence (hazard 2, via scriptPath):** three `refute-financial-change` runs (`wf_c47d11aa-990`, `wf_04e3f4be-054`, `wf_a572d07e-620`) — args typed as JSON in the Workflow tool call arrived at the script as a STRING every time, even on the third run where the JSON was authored as an object-shaped value. The script's string-fallback (`typeof args === 'string' → treat as changeSet`) gracefully degraded: the whole JSON blob became the changeSet prose (so refuters still saw repo path + change description as text) but custom `lenses` were silently ignored — all three runs executed the DEFAULT 3 lenses. Detect it the same way each time: the verdicts' `lens` labels match the script's defaults, and `agent_count` is 3, not your lens count. Practical upshot: for refute-financial-change, steer attention via changeSet prose (works — round-2/3 refuters attacked exactly the flagged surfaces) rather than relying on custom lenses arriving; and treat the diagnostics echo's `args: "..."` (quoted string) as confirmation of stringification.
