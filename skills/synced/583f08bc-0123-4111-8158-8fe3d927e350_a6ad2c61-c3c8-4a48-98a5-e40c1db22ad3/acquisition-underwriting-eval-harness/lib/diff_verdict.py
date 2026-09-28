"""Comparison/tolerance engine for the acquisition-underwriting golden-set harness.

Pure function: diff a live SCREEN-mode replay's observed result against one
frozen golden_set/*.json record. The pilot's primary signal is the combined
score only (per every golden file's diff_policy.primary_signal); tier and
per-category comparisons are reported as informational detail and never gate.

`golden["golden"]` values are taken as given, never recomputed or "corrected"
by this module — as of the 2026-08-14 rebaseline they are themselves a fresh
replay's own output (see each golden file's `baselined_date`), not an
external archive, so there is nothing to reconcile here. The ORIGINAL
Notion-archived pre-rebaseline scores (where they carried their own internal
arithmetic inconsistencies, e.g. quality + economics != combined on the 1333
Research Rd and Liberty Office Park rows) live under the sibling key
`archived_pre_v03_reference` and are never read by this module.
"""

import re
from numbers import Real

_VALID_CONFIDENCE_LEVELS = ("HIGH", "MEDIUM", "LOW")

# cc-audit-army finding M18-eval-harness-cannot-detect-governor-drift (2026-08-21), Gabriel-
# approved NARROW fix: the harness gated on Combined score only, and DSCR/IRR are excluded from
# Combined BY DESIGN (acquisition-underwriting/SKILL.md: "IRR remains floor-only... NOT
# point-scored"; the 100-pt scorecard has no DSCR row) — so a change to the 1.25x DSCR governor
# or the 8% YoC floor produced a Combined delta of exactly zero and could never move `status`.
# Governor outcomes exist today only as free-form prose inside floor_result, and that prose is
# too inconsistent across golden files (ranges, varying orderings, one row structured entirely
# differently, several rows that never restate the floor number at all) to reliably parse the
# per-deal COMPUTED values — a parsing bug there would silently fabricate a wrong financial
# number, worse than the known gap. This stays deliberately narrow: it parses ONLY an explicit
# "<observed> vs <floor>" comparison for the two floors that are TRUE fixed constants across
# every deal (DSCR 1.25x, YoC 8.0% — unlike the Basis floor, which is vintage-dependent per deal
# and is NOT attempted here). Any row whose prose doesn't state that comparison in this exact
# shape is reported as an explicit "not verified" gap, never silently skipped or guessed.
_CANON_DSCR_FLOOR = 1.25
_CANON_YOC_FLOOR = 8.0

# Label + two patterns per label, because the underlying prose has "varying orderings"
# (see module comment above) and neither the label's position relative to the two numbers,
# nor which capture group is observed vs. floor, can be assumed fixed. Confirmed real
# golden-file shape: "~6.0-6.9% YoC vs 8.0% floor" -- the observed number precedes the
# LABEL ITSELF, not just the floor. Handling that means matching is scoped to the label's
# own semicolon-delimited CLAUSE (see module comment below; searched independently, not
# required to sit adjacent to either number) rather than anchoring a single regex to "LABEL ... num1 ...
# sep ... num2" in that literal order. Within that clause: _EXPLICIT_FLOOR_RE requires the
# word "floor" to sit directly next to (and unambiguously label) ONE specific number --
# "floor of 1.25x" or "1.25x floor" immediately followed by "vs <other>" -- so that number
# is floor regardless of position; tried FIRST since it is the unambiguous case.
# _POSITIONAL_RE (group1=observed, group2=floor) is the fallback for plain "<num> vs <num>"
# with no adjacent "floor" label -- the shape "YoC vs 8.0% floor" itself resolves via this
# fallback (floor trails the already-second number there, not a genuine reorder).
# Deliberately NOT canon-matching to disambiguate (i.e. "whichever number equals 1.25 must
# be the floor"): that would defeat the exact case this check exists to catch -- a REAL
# drift means the floor number in the text no longer equals canon, so canon-matching could
# never identify it as "floor" then.
_DSCR_LABEL_RE = re.compile(r"DSCR\b", re.I)
# Leading \b so this can't match the "YC" inside an unrelated word like "NYC".
_YOC_LABEL_RE = re.compile(r"\bYo?C\b", re.I)
_EXPLICIT_FLOOR_X_RE = re.compile(
    r"(?:floor\s+of\s+(\d+(?:\.\d+)?)x|(\d+(?:\.\d+)?)x\s+floor)"
    r"[^.;]{0,20}?(?:vs\.?|against)\s*(\d+(?:\.\d+)?)x", re.I)
_EXPLICIT_FLOOR_PCT_RE = re.compile(
    r"(?:floor\s+of\s+(\d+(?:\.\d+)?)%|(\d+(?:\.\d+)?)%\s+floor)"
    r"[^.;]{0,20}?(?:vs\.?|against)\s*(\d+(?:\.\d+)?)%", re.I)
# The `(?:label\s*)?` segment tolerates the confirmed real shape "6.9% YoC vs 8.0% floor",
# where the label sits between the first number and the vs/against separator rather than
# immediately after it.
_POSITIONAL_X_RE = re.compile(r"(\d+(?:\.\d+)?)x\s*(?:DSCR\b\s*)?(?:vs\.?|against|floor\s+of)\s*(\d+(?:\.\d+)?)x", re.I)
_POSITIONAL_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)%\s*(?:\bYo?C\b\s*)?(?:vs\.?|against|floor\s+of)\s*(\d+(?:\.\d+)?)%", re.I)

# Real floor_result prose always separates distinct metric assertions (Basis / YoC / DSCR
# / IRR) with a semicolon -- confirmed across every golden file, including cases where
# "and" joins two metrics' prose within a single semicolon-delimited segment (e.g. 1333
# Research Rd's "...vs 65% vintage-ramp floor (...) and YoC ~6.5% vs 8.0% floor..."). A
# FIXED CHARACTER WINDOW around a label mention (the prior approach) can still reach past
# that semicolon into an unrelated clause -- on "Basis 75.0% vs 65% floor; YoC 10.96% vs
# 8%", a window centered on "YoC" easily spans back into the Basis clause, and
# _POSITIONAL_PCT_RE (whose label group is optional) then matches the Basis pair (75.0,
# 65.0) instead of the YoC pair -- a silent false negative on exactly the drift class this
# module exists to catch. Scoping the search to the label's own clause (bounded by the
# nearest ';' on each side, or the string's start/end) makes that CROSS-SEMICOLON capture
# impossible: the numbers on the other side of a ';' are never read as a comparison for a
# label found in a different clause.
#
# KNOWN RESIDUAL LIMITATION (2026-08-22 re-review): this does not fully close the same bug
# class WITHIN one semicolon-delimited clause. All 6 real golden files that join Basis and
# YoC prose with "and" instead of ';' (e.g. 1333 Research Rd's "...vs 65% vintage-ramp
# floor (...) and YoC ~6.5% vs 8.0% floor...") parse correctly today only because their
# Basis text has a word (e.g. "discount", "vintage-ramp") sitting between a number and the
# vs/floor keyword, which breaks _POSITIONAL_PCT_RE's adjacency requirement. A future
# golden/observed row that phrases an "and"-joined Basis clause as compactly as "Basis 54%
# vs 65% floor and YoC 6.9% vs 8.0%" (no intervening qualifier word, no ';') would still
# let the YoC search capture the Basis pair -- confirmed by direct execution against that
# string during the 2026-08-22 re-review. Not fixed here to keep this a narrow, Gabriel-
# approved change (see finding M18 above); if a real golden/observed row is ever found in
# this compact "and"-joined shape, the fix is to require _POSITIONAL_PCT_RE's/_POSITIONAL_X_RE's
# optional label group when the clause contains more than one recognized metric label.


def _parse_floor_pair(text, label_pattern, explicit_pattern, positional_pattern):
    """(observed, floor) as floats from the FIRST unambiguous match within the semicolon-
    delimited CLAUSE containing `label_pattern`'s mention in `text` (see module comment
    above), or None if `text` isn't a string, the label never appears, or no recognized
    comparison shape is found in that clause. Never guesses at which number is which from
    an ambiguous match, and never reaches into a different clause to find one."""
    if not isinstance(text, str):
        return None
    label_match = label_pattern.search(text)
    if not label_match:
        return None
    prior_semi = text.rfind(";", 0, label_match.start())
    start = prior_semi + 1 if prior_semi != -1 else 0
    next_semi = text.find(";", label_match.end())
    end = next_semi if next_semi != -1 else len(text)
    window = text[start:end]

    m = explicit_pattern.search(window)
    if m:
        floor = float(m.group(1) if m.group(1) is not None else m.group(2))
        observed = float(m.group(3))
        return observed, floor
    m = positional_pattern.search(window)
    if not m:
        return None
    return float(m.group(1)), float(m.group(2))


def _check_floor_constants(golden_floor_result, observed_floor_result):
    """Compare the DSCR/YoC floor CONSTANTS stated in golden vs observed floor_result prose.

    Returns (notes, drift_detected): drift_detected is True only when BOTH sides parsed
    unambiguously AND the stated floor constants disagree with each other -- that is governor
    drift, exactly what this check exists to catch, and it gates (see diff_verdict below). An
    unparseable side never counts as drift; it is reported as a gap in `notes` only.
    """
    notes = []
    drift_detected = False
    for label, label_pattern, explicit_pattern, positional_pattern, canon in (
        ("DSCR", _DSCR_LABEL_RE, _EXPLICIT_FLOOR_X_RE, _POSITIONAL_X_RE, _CANON_DSCR_FLOOR),
        ("YoC", _YOC_LABEL_RE, _EXPLICIT_FLOOR_PCT_RE, _POSITIONAL_PCT_RE, _CANON_YOC_FLOOR),
    ):
        golden_pair = _parse_floor_pair(golden_floor_result, label_pattern, explicit_pattern, positional_pattern)
        observed_pair = _parse_floor_pair(observed_floor_result, label_pattern, explicit_pattern, positional_pattern)
        if golden_pair is None or observed_pair is None:
            unparsed_sides = [
                side for side, pair in (("golden", golden_pair), ("observed", observed_pair)) if pair is None
            ]
            notes.append(
                f"{label} floor constant not verified: floor_result prose on "
                f"{' and '.join(unparsed_sides)} side does not state an explicit "
                "'<observed> vs <floor>' comparison (reported as a gap, not assumed clean)"
            )
            continue
        _golden_observed, golden_floor = golden_pair
        _observed_observed, observed_floor = observed_pair
        if golden_floor != observed_floor:
            drift_detected = True
            notes.append(
                f"GOVERNOR DRIFT on {label} floor: golden states {golden_floor} vs observed "
                f"states {observed_floor} (canonical: {canon})"
            )
        elif golden_floor != canon:
            # Both sides agree with EACH OTHER but not with the canonical constant -- the golden
            # fixture itself may be stale (baselined against an older governor value). Reported,
            # not gated: this module never recomputes/"corrects" golden values (see module
            # docstring); a stale golden fixture is a fixture-maintenance finding, not a live
            # replay defect.
            notes.append(
                f"{label} floor ({golden_floor}) on both sides differs from the canonical value "
                f"({canon}) -- golden fixture may be stale, not a live drift"
            )
    return notes, drift_detected


def _require_number(value, label):
    """Return value if it is a real (non-bool) number, else raise ValueError."""
    if isinstance(value, Real) and not isinstance(value, bool):
        return float(value)
    raise ValueError(f"{label} must be a number, got {value!r}")


def _is_number_or_none(value):
    """True for None or a real (non-bool) number -- guards optional aggregate fields."""
    return value is None or (isinstance(value, Real) and not isinstance(value, bool))


def _normalize_tier(tier):
    """Normalize a tier label for informational comparison.

    Strips any trailing parenthetical annotation (McCormick's archived tier is
    'KILLED (post-hoc status overwrite, ...)'), then compares casefolded.
    Returns None for non-string/empty input.
    """
    if not isinstance(tier, str):
        return None
    base = tier.split("(", 1)[0].strip()
    return base.casefold() if base else None


def _category_deltas(golden_bd, observed_bd):
    """Per-category observed-minus-golden deltas, or None if either side absent.

    Only numeric golden entries are diffed (Hamilton's breakdown carries
    non-numeric '*_flag' annotation entries — skipped). A golden category
    missing or non-numeric on the observed side maps to None so the reader
    sees the gap rather than a silent omission.
    """
    if not isinstance(golden_bd, dict) or not isinstance(observed_bd, dict):
        return None
    deltas = {}
    for key, golden_val in golden_bd.items():
        if not (isinstance(golden_val, Real) and not isinstance(golden_val, bool)):
            continue  # annotation entry like 'basis_flag': '[est]'
        observed_val = observed_bd.get(key)
        if isinstance(observed_val, Real) and not isinstance(observed_val, bool):
            deltas[key] = float(observed_val) - float(golden_val)
        else:
            deltas[key] = None
    return deltas


def diff_verdict(golden: dict, observed: dict) -> dict:
    """Diff one observed SCREEN replay against its golden record.

    Args:
        golden: full parsed golden_set/*.json dict (top-level `confidence` and
            `diff_policy`; scores under `golden`, keyed `golden["golden"]["verdict_tier"]`
            -- NOT `archived_verdict_tier`, which is a pre-2026-08-14-rebaseline field
            name that only survives inside `archived_pre_v03_reference` for historical
            context and is never read by this module).
        observed: replay report dict with at least `combined` (float),
            `verdict_tier` (str), and optionally `category_breakdown` (dict|None).

    Returns:
        Result dict. `status` (PASS/FLAG) is driven by the combined-score tolerance --
        strictly beyond tolerance flags; exactly at tolerance passes -- OR by a confirmed
        DSCR/YoC floor-constant drift (both sides parsed unambiguously and disagree; see
        `_check_floor_constants`), since DSCR/IRR are excluded from Combined by design and a
        governor change there would otherwise never move status. `scored` is False (and
        `informational_only` True) for LOW-confidence golden rows: the delta is still computed
        and reported, but the caller must exclude the row from any strict pass/fail tally.

    Raises:
        ValueError: if either combined score or the tolerance is missing/non-numeric,
            or if golden['confidence'] is not one of HIGH/MEDIUM/LOW.
    """
    golden_block = golden.get("golden") or {}
    diff_policy = golden.get("diff_policy") or {}

    combined_golden = _require_number(
        golden_block.get("combined"), "golden['golden']['combined']"
    )
    combined_observed = _require_number(
        observed.get("combined"), "observed['combined']"
    )
    tolerance_pts = _require_number(
        diff_policy.get("tolerance_combined_pts"),
        "golden['diff_policy']['tolerance_combined_pts']",
    )

    combined_delta = combined_observed - combined_golden
    floor_notes, floor_drift = _check_floor_constants(
        golden_block.get("floor_result"), observed.get("floor_result")
    )
    # aggregate_replays.py carries only replay #1's verbatim text into observed['floor_result']
    # (never a 3-replay consensus -- see its own comment there); when replays disagreed on that
    # wording, `floor_result_variants` is populated and a floor-constant comparison built on
    # replay #1 alone cannot distinguish real governor drift from replay-to-replay prose
    # variance. Never gate status on that -- report it as a gap instead (never a single draw).
    if floor_drift and (observed.get("aggregate") or {}).get("floor_result_variants"):
        floor_drift = False
        floor_notes.append(
            "floor constant drift NOT gated: replays disagreed on floor_result wording "
            f"({observed['aggregate']['floor_result_variants']}) -- observed['floor_result'] is "
            "only replay #1's text, not a 3-replay consensus, so drift here cannot be "
            "distinguished from replay-to-replay phrasing variance"
        )
    status = "FLAG" if (abs(combined_delta) > tolerance_pts or floor_drift) else "PASS"

    confidence = golden.get("confidence")
    if confidence not in _VALID_CONFIDENCE_LEVELS:
        raise ValueError(
            f"golden['confidence'] must be one of {_VALID_CONFIDENCE_LEVELS}, "
            f"got {confidence!r} -- an unrecognized value must not silently "
            "fall through to scored=False (that would exclude a row from the "
            "strict pass/fail tally without anyone deciding to)"
        )
    scored = confidence in ("HIGH", "MEDIUM")

    golden_tier = golden_block.get("verdict_tier")
    observed_tier = observed.get("verdict_tier")
    norm_golden = _normalize_tier(golden_tier)
    norm_observed = _normalize_tier(observed_tier)
    tier_match = (
        norm_golden is not None
        and norm_observed is not None
        and norm_golden == norm_observed
    )

    category_deltas = _category_deltas(
        golden_block.get("category_breakdown"), observed.get("category_breakdown")
    )

    notes = []
    notes.extend(floor_notes)
    known_gaps = golden.get("known_gaps") or []
    for gap in known_gaps:
        notes.append(f"known_gap: {gap}")
    if not scored:
        notes.append(
            f"excluded from strict scoring: {confidence} confidence "
            "(delta reported as informational only)"
        )
    if not tier_match:
        notes.append(
            "tier mismatch (informational only, per diff_policy.tier_check): "
            f"golden={golden_tier!r} vs observed={observed_tier!r}"
        )
    if category_deltas is None and golden_block.get("category_breakdown"):
        notes.append(
            "golden category_breakdown present but observed side absent — "
            "per-category deltas not computed"
        )

    # Carry the aggregation provenance (n, samples, stdev, range) through to the
    # result so record_run() persists it. Without this the snapshot cannot show
    # how many replays actually went into `combined_observed` -- a mean built
    # from 2-of-3 parsed replays would be indistinguishable from a clean run in
    # the permanent record, and Step 3's range-exceeds-tolerance advisory would
    # be unrecordable. Absent for a single-replay (unaggregated) observed dict.
    aggregate = observed.get("aggregate")
    if isinstance(aggregate, dict):
        n = aggregate.get("n")
        observed_range = aggregate.get("combined_range")
        if isinstance(n, int) and n < 3:
            notes.append(
                f"degraded measurement: mean built from only {n} replay(s) -- "
                "the harness gates on a 3-replay mean (SKILL.md Step 1)"
            )
        if (
            _is_number_or_none(observed_range)
            and observed_range is not None
            and observed_range > tolerance_pts
        ):
            notes.append(
                f"replay spread ({observed_range} pts) exceeds this deal's own "
                f"tolerance ({tolerance_pts} pts) -- the replays disagreed with "
                "each other by more than the gate's width, so this verdict is "
                "weakly supported whichever way it landed"
            )

    return {
        "deal_id": golden.get("deal_id"),
        "status": status,
        "scored": scored,
        "informational_only": not scored,
        "confidence": confidence,
        "combined_golden": combined_golden,
        "combined_observed": combined_observed,
        "combined_delta": combined_delta,
        "tolerance_pts": tolerance_pts,
        "tier_match": tier_match,
        "golden_tier": golden_tier,
        "observed_tier": observed_tier,
        "category_deltas": category_deltas,
        "aggregate": aggregate if isinstance(aggregate, dict) else None,
        "floor_drift": floor_drift,
        "notes": notes,
    }
