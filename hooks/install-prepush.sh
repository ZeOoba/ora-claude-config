#!/bin/sh
# ORA portable git pre-push shim installer.
# Usage: install-prepush.sh /path/to/repo [--force]
# Writes .git/hooks/pre-push (executable) so every push in that repo runs
# ~/.claude/hooks/git-prepush-confidential-scan.py (fail-closed history scan;
# 2026-06-11 incident remediation). The shim resolves python3 -> python and
# BLOCKS the push if no interpreter is found (fail-closed, exit 1).
# Refuses (exit 1) if the target is not a git repo, and refuses to overwrite
# a DIFFERENT existing pre-push hook unless --force is given.
# POSIX sh; works from Git Bash on Windows and sh on Linux. ASCII only.

REPO=$1
if [ -z "$REPO" ]; then
  echo "usage: install-prepush.sh /path/to/repo [--force]" >&2
  exit 1
fi
FORCE=0
[ "$2" = "--force" ] && FORCE=1

GITDIR=$(git -C "$REPO" rev-parse --git-dir 2>/dev/null)
if [ -z "$GITDIR" ]; then
  echo "install-prepush: not a git repo: $REPO" >&2
  exit 1
fi
# rev-parse may return a path relative to the repo root; anchor it.
case "$GITDIR" in
  /*|[A-Za-z]:*) ;;
  *) GITDIR="$REPO/$GITDIR" ;;
esac
HOOK="$GITDIR/hooks/pre-push"

# shellcheck disable=SC2016  # single quotes are intentional: $PY/$HOME/$@ must expand at push time, not install time
SHIM='#!/bin/sh
PY=$(command -v python3 || command -v python)
[ -n "$PY" ] || { echo "pre-push: no python found - BLOCKING (fail-closed)" >&2; exit 1; }
exec "$PY" "$HOME/.claude/hooks/git-prepush-confidential-scan.py" "$@"
'

if [ -f "$HOOK" ]; then
  if printf '%s' "$SHIM" | cmp -s - "$HOOK"; then
    echo "install-prepush: pre-push shim already installed at $HOOK"
    exit 0
  fi
  if [ "$FORCE" -ne 1 ]; then
    echo "install-prepush: a DIFFERENT pre-push hook exists at $HOOK - refusing to overwrite (use --force)" >&2
    exit 1
  fi
fi

mkdir -p "$GITDIR/hooks" || exit 1
printf '%s' "$SHIM" > "$HOOK" || exit 1
chmod +x "$HOOK" || exit 1
echo "install-prepush: installed pre-push shim at $HOOK"
exit 0
