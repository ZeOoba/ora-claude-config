---
name: project-workflow-optimizations-2026-08-21-resolution
description: "Outcome of the 5-item 2026-08-21 workflow-optimizations punch list -- 1 already fixed by another session (discard), 1 shipped on a branch awaiting merge, 1 scoped not fixed, 2 resolved as memory/investigation only."
metadata: 
  node_type: memory
  type: project
  originSessionId: ebb79ea0-b175-4704-a8be-c1b84203d48e
  modified: 2026-08-21T22:21:37.515Z
---

Disposition of the 5 items:

1. **governor-drift-probe known-triaged-failure allowlist** -- NOT BUILT. The specific FP driving
   it (acquisition-buy-box-v1.md:31, ratified per-property 65% LTV refi ceiling) was already
   fixed properly by another concurrent session via commit `c7875a5` ("stop flagging the
   ratified per-property refi-sizing 65% LTV ceiling"), landed on `main` before this session's
   allowlist implementation was committed. A generic allowlist mechanism was drafted and fully
   tested but discarded as redundant infrastructure for an already-closed problem -- this
   codebase's own established pattern (a precise regex suppressor per FP, not a bypass list) is
   architecturally preferable and is what landed. Caught only because a routine "already-done"
   check (`git log -- maintenance/governor-drift-probe.py`) was run before committing.

2. **eos-plan-gate structured-prompt recognition** -- SHIPPED, awaiting merge. Branch
   `fix/hooks-workflow-opts-2026-08-21` (worktree `.claude/worktrees/hooks-workflow-opts`,
   commit `c4d71e2`) adds `_written_plan_evidence`/`_approve_plan_from_prompt` to
   `hooks/engineering-router.py`: a prompt containing >=2 distinct "Phase N"/"Stage N" headers
   now writes the same permanent plan-approved marker `/plan` itself writes, closing the gap
   where the existing budget-reset mechanism can only fire on a follow-up turn (a plan stated
   and executed within one turn never gets one). Full test suite green
   (`test-engineering-router.py` +6 cases including a true end-to-end round-trip through
   `eos-plan-gate.py`; `test-eos-plan-gate.py`/`test-eos-plan-marker.py` unaffected). Needs
   Gabriel's review/merge per the config-write-guard live-edit gate on `hooks/**` -- this is
   governance code.

3. **commit-hygiene-guard.py / git_commit_parse.py tokenizer consolidation** -- CONFIRMED real,
   filed not fixed: [[project_commit_hygiene_guard_tokenizer_consolidation_gap_2026-08-21]].
   Refactoring adversarially-hardened security-gate code without matching TDD/REFUTE rigor
   would be reckless under this session's time budget.

4. **`/tmp` + heredoc commit-message unreliability** -- captured as
   [[feedback_commit_message_via_write_tool_not_heredoc]]. No code change; a working-practice
   lesson.

5. **ora-skills "auto-push on commit" hook** -- INVESTIGATED, premise did not hold. `ora-skills`
   has `core.hooksPath=tools/hooks` wired to a real `post-commit` hook, but it only runs
   `tools/pending_reimport.py record` (PENDING-REIMPORT ledger) and
   `tools/sync_local_skills_mirror.py` (local Code-surface mirror sync) -- neither touches the
   remote. No hook anywhere in the repo runs `git push`. Whatever push the punch-list item
   observed was an explicit command (its own or an earlier one), not hidden automation; no
   action needed.

Two incidental process lessons surfaced while doing this work, both filed standalone:
[[reference_worktree_wrong_base_branch_2026-08-21]] (worktree creation branched from another
session's live feature branch, not main, because no explicit base ref was given) and
[[feedback_commit_message_via_write_tool_not_heredoc]] (item 4, above).
