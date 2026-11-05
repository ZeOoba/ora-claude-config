#!/usr/bin/env python3
"""Tests for funnel-backtest.py -- the December sourcing back-test engine (TDD).

What is pinned here, and why:
  * INPUT CONTRACT -- an unknown select value (including a near miss, such as an ASCII
    hyphen where the Go option has an em dash) is FATAL: one [FATAL] line, exit 2, never a
    traceback and never a silent bucket. The option sets were read from the live Notion
    schema on 2026-11-05 and a schema change must be loud. Checkbox, p_exec (a non-whole
    value above 1 is ambiguous), n, created, verdict_first and score_first parsing;
    "results"-wrapped and BOM-prefixed exports; any has_more other than absent/null/false is
    refused on every input flag.
  * EXPORT CONTRACT -- QUERY_A / QUERY_B / QUERY_P / QUERY_N are module constants documented
    verbatim. QUERY_A run per verdict partition through sqlite3 (Notion column names) yields
    the same metrics as the same fixture rows fed per-row, and --expect-rows (QUERY_N) catches
    a row whose Verdict falls in no partition (a new option, or a blank string pre-fix).
  * MUTATION GAPS from the adversarial pass -- weighted Brier (M13) and the first-sighting
    tier on the --t1-rows PROVISIONAL count (M20) each have a test an unweighted / current-
    Verdict mutant fails.
  * CLASSIFICATION -- every branch, including EXPIRED-UNSENT (a go decision that never
    became an LOI) and Dead (withdrawn: outside the strict denominator, not a rejection), and
    the second "held incl. Dead" rate that counts every closed row as not-held.
  * ERAS -- the boundary date belongs to the NEW era; any --era replaces the default.
  * STATISTICS -- Wilson 95% interval and Brier score against hand-computed values; every
    count weighted by n.
  * RATE DISCIPLINE -- below min-n a rate prints as raw k/n (n<MIN); a zero denominator
    prints "-", never 0%.
  * AUXILIARY EXPORTS -- --t1-rows (stalled-T1 count and list, exact dates) and --pexec-rows
    (P(exec) calibration) are never added to any other count.
  * REPORT SURFACE -- markdown section headers, tier-basis label, stable --json keys, exactly
    one [BACKTEST] stderr line, and the 2026-10-30 hand back-test replayed (0 of 8 held).

Non-ASCII option strings are written as 8-digit escapes (U+2014 em dash as a capital-U
escape) so this source stays ASCII.

HERMETIC: every fixture is synthetic ("Fixture Flex 01", example.test URLs) and lives in a
temp dir or an in-memory sqlite3 table; nothing reads Notion or the live Deal Sourcing Log.

Run: python test-funnel-backtest.py
Stdlib only. ASCII-only.
"""
import contextlib
import importlib.util
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE_PATH = os.path.join(HERE, "funnel-backtest.py")
spec = importlib.util.spec_from_file_location("funnel_backtest", MODULE_PATH)
fb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fb)

# Option strings exactly as the live schema spells them (escaped, so this source stays ASCII).
BROKER = "Broker \U00002014 Direct"
GO_SUBMIT = "\U0001F7E2 Go \U00002014 Submit LOI"
GO_MAYBE = "\U0001F7E1 Maybe \U00002014 Need More Info"
GO_PASS = "\U0001F534 Pass"
GO_REVIEW = "\U000023F3 Under Review"
LOSS_CLASSES = ("UNCLASSIFIED", "BASIS-DISCIPLINE", "NON-COMPARABLE BUYER", "BASIS-ELECTIVE",
                "PRICE-MARGINAL", "EXECUTION", "WINNER-BUSTED")

V29 = date(2026, 10, 30)
TODAY = date(2026, 12, 15)
TITLE = ("## Sourcing back-test - 2026-12-15 (report-only; any weight/band/gate change "
         "needs Gabriel's sign-off)")
SECTION_HEADERS = ("### 1. Tier vs decision", "### 2. Funnel conversion", "### 3. Source yield",
                   "### 4. P(exec) calibration", "### 5. Loss class mix", "### 6. Stalled T1",
                   "### 7. Data quality", "### Definitions")
JSON_KEYS = {"schema", "report_only", "today", "params", "totals", "tier_vs_decision", "funnel",
             "source_yield", "pexec_calibration", "loss_class_mix", "stalled_t1", "data_quality",
             "definitions"}
BASIS_CURRENT = ("current Verdict (may be overwritten by later decisions; calibration "
                 "understates T1 misses)")
BASIS_FIRST = "first-sighting (write-once)"
APPROXIMATE = "approximate: uses --rows created dates, which may be era-bucketed"
TRUNCATED = "export truncated (has_more=true); re-run the query with coarser buckets"


# --- helpers ---------------------------------------------------------------------------

def rec(**fields):
    """One normalized record; created defaults to a date inside the default v2.9 era."""
    raw = {"created": "2026-11-02"}
    raw.update(fields)
    return fb.normalize_record(raw, 0, "fixture")


def agg(records, eras=None, today=TODAY, stall_days=14, min_n=5, t1_rows=None, pexec_rows=None):
    if eras is None:
        eras = fb.build_eras([("v2.9", V29)])
    return fb.aggregate(records, eras, today, stall_days, min_n, t1_rows=t1_rows,
                        pexec_rows=pexec_rows)


def expect_input_error(fn, *needles):
    try:
        fn()
    except fb.InputError as exc:
        msg = str(exc)
        for needle in needles:
            assert needle in msg, "expected %r in %r" % (needle, msg)
        return msg
    raise AssertionError("expected an InputError, none was raised")


def write_json(folder, name, payload, encoding="utf-8", ensure_ascii=True):
    path = os.path.join(folder, name)
    with open(path, "w", encoding=encoding) as fh:
        json.dump(payload, fh, ensure_ascii=ensure_ascii)
    return path


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = fb.main(argv)
    return rc, out.getvalue(), err.getvalue()


def table_row(md, *prefix_cells):
    prefix = "| " + " | ".join(prefix_cells) + " |"
    hits = [line for line in md.splitlines() if line.startswith(prefix)]
    assert len(hits) == 1, "expected exactly one row starting %r, got %r" % (prefix, hits)
    return hits[0]


def section(md, header):
    """The markdown between one '### ' header and the next."""
    start = md.index(header)
    end = md.find("\n### ", start + 1)
    return md[start:] if end < 0 else md[start:end]


# --- input contract ----------------------------------------------------------------------

def test_option_sets_match_live_schema_2026_11_05_unit():
    """Double entry on purpose: a schema change has to touch the engine AND this pin."""
    assert fb.SOURCE_OPTIONS == ("Crexi", BROKER, "Off-Market", "LoopNet", "CoStar", "Other")
    assert fb.VERDICT_OPTIONS == ("T1 PURSUE", "T2 WATCH", "PASS", "KILLED")
    assert fb.FLOOR_OPTIONS == ("PASS", "FAIL-BASIS", "FAIL-YIELD", "FAIL-BOTH", "N/A")
    assert fb.STATUS_OPTIONS == ("New Lead", "Reviewing", "LOI Submitted", "Under PSA", "Passed",
                                 "Dead", "Screened")
    assert fb.GO_OPTIONS == (GO_SUBMIT, GO_MAYBE, GO_PASS, GO_REVIEW)
    assert fb.LOI_OUTCOME_OPTIONS == ("PENDING", "WON", "LOST", "SELLER-PULLED", "EXPIRED-UNSENT",
                                      "WINNER-BUSTED", "TERMINATED-DILIGENCE")
    assert fb.LOSS_CLASS_OPTIONS == LOSS_CLASSES
    assert fb.CERT_OPTIONS == ("PROVISIONAL", "CERTIFIED")
    assert [ord(c) for c in GO_SUBMIT[:1] + BROKER[7] + GO_REVIEW[:1]] == [0x1F7E2, 0x2014, 0x23F3]
    print("  PASS test_option_sets_match_live_schema_2026_11_05_unit")


def test_known_select_values_and_blanks_unit():
    r = rec(source=BROKER, verdict="T1 PURSUE", floor="FAIL-BOTH", status="Under PSA", go=GO_SUBMIT,
            loi_outcome="TERMINATED-DILIGENCE", loss_class="NON-COMPARABLE BUYER", cert="PROVISIONAL",
            verdict_first="T2 WATCH")
    assert r["source"] == BROKER and r["go"] == GO_SUBMIT and r["floor"] == "FAIL-BOTH"
    assert r["loss_class"] == "NON-COMPARABLE BUYER" and r["cert"] == "PROVISIONAL"
    assert r["verdict_first"] == "T2 WATCH"
    for field in ("source", "verdict", "verdict_first", "floor", "status", "go", "loi_outcome",
                  "loss_class", "cert"):
        assert rec(**{field: None})[field] is None, field
        assert rec(**{field: ""})[field] is None, field  # an empty string carries no option
        assert rec()[field] is None, field
    print("  PASS test_known_select_values_and_blanks_unit")


def test_unknown_select_value_is_fatal_unit():
    cases = (("verdict", "T3 MAYBE"), ("source", "Craigslist"), ("status", "Closed"),
             ("go", "\U0001F7E2 Go - Submit LOI"),  # ASCII hyphen: a near miss must still be loud
             ("loi_outcome", "won"), ("loss_class", "PRICE"), ("cert", "DRAFT"), ("floor", "FAIL"),
             ("verdict_first", "T1"), ("verdict", "T1 PURSUE "), ("source", ["Crexi"]),
             ("status", 3))
    for field, bad in cases:
        msg = expect_input_error(
            lambda: fb.normalize_record({"created": "2026-11-02", field: bad}, 4, "rows.json"))
        assert msg == "row 4 (rows.json): %s=%r is not a known option" % (field, bad), msg
    print("  PASS test_unknown_select_value_is_fatal_unit")


def test_unknown_select_value_main_returns_2_with_fatal_line_e2e():
    with tempfile.TemporaryDirectory(prefix="fbt-") as tmp:
        path = write_json(tmp, "rows.json", [{"created": "2026-11-01", "verdict": "T1 PURSUE"},
                                             {"created": "2026-11-02", "verdict": "T3 MAYBE"}])
        rc, out, err = run_main(["--rows", path, "--today", "2026-12-15"])
        assert rc == 2, (rc, err)
        assert "[FATAL] row 1 (%s): verdict='T3 MAYBE' is not a known option" % path in err, err
        assert "Traceback" not in err and "[BACKTEST]" not in err and out == "", err
        # The real process: exit code 2 and no traceback, exactly as the scheduled run sees it.
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run([sys.executable, MODULE_PATH, "--rows", path, "--today", "2026-12-15"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=120, env=env)
        assert proc.returncode == 2, (proc.returncode, proc.stderr)
        assert "[FATAL] row 1 (" in proc.stderr and "Traceback" not in proc.stderr, proc.stderr
        assert proc.stdout == "", proc.stdout
    print("  PASS test_unknown_select_value_main_returns_2_with_fatal_line_e2e")


def test_missing_or_unparseable_created_is_fatal_unit():
    for raw in ({}, {"created": None}, {"created": ""}, {"created": "10/30/2026"},
                {"created": "2026-02-30"}, {"created": 20261030}, {"created": "2026-10-30junk"}):
        expect_input_error(lambda: fb.normalize_record(raw, 0, "rows.json"),
                           "row 0 (rows.json): created=")
    expect_input_error(lambda: fb.normalize_record(["not", "an", "object"], 2, "rows.json"),
                       "row 2 (rows.json)")
    print("  PASS test_missing_or_unparseable_created_is_fatal_unit")


def test_created_iso_datetime_takes_the_date_part_unit():
    assert rec(created="2026-10-30")["created"] == date(2026, 10, 30)
    assert rec(created="2026-10-30T03:15:00.000Z")["created"] == date(2026, 10, 30)
    assert rec(created="2026-10-29T23:59:59-04:00")["created"] == date(2026, 10, 29)
    assert rec(created="2026-10-30 08:00:00")["created"] == date(2026, 10, 30)
    print("  PASS test_created_iso_datetime_takes_the_date_part_unit")


def test_checkbox_variants_unit():
    for value, want in ((True, True), ("__YES__", True), (False, False), ("__NO__", False),
                        (None, False), ("", False)):
        assert rec(scorecard=value)["scorecard"] is want, value
        assert rec(exclude=value)["exclude"] is want, value
    absent = rec()
    assert absent["scorecard"] is False and absent["exclude"] is False
    for bad in (1, 0, "yes", "true", "__yes__", "YES"):
        expect_input_error(lambda: rec(scorecard=bad), "scorecard=%r is not a known option" % (bad,))
        expect_input_error(lambda: rec(exclude=bad), "exclude=%r is not a known option" % (bad,))
    print("  PASS test_checkbox_variants_unit")


def test_p_exec_fraction_and_percent_normalization_unit():
    cases = ((0.6, 0.6, False), (0, 0.0, False), (1, 1.0, False), (0.05, 0.05, False),
             (60, 0.6, True), (60.0, 0.6, True), (2, 0.02, True), (100, 1.0, True),
             (None, None, False), ("", None, False))
    for value, want, percent in cases:
        r = rec(p_exec=value)
        if want is None:
            assert r["p_exec"] is None, value
        else:
            assert abs(r["p_exec"] - want) < 1e-12, (value, r["p_exec"])
        assert r["p_exec_percent"] is percent, value
    recs = [rec(p_exec=60, n=2), rec(p_exec=75), rec(p_exec=0.5, n=3), rec(p_exec=40, exclude=True)]
    dq = agg(recs)["data_quality"]
    assert dq["p_exec_percent_normalized"] == 3 and dq["p_exec_source"] == "--rows", dq
    print("  PASS test_p_exec_fraction_and_percent_normalization_unit")


def test_p_exec_out_of_range_or_non_numeric_is_fatal_unit():
    for bad in (-0.1, -5, 100.5, 150, 10 ** 400, "0.6", "60%", True, False, [0.5],
                float("nan"), float("inf")):
        expect_input_error(lambda: rec(p_exec=bad), "p_exec=")
    with tempfile.TemporaryDirectory(prefix="fbt-") as tmp:
        path = write_json(tmp, "rows.json", [{"created": "2026-11-02", "p_exec": 150}])
        rc, out, err = run_main(["--rows", path])
        assert rc == 2 and err.startswith("[FATAL] row 0 (%s): p_exec=150 " % path), err
        assert "Traceback" not in err
    print("  PASS test_p_exec_out_of_range_or_non_numeric_is_fatal_unit")


def test_p_exec_non_whole_value_above_one_is_ambiguous_unit():
    """Above 1 a p_exec can only be a whole-number percent. 1.5 is neither a fraction nor a
    whole percent, so it is refused instead of being read silently as 1.5%."""
    for bad in (1.5, 62.5, 99.99, 1.0000001, 100.0 - 1e-9):
        expect_input_error(lambda: rec(p_exec=bad), "p_exec=%r is ambiguous" % (bad,))
    with tempfile.TemporaryDirectory(prefix="fbt-") as tmp:
        path = write_json(tmp, "rows.json", [{"created": "2026-11-02", "p_exec": 1.5}])
        rc, out, err = run_main(["--rows", path])
        assert rc == 2 and err.startswith("[FATAL] row 0 (%s): p_exec=1.5 is ambiguous" % path), err
        assert "Traceback" not in err and out == ""
    print("  PASS test_p_exec_non_whole_value_above_one_is_ambiguous_unit")


def test_n_weighting_unit():
    recs = [rec(verdict="T1 PURSUE", status="Passed", n=3),  # grouped: counts 3
            rec(verdict="T1 PURSUE", go=GO_SUBMIT),          # per-row: counts 1
            rec(verdict="T2 WATCH", n=4)]
    res = agg(recs, min_n=1)
    t1 = res["tier_vs_decision"]["v2.9"]["T1 PURSUE"]
    assert (t1["logged"], t1["decided"], t1["go"], t1["rejected"]) == (4, 4, 1, 3), t1
    assert (t1["held"]["k"], t1["held"]["n"]) == (1, 4)
    assert res["tier_vs_decision"]["v2.9"]["T2 WATCH"]["open"] == 4
    assert res["totals"]["records"] == 3 and res["totals"]["rows"] == 8
    assert res["funnel"]["v2.9"]["logged"] == 8
    assert res["source_yield"]["by_source"]["(blank)"]["logged"] == 8
    print("  PASS test_n_weighting_unit")


def test_n_must_be_an_integer_of_at_least_one_unit():
    for bad in (0, -1, "3", 2.5, 3.0, True, None):
        expect_input_error(lambda: rec(n=bad), "n=%r is not an integer >= 1" % (bad,))
    assert rec()["n"] == 1 and rec(n=7)["n"] == 7
    print("  PASS test_n_must_be_an_integer_of_at_least_one_unit")


# --- classification ----------------------------------------------------------------------

def C(**fields):
    return fb.classify(rec(**fields))


def test_classify_go_decision_branches_unit():
    assert C(go=GO_SUBMIT) == "go"
    assert C(loi_sent="2026-11-03") == "go"
    assert C(status="LOI Submitted") == "go"
    assert C(status="Under PSA") == "go"
    for outcome in ("PENDING", "WON", "LOST", "SELLER-PULLED", "WINNER-BUSTED", "TERMINATED-DILIGENCE"):
        assert C(loi_outcome=outcome) == "go", outcome
        assert fb.is_advanced_to_loi(rec(loi_outcome=outcome)) is True, outcome
    assert fb.is_advanced_to_loi(rec(go=GO_SUBMIT)) is False  # a go is not yet an LOI
    # a go decision beats a later Pass / Passed / Dead
    assert C(go=GO_PASS, loi_sent="2026-11-03") == "go"
    assert C(status="Passed", loi_outcome="LOST") == "go"
    assert C(status="Dead", loi_outcome="SELLER-PULLED") == "go"
    print("  PASS test_classify_go_decision_branches_unit")


def test_expired_unsent_is_go_but_not_advanced_unit():
    r = rec(loi_outcome="EXPIRED-UNSENT", status="Passed")
    assert fb.classify(r) == "go"
    assert fb.is_advanced_to_loi(r) is False
    f = agg([r], min_n=1)["funnel"]["v2.9"]
    assert (f["go"], f["loi"]) == (1, 0), f
    print("  PASS test_expired_unsent_is_go_but_not_advanced_unit")


def test_classify_rejected_branches_unit():
    assert C(go=GO_PASS) == "rejected"
    assert C(status="Passed") == "rejected"
    assert C(status="Passed", go=GO_MAYBE) == "rejected"
    assert C(go=GO_PASS, status="Dead") == "rejected"  # rejected beats withdrawn
    print("  PASS test_classify_rejected_branches_unit")


def test_dead_is_withdrawn_and_outside_the_strict_denominator_unit():
    assert C(status="Dead") == "withdrawn"
    assert C(status="Dead", go=GO_MAYBE) == "withdrawn"
    assert C(status="Dead", go=GO_REVIEW, scorecard=True) == "withdrawn"
    recs = [rec(verdict="T1 PURSUE", go=GO_SUBMIT), rec(verdict="T1 PURSUE", status="Passed"),
            rec(verdict="T1 PURSUE", status="Dead", n=3)]
    t1 = agg(recs, min_n=1)["tier_vs_decision"]["v2.9"]["T1 PURSUE"]
    assert (t1["logged"], t1["withdrawn"], t1["decided"]) == (5, 3, 2), t1
    assert (t1["held"]["k"], t1["held"]["n"]) == (1, 2), t1["held"]
    print("  PASS test_dead_is_withdrawn_and_outside_the_strict_denominator_unit")


def test_held_incl_dead_second_rate_unit():
    """Live evidence: quality passes are often recorded as Status Dead with no Go / No-Go value,
    so Dead conflates "listing gone" with "passed on quality". Strict held keeps Dead out of
    the denominator; held incl. Dead counts every closed row as not-held.
    Fixture: 3 Dead + 1 Pass + 0 Go T1 rows -> strict 0/1, incl. Dead 0/4."""
    recs = [rec(verdict="T1 PURSUE", status="Dead", n=2), rec(verdict="T1 PURSUE", status="Dead"),
            rec(verdict="T1 PURSUE", go=GO_PASS),
            rec(verdict="T2 WATCH", status="Dead", go=GO_MAYBE)]  # Dead, no decision, not T1
    res = agg(recs)
    t1 = res["tier_vs_decision"]["v2.9"]["T1 PURSUE"]
    assert (t1["held"]["k"], t1["held"]["n"]) == (0, 1), t1["held"]
    assert (t1["held_incl_dead"]["k"], t1["held_incl_dead"]["n"]) == (0, 4), t1["held_incl_dead"]
    assert t1["held_incl_dead"]["status"] == "n<min"
    dq = res["data_quality"]
    assert (dq["dead_without_decision"], dq["dead_without_decision_t1"]) == (4, 3), dq
    md = fb.render_markdown(res)
    assert table_row(md, "v2.9", "T1 PURSUE").rstrip().endswith("| 0/1 (n<5) | 0/4 (n<5) |")
    assert ("closed as Dead with no Go / No-Go decision: 4 (of which T1: 3) - record quality passes "
            "as Go / No-Go = Pass so calibration can tell them from withdrawn listings") in md
    assert "strict: Dead excluded; incl. Dead: every closed row counts as not-held" in \
        section(md, "### Definitions")
    row1 = table_row(fb.render_markdown(agg(recs, min_n=1)), "v2.9", "T1 PURSUE")
    assert "| 0/1 = 0.0% [0.0-79.3%] | 0/4 = 0.0% [0.0-49.0%] |" in row1, row1
    print("  PASS test_held_incl_dead_second_rate_unit")


def test_classify_open_unit():
    for fields in ({}, {"go": GO_MAYBE}, {"go": GO_REVIEW}, {"status": "New Lead"},
                   {"status": "Reviewing"}, {"status": "Screened"},
                   {"verdict": "T1 PURSUE", "scorecard": True, "p_exec": 0.4}):
        assert C(**fields) == "open", fields
    print("  PASS test_classify_open_unit")


def test_excluded_rows_are_dropped_from_every_metric_unit():
    assert C(exclude=True, go=GO_SUBMIT, loi_sent="2026-11-03") == "excluded"
    base = [rec(verdict="T1 PURSUE", status="Passed", source="Crexi", loss_class="BASIS-DISCIPLINE"),
            rec(created="2026-11-01", verdict="T1 PURSUE")]
    noise = rec(created="2026-11-01", verdict="T1 PURSUE", go=GO_SUBMIT, source="Crexi",
                loi_outcome="WON", p_exec=0.9, loss_class="EXECUTION", scorecard=True,
                cert="PROVISIONAL", exclude=True, n=5)
    stale_open = rec(created="2026-10-01", verdict="T1 PURSUE", status="Dead", exclude="__YES__", n=2)
    a, b = agg(base), agg(base + [noise, stale_open])
    for key in ("tier_vs_decision", "funnel", "source_yield", "pexec_calibration", "loss_class_mix",
                "stalled_t1"):
        assert a[key] == b[key], key
    assert (a["data_quality"]["excluded_rows"], b["data_quality"]["excluded_rows"]) == (0, 7)
    for key in ("t1_provisional", "dead_without_decision", "tier_basis"):
        assert a["data_quality"][key] == b["data_quality"][key], key
    assert (b["totals"]["records"], b["totals"]["rows"], b["totals"]["logged_rows"]) == (4, 9, 2)
    print("  PASS test_excluded_rows_are_dropped_from_every_metric_unit")


# --- tier basis: verdict_first -------------------------------------------------------------

def test_verdict_first_overrides_verdict_for_tier_unit():
    """Live evidence: Verdict is overwritten after a later review, so the scan's prediction is
    lost. verdict_first (first sighting, write-once) wins whenever the record carries it."""
    r = rec(verdict="T2 WATCH", verdict_first="T1 PURSUE", status="Passed", score_first=72)
    assert fb.tier_of(r) == "T1 PURSUE" and r["score_first"] == 72
    assert fb.tier_of(rec(verdict="T2 WATCH")) == "T2 WATCH"
    assert fb.tier_of(rec(verdict="T2 WATCH", verdict_first=None)) == "T2 WATCH"
    assert fb.tier_of(rec(verdict_first="KILLED")) == "KILLED"
    res = agg([r, rec(verdict="T2 WATCH", go=GO_SUBMIT)], min_n=1)
    tiers = res["tier_vs_decision"]["v2.9"]
    assert (tiers["T1 PURSUE"]["rejected"], tiers["T2 WATCH"]["go"], tiers["T2 WATCH"]["logged"]) == \
        (1, 1, 1), tiers
    assert res["source_yield"]["by_source"]["(blank)"]["t1"] == 1
    for good in (None, "", 0, 72, 7.5):
        rec(score_first=good)
    for bad in ("72", True, float("nan"), [1]):
        expect_input_error(lambda: rec(score_first=bad), "score_first=")
    print("  PASS test_verdict_first_overrides_verdict_for_tier_unit")


def test_tier_basis_label_none_all_mixed_unit():
    none = agg([rec(verdict="T1 PURSUE"), rec(verdict="T2 WATCH", n=2)])
    every = agg([rec(verdict_first="T1 PURSUE", verdict="PASS"), rec(verdict_first="T2 WATCH", n=2),
                 rec(verdict="KILLED", exclude=True)])  # an excluded row never counts
    mixed = agg([rec(verdict_first="T1 PURSUE", n=2), rec(verdict="T1 PURSUE", n=3)])
    cases = ((none, BASIS_CURRENT, 3), (every, BASIS_FIRST, 0),
             (mixed, "mixed (2 of 5 first-sighting)", 3))
    for res, label, from_current in cases:
        dq = res["data_quality"]
        assert dq["tier_basis"]["label"] == label, dq["tier_basis"]
        assert dq["tier_from_current_verdict"] == from_current, dq
        md = fb.render_markdown(res)
        assert ("Tier basis: " + label) in md.split("### 1.")[0], md.split("### 1.")[0]
    assert mixed["data_quality"]["tier_basis"]["first_sighting_rows"] == 2
    print("  PASS test_tier_basis_label_none_all_mixed_unit")


# --- eras --------------------------------------------------------------------------------

def test_era_boundary_is_inclusive_for_the_new_era_unit():
    eras = fb.build_eras([("v2.9", V29)])
    assert fb.era_of(date(2026, 10, 29), eras) == "baseline"
    assert fb.era_of(date(2026, 10, 30), eras) == "v2.9"
    assert fb.era_of(date(2027, 1, 1), eras) == "v2.9"
    two = fb.build_eras([("v3.0", date(2026, 12, 1)), ("v2.9", V29)])  # given out of order
    assert [name for name, _ in two] == ["v2.9", "v3.0"]
    assert fb.era_of(date(2026, 10, 29), two) == "baseline"
    assert fb.era_of(date(2026, 11, 30), two) == "v2.9"
    assert fb.era_of(date(2026, 12, 1), two) == "v3.0"
    res = agg([rec(created="2026-10-29", verdict="T1 PURSUE", status="Passed"),
               rec(created="2026-10-30T00:30:00.000Z", verdict="T1 PURSUE", go=GO_SUBMIT)], min_n=1)
    assert list(res["tier_vs_decision"]) == ["baseline", "v2.9"]
    assert res["tier_vs_decision"]["baseline"]["T1 PURSUE"]["rejected"] == 1
    assert res["tier_vs_decision"]["v2.9"]["T1 PURSUE"]["go"] == 1
    assert res["tier_vs_decision"]["baseline"]["T1 PURSUE"]["go"] == 0
    print("  PASS test_era_boundary_is_inclusive_for_the_new_era_unit")


def test_era_flag_default_override_and_errors_e2e():
    with tempfile.TemporaryDirectory(prefix="fbt-") as tmp:
        path = write_json(tmp, "rows.json", [{"created": "2026-11-02"}])
        common = ["--rows", path, "--today", "2026-12-15", "--json"]
        rc, out, err = run_main(common)
        assert rc == 0, err
        assert json.loads(out)["params"]["eras"] == [{"name": "v2.9", "start": "2026-10-30"}]
        rc, out, err = run_main(common + ["--era", "v3.0=2026-12-01", "--era", "v2.9=2026-10-30"])
        assert rc == 0, err
        assert [e["name"] for e in json.loads(out)["params"]["eras"]] == ["v2.9", "v3.0"]
        rc, out, err = run_main(common + ["--era", "v3.0=2026-12-01"])  # replaces, never appends
        assert rc == 0, err
        res = json.loads(out)
        assert res["params"]["eras"] == [{"name": "v3.0", "start": "2026-12-01"}]
        assert list(res["tier_vs_decision"]) == ["baseline", "v3.0"]
        for bad in (["v2.9"], ["=2026-10-30"], ["v3=2026-13-01"], ["baseline=2026-01-01"],
                    ["a=2026-10-30", "b=2026-10-30"], ["a=2026-10-30", "a=2026-11-30"]):
            argv = ["--rows", path]
            for item in bad:
                argv += ["--era", item]
            rc, out, err = run_main(argv)
            assert rc == 2 and err.startswith("[FATAL] --era"), (bad, err)
            assert "Traceback" not in err and out == "", (bad, err)
    print("  PASS test_era_flag_default_override_and_errors_e2e")


# --- statistics --------------------------------------------------------------------------

def test_wilson_interval_known_values_unit():
    lo, hi = fb.wilson(0, 8)
    assert lo == 0.0 and round(hi, 4) == 0.3244, (lo, hi)
    lo, hi = fb.wilson(5, 10)
    assert round(lo, 3) == 0.237 and round(hi, 3) == 0.763, (lo, hi)
    lo, hi = fb.wilson(8, 8)
    assert hi == 1.0 and round(lo, 4) == 0.6756, (lo, hi)
    assert fb.wilson(0, 0) is None
    print("  PASS test_wilson_interval_known_values_unit")


def test_brier_known_value_unit():
    s = fb.brier_stats([(0.8, 1, 1), (0.3, 0, 1)])
    assert s["n"] == 2 and s["executed"] == 1
    assert abs(s["brier"] - 0.065) < 1e-12, s
    assert abs(s["base_rate"] - 0.5) < 1e-12 and abs(s["reference_brier"] - 0.25) < 1e-12
    assert abs(s["brier_skill"] - 0.74) < 1e-12, s
    every_one_won = fb.brier_stats([(0.7, 1, 3)])  # base rate 1 -> reference 0 -> skill null
    assert every_one_won["reference_brier"] == 0.0 and every_one_won["brier_skill"] is None
    assert abs(every_one_won["brier"] - 0.09) < 1e-12
    empty = fb.brier_stats([])
    assert empty["n"] == 0 and empty["brier"] is None and empty["brier_skill"] is None
    print("  PASS test_brier_known_value_unit")


def test_brier_is_weighted_by_n_unit():
    """Mutation M13: equal weights cannot tell a weighted Brier from an unweighted mean over
    records. Distinct p values with unequal n can (unweighted values in the comments)."""
    s = fb.brier_stats([(0.8, 1, 3), (0.3, 0, 1)])
    assert abs(s["brier"] - 0.0525) < 1e-12, s          # unweighted: 0.065
    assert abs(s["base_rate"] - 0.75) < 1e-12, s        # unweighted: 0.5
    recs = [rec(p_exec=0.8, loi_outcome="WON", n=6), rec(p_exec=0.3, loi_outcome="LOST", n=2),
            rec(p_exec=0.6, loi_outcome="LOST", n=3), rec(p_exec=0.7, loi_outcome="WON")]
    cal = agg(recs)["pexec_calibration"]
    assert cal["resolved_n"] == 12 and cal["insufficient_sample"] is False, cal
    assert abs(cal["brier"] - 0.1325) < 1e-9, cal["brier"]                     # unweighted: 0.145
    assert (cal["base_rate"]["k"], cal["base_rate"]["n"]) == (7, 12), cal["base_rate"]  # 2/4
    assert abs(cal["reference_brier"] - 35.0 / 144.0) < 1e-6, cal["reference_brier"]
    assert abs(cal["brier_skill"] - 0.454857) < 1e-6, cal["brier_skill"]
    bin3 = cal["bins"][3]
    assert (bin3["n"], bin3["executed"]) == (4, 1), bin3                         # unweighted: 2, 1
    assert abs(bin3["mean_predicted"] - 0.625) < 1e-9, bin3                      # unweighted: 0.65
    print("  PASS test_brier_is_weighted_by_n_unit")


def test_pexec_calibration_weighted_pipeline_unit():
    recs = [rec(p_exec=0.8, loi_outcome="WON", n=5),
            rec(p_exec=0.3, loi_outcome="LOST", n=5),
            rec(p_exec=0.5, loi_outcome="PENDING", n=2),        # unresolved: counted, not scored
            rec(p_exec=0.4, n=1),                               # unresolved (no outcome)
            rec(loi_outcome="WON"),                             # resolved, no prediction
            rec(p_exec=0.9, loi_outcome="LOST", n=4, exclude=True)]
    res = agg(recs)
    cal = res["pexec_calibration"]
    assert cal["source"] == "--rows"
    assert (cal["with_p_exec"], cal["resolved_n"], cal["unresolved_n"],
            cal["resolved_without_p_exec"]) == (13, 10, 3, 1), cal
    assert cal["insufficient_sample"] is False
    assert abs(cal["brier"] - 0.065) < 1e-9, cal["brier"]
    assert cal["base_rate"]["k"] == 5 and abs(cal["base_rate"]["rate"] - 0.5) < 1e-9
    assert abs(cal["reference_brier"] - 0.25) < 1e-9 and abs(cal["brier_skill"] - 0.74) < 1e-9
    bins = cal["bins"]
    assert [b["n"] for b in bins] == [0, 5, 0, 0, 5], bins
    assert [b["executed"] for b in bins] == [0, 0, 0, 0, 5], bins
    assert abs(bins[1]["mean_predicted"] - 0.3) < 1e-9 and abs(bins[4]["mean_predicted"] - 0.8) < 1e-9
    assert bins[0]["mean_predicted"] is None and bins[0]["observed"]["status"] == "empty"
    assert bins[4]["observed"]["rate"] == 1.0 and bins[1]["observed"]["rate"] == 0.0
    md = fb.render_markdown(res)
    assert "INSUFFICIENT SAMPLE" not in md and "0.065" in md
    print("  PASS test_pexec_calibration_weighted_pipeline_unit")


def test_pexec_insufficient_sample_banner_keeps_counts_unit():
    res = agg([rec(p_exec=0.8, loi_outcome="WON"), rec(p_exec=0.3, loi_outcome="LOST"),
               rec(p_exec=0.6, loi_outcome="PENDING")])
    cal = res["pexec_calibration"]
    assert cal["resolved_n"] == 2 and cal["unresolved_n"] == 1 and cal["insufficient_sample"] is True
    assert cal["brier"] is None and cal["brier_skill"] is None and cal["base_rate"]["rate"] is None
    assert [b["n"] for b in cal["bins"]] == [0, 1, 0, 0, 1]
    assert [b["executed"] for b in cal["bins"]] == [0, 0, 0, 0, 1]
    md = fb.render_markdown(res)
    assert "INSUFFICIENT SAMPLE (resolved n=2 < 10)" in md, md
    assert "0.065" not in md
    print("  PASS test_pexec_insufficient_sample_banner_keeps_counts_unit")


def test_reliability_bin_edges_unit():
    got = [fb.bin_index(p) for p in (0.0, 0.1999, 0.2, 0.4, 0.6, 0.7999, 0.8, 1.0)]
    assert got == [0, 0, 1, 2, 3, 3, 4, 4], got
    # 60 typed as a percent -> 0.6; must not float-round down into [0.4,0.6)
    assert fb.bin_index(rec(p_exec=60)["p_exec"]) == 3
    assert fb.bin_index(rec(p_exec=80)["p_exec"]) == 4
    print("  PASS test_reliability_bin_edges_unit")


def test_pexec_rows_replace_rows_for_calibration_e2e():
    rows = [{"created": "2026-11-02", "verdict": "T1 PURSUE", "go": GO_SUBMIT, "loi_outcome": "LOST",
             "p_exec": 0.9, "n": 3},
            {"created": "2026-11-03", "verdict": "T2 WATCH", "p_exec": 45}]
    pexec = ([{"created": "2026-11-0%d" % (i + 1), "verdict": "T1 PURSUE", "p_exec": 0.8,
               "loi_outcome": "WON"} for i in range(5)]
             + [{"created": "2026-11-0%d" % (i + 1), "verdict": "T2 WATCH", "p_exec": 30,
                 "loi_outcome": "LOST"} for i in range(5)]
             + [{"created": "2026-11-04", "verdict": "T1 PURSUE", "p_exec": 0.5, "loi_outcome": "PENDING"},
                {"created": "2026-11-04", "verdict": "T1 PURSUE", "p_exec": 0.9, "loi_outcome": "LOST",
                 "exclude": "__YES__"}])
    with tempfile.TemporaryDirectory(prefix="fbt-") as tmp:
        rows_path = write_json(tmp, "rows.json", rows)
        pexec_path = write_json(tmp, "pexec.json", {"results": pexec})
        rc, out, err = run_main(["--rows", rows_path, "--today", "2026-12-15", "--json"])
        assert rc == 0, err
        from_rows = json.loads(out)
        cal = from_rows["pexec_calibration"]
        assert cal["source"] == "--rows" and (cal["with_p_exec"], cal["resolved_n"]) == (4, 3), cal
        assert from_rows["data_quality"]["p_exec_percent_normalized"] == 1
        rc, out, err = run_main(["--rows", rows_path, "--pexec-rows", pexec_path, "--today",
                                 "2026-12-15", "--json"])
        assert rc == 0, err
        with_p = json.loads(out)
        cal2 = with_p["pexec_calibration"]
        assert cal2["source"] == "--pexec-rows" and cal2["source_records"] == 12, cal2
        assert (cal2["with_p_exec"], cal2["resolved_n"], cal2["unresolved_n"]) == (11, 10, 1), cal2
        assert abs(cal2["brier"] - 0.065) < 1e-9 and cal2["insufficient_sample"] is False
        dq, dq_rows = with_p["data_quality"], from_rows["data_quality"]
        assert (dq["p_exec_percent_normalized"], dq["p_exec_source"]) == (5, "--pexec-rows"), dq
        # never added to any other count
        for key in ("tier_vs_decision", "funnel", "source_yield", "loss_class_mix", "stalled_t1",
                    "totals"):
            assert from_rows[key] == with_p[key], key
        for key in set(dq) - {"p_exec_percent_normalized", "p_exec_source"}:
            assert dq[key] == dq_rows[key], key
        rc, md, err = run_main(["--rows", rows_path, "--pexec-rows", pexec_path, "--today", "2026-12-15"])
        assert rc == 0 and "--pexec-rows" in section(md, "### 4. P(exec) calibration")
    print("  PASS test_pexec_rows_replace_rows_for_calibration_e2e")


# --- rate discipline ---------------------------------------------------------------------

def test_rate_discipline_min_n_and_zero_denominator_unit():
    small = fb.rate(2, 4, 5)
    assert small["rate"] is None and small["status"] == "n<min"
    assert fb.format_rate(small) == "2/4 (n<5)"
    zero = fb.rate(0, 0, 5)
    assert zero["rate"] is None and zero["status"] == "empty" and fb.format_rate(zero) == "-"
    ok = fb.rate(3, 5, 5)
    assert ok["rate"] == 0.6 and ok["status"] == "ok" and fb.format_rate(ok) == "3/5 = 60.0%"
    assert fb.format_rate(fb.rate(0, 8, 5, ci=True)) == "0/8 = 0.0% [0.0-32.4%]"
    recs = [rec(verdict="T1 PURSUE", go=GO_SUBMIT), rec(verdict="T1 PURSUE", status="Passed", n=3)]
    md = fb.render_markdown(agg(recs))
    assert table_row(md, "v2.9", "T1 PURSUE").rstrip().endswith("| 1/4 (n<5) | 1/4 (n<5) |")
    t2 = table_row(md, "v2.9", "T2 WATCH")
    assert t2.rstrip().endswith("| - | - |") and "%" not in t2, t2
    md1 = fb.render_markdown(agg(recs, min_n=1))
    assert "1/4 = 25.0% [" in table_row(md1, "v2.9", "T1 PURSUE")
    print("  PASS test_rate_discipline_min_n_and_zero_denominator_unit")


# --- metrics -----------------------------------------------------------------------------

def test_funnel_conversion_unit():
    recs = [rec(status="Dead", n=2), rec(status="Dead", scorecard=True),   # withdrawn: 3
            rec(scorecard=True, go=GO_SUBMIT, loi_outcome="WON"),          # go, LOI, won
            rec(scorecard=True, loi_sent="2026-11-05"),                     # go, LOI
            rec(scorecard=True, go=GO_SUBMIT),                              # go
            rec(scorecard=True, status="Passed", n=2),                      # rejected
            rec(scorecard=True),                                            # open
            rec(go=GO_SUBMIT),                                              # go without a scorecard
            rec(n=3)]                                                       # open
    res = agg(recs, min_n=1)
    f = res["funnel"]["v2.9"]
    assert (f["logged"], f["withdrawn"], f["eligible"], f["scorecard"]) == (13, 3, 10, 6), f
    assert (f["go"], f["go_with_scorecard"], f["go_without_scorecard"], f["loi"], f["won"]) == \
        (4, 3, 1, 2, 1), f
    kn = {name: (r["k"], r["n"]) for name, r in f["rates"].items()}
    assert kn == {"scorecard_of_eligible": (6, 10), "go_of_scorecard": (3, 6), "loi_of_go": (2, 4),
                  "won_of_loi": (1, 2)}, kn
    assert res["funnel"]["baseline"]["logged"] == 0
    md = fb.render_markdown(agg(recs))
    assert "6/10 = 60.0%" in md and "3/6 = 50.0%" in md and "2/4 (n<5)" in md
    print("  PASS test_funnel_conversion_unit")


def test_source_yield_unit():
    recs = [rec(source="Crexi", verdict="T1 PURSUE", go=GO_SUBMIT, loi_outcome="WON", n=2),
            rec(source="Crexi", verdict="T2 WATCH", status="Passed"),
            rec(source=BROKER, verdict="T1 PURSUE"),
            rec(source="Other", n=2),
            rec(source=None, verdict="T1 PURSUE", status="Dead"),
            rec(n=2)]
    sy = agg(recs)["source_yield"]
    assert list(sy["by_source"]) == ["Crexi", BROKER, "Off-Market", "LoopNet", "CoStar", "Other",
                                     "(blank)"]
    assert sy["by_source"]["Crexi"] == {"logged": 3, "t1": 2, "decided": 3, "go": 2, "loi": 2,
                                        "won": 2}, sy["by_source"]["Crexi"]
    blank = sy["by_source"]["(blank)"]
    assert (blank["logged"], blank["t1"], blank["decided"]) == (3, 1, 0), blank
    assert sy["by_source"]["LoopNet"]["logged"] == 0
    share = sy["other_or_blank"]
    assert (share["k"], share["n"]) == (5, 9) and abs(share["rate"] - 5.0 / 9.0) < 1e-6, share
    md = fb.render_markdown(agg(recs))
    assert table_row(md, BROKER).startswith("| %s | 1 | 1 |" % BROKER)
    assert "5/9 = 55.6%" in md
    print("  PASS test_source_yield_unit")


def test_loss_class_mix_unit():
    recs = [rec(loss_class="BASIS-DISCIPLINE", n=3), rec(loss_class="EXECUTION"),
            rec(loss_class=None, n=5), rec(loss_class="EXECUTION", exclude=True, n=7)]
    mix = agg(recs)["loss_class_mix"]
    assert list(mix) == list(LOSS_CLASSES)
    assert mix["BASIS-DISCIPLINE"] == 3 and mix["EXECUTION"] == 1 and mix["UNCLASSIFIED"] == 0
    assert sum(mix.values()) == 4
    print("  PASS test_loss_class_mix_unit")


def test_data_quality_counts_unit():
    recs = [rec(exclude=True, n=2, verdict="T1 PURSUE", cert="PROVISIONAL", p_exec=70),
            rec(verdict="T1 PURSUE", cert="PROVISIONAL", n=3),
            rec(verdict="T1 PURSUE", cert="CERTIFIED", status="Dead"),
            rec(verdict="T2 WATCH", cert="PROVISIONAL"),
            rec(n=4, status="Dead", go=GO_MAYBE),
            rec(verdict="PASS", p_exec=55)]
    dq = agg(recs)["data_quality"]
    assert dq == {"records": 6, "rows": 12, "excluded_rows": 2,
                  "p_exec_percent_normalized": 1, "p_exec_source": "--rows",
                  "t1_provisional": 3, "t1_provisional_source": "--rows",
                  "no_verdict": 4, "dead_without_decision": 5, "dead_without_decision_t1": 1,
                  "tier_from_current_verdict": 10,
                  "tier_basis": {"label": BASIS_CURRENT, "first_sighting_rows": 0,
                                 "logged_rows": 10},
                  "row_count_reconciliation": {"status": "not-run", "covered_rows": 12,
                                               "expected_rows": None}}, dq
    print("  PASS test_data_quality_counts_unit")


def test_t1_provisional_from_t1_rows_when_they_carry_cert_unit():
    rows = [rec(verdict="T1 PURSUE", cert="PROVISIONAL", n=4), rec(verdict="T1 PURSUE", n=3)]
    with_cert = [rec(verdict="T1 PURSUE", cert="PROVISIONAL"), rec(verdict="T1 PURSUE", cert=None),
                 rec(verdict="T1 PURSUE", cert="CERTIFIED"),
                 rec(verdict="T1 PURSUE", cert="PROVISIONAL", exclude=True)]
    dq = agg(rows, t1_rows=with_cert)["data_quality"]
    assert (dq["t1_provisional"], dq["t1_provisional_source"]) == (1, "--t1-rows"), dq
    no_cert = [fb.normalize_record({"created": "2026-11-02", "verdict": "T1 PURSUE"}, 0, "t1")]
    dq2 = agg(rows, t1_rows=no_cert)["data_quality"]
    assert (dq2["t1_provisional"], dq2["t1_provisional_source"]) == (4, "--rows"), dq2
    dq3 = agg(rows, t1_rows=with_cert + no_cert)["data_quality"]  # not every record carries cert
    assert (dq3["t1_provisional"], dq3["t1_provisional_source"]) == (4, "--rows"), dq3
    dq4 = agg(rows)["data_quality"]
    assert (dq4["t1_provisional"], dq4["t1_provisional_source"]) == (4, "--rows"), dq4
    print("  PASS test_t1_provisional_from_t1_rows_when_they_carry_cert_unit")


def test_t1_provisional_uses_first_sighting_tier_unit():
    """Mutation M20: the T1 PROVISIONAL count must use the tier (verdict_first when carried),
    not the current Verdict. Query B selects rows whose FIRST verdict was T1 even after a
    review overwrote Verdict."""
    rows = [rec(verdict="T1 PURSUE", n=2)]
    t1 = [rec(verdict="PASS", verdict_first="T1 PURSUE", cert="PROVISIONAL"),
          rec(verdict="T1 PURSUE", cert="CERTIFIED")]
    dq = agg(rows, t1_rows=t1)["data_quality"]
    assert (dq["t1_provisional"], dq["t1_provisional_source"]) == (1, "--t1-rows"), dq
    # the converse: current Verdict T1 but first sighted as T2 is not a T1 row
    converse = [rec(verdict="T1 PURSUE", verdict_first="T2 WATCH", cert="PROVISIONAL")]
    assert agg(rows, t1_rows=converse)["data_quality"]["t1_provisional"] == 0
    # the --rows path follows the same tier rule
    dq_rows = agg([rec(verdict="PASS", verdict_first="T1 PURSUE", cert="PROVISIONAL", n=3)])["data_quality"]
    assert (dq_rows["t1_provisional"], dq_rows["t1_provisional_source"]) == (3, "--rows"), dq_rows
    print("  PASS test_t1_provisional_uses_first_sighting_tier_unit")


# --- stalled T1 --------------------------------------------------------------------------

def test_stalled_t1_exact_from_t1_rows_approximate_from_rows_unit():
    """Query A buckets created to the era boundary, so every v2.9 row reads 2026-10-30 in the
    grouped export. The stalled count must come from --t1-rows' exact per-row dates when
    supplied; computed from --rows it is labelled approximate."""
    bucketed = [rec(created="2026-10-30", verdict="T1 PURSUE", n=5)]   # all open, era-bucketed
    exact = [rec(created="2026-11-03", verdict="T1 PURSUE", name="Fixture Old 1"),
             rec(created="2026-11-20", verdict="T1 PURSUE", name="Fixture Old 2"),
             rec(created="2026-12-05", verdict="T1 PURSUE", name="Fixture New 1"),
             rec(created="2026-12-08", verdict="T1 PURSUE", name="Fixture New 2"),
             rec(created="2026-12-10", verdict="T1 PURSUE", name="Fixture New 3")]
    approx = agg(bucketed)
    st = approx["stalled_t1"]
    assert (st["count"], st["approximate"], st["count_source"]) == (5, True, "--rows"), st
    md = section(fb.render_markdown(approx), "### 6. Stalled T1")
    assert APPROXIMATE in md and "names not supplied" in md, md
    exact_res = agg(bucketed, t1_rows=exact)
    st2 = exact_res["stalled_t1"]
    assert (st2["count"], st2["approximate"], st2["count_source"]) == (2, False, "--t1-rows"), st2
    assert [x["name"] for x in st2["list"]] == ["Fixture Old 1", "Fixture Old 2"]
    md2 = section(fb.render_markdown(exact_res), "### 6. Stalled T1")
    assert "approximate" not in md2 and "Fixture Old 1" in md2 and "Fixture New 1" not in md2, md2
    assert exact_res["tier_vs_decision"] == approx["tier_vs_decision"]  # never added elsewhere
    print("  PASS test_stalled_t1_exact_from_t1_rows_approximate_from_rows_unit")


def test_stalled_t1_count_and_list_unit():
    rows = [rec(created="2026-11-30", verdict="T1 PURSUE", n=2),           # 15 days old: stalled
            rec(created="2026-11-10", verdict="T1 PURSUE"),                # stalled
            rec(created="2026-12-01", verdict="T1 PURSUE", n=4),           # exactly 14: not stalled
            rec(created="2026-11-01", verdict="T1 PURSUE", status="Passed"),
            rec(created="2026-11-01", verdict="T1 PURSUE", status="Dead"),
            rec(created="2026-11-01", verdict="T2 WATCH"),
            rec(created="2026-11-01", verdict="T1 PURSUE", exclude=True)]
    res = agg(rows)
    st = res["stalled_t1"]
    assert st["count"] == 3 and st["names_supplied"] is False and st["list"] == [], st
    assert "names not supplied" in fb.render_markdown(res)
    t1 = [rec(created="2026-11-30", verdict="T1 PURSUE", name="Fixture Flex C", url="https://example.test/c"),
          rec(created="2026-11-30", verdict="T1 PURSUE", name="Fixture Flex B", url="https://example.test/b"),
          rec(created="2026-11-10", verdict="T1 PURSUE", name="Fixture Flex A", url="https://example.test/a"),
          rec(created="2026-12-01", verdict="T1 PURSUE", name="Fixture Too New"),
          rec(created="2026-11-01", verdict="T1 PURSUE", status="Passed", name="Fixture Decided")]
    st2 = agg(rows, t1_rows=t1)["stalled_t1"]
    assert st2["count"] == 3 and st2["names_supplied"] is True and st2["t1_records"] == 5, st2
    assert [x["name"] for x in st2["list"]] == ["Fixture Flex A", "Fixture Flex B", "Fixture Flex C"]
    assert st2["list"][0] == {"created": "2026-11-10", "name": "Fixture Flex A",
                              "url": "https://example.test/a"}, st2["list"][0]
    md = fb.render_markdown(agg(rows, t1_rows=t1))
    assert "Fixture Flex A" in md and "Fixture Too New" not in md and "names not supplied" not in md
    print("  PASS test_stalled_t1_count_and_list_unit")


def test_retiered_t1_without_decision_is_open_and_stalls_unit():
    """C1 design note: a row first sighted as T1 and re-tiered later, with no Go / No-Go and a
    status other than Dead or Passed, is OPEN -- not a decided miss -- so T1 precision covers
    explicit decisions only; it surfaces in the stalled-T1 list once it ages."""
    r = rec(created="2026-11-01", verdict="PASS", verdict_first="T1 PURSUE", status="Reviewing",
            name="Fixture Retiered")
    assert fb.classify(r) == "open" and fb.tier_of(r) == "T1 PURSUE"
    res = agg([r], t1_rows=[r])
    t1 = res["tier_vs_decision"]["v2.9"]["T1 PURSUE"]
    assert (t1["logged"], t1["open"], t1["decided"]) == (1, 1, 0), t1
    assert t1["held"]["status"] == "empty" and res["tier_vs_decision"]["v2.9"]["PASS"]["logged"] == 0
    st = res["stalled_t1"]
    assert st["count"] == 1 and st["list"][0]["name"] == "Fixture Retiered", st
    note = "T1 precision covers explicit decisions only"
    assert note in fb.__doc__ and note in section(fb.render_markdown(res), "### Definitions")
    print("  PASS test_retiered_t1_without_decision_is_open_and_stalls_unit")


def test_stalled_t1_flags_and_list_cap_e2e():
    with tempfile.TemporaryDirectory(prefix="fbt-") as tmp:
        rows = write_json(tmp, "rows.json", [{"created": "2026-11-10", "verdict": "T1 PURSUE"},
                                             {"created": "2026-11-30", "verdict": "T1 PURSUE", "n": 2}])
        t1 = write_json(tmp, "t1.json", [
            {"created": "2026-11-10", "verdict": "T1 PURSUE", "name": "Fixture Flex A",
             "url": "https://example.test/a"},
            {"created": "2026-11-30", "verdict": "T1 PURSUE", "name": "Fixture Flex B"},
            {"created": "2026-11-30", "verdict": "T1 PURSUE", "name": "Fixture Flex C"}])
        rc, out, err = run_main(["--rows", rows, "--t1-rows", t1, "--today", "2026-12-15",
                                 "--stall-days", "30", "--json"])
        assert rc == 0, err
        st = json.loads(out)["stalled_t1"]
        assert st["count"] == 1 and [x["name"] for x in st["list"]] == ["Fixture Flex A"], st
        rc, out, err = run_main(["--rows", rows, "--today", "2026-12-01", "--json"])
        assert rc == 0 and json.loads(out)["stalled_t1"]["count"] == 1
        rc, out, err = run_main(["--rows", rows, "--today", "2026-12-15", "--json"])
        assert rc == 0 and json.loads(out)["stalled_t1"]["count"] == 3
        # the named list is capped at 10, oldest first; the count is every stalled --t1-rows row
        many = [{"created": "2026-11-%02d" % d, "verdict": "T1 PURSUE", "name": "Fixture %02d" % d}
                for d in range(12, 0, -1)]
        rc, out, err = run_main(["--rows", rows, "--t1-rows", write_json(tmp, "t12.json", many),
                                 "--today", "2026-12-15"])
        assert rc == 0, err
        assert "Fixture 01" in out and "Fixture 10" in out and "Fixture 11" not in out
        assert out.index("Fixture 01") < out.index("Fixture 10")
        assert "showing 10 of 12" in out, out
    print("  PASS test_stalled_t1_flags_and_list_cap_e2e")


def test_t1_rows_never_change_other_counts_e2e():
    rows = [{"created": "2026-10-20", "verdict": "T1 PURSUE", "status": "Passed", "n": 3},
            {"created": "2026-11-01", "verdict": "T1 PURSUE", "n": 2},
            {"created": "2026-11-03", "verdict": "T2 WATCH", "source": "Crexi", "p_exec": 0.4,
             "loi_outcome": "LOST", "go": GO_SUBMIT}]
    t1 = [{"created": "2026-11-01", "verdict": "T1 PURSUE", "name": "Fixture Flex A"},
          {"created": "2026-11-01", "verdict": "T1 PURSUE", "name": "Fixture Flex B"},
          # rows that would move every metric if they were ever counted
          {"created": "2026-11-02", "verdict": "T1 PURSUE", "go": GO_SUBMIT, "loi_outcome": "WON",
           "p_exec": 0.9, "source": "Crexi", "scorecard": True, "loss_class": "EXECUTION",
           "status": "Dead", "name": "Fixture Won"},
          {"created": "2026-10-01", "verdict": "T1 PURSUE", "status": "Passed", "name": "Fixture Passed"}]
    with tempfile.TemporaryDirectory(prefix="fbt-") as tmp:
        rows_path, t1_path = write_json(tmp, "rows.json", rows), write_json(tmp, "t1.json", t1)
        common = ["--rows", rows_path, "--today", "2026-12-15", "--json"]
        rc, out, err = run_main(common)
        assert rc == 0, err
        without = json.loads(out)
        rc, out, err = run_main(common + ["--t1-rows", t1_path])
        assert rc == 0, err
        with_t1 = json.loads(out)
    for key in sorted(JSON_KEYS - {"stalled_t1", "params"}):
        assert without[key] == with_t1[key], key
    assert without["stalled_t1"]["count"] == with_t1["stalled_t1"]["count"] == 2
    assert [x["name"] for x in with_t1["stalled_t1"]["list"]] == ["Fixture Flex A", "Fixture Flex B"]
    print("  PASS test_t1_rows_never_change_other_counts_e2e")


# --- file handling -----------------------------------------------------------------------

def test_results_wrapped_and_bom_export_e2e():
    with tempfile.TemporaryDirectory(prefix="fbt-") as tmp:
        wrapped = write_json(tmp, "wrapped.json",
                             {"results": [{"created": "2026-11-02", "source": BROKER, "go": GO_SUBMIT,
                                           "verdict": "T1 PURSUE", "extra_col": "ignored"}],
                              "has_more": False},
                             encoding="utf-8-sig", ensure_ascii=False)
        with open(wrapped, "rb") as fh:
            raw = fh.read()
        assert raw.startswith(b"\xef\xbb\xbf") and b"\xe2\x80\x94" in raw  # BOM + literal em dash
        plain = write_json(tmp, "plain.json", [{"created": "2026-11-03", "verdict": "T2 WATCH", "n": 2}])
        rc, out, err = run_main(["--rows", wrapped, "--rows", plain, "--today", "2026-12-15", "--json"])
        assert rc == 0, err
        res = json.loads(out)
        assert res["totals"]["records"] == 2 and res["totals"]["rows"] == 3
        assert res["source_yield"]["by_source"][BROKER]["logged"] == 1
        assert res["tier_vs_decision"]["v2.9"]["T1 PURSUE"]["go"] == 1
        assert res["tier_vs_decision"]["v2.9"]["T2 WATCH"]["open"] == 2
    print("  PASS test_results_wrapped_and_bom_export_e2e")


def test_truncated_export_is_refused_on_every_flag_e2e():
    """Notion SQL mode returns one page of about 100 rows and cannot paginate. A truncated
    export must never produce a calibration report, whichever flag carries it."""
    with tempfile.TemporaryDirectory(prefix="fbt-") as tmp:
        record = {"created": "2026-11-02", "verdict": "T1 PURSUE"}
        # complete exports: has_more absent, null or false
        for i, wrapper in enumerate(({"results": [record]}, {"results": [record], "has_more": None},
                                     {"results": [record], "has_more": False})):
            good = write_json(tmp, "good-%d.json" % i, wrapper)
            rc, out, err = run_main(["--rows", good, "--today", "2026-12-15"])
            assert rc == 0, (wrapper, err)
        # anything else is refused: true, and every non-false spelling of it
        for value in (True, "true", 1, 0, "false", "yes", [], {}):
            trunc = write_json(tmp, "trunc.json", {"results": [record], "has_more": value})
            for flag in ("--rows", "--t1-rows", "--pexec-rows", "--expect-rows"):
                rc, out, err = run_main(["--rows", good, flag, trunc, "--today", "2026-12-15"])
                assert rc == 2, (value, flag, rc, err)
                assert err == "[FATAL] %s: %s\n" % (trunc, TRUNCATED), (value, flag, err)
                assert out == "", (value, flag, out)
    print("  PASS test_truncated_export_is_refused_on_every_flag_e2e")


def test_row_count_reconciliation_e2e():
    """--expect-rows (QUERY_N): the weighted rows of every --rows file, excluded rows
    included, must equal the log's row count, or the run refuses to report."""
    rows = [{"created": "2026-11-02", "verdict": "T1 PURSUE", "n": 3},
            {"created": "2026-11-02", "verdict": "T2 WATCH", "exclude": "__YES__", "n": 2}]
    with tempfile.TemporaryDirectory(prefix="fbt-") as tmp:
        base = ["--rows", write_json(tmp, "rows.json", {"results": rows}), "--today", "2026-12-15"]
        rc, md, err = run_main(base)
        assert rc == 0, err
        assert "row-count reconciliation: NOT RUN (no --expect-rows)" in section(md, "### 7. Data quality")
        ok = write_json(tmp, "n-ok.json", {"results": [{"n": 5}], "has_more": False})
        rc, md, err = run_main(base + ["--expect-rows", ok])
        assert rc == 0, err
        dq_section = section(md, "### 7. Data quality")
        assert "row-count reconciliation: OK" in dq_section and "NOT RUN" not in dq_section, dq_section
        rc, out, err = run_main(base + ["--expect-rows", ok, "--json"])
        assert rc == 0, err
        assert json.loads(out)["data_quality"]["row_count_reconciliation"] == {
            "status": "ok", "covered_rows": 5, "expected_rows": 5}
        short = write_json(tmp, "n-short.json", {"results": [{"n": 7}]})
        rc, out, err = run_main(base + ["--expect-rows", short])
        assert rc == 2 and out == "", err
        assert err == ("[FATAL] %s: partitions cover 5 rows but the log holds 7; a Verdict value is "
                       "outside QUERY_A_PARTITIONS (new option or blank string)\n" % short), err
        over = write_json(tmp, "n-over.json", [{"n": 4}])
        rc, out, err = run_main(base + ["--expect-rows", over])
        assert rc == 2 and err.startswith("[FATAL] %s: partitions cover 5 rows but the log holds 4; "
                                          % over), err
        for i, payload in enumerate(([], [{"n": 5}, {"n": 5}], [{"count": 5}], [{"n": "5"}],
                                     [{"n": -1}], [{"n": True}], [7], {"results": [{"n": 5.0}]})):
            bad = write_json(tmp, "n-bad-%d.json" % i, payload)
            rc, out, err = run_main(base + ["--expect-rows", bad])
            assert rc == 2 and err.startswith("[FATAL] %s: expected exactly one record" % bad), (payload, err)
            assert "Traceback" not in err and out == "", (payload, err)
    print("  PASS test_row_count_reconciliation_e2e")


def test_unreadable_or_malformed_input_returns_2_e2e():
    with tempfile.TemporaryDirectory(prefix="fbt-") as tmp:
        good = write_json(tmp, "good.json", [{"created": "2026-11-02"}])
        bad_json = os.path.join(tmp, "bad.json")
        with open(bad_json, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        cases = [
            (["--rows", os.path.join(tmp, "missing.json")], "cannot read"),
            (["--rows", tmp], "cannot read"),
            (["--rows", bad_json], "is not valid JSON"),
            (["--rows", write_json(tmp, "shape.json", {"rows": []})], '"results" array'),
            (["--rows", write_json(tmp, "badres.json", {"results": "x"})], '"results" array'),
            (["--rows", write_json(tmp, "scalar.json", 42)], '"results" array'),
            (["--rows", write_json(tmp, "nonobj.json", [{"created": "2026-11-02"}, 7])], "row 1 ("),
            (["--rows", good, "--rows", good], "more than once"),
            (["--rows", good, "--today", "12/15/2026"], "--today"),
            (["--rows", good, "--stall-days", "-1"], "--stall-days"),
            (["--rows", good, "--min-n", "0"], "--min-n"),
            (["--rows", good, "--t1-rows", write_json(tmp, "t1bad.json",
                                                      [{"created": "2026-11-02", "verdict": "T1"}])],
             "verdict='T1' is not a known option"),
            (["--rows", good, "--pexec-rows", write_json(tmp, "pbad.json",
                                                         [{"created": "2026-11-02", "p_exec": 101}])],
             "p_exec=101 is out of range"),
        ]
        for argv, needle in cases:
            rc, out, err = run_main(argv)
            assert rc == 2, (argv, rc, err)
            assert err.startswith("[FATAL] ") and needle in err, (argv, err)
            assert "Traceback" not in err and "[BACKTEST]" not in err and out == "", (argv, err)
    print("  PASS test_unreadable_or_malformed_input_returns_2_e2e")


# --- export contract: the four Notion SQL queries -----------------------------------------

NOTION_TABLE = '"collection://9a6ae219-85a3-4621-899c-c757fd062f8b"'
NOTION_COLUMNS = ("url", "Deal Name / Address", "Date Added", "Source", "Verdict", "Status",
                  "Go / No-Go", "Scorecard Done", "date:LOI Sent Date:start", "LOI Outcome",
                  "Loss Class", "Exclude from Calibration", "Data Certification", "P(exec) %",
                  "Verdict at First Sighting", "Score at First Sighting")
YES, NO = "__YES__", "__NO__"
# QUERY_A's partition predicate before and after the blank-string fix (C4)
OLD_PREDICATE = 'coalesce("Verdict",' + "'(none)') = ?"
NEW_PREDICATE = 'coalesce(nullif("Verdict",' + "''),'(none)') = ?"


def _notion_fixture():
    """Synthetic Deal Sourcing Log rows in Notion column order: every partition, both eras
    (incl. the last pre-boundary and first boundary day, and a -04:00 timestamp whose UTC date
    is the boundary but whose literal date part is not), every class, duplicate groups, and a
    blank-string Verdict, which must land in the (none) partition."""
    rows = [
        # Date Added, Source, Verdict, Status, Go / No-Go, Scorecard, LOI Sent, LOI Outcome,
        # Loss Class, Exclude, Data Certification, P(exec) %
        ("2026-09-14T13:05:00.000Z", "Crexi", "T1 PURSUE", "Passed", None, NO, None, None,
         "BASIS-DISCIPLINE", NO, "CERTIFIED", None),
        ("2026-09-20T09:00:00.000Z", "Crexi", "T1 PURSUE", "Passed", None, NO, None, None,
         "BASIS-DISCIPLINE", NO, "PROVISIONAL", None),
        ("2026-10-12", BROKER, "T1 PURSUE", "Dead", None, YES, None, None, None, NO, "PROVISIONAL", None),
        ("2026-10-27T16:30:00.000Z", "Off-Market", "T1 PURSUE", "LOI Submitted", GO_SUBMIT, YES,
         "2026-10-29", "PENDING", None, NO, "PROVISIONAL", 0.55),
        ("2026-10-29T23:59:00.000Z", "Crexi", "T1 PURSUE", "Reviewing", GO_REVIEW, NO, None, None,
         None, NO, None, None),
        ("2026-10-30T00:01:00.000Z", "Crexi", "T1 PURSUE", "Reviewing", GO_REVIEW, NO, None, None,
         None, NO, None, None),
        ("2026-11-03T12:00:00.000Z", "LoopNet", "T1 PURSUE", "Under PSA", GO_SUBMIT, YES, "2026-11-10",
         "WON", None, NO, "CERTIFIED", 0.7),
        ("2026-11-05", "LoopNet", "T1 PURSUE", "Passed", GO_PASS, YES, None, None, "PRICE-MARGINAL",
         NO, "PROVISIONAL", None),
        ("2026-11-20", "Crexi", "T1 PURSUE", "New Lead", None, NO, None, None, None, NO, None, None),
        ("2026-12-08", "Crexi", "T1 PURSUE", "New Lead", None, NO, None, None, None, NO, None, None),
        ("2026-08-02", "CoStar", "T2 WATCH", "Passed", GO_PASS, NO, None, None, "BASIS-ELECTIVE", NO,
         None, None),
        ("2026-08-09", "CoStar", "T2 WATCH", "Passed", GO_PASS, NO, None, None, "BASIS-ELECTIVE", NO,
         None, None),
        ("2026-11-11", "Other", "T2 WATCH", "Screened", GO_MAYBE, YES, None, None, None, NO, None, 30),
        ("2026-11-12", "Other", "T2 WATCH", "Screened", GO_MAYBE, YES, None, None, None, NO, None, None),
        ("2026-11-13", None, "T2 WATCH", "Passed", None, NO, None, "EXPIRED-UNSENT", None, NO, None, 0.4),
        ("2026-07-01", "Crexi", "PASS", "Passed", GO_PASS, NO, None, None, None, NO, None, None),
        ("2026-11-15", "Crexi", "PASS", "Dead", None, NO, None, None, None, NO, None, None),
        ("2026-11-16", "Crexi", "PASS", "LOI Submitted", GO_SUBMIT, YES, "2026-11-25", "LOST",
         "NON-COMPARABLE BUYER", NO, None, 0.35),
        ("2026-06-10", "Off-Market", "KILLED", "Dead", None, NO, None, None, None, NO, None, None),
        ("2026-11-18", "Off-Market", "KILLED", "Passed", GO_PASS, NO, None, None, None, YES, None, None),
        ("2026-10-01", None, None, "New Lead", None, NO, None, None, None, NO, None, None),
        ("2026-10-02", None, None, "New Lead", None, NO, None, None, None, NO, None, None),
        ("2026-11-21", "Crexi", None, "Reviewing", None, YES, None, None, None, NO, None, None),
        ("2026-11-22", BROKER, None, "Dead", GO_MAYBE, NO, None, None, None, NO, None, None),
        ("2026-10-29T23:30:00-04:00", "Crexi", "T2 WATCH", "Passed", GO_PASS, NO, None, None, None,
         NO, None, None),
        ("2026-11-25", "LoopNet", "", "New Lead", None, NO, None, None, None, NO, None, None),
    ]
    # first-sighting columns: blank (rows created before 2026-11-05) except one row whose
    # current Verdict was overwritten after review -- its T1 prediction must still count.
    first = {18: ("T1 PURSUE", 81)}
    return [("https://example.test/%d" % i, "Fixture Flex %02d" % i) + row + first.get(i, (None, None))
            for i, row in enumerate(rows, 1)]


def _sql_records(con, query, params=()):
    cur = con.execute(query, params)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


def _notion_db(rows):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE %s (%s)" % (NOTION_TABLE, ", ".join('"%s"' % c for c in NOTION_COLUMNS)))
    con.executemany("INSERT INTO %s VALUES (%s)" % (NOTION_TABLE, ", ".join("?" * len(NOTION_COLUMNS))),
                    rows)
    return con


def test_export_queries_are_module_constants_documented_verbatim_unit():
    assert fb.QUERY_A_PARTITIONS == ("T1 PURSUE", "T2 WATCH", "PASS", "KILLED", "(none)")
    for name in ("QUERY_A", "QUERY_B", "QUERY_P", "QUERY_N"):
        query = getattr(fb, name)
        assert query.isascii() and "\n" not in query and query.startswith("SELECT "), name
        assert query in fb.__doc__, "%s must appear verbatim in the module docstring" % name
    assert fb.QUERY_A.count("?") == 1
    assert fb.QUERY_B.count("?") == fb.QUERY_P.count("?") == fb.QUERY_N.count("?") == 0
    assert fb.QUERY_N == 'SELECT COUNT(*) AS n FROM ' + NOTION_TABLE
    # the CASE compares the literal date part, exactly as Query B / Query P / the engine read
    # created; it is the default --era boundary
    assert ('CASE WHEN substr("Date Added",1,10) >= ' + "'2026-10-30'") in fb.QUERY_A
    assert "date(" not in fb.QUERY_A and fb.DEFAULT_ERAS == (("v2.9", V29),)
    # a blank-string Verdict lands in (none) instead of falling between the partitions
    assert NEW_PREDICATE in fb.QUERY_A and OLD_PREDICATE not in fb.QUERY_A
    print("  PASS test_export_queries_are_module_constants_documented_verbatim_unit")


def test_query_a_partitions_through_sqlite_match_per_row_metrics_e2e():
    """QUERY_A run once per verdict partition (the Notion SQL page limit) must yield the same
    metrics as the same fixture rows fed per-row, and QUERY_N must reconcile the row count.
    QUERY_B and QUERY_P must produce records the engine accepts for --t1-rows and
    --pexec-rows."""
    fixture = _notion_fixture()
    con = _notion_db(fixture)
    try:
        partitions = [_sql_records(con, fb.QUERY_A, (value,)) for value in fb.QUERY_A_PARTITIONS]
        t1_rows = _sql_records(con, fb.QUERY_B)
        pexec_rows = _sql_records(con, fb.QUERY_P)
        expect = _sql_records(con, fb.QUERY_N)
    finally:
        con.close()
    assert expect == [{"n": len(fixture)}], expect
    grouped_records = [r for part in partitions for r in part]
    assert {r["created"] for r in grouped_records} == {"2026-01-01", "2026-10-30"}
    assert sum(r["n"] for r in grouped_records) == len(fixture)  # disjoint and exhaustive
    assert len(grouped_records) < len(fixture)                    # grouping collapsed rows
    assert all(len(part) < 100 for part in partitions)
    col = {name: i for i, name in enumerate(NOTION_COLUMNS)}
    per_row = [{"created": row[col["Date Added"]][:10], "source": row[col["Source"]],
                "verdict": row[col["Verdict"]], "status": row[col["Status"]],
                "go": row[col["Go / No-Go"]], "scorecard": row[col["Scorecard Done"]],
                "loi_sent": row[col["date:LOI Sent Date:start"]],
                "loi_outcome": row[col["LOI Outcome"]], "loss_class": row[col["Loss Class"]],
                "exclude": row[col["Exclude from Calibration"]],
                "verdict_first": row[col["Verdict at First Sighting"]]} for row in fixture]
    with tempfile.TemporaryDirectory(prefix="fbt-") as tmp:
        expect_path = write_json(tmp, "query-n.json", {"results": expect, "has_more": False})
        argv = ["--today", "2026-12-15", "--json", "--expect-rows", expect_path]
        for i, part in enumerate(partitions):
            argv += ["--rows", write_json(tmp, "query-a-%d.json" % i, {"results": part, "has_more": False},
                                          ensure_ascii=False)]
        rc, out, err = run_main(argv)
        assert rc == 0, err
        grouped = json.loads(out)
        assert grouped["data_quality"]["row_count_reconciliation"] == {
            "status": "ok", "covered_rows": len(fixture), "expected_rows": len(fixture)}
        rc, out, err = run_main(["--rows", write_json(tmp, "per-row.json", per_row), "--today",
                                 "2026-12-15", "--json", "--expect-rows", expect_path])
        assert rc == 0, err
        flat = json.loads(out)
        for key in ("tier_vs_decision", "funnel", "source_yield", "pexec_calibration", "loss_class_mix"):
            assert grouped[key] == flat[key], key
        for key in ("totals", "data_quality"):
            g, f = dict(grouped[key]), dict(flat[key])
            assert g.pop("records") < f.pop("records"), key
            assert g == f, (key, g, f)
        # bucketed dates make the --rows stalled count wrong; it is labelled, not trusted
        assert (grouped["stalled_t1"]["count"], grouped["stalled_t1"]["approximate"]) == (4, True)
        rc, out, err = run_main(argv + ["--t1-rows", write_json(tmp, "query-b.json", {"results": t1_rows}),
                                        "--pexec-rows", write_json(tmp, "query-p.json", {"results": pexec_rows})])
        assert rc == 0, err
        full = json.loads(out)
    st = full["stalled_t1"]
    assert (st["count"], st["count_source"]) == (3, "--t1-rows"), st
    assert [x["name"] for x in st["list"]] == ["Fixture Flex 05", "Fixture Flex 06", "Fixture Flex 09"], st
    cal = full["pexec_calibration"]
    assert (cal["source"], cal["with_p_exec"], cal["resolved_n"], cal["unresolved_n"]) == \
        ("--pexec-rows", 5, 3, 2), cal
    dq = full["data_quality"]
    assert (dq["t1_provisional"], dq["t1_provisional_source"], dq["p_exec_percent_normalized"]) == \
        (4, "--t1-rows", 1), dq
    assert grouped["data_quality"]["t1_provisional"] == 0  # Query A carries no cert
    for key in ("tier_vs_decision", "funnel", "source_yield", "loss_class_mix", "totals"):
        assert full[key] == grouped[key], key
    print("  PASS test_query_a_partitions_through_sqlite_match_per_row_metrics_e2e")


def test_verdict_outside_every_partition_is_caught_by_query_n_e2e():
    """A row whose Verdict matches no QUERY_A partition vanishes from every --rows file
    without a trace. A blank-string Verdict now lands in (none) via nullif; under the pre-fix
    predicate it vanished, and --expect-rows (QUERY_N) catches that, exactly as it catches a
    new Verdict option added to the Notion schema."""
    fixture = _notion_fixture()
    assert any(row[NOTION_COLUMNS.index("Verdict")] == "" for row in fixture)
    pre_fix_query = fb.QUERY_A.replace(NEW_PREDICATE, OLD_PREDICATE)
    assert pre_fix_query != fb.QUERY_A
    new_option = ("https://example.test/new", "Fixture Flex New", "2026-11-26", "Crexi", "T0 MOONSHOT",
                  "New Lead", None, NO, None, None, None, NO, None, None, None, None)
    con = _notion_db(fixture)
    try:
        fixed = [_sql_records(con, fb.QUERY_A, (v,)) for v in fb.QUERY_A_PARTITIONS]
        pre_fix = [_sql_records(con, pre_fix_query, (v,)) for v in fb.QUERY_A_PARTITIONS]
        expect = _sql_records(con, fb.QUERY_N)
        con.execute("INSERT INTO %s VALUES (%s)" % (NOTION_TABLE, ", ".join("?" * len(NOTION_COLUMNS))),
                    new_option)
        with_new = [_sql_records(con, fb.QUERY_A, (v,)) for v in fb.QUERY_A_PARTITIONS]
        expect_new = _sql_records(con, fb.QUERY_N)
    finally:
        con.close()
    n = len(fixture)
    assert any(r["verdict"] == "" for r in fixed[fb.QUERY_A_PARTITIONS.index("(none)")])
    assert sum(r["n"] for part in pre_fix for r in part) == n - 1  # the blank row fell through
    assert sum(r["n"] for part in with_new for r in part) == n     # so does the new option
    assert expect == [{"n": n}] and expect_new == [{"n": n + 1}]

    def run(tmp, tag, parts, expected):
        expect_path = write_json(tmp, "n-%s.json" % tag, {"results": expected})
        argv = ["--today", "2026-12-15", "--json", "--expect-rows", expect_path]
        for i, part in enumerate(parts):
            argv += ["--rows", write_json(tmp, "a-%s-%d.json" % (tag, i), {"results": part},
                                          ensure_ascii=False)]
        return run_main(argv) + (expect_path,)

    with tempfile.TemporaryDirectory(prefix="fbt-") as tmp:
        rc, out, err, _ = run(tmp, "fixed", fixed, expect)
        assert rc == 0, err
        res = json.loads(out)
        assert res["data_quality"]["row_count_reconciliation"]["status"] == "ok"
        assert res["tier_vs_decision"]["v2.9"]["(none)"]["logged"] == 3  # the blank row is counted
        for tag, parts, expected, covered, held in (("pre-fix", pre_fix, expect, n - 1, n),
                                                     ("new-option", with_new, expect_new, n, n + 1)):
            rc, out, err, expect_path = run(tmp, tag, parts, expected)
            assert rc == 2 and out == "", (tag, rc, err)
            assert err == ("[FATAL] %s: partitions cover %d rows but the log holds %d; a Verdict value "
                           "is outside QUERY_A_PARTITIONS (new option or blank string)\n"
                           % (expect_path, covered, held)), (tag, err)
    print("  PASS test_verdict_outside_every_partition_is_caught_by_query_n_e2e")


# --- the 2026-10-30 replay -----------------------------------------------------------------

def test_replay_2026_10_30_hand_backtest_zero_of_eight_e2e():
    """The 2026-10-30 hand back-test found 0 of 8 decided rows held T1. Replayed through the
    engine it must read 0/8 with its Wilson interval shown (n=8 clears min-n 5)."""
    rows = [  # 8 decided T1 rows, all rejected, all before the v2.9 boundary, mixed grouping
        {"created": "2026-10-02", "verdict": "T1 PURSUE", "status": "Passed", "n": 3},
        {"created": "2026-10-09T14:00:00.000Z", "verdict": "T1 PURSUE", "go": GO_PASS, "n": 2},
        {"created": "2026-10-16", "verdict": "T1 PURSUE", "go": GO_PASS, "status": "Passed"},
        {"created": "2026-10-23", "verdict": "T1 PURSUE", "status": "Passed", "scorecard": "__YES__", "n": 2},
        # not decided: must stay out of the strict denominator
        {"created": "2026-10-20", "verdict": "T1 PURSUE", "status": "Dead"},
        {"created": "2026-10-27", "verdict": "T1 PURSUE", "status": "Reviewing", "n": 2}]
    with tempfile.TemporaryDirectory(prefix="fbt-") as tmp:
        path = write_json(tmp, "replay.json", {"results": rows})
        rc, out, err = run_main(["--rows", path, "--today", "2026-11-05", "--json"])
        assert rc == 0, err
        held = json.loads(out)["tier_vs_decision"]["baseline"]["T1 PURSUE"]["held"]
        assert (held["k"], held["n"], held["rate"], held["ci_low"]) == (0, 8, 0.0, 0.0), held
        assert round(held["ci_high"], 4) == 0.3244, held
        rc, md, err = run_main(["--rows", path, "--today", "2026-11-05"])
        assert rc == 0, err
        row = table_row(md, "baseline", "T1 PURSUE")
        assert row.startswith("| baseline | T1 PURSUE | 11 | 8 | 0 | 8 | 1 | 2 |"), row
        assert "| 0/8 = 0.0% [0.0-32.4%] | 0/9 = 0.0% [0.0-29.9%] |" in row, row
        assert "baseline=0/8" in err and "v2.9=0/0" in err, err
    print("  PASS test_replay_2026_10_30_hand_backtest_zero_of_eight_e2e")


# --- report surface ----------------------------------------------------------------------

def test_markdown_has_title_and_every_section_header_unit():
    md = fb.render_markdown(agg([rec(verdict="T1 PURSUE", status="Passed", source="Crexi"),
                                 rec(created="2026-10-01", verdict="T2 WATCH")]))
    lines = md.splitlines()
    assert lines[0] == TITLE, lines[0]
    positions = []
    for header in SECTION_HEADERS:
        hits = [i for i, line in enumerate(lines) if line.startswith(header)]
        assert len(hits) == 1, (header, hits)
        positions.append(hits[0])
    assert positions == sorted(positions), positions
    print("  PASS test_markdown_has_title_and_every_section_header_unit")


def test_json_has_stable_top_level_keys_e2e():
    with tempfile.TemporaryDirectory(prefix="fbt-") as tmp:
        for payload in ([{"created": "2026-11-02", "verdict": "T1 PURSUE", "source": BROKER, "go": GO_SUBMIT}],
                        []):
            path = write_json(tmp, "rows.json", payload)
            rc, out, err = run_main(["--rows", path, "--today", "2026-12-15", "--json"])
            assert rc == 0, err
            res = json.loads(out)
            assert set(res) == JSON_KEYS, sorted(res)
            assert res["schema"] == "funnel-backtest/1" and res["report_only"] is True
            assert res["today"] == "2026-12-15"
            assert out.isascii(), "JSON is ASCII-escaped so any console code page can carry it"
    print("  PASS test_json_has_stable_top_level_keys_e2e")


def test_out_md_writes_utf8_and_prints_nothing_e2e():
    with tempfile.TemporaryDirectory(prefix="fbt-") as tmp:
        path = write_json(tmp, "rows.json", [{"created": "2026-11-02", "source": BROKER}])
        md_path = os.path.join(tmp, "report.md")
        rc, out, err = run_main(["--rows", path, "--today", "2026-12-15", "--out-md", md_path])
        assert rc == 0 and out == "", (rc, out, err)
        with open(md_path, encoding="utf-8") as fh:
            text = fh.read()
        assert text.startswith(TITLE) and BROKER in text
        assert err.count("[BACKTEST]") == 1, err
        os.remove(md_path)
        rc, out, err = run_main(["--rows", path, "--today", "2026-12-15", "--out-md", md_path, "--json"])
        assert rc == 0 and set(json.loads(out)) == JSON_KEYS and os.path.exists(md_path)
        rc, out, err = run_main(["--rows", path, "--out-md", os.path.join(tmp, "no-such-dir", "r.md")])
        assert rc == 2 and err.startswith("[FATAL] ") and "--out-md" in err, err
    print("  PASS test_out_md_writes_utf8_and_prints_nothing_e2e")


def test_exactly_one_backtest_summary_line_on_stderr_e2e():
    with tempfile.TemporaryDirectory(prefix="fbt-") as tmp:
        path = write_json(tmp, "rows.json", [
            {"created": "2026-10-01", "verdict": "T1 PURSUE", "status": "Passed", "n": 3},
            {"created": "2026-11-01", "verdict": "T1 PURSUE", "go": GO_SUBMIT},
            {"created": "2026-11-02", "verdict": "T1 PURSUE", "go": GO_PASS}])
        for extra in ([], ["--json"]):
            rc, out, err = run_main(["--rows", path, "--today", "2026-12-15"] + extra)
            assert rc == 0, err
            lines = [line for line in err.splitlines() if line.strip()]
            assert len(lines) == 1 and lines[0].startswith("[BACKTEST] "), lines
            for needle in ("rows=5", "records=3", "baseline=0/3", "v2.9=1/2"):
                assert needle in lines[0], (needle, lines[0])
    print("  PASS test_exactly_one_backtest_summary_line_on_stderr_e2e")


def test_help_and_missing_rows_unit():
    rc, out, err = run_main(["--help"])
    assert rc == 0, (rc, err)
    for flag in ("--rows", "--t1-rows", "--pexec-rows", "--expect-rows", "--era", "--today",
                 "--stall-days", "--min-n", "--out-md", "--json"):
        assert flag in out, flag
    rc, out, err = run_main([])
    assert rc == 2 and "--rows" in err and "Traceback" not in err, err
    print("  PASS test_help_and_missing_rows_unit")


def test_definitions_in_docstring_and_footer_unit():
    md = fb.render_markdown(agg([rec()]))
    footer = section(md, "### Definitions")
    for term in ("excluded:", "advanced_to_loi:", "go_decision:", "rejected:", "withdrawn:", "open:",
                 "decided ="):
        assert term in fb.__doc__, term
        assert term in footer, term
    assert "HARD RULE" in fb.__doc__ and "REPORT-ONLY" in fb.__doc__
    assert "Gabriel's sign-off" in fb.__doc__
    for phrase in ("must match the --era boundaries", "month-bucketed", "REST export", "QUERY N",
                   "--expect-rows", "literal date part", "nullif", "is ambiguous"):
        assert phrase in fb.__doc__, phrase
    for phrase in ("--expect-rows", "is ambiguous", "T1 precision covers explicit decisions only"):
        assert phrase in footer, phrase
    print("  PASS test_definitions_in_docstring_and_footer_unit")


def test_sources_are_ascii_only_unit():
    for path in (MODULE_PATH, os.path.abspath(__file__)):
        with open(path, "rb") as fh:
            data = fh.read()
        bad = [i for i, byte in enumerate(data) if byte > 127]
        assert not bad, "%s has non-ASCII bytes at offsets %r" % (path, bad[:5])
    print("  PASS test_sources_are_ascii_only_unit")


def main():
    test_option_sets_match_live_schema_2026_11_05_unit()
    test_known_select_values_and_blanks_unit()
    test_unknown_select_value_is_fatal_unit()
    test_unknown_select_value_main_returns_2_with_fatal_line_e2e()
    test_missing_or_unparseable_created_is_fatal_unit()
    test_created_iso_datetime_takes_the_date_part_unit()
    test_checkbox_variants_unit()
    test_p_exec_fraction_and_percent_normalization_unit()
    test_p_exec_out_of_range_or_non_numeric_is_fatal_unit()
    test_p_exec_non_whole_value_above_one_is_ambiguous_unit()
    test_n_weighting_unit()
    test_n_must_be_an_integer_of_at_least_one_unit()
    test_classify_go_decision_branches_unit()
    test_expired_unsent_is_go_but_not_advanced_unit()
    test_classify_rejected_branches_unit()
    test_dead_is_withdrawn_and_outside_the_strict_denominator_unit()
    test_held_incl_dead_second_rate_unit()
    test_classify_open_unit()
    test_excluded_rows_are_dropped_from_every_metric_unit()
    test_verdict_first_overrides_verdict_for_tier_unit()
    test_tier_basis_label_none_all_mixed_unit()
    test_era_boundary_is_inclusive_for_the_new_era_unit()
    test_era_flag_default_override_and_errors_e2e()
    test_wilson_interval_known_values_unit()
    test_brier_known_value_unit()
    test_brier_is_weighted_by_n_unit()
    test_pexec_calibration_weighted_pipeline_unit()
    test_pexec_insufficient_sample_banner_keeps_counts_unit()
    test_reliability_bin_edges_unit()
    test_pexec_rows_replace_rows_for_calibration_e2e()
    test_rate_discipline_min_n_and_zero_denominator_unit()
    test_funnel_conversion_unit()
    test_source_yield_unit()
    test_loss_class_mix_unit()
    test_data_quality_counts_unit()
    test_t1_provisional_from_t1_rows_when_they_carry_cert_unit()
    test_t1_provisional_uses_first_sighting_tier_unit()
    test_stalled_t1_exact_from_t1_rows_approximate_from_rows_unit()
    test_stalled_t1_count_and_list_unit()
    test_retiered_t1_without_decision_is_open_and_stalls_unit()
    test_stalled_t1_flags_and_list_cap_e2e()
    test_t1_rows_never_change_other_counts_e2e()
    test_results_wrapped_and_bom_export_e2e()
    test_truncated_export_is_refused_on_every_flag_e2e()
    test_row_count_reconciliation_e2e()
    test_unreadable_or_malformed_input_returns_2_e2e()
    test_export_queries_are_module_constants_documented_verbatim_unit()
    test_query_a_partitions_through_sqlite_match_per_row_metrics_e2e()
    test_verdict_outside_every_partition_is_caught_by_query_n_e2e()
    test_replay_2026_10_30_hand_backtest_zero_of_eight_e2e()
    test_markdown_has_title_and_every_section_header_unit()
    test_json_has_stable_top_level_keys_e2e()
    test_out_md_writes_utf8_and_prints_nothing_e2e()
    test_exactly_one_backtest_summary_line_on_stderr_e2e()
    test_help_and_missing_rows_unit()
    test_definitions_in_docstring_and_footer_unit()
    test_sources_are_ascii_only_unit()
    print("ALL FUNNEL-BACKTEST TESTS PASS")


if __name__ == "__main__":
    main()
