# Write-Guard Architecture Hardening — Build + REFUTE Evidence (2026-07-18)

Plan 5 of 5. Branch `write-guard-hardening-2026-07-18` (isolated worktree at
`.claude/worktrees/write-guard-hardening-2026-07-18`, cut from main @ e032134).
**NOT LANDED — awaiting Gabriel's explicit approval before any merge.**

Compatibility with `systematization-candidates` (checked first): that branch adds an
`OVERRIDE_DIR` env test seam to `ora-autonomy-gate.py`, OVERRIDE_DIR-isolation tests
to `test-ora-autonomy-gate.py`, and untracks `maintenance/_state/doctrine-status.json`
via `.gitignore`. This branch touches NONE of those four files — no overlap, no
conflict with its untracked-`_state` direction.

## Files

| File | Change |
|---|---|
| `hooks/lib/tool_call_paths.py` | NEW — single source of write-capable tool-call shape knowledge (native Write/Edit/MultiEdit/NotebookEdit; DC write_file/edit_block/move_file/write_pdf; shell via Bash/start_process/interact_with_process; suffix-family MCP recognition; decoy double-field defense; honest unresolved-shell flagging; SHAPES registry for the meta-test) |
| `hooks/memory-index-guard.py` | Refactored onto the shared layer; behavior-preserving (verbatim-fallback on lib failure); existing tests pass unmodified |
| `hooks/registry-write-guard.py` | Same refactor, same contract |
| `hooks/config-write-guard.py` | NEW — hard write-gate over `hooks/**` (minus `sessions/`, `state/`), `settings.json`, `settings.local.json`, `CLAUDE.md`, both fleet registry JSONs; override via the EXISTING `lib/override_tokens.py` tier `allow-config-write` (scope `config-write`, 60 min, multi-use); chip claim-lock over `handoffs/**` + `workflows/**`, fail-open + TTL per ratified doctrine; exit 0/2 only |
| `hooks/tests/test-tool-call-paths.py` | NEW — 106 PASS cases (TDD, written before the lib) |
| `hooks/tests/test-config-write-guard.py` | NEW — 78 PASS cases (TDD, written before the hook), incl. REFUTE regressions |
| `hooks/tests/test-write-guard-coverage.py` | NEW — 85 PASS cases: SHAPES x guard matrix + settings.json matcher routing cross-check |
| `settings.json` | Registers config-write-guard (PreToolUse) with matcher `Edit\|Write\|MultiEdit\|NotebookEdit\|Bash\|mcp__excel__.*\|mcp__.*(write_file\|edit_block\|move_file\|start_process\|interact_with_process\|write_pdf)` — worktree copy only; takes effect only if merged |

## Test evidence

Command: run every `hooks/tests/test-*.py` under the worktree; full per-suite output in
`docs/2026-07-18_write-guard-hardening_full-suite-output.txt`.

**Result: 27/28 suites pass.** The single failure is `test-confidentiality-guard.py`,
which is ENVIRONMENTAL: it requires the live `hooks/confidential-terms.json`, which is
deliberately untracked (invariant 3) and therefore absent from every fresh worktree.
Both that test and `confidentiality-guard.py` are byte-identical to main on this
branch (`git diff main --stat` empty for both), and the same test run from the live
checkout (where the terms file exists) prints
`ALL PASS -- guard blocks every derived variant on every egress surface...`.

Meta-test falsification proof (step 6 mandate): with the DC handling in
`registry-write-guard.py` temporarily replaced by native-only `file_path` parsing,
`test-write-guard-coverage.py` went red with
`FAIL registry-write-guard.py fires for shape dc-write-file` (+ the plugin-prefix
twin); restored, green again.

## Adversarial REFUTE pass (mandatory; security-gate code)

### (a) Shape bypasses — 5 found, 5 fixed, all live-proven then regression-locked

Each probe reached exit 0 against a blocked control before its fix:

1. **DC `write_pdf` onto a hook** — not a modeled shape. Fixed: write_pdf is now a
   file shape in the lib (path/file_path/output_path fields).
2. **Excel MCP writer onto `settings.json`** (`mcp__excel__write_data_to_excel`,
   `filepath` field) — outside the shape registry entirely. Fixed: generic
   path-field scan in the gate for routed-but-unshaped tools (deny-by-default,
   same direction as ora-autonomy-gate check_mcp's Round-3 fix) + `mcp__excel__.*`
   added to the matcher.
3. **Hypothetical third DC tool-name prefix** (`mcp__desktop-commander-v2__write_file`)
   — the exact-name allowlists would re-open the 2026-07-14 gap on any connector
   rename. Fixed: suffix-family recognition (`mcp__*` + known writer suffix), and
   the settings matcher uses the same suffix form. This deliberately does NOT
   repeat the narrowing mistake documented in
   `feedback_autonomy_gate_matcher_cannot_be_safely_narrowed.md` — every change in
   this pass WIDENS detection.
4. **`git -C ~/.claude checkout main -- hooks/`** — rewrites the live governance
   layer with no classic write verb; a literal "git checkout" indicator ALSO missed
   it (verb not adjacent to `git`). Fixed: `GIT_MUTATE_RE` (git + same-segment
   mutating verb) + governance-root-mention rule. Controls verified: read-only git
   on the live checkout allows; mutating git inside a worktree allows (whole-token
   exempt blanking so a worktree path contributes nothing, not even its root
   prefix).
5. **PowerShell `Move-Item` onto `settings.json`** — `"move "` never matches
   `move-item`. Fixed: `move-item`/`copy-item`/`rename-item` indicators.

Bonus finding during the behavior-preservation work: a **decoy double-field payload**
(DC write_file with innocent `file_path` + gated `path`) could steer a single-path
check onto the decoy. `write_targets()` now emits a target per distinct candidate
path; the gate blocks on any of them (regression-tested).

### (b) Self-deadlock — none; probed live

- The override token lives at `hooks/sessions/<sid>/overrides/` → `hooks/sessions/**`
  and `hooks/state/**` are exempt from the gate (file-tool AND shell paths both
  tested: token minting via Write and via Bash echo both allow, while a gated write
  in the same environment still blocks).
- `chip-claims.log` sits at the root, outside every protected set — appending
  CLAIMED/HEARTBEAT/DONE lines is never gated (tested).
- The eos-plan-gate `hooks/sessions/<sid>/override` marker is likewise exempt.
- The gate only READS its dependencies (override token, claims log, lib modules);
  it gates writes to `hooks/lib/**` — and pleasingly, deleting/breaking
  `tool_call_paths.py` to disable the gate is itself a gated write.
- The retired flat `hooks/overrides/` dir has NO live consumers (grep: docstring
  history only), so leaving it inside the gated zone is correct — the retired
  sentinel scheme stays dead.
- Import-failure posture: hook copied to a directory with no `lib/` → exit 0
  (inert, status-quo), never exit 1 (which would be non-blocking anyway) and never
  a session-bricking block — the exact lesson of
  `reference_pretooluse_vs_git_hook_exit_codes.md` and the confidentiality-guard
  self-deadlock precedent.

### (c) Fail-open under malformed input — all constructed cases pass

Probed live and regression-tested: missing log; empty log; truncated line;
non-UTF-8 log bytes; empty stdin; malformed JSON; non-dict payload; **non-UTF-8
stdin bytes** (stdin is read via `sys.stdin.buffer.read().decode("utf-8")`, immune
to the documented cp1252 harness gap —
`reference_windows_hook_stdin_cp1252_encoding_gap.md`); `tool_input` not a dict;
Bash `command` as a list. All exit 0. A dedicated test asserts the exit code is
only ever 0 or 2.

### (d) Claim-lock race window — accepted per ratified doctrine, documented

TOCTOU exists (a claim can be ABORTED between check and write; two sessions holding
different open claims can write the same handoff file). This is deliberate:
`feedback_fail_open_over_mutex_for_fleet_gates` is Gabriel's explicit rejection of
hard mutexes for cross-session coordination — a wedged claim would be a fleet-wide
outage across 8-14+ concurrent sessions. The lock's job is making uncoordinated
writes LOUD and self-recoverable (the block message gives the exact CLAIMED line to
append), not making them impossible. Staleness follows rules.md §8 exactly: latest
CLAIMED-or-HEARTBEAT < 60 min, closed by any later DONE/ABORTED.

### Honest limits (documented, deliberately not "fixed")

- **Value indirection** (`$d='...ho'+'oks'; echo x > $d/g.py`) passes — proven live,
  same structural ceiling as ora-autonomy-gate's HONEST LIMIT; closing it requires
  enforcement at the outbound action, not better text matching.
- **Worktree copies are ungated by design** — the sanctioned dev path. Residual
  risk: a merge into the live checkout is a git operation; the git-mutating rule
  above now gates checkout/merge/etc. aimed at `~/.claude`, so even the merge step
  needs the token or a human at the wheel.
- **Token self-minting**: the gate cannot distinguish a Gabriel-approved token from
  a self-granted one (override_tokens.py's documented limit (a)). It converts a
  silent edit into an auditable, deliberate act; it is not authentication.
- **Claim "matching-enough title"**: implemented as SESSION-identity matching
  (full id or first-8 substring in the claim's surface/session field) rather than
  fuzzy title matching — a file being written carries no chip title to match
  against, and session attribution is the robust signal the log actually encodes.
- Headless payloads with no `session_id`: claim-lock fails open (cannot attribute);
  the governance token-gate still fails CLOSED (no token reachable).

## Suggested follow-ups (not built; candidates for separate chips)

1. Extend `ora-autonomy-gate.py`'s site-tree Gate 2b onto `tool_call_paths.py` so
   DC move_file/write_pdf into the site tree are covered there too (it currently
   models FILE_TOOLS + Bash + MCP names only).
2. `rules.md` §10 still describes the RETIRED flat `hooks/overrides` sentinel
   protocol — stale doctrine; update to the session-scoped token contract.
3. Consider adding `mcp__excel__.*`-class routing to the two legacy guards'
   matchers once their behavior-preservation freeze is lifted.
