import json, os

BASE = r"C:\Users\Owner\AppData\Roaming\Claude"
SESS = r"a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\583f08bc-0123-4111-8158-8fe3d927e350\scheduled-tasks.json"
LAMS = os.path.join(BASE, "local-agent-mode-sessions", SESS)
CC = os.path.join(BASE, "claude-code-sessions", SESS)

# Pre-pause truth, from fleet-status.py run at 14:45 local (before the 14:50 toggle):
# lams had 26 enabled / 2 disabled.
PRE_OFF = {"ora-cam-data-backfill", "ora-passed-deal-tracker"}   # already OFF before today
UNTOUCHED = {"ora-counsel-review-standard-positions-2027"}        # one-time 2027, still on

lams = json.load(open(LAMS, encoding="utf-8"))["scheduledTasks"]
now_off = [t["id"] for t in lams if t.get("enabled") is not True]
now_on = [t["id"] for t in lams if t.get("enabled") is True]

restore = sorted(set(now_off) - PRE_OFF)
print("LAMS n=%d  now_on=%s" % (len(lams), now_on))
print("newly disabled today -> RESTORE (%d):" % len(restore))
for i in restore:
    print("   ", i)
print("MUST STAY OFF (%d): %s" % (len(PRE_OFF), sorted(PRE_OFF)))

# sanity: the two pre-existing OFF ids must actually be present and off
missing = [i for i in PRE_OFF if i not in now_off]
print("SANITY pre-off ids not currently off:", missing or "none (ok)")

cc = json.load(open(CC, encoding="utf-8"))["scheduledTasks"]
cc_off = sorted(t["id"] for t in cc if t.get("enabled") is not True)
print("\nCC disabled count: %d (resume task covers 35)" % len(cc_off))

out = {
    "corrected": "2026-08-17 (supersedes _v01 which was captured mid-toggle and is WRONG)",
    "pause_window_end": "2026-08-21T17:00:00-04:00",
    "cc_handled_by": "ora-routine-pause-resume-08-21 (registered, fireAt 2026-08-21T17:00 local)",
    "lams_resume_registered": False,
    "LAMS_RE_ENABLE": restore,
    "LAMS_MUST_STAY_OFF": sorted(PRE_OFF),
    "LAMS_UNTOUCHED_STILL_ON": sorted(UNTOUCHED),
    "CC_DISABLED_NOW": cc_off,
}
fp = r"C:\Users\Owner\.claude\maintenance\_state\2026-08-17_FleetPause_RestoreLedger_v02_CORRECTED.json"
json.dump(out, open(fp, "w", encoding="utf-8"), indent=1)
print("\nWROTE", fp)
