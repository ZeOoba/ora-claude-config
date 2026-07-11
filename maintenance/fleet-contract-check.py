#!/usr/bin/env python3
"""ORA fleet internal-contract-check probe.

WHY: existing guards (registry-membership-probe.py, governor-drift-probe.py,
doctrine-integrity-probe.py) all check that a task RAN or that content matches
a known-good value. None of them check that a producer script's OUTPUT FILE is
still being kept fresh by whatever is supposed to update it -- so when a
producer's cadence silently breaks (refactored away, its own task disabled,
an exception swallowed), a downstream consumer keeps reading a frozen file
with no alarm. This is the exact failure class a 2026-07-11 workflow-audit
session found three separate times: automation-health-monitor was refactored
to read live instead of exporting a snapshot file, and a downstream consumer
kept silently reading the last-frozen snapshot until someone manually traced
a false-positive staleness alarm back to it; a Notion "Rate Snapshot" page
went 19 days stale after its producer (ora-treasury-yield-prefetch) was
archived on an unverified assumption another task had absorbed its duty; and
a scheduled task's own SKILL.md was lost outright at least 3 times, each
requiring manual session-transcript archaeology to recover (see the
orphaned-task-forensics skill, added the same day).

This probe does NOT try to be exhaustive -- it checks a small, explicitly
seeded registry of CONTRACTS (producer script -> output file -> consumer
script) discovered by grepping which scripts read vs. write each _state/*.json
file. Add a contract here the next time a producer/consumer pair is
identified; this is meant to grow, not to be complete on day one.

Exit 0 = all contracts fresh. Exit 1 = at least one contract stale/missing.
Exit 2 = probe error (fail loud, not silent -- I5).

Usage: python fleet-contract-check.py            # check all seeded contracts
       python fleet-contract-check.py --quiet     # only print on drift
"""
import datetime
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
STATE_DIR = os.path.join(CLAUDE, "maintenance", "_state")

# Seeded contracts, discovered 2026-07-11 by grepping which scripts read vs.
# write each _state/*.json file. `max_age_hours` = producer's expected cadence
# + a buffer (roughly 1.5x the cadence), not a tight SLA -- this probe is
# meant to catch "stopped updating entirely", not to police punctuality
# (that's registry-membership-probe.py's / automation-health-monitor's job).
CONTRACTS = [
    {
        "name": "registry-membership -> doctrine-status",
        "producer": "registry-membership-probe.py",
        "output_file": os.path.join(STATE_DIR, "registry-membership.json"),
        "consumer": "_shared/write-doctrine-status.py (reads registry-membership.json as an input)",
        "max_age_hours": 36,  # producer runs daily via ora-setup-audit STEP 1
    },
    {
        "name": "write-doctrine-status -> git-prepush-doctrine-gate",
        "producer": "_shared/write-doctrine-status.py",
        "output_file": os.path.join(STATE_DIR, "doctrine-status.json"),
        "consumer": "hooks/git-prepush-doctrine-gate.py (a git pre-push hook -- stale input here means every push is gated on frozen data)",
        "max_age_hours": 36,
    },
    {
        "name": "emit-fleet-heartbeat -> ora-cowork-watchdog dead-man's-switch",
        "producer": "emit-fleet-heartbeat.py (pushed via push-fleet-heartbeat.ps1)",
        "output_file": os.path.join(STATE_DIR, "fleet-heartbeat.json"),
        "consumer": "external GitHub ora-cowork-watchdog (checks the pushed copy; a stale LOCAL file is a leading indicator the push side broke too)",
        "max_age_hours": 20,  # producer's own cron is twice-daily, 05:50 + 17:50
    },
]


def check_contract(c, now):
    path = c["output_file"]
    if not os.path.isfile(path):
        return "MISSING", None
    age_hours = (now - datetime.datetime.fromtimestamp(os.path.getmtime(path))).total_seconds() / 3600.0
    if age_hours > c["max_age_hours"]:
        return "STALE", age_hours
    return "OK", age_hours


def main():
    quiet = "--quiet" in sys.argv
    now = datetime.datetime.now()
    bad = False
    results = []

    for c in CONTRACTS:
        status, age_hours = check_contract(c, now)
        results.append((c, status, age_hours))
        if status != "OK":
            bad = True

    if not quiet or bad:
        print("ORA FLEET INTERNAL-CONTRACT-CHECK PROBE")
        for c, status, age_hours in results:
            if status == "MISSING":
                print(f"  [ACTION] {c['name']}: output file never found -- "
                      f"{c['output_file']} does not exist. Producer ({c['producer']}) "
                      f"may never have run, or the path moved. Consumer: {c['consumer']}")
            elif status == "STALE":
                print(f"  [ACTION] {c['name']}: output is {age_hours:.1f}h old "
                      f"(> {c['max_age_hours']}h threshold) -- {c['producer']} appears to "
                      f"have stopped updating {c['output_file']}. Consumer reading it "
                      f"silently: {c['consumer']}. Verify the producer is still enabled "
                      f"and running (fleet-status.py), or route through "
                      f"orphaned-task-forensics if it was archived/refactored away.")
            else:
                print(f"  OK {c['name']}: {age_hours:.1f}h old (<= {c['max_age_hours']}h)")

        if not bad:
            print("  OK -- all seeded contracts fresh.")

    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
