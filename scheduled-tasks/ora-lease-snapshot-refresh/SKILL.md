---
name: ora-lease-snapshot-refresh
description: Weekday 1x/day (07:40 ET, collapsed from 3x/day 2026-08-05 per ORA-wide once/day cadence policy) regeneration of oxford-command-center's data/snapshots/portfolio.json via scripts/lease-snapshot-drift-check.ts, independent of interactive server uptime — reports lease drift (new/removed/date-changed) with an anomaly floor that refuses to write on a suspicious parse (closes the 2026-07-24 lease-date integrity incident, PR #232). On a successful write (exit 0/2) with lease data that actually moved (material-change gate structurally ignores write-clock-only churn) auto-commits locally, then lands it via an auto-merged PR (changed 2026-09-02 from a direct push to origin/main, which branch protection makes structurally impossible) under a section-shrink + deals-degradation guard and an own-commits-only pattern ^Auto-refresh: (CC|lease) snapshot shared with ora-cc-snapshot-refresh (never any force variant). 2026-08-03 phantom-lease incident (parse.ts:476) CLOSED. Full versioned changelog lives in the body of this file (migrated from frontmatter, class-n remediation 2026-08-17). [MODEL: claude-opus-5 observed | checked 2026-08-09 via live-run transcript canary]
---

You are running the scheduled task `ora-lease-snapshot-refresh` for Oxford Realty Advisors. This regenerates `data/snapshots/portfolio.json` in the `oxford-command-center` repo (`C:\Users\Owner\oxford-command-center`) via `scripts/lease-snapshot-drift-check.ts`, on a cadence independent of whether the interactive Command Center dev/prod server happens to be running (that dependency was the root cause of a 2026-07-24 lease-date integrity incident — the Command Center's alerts engine and its own portfolio snapshot disagreed about the portfolio's largest near-term lease expiration because the snapshot had gone stale). Full context: `CHANGELOG.md`'s "Stable lease ids + overlay-write hardening (2026-07-24)" entry and `docs/superpowers/plans/2026-07-24-lease-id-integrity-fix-plan.md` Task 3, both in that repo.

## Steps

0. **Resync `main` BEFORE the extract runs — the previous run's PR has usually landed since (added 2026-09-02, option A′).** Snapshot commits now land via an auto-merged PR rather than a direct push (see **Auto-push**), so when the last run's PR merged, `origin/main` gained a merge commit whose second parent is this checkout's own last snapshot commit. Local `main` therefore reads as *behind*, not diverged. Fast-forward it while the tree is still clean:

   ```bash
   git fetch origin
   git rev-list --left-right --count origin/main...HEAD
   ```

   If behind > 0 and ahead == 0 → `git merge --ff-only origin/main`. **This must happen before the extract**, not inside Auto-push: once the extract has rewritten `data/snapshots/portfolio.json`, a fast-forward that also touches that file is refused for local modifications and the run deadlocks with a dirty tree it cannot clean. A pure fast-forward is the ONLY history-moving operation this task may ever perform — never a reset, a rebase, or `pull --rebase`. If `--ff-only` fails, the checkout has genuinely diverged: stop before the extract, surface it as a guard-condition failure with a QUESTION FOR GABRIEL, and let a human reconcile it.

1. Run, from the `oxford-command-center` repo root: `npx tsx scripts/lease-snapshot-drift-check.ts`
2. Read the exit code AND the full stdout/stderr output — the exit code alone doesn't carry the detail a human needs.
3. On Exit 0 or Exit 2 only, commit the regenerated snapshot per "Auto-commit" below.
4. If step 3 produced a commit, land it per "Auto-push" below — an auto-merged PR since 2026-09-02, NOT a direct push (automation snapshot commits only; see that section for which prefixes qualify and why the direct push was retired).

## ✅ 2026-08-03 phantom-lease incident — CLOSED, suspension LIFTED 2026-08-03 20:2x UTC (Gabriel ruling)

This task was suspended (write, then write-and-commit) 2026-08-03 after `parse.ts:476`'s `propertyKey` guard stringified a Date instead of rejecting it, ingesting the rent roll's derived "VACANCY & UPCOMING AVAILABILITY" block as 10 phantom leases (138 → 148 leases, annual rent +$312,540). Full diagnosis: `memory/reference_parseleases_vacancy_block_phantom_leases_2026-08-03.md`.

Both halves of the lifting condition are now done and independently verified, not merely merged:
1. **Parser fix** — [PR #250](https://github.com/ZeOoba/oxford-command-center/pull/250) (`d35931a`).
2. **checkSnapshot wired into both CLI writers as defense-in-depth** — [PR #252](https://github.com/ZeOoba/oxford-command-center/pull/252) (`1185638`). `evaluateReconciliationGate()` refuses the write on any error-severity flag from `checkSnapshot()` + `snapshot.dataQuality`. Live A/B proof against the real production workbook (fix reverted vs. present, in an isolated worktree) confirmed both writers now refuse with the exact incident numbers instead of writing corrupt data.

First live resume, run by hand 2026-08-03 20:2x UTC on synced `main`: clean write, 138 leases, $5,576,537, 0 flags, both gates passed. Committed (`fa9ed8b`, "Auto-refresh: lease snapshot (138 leases, no drift)") — the material-change gate found a genuine non-timestamp diff (5 days of accumulated portfolio movement: loan amortization, rent/NOI changes — not corruption) and correctly did not restore/discard it. **Normal cadence resumes at the next scheduled fire; STEPS above apply as written, no special handling needed.**

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
- Before touching git at all, run a repo-sanity check: `git status --short` (no path filter) and `git log -1`. If the repo is mid-merge/mid-rebase (a `MERGE_HEAD` or `rebase-merge`/`rebase-apply` directory present), on a detached HEAD, or not on `main`, do NOT commit — treat it exactly like a guard-condition failure below (report the anomaly, escalate with a QUESTION FOR GABRIEL, leave the working tree alone). This protects against colliding with a human's or another session's in-progress work in this shared checkout.
- If other files besides `data/snapshots/portfolio.json` are also dirty, that is pre-existing WIP that is not this task's to touch — never `git add -A` / `git add .`. Stage ONLY the one file: `git add data/snapshots/portfolio.json`.
- Commit with a message summarizing the script's own printed counts, e.g. `Auto-refresh: lease snapshot (138 leases, no drift)` for Exit 0, or `Auto-refresh: lease snapshot (139 leases; drift: +2 new / -1 removed / 3 date-changed)` for Exit 2 — pull the actual numbers from stdout, never fabricate them.
- A commit failure (hook rejection, lock file, anything non-clean) is a guard-condition failure, not a silent skip — surface it the same way as the exit-code alarms below rather than swallowing it.

## Auto-push (Gabriel directive 2026-08-09; landing mechanism changed to auto-merged PR 2026-09-02)

Through 2026-08-08 this task committed on `main` and stopped, because an unattended push to the shared remote was a standing decision Gabriel had not made. He made it on 2026-08-09 (after a manual push of `8e4f51e`): **once a commit has been made per Auto-commit above, push it.** No commit → nothing to push; this whole section is skipped.

Landing a commit publishes *every* local commit on `main` that is ahead, not just this task's — so the guards below exist to make sure that's only ever an automation snapshot commit. **The landing mechanism changed on 2026-09-02 from a direct `git push origin main` to an auto-merged PR**; the direct push was structurally impossible against `main`'s required status checks. See **Landing the commit** at the end of this section. The guards themselves are unchanged.

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
- Both guards satisfied → land the commit per **Landing the commit** below. Report the PR number and, once merged, the resulting `origin/main` range in the run report.
- A failure at any point in that sequence (branch push rejected, `gh` auth, network, pre-push hook, PR creation, auto-merge refused) is a guard-condition failure, not a silent skip — surface it. Never retry with any force variant, and do not retry more than once for a plainly transient network error.
- **Exit-code routing is unchanged by this section** — an exit-0 landing still gets no Notion post and no email.

### Landing the commit — auto-merged PR, NOT a direct push (Gabriel ruling 2026-09-02, option A′)

**A direct `git push origin main` can never succeed and must not be attempted.** `main` carries classic branch protection (no rulesets) with `enforce_admins: true` and two required contexts, `gate` and `refute-required`. `refute-required` is declared `if: github.event_name == 'pull_request'` (`.github/workflows/ci.yml:33`), so it never reports a status on a push at all; `gate` runs only *after* a push is accepted. A pushed commit therefore carries 0 of 2 required statuses and GitHub rejects it:

```
remote: error: GH006: Protected branch update failed for refs/heads/main.
remote: - 2 of 2 required status checks are expected.
```

This is **structural, not transient** — it failed identically on 2026-08-25 ([[open-items-tracker.md#OI-205]]) and again on 2026-09-02, and it would fail every run. Do not retry it, do not reach for any force variant, and do not propose disabling `enforce_admins`: that was evaluated and **rejected** on 2026-09-02 because branch-protection bypass is actor-scoped, never commit-scoped — it would exempt *every* admin direct push from the refute doctrine gate, not just these snapshots. (A push-restriction allowlist, which could scope it to one account, is an organization-only feature; `ZeOoba` is a User account, so it is unavailable here regardless.)

Land it through a PR that merges itself:

```bash
BR="snapshot/lease-refresh-$(date +%Y-%m-%d-%H%M)"
git push origin HEAD:refs/heads/$BR    # creates the branch AT the commit; HEAD never leaves main
gh pr create --base main --head "$BR" --title "<the commit subject, verbatim>" --body "<run summary>"
gh pr merge <n> --auto --merge         # lands itself the moment gate + refute-required pass
```

- **`--merge` is mandatory. NEVER `--squash` or `--rebase`.** A merge commit keeps this checkout's local commit as an *ancestor* of the new `origin/main`, which is exactly what makes the next run's resync a clean fast-forward. A squash or rebase rewrites the SHA, permanently diverging the shared checkout from the remote and stranding every later run behind a divergence the fast-forward guard will correctly refuse to resolve.
- `git push origin HEAD:refs/heads/$BR` deliberately does **not** check the branch out. This is a shared checkout other sessions work in; moving `HEAD` off `main` is the hazard `memory/rules.md` §14 warns about.
- **`refute-required` passes trivially on these commits** — they touch only `data/snapshots/portfolio.json`, never financial-decision source (verified live on PR #307, 2026-09-02: passed in 46s). If it ever FAILS, that is real signal that something outside the snapshot got staged. Surface it; do not retry.
- **If the PR does not merge** — a check went red, auto-merge was disarmed, or the repo's `allow_auto_merge` was turned back off — the commit is safe on the branch and in the open PR. Report it as a guard-condition failure naming the PR number and the failing check. **Never merge it by hand to force it through**, and never fall back to a direct push.
- **If a snapshot PR from an earlier run is still open**, do NOT open a second one: push the new commit onto that same existing branch so the open PR picks it up, and say so in the run report. Two open PRs against the same file will conflict with each other.
- After confirming the merge, delete the remote branch (`git push origin --delete "$BR"`). The repo's `delete_branch_on_merge` is false, so these otherwise accumulate.
- Repo prerequisite, set 2026-09-02: `allow_auto_merge: true`. If `gh pr merge --auto` reports auto-merge is unavailable, that setting was reverted — surface it rather than merging manually.
- Keep this section in sync with the identical one in `ora-cc-snapshot-refresh`.

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
