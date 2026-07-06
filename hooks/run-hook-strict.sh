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
  # Skip the Microsoft Store App-Execution-Alias stub: on stock Windows,
  # "python3" resolves to a WindowsApps stub that cannot actually run.
  RESOLVED=$(command -v "$CAND" 2>/dev/null) || RESOLVED=$CAND
  case "$RESOLVED" in
    *[Ww]indows[Aa]pps*) continue ;;
  esac
  # Functional probe (not mere existence): the stub fails to run Python.
  if "$CAND" -c "import sys" >/dev/null 2>&1; then
    PY=$CAND
    break
  fi
done
if [ -z "$PY" ]; then
  echo "run-hook-strict: no python interpreter found - BLOCKING (fail-closed)" >&2
  exit 2
fi

# Do NOT exec: we must inspect the hook's exit code and coerce fail-closed.
# Claude Code treats only exit 2 as a block; any other non-zero (stub exit 49,
# 126, OOM kill, etc.) would otherwise fail OPEN. Force those to 2.
"$PY" "$HOOK_FILE" "$@"
RC=$?
case "$RC" in
  0|2) exit "$RC" ;;
  *)
    echo "run-hook-strict: hook exited $RC (not 0/2) - BLOCKING (fail-closed)" >&2
    exit 2
    ;;
esac
