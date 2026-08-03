---
name: reference-config-write-guard-blocks-eos-review-gate
description: "Guard deadlock — eos-review-gate demands a recorded review to commit hooks/**, but config-write-guard blocks the --record command itself"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 83715320-ea98-4ae2-8ebd-e3ec6f2163dd
  modified: 2026-08-03T20:39:16.264Z
---

Landing any `hooks/**` change (including **`hooks/tests/**`**) hits a guard-vs-guard deadlock:

1. `eos-review-gate` blocks `git commit` until an independent review is recorded via `eos-review-gate.py --record`.
2. `config-write-guard` blocks that `--record` invocation — its matcher is "write indicator + governance-path marker **anywhere in the command text**", and the script's own path contains `hooks/`.

Hit 2026-08-03 landing the eos-telemetry-rollup session-dedupe fix.

**The blocked write is not governance code.** `--record` writes `hooks/sessions/<session-id>/reviews/<key>.json` — gitignored, session-scoped state, deliberately placed there so an artifact can't be swept into a commit by `git add -A`. `config-write-guard` matches on the `hooks/**` prefix and cannot tell session state from the hook layer.

Resolution (Gabriel, 2026-08-03): mint `allow-config-write` for the record + commit. Recording is the honest path — `allow-unreviewed-commit` would misstate the audit trail when a review actually happened.

**Do not route around the matcher.** Rewriting the path via `cygpath`/`$HOME`/variables to slip past it is evasion of a security guard, and the guard's message explicitly says it is *deliberately* not narrowed. Reshaping a command so it no longer *names* the tree is only legitimate when the target genuinely is a blessed worktree and the effect is identical (e.g. `git add -A` inside an isolated worktree whose `git status` you just verified holds only your files). When genuinely deadlocked: stop and ask.

Standing friction: the worktree escape hatch `config-write-guard` recommends does **not** avoid this, because the review gate fires on commit regardless of which checkout you are in. Candidate fix (unbuilt, needs its own review round): carve `hooks/sessions/**` out of `config-write-guard`.

Related: [[feedback_confidentiality_guard_selfdeadlock]] · [[reference_autonomy_gate_override_mechanism]] · [[feedback_auto_review_blast_radius_gate]]
