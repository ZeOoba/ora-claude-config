---
name: reference_prepush_doctrine_gate_reads_live_checkout_claude_md
description: "The ~/.claude pre-push doctrine gate reads the LIVE checkout's CLAUDE.md, so another session's uncommitted CLAUDE.md bloat blocks YOUR unrelated push"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f74b697f-cc6f-48f6-818b-8de7d95b393e
  modified: 2026-08-14T21:35:57.106Z
---

The `ora-claude-config` (`~/.claude`) pre-push **doctrine gate** (`hooks/git-prepush-doctrine-gate.py` → `maintenance/doctrine-integrity-probe.py`) reads the **LIVE checkout's** `CLAUDE.md` (`~/.claude/CLAUDE.md`), NOT the pushed ref's tree and NOT the pushing worktree's own copy. The gate comment calls this "the real, live checkout this gate ships in."

**Consequence:** another session's *uncommitted* `M CLAUDE.md` in the live checkout — bloat over the 1850-word FAIL budget, or a bare ISO date (violates the dateless rule, [[reference_claude_md_word_budget_is_a_floor]]) — **blocks YOUR unrelated push**, even when you push from an isolated worktree whose own `CLAUDE.md` is clean and even when `origin/main`'s `CLAUDE.md` is clean.

**Diagnosis tell (seen 2026-08-14, OI-052 Opus-floor push):** commit-1 push from a worktree PASSES; a commit-2 push minutes later from the *same* worktree (CLAUDE.md untouched by you) FAILS citing `CLAUDE.md size budget (N > 1850)` + `dated annotation`. That divergence with your tree unchanged = the gate is reading the live checkout, which another session dirtied in between. Confirm with `git -C ~/.claude status --porcelain` → ` M CLAUDE.md`, and check `origin/main` hasn't moved.

**Fix: wait + retry (polling-loop default, [[feedback_polling_claim_loop_default_2026-08-13]]).** It's transient — the other session is blocked by the *same* gate, so it must trim CLAUDE.md back under budget before it can push; your retry then passes (cleared in ~minutes, 2026-08-14). Do NOT edit CLAUDE.md to "fix" it (another session's live WIP + [[config-write-guard]] blocks it anyway) and do NOT mint a gate override for what is someone else's transient drift. Distinct from OI-119 (gate flaky under *load*): this is a *content* block from a concurrent CLAUDE.md edit, not a timeout.
