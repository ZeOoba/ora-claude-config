import json, os, collections

BASE = r"C:\Users\Owner\AppData\Roaming\Claude"
SESS = r"a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\583f08bc-0123-4111-8158-8fe3d927e350\scheduled-tasks.json"
regs = {
    "cc":   os.path.join(BASE, "claude-code-sessions", SESS),
    "lams": os.path.join(BASE, "local-agent-mode-sessions", SESS),
}

for f, p in regs.items():
    tasks = json.load(open(p, encoding="utf-8"))["scheduledTasks"]
    print("=== fleet", f, "n=", len(tasks))
    keys = collections.Counter()
    vals = collections.Counter()
    for t in tasks:
        keys.update(t.keys())
        vals[repr(t.get("enabled", "<<MISSING>>"))] += 1
    print("  enabled-value distribution:", dict(vals))
    print("  keys containing 'nabl'/'ctiv'/'aus'/'isabl':",
          [k for k in keys if any(s in k.lower() for s in ("nabl", "ctiv", "aus", "isabl"))])
    print("  sample of entries whose enabled is not True:")
    n = 0
    for t in tasks:
        if t.get("enabled") is not True and n < 4:
            print("   ", t["id"], "| enabled=", repr(t.get("enabled", "<<MISSING>>")),
                  "| lastRunAt=", t.get("lastRunAt"), "| keys=", sorted(t.keys()))
            n += 1
