#!/usr/bin/env python
"""Idempotently register the EOS reliability hooks in settings.json.
Backs up first. Re-runnable: skips any hook whose command is already present.
Run with the Claude app CLOSED is NOT required (settings.json is read live), but
re-launch/restart is needed for new hooks to take effect."""
import json, shutil, sys, os

SETTINGS = r"C:/Users/Owner/.claude/settings.json"
BACKUP = SETTINGS + ".bak-eos-hooks"

def cmd(path):
    return {"type": "command", "command": f'python "{path}"'}

# (event, matcher_or_None, command_path)
NEW = [
    ("PreToolUse",  "Edit|Write|MultiEdit", "C:/Users/Owner/.claude/hooks/eos-plan-gate.py"),
    ("PreToolUse",  "Bash",                 "C:/Users/Owner/.claude/hooks/eos-evidence-gate.py"),
    ("PostToolUse", "Write|Edit",           "C:/Users/Owner/.claude/hooks/eos-plan-marker.py"),
    ("PostToolUse", "Bash",                 "C:/Users/Owner/.claude/hooks/eos-gate-sentinel.py"),
    ("SessionEnd",  None,                   "C:/Users/Owner/.claude/hooks/eos-telemetry.py"),
]

def main():
    with open(SETTINGS, encoding="utf-8") as f:
        data = json.load(f)
    shutil.copy(SETTINGS, BACKUP)
    hooks = data.setdefault("hooks", {})

    def already(event, path):
        for entry in hooks.get(event, []):
            for h in entry.get("hooks", []):
                if path in h.get("command", ""):
                    return True
        return False

    added = []
    for event, matcher, path in NEW:
        if not os.path.exists(path):
            print(f"[ABORT] hook script missing: {path}"); sys.exit(1)
        if already(event, path):
            print(f"[SKIP] {event} already has {os.path.basename(path)}")
            continue
        entry = {"hooks": [cmd(path)]}
        if matcher is not None:
            entry = {"matcher": matcher, "hooks": [cmd(path)]}
        hooks.setdefault(event, []).append(entry)
        added.append(f"{event}:{os.path.basename(path)}")

    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    # validate
    with open(SETTINGS, encoding="utf-8") as f:
        json.load(f)
    print("[OK] settings.json valid after edit.")
    print("[ADDED]", added if added else "(nothing new)")
    for ev in ("UserPromptSubmit", "PreToolUse", "PostToolUse", "SessionStart", "Stop", "SessionEnd"):
        print(f"  {ev}: {len(hooks.get(ev, []))} entries")

if __name__ == "__main__":
    main()
