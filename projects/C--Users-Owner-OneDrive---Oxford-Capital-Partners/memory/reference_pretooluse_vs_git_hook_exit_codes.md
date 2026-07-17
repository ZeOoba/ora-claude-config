---
name: reference-pretooluse-vs-git-hook-exit-codes
description: "PreToolUse hooks and git hooks (pre-push) use OPPOSITE exit-code conventions in this repo: PreToolUse exit 1 = non-blocking (tool call proceeds), only exit 2 blocks; a git hook, ANY non-zero exit blocks. Reasoning from one gate's semantics while editing the other silently disables it. Bit ora-autonomy-gate.py 2026-07-17 (ImportError -> exit 1 -> prod deploy passed through)."
metadata:
  type: reference
  originSessionId: 794cdebc-d469-4137-b46e-43a56a39b1b0
---

**The contract, both directions, verified against the official Claude Code hooks reference:**

| Hook type | Exit 0 | Exit 1 | Exit 2 |
|---|---|---|---|
| PreToolUse (`hooks/ora-autonomy-gate.py`) | allow | **non-blocking error — tool call PROCEEDS** | block |
| git hook (`hooks/git-prepush-doctrine-gate.py` via `.git/hooks/pre-push`) | allow | **block** | block |

**Why it bit real code.** Adopting a shared token-validation module in `ora-autonomy-gate.py`
(2026-07-17), the first cut imported it with no fallback, reasoning: "a validator we cannot
load cannot validate an override — it raises, the hook errors, and no override is granted."
That reasoning is TRUE for the git hook (any non-zero exit aborts the push) and FALSE for the
PreToolUse hook: an uncaught `ImportError` produces a Python traceback and exit code **1**,
which is non-blocking, so the gated action (a prod deploy, an external send) proceeds. Caught
by adversarial review, reproduced empirically (module removed → exit 1 → deploy allowed, vs
exit 2 pre-refactor). Fixed via `try/except` that degrades to "no override exists" rather than
letting the ImportError propagate — see [[reference-autonomy-gate-override-mechanism]].

**The corollary that also matters:** you cannot fix this by blanket `sys.exit(2)` at import
time either — a PreToolUse hook fires on EVERY tool call in the session, so an import-time
hard block bricks the whole session (the exact shape of
[[feedback_confidentiality_guard_selfdeadlock]]). The only safe pattern for a PreToolUse
guard's import-time failure is: degrade to "nothing is gated / no grant exists," never exit
non-zero from module-load code.

**Applies to:** any hook in `settings.json`'s PreToolUse block, vs. anything invoked from
`.git/hooks/pre-push` (currently `git-prepush-doctrine-gate.py` and
`git-prepush-confidential-scan.py`). Before writing "fail closed" logic in EITHER, check which
family it's in — the two families fail closed in opposite directions.
