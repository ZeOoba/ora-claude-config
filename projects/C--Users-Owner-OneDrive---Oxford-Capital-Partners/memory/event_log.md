---
name: event_log
description: "ORA append-only event log — system changes, deal milestones, decisions. Newest first. This is the ONLY append-wall; living docs are overwritten to current state and point here for history."
metadata: 
  node_type: memory
  type: log
  originSessionId: 8ffab475-017d-4acd-9f70-f4496936d089
  modified: 2026-07-21T16:29:47.975Z
---

# ORA Event Log (append-only, newest first)

Renamed/expanded 2026-06-03 from reference_optimization_log.md. Living docs (firm/projects/tech/etc.) hold current state; their history accumulates HERE.

## 2026-07-21 (18:08 ET) — acquisition-underwriting + deal-retirement (ora-operations-extensions) CONFIRMED INSTALLED — Cowork session, package-and-stage-skill Entry point B

Two pre-packaged, pre-verified artifacts staged from an earlier Code-surface session (`C:\Users\Owner\ora-skills\_staging\2026-07-21_index-unregistered-batch\`) — the only two entries `pending_reimport.py list` carried at session start — installed via distinct paths per Step 0's plugin-membership routing gate.

**acquisition-underwriting.skill** (standalone; `plugin_of()` → `None`): 4-item integrity pre-check run before surfacing — exists · 2 zip entries, forward-slash, expected set (SKILL.md + injected `target-markets.json`) · SKILL.md raw SHA256 byte-identical to repo commit `f2e452f` (`77e9763a...`), shared-root-dep `target-markets.json` byte-identical to repo-root copy (`28dba293...`) · staged to session outputs. No repackaging. **Gabriel confirmed the Save-skill click.** Post-install verify: runtime cache (`...\skills-plugin\...\skills\acquisition-underwriting\`) description now reads "schema rev 1.1" (was "v1.1") — the f2e452f fix is live; both files present. `pending_reimport.py clear acquisition-underwriting` run. This closes the item logged eight entries below today ("acquisition-underwriting skill staging — Not sure, recheck") as still needing a fresh click against f2e452f.

**ora-operations-extensions.plugin v0.1.5** (deal-retirement is plugin-member-only; `plugin_of('deal-retirement')` → `ora-operations-extensions` — routed as plugin reinstall, NOT a standalone Save-skill, per Step 0). Verified before surfacing: 9 zip entries (`.claude-plugin/plugin.json` + README + 7 member SKILL.md files, matching the "seven institutional skills" manifest description) · `skills/deal-retirement/SKILL.md` raw SHA256 byte-identical to the repo's canonical top-level `deal-retirement/SKILL.md` (commit `d701493`, not the `plugins/.../skills/...` path — that resolves to a non-existent file per the 2026-07-17 false-mismatch precedent). **Gabriel confirmed the plugin install.** Post-install verify at the PLUGIN cache mirror specifically (`...\rpm\plugin_01Sq7t7TEQEoa4G1asrLe8ms\`, not the standalone skills-plugin cache): `.claude-plugin\plugin.json` version `0.1.5` ; `skills\deal-retirement\SKILL.md` description now reads "Prior rev 1.1 (...)" / "v1.2" (the d701493 disambiguation is live, was previously the stacked/ambiguous v1.1+v1.2 wording); all 7 member skill dirs present. `pending_reimport.py clear deal-retirement` run; ledger now reports "none pending (cache in sync with repo)".

**Flagged, not actioned:** `plugins/ora-operations-extensions/plugin-build.json` carries an uncommitted working-tree change (`"version": "0.1.4"` → `"0.1.5"`) — the installed plugin content matches this uncommitted state, so the install is sound, but the repo will read as one version behind the shipped plugin until Gabriel commits the bump. Left for Gabriel rather than committed unprompted.

Did not touch the unrelated staged `_event_entry.md` found in the same staging folder (a draft entry for a separate, already-completed 15-skill standalone Save-skill batch from an earlier session today — out of scope for this task, not logged here to avoid misattributing that batch's work to this session).

No deploys, no scheduled-task changes, no email.

## 2026-07-21 — Open-sessions board dispatched; 6 items decided

ora-open-sessions-board 2026-07-21 17:00 ET run: probed 364 unarchived sessions, 6 actionable items reached the board (4 NEEDS-ANSWER, 1 STALLED, 1 INTERRUPTED; 27 excluded as fleet runs / already-decided-and-unchanged / sub-30-min). Notion deal-stage reconciliation ran clean (5 transitions logged — see separate 2026-07-21 deal-stage-sync entries — 3 with disposition PASS appended to deal-decision-ledger.md; flagged 1333 Research Road Passed → Candidate for Gabriel's awareness, not in the active-deal-pipeline table). Gabriel's decisions:

- **Loans External covenant analysis / Red Branch Road register** (local_47ae43e6) — Add line item. Executed: added the Muirkirk Properties, LLC intercompany promissory note ($1,778,552.34 orig., $1,380,000 o/s 12/31/2025) as its own entry in `loans-external-register.html`, tagged as related-party/not-external-debt, JS syntax validated via node.
- **ora-cowork-heartbeat beacon gap, thread A** (local_2674549c) — Check inbox now. Checked: no GitHub watchdog alert has landed today (2026-07-21) despite the 16-hr stale threshold having passed hours ago; last watchdog email was yesterday's Issue #6 thread (2026-07-20, still open). The external monitor appears not to have re-fired today — worth a look independent of the heartbeat task itself.
- **ora-cowork-heartbeat beacon gap, thread B** (local_a67aca7d) — Spin off Cowork session. Cannot execute directly — confirmed via ccd_session_mgmt tooling that this Code-surface session has no cross-surface session-creation capability into Cowork/LAMS. Handoff prompt for the delete+recreate drafted and returned to Gabriel to paste into a Cowork session himself.
- **acquisition-underwriting skill import** (local_8d6215b6) — Already done, drop.
- **acquisition-underwriting skill staging** (local_0e4c2618) — Not sure, recheck. Checked `tools/pending_reimport.py list`: acquisition-underwriting is STILL pending reimport as of 2026-07-21T20:44Z, now against a newer commit (`f2e452f`, description-token disambiguation) than the v4.3/`34c0094` package this session staged. Whether that earlier Save-skill click took is now moot — a fresh Save-skill + ledger clear is needed regardless.
- **Add confidential-deal egress guard to om-extract.ts** (local_41d96432) — Drop.

## 2026-07-21 — Deal-stage sync: 2900 Northridge Dr NW — Walker, MI (Kent County) — (none) → Passed (Notion)

Detected by ora-open-sessions-board's reconciliation step; no corresponding entry existed. Tripwire only — see Notion for the actual decision context.

## 2026-07-21 — Deal-stage sync: 2196 Port Sheldon Street — Jenison, MI — (none) → Passed (Notion)

Detected by ora-open-sessions-board's reconciliation step; no corresponding entry existed. Tripwire only — see Notion for the actual decision context.

## 2026-07-21 — Deal-stage sync: 1150 Newark Road Industrial — Zanesville, OH — (none) → Candidate (Notion)

Detected by ora-open-sessions-board's reconciliation step; no corresponding entry existed. Tripwire only — see Notion for the actual decision context.

## 2026-07-21 — Deal-stage sync: 4331 Brockton Dr SE — Kentwood, MI (Airport Industrial Center) — (none) → Passed (Notion)

Detected by ora-open-sessions-board's reconciliation step; no corresponding entry existed. Tripwire only — see Notion for the actual decision context.

## 2026-07-21 — Deal-stage sync: 1333 Research Road — Passed → Candidate (Notion)

Detected by ora-open-sessions-board's reconciliation step; no corresponding entry existed. Tripwire only — see Notion for the actual decision context.

## 2026-07-21 — Repo-wide sweep for the acquisition-underwriting version-token gotcha: one more instance found and fixed (deal-retirement)

Follow-up Code-surface session to the same-day `acquisition-underwriting` description fix (commit `f2e452f`) and its companion memory file `reference_skill_description_version_extraction_gotcha.md`. Swept all 53 `SKILL.md` files in `ora-skills` for the same class of bug: a bare `vX.Y(` token in the frontmatter description that a naive version-extraction regex could misread as the skill's file version.

**22 skills carry a `vX.Y(` description token; 21 are clean** — each is a single, self-referential note matching its own changelog's latest entry (or the file's only version reference). `register-scheduled-task`'s H1 also states its version (`v2.7`), consistent with the description.

**1 flagged and fixed: `deal-retirement`.** A different variant of the same risk — not a sub-component/schema version colliding with the file version (the acquisition-underwriting pattern), but two genuine file-version notes stacked back-to-back in the description (`v1.1 (2026-07-16: ...)`. `v1.2 (2026-07-18: ...)`) with no body changelog section to disambiguate. A naive first-match regex would have logged the superseded v1.1 instead of the true current v1.2 (visible only via inline `[v1.2]` tags in the Standard Workflows steps). Fixed the same way: reworded the superseded entry to `Prior rev 1.1 (...)` so it no longer matches a bare `vX.Y(` token, leaving v1.2 as the sole marker. Packager-validated (925/1024 chars, `python tools/package_skills.py` exit 0). Committed as `d701493`.

Repo-first check (`git log -1` / `git status`) was clean before editing — HEAD was `f2e452f`, only untracked `_staging/` present (the expected `PENDING_REIMPORT.md` side effect from the acquisition-underwriting fix). No ruling, scorecard weight, governor constant, or substantive skill logic changed by either fix — description wording only.

This closes the "was not exhaustively swept" gap the acquisition-underwriting memory entry flagged the same day — a future session does not need to re-run this audit from scratch unless new skills are added or existing descriptions are re-edited.

## 2026-07-21 — Correction: archiving 01_Workspace/outputs/ stale copies broke doctrine-integrity-probe.py; refreshed in place instead of allowlisting

Follow-up to the same-day archive of 12 stale `01_Workspace/outputs/<skill>/SKILL.md` copies to `_archive/2026-07-21_stale-outputs-skills/`. That move removed the only Code/Cowork-surface resolution path `doctrine-integrity-probe.py`'s `collect_skill_dirs()` had for all 12 — re-ran the probe's own resolver post-archive and confirmed all 12 flipped to unresolvable.

**First fix attempt was wrong.** Added all 12 to `PLUGIN_SKILL_ALLOWLIST` (mirroring the existing `re-operations` entry). `test-doctrine-integrity-probe.py`'s `test_real_doctrine_skills_resolve()` caught it: a deliberate regression guard, dated to the 2026-06-06 review, asserts `communication-intelligence` and `deal-comparison` must resolve via a REAL directory, explicitly NOT via the allowlist — because allowlist-masking a skill that's actually missing/stale is the exact failure mode that guard exists to prevent. Reverted the allowlist change back to `{"re-operations"}` only, restored the original comment.

**Correct fix:** refreshed all 12 `outputs/<skill>/SKILL.md` files in place with byte-exact current content copied from the authoritative `ora-skills` repo (SHA256-verified match, all 12). This satisfies the probe's structural resolution AND eliminates the stale/governor-relevant content the original audit flagged (deal-comparison's pre-RCT-v03 scoring bands, exception-detection's retired-Rube reference) — the stale versions remain preserved in `_archive/2026-07-21_stale-outputs-skills/` as the historical record, not touched further.

Re-ran the full test suite (`test-doctrine-integrity-probe.py`) after the refresh: all 39 tests pass, exit 0, including `test_real_doctrine_skills_resolve`.

No commits made to `~/.claude` (shared-checkout hazard flagged again by the PreToolUse hook — session `a0d59799` has 36 unrelated uncommitted changes in that checkout; committing now would co-mingle their WIP with this fix). The `doctrine-integrity-probe.py` edit and the `01_Workspace/outputs/` refresh are both saved to disk and verified working, but `git add`/`commit` on `~/.claude/maintenance/doctrine-integrity-probe.py` is left for whoever reconciles that session's WIP.

## 2026-07-21 — 15-skill Save-skill batch confirmed installed (Entry point B pre-packaged install)

Companion to the same-day "21 index-unregistered skills" backfill entry above: the 14 re-staged skills plus the 1 held skill (acquisition-underwriting) — 15 total — were packaged today via `tools/package_skills.py` in an earlier Code-surface session, hash-verified against the repo at package time, and handed off to this Cowork session for install via `package-and-stage-skill` Entry point B (pre-packaged install, steps 5-8 only).

**Step 0 (plugin-membership gate):** `plugin_of()` returned `None` for all 15 — none are shadowed by a plugin bundle; standalone Save-skill path confirmed correct for every package.

**Integrity pre-check (per package, before surfacing):** exists · zip entries forward-slash, expected file set matches repo dir · SKILL.md byte-identical to repo · `SHARED_ROOT_DEPS` `target-markets.json` byte-identical to repo root for the 3 consumers in this batch (acquisition-underwriting, deal-comparison, rent-comp). No package rejected back to Entry point A.

**Gabriel confirmed the Save-skill click on all 15.** Post-install verification: every packaged file present and content-identical in the runtime cache mirror (`...\skills-plugin\...\skills\<skill>\`) for all 15 — no missing files, no stale content. Runtime-cache `SKILL.md` mtimes cluster 2026-07-21 16:31:14-16:33:43, consistent with sequential clicks landing this session (not stale pre-existing cache), including acquisition-underwriting (16:31:14) — closing the gap the 2026-07-18 doctrine review had logged as still awaiting this click, independent of content freshness (content was already byte-identical pre-click, per that entry).

**Confirmed installs (skill v version):**
- acquisition-underwriting v4.3
- census-acs-extract v1.0
- communication-intelligence v1.2
- conversation-archival v2.0
- deal-comparison v1.0
- document-assembly v1.3
- file-reconciliation v1.0
- fleet-advisory-remediation v1.1
- graph-app-registration v1.0
- legal-intelligence v1.1
- orphaned-task-forensics v1.1
- portfolio-growth v1.0
- portfolio-reporting v1.1
- rent-comp v1.1
- tenant-intelligence v1.0

`pending_reimport.py clear <skill>` run for all 15 post-verification. The 6 skills backfill-confirmed earlier today (exception-detection, deal-execution, loi-generation, owner-outreach, disposition-analysis, market-monitor) were untouched, per instruction — no click needed for those.

## 2026-07-21 — 21 index-unregistered skills: evidence-proportionate backfill (6 confirmed, 14 re-staged, 1 held for Gabriel)

Gabriel-directed follow-up to the 2026-07-21 16:04:58 UTC drift-check correction's 24-item (later 21, after lease-renewal-pipeline/personal-portfolio/website-perfection closed same day) index-unregistered list. Rather than treat every skill as an individual incident, researched actual usage evidence per skill (event_log.md + memory dir) and split by evidence strength — matching the drift-check's own 2026-07-20 recommendation to treat this as a backfill exercise where evidence supports it.

**Backfill-confirmed (6), no re-staging, no new click required — content already hash-clean in cache, and dated usage evidence corroborates the CURRENT version is what's actually running:**
- **exception-detection** v1.2 (`b723118`) — same-day (2026-07-21) log directly confirms `Skill({skill:"exception-detection"})` served v1.2 content matching current commit, with v1.2-specific features (3 new Category 2 rows) verified present. Strongest evidence in the set.
- **deal-execution** v1.2 (`643dd9f`) — `open-items-tracker.md` OI-012: Gabriel explicitly confirmed "all 3 imported (all done)" at commit `643dd9f`, exact match to current repo HEAD, dated 2026-07-17.
- **loi-generation** v1.4 (`643dd9f`) — same OI-012 confirmed-import event, exact commit match.
- **owner-outreach** v1.0 (`5dda2cd`) — 2026-07-21 log entry: real scheduled-run failure/fix touching the pipeline scripts and the skill's own SKILL.md, postdating the commit; OI-012 also confirms repo↔runtime matching at this exact version.
- **disposition-analysis** v1.0 (`e2764e0`) — `deal_1100_rarig_disposition_2026-07.md`: "Ran as a standing portfolio-health check... via the disposition-analysis skill," dated 2026-07-09, postdating the only-ever commit.
- **market-monitor** v1.1 (`35cdbca`) — `markets.md`: Des Moines market-data row sourced "via market-monitor skill v1.1," version token matches current — moderate confidence only, since that entry predates the 07-16 commit by 5 days and can't confirm every feature in that commit was exercised.

**Re-staged (14) — no usage evidence found either way; packaged via `tools/package_skills.py` into session outputs (`.../scratchpad/restage-2026-07-21/`), frontmatter-validated, SHA256-verified against repo, awaiting Gabriel's Save-skill click:** census-acs-extract, conversation-archival, document-assembly, file-reconciliation, fleet-advisory-remediation, graph-app-registration, orphaned-task-forensics, portfolio-growth, portfolio-reporting, rent-comp, communication-intelligence, deal-comparison, legal-intelligence, tenant-intelligence.

The last 4 were initially held pending a surface-architecture question (`reference_skill_surfaces.md` claimed they load via a distinct Code-CLI `anthropic-skills` plugin bundle with "no local SKILL.md," not the individual Cowork Save-skill cache). Resolved same session: this session's own available-skills listing shows the identical `anthropic-skills:` prefix on personal-portfolio/website-perfection/lease-renewal-pipeline — skills already confirmed individually Save-skill-installed earlier today — proving the prefix is a generic Code/CLI namespace label, not evidence of a separate bundle mechanism. Combined with all 4 already being present and byte-matching in the Store B runtime cache, the "no local SKILL.md" claim in `reference_skill_surfaces.md` is stale — it describes the defunct Cowork-workspace-folder sync that document's own 2026-07-21 correction says was superseded by the runtime-cache mechanism. Folded into the standard re-stage batch accordingly. `reference_skill_surfaces.md` should be corrected in a follow-up pass (not done here — read-only investigation only).

**Held (1) — genuinely confirmed open gap, not just a missing log line:**
- **acquisition-underwriting** v4.3 (`34c0094`) — `project_acquisition_underwriting_doctrine_review_2026-07-18.md` explicitly logged this version as "awaiting Gabriel's manual Save-skill click" as of its 2026-07-18 close. Content is already byte-identical in cache (confirmed in this session's full 43-skill sweep) — no repackaging needed, only the click itself, which registers the install event independent of content freshness (same rationale as step 2g / the psa-reconciliation raw-sync precedent). Not yet actioned this session — flagged for Gabriel alongside the 14-skill batch above.

No files modified in ora-skills beyond what package_skills.py wrote to session outputs (untracked, outside the repo). No Save-skill clicks performed by this session — registration remains Gabriel's action per doctrine.

## 2026-07-21 — rent-roll-reconciliation captured into ora-skills repo (PR #22, not yet merged)

Captured from the runtime cache into `C:\Users\Owner\ora-skills\rent-roll-reconciliation\` (SKILL.md + scripts/parse_rent_roll.py + scripts/diff_tenants.py) — the 2026-07-21 ad hoc `ora-skill-store-drift-check` run had flagged this skill CACHE-ONLY with no repo counterpart. Byte-exact copy per the CACHE→REPO RECOVERY PROCEDURE (parcel-data-recovery precedent, PR #20, 2026-07-16): SHA256-verified pre/post-copy (SKILL.md `d684328a...`, parse_rent_roll.py `101969cb...`, diff_tenants.py `86496da9...`). Committed `0b3db80` on branch `capture/rent-roll-reconciliation`, pushed, PR [#22](https://github.com/ZeOoba/ora-skills/pull/22) opened — not merged (Gabriel's review pending, never merging unreviewed per doctrine).

**Pending-reimport ledger false-positive, cleared.** `tools/hooks/post-commit` fired on this commit (as it does for any commit touching a skill's packaged content) and recorded rent-roll-reconciliation in `_staging/PENDING_REIMPORT.md` as "repo ahead of cache, needs reimport." That's incorrect in this specific case: the repo content was sourced byte-for-byte FROM the runtime cache, so cache and repo are already identical — no platform-side change occurred, no Save-skill click is needed. Cleared via `python tools/pending_reimport.py clear rent-roll-reconciliation` rather than leaving a stale pending-reimport signal for a future drift-check or package-and-stage-skill session to act on unnecessarily (the exact class of stale-finding problem root-caused earlier today re: lease-renewal-pipeline/personal-portfolio/website-perfection). The hook's blanket "any skill-content commit → flag for reimport" logic doesn't distinguish a genuine new repo edit from a verbatim cache backfill — worth hardening later, not done here.

**Content note, unresolved:** `scripts/diff_tenants.py`'s docstring cites "the Bay Area Corporation / Bay Area Exteriors case in SKILL.md history," but the captured SKILL.md has no history/changelog section documenting it — flagged in the PR description, not resolved.

## 2026-07-21 — Skill reimport "stale content" traced to async SkillsPlugin sync lag, not a broken cache

Investigated why `Skill({skill: "exception-detection"})` served old v1.1 content in two fresh sessions/agent spawns even though the on-disk SKILL.md (grepped directly) already showed v1.2 and `PENDING_REIMPORT.md` had been cleared after "Save skill." Root cause found in `AppData\Roaming\Claude\logs\main.log`, not in `ora-skills` or any Code-side mechanism: the served base directory (`local-agent-mode-sessions\skills-plugin\<profile>\<id>\skills\`) is a single shared store across all sessions from this app instance, not a per-session copy — confirmed by repeated `[CCD] Using skills plugin at: <same path>` lines across separate session starts. Content only updates there via a periodic `[SkillsPlugin] Starting skills sync` → `Delta: N to download` → `Sync complete` cycle, observed running roughly every 2-10 minutes. "Save skill" registers the update to a remote skill store immediately, but the local file on disk (and therefore what the Skill tool serves) doesn't update until the next sync tick actually downloads it — up to ~10 min later. Confirmed: sync at 13:08:51 showed `Delta: 0` (update not yet visible remotely); sync at 13:11:46 showed `Delta: 1 to download` and completed at 13:11:47, matching the SKILL.md file's CreationTime/LastWriteTime exactly. Any session/agent that reads the Skill tool before that sync tick sees stale content regardless of how "fresh" the session is — this is a race, not a stale in-memory cache that ignores disk changes. Re-tested `Skill({skill: "exception-detection"})` after 13:18:05 (next sync, `Delta: 0`, confirming stable) — now correctly serves v1.2 (3 new Category 2 rows + disambiguated Category 4 row present).

**Systemic implication:** `PENDING_REIMPORT.md` clearing on "Save skill" click is not proof the update is live — it only confirms the registration step, not the sync-to-disk step. Any skill update tested within ~10 min of "Save skill" risks a false "it didn't take" reading. Detail + verification procedure: `memory/reference_skill_reimport_sync_lag.md`.

## 2026-07-21 - package-and-stage-skill workflow-optimization follow-ups: post-commit hook, append-event-log.py, and event_log.md.pending all root-caused
Gabriel asked to "fix all workflow optimizations" flagged at the close of the lease-renewal-pipeline/personal-portfolio/website-perfection install session. Three findings:
1. **Post-commit hook miss for commit 40e5a4d.** Root-cause hunt: tools/hooks/post-commit and pre-commit are both mode 100644 in C:\Users\Owner\ora-skills, but pre-commit still fires reliably (proven live: blocked a malformed test commit). Ruled out the executable-bit theory. Directly ran python tools/pending_reimport.py record 40e5a4d -- it correctly recorded all three skills, proving the record logic itself is sound. Then proved the live post-commit hook DOES fire correctly on this clone today: committed and cleaned up a throwaway _hook-test-scratch skill (2 test commits, fd243a1/eb29889, both tagged "test:"), and the hook fired and recorded on the first passing commit. Conclusion: this clone's hook is healthy; the miss on 40e5a4d most likely traces to a different, since-removed environment (a linked worktree, e.g. the "strange-sutherland" one referenced in this machine's session-memory index, no longer in git worktree list) where core.hooksPath or the shell's python resolution differed. Not independently confirmable post-hoc since that worktree is gone. No code change made -- none was warranted once the mode-bit theory was falsified.
2. **append-event-log.py "undiscoverable."** Wrong-location miss, not a retirement: it lives at ~/.claude/maintenance/append-event-log.py (actively maintained, last touched 2026-07-18, with a live test-append-event-log.py suite), not under ~/.claude/projects/.../memory/ (which only holds session transcripts + the memory *data* files, not the maintenance *code*). Root-caused via reference_memory_scope_fragmentation.md, which names the canonical path directly.
3. **event_log.md.pending directory.** Confirmed active, not cruft: it's the literal spool directory (spool_dir_for() = log + ".pending") append-event-log.py uses when os.replace is blocked by a file-handle lock (see reference_event_log_app_handle_lock.md). Empty = healthy (nothing currently parked), not abandoned.
**Self-correction, same session:** the original install closeout entry was appended via raw .NET AppendAllText (append-event-log.py hadn't been located yet), landing at the tail of the file -- after the 2026-07-18 rollover footer, violating the newest-first convention documented in this file's own frontmatter. A separate, correctly-placed entry describing the same install (titled "Version tokens installed: ...") had since landed properly at the top via another session's proper use of the canonical tool. Removed the misplaced tail duplicate (exact-substring match, verified before and after) rather than leaving two entries for one event. This entry itself is being appended via the canonical append-event-log.py --entry-file path, not manual editing.

## 2026-07-21 — Version tokens installed: lease-renewal-pipeline, personal-portfolio, website-perfection (v1.0 each)

Closed the ora-skill-store-drift-check doctrine gap where these three SKILL.md files had no version token, breaking version-based drift comparison. Repo edit + commit `40e5a4d` (Code session); packaged via `tools/package_skills.py` (single-file skills, no plugin membership). **Gabriel confirmed the Save-skill install click** via Cowork. Runtime cache re-sync verified (EOL-normalized SHA256 match, repo vs `…\local-agent-mode-sessions\skills-plugin\583f08bc…\a6ad2c61…\skills\<skill>\`, post-install mtimes ~12:19 ET, all matching repo content). All three cleared from the post-commit PENDING-REIMPORT ledger (`_staging/PENDING_REIMPORT.md`, now empty/removed). A future `ora-skill-store-drift-check` run should read IN-SYNC for these three.

## 2026-07-21 — ora-owner-outreach-queue-refresh: recurring path defect root-caused and closed across all 3 hosts; staleness heuristic de-coupled from frozen filename vintage

Scheduled run halted at Step 1 with `[FATAL] queue script failed` → `can't open file '...owner_outreach_queue.py'`. Root cause: the 2026-07-05 machine migration nested `Investment Candidates -- 2026` one level deeper under a new `Business\` folder; the 2026-07-11 fix (documented inline in both scripts) addressed a *different* defect — a stray OneDrive `"(1)"` duplicate-folder suffix — and never caught the `Business\` nesting. Patched (with Gabriel's in-turn sign-off) in all three places the path was hardcoded:
- `owner_outreach_weekly.py` — `FOLDER` constant
- `owner_outreach_queue.py` — `_MASTER_FOLDER` constant
- the scheduled task's own `SKILL.md` (Steps 1 and 3's literal `python "..."` invocation) — this is the one that would have kept failing next Monday even with the two scripts fixed, since the harness invokes this path literally.

Swept the rest of the folder's `*.py` (`build_t1_letterpack.py`, `_check_addr_fields_20260712.py`) for the same broken-path string — clean, no other instances.

**This is a recurrence, not a first occurrence.** `send-log.txt` shows an identical ALERT on 2026-07-12 13:16, a "corrected" successful send 8 minutes later, and a broader Cowork Automation Alert at 13:57 flagging 4 tasks including this one. It ran clean on 07-13, then broke again by today with the *identical* defect — meaning the 07-12 correction was very likely a manual override/workaround that session (e.g. an explicit master-path arg), not a persisted edit to the `FOLDER`/`_MASTER_FOLDER` constants: both scripts' content going into today's session still had the bug, and no event_log entry existed documenting a 07-12 fix. Logging this now specifically so the defect can't recur a third time without a paper trail.

**Second, related finding while investigating "no refresh since 06-10":** the master workbook *has* been refreshed — `_v01` through `_v06` all sit in the correct folder, `v02`–`v06` all written 2026-07-12 (archive copies tagged `PREEDIT-cincy10-20260712` indicate a Hamilton/Cincinnati-area SF recovery pass, consistent with parcel-data-recovery's Iron rule 6: new version per pass, never overwrite). But `owner_outreach_queue.py`'s `stale` flag was computed as `(vintage_age > STALE_DAYS) OR (mtime_age > STALE_DAYS)`, where `vintage_age` derives from the filename's frozen `20260610` date prefix — a date recovery passes never rebump. That clause alone pins `stale=True` forever regardless of how fresh the data actually is (confirmed: a same-day-fresh master already read 41d "stale" by vintage). Fixed by gating `stale` on `mtime_age` alone; `vintage`/`vintage_age` still computed and printed (provenance, STANDING RATIFICATIONS matching) but no longer gate the flag. Verified against a disposable fresh-mtime copy of the real master (never touched the pinned master itself) — `STALE=no` with vintage still showing `2026-06-10 (41d)`, confirming the fix behaves as intended.

Doctrine change made: `owner_outreach_queue.py`'s freshness-gating logic (mtime-only). No change to `STALE_DAYS=7` itself, the STANDING RATIFICATIONS mechanism, or the master/ledger data — none of those were in scope or at fault.

## 2026-07-20 — IWNS LLC primary lease verified: escalation date corrected, cannabis-use risk flagged

Gabriel asked to verify the primary lease document for IWNS LLC DBA Jasis Laboratory once available. Located "Lease Suite A1-2 Steven Utieyin Johnson Jr. and IWNS LLC DBA Jasis Laboratory #2 6.17.2026 -- 2203-2207.pdf" (Adobe Sign, Status Signed, Agreement completed 2026-06-22, Gabriel signed for Landlord). Confirms SF 2,400, Suite A1-2, Lease 2026-07-01 through 2031-06-30, Monthly Rent $3,000, Security Deposit $6,000, 3%/year escalation -- all already-written fields matched. **Corrected** Next Escalation Date from 2027-07-01 (a rent-roll-derived estimate) to **2026-10-01** (the lease's actual stated date). **Caveat noted, not resolved**: the Adobe Sign audit trail lists only Gabriel Goldberg as recipient/signer -- Tenant's own signature blocks appear blank in the extracted text, so Tenant-side execution isn't independently confirmed from this document alone. **Material risk surfaced**: this is a cannabis-processing tenant: Sections 5-6 grant Landlord sole-discretion termination rights if Tenant hasn't secured all required cannabis zoning/licensing approvals by September 1, 2026 -- the lease's own text notes current Salisbury zoning restricts this use and may or may not be amended in time. Written via notion-update-page, verified via fresh fetch. Detail: `open-items-tracker.md` OI-023.

## 2026-07-20 — OI-023 closed: IWNS LLC DBA Jasis Laboratory added to Notion

Gabriel confirmed adding the tenant found missing during the rent-roll reconciliation. Created via `notion-create-pages`: Tenant Name "IWNS LLC DBA Jasis Laboratory", Tenant Legal Entity Name "IWNS LLC", Property Address 2203-2207 Northwood Dr -- Salisbury MD, Suite A1+A2, 2,400 SF, $3,000/mo, Lease Status Active, Primary Contact Steven Johnson, Lease Start 2026-07-01, Lease Expiration 2031-06-30, Next Escalation Date 2027-07-01, Escalation Percent 3%. All fields sourced directly from the rent roll (no primary lease document read yet). Assigned Tenant ID ORA-T-299, verified via fresh fetch. Closes OI-023. Detail: `open-items-tracker.md` OI-023.

## 2026-07-20 — Rent roll reconciliation residual spun off as OI-023

Gabriel asked to check open-items-tracker.md for any lingering rent-roll gaps after the reconciliation. No tracker entry existed for the reconciliation's residuals yet. Investigated the one genuinely unmatched rent-roll row: IWNS LLC DBA Jasis Laboratory ($3,000/mo, 2203-2207 Northwood Suite A1+A2) -- confirmed via `notion-search` (no result) that it has zero Notion Tenant DB record, unlike the 4 tenants restored earlier this session which existed but were mistakenly retired. Lease Start of 2026-07-01 suggests a genuinely new, not-yet-onboarded tenant. Not written -- opened as OI-023 pending Gabriel's go-ahead. Also confirmed the other unmatched rent-roll rows (Hobart Services, Masala Bazaar/XPO Foods, Green Home Solutions) are naming variants only, not real gaps -- rent already matches Notion exactly. Detail: `open-items-tracker.md` OI-023.

## 2026-07-20 — Portfolio-wide rent roll reconciliation: 4 tenants restored, systemic escalation-drift fixed (60 rows)

Gabriel asked to check the 7/20/2026 Rent Roll for discrepancies against the Notion Tenant Database, then to update Notion to match. Reconciled all 137 rent-roll rows against 160 non-retired Notion rows (SQL query mode hit the same free-plan quota wall documented in reference_tenant_db_completeness_gap.md mid-pull; page IDs for the write pass were gathered via `notion-search` instead, which was unaffected). Findings and actions:

- **4 real, currently-paying tenants had zero live Notion record**: Bay Area Exteriors LLC (29000 Info Ln #502+503, $3,700/mo), Eastern Shore Karate & Fitness LLC (#306, $1,802.50/mo), Palmer's Plumbing LLC (#301+302, $3,069.76/mo), and Scarlet Covering Inc. (1900 N Broadway #100, $10,790.41/mo) -- all four were retired 2026-07-17 (OI-009) as duplicates of an "already-correctly-resolved" counterpart that, on inspection, either never existed or was itself archived/retired. Restored all 4: un-retired, corrected Property Address/Suite/Unit to match the rent roll, updated Palmer's Plumbing's stale rent. Combined ~$19,363/mo (~$232K/yr) of real rent now visible again in the active roster.
- **Systemic Escalation Percent corruption, 9 rows**: values like 11.66, 130.05, 36.06, 164.7975 (should be 0.03-0.06 range) -- a recurring data bug, not isolated typos (same class as Childs Play Diesel Performance, fixed earlier this session). Corrected 8 to the rent roll's sane value; Baltimore Dialysis/Fresenius's rent-roll value was itself nonsensical (-0.0001) so that field was cleared to null rather than filled with garbage.
- **Systemic stale post-escalation rent, ~40 rows**: Notion's Monthly Rent and Next Escalation Date were exactly one escalation cycle behind the rent roll for a large share of the portfolio -- the same root cause as the I Dig Ditches correction earlier this session, just never rolled forward in Notion when escalations actually fired. Bulk-corrected via `notion-update-page`.
- **Exceptions NOT applied mechanically**: Maryland Hospital Association's rent-roll lease-end (2027-05-31) was left alone -- conflicts with the fully-executed PDF Gabriel supplied and confirmed this session (2027-06-30), and a signed document outranks a rent-roll spreadsheet. Upgraded Roofing's SF/Lease Start/Lease Expiration were left alone -- conflict with an executed lease + estoppel verified earlier this session; only its rent-drift figure (already primary-doc-consistent) was left as-is since no diff existed there. Gator Roofing's SF/Lease Start/Lease Expiration were excluded for the same reason, but its Monthly Rent/Next Escalation Date were corrected (consistent with the well-understood drift pattern). Granite Tops' Monthly Rent was corrected to the rent roll ($7,496, resolving a previously "unexplained" figure) but its Lease Expiration/Next Escalation Date were NOT reverted to the rent roll's stale values -- those fields carry Gabriel's explicit 2026-07-31 vacate-date confirmation from earlier this session.
- 60 total `notion-update-page` writes (4 restorations + 56 corrections). Spot-verified via fresh fetch: both restorations, the nulled Baltimore Dialysis field, and the Granite Tops exclusion all confirmed correct.

## 2026-07-20 — I Dig Ditches (Gyurcsik Construction) rent corrected for uncounted escalation (OI-009 sub-item)

Gabriel corrected the Monthly Rent written earlier this session: current base rent is $1,147.36, not the $1,113.94 taken directly from the executed addendum. The addendum's $1,113.94 figure was only effective as of 4/1/2025 (Lease Year 3); the 3%/year escalation clause meant one more step-up was already due by 4/1/2026 (Lease Year 4, which we are now past) -- $1,113.94 x 1.03 = $1,147.36, reconciling exactly with Gabriel's figure. Corrected `Monthly Rent` to $1,147.36, set `Last Rent Increase Date` 2026-04-01 and `Next Escalation Date` 2027-04-01 via `notion-update-page`, verified via fresh fetch. Detail: `open-items-tracker.md` OI-009.

## 2026-07-20 — Childs Play Diesel Performance escalation fixed, I Dig Ditches identity/dates added (OI-009 sub-item)

Gabriel supplied two executed documents directly. **Childs Play Diesel Performance**: the full executed lease (DocuSign, term 4/1/2026-3/31/2029) shows a fixed 3-tier dollar rent schedule (Yr1 $2,100/mo, Yr2 $2,350/mo, Yr3 $2,600/mo), not a flat annual escalation -- the prior `Escalation Percent` of 23.5 was ~(2600-2100)/2100=23.8%, the cumulative 3-year growth mistakenly entered as an annual rate. Corrected to 11.90% (the Yr1->Yr2 rate); `Next Escalation Date` corrected from 2026-04-01 (commencement date, not an escalation) to 2027-04-01; `Tenant Legal Entity Name` added (Ian Blake Childs DBA Childs Play Diesel Performance); full schedule documented in Notes. Monthly Rent ($2,100) confirmed already correct -- still Year 1. **I Dig Ditches**: Gabriel identified the tenant as Gyurcsik Construction; a fully-executed addendum (Adobe Sign, 2025-01-23) confirmed Christopher J. Gyurcsik trades as I Dig Ditches. Wrote `Tenant Legal Entity Name` (Gyurcsik Construction), `Lease Start` (2023-04-01, Prime Lease date), `Lease Expiration` (2027-03-31), and `Escalation Percent` (3%/year from Lease Year 2) -- this row previously had neither date set. Monthly Rent ($1,113.94) already matched, no change. Both written via `notion-update-page`, verified via fresh fetch. Detail: `open-items-tracker.md` OI-009.

## 2026-07-17 — Granite Tops: AR collection flag added ahead of move-out (OI-009 sub-item)

Gabriel asked to check the AR balance on Granite Tops given the confirmed 2026-07-31 vacate date: $180.19, aged 90+ days (per the 2026-07-15 AR data pull). Added a collection flag to the row's `Notes` via `notion-update-page` — the balance becomes materially harder to collect once the tenant is out and the lease relationship ends; recommended the PM collect or apply against the security deposit at or before move-out. Verified via fresh fetch. No tracker change (informational addition to an already-closed OI-009 sub-item).

## 2026-07-20 — ora-cc-schematic-refresh (Rev 2026-07-20a): fleet verdict flipped OK→ATTENTION

Scheduled Mon-cadence refresh of the Claude Code System Schematic artifact. Material changes vs rev 2026-07-18d:
- **Fleet VERDICT ATTENTION** (was OK): 13 throttle-skip events in the last 24h (ora-deal-aging-sla=5, automation-health-monitor=3, check-github-support-ticket-4584520=3, ora-deal-command-board=1, ora-sofr-direct-prefetch=1) + **1 new same-time collision at 09:20** (ora-site-exposure-probe ∥ ora-deal-aging-sla, both cc weekday-morning). 0 overdue, 0 missed/stuck. Candidate fix if the 09:20 overlap recurs: shift one task by 5–10 min.
- Fleet enabled 43→44 (cc 22→23, lams steady 21); 3 disabled = spent EXPIRED one-time entries.
- **ora-pm repo dirty→clean** (rev-d WIP committed/cleared by its owning session), HEAD 1b304e8; oxford-command-center clean @1cb8f1a.
- memory-integrity now shows 2 present-but-unlisted files (project_plan2_effect_verification_design_2026-07-18.md, project_setup_improvement_top5_plan_2026-07-18.md) — non-fatal, index pointers owed by the authoring session.
Probes otherwise green: governor-drift exit 0 (774 files), doctrine-integrity exit 0, confidentiality-guard 131/131. enabledPlugins unchanged (12 true).

## 2026-07-19 — OI-015 closed as verified-clean (no history purge needed); real residual found and spun off as OI-022

Gabriel asked to close out the ora-appsec-sweep's OI-015 finding (real E. Fulton deal terms allegedly "still in git history on the remote" for ora-pm) and investigate the theoretical residual further, implementing whatever solution followed.

**OI-015 closed, not fixed by a purge — the original finding was wrong.** A completely fresh clone directly from github.com/ZeOoba/ora-pm (bypassing any local object cache) shows commit `c4c69a8` already contains only placeholders, and `git log -p --all` across every reachable commit/branch in that fresh clone returns zero matches for any real E. Fulton term variant. The reachable, clonable, browsable history is genuinely clean — no rewrite or force-push was needed or performed. The original sweep finding (and fix-commit `866480f`'s own note) were based on a stale signal: a local dangling/unreachable blob mistaken for "still in history."

**Real residual found and confirmed, spun off as OI-022:** that same blob (`39b02f4585cc6357876423d04d5c3fcee65793b0`) IS still directly retrievable via GitHub's Git Data API — confirmed via `gh api repos/ZeOoba/ora-pm/git/blobs/<sha>`, which returned the actual content. Root cause: `refs/pull/2/head` (a GitHub-internal ref for the closed/merged PR #2 that originally carried the sensitive commit) keeps the object alive server-side, independent of what happens to `main`'s history. These refs cannot be deleted by the repo owner via git push, the API, or repo settings — no self-service mechanism exists. The only documented fix is a GitHub Support request. Drafted the full request text (repo confirmed private, 0 forks via API) at the scratchpad path recorded in OI-022; submitting it is Gabriel's action (outbound third-party request), not something this session executes.

Not a live-credential emergency (E. Fulton declassified 2026-07-09), but a real, low-probability residual exposure path worth closing via the support request when Gabriel has a moment.

## 2026-07-19 — PR #222 (Debt & Maturity Module v1) merged — both Invariant-4 blockers resolved via direct workbook read + Gabriel ratification

Closes out the last open item from the 2026-07-18/19 next5-improvements round (N3).

- **Workbook column mapping resolved by direct read, not guessed** (commit `53c8ea3`): opened the live Master Workbook's Loan Index + External Loans Summary sheets. LTV confirmed per-loan balance/collateral-value (Loan Index's `ltv` cell is literally `='External Loans Summary'!O_`, that column's own header reads "LTV (Balance/Value)") — validates the module's existing single-active-loan aggregation as correct, not a guess. Rate-type/next-rate-reset confirmed **absent from the workbook entirely** — full header scan of both sheets found exactly one rate field anywhere ("Annual Rate"); migration 023's two columns stay NULL because there is nothing to map, not because of an unresolved question.
- **Refi-window thresholds (12/24-month) ratified by Gabriel, "approve as-is"** (commit `4bbb2d4`) — constants unchanged, doc comments now record the ratification so a future reader doesn't re-flag them `[SPECULATIVE]`.
- **Merged:** squash commit `1cb8f1a` on `oxford-command-center@main`, branch deleted (remote + local). Independent Fable review (APPROVE-WITH-NOTES) stands as the pre-merge record; 233 files/2865 tests green throughout, re-verified after each of the two follow-up commits (31/31 debt-maturity suite + tsc clean post-ratification).
- **Residual, not blocking:** the 65% per-property refi ceiling still isn't DB-backed/ratifiable like the other two governors (`ALERT_THRESHOLDS.ltvCeiling` in `conditions.ts`, self-labeled "non-governor thresholds") — flagged for a future governor-consolidation pass, not this module's scope.
- **v2 follow-ups on record** (not built): wire `/timeline` + `/refi-windows` into `ora-am-brief`/`ora-monthly-portfolio-briefing`; rate-type/reset ingestion if Gabriel ever adds the workbook column or an alternate source; true multi-loan combined-LTV (needs per-loan implied-value reconciliation, not a blocker for v1's conservative single-loan-only approach).

## 2026-07-19 — Next-5 improvements round: 2 crashed agents recovered mid-flight, all 5 completed (chip next5-improvements-2026-07-18, Code/02323ec2)

Same F-id-dossier-adjacent discipline as the architecture-refresh (independently verify before trusting, resume don't rewrite when real partial work exists). Two of five subagents (N2 sourcing-data, N3 debt module) were cut off mid-implementation with no final report — investigated for orphaned work before re-running rather than blindly restarting, per `feedback_verify_subagent_safe_claims`.

- **N1 — deal-unblock drafts (3 requested):** 2040 S Hamilton OM request and 275 Old County Line diligence list drafted to Outlook Drafts + deal folders, grounded on live deal-folder/Notion state, nothing sent. **754 Old State Route 74 PSA-revision memo was built on a stale premise** (the original setup-review's "counsel non-responsive since 6/11" framing) that a 2026-07-17 Gabriel correction in `projects.md` had already overturned (Eric negotiating PSA directly). Caught by cross-checking memory before presenting the deliverable; both the memo file and the Outlook draft were discarded (soft-deleted, recoverable) on Gabriel's explicit choice.
- **N2 — sourcing-data upgrades:** first attempt crashed with zero trace in its target dirs; second attempt discovered a genuine orphaned worktree (`ora-skills/.claude/worktrees/next5-sourcing-data`, real partial SKILL.md edits) that my own initial "is it lost" check had missed (checked file mtimes, not `git worktree list`) — resumed and completed rather than restarted, avoiding a collision the resuming agent itself correctly detected and halted on first. Built `county-parcel-screen/references/county-endpoints.v1.json`, a live-verified ArcGIS parcel/CAMA registry across all 22 documented counties (19 VERIFIED, 2 VERIFIED-PARTIAL, 2 honest NOT-FOUND); caught 2 real endpoint drifts (Dane Co WI service rename, Kent Co MI now token-gated) and one accuracy issue (MD registry is point geometry, not polygon — insufficient for the pad/yard split; fixed the flood-zoning-dd cross-link text to say so). Real drive-time routing (OpenRouteService keyed → keyless OSRM public server, live-verified → straight-line last resort) added to submarket-spatial-analysis, each tier honestly labeled. Pushed: `ora-skills#next5-sourcing-data` (b5ad834) and `ora-claude-config@main` (b982a47, county-parcel-screen registry only). Still needs: package-and-stage-skill + Gabriel's Save-skill click before either ora-skills change reaches the Cowork cache.
- **N3 — debt & maturity warehouse module v1:** first attempt left real, high-quality partial code uncommitted in `oxford-command-center/.claude/worktrees/next5-debt-module` (based on ef9e73e, before main advanced 7 commits). Resumed rather than discarded — independently re-reviewed every existing line rather than trusting the draft. Its own adversarial refute pass caught a real NaN-comparator determinism bug in the timeline sort (two same-key events, e.g. two demand-callable loans, produced `Infinity - Infinity = NaN`); fixed and proven load-bearing. Merged cleanly with main's 7 intervening commits. Full suite 233 files/2865 tests, typecheck, lint all green. **Independent Fable-tier review (financial-decision code, reviewer ≥ implementer per house doctrine): APPROVE-WITH-NOTES** — reproduced every number from scratch, ran 9 of its own adversarial edge cases, confirmed governor-read discipline (DSCR 1.25/LTV 0.40/0.65 read-only, never redefined), confirmed the multi-loan-property guard genuinely excludes rather than silently picking a value. One architectural note surfaced (the 65% per-property refi ceiling isn't DB-backed/ratifiable like the other two governors — pre-existing gap, not introduced here, worth a future consolidation pass). Pushed `oxford-command-center#next5-debt-module` (b09995e); opened **draft PR #222, titled DO NOT MERGE**, listing every blocking confirm (workbook column mapping ×2, ratify the [SPECULATIVE] 12/24-month refi-window thresholds) — awaits Gabriel per Hard Invariant 4.
- **N4 — oxfordra.net site fixes:** async-CSS pattern fixed on 5 pages (not the originally-briefed ~10 — verified live), LinkedIn Insight placeholder stripped from 16 files (not 62 — that count had drifted), dead `snap.licdn.com` CSP entry flagged but not touched (blast-radius). Isolated worktree branch `website-canonical#next5-site-fixes` (2451873), build/JSON-LD/local-render all verified. **Committed, deliberately NOT pushed** (Hard Invariant 2 — oxfordra.net always needs explicit per-deploy confirmation; a push risks triggering Netlify).
- **N5 — financial-skill cache verification:** read-only. monthly-close repo↔Cowork-cache byte-identical (Restoration Church Trust ~$983K balloon alert, due 2027-02-20, confirmed intact in both). Surfaced two real gaps, neither actioned this pass: `cash-position-monitor` is entirely absent from the Cowork cache (repo-only, never synced); the drift-check scheduled task's last registry-recorded firing (07-13) has no matching Notion output — only the 07-16 manual run posted results, meaning the automated cadence may be silently under-reporting even when it fires.

**Coordination:** ran alongside the concurrent `setup-improvement-top5-2026-07-18` session (5 different plans, completed same evening — flywheel merged, appsec sweep landed dependency-security fixes now visible on oxford-command-center main) without collision; every write this round was pathspec-scoped and verified against `git status`/`worktree list` first, catching one real foreign-staged-file risk (`commit-provenance-guard.py` blocked a bare `git commit` that would have swept another live session's staged `open-items-tracker.md` edit).

**Not yet actioned, Gabriel's call:** PR #222 merge (debt module) · PR (unopened) for `next5-sourcing-data` Save-skill reimport · website-canonical branch push/preview-deploy · cash-position-monitor Cowork resync · drift-check cadence-reporting gap.

## 2026-07-19 — Restoration Church Trust note: Notion tracker mislabels corrected; borrower repayment/extension terms remain unconfirmed; HubSpot renewal pipeline stall root-caused

Investigated Gabriel's Restoration Church Trust flag (read-only research agent, then direct Notion corrections). Confirmed via Loan Portfolio Tracker + Covenant Watch history + the 2026-07-18 EOD Action Ledger: Oxford Capital Partners is the LENDER, Restoration Church Trust the borrower, on an originally-~$2.0M IO note at 9.00%, balloon maturity 2027-02-20 (confirmed matches Gabriel's own figure; a mid-session relay of this date as "2026" in an internal sub-agent prompt was this session's own transcription slip, not a data error — corrected before reaching any output). Current balance per the freshest source (Jul-18 EOD Ledger): $979,772, matching Gabriel's figure exactly.

Found and fixed the mislabel in 4 live Notion tracker rows (NOT the dated historical snapshot pages like "Covenant Watch — April 2026" or "Debt Snapshot," which were left untouched as point-in-time records): Loan Portfolio Tracker's "Restoration Church Trust Balloon" row, and 3 rows in the Critical Deadlines Tracker. All previously read "Begin refi/payoff planning" (borrower-side framing, wrong direction) — corrected to lender-side framing matching the already-fixed conditions.ts language (confirm the borrower's repayment/extension intent, not an Oxford-side refinance action). Also found and fixed an independent, unrelated data bug on all 3 Critical Deadlines Tracker rows: the "Counterparty" field said "Oxford Capital Partners" (i.e., Oxford itself) instead of "Restoration Church Trust" (the actual counterparty) -- corrected on all 3.

**Confirmed still unresolved, needs Gabriel's own action:** no record anywhere (Notion, event_log.md, deal-decision-ledger.md) of any borrower-side conversation about repayment intent or extension terms. The April 2026 Covenant Watch report called for "lender conversations by June 2026" -- that deadline passed over a month ago with nothing logged since. Recourse and prepayment-penalty fields are also blank in the Loan Portfolio Tracker. This needs Gabriel's direct outreach or explicit instruction to draft one (outbound counterparty communication -- Hard Invariant 1, not something to initiate unprompted).

**HubSpot renewal-pipeline stall, root-caused (read-only, not fixed):** 50 deals sit in the Lease Renewals pipeline's `appointmentscheduled` stage. 49 of 50 were created in the same ~3-minute window on 2026-03-27 (the 50th, 2026-04-29) -- strong evidence of a one-time bulk import with no downstream stage-advancement automation ever wired up, not an active process that stalled. ~38 of 50 show zero activity since creation. Nearly all share one hubspot_owner_id. One of the 50 is "Lease Renewal — Restoration Church Trust" ($16,714) -- the same mis-entered-loan-counterparty error already corrected in the Notion Tenant DB (OI-009, 2026-07-17) appears to have been carried into HubSpot too; flagged for a retirement decision, not retired here (a live CRM record, Gabriel's call). No property/market/PM-platform field exists on the HubSpot Deal object, so the stall can't be broken down further from CRM data alone -- needs the lease-renewal-pipeline skill's own batch pass once Gabriel sets terms, per his original note.

Detail: OI-021 (open-items-tracker.md).

## 2026-07-19 — ora-cowork-heartbeat write-auth: root cause confirmed, fix requires Gabriel's own manual UI approval (not reachable from any automated session)

Investigated Gabriel's "Cowork heartbeat write-auth is the highest-priority infra fix" flag (read-only, general-purpose agent). Root cause: the LAMS registry entry for ora-cowork-heartbeat has no approvedPermissions grant, unlike sibling tasks that write Notion successfully (e.g. automation-health-monitor carries 8 grants including a Notion page-create grant). This has been documented 3x already (07-16/17/18) and remains unresolved. The task's own SKILL.md claims "tool-grant re-approved 2026-07-17," but a manual "Run Now" UI approval does not persist the same grant that live cron-time approval does -- so the claimed fix did not actually hold.

Current live status is NOT currently blind: the heartbeat's Notion page shows an update as of 2026-07-19T15:54:52Z (~20 min old at investigation time), matching the registry's lastRunAt. But that fire time (11:54 ET) doesn't align with either scheduled slot (05:50/17:50 ET) -- almost certainly another ad-hoc "Run Now," not proof the unattended cron path is fixed. The next genuine unattended fire remains at risk of the same silent-write failure (dispatch succeeds, lastRunAt advances, the actual write never lands -- the exact failure mode documented in [[reference_scheduled_task_approved_permissions.md]]). The GitHub watchdog issue tracking this ("silent for 22.8h") is still OPEN off a stale read and needs manual closure once the fix genuinely holds, not before.

**Structural finding, stronger than the general CC/LAMS write asymmetry:** no MCP tool on EITHER surface (Code/CC or Cowork/LAMS) can write an approvedPermissions grant -- this is UI-approval-only. The only fix is Gabriel personally clicking through the Notion-tool approval prompt in Cowork's own Scheduled Tasks UI during a live unattended fire (a manual "Run Now" does not exercise the same approval path). No automated session, on any surface, can do this. Flagged in OI-020 (open-items-tracker.md).

## 2026-07-19 — conditions.ts balloon-alert direction bug: already fixed 2026-07-16 (PR #217), no code action needed

Gabriel flagged "conditions.ts / Master Workbook balloon-alert direction bug (fires refi/payoff on lender notes)" as an open item. Checked the live code first rather than assuming the report was current: src/analytics/conditions.ts already splits on `l.direction` (borrower vs. lender vs. internal) -- `direction === 'lender'` produces a distinct `note-maturity-*` alert ("Oxford is the lender — confirm the borrower's repayment or extension terms"), capped at severity 'warning' (never critical, since inbound capital isn't an emergency), while `direction === 'borrower'` keeps the original refi/payoff copy. This shipped in commit dd424c2 (PR #217, "fix(analytics): stop telling Gabriel to refinance a note Oxford holds"), merged to main 2026-07-16 -- 3 days before this session. Confirmed server/brief/run.ts (the email Daily Brief generator) imports and calls this same evaluateConditions() -- no separate/duplicated alert-text path -- and confirmed ora-am-brief's own SKILL.md sources its critical-dates section from this exact oxford-command-center alerts-engine output (portfolio.json / Command Center Daily Brief), not an independent computation. So both the in-app Command Center and the emailed Daily Brief already carry the corrected lender-framing text.

**What remains, NOT code:** the Master Workbook's own balloon-alert row (an Excel cell/note inside the live SharePoint source-of-record document) still carries the old borrower-framed "Prepare refinance or payoff strategy" label. No code in this repo reads that label through verbatim -- conditions.ts generates its own alert text independently -- so there is no pass-through bug to fix here. This is a data-content correction inside the live financial source-of-record workbook, which needs Gabriel's own edit (or his explicit go-ahead + the exact sheet/cell location) rather than an unprompted assistant write to that document.

**Lesson (ties to [[feedback_verify_before_repeating_session_claims]]):** a second instance in the same session of a punch-list item being stale relative to the actual code/branch state -- check `git log -- <file>` before treating a described bug as still-open.

## 2026-07-19 — HubSpot Acquisitions-pipeline visibility gap: PR #221 shipped, corrects 2026-07-18's "no code changes needed" call

Re-investigated the 2026-07-18T18:29 finding (HubSpot -> acq_candidates sync gap) from Gabriel's in-turn "fix this" request. That prior session's conclusion -- "No code changes needed once the token is set; the sync is already tested and ready" -- was half right: syncHubSpotPipeline()/POST /acq/sync/hubspot (PR #203) is indeed fully built and tested. But it checked only the token; it never diffed the frontend. AcquisitionsModule.tsx has always had a "Sync from Notion" button (handleNotionSync, wired since PR #153) -- PR #203 shipped the backend HubSpot route but never added its counterpart button. With no UI trigger and no scheduled caller anywhere in the repo or the scheduled-task fleet, the route was structurally unreachable even once a token exists.

Fixed via TDD in worktree fix-acq-hubspot-sync-button (confirmed red against pre-fix code, 5/5 failing; implemented handleHubSpotSync() + "Sync from HubSpot" button mirroring the Notion pattern exactly; local code-reviewer pass found one test-quality gap, fixed). Full gate green: typecheck 0, lint 0, 232/232 test files (2834 tests). PR #221 opened (not merged -- Gabriel's call).

Re-confirmed live via HubSpot MCP: same 4 real deals as 2026-07-18 (6150 Avery Road, 1333 Research Road, 2146 Enterprise Pkwy Twinsburg OH -- still untracked anywhere in projects.md/deal-decision-ledger.md/event_log -- Pendleton Trade Center), plus the 5th legacy/terminated deal at a stale HubSpot stage (unchanged, not touched, this repo's own confidentiality guard blocks naming it here).

**Lesson for [[feedback_verify_before_repeating_session_claims]]:** a prior session's "no code changes needed" is a claim about what THAT session checked, not a verified absence of gaps -- it hadn't diffed the frontend against the backend PR. Re-verify the actual diff/git history, not just re-read the conclusion, before treating a "nothing to fix" finding as closed.

## 2026-07-18 — oxford-command-center: NOI/value/rent reconciliation now live, not CI-only

Closed a real gap flagged in ora-intelligence-platform-master-plan.md: reconcile-runtime.ts (the always-on brain.refresh() check feeding the Health module's Reconciliation card) only verified snapshot-internal invariants -- the cross-check against the workbook's own declared "Portfolio Total" row (NOI/value/rent) lived only in scripts/reconcile.ts, the CI-only gate that does a second independent workbook read. reconcile-runtime.ts's own doc comment explicitly named this as the intentional scope split.

Extended parse.ts to capture that row's NOI/Value (Property NOI cols 13/10) and Annualized Rent (Master Tenant Rent Roll col 14) during the SAME single read that already skips it from the per-entity lists -- zero extra I/O. Added snapshot.workbookTotals (nullable per-field, defaults to null for legacy payloads/workbooks with no such row). reconcile-runtime.ts now cross-checks derived sums against these, plus a cash-history-latest-vs-current check that needed no plumbing at all. TDD (tests added to parse-workbook.test.ts + reconcile-runtime.test.ts), full gate:ci green (typecheck/lint/2819 tests/build/bundle-budget), and separately re-verified npm run reconcile against the REAL production Master Workbook (all values match).

Mandatory adversarial REFUTE pass (financial-adjacent code) found one genuine defect before commit: the portfolio-total-row capture had no first-match-only guard, creating last-match-wins semantics inconsistent with reconcile.ts's own find() helper (which returns on first match) -- dormant today but a real latent fragility if a second matching row ever appeared. Fixed (first-match-wins in both parseProperties and parseLeases) with a regression test (two matching rows, asserts the first is kept), re-verified full gate green + real-workbook reconcile clean again.

Committed 33c9aa6, pushed, GitHub Actions CI green (gate job; refute-required correctly skipped -- PR-only trigger, doesn't fire on a direct main push, and the REFUTE pass was performed manually per this org's doctrine regardless).

## 2026-07-18 — HubSpot Acquisitions-pipeline visibility gap: verified live, precisely scoped, reported to Gabriel

Verified directly against live HubSpot data (Notion/HubSpot MCP connectors came online mid-session): oxford-command-center's HubSpot -> acq_candidates sync (PR #203, commit de23c8f, tested) is fully built and gracefully handles a missing HUBSPOT_TOKEN (400, not a crash) -- but the token was never set in .env, so acq_candidates has 0 rows. Queried HubSpot directly: 4 real deals sit in the Acquisitions pipeline (885606973) -- 6150 Avery Road (Sourced), 1333 Research Road (Screened), 2146 Enterprise Pkwy Twinsburg OH (Screened), Pendleton Trade Center (Screened) -- plus E Fulton Street (Due Diligence stage, but that's the already-declassified/terminated deal; HubSpot's stage just hasn't been updated to reflect that, a separate lower-priority item).

**Real finding: 2146 Enterprise Pkwy, Twinsburg OH does not appear anywhere in projects.md, deal-decision-ledger.md, or recent event_log entries** -- sitting in HubSpot's Screened stage since 2026-03-22, touched 2026-07-17, with zero corresponding awareness in the memory system. Flagged prominently to Gabriel rather than silently noted.

Sent a report to ggoldberg@oxfordra.net only (send-log confirms OK, 2026-07-18T18:29:06-04:00) with the precise deal table and the exact unblock step (add HUBSPOT_TOKEN to oxford-command-center/.env -- a credential, not something to be entered by an assistant). No code changes needed once the token is set; the sync is already tested and ready.

## 2026-07-18 — systematization-candidates branch PARKED (Gabriel-directed), not merged

Investigated for a possible merge to unblock Plan 2 of the setup-improvement effort. Of its 3 substantive changes: (1) `hooks/ora-autonomy-gate.py`'s OVERRIDE_DIR test-seam fix is **obsolete** — main's 2026-07-17 refactor deleted the bare `OVERRIDE_DIR` constant entirely in favor of the shared `hooks/lib/override_tokens.py` module (`Tier`/`token_grants`/`token_path`); merging the branch's version would partially revert that adversarially-reviewed hardening. (2) its `.gitignore` addition for `maintenance/_state/doctrine-status.json` is **redundant** — main already ignores that path (line 105, landed via a different commit). (3) `agents/deal-recon.md` is already identical on main. Only `maintenance/model-currency-probe.py` (+ test) is genuinely new and non-conflicting, but not merged this pass per Gabriel's explicit choice to park rather than cherry-pick.

**Decision: parked, not merged.** Branch/worktree left as-is at `.claude/worktrees/systematization-candidates` (430bf19) — do not re-attempt a wholesale merge without re-checking `hooks/ora-autonomy-gate.py` against whatever the current override-token architecture is by then, since it may drift further. If `model-currency-probe.py` is wanted later, cherry-pick that one file only.

Plan 2 (effect-verification layer) was NOT actually blocked by this branch's unmerged state in practice — main's `.gitignore`/`_state` untracking convention already independently satisfies the compatibility concern that motivated waiting on it.

## 2026-07-18 — Open-sessions board dispatched; 10 items decided

ora-open-sessions-board 2026-07-18 17:00 ET run: probed 292 unarchived sessions, 10 actionable items reached the board (7 NEEDS-ANSWER, 3 INTERRUPTED; 18 excluded as fleet runs / already-decided-and-unchanged / sub-30-min). Notion deal-stage reconciliation ran clean (0 transitions). Gabriel's decisions:

- **Punch-list tracker "finish this" ask** (local_d0909d82) — Drop, nothing to finish.
- **Northwood tenant-row fix commit** (local_ba9fbd75) — Leave the hunk uncommitted for the consolidation pass rather than isolating and committing now.
- **Midwest expansion (Dayton/Fort Wayne/Omaha) target-markets.json draft** (local_54410484) — Not yet.
- **package-and-stage-skill branch push/PR** (local_46a56789) — Wait; branch stays local, unpushed.
- **Cowork EOD verification monitor midday check** (local_1f5d6000) — Drop; no second checkpoint added.
- **acquisition-underwriting v4.0 upgrade prompt** (local_4eedbc94) — Drop; prompt stays in outputs/, not run in Code.
- **Newsletter archive link-list save folder** (local_c7eb8de7) — Confirmed: Investment Candidates 2026 (its current location; no move needed).
- **Cornerstone Tours SEO audit DOCX formatting QC** (local_95a563f2) — Drop; deliverable stands as-is, no further formatting pass.
- **MEMORY.md lines 84-85 over-length trim** (local_b5d10619) — Drop; left over the 150-char policy cap, non-blocking.
- **Catfish Court, WI (5515 Catfish Court) IC decision** (local_71295051) — Wait; LOI at $2,742,267 vs. Pass not decided. Notion Stage stays "Candidate" — no ledger row (not a terminal disposition).

All ten sessionIds upserted into answered.json. No outbound counterparty communication triggered by any of these decisions.

## 2026-07-18 — Architecture-refresh: 3 standing artifacts refreshed + G-batch executed (chip architecture-refresh-2026-07-18, Code/02323ec2)

Fable-planned, Gabriel-ruled (interactive batch, all recommendations accepted), executed same session under the chip claim. Evidence dossier: `00_Governance/outputs/2026-07-18_Architecture-Refresh_FactsDossier_v01.md` (F-01..F-29); plan: `2026-07-18_Architecture-Refresh_ImplementationPlan_v01.md`.

- **Artifacts republished same-URL after a Fable cross-artifact refute pass (PASS-with-edits, 10 defects fixed pre-publish):** schematic → REV 2026-07-18d (probe suite green: governor-drift exit 0/682 files, doctrine-integrity 8/8, memory-integrity 112/112, confidentiality-guard 131/131; fleet VERDICT OK 43 enabled = 22 CC + 21 LAMS) · review-v02 (closeout matrix evidence-upgraded: 0.C and 4.1 → Closed; 12/34 closed) · setup-audit (new "Observations for the 2026-09-15 audit" section — documented, deliberately NOT executed per the frozen cadence).
- **Producer-clobber repaired:** the schematic's durable source (`~/.claude/artifacts/claude-code-schematic.html`) had silently diverged from the published artifact by two revisions (source rev 07-16 vs artifact rev 07-17c) — Monday's ora-cc-schematic-refresh fire would have wiped revs b+c. Source synced to rev-d; WebFetch post-verify confirmed all 3 URLs serving new content.
- **Roster-undercount root-caused:** registry-membership-probe.py omits enabled future-fireAt one-time tasks → session-context showed LAMS 19 vs live 21 (ora-cam-data-backfill @08-15, ora-counsel-review-standard-positions @08-03). Documented for the 09-15 audit; probe not modified.
- **G-A router fix LANDED (L2: fixtures-first, tests green):** engineering-router.py no longer suggests L7 on research/plan/"do not code" prompts and no longer scans system-notification text for the confidential-cloud-review DOCTRINE BLOCK (3 live misfires 07-18 were the fixtures). Root causes: substring "ship/deploy" match + L7-first sort; unconditional prompt-field scan. hooks/tests/test-engineering-router.py extended (7 assertions incl. 2 regressions); ALL PASS, re-verified independently by the orchestrator.
- **G-E retire flow:** 4 spent one-time tasks (heartbeat-beacon-recovery-check, heartbeat-check-backup-verify, ora-setup-review-closeout-recheck, ora-uw-northridge-brockton-full) deleted via supervised delete_scheduled_task, registry re-verified at exactly 22 entries/0 spent, folders archived to `scheduled-tasks/_archive_2026-07-18_retired/`. Northridge-brockton had FIRED clean 14:16:29Z before retirement; run-outcome verification delegated to session local_47ad0cef.
- **G-B:** dead RAM-guard chain (ram-watchdog.sh + ram-guard.ps1, never wired in settings.json) archived to `_archive/2026-07-18_ram-guard-retired/`; tech.md updated.
- **G-C:** roi-brief-ws1-ws4-ws7 worktree removed (0 unmerged commits, branch preserved); gate-matcher-hardening (1) and systematization-candidates (3) KEPT — intentional unmerged anti-revert patches.
- **§7b completion:** EFULTON-counsel-questions staging file archived to `_archive/2026-07-18_efulton-declassification/` (missed at 07-09 declassification).
- **setup-review-closeout chip DONE-closed** on Gabriel's explicit interactive sign-off (the 07-17 TERMINAL entry required a human close).
- **event_log rolled over** (1,137 → 607 live; archive `_archive/event_log_2026-07-18.md`).
- **New standing rule:** all Gabriel decisions via interactive multiple-choice with researched recommendation (`feedback_interactive_decision_questions.md`).
- **Coordination:** ownership conflict with session a67aca7d (origin of the 5-phase tree) resolved by Gabriel ruling + stand-down message; that session pivoted to planning `setup-improvement-top5-2026-07-18` (5 plans incl. Plan-5 hooks hardening — its executor MUST rebase on today's engineering-router.py change). Session 47ad0cef ran parallel deal-side verification, no overlap. Concurrent-session duplicate-work check performed at every write.

## 2026-07-18 — LOI Throughput line added to ora-friday-closeout (v2.1)

Added the Gabriel-carried-forward LOI Throughput block to `ora-friday-closeout`'s SKILL.md (`OneDrive...\Documents\Claude\Scheduled\ora-friday-closeout\SKILL.md`, single-writer check clean — mtime predated this session) as a new Part A step: LOIs generated/sent this week (source: `loi-generation` skill outputs + deal-decision-ledger.md), Notion Acquisition Pipeline stage conversions, and a week-over-week trend line. Report-only, no new send path, reuses the task's existing ggoldberg-only email leg. Bumped to v2.1 with a changelog line; RUN SUMMARY format updated to include the LOI count/delta.

Dry-ran the filesystem-sourced portion against live data: 0 LOI files generated this week (2026-07-11 through 07-18) and 0 new deal-decision-ledger rows — confirmed via direct search, not assumed. Could NOT dry-run the Notion Acquisition Pipeline stage-conversion portion from this Code session (no Notion connector available here) — the SKILL.md's own graceful-degradation line ("LOI pipeline-stage data unavailable this run") will catch that same gap on the real Friday fire if CC/MCP still lacks Notion access then; worth a Cowork-surface check before 2026-07-24 if that matters before the real fire.

## 2026-07-18 — ora-uw-northridge-brockton-full closeout: QC'd, verdict-drift found, summary sent (Notion row + registry cleanup still pending)

Closed the loop on the 2026-07-18T14:16:29Z `ora-uw-northridge-brockton-full` run whose summary email never sent. Dispatched two independent underwriting-checker passes (re-derived cell formulas directly, not a recalc-trust pass) against both 07-18 workbooks/memos, then diffed against the 07-16 manual baseline (`ORA_ICMemo_{2900-Northridge-Dr-NW,4331-Brockton-Dr-SE}_v1.0.*`, `ORA_Underwriting_{...}_v1.0.xlsx`).

- **2900 Northridge:** DSCR 1.45x PASS, LTV 65% at ceiling, aggregate 40% correctly left unverified, basis floor FLOOR-FLAGGED (59.9% vs 61.5% required), INVERTED-SPREAD flagged, MI reassessment tab confirmed formula-driven (v4.0-compliant). Real gap found: single-tenant rollover (Nov 2031 lease expiry, Year 5 of a 10-yr hold) is not stress-tested even in Bear — no re-lease TI/LC/downtime priced at that point.
- **4331 Brockton:** same governor picture (DSCR 1.45x PASS, LTV 65%, both Stage-1 floors breached — Basis 57.43%/Yield 6.67% vs 65%/8% required, INVERTED-SPREAD). Verdict unchanged from 07-16 (kill on floors). **Verdict-drift finding:** Base levered 10-yr IRR swung from -0.26% (07-16) to +6.60% (07-18) with Bear/Bull moving similarly, driven entirely by model structure (an all-cash-close + Yr2 65%-LTV cash-out refi, full lease-up credit) not by any change in source facts — and the 07-18 IC memo never discloses or reconciles the swing. Secondary discrepancies noted (lease-up carry likely understated vs the workbook's own reassessed-tax figure; missing standing 5% LC/2mo free-rent; vacant-share opex not deducted; MI uncap mechanic mis-stated conservatively; inverted-spread magnitude understated; CoStar rent comp unverifiable this session).
- Sent a closeout summary (governor status, both findings, bottom line) to ggoldberg@oxfordra.net only via send-via-outlook.ps1 — confirmed OK in send-log.
- **Not done (Gabriel-decision, not auto-executed):** closing the TERMINAL setup-review-closeout chip; retiring 5 spent one-time registry entries; a Notion Ops Hub (32b6ecd8) completion row — no Notion connector available in this Code session, needs a Cowork-surface pass.

## 2026-07-18 — 511/275 re-screens confirmed complete (were already done, not missing); monthly-close verified current

Verified the 2026-07-17 Gabriel-authorized `verified-deal-recon` re-screens for 511 Industrial Mile Rd and 275 Old County Line Rd, which the 07-18 artifact-content plan flagged as "launched but never confirmed." Found they DID complete — session `local_380f407b-4255-4be9-ac5e-44b051c5cc2e` (07-17 22:49 ET) surfaced the results as another session's then-uncommitted `projects.md` diff; that diff has since landed and is now the current record (memory/projects.md lines 24-26). No re-run was needed.

- **511 Industrial Mile Rd — verdict PASS.** The "below-replacement bargain" thesis broke on a closer comp (1945 Jackson Rd prices below the subject despite having a dock) and lower-than-assumed achievable rent. CRITICAL unresolved fact: the live Crexi listing + Auditor land-use code ("HEALTH SPA") suggest this may currently be an operating indoor sports center, not a vacant industrial shell. The recon's own recommendation is do NOT re-engage broker Noah Kahkonen on the prior bargain framing — so no outbound broker contact is actually being proposed right now; if Gabriel wants to revisit at all, the recon says confirm actual current use with the broker first.
- **275 Old County Line Rd — verdict PURSUE, contingent.** Building resized to a corroborated 30,200 SF (vs. the prior 18-25K SF estimate), pushing the basis discount to 40-53%, past the 25% floor; ~7 active tenant suites suggest substantially occupied. Roof/HVAC totally unverified; a departed gunsmithing tenant (hot bluing/parkerizing/Cerakote) needs explicit Phase I REC scoping. Next step is Auditor/rent-roll confirmation (internal research), not outbound contact.
- **Bonus (same batch, not in original scope):** 2040 S Hamilton Rd also re-screened same day — verdict PURSUE on basis alone; next step (calling listing broker NAI Ohio Equities to confirm occupancy/rent) IS outbound counterparty contact and would need Gabriel's confirmation if pursued.
- **Residual gap:** the recon notes explicitly say these supersede the Notion Acquisition Pipeline tracker, which is "now stale" relative to this — Notion has not been updated to match. That's a Cowork-surface follow-up (no Notion connector in this Code session).

**monthly-close currency check:** compared `C:\Users\Owner\ora-skills\monthly-close\SKILL.md` (canonical, v2.1, HEAD, clean tree) against the live Cowork runtime cache (`AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\...\skills\monthly-close\SKILL.md`) — byte-identical, no drift. No packaging/staging or Save-skill action needed; current for the 2026-08-01 close cycle.

## 2026-07-18 — ora-cowork-heartbeat: re-confirmed still broken, blocked on Gabriel/Cowork-surface action

Re-checked the LAMS registry directly (`scheduled-tasks.json`): `ora-cowork-heartbeat` still has NO `approvedPermissions` array (lastRunAt 2026-07-18T10:42:05Z, the 05:50 ET slot firing late as an app-open catch-up), unchanged since the 2026-07-17 root-cause finding and both ACTION-REQUIRED alerts (07-17 18:49 ET, 07-18 10:16 ET). No new diagnosis needed — this session's Code surface confirms the already-documented root cause (missing Notion-write tool grant; manual "Run Now" approval does not persist to the registry the way live cron-time approval does for sibling tasks) is still the live blocker. Per standing doctrine, hand-editing `scheduled-tasks.json` remains prohibited and no MCP tool exposes `approvedPermissions` for writing — this cannot be fixed from Code. Needs either Gabriel doing a supervised "Run Now" in Cowork's Scheduled Tasks UI (explicitly granting/re-approving the Notion write tool at the prompt if one appears) or a Cowork-surface session performing a supervised `update_scheduled_task` write. No further automated action taken this session; flagging to Gabriel per [[open-items-tracker]].

## 2026-07-18 — ora-pm PortalDashboard divide-by-100 bug fixed; discovered CI has silently blocked all deploys for 2 days

Fixed the 07-16 audit's finding #3 (PortalDashboard.tsx divided plain-dollar total_balance/amount fields by 100, showing tenants 1/100th of their true balance) — deleted the local fmt/fmtDate, switched to canonical formatCurrency/formatDate, added a format-contract regression test plus a source-level guard against reintroduction. Full local gate green (tsc 0 errors, 169/169 tests), adversarial REFUTE pass confirmed the fix correct on all axes and flagged the one real gap (test doesn't render the component) — closed with the source-guard test. Committed `43f0b76`, pushed.

**Bigger finding surfaced while confirming deploy:** CI (`npm run typecheck`) had been failing on every push to main since commit `0367ec0` (2026-07-16) — a Windows-vs-Linux TypeScript resolution difference meant `node:fs`/`node:path`/`__dirname` in `tests/db/ar-ledger.test.ts` typechecked locally but not in CI's clean Linux install, and the single CI job runs typecheck -> test -> build -> deploy sequentially, so the failure silently blocked deploy too. `wrangler pages deployment list` confirmed production was still serving commit `866480f` — the commit immediately BEFORE the two 2026-07-16 critical DB fixes (`0367ec0` ar_ledger cartesian-fan-out, `b7321f6` property_name). Those fixes had been merged and believed-shipped for 2 days but never actually reached ora-pm.pages.dev. Root-caused and fixed by pinning `@types/node` as a devDependency (matching CI's Node 20) and adding explicit `/// <reference types="node" />` to the two affected test files rather than widening the global tsconfig `types` array (which is deliberately restricted to avoid a DOM/@cloudflare/workers-types conflict). Committed `f196337`, pushed. CI ran fully green (typecheck/test/build/deploy all ✓) and `wrangler pages deployment list` confirms production is now on `f196337` — the ar_ledger fix, property_name fix, and this divide-by-100 fix are all finally live.

**Concurrent-writer note:** mid-verification, detected a second, legitimate concurrent session actively fixing the related Charge/Lease schema-drift bug (audit finding #7) in the same shared checkout, citing "Gabriel's 2026-07-18 ruling" in its own code comment. Left `src/portal/lib/portal-api.ts`, `PortalMyLease.tsx`, `PortalPayNow.tsx`, and its two new test files untouched per single-writer doctrine; verified no file overlap with my own committed diffs before pushing.

**Not fixed here (flagged separately):** a real crash risk found during the REFUTE pass — `PortalPayNow.tsx:139` falls back to a `charge_type` field that doesn't exist on the schema, throwing on any charge with no description. Spawned as its own task (`task_6a25b41e`) rather than folded into this fix.

## 2026-07-18 — 3 most-recent artifacts remediated: schematic-working, review-v02-working.md, Setup Audit 2026-07-09

Gabriel requested a deep review + fix plan for his 3 most recently updated Claude.ai artifacts (all touched 2026-07-18), then had it re-evaluated via Fable and executed via a subagent-driven remediation pipeline (fact-verification → 3 parallel draft writers → cross-artifact refute pass → 2 targeted fix passes → publish). All 3 republished in place, same URLs.

**Most consequential finding:** review-v02's closeout claim that `ora-uw-northridge-brockton-full` "was retired rather than fired" was factually wrong per live `list_scheduled_tasks` + event_log evidence — the task's deadline was re-armed/slipped from 2026-07-17 16:01 ET to 2026-07-18 10:00 AM ET and it DID fire today (`lastRunAt` 2026-07-18T14:16:29Z), then auto-disabled per normal one-time-task lifecycle. Corrected in the artifact. **Open follow-up, not yet resolved:** whether the fired run's actual output (6-tab Excel workbook, summary email) completed successfully has not been confirmed by any artifact or memory entry — flagging for Gabriel or a follow-up session to verify directly.

**10 facts verified against ground truth** (skill version, task KEEP/retired state, 754 Old State Route 74 pipeline stage, B3 migration closure, Apify/chrome-devtools disposition, confidentiality-guard test count, live fleet counts, live agent roster count, underwriting-defaults table fill-state, dropped-connector dispositions) — dossier at session scratchpad, not persisted. Several original review-pass "findings" (754 dual-classification, KEEP-ruling "reversal") turned out to be false positives on closer reading, not real contradictions — resolved via re-reading rather than a documentation fix.

**Process gap identified and closed:** all 3 artifacts shared one root-cause defect — Resolved/Closed claims asserted without a citation. New standing memory: [[feedback_artifact_citation_requirement]]. No registry writes were needed or attempted; no `BLOCKED-NEEDS-COWORK` items surfaced.

## 2026-07-17 — OI-009: Granite Tops vacating, unsigned lease-extension addendum now moot (OI-009 sub-item)

Gabriel confirmed Granite Tops & More is vacating end of month (2026-07-31), mooting the unsigned 5/28/2026 addendum that had proposed extending the lease to 2029-05-31 — the tenant isn't renewing, they're leaving. Wrote via `notion-update-page`: `Lease Status` → Notice Given, `Lease Expiration` → 2026-07-31 (vacate date). `Monthly Rent` ($16,713.65, still unexplained by any source found) left as-is — now a move-out reconciliation question rather than a lease-terms one. Verified via fresh fetch. This closes the last blocking item on OI-009's 4 named stragglers list — only Chesapeake Communications (already retired) and the untouched rest of the 93-row universe remain. Detail: `open-items-tracker.md` OI-009.

## 2026-07-17 — OI-009: Maryland Hospital Association tenant-rename question decided (OI-009 sub-item)

Gabriel decided the LogicQual Research Institute reassignment flagged in the prior entry: keep `Tenant Name` as Maryland Hospital Association, no rename. Updated the row's `Notes` to record the decision. Closes the last open thread on this tenant. Detail: `open-items-tracker.md` OI-009.

## 2026-07-17 — OI-009: Maryland Hospital Association resolved from Gabriel-supplied executed PDF (OI-009 sub-item)

The Third Addendum found earlier this session was an unexecuted draft, superseded by the actual final version. Gabriel supplied the fully-executed PDF directly (`Lease Suite B2-3 MHA Third Addendum Fully Executed 05.2026 -- 2203-2207 Northwood.pdf`) and stated the terms (Termination 6/30/2027, Rent $2,332/mo) before I finished extracting it. Standard PDF text extraction (`pdftotext`, `pdfminer`) failed on broken font encoding — pages were rendered to images via `pypdfium2` and read visually instead, which confirmed Gabriel's figures exactly and the Adobe Sign audit trail (signed by Gabriel Goldberg for Landlord, 2026-05-06, "Agreement completed"). Wrote `Monthly Rent` 1483.39→2332 and `Lease Expiration` null→2027-06-30 via `notion-update-page`, verified via fresh fetch. Separately surfaced (not acted on): the same addendum reassigns the Tenant under the Prime Lease from Maryland Hospital Association to "LogicQual Research Institute, Inc." (an MHA affiliate), releasing MHA from all obligations — flagged in the row's `Notes`, left under the existing Tenant Name pending Gabriel's decision on renaming. Detail: `open-items-tracker.md` OI-009.

## 2026-07-17 — OI-009: Harold Palmer resolved, Maryland Hospital / Granite Tops re-checked (OI-009 sub-item)

Re-checked the 4 named 93-row-universe stragglers left open from earlier OI-009 passes. **Harold Palmer**: located the addendum's source `.docx` (prior pass only found the DocuSign completion-certificate page) plus its own DocuSign audit trail confirming full execution (signed by Eric Goldberg, 2025-03-26). Wrote `Monthly Rent` 1157→1166 and `Lease Expiration` null→2027-04-30 via `notion-update-page`, verified via fresh fetch. **Maryland Hospital Association**: found a newer Third Addendum resolving the earlier entity-name ambiguity (confirms "The Maryland Hospital Association, Incorporated" as the tenant's proper name) and giving Termination 5/31/2027 + Rent $2,332/mo effective 6/1/2026 — but no executed/signed copy located despite two targeted searches, so left unwritten pending confirmation. **Granite Tops**: re-confirmed still unresolved, same blank-signature addenda as before plus one previously undocumented smaller-footprint draft. **Chesapeake Communications**: already retired per Gabriel's prior decision, fresh search found nothing new. Detail: `open-items-tracker.md` OI-009.

## 2026-07-17 — ora-uw-northridge-brockton-full RE-ARMED (Gabriel-directed) — on CC/MCP, not LAMS

- **Gabriel directed a clean scheduled re-arm** of the one-time northridge/brockton FULL underwriting that this morning's setup-review-closeout recheck found deleted from the registry (see prior entry — item (c) never fired). Registered via supervised `create_scheduled_task` (MCP, no JSON splice) with QC verified against `list_scheduled_tasks`: `enabled:true`, one-time `fireAt 2026-07-18T14:00:00Z` (10:00 ET), path `~\.claude\scheduled-tasks\ora-uw-northridge-brockton-full\SKILL.md`, id unique across both fleets.
- **Deliberately homed on CC/MCP, not the original LAMS/Cowork fleet.** The task must build a 6-tab Excel workbook (Excel COM) and email a summary (Outlook COM) — both COM paths work only on CC/MCP; the LAMS/Cowork sandbox cannot COM-send. This is the same doctrine that migrated `ora-am-brief` LAMS→CC/MCP on 2026-07-16. The original LAMS design's email leg would have failed structurally.
- **One adaptation vs. the backup SKILL.md:** because `acquisition-underwriting` is a Cowork-surface skill (NOT a CC plugin — confirmed absent from the CC Skill-tool list and per `reference_skill_surfaces.md`), the CC prompt instructs the run to READ AND FOLLOW its authoritative source at `C:\Users\Owner\ora-skills\acquisition-underwriting\SKILL.md` (v4.1, repo HEAD `5dda2cd`, clean; whole skill self-contained in that one file, no references/ subfolder) rather than invoke it via the Skill tool. `ora-flood-zoning-dd` remains a native CC plugin-skill invocation. All else preserved verbatim: both properties + source PDFs in `Business\Investment Candidates -- 2026\`, FULL-mode deliverables, `/outputs/` file-naming + 16-pt QC gate, Notion Ops Hub `32b6ecd8` completion row, ggoldberg-only email via `send-via-outlook.ps1`, DSCR≥1.25 / LTV≤40 aggregate governors, no-fabricate + QUESTIONS-FOR-GABRIEL escalation.
- **OPEN CAVEAT — tool pre-approval for a truly unattended clean run:** the run will use Bash/PowerShell (send script, openpyxl/Excel COM), the `ora-flood-zoning-dd` Skill, Notion MCP writes, and file writes. Per `reference_scheduled_task_approved_permissions.md`, a scheduled task missing a tool grant can pause on a prompt or silently fail the write while `lastRunAt` still advances. To de-risk, Gabriel should click **Run now** once (pre-approves the tool set onto the task) OR accept that the 10:00 ET fire may need a prompt. Flagged to Gabriel this session.
- **Chip status unchanged:** setup-review-closeout stays ABORTED/open from this morning's recheck; re-arming does not retroactively satisfy that DONE-gate (the recheck task is spent). This re-arm is a fresh forward action, not a chip closure.

## 2026-07-17 — Title-archived Row Retired gap swept DB-wide (OI-009 sub-item)

Gabriel asked to check the same title-archive/Row-Retired gap (rows named "⛔ ARCHIVED 2026-07-12 — ..." that never had the Row Retired checkbox actually set) across the whole Tenant Database, not just the 42 already fixed at Northwood. Queried DB-wide with no property filter: 73 additional rows found, spanning 9620 State 350, Zettler, Red Branch, Morrison, FVC/Fairground Village Center, 1100 Rarig, 1900 N Broadway, 29000 Information Ln, and many with a null Property Address. Set Row Retired=__YES__ on all 73 via notion-update-page, verified clean via a fresh DB-wide COUNT query returning 0. Combined with the 42 Northwood rows, 115 total stale archived rows are now correctly flagged across the entire Tenant Database — this gap is fully closed everywhere, not just Northwood. Detail: open-items-tracker.md OI-009.

## 2026-07-17 — Northwood title-archived Row Retired gap closed (OI-009 sub-item)

Gabriel asked to close out the 42 Northwood-tagged rows (re-counted precisely from the earlier "~45" estimate) that were archived by title prefix (`⛔ ARCHIVED 2026-07-12 — ...`) in a 2026-07-12 remediation but never had the `Row Retired` checkbox actually set (the same gap OI-004 closed for other rows, never swept DB-wide). Set `Row Retired=__YES__` on all 42 via `notion-update-page`, verified clean via a fresh COUNT query returning 0 remaining. Scoped to the Northwood cluster only — the same gap is unverified across the rest of the Tenant Database. Detail: `open-items-tracker.md` OI-009.

## 2026-07-17 — Northwood bulk address fix closed (OI-009 sub-item)

Retried the Notion `query_data_sources` SQL tool after it hit an `entitlement_required` quota wall earlier (all of today's parallel OI-009 research agents had exhausted the free query allowance). Quota reset after ~1h; query returned 76 rows still on the wrong `2203-2207 Northwood — Columbus OH` address option, 45 of which are pre-existing archived-by-title duplicates (flagged as a residual, not touched — out of scope). Corrected all 31 genuinely active rows to `2203-2207 Northwood Dr — Salisbury MD` via `notion-update-page`, including 2 rows (Bay-Care Heating & Air LLC, Childs Play Diesel Performance) that earlier same-day cluster passes had written to the old wrong option before the address bug was known. Verified clean via a fresh query: 0 active rows remain on the wrong address; 38 rows now on the correct option (31 + 5 from the original pass + 2 from Zettler), reconciling exactly. Address-only fix — Harold Palmer and Maryland Hospital Association's rent/date fields were deliberately left untouched per Gabriel's earlier instruction. Separately noted: `task_6719632a` (the spawned follow-up session) ran on a Code surface without Notion access and correctly declined to guess at the bulk fix, only handling the Restoration Church Trust retirement (redundant with, and consistent with, the earlier retirement — verified no corruption). Detail: `open-items-tracker.md` OI-009.

## 2026-07-17 — OI-009 bulk lease-abstraction pass (5 parallel clusters + Gabriel-gated writes)

Gabriel authorized starting the OI-009 bulk pass (previously deferred as low-priority). Ran 5 parallel research agents against the Notion Tenant Database, each independently verifying against primary lease documents before writing: Red Branch stragglers (4/5 resolved), Zettler (7/8 + 1 partial), Northwood (5/7 checked — cluster turned out to be ~80 rows, not 7; follow-up chip spawned for the remainder), Sunburst (3/3), and 6 no-address-but-Active tenants (6/6). 26 of 29 originally-targeted tenants resolved this pass. Real bugs found: a new landlord-name-in-Tenant-Name variant (Seafire Properties LLC), every Northwood row carrying the wrong city/state (Salisbury MD tagged as Columbus OH — new select option added), and a $2M loan counterparty ("Restoration Church Trust") mistakenly entered as a tenant.

6 decisions surfaced needing Gabriel's judgment, all resolved via AskUserQuestion and executed same session: Eurosort's address added as a new schema option (55 New Plant Court — Owings Mills MD); InSite Build updated in place to its $50/mo signage-license terms; Restoration Church Trust retired from the Tenant DB; Chesapeake Communications LLC retired as untraceable bad data; Granite Tops & More and the two remaining Northwood tenants (Harold Palmer, Maryland Hospital Association) left open pending further documents, per Gabriel's explicit choice not to guess. OI-009 remains OPEN — real residual scope (~35 Northwood stragglers) tracked via task chip `task_6719632a`. Detail: `open-items-tracker.md` OI-009.

## 2026-07-17 — setup-review-closeout chip: proper 16:10 ET recheck run — ABORTED (TERMINAL); item (c) task deleted, never fired

- **`ora-setup-review-closeout-recheck` fired on schedule** this run (registry `lastRunAt 2026-07-17T22:47:21Z` = 18:47 ET, after its 20:10Z/16:10 ET `fireAt`; task now `enabled:false`, auto-disabled — this was the proper run the 13:54 ET early-fire abort deferred to). STEP 0 concurrent-writer check clean: the only "setup review closeout recheck" session (local_87aaebe8) is not running; no live session overlaps the chip / "northridge" / "closeout" title.
- **DONE-gate re-verified against LIVE state — NOT 6/6; ABORTED:**
  - **(a) `ora-task-integrity-guard` — fired, but alarmed.** `lastRunAt 2026-07-17T16:55:18Z` (12:55 ET, after 12:45 target); STEP-1.5 emitters all ran clean (see item d). **Caveat / not-clean:** the 12:55 run's registry-membership-probe logged a LAMS drop `ora-skills-reimport-watch` (`membership.log 2026-07-17T13:00:35 drops={'lams':['ora-skills-reimport-watch']}`, re-synced to `drops=-` by 13:01:45). Under the guard's v1.5 doctrine a registry drop is a STEP-3 alarm. Almost certainly benign — a live "Reimport 3 pending ora-skills into Cowork cache" session is active and that one-time watch legitimately left the registry — but not independently confirmed as intended, so treated as an alarm, not clean.
  - **(b) `automation-health-monitor` v1.8 — fired clean.** LAMS registry `lastRunAt 2026-07-17T15:08:57Z` (11:08 ET, after 11:05 target); LAMS `_state` clean, no drop attributable to it.
  - **(c) `ora-uw-northridge-brockton-full` — DID NOT FIRE (decisive, terminal blocker).** Absent from BOTH registries: not in CC/MCP `list_scheduled_tasks`, and a full read of the LAMS registry (`scheduledTasks` len=23) contains no such task. It is NOT present even as a consumed one-time entry — compare `ora-heartbeat-fix-verify` / `psa-reconciliation-fix-monitor`, which fired today and remain as `enabled:false` with a `lastRunAt`; a fired one-time task is retained, a **deleted** one vanishes. Zero run artifacts dated 2026-07-17 in `Business/Investment Candidates -- 2026/` or its `outputs/`. The task was removed from the LAMS registry before its 16:01 ET fire window and will never fire (this recheck is the last automated check — it just auto-disabled).
  - **(d) State timestamps — all advanced past the 2026-07-16 baseline:** `registry-membership.log 2026-07-17T14:43:35` (was 07-16T13:50:00); `fleet-heartbeat.json ts 2026-07-17T17:02:20Z` (was 07-16T17:50:00Z); `push-fleet-heartbeat.log 2026-07-17T17:02:24Z OK` (was 07-16T17:50:02Z).
- **Substantive purpose already satisfied (context for the human decision, NOT grounds to auto-close):** the northridge/brockton FULL underwriting was completed MANUALLY via a Cowork run on 2026-07-16 — deliverables `ORA_ICMemo_2900-Northridge-Dr-NW_v1.0.docx/.pdf`, `ORA_ICMemo_4331-Brockton-Dr-SE_v1.0.*`, `ORA_Underwriting_{2900-Northridge,4331-Brockton}_v1.0.xlsx`, all dated 2026-07-16 10:06–10:10 ET — the same run that drove the acquisition-underwriting v3.9→v4.0 amendment. Per the 07-16 T5 finding, the skill caches were already current (acquisition-underwriting v4.1, ora-flood-zoning-dd v1.1), so the scheduled re-run would have added no fresh signal.
- **Outcome — chip left OPEN; ABORTED (terminal).** Appended `ABORTED` to chip-claims.log (Code/f7ebd0e5). The chip CANNOT self-close now: the recheck task auto-disables after this run and item (c)'s task is deleted, so no future automated run will re-verify. **Needs a human call (Gabriel / a future session):** either accept the 07-16 manual underwriting as satisfying the chip's substantive intent and close it, or re-arm `ora-uw-northridge-brockton-full` if a genuine against-current-skills scheduled re-run is still wanted. No email — internal bookkeeping; any real watch alarm has its own notify path (item (a)'s guard alarm, if real, already emailed ggoldberg).

## 2026-07-17 — OneDrive Business/Personal physical split executed; machine migration B3 closed

**OneDrive split:** Gabriel authorized the full coordinated execution of the 2026-07-09 proposal (`2026-07-09_OneDrive-Business-Personal-Split_Proposal_v01.md`). All Business-bucket and Personal-bucket items physically moved into new `Business\`/`Personal\` folders at the OneDrive root; Ambiguous-bucket items (incl. `eric spreadsheets\`, `eric documents\`) and the "not filed either way" housekeeping items were left at root, unresolved, per the proposal's own fallback. 4 hardcoded automation paths updated in the same pass (`ora-am-brief`, `ora-master-workbook-ingest`, `ora-pm-ledger` ×2, `ora-deal-sourcing-scan`), all verified reachable post-move via `Test-Path`. **Near-miss caught and fixed same session:** an initial pass mistakenly also redirected the Master Workbook path (`eric spreadsheets\`) under `Business\` even though that folder was correctly left un-moved in the Ambiguous bucket — caught via verification before any automation next ran, reverted. One real omission from the original proposal (`Toledo Sale`, named in the proposal's own Business list) was initially missed in the move, caught via a post-move root-listing diff, and moved. Several items not covered by the 2026-07-09 proposal at all were discovered at root during this pass (`Loans External/`, `GFU/`, `Muirkirk 2013 Refinancing/`, and assorted loose files/scripts) — left unclassified for a future pass rather than guessed at. Detail: `reference_onedrive_business_scope.md`.

**Machine migration B3 (48h burn-in) — CLOSED.** All 10 checklist boxes verified with command-output evidence in one session, including a one-time COM test send to ggoldberg@oxfordra.net (Gabriel's explicit in-session confirmation), confirmed via `send-log.txt`. Detail: `project_claude-setup-audit-2026-07-09.md`.

## 2026-07-17 — bash-guard.mjs (oxford-command-center): OI-011 read/write + cp source-dest false positives closed

- **Closed by a concurrent session the same night**, working in its own git worktree
  (`fix/bash-guard-read-write-oi011`) off this session's OI-010 commit — landed on
  `oxford-command-center` `main`, commit `8006a15`, on top of `60c45ed`. Fixes the 2 pre-existing
  false positives flagged (not fixed) during OI-010's adversarial review: `git config --get
  core.hooksPath` (a pure read) was denied identically to an actual write; `cp` reading FROM a
  guardrail file (e.g. a benign backup) was denied identically to overwriting it.
- Check (d) now distinguishes mutation from read: a trailing token after `core.hooksPath` counts as
  a value being set unless the command carries an explicit `--get`/`--get-all`/`--get-regexp`/
  `--get-urlmatch` flag; `--unset`/`--add`/`--replace-all` and inline `-c core.hooksPath=` still
  always deny. Check (g)'s `mv`/`cp` guard now treats them differently: `mv` still denies the guard
  path in either argument position (source-position `mv` removes/neutralizes the file, same
  severity as `rm` — no pure-read form exists for `mv`), while a new `cpGuardWrite()` helper denies
  `cp` only on its destination argument, covering the plain form plus all 3 `-t`/`--target-directory`
  shapes.
- **3 rounds of adversarial review** (mandatory per CLAUDE.md for `hooks/**` security-gate code)
  found and fixed 3 real bypasses before landing: a dash-prefixed `core.hooksPath` value defeating
  the initial read/write classifier; `--target-dir=` (GNU abbreviation) and `--target-directory`
  (space-separated) both missed by earlier destination-detection passes. 68 tests in
  `bash-guard.test.ts` (was 64), full project suite 231 files/2792 tests green, typecheck 0, lint 0.
  Landed via isolated worktree, fast-forward merge (matching the OI-010 convention), verified zero
  collateral impact.
- Full detail in `open-items-tracker.md#OI-011` (closed) and `project_bash_guard_indirection_gap.md`.

## 2026-07-17 — registry-membership-probe: retired_drops added + hardened (plain-prose retirement reconciliation, completion-only)

- **Trigger:** the 2026-07-17 `ora-task-integrity-guard` run had to hand-reconcile a false `[ACTION]`/exit-1 from `registry-membership-probe.py`. `ora-skills-reimport-watch` was retired earlier that day (twice-logged: paused+archived, then registry entry deleted — see the two `2026-07-17:` lines under the `## 2026-07-16` plugin-reimport entry), yet the probe still alarmed on the drop.
- **Root cause:** the probe's only auto-reconciliation path (`ratified_drops`) required the ceremonial uppercase token `RATIFIED` inside the drop's `## ` section. ORA documents most scheduled-task retirements in plain prose ("... retirement ...", "registry entry deleted"), never that token — so a fully-ratified, event-logged retirement still raised a one-time false alarm.
- **Fix 1 — feature (commit a9fb77e):** added `retired_drops()` — reconciles a drop when a recent (≤14d) event_log LINE names the task id alongside a retirement signal, with per-line date resolution (inline `YYYY-MM-DD` prefix wins, else nearest `## ` header). `main()` now reconciles via `ratified_drops | retired_drops`. Also repaired a pre-existing RED test: the fixture still used `### ` headers and had silently stopped matching after the 2026-07-16 `### `→`## ` split fix (suite was 24/25; the failing assertion was never caught because nothing re-ran it).
- **Fix 2 — hardening (commit 8b2acbd):** closed a residual risk in Fix 1 — matching any `retire*`/`decommission*` verb meant a forward-looking "we should retire ora-X next quarter" or a negated "do not retire ora-X" would have reconciled (silenced) a genuine drop of ora-X. Replaced the verb match with `_retirement_completed()`: reconcile only on accomplished-fact wording — `retired`/`decommissioned`/`deregistered` (past participles, so the infinitives no longer match), `retirement`+`completed`, or `registry`+`deleted`/`removed` (past-tense forms that exclude `deletion`/`deleting`/`pending deletion`). Bonus: a two-part retirement now reconciles only on its part-2 completion line, never the part-1 "entry still exists, pending deletion" line. Completion-only wording makes fragile tense/negation parsing unnecessary.
- **Verification:** suite 41/41 (was 24/25). Verified against the real event_log — `ora-skills-reimport-watch` reconciles via its completion line; planted "should retire … next quarter" and "do NOT retire" lines both → ∅; a planted genuine completion → reconciles. Live probe runs exit 0, no regression.
- **Shipped:** both commits pushed to `ZeOoba/ora-claude-config` `main` (HEAD 8b2acbd); pre-push doctrine gate clean. Two files only: `maintenance/registry-membership-probe.py` + `maintenance/test-registry-membership-probe.py`; no other session's WIP swept.
- **Residual (documented, not fixed):** if a future planning note ever uses accomplished-fact phrasing about a not-yet-removed task, it could reconcile prematurely — vanishingly unlikely given the completion-only gate; guard remains defense-in-depth (task-folder-registration-probe + membership-guard.ps1 + integrity-guard cross-checks).

## 2026-07-17 — Weekly punch-list review: 754 corrected, reference-library governance ratified, deal re-screens launched

Gabriel reviewed the week's open items (open-items-tracker + deal pipeline + reference-library governance + machine migration) via interactive multiple-choice questions:
- **754 Old State Route 74:** corrected projects.md — deal is NOT stalled; LOI agreed, ORA sole purchaser, Eric negotiating PSA directly (live email thread 2026-07-16 re: parking easement not previously logged here).
- **Reference-library governance — all 3 open decisions ratified:** (1) subject-first naming schema (Style Guide §3.1) is canonical over date-first; (2) DocType controlled vocabulary locked to exactly ICMemo/LOI/PSA/RentRoll/Deck; (3) Naming Standard v1.1 ratified provisionally pending Eric's formal sign-off.
- **511 Industrial Mile Rd** and **275 Old County Line Rd:** Gabriel authorized fresh `verified-deal-recon` re-screens from scratch (511: re-screen before re-engaging broker Noah Kahkonen; 275: full redo, treating the 6/12 WAIT-FOR-DILIGENCE plan's diligence as never having happened given 27 days of zero Notion movement). Both launched as background Workflows same session.
- **2040 S Hamilton Rd:** parked — Gabriel will supply the OM/rent-roll/financials location later.
- **Machine migration B3 burn-in:** Gabriel asked for the checklist to actually be run this session (separate from this entry — see its own result once complete).
- **OneDrive Business/Personal split:** Gabriel authorized executing the physical folder move (previously only a non-destructive classification reference existed) — see separate entry once complete.

## 2026-07-17 — setup-review-closeout chip: recheck fired ~2h20m early, ABORTED (not DONE); item (c) northridge not yet fired

- **`ora-setup-review-closeout-recheck` executed prematurely** at ~13:50 ET (17:50Z) while its own
  registry `fireAt` is 20:10Z (16:10 ET) — the entry still shows `enabled:true`, `nextRunAt 20:10Z`,
  no `lastRunAt`, so the proper run is still pending. Because it ran early, item (c) — the one-time
  `ora-uw-northridge-brockton-full` acquisition-underwriting re-run scheduled for **16:01 ET** — had
  not yet fired. Verified: task absent from the live CC/MCP registry; backup folder
  `_scheduled_tasks_backup/ora-uw-northridge-brockton-full/` holds only its SKILL.md (Jul 15) with
  **no `outputs/` and zero run artifacts**. Blocker for the DONE-gate.
- **DONE-gate now 3 clear / 1 blocked / 2 unconfirmed — NOT 6/6:**
  - (a) `ora-task-integrity-guard` — **fired** 12:55 ET (`lastRunAt 2026-07-17T16:55:18Z`, after its
    12:45 target); STEP-1.5 emitters confirmed to have run (see item d). Caveat: membership-probe
    logged one LAMS drop today (`ora-skills-reimport-watch`); its STEP-3 alarm status was NOT
    independently confirmed from the guard's Notion post — treated as unconfirmed, not clean.
  - (b) `automation-health-monitor` v1.8 beacon — **not verifiable from the CC/MCP surface** (LAMS
    task; not in this fleet's `list_scheduled_tasks`). Left unconfirmed.
  - (c) `ora-uw-northridge-brockton-full` (16:01 ET) — **NOT fired** (decisive blocker, above).
  - (d) State timestamps — **all advanced past the 2026-07-16 baseline**:
    registry-membership.log `2026-07-17T13:01:45` (was 07-16T13:50:00); fleet-heartbeat.json `ts
    2026-07-17T17:02:20Z` (was 07-16T17:50:00Z); push-fleet-heartbeat.log `2026-07-17T17:02:24Z OK`
    (was 07-16T17:50:02Z).
- **STEP 0 concurrent-writer check:** clean — no running session with an overlapping
  chip/"northridge"/"closeout" title; chip-claims.log CLAIMED (Code/c3a1e79e 2026-07-16) still open,
  no prior DONE/ABORTED.
- **Outcome:** chip left OPEN. Appended `ABORTED` to chip-claims.log (Code/30222b1d) citing the early
  fire + unfired item (c). The recheck's proper 16:10 ET run (still pending in the registry) should
  re-verify after northridge's 16:01 ET fire and can legitimately close the chip DONE then. No email
  (internal bookkeeping; any real watch alarm has its own notify path).

## 2026-07-17 — bash-guard.mjs (oxford-command-center): git-alias/wrapper-script indirection closed, OI-010

- **Audited then closed a real, confirmed gap in oxford-command-center's `bash-guard.mjs`** (its
  Bash PreToolUse guard), following up on an unconfirmed hypothesis raised while checking that repo
  for anything resembling the same-night `ora-autonomy-gate.py` OI-007 indirection work. Confirmed:
  a two-step disk-persisted indirection (a git alias, or a wrapper script deferring its verb/path to
  a positional or shell variable) defeated all 7 blocked command classes, with neither step's own
  text containing the trigger pattern. Proved end-to-end (not just at the hook-logic level): a git
  alias genuinely staged a file via `add -A` in a disposable repo; a wrapper script genuinely
  deleted a `data/warehouse` test directory.
- **Fixed and landed** on `oxford-command-center` `main`, commit `60c45ed`, via isolated worktree +
  TDD + fast-forward merge. Resolves both indirection layers into one expanded text every existing
  check scans: git aliases via `git config --get` (plus inline `-c alias.X=value` one-shot
  overrides), and script content read through a widened set of invocation forms (sh/bash/zsh/dash/
  ksh, source/dot, stdin redirection, direct execution) with best-effort positional-parameter and
  simple-variable substitution.
- **Three rounds of independent adversarial review (3 parallel agents) found and fixed 4 real bugs**
  before landing, most severe first: (1) git global options (`-c`/`-C`/`--git-dir=`/`-p`/
  `--no-pager`) before the alias name broke candidate detection entirely; (2) a DoS-class
  exponential subprocess-spawn blowup from a plausible chained-alias config (4-8s+ stalls on every
  Bash call, fixed via a shared 16-lookup budget); (3) a DoS-class backtracking regex costing ~10s
  on a crafted payload (fixed via a length bound, applied consistently to 3 similarly-shaped
  regexes); (4) a quote-handling bug hiding a substituted value from the downstream commit-message
  quote-blanking logic. 59 new/updated tests including timing guards on both DoS fixes; full project
  suite 231 files/2783 tests green, typecheck 0, lint 0.
- **Accepted, documented limits (same architectural ceiling as OI-007)**: arbitrary shell constructs
  beyond simple literal variable assignment (command substitution, arithmetic, exported variables,
  control flow, >3-level nested wrappers, >64KB scripts) are not resolved — closing those for real
  needs the same shift OI-007 used (verify the actual outbound action/state), not another regex.
- **2 unrelated, pre-existing false positives found during review, deliberately not fixed here** to
  keep scope tight — tracked separately as `open-items-tracker.md#OI-011`.
- Full detail in `project_bash_guard_indirection_gap.md` and `open-items-tracker.md#OI-010` (closed).

## 2026-07-17 — ora-autonomy-gate.py hardening: override tokens, 8 matcher bypasses, OI-007 (indirection ceiling) fully closed

- **Override-token mechanism hardened.** The flat, mtime-only `hooks/overrides/<name>`
  sentinel was content-blind, session-blind, and git-trackable — a plain `git clone` of
  `~/.claude` could self-grant a live production-deploy window with no human involved
  (proven empirically: fresh clone → exit 0 for `netlify deploy --prod`, vs. an empty-dir
  control at exit 2). Replaced with session-scoped, severity-split, content-bound tokens
  under `hooks/sessions/<id>/overrides/` (gitignored, so structurally uncommittable).
  Landed on `ora-autonomy-gate.py`; a concurrent session independently reached the same
  root-cause conclusion and hardened `git-prepush-doctrine-gate.py` the same night — the
  two were later unified onto one shared `hooks/lib/override_tokens.py` contract to stop
  them drifting apart.
- **Adversarial review (3 rounds) found and fixed 8 real detection-matcher bypasses** in
  `ora-autonomy-gate.py`, independent of the token work above: dotless-domain email
  recipients, PowerShell `-T` prefix-binding, `cmd /c`/`powershell -Command` netlify
  indirection, Unicode homoglyphs and invisible characters (zero-width space, RTL
  override) defeating word-boundary matches, the mail script's Windows 8.3 short-name
  alias, `check_mcp`'s allow-by-default logic, and a foundational `sys.stdin` UTF-8
  decoding bug (the platform codepage was silently mojibaking non-ASCII payloads,
  undermining the Unicode fixes for any real, non-Python-escaped invocation). Test suite
  grew 44 → 65.
- **OI-007 (the value-indirection ceiling these matcher fixes couldn't close) fully
  closed**, in three parts:
  1. **Email side**: an outbound-action check inside `send-via-outlook.ps1` itself
     (gitignored, not git-tracked — see the 2026-07-17 entry above this one for detail).
     3 real bugs found and fixed by adversarial review before landing.
  2. **Netlify side, repo-local**: `website-canonical` PR #30, merged by Gabriel —
     `scripts/netlify-guard.js` + a `postinstall` shim patcher routing the netlify CLI
     through an authorization check. 2 real bugs found and fixed pre-merge (an
     exact-array-element flag-detection bypass letting `--prod=true`/`--prod-if-unlocked`
     through unauthorized; a postinstall patcher that silently exited 0 even when it
     patched nothing).
  3. **Netlify side, machine-wide follow-up**: `npx netlify` / a bare `netlify` command
     invoked from OUTSIDE `website-canonical` resolved an unguarded copy via npm's
     global/registry fallback (npx doesn't consult PATH the way a bare command does, so a
     simple PATH-shadowing wrapper wouldn't have closed this). Closed by deliberately
     installing netlify-cli globally (pinned to the repo's own 26.2.0) and patching its
     shims too — `hooks/bin/netlify-guard-global.js` + `maintenance/patch-global-netlify-shim.js`,
     landed on `~/.claude` main. Verified empirically that a local guarded install always
     wins over the global one in npx's own resolution order, so there is zero
     double-check / double-token-consumption risk between the two layers. Accepted limit
     (Gabriel-ratified): global npm installs have no postinstall-equivalent hook, so the
     patch needs a manual re-run after any future global reinstall/update — documented,
     not automated, given the underlying gap was already flagged low-priority.
- Full detail in `reference_autonomy_gate_override_mechanism.md`,
  `project_autonomy_gate_indirection_ceiling_followup.md`, and `open-items-tracker.md#OI-007`
  (now closed).

## 2026-07-17 — Session close-out: OI-006/008 completed, canonical tracker fully closed

Continuation of the Tenant DB remediation session. Closed the remainder of the OI-003–008 arc:

- **OI-006** completed: read all 5 primary executed lease documents via SharePoint for the 4
  turnovers + Soldier Trucking property conflict. Soldier Trucking confirmed via a Gabriel-signed
  Second Addendum (1100 Rarig Ave Unit G&H, not Zettler Rd 301 as Notion had it). Wrote and
  verified 6 Notion corrections.
- Ran down the 7 remaining WORKBOOK-NEWER rows + Masala Bazaar/Azad Shah dedup at Gabriel's
  follow-up request: 5 of 6 date corrections confirmed against primary lease/addendum documents;
  Pedro Ulate corrected on pattern-inference only (no lease document locatable — flagged as the
  one weaker-evidence write). Surfaced a second, distinct systematic bug: several Notion rows had
  the workbook's Escalation Date miscopied into Lease Expiration at the original March import.
- **OI-008 opened and closed same-day**: swept the full 79-pair Notion↔workbook reconciliable
  overlap for the Escalation-Date bug. Zero new instances found beyond the ones already fixed —
  confirms the defect was fully contained to the 7 originally-flagged rows.
- **OI-007** (owned by a concurrent session, not this one): independently verified rather than
  taken on faith — confirmed via `git fetch`/`pull` on `website-canonical` that PR #30 (netlify
  deploy guard) is genuinely merged at `b25a70d`, with real 113+149-line guard files, not a
  placeholder claim. Both Gate 1 (email) and Gate 2a (netlify) are closed.
- **Canonical tracker (`open-items-tracker.md`) now has zero open items** — OI-001 through
  OI-008 all CLOSED with evidence.
- Two shared-checkout commits landed this session using the `commit-provenance-guard` override
  after independently verifying (via `git diff --cached`) that the flagged co-edit was a
  recency-heuristic false positive, not real foreign content — the guard behaved as designed.
- Git state at close: `main` in sync with `origin/main`, nothing of this session's uncommitted or
  unpushed. Concurrent session `3fc20af9` remained active throughout with its own WIP, not
  touched.

**Workflow/systematization candidates surfaced, not yet actioned:**
- The commit-provenance-guard's recency-heuristic false-positive rate on `open-items-tracker.md`
  was 3-for-3 this session (every co-edit flag was already safely in `HEAD`). Worth checking
  whether the guard's TTL window is longer than it needs to be, or whether it should re-diff
  against `HEAD` before flagging instead of relying purely on a recency timestamp.
- OI-008's residual scope note (93 Notion Tenant DB rows with no workbook counterpart, never
  independently verified against primary leases) is real but was explicitly out of scope tonight
  — worth a deliberate decision on whether it's worth pursuing, not a silent drop.

## 2026-07-17 - psa-reconciliation reimported (Save-skill click confirmed)

Standalone MULTI-FILE reimport via Entry Point A. plugin_of => None. Repo commit 7e6d14d (frontmatter description trim 1274->956 for the 1024 import limit, ora-skill-text-audit follow-up). Only SKILL.md had drifted from cache; packaged clean (description 956/1024, 16-point QC OK, 5 forward-slash entries). Routed to the Cowork Save-skill button (multi-file: SKILL.md + INSTALLATION.md + 3 references/ - the desktop Settings path drops subfolder files). Gabriel confirmed the click. Post-install verify: all 5 cache files present, raw+normalized byte-match the repo. Ledger cleared; pending-reimport queue now empty.

## 2026-07-17 — OI-007 email-side fix: outbound-action check in send-via-outlook.ps1 (gitignored file, record here)

- Landed the email side of OI-007 ([open-items-tracker.md#OI-007](open-items-tracker.md#OI-007)):
  ora-autonomy-gate.py's Gate 1 detects an external recipient by parsing Bash command TEXT,
  which adversarial review proved is structurally blind to value indirection (a recipient
  built from a PowerShell variable/concatenation/file-read never appears as a literal
  substring, so Gate 1 never fires). Fix: an outbound-action check inside
  `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` itself, at the point
  where PowerShell has already resolved `$To`/`$Cc` to concrete values.
- **This file is gitignored (`scheduled-tasks/*/*`) — this log entry is the only durable
  record of the change.** No worktree, no commit, no diff history exists for it.
- New git-tracked pieces (landed via normal worktree process): `hooks/lib/email_send_tier.py`
  (shared `EXTERNAL_SEND` tier + recipient-binding, imported by BOTH Gate 1 and this new
  check so they cannot diverge), `hooks/lib/check_external_send.py` (the CLI the PowerShell
  script shells out to, validating against the same session-scoped, content-bound,
  single-use token contract). `ora-autonomy-gate.py` refactored to import from the shared
  module instead of its own inline copy.
- Added `-WhatIf` to send-via-outlook.ps1: performs every check but stops short of the real
  Outlook COM call, so the gating logic can be tested end-to-end without ever sending a
  real email. Exit code 5 = external recipient(s) not authorized (new).
- **Two real bugs found by adversarial review and fixed before this reached production:**
  1. A suffix-only regex (`-notmatch '@oxfordra\.net$'`) misclassified
     `attacker@evilhost.com@oxfordra.net` as internal — a complete bypass. Fixed: require
     exactly one `@` and an EXACT domain match, not a suffix match.
  2. Recipients were passed to `check_external_send.py` via a `--recipients` CLI argument;
     PowerShell's native-argument marshaling silently stripped an embedded double-quote
     before python ever saw it, so the checked value could differ from the actual send
     value. Fixed: recipients now travel one-per-line on stdin, never argument-parsed.
  3. (Found along the way, affects ALL token tiers not just this one) `override_tokens.py`
     opened token files as plain `utf-8`; PowerShell's default `Out-File`/`Set-Content`/`>`
     writes a UTF-8 BOM, corrupting the leading `scope` key and silently failing closed on
     a genuinely Gabriel-approved token. Fixed: `utf-8-sig`.
- Verified via 6+ `-WhatIf` scenarios against the LIVE file (internal-only, external+no-token,
  external+valid-token+consumed, no-session-id fail-closed, Cc-field checked, the Daily-Brief
  internal-To+Cc pattern with zero regression) plus the two bypass reproductions above,
  re-confirmed fixed post-patch.
- **Still open (deferred separately, not this entry's scope):** the netlify/Gate 2a side of
  OI-007 — postinstall-hook wrapper in website-canonical, Gabriel-ratified direction, not yet
  built (Invariant 2 gates any change to that repo's build tooling).

## 2026-07-17 - package-and-stage-skill v1.10 reimported (Save-skill click confirmed)

Standalone single-file reimport via Entry Point A. plugin_of => None (correctly standalone). Repo committed+pushed at fc93248 (plus release_plugin.py wrapper). Packaged clean (description 1019/1024, 1 forward-slash entry, exit 0); cache was stale (pre-v1.10) so real drift, packaged and staged. Gabriel confirmed the Save-skill click. Post-install verify: skills-plugin cache SKILL.md now v1.10, single file, raw+normalized byte-match the repo. Ledger entry cleared. Content: Step 0 plugin-member repo-path clarification (top-level dir, not plugins/<plugin>/skills/). Companion .claude fix pushed same pass: append-event-log.py BOM tolerance (620612d/ea0f9f1).

## 2026-07-17 - package-and-stage-skill v1.10 reimported (Save-skill click confirmed)

Standalone single-file reimport via Entry Point A. plugin_of => None (correctly standalone). Repo committed+pushed at fc93248 (plus release_plugin.py wrapper). Packaged clean (description 1019/1024, 1 forward-slash entry, exit 0); cache was stale (pre-v1.10) so real drift, packaged and staged. Gabriel confirmed the Save-skill click. Post-install verify: skills-plugin cache SKILL.md now v1.10, single file, raw+normalized byte-match the repo. Ledger entry cleared. Content: Step 0 plugin-member repo-path clarification (top-level dir, not plugins/<plugin>/skills/). Companion .claude fix pushed same pass: append-event-log.py BOM tolerance (620612d/ea0f9f1).

## 2026-07-17 — ora-cowork-heartbeat beacon recovery check

STILL STUCK. The Notion beacon page (`35c6ecd8-9e59-81d5-8d2c-d08002458b78`) still reads `Last heartbeat: 2026-07-15T21:57:21Z · Next expected: 2026-07-16T09:57:21Z` — identical to the known-stale baseline `2026-07-15T21:57:21Z`, and Notion's own as-of stamp on the fetch (`2026-07-15T21:57:30Z`) confirms the page has not been edited since. The LAMS registry confirms the task DID fire: `ora-cowork-heartbeat` shows `lastRunAt` `2026-07-17T10:46:53.712Z` with `lastScheduledFor` `2026-07-17T09:50:00.000Z` (the 05:50 ET slot, executed as an app-open catch-up), so this is "task fired but the Notion write still failed," not "task never ran" — the beacon is now ~37 hours stale against a 12-hour cadence and 16-hour watchdog threshold. The registry entry still carries no `approvedPermissions` array, consistent with the 2026-07-16 diagnosis; the alert email sent that day (~18:32 ET) recommended Gabriel check/re-approve the task's Notion permission grant in Cowork's Scheduled Tasks UI, and that grant does not appear to have been made.

## 2026-07-17 - ora-operations-extensions plugin reinstalled (README 7-skill correction)

Rebuilt ora-operations-extensions.plugin v0.1.2 from plugins/ora-operations-extensions/plugin-build.json via tools/build_plugin.py (9 entries OK, forward-slash paths, repo clean at HEAD a6a2677); no version bump - README-only fix. Gabriel confirmed the Save-skill click. Post-install verify against plugin cache rpm/plugin_01Sq7t7TEQEoa4G1asrLe8ms: README.md now reads "Seven institutional skills..." (was "Eight new skills..." pre-debt-management-exclusion); deal-retirement and submarket-spatial-analysis SKILL.md byte-match their canonical top-level repo copies (raw SHA256, no EOL-normalization needed) - both confirmed live via the plugin cache mirror, NOT the standalone skills-plugin shadow-copy path this fix exists to avoid. package-and-stage-skill Entry Point A (plugin-rebuild remedy).

## 2026-07-16 — Shipped commit-provenance guard; Tenant DB open items canonicalized (session close-out)

Two new hooks landed and pushed (`0b81232`, roster added to CLAUDE.md's Guards: line in
`de63351`): `commit-provenance-guard.py` + `commit-provenance-recorder.py` block a `git commit`
that would sweep another live session's uncommitted work into it. Fail-open, requires TWO
affirmative signals (foreign touched-set hit + live session within TTL), no lock ever held.
Gabriel explicitly rejected a hard claim-lock/mutex in favor of this shape — see
`feedback_fail_open_over_mutex_for_fleet_gates.md`, now the house default for future cross-session
coordination guards. Motivating incident: 4 concurrency collisions in one hour in this same
checkout, the worst being a staged MEMORY.md edit swept into another session's commit inside a
~30s window. Spec: `docs/superpowers/specs/2026-07-16-commit-provenance-guard-design.md`. Quick
reference for hitting the block: `reference_commit_provenance_guard.md`.

Separately, the Notion Tenant DB no-sync root-cause investigation's 4 residual action items moved
into `open-items-tracker.md` as OI-003 through OI-006 (build the workbook mirror from
`EXPORT_RentRoll`, add a real `Archived` property to the Tenant DB schema, dedup 2 stale Heritage
Pool Supply rows, confirm 4 tenant turnovers + the Soldier Trucking property conflict against
executed leases) — canonical descriptions live there now, `project_tenant_db_no_sync_rootcause.md`
carries only pointers. Also closed a stale claim in that file: `ora-master-workbook-ingest`'s
"should be 34 tabs" assertion was corrected to 49 earlier this session (`d5a1006`) and the memory
file had not caught up.

## 2026-07-16 — ora-skills: staged-frontmatter-validator review-fix shipped (5d33b99 -> ac51978)

Post-hoc gate + review of 3 commits the other concurrent session had already pushed to `ZeOoba/ora-skills` main (f46cfa8, 233349d, merge 5d33b99 — extracts `validate_skill_frontmatter` into a shared gate used by both packaging and a new `tools/hooks/pre-commit` staged-content check, closing the gap where a raw runtime-cache sync could skip frontmatter validation entirely). Gate green (19+32 tests, compile, hook syntax). Independent review (superpowers:requesting-code-review, isolated worktree at 5d33b99) returned "With fixes" — 2 Important, no Critical: (1) `validate_skill_frontmatter`'s per-file loop only exception-guarded the SKILL.md read, so an unreadable secondary staged file (e.g. merge-conflicted, no stage-0 index entry) propagated as a raw traceback instead of a clean finding; (2) `_staged_content()` omitted explicit `encoding='utf-8'` on its `subprocess.run` call, unlike every disk-based reader in the file, risking cp1252-locale mis-decode/crash on multi-byte UTF-8 staged content on Windows. Both fail-closed (no false-pass risk) — polish, not a safety gap.

Fixed both in an isolated worktree (`ora-skills-frontmatter-fix`, branch `fix-staged-frontmatter-review-followup` off 5d33b99) per the now-standard pattern: the shared checkout had live, unrelated concurrent WIP again (staged changes to build_plugin.py/pending_reimport.py on branch `plugin-reimport-routing`). Added exception handling around the loop's `_read(rel)` calls and explicit `encoding='utf-8', errors='replace'` to `_staged_content()`. 3 new tests (2 unit tests reproducing the unreadable-secondary-file case via the existing `read_text` injection point, 1 live-git-index test staging multi-byte UTF-8 content and confirming exact round-trip). 22/22 package_skills tests green, pending_reimport's 32 unaffected. Pushed via `git push origin fix-staged-frontmatter-review-followup:main` (clean fast-forward, re-verified immediately before push since state had moved), confirmed `origin/main` = ac51978, worktree + branch removed.

## 2026-07-17 — Built canonical open-items tracker (`open-items-tracker.md`), closing the dead-pointer incident that motivated it

Motivating incident: `oxford-cc-repo-health.md`'s "residual open items" line pointed at `session-context.md` as carrying "the live list" of two unresolved items (purge 2 dangling disabled LAMS entries; `ora-cam-reconciliation-annual` year-round-vs-seasonal timing). One sibling item (automation-health-monitor canonicalization) got a RESOLVED update logged inline in the same file same-day (2026-07-09); these two never did, and by 2026-07-16/17 `session-context.md` no longer mentioned either — the pointer had gone dead with nobody closing the loop. Both turned out to already be resolved (verified live, not assumed): `fleet-status.py` shows zero disabled LAMS entries fleet-wide; `ora-cam-reconciliation-annual`'s live cron `0 7 15 1 *` confirms the seasonal decision. Confirming that required a from-scratch investigation because the item text lived in two places (the source file's prose and the target file it pointed to) and only needed to rot in one for the trail to go cold.

Built `memory/open-items-tracker.md` as the single canonical home for open/residual/TODO items system-wide: one `### OI-NNN` row per item, OPEN/CLOSED status, opened/closed dates, evidence on closure, and an optional bounded `Auto-check` field (`registry_disabled_count` / `registry_field_equals`) that `memory-integrity-probe.py` can evaluate against live `fleet-status.py --json` output — no arbitrary code execution, just a closed vocabulary of registry comparisons. Migrated both closed items in as `OI-001`/`OI-002` with their closure evidence. `oxford-cc-repo-health.md`'s dead pointer now targets the tracker instead of `session-context.md`.

Extended `memory-integrity-probe.py` (report-only, wired into the existing daily `ora-health-guard` and twice-weekly `ora-cc-schematic-refresh` runs — no new scheduled task registered) with two checks: (a) any `open-items-tracker.md#OI-NNN` reference elsewhere in `memory/*.md` that doesn't resolve to a row in the tracker fails hard, same severity as an existing orphan-index-link finding; (b) any OPEN item whose `Auto-check` now matches gets a WARN nudging closure, without auto-closing anything. Extended `fleet-status.py --json` additively with `tasks` (per-task id/fleet/enabled/cron) and `disabled_by_fleet`, reused by the new checks rather than re-implementing registry discovery — kept the "GUIDs rotate, never hardcode, one source of truth" discipline intact.

Ratified pattern going forward: any file that wants to reference an open item points at `open-items-tracker.md#OI-NNN` and states nothing else about it — no paraphrase, no restated status. `ops_decision_log.md` stays a separate, narrower log (already-decided yes/no operational questions, not items with a mutable open→closed lifecycle) — checked its scope before deciding not to fold this into it.

## 2026-07-16 — ora-skills: shared-dep direction-aware reconciliation shipped (10f042f + follow-up)

Shipped 3 commits to `ZeOoba/ora-skills` main (`35cdbca..15f5497`): 7e6d14d (psa-reconciliation description trim), 10f042f (pending_reimport.py `shared-deps` subcommand + `candidates` advisory — direction-aware reconciliation of shared repo-root deps against the runtime cache: REPO-AHEAD/CACHE-AHEAD/DIVERGENT/UNKNOWN, closing the 2026-07-16 target-markets.json no-direction gap), and a same-day review-fix commit 15f5497.

Gate: 21+6 tests, compile clean, `shared-deps` sanity check all 5 target-markets.json consumers in sync. Independent local review (superpowers:requesting-code-review) returned "Ready to merge: With fixes" — 2 Important issues, no Critical/security/correctness bugs: (1) package-and-stage-skill step 2 didn't consult the new direction advisory before treating a shared-dep hash mismatch as reimport-needed, so a session could still reimport a CACHE-AHEAD dep and reproduce the incident the commit was meant to prevent; (2) the git-integration layer (shared_dep_report/_git_text/_git_blob_bytes/_file_history_hashes) had zero regression coverage, only the pure classifier did. Gabriel elected to fix both before push rather than ship with a known gap.

Mid-fix, discovered a second session (01a43b3e) actively editing the same two target files (package-and-stage-skill/SKILL.md, tools/pending_reimport.py, tools/test_pending_reimport.py) in the shared ora-skills checkout — a live build_plugin.py/plugin-packaging feature, unrelated to this fix. Isolated the review-fix work into a fresh git worktree off commit 10f042f (`git worktree add ../ora-skills-shipfix -b shipfix-review-followup 10f042f`) rather than risk clobbering their uncommitted WIP, since a worktree only pulls from committed history. Added package-and-stage-skill v1.8 (step 2 now requires checking `shared-deps` direction before repackaging a mismatched shared dep; CACHE-AHEAD/DIVERGENT stop for manual reconciliation) and 11 new SharedDepGitIntegration tests (real git repos, not just the pure classifier) to tools/test_pending_reimport.py (21->32 total). Pushed via `git push origin shipfix-review-followup:main` (clean fast-forward), verified `origin/main` = 15f5497, then removed the worktree and force-deleted the local branch (content already confirmed on origin).

Left the shared checkout's local `main` ref 1 commit behind origin deliberately — a `git pull`/merge there would touch the same 2 files the other session has uncommitted edits on, silently rewriting their working tree. That reconciliation is the other session's to do when it commits its own work.

No scheduled-task or Notion changes; tools/pending_reimport.py and package-and-stage-skill/SKILL.md are live on disk immediately (no Save-skill reimport needed for tooling).

## 2026-07-16 — membership-guard.ps1 sticky-fold-in bug fixed (code change, not just a state-file workaround)

Implemented the actual fix for the bug found earlier tonight (see the prior "ora-task-integrity-guard next-run-clean confirmed by live dry-run" entry this same day): `scheduled-tasks/ora-task-integrity-guard/membership-guard.ps1`'s once-daily `.lams.json` snapshot fold-in unconditionally trusted a stale `true` over the live direct registry scan, which had already correctly determined an id was gone.

**Change:** added `$liveLamsOk` tracking — set `true` when the live direct scan successfully parses at least one store this run. The snapshot fold-in's mutation of `$current` is now gated on `-not $liveLamsOk`: when the live scan succeeded, it is treated as closed-world for this run and the once-daily snapshot is skipped entirely for mutation purposes (still contributes to `$stores`/staleness reporting). Added a `snapshot_suppressed` boolean to the output JSON so this is directly observable per-run, matching a field name that had already appeared in the script's own docstring before I started (a second session was independently working the same fix — see reconciliation note below).

**Verified:** ran the patched script three times live. First run: `snapshot_suppressed:true`, confirming the live scan now wins; also surfaced a related latent issue — the snapshot fold-in's loop never had the direct-scan loop's one-time-task (`fireAt`) skip, so two one-time tasks (`ora-cam-data-backfill`, `ora-counsel-review-standard-positions`) had been wrongly baked into the persisted baseline as tracked recurring entries by earlier (pre-fix) runs; suppressing the fold-in surfaced them as a one-time false "disappeared" in that run's output (no real alarm fired — this was a manual diagnostic run, not the scheduled task). Second and third runs: fully clean (`disappeared`/`disabled`/`added` all empty, `snapshot_suppressed:true`, `enabled_total:20`) — baseline is self-consistent and stable going forward.

**Reconciliation note:** this file is edited concurrently by another active session that had already started the same fix (evidenced mid-edit by an unexplained `snapshot_suppressed` mention appearing in the docstring before I wrote it). Continued per explicit instruction rather than backing off. `membership-guard.ps1` (and its sibling `guard.ps1`) are gitignored (`.gitignore:57: /scheduled-tasks/*/*` opts in only each task's `SKILL.md`, not its engine scripts) — this code fix cannot be committed to `ora-claude-config` regardless of who authored it; only this log entry is.

## 2026-07-17 — psa-reconciliation description fix + skill-store hardening (Task 1-3)

- **What:** Trimmed psa-reconciliation's frontmatter description 1274→956 chars (all trigger classes preserved), committed `7e6d14d`. Extracted `package_skills.py`'s frontmatter checks into a shared `validate_skill_frontmatter(skill_dir) -> list[str]`, wired it into the existing (previously target-markets.json-only) `tools/hooks/pre-commit` via a new `--check-staged` CLI mode, TDD (9 new tests, 5 pre-existing green), committed `f46cfa8` on worktree branch `psa-skill-hardening`. Codified the raw-sync-is-provisional doctrine: `ora-skill-store-drift-check` (OneDrive `Documents\Claude\Scheduled\ora-skill-store-drift-check\SKILL.md` — NOT in the ora-skills git repo, a Cowork/LAMS scheduled-task home) bumped v1.9→v1.10, new step 2g cross-checks `event_log.md` for a confirmed Save-skill install before calling a hash-matched skill IN-SYNC; no match → REIMPORT-PENDING (index-unregistered). Mirrored the one-liner into `rules.md` §15 (dateless per policy).
- **Why:** psa-reconciliation's SKILL.md had been synced straight into the AppData runtime cache by an earlier Code-surface session, bypassing `tools/package_skills.py`'s frontmatter validation entirely — the cache read hash-IN-SYNC even though its description (1274 chars) would have been REJECTED by the sanctioned packager. Nothing at commit time caught the defect either, since `package_skills.py` only validates at package time.
- **Root-cause note:** the task brief assumed `ora-skill-store-drift-check`'s SKILL.md lived in the ora-skills git repo (framed as a pure Code-surface job); it doesn't — confirmed via Glob (negative) + filesystem cross-check per `reference_memory_scope_fragmentation.md`-adjacent doctrine (never trust a negative Glob alone). Edited the real Cowork/LAMS home directly (editing a scheduled task's SKILL.md is authoritative, per `reference_cc_scheduler_filepath_mechanism.md`), not the repo.
- **Concurrent-writer note:** session `01a43b3e` was live on the ora-skills MAIN checkout with uncommitted WIP in `tools/pending_reimport.py`/`tools/test_pending_reimport.py` (a hash-normalization refactor) for the full duration of this work. Per rules.md §14, isolated Tasks 2-3's ora-skills-repo work into worktree branch `psa-skill-hardening` (`.claude/worktrees/psa-skill-hardening`) rather than building on the shared checkout; Task 1's single-file commit was staged with an explicit path (never `git add -A`) directly on main since it touched no file the other session had modified. Worktree not yet merged back to main — pending local code review.

## 2026-07-16 — ora-task-integrity-guard next-run-clean confirmed by live dry-run; membership-guard.ps1 sticky-fold-in bug found + baseline corrected

To confirm tomorrow's (2026-07-17 12:54 ET) scheduled `ora-task-integrity-guard` run reports clean re: the ora-am-brief LAMS retirement, ran all of its STEP-3 alarm-surface engines live rather than asserting confidence: `guard.ps1`, `membership-guard.ps1`, `registry-membership-probe.py`, `emit-fleet-heartbeat.py`, and Step 2.75's `task-folder-registration-probe.py` (skipped script 3, `push-fleet-heartbeat.ps1` — a failure there is a STEP-4 note only per the guard's own doc, not an alarm condition, so not needed to confirm "clean").

**Findings, in order:**
1. `guard.ps1` first run: `restored:["ora-skill-text-audit"]` (unrelated to ora-am-brief — its LAMS-side SKILL.md was stale/missing and got repaired from a mirror, newest-wins, no data loss). Re-run immediately after: fully clean (`restored:[]`) — confirms it was a one-time, idempotent repair, not a recurring alarm source.
2. STEP 0.5 (today's CC/MCP fleet snapshot) had not actually been written today despite the guard's own `lastRunAt` showing a 17:00 UTC run — wrote `_state-history/2026-07-16.cc.json` by hand (fresh `list_scheduled_tasks` capture) to unblock `membership-guard.ps1`'s diff. Not deeply root-caused; flagged for awareness only.
3. **Real bug found:** `membership-guard.ps1`'s `.lams.json` fold-in (lines ~64-83) merges any snapshot-listed task into `$current` whenever the snapshot says `true`, even when a more authoritative/live source already says otherwise (`if (-not $current.ContainsKey($id) -or $en) { $current[$id] = $en }` — a "sticky-true" merge with no freshness check). Today's `2026-07-16.lams.json` was captured at 15:15 UTC by `automation-health-monitor`, **before** the evening's LAMS ora-am-brief retirement, so every manual run this session kept resurrecting `ora-am-brief: true` into `$current` and thus into the persisted `_state-history/membership-state.json` baseline — which would have caused a **false "disappeared" alarm** on tomorrow's real scheduled run once `automation-health-monitor`'s fresh 2026-07-17 snapshot correctly excludes it (diffing a correct absence against a wrongly-`true` prior baseline). Corrected `membership-state.json`'s `ora-am-brief` entry to `false` by hand (the disappeared/disabled checks only fire `if ($prev[$k])` was `true`, so `false` permanently and correctly excludes it from future alarm consideration — matching the ratified-retirement intent). Did not fix the underlying merge-logic defect in the script itself (out of scope for this confirmation pass) — flagged separately.
4. Final live-run tally, all STEP-3 alarm conditions clear: `guard.ps1` restored/backed_up/missing_everywhere empty; `membership-guard.ps1` disappeared/disabled/added/parse_miss empty; `registry-membership-probe.py` exit 0, no `[ACTION]`; `emit-fleet-heartbeat.py` exit 0; `task-folder-registration-probe.py` exit 0 on both fleets.

**Conclusion:** tomorrow's scheduled `ora-task-integrity-guard` run (2026-07-17, ~12:54 ET) is expected to output `GUARD OK cc=21 lams=20 | MODEL: ...` and send no alarm email, contingent on no new drift between now and then.

**Deferred:** the sticky-true merge bug in `membership-guard.ps1`'s `.lams.json` fold-in is a latent defect independent of this incident — any same-day retirement landing after `automation-health-monitor`'s daily ~11:05 ET snapshot capture and before the next day's refresh could reproduce this exact false-alarm setup. Worth a proper freshness-aware merge fix later.

## 2026-07-16 — oxfordra.net deploy: GA4/analytics wiring, image/CSS/focus optimization, 404 mobile-nav fix

Pushed and deployed 5 commits on `website-canonical` `main` to production (`https://oxfordra.net`): `670ef4d` (deno.lock build exclusion), `df2bc2a` (real GA4 Measurement ID wired into all 16 analytics snippets), `f45a735` (image recompression/responsive srcset/deferred CSS/focus management), `ad44f6d` (GA4/LinkedIn tracking added to remaining pages), `fe1e271` (404.html mobile-nav fix — restored keyboard/SR-reachable links via horizontal-scroll strip, replacing a broken `display:none` under 960px). The 5th commit was authored mid-session by a concurrent Claude Code session (co-authored by Claude Sonnet 5) — surfaced to Gabriel before push since it wasn't part of the original push request; Gabriel confirmed include-and-deploy-all-5.

`site-qc-reviewer` gate: APPROVE (zero confidential-term matches against the live `confidential-terms.json` roster, no broken links/assets, CSP preload-onload pattern confirmed non-breaking under current headers, 404 nav strip verified keyboard/SR-reachable). Deploy via `netlify deploy --build --prod` (MCP deploy-services-updater tool was permission-denied, used the documented CLI fallback); prod deploy only re-uploaded 2 changed files, confirming the concurrent session had already CLI-deployed most of this content live minutes earlier — the git push brought origin/main in sync with what was already running in production, closing the no-remote-backup gap flagged at session start. Post-verify: curl 200 on `/` and `/404.html`; page content confirmed live.

Non-blocking follow-ups flagged, not yet actioned: (1) convert the 5 pages using the preload-onload CSS pattern (index, about, contact, tenant-application, markets/index) to the safer `media="print"` swap already used elsewhere on the site; (2) LinkedIn Insight partner ID is still the placeholder `XXXXXXX` across all 16 analytics snippets.

## 2026-07-16 — CC/MCP residuals closed for LAMS ora-am-brief retirement; registry-membership-probe.py ratification bug fixed

Closed out the CC/MCP-surface residuals from the same-day LAMS ora-am-brief retirement (see prior entry "RATIFIED: LAMS ora-am-brief retired" and `memory/project_ora_am_brief_lams_retirement_blocked.md`, now RETIRED + VERIFIED). Concurrent-writer check clear (registry-membership.log latest entry complete, not mid-edit; `~/.claude` git tree clean at `242fd6f`).

1. **CC/MCP copy verified healthy** — `list_scheduled_tasks` on this CC surface: `ora-am-brief` `enabled:true`, cron `0 6 * * *`, path `~\.claude\scheduled-tasks\ora-am-brief\SKILL.md`.
2. **LAMS drop confirmed live (not just Cowork-view)** — `fleet-status.py` (reads both registries regardless of surface): `ora-am-brief` appears exactly once, cc-only, `on`; absent from lams.
3. **Roster refresh** — re-ran `registry-membership-probe.py`. It raised a false `[ACTION]` on the LAMS drop instead of auto-ratifying, despite this file's RATIFIED token being present and within the 14-day window. Root cause: `ratified_drops()` split event_log text on the literal `"\n### "` (three `#`), but `append-event-log.py` enforces and every real entry uses `"## "` (two `#`) headers — auto-ratification had never matched a real entry against this file's actual format. Fixed the split token to `"\n## "` (`~/.claude/maintenance/registry-membership-probe.py`); re-ran and directly unit-tested `ratified_drops()` against the live file — now correctly resolves `ora-am-brief` as ratified. Re-ran the probe again: `OK -- no actionable drift`, roster regenerated (cc 21 / lams 20 enabled recurring, session-context.md fleet block current).
4. **Ledgers updated** — `Claude_Workspace/00_Governance/outputs/2026-06-10_fleet-disposition-ledger.md` and `memory/oxford-cc-repo-health.md` both got a dated entry recording the retirement + this fix.
5. **Integrity guard check** — confirmed `ora-task-integrity-guard`'s STEP 1.5 runs this same probe daily; with the fix in place its next run will report the LAMS drop as an auto-ratified INFO (already consumed as this run's snapshot baseline), not a false alarm.

No registry-JSON edits. No re-registration of the LAMS copy (per do-NOT-re-register note). `~/.claude` is git-tracked to private `ZeOoba/ora-claude-config` — the probe fix is a plain code change, no deal terms touched.

## 2026-07-16 — event_log.md rolled over (3083 → 604 lines) via new rollover-event-log.py script

Live log had grown to 3083 lines (~3x the ~1000-line soft cap) with no dedicated rollover tool — the 2026-07-09 rollover was done by hand. Built `~/.claude/maintenance/rollover-event-log.py`, mirroring `append-event-log.py`'s mtime-guard + atomic-replace + pre-write backup + post-write verify pattern, since this is a structural single-writer edit on a file multiple concurrent sessions were actively appending to today. Dry-run first (`--dry-run`), confirmed the cut landed cleanly on a `## ` entry boundary, then ran for real.

Cut at "2026-07-16 — cc-audit-army generalized to repo-generic audits (Gabriel-directed)" — entries at and before that point (2483 lines) moved to `_archive/event_log_2026-07-16.md`; live log now 604 lines with a pointer at the bottom. No content altered — straight cut, consistent with the 2026-07-09 precedent. `memory-policy.md`'s rollover note updated to point at the new script. Known pre-existing defect not fixed in this pass (out of scope for a mechanical rollover): a single 2026-07-12 entry sits out of newest-first order just after the 2026-07-09 archive pointer (now inside the new archive file) — flagged, not reordered.

## 2026-07-16 — Master Workbook corrected: Heritage Pool Supply lease end → 2031-09-30 (DSOR was wrong)

Gabriel confirmed Heritage Pool Supply (7658 Fishel, Kristen Morgan, $8,540/mo) **exercised their
option to renew 5 years through 2031-09-30**. The live Master Workbook still carried
`2026-09-30 / "Expiring Soon"`. Notion's `SRS Distribution / Heritage Pool Supply` row already had
2031-09-30 — **Notion was right, the DSOR was wrong.** Authorized in-turn (Invariants 4 + 5).

- **Change:** `Master Tenant Rent Roll!I81` 2026-09-30 → 2031-09-30. One cell. Written via **Excel
  COM**, not openpyxl (openpyxl warns "Conditional Formatting extension is not supported and will
  be removed" on save — a lossy round-trip on Eric's model; `data_only=True`+save would flatten
  every formula across all 49 tabs).
- **Verified downstream:** `L81` Status Expiring Soon → Active · `L143` portfolio counters
  127A|7S|3E → **128A|6S|3E** · `I144` **portfolio WALT 2.36 → 2.45 yrs** (the understatement this
  fixes) · `EXPORT_RentRoll` I77/L77 propagated. Cell-level diff vs backup across all 49 tabs:
  **exactly 1 formula/literal change**; all other deltas are `TODAY()`-volatile recalcs.
- **Backup:** `Documents\Claude\_backups\Master Excel Template Company Wide -- Oxford_pre-HeritagePool-leaseend-fix_20260716.xlsx` (sha-verified identical pre-write).
- **⚠ Gotcha recorded:** the workbook is OneDrive-hosted → Excel **AutoSave persisted the cell
  before the error path could `Close($false)`**; the COM call then threw `RPC_E_CALL_REJECTED`
  *after* the write already landed. A COM error on this workbook does NOT imply rollback — always
  back up and diff to establish ground truth.
- **Doctrine:** DSOR ≠ infallible. This is the confirmed counterexample that forces the planned
  Tenant-DB mirror to be reconcile-and-escalate, never blind-overwrite — a naive workbook→Notion
  sync would have destroyed the correct 2031 date. See
  `memory/project_tenant_db_no_sync_rootcause.md` + spec
  `Claude_Workspace/01_Workspace/outputs/2026-07-16_TenantDB-Workbook-Mirror_Spec_v01.md`.
- **Still open:** dedup the two stale Notion Heritage Pool rows (2026-09-30) vs the correct SRS
  row — Notion untouched this session.

## 2026-07-16 — RATIFIED: LAMS ora-am-brief retired (migrated to CC/MCP)

RATIFIED drop — task id `ora-am-brief` (LAMS/Cowork fleet). Auto-ratify token present for registry-membership-probe.py.

Retired the LAMS/Cowork copy of `ora-am-brief` permanently, archive-first per register-scheduled-task v2.7 RETIRE doctrine. Reason: the Cowork sandbox has no local COM access, so the Outlook email leg (`send-via-outlook.ps1`) structurally could not send — confirmed by the 2026-07-16 edition never sending despite 7/13–7/15 sending fine. Gabriel-approved migration to CC/MCP on 2026-07-16; a CC/MCP registration (same content, same cron `0 6 * * *`, three surface adaptations in its own frontmatter) is live and independently confirmed at `~/.claude/scheduled-tasks/ora-am-brief/SKILL.md`. Both fleets had been double-firing daily at 06:00 ET; this retirement removes the LAMS duplicate.

Actions (in order): (1) concurrent-writer check clear (no live sibling session; registry-membership.log latest entry not mid-edit); (2) disabled LAMS entry via `update_scheduled_task enabled:false`; (3) moved folder to `Documents\Claude\Scheduled\_archive_2026-07-16_retired-to-ccmcp\ora-am-brief\` — verified SKILL.md present at new path, ENOENT at old path; (4) deleted LAMS registry entry via `delete_scheduled_task` (9 run sessions archived). CC/MCP copy untouched (SKILL.md intact, 217 lines). No registry-JSON edits anywhere. Producer-script check clear — `open_sessions_probe.py` (Block C.5.6) co-owned by `ora-open-sessions-board` and the CC `ora-am-brief` copy, so no orphaning. `session-context.md` do-NOT-re-register roster updated with the LAMS-copy retirement note (CC/MCP copy explicitly excluded — must stay enabled).

## 2026-07-16 — Leaked Netlify MCP proxy token found in oxford-site git repair, purged, rotated — CLOSED

Follow-on from repairing `Claude_Workspace/01_Workspace/oxford-site`'s corrupted `.git` (missing
`refs/` entirely). During the mandated "second look" pass before retiring the checkout, found a
live-looking Netlify MCP proxy token (JWE-encrypted, tied to production site `95ac0a0f-a84d-4400-
b919-b8d7a8526646`) hardcoded in plaintext in `run-deploy.bat`, already sitting in the recovery-
baseline commit. Never pushed anywhere (no remote configured on this checkout), so exposure was
local-only throughout.

Remediation, in two passes:
1. Redacted the working file; rewrote history to drop the token from the root commit (`c886245`),
   using a transport-level `git clone --no-local` after discovering in-place `git gc`/`repack -ad`
   left the blob recoverable in the pack — verified zero matches across every object afterward.
2. A secondary sweep of the preserved forensic archive (`.git-corrupted-20260716/`, ~26,800 objects,
   scanned for a full secret-pattern set) caught that the archive itself — kept "for forensics" —
   was still tracked in the live repo's history, meaning the first purge wasn't actually complete
   (same token blob, still technically recoverable). Untracked it from git (kept on disk, gitignored;
   also independently preserved in a non-OneDrive backup), repeated the clean-clone purge (pack
   268,746 KB → 9,917 KB), reverified zero hits. Also found 2 false positives (dotenv npm package's
   own README placeholder key text, bundled in an old committed `node_modules` snapshot) — confirmed
   not real. Final state: `main` @ `8c97652`, no remote, no reflog, no dangling objects.

**Token rotated same day (Gabriel):** revoked "Netlify MCP" under Authorized Applications
(app.netlify.com → User settings → OAuth), reconnected the Netlify MCP connector
(`a66aaa4a-ffcd-4066-b2af-79c4ce807809`). Verified live post-reconnect via the connector itself
(`get-user` → ggoldberg@oxfordra.net; `get-project` on `95ac0a0f…` → deploy state `current`/`ready`).
No other on-disk reference to the old token found (searched `~/.claude` JSON configs). Thread closed.

## 2026-07-16 — Correction: Monthly Checklist location (Gabriel-supplied)

Gabriel corrected the last open item from the EOD Ledger remediation: the Monthly Checklist is not a separate/unreachable file — it's a sheet (`Monthly Checklist`, plus an `EXPORT_MonthlyChecklist` mirror tab) inside the same Master Workbook already confirmed locally reachable at `...\eric spreadsheets\Master Excel Template Company Wide -- Oxford.xlsx`. Verified directly: both tabs exist (`get_workbook_metadata`), and `Monthly Checklist` has real, current content (a WE PAY / WE RECEIVE loan-payment matrix by property/counterparty, not a stale placeholder). Updated `ora-pm-ledger` SKILL.md's DSOR-reachability note (previously wrong, written earlier today) to reflect this — future runs should read the sheet directly rather than declaring a COVERAGE GAP or citing the stale standalone "Monthly Checklist Accounting+Operations.xlsx" at the OneDrive root.

Follow-on not yet done (flagging, not building unasked): `ora-master-workbook-ingest`'s source-of-truth tab list doesn't currently include `Monthly Checklist` — since ora-pm-ledger reads it live daily anyway, this is a nice-to-have for the weekly mirror/dashboard, not a blocking gap.

All 3 EOD Ledger decision items plus both DSOR/Monthly-Checklist coverage-gap items are now closed. Only the LAMS ora-am-brief retirement handoff remains open (user started task_98448323 in a separate session).

## 2026-07-16 (evening) — Full re-verification of all 15 original drift-check findings: negative result, nothing open

Prompted by a direct request to check whether the "other 7" (no-action/CRLF-FP group) tied back to anything still open, after the daily-brief saga showed "closed" can hide an unpushed commit or un-clicked install. Re-checked all 15, not just 7.

- **Push check:** all 9 relevant commits (batch1 x4: `e605d40`/`1474349`/`fd030b6`/register-scheduled-task's `d5ca189`; batch2 x4 installs: `a66612a`/`e207b7f`/`9aa26d4`/`d0c0cb1`; parcel-data-recovery merge `943f16c`; register-scheduled-task v2.7 `98c52d2`) confirmed via `git merge-base --is-ancestor <hash> origin/main` — all on origin/main, no unpushed-commit gaps.
- **Repo↔cache hash check (EOL-normalized), all 15:** 14/15 clean on first pass. `oxford-cc-strategic-audit` initially read DRIFTED — investigated rather than reported as a new finding: cache carries 228 trailing NUL bytes (the documented platform-upload padding artifact, ora-skill-store-drift-check step 2b), which the first-pass check didn't strip. Re-hashed after stripping `\r` and `\000` from both sides — exact match (`6737ba37...`). Not real drift; a gap in this session's own check, not the skill store's.

Nothing from the original 2026-07-16 15-finding drift-check (Notion comment `39f6ecd8-9e59-814b-83d3-001d8db86fff`) ties back to anything still open.

## 2026-07-16 — EOD Ledger decision items executed (Gabriel's picks: all three "Recommended" options)

Following up the earlier remediation pass, Gabriel chose all three recommended options and asked for them to be built.

**1. ora-am-brief moved to CC/MCP fleet.** Registered `ora-am-brief` on CC/MCP (`0 6 * * *`, taskId `ora-am-brief`, file `C:\Users\Owner\.claude\scheduled-tasks\ora-am-brief\SKILL.md`) — content carried over from the LAMS spec verbatim except: (a) Block B now cites the Command Center alerts engine for critical dates instead of independently re-deriving from Notion (implements decision #2 below); (b) Block D drops the Cowork-only `mcp__cowork__update_artifact` step and reads the Master Workbook at its confirmed local path (`...\eric spreadsheets\Master Excel Template Company Wide -- Oxford.xlsx`, same path `ora-master-workbook-ingest` already uses) instead of an assumed mount; (c) NON-MUTATION GUARANTEE's output list drops the Cowork artifact reference. `fleet-status.py` confirms CC/MCP 21->22. Retiring the superseded LAMS registration was handed off via `spawn_task` (task_98448323, "Retire LAMS ora-am-brief scheduled task") since this session can register on CC/MCP but can't write to the LAMS registry — needs a Cowork-side session to archive-first retire it and re-verify via its own `list_scheduled_tasks`.

**2. Command Center ruled authoritative for critical dates.** Implemented directly in the new CC/MCP `ora-am-brief`'s Block B as an explicit OVERRIDE to the shared `daily-brief` skill's Section 4b/4c: read the Command Center Daily Brief / `portfolio.json` (DSOR-lineage) rather than independently deriving lease/debt dates from a live Notion read; record a COVERAGE GAP rather than falling back to independent computation if Command Center's data is unavailable that morning.

**3. HubSpot renewal-signal fix.** Edited the shared `daily-brief` SKILL.md Section 4b directly (now v2.7) — replaced the "no HubSpot renewal activity" check (root cause: all ~50-56 renewal deals permanently parked at HubSpot's default stage 1, so the signal was inert for every tenant) with a Notion-native check: renewal activity now = `Renewal Option Terms` non-empty OR `Lease Extension / Amendment Log` has an entry OR `Next Renewal Action Date`/`Renewal Offer Date` is set. This is the actual producer of the "no renewal signal" defect the EOD Ledger flagged — HubSpot's dealstage itself was never touched (that's a separate, not-yet-authorized fix if Gabriel later wants HubSpot's own pipeline made meaningful).

**Bonus finding while investigating #1 (Block D adaptation):** the ORA Master Workbook IS present as a local file on this machine (`...\eric spreadsheets\Master Excel Template Company Wide -- Oxford.xlsx`, OneDrive-synced, `lastModifiedDateTime` 2026-07-15) — the same path `ora-master-workbook-ingest` already reads directly via Desktop Commander. The original EOD Ledger's "DSOR not locally resolvable" claim was a miss, not a structural gap: neither the local path nor `sharepoint_search` (both confirmed reachable) were tried before declaring the gap. Added a DSOR-reachability check to `ora-pm-ledger` SKILL.md's C.2 mandated-source discipline documenting both paths, so future runs try them before recording the gap. The **Monthly Checklist** (31/59-item workbook) genuinely remains unreachable — confirmed absent from both the local `eric spreadsheets` folder and SharePoint search by name/category; only a stale (2026-04-17) copy exists at the OneDrive root. That specific gap stands; recommend asking Gabriel directly where the live version lives.

Net: 2 of 3 decision items fully closed this session (CC/MCP registration live, daily-brief HubSpot fix live); LAMS-side retirement is the one open handoff (chip pending, not yet actioned).

## 2026-07-16 (evening) — daily-brief v2.7 INSTALLED — Gabriel's Save-skill click confirmed, ledger cleared

Post-install verify: cache `SKILL.md` raw SHA256 exact match to repo (`129c50d5...`, no EOL divergence this import), cache `target-markets.json` raw SHA256 exact match to repo root (`f06e71e9...`), v2.7 version marker present in cache, cache mtime 2026-07-16 18:51 (consistent with the click). `python tools/pending_reimport.py clear daily-brief` run — ledger entry cleared, `_staging/PENDING_REIMPORT.md` deleted (documented behavior: file is removed once empty, not an error despite the script's exit 1). Runtime and repo both at v2.7 (commit `936f9f4`, on origin/main).

No deploys, no scheduled-task changes, no email.

## 2026-07-16 (evening) — daily-brief v2.7 packaged + staged for reimport (Entry point A)

Repo commit `936f9f4` (Notion-vs-Workbook lease-expiration cross-check, Patch 10) pushed to origin/main this session. Packaged via `tools/package_skills.py _staging/2026-07-16_daily-brief-v2.7 daily-brief` — 2 entries OK (SKILL.md + injected target-markets.json), description 378/1024 chars. Shared-dep pre-check: packaged `target-markets.json` SHA256 `f06e71e9...` matches repo-root source exactly — no drift. Multi-file skill → routed to Cowork **Save skill** button per multi-file doctrine (desktop Settings→Capabilities silently drops bundled files). Runtime cache stays at pre-v2.7 until Gabriel's click; `_staging/PENDING_REIMPORT.md` entry for daily-brief (commit `936f9f4`) stays open until then — clear only after a confirmed post-install hash-verify.

No deploys, no scheduled-task changes, no email.

## 2026-07-16 — ora-am-brief follow-ups (4) + doctrine-probe gains a LAMS-fleet regression guard

Closed the four items flagged after the Block A callout fix earlier today.

**#1 — callout hardened from prohibition to literal template.** A prohibition ("must NOT narrate SOFR freshness") is weaker under generative pressure than a fixed skeleton. A.3 now carries a CALLOUT TEMPLATE: the callout is assembled by concatenating only the true clauses from an enumerated menu (UST-derived / BBB-stale / FedWatch / 30Y-FRM / overnight-SOFR-unobtainable). There is deliberately NO menu clause for the SOFR 30/90/180-day averages or Index, so the model has no slot to narrate them. The earlier hard rule remains as backstop.

**#2 — §7 Sources line patched (live Notion, ephemeral).** Removed the stale "carried forward from 2026-07-15 patch" phrasing; now states overnight SOFR eff. 07-15, averages/Index eff. 07-16 via the local direct pull. Self-regenerates tomorrow under the new rule; this was a same-day cosmetic cleanup.

**#3 — version pin REMOVED, not bumped.** ora-am-brief cited "daily-brief skill v2.5" in two places (frontmatter desc + Block B instruction); installed is v2.7. Bumping just resets the rot clock (feedback_prompt_current_state_prose.md). The pin isn't load-bearing — the skill resolves by name — so both references now say "the installed daily-brief skill" with no version. Stops the rot permanently.

**#4 — NEW doctrine-probe Check 12 (regression guard) + a fleet-coverage finding.** FINDING: doctrine-integrity-probe.py's scheduled-task scanning uses `CLAUDE_DIR/scheduled-tasks` — the CC/MCP fleet ONLY. The entire LAMS/Cowork fleet (OneDrive\Documents\Claude\Scheduled\, 20 tasks incl. ora-am-brief) is invisible to every check in the probe. So the casually-proposed "grep the scheduled SKILL.mds for cross-task narration" would have scanned the wrong fleet and never seen the file it was meant to guard. Gabriel chose (via AskUserQuestion) the narrow regression guard over a general LAMS-wide heuristic (no machine-readable field-ownership map → the general version is keyword-noisy). Check 12: reads ora-am-brief's known OneDrive path (fail-open, WARN-only, live_mode only) and asserts 3 fix sentinels are present (CALLOUT TEMPLATE header, the "deliberately NO clause" guarantee, CALLOUT SCOPE hard rule). It is a fix-PRESENCE check, not an anti-pattern grep — the hard rule legitimately QUOTES the forbidden phrases, so a co-occurrence scan would flag the fix itself. TDD: 6-assertion unit test (red→green), py_compile clean, full probe run exit 0, my check prints "intact (3/3)", the one WARN is the pre-existing benign confidential-term self-check. NOT committed (steady-state uncommitted drift in ~/.claude; user did not ask to commit).

**Open (not built, by decision):** general cross-task-narration detection across the LAMS fleet — deferred; would need a LAMS scan root (cloud/fail-open) + a field-ownership map to avoid false WARNs across 20 tasks. Check 12 can be generalized into it later if warranted.


## 2026-07-13 — ora-lease-expiration-brief: re-hit the confirmed DC PowerShell $var-stripping bug; closing note corrected

During the ORA Lease Expiration Brief scheduled-task run, the Outlook COM send (`send-via-outlook.ps1`) was first attempted with an inline `start_process` command of the form `$body = Get-Content ...; & send-via-outlook.ps1 ... -Body $body -Html` — this is exactly the failure mode already logged in [reference_desktop_commander_powershell_variable_stripping.md](reference_desktop_commander_powershell_variable_stripping.md) (confirmed engine-wide 2026-07-12): `$body` was silently stripped from the `-Command` string, producing a `The term '=' is not recognized` parse error immediately followed by a real (malformed, ~5-byte) send to ggoldberg@oxfordra.net. A second attempt wrote a `.ps1` file but hit the sibling nested-encoding issue from an em dash in an inline literal (`reference_desktop_commander_nested_quote_mangling.md`'s "quoting layer" family). Root-caused and fixed on the third attempt by writing the body to a file directly (`write_file`) and invoking `send-via-outlook.ps1 -BodyFile ... -BodyFormat html` from a `.ps1` script file (no inline `$var` in the `-Command` string) — this matches both the already-documented DC workaround and the pre-existing, actively-maintained doctrine in `_shared/README-SEND-PATTERN.md` (updated 2026-06-15) and `_shared/EMAIL_DELIVERY.md`, which already mandate exactly this file-based `-BodyFile` pattern fleet-wide.

**Correction to my own initial framing:** the session's closing note characterized "prefer `-BodyFile` over inline `-Body $var`" as a new workflow-optimization recommendation. That was wrong — it's not a gap to fix, it's an existing, correctly-designed doctrine I failed to follow on the first two attempts. The actual miss was process discipline: not checking `reference_desktop_commander_powershell_variable_stripping.md` / `_shared/README-SEND-PATTERN.md` before building the send command, despite this bug being confirmed engine-wide the day before (2026-07-12). Logging here per Calibrate convention so the next scheduled-task-authoring or ad-hoc-send session checks the existing reference first rather than rediscovering it a fourth time.

No doctrine change made (none needed) — this is a "read the existing reference first" miss, not a doctrine gap.

---

*Entries at and before “2026-07-16 — ora-am-brief follow-ups (4) + doctrine-probe gains a LAMS-fleet regression guard” rolled over 2026-07-18 to [_archive/event_log_2026-07-18.md](_archive/event_log_2026-07-18.md) per memory-policy.md's rollover rule.*
