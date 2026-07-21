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

**⚠ 2026-07-20 — `already_committed_since()` never fires on Windows; two stacked bugs defeat
both the TTL and the recency fix. CLOSED same day.** Hit a block committing `open-items-tracker.md`
attributed to session `15ec64e8` as "working," even though: (a) that session's *only* touches to
this exact path were six entries clustered 2026-07-17 23:03–23:15, three days stale, and (b) the
path had already been safely committed since (`db5a8d4`, 2026-07-19 21:45:23 — newer than every
one of those touches). The documented `already_committed_since()` fix (2026-07-17, same file)
should have suppressed this outright. Root-caused empirically, not by reading the code alone:
1. **`commit-provenance-guard.py:145-154` (`last_commit_time`) — the real defect.** It ran
   `git log -1 --format=%ct -- <abs_path>` against the `norm()`-ed (normcase'd — lowercase,
   backslash) absolute path pulled straight from `touched-files.txt`. On this Windows checkout that
   query silently returned **empty stdout, rc 0** — no error, just no match — for a path git can find
   fine as a repo-relative forward-slash pathspec (verified side-by-side: the normcased absolute
   form returned nothing; the plain relative form returned the correct `%ct` immediately). Follow-up
   root-causing (not just "backslash vs forward-slash," per the original hypothesis) isolated the
   real mechanism: git's pathspec match against history is **literal, independent of
   `core.ignorecase`** — a fully-lowercased pathspec matches only paths whose real on-disk casing is
   already all-lowercase. Every fixture filename in the guard's own test suite happened to be
   lowercase (`shared.txt`, `theirs.txt`, ...), so `normcase()` was a no-op there and the bug never
   surfaced in tests — only against real repo paths with mixed-case components (`CLAUDE.md`,
   `OneDrive`, `Oxford-Capital-Partners`, ...). So `already_committed_since()` read "never committed"
   for files that plainly had been, and always returned `False` on this OS — the 2026-07-17 recency
   fix was dead code in practice here, not just for this one file.
2. **`commit-provenance-guard.py:249` — a compounding TTL bug.** The per-session TTL cutoff checked
   `os.path.getmtime(<the whole touched-files.txt file>)`, not the timestamp of the specific entry
   being evaluated. A long-lived session that keeps touching *anything* keeps its entire touched-set
   file "fresh" indefinitely — so a 3-day-stale entry for one path never aged out on its own as long
   as the owning session was still active on other files. This TTL was effectively per-session-activity,
   not per-file-recency, despite being read that way at the call site.
   Together: for any still-open session, any file it ever touched — no matter how long ago, even if
   safely committed since — permanently blocked every other session from committing it. Worked
   around at the time via the documented `allow-foreign-commit` override (verified the working-tree
   diff was 100% mine before doing so), same as the 2026-07-16
   `feedback_shared_checkout_guard_session_attribution_unreliable` pattern, but this was a distinct,
   root-caused code defect rather than an attribution-log ambiguity.

**Resolution (commit `ebb321f`, 2026-07-20, `claude/inspiring-pascal-d23945`):** both bugs fixed in
`hooks/commit-provenance-guard.py`. (1) `last_commit_time()` now wraps the pathspec as
`:(literal,icase)<abs_path>` before calling `git log` — case-insensitive match, `literal` guards
against glob-metacharacters in real paths; verified against the exact production repro
(`open-items-tracker.md` under `C--Users-Owner-OneDrive---Oxford-Capital-Partners`) and confirmed it
now returns the correct commit timestamp instead of empty output. (2) `foreign_hits()` dropped the
whole-file `os.path.getmtime()` TTL gate entirely and now checks each entry's own `touch_ts` (already
returned by `read_touched()`) against the TTL cutoff — an unknown `touch_ts` (old-format line) still
never ages out, per `commit_provenance.py`'s documented "just touched" contract. Added 5 regression
tests to `hooks/tests/test-commit-provenance-guard.py` (2 case-sensitivity, 2 per-entry-TTL, 1 test
corrected to exercise the new per-entry mechanism instead of the removed file-mtime one); confirmed
each fails against the pre-fix code and passes against the fix. Full 23/23 guard suite + 6/6 recorder
suite green. Independent adversarial refute pass (per this repo's `hooks/**` mandatory-REFUTE
doctrine) found no confirmed flaws — one accepted, now-documented design tradeoff: per-entry TTL
narrows the block window for a still-live session that touched a path >TTL_H ago and stayed active
elsewhere, which now ages out and allows the commit (intended effect of keying TTL to
`SESSION_PRUNE_H` per-touch rather than per-file-activity; `already_committed_since()` remains the
correctness backstop for genuinely-landed content).
