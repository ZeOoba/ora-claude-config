---
name: reference-commit-provenance-guard
description: "New hooks 2026-07-16: commit-provenance-guard.py + commit-provenance-recorder.py block a git commit that would sweep another live session's uncommitted work. Hit BLOCKED? use a pathspec or the override sentinel."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 0888c827-119f-4877-98ae-23ac7c404a27
---

**What it is:** two cooperating hooks, live in `~/.claude` since 2026-07-16 (registered in
`settings.json`, rostered in `CLAUDE.md`'s `Guards:` line). `commit-provenance-recorder.py`
(PostToolUse) appends every file this session Edits/Writes to
`hooks/sessions/<sid>/touched-files.txt`. `commit-provenance-guard.py` (PreToolUse/Bash) blocks a
`git commit` only when a file it would capture appears in ANOTHER session's touched-set AND
`session_liveness` affirmatively reports that session open AND the set is within a 6h TTL — two
affirmative signals required, so it fails open on any missing/stale/unreadable information. No
lock is ever held; it is not a mutex.

**Why it exists:** one 2026-07-16 session hit 4 concurrency collisions in an hour in this same
shared checkout — 3 were Bash `git commit`/`git push`, invisible to the pre-existing
`shared-checkout-guard.py` (which only watches Edit/Write). Worst case: a staged MEMORY.md edit
got swept into another session's commit inside a ~30s window between `git add` and `git commit`.
Full incident + rejected alternatives:
`~/.claude/docs/superpowers/specs/2026-07-16-commit-provenance-guard-design.md`. The design
choice itself (fail-open + two-signal over a hard claim-lock) was Gabriel-ratified — see
[[feedback_fail_open_over_mutex_for_fleet_gates]].

**If you hit `BLOCKED (commit-provenance-guard)`:** the message names the file and the owning
session. Two ways forward, both stated in the block message itself: (1)
`git commit -m "..." -- <your files only>` — an explicit pathspec genuinely narrows what gets
captured (tested, not assumed); (2) if DELIBERATELY landing another session's orphaned work (the
"land the backlog" janitor pattern, e.g. commits `c0272bb`/`4da5d26` from 2026-07-16),
`touch hooks/sessions/<your-sid>/allow-foreign-commit`.

**⚠ Pathspec safety has a scope condition (2026-07-17 near-miss).** "Use a pathspec" is safe when
it names a WHOLE FILE that is entirely your own content (e.g. `-- mine.txt` where `theirs.txt` is
a different file — the guard's own test suite validates exactly this). It is UNSAFE when the
flagged file is one you only want to commit a PARTIAL, isolated patch from (e.g. `event_log.md`
with several sessions' entries stacked in one uncommitted diff): `git commit -- <path>` silently
re-adds the FULL WORKING-TREE version of that path before committing, overriding whatever you
staged with `git apply --cached`. A bare `git commit` (no pathspec at all) commits exactly the
staged index instead — that is the correct move once you have isolated a partial hunk. Full
technique + the incident this was caught in: [[reference_event_log_uncommitted_backlog]].

**Known gap:** only catches files touched via the Edit/Write tools or the Desktop Commander write
aliases — a foreign file written by a Bash script/heredoc is invisible to the recorder and will
NOT be caught. Accepted trade-off: a "block anything I didn't touch" design was rejected because
it would have blocked legitimate script-generated commits (e.g. the `event_log.md` rollover).

Related: [[reference_hook_systemmessage_not_model_visible]] (same-day sibling fix — made
`shared-checkout-guard.py`'s warning actually reach the model) ·
[[shared-checkout-cofile-patch-hazard]] · [[project_tenant_db_no_sync_rootcause]] (the session
that produced this).
