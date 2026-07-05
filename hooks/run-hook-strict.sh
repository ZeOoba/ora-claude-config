#!/bin/sh
# ORA portable hook launcher -- FAIL-CLOSED.
# Usage: bash "$HOME/.claude/hooks/run-hook-strict.sh" <hook-file.py> [args...]
# Resolves a Python interpreter (python3 -> python -> desktop Python313) and
# execs the named hook from this script's own directory, passing stdin through.
# FAIL-CLOSED CONTRACT: any launcher-level failure -- missing argument, missing
# hook file, no interpreter -- exits 2 with a one-line ASCII reason on stderr,
# which Claude Code treats as a BLOCK. This launcher guards the confidentiality
# egress hook: if the guard cannot run, the tool call must not proceed.
# POSIX sh; runs under Git Bash on Windows and sh on Linux. ASCII only.

if [ "$#" -lt 1 ]; then
  echo "run-hook-strict: missing hook file argument - BLOCKING (fail-closed)" >&2
  exit 2
fi
HOOK_NAME=$1
shift

HOOK_DIR=$(dirname "$0")
HOOK_FILE="$HOOK_DIR/$HOOK_NAME"
if [ ! -f "$HOOK_FILE" ]; then
  echo "run-hook-strict: hook file not found: $HOOK_FILE - BLOCKING (fail-closed)" >&2
  exit 2
fi

PY=""
for CAND in python3 python \
    /c/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe \
    "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe"; do
  if command -v "$CAND" >/dev/null 2>&1; then
    PY=$CAND
    break
  fi
done
if [ -z "$PY" ]; then
  echo "run-hook-strict: no python interpreter found - BLOCKING (fail-closed)" >&2
  exit 2
fi

exec "$PY" "$HOOK_FILE" "$@"
