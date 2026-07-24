---
name: positive-attribution-over-mtime
description: "When landing a multi-file backlog in a shared checkout, commit only your own touched-set; never infer \"settled\" from mtime quiet periods."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 53f57fbe-7aee-490a-98aa-61f29d5c9aea
  modified: 2026-07-24T16:25:34.641Z
---

Commit only paths you can positively attribute to yourself (your own session's
`hooks/sessions/<sid>/touched-files.txt`, or files you can otherwise name as yours).
Never treat "no writes for N minutes" as evidence a file is abandoned and safe to
sweep into your own commit.

**Why:** On 2026-07-24, before a `git add <41 paths> && git commit` backlog-landing
sweep, the justification given was "tree settled ~10 min, authoring session idle" —
mtime-based. In reality the true gap was 73 seconds, and the session had *deliberately*
deferred an in-flight edit with a stated plan to splice it out later. The sweep
captured it anyway, before the splice could run. Nothing was lost (verified
marker-by-marker), but the reasoning that green-lit the sweep was wrong in kind, not
just wrong in degree — mtime is negative inference about intent, and intent doesn't
live on the filesystem. No threshold fixes this: raising the window just trades a
false-positive for a janitor that never runs, since "quiet" is the identical
observable for a crashed session, one waiting on a person, and one mid-turn thinking.

Separately, `commit-provenance-guard.py` — the hook specifically built to catch this
class of collision — had a real bug (compound `git add X && git commit` blind spot,
confirmed root cause and fixed same day, see event_log 2026-07-24 and
[[reference_commit_provenance_guard]]) that let the same sweep through even though
every other precondition for a block was met. That fix closes the *mechanical*
backstop. This entry is the *behavioral* rule that should hold even when the backstop
is working: don't rely on a guard (or on mtime) to do the judgment a positive-
attribution check would have done for free.

**How to apply:** Before any `git add`/`git commit` that spans more than your own
edits this turn — a "land the backlog" / janitor pass, a cleanup sweep, closing out a
multi-session gap — filter the candidate file list down to paths your own session
actually touched (or that you can otherwise name with certainty, e.g. machine-
generated state files with a known single producer). Land those. For everything else,
*report* what's uncommitted and why, rather than folding it in on an inferred
"probably done" signal. If the backlog genuinely needs landing regardless of
authorship (e.g. clearing a multi-day gap before a push), say so explicitly and
proceed with eyes open — that's a different, defensible decision from mistaking
silence for consent. Group commits by real provenance (own work / other sessions'
finished work / machine-generated state) rather than one flat sweep, so a
mis-attribution is contained to one commit, not smeared across all of them.

Related: [[reference_commit_provenance_guard]] · [[feedback_verify_wip_settled_via_mtime]] · [[reference_event_log_partial_commit_splice]].
