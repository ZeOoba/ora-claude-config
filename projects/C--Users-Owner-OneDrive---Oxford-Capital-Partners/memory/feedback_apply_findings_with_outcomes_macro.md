---
name: feedback-apply-findings-with-outcomes-macro
description: "Reusable macro for applying a findings list (from /code-review, cc-audit-army, Qodo, or a manual audit) and re-reporting with per-finding outcomes — proven twice, now the default procedure rather than a re-typed prompt."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: efe758ee-6a0d-48c9-9be0-55ad97d0d6e8
  modified: 2026-08-22T17:12:24.457Z
---

**Procedure, not a one-off prompt.** Two independent rounds — a CC-round (oxford-command-center PR review remediation) and an ora-skills-round (`ratify-hurdle-rate`/eval-harness Qodo findings, 2026-08-22) — both used the identical shape: take a findings list, apply or skip each one, then re-invoke `ReportFindings` with `outcome` set per finding (`fixed` / `skipped` / `no_change_needed`). Proven twice is the bar for "this is a procedure, stop re-deriving it" — use this macro verbatim next time rather than re-typing the steps.

**Steps:**
1. **Triage each finding** into fix-now / skip-with-reason / needs-a-follow-up-ticket. A finding that's real but out of scope for this pass is not the same as a finding that's wrong — the former gets an OI-NNN via `allocate-oi-id.py` (never hand-compute the id), the latter gets `outcome: no_change_needed` with the reason inline.
2. **Claim before editing shared checkouts.** Code-review remediation is not exempt from `claim_work.py` — the slug is decided by the touched path (`hooks/**` → `hooks-override-auth`, everything else in `~/.claude` → `repo-housekeeping`, `ora-skills` → `ora-skills-housekeeping`). See [[reference_ora_skills_claim_protocol_pointer_stale_2026-08-14]] for the adjacent gap this closes. Ruled 2026-08-22 after a session skipped claiming during exactly this macro because none of the four slug names read as "about review work."
3. **Apply fixes.** hooks/**, financial, or governor-constant paths go through an isolated worktree + independent review before landing (see `isolated-commit` skill) — never edited live in a contended shared checkout. Verify disjointness (`git status --short -- <path>`) before staging, and stage by exact pathspec (`git add -- <path>`), never `-A`.
4. **Re-report with outcomes.** Call `ReportFindings` again with the SAME findings, each carrying `outcome`. This is what makes the remediation auditable after the fact — a findings list with no outcome pass is a list nobody checked.
5. **Close-out candidates, not silent completion.** Anything surfaced during triage that's a real recurring pattern (not this round's specific bug) is a `knowledge` close-out candidate per CLAUDE.md's autonomy bullet — file it (OI-NNN or a memory note), don't leave it as a comment buried in a skipped finding. This session's own close-out did exactly that: [[open-items-tracker]] OI-204 (governor-constant duplication, 3rd repo) came out of a finding that would otherwise have been silently dropped.

**Why a memory macro, not a new skill:** the four-item vocabulary (`code-review`, `cc-audit-army`, `isolated-commit`, `ReportFindings`'s own `outcome` field) already covers every mechanical step — this procedure is the connective tissue between tools that already exist, not a new capability. A new discoverable SKILL.md would add trigger-collision risk (see `ora-setup-audit`'s whole mandate) for zero new mechanism. If a third proven round needs actual new tooling (e.g. a script that mechanically re-derives `outcome` from a diff), promote this to a real skill then — not before.
