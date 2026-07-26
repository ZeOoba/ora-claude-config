---
name: git-commit-parse-review-risk
description: "hooks/lib/git_commit_parse.py (shared git-commit tokenizer + pathspec resolver behind commit-provenance-guard.py and eos-review-gate.py) has repeatedly needed multiple adversarial review rounds to converge -- budget for that on any future edit, don't expect one pass to suffice."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 514f0995-d7f9-40f3-84fa-c1726b3461b1
  modified: 2026-07-26T21:56:25.770Z
---

`hooks/lib/git_commit_parse.py` is a hand-rolled shell tokenizer + git-pathspec resolver shared by `commit-provenance-guard.py` and `eos-review-gate.py`. It has a track record of taking **multiple independent adversarial review rounds to converge, each finding a genuinely new class of defect**, not variations on one already-found theme:

- **2026-07-26 heredoc-tokenizer fix** (`tokenize_cmd_segments`): 5 documented rounds in one session (see the function's own docstring in the file) before landing — round 1 the original bug, round 2 a fix that converted it into an opposite-direction bug (false-allow) with O(n^2) blowup, round 3 closed that but left two new gaps, rounds 4-5 each found further edge-case misreadings of bash's actual heredoc-terminator/quote rules.
- **2026-07-26 `pathspec_arg_paths` fix** (directory/glob/pathspec-magic expansion, added to close a content-independent-review-key hole): round 1 of adversarial review found the CRITICAL defect (a directory pathspec collapsed to a constant digest) and a HIGH sibling (`git commit -- .` silently un-gated). The FIX for round 1 was itself adversarially re-reviewed in round 2, which found the fix's own predicate still left FOUR more bypass shapes open (`'*'`, `:(top)`, `:(glob)...`, `:(icase)...`) plus a missing untracked-files case — i.e. even the *remediation* needed its own adversarial pass before it actually closed what it claimed to close.

**Why:** this module's job is answering "what would `git commit` actually capture" from a Bash command string, before the command runs — a genuinely hard, high-surface-area problem (shell quoting, heredocs, git pathspec magic, compound commands) sitting directly behind two security-enforcement gates. The failure mode on a miss is *silent* (an under-resolved candidate set just means the gate sees less than it should, no error, no traceback) — the opposite of a loud crash, which is what makes bugs here hard to catch with ordinary testing and easy to under-review.

**How to apply:** any future edit to this file (or to `commit-provenance-guard.py`/`eos-review-gate.py`'s own pathspec/tokenization logic) should be planned assuming it will need **2+ independent adversarial review rounds**, not one. Don't declare done after a single REFUTE pass reports "SHIP AS-IS" if the diff touches this file's core resolution logic — re-review the FIX itself, not just the original defect. This matches [[feedback_refute_pass_proactive_default]]'s general rule but is a stronger, module-specific instance of it: budget the extra round into the plan up front rather than being surprised by it.
