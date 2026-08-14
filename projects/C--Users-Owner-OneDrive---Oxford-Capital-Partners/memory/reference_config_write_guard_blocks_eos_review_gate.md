---
name: reference-config-write-guard-blocks-eos-review-gate
description: "The eos-review-gate deadlock was a substring bug — \"del \" matched inside \"--model \" — NOT a missing carve-out; fixed 2026-08-03"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 83715320-ea98-4ae2-8ebd-e3ec6f2163dd
  modified: 2026-08-04T01:18:49.561Z
---

**CORRECTED 2026-08-03 (same day it was written).** The first version of this file said the deadlock needed a `hooks/sessions/**` carve-out in `config-write-guard`. **That was wrong twice over:** the carve-out already existed, and the real cause was elsewhere. Recorded here because the wrong diagnosis is the more likely one to be re-derived.

## What actually happened

`SHELL_WRITE_INDICATORS` in `hooks/lib/tool_call_paths.py` matched **bare substrings**, so `"del "` fired from inside `"--model "`. `eos-review-gate.py --record ... --model <id>` therefore read as a write to the governance layer, and `config-write-guard` blocked the only sanctioned way to satisfy `eos-review-gate`. Same class: `"dd "` inside `"git add "`, `"rm "` inside `"confirm "`, `"ren "` inside `"children "`.

A false positive that forces a strictly **broader** privilege is a security regression, not caution — the documented exit was minting `allow-config-write`: 60 minutes of multi-use write access to the whole governance layer, to permit one single-file write.

## Fixed

Word-boundary anchoring, `(?<![\w-])(?:verb)\s`, on branch `claude/guard-ergonomics`. Verified against the live guard: `--record ... --model <id>` BLOCK → ALLOW, while `del <guard>` and `echo x > <guard>` stay BLOCK.

**The first draft of that fix shipped a security regression** — anchoring removed *accidental* coverage of composite writers (`copy ` inside robocopy/xcopy, `cp ` inside scp/rcp/pscp, git-rm/git-mv), un-flagging 7 real writes. `robocopy.EXE`/`xcopy.EXE`/`scp.EXE` are present on this box and `robocopy <src> <hooks> /MIR` **mirrors — deletes and replaces the whole tree**. Now named explicitly as unbounded indicators. The lesson is in EOS spec §7.9: **when narrowing a matcher, enumerate the collision class mechanically, not from memory.**

## Still true, and useful

- `hooks/sessions/**`, `hooks/state/**`, `hooks/active-work/**` and `<root>/worktrees` **are** exempt from `config-write-guard`, at both the tool-path and command-text layers.
- `--key` is read-shaped and never blocked.
- A **relative** path invocation from a worktree is not blocked — the markers are `<root>/hooks`, `~/.claude/hooks`, `.claude/hooks`, and a bare `hooks/...` matches none. This is the audit-complete way to record a review without any token, and it is what actually landed the fix.
- Never route around the matcher by obfuscating a path (`cygpath`, `$HOME`, variables). That is evasion of a security guard. Reshaping a command so it no longer *names* the tree is legitimate ONLY when the target genuinely is a blessed worktree and the effect is identical.

## Hardening candidates — BOTH CLOSED 2026-08-03 ([PR #35](https://github.com/ZeOoba/ora-claude-config/pull/35))

1. **Quoted verbs** — closed. Justified by bash `"rm" f` and PowerShell `& 'del' x`, both **executed** to confirm. NOT by `del"x"`, which concatenates to `delx` and executes in no shell — that was fiction in the original comment and was removed along with the test pinning it.
2. **Tab-separated composite writers** — closed; composites moved from literal-space substrings into a regex sharing the separator class.
3. **Found during that review, larger than either**: cmd.exe treats `,` `;` `=` as token delimiters exactly like `/`. `del,f` / `del;f` / `del=f` were each proven via a `.bat` harness to **actually delete a file**, and `rm<f` executes in bash. The `/`-only fix had closed one third of the class it claimed to close.

Separator class is now `[\s"'/,;=<]`. Safe because widening a character class is **strictly broadening** — `shell_may_write` is a pure disjunction of monotone predicates and the only negation sits in an untouched regex, so an enlarged disjunct cannot turn True into False. That is the structural reason this could not repeat the `robocopy` regression; the 323k sampled commands corroborate it rather than establish it.

**Cost, accepted:** 19 false positives across 107 probed benign commands — quoted/regex text · env-var assignment prefixes (`make clean RM=del`; RM/CP/DD are GNU make built-ins) · command chaining. All require a governance-path marker too, and every governance operation with no ungated substitute still allows.

**Residual ceiling, unchanged:** value indirection (`$IFS`, variables) — a static text matcher cannot resolve it.

Related: [[reference-lane-telemetry-records-are-not-sessions]] · [[feedback_confidentiality_guard_selfdeadlock]] · [[feedback_autonomy_gate_matcher_cannot_be_safely_narrowed]]
