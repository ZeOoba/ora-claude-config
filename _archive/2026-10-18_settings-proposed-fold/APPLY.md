# Applying the hooks-audit settings proposal (branch feat/hooks-audit-0930)

> **Status: APPLIED (R-02, Gabriel's decision 2026-10-18).** Step 4 ran on the
> "state pending, sha256 DIFFERS" branch: the proposal was rendered onto the
> then-current `settings.json` (blob c30368ef, origin/main c9242c2a), not copied
> from this folder's stale `settings.json`. This folder was `_proposed/`; it is
> kept here as the record. Its `settings.json` / `settings.diff` are the
> 1370b41-based renderings and do NOT equal the applied file.

`_proposed/settings.json` is the full proposed file. `_proposed/settings.diff` is the
unified diff against live `settings.json` at 1370b41. Both are RENDERINGS of the
proposal, which is defined as code in `hooks/tests/lib/settings_proposal.py`
(`apply()`). test-matcher-coverage.py asserts the artifact and the code agree
byte-for-byte. The live file and the tracked copy at 1370b41 were identical when this
was generated: LF-normalized sha256
`02729fffb3d43ef3ef7239e782e5373fc233cabe2185667db4eaa67448fa7a06` (the
CRLF-on-disk bytes hash to `ed223ed4...`).

**Correction to the brief:** `settings.json` IS git-tracked (blob 93c8c15, re-included by
`!/settings.json` in .gitignore). This branch deliberately leaves the tracked copy
untouched and puts the proposal here, as instructed. Merging the branch therefore does
NOT change `settings.json`. The proposal is applied as a separate, explicit step.

## What the proposal changes

PostToolUse (9 entries become 6):
- **Removed:** the Bash `catch_up_main.py --hook` entry, the inline Bash deploy-grep
  curl, the inline Netlify-updater curl, and the Bash `eos-gate-sentinel.py` entry.
- **Added** as the first entry: matcher `Bash` runs `hooks/posttooluse-dispatcher.py`
  with `timeout: 360`. It runs catch_up (only on `gh pr merge`) and eos-gate-sentinel,
  each under its original matcher. The inline Netlify-updater curl hook is deleted,
  not folded (Gabriel, 2026-09-30). All three `*-updater` tools are in
  `permissions.deny`, so it could never fire, and no Netlify tool gains a
  PostToolUse hook.
- **Unchanged:** fleet-session-hook (matcher still
  `Bash|Task|TaskCreate|TaskUpdate|Edit|Write|MultiEdit`, async; Task 2c was withheld),
  eos-plan-marker, commit-provenance-recorder, memory-nag-correction and
  scheduled-task-update-postguard.

PreToolUse (11 entries become 12):
- **Added** after the registry-write-guard entry: the Desktop Commander
  write_file/edit_block twins run `hooks/ascii-only-guard.py`. The Edit and Write side
  is covered by GUARD_CHAIN in the dispatcher, not by a settings entry.
- **Untouched:** the confidentiality-guard matcher (Task 1, Fable tier) and the inline
  Edit|Write sensitive-file blocker.

## Landing order (hook files first, then settings)

This follows the rule in the pretooluse-dispatcher.py header: a settings file must
never name a hook that the live hooks dir does not have yet.

1. **Review gate.** The branch commits already carry the recorded independent-review
   artifacts. Merge the PR on GitHub only after the review verdict is in place.
2. **Land the hook files in the live checkout.** Pull or fast-forward main in
   `~/.claude` so these files exist in the live `hooks/`:
   - `hooks/posttooluse-dispatcher.py`
   - `hooks/lib/guard_telemetry.py`
   - `hooks/guard-telemetry-summary.py`
   - `hooks/pretooluse-dispatcher.py` (adds ascii-only-guard to GUARD_CHAIN, plus
     telemetry)
   - `hooks/ascii-only-guard.py` (docstring only)

   The last two take effect as soon as they land, because the existing Edit|Write
   dispatcher entry already runs GUARD_CHAIN. That is safe without step 4.
3. **Verify in the live checkout before you touch settings:**
   ```
   python hooks/pretooluse-dispatcher.py --selfcheck          # both chains OK, ascii-only-guard last in editwrite
   echo {} | python hooks/posttooluse-dispatcher.py; echo rc=$?   # prints nothing, rc=0
   python hooks/tests/test-posttooluse-dispatcher.py
   python hooks/tests/test-matcher-coverage.py
   python hooks/tests/test-write-guard-coverage.py
   ```
   These pass BEFORE the apply. They read the tracked `settings.json` (state
   `pending`) and apply the proposal in memory. They never read `_proposed/` as a
   stand-in.
4. **Apply settings. Check first, never blind-replace.** Other sessions edit
   `settings.json`, so the file may have moved since 1370b41.
   ```
   python hooks/tests/lib/settings_proposal.py --status settings.json
   ```
   - **`state: pending` and sha256 MATCHES:** the live file is still the one the
     proposal was authored on. Back it up to `archive/` (never delete). Then either
     copy `_proposed/settings.json` over it, or render it fresh. Both are identical.
   - **`state: pending` and sha256 DIFFERS FROM:** someone changed settings since
     1370b41. Do NOT copy `_proposed/settings.json`, because that would silently revert
     their edits. Render the proposal onto the CURRENT file instead:
     ```
     python hooks/tests/lib/settings_proposal.py --render settings.json <scratch>/settings.new.json
     ```
     The renderer never writes in place. Diff `<scratch>/settings.new.json` against
     live. The only changes must be the four removed PostToolUse entries, the one
     added dispatcher entry and the one added ascii DC entry. Back up live to
     `archive/`, then install the rendered file.
   - **`state: partial` or `applied`, or `--render` raises ProposalError:** ABORT.
     Someone half-applied or re-shaped the relevant entries. Reconcile by hand, and
     re-run the three tests from step 3. They fail loudly on a partial state.

   Commit it as its own blast-radius commit. That commit needs its own review
   artifact, because eos-review-gate keys on `settings.json`.
5. **Move `_proposed/` to `archive/`** in the same commit. `_proposed/` is tracked
   (`!/_proposed/` in .gitignore), so this is a `git mv`. After the apply,
   `settings_proposal.state(settings.json)` is `applied` and the tests judge the
   real file as-is. test-matcher-coverage.py's D2 artifact check and
   test-posttooluse-dispatcher.py's E0 frozen-baseline check then report SKIP. That
   is expected: the frozen pre-change table remains the record.
6. **Post-apply smoke test** in a fresh session:
   - Run any Bash command. `hooks/_state/guard-telemetry.jsonl` gains `chain: "bash"`
     records and one `chain: "post"` record per post hook, with catch-up-main
     `skipped`.
   - Run `python hooks/guard-telemetry-summary.py`.

## Accepted residuals (review rounds 1-3)

- **Telemetry stale-lock TOCTOU.** Two processes can both judge the rotation lock
  stale in the same instant. The worst case is one extra rotation of an
  under-threshold log. It is telemetry-only and never affects a guard decision.
- **Non-folded PostToolUse hooks are not presence-checked.** The tests assert that
  the proposal leaves every non-folded hook exactly as live has it (E1b), but not
  that any particular one exists. Removing fleet-session-hook or
  commit-provenance-recorder from settings.json is outside this branch's tests; those
  hooks' own tests and doctrine-integrity-probe cover their wiring.
- **After the apply, `applied` is judged structurally.** One dispatcher entry and one
  ascii entry must exist, and no folded entry may remain. Their content is judged by
  E3-E7, R1, A3 and the write-guard routing checks. That means routine edits (a
  timeout, an interpreter path) do not trip the pre-push gate.
- **A second hook on the dispatcher entry without its own timeout.** The E5/E6
  timeout checks read `all()`/`min()` over the entry's hooks, so a timeout-less
  sibling hook makes them evaluate against the harness default rather than 360. This
  is harmless for routing, but the timeout assertions weaken for that entry.
- **An ascii entry repointed to a different script reads as `partial`.** The
  ProposalError text then says "half-applied", which is a misleading diagnosis for
  what is really a repointed entry. Fix the entry. Do not re-run the apply.

## Rollback

- Settings: restore the archived `settings.json` from step 4. The old PostToolUse
  entries come back as they were. The new hook files are inert when no settings
  entry names them, except the two dispatcher changes from step 2.
- ascii-only-guard on Edit/Write: remove `"ascii-only-guard"` from GUARD_CHAIN. A
  per-write override is also available: the token `allow-ascii-only-write` (see that
  guard's docstring).
- Telemetry: set `ORA_GUARD_TELEMETRY=0` in the environment. Nothing reads the log
  except the summary script.

## If the order is violated

If settings are applied before the hook files land, every Bash call's PostToolUse
fails with "can't open file ... posttooluse-dispatcher.py". The interpreter exits 2,
which is visible to the model but blocks nothing, because the tool already ran. For
that window catch_up_main and eos-gate-sentinel do not run, so no gate-green marker
and no ora-skills catch-up.

On the PreToolUse side the new DC entry names `hooks/ascii-only-guard.py`, which is
**already live** (it has been on main since before 1370b41; only its docstring
changes here). That matters because on PreToolUse a missing script means the
interpreter exits 2, which is a BLOCK: every Desktop Commander write would be refused.
Do not apply this settings file to a checkout that lacks that file.
