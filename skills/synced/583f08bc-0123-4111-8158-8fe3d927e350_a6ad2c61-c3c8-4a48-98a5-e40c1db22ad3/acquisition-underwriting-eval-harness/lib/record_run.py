"""Dated, re-runnable snapshot writer for the acquisition-underwriting golden-set harness.

Each call to record_run() writes one timestamped, self-contained JSON snapshot
under runs/ (never overwritten by a later run) and appends one row to
runs/summary.csv for at-a-glance trend visibility across runs over time.
"""

import csv
import json
import os
import re
from datetime import datetime, timezone

# Windows-reserved filename characters, plus space (kept out of the filename
# for readability, not because it's reserved) -- a run_label like
# "post-<doctrine-change>" (an example literally used in SKILL.md's own docs)
# or one containing a colon would otherwise raise or silently produce a
# mis-scoped file on Windows.
_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\s]+')


def _sanitize_run_label(run_label):
    if not run_label:
        return run_label
    sanitized = _UNSAFE_FILENAME_CHARS.sub("-", run_label).strip("-")
    return sanitized or None


def record_run(results, run_dir, skill_sha=None, run_label=None, run_timestamp=None):
    """Write a dated snapshot of a harness run.

    Args:
        results: list of diff_verdict() result dicts (one per golden deal).
        run_dir: path to the harness's runs/ directory.
        skill_sha: optional short SHA / version string identifying the
            acquisition-underwriting SKILL.md revision this run was executed
            against (for provenance — lets a trend view attribute a score
            delta to a specific doctrine edit).
        run_label: optional short human label for this run (e.g. "baseline",
            "post-v4.12-edit"). Purely descriptive.
        run_timestamp: ISO-8601 UTC timestamp to use; defaults to now(). Exposed
            as a parameter so callers (and tests) can pin a deterministic value.

    Returns:
        dict with the written snapshot path, csv path, and the aggregate
        summary that was appended.

    Raises:
        ValueError: if results is empty or a result dict is missing required keys.
    """
    if not results:
        raise ValueError("results must be a non-empty list of diff_verdict() outputs")

    required_keys = {"deal_id", "status", "scored"}
    for i, r in enumerate(results):
        missing = required_keys - r.keys()
        if missing:
            raise ValueError(f"results[{i}] missing required keys: {sorted(missing)}")

    run_label = _sanitize_run_label(run_label)
    timestamp = run_timestamp or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H%M%SZ"
    )

    scored = [r for r in results if r["scored"]]
    informational = [r for r in results if not r["scored"]]
    scored_pass = [r for r in scored if r["status"] == "PASS"]
    scored_flag = [r for r in scored if r["status"] == "FLAG"]

    snapshot = {
        "run_timestamp": timestamp,
        "run_label": run_label,
        "skill_sha": skill_sha,
        "total_deals": len(results),
        "scored_deals": len(scored),
        "informational_deals": len(informational),
        "scored_pass": len(scored_pass),
        "scored_flag": len(scored_flag),
        "results": results,
    }

    os.makedirs(run_dir, exist_ok=True)
    snapshot_filename = f"{timestamp}{'_' + run_label if run_label else ''}.json"
    snapshot_path = os.path.join(run_dir, snapshot_filename)
    tmp_path = snapshot_path + ".tmp"
    try:
        # Exclusive-create ("x") the temp file, not the exists-check-then-open("w")
        # pattern this used to follow -- that had a TOCTOU window (another process
        # could create snapshot_path between the check and the open) and, more to
        # the point, would leave a truncated/partial JSON file behind if the
        # process died mid-write, which the refuse-to-overwrite guard below would
        # then permanently treat as "already recorded" on any retry.
        with open(tmp_path, "x", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)
        # os.rename fails outright (does not silently overwrite) if snapshot_path
        # already exists on Windows -- this IS the refuse-to-overwrite guard now,
        # atomically, rather than a separate exists() check racing the write.
        os.rename(tmp_path, snapshot_path)
    except FileExistsError as e:
        raise ValueError(
            f"refusing to overwrite an existing snapshot or in-progress write "
            f"({e.filename}) -- re-run with a distinct run_timestamp/run_label, "
            "or check the clock"
        ) from e
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    csv_path = os.path.join(run_dir, "summary.csv")
    csv_is_new = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if csv_is_new:
            writer.writerow(
                [
                    "run_timestamp",
                    "run_label",
                    "skill_sha",
                    "total_deals",
                    "scored_deals",
                    "informational_deals",
                    "scored_pass",
                    "scored_flag",
                    "snapshot_file",
                ]
            )
        writer.writerow(
            [
                timestamp,
                run_label or "",
                skill_sha or "",
                len(results),
                len(scored),
                len(informational),
                len(scored_pass),
                len(scored_flag),
                snapshot_filename,
            ]
        )

    return {
        "snapshot_path": snapshot_path,
        "csv_path": csv_path,
        "summary": {
            "total_deals": len(results),
            "scored_deals": len(scored),
            "informational_deals": len(informational),
            "scored_pass": len(scored_pass),
            "scored_flag": len(scored_flag),
        },
    }
