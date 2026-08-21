import json, os

BASE = r"C:\Users\Owner\AppData\Roaming\Claude"
SESS = r"a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\583f08bc-0123-4111-8158-8fe3d927e350\scheduled-tasks.json"
regs = {
    "cc":   os.path.join(BASE, "claude-code-sessions", SESS),
    "lams": os.path.join(BASE, "local-agent-mode-sessions", SESS),
}

led = {
    "captured": "2026-08-17T18:45:00-04:00",
    "purpose": "Pause-all until 2026-08-21T17:00-04:00; before-state for EXACT restore",
    "registries": regs,
    "tasks": [],
}
for f, p in regs.items():
    for t in json.load(open(p, encoding="utf-8"))["scheduledTasks"]:
        led["tasks"].append({
            "fleet": f,
            "id": t["id"],
            "enabled": bool(t.get("enabled")),
            "cron": t.get("cronExpression"),
            "fireAt": t.get("fireAt"),
        })

on = [t for t in led["tasks"] if t["enabled"]]
off = [t for t in led["tasks"] if not t["enabled"]]
led["counts"] = {"total": len(led["tasks"]), "enabled": len(on), "disabled": len(off)}
led["MUST_STAY_OFF_ON_RESTORE"] = ["%s/%s" % (t["fleet"], t["id"]) for t in off]
led["RE_ENABLE_ON_RESTORE"] = ["%s/%s" % (t["fleet"], t["id"]) for t in on]

d = r"C:\Users\Owner\.claude\maintenance\_state"
os.makedirs(d, exist_ok=True)
fp = os.path.join(d, "2026-08-17_FleetPause_RestoreLedger_v01.json")
json.dump(led, open(fp, "w", encoding="utf-8"), indent=1)

print("WROTE", fp)
print("counts:", led["counts"])
print("MUST STAY OFF ON RESTORE:", led["MUST_STAY_OFF_ON_RESTORE"])
