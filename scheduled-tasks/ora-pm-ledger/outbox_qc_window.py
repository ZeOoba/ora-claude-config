#!/usr/bin/env python3
"""
ora-pm-ledger / Block B — Outbox QC sweep-window planner (retro-sweep mode).

WHY THIS EXISTS
  Block B originally swept only [today 00:00 -> run time]. That left TWO permanent
  holes, and the spec was wrong about the second:

  1. MISSED DAYS. If the task doesn't fire (machine offline overnight — e.g. 2026-07-23),
     that day's outbound mail is never audited. Nothing retries it.
  2. EVENING TAILS. The old spec claimed mail sent after the ~18:00 fire "lands in next
     day's window". It does not. The next day's window is [D+1 00:00 -> D+1 18:00], and a
     message sent 18:30 on day D carries sentDateTime on day D — so it falls in NO window,
     ever. Every single day silently lost its 18:00->24:00 tail.

  Both are the same bug: coverage was modelled as "did we run today?" instead of "which
  spans of time have actually been swept?". This tracks COVERED INTERVALS and reports the
  uncovered gaps, which closes both holes with one mechanism.

USAGE
  --plan   --now <iso>                      -> RESULT_JSON with the gaps to sweep now
  --commit --date <YYYY-MM-DD> --from <iso> --to <iso>
                                            -> record a span as swept (call ONLY after the
                                               day's page+email actually succeeded)
  --selftest                                -> no-network unit tests

BOOTSTRAP: there is no separate seed mode — replay the historical sweeps with --commit,
one call per already-swept day (the first commit sets `tracking_since`, which floors the
window so nothing before it is ever claimed as owed).

FAIL-CLOSED: --commit is a separate step on purpose. If the Notion post or the send fails,
do NOT commit — the gap stays open and the next run retries it. Committing on plan would
silently swallow a day whose report never reached Gabriel.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
STATE_PATH = os.path.join(STATE_DIR, "outbox-qc-coverage.json")

# How far back a single run will reach. Bounds runtime: each retro day costs an Outlook
# query + a Notion page. Gaps older than this are REPORTED as dropped, never silently lost.
LOOKBACK_DAYS = 7
# Never report gaps before this many days back even as dropped — keeps the report bounded.
DROPPED_HORIZON_DAYS = 30
# Ignore sub-minute slivers (run-time jitter between plan and commit).
MIN_GAP_SECONDS = 60


# ---------- time helpers ----------
def parse_dt(s):
    d = datetime.fromisoformat(s)
    return d.astimezone(ET) if d.tzinfo else d.replace(tzinfo=ET)


def iso(d):
    return d.isoformat()


def day_bounds(date_str, now):
    """[00:00:00, min(end-of-day, now)] in ET for a YYYY-MM-DD string."""
    start = datetime.fromisoformat(date_str + "T00:00:00").replace(tzinfo=ET)
    end = start + timedelta(days=1) - timedelta(microseconds=1)
    return start, min(end, now)


# ---------- interval algebra ----------
def merge(intervals):
    out = []
    for s, e in sorted(intervals):
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def subtract(span, covered):
    """span minus covered -> list of uncovered [start, end]."""
    s, e = span
    gaps, cursor = [], s
    for cs, ce in merge(covered):
        if ce <= cursor or cs >= e:
            continue
        if cs > cursor:
            gaps.append([cursor, min(cs, e)])
        cursor = max(cursor, ce)
        if cursor >= e:
            break
    if cursor < e:
        gaps.append([cursor, e])
    return [g for g in gaps if (g[1] - g[0]).total_seconds() >= MIN_GAP_SECONDS]


# ---------- state ----------
def empty_state():
    """Fresh state. MUST be a function, not a module-level dict: `dict(CONST)` only
    shallow-copies, so every caller would share — and mutate — the same `covered` dict,
    silently cross-contaminating state between calls in one process."""
    return {"version": 1, "tracking_since": None, "covered": {}}


def load_state():
    """State, or a fresh empty one. A corrupt/hand-broken file must NOT raise: an uncaught
    exception here kills every subsequent 18:00 run until a human notices, turning one
    transient crash into a permanent silent outage of the report. Degrading to empty is
    safe in the only direction that matters — it re-sweeps, it never marks unswept time as
    covered."""
    if not os.path.exists(STATE_PATH):
        return empty_state(), None
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            st = json.load(f)
        if not isinstance(st, dict) or not isinstance(st.get("covered"), dict):
            return empty_state(), "coverage state had unexpected shape - reset to empty"
        # Validate every span parses AND is correctly ordered. commit() rejects inverted
        # spans at the entry point, but a hand-edited or legacy file can still carry one,
        # and the interval algebra turns it into permanently overlapping gaps (a 1440-min
        # day reporting >1440 uncovered minutes, re-sweeping the same hours forever).
        # Drop them and say so — dropping over-sweeps, which is the safe direction.
        dropped = []
        for d, spans in st["covered"].items():
            good = []
            for a, b in spans:
                if parse_dt(b) <= parse_dt(a):
                    dropped.append("%s %s->%s" % (d, a, b))
                else:
                    good.append([a, b])
            st["covered"][d] = good
        if dropped:
            return st, ("dropped %d malformed (non-increasing) coverage span(s), those "
                        "windows will be re-swept: %s" % (len(dropped), "; ".join(dropped[:5])))
        return st, None
    except Exception as e:
        return empty_state(), "coverage state unreadable (%s: %s) - reset to empty" % (
            type(e).__name__, e)


def save_state(st, now=None):
    """Persist atomically (tmp + os.replace) so a crash cannot truncate the file.

    `now` is injected rather than read from the clock: pruning on the real date while the
    caller operates on an injected date silently discarded spans the caller had just
    committed (and a machine clock skewed forward would wipe live coverage).
    """
    os.makedirs(STATE_DIR, exist_ok=True)
    today = (now or datetime.now(ET)).date()
    keep = {}
    for d, spans in st.get("covered", {}).items():
        try:
            age = (today - datetime.fromisoformat(d).date()).days
        except ValueError:
            continue  # unparseable key: drop rather than propagate corruption
        if age <= DROPPED_HORIZON_DAYS * 2:
            keep[d] = spans
    st["covered"] = keep
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, STATE_PATH)


def covered_for(st, date_str):
    return [[parse_dt(a), parse_dt(b)] for a, b in st.get("covered", {}).get(date_str, [])]


# ---------- planning ----------
def plan(st, now, lookback=LOOKBACK_DAYS):
    today = now.date()
    tracking_since = (datetime.fromisoformat(st["tracking_since"]).date()
                      if st.get("tracking_since") else None)

    def eligible(d):
        return tracking_since is None or d >= tracking_since

    days = []
    for back in range(lookback - 1, -1, -1):
        d = today - timedelta(days=back)
        if not eligible(d):
            continue
        ds = d.isoformat()
        span = day_bounds(ds, now)
        if span[1] <= span[0]:
            continue
        gaps = subtract(span, covered_for(st, ds))
        if not gaps:
            continue
        days.append({
            "date": ds,
            "is_today": d == today,
            "weekend": d.weekday() >= 5,
            "gaps": [[iso(a), iso(b)] for a, b in gaps],
            "uncovered_minutes": int(sum((b - a).total_seconds() for a, b in gaps) // 60),
        })

    # Anything still uncovered but older than the lookback: reported, never silently lost.
    dropped = []
    for back in range(lookback, DROPPED_HORIZON_DAYS + 1):
        d = today - timedelta(days=back)
        if not eligible(d):
            continue
        ds = d.isoformat()
        if subtract(day_bounds(ds, now), covered_for(st, ds)):
            dropped.append(ds)

    return {
        "now": iso(now),
        "today": today.isoformat(),
        "lookback_days": lookback,
        "tracking_since": st.get("tracking_since"),
        "days_to_sweep": days,
        "retro_days": [d for d in days if not d["is_today"]],
        "dropped_beyond_lookback": sorted(dropped),
    }


def commit(st, date_str, frm, to):
    # Reject inverted/empty spans. An inverted span is stored happily by the interval
    # algebra but then yields OVERLAPPING gaps forever after (a 1440-minute day reporting
    # 1920 uncovered minutes), double-sweeping until the state file is hand-repaired.
    if parse_dt(to) <= parse_dt(frm):
        raise ValueError("--to (%s) must be after --from (%s)" % (to, frm))
    spans = st.setdefault("covered", {}).setdefault(date_str, [])
    merged = merge([[parse_dt(a), parse_dt(b)] for a, b in spans] + [[parse_dt(frm), parse_dt(to)]])
    st["covered"][date_str] = [[iso(a), iso(b)] for a, b in merged]
    if not st.get("tracking_since"):
        st["tracking_since"] = date_str
    return st


# ---------- selftest ----------
def selftest():
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("  PASS " if cond else "  FAIL ") + msg)
        ok = ok and cond

    def st_with(covered, since="2026-07-20"):
        return {"version": 1, "tracking_since": since, "covered": covered}

    now = parse_dt("2026-07-24T18:00:00-04:00")

    # 1. Fully-swept prior days + today unswept -> only today.
    s = st_with({
        "2026-07-20": [["2026-07-20T00:00:00-04:00", "2026-07-20T23:59:59-04:00"]],
        "2026-07-21": [["2026-07-21T00:00:00-04:00", "2026-07-21T23:59:59-04:00"]],
        "2026-07-22": [["2026-07-22T00:00:00-04:00", "2026-07-22T23:59:59-04:00"]],
        "2026-07-23": [["2026-07-23T00:00:00-04:00", "2026-07-23T23:59:59-04:00"]],
    })
    p = plan(s, now)
    check([d["date"] for d in p["days_to_sweep"]] == ["2026-07-24"], "only today when history complete")
    check(p["retro_days"] == [], "no retro days when history complete")

    # 2. THE MISSED DAY — real history: 07-20/21/22 swept, 07-23 never fired (machine
    #    offline overnight). It must surface as a full-day retro gap.
    s2 = st_with({
        "2026-07-20": [["2026-07-20T00:00:00-04:00", "2026-07-20T23:59:59-04:00"]],
        "2026-07-21": [["2026-07-21T00:00:00-04:00", "2026-07-21T23:59:59-04:00"]],
        "2026-07-22": [["2026-07-22T00:00:00-04:00", "2026-07-22T23:59:59-04:00"]],
    })
    p2 = plan(s2, now)
    dates = [d["date"] for d in p2["days_to_sweep"]]
    check("2026-07-23" in dates, "missed day 07-23 detected")
    g23 = next(d for d in p2["days_to_sweep"] if d["date"] == "2026-07-23")
    check(g23["uncovered_minutes"] > 1430, "07-23 reported as a FULL day (~1440 min)")
    check([d["date"] for d in p2["retro_days"]] == ["2026-07-23"], "07-23 classified retro, today is not")

    # 3. THE EVENING TAIL — the hole the old spec denied existed. 07-22 swept only to
    #    18:15; 18:15->24:00 must resurface as a gap.
    s3 = st_with({
        "2026-07-22": [["2026-07-22T00:00:00-04:00", "2026-07-22T18:15:00-04:00"]],
        "2026-07-23": [["2026-07-23T00:00:00-04:00", "2026-07-23T23:59:59-04:00"]],
    })
    p3 = plan(s3, now)
    tail = next((d for d in p3["days_to_sweep"] if d["date"] == "2026-07-22"), None)
    check(tail is not None, "evening tail of 07-22 detected")
    check(tail and tail["gaps"][0][0].startswith("2026-07-22T18:15"), "tail gap starts at 18:15")
    check(tail and 340 <= tail["uncovered_minutes"] <= 346, "tail is ~5h45m (18:15->24:00)")

    # 4. Today is capped at `now`, never the whole calendar day.
    tdy = next(d for d in p3["days_to_sweep"] if d["date"] == "2026-07-24")
    check(tdy["gaps"][0][1].startswith("2026-07-24T18:00"), "today's gap ends at now, not midnight")

    # 5. Re-running after a commit is a no-op for that span (idempotent).
    s5 = commit(st_with({}), "2026-07-24", "2026-07-24T00:00:00-04:00", "2026-07-24T18:00:00-04:00")
    p5 = plan(s5, now)
    check(not any(d["date"] == "2026-07-24" for d in p5["days_to_sweep"]), "committed span not re-swept")

    # 6. Lookback clamp: an old uncovered day is DROPPED, and reported — not silent.
    s6 = st_with({}, since="2026-07-01")
    p6 = plan(s6, now, lookback=3)
    check(len(p6["days_to_sweep"]) == 3, "lookback=3 sweeps exactly 3 days")
    check("2026-07-10" in p6["dropped_beyond_lookback"], "older uncovered day reported as dropped")
    check(all(d not in [x["date"] for x in p6["days_to_sweep"]]
              for d in p6["dropped_beyond_lookback"]), "dropped days are not also swept")

    # 7. tracking_since floor: nothing before bootstrap is ever claimed as owed.
    s7 = st_with({}, since="2026-07-23")
    p7 = plan(s7, now)
    check([d["date"] for d in p7["days_to_sweep"]] == ["2026-07-23", "2026-07-24"],
          "tracking_since floors the window")
    check(p7["dropped_beyond_lookback"] == [], "nothing dropped before tracking_since")

    # 8. Interval merge handles out-of-order and overlapping commits.
    s8 = commit(st_with({}), "2026-07-24", "2026-07-24T12:00:00-04:00", "2026-07-24T18:00:00-04:00")
    s8 = commit(s8, "2026-07-24", "2026-07-24T00:00:00-04:00", "2026-07-24T13:00:00-04:00")
    check(len(s8["covered"]["2026-07-24"]) == 1, "overlapping commits merge into one span")
    check(not any(d["date"] == "2026-07-24" for d in plan(s8, now)["days_to_sweep"]),
          "merged span fully covers today")

    # 9. Weekend days are surfaced (flagged), not skipped — Fri-tail + Sat/Sun mail would
    #    otherwise be permanently unaudited given Block B's Mon-Fri cadence.
    #    2026-07-25 Sat, 07-26 Sun, 07-27 Mon.
    mon = parse_dt("2026-07-27T18:00:00-04:00")
    p9 = plan(st_with({}, since="2026-07-25"), mon)
    check([d["date"] for d in p9["days_to_sweep"]] == ["2026-07-25", "2026-07-26", "2026-07-27"],
          "Monday run reaches back over the weekend")
    check([d["date"] for d in p9["days_to_sweep"] if d["weekend"]] == ["2026-07-25", "2026-07-26"],
          "Sat+Sun flagged weekend, Monday not")

    # 10. Sub-minute slivers are ignored (no noise from plan/commit jitter).
    s10 = commit(st_with({}), "2026-07-24", "2026-07-24T00:00:00-04:00", "2026-07-24T17:59:30-04:00")
    check(not any(d["date"] == "2026-07-24" for d in plan(s10, now)["days_to_sweep"]),
          "30-second sliver ignored")

    # --- REVIEW-PASS REGRESSIONS (independent review 2026-07-24) ---

    # 11. Inverted / zero-length spans are refused, not stored. Storing one yields
    #     overlapping gaps forever (a 1440-min day reporting 1920 uncovered minutes).
    try:
        commit(st_with({}), "2026-07-24", "2026-07-24T18:00:00-04:00", "2026-07-24T06:00:00-04:00")
        check(False, "inverted span rejected")
    except ValueError:
        check(True, "inverted span rejected")
    try:
        commit(st_with({}), "2026-07-24", "2026-07-24T06:00:00-04:00", "2026-07-24T06:00:00-04:00")
        check(False, "zero-length span rejected")
    except ValueError:
        check(True, "zero-length span rejected")

    # 12. save_state prunes against the INJECTED now, not the wall clock — otherwise a
    #     just-accepted commit for an out-of-window date is silently discarded on write.
    #     The date is derived as (real today - 200d) so this test DISCRIMINATES whenever it
    #     runs: under the wall clock that span is 200 days old and gets pruned (fail);
    #     under the injected now it is age 0 and survives (pass). An earlier version of
    #     this test committed *today's* date, which both clocks keep — it passed with the
    #     fix reverted and therefore certified nothing.
    global STATE_PATH
    real_path = STATE_PATH
    STATE_PATH = os.path.join(STATE_DIR, "_selftest-coverage.json")
    try:
        old_day = (datetime.now(ET) - timedelta(days=200)).date().isoformat()
        old_now = parse_dt(old_day + "T18:00:00")
        s12 = commit(empty_state(), old_day, old_day + "T00:00:00", old_day + "T18:00:00")
        save_state(s12, now=old_now)
        back, warn = load_state()
        check(warn is None and old_day in back.get("covered", {}),
              "prune honors injected now, not the wall clock (200d-old span survives)")

        # Same span written with the REAL clock is correctly pruned — proves the prune
        # still works and the test above is measuring the clock source, not a no-op prune.
        s12b = commit(empty_state(), old_day, old_day + "T00:00:00", old_day + "T18:00:00")
        save_state(s12b)  # now=None -> wall clock
        back2, _ = load_state()
        check(old_day not in back2.get("covered", {}),
              "prune still drops genuinely stale spans under the wall clock")

        s12c = commit(empty_state(), "2026-07-24",
                      "2026-07-24T00:00:00-04:00", "2026-07-24T18:00:00-04:00")
        save_state(s12c, now=now)
        back3, warn3a = load_state()
        check(warn3a is None and "2026-07-24" in back3.get("covered", {}),
              "committed span survives save/load round-trip")

        # 13. Corrupt state degrades to empty WITH a warning instead of raising — an
        #     uncaught error here would kill every future unattended run.
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            f.write('{"covered": {"2026-07-24": [["not-a-date","also-not"]]}}')
        bad, warn2 = load_state()
        check(warn2 is not None and bad["covered"] == {}, "corrupt state -> empty + warning")
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            f.write("")  # truncated write, the crash-mid-save shape
        empty, warn3 = load_state()
        check(warn3 is not None and empty["covered"] == {}, "truncated state -> empty + warning")

        # 14. Atomic write leaves no .tmp behind.
        save_state(empty_state(), now=now)
        check(not os.path.exists(STATE_PATH + ".tmp"), "atomic write leaves no .tmp residue")

        # 14b. A legacy/hand-edited INVERTED span in the stored file is dropped with a
        #      warning. Left in place it yields overlapping gaps forever (>1440 uncovered
        #      minutes in a 1440-minute day), re-sweeping the same hours indefinitely.
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "tracking_since": "2026-07-24", "covered": {
                "2026-07-24": [["2026-07-24T18:00:00-04:00", "2026-07-24T06:00:00-04:00"]]}}, f)
        inv, warn_inv = load_state()
        check(warn_inv is not None and "non-increasing" in warn_inv,
              "stored inverted span is dropped with a warning")
        check(inv["covered"]["2026-07-24"] == [], "inverted span removed from coverage")
        pinv = plan(inv, now)
        mins = pinv["days_to_sweep"][0]["uncovered_minutes"]
        check(mins <= 1440, "no overlapping gaps after sanitising (%d min <= 1440)" % mins)
    finally:
        for p in (STATE_PATH, STATE_PATH + ".tmp"):
            if os.path.exists(p):
                os.remove(p)
        STATE_PATH = real_path

    # 15. DST: the spring-forward day (2026-03-08, 23h) round-trips with zero residue.
    dst_now = parse_dt("2026-03-08T18:00:00-05:00")
    s15 = st_with({}, since="2026-03-08")
    p15 = plan(s15, dst_now)
    g = p15["days_to_sweep"][0]["gaps"][0]
    s15 = commit(s15, "2026-03-08", g[0], g[1])
    check(not plan(s15, dst_now)["days_to_sweep"], "DST spring-forward day leaves no residual gap")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# ---------- cli ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--now")
    ap.add_argument("--date")
    ap.add_argument("--from", dest="frm")
    ap.add_argument("--to")
    ap.add_argument("--lookback", type=int, default=LOOKBACK_DAYS)
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    if a.plan and a.commit:
        # Silently honouring only one of them is how a caller ends up believing a gap was
        # committed when it was not.
        print("--plan and --commit are separate steps; pass exactly one", file=sys.stderr)
        return 1

    st, state_warning = load_state()
    if state_warning:
        print("WARNING: " + state_warning, file=sys.stderr)

    if a.plan:
        now = parse_dt(a.now) if a.now else datetime.now(ET)
        result = plan(st, now, a.lookback)
        if state_warning:
            result["state_warning"] = state_warning
        print("RESULT_JSON=" + json.dumps(result))
        return 0

    if a.commit:
        if not (a.date and a.frm and a.to):
            print("--commit requires --date --from --to", file=sys.stderr)
            return 1
        try:
            st = commit(st, a.date, a.frm, a.to)
        except ValueError as e:
            print("refusing commit: %s" % e, file=sys.stderr)
            return 1
        save_state(st, now=parse_dt(a.now) if a.now else None)
        print("COMMITTED %s %s -> %s" % (a.date, a.frm, a.to))
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
