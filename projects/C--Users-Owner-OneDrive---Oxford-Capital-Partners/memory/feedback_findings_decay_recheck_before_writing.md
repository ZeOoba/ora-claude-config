---
name: findings-decay-recheck-before-writing
description: "Under concurrent sessions a finding has a shelf life of minutes — re-verify immediately before the WRITE, not just before the conclusion; and prefer waiting, because the condition frequently resolves itself and the write turns out to be unnecessary or actively harmful (4/4 on 2026-08-03)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ebb67ffe-c6aa-4b85-aeff-a2edf57cf1eb
  modified: 2026-09-07T16:29:08.577Z
---

A read is evidence about a moment, not a fact. With several sessions live on
`~/.claude` and `ora-skills`, a finding can be false within a minute or two of
being true — so **the check that licenses a write must be the one taken
immediately before the write**, not the earlier one that produced the
conclusion.

**Why:** on 2026-08-03, four separate findings decayed between observation and
action. In every case waiting beat intervening, and in every case acting on the
older read would have caused damage rather than fixed anything.

| Finding | What the later re-check showed |
|---|---|
| ora-skills merge conflict "being resolved by another session" | They had **aborted**, not finished — `MERGE_HEAD` gone but HEAD never advanced |
| MAX_PATH false positive in `skill_drifted()`, about to be fixed | Another session had **claimed it 12 min earlier** and was mid-edit in the file |
| `open-items-tracker.md` OI-061 collision, "committed defect" | HEAD had **one** OI-061; the second was another session's **uncommitted** WIP |
| Dropped ora-pm appsec item, "vanished — file it fresh" | Already re-filed as **OI-063**, more completely than the version I'd captured |

**The last one is the sharpest.** Searching for the item genuinely returned
nothing — the tracker's max id was OI-062 at that moment and OI-065 by the time
the claim was taken. The search wasn't faulty; the file moved under it. Filing
"the lost item" would have created a duplicate of the very item the loss was
feared for — the exact failure the ID-collision checker exists to catch.

**How to apply:**

1. **Re-read state in the same tool call that acts on it**, or immediately
   before. Never carry a conclusion across several turns of investigation and
   then write on it — investigation takes minutes, and minutes are the decay
   window.
2. **Prefer waiting to intervening.** If the condition is one another session is
   plausibly mid-way through (a merge, a conflicted file, a half-filed tracker
   item), waiting costs a re-check and frequently costs nothing else, because it
   resolves itself. Intervening costs a collision.
3. **Distinguish "the problem is gone" from "the problem is resolved."** They
   look identical from a file-state view. An aborted merge and a completed merge
   both clear `MERGE_HEAD`; only HEAD failing to advance distinguishes them. A
   wait condition must assert the **goal** state, not the absence of the
   intermediate one — see [[verify-wip-settled-via-mtime]].
4. **When a search comes back empty on a shared file, treat empty as
   provisional.** Re-run it right before acting, and prefer a claim +
   re-check over a write built on the first result.

**The inverse failure — a re-enumerated BATCH sweeps in new arrivals
(2026-09-07).** Rule 1 says re-read immediately before the write. That is right
for a *condition*, and wrong for a *file set*. Archiving 26 loose scratch files
from `ora-skills/_staging/`, the inventory was taken at 11:52 and the move
re-globbed `find _staging -maxdepth 1 -type f` at 12:02 — by which time another
live session had written two new files (12:00, 12:01). The fresh glob dutifully
included them and both were archived out from under a running session; caught
only because the moved count (28) did not match the reviewed count (26), and
restored immediately.

So: **for a batch operation, act on the reviewed inventory — an explicit list —
not on a glob re-run at write time.** Re-enumerating is the correct instinct for
"is this still true?" and the wrong one for "which files did I decide to move?"
The cheap safeguard is the one that worked: **assert the acted-on count against
the reviewed count**, and treat any mismatch as a stop, not a rounding error.
Corollary: an explicit skip-list (the live `PENDING_REIMPORT.md` ledger and
`reimport-baselines/` were correctly protected) only guards what you already knew
about — it cannot protect a file that did not exist when you wrote the list.

**Not a counsel of paralysis.** This applies to writes into *shared,
concurrently-edited* surfaces — `open-items-tracker.md`, `event_log.md`,
`MEMORY.md`, `ora-skills` SKILL.mds, `hooks/**`. Work in an isolated worktree or
on this session's own artifacts does not decay this way and needs no re-check
ritual.

Related: [[concurrent-session-duplicate-hardening-work]] (claim before starting;
re-derive next-free IDs fresh) · [[verify-wip-settled-via-mtime]] (is *their*
WIP settled — this file is about whether *your finding* is still true) ·
[[verify-probe-findings-before-acting]] (a probe finding is a hypothesis) ·
[[verify-before-repeating-session-claims]] (check ground truth before relaying).
