#!/usr/bin/env bash
# install-runner.sh -- self-hosted GitHub Actions runner for
# ZeOoba/oxford-command-center (full 'npm run gate' incl. reconcile +
# warehouse:verify, which need the local data corpus).
#
# CAUTION -- CONFIDENTIALITY:
#   This runner sees the confidential data paths (WORKBOOK_PATH /
#   FINANCIALS_DIR). The repository MUST stay PRIVATE: on a public repo,
#   fork PRs would execute arbitrary workflow code next to the corpus.
#   Workflow logs print property names and NOI matrices (warehouse-verify
#   prints the NOI matrix) -- restrict who can read Actions logs.
#   Never add this runner to any other repository.
#
# Usage:
#   RUNNER_TOKEN=<token> bash install-runner.sh
#   bash install-runner.sh --token <token>
# Mint the (short-lived) registration token here:
#   https://github.com/ZeOoba/oxford-command-center/settings/actions/runners/new?arch=x64&os=linux
#
# Idempotent: an already-configured runner (~/actions-runner-occ/.runner)
# skips download+config; the service install is detected via svc.sh status.
#
# Runner job env: the runner exports every VAR=value line found in its .env
# file (~/actions-runner-occ/.env) into each job. This script sources
# ~/.config/ora/ora.env and appends exactly these lines (values inlined):
#   WORKBOOK_PATH=<value from ora.env>
#   FINANCIALS_DIR=<value from ora.env>
#   WAREHOUSE_DB=<value from ora.env>    (optional; enables live drift check)
# A workflow job then targets it with:  runs-on: [self-hosted, linux, ora-data]
# ASCII only. shellcheck-clean.

set -euo pipefail

REPO_URL="https://github.com/ZeOoba/oxford-command-center"
MINT_URL="https://github.com/ZeOoba/oxford-command-center/settings/actions/runners/new?arch=x64&os=linux"
RUNNER_DIR="$HOME/actions-runner-occ"
FALLBACK_VER="2.325.0"

TOKEN="${RUNNER_TOKEN:-}"
while [ $# -gt 0 ]; do
  case "$1" in
    --token)   TOKEN="${2:-}"; shift 2 ;;
    --token=*) TOKEN="${1#--token=}"; shift ;;
    *) echo "install-runner: unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [ -f "$RUNNER_DIR/.runner" ]; then
  echo "runner already configured at $RUNNER_DIR (delete .runner to reconfigure)"
else
  if [ -z "$TOKEN" ]; then
    echo "install-runner: no registration token." >&2
    echo "Mint one (repo admin, expires in ~1 hour) at:" >&2
    echo "  $MINT_URL" >&2
    echo "then re-run:  RUNNER_TOKEN=<token> bash install-runner.sh" >&2
    exit 1
  fi

  # ------------------------------------------------------------- download
  if [ ! -x "$RUNNER_DIR/config.sh" ]; then
    mkdir -p "$RUNNER_DIR"
    VER="$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest 2>/dev/null | jq -r '.tag_name' 2>/dev/null | sed 's/^v//')" || VER=""
    if [ -z "$VER" ] || [ "$VER" = "null" ]; then
      VER="$FALLBACK_VER"
      echo "could not query latest runner release; using pinned $VER"
    fi
    TARBALL="actions-runner-linux-x64-$VER.tar.gz"
    echo "downloading actions-runner $VER ..."
    curl -fL -o "$RUNNER_DIR/$TARBALL" "https://github.com/actions/runner/releases/download/v$VER/$TARBALL"
    tar -xzf "$RUNNER_DIR/$TARBALL" -C "$RUNNER_DIR"
    rm -f "$RUNNER_DIR/$TARBALL"
  fi

  # ------------------------------------------------------------ configure
  (
    cd "$RUNNER_DIR"
    ./config.sh \
      --url "$REPO_URL" \
      --token "$TOKEN" \
      --labels self-hosted,linux,ora-data \
      --name "$(hostname)-occ" \
      --unattended \
      --replace
  )
fi

# -------------------------------------------- job env from ~/.config/ora
ORA_ENV="$HOME/.config/ora/ora.env"
RUNNER_ENV="$RUNNER_DIR/.env"
if [ -f "$ORA_ENV" ]; then
  set -a
  # shellcheck source=/dev/null
  . "$ORA_ENV"
  set +a
  touch "$RUNNER_ENV"
  chmod 600 "$RUNNER_ENV"
  for VAR in WORKBOOK_PATH FINANCIALS_DIR WAREHOUSE_DB; do
    VAL="$(eval "printf '%s' \"\${$VAR:-}\"")"
    if [ -z "$VAL" ]; then
      echo "skipping $VAR (not set in ora.env)"
      continue
    fi
    if grep -q "^$VAR=" "$RUNNER_ENV" 2>/dev/null; then
      TMP="$RUNNER_ENV.tmp"
      grep -v "^$VAR=" "$RUNNER_ENV" > "$TMP" || true
      mv "$TMP" "$RUNNER_ENV"
    fi
    printf '%s=%s\n' "$VAR" "$VAL" >> "$RUNNER_ENV"
    echo "runner .env: exported $VAR"
  done
  # Re-assert 600: the grep-into-tmp + mv rewrite above replaces the file with
  # one created under the default umask (0644), which would expose the inlined
  # confidential data paths to other local users. Runner jobs read it either way.
  chmod 600 "$RUNNER_ENV"
else
  echo "WARN: $ORA_ENV missing -- runner jobs will not see WORKBOOK_PATH/FINANCIALS_DIR (full gate will fail); re-run after provisioning secrets" >&2
fi

# ------------------------------------------------------- systemd service
# Mirror provision.sh's sudo probe: svc.sh needs root. Without working sudo,
# degrade to a printed manual step rather than aborting under set -e -- the
# runner is already registered (config.sh consumed the one-shot token above),
# so aborting here would waste that token on the next re-run.
HAVE_SUDO=0
if command -v sudo >/dev/null 2>&1; then
  if sudo -n true 2>/dev/null; then
    HAVE_SUDO=1
  elif [ -t 0 ] && sudo -v; then
    HAVE_SUDO=1
  fi
fi

cd "$RUNNER_DIR"
if [ "$HAVE_SUDO" -ne 1 ]; then
  echo "WARN: sudo unavailable -- cannot install/restart the runner service. Run manually:" >&2
  echo "  sudo $RUNNER_DIR/svc.sh install $(id -un)" >&2
  echo "  sudo $RUNNER_DIR/svc.sh start" >&2
elif sudo ./svc.sh status >/dev/null 2>&1; then
  # Already installed: restart so the rewritten .env is re-read by the job runner.
  echo "runner service already installed -- restarting to pick up .env changes"
  sudo ./svc.sh stop || true
  sudo ./svc.sh start || true
  sudo ./svc.sh status || true
else
  sudo ./svc.sh install "$(id -un)"
  sudo ./svc.sh start || true
  sudo ./svc.sh status || true
fi

echo ""
echo "install-runner: done. Verify at $REPO_URL/settings/actions/runners"
echo "Workflow jobs target this box with:  runs-on: [self-hosted, linux, ora-data]"
