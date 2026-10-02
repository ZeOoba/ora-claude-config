---
name: reference_worktrees_freeze_stale_memory
description: "Memory files are git-tracked, so every ~/.claude worktree carries a frozen snapshot of memory. A session working in a stale worktree recalls withdrawn facts as current — the `description:` line is what recall surfaces, and it carries no staleness signal. Found 2026-09-18."
metadata:
  node_type: memory
  type: reference
  originSessionId: 94d37710-d72c-4c25-9000-53907e7e35d9
  modified: 2026-09-18
---

`~/.claude/projects/.../memory/` is inside the git repo, so **every worktree under
`~/.claude/.claude/worktrees/` holds its own frozen copy of every memory file, pinned at whatever
commit that branch was cut from.** A session running in a worktree recalls *that* copy, not main's.

**Confirmed 2026-09-18.** Gabriel reported `reference_hubspot_lease_renewal_pipeline_stalled_2026-08-23.md`
as saying "43 stuck" when main's copy had carried the corrected 37 open / 5 won / 8 lost since
2026-09-02. Both were true. Of 14 worktree copies of that file, 13 were current and one —
`fix/fleet-status-never-ran-first-slot`, **163 commits behind main** — still carried the
pre-correction text. The correction landed on main in `e13d87d` (an automated memory sync
checkpoint), which is not an ancestor of that branch. The file was clean in that worktree: nobody
edited it, it simply never caught up. That is why "I did not edit it" and "it says 43" were both
accurate.

**Why this is worse than ordinary staleness:** the withdrawn number lived in the **`description:`
frontmatter field**, which is the line recall uses to decide relevance and the line that gets
surfaced. So the stale worktree does not merely hold an old body — it advertises a withdrawn fact
as the file's headline, with nothing marking it stale. The corrected copy on main had explicitly
removed the count anchor and said "never cite a count from this file"; the stale copy said the
opposite, confidently.

**How to apply:**
- Do not answer "is this memory current?" from the copy in front of you. Check which checkout you
  are in, and how far behind main it is (`git rev-list --count HEAD..main`).
- When a memory file's claim is disputed, search **all** worktrees, not just the live tree, and
  diff them. A single `find`/`grep` scoped to `~/.claude/projects` will miss every worktree copy
  and produce a confident "only one copy exists, and it's current." That exact wrong claim was made
  in this session before the wider search returned.
- Reading `~/.claude` with git commands trips `config-write-guard` (write-shaped matcher). Run the
  same query with `git -C <a worktree path>` — worktree paths are exempt and share the object
  database, so `log`, `merge-base` and `rev-list` all resolve identically. Do not mint an override
  token for a read.
- The standing remedy for a far-behind worktree is merge-forward (`ora-checkout-merge-forward`,
  `45 16 * * *`), not hand-patching one file into someone else's branch.

Sibling of [[feedback_verify_freshness_before_acting]] and
[[feedback_verify_negative_glob_results]] — this is the specific shape where the negative result
("no other copy") is wrong because the search root was too narrow. See also
[[reference_memory_scope_fragmentation]].
