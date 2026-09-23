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
        "name": "publish-fleet-heartbeat -> fleet-deadman GitHub Action",
        "producer": "publish-fleet-heartbeat.py (run daily by push-fleet-heartbeat.ps1; OI-323)",
        "output_file": os.path.join(STATE_DIR, "heartbeat-publish-ok.json"),
        "consumer": "external fleet-deadman.yml (reads the deadman-heartbeat branch this publish updates; a stale ok-stamp means the publish stopped and the dead-man is reading old data)",
        "max_age_hours": 26,  # daily 07:30 ET publish + slack, same window as publish-fleet-heartbeat.py --status
    },
    {
        # OI-331 (2026-09-22): before this, the backup push's failures (no main
        # worktree, a real merge conflict, or the push itself failing) were only
        # ever a log line in push-fleet-heartbeat.log -- nothing outside that log
        # read them, so ~a dozen hook-test-gate failures and 4 remote-main races
        # since 08-15 went unnoticed until a second adversarial review of the
        # OI-323 build found them by hand. This entry gives that signal the same
        # freshness-contract monitoring as the heartbeat publish above -- a stale
        # or missing stamp here means the backup push (getting pending
        # main-checkout work onto GitHub) has stopped succeeding, independent of
        # whether the heartbeat publish itself is still healthy.
        "name": "push-fleet-heartbeat backup-push -> ~/.claude durable-backup coverage",
        "producer": "push-fleet-heartbeat.ps1 backup-push step (writes on every success, including a no-op day; OI-331)",
        "output_file": os.path.join(STATE_DIR, "backup-push-ok.json"),
        "consumer": "state-freshness-probe.py (guard STEP 2.95; 48h, pause-independent) also watches this file; nothing else reads it. This is currently the SOLE route any local ~/.claude history has to GitHub (confirmed 2026-09-22: no other script in the codebase runs `git push` against this repo), so a stale/missing stamp means committed work is accumulating with no durable copy off this machine",
        "max_age_hours": 26,  # daily 07:30 ET run + slack, same window as the heartbeat-publish contract above
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
