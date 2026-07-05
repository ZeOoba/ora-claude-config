#!/usr/bin/env bash
# provision.sh -- one-shot Ubuntu 24.04 setup for the ORA Linux server.
#
# Run as the LOGIN user (not root); sudo is used only where needed and its
# availability is checked first. Idempotent: safe to re-run at any time --
# every step detects "already done" and moves on.
#
# What it does (in order):
#   1. apt packages (git curl ripgrep python3 python3-venv jq sqlite3
#      build-essential unzip)
#   2. server timezone -> America/New_York (user timers fire in LOCAL time)
#   3. Node 22 via fnm; Claude Code via the native installer
#   4. git identity (env GIT_AUTHOR_NAME/GIT_AUTHOR_EMAIL, or prompt)
#   5. clone ZeOoba repos: ora-claude-config -> ~/.claude,
#      oxford-command-center, ora-skills, BrainVault (SSH first, HTTPS
#      fallback; on auth failure prints the manual step and CONTINUES)
#   6. data dirs ~/ora-data/{eric-spreadsheets,property-financials};
#      ~/.config/ora/ora.env seeded from server/secrets.env.example (600)
#   7. pre-push confidentiality shim into every repo (fail-closed egress
#      gate; hooks/install-prepush.sh)
#   8. npm install in ~/oxford-command-center
#   9. systemd --user units installed + daemon-reload + linger. Timers are
#      NOT enabled -- that is gated on verify-setup.sh passing (see the
#      NEXT STEPS block this script prints).
#  10. ufw guidance is PRINTED ONLY -- network policy is operator-owned.
#
# EOS doctrine note: this is a productivity script -- individual optional
# steps degrade to a printed manual step instead of aborting the run, but
# the confidentiality shim install failures are surfaced loudly.
# ASCII only. shellcheck-clean.

set -euo pipefail

log()  { printf '\n=== %s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SELF_USER="$(id -un)"

MANUAL_STEPS=()
add_manual() { MANUAL_STEPS+=("$1"); }

# ---------------------------------------------------------------- sudo check
HAVE_SUDO=0
if command -v sudo >/dev/null 2>&1; then
  if sudo -n true 2>/dev/null; then
    HAVE_SUDO=1
  elif [ -t 0 ] && sudo -v; then
    HAVE_SUDO=1
  fi
fi
if [ "$HAVE_SUDO" -ne 1 ]; then
  warn "sudo unavailable -- apt install, timezone, and linger steps will be skipped"
  add_manual "re-run provision.sh with working sudo (apt packages, timezone, linger were skipped)"
fi

# ------------------------------------------------------------- apt packages
if [ "$HAVE_SUDO" -eq 1 ]; then
  log "apt packages"
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    git curl ripgrep python3 python3-venv jq sqlite3 build-essential unzip
fi

# ----------------------------------------------------------------- timezone
# systemd USER timers fire in the server's LOCAL timezone. The heartbeat
# cadence (06:00/18:00) and every other OnCalendar in server/units/ assume
# America/New_York -- the GitHub watchdog's 16h threshold depends on it.
log "timezone"
if command -v timedatectl >/dev/null 2>&1; then
  TZ_NOW="$(timedatectl show -p Timezone --value 2>/dev/null || true)"
  if [ "$TZ_NOW" = "America/New_York" ]; then
    echo "timezone already America/New_York"
  elif [ "$HAVE_SUDO" -eq 1 ] && sudo timedatectl set-timezone America/New_York; then
    echo "timezone set to America/New_York (was: ${TZ_NOW:-unknown})"
  else
    add_manual "sudo timedatectl set-timezone America/New_York  # user timers fire in LOCAL time; the 06,18:00 heartbeat cadence must be ET"
  fi
else
  add_manual "set the system timezone to America/New_York (timedatectl not found)"
fi

# --------------------------------------------------------- Node 22 via fnm
log "Node 22 via fnm"
FNM_DIR="$HOME/.local/share/fnm"
if ! command -v fnm >/dev/null 2>&1 && [ ! -x "$FNM_DIR/fnm" ]; then
  curl -fsSL https://fnm.vercel.app/install | bash -s -- --install-dir "$FNM_DIR" --skip-shell
fi
export PATH="$FNM_DIR:$PATH"
if command -v fnm >/dev/null 2>&1; then
  eval "$(fnm env)"
  fnm install 22
  fnm default 22
  # Idempotent shell init (the systemd units do NOT rely on this -- they
  # source fnm themselves via server/run-full-gate.sh).
  if ! grep -q 'fnm env' "$HOME/.bashrc" 2>/dev/null; then
    {
      echo ''
      echo '# fnm (installed by ora provision.sh)'
      # shellcheck disable=SC2016  # literal $HOME/$(...) must expand at shell startup, not now
      echo 'export PATH="$HOME/.local/share/fnm:$PATH"'
      # shellcheck disable=SC2016
      echo 'command -v fnm >/dev/null 2>&1 && eval "$(fnm env)"'
    } >> "$HOME/.bashrc"
  fi
  echo "node: $(node --version 2>/dev/null || echo 'NOT ON PATH')"
else
  warn "fnm install failed"
  add_manual "install Node 22: curl -fsSL https://fnm.vercel.app/install | bash && fnm install 22 && fnm default 22"
fi

# ------------------------------------------------------------- git identity
log "git identity"
if [ -z "$(git config --global user.name 2>/dev/null || true)" ]; then
  if [ -n "${GIT_AUTHOR_NAME:-}" ]; then
    git config --global user.name "$GIT_AUTHOR_NAME"
  elif [ -t 0 ]; then
    read -r -p "git user.name (e.g. Gabriel Goldberg): " GIT_NAME_IN
    [ -n "$GIT_NAME_IN" ] && git config --global user.name "$GIT_NAME_IN"
  else
    add_manual "git config --global user.name 'Gabriel Goldberg'"
  fi
fi
if [ -z "$(git config --global user.email 2>/dev/null || true)" ]; then
  if [ -n "${GIT_AUTHOR_EMAIL:-}" ]; then
    git config --global user.email "$GIT_AUTHOR_EMAIL"
  elif [ -t 0 ]; then
    read -r -p "git user.email (e.g. ggoldberg@oxfordra.net): " GIT_EMAIL_IN
    [ -n "$GIT_EMAIL_IN" ] && git config --global user.email "$GIT_EMAIL_IN"
  else
    add_manual "git config --global user.email 'ggoldberg@oxfordra.net'"
  fi
fi

# ------------------------------------------------------------------- clones
# SSH first (the long-term auth path: deploy key / user key), HTTPS fallback
# (works with gh auth or a PAT credential helper). On failure: print the
# exact manual step and CONTINUE -- a fresh box often has no key yet.
clone_repo() {
  # $1 = repo name under ZeOoba/, $2 = destination dir
  REPO_NAME="$1"
  DEST="$2"
  if [ -d "$DEST/.git" ]; then
    echo "already cloned: $DEST"
    return 0
  fi
  if [ -e "$DEST" ] && [ -n "$(ls -A "$DEST" 2>/dev/null)" ]; then
    warn "$DEST exists, is not empty, and is not a git repo -- not touching it"
    add_manual "mv '$DEST' '$DEST.bak' && git clone git@github.com:ZeOoba/$REPO_NAME.git '$DEST'  # then copy any local-only files (e.g. .credentials.json) back from the .bak"
    return 0
  fi
  if git clone "git@github.com:ZeOoba/$REPO_NAME.git" "$DEST" 2>/dev/null; then
    return 0
  fi
  warn "SSH clone failed for $REPO_NAME (no key yet?) -- trying HTTPS"
  if git clone "https://github.com/ZeOoba/$REPO_NAME.git" "$DEST"; then
    return 0
  fi
  warn "clone failed for ZeOoba/$REPO_NAME"
  add_manual "authenticate to GitHub (ssh-keygen -t ed25519 && add the key at https://github.com/settings/keys, or 'gh auth login'), then: git clone git@github.com:ZeOoba/$REPO_NAME.git '$DEST'"
  return 0
}

log "repos"
clone_repo ora-claude-config "$HOME/.claude"
clone_repo oxford-command-center "$HOME/oxford-command-center"
clone_repo ora-skills "$HOME/ora-skills"
clone_repo BrainVault "$HOME/BrainVault"

# ------------------------------------------------- data dirs + ora.env seed
log "data dirs + ~/.config/ora/ora.env"
mkdir -p "$HOME/ora-data/eric-spreadsheets" "$HOME/ora-data/property-financials" "$HOME/.config/ora"
ENV_FILE="$HOME/.config/ora/ora.env"
EXAMPLE="$SCRIPT_DIR/secrets.env.example"
[ -f "$EXAMPLE" ] || EXAMPLE="$HOME/.claude/server/secrets.env.example"
if [ -f "$ENV_FILE" ]; then
  echo "ora.env already present (not overwritten)"
elif [ -f "$EXAMPLE" ]; then
  # /home/YOURUSER placeholders become the real home dir here because
  # systemd EnvironmentFile does NOT expand $HOME or ~.
  sed "s|/home/YOURUSER|$HOME|g" "$EXAMPLE" > "$ENV_FILE"
  echo "seeded $ENV_FILE from secrets.env.example -- fill in real values"
else
  warn "secrets.env.example not found (is ~/.claude cloned?)"
  add_manual "create $ENV_FILE from ~/.claude/server/secrets.env.example and chmod 600 it"
fi
chmod 600 "$ENV_FILE" 2>/dev/null || true

# ------------------------------------------ pre-push confidentiality shims
# FAIL-CLOSED egress gate (2026-06-11 incident remediation): every push in
# every repo runs the full-history confidential scan. Clones do not carry
# .git/hooks, so this must run on every fresh checkout.
log "pre-push confidentiality shims"
INSTALLER="$HOME/.claude/hooks/install-prepush.sh"
if [ -f "$INSTALLER" ]; then
  for REPO in "$HOME/.claude" "$HOME/oxford-command-center" "$HOME/ora-skills" "$HOME/BrainVault"; do
    if [ -d "$REPO/.git" ]; then
      if ! bash "$INSTALLER" "$REPO"; then
        warn "pre-push shim install FAILED for $REPO (confidentiality gate!)"
        add_manual "bash ~/.claude/hooks/install-prepush.sh '$REPO'  # FAIL-CLOSED egress gate -- do not push from this repo until installed"
      fi
    fi
  done
else
  warn "install-prepush.sh not found -- ~/.claude clone missing?"
  add_manual "after cloning ~/.claude: bash ~/.claude/hooks/install-prepush.sh <each repo>"
fi

# -------------------------------------------------------------- Claude Code
log "Claude Code"
export PATH="$HOME/.local/bin:$PATH"
if command -v claude >/dev/null 2>&1; then
  echo "claude already installed: $(claude --version 2>/dev/null || echo present)"
else
  curl -fsSL https://claude.ai/install.sh | bash || {
    warn "Claude Code install failed"
    add_manual "install Claude Code: curl -fsSL https://claude.ai/install.sh | bash"
  }
fi
if ! command -v claude >/dev/null 2>&1; then
  add_manual "put ~/.local/bin on PATH (claude binary) -- re-login or add to ~/.bashrc"
fi

# -------------------------------------------------------------- npm install
log "npm install in ~/oxford-command-center (compiles better-sqlite3; can take minutes)"
if [ -d "$HOME/oxford-command-center" ] && command -v npm >/dev/null 2>&1; then
  (cd "$HOME/oxford-command-center" && npm install --no-fund --no-audit) || {
    warn "npm install failed"
    add_manual "cd ~/oxford-command-center && npm install"
  }
else
  add_manual "cd ~/oxford-command-center && npm install  # skipped (repo or npm missing)"
fi

# ------------------------------------------------------- systemd user units
log "systemd --user units"
UNIT_SRC="$SCRIPT_DIR/units"
[ -d "$UNIT_SRC" ] || UNIT_SRC="$HOME/.claude/server/units"
if [ -d "$UNIT_SRC" ]; then
  mkdir -p "$HOME/.config/systemd/user"
  cp "$UNIT_SRC"/*.service "$UNIT_SRC"/*.timer "$HOME/.config/systemd/user/"
  echo "installed: $(cd "$UNIT_SRC" && printf '%s ' -- *.service *.timer)"
  systemctl --user daemon-reload 2>/dev/null || {
    warn "systemctl --user unavailable (no user bus in this shell?)"
    add_manual "log in as $SELF_USER over ssh and run: systemctl --user daemon-reload"
  }
  # Linger: user units must run without an open login session.
  if loginctl enable-linger "$SELF_USER" 2>/dev/null; then
    echo "linger enabled for $SELF_USER"
  elif [ "$HAVE_SUDO" -eq 1 ] && sudo loginctl enable-linger "$SELF_USER"; then
    echo "linger enabled for $SELF_USER (via sudo)"
  else
    add_manual "sudo loginctl enable-linger $SELF_USER  # timers must fire with no login session open"
  fi
  echo "NOTE: timers are installed but NOT enabled -- enable only after verify-setup.sh passes (see NEXT STEPS)."
else
  warn "server/units not found -- ~/.claude clone missing?"
  add_manual "cp ~/.claude/server/units/* ~/.config/systemd/user/ && systemctl --user daemon-reload"
fi

# ------------------------------------------------------------- ufw guidance
log "firewall guidance (NOT applied -- network policy is operator-owned)"
cat <<'UFW'
Suggested ufw baseline (run manually if this box should be locked down):
  sudo ufw default deny incoming
  sudo ufw default allow outgoing
  sudo ufw allow OpenSSH
  sudo ufw enable
The oxford-command-center server binds 127.0.0.1 ONLY (CLAUDE.md section 9).
Do NOT open port 8911; reach it via an SSH tunnel instead:
  ssh -L 8911:127.0.0.1:8911 <user>@<server>
UFW

# --------------------------------------------------------------- NEXT STEPS
log "NEXT STEPS (manual, in order -- see server/README.md + server/SECRETS-MANIFEST.md)"
cat <<'STEPS'
  1. SECRETS (out-of-band ONLY -- never via git/OneDrive/email):
       - edit ~/.config/ora/ora.env with real values (stays mode 600)
       - place ~/.claude/hooks/confidential-terms.json  (fail-closed egress
         guard; sessions and pushes are limited until it exists)
       - place ~/.claude/.credentials.json if reusing desktop Claude auth
  2. CLAUDE AUTH: run 'claude' once and log in (device flow), then check:
       claude -p 'reply OK' --output-format text
  3. DATA CORPUS (pick one):
       a) server pull:  rclone config   (one-time device-code auth for the
          'onedrive-oxford' remote), then bash ~/.claude/server/rclone-sync.sh
       b) desktop push: run server/desktop-push-data.ps1 on the Windows box
  4. VERIFY: bash ~/.claude/server/verify-setup.sh   (fix every FAIL)
  5. ENABLE TIMERS (only after verify passes):
       systemctl --user enable --now ora-heartbeat.timer ora-vault-backup.timer \
         ora-telemetry-rollup.timer ora-full-gate.timer ora-data-sync.timer
  6. GITHUB RUNNER: mint a token at
       https://github.com/ZeOoba/oxford-command-center/settings/actions/runners/new?arch=x64&os=linux
     then: RUNNER_TOKEN=<token> bash ~/.claude/server/install-runner.sh
STEPS

if [ "${#MANUAL_STEPS[@]}" -gt 0 ]; then
  printf '\nADDITIONAL MANUAL ITEMS from this run:\n'
  for STEP in "${MANUAL_STEPS[@]}"; do
    printf '  - %s\n' "$STEP"
  done
fi

log "provision complete"
