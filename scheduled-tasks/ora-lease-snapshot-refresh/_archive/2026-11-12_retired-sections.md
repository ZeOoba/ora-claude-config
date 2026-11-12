# Retired 2026-11-12 (v2.0) — verbatim text of the v1.x steps, Worktree isolation, Auto-commit and Auto-push sections

Superseded by the Live-checkout refresh section: data/snapshots/portfolio.json is untracked since oxford-command-center PR #565.

## Old steps

1. Worktree isolation: create this run's own private worktree per the **Worktree isolation** section below (stale-worktree sweep, then `npm run worktree -- add` off a freshly-fetched `origin/main`, then copy `.env` AND `data/overlay.json` in — both are gitignored, so the worktree has neither). Every step from here on runs inside that worktree, never against the live `oxford-command-center` checkout directly — the live checkout is touched only to fetch and to create/remove the worktree; the only shared state it touches is the final branch push and PR (`main` moves only when that PR merges).
2. Run, from inside the worktree: `npx tsx scripts/lease-snapshot-drift-check.ts`
3. Read the exit code AND the full stdout/stderr output — the exit code alone doesn't carry the detail a human needs.
4. On Exit 0 or Exit 2 only, commit the regenerated snapshot per "Auto-commit" below — from inside the worktree, comparing against the worktree's own `HEAD`.
5. If step 4 produced a commit, land it per "Auto-push" below (via PR + auto-merge, never a direct push to main; automation snapshot commits only — see that section for which prefixes qualify), from inside the worktree.
6. **Regardless of exit code, and regardless of which Auto-commit/Auto-push branch this run takes** (committed-and-pushed, a `MATERIAL: none` no-op, a shrink/degradation refusal, a push refusal, or a crash mid-guard) **the last action of this run is always Cleanup**, per the Worktree isolation section below. Never leave a run's worktree behind on disk.

## Old sections

## Worktree isolation (added 2026-09-02 — closes the Qodo review gap on this file's Auto-commit section: no isolation existed between the drift-check script and the eventual `git add`/commit, so a concurrent session's commit landing on `oxford-command-center`'s `main` mid-run, or a concurrent edit mid-run, could go undetected by the repo-sanity check's point-in-time snapshot alone)

Every run of this task gets its own **private, ephemeral git worktree** — a fresh checkout of `origin/main` that only this run touches. The drift-check script, every comparison guard (material-change, section-shrink, degradation), and the commit all happen INSIDE that worktree, against the worktree's OWN `HEAD` — never against the live checkout's working tree. The only points where a run touches shared state are the final branch push and PR (Auto-push below); `main` itself moves only when that PR merges.

**Naming — unique per run, never collides with the sibling task or a concurrent fire of this same task.**
- Base directory: `C:\Users\Owner\AppData\Local\Temp\ora-cc-worktrees\`
- This task's prefix: `lease-snapshot-` (the sibling `ora-cc-snapshot-refresh` uses `cc-snapshot-` — different prefixes so the two tasks' worktrees can never collide, even fired at the same instant).
- Run id: `<UTC timestamp>-<4 hex chars>`, generated fresh each run, e.g. via Desktop Commander:
  ```bash
  python -c "import secrets,datetime;print(datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(2))"
  ```
- Worktree path: `C:\Users\Owner\AppData\Local\Temp\ora-cc-worktrees\lease-snapshot-<runid>`
- Branch: `auto/lease-snapshot-<runid>`, created off `origin/main` EXPLICITLY — never a bare `git worktree add` with no base. With no explicit base a worktree silently forks from whatever branch the live checkout currently has checked out, which in a shared checkout is often another session's WIP, not `main` (`reference_worktree_wrong_base_branch_2026-08-21.md`).

**Stale-worktree sweep — run BEFORE creating this run's worktree**, from the live checkout:
```bash
cd C:/Users/Owner/oxford-command-center
git fetch origin
git worktree list --porcelain
```
For any listed worktree whose path is under `C:\Users\Owner\AppData\Local\Temp\ora-cc-worktrees\` and starts with `lease-snapshot-` (left behind by a crashed or killed prior run of THIS task — a stale `cc-snapshot-` worktree is the sibling task's own concern, leave it alone), check whether it holds an unpushed automation commit before touching it:
```bash
git -C "<stale-path>" log origin/main..HEAD --oneline
```
- **No commits listed, or none matching `^Auto-refresh: (CC|lease) snapshot`** → safe to discard. `npm run worktree -- remove "<stale-path>"`, then `git branch -D <its-auto-branch>`, then continue to worktree creation below.
- **A matching commit is listed BUT is already on origin** (`git fetch origin <its-auto-branch>` then `git merge-base --is-ancestor <sha> FETCH_HEAD` exits 0 (the remote holds it, even after `gh pr update-branch` moved the tip; a fetch error means it is not on origin), or `gh pr list --repo ZeOoba/oxford-command-center --head <its-auto-branch> --state merged --json number` is non-empty — it was published as a PR branch, so it is not stranded; a local `origin/*` tracking ref alone is NOT proof, since `fetch.prune` is off) → `npm run worktree -- remove "<stale-path>"`, then `git branch -D <its-auto-branch>` (the commit is preserved on origin), and continue. Report that PR's state in the run report: `gh pr list --repo ZeOoba/oxford-command-center --head <branch> --state all --json number,state,mergedAt`.
- **A matching commit IS listed and is NOT on origin** → do NOT delete it. A prior run committed but crashed or was killed before pushing. Leave that stale worktree exactly as found, do NOT create a new worktree this run, and escalate with a QUESTION FOR GABRIEL quoting the stranded commit subject(s) and the stale worktree path — this needs a human to reconcile (push it by hand, or discard it deliberately), the same standing rule as any other contaminated shared-checkout tree (`rules.md` §14). Treat this like an Exit-3/Exit-1-class alarm for the exit-code handling below (post to Notion AND email) even though the drift-check script itself never got a chance to run this cycle.

**Create this run's worktree**, from the live checkout, once the sweep above finds nothing to stop for:
```bash
cd C:/Users/Owner/oxford-command-center
npm run worktree -- add "C:\Users\Owner\AppData\Local\Temp\ora-cc-worktrees\lease-snapshot-<runid>" origin/main "auto/lease-snapshot-<runid>"
```
This wraps `scripts/safe-worktree.ts` (PR #29), which does a REAL `npm install` inside the new worktree — its own independent `node_modules`, never a directory junction back to the live checkout's. A junctioned worktree, later force-removed, is exactly what once deleted the live checkout's real `node_modules` and broke its tooling for every session (`reference_worktree_node_modules_junction_hazard.md`) — this procedure never does that. If `npm run worktree` is ever missing or broken, fall back by hand: `git worktree add "<path>" -b "auto/lease-snapshot-<runid>" origin/main`, then `npm install` inside `<path>` — but never junction `node_modules` for speed.

**Copy `.env` AND `data/overlay.json` into the new worktree.** `git worktree add` only brings TRACKED files, and both of these are gitignored, so a fresh worktree has neither. Copy both, before running the drift-check script:
- `C:\Users\Owner\oxford-command-center\.env` -> `<worktree-path>\.env` — without it the script cannot find `WORKBOOK_PATH`.
- `C:\Users\Owner\oxford-command-center\data\overlay.json` -> `<worktree-path>\data\overlay.json` — **added 2026-09-05, after this omission broke a live run.** The overlay carries the enrichment maps (`tenantArrears`, `arBalances`, `renewalStages`, `dealComps`, `marketRents`, `noiBudgets`) that `applyOverlay()` merges onto the parsed snapshot. Absent, the merge writes them as EMPTY. On 2026-09-05 `ora-cc-snapshot-refresh` — the first CC fire under v1.7 worktree isolation — nulled `arBalances` 44->0, `tenantArrears` 44->0, `dealComps` 2->0 and `renewalStages` 1->0 while reporting `No lease drift` and `Data-quality flags: 0` at **exit 0**. Only the section-shrink guard caught it, at commit time, and only via its GENERIC non-list check (the hardcoded 5-key list loop saw nothing — leases/deals/counterparties/properties/loans were all flat).

Verify BOTH copies landed before running the script. As of [PR #311](https://github.com/ZeOoba/oxford-command-center/pull/311) a missing overlay is refused outright (`not found — refusing to proceed`, exit 1) rather than silently zeroing, so skipping this step now costs the run rather than corrupting the snapshot — but the copy is still what makes the run SUCCEED. Do NOT "fix" that refusal by creating an empty `{}` overlay in the worktree: `{}` is the deliberate bootstrap escape hatch for a genuinely new install, and using it here would reintroduce exactly the silent zeroing the refusal exists to stop. Copy the real file.

Every step above and below — the script run, Auto-commit, Auto-push — now runs with the worktree as the working directory, never the live checkout.

**Cleanup — unconditional, every exit path, always the last action of the run.** Whether this run committed and pushed, restored a `MATERIAL: none` no-op, refused on a shrink/degradation guard, failed to land its PR, or crashed mid-guard: remove the worktree before finishing. **The local branch is different — delete it (`git branch -D`) ONLY when its tip is preserved elsewhere:** `git log origin/main..<branch> --oneline` is empty (no commit was made), OR the remote holds that commit — `git fetch origin <branch>` then `git merge-base --is-ancestor <local-sha> FETCH_HEAD` exits 0 (it equals or descends from it: `gh pr update-branch` moves the remote tip past the local one, so a bare sha compare misfires, and a sha mismatch alone is NOT a landing failure; a `git fetch` error such as exit 128 only means the branch is not on origin, so KEEP the local branch — that is not itself an alarm). If a commit exists ONLY on that local branch (push or PR creation failed, or this run was SUPERSEDED), KEEP the branch and report its name and sha — deleting it discards the run's only copy, which is how the 2026-09-14 commits came within one cleanup step of being lost.
```bash
cd C:/Users/Owner/oxford-command-center
npm run worktree -- remove "<worktree-path>"
git branch -D "auto/lease-snapshot-<runid>"   # ONLY when the rule above allows; otherwise skip this line and KEEP the branch
git worktree prune
```
Because this procedure always gives the worktree its own real `npm install` (never a junction), removal carries none of the junction-deletion hazard above — `npm run worktree -- remove` (or, if that script is unavailable, plain `git worktree remove "<worktree-path>" --force`) is safe here. A removal failure is a guard-condition failure like any other in this file — surface it (it leaves a stale worktree for the NEXT run's sweep to find and reconcile, not silent data loss) rather than retrying destructively or ignoring it.

## Auto-commit (`data/snapshots/portfolio.json` is git-tracked)

`data/snapshots/portfolio.json` was un-ignored and committed to `main` on 2026-07-27 (Gabriel directive) — it is no longer a gitignored scratch file, so every successful regeneration should land in history, not just sit unversioned on disk.

- **Material-change gate (Gabriel ruling 2026-07-27; mechanism replaced 2026-08-27 — supersedes BOTH the original bare `git status` check and the by-name `generatedAt` grep filter that replaced it).** The script rewrites a write-clock on *every* run, so `git status` on this file is **never** empty and a bare status check commits on every fire — ~15 timestamp-only commits/week that bury the commits representing real lease movement. That ruling stands unchanged; only the mechanism enforcing it moved. **Why it moved:** the original fix filtered exactly one field, `meta.generatedAt`, *by name*, and went stale the moment a second clock arrived. The `quickbooks` block (populated ~2026-08-17) carries its own `parsedAt`, so on 2026-08-27 this task's run produced a 4-line diff — two clock pairs and nothing else, structurally identical to `HEAD` — which the by-name filter read as "real portfolio data moved" and would have committed *and pushed* to `origin/main`. That is the same failure class as the shrink guard's hardcoded-list-keys gap (`reference_cc_snapshot_shrink_guard_covers_lists_only.md`): a by-name filter silently goes stale when a new section lands. Decide **structurally** instead, from the `oxford-command-center` repo root:

  ```bash
  python -c "
import json, re, subprocess
# Structural material-change gate (replaced the by-name grep filter 2026-08-27).
# Strips WRITE-CLOCK stamps -- any key ending in 'At' whose value is an ISO-8601
# datetime -- recursively from BOTH sides, then compares what is left. Schema-agnostic
# by construction: a FUTURE clock field (a new section's 'refreshedAt', 'syncedAt', ...)
# is handled with no edit to this spec, which is exactly what the by-name filter could
# not do. Real data is untouched -- 'asOf', 'asOfDate', 'daysToExpiry',
# 'monthsToMaturity', 'holdYrs' and every lease/loan/deal/counterparty value still count
# as material, so genuine clock-driven drift is still committed as before.
# KNOWN RESIDUAL, disclosed not silently accepted: a genuine BUSINESS timestamp that
# happens to end in 'At' (a lease 'signedAt', a comp's 'sourcedAt') is suppressed too.
# It is never silent -- every suppressed path prints on the 'suppressed as write-clock:'
# line, so it lands in the run report where a human can catch it. As of 2026-08-27 the
# live snapshot carries four: meta.generatedAt, quickbooks.parsedAt, and two
# dealComps.*.sourcedAt. If a suppressed path ever looks like business data whose
# movement SHOULD trigger a commit, escalate -- do not silently widen or narrow the strip.
# Keep this block in sync with the identical gate in the sibling snapshot task.
Q = chr(34)
ISO = re.compile('^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}')
stripped = set()
def strip(o, path=''):
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            if isinstance(k, str) and k.endswith('At') and isinstance(v, str) and ISO.match(v):
                stripped.add((path + '.' + k).lstrip('.')); continue
            out[k] = strip(v, path + '.' + k)
        return out
    if isinstance(o, list):
        return [strip(x, path + '[' + str(i) + ']') for i, x in enumerate(o)]
    return o
head = json.loads(subprocess.run(['git','show','HEAD:data/snapshots/portfolio.json'],capture_output=True,text=True,encoding='utf-8').stdout)
work = json.load(open('data/snapshots/portfolio.json', encoding='utf-8'))
material = strip(head) != strip(work)
if stripped: print('suppressed as write-clock: ' + ', '.join(sorted(stripped)))
print('MATERIAL: ' + ('yes' if material else 'none'))
if material:
    clocks = set(p.split('.')[-1] for p in stripped)
    for ln in subprocess.run(['git','diff','-U0','--','data/snapshots/portfolio.json'],capture_output=True,text=True,encoding='utf-8').stdout.splitlines():
        if ln.startswith('+++') or ln.startswith('---'): continue
        if not (ln.startswith('+') or ln.startswith('-')): continue
        if any(ln.lstrip('+-').strip().startswith(Q + k + Q + ':') for k in clocks): continue
        print('  ' + ln)
"
  ```

  Read the printed **`MATERIAL:`** verdict — branch on that word, never on the command's exit code (it exits 0 either way). A crash, an unreadable file, or unparseable JSON prints no verdict at all: that is a guard-condition failure, so surface it and do NOT commit, rather than reading a missing verdict as `none`. (`encoding='utf-8'` is required on both reads: this file has bytes that break Python's default cp1252 on Windows.)
  - **`MATERIAL: none`** → only write-clocks moved. Do NOT commit. Run `git restore data/snapshots/portfolio.json` so the shared checkout isn't left permanently dirty, then skip the rest of this section. The only content discarded is the clock stamps the script wrote seconds earlier, which the next run regenerates; lease data is by definition structurally identical to `HEAD` in this branch. If the `restore` itself fails, treat that as a guard-condition failure and surface it rather than leaving the tree dirty and silent.
  - **`MATERIAL: yes`** → real portfolio data moved. Continue to the **section-shrink guard** and sanity check below, and quote the printed `+`/`-` lines in the run report — that is the actual change, and on an Exit 0 it is the *only* place it surfaces (the drift reporter only speaks up for new/removed/date-changed leases, so a rent or SF correction lands here as an Exit 0 with a material diff).
- **Section-shrink guard (added 2026-08-09 after the seed-fallback near-miss — run this on EVERY `MATERIAL: yes`, before staging anything).** A material diff is not proof of portfolio movement: it is equally the signature of a *degraded write*. On 2026-08-09 07:40 ET a transient `[notion-deals] live fetch failed, using seed: fetch failed` made the script write the ~6-deal seed placeholder set over the live pipeline — `deals` 20 → 6, `counterparties` 15 → 14, `leases` unchanged — and still exit 0. The material-change gate as written above read that wipe as "real portfolio data moved" and would have committed and (per Auto-push) published it to `origin/main`, silently, because Exit 0 suppresses both alert channels. Compare the working copy against `HEAD` and refuse on any **shrink**:

  ```bash
  python -c "
import json, subprocess
head = json.loads(subprocess.run(['git','show','HEAD:data/snapshots/portfolio.json'],capture_output=True,text=True,encoding='utf-8').stdout)
work = json.load(open('data/snapshots/portfolio.json', encoding='utf-8'))
for k in ('leases','deals','counterparties','properties','loans'):
    h, w = len(head.get(k,[])), len(work.get(k,[]))
    print(('SHRINK ' if w < h else 'ok     ') + f'{k}: {h} -> {w}')
# Generic non-list section-shrink check (added 2026-08-24, OI-137/quickbooks incident):
# the list-key loop above only ever covered 5 hardcoded keys, so the 2026-08-17 incident
# (a CLI writer nulling the whole server-attached 'quickbooks' dict -- 828 deleted lines --
# see reference_cc_snapshot_shrink_guard_covers_lists_only.md) went undetected. This check is
# schema-agnostic -- any top-level key that was a non-empty/non-null value in HEAD and is
# null or empty (dict/list/str) in the working copy is flagged, so a FUTURE server-attached
# section shaped like quickbooks is automatically covered without a bespoke fix. SKIP excludes
# keys with their own, different-from-'bigger-is-better' semantics: the 5 list keys (already
# handled above), 'meta' (generatedAt always differs -- noise, not signal), and 'dataQuality'
# (fewer flags is an IMPROVEMENT per the sibling task's ratified severity gate, not a defect).
# KNOWN RESIDUAL, disclosed not silently accepted: this only catches a section's TOP LEVEL going
# populated -> empty/null. A nested list shrinking while the parent dict stays non-empty (e.g.
# quickbooks.properties dropping some but not all rows) is NOT caught -- would need per-section
# shape knowledge, which is exactly what 'generic' is trying to avoid. Strictly better than
# before (zero coverage of non-list sections), not a claim of full coverage. Keep this block in
# sync with the identical guard in ora-cc-snapshot-refresh -- see this file's own header note.
SKIP = {'leases','deals','counterparties','properties','loans','meta','dataQuality'}
def is_empty(v):
    if v is None: return True
    if isinstance(v, (list, dict, str)): return len(v) == 0
    return False
for k in sorted(set(head) | set(work)):
    if k in SKIP: continue
    h, w = head.get(k), work.get(k)
    if not is_empty(h) and is_empty(w):
        print(f'SHRINK  {k}: populated -> empty/null')
"
  ```

  Any `SHRINK` line → do **NOT** commit, do **NOT** push. `git restore data/snapshots/portfolio.json` and escalate with a QUESTION FOR GABRIEL quoting the counts. A genuine disposition or deal retirement also shrinks a section, so this is a *stop-and-ask*, not a verdict — but it must be Gabriel's call, never an unattended commit. (Note `encoding='utf-8'` is required: this file has bytes that break Python's default cp1252 on Windows.)
- **Degradation check.** Independently of the counts, scan the script's stdout/stderr for `[notion-deals] live fetch failed` or `live fetch returned 0 deals`. As of the 2026-08-09 script fix these should now surface as an **Exit 1** refusal (`parse.ts` raises an error-severity `dataQuality` flag on a data-losing deals degradation, and `evaluateReconciliationGate` refuses the write; a missing `NOTION_TOKEN` is refused separately by `requireLiveDealsSource`). If you ever see one of those messages on an Exit 0/2 run, the fix has regressed — refuse to commit and escalate.
- **Worktree-sanity check, before touching git at all (replaces the old shared-checkout repo-sanity check — see Worktree isolation above).** This run's worktree is private by construction (unique path, unique branch, forked fresh from a just-fetched `origin/main`), so there is no other session to collide with inside it — check anyway, as defense-in-depth: `git status --short` (no path filter) and `git log -1`, run inside the worktree. If the worktree is mid-merge/mid-rebase (a `MERGE_HEAD` or `rebase-merge`/`rebase-apply` directory present) or `HEAD` is detached, something went wrong creating it — do NOT commit, treat it exactly like a guard-condition failure below (report the anomaly, escalate with a QUESTION FOR GABRIEL) and go straight to Cleanup rather than leaving a broken worktree behind. (There is deliberately no "not on `main`" check here — this worktree is never on `main`; this run never touches that ref directly — `main` moves only when its PR merges (Auto-push below).) The risk this check used to be the sole protection against — colliding with a human's or another session's in-progress work in this shared checkout — now lives only at that final push; everything before it (script run, read, every comparison guard, commit) runs against this run's own isolated `HEAD`, so a concurrent session's mid-run commit to the live checkout can no longer be silently read as this run's baseline or missed by a point-in-time check.
- If other files besides `data/snapshots/portfolio.json` are also dirty, that is pre-existing WIP that is not this task's to touch — never `git add -A` / `git add .`. Stage ONLY the one file: `git add data/snapshots/portfolio.json`.
- Commit with a message summarizing the script's own printed counts, e.g. `Auto-refresh: lease snapshot (138 leases, no drift)` for Exit 0, or `Auto-refresh: lease snapshot (139 leases; drift: +2 new / -1 removed / 3 date-changed)` for Exit 2 — pull the actual numbers from stdout, never fabricate them.
- A commit failure (hook rejection, lock file, anything non-clean) is a guard-condition failure, not a silent skip — surface it the same way as the exit-code alarms below rather than swallowing it.

## Auto-push (Gabriel directive 2026-08-09 — supersedes the prior "commit locally, never push" default)

Through 2026-08-08 this task committed on `main` and stopped, because an unattended push to the shared remote was a standing decision Gabriel had not made. He made it on 2026-08-09 (after a manual push of `8e4f51e`): **once a commit has been made per Auto-commit above, push it.** No commit → nothing to push; this whole section is skipped.

Landing publishes this run's branch as a PR and, once merged, every commit on it to `main`, not just this task's — so the guards below exist to make sure that's only ever this task's own commit.

- **Fetch before deciding — never push blind.** `git fetch origin`, then read the divergence:

  ```bash
  git rev-list --left-right --count origin/main...HEAD   # output: "<behind>	<ahead>"
  git log origin/main..HEAD --oneline
  ```
- **Land only from a base that has not moved (behind-count `0`; protection is strict).** Behind-count must be `0`. If it is non-zero, `origin/main` has moved since the last local commit — do **NOT** push, and do **NOT** merge, rebase, reset, pull, or `--force`/`--force-with-lease` to make it pushable. The commit stays local and safe; report the divergence as a guard-condition failure with a QUESTION FOR GABRIEL and let a human reconcile the shared checkout.
- **Push only automation snapshot commits — both writers' (widened by Gabriel ruling 2026-08-11; was this task's own prefix only).** Every commit subject listed by `git log origin/main..HEAD` must match:

  ```
  ^Auto-refresh: (CC|lease) snapshot
  ```

  If anything else is ahead — a human's or another session's work deliberately left unpushed — do **NOT** push; pushing would publish their work as a side effect of a snapshot refresh. Surface it instead, same as above.

  **Why `CC` as well as this task's own `lease`.** `ora-cc-snapshot-refresh` writes the same tracked `data/snapshots/portfolio.json` under the same anomaly floor, material-change gate, and shrink guard, and gained its own Auto-push section on 2026-08-11. From that point on either task can find the other's commit ahead of `origin/main`: whichever commits second would read it as a human's unpushed work and refuse, deadlocking the pair. That forward-looking collision is the whole reason for the widened pattern. Neither task can publish work a human meant to hold back, because a human commit does not match it. Keep it in sync with the identical guard in `ora-cc-snapshot-refresh`.

  **Rationale corrected 2026-08-12 (transcript-verified) — do not restore the old wording.** This paragraph previously cited `0b5b36e`'s stranding as that deadlock actually occurring. It was not. Session `1de11c79-1c29-4ad7-8e6b-20c60c5f8279` (the `ora-cc-snapshot-refresh` run of 2026-08-11, `createdAt` 22:39:34Z) evaluated **no push guard at all** — that task had neither an Auto-push nor an Auto-commit section that day, and its own run report reads: *"Committed locally as `0b5b36e` … Not pushed — no push step is in the spec."* Its commit was an unattended run improvising against an unwritten rule. A deadlock was impossible regardless: that run's pre-flight recorded `origin/main` at `b9a58c2` with a clean tree, so after committing exactly one commit — its own — was ahead, and an own-prefix guard would have matched and pushed it. The widened pattern **stands** on its forward-looking merit above; only the false historical evidence is withdrawn. Do not re-narrow to a single prefix on the strength of that retracted claim.
- **Why a PR, not a push (Gabriel Option A, 2026-09-19).** `main` has been branch-protected since OI-205 (2026-08-24; required checks `gate` + `refute-required`, `enforce_admins`). Both required checks must already be reported on the pushed commit before GitHub accepts it — `refute-required` runs only on pull requests and `gate` only reports after a push lands, too late — so every direct `git push origin HEAD:main` is refused with GH006. Protection is also *strict*: a PR branch must be up to date with `main` to merge. That stranded the 2026-09-14 commits (`a2e4e1b`, and `ora-cc-snapshot-refresh`'s `de59723`) on local branches for five days.
- **One open snapshot PR at a time — check BEFORE pushing.** `gh pr list --repo ZeOoba/oxford-command-center --state open --json number,title,headRefName,createdAt,mergeStateStatus,autoMergeRequest,statusCheckRollup --jq '[.[]|select(.title|test("^Auto-refresh: (CC|lease) snapshot"))]'` — deliberately not `--search`, whose index can lag a seconds-old PR. If the result is non-empty do NOT open a second PR: both writers edit the same file and the second is stale the moment the first merges. First, if it reads `BEHIND`, run exactly one `gh pr update-branch <n> --repo ZeOoba/oxford-command-center` (never rebase or force) and re-read it once. Then: **if it is under 60 minutes old, `autoMergeRequest` is set, `mergeStateStatus` is not `DIRTY`, and no `statusCheckRollup` entry has `conclusion` `FAILURE`, `CANCELLED` or `TIMED_OUT`, it is in flight — report this run as SUPERSEDED and stop: keep this run's local branch, no alarm** (the sibling writer's PR carries the same regenerated file; with the landing poll below the sibling's PR is normally MERGED before this run even starts, in which case nothing is open and this run simply forks from the new `origin/main`). Anything else — older than 60 minutes, auto-merge not armed, `DIRTY`, a failed check, still `BEHIND` — is stuck: alarm as below; do not close, merge or rebase it.
- Both guards satisfied and no PR open → land it through a **pull request**, run inside the worktree (bash syntax — run these through Bash, never cmd.exe):

  ```bash
  git push origin HEAD:refs/heads/auto/lease-snapshot-<runid>
  gh pr create --repo ZeOoba/oxford-command-center --base main --head auto/lease-snapshot-<runid> --title "<this commit's subject, verbatim>" --body-file "<tmp file>"
  gh pr merge <pr-number> --repo ZeOoba/oxford-command-center --auto --squash
  gh pr view <pr-number> --repo ZeOoba/oxford-command-center --json state,mergeStateStatus,autoMergeRequest,statusCheckRollup     # first poll — see the landing poll below
  ```

  Use the commit subject verbatim as the PR title (GitHub squashes a one-commit PR under the commit subject and appends ` (#N)`), so what lands on `main` keeps the `^Auto-refresh: (CC|lease) snapshot` prefix. The body carries the material-change verdict, the drift lines verbatim, the section counts against `origin/main`, and ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. The required checks `gate` and `refute-required` gate the merge; data-only snapshot PRs have cleared them in about 12 minutes (#344; #321 additionally needed a human merge of `main` into its branch, because protection is strict). **Never** `git push origin HEAD:main`, `--admin`, `--no-verify` or any force variant, and never exempt this automation from the checks — that reopens the hole OI-205 closed (a direct push skipped `refute-required`).
- **Bounded landing poll — the run that creates the PR owns it until it is MERGED or alarmed.** Both snapshot tasks are Monday-only, so nothing else would notice a stuck PR for a week. After arming auto-merge, poll `gh pr view <pr-number> --repo ZeOoba/oxford-command-center --json state,mergeStateStatus,autoMergeRequest,statusCheckRollup` about every 2 minutes for at most 20 minutes, waiting between polls with `powershell -NoProfile -Command "Start-Sleep -Seconds 90"` (kept under the Bash tool's 120 s timeout — the same wait pattern `ora-routine-pause-resume-09-21` uses). `mergeStateStatus` reads `UNKNOWN` for the first minutes after creation (GitHub computes it lazily): treat it as pending, never as a fault. Per poll: `state` `MERGED` → landed, stop. `mergeStateStatus` `BEHIND` → run exactly ONE `gh pr update-branch <pr-number> --repo ZeOoba/oxford-command-center` (protection is strict and auto-merge does not update a BEHIND branch; the merge commit it adds is flattened by the squash, and the own-commits guard already ran before the push) and keep polling. Any `statusCheckRollup` entry with `conclusion` `FAILURE`, `CANCELLED` or `TIMED_OUT`, `mergeStateStatus` `DIRTY`, or `autoMergeRequest` null → stuck: alarm at once. Still `OPEN` at 20 minutes → alarm as LANDING UNVERIFIED and say so. Never close, merge or rebase the PR. Only the exit codes of `git push`, `gh pr create` and `gh pr merge --auto` decide push/create/arm failure — never `gh pr checks`, which exits non-zero while checks are merely pending.
- **Report what was observed.** Write "PR #N MERGED" only after the poll read `MERGED`; otherwise "PR #N opened, auto-merge armed — not yet merged" with the reason; never "pushed to main". The `ora-am-brief` snapshot read additionally depends on the live `oxford-command-center` checkout being advanced, which is NOT this task's job (and no other task does it yet — known gap): do not pull, merge or reset it from here. The CC mirror is unaffected — it builds from `origin/main` in its own build root.
- Any of push / PR create / auto-merge failing (auth, network, `gh` absent or unauthenticated, GH006 anyway) is a guard-condition failure: keep this run's local branch (Cleanup rule), report its name and sha, and put the exact manual commands in a QUESTION FOR GABRIEL. Retry at most once, and only for a plainly transient network error. Report the PR number/URL and the branch tip sha in the run report. **Every failure or stuck outcome in this section is an Exit-3-class alarm for exit-code routing — Notion AND email to ggoldberg only — even on an exit 0 or 2 run**; a silent landing failure is exactly how the 2026-09-14 stranding went unseen for five days. SUPERSEDED (above) is the only silent non-landing outcome.
- Still **no** Notion post and **no** email for an Exit 0 run whose PR the landing poll read as `MERGED`; opened-and-armed but not yet `MERGED` at the 20-minute cap is the LANDING UNVERIFIED alarm, not silence. A failed, stuck or unverifiable landing is an alarm (above) and **overrides** the Exit 0 silence rule in the exit-code handling below for that case only.
- **Whatever happens above — pushed, refused, or failed — Cleanup (Worktree isolation section) is always the next and last step.**
