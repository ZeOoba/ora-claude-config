"""AM-cluster availability analysis.

Question being answered: does moving the AM cron slots later actually fix the
recurring morning lateness, or is the machine's first-availability time too
variable for ANY fixed slot to help?

Evidence = the first scheduler dispatch of each calendar day, taken from the
rotated main*.log set. That is the operative fact: a cron slot earlier than
first-availability cannot fire on time no matter where it is placed.
"""
import glob, os, re, collections, datetime

LOGDIR = os.path.join(os.environ["APPDATA"], "Claude", "logs")
paths = sorted(glob.glob(os.path.join(LOGDIR, "main*.log")))
print("logs scanned: %d" % len(paths))

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
