"""AM-cluster availability analysis.

Question being answered: does moving the AM cron slots later actually fix the
recurring morning lateness, or is the machine's first-availability time too
variable for ANY fixed slot to help?

Evidence = the first scheduler dispatch of each calendar day, taken from the
rotated main*.log set. That is the operative fact: a cron slot earlier than
first-availability cannot fire on time no matter where it is placed.
"""
import glob, os, re, sys, collections, datetime

# LOGDIR is DISCOVERED, not hardcoded (fixed 2026-08-26). This line read
# %APPDATA%\Claude\logs until the app moved its logs to %LOCALAPPDATA%\Claude\Logs
# on 2026-08-20; for six days afterwards this script silently produced a table
# that simply ended on 2026-08-17 and said nothing about why -- one of three
# detectors that reported success off an abandoned directory.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shared"))
try:
    import log_liveness
except Exception:
    log_liveness = None

if log_liveness is not None:
    try:
        LOGDIR = str(log_liveness.discover_log_dir()[0])
    except Exception:
        LOGDIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Claude", "Logs")
else:
    LOGDIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Claude", "Logs")

paths = sorted(glob.glob(os.path.join(LOGDIR, "main*.log")))
print("log dir      : %s" % LOGDIR)
print("logs scanned: %d" % len(paths))
if not paths:
    print("[ACTION] no main*.log under that directory — this table would be EMPTY, "
          "not clean. Run _shared/log_liveness.py before trusting anything below.")

# ---- LOG-LIVENESS GATE (added 2026-09-02) -----------------------------
# Discovering the newest log directory only proves it is READABLE. It says
# nothing about whether that directory's logs are FRESH ENOUGH to trust for
# this report -- a directory can resolve cleanly and still hold nothing
# newer than a freeze days ago (see _shared/log_liveness.py's docstring,
# which names this script by name as a caller whose output goes stale when
# that happens). dispatch-skip-probe.py and phantom-dispatch-probe.py both
# already gate on this; this script discovered the directory but never
# checked it, so a stale/frozen directory could still emit a historical-
# looking table with no indication it was unverifiable.
WINDOW_HOURS = 24.0
liveness = None
if log_liveness is not None:
    try:
        newest_activity = log_liveness.newest_registry_dispatch()
    except Exception:
        newest_activity = None
    liveness = log_liveness.assess(LOGDIR, window_hours=WINDOW_HOURS,
                                    newest_activity=newest_activity)
    print("log liveness : %s" % liveness.verdict)
    if not liveness.usable:
        print(liveness.banner())
else:
    print("[unverifiable] _shared/log_liveness.py could not be imported — log "
          "liveness is UNESTABLISHED this run; treat everything below as unverifiable.")

# e.g. 2026-08-14 07:57:23.123 ... Spawning new session for scheduled task <id>
TS = re.compile(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2}):(\d{2})")
HIT = ("Spawning new session for scheduled task", "Confirmed task run for:")

first = {}          # date -> (h, m, s, line)
per_day_count = collections.Counter()

for p in paths:
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                if not any(h in line for h in HIT):
                    continue
                m = TS.search(line)
                if not m:
                    continue
                d, h, mi, s = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
                per_day_count[d] += 1
                key = (h, mi, s)
                if d not in first or key < first[d][:3]:
                    first[d] = (h, mi, s, line.strip()[:110])
    except Exception as e:
        print("  WARN could not read %s: %s" % (os.path.basename(p), e))

if not first:
    print("NO DISPATCH LINES FOUND - cannot answer from this source.")
    raise SystemExit(2)

print("\n%-12s %-4s %-10s %-8s %s" % ("DATE", "DOW", "FIRST-DISP", "N-DISP", "vs 06:00 target"))
print("-" * 78)
rows = []
for d in sorted(first):
    h, mi, s, _ = first[d]
    dow = datetime.date(*map(int, d.split("-"))).strftime("%a")
    mins_late = (h * 60 + mi) - 360          # 06:00 ET reference
    rows.append((d, dow, h * 60 + mi, mins_late))
    print("%-12s %-4s %02d:%02d:%02d   %-8d %+d min" % (d, dow, h, mi, s,
                                                        per_day_count[d], mins_late))

wk = [r for r in rows if r[1] not in ("Sat", "Sun")]
if wk:
    firsts = sorted(r[2] for r in wk)
    n = len(firsts)
    def hm(x): return "%02d:%02d" % (x // 60, x % 60)
    print("\nWEEKDAYS ONLY (n=%d)" % n)
    print("  earliest first-dispatch : %s" % hm(firsts[0]))
    print("  median                  : %s" % hm(firsts[n // 2]))
    print("  latest                  : %s" % hm(firsts[-1]))
    print("  spread (max-min)        : %d min" % (firsts[-1] - firsts[0]))
    for slot in (360, 420, 480, 510, 540, 600, 630, 660):
        ontime = sum(1 for x in firsts if x <= slot)
        print("  a %s slot would have been on time %d/%d days (%.0f%%)"
              % (hm(slot), ontime, n, 100.0 * ontime / n))

# ---- LOG-LIVENESS TRAILER ----------------------------------------------
# Print the table above in full either way (same discipline as
# dispatch-skip-probe.py / phantom-dispatch-probe.py: a dead confirmation
# leg is "could not look", not "looked and it was clean" -- the historical
# rows are still real data), but never let the run exit clean when the
# directory backing them could not be confirmed fresh.
if liveness is not None and not liveness.usable:
    print("\n[ACTION] TABLE ABOVE IS UNVERIFIABLE — log liveness verdict is %s. "
          "The discovered log directory is readable but its logs are not "
          "confirmed fresh enough to trust for this reporting window; recent "
          "days may be silently missing. Do not treat this table as a current "
          "picture of AM-cluster dispatch times. See the banner above for "
          "remedy." % liveness.verdict)
    raise SystemExit(2)
elif liveness is None:
    print("\n[unverifiable] log liveness could not be established this run "
          "(log_liveness module unavailable) — do not treat the table above "
          "as current.")
    raise SystemExit(2)
