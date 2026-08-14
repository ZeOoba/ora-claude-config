#!/usr/bin/env python3
"""Deterministic, verified upsert into ora-open-sessions-board's answered.json.

WHY (2026-08-14): the 2026-08-12 17:46 ET board run answered 5 items and correctly
logged all 5 decisions to event_log.md (via the concrete append-event-log.py call
STEP 6(a) already names) -- but answered.json was never touched, because STEP 6(a)'s
instruction to "upsert each decided sessionId into answered.json" was prose only, with
no script backing it (unlike the event-log half of the same step, which is a copy-paste
command). 3 of the 5 items resurfaced on 2026-08-14 and had to be re-decided from
scratch. This script makes the answered.json half a deterministic tool call too, and
-- unlike append-event-log.py, which is designed to NEVER fail an append (spool-and-
drain) -- this script is designed to NEVER succeed silently: it reads the file back
after writing and fails loudly if the entries didn't actually land, because a silent
write gap here is exactly the failure mode it exists to close.

Usage:
  python upsert-answered-sessions.py --entries-file path\\to\\entries.json
  python upsert-answered-sessions.py --entries-file entries.json --answered-file custom.json

entries.json shape (same as answered.json itself): a JSON object mapping
sessionId -> {"title": ..., "decidedAt": ISO8601, "decision": ...}. Existing keys are
overwritten (upsert) -- a re-decided session should record the newer decision, matching
existing answered.json precedent (e.g. "Reconfirmed 2026-07-10 ...").

Exit 0 = every entry verified present in the on-disk file after the write.
Exit 1 = bad input (malformed entries-file, missing required field, malformed existing
  answered.json) -- nothing was written.
Exit 2 = write attempted but read-back verification failed (or the file stayed locked
  across all retries) -- the caller MUST treat this as a failure and surface it in the
  run summary, never proceed as if the upsert succeeded.
"""
import argparse
import json
import os
import sys
import time

ANSWERED = os.path.join(os.path.expanduser("~"), ".claude", "scheduled-tasks",
                        "ora-open-sessions-board", "answered.json")

REQUIRED_FIELDS = ("title", "decidedAt", "decision")


def load_json_dict(path):
    """Return the JSON object at `path`, or {} if it doesn't exist yet. Raises
    ValueError on anything else that isn't a clean parse -- a malformed existing
    file must never be silently treated as empty (that would discard history)."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if not content.strip():
        return {}
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError("%s is not valid JSON: %s" % (path, e))
    if not isinstance(data, dict):
        raise ValueError("%s does not contain a JSON object at the top level" % path)
    return data


def validate_entries(entries):
    if not isinstance(entries, dict):
        raise ValueError("entries-file must contain a JSON object mapping sessionId -> record")
    if not entries:
        raise ValueError("entries-file contains no sessionIds to upsert")
    for session_id, rec in entries.items():
        if not isinstance(rec, dict):
            raise ValueError("entry %r is not an object" % session_id)
        missing = [k for k in REQUIRED_FIELDS if k not in rec]
        if missing:
            raise ValueError("entry %r is missing required field(s): %s" % (session_id, ", ".join(missing)))


def write_atomic(path, data):
    tmp = path + ".tmp-upsert"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)  # atomic on the same volume


def verify(path, entries):
    """Re-read `path` from disk and confirm every entry in `entries` landed exactly.
    Returns a list of sessionIds that failed to verify (empty = full success)."""
    try:
        on_disk = load_json_dict(path)
    except ValueError as e:
        return list(entries.keys())  # can't even parse it back -> everything failed
    failed = []
    for session_id, rec in entries.items():
        if on_disk.get(session_id) != rec:
            failed.append(session_id)
    return failed


def main(argv=None):
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="Upsert decided sessionIds into answered.json, verified.")
    ap.add_argument("--entries-file", required=True, help="JSON file: {sessionId: {title, decidedAt, decision}, ...}")
    ap.add_argument("--answered-file", default=ANSWERED, help="target answered.json (default: canonical ora-open-sessions-board path)")
    a = ap.parse_args(argv)

    try:
        with open(a.entries_file, encoding="utf-8") as f:
            entries = json.load(f)
        validate_entries(entries)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        sys.stderr.write("FAILED: %s\n" % e)
        return 1

    for attempt in range(3):
        try:
            existing = load_json_dict(a.answered_file)
        except ValueError as e:
            sys.stderr.write("FAILED: existing answered.json is corrupt, refusing to overwrite blind: %s\n" % e)
            return 1
        merged = dict(existing)
        merged.update(entries)
        try:
            write_atomic(a.answered_file, merged)
        except OSError as e:
            sys.stderr.write("attempt %d: write failed (%s) — retrying\n" % (attempt + 1, e))
            time.sleep(0.25 * (attempt + 1))
            continue

        failed = verify(a.answered_file, entries)
        if not failed:
            print("upserted %d sessionId(s) into %s: %s" % (
                len(entries), a.answered_file, ", ".join(entries.keys())))
            return 0
        sys.stderr.write("attempt %d: wrote %s but read-back verification failed for: %s — retrying\n" % (
            attempt + 1, a.answered_file, ", ".join(failed)))
        time.sleep(0.25 * (attempt + 1))

    sys.stderr.write(
        "FAILED: could not verify all entries landed in %s after 3 attempts.\n"
        "  DO NOT report this upsert as done — surface this failure in the run summary.\n"
        % a.answered_file)
    return 2


if __name__ == "__main__":
    sys.exit(main())
