# Commit-Provenance Guard — Design Spec

**Date:** 2026-07-16 · **Status:** DESIGN APPROVED (Gabriel, 2026-07-16), not yet implemented
**Supersedes nothing.** Complements `hooks/shared-checkout-guard.py` (advisory, edit-time);
this guard is enforcing, commit-time. Neither replaces the other.

## 1. Goal

Stop one session's `git commit` from sweeping up **another live session's uncommitted work**
in the shared single-instance repos (`~/.claude`, `ora-skills`, `oxford-command-center`).

Success: the 2026-07-16 sweep (below, event #4) is blocked with an actionable message, while
every legitimate commit in the fleet — including the deliberate "land the orphaned backlog"
janitor commit — still succeeds.

Explicit non-success criteria: this is **not** a mutex and does **not** serialize writers. See §10.

## 2. Evidence — the honest foundation

Four concurrency events in ONE session on 2026-07-16 (session `0888c827`), all observed, none
hypothetical:

| # | Event | Mechanism | Caught by an Edit/Write claim-lock? |
|---|---|---|---|
| 1 | `ora-pm-ledger/SKILL.md` rewritten under the session (781→867 lines, writes at 19:41 + 19:45) | Edit/Write | yes |
| 2 | HEAD moved mid-session (`31ac61d`, event_log rollover 3083→604 lines) | Bash `git commit` | **no** |
| 3 | `git push` raced the session; "Everything up-to-date" while `ahead 3` | Bash `git push` | **no** |
| 4 | A **staged** MEMORY.md edit swept into another session's commit `4da5d26`, between this session's `git add` and its `git commit` (~30s window) | Bash `git add`/`commit` | **no** |

**3 of the 4 are Bash git operations.** A PreToolUse hook on `Edit|Write|MultiEdit` structurally
cannot observe a `git commit`. This is why the original ask ("make the guard a real claim-lock")
was re-scoped: a claim-lock addresses event #1 only — the minority, and the least harmful
(event #1 cost nothing; event #4 smeared authorship and, with different timing, loses work).

Precedent for Bash inspection already exists: `ora-autonomy-gate.py:169` calls
`check_bash(tool_input.get("command", ""))`.

## 3. Rejected alternatives

**A. Provenance-negative — "block if the commit includes a file THIS session never touched."**
REJECTED. Fatal false-positive rate. It would have blocked `31ac61d`, a legitimate commit, because
that session generated `event_log.md` with a **script** (`rollover-event-log.py`), not the Edit
tool. Same for every `cp`-, `python`-, or heredoc-created file. With ~8 concurrent sessions this
guard gets disabled within a day, which is worse than no guard.

**B. Full claim registry / lease-based mutex.** REJECTED (Gabriel, 2026-07-16). Requires atomic
`O_CREAT|O_EXCL` claim storage, TTL-based stale-claim recovery, and release-on-crash handling. A
crashed session holding a claim can wedge the fleet. This repo has exactly one fail-closed guard
(`confidentiality-guard.py`) and it has already self-deadlocked the machine once (memory:
`feedback_confidentiality_guard_selfdeadlock`). Not worth the class of risk.

**C. Build on `session_liveness` as the gate.** REJECTED BY ITS OWN CONTRACT. Its docstring:
> "ENRICHMENT ONLY, never a hard gate: fleet-session-hook.py is itself fail-open/best-effort ...
> its save_state() load-mutate-replace cycle is unlocked — a real, accepted, bounded race under
> concurrent writers, which is exactly the two-sessions-open scenario this module exists to
> detect. A caller MUST treat a read failure, or a stale/empty result, the same as 'no
> information' — never as 'definitely no other session' or 'definitely another session' — and
> degrade to whatever git-status-only behavior existed before consuming this module."

Liveness may therefore only ever be consumed as an **affirmative** signal (§5). "No info" must
never license a block, and must never license treating a commit as safe either — it simply means
this guard has nothing to say.

## 4. Architecture — two small pieces

**4a. Recorder — `hooks/commit-provenance-recorder.py`** (PostToolUse)
Records what THIS session edited, so other sessions can recognise it as owned.
* Matcher: `Edit|Write|MultiEdit` plus the four Desktop Commander write aliases
  (`mcp__Desktop_Commander__write_file|edit_block` and the
  `mcp__plugin_desktop-commander_desktop-commander__` variants), matching the coverage
  `registry-write-guard.py` and `memory-index-guard.py` already settled on.
* Reads `tool_input.file_path`, falling back to `tool_input.path` (DC's `write_file` uses `path`;
  `edit_block` shares Edit's `file_path`).
* Appends one absolute, `os.path.normcase`-normalised path per line to
  `hooks/sessions/<session_id>/touched-files.txt`.
* **Append-only.** No read-modify-write, therefore no race — deliberately unlike
  `fleet-session-hook.py`'s unlocked load-mutate-replace (§3C). Duplicates are expected and
  deduped on read.
* PostToolUse, so it records only writes that actually happened.

**4b. Guard — `hooks/commit-provenance-guard.py`** (PreToolUse, matcher `Bash`)
Blocks a `git commit` that would capture another live session's edits.

## 5. The block predicate (precise)

BLOCK if and only if **all** of these hold:
1. The Bash command is a `git commit` invocation (§6), and not `--dry-run`.
2. The candidate file set (§7) is non-empty.
3. Some candidate file appears in `hooks/sessions/<other_sid>/touched-files.txt` for at least one
   `other_sid != my session_id`, where **both**:
   a. `session_liveness.other_active_sessions()` **affirmatively** reports `other_sid` as open, and
   b. that `touched-files.txt`'s mtime is within `TTL_HOURS` (default **6**, matching
      `fleet-session-hook.py`'s `SESSION_PRUNE_H=6`).
4. No override sentinel at `hooks/sessions/<my_sid>/allow-foreign-commit` (§8).

Otherwise ALLOW, silently.

**Two affirmative signals are required.** This makes the guard fail-open *by construction*, not by
exception handling: missing liveness data, a missing sessions dir, an unreadable touched-file, or
a stale set all yield "no information" → allow. §3C's contract is honoured exactly.

**Self-recognition is structural**: the session's own `touched-files.txt` is excluded by
`other_sid != my session_id`, so a session can never block itself.

**No lock is ever held**, so the deadlock class does not exist — a crashed session cannot wedge
anyone. TTL is belt-and-braces against a stale session dir whose liveness is wrongly positive, not
the thing standing between the fleet and a wedge.

## 6. Detecting a `git commit`

Match `\bgit\b[^|;&]*\bcommit\b` per shell segment. Handle:
* `git commit -m "x"`, `git commit -F file`, `git commit -am "x"`
* `git -C <path> commit ...` → repo is `<path>`
* `cd <path> && git commit ...` → repo is `<path>`
* otherwise → repo is the payload's `cwd`

Resolve the repo root with `git -C <dir> rev-parse --show-toplevel`. If that fails (not a repo) →
ALLOW. If the command `cd`s somewhere this parse misses, the staged set won't resolve and the
guard yields no hit → ALLOW. Under-blocking is the correct direction (§10, precision over recall).

Skip `--dry-run` (no provenance is fixed).

## 7. The candidate file set

Given repo root R, produce absolute normcase paths:
* **Default** (`git commit`): staged set = `git -C R diff --cached --name-only`.
* **`-a` / `--all`**: staged set ∪ tracked-modified (`git -C R diff --name-only`).
* **Explicit `-- <pathspec>`**: **only** those paths.

The pathspec case is load-bearing, not an optimisation: the guard's own remediation message tells
the user to "commit with an explicit pathspec", so a pathspec commit MUST actually narrow the
candidate set or the advice is a lie. A test asserts this (§9, case 6).

Git returns repo-relative POSIX paths; convert to absolute + `normcase` before comparing, since
the recorder stores absolute normcase paths.

## 8. Override — the janitor must still work

`c0272bb` ("chore: land 2026-07-16 scheduled-tasks backlog") and `4da5d26` were **legitimate**
commits deliberately landing other sessions' orphaned WIP. That workflow must remain possible.

Escape hatches, in order of preference:
1. Commit with an explicit `--` pathspec naming only your own files.
2. `touch hooks/sessions/<my_sid>/allow-foreign-commit` — deliberate backlog-landing. Mirrors
   `eos-plan-gate.py`'s existing `override` sentinel pattern (a session-scoped file, surfaced in
   telemetry), so the fleet already knows this idiom.

The block message MUST state both.

## 9. Testing (TDD — tests first, RED before GREEN)

New: `hooks/tests/test-commit-provenance-guard.py` and
`hooks/tests/test-commit-provenance-recorder.py`. Follow
`test-shared-checkout-guard.py`'s established conventions: stdlib only, ASCII-only, self-contained
temp git repos, env-var injection, no network, no real fleet state.

Env seams: `COMMIT_PROVENANCE_SESSIONS_DIR`, `COMMIT_PROVENANCE_TTL_H`, and the existing
`ORA_FLEET_STATE` consumed by `session_liveness`.

Guard cases:
1. Non-git Bash command → allow, silent.
2. `git commit`, only this session's files staged → allow.
3. `git commit`, a staged file is in another **live** session's touched-set → **BLOCK (exit 2)**,
   stderr names the file and the owning session.
4. Same as 3, but the other session is **not** live → allow (liveness contract, §3C).
5. Same as 3, but the other session's touched-set is **older than TTL** → allow.
6. Same as 3, but `git commit -- <my file>` excludes the foreign file → allow (§7).
7. Same as 3, with `allow-foreign-commit` sentinel present → allow.
8. Malformed stdin → allow (fail open).
9. `cwd` is not a git repo → allow.
10. `git commit --dry-run` with a foreign staged file → allow.
11. A session's OWN touched-set never blocks it (self-recognition).
12. `git commit -a` picks up tracked-modified foreign files → BLOCK.

Recorder cases:
1. Edit payload (`file_path`) → path appended.
2. DC `write_file` payload (`path`) → path appended.
3. Repeated writes → duplicates tolerated, deduped on read.
4. Malformed stdin → no crash, exit 0.

Done = both suites green **and** the full existing 18-file hook suite green (no regressions).

## 10. Non-goals (deliberate under-reach)

* **Not a mutex.** Does not serialize writers, does not prevent two sessions editing one file —
  that stays `shared-checkout-guard.py`'s advisory job (whose delivery was fixed in `d80074e`).
* **Does not guard `git add`.** Staging is reversible and harmless; `commit` is the single
  chokepoint where provenance is fixed, and it catches the sweep in both directions.
* **Does not guard `git push`.** Pushing already-committed work is not the harm.
* **Does not catch foreign files written by a script** rather than the Edit tool. Accepted false
  negative — this is the exact concession that makes the guard survivable (§3A). Precision over
  recall, matching `registry-write-guard.py`'s stated philosophy.
* **Does not fix event #2 or #3** (HEAD moving, push races). Those are ordinary distributed-git
  conditions with existing remedies (`fetch` + `--ff-only`); they cost attribution clarity, not
  work.

## 11. Work breakdown

1. `hooks/tests/test-commit-provenance-recorder.py` (RED) → `hooks/commit-provenance-recorder.py` (GREEN).
2. `hooks/tests/test-commit-provenance-guard.py` (RED) → `hooks/commit-provenance-guard.py` (GREEN).
3. Register both in `settings.json` (PostToolUse `Edit|Write|MultiEdit|<DC aliases>`; PreToolUse `Bash`).
   Ordering note: `ora-autonomy-gate.py` is PreToolUse #1 and denies via exit 2; this guard is
   independent of it — all matching hooks run and deny wins, so relative order does not matter
   (verified live 2026-07-16: with `shared-checkout-guard` returning `allow`, `registry-write-guard`
   still blocked).
4. Full 18-file hook suite + both new suites green; live smoke test of a real blocked commit.
5. Memory: extend `reference_hook_systemmessage_not_model_visible` or add a pointer, and record the
   guard in the fleet guard roster that `doctrine-integrity-probe.py`'s guard-liveness check reads
   (it currently checks 6 guards and verifies each has a live invocation point).

## 12. Open risk

The recorder only sees tool-driven writes. A session that does ALL its editing via Bash
heredocs/scripts records nothing, and its work is therefore unprotected by this guard. This is the
§10 false negative stated plainly: the guard protects Edit/Write-authored work, which is the
overwhelming majority of what these repos contain, and silently protects nothing else. It must not
be described to users as complete coverage.
