# Deal-Sourcing Funnel Upgrades — Design

**Date:** 2026-09-22 · **Lane:** L3 `/build` · **Owner:** Gabriel Goldberg
**Scope:** A (owner-outreach loop completion) + B (passed-deal re-marketing detection). C (loan-maturity data) is a vendor decision, not a build — see §C.

## Context (verified 2026-09-22)

- Outreach pipeline lives in `OneDrive…/Business/Investment Candidates -- 2026/` (not in the skill package, by design). T1/T3/T4 rendering exists (`--touch 1|3|4`); 70/70 ladder tests pass (`python test_owner_outreach_ladder.py`). Response capture exists (`log_outreach_response.py` → `outreach-responses.csv`, suppresses further letters for any outcome).
- `mail-log.csv` holds ONE release (50 × T1, 2026-08-24). Packs built 09-02, 09-07, 09-14 were physically mailed (Gabriel, 2026-09-22) but never logged via `--released`. `_oo_pack_manifest.json` is overwritten each build and now holds only the 09-14 pack — the 09-02/09-07 parcel lists must be reconstructed.
- No 09-21 pack exists: the LAMS task `ora-owner-outreach-queue-refresh` (`55 10 * * 1`) did not produce one.
- "A couple" of responses received, none logged (`outreach-responses.csv` absent).
- The ratified ladder (OR-2026-001) defines T2 = call at +30d, top slice 5–8/week. No call-sheet tooling exists. The 08-24 cohort reaches T2 on 2026-09-23.
- `ora-passed-deal-tracker` (CC/MCP, `30 6 15 * *`) watches Deal Sourcing Log passes/losses for recorded TRADES only; it never detects a passed deal returning to market or cutting price. LoopNet/CoStar/Crexi block automated fetch; broker blast emails in the Outlook inbox are the reachable signal.

## A. Outreach loop completion

### A0. Release reconciliation (one-time, data repair — precedes all A code)
1. Reconstruct parcel lists for the 09-02 and 09-07 packs: parse each pack DOCX for recipient mail name + site address, join to that date's `YYYYMMDD_Owner-Outreach-Queue_Phase1_v01.xlsx` on normalized site address → Parcel ID. Letter count must equal the DOCX letter count exactly; any unmatched letter halts the backfill (no partial log).
2. Add `--released DATE --manifest PATH` to `owner_outreach_weekly.py` so a release can be recorded against an explicit manifest instead of only the latest one. Existing behavior (no `--manifest`) unchanged.
3. Backfill with pack-build dates (09-02, 09-07, 09-14) unless Gabriel supplies actual mail dates. Guard: refuse to log a parcel+touch pair already present in `mail-log.csv` (idempotent re-run).
4. Log the received responses via the existing `log_outreach_response.py` (parcel + outcome from Gabriel).
5. Diagnose the missed 09-21 run (fleet-roster / LAMS run history) — report only; any re-registration goes through `register-scheduled-task`.

### A1. T2 call sheet — `build_t2_callsheet.py` (new)
- **Input:** `mail-log.csv`, `outreach-responses.csv`, queue workbooks, `outreach-ratification.json` (call slice bounds, `min_touch_gap_days`).
- **Eligible:** highest mailed stage = 1, days since T1 ≥ ladder t2 gap (30), no logged response, not already on a prior call sheet (`call-log.csv`, new: `parcel_id, sheet_date, outcome`).
- **Rank:** Score desc; ties by motivation (estate > delinquent > in-motion > none). Take slice upper bound (8).
- **Output:** `YYYYMMDD_Owner-Outreach_T2-CallSheet_v01.xlsx` — owner, mail name, mailing address, site address, metro, score, motivation, T1 date, blank Phone, Outcome dropdown whose values = `log_outreach_response.py` outcomes + `no-answer`/`left-vm`.
- Phone numbers are out of scope (paid skip-trace). Call outcomes other than `no-answer`/`left-vm` are logged through `log_outreach_response.py` (single suppression source of truth).
- Invoked by the weekly orchestrator after the letter pack; failure is WARN, never blocks the pack.
- No sends, no Notion writes by the script (orchestrating agent syncs as today).

### A2. Conversion report — `outreach_conversion_report.py` (new)
- Joins mail-log (mailed parcel×touch) × responses × queue metadata.
- Cuts: overall, by metro, motivation signal, score band (A/B/C tiers), touch, cohort week. Metrics: mailed, responses, warm (`responded`+`converted`), response rate, warm rate, converted.
- Banner `INSUFFICIENT SAMPLE (n=X)` while total responses < 10; no per-cut rates shown for cuts with mailed < 20.
- Output: markdown/HTML block appended to the weekly summary email on the first run of each month; CSV snapshot to `outreach-conversion-YYYYMM.csv`.
- Read-only; never changes scoring weights. Findings route to Gabriel for any county-parcel-screen weight change.

### A-docs
Update `ora-skills/owner-outreach/SKILL.md`: remove stale "T2–T4 pending" note, document A0 flag, A1, A2. Commit via `isolated-commit`.

## B. Passed-deal re-marketing detection

New **Step 3b** in `~/.claude/scheduled-tasks/ora-passed-deal-tracker/SKILL.md` (and mirrored into the ora-skills source if one exists), after the trade check:
- For each watch-list row (normalized address; deduped per existing rule), search the Outlook inbox (M365 MCP `outlook_email_search`) over the trailing 35 days for the street address and property name.
- On a hit: extract asking price if stated; compare to the row's last known ask and `ORA Max Defensible Price`.
- Flags: **RE-MARKETED** (hit, no/unknown price) · **PRICE-CUT x%** (ask < last ask) · **INSIDE-WALK** (ask ≤ Max Defensible — forces the email path even with zero trades).
- Output: new "RE-MARKETED PASSES" section in the existing email/Ops Hub post. Read-only: no Notion writes beyond what the task already does, no outreach drafts, no link-clicking.
- Guards: an email whose sender is ORA itself is ignored; address match requires street number + street name; ambiguous matches listed as UNCONFIRMED, never flagged INSIDE-WALK.
- Out of scope: retiring the LAMS twin (needs an on-device Cowork session).

## C. Loan-maturity data (decision, no build)
Vendor research: `scratchpad/mortgage-vendor-pricing.md`. Recommendation: one-month Reonomy pilot on Franklin OH; kill criterion < 40% maturity-date population on industrial parcels. Confirm mailing-use license before any purchased data feeds outreach. Gabriel's spend decision; would re-open the 2026-09-18 ruling in `county-parcel-screen` SKILL.md:174-176.

## Error handling
- Every new script: fail loud on missing inputs, non-zero exit; orchestrator treats A1/A2 failure as WARN.
- A0 backfill is all-or-nothing per pack.
- Suppression remains single-sourced in `outreach-responses.csv`.

## Testing
- TDD, extending `test_owner_outreach_ladder.py` style (plain-assert runner): manifest backfill idempotence + count-mismatch halt; call-sheet eligibility (30d gap, response suppression, prior-sheet exclusion, slice cap, ranking); conversion math + small-sample suppression.
- Existing 70 ladder tests must remain green.
- B: dry run against the live inbox with output to scratchpad; verify on one known re-marketed or synthetic address before relying on it.

## Guardrails
Invariant 1: nothing sends to owners; call sheet and letters are Gabriel-executed. Invariant 5: scripts live in an Oxford OneDrive business folder — writes are authorized by this build request; archive-first before modifying any existing script (`_archive/2026-09-22_…`). Routing: email output to ggoldberg@ only via `send-via-outlook.ps1`.
