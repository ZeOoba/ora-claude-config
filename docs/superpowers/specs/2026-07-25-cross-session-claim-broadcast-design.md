# Cross-session claim/broadcast mechanism — design

**Phase 2 shipped 2026-07-26** (file-level collision detection). This document
describes v1 as designed; the "Not building" section carries the superseding note
and the incidents that forced it. Read that before treating any deferral here as
current.

**Status:** approved by default (AskUserQuestion sent to Gabriel with researched
recommendations on all 3 open decisions; no response — session proceeded per the
Autonomy doctrine's "no clarifying questions when unambiguous/non-destructive" rule.
All three recommended defaults below were used. Flag for Gabriel to revisit if he'd
have chosen differently.)

**Origin:** `reference_concurrent_session_duplicate_hardening_work.md` — 6 recorded
collisions 2026-07-16 through 2026-07-24 of concurrent sessions independently
duplicating work on shared `~/.claude` subsystems. The file's own 2026-07-17
prediction ("a lightweight in-progress-work board... would generalize the existing
per-path single-writer rules to ANY shared subsystem") was escalated by Gabriel
2026-07-25 as `task_17998414` after the 6th recurrence. Current mitigation (manual
`git worktree list` + `list_sessions` pre-check) already failed to catch the most
severe incident (07-16/17, two sessions hardening the same override-token defect in
different gate files).

## Problem shape

Two sessions independently decide to fix the same class of bug (or claim the same
tracker ID slot, or write the same data file) in a shared, non-git-locked area of
`~/.claude`, without either being aware of the other. This is narrower than a
file-level conflict — the sessions may never touch the same file — so git alone
can't catch it, and it's proactive-visibility this repo doesn't yet have for ad-hoc
work (unlike the three NAMED single-writer paths: `ora-skills`, scheduled-task
registries, `workflows/`).

## Prior art already in this codebase (why this design is not novel)

- **Per-writer-file, no lock** (`hooks/fleet-session-hook.py`, rewritten
  2026-07-24): moved OFF a shared `session-state.json` + mutex after it measurably
  lost data under concurrency (10/12 sessions), onto one file per session
  (`SESSIONS_STATE_DIR/<sid>.json`, atomic rename + pid-unique tmp name). Only the
  owning writer ever touches its own file — nothing to race.
- **Fail-open + TTL over hard lock** (`tech.md` §3d, Master Workbook single-writer
  protocol, ratified 2026-07-25): "NOT a hard lock... a crashed session holding a
  hard claim... would wedge every other session... a worse failure than an
  occasional missed collision." Scoped to structural writes only, not every edit.
- **`additionalContext` is the only model-visible, non-blocking hook channel**
  (`reference_hook_systemmessage_not_model_visible.md`): `systemMessage` is
  user-only and invisible to the agent — a hook that "warns" via `systemMessage`
  alone silently never helps (measured: 168 firings, 0 deliveries, one incident).
- **Working `SessionStart` template** (`hooks/repo-freshness.py`): reads live state,
  no-ops silently on any error or out-of-scope cwd, emits
  `hookSpecificOutput.additionalContext`. This new hook is structurally the same
  shape, generalized from one repo's git-freshness to any subsystem's claim state.

## Mechanism

**Claim files** — new `hooks/active-work/` directory, one JSON file per active
claim, named `<subsystem-slug>.json`:
```json
{"session_id": "...", "title": "...", "description": "...",
 "claimed_at": "2026-07-25T22:41:00", "cwd": "..."}
```
Written/cleared by `hooks/lib/claim_work.py` (`claim <slug> "<desc>"` /
`release <slug>`), atomic rename + pid-unique tmp name (same pattern as
`fleet-session-hook.py`'s `save_session()`). `session_id` defaults to
`$CLAUDE_CODE_SESSION_ID` (confirmed present in the Bash environment). Only the
claiming session writes its own claim file — same no-lock-needed argument as
`fleet-session-hook.py`.

**Broadcast** — new sync `SessionStart` hook, `hooks/active-work-broadcast.py`
(4th entry in `settings.json`'s `SessionStart` array, alongside `repo-freshness.py`
— both are sync/context-emitting; `fleet-session-hook.py` stays last since it's
`async` and a pure side-effect mirror). Reads `hooks/active-work/*.json`, drops
anything past a 2-hour TTL (no release required — fail-open expiry, not a lock),
emits any survivors via `additionalContext`. A starting session now sees "⚠ session
X claimed hooks-override-auth 12m ago: hardening override token" automatically —
replacing the manual `git worktree list` step for this signal (not for git-state
generally, which the existing rule still covers).

**TTL = 2 hours.** Headroom above the 90-minute stuck-session-watchdog kill
threshold (`maintenance/stuck-session-watchdog.ps1`), so a legitimately long task's
claim doesn't expire mid-task, while a genuinely stuck session gets killed before
its stale claim misleads anyone for long.

**Not building:** a `PreToolUse` *block* on `hooks/**` edits keyed to claims. This
mechanism stays a nudge, matching the two existing named single-writer rules
(`ora-skills`, scheduled-task registries), which are check-and-decide conventions,
not hard gates — and matching the ratified "fail-open + TTL beats mutex" call for
this exact problem class. **That still holds: nothing added since blocks anything.**

> **PHASE 2 SHIPPED 2026-07-26 — this section's deferral is now superseded.**
> The paragraph above originally continued: *"A mid-session (not just SessionStart)
> warn-on-edit extension is a plausible Phase 2 if this recurs after shipping v1;
> not built now per YAGNI — first offense doesn't justify the extra surface, and
> this file's own history shows the *class* of collision recurring is what
> justifies each escalation."*
>
> **It recurred, twice, within 24 hours of v1 shipping** — which is exactly the
> bar this file set for escalation, met faster than anyone expected:
> - 2026-07-25/26: two sessions ran the identical worktree/branch cleanup sweep in
>   parallel and raced deleting the same remote branch. Answer at the time: add a
>   `repo-housekeeping` slug. Vocabulary only, no mechanism change.
> - 2026-07-26: **four** sessions edited `scheduled-tasks/ora-weekly-hygiene/SKILL.md`
>   within minutes. Two held honest claims, under *different* slugs
>   (`ora-weekly-hygiene-spec`, `repo-housekeeping`). Adding vocabulary could not
>   have helped, and this is what made the deferral untenable:
>   1. **Slugs are work-TYPE scoped.** Two correct slugs on one file are
>      indistinguishable from two claims on unrelated subsystems. No slug taxonomy
>      fixes this; the claim needed to be able to name a *path*.
>   2. **SessionStart-only delivery was the load-bearing gap.** Every claim that
>      day was made mid-session, so no broadcast could reach an already-running
>      session *regardless of slug naming*. v1 could only ever warn sessions that
>      start after a claim — the minority case. Fixing (1) alone would still have
>      warned nobody.
>
> **What shipped** (see `hooks/tests/test-claim-file-collision.py`): optional
> `paths` on a claim (files or directories), and a same-file check inside
> `shared-checkout-guard.py` — which was *already* `PreToolUse`-bound, so this
> needed **no `settings.json` change** and added no new hook registration. It
> OR-s claim-declared paths with other live sessions' provenance touched-sets, so
> the common case works with **no discipline required**: nobody has to remember
> `--paths` for the automatic half to fire.
>
> **The YAGNI call was still right when it was made.** v1 was correctly scoped to
> the evidence available; what changed is the evidence, not the reasoning. Worth
> recording for the next deferral: the trigger that fired here was not "the
> feature would be nice" but "a logged incident that the shipped design provably
> could not have caught."
>
> **Two design constraints discovered only in Phase 2**, both from adversarial
> review, both worth carrying forward:
> - Moving the check off the SessionStart path made claim/liveness free text
>   reachable as **model-visible** `additionalContext` on every edit, not just at
>   session start — a prompt-injection surface v1's threat model never had to
>   cover. Descriptions are sanitized *and* fenced as untrusted; `status` is
>   allowlisted. Any new field interpolated there needs the same.
> - Reading the claims dir on the Edit hot path turned "world-writable and never
>   pruned" from a tidiness note into a self-DoS (measured: 20k files → ~33 s per
>   edit, silently under the hook timeout). Hence the 512-file / 64 KB caps.

## Generalization (the three collision shapes already logged)

| Slug | Trigger | Notes |
|---|---|---|
| `hooks-override-auth` | starting non-trivial hook/override/auth work | originally-escalated case |
| `open-items-tracker` | before appending a new `OI-NNN` entry | does NOT replace re-deriving the next-free ID fresh at write/merge time — that tactical fix stays; the claim is an earlier warning that prompts it |
| `oxford-command-center-data` | structural writes to `data/overlay.json` / `data/snapshots/portfolio.json` | mirrors the Master Workbook doctrine's own structural-vs-single-cell scope cut; lowest expected value of the three (the logged incident was a sub-minute scheduled-task write, a narrower race window than SessionStart-time visibility can reliably catch) but free to include since it's the same primitive |

Slugs are free-form strings, not a hardcoded enum — new subsystems can adopt the
convention without a code change, only a doc note (this file + the
`session-context.md` active-context block).

**Since Phase 2, a slug is no longer the only axis.** `repo-housekeeping` (added
2026-07-26) was the last collision shape answered with vocabulary alone until
`ora-skills` (added 2026-08-12 — two sessions handed the same remediation prompt,
caught only by reading the other's transcript; that repo's own tech.md §2 git-state
rule is blind to a concurrent session because commits there carry the machine's
shared human author identity rather than a per-session one, so git identity cannot
answer *"is this HEAD mine?"* — the two rules are complementary and both apply).
The same-file collision later on 2026-07-26 — four sessions on
`ora-weekly-hygiene/SKILL.md`, two holding *correct* but different slugs — could
not be answered with vocabulary, which is what forced `--paths`. Prefer
`--paths` whenever the work is scoped to specific files or a directory — it is
the axis that actually catches a same-file collision, and it composes with any
slug rather than competing with it.

## Testing

TDD per Engineering OS "Done" criteria (hooks/** is blast-radius; this also
qualifies as security/gate-adjacent code per the auth/override use case, so it
gets the mandatory adversarial REFUTE pass before being called done):
- `hooks/lib/claim_work.py`: write/read/release round-trip, TTL expiry filtering,
  malformed-JSON fail-open, concurrent-claim-different-slugs no-interference.
- `hooks/active-work-broadcast.py`: empty-directory no-op (no `additionalContext`
  emitted), single live claim emitted, expired claim filtered out, malformed claim
  file skipped not crashed, stdin-read failure fail-open.
- **Phase 2 — `hooks/tests/test-claim-file-collision.py` (39 assertions):** claim
  `paths` round-trip, two-slugs-one-file, directory coverage + sibling-prefix
  rejection, back-compat with pathless claims, dead-session suppression *with a
  positive control*, dedup + re-fire on a newly-arrived session, status-flip
  stability, recency window, injection via both claim text and liveness fields,
  fail-open (asserting no traceback, not merely exit 0).

  **Lesson from Phase 2's review, worth more than the tests themselves:** the
  first cut shipped "27/27 green" with two assertions that were vacuous —
  injection checks run against raw hook stdout, a `json.dumps` blob in which
  newlines are already escaped, so the assertion was False *by construction* and
  passed with the sanitizer stubbed to identity. A green suite on a
  security-relevant path is not evidence unless it has been **mutation-tested**:
  break the fix on purpose and confirm the suite goes red. Both Phase 2 fixes are
  now verified that way. See `feedback_fixture_shaped_tests_certify_dead_branches.md`.

## Out of scope for this pass

- Auto-detecting "non-trivial hook work" and auto-*claiming* (false positive/negative
  risk too high from a single tool call; stays a documented manual convention, like
  the two existing named single-writer rules). **Still out of scope after Phase 2** —
  note the distinction it turns on: auto-**detecting an overlap** from evidence
  already on disk (provenance, declared paths) is cheap and accurate; auto-**inferring
  intent** to claim from one tool call is not. Phase 2 built only the former.
- A UI/dashboard for claims beyond the SessionStart text broadcast.
- Migrating `fleet-session-hook.py`'s activity mirror to also carry claim data —
  kept as a separate, single-purpose module (`hooks/lib/active_claims.py`) rather
  than overloading an existing event-driven mirror with agent-declared state.
