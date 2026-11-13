#!/usr/bin/env python3
"""RCT leak check: block a push that re-adds the ratified replacement-cost (RCT) figures.

WHY (2026-11-13). Gabriel's 2026-11-12 six-repo audit found the ratified RCT table -- a
governor-level input used to score acquisitions -- readable in this PUBLIC repo
(ZeOoba/ora-claude-config). He kept the repo public (2026-11-09 ruling) and moved the table
out of source: the scheduled tasks now read it at run time from a private file. This check is
what stops the figures from coming back, through a task spec, a memory note, an archive copy or
a commit message.

WHAT IT COMPARES AGAINST. Never anything in this repo. The needles are built at push time from
two optional files that live OUTSIDE the tracked tree:
  * the private RCT table   -- $ORA_RCT_TABLE_PATH, else ~/.ora-private/rct/replacement-cost.json
                                (same schema as oxford-command-center's replacement-cost.v3.json
                                plus a `vintageFloor` {oldYear, oldPct, newYear, newPct} block)
  * an extra local denylist -- $ORA_RCT_LEAK_DENYLIST, else ~/.ora-private/rct/leak-denylist.json
                                {"values": [numbers], "strings": [literal strings]} -- for
                                superseded table versions still worth guarding
Needles: every numeric value >= 10 in the table (underscore keys skipped, booleans skipped),
formatted to two decimals (plus the one-decimal form when it ends in 0), and, when the table has
a `vintageFloor`, the per-vintage basis floor LOW x (1 - floor%) for every year on the ramp. Never
publish a hash of any of these: a hash of a value that is already in public history confirms it.

FAIL MODES.
  * Neither file exists (CI, a fresh clone, another machine) -> load_needles() returns None and
    the caller SKIPS this check, announcing it on stderr. Deliberate (task brief 2026-11-13):
    the figures cannot be checked where they are not known, and CI must not need them.
  * A file EXISTS but cannot be read, parsed, or yields no values -> RctSourceError; the caller
    BLOCKS. A present-but-broken source is a broken guard, not an absent one.

WHAT COUNTS AS A LEAK. Only ADDED content: '+' lines of `git log -p --cc` (combined-diff
prefixes included) and commit-message lines. Removed lines are the fix, not the leak, so the
push that deletes the figures passes. Reports carry file paths only, never a figure.

RESIDUAL (stated, not hidden): figures re-typed in another form ("$222", "222.2", words) are not
caught; compressed / UTF-16 blobs are not decoded by this check (the confidential scan's
compressed walk covers roster terms and credentials only); history already on the remote is not
rescanned. Stdlib only. ASCII-only.
"""
import json
import os
import re

DEFAULT_TABLE = os.path.join("~", ".ora-private", "rct", "replacement-cost.json")
DEFAULT_DENYLIST = os.path.join("~", ".ora-private", "rct", "leak-denylist.json")
MIN_VALUE = 10.0


class RctSourceError(Exception):
    """A private RCT source exists but cannot be used. The caller must block."""


def _path(explicit, env_name, default):
    if explicit:
        return explicit
    return os.path.expanduser(os.environ.get(env_name) or default)


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # unreadable, a directory, bad JSON ...
        raise RctSourceError("%s: %s" % (os.path.basename(path), type(e).__name__))


def _numbers(obj, out):
    """Every numeric leaf of obj, skipping keys that start with '_' and booleans."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and k.startswith("_"):
                continue
            _numbers(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _numbers(v, out)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out.append(float(obj))


def _ramp(vf):
    """[floor fraction] for each year on the vintage ramp, or [] when absent/invalid."""
    try:
        y0, p0 = int(vf["oldYear"]), float(vf["oldPct"])
        y1, p1 = int(vf["newYear"]), float(vf["newPct"])
    except Exception:
        return []
    if y1 <= y0:
        return [p0, p1]
    return [p0 + (p1 - p0) * (y - y0) / float(y1 - y0) for y in range(y0, y1 + 1)]


def _fmt(v):
    s = "%.2f" % v
    out = {s}
    if s.endswith("0"):
        out.add(s[:-1])
    return out


def load_needles(table_path=None, denylist_path=None):
    """(needles, sources). needles is None when NO private source exists on this machine
    (caller skips). Raises RctSourceError when a source exists but is unusable (caller blocks)."""
    table_path = _path(table_path, "ORA_RCT_TABLE_PATH", DEFAULT_TABLE)
    denylist_path = _path(denylist_path, "ORA_RCT_LEAK_DENYLIST", DEFAULT_DENYLIST)
    sources, values, strings, ramp = [], [], [], []
    if os.path.lexists(table_path):
        table = _read(table_path)
        if not isinstance(table, dict):
            raise RctSourceError("%s: not a JSON object" % os.path.basename(table_path))
        vf = table.get("vintageFloor")
        ramp = _ramp(vf) if isinstance(vf, dict) else []
        found = []
        _numbers({k: v for k, v in table.items() if k != "vintageFloor"}, found)
        found = [v for v in found if v >= MIN_VALUE]
        if not found:
            raise RctSourceError("%s: no RCT values found" % os.path.basename(table_path))
        values.extend(found)
        sources.append(table_path)
    if os.path.lexists(denylist_path):
        deny = _read(denylist_path)
        if not isinstance(deny, dict):
            raise RctSourceError("%s: not a JSON object" % os.path.basename(denylist_path))
        found = []
        _numbers(deny.get("values", []), found)
        found = [v for v in found if v >= MIN_VALUE]
        lits = [s for s in deny.get("strings", []) if isinstance(s, str) and s.strip()]
        if not found and not lits:
            raise RctSourceError("%s: no values or strings" % os.path.basename(denylist_path))
        values.extend(found)
        strings.extend(lits)
        sources.append(denylist_path)
    if not sources:
        return None, []
    needles = set(strings)
    for v in values:
        needles |= _fmt(v)
        for pct in ramp:
            floor = round(v * (1.0 - pct) + 1e-9, 2)
            if floor >= MIN_VALUE:
                needles |= _fmt(floor)
    return sorted(needles), sources


def _matcher(needles):
    nums = [n for n in needles if re.fullmatch(r"\d+\.\d+", n)]
    lits = [n for n in needles if n not in nums]
    rx = None
    if nums:
        rx = re.compile(r"(?<![\d.])(?:%s)(?!\d)"
                        % "|".join(re.escape(n) for n in sorted(nums, key=len, reverse=True)))
    return rx, lits


def text_hits(text, needles, _m=None):
    """True if text carries any needle (number-bounded match; literals as substrings)."""
    rx, lits = _m or _matcher(needles)
    if rx is not None and rx.search(text):
        return True
    return any(s in text for s in lits)


def scan_diff(body, needles):
    """Sorted paths (and '<commit message xxxxxxxx>' markers) whose ADDED content in a
    `git log -p --cc` body carries a needle. Never returns the needle itself."""
    m = _matcher(needles)
    hits = set()
    commit, path, width, in_msg = None, None, 0, False
    for line in body.splitlines():
        if line.startswith("commit ") and re.fullmatch(r"commit [0-9a-f]{40}.*", line):
            commit, path, width, in_msg = line.split()[1], None, 0, True
            continue
        if line.startswith("diff --git "):
            path, width, in_msg = line.rsplit(" b/", 1)[-1], 0, False
            continue
        if line.startswith("diff --cc ") or line.startswith("diff --combined "):
            path, width, in_msg = line.split(" ", 2)[2], 0, False
            continue
        if in_msg:
            if line.startswith("    ") and commit and text_hits(line, needles, m):
                hits.add("<commit message %s>" % commit[:8])
            continue
        if line.startswith("@@"):
            width = max(1, len(line) - len(line.lstrip("@")) - 1)
            continue
        if not width or path is None:
            continue  # file header lines (---/+++/index/mode) before the first hunk
        prefix = line[:width]
        if "+" in prefix and "-" not in prefix and text_hits(line[width:], needles, m):
            hits.add(path)
    return sorted(hits)
