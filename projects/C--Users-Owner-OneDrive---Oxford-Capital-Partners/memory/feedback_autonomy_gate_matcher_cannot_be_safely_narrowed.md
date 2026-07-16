---
name: feedback-autonomy-gate-matcher-cannot-be-safely-narrowed
description: "Do NOT attempt to narrow ora-autonomy-gate.py's Gate 2b site-write matcher (require marker+indicator to be related) -- three independent adversarial review rounds each found a real, confirmed bypass in one session, 2026-07-16. The 2026-07-14 broad-match design is correct; leave it."
metadata:
  node_type: memory
  type: feedback
  originSessionId: 1a905dab-bee0-465f-b364-7beeecd61271
---

**Do not narrow `hooks/ora-autonomy-gate.py`'s Gate 2b matcher** (the check that a site-path
marker like `oxford-site` and a write-verb like `cp `/`>` co-occur ANYWHERE in a Bash command,
with no requirement that they be related). This is repeat guidance: the file's own 2026-07-14
comment already documents this as a deliberate design choice, not an oversight. This entry exists
because 2026-07-16 re-litigated it anyway (real friction: the gate false-tripped twice that
session on git commit messages merely mentioning a site word in prose) and, after three rounds of
independent adversarial review, reverted the attempt.

**Why:** the gate is the SOLE enforcement of Hard Invariant 2 (never write to oxfordra.net without
confirmation) under `defaultMode=bypassPermissions`, where no permission prompt exists as a
backstop. Its own stated doctrine: a false negative here means confidential or broken content
reaches a live production site; a false positive only costs a retry. Any narrowing attempt must
hold to a **zero false-negative** bar, not "very unlikely."

**What was tried and why it failed, in order** (each fix closed the PRIOR round's finding and
introduced or left open a NEW one):
1. Unanchored match: stripped `-m "..."` anywhere the substring "git commit" appeared, with no
   requirement the two be related — a real write could hide behind a *different* command's
   quoting that merely contained the literal text `-m "` (`git commit ; echo '-m "' ; cp evil
   oxford-site/y.html ; echo '"'`).
2. Fix 1 (anchor "git commit ... -m" to a command-boundary position) closed that, but a
   **command substitution** `$(...)`/backtick inside a genuine, correctly-anchored double-quoted
   `-m` message executes as real shell code BEFORE git runs (`git commit -m "$(cp evil
   oxford-site/y.html)"`) — the message-is-inert premise itself was false.
3. Fix 2 (refuse to strip a double-quoted message containing `$(`/backtick) closed THAT, but the
   guard was only applied to the double-quote branch — the SAME construct one quoting level
   deeper (`echo "; git commit -m '$(cp evil oxford-site/x.html)'"`, where an outer double-quoted
   context makes the inner `;` and `'...'` behave differently than the regex assumed) still
   executed the write invisibly. Confirmed empirically: the write actually happened (a marker file
   was created) and the gate still returned exit 0.

**The pattern, not just the instances:** each fix was locally correct against the finding that
motivated it, but a flat regex has no way to track bash's actual quoting STATE (what's really
inside single- vs double- vs no-quotes at any given character position) — so "is this text really
inert" is not decidable by pattern-matching alone. There is no reason to expect a fourth attempt
would be the last; this is a structural limit, not a bug count. A real shell-aware parser (proper
tokenizer/AST, not `shlex.split` — which also doesn't match bash's `$()`/heredoc semantics) is the
only way to do this soundly, and is disproportionate engineering for the actual cost (an
occasional git-commit-message retry).

**How to apply:** if this friction recurs, the safe response is a smaller, non-regex-based
narrowing that doesn't try to parse quoting at all — e.g. rephrase the commit message to avoid the
trigger words (what this session did both times, successfully, with zero risk) — never a "smarter
matcher." If a future session is tempted to try again, read this file first; if you still think you
have a sound approach, it needs the SAME three-round adversarial gauntlet (independent
`pr-review-toolkit:code-reviewer` passes, each explicitly told to try to break the PRIOR fix, not
just review the diff) before it may land, and the reviewer should be pointed at this file's history
so it doesn't re-discover the same three holes from scratch.

Related: [[feedback_autonomy_gate_blocks_writes_not_reads]] (the companion guidance on how to
correctly respond to a genuine false-positive block without touching the gate at all).
