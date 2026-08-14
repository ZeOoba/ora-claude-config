#!/usr/bin/env python3
"""ORA override-token frequency probe (OI-136).

WHY: override tokens (allow-hook-test-failure, allow-config-write, etc.) are legitimate,
in-turn-authorized, and audited one-by-one -- but nothing tracks how OFTEN a given tier
gets minted. OI-136 (2026-08-12) found `allow-hook-test-failure` used 5 times across 4
sessions inside a 47-minute window, all citing the same known flake (a load-induced
exit-124 timeout on test-eos-review-gate.py that passes in isolation -- see OI-057/OI-059
in open-items-tracker.md). No protocol was broken: every token recorded explicit
authorization. The finding was that a gate which false-blocks under load makes overriding
the rational move, and repetition trains the reflex to approve without weighing it -- so
the next GENUINE failure inherits that reflex.

This probe does NOT gate anything and must NEVER be used to tighten
hooks/git-prepush-hook-tests-gate.py or any override tier's TTL/scope. It is read-only
telemetry: a rate/repeat signal for a human to notice, exactly what OI-136 asked for
("needs a rate/repeat signal, not a stricter gate").

Sources, most durable first (a token can appear in more than one; deduped by
session_id+name, preferring the source with a real mtime):
  1. hooks/sessions/_archive_override_tokens/<sid>_overrides_<name> file mtimes -- the
     archived token content; mtime survives the sweep's move/rename.
  2. maintenance/override-token-sweep.log ARCHIVED lines (gitignored, append-only) --
     fallback when the archived file itself is gone; timestamp here is sweep time, not
     mint time, so it is only used to fill gaps source 1 cannot answer.
  3. hooks/sessions/<sid>/overrides/<name> -- live, not-yet-swept tokens.

Exit 0 = no signal. Exit 1 = signal: some override NAME was used >=5 times within a
trailing 7-day window (the exact shape that flagged OI-136 -- generalized to any tier,
not hardcoded to allow-hook-test-failure, since the same "gate false-blocks -> override
becomes routine" failure mode could recur on a different tier). Exit 2 = probe error
(fail loud, not silent -- I5).

Usage: python override-token-frequency-probe.py            # human-readable report
       python override-token-frequency-probe.py --json      # machine-readable
       python override-token-frequency-probe.py --days 14   # widen the trailing window
       python override-token-frequency-probe.py --threshold 5  # override the signal count

Stdlib only. ASCII-only. Windows (`python`).
"""
import datetime
import json
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
SESSIONS_DIR = os.path.join(CLAUDE, "hooks", "sessions")
ARCHIVE_DIR = os.path.join(SESSIONS_DIR, "_archive_override_tokens")
SWEEP_LOG = os.path.join(CLAUDE, "maintenance", "override-token-sweep.log")

DEFAULT_WINDOW_DAYS = 7
DEFAULT_SIGNAL_THRESHOLD = 5  # the exact count that flagged OI-136

# "2026-08-10T12:31:29 ARCHIVED <src> -> <dst>" -- LIVE sweep summary lines are skipped.
SWEEP_LOG_LINE_RE = re.compile(r"^(\S+)\s+ARCHIVED\s+(.+?)\s+->\s+(.+)$")


def _split_archive_name(basename):
    """('<sid>', '<name>') from an archive-dir basename, or (None, None) if it is the
    legacy flat '<sid>_override' form (no tier name -- cannot attribute, skipped)."""
    marker = "_overrides_"
    idx = basename.find(marker)
    if idx == -1:
        return None, None
    return basename[:idx], basename[idx + len(marker):]


def _events_from_archive_dir():
    """(session_id, name, mtime) for every archived token still on disk."""
    events = []
    try:
        entries = os.listdir(ARCHIVE_DIR)
    except OSError:
        return events
    for basename in entries:
        sid, name = _split_archive_name(basename)
        if not sid or not name:
            continue
        path = os.path.join(ARCHIVE_DIR, basename)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        events.append((sid, name, mtime))
    return events


def _events_from_sweep_log():
    """(session_id, name, sweep_timestamp) for every ARCHIVED line naming a tier.

    sweep_timestamp is when the sweep MOVED the token, not when it was minted -- used
    only to fill in entries whose archived file source 1 can no longer find (e.g. a
    prior manual cleanup), so a small skew here does not matter for a 7-day signal.
    """
    events = []
    try:
        with open(SWEEP_LOG, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return events
    for line in lines:
        m = SWEEP_LOG_LINE_RE.match(line.strip())
        if not m:
            continue
        ts_str, _src, dst = m.groups()
        # dst is the sweep's flattened archive filename ("<sid>_overrides_<name>"), same
        # shape _split_archive_name expects -- src is the pre-sweep directory path
        # ("sessions/<sid>/overrides/<name>") and is not usable here.
        basename = os.path.basename(dst.replace("\\", "/"))
        sid, name = _split_archive_name(basename)
        if not sid or not name:
            continue
        try:
            ts = datetime.datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S").timestamp()
        except ValueError:
            continue
        events.append((sid, name, ts))
    return events


def _events_from_live_sessions():
    """(session_id, name, mtime) for tokens not yet swept into the archive."""
    events = []
    try:
        session_ids = os.listdir(SESSIONS_DIR)
    except OSError:
        return events
    for sid in session_ids:
        overrides_dir = os.path.join(SESSIONS_DIR, sid, "overrides")
        try:
            names = os.listdir(overrides_dir)
        except OSError:
            continue
        for name in names:
            path = os.path.join(overrides_dir, name)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            events.append((sid, name, mtime))
    return events


def collect_events():
    """De-duplicated (session_id, name, timestamp) triples from all three sources.

    Dedup key is (session_id, name) only -- one token grant, however observed, counts
    once. Source 1 (archive-dir mtime) wins when both it and source 2 (sweep log) see
    the same key, since mtime approximates mint time and the log only records sweep
    time. Source 3 (live) keys are disjoint from 1/2 by construction (a token is either
    swept or not), so it never overwrites either.
    """
    by_key = {}
    for sid, name, ts in _events_from_sweep_log():
        by_key[(sid, name)] = ts
    for sid, name, ts in _events_from_archive_dir():
        by_key[(sid, name)] = ts  # archive-dir mtime overrides the log's sweep time
    for sid, name, ts in _events_from_live_sessions():
        by_key.setdefault((sid, name), ts)
    return [(sid, name, ts) for (sid, name), ts in by_key.items()]


def build_report(window_days, threshold, now=None):
    now = now if now is not None else datetime.datetime.now().timestamp()
    window_start = now - window_days * 86400.0
    prior_start = now - 2 * window_days * 86400.0

    events = collect_events()
    by_name = {}
    for sid, name, ts in events:
        by_name.setdefault(name, []).append((sid, ts))

    per_name = {}
    signals = []
    for name, occurrences in sorted(by_name.items()):
        in_window = [(sid, ts) for sid, ts in occurrences if window_start <= ts < now]
        in_prior = [(sid, ts) for sid, ts in occurrences if prior_start <= ts < window_start]
        sessions_in_window = sorted(set(sid for sid, _ts in in_window))
        entry = {
            "name": name,
            "count_trailing_window": len(in_window),
            "count_prior_window": len(in_prior),
            "distinct_sessions_trailing_window": len(sessions_in_window),
        }
        per_name[name] = entry
        if len(in_window) >= threshold:
            signals.append(entry)

    return {
        "window_days": window_days,
        "threshold": threshold,
        "generated_at": datetime.datetime.fromtimestamp(now).isoformat(),
        "per_name": per_name,
        "signals": signals,
    }


def format_human(report):
    lines = []
    lines.append(
        "Override-token frequency (trailing %dd vs prior %dd, signal >= %d in a window):"
        % (report["window_days"], report["window_days"], report["threshold"])
    )
    if not report["per_name"]:
        lines.append("  (no override-token activity found in any source)")
        return "\n".join(lines)
    for name, entry in sorted(report["per_name"].items()):
        flag = "  <-- SIGNAL" if entry in report["signals"] else ""
        lines.append(
            "  %-32s %d uses (%d sessions) this window, %d prior%s"
            % (
                name,
                entry["count_trailing_window"],
                entry["distinct_sessions_trailing_window"],
                entry["count_prior_window"],
                flag,
            )
        )
    if report["signals"]:
        lines.append("")
        lines.append(
            "SIGNAL: %d override tier(s) hit the repeat threshold. This is telemetry, "
            "not a gate -- it does not block anything. Read OI-136 in "
            "open-items-tracker.md before deciding whether to act."
            % len(report["signals"])
        )
    return "\n".join(lines)


def main():
    argv = sys.argv[1:]
    as_json = "--json" in argv
    window_days = DEFAULT_WINDOW_DAYS
    threshold = DEFAULT_SIGNAL_THRESHOLD
    for i, arg in enumerate(argv):
        if arg == "--days" and i + 1 < len(argv):
            window_days = int(argv[i + 1])
        if arg == "--threshold" and i + 1 < len(argv):
            threshold = int(argv[i + 1])

    report = build_report(window_days, threshold)

    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_human(report))

    return 1 if report["signals"] else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail loud, not silent -- I5
        sys.stderr.write("override-token-frequency-probe.py ERROR: %r\n" % (exc,))
        sys.exit(2)
