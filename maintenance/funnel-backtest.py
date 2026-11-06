#!/usr/bin/env python3
"""Sourcing funnel back-test: Deal Sourcing Log export -> calibration evidence.

HARD RULE -- REPORT-ONLY. This script never changes a score weight, band, gate, doctrine
file or Notion page. It reads JSON exports, computes, and prints the report (or writes it
to --out-md). Any weight, band or gate change the report motivates is a separate edit that
needs Gabriel's sign-off -- never this script.

WHY. Three live doctrines defer every calibration decision to a "December back-test" that
existed nowhere as code: scheduled-tasks/ora-passed-deal-tracker/SKILL.md (weights and
bands move only there, with Gabriel's sign-off), scheduled-tasks/ora-deal-sourcing-scan/
SKILL.md v2.9 (the 2026-10-30 hand back-test found 0 of 8 decided rows held T1; the v2.9
evidence tags sunset at the December back-test; testable: the share of T1 PURSUE rows that
survive verified-deal-recon), and the FORT column note in memory deal-decision-ledger.md.
This is the deterministic engine for that back-test: the same exports in, the same numbers
out, every time.

EXPORT CONTRACT. Notion SQL mode returns one page of about 100 rows and cannot paginate, so
the grouped export is era-bucketed and partitioned by verdict. The caller runs these five
queries exactly as written (they are also the module constants QUERY_A, QUERY_B, QUERY_P,
QUERY_N, QUERY_D; the Query A partition values are QUERY_A_PARTITIONS).

QUERY A (grouped; required; run 5 times with the single SQL param ["T1 PURSUE"],
["T2 WATCH"], ["PASS"], ["KILLED"], ["(none)"]; one --rows file each):
SELECT CASE WHEN substr("Date Added",1,10) >= '2026-10-30' THEN '2026-10-30' ELSE '2026-01-01' END AS created, "Source" AS source, "Verdict" AS verdict, "Verdict at First Sighting" AS verdict_first, "Status" AS status, "Go / No-Go" AS go, "Scorecard Done" AS scorecard, CASE WHEN "date:LOI Sent Date:start" IS NOT NULL THEN substr("date:LOI Sent Date:start",1,7) || '-01' END AS loi_sent, "LOI Outcome" AS loi_outcome, "Loss Class" AS loss_class, "Exclude from Calibration" AS exclude, COUNT(*) AS n FROM "collection://9a6ae219-85a3-4621-899c-c757fd062f8b" WHERE coalesce(nullif("Verdict",''),'(none)') = ? GROUP BY 1,2,3,4,5,6,7,8,9,10,11

QUERY B (per-row T1; optional; feeds --t1-rows):
SELECT url, "Deal Name / Address" AS name, substr("Date Added",1,10) AS created, "Verdict" AS verdict, "Verdict at First Sighting" AS verdict_first, "Score at First Sighting" AS score_first, "Status" AS status, "Go / No-Go" AS go, "Scorecard Done" AS scorecard, substr("date:LOI Sent Date:start",1,10) AS loi_sent, "LOI Outcome" AS loi_outcome, "Exclude from Calibration" AS exclude, "Data Certification" AS cert FROM "collection://9a6ae219-85a3-4621-899c-c757fd062f8b" WHERE "Verdict" = 'T1 PURSUE' OR "Verdict at First Sighting" = 'T1 PURSUE' ORDER BY 3

QUERY P (per-row P(exec); optional; feeds --pexec-rows):
SELECT substr("Date Added",1,10) AS created, "Verdict" AS verdict, "P(exec) %" AS p_exec, "LOI Outcome" AS loi_outcome, "Exclude from Calibration" AS exclude FROM "collection://9a6ae219-85a3-4621-899c-c757fd062f8b" WHERE "P(exec) %" IS NOT NULL

QUERY N (row count; optional but recommended; feeds --expect-rows):
SELECT COUNT(*) AS n FROM "collection://9a6ae219-85a3-4621-899c-c757fd062f8b"

QUERY D (per-row duplicate sets; optional but recommended; feeds --dup-rows):
SELECT url, "Deal Name / Address" AS name, createdTime AS created_ts, CASE WHEN substr("Date Added",1,10) >= '2026-10-30' THEN '2026-10-30' ELSE '2026-01-01' END AS created, substr("Date Added",1,10) AS created_day, "Source" AS source, "Verdict" AS verdict, "Verdict at First Sighting" AS verdict_first, "Score at First Sighting" AS score_first, "Status" AS status, "Go / No-Go" AS go, "Scorecard Done" AS scorecard, CASE WHEN "date:LOI Sent Date:start" IS NOT NULL THEN substr("date:LOI Sent Date:start",1,7) || '-01' END AS loi_sent, "LOI Outcome" AS loi_outcome, "Loss Class" AS loss_class, "Exclude from Calibration" AS exclude, "Data Certification" AS cert, "Duplicate Of" AS dup_of FROM "collection://9a6ae219-85a3-4621-899c-c757fd062f8b" AS t WHERE coalesce(t."Duplicate Of",'') <> '' OR EXISTS (SELECT 1 FROM "collection://9a6ae219-85a3-4621-899c-c757fd062f8b" AS d WHERE coalesce(d."Duplicate Of",'') <> '' AND instr(lower(replace(d."Duplicate Of",'-','')), lower(substr(replace(t.url,'-',''),-32))) > 0) ORDER BY 3

  - QUERY D returns every row in a duplicate set: each row whose "Duplicate Of" is set
    (deal-retirement 3a / Closed 2b write "app.notion.com/<32-hex page id> (deduped ...)")
    and each row such a value points at. Its created CASE and loi_sent bucket are QUERY A's,
    so every QUERY D row falls in exactly one --rows group.

  - The CASE boundary in Query A must match the --era boundaries (default: one boundary,
    v2.9=2026-10-30). When the era set changes (a new --era), Query A's CASE must gain the
    same boundary, or rows land in the wrong era. The CASE compares the literal date part
    (substr of "Date Added"; no time-zone conversion), exactly as Query B, Query P and this
    engine read created, so a time-zone-suffixed timestamp buckets identically everywhere.
    Query A's created is exact only to the era, which is why the stalled-T1 count prefers
    --t1-rows.
  - loi_sent is month-bucketed in Query A because only its presence is used.
  - The partitions are disjoint, so the five --rows files concatenate with no double count.
    They are exhaustive only for the known Verdict options: nullif folds a blank-string
    Verdict into (none), but a NEW Verdict option falls in no partition and would vanish
    silently. --expect-rows (the QUERY N result) closes that gap: the weighted rows of every
    --rows file, excluded rows included, must equal the log's row count, or the run exits 2.
    Without --expect-rows the report says "row-count reconciliation: NOT RUN".
  - Any input file whose results wrapper carries a has_more other than absent, null or false
    is refused (exit 2): a truncated export must never produce a calibration report.
  - A future REST export (once the Deal Sourcing Log is shared with the outreach
    integration) can replace Queries A, B and P with exact per-row records with no code
    change; QUERY N then stays a cheap completeness check.
  - verdict_first / score_first are the write-once first-sighting predictions: Notion
    properties "Verdict at First Sighting" and "Score at First Sighting", created
    2026-11-05 (Gabriel-approved) and written by the scans on row CREATION only. Rows
    created earlier carry neither, so the report states its tier basis every run. Query B
    also selects rows whose first verdict was T1 but whose current Verdict was overwritten.

INPUT. Each file is a JSON array of records or an object with a "results" array (the raw
Notion SQL tool response), read as utf-8-sig; --rows files are concatenated. A record is a
GROUPED row carrying n = COUNT(*) (an int >= 1) or a per-row record (no n, counts 1).
Fields are the SQL aliases; unknown extra keys are ignored; an empty string reads as null.
Every field is optional except created.
  created      YYYY-MM-DD or an ISO datetime; the date part is taken as written (no
               time-zone conversion). Missing or unparseable is fatal.
  source, verdict, verdict_first, floor, status, go, loi_outcome, loss_class, cert
               single selects, validated against the option sets below (read from the live
               schema on 2026-11-05); verdict_first uses the verdict options.
  scorecard, exclude
               checkboxes: true/false, "__YES__"/"__NO__", null (null = false).
  p_exec       a fraction in [0,1] is used as-is; a whole number in (1,100] is a percent,
               divided by 100 and counted under data quality. A non-whole value above 1
               (1.5 is neither a fraction nor a whole percent) is ambiguous and fatal, as is
               anything negative, above 100, non-numeric or NaN.
  score_first  any finite number (validated; unused in metrics for now).
  loi_sent     a date string or null; only its presence is used.
  name, url    display only (the stalled-T1 list).
An unknown select value is FATAL, never silently bucketed: exit 2 with one stderr line
"[FATAL] row <i> (<file>): <field>=<value!r> is not a known option", where i is the 0-based
position in that file's record array. A schema change must be loud.
--dup-rows (Query D) re-attributes rows before any metric is computed (see DUPLICATE
RECOVERY); it never adds or removes a row, so the row-count reconciliation is unchanged.
--t1-rows (Query B) feeds ONLY the stalled-T1 count and list and, when every record carries
cert, the T1 PROVISIONAL data-quality count. --pexec-rows (Query P) feeds ONLY the P(exec)
calibration. Neither is ever added to any other count. --expect-rows (Query N) holds one
record whose n is the log's row count; it feeds only the row-count reconciliation.

CLASSIFICATION (per record; the classes are exclusive; advanced_to_loi flags a subset of
go_decision):
  excluded: exclude checked. Dropped from every metric; counted only under data quality.
  advanced_to_loi: loi_sent present, OR status in {LOI Submitted, Under PSA}, OR
    loi_outcome in {PENDING, WON, LOST, SELLER-PULLED, WINNER-BUSTED, TERMINATED-DILIGENCE}.
  go_decision: go == the "Go - Submit LOI" option (U+1F7E2 green circle, U+2014 em dash),
    OR advanced_to_loi, OR loi_outcome == EXPIRED-UNSENT.
  rejected: not go_decision AND (go == the "Pass" option OR status == Passed).
  withdrawn: not go_decision AND not rejected AND status == Dead (listing gone; not a
    quality judgment; outside every strict rate denominator).
  open: everything else.
  decided = go_decision + rejected.
Tier = verdict_first when the record carries it, else the current verdict ("(none)" when
both are blank); every tier and T1 count uses it. Era = the latest --era boundary <=
created (a boundary date belongs to the new era); rows before every boundary are
"baseline". Default: --era v2.9=2026-10-30; any --era replaces the default.
Design note: a row re-tiered away from T1 (Verdict overwritten, verdict_first still T1)
with no Go / No-Go and a status other than Dead or Passed counts as open, not decided, so
T1 precision covers explicit decisions only; such rows appear in the stalled-T1 list once
they age past --stall-days.

DUPLICATE RECOVERY (--dup-rows). Two writers can create two rows for one parcel (a sourcing
scan and a Code session racing). The write-once first-sighting fields are never moved by any
writer, so the prediction can sit on a row that deal-retirement later flags as the duplicate.
The engine recovers it instead:
  - set: a kept (canonical) row plus every row whose "Duplicate Of" resolves to it,
    following chains (a cycle, a page id seen twice, or a url with no page id is fatal).
  - every flagged row is treated as excluded, even with Exclude unticked (it is moved from
    its --rows group to an excluded copy, counted as moved_to_excluded).
  - the canonical row's tier basis becomes the EARLIEST non-blank verdict_first in its set
    (by created_ts): "recovered" when its own was blank, "replaced" when an earlier row's
    differs. A canonical row that is itself excluded is left alone.
  - a "Duplicate Of" whose target is not in the export is "unresolved"; its row is still
    excluded.
  - --t1-rows follows: flagged rows are excluded there, and a canonical row that becomes T1
    is added with its exact created_day.
  - a QUERY D row matching no --rows group means the exports disagree: fatal.
Without --dup-rows the report says "duplicate recovery: NOT RUN".

METRICS (all counts weighted by n):
  1. Tier vs decision, per era: logged, decided, go, rejected, withdrawn, open per tier;
     held (strict) = go/decided and held incl. Dead = go/(decided + withdrawn), each with a
     Wilson 95% interval (z=1.96). Strict: Dead excluded; incl. Dead: every closed row
     counts as not-held (Dead often records a quality pass with no Go / No-Go value). For
     T1 held is scan precision; for T2 WATCH / PASS it is the under-ranking signal.
  2. Funnel conversion, per era: logged -> scorecard done -> go_decision -> advanced_to_loi
     -> WON; withdrawn rows stay out of every stage rate.
  3. Source yield, all eras: logged, T1, decided, go, LOI, WON per source ("(blank)" for
     null) and the share of logged rows whose source is Other or blank.
  4. P(exec) calibration (from --pexec-rows when given, else p_exec in --rows): executed=1
     for WON; 0 for LOST, SELLER-PULLED, EXPIRED-UNSENT, WINNER-BUSTED, TERMINATED-DILIGENCE;
     PENDING or null = unresolved (counted, not scored). Weighted Brier score, base rate,
     reference Brier base*(1-base), Brier skill 1 - brier/ref (null when ref == 0), and a
     reliability table over [0,0.2) [0.2,0.4) [0.4,0.6) [0.6,0.8) [0.8,1.0]. Under 10
     resolved rows: banner "INSUFFICIENT SAMPLE (resolved n=X < 10)", counts only.
  5. Loss class mix: counts by loss_class (non-null only).
  6. Stalled T1: open, tier T1 PURSUE, created more than --stall-days before --today. From
     --t1-rows (exact dates; up to 10 named, oldest first) when given; else counted from
     --rows and labelled approximate (Query A dates are era-bucketed).
  7. Data quality: excluded rows, p_exec typed as a percent, T1 with cert PROVISIONAL, no
     verdict, closed as Dead with no Go / No-Go decision (of which T1), tier taken from the
     current Verdict (the tier basis), records vs weighted rows, and the row-count
     reconciliation (OK, or NOT RUN without --expect-rows; a mismatch is fatal).
RATE DISCIPLINE: a rate (and its interval) prints only when its denominator >= --min-n;
otherwise the raw k/n and "(n<MIN)"; a zero denominator prints "-", never 0%.

OUTPUT: markdown (stdout, or --out-md as UTF-8) or --json (ASCII-escaped), plus exactly one
"[BACKTEST] ..." summary line on stderr. Exit 0 on success, 2 on any input error (one
[FATAL] line, never a traceback).

Usage:
  python funnel-backtest.py --rows A1.json --rows A2.json ... [--t1-rows B.json]
      [--pexec-rows P.json] [--expect-rows N.json] [--dup-rows D.json] [--era NAME=YYYY-MM-DD ...]
      [--today YYYY-MM-DD] [--stall-days 14] [--min-n 5] [--out-md PATH] [--json]

Stdlib only. ASCII-only.
"""
import argparse
import json
import math
import os
import re
import sys
from datetime import date

# The report carries the live option strings (em dash, emoji) -> force UTF-8 so a Windows
# cp1252 pipe can never crash the run on its own output.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCHEMA = "funnel-backtest/1"
TITLE = ("## Sourcing back-test - %s (report-only; any weight/band/gate change needs "
         "Gabriel's sign-off)")

# --- export contract (documented verbatim in the module docstring; run exactly) ----------
QUERY_A = '''SELECT CASE WHEN substr("Date Added",1,10) >= '2026-10-30' THEN '2026-10-30' ELSE '2026-01-01' END AS created, "Source" AS source, "Verdict" AS verdict, "Verdict at First Sighting" AS verdict_first, "Status" AS status, "Go / No-Go" AS go, "Scorecard Done" AS scorecard, CASE WHEN "date:LOI Sent Date:start" IS NOT NULL THEN substr("date:LOI Sent Date:start",1,7) || '-01' END AS loi_sent, "LOI Outcome" AS loi_outcome, "Loss Class" AS loss_class, "Exclude from Calibration" AS exclude, COUNT(*) AS n FROM "collection://9a6ae219-85a3-4621-899c-c757fd062f8b" WHERE coalesce(nullif("Verdict",''),'(none)') = ? GROUP BY 1,2,3,4,5,6,7,8,9,10,11'''
QUERY_A_PARTITIONS = ("T1 PURSUE", "T2 WATCH", "PASS", "KILLED", "(none)")
QUERY_B = '''SELECT url, "Deal Name / Address" AS name, substr("Date Added",1,10) AS created, "Verdict" AS verdict, "Verdict at First Sighting" AS verdict_first, "Score at First Sighting" AS score_first, "Status" AS status, "Go / No-Go" AS go, "Scorecard Done" AS scorecard, substr("date:LOI Sent Date:start",1,10) AS loi_sent, "LOI Outcome" AS loi_outcome, "Exclude from Calibration" AS exclude, "Data Certification" AS cert FROM "collection://9a6ae219-85a3-4621-899c-c757fd062f8b" WHERE "Verdict" = 'T1 PURSUE' OR "Verdict at First Sighting" = 'T1 PURSUE' ORDER BY 3'''
QUERY_P = '''SELECT substr("Date Added",1,10) AS created, "Verdict" AS verdict, "P(exec) %" AS p_exec, "LOI Outcome" AS loi_outcome, "Exclude from Calibration" AS exclude FROM "collection://9a6ae219-85a3-4621-899c-c757fd062f8b" WHERE "P(exec) %" IS NOT NULL'''
QUERY_N = '''SELECT COUNT(*) AS n FROM "collection://9a6ae219-85a3-4621-899c-c757fd062f8b"'''
QUERY_D = '''SELECT url, "Deal Name / Address" AS name, createdTime AS created_ts, CASE WHEN substr("Date Added",1,10) >= '2026-10-30' THEN '2026-10-30' ELSE '2026-01-01' END AS created, substr("Date Added",1,10) AS created_day, "Source" AS source, "Verdict" AS verdict, "Verdict at First Sighting" AS verdict_first, "Score at First Sighting" AS score_first, "Status" AS status, "Go / No-Go" AS go, "Scorecard Done" AS scorecard, CASE WHEN "date:LOI Sent Date:start" IS NOT NULL THEN substr("date:LOI Sent Date:start",1,7) || '-01' END AS loi_sent, "LOI Outcome" AS loi_outcome, "Loss Class" AS loss_class, "Exclude from Calibration" AS exclude, "Data Certification" AS cert, "Duplicate Of" AS dup_of FROM "collection://9a6ae219-85a3-4621-899c-c757fd062f8b" AS t WHERE coalesce(t."Duplicate Of",'') <> '' OR EXISTS (SELECT 1 FROM "collection://9a6ae219-85a3-4621-899c-c757fd062f8b" AS d WHERE coalesce(d."Duplicate Of",'') <> '' AND instr(lower(replace(d."Duplicate Of",'-','')), lower(substr(replace(t.url,'-',''),-32))) > 0) ORDER BY 3'''

# --- option sets, read from the live Deal Sourcing Log schema on 2026-11-05 ---------------
# Non-ASCII characters are 8-digit escapes so this source stays ASCII.
SOURCE_OPTIONS = ("Crexi", "Broker \U00002014 Direct", "Off-Market", "LoopNet", "CoStar", "Other")
VERDICT_OPTIONS = ("T1 PURSUE", "T2 WATCH", "PASS", "KILLED")
FLOOR_OPTIONS = ("PASS", "FAIL-BASIS", "FAIL-YIELD", "FAIL-BOTH", "N/A")
STATUS_OPTIONS = ("New Lead", "Reviewing", "LOI Submitted", "Under PSA", "Passed", "Dead",
                  "Screened")
GO_SUBMIT = "\U0001F7E2 Go \U00002014 Submit LOI"
GO_MAYBE = "\U0001F7E1 Maybe \U00002014 Need More Info"
GO_PASS = "\U0001F534 Pass"
GO_REVIEW = "\U000023F3 Under Review"
GO_OPTIONS = (GO_SUBMIT, GO_MAYBE, GO_PASS, GO_REVIEW)
LOI_OUTCOME_OPTIONS = ("PENDING", "WON", "LOST", "SELLER-PULLED", "EXPIRED-UNSENT",
                       "WINNER-BUSTED", "TERMINATED-DILIGENCE")
LOSS_CLASS_OPTIONS = ("UNCLASSIFIED", "BASIS-DISCIPLINE", "NON-COMPARABLE BUYER",
                      "BASIS-ELECTIVE", "PRICE-MARGINAL", "EXECUTION", "WINNER-BUSTED")
CERT_OPTIONS = ("PROVISIONAL", "CERTIFIED")

SELECT_FIELDS = (("source", SOURCE_OPTIONS), ("verdict", VERDICT_OPTIONS),
                 ("verdict_first", VERDICT_OPTIONS), ("floor", FLOOR_OPTIONS),
                 ("status", STATUS_OPTIONS), ("go", GO_OPTIONS),
                 ("loi_outcome", LOI_OUTCOME_OPTIONS), ("loss_class", LOSS_CLASS_OPTIONS),
                 ("cert", CERT_OPTIONS))
CHECKBOX_FIELDS = ("scorecard", "exclude")

# --- classification and metric constants --------------------------------------------------
T1 = "T1 PURSUE"
NO_VERDICT = "(none)"
TIERS = VERDICT_OPTIONS + (NO_VERDICT,)
BLANK_SOURCE = "(blank)"
BASELINE = "baseline"
DEFAULT_ERAS = (("v2.9", date(2026, 10, 30)),)
ADVANCED_STATUSES = frozenset(("LOI Submitted", "Under PSA"))
ADVANCED_OUTCOMES = frozenset(("PENDING", "WON", "LOST", "SELLER-PULLED", "WINNER-BUSTED",
                               "TERMINATED-DILIGENCE"))
DECIDED_CLASSES = ("go", "rejected")
EXECUTED = {"WON": 1, "LOST": 0, "SELLER-PULLED": 0, "EXPIRED-UNSENT": 0, "WINNER-BUSTED": 0,
            "TERMINATED-DILIGENCE": 0}  # PENDING and null are unresolved
CAL_BINS = ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0))
MIN_RESOLVED = 10
Z95 = 1.96
STALLED_LIST_MAX = 10
BASIS_FIRST = "first-sighting (write-once)"
BASIS_CURRENT = ("current Verdict (may be overwritten by later decisions; calibration "
                 "understates T1 misses)")
APPROXIMATE = "approximate: uses --rows created dates, which may be era-bucketed"

_CREATED_RE = re.compile(r"(\d{4}-\d{2}-\d{2})(?:[T ].*)?", re.ASCII | re.DOTALL)
_DAY_RE = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)


class InputError(Exception):
    """Bad input. main() prints it as one [FATAL] line and exits 2 -- never a traceback."""


# --- load / validate ----------------------------------------------------------------------

def _blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def _is_number(value):
    """A finite JSON number. bool is excluded (True == 1 in Python), and so are NaN and
    Infinity, which json.loads accepts."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return not (isinstance(value, float) and not math.isfinite(value))


def _parse_day(text):
    """'YYYY-MM-DD' -> date, else None."""
    if not isinstance(text, str) or not _DAY_RE.fullmatch(text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _bad(index, source, field, value, why):
    return InputError("row %d (%s): %s=%r %s" % (index, source, field, value, why))


def normalize_record(raw, index, source):
    """Validate one export record and return it normalized. Raises InputError on any value
    outside the input contract; the message names the 0-based row and the file."""
    if not isinstance(raw, dict):
        raise InputError("row %d (%s): record is not a JSON object (got %s)"
                         % (index, source, type(raw).__name__))
    rec = {"_row": index, "_file": source, "_has_cert": "cert" in raw}
    created = raw.get("created")
    match = _CREATED_RE.fullmatch(created.strip()) if isinstance(created, str) else None
    day = _parse_day(match.group(1)) if match else None
    if day is None:
        raise _bad(index, source, "created", created, "is missing or not a YYYY-MM-DD date")
    rec["created"] = day
    if "n" in raw:
        n = raw["n"]
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            raise _bad(index, source, "n", n, "is not an integer >= 1")
        rec["n"] = n
    else:
        rec["n"] = 1
    for field, options in SELECT_FIELDS:
        value = raw.get(field)
        if _blank(value):
            rec[field] = None
        elif isinstance(value, str) and value in options:
            rec[field] = value
        else:
            raise _bad(index, source, field, value, "is not a known option")
    for field in CHECKBOX_FIELDS:
        value = raw.get(field)
        if value is True or value == "__YES__":
            rec[field] = True
        elif value is False or value == "__NO__" or _blank(value):
            rec[field] = False
        else:
            raise _bad(index, source, field, value, "is not a known option")
    p_exec = raw.get("p_exec")
    rec["p_exec"], rec["p_exec_percent"] = None, False
    if not _blank(p_exec):
        if not _is_number(p_exec):
            raise _bad(index, source, "p_exec", p_exec, "is not a number")
        if p_exec < 0 or p_exec > 100:
            raise _bad(index, source, "p_exec", p_exec, "is out of range (a fraction in [0,1] "
                       "or a whole-number percent in (1,100])")
        if p_exec <= 1:
            rec["p_exec"] = float(p_exec)
        elif isinstance(p_exec, float) and not p_exec.is_integer():
            raise _bad(index, source, "p_exec", p_exec, "is ambiguous (above 1 it must be a "
                       "whole-number percent; a fraction lies in [0,1])")
        else:
            rec["p_exec"], rec["p_exec_percent"] = p_exec / 100.0, True
    score = raw.get("score_first")
    if _blank(score):
        rec["score_first"] = None
    elif _is_number(score):
        rec["score_first"] = score
    else:
        raise _bad(index, source, "score_first", score, "is not a number")
    loi_sent = raw.get("loi_sent")
    if _blank(loi_sent):
        rec["loi_sent"] = False
    elif isinstance(loi_sent, str):
        rec["loi_sent"] = True
    else:
        raise _bad(index, source, "loi_sent", loi_sent, "is not a date string")
    for field in ("name", "url"):
        value = raw.get(field)
        rec[field] = None if _blank(value) else str(value)
    return rec


def read_export(path):
    """One export file -> its list of raw records. Accepts a JSON array or an object with a
    "results" array; refuses a results wrapper whose has_more is anything but absent, null or
    false (identity, not truthiness: "false", 0 and "true" are all refused)."""
    try:
        with open(path, encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except OSError as exc:
        raise InputError("cannot read %s: %s" % (path, exc))
    except UnicodeDecodeError as exc:  # before ValueError: it is a subclass
        raise InputError("%s is not UTF-8 text: %s" % (path, exc))
    except (ValueError, RecursionError) as exc:
        raise InputError("%s is not valid JSON: %s" % (path, exc))
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        has_more = data.get("has_more")
        if has_more is not None and has_more is not False:
            raise InputError("%s: export truncated (has_more=true); re-run the query with "
                             "coarser buckets" % path)
        return data["results"]
    if isinstance(data, list):
        return data
    raise InputError('%s: expected a JSON array of records or an object with a "results" '
                     'array' % path)


def load_records(paths, flag="--rows"):
    """Read, validate and concatenate every file passed to one flag."""
    seen, records = set(), []
    for path in paths:
        key = os.path.normcase(os.path.abspath(path))
        if key in seen:
            raise InputError("%s was passed to %s more than once; its rows would be "
                             "double-counted" % (path, flag))
        seen.add(key)
        for index, raw in enumerate(read_export(path)):
            records.append(normalize_record(raw, index, path))
    return records


def load_expected_rows(path):
    """The QUERY N result: exactly one record whose n is the log's row count."""
    records = read_export(path)
    n = records[0].get("n") if len(records) == 1 and isinstance(records[0], dict) else None
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise InputError("%s: expected exactly one record with an integer n >= 0 (the QUERY N "
                         "result)" % path)
    return n


def check_row_count(covered, expected, path):
    """Row-count reconciliation: the --rows partitions (excluded rows included) must cover
    every row of the log. A Verdict outside QUERY_A_PARTITIONS falls in no partition."""
    if covered < expected:
        raise InputError("%s: partitions cover %d rows but the log holds %d; a Verdict value is "
                         "outside QUERY_A_PARTITIONS (new option or blank string)"
                         % (path, covered, expected))
    if covered > expected:
        raise InputError("%s: partitions cover %d rows but the log holds %d; the --rows files "
                         "hold more rows than the log (a partition exported twice, or the log "
                         "changed between queries)" % (path, covered, expected))


# --- duplicate recovery (--dup-rows, QUERY D) ----------------------------------------------

_PAGE_ID_RE = re.compile(r"[0-9a-f]{32}", re.ASCII)
GROUP_KEY = ("created", "source", "verdict", "verdict_first", "status", "go", "scorecard",
             "loi_sent", "loi_outcome", "loss_class", "exclude")


def _page_ids(text):
    return _PAGE_ID_RE.findall(text.lower().replace("-", "")) if isinstance(text, str) else []


def normalize_dup_records(raws, source):
    """Validate QUERY D records. Each also carries page_id (from url), dup_target (the page id
    in dup_of, or None), created_day (exact date) and created_ts (ordering key)."""
    out, seen = [], set()
    for index, raw in enumerate(raws):
        rec = normalize_record(raw, index, source)
        ids = _page_ids(raw.get("url"))
        if not ids:
            raise _bad(index, source, "url", raw.get("url"), "carries no 32-hex page id")
        rec["page_id"] = ids[-1]
        if rec["page_id"] in seen:
            raise _bad(index, source, "url", raw.get("url"), "appears twice in --dup-rows")
        seen.add(rec["page_id"])
        dup_of = raw.get("dup_of")
        if _blank(dup_of):
            rec["dup_target"] = None
        else:
            targets = _page_ids(dup_of)
            if not targets:
                raise _bad(index, source, "dup_of", dup_of, "carries no 32-hex page id")
            rec["dup_target"] = targets[0]
            if rec["dup_target"] == rec["page_id"]:
                raise _bad(index, source, "dup_of", dup_of, "points at its own row (a cycle)")
        day = _parse_day(raw.get("created_day")) if isinstance(raw.get("created_day"), str) else None
        if day is None:
            raise _bad(index, source, "created_day", raw.get("created_day"),
                       "is missing or not a YYYY-MM-DD date")
        rec["created_day"] = day
        ts = raw.get("created_ts")
        rec["created_ts"] = ts.strip() if isinstance(ts, str) and ts.strip() else day.isoformat()
        out.append(rec)
    return out


def load_dup_records(paths):
    seen, records = set(), []
    for path in paths:
        key = os.path.normcase(os.path.abspath(path))
        if key in seen:
            raise InputError("%s was passed to --dup-rows more than once" % path)
        seen.add(key)
        records.extend(normalize_dup_records(read_export(path), path))
    ids = [r["page_id"] for r in records]
    if len(ids) != len(set(ids)):
        raise InputError("--dup-rows: a page id appears twice across the --dup-rows files")
    return records


def _take(records, dup_rec):
    """Remove one row of dup_rec's --rows group; return a 1-row copy of that group."""
    key = tuple(dup_rec[f] for f in GROUP_KEY)
    for group in records:
        if group["n"] >= 1 and tuple(group[f] for f in GROUP_KEY) == key:
            group["n"] -= 1
            copy = dict(group)
            copy["n"] = 1
            return copy
    raise InputError("--dup-rows row %d (%s): url %s matches no --rows group with a row left; "
                     "the exports were taken at different times or with different queries"
                     % (dup_rec["_row"], dup_rec["_file"], dup_rec["url"]))


def apply_duplicates(records, dup_records, t1_rows):
    """Re-attribute rows by duplicate set (module docstring, DUPLICATE RECOVERY). Returns
    (records, t1_rows, stats); the inputs are not mutated and the weighted total is kept."""
    if dup_records is None:
        return records, t1_rows, {"status": "not-run"}
    records = [dict(r) for r in records]
    by_id = {r["page_id"]: r for r in dup_records}
    flagged = [r for r in dup_records if r["dup_target"] is not None]

    def root_of(page_id):
        seen = [page_id]
        while page_id in by_id and by_id[page_id]["dup_target"] is not None:
            page_id = by_id[page_id]["dup_target"]
            if page_id in seen:
                raise InputError("--dup-rows: Duplicate Of forms a cycle through %s"
                                 % ", ".join(seen))
            seen.append(page_id)
        return page_id

    members, unresolved, moved = {}, 0, 0
    for row in flagged:
        root = root_of(row["page_id"])
        if root in by_id:
            members.setdefault(root, []).append(row)
        else:
            unresolved += 1
    for row in flagged:
        if not row["exclude"]:
            copy = _take(records, row)
            copy["exclude"] = True
            records.append(copy)
            moved += 1
    recovered = replaced = 0
    overrides = {}
    for root, rows in members.items():
        canon = by_id[root]
        if canon["exclude"]:
            continue
        cands = [r for r in [canon] + rows if r["verdict_first"] is not None]
        if not cands:
            continue
        first = min(cands, key=lambda r: (r["created_ts"], r["page_id"]))
        if first is canon or first["verdict_first"] == canon["verdict_first"]:
            continue
        copy = _take(records, canon)
        copy["verdict_first"], copy["score_first"] = first["verdict_first"], first["score_first"]
        records.append(copy)
        if canon["verdict_first"] is None:
            recovered += 1
        else:
            replaced += 1
        overrides[root] = first
    records = [r for r in records if r["n"] >= 1]
    if t1_rows is not None:
        flagged_ids = {r["page_id"] for r in flagged}
        adjusted, present = [], set()
        for row in t1_rows:
            row = dict(row)
            ids = _page_ids(row["url"])
            pid = ids[-1] if ids else None
            present.add(pid)
            if pid in flagged_ids:
                row["exclude"] = True
            elif pid in overrides:
                row["verdict_first"] = overrides[pid]["verdict_first"]
                row["score_first"] = overrides[pid]["score_first"]
            adjusted.append(row)
        for pid, first in sorted(overrides.items()):
            if pid not in present and first["verdict_first"] == T1:
                row = dict(by_id[pid])
                row["created"] = row["created_day"]
                row["verdict_first"], row["score_first"] = first["verdict_first"], first["score_first"]
                row["n"] = 1
                adjusted.append(row)
        t1_rows = adjusted
    stats = {"status": "run", "sets": len(members), "flagged": len(flagged),
             "moved_to_excluded": moved, "recovered": recovered, "replaced": replaced,
             "unresolved": unresolved}
    return records, t1_rows, stats


# --- eras ---------------------------------------------------------------------------------

def parse_era(text):
    """'NAME=YYYY-MM-DD' -> (name, date). Validation of the whole set is build_eras()."""
    name, sep, day_text = text.rpartition("=")
    day = _parse_day(day_text.strip())
    if not sep or day is None:
        raise InputError("--era %r: expected NAME=YYYY-MM-DD" % text)
    return name.strip(), day


def build_eras(specs):
    """Validate (name, start) pairs and return them sorted by start date."""
    eras = sorted(specs, key=lambda era: era[1])
    names = [name for name, _ in eras]
    days = [day for _, day in eras]
    for name in names:
        if not name:
            raise InputError("--era: every era needs a NAME (NAME=YYYY-MM-DD)")
        if name == BASELINE:
            raise InputError("--era: %r is reserved for rows before every boundary" % BASELINE)
    dup_names = sorted({name for name in names if names.count(name) > 1})
    if dup_names:
        raise InputError("--era: duplicate era name %s" % ", ".join(dup_names))
    dup_days = sorted({day.isoformat() for day in days if days.count(day) > 1})
    if dup_days:
        raise InputError("--era: two eras share the boundary %s" % ", ".join(dup_days))
    return eras


def era_of(created, eras):
    """The latest era whose start <= created; BASELINE before every boundary."""
    current = BASELINE
    for name, start in eras:
        if start <= created:
            current = name
        else:
            break
    return current


# --- classify -----------------------------------------------------------------------------

def tier_of(rec):
    """verdict_first (first sighting, write-once) when carried, else the current verdict."""
    return rec["verdict_first"] if rec["verdict_first"] is not None else rec["verdict"]


def is_advanced_to_loi(rec):
    return bool(rec["loi_sent"] or rec["status"] in ADVANCED_STATUSES
                or rec["loi_outcome"] in ADVANCED_OUTCOMES)


def classify(rec):
    """One of: excluded, go, rejected, withdrawn, open (see the module docstring)."""
    if rec["exclude"]:
        return "excluded"
    if rec["go"] == GO_SUBMIT or is_advanced_to_loi(rec) or rec["loi_outcome"] == "EXPIRED-UNSENT":
        return "go"
    if rec["go"] == GO_PASS or rec["status"] == "Passed":
        return "rejected"
    if rec["status"] == "Dead":
        return "withdrawn"
    return "open"


# --- statistics ---------------------------------------------------------------------------

def wilson(k, n, z=Z95):
    """Wilson score interval for k successes in n trials; None when n == 0."""
    if n <= 0:
        return None
    p = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n))
    low = 0.0 if k == 0 else max(0.0, center - half)
    high = 1.0 if k == n else min(1.0, center + half)
    return low, high


def _r(value):
    return None if value is None else round(value, 6)


def rate(k, n, min_n, ci=False):
    """A rate under the rate discipline: the value (and interval) only when n >= min_n."""
    out = {"k": k, "n": n, "min_n": min_n, "rate": None, "status": "ok"}
    if ci:
        out["ci_low"] = out["ci_high"] = None
    if n <= 0:
        out["status"] = "empty"
    elif n < min_n:
        out["status"] = "n<min"
    else:
        out["rate"] = _r(k / n)
        if ci:
            low, high = wilson(k, n)
            out["ci_low"], out["ci_high"] = _r(low), _r(high)
    return out


def format_rate(r):
    if r["status"] == "empty":
        return "-"
    if r["status"] == "n<min":
        return "%d/%d (n<%d)" % (r["k"], r["n"], r["min_n"])
    text = "%d/%d = %.1f%%" % (r["k"], r["n"], 100.0 * r["rate"])
    if "ci_low" in r:
        text += " [%.1f-%.1f%%]" % (100.0 * r["ci_low"], 100.0 * r["ci_high"])
    return text


def brier_stats(items):
    """items: (p_exec, executed 0/1, weight). Unsuppressed statistics; None when empty."""
    items = list(items)
    weight = sum(w for _, _, w in items)
    if weight <= 0:
        return {"n": 0, "executed": 0, "brier": None, "base_rate": None,
                "reference_brier": None, "brier_skill": None}
    executed = sum(w * o for _, o, w in items)
    brier = sum(w * (p - o) ** 2 for p, o, w in items) / weight
    base = executed / weight
    reference = base * (1.0 - base)
    skill = None if reference == 0 else 1.0 - brier / reference
    return {"n": weight, "executed": executed, "brier": brier, "base_rate": base,
            "reference_brier": reference, "brier_skill": skill}


def bin_index(p):
    """Reliability bin by edge comparison (division would put 0.6 in [0.4,0.6))."""
    last = len(CAL_BINS) - 1
    for i, (low, high) in enumerate(CAL_BINS):
        if low <= p < high or (i == last and p == high):
            return i
    raise ValueError("p_exec %r is outside [0,1]" % (p,))


# --- aggregate ----------------------------------------------------------------------------

TIER_COUNTS = ("logged", "decided", "go", "rejected", "withdrawn", "open")
FUNNEL_COUNTS = ("logged", "withdrawn", "eligible", "scorecard", "go", "go_with_scorecard",
                 "go_without_scorecard", "loi", "won")
SOURCE_COUNTS = ("logged", "t1", "decided", "go", "loi", "won")

DEFINITIONS = (
    "excluded: exclude checked; dropped from every metric, counted only under Data quality.",
    "advanced_to_loi: loi_sent present, OR status in {LOI Submitted, Under PSA}, OR "
    "loi_outcome in {PENDING, WON, LOST, SELLER-PULLED, WINNER-BUSTED, TERMINATED-DILIGENCE}.",
    'go_decision: go = "%s", OR advanced_to_loi, OR loi_outcome = EXPIRED-UNSENT.' % GO_SUBMIT,
    'rejected: not go_decision AND (go = "%s" OR status = Passed).' % GO_PASS,
    "withdrawn: not go_decision AND not rejected AND status = Dead (listing gone; not a "
    "quality judgment; outside every strict rate denominator).",
    "open: everything else.",
    "decided = go_decision + rejected. Held (strict) = go_decision / decided; held incl. Dead "
    "= go_decision / (decided + withdrawn) (strict: Dead excluded; incl. Dead: every closed row "
    "counts as not-held). For T1 PURSUE held is scan precision; for T2 WATCH / PASS it is the "
    "under-ranking signal.",
    "Tier: verdict_first (first sighting, write-once) when the record carries it, else the "
    "current Verdict; every tier and T1 count uses it.",
    "Re-tiered T1: a row whose tier is T1 but whose Verdict was overwritten, with no Go / No-Go "
    "and a status other than Dead or Passed, is open, not decided, so T1 precision covers "
    "explicit decisions only; it appears in the stalled-T1 list once older than stall-days.",
    "Era: the latest --era boundary <= created (a boundary date belongs to the new era); rows "
    "before every boundary are baseline. created is the date part as written.",
    "Counts are weighted by n (COUNT(*) of a grouped export row); a record without n counts 1.",
    "Rates print only when the denominator >= min-n; otherwise raw k/n (n<MIN); - = zero "
    "denominator. [lo-hi%] = Wilson 95% interval (z = 1.96).",
    "Funnel: withdrawn rows stay out of every stage rate; Go/scorecard counts go decisions that "
    "have a scorecard; LOI/go and Won/LOI use every go decision and every LOI.",
    "P(exec): --pexec-rows only when supplied, else p_exec in --rows. executed = 1 for WON; 0 "
    "for LOST, SELLER-PULLED, EXPIRED-UNSENT, WINNER-BUSTED, TERMINATED-DILIGENCE; PENDING or "
    "blank = unresolved (counted, not scored). Brier = n-weighted mean of (p_exec - "
    "executed)^2; reference = base*(1-base); skill = 1 - Brier/reference (null when reference "
    "= 0); statistics withheld below 10 resolved rows. A whole-number p_exec in (1,100] is a "
    "percent, divided by 100; a non-whole value above 1 is ambiguous and refused.",
    "Stalled T1: open, tier T1 PURSUE, created more than stall-days before today; counted from "
    "--t1-rows (exact per-row dates) when supplied, else from --rows (" + APPROXIMATE + ").",
    "--t1-rows and --pexec-rows are never added to any other count. T1 cert PROVISIONAL comes "
    "from --t1-rows when every record carries cert, else from --rows.",
    "Row-count reconciliation: with --expect-rows (QUERY_N) the weighted rows of every --rows "
    "file, excluded rows included, must equal the log's row count, else exit 2 (a Verdict value "
    "outside QUERY_A_PARTITIONS); without --expect-rows the check is NOT RUN.",
    "Duplicate recovery (--dup-rows, QUERY_D): every row with Duplicate Of set is excluded; "
    "each kept row's tier basis is the earliest first-sighting verdict in its duplicate set "
    "(by created time). No row is added or removed. Without --dup-rows: NOT RUN.",
    "Data quality rows are weighted, non-excluded rows (Excluded and the totals aside).",
    "Report-only: nothing here changes a score weight, band, gate, doctrine file or Notion; any "
    "change needs Gabriel's sign-off.",
)


def _is_stalled(rec, cls, today, stall_days):
    return cls == "open" and tier_of(rec) == T1 and (today - rec["created"]).days > stall_days


def _pexec_section(source_records, source_label, source_count, min_n):
    """P(exec) calibration over ONE record source. Returns (section, percent-typed rows)."""
    items, with_p, unresolved, resolved_without, percent = [], 0, 0, 0, 0
    bins = [{"n": 0, "executed": 0, "sum_p": 0.0} for _ in CAL_BINS]
    for rec in source_records:
        if rec["exclude"]:
            continue
        n = rec["n"]
        if rec["p_exec_percent"]:
            percent += n
        outcome = EXECUTED.get(rec["loi_outcome"])
        if rec["p_exec"] is None:
            if outcome is not None:
                resolved_without += n
            continue
        with_p += n
        if outcome is None:
            unresolved += n
            continue
        items.append((rec["p_exec"], outcome, n))
        cell = bins[bin_index(rec["p_exec"])]
        cell["n"] += n
        cell["executed"] += n * outcome
        cell["sum_p"] += n * rec["p_exec"]
    stats = brier_stats(items)
    resolved = stats["n"]
    insufficient = resolved < MIN_RESOLVED
    stats_min = max(min_n, MIN_RESOLVED)  # Brier, base rate and skill need both thresholds
    shown = resolved >= stats_min
    bin_min = stats_min if insufficient else min_n  # INSUFFICIENT SAMPLE -> counts only
    out_bins = []
    for i, ((low, high), cell) in enumerate(zip(CAL_BINS, bins)):
        out_bins.append({
            "bin": "[%.1f,%.1f%s" % (low, high, "]" if i == len(CAL_BINS) - 1 else ")"),
            "n": cell["n"], "executed": cell["executed"],
            "mean_predicted": (_r(cell["sum_p"] / cell["n"])
                               if cell["n"] and not insufficient else None),
            "observed": rate(cell["executed"], cell["n"], bin_min)})
    section = {
        "source": source_label, "source_records": source_count, "min_resolved": MIN_RESOLVED,
        "with_p_exec": with_p, "resolved_n": resolved, "unresolved_n": unresolved,
        "resolved_without_p_exec": resolved_without, "insufficient_sample": insufficient,
        "executed": stats["executed"],
        "base_rate": rate(stats["executed"], resolved, stats_min),
        "brier": _r(stats["brier"]) if shown else None,
        "reference_brier": _r(stats["reference_brier"]) if shown else None,
        "brier_skill": _r(stats["brier_skill"]) if shown else None,
        "bins": out_bins}
    return section, percent


def aggregate(records, eras, today, stall_days, min_n, t1_rows=None, pexec_rows=None,
              rows_files=(), t1_files=(), pexec_files=(), expected_rows=None, expect_file=None,
              dup_stats=None, dup_files=()):
    """Every metric from validated records. Pure (no I/O). t1_rows and pexec_rows feed only
    their own sections and are never added to any other count. expected_rows (the QUERY N
    count) must equal the weighted --rows total, excluded rows included, or InputError."""
    era_names = [BASELINE] + [name for name, _ in eras]
    tiers = {era: {tier: dict.fromkeys(TIER_COUNTS, 0) for tier in TIERS} for era in era_names}
    funnel = {era: dict.fromkeys(FUNNEL_COUNTS, 0) for era in era_names}
    sources = {name: dict.fromkeys(SOURCE_COUNTS, 0) for name in SOURCE_OPTIONS + (BLANK_SOURCE,)}
    loss = dict.fromkeys(LOSS_CLASS_OPTIONS, 0)
    totals = {"records": len(records), "rows": 0, "excluded_rows": 0, "logged_rows": 0}
    stalled = t1_provisional = no_verdict = dead = dead_t1 = first_rows = 0
    for rec in records:
        n = rec["n"]
        totals["rows"] += n
        cls = classify(rec)
        if cls == "excluded":
            totals["excluded_rows"] += n
            continue
        totals["logged_rows"] += n
        era = era_of(rec["created"], eras)
        tier = tier_of(rec)
        advanced = is_advanced_to_loi(rec)
        won = rec["loi_outcome"] == "WON"
        decided = cls in DECIDED_CLASSES
        cell = tiers[era][tier or NO_VERDICT]
        cell["logged"] += n
        cell[cls] += n
        if decided:
            cell["decided"] += n
        stage = funnel[era]
        stage["logged"] += n
        if cls == "withdrawn":
            stage["withdrawn"] += n
        else:
            stage["eligible"] += n
            if rec["scorecard"]:
                stage["scorecard"] += n
            if cls == "go":
                stage["go"] += n
                stage["go_with_scorecard" if rec["scorecard"] else "go_without_scorecard"] += n
            if advanced:
                stage["loi"] += n
            if won:
                stage["won"] += n
        src = sources[rec["source"] or BLANK_SOURCE]
        src["logged"] += n
        if tier == T1:
            src["t1"] += n
        if decided:
            src["decided"] += n
        if cls == "go":
            src["go"] += n
        if advanced:
            src["loi"] += n
        if won:
            src["won"] += n
        if rec["loss_class"]:
            loss[rec["loss_class"]] += n
        if _is_stalled(rec, cls, today, stall_days):
            stalled += n
        if tier == T1 and rec["cert"] == "PROVISIONAL":
            t1_provisional += n
        if tier is None:
            no_verdict += n
        if cls == "withdrawn":
            dead += n
            if tier == T1:
                dead_t1 += n
        if rec["verdict_first"] is not None:
            first_rows += n
    if expected_rows is None:
        reconciliation = {"status": "not-run", "covered_rows": totals["rows"], "expected_rows": None}
    else:
        check_row_count(totals["rows"], expected_rows, expect_file or "--expect-rows")
        reconciliation = {"status": "ok", "covered_rows": totals["rows"],
                          "expected_rows": expected_rows}
    for era in era_names:
        for cell in tiers[era].values():
            cell["held"] = rate(cell["go"], cell["decided"], min_n, ci=True)
            cell["held_incl_dead"] = rate(cell["go"], cell["decided"] + cell["withdrawn"], min_n,
                                          ci=True)
        stage = funnel[era]
        stage["rates"] = {
            "scorecard_of_eligible": rate(stage["scorecard"], stage["eligible"], min_n),
            "go_of_scorecard": rate(stage["go_with_scorecard"], stage["scorecard"], min_n),
            "loi_of_go": rate(stage["loi"], stage["go"], min_n),
            "won_of_loi": rate(stage["won"], stage["loi"], min_n)}
    other_or_blank = sources["Other"]["logged"] + sources[BLANK_SOURCE]["logged"]

    if pexec_rows is not None:
        calibration, percent = _pexec_section(pexec_rows, "--pexec-rows", len(pexec_rows), min_n)
    else:
        calibration, percent = _pexec_section(records, "--rows", None, min_n)

    if t1_rows is not None:
        hits = sorted((r for r in t1_rows if _is_stalled(r, classify(r), today, stall_days)),
                      key=lambda r: (r["created"], r["name"] or "", r["url"] or ""))
        stalled_t1 = {"count": sum(r["n"] for r in hits), "count_source": "--t1-rows",
                      "approximate": False, "stall_days": stall_days, "names_supplied": True,
                      "t1_records": len(t1_rows), "listed_total": len(hits),
                      "list": [{"created": r["created"].isoformat(), "name": r["name"],
                                "url": r["url"]} for r in hits[:STALLED_LIST_MAX]]}
    else:
        stalled_t1 = {"count": stalled, "count_source": "--rows", "approximate": True,
                      "stall_days": stall_days, "names_supplied": False, "t1_records": None,
                      "listed_total": None, "list": []}

    if t1_rows and all(r["_has_cert"] for r in t1_rows):
        t1_prov = sum(r["n"] for r in t1_rows
                      if not r["exclude"] and tier_of(r) == T1 and r["cert"] == "PROVISIONAL")
        t1_prov_source = "--t1-rows"
    else:
        t1_prov, t1_prov_source = t1_provisional, "--rows"

    logged = totals["logged_rows"]
    if first_rows == 0:
        basis = BASIS_CURRENT
    elif first_rows == logged:
        basis = BASIS_FIRST
    else:
        basis = "mixed (%d of %d first-sighting)" % (first_rows, logged)

    return {
        "schema": SCHEMA,
        "report_only": True,
        "today": today.isoformat(),
        "params": {"eras": [{"name": name, "start": start.isoformat()} for name, start in eras],
                   "stall_days": stall_days, "min_n": min_n, "rows_files": list(rows_files),
                   "t1_rows_files": list(t1_files), "pexec_rows_files": list(pexec_files),
                   "expect_rows_file": expect_file, "dup_rows_files": list(dup_files)},
        "totals": totals,
        "tier_vs_decision": tiers,
        "funnel": funnel,
        "source_yield": {"by_source": sources,
                         "other_or_blank": rate(other_or_blank, logged, min_n)},
        "pexec_calibration": calibration,
        "loss_class_mix": loss,
        "stalled_t1": stalled_t1,
        "data_quality": {
            "records": totals["records"], "rows": totals["rows"],
            "excluded_rows": totals["excluded_rows"],
            "p_exec_percent_normalized": percent, "p_exec_source": calibration["source"],
            "t1_provisional": t1_prov, "t1_provisional_source": t1_prov_source,
            "no_verdict": no_verdict,
            "dead_without_decision": dead, "dead_without_decision_t1": dead_t1,
            "tier_from_current_verdict": logged - first_rows,
            "tier_basis": {"label": basis, "first_sighting_rows": first_rows,
                           "logged_rows": logged},
            "row_count_reconciliation": reconciliation,
            "duplicate_recovery": dict(dup_stats) if dup_stats else {"status": "not-run"}},
        "definitions": list(DEFINITIONS),
    }


# --- render -------------------------------------------------------------------------------

def _cell(value):
    """Make a value safe inside a markdown table cell."""
    return str(value).replace("|", r"\|").replace("\r", " ").replace("\n", " ")


def render_markdown(res):
    params, totals = res["params"], res["totals"]
    eras = list(res["tier_vs_decision"])
    cal, st, dq = res["pexec_calibration"], res["stalled_t1"], res["data_quality"]
    out = [TITLE % res["today"], ""]
    files = (" from %d --rows file(s)" % len(params["rows_files"])) if params["rows_files"] else ""
    extra = ""
    if st["t1_records"] is not None:
        extra += "; --t1-rows: %d record(s)" % st["t1_records"]
    if cal["source_records"] is not None:
        extra += "; --pexec-rows: %d record(s)" % cal["source_records"]
    out.append("Input: %d record(s) = %d row(s)%s (%d excluded, %d logged)%s."
               % (totals["records"], totals["rows"], files, totals["excluded_rows"],
                  totals["logged_rows"], extra))
    if params["eras"]:
        bounds = (["baseline (before %s)" % params["eras"][0]["start"]]
                  + ["%s (from %s)" % (_cell(e["name"]), e["start"]) for e in params["eras"]])
    else:
        bounds = ["baseline (no boundaries)"]
    out.append("Eras: %s. Stall threshold: %d days. Rates print at n >= %d."
               % (", ".join(bounds), params["stall_days"], params["min_n"]))
    out.append("Tier basis: %s." % dq["tier_basis"]["label"])
    out.append("")

    out += ["### 1. Tier vs decision (held = go / decided; Wilson 95%)", "",
            "| Era | Tier | Logged | Decided | Go | Rejected | Withdrawn | Open | Held (strict) "
            "| Held incl. Dead |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|---|"]
    for era in eras:
        for tier, c in res["tier_vs_decision"][era].items():
            out.append("| %s | %s | %d | %d | %d | %d | %d | %d | %s | %s |"
                       % (_cell(era), tier, c["logged"], c["decided"], c["go"], c["rejected"],
                          c["withdrawn"], c["open"], format_rate(c["held"]),
                          format_rate(c["held_incl_dead"])))
    out.append("")

    funnel = res["funnel"]
    stages = (
        ("Logged", lambda f: str(f["logged"])),
        ("Withdrawn (Dead, no decision; outside every rate)", lambda f: str(f["withdrawn"])),
        ("Scorecard done / (logged - withdrawn)",
         lambda f: format_rate(f["rates"]["scorecard_of_eligible"])),
        ("Go decision with scorecard / scorecard done",
         lambda f: format_rate(f["rates"]["go_of_scorecard"])),
        ("Advanced to LOI / go decision", lambda f: format_rate(f["rates"]["loi_of_go"])),
        ("Won / advanced to LOI", lambda f: format_rate(f["rates"]["won_of_loi"])),
        ("Go decision without scorecard", lambda f: str(f["go_without_scorecard"])),
    )
    out += ["### 2. Funnel conversion", "",
            "| Stage | " + " | ".join(_cell(era) for era in eras) + " |",
            "|---|" + "---|" * len(eras)]
    for label, show in stages:
        out.append("| %s | %s |" % (label, " | ".join(show(funnel[era]) for era in eras)))
    out.append("")

    sy = res["source_yield"]
    out += ["### 3. Source yield (all eras)", "",
            "| Source | Logged | T1 | Decided | Go | LOI | Won |",
            "|---|---:|---:|---:|---:|---:|---:|"]
    for name, c in sy["by_source"].items():
        out.append("| %s | %d | %d | %d | %d | %d | %d |"
                   % (name, c["logged"], c["t1"], c["decided"], c["go"], c["loi"], c["won"]))
    out += ["", "Other or blank source: %s of logged rows." % format_rate(sy["other_or_blank"]), ""]

    out += ["### 4. P(exec) calibration", ""]
    if cal["source"] == "--pexec-rows":
        out.append("Source: --pexec-rows (%d record(s)); never added to any other count."
                   % cal["source_records"])
    else:
        out.append("Source: p_exec values in --rows.")
        if cal["with_p_exec"] == 0:
            out.append("No p_exec values in --rows (Query A does not export P(exec)); pass "
                       "--pexec-rows (Query P).")
    counts = ("Resolved: %d | unresolved (PENDING or blank; counted, not scored): %d | "
              "resolved without p_exec (not scored): %d"
              % (cal["resolved_n"], cal["unresolved_n"], cal["resolved_without_p_exec"]))
    if cal["insufficient_sample"]:
        out += ["", "**INSUFFICIENT SAMPLE (resolved n=%d < %d)** - statistics withheld; counts "
                "only." % (cal["resolved_n"], cal["min_resolved"]), "", counts, "",
                "| Bin | n | Executed |", "|---|---:|---:|"]
        for b in cal["bins"]:
            out.append("| %s | %d | %d |" % (b["bin"], b["n"], b["executed"]))
    else:
        out += ["", counts, ""]
        if cal["brier"] is None:
            out += ["Statistics withheld: resolved n=%d (n<%d)."
                    % (cal["resolved_n"], cal["base_rate"]["min_n"]), ""]
        else:
            skill = "-" if cal["brier_skill"] is None else "%.3f" % cal["brier_skill"]
            out += ["| Brier | Base rate | Reference Brier | Brier skill |",
                    "|---:|---|---:|---:|",
                    "| %.3f | %s | %.3f | %s |" % (cal["brier"], format_rate(cal["base_rate"]),
                                                  cal["reference_brier"], skill), ""]
        out += ["| Bin | n | Mean predicted | Observed |", "|---|---:|---:|---|"]
        for b in cal["bins"]:
            mean = "-" if b["mean_predicted"] is None else "%.2f" % b["mean_predicted"]
            out.append("| %s | %d | %s | %s |" % (b["bin"], b["n"], mean, format_rate(b["observed"])))
    out.append("")

    mix = res["loss_class_mix"]
    out += ["### 5. Loss class mix (non-null loss_class)", "", "| Loss class | Rows |", "|---|---:|"]
    for name, k in mix.items():
        out.append("| %s | %d |" % (name, k))
    out += ["| Total classified | %d |" % sum(mix.values()), ""]

    out += ["### 6. Stalled T1 (open T1 PURSUE created more than %d days before %s)"
            % (st["stall_days"], res["today"]), ""]
    if st["approximate"]:
        out.append("Count: %d row(s) (%s)." % (st["count"], APPROXIMATE))
        out.append("Names: names not supplied (pass --t1-rows from Query B for exact dates and "
                   "names).")
    else:
        out.append("Count: %d row(s) (exact: --t1-rows per-row dates; never added to any other "
                   "count)." % st["count"])
        if st["list"]:
            out += ["", "| Created | Name | URL |", "|---|---|---|"]
            for item in st["list"]:
                out.append("| %s | %s | %s |" % (item["created"], _cell(item["name"] or "(unnamed)"),
                                                 _cell(item["url"] or "-")))
            if st["listed_total"] > len(st["list"]):
                out += ["", "(showing %d of %d, oldest first)" % (len(st["list"]), st["listed_total"])]
        else:
            out.append("No stalled T1 rows in --t1-rows.")
    out.append("")

    recon = dq["row_count_reconciliation"]
    if recon["status"] == "ok":
        recon_line = ("row-count reconciliation: OK (--rows cover all %d rows in the log; QUERY N)"
                      % recon["expected_rows"])
    else:
        recon_line = "row-count reconciliation: NOT RUN (no --expect-rows)"
    out += ["### 7. Data quality", "", "| Check | Rows |", "|---|---:|",
            "| Excluded (dropped from every metric) | %d |" % dq["excluded_rows"],
            "| p_exec typed as a whole-number percent, divided by 100 (source: %s) | %d |"
            % (dq["p_exec_source"], dq["p_exec_percent_normalized"]),
            "| T1 PURSUE with cert PROVISIONAL (source: %s) | %d |"
            % (dq["t1_provisional_source"], dq["t1_provisional"]),
            "| No verdict (tier blank) | %d |" % dq["no_verdict"],
            "| Tier from the current Verdict (no verdict_first; may be overwritten by later "
            "decisions) | %d of %d |" % (dq["tier_from_current_verdict"],
                                        dq["tier_basis"]["logged_rows"]),
            "| Total records / weighted rows | %d / %d |" % (dq["records"], dq["rows"]),
            "",
            "closed as Dead with no Go / No-Go decision: %d (of which T1: %d) - record quality "
            "passes as Go / No-Go = Pass so calibration can tell them from withdrawn listings"
            % (dq["dead_without_decision"], dq["dead_without_decision_t1"]),
            "",
            recon_line,
            "",
            _dup_line(dq["duplicate_recovery"]),
            ""]

    out += ["### Definitions", ""] + ["- " + text for text in res["definitions"]]
    return "\n".join(out) + "\n"


def _dup_line(dup):
    if dup["status"] != "run":
        return "duplicate recovery: NOT RUN (no --dup-rows)"
    return ("duplicate recovery (--dup-rows, QUERY D): %d set(s); %d flagged duplicate row(s), "
            "%d moved to excluded (Duplicate Of set, Exclude unticked); first sighting recovered "
            "on %d kept row(s), replaced by an earlier sighting on %d; %d Duplicate Of target(s) "
            "not found" % (dup["sets"], dup["flagged"], dup["moved_to_excluded"], dup["recovered"],
                           dup["replaced"], dup["unresolved"]))


def summary_line(res):
    held = " ".join("%s=%d/%d" % (era, tiers[T1]["go"], tiers[T1]["decided"])
                    for era, tiers in res["tier_vs_decision"].items())
    return "[BACKTEST] today=%s rows=%d records=%d t1_held %s" % (
        res["today"], res["totals"]["rows"], res["totals"]["records"], held)


# --- CLI ----------------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="funnel-backtest.py",
        description="Sourcing funnel back-test (REPORT-ONLY): Deal Sourcing Log exports -> "
                    "calibration evidence. Never changes a score weight, band, gate, doctrine "
                    "file or Notion; any change needs Gabriel's sign-off.",
        epilog="Export contract (Query A/B/P/N), field contract and metric definitions: see the "
               "module docstring. Exit 0 = report produced; 2 = input error (one [FATAL] line).")
    parser.add_argument("--rows", action="append", required=True, metavar="FILE",
                        help="grouped Query A export; repeatable, one file per verdict partition")
    parser.add_argument("--t1-rows", action="append", metavar="FILE",
                        help="per-row Query B export: the stalled-T1 count and names (and T1 "
                             "cert) only; never added to any other count")
    parser.add_argument("--pexec-rows", action="append", metavar="FILE",
                        help="per-row Query P export: the P(exec) calibration only; never added "
                             "to any other count")
    parser.add_argument("--expect-rows", metavar="FILE",
                        help="Query N result (the log's row count): exit 2 unless the --rows "
                             "partitions, excluded rows included, cover every row")
    parser.add_argument("--dup-rows", action="append", metavar="FILE",
                        help="per-row Query D export (duplicate sets): flagged duplicates are "
                             "excluded and each kept row takes its set's earliest first-sighting "
                             "prediction; never adds or removes a row")
    parser.add_argument("--era", action="append", metavar="NAME=YYYY-MM-DD",
                        help="era boundary; repeatable (default v2.9=2026-10-30; any --era "
                             "replaces the default; must match Query A's CASE)")
    parser.add_argument("--today", metavar="YYYY-MM-DD", help="as-of date (default: local today)")
    parser.add_argument("--stall-days", type=int, default=14, metavar="N",
                        help="an open T1 older than N days is stalled (default 14)")
    parser.add_argument("--min-n", type=int, default=5, metavar="N",
                        help="print a rate only when its denominator >= N (default 5)")
    parser.add_argument("--out-md", metavar="PATH",
                        help="write the markdown here as UTF-8 instead of printing it")
    parser.add_argument("--json", action="store_true",
                        help="print the computed result as JSON instead of markdown")
    return parser


def main(argv=None):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # --help (0) or a usage error (2); argparse already printed it
        if exc.code is None:
            return 0
        return exc.code if isinstance(exc.code, int) else 2
    try:
        if args.today is None:
            today = date.today()
        else:
            today = _parse_day(args.today)
            if today is None:
                raise InputError("--today %r is not a YYYY-MM-DD date" % args.today)
        eras = build_eras([parse_era(text) for text in args.era] if args.era
                          else list(DEFAULT_ERAS))
        if args.stall_days < 0:
            raise InputError("--stall-days %d is negative" % args.stall_days)
        if args.min_n < 1:
            raise InputError("--min-n %d must be >= 1" % args.min_n)
        records = load_records(args.rows, "--rows")
        t1_rows = load_records(args.t1_rows, "--t1-rows") if args.t1_rows else None
        pexec_rows = load_records(args.pexec_rows, "--pexec-rows") if args.pexec_rows else None
        expected = load_expected_rows(args.expect_rows) if args.expect_rows else None
        dup_records = load_dup_records(args.dup_rows) if args.dup_rows else None
        records, t1_rows, dup_stats = apply_duplicates(records, dup_records, t1_rows)
        result = aggregate(records, eras, today, args.stall_days, args.min_n, t1_rows=t1_rows,
                           pexec_rows=pexec_rows, rows_files=args.rows,
                           t1_files=args.t1_rows or (), pexec_files=args.pexec_rows or (),
                           expected_rows=expected, expect_file=args.expect_rows,
                           dup_stats=dup_stats, dup_files=args.dup_rows or ())
        markdown = render_markdown(result)
        if args.out_md:
            try:
                with open(args.out_md, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(markdown)
            except OSError as exc:
                raise InputError("cannot write --out-md %s: %s" % (args.out_md, exc))
    except InputError as exc:
        print("[FATAL] %s" % exc, file=sys.stderr)
        return 2
    if args.json:
        sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=True) + "\n")
    elif not args.out_md:
        sys.stdout.write(markdown)
    print(summary_line(result), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
