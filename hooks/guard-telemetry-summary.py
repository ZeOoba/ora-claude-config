#!/usr/bin/env python3
"""Read-only summary of hooks/_state/guard-telemetry.jsonl (+ its .1 rotation).

Per (chain, guard): fires, blocks (exit_code == 2), other non-zero exits,
subprocess-fallback and fail-open counts, and p50 / p95 / max wall-clock ms.
This is the instrument for the question the dispatchers could not answer
before 2026-09-30: which guard actually costs the latency, which one actually
blocks, and which one is silently degrading to the subprocess path.

    python hooks/guard-telemetry-summary.py [--hours N] [--path FILE] [--json]

READ-ONLY: never writes, rotates or truncates the log. Malformed lines are
counted and skipped, never fatal. The log itself carries no payload content
(see hooks/lib/guard_telemetry.py's confidentiality contract), so neither does
this report.

Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import math
import os
import sys
import time

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))

try:
    import guard_telemetry as _telemetry  # noqa: E402
    DEFAULT_PATH = _telemetry.log_path()
except Exception:  # noqa: BLE001
    DEFAULT_PATH = os.path.join(HOOKS_DIR, "_state", "guard-telemetry.jsonl")


def percentile(sorted_values, pct):
    """Nearest-rank percentile over an already-sorted list; None if empty."""
    if not sorted_values:
        return None
    rank = max(1, int(math.ceil(pct / 100.0 * len(sorted_values))))
    return sorted_values[min(rank, len(sorted_values)) - 1]


def read_records(path, since_ts=None):
    """(records, malformed_count) across `path.1` (older) then `path`."""
    records, bad = [], 0
    for p in (path + ".1", path):
        try:
            fh = open(p, "r", encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    bad += 1
                    continue
                if not isinstance(rec, dict):
                    bad += 1
                    continue
                if since_ts is not None:
                    try:
                        if float(rec.get("ts", 0)) < since_ts:
                            continue
                    except (TypeError, ValueError):
                        bad += 1
                        continue
                records.append(rec)
    return records, bad


def summarize(records):
    """{(chain, guard): stats-dict}, stable-sorted by chain then guard."""
    groups = {}
    for rec in records:
        key = (str(rec.get("chain", "?")), str(rec.get("guard", "?")))
        g = groups.setdefault(key, {"fires": 0, "blocks": 0, "other_nonzero": 0,
                                    "subprocess": 0, "failopen": 0,
                                    "failclosed": 0, "skipped": 0, "_ms": []})
        g["fires"] += 1
        rc = rec.get("exit_code")
        if rc == 2:
            g["blocks"] += 1
        elif rc not in (0, None):
            g["other_nonzero"] += 1
        path_taken = rec.get("path_taken")
        if path_taken in ("subprocess", "failopen", "failclosed", "skipped"):
            g[path_taken] += 1
        try:
            g["_ms"].append(float(rec.get("ms")))
        except (TypeError, ValueError):
            pass
    out = {}
    for key in sorted(groups):
        g = groups[key]
        ms = sorted(g.pop("_ms"))
        g["p50_ms"] = percentile(ms, 50)
        g["p95_ms"] = percentile(ms, 95)
        g["max_ms"] = ms[-1] if ms else None
        out[key] = g
    return out


def _fmt(v):
    return "-" if v is None else ("%.1f" % v)


def render(summary, bad, path):
    lines = ["guard telemetry: %s" % path]
    if not summary:
        lines.append("  (no records)")
    else:
        lines.append("  %-10s %-26s %7s %6s %5s %5s %5s %8s %8s %8s" % (
            "chain", "guard", "fires", "blocks", "subp", "fopen", "skip",
            "p50ms", "p95ms", "maxms"))
        for (chain, guard), g in summary.items():
            lines.append("  %-10s %-26s %7d %6d %5d %5d %5d %8s %8s %8s" % (
                chain[:10], guard[:26], g["fires"], g["blocks"], g["subprocess"],
                g["failopen"] + g["failclosed"], g["skipped"],
                _fmt(g["p50_ms"]), _fmt(g["p95_ms"]), _fmt(g["max_ms"])))
    if bad:
        lines.append("  (%d malformed line(s) skipped)" % bad)
    return "\n".join(lines)


def main(argv):
    path = DEFAULT_PATH
    since = None
    as_json = "--json" in argv
    if "--path" in argv:
        i = argv.index("--path")
        if i + 1 >= len(argv):
            sys.stderr.write("usage: --path FILE\n")
            return 2
        path = argv[i + 1]
    if "--hours" in argv:
        i = argv.index("--hours")
        try:
            since = time.time() - float(argv[i + 1]) * 3600.0
        except (IndexError, ValueError):
            sys.stderr.write("usage: --hours N\n")
            return 2
    records, bad = read_records(path, since)
    summary = summarize(records)
    if as_json:
        print(json.dumps({"path": path, "malformed": bad, "groups": [
            dict(chain=k[0], guard=k[1], **v) for k, v in summary.items()]},
            indent=2, sort_keys=True))
    else:
        print(render(summary, bad, path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
