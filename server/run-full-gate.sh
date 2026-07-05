#!/usr/bin/env bash
# run-full-gate.sh -- nightly full-gate wrapper for ora-full-gate.service.
#
# Runs the FULL oxford-command-center gate (governance, typecheck, lint,
# test, reconcile, warehouse:verify, warehouse:drift) -- the two data-bound
# steps need WORKBOOK_PATH + FINANCIALS_DIR, which arrive via the unit's
# EnvironmentFile (~/.config/ora/ora.env).
#
# SKIP semantics (EOS doctrine: productivity gates FAIL OPEN): systemd's
# ConditionPathExists cannot read a path out of an EnvironmentFile variable,
# so the data-presence check lives here instead -- when the corpus is not
# on this host yet, print SKIP and exit 0. A non-zero exit therefore always
# means the gate itself is red, which is the signal the timer exists for.
# ASCII only. shellcheck-clean. Idempotent (gate is read-only + tmpdir).

set -euo pipefail

# fnm-installed node is not on systemd's default PATH.
if [ -x "$HOME/.local/share/fnm/fnm" ]; then
  export PATH="$HOME/.local/share/fnm:$PATH"
  eval "$(fnm env)"
fi

if [ ! -f "${WORKBOOK_PATH:-}" ]; then
  echo "SKIP: WORKBOOK_PATH unset or file missing -- data corpus not on this host yet; gate not run (exit 0)"
  exit 0
fi
if [ ! -d "${FINANCIALS_DIR:-}" ]; then
  echo "SKIP: FINANCIALS_DIR unset or dir missing -- data corpus not on this host yet; gate not run (exit 0)"
  exit 0
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "run-full-gate: npm not found (fnm not provisioned?) -- cannot run gate" >&2
  exit 1
fi

# warehouse-verify and warehouse-drift resolve the committed seed JSON from
# process.cwd() -- the gate MUST run from the repo root.
cd "$HOME/oxford-command-center"
exec npm run gate
