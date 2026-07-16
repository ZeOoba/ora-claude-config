---
name: oxford-command-center-worktree-gotchas
description: WORKBOOK_PATH isn't inherited per-worktree (still true). warehouse:verify EPERM-on-cleanup was corrected 2026-07-08 (unguarded rmSync, now fixed, verified still intact) — don't confuse with the separate same-day dev:server hang fix (dev-watchdog.cjs). Also: status.json has a real recurring concurrent-merge corruption history; current dev-watchdog work is uncommitted directly on the main checkout, not a worktree.
metadata:
  node_type: memory
  type: project
  originSessionId: 70f9b684-041c-4849-9383-0c2a9f2c4ac1
---

Found while running the full `npm run gate` chain from an isolated worktree
(`.claude/worktrees/<name>`) for [oxford-command-center#185](https://github.com/ZeOoba/oxford-command-center/pull/185):

**WORKBOOK_PATH is not inherited by a worktree.** `worktree-env.example` (copied to each
worktree's own `.env` per `CLAUDE.md` §5) only documents `WAREHOUSE_DB` and `BRAIN_SERVER_PORT`
— it says nothing about `WORKBOOK_PATH`. Without it, `npm run reconcile` and
`npm run warehouse:verify` fail trying to read the live Master Workbook, and — oddly — resolve to
a path with a stray `(1)` suffix (`OneDrive - Oxford Capital Partners (1)\...`) rather than a
clean "not set" error. Fix: pass `WORKBOOK_PATH="<value from root .env>"` inline before the
command (dotenv doesn't override an already-set process env var), or add it to the worktree's
own `.env` — do NOT edit `.env` files with the Edit tool, a hook blocks it; use Bash instead.

**`warehouse:verify` can EPERM-fail its own cleanup — CORRECTED 2026-07-08, was NOT worktree-specific.** The script's
`finally { rmSync(tmp, {recursive:true,force:true}) }` (scripts/warehouse-verify.ts:636) threw
`EPERM` on the tmp dir 3/3 times when run from `.claude/worktrees/fix-design-parity-p2-p3`, but
passed clean (full PASSED output, all assertions) 1/1 time run from the main checkout at the
identical commit. Same general family as [[feedback-gitbash-npm-test-crash]] (native module +
freshly-written temp-dir file + likely AV/EDR real-time-scan interaction on this machine).

Follow-up investigation (same day) found the worktree-vs-main-checkout correlation didn't hold up
— `tmp` is created via `mkdtempSync(join(tmpdir(), ...))`, which resolves to
`C:\Users\Owner\AppData\Local\Temp` regardless of cwd, so there's no code path by which worktree
location could cause this deterministically. Two more reruns from the main checkout came back
clean (2/2), consistent with the original 3-vs-1 sample just being small-sample noise (the sibling
`npm-test-intermittent-access-violation` memory shows this AV-race flake ranges 3/3-clean to
6-in-a-row on this machine — not stable enough for an n=1 "main checkout passed" to be dispositive).

There WAS a real bug, though: the `rmSync` had no `maxRetries`/`retryDelay` (Node's built-in
opt-in retry for exactly this Windows race) and no try/catch, so when the AV race did hit, the
whole script crashed with a raw EPERM stack trace INSTEAD of printing its actual
PASSED/FAILED result — a run where every real check passed could still look like a hard failure.
**Fixed 2026-07-08**: added `maxRetries: 5, retryDelay: 200` plus a non-fatal catch (logs a
warning, doesn't crash). Full details: oxford-command-center repo-scoped memory
`warehouse-verify-eperm-fixed.md`.

**How to apply:** if `warehouse:verify` shows a bare EPERM/stack-trace exit again (post-fix, this
should no longer happen — a recurrence is a real regression, not noise). Don't re-attribute future
cleanup flakes to worktree-vs-main-checkout; that theory was tested and didn't hold.

**Correction 2026-07-08 (evening) — the prior "may have been superseded" note (below, now retracted)
was a misattribution; verified directly against the repo.** A handoff described a concurrent
session's uncommitted changes to `scripts/warehouse-verify.ts`, `package.json`,
`.claude/launch.json.example`, plus a new `scripts/dev-watchdog.cjs` as re-fixing the warehouse-verify
rmSync EPERM issue "for real this time." Checked directly: `scripts/warehouse-verify.ts` is clean
(no uncommitted changes) — the maxRetries/retryDelay fix (commit `9f2873f`) is intact on `main` and
was NOT touched by this concurrent work. The actual uncommitted diff is a **different, unrelated
bug**: `dev:server` (`tsx watch`) intermittently hangs before binding its port (~2/5 trials,
2026-07-08 per the package.json comment added). Fix in progress: `scripts/dev-watchdog.cjs` wraps
`tsx watch` via `node --require`, and a new `dev:server:once` (no watch, 5/5 reliable) was added and
made the `.claude/launch.json.example` default. The "dev-watchdog" name and the retry/reliability
framing likely caused the cross-attribution to the EPERM fix — they're separate issues that happened
to land in the repo the same day. **How to apply:** don't assume two same-day fixes touching
adjacent dev-tooling files are the same fix — verify the actual diff before concluding one supersedes
the other.

**Update 2026-07-08 (evening) — `architecture/status.json` corruption risk is real and well-documented
in-file; the dev-watchdog work above is happening directly on the shared main checkout, not a worktree.**
Read `architecture/status.json` directly: it contains multiple first-person "repair lineage" entries
(`ic-memo`, `design-parity-impl`, `fix-status-json-ic-memo-parse-error`, `chore-post-w2-merge`) each
describing a real past incident of concurrent merges splicing two edits to the same JSON key without a
separating comma/brace, corrupting the file — this is a recurring failure mode, not a hypothetical.
Deferring a "flip my worktree entry to merged" edit rather than forcing it into a repo with other live
uncommitted work was the right call generically. Separately notable: as of this check, the
`dev:server` hang fix (package.json/launch.json.example/dev-watchdog.cjs, file mtimes ~16:08 EDT,
minutes before this check) is uncommitted directly in the **main checkout**
(`C:/Users/Owner/oxford-command-center`), not an isolated `.claude/worktrees/<name>` — a deviation from
the global CLAUDE.md single-writer doctrine ("never build on the shared main checkout"). No
`architecture/status.json` entry exists for this work (all current entries are `merged`), so it isn't
tracked via the file's own coordination mechanism either. **How to apply:** treat any live main-checkout
diff as a signal another session may be mid-edit right now — re-check `git status` immediately before
any write to shared files (`status.json`, `package.json`, `CLAUDE.md`) rather than trusting a
snapshot from minutes earlier.

## 2026-07-09 addendum — workbookPath default repointed
PR #199 repointed `workbookPath()`'s DEFAULT from the dead "(1)" path to the canonical root, so
a worktree without WORKBOOK_PATH now falls back to a REAL workbook instead of a nonexistent
path. The env var still wins when set; per-worktree env inheritance is still absent — but the
failure mode changed from "silently points at nothing" to "works via canonical default".
