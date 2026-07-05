#!/usr/bin/env bash
# ORA RAM guard -- PostToolUse hook (throttle wrapper + OS dispatcher).
# Cheap path: 60s throttle in bash so the guard is only spawned once/minute.
# When the throttle passes, hands off to the per-OS guard -- ram-guard.ps1
# (Windows: RAM read + warn/auto-park) or ram-guard.sh (Linux: warn-only) --
# passing the authoritative session_id from the hook's stdin so the guard never
# parks THIS session. Guard paths resolve from this script's own directory.
# Always exits 0; can never block a tool.

INPUT=$(cat 2>/dev/null)
STAMP="/tmp/.ora_ram_watchdog"
NOW=$(date +%s); LAST=0
[ -f "$STAMP" ] && LAST=$(cat "$STAMP" 2>/dev/null || echo 0)
[ $((NOW - LAST)) -lt 60 ] && exit 0
echo "$NOW" > "$STAMP"

DIR=$(cd "$(dirname "$0")" 2>/dev/null && pwd)
PY=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
SID=""
if [ -n "$PY" ]; then
  SID=$(printf '%s' "$INPUT" | "$PY" -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
fi

if { command -v powershell >/dev/null 2>&1 || command -v powershell.exe >/dev/null 2>&1; } && [ -f "$DIR/ram-guard.ps1" ]; then
  powershell -NoProfile -ExecutionPolicy Bypass -File "$DIR/ram-guard.ps1" "$SID" 2>/dev/null
elif [ -f "$DIR/ram-guard.sh" ]; then
  bash "$DIR/ram-guard.sh" "$SID" 2>/dev/null
fi
exit 0
