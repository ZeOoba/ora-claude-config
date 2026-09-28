"""Aggregate N independent frozen replays of ONE golden deal into a single observed result.

Why this exists (2026-08-14, n=6 repeatability finding): a single frozen replay is
not a stable measurement. Six independent replays of 2196 Port Sheldon under
IDENTICAL inputs and IDENTICAL doctrine spanned 25.0-32.0 Combined -- a 7.0-point
range that exceeds the harness's own 5.0-point tolerance. Gating on one sample
therefore risks both false FLAGs (noise read as doctrine drift) and false PASSes.

The fix is to gate on the MEAN of N replays rather than a single draw. The standard
error of a mean of N shrinks as sqrt(N): at the measured stdev of 2.31, a 3-replay
mean has SE ~1.33, where a single draw carries the full 2.31.

The gate diffs that 3-replay mean against a golden that is ITSELF an estimate (a
mean of 6, SE ~0.94), so the honest dispersion of the delta combines both:
sqrt(2.31^2/3 + 2.31^2/6) = ~1.63, i.e. a +/-2 sigma band of ~+/-3.3 pts against the
5.0-pt tolerance (false-FLAG probability ~0.2% under normality, z = 3.06). Quoting
the 3-replay SE alone (~1.33 -> +/-2.7) understates it by roughly 10x in probability
terms. Both figures clear the tolerance comfortably; the point is that the margin is
~3.3 pts, not ~2.7, and it shrinks if the golden's own n is ever reduced.

This module is deliberately pure and side-effect free: it takes parsed replay dicts
and returns one observed dict shaped for diff_verdict(), plus the dispersion stats
needed to tell "the doctrine moved" from "this deal is just noisy".

It also owns CATEGORY-KEY NORMALIZATION. The SKILL.md replay prompt asks subagents
for display-name category keys ("Product & Physical") while golden_set/*.json stores
snake_case ("product_physical"). diff_verdict() matches keys exactly, so before this
module existed every per-category delta silently came back None on a real replay
diff. That went unnoticed because the 2026-08-14 "baseline run" fed each golden
block back in as its own observed value -- golden-vs-golden trivially matched keys,
so the mismatch could not surface until the first genuine replay-to-golden diff.
"""

import statistics
from numbers import Real

# Display-name -> golden_set snake_case. Keys already in snake_case pass through.
CATEGORY_KEY_MAP = {
    "Basis": "basis",
    "Yield": "yield",
    "Product & Physical": "product_physical",
    "Market & Location": "market_location",
    "Seller & Motivation": "seller_motivation",
    "Tenancy & Lease": "tenancy_lease",
    "Value-Add Optionality": "value_add",
}

_SCALAR_FIELDS = ("quality", "economics", "expected_score", "p_exec_pct")


def _is_number(value):
    """True for real, non-bool numbers. Guards against bool being a Real subclass."""
    return isinstance(value, Real) and not isinstance(value, bool)


def normalize_category_keys(breakdown, key_map=None):
    """Fold display-name category keys to golden_set snake_case.

    Unmapped keys pass through unchanged rather than being dropped -- a silently
    discarded category would understate a per-category delta.

    Raises if two source keys collide on one target with DIFFERENT values (e.g. a
    breakdown carrying both "Product & Physical" and "product_physical"). A plain
    dict comprehension would silently keep whichever came last, which is exactly
    the silent-discard failure this module exists to prevent. Identical values
    are harmless and pass through.
    """
    if not isinstance(breakdown, dict):
        return breakdown
    mapping = CATEGORY_KEY_MAP if key_map is None else key_map
    out = {}
    for key, value in breakdown.items():
        target = mapping.get(key, key)
        if target in out and out[target] != value:
            raise ValueError(
                f"category-key collision on {target!r}: two source keys in the "
                f"same breakdown normalize to it with different values "
                f"({out[target]!r} vs {value!r}). Refusing to silently drop one -- "
                "fix the replay output rather than guessing which was intended"
            )
        out[target] = value
    return out


def _mean_scalar(replays, field):
    """Mean of a scalar field over replays that supplied a number, else None.

    A null on one replay means that replay could not support the value; it is
    excluded from the mean rather than coerced to 0, because these fields are
    informational and never gate. (Category points are handled differently --
    see _mean_categories.)
    """
    values = [r.get(field) for r in replays]
    numeric = [float(v) for v in values if _is_number(v)]
    if not numeric:
        return None
    return round(statistics.mean(numeric), 2)


def _mean_categories(replays, key_map=None):
    """Per-category means across replays, with a NULL category counted as 0 points.

    A null category is treated as 0 (NOT excluded) so the category means still sum
    to the mean Combined: a replay that returns null for a category has already
    excluded those points from its own Combined total. Excluding nulls from the
    mean instead would inflate that category above what any run actually scored
    and break the sum check.

    A replay that supplies NO category_breakdown at all is different, and is
    skipped entirely rather than treated as all-zeros. Zero-filling it would
    invent an attribution its own Combined total contradicts -- e.g. replays
    [combined 28 with {basis: 28}] and [combined 28, no breakdown] would yield a
    basis mean of 14.0 against a Combined mean of 28.0, manufacturing a phantom
    -14 per-category delta. The count of skipped replays is returned so the
    weaker basis of those means stays visible.

    Note the sum-to-Combined invariant holds exactly only when EVERY replay
    supplies a breakdown. When some don't, the category means are computed over a
    subset while Combined is computed over all replays, so the two can diverge --
    read `replays_without_breakdown` before trusting a per-category delta.

    The conflation of "scored zero" with "could not score" is real, so the count
    of nulls per category is returned as `category_null_counts` -- a category that
    is frequently null is an input-packet gap, not a true zero.
    """
    normalized = [
        normalize_category_keys(r.get("category_breakdown"), key_map)
        for r in replays
    ]
    scored = [bd for bd in normalized if isinstance(bd, dict) and bd]
    skipped = len(normalized) - len(scored)

    keys = []
    for bd in scored:
        for k in bd:
            if k not in keys:
                keys.append(k)
    if not keys:
        return None, {}, skipped

    means, null_counts = {}, {}
    for key in keys:
        points, nulls = [], 0
        for bd in scored:
            val = bd.get(key)
            if _is_number(val):
                points.append(float(val))
            else:
                points.append(0.0)
                nulls += 1
        means[key] = round(statistics.mean(points), 2)
        null_counts[key] = nulls
    return means, null_counts, skipped


def aggregate_replays(replays, key_map=None):
    """Aggregate N replays of one deal into a single observed result.

    Args:
        replays: non-empty list of parsed replay dicts. Each MUST carry a numeric
            `combined`; other fields are optional.
        key_map: optional override for category-key normalization.

    Returns:
        An observed dict for diff_verdict() -- `combined` is the MEAN across
        replays, not any single run -- carrying an `aggregate` block with:
          n, combined_samples, combined_mean, combined_stdev (None at n=1),
          combined_range, combined_min/max, combined_sem (standard error of the
          mean, None at n=1), category_null_counts, and single_sample (True at
          n=1, where the mean is just that one draw and carries no noise
          averaging -- the caller should treat the result as provisional).

    Raises:
        ValueError: if replays is empty or any replay lacks a numeric `combined`.
    """
    if not replays:
        raise ValueError("replays must be a non-empty list of parsed replay dicts")

    combined = []
    for i, r in enumerate(replays):
        value = r.get("combined")
        if not _is_number(value):
            raise ValueError(
                f"replays[{i}]['combined'] must be a number, got {value!r} -- a "
                "replay that failed to produce a usable score must be reported as "
                "an error, never silently dropped from or averaged into the mean"
            )
        combined.append(float(value))

    n = len(combined)
    mean = statistics.mean(combined)
    stdev = statistics.stdev(combined) if n > 1 else None
    category_means, null_counts, no_breakdown = _mean_categories(replays, key_map)

    observed = {
        "combined": round(mean, 2),
        "category_breakdown": category_means,
        "aggregate": {
            "n": n,
            "single_sample": n == 1,
            "combined_samples": combined,
            "combined_mean": round(mean, 2),
            "combined_stdev": round(stdev, 2) if stdev is not None else None,
            "combined_sem": round(stdev / (n ** 0.5), 2) if stdev is not None else None,
            "combined_min": min(combined),
            "combined_max": max(combined),
            "combined_range": round(max(combined) - min(combined), 2),
            "category_null_counts": null_counts,
            "replays_without_breakdown": no_breakdown,
        },
    }
    for field in _SCALAR_FIELDS:
        observed[field] = _mean_scalar(replays, field)

    # Tier/floor labels are strings and cannot be averaged. Carry the first
    # replay's verbatim for the informational tier check, and keep every distinct
    # label so a run where replays disagreed on tier stays visible rather than
    # being silently represented by run 1's label alone.
    for field in ("verdict_tier", "floor_result"):
        labels = [r.get(field) for r in replays if isinstance(r.get(field), str)]
        observed[field] = labels[0] if labels else None
        distinct = sorted(set(labels))
        if len(distinct) > 1:
            observed["aggregate"][f"{field}_variants"] = distinct

    return observed
