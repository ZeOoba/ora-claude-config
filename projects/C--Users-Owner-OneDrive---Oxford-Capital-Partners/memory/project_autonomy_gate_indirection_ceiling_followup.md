---
name: project-autonomy-gate-indirection-ceiling-followup
description: "OPEN follow-up (Gabriel-scoped 2026-07-17): value/reference indirection (a variable/file-sourced recipient, a renamed netlify binary, splitting a deploy across two Bash calls) defeats ora-autonomy-gate.py's Gate 1/2a detection entirely, and cannot be closed by better regexes -- real fix needs enforcement at the actual outbound action, not the invoking shell command. Tracked: open-items-tracker.md#OI-007."
metadata:
  type: project
  originSessionId: 3fc20af9-9fcb-4681-a66a-c6eb07fdd7db
---

**What's open:** `hooks/ora-autonomy-gate.py`'s Gate 1 (external email) and Gate 2a (oxfordra.net
prod deploy) can be defeated entirely — no override token even needed — by referring to the
sensitive value/executable indirectly rather than typing it literally in the current command:
a PowerShell variable or `Get-Content`-sourced recipient, string concatenation building
"netlify" inside one command, a renamed/copied netlify binary, an `npm run deploy` wrapper, or
splitting a deploy across two separate Bash tool calls (build the executable reference in one,
invoke `deploy --prod` via that reference in a second). All proven live during the 2026-07-17
adversarial hardening pass — see `[[reference_autonomy_gate_override_mechanism]]` and the
hook's own docstring ("HONEST LIMIT" section) for the exact reproduction commands.

**Why:** any detector that parses ONE command's literal text is structurally blind to this —
it was equally true of the code before 2026-07-17's fixes, not a regression those fixes caused
or could have prevented. Closing it for real means moving enforcement to the actual outbound
action (wrapping the Netlify CLI/API call or the Outlook send itself) rather than the invoking
shell command — a different architecture, not a patch to the existing matchers.

**How to apply:** do not attempt another regex/matcher tweak for this — Gabriel explicitly
chose "scope a real fix as separate follow-up work" over further patching on 2026-07-17. When
picked up, the design question is where to intercept: wrapping `netlify`/`send-via-outlook.ps1`
themselves (a thin proxy binary that enforces the same override-token contract at the point of
actual execution), vs. some other outbound-action interception point. Read
`hooks/lib/override_tokens.py` first — the token-validation contract this would still need to
call into already exists and is solid; only the interception POINT needs to change.

Related: [[reference_autonomy_gate_override_mechanism]] (the mechanism this gap sits alongside),
[[feedback_autonomy_gate_matcher_cannot_be_safely_narrowed]] (the sibling constraint on NOT
narrowing Gate 2b's breadth — this is a different, orthogonal problem).
