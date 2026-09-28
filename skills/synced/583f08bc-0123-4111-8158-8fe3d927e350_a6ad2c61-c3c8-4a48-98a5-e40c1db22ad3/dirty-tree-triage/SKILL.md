---
name: dirty-tree-triage
description: Safely triage uncommitted "dirty" git working trees across ORA's shared checkouts (~/.claude, ora-skills, website-canonical, oxford-command-center) — enumerate what's uncommitted, attribute it to a session with real evidence (never a guess), settle it with a two-pass mtime check, then isolate-and-commit only what's genuinely safe via commit_isolated_replacement(). Contested or live WIP is reported, never force-resolved. Use when the user says dirty tree(s), clean up the dirty repos, investigate and fix dirty trees, uncommitted files backlog, who owns this WIP, reconcile the shared checkout, or git status is a mess across my repos. v1.1 (2026-08-21: step 7's ora-skills check now pairs with a claim_work.py claim — OI-203)
license: ORA Internal
---

# Dirty-Tree Triage

Turns "there's a pile of uncommitted files somewhere" into a per-repo report and, only where the evidence genuinely supports it, a safe isolated commit — never a blind sweep. ORA's checkouts (above all `~/.claude`, driven by a dozen-plus concurrent sessions) accumulate uncommitted WIP by design; the failure mode this skill exists to prevent is treating that pile as a problem to be flattened in one action, which is exactly how another session's in-flight work gets clobbered.

## Scope

Mechanical enumeration + evidence-gated isolation-commit of settled, attributable WIP. Does **not** decide whether the content of someone's WIP is correct, does **not** resolve branch-level divergence (e.g. a checkout that's behind/ahead of `origin/main` in a way that needs a real merge decision), and never force-switches, resets, or rebases a shared checkout. Those are separate, larger decisions that stay with the user — see [[project_primary_checkout_main_move_blocked_2026-08-12]] for a case where exactly that line was already drawn.

## Triggers

"dirty tree(s)", "clean up the dirty repos", "investigate and fix dirty trees", "uncommitted files backlog", "who owns this WIP", "reconcile the shared checkout", "git status is a mess across my repos".

## Inputs

- **Repo set:** the default four (`~/.claude`, `ora-skills`, `website-canonical`, `oxford-command-center` — see `scripts/scan_dirty_trees.py`'s `DEFAULT_REPOS`). If the user names a different or additional repo, pass it via `--repo`; don't silently expand or shrink the set on your own guess.
- **Live session roster:** `list_sessions` (isRunning + lastActivityAt).
- **Commit provenance:** `hooks/lib/commit_provenance.py`'s touched-set data — only exists for the primary `~/.claude` checkout; the other repos have no equivalent recorder, so attribution there leans more on `git log -1`/session self-report.

## Standard Workflow

1. **Scan.** Run `python scripts/scan_dirty_trees.py` — wraps `git status --porcelain=v1 --branch` per repo and classifies every entry as `untracked-trivial` / `untracked-dir` / `untracked-file` / `modified-tracked` / `staged`. Most of what it finds is normal for an always-on shared checkout, not a problem — the scan is the start of triage, not a to-do list to clear.

2. **Split off the trivial bucket.** `untracked-trivial` entries (scratch/preview-deploy/archive-scratch dirs — see the script's `TRIVIAL_HINTS`) are near-zero risk: nothing else references paths inside a directory nobody tracks. List them and propose moving to `/archive/` — **never delete** (Hard Invariant 6) — and apply only after the user confirms.

3. **Attribute the tracked/modified bucket with evidence, not a guess.** For each `modified-tracked`/`staged` entry, before treating it as anyone's:
   - Cross-check provenance (which session's recorded edits actually intersect this path), where that data exists.
   - Cross-check `list_sessions` for real, corroborating activity — not just a name. A heuristic naming "the likely session" without an intersecting touched-set is not attribution; see [[feedback_shared_checkout_guard_session_attribution_unreliable]], where the same class of guess (`others[0]`) named idle or unrelated sessions four separate times before the underlying tool was fixed to require intersecting evidence.
   - No corroborating session? Report the file `UNATTRIBUTED` — that's a valid, honest finding on its own, not something to work around by guessing.

4. **Settle before touching anything — two real, time-separated checks.** Uncommitted does not mean still-being-edited. Record each candidate file's mtime, wait a genuine interval (15–30 minutes — running the scan twice back-to-back proves nothing), and re-check. Identical mtime across both checks means settled, regardless of any session's `isRunning` flag; a moved mtime means still live. See [[feedback_verify_wip_settled_via_mtime]] — this step was deliberately left as a manual technique rather than an automated one-shot detector, because a single snapshot can't distinguish "mid-edit" from "finished twenty minutes ago and moved on." Don't shortcut it by skipping straight to step 5 on one scan.

5. **Isolate and commit — never a batch operation.** Only for files that are both (a) attributed to one owner, or honestly `UNATTRIBUTED` and stable, and (b) mtime-settled: use `commit_isolated_replacement()` in `hooks/lib/isolated_commit.py` (landed on the primary checkout 2026-08-13, commit `522075e8` — see [[reference_isolated_commit_repair_wrapper_2026-08-13]]) to stage and commit *that file's content only*. Never `git add -A` / `git commit -a` / a pathspec-less commit without first checking `git diff --cached` — on a shared checkout the index itself can hold another session's staged work; see [[feedback_git_index_is_shared_state]] and [[reference_event_log_uncommitted_backlog]] for the two independent ways a naive commit sweeps in foreign content. On the primary `~/.claude` checkout, `config-write-guard.py` blocks any git write without an `allow-config-write` override token — mint it with the user's in-turn approval quoted as the reason, use it, and delete it immediately after the commit lands rather than leaving a 60-minute window open.

6. **Contested or live WIP: report, don't act.** Anything that fails settlement (mtime moved) or is attributed to a currently-running session stays untouched — surface it in the report. A large multi-session backlog (the primary checkout has run into a 100+-file version of exactly this) resolves session-by-session, never as one batch housekeeping action — do not try to shortcut that by force-switching, resetting, or rebasing the checkout on the theory that it would "clear the noise."

7. **`ora-skills` gets an independent single-writer check first**, before touching anything there regardless of the steps above: `git log --oneline -1` + `git status`. If HEAD is newer than session start, or there's uncommitted work that isn't yours, stop and surface the conflict. **Pair it with a claim (added 2026-08-21, `open-items-tracker.md#OI-203`):** run `python hooks/lib/claim_work.py claim ora-skills-housekeeping "<what/why>" --paths <target files/dirs>` before starting any actual triage work on `ora-skills`. Git state alone is structurally blind to a concurrent session — commits on this shared checkout carry the same handful of human author identities regardless of which session made them, so a clean `git status` and a normal-looking HEAD can both be true while another session is mid-triage on the exact same folder. Confirmed live 2026-08-21: two sessions independently ran this skill's full workflow against the same `_staging` folders with neither claiming first — the collision was caught only by accident, when one session's archive `mv` found its source already moved by the other. `claim_work.py`'s own docstring documents the identical failure from 2026-08-12 as the reason the module exists; running the git check without the claim only re-derives half the protection.

8. **Report.** One table per repo — file, category, attribution, settlement status, action (isolated+committed / proposed-archive / left-untouched-contested). Log a single consolidated `event_log.md` entry for whatever was actually committed or archived, not one line per file.

## Outputs

- A per-repo dirty-tree report.
- Isolated commits for settled, evidence-attributed (or honestly-unattributed-and-settled) WIP only, via `commit_isolated_replacement()`.
- A proposed (not executed) archive list for trivial untracked scratch directories, pending confirmation.
- A list of contested/live files left untouched, with owning session where attributable.
- One consolidated `event_log.md` entry.

## Boundaries

- Never `git add -A`, `git commit -a`, or any pathspec-less commit without checking `git diff --cached` first on a checkout other sessions may be using.
- Never force-switch, `reset --hard`, or rebase a shared checkout to "resolve" its dirty backlog — branch-level divergence is a separate decision that stays with the user.
- Never delete anything — archive only, and only after confirmation.
- Never treat one `git status` snapshot as proof a file is settled.
- Never trust a named "owning session" without corroborating provenance/session evidence.

## Dependencies

- `hooks/lib/isolated_commit.py`'s `commit_isolated_replacement()` (primary checkout only).
- `hooks/lib/claim_work.py` — required for step 7's `ora-skills` single-writer check (see step 7), and for any hands-on session in `hooks/`, override/auth logic, or repo housekeeping broader than this skill's mechanical scope.

## Changelog

- v1.1 (2026-08-21, `open-items-tracker.md#OI-203`): step 7's `ora-skills` single-writer check now requires a `claim_work.py claim ora-skills-housekeeping` call alongside the existing `git log -1`/`git status` check. Root cause: two sessions independently ran this skill's full workflow against the same `ora-skills/_staging` folders on 2026-08-21 with neither claiming first — git state alone can't see a concurrent session (shared author identity across sessions), so both saw a clean tree and proceeded. Caught only by accident when one session's archive `mv` found its source already moved by the other. No procedure logic changed beyond the new claim step.
