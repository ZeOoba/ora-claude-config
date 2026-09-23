---
name: feedback-autonomy-gate-matcher-cannot-be-safely-narrowed
description: "Do NOT attempt to narrow ora-autonomy-gate.py's Gate 2b site-write matcher -- FOUR independent attempts (2026-07-16 x3, 2026-08-13 x1) each found a real, confirmed bypass, the 4th using a REAL shell tokenizer (not a regex) and still failing on a DIFFERENT, more fundamental problem: quoted text is not inert, it's still a command argument. The 2026-07-14 broad-match design is correct; leave it."
metadata:
  node_type: memory
  type: feedback
  originSessionId: 1a905dab-bee0-465f-b364-7beeecd61271
  modified: 2026-08-14T00:06:05.895Z
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

---

## Round 4 (2026-08-13): a REAL shell tokenizer was built and adversarially killed on Round 1 -- a NEW, more fundamental failure mode, not a repeat of 1-3

Context: [OI-147](open-items-tracker-history.md#OI-147), an [[external-artifact-intake]] evaluation of the
external ECC repo, ratified adopting the SHELL-PARSING TECHNIQUE from its `gateguard-fact-force.js`
(quote/subshell-aware tokenizer) specifically because this file's own line 45-48 conclusion --
"a real shell-aware parser... is the only way to do this soundly, and is disproportionate
engineering" -- read differently once an existing, tested implementation was available to adapt
rather than build from scratch. `hooks/lib/shell_tokenizer.py` was built: a genuine recursive-
descent scanner correctly tracking single/double-quote state and `$()`/backtick command
substitution at every nesting depth (unlike rounds 1-3's flat regexes). It correctly classified
ALL THREE historical bypass commands above as dangerous, passed a full mutation battery (6/8
killed, 2 proven equivalent/safe-direction), and was integrated as a DOWNGRADE-ONLY layer (narrows
a marker/indicator from "present" to "absent" ONLY when the tokenizer can fully parse the command
AND prove every occurrence sits in text with no live substitution touching it; any parse
uncertainty falls back to exactly today's broad match). All 72 tests (66 original + 6 new,
including all three historical bypasses run through the FULL integrated hook) passed. It was then
killed in Round 1 of the mandated adversarial gauntlet, before Rounds 2-3 were even needed --
the design was not patchable, only discardable.

**The new failure mode, and why it is CATEGORICALLY different from rounds 1-3:** rounds 1-3 were
all bugs in tracking WHICH characters are live vs quote-suppressed -- a real question a real
tokenizer answers correctly. Round 4's tokenizer answered that question correctly and it did not
matter, because **quoting suppresses metacharacter interpretation, it does not remove text from
the command's argument vector.** `cp evil.html 'oxford-site/index.html'` is a completely ordinary,
extremely common shell idiom -- quoting a path operand -- and the site marker sitting inside those
quotes is not "inert prose", it is the literal write target. The tokenizer confidently (ok=True)
classified it as fully inert and the narrowed gate returned exit 0; the file was verified as
actually written in a sandbox. The same false-negative class covered every quoted-argument form
(`"..."`, `'...'`) and every interpreter-wrapper indirection (`bash -c "..."`, `powershell -Command
"..."`, `eval "..."`, `sh -c '...'`, `ssh box "..."`, nested `bash -c "bash -c '...'"` ), because in
every case the tokenizer correctly reports "no live substitution here" while the shell still reads
the quoted text as a real operand or program. A SEPARATE regression (also found Round 1, also
would have needed fixing even if the above were somehow acceptable): `classify()`'s recursive
descent has no depth cap, so a comment-embedded `$(` bomb (`# $($($(...` x1500) throws
`RecursionError`, which `main()` has no outer `try/except` for -- the process exits 1, which this
file's own module docstring already documents as NON-BLOCKING, so the crash doesn't just skip the
narrowing, it disables the WHOLE gate (Gates 1 and 2a still ran first and still worked; Gate 2b did
not run at all). An attacker-triggerable crash of a hard-invariant's sole enforcement is strictly
worse than a narrowing false negative.

**Why this generalizes, and why a 5th attempt at the SAME approach will fail the same way:**
distinguishing "a quoted mention in a commit message" (safe to narrow) from "a quoted path argument
to `cp`" (not safe) requires knowing, per argument, *which command consumes it and whether that
command writes* -- i.e. a model of shell COMMAND SEMANTICS (argv parsing per invoked command, at
minimum), not shell QUOTING STATE. That is a strictly larger, different problem than the one this
file already ruled disproportionate for rounds 1-3, and no improvement to quote/substitution
tracking closes it -- the parser answers a different question than the gate asks. The `feedback_
autonomy_gate_blocks_writes_not_reads` response (rephrase to avoid the trigger words) remains the
correct answer to the friction case; do not reach for tokenizer depth as the fix.

**What survived from this attempt: nothing landed.** `hooks/lib/shell_tokenizer.py` and its test
file were deleted; `ora-autonomy-gate.py`'s Gate 2b is unchanged (`git checkout --` reverted the
integration cleanly, uncommitted). [OI-147](open-items-tracker-history.md#OI-147) closed as REJECTED with
this file as the evidence trail. If a 5th attempt is tempted: the bar is not "build a better
parser" -- it is "model which shell command consumes each argument and whether that command
writes", which is a different and larger engineering problem, not a deeper version of this one.
