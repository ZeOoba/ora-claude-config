#!/usr/bin/env bash
# verify-setup.sh -- ORA Linux server burn-in smoke test. READ-ONLY: checks
# state, never changes it (the hooks test suite writes only to $TMPDIR).
#
# Prints an ASCII PASS/FAIL/WARN table. Exit 1 only on hard FAILs; WARNs
# (e.g. timers not yet enabled, runner not yet installed) exit 0 so the
# provision -> secrets -> data -> verify loop can be run incrementally.
# Never prints secret values -- env checks are presence-only.
# ASCII only. shellcheck-clean. Idempotent by nature (read-only).

set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
# fnm-installed node is not on a non-login shell's PATH.
if ! command -v node >/dev/null 2>&1 && [ -x "$HOME/.local/share/fnm/fnm" ]; then
  export PATH="$HOME/.local/share/fnm:$PATH"
  eval "$(fnm env 2>/dev/null || true)"
fi

FAILS=0
ROWS=()
report() { # $1=PASS|FAIL|WARN  $2=check name  $3=detail
  ROWS+=("$(printf '%-5s %-34s %s' "$1" "$2" "$3")")
  if [ "$1" = "FAIL" ]; then FAILS=$((FAILS + 1)); fi
  return 0
}

ver_ge() { # $1=have $2=need (dotted numerics); true if have >= need
  [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]
}

# ------------------------------------------------------------------ binaries
GIT_VER="$(git --version 2>/dev/null | awk '{print $3}' || true)"
if [ -n "$GIT_VER" ] && ver_ge "$GIT_VER" "2.39"; then
  report PASS "git >= 2.39" "$GIT_VER"
else
  report FAIL "git >= 2.39" "found: ${GIT_VER:-none}"
fi

NODE_VER="$(node --version 2>/dev/null | sed 's/^v//' || true)"
if [ -n "$NODE_VER" ] && ver_ge "$NODE_VER" "20"; then
  report PASS "node >= 20" "$NODE_VER"
else
  report FAIL "node >= 20" "found: ${NODE_VER:-none} (fnm install 22)"
fi

for BIN in claude python3 rg jq; do
  if command -v "$BIN" >/dev/null 2>&1; then
    report PASS "binary: $BIN" "$(command -v "$BIN")"
  else
    report FAIL "binary: $BIN" "not on PATH"
  fi
done

# --------------------------------------------------- ~/.claude config repo
if [ -d "$HOME/.claude/.git" ]; then
  ORIGIN="$(git -C "$HOME/.claude" remote get-url origin 2>/dev/null || true)"
  case "$ORIGIN" in
    *ora-claude-config*) report PASS "config repo (HOME/.claude)" "origin -> ora-claude-config" ;;
    "") report FAIL "config repo (HOME/.claude)" "no origin remote" ;;
    *)  report FAIL "config repo (HOME/.claude)" "unexpected origin (expected ora-claude-config)" ;;
  esac
else
  report FAIL "config repo (HOME/.claude)" "not a git repo -- clone ZeOoba/ora-claude-config there"
fi

# ----------------------------------------------------------- hooks test suite
RUNALL="$HOME/.claude/hooks/tests/run-all.sh"
if [ -f "$RUNALL" ]; then
  HOOKS_OUT="$(sh "$RUNALL" 2>&1 || echo "RUNALL_FAILED")"
  HOOKS_SUMMARY="$(printf '%s\n' "$HOOKS_OUT" | grep '^run-all:' | tail -n1 || true)"
  case "$HOOKS_OUT" in
    *RUNALL_FAILED*) report FAIL "hooks tests (run-all.sh)" "${HOOKS_SUMMARY:-suite failed -- run manually for detail}" ;;
    *)               report PASS "hooks tests (run-all.sh)" "${HOOKS_SUMMARY:-passed}" ;;
  esac
else
  report FAIL "hooks tests (run-all.sh)" "missing: $RUNALL"
fi

# --------------------------------------------------- confidential-terms.json
if [ -f "$HOME/.claude/hooks/confidential-terms.json" ]; then
  report PASS "confidential-terms.json" "present (untracked, as designed)"
else
  report WARN "confidential-terms.json" "ABSENT -- fail-closed guard will brick sessions; place via out-of-band transfer"
fi

# ------------------------------------------------------------------- ora.env
ENV_FILE="$HOME/.config/ora/ora.env"
WB=""
FD=""
if [ -f "$ENV_FILE" ]; then
  MODE="$(stat -c '%a' "$ENV_FILE" 2>/dev/null || echo '?')"
  if [ "$MODE" = "600" ]; then
    report PASS "ora.env mode 600" "$ENV_FILE"
  else
    report FAIL "ora.env mode 600" "mode is $MODE -- chmod 600 $ENV_FILE"
  fi
  for VAR in WORKBOOK_PATH FINANCIALS_DIR NOTION_TOKEN; do
    # Presence-only, value never printed. Sourced in a subshell so nothing
    # leaks into this process.
    VAL_STATE="$(
      set +u
      # shellcheck source=/dev/null
      . "$ENV_FILE" >/dev/null 2>&1 || true
      VAL="$(eval "printf '%s' \"\${$VAR:-}\"")"
      if [ -z "$VAL" ]; then echo empty
      elif printf '%s' "$VAL" | grep -qi 'REPLACE'; then echo placeholder
      else echo set; fi
    )"
    case "$VAL_STATE" in
      set)         report PASS "ora.env defines $VAR" "set (value not shown)" ;;
      placeholder) report WARN "ora.env defines $VAR" "still a REPLACE placeholder" ;;
      *)           report FAIL "ora.env defines $VAR" "missing or empty" ;;
    esac
  done
  # shellcheck source=/dev/null
  WB="$( (set +u; . "$ENV_FILE" >/dev/null 2>&1 || true; printf '%s' "${WORKBOOK_PATH:-}") )"
  # shellcheck source=/dev/null
  FD="$( (set +u; . "$ENV_FILE" >/dev/null 2>&1 || true; printf '%s' "${FINANCIALS_DIR:-}") )"
else
  report FAIL "ora.env" "missing: $ENV_FILE (provision.sh seeds it from server/secrets.env.example)"
fi

# --------------------------------------------------------------- data corpus
if [ -n "$WB" ] && [ -f "$WB" ]; then
  report PASS "workbook file (WORKBOOK_PATH)" "present"
else
  report FAIL "workbook file (WORKBOOK_PATH)" "missing -- run rclone-sync.sh or desktop-push-data.ps1"
fi
if [ -n "$FD" ] && [ -d "$FD" ]; then
  XLS_COUNT="$(find "$FD" -maxdepth 1 -type f \( -name '*.xlsx' -o -name '*.xlsm' \) 2>/dev/null | wc -l | tr -d ' ')"
  if [ "$XLS_COUNT" -ge 32 ]; then
    report PASS "financials corpus (>=32 files)" "$XLS_COUNT .xlsx/.xlsm files"
  else
    report FAIL "financials corpus (>=32 files)" "only $XLS_COUNT .xlsx/.xlsm files"
  fi
else
  report FAIL "financials corpus (>=32 files)" "FINANCIALS_DIR missing"
fi

# ------------------------------------------------------------ pre-push shims
for REPO in "$HOME/.claude" "$HOME/oxford-command-center" "$HOME/ora-skills" "$HOME/BrainVault"; do
  NAME="$(basename "$REPO")"
  if [ ! -d "$REPO/.git" ]; then
    report FAIL "pre-push shim: $NAME" "repo not cloned"
  elif [ -f "$REPO/.git/hooks/pre-push" ] && grep -q 'git-prepush-confidential-scan.py' "$REPO/.git/hooks/pre-push" 2>/dev/null; then
    report PASS "pre-push shim: $NAME" "installed"
  else
    report FAIL "pre-push shim: $NAME" "missing -- bash ~/.claude/hooks/install-prepush.sh $REPO"
  fi
done

# --------------------------------------------------------- systemd user units
UNITS="ora-heartbeat ora-vault-backup ora-telemetry-rollup ora-full-gate ora-data-sync"
if systemctl --user show-environment >/dev/null 2>&1; then
  for U in $UNITS; do
    if systemctl --user list-unit-files "$U.timer" 2>/dev/null | grep -q "$U.timer"; then
      ENABLED="$(systemctl --user is-enabled "$U.timer" 2>/dev/null || true)"
      ACTIVE="$(systemctl --user is-active "$U.timer" 2>/dev/null || true)"
      if [ "$ENABLED" = "enabled" ] && [ "$ACTIVE" = "active" ]; then
        report PASS "timer: $U" "enabled + active"
      else
        report WARN "timer: $U" "loaded, ${ENABLED:-?}/${ACTIVE:-?} -- enable after burn-in: systemctl --user enable --now $U.timer"
      fi
    else
      report FAIL "timer: $U" "unit files not installed -- rerun provision.sh"
    fi
  done
  if loginctl show-user "$(id -un)" 2>/dev/null | grep -q '^Linger=yes'; then
    report PASS "linger" "enabled (timers fire without a login session)"
  else
    report WARN "linger" "not enabled -- sudo loginctl enable-linger $(id -un)"
  fi
else
  report FAIL "systemd --user" "user manager unreachable (no user bus) -- log in as the user directly"
fi

# --------------------------------------------------------------- GitHub runner
if systemctl list-unit-files 'actions.runner.*' 2>/dev/null | grep -q 'actions.runner'; then
  report PASS "GitHub runner service" "installed (actions.runner.*)"
elif [ -f "$HOME/actions-runner-occ/.runner" ]; then
  report WARN "GitHub runner service" "configured but service not installed -- sudo ~/actions-runner-occ/svc.sh install"
else
  report WARN "GitHub runner service" "not installed -- see server/install-runner.sh"
fi

# ------------------------------------------------------------------ timezone
TZ_NOW="$(timedatectl show -p Timezone --value 2>/dev/null || true)"
if [ "$TZ_NOW" = "America/New_York" ]; then
  report PASS "timezone" "America/New_York"
else
  report WARN "timezone" "${TZ_NOW:-unknown} -- timers assume ET: sudo timedatectl set-timezone America/New_York"
fi

# --------------------------------------------------------------- claude auth
if command -v claude >/dev/null 2>&1; then
  CLAUDE_OUT="$(timeout 30 claude -p 'reply OK' --output-format text 2>&1 || true)"
  case "$CLAUDE_OUT" in
    *OK*) report PASS "claude auth (-p smoke)" "replied" ;;
    *)    report WARN "claude auth (-p smoke)" "no OK reply within 30s -- run 'claude' once to log in" ;;
  esac
else
  report WARN "claude auth (-p smoke)" "claude binary missing (see binaries above)"
fi

# ----------------------------------------------------------------- BrainVault
BV="$HOME/BrainVault"
if [ -d "$BV/.git" ]; then
  DIRTY="$(git -C "$BV" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
  AHEAD="$(git -C "$BV" rev-list --count '@{upstream}..HEAD' 2>/dev/null || echo '?')"
  if [ "$AHEAD" = "?" ]; then
    report WARN "BrainVault pushable" "no upstream tracking branch -- git -C ~/BrainVault branch -u origin/main"
  elif [ "$AHEAD" != "0" ]; then
    report WARN "BrainVault pushable" "$AHEAD unpushed commit(s) -- backup lane not current"
  elif [ "$DIRTY" != "0" ]; then
    report PASS "BrainVault status" "clean vs remote; $DIRTY uncommitted change(s) await the 18:05 backup timer"
  else
    report PASS "BrainVault status" "clean and pushed"
  fi
else
  report FAIL "BrainVault status" "repo not cloned at HOME/BrainVault"
fi

# -------------------------------------------------------------------- output
printf '\n%-5s %-34s %s\n' "RSLT" "CHECK" "DETAIL"
printf '%s\n' "----- ---------------------------------- ------------------------------------------"
for ROW in "${ROWS[@]}"; do
  printf '%s\n' "$ROW"
done
printf '\n'
if [ "$FAILS" -gt 0 ]; then
  printf 'verify-setup: %d hard FAIL(s) -- fix before enabling timers or the runner.\n' "$FAILS"
  exit 1
fi
printf 'verify-setup: no hard failures (WARNs above are pending manual steps).\n'
exit 0
