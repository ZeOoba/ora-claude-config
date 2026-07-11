#!/bin/bash
# UUID drift detection for ORA skill audit — run anytime to check if Claude Desktop
# has regenerated its local-agent-mode skills-plugin directory. If drift is detected,
# the AppData skill installs are stale and need to be re-synced from Cowork OS
# (the authoritative source).
#
# Environment: Git Bash / MSYS2 on Windows. Adjust paths if porting to WSL2.

BASELINE_FILE="$HOME/.claude/uuid-baseline.json"
COWORK_ROOT="/c/Users/Owner/OneDrive - Oxford Capital Partners (1)/Cowork OS/.claude/skills"
APPDATA_SEARCH_ROOT="/c/Users/Owner/AppData/Roaming/Claude/local-agent-mode-sessions/skills-plugin"

if [ ! -f "$BASELINE_FILE" ]; then
  echo "✗ No baseline found at $BASELINE_FILE — run the UUID baseline capture first"
  exit 1
fi

# Discover current AppData skills dir (find first skills/ two levels deep under skills-plugin)
CURRENT_APPDATA=$(find "$APPDATA_SEARCH_ROOT" -maxdepth 3 -type d -name "skills" 2>/dev/null | head -1)
if [ -z "$CURRENT_APPDATA" ]; then
  echo "⚠ No AppData skills dir found under $APPDATA_SEARCH_ROOT"
  echo "  Either Claude Desktop is uninstalled or the directory structure changed."
  echo "  Cowork OS skills at $COWORK_ROOT remain valid."
  exit 1
fi

CURRENT_OUTER=$(echo "$CURRENT_APPDATA" | sed 's|.*skills-plugin/\([^/]*\)/.*|\1|')
CURRENT_INNER=$(echo "$CURRENT_APPDATA" | sed 's|.*skills-plugin/[^/]*/\([^/]*\)/skills|\1|')

# Parse baseline values (simple grep — avoid jq dependency)
BASELINE_OUTER=$(grep '"outer_uuid"' "$BASELINE_FILE" | head -1 | sed 's/.*: "\([^"]*\)".*/\1/')
BASELINE_INNER=$(grep '"inner_uuid"' "$BASELINE_FILE" | head -1 | sed 's/.*: "\([^"]*\)".*/\1/')

echo "=== UUID Drift Check ==="
echo "Baseline outer: $BASELINE_OUTER"
echo "Current outer:  $CURRENT_OUTER"
echo "Baseline inner: $BASELINE_INNER"
echo "Current inner:  $CURRENT_INNER"
echo

DRIFT=false
if [ "$CURRENT_OUTER" != "$BASELINE_OUTER" ]; then
  echo "✗ OUTER UUID CHANGED — Claude Desktop skills-plugin install regenerated"
  DRIFT=true
fi
if [ "$CURRENT_INNER" != "$BASELINE_INNER" ]; then
  echo "✗ INNER UUID CHANGED — skill-set directory regenerated"
  DRIFT=true
fi

if [ "$DRIFT" = "true" ]; then
  echo
  echo "ACTION REQUIRED: AppData skill installs may be stale."
  echo "Re-sync from Cowork OS (the authoritative source) with:"
  echo
  echo "  for s in underwrite acquisition-underwriting document-assembly lease-abstraction-pipeline monthly-close; do"
  echo "    cp \"$COWORK_ROOT/\$s/SKILL.md\" \"$CURRENT_APPDATA/\$s/SKILL.md\""
  echo "  done"
  echo
  echo "Then re-run this script to confirm and update the baseline."
  exit 1
fi

# UUIDs match — also sanity-check file hashes
echo "✓ UUIDs match baseline — checking per-skill hashes…"
DRIFT_FILE=0
for s in underwrite acquisition-underwriting document-assembly lease-abstraction-pipeline monthly-close; do
  cf="$COWORK_ROOT/$s/SKILL.md"
  af="$CURRENT_APPDATA/$s/SKILL.md"
  if [ ! -f "$af" ]; then
    echo "  ✗ $s — missing in AppData"
    DRIFT_FILE=$((DRIFT_FILE+1))
    continue
  fi
  if [ ! -f "$cf" ]; then
    echo "  ⚠ $s — missing in Cowork (not promoted)"
    continue
  fi
  ch=$(md5sum "$cf" | awk '{print $1}')
  ah=$(md5sum "$af" | awk '{print $1}')
  if [ "$ch" = "$ah" ]; then
    echo "  ✓ $s — consistent ($ch)"
  else
    echo "  ✗ $s — HASH DRIFT (cowork=$ch vs appdata=$ah)"
    DRIFT_FILE=$((DRIFT_FILE+1))
  fi
done

if [ "$DRIFT_FILE" -eq 0 ]; then
  echo
  echo "✓ All checks pass. AppData installs remain valid."
  exit 0
else
  echo
  echo "✗ $DRIFT_FILE skills show hash drift — Cowork OS is authoritative; re-sync to AppData:"
  echo "  for s in underwrite acquisition-underwriting document-assembly lease-abstraction-pipeline monthly-close; do"
  echo "    cp \"$COWORK_ROOT/\$s/SKILL.md\" \"$CURRENT_APPDATA/\$s/SKILL.md\""
  echo "  done"
  exit 1
fi
