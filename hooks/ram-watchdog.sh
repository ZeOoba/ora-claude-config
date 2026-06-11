#!/usr/bin/env bash
# ORA RAM guard -- PostToolUse hook (throttle wrapper).
# Cheap path: 60s throttle in bash so PowerShell is only spawned once/minute.
# When the throttle passes, hands off to ram-guard.ps1 (RAM read + warn/auto-park),
# passing the authoritative session_id from the hook's stdin so the guard never
# parks THIS session. Always exits 0; can never block a tool.

INPUT=$(cat 2>/dev/null)
STAMP="/tmp/.ora_ram_watchdog"
NOW=$(date +%s); LAST=0
[ -f "$STAMP" ] && LAST=$(cat "$STAMP" 2>/dev/null || echo 0)
[ $((NOW - LAST)) -lt 60 ] && exit 0
echo "$NOW" > "$STAMP"

SID=$(printf '%s' "$INPUT" | python -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
powershell -NoProfile -ExecutionPolicy Bypass -File "C:/Users/Owner/.claude/hooks/ram-guard.ps1" "$SID" 2>/dev/null
exit 0
