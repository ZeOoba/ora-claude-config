#!/bin/sh
# ORA RAM guard (Linux) -- called by ram-watchdog.sh once per 60s.
# Linux sibling of ram-guard.ps1. WARN-ONLY first cut:
#   free >= WARN_MB            -> silent
#   CRIT_MB <= free < WARN_MB  -> warn JSON (offer /solo or /heavy), no action
#   free < CRIT_MB             -> stronger warning JSON, still NO action.
# TODO(parking): v1 does NOT kill/park processes. A future v2 may replicate
# ram-guard.ps1's auto-park at the critical tier (scan `pgrep -a` for claude
# processes with --resume UUIDs, map to ~/.claude/projects/**/<sid>.jsonl
# mtimes, kill the most-idle non-current one with the same 900s idle floor).
# $1 = current session id (unused in warn-only v1; kept for signature parity
# with ram-guard.ps1 so the ram-watchdog.sh dispatch is identical per OS).
# Emits ONLY a JSON object on stdout (or nothing). Always exits 0. ASCII only.

WARN_MB=300
CRIT_MB=200

KB=$(awk '/^MemAvailable:/ {print $2; exit}' /proc/meminfo 2>/dev/null)
case "$KB" in
  ''|*[!0-9]*) exit 0 ;;  # unreadable/odd /proc/meminfo -> silent (never block)
esac
FREE=$((KB / 1024))

if [ "$FREE" -ge "$WARN_MB" ]; then
  exit 0
fi

if [ "$FREE" -ge "$CRIT_MB" ]; then
  # Warn tier: same JSON shape as ram-guard.ps1's WarnObj.
  printf '{"systemMessage":"Low RAM: %s MB free. Type /solo to move THIS session to a lean CLI (other sessions keep running), or /heavy.","hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"System RAM is low (%s MB free). Proactively tell Gabriel and offer to run /solo or /heavy. Do not run any command without his confirmation."}}' "$FREE" "$FREE"
else
  # Critical tier: stronger warning only -- no auto-park in v1 (see TODO above).
  printf '{"systemMessage":"RAM critical: %s MB free. Auto-parking is not enabled on Linux yet -- type /solo now or close idle sessions.","hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"System RAM is critically low (%s MB free). Urgently tell Gabriel; recommend /solo for this session or closing idle sessions now. Do not run any command without his confirmation."}}' "$FREE" "$FREE"
fi
exit 0
