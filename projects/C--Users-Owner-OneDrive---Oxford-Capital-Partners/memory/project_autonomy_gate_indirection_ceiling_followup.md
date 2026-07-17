---
name: project-autonomy-gate-indirection-ceiling-followup
description: "CLOSED 2026-07-17: value/reference indirection (a variable/file-sourced recipient, a renamed netlify binary, splitting a deploy across two Bash calls) used to defeat ora-autonomy-gate.py's Gate 1/2a detection entirely -- fixed via outbound-action checks at the point where a shell has already resolved indirection, not another regex. Email side landed on ~/.claude main; netlify side merged via website-canonical PR #30. Tracked: open-items-tracker.md#OI-007."
metadata:
  type: project
  originSessionId: 3fc20af9-9fcb-4681-a66a-c6eb07fdd7db
---

**What was open:** `hooks/ora-autonomy-gate.py`'s Gate 1 (external email) and Gate 2a (oxfordra.net
prod deploy) could be defeated entirely — no override token even needed — by referring to the
sensitive value/executable indirectly rather than typing it literally in the current command:
a PowerShell variable or `Get-Content`-sourced recipient, string concatenation building
"netlify" inside one command, a renamed/copied netlify binary, an `npm run deploy` wrapper, or
splitting a deploy across two separate Bash tool calls. All proven live during the 2026-07-17
adversarial hardening pass — see `[[reference_autonomy_gate_override_mechanism]]` and the
hook's own docstring ("HONEST LIMIT" section) for the exact reproduction commands.

**Why it was hard:** any detector that parses ONE command's literal text is structurally blind
to this — it was equally true of the code before 2026-07-17's matcher fixes, not a regression
those fixes caused or could have prevented. Closing it for real meant moving enforcement to the
actual outbound action (wrapping the netlify CLI / the Outlook send itself) rather than the
invoking shell command — a different architecture, not a patch to the existing matchers.

**How it was closed (2026-07-17):** two outbound-action checks, each validating the value AFTER
a shell has already resolved any indirection — by that point there is no more text left to
obfuscate, because the shell had to name a real executable and pass real arguments to get there
at all.

- **Email side** (`~/.claude`, landed on `main`): `hooks/lib/email_send_tier.py` +
  `hooks/lib/check_external_send.py`, invoked by `send-via-outlook.ps1` itself right before
  Outlook COM, validating the SAME session-scoped `allow-external-send` token contract Gate 1
  uses. Adversarial review found and fixed 3 real bugs before this landed: a suffix-only
  domain-classification regex that let `attacker@evilhost.com@oxfordra.net` bypass entirely; a
  PowerShell CLI-argument quote-stripping bug that broke the checked/sent value equivalence
  (fixed by moving recipients to stdin); and a UTF-8 BOM handling bug in the shared token parser
  (affects all tiers, fixed with `utf-8-sig`). Verified via 6+ `-WhatIf` dry-run scenarios
  against the live script, including the exact indirection trick that originally defeated Gate 1.
- **Netlify side** (`website-canonical`, [PR #30](https://github.com/ZeOoba/Website/pull/30),
  merged by Gabriel 2026-07-17, merge commit `b25a70d9`): `scripts/netlify-guard.js` +
  `scripts/patch-netlify-shim.js`, a `postinstall` hook that patches
  `node_modules/.bin/netlify(.cmd/.ps1)` to route through the guard on every install (npm
  regenerates those shims from its own template each time, so a one-off edit wouldn't survive).
  Adversarial review found and fixed 2 real bugs before the PR: an exact-array-element argv
  check that let `--prod=true` and the documented `--prod-if-unlocked` flag bypass authorization
  completely; and a postinstall patcher that silently exited 0 even when zero shims were
  patched (fixed to fail the install loudly instead). Verified via the wrapper's own dry-run
  switch across 9+ scenarios, plus a real `npm install` proving the postinstall hook re-patches
  a reverted shim.

**Known residual gap, not fixed (low priority, flagged in the PR):** invoking the netlify CLI
from OUTSIDE website-canonical's directory tree resolves a separate, unguarded copy via npm's
global/registry fallback — the wrapper protects the local `node_modules` tree, not the `netlify`
command globally. Revisit if this ever becomes a real vector (would need a machine-wide PATH
shim rather than a per-repo postinstall hook).

Related: [[reference_autonomy_gate_override_mechanism]] (the token mechanism these checks build
on), [[feedback_autonomy_gate_matcher_cannot_be_safely_narrowed]] (the sibling constraint on NOT
narrowing Gate 2b's breadth — a different, orthogonal problem, never touched by this work).
