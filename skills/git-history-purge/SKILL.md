---
name: git-history-purge
description: Use when private data (deal figures, phone numbers, a notes or memory folder, a work email in commit authors, a leaked file) must be removed from the HISTORY of a GitHub repo, not just from its tip - especially a PUBLIC repo with many branches, a live local checkout that a scheduled task pushes from, or old pull requests that still show the data. Trigger on: purge history, rewrite history, scrub history, filter-repo, BFG, remove from all commits, force-push every branch, the data is still in old commits, old PRs still show it, GitHub Support sensitive-data removal, refs/pull. NOT for removing data from the current tree only (a normal reviewed PR), NOT for rotating a leaked live secret (rotate first; a purge never un-leaks it), NOT for syncing a stale branch (branch-catchup) or triaging dirty trees (dirty-tree-triage).
license: ORA Internal
---

# Git history purge (v1.0)

Proven 2026-11-20 on a public config repo: 313 branches + 1 tag rewritten, 3,889 blobs verified clean from a fresh clone, main's tree byte-identical, live checkout re-pointed, GitHub Support ticket filed for the 470 `refs/pull/*`. Every step below either ran or was learned from a failure.

**Principle: the purge changes history, never main's current tree.** Scrub the tip first with a normal reviewed PR; the purge then only rewrites what is no longer visible.

**Gates (Hard Invariant 1 class, irreversible):** Gabriel's in-turn yes before the force-push, before any repo-setting change, and before filing the Support request. Never change repo visibility or delete/recreate the repo to "fix" a purge; on ORA's six public repos visibility is ruled ("keep public, do not re-ask").

Scripts live in this skill's `scripts/` folder (stdlib Python). Set `S=~/.claude/skills/git-history-purge/scripts` once and call them as `python -I "$S/<script>"` from any directory.

## Step 0 - inventory and freeze (before the backup, so nothing moves after it)
- Remote: branch/tag count, fork count (`gh api repos/O/R --jq .forks_count`), PR count, branch protection and rulesets. Forks keep the data; say so.
- Every pusher: scheduled tasks (both fleets), CI that pushes, the live checkout. Pause each via its supervised tool (`update_scheduled_task enabled:false`, never delete). Block the live checkout: `git config remote.origin.pushurl DISABLED-history-purge-<date>`.

## Step 1 - backup outside every repo
`git clone --mirror <url> <B>/mirror.git`, `git bundle create <B>/all.bundle --all`, `git bundle verify`. `<B>` = `C:/Users/Owner/_archive/<repo>-prepurge-<date>/`. The backup holds the private data: local only, never pushed.

## Step 2 - build rules from what is actually present
- Private values go in a config file OUTSIDE every repo (`~/.ora-private/purge/`). Never type them into a command, commit message, PR, chat or log.
- Run `python -I "$S/purge_scan.py" scan <B>/mirror.git <config.json> <rules.txt>`. It checks every path a file was ever stored at, plus commit and tag messages, and writes a rule only for values present (every written form of each figure: `123,457`, `123457`, `9,876.54`). Rules are anchored so hashes, longer numbers and longer digit runs are untouched. Any rule that matches main's tip is dropped (it would change main's tree). It prints counts only. Report counts, never values or "masked samples".
- A dropped rule means the value is still live at the tip: scrub it by PR first, or accept it stays.
- Work email in authors: GitHub REJECTS pushes of commits carrying a private email ("push declined due to email privacy restrictions"). Plan the mailmap now (`Name <ID+login@users.noreply.github.com> <work@email>`; ID = `gh api user --jq .id`), not after a failed push.
- The scan reads text only (by content, as filter-repo decides). Binary files that hold the data (PDF, XLSX, images) must be removed by path in Step 3; find them with `git filter-repo --analyze` on a scratch copy.

## Step 3 - rewrite a copy, then prove it
```bash
git clone -q --mirror --no-local <B>/mirror.git <B>/work.git && cd <B>/work.git
git filter-repo --force --invert-paths --path-regex '<removed-paths>' \
  --replace-text <rules.txt> --replace-message <rules.txt> --mailmap <mailmap.txt>
```
filter-repo drops the `origin` remote; push by URL. Then all must hold, else stop:
- `git rev-parse main^{tree}` equals the mirror's.
- `python -I "$S/purge_scan.py" verify <B>/work.git <config> <rules.txt>` exits 0.
- `git log --branches --tags --format='%ae%n%ce' | grep -ci <work-domain>` is 0.
- Ref count equals the snapshot's.

## Step 4 - leased push, in batches, main last (after Gabriel's yes)
- Protected `main` or a ruleset that blocks force-push: loosening it is a repo-setting change (its own yes); restore it right after.
- Run `python -I "$S/leased_push.py" <B>/mirror.git <B>/work.git <url> --dry-run`, then without `--dry-run`. Every ref is leased against its SHA in the BACKUP (`mirror.git`), never against what the remote shows at push time: a commit pushed after the backup is not in the rewrite, and a lease read from the remote would overwrite it. Batches of 40 (hundreds of lease arguments exceed the Windows command-line limit), `refs/heads/main` last and held back if anything earlier was rejected.
- Exit 3: a ref moved since the backup; nothing was pushed. Fetch it into `mirror.git`, redo Step 3 for it, run again.
- Exit 1: a PARTIAL push. Read each `REJECTED` / `HELD` line, fix the cause, run again; refs already pushed are skipped, and a ref that moved meanwhile now stops the run (exit 3) instead of being overwritten.
- Hand-rolling it: `--force-with-lease=<ref>:<backup-sha>` and a refspec WITHOUT `+`. A `+<ref>:<ref>` refspec forces past its own lease. Never bare `--force`, `--prune` or `--mirror` (it hits `refs/pull/*`).

## Step 5 - verify from a fresh clone
Clone the remote again into `<B>/verify.git` and re-run Step 3's checks there. A local check of `work.git` proves nothing about GitHub.

## Step 6 - the live checkout: re-point, do not rebuild
- Archive old tips: `git update-ref refs/archive/pre-purge/<name> <old-sha>`.
- Re-point the live branch onto purged main with the SAME files. Pin the old tip as a SHA first, so the compare-and-swap can fail: `OLD=$(git rev-parse refs/heads/<branch>)`, `N=$(git commit-tree "$OLD^{tree}" -p <new-main> -m ...)`, `git update-ref refs/heads/<branch> "$N" "$OLD"`. A branch NAME as the old value resolves at swap time and always passes. Working files are untouched. In `~/.claude` this is a governance write: config-write token with Gabriel's quoted words.
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
| Lease read from `git ls-remote` at push time | Lease against the backup; a post-backup push otherwise vanishes |
| Rules built from a guessed value list | `purge_scan.py scan` writes only rules for values present |
| A rule that matches main's tip | Dropped by the scan; scrub the tip by PR first |
| Retrying a partial push with the first snapshot | Re-snapshot, then push |
| Rebuilding the live checkout and its worktrees | Re-point one branch with `commit-tree`; list old-history branches |
| `rm -rf` of a work or verify clone | Move it into `<B>/`; never delete |
| Calling it done after the push | Fresh-clone verify, Support ticket, old-PR spot check |

## Changelog
- v1.0 (2026-11-23): first version, from the ora-claude-config purge of 2026-11-20. Bundles `scripts/purge_scan.py` and `scripts/leased_push.py` with tests. The leased-push test showed the 2026-11-20 push form (`+` refspec plus lease) did not honor its leases; it was safe only because every pusher was paused. Merge-gate round 1 fixes: leases come from the backup (not the remote at push time), main is held after a rejection, the scan covers every path a blob was stored at, all figure forms, text by content, commit and tag messages, and anchors phone rules. No governor constants touched.
