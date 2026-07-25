---
name: project-eos-review-gate-shipped-2026-07-24
description: "eos-review-gate.py shipped 2026-07-24 (commit c53c69c) -- blocking independent-review gate for blast-radius/financial-decision commits; 4 review rounds, 3 real defects caught and fixed"
metadata:
  node_type: memory
  type: project
  originSessionId: 7a4a4780-8a9c-48c2-839a-f10e60f49524
  modified: 2026-07-24T18:28:37.742Z
---

**Built and merged 2026-07-24**, ratified per [[feedback-auto-review-blast-radius-gate]].
`hooks/eos-review-gate.py` blocks `git commit` on CLAUDE.md's risk list
(`hooks/**`, `*.env*`, `*credentials*`, `confidential-terms.json`,
`settings.json`, `CLAUDE.md`/`~/.claude` config, scheduled-task registries,
CSP/headers, financial-decision/governor code) unless a review artifact is
keyed to the exact content under review. CLI: `--key` / `--record`. Same
override-token escape hatch as `eos-plan-gate.py`; `EOS_REVIEW_GATE_MODE=warn|off`
for staged rollout.

**Why this took 4 review rounds, not 1** — the process worked exactly as
intended: the gate caught real defects in itself before shipping.
- Round 1 (full review): BLOCKING, 8 confirmed PoCs. Major ones: content key
  hashed working-tree bytes even when the commit would actually land the
  INDEX (M1); a `--` in a *different* chained command hijacked the pathspec
  (M2); the fleet's own `git add <untracked> && git commit` shape was
  blockable but unsatisfiable via `--record` (M3); `src/hooks/useX.ts`
  (React) falsely flagged as this repo's `hooks/**` (M4).
- Round 2 (fresh full pass on the fixes): BLOCKING — the M1 fix itself
  introduced **B1**, a case-sensitivity bug: `git show :path` matches
  literally even under `core.ignorecase=true`, so `CLAUDE.md` (the flagship
  risk file) silently missed and fell back to the exact behavior M1 existed
  to close. Same bug class `commit-provenance-guard.py` already hit and fixed
  2026-07-20 (`:(literal,icase)`).
- Round 3: independent re-verification, APPROVED WITH MINOR NOTES.
- Round 4 — **B2, found live during the actual merge attempt, not by any
  review round's test repos**: this machine runs `core.autocrlf=true`, and
  hashing raw disk bytes for the working-tree digest vs. git's LF-normalized
  index blob for the staged digest meant the two digests differed for
  **every text file**, regardless of real content divergence — permanently
  unsatisfiable via `--record` for a common commit shape. No test fixture
  ever round-tripped a file through a real `git checkout`, so autocrlf never
  fired in any of them. Full detail: [[reference-autocrlf-defeats-content-hash-gates]].

**Shared-checkout collision hit mid-merge** (not a bug in the gate itself):
an earlier `git merge --no-commit --no-ff` left staged mid-review; another
live session's ordinary commit landed in the meantime and silently became a
2-parent merge commit (picked up the stale `MERGE_HEAD`) whose tree never
actually included the staged content — poisoning the merge-base for any
subsequent real `git merge` of the branch. Recovered by verifying no other
session had touched the target files, then applying the branch's exact
content directly via `git checkout <branch> -- <paths>` and committing
single-parent instead of merging. Full detail:
[[reference-stale-merge-head-poisons-graph]].

**Operational near-miss**: cleaning up test state with `git clean -fd` in the
live checkout deleted the (untracked) `hooks/eos-review-gate.py` while the
session's hook engine still held a stale reference to it — every subsequent
Bash call in-session failed to launch until the file was restored. Recovered
via Gabriel's explicit in-turn confirmation + an `allow-config-write` token
(narrow, single-purpose restore, not a new edit). Lesson: `git clean -fd` in
`~/.claude` is riskier than it looks when a file just got wired into the live
hook config — the harness's hook list can go stale relative to disk within a
single session.

**How to apply:** when building a SECOND commit-time gate (anything else that
needs to inspect `git commit` diffs), reuse `hooks/lib/git_commit_parse.py`
rather than re-deriving the tokenizer — it already carries every fix listed
above plus `commit-provenance-guard.py`'s own history. If it ever needs a
content-hash digest of a file, use git's own blob object-id
(`git hash-object` / `git rev-parse :path`), never a raw
`sha256(open(path,"rb").read())` — see
[[reference-autocrlf-defeats-content-hash-gates]] for why.
