#!/bin/sh
# ~/.claude pre-commit shim (template). Install: copy to .git/hooks/pre-commit.
# NOT version-controlled there (.git/hooks is dropped on every clone); this tracked copy
# is the source. FAIL-OPEN by construction: only the hook's own exit 10 (a deliberate
# block, exit 10) stops a commit. A missing hook file (older branch), a missing or aliased python
# (127 / 9009) or any crash (Python exits 1 on an uncaught exception) lets the commit through -- the event_log auto-commit and the
# memory sweep must never be blocked by tooling. -I: no hooks/ dir on sys.path.
ROOT="$(git rev-parse --show-toplevel)" || exit 0
HOOK="$ROOT/hooks/git-precommit-send-lint.py"
[ -f "$HOOK" ] || exit 0
command -v python >/dev/null 2>&1 || exit 0
python -I "$HOOK"
[ $? -eq 10 ] && exit 1
exit 0
