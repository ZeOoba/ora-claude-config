---
name: ops_decision_log
description: "Standing log of small recurring yes/no operational calls (existence checks, counts, config confirmations) that otherwise get re-litigated from scratch each session. One row per decided question — check here before re-deriving."
metadata:
  node_type: memory
  type: reference
  originSessionId: local_3a091e05-9759-4627-93c2-c948e6c29e71
---

**Purpose:** a lightweight companion to [deal-decision-ledger.md](deal-decision-ledger.md) (which
is scoped to deal PASS/SKIP/DROP/PARK/CLOSE/TERMINATE calls) for smaller *operational* yes/no
questions — "does X exist," "how many of Y," "is Z still true" — where a session burns real effort
re-deriving an answer another session already nailed down. Add one entry per decided question;
update in place (don't duplicate) if a later session re-confirms or overturns an answer, and note
the overturn explicitly rather than silently replacing.

## Log

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
[OI-005](open-items-tracker.md#OI-005) (Heritage Pool row dedup) as a discrepancy against the
Year-1 escalation rate implied by the lease amendment, deliberately left uncorrected pending
Gabriel's call rather than silently overwritten. Gabriel confirmed the live figure stands — no
Notion or workbook write needed. **Do not re-flag this specific $8,540 vs. $8,710.80 delta**;
treat it as resolved, not as residual drift.
