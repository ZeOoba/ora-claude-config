---
name: project-orphan-guard-timing-2026-07-24
description: "CLOSED 2026-08-05 (re-verified on main: shlex whole-command tokenization present, raw-string _has_pathspec decoy check removed, 79/79 tests pass). History below is retained: this was REOPENED 2026-07-24 when a SECOND bypass (decoy ' -- ' inside an ordinary -m message) landed 1687fbc 13 min after the first 'CLOSED' fix, orphaning 2 links."
metadata: 
  node_type: memory
  type: project
  originSessionId: d6635568-ae53-453c-9bd7-ec8551f96c73
  modified: 2026-08-05T20:01:30.005Z
---

**CLOSED 2026-08-05.** Re-verified directly against `main`, not inferred: the fix
this file described as "uncommitted WIP on fix/orphan-guard-pathspec-exclusivity"
did land. `hooks/memory-orphan-link-guard.py` imports `shlex` and tokenizes the
WHOLE command once via `shlex.shlex(cmd, posix=True, punctuation_chars=True)`
(not `shlex.split`, not pre-split by line); the second, independent raw-string
`_has_pathspec(cmd)` scanner was removed. **79/79 tests pass** — this file's
"52/52" was the pre-merge branch count. That branch no longer exists locally.

Anyone reading the description before 2026-08-05 would have concluded a live
bypass was still open. It was not. Re-check ground truth before acting on a
memory entry that names a branch.

---

**REOPENED 2026-07-24, ~13:56 (historical).** This file originally read "CLOSED" after the
compound-command bypass fix below (landed 12:54). That fix was real and is not in
question. But `1687fbc` (13:07 — 13 minutes *after* the "CLOSED" fix was deployed)
still landed 2 orphaned index links, proving a distinct hole survived.

**The second bypass:** `_has_pathspec(cmd)` used `re.search(r"\s--\s", cmd)` against
the raw Bash command string — including the `-m` message text. A commit message
containing an ordinary standalone " -- " (`1687fbc`'s own message has three) makes
the guard misread a plain staged commit as a pathspec commit, so it validates the
WORKING TREE instead of the INDEX. If the working tree had since reverted to a clean
MEMORY.md while the orphaned version stayed staged (real git commits the index here,
not the tree), the guard sees clean content and ALLOWs — the orphan lands unchecked.
Confirmed live via an isolated harness (throwaway repo + `ORA_MEMORY_INDEX`, positive
control verified — first pass falsely read the guard's stdout-JSON DENY as an
exit-code ALLOW; corrected before trusting the result).

**Status as of 2026-07-24 13:56:** a fix already exists — `bb02f5e` /
`475d360` on worktree `fix-orphan-guard-pathspec` (branch
`fix/orphan-guard-pathspec-exclusivity`), replacing the raw-string `_has_pathspec`
regex with a `shlex`-tokenized, option-aware pathspec scan (`_commit_pathspec`), so a
`--` embedded inside a quoted `-m` argument is no longer visible as a standalone
token. That branch's own test suite (`hooks/tests/test-memory-orphan-link-guard.py`,
52/52 passing) includes this exact scenario verbatim (line ~392: "staged=orphan,
worktree=clean, decoy ' -- ' in message, plain commit -> DENY") and passes. As of
this edit the branch carries further uncommitted WIP on top of `475d360` (mtimes
~13:52–13:53) — still an active session, not yet merged to `main`. Do not duplicate
this fix; if picking this up later, check whether that branch has since merged
before starting fresh.

## Original entry (12:54 fix — real, but not the whole story)

Started as "document an annoying false positive", ended as a
security-gate fix.

## What was wrong

`memory-orphan-link-guard.py` decided whether MEMORY.md was part of a commit by reading
`git diff --cached` — but it is a **PreToolUse** hook, so that read happens *before* the
command runs. For a compound command the index it inspected was the pre-command one:

* **False positive** (what surfaced it): `git restore --staged MEMORY.md && git commit`
  — staged at hook time, so a commit that would not have included MEMORY.md was blocked.
* **BYPASS** (the real defect): `git add MEMORY.md && git commit` — unstaged at hook
  time, so the guard returned "not our business" and the orphan links landed unchecked.
  Reachable by the most natural way anyone commits.

General lesson: [[pretooluse-evaluates-pre-command-state]].

## Fix

Walk the command's segments in order and simulate whether MEMORY.md ends up in the commit
— `git add` (explicit path, `-A`/`--all`, `-u`/`--update`, `.`), `git restore --staged`,
`git reset`, and `git commit -a/--all` (which re-stages what an earlier segment just
unstaged). Content is read from the working tree when the command stages it, from the
index otherwise. Errs toward INCLUDED: a wrong "included" costs a block a human can
inspect; a wrong "excluded" silently lands the orphan.

Plus a HEAD-identical short-circuit so `git add -A` on an unmodified MEMORY.md cannot
deadlock on pre-existing HEAD orphans, and one shared git-invocation parser
(`_segment_git_parts`) instead of two.

**Test-harness bug fixed in passing:** `GUARD` was hardcoded to the absolute *live* path,
so a worktree run silently exercised the deployed guard rather than the copy under test —
the same class as `setup-self-audit`'s lib path, fixed earlier the same day.

## Verification

34/34 tests (11 new, written red first). REFUTE pass clean on four attacks: 12 bypass
variants outside the suite (`--all`, `--update`, `;` separators, `git -C`, absolute git
path, `--amend`, `git commit --all`, bare basename, `./`-prefixed) all DENY; the
false-positive narrowing opened no hole (unstage-then-re-add and unstage-then-`commit -a`
still DENY); the short-circuit does not swallow a real orphan; no scope creep.

Confirmed against the **deployed** guard on the real repo: every bypass variant DENY,
plain commit and unrelated-path commit ALLOW.

Landed via worktree → review → merge, per config-write-guard's prescribed path for
`hooks/**` — no blanket write token was minted.
