# Audit follow-up: hook/coordination fixes (2026-07-09)

Five follow-up items surfaced after the 2026-07-09 Claude Code setup audit
(`memory/project_claude-setup-audit-2026-07-09.md`). All touch `hooks/**`
or `~/.claude` doctrine files (blast radius; no L1 fast-path). Built directly
on the existing `~/.claude` checkout — its current uncommitted diff is this
same audit's in-flight output (archive-sweep renames, the `shared-checkout-
guard.py` `.claude`-coverage fix, the `ratify-hurdle-rate` skill conversion
all match the audit memory doc's "what was fixed" list), not a foreign
collision, so no worktree isolation.

**Revision note (post self-review):** this version incorporates a full
adversarial pass — one factual error caught and corrected (item 1's
mechanism), five real gaps fixed (items 2, 3, 4, 5, plus guard-liveness
registration). See "Self-review corrections" at the end for the delta.

## 1. CLAUDE.md edit-time doctrine signal

**Problem:** `doctrine-integrity-probe.py` checks 5 (word budget,
`WORD_BUDGET_FAIL=1850`) and 6 (bare ISO dates) are hard-fail
(`sys.exit(1)`), but the only caller is `git-prepush-doctrine-gate.py`,
which fires solely on `git push` (`.git/hooks/pre-push` shim). An edit that
trips either check gets no local signal until the next push, which may be
hours later.

**Mechanism — PreToolUse, simulate + deny (revised from PostToolUse-block).**
Verified directly: this repo has **no existing precedent for a blocking
PostToolUse hook** — `eos-plan-gate.py` (the only comparable blocking gate)
is PreToolUse with `hookSpecificOutput.permissionDecision:"deny"`;
every actual PostToolUse hook in settings.json (`fleet-session-hook.py`,
`eos-gate-sentinel.py`) is explicitly fail-open, exit 0 unconditionally.
Rather than pioneer a new, unverified PostToolUse block contract, reuse the
proven PreToolUse deny pattern:

- Add `--quick` to `doctrine-integrity-probe.py`: runs only checks 5+6
  against given TEXT (not just a path — see below), skips 1-4/7-11 entirely
  (no OneDrive skill walk, no git ls-files leak scan, no guard-liveness
  scan). Refactor checks 5+6 into a small pure function,
  `check_size_and_dates(text) -> list[str]` (list of violation messages,
  empty = OK), called both by `--quick` (reads a file) and by the new
  PreToolUse hook (passes simulated in-memory text, no file needed).
- New `hooks/eos-claude-md-guard.py`, registered **PreToolUse** on
  `Edit|Write|MultiEdit`. Reads `tool_input`; no-ops unless the target path
  resolves to `CLAUDE.md` at the `~/.claude` root — comparison via
  `Path(...).resolve()` + `os.path.normcase`, not naive string equality
  (Windows path casing/separator variance must not cause a silent
  false-negative — that would reproduce the exact "silently orphaned
  guard" failure class check 11 exists to catch).
  - **Write**: `tool_input.content` is the simulated post-edit text directly.
  - **Edit**: apply `tool_input.old_string` → `tool_input.new_string` against
    the current on-disk text (single occurrence, mirroring the real Edit
    tool's own match semantics) to get simulated post-edit text.
  - **MultiEdit**: apply each edit in `tool_input.edits` in sequence.
  - Run `check_size_and_dates()` against the simulated result. On violation,
    emit `hookSpecificOutput.permissionDecision:"deny"` with the violation(s)
    as the reason — same mechanism `eos-plan-gate.py` already uses. The
    edit never lands on disk in a violating state.
- **Guard-liveness registration**: add `eos-claude-md-guard` to CLAUDE.md's
  "Guards:" line so check 11 covers it — this whole audit thread traces to
  a guard that silently lost its runner; shipping a new guard without
  registering it would reproduce that failure class. (Minor: this edit to
  CLAUDE.md is itself checked by the new guard once live — a natural
  bootstrap test; confirm current word count has headroom first.)
- Acceptance criterion: the no-flag/default path `git-prepush-doctrine-gate.py`
  depends on must be byte-for-byte unchanged after the `check_size_and_dates()`
  refactor — regression-test this explicitly, not just assumed.

## 2. MEMORY.md index threshold measures the wrong span

**Problem:** Check 9 ([maintenance/doctrine-integrity-probe.py:806-810])
measures `len(ln.strip())` on the entire bullet — `- [Title](file.md) —
hook text` — against `MEMORY_INDEX_LINE_MAXLEN=150`. memory-policy.md sec 3
only requires the *description* be one line; a long title/filename alone
can exceed 150 chars before the hook text even starts, so some entries warn
permanently regardless of how terse the hook is.

**Fix (revised):** Not a string split on the em-dash (fragile — a title
containing its own em-dash would misparse). Instead reuse
`MEMORY_INDEX_ENTRY_RE.match(ln)`, already computed for the line, and
measure `ln[match.end():]` — everything after the matched markdown link,
regardless of separator character. A hook-less/malformed entry yields an
empty/short slice and simply doesn't warn, no special-casing needed.
Rename `MEMORY_INDEX_LINE_MAXLEN` → `MEMORY_INDEX_HOOK_MAXLEN`; keep 150 as
the default — deliberately treated as a fresh number for the now-isolated
hook text (previously the hook portion rarely got close to 150 once
title+filename ate part of the old whole-line budget, so keeping the same
number is a real, intentional loosening, not a like-for-like carryover).

## 3. Declassification checklist gap

**Problem:** No checklist exists anywhere for which files change when a
deal is declassified. The E. Fulton declassification
(`memory/event_log.md:41-49`) touched `hooks/confidential-terms.json`,
`memory/projects.md`, `memory/MEMORY.md`, `memory/firm.md` — but not
`session-context.md`, the sanctioned untracked roster home per Hard
Invariant 3 (`rules.md` §7a). It needed updating and eventually got it,
out-of-band, not because any checklist said to. `ora-skills/deal-
retirement/SKILL.md` is the nearest existing skill but covers CLOSED/KILLED
lifecycle only — declassification is a distinct event.

**Fix:** Add a "Declassification / reclassification file checklist" to
`memory/rules.md` §7a, generalized from the E. Fulton precedent —
corrected to include the file it was actually sourced from:
`hooks/confidential-terms.json` (flip `active`), `session-context.md`
(roster line), `memory/event_log.md` (dated decision entry — every
declassification is exactly the kind of dated history that belongs there),
`memory/projects.md`, `memory/MEMORY.md` (index, only if the entry text
changes), `memory/firm.md` (only if firm-level facts changed).

**Enforcement: doc-only (decided).** Declassification is rare (one instance
on record); add a one-line pointer from Hard Invariant 3 to the rules.md
§7a checklist so it's at least reachable from the place a future session is
already looking when the roster is on-screen. No automated check — revisit
if a future declassification misses it again despite the pointer.

## 4. Session liveness (replaces mtime-quiescence guesswork)

**Problem:** Interactive-routine coordination currently relies on humans
eyeballing `registry-membership.log`'s latest timestamp, or ad hoc mtime
checks on unrelated files — which misfire on ordinary interactive pauses
(observed: a 14-minute human-thinking gap read as "session dead"). No
code-enforced liveness signal exists.

**Fix:** No new lockfile. `hooks/fleet-session-hook.py` already maintains
`obsidian-fleet-mirror/session-state.json` with exactly the right
granularity: `SessionStart`/`PostToolUse` → `status:"working"`, `Stop` →
`status:"idle"` (session still open, paused awaiting user input), `SessionEnd`
→ popped from `state["sessions"]` immediately (fleet-session-hook.py:306).
A session's key-presence in that dict is a precise, already-maintained
"is it open" signal for the clean-exit case; `SESSION_PRUNE_H=6` (hours)
remains the only fallback, for sessions that crash without `SessionEnd`.

**Two corrections from self-review:**
- **Matcher gap (verified against live settings.json):** `fleet-session-
  hook.py`'s PostToolUse registration is confirmed `Bash|Task|TaskCreate|
  TaskUpdate` only — it does not fire on Edit/Write/MultiEdit. During an
  edit-heavy stretch, `status`/`lastAt` go stale even though the session is
  genuinely active (dict presence — the load-bearing signal — is
  unaffected, since only Stop/SessionEnd/6h-prune remove an entry, but the
  working-vs-idle nicety item 5 leans on for message text becomes
  unreliable). **Fix:** widen the PostToolUse matcher to
  `Bash|Task|TaskCreate|TaskUpdate|Edit|Write|MultiEdit` in settings.json.
  Cheap — the hook is already async/fire-and-forget.
- **Accepted risk, documented (not fixed):** `save_state()`'s load→mutate→
  replace cycle is unlocked. Safe as a best-effort Obsidian mirror; a real
  (if narrow) risk once repurposed as a coordination signal for the exact
  scenario — two concurrently active sessions — most likely to race on it.
  Bounded by this design's own WARN-only/enrichment-only principle below:
  worst case is an imprecise warning message, never a false "all clear"
  that suppresses a real hard check. Not adding locking (YAGNI given the
  bound); documented explicitly in the code comment rather than left
  implicit.

Add `hooks/lib/session_liveness.py` (new convention — `hooks/lib/` doesn't
exist yet; every other hook is currently self-contained):
```python
def other_active_sessions(own_sid, state_path=None) -> list[dict]:
    """Sessions present in session-state.json other than own_sid.
    Honors the ORA_FLEET_STATE env var override (same as fleet-session-
    hook.py) so a non-default config can't silently desync writer/reader.
    Fail-open: any read/parse error returns [] (never raises, never blocks).
    Each item: {sid, status, cwd, lastAt}."""
```
Consumers treat this as an *enrichment* signal only — never a hard gate.
If the mirror file is stale, missing, or fleet-session-hook.py silently
errored (it always exits 0 by design), callers degrade to whatever
git-status-only behavior they had before.

## 5. shared-checkout-guard co-file collision detection

**Depends on #4.** Today `hooks/shared-checkout-guard.py` warns once per
session when a **repo-wide** `git status --porcelain` (not scoped to the
touched file) reports any dirty lines in a covered repo's main checkout
(`DEFAULT_REPOS`, `.claude` just added there in the current uncommitted
diff), with no self-vs-other distinction and no re-arm — the exact gap
that let two sessions both edit CLAUDE.md today without either getting a
second, more urgent warning once the other party's change actually landed.

**Fix (re-arm key corrected from the original draft):**
- When the guard's existing repo-wide dirty check fires, cross-reference
  `session_liveness.other_active_sessions()`. If another session is
  currently open, upgrade the warning to name it specifically ("session
  `<short-id>` is open right now editing in this repo") instead of the
  generic "tree is dirty" message. Stays WARN-only — no change to the
  existing non-blocking severity.
- Re-arm the per-session dedup marker keyed on a fingerprint of the full
  `git status --porcelain` **repo-wide** output (not a single file's diff —
  the original draft keyed re-arm on the file currently being edited, which
  doesn't match the check's actual repo-wide scope: the file being edited
  right now may not be the dirty file the warning is about). Re-warn
  whenever the overall dirty-file set changes, regardless of which file
  triggered the check.
- Worktree-scoped work is confirmed out of scope by design (the existing
  guard already only fires for a repo's *main* checkout, not a linked
  worktree — isolation already solves the collision problem structurally
  there).

## Build order

1, 2, 3 are independent and can run in parallel. 4 must land before 5.
Dispatch: `subagent-driven-development`, sonnet pinned per task (none of
this is confidential/financial/governor code) — 5 code-heavy, mostly
independent tasks, matches the CLAUDE.md dispatch threshold (>4 tasks).

## Testing

Each touched hook already has a sibling `test-*.py` in `hooks/` /
`hooks/tests/` (e.g. `test-ora-autonomy-gate.py`, `test-confidentiality-
guard.py`) — new/changed logic gets equivalent stdlib-only unit tests
following that existing pattern, run before any commit. Item 1 additionally
needs a regression test proving the no-flag probe path is unchanged.

## Self-review corrections (delta from the original draft)

Caught by a full adversarial pass, verified against the live repo rather
than assumed:
1. Item 1: switched PostToolUse-block → PreToolUse-simulate-deny after
   confirming no local precedent exists for the former and a proven
   pattern already exists for the latter.
2. Item 1: added explicit Windows-safe path comparison and guard-liveness
   registration (both missing from the original draft).
3. Item 2: `match.end()` slicing replaces the fragile em-dash split.
4. Item 3: added the missing `memory/event_log.md` to the checklist (an
   outright omission — ironic, since it's literally where the E. Fulton
   precedent was read from) plus the Hard-Invariant-3 pointer.
5. Item 4: added the PostToolUse matcher widening (verified gap against
   live settings.json) and explicitly documented the `save_state()` race
   as an accepted, bounded risk instead of silently inheriting it.
6. Item 5: corrected the re-arm key from per-file-diff to repo-wide-status
   fingerprint after re-verifying the existing check's actual scope.
