#!/usr/bin/env python3
"""ORA deal-stage reconciler.

Diffs live Notion Acquisition Pipeline Tracker Stage values (supplied by the caller as
already-fetched JSON -- this module never calls Notion, subprocess, or the network
itself) against a rolling local snapshot, and formats event_log.md entries +
deal-decision-ledger.md rows for anything that changed. Writing those files is the
calling agent's job (append-event-log.py for event_log.md, an Edit-tool append for
deal-decision-ledger.md) -- this module only owns its own snapshot file.

See: docs/superpowers/specs/2026-07-09-cross-fleet-deal-stage-reconciliation-design.md

Usage:
  python deal-stage-reconciler.py --current-file <path.json> --stage-map-file <path.json> \\
      [--snapshot-file <path>] [--bootstrap] [--date YYYY-MM-DD]

--current-file / --stage-map-file are always files, never stdin -- Windows cp1252 stdin
decoding mangles UTF-8 em-dashes/arrows (see feedback_append_event_log_stdin_encoding.md).
Exit 0 = ran fine (transitions may be zero). Exit 2 = could not read an input file
(fail loud, not silent). Exit 3 = refused: a snapshot row is absent from --current-file
(apparent partial fetch; --allow-shrink accepts a deliberate removal). Exit 4 = refused: the
snapshot is missing, unreadable or not a JSON object (re-seed with --bootstrap). Exits 3/4
write nothing and emit no transitions.
"""
import argparse
import datetime as dt
import json
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_SNAPSHOT = os.path.join(os.path.expanduser("~"), ".claude", "maintenance",
                                 "_state", "deal-stage-snapshot.json")

DISPOSITION_TOKENS = {"PASS", "SKIP", "DROP", "PARK", "CLOSE", "TERMINATE"}


def load_snapshot(path):
    """Read the snapshot JSON file. Returns None if missing, unreadable or not a JSON
    object -- never raises. None is NOT an empty baseline (2026-11-08 audit
    deal-stage-reconciler-empty-snapshot-fail-open): treating it as {} made every live
    row a first-seen "transition", i.e. mass false event_log entries and ledger rows,
    and the shrink guard (then count-only) could not catch it. main() refuses (exit 4)
    unless --bootstrap re-seeds deliberately."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def save_snapshot(path, current):
    """Atomically write `current` ({page_id: {"deal":..., "stage":...}}) to `path`."""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp-write"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2, sort_keys=True, ensure_ascii=False)
    os.replace(tmp, path)


def diff_stages(current, snapshot):
    """Compare current live Notion state against the last-seen snapshot.
    current / snapshot: {page_id: {"deal": str, "stage": str}}.
    Returns a list of transition dicts, one per page_id whose stage differs from (or is
    absent from) the snapshot: {"page_id", "deal", "old_stage", "new_stage"}.
    old_stage is None for a page_id not present in the snapshot (first time seen).
    A page_id present in the snapshot but missing from current (e.g. archived in
    Notion) is NOT reported -- disappearance is not a stage change."""
    transitions = []
    for page_id, info in current.items():
        deal = info.get("deal", "")
        new_stage = info.get("stage", "")
        prior = snapshot.get(page_id)
        old_stage = prior.get("stage") if prior else None
        if old_stage != new_stage:
            transitions.append({
                "page_id": page_id,
                "deal": deal,
                "old_stage": old_stage,
                "new_stage": new_stage,
            })
    return transitions


def classify_disposition(new_stage, stage_map):
    """Map a live Notion Stage string to a terminal-disposition token using `stage_map`
    ({notion_stage_string: disposition_token}). Returns the token only if `new_stage` is
    a key in `stage_map` AND the mapped value is a real DISPOSITION_TOKENS member;
    otherwise None -- never guesses. None means "log to event_log only, no ledger row"."""
    token = stage_map.get(new_stage)
    if token in DISPOSITION_TOKENS:
        return token
    return None


def format_event_log_entry(transition, date):
    """Render the dated event_log.md entry body for one transition. `date` is a
    'YYYY-MM-DD' string supplied by the caller -- never computed inside this pure
    function (no datetime.today() here, so it stays trivially testable)."""
    deal = transition["deal"]
    old = transition["old_stage"] if transition["old_stage"] is not None else "(none)"
    new = transition["new_stage"]
    return (
        "## %s — Deal-stage sync: %s — %s → %s (Notion)\n\n"
        "Detected by ora-open-sessions-board's reconciliation step; no corresponding "
        "entry existed. Tripwire only — see Notion for the actual decision context."
        % (date, deal, old, new)
    )


def format_ledger_row(transition, disposition, date, reason=None):
    """Render one deal-decision-ledger.md markdown table row: | Date | Deal | Verdict |
    One-line reason | Buy-box rule validated / refined |. `reason` is the one-line
    rationale if known; when None, uses the standing fallback rather than fabricating
    one."""
    if reason is None:
        reason = ("Notion Stage → %s; reason not logged elsewhere — "
                   "reconcile manually" % transition["new_stage"])
    return "| %s | %s | %s | %s | — |" % (date, transition["deal"], disposition,
                                                 reason)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Deal-stage reconciler: diff live Notion stage values against the "
                     "last snapshot.")
    ap.add_argument("--current-file", required=True,
                     help="JSON file: {page_id: {\"deal\":..., \"stage\":...}} (live "
                          "Notion state, written by the caller -- never stdin, see "
                          "feedback_append_event_log_stdin_encoding.md)")
    ap.add_argument("--stage-map-file", required=True,
                     help="JSON file: {notion_stage_string: disposition_token}")
    ap.add_argument("--snapshot-file", default=DEFAULT_SNAPSHOT,
                     help="path to the rolling snapshot (default: canonical _state path)")
    ap.add_argument("--bootstrap", action="store_true",
                     help="seed the snapshot from --current-file with ZERO diff output "
                          "(first-run only -- never logs pre-existing state as a change)")
    ap.add_argument("--allow-shrink", action="store_true",
                     help="accept snapshot rows that are absent from --current-file "
                          "(a deliberate Notion delete/archive); without it such a run is "
                          "refused (exit 3) as an apparent partial fetch")
    ap.add_argument("--date", default=None,
                     help="YYYY-MM-DD to stamp entries with (default: today)")
    a = ap.parse_args(argv)

    try:
        with open(a.current_file, encoding="utf-8") as f:
            current = json.load(f)
    except (OSError, ValueError) as e:
        sys.stderr.write("cannot read --current-file: %s\n" % e)
        return 2
    if not isinstance(current, dict):
        sys.stderr.write("--current-file must contain a JSON object\n")
        return 2

    if a.bootstrap:
        save_snapshot(a.snapshot_file, current)
        print(json.dumps({"bootstrap": True, "count": len(current)}))
        return 0

    try:
        with open(a.stage_map_file, encoding="utf-8") as f:
            stage_map = json.load(f)
    except (OSError, ValueError) as e:
        sys.stderr.write("cannot read --stage-map-file: %s\n" % e)
        return 2
    if not isinstance(stage_map, dict):
        sys.stderr.write("--stage-map-file must contain a JSON object\n")
        return 2

    date = a.date or dt.date.today().isoformat()
    snapshot = load_snapshot(a.snapshot_file)
    if snapshot is None:
        sys.stderr.write(
            "snapshot %s is missing, unreadable or not a JSON object -- refusing to diff "
            "against an empty baseline (every row would read as a new transition). Re-seed "
            "deliberately with --bootstrap.\n" % a.snapshot_file)
        return 4
    # KEY-SET guard, not a count guard: a partial fetch padded by new rows (or a page-id
    # format change) keeps the count while dropping real rows.
    dropped = set(snapshot) - set(current)
    if dropped and not a.allow_shrink:
        sys.stderr.write(
            "current-file is missing %d snapshot row(s) (current has %d rows, the snapshot "
            "has %d; fewer rows or swapped keys) -- refusing to overwrite (possible partial "
            "Notion fetch). Pass --allow-shrink if the rows were deliberately removed.\n"
            % (len(dropped), len(current), len(snapshot)))
        return 3
    transitions = diff_stages(current, snapshot)
    out = []
    for t in transitions:
        disposition = classify_disposition(t["new_stage"], stage_map)
        out.append({
            "page_id": t["page_id"],
            "deal": t["deal"],
            "old_stage": t["old_stage"],
            "new_stage": t["new_stage"],
            "disposition": disposition,
            "event_log_entry": format_event_log_entry(t, date),
            "ledger_row": (format_ledger_row(t, disposition, date)
                            if disposition else None),
        })
    save_snapshot(a.snapshot_file, current)
    print(json.dumps({"transitions": out, "count": len(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
