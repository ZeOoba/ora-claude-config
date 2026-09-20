---
name: feedback-website-canonical-slug-blocks-scratchpad-and-memory
description: "In a website-canonical session the autonomy gate blocked the scratchpad AND that project's whole memory scope, because both paths carry the cwd slug. FILE-PATH HALF FIXED 2026-09-18 (PR #212, MERGED on origin/main) -- Write/Edit now work; Bash/Gate 2b still blocks on the marker anywhere in the command, including a heredoc payload on a pure read. Never mint allow-website-write for a non-site write."
metadata:
  node_type: memory
  type: feedback
---

**Symptom.** In a session with cwd `C:\Users\Owner\website-canonical`, the ORA autonomy gate refuses
Write calls to two paths that are not the site tree, both reported as
`BLOCKED by ORA autonomy gate: write to oxfordra.net site tree`:

1. the session scratchpad — `…\Temp\claude\C--Users-Owner-website-canonical\<session-id>\scratchpad\*`,
   which the harness itself nominates for temp files; and
2. `~/.claude/projects/C--Users-Owner-website-canonical/memory/*` — so that project's **entire
   auto-memory scope is unwritable**, including ordinary `feedback_*.md` notes.

Both paths inherit the literal string `website-canonical` from the cwd slug. Reproduced twice on
2026-09-18 (a read-only Python extraction script; a memory note) while building the ORA Forward
Calendar artifact. Filed as [OI-313](open-items-tracker.md#OI-313).

**Why it matters.** The tempting workaround is the token the gate itself offers. Don't take it:
minting `allow-website-write` to place a scratch file or a memory note buys 60 minutes of
**multi-use WRITE access to the real oxfordra.net site tree** — strictly worse than the write you
wanted, and the same trap `config-write-guard` documents for read-shaped commands. A false positive
is not a reason to widen a gate; it is a reason to move the file.

**How to apply (updated 2026-09-18 after the fix above).**
- **Write/Edit tool → both paths now work.** The scratchpad and the project memory scope are
  exempted. The two workarounds below are no longer *required* for tool-based writes — they remain the
  fallback for any checkout whose gate predates PR #212 (the shared `~/.claude` checkout lagged
  origin/main by ~179 commits, though its working-tree gate file already carried the fix).
- **Bash still blocks, and that is correct.** Gate 2b is unchanged and matches the site marker
  ANYWHERE in the command — including inside a heredoc body, a quoted string, or a commit message,
  on a command that only *reads*. Reproduced twice more on 2026-09-18: once on a `python - <<PY`
  that merely read a file under the slug, once where the path was innocent (OneDrive) and the marker
  appeared only in the heredoc **payload text**. Fix: use Read/Grep/Glob to read and Edit/Write to
  write — those carry the narrowed path check instead — or keep the marker out of the command text.
- Scratch files for artifact/tooling work → a neutral temp dir is still the least-friction choice,
  e.g. `C:\Users\Owner\AppData\Local\Temp\<topic>\`; publishing an Artifact with `file_path` pointing
  there works, so the session's working directory never needs changing.
- **Never mint `allow-website-write` for a write that is not actually to the site tree.** This
  survives the fix intact and is the part that matters: the token buys 60 minutes of multi-use write
  access to the real oxfordra.net tree. A false positive is a reason to move the file or change the
  tool, never to widen the gate.

**RESOLVED for the file-path half — 2026-09-18, same day, session `109dd884`, PR
[ora-claude-config#212](https://github.com/ZeOoba/ora-claude-config/pull/212).** The open question
below has been answered: the blocks came from `check_file_write`, it *was* narrowable, and it was
narrowed — resolved-path-anchored exemptions for `~/.claude/projects/<slug>/memory/` and
`%TEMP%/claude/<slug>/<session>/scratchpad/`. Verified live 2026-09-18 by a later session: a Write
to the session scratchpad under the `website-canonical` slug now succeeds where the identical shape
was blocked twice hours earlier. **It is MERGED on `origin/main`** (`906ba96`, merge `59a0f51`,
PR #212) — an earlier note in this file said "staged, not committed", which was wrong: that reading
came from `git log HEAD` on a shared checkout sitting 171 commits behind origin/main. Baseline
against the push target ([[feedback_preexisting_failure_verify_against_push_target]]). Detail and the four adversarial traps
it had to survive: the note `feedback_site_gate_file_path_narrowing_is_allowed` (it lives in the
`website-canonical` project memory scope — the very scope this memo said was unwritable — so it cannot
be wikilinked from this scope).

*Original open question, kept for the reasoning:* [[feedback_autonomy_gate_matcher_cannot_be_safely_narrowed]]
is emphatic that Gate 2b must NOT be narrowed — four independent attempts each produced a confirmed
bypass. But that guidance is about Gate 2b's **Bash-command** matcher (site marker + write verb
co-occurring anywhere in a command string), whereas these two blocks came from the **Write tool on a
file path**. The two functions answer different questions: Gate 2b must decide *which command
consumes this token and does that command write*, which pattern-matching cannot decide;
`check_file_write` gets one absolute path and `realpath()` answers the only question that matters —
where do the bytes land. **The generalizable lesson: "this gate cannot be narrowed" was true of one
matcher and got over-applied to the whole gate. Check which check fires before inheriting a
prohibition.**

Related: [[feedback_autonomy_gate_matcher_cannot_be_safely_narrowed]],
[[feedback_config_write_guard_bash_read_shaped_false_positive]].
