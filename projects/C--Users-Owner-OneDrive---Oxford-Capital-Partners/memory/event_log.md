---
name: event_log
description: "ORA append-only event log — system changes, deal milestones, decisions. Newest first. This is the ONLY append-wall; living docs are overwritten to current state and point here for history."
metadata: 
  node_type: memory
  type: log
  originSessionId: 8ffab475-017d-4acd-9f70-f4496936d089
  modified: 2026-08-22T22:08:49.565Z
---

# ORA Event Log (append-only, newest first)

Renamed/expanded 2026-06-03 from reference_optimization_log.md. Living docs (firm/projects/tech/etc.) hold current state; their history accumulates HERE.

## 2026-08-22 -- Save-skill clicks confirmed: package-and-stage-skill v1.25, acquisition-underwriting v4.13

Two confirmed platform installs from the refi-rate-rebase session. Logged per package-and-stage-skill
step 7 (the click, not merely the repo commit).

- **package-and-stage-skill v1.25** (commit 8f00bb4). CONFIRMED, two independent signals:
  (i) a live `ListSkills` account call returns the skill enabled with a description string ending
  "Commit by pathspec. v1.25" -- the platform's own copy, not the cache; (ii) runtime-cache directory
  CreationTime = 2026-08-22 17:58:05, after the 17:55 commit. A mirror-sync overwrite rewrites bytes in
  place and leaves CreationTime untouched, so a moved CreationTime is a real teardown/recreate.
  PENDING_REIMPORT line cleared.

- **acquisition-underwriting v4.13** (commit 5b1f319, refi rate default 7.00% -> 6.50%). CONFIRMED on
  CreationTime alone: cache directory CreationTime = 2026-08-22 17:50:08, after the 17:45:01 commit, and
  the repo state at that moment was v4.13. ListSkills is NOT corroborating here -- this skill's
  description carries no version token, so the account call cannot discriminate versions for it.
  CAVEAT, recorded rather than smoothed over: no pre-click CreationTime baseline was captured during
  this session's step 2, which the v1.23 rule requires unconditionally. The 17:50:08 reading is
  therefore compared against an inferred prior state, not a measured one. Evidence is good but one
  notch weaker than the doctrine calls for.
  PENDING_REIMPORT line NOT cleared -- see below.

- **acquisition-underwriting ledger line deliberately left pending.** The current pending line is for
  commit 8728924 (Kinsman Blvd doctrine bundle, v4.14) written at 22:01Z by a concurrent session, not
  for v4.13. v4.14 has not been installed: the cache CreationTime has not moved since 17:50:08. Clearing
  the line would mark an uninstalled version as installed.

- **DUPLICATE REGISTRATION FLAGGED (needs Gabriel).** `ListSkills` returns TWO enabled entries named
  `acquisition-underwriting`, ids `skill_012DJmjQBkLtQtfu6We1owXx` and `skill_01Ukeyw2g9c99nVdsSpnTiyr`,
  with byte-identical descriptions. `plugin_of('acquisition-underwriting')` returns None, so this is not
  the known plugin-shadow-copy case (step 0). Two registrations of the same skill name means an
  ambiguous resolution at invocation time and an install that may land on only one of them. A session
  cannot delete a registry entry; this needs a manual removal in Settings -> Capabilities.

- Local main.log (`%LOCALAPPDATA%\Claude\Logs\main.log`) was live (mtime 18:07:36) but its last 400 lines
  carried no `[SkillsPlugin]` entries, so the v1.24 exact-second correlation was unavailable for either
  skill. CreationTime was the operative discriminator, as v1.22/v1.23 anticipate.

## 2026-08-22 — v2.10-class surface gap closed at DISPATCH time; session-context xref probe built; retire-pending register guards the in-flight LAMS retirement

Implemented the four optimizations Gabriel carried forward from the second `ora-passed-deal-tracker` incident. Session surface: cloud-sandbox Cowork (device bridge, no native app process) — `list_scheduled_tasks` / `create_` / `update_` / `delete_scheduled_task` confirmed ABSENT by tool-registry search. No registry write was attempted from here, and none of the work below required one.

**1. `register-scheduled-task` v2.13 -> v2.14 — RULE 3 (pre-flight surface assertion) + RULE 4 (dispatch-time surface routing).** v2.10 documented the cloud-vs-native surface gap correctly; the gap recurred anyway on the same id because nothing at dispatch time read the note and the receiving session could only discover it mid-pass. RULE 3 makes the assertion the first action of any registration/update/pause/retire pass — prove the surface by tool-registry search, never by calling a tool (a test call on `delete_scheduled_task` is a delete), and never split an ordered pass across the discovery. RULE 4 moves the decision one step earlier still, to whoever writes the brief: a LAMS registry WRITE is handed to "a native on-device Cowork session" by name, never a bare "Cowork session"; READS stay exempt (`fleet-status.py` reads both registries from any surface). QC gate updated. Also added a RETIRE bullet and a bounded-pause carve-out bullet for the retire-pending register (item 3).

**2. `fleet-advisory-remediation` v1.2 -> v1.3 — the dispatch step itself.** Step 6 was the actual dispatch site and said "flag it for a Cowork-side session", which a cloud sandbox satisfies. It now names the native on-device surface literally, requires RULE 3's assertion as the brief's step 1, and requires an ordered multi-step write (archive-first-delete-second) to be flagged as ONE indivisible pass. Matching Outputs + Boundaries bullets. Also corrected the frontmatter version, which read v1.1 while the changelog was at v1.2.

**3. Retire-pending register + `pause-resume-guard.py` check — the live hazard.** `enabled:false` is a pause, not a retirement: the LAMS `ora-passed-deal-tracker` entry is disabled only as a side effect of the stalled 08-21 bulk resume, so every future fleet-wide resume re-arms it until the registration is dropped. New `maintenance/_state/retire-pending.json` records ratified-but-unexecuted retirements; `pause-resume-guard.py` (native, off-fleet, every 6h) now alarms when a listed id is found `enabled:true` on its named fleet. Fail-open by construction (absent/unreadable/malformed register = no findings), fleet-scoped so the canonical CC copy is never flagged, per-key alarm bookkeeping namespaced under `_retirePending` so it cannot collide with fleet-ratio state. Six new tests; full suite green (14/14). Verified against the live registries read-only: cc=40, lams=30, LAMS copy `enabled:false` (no finding), CC copy `enabled:true` (correctly not flagged).

**State correction found mid-session:** the LAMS archive step HAS since been executed — `Documents\Claude\Scheduled\ora-passed-deal-tracker\` is gone and the archived copy is at `_archive_2026-08-22_retired-to-ccmcp\ora-passed-deal-tracker\SKILL.md`. The registration therefore now carries a DANGLING filePath. The retire-pending entry records that half-executed state and the remaining step. **Step 2 of 2 is still open and still requires a native on-device Cowork session** (`delete_scheduled_task` takes no fleet parameter and resolves session-local — the same call from Claude Code would delete the LIVE CC copy).

**4. `session-context-xref-probe.py` — new, wired as the 7th engine of `ora-doctrine-integrity-guard` (v1.4 -> v1.5).** Validates that session-context.md's own pointers resolve: a dated `event_log.md` citation must match a real entry heading (live log OR a rolled-over `memory/_archive/` chunk); a backticked file citation must exist on disk across the memory dir, `~/.claude` + its usual subdirs, `ora-skills`, the LAMS store, and the two OneDrive homes (extensible via `_state/xref-extra-roots.json`). Deliberately narrow — elided paths, prose, and call syntax are skipped, because a false `[XREF-MISSING]` in a daily guard costs more than a missed one. `[SKIP]` is fail-open; a missing/empty session-context.md stays `backup-session-context.py`'s alarm. 11 tests, all pass.

**Its first live run found two genuine dangling references:** (a) `reference_tech.md` — no such file has ever existed; the file is `tech.md`. FIXED in session-context.md. (b) `outreach-ratification.json` — a FALSE positive, the file is real but lives under the OneDrive business folder; that root was added rather than reported. The probe now runs clean: 7 dated event_log citations and 18 file citations validated.

**Not done here, deliberately:** nothing was committed in `~/.claude` or `ora-skills` — both had another session's uncommitted work in flight (Automation Audit Rev 18 remediation, and the M18 eval-harness batch), and the single-writer discipline says land these separately. The two edited skills also need a `package-and-stage-skill` reimport to reach the runtime cache; until then `repo_first_check.py` will correctly report them REPO-AHEAD, which is normal and not an alarm.

## 2026-08-22 — ORA Doctrine Patch Bundle v01 applied (3700 Kinsman Blvd origin) — `8728924`

Gabriel pasted a 4-patch doctrine bundle from the 3700 Kinsman Blvd (Madison WI) FULL underwrite. Verified base SHA256 for all four target files before editing (bundle's own integrity rule); 3 of 4 matched and were applied as written, 1 was stale and re-anchored.

**Applied to `ora-skills` (commit `8728924`, main):**
- `acquisition-underwriting/SKILL.md` v4.13→v4.14 — STAGE -1 item 8 (zoning-GIS + assessed-value intake via `ora-flood-zoning-dd`/`ora-millage-lookup`), QC Gate floor-test-block extension, corrupted/non-numeric doctrine-constant halt rule, December-back-test drift-sweep hook.
- `acquisition-proposal-generation/SKILL.md` v3.1→v3.2 — walk-price QC gate (refuse to produce a proposal above the ORA walk price).
- `market-monitor/SKILL.md` v1.4→v1.5 — new DOCTRINE-DRIFT REPORT section, run-triggered/reporting-only.
- `loi-generation/SKILL.md` v1.7→v1.8 — walk-price required-input + hard-fail QC Gate item, **re-anchored as item 23** (bundle assumed the gate had 16 items; two same-day commits, `3c477f5` + `0eb8f5f`, had already expanded it to 22 for an unrelated reason before this session started — stated base hash `7bb9b372ed56` did not match the live file `2f179af…`, correctly caught by the bundle's own refuse-if-hash-mismatches rule).

Skipped per the bundle's own instruction: item 1D (single-tenant Stage 2 row 6 scoring branch) — would change a scorecard weight, held for the December back-test.

**Findings during application (both fixed pre-commit):**
- Independent review caught a fabricated "true" Louisville rent figure ($4.90–$6.00) in the bundle's own corrupted-constant incident narrative — the file's actual on-disk Louisville constant is $3.90–$5.00. Corrected to match reality before commit; ironic given the bullet's own subject is "don't infer, read the on-disk file."
- Pre-commit skill-frontmatter gate blocked on `acquisition-proposal-generation`'s description exceeding the 1024-char platform limit after the version-tag edit — trimmed rather than overridden (`--no-verify` not used).

Landed via `isolated-commit` (claimed slug `ora-skills-doctrine-patch-v01`, pathspec-scoped stage, two independent-review passes — second after post-review fixes, per the skill's re-review-don't-reuse rule). Not pushed to remote (no explicit push instruction this session). Post-commit hook recorded all 4 skills to `_staging/PENDING_REIMPORT.md` — Cowork/LAMS runtime copies need repackage+reinstall via `package-and-stage-skill` before these changes are live there; the Code-surface repo copies are authoritative as of this commit.

Not patchable from this session (per bundle): the skill-injection constant-corruption defect itself is an Anthropic-side platform issue (bug report shipped separately, outside this repo); `verified-deal-recon`'s absence from the Cowork synced skill set remains unresolved (Patch 1A re-routed around it into STAGE -1, but the routing-default-resolves-to-nothing gap is general, not closed).

## 2026-08-22 — Pointer: the M18 eval-harness event_log entry landed via commit `b26b7f1`, mislabeled

The preceding "M18 eval-harness YoC/DSCR floor-constant parser" entry above was appended via `append-event-log.py` (collision-safe at the file level) while 3 other sessions' entries were also sitting uncommitted in the same backlog. Before this session could isolate and commit its own entry (per [[reference_event_log_uncommitted_backlog]]), a concurrent session committed the full accumulated backlog first, at `b26b7f1` -- whose message is `"memory: document debt-scoring oxfordNoi basis is conservative, not proven correct"` and says nothing about the M18 fix. Verified byte-for-byte that the M18 entry landed intact and unaltered inside that commit; nothing was lost, nothing further needed committing. Logging this pointer so anyone searching commit history by message for the M18/diff_verdict.py change finds `b26b7f1`, not a nonexistent commit named after it. Same pattern as this session's earlier `febb870`/ora-skills co-mingled-commit incident (see the entry above), just on `~/.claude` instead.

## 2026-08-22 — M18 eval-harness YoC/DSCR floor-constant parser: cross-clause regex bug found by review, fixed and landed (`7d10e3f`)

**What:** A prior session's (1c2b8337) uncommitted M18-eval-harness-cannot-detect-governor-drift fix to `acquisition-underwriting-eval-harness/lib/diff_verdict.py` was independently code-reviewed and REJECTED before landing. `_parse_floor_pair` (extracts an "<observed> vs <floor>" pair from free-form `floor_result` prose, for DSCR/YoC governor-drift detection) searched a fixed +/-100-char window around a metric label. Since the window could span past a `;` into an unrelated metric's clause, and `_POSITIONAL_PCT_RE`'s label group is optional, a YoC search on the module's own canonical test string `"CLEARS (Basis 75.0% vs 65% floor; YoC 10.96% vs 8%; DSCR 1.45x vs 1.25x)"` incorrectly returned the Basis pair `(75.0, 65.0)` instead of `(10.96, 8.0)` — a silent false negative on exactly the governor-drift class this fix exists to catch. The existing test using this string only asserted status/floor_drift, so it passed for the wrong reason and never caught the bug.

**Fix:** Scoped `_parse_floor_pair`'s search to the label's own semicolon-delimited clause (`text.rfind(";", ...)` / `text.find(";", ...)`) instead of a fixed character window. Verified by direct execution — not just test-passing — against: the repro string; a reconstruction of the old buggy logic (confirmed it still returns the wrong pair on both healthy and drifted variants of the string); and all 6 real `golden_set/*.json` `floor_result` strings (zero misparses, including the 3 files that join Basis/YoC prose with "and" inside one semicolon segment). Also tightened both YoC label regexes with a leading `\b` (previously could match the "YC" inside "NYC").

Added 3 regression tests (`test_yoc_parses_own_clause_not_the_adjacent_basis_clause`, `test_yoc_drift_inside_full_combined_clears_phrasing_flags`, `test_trailing_floor_label_reversal_inside_combined_phrasing_flags_drift`) plus a direct-pair assertion. All 32 tests in `test_diff_verdict.py` pass.

**Known residual limitation, documented in-code (not fixed — kept the change narrow per Gabriel's original M18 approval):** the clause-scoping does not fully close the same bug class WITHIN one semicolon-delimited clause. A hypothetical compact "and"-joined phrasing like `"Basis 54% vs 65% floor and YoC 6.9% vs 8.0%"` (no intervening qualifier word, no `;`) would still misparse YoC to the Basis pair — confirmed by execution. Not present in any real golden file today (their "and"-joined clauses all have a qualifier word like "discount"/"vintage-ramp" breaking the false adjacency). Future fix if ever hit: require the optional label group in `_POSITIONAL_PCT_RE`/`_POSITIONAL_X_RE` when a clause contains more than one recognized metric label.

**Review:** Two independent `claude-fable-5` review passes per [[feedback_refute_pass_proactive_default]] / Gabriel's 2026-07-24 ratified financial-code review policy. Pass 1 (on the fix before cleanup) confirmed the defect and the fix, flagged 3 minor items (stale comment referencing a since-removed constant, missing leading `\b`, undocumented edge case) — all addressed. Pass 2 (on final content) returned APPROVED. Verdict recorded through `eos-review-gate.py` (key `7ec31d7c3f12ca4b2de7efe597156563a4194fcdc4976b812f34a1e932e3b740`).

**Shared-checkout incident, resolved cleanly:** mid-task, a concurrent session (04d7cdf1) briefly swept these two staged files into one of its own commits (`febb870`, message about an unrelated refi-rate default change) via what looks like a broad `add`/`commit -a`, then reset it back out (`git reset` to `HEAD~1`, followed by its own clean re-commit at `5b1f319` without these files). No content was lost or altered — verified `git diff febb870 -- <these 2 files>` was empty against the working tree before committing, i.e. the working tree still held exactly the twice-reviewed content. `commit-provenance-guard` correctly flagged `diff_verdict.py` as "edited by session 04d7cdf1" (tracking the commit-history touch, not actual content authorship); declared `allow-foreign-commit` with the verification evidence in the reason, then landed pathspec-scoped to just these 2 files so none of 04d7cdf1's unrelated `SKILL.md` WIP (still dirty/actively changing across several skills at commit time) got pulled in.

**Landed:** commit `7d10e3f` on `main`, `acquisition-underwriting-eval-harness/lib/diff_verdict.py` + `acquisition-underwriting-eval-harness/lib/test_diff_verdict.py` only (382 insertions, 9 deletions).

## 2026-08-22 — ora-passed-deal-tracker LAMS retirement: step 1 (ARCHIVE) EXECUTED; step 2 (DEREGISTER) still blocked on the surface gap

Supersedes the earlier 2026-08-22 entry ("retirement RATIFIED, execution BLOCKED"). Gabriel granted all approvals in-turn and directed execution of the full 4-step finish. Two of the four steps were capability-blocked, not permission-blocked — approval cannot supply a tool the session does not carry.

**Step 1 — ARCHIVE: DONE and verified.**
- Moved `…\Documents\Claude\Scheduled\ora-passed-deal-tracker\` → `…\Documents\Claude\Scheduled\_archive_2026-08-22_retired-to-ccmcp\ora-passed-deal-tracker\` (move, not delete; archive folder created as a sibling INSIDE the store, per this fleet's convention and the `_archive_2026-07-16_retired-to-ccmcp\` precedent).
- Verified: source path no longer exists; destination holds `SKILL.md`, 4,775 bytes, mtime `2026-08-05 17:32:21` preserved, SHA256 `7933FF2F46E5AD9AD3DFD4F9096C08CE6FDA4EDCAF12894BDB1BC8A38D1651E2` — byte-identical to the pre-move hash.
- The older `_archive_2026-06-11_orphans\ora-passed-deal-tracker\` sibling (2,236 bytes, mtime 2026-06-09) was NOT touched and NOT merged. Two distinct archives, unrelated provenance.

**Step 2 — DEREGISTER: NOT DONE.** `delete_scheduled_task` is absent from this session; re-confirmed by two further exhaustive tool-registry searches after approval was granted. This is a cloud-sandbox Cowork session (device-bridge only, no native app process), which per register-scheduled-task v2.13 Rule 1 + the v2.10 surface note never carries `create_scheduled_task` / `update_scheduled_task` / `delete_scheduled_task` / `list_scheduled_tasks`. Did NOT hand-edit `scheduled-tasks.json` to compensate (Rule 2, JSON-splice PROHIBITED). Second occurrence of the v2.10 incident class on this same task id.

**Step 3 — VERIFY via `list_scheduled_tasks`: NOT DONE** (same missing tool). Substituted a read-only registry read, which Rule 2 explicitly says is NOT verification — treat the LAMS line below as evidence, not proof:
- LAMS/Cowork: id `ora-passed-deal-tracker` STILL PRESENT, `30 6 15 * *`, `enabled: false`, `filePath` now DANGLING (points at the moved folder). 30 entries / 27 enabled.
- CC/MCP: id `ora-passed-deal-tracker`, `30 6 15 * *`, `enabled: true`, filePath `C:\Users\Owner\.claude\scheduled-tasks\ora-passed-deal-tracker\SKILL.md`, SKILL.md 25,288 bytes, SHA256 `025934498C6DEA95860F7AEEAD92F5684D57153DC049E47C93DD9A7EA0ACFE8F`. 40 entries / 36 enabled. **Untouched — cron and enabled state identical before and after this session's only write.**

**Step 4 — session-context.md: UPDATED** to the true intermediate state (archived / not yet deregistered), not flipped to complete.

**Net risk change.** The half-state is now a REGISTERED id with a MISSING SKILL.md rather than a registered id with a live duplicate spec. On balance this reduces exposure: if a future fleet-wide resume re-enables the LAMS entry (the 2026-08-21 near-incident pattern, which recurs on every pause/resume pass), it can no longer execute a duplicate sweep against Notion — there are no instructions on disk to run. It will instead fail on a missing file, which `task-folder-registration-probe.py` should surface as a visible [ACTION] rather than a silent duplicate. That probe alarm is EXPECTED until step 2 lands; do not "fix" it by restoring the folder.

**Still-open, one step:** from a NATIVE on-device Cowork session, run `delete_scheduled_task` for id `ora-passed-deal-tracker`, then confirm via `list_scheduled_tasks` that the LAMS entry is gone AND the CC/MCP entry is still `enabled: true` (the `path` field is the sole fleet disambiguator). Never the Cowork Scheduled-sidebar trash icon. The `RATIFIED` token for this drop is logged in the preceding 2026-08-22 entry, so `registry-membership-probe.py` will auto-ratify it inside the <=14d window — clock started 2026-08-22.

## 2026-08-22 — ora-passed-deal-tracker LAMS retirement RATIFIED, execution BLOCKED on surface gap (cloud Cowork session lacks the MCP tools)

**Status: NOT executed.** The LAMS/Cowork twin of `ora-passed-deal-tracker` is still registered and still unarchived as of this entry. Nothing was moved, deleted, disabled, or re-enabled on either fleet by this session.

**RATIFIED — planned registry drop: `ora-passed-deal-tracker` (LAMS/Cowork fleet ONLY).** Logged per register-scheduled-task v2.13's archive-first-delete-second bullet so `registry-membership-probe.py` auto-ratifies the drop (<=14d window) instead of raising a false [ACTION] when the native session executes it. The CC/MCP copy of this id is NOT being dropped and MUST stay enabled.

**Why it did not run here.** A retirement pass was dispatched to a cloud-sandbox Cowork session (device-bridge only, no native app process). Per register-scheduled-task v2.13 Rule 1 + the v2.10 surface note, such a session never carries `create_scheduled_task` / `update_scheduled_task` / `delete_scheduled_task` / `list_scheduled_tasks` — confirmed absent here by exhaustive tool-registry search, not inferred from a failed call. Stopped rather than improvising; specifically did NOT hand-edit `scheduled-tasks.json` (Rule 2, JSON-splice PROHIBITED) and did NOT perform the archive move alone, since archive-first-delete-second is a single ordered pass and half-executing it is the exact failure mode that produced this handoff. This is the SECOND occurrence of the v2.10 incident class, on the same task id — the 2026-08-17 original is what created the doctrine note.

**Verified ground truth (live registry read, read-only, 2026-08-22):**

- LAMS/Cowork — `local-agent-mode-sessions\...\scheduled-tasks.json`: id `ora-passed-deal-tracker`, cron `30 6 15 * *`, `enabled: false`, filePath `...\Documents\Claude\Scheduled\ora-passed-deal-tracker\SKILL.md`, `lastRunAt 2026-08-15T18:28:04.621Z`, `lastScheduledFor 2026-08-15T10:30:00.000Z`. Registry holds 30 entries, 27 enabled.
- CC/MCP — `claude-code-sessions\...\scheduled-tasks.json`: id `ora-passed-deal-tracker`, cron `30 6 15 * *`, **`enabled: true`** (canonical, untouched), filePath `C:\Users\Owner\.claude\scheduled-tasks\ora-passed-deal-tracker\SKILL.md`. Registry holds 40 entries, 36 enabled.
- Both copies confirmed present on disk with their own SKILL.md.

**Two pre-conditions cleared for whoever executes this:**

1. **Cross-fleet shared-file risk: CLEARED.** The CC/MCP `SKILL.md` (275 lines) is a full self-contained spec, NOT a redirect stub pointing at the LAMS OneDrive path. The LAMS `SKILL.md` (59 lines) is a strict content subset. Archiving the LAMS folder cannot destroy the CC copy's spec.
2. **Solely-run producer scripts: NONE.** Swept `~/.claude` for scripts this task is the sole invoker of. The LAMS copy invokes only `_shared/send-via-outlook.ps1` (shared across the fleet) and reads the `annual-cycle` repo path (also read by the CC copy). All other hits (`fleet-status.py`, `task-folder-registration-probe.py`, and their tests) reference the id as monitoring/test data, not as a dependency on the LAMS registration.

**Correction to the dispatched brief:** it proposed archiving to `Documents\Claude\Scheduled_archive_2026-08-22_retired\`. That is not this fleet's convention. Archives are siblings INSIDE the store: `Documents\Claude\Scheduled\_archive_YYYY-MM-DD_*\`. Nearest precedent for this exact case (retired because migrated to CC/MCP) is `_archive_2026-07-16_retired-to-ccmcp\`.

**Also found: session-context.md cites "History: `event_log.md` 2026-08-22" for this id, but no such entry existed.** The 2026-08-22 ratification was recorded in `session-context.md` only. This entry closes that gap. `session-context.md`'s bullet remains accurate as written ("ratified 2026-08-22 but NOT yet executed") and must NOT be flipped to complete until the two steps below actually run.

**Ready-to-run procedure — native on-device Cowork session ONLY** (Claude Code cannot do step 2: `delete_scheduled_task` carries no fleet parameter and resolves session-local, so the identical call from Code would delete the LIVE CC/MCP copy):

1. Archive: move `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-passed-deal-tracker\` to `...\Documents\Claude\Scheduled\_archive_2026-08-22_retired-to-ccmcp\ora-passed-deal-tracker\`. Move, never delete. Verify the move landed before step 2.
2. Deregister: `delete_scheduled_task` for id `ora-passed-deal-tracker` from that native LAMS session. Do NOT use the Cowork Scheduled-sidebar trash icon (folder-destructive, bypasses the Recycle Bin).
3. Verify: `list_scheduled_tasks` shows the LAMS entry gone AND the CC/MCP entry still `enabled: true` at `30 6 15 * *` with path `...\.claude\scheduled-tasks\...` (the `path` field is the sole fleet disambiguator).
4. Then update `session-context.md`'s `ora-passed-deal-tracker` bullet to record the retirement as executed, and append the completion entry here.

**Constraints honored this session:** LAMS copy never re-enabled, not even transiently; CC/MCP copy and its cron never touched; no JSON edits anywhere.

## 2026-08-22 — Dirty-tree-triage: cross-repo cleanup, 4 repos (Gabriel: "commit everything you can")

Full dirty-tree-triage run across `~/.claude`, `ora-skills`, `oxford-command-center`, `website-canonical` (98 dirty entries + stray-clone discovery, no strays found). Two-check settle window (20 min) confirmed staticity except `event_log.md`/`MEMORY.md`, which the live "Oracle setup audit" (Rev 18) session was actively writing — correctly excluded throughout.

**`~/.claude`** — 9 isolated commits: backup-mirror resync (32 files, verified byte-identical to already-committed live `scheduled-tasks/`), new `ora-pm-monthly-billing` task, 5 qodo-* skill installs, 4 already-deindexed memory deletions, 3 attributed reference-memory edits (2 from idle sessions, landed via `allow-foreign-commit`), push-fleet-heartbeat.ps1 worktree-resolution fix (idle session 80720188), 2 auto-generated guard-state files, `confidential-repos.json`'s oxford-command-center second-consumer addition (blast-radius file, landed on Gabriel's explicit in-turn approval).

**`ora-skills`** — landed the "Qodo code review on merged code" remediation batch (sessions 1c2b8337 + 04d7cdf1) minus 2 holds: `loi-generation/references/qc-gate.md` (pre-commit hook caught a real content defect — title says "22-Point" but only 16 items present, not resolved here per triage scope) and `acquisition-underwriting-eval-harness/lib/diff_verdict.py` + test (eos-review-gate: financial/governor code, independent review dispatched). 20 already-archived `_archive/*` scratch dirs (305 files, ~59.5K lines) left untracked — too large to blind-commit under a general go-ahead, flagged for Gabriel's explicit call.

**`oxford-command-center`** — landed the cc-audit-army remediation batch (session 1c2b8337) minus `server/warehouse/debt-scoring.ts` + test, held for independent review (DSCR now correctly uses ownership-adjusted `oxfordNoi` instead of 100%-basis `noi`, fixing a false-governor-clearance risk on jointly-owned properties — Hard Invariant 4 adjacent).

**`website-canonical`** — 1 dirty file (`netlify/edge-functions/knowledge-base.json`), untouched per Hard Invariant 2 (no per-deploy confirmation obtained).

Two independent reviews (model: claude-fable-5) dispatched for the held financial/governor-code diffs per Gabriel's 2026-07-24 eos-review-gate ratification; verdicts pending as of this entry.

## 2026-08-22 — Pre-push encoding-crash + two self-inflicted governor-drift-probe false positives, ROOT-CAUSED AND LANDED

- Root-caused and fixed the recurring `UnicodeDecodeError` crash Gabriel reproduced twice (same byte 0x9D, same position 1061) in `git-prepush-hook-tests-gate.py`'s subprocess capture. `subprocess.run(..., text=True)` with no explicit `encoding=` decodes a child's stdout using `locale.getpreferredencoding()` (cp1252 on Windows); `governor-drift-probe.py` reconfigures its own stdout to UTF-8 to echo scanned content, so it can legitimately emit bytes invalid under cp1252 (U+201D → `E2 80 9D`; `0x9D` has no cp1252 mapping at all), crashing `subprocess`'s internal reader thread and silently dropping captured output to `None` instead of raising — the gate then misread the decode artifact as a real test failure. Fixed both call sites (`git-prepush-hook-tests-gate.py::run_test_file`, `maintenance/test-governor-drift-probe.py::run_probe`, the latter being where the crash actually originates) with `encoding="utf-8", errors="replace"`. This is the same bug class multiple other sessions hit and overrode today (see the three `allow-hook-test-failure` override entries directly above this one, all citing claim `hooks-override-auth-prepush-encoding-crash`). Landed: [PR #150](https://github.com/ZeOoba/ora-claude-config/pull/150), independently reviewed (claude-fable-5, approved).
- While landing that fix, hit — and fixed — two more instances of the SAME underlying false-positive class in `governor-drift-probe.py`'s `is_gov` gate (a bare `"governor" in low` substring check): (1) `memory/reference_concurrent_session_duplicate_hardening_work.md:85` quotes another session's own investigation title, `"Fix governor-drift-probe false positive on LTV 65%/40%"`, in prose — the quoted title's `"governor-drift-probe"` alone satisfied `is_gov`, and the probe read `65%`/`40%` out of it as a live LTV drift. Fixed with an exact-filename `skip_names` exemption, mirroring the existing `disposition-ledger.md`/`deal-decision-ledger.md`/historical-evaluations-review precedent. (2) Recording that fix's own review artifact via `eos-review-gate.py --record` immediately self-triggered the identical class one layer up: the artifact's free-text `notes` field (describing the bug) lives under `hooks/sessions/<id>/reviews/*.json`, an ephemeral, session-id-unbounded path the probe was still scanning. Fixed by adding `"sessions"` to `_PRUNE_EXACT`, mirroring the `active-work` claim-file precedent landed earlier today. Landed together: [PR #149](https://github.com/ZeOoba/ora-claude-config/pull/149), independently reviewed (claude-fable-5, approved).
- Both were full-suite green (97/97 hook-tests-gate files pass) and independently reviewed by `claude-fable-5` per `eos-review-gate.py`'s mandatory review requirement before landing hooks/**-and-governor-code changes. Gabriel confirmed both merges in-turn. Closes the recurring need for `allow-hook-test-failure` overrides for this class of push — related prior history: OI-136 in `open-items-tracker.md`.

## 2026-08-22 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `efe758ee-6a0d-48c9-9be0-55ad97d0d6e8` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel authorized 2026-08-22 -- pushing a verified docstring-only commit to claim_work.py (branch oi-slug-clarify) blocked by two unrelated pre-existing failures: (1) encoding-crash in git-prepush-hook-tests-gate.py, already fixed by session d33391a0 (unmerged, applied locally read-only to unblock), and (2) governor-drift-probe LTV 65%/40% false-positive match inside reference_concurrent_session_duplicate_hardening_work.md (historical narrative text another session edited today, in session 8c98eacf's active governor-dscr-changelog scope, not mine to fix). My diff touches only hooks/lib/claim_work.py's docstring; 204/204 existing tests pass; independently reviewed PASS. One-time, this push only.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-08-22 13:43:02 local.

## 2026-08-22 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `fe5e4953-9754-4ecf-83cc-ead704bdd3f6` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel explicit in-turn confirmation 2026-08-22 to push claude/override-frequency-claim-hint despite the pre-existing, unrelated UnicodeDecodeError in git-prepush-hook-tests-gate.py's subprocess.run capture (missing encoding=utf-8) crashing maintenance/test-governor-drift-probe.py -- same bug and same authorization class Gabriel already gave earlier today for fix/governor-drift-probe-changelog-fp-v2 (PR #145); root-cause fix already claimed by a separate session (hooks-override-auth-prepush-encoding-crash)
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-08-22 13:41:24 local.

## 2026-08-22 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `efe758ee-6a0d-48c9-9be0-55ad97d0d6e8` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel authorized 2026-08-22 -- pushing a verified docstring-only commit to claim_work.py (branch oi-slug-clarify) blocked by two unrelated pre-existing failures: (1) encoding-crash in git-prepush-hook-tests-gate.py, already fixed by session d33391a0 (unmerged, applied locally read-only to unblock), and (2) governor-drift-probe LTV 65%/40% false-positive match inside reference_concurrent_session_duplicate_hardening_work.md (historical narrative text another session edited today, in session 8c98eacf's active governor-dscr-changelog scope, not mine to fix). My diff touches only hooks/lib/claim_work.py's docstring; 204/204 existing tests pass; independently reviewed PASS. One-time, this push only.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-08-22 13:37:39 local.

## 2026-08-22 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `fe5e4953-9754-4ecf-83cc-ead704bdd3f6` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel explicit in-turn confirmation 2026-08-22 to push claude/override-frequency-claim-hint despite the pre-existing, unrelated UnicodeDecodeError in git-prepush-hook-tests-gate.py's subprocess.run capture (missing encoding=utf-8) crashing maintenance/test-governor-drift-probe.py -- same bug and same authorization class Gabriel already gave earlier today for fix/governor-drift-probe-changelog-fp-v2 (PR #145); root-cause fix already claimed by a separate session (hooks-override-auth-prepush-encoding-crash)
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-08-22 13:35:07 local.

## 2026-08-22 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `fe5e4953-9754-4ecf-83cc-ead704bdd3f6` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel explicit in-turn confirmation 2026-08-22 to push claude/override-frequency-claim-hint despite the pre-existing, unrelated UnicodeDecodeError in git-prepush-hook-tests-gate.py's subprocess.run capture (missing encoding=utf-8) crashing maintenance/test-governor-drift-probe.py -- same bug and same authorization class Gabriel already gave earlier today for fix/governor-drift-probe-changelog-fp-v2 (PR #145); root-cause fix already claimed by a separate session (hooks-override-auth-prepush-encoding-crash)
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-08-22 13:30:45 local.

## 2026-08-22 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `efe758ee-6a0d-48c9-9be0-55ad97d0d6e8` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel authorized 2026-08-22 -- pushing a verified docstring-only commit to claim_work.py (branch oi-slug-clarify) blocked by two unrelated pre-existing failures: (1) encoding-crash in git-prepush-hook-tests-gate.py, already fixed by session d33391a0 (unmerged, applied locally read-only to unblock), and (2) governor-drift-probe LTV 65%/40% false-positive match inside reference_concurrent_session_duplicate_hardening_work.md (historical narrative text another session edited today, in session 8c98eacf's active governor-dscr-changelog scope, not mine to fix). My diff touches only hooks/lib/claim_work.py's docstring; 204/204 existing tests pass; independently reviewed PASS. One-time, this push only.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-08-22 13:28:58 local.

## 2026-08-22 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `fe5e4953-9754-4ecf-83cc-ead704bdd3f6` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel explicit in-turn confirmation 2026-08-22 to push claude/override-frequency-claim-hint despite the pre-existing, unrelated UnicodeDecodeError in git-prepush-hook-tests-gate.py's subprocess.run capture (missing encoding=utf-8) crashing maintenance/test-governor-drift-probe.py -- same bug and same authorization class Gabriel already gave earlier today for fix/governor-drift-probe-changelog-fp-v2 (PR #145); root-cause fix already claimed by a separate session (hooks-override-auth-prepush-encoding-crash)
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-08-22 13:21:18 local.

## 2026-08-22 -- package-and-stage-skill v1.24 installed (Gabriel's Save-skill click)

`package-and-stage-skill` v1.24 confirmed installed via Gabriel's **Save-skill click** in Cowork (Entry point B, `_staging\2026-08-22_reimport-batch6\package-and-stage-skill.skill`), not merely the upstream repo commit `b07f599` ("fix(package-and-stage-skill): v1.24 - check Local main.log too, not just Roaming", 2026-08-22 12:15:08 -0400).

Corroboration (main.log-based, both paths checked per v1.24's own fix):
- Roaming `main.log` (`%APPDATA%\Claude\logs\main.log`) was stale (last write 2026-08-20 20:51:03) — unusable for this check, consistent with the doctrine v1.24 itself documents.
- Local `main.log` (`%LOCALAPPDATA%\Claude\Logs\main.log`) was live and showed `[SkillsPlugin] Delta: 1 to download, 0 to remove` -> `Sync complete: 1 downloaded, 0 failed, 0 removed, 0 orphans cleaned` at **2026-08-22 12:37:42**.
- Cache directory CreationTime (`...\skills-plugin\...\skills\package-and-stage-skill`) moved from the pre-click baseline 2026-08-21 17:53:56 to **2026-08-22 12:37:42** -- an exact-second match with the Local-log Sync-complete event, confirming a genuine re-import rather than the pre-commit mirror-sync overwrite.
- Runtime cache file set verified against the packaged `.skill`: single entry `SKILL.md`, 62,377 bytes, SHA256 `d3d6a422187783b51b85f41e9e3c0cf19659e129943429f92f93ee771c3b283d` -- matches the package's zipped-entry hash exactly.

Ledger cleared: `pending_reimport.py clear package-and-stage-skill`. Spent `_staging\2026-08-22_reimport-batch6\` scratch archived to `_archive\` per Hard Invariant 6.

## 2026-08-22 -- package-and-stage-skill v1.24 installed via Gabriel's Save-skill click (dogfoods its own Local main.log fix)

Entry point A (fresh package) on the item that entered `pending_reimport.py` when v1.24 itself was committed (`b07f599`, checks `AppData\Local\Claude\Logs\main.log` in addition to the Roaming copy). Skill dir confirmed git-clean and `plugin_of` returned `None` (standalone Save-skill path) before packaging. Packaged via `tools/package_skills.py`, exit 0, frontmatter gate passed (description 1010/1024). Gabriel confirmed the Save-skill click.

Verification used the new v1.24 doctrine on itself: cache-directory CreationTime moved 2026-08-21 17:53:56 -> 2026-08-22 12:37:42, SKILL.md byte-identical to the packaged build. `AppData\Local\Claude\Logs\main.log` (the newly-added check) shows an exact `[SkillsPlugin] Delta: 1 to download` / `Sync complete: 1 downloaded` pair at the identical second, 12:37:42 -- first-hand, skill-specific corroboration (only one skill was installed in this window, no count-attribution ambiguity). Confirmed genuine re-import, no ambiguity. Cleared from `_staging/PENDING_REIMPORT.md` (`pending_reimport.py clear`).

## 2026-08-22 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `8c98eacf-04d4-4d51-9116-59f55a6b49b2` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel explicit in-turn authorization (2026-08-22) to push the Qodo-review-fix commit onto PR #145 despite a THIRD distinct instance this session of the LTV 65%/40% narration false positive -- this time in memory/reference_concurrent_session_duplicate_hardening_work.md, introduced by a concurrent session minutes ago, already tracked separately as task_bb18f708 (not yet landed). PR #145's own fix (two-round-plus-Qodo-round reviewed) is unrelated and correct.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-08-22 13:00:25 local.

## 2026-08-22 — duplicate-work collision investigated: NOT a dispatch bug, refuse-without-force reproduces correctly

Investigated the DSCR-changelog-scaling-multiplier duplicate-fix collision flagged earlier today (3+ sessions independently fixing the identical `governor-drift-probe.py` false positive; see [[project_governor_drift_probe_dscr_scaling_multiplier_fix_2026-08-22]]). Two questions, both answered:

**(1) No dispatcher/broadcast sent this task to multiple sessions.** Grepped `fleet-roster.md` and both scheduled-task registries for anything referencing `governor-drift-probe`/`deal-comparison` around 08-22 11:00-12:30 -- zero matches. Pulled the actual session transcripts (`list_events`/`search_session_transcripts`) for both colliding sessions: `local_564ffdae` (agent id `8c98eacf`) was titled "Fix governor-drift-probe false positive on LTV 65%/40%" -- a DIFFERENT, already-resolved false positive (found 08-21, landed 08-22 at `c7875a5`, see MEMORY.md). Its own override-usage-log hit on the DSCR-changelog signature came at 11:53:08, 35 minutes before it claimed the DSCR slug at 12:28:11 -- it was blocked by the DSCR bug as a SIDE EFFECT of pushing its own unrelated LTV fix, and only later chose to fix the DSCR bug too, in the same session. A THIRD, still-unidentified session independently built a competing fix on `fix/governor-drift-probe-changelog-fp` (commit `2155fb4`, 12:14:14 -0400), also unmerged. Two MORE sessions (`cde87cef` 11:52:37, `d1847790` 12:00:16) hit the same override without building any fix at all. **Root cause of the convergence: `governor-drift-probe.py` scans the ENTIRE tree on every push regardless of what changed, so one false-positive line in a shared file (`deal-comparison/SKILL.md:153`) blocks every concurrently-active session's push, not just sessions touching that file.** With 16+ sessions routinely active, a widely-blocking gate bug gets hit by many unrelated sessions in a short window, and several independently choose "fix root cause" over "override again" once it gets old. This is a consequence of (a) a real bug, (b) whole-tree scanning, and (c) high concurrency -- not a task-dispatch defect. No broadcast/dispatch mechanism needs fixing.

**(2) `claim_work.py`'s refuse-without-force is correctly implemented and reproduces as documented.** Read `main()`'s full `claim` branch: `write_claim()` is unreachable on the colliding-without-`--force` path -- the function returns `EXIT_CLAIM_REFUSED` (3) first. Verified with a clean-room reproduction (logic copied to an isolated sandbox, `ORA_ACTIVE_WORK_DIR` pointed at a scratch dir): session A claims, session B without `--force` is REFUSED at exit 3 and writes nothing, A's claim is untouched on disk; `--force` correctly takes over and preserves `prior_claim`. The live incident's actual behavior (8c98eacf's claim landing with no `prior_claim` and no REFUSED trail) could NOT be fully reconciled against this: the session-transcript tool compacts ordinary tool calls without showing raw arguments/stdout, so 8c98eacf's exact `claim` invocation and its printed output were not recoverable. Corroborating evidence (8c98eacf's own claim file recorded `cwd` as the OneDrive project folder and `paths` resolved as absolute paths under that same folder, not the real `~/.claude` repo paths -- the signature of the tool being invoked from the wrong working directory) suggests environment/context confusion in how that session invoked the CLI, but `CLAIMS_DIR` is a fixed absolute path independent of `cwd`, so a wrong-cwd invocation alone does not explain a bypassed collision check. Also untested: my reproduction was sequential, not a genuine concurrent-process race -- a true TOCTOU race between two real simultaneous `claim` invocations remains unverified either way. **Conclusion: the refusal code is provably correct in isolation; what happened live could not be fully explained with the evidence available and is left open, not closed as "not a bug."**

**Recommendation surfaced to Gabriel, not yet actioned:** two independent, non-exclusive options were flagged --  (a) narrow `governor-drift-probe.py`'s pre-push scan to changed files only, shrinking blast radius (bigger, separate project, needs its own review as governor code); (b) cheaper -- when the override-usage-log's already-tracked `signature` field sees a repeat hit, surface a "this false positive has been overridden N times by M sessions in 24h, check active claims before building a fix" warning at override time (reuses existing data, no gate-logic change). No implementation authorized this session -- read-only investigation only, per the request.

## 2026-08-22 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `8c98eacf-04d4-4d51-9116-59f55a6b49b2` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel explicit in-turn authorization (2026-08-22) to push fix/governor-drift-probe-changelog-fp-v2 (the two-round-reviewed changelog/active-work false-positive fix) despite a DIFFERENT, pre-existing bug in git-prepush-hook-tests-gate.py itself: subprocess.run(..., text=True) with no explicit encoding crashes with UnicodeDecodeError (byte 0x9d under cp1252) while capturing test-governor-drift-probe.py's subprocess output. Reproduces consistently (same byte, same position, 2 attempts) and is unrelated to the reviewed fix -- confirmed root cause: missing encoding="utf-8", errors="replace" on the subprocess.run call at hooks/git-prepush-hook-tests-gate.py:266-268. Gabriel chose to override and push now rather than fix the harness bug first; flagged separately as a follow-up.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-08-22 12:48:30 local.

## 2026-08-22 — governor-drift-probe DSCR-changelog-scaling-multiplier false positive FIXED, closing the recurring-override pattern (commit ecf7b42 -> main)

- `deal-comparison/SKILL.md:153`'s v1.2 changelog entry ("...inflating computed DSCR ~1.6x and letting deals that would floor-flag...") was misread by `governor-drift-probe.py` as a live DSCR governor declaration of 1.6x, blocking every push. Overridden via the `allow-hook-test-failure` token **8 times by at least 3 distinct sessions** across 2026-08-21/22 before landing (5 tallied at task start, signature `d491c6e47418`; 3 more by session `ebb79ea0` at 12:23/12:25/12:30 local on 2026-08-22 while this fix was in flight — see the three preceding event_log entries).
- Root cause: `RE_DSCR_THRESH` has no notion of "multiplier vs threshold" — "DSCR ~1.6x" (a scaling-factor narration of how wrong a buggy calculation's output was) reads identically to a declared floor. None of the module's existing qualifiers (`_portfolio_qualified`/`_refi_qualified`/`_stabilization_qualified`) matched this narrative shape — it needed its own suppressor.
- Fix: `RE_DSCR_COMPUTED_SCALING` + `_dscr_scaling_multiplier_spans()` — a narrow, span-scoped suppressor requiring the exact "&lt;scaling verb&gt; ... computed/calculated/measured ... dscr ... (~ | by [a factor of]) ... N.Nx" shape, deferred whole-line to the existing `RE_GOV_DSCR_BOUND` structural veto and gated on an explicit fix/bug/correction context token. Deliberately does NOT reuse the module's usual wide proximity veto (`_governor_declared_nearby`) — the real line's own "floor-flag" (ORA's Ruling-5 term of art) sits inside that veto's normal reach and would have wrongly blocked the fix.
- Built in an isolated worktree (`hooks-override-auth-governor-dscr-changelog` claim), 3 rounds of independent adversarial review (`eos-review-gate.py`, claude-fable-5): round 1 found a HIGH false negative + MEDIUM tense-blindness gap (both fixed); round 2 found a live regression in round 1's own fix (a modifier-word gap in the keyword lookahead — fixed by widening to 2-word tolerance) and identified 2 residual gaps (topic-blind and negation-blind changelog-context gating) accepted as documented, deliberately-pinned residuals rather than chased with new negation-detection logic; round 3 APPROVE WITH NITS (one tautological test line fixed). 8 new regression tests. Full suite green (94 local / 97 via the real pre-push hook-tests gate); live probe exit 0 against the real tree (was exit 1). Doctrine gate, hook-tests gate, and confidential-scan gate all run for real via `git push` (not just simulated).
- **Duplicate-work collision discovered mid-task**: at least 2 other parallel sessions were independently working this identical false positive — a fully-formed but unmerged competing fix on branch `fix/governor-drift-probe-changelog-fp` (commit `2155fb4`, worktree `fix-governor-drift-probe-changelog-fp`, different design: 3-signal line-wide gate requiring a tilde-glued value + literal "corrected" + a separate plain-1.25 restatement, no proximity/adjacency requirement between the three) — inspected and found to have a plausible false-negative gap of its own (a real drift sharing a line with an unrelated "corrected"/"1.25" mention elsewhere would be masked, since none of its three signals are scoped to each other) — and a claim on the identical `hooks-override-auth-governor-dscr-changelog` slug by session `8c98eacf` (claimed 2026-08-22T12:28:11, description referenced "currently uncommitted in shared checkout working tree" but the shared checkout had zero uncommitted changes to these files at check time; its recorded `paths` pointed under the OneDrive project folder rather than the actual `~/.claude` repo, suggesting `claim_work.py` was run from the wrong cwd). Neither session was reachable via `ListAgents`/`SendMessage` (not listed by a resolvable name). Proceeded to push after confirming `origin/main` had no conflicting commits for these 2 files and the shared checkout had no uncommitted collision — git's normal non-fast-forward protection covers any later conflicting push from those sessions. Flagging for Gabriel: this task appears to have been dispatched to 3+ parallel sessions simultaneously: worth checking whether that was intentional or a dispatch/scheduling duplication worth tightening.

## 2026-08-21 -- oxfordra.net deploy: broker auth-binding security fix

Deployed commits `eb80fe7` + `fde9328` (website-canonical `main`) to production via `netlify deploy --build --prod`, with Gabriel's explicit in-turn confirmation ("push and deploy it"). Deploy ID `6a88d33d177dcd3eecce9b27`.

**What shipped:** closes cc-audit-army finding `unauth-sharepoint-read-oracle-via-background-fn`. `broker-finalize.mjs` mints a short-lived HMAC `authToken` binding `{submissionId, itemPath}` for the internal `broker-finalize` -> `broker-score-background` handoff (previously unauthenticated, a public-URL SharePoint read-and-persist oracle). Base fix found already in progress, uncommitted, in the shared checkout -- origin unattributed after checking with two other concurrently-active sessions; reviewed thoroughly (8-angle adversarial code review) before building on it and shipping.

5 adversarial-review findings fixed on top of the base fix: cross-boundary token replay closed via a `type` claim (`upload`/`bg-auth`/`status`); the read-side auth gap on `broker-score-status.mjs` closed via a new `statusToken` (client-threaded through `broker-upload.js`/`for-brokers.html`); `SUBMISSION_ID_RE`/`UPLOAD_PATH_RE` deduplicated into `_shared/validate.js` next to their generators; auth check reordered ahead of shape checks in `broker-score-background.mjs`; `verifyIntakeToken` hardened to fail closed instead of throwing on a missing secret. A 6th finding (an unrelated, uncited change to `track-record.html`'s public Fairground Village Center return figures) was NOT applied -- Gabriel confirmed the live 4.5x/63%+ figures were already correct and a peer session reverted that edit separately.

**Pre-deploy gate:** `site-qc-reviewer` caught a real BLOCK on the first pass -- `for-brokers.html` referenced `/broker-upload.js` with no cache-bust query param (the only script on the site missing one), while `_headers` sets a 1-year immutable cache on `/*.js` and this diff changed `pollForScore()`'s signature. A returning visitor's stale cached JS would have called the new server code with no `statusToken`, gotten a 401, and hung/crashed silently. Fixed with `?v=2` (commit `fde9328`, matching the site's existing per-file cache-bust convention); re-review returned APPROVE.

**Verification:** 60/60 tests passing (`node --test tests/functions/`, including 7 new tests pinning the fixes) both before and after the cache-bust fix. `verify-push.py` confirmed local HEAD == `origin/main` tip (`fde9328`) before deploy. Post-deploy: `https://oxfordra.net/` and `/for-brokers` both 200; served `/broker-upload.js` confirmed live with the 4-parameter `pollForScore` signature and `?v=2` reference; `/api/broker-score-status` confirmed returning `401 invalid_auth` with no `statusToken` -- the fix is live and functioning in production.

## 2026-08-21 -- repo-architecture-review description-trim (commit 73feef1): content verified live, Save-skill click provenance inconclusive

Gabriel reported clicking **Save skill** in Cowork on the staged
`repo-architecture-review.skill` (904/1024-char description trim, commit `73feef1`,
2026-08-21 18:08:05 -0400). Package staged at
`ora-skills\_staging\2026-08-21_repo-architecture-review-desclen-fix\`, SHA256
`d813a1e536493bd3b46c8736a48a04bee84607efe1112379a469004f5eb4ecb2`.

**Content verified correct and live.** Cache SKILL.md at
`...\skills-plugin\583f08bc-...\a6ad2c61-...\skills\repo-architecture-review\SKILL.md`
is byte-identical to the current repo copy (SHA256 `f89750d5...4681` both sides) --
confirmed via direct grep for the trimmed phrasing (new wording present, old wording
absent) as well as a full-file hash match.

**But CreationTime evidence does NOT corroborate a fresh click.** The cache directory's
CreationTime is still 2026-08-21 18:01:19 -- unchanged from the batch8 install
recorded earlier today (`automation-health-monitor v1.6 + repo-architecture-review v1.0
(post-1aec229)` entry). No re-creation event happened after the 18:08:05 commit. This
is fully explained by `sync_appdata_mirror.py`'s pre-commit hook, which overwrites
content in place into any EXISTING AppData mirror on every commit -- per this skill's
own v1.13 doctrine, content matching the repo is not itself evidence of a genuine
platform re-import when CreationTime hasn't moved. No verification scripts or
`present_files` artifacts were found in the staging folder either (unlike every prior
round in today's session, which left a scratch-script trail), consistent with the
click not having actually reached Entry point B in Cowork.

**Conclusion, following the same-day precedent for this exact ambiguous pattern
(debt-management, package-and-stage-skill entries above):** content is verified
correct and live regardless of whether today's click did anything -- the pre-commit
hook alone guarantees that. Cleared from the ledger on that basis, but this is NOT
being recorded as a confirmed Save-skill click; provenance for this specific instance
is inconclusive.

`_staging\2026-08-21_repo-architecture-review-desclen-fix\` archived to
`_archive\2026-08-21_repo-architecture-review-desclen-fix\` (never deleted).

## 2026-08-21 -- 6-skill reimport batch (deal-execution, debt-management, document-assembly, estoppel-request-generation, lease-abstraction-pipeline, legal-intelligence) installed via Gabriel's Save-skill clicks

Entry point A (fresh package) on the 6 items that entered `pending_reimport.py` after a concurrent session committed `63f0efe` (deal-execution, document-assembly, estoppel-request-generation, lease-abstraction-pipeline, legal-intelligence -- 8 code-review findings closed: landlord/vesting wiring, estoppel routing, CreationTime gap) and `27cb034` (debt-management v1.3 -- PAYOFF STATEMENTS workflow, repo-first reconciliation). All six skill dirs confirmed git-clean and `plugin_of` returned `None` for all six (standalone Save-skill path) before packaging. Packaged via `tools/package_skills.py`, exit 0, frontmatter gate passed on all six (deal-execution 980/1024, debt-management 929/1024, document-assembly 778/1024, estoppel-request-generation 902/1024, lease-abstraction-pipeline 966/1024, legal-intelligence 969/1024). Staged and handed to a Cowork session (this Code session has no Save-skill install control) for Entry point B present_files + Save-skill clicks; Cowork routed all six through the Cowork install button (two are multi-file: deal-execution has `scripts/`, lease-abstraction-pipeline has `references/` + `SCHEDULED_TASK.md`). Gabriel confirmed all six clicks.

`main.log` remained stale throughout (last write 2026-08-20 20:51:03), so verification used the cache-directory CreationTime discriminator against pre-click baselines captured before the clicks:
- `deal-execution`: CreationTime moved 17:21:59 -> 17:53:45. Confirmed genuine re-import, content byte-identical.
- `document-assembly`: CreationTime moved 2026-08-14 18:00:44 -> 17:53:44. Confirmed genuine re-import, content byte-identical.
- `estoppel-request-generation`: CreationTime moved 17:22:05 -> 17:53:48. Confirmed genuine re-import, content byte-identical.
- `lease-abstraction-pipeline`: CreationTime moved 17:21:51 -> 17:53:51. Confirmed genuine re-import, content byte-identical (all 3 packaged files, incl. `SCHEDULED_TASK.md`).
- `legal-intelligence`: CreationTime moved 2026-08-03 14:51:09 -> 17:53:56. Confirmed genuine re-import, content byte-identical.
- `debt-management`: CreationTime did NOT move (unchanged at 2026-08-17 17:34:25) even though content is byte-identical to the packaged v1.3. Same ambiguous pattern as `package-and-stage-skill` in the prior batch: the pre-commit `sync_appdata_mirror.py` hook overwrites content in-place into any EXISTING AppData mirror on every commit, so a byte-match here is expected regardless of whether today's click actually re-imported anything -- per this skill's own v1.13 doctrine, content match with an unmoved CreationTime is not first-hand proof of install. Flagging rather than asserting a clean confirmation: **content is verified correct and live; today's click's provenance for debt-management specifically is inconclusive.**

All six cleared from `_staging/PENDING_REIMPORT.md` (`pending_reimport.py clear`) -- content re-sync independently confirmed for all six, genuine re-import confirmed via CreationTime for five of the six.

## 2026-08-21 -- Save-skill click confirmed: 6-skill batch (commit 63f0efe)

Packaged, staged, and installed via package-and-stage-skill v1.22/v1.23 Entry point A,
run from a cloud Cowork session over the Desktop Commander bridge. `main.log` was
stale (last write 2026-08-20 20:51:03) for the entire session, so the CreationTime
fallback discriminator (v1.22 step 7) was used for post-install verification instead
of the main.log Delta/Sync-complete gate.

Skills confirmed installed (cache dir CreationTime moved to 2026-08-21 17:53:44-56,
all post-dating both the 17:45:17 commit and the pre-check baseline, file counts
matching the packaged .skill entries exactly):

- deal-execution v1.6 (3 files: SKILL.md, scripts/audit_completeness.py, scripts/extract_revisions.py)
- document-assembly v1.4 (1 file: SKILL.md)
- estoppel-request-generation v1.1 (1 file: SKILL.md)
- lease-abstraction-pipeline v2.7 (3 files: SKILL.md, SCHEDULED_TASK.md, references/extraction-edge-cases.md)
- legal-intelligence v1.3 (1 file: SKILL.md)
- package-and-stage-skill v1.23 (1 file: SKILL.md)

Note: package-and-stage-skill's own AppData cache hash-matched the repo BEFORE this
install (pre-commit mirror-sync hook artifact, per v1.13 doctrine) -- the stale
CreationTime baseline (16:56:54, pre-dating the 17:45:17 commit) and this session's
own synced mirror still reading v1.22 were what correctly flagged it as needing
reimport despite the false-negative hash match.

This is Gabriel's confirmed Save-skill click on all 6, not merely the upstream repo
commit. Source commit: 63f0efe80fc8b6377211bc79d455676afda54add.

## 2026-08-21 -- orphaned oxford-command-center-1.worktrees archived (OI-200 loose end)

Running dirty-tree-triage's new stray-clone-by-remote discovery (scan_dirty_trees.py, commit 1aec229) surfaced C:\Users\Owner\oxford-command-center-1.worktrees\qodo-github-repo-review -- a git-worktree checkout left behind when its parent clone (oxford-command-center-1) was archived under OI-200's closure. Not flagged by the discovery tool itself (no top-level .git of its own), and git couldn't even recognize it as a repo any more ("fatal: not a git repository") since its .git pointer referenced the now-moved parent -- confirmed genuinely orphaned, not live: absent from the primary repo's own `git worktree list` (which only shows the 5 real worktrees under oxford-command-center/.claude/worktrees/ and oxford-command-center-worktrees/, a different naming pattern entirely). Archived (never deleted, Hard Invariant 6) to C:\Users\Owner\_archive-non-onedrive\oxford-command-center-1-worktrees-orphan-20260821\, alongside the original stray-clone archive from OI-200. Verified the primary repo's 5 live worktrees are unaffected post-move.

## 2026-08-21 -- loi-generation v1.7 committed and pushed: merged colliding v1.6 revisions (commit 3c477f5)

Reconciled the loi-generation version collision at Gabriel's direction. Repo's v1.6 (2026-08-16, committed) added Phase 6c Lost-Deal Ledger capture (Notion Deal Sourcing Log, `ORA Max Defensible Price`); the platform's independent v1.6 (2026-08-18, never committed) wired `{{PROPERTY_ZONING_PHRASE}}` + a new inline SS13 entity-interest conditional into the master template, fixed the EXECUTION PAGE subtitle token gap, and fixed a `{{TENANT_DISCLOSURE_PHRASE}}` trailing-comma defect -- both diverged from the same v1.5 base with no knowledge of each other. Neither was a superset, so this merged both feature sets into v1.7: `SKILL.md` combines both sides' Decision Logic/Token Reference/Phase 4/Versioning changes, and `templates/LOI_Master_Template_Condensed.docx` was replaced with the platform-side v1.1 copy (Phase 6c is Notion-only and needed no template changes, so nothing from the repo side was lost). Pre-commit gate initially BLOCKED on the merged description exceeding the 1024-char platform limit (1094 chars) -- trimmed to 912 and re-committed clean; this is the pre-flight frontmatter gate working as designed, not a defect. Pushed `1aec229..3c477f5` to origin/main. Archived both spent rescue copies to `_archive\2026-08-21_repo-first-rescue-triage\loi-generation-merged-3c477f5\`. Verified the platform runtime-cache mirror now byte-matches the committed content (auto-synced by pre-commit Check 4). Companion to the same-session `debt-management` v1.3 reconciliation (commit 27cb034). **One item from the same `STORE_AHEAD_OF_REPO.md` sweep remains OPEN:** `lease-addendum` -- real committed work on unmerged branch `claude/determined-cannon-8126a7` commit `a359381` (ora_doc_qc retrofit), needs a merge-to-main decision, not touched.

## 2026-08-21 -- dirty-tree-triage v1.1 installed via Save-skill click (OI-203 fix now live)

Gabriel clicked **Save skill** in Cowork on the `dirty-tree-triage.skill` package (2 entries: `SKILL.md`, `scripts/scan_dirty_trees.py`; commit `4e44f72`, the OI-203 fix pairing step 7's ora-skills git check with a `claim_work.py claim`). Verified as a genuine re-import, not a mirror-sync artifact: the runtime cache directory's CreationTime moved from the 2026-08-13 baseline to 2026-08-21 17:41:42, with both files sharing that exact timestamp (directory torn down and recreated); `main.log` was unavailable for corroboration (no activity since 2026-08-20 20:51:03, "going down for update"), so the CreationTime discriminator was the sole evidence, per package-and-stage-skill v1.22. Content hash-matches commit `4e44f72` exactly. `open-items-tracker.md#OI-203` fix is now live end-to-end (repo + platform). Cleared from `ora-skills/_staging/PENDING_REIMPORT.md`.

Noted in passing: the repo has since moved past this commit with uncommitted v1.2 WIP (stray-clone-by-remote discovery, OI-200) under a live, properly-filed `ora-skills-housekeeping` claim (session `d7aee8c2`) -- correctly left untouched, not a conflict with this install.

## 2026-08-21 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `00eb97d5-5753-4335-93e9-891e19413564` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel authorized in-turn 2026-08-21. maintenance/test-governor-drift-probe.py fails on unmodified main (confirmed, unrelated to this push's 2-file diff) -- false positive flagging acquisition-buy-box-v1.md's ratified 65%-per-property-refi/40%-aggregate LTV split as drift. Fix spawned as a separate task (task_bb18f708).
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-08-21 17:47:16 local.

## 2026-08-21 -- 3-skill reimport batch (insurance-renewal-review, dirty-tree-triage, package-and-stage-skill) installed via Gabriel's Save-skill clicks

Entry point A (fresh package, no pre-built `.skill` existed for any of the three) on the 3 items left open by the earlier batch5 handoff: `insurance-renewal-review` (commit `834bfe3`, trims `description` off the 1024-char hard import limit), `dirty-tree-triage` (commit `4e44f72`, pairs step 7's `ora-skills` single-writer check with a `claim_work.py` claim per OI-203), `package-and-stage-skill` (commit `c31fa66`, v1.22 -- `main.log` liveness fallback + canonical `.ps1` invocation snippet). Repo confirmed clean for all three skill dirs before packaging; `plugin_of` returned `None` for all three (standalone Save-skill path, no plugin rebuild). Packaged via `tools/package_skills.py`, exit 0, frontmatter gate passed (`insurance-renewal-review` now 940/1024, confirming the 834bfe3 trim took effect; `package-and-stage-skill` 1010/1024; `dirty-tree-triage` 729/1024). Staged and presented; Gabriel confirmed all three Save-skill clicks.

`main.log` was stale throughout (last write 2026-08-20 20:51:03, per v1.22's own documented fallback), so post-install verification used the cache-directory CreationTime discriminator instead of log corroboration:
- `insurance-renewal-review`: cache dir CreationTime moved 17:19:31 -> 17:41:42 -- confirmed genuine re-import. Content byte-identical to the packaged v-trim.
- `dirty-tree-triage`: cache dir CreationTime moved 2026-08-13 20:08:25 -> 17:41:42 -- confirmed genuine re-import. Content byte-identical to the packaged build.
- `package-and-stage-skill`: cache dir CreationTime did NOT move (unchanged at 16:56:54, i.e. ~2 min after the c31fa66 commit itself) even though content is byte-identical to the packaged v1.22. Per this skill's own v1.13 doctrine, an unchanged CreationTime with matching content is NOT first-hand proof that today's click is what installed it -- most likely an earlier, unlogged install already landed v1.22 minutes after the commit, and today's click was a no-op against already-current content. Flagging this rather than asserting a clean "confirmed click" for this one item: **content is verified correct and live; install-timing provenance for this specific instance is inconclusive.**

All three cleared from `_staging/PENDING_REIMPORT.md` (`pending_reimport.py clear`) since the runtime cache re-sync is independently confirmed for content on all three, and confirmed genuine re-import for two of the three. Note: an uncommitted, in-progress edit to `package-and-stage-skill/SKILL.md` (session `04d7cdf1`, toward a v1.23 doc-only fix) was observed mid-task, unrelated to this batch -- will surface as its own future pending-reimport once committed.

## 2026-08-21 -- debt-management v1.3 committed: repo-first reconciliation of platform-side PAYOFF STATEMENTS work (commit 27cb034)

Committed `debt-management/SKILL.md` v1.2 -> v1.3, landing the PAYOFF STATEMENTS section (Step 0 direction check, Workflow A issuing / Workflow B auditing, 13-point payoff QC gate) that had been running on the platform cache since 2026-08-17 but was never committed to `ora-skills` -- surfaced by re-running `tools/repo_first_check.py`'s full sweep while investigating a Gabriel-flagged `STORE_AHEAD_OF_REPO.md` entry (which itself turned out to be stale/already-resolved for lease-form-qc/listing-agreement-qc). Verified the cache content byte-matched (CRLF-normalized) the committed result before archiving its rescue copy. Committed in isolation (explicit pathspec, not `git add -A`) after a concurrent live session's own 6-file staged commit (`63f0efe`) landed first -- avoided co-mingling per the shared-checkout hygiene hook's warning. Pre-commit mirror sync (Check 4) pushed the new content into the AppData runtime cache automatically; `PENDING_REIMPORT.md` now carries a `debt-management` line awaiting Gabriel's Save-skill click. Archived the spent rescue copy to `_archive\2026-08-21_repo-first-rescue-triage\debt-management-committed-27cb034\`. **Two items from the same sweep remain OPEN, need Gabriel's decision, NOT touched:** `loi-generation` (a genuine two-way v1.6 version collision -- repo's Lost-Deal Ledger Phase 6c vs. cache's template-token wiring, both real, neither a superset) and `lease-addendum` (real committed work on unmerged branch `claude/determined-cannon-8126a7` commit `a359381`, retrofitting `addendum_qc.py`/`ora_doc_qc.py` -- needs a merge-to-main decision, not a rescue). Their rescue copies remain in `_staging/repo-first-rescue/`, untouched.

## 2026-08-21 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `00eb97d5-5753-4335-93e9-891e19413564` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel authorized in-turn 2026-08-21. maintenance/test-governor-drift-probe.py fails on unmodified main (confirmed, unrelated to this push's 2-file diff) -- false positive flagging acquisition-buy-box-v1.md's ratified 65%-per-property-refi/40%-aggregate LTV split as drift. Fix spawned as a separate task (task_bb18f708).
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-08-21 17:42:51 local.

## 2026-08-21 -- dirty-tree-triage: full `ora-skills\_staging\` sweep, 26 dated folders + 32 loose files archived, zero live/uncommitted work found

Extended the earlier repo-first-rescue triage to the entire remaining `_staging\` backlog (six weeks, 2026-07-09 through 2026-08-21, ~18MB). Six parallel read-only investigation passes hash-compared every packaged `.skill`/source-mirror file against full `ora-skills` git history (CRLF-normalized) and cross-checked loose `.ps1`/`.py`/`.md` session scripts against confirmed-shipped commits and `event_log.md`. Result: **every single item resolved to an exact historical commit match or confirmed-shipped/confirmed-installed state** — no live, uncommitted, or contested content anywhere in the backlog. Notable corroborating evidence along the way: `2026-07-21_index-unregistered-batch`'s own `_verify_output.txt` independently confirmed 15/15 installs; `2026-08-17`'s `CODE-HANDOFF.md` task list (including reconciling `_staging/repo-first-rescue/`) was independently confirmed complete; `2026-08-17`'s LAMS pause/resume draft's underlying scheduled task was confirmed to have actually fired live today at 21:06:45Z. One folder (`2026-08-21_batch5-reimport`) was auto-archived by a concurrent live session mid-sweep — left untouched, already resolved. Archived (never deleted, Hard Invariant 6) the remaining 25 dated folders + 32 loose files to `_archive\2026-08-21_staging-full-sweep-triage\`, structure preserved. Left `_staging\PENDING_REIMPORT.md` and `_staging\STORE_AHEAD_OF_REPO.md` untouched — confirmed live/active (PENDING_REIMPORT.md's own mtime advanced mid-sweep). `_staging\` now holds only those two active ledger files. Separate open item surfaced, out of scope for this sweep: `STORE_AHEAD_OF_REPO.md` currently flags `lease-form-qc` and `listing-agreement-qc` runtime-cache content as DIVERGENT from repo on `scripts/ora_doc_qc.py` since 2026-08-17T20:23Z — a live, still-open drift, unrelated to any archived item here.

## 2026-08-21 -- OI-203 fixed: dirty-tree-triage step 7 now pairs the ora-skills git check with a claim_work.py claim

`ora-skills` commit `4e44f72` (`dirty-tree-triage` v1.1, Gabriel-directed): step 7's `git log -1`/`git status` single-writer check now also requires `claim_work.py claim ora-skills-housekeeping --paths <target>` before any hands-on ora-skills triage. Claimed the work under that exact slug before making this edit -- clean claim, no takeover needed -- and released it after commit. Root cause (filed as `open-items-tracker.md#OI-203`): two sessions independently ran this skill's full workflow against the same `ora-skills/_staging` folders earlier today with neither claiming first; git state alone can't see a concurrent session since commits share author identity across sessions, so both saw a clean tree and proceeded, and the collision was caught only by accident. The pre-commit hook auto-synced the AppData mirror and logged the skill to `ora-skills/_staging/PENDING_REIMPORT.md` -- **not yet live on the platform account** until a `package-and-stage-skill` re-upload runs; a session still reading the old synced copy won't see the new step 7 language in the meantime. OI-203 row updated to FIXED (repo) with the commit citation.

## 2026-08-21 -- governor-drift-probe.py KNOWN GAP 2 closed: per-property refi-sizing 65% LTV ceiling no longer flags as drift

Fixed a false positive that was blocking every push repo-wide: `governor-drift-probe.py`
flagged `acquisition-buy-box-v1.md:31` ("LTV ceiling (per-property refi sizing): <= 65%
LTV...") as "LTV governor 65% != canonical 40%". Doctrine states the ratified per-property
refi-sizing ceiling (<= 65% LTV) and the portfolio-aggregate ceiling (<= 40% LTV, Hard
Invariant 4) on SEPARATE bullets (buy-box-v1.md :31 vs :33); the probe's existing pairing
suppressor only recognized the two governors when stated together on the same line. This
was a previously-documented, deliberately-deferred gap in the probe's own comments (KNOWN
GAP 2: "Closing it requires widening LTV SUPPRESSION -- a false-negative risk on Hard
Invariant 4 that belongs in its own reviewed change").

Fix: a narrow suppressor in `_flag_ltv` that is VALUE-LOCKED (only the literal ratified
"65" ever matches -- a real per-property drift still flags) and VALUE-ADJACENT (the
ratified "per-property ... refi ... siz(ing)" wording must end within a short window
immediately before the flagged value, not merely appear anywhere on the line), vetoed by
the existing `_governor_declared_nearby` check.

Two-round independent review via `eos-review-gate.py` (pinned `claude-fable-5`, the
gate's top reviewer tier). Round 1 caught a real Critical: the first cut's frame check was
line-wide, which could mask a genuine AGGREGATE-governor drift restated as 65% elsewhere
on the same line (e.g. "Portfolio LTV ceiling raised to 65% given our per-property refi
sizing convention."). Fixed with the value-adjacency requirement; round 2 approved with no
blocking findings. A known, narrower residual was accepted rather than fixed (a
governor/acquisition-declaration token sitting >28 chars before the value, outside the
existing veto's reach, could still be masked in this one shape) -- documented in-code
rather than widening `VETO_BEFORE`, since that constant is independently tuned against
other real-tree margins and the value-lock means only the literal "65" is ever at stake.

Added 4 regression tests: the real false positive (plus a hyphenated "refi-sizing"
spelling), a drifted per-property value still flagging, and the two round-1
adversarial-masking shapes still flagging. Full `test-governor-drift-probe.py` suite
green; live probe now exits 0 against the real tree (1242 files scanned; was exit 1).
Full local pre-push chain run for real (doctrine gate, 94/94 hook-tests, confidentiality
scan) -- all green, both as a standalone simulation and during the actual push.

Built in an isolated worktree per the shared-checkout single-writer doctrine (claimed via
`claim_work.py` under a distinct `hooks-override-auth-governor-drift` slug alongside a
concurrent session's unrelated `hooks-override-auth` claim on `commit-hygiene-guard.py`).
Merged to `main` (`c7875a5` -> merge commit) and pushed to `origin/main` on
`ora-claude-config` (`7221e63..bfcd26b`). Scratch worktrees and the merged feature branch
cleaned up after push.

## 2026-08-21 — Skill fleet: manuscript-amendment discipline (754 Old State)

Four skills committed (`ora-skills` 29e78e8) and confirmed installed. Origin: a scanned
lease at 754 Old State Route 74 whose typed expiry of "May 31, 2030" was struck through in
ink and replaced by hand with "2027", circled and initialed. Tesseract transcribed the typed
layer and dropped the manuscript change with no signal. An IC memo (v02) and a full IRR
model were published on the wrong date before Gabriel caught it. The visual sweep that
followed found four more hand changes OCR had missed, plus an unexecuted base lease that
four months of file review had not surfaced.

- **lease-abstraction-pipeline v2.6** — new STEP 2A: mandatory page-image review for every
  OCR-path document before any field is reported (render, contact-sheet, zoom every economic
  term / party block / signature page). Adds `EXECUTION_STATUS` and lease-chain-gap checks to
  every document, +9 STEP 5 quality flags. Rule of record: on a scanned document, OCR text is
  evidence of the FORM, not of the BARGAIN.
- **deal-execution v1.5** — LEASE-CHAIN INTEGRITY in Workflow 3 DD (instrument chain, executed
  counterpart per link, landlord-of-record match, manuscript-amendment catalogue); Workflow 2A
  item 12 extended so estoppels carry the chain and reproduce hand amendments verbatim.
- **title-exam-abstraction v1.0** (new) — exam-vs-commitment distinction; the mortgage-location-
  vs-boundary-survey trap (OAC 4733-38 vs -37); cross-collateral/cross-default as its own
  category with payoff ≠ parcel release; every exception routed to a deliverable or register item.
- **estoppel-request-generation v1.0** (new) — estoppels built from the 32-field abstract,
  pre-filled, each abstraction defect converted into an affirmative certification. Never amends.

**Install verified before clearing the ledger.** main.log showed no SkillsPlugin sync (last
entry 2026-08-20 20:40), so verification rested on the two NEW skills: the post-commit hook
reported "no local AppData mirror installed yet — nothing to sync" for both, yet both cache
directories existed at 17:22 local, three minutes after the 21:19Z commit. The hook could not
have created them, so only a real Save-skill install could. All four then hashed byte-identical
(EOL-normalized) to the repo. Ledger entries cleared for the four.

**Observed, not actioned:** five other ledger entries (daily-brief, insurance-renewal-review,
listing-agreement-qc, register-scheduled-task, settlement-basis-extraction) disappeared between
this session's read and its clear. `cmd_clear` provably pops only named skills, so another actor
cleared them; a subsequent always-verify `candidates` sweep shows none of the five has drift, so
nothing was lost. That sweep did surface **three skills with repo-ahead-of-cache drift and no
ledger entry at all — `debt-management`, `lease-addendum`, `loi-generation`** — the retroactive-
blindness case `candidates` exists to catch. Left for Gabriel: they belong to other workstreams
and packaging/installing them was not in scope.

**Process note:** a cloud Cowork session CAN reach the repo-first path through the Desktop
Commander bridge. Route: author in-container → SendUserFile → device_commit_files into a
connected folder → PowerShell copy into `ora-skills` → idempotent patch scripts → pre-flight
gate → commit → `tools\package_skills.py` → device_stage_files back → SendUserFile renders the
Save-skill button. Use PowerShell, not `cmd /c` with `set VAR=...&` (breaks on spaced paths).
Watch line endings: reading utf8 and writing `newline=''` flips CRLF→LF, which `.gitattributes`
wants but makes a legacy-CRLF blob diff look like a full-file rewrite — verify with `git diff -w`
and say so in the commit message.

## 2026-08-21 -- Filed OI-203: claim_work.py process gap surfaced by today's ora-skills `_staging` triage collision

Two sessions were independently handed the same investigation of `ora-skills/_staging/repo-first-rescue/` + `session_outputs/lease-addendum.skill` today; both reached the same conclusion (all 8 items fully superseded, safe to archive) but neither filed a `claim_work.py claim` before starting, so the collision was caught only by accident -- one session's archive `mv` found its source already moved by the other, seconds after `event_log.md` had already been updated. `hooks/active-work/*.json` held no claim for this task at the time. The module's own docstring cites a near-identical 2026-08-12 ora-skills precedent as its reason for existing; this is a fresh instance of the same gap, not a new failure mode. Distinct from [open-items-tracker.md#OI-166](open-items-tracker.md#OI-166) (fixed 2026-08-16 -- a bug inside the claim mechanism itself); this one is non-adoption -- the mechanism was never invoked. Filed per Gabriel's in-turn instruction as [open-items-tracker.md#OI-203](open-items-tracker.md#OI-203); full detail in the tracker row.

## 2026-08-21 -- 5-skill reimport batch INSTALLED (Save-skill clicks confirmed, not merely committed)

**What happened.** Gabriel clicked **Save skill** in Cowork for 5 skills that had sat in
`PENDING_REIMPORT.md` since 2026-08-17 (one since 2026-08-21). The Cowork session that ran
the clicks got through Entry point B's pre-check and staging (extracted zips to
`_extract_check\`, ran a freshness screen) but did not complete steps 5-8 -- no event_log
entry, no ledger clear, staging folder left unarchived. This Code session verified the
installs independently and closed out steps 5-8 itself rather than trust the claim on sight
(the ledger still showed all 5 pending when first checked, which is what triggered the
independent verify instead of a same-turn "done").

**Skills, versions, staged packages:**
- `daily-brief` v2.12 (commit fd9bd17, "v2.11->v2.12: drop 'market update' trigger")
- `insurance-renewal-review` v2.0 (commit 5953732, "text-layer triage, quoted-vs-realized
  check, named-insured-by-location reconciliation, HTML dashboard")
- `listing-agreement-qc` v1.2 (commit 8ae16b5, "REPO-FIRST capture of previously-uncaptured
  cache-only skill")
- `register-scheduled-task` v2.12 (commit 655c346, "a bounded pause must register its resume
  per fleet, same session/surface/pass")
- `settlement-basis-extraction` v1.0 (commit 9ca7a2f, first install -- brand new skill)

**Path.** package-and-stage-skill Entry point A (this session packaged fresh via
`tools\package_skills.py`, not a handoff) -> staged to
`ora-skills\_staging\2026-08-21_batch5-reimport\` -> handed to Cowork via Entry point B for
the Save-skill clicks.

**Pre-check (all green).** None are plugin members (`plugin_of` = None for all 5). Repo tree
clean on all 5 dirs before packaging. Packager exit 0 on all 5: forward-slash entries, `name`
== dir, description within the 1024-char limit -- **`insurance-renewal-review` packaged at
exactly 1024/1024 chars, zero margin before a future one-character addition silently fails
import** (flagged to Gabriel, not edited). `daily-brief` (target-markets.json) and
`listing-agreement-qc` (tools/ora_doc_qc.py) are SHARED_ROOT_DEPS consumers; `pending_reimport.py
shared-deps` read all-in-sync before packaging, no CACHE-AHEAD/DIVERGENT direction conflict.

**Post-install verify -- 5/5 skills, all files, and every cache directory was REBUILT, not
overwritten.** Directory CreationTime moved to match LastWriteTime for all 5 (17:19:31,
17:19:31, 17:19:34, 17:19:37, 17:19:39 ET respectively -- staggered a few seconds apart,
consistent with one sequential batch of Save-skill clicks), versus their pre-click
CreationTimes of 8/17 or earlier -- the same directory-recreation discriminator used for
`acquisition-proposal-generation` earlier today. All shipped files byte-matched the repo
(raw SHA256, no EOL normalization needed). Both shared deps confirmed: `daily-brief`'s
`target-markets.json` and `listing-agreement-qc`'s `scripts/ora_doc_qc.py` both hash-identical
to their repo-root/tools sources.

**`main.log` unavailable as corroboration on this machine** (same standing gap recorded in
today's earlier `acquisition-proposal-generation` entry -- no `SkillsPlugin` activity logged
since 2026-08-20 20:51:03). Directory-recreation timestamp used as the first-hand substitute,
consistent with that entry's documented fallback.

**Ledger.** `pending_reimport.py clear <skill>` run for all 5, each only after this append
returned exit 0. Ledger entries added later in the session for other work (`deal-execution`,
`estoppel-request-generation`, `lease-abstraction-pipeline`, `title-exam-abstraction`,
`package-and-stage-skill`) were left untouched -- out of scope for this task.

**Staging archived.** `_staging\2026-08-21_batch5-reimport\` (including the Cowork session's
own partial-verification scripts) moved to `_archive\2026-08-21_batch5-reimport\`, nothing
deleted.

## 2026-08-21 -- dirty-tree-triage: ora-skills `_staging\repo-first-rescue\` + `_staging\session_outputs\lease-addendum.skill` archived, all 8 items confirmed superseded

Two undated staging folders flagged by a 2026-08-21 Cowork session (no manifest/event_log signature) were triaged file-by-file against `ora-skills` git history. All 17 files in `repo-first-rescue\` (7 skill trees: exception-detection, insurance-renewal-review, lease-addendum, lease-form-qc, listing-agreement-qc, masterlease-jurisdiction-rebase, package-and-stage-skill) hash-matched an exact prior commit already superseded by later work — notably masterlease-jurisdiction-rebase's v1.1.2 content matches commit `ea9dddf`'s own "Code-surface close-out" reconciliation of a Cowork-hand-edit, and package-and-stage-skill's mislabeled "v1.20" draft is the exact stale-mirror-clobber incident already documented in the current v1.21 Changelog. `session_outputs\lease-addendum.skill` is byte-identical to both current repo HEAD and the already-installed AppData synced mirror — a spent package missing only its event_log confirmation line, not its content. No live or uncommitted work found in either folder. Archived (never deleted, Hard Invariant 6) to `_archive\2026-08-21_repo-first-rescue-triage\`, structure preserved. Repo verified git-clean on package-and-stage-skill and all 6 other touched skill dirs before and after.

## 2026-08-21 -- repo-architecture-review: cross-repo audit filed OI-197 through OI-201, remediation started

Cowork session ran `repo-architecture-review` across all 10 ZeOoba repos (local
clones: ora-skills, oxford-command-center, ora-pm, AAOS, website-canonical;
READMEs via `gh api`: ora-cowork-watchdog, BrainVault, ora-claude-config,
Claude-Guru-Ooba-; Internal-Accounting-App has no documentation at all). Filed
5 new items via `allocate-oi-id.py`: OI-197 (circular monitoring dependency
across 5 scheduler substrates), OI-198 (ora-cowork-watchdog README describes an
unbuilt systemd producer path), OI-199 (Internal-Accounting-App undocumented,
uncloned -- the highest financial-consequence repo, structurally blind to this
audit), OI-200 (stray third writable clone `oxford-command-center-1`, plus 2
unpushed commits on the primary including a tax recapture absent from every
mirror deploy since 08-17), OI-201 (ora-pm README stale on the billing/deploy
path). `check-open-items-duplicate-ids.py` confirmed zero duplicate rows/
sections. Tracker commit: `6985b46` on `feat/model-canary-probe-step25`.

Also surfaced, not yet actioned: both scheduler fleets have read `EN=OFF`
since 2026-08-17 (needs Gabriel's decision, not a unilateral resume); ora-pm
monthly billing still has no trigger anywhere, next billing date 2026-09-01
(new unattended automation on a money-moving path -- needs explicit
confirmation before registering).

A Code session picked up remediation same-day per the audit's handoff brief:
committing the tracker, then working the punch list (A-E) and five workflow
optimizations (WO-1 through WO-5).

## 2026-08-21 — acquisition-proposal-generation v3.1 INSTALLED (Save-skill click confirmed, not merely committed)

**What happened.** Gabriel clicked **Save skill** in Cowork on the staged
`acquisition-proposal-generation.skill` package and confirmed it in-session at
**2026-08-21 16:46 ET**. This entry records the CLICK, not the upstream repo commit —
the repo commit (`fc78d55`, 2026-08-21 16:31:50 -0400, "Add acquisition-proposal-generation
skill v3.1") is evidence the skill was authored, never evidence anyone installed it.
First install of this skill; it is new, not a revision of a previously-installed version.

**Path.** package-and-stage-skill v1.21 Entry point B (pre-packaged install, no repackaging).
Package built by an earlier Code session at
`ora-skills\_staging\2026-08-21_acquisition-proposal-generation-reimport\`.

**Pre-check (all green).** Existence ASSERTED, not inferred: 439,052 bytes, mtime 16:39:59.
SHA256 `1105ff284549d99fd378a3f3c3165610c0791a666f620f3530ded6b9609bd4d6` — matched the
handoff's expected hash, and the copy staged into session outputs re-hashed identical.
5 zip entries, all forward-slash, no directory records, expected file set exactly.
All 5 packaged entries byte-matched the current repo copies. Frontmatter gate:
`name` == dir, description 966/1024. `plugin_of` = None (standalone path correct).
Repo tree clean. Not a SHARED_ROOT_DEPS consumer.

**Routed to Cowork Save-skill deliberately.** 5-file skill (`SKILL.md`, `scripts/build.js`,
`scripts/photos/{1100_rarig,55_newplant,9050_redbranch}.jpg`). Desktop Settings →
Capabilities was explicitly ruled out per the 2026-07-11 subfolder-drop bug — that path
would have landed SKILL.md alone and silently discarded the generator.

**Post-install verify — 5/5 files, and the directory was REBUILT, not overwritten.**
The cache mirror at
`…\skills-plugin\583f08bc-…\a6ad2c61-…\skills\acquisition-proposal-generation\`
carries all five files, each hashing MATCH against the repo. Decisive signal: the
directory's own **CreationTime moved to 16:46:25** (from 16:21:45 pre-click), with every
file created at 16:46:25 — a genuine platform tear-down-and-re-download. A
`sync_appdata_mirror.py` content overwrite replaces file bytes in place and leaves the
directory's CreationTime untouched, so directory re-creation is the discriminator.

**Evidence caveat, recorded deliberately (v1.13 doctrine).** The pre-click state was
*contaminated* and would have read as "already installed" to a careless pass: `ListSkills`
already returned the skill enabled at v3.1, and all 5 cache files already hashed identical
to the repo. Both were untrustworthy — the pre-commit mirror-sync hook had overwritten the
cache files at 16:31:01–16:31:09 (before the 16:31:50 commit), which is the
hash-match-by-construction case, and the account-side v3.1 description was consistent with
a 16:21:45 *pre-commit* build whose contents the hook had already erased locally. The
ledger still listing the skill pending, plus the absence of any corroborating sync cycle,
is what correctly kept this on the install path.

**`main.log` was unavailable as corroboration on this machine.** `main.log` has not been
written since 2026-08-20 20:51:03 ("going down for update"); there is no 2026-08-21
`SkillsPlugin` activity in any log file in `%APPDATA%\Claude\logs`. Step 2's normal
Delta→Sync-complete corroboration could not be obtained, so the directory-recreation
timestamp above was used as the first-hand substitute. **Standing consequence: while the
desktop build is not writing main.log, the step-2 short-circuit gate cannot be satisfied
at all — every skill will read as un-corroborated, and cache-directory CreationTime is the
fallback discriminator.**

**Ledger.** `pending_reimport.py clear acquisition-proposal-generation` run only AFTER
this append returned exit 0. The other 5 pending entries (daily-brief,
insurance-renewal-review, listing-agreement-qc, register-scheduled-task,
settlement-basis-extraction) were left untouched.

**Discrepancy surfaced, not repaired.** The dispatch named 8 other pending skills; the
ledger holds only 5. `debt-management`, `lease-addendum`, and `loi-generation` are NOT in
`_staging/PENDING_REIMPORT.md`. Reported, not acted on — out of scope for this task.

## 2026-08-21 -- MEMORY.md archival pass, 918B WARN breach cleared (Automation Audit R17, Gabriel-approved)

Rev 17 of the ORA Automation Audit flagged MEMORY.md at 22,418B, 918B past the
21,500B WARN runway marker. Gabriel chose "archive stale entries now, with
ref-repair" over leaving it or splitting the index.

Archived 4 entries, each verified genuinely closed/superseded and checked for
inbound references before moving:
- `reference_portfolio_json_notion_seed_fallback_regression.md` (FIXED 08-09, 0 inbound refs)
- `reference_settings_json_enabledplugins_skilloverrides_attribution_2026-08.md` (resolved, 0 inbound refs)
- `project_broker_pipeline_blobs_v1_outage_2026-08-04.md` (fully resolved 08-16, 0 inbound refs)
- `reference_cc_snapshot_refresh_dq_flag_alert_is_count_not_severity.md` (FIXED 08-11, 2 inbound refs in
  `open-items-tracker.md` -- one `[[wikilink]]`, one literal markdown path link)

All 4 moved to `_archive/<name>_archived_2026-08-21.md` per the archive-not-delete
policy (memory-policy.md section 4) -- full prose preserved, nothing deleted.
Corresponding lines removed from MEMORY.md's index. The one literal-path link in
`open-items-tracker.md` (line ~6960, which would have broken since it pointed at
the file's pre-move location) was repaired to point at the new archived path; the
adjacent `[[wikilink]]` reference (name-based, doesn't break on a file move) was
annotated with the same archived-path note for a future reader's benefit.

**Result:** MEMORY.md 22,544B -> 21,437B (1,107B freed), back under the 21,500B
WARN marker with 2,963B of headroom to the 24,400B HARD ceiling. Zero orphaned
links introduced -- both inbound-ref sites in open-items-tracker.md were checked
and repaired, not just the index.

Full detail: [[project_automation_audit_rev17_2026-08-21]].

## 2026-08-17 -- dirty-tree-triage: 4 settled isolated commits landed on `~/.claude`; ora-skills and oxford-command-center left untouched

Ran the `dirty-tree-triage` skill against the default four checkouts. `website-canonical`
was clean. `~/.claude` had 17 dirty entries; 14 were settled and evidence-attributed,
landed via `commit_isolated_replacement()` in 4 isolated commits:

- `d27c51e` -- event_log.md + 3 new reference notes (Tax & Basis Register gap-check,
  insurance-renewal-review v2.0 / 9620 State 350, Metrics-History non-existence-check),
  attributed to sessions `8f27ce3a` (Tax & Basis import repo systemization) and
  `8d2515c6` (Insurance renewal review skill v2.0), both settled and not running.
- `2903132` -- rules.md Zapier status correction, corroborated by an already-committed
  event_log entry describing the same fix.
- `39c7f35` -- INDEX_reference.md + reference_ora_pm.md (ora-pm BETA status + N+1
  delinquency-check timeout finding). No corroborating session found in `list_sessions`
  -- reported UNATTRIBUTED per triage doctrine, but settled (mtime unchanged across two
  checks, ~9h stale).
- `324cb73` -- maintenance/_state FleetPause restore ledger + its debug-script archive +
  the `ora-routine-pause-resume-08-21` one-time task folder, attributed to session
  `cd9e6e4e` (Pause routines until Friday 5 PM).

**Left untouched, contested/live:** `MEMORY.md`, `open-items-tracker.md`, and the new
`project_ora_doc_qc_shared_module_pr48_2026-08-17.md` -- mtime moved BETWEEN two checks
made ~4 minutes apart (20:31:19->20:35:18 on MEMORY.md), and session `local_ceb1bb01`
("Retrofit listing/lease QC onto shared module", PR #48) showed `isRunning: true` mid-triage
before its PR merged. Both `MEMORY.md` and `open-items-tracker.md` are also jointly edited
by session `local_bd6f4916` (PR #137 merged, closing OI-184) -- multi-session collision,
not something this skill force-resolves. Leave for the next session to reconcile.

**ora-skills:** single-writer check (step 7) caught the repo mid-merge -- HEAD moved to
`5f8b65b` (PR #48 merge) and a brand-new `_archive/2026-08-18_superseded_pre_merge_untracked/`
appeared between the initial scan and the attribution pass, with `tools/ora_doc_qc.py`'s mtime
seconds old. Stopped per doctrine; nothing touched. Pre-existing dirty entries there
(`_archive/2026-08-17_item1-reimport-prep/`, `_archive/2026-08-17_register-scheduled-task-v2.10/`,
`pma-qc/`) still need a fresh triage pass once the merge settles.

**oxford-command-center:** `data/snapshots/portfolio.json` modified-tracked, mtime settled
(~9h stale), but branch is `ahead 1, behind 1` of origin -- real divergence, out of this
skill's scope per its own Boundaries section. Also this file is documented
([[reference_command_center_snapshot_is_tracked_not_ignored]]) as normally auto-committed by
its own tooling; reported rather than force-committed, since a 9h-stuck auto-commit plus a
divergent branch together read as an anomaly worth a human look, not a mechanical isolate.

Net: 4 clean isolated commits, 0 files force-resolved, 2 repos correctly left alone on
evidence (one live merge, one branch divergence + tooling anomaly), 1 file cluster correctly
reported as still-contested rather than guessed at.

## 2026-08-17 -- Tax & Basis Register gap-check: 5 remaining priority-1 findings + entity/exchange index filed

Code-surface session, gap-check pass after a concurrent session (`3f365fd1`
and others) scoped its own Code-side work on the same 2026-08-17 "Tax &
Settlement systemization" handoff narrowly to skill authoring +
Metrics-History fact-check + the 2 data-gap items (OI-187/OI-188) it hit
along the way. Verified `settlement-basis-extraction` (Task 1) was already
committed and validated -- no action needed there. Confirmed 5 of the
handoff's 6 priority-1 findings, plus the cost-seg memo correction, were not
yet anywhere in `.claude`; filed them:

- [OI-189](open-items-tracker.md#OI-189) -- 1100 Rarig: $1,803,121.50 settlement
  capitalized with zero land allocation
- [OI-190](open-items-tracker.md#OI-190) -- McGregor Lane parcel on the
  07/02/2024 settlement but missing from the 2024 Form 8824
- [OI-191](open-items-tracker.md#OI-191) -- 1100 Rarig $217,346 Section 481(a)
  adjustment, no Form 3115 on file
- [OI-192](open-items-tracker.md#OI-192) -- 5600 Sunnyside title-chain gap
  (1992 individual owners vs. 02/2025 LLC seller, no intervening conveyance
  documented)
- [OI-193](open-items-tracker.md#OI-193) -- `2026-07-28_CostSegDispositionPortfolio_Memo_v02.docx`
  Table 1/2 arithmetic errors ($200K understatement); flagged only, not
  edited -- the memo lives in a non-Claude OneDrive business folder

Also added [[reference_tax_settlement_entity_and_exchange_index_2026-08-17]]
(6 entity EINs, the EX-12-*/IPX 1031 exchange-number index 2015-2026, and the
Fenton Street LLC 2024 status-change note -- it exited rental-flow-through
holding via five 12.5% zero-gain transfers but federal K-1s still print its
old 62.5%, EXCEPTIONS tab defect #9, uncorrected).

**Editing discipline:** `open-items-tracker.md` and `MEMORY.md` both carried
a live same-file-collision warning (session `3f365fd1` working, 4 others with
recorded edits in the same dirty checkout) at edit time. Both edits were
kept strictly additive (new rows/lines only, no existing content touched) and
were NOT committed -- the working tree is jointly authored right now and
committing risks co-mingling another session's uncommitted hunks. Whoever
next reconciles this checkout should fold these rows in along with the rest
of the outstanding WIP.

**Still not located anywhere in `.claude` as of this pass:** the Fenton
Street K-1 62.5%-vs-actual-0% defect is now captured only inside the entity/
exchange reference file above (folded in rather than given its own OI row,
since it's a return-preparation correction, not an open investigation), and
Task 4's remaining flag-only items (Fenton Street TY2025 MD return image-only
scan, 7658 Fishel needing a Franklin County re-pull, no Form 4562 for 3
entities) were not filed by either session -- still open.


---

*Entries at and before “2026-08-17 -- Tax & Basis Register gap-check: 5 remaining priority-1 findings + entity/exchange index filed” rolled over 2026-08-22 to [_archive/event_log_2026-08-22.md](_archive/event_log_2026-08-22.md) per memory-policy.md's rollover rule.*
