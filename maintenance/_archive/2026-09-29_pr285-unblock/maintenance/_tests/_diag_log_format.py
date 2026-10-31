"""Throwaway diagnostic: what do scheduler dispatch lines actually look like now?"""
import os, pathlib, re

appdata = os.environ.get("APPDATA")
logs = pathlib.Path(appdata) / "Claude" / "logs"
paths = [logs / "main.log"] + [logs / ("main%d.log" % i) for i in range(1, 5)]

NEEDLES = ("Spawning new session for scheduled task",
           "Confirmed task run for",
           "Cleared stale pending dispatch",
           "Skipping dispatch")

OLD = re.compile(
    r"^(?P<ts>\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) \[(?:info|warn)\] "
    r"\[(?P<prefix>CCDScheduledTasks|ScheduledTasks)\] ")

for p in paths:
    if not p.exists():
        print("ABSENT", p.name)
        continue
    hits = {n: 0 for n in NEEDLES}
    samples = {}
    matched_old = 0
    with open(p, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            for n in NEEDLES:
                if n in line:
                    hits[n] += 1
                    if n not in samples:
                        samples[n] = line.rstrip()[:180]
                    if OLD.match(line):
                        matched_old += 1
    print("=== %s  (size %d)" % (p.name, p.stat().st_size))
    print("    old-regex prefix matches:", matched_old)
    for n in NEEDLES:
        print("    %-45s %d" % (n, hits[n]))
        if n in samples:
            print("        SAMPLE: %s" % samples[n])
