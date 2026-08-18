import json, os, datetime

BASE = r"C:\Users\Owner\AppData\Roaming\Claude"
SESS = r"a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\583f08bc-0123-4111-8158-8fe3d927e350\scheduled-tasks.json"
regs = {
    "cc":   os.path.join(BASE, "claude-code-sessions", SESS),
    "lams": os.path.join(BASE, "local-agent-mode-sessions", SESS),
}

def ts(v):
    if not v:
        return None
    try:
        return datetime.datetime.fromtimestamp(int(v) / 1000).isoformat(timespec="minutes")
    except Exception:
        return str(v)

for f, p in regs.items():
    for t in json.load(open(p, encoding="utf-8"))["scheduledTasks"]:
        if t.get("enabled") is True:
            print("=== %s / %s" % (f, t["id"]))
            print("   cron     :", t.get("cronExpression"))
            print("   fireAt   :", ts(t.get("fireAt")), "(raw", t.get("fireAt"), ")")
            print("   created  :", ts(t.get("createdAt")))
            print("   lastRunAt:", t.get("lastRunAt"))
            print("   filePath :", t.get("filePath"))
