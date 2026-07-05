#!/usr/bin/env bash
# rclone-sync.sh -- pull the two OneDrive data corpora onto the server.
#
# Direction is ONE-WAY, read-only from the server's point of view:
#   OneDrive 'eric spreadsheets'    -> ~/ora-data/eric-spreadsheets
#   OneDrive 'Property Financials'  -> ~/ora-data/property-financials
# 'rclone sync' makes the destination MIRROR the source (server-side edits
# and strays are deleted) -- never hand-edit ~/ora-data.
#
# Refuses to run until the rclone remote 'onedrive-oxford' exists; the
# one-time device-code setup is printed. Supports --dry-run.
# Scheduled hourly by ora-data-sync.timer (see server/units/).
# Remote paths can be overridden via ORA_ONEDRIVE_SPREADSHEETS /
# ORA_ONEDRIVE_FINANCIALS in ~/.config/ora/ora.env.
# ASCII only. shellcheck-clean. Idempotent (sync is convergent).

set -euo pipefail

DRY_ARGS=()
for ARG in "$@"; do
  case "$ARG" in
    --dry-run) DRY_ARGS=(--dry-run) ;;
    *) echo "rclone-sync: unknown argument: $ARG (only --dry-run is supported)" >&2; exit 1 ;;
  esac
done

if ! command -v rclone >/dev/null 2>&1; then
  echo "rclone-sync: rclone is not installed. Install it with:" >&2
  echo "  sudo apt-get install -y rclone" >&2
  echo "(or the current upstream build: curl https://rclone.org/install.sh | sudo bash)" >&2
  exit 1
fi

if ! rclone listremotes 2>/dev/null | grep -qx 'onedrive-oxford:'; then
  cat >&2 <<'SETUP'
rclone-sync: remote 'onedrive-oxford' is not configured. One-time setup
(device-code flow -- works headless):
  1. On this server run:  rclone config
     n) new remote, name: onedrive-oxford, storage: onedrive
     leave client_id/client_secret blank; when asked "Use web browser to
     automatically authenticate?" answer NO (headless).
  2. rclone prints a command to run on a machine WITH a browser
     (rclone authorize "onedrive"); run it on the Windows desktop, sign in
     as ggoldberg@oxfordra.net, and paste the resulting token back here.
  3. Pick the OneDrive (business) drive for Oxford Capital Partners.
The token cache lands in ~/.config/rclone/rclone.conf -- treat it as a
secret (see server/SECRETS-MANIFEST.md).
SETUP
  exit 1
fi

SRC_SPREADSHEETS="${ORA_ONEDRIVE_SPREADSHEETS:-onedrive-oxford:eric spreadsheets}"
SRC_FINANCIALS="${ORA_ONEDRIVE_FINANCIALS:-onedrive-oxford:Property Financials}"
DST_SPREADSHEETS="$HOME/ora-data/eric-spreadsheets"
DST_FINANCIALS="$HOME/ora-data/property-financials"
mkdir -p "$DST_SPREADSHEETS" "$DST_FINANCIALS"

# ~$* excludes Office lock files (open workbook on the desktop).
COMMON_ARGS=(--exclude '~$*' --verbose)

echo "rclone-sync: '$SRC_SPREADSHEETS' -> $DST_SPREADSHEETS"
rclone sync "$SRC_SPREADSHEETS" "$DST_SPREADSHEETS" "${COMMON_ARGS[@]}" ${DRY_ARGS[@]+"${DRY_ARGS[@]}"}

echo "rclone-sync: '$SRC_FINANCIALS' -> $DST_FINANCIALS"
rclone sync "$SRC_FINANCIALS" "$DST_FINANCIALS" "${COMMON_ARGS[@]}" ${DRY_ARGS[@]+"${DRY_ARGS[@]}"}

echo "rclone-sync: done"
