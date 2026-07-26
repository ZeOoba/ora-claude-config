---
name: project-master-workbook-single-writer-proposal-2026-07-25
description: "RATIFIED 2026-07-25 -- fail-open + TTL claim protocol for Master Excel Template Company Wide -- Oxford.xlsx, modeled on the existing ora-skills single-writer rule and the house fail-open+TTL default. Full protocol text: [[tech]] new section 'Master Workbook single-writer protocol'."
metadata:
  type: project
  originSessionId: e3f980f6-f186-4928-ba79-212963641f99
  modified: 2026-07-25T18:19:37.170Z
---

**Status: RATIFIED 2026-07-25 (Gabriel, via AskUserQuestion — "ratify as recommended package").** The recommended design below is now the standing protocol; canonical text lives in `tech.md` (new section, cross-linked from here) so every future session finds it via the same lookup path as the ora-skills claim protocol. This file stays as the historical proposal/rationale record — do not restate the protocol text here if `tech.md` is later revised; that copy is authoritative.

## Ratified answers to the 3 open questions

1. **Marker location:** new `_active_sessions` sheet (forward declaration, not just after-the-fact Log detection).
2. **Enforcement:** documented convention only — no shared script/skill required to route through. Matches the ora-skills `git log -1` precedent; the audit trail already shows agents self-correct once a problem is found (Turn 115).
3. **Scope:** the 4 highest-blast-radius sheets implicated in 2026-07-24's chaos — Master Tenant Rent Roll, External Loans Summary, Property NOI, Portfolio Summary — not workbook-wide.

## Why

See [[project_master_workbook_no_single_writer_2026-07-24]]: the master workbook's own embedded
"Claude Log" sheet shows ~140 turns, most on 2026-07-24, from what read as multiple uncoordinated
agent sessions writing to the same file — a botched rent-roll sort that corrupted formula
references (Turns 108/111/112, caught in 115), and a debt-balance cell (`External Loans
Summary!E10`) flip-flopped 5× in immediate succession (Turns 132–136). Unlike `ora-skills`
(git-based single-writer check before any `SKILL.md` edit) or the scheduled-task registries
(membership-log check before registration), this workbook has no analogous gate — and it's the
one file CLAUDE.md names as "FIRST for firm figures."

## Why NOT a hard lock

[[feedback_fail_open_over_mutex_for_fleet_gates]] is the ratified house default (Gabriel,
2026-07-16, commit-provenance-guard design): reject a true mutex/claim-lock for cross-session
coordination in this fleet. A crashed session holding a hard claim on the ONE master workbook would
be worse than today's problem — every other session (and every scheduled brief/reconciliation job)
would be wedged, not just racing. The fleet runs 8-14+ concurrent sessions; the failure mode of
blocking must not be worse than the failure mode of an occasional missed collision.

## Proposed design (mirrors the ratified pattern)

**Two independent affirmative signals required before treating a write as unsafe** — absence of
information is never license to block:

1. **Liveness signal — a claim marker with TTL.** A small dedicated area in the workbook (a new
   `_active_sessions` sheet, or a reserved cell block) where a writing agent stamps
   `{sessionId, startedAt, expiresAt}` (TTL ~15 min — long enough for a batch of structural edits,
   short enough that a crashed session self-clears) before beginning STRUCTURAL writes (sorts, row
   insert/delete, mass formula rewrite — the actual failure category in Turns 108/111/112). Simple
   single-cell value edits (the vast majority of turns, e.g. one lease-date correction) are lower
   blast-radius and can skip the claim, matching Engineering OS's existing blast-radius calibration
   (even L1-equivalent work still runs the cheapest verify).
2. **Recency signal — the Claude Log itself.** Before claiming, read the Log's last row. If its
   timestamp is within the TTL window and its logged actor isn't this session, that's the second
   affirmative signal — stop and surface, don't silently proceed or silently overwrite.

**Fail-open:** if the claim area is unreadable, malformed, or the check itself errors, proceed
anyway (log a warning to the Claude Log) rather than block — consistent with the ratified stance
that a broken gate must never be able to wedge the one file every financial figure in the firm
depends on.

**On completion:** clear (or let expire) the claim; log the turn to Claude Log as already happens.

## Open questions for Gabriel

1. Where should the claim marker live — a new sheet, or repurpose the existing Claude Log's own
   last-row timestamp as the sole recency signal (simpler, no new sheet, but weaker — no forward
   declaration of intent, only after-the-fact detection)?
2. Should this be enforced by a shared helper script/skill that every agent touching this workbook
   is required to route through, or is a documented convention (like the ora-skills `git log -1`
   check) sufficient given the audit trail already shows agents mostly self-report correctly once a
   problem is found (Turn 115's own detailed self-correction)?
3. Scope: workbook-wide, or only the highest-blast-radius sheets (Master Tenant Rent Roll, External
   Loans Summary, Property NOI, Portfolio Summary — the ones actually implicated in 07-24's chaos)?

Related: [[project_master_workbook_no_single_writer_2026-07-24]] (the evidence) ·
[[feedback_fail_open_over_mutex_for_fleet_gates]] (the pattern this mirrors) ·
[[reference_concurrent_session_duplicate_hardening_work]] (same failure class, different surface).
