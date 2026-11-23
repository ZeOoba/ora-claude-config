---
name: git-history-purge
description: Use when private data (deal figures, phone numbers, a notes or memory folder, a work email in commit authors, a leaked file) must be removed from the HISTORY of a GitHub repo, not just from its tip - especially a PUBLIC repo with many branches, a live local checkout that a scheduled task pushes from, or old pull requests that still show the data. Trigger on: purge history, rewrite history, scrub history, filter-repo, BFG, remove from all commits, force-push every branch, the data is still in old commits, old PRs still show it, GitHub Support sensitive-data removal, refs/pull. NOT for removing data from the current tree only (a normal reviewed PR), NOT for rotating a leaked live secret (rotate first; a purge never un-leaks it), NOT for syncing a stale branch (branch-catchup) or triaging dirty trees (dirty-tree-triage).
license: ORA Internal
---

# Git history purge (v1.0)

Proven 2026-11-20 on a public config repo: 313 branches + 1 tag rewritten, 3,889 blobs verified clean from a fresh clone, main's tree byte-identical, live checkout re-pointed, GitHub Support ticket filed for the 470 `refs/pull/*`. Every step below either ran or was learned from a failure.

**Principle: the purge changes history, never main's current tree.** Scrub the tip first with a normal reviewed PR; the purge then only rewrites what is no longer visible.

**Principle: nothing else may write to the remote between the backup and the push.** The freeze (Step 0) makes that true; `leased_push.py` (Step 4) proves it before pushing and refuses otherwise. Neither is enough alone.

**Gates (Hard Invariant 1 class, irreversible):** Gabriel's in-turn yes before the force-push, before any repo-setting change (rulesets, branch protection), and before filing the Support request. Never change repo visibility or delete/recreate the repo to "fix" a purge; on ORA's six public repos visibility is ruled ("keep public, do not re-ask").

Scripts are stdlib Python in this skill's `scripts/` folder. Set `S` once to that folder: `~/.claude/skills/git-history-purge/scripts` when the skill is installed there, otherwise `<ora-skills checkout>/git-history-purge/scripts`. Call them as `python -I "$S/<script>"` from any directory.

## Step 0 - inventory and freeze (before the backup)
- Remote: branch/tag count, fork count (`gh api repos/O/R --jq .forks_count`), PR count, branch protection and rulesets. Forks keep the data; say so.
- Local pushers: scheduled tasks (both fleets), CI that pushes, the live checkout and other sessions on it. Pause each via its supervised tool (`update_scheduled_task enabled:false`, never delete). Block the live checkout: `git config remote.origin.pushurl DISABLED-history-purge-<date>`.
- Remote lock (repo-setting change, its own yes): a temporary ruleset on all branches and tags restricting creation, update and deletion, with bypass for the repository admin role only. It stops every other account, app and bot. It does NOT stop pushes made with the owner's own credentials (scheduled tasks, other sessions on this machine): those stay covered by the local freeze above and by the Step 4 check. Remove the ruleset after Step 5.

## Step 1 - backup outside every repo
`git clone --mirror <url> <B>/mirror.git`, `git bundle create <B>/all.bundle --all`, `git bundle verify`. `<B>` = `C:/Users/Owner/_archive/<repo>-prepurge-<date>/`. The backup holds the private data: local only, never pushed.

## Step 2 - build rules from what is actually present
- Private values go in a config file OUTSIDE every repo (`~/.ora-private/purge/`). Never type them into a command, commit message, PR, chat or log. Set `"tip_ref"` if the default branch is not `refs/heads/main` (the scan refuses a missing one).
- Run `python -I "$S/purge_scan.py" scan <B>/mirror.git <config.json> <rules.txt>`. It checks every path a file was ever stored at, plus commit and tag messages, and writes a rule only for values present, in each written form (`123,457`, `123457`, `9,876.54`, `123,456.5`). Rules are anchored so hashes, longer numbers and longer digit runs are untouched. Any rule that matches the tip is dropped (it would change the tip's tree). It prints counts only. Report counts, never values or "masked samples".
- Read the `values skipped ... NOT searched` count: round thousands, whole numbers below `min_integer` (default 10000) and non-whole values below 1,000 are not searched, because replacing them would hit unrelated text. If one of them must go, remove its file by path or add an exact literal.
- A dropped rule means the value is still live at the tip: scrub it by PR first, or accept it stays.
- Work email in authors: GitHub REJECTS pushes of commits carrying a private email ("push declined due to email privacy restrictions"). Plan the mailmap now (`Name <ID+login@users.noreply.github.com> <work@email>`; ID = `gh api user --jq .id`), not after a failed push.
- The scan reads text only (by content, as filter-repo decides). Binary files that hold the data (PDF, XLSX, images) must be removed by path in Step 3; find them with `git filter-repo --analyze` on a scratch copy.

## Step 3 - rewrite a fresh copy, then prove it
```bash
cd <B> && git clone -q --mirror --no-local mirror.git work.git
git -C work.git filter-repo --force --invert-paths --path-regex '<removed-paths>' \
  --replace-text <rules.txt> --replace-message <rules.txt> --mailmap <mailmap.txt>
```
Always a FRESH clone of the backup: if `work.git` exists, move it aside first (`mv work.git work-<n>.git`). A further filter-repo pass on the same copy is fine (its `filter-repo/ref-map` keeps the backup as the starting point); reusing a copy after the backup changed is not, and Step 4 refuses it. filter-repo drops the `origin` remote; push by URL. Then all must hold, else stop:
- `git -C work.git rev-parse main^{tree}` equals the backup's.
- `python -I "$S/purge_scan.py" verify <B>/work.git <config> <rules.txt>` exits 0. Besides re-applying the rules, verify searches EVERY object in the store (all blobs, commits and tags, not walked by ref or path) for every configured value and literal, independent of the rules, so a value the scan missed still fails it. Values present in the tip's files are reported as kept at the tip (accepted). A remaining value is either a scan miss (add an exact literal, redo Step 3) or a different number that contains it (e.g. `1,123,457`); confirm which with `git -C <B>/work.git grep` locally, and proceed past a confirmed false alarm only with Gabriel's yes.
- `git -C work.git log --branches --tags --format='%ae%n%ce' | grep -ci <work-domain>` is 0.
- Ref count equals the backup's, minus refs the rewrite deleted (Step 4 lists them).

## Step 4 - checked, leased push (after Gabriel's yes)
- Protected `main` or a ruleset that blocks force-push: loosening it is a repo-setting change (its own yes); restore it right after.
- Run `python -I "$S/leased_push.py" <B>/mirror.git <B>/work.git <url> --dry-run`, then without `--dry-run`. Before pushing anything it checks the chain: every ref was rewritten from the backup's SHA (from `work.git/filter-repo/ref-map`), and the remote still has the backup's SHA. Every lease is against the backup, never against what the remote shows at push time. Batches of 40 (hundreds of lease arguments exceed the Windows command-line limit); the default branch (`--main-ref`, default `refs/heads/main`) is pushed alone, last, and only if nothing else was rejected.
- Exit 2: bad path or URL, or `STALE` refs (the copy was not made from this backup). Redo Step 3 from a fresh clone.
- Exit 3: `MOVED` refs (someone pushed after the backup, including a brand-new branch or tag the backup does not have); nothing was pushed. Find who (the freeze leaked), fetch the ref into `mirror.git`, redo Step 3 from a fresh clone, run again.
- Exit 4: `DELETED-BY-REWRITE` refs (every commit on them was purged) still hold the data on the remote; nothing was pushed. Confirm the list, then run again with `--delete-removed`.
- Exit 1: a partial push. Read each `REJECTED` / `HELD` line, fix the cause, run again as-is: refs already pushed are skipped, and anything that moved meanwhile stops the run (exit 3) instead of being overwritten. Never re-clone the backup to "refresh" it after a partial push.
- Hand-rolling it: `--force-with-lease=<ref>:<backup-sha>` and a refspec WITHOUT `+`. A `+<ref>:<ref>` refspec forces past its own lease. Never bare `--force`, `--prune` or `--mirror` (it hits `refs/pull/*`).

## Step 5 - verify from a fresh clone
`git clone --bare <url> <B>/verify.git` and re-run Step 3's checks there. A local check of `work.git` proves nothing about GitHub. Use `--bare`, not `--mirror`: a mirror clone also fetches GitHub's `refs/pull/*`, which still hold the old history until Step 7. Then remove the Step 0 ruleset.

## Step 6 - the live checkout: re-point, guard, then re-enable
- Archive old tips: `git update-ref refs/archive/pre-purge/<name> <old-sha>`.
- Re-point the live branch onto purged main with the SAME files. Pin the old tip as a SHA first, so the compare-and-swap can fail: `OLD=$(git rev-parse refs/heads/<branch>)`, `N=$(git commit-tree "$OLD^{tree}" -p <new-main> -m ...)`, `git update-ref refs/heads/<branch> "$N" "$OLD"`. A branch NAME as the old value resolves at swap time and always passes. Working files are untouched. In `~/.claude` this is a governance write: config-write token with Gabriel's quoted words.
- List local branches whose root commit is not on purged main to `<B>/old-history-local-branches.txt`. Do not migrate worktrees or delete branches; deleting them is a separate decision.
- BEFORE restoring `pushurl`, install the old-history guard, because `git push origin <old-branch>` from any worktree would re-publish the purged data and `pushurl`/`pushRemote` do not stop an explicit remote.
  - `python -I "$S/old_history_guard.py" commits <B>/mirror.git <B>/verify.git <B>/old-commits.txt` records every commit the purge changed or dropped (exit 1 if none: stop and find out why). It works by commit, not root: a clean first commit keeps its SHA and every old branch shares it.
  - The repo's pre-push hook must run `check` with git's stdin and its own arguments. When a pre-push hook already exists (in `~/.claude` it ends by `exec`-ing the confidentiality scan, which also reads stdin), put the guard in front and pass the existing command after `--`, so both see the same input: `exec python -I "$S/old_history_guard.py" check <B>/old-commits.txt -- <existing command> "$@"`. Never read stdin twice or redirect it to `/dev/null`: either blinds one of them.
  - In `~/.claude` hooks are a governance write: Gabriel's yes. Test it before re-enabling: an old-history branch must be refused and a purged one allowed.
- Restore `pushurl`, re-enable paused tasks (re-date their `[MODEL:]` tag), confirm the first scheduled push lands, then re-run the Step 5 verify once more.

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
| Reusing `work.git` after fetching a moved ref into the backup | Move it aside and re-clone; `leased_push.py` refuses a `STALE` copy |
| Re-cloning the backup after a partial push | Rerun as-is; the backup is the baseline the leases depend on |
| Rules built from a guessed value list | `purge_scan.py scan` writes only rules for values present |
| A rule that matches the tip | Dropped by the scan; scrub the tip by PR first |
| Re-enabling pushes with old-history branches around | Install `old_history_guard.py` as pre-push first |
| Guarding by root commit | A clean first commit survives the purge; guard by changed commits (`commits` mode) |
| Chaining a second pre-push check that also reads stdin | `check ... -- <next command>`; never read stdin twice |
| Verifying from a `--mirror` clone | `--bare`: a mirror fetches `refs/pull/*` with the old history |
| Rebuilding the live checkout and its worktrees | Re-point one branch with `commit-tree`; list old-history branches |
| `rm -rf` of a work or verify clone | Move it into `<B>/`; never delete |
| Calling it done after the push | Fresh-clone verify, Support ticket, old-PR spot check |

## Changelog
- v1.0 (2026-11-23): first version, from the ora-claude-config purge of 2026-11-20. Bundles `scripts/purge_scan.py`, `scripts/leased_push.py` and `scripts/old_history_guard.py` with tests. The leased-push test showed the 2026-11-20 push form (`+` refspec plus lease) did not honor its leases; it was safe only because every pusher was paused. Merge-gate rounds 1-2 (redesign chosen by Gabriel after round 2): the push checks the whole chain backup -> rewrite -> remote before pushing (stale copy, moved ref and deleted-ref refusals), leases come from the backup, main is pushed alone and last; Step 0 adds a temporary remote ruleset; Step 6 installs a pre-push guard before re-enabling pushes; the scan covers every path a blob was stored at, all figure forms, text by content, commit and tag messages, anchors hashes on both sides, refuses a missing tip branch and counts skipped values. Round 3 (cap raised to 4 by Gabriel, redesign): verify adds a search of every object for every configured value, independent of the rules; figures beside CSV/JSON neighbours are matched; refs are walked with `--branches --tags` (no command-line limit); a branch created after the backup stops the push; `--main-ref` for other default branches; the guard records changed commits instead of roots and chains in front of an existing hook with the same stdin; Step 5 uses a bare clone. No governor constants touched.
