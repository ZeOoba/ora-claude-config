---
name: project-primary-checkout-main-move-blocked-2026-08-12
description: "Primary ~/.claude checkout stays on feat/model-canary-probe-step25, not main -- 117 uncommitted files span 15+ sessions' live WIP, so the move was ruled out as an isolated-worktree job instead of a branch switch on the shared checkout"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2fb76021-f614-4123-8063-7d2937ad137b
  modified: 2026-08-12T20:56:57.782Z
---

Primary checkout (`C:/Users/Owner/.claude`) is on `feat/model-canary-probe-step25` @ e574bdf, 19 ahead / 48 behind `origin/main`, with 117 uncommitted files. Local `main` is 9e6c00a, 4 ahead / 0 behind `origin/main`; `worktrees/_push-main-tmp` already holds `main` cleanly at that commit. A relayed handoff (session `08df9f95`, 2026-08-12 ~16:3x) asked for the primary checkout to be force-moved onto `main` so PRs #51 (confidentiality-test worktree fallback) and #55 (gate fail-retry) take effect for it. Its git-state facts were independently verified and were accurate.

What the handoff did NOT flag: the 117 uncommitted files are not stale/unowned. A `config-write-guard` write attempt (claiming `repo-housekeeping` to do the move) surfaced that 15+ sessions have recorded edits inside that dirty set (08df9f95, 1de11c79, 45979807, +12 more). Gabriel, given this, chose "isolated worktree only" over force-claiming and switching the shared checkout — the primary checkout was left untouched.

**Why:** a branch switch or reconciliation on a working tree with 15+ sessions' live hunks intermingled is the "contaminated tree" case the single-writer doctrine (`CLAUDE.md` Engineering OS) exists to prevent — never checkout/reset/rebase it directly.

**How to apply:** don't re-attempt moving the primary checkout onto `main` by switching branches there. If PR #51/#55 need to take effect somewhere, do it in a fresh worktree checked out at `main` (`_push-main-tmp` already is one). The primary checkout only resolves onto `main` once the 15+ sessions with WIP in that dirty set have committed/reconciled their own hunks — that has to happen session-by-session, not as a single housekeeping action. Re-verify the dirty-file-ownership breadth (not just the file count) before trusting any future relayed claim that this checkout is safe to move. Related: [Shared-checkout single-writer rule](reference_concurrent_session_duplicate_hardening_work.md), [[reference_git_hazards_isolated_hunk_recipe]] if it exists.
