---
name: workflow-named-args-not-delivered
description: "Workflow({name, args}) silently drops args on the CC Desktop surface — scripts fall back to defaults; use scriptPath with hardcoded targets and verify the first agent prompt"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: dc65ba75-a691-40e7-85ac-57e4b5aff328
---

`Workflow({name: '...', args: {...}})` did **not** deliver `args` to the workflow script on the Claude Code Desktop surface (2026-07-16, proven on 4 independent runs: wf_ae4150f2-651, wf_9c31252e-d08, wf_e40dd80a-d54, wf_b9404c6c-a7d/wf_c92474b5-b38). The script's `args` global arrived unusable (first observed as a JSON-encoded string; post-guard runs behaved as `undefined`), so `cc-audit-army` silently fell back to cc mode on the default worktree — two full ~2.7M-token audits ran against oxford-command-center instead of their intended targets (ora-pm, the public site repo) before detection.

**Why:** the failure is silent and expensive — the launch call succeeds, progress looks normal, and the wrong-target result only surfaces ~40 min and ~2.7M tokens later. Script-side guards cannot fully protect: a string-args guard throws correctly, but `args === undefined` is indistinguishable from a legitimate bare invocation, so a default-target script silently runs its default.

**How to apply:**
1. For any parameterized named-workflow run where the wrong default is expensive, do NOT rely on `name` + `args`. Generate a per-target script copy with the parameters hardcoded as consts (pattern: `gen-audit-scripts.py`, anchored textual replacement of the args-derivation block), validate it with the mock-DSL harness (`~/.claude/workflows/_tests/harness.mjs`) asserting the intended target appears in the dispatched prompts, then launch via `Workflow({scriptPath})`.
2. ALWAYS verify launch: within the first minute, read the run's `subagents/workflows/<runId>/agent-*.jsonl` first prompt and confirm the worktree/target. Identical first-agent journal keys across two differently-parameterized runs = both ignored their args.
3. When authoring workflow scripts with an expensive default target, prefer fail-closed: throw when the expected args keys are absent, or require an explicit `confirmDefault: true` — [[verify-registry-mutation-claims]]-style "a launch isn't confirmed by the launch call; confirm from the run's own artifacts".

Related: [[verify-subagent-safe-claims]], [[verify-probe-findings-before-acting]].
