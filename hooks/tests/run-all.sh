#!/bin/sh
# ORA hooks aggregate test runner.
# Usage: sh hooks/tests/run-all.sh [--require-confidentiality]
# Runs every hooks/tests/test-*.py plus hooks/test-ora-autonomy-gate.py with
# the resolved interpreter (python3 -> python) and prints per-suite PASS/FAIL.
# Special case: test-confidentiality-guard.py needs the live (untracked)
# hooks/confidential-terms.json -- if that file is absent the suite is
# SKIPped and does NOT count as a failure (it cannot run on a fresh clone).
#   --require-confidentiality: turn that SKIP into a hard FAIL (exit 1). The
#   final burn-in / a fail-closed gate passes this so a missing terms file
#   can never yield a vacuous confidentiality pass. Default: SKIP tolerated.
# Exits nonzero if any suite that ran failed. ASCII only.

REQUIRE_CONF=0
for ARG in "$@"; do
  case "$ARG" in
    --require-confidentiality) REQUIRE_CONF=1 ;;
    *) echo "run-all: unknown argument: $ARG (only --require-confidentiality is supported)" >&2; exit 2 ;;
  esac
done

DIR=$(cd "$(dirname "$0")" && pwd)
PY=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
if [ -z "$PY" ]; then
  echo "run-all: no python interpreter found (need python3 or python)" >&2
  exit 1
fi

TMP_OUT="${TMPDIR:-/tmp}/ora-hooks-run-all.$$"
FAILED=0
RAN=0

for SUITE in "$DIR"/test-*.py "$DIR/../test-ora-autonomy-gate.py"; do
  [ -f "$SUITE" ] || continue
  NAME=$(basename "$SUITE")
  if [ "$NAME" = "test-confidentiality-guard.py" ] && [ ! -f "$DIR/../confidential-terms.json" ]; then
    if [ "$REQUIRE_CONF" -eq 1 ]; then
      echo "FAIL  $NAME (--require-confidentiality: terms file absent -- refusing vacuous pass)"
      FAILED=$((FAILED + 1))
    else
      echo "SKIP (terms file not provisioned)  $NAME"
    fi
    continue
  fi
  RAN=$((RAN + 1))
  if "$PY" "$SUITE" >"$TMP_OUT" 2>&1; then
    echo "PASS  $NAME"
  else
    echo "FAIL  $NAME"
    sed 's/^/      /' "$TMP_OUT"
    FAILED=$((FAILED + 1))
  fi
done
rm -f "$TMP_OUT"

echo ""
echo "run-all: $RAN suite(s) run, $FAILED failed"
[ "$FAILED" -eq 0 ] || exit 1
exit 0
