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
(fail loud, not silent).
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
    """Read the snapshot JSON file. Returns {} if missing or unparseable -- never
    raises; the CLI decides what "fail loud" means for its own inputs, not this
    internal state file."""
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
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
