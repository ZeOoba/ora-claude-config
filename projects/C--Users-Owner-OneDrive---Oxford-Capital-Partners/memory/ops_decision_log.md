---
name: ops_decision_log
description: "Standing log of small recurring yes/no operational calls (existence checks, counts, config confirmations) that otherwise get re-litigated from scratch each session. One row per decided question — check here before re-deriving."
metadata:
  node_type: memory
  type: reference
  originSessionId: local_3a091e05-9759-4627-93c2-c948e6c29e71
  modified: 2026-09-12T22:00:15.401Z
---

**Purpose:** a lightweight companion to [deal-decision-ledger.md](deal-decision-ledger.md) (which
is scoped to deal PASS/SKIP/DROP/PARK/CLOSE/TERMINATE calls) for smaller *operational* yes/no
questions — "does X exist," "how many of Y," "is Z still true" — where a session burns real effort
re-deriving an answer another session already nailed down. Add one entry per decided question;
update in place (don't duplicate) if a later session re-confirms or overturns an answer, and note
the overturn explicitly rather than silently replacing.

## Log

### 2026-09-12 — How does the morning fleet host stay awake overnight?
**Answer (Gabriel, via AskUserQuestion):** plug the laptop in overnight, and set lid-close on AC to "Do nothing" (`powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0` + `powercfg /setactive SCHEME_CURRENT`, which Gabriel runs; Claude does not change power settings). DC behavior is unchanged (DC sleep 3h stays per the 2026-08-12 ruling).
**Evidence:** on the 09-12 late wake (666 min), Kernel-Power 506 showed standby entries at 09-11 23:38 and 09-12 01:38 with LidOpenState=false and BatteryRemainingCapacityOnEnter falling (76,103 → 55,409 → 51,270 mWh). The laptop was on battery with the lid closed. The existing 04:45 `ORA Claude Desktop Wake-and-Launch` wake timer did not overcome it.
**Rejected:** lid open with no config change (fragile), accepting late mornings, and moving AM tasks to an always-on host (unscoped project).
**Follow-up:** `ora-health-guard` A.0b's run-time BatteryStatus annotation is wrong for this case; the fix is spawned as task_036d0e55. Once LIDACTION AC=0 is applied, A.0b could regression-check it alongside STANDBYIDLE.

### 2026-08-16 — What is the owner-outreach touch ladder, channel, and dispatch model?
**Answer (Gabriel, via AskUserQuestion), ratified as `outreach-ratification.json` OR-2026-001:**
- **Ladder:** T1 letter → T2 **CALL** (top slice) → T3 letter (+90d) → T4 letter (+180d). T5 call. Only T1/T3/T4 render; calls are Notion-tracked and must NEVER consume a mail touch.
- **Channel: postal ONLY.** Cold email is ruled out permanently. Not merely policy — county records carry **no email addresses**, so it is unaddressable without a skip-tracing vendor; and cold volume from `ggoldberg@oxfordra.net` risks the single mailbox every firm automation depends on.
- **T3 names no price.** Creative structures (1031 runway, IRC §453 carry-back, leaseback) deploy on the CALL only. This supersedes the 2026-06-15 creative-structures doc, which scoped them to a "T3 specific-offer letter." Because no letter carries a number, the whole ladder stays inside the generate-only carve-out with no per-letter approval.
- **Dispatch: Gabriel hand-addresses everything**, ~50/wk (`--wave-cap 50` standing). He was offered a print-mail vendor and a hybrid and chose full hand-addressing, accepting ~3–5 hrs/wk indefinitely. **"200 qualified leads/month" = 200 letters dispatched**, not 200 net-new parcels.
- **T2 call slice:** top 5–8/week by Screen Score (tiebreak P1 %). A universal call touch at 50 letters/wk would be ~48 calls/wk, which does not fit alongside addressing.
- **Targeting:** all 10 canonical clusters incl. Louisville. Metro `Other` deliberately NOT ratified — it holds.
Any change to template text, metros, cadence, wave cap, signature, or channel is a re-ratification trigger; template SHA-256s hard-fail the pack build.

### 2026-08-16 — Does a malformed date in mail-log.csv hold the parcel, or mail it?
**Answer (Gabriel, via AskUserQuestion): HOLD, and alarm loudly in the summary email.** This **reverses** the original documented behavior (`return False  # malformed date in log: fail open, letter goes out`). Rationale: mailing an owner twice is unrecoverable, skipping a wave is not — but a *silent* hold would quietly shrink every wave if the log were corrupted, and read as normal attrition. The driver now emits an `[ALARM]` line naming the affected parcels, and the task spec requires that line to LEAD the summary email verbatim.

### 2026-08-16 — Should the cold-outreach carve-out be written into CLAUDE.md's Hard Invariant 1?
**Answer: NO — dropped; it lives in `session-context.md` only.** Initially approved as a CLAUDE.md edit, then withdrawn on two findings. (1) Under the hand-address ruling **the engine never sends anything** — Invariant 1 bans *sending*, and `owner-outreach` had already generated full packs DRAFT-ONLY for two months without per-letter approval, so the autonomy the carve-out would buy already existed. `outreach-ratification.json` is a *tightening*, not relief. (2) CLAUDE.md is ~9 words from its hard FAIL gate (see the word-budget gotcha in `event_log.md` 2026-08-16), so the edit would have forced an unrequested one-in-one-out trim of the governance file. The `allow-config-write` token minted for the edit was revoked when it was cancelled.

### 2026-08-16 — Ratify the 2026-07-27 off-market master vintage so the held net-new owners can promote?
**Answer (Gabriel, via AskUserQuestion): RATIFY 2026-07-27.** He was explicitly offered "ratify AND widen STALE_DAYS" and **declined the threshold change** — same posture as the 2026-07-14 precedent below.
**Context.** The master WAS refreshed on 2026-07-27 (the P1 outreach plan's claim that it was "frozen at 2026-06-10" is WRONG — `_latest_master()` globs by **version number, not date**, and correctly selects `20260727_AllMarkets-OffMarket-Master_v09.xlsx`). Because the 06-10 ratification lapses automatically the instant the vintage changes, every run since has HELD. The 2026-08-10 summary email reported verbatim: "Notion Owner Outreach Queue upsert: **HELD** … No pages created this run", ledger commit SKIPPED, **83 net-new owners** withheld (Columbus 35, Cincinnati 40, Grand Rapids 4, Des Moines 4). Live re-run 2026-08-16: 18,389 scanned / 7,438 t2plus / 5,290 floor-clear / 208 motiv-ok / **187 promoted** / Tier-0 coverage 100% / RECOVER 0.
**Mechanism.** Added a dated per-vintage entry to `ora-owner-outreach-queue-refresh/SKILL.md` STEP 1 STANDING RATIFICATIONS; struck through (did not delete) the superseded 06-10 entry per that block's own audit rule. Lapses automatically when the vintage changes again.
**Companion ruling same session — mail history: NONE of the 06-15…08-10 packs were ever physically mailed.** Seeded `mail-log.csv` header-only (`parcel_id,mailed_date,touch_num,pack`) so the 21-day cadence gate starts clean and suppresses nobody incorrectly. Everything to date was draft-only.
**Standing lesson:** the pipeline was never broken — it asked a question every Monday and the answer sat unread. A held automation that emails a QUESTIONS FOR GABRIEL block is invisible unless someone reads the mail; consider surfacing HELD state in the daily brief.
Related: [[project_ora_strategic_constraints_2026-08-16]], [[project_owner_outreach_stale_guard_watch]].

### 2026-07-28 — ora-appsec-sweep confirmed running below the CLAUDE.md never-below-Fable floor for security-gate code (since 2026-07-24) — escalate now or wait?
**Answer (Gabriel, via AskUserQuestion): accept the gap for now, wait for the Wednesday 2026-07-29 re-canary.** Context: `ora-appsec-sweep`'s scheduled session itself runs on CC/MCP's server-pinned model (confirmed `claude-opus-4-8` via the 2026-07-24 transcript canary; frontmatter `model: fable` is inert on this fleet — see [[reference_scheduled_task_model_standard]]), which is below-floor for security-gate code per CLAUDE.md. No config-level fix exists on this fleet (filed as [anthropics/claude-code#81408](https://github.com/anthropics/claude-code/issues/81408)).
**Ruling: no escalation, no surface change.** Reasoning: the task's actual security review work is dispatched to the `security-auditor` Agent, which IS correctly Fable-pinned per the task's own v1.3 design (`CLAUDE.md`'s floor is carried by that dispatch, not the orchestrating session) — only the orchestrating session itself runs below-floor, and that session's job is report-only/read-only (secret scan, CVE audit, OWASP checks), not itself making security judgments. `ora-appsec-siteexposure-canary-recheck` (one-time, 2026-07-29 15:00 ET) will produce the first genuine post-Opus-5-rollout data point for this task; revisit after that fires rather than acting on stale 07-22/07-24 data.
Related: [[reference_scheduled_task_model_standard]] (full drift history), [[reference_fleet_throttle_skip_catchup_burst]].

### 2026-07-25 — Should oxford-command-center's lease-snapshot drift check's >25% anomaly floor gate on raw id-level removals or business-key-reconciled removals?
**Answer (Gabriel, via AskUserQuestion): keep the raw id-level gate — no code change.** PR #234
(`ff23bd2`) added business-key pairing (propertyKey+unit+tenant) to `computeDrift()` in
`scripts/lease-snapshot-drift-check.ts`, which could distinguish a pure id-rekeying event from a
genuine mass disposition. The floor could have been changed to gate on the business-key-reconciled
`genuinelyRemoved` count instead of raw `removedIds`, which would let a future id-scheme migration
(like PR #232, which caused the 2026-07-24 re-baseline incident) write through automatically instead
of requiring a manual `--force`.
**Ruling: don't.** The floor stays gated on raw id-level removals — any future id-scheme change will
require a manual `--force` again, same as this week. Reasoning given: trusting the newer business-key
pairing logic to gate a safety-critical write path would mean a blind spot in that logic (the review
of PR #234 surfaced one candidate — an unescaped `" | "` delimiter in `businessKey()` — that scored
40/100, real in principle, not observed in live data) could silently misclassify a genuine mass
disposition as safe rekeying and let it through unattended, defeating the exact failure mode the
floor exists to catch. The `--force` path already prints the business-key breakdown
(re-keyed/genuinely-new/genuinely-removed) for the human forcing through, so no information is lost
by keeping the gate itself simple.
Related: [[project_lease_snapshot_id_rebaseline_pending_2026-07-24]] (the incident this decision
followed), PR #234 review comment (no code issues found, scored below the 80-point bar).

### 2026-07-12 — How many `.skill` packages are staged for Settings → Capabilities import?
**Answer: 10, not 4.** communication-intelligence, market-monitor, rent-comp, tax-appeal,
maintenance-analytics, deal-execution, lease-abstraction-pipeline, psa-reconciliation,
oxford-cc-strategic-audit, automation-health-monitor — per the 2026-07-08 remediation record. No
more recent record narrowing this to 4 was found. Use 10 as current until Gabriel confirms
otherwise at the actual Settings → Capabilities screen (the click itself is manual-only, per Hard
Invariant scope — no session should attempt the import).
Source: 2026-07-12 Punch-List Review, Notion Ops Hub page `39b6ecd8`, item 7.

### 2026-07-12 — Does a "Stale-Guard Watch" standing note exist?
**Answer: no, as of 2026-07-12, it did not exist as a standing document** — despite being
referenced as if it already existed in that evening's punch-list task prompt. Two notes now exist
as of the same day: [[project_owner_outreach_stale_guard_watch]] (scoped tracking ticket for the
specific ora-owner-outreach-queue-refresh recurrence check, self-archiving after the 2026-07-13
Monday-fire data point) and
[[reference_scheduled_task_staleness_guard_trips]] (standing pattern log for the false-
positive guard-trip class generally, across any task). Check both before re-investigating a future
staleness-guard trip.

### 2026-07-12 — Tenant DB dedup: which remediation option per category?
**Answer (Gabriel, via AskUserQuestion): A=Archive, B=Keep newest/archive rest, C=Re-link via HubSpot
cross-reference, D=Bulk-archive confirmed phantom batch, leave unconfirmed singletons for
individual review.** Full category detail and rationale in
[[reference_tenant_db_completeness_gap]]. This satisfies the standing guardrail requiring
Gabriel's category-by-category call before any Tenant DB writes — execution authorized.

### 2026-07-14 — Is the 2026-06-10 off-market master vintage current enough to promote to Notion?
**Answer (Gabriel, via interactive elicitation): Current — unblock next run.** No rescreen. The
`ora-owner-outreach-queue-refresh` 2026-07-13 fire held Notion page-creation/`--commit` on a
genuine (not false-positive) STALE trip — master content vintage 2026-06-10, 33 days old — and
emailed a QUESTIONS FOR GABRIEL block. Gabriel ratified the master as current rather than
choosing "rescreen first" or "widen the threshold." **Scope: this is a one-time ratification for
the current cycle, not a standing threshold change** — he did not pick the adjust-threshold option.
**Mechanism gap CLOSED 2026-07-14 (same day).** The halt-and-ask logic turned out to live entirely
in SKILL.md STEP 1 prose (interpreted by the Cowork agent each run), not in `owner_outreach_weekly.py`
— the script itself is WARN-only since the 2026-07-12 relax. Added a **STANDING RATIFICATIONS**
clause to `ora-owner-outreach-queue-refresh/SKILL.md` STEP 1 (v1.2 → v1.3): the guard now checks
the reported master vintage against a dated, per-vintage ratification list before halting — vintage
2026-06-10 confirmed CURRENT by Gabriel on 2026-07-14 is entered there. Proceeds without re-asking
while the reported vintage stays 2026-06-10; the halt-and-ask fires again automatically the instant
the vintage changes to anything else (a real refresh, even a still-stale one). `STALE_DAYS` and the
default halt behavior are unchanged — nothing was silently widened or disabled. Edited directly
(the file is plain OneDrive prose, not git-tracked or registry-spliced — SKILL.md content is
authoritative per [[reference_cc_scheduler_filepath_mechanism]] regardless of which surface writes
it). See [[project_owner_outreach_stale_guard_watch]] for full detail and the Case 2 true-positive
analysis this decision follows from.

### 2026-07-16 — Should CLAUDE.md's Skill tie-breaks section propagate to the 4 known "ported copy" files?
**Answer (Gabriel, via AskUserQuestion): No — leave as-is.** Investigated before asking: none of the
4 files (`Claude Command Center Code/CLAUDE.md`, `Claude_Workspace/01_Workspace/CLAUDE.md`,
`Claude_Workspace/01_Workspace/oxford-site/.claude/CLAUDE.md`, `Obsidian/BrainVault/CLAUDE.md`)
actually carry the Skill tie-breaks section today — they're narrowly-scoped project/vault context
files, not verbatim doctrine mirrors, despite the master CLAUDE.md's scope-note language ("true on
EVERY surface... ported copies omit only Engineering OS"). One (`Claude_Workspace/01_Workspace/
CLAUDE.md`) is an explicit "THIN POINTER" that states it intentionally avoids duplicating doctrine
and points to the master file instead — adding content there would contradict its own design. The
propagation mandate that DID apply for real (Hard Invariant 3 / confidentiality, the E. Fulton
Obsidian-copy fix) is invariant-specific, not a general rule that every CLAUDE.md-named file mirrors
every section. **Scope: this is a ruling about the Skill tie-breaks section specifically** — a future
Hard Invariant change still needs the per-file propagation check these 4 files got during E. Fulton.

**REVERSED same day (Gabriel, via AskUserQuestion, later 2026-07-16 session):** shown the ruling
above, Gabriel chose "Reverse it — propagate for real," including into the thin-pointer file. Done:
the bullet was added to all 4 files (a new "## Skill tie-breaks" section in each, since none carried
it). Git/PR reality varied by location — `Claude Command Center Code/` and `Claude_Workspace/
01_Workspace/` are not git repos (direct edit only); `oxford-site/.claude/`'s parent repo has a
corrupted `.git` (missing `refs/` entirely — direct edit only, flagged separately, see
[[reference_workflows_dir_single_writer_gap]]-adjacent finding in event_log.md); only
`Obsidian/BrainVault` is a working git repo with a GitHub remote, where the change shipped as
[ZeOoba/BrainVault#2](https://github.com/ZeOoba/BrainVault/pull/2) off an isolated branch (that repo
had ~1,100 unrelated uncommitted paths already sitting in its working tree — untouched, flagged
separately as a likely auto-backup-hook failure). **This entry supersedes the "No — leave as-is"
ruling above; kept for the record rather than deleted, per this log's own append-only convention.**

### 2026-07-12 — Is the fleet's shared Python 3.13 environment missing packages?
**Answer: no, as of 2026-07-12** — `python-docx`, `openpyxl`, `pandas`, `reportlab`, `pypdf` all
verified installed at the pinned versions (`pip show`, live machine check) against
`scheduled-tasks\_shared\python-requirements.txt` and the sibling
`Investment Candidates -- 2026\requirements.txt` (same interpreter, both frozen 2026-07-12). The
2026-07-05→07-12 reactive-install gap that caused this is now closed procedurally too — see
`MIGRATION_RUNBOOK.md` B1.3a (added 2026-07-12).

### 2026-07-17 — Should `scheduled-tasks/_archive_2026-05-31_orphans/ora-fulton-deadline-alert/SKILL.md` be tracked (or redacted-and-tracked) now that `.gitignore` opts in archived task specs?
**Answer: no — leave excluded, untracked, local-disk-only. Decided, not deferred.** During the
2026-07-17 55-file historical backfill (see [[reference_commit_provenance_guard]]'s sibling
`.gitignore` work), this file was the one exclusion out of 55: it carries raw, granular E. Fulton
PSA terms from while that deal was still live-confidential — $4M closing price, $200K deposit
wired to a named title company, named counterparties (McGrath, August Mack, Vector Security,
Whitehall CCD). Checked `confidential-terms.json`'s live `e_fulton` record before deciding (not
assumed from memory): declassified 2026-07-09, but **"over a stated recommendation to keep it
confidential during the live lender discussion"** — ORA is in an ACTIVE lender note/foreclosure
discussion on this property right now, with confirmed TCE/chlorinated-solvent contamination.
Declassification authorized referencing the deal by name operationally, not publishing its raw
financial/DD terms — the precedent's own bar is "matching already-tracked memory files," and this
file exceeds it (none of these figures exist anywhere else in the tracked repo). Redaction was
considered and rejected: there is no clean secret-shaped token to substitute — the file's entire
content IS the sensitive part, so a redacted version would be a near-empty husk duplicating what
tracked memory files already say about the deal's existence/outcome. Re-scanned all 49 files that
WERE backfilled against the full `e_fulton` term list (SIJ, Nutis, Columbus Stamping, 3520, TCE,
chlorinated solvent, vinyl chloride — not just "fulton") before finalizing: clean, nothing else
leaked. **Do not re-open this without new information** (e.g. the lender matter actually closing)
— check here first.

### 2026-07-17 — Heritage Pool Supply `Monthly Rent`: workbook/Notion $8,540 vs. lease amendment Year-1 rate $8,710.80 — which is correct?
**Answer (Gabriel, in-turn): the current $8,540 figure is correct.** Flagged during
[OI-005](open-items-tracker-history.md#OI-005) (Heritage Pool row dedup) as a discrepancy against the
Year-1 escalation rate implied by the lease amendment, deliberately left uncorrected pending
Gabriel's call rather than silently overwritten. Gabriel confirmed the live figure stands — no
Notion or workbook write needed. **Do not re-flag this specific $8,540 vs. $8,710.80 delta**;
treat it as resolved, not as residual drift.

### 2026-07-17 — Should the Claude Code setup-audit cadence continue on its recent every-few-days rhythm?
**Answer (Gabriel, per the 2026-07-17 ROI-brief evaluation): no — freeze for 60 days (until
~2026-09-15).** Three read-only diagnostic sweeps landed in 8 days (07-09, 07-16, 07-17), each
producing small in-session fixes and a fresh tier of follow-ups — a self-sustaining meta-work loop
competing with the firm's #1 priority (acquisition velocity) for attention. No scheduled or
ad-hoc full setup audit before ~2026-09-15 unless triggered by an actual failure, not the calendar.
Does not affect the already-scheduled quarterly fleet review (2026-09-09) or any individual guard
probe (governor-drift, doctrine-integrity, etc.), which keep running as designed.

### 2026-07-17 — Is disambiguating "GitHub MCP connector vs. lighter Web Integration" worth investigating now?
**Answer (agent operational call, low-risk default — not a Gabriel ruling): no — closed/ignored
until it actually matters.** Zero present consequence; repo work runs fully via `gh` CLI on the
Code surface today. Revisit only if Cowork-side PR/CI visibility becomes a genuine, concrete
need — do not spend session time on this speculatively.

### 2026-07-17 — Does `ora-setup-review-closeout-recheck` (fires 2026-07-17 20:10 UTC) need any action beyond reading its output?
**Answer (agent operational call, low-risk default — not a Gabriel ruling): no.** It's a
self-contained one-time check of three other 07-17 gate conditions (task-integrity-guard
12:45 ET, automation-health-monitor beacon 11:05 ET, and the now-retired northridge-brockton
deadline). Read its output when it fires; no build, no registry mutation, no follow-up task
required either way.

### 2026-07-17 — Do Tier 3 (hooks/settings/plugin hygiene) and Tier 4 (memory/event-log hygiene) of the 2026-07-16 setup-review plan still need building?
**Answer (Gabriel, per the 2026-07-17 ROI-brief evaluation): no — deliberately DROPPED, not
deferred.** Only the Tier-2 acquisition-velocity items (deal-first weekly board, LOI-throughput
line, broker touch cadence) were carried forward into the 2026-07-17 implementation pass. Tier 3
and Tier 4 are meta-work on the tooling itself with no near-term payoff toward acquisition
velocity — do not "helpfully" pick them up from the 07-16 report's open-items framing; that
report's plan is superseded on this point.


### 2026-07-27 — Should the off-market master's Columbus tab use $150/SF or RCT v03 as its replacement-cost benchmark?
**Answer (Gabriel, in-turn, then reconciled same session): RCT v03 — the $150/SF instruction is
withdrawn.** Gabriel initially ruled $150/SF (matching what the `county-parcel-screen` tool already
used for the Columbus v04 screen). Before extending that to memory or other markets, the standing
2026-07-14 governor-level ratification was located (`project_replacement_cost_benchmark_unratified.md`:
"THERE IS ONE BASIS DENOMINATOR: RCT v03 ... if you find a second denominator, it is a bug") and
flagged as in conflict. Gabriel's recommendation on reconciliation, confirmed: revert to RCT v03,
not carve out a screening-only exception. `20260727_AllMarkets-OffMarket-Master_v08.xlsx` ships
Columbus on RCT v03 (Columbus LOW $229.65, conservative 35%-of-replacement threshold = $80.38/SF,
since Yr Built is unknown for the v04 source rows). v07 (the $150/SF build) is superseded, not
deleted. **Do not re-litigate $150/SF for Columbus** without new information (e.g., a GC/lender
quote specifically challenging RCT v03's Columbus figure) — treat the one-denominator rule as
holding here same as everywhere else. The other 8 markets remain on RCT v02 and were not touched
by this decision; that migration is separately open per the 07-14 ratification's own "stale
consumers" list, not new.


### 2026-07-28 — Columbus Suburban Construction (392 Morrison Rd): move-out or mis-staged HubSpot deal?
**Answer (Gabriel, in-turn: genuine move-out.)** Today's Daily Brief flagged a three-way
lease-expiration discrepancy — workbook and the HubSpot deal name both said 2026-08-31, Notion
said 2026-06-30, and the HubSpot renewal deal ("Columbus Suburban Construction — Lease Renewal
2026-08-31") was marked closed-lost 2026-07-25 with no `closed_lost_reason` and no notes.
Gabriel ruled it a genuine move-out, not a mis-staged deal. Executed same session: Notion Tenant
DB corrected (Lease Expiration 06-30 -> 08-31, Lease Status -> "Notice Given", matching workbook +
HubSpot; verified via re-query). AR $5,670.84 outstanding — move-out/collection email drafted via
`tenant-email` skill, NOT sent (Hard Invariant 1); signature entity left unresolved and flagged to
Gabriel, since 392 Morrison Rd is absent from `ORA_Property-LLC-Signature-Roster_v01.md` (a real
gap, not a lookup miss — full-file grep confirmed no "Morrison" or "392" entry). Loan data (the
"Banwick / Morrison Refi" Symetra loan lists Fairground Village Center LLC as counterparty) is a
plausible but unconfirmed signing-entity clue; do not use it to sign an executed instrument
without separate confirmation, per the roster's own Zettler/Banwick-vs-401-Sunburst caution.
**Follow-up:** confirm the Morrison Rd signing LLC and add it to the roster to close this gap.
