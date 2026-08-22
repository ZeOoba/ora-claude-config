---
name: project-commit-hygiene-guard-tokenizer-consolidation-gap-2026-08-21
description: "commit-hygiene-guard.py carries its own ~150-line git-command tokenizer, parallel to and overlapping with hooks/lib/git_commit_parse.py (which was extracted specifically so commit-provenance-guard.py and eos-review-gate.py would not diverge) -- confirmed real, deliberately NOT fixed live this session; scoped here for a dedicated future pass."
metadata: 
  node_type: memory
  type: project
  originSessionId: ebb79ea0-b175-4704-a8be-c1b84203d48e
  modified: 2026-08-21T22:21:15.578Z
---

`hooks/commit-hygiene-guard.py` (warn-only, PreToolUse/Bash) implements its own segment
tokenizer (`_segments`/`_tokens`/`_strip_prefixes`/`_git_subcommand`/`_cluster_stages_all`,
~150 lines) rather than reusing `hooks/lib/git_commit_parse.py`'s `tokenize_cmd_segments`/
`_segment_git_subcommand_and_args`/`has_all_flag` -- the module `git_commit_parse.py` exists
specifically to prevent exactly this: its own docstring records that its two current
consumers (`commit-provenance-guard.py`, which BLOCKS, and `eos-review-gate.py`, which BLOCKS)
were "two inline copies of one security contract, written hours apart by two sessions, and had
already begun to diverge before either was reviewed."

commit-hygiene-guard.py's docstring gives an explicit reason for NOT sharing the module's full
adversarial-tearing defence (heredoc-aware parsing, multi-round REFUTE hardening): it only ever
PRINTS an advisory, never blocks, so a fooled parser costs a wrong/missing advisory line, not a
bypassed gate -- a materially lower stakes failure mode than the two BLOCKING consumers. That
reasoning is sound for why it doesn't need `git_commit_parse.py`'s FULL hardening, but does not
establish that it can't reuse the underlying tokenizer at all -- `tokenize_cmd_segments` would
only ever make commit-hygiene-guard.py MORE robust (free heredoc handling), never less, since
it's a pure segmentation function with no blocking side effect.

**Why this is filed, not fixed:** `git_commit_parse.py` is 800 lines with 5 documented ROUNDS
of REFUTE-hardening on its heredoc-recognition alone; `commit-hygiene-guard.py` is 600 lines
with its own hard-won fixes (branch-identity Gap A, memory-stamp Gap B, both from a real 2026-08-09
incident). Refactoring commit-hygiene-guard.py to consume git_commit_parse.py's tokenizer
without the SAME TDD/REFUTE rigor this codebase applies to every other change on these two
files would be reckless -- consolidating under time pressure is exactly the failure mode
CLAUDE.md's "financial code needs upfront load derivation" / REFUTE-pass doctrine exists to
prevent. Confirmed real via direct read of both files 2026-08-21; not attempted live.

**Scope for the future pass:** (1) verify git_commit_parse.py's `analyze()`-equivalent (repo
resolution via `cd`-segment tracking + `-C`, `stages_all`, pathspec extraction) can be built
from its exported functions without behavior drift from commit-hygiene-guard.py's own
`analyze()`; (2) full regression run of both test suites (`test-commit-hygiene-guard.py`,
`test-commit-provenance-guard.py`, `test-eos-review-gate.py`) before and after; (3) do the work
in an isolated worktree per [[reference_worktree_wrong_base_branch_2026-08-21]], with an
explicit base ref.
