---
name: ora-lease-snapshot-refresh
description: Weekday 1x/day (07:40 ET, collapsed from 3x/day 2026-08-05 per ORA-wide once/day cadence policy) regeneration of oxford-command-center's data/snapshots/portfolio.json via scripts/lease-snapshot-drift-check.ts, independent of interactive server uptime — reports lease drift (new/removed/date-changed) with an anomaly floor that refuses to write on a suspicious parse (closes the 2026-07-24 lease-date integrity incident, PR #232). On a successful write (exit 0/2) with lease data that actually moved (material-change gate structurally ignores write-clock-only churn) auto-commits locally, then auto-pushes to origin/main fast-forward-only under a section-shrink + deals-degradation guard and an own-commits-only pattern ^Auto-refresh: (CC|lease) snapshot shared with ora-cc-snapshot-refresh (never any force variant). 2026-08-03 phantom-lease incident (parse.ts:476) CLOSED. Full versioned changelog lives in the body of this file (migrated from frontmatter, class-n remediation 2026-08-17). [MODEL: claude-opus-5 observed | checked 2026-08-09 via live-run transcript canary]
---

You are running the scheduled task `ora-lease-snapshot-refresh` for Oxford Realty Advisors. This regenerates `data/snapshots/portfolio.json` in the `oxford-command-center` repo (`C:\Users\Owner\oxford-command-center`) via `scripts/lease-snapshot-drift-check.ts`, on a cadence independent of whether the interactive Command Center dev/prod server happens to be running (that dependency was the root cause of a 2026-07-24 lease-date integrity incident — the Command Center's alerts engine and its own portfolio snapshot disagreed about the portfolio's largest near-term lease expiration because the snapshot had gone stale). Full context: `CHANGELOG.md`'s "Stable lease ids + overlay-write hardening (2026-07-24)" entry and `docs/superpowers/plans/2026-07-24-lease-id-integrity-fix-plan.md` Task 3, both in that repo.

## Steps

1. Worktree isolation: create this run's own private worktree per the **Worktree isolation** section below (stale-worktree sweep, then `npm run worktree -- add` off a freshly-fetched `origin/main`, then copy `.env` in). Every step from here on runs inside that worktree, never against the live `oxford-command-center` checkout directly — the live checkout is touched only to fetch and to create/remove the worktree; the shared `main` ref is touched only by the final fast-forward push.
2. Run, from inside the worktree: `npx tsx scripts/lease-snapshot-drift-check.ts`
3. Read the exit code AND the full stdout/stderr output — the exit code alone doesn't carry the detail a human needs.
4. On Exit 0 or Exit 2 only, commit the regenerated snapshot per "Auto-commit" below — from inside the worktree, comparing against the worktree's own `HEAD`.
5. If step 4 produced a commit, push it per "Auto-push" below (fast-forward only, automation snapshot commits only — see that section for which prefixes qualify), from inside the worktree.
6. **Regardless of exit code, and regardless of which Auto-commit/Auto-push branch this run takes** (committed-and-pushed, a `MATERIAL: none` no-op, a shrink/degradation refusal, a push refusal, or a crash mid-guard) **the last action of this run is always Cleanup**, per the Worktree isolation section below. Never leave a run's worktree behind on disk.

## ✅ 2026-08-03 phantom-lease incident — CLOSED, suspension LIFTED 2026-08-03 20:2x UTC (Gabriel ruling)

This task was suspended (write, then write-and-commit) 2026-08-03 after `parse.ts:476`'s `propertyKey` guard stringified a Date instead of rejecting it, ingesting the rent roll's derived "VACANCY & UPCOMING AVAILABILITY" block as 10 phantom leases (138 → 148 leases, annual rent +$312,540). Full diagnosis: `memory/reference_parseleases_vacancy_block_phantom_leases_2026-08-03.md`.

Both halves of the lifting condition are now done and independently verified, not merely merged:
1. **Parser fix** — [PR #250](https://github.com/ZeOoba/oxford-command-center/pull/250) (`d35931a`).
2. **checkSnapshot wired into both CLI writers as defense-in-depth** — [PR #252](https://github.com/ZeOoba/oxford-command-center/pull/252) (`1185638`). `evaluateReconciliationGate()` refuses the write on any error-severity flag from `checkSnapshot()` + `snapshot.dataQuality`. Live A/B proof against the real production workbook (fix reverted vs. present, in an isolated worktree) confirmed both writers now refuse with the exact incident numbers instead of writing corrupt data.

First live resume, run by hand 2026-08-03 20:2x UTC on synced `main`: clean write, 138 leases, $5,576,537, 0 flags, both gates passed. Committed (`fa9ed8b`, "Auto-refresh: lease snapshot (138 leases, no drift)") — the material-change gate found a genuine non-timestamp diff (5 days of accumulated portfolio movement: loan amortization, rent/NOI changes — not corruption) and correctly did not restore/discard it. **Normal cadence resumes at the next scheduled fire; STEPS above apply as written, no special handling needed.**

## Worktree isolation (added 2026-09-02 — closes the Qodo review gap on this file's Auto-commit section: no isolation existed between the drift-check script and the eventual `git add`/commit, so a concurrent session's commit landing on `oxford-command-center`'s `main` mid-run, or a concurrent edit mid-run, could go undetected by the repo-sanity check's point-in-time snapshot alone)

Every run of this task gets its own **private, ephemeral git worktree** — a fresh checkout of `origin/main` that only this run touches. The drift-check script, every comparison guard (material-change, section-shrink, degradation), and the commit all happen INSIDE that worktree, against the worktree's OWN `HEAD` — never against the live checkout's working tree. The only point where a run touches the actually-shared `main` ref is the final fast-forward `git push`.

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
cd C:\Users\Owner\oxford-command-center
git fetch origin
git worktree list --porcelain
```
For any listed worktree whose path is under `C:\Users\Owner\AppData\Local\Temp\ora-cc-worktrees\` and starts with `lease-snapshot-` (left behind by a crashed or killed prior run of THIS task — a stale `cc-snapshot-` worktree is the sibling task's own concern, leave it alone), check whether it holds an unpushed automation commit before touching it:
```bash
git -C "<stale-path>" log origin/main..HEAD --oneline
```
- **No commits listed, or none matching `^Auto-refresh: (CC|lease) snapshot`** → safe to discard. `npm run worktree -- remove "<stale-path>"`, then `git branch -D <its-auto-branch>`, then continue to worktree creation below.
- **A matching commit IS listed** → do NOT delete it. A prior run committed but crashed or was killed before pushing. Leave that stale worktree exactly as found, do NOT create a new worktree this run, and escalate with a QUESTION FOR GABRIEL quoting the stranded commit subject(s) and the stale worktree path — this needs a human to reconcile (push it by hand, or discard it deliberately), the same standing rule as any other contaminated shared-checkout tree (`rules.md` §14). Treat this like an Exit-3/Exit-1-class alarm for the exit-code handling below (post to Notion AND email) even though the drift-check script itself never got a chance to run this cycle.

**Create this run's worktree**, from the live checkout, once the sweep above finds nothing to stop for:
```bash
cd C:\Users\Owner\oxford-command-center
npm run worktree -- add "C:\Users\Owner\AppData\Local\Temp\ora-cc-worktrees\lease-snapshot-<runid>" origin/main "auto/lease-snapshot-<runid>"
```
This wraps `scripts/safe-worktree.ts` (PR #29), which does a REAL `npm install` inside the new worktree — its own independent `node_modules`, never a directory junction back to the live checkout's. A junctioned worktree, later force-removed, is exactly what once deleted the live checkout's real `node_modules` and broke its tooling for every session (`reference_worktree_node_modules_junction_hazard.md`) — this procedure never does that. If `npm run worktree` is ever missing or broken, fall back by hand: `git worktree add "<path>" -b "auto/lease-snapshot-<runid>" origin/main`, then `npm install` inside `<path>` — but never junction `node_modules` for speed.

**Copy `.env` into the new worktree.** `git worktree add` only brings tracked files; `.env` is gitignored, so the drift-check script cannot find `WORKBOOK_PATH` without this step. Copy `C:\Users\Owner\oxford-command-center\.env` to `<worktree-path>\.env` (Desktop Commander file copy) before running the script.

Every step above and below — the script run, Auto-commit, Auto-push — now runs with the worktree as the working directory, never the live checkout.

**Cleanup — unconditional, every exit path, always the last action of the run.** Whether this run committed and pushed, restored a `MATERIAL: none` no-op, refused on a shrink/degradation guard, failed to push on a non-fast-forward, or crashed mid-guard: remove the worktree before finishing.
```bash
cd C:\Users\Owner\oxford-command-center
npm run worktree -- remove "<worktree-path>"
git branch -D "auto/lease-snapshot-<runid>"
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
- **Worktree-sanity check, before touching git at all (replaces the old shared-checkout repo-sanity check — see Worktree isolation above).** This run's worktree is private by construction (unique path, unique branch, forked fresh from a just-fetched `origin/main`), so there is no other session to collide with inside it — check anyway, as defense-in-depth: `git status --short` (no path filter) and `git log -1`, run inside the worktree. If the worktree is mid-merge/mid-rebase (a `MERGE_HEAD` or `rebase-merge`/`rebase-apply` directory present) or `HEAD` is detached, something went wrong creating it — do NOT commit, treat it exactly like a guard-condition failure below (report the anomaly, escalate with a QUESTION FOR GABRIEL) and go straight to Cleanup rather than leaving a broken worktree behind. (There is deliberately no "not on `main`" check here — this worktree is never on `main`; only the final push touches that ref, under its own fast-forward guard in Auto-push below.) The risk this check used to be the sole protection against — colliding with a human's or another session's in-progress work in this shared checkout — now lives only at that final push; everything before it (script run, read, every comparison guard, commit) runs against this run's own isolated `HEAD`, so a concurrent session's mid-run commit to the live checkout can no longer be silently read as this run's baseline or missed by a point-in-time check.
- If other files besides `data/snapshots/portfolio.json` are also dirty, that is pre-existing WIP that is not this task's to touch — never `git add -A` / `git add .`. Stage ONLY the one file: `git add data/snapshots/portfolio.json`.
- Commit with a message summarizing the script's own printed counts, e.g. `Auto-refresh: lease snapshot (138 leases, no drift)` for Exit 0, or `Auto-refresh: lease snapshot (139 leases; drift: +2 new / -1 removed / 3 date-changed)` for Exit 2 — pull the actual numbers from stdout, never fabricate them.
- A commit failure (hook rejection, lock file, anything non-clean) is a guard-condition failure, not a silent skip — surface it the same way as the exit-code alarms below rather than swallowing it.

## Auto-push (Gabriel directive 2026-08-09 — supersedes the prior "commit locally, never push" default)

Through 2026-08-08 this task committed on `main` and stopped, because an unattended push to the shared remote was a standing decision Gabriel had not made. He made it on 2026-08-09 (after a manual push of `8e4f51e`): **once a commit has been made per Auto-commit above, push it.** No commit → nothing to push; this whole section is skipped.

`git push` publishes *every* local commit on `main`, not just this task's — so the guards below exist to make sure that's only ever this task's own commit.

- **Fetch before deciding — never push blind.** `git fetch origin`, then read the divergence:

  ```bash
  git rev-list --left-right --count origin/main...HEAD   # output: "<behind>	<ahead>"
  git log origin/main..HEAD --oneline
  ```
- **Push only on a clean fast-forward.** Behind-count must be `0`. If it is non-zero, `origin/main` has moved since the last local commit — do **NOT** push, and do **NOT** merge, rebase, reset, pull, or `--force`/`--force-with-lease` to make it pushable. The commit stays local and safe; report the divergence as a guard-condition failure with a QUESTION FOR GABRIEL and let a human reconcile the shared checkout.
- **Push only automation snapshot commits — both writers' (widened by Gabriel ruling 2026-08-11; was this task's own prefix only).** Every commit subject listed by `git log origin/main..HEAD` must match:

  ```
  ^Auto-refresh: (CC|lease) snapshot
  ```

  If anything else is ahead — a human's or another session's work deliberately left unpushed — do **NOT** push; pushing would publish their work as a side effect of a snapshot refresh. Surface it instead, same as above.

  **Why `CC` as well as this task's own `lease`.** `ora-cc-snapshot-refresh` writes the same tracked `data/snapshots/portfolio.json` under the same anomaly floor, material-change gate, and shrink guard, and gained its own Auto-push section on 2026-08-11. From that point on either task can find the other's commit ahead of `origin/main`: whichever commits second would read it as a human's unpushed work and refuse, deadlocking the pair. That forward-looking collision is the whole reason for the widened pattern. Neither task can publish work a human meant to hold back, because a human commit does not match it. Keep it in sync with the identical guard in `ora-cc-snapshot-refresh`.

  **Rationale corrected 2026-08-12 (transcript-verified) — do not restore the old wording.** This paragraph previously cited `0b5b36e`'s stranding as that deadlock actually occurring. It was not. Session `1de11c79-1c29-4ad7-8e6b-20c60c5f8279` (the `ora-cc-snapshot-refresh` run of 2026-08-11, `createdAt` 22:39:34Z) evaluated **no push guard at all** — that task had neither an Auto-push nor an Auto-commit section that day, and its own run report reads: *"Committed locally as `0b5b36e` … Not pushed — no push step is in the spec."* Its commit was an unattended run improvising against an unwritten rule. A deadlock was impossible regardless: that run's pre-flight recorded `origin/main` at `b9a58c2` with a clean tree, so after committing exactly one commit — its own — was ahead, and an own-prefix guard would have matched and pushed it. The widened pattern **stands** on its forward-looking merit above; only the false historical evidence is withdrawn. Do not re-narrow to a single prefix on the strength of that retracted claim.
- Both guards satisfied → `git push origin HEAD:main`, run inside the worktree. This run's worktree is checked out on `auto/lease-snapshot-<runid>`, not `main` — `HEAD:main` pushes this run's commit onto the shared `main` ref without ever checking `main` itself out locally, and git still enforces fast-forward-only on the destination ref exactly as a plain `git push origin main` would. Report the pushed range (`<old>..<new>`) in the run report.
- A push failure (rejected, auth, network, pre-push hook) is a guard-condition failure, not a silent skip — surface it. Do not retry with any force variant, and do not retry more than once for a plainly transient network error.
- Still **no** Notion post and **no** email for an Exit 0 push — the exit-code routing below is unchanged by this section.
- **Whatever happens above — pushed, refused, or failed — Cleanup (Worktree isolation section) is always the next and last step.**

## Exit code handling (differentiated 0/1/2/3 — do not treat them the same)

- **Exit 0 (clean, no drift):** nothing to report to Notion/email. Still runs the Auto-commit step above, but expect the *usual* Exit 0 outcome to be **no commit and a restored, clean tree** — the material-change gate suppresses the timestamp-only churn. An Exit 0 that *does* commit means a non-date field (rent, SF, tenant attribute) moved without tripping the drift reporter; that is the informative case and belongs in the run report. Do not post to Notion, do not email regardless of whether a commit happened.
- **Exit 2 (wrote portfolio.json, found drift worth a look — new/removed/date-changed leases):** this is routine, not an alarm. Post a brief status note to the Notion Operations Hub (page `32b6ecd8-9e59-81f2-b329-df3fd0e25062`, or search for "Operations Hub" if that ID has moved — verify before trusting a hardcoded ID) summarizing the new/removed/date-changed lease counts from the script's own printed output. No email for this case. Also runs the Auto-commit step above.
- **Exit 1 (refused to write — anomaly floor tripped, or corrupt overlay/previous-snapshot):** `portfolio.json` is UNCHANGED, real financial/portfolio data is stale until a human investigates. This is an alarm: post to Notion Operations Hub AND email `ggoldberg@oxfordra.net` ONLY (no cc — routing canon, see CLAUDE.md Email & scheduler section) via the Outlook COM send path (`C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` — the SOLE send path). Quote the script's own refusal message verbatim in both the Notion note and the email so the specific cause (overlay corruption, previous-snapshot corruption, 0-lease parse, >25% lease removal, **or — as of 2026-08-09 — an unavailable Notion deals pipeline**) is immediately visible, not just "it refused." Do NOT retry automatically and do NOT pass `--force` — this needs a human decision, not an automated override.
  - **Deals-pipeline refusals are usually transient.** `Notion deals pipeline unavailable (fetch-failed)` means one Notion request failed, not that data is corrupt; the refusal is doing its job (a seed-placeholder wipe was prevented, `portfolio.json` is intact and simply not refreshed this cycle). Note that in the alert so it reads as "refresh skipped, data safe" rather than "portfolio data is corrupt." If it recurs on consecutive fires, that is a real outage or a revoked/expired `NOTION_TOKEN` and warrants investigation. Still never `--force`: forcing writes the placeholders, which is the exact damage the guard exists to prevent.
- **Exit 3 (unexpected crash — parseWorkbook failure, missing worksheet, workbook locked mid-sync):** same alarm treatment as exit 1 (Notion + email, ggoldberg only, quote the error). On a COM send failure specifically: retry the send once, then flag loudly in the Notion completion row if it still fails — do not silently drop the alert.

## Guard conditions

- If the script itself is missing (e.g. this task fires before a future revert of the branch that added it), report that clearly as a setup/environment problem in the Notion note and email — do not fabricate a "no drift" result.
- Never fabricate lease counts, drift details, or a "clean" result if the script's actual output is ambiguous or unparseable — if you can't tell what happened from the output, say so explicitly and escalate with a QUESTION FOR GABRIEL rather than guessing.

## Pointers, not duplication

- Do not re-implement the drift-check's own logic (id comparison, staleness thresholds, anomaly floor) — that all lives in the script itself and in `server/config.ts`'s `isSnapshotStale`. This task's only job is to run the script, read its output, and route the result (silent / Notion-only / Notion+email) per the exit code.
- **Corrected 2026-07-26 — the line below was stale.** `ora-cc-snapshot-refresh` (weekly Monday `npm run extract`) now shares BOTH the anomaly floor AND the drift report with this task (`evaluateAnomalyFloor`/`formatDriftReport`, exported from `scripts/lease-snapshot-drift-check.ts` and imported by `scripts/extract-workbook.ts`) — see event_log.md, "orphaned-task-forensics: portfolio.json snapshot regression" and its follow-ups, 2026-07-26. A manual off-schedule `npm run extract` run corrupted two tenants' lease-end dates on 2026-07-25 specifically because that path had neither protection at the time. `ora-cc-snapshot-refresh` remains the lower-frequency (weekly) backstop by CADENCE — this task is still the primary, more-frequent (3x/weekday) refresh path — but it is no longer the only one with data-integrity protection. Do not repeat the old "no anomaly floor, no drift reporting" framing.

## Changelog — MIGRATED FROM FRONTMATTER (v1.8, 2026-08-17, class-n remediation)

*The frontmatter `description` field previously carried both an un-versioned preamble (retiming history, git-tracking decision, phantom-lease incident) and versioned entries v1.4-v1.7. The versioned entries were auto-migrated by the class-n tool (real "vX.Y (YYYY-MM-DD" pointer fragments). The preamble below has no version marker the tool's fragment scan recognizes, so it is moved here by hand, verbatim, per the same MOVE-TO-BODY doctrine — not because a pointer pointed at it, but because deleting it from the description without a body copy would be exactly the loss class n exists to prevent.*

Original preamble: Weekday 3x/day (7:40am/1:40pm/7:40pm ET) regeneration of oxford-command-center's data/snapshots/portfolio.json via scripts/lease-snapshot-drift-check.ts, independent of interactive server uptime — keeps the snapshot within its 6h staleness threshold and reports lease drift (new/removed/date-changed) with an anomaly floor that refuses to write on a suspicious parse. Closes the 2026-07-24 lease-date integrity incident (PR #232). Retimed 07:00/13:00/19:00 -> 07:40/13:40/19:40 ET on 2026-07-27 (thin-the-AM-window pass): this was the single highest throttle-skip contributor (18 skips) in that morning's catch-up-burst event, sitting in a 3-task, 12-minute cluster with ora-task-integrity-guard (07:05, fixed by deliberate 2026-07-24 ruling) and ora-aaos-expire-leases (also retimed same pass). Uniform +40min offset preserves the 6h symmetric cadence across all three daily fires. As of 2026-07-27, data/snapshots/portfolio.json is git-tracked (Gabriel directive) — this task now commits its own regenerated snapshot locally on main after a successful write (Exit 0/2 only), but ONLY when lease data actually moved — a material-change gate ignores the meta.generatedAt timestamp the script rewrites on every run and restores the file rather than committing timestamp-only churn (Gabriel ruling 2026-07-27). As of 2026-08-09 it ALSO pushes that commit to origin/main, fast-forward only, under the guards in the Auto-push section (Gabriel directive 2026-08-09, superseding the prior do-not-push default). 2026-08-03 phantom-lease incident (parse.ts:476) CLOSED — suspension lifted same day after PR #250 (parser fix) + PR #252 (checkSnapshot wired into both CLI writers as defense-in-depth) both merged and independently verified, including a live A/B proof against the production workbook. See the "CLOSED" banner below STEPS for detail.


*Changelog — MIGRATED FROM FRONTMATTER (v1.8 (2026-08-17), class-n remediation). These entries previously existed ONLY in the `description` field; the body carried pointers reading "see description field above", which stops being true the moment the description is trimmed. Moved verbatim, not summarised.*

- **v1.4 (2026-08-05, Gabriel-directed, ORA-wide once/day cadence policy): collapsed 3x/day weekday -> 1x/day weekday (07:40 ET). Staleness window between refreshes widens from 6h to up to ~24h; the PR #232 parser fix itself is unaffected, only refresh frequency changed

- **v1.5 (2026-08-09, Gabriel directive): auto-push added -- after a successful Auto-commit the task now pushes to origin/main, fast-forward only, and refuses to push (surfacing a QUESTION FOR GABRIEL instead) if origin/main has moved or if any commit ahead is not this task's own Auto-refresh commit. No force variant, ever. Exit-code routing unchanged. [MODEL: claude-opus-5 observed | checked 2026-08-09 via live-run transcript canary]

- **v1.6 (2026-08-09, Gabriel-directed): seed-fallback guard. A transient Notion deals fetch failure had made the script write the ~6-deal seed placeholder set over the ~20-deal live pipeline at Exit 0 (deals 20 -> 6, counterparties 15 -> 14, leases untouched), which the material-change gate read as real portfolio movement and auto-push would have published to origin/main silently. Two layers added: (a) this spec now runs a section-shrink guard against HEAD on every non-empty $MATERIAL and refuses to commit/push on any shrink, plus a stdout degradation check; (b) the upstream script now refuses the write outright -- loadDeals reports the degradation, parse.ts raises an error-severity dataQuality flag, and evaluateReconciliationGate turns it into an Exit 1 alarm, with requireLiveDealsSource separately refusing a token-less write in both CLI writers. Deals-pipeline refusals are usually transient; never --force them

- **v1.7 (2026-08-11, Gabriel ruling, in-turn): Auto-push's own-commits-only guard WIDENED from this task's `Auto-refresh: lease snapshot ...` prefix alone to the pattern ^Auto-refresh: (CC|lease) snapshot, covering ora-cc-snapshot-refresh's commits too. That sibling task gained its own Auto-push section the same day, so from 2026-08-11 on either task can find the other's commit ahead of origin/main: whichever commits second would read it as a human's unpushed work and refuse, deadlocking the pair -- that forward-looking collision is the reason for the widened pattern. RATIONALE CORRECTED 2026-08-12 (transcript-verified): the original v1.7 note cited 0b5b36e's stranding as that deadlock actually occurring; it was not. Session 1de11c79 (the ora-cc-snapshot-refresh run of 2026-08-11, createdAt 22:39:34Z) evaluated NO push guard at all -- that task had neither an Auto-push nor an Auto-commit section that day, and its own run report reads 'Committed locally as 0b5b36e ... Not pushed -- no push step is in the spec.' A deadlock was impossible regardless: that run's pre-flight recorded origin/main at b9a58c2 with a clean tree, so after committing exactly one commit -- its own -- was ahead, and an own-prefix guard would have matched and pushed it. The widened pattern STANDS on its forward-looking merit; only the false historical evidence is withdrawn. Do not re-narrow to a single prefix on the strength of that retracted claim. The guard's actual purpose is preserved: a human's commit still matches nothing and still blocks the push. Keep this pattern in sync with the identical guard in ora-cc-snapshot-refresh. No other guard changed -- fast-forward-only, behind-must-be-0, and the no-force-ever rule are untouched

- **v1.9 (2026-08-27, Gabriel-approved in-turn): material-change gate MECHANISM replaced — by-name grep filter -> structural comparison. The 2026-07-27 no-timestamp-churn ruling is UNCHANGED; only its enforcement moved. The old filter named exactly one field, meta.generatedAt, and went stale the moment the quickbooks block (populated ~2026-08-17) brought a second write-clock, parsedAt. This task's 2026-08-27 run produced a 4-line diff that was two clock pairs and nothing else, structurally identical to HEAD, which the by-name filter read as "real portfolio data moved" and would have committed AND pushed to origin/main. That run restored instead of committing and escalated rather than following the stale letter of the spec. The replacement strips any key ending in 'At' whose value is an ISO-8601 datetime, recursively, from both sides, then compares what remains — so a FUTURE clock field is handled with no edit to this spec. Same staleness class as the shrink guard's hardcoded-list-keys gap (reference_cc_snapshot_shrink_guard_covers_lists_only.md). Verified BEFORE shipping, not asserted after: 10 synthetic cases (clock-only, clock+real rent change, section removal, asOf and daysToExpiry drift which must still count as material, and a future 'refreshedAt'), a live A/B on the real repo where the old gate said COMMIT+PUSH and the new one said none, and a synthetic annualRent injection confirming the 'yes' path still prints the +/- lines the run report has to quote. KNOWN RESIDUAL, disclosed not silently accepted: a genuine BUSINESS timestamp ending in 'At' is suppressed too — but never silently, since every suppressed path prints on the 'suppressed as write-clock:' line and lands in the run report. The live snapshot already carries four such paths: meta.generatedAt, quickbooks.parsedAt, and two dealComps.*.sourcedAt. Those dealComps stamps are provenance, not a write-clock; if a re-sourced comp should ever force a commit, ESCALATE rather than widening or narrowing the strip. Guard block kept byte-identical in ora-cc-snapshot-refresh. No other guard changed — section-shrink, deals-degradation stdout scan, repo-sanity, fast-forward-only, own-commits-only and the no-force-ever rule are all untouched

- **v1.10 (2026-09-02, Qodo review gap, PR #156 remediation): added a Worktree isolation section around Auto-commit/Auto-push. The drift-check script, every comparison guard (material-change, section-shrink, degradation), and the commit itself now run inside a fresh, private git worktree forked from a just-fetched origin/main (unique path/branch per run under C:\Users\Owner\AppData\Local\Temp\ora-cc-worktrees\, real npm install per worktree, never a node_modules junction), comparing against that worktree's own HEAD rather than the live checkout's working tree. Only the final git push origin HEAD:main still touches the shared checkout's main ref, under the same fast-forward-only / own-commits-only (^Auto-refresh: (CC|lease) snapshot) / no-force-ever guards as before -- none of those guards changed. This closes the gap the point-in-time repo-sanity check alone could not: a concurrent session's commit landing on main, or a concurrent edit, between this task's script run and its eventual git add/commit. The old "not on main" repo-sanity check is replaced by a worktree-sanity check (mid-merge/rebase/detached-HEAD only -- this worktree is deliberately never on main). A stale-worktree sweep runs at the start of every fire to handle a crashed/killed prior run's leftover worktree (discard if it holds no unpushed automation commit, else escalate rather than delete -- never silently lose a stranded commit). Cleanup (worktree + branch removal, git worktree prune) is unconditional on every exit path, including guard-refusal and escalation branches. Guard block kept byte-identical in ora-cc-snapshot-refresh, per this file's own stated convention
