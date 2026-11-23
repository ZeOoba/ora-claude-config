---
name: git-history-purge
description: Use when private data (deal figures, phone numbers, a notes or memory folder, a work email in commit authors, a leaked file) must be removed from the HISTORY of a GitHub repo, not just from its tip - especially a PUBLIC repo with many branches, a live local checkout that a scheduled task pushes from, or old pull requests that still show the data. Trigger on: purge history, rewrite history, scrub history, filter-repo, BFG, remove from all commits, force-push every branch, the data is still in old commits, old PRs still show it, GitHub Support sensitive-data removal, refs/pull. NOT for removing data from the current tree only (a normal reviewed PR), NOT for rotating a leaked live secret (rotate first; a purge never un-leaks it), NOT for syncing a stale branch (branch-catchup) or triaging dirty trees (dirty-tree-triage).
license: ORA Internal
---

# Git history purge (v1.0)

Proven 2026-11-20 on a public config repo: 313 branches + 1 tag rewritten, 3,889 blobs verified clean from a fresh clone, main's tree byte-identical, live checkout re-pointed, GitHub Support ticket filed for the 470 `refs/pull/*`. Every step below either ran or was learned from a failure.

**Principle: the purge changes history, never main's current tree.** Scrub the tip first with a normal reviewed PR; the purge then only rewrites what is no longer visible.

**Gates (Hard Invariant 1 class, irreversible):** Gabriel's in-turn yes before the force-push, before any repo-setting change, and before filing the Support request. Never change repo visibility or delete/recreate the repo to "fix" a purge; on ORA's six public repos visibility is ruled ("keep public, do not re-ask").

Scripts live in this skill's `scripts/` folder (stdlib Python; run with `python -I`).

## Step 0 - inventory and freeze (before the backup, so nothing moves after it)
- Remote: branch/tag count, fork count (`gh api repos/O/R --jq .forks_count`), PR count, branch protection and rulesets. Forks keep the data; say so.
- Every pusher: scheduled tasks (both fleets), CI that pushes, the live checkout. Pause each via its supervised tool (`update_scheduled_task enabled:false`, never delete). Block the live checkout: `git config remote.origin.pushurl DISABLED-history-purge-<date>`.

## Step 1 - backup outside every repo
`git clone --mirror <url> <B>/mirror.git`, `git bundle create <B>/all.bundle --all`, `git bundle verify`. `<B>` = `C:/Users/Owner/_archive/<repo>-prepurge-<date>/`. The backup holds the private data: local only, never pushed.

## Step 2 - build rules from what is actually present
- Private values go in a config file OUTSIDE every repo (`~/.ora-private/purge/`). Never type them into a command, commit message, PR, chat or log.
- Run `python -I scripts/purge_scan.py scan <B>/mirror.git <config.json> <rules.txt>`. It writes a rule only for values present in history, anchors numbers so hashes and longer numbers are untouched, and drops any rule that matches main's tip (it would change main's tree). It prints counts only. Report counts, never values or "masked samples".
- A dropped rule means the value is still live at the tip: scrub it by PR first, or accept it stays.
- Work email in authors: GitHub REJECTS pushes of commits carrying a private email ("push declined due to email privacy restrictions"). Plan the mailmap now (`Name <ID+login@users.noreply.github.com> <work@email>`; ID = `gh api user --jq .id`), not after a failed push.
- The scan reads text files only. Binary files that hold the data (PDF, XLSX, images) must be removed by path in Step 3; find them with `git filter-repo --analyze` on a scratch copy.

## Step 3 - rewrite a copy, then prove it
```bash
git clone -q --mirror --no-local <B>/mirror.git <B>/work.git && cd <B>/work.git
git filter-repo --force --invert-paths --path-regex '<removed-paths>' \
  --replace-text <rules.txt> --replace-message <rules.txt> --mailmap <mailmap.txt>
```
filter-repo drops the `origin` remote; push by URL. Then all must hold, else stop:
- `git rev-parse main^{tree}` equals the mirror's.
- `purge_scan.py verify <B>/work.git <config> <rules.txt>` exits 0.
- `git log --branches --tags --format='%ae%n%ce' | grep -ci <work-domain>` is 0.
- Ref count equals the snapshot's.

## Step 4 - leased push, in batches, main last (after Gabriel's yes)
- Protected `main` or a ruleset that blocks force-push: loosening it is a repo-setting change (its own yes); restore it right after.
- Run `python -I scripts/leased_push.py <B>/work.git <url> --dry-run`, then without `--dry-run`. It snapshots the remote with `git ls-remote`, leases every branch and tag against that snapshot, pushes batches of 40 (hundreds of lease arguments in one push exceed the Windows command-line limit) with `refs/heads/main` last, and tallies the porcelain flags.
- Hand-rolling it: lease with `--force-with-lease=<ref>:<sha>` and a refspec WITHOUT `+`. A `+<ref>:<ref>` refspec forces past its own lease and silently overwrites anything pushed after the snapshot. Never bare `--force`, `--prune` or `--mirror` (it hits `refs/pull/*`).
- Exit 1 means a PARTIAL push: some refs rewritten, some not. Read each `REJECTED` line, fix the cause, run again (it re-snapshots). Never `--use-snapshot` after a partial push.

## Step 5 - verify from a fresh clone
Clone the remote again into `<B>/verify.git` and re-run Step 3's checks there. A local check of `work.git` proves nothing about GitHub.

## Step 6 - the live checkout: re-point, do not rebuild
- Archive old tips: `git update-ref refs/archive/pre-purge/<name> <old-sha>`.
- Re-point the live branch onto purged main with the SAME files: `N=$(git commit-tree <old-tip>^{tree} -p <new-main> -m ...)`, then `git update-ref refs/heads/<branch> $N <old-tip>` (CAS). Working files are untouched. In `~/.claude` this is a governance write: config-write token with Gabriel's quoted words.
- List local branches whose root commit is not on purged main to `<B>/old-history-local-branches.txt`. They must NEVER be pushed. Do not migrate worktrees or delete branches; deleting them is a separate decision.
- Restore `pushurl`, re-enable paused tasks (re-date their `[MODEL:]` tag), confirm the first scheduled push lands.

## Step 7 - what a force-push cannot reach
`refs/pull/*`, cached commit/diff views and direct SHA URLs still serve old content. Only GitHub Support can purge them (support.github.com, logged in as the owner). Use category Repositories > Repository features (NOT "Deletes", which is the delete-a-repository flow). Include: the repo URL, the PR count, the "First Changed Commit" from `<B>/work.git/filter-repo/first-changed-commits`, orphaned LFS objects (or "none"), and that no secrets are among the removed data (or which were rotated). Never paste removed data. After Support confirms, open one old PR's "Files changed" and check a removed path is gone. Mirrors, forks and past clones cannot be recalled.

## Step 8 - record
Event-log entry via `append-event-log.py` (counts, SHAs, backup path, residuals, ticket number), with Gabriel's quoted decisions.

## Common mistakes
| Mistake | Fix |
|---|---|
| `git push --force --prune` or `--mirror` | `leased_push.py`; `--mirror` touches `refs/pull/*`, `--prune` deletes refs |
| `--force-with-lease=<ref>:<sha> +<ref>:<ref>` | The `+` overrides the lease; drop it |
| Rules built from a guessed value list | `purge_scan.py scan` writes only rules for values present |
| A rule that matches main's tip | Dropped by the scan; scrub the tip by PR first |
| Retrying a partial push with the first snapshot | Re-snapshot, then push |
| Rebuilding the live checkout and its worktrees | Re-point one branch with `commit-tree`; list old-history branches |
| `rm -rf` of a work or verify clone | Move it into `<B>/`; never delete |
| Calling it done after the push | Fresh-clone verify, Support ticket, old-PR spot check |

## Changelog
- v1.0 (2026-11-23): first version, from the ora-claude-config purge of 2026-11-20. Bundles `scripts/purge_scan.py` and `scripts/leased_push.py` with tests. The leased-push test showed the 2026-11-20 push form (`+` refspec plus lease) did not honor its leases; it was safe only because every pusher was paused. No governor constants touched.
