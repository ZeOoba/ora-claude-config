---
name: project-orphan-guard-timing-2026-07-24
description: "CLOSED 2026-07-24 — investigating a memory-orphan-link-guard false positive uncovered a straight bypass underneath it; both fixed, merged, verified against the deployed guard."
metadata: 
  node_type: memory
  type: project
  originSessionId: d6635568-ae53-453c-9bd7-ec8551f96c73
  modified: 2026-07-24T17:01:07.456Z
---

**CLOSED 2026-07-24.** Started as "document an annoying false positive", ended as a
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
