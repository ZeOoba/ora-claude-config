---
name: feedback-recheck-before-reflagging-tooling-gaps
description: "Before repeating a 'known tooling gap / workaround needed' note in a scheduled-task report, re-check current repo state and memory first -- another session may have already fixed it."
metadata:
  type: feedback
  originSessionId: b7e63012-b27f-4f9c-8c01-825d6883246a
  modified: 2026-07-22T22:04:06.157Z
---

**What happened (2026-07-13/22 session):** `ora-financial-code-integrity-sweep` hit the
`Workflow({scriptPath})` CRLF control-character rejection on
`oxford-command-center/.claude/workflows/refute-financial-change.js`, worked around it
with an LF-normalized scratchpad copy, and flagged it in both the Notion completion
row and the defect email as an open tooling issue that "will recur every run until
the repo file is converted to LF." When Gabriel asked to fix it, direct verification
showed a *different* session had already fixed it on 2026-07-21 -- `.gitattributes`
now forces `.claude/workflows/*.js text eol=lf`, and the committed file has zero `\r`
bytes -- documented in [[reference_workflow_scriptpath_crlf_rejection]]. No code
change was actually needed; the flag itself was stale.

**Why:** a scheduled task is a fresh session every run with no memory of prior runs
except what's written to Notion/memory. It's easy to re-diagnose a symptom from
scratch and report it as newly-open when another session (fleet task or ad hoc) has
already closed it -- especially for tooling/environment gaps that live outside the
task's own read-only scope (this sweep is explicitly forbidden from touching the repo
itself, so it can only ever *propose* the fix, never confirm it landed).

**How to apply:** before writing a "tooling note" / "known gap" / "needs a separate
fix" line into any completion row, email, or report -- especially on a recurring
scheduled task -- spend one cheap check first:
1. Grep `MEMORY.md` and the relevant `reference_*`/`feedback_*` files for the
   symptom (error string, filename, tool name).
2. If the gap lives in a repo, check current state directly (`git log -1` on the
   affected file, `.gitattributes`, or a live grep for the specific broken
   condition) rather than trusting the workaround note from the run that first hit it.
3. Only carry the note forward if the check confirms it's still open. If fixed,
   drop it silently or note it as resolved -- don't repeat stale diagnosis by habit.

This generalizes the same discipline as [[feedback_verify_before_repeating_session_claims]]
and the verify-first cluster in `MEMORY.md`, applied specifically to a scheduled
task's own carried-forward "known issue" notes, not just another session's claims.
