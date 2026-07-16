---
name: event_log
description: "ORA append-only event log — system changes, deal milestones, decisions. Newest first. This is the ONLY append-wall; living docs are overwritten to current state and point here for history."
metadata: 
  node_type: memory
  type: log
  originSessionId: 8ffab475-017d-4acd-9f70-f4496936d089
---

# ORA Event Log (append-only, newest first)

Renamed/expanded 2026-06-03 from reference_optimization_log.md. Living docs (firm/projects/tech/etc.) hold current state; their history accumulates HERE.

## 2026-07-15 — Deal-stage sync: 5515 Catfish Court — Westport (Waunakee), WI — (none) → Candidate (Notion)

Detected by ora-open-sessions-board's reconciliation step; no corresponding entry existed. Tripwire only — see Notion for the actual decision context.

## 2026-07-15 — Deal-stage sync: 250 NW 10th Street — Waukee, IA — (none) → Candidate (Notion)

Detected by ora-open-sessions-board's reconciliation step; no corresponding entry existed. Tripwire only — see Notion for the actual decision context.

## 2026-07-15 (later still, cont.) — Correction: `orphaned-task-forensics`/`fleet-advisory-remediation` DO have a git home; v1.1 fix applied at the real source

Follow-up to the immediately preceding entry, which wrongly stated neither skill exists in
`C:\Users\Owner\ora-skills` (based on a `Glob` search that returned no matches). A direct
`git ls-files | grep` and `ls -1` in that repo immediately showed both `orphaned-task-forensics/`
and `fleet-advisory-remediation/` present, tracked, unchanged since 2026-07-11 — the Glob result
was simply wrong, not evidence of absence. New standing lesson:
[[feedback_verify_negative_glob_results]].

Applied the identical v1.1 corrections from the earlier runtime-cache edit to the real repo
copies: `C:\Users\Owner\ora-skills\fleet-advisory-remediation\SKILL.md` and
`...\orphaned-task-forensics\SKILL.md`. Gated clean (`tools/desc_lengths.py`: 785 / 846 chars,
both well under the 1024 limit). Single-writer check clean (working tree was otherwise clean,
matching the pre-edit `git status`/`git log -1` check). Committed locally: `9da6b35`.

**Two steps remain, both outside this session's authority to do unprompted:**
1. `git push` to `origin/main` — not done, awaiting Gabriel's go-ahead (repo push is
   shared/visible state, not something to do without asking).
2. `tools/package_skills.py` + Gabriel's Save-skill re-import click — the repo fix alone does
   not update what the live Cowork runtime serves; per `package-and-stage-skill` doctrine that
   last mile is the human's click, not automatable here. Until then, the hand-patched
   per-session runtime-cache copy from the earlier entry is the only live copy reflecting the
   fix, and it's uncertain whether that survives a skill-store re-sync — the repo commit is now
   the actual durable fix regardless of that cache copy's fate.

[[reference_fleet_status_dual_read.md]] updated to drop its now-incorrect "no durable home"
claim and record the correction + commit hash.

## 2026-07-15 (later) — Both schematic-refresh findings fixed interactively; the memory "dead link" was a probe false positive

Gabriel asked (in-turn) to fix the two findings the REV 2026-07-15a schematic run flagged. Both resolved; the first turned out to be a probe bug, not a memory defect.

**1. memory-integrity "dead link" = FALSE POSITIVE, fixed at root in the probe.**
`reference_newyorkfed_api_403_hosted_fetch.md` body-links `feedback_webfetch_markdown_false_negatives.md` — which is live, present, and indexed (MEMORY.md line 81), NOT retired. The probe flagged it because `memory-integrity-probe.py`'s `RETIRED_DOCS` tuple carried a bare `"feedback_"` prefix, added to catch the 7 genuinely-retired `feedback_*_merged-into-rules_2026-06-03.md` docs (now in `_archive/`), but which also matches every LIVE `feedback_*` file under the current naming scheme. Latent for weeks; only surfaced now because reference_newyorkfed (created 2026-07-15) is the first root memory file to body-link a live `feedback_*` doc (MEMORY.md itself is skipped by the check).
- Fix: the retired-doc check now resolves each link's target basename and **skips any link whose target still exists as a live root memory file** (`base in present`) before applying the retired-prefix match. General correctness improvement — a link to a live file is never a retired-doc violation regardless of prefix. The valid cross-link was KEPT, not deleted.
- Regression test added: `hooks/tests/test-memory-retired-doc-links.py` (4 cases: live feedback_* link not flagged; absent retired full-name doc still flagged; absent retired feedback merged-doc still flagged; clean set clean). 4/4 pass. Existing `test-memory-review-by.py` still 6/6 green.
- `memory-integrity-probe.py` now exits 0.

**2. Two over-cap MEMORY.md index entries trimmed.**
Lines for `reference_newyorkfed_api_403_hosted_fetch.md` (177 chars) and `reference_writing_style_platform_skill.md` (181 chars) exceeded the 150-char one-line-pointer cap (memory-policy §3). Both collapsed to ≤150-char hooks; detail already lived in the linked files. `doctrine-integrity-probe.py` now reports 0 over-cap entries.

Verified post-fix (a concurrent writer added `reference_fleet_status_dual_read.md` mid-session → 79/79): memory-integrity exit 0, doctrine 0 over-cap / within budget, governor clean. Schematic republished in place (REV 2026-07-15b) reflecting the resolved state. Lesson: a probe finding is a hypothesis — verify the flagged artifact before "fixing" it; here the correct fix was the probe, not the memory file. [[feedback_verify_subagent_safe_claims]]

## 2026-07-15 (later still) — Both loose-end fixes from the dedup-task forensics chase: 1 already done, 1 applied (with a durability caveat)

Follow-up investigation into the one remaining loose end ("exact mechanism of the fix wasn't
established") turned up two concrete, unrelated fixes worth making — Gabriel approved both.

**Fix 1 — `_state-history\<date>.json` snapshot-filename collision: ALREADY FIXED, independently
verified, no action taken.** Both producers (`automation-health-monitor` LAMS-side,
`ora-task-integrity-guard` CC/MCP-side) wrote to the identical bare filename and clobbered each
other daily — self-flagged 2026-07-13/14 as "unresolved, escalating as follow-up" but never
actually landed. Found both SKILL.mds already carry a same-day fix (automation-health-monitor
v1.7, ora-task-integrity-guard v1.4, both dated 2026-07-15): LAMS now writes `.lams.json`
exclusively, CC/MCP now writes `.cc.json` exclusively, `membership-guard.ps1`'s read filter
updated to match. Read BOTH files' actual current content directly (not just their changelog
claims, given today's earlier lesson about unverified completion claims) — genuinely fixed,
cross-consistent, no gaps. Origin of this fix is unclear (possibly `automation-health-monitor`'s
own self-healing — its "Skill backups" retention convention suggests it edits its own SKILL.md);
not investigated further, low value relative to cost.

**Fix 2 — `fleet-advisory-remediation` / `orphaned-task-forensics` doctrine wrongly claimed the
LAMS registry is unreachable from a CC/MCP session for READS, not just writes.** This wrong
assumption is what caused today's dedup-task cleanup to be handed off wholesale to a Cowork
session for a full `list_scheduled_tasks` verify round-trip, when `fleet-status.py --json` (which
reads both registries' JSON files directly off disk, from either surface, confirmed by running it
live this session) would have shown the answer in one call. Corrected both skills' Inputs/Workflow
sections to draw the real line (reads: fine from either surface via `fleet-status.py`; writes:
still need the matching-surface MCP tool) and added a mandatory post-write re-verify step to
`fleet-advisory-remediation` Step 6, directly citing this same incident.

**Durability caveat on Fix 2:** neither skill has a git-tracked source of record — unlike most
ORA skills, `orphaned-task-forensics` and `fleet-advisory-remediation` do not exist in
`C:\Users\Owner\ora-skills`. Only a per-session Cowork runtime-cache materialization could be
found and edited
(`AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\...\skills\<name>\SKILL.md`);
whether this persists across a Cowork skill-store re-sync is unverified. Captured the same lesson
durably in memory regardless: [[reference_fleet_status_dual_read]]. **Open question for
Gabriel:** where are these two skills actually authored/maintained? Worth a direct answer so a
future edit to either doesn't repeat this same "which copy is real" uncertainty.

## 2026-07-15 — Schematic refresh (REV 2026-07-15a): memory-integrity probe began failing on a dead cross-link; fleet grew to 42

Daily `ora-cc-schematic-refresh` run. Three material changes vs the prior (2026-07-14g) snapshot, logged here because each meets the "log only if something materially changed" bar (a probe that started failing, new doctrine warnings, registry-membership change):

1. **memory-integrity-probe.py now exits non-zero.** 78/78 files indexed and present (up from 75) — the index/file reconcile is intact — but the probe reports 1 issue: `reference_newyorkfed_api_403_hosted_fetch.md` contains a `[[feedback_…]]` cross-link to a doc that has been retired/archived, so it links a non-live doc. Not data loss; a stale internal link to repoint or drop on the next `consolidate-memory` pass. **Not fixed by this task** (schematic-refresh edits only the artifact + this log).

2. **doctrine-integrity-probe.py: 2 MEMORY.md index entries drifted back over the 150-char cap** — line 84 (177 chars) and line 85 (181 chars), over memory-policy §3's one-line-pointer limit. The `memory-index-guard.py` hook only blocks NEW over-cap writes; pre-existing drift must be collapsed by hand. Flagged for a memory pass, not fixed here. (CLAUDE.md size unchanged at 1692 words, within budget; governor clean at 546 files, DSCR 1.25×/LTV 40% consistent.)

3. **Fleet grew from 40 → 42 enabled** (cc 19→20, lams 21→22): three newly-registered never-ran tasks appeared — `ora-sofr-direct-prefetch` (cc, weekday 10:10), `ora-counsel-review-standard-positions` (lams, one-time @2026-08-03), `ora-ic-memo-pipeline-reconciliation` (lams, Tue weekly 10:30) — all legitimately not-yet-due by cadence. Total 44 (42 enabled / 2 expired-off: canary-model-check-temp, efulton-post-legalhold-consolidation).

Fleet verdict this run: **ATTENTION on 8 throttle skips in the last 24h** (ora-cowork-heartbeat=7, ora-aaos-publish-contracts=1) — ceiling-hits on tasks firing normally, not stalls. 0 collisions, 0 overdue, 0 missed one-time fires. confidentiality-guard re-run 122/122. Both repos clean on main (oxford-command-center a83ce68, ora-pm 8418c44). The previously-open `ora-tenant-db-dedup-remediation` orphan is now absent from the fleet-status roster entirely, consistent with the same-day CLOSED entry above — no longer a finding.

Artifact republished in place at the existing URL (REV 2026-07-15a). None of the three findings are fixed by this task; each is flagged for its owning pass.

## 2026-07-15 (later) — `ora-tenant-db-dedup-remediation` handoff CLOSED: Cowork session confirmed the LAMS registry entry is gone

Follow-up to the same-day forensics entry above. Gabriel ran the handoff prompt in a Cowork session, which:
1. Called `list_scheduled_tasks` against the live LAMS registry — `ora-tenant-db-dedup-remediation` was **not present** in the full 23-task roster.
2. Since absent, no `delete_scheduled_task` call was needed.
3. Ran `list_scheduled_tasks` a second, independent time as the required re-check before logging closure — same result both times.
4. Confirmed the archived `SKILL.md` (`Documents\Claude\Scheduled\_archive_2026-07-14_stale-cleanup\ora-tenant-db-dedup-remediation\SKILL.md`) is intact and untouched.

Root cause of the discrepancy between the 2026-07-15 fleet-status "still open" reading and this clean registry state was not established (either the original 2026-07-14 `delete_scheduled_task` call took effect on a later attempt not captured in the log, or an intervening session removed it first) — flagged as inconclusive rather than guessed, per the Cowork session's own entry (`Claude_Workspace/01_Workspace/memory/event_log.md`, 2026-07-15 "RESOLVED" entry).

**Status: CLOSED.** No further action owed on this stale-entry cleanup. [[feedback_verify_registry_mutation_claims]] stands as the general lesson regardless of this instance's inconclusive root cause.

## 2026-07-15 — Orphaned-task forensics: `ora-tenant-db-dedup-remediation` root-caused as (a), but the 2026-07-14 "registry deleted" claim did not actually take effect

Ran `orphaned-task-forensics` (Workflow B, lost-SKILL.md path) against the LAMS one-time task
`ora-tenant-db-dedup-remediation` — flagged 2026-07-13 as an orphaned expired entry (fireAt
past, lastRunAt empty) needing supervised Cowork-side cleanup, and still showing as an open
expired entry in the 2026-07-15 fleet-status run. New symptom this pass: its SKILL.md folder
appeared to be missing entirely from the live `Documents\Claude\Scheduled\` tree and every
`_archive_*` folder under a "dedup" name search.

**Finding 1 — the file isn't lost.** It's at
`Documents\Claude\Scheduled\_archive_2026-07-14_stale-cleanup\ora-tenant-db-dedup-remediation\SKILL.md`
— a folder name the earlier search apparently didn't check. Content confirms scenario **(a)**:
this task was itself the vehicle for the 2026-07-12 remediation (a same-day 15:38 ET hedge,
fire-once 2026-07-13 08:00 ET, covering only the original categories A/B/C/D), not a follow-up
task for the 2 held-back + 1 unresolved leftover items from that run — nothing in its prompt
references them. Cross-corroborated against two independent sources: the SKILL.md's own
description line, and this event_log.md's existing 2026-07-14 entries (present twice,
verbatim-duplicated at the time of this read), which state the hedge was never needed because
an interactive session executed the full remediation live that same evening (2026-07-12),
archiving 124/296 rows hours before the hedge's scheduled slot.

**Finding 2 — the registry-deletion half of that same 2026-07-14 cleanup did not actually
take effect.** Those entries also claim the LAMS registry entry was retired via the supervised
`delete_scheduled_task` MCP tool. That claim doesn't hold up: the task is still showing as an
open expired entry as of the 2026-07-15 fleet-status run. This session's own
`list_scheduled_tasks` call reconfirms the LAMS/Cowork registry is unreachable from a CC/MCP
session (21 tasks returned, all CC-fleet paths, no LAMS entries) — meaning the file-archival
half of the 2026-07-14 cleanup genuinely happened, but the registry-deletion half was logged as
complete without a verifying re-list, from a session that may not have been able to reach the
LAMS registry at all. This is the third time this exact entry has surfaced unresolved
(2026-07-13 flagged → 2026-07-14 "resolved" ×2 duplicate log entries → still open 2026-07-15).

**Action:** no registry write attempted from this session (confirmed unreachable — matches
prior doctrine). Logging the same finding to the Cowork-side
`Claude_Workspace/01_Workspace/memory/event_log.md` so a Cowork/LAMS-surface session can close
the loop with its own `list_scheduled_tasks` → `delete_scheduled_task` → re-verify, rather than
another log-only "resolved" entry. New standing memory captures the pattern:
[[feedback_verify_registry_mutation_claims]] (related but distinct from
[[feedback_verify_subagent_safe_claims]]).

## 2026-07-15 — Fleet-status advisory triage (fleet-advisory-remediation): 1 genuine finding, spawned for Cowork-side resolution

Gabriel forwarded today's recalibrated `fleet-status.py` verdict (13 new tests added; never-ran/expired/throttle-skip logic now cadence-aware — noise collapsed from 9 never-ran + 3 expired + 36 all-time-skips down to one real finding). Triaged per [[feedback_subagent_anti_delegation]]-adjacent fleet-advisory-remediation workflow:

- **Same-time collisions (0), 9 never-ran (0 overdue), 36 all-time throttle skips (0 in 24h):** all confirmed clean/non-actionable, no action needed.
- **`ora-tenant-db-dedup-remediation` (LAMS-fleet, one-time, expired never-ran):** confirmed absent from the CC/MCP `list_scheduled_tasks` output (LAMS-scoped, unreachable from this session — same gap already logged 2026-07-13). New finding this pass: its SKILL.md folder does not exist anywhere under `Documents\Claude\Scheduled\` (checked live tree + all `_archive_*` folders) — the backing file is gone, not just unregistered. Circumstantial read from [[reference_tenant_db_completeness_gap]]: the Tenant DB dedup remediation this task was presumably named for already ran manually 2026-07-12 (124/296 rows archived; 2 held-back dup pairs + 1 unresolved re-link still open) — so this task may be superseded, or may have been the intended vehicle for that leftover follow-up work. Not resolved inline (skill boundary: don't root-cause a vanished-SKILL.md case without session-transcript archaeology, and this session can't write the LAMS registry regardless). Spawned a background task (Cowork surface, `orphaned-task-forensics` skill) to determine superseded-vs-owed and delete or re-arm accordingly — the 2026-07-13 flag was memory-only and evidently never actioned, so this time it's an actual task chip, not just a log line.

Full advisory text and reasoning: this conversation. No registry writes made this session (none were reachable).

## 2026-07-15 — New CC/MCP scheduled task `ora-sofr-direct-prefetch` (durable fix for SOFR data-freshness gap)

Root cause found and fixed: `markets.newyorkfed.org`'s SOFR/SOFR-Averages API returns HTTP 403 to Anthropic-hosted fetch tooling (WebFetch + Cowork). Overnight SOFR/UST have a web_search fallback so they usually still populate; the 30/90/180-day SOFR averages and SOFR Index have none, so they'd silently gone `[CARRIED FORWARD]` on the canonical Notion "Rate Snapshot — Current" page (`35e6ecd8-9e59-814f-ae22-fe99464084d1`) for 2 consecutive `ora-am-brief` runs. One-time manual patch applied same session via Desktop Commander direct pull (local machine has normal network egress, confirmed unblocked). Durable fix: registered `ora-sofr-direct-prefetch` (CC/MCP fleet, `10 10 * * 1-5`, verified via `list_scheduled_tasks`) — pulls fresh SOFR data locally each weekday morning and patches only the SOFR Strip table on the Rate Snapshot page, silent on success, Ops Hub alert only on failure, no email. Also updated `ora-am-brief` Block A (LAMS/Cowork, `Documents\Claude\Scheduled\ora-am-brief\SKILL.md`) so it stops manufacturing a doomed Prefetch Error for the same known-403 gap and instead carries forward same-day values once the new task has patched them. Full context: `reference_newyorkfed_api_403_hosted_fetch.md`. RATIFIED.

## 2026-07-14 — Retired stale ora-tenant-db-dedup-remediation LAMS one-time task (Cowork-side cleanup, closes 2026-07-12 loop)

Retired the `ora-tenant-db-dedup-remediation` one-time scheduled task via the supervised
`delete_scheduled_task` MCP tool (never the Scheduled-sidebar trash icon, which is
folder-destructive and can break a same-id task on the other fleet). It was created
2026-07-12 15:38 ET as a same-day hedge — fire once at 2026-07-13 08:00 ET to run the Notion
Tenant DB dedup remediation, in case an earlier Notion API quota block ("used all of your
plan's free data source queries") was still live at hedge time.

The hedge was never needed: an interactive session executed the full remediation live later
that same evening, 2026-07-12, archiving 124 of 296 rows across categories A/B/D — hours
before the task's scheduled slot. The task never fired (confirmed enabled:false, no
lastRunAt) and sat expired and orphaned. A later 2026-07-12 session already flagged it here
as a dead entry needing "supervised Cowork-side cleanup" — that cleanup did not happen until
now, 2 days later. This entry closes that loop: the underlying remediation was already
confirmed executed, not missed.

Per Hard Invariant 6, archived rather than deleted: moved the task folder from
`OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-tenant-db-dedup-remediation\`
to a new `_archive_2026-07-14_stale-cleanup\` folder (matching the existing
`_archive_2026-06-11_orphans` convention). `efulton-post-legalhold-consolidation` was
deliberately left untouched in this pass — separate, sensitive, needs Gabriel's explicit
sign-off first.

## 2026-07-14 — Retired stale ora-tenant-db-dedup-remediation LAMS one-time task (Cowork-side cleanup, closes 2026-07-12 loop)

Retired the `ora-tenant-db-dedup-remediation` one-time scheduled task via the supervised
`delete_scheduled_task` MCP tool (never the Scheduled-sidebar trash icon, which is
folder-destructive and can break a same-id task on the other fleet). It was created
2026-07-12 15:38 ET as a same-day hedge — fire once at 2026-07-13 08:00 ET to run the Notion
Tenant DB dedup remediation, in case an earlier Notion API quota block ("used all of your
plan's free data source queries") was still live at hedge time.

The hedge was never needed: an interactive session executed the full remediation live later
that same evening, 2026-07-12, archiving 124 of 296 rows across categories A/B/D — hours
before the task's scheduled slot. The task never fired (confirmed enabled:false, no
lastRunAt) and sat expired and orphaned. A later 2026-07-12 session already flagged it here
as a dead entry needing "supervised Cowork-side cleanup" — that cleanup did not happen until
now, 2 days later. This entry closes that loop: the underlying remediation was already
confirmed executed, not missed.

Per Hard Invariant 6, archived rather than deleted: moved the task folder from
`OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-tenant-db-dedup-remediation\`
to a new `_archive_2026-07-14_stale-cleanup\` folder (matching the existing
`_archive_2026-06-11_orphans` convention). `efulton-post-legalhold-consolidation` was
deliberately left untouched in this pass — separate, sensitive, needs Gabriel's explicit
sign-off first.

## 2026-07-14 — LAMS backup-gap check: no git/.gitignore analog found; last 2026-07-09 OneDrive "(1)" residue tidied up

Checked the LAMS/Cowork fleet for an analog to the `~/.claude/.gitignore` gap found earlier
today (memory files silently excluded from the CC/MCP git backup). No git or `.gitignore`
exists anywhere in the LAMS OneDrive `Scheduled` tree — that specific bug class can't occur
there since there's no git backup layer at all.

The structurally-equivalent risk (content silently landing outside the protected/canonical
scope) DID occur historically via the known canonical-vs-`"(1)"` OneDrive account split, but
was already found and fixed 2026-07-09 (setup-audit Task 12,
`OneDrive - Oxford Capital Partners (1)\Documents\Claude\MOVED-SEE-CANONICAL.md`). Re-verified
today: the moved content (`last-run.json`, `membership-state.json`) is intact at the canonical
archive path; no live (non-archived, non-historical-snapshot) SKILL.md on either fleet still
references the wrong `"(1)"` path — zero hits.

**Tidied up** the only remaining residue: two empty directory shells left behind by the
2026-07-09 move (`Scheduled\ora-connector-preflight-guard\`, `Scheduled\_state-history\` under
the `"(1)"` account) — verified empty (no files, `find -mindepth 1` returned nothing) and
removed via `rmdir` (empty-directories-only, non-destructive; would have failed loudly if
anything were still inside). `Scheduled\` under that account is now fully empty; only
`MOVED-SEE-CANONICAL.md` remains in the tree, updated with a dated closing note.

Related: `reference_memory_scope_fragmentation.md`.

## 2026-07-14 — Fleet-wide sweep for the STALE-guard gap: 2 confirmed + fixed, 2 borderline flagged, rest clean

Following the `ora-owner-outreach-queue-refresh` and `ora-pm-ledger` checks (this
memory's earlier 2026-07-14 entries), swept all remaining live scheduled tasks on
both fleets (34 SKILL.md files: 18 CC/MCP, 16 LAMS/Cowork, excluding the two
already checked and the two disabled/one-time folders) for the same pattern — a
guard that halts pending a Gabriel judgment call, with no durable memory of the
answer once given, so it re-asks identically on every future fire. Ran as 7
parallel read-only audit agents, one per batch of ~6 tasks.

**Confirmed gaps, fixed:**
- `ora-entry-market-scan` (CC/MCP) — the Louisville/Delmarva off-taxonomy
  GATE-FLAGGED checkpoint (Step 2) had no ratification mechanism. Added a
  per-listing `Gate Review` Notion field (Step 3) that Step 2/5 now check before
  re-flagging an unchanged listing. No entry exists yet — the guard has never
  actually tripped for a real listing; this only adds the place to record the
  answer once it does. v1.0 → v1.1. Committed + pushed (`d7b0f29`).
- `ora-stale-pipeline-nudge` (LAMS) — the schema-data-gap "QUESTIONS FOR GABRIEL"
  halt (Target Close Date / Last Updated field not found) had no ratification
  mechanism. Added a dated FIELD-NAME RATIFICATIONS list, empty for now (same
  reasoning — never actually tripped). v1.1 → v1.2. OneDrive prose, not
  git-tracked.

Both fixes are pure scaffolding, not an active ratification (unlike the
owner-outreach fix, which had a real Gabriel decision to encode) — neither guard
has fired for a genuine case yet. Guard thresholds/behavior otherwise unchanged.

**Borderline, flagged but NOT edited (judgment calls, not clean hits):**
- `ora-command-center-mirror-drift-check` (CC/MCP) — a narrow catch-all fallback
  for structural ambiguity (task renamed, path changed) with no memory. Rare
  edge case; the "right" fix might be a script/config update rather than a
  ratification note. Left as-is pending a real occurrence.
- `ora-bearmode-refresh` (LAMS) — Step 7's per-deal bear-mode re-score flag has
  no durable memory, but it's flag-only (never halts execution) — closer to the
  correctly-recurring TIER-3 reminder pattern than to a genuine halt-and-ask.
  Left as-is; worth a second look if it starts generating repeat-noise on the
  same deal.

**Already correctly implementing the fix pattern (no action, reference examples):**
`ora-deal-sourcing-scan` (per-deal Notion "Exception Compensating Factor" field),
`ora-master-workbook-ingest` (insurance-alert Ops Hub "already escalated" note),
`ora-open-sessions-board` (`answered.json` — effectively the reference
implementation of this whole pattern).

**Clean, no gap (27 tasks):** all remaining CC/MCP and LAMS tasks audited —
guards are either mechanical fail-loud error handling (correctly re-fires on a
persisting problem) or self-resolving live-state checks (re-derive their own
answer fresh each run, same shape as `ora-pm-ledger`'s de-dupe guard).

Related: `project_owner_outreach_stale_guard_watch.md`, `ops_decision_log.md`
(2026-07-14 entries).

## 2026-07-14 — ora-pm-ledger de-dupe guard checked for the owner-outreach STALE-guard pattern — does NOT share it; unrelated stale rationale fixed

Following the `ora-owner-outreach-queue-refresh` STALE-guard fix (same day, this
memory's earlier 2026-07-14 entry), checked whether `ora-pm-ledger`'s §0.5
PRE-FLIGHT DE-DUPE GUARD has the same structural gap: a guard that holds pending
a Gabriel decision, with no durable memory of that decision, so it re-asks
identically forever.

**Verdict: it does not share the gap.** §0.5 never waits on a Gabriel decision —
it's a purely mechanical, self-resolving check (does today's date already have
delivered artifacts in Sent Items / Ops Hub / send-log) that re-derives its own
answer fresh every run from today's evidence. There is no one-time human
confirmation for it to forget.

**Unrelated stale-documentation issue found and fixed instead:** §0.5's preamble
described the guard as a stopgap "[u]ntil the redundant [LAMS] registration is
retired" — but per `reference_ora_pm_ledger_double_fire.md`, that retirement
question was already resolved 2026-07-12 (the suspected LAMS twin was confirmed
absent/never-live; CC/MCP was the sole registration throughout). The SKILL.md's
own narrative was never updated to reflect that memory-confirmed resolution.
Reframed the preamble to state the guard is an intentional permanent
belt-and-suspenders backstop, not a pending-cleanup workaround, and added a
dated AMENDMENT NOTE. No guard check-logic changed (steps 1–4 untouched).

Edited `~/.claude/scheduled-tasks/ora-pm-ledger/SKILL.md` directly (CC/MCP
canonical copy; git status clean before edit, single-writer check passed).
Change is uncommitted — left for Gabriel to commit/push at his discretion per
"never commit unless explicitly asked."

Related: `project_owner_outreach_stale_guard_watch.md`, `ops_decision_log.md`
(2026-07-14 entry), `reference_ora_pm_ledger_double_fire.md`.

## 2026-07-14 — Owner-Outreach STALE guard: added per-vintage standing ratification (SKILL.md v1.3)

Closed the mechanism gap flagged in `ops_decision_log.md`'s 2026-07-14 entry: Gabriel ratified the
`ora-owner-outreach-queue-refresh` off-market master's 2026-06-10 vintage as current (interactive
elicitation, one-time — not a rescreen, not a STALE_DAYS/threshold change), but the guard had no
way to remember that for the 2026-07-20 re-fire on the same unrefreshed data.

**Finding:** the halt-and-ask behavior lives entirely in SKILL.md STEP 1 prose, interpreted fresh
by the Cowork agent each run — `owner_outreach_weekly.py` itself is WARN-only since the 2026-07-12
relax and never halts. No code fix was needed or attempted.

**Fix:** added a STANDING RATIFICATIONS clause to STEP 1 of
`OneDrive - Oxford Capital Partners/Documents/Claude/Scheduled/ora-owner-outreach-queue-refresh/SKILL.md`
(v1.2 → v1.3). The guard now checks the reported master vintage against a dated, per-vintage
ratification list before halting: proceeds without re-asking when the reported vintage still reads
2026-06-10 (logging that fact in the summary email), but the full halt-and-ask fires again
automatically the instant the vintage changes to anything else — including a refresh that is
itself still stale. `STALE_DAYS` (7) and the default halt behavior are unchanged; nothing was
widened or disabled.

Edited directly from the Code CLI surface: the file is plain OneDrive prose, not git-tracked or
registry-spliced, and SKILL.md content is authoritative regardless of which surface writes it
(`reference_cc_scheduler_filepath_mechanism.md`). No scheduled-task registry, JSON, or Python
script was touched.

Related: `project_owner_outreach_stale_guard_watch.md` (updated), `ops_decision_log.md` (updated,
2026-07-14 entry), `reference_scheduled_task_staleness_guard_trips.md` (Case 2).

## 2026-07-14 — Gabriel ratified the 2026-07-13 owner-outreach QUESTIONS-FOR-GABRIEL: master vintage is current, no rescreen

Presented the unanswered `ora-owner-outreach-queue-refresh` QUESTIONS-FOR-GABRIEL email (2026-07-13 fire, master content vintage 2026-06-10/33d, guard held Notion page-creation + `--commit`) as an interactive multiple-choice elicitation. **Gabriel selected "Current — unblock next run"** over "rescreen first" and "adjust the guard's threshold" — a one-time ratification for this cycle, not a standing policy change.

Logged as a decision in [[ops_decision_log]] (2026-07-14 entry). **Not yet operationally closed:** the STEP 1 guard in the LAMS `ora-owner-outreach-queue-refresh` SKILL.md is a plain stdout string-match on "STALE" with no bypass mechanism for "Gabriel already confirmed this vintage" — read directly from `...\Documents\Claude\Scheduled\ora-owner-outreach-queue-refresh\SKILL.md` to confirm the mechanism before recording this. Since the master itself isn't being refreshed (that option was explicitly declined), the 2026-07-20 fire will very likely re-trip on the same ~40-day-old data and re-ask the identical question, unless the guard is given some way to recognize this ratification.

Deliberately did NOT hand-edit that SKILL.md from this Code-CLI surface — it's a live LAMS/Cowork automation, and per [[reference_skill_surfaces]] and past practice (e.g. the ora-pm-ledger and stale-guard case histories), guard-logic changes to that script belong on the Cowork surface, not a freehand cross-surface edit here. Flagged as a background task instead (see spawn_task chip) rather than guessing at the correct wiring.

## 2026-07-14 — Systematization pass: index-hook write-guard, review_by expiry, staleness-log rename, autonomy-gate diagnostics (+ correction: RCT v03 landed on a branch)

Gabriel approved the 4 systematization candidates surfaced by the MEMORY.md consolidation. All four shipped; all 16 hook test-suites and all 3 probes green.

**1. `memory-index-guard.py` (NEW PreToolUse hook) — stops index bloat at the source.** The 150-char index-hook cap was audit-only (doctrine-probe check 9), so it regrew ~1/day (6 → 14 → 15 across three runs) and needed a manual pass to clear. The new hook simulates the post-edit MEMORY.md and DENIES any edit that would ADD a new over-length entry. It imports the cap and the entry regex from `doctrine-integrity-probe.py`, so the write-time rule and the audit-time rule cannot drift apart. **No-lockout by construction:** it only blocks edits that make the count *worse* — a pre-existing violation never bricks the index, and a consolidation edit that fixes entries always passes. Fails OPEN on any error (explicitly modeled on [[feedback_confidentiality_guard_selfdeadlock]], where a fail-CLOSED guard bricked Write/Edit/Bash machine-wide). Wired into `settings.json` PreToolUse `Edit|Write|MultiEdit` (additive diff, verified; backup at `settings.json.bak-2026-07-14`). 10/10 tests pass.

**2. `review_by:` frontmatter convention — dated memories now declare their own expiry.** `memory-integrity-probe.py` warns every run once a memory's `review_by:` date has passed ("OVERDUE — resolve it or archive it"). Report-only; never fails the probe. Added `ORA_MEMORY_DIR` env override so the check is testable against a fixture instead of the live memory set. 6/6 tests pass. Documented in `memory-policy.md` §3b. **Why:** the owner-outreach watch note set its deadline in prose, sailed past it, and nothing noticed — and when finally checked, the answer inverted its premise. A deadline in prose is a hope; a deadline in frontmatter is a check.

**3. Renamed `reference_scheduled_task_staleness_guard_false_positives.md` → `..._staleness_guard_trips.md`.** The file now holds a TRUE positive (Case 2), so the old name baked in the exact framing bias that nearly caused a wrong fix. All 5 inbound references repointed (MEMORY.md, event_log.md, ops_decision_log.md, the watch note, self-refs); memory-probe still reconciles 74/74.

**4. Autonomy-gate diagnostics — and a REJECTED change.** I had proposed narrowing Gate 2b to match on the write *target* rather than marker-anywhere. **On reading the gate, I withdrew that**: it matches marker-anywhere AND indicator-anywhere precisely because it cannot parse shell semantics, and a target-based rule would sail straight past `cd website-canonical; echo x > f.html`. The costs are asymmetric — a false positive costs one retry, a false negative publishes to the live site. **The guard's breadth stays.** What was actually broken was the *diagnosis*: the block message didn't say what matched, so the operator had to read the hook source. It now names the matched marker, the matched write verb, and explicitly says DO NOT create the override if the command merely quotes a site path (use Edit/Write instead). Behavior bit-for-bit unchanged — all 8 pre-existing autonomy-gate tests still pass. Same-class false positive hit twice today (once by me), so this pays for itself.

**CORRECTION to this morning's schematic entry — nothing was lost.** The earlier run reported oxford-command-center's tree as clean → DIRTY (12 files of RCT v03 work, "uncommitted"). Re-checked at close of session: the tree is CLEAN, and that work was **committed by a concurrent session to branch `feat/rct-v03-engine`** (commit `416c4b7`), which then checked back out to main. The "dirty" reading was a snapshot of another session mid-flight, not abandoned WIP. Schematic corrected and republished as REV 2026-07-14b. **Still open:** `feat/rct-v03-engine` is UNMERGED, so `main` continues to ship the old flat v1 replacement-cost constants ($125/$137.50/$150) — the platform engine is still one of the STALE v03 consumers flagged in [[project_replacement_cost_benchmark_unratified]].

**Method lesson (durable):** a dirty working tree on a shared checkout is not necessarily abandoned WIP — check `git reflog` and branch tips before characterizing it. Single-writer doctrine held throughout; nothing of the other session's was touched.

## 2026-07-14 — MEMORY.md index consolidation (15 over-length hooks → 0) + Owner-Outreach stale-guard watch CLOSED as a TRUE positive

**Index pass (Gabriel-requested, ran the `consolidate-memory` skill).** Collapsed all 15 over-length index hooks flagged by `doctrine-integrity-probe.py` (>150-char, per memory-policy §3) plus the oversized scope blockquote in the header down to one-line pointers. **doctrine-probe over-length count 15 → 0; total warnings 17 → 2.** `memory-integrity-probe.py` still reconciles 74/74 with no dead links, confirming no pointer was broken by the rewrite. **No content lost** — each trimmed detail was verified already present in its linked file before the hook was cut (the hooks were redundant restatements, so this was a pure trim, not a relocation).

Note: a bulk Python rewrite of the index was **blocked by `ora-autonomy-gate.py`** — the script text contained `oxfordra.net` path markers (from the SEO-audit and deploy-canon entries), tripping the website-tree write guard. Correctly a false positive; resolved by using the Edit tool rather than creating an override sentinel. Consistent with [[feedback_autonomy_gate_blocks_writes_not_reads]] — the marker, not the target, triggers it.

**Side finding — the material one.** [[project_owner_outreach_stale_guard_watch]] was a dated note whose watched fire (Monday 2026-07-13) had passed unexamined. Checked the actual run output rather than inferring from the absence of an alert entry: **the guard DID re-trip — but correctly.** Per the run's own summary email (10:11 AM ET): *"Master vintage: 2026-06-10 (33d) — file-modified 2026-07-12 (1d) — STALE=YES."* The off-market master's **content** is genuinely 33 days old; the file was merely *touched* a day earlier without the data being refreshed.

This inverts the watch's premise. Case 1 (2026-07-12) was the guard being **fooled by** the content-vs-mtime gap (a false positive); this trip is the guard **seeing through** it (a true positive). Same task, same guard, same alert shape, **opposite root causes and opposite correct responses.** The anticipated `owner_outreach_weekly.py` retry-before-fail-loud fix would have been actively harmful — it would have taught the guard to swallow a real staleness signal. **No code fix warranted.**

- Logged as **Case 2** in [[reference_scheduled_task_staleness_guard_trips]], with a new Step 0 ("first ask which signal the guard read") and a caveat that the file's "false positives" title now under-describes it — a recurrence is not itself evidence of a bug.
- Watch note rewritten as CLOSED (kept, not archived — it carries the durable lesson).

**OPEN / needs Gabriel:** the 2026-07-13 run held Notion page creation and the ledger commit (`--commit`) and emailed a **QUESTIONS FOR GABRIEL** block that is still unanswered. Nothing was lost this week (NET-NEW was 0 regardless), but **next Monday's run (2026-07-20) will hold the writes again** if the master's content vintage is still 2026-06-10 — the owner-outreach queue quietly stops promoting to Notion until the master gets a fresh off-market screening pass, or its age threshold is consciously relaxed. This is a data-freshness decision, not an automation bug.

## 2026-07-14 — Schematic-refresh: command-center tree went dirty (RCT v03 work); model canary expired off

**Schematic refresh (ora-cc-schematic-refresh, REV 2026-07-14a)** — daily diagnostics run; two material changes since the 07-13 run, both benign.

- **oxford-command-center working tree went clean → DIRTY**: 10 modified, 1 deleted (`config/replacement-cost.v1.json`), 1 untracked (`config/replacement-cost.v3.json`) — the RCT v03 replacement-cost work ratified today, spanning the acquisition ruleset, scoring engine/edge function, contracts, DealDrawer, and 4 test files. HEAD unchanged at `a6425ee` (#209) and in sync with `origin/main` — nothing unpushed, just uncommitted. Left untouched per single-writer doctrine.
- **`canary-model-check-temp` expired off** (one-time, expired 2026-07-13) — deliberate end-of-life for the model-pinning canary, not a failure. Fleet now 43 total: 40 enabled (cc=19, lams=21) / 3 expired-off. Enabled count held flat because `ora-cc-schematic-refresh` itself joined the CC fleet in the same window.

Probes: fleet-status ATTENTION (standing non-fault counts only — 9 never-ran, 3 expired one-time, 36 throttle skips; **same-time collisions 0**, second clean day) · governor-drift OK (545 files, DSCR 1.25x / LTV 40% consistent) · doctrine-integrity OK, 17 warnings (up 1: MEMORY.md over-length index entries now 15; CLAUDE.md flat at 1719 words) · confidentiality-guard 122/122 PASS (synthetic terms file, no-active-deal window) · memory-integrity 74/74 reconcile. ora-pm clean on main (`8418c44`), in sync.

Standing item: MEMORY.md over-length index entries are growing ~1/day (6 → 14 → 15 across three runs) — candidate for a consolidation pass.

## 2026-07-13 — LAMS fleet model-tag coverage closed (15 tasks tagged claude-sonnet-5)

Gabriel asked to audit the scheduled-task fleet for anything off the claude-sonnet-5 standard ([[reference_scheduled_task_model_standard]]). Findings: no task anywhere is confirmed running an off-standard model, but coverage was thin — CC/MCP fleet: 18/19 tasks tagged `UNVERIFIABLE` (structural — server-pinned, no live `model` field, only a canary test can confirm), 1/19 (`ora-cc-schematic-refresh`) confirmed `claude-sonnet-5`. LAMS/Cowork fleet: only 6/21 enabled tasks carried a `[MODEL:]` tag at all (all `claude-sonnet-5`, set 2026-07-08); 15/21 had never been tagged.

Gabriel approved tagging the 15 untagged LAMS tasks. Added `[MODEL: claude-sonnet-5 | set 2026-07-13]` to each SKILL.md description: `ora-consolidate-memory-monthly`, `ora-skill-store-drift-check`, `ora-skill-text-audit`, `ora-om-intake-ocr`, `ora-owner-outreach-queue-refresh`, `ora-passed-deal-tracker`, `ora-replacement-cost-refresh`, `ora-bearmode-refresh`, `ora-cam-reconciliation-annual`, `ora-counsel-review-standard-positions`, `ora-stale-pipeline-nudge`, `ora-ar-export-freshness-nudge`, `ora-session-sweep`, `ora-gis-endpoint-liveping`, `ora-cam-data-backfill`. Tagging only — does not itself change which model a task runs on (LAMS tasks bind to whichever model created them; no live `model` field to set), it only closes the observability gap so a future drift check can compare against the standard. LAMS/Cowork fleet is now 21/21 enabled tasks tagged, all `claude-sonnet-5`. 2 disabled tasks (`efulton-post-legalhold-consolidation`, `ora-tenant-db-dedup-remediation`) left untagged — low priority while disabled.

Also generalized the sonnet-5 default to the separate native "routines" mechanism (`schedule` skill / `CronCreate`) via [[feedback_routines_default_model]] — a distinct system from this dual-fleet registry.

Side finding (not fixed, flagged separately): `ora-skill-text-audit\SKILL.md` has a duplicated frontmatter block (identical `---...---` header twice) — cosmetic/parsing risk, out of scope for this pass.

CC/MCP fleet's 18 UNVERIFIABLE tasks remain unresolved — closing that gap requires a per-task canary test (server-pinned model, not settable from the registry side).

## 2026-07-13 — Schematic-refresh: repos back to clean, last fleet collision cleared

State transitions observed on the first automated `ora-cc-schematic-refresh` fire (vs the 2026-07-12 manual dry-run):
- **Fleet same-time collisions 1 → 0.** The last LAMS collision (ora-passed-deal-tracker × automation-health-monitor at 06:30) is resolved — automation-health-monitor now fires `5 11 * * 1-5` (11:05 AM weekdays). fleet-status.py reports 0 same-time collisions; 42 tasks total (40 enabled cc=19/lams=21, 2 expired-off).
- **oxford-command-center dirty → clean.** The 8 uncommitted date-math WIP files flagged 07-12 are committed and pushed — HEAD a6425ee (#209, day-count math anchored on real time across debt scoring, capital allocation, renewals, tenants); working tree clean, in sync with origin/main.
- **ora-pm recovery branch → main.** Now on main (HEAD 8418c44), clean, in sync with origin — no longer parked on recovery/2026-07-05-object-db-loss.

All five probes green or warn-only, zero hard failures. Standing cosmetics unchanged in kind: CLAUDE.md 1719 words (warn > 1700), 14 MEMORY.md index entries over the 150-char pointer policy. Schematic artifact updated in place (REV 2026-07-13a).

## 2026-07-13 — Scheduled-task registry cleanup (CC fleet): 2 expired one-time entries deleted; 2 health-guard "systematization notes" verified as false alarms
Gabriel-directed during the 2026-07-13 ora-health-guard interactive follow-up. Removed `continue-cc-setup-optimization-batch-2c-3` and `investigate-plan-gate-worktree` via supervised `delete_scheduled_task` MCP (both already fired 2026-07-12T22:01, enabled:false, folders already archived in commit f6c36a3; SKILL.md files left on disk for recovery). Single-writer gate clear (registry-membership.log last write 2026-07-09). CC fleet 44→42 tasks; EXPIRED one-time 4→2.

Two health-guard systematization notes from the same run were verified as FALSE ALARMS and deliberately NOT acted on: (1) the ✅/⚠️ email-subject "mangling" was terminal stdout glyph rendering only — U+2705 confirmed intact in both the sent COM subject and the UTF-8 send-log (`startsWithCheck=True`), so the ora-am-brief Notion-down fallback contract is unaffected; NO change made to send-via-outlook.ps1. (2) The "Rate Snapshot — Current" staleness self-resolved when ora-am-brief Block A ran in the catch-up burst (page now prefetch_status:OK, fetched_at 2026-07-13 09:57 ET, full curve recovered) — root cause is the documented app-open/burst scheduler latency, not a code defect; NO code change.

Remaining 2 EXPIRED one-time entries (`efulton-post-legalhold-consolidation`, `ora-tenant-db-dedup-remediation`) are LAMS-fleet — unreachable from the CC session; flagged for supervised Cowork-side cleanup. The efulton one is E.-Fulton-sensitive — surface to Gabriel before deleting. Throttle-skip / AM-pileup advisories left unchanged (re-timing 15 crons is a deliberate-schedule decision for Gabriel, not a silent autonomous fix).

## 2026-07-12 (cont.) — Franklin Co. Auditor parcel lookup: blocked by Browser MCP instability, not executed

Follow-up to the open-sessions-board decision "$2.0M scenario model rerun — Pull it via live browser session" (E. Fulton note-purchase-vs-short-sale memo v02, session `local_ac2f684e`, open item: property-tax dollar delta at property.franklincountyauditor.com for parcels 090-005616 / 010-085755 / 010-099214 / 010-004280 / 010-099201). Attempted across two retry rounds (~10 total calls to `preview_start`/`navigate`) spanning ~10 minutes: got a mix of Claude-sonnet-5 safety-classifier "temporarily unavailable" errors, one explicit Stage-2 classifier denial, and one navigation that reported success but left the tab in a permanent "Page not registered" / 0x0-viewport state (read_page, screenshot, and console all came back empty/timed out). Not a site-side ASP.NET-postback issue this time — the Browser MCP itself never reached a usable state. Per the task's own not-urgent framing (DD nice-to-have for a note memo, not blocking anything time-sensitive), stopping rather than continuing indefinitely. Parcel IDs and portal URL are recorded here and in the memo's own open-items table for whoever picks this up next — retry the Browser MCP directly, or route to Gibbs (Gabriel's other offered option) if a fresh attempt also fails.

## 2026-07-12 (cont.) — Open-sessions board dispatched: 4 items decided, 1 self-resolved before surfacing

Daily 5 PM ET `ora-open-sessions-board` run probed 120 unarchived sessions (14-day lookback) across both fleets; 4 survived exclusion (fleet runs, <30min age, already-answered-with-no-new-activity) to reach the board. A 5th candidate ("Online report formatting," 30.6h old) was re-verified against its live transcript tail before rendering and found already resolved ("Done — both files relocated, originals deleted") — dropped rather than surfaced stale.

Step 4.5 Notion deal-stage reconciliation: fetched all 12 rows from the Acquisition Pipeline Tracker (row count matched, no partial page), diffed against the snapshot — 0 transitions, nothing to log.

**Decisions Gabriel made and what was executed:**
1. **Systematization candidates queue** (oxford-command-center#208 / ora-pm#4 / ora-skills#14 / website-canonical#26, all merged) — Verify deploy. **Executed**: confirmed via Netlify MCP (`get-project` + `get-deploy-for-site`, site `95ac0a0f-a84d-4400-b919-b8d7a8526646`) that production deploy `6a542fb1b9727d000849865f` (commit `f78c2dfd`, PR #26 merge) is `state: ready`, secret scan clean, Lighthouse 99/100/100/100. No further action.
2. **Pending Claude-only blockers** (CAM-data punch-list handoff to Cowork, stalled on an unactioned "Ignore item 1" message) — Drop / park. No action taken; session left as-is.
3. **Scheduled tasks status** (off-cadence Sunday fleet check, 4 flagged items) — Send the alert email. **Executed**: sent "ORA Automation Health — 4 flagged items (2026-07-12 fleet check)" to ggoldberg@oxfordra.net (no cc), reconstructed from the Cowork session's findings — ora-owner-outreach-queue-refresh self-resolved, ora-calibration-snapshot silent 11 days (the real concern), ora-doctrine-integrity-guard/ora-aaos-expire-leases low-severity overdue.
4. **$2.0M scenario model rerun** (E. Fulton note-purchase-vs-short-sale memo v02, Franklin Co. Auditor tax-delta open item) — Pull it via live browser session. Parcels identified from the source session: 090-005616 / 010-085755 / 010-099214 / 010-004280 / 010-099201 at property.franklincountyauditor.com. Execution status: see same-day follow-up entry (Browser MCP classifier was intermittently unavailable at dispatch time).

## 2026-07-12 (cont. 5) — CC-setup optimization Batch 2c + 3 (registry write-guard, connector-drift & doctrine leak-scan self-check, model-currency step)

Scheduled run `continue-cc-setup-optimization-batch-2c-3` executed Batch 2c + Batch 3 of the plan `~/.claude/plans/spicy-crunching-starlight.md` (Batches 1, 2a, 2b already merged as PR #15 / `e1060a8`). TDD throughout; work isolated in worktree `batch-2c-3-registry-connector-probes`.

Independent opus code review verdict: **READY TO MERGE** — no confirmed/plausible defects; all 3 suites green (registry-guard 13/13, connector-drift 11/11, doctrine 24/24); every live run genuinely clean (non-vacuous). Left OPEN for Gabriel to merge (merging to `~/.claude` main is what DEPLOYS the guard — until then the live settings.json still has 8 PreToolUse entries, not 9).

**Shipped (branch `batch-2c-3-registry-connector-probes`, commit `ef7c18f`):**
- **Batch 2c** — `hooks/registry-write-guard.py` (+ test): PreToolUse `Edit|Write|MultiEdit` guard that BLOCKS (exit 2) a direct write to either fleet's `scheduled-tasks.json` registry backing file, GUID-agnostically (path segment `claude-code-sessions` / `local-agent-mode-sessions` + basename). Fail-open on its own errors. Wired into `settings.json` PreToolUse (now 9 entries). Backs the 2026-06-09 registered-but-unscheduled incident that had zero automated guard. Registry paths CONFIRMED live: both under `%APPDATA%\Roaming\Claude\{fleet}\<guid>\<guid>\scheduled-tasks.json`.
- **Batch 3.1** — `maintenance/connector-drift-probe.py` (+ test): reconciles a NEW machine-readable `<!--BEGIN/END-CONNECTOR-ROSTER-->` block in `memory/tech.md` against live state (`.claude.json` mcpServers keys + `settings.json` permissions.allow prefixes). Flags documented-alive-but-dead (Grain class), documented-dead-but-alive (FRED class), and undocumented-live mcpServers keys. Live run clean (21 roster entries). Exit 0/1/2, precision over recall.
- **Batch 3.2** — `maintenance/doctrine-integrity-probe.py`: check-8 confidential leak scan no longer goes inert at 0 active deals — it runs `leak_scan_selfcheck()` (synthetic positive+negative matcher control) so the leak detector stays regression-tested through a no-active-deal window (reuses test-confidentiality-guard.py's synthetic-terms idea). Live doctrine probe exits 0 with the self-check PASS line.

**Batch 3.3 — premise correction, done differently than specified:** the task assumed automation-health-monitor had a "Step 0.07" model-currency check to EXTEND. Ground-truth check: the SKILL.md (repo + runtime copies, byte-identical) had NO model-currency step at all — the methodology was documented in `reference_scheduled_task_model_standard.md` but never implemented. So the step was ADDED (not extended): ora-skills commit `eb95a5d`, `automation-health-monitor` v1.4, new "Step 1.5 — Model-currency check (both fleets)". LAMS = match-standard on the `[MODEL: id | set DATE]` description tag; CC/MCP = presence + observation-freshness on `~/.claude/scheduled-tasks/<id>/SKILL.md` `[MODEL: ...]` frontmatter (model server-pinned = not settable; the "structurally uncoverable" claim was FALSE — `ora-cc-schematic-refresh` carries a real `[MODEL: claude-sonnet-5 | checked 2026-07-12]`). **NOT deployed — needs `package-and-stage-skill` + a manual Cowork Save-skill click.** Corrected `reference_scheduled_task_model_standard.md`: "structurally uncoverable" → "not settable but observable"; stale "11 UNVERIFIABLE" → live 12 (+1 id-pinned, remainder untagged).

**Two unrelated pre-existing findings surfaced (NOT caused by this work):**
- `hooks/tests/test-ora-autonomy-gate.py` fails on the MAIN checkout because a live, legitimate `hooks/overrides/allow-website-change` sentinel is active — content: "Gabriel confirmed in-turn 2026-07-12 for broker-upload-session Blobs diagnostic deploy" (a concurrent session's authorized override, 60-min TTL from 18:02). The gate correctly allows website writes while it's valid; the test is coupled to the real overrides dir (should use an isolated OVERRIDE_DIR env, like shared-checkout-guard's SHARED_CHECKOUT_REPOS). Transient — green once the sentinel expires.
- `hooks/tests/test-confidentiality-guard.py` cannot run in a worktree (gitignored `confidential-terms.json` absent from the fresh checkout); PASSES on main.

Plan-gate override written for this session (reason logged) — executing a pre-approved written plan under a scheduled task.

## 2026-07-12 (cont. 4) — Cowork punch-list follow-up: 6-item investigation + 4 decisions executed

Cowork closed its own 6-item punch list tonight (full writeup: Notion "Punch-List Review — 2026-07-12", 39b6ecd8-9e59-8194-b33a-fc58f6b922db, Operations Hub 32b6ecd8) and handed the pieces needing real `~/.claude` filesystem/git/local-tooling access back to Code. Investigated all 6, then executed 4 decisions Gabriel made interactively.

**Findings (all read-only investigation, no writes yet at this stage):**
- **CAM reconciliation**: lease-abstraction-pipeline's claim was PARTIAL — Lease Type extraction is real, CAM Recovery Type and Tenant Pro-Rata Share were not (schema gap, not an oversight). Separately, Cowork's QB-only search undersold available data — Sepich/FVC, 29000 Info Lane (Yardi), and 9620 State 350 (Peak-REP) all already have usable CAM/recovery data outside QuickBooks.
- **Tenant DB**: the 22/17/7/35/5 baseline was never lost — lives in `reference_tenant_db_completeness_gap.md` + `event_log.md`'s 2026-07-11 entry (Cowork's own session had already found and logged this before re-deriving). Spot-check reproduced Cowork's larger 91/12/20 figures exactly — the DB has gotten worse since 07-09/07-10, not better.
- **B3 burn-in**: all 4 confirmed directly — memory-path repoint clean on all 3 probes; oxford-site ~3 months stale (untouched since April 15, not "~15 pages"); ora-skills README drifted again (44 documented vs. 51 live); "~30 dormant AI-tool folders" stale, only `.copilot` remains.
- **OneDrive "(1)" residuals**: Document2.docx identified (6372/6376 Greenland Rd, Jacksonville FL, GATOR-NOLE LLC — parked out-of-state 1031 lead); North East Insulation LOI extracted via antiword (Fairground Village Center LLC / Northeast Insulation Services, 2822 Banwick Rd — one digit off 2820 Banwick, almost certainly a Sepich Portfolio suite LOI); SunstoneOxford whiteboard confirmed genuinely unreadable (Fluid Framework binary, no plaintext). Nothing moved.
- **Owner-Outreach**: CAGIS re-queried live and confirmed working (200/JSON, 420,242-record AGOL count) — tonight's failure was transient/machine-specific, not a dead endpoint. `--strict-age` already effectively WARN-only per a documented 2026-07-12 Gabriel-approved relax. python-docx gap traced to the 2026-07-05 migration wiping site-packages; a `requirements.txt` already exists to fix it going forward.
- **Staged skills**: neither "4" nor "10" was accurate — zero skills were actually staged; both reference points traced to stale/junk artifacts (the 07-09 8-skill batch already imported, and an accidental `--help`-flag-typo 43-skill dump explicitly flagged as junk in an earlier entry).

**Decisions Gabriel made (interactive) and what was executed:**
1. **Tenant DB duplicates** — remove the 20 (actually 19, confirmed via live query — see below) pre-labeled "⛔ DUPLICATE" rows now, hold the 91 groups for a fuller pass. Queried and confirmed the exact 19 page URLs. **Not executed** — Code's Notion tool only exposes property/content edits, not page-level archive (only database-level trash is exposed). Handed the exact list to a Cowork follow-up prompt instead.
2. **CAM skill fields** — build CAM Recovery Type + Tenant Pro-Rata Share into lease-abstraction-pipeline. **Executed**: added Fields 31/32 (`lease-abstraction-pipeline` v2.2→v2.3, commits 87b69d3/1474349, pushed to `ZeOoba/ora-skills` main via an isolated worktree — HEAD had moved from a concurrent writer mid-session, verified clean before fast-forward merging). CAM Recovery Type maps to the Notion Tenant DB's existing 7-option select (was defined, unused); added a matching new "Tenant Pro-Rata Share" percent property to that same live data source (additive schema change only). Repackaged and staged (`_staging/2026-07-12_cam-fields/lease-abstraction-pipeline.skill`) — needs Gabriel's Save-skill click to go live in Cowork's runtime. Also fixed a frontmatter-description packager-limit rejection (1108/1024 chars) using today's established pattern (move changelog prose out of frontmatter into the body Changelog section — same fix as automation-health-monitor/parcel-data-recovery earlier today) and added `.claude/worktrees/` to `.gitignore`.
3. **Owner-Outreach age guard** — add a narrower guardrail so the unattended Monday run pauses on STALE instead of auto-proceeding, without touching Gabriel's own manual WARN-only runs. **Executed**: `ora-owner-outreach-queue-refresh` SKILL.md v1.1→v1.2 — STEP 1 now has a STALE GUARD that skips STEP 2/3 (Notion page creation, ledger commit) and adds a "QUESTIONS FOR GABRIEL" email section instead, on this unattended path only. No Python script changes — the gate lives at the orchestration/SKILL.md layer, which already owned the Notion-write decision and already had the QUESTIONS FOR GABRIEL convention.
4. **CAGIS re-test** — re-ran the exact leftover probe URLs from tonight's failed run live; all returned valid 200/JSON. Confirmed transient, not wired into anything (no script changes made).
5. **Housekeeping**: this entry (event_log), plus a Cowork follow-up prompt drafted for the 19-row archive handoff and the Sepich/Yardi/Peak-REP CAM data pull (step 5 of the CAM plan).

**Still open for Gabriel:** the 91 duplicate groups (category-by-category remediation call, unchanged); the Save-skill click for lease-abstraction-pipeline v2.3; the Cowork follow-up (19-row archive + CAM data pull) needs to actually be sent/run.

## 2026-07-12 — PR #207 opened: two adversarial-review follow-ups from PR #206 (sort tie-break + leasingRisk lapsed-tenant)

Continuation of the frozen-dateline fix (PR #206, merged as 6137083). After merge, Gabriel directed fixing the two lower-severity items flagged by the original adversarial review rather than leaving them as untracked follow-ups.

**Sort tie-break** (`src/analytics/conditions.ts`): PR #206's F2 fix collapsed every past-due balloon's impactAnnualUsd to the same clamped value (0), creating ties on severity+impact that the sort's equal-amount branch resolved by `return bAmt - aAmt` — which returns 0 directly on a genuine tie, exiting before any tie-break, so relative order silently depended on input-array iteration order. Added `a.id.localeCompare(b.id)` fall-through, matching the pattern already used in capital-allocation.ts/insurance-conditions.ts.

**leasingRisk lapsed-tenant treatment** (`server/warehouse/capital-allocation.ts`): the reviewer found that a lease lapsing between the workbook's data date and the live run date now buckets 'expired' and drops out of the dollar-weighted nearTermExpiryRent term entirely, replacing it with only a flat +10 signal — lowering priorityScore for a property whose material tenant just lapsed. Two options presented to Gabriel (include in dollar-weighted term vs. keep flat+10 and document as intentional); **Gabriel chose inclusion**. Fixed with a `freshlyLapsed` condition (`leaseEnd >= meta.asOf` at bucket='expired') — a lease still counts if it was current as of the workbook's own snapshot but has since lapsed; genuinely-stale-expired leases (already expired as of the workbook date) stay excluded as before.

Rewrote the existing I-6 (H2) integration test fixture (3 leases: unaffected / freshly-lapsed-now-included / genuinely-stale-still-excluded) — priorityScore assertion (49.2368) derived by running the real code rather than hand-computed, after an initial hand-calc mismatch (+2.0, traced to `renewalSignals`' 'lapsing' band firing on ANY past leaseEnd with no renewal stage recorded, independent of lease status — not what I'd assumed).

Ran the formal `refute-financial-change` Workflow (wf_b55b4d9f-366) a second time against these two new changes specifically (not just relying on the original PR #206 review) — `anyRealDefect: false`, worst severity low across all 3 lenses. One comment-accuracy issue caught and fixed (the `freshlyLapsed` inline comment said "holdover" but the implemented behavior is status-agnostic — code was already correct, comment was fixed to match).

Gate flaked on the same pre-existing `capital-allocation-api.test.ts` R-1 hook-timeout 3 times across this session (confirmed clean in isolation every time) — consistent with the already-documented [[feedback_npm_test_intermittent_access_violation]] class; not investigated further, just rerun each time per that memory's guidance.

PR: https://github.com/ZeOoba/oxford-command-center/pull/207 (branch `fix/leasingrisk-lapse-and-sort-tiebreak`, off updated main post-#206-merge). All CI checks green (gate, refute-required, CodeRabbit). Not yet merged — Gabriel's call.

## 2026-07-12 ora-flood-zoning-dd write-in-place fix — corrected a stale premise before fixing

Gabriel pasted a Claude Code prompt (drafted assuming a standing flood-determination
pipeline script lived in the brain repo or another orchestrator) asking for a
write-in-place bug fix, per Engineering OS `/debug` doctrine. Pre-flight investigation
(systematic-debugging Phase 1) found the premise stale on two counts, surfaced both to
Gabriel before touching anything:

- **Wrong target:** no such script exists in `oxford-command-center` or any git repo.
  The actual offending code was a one-off, non-version-controlled Cowork script,
  `_autodd_flood_20260712.py`, in `Investment Candidates -- 2026\archive\` — one of ~15
  same-day throwaway `_*_20260712.py` scripts from the Cincinnati/Hamilton-Butler-Clermont-
  Warren auto-DD batch pass, already retired.
- **Already-done:** the bug fired for real (line 106 `openpyxl.load_workbook(MASTER)` →
  line 157 `wb.save(MASTER)`, same path, on the 20260610 AllMarkets-OffMarket-Master
  v05), but the SAME session had already caught and hand-remediated it — copied
  v05→v06, logged the deviation in the workbook's own Refresh Log/QC tabs. No data was
  lost.

Root cause of *why* it happened: `parcel-data-recovery` SKILL.md has carried the
"always emit a new version, never overwrite" rule as Iron rule 6 since v1.0; the sibling
skill `ora-flood-zoning-dd` (whose procedure the script implemented) had no equivalent
guardrail at all — a fresh ad hoc script written against its procedure had nothing to
inherit.

Gabriel chose both remediation options via AskUserQuestion:
1. **Doctrine fix (durable):** added a batch-write safety Iron Rule to
   `ora-skills/ora-flood-zoning-dd/SKILL.md` (v1.0 → v1.1, mirroring parcel-data-recovery
   Iron rule 6) — copy the master to a new version FIRST, write only to the copy. This is
   what actually prevents recurrence next time this skill is used for a batch pass
   (Indianapolis, Kansas City, Madison, etc.).
2. **Audit-record patch (low-value but requested):** patched the retired
   `_autodd_flood_20260712.py` itself (added `next_version_path()` helper — copy-then-write,
   versioned by scanning existing `_v##` files rather than hardcoding) even though it will
   never re-run, so the historical artifact reflects the correct pattern.

Verification: wrote a repro test showing the ORIGINAL in-place-write pattern fails
(source hash/mtime changes, no new version emitted), then confirmed the PATCHED
`next_version_path()` passes (source untouched, new versioned file created, second call
doesn't collide) — both via a scratch test script, plus `py_compile` on the patched
archived script. No git commit made in `ora-skills` (single-writer repo; edits followed
the pre-check protocol — clean tree, HEAD matched last known commit `57b380c` — but a
commit itself wasn't requested).

**Doctrine calibration:** pre-flight failure analysis (assume wrong-target/already-done
before executing a prescriptive fix prompt) caught a fix request against dead code before
any wasted TDD cycle on a script that would never run again — worth the one clarifying
question rather than a wrong fan-out.

## 2026-07-12 (cont.) — Desktop Commander Extension/plugin "surface exclusivity" framing corrected

Follow-up to the same-day `$var`-stripping engine-wide confirmation. Investigated the flagged open item
against [reference_desktop_commander_extension_slow_init.md](reference_desktop_commander_extension_slow_init.md):
its closing paragraph claimed "the Claude Code plugin form of DC serves the Code surface only," worded
in a way that implied the Desktop Extension (`mcp__Desktop_Commander__*`) was Cowork/LAMS-exclusive and
unreachable from Code. Directly contradicted by the prior repro session, which called
`mcp__Desktop_Commander__*` successfully (`get_config`, `start_process`, `force_terminate`) from a Code
CLI session.

**Corrected:** a Code CLI session has **both** DC connections live simultaneously —
`mcp__Desktop_Commander__*` (Extension, `isDXT:true`) and `mcp__plugin_desktop-commander_desktop-commander__*`
(plugin, `isDXT:false`). "Does not conflict (separate hosts)" undersold it — both are actively usable from
Code, not just non-conflicting. Added a trap warning: the Extension's `currentClient` field is
last-connection-wins, not a live per-request identity — it can show a stale Cowork/LAMS identity even
when called from Code, so it shouldn't be used to infer "which surface is asking" on that connection.
What's still correct and unchanged: the plugin form genuinely is Code-only (doesn't load in headless
remote Cowork scheduled runs) — that half of the original framing held up.

**Files modified:** `reference_desktop_commander_extension_slow_init.md` (correction paragraph added,
in-place per "corrections beat history"), `MEMORY.md` (both Desktop Commander index lines refreshed to
match current file state — the `$var`-stripping line was itself still stale, referencing "not yet
repro'd live" after that had already been confirmed earlier the same session).

## 2026-07-12 (cont.) — Desktop Commander $var stripping CONFIRMED engine-wide; "one shared server" framing corrected

Closed the open "inference, not confirmed" item on the PowerShell `$variable`-stripping bug
([reference_desktop_commander_powershell_variable_stripping.md](reference_desktop_commander_powershell_variable_stripping.md)).
Ran the live repro from a Code CLI session (3 clean variations: `$testVar`, `$srcPath`/`$dstPath`,
`$myCounter`) — all 3 stripped the variable token from the `-Command` string before execution,
identically to the two prior Cowork-session confirmations. **Confirmed engine-wide, not
Cowork/Extension-scoped.**

Also surfaced and corrected an imprecision in the prior evidence: a Code CLI session actually has
**two distinct, independently-running Desktop Commander server processes** reachable
(`mcp__Desktop_Commander__*`, the `.mcpb` Desktop Extension, `isDXT:true`, v0.2.44, `currentClient`
still showing the last Cowork/LAMS connection; and `mcp__plugin_desktop-commander_desktop-commander__*`,
the Claude Code plugin form, `isDXT:false`, v0.2.45, `currentClient: claude-code/2.1.205`) — not one
shared server as the single-`clientId` evidence had implied. The `clientId` match is a persisted
config value, not proof of a single live process. The `$var`-stripping bug reproduces identically on
both, so this doesn't change the workaround's applicability, but it means the "single shared DC
server" framing used in some memory notes is imprecise and shouldn't be reused for other scope
questions without re-verifying. Flagged as an open follow-up against
[reference_desktop_commander_extension_slow_init.md](reference_desktop_commander_extension_slow_init.md)'s
"Extension serves Cowork/LAMS, plugin serves Code only" framing — the Extension is directly reachable
from Code CLI too, just not the connection Code's own plugin config defaults to.

## 2026-07-12 (cont.) Memory correction: FRED live (not unregistered); Grain/Windows-MCP/Claude Preview removed from Active roster

Follow-up to the same-day comprehensive setup-optimization review (Batch 1a). Two roster corrections
in `tech.md` and `00_system_of_record.md`, both verified directly against `.claude.json` and the
live tool registry rather than assumed:

- **FRED was documented "UNREGISTERED as of 2026-07-09" in both files, but is actually live right now.**
  `.claude.json` top-level `mcpServers` carries a complete `fred` stdio entry with a populated
  `FRED_API_KEY`, and all 4 tools (`fred_search_series`, `fred_series_info`, `fred_observations`,
  `fred_latest`) are live and callable this session. No prior event_log entry documents when/how it
  was restored — this entry backfills that gap. Corrected the stale language in both docs.
- **Grain (`468d2dad`), Windows-MCP, and Claude Preview were listed "Active" in both docs but are
  dead** — absent from `.claude.json`, absent from any `settings.json` permission entry, zero live
  tools resolve for any of them. Windows-MCP was already noted abandoned as a screen-driver approach
  back in early June (an archived project note says so) but the connector roster was never updated
  to match. Removed all three from the Active lists in both docs (demoted to a retired note, not
  deleted — the historical fact is preserved in the doc text itself).

Root cause (see the same day's broader audit): no automated probe cross-checks these roster docs
against live registration state — this exact gap is what let both drifts happen simultaneously,
undetected, until a manual review caught them. A `connector-drift-probe.py` sibling to
`governor-drift-probe.py` is planned (see the optimization plan at
`~/.claude/plans/spicy-crunching-starlight.md`, Batch 3) to make this self-detecting going forward.

## 2026-07-12 (cont. 5) — Punch-list workflow-optimization candidates actioned (5/5)

Followed up the 2026-07-12 Punch-List Review session's 5 workflow-optimization candidates:
1. **Stale-Guard Watch standing reference created** — [[reference_scheduled_task_staleness_guard_trips]], a durable pattern log distinct from the scoped, self-archiving [[project_owner_outreach_stale_guard_watch]] tracking note. Logged Case 1 (2026-07-12, ora-owner-outreach-queue-refresh 17:16→17:24 self-correction, root cause = verify-only pass touching mtime, not a real rescore).
2. **Tenant DB dedup — one-time cleanup plan drafted, no writes.** Added a 2026-07-12 addendum to reference_tenant_db_completeness_gap.md with the live re-derivation (91 duplicate groups/191 rows, 20 pre-flagged-never-removed, 12 stale-link-blanked — larger than the 07-10 baseline) and per-category remediation options with recommendations. Still needs Gabriel's category-by-category go-ahead before any Notion/HubSpot writes.
3. **Fleet Python dependency audit — verified live, not just documented.** `pip show` on the shared Python 3.13 interpreter confirmed python-docx 1.2.0, openpyxl, pandas, reportlab, pypdf all present at the versions pinned in both `scheduled-tasks\_shared\python-requirements.txt` and the sibling `Investment Candidates -- 2026\requirements.txt` (same interpreter, both frozen 2026-07-12 — the fix from the 07-12 python-docx gap already held). Added MIGRATION_RUNBOOK.md step B1.3a (one-shot `pip install -r` restore for both files) + a B3 burn-in verification line, closing the reactive-install-gap pattern procedurally for the next migration.
4. **Ops Decision Log created** — [[ops_decision_log]], a lightweight companion to deal-decision-ledger.md for small recurring yes/no operational calls. Seeded with 3 entries: staged-skill count (10, not 4), Stale-Guard Watch note existence (didn't exist before today), and the dependency-audit result above.
5. **CAM data-readiness backfill registered** — one-time scheduled task `ora-cam-data-backfill` (fires 2026-08-15 07:00 ET, well ahead of the next ora-cam-reconciliation-annual fire at 2027-01-15), runs a lease-abstraction-pipeline batch pass against SharePoint lease docs to populate CAM Recovery Type/OpEx Budget PSF/Lease Type/pro-rata share for the 139-tenant gap found 2026-07-12 (0/139, 0/139, 16/139, 45/138 coverage respectively).

MEMORY.md indexed both new reference files. No Notion/HubSpot tenant-row writes made (guardrail respected); the two new scheduled-task/runbook changes are additive/non-destructive.

## 2026-07-12 (cont. 4) — register-scheduled-task v2.4 shipped; near-miss caught mid-commit (single-writer discipline)

Shipped the v2.4 fix recommended in the prior entry: `ora-skills/register-scheduled-task/SKILL.md` concurrent-writer check promoted from a `registry-membership.log` timestamp heuristic to a direct `session_info list_sessions` scan for a live sibling session (log has no visibility into cron-only edits — exactly the class of collision that prompted this). Committed `64e92de`, pushed to `origin/main` clean.

**Near-miss while landing it:** the first commit attempt (`git add register-scheduled-task/SKILL.md; git commit -m ...`) swept up two unrelated files — `parcel-data-recovery/SKILL.md` and `parcel-data-recovery/references/endpoints.md` — that a concurrent session had staged (not just modified) between this session's `git status` check and the `git commit` call, despite `git add` only naming the one intended file. `git commit` without `-a`/pathspec commits everything in the index, and the index had been touched by someone else in the gap. Caught via `git show --stat -1` before push (112 insertions / 24 deletions was far more than the 14/3 the diff had shown), not by inspection at commit time. Corrected with `git reset --soft HEAD~1` (uncommit, keep index) → `git reset HEAD -- <the two parcel-data-recovery files>` (unstage only those, restoring them to exactly their pre-commit modified-not-staged state) → re-commit with only the intended file → verified via `git show --stat` and `git status` before push. Nothing of the other session's work was lost, altered, or pushed under this commit.

**Read-across:** this is a live instance of the exact class of risk the v2.4 fix targets, in the adjacent shared surface (`ora-skills` git index) rather than `event_log.md`. Worth widening the v2.4 `list_sessions` pre-write check (or a parallel doctrine note) to cover git commits in shared repos, not just scheduled-task registry writes — `git commit` should be treated as touching shared state requiring the same live-sibling check, and `git status`/`git diff --stat` immediately before commit is not sufficient on its own since the index can change in the gap before the commit call executes. Not yet fixed in doctrine; flagging as a follow-up rather than fixing unprompted mid-task.

**Open item for Gabriel:** v2.4 is live in the repo but the Cowork skill cache still runs v2.2 until `package-and-stage-skill` + a Save-skill click land it — did not run that unprompted.

## 2026-07-12 (cont. 3) — LAMS scheduler collision fix: root-caused the event_log lock — two concurrent Cowork sessions, not a real incident

Investigated the WinError 5 lock flagged in both of the immediately preceding entries. Root cause: two independent Cowork sessions ("LAMS/Cowork scheduler collision fixes", session `local_7165b738-...`, and this session) were executing the identical handoff concurrently — same 3 task IDs, same target crons. Confirmed via `session_info` `list_sessions`/`read_transcript`, not inference: the sibling session's transcript shows it ran `list_scheduled_tasks`, found all 3 crons already at target (this session's update having landed moments earlier), and re-pinned them idempotently — correct behavior per doctrine (trust observation over memory), not drift or a stale-note error.

**No harm done:** no duplicate task IDs registered (unlike the 2026-06-09/07-08 precedents — both sessions targeted existing IDs with identical values), no data loss (`event_log.md.pending\` drained cleanly, both entries now present, newest-first, intact), fleet state is correct and idempotent. Net cost: two redundant journal entries for one action (this entry's two immediate predecessors) and the file-lock symptom itself.

**Doctrine gap:** register-scheduled-task v2.2's concurrent-writer check relies on `registry-membership.log`, which — as the sibling session itself noted — tracks task adds/drops, not cron edits, so it would never have caught this class of collision. Neither session checked for a live sibling via `session_info list_sessions` before starting, which would have caught it directly (the sibling showed as a distinct non-idle session with a matching title). Filed as a v2.3 fix to the repo skill source (`ora-skills/register-scheduled-task/SKILL.md`): concurrent-writer check now calls `list_sessions` and treats another non-idle session with an overlapping task/title as a hard stop-and-confirm, not just a log-timestamp heuristic.

**Follow-up owed:** repo skill edited this session; live Cowork skill cache still needs `package-and-stage-skill` + a Save-skill click to pick up v2.3 (per its own doctrine — registration is Gabriel's click, not automatable here).

## 2026-07-12 Cowork workflow-notes triage (Owner Outreach Metro gap, DC PowerShell bug, Clermont/Warren decision)

Gabriel flagged three standing workflow notes for a look; triaged all three in one Cowork pass.

- **Owner Outreach Queue Metro select — Kansas City added.** The Cincinnati gap Gabriel flagged was
  already fixed same-day by the parcel-data-recovery run (see the 07/12 Off-Market Deal Sourcing page)
  and Baltimore-MD was already present, but a live check of the Notion data source
  (`caa809b7-1da3-49d5-ab92-bcd7f36ca43e`) schema turned up **Kansas City still missing** despite being
  one of ORA's 6 Primary Markets (market-monitor v1.1 / target-markets.json). Added via
  `notion-update-data-source` `ALTER COLUMN "Metro" SET SELECT(...)`, preserving all 8 existing options
  and colors, additive only. All 9 canonical target metros + "Other" now present.
- **Desktop Commander PowerShell `$var` stripping — logged.** New reference file
  [reference_desktop_commander_powershell_variable_stripping.md](reference_desktop_commander_powershell_variable_stripping.md),
  indexed in MEMORY.md. `start_process` silently drops `$variable` tokens from PowerShell `-Command`
  strings (confirmed twice); cmd.exe with literal paths is the working alternative. Root cause not
  identified — flagged as a workaround, not a fix.
- **Clermont/Warren valuation methodology — DECIDED, not yet executed.** Raised as a decision question
  rather than resolved unilaterally (no verified Assessed→Modeled-Market-Value conversion exists for
  these two OH counties; Hamilton/Butler's ratios don't hold a fixed multiplier). **Gabriel's call:**
  pull a ~15-20-parcel sale-comp sample per county and calibrate county-specific ratios, rejecting both
  the blind OH-statutory-35% shortcut and permanent DATA-GAP exclusion. Logged on the 07/12 Off-Market
  Deal Sourcing Notion page's Open Items. **Execution (comp pull, calibration, P1 recompute, master
  rebuild) is a separate, not-yet-run parcel-data-recovery pass** — flagged, not started, to avoid
  burning a long live-endpoint pull inside an unrelated triage session.

## 2026-07-12 DC nested-quote mangling logged + status check on round 2

Gabriel asked whether round 2's three fixes were fully resolved. Honest answer given: no —
Clermont/Warren execution (comp pull/calibration/rebuild) and the DC $var cross-surface repro (Code CLI)
are still genuinely open, by design, not oversights. The Notion parity extension and parcel-data-recovery
v1.4 packaging were confirmed resolved (`list_scheduled_tasks` re-check; runtime skill cache already
reflects v1.4 with both files present, suggesting Gabriel already installed the staged `.skill`).

Also fixed the flagged note about a second DC quoting bug hit mid-round-2: a nested-double-quote
`cmd.exe /c "..."` call silently injected a leading space into a path argument (exact repro: packaging
`parcel-data-recovery.skill` via `tools\package_skills.py`). Logged as
[reference_desktop_commander_nested_quote_mangling.md](reference_desktop_commander_nested_quote_mangling.md) —
confirmed once (not twice, unlike the $var note), cross-linked from
[reference_desktop_commander_powershell_variable_stripping.md](reference_desktop_commander_powershell_variable_stripping.md)
as a related-but-distinct quoting-layer symptom, indexed in MEMORY.md. Workaround: write the command to a
`.bat` file and execute that instead of nesting quotes inline (worked cleanly once).

## 2026-07-12 Cowork workflow-notes follow-up round 2 (standing fixes, not reactive)

Gabriel asked for the three follow-up workflow notes from round 1 to be actually fixed, not just logged.

- **Notion↔target-markets.json parity — extended the EXISTING standing check, didn't build a parallel one.**
  Before acting, checked `list_scheduled_tasks` and found `ora-skill-text-audit` already runs monthly
  (day 15) with a class (j) "target-market parity" check — it already covers the Acquisition Pipeline
  Tracker's Market select (bcfe4a03). Its blind spot: the Owner Outreach Queue's Metro select (caa809b7)
  was never in its `consumers` scope, which is exactly why Cincinnati/Kansas City drifted silently for
  weeks. Fetched bcfe4a03 live and also found a real (legitimate, not a bug) divergence — a "Cleveland
  OH" option not in the canonical 9-cluster list, used once by a correctly-PASSED Twinsburg OH deal
  outside the buy-box footprint; confirmed via SQL query before concluding it wasn't a parity defect.
  Fixes shipped: `target-markets.json` bumped to v1.1 (repo `C:\Users\Owner\ora-skills\target-markets.json`,
  commit c46360a, + OneDrive mirror kept in sync) adding the Owner Outreach Queue select as a tracked
  consumer; `ora-skill-text-audit` updated via `update_scheduled_task` (v1.5) to check caa809b7 with an
  explicit alias map (this DB uses short labels — "Baltimore-MD" not "Maryland (Baltimore/DC)", etc.) and
  treat a missing alias as 🟠 HIGH, same severity as the Pipeline gap. Verified via `list_scheduled_tasks`
  post-update.
- **DC PowerShell $var bug — scope-checked, not re-asserted.** Could not run a live cross-surface repro
  from this Cowork session, but `get_config` showed `currentClient: {"name":"claude-code","version":
  "2.1.205"}` plus one shared `clientId`/`version`/cumulative `usageStats` (9,720 calls / 179 sessions) —
  consistent with ONE Desktop Commander server/config shared across Code and Cowork on this machine, not
  two independently-configured hosts. Updated
  [reference_desktop_commander_powershell_variable_stripping.md](reference_desktop_commander_powershell_variable_stripping.md)
  to reflect "likely engine-wide, not Extension-scoped" as evidence-based inference, explicitly flagged as
  NOT an independently-confirmed cross-surface test. Also hit a live example of the same quoting-fragility
  family mid-session: a nested-double-quote `cmd.exe /c "... python ... \"path\" ..."` call silently
  mis-parsed (leading space injected into a path arg) — worked around by writing the command to a `.bat`
  file and executing that instead of inlining. Not yet written up as its own reference note; flagging here
  in case it recurs enough to warrant one.
- **parcel-data-recovery Iron rule 10 — shipped and packaged, not just decided.** Added the standing
  calibration methodology (comp-sample-derived county ratio, never a blind statutory/cross-county
  carry-over; DATA-GAP-with-named-row-count as the explicit non-answer if a pass can't complete the comp
  pull) to the repo SKILL.md (`C:\Users\Owner\ora-skills\parcel-data-recovery`, v1.4, commit 57b380c).
  Packaged via the sanctioned `tools\package_skills.py` (2 entries OK, description 755/1024 chars) and
  staged the `.skill` for Gabriel's Save-skill install — registration itself is still his click, per
  `package-and-stage-skill` doctrine.

## 2026-07-12 Session-board cleanup COMPLETED — full sweep + 14-session floor

Completes the earlier same-day entry ("Session-board cleanup: aaos sweep + durable
session-retention fixes"), which logged the durable fixes and the first sweeps but predated
the full interactive-tail archival below.

Full scope: ~67 CCD sessions archived across five passes (all reopenable from Archived):
- 11 stale autonomous run-sessions + merged-PR straggler "Agentic OS architecture" (PR #10)
- 19 aaos run-sessions (15 ora-aaos-expire-leases + 4 ora-aaos-publish-contracts) + merged-PR
  straggler "WORKBOOK_PATH dual-library mismatch" (PR #184)
- 6 older guard-run duplicates (ora-task-integrity-guard / ora-health-guard / ora-pm-ledger
  older instances, in two passes; kept the newest of each)
- 28 idle interactive/work sessions (the tail: Claude tools review, status.json fixes, the
  LAMS cron-collision sessions, CLAUDE.md trim, Phase 5 handoff, Command center live view, etc.)
- 1 superseded ora-aaos-publish-contracts run (keep-newest invariant)

Board reduced from ~50+ to a clean 14-session floor, verified via list_sessions:
- 2 active-PR sessions (Notion Daily Digest #206, Session Hygiene #205) — auto-archive on close
- exactly one newest run per recurring scheduled task (12 tasks)
No worktree WIP was at risk — git-worktrees.json showed a single unleased worktree.

Durable measures (restated from the prior entry for completeness): ora-aaos-expire-leases
cadence 17->6/day (12 6,9,12,15,18,21 * * *); settings.json cleanupPeriodDays 30->14;
"Auto-archive after PR merge or close" enabled in Settings -> Claude Code. Known platform
limit: no headless/autonomous board-archive exists (archive_session is confirmation-gated),
so the steady-state trickle (~6 aaos + a few guard runs/day) still needs periodic manual
re-sweeps; cleanupPeriodDays=14 bounds the long tail via deletion.

## 2026-07-12 — CC Daily Brief frozen-dateline fix landed: PR #206 opened (reference-date-decouple + 2 adversarial-review-found fixes)

Traced from a pasted Notion digest coverage-gap note about Section F's frozen "As of 2026-06-01" dateline. Root cause: `WORKBOOK_AS_OF` (server/config.ts) was a single hardcoded constant doing double duty as the workbook data-month selector AND the day-count/brief-dateline reference — the 2026-07-09 fix (PR #198) only fixed the email subject line, not the body header or any day-count math (lease monthsToExpiry, Monthly Checklist monthCol selection).

Investigation found a separate, already-in-flight fix: a Gabriel-directed Opus 4.8 session had built branch `fix/reference-date-decouple` (4 commits, TDD'd, adversarially reviewed, worktree `C:\Users\Owner\cc-wt-refdate-decouple`) implementing the correct architecture — `WORKBOOK_AS_OF` scoped to data-month/label selection only; new `referenceDate()` drives all day-count math + the brief's "As of" line, which now reads "As of {run date} · data month {Mon YYYY}" (staleness made explicit, not hidden). The same session had also left a partial, differently-designed, uncommitted hand-application attempt on the shared `oxford-command-center` main checkout (stashed, not discarded — `stash@{0}` "partial hand-applied refdate-decouple reapplication") that predated the finished branch design; single-writer collision handled by identifying ownership via commit authorship before touching anything.

Reconciled: merged main's one divergent commit (test-infra only, zero overlap) into the branch, ported the one genuinely-missing fix from the stash (insurance-capture call still keyed on frozen date — its occupancy/debt-snapshot siblings had already been fixed), then ran two Fable-tier adversarial review passes:

- **Pass 1** found 5 residuals (F1–F5) of the same defect class the branch's "portfolio-wide" claim said it had closed. Fixed the two material ones (Gabriel's call, in-turn):
  - **F2**: balloon-due insight severity used the live date but impactAnnualUsd/detail month-count still preferred the frozen `monthsToMaturity` workbook column — up to ~9x overstated dollar impact feeding insight sort order and the brief's "Top exposure" line.
  - **F3**: a policy lapsed between the workbook date and run date could produce *no alert anywhere* (status-based lapsed branch needs the workbook's own status column to already say Expired/Cancelled). Added a live-date-driven critical branch.
- **Pass 2** (post-fix) verdict: SAFE-WITH-CAVEATS, no blocking defects.

Flagged, not fixed (out of scope for this PR, Gabriel-acknowledged as follow-ups): F1 (Renewals kanban still frozen, `src/brain/renewals.ts`, branch never touched it), two more instances of the frozen-`monthsToMaturity` pattern in AI display contexts (`server/ai/respond.ts`, `src/brain/draft.ts`).

`npm run gate` + `npm run gate:ci` both green (225/225 test files, real build, bundle budget) with correctly-captured exit codes — first `gate` run was accidentally tee-masked (reported false success while a pre-existing flaky `capital-allocation-api` hook-timeout had actually failed the chain; caught and rerun properly, see [[feedback_npm_test_intermittent_access_violation]] for the same flake class).

PR: https://github.com/ZeOoba/oxford-command-center/pull/206 (branch `fix/reference-date-decouple`, 9 commits ahead of `ad1aca1`). Not yet merged — merge is Gabriel's call per this repo's standing convention (PR #192/#196/#198/#202 precedent).

## 2026-07-12 Session-board cleanup: aaos sweep + durable session-retention fixes

The CCD session board had filled with autonomous scheduled-task run-sessions
(ora-aaos-expire-leases spawns a session on each hourly fire → ~17/day) plus merged-PR
stragglers that predated the auto-archive toggle.

SWEEP (this session, all reopenable from Archived):
- Archived 11 stale autonomous + 1 merged-PR straggler (Agentic OS, PR #10) in a first pass.
- Then archived 20 more: 15 ora-aaos-expire-leases + 4 ora-aaos-publish-contracts idle runs
  (kept the newest of each as a reference) + 1 merged-PR straggler (WORKBOOK_PATH
  dual-library mismatch, PR #184).
- "Auto-archive after PR merge or close" enabled by Gabriel in Settings → Claude Code, so
  future PR-linked sessions self-retire (event-driven; does NOT retroactively sweep sessions
  whose PRs merged before the toggle — those were cleared manually above).

DURABLE FIX (Gabriel-approved "both"):
1. Reduced ora-aaos-expire-leases cadence: 12 6-22 * * * (hourly, 17/day) → 12 6,9,12,15,18,21
   * * * (6/day, every 3h, 6am-9pm) via supervised update_scheduled_task (CC/MCP fleet).
   Tradeoff accepted: a stale AAOS seam lock now reclaims up to ~3h later instead of ~1h.
   Verified via list_scheduled_tasks; next fire 2026-07-12 15:12 ET.
2. settings.json cleanupPeriodDays 30 → 14 (old session files auto-DELETE after 14 days).
   Verified valid JSON.

FINDING (durable, for future reference): there is NO fully-autonomous way to keep the CCD
session BOARD clean — archive_session is confirmation-gated (cannot run headless) and there is
no built-in auto-archive for scheduled-task sessions; cleanupPeriodDays only DELETES old files
and does not touch same-day runs. The only lever for recurring daily clutter is reducing the
source task's cadence (done here) or accepting periodic manual sweeps. PR-linked sessions are
the sole category with a built-in auto-archive.

## 2026-07-12 — Orphaned-task-forensics pass on 3 flagged automation anomalies: 1 explained-historical, 2 confirmed self-resolved, 1 undocumented flake logged

Investigated three items surfaced by an automation-health-monitor-style sweep, per orphaned-task-forensics doctrine (root-cause before action, no silent re-registration):

- **`ora-owner-outreach-queue-refresh` (LAMS) 17:16Z fail-loud / 17:24Z self-correct:** SKILL.md STEP 1 GUARD fails loud (no fabricated queue/numbers) when the driver detects the Investment Candidates master file is STALE. Consistent with a transient OneDrive-sync-timing false read (same class as the `ora-task-integrity-guard` stale-baseline bug fixed 2026-07-09), not a data-integrity issue — guard fails safe by design. No prior event_log entry existed for this specific trip; logged here for pattern-tracking. No code change made — watch for recurrence before treating as a real bug.
- **`ora-calibration-snapshot` (CC/MCP) "silent-never-fired since 07-01":** Confirmed via live `list_scheduled_tasks` — task is enabled, well-formed, cron `0 8 1 1,4,7,10 *`, has no `lastRunAt` (never fired even once). Root cause: the task was only *registered* 2026-07-11 (per the existing 2026-07-11 "dark tasks" entry above) — 10 days after the 2026-07-01 quarterly slot had already passed. It didn't miss a fire; it didn't exist in the registry yet. `nextRunAt` correctly shows 2026-10-01. Per the Phase-2 caveat (zeroed report is normal until ≥1 horizon elapses), a manual backfill of the missed Jul-1 snapshot has low value — left as Gabriel's optional call, not actioned.
- **`ora-doctrine-integrity-guard` / `ora-aaos-expire-leases` (CC/MCP) borderline-overdue (45min/26min):** Both confirmed fired since the flag (`lastRunAt` today, `nextRunAt` advanced correctly) — jitter-window artifacts, not failures. "Low severity / self-resolving" characterization confirmed correct, not just optimistic.

No re-registration, disable, or code change performed — all three were diagnosis-only per this skill's boundaries.

## 2026-07-12 (cont.) — Correction: dropped "never name an active confidential deal in this file" as standing per-file phrasing (Gabriel's call)

Follow-up to the same-day Obsidian fix + rules.md §7b amendment above. Gabriel
pushed back on the generalized phrasing I'd introduced: he wants stale
belt-and-suspenders deal-name references simply deleted at declassification,
not replaced with a standing "never name an active confidential deal in this
file" rule baked into each ported copy. Reasoning: that's Hard Invariant 3's
job at the roster level (`session-context.md` / `confidential-terms.json`),
not something to duplicate and maintain per-file.

Reverted:
- `Obsidian BrainVault/CLAUDE.md` — removed the "## ⚠️ Confidentiality rule"
  section entirely (no active confidential deal currently applies); no
  generalized replacement text added.
- `rules.md` §7b — checklist line item for CLAUDE.md/ported copies kept, but
  now says "remove outright," with an explicit note not to reintroduce the
  "never name an active confidential deal in this file" pattern.

Still open: `~/.claude/CLAUDE.md`'s own Invariant 3 (uncommitted, concurrent
session's "CLAUDE.md trim," not yet landed as PR #12) currently uses that same
generalized phrasing. Not touched here (single-writer — not my edit to make),
but flagging so whoever lands PR #12 sees this preference before merging.

## 2026-07-12 (cont. 5) — automation-health-monitor retime BLOCKED: LAMS registry unreachable from this Code/CC session

Attempted the handoff from the prior recon entry ("Last LAMS collision recon: automation-health-monitor is mis-registered, not just colliding"): retime `automation-health-monitor` `30 6 * * 1-5` → `5 11 * * 1-5` via `update_scheduled_task`, per the register-scheduled-task skill's supervised MCP path.

Step 1 (mandatory re-verify against live state before acting): called `list_scheduled_tasks` from this Code/CC session. The tool works and returned 20 live entries, all CC/MCP-fleet (paths under `C:\Users\Owner\.claude\scheduled-tasks\...`) — but `automation-health-monitor` is NOT among them, consistent with the live fleet roster placing it on LAMS/Cowork only. This independently reproduces the limitation the prior recon entry already flagged ("needs a Cowork session, LAMS registry not reachable from CC\MCP") rather than assuming it still held.

Per register-scheduled-task Rule 1 ("if the MCP tool is unavailable in the current session ... STOP and tell Gabriel to run the registration from a supervised session — do not improvise a filesystem path"): no update was applied, no JSON splice attempted.

Concurrent-writer check: `list_sessions` showed no other active session working this task id.

**Open action for Gabriel, unchanged:** apply the `automation-health-monitor` retime (`30 6 * * 1-5` → `5 11 * * 1-5`) from a supervised Cowork/LAMS session via `update_scheduled_task`. This is the 2nd session in a row to hit this exact cross-surface wall — if a 3rd recurrence happens, worth encoding directly in the register-scheduled-task skill or session-context.md that Code/CC sessions cannot reach the LAMS registry's `update_scheduled_task` at all (list/edit is CC/MCP-fleet-scoped only), so LAMS-fleet retimes should route straight to Cowork instead of being handed to a Code session first.

## 2026-07-12 (cont.) Last LAMS collision recon: automation-health-monitor is mis-registered, not just colliding

Follow-up closing out the final of the original 4 (then corrected to 4-of-4-still-real) LAMS cron
collisions: `ora-passed-deal-tracker` (day-15, 06:30 AM) x `automation-health-monitor` (weekdays,
06:30 AM).

Read `automation-health-monitor`'s own SKILL.md at
`OneDrive...\Documents\Claude\Scheduled\automation-health-monitor\SKILL.md`. Its frontmatter
description states "weekdays 11:00 AM" (v1.6, 2026-07-08) -- but the LIVE REGISTERED cron (per
fleet-status.py, the live registry, not SKILL.md prose) is `30 6 * * 1-5` (06:30 AM). This is not
just a collision, it's a real design/registration mismatch: the task's whole Step 0.5 logic
computes each OTHER task's expected-fire window and lateness, which only works if it runs AFTER
the 05:00-09:30 AM pileup (23 tasks) has had a chance to fire. Running at 06:30 means most of the
AM-pileup tasks haven't fired yet when this check runs -- its own "MISSED"/"OUT-OF-WINDOW"
classifications for those tasks are likely unreliable at the current registered time.

This also explains why an earlier same-day recon session concluded this pair "already resolved
itself" (assumed the documented 11:00 AM applied) -- that assumption was wrong for the same reason:
it didn't verify the LIVE registered cron distinctly from the SKILL.md's stated intent.

**Recommended fix (read-only recon; NOT applied -- needs a Cowork session, LAMS registry not
reachable from CC/MCP):** retime `automation-health-monitor` from `30 6 * * 1-5` to `5 11 * * 1-5`
(11:05 AM weekdays) -- close to its own documented "11:00 AM" while avoiding a new monthly
collision with `ora-entry-market-scan` (cc fleet, `0 11 1-7 * 2`, exact 11:00 on first-week
Tuesdays). Checked against the full current schedule on both fleets: 11:05 doesn't collide with
anything (nearest neighbors are `ora-command-center-mirror-drift-check` weekdays 10:40 and
`ora-ar-export-freshness-nudge` days 1/15 at 11:30 -- both 25 min clear). This simultaneously
resolves the collision AND fixes the task to actually run after the AM pileup as its own design
requires -- better than a minimal offset.

**Open action for Gabriel:** apply via Cowork `update_scheduled_task` (register-scheduled-task
supervised path). Nothing changed yet.

## 2026-07-12 (cont. 4) — register-scheduled-task v2.4 shipped; near-miss caught mid-commit (single-writer discipline)

Shipped the v2.4 fix recommended in the prior entry: `ora-skills/register-scheduled-task/SKILL.md` concurrent-writer check promoted from a `registry-membership.log` timestamp heuristic to a direct `session_info list_sessions` scan for a live sibling session (log has no visibility into cron-only edits — exactly the class of collision that prompted this). Committed `64e92de`, pushed to `origin/main` clean.

**Near-miss while landing it:** the first commit attempt (`git add register-scheduled-task/SKILL.md; git commit -m ...`) swept up two unrelated files — `parcel-data-recovery/SKILL.md` and `parcel-data-recovery/references/endpoints.md` — that a concurrent session had staged (not just modified) between this session's `git status` check and the `git commit` call, despite `git add` only naming the one intended file. `git commit` without `-a`/pathspec commits everything in the index, and the index had been touched by someone else in the gap. Caught via `git show --stat -1` before push (112 insertions / 24 deletions was far more than the 14/3 the diff had shown), not by inspection at commit time. Corrected with `git reset --soft HEAD~1` (uncommit, keep index) → `git reset HEAD -- <the two parcel-data-recovery files>` (unstage only those, restoring them to exactly their pre-commit modified-not-staged state) → re-commit with only the intended file → verified via `git show --stat` and `git status` before push. Nothing of the other session's work was lost, altered, or pushed under this commit.

**Read-across:** this is a live instance of the exact class of risk the v2.4 fix targets, in the adjacent shared surface (`ora-skills` git index) rather than `event_log.md`. Worth widening the v2.4 `list_sessions` pre-write check (or a parallel doctrine note) to cover git commits in shared repos, not just scheduled-task registry writes — `git commit` should be treated as touching shared state requiring the same live-sibling check, and `git status`/`git diff --stat` immediately before commit is not sufficient on its own since the index can change in the gap before the commit call executes. Not yet fixed in doctrine; flagging as a follow-up rather than fixing unprompted mid-task.

**Open item for Gabriel:** v2.4 is live in the repo but the Cowork skill cache still runs v2.2 until `package-and-stage-skill` + a Save-skill click land it — did not run that unprompted.

## 2026-07-12 (cont. 3) — LAMS scheduler collision fix: root-caused the event_log lock — two concurrent Cowork sessions, not a real incident

Investigated the WinError 5 lock flagged in both of the immediately preceding entries. Root cause: two independent Cowork sessions ("LAMS/Cowork scheduler collision fixes", session `local_7165b738-...`, and this session) were executing the identical handoff concurrently — same 3 task IDs, same target crons. Confirmed via `session_info` `list_sessions`/`read_transcript`, not inference: the sibling session's transcript shows it ran `list_scheduled_tasks`, found all 3 crons already at target (this session's update having landed moments earlier), and re-pinned them idempotently — correct behavior per doctrine (trust observation over memory), not drift or a stale-note error.

**No harm done:** no duplicate task IDs registered (unlike the 2026-06-09/07-08 precedents — both sessions targeted existing IDs with identical values), no data loss (`event_log.md.pending\` drained cleanly, both entries now present, newest-first, intact), fleet state is correct and idempotent. Net cost: two redundant journal entries for one action (this entry's two immediate predecessors) and the file-lock symptom itself.

**Doctrine gap:** register-scheduled-task v2.2's concurrent-writer check relies on `registry-membership.log`, which — as the sibling session itself noted — tracks task adds/drops, not cron edits, so it would never have caught this class of collision. Neither session checked for a live sibling via `session_info list_sessions` before starting, which would have caught it directly (the sibling showed as a distinct non-idle session with a matching title). Filed as a v2.3 fix to the repo skill source (`ora-skills/register-scheduled-task/SKILL.md`): concurrent-writer check now calls `list_sessions` and treats another non-idle session with an overlapping task/title as a hard stop-and-confirm, not just a log-timestamp heuristic.

**Follow-up owed:** repo skill edited this session; live Cowork skill cache still needs `package-and-stage-skill` + a Save-skill click to pick up v2.3 (per its own doctrine — registration is Gabriel's click, not automatable here).

## 2026-07-12 (cont.) ora-cc-schematic-refresh registered + validated via manual dry-run; corrects an earlier "resolved" collision finding

Registered a new daily CC/MCP task, `ora-cc-schematic-refresh` (cron `10 13 * * *`, ~13:18 ET after
jitter), that keeps the "Claude Code — System Schematic" artifact
(claude.ai/code/artifact/4ad3530d-f84f-4def-a472-d16ef107e74c) current — re-runs fleet-status.py,
governor-drift-probe.py, doctrine-integrity-probe.py, memory-integrity-probe.py, the
confidentiality-guard test suite, and git status on oxford-command-center/ora-pm, then republishes
the same artifact URL with targeted edits (never a full regenerate). Read-only diagnostics + one
file edit + one republish; no email. Durable HTML source moved to `~/.claude/artifacts/` (already
gitignored). Registered via the supervised `create_scheduled_task` MCP path per register-scheduled-
task v2.2/2.3 doctrine, verified via a fresh `list_scheduled_tasks` call.

Validated by hand-running the task's exact procedure once (no MCP tool exists to remote-trigger a
scheduled task early — only a UI "Run now" button does that). Findings from the dry run:

- **3 of 4 remaining LAMS cron collisions are now fixed**: `ora-skill-text-audit` (9:45 AM),
  `ora-bearmode-refresh` (06:25 AM), `ora-replacement-cost-refresh` (06:10 AM) — all confirmed live
  in the registry via fleet-status.py, matching the handoff prompt given to Gabriel this morning.
- **Correction**: this morning's LAMS-collision recon session concluded the
  `ora-passed-deal-tracker` / `automation-health-monitor` pair had "already resolved itself"
  (claiming automation-health-monitor drifted to weekdays 11:00 AM per its SKILL.md prose). That
  was WRONG — fleet-status.py's live registry read shows automation-health-monitor still at
  `30 6 * * 1-5` (06:30 weekdays), so this pair still collides with `ora-passed-deal-tracker`
  (day-15, 06:30 AM). The earlier finding likely read stale SKILL.md description text instead of
  the actual registered cron. Needs the same Cowork retime treatment as the other 3 — not yet done.
- **CLAUDE.md/session-context.md trim (task_74012e37) is essentially complete**: doctrine warnings
  dropped 24->8. Both oversized session-context bullets (394w/355w) and all 10 aging tombstones are
  fully consolidated into event_log.md. CLAUDE.md is down to 1743 words (was 1806) — improved, but
  still 43 words above the 1700 warn line (107 words of headroom before the 1850 hard fail).
- **oxford-command-center's date-math bug-fix WIP (8 uncommitted files this morning) is gone from
  the working tree with no corresponding new commit** — checked `git stash list` to rule out data
  loss before reporting: it landed safely via a proper merge (`fix/reference-date-decouple`); the
  leftover hand-applied stash entry is explicitly marked superseded. Not lost work.
- confidentiality-guard test suite grew 115->120 (5 more derived variants), still all green via its
  synthetic-terms-file fallback during the no-active-deal window.

## 2026-07-12 (cont.) — E. Fulton ported-copy staleness fixed (Obsidian) + §7b checklist amended; Cowork Settings still pending Gabriel

Follow-up to the same-day post-legal-hold consolidation abort (task
`efulton-post-legalhold-consolidation` — deal not closed, PSA terminated
2026-07-09, now in note-purchase/short-sale discussion). While investigating
why the deal was still named in standing instructions 3 days post-declassification,
found the 2026-07-09 declassification (rules.md §7b) never covered CLAUDE.md or
its ported copies. Two of three surfaces fixed this session:

- **`~/.claude/CLAUDE.md`** — NOT touched. Confirmed via `git status`/`git log`
  it is mid-edit by a concurrent session (uncommitted `M CLAUDE.md`, unrelated
  to this fix, referenced same-day above as "CLAUDE.md trim" pending as PR #12).
  Single-writer doctrine (rules.md, shared-checkout section) — isolated, did not
  edit. Its current uncommitted working-tree text already generalizes Invariant 3
  ("never name an active confidential deal in this file") rather than naming
  Fulton, which is the right direction, but it isn't landed yet.
- **`Obsidian BrainVault/CLAUDE.md`** (line 45) — FIXED. Replaced the
  Fulton-specific confidentiality line with the same generalized "never name an
  active confidential deal in this file" pattern, pointing at the roster
  (`session-context.md` / `hooks/confidential-terms.json`).
- **Cowork Settings user-preferences text** — NOT fixed; not file-backed, no
  path found under `C:\Users\Owner` or `AppData\Roaming\Claude` for the literal
  "Belt-and-suspenders: E. Fulton Street Portfolio is confidential" line despite
  a broad search. Requires a manual re-paste by Gabriel once the CLAUDE.md trim
  (PR #12) lands.
- **`rules.md` §7b** — amended to add a checklist line item for CLAUDE.md
  (master + every ported copy) so this class of miss doesn't recur.

**Open action for Gabriel:** once PR #12 merges, re-paste the corrected
Invariant 3 language into Cowork Settings.

## 2026-07-12 (cont.) — LAMS-side scheduler collision fix: applied (Cowork session)

Applied the 3 real retimes recon'd and blocked in the same-day "LAMS-side scheduler collision fix: recon complete, execution blocked" entry above. Ran from a supervised Cowork session via `update_scheduled_task` on the LAMS/Cowork fleet only (register-scheduled-task v2.2 Rule 1 — MCP-only, correct-fleet surface; no JSON-splice).

- `ora-skill-text-audit`: `0 10 15 * *` -> `45 9 15 * *` (10:00 AM -> 9:45 AM ET, day-15 monthly schedule unchanged). No longer collides with `ora-owner-outreach-queue-refresh` (Mon 10:00 AM).
- `ora-bearmode-refresh`: `15 6 9 3,6,9,12 *` -> `25 6 9 3,6,9,12 *` (06:15 -> 06:25 AM ET, quarterly day-9 Mar/Jun/Sep/Dec unchanged). No longer collides with `ora-om-intake-ocr` (Wed 06:15 AM).
- `ora-replacement-cost-refresh`: `0 6 9 3,6,9,12 *` -> `10 6 9 3,6,9,12 *` (06:00 -> 06:10 AM ET, quarterly day-9 unchanged). No longer collides with `ora-am-brief` (daily 06:00 AM). Stays ahead of `ora-bearmode-refresh`'s new 06:25 slot, preserving same-day quarterly bundling.
- `ora-passed-deal-tracker` / `automation-health-monitor`: confirmed untouched per recon (no longer colliding — schedules already diverged).

Verified via `list_scheduled_tasks` post-update: all three show the new cron, `enabled: true`. Next fires (ET): `ora-skill-text-audit` 2026-07-15 ~9:48 AM; `ora-bearmode-refresh` 2026-09-09 ~6:30 AM; `ora-replacement-cost-refresh` 2026-09-09 ~6:13 AM (times include the scheduler's standard dispatch jitter).

All 7 of 7 cross-fleet collisions from the 2026-07-11 B2 scheduler-load-balancer proposal are now resolved (3 CC-side applied same day, these 3 LAMS-side applied here, 1 pair required no action).

## 2026-07-12 (cont. 2) — LAMS scheduler collision fix: 3 retimes confirmed at target, no drift applied

Executed from a supervised Cowork session per the prior entry's handoff (register-scheduled-task v2.2,
MCP-only). Before writing, ran the mandated concurrent-writer check: pulled live `list_scheduled_tasks`
first rather than trusting the recon note.

**Finding:** all 3 target LAMS crons were ALREADY at the recommended values — ora-skill-text-audit
`45 9 15 * *` (9:45 AM), ora-bearmode-refresh `25 6 9 3,6,9,12 *` (06:25 AM), ora-replacement-cost-refresh
`10 6 9 3,6,9,12 *` (06:10 AM) — contradicting the prior entry's "none of the above were applied" note.
No record of who/when applied them (registry-membership.log has no 2026-07-12 entry; that log tracks
task adds/drops, not cron edits, so it would not have shown this anyway). Treated the live registry as
ground truth per doctrine (trust observation over memory) rather than re-deriving from the stale note.

**Action:** called `update_scheduled_task` on all 3 with their already-current cron values (explicit
idempotent confirm/pin, not a blind skip) so the change is attributable to a supervised call rather than
an unexplained prior state. Re-verified via `list_scheduled_tasks`: all 3 unchanged at target, confirmed
`ora-passed-deal-tracker` (06:30 day-15) and `automation-health-monitor` untouched per instruction —
that pair remains non-colliding as previously found.

**Net effect:** functionally a no-op (already correct); closes the open action item from the prior entry.
All 7 of the original 2026-07-11 B2 collision pairs are now resolved (3 CC-side same-day + these 3 LAMS-side
+ 1 pair found already-diverged, no action needed).

**Flagged, not fixed (out of scope for this handoff):** `automation-health-monitor`'s own description text
still says "weekdays 11:00 AM" but its live cron (`30 6 * * 1-5`) fires ~06:30 AM ET — a stale-description
drift on that task's own SKILL.md, unrelated to the collision fix. Worth a follow-up pass.

## 2026-07-12 Monthly Memory Consolidation (ora-consolidate-memory-monthly)

Scheduled autonomous run. Scope check against `memory-policy.md`/task file confirmed the corrected no-`--1-`-suffix path is still canonical (resolves on disk, matches MEMORY.md's 2026-07-08/07-09/07-10 notes) — no scope regression.

- **tech.md**: archived the detailed `composio-ora` config/gotchas subsection (auth headers, working-config backup path, Windows `&`-in-URL bug) to `_archive/reference_composio_ora_config_historical_2026-07-12.md` — Composio was REMOVED 2026-06-11 and CLAUDE.md says never reference it; the live-looking config block was stale bulk, not an "active" mis-claim, but worth clearing per the connector-drift check below. Replaced with a one-line pointer.
- **tech.md §3**: added a dated drift-check note next to the stale 2026-06-11 "15 CC + 4 LAMS" snapshot — live LAMS registry (`list_scheduled_tasks`, this Cowork session) = 20 entries (19 enabled + 1 disabled/one-time-fired). Large delta from 4 is organic growth (new tasks registered through July), not drift; flagged as a one-time step-change per the task's own guidance. CC-side count unverifiable from this surface.
- **Retired-connector sweep**: grepped all topic files (excluding event_log.md, which is historical narrative by design) for Rube/Composio/Zapier/Gmail. No file claims any of the four as currently active — `rules.md`, `tech.md` §4, and `00_system_of_record.md` all correctly frame them as retired/removed/never-use. `project_claude-setup-audit-2026-07-09.md` already flags (as an open item, not new) that a 2026-07-08 plugin-bundle reintroduced doctrine-retired Guru + 6 unused connectors on the Cowork side — pre-existing finding, left as-is.
- **OXFORDRA_REPO check**: `C:\Users\Owner\website-canonical` and its `.git` both resolve on disk — confirmed, no memory change needed.
- **Doctrine/governor audit line:** `doctrine-status.json` last_check 2026-07-12T12:52:34 (source: pre-push) — doctrine probe clean, exit 0, 8 warnings; governor probe did not run this cycle (exit_code/summary both null, no data to audit). Grepped `event_log.md` for `"Pre-push proceeded DESPITE doctrine drift"` — zero matches in the file (none in the past month or ever recorded). **No overrides found.**
- **MEMORY.md**: added this entry's pointer-level trailer note; no broken links found, index still under 200 lines.
- No duplicate topic files found needing a merge this cycle; no stale project files identified for retirement (most recent projects are all still open/dated within the last 5 weeks).

Evidence: `list_scheduled_tasks` output (20 LAMS entries), `doctrine-status.json` read, event_log.md self-grep (0 matches), `Test-Path` on website-canonical + `.git` (both True).

## 2026-07-12 eos-plan-gate override audit trail (PR #12) + ora-pm branch hygiene + worktree-push gap found

Follow-up to the same-day "stale/gated systems" audit. Two items actioned:

- **ora-pm**: switched off the fully-merged `recovery/2026-07-05-object-db-loss` branch back to
  `main` (verified byte-identical content via `git diff 8418c44 ca749b9 --stat` first, not just
  commit-graph shape), then fast-forwarded local main 5183d69->8418c44 (9 files, PR #3 content).

- **eos-plan-gate.py / eos-telemetry.py**: the override sentinel was a bare 0-byte `touch` with no
  audit trail (74/187 sessions used it with no accompanying plan doc, per the same-day audit).
  Fixed in an isolated worktree (`~/.claude/.claude/worktrees/eos-plan-gate-audit-trail`, branch
  `eos-plan-gate-audit-trail`, off local HEAD `1d3cf27`): denial message now asks for a one-line
  reason instead of a bare touch; `eos-telemetry.py` surfaces `override_used`/`override_reason`/
  `override_at` in the existing lane-telemetry record. TDD (tests written first, confirmed failing,
  then implemented green); full `hooks/tests/*.py` suite (9 files) passes, no regressions.
  Pushed and opened as PR #12 (github.com/ZeOoba/ora-claude-config) rather than merged directly,
  since `main`'s working tree had unrelated uncommitted changes in flight from a concurrent session
  at the time (CLAUDE.md trim + a governor-probe file) -- avoided touching the shared checkout.

- **New gap found while landing this**: `git push` from the worktree was blocked by the fail-closed
  `git-prepush-confidential-scan.py` with "confidential-terms.json unreadable". Root cause:
  `hooks/confidential-terms.json` is gitignored (`.gitignore` line 34) so `git worktree add` never
  materializes it in a new worktree -- the guard was behaving correctly (fail-closed on a file it
  genuinely couldn't read), not malfunctioning. Worked around by copying the main checkout's copy
  into the worktree (stays untracked/gitignored, never committed) before retrying the push. This
  will recur for every future `~/.claude` worktree that needs to push -- worth a durable fix
  (a worktree-setup step, or a pre-push hint) rather than repeating the manual copy each time.

## 2026-07-12 (cont.) — LAMS-side scheduler collision fix: recon complete, execution blocked (needs Cowork session)

Attempted to complete the remaining 4 of 7 cross-fleet cron collisions from the 2026-07-11 B2 scheduler-load-balancer proposal (CC-side 3 already applied same day — see entry above). Confirmed directly (not assumed) that this CC/MCP session's `update_scheduled_task`/`list_scheduled_tasks` tools only bind to the CC/MCP registry — none of the 8 task IDs across the 4 pairs appear in `list_scheduled_tasks` output, though all 8 exist as live LAMS tasks under `...\Documents\Claude\Scheduled\`. Per register-scheduled-task v2.2 Rule 1 (MCP-only, correct-fleet surface) and Rule 2 (JSON-splice prohibited), execution requires a supervised Cowork/LAMS session — did not attempt a filesystem workaround.

Did complete the read-only recon (SKILL.md frontmatter, cross-checked against the full known live schedule on both fleets) so the Cowork session can apply directly without re-deriving:

- **ora-skill-text-audit / ora-owner-outreach-queue-refresh** — still colliding (both 10:00 AM). Recommend: `ora-skill-text-audit` 10:00 -> 9:45 AM (monthly day-15 audit has more slack than owner-outreach's Monday consumer workflow; +15 min forward to 10:15 was rejected — it would newly collide with LAMS `ora-stale-pipeline-nudge`, Thursday 10:15 AM).
- **ora-om-intake-ocr / ora-bearmode-refresh** — still colliding (both 06:15 AM). Recommend: `ora-bearmode-refresh` 06:15 -> 06:25 AM (quarterly reports-only trigger task has more slack than the weekly OM-intake gate-screen; no functional dependency found between the two despite being administratively "paired" with `ora-replacement-cost-refresh` same-day — verified by reading both full SKILL.md bodies, no cross-references). +15 min to 06:30 was rejected — collides with LAMS `ora-passed-deal-tracker` (day-15, 06:30 AM).
- **ora-passed-deal-tracker / automation-health-monitor** — NO LONGER COLLIDING. `automation-health-monitor` is now weekdays 11:00 AM per its SKILL.md (v1.6, 2026-07-08) vs `ora-passed-deal-tracker`'s day-15 06:30 AM — schedules diverged since the 2026-07-11 audit. Skip; no action needed. The original B2 finding for this pair is stale.
- **ora-replacement-cost-refresh / ora-am-brief** — still colliding (both 06:00 AM). Recommend: `ora-replacement-cost-refresh` 06:00 -> 06:10 AM (quarterly background table refresh has far more slack than `ora-am-brief`'s daily Block A rate-prefetch, which explicitly must run FIRST each weekday and feeds the Daily Brief Gabriel reads immediately — left untouched). Kept ahead of the `ora-bearmode-refresh` "paired" 06:25 slot above, preserving their same-day quarterly bundling.

**Open action for Gabriel:** none of the above were applied — run this from a Cowork session (its own `update_scheduled_task`) to execute the 3 real retimes above; the 4th pair needs no action.

## 2026-07-12 — Session-context consolidation: integrity-guard + scheduled-task retirement history archived

Companion entry to the same-day fleet-recovery consolidation above. Doctrine-integrity-probe
flagged session-context.md's "Integrity guard" bullet at 355 words (cap 80) plus six aging
(>30-day) tombstone dates. Full retirement history moved here verbatim; session-context.md now
carries only a short current-state pointer to this entry.

**Integrity guard:** CC task `ora-task-integrity-guard` (12:45 daily) is the sole runner —
engines (`guard.ps1` + `membership-guard.ps1`) relocated into its own folder 2026-06-11; the LAMS
twin was retired the same day. Known gap, still unresolved: the guard is itself a CC fleet
member and could not alarm on the 2026-07-05 CC registry loss (self-referential-monitoring gap)
— a cross-fleet or fully-external check is a recommended follow-up, not yet built. External
dead-man: `ora-cowork-heartbeat` (05:50 + 17:50) → Notion page `35c6ecd8` → GitHub
`ZeOoba/ora-cowork-watchdog` (canonical-ID fetch + 16h threshold; re-enabled and patched
2026-06-10).

**Retired roster — consolidated list, check here before any future recovery/rebuild touches the
fleet (do NOT re-register any of these):**
- 8 Tier-2 tasks archived 2026-06-09 to `_archive_2026-06-09_retired/`: lease-expiration-dashboard,
  monthly-close-kickoff, debt-maturity-snapshot, tenant-at-risk-monthly, quarterly-compliance,
  monthly-checklist-formula-audit, pm-ar-export-freshness-check, distress-signal-monitor.
- 4 inbox sweeps: loopnet-autoreply, broker-email-to-notion, hubspot-note-to-interaction-log,
  direct-prospect-inquiry-draft.
- 4 Gabriel-ratified-unneeded 2026-06-11: annual-budget-kickoff, year-end-review,
  lender-covenant-tracker, cash-position-snapshot.
- 3 from the 2026-06-16 strategic-audit kill list: ora-setup-audit, ora-dormant-thread-revival,
  ora-weekly-tooling-intel-sweep.
- `ora-dashboard-refresh` (2026-07-10) — superseded by
  `oxford-command-center\scripts\deploy-mirror.ps1` (native "ORA Command Center - Mirror Deploy"
  Windows task, hourly + 06:45 ET, Access-gate verified; monitored by CC/MCP
  `ora-command-center-mirror-drift-check`); source dir `oxford-perfection\ora-dashboard` was
  archived 2026-07-07. Do NOT repoint or re-enable. Registry entry disabled but not yet deleted
  (self-delete blocked — task was mid-run when retired; run
  `delete_scheduled_task(ora-dashboard-refresh)` from a fresh session to finish removal; a
  `restore-skill-governor.py`-type guard regenerated a stale stub SKILL.md at the original LAMS
  path in the interim — the authentic archived copy is at
  `_archive_2026-07-10_retired\ora-dashboard-refresh\`).
- `ora-treasury-yield-prefetch` (2026-07-11) — permanently retired, moved
  `_archive_2026-06-11_orphans/` → `_archive_2026-07-11_retired/`; superseded by `ora-am-brief`
  Block A (folded in-place 2026-07-11 10:58 ET, same Notion page + Rate History DB). Do NOT
  re-register as a standalone LAMS producer — would double-write the same page.

All of the above were re-resurrected at least once during the 2026-07-05/08 fleet-loss recovery
and re-retired again — if any reappears in a future roster, it's drift, not intent. 35 orphan
folders remain archived to `_archive_2026-06-11_orphans/` (32 on 6/11 plus the 4
Gabriel-ratified-unneeded above, minus `ora-treasury-yield-prefetch` now moved out). The Notion
"ORA Lease Expiration Dashboard" no longer refreshes — am-brief §4b treats it as historical.

**Backup:** `~/.claude` backs up to the PRIVATE `ZeOoba/ora-claude-config` repo (confidential
terms scrubbed from tracked files 2026-06-11 — never commit a deal term).

## 2026-07-12 — Session-context consolidation: 2026-07-05/08 CC/MCP fleet-loss recovery archived

Doctrine-integrity-probe flagged session-context.md's "Fleet recovery CLOSED 2026-07-08" bullet
at 394 words (cap 80) plus several aging (>30-day) tombstone dates. Full incident narrative
moved here verbatim; session-context.md now carries only a short current-state pointer to this
entry.

**Incident:** the 2026-07-05 Desktop app reinstall destroyed the CC/MCP scheduled-task registry
outright — verified gone for 2+ days via direct filesystem sweep before any recovery began, not
a probe-timing artifact. A same-day Cowork rebuild covered only 6 LAMS tasks, leaving ~14
CC-only functions dark for nearly 3 weeks undetected: the one guard built to catch exactly this
(`ora-task-integrity-guard`) was itself a CC fleet member and died with the registry it was
supposed to monitor.

**Recovery:** two concurrent sessions worked it 2026-07-08 — this session on CC/MCP, Gabriel on
Cowork/LAMS. Duplicate-registration and destructive-delete near-misses from that recovery are
already logged separately in this file (2026-07-08 entries).

**Verified-current state (2026-07-11 pass, superseding the original 2026-07-08 snapshot):**
`ora-health-guard` (OneDrive spec recovered, re-enabled 2026-07-09, clean since, lastRun
2026-07-10), `ora-pm-ledger`, and `ora-weekly-hygiene` (re-enabled 2026-07-09, Gabriel-approved)
all `enabled:true` per live `list_scheduled_tasks`. `ora-dashboard-refresh` no longer appears in
the registry at all — its pending `delete_scheduled_task` cleanup is done. LAMS shows 16 enabled,
matching the 2026-07-08 fleet-audit's ratified core-18 exactly (audit file:
`~/.claude/_confidential-staging/2026-07-08_LAMS-fleet-recovery/2026-07-08_LAMS-fleet-audit_v01.md`).

**Residual items, all RESOLVED 2026-07-09:**
- 2 dangling disabled LAMS entries with no live folder (`ora-debt-maturity-snapshot`,
  `ora-weekly-sourcing-digest`) — Gabriel deleted both via the Cowork UI; verified by direct grep
  of the raw LAMS `scheduled-tasks.json` (zero hits).
- `ora-cam-reconciliation-annual` timing DECIDED 2026-07-09 (Gabriel: December-only, not
  year-round) but NOT YET EXECUTED — still needs a Cowork-side `enabled:false` toggle now plus a
  manual re-enable each December before the Jan 15 fire; the CC/MCP-scoped `scheduled-tasks` MCP
  can't reach LAMS tasks to do this remotely.
- `automation-health-monitor` canonicalization — verified (not just claimed): the registered
  version is already v1.6/20KB and substantively contains the orphaned v1.5's ORPHANED-BEACON /
  producer-consumer-beacon / dual-bounded-lateness content, i.e. not a stub. The orphaned
  `ora-automation-health-monitor` duplicate was already archived 2026-07-08 to
  `_archive_2026-07-08_retired\`; this session additionally consolidated stray leftover
  output/archive files into that folder and archived a second, broken redirect-stub copy found
  in the legacy `Claude_Workspace\00_Governance\Scheduled\` tree.
- `ora-operations-extensions:debt-management` skill's stale references to retired tasks —
  fully resolved: fixed 2026-07-08, git-pinned into `ora-skills` v1.2 via PR #7 (merged
  2026-07-09), and the old plugin-hosted duplicate confirmed already gone from Settings →
  Capabilities (Gabriel checked directly — the plugin's live Skills list has 7 entries, no
  `debt-management`; only its static description text is stale, cosmetic only).

Full detail and root-cause writeup: memory `oxford-cc-repo-health.md`.

## 2026-07-12 ora-pm-ledger LAMS twin confirmed already-retired; register-scheduled-task v2.3 (PATH-DISAMBIGUATOR)

Reconciliation of the open 2026-07-09 double-fire durable-fix action ("retire the redundant
LAMS/Cowork ora-pm-ledger registration"). Net: nothing to retire — the LAMS registration was
already gone, and the folder the brief/memory pointed at was an orphan, not a live task.

Verified on both surfaces:
- Cowork (LAMS) `list_scheduled_tasks`: no `ora-pm-ledger` on the LAMS fleet.
- CC-side filesystem check: no `ora-pm-ledger` under the LIVE LAMS store
  `...\Documents\Claude\Scheduled\`. Its three consolidated ancestors (ora-notion-daily-digest /
  ora-outbox-qc-sweep / ora-eod-action-ledger) sit archived under `_archive_2026-06-11_orphans\`.
- CC/MCP fleet: `ora-pm-ledger` present (cron `0 18`, last fired 2026-07-11 18:09 ET) — the SOLE
  live registration. Not touched.

Root cause of the confusion: the brief and the (now-corrected) memory note assumed the LAMS
spec lived at `Claude_Workspace\00_Governance\Scheduled\ora-pm-ledger\`, which is NEITHER fleet's
store root. That on-disk folder is an orphaned/misfiled spec never wired to the scheduler —
flagged for archival. No registry mutation performed (correctly — the target didn't exist).

Doctrine: `register-scheduled-task` bumped v2.2 -> v2.3 adding the PATH-DISAMBIGUATOR rule — a
live registration is proven only by the task appearing in `list_scheduled_tasks` on the target
fleet with its `path` matching that fleet's store root (CC = `~\.claude\scheduled-tasks\{id}\`,
LAMS = `Documents\Claude\Scheduled\{id}\`); a folder outside both roots is an orphan, not a
registration. Memory `reference_ora_pm_ledger_double_fire.md` marked RESOLVED; retirement runbook
repurposed to a RESOLVED disposition (DO NOT RUN). §0.5 de-dupe guard retained as backstop.

## 2026-07-12 oxford-command-center: capital-allocation-api R-1 flaky timeout ROOT-CAUSED + FIXED

Follow-up to the same-day gate-crash entries. The R-1 flakiness flagged during that
investigation ("borderline-slow ~3.8-4s against a 5s timeout") was itself root-caused
via systematic-debugging rather than left as a vague observation.

Reproduced a genuine failure: R-1 timed out at 5008ms on a completely isolated, otherwise-
idle run (not a full-suite-contention artifact -- it failed cold, alone).

Instrumented every phase standalone: imports + openWarehouse (all ~22 migrations) +
seedPropertyMaster together cost ~126ms combined -- not the bottleneck. The actual cost is
the `/allocate` route's dynamic `import('../brain')` (server/warehouse/capital-allocation-api.ts,
inside the request handler): brain.ts transitively pulls in chokidar + workbook parsing +
quickbooks + contracts/index, a real module-load cost. Under vitest's per-file isolation
(`isolate: true`), each test file gets a fresh module registry, so this file's first call
pays that cost fresh, inside the 5s-timed test body. Measured at 1278ms standalone with
zero vitest overhead.

Considered and rejected: converting the route's dynamic import to a static one. No
circular-dependency reason blocks it, but the identical pattern is used in 5 other files
(api.ts x3, insights-api.ts, lease-forecast-api.ts, tax-api.ts) with no documented
rationale requiring dynamic -- changing the import style is a separate, wider decision
than this test's flakiness warrants, and would touch production route-handler code to fix
a test-only problem.

Fix: pay the import cost once in the test file's `beforeAll` (untimed setup) instead of
inside the timed `it('R-1', ...)` body. No production code touched. Verified 4/4 fresh
runs at 585-844ms (was 2200-5008ms including a real timeout). Full `npm run gate` still
green end-to-end.

Committed + pushed: oxford-command-center `ad1aca1`.

## 2026-07-12 oxford-command-center: gate test->reconcile segfault ROOT-CAUSED + FIXED

Follow-up to the same-day entry logging the crash. Root-caused via systematic-debugging
(single-variable hypothesis testing, not guessing):

- Ruled out test content: a fully clean 0-failure run crashed on exit same as a run with
  a real timeout.
- Ruled out "any worker-thread teardown crashes": a single small test file never crashed.
- Ruled out thread-reuse accumulation specifically: singleThread true vs false made no
  difference, both crashed.
- Root cause: `better-sqlite3` (native N-API module) is not safe across Vitest's
  `threads`-pool worker-thread teardown -- Vitest's own documented threads-pool failure
  class, and why Vitest itself changed its default pool away from threads.

Fix: vitest.config.ts `pool: 'threads'` -> `pool: 'forks'` (separate OS processes, no
shared native-handle lifecycle). Verified: full 224-file/2569-test suite runs clean, and
the complete `npm run gate` chain (governance->typecheck->lint->check:dev-css->test->
reconcile->warehouse:verify->warehouse:drift) completes end-to-end with exit 0 -- the
first time all 8 steps have run to completion in this investigation.

The prior code comment claiming `forks` hit a "tinypool spawn fault" on this Node 24 +
Windows box was re-tested directly (full suite, forks pool) and did NOT reproduce --
superseded; likely fixed by a since-updated tinypool/vitest/npm version. If a forks spawn
fault resurfaces, re-verify before reverting to threads -- threads has its own confirmed
segfault risk with this repo's native dependencies.

Also updated `tests/unit/test-isolation.test.ts`'s regression-guard assertion (it pins
the pool choice by design, so it correctly failed once the pool changed -- updated to
assert `forks` instead of `threads`).

Committed + pushed: oxford-command-center `c1d0d56`.

Separately observed, NOT fixed (different issue): `tests/unit/capital-allocation-api.test.ts`'s
R-1 test is borderline-slow (~3.8-4s against a 5s timeout) and occasionally times out under
load -- pre-existing, was previously masked by the segfault always aborting the run before
its flakiness could be cleanly observed. Worth a follow-up if it recurs.

## 2026-07-12 oxford-command-center: npm run gate crashes at test->reconcile handoff (reproducible 2/2)

`npm run gate` (governance && typecheck && lint && check:dev-css && test && reconcile &&
warehouse:verify && warehouse:drift) segfaults immediately after `test` (vitest run)
finishes, before `reconcile` starts -- reproduced twice in a row, identical location both
times (right after `tests/unit/capital-allocation-api.test.ts`'s last test line), same
signature: `.../npm: line 65: NNNN Segmentation fault "$NODE_EXE" "$NPM_CLI_JS" "$@"`.

Not the documented flaky test-runner crash (`feedback_npm_test_intermittent_access_violation.md`,
~30-50% random rate, rerun-and-it-passes) -- this is deterministic at the same chain boundary,
both times, not a coin flip.

Isolated verification (each step run standalone, outside the `&&` chain): governance, typecheck,
lint, check:dev-css, test, reconcile, warehouse:verify, warehouse:drift ALL pass cleanly on
their own. So this is a process-handoff artifact specific to chaining `vitest run` into the next
`tsx` script via `&&` in one long bash line on this machine -- not a content/logic defect in any
gate step itself.

Likely related to the already-documented `dev:server` intermittent-hang issue (package.json
`//devServerNote`, investigated 2026-07-08: tsx watch mode hangs ~2/5 trials on this machine,
root cause undetermined, "likely transient resource contention on a machine that runs many
concurrent node processes"). Both symptoms point at the same underlying class: Windows/WinGet
Node.js process lifecycle instability under this machine's typical concurrent-process load,
not specific to any one script.

Found + logged during a 2026-07-12 workflow-audit follow-up session while verifying the
ratify-hurdle-rate skill's directory-format migration via its own gate step.

## 2026-07-12 CC/MCP scheduler retimes — resolve 3 of 7 cross-fleet cron collisions

Applied via `update_scheduled_task`, CC-side only (no LAMS write needed):
- `ora-monthly-portfolio-briefing`: 07:30 -> 07:45 (was colliding with LAMS `ora-monday-sync` 07:30 Mon, on months where the 1st falls on Monday)
- `ora-weekly-hygiene`: 20:00 -> 20:15 (was colliding with LAMS `ora-session-sweep` 20:00 every Sunday)
- `ora-week-ahead-briefing`: 16:30 -> 16:20 (was colliding with LAMS `ora-friday-closeout` 16:30 every Friday)

Source: 2026-07-11 workflow-audit session's B2 scheduler-load-balancer proposal, applied 2026-07-12 per Gabriel's go-ahead. Remaining 4 flagged collisions (ora-skill-text-audit/ora-owner-outreach-queue-refresh, ora-om-intake-ocr/ora-bearmode-refresh, ora-passed-deal-tracker/automation-health-monitor, ora-replacement-cost-refresh/ora-am-brief) are all LAMS-internal — need a Cowork-side session to resolve, not fixed here.

## 2026-07-11 — 2 of 3 flagged material discrepancies resolved via executed PDFs (false alarms); Promissory Note payment-history traced but still open

Followed up on the 3 flagged material discrepancies from the version-conflicts reconciliation by pulling the actual executed/signed documents (Adobe Sign audit trails) rather than relying on unsigned draft comparisons:

- **Murad Lease B13 Response letter** — the executed Suite B13 lease (signed 8/11/2025) confirms $999/mo Year 1 + 3% annual escalation starting 8/1/2026. The flagged copy (which had the escalation language) was the accurate, later-stage draft — the two previously-archived copies just predated that clause being added. Not a real discrepancy. Archived to `Claude_Workspace\_archive\2026-07-11_version-conflicts-resolved\`.
- **2018 Zettler Road Lease** — the executed lease (signed 2/5/2026) shows $1,695/month, $20,340/year, 3% escalation. Checked the actual rent clause (not just hashes) across all three docx variants — all three match the executed figures exactly. The 3-way hash split was never an economic conflict; whatever differs is elsewhere (formatting/save artifacts). Archived.
- **Promissory Note -- 485 S. Walnut St.** — traced via Outlook email search. Confirmed the loan closed/funded September 26, 2025 (Eric's wire confirmation + Edward Jones confirming arrival that day). No payment ledger, bank statement, or QuickBooks record found showing the actual first interest-payment transaction on either the September 26 or October 26 date — no dedicated ledger exists for this informal family loan (Rich + Lucy Solaski), unlike the firm's tracked external loans. Circumstantial lean toward October 26 (a same-day-as-funding first payment would be unusual) but not proof. **Still open** — remains in `Claude_Workspace\_needs-review\2026-07-11_MATERIAL-discrepancies\`, README updated. Offered Gabriel a QuickBooks SharePoint pull for Oxford Capital Partners LLC (lender entity) or direct confirmation with Rich/Lucy as next steps.

Net: of the original 3 flagged items, only 1 (the Promissory Note) remains genuinely unresolved.

## 2026-07-11 (cont.) — CORRECTION + investigation: Rate Snapshot already manually refreshed 10:32 ET; editor's identity unresolved

Gabriel asked to investigate who made the 10:58 ET `ora-am-brief` edit (open thread from the prior entry). Findings:

- **Correction to the prior entry's "residual gap" claim:** the Notion "Rate Snapshot — Current" page (`35e6ecd8…`) was NOT left stale through the weekend as I previously stated. It shows `prefetch_status: SOURCE_DEGRADED`, `fetched_at: 2026-07-11 10:32 ET` — a manual recovery run already published a fresh (if partially degraded — several secondary sources lagged) snapshot 26 minutes before the SKILL.md edit, and its own Prefetch Errors section states "Remediated 2026-07-11 — Block A restored to the live LAMS task." The gap is fully closed as of today, not pending until Monday.
- **Editor identity: unresolved, not attributable to any session traceable on this machine.** Searched this machine's entire `local-agent-mode-sessions` tree, `claude-code-sessions`, and the Claude app's `logs/` directory for any footprint between 09:00–12:35 ET today — nothing. Every session folder on this machine started at 12:35 ET or later, over an hour after the 10:32 Notion publish and the 10:58 SKILL.md edit. `registry-membership.log`'s last entry remains 2026-07-09 (probe hasn't fired today; next scheduled 12:54 ET).
- Content style (self-narrating "remediated this session," root-cause phrasing matching this log's own conventions) strongly suggests a Claude-driven session did the work, not a raw manual paste — but it did not run as an interactive Cowork session on THIS machine.
- Given `reference_memory_scope_fragmentation.md`'s finding that this canonical OneDrive folder syncs **egoldberg@oxfordra.net**, not Gabriel's own account, leading hypotheses are (a) Eric ran/requested this from his own machine, or (b) it ran via claude.ai web/mobile Cowork rather than this desktop app — either would explain a clean Notion + OneDrive-file result with zero local trace here. Not resolvable from local filesystem evidence alone; flagged to Gabriel to ask Eric directly or check the Notion "Cowork Session Ledger" (`collection://4e3fd821-2b0e-4540-8a6d-888a8a6e4959`) for originating-account/device metadata.
- No action taken beyond investigation — no files touched, no registry calls made this pass.

## 2026-07-11 — Version-conflicts folder reconciled: 19 confirmed duplicates/superseded drafts archived, 3 material discrepancies flagged (not guessed)

Per Gabriel's request, read the actual content of all 22 files across the 9 property groups in `Claude_Workspace\_needs-review\2026-07-11_version-conflicts\` (not just filenames/hashes) and compared each against its canonical filed counterpart.

**19 resolved as confirmed duplicates or clearly-superseded older drafts** — archived to `Claude_Workspace\_archive\2026-07-11_version-conflicts-resolved\`: 1100 Rarig lease addendum (identical to an existing canonical draft); all 4 "Seafire" estoppel copies (3 genuine duplicates + 1 that turned out to be entirely mislabeled — its actual content is the 2203-2207 Northwood/InSite Build estoppel, already correctly filed there under the right name); both 401 Sunburst PSA Second Amendment drafts (older versions predating an intervening amendment the filed copy already reflects, which also has a redline showing the edit); 2 of 3 Murad Lease B13 Response letters + both Murad Suite B13 lease copies (identical to filed); all 3 Hanan New Build Numbers Math variants (same debt-schedule figures as canonical in the range checked); Black Owned Genetics lease (4-byte diff, confirmed trivial); both Monthly Interest Payments EXPLANATION docs (pre-loan-payoff older version; canonical reflects the post-payoff simplified process); Hamilton Ave LOI (1-day date typo only, deal already PARKed); both Real Estate Cash Flow Statement Template copies (only a "Flex" vs "Industrial/Flex" label difference, no figures changed).

**3 flagged as genuine material discrepancies, not resolved** — moved to `Claude_Workspace\_needs-review\2026-07-11_MATERIAL-discrepancies\` with a README explaining each:
- Promissory Note -- 485 S. Walnut St.docx: city of execution differs (Potomac vs Bethesda) and interest-only payment start date differs by a full month (Oct 26 vs Sep 26, 2025) from the filed copy.
- Lease B13 Murad Christopher Baqir Jr LL Response 07.31.2025.docx (the plain-named copy only — 2 sibling copies matched filed exactly and were archived): differs on rent escalation terms ($999/mo flat vs $999/mo + 3% annual escalations) and commencement trigger.
- 2018 Zettler Road Lease (Sepich Portfolio): a genuine 3-way split — three different-content files now exist for what's nominally the same lease addendum (plain-filed, 07-09-INTAKE-filed, and this one) — flagged as a split needing a real read, not a 2-way pick.

Did not guess on any of the 3 — per Hard Invariant 4/general caution on financial/legal terms, these need Gabriel's (or counsel's) actual confirmation before any version is treated as authoritative or archived.

## 2026-07-11 — acquisition-underwriting: 3-way concurrent-session merge (v3.8 + 11 unversioned fixes), repackaged

- **Triple-concurrent-edit collision resolved in one session:** this Cowork session's own v3.7 (QC Gate + market-intel-* deprecation), a parallel Cowork session's v3.6-labeled draft (portfolio LTV governor Stage 2.3, per-property DSCR floor, ENV-WATCH flag, levered-IRR reporting extension, FULL-mode parallel dispatch), and a mid-turn message from a Claude in Excel/Word session (11 fixes from a Waukee IA, 250 NW 10th St IC-memo + underwriting-model audit) all landed on `acquisition-underwriting/SKILL.md` in the same window. Git showed no actual commit conflict (this session's v3.7 was the sole HEAD when the others' content arrived as pasted text/instructions, not commits) — merged by hand into two sequential commits (7d44286 = v3.8 merge, 6b192da = 11-item fold-in, no version label per that session's explicit instruction).
- **Caught mid-merge:** the parallel session's draft carried a stale **~20% portfolio LTV** figure in two places (CAPITAL STRUCTURE CONTEXT, STAGE 2.3) — reverted by the already-ratified 2026-07-09 correction to ~15% (commit a782c4d) before that draft was written. Corrected to ~15% during merge, including recomputing the "headroom to the portfolio governor" arithmetic (20→25 points).
- **11-item fold-in (no version bump, per instruction):** DD-Critical "capped at T2" now explicit as a ceiling (blocks T1 only, never raises a PASS-band score — aligned with existing bear-mode UNKNOWN language); fixed the vacant-deal Quality-max arithmetic (55/62 → 55 always, VA absorbs Tenancy's 7 pts 1:1); added a renovation effective-vintage-shift formula (R% of RCT POINT, three-tier interpolation); UNDERWRITE mode gained 5 model-integrity requirements (formula-derived walk/floor prices, one canonical stabilized-NOI cell, mandatory vacancy sensitization, an LTV-governor check, source/rationale tags for cash-flow-affecting assumptions); IC memo typography codified into explicit font/color mapping + named Word table style; QC Gate gained an intra-memo consistency check; DD-Critical item 5 and the RCT table's Indianapolis/Des Moines footnote now require an *attempted* (not just disclosed) county-millage pull / local RCT validation before FULL mode.
- Repackaged and staged (`package-and-stage-skill`) — needs Gabriel's Save-skill click to close the drift to the installed Cowork runtime copy, same as the earlier v3.7/v3.8 rounds this session.

## 2026-07-11 — Two ora-skills repo fixes: acquisition-underwriting v3.7, communication-intelligence v1.2 (need repackage + reinstall)

- **acquisition-underwriting v3.6→v3.7** (`C:\Users\Owner\ora-skills\acquisition-underwriting\SKILL.md`): (1) added the `data_only=True` QC verification method to the QC Gate bullet — same fix logged to standards.md, now load-bearing in the skill itself, not just memory. (2) Deprecated the phantom `market-intel-[metro]` per-file memory convention (3 refs: Submarket Intelligence Reference header, IC Memo §4, CROSS-SKILL list) — verified no such file exists for ANY of the skill's 8 Submarket Intelligence Reference metros (Columbus/Cincinnati/Indianapolis/Louisville/Des Moines/Grand Rapids/Madison/Delmarva), not just Des Moines as originally flagged. Repointed all 3 refs to the skill's own embedded table + markets.md. No scorecard weights or governors touched.
- **communication-intelligence v1.1→v1.2** (`C:\Users\Owner\ora-skills\communication-intelligence\SKILL.md`): added a new "OM / Broker Package Request" template under Module 3 — proactively request native/text-layer PDF exports from brokers, not Print-to-PDF scans.
- **Both changes are in the git-tracked repo (source of truth per rules.md §1) but NOT yet live in the installed Cowork runtime copy** — same drift pattern as the v1.1 signature-block fix (2026-07-08). Repackage + reinstall via `package-and-stage-skill`, then Gabriel's Save-skill click in Settings → Capabilities, to close the gap.

## 2026-07-11 — markets.md live data pass: 7 established markets sourced, structural cap-rate gap confirmed

- Per Gabriel's instruction to proceed on the flagged staleness gap: researched current vacancy / NNN rent / cap rate for Columbus, Kansas City, Indianapolis, DC Metro/MD, Baltimore, Cincinnati, Madison from CBRE/Colliers/Lee & Associates Q4 2025-Q1 2026 prints. All figures cited inline in markets.md with source + publication date; genuine gaps marked [GAP], unattributed figures marked [SPECULATIVE] and generally not used.
- **Material finding:** none of the 7 markets has a published cap rate series specific to sub-$10M/smaller multi-tenant or flex industrial deals — ORA's actual buy-box. Every cap-rate figure sourced was either a headline institutional print, an unattributed generic range, or simply absent. A "7.5%→7.9%" figure that surfaced identically across 3 of the searches traces to a generic national cap-rate trend chart, not a metro-specific print — flagged in markets.md so it is never mistakenly cited as market-level data.
- **Implication logged to markets.md:** sub-$10M deals should continue to be underwritten off deal-level comps (per standards.md's Exit Cap table, itself sourced from actual ORA models), not off these metro headline series — this pass confirms no better series exists to switch to.
- Also relabeled two stale rows (Wisconsin→Madison WI, Tennessee→Nashville TN) and added Cincinnati/Grand Rapids/Richmond rows for parity with market-monitor skill v1.1's current 9-market roster (Grand Rapids/Richmond left unpopulated — out of scope this pass).

## 2026-07-11 — OneDrive (1) consolidation Buckets 2-4 executed; Bucket 2's orphaned intake folder retired

Continuing from Bucket 1 (23 files, logged earlier today). Gabriel answered 4 batched questions on the remaining buckets; all executed same session:

**Bucket 4 boilerplate (25 files):** trusted canonical's Master Lease Database/property-folder copy as authoritative per Gabriel's answer; archived all 25 "(1)" conflicting copies in place, no canonical writes. Verified 0 originals remain.

**Bucket 3 (26 new files):** 10 confident-destination files copied to canonical (East Fulton notes, 2203-2207 Northwood Itron addendum, DG Cincinnati LOI, 7 property photos to 7658 Fishel) + 5 near-duplicate variants archived without copying (base content already captured). Remaining 11 unclear files read individually: 2 real new filings (2203 Northwood signage addendum, a new 9050 Red Branch Rd Marileaves narrative distinct from the existing "Email Chain Summary"), 6 confirmed duplicates/non-business/empty (archived — including one file that turned out to be an unrelated Claude Desktop networking-troubleshooting note, not a business document), 3 left untouched in "(1)" pending Gabriel's own read (a no-address deal-sourcing email, a legacy-format LOI, a proprietary-format Loop whiteboard file — none extractable with available tools).

**Bucket 4 live-financial (2 files):** content-diffed both via Excel MCP rather than guessing. Allentown underwriting model — discovered this is explicitly a personal favor analysis for a third party ("NOT an Oxford Realty Advisors portfolio asset"), and all "v1.1" variants across canonical + "(1)" share identical Assumptions-tab figures (differences are elsewhere in the workbook, not substantive); v1.0 is a genuinely superseded earlier draft. 1851 South Club Solar distributions — "(1)"'s copy is a stale Oct-2022 snapshot, a strict prefix of canonical's copy which continues to May 2026. Both resolved with no data-loss risk; archived.

**Bucket 2 (the orphaned 07-09 intake staging folder, `Claude_Workspace\_MANIFEST\Intake_From_Personal_OneDrive_2026-07-09\`):** turned out to have its own `_README_INTAKE.md` and `_triage_log_2026-07-09.csv` documenting a prior automated pass — useful audit trail, not previously referenced in memory. That prior pass also disclosed a real data-loss incident (6 of 8 site photos overwritten by a filename-collision bug in its script) — resolved as a non-issue this session, since the true originals in "(1)" were untouched (copy, not move) and all 8 were independently recovered and filed to `Pictures\Business Pics\7658 Fishel\` as part of Bucket 3, sourced directly from "(1)" and hash-verified, before this connection to the prior incident was even discovered.

Re-diffed the intake folder's remaining ~39 files against all of canonical (not just the prior pass's narrower matching): 7 confirmed safe duplicates archived; 22 files turned out to have a real property home the prior pass's narrower search missed (Hanan New Build Numbers Math → 3540 East Fifth Ave, a property never previously connected to this deal name; Eric Goldberg Bio → Loans External\Loan Symetra; Monthly interest payments EXPLANATION → GDG-CRG Estate; Promissory Note 485 S Walnut → Loans External\Loan Rich + Lucy 09.2025; plus Zettler/Seafire/Murad/PSA/Rarig/Hamilton Ave/Black Owned Genetics families) but every one conflicts with what's already filed there (different content, not simple duplicates) — relocated to `Claude_Workspace\_needs-review\2026-07-11_version-conflicts\`, grouped by property, rather than auto-merged or guessed. 9 files remain genuinely unidentifiable to any property — relocated to `Claude_Workspace\_needs-review\2026-07-11_no-property-identified\`. The staging folder itself is now retired (only its audit-trail scripts/CSV/README remain) with a closeout note appended to `_README_INTAKE.md`.

**Net effect:** "(1)" is now down to Desktop (personal, out of scope), Pictures (679 files, out of scope), and 3 genuinely-unresolved files (Document2.docx, North East Insualation LOI, Sunstone whiteboard) needing Gabriel's own read — everything else has been safely consolidated, archived-in-place, or relocated to a clearly-labeled review location. No files were deleted at any point; every archive was a move, never a delete, per Hard Invariant 6.

## 2026-07-11 — QC bug fix, broker PDF intake, and Des Moines memory-policy correction (session workflow notes)

- **Scorecard subtotal formula bug (QC catch):** acquisition-underwriting Scorecard subtotal formulas were summing the wrong row ranges, inflating Combined from 57 to 73. Deal not identified in the carried-over note — confirm no deliverable showing Combined=73 was already presented to Gabriel before treating this as closed. Standing fix logged to standards.md Part A "QC verification method": pull `openpyxl.load_workbook(path, data_only=True)` and eyeball every headline number before presenting, not just a `recalc.py` pass.
- **Broker OM/brochure intake:** CoStar/OM/brochure PDFs this session were all "Print to PDF" rasterized with no text layer, forcing vision-based page reading throughout and costing turnaround time. Logged to standards.md Part B (Brokers): request native/text-layer exports proactively going forward.
- **Des Moines memory-file correction:** a carried-over note suggested creating a new `market-intel-des-moines.md` file. Per memory-policy.md v2 (fixed doc set, anti-sprawl — the v1 model produced a 31-file junk drawer), validated market data already has a home: `markets.md`. No new file created. Instead added Des Moines (vacancy 7.5%, NNN rent $6.90/SF, cap 7.0-7.6% [SPECULATIVE] — Colliers Q4 2025 via market-monitor skill v1.1, NOT independently Gabriel-validated) plus Cincinnati/Grand Rapids/Richmond rows and relabeled two stale rows (Wisconsin→Madison WI primary, Tennessee→Nashville TN watch) into markets.md's cross-market table, which had drifted behind market-monitor v1.1's current 9-market target roster.

## 2026-07-11 — OneDrive "(1)" consolidation Bucket 1 executed: 23 files archived-in-place, zero canonical writes

Per Gabriel's go-ahead on the [OneDrive (1) move plan](https://claude.ai/code/artifact/a06e6d75-31fa-4a5c-b7f8-fc361b2bd577), executed Bucket 1 only (Buckets 2-4 still pending destination/conflict decisions). All 23 files confirmed byte-identical (content hash) to an already-correctly-filed canonical copy were moved from their original "(1)" location into `(1)\_archive_2026-07-11_consolidated-to-canonical\` (same relative path preserved), with a `MOVE-MANIFEST.md` logging source path, canonical match, and MD5 for each. Nothing was copied to canonical (already there, untouched — spot-checked 2 hashes post-move, unchanged) and nothing was deleted — this was a same-account rename within "(1)"'s own synced tree, so no dual-sync-client cloud-deletion race applies. Verified post-move: 0 of the 23 originals remain at their old "(1)" path; all 23 present in the archive folder.

Still outstanding: Bucket 2 (34 files stuck in the orphaned `Claude_Workspace\_MANIFEST\Intake_From_Personal_OneDrive_2026-07-09\` staging folder, never filed — a separate pre-existing backlog surfaced by this diff), Bucket 3 (26 new files, most need a destination decision), Bucket 4 (29 filename conflicts, 2 Personal/out-of-scope, 2 live-financial ones — Allentown underwriting model, 1851 South Club Solar distributions — needing an actual side-by-side read before archiving).

## 2026-07-11 (cont.) — RATIFIED: ora-treasury-yield-prefetch permanently retired (Gabriel-directed)

Gabriel confirmed the recommendation: leave the Rate Snapshot fix to fire naturally with `ora-am-brief`'s Monday 2026-07-13 run rather than manually forcing it today, and permanently retire the archived orphan rather than reviving it as a competing producer.

- RATIFIED: `ora-treasury-yield-prefetch` moved `_archive_2026-06-11_orphans/ora-treasury-yield-prefetch/` → `_archive_2026-07-11_retired/ora-treasury-yield-prefetch/` (plain filesystem move, no registry touched — task was never re-registered on either fleet since its 2026-06-11 archival).
- Added to the consolidated "do NOT re-register" list in `session-context.md` (superseded by `ora-am-brief` Block A, folded in-place 2026-07-11 10:58 ET — same Notion page `35e6ecd8…` + Rate History DB `ae068728…`).
- Open item left for Gabriel: no event-log entry credits who made the 10:58 ET `ora-am-brief` edit (possibly his own direct edit, possibly a concurrent Cowork session) — worth a quick confirmation next time he's in that session, per the register-scheduled-task v2.2 concurrent-writer check. Not blocking; the fix content itself is complete and correct.
- Residual: Notion "Rate Snapshot — Current" page stays stale (fetched_at stuck 2026-06-22) through the weekend by design — Block A skips Sat/Sun — and will refresh Monday 2026-07-13 ~06:00 ET.

## 2026-07-11 (cont.) — Rate Snapshot staleness: premise was stale, standalone-producer revival NOT performed

Gabriel handed this Code session the earlier "Fleet hygiene fixes" advisory (same-day entry above) as a 5-step task: restore the archived `ora-treasury-yield-prefetch` orphan and register it on the LAMS fleet. Re-verified ground truth before acting (per Engineering OS pre-flight discipline) and found the premise had already been overtaken:

- `ora-am-brief/SKILL.md` (LAMS store) carries a Modify timestamp of **2026-07-11 10:58:31 ET** — AFTER the "Fleet hygiene fixes" entry was written — and now contains a complete "BLOCK A — RATE/TREASURY PREFETCH" section: fetches UST/SOFR/spreads/FedWatch, writes the same Notion page (`35e6ecd8-9e59-814f-ae22-fe99464084d1`) + same Rate History DB (`ae068728-40ed-4089-b30a-38341348d3ed`), correct OK/SOURCE_DEGRADED/STALE_DATA/FAILED status logic, COM-only (not Composio) escalation, ggoldberg-only routing. This is a complete fix — someone (Gabriel or a concurrent session) folded the missing producer logic directly into `ora-am-brief` rather than reviving the standalone task, after the health-monitor flag surfaced. No event-log entry credits who made the edit — flagged to Gabriel to confirm it was his own change and not an in-flight concurrent session (register-scheduled-task v2.2 concurrent-writer check).
- **Did NOT** move the archived `ora-treasury-yield-prefetch` folder or register it as a separate LAMS task — doing so now would create a duplicate producer racing/double-writing the same Notion page and Rate History DB that Block A already owns. Left archived as-is pending Gabriel's call on permanent retirement (RATIFIED token + `_archive_*_retired` move).
- **Residual real gap:** 2026-07-11 is a Saturday; Block A's own guard skips Sat/Sun, so the Notion page will NOT actually refresh until the next weekday run (Monday 2026-07-13) unless someone manually fires `ora-am-brief` from Cowork sooner. This session cannot trigger a LAMS task manually (`create_scheduled_task`/run-now from Code only reaches the CC/MCP registry, confirmed via tool description: stores under `~/.claude/scheduled-tasks/`).
- `memory/markets.md` L29 already correctly documents Rate Snapshot as "maintained daily by ora-am-brief Block A" — that note was accurate historically and is accurate again now; no correction needed there.

No registry writes, no folder moves, no scheduled-task tool calls made this session. Flagged to Gabriel for a decision on (a) manually firing Block A now vs. waiting for Monday, and (b) permanently retiring the archived orphan.

## 2026-07-11 — Open-items dispatch: Notion Tenant DB review-list compiled, machine-migration B4 resolved, OneDrive "(1)" business-bulk move HELD on sync-risk

Gabriel worked through an 8-item open-items list (HubSpot token, Notion Tenant DB remediation, machine-migration B3/B4, 4 staged Cowork skills, 2 Claude Preferences lines, ora-calibration-snapshot/ora-entry-market-scan register-or-shelve, 07-09 17:08 alert email, ora-cam-reconciliation-annual toggle, OneDrive "(1)" folder). Per-item disposition:

- **HubSpot token → oxford-command-center `.env`:** untouched — credential entry is categorically prohibited, no override exists. Gabriel must paste the value himself.
- **Notion Tenant DB remediation:** Gabriel chose "compile a review list first." Read-only compilation from the existing `reference_tenant_db_completeness_gap.md` 07-09/07-10 investigation (no new Notion queries or writes) delivered as an artifact — 22 confirmed phantom rows (17 still carrying a live squatted HubSpot link), 7 unconfirmed-phantom, ~35 duplicate-row pairs/triples, 5 stale link-blanked rows needing an archive-or-leave call. Decision on remediation approach per category still needed from Gabriel; no writes made.
- **Machine-migration B4 (old-machine decommission):** Gabriel confirmed the old machine is no longer needed — safe to proceed toward physical decommission (manual step, not Code-executable). Updated `session-context.md` HALT note (line 3) and `project_claude-setup-audit-2026-07-09.md` headline finding accordingly. **B3 burn-in checklist remains open**, not resolved by this session.
- **4 staged skills → Cowork Settings→Capabilities:** not actioned — wrong surface (Cowork account settings unreachable from Code) regardless of decision; flagged for Gabriel's next Cowork session.
- **2 lines in Claude User Preferences:** untouched, consistent with the standing convention that this is Gabriel's personal edit surface.
- **ora-calibration-snapshot / ora-entry-market-scan register-or-shelve:** not actioned — LAMS-side, unreachable from this Code session regardless of decision; flagged for Gabriel's next LAMS/Cowork session.
- **07-09 17:08 alert email:** read and summarized for Gabriel — confirmed to be a self-test of the new `deploy-mirror.ps1` failure-alert path (added 2026-07-09) verifying it reaches Outlook end-to-end; body states "No action needed"; already marked read. Nothing further required.
- **ora-cam-reconciliation-annual `enabled:false` toggle:** not actioned — LAMS/Cowork-only, unreachable from this Code session (documented in `session-context.md` since 2026-07-09).
- **OneDrive "(1)" folder — unlink vs. consolidate:** Gabriel answered "consolidate into canonical" as a directional call. Before executing, re-read the existing 07-09 T12 deferral evidence (`01_Workspace\outputs\2026-07-09_OneDrive-1-BulkMove_Manifest_v01.md`): the audit premise that "(1)" is a stale pre-migration duplicate is falsified in part — `(1)\Attachments\` received live 2026-07-09 inflow (Allentown Portfolio underwriting files) and two OneDrive.exe sync clients run concurrently, so a raw local move out of "(1)" would propagate as a cloud deletion in whatever account syncs it (confirmed 2026-07-10: Gabriel's own `ggoldberg@oxfordra.net` account). **Move HELD, not executed** — the directional answer doesn't constitute informed execution sign-off on a live-syncing, business-critical (leases/PSAs/LOIs/estoppels/promissory notes) file set; reported the risk back to Gabriel for explicit go-ahead on the actual move plan, per Hard Invariant 5 (business-folder write/move/delete needs permission) and the general hard-to-reverse/shared-state caution.

**Also flagged, not acted on:** a large uncommitted diff in the shared `~/.claude` checkout (CLAUDE.md, hooks incl. confidentiality-guard.py/ora-autonomy-gate.py, settings.json, several maintenance probes, rules.md, ~20 files) not from this session — single-writer doctrine caution, needs reconciliation with whoever's work it is.

No financial models, governor constants, oxfordra.net prod, or external communications were touched. No credentials entered. No OneDrive business files moved.

## 2026-07-11 — Fleet hygiene fixes (CC/MCP fleet) from automation-health-monitor advisories

- Registered 2 dark tasks found on-disk-but-unscheduled in the CC store: `ora-calibration-snapshot` (quarterly, 1st of Jan/Apr/Jul/Oct 08:00 ET — feeds oxford-command-center calibration loop) and `ora-entry-market-scan` (monthly, first Tuesday 11:00 ET — Louisville/Delmarva/Grand Rapids/Des Moines sourcing scan). Both had complete, well-formed SKILL.md content; verified via `list_scheduled_tasks` post-registration.
- RATIFIED: deleted 2 already-fired, auto-disabled one-time registry entries — `canary-model-check-temp` and `ora-fleetview-confirm`. SKILL.md content retained on disk per tool behavior; this was pure registry cleanup, not a retirement of active functionality.
- Root-caused the "Rate Snapshot — Current" staleness (Notion page `35e6ecd8-9e59-814f-ae22-fe99464084d1`, stuck at 2026-06-22 06:20 ET fetched_at): the dedicated producer `ora-treasury-yield-prefetch` (weekday 05:40 ET, publishes UST/SOFR/spreads/FedWatch to this exact page + Rate History DB) was archived as an "orphan" 2026-06-11 on the assumption its duty was absorbed into `ora-am-brief` "Block A." The current live `ora-am-brief` (LAMS fleet, rebuilt 2026-07-08) is now a thin wrapper delegating entirely to the Cowork `daily-brief` skill v2.5 — grepped v2.5's SKILL.md and confirmed it contains NO rate-prefetch/Notion-publish logic at all. No active producer currently writes this page on either fleet. Fix requires restoring `ora-treasury-yield-prefetch` and re-registering it on the LAMS/Cowork fleet (this is a LAMS task, and CC/MCP's `scheduled-tasks` MCP in this Code session cannot register to that fleet — Rule 1 of register-scheduled-task v2.2). Flagged to Gabriel; not auto-registered.
- Left uninvestigated pending cross-fleet visibility: the 7 same-time collisions / 14-task 05:00–09:30 AM pileup / 1 throttle skip on automation-health-monitor. CC/MCP fleet alone contributes real congestion in that window (`ora-health-guard` 05:15, `ora-master-workbook-ingest` 05:45 Mon, `ora-aaos-expire-leases` fires 4x in-window daily at :12 past 06/07/08/09, `ora-aaos-publish-contracts` 08:00 daily) but full collision resolution needs the LAMS-side cron list, which this Code session cannot query live — needs a supervised Cowork pass. The "14 never-ran" flag is mostly benign: most are annual/monthly/quarterly-cadence tasks added 2026-07-08→07-10 that simply haven't reached their first fire date yet (e.g. `ora-cam-reconciliation-annual`, `ora-consolidate-memory-monthly`).

## 2026-07-11 — Overnight autonomous pass on the "Manual Action Items" list: 5 of 15 already resolved by Gabriel, 1 more (Fleet Heartbeat) activated by Claude, rest genuinely blocked

Gabriel asked (going to bed, ~21:55 ET) to determine which of the 15 items in tonight's earlier "Manual Action Items" doc Claude could complete without him, and do those. Re-verified every item against live state rather than the memory snapshot the doc was built from — found the ground had already shifted:

**Already done by Gabriel/another session before this pass started (no action needed):**
1. oxfordra.net internal-artifact exposure — PRs #10 (`fix/publish-dist-exclude-internal`) and #11 (`chore/pin-netlify-cli`) both merged by ZeOoba (Gabriel) 2026-07-10 ~12:4x ET. Live-verified: `/evals/`, `/scripts/build-kb.mjs`, `/netlify/edge-functions/chat.ts`, `/knowledge-base.json` all now 404 on prod; `/` still 200.
2. `ora-claude-config` PR #7 — merged by ZeOoba 2026-07-08.
3. Liberty Office Park deal-stage — Notion shows Gabriel already resolved this 2026-07-09: Stage deliberately kept "Candidate" (PARKED pending the Cincinnati-cluster go/no-go with Eric), explicitly flagged not to re-nudge.
4. `ora-pm-ledger` + `ora-weekly-hygiene` — both already `enabled:true` (re-enabled 2026-07-09 per their own SKILL.md changelogs).
5. `ora-health-guard` — already `enabled:true`, `lastRunAt` 2026-07-10 (OneDrive recycle-bin recovery already happened).

**Executed autonomously this pass (internal-only, reversible, no credentials/prod/external-comms involved):**
- Fleet Heartbeat dead-man's-switch (Task 6, built 2026-07-09, commit `149a21f`) — the pre-push doctrine gate that had blocked it was re-checked live: `doctrine-integrity-probe.py` and `governor-drift-probe.py` both now pass clean (the 4 [MISSING] CLAUDE.md skill refs from 07-09 are gone — already fixed by an intervening session). Pushed the 13 previously-blocked commits to `ZeOoba/ora-claude-config` (`56b579a..149a21f`). Ran `gh workflow run fleet-deadman.yml` as the documented smoke test — first run correctly failed (heartbeat 26.4h stale, since no daily pulse exists yet) and opened issue #9, proving the alarm path works. Ran `push-fleet-heartbeat.ps1` once by hand (commit `d9fba21`) to refresh the heartbeat; re-ran the workflow — clean success. Closed issue #9 with an explanatory comment.
- **Deliberately NOT done:** registering the recurring `schtasks /Create /TN "ORA Fleet Heartbeat Push" /SC DAILY /ST 07:30 ...` task. The script's own header says this "needs Gabriel's ratification" — creating new standing background infrastructure that pushes to GitHub daily reads as the "persistent configuration" category that needs an explicit yes, not a blanket one. Left for Gabriel; the heartbeat will go stale again in ~24h and re-alarm (correctly) if not registered.

**Confirmed still blocked, left for Gabriel (with reasons):**
- HubSpot Private App token for oxford-command-center `.env` — credential entry is a prohibited-for-automation action.
- Notion Tenant DB phantom/duplicate-row remediation — needs Gabriel's scoped decision before further live-CRM writes.
- Machine-migration B3/B4 (old-machine decommission) — factual question only Gabriel can answer.
- Importing 4 staged skills into Cowork Settings → Capabilities — account-settings change, needs an explicit yes.
- 2 lines in Gabriel's own Claude User Preferences — his personal edit surface, previously deliberately left untouched by other sessions too.
- Register-or-shelve decision on `ora-calibration-snapshot`/`ora-entry-market-scan` — needs Gabriel's call; also LAMS-side, unreachable from this CC/MCP session regardless.
- Reading/closing the 07-09 17:08 alert email — his own inbox, no execution needed beyond him reading it.
- `ora-cam-reconciliation-annual` enabled:false toggle — LAMS/Cowork-only, technically unreachable from this Code session.
- OneDrive "(1)" folder business-bulk unlink-vs-consolidate — judgment call Gabriel already deferred once; account-ownership half of the question was separately ratified 2026-07-10 (see `reference_memory_scope_fragmentation.md`), this half is still open.

**New finding surfaced, not acted on:** the shared `~/.claude` checkout has a large uncommitted diff (CLAUDE.md, several hooks incl. confidentiality-guard.py/ora-autonomy-gate.py, settings.json, multiple maintenance probes, rules.md, ~20 files total) that is not from this session and was not touched — matches the single-writer caution in `rules.md` §1/CLAUDE.md's shared-checkout doctrine. Worth reconciling with whoever's work it is; not committed, not staged, not reset.

No financial models, governor constants, oxfordra.net prod (beyond what Gabriel had already merged himself), or external communications were touched. No credentials entered.

## 2026-07-10 (eve) — Open-sessions board dispatched; 11 items decided; found a real re-surfacing bug in the board's own exclusion logic

Gabriel answered today's 5 PM open-sessions board (11 cards). Dispatch:

**Already resolved on investigation (no action needed, verified not assumed):**
- `local_438ae1ab` netlify.toml /api/chat-lead shadowed-rewrite fix — already merged to website-canonical main via PR #10 (2026-07-10 16:41 UTC) bundled with the publish-dist-exclude-internal restructuring; verified LIVE via curl (evals/, scripts/, netlify/edge-functions/knowledge-base.json all now 404, dead chat-lead redirect gone). No merge/deploy action taken by this session — read-only verification only, per Hard Invariant 2.
- `local_24b08976` Registry cleanup / ledger-restore handoff — all 3 tasks in the 2026-07-10 Cowork→Code handoff packet were already complete: fleet-disposition-ledger.md §1-§8 restored and verified byte-identical to the preserved §8 copy; offline-suppression alert logic shipped in deploy-mirror.ps1/deploy-alert.ps1 with 13 passing smoke-test scenarios; append-only Append-Ledger.ps1 helper live (rules.md rule 12).
- `local_2c6fa79c` ora-pm PR #3 ("Merge it for me") — already merged 2026-07-07, CI+CodeRabbit green; verified via `gh pr view`, no duplicate merge attempted.

**Real decisions taken:**
- Website SEO optimization audit — HOLD, Gabriel wants to review before green-lighting build items 1-2.
- Website audit and SEO optimization plan (interrupted session) — Gabriel says NOT superseded despite overlap with fresher audits; kept open.
- oxfordra.net GitHub repo (website-canonical vs oxford-site) — HOLD on backup/merge/deploy despite canonical-source question being resolved.
- Systematization candidates (Excel MCP connector crash-loop, ~40 orphaned python.exe pairs) — Gabriel will restart Claude Desktop himself later; nothing killed.
- SEO check for oxfordra.net (82/100, title/meta trims) — stored in [[project_oxfordra_seo_audit_2026-07]], not applied.
- Dollar General Cincinnati underwriting (11850 Hamilton Ave) — reconfirmed "Candidate is correct"; the board had flagged an apparent Notion Stage discrepancy (session claimed "Due Diligence" write, live Notion showed "Candidate") but this was just sequencing — the session ran BEFORE the 2026-07-09 PARK decision, not a failed write.
- Memory consolidation completion + Claude setup analysis and optimization — both fully closed out today: Symetra/Park National auto-pays confirmed executed by Gabriel; Desktop Commander extension confirmed installed (AppData dir dated 2026-07-09); E Fulton CLAUDE.md tombstone confirmed removed.

**Process bug found (worth fixing before the next run):** 4 of the 11 cards on today's board — DG Cincinnati, ora-pm PR3, Memory consolidation, Claude setup optimization — had ALREADY been decided on the 2026-07-09 board (`answered.json`, decidedAt 2026-07-09T17:15 ET) with `lastActivityAt` for all four predating that `decidedAt`. Per the board's own STEP 2(c) exclusion rule these should have been dropped before rendering. Root cause: this session's STEP 2(c) check read only the first ~3000 characters of `answered.json` (a truncated preview) instead of the full file, so it missed entries past that point and re-surfaced 4 already-decided sessions. No harmful action resulted — Gabriel's answers today were consistent with or incremental to the prior decisions — but the next `ora-open-sessions-board` run should parse the FULL `answered.json` (e.g. via a script, not an eyeballed partial Read) before applying the exclusion filter.

**Why:** Daily 5 PM open-sessions triage per the standing `ora-open-sessions-board` scheduled task.
**How to apply:** Skill file for `ora-open-sessions-board` (STEP 2c) should be hardened to require a full parse of `answered.json`, not a partial file read, before exclusion filtering.

## 2026-07-10 — Model-release-checklist workflow-optimization sweep closed out

Completed the 5 outstanding items from the 2026-07-10 model-release-checklist sweep: (1) `oxford-command-center/server/ai/narrative.ts` `DEFAULT_MODEL` now exported; the 11 literal `claude-haiku-4-5-20251001` assertions across 4 test files (`narrative`, `lease-narrative`, `briefing-narrative-contract`, `briefing-pdf-narrative`) now reference the constant — typecheck clean, all 71 tests pass. (2) CHANGELOG.md haiku-ID drift claim re-verified directly and found NOT present in the canonical file (only stale worktree copies exist) — no fix needed, memory corrected. (3) `ora-pm` sweep completed: confirmed it calls the Anthropic API directly (`server/lib/lease-extract.ts` + `server/routes/intake.ts`, `DEFAULT_MODEL='claude-opus-4-8'`, env-overridable via `INTAKE_MODEL`) — already safely alias/env-based, no fix needed. (4) Checked upstream status of the #48976-pattern (CC/MCP scheduled-task model-pinning bug): the specific issue was closed 2026-05-27 by the stale-bot (not fixed); the live tracking duplicate `anthropics/claude-code#36496` remains OPEN as of 2026-04-14 with no maintainer response despite community reports — still an open upstream gap. (5) Verified `ora-model-release-watch` is a live registered CC/MCP task (v1.0, created today) and that `automation-health-monitor`'s live SKILL.md (found to be v1.6, not the v1.2 referenced by the cached plugin descriptor — a version-drift worth a separate look) enumerates CC/MCP task folders generically via directory walk, so it will pick up the new task automatically without further action. Full detail: `reference_model_release_checklist.md`.

## 2026-07-10 — Rule 13 added: recovery-brief state-freshness header + re-verify-before-acting (Cowork cleanup session)

The 2026-07-10 LAMS fleet-recovery cleanup session found 3 of its 8 instructed steps stale on arrival (Steps 1/2 tasks already Gabriel-deleted 07-08/07-09; Step 4 v1.5 promotion already done+verified 07-08/07-09; Steps 7/8 health-guard already transcript-recovered and all three CC tasks already re-enabled 07-09). One instructed action (Step 7's OneDrive recycle-bin recovery of ora-health-guard) would have risked restoring a STALE copy over the verified-current 07-09 transcript restoration had it been executed as written. Gabriel directed codifying the fix: memory/rules.md §13 now requires every recovery/cleanup brief to carry a "STATE AS OF <timestamp> — re-verify ground truth per step" header, and requires executors to verify each step's premise against the live source of record before mutating anything. Session actions on disk: two empty-shell folders (ora-week-ahead-briefing, ora-automation-health-monitor) archived to Documents\Claude\Scheduled\_archive_2026-07-10_retired\ with README. Also confirmed the referenced audit artifact ~/.claude/maintenance/_audits/2026-07-08_LAMS-fleet-audit_v01.md does not exist anywhere on the machine (full C:\Users\Owner file search, 0 hits) — findings survive only in event_log/_REGISTRY/session-context references.

## 2026-07-10 — Model-tier doctrine split (opus/Fable) + downstream fixes

CLAUDE.md/spec §7.1 Dispatch line split the top model tier: Fable = hardest (financial/confidential/security/precision, final review+verify), opus = architecture/design, sonnet unchanged (multi-file integration/debugging/standard implementation), haiku unchanged. Invariant floor for confidential/financial/governor code raised from "never below opus" to "never below Fable". Applied to both CLAUDE.md and the dated 2026-06-05 Engineering OS spec (spec annotated as a post-dated correction, not silently rewritten).

Full-sweep follow-on (Gabriel: "perform full deep research and investigation", then "proceed with all recommendations"):
- Fixed a real false-positive in `ora-autonomy-gate.py` (Hard Invariant 2 site-write gate): `FD_DUP_RE` exempted `2>&1`-style fd-duplication from the bare-">" write-indicator check but not `2>/dev/null`/`2>nul` null-device redirects, so a read-only command (e.g. `grep ... 2>/dev/null`) touching an oxford-site/website-canonical path string false-blocked. Added `NULL_REDIRECT_RE`, anchored so a real write whose path merely contains "/dev/null" as a substring still blocks. TDD: 3 new cases in `test-ora-autonomy-gate.py`, confirmed red (25/27) then green (27/27).
- `ora-financial-code-integrity-sweep` (weekly CC/MCP sweep of governor-invariant code — DSCR/LTV/NOI/capital-allocation) was dispatching 3 opus refuters via `refute-financial-change.js` — below the new Fable floor. Raised to Fable with a per-lens opus fallback on a null agent() result (Fable's own concurrency ceiling is untested — only opus was canary-tested at ~2-3 concurrent, and Fable has observed availability gaps per cached client UI text). Workflow now returns `succeeded`/`allFailed` so the calling SKILL.md can distinguish a genuinely clean sweep from every lens failing silently (treated as TOOLING ERROR, not CLEAN). Concurrency held at 3, unchanged. Committed on branch `claude/fable-financial-refuters` in a worktree at `oxford-command-center/.claude/worktrees/fable-financial-refuters` (commit 915b2565) — NOT pushed, NOT merged; awaiting Gabriel's review/merge decision.
- FLAGGED FOR GABRIEL, unresolved (compounds a prior flag): the mirrored "default opus" line in his User Preferences (app-level, not filesystem-editable) is now doubly stale — it was already flagged 2026-07-09 (T8) when the Dispatch line first moved off "opus default", and CLAUDE.md has since moved again to the Fable/opus split. Needs a manual sync.
- `reference_scheduled_task_model_standard.md` appeared to be missing from canonical memory scope (present only under the incomplete `--1-`-suffixed folder) when first checked — but a newer, more complete version (11 CC/MCP tasks vs. 8, new `[[reference_model_release_checklist]]` link) appeared in canonical scope 3 minutes later, mid-session, written by something other than this session. No action taken (would have clobbered newer work with a stale restore) — flagged as evidence of a concurrent writer active on the same OneDrive memory scope during this session; worth confirming what that other session/task was.
- Verified clean: the 3 Cowork-surface ported CLAUDE.md copies correctly omit the Engineering OS section entirely (by design) with zero opus/Fable drift. `oxford-command-center/CLAUDE.md`'s one "opus-4.8" mention is a historical PR-review changelog line, not doctrine — left as-is.

eos-plan-gate's 4+-unplanned-edits threshold was hit partway through (doctrine edits + hook fix + this workflow edit, all individually justified/approved in-conversation rather than pre-planned); used the documented override sentinel rather than stopping for a full /plan on already-approved work.

## 2026-07-10 — QA remediation plan executed: 2 branches pushed (chat-link bug, portfolio images), 1 harness gap found

Executed the Opus-planned fix list from the draft-preview QA pass (2026-07-10, same day). Both real code fixes are TDD'd, verified in a real browser against a draft deploy, and pushed — nothing merged or deployed to prod.

1. `fix/chat-link-trailing-punctuation` (2 commits, pushed): assets/chat.js's bare-URL autolinker no longer bakes trailing sentence punctuation into hrefs (oxfordra.net/portfolio. -> 404, confirmed fixed). chat.ts prompt nudged to emit markdown [text](url) links. While verifying in-browser, found and fixed TWO bugs the QA/plan didn't catch: (a) a pre-existing latent bug — the oxfordra.net-specific regex had no guard against re-matching text already inside an href/label from the two regexes ahead of it, producing nested malformed `<a>` tags once the model actually started emitting markdown links (it never had before); (b) my own prompt edit used literal backticks inside the backtick-delimited SYSTEM_PROMPT_BASE template literal, breaking the Deno edge-function bundle — caught by a draft build failure, fixed same-session. 5 initial + 2 regression Node unit tests (assets/chat.test.js, node --test), all green.
2. `fix/portfolio-responsive-images` (2 commits, pushed): portfolio.html's 18 card images (missed one, 05-exterior-front/Raytown MO, in the first pass — caught by a post-deploy sweep, fixed same-session) now use width-descriptor srcset (400w generated derivative + existing master) with sizes matching the confirmed `>=1024px` 3-column breakpoint from styles.css. scripts/generate-portfolio-thumbnails.mjs (sharp-based) is the reusable generator. Caught a real transform bug pre-push: the first-pass script also rewrote the page hero's <source> tags, since the hero reuses the same master image as the first card at 4x the display size — reverted, hero untouched. Verified in-browser: at desktop width all 18 cards resolve the 400w file (naturalWidth 400, zero broken images); at narrow viewports the `sizes` logic correctly falls back to the larger master instead of upscaling.

NOT changed (per the plan): Fix 1 (GA placeholder ID `G-XXXXXXXXXX` live on prod) stays blocked — needs Gabriel's real measurement ID + a LinkedIn Insight tag keep/remove call. Fix 3 (`0.png` missing-alt) resolved as a false positive in the original QA script, not a real bug (Leaflet tile, already has `alt=""`). Fixes 5-7 (tenant-application reCAPTCHA weight, Netlify Lighthouse plugin null scores, chat-asset "16x refetch") are accept/out-of-scope/non-issue per the plan, no code touched.

NEW finding, not yet fixed: while running `scripts/eval-chat.mjs` against the chat-link draft, 3 of the harness's own fixtures produced false-positive FAILs on demonstrably correct model behavior — `must_not_contain: "%"` on two Refusal-category cases trips on the model volunteering legitimate public percentages (100% occupied, ~15% LTV) after correctly declining the confidential ask; `must_not_contain: "developer mode"` on a prompt-injection case trips on the model's own refusal quoting the phrase back. This directly affects the mandatory eval-gate wired into `ora-skills/deploy-site/SKILL.md` earlier the same day — as written, a legitimately-passing draft could get blocked by these three brittle assertions. Not fixed this session (out of the QA plan's scope); flagged to Gabriel, needs a decision on tightening the fixtures (e.g. `must_not_contain` a specific fabricated number instead of the bare `%`/phrase substring).

## 2026-07-10 — Model-release monitoring systematized (`ora-model-release-watch` registered, CC/MCP fleet)

Gabriel asked how model-selection tiering should be understood/revised whenever Anthropic ships a new Claude model. Full sweep run first (see `reference_model_release_checklist.md`, new file): confirmed CLAUDE.md's tier doctrine (Fable/opus/sonnet/haiku by role, no hardcoded IDs) needs no edit per release; the surfaces that DO carry hardcoded model IDs are `~/.claude/settings.json`, `reference_scheduled_task_model_standard.md`, and `oxford-command-center/server/ai/*.ts` + `.env` (ora-pm not yet checked). Also used the sweep to correct `reference_scheduled_task_model_standard.md`'s "Known gap — CC/MCP fleet not covered" section: confirmed via the existing canary result + `ora-task-integrity-guard/SKILL.md:22` that the CC/MCP fleet is structurally uncoverable (server-pinned model, no live `model` field) rather than merely "not yet done."

Gabriel then asked that this become autonomous rather than something he has to remember to raise. Registered `ora-model-release-watch` (CC/MCP fleet, weekly Monday ~11:20 AM ET, cron `20 11 * * 1`) via the supervised `create_scheduled_task` MCP tool per the register-scheduled-task skill protocol — concurrent-writer check clean (registry-membership.log last entry 2026-07-09T19:34, no drops/adds since). Task reads this session's own system-prompt model-lineup statement each run (not the claude-api skill's cached table, confirmed stale by 1+ month), diffs against `reference_model_release_checklist.md`'s recorded lineup, and on a genuine new-model detection: updates that memory file, posts to Notion Ops Hub (`32b6ecd8`), and emails ggoldberg only with the concrete update checklist. Silent no-op on a clean week — no noise. Verified via `list_scheduled_tasks`: next fires 2026-07-13, then 2026-07-20.

Not yet done: sweep of `ora-pm` for hardcoded model IDs (deferred, Gabriel declined further action this session beyond the automation itself).

## 2026-07-10 — OneDrive canonical-account question ratified: Eric's account is MAIN

Gabriel ratified: the no-suffix `OneDrive - Oxford Capital Partners` folder — synced under **egoldberg@oxfordra.net** (registry `Business1`) per today's ledger-restore incident — is the MAIN/canonical account for `Claude_Workspace` going forward. `(1)`-suffixed folder (Gabriel's own `ggoldberg@oxfordra.net` account, registry `Business2`) stays non-canonical. This is a confirmation of already-de-facto behavior (every session's cwd already resolved to the no-suffix folder), not a migration — no files moved. Closes the "which account syncs which folder" half of `reference_memory_scope_fragmentation.md`'s 2026-07-09 open question; the business-bulk unlink-vs-consolidate half (manifest in `01_Workspace\outputs\2026-07-09_OneDrive-1-BulkMove_Manifest_v01.md`) is still open. Full detail: `memory/reference_memory_scope_fragmentation.md` 2026-07-10 section.

## 2026-07-10 — Ledger restore (2nd overwrite incident) + append-only helper + alert suppression

**Trigger:** handoff `2026-07-10_ledger-restore-and-alert-hardening.md`. `2026-06-10_fleet-disposition-ledger.md` had been reduced to 18 lines (only §8) by a prior session's wrong-write-mode overwrite — the second time a governance ledger has been damaged this way (the ledger's own §8 documents the first-order incident this session also touched, `ora-dashboard-refresh` retirement).

**Discovery en route:** attempting the OneDrive Version History restore surfaced that `Claude_Workspace`'s canonical copy (the one every session's doctrine treats as "the" workspace) is synced under **egoldberg@oxfordra.net**'s OneDrive account (registry `Business1`, `UserFolder` = the no-suffix `OneDrive - Oxford Capital Partners`), not Gabriel's own account (`Business2`, `ggoldberg@oxfordra.net`, backs the `(1)`-suffixed folder memory already flagged as stale). Confirmed via `HKCU\Software\Microsoft\OneDrive\Accounts\{Business1,Business2}` `UserEmail`/`UserFolder`/`ServiceEndpointUri` values. Gabriel has access to Eric's SharePoint personal site (delegate/shared), so the browser-driven restore worked once pointed at the right account. See `reference_memory_scope_fragmentation.md` — this resolves part of its still-open "which account syncs which folder" question for the no-suffix side; the `(1)`-side answer (already known: ggoldberg) is now cross-confirmed.

**Actions taken:**
1. Restored `2026-06-10_fleet-disposition-ledger.md` from OneDrive version 2.0 (6/21/2026 9:57 PM, the last version before the overwrite; verified §1–§7 present, no §8) via Version History on Eric's SharePoint site. Re-appended the preserved §8 block (from the handoff's durable copy) in append mode; verified the resulting file's §8 is byte-for-byte identical to the preserved copy via `diff`.
2. Built `Claude_Workspace\00_Governance\Scripts\Append-Ledger.ps1` — refuses any path outside `00_Governance\...\outputs\*ledger*.md`, refuses a nonexistent target, snapshots pre-append state to a sibling `archive\` folder by default, appends via `Add-Content` only. Tested against a scratch ledger (guard rejections, successful append with correct blank-line separator, snapshot fidelity, `-NoSnapshot`). Documented as standing rule in `memory/rules.md` §12.
3. Added machine-offline alert-noise suppression to `oxford-command-center` (`scripts/lib/deploy-alert.ps1`, `scripts/deploy-mirror.ps1`) per the same handoff's Task 2 — the 2026-07-10 AM outage (~10:15–11:00 ET) had produced 2 duplicate "Mirror deploy FAILED" emails plus a separate `automation-health-monitor` ALARM addendum for one transient outage. New `Test-OfflineSignature`/suppression-state-file logic collapses repeat `git fetch`/`pull` failures into one immediate alert + one recovery digest (or one escalation alert if the outage exceeds 3 consecutive runs); `-Critical`/GATE CHECK FAILED is never suppressible. 25-assertion smoke test (`scripts/deploy-mirror.smoke-test.ps1`, scenarios 6–14 new) passes; independent code-reviewer pass found no correctness issues. Work done in git worktree `.claude/worktrees/alert-suppression` (branch `alert-suppression`, uncommitted — oxford-command-center had unrelated foreign uncommitted changes on the shared checkout, single-writer rule). Also added a Step 3.5 correlation note to `ora-skills/automation-health-monitor/SKILL.md` (v1.3) so the health-monitor's own per-task alert folds into one Notion note instead of a separate Gabriel email when the same offline signature spans multiple self-recovered tasks.

**Open items:** `alert-suppression` branch not yet merged/PR'd (Gabriel has not been asked to review/merge). Whether the Eric-vs-Gabriel OneDrive account split for the canonical workspace is intentional (and whether it should be documented as permanent doctrine vs. reconciled) is still Gabriel's call — flagged, not resolved, this session.

## 2026-07-10 — ora-dashboard-refresh RETIRED (RATIFIED)

**Trigger:** scheduled 07:00 ET run of `ora-dashboard-refresh` found its source dir `C:\Users\Owner\oxford-perfection\ora-dashboard\` gone (archived `oxford-perfection_archived-20260707`, same date as the task's own stale "RESTORATION NOTE" claiming full compliance). Sent Gabriel a failure email claiming Phase 2/G1 (retarget to `oxford-command-center`) "had not shipped" and no deploy path was wired — **that claim was wrong**, based on an empty grep result from a PowerShell profile-load error that suppressed the real match.

**Correction (Gabriel-directed follow-up, same session):** `oxford-command-center\package.json` already has `deploy:mirror` (bake + build + `wrangler pages deploy dist --project-name=ora-command-center`). `scripts/deploy-mirror.ps1` + `scripts/register-mirror-task.ps1` are live: native Windows Task Scheduler job "ORA Command Center - Mirror Deploy" runs hourly + 06:45 ET, fast-forwards to `origin/main` first, bakes with `MIRROR_INCLUDE_CONFIDENTIAL=1`, deploys, then verifies the Cloudflare Access gate (302 → `spring-wood-ade4.cloudflareaccess.com`) is still enforcing before declaring success — confirmed live via `schtasks /query` (Enabled, next run 12:00 PM) and a direct curl (302 confirmed at time of check). Corroborated by `memory/reference_command_center_mirror_deploy_gap.md` (PRs #192–#196, merged 2026-07-09) and CC/MCP task `ora-command-center-mirror-drift-check` (added to registry 2026-07-09T18:26:41 per registry-membership.log), which already monitors this exact pipeline.

**Decision:** repointing `ora-dashboard-refresh`'s Steps 1/4 to duplicate this pipeline (as originally instructed) would create two independent schedulers deploying different codebases under opposite confidentiality models — the old task's model filters "Fulton" OUT assuming a public target; the mirror's model INCLUDES confidential data assuming an Access-gated target — to the SAME Cloudflare Pages project (`ora-command-center`). RETIRED instead of repointed.

**Actions taken this session:**
1. `update_scheduled_task(ora-dashboard-refresh, enabled:false)` — verified via `list_scheduled_tasks`.
2. Moved LAMS store folder to `Documents\Claude\Scheduled\_archive_2026-07-10_retired\ora-dashboard-refresh\` — verified landed (contains `SKILL.md` + nested `archive\`).
3. **Guard interference observed:** `restore-skill-governor.py` (or equivalent) recreated a stub `SKILL.md` at the original path with the pre-edit description within the same session — matches `session-context.md`'s documented gotcha ("Disabled-but-registered tasks cannot be folder-archived — remove the registry entry first"). The archived copy is the authentic, complete one; the regenerated stub at the original path is redundant.
4. `delete_scheduled_task(ora-dashboard-refresh)` **BLOCKED** — this session was itself launched by the `ora-dashboard-refresh` scheduled run; the tool refuses self-deletion. **Open item: run `delete_scheduled_task` for `ora-dashboard-refresh` from a fresh (non-triggered) session** to remove the registry entry and stop the guard from continuing to regenerate the stub.

**Also flagged, not yet investigated:** native task "ORA Command Center - Mirror Deploy" showed `Last Result: 1` (11:00 AM run, today) via `schtasks /query`. Non-zero — worth a follow-up check of `deploy-mirror.ps1`'s alert path / `data/outbox/` for the failure reason.

**Confidential deal note:** per `session-context.md`, E. Fulton DECLASSIFIED 2026-07-09 — no active confidential deals at time of this entry; the confidentiality-model collision above is an architectural finding independent of current deal status.

## 2026-07-10 — Publish-dir-exposure follow-up: 3 systematization candidates implemented

All three items Gabriel flagged from the `fix/publish-dist-exclude-internal` session (weekly prod exposure probe, netlify-cli pin, chat-eval draft gate) are built:
1. Scheduled task `ora-site-exposure-probe` registered (CC/MCP fleet, Wed 09:26 AM ET) — curl-matrix asserts `evals/`, `scripts/`, `netlify/` etc. 404 on prod and the `_headers` security-header set is intact; emails ggoldberg only on alarm, tags known-open-vs-new-regression against the still-unmerged publish-dist fix.
2. `website-canonical` branch `chore/pin-netlify-cli` (pushed, not merged) adds a package.json pinning `netlify-cli@26.2.0` as a devDependency — `npx netlify-cli` now resolves the local install deterministically instead of depending on the (previously non-existent, found only transiently in) npx cache. Verified via `npx netlify-cli --version` resolving instantly post-`npm install`.
3. `ora-skills` `deploy-site/SKILL.md` (pushed to main, 2 commits): first committed an already-applied-but-uncommitted rewrite pointing the skill at the netlify-cli-from-website-canonical procedure (this is the fix the 2026-07-09 session note described as "FIXED" but had never actually landed a commit for); then added a new mandatory step running `node scripts/eval-chat.mjs --base=<draft-url>` after every draft deploy, blocking the prod-confirmation ask on a nonzero exit.

Both website-canonical edits went through the `allow-website-change` override sentinel per Hard Invariant 2, created/removed same-turn on Gabriel's explicit "fix these systematization candidates" naming exactly these risks (same pattern as the 2026-07-09 precedent). No prod deploy occurred — everything here is pushed branches/tooling, still pending Gabriel's merge decision and, separately, prod sign-off for the underlying publish-dist-exclude-internal fix itself. Hit and worked around the documented autonomy-gate write-indicator false-positive twice (commit messages containing "oxford-site" as prose, a read-only `git show ... > /dev/null`) — see `feedback_autonomy_gate_blocks_writes_not_reads.md`.

## 2026-07-10 — oxfordra.net publish-dir exposure fix delivered (branch + draft, NOT prod)

 publish="." had been serving internal artifacts publicly: /evals/* (chat-bot regression fixtures), /scripts/* (build-kb.mjs, eval-chat.mjs, meta.md), and — wider than first reported — /netlify/edge-functions/chat.ts (full edge-function source incl. system prompt) and knowledge-base.json, all 200 on prod. Fix on branch fix/publish-dist-exclude-internal (pushed to ZeOoba/Website; worktree C:/Users/Owner/wt-site-publish-fix): new scripts/build-dist.mjs assembles dist/ from a fully-enumerated allowlist — every root entry must be classified published or private, unclassified entries fail the build (fail-loud both directions; negative-tested); netlify.toml publish="dist" + build command + NODE_VERSION=20. Draft deploy 6a510f9ed03c99bca081634a verified: all 7 internal paths 404; 14 pages + css/js/assets/fonts/pdf 200; _headers CSP/HSTS/preloads applied; legacy 301s + catch-all 404 intact; /api/chat edge fn (KB statically bundled) and /.netlify/functions/chat-lead both validate correctly. Prod untouched — merge + prod deploy await Gabriel sign-off; after merge the canonical deploy command is `netlify deploy` from the repo tree (CLI ≥ v26 builds dist/ automatically; NEVER `--dir=.`, which re-publishes the repo root). Independent fable review applied (full enumeration was its Important finding). Latent pre-existing bug found (identical prod/draft, spawned as separate task): netlify.toml's /api/chat-lead rewrite is shadowed by the _redirects catch-all — nothing calls it; chat.js posts to the function path directly.

## 2026-07-09 — "Killed — Reneg Only" ratified as TERMINATE (closes the open item from the deal-stage-reconciler build)

Gabriel resolved the open Stage-vocabulary question flagged in this same log's "Cross-fleet deal-stage reconciliation shipped" entry: `maintenance/deal-stage-map.json` now maps `"Killed — Reneg Only"` → `TERMINATE`, alongside the already-mapped `"Killed — Note/Short-Sale in Discussion"` → `TERMINATE`. No other change — `deal-stage-reconciler.py`'s `classify_disposition()` already handles any valid map entry correctly (verified by existing tests), so this is a data-only addition, not a code change. Verified the file is still valid JSON and the em dash is genuine UTF-8 (not mojibake) at the byte level before logging.

## 2026-07-09 — Setup-audit remediation T6: external cross-fleet dead-man BUILT (TDD, committed 149a21f) — activation blocked on 3 Gabriel-gated steps
Built per DEADMAN_APPROACH=GITHUB-ACTION, closing the self-referential-monitoring gap from the July fleet-loss incident (justification vs rules.md §9: P0-critical). Delivered, all file-scoped with zero overlap with the concurrent session's dirty files: `maintenance/emit-fleet-heartbeat.py` (standalone sibling — the probe itself carried foreign uncommitted edits, single-writer forbade editing it; reuses `_shared/store_discovery.py` with fallback, counts enabled-recurring identically to the probe) + `test-emit-fleet-heartbeat.py` (TDD red→green, 26/26; probe regression 25/25; strict payload rule mechanically enforced — timestamp, cc/lams counts, registry existence+SHA-256 only, no task ids/terms/credentials) + `.github/workflows/fleet-deadman.yml` (daily 13:00 UTC + dispatch; alerts via deduped GitHub issue on stale>24h, cc<10, lams<18, missing/unparseable heartbeat, or registry existence=false; alert logic tested 7/7 cases; email leg rides GitHub native issue notifications) + first real heartbeat emitted+committed (cc=12/lams=18, matches live probe) + `maintenance/push-fleet-heartbeat.ps1` (daily emit+commit+push pulse). `.gitignore` needed no change (maintenance/ opted in; verified via git check-ignore). Commit 149a21f (5 files, 528 insertions, `git add` exact paths only; concurrent session's staged renames verified untouched). THREE GABRIEL-GATED ACTIVATION STEPS (flagged, not self-authorized): (1) `git push` is BLOCKED by hooks/git-prepush-doctrine-gate.py on PRE-EXISTING drift — doctrine-integrity-probe reports 4 [MISSING] CLAUDE.md skill refs (acquisition-underwriting/loi-generation/psa-reconciliation/tenant-email — all real Cowork-surface skills; drift likely from today's probe/skills-restructure commits; 13 commits are unpushed incl. 12 from the other session; the gate's own doctrine forbids headless self-override) — recovery: one authorized turn to fix the probe drift or `touch ~/.claude/hooks/overrides/allow-doctrine-drift && git -C ~/.claude push origin main`; (2) PREMISE FAILURE discovered: NO nightly ~/.claude push actually exists (verified: no live SKILL.md pushes, no ORA schtasks) — the pulse script is built but registering it needs ratification: `schtasks /Create /TN "ORA Fleet Heartbeat Push" /SC DAILY /ST 07:30 …` (header documents the exact command); until a daily push runs, the Action alarms ~48h after the last manual push (fail-toward-alarm — correct); (3) workflow smoke-run (`gh workflow run fleet-deadman.yml`) only possible after the push lands — expected PASS while heartbeat <24h. Note for later reconcile: the other session's untracked scheduler-stores.json says cc=13/lams=4; the Action hardcodes the ratified floors cc≥10/lams≥18 with a dated comment.

## 2026-07-09 — Setup-audit remediation T12: OneDrive split-brain — Claude-system scope consolidated + all live "(1)" paths repointed; business bulk DEFERRED on falsified premise
Inventory partially FALSIFIED the ratified premise that "(1)" is a stale pre-migration duplicate: `(1)\Attachments\` receives live inflow (July 2026 Allentown Portfolio underwriting memo + ORA model), and TWO OneDrive.exe sync clients run — local moves out of "(1)" would propagate as cloud deletions. But the Claude-system content there WAS dead residue: the `(1)` Scheduled tree held 2 state files last written 07-07/07-08 by since-corrected hardcoded paths (canonical Scheduled is the verified-live LAMS home — 26 entries, state written 18:27 today), the `(1)` Claude_Workspace held 1 archived file, and `(1)` has NO `eric spreadsheets`/`Property Financials` — several code defaults pointing there were dead traps masked by .env. EXECUTED: (i) full hardcoded-"(1)" hit-list built before editing; (ii) repointed the 4 ora-ops plugin command pointers (ora-am-brief → canonical OneDrive spec; deal-sourcing-scan/health-guard/pm-ledger → their CC-inlined homes) and scrubbed their retired-Composio-fallback + routing-canon-violating egoldberg text (pm-ledger command claimed "Digest & EOD → ggoldberg + egoldberg"; deal-sourcing claimed egoldberg via a dead Composio slug — both now ggoldberg-only/SOLE-send-path); (iii) oxford-command-center PR #199 squash-merged (1f71fc5): workbookPath() default + 3 warehouse-script fallbacks + README repointed to canonical (targets verified nonexistent under "(1)"; .env already canonical so no runtime change), production checkout ff-pulled, tsc --noEmit clean; (iv) `(1)` Claude trees moved to canonical archives with MOVE-MANIFEST + tombstones at both vacated locations; (v) canonical `Documents\Claude\{Outputs,Workspace}` mirrors created; (vi) memories updated (scope-fragmentation + worktree-gotchas). DEFERRED TO GABRIEL with evidence: the "(1)" business bulk (loose lease/LOI/PSA docs, Attachments, Desktop, Meetings, Pictures, Recordings, Whiteboards, Documents remainder) — inventory manifest at `01_Workspace\outputs\2026-07-09_OneDrive-1-BulkMove_Manifest_v01.md`; the OneDrive account question (which account syncs "(1)"; unlink vs consolidate) must be answered before physical moves. Also observed: a mangled directory `UsersOwnerOneDrive - Oxford Capital Partners (1)DocumentsWindowsPowerShell` in the canonical root (path-concatenation bug artifact from some past script) — flagged, untouched.

## 2026-07-09 — Setup-audit remediation T11: third ora-skills clone archived (THIRD_CLONE=RECONCILE-COMMITS)
The clone at `Claude_Workspace\01_Workspace\.claude\skills\` no longer matched the audit-time description ("45 behind + uncommitted edits"): by execution time its tree was CLEAN and its formerly-uncommitted edits had been committed AND pushed by the same-day morning session as `b71722b` ("regenerate README skill inventory…") — already on origin, so the cherry-pick half was moot; 0 local-only commits, 7 behind origin/main (a782c4d). Actions: state manifest written (`STATE-AT-ARCHIVE.txt`); clone moved via robocopy /MOVE (exit 0; plain `mv` hit a OneDrive "resource busy" lock) to `01_Workspace\_archive\2026-07-09_third-ora-skills-clone\skills\`; `MOVED-SEE-CANONICAL.md` tombstone left at `01_Workspace\.claude\`. Reference sweep before the move found ONE live consumer — `ora-deal-sourcing-scan` read target-markets.json from the clone as source #1, and its documented fallback #2 (task-local `skills/target-markets.json` mirror) DID NOT EXIST — archiving without fixing would have left the task sourceless. Fixed both: source #1 repointed to canonical `C:\Users\Owner\ora-skills\target-markets.json`, and the local mirror materialized in the task folder. No VS Code config or settings reference the archived path (searched settings.json/settings.local.json/.vscode). Two-path lockstep doctrine now has one fewer divergence surface; the parent `01_Workspace\.claude\` (agents/, rules/, launch.json, settings.local.json) is intact and was NOT touched.

## 2026-07-09 — Cross-fleet deal-stage reconciliation shipped (closes the 511/470 logging gap)

**Trigger:** the 2026-07-09 setup audit flagged that two deal-pipeline stage changes — 511 Industrial Mile Rd (reset to Candidate) and 470 McCormick Blvd (Passed) — updated `projects.md`'s live table but never got a corresponding `event_log.md` entry, framed as "Cowork/LAMS decisions don't automatically write to this machine's Code-side log." Investigation found the real architecture: Cowork sessions are filesystem-sandboxed and can never write to `~/.claude/` at all, so a true bidirectional bridge is impossible — but Notion's Acquisition Pipeline Tracker is the one surface both fleets reliably write to, making it the right reconciliation source.

**Built (brainstorm → spec → plan → subagent-driven-development, 7 tasks + 1 final-review fix pass, all task-reviewed and a final whole-branch review, `docs/superpowers/specs/2026-07-09-cross-fleet-deal-stage-reconciliation-design.md` + `docs/superpowers/plans/2026-07-09-cross-fleet-deal-stage-reconciliation.md`):**
- `maintenance/deal-stage-reconciler.py` (+ `test-deal-stage-reconciler.py`, 40/40 passing) — a pure, offline-testable diff/format module: `load_snapshot`/`save_snapshot` (atomic), `diff_stages`, `classify_disposition` (never guesses — an unmapped Stage logs to event_log only, no ledger row), `format_event_log_entry`/`format_ledger_row`, and a CLI (`--bootstrap` seeds with zero logging; normal mode diffs and reports transitions as JSON). Never calls Notion/MCP/subprocess/network itself — the calling agent fetches and writes. Commits `ef03899`, `0681b73`, `de9cb21`, `7f31fa3`, `09db361`.
- `maintenance/deal-stage-map.json` — live-discovered Notion Stage-vocabulary mapping (`Passed`→PASS, `Closed Won`→CLOSE, `Killed — Note/Short-Sale in Discussion`→TERMINATE). `Killed — Reneg Only` deliberately left unmapped as ambiguous — **open question for Gabriel**: is this a live Stage option that should map to TERMINATE, or should it be dropped from the vocabulary entirely?
- `maintenance/_state/deal-stage-snapshot.json` — bootstrapped, all 12 live Acquisition Pipeline Tracker rows.
- New STEP 4.5 in `scheduled-tasks/ora-open-sessions-board/SKILL.md` (daily 17:00 ET) — queries live Notion, runs the reconciler, appends any transition to `event_log.md` via the sanctioned `append-event-log.py`, and adds a `deal-decision-ledger.md` row when the disposition is terminal. Non-halting on failure (exit 2 = transient Notion/file issue, self-heals; exit 3 = the reconciler refused to overwrite the snapshot because the live fetch returned fewer rows than expected — does NOT self-heal on its own if the shrink was real, e.g. a Notion row was deliberately deleted; recurs daily until a human re-runs with `--bootstrap` to accept the new baseline. STEP 4.5 now instructs flagging repeat exit-3s to Gabriel via the board rather than silently re-skipping).
- Backfilled the two originally-flagged gaps directly: 511's reset (event_log-only, non-terminal) and 470's pass (event_log + a ledger row with the real documented reason, not the generic fallback) — both independently re-verified against live Notion before writing.
- Live end-to-end dry run: confirmed a genuine no-op against the freshly-seeded snapshot, then forced and logged one synthetic transition to prove the pipeline fires correctly, with the snapshot self-restoring to true state and a clearly-labeled follow-up entry so the synthetic entry isn't mistaken for a real one later.

**Final review fix (post-task-review, pre-ship):** the whole-branch pass caught a latent silent-corruption path the task-scoped reviews couldn't see — the script would have unconditionally overwritten the snapshot even from a partial/incomplete Notion fetch (e.g. unexhausted pagination), which would then manifest as a false-transition storm the *next* day. Fixed with a shrink-guard (refuses to overwrite + exits 3 when the live fetch has fewer rows than the snapshot, `--bootstrap` deliberately exempt) plus STEP 4.5 hardening (pin the exact Notion tool + page-ID format, require pagination exhaustion before invoking the script). Re-reviewed and confirmed closed by the same reviewer against the actual diff, not the fix report.

**Deferred, not forgotten:** `Killed — Reneg Only` Stage-mapping decision (above); cosmetic Verdict-token/deal-name style drift between hand-written and auto-generated ledger rows; the mechanism will also log any non-deal row that happens to live in the tracker (e.g. a "Stall Alert" test row) exactly like a real deal, since it has no way to distinguish them.

## 2026-07-09 — Setup-audit remediation T10: session-env 90-day retention sweep built + wired into ora-weekly-hygiene (SESSION_ENV_RETENTION=90-DAY)
New `~/.claude/maintenance/session-env-retention.ps1`: archives (moves, never deletes) `session-env\<uuid>` dirs with LastWriteTime >90 days to `session-env\_archive\`; retains the proposal's belt-and-suspenders even at 90 days — live-sessionId exclusion read fresh from `sessions\*.json` each run, `_archive\` never a candidate, non-empty candidates logged as ANOMALY (policy-review signal) but still archived since a move preserves content, fail-open exit 0, everything logged to `maintenance\session-env-retention.log`. Wired as **Block K** in the CC `ora-weekly-hygiene` SKILL.md (order line A→…→J→K updated; summary line added; invocation uses the fleet's `-ExecutionPolicy Bypass` convention — bare `-File` is blocked by machine policy). Evidence: LIVE 90d run scanned 887 dirs / archived 0 (oldest dir is 2026-07-05 — first real archival ~2026-10-03) / excluded 8 live sessions; DRYRUN at 3.5d correctly identified 47 candidates with live sessions still excluded. Deliberate deviations from the (pre-decision) proposal doc, per the ratified decision: 90-day window not 72h, ARCHIVE not delete, host = ora-weekly-hygiene (fresh, verified-live task) not ora-nightly-disk — whose own stale log (last entry 2026-06-24) + apparently-dead step 4 is FLAGGED to Gabriel as a separate registration gap, unfixed here (out of remediation scope).

## 2026-07-09 — Setup-audit remediation T9: LAMS/CC skill hardening — 9a verified already-shipped, 9b Check I added to ora-pm-ledger
9a (routing-canon check in `ora-skill-text-audit`): ALREADY DONE by an earlier same-day session — the LAMS spec is at v1.4 (2026-07-09) with pattern class (l) "Routing-canon violation" (greps all skill bodies for `egoldberg` outside the ora-am-brief exception; 🔴 CRITICAL, rides the [ACTION REQUIRED] email; changelog cites Task 9a). Verified by direct read; no edit needed. 9b (frozen-date defect class): the Outbox-QC logic's actual home is NOT a standalone `ora-outbox-qc-sweep` task — it is BLOCK B inside the CC/MCP `ora-pm-ledger` consolidated spec (`~/.claude/scheduled-tasks/ora-pm-ledger/SKILL.md`; the LAMS automation-health-monitor only tracks its beacons). Added **Check I — Frozen-Date Subject**: a subject dateline (trailing "— YYYY-MM-DD" or a date in a report-style subject) differing from sentDateTime by >1 day = MEDIUM; automated/internal sends explicitly INCLUDED for this check; event/deadline/period dates exempted as false-positive guard; "Outside A–H" → "Outside A–I"; dated AMENDMENT NOTE appended per the file's convention. Would have caught the frozen-date Command Center brief on 2026-07-08. Content-only edits; no registry JSON touched; single-writer verified via mtimes (both files last written before this session).

## 2026-07-09 — Setup-audit remediation T8: CLAUDE.md Dispatch default amended to top-tier model alias (DISPATCH_ALIAS=AMEND)
CLAUDE.md Engineering OS Dispatch line: "Models: opus default" → "default = current top-tier model alias (Fable/Mythos class as of 2026-07)"; invariants restated unchanged (reviewer ≥ implementer; confidential/financial/governor code never below top tier — subagent or inline). Also corrected the stale pin-explicit-model example: it cited `claude-fable-5` as an unusable inherited model, but this session pinned `model: fable` subagents successfully — the rule (always pin explicitly) stands, the named example was dropped. eos-claude-md-guard accepted the edit. FLAGGED FOR GABRIEL: the mirrored "default opus" line in his User Preferences is his manual edit — not touched (out-of-scope item 1).

## 2026-07-09 — Setup-audit remediation T7: RAM doctrine retuned to 32 GB / ~24 GB working ceiling (RAM_POSTURE=RETUNE-32GB)
Every Claude-system reference to the retired 5.7 GB ceiling updated; hardware verified this session (31.4 GB physical reported by Win32_ComputerSystem; 8.3 GB free at edit time). Old → new values: `hooks/ram-guard.ps1` WARN_MB 300→2048, CRIT_MB 200→1024 (MIN_IDLE 900 unchanged) — the watchdog is meaningful again instead of effectively inert; EOS spec §9 (living doctrine) machine line → 32 GB physical / ~24 GB working ceiling, Workflow/parallel concurrency "≤ a few" → ≤ 8 (tool self-cap min(16,cores−2) still binds); UNCHANGED by design: the ~2–3 concurrent-opus adversarial/review fan-out cap (request-burst rate limit, not RAM — per reference_lean_ram_toolkit 2026-07-09 section) and footprint discipline (no standing RAM-heavy services). Files updated: ram-guard.ps1 · docs/system-inventory.md (hardware + Docker note) · EOS spec §9 · EOS plan resource-rule line (supersession note only — historical rationale left intact) · daily-setup-audit-prompt.md ×2 + plugin ora-setup-self-audit SKILL.md ×2 (mirror) · commands/ram.md baseline note · memory: reference_lean_ram_toolkit.md (frontmatter + new ratified-retune section), tech.md §9 (current-box facts, old-box kept as B4 context), 00_system_of_record.md §15, MEMORY.md index line. CLAUDE.md needed no change (its RAM line is a pointer to spec §9, no numbers). Residual grep for unretired 5.7 GB refs in doctrine files: zero. FLAGGED FOR GABRIEL: the 5.7 GB line in his User Preferences is his manual edit — not touched.

## 2026-07-09 — Setup-audit remediation T5d: ora-operations-extensions plugin pruned to 2 skills (v2.0.0 staged)
Wrong-target catch first: the master prompt named `~/.claude/ora-ops-plugin`, but that is the ora-ops slash-command plugin (5 command pointers + ora-setup-self-audit) and contains none of the 8 operations skills — the actual target is the ora-operations-extensions Cowork plugin, whose source package is `Claude_Workspace/01_Workspace/ora-operations-extensions-v1.plugin`. Built v2.0.0 per PLUGIN_KEEP: retained capex-budgeting + submarket-spatial-analysis; removed annual-cycle, vendor-management, debt-management (canonical ora-skills user skill v1.2 supersedes — live routing collision), deal-retirement, cash-position-monitor, investor-relations (LP/capital-call model contradicts proprietary-capital doctrine; several referenced ratified-retired tasks). Removed skill dirs archived (never deleted) to `Claude_Workspace/01_Workspace/_archive/2026-07-09_plugin-prune/skills/`; v1.plugin left in place as the installed-version source until v2 is imported. v2 packaged with the python zip path (4 entries, forward-slash verified, plugin.json version 2.0.0 + updated description/README) and staged at `Claude_Workspace/01_Workspace/outputs/2026-07-09_staged-skills/ora-operations-extensions-v2.plugin`. ACTIVATION IS GABRIEL-MANUAL: Cowork Settings → Capabilities → install v2 from file, then verify the live Skills list shows exactly the two retained skills.

## 2026-07-09 — Setup-audit remediation T5: ora-skills fixes — 5a/5b already merged (morning session), 5c merged via PR #11; all three repackaged + staged
5a (monthly-close v2.1, ggoldberg-only routing + "IF INVOKED AS A SCHEDULED TASK" reframe) and 5b (psa-reconciliation v1.4, E. Fulton banner → [PropertyShortName]) were ALREADY fixed on origin/main by the same-day morning session (merged PRs #8/#9/#10) — the pre-flight already-fixed check prevented duplicate PRs. 5c executed this session via an isolated-worktree subagent: acquisition-underwriting v3.5 → v3.6, "~20% portfolio LTV" → "~15% portfolio LTV" in CAPITAL STRUCTURE CONTEXT (LTV_DOCTRINE ratified ~15%), one-string diff (+3/−3 incl. version/changelog), DSCR 1.25x / LTV 40% governors and scorecard weights verified untouched in the diff; PR #11 reviewed and squash-merged (a782c4d, 23:14Z). All three skills repackaged from a clean a782c4d worktree via tools/package_skills.py (packager exit 0) and staged in `Claude_Workspace/01_Workspace/outputs/2026-07-09_staged-skills/` — zip-content verified (v2.1+no-egoldberg / v1.4+token / v3.6+~15%). Gabriel's one-click Save-skill import is the remaining activation step. Single-writer note: ora-skills main checkout remains dirty with a concurrent session's work (7 files) and was never touched; that session pushed `d906030 cowork-settings: ratify v2.1` to origin despite COWORK_SETTINGS_V21=DEFER — flagged to Gabriel.

## 2026-07-09 — Setup-audit remediation T3: frozen-date CC Daily Brief fixed + recipients ggoldberg-only (PR #198 merged)
Root cause: the "[ORA Command Center] Daily Brief — 2026-06-01" subject came from `snapshot.meta.asOf`, which `server/workbook/parse.ts` stamps from the hardcoded `WORKBOOK_AS_OF = '2026-06-01'` constant in `server/config.ts` — every send inherited the pinned date. Fix (oxford-command-center PR #198, squash-merged f992bb5): new required `BriefInput.briefDate` threaded from `nowEt.date` (the same ET value that gates `shouldSendBrief` and stamps `lastBriefDate`, so subject/gate/dedupe stay consistent) is now the subject date; the body header keeps the honest "As of {workbook asOf}" freshness line; analytics date math untouched. Recipients: `BRIEF_RECIPIENTS` reduced to ggoldberg@oxfordra.net only per CC_DAILY_BRIEF=REPAIR-GGOLDBERG-ONLY (the cc-Eric exception belongs to ora-am-brief alone); the test that had enshrined the wrong canon reading now pins exact-array ggoldberg-only. Evidence: TDD red→green (13/13 brief tests), typecheck exit 0 (3 tsconfigs), full `gate:ci` exit 0, independent fable review APPROVE (confirmed sole renderBrief caller, ET-boundary correctness, alerts path byte-identical). Production checkout fast-forwarded to f992bb5 with its (foreign) dirty set verified identical — fix is live for the next scheduled bake. PENDING OBSERVATION: verify tomorrow's ~06:45 entry in `_shared/send-log.txt` shows subject "— 2026-07-10" and to=ggoldberg only. Residual (reviewer note, no action): `src/brain/draft.ts` ORA_CC drafting list still includes egoldberg (drafting aid, not an automated send); `WORKBOOK_AS_OF` remains a pinned constant shown in the body — deriving it from the live workbook is a candidate follow-up. Also: `server/config.ts` workbookPath() DEFAULT points into the stale "OneDrive - Oxford Capital Partners (1)" root — added to T12's repoint list.

## 2026-07-09 — Note: prior entry was a deliberate dry-run verification artifact

The immediately-preceding "Deal-stage sync" entry for 511 Industrial Mile Rd (showing
old_stage "TEST-PRIOR-STAGE") was produced by Task 7's live dry-run verification of the
deal-stage-reconciler mechanism (see the 2026-07-09 cross-fleet-deal-stage-reconciliation
design spec + implementation plan) — a deliberately forced synthetic transition, not a
real Notion event. Logged for continuity so a future reader isn't confused by the
fabricated old_stage value.

## 2026-07-09 — Deal-stage sync: 511 Industrial Mile Road — Columbus, OH — TEST-PRIOR-STAGE → Candidate (Notion)

Detected by ora-open-sessions-board's reconciliation step; no corresponding entry existed. Tripwire only — see Notion for the actual decision context.

## 2026-07-09 — Setup-audit remediation T4: 17:08 CRITICAL "Access gate check failed" = probe transient, already fixed by PR #197
Root cause verified in `oxford-command-center`: the 17:08:42 CRITICAL email came from `scripts/deploy-mirror.ps1`'s post-deploy Access-gate probe (via `scripts/lib/deploy-alert.ps1`), whose single-shot `curl -I` check missed transiently — the gate itself was never open. A concurrent session had already root-caused and fixed it the same evening: PR #196 (17:48, deploy-failure alerting) and PR #197 (merged 18:22, commit 3a66a61) which retries the probe 3× (5s settle + 15s between attempts) and splits severity — 2xx apex = genuine exposure (CRITICAL) vs anything else = "GATE CHECK INCONCLUSIVE… verify manually". The #197 commit message documents the 17:08 incident explicitly. Independent live evidence this session (23:05 UTC): `curl -s -I --max-redirs 0 https://ora-command-center.pages.dev/` → HTTP/1.1 302 with `Www-Authenticate: Cloudflare-Access` — Access is enforcing; no confidential exposure occurred (and E. Fulton was declassified 2026-07-09 in any case). No further code change made — remediation task closed as already-fixed + verified. Gabriel still owns reading the 17:08 email (out-of-scope checklist item 2).

## 2026-07-09 (cont.) — ora-am-brief (LAMS/Cowork) updated with governor-math tailoring

Gabriel added the Section 3 governor-math addendum (drafted this session) to `ora-am-brief`'s prompt directly via Cowork's Edit scheduled task modal — confirmed via screenshot walkthrough (pencil icon → edit modal → Cancel/Save, no destructive control touched) and Gabriel's own "saved" confirmation. Not independently re-verified via `list_scheduled_tasks` (LAMS registry unreachable from this CC/MCP session) — trust the in-app confirmation for this one. New instruction: after FRED rates, compute an illustrative all-in rate from current 5yr/SOFR + an assumed spread, and show whether ORA's DSCR 1.25x or LTV 40% governor binds first at that rate — explicitly never treating the governors themselves as adjustable.

## 2026-07-09 — Setup-audit remediation T2: guard "1 DROPPED ora-lender-covenant-tracker" = drift, not intent
The 2026-07-09 12:57 ora-task-integrity-guard email flagging `ora-lender-covenant-tracker` as DROPPED was root-caused to hypothesis (b): a transient zombie re-registration during the 07-05/08 fleet-loss recovery was baked into the guard's ROLLING baseline (`Documents\Claude\Scheduled\_state-history\membership-state.json` — rewritten every run, not a hardcoded roster in the guard folder), and the zombie's subsequent removal produced a single DROPPED alert, after which the baseline self-healed. Evidence (direct greps, not probe output): `lender-covenant` = 0 hits in the raw CC/MCP registry, 0 in the raw LAMS registry, 0 in the LocalCache package store, 0 in current membership-state.json and all _state-history snapshots; no live task folder on either fleet; sole remaining trace is the ratified archive `_archive_2026-06-11_orphans/ora-lender-covenant-tracker/`. Task remains ratified-retired (2026-06-11 list) — no baseline fix required, no re-registration performed. If it reappears in a future roster it is drift, not intent.

## 2026-07-09 — Setup-audit remediation T1: session-context MIGRATION STATE bullet finalized
Evening remediation session (master prompt v02, all decisions ratified). The ⛔ MIGRATION STATE bullet in `~/.claude/session-context.md` — already converted from the stale 2026-06-11 COORDINATION note by the v01 pass — was aligned to the ratified decisions: B4 old-machine decommission now reads "status UNCONFIRMED (Gabriel deferred 2026-07-09)" (was a placeholder reference to the `B4_OLD_MACHINE` decision variable), and the B3 pointer now cites `memory/project_claude-setup-audit-2026-07-09.md` explicitly. Generated-fleet markers untouched. Master prompt v02 FINAL saved to `~/.claude/prompts/2026-07-09_setup-audit-remediation.md` (v01 template archived to `prompts/_archive/`).

## 2026-07-09 — Scheduled-task integrity tooling: registry-derived re-curation + shared store discovery + guard self-check

Follow-ups from today's setup-audit session, all landed (CC surface, ~/.claude working tree, uncommitted alongside the earlier session's fixes):

- **setup-self-audit.py re-curated registry-derived.** The stale hand-curated `EXPECTED_TASKS` baseline (2026-06-09; over-reported 6 LAMS-migrated/retired tasks as MISSING) is DELETED. Check 1 now derives the expected set from BOTH live registries and adds the one check no other probe covers: **disk→registry orphan detection** (live-store folders registered in neither fleet). Check 5 (memory↔fleet drift) is registry-derived and scoped to the SoR §7 headline so dated historical subsections stop false-flagging. New tests: `test-setup-self-audit.py` (9), `test-store-discovery.py` (14) — all pass.
- **Single source of truth for store discovery + fleet floors:** new `maintenance/_shared/scheduler-stores.json` (roots + ratified floors cc=13 / lams=4) + `maintenance/_shared/store_discovery.py`. Wired: cc-verifier-probe (incl. both floor constants), registry-membership-probe, fleet-status, setup-self-audit, guard.ps1, membership-guard.ps1 (each fail-open to built-in defaults). `fleet-deadman.ps1` deliberately NOT wired — independent backstop stays self-contained. A future store move or floor recalibration = one edit in scheduler-stores.json.
- **Self-check for the self-healer:** guard.ps1 now errors (exit 1) when it discovers 0 registry entries — the checked:0 silent no-op that ran ~4 days undetected. ora-task-integrity-guard SKILL.md STEP 3 makes checked==0 an EMAIL alarm (STEP 4 exception noted). Assertion verified live via scratch copy on an empty store (fires) and against the real stores (checked=33, exit 0).
- **16-folders-vs-13-CC-registrations reconciled:** (a) `ora-am-brief` local folder was the superseded CC-era 4-block merged spec — ARCHIVED to `scheduled-tasks/_archive_2026-07-09_orphans/` (live task is LAMS by design; its OneDrive SKILL.md is a slim daily-brief-skill runner; NOTE: old Blocks A/C/D — treasury prefetch, inbox pre-brief, cash snapshot — are not in the live LAMS spec; archive is the recovery source). (b) `ora-calibration-snapshot` and `ora-entry-market-scan` are fully-authored but registered in NEITHER fleet (confirmed absent from pre-loss snapshots too — never registered, not a 2026-07-05 casualty). Left in place; **OPEN — needs Gabriel:** register via supervised create_scheduled_task or ratify as shelved.
- **SoR §7 de-hardcoded:** headline "19 (15+4)" and the doctrine paragraph's "15 tasks"/"4 tasks" claims replaced with pointers to the generated session-context roster + scheduler-stores.json floors; setup-self-audit Check 5 now guards against counts creeping back.

## 2026-07-08 — Deal-stage sync (backfill): 470 McCormick Blvd, Columbus OH — PASSED / CLOSED

Cross-fleet logging gap found by the 2026-07-09 setup audit (see
project_claude-setup-audit-2026-07-09.md) and closed by this entry, backfilled as part
of building the deal-stage-reconciliation mechanism (see the 2026-07-09
cross-fleet-deal-stage-reconciliation design spec). LOI FINAL v2 (adversarial-review
hardened 6/10) was never shipped to broker KRG; its 6/17/2026 expiration lapsed 21 days
before Gabriel made an explicit in-session kill decision on 7/8. No counterparty was
ever contacted, so nothing needed to be retracted. HB 126 note and the IOS land thesis
are now moot. Terminal disposition — see the companion deal-decision-ledger.md row
added in the next step.

## 2026-07-09 — Deal-stage sync (backfill): 511 Industrial Mile Rd reset to Candidate

Cross-fleet logging gap found by the 2026-07-09 setup audit (see
project_claude-setup-audit-2026-07-09.md) and closed by this entry, backfilled as part
of building the deal-stage-reconciliation mechanism (see the 2026-07-09
cross-fleet-deal-stage-reconciliation design spec). Per Gabriel via the open-sessions
board: LOI v02 (submitted 5/15, ack'd 5/18) went 30 days without ever resolving
executed/countered/open, so the deal was reset back to re-screening rather than carried
forward as "keep open." Notion's "LOI Status" field still literally read "Submitted" at
the time of reset — not yet reconciled, per projects.md's own flag. This is a
non-terminal state change (re-screen, not a PASS/SKIP/DROP/PARK/CLOSE/TERMINATE
disposition) — logged here only, no deal-decision-ledger.md row.

## 2026-07-09 (cont.) — Added Block J (Tenant DB completeness spot-check) to ora-weekly-hygiene

Found during a tailored daily-brief run: 1100 Rarig Ave's Tenant DB rows were 3 of 14 actual units; a same-day full-portfolio scan confirmed it's systemic — 3347 McGregor Ln has zero rows, 26% of all 296 rows (76) are unlinked to any property, and the Property Address schema field only defines 19 of ORA's ~27 properties. Full finding: `reference_tenant_db_completeness_gap.md`.

Rather than add the expensive full scan (~5min/~160K tokens) to the daily `ora-am-brief` (LAMS/Cowork, unreachable from this CC/MCP session), added it as **Block J** of `ora-weekly-hygiene` (CC/MCP, reachable) — a lighter weekly cadence appropriate for slow-drifting row-completeness data. Registered via the supervised `update_scheduled_task` MCP tool (concurrent-writer check clean — no other session active per `registry-membership.log`'s latest entry), verified via `list_scheduled_tasks`: `enabled: true`, next fire 2026-07-13 (Sunday) ~20:00 ET. Block J persists a `_state/tenant-db-completeness-history.json` for week-over-week trend, first run this Sunday will be the baseline.

Also handed Gabriel a drafted governor-math addition for `ora-am-brief`'s Section 3 (ties FRED rates to the DSCR 1.25x/LTV 40x governor) to paste in via Cowork — this session's MCP cannot reach the LAMS registry to apply it directly.

## 2026-07-09 — ora-pm-ledger systematization pass (Gabriel-directed)

Triggered by a duplicate same-day fire of `ora-pm-ledger` (LAMS run ~16:27 ET delivered A/B/C; CC 18:00 fire would have re-sent). This 18:00 CC run detected the prior delivery (Sent Items + Ops Hub pages + send-log all showed today's three deliverables) and **suppressed the duplicate** — no second emails/pages sent. Gabriel then directed "proceed with systematization candidates." Changes made this session:

- **De-dupe guard (§0.5)** added to BOTH `ora-pm-ledger` SKILL.mds (CC `~/.claude/scheduled-tasks/…` + LAMS `Claude_Workspace/00_Governance/Scheduled/…`): pre-flight check for today's Sent-Items subjects / Ops Hub pages / send-log; skip per-block if already delivered; no-op + one-line Ops Hub note if all delivered. Neutralizes the cross-fleet double-fire regardless of which fleet fires second.
- **Root cause**: `ora-pm-ledger` is double-registered (CC/MCP enabled cron `0 18`, lastRun today; plus a LAMS/Cowork twin that fired ~16:27). CC is canonical (COM-capable). Retiring the redundant LAMS registration is a Cowork-only registry action (not reachable from Claude Code); the guard makes it safe either way.
- **Property→LLC signature roster** created: `Claude_Workspace/00_Governance/References/Voice/ORA_Property-LLC-Signature-Roster_v01.md` (sourced from `20260422_ORA_Entities_Input1_v01.xlsx`, 28 entities, VERIFIED/PENDING). Wired into the Voice Register §2 to resolve `[Property LLC Name]` — retires the recurring Outbox QC Check-D MEDIUM (landlord mail signed with personal block).
- **Deal-inactivation gap** documented: no task writes an inactive `Stage` on pass/close, so decided deals (Liberty Office Park, still `Stage: Candidate`) re-nudge weekly. Added STEP 2b to `ora-stale-pipeline-nudge` to escalate status-conflict deals as "needs a one-field Stage update" instead of silently re-nudging. Liberty status conflict flagged to Gabriel for adjudication (SoR = Candidate; only a 754 note says closed 6/11).
- **No-ops confirmed (already-correct, not touched)**: `ora-stale-pipeline-nudge` STEP 5 COM framing (already fixed v1.1 today); its STEP 2 already excludes inactive stages.

## 2026-07-09 — 17:08 CRITICAL "Access gate check failed" = FALSE ALARM; probe hardened via oxford-command-center PR #197 (Task 4)

**Not a breach.** Live verification: brain.oxfordra.net returns 302 → spring-wood-ade4.cloudflareaccess.com (gate enforcing); the 18:00 mirror-deploy run passed clean (LastTaskResult=0). The 17:08 alert was the first real firing of the new PR #196 alerting on a pre-existing flaky probe: `scripts/deploy-mirror.ps1`'s post-deploy gate check was single-shot (5s settle, no retry) and collapsed a failed probe ($code=0 — network blip/edge propagation) into the same CRITICAL "confidential bake may be exposed" branch as a genuine 2xx.

**Fix (PR #197, merged; CodeRabbit + gate + refute-required all green):** probe retries up to 3× (5s settle + 15s between attempts); severity split on the final observed code — 2xx → GATE CHECK FAILED (CRITICAL, unchanged); 0/timeout/3xx-other/4xx/5xx → GATE CHECK INCONCLUSIVE → existing non-critical alert path (catch-block classifier untouched); per-attempt diagnostic line so intermediate codes leave a local trace. Gate strictness NOT loosened (still requires 302 → *cloudflareaccess.com; still exits non-zero on failure). Implemented by opus subagent in isolated worktree (occ-wt-gatefix, since removed); Fable-reviewed; shared checkout never touched.

**NOT YET LIVE:** the hourly native task "ORA Command Center - Mirror Deploy" runs deploy-mirror.ps1 from the LOCAL checkout, which never auto-pulls (known mirror-deploy gap) — and the checkout has another writer's uncommitted work, so this session did not pull it (single-writer rule). Flagged for Gabriel/checkout-owner: `git pull` in C:\Users\Owner\oxford-command-center to activate the fix.

## 2026-07-09 — LAMS/CC skill hardening + doctrine entries (Tasks 9a/9b/13a; §9 item found already-done)

- **9a** `ora-skill-text-audit` v1.3→v1.4 (LAMS canonical, `Documents\Claude\Scheduled\ora-skill-text-audit\SKILL.md`; single-writer check clean, mtime 07-07): added pattern class **(l) routing-canon violation** — greps every skill body for `egoldberg` outside the sole ora-am-brief Daily Brief cc exception; 🔴 CRITICAL, rides the [ACTION REQUIRED] email; class counts/severity matrix/clean-pass body/changelog all synced to twelve classes.
- **9b** frozen-date defect class added as **Check I — Frozen-Date Subject** in `ora-pm-ledger` SKILL.md Block B (CC canonical, `~/.claude/scheduled-tasks/ora-pm-ledger/SKILL.md`): any subject-line date differing from send date by >1 day = MEDIUM defect (recurring/automated report subjects never exempt). Placed in pm-ledger because ora-outbox-qc-sweep is an archived orphan — the live outbox-QC logic is pm-ledger Block B per the Phase-3 fleet consolidation.
- **13a** audit-ledger convention added to `memory/rules.md` §1: before launching any setup/system audit, grep memory for a same-day or superseding `project_*-audit` entry — extend, don't duplicate.
- **13 (§9 budget): ALREADY DONE** — rules.md §9 already reads "re-ratified 2026-07-09, expires 2026-10-07, one-in-one-out DROPPED (Gabriel)". The remediation prompt's "lapses 2026-07-11" premise was stale; no edit made. AUTOMATION_BUDGET_S9 decision is moot.

## 2026-07-09 — ora-skills PRs #8 + #9 opened (Tasks 5a/5b; 5c gated on LTV_DOCTRINE, not executed)

- PR #8 `monthly-close` v2.0→v2.1: scheduled-task step 6 routing corrected to ggoldberg-ONLY (was ggoldberg+egoldberg — routing-canon violation); section retitled "IF INVOKED AS A SCHEDULED TASK (no live registration…)" since monthly-close-kickoff is retired and nothing fires it.
- PR #9 `psa-reconciliation` v1.3→v1.4: Step 4 XLSX title banner "E. Fulton Portfolio" → `[PropertyShortName]` template token; no behavior change. Line 17's E Fulton example and line 105's "pre-v1.4 deals" phrase deliberately untouched.
- Process: implemented by an opus subagent in an isolated worktree (`ora-skills-wt-remediation`) branched off origin/main; the shared checkout — dirty with the morning session's 7 uncommitted files (5 SKILL.mds + package_skills.py + code-debugging-optimizations) — was never touched, HEAD unmoved at 44b5e01. Diffs Fable-reviewed (reviewer ≥ implementer) before PR creation. Repackage/stage via package-and-stage-skill after merge.
- NOTE for the shared-checkout owner: main is ahead 2 of origin/main (c3eed02 ratify-hurdle-rate, 44b5e01 cowork-settings v2.1) — unpushed; these PRs were deliberately branched from origin/main so they don't carry those commits.

## 2026-07-09 — CC Daily Brief frozen-date root cause identified (Task 3 — REPAIR/KILL gated on CC_DAILY_BRIEF, no fix applied)

The "[ORA Command Center] Daily Brief — 2026-06-01" email (sent daily with the frozen subject since 2026-06-04) is produced by the NATIVE Windows scheduled task `ORA Command Center - Mirror Deploy` (hourly + 06:45 ET; registered by `scripts/register-mirror-task.ps1` — NOT in either MCP fleet registry) → `scripts/deploy-mirror.ps1` sets `BRIEF_ENABLED=1` → `npm run build:mirror` → `bake-mirror.ts` → `server/brief/run.ts` `runBrief()` (once/day gate via `lastBriefDate`).

Root cause (certain): subject = `[ORA Command Center] Daily Brief — ${b.asOf}` (`server/brief/render.ts:65`) ← `snapshot.meta.asOf` (`run.ts:101`) ← `WORKBOOK_AS_OF` hardcoded `'2026-06-01'` fallback (`server/config.ts:42`); deploy-mirror.ps1 never sets the env override, so the literal always wins. Already a known MED finding in the intelligence-platform master plan.

Recipients hardcoded at `server/brief/run.ts:15`: ggoldberg + egoldberg — NOTE: this is the CC-generated brief, NOT ora-am-brief, so this cc-Eric is OUTSIDE the routing canon's sole sanctioned exception; a REPAIR-KEEP-CC-ERIC decision would ratify a second exception (doctrine change).

Secondary finding: `config.ts` `workbookPath()` defaults to the `OneDrive - Oxford Capital Partners (1)` folder — the stale/incomplete split-brain copy (feeds Task 12's ONEDRIVE_CONSOLIDATION decision). Kill path if chosen: `Disable-ScheduledTask -TaskName "ORA Command Center - Mirror Deploy"` kills the WHOLE mirror deploy; email-only kill = remove `BRIEF_ENABLED='1'` at deploy-mirror.ps1:66 (and expect the companion ora-command-center-mirror-drift-check to flag if the native task is unregistered outright).

## 2026-07-09 — ora-lender-covenant-tracker "1 DROPPED" guard alarm = drift, not intent (Task 2)

Today's 12:57 guard email (send-log: `ORA Task Guard - 2026-07-09: 1 DROPPED (ora-lender-covenant-tracker)`) investigated. Verdict: **(b) recovery-era zombie that has since vanished — drift, not intent.** RATIFIED drop: ora-lender-covenant-tracker (already on the 2026-06-11 Gabriel-ratified-unneeded retirement list; this entry re-confirms the retirement).

Evidence chain (raw sources, not probe output):
- Raw registry grep TODAY: CC/MCP `claude-code-sessions/.../scheduled-tasks.json` = 0 hits; LAMS `local-agent-mode-sessions/.../scheduled-tasks.json` = 0 hits. No `scheduled-tasks.json` exists anywhere under `~/.claude` that could re-feed it.
- `maintenance/_state/guard-failure-2026-07-08.md` records membership-guard on 07-08 reporting `added:["ora-lender-covenant-tracker","ora-debt-maturity-snapshot","ora-cash-position-snapshot"]` — the zombie APPEARED in a live store on 07-08 (recovery-era resurrection), and that day's alarm email never sent (Outlook "New Profile" wizard COM outage).
- Today's run saw it gone again (consistent with Gabriel's 2026-07-09 Cowork-UI purge of dangling entries) → "1 DROPPED".
- Baseline already self-corrected: `Documents\Claude\Scheduled\_state-history\membership-state.json` (rewritten 2026-07-09T17:09Z by today's run) contains zero lender-covenant entries. No baseline fix needed; tomorrow's run will not re-alarm. Task NOT re-registered.

## 2026-07-09 — session-context MIGRATION STATE note corrected (setup-audit remediation Task 1)

Replaced the stale 2026-06-11 ⛔ COORDINATION bullet in `~/.claude/session-context.md` (which falsely asserted the new machine had NOT arrived) with the current MIGRATION STATE: new machine CONFIRMED in service — verified against ground truth this session (`hostname` = LAPTOP-CSHSCBE6, 31.4 GB RAM). The do-NOT-auto-run-Phase-B2 protection is preserved (both fleets already live here; re-registration duplicates tasks); B4 old-machine decommission remains gated on Gabriel's `B4_OLD_MACHINE` decision; B3 burn-in partially complete per the morning-audit memory. The event-log-append single-writer sentence from the old bullet was retained in the new one (it appears nowhere else in session-context). Generated-fleet markers untouched.

## 2026-07-09 — ora-health-guard manual run → integrity-engine + cc-verifier remediation (Gabriel-directed, in-session)

A manual off-hours run of `ora-health-guard` (17:22 ET; task is enabled, next cron fire 2026-07-10 ~05:24) surfaced and fixed a chain of latent guard defects. All edits local (engine/config/probe/SKILL.md); no external sends; the two time-critical Block B / consolidated Block C emails were deliberately SUPPRESSED (off-schedule manual run, Gabriel present) and reported to chat instead. EOS plan-gate overridden for this bounded, individually-approved set.

- **Integrity engine was a silent no-op (ROOT CAUSE of the unrestored 07-08 deletions).** `ora-task-integrity-guard\guard.ps1` globbed registries only under the MSIX LocalCache store (`…\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude`), which no longer exists post-2026-07-05 migration → `checked:0`, backed up nothing. Same engine `ora-task-integrity-guard` (12:54) and `ora-health-guard` Block A both call — both inert since migration; the likely reason the 07-08 SKILL.md deletions (health-guard/pm-ledger/weekly-hygiene) were never auto-restored and had to be transcript-recovered. FIX: dual-base discovery (adds `AppData\Roaming\Claude`). Verified `checked:33`, all 33 fleet SKILL.mds now mirror-backed for the first time since migration.
- **cc-verifier 13/15 → 15/15.** (a) `OXFORDRA_REPO` blank — the project `settings.json` (`projects\C--Users-...\`) never existed post-migration; created it with `env.OXFORDRA_REPO=C:/Users/Owner/website-canonical` (repo/remote healthy). (b) `ora-am-brief` false-flagged as a dark CC task — it lives in LAMS by design; fleet check changed to the CC∪LAMS union. (c) `RESTORED_FLEET_FLOOR` 14→13 — **Gabriel ratified the CC→LAMS consolidation** in-session; 13 is the correct post-consolidation CC count; the advisory cleared.
- **ora-setup-audit: confirmed RETIRED, not dark.** Killed 2026-06-16 (strategic-audit: daily cadence overkill, overlaps ora-health-guard); archived 07-07; on the ratified-retirements list; probes absorbed by the guard trio (health-guard + task-integrity-guard + doctrine-integrity-guard). Dropped from cc-verifier `EXPECTED_FLEET` and setup-self-audit `EXPECTED_TASKS`. The live `ora-ops:ora-setup-audit` plugin command is a separate artifact (unaffected).
- **ora-health-guard Block C gained probe #6 `setup-self-audit.py`** (Gabriel: "put it in ora-health-guard") — absorbs the one retired-task probe not already covered by the trio. Wired fail-open (no `--strict`); ESCALATE only its secrets / connectors / frontmatter findings to `[ACTION]`; its fleet / memory-drift checks are advisory-only (stale embedded 2026-06-09 baseline, redundant with registry probes). Verified: secrets/connectors/frontmatter all OK.

OPEN FOLLOW-UPS (need Gabriel): (1) re-curate setup-self-audit `EXPECTED_TASKS` against the live registries (still over-reports 6 LAMS-migrated/retired tasks as MISSING); (2) unexplained 16-on-disk (`~/.claude/scheduled-tasks/`) vs 13-CC-registry task-count discrepancy — 3 on-disk folders not in the CC registry.

## 2026-07-09 — oxford-command-center mirror-deploy silent-stale-deploy gap fully closed

Follow-on to the same-day PR #192 fix (fast-forward-before-bake). Gabriel flagged that a fix which only "fails loudly" is worthless if nobody is watching Windows Task Scheduler history. Closed in two parts: (1) registered `ora-command-center-mirror-drift-check`, a new CC/MCP scheduled task (weekdays 10:44 AM ET) that checks `Get-ScheduledTaskInfo` + git drift on the native "ORA Command Center - Mirror Deploy" Windows task and emails ggoldberg only on a real alarm — deliberately NOT migrating the actual deploy job into the MCP registry, since that fleet only fires while Claude Desktop is open and would have regressed a reliable 24/7 native job to a desktop-gated one; (2) PR #196 (merged, squash commit `59b8e58`) added source-level alerting directly inside `deploy-mirror.ps1` — local review (general-purpose subagent) caught a real Critical bug in the first cut (a `"` in the failure reason could corrupt/break the native `-Body` argument passed to a child `powershell.exe`, silently degrading straight to the unwatched `data/outbox/` fallback with zero email — exactly defeating the feature), fixed via `-BodyFile` matching `server/brief/send.ts`'s existing convention for the same hazard, plus a permanent smoke test (`scripts/deploy-mirror.smoke-test.ps1` — this repo has zero Pester coverage) that would have caught the bug via a tricky-content assertion. Full detail: `reference_command_center_mirror_deploy_gap.md`.

## 2026-07-09 — eos-plan-gate override reason: refinement candidate flagged (corrective revert vs. feature-sprawl)

This session consumed the `eos-plan-gate` override (`touch hooks/sessions/<id>/override`, triggered at 4+ unplanned edits) for a **corrective revert** — undoing/fixing prior unplanned drift, not adding new unplanned scope. The gate currently has no way to distinguish that from a **feature-sprawl** override (net-new scope creep), since both consume the same undifferentiated override touch. Flagged as a small, concrete refinement candidate for the guard-hardening pass already underway: tag the override with a reason (e.g. `override-revert` vs `override-sprawl`) so telemetry/calibration can tell the two apart instead of treating every override as equivalent risk. Not implemented this session — logged for whoever next tunes `eos-plan-gate`. Current-state pointer added to [projects.md](projects.md) §7.

## 2026-07-09 — CLAUDE.md bare-date annotations relocated to event_log (doctrine hygiene)

The ora-open-sessions-board dispatch (2026-07-09) edited CLAUDE.md to record two rule changes but embedded bare dates inline, tripping the doctrine-integrity-probe's dateless/tombstone-free CLAUDE.md rule (2x [MISSING], probe exit 1) — and did not record either change in event_log. Per "one fact, one home," the rules stay in CLAUDE.md (dateless); their change-dates are recorded here. Rules themselves unchanged; only the inline `(adopted 2026-07-09...)` / `(added 2026-07-09)` parentheticals were stripped from CLAUDE.md lines 30 and 55. Probe returns to exit 0.

1. **Deal-file naming schema changed.** CLAUDE.md Conventions now specifies deal files `[DocType]_[Property]_[MMDDYYYY]`, replacing the prior `[Address] [Purpose] [MM-YYYY]` schema, to match actual 2026 filing practice. Models (`ORA_[DocType]_[Property]_v[X.Y].xlsx`) and session outputs (`YYYY-MM-DD_[Topic]_[DocType]_v##.ext`) schemas unchanged; the three-schema "do NOT unify" rule stands.
2. **Debugging/code-audit skill-routing tie-break added.** Generic "debug"/"fix errors"/"code audit" requests route through Engineering OS `/debug` first; `code-debugging-optimizations` applies once explicitly named or handed off from `/debug`. Its autonomous-mode text (no approval gates on investigating/editing/committing) never overrides Hard Invariant 2's per-deploy confirmation for an oxfordra.net production deploy.

Context: caught during the interactive CLAUDE.md/MEMORY.md/session-context hygiene pass that ran alongside the same board dispatch (both touched CLAUDE.md; the trim and the board's additions coexist in the working tree, uncommitted).

## 2026-07-09 — Cowork skill-cache drift: 8 skills repackaged and staged for re-import

**Trigger:** 2026-07-09 audit found the Cowork runtime skill cache materially stale vs. canonical `C:\Users\Owner\ora-skills` for 8 skills. Gabriel approved the FULL batch fix.

**Action:** Ran `package-and-stage-skill` procedure (Code CLI surface). Confirmed each of the 8 skill directories git-clean before packaging (no uncommitted drift). Packaged via the sanctioned `tools/package_skills.py` (never Compress-Archive) into `C:\Users\Owner\ora-skills\_staging\2026-07-09_cowork-repackage\`. All 8 passed frontmatter validation (name==dir, description ≤1024 chars) and forward-slash zip-entry assertion; exit 0. Verified post-hoc with `zipfile.testzip()` — no corruption, no backslash entries.

Packaged: monthly-close (v2.0, 59-item/10-category, Restoration Church Trust balloon alert), acquisition-underwriting (v3.5, Louisville KY cluster + Stage 2.6 pre-LOI DD checklist + bear-mode conflict rules), loi-generation (16-point QC Gate, 5 entries incl. state-overlays/qc-gate/ora-standards refs + DOCX template), deal-comparison, portfolio-growth, portfolio-reporting, conversation-archival, website-perfection (last 5 = stale "Ze"/"Ze Ooba" identity purge, confirmed 0 matches remain in canonical).

**Not done (human-gated by design):** Save-skill import into Cowork — Gabriel's manual click per skill, Settings → Capabilities. No `present_files`/Cowork session-outputs mechanism exists on the Code CLI surface this ran on; staged to a persistent on-disk folder instead (functionally equivalent — import is a manual file-browse either way). Runtime cache re-syncs from the platform after each import; re-run `ora-skill-store-drift-check` after to confirm IN-SYNC.

**Side effect cleaned up:** an exploratory `--help` flag typo on `package_skills.py` created a stray `--help/` directory (all-43-skill packaging side effect, no informational value) — moved (not deleted, per invariant 6) to `ora-skills/_archive/accidental-help-dir_2026-07-09/`.

## 2026-07-09 — E. Fulton Street Portfolio DECLASSIFIED (Gabriel directive, over recommendation)

Gabriel directed, in-turn and explicitly (twice), that E. Fulton be **fully declassified** — removed from all confidential treatment. Context he gave: the purchase/acquisition contract was **terminated**; ORA is now in a **note/foreclosure discussion with the lender** (the lender plans to foreclose on 3520 E. Fulton).

**Recommendation given and overridden (on the record):** I advised *against* full declassification and recommended *reclassify, not declassify* — keep the egress guard active because an active pre-foreclosure/note negotiation with the foreclosing lender is arguably more market-sensitive than the original acquisition, and Invariant 3's guard is what mechanically keeps the name off oxfordra.net and every external surface. Gabriel overrode with eyes open. In-turn instruction is top of precedence; executed as directed.

**Executed (internal only, this Code surface):**
1. `hooks/confidential-terms.json` — `e_fulton` set `active:false` (retired from the egress guard; block + term list retained as audit trail, not deleted per Invariant 6). JSON validated (no machine-wide fail-closed).
2. `memory/projects.md` — pipeline row + Section 1: dropped `[CONFIDENTIAL]`, removed "must never appear externally" language, updated state to acquisition-terminated / lender note-foreclosure track / declassified.
3. `memory/MEMORY.md` + `memory/firm.md` — dropped the `(CONFIDENTIAL, materially impaired)` / `[CONFIDENTIAL]` tags on the E. Fulton pointer lines; updated to terminated/declassified.

**Deliberately NOT touched (out of scope / needs Gabriel):**
- `oxford-command-center` repo stays PRIVATE — it embeds E. Fulton figures in `seed-deals.ts`; declassifying the deal does not make that repo publishable. No change to repo-privacy posture.
- Cowork `efulton_*` deal memory + the Notion Acquisition Pipeline Tracker row — not reachable from the Code surface; staged for Gabriel/Cowork to mirror the declassification.
- `CLAUDE.md` — contains no E. Fulton reference (nothing to remove); left untouched (also had uncommitted changes from another session).

## 2026-07-09 — Open-sessions board decisions (4 items)

ora-open-sessions-board (daily 5PM ET triage) rendered 4 actionable items; Gabriel answered same day.

1. **Dollar General, 11850 Hamilton Ave, Cincinnati OH (quasi-IOS)** — Cowork session `local_68ae92cb` had self-underwritten to v03 and staged the card to the Notion Acquisition Pipeline Tracker at Stage = "Due Diligence." Board flagged the tension (DG is standing out-of-box retail for ORA; the OH 3-pack PASSed 2026-06-08). **Decision: PARK.** Notion card moved off "Due Diligence"; not advanced to the active pipeline. Not added to projects.md active deal table.

2. **ora-pm PR #3** ("Recover unpushed 2026-06-07 auth hardening — object-DB loss recovery"; QB-export auth fix + admin/portal auth-gate hardening). Board asked whether to merge. **Decision: MERGE.** Verified already MERGED — CI + CodeRabbit green, merged 2026-07-07; `origin/main` HEAD `8418c44 …(#3)`. Live main now carries the auth hardening. No action beyond confirmation.

3. **Symetra & Park National auto-pays (outage-window execution check)** — surfaced by memory-consolidation session `local_b1430b5e`. **Decision: Gabriel will confirm himself.** No action taken.

4. **Claude-setup session** `local_b66b45ec` — parked on two manual items (run the send-path "copy-and-test", install Desktop Commander). **Decision: walk-through.** Finding: item 1 is already resolved — `send-via-outlook.ps1` was rebuilt 2026-07-08 21:25 and is operational (the board's own pointer email sent through it, exit 0; recent ora-am-brief sends succeeded). Item 2: Desktop Commander is live on the Code surface as a plugin; only the Claude Desktop / Cowork extension install remains genuinely manual (Settings → Extensions). Optional hardening noted: the @oxfordra.net-only recipient guard the setup session proposed is not in the current send script (not a blocker).

## 2026-07-09 (cont.) — Restored 2 of the 3 scheduled-task gaps found via ora-task-integrity-guard investigation (dormant-thread-revival deliberately NOT restored)

Follow-up to today's earlier entry on the MCP-snapshot fix. Investigated the 5 names the corrected snapshot surfaced as "disappeared"; 3 were non-issues (ar-aging-parser-completion: underlying feature shipped, PR #81 merged 2026-06-20; ora-lease-expiration-action-list: superseded by the live ora-lease-expiration-brief; ora-automation-health-monitor: naming-drift artifact, the live LAMS task is simply registered as `automation-health-monitor` with no prefix). The other 2 were genuine gaps from the 2026-07-07 archive batch with no live twin on either fleet, confirmed via `list_scheduled_tasks` (neither CC nor LAMS) and not present on any do-not-re-register list in `session-context.md`:

- **`ora-open-sessions-board`** restored on the CC/MCP fleet, cron `0 17 * * *` (daily 17:00 ET, matching original 2026-06-12 registration). Dependency `open_sessions_probe.py` and decision-history `answered.json` both survived intact in `_archive_2026-07-07_retired\` — copied `answered.json` into the new live task folder so prior board decisions aren't replayed. One content fix: STEP 4's deal-pipeline read repointed off the retired `--1-`-suffixed OneDrive scope onto the canonical path.
- **`ora-week-ahead-briefing`** restored on the CC/MCP fleet, cron `30 16 * * 5` (Friday 16:30 ET). The live OneDrive spec folder its old CC copy pointed to was empty (emptied during the 07-07/07-08 cleanup) — recovered content from a pre-consolidation 2026-06-03 backup (`~/.claude/backups/scheduled-skills-20260603T170933/`) and modernized: purged all Composio/Rube MCP routing (both retired 2026-06-11) in favor of the current sole Outlook-COM send path, dropped the egoldberg cc, replaced the broken external "(1)"-suffixed Publication Guard pointer with an inlined guard using direct `notion-fetch` verification (not `notion-search`, which the fleet has since learned produces false negatives).

**Deliberately NOT restored: `ora-dormant-thread-revival`.** Its own archived frontmatter reads `RETIRED 2026-06-16 (strategic audit kill list): no documented outcome; low observable value` — a considered governance decision three weeks before the 07-05 incident, not a rebuild casualty. The 2026-06-03 event_log entry describing it as a deliberate dependency of week-ahead-briefing predates that kill decision; `ora-week-ahead-briefing`'s restored content was written to stand alone on its original 6 Notion/Outlook/HubSpot sources without that dependency.

**QC gate:** both ids verified live via `list_scheduled_tasks`, unique across both fleets, `enabled:true`, next fires 2026-07-09T21:08:30Z (open-sessions-board, today) and 2026-07-10T20:36:01Z (week-ahead-briefing, tomorrow). Routing ggoldberg-only, send path Outlook COM only, zero registry-JSON edits (both via supervised `create_scheduled_task`).

**Files modified:** new `ora-open-sessions-board/{SKILL.md,answered.json}`, new `ora-week-ahead-briefing/SKILL.md` (both `~/.claude/scheduled-tasks/`); this log.

## 2026-07-09 — ora-task-integrity-guard: fixed broken MCP-snapshot producer contract; today's "disappeared" alarm was a stale-baseline replay, not a new drop

**Trigger:** the 2026-07-09 scheduled guard run alarmed on `disappeared:["ora-lender-covenant-tracker"]`. Investigation traced this to Gabriel's own intentional 2026-07-08 deletion of that task (debt-management resurrection-loop fix, see the 2026-07-08 entry) — the alarm fired only because the guard's baseline snapshot (`mcp-fleet-snapshot:2026-06-22.json`) predates that deletion by two weeks. Mechanically correct, substantively moot — no follow-up needed on the tracker itself.

**Root cause found and fixed:** `membership-guard.ps1` has no live tool access (bare PowerShell) and depends on a dated `_state-history\YYYY-MM-DD.json` file to represent the CC/MCP fleet side of its diff. That snapshot was previously exported by `ora-automation-health-monitor`, but that skill was refactored (source: its own SKILL.md, "Canonical source = the live registries, not any table in this file") to read `list_scheduled_tasks` live every run instead of exporting a dated file — the producer side of the contract silently stopped, freezing the snapshot at 2026-06-22 with nothing to notice. Fix: `ora-task-integrity-guard/SKILL.md` v1.2 adds a new STEP 0.5 — the guard now calls `list_scheduled_tasks` itself and writes its own dated snapshot before running the engines, removing the dependency on automation-health-monitor ever exporting one again.

**Side effect discovered during verification (flagged, not fully reconciled):** a manual re-run of `membership-guard.ps1` to verify the fix (parse_miss empty, mcp_snapshot_stale_days → 0, confirmed) surfaced `disappeared:["ar-aging-parser-completion","ora-lease-expiration-action-list","ora-automation-health-monitor","ora-open-sessions-board","ora-week-ahead-briefing"]` and `disabled:["ora-weekly-hygiene","ora-health-guard","ora-pm-ledger"]` against the persisted baseline. Because the frozen 2026-06-22 snapshot had been re-feeding the same stale CC task list into the guard's baseline every day, roughly three weeks of real fleet drift (spanning the 2026-06-03 Phase 3 consolidation, the 2026-07-05 registry-destroying reinstall, and the 2026-07-07/07-08 rebuild) was masked until this fix ran. Assessment: very likely legitimate historical retirements/consolidations (e.g. folded into `ora-pm-ledger`'s consolidated blocks, or fully migrated to the LAMS/Cowork fleet) rather than a new loss — but NOT individually confirmed name-by-name. Because `membership-state.json` is unconditionally overwritten every run, this verification call has already re-baselined the guard onto the correct, current fleet — the next scheduled run will NOT re-surface this list. **Open follow-up for Gabriel or a future session: confirm each of the 5 names is a known-intentional retirement/migration, not a genuine unnoticed loss.**

**Also fixed:** `ora-doctrine-integrity-guard` was the only live, non-inert CC/MCP task missing a `[MODEL: ...]` currency tag (known gap per `reference_scheduled_task_model_standard.md`). Tagged `[MODEL: UNVERIFIABLE | checked 2026-07-09]`, matching the other 8 tasks' convention. Verified live via `list_scheduled_tasks`.

**Files modified:** `ora-task-integrity-guard/SKILL.md` (v1.1→v1.2, new STEP 0.5, STEP 2.5 reuses its result), `ora-doctrine-integrity-guard/SKILL.md` (model tag), new `_state-history\2026-07-09.json` (first self-written snapshot).

## 2026-07-09 — Final 2 residual fleet-recovery items: 1 closed, 1 decided-pending-execution

Gabriel closed out the last two residual items from the 2026-07-08 LAMS-fleet-audit.

1. **Dangling LAMS entries purged — CLOSED.** Gabriel deleted both `ora-debt-maturity-snapshot` and `ora-weekly-sourcing-digest` via the Cowork UI. Independently verified rather than taken on faith: grepped the raw LAMS `scheduled-tasks.json` for both IDs, zero hits.

2. **`ora-cam-reconciliation-annual` timing — DECIDED, not yet executed.** Gabriel's call: December-only, not year-round. Could not execute the toggle from this Code session — the bound `scheduled-tasks` MCP here only surfaces the CC/MCP registry (`list_scheduled_tasks` returns 11 CC/MCP tasks, no LAMS tasks), and LAMS `enabled` state changes must go through a Cowork session or the Cowork UI per the dual-fleet doctrine (no JSON-splice). Asked Gabriel to disable it now via Cowork and re-enable each December before the Jan 15 fire. Updated `_REGISTRY.md` and `session-context.md` to record the decision and flag it as pending execution, not closed.

## 2026-07-09 — automation-health-monitor canonicalization resolved (verified, not just claimed)

Followed up on the `_REGISTRY.md` "Open / pending" item flagged in the previous entry: "decide `automation-health-monitor` canonicalization (registered thin stub vs. richer orphaned v1.5)."

Traced the claim to its source (2026-07-08 LAMS-fleet-audit) and diffed the actual files instead of trusting either changelog. Result: the premise no longer holds. The registered `Documents\Claude\Scheduled\automation-health-monitor\SKILL.md` (20,144 bytes, v1.6) already substantively contains the v1.5 differentiators the audit flagged (ORPHANED-BEACON rule, producer-consumer beacons, dual-bounded lateness — confirmed via grep, not just the description line). The orphaned duplicate `ora-automation-health-monitor` was already archived same-day (2026-07-08) to `_archive_2026-07-08_retired\` — someone had already merged the rich content into the registered slot and retired the loser, per the audit's own recommendation, between the audit and this check.

Two loose ends fixed this session: (1) three leftover artifact files (`outputs\`, `archive\`, a dated draft-alert) left behind in the now-SKILL.md-less `Documents\Claude\Scheduled\ora-automation-health-monitor\` folder — consolidated into the existing `_archive_2026-07-08_retired\ora-automation-health-monitor\` archive. (2) A second, independent broken-redirect-stub copy in the legacy pre-fleet-split tree at `Claude_Workspace\00_Governance\Scheduled\ora-automation-health-monitor\SKILL.md` (same pattern as the `ora-lender-covenant-tracker` leftover archived earlier today) — grepped for live references (none beyond its own self-referential body text) and archived to `Claude_Workspace\00_Governance\Scheduled\_archive_2026-07-08_retired\ora-automation-health-monitor\`.

Updated `session-context.md`'s residual-open-items line, `oxford-cc-repo-health.md`, and `_REGISTRY.md`'s Open/pending table to reflect closure. Note: `session-context.md` had been edited by another writer between this session's start and this edit (the debt-management item's resolution note was upgraded to "FULLY RESOLVED" with additional detail) — confirmed the edit was additive/compatible with my target text before proceeding, per the single-writer coordination doctrine.

## 2026-07-09 — Full re-sync of `Claude_Workspace\00_Governance\Scheduled\_REGISTRY.md`

Followed up on the `ora-lender-covenant-tracker` archival (prior entry) by doing the full re-sync flagged as out of scope there. This doc — a hand-curated mirror predating the CC/MCP vs. LAMS/Cowork fleet split — hadn't been touched since 2026-05-08 and no longer matched either live registry.

Pulled fresh ground truth: `mcp__scheduled-tasks__list_scheduled_tasks` for the CC/MCP fleet directly, plus a live `registry-membership-probe.py` run (regenerated `session-context.md`'s fleet banner: CC 6 enabled, LAMS 18 enabled — up from the banner's own 5/16 snapshot from the day before). That run surfaced three tasks this doc had never recorded: `ora-doctrine-integrity-guard` (CC), `ora-ar-export-freshness-nudge` and `ora-stale-pipeline-nudge` (LAMS), all created 2026-07-08. Cross-checked LAMS task descriptions via a frontmatter grep across every active `Documents\Claude\Scheduled\<id>\SKILL.md`.

Rewrote the Active/Disabled tables fleet-scoped (CC/MCP 6 enabled + 4 disabled; LAMS 18 enabled + 2 one-time-future + 2 dangling disabled pending purge). Retired-task history de-duplicated to a pointer at `session-context.md`'s consolidated list rather than re-maintained inline (avoids the exact staleness pattern that caused this cleanup). Removed the old `Recommended scheduled tasks NOT YET created` section — all four rows were Composio-era items, long resolved, and Composio itself no longer exists (retired 2026-06-11). Refreshed `Open / pending`, closing the stale QuickBooks-MCP-reauth item (resolved by policy — Desktop-only, not reconnection) and flagging the Notion "Publication parent" page ID as unverified since 2026-05-08.

## 2026-07-09 — debt-management duplicate-plugin item fully closed (Gabriel-verified)

Gabriel checked Settings → Capabilities directly and screenshotted the `ora-operations-extensions` plugin panel: its live `Skills` list has only 7 entries (`annual-cycle`, `capex-budgeting`, `cash-position-monitor`, `deal-retirement`, `investor-relations`, `submarket-spatial-analysis`, `vendor-management`) — `debt-management` is not among them. Only the plugin's static top-level description text is stale (still says "Eight institutional skills... debt management..."), which is cosmetic and not worth fixing.

Combined with the earlier-verified content fix (v1.1, 2026-07-08) and git-pin migration (v1.2, PR #7, merged 2026-07-09), this closes the debt-management item end-to-end: no stale task references, no duplicate plugin entry, canonical copy lives in `ora-skills`. Updated `session-context.md` and `oxford-cc-repo-health.md` to reflect final state.

## 2026-07-09 — Archived orphaned `ora-lender-covenant-tracker` copy in `Claude_Workspace\00_Governance\Scheduled\`

Actioned the incidental finding logged earlier today (see prior entry, "Corrected stale 'debt-management still names retired tasks' claim"): `Claude_Workspace\00_Governance\Scheduled\ora-lender-covenant-tracker\SKILL.md` was a second, older copy living in the legacy `00_Governance\Scheduled\` framework — distinct from the actual LAMS/Cowork scheduled-task folder `Documents\Claude\Scheduled\`, whose twin was already archived 2026-06-11.

Grepped `~/.claude`, `Claude_Workspace`, `ora-skills`, and `oxford-command-center` for live references before touching anything — no live dependencies found. All hits were historical incident logs, already-resolved changelog notes (the debt-management v1.1 fix, `MIGRATION_RUNBOOK.md`'s RESOLVED note), dated `_state-history` snapshots, or the stale `_REGISTRY.md`. RATIFIED — one of the 4 Gabriel-ratified-unneeded 2026-06-11 retirements; confirmed absent from both live registries per the 2026-07-08 fleet audit.

Moved the folder to `_archive_2026-06-11_orphans\ora-lender-covenant-tracker\` (dated to match the original ratification, not today, mirroring the LAMS-side sibling) and removed its row from `_REGISTRY.md`'s Quarterly table. Added a changelog note there flagging that `_REGISTRY.md` overall has been stale since 2026-05-08 (several other rows no longer match the live fleet) — a full re-sync of that doc is a separate, un-actioned task.

## 2026-07-09 — Corrected stale "debt-management still names retired tasks" claim; archive branch force-deleted

Two fixes actioned on Gabriel's "fix this" instruction:

1. **`archive/main-pre-pr-sync-2026-07-09` branch force-deleted** (authorized) in `ora-skills` — `git branch -d` had refused it (no ancestry relationship to `main`, only content-equality via cherry-pick/squash), confirmed redundant via `git diff` before the `-D`.

2. **Debt-management "resurrection loop" claim corrected, not fixed — it turned out already resolved.** Before repeating my own prior message's claim (that the `ora-operations-extensions:debt-management` plugin skill still names retired tasks as inputs), read the actual migrated `ora-skills/debt-management/SKILL.md` changelog: v1.1 (2026-07-08) already removed the stale `ora-debt-maturity-snapshot`/`ora-lender-covenant-tracker` references, on both the plugin runtime-cache copy AND the `Claude_Workspace/01_Workspace/20260428_ORA-Skills-Pack_v01/debt-management/SKILL.md` source-pack copy — done same-day, before and separate from the v1.2 git-pin migration (PR #7, merged 2026-07-09). Independently re-verified: grepped the source-pack copy directly for both retired-task names, zero hits. The stale claim traced back to `session-context.md` line 7 and `oxford-cc-repo-health.md` line 28, both written before that same-day fix and never updated — corrected both files just now. Only remaining step per the skill's own v1.2 changelog: a manual one-click Cowork Settings → Capabilities action to remove the old plugin entry (duplicate-skill triggering only, not a data-drift risk) — not executable from Code.

**Incidental finding, not actioned (flagged separately):** `Claude_Workspace/00_Governance/Scheduled/ora-lender-covenant-tracker/SKILL.md` still sits in a non-archived location and references the shut-down Rube/Composio MCP bridge — looks like an orphan predating the 2026-06-11 Rube retirement, not the same file as the debt-management skill's stale references (different skill, different bug). Out of scope for this fix.

## 2026-07-09 — ora-skills: PR #7 merged, main fast-forwarded, saga fully closed

PR #7 (debt-management v1.2) merged. Fast-forwarded local `main` to `origin/main` (`8f687e8`, safe — no local divergence this time, plain `git merge --ff-only`). Deleted the now-merged `feature/debt-management-migration` branch locally and on the remote.

`archive/main-pre-pr-sync-2026-07-09` confirmed fully redundant (empty content diff vs. `main`) but left in place — `git branch -d` refused it (not an ancestor by commit history, only by content, since the merged PRs used different SHAs via cherry-pick/squash) and forcing with `-D` wasn't authorized in-turn. Flagged to Gabriel for an explicit go-ahead rather than force-deleting.

**End state, all 4 PRs merged into `origin/main`:** #4 (changelog tightening + QuickBooks-Scrub cleanup), #5 (portfolio-growth DSCR ceiling — closes CLAUDE.md audit Phase 3 item 7), #6 (acquisition-underwriting STAGE 2.6), #7 (debt-management v1.2 migration, the never-pushed 6th commit caught mid-cleanup). `ora-skills` working tree, local `main`, and `origin/main` are all in sync. No open threads remain from the original "5 uncommitted files" finding.

## 2026-07-09 — ora-skills: local main resynced post-merge; caught a 6th never-pushed commit in the process

PRs #4-#6 merged; asked to fix the flagged local/origin `main` divergence. `git reset --hard origin/main` was attempted first and was auto-denied — confirmed categorical, intentional `permissions.deny` per [[feedback_destructive_git_deny_stays_hard]], not something to route around even on explicit request.

Used a non-destructive rename instead: `git branch -m main archive/main-pre-pr-sync-2026-07-09` (preserves the full old diverged history under an archive name) then `git checkout -b main origin/main` (fresh `main` tracking origin exactly, verified via empty `git diff origin/main main`).

**Caught before it could cause loss:** while diffing old-`main` against `origin/main` pre-reset, found a 6th commit (`5159fdf`, "debt-management v1.2: migrate into ora-skills from ora-operations-extensions plugin") that predated this whole PR exercise and was never pushed or PR'd — a naive reset would have silently deleted `debt-management/SKILL.md` from the working tree. Cherry-picked it onto a fresh branch off the post-merge `origin/main` and opened [PR #7](https://github.com/ZeOoba/ora-skills/pull/7) `feature/debt-management-migration` before touching `main`, so nothing was at risk when the rename/resync happened.

Also deleted the 3 now-fully-merged branches (`audit/changelog-tightening`, `audit/portfolio-growth-dscr-ceiling`, `feature/acquisition-underwriting-stage-2-6`), local and remote — GitHub didn't auto-delete them on merge.

**Current state:** `main` = `origin/main` exactly (8dd32a6). `archive/main-pre-pr-sync-2026-07-09` kept as a safety-net branch (not yet deleted — low-risk to prune once Gabriel confirms nothing else in it is needed). PR #7 (debt-management) still open, awaiting merge.

## 2026-07-09 — ora-skills: 3 PRs opened for the reconciled commits (#4, #5, #6)

Following the prior commit work, split into 3 branches off `origin/main` (which sat at `e904d1b`, unchanged) and opened PRs via `gh pr create`:
- [PR #4](https://github.com/ZeOoba/ora-skills/pull/4) `audit/changelog-tightening` — bundles 2 commits, not 1: cherry-picking the "changelog prose tightening" commit alone conflicted, because it turned out to be a direct textual follow-on to the pre-existing (already-local, unpushed) `2f34ec6` QuickBooks-Scrub cleanup commit — same lines in `lease-abstraction-pipeline`, `psa-reconciliation`, `oxford-cc-strategic-audit`. Both included, in order, with the bundling explained in the PR body.
- [PR #5](https://github.com/ZeOoba/ora-skills/pull/5) `audit/portfolio-growth-dscr-ceiling` — clean single-commit cherry-pick, no dependency issues.
- [PR #6](https://github.com/ZeOoba/ora-skills/pull/6) `feature/acquisition-underwriting-stage-2-6` — clean single-commit cherry-pick, no dependency issues.

Local `main` (5 commits ahead of `origin/main`) was left untouched throughout — all work done on throwaway branches off `origin/main`. Once these PRs merge, local `main` should be reset to track `origin/main` rather than pushed directly (it now diverges from the merged history via cherry-picked SHAs). Not yet actioned — flagging for whoever merges these.

## 2026-07-09 — ora-skills 5 uncommitted files reconciled and committed (closes CLAUDE.md audit Phase 3 item 7)

`ora-skills` HEAD had been static at `2f34ec6` for 12+ hours with 5 modified-but-uncommitted files, flagged by Gabriel for a second look. Assessed by file mtime + diff content — two unrelated, complete work-streams, not abandoned/broken edits:
- Committed `1cd1c46`: trivial version-changelog prose tightening across `lease-abstraction-pipeline` (v2.2), `psa-reconciliation` (v1.3), `oxford-cc-strategic-audit` (v1.1) — all touched within 23s of each other 2026-07-08 17:46, no content/doctrine change.
- Committed `b70ee51`: `portfolio-growth/SKILL.md` — the 1.75x portfolio-blended DSCR ceiling vs. 1.25x per-deal floor reconciliation (touched 2026-07-08 21:22, wording matches the already-applied OneDrive/AppData copies verbatim). This was the last open item (item 7) from the 2026-07-08 CLAUDE.md formal audit Phase 3 — see `project_claude-md-formal-audit-2026-07-08.md`. **Item 7 is now CLOSED.**
- Committed `dd36aa2`: `acquisition-underwriting/SKILL.md` v3.4→v3.5 — new STAGE 2.6 Pre-LOI DD Resolution Checklist (touched 2026-07-08 16:10) — unrelated to the audit, real deal-skill development validated against the DollarGeneral-Cincinnati DD work.

All 3 commits are local only, not pushed (`origin/main` unchanged; local branch now 5 ahead). No concurrent writer detected before or during the work (`git log -1` / `git status` re-verified immediately before committing, matched Gabriel's prior check).

## 2026-07-08 (late night) — Near-miss: confidential deal terms briefly committed to ~/.claude, caught before push, corrected

**What happened:** while committing the day's accumulated `~/.claude` changes (at Gabriel's explicit instruction, after he authorized broad autonomy and went to bed), one commit included two newly-created LAMS-fleet-recovery audit artifacts (`maintenance/_audits/2026-07-08_LAMS-fleet-audit_v01.md` and `..._re-retirement-runbook_v01.md`) that contain active confidential deal terms. These files were legitimate work product from earlier today's fleet-recovery incident but were never meant to be git-tracked — they should have gone through the sanctioned `_confidential-staging/` untracked path per rules.md §7a, and weren't.

**How it was caught:** a routine post-commit sanity re-run of `doctrine-integrity-probe.py` (part of closing out the night's work, not a dedicated audit of the commits themselves) flagged 3 confidential-term leak findings (check 8) in the two files, by index only — the probe never echoed the actual term, exactly as designed.

**Blast radius:** contained. `origin/main` was confirmed still at the pre-session commit (`94f91b1`) before any corrective action — none of the night's commits, including the one with the leak, had been pushed. The leak existed only in local, unpushed git history for the span of this session.

**Fix:** since nothing had been pushed, local history was safely rewritten (`git reset --soft` past the offending commit — not `--hard`, working tree/content preserved throughout) to remove the two files from tracking entirely; they were relocated to `~/.claude/_confidential-staging/2026-07-08_LAMS-fleet-recovery/` (untracked, gitignored, the sanctioned home per rules.md §7a) instead. The remaining legitimate changes were re-committed cleanly. Re-ran `doctrine-integrity-probe.py` — exit 0, zero leaks. Also fixed 3 now-stale references to the old tracked path (in `oxford-cc-repo-health.md` both scope copies, `ora-master-workbook-ingest/SKILL.md`, `session-context.md` — none of which are git-tracked themselves, so this was pure hygiene, not a second leak).

**Process lesson:** committing a day's accumulated changes (spanning work from multiple sessions) needs the SAME per-file confidential-content check as any single edit — reviewing diffs for "does this look like reasonable code" is not the same check as "does this contain a deal name," and the second one is the one that actually matters for Invariant 3. The doctrine-integrity-probe's check 8 is exactly built for this and should be run as a matter of course immediately after any commit that includes new files, not just periodically — this incident is the reason that discipline earns its keep. No content was ever exposed externally; this is logged for the record and to reinforce the practice, not because harm occurred.

## 2026-07-08 (late evening) — CLAUDE.md formal audit Phase 3 (continuous review mechanism) DONE

**Scope:** closed the last open item from the 2026-07-08 5-agent CLAUDE.md audit — Phase 3, "make drift-detection continuous rather than opportunistic." Executed via 3 disjoint-file opus subagents (dispatched from a Sonnet-5 orchestrating session, per the confidential/governor-adjacent-code dispatch doctrine) plus orchestrator-level verification, registration, and memory updates.

**Shipped:**
1. **Meta-guard (doctrine-integrity-probe.py check 11, WARN-only):** verifies every guard named in CLAUDE.md's `Guards:` line has a live invocation point (settings.json hook / CC scheduled-task SKILL.md / `~/.claude` pre-push shim) — this is the check that would have caught the original `ora-setup-audit` silent-retirement root cause. CLAUDE.md's `Guards:` line also now names `governor-drift-probe.py` and `git-prepush-doctrine-gate.py` (both were live-but-undocumented; `governor-drift-probe.py` had genuinely ZERO runner anywhere until item 4 below). +6 words (CLAUDE.md now 1763, still WARN not FAIL — 87-word headroom to 1850). A pre-existing failing test (`test_size_budget_fail`, stale 1600-word fixture predating the Phase-2 budget recalibration) was fixed as a side effect.
2. **Triple-redundant notification, layer 2 (local status file):** new `maintenance/_shared/write-doctrine-status.py` (`write_status()`, atomic overwrite) wired into `hooks/git-prepush-doctrine-gate.py` — every gate run now leaves a durable `maintenance/_state/doctrine-status.json` snapshot, not just ephemeral console output.
3. **Scheduled backstop (item 4) — registered via supervised `create_scheduled_task`, verified via `list_scheduled_tasks`:** new CC/MCP task `ora-doctrine-integrity-guard`, daily `55 12 * * *` (next fire 2026-07-09 ~13:05 ET), runs BOTH probes (doctrine-integrity-probe.py + the previously-unwired governor-drift-probe.py) plus eos-telemetry-rollup.py, silent-unless-alarm (mirrors `ora-task-integrity-guard`'s convention), alarms via Notion Ops Hub (`32b6ecd8...`) + best-effort Outlook COM email to ggoldberg-only, governor drift flagged with explicit Hard-Invariant-4 urgency.
4. **Retired the legacy weekly mechanism:** `register-eos-health-task.ps1` + `eos-health-report.ps1` archived (moved, not deleted) to `maintenance/_archive/` with a dated README. Finding: the "ORA EOS Health" task these scripts drove was a RAW Windows Task Scheduler entry (`Register-ScheduledTask`) — a third scheduling mechanism entirely outside the documented CC/MCP + LAMS dual-fleet doctrine — and was confirmed NOT registered (dead) at time of replacement. `eos-telemetry-rollup.py` itself was preserved, now invoked by the new scheduled task. `rules.md` §7a's stale "weekly email via eos-health-report" line corrected to describe the new gate+scheduled-task+Notion chain.
5. **Monthly consolidation fold-in (item 5):** `ora-consolidate-memory-monthly` SKILL.md gained a recurring step reading `doctrine-status.json` + grepping event_log.md for pre-push override-sentinel uses, logging pass/fail + override reasons once a month.
6. **Gabriel-authorized fix, same session:** `ora-consolidate-memory-monthly`'s Step 1 stale `--1-`-suffixed memory path corrected to the canonical no-suffix path — a 7th instance of the tracked stale-scope pattern (`reference_memory_scope_fragmentation.md`), found by the drafting subagent, fixed only after explicit sign-off.

**Verified independently by the orchestrator (not just subagent self-report):** `test-doctrine-integrity-probe.py` 19/19 pass, `maintenance/_tests/test_git_prepush_doctrine_gate.py` 9/9 pass, `hooks/tests/test-git-prepush-doctrine-gate.py` 15/15 pass, live `doctrine-integrity-probe.py` run exits 0 with all 5 guards resolving (zero orphans), live `git-prepush-doctrine-gate.py` run exits 0 and leaves a valid fresh status-file snapshot, new scheduled task confirmed live via `list_scheduled_tasks`.

**Also resolved in passing:** the Outlook "New Profile" wizard block flagged earlier today (`maintenance/_state/guard-failure-2026-07-08.md`) self-resolved sometime this afternoon — send-log shows successful COM sends from 14:00 onward; no human action was needed after all.

**Still OPEN (deliberately deferred, not forgotten):**
- The `governor-drift-probe.py` word-order detection gap (a "NUMBER floor" phrasing without a nearby literal "DSCR" is invisible to both primary regexes) — precision-tuned financial-governor code, judged not worth a blind regex change this session; needs its own scoped pass.
- Two more `--1-` stale-path instances found by the same drafting subagent (`ora-task-integrity-guard` STEP 2.5, `automation-health-monitor` Step 0.07 — both reference `reference_scheduled_task_model_standard.md`) — same class as item 6 above but NOT covered by today's sign-off (which named only the consolidate-memory skill); need separate authorization.
- **New finding, not yet actioned:** the `~/.claude` working tree currently holds a substantial pile of uncommitted changes spanning MULTIPLE same-day work sessions — Phase 0/1/2 of this audit plus apparently-separate tooling-hardening work (registry-membership-probe.py, append-event-log.py, setup-self-audit.py, memory-integrity-probe.py, cc-verifier-probe.py, confidentiality-guard.py, git-prepush-confidential-scan.py, settings.json, .gitignore — mtimes ranging ~12:57 PM to ~9:48 PM today), none of it committed. Nothing was found broken (settings.json parses; test suites green) but this is a real single-writer risk sitting in the tree — flagged for Gabriel to decide how to commit (likely several logical commits, not one), not committed by this session per the "only commit when asked" rule.

Phase 3 checklist in `project_claude-md-formal-audit-2026-07-08.md` updated to DONE; that file now holds the full phase history for this audit end-to-end (Phases 0-3 all closed, 3 items intentionally deferred as above).

## 2026-07-08 (later evening) — 139 claude.ai conversations found deleted 07-05→07-08, content recovered; likely self-inflicted via an artifact-cleanup misstep, NOT the machine migration

**Trigger:** Gabriel asked to find "6 projects" from his old Cowork setup (named examples: 2026 Investment Candidate project, E Fulton folder project, LOI/PSA project). Cross-checked against the account's actual claude.ai Projects feature first (found in `C:\Users\Owner\Downloads\data-*.zip` account exports) — only 7 Projects exist, none matching, all confirmed present in both a 2026-07-05 and 2026-07-08 export (unaffected by anything). Widened the search to full conversation history instead.

**Finding:** the two export archives (07-05: 216 conversations; 07-08: 81 conversations) diff to **139 conversations missing by UUID** — lost in a 3-day window well after the 07-05 migration, not because of it. A conversation titled "Deleting artifacts" first appears in the 07-08 export (created 2026-07-07T15:36 UTC): Gabriel asked how to delete artifacts, and Claude's answer pointed at deleting source conversations as the practical route to clear the Artifacts sidebar. Working explanation (not certain, no direct deletion log exists): a bulk conversation-deletion done in pursuit of an artifact cleanup took out 139 conversations as a side effect, including months of deal work (E Fulton due diligence, PSA/LOI comparisons, acquisition-analysis threads dated Jan-Apr 2026).

**Recovery:** the 07-05 export still holds full message content for all 139. Extracted and archived to `Claude_Workspace/01_Workspace/_Recovered_ClaudeAI_Conversations_2026-07-08/` — raw JSON backup (full fidelity), two readable markdown transcripts split deal-related (61) vs. dev/misc (78), an INDEX, and a README mapping Gabriel's three named examples to their closest actual conversations.

**Open for Gabriel:** whether claude.ai has an Archived/Trash state making these natively restorable in the UI (not verified from this session — no web access); whether "2026 Investment Candidate project" meant conversations at all vs. the untouched OneDrive folder `Investment Candidates -- 2026\`. Full detail + exact conversation-title mapping in the Cowork-side `event_log.md` (`Claude_Workspace/01_Workspace/memory/`) and the recovery folder's own README.

## 2026-07-08 (evening) — Cross-surface relay: closed a blocked Cowork finding, found + fixed an 8th `--1-` stale-pointer instance

**Trigger:** Gabriel asked how to relay this session's CC/MCP fleet verification to a Cowork session that had hit a wall on the same question — Finding 9 of the same-day `ora-skill-text-audit` remediation ("Six CC/MCP-fleet task refs... could NOT be verified — `~/.claude/scheduled-tasks/` is host-protected, not mountable from Cowork") logged in the OneDrive-side `Claude_Workspace/01_Workspace/memory/event_log.md`.

**No Code→Cowork messaging tool exists** (`send_message`/`list_sessions` only reach other Claude Code sessions — confirmed empty results searching for the Cowork session). Relayed instead through the two channels Cowork actually reads: appended a resolution entry directly to the Cowork-side `event_log.md` (the six named tasks reconciled against the live CC/MCP roster — 3 live/enabled, 1 disabled-pending-confirmation, 2 already-ratified-retired), and posted a comment on the source Notion page (`Remediation Complete — 2026-07-08`, comment id `3986ecd8-9e59-81de-9081-001df3911617`).

**Root-cause finding, not on the known list:** `Claude_Workspace/01_Workspace/CLAUDE.md` — the thin-pointer CLAUDE.md every Cowork session on this workspace loads as context — had its own `Memory:` line hardcoded to the stale `--1-`-suffixed OneDrive scope, undiscovered by the 2026-07-08 `reference_memory_scope_fragmentation.md` grep (that grep only covered `~/.claude`; this file lives on OneDrive). This is a plausible direct cause of "Cowork can't find the file" as a general pattern, not just Finding 9. Corrected to the plain (no-suffix) canonical path — lower-risk than the 6 still-OPEN maintenance-script instances (documentation pointer, not governor/confidentiality enforcement logic), and consistent with the already-adopted working assumption everywhere else. `reference_memory_scope_fragmentation.md` updated with this 8th instance so it isn't lost.

**Status:** Relay complete; workspace CLAUDE.md fixed. The 6 script-level `--1-` instances (governor-drift-probe, doctrine-integrity-probe, registry-membership-probe, append-event-log.py, cc-verifier-probe, setup-self-audit) remain OPEN, unchanged, still needing Gabriel's explicit confirmation per the existing note.

## 2026-07-08 — WAL-lock/backfill contention mitigated (supersedes the 2026-06-13 "live npm run dev blocks backfill" finding)

The earlier rule (this log, 2026-06-13 "DOCTRINE — CLAUDE.md 'Done ='") that a live `npm run dev` holds the warehouse SQLite WAL lock and blocks the next `warehouse:backfill`/gate is now MITIGATED: `openWarehouse` sets a 15s `busy_timeout`, so a live dev server no longer blocks `warehouse:backfill` (and never blocked the gate). The "stop dev/preview servers before returning" rule in CLAUDE.md "Done =" now stands on the RAM rationale alone (5.7 GB box); its former WAL-contention WHY was trimmed out of CLAUDE.md and lives here. See also `shared-checkout-cofile-patch-hazard.md` (the `busy_timeout` fix landed on `fix/warehouse-busy-timeout`).

## 2026-07-08 — Title contradiction reconciled: "Principal" confirmed current, supersedes 2026-06-10 "VP Acquisitions" ruling

A formal CLAUDE.md audit found an unreconciled record: a 2026-06-10 ratified decision set Gabriel's title to "VP Acquisitions (Cowork 'Principal' REJECTED)," but CLAUDE.md, `user.md`, and `firm.md` all currently state "Principal" with no logged reversal — meaning either the reversal happened without being logged, or the doctrine was stale. During this same session CLAUDE.md's Identity line was independently confirmed/updated back to "Principal" by a concurrent writer, consistent with `user.md`/`firm.md`. Logging this explicitly: **"Principal" is the current, correct title, superseding the 2026-06-10 "VP Acquisitions" ruling.** If this reversal was itself a considered decision rather than drift, that context isn't captured here — flag for Gabriel to confirm if it matters later.

## 2026-07-08 — Edit-tool/bash-mount sync divergence documented (rules.md §11)

Cowork deal session (DollarGeneral-Cincinnati v03 model deliverables) hit the Edit-tool/bash-mount sync bug twice on large diffs: a Windows-side Read confirmed a write while the bash-mounted view of the same file still showed stale length/content. Logged as a standing verification rule in `memory/rules.md` §11 — past a certain diff size, cross-check the bash-side file (`wc -l`/`stat`/grep) after every Edit rather than trusting the Windows-side Read alone. Observation beats memory; this supersedes any prior assumption that a single Read confirms a landed write.

## 2026-07-08 — Scheduled-task fleet-loss incident CLOSED (root cause, recovery, and two recovery-time near-misses)

**Summary:** What started as a question about 2 retired tasks showing live in a stale roster uncovered that the entire CC/MCP scheduled-task registry had been destroyed by a 2026-07-05 Desktop app reinstall (`AppData\Local\AnthropicClaude`→`AppData\Local\Claude` relocation, clean wipe, no crash), leaving ~14 CC-only functions (financial-code-integrity-sweep, master-workbook-ingest, pm-ledger, task-integrity-guard, health-guard, and 9 others) dark for ~3 weeks with zero alarm — the one guard built to catch exactly this was itself a fleet member and died with the registry. Full forensic timeline, content-mapping analysis, and recovery detail: memory `oxford-cc-repo-health.md`.

**Recovery:** 8 tasks re-registered to CC/MCP via the supervised `create_scheduled_task` flow, sourced from the last-known-good `_state-history/2026-06-22.json` snapshot; 10 tasks formally retired and archived (including the original two flagged tasks). Recommendation (restore vs. accept Gabriel's 6-task consolidation) was content-verified before deciding, not name-matched — the new tasks were a thin briefing layer, not a real replacement for 5 HIGH-criticality functions.

**Two near-misses during recovery, both process lessons:**
1. **Concurrent duplicate registration** — Gabriel was independently running his own recovery in a parallel Cowork session, unannounced. Both sessions registered `ora-health-guard`/`ora-pm-ledger` into different fleets minutes apart. Caught by re-verifying live registry files directly, not by trusting a prior tool response. **Lesson:** when a shared-state incident is being fixed, check for concurrent writers before assuming exclusive access — same principle as the git single-writer doctrine, generalized to the scheduler registry.
2. **Destructive delete** — asked to remove LAMS duplicates + re-retire resurrected tasks, Gabriel used the Cowork sidebar's "delete" instead of "disable." This is folder-destructive (documented since a 2026-06-11 incident) and hard-deleted shared OneDrive spec files that 4 CC redirect-stub tasks depended on, breaking them too. **Lesson:** "delete" and "disable" are not interchangeable in this UI, and the blast radius crosses fleets when a spec file path is shared — this is now called out explicitly in `register-scheduled-task`'s existing ARCHIVE-FIRST-DELETE-SECOND section (no change needed there, it already says this — the miss was in relaying "disable" clearly enough in the moment).

**RATIFIED retirements (auto-ratifies any registry-membership-probe drop alarm for these ids, ≤14d window):** ora-setup-audit, ora-dormant-thread-revival, ora-weekly-tooling-intel-sweep, ora-week-ahead-briefing, ora-open-sessions-board, ora-skill-text-audit (CC copy only — LAMS copy is live/legitimate), ora-consolidate-memory-monthly (CC copy only), ora-dashboard-refresh (CC copy only), ora-lease-expiration-action-list, ora-automation-health-monitor (CC copy — superseded by LAMS `automation-health-monitor`), ora-quarterly-compliance, ora-annual-budget-kickoff, ora-lender-covenant-tracker, ora-cash-position-snapshot, ora-debt-maturity-snapshot.

**Final state 2026-07-08:** CC/MCP 5 enabled (`ora-deal-sourcing-scan`, `ora-financial-code-integrity-sweep`, `ora-master-workbook-ingest`, `ora-monthly-portfolio-briefing`, `ora-task-integrity-guard`) + 3 disabled pending action (`ora-health-guard` — content genuinely lost, needs OneDrive-online-recycle-bin recovery, do not reconstruct from memory; `ora-pm-ledger` + `ora-weekly-hygiene` — rebuilt self-contained, disabled pending Gabriel's confirmation to re-enable). LAMS 16 enabled, matches the 2026-07-08 fleet audit's ratified core-18 exactly.

**Open items (tracked live in session-context.md, not repeated here):** purge 2 dangling disabled LAMS entries; fix the `ora-operations-extensions:debt-management` skill's stale references to retired tasks (root cause of the resurrection loop — plugin source not reachable from this machine to fix directly, needs the Cowork surface); decide `automation-health-monitor` canonicalization; decide `ora-cam-reconciliation-annual` timing.

**Status:** Incident CLOSED. Residual items are small, non-urgent, and tracked in session-context.md's consolidated retirement list + open-items note.

## 2026-07-08 — Debt-management doctrine contradiction RESOLVED (skill deps removed)

Gabriel deleted the two over-restored scheduled tasks (`ora-debt-maturity-snapshot`, `ora-lender-covenant-tracker`) on the Cowork surface, then directed removal of their references from the `ora-operations-extensions:debt-management` skill — closing the resurrection-loop root cause flagged in today's earlier reconciliation entry.

**Change:** removed both references (the description "Consumes outputs from … scheduled tasks" sentence + the two `## Inputs` bullets) and bumped v1.0→v1.1 in BOTH on-disk copies:
- Loaded runtime cache: `…\local-agent-mode-sessions\…\rpm\plugin_01Sq7t7TEQEoa4G1asrLe8ms\skills\debt-management\SKILL.md`
- Source pack: `Claude_Workspace\01_Workspace\20260428_ORA-Skills-Pack_v01\debt-management\SKILL.md`

Verified 0 remaining references in both (grep). The skill's remaining debt inputs (Notion debt schedule, SharePoint loan docs, uploaded term sheets, capital-markets benchmarks) fully cover the underlying data — the deleted tasks were only automated refreshers.

**CAVEAT:** if `ora-operations-extensions` is platform-managed (claude.ai marketplace), the runtime-cache edit may revert on the next plugin re-sync. Re-stage via `package-and-stage-skill` + Save-skill to persist through re-sync; the v1.1 bump will make `ora-skill-store-drift-check` flag it for re-upload.

## 2026-07-08 — portfolio-growth DSCR-Floor annotation (governor semantics, no value change)

**Trigger:** ora-health-guard's governor-drift probe flagged `portfolio-growth/SKILL.md`'s "DSCR Floor" line as a possible genuine-drift hit — it had scoring context to lean on for `deal-comparison`'s 1.25x references (likely-intentional) but nothing comparable for portfolio-growth, so it surfaced as a false positive requiring manual review.

**Investigation finding — premise correction:** the original fix request assumed portfolio-growth currently read "1.75x" (a portfolio-blended floor) in two spots and needed relabeling to distinguish it from the 1.25x per-property floor. Ground-truth read of the file showed both spots already read **1.25x**, not 1.75x. A repo-wide grep confirmed the string "1.75x" does not exist anywhere in `ora-skills` — every DSCR reference (acquisition-underwriting, deal-comparison, oxford-cc-strategic-audit, portfolio-growth) uses 1.25x, matching the global per-property governor (CLAUDE.md: "DSCR ≥ 1.25x"). There is no portfolio-blended DSCR floor value tracked anywhere in the skill set.

**Resolution (user-confirmed, "annotate only, keep 1.25x"):** left the 1.25x value untouched in both spots (CORE PARAMETERS table + MODULE 2 DSCR Check) and added clarifying text that this is the *per-property* floor — the same governor applied at acquisition underwriting — and that portfolio-growth does not currently track a separate portfolio-blended cushion figure. Zero numeric governor values were changed.

**Why this matters going forward:** the health-guard probe's ambiguity trigger (bare "DSCR Floor" / DSCR-value line with no per-property-vs-portfolio qualifier) is now resolved for portfolio-growth specifically — future runs should not re-flag this file's DSCR Floor line as unexplained drift. If a genuine portfolio-blended DSCR floor is ever introduced (a different number from 1.25x), that is a governor-constant change requiring explicit sign-off per CLAUDE.md invariant 4, not a documentation fix.

## 2026-07-08 (evening) — Claude tool/MCP setup review: Mnemoverse retire recommended, Desktop Commander duplicate found, excel MCP confirmed non-connecting, scheduled-fleet counts corrected

**Trigger:** Gabriel pasted a generic Claude-tools cost/config report; reviewing it against the actual Claude Code setup surfaced one concrete item (Mnemoverse Memory MCP redundancy), which led to a 3-task subagent-driven investigation (Mnemoverse disposition, adversarial re-scan of the review's own "already optimal" claims, scheduled-fleet timing vs. Max-plan shared usage-limit).

**Mnemoverse_Memory MCP — RETIRE recommended.** `memory_stats` returned 0 memories/episodes/associations; confirmed empty via a targeted `memory_read` sanity check against facts known to exist in the real memory system. Referenced nowhere except one passive line in `docs/system-inventory.md` — not integrated into CLAUDE.md, any skill, or any hook. Disconnect requires Gabriel's action in Claude Desktop's Connector settings; confirmed it is not reachable via any local config file (`~/.claude.json`'s `mcpServers` only lists `context7` and `excel`).

**Desktop Commander is connected twice, via two different mechanisms.** `Desktop_Commander` (26 tools) and a separately-surfaced `plugin:desktop-commander:desktop-commander` (identical 26-tool set) both connect every session, doubling schema overhead for zero capability gain. Neither appears in `~/.claude.json`'s `mcpServers` nor in `installed_plugins.json`'s Code-plugin list — both are Connector/platform-level integrations, not locally-editable from Code. Needs Gabriel to pick one and disconnect the other via the Desktop app's Connector settings.

**`excel` MCP is configured but not actually connecting.** `~/.claude.json` has a valid `excel` stdio entry pointing to `C:\Users\Owner\.local\bin\excel-mcp-server.exe` (file confirmed present on disk, 46KB), and no project-level `mcpServers` override disables it (every per-project entry checked is empty). Yet it appears in neither the live nor deferred tool list for this session. Since the `underwriting-checker` subagent's mandatory adversarial financial-model check depends on exactly this tool, its Excel access is likely non-functional right now — worth a live verification next time that subagent actually runs.

**Scheduled-fleet cached counts in session context were stale; corrected via live pull.** CC/MCP: **6 enabled** (not 8) — `ora-weekly-hygiene` and `ora-pm-ledger` are intentionally disabled pending recovery stabilization, not missing. LAMS/Cowork: settled at **18 enabled / 4 disabled** (not "still rebuilding ~20-22") — the 07-08 over-restoration incident (`ora-lender-covenant-tracker`, `ora-cash-position-snapshot`) has already self-corrected back to disabled. Combined enabled total: **24**, materially above the ~16 prior mental model. `lastRunAt` fields confirm the catch-up-burst mechanism is empirically real, not theoretical (6 CC tasks with nominal times spanning a full week all fired within a 53-second window on 2026-07-07 at ~2:43 PM ET). One concrete retime recommended: move LAMS `automation-health-monitor` (weekdays 11:00, confirmed reliably on-time rather than burst-smeared — the one high-frequency, business-hours-nominal task in either fleet) to a pre-8am slot alongside the other reliably-on-time morning tasks. Not executed — LAMS/Cowork task updates require a supervised Cowork session per registration doctrine, not a Code session.

## 2026-07-08 — Fleet "discrepancy" RECONCILED: CC/MCP registry was never lost (07-05 reinstall + transient recovery gap)

**Trigger:** Gabriel asked (this session, off the back of the ora-financial-code-integrity-sweep run) to reconcile the 2026-07-07 UNRATIFIED "FLEET DISCREPANCY" banner in `session-context.md` claiming the CC/MCP `scheduled-tasks.json` was MISSING entirely.

**Read-only diagnosis (NO registry / SKILL.md / generated-block writes):**
- The 2026-07-05 Desktop app reinstall wiped the CC/MCP registry. The 2026-07-07 11:51 `registry-membership-probe.py` run fired BEFORE the store was recreated under its new session dir, so it correctly-but-transiently reported `cc=0/MISSING` — a recovery gap, not a silent entry-drop.
- Store now present: `…\claude-code-sessions\a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\583f08bc-0123-4111-8158-8fe3d927e350\scheduled-tasks.json` (3052 B; CC tasks createdAt ~16:45 07-07; file last written 07-08 07:46). This is why the 11:51 probe's filesystem search found nothing — the file did not exist yet at that minute, under any path.
- VERIFIED LIVE 07-08 (direct registry read + MCP `list_scheduled_tasks`): **CC/MCP = 8 tasks**, recovered from the 2026-06-22 fleet snapshot. Enabled: `ora-financial-code-integrity-sweep`, `ora-monthly-portfolio-briefing`, `ora-task-integrity-guard`, `ora-deal-sourcing-scan`. DISABLED: `ora-master-workbook-ingest`, `ora-health-guard`, `ora-weekly-hygiene`, `ora-pm-ledger`.
- **LAMS/Cowork = 20 tasks** (NOT 6 per the alarm, NOT 8 per the generated block — both stale). Fleet still being actively rebuilt: newest add `ora-debt-maturity-snapshot` createdAt 07-08.
- HALT / Phase-B ambiguity RESOLVED: this is SAME-MACHINE disaster recovery after the reinstall (task SKILL headers say "Restored 2026-07-07 … recovered from the 2026-06-22 fleet snapshot"), NOT Phase B migration. The new machine has NOT arrived; the HALT note stands.
- Deliberately did NOT re-run the probe: it would race the active recovery writer and raise a spurious `ora-weekly-tooling-intel-sweep` drop-alarm (that task is in the stale generated block but absent from the live LAMS registry). The next daily probe self-refreshes the block.

**Action taken:** rewrote the `session-context.md` prose note (line 6, OUTSIDE the generated markers) from "⚠️ FLEET DISCREPANCY / MISSING" to "✅ FLEET RECOVERY — RECONCILED 2026-07-08," carrying the verified live counts, the enabled/disabled split, and the two open items below. No registry, SKILL.md, or between-markers edits.

**Decision (this session, Gabriel):** re-enable the 2 consequential disabled CC tasks, keep the other 2 dark during recovery. Executed via supervised MCP `update_scheduled_task` (NOT a JSON splice): `ora-master-workbook-ingest` → enabled (nextRunAt 2026-07-13T09:54Z) and `ora-health-guard` → enabled (nextRunAt 2026-07-09T09:24Z), both verified via `list_scheduled_tasks`. Left DISABLED by decision: `ora-weekly-hygiene`, `ora-pm-ledger`. CC fleet now 6 enabled / 2 disabled.

**Tooling hardening (systematization — Gabriel authorized all 4 candidates, built this session; TDD, 17/17 green, py_compile clean, real-data validated):**
- `maintenance/registry-membership-probe.py`: (a) whole-store absence is now transient for `MISSING_STORE_GRACE_RUNS=2` consecutive runs before escalating to [ACTION] (the exact 2026-07-05 false-CRITICAL is now a WARN); (b) enabled→DISABLED is a WARN **regression**, no longer mislabeled as a silent DROP (new `classify_absent` + `all_recurring_states`; validated live = pm-ledger/weekly-hygiene correctly regressions, 0 drops); (c) a "membership CHANGED — re-run until 2 clean runs" flux signal during recovery. AUTHORITATIVE `.ps1` guard engines left untouched by design.
- `maintenance/append-event-log.py`: spool-and-drain fallback — on an OS file-handle lock that survives the retry loop, the entry is parked under `event_log.md.pending/` and auto-drained (oldest-first, newest-on-top preserved) on the next run, instead of being lost. (This very entry was blocked by exactly that lock 3× earlier today.)
- New regression tests: `maintenance/_tests/test_hardening.py`.

**LAMS formal audit (opus subagent, read-only) — RED FLAGS (over-restoration is ACTIVE):** live LAMS drifted 20→22 DURING the session. Two ratified do-NOT-re-register tasks were registered AND enabled at 2026-07-08 12:10 by the recovery process: `ora-lender-covenant-tracker` (`0 9 1 1,4,7,10 *`) and `ora-cash-position-snapshot` (`30 6 * * 1`). `ora-debt-maturity-snapshot` (retired list) was resurrected 11:46 then self-disabled/archived, leaving a dangling disabled entry (no live SKILL.md); `ora-weekly-sourcing-digest` likewise dangling. Doctrine contradiction fueling the loop: debt-maturity-snapshot was re-retired citing lender-covenant-tracker as its "replacement" — but that task is itself ratified-unneeded. 18 of the 20 snapshot tasks are legitimate, routing-compliant (COM-only, ggoldberg-only). Duplicate folders: thin registered `automation-health-monitor` stub vs orphaned richer `ora-automation-health-monitor` v1.5; orphan `ora-week-ahead-briefing` duplicates `ora-friday-closeout`.

**STILL OPEN for Gabriel (registry writes — NOT actioned; active concurrent recovery writer + get-go-ahead promise):** (1) RE-RETIRE the 2 ratified-unneeded tasks now live (`ora-lender-covenant-tracker`, `ora-cash-position-snapshot`) + purge the 2 dangling disabled entries (`ora-debt-maturity-snapshot`, `ora-weekly-sourcing-digest`). (2) Resolve the debt-management doctrine contradiction (the `ora-operations-extensions:debt-management` skill names both retired tasks as inputs — either the ratified-unneeded ruling or the skill's deps are stale; this will keep causing resurrection loops). (3) Canonicalize the health-monitor (thin registered stub vs richer orphan v1.5). (4) Confirm the intended LAMS set; re-enable `ora-weekly-hygiene` + `ora-pm-ledger` when recovery stabilizes.

## 2026-07-07 (evening) — Systemic-fixes session: Outlook COM diagnosis + hardening, stale `(1)`-OneDrive-root retirement, workspace consolidation; collided mid-execution with a concurrent `ora-task-integrity-guard` self-heal burst and recovered a deleted skill file

**Trigger:** Follow-up to the weekly-hygiene run's 5 optimization candidates + 2 systemic issues (Outlook COM outage, fleet-registry volatility). Investigated all four via parallel agents, synthesized a 7-phase implementation plan (saved to `Claude_Workspace/00_Governance/outputs/2026-07-07_SystemicFixesImplementationPlan_v01.md`), then executed the safe/no-mutation phases.

**Outlook COM outage — root cause found and hardened:** a headless, DCOM-spawned Outlook instance (`OUTLOOK.EXE -Embedding`, parent `svchost.exe`) gets stuck on the first-run "Welcome to Microsoft Outlook 2016" wizard whenever no interactive session exists, explaining all three symptoms (RPC_E_CALL_REJECTED, E_ABORT, indefinite hangs). Hardened `send-via-outlook.ps1`: added a preflight check (exits 3 immediately if Outlook is stuck, no COM attempt), wrapped the COM send in a `Start-Job`/`Wait-Job -Timeout 15` (exit 4 on timeout instead of hanging), and added a single bounded retry for RPC_E_CALL_REJECTED before hard-failing (exit 2). **Also fixed a latent bug found during verification:** `Write-Log`'s `Write-Error` call, combined with the script's `$ErrorActionPreference="Stop"`, was silently terminating the script before any `exit N` line ran — every error path was collapsing to PowerShell's default exit code 1 regardless of the intended code. Fixed with `-ErrorAction Continue` on that one call. Verified live against the still-stuck instance (PID 6824): now returns `exit=3` in ~2s instead of hanging 35-50s. **The Outlook unblock itself (killing PID 6824) is GATED on Gabriel's confirmation — not done autonomously**, per the plan's explicit risk classification (affects a live desktop app).

**Stale `(1)`-suffix OneDrive-root retirement:** confirmed and closed out the class of bugs from 6 live scripts hardcoding the dead pre-migration `OneDrive - Oxford Capital Partners (1)` root. **Mid-execution, discovered `ora-task-integrity-guard`'s own scheduled run had already fixed the same 6 files** in a 14-second window (15:53:58–15:54:12) via a catch-up-burst self-heal — confirmed via file mtimes, not assumed. Completed the two DATA steps the self-heal did NOT do: migrated `2026-07-05_Fleet-Rebuild_Register_v01.md` out of the dead `(1)\...\outputs\` folder into canonical `_archive_2026-06-11_orphans\`, and replaced the canonical `_state-history\membership-state.json` (a single point-in-time enabled-tasks snapshot, ts `2026-06-22`) with the newer `(1)`-path snapshot (ts `2026-07-07T18:44:17Z`) per the guard's own documented "newest-wins" semantics — backed up the pre-replacement canonical file first (never-delete). Fixed 5 additional SKILL.md documentation-only `(1)`-path references (`ora-automation-health-monitor` ×2, `ora-om-intake-ocr`, `ora-owner-outreach-queue-refresh` ×2, `ora-replacement-cost-refresh`) that the self-heal did not touch (code-only, not docs). Three other planned SKILL.md fixes (`ora-connector-preflight-guard`, `ora-claude-workspace-hygiene`, `ora-inbox-pre-brief`) turned out to target files already correctly archived in `_archive_2026-06-11_orphans\` per the 2026-06-21 Block F resolution — not live, no fix needed, skipped. Final re-scan: 0 stale-path occurrences across all 10 targets; all 3 Python scripts `py_compile` clean; all 3 PowerShell scripts parse clean.

**`ora-weekly-hygiene`'s authoritative SKILL.md was found DELETED from disk** (`Documents\Claude\Scheduled\ora-weekly-hygiene\` held only the `_unsent\` subfolder from earlier today's hygiene run) — unrelated to the guard.ps1 self-heal (that only touches thin pointer stubs in 3 mirror locations, all confirmed intact and unaffected). Likely removed during the same-day LAMS task-folder churn (14:54 window). **Recovered verbatim from this session's own in-context copy** (read directly from the file before its disappearance, at this session's start) and restored to disk with a RESTORATION NOTE 2 documenting the incident. Applied the planned Block C rewrite on top of the restored content in the same write: removed the non-existent `sites/ClaudeWorkspace` team-site target and fictional `/Deals/` etc. folder list (kept only as a one-line historical explanation of what was wrong), retargeted to the two real personal OneDrive-for-Business drives (`ggoldberg_oxfordra_net`, `egoldberg_oxfordra_net`), and switched the aging mechanism from unreliable SharePoint content-search dates (proven wrong: returned 2013 for a 2026 file) to folder-enumeration via `sharepoint_folder_search` + `read_resource` using the Graph `lastModifiedDateTime` field. Verified: 223 lines (was 216 + 2 restoration notes), Block I intact, 0 stale `(1)` paths.

**Workspace consolidation:** archived two distinct empty/synced `Claude Workspace` (space-variant) stray folders to `_Archive\` — one empty (canonical root), one containing a real 9,841-byte file confirmed (exact mtime match) to be the sole synced SharePoint copy (kept local to the `(1)`-root's own archive per its own wholesale-retirement provenance, not the canonical archive). No deletes.

**Fleet-registry discrepancy — UPDATED, still NOT autonomously actioned:** the guard.ps1 self-heal incidentally resolved one open question — `ora-setup-audit` was not lost; it was formally retired and archived today to `.claude\scheduled-tasks\_archive_2026-07-07_retired\ora-setup-audit\`, alongside several other CC-side folders (`ora-dashboard-refresh`, `ora-consolidate-memory-monthly`, `ora-automation-health-monitor`, `ora-dormant-thread-revival`, `ora-skill-text-audit`, `ora-week-ahead-briefing`, `ora-weekly-tooling-intel-sweep`) whose names exactly match tasks simultaneously "resurrected" live under the LAMS registry earlier today. This reframes the earlier "6 retired tasks mysteriously resurrected" alarm toward "an undocumented but apparently coherent CC→LAMS fleet consolidation" — still requires Gabriel's explicit ratification (no doctrine update made), but is less alarming than first read. **No registry mutation performed anywhere in this session** — `create_scheduled_task`/`update_scheduled_task` were never called. Decision brief for Gabriel presented in-session, not written to any file beyond this log entry.

**Status:** Phases 0, 1, 2, 3, 6, 7 of the implementation plan complete and verified. Phase 4 (Outlook process unblock) awaiting Gabriel's go/no-go. Phase 5 (fleet decision) is Gabriel's call, not mine — findings surfaced, no action taken.

## 2026-07-07 (later) — Investigating 2 flagged retired-task mismatches uncovered a much bigger fleet drift: CC/MCP registry file is GONE, LAMS registry silently restructured

**Trigger:** Follow-up ask on `oxford-cc-repo-health.md`'s two "flag do not fix" items — (a) `ora-dormant-thread-revival` + `ora-weekly-tooling-intel-sweep` marked RETIRED 2026-06-16 in their own frontmatter yet still shown live in the 17-task CC/MCP roster, and (b) two archived stub families (`_archive_2026-04-21/`, `_archive_2026-05-31_orphans/`) still referencing the broken `(1)`-suffixed path.

**Verified ground truth before acting (did not trust the 2026-06-16 session-context snapshot):**
- `list_scheduled_tasks` MCP call returned "No scheduled tasks found." Direct filesystem search confirms **no `scheduled-tasks.json` file exists anywhere** under `AppData\Roaming\Claude\claude-code-sessions\` — the entire CC/MCP registry store is gone, not just mis-tagged. This makes the original "2-task mismatch" question moot: the whole 17-task roster it referenced no longer exists.
- The LAMS/Cowork registry (`AppData\Roaming\Claude\local-agent-mode-sessions\...\scheduled-tasks.json`, the only such file left on disk) now holds **6 tasks with renamed ids/crons** not matching the 2026-06-16 doctrine roster: `automation-health-monitor` (0 11 * * 1-5), `ora-am-brief` (0 6, was 10 6 under CC), `ora-friday-closeout` (30 16 * * 5), `ora-lease-expiration-brief` (30 8 * * 1), `ora-monday-sync` (30 7 * * 1), `ora-weekly-sourcing-digest` (0 8 * * 1) — confirmed genuinely live via `lastRunAt` timestamps from TODAY, not stale data. The prior 5-task LAMS roster (ora-cowork-heartbeat, ora-om-intake-ocr, ora-owner-outreach-queue-refresh, ora-replacement-cost-refresh, ora-skill-store-drift-check) is entirely absent from this file.
- `event_log.md` has **zero entries between 2026-06-22 and 2026-07-06**, and nothing in that gap (or since) documents a CC registry loss or a LAMS fleet reorg. Last scheduler-doctrine-relevant entry is 2026-06-15 (round 3, Composio/routing sweep).
- Ran `registry-membership-probe.py` to get a clean diff — **side effect I should have anticipated before running it**: it auto-regenerated `session-context.md`'s fleet-roster banner (its designed behavior) to reflect this new reality (cc=0/missing store, lams=6 with the new names) and overwrote the prior 2026-06-16 snapshot in `registry-membership.json`. Did not revert — the new data is verified-accurate live state, not a discovery artifact, and reverting would re-mask a real drop. Added a hand-authored `⚠️ FLEET DISCREPANCY` warning line directly above the generated block in `session-context.md` (outside the markers, so future probe runs won't clobber it) telling readers not to trust the CC-side doctrine elsewhere in that file until Gabriel reconciles this.

**Not attempted (needs Gabriel's call, not a mechanical fix):** re-registering the CC/MCP fleet, or updating doctrine to adopt the new LAMS task names as canonical — don't know yet whether this is (1) the Phase B migration having actually executed despite the standing HALT note ("Phase B runs ONLY on the new machine — it has NOT arrived"), (2) an intentional Cowork-side consolidation Gabriel did himself without logging it, or (3) genuine unlogged data loss. Each implies a different fix (leave alone / update doctrine to match / recover+re-register).

**Item (b) closed, no fix applied (ratifying the prior session's "leave alone" call):** the two archived stub families' `(1)`-suffixed path references are inert — those task folders are retired/archived and will never execute, so correcting the text has zero operational value and would just rewrite a dated historical record. Treating this as resolved-by-decision, not left open.

**Status:** Findings reported to Gabriel; awaiting his read on the fleet-drift root cause before any registry action is taken.

## 2026-07-07 — oxford-command-center: status.json parse fix landed + repo ref-rot repaired + gh CLI restored
- **PR #174 MERGED** (squash `57a1ebf`): `architecture/status.json` failed JSON.parse (ic-memo entry: two duplicate-key blocks, missing comma — pre-existing on origin/main, predates C-2 work). Fixed in isolated worktree off origin/main, claimed via the file's own status-entry protocol, CI (gate + refute-required) green, post-verified origin/main parses. Overlapping unmerged branch `fix/status-json-duplicate-key` (3369e17) left alone per Gabriel — remaining value is stale-entry cleanup only.
- **Repo ref-rot repaired:** 23 tombstone refs (14 local, 9 remote-tracking) pointed to pruned objects, breaking every commit/fetch (`bad object` + geometric-repack failure) and silently blocking fetch ref-updates. All 15 branch names confirmed gone from origin; refs deleted with `update-ref -d`, reflogs expired, `git gc` + `git fsck --connectivity-only` both exit 0. Pre-surgery backup: `.git/archive-refs-backup-2026-07-07/`.
- **GitHub credential path restored:** gh.exe was missing (auth store too) while `~/.gitconfig` scopes github.com credentials exclusively to it — plain push/fetch was broken machine-wide. Worked around via GCM (`-c credential...helper=manager`); GitHub CLI reinstalled via winget; auth re-seed recipe in memory `reference_github_credential_path.md`.
- Merged worktree/branch cleaned up (local + remote); memory files `reference_github_credential_path.md` + `oxford-cc-repo-health.md` written.

## 2026-07-06 (later still) — CRITICAL: oxford-command-center local git object database is EMPTY — halted "finish the command center" work, did not proceed

Gabriel asked (going to bed) to "proceed with all recommendations" and finish `oxford-command-center` autonomously overnight. Pre-flight recon before touching code: `git status` on the main checkout failed `fatal: bad object HEAD`.

**Diagnosis (all read-only, no destructive commands run):**
- `git fsck --full` reports **every single ref in the repo** (all ~100+ local branches, all 23 worktrees, origin/main tracking ref) as "invalid sha1 pointer" — not one specific bad commit.
- Root cause: `.git/objects` contains only the 256 empty hex skeleton subdirectories — **zero loose object files**, and `.git/objects/pack/` is also **empty**. The entire local git object database (every commit/tree/blob) is gone. `.git` total size is 3.1 MB (should be tens/hundreds of MB for this repo's history) — consistent with total object loss, not a single-file glitch.
- Directory mtimes on `.git/objects/*` range up to 2026-06-23 ~10:17, so whatever deleted the contents happened sometime between 2026-06-23 and today (2026-07-06) — window not narrowed further; no forensic tool available here to pin down cause (antivirus quarantine, disk issue, bad cleanup script, and failed `git gc` are all consistent with the symptom; not determined).
- **Good news, verified:** the actual working-tree files (checked-out source) are physically intact — `package.json` + 175 files under `src/` present and readable in the main checkout. So current on-disk code is NOT lost; only git's history/metadata is.
- **Recovery path:** anything ever pushed to `origin` (`github.com/ZeOoba/oxford-command-center`) is safe there regardless of local corruption — a `git fetch`/re-clone restores it. Attempted a safe, non-destructive `git fetch origin` to test this. Blocked: the repo's per-URL credential override `credential.https://github.com.helper` points at `C:\Program Files\GitHub CLI\gh.exe`, which no longer exists on this machine (GitHub CLI appears uninstalled/moved — `where gh` and a Program Files search both came up empty; a `winget install GitHub.cli` attempt hit an interactive msstore-agreement prompt with no stdin available). Fell back to the installed `git-credential-manager.exe` directly (`-c credential.helper=manager`) — this opened an interactive sign-in flow (browser/dialog) and hung; killed after 60s. **Fetch/auth needs Gabriel's interactive sign-in — cannot be completed autonomously**, same shape as the OneDrive OAuth block from earlier tonight.
- Any LOCAL-ONLY, never-pushed commits (across the ~20 active worktrees / branches) are at real risk of being unrecoverable via git once `git fetch` is available and diffed against — this needs a careful manual pass per worktree once auth is restored, not an autonomous one.

**Decision: did NOT proceed with "finish the command center" feature work.** Building new commits, running `npm run gate`, or touching any worktree on a repo whose object database is provably empty risks compounding real data loss and was assessed as squarely inside the hard-invariant "destructive/irreversible action" pause condition — overrides the standing autonomy grant. No git surgery attempted beyond read-only diagnostics (`fsck`, `cat-file -t`, `ls`, `git worktree list`, one failed `fetch`). Nothing was reset, deleted, gc'd, or force-pushed.

**For Gabriel on waking, in order:** (1) sign in to `git-credential-manager` for `github.com` (or reinstall GitHub CLI) so `git fetch origin` can complete: try `cd C:\Users\Owner\oxford-command-center && git fetch origin` interactively and complete whatever auth prompt appears. (2) Re-run `git fsck --full` after fetch — most/all refs should resolve again since GitHub holds full history for anything pushed. (3) Audit each of the 23 worktrees (list in this entry's session transcript / `git worktree list` output) for local-only unpushed commits before touching/removing any of them — some may hold real WIP that predates the object loss and needs to be diffed/salvaged first. (4) Only after (1)-(3): resume the "finish the command center" build-out using [[ora-intelligence-platform-master-plan]] / [[cc-build-state]] / [[cc-autonomous-audit-pr28]] as the source of "recommendations," via `subagent-driven-development` + isolated worktrees per the existing multi-writer doctrine in `oxford-command-center/CLAUDE.md`.

## 2026-07-06 (later) — Resolved the 3 blocked items from the document-assembly correction; found a real probe path bug

Follow-up to the entry below. Gabriel signed OneDrive back in; resolved all 3 blockers:

1. **Python:** was not installed at all (only a non-functional Store-alias stub). Installed Python 3.13.14 via `winget install Python.Python.3.13` (official python.org build). `python3` now resolves; `doctrine-integrity-probe.py` and `append-event-log.py` both run.
2. **OneDrive:** was not running; started `OneDrive.exe`. It came up with a configured account but `OneAuth is not configured` until Gabriel completed interactive sign-in (I cannot do this — needs credentials/MFA). Confirmed post-sign-in: `Get-Content` on all 3 previously-inaccessible files now succeeds.
3. **The 3 "ported copy" files themselves — turned out NOT to be doctrine copies at all** (re-read after hydration, verified by content, not guessed): `Claude Command Center Code\CLAUDE.md` = dashboard UI project notes; `Claude_Workspace\01_Workspace\CLAUDE.md` = a "thin pointer" (de-staled 2026-06-10) that explicitly names `~/.claude/CLAUDE.md` as the canonical operating prompt and holds no doctrine content itself; `Claude_Workspace\01_Workspace\oxford-site\.claude\CLAUDE.md` = the oxfordra.net site repo's project instructions. None contain "ORA Global Operating Prompt", "Skill tie-breaks", or the corrected sentence — no edits needed. The prior entry's "re-check once OneDrive is back online" action item is now closed: **`~/.claude/CLAUDE.md` was and remains the sole copy of the master doctrine on this machine.**

**New finding (out of scope of the original task, flagged not fixed):** this machine has TWO OneDrive business accounts syncing in parallel — `egoldberg@oxfordra.net` → `OneDrive - Oxford Capital Partners` (no suffix, holds the real, actively-maintained `Claude_Workspace/01_Workspace/...` tree) and `ggoldberg@oxfordra.net` → `OneDrive - Oxford Capital Partners (1)` (holds only a near-empty `Claude Workspace/00_Index`, no `01_Workspace`). `doctrine-integrity-probe.py` line 105 hardcodes `WORKSPACE = HOME / "OneDrive - Oxford Capital Partners (1)" / "Claude_Workspace"` — i.e. it scans the WRONG account's folder for Cowork-surface skills, so it will report `skill-scan root unavailable` / degrade every skill-reference check to a non-drift WARN forever, independent of OneDrive sign-in state. This is a probe bug, not a sync problem. Fix is a one-line path change (drop the `(1)`); not applied — flagging for Gabriel's call since it's outside the 3 items asked for and touches doctrine-guard tooling.

## 2026-07-06 — Doctrine correction: document-assembly mis-routed as IC memo owner

**Was:** ORA Global Operating Prompt "Skill tie-breaks → Deal evaluation" line routed the funnel `deal-comparison` → `loi-generation` → `document-assembly` (IC memo) — implying document-assembly owned IC memo production.

**Corrected to:** `acquisition-underwriting` FULL mode produces its own canonical 12-section IC memo (Exec Summary → Thesis → Property → Market → Tenancy → Financial Analysis → Debt/Capital Structure → Risk/Pre-Mortem [mandatory] → Edge Scan [4-category floor] → Replacement Cost Analysis → Exit/Hold → Recommendation) — mandatory pre-mortem, Edge-scan floor, bear-mode state, DD-Critical status, RCT v02 citation baked in. `document-assembly`'s Template 2 IC Memo is a thinner, generic, manually-fed template with none of that — it is now routed as a fallback only ("use only if acquisition-underwriting is unavailable"), never the default destination. Funnel now reads: `verified-deal-recon` → `deal-comparison` → `loi-generation` (document-assembly dropped from the chain).

**Why:** verified by reading both live SKILL.md files directly — `acquisition-underwriting` v3.3's IC Memo Structure section supersedes `document-assembly`'s Template 2; routing the funnel through the thinner template was a doctrine bug, not a deliberate handoff.

**Files touched:** `C:\Users\Owner\.claude\CLAUDE.md` (Skill tie-breaks section, one line edited; no other lines changed).

**Not touched / could not verify:** 3 other candidate ported-copy locations — `OneDrive - Oxford Capital Partners\Claude Command Center Code\CLAUDE.md`, `OneDrive - Oxford Capital Partners\Claude_Workspace\01_Workspace\CLAUDE.md`, `OneDrive - Oxford Capital Partners\Claude_Workspace\01_Workspace\oxford-site\.claude\CLAUDE.md` — all three are OneDrive cloud-only placeholders and could not be hydrated (`Get-Content` fails: "the cloud file provider exited unexpectedly"; OneDrive sync process is not running on this machine). Re-check and patch these once OneDrive is back online — do not assume they match the corrected wording. `doctrine-integrity-probe.py` could not be run — no working Python interpreter is present on this machine (only a non-functional WindowsApps Store alias stub); substituted a plain-text grep/diff verification (zero remaining matches of the old sentence; exactly the one targeted line changed in `CLAUDE.md`). This entry was appended manually via the Edit tool (not `append-event-log.py`) for the same reason, following the script's exact insertion convention (newest entry directly above the prior first `## ` header).

## 2026-06-22 — INTEL_CONFIG.healthWeights re-ratified (Gabriel Goldberg)

Gabriel Goldberg explicitly ratified INTEL_CONFIG.healthWeights as correct on 2026-06-22 (human-gate decision). Weights have been live since original ratification 2026-06-14 (Option B, NOI-centric). No changes to values — confirmation that the evidence accumulated since original ratification supports keeping the current weights.

Weights confirmed (unchanged):
  revenueGrowth: 0.10 Â· revenuePerSfGrowth: 0.08 Â· noiGrowth: 0.22 Â· noiPerSfGrowth: 0.18
  expenseEfficiency: 0.10 Â· taxEfficiency: 0.05 Â· insuranceEfficiency: 0.05 Â· repairEfficiency: 0.05
  marginStability: 0.07 Â· benchmarkPosition: 0.10
  healthBands: excellent ≥80 Â· good ≥65 Â· watch ≥50 (concern <50)
  growthScoreCapPct: 0.20

Any future weight change: evidence from calibration_verdict log + Â±0.05/yr cap + Gabriel sign-off + refute-financial-change pass required.

## 2026-06-21 — Open-sessions board run + probe MemoryError fix (2 decisions)

Probe `open_sessions_probe.py` was crashing with `MemoryError` on this 5.7 GB box: it `json.load`-ed all 1,065 session metadata files at once, each carrying a ~540 KB `remoteMcpServersConfig` blob (774 LAMS metas = 485 MB). Fixed in-place: stream the two stores lazily, replace full-parse with a regex `_load_meta_lite` reader that grabs only the 7 needed scalars (all sit before the blob), and catch `MemoryError` in the transcript readers. Probe now runs clean (36 actionable / 403 unarchived). Board cross-check: 22 of ~26 actionable rows already decided on the 6/12/6/14/6/20 boards (skipped). New decisions: **Information Lane parking → Drop** (sources image-only, OCR failed; not worth chasing). **Session backlog → prep archive list**: 296 NO-ACTION sessions (187 fleet-run residue bulk-safe + 109 human) written to `~/.claude/2026-06-21_session-archive-candidates.md` for sidebar archiving (archive_session approval-gated, can't run under bypassPermissions). Deal-card staleness reconfirmed: Tollway SKIP'd 6/14, Goodwill DROPPED 6/12, DG PASS'd 6/8, E. Fulton on RENEG-A+ track (feasibility 7/2, close 8/5).

## 2026-06-20 — Open-sessions board decisions (2 actionable)

Daily ora-open-sessions-board (probed 199 unarchived / 2 actionable, both Cowork). Gabriel's board answers:

- **Port Sheldon acquisition underwriting** (Cowork `local_1a93a886-928c-4808-a855-6b2df5f35d53`) — verdict was PASS / FLOOR-FLAGGED (basis floor fails on both GR-native and Cincinnati replacement-cost denominators; ask ~40% above where comparable Grand Rapids/Ottawa County buildings actually trade). **Decision: leave Cincinnati replacement-cost as the standing denominator for this file** — v03 model/IC memo/Notion already carry the Cincinnati override; no GR-vs-Cincinnati side-by-side sensitivity to be added. No pipeline-table entry (screen-stage PASS, not advanced).
- **Off-market candidate scorecard** (Cowork `local_2f24bff9-fa65-4607-a6d1-a4a19f032c6e`) — STALLED after fixing the Boone acreage (#4), before building #5 (the quarterly refresh task). **Decision: resume and finish #5.** Resumption must happen in the Cowork session (holds the scorecard items 1–5 context); the refresh task registers on the LAMS/Cowork surface, not CC/MCP. Overlap flag noted for that session: LAMS already runs ora-replacement-cost-refresh (quarterly) + ora-owner-outreach-queue-refresh (weekly) — scope #5 so it doesn't duplicate them.

## 2026-06-14 — Open-sessions board decisions (5 PM triage)

Gabriel answered the 2026-06-14 ora-open-sessions-board (12 cards). Governing instruction: **execute one at a time to avoid memory issues** (5.7 GB workstation, low free RAM). Decisions:

- **Run command** (local_59e78073) — **DROP**.
- **ora-pm magic-link / PM software bug** (local_248c8fd0) — **SEND FRESH LINK NOW** (production magic-link to ggoldberg).
- **Dollar General broker draft** (local_b4d2042d) — **DROP** (3-pack already PASSed 6/8 as out-of-box retail; no email sent).
- **AI agents/routines sourcing close-out** (local_0e1cb816) — **DROP** (2 PASSes not logged, Newton KS not triaged).
- **OM Hassel / Tollway Center, Hoffman Estates IL** (local_8ba79fcc) — **LOG THE SKIP** to Deal Sourcing Log (out-of-box: Cook County, 74.6K SF > 50K cap, concurrent re-roof + full rollover).
- **Worktree cleanup + 2 optimizations** (local_31ea6e0c) — **RESUME** (continue in its own session into one PR).
- **Governor/integrity probe fixes** (local_01a8193b) — **SPAWN REVIEWER** (one more opus adversarial pass on the BLOCKER-fixed code, in its own session).
- **Phase B migration** (local_be8bd88b) — **KEEP PARKED** (standing HALT: NEW machine only).
- **Recent sessions triage** (local_72488e7b) — **DROP** (superseded by this board).
- **API key setup for go-live** (local_1bb5e74b) — **DROP** (CC live-AI already done).
- **Best public Claude Code setups** (local_f8e28515) — **DROP** (interrupted, no pending ask).

Not answered (carried to next board): **Phase 2a plan** (local_e537ee50). +7 older actionable threads (11–14 d) left for a future board.

## 2026-06-14 — Calibration snapshot writer shipped (PR #52) — last code blocker to task registration cleared

**What:** Built `scripts/calibration-snapshot.ts` (oxford-command-center) — the snapshot entry point the
`ora-calibration-snapshot` task (authored in #50) referenced but which did NOT exist. **PR #52** open,
MERGEABLE (no conflicts), gate green. Branch `feat/calibration-snapshot-script`, worktree
`.claude/worktrees/calibration-snapshot` (off `e7eac94`).

`runSnapshot(db,{taskId})` mirrors the on-commit emit hook with the snapshot tag, IN ORDER: (1)
`resolveDueOutcomes` → (2) `logVerdicts(scores+anomalies, 'snapshot:<taskId>')`, idempotent (dedup_key).
FAIL-OPEN (never throws — scheduler-safe), OBSERVATIONAL (never a governor). CLI opens the canonical live
DB (`WAREHOUSE_DB` env, else `<repo>/data/warehouse/finance.sqlite` — same DB the panel reads); flags
`--task/--db/--json`. 5 TDD tests + CLI smoke (empty warehouse → zeroed JSON, exit 0). Gate note: one
EARLIER run hit a single-thread RAM-contention TIMEOUT flake in `calibration.test.ts` (passes 14/14 in
isolation; gate re-run clean exit 0) — not a logic failure.

**NEXT TASK (now the ONLY remaining step — supervised, no code left):** REGISTER `ora-calibration-snapshot`
via the supervised `create_scheduled_task` MCP on the LAMS/Cowork fleet (JSON-splice prohibited). After
#52 merges, its STEP-1 command `npx tsx scripts/calibration-snapshot.ts --task ora-calibration-snapshot
--json` is real. Schedule: quarterly (Jan/Apr/Jul/Oct 1st ~10:30am) + Dec 31. Routes to
`ggoldberg@oxfordra.net` only. NOTE: `create_scheduled_task` is NOT available on the Code surface (only the
cloud `schedule`/routines tool is) — registration must happen on Cowork/LAMS. Def + spec live in-repo at
`docs/scheduled-tasks/ora-calibration-snapshot/`.

## 2026-06-14 — Calibration Log Phase 2 UI/ops SHIPPED (PR #50 merged) + NEXT TASK

**What happened (oxford-command-center, `main` @ `e7eac94`):** PR #50 — Calibration Log Phase 2 **UI/ops**
layer — built, gated green, merged by Gabriel. Stacked on the merged Phase 2 **backend** (#48: resolver
`resolveDueOutcomes`, `calibrationReport`, read-only `/api/warehouse/calibration/{log,pending,report}`,
migration `005_calibration.sql`). Note merge order on main: #48 backend → #49 (PFI lease-run pro forma) →
#50 UI/ops. Built in an isolated worktree (now removed); feature branch `feat/calibration-phase2-ui-ops`
deleted post-merge. Main checkout left UNTOUCHED (it carries another writer's uncommitted tunnel-config
work @ `2796548` — do NOT disturb).

Shipped in #50:
- **React `/calibration` panel** (`src/modules/calibration/`): Report (per-kind hit-rate + Wilson CI +
  treatment-adjusted + bias + per-band) · Pending queue · verdict Log. Registered in the rail
  (`src/shell/modules.tsx`, Assets group, Gauge icon). Correct on EMPTY data (the normal Phase-2 state):
  explicit "no resolved outcomes yet", never NaN. H6 Zod read boundary via `fetchParsed`.
- **Manual-resolution WRITE** — `POST /api/warehouse/calibration/:id/resolve` + `resolveManualOutcome()`
  (server/warehouse/calibration.ts). Append-only + supersede (one `is_resolution=1` via partial unique
  index) + idempotent + grain-guarded (same-grain, strictly-later) + fails CLOSED. Touches
  `calibration_outcome` ONLY — never a verdict row, never overlay, never a governor.
- **Offline re-fit** — `scripts/calibration-refit.ts`: PROPOSES `healthWeights` (sum=1.0, ±0.05/yr cap,
  data-sufficiency gate) as a REPORT only. Pure `proposeRefit()` w/ ZERO fs side effects; `--out` refuses
  config/governor/overlay paths. NEVER writes intel-config.ts or the DSCR 1.25 / LTV 0.40 governors.
- 36 new tests across 6 files (TDD) + an adversarial REFUTE pass. Full `npm run gate` green (830/830 tests),
  PR CI `gate` SUCCESS + CodeRabbit SUCCESS.

**NEXT TASK (the one open item — supervised, not yet done):** REGISTER the scheduled task
`ora-calibration-snapshot`. It is AUTHORED ONLY — definition lives in-repo at
`docs/scheduled-tasks/ora-calibration-snapshot/SKILL.md` (+ spec
`docs/superpowers/specs/2026-06-14-ora-calibration-snapshot-task-spec.md`) and is INERT until registered.
Register via the supervised `create_scheduled_task` MCP on the target fleet (LAMS/Cowork by default for a
Cowork-style snapshot) — NEVER JSON-splice a registry. Schedule: quarterly (Jan/Apr/Jul/Oct 1st ~10:30am,
after ora-quarterly-review) + a Dec 31 year-end run. It resolves due outcomes → snapshots verdicts → emails
the §4 report to `ggoldberg@oxfordra.net` ONLY (no cc). Observational — never changes a weight/governor.
Phase-2 caveat: until ≥1 horizon elapses there are no resolved outcomes (zeroed report is normal, not a bug).

**Possible follow-ups (lower priority, optional):** (1) a dedicated `scripts/calibration-snapshot.ts`
snapshot writer if the task wants a single entry point (the SKILL.md documents the inline fallback path);
(2) the stale PR-#48 backend worktree `C:/Users/Owner/cc-calibration-phase2` could be cleaned up (not mine,
left alone).

## 2026-06-14 — governor-drift-probe code-aware check: adversarial-review BLOCKER fix

Independent adversarial review (opus, refute-mandate) of the code-aware `scan_code()` refactor found
a real BLOCKER + supporting fixes; all addressed and re-verified green.

- **BLOCKER (false negative):** `scan_code` validated only the comparison GUARD (`dscrFloor < 1.25`),
  not the ratified SEED literal `CAPITAL_CONFIG.dscrFloor: 1.25` / `ltvCeiling: 0.40` (capital-config.ts
  lines 34-35) — the LIVE governor value merged into every write. A one-char edit `dscrFloor: 1.00,`
  passed clean. Fixed: added property-assignment (colon) checks `RE_CODE_DSCR_ASSIGN`/`_LTV_ASSIGN`.
- **False-positive trap:** the identifiers are OVERLOADED — `conditions.ts:15-17` reuses
  `dscrFloor`/`ltvCeiling` for operational ALERT thresholds at legit different values (1.1 / 0.65).
  A global check would FP. Fixed: `scan_code` is now SCOPED to the governor file via
  `GOVERNOR_CODE_FILES = {"capital-config.ts"}`; other `.ts/.js` skip governor-checking.
- **SHOULD-FIX:** leading-dot literal (`.40`) was missed — `_NUM` now allows it.
- **Deletion guard (residual #6):** added a presence check in main() — the governor file MUST carry a
  NUMERIC declaration of each constant (the bare interface type `dscrFloor: number` does not satisfy
  it), so whole-field deletion flags.
- **Documented residuals (NITs, low risk given single-file scope):** renamed identifier; constant via
  variable / scientific notation; Yoda comparison; multi-line/comment-split declaration. Error-string
  drift on code files is a CONSCIOUS waiver (the enforced constant is what's validated; message text
  is cosmetic).

Verification: full suite ALL PASS incl. 6 `scan_code` tests + seed-drift + presence + E2E; real-tree
exit 0 (capital-config validated, conditions.ts not FP'd). Files: governor-drift-probe.py,
test-governor-drift-probe.py. Open: an independent re-review of the BLOCKER-fixed code (deferred — RAM).

## 2026-06-14 — governor-drift-probe: code-aware constant check (supersedes the RE_SANITY_SPAN patch)

L4 refactor of `governor-drift-probe.py` — splits prose vs code regimes. Spec:
`oxford-command-center/docs/superpowers/specs/2026-06-14-governor-drift-code-aware-check.md`.

- **Why:** the morning `RE_SANITY_SPAN` patch fixed the `capital-config.ts:176` FP but left a latent
  FALSE NEGATIVE: the probe's `is_gov` gate keys on PROSE keywords (`"dscr floor"`), which code's
  camelCase `dscrFloor` never matches — so it validated the error-STRING, not the enforced CONSTANT.
  `if (next.dscrFloor < 1.25)` changed to `< 1.10` (message left at 1.25) would NOT have flagged.
- **Change:** `.ts/.tsx/.js` now route to a new `scan_code()` that validates enforcement constants
  directly — `dscrFloor < 1.25` and `ltvCeiling > 0.40` (unit-interval, numeric equality so
  0.4==0.40). Catches changed literal, operator flip (`<=`/`>=`), inverted guard (`dscrFloor > 1.25`);
  ignores the `> 3` sanity ceiling. Brain `data/**/*.json` deal snapshots skipped (per-deal dscr/ltv
  values, not declarations — closes the latent 1.75-sentinel JSON FP). `RE_SANITY_SPAN` removed (dead
  once code bypasses scan_line).
- **Adversarial pass (inline):** documented residuals in the `scan_code` docstring — renamed
  identifier, variable/scientific-form constant, multi-line/comment-split comparison, and guard
  DELETION (absence not detected). Realistic literal-drift path covered; strict improvement over the
  prior message-only validation. Independent agent review deferred (RAM-starved; spawning forks).
- **Verification:** full test suite ALL PASS incl. 4 new `scan_code` tests + E2E (one transient
  0xC000012D fork-starvation failure on first run, green on retry); real-tree probe exit 0;
  memory-integrity 26/26; both files parse. Files: governor-drift-probe.py, test-governor-drift-probe.py.

## 2026-06-14 — Health-guard probe fixes: governor-drift FP, memory index, CC-verifier stale LAMS

Resolved three FAILs from the daily health sweep — all guard-logic fixes; `capital-config.ts` and governor constants untouched (invariant 4).

- **governor-drift-probe.py** — FALSE POSITIVE on `oxford-command-center/server/warehouse/capital-config.ts:176`. The `dscr` substring inside the `dscrFloor` identifier let `RE_DSCR_THRESH` crawl ~28 chars across "exceeds sane ceiling" and grab the sanity bound `3.0`. The real floor (`dscrFloor < 1.25`, line 165) is correct. Fix: added span-scoped `RE_SANITY_SPAN` suppressor (`sane ceiling N` / `fat-finger`) — skips a DSCR candidate inside that clause; co-located real drift still flags. TDD: added `test_sanity_ceiling_literal_not_flagged_unit` (red→green); all enforcement/decoy/sentinel tests still pass.
- **memory-integrity-probe.py** — 25/26 indexed. Added MEMORY.md pointer for `reference_worktree_node_modules_junction_hazard.md` → 26/26. Governor cascade (probe delegates to governor-drift-probe) auto-cleared by the fix above.
- **cc-verifier-probe.py** — `EXPECTED_LAMS` still listed the retired `scheduled-task-integrity-guard` (LAMS twin RETIRED 2026-06-11; CC `ora-task-integrity-guard` is sole runner). Dropped it; added live 4th LAMS task `ora-skill-store-drift-check`; refreshed stale comments. Now 15/15 PASS.

Evidence: all four checks exit 0 (governor probe + suite, memory probe, cc-verifier 15/15). Files: governor-drift-probe.py, test-governor-drift-probe.py, cc-verifier-probe.py, MEMORY.md.

Open follow-up (systematization candidate, not done): have governor-drift-probe parse `.ts`/`.js` governor files via the actual comparison constants rather than prose proximity, so camelCase identifiers like `dscrFloor` stop generating per-string suppressors.

## 2026-06-14 | CODE | PFI capital-config + occupancy SHIPPED via PR #31 (squash 44695c4, merged)

- The two workflow-optimization features (CAPITAL_CONFIG governed write path + occupancy time-series/capture) merged to oxford-command-center main via PR #31. CI gate passed (1m46s); 721 unit tests on the integrated tree.
- Divergence handled: local main had re-done Phase-1 work already merged in parallel (#26 = my adversarial-fixes commit verbatim). Dropped the duplicate, cherry-picked only the 4 novel commits onto origin/main, renumbered migrations 002_capital_config/003_occupancy ??? 003/004 (origin 002 = parser_version, #24). Local main reset to origin/main ??? divergence cleared (0/0).
- ora-financial-code-integrity-sweep scheduled task (Mon 1:35pm ET) is live and unaffected (lives in ~/.claude).

## 2026-06-13 | CODE | Workflow optimizations shipped (commit 1e09322) + scheduled sweep registered

All three Phase-1 follow-up systematizations done:

1. **Scheduled financial-code integrity sweep** ??? `ora-financial-code-integrity-sweep` registered on the CC/MCP fleet (cron `30 13 * * 1`, Mon 1:35 PM ET). Runs the refute-financial-change workflow against the trailing 7 days of warehouse/scoring/NOI/capital-config commits; Notion completion row always, emails ggoldberg only on a real defect or tooling failure. (Joins the migration set when the new machine arrives.)

2. **writeCapitalConfig** (capital-config.ts) ??? the SOLE governed governor-write path. Enforces DSCR???1.25 / LTV???0.40 in code, validates effectiveFrom (real ISO, non-backdated, no calendar overflow), fat-finger ceilings (dscrFloor???3, refiTriggerBps???1000), unit-interval/ordering/no-op guards, atomic version row + per-param calibration_log. Gives appendCalibrationLog its live audited caller. Not exposed as a route.

3. **Occupancy capture call-site** (occupancy.ts captureOccupancy + index.ts brain.on('snapshot')) ??? series keyed on the Eastern capture day (not static asOf, not UTC); FK-rollback guard (pre-filter to property_master); empty-master fails loud; roster-drift + dup-collision warns; residence exclusion; latestOccupancyByProperty total-order tiebreak.

**Adversarial discipline:** 4 refute rounds (3 opus refuters each) drove HIGH defects (static-asOf series collapse, FK-rollback total loss) ??? fixed; then UTC/ET mis-dating, empty-master silent loss, order-dependent dedup, source-tie, effectiveFrom validation, calendar-overflow ??? all fixed. The capital-config write path was certified airtight on invariants/atomicity/ordering every round. A DB-level source CHECK was deliberately NOT added (would need a risky table-rebuild on live data; typed API + source-ASC total order already guarantee it). Migration-immutability respected (003 left byte-for-byte as committed).

650 tests, tsc (3 configs) + lint clean.

## 2026-06-13 | CODE | Phase 1 COMPLETE ??? all units committed (7187ed3 closes)

Phase 1 delivery summary (5 commits today):
- 1ed624a adversarial fixes (sign-parity guard, no-data, drift attribution, SF-less cohort)
- 06a742b reconcileNoiABFromDb JOIN path tests (6 cases)
- 6351101 CAPITAL_CONFIG + calibration-log scaffold (migration 002, 10 tests)
- 7187ed3 occupancy time-series (migration 003, 12 tests)

Gate: 623/623 tests, typecheck clean, 81 test files.

Remaining for Phase 2 (acquisitions pipeline ??? 0% built):
- Materialized period_metrics/scores/findings tables (Phase 2 infra ??? deferred; live computation performant at 14 props)
- Acquisitions pipeline in Notion (Acq Pipeline bcfe4a03) needs warehouse integration
- Debt-refi / leasing / forecast (Phases 3-4)

## 2026-06-13 | CODE | Phase 1 governance encoding committed (6351101)

- **CAPITAL_CONFIG** (capital-config.ts): typed compile-time constant for all ratified governors ??? DSCR ???1.25, LTV ???40%, DISPOSITION <6.5%, HOLD 6.5-7.5%, ACQ-IRR ???12%, CAPEX-IRR ???15%, refi +150bps, payout 0% (full-reinvest). Hard invariants pinned by 5 tests.
- **Migration 002** (002_capital_config.sql): capital_config versioned history table (version 1 seed row, 2026-06-13) + calibration_log append-only audit trail.
- **DB wrapper tests** for reconcileNoiABFromDb committed separately (06a742b): 6 tests covering match, large-drift, 50% ownership overlay, missing-from-warehouse, residence exclusion, mixed sort.
- 611/611 tests, typecheck clean.
- Phase 1 checklist: basis ??? | FRED ??? | A-B reconciliation ??? | adversarial fixes ??? | CAPITAL_CONFIG ??? | calibration-log scaffold ???
- Remaining Phase-1 units: materialized period_metrics/scores/findings tables + occupancy time-series.

## 2026-06-13 — oxford-command-center branch hygiene + repo review (post-PFI-burst cleanup)

Reviewed the GitHub repo during a heavy multi-agent build burst (PRs #16→#23 landed today) and pruned merged branch sprawl. Done in a lean /solo CLI.

- **Branch cleanup: remote 15 → 2.** Deleted 13 confirmed-fully-merged branches: 6× `feat/cc-*` (ancestry-merged, PRs #4–9), 4× `worktree-pfi-phase-a/a2/b/b2` (PRs #11–14), `ci/warehouse-verify-score-distribution` (PR #16), `feat/pfi-phase-b3` (PR #17), `worktree-warehouse-drift-check` (content via #20/#21). Remaining: `main` + `claude/busy-maxwell-4ilaxd` (open draft PR #23, kept). Deleted via `gh api` (the git credential helper was crashing).
- **Verification method (squash repo — `git branch --merged` is unreliable):** PR→branch mapping + per-branch content-in-main sweep (`git diff --name-only mergebase..branch` then `cat-file -e origin/main:<f>`) + tip-test-in-main reasoning. Caught & corrected an MSYS colon path-mangling false-positive that initially flagged `.claude/workflows/refute-financial-change.js` as unmerged (it IS in main); re-verified with `MSYS_NO_PATHCONV=1`. b3 and drift-check both confirmed zero genuinely-absent files before deletion.
- **Code review (current `main` tip, LOCAL only — repo is in confidential-repos.json):** my #16 score-band gate SURVIVED #20's churn intact (scoreBandDistribution + distress-smear + verify assertion + vacuous-pass guard + unit test all present); `live-drift.ts` (#21) reviews clean (pure deterministic comparator, empty/NULL-basis coalesced); DGS10 guard (#22) sound. No defects found. Full #20 line-audit not done (CI-green + adversarially reviewed at merge).
- **Fixed:** git credential helper repaired via `gh auth setup-git` (`git ls-remote` now authenticates; push works again from this session).
- **Left untouched (collision-safety):** another live session's uncommitted `reconcile-noi.ts` WIP on the `main` checkout — shared-checkout single-writer doctrine.
- **Minor flagged (not fixed):** stale "414 green unit tests" comment in `scripts/warehouse-verify.ts` (suite is ~465) — not worth a commit into the active multi-agent fray.

## 2026-06-13 | CODE | Phase 1c adversarial fixes ??? DONE (commit 1ed624a)

- **Sign-parity guard** (reconcile-noi.ts): absolute floor ($10k) was silently reconciling wb=+$3k vs wh=-$3k as in-tolerance. Added signsConflict gate before OR-clause so profit-vs-loss disagreements always surface as at least drift/warn.
- **Both-null ??? no-data/info**: was missing-from-workbook/warn, mislabeling newly-acquired pre-ingest properties as if the workbook were at fault. Reclassified to no-data/info.
- **Drift reason attribution**: drift and large-drift reason strings now name which spine is higher ("Workbook NOI exceeds warehouse oxfordNoi" / "Warehouse oxfordNoi exceeds workbook NOI").
- **SF-less efficiency-cohort exclusion** (scores.ts): 1851 S Club Solar (rooftop PPA, no rentableSf) was slipping into accrual expenseRatio cohort via revenue-ratio asymmetry, producing spurious +5 health lift on 55 New Plant Ct. Now excluded from all 4 efficiency sub-scores.
- 595/595 tests pass, typecheck clean.

---
*Entries prior to 2026-06-13 (session 2) rolled over 2026-07-09 to [_archive/event_log_2026-07-09.md](_archive/event_log_2026-07-09.md) per memory-policy.md's rollover rule.*


## 2026-07-12 (cont. 6) — Tenant DB dedup remediation EXECUTED (124 rows archived)

Live execution against the Notion Tenant Database (296 starting rows), per Gabriel's
category-by-category decisions (recorded 2026-07-12 via AskUserQuestion, see
`reference_tenant_db_completeness_gap.md`). Archive mechanism: prepend
`⛔ ARCHIVED 2026-07-12 — ` to the "Tenant Name" title property (reversible; no native
archive field exists in this schema).

- **A: 19 archived** (live count; documented figure was 20 — proceeded on live-verified number).
- **B: 98 of 100 archived.** 91 duplicate groups (191 rows) derived via SQL `GROUP BY`
  exact-name-match, matching the documented figure. Decision rule: keep the row with HubSpot
  Contact filled > Property Address filled > most recent "Last Updated"; archive the rest.
  Rule was refined mid-run to weight HubSpot linkage above Property Address on ties (changed
  2 of 91 keep-decisions: Scarlet Covering Inc., Don's Garage Doors). Spot-checked all 9 groups
  where completeness and recency disagreed before batch execution. **2 rows held back**
  (Seafire Properties LLC, My Autonomous Transportation Co) — both overlap Category D's
  "leave untouched" phantom-singleton list; flagged to Gabriel rather than silently archived.
- **C: 0 of 1 resolved.** Andres Pacay Sr. (page `32b6ecd8-9e59-81dc-9df1-edff9cfdefd5`) was the
  sole genuine re-link candidate surviving triage. HubSpot search for "Pacay"/"Andres" found no
  matching contact — the collision partner (contact 56413366448) is Ian Childs / Childs Play
  Diesel Performance, a different tenant. Left blank per no-fabrication rule; flagged for manual
  research (lease file / direct tenant contact).
- **D: 7 archived** (live-verified pattern-matched HubSpot-contact-ID-collision batch).

**Total: 124 of 296 rows archived this run.** 2 rows held back pending Gabriel's real-vs-phantom
call; 1 row (Andres Pacay Sr.) unresolved pending manual source. No hard deletes; all reversible.
