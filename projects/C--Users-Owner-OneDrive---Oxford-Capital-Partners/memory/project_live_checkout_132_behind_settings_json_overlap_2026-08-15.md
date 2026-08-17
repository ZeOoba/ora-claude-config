---
name: project-live-checkout-132-behind-settings-json-overlap
description: "SUPERSEDED 2026-08-16 (gap closed, now behind 4; kept for the settings.json conflict-class lesson) -- Live ~/.claude checkout is 132 commits behind origin/feat/model-canary-probe-step25 (PR #106 + #109 merged, not yet pulled); its current dirty set collides with session 39572813's active repo-housekeeping claim on the same files."
metadata: 
  node_type: memory
  type: project
  originSessionId: 71202c4a-c638-4821-95ea-6b6a43606cdf
  modified: 2026-08-16T18:02:42.111Z
---

**Fact:** as of 2026-08-15, the live `~/.claude` checkout is on `feat/model-canary-probe-step25` at `4db11a0`, **132 commits behind** `origin/feat/model-canary-probe-step25`. That remote tip includes [PR #106](https://github.com/ZeOoba/ora-claude-config/pull/106) (the full main-merge reconciliation — 12 files, verified conflict resolution) and [PR #109](https://github.com/ZeOoba/ora-claude-config/pull/109) (OI-111 reconciliation), both merged 2026-08-15. Neither is live in the checkout that hooks/scripts actually execute from.

The checkout's current dirty set at discovery time:
- `settings.json` (M)
- `projects/.../memory/MEMORY.md` (M)
- `projects/.../memory/event_log.md` (M)
- `maintenance/doctrine-integrity-probe.py` (M)
- `projects/.../memory/project_automation_audit_rev10_2026-08-14.md` (??, untracked)

This matches session `39572813`'s active `repo-housekeeping` claim, opened the same day, described as "Dirty-tree triage continuation: post-Rev10-remediation cleanup (backup mirror sync, maintenance state refresh, MEMORY.md/event_log.md, settings.json, rev10 memo/task spec)."

**Why this matters:** a pull/merge to close the 132-commit gap will land on top of whatever that session commits, and `settings.json` specifically carries real risk — the PR #106 merge resolved a genuine hooks-array conflict there (two unrelated hook entries, `lint-config-guard.py`/`workbook-write-guard.py` and `commit-hygiene-guard.py`/`scheduled-task-update-preguard.py`, that had landed at the same array position on each branch; both pairs were kept, verified against `json.load()` before staging). If session `39572813`'s local `settings.json` edit predates that merge, a pull is likely to reopen that same conflict class. `doctrine-integrity-probe.py`'s upstream change came from a verified real bug fix (a `check_stage_exclusion_sync` addition, tested), not mere staleness — worth knowing before assuming a stale-vs-mine diff is safe to blindly discard either way.

**How to apply:** whoever advances this checkout next (most likely session `39572813` finishing its claimed cleanup, or Gabriel directly) should fetch and reconcile the full 132-commit gap as part of that pass, not treat it as a quick fast-forward once their own dirty files are committed. Attempted delivery via `send_message` to that session directly (`local_78c6dc2f-4a0c-401b-8322-cd14993e40c8`) — blocked, this session is unattended (originated as the `ora-deal-command-board` scheduled task) and cannot send cross-session messages. This file is the fallback record per Gabriel's direction (2026-08-15, in-turn).

**Deliberately not done:** no `MEMORY.md` index pointer added yet — `MEMORY.md` is itself one of the contested dirty files in the live checkout (see list above), so editing it now would create exactly the collision this note exists to flag. Add the index entry once session `39572813`'s edit to `MEMORY.md` has landed or cleared.

Related: [[project_primary_checkout_main_move_blocked_2026-08-12]] (a prior instance of the same class of problem — a live checkout unable to advance because of dirty-tree/branch-position issues).

**UPDATE 2026-08-16 — SUPERSEDED; the gap is closed.** Re-measured today via `git rev-list --left-right --count`: the live checkout is **behind 4**, not 132, of `origin/feat/model-canary-probe-step25`. PRs #106/#109 — and since then #118/#119/#120 — are merged and pulled. The `settings.json` conflict this note flagged never came due: `settings.json` is no longer in the live dirty set at all. **Keep** the general lesson (a large behind-count gets reconciled by whoever advances the checkout, never by a blind fast-forward, and an upstream probe change can be a real bug fix rather than staleness). **Discard** the 132 figure and the session-`39572813` collision framing as point-in-time. The "deliberately not done" MEMORY.md pointer was in fact added later and is live in the index.
