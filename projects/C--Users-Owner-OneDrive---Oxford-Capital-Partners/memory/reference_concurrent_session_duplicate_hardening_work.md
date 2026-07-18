---
name: reference-concurrent-session-duplicate-hardening-work
description: "2026-07-17: two independent sessions built the SAME override-token hardening (one for git-prepush-doctrine-gate.py, one for ora-autonomy-gate.py) without knowing about each other -- discovered only by chance via `git worktree list`. RECURRED same day as ID-numbering collisions on open-items-tracker.md during a branch merge (two sessions independently claimed the same next-free OI-NNN slot, twice). Existing single-writer rules cover ora-skills/scheduled-tasks/workflows-dir by name, but nothing covers ad-hoc hook/security fixes or shared ID-bearing trackers generally. Before starting non-trivial hook/security work, check `git worktree list` + recently-active sessions first; before merging into a shared tracker, re-derive the next-free ID fresh, never trust a previously-computed number."
metadata:
  type: reference
  originSessionId: 794cdebc-d469-4137-b46e-43a56a39b1b0
---

**What happened.** Asked to harden `git-prepush-doctrine-gate.py`'s override token
(session-scope + content-bind it, mirroring a pattern that turned out not to exist yet on
`main`). Mid-task, discovered a SEPARATE session had independently reached the same
conclusion about the SAME underlying defect (clone-mintable override tokens) and was mid-way
through hardening the sibling gate, `ora-autonomy-gate.py`, in its own worktree
(`.claude/worktrees/autonomy-gate-hardening/`) — 622 lines, uncommitted, no memory or
`open-items-tracker.md` entry pointing at it. Found only by running `git worktree list` and
noticing the file's mtime was 3 minutes old with two other sessions more recently active than
mine. No proactive signal surfaced the overlap before that.

**Why the existing rules didn't catch it.** `~/.claude`'s single-writer doctrine
(`tech.md §2`, `MEMORY.md` fleet-registry rules, `workflows_dir_single_writer_gap.md`) names
specific high-traffic paths — `ora-skills`, scheduled-task registries, `workflows/`. It has no
general mechanism for "two sessions independently decide to fix the same class of bug in
different files of the same subsystem." That's a narrower, harder-to-name collision than a
file-level lock can catch, because the two sessions were never editing the same file.

**Cheap mitigation, no new infrastructure needed:** before starting non-trivial hook or
security work in `~/.claude`, run `git worktree list` and check for recently-active sessions
(`mcp__ccd_session_mgmt__list_sessions`, sorted by `lastActivityAt`) whose titles suggest
overlapping scope. Not foolproof — titles can be generic — but it is exactly the check that
would have surfaced this collision in under a minute instead of by chance.

**Not (yet) worth building:** a formal claims/locking system for ad-hoc work. This was the
first observed instance in the memory record; one incident doesn't justify new tooling. If it
recurs, escalate to Gabriel as a systematization candidate — a lightweight
"in-progress-work" board (even just a convention: touch a marker file naming the subsystem you
're about to fix) would generalize the existing per-path single-writer rules to ANY shared
subsystem, not just the three named today.

Related: [[reference_autonomy_gate_override_mechanism]] (what the two sessions built),
[[shared-checkout-cofile-patch-hazard]] (the file-level version of this class of risk).

**RECURRED 2026-07-17 — a related-but-distinct shape, on `open-items-tracker.md`.** Merging a long-lived branch (a 7-workstream ROI-optimization implementation, isolated in a worktree for hours) back into `main` hit the SAME class of collision twice in succession, but this time it was ID-numbering, not file-content: two different concurrent sessions each independently claimed the same next-free `OI-NNN` slot (first `OI-011`, then after a rebase, `OI-012` too) for entirely unrelated findings. Neither session could have known about the other's claim — there's no lock or reservation step for "the next tracker ID," unlike the named single-writer paths (`ora-skills`, scheduled-task registries, `workflows/`). Resolved by re-deriving the true next-free ID fresh at rebase time (never trusting a previously-computed number) and renumbering the weaker/later entry — in one case dropping an entire entry outright because another session's independently-landed closure of the same underlying item was stronger and arrived first. **Confirms the file's own prediction above: this class of collision recurring is exactly the trigger for escalating "in-progress-work" visibility as a systematization candidate** — `open-items-tracker.md` (and likely any shared append-only ID-bearing tracker) needs the same protection ora-skills/scheduled-tasks already have, not just ad-hoc rebase-time discovery. See [[feedback_verify_wip_settled_via_mtime]] for the companion tactical lesson (how to tell settled-but-uncommitted WIP from still-in-flight WIP once you've found a collision).
