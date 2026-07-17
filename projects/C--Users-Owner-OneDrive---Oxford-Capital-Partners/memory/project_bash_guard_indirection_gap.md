---
name: project-bash-guard-indirection-gap
description: "CLOSED 2026-07-17: oxford-command-center's bash-guard.mjs (all 7 blocked command classes) had been defeated by git-alias/wrapper-script indirection -- fixed by resolving both into one expanded text every check scans, landed on main commit 60c45ed after 3 rounds of adversarial review found and fixed real bugs (a detection-breaking git-flag gap, a DoS-class exponential subprocess blowup, a backtracking regex, a quote-handling bug). A concurrent session closed the 2 pre-existing false positives flagged during that review (hooksPath read; cp source-vs-dest) same night, commit 8006a15. Tracked: open-items-tracker.md#OI-010 and #OI-011 (both closed)."
metadata:
  type: project
  originSessionId: 3fc20af9-9fcb-4681-a66a-c6eb07fdd7db
---

**How it was closed (2026-07-17, same session):** landed on `oxford-command-center` `main`,
commit `60c45ed`, via an isolated worktree (`npm install`'d locally, not junctioned) + TDD +
fast-forward merge. Resolves both indirection layers found below into one "expanded" text that
every existing check (a)-(g) scans unchanged: `resolveGitAliases`/`resolveGitAliasesOnce` (git
aliases via `git config --get alias.<name>`, skipping known builtins, recursive with a depth cap),
`resolveAliasDefinitions` + `resolveInlineAliasOverrides` (catches `git config alias.X value` and
one-shot `git -c alias.X=value` definitions directly, not just their later invocation), and
`expandScriptInvocations` (reads the content of any script referenced via `sh`/`bash`/`zsh`/`dash`/
`ksh`/`source`/`.`-invocation, stdin redirection, or direct execution — case-insensitive, quoted
paths with spaces handled — with best-effort `$1`/`$@` positional-parameter AND simple literal
`VAR=value`/`$VAR` substitution inside that content, iterated a few passes for chained/concatenated
variables).

**Three rounds of independent adversarial review** (3 parallel agents — git-alias angle,
wrapper-script angle, architecture/performance/false-positive angle — each personally
re-verified before accepting) found and fixed real bugs before landing:
- Git global options (`-c`/`-C`/`--git-dir=`/`-p`/`--no-pager`) preceding the alias name made the
  original candidate-detection bail out entirely (any leading dash was treated as "not a
  candidate" rather than "skip past this option") — defeated alias resolution broadly, even for a
  plain persisted alias, no other trick needed.
- **DoS-class**: `MAX_ALIAS_DEPTH` bounded recursion depth but not breadth — a handful of
  chained/self-referential aliases (an entirely plausible `.gitconfig` pattern) multiplied
  subprocess spawns exponentially, producing 4.6-7.8s stalls on a hook that fires on every Bash
  call. Fixed via a shared 16-lookup budget across the whole resolution, capping worst-case
  wall-clock regardless of branching.
- **DoS-class**: an unbounded lazy-quantifier-plus-quote-backreference regex in
  `resolveInlineAliasOverrides` cost up to ~10s on a crafted large unterminated-quote payload.
  Fixed via a length bound (`{0,4096}?`), applied consistently to the same shape in
  `resolveAliasDefinitions` and to the pre-existing `sh -c`/`$()`/backtick extraction (whose
  exposure this fix increased, since it now also scans large inlined script content).
- A quote-handling bug: substituting a variable referenced inside double quotes (`"$SUB"`) left
  the quote characters as stale text, making the substituted value look like a quoted STRING
  LITERAL to the downstream commit-message quote-blanking logic — hiding the very thing the
  substitution was supposed to reveal. Fixed by consuming a matched quote pair as one unit.

**Proved several bypasses end-to-end (not just at the hook-logic level) before fixing**: a git
alias genuinely staged an untracked file via `add -A` in a disposable repo (both the plain form
and past a `-c` global-option prefix); a direct-executable wrapper and a variable-built-verb
wrapper (`V=rm; $V -rf <path>`) each genuinely deleted a `data/warehouse` test directory.

**Accepted, documented limits (same architectural ceiling as OI-007):** arbitrary shell constructs
beyond simple literal variable assignment — command substitution `$(...)`, arithmetic, exported/
environment variables, control flow (loops/conditionals/arrays), >3-level nested script wrappers,
scripts over the 64KB read cap, symlinks (untested) — are not resolved. Closing those for real
would need the same architectural shift OI-007 used (verify the actual outbound action/repo state,
not more text patterns), which doesn't fit this hook's "zero-dependency, cheap, fail-open text
scan" design philosophy any more than an override-token system did (see "why this differs from
OI-007's fix pattern" below, still accurate).

**2 unrelated, pre-existing false positives found during review, deliberately NOT fixed here** to
keep this change scoped to the indirection fix — tracked separately at
[open-items-tracker.md#OI-011](open-items-tracker.md#OI-011): `git config --get core.hooksPath` (a
pure read) denied identically to a write; `cp` FROM a guard file (e.g. a benign backup) denied
identically to overwriting it. **Closed same night by a concurrent session**, commit `8006a15` —
full evidence at OI-011 (3 more real bugs found via its own 3-round adversarial pass before landing:
a dash-prefixed hooksPath value, and two missed `cp --target-dir(ectory)` abbreviation forms).

**Verification:** 59 new/updated tests (regression on all 7 original classes + every adversarial
finding above + timing guards locking in both DoS fixes, each asserting completion well under the
regressed multi-second times). Full project suite 231 files/2783 tests green, typecheck 0, lint 0.
Landed via fast-forward merge from the main checkout; before/after `git status` confirmed zero
collateral impact.

---

## Original audit (below, still accurate as history)

**What was asked:** audit `oxford-command-center/.claude/hooks/bash-guard.mjs` for cross-call
splitting, following up on an unconfirmed hypothesis raised while checking that repo for anything
resembling the same-night `ora-autonomy-gate.py` OI-007 indirection work (see
`[[project_autonomy_gate_indirection_ceiling_followup]]`, CLOSED).

**Finding, confirmed empirically:** `bash-guard.mjs` is a fully stateless, per-invocation PreThink
scanner — one JSON payload in on stdin, one deny/allow decision out, zero memory of any prior
invocation (no session directory, no persisted state at all, unlike `ora-autonomy-gate.py`'s
`hooks/sessions/<id>/`). This means any attack that bridges DISK state (not shell state) across two
steps defeats every text-based check in the file, whether the two steps are combined in one
`&&`-joined command or genuinely split across two separate Bash tool invocations — disk persistence
makes the shell-state-doesn't-persist-between-calls question moot entirely.

**Two working patterns, both proven live against the real hook (crafted PreToolUse JSON piped into
`node bash-guard.mjs` via stdin, controls confirmed DENY first):**
1. **Git alias indirection** — `git config alias.qa "add -A"` (step 1) is allowed because the
   literal token `add` never appears as its own array element (it's glued to a quote character in
   the naive whitespace split); `git qa` (step 2) is allowed because it contains neither `add` nor
   `-A`/`--all` anywhere. **Proved end-to-end in a disposable throwaway repo**: `git status --short`
   showed `?? untracked-file.txt` before, `A  untracked-file.txt` after running `git qa` — the alias
   genuinely executed `git add -A` for real. Same pattern confirmed for `git commit --no-verify`
   (alias `qc = "commit --no-verify -m"`) and `git push --force` (alias `qp = "push --force"`) — for
   these two the quoted alias value is blanked to `""` by the guard's own quote-stripping (meant to
   stop commit-message false positives) before the token scan runs, so the alias-definition step is
   invisible to the check even without the token-glue trick.
2. **Wrapper-script indirection (more general — covers non-git checks too)** — write a tiny script
   to disk that embeds the trigger keyword but defers the dangerous argument to `$1`/`$@`
   (`printf 'rm -rf "$1"' > /tmp/w.sh`), then invoke it with the dangerous argument
   (`sh /tmp/w.sh data/warehouse`). Confirmed bypassing: (a) `git add -A`, (e) sqlite3 DDL/DML
   against the live warehouse, (f) `rm` of `data/warehouse`, (g) writes into
   `.claude/settings*.json`/`.claude/hooks/`, and (d) `core.hooksPath` tampering. In every case
   neither the write-the-wrapper step nor the invoke-the-wrapper step contains the literal
   keyword/flag/path combination the check requires, because the guard never reads the *contents*
   of a file a command merely references by path.

**One category resists the alias sub-pattern but not the wrapper sub-pattern:** (d) `core.hooksPath`
is checked via a blunt substring regex against the *whole raw segment* (`/core\.hookspath/i.test(rawSeg)`),
not a token-exact-position match — so `git config alias.x "! git config core.hookspath /tmp/evil"`
IS correctly denied (the trigger substring is literally present in that command's raw text, quotes
or not). But the wrapper-script version (`printf 'git config core.hookspath "$1"' > /tmp/hp.sh` then
`sh /tmp/hp.sh /tmp/evil`) still gets through both steps, for the same reason as the others: the
trigger text lives inside a file the guard never opens.

**Root cause, one sentence:** every check in the file inspects the literal text of the CURRENT
command only, and none of them account for a command that merely *names* something (an alias, a
script path) whose real, disk-persisted definition contains the blocked pattern.

**Why this differs from OI-007's fix pattern:** OI-007 closed by moving enforcement to the actual
outbound action (wrapping the netlify CLI / the Outlook send call itself), using a session-scoped
override-token contract for the *legitimate* bypass case. `bash-guard.mjs`'s own docstring is
explicit that its 7 classes have **NO override sentinel — they are always wrong per doctrine**, so
an override-token architecture doesn't fit here; there is no legitimate case to authorize. The
outbound-action principle still applies, but the natural enforcement point for a git-side action is
git's own hooks (`pre-commit`/`pre-push`), which `oxford-command-center` already partially uses via
`scripts/install-git-hooks.mjs` (a separate, hooks-path-anchored, fail-closed confidentiality
scanner with its own known gap — see below). A PreToolUse text scanner structurally cannot close
this family of gap by adding more regexes; it would need either (a) a git `pre-commit`/`pre-push`
hook that re-checks the *actual* diff/ref state after alias/shell expansion has already happened
(the same principle as OI-007, applied to git's own hook points instead of a wrapped CLI), or (b)
literally executing `git config --get alias.<name>` / resolving the target of any `sh <path>` /
`bash <path>` invocation before deciding, which is a much larger scope change to a hook that is
explicitly designed to be a cheap, zero-dependency, fail-open text scan.

**Not yet fixed — this session only audited and confirmed.** No code changed in
`oxford-command-center`. Decision on whether/how to remediate is Gabriel's: extend git's native
hooks (lower blast radius, fits the "always wrong, no override" doctrine already in place for
`install-git-hooks.mjs`) vs. a larger rewrite of `bash-guard.mjs` itself to resolve indirection
before deciding.

**Related, found the same night but out of scope for this fix:** `scripts/install-git-hooks.mjs` /
`scripts/prepush-confidential-scan.mjs` has a genuinely zero-override-mechanism confidentiality
scanner (finding H1 from the earlier oxford-command-center investigation) that WARNs rather than
blocks when its local `confidential-terms.json` roster is missing — a different, already-known gap,
not re-verified this session.

Related: [[project_autonomy_gate_indirection_ceiling_followup]] (the sibling, CLOSED finding on
`~/.claude`'s gates — same root-cause class, different architecture, different repo).
