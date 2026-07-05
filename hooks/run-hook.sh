#!/bin/sh
# ORA portable hook launcher -- FAIL-OPEN.
# Usage: bash "$HOME/.claude/hooks/run-hook.sh" <hook-file.py> [args...]
# Resolves a Python interpreter (python3 -> python -> desktop Python313) and
# execs the named hook from this script's own directory, passing stdin through.
# FAIL-OPEN CONTRACT: any launcher-level failure -- missing argument, missing
# hook file, no interpreter -- exits 0 silently, so a broken launcher can never
# block a tool call. Use run-hook-strict.sh for fail-closed hooks.
# POSIX sh; runs under Git Bash on Windows and sh on Linux. ASCII only.

[ "$#" -ge 1 ] || exit 0
HOOK_NAME=$1
shift

HOOK_DIR=$(dirname "$0")
HOOK_FILE="$HOOK_DIR/$HOOK_NAME"
[ -f "$HOOK_FILE" ] || exit 0

PY=""
for CAND in python3 python \
    /c/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe \
    "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe"; do
  if command -v "$CAND" >/dev/null 2>&1; then
    PY=$CAND
    break
  fi
done
[ -n "$PY" ] || exit 0

exec "$PY" "$HOOK_FILE" "$@"
