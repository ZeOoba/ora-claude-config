import json, os, time, datetime

BASE = r"C:\Users\Owner\AppData\Roaming\Claude"
SESS = r"a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\583f08bc-0123-4111-8158-8fe3d927e350\scheduled-tasks.json"
regs = {
    "cc":   os.path.join(BASE, "claude-code-sessions", SESS),
    "lams": os.path.join(BASE, "local-agent-mode-sessions", SESS),
}

def snap():
    out = {}
    for f, p in regs.items():
        st = os.stat(p)
        tasks = json.load(open(p, encoding="utf-8"))["scheduledTasks"]
        out[f] = {
            "mtime": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
            "on": sorted(t["id"] for t in tasks if t.get("enabled") is True),
            "n": len(tasks),
        }
    return out

a = snap()
print("PASS 1", datetime.datetime.now().isoformat(timespec="seconds"))
for f, v in a.items():
    print("  %-5s n=%d mtime=%s enabled=%d %s" % (f, v["n"], v["mtime"], len(v["on"]), v["on"]))

time.sleep(45)

b = snap()
print("PASS 2", datetime.datetime.now().isoformat(timespec="seconds"))
for f, v in b.items():
    print("  %-5s n=%d mtime=%s enabled=%d %s" % (f, v["n"], v["mtime"], len(v["on"]), v["on"]))

print("---")
for f in regs:
    moved = (a[f]["mtime"] != b[f]["mtime"]) or (a[f]["on"] != b[f]["on"])
    print("%-5s SETTLED=%s  delta_on=%s" % (
        f, not moved, sorted(set(a[f]["on"]) ^ set(b[f]["on"])) or "none"))
