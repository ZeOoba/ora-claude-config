#!/usr/bin/env python3
"""Snapshot guards shared by ora-cc-snapshot-refresh and ora-lease-snapshot-refresh.

Since oxford-command-center PR #565 (2026-11-12), data/snapshots/portfolio.json is
gitignored: the refresh writes it in place in the live checkout and never commits it.
The guards therefore compare the freshly written snapshot against the PREVIOUS live
snapshot (a copy taken just before the refresh), not against git HEAD.

Usage:  python snapshot-guard.py <previous.json> <current.json>

Prints, in this order, and always exits 0 when it could read both files:
  suppressed as write-clock: <paths>     (only when any were stripped)
  MATERIAL: yes|none
    <added|removed|changed> <path>       (only on yes; at most 40, then a count)
  ok     <key>: <prev> -> <cur>          (one per list section)
  SHRINK <key>: ...                      (one per shrunk section, list or non-list)
  VERDICT: clean|shrink
Exits 2 (and prints no VERDICT) when either file is missing, not valid JSON, not a JSON
object, or holds a list section that is not a list. Any other exit code, or no VERDICT
line at all, is equally a guard-condition failure, never a pass.

Logic is carried over from the specs' inline blocks (material-change gate v1.4
2026-08-27; list + generic non-list shrink guard 2026-08-24), with HEAD replaced by the
previous live snapshot. Two deliberate differences: the old gate's +/- git-diff lines are
replaced by the changed-path list above (there is no git diff of an untracked file), and a
malformed list section is an explicit error rather than a crash. Known residuals are
unchanged and disclosed:
  - a genuine business timestamp ending in 'At' is stripped as a write-clock, but every
    stripped path is printed;
  - the generic shrink check sees only a top-level section going populated -> empty/null,
    not a nested list shrinking inside a still-populated section.
"""
import json
import re
import sys

ISO = re.compile(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}')
LIST_KEYS = ('leases', 'deals', 'counterparties', 'properties', 'loans')
# meta: generatedAt always differs; dataQuality: fewer flags is an improvement.
SKIP = set(LIST_KEYS) | {'meta', 'dataQuality'}


def strip_clocks(o, stripped, path=''):
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            if isinstance(k, str) and k.endswith('At') and isinstance(v, str) and ISO.match(v):
                stripped.add((path + '.' + k).lstrip('.'))
                continue
            out[k] = strip_clocks(v, stripped, path + '.' + k)
        return out
    if isinstance(o, list):
        return [strip_clocks(x, stripped, path + '[' + str(i) + ']') for i, x in enumerate(o)]
    return o


def is_empty(v):
    if v is None:
        return True
    if isinstance(v, (list, dict, str)):
        return len(v) == 0
    return False


CHANGED_CAP = 40


def changed_paths(a, b, path=''):
    """Paths where two clock-stripped trees differ (the old gate printed +/- diff lines;
    the snapshot is untracked now, so this is what tells a human what moved)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b), key=str):
            p = (path + '.' + str(k)).lstrip('.')
            if k not in a:
                out.append('added ' + p)
            elif k not in b:
                out.append('removed ' + p)
            else:
                out.extend(changed_paths(a[k], b[k], p))
        return out
    if isinstance(a, list) and isinstance(b, list):
        out = []
        for i in range(max(len(a), len(b))):
            p = path + '[' + str(i) + ']'
            if i >= len(a):
                out.append('added ' + p)
            elif i >= len(b):
                out.append('removed ' + p)
            else:
                out.extend(changed_paths(a[i], b[i], p))
        return out
    return [] if a == b else ['changed ' + (path or '<root>')]


def section_len(doc, k):
    """Strict, like the old `len(head.get(k, []))`: an absent key counts as empty, but a
    present non-list value (None, a number, a dict) is a malformed snapshot -> raise, so the
    CLI prints no verdict (fails closed) instead of reading it as an empty section."""
    v = doc.get(k, [])
    if not isinstance(v, list):
        raise ValueError(f'section {k!r} is {type(v).__name__}, not a list')
    return len(v)


def evaluate(prev, cur):
    """Return (lines, material, shrunk). Raises ValueError on a malformed list section."""
    lines = []
    stripped = set()
    sp, sc = strip_clocks(prev, stripped), strip_clocks(cur, stripped)
    material = sp != sc
    if stripped:
        lines.append('suppressed as write-clock: ' + ', '.join(sorted(stripped)))
    lines.append('MATERIAL: ' + ('yes' if material else 'none'))
    if material:
        diffs = changed_paths(sp, sc)
        for d in diffs[:CHANGED_CAP]:
            lines.append('  ' + d)
        if len(diffs) > CHANGED_CAP:
            lines.append(f'  ... and {len(diffs) - CHANGED_CAP} more changed paths')
    shrunk = False
    for k in LIST_KEYS:
        h, w = section_len(prev, k), section_len(cur, k)
        if w < h:
            shrunk = True
        lines.append(('SHRINK ' if w < h else 'ok     ') + f'{k}: {h} -> {w}')
    for k in sorted(set(prev) | set(cur)):
        if k in SKIP:
            continue
        if not is_empty(prev.get(k)) and is_empty(cur.get(k)):
            shrunk = True
            lines.append(f'SHRINK {k}: populated -> empty/null')
    return lines, material, shrunk


def main(argv):
    if len(argv) != 3:
        print('usage: snapshot-guard.py <previous.json> <current.json>', file=sys.stderr)
        return 2
    try:
        with open(argv[1], encoding='utf-8') as f:
            prev = json.load(f)
        with open(argv[2], encoding='utf-8') as f:
            cur = json.load(f)
    except (OSError, ValueError) as e:
        print(f'GUARD ERROR: {e}', file=sys.stderr)
        return 2
    if not isinstance(prev, dict) or not isinstance(cur, dict):
        print('GUARD ERROR: snapshot is not a JSON object', file=sys.stderr)
        return 2
    try:
        lines, _material, shrunk = evaluate(prev, cur)
    except Exception as e:  # any failure -> no verdict (fails closed)
        print(f'GUARD ERROR: {type(e).__name__}: {e}', file=sys.stderr)
        return 2
    for ln in lines:
        print(ln)
    print('VERDICT: ' + ('shrink' if shrunk else 'clean'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
