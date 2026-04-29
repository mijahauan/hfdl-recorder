#!/bin/bash
# install.sh — first-run bootstrap for hfdl-recorder (Pattern A editable install)
#
# Usage: sudo ./scripts/install.sh [--pull] [--yes] [--no-build]
#
# What it does:
#   1. Creates service user hfdlrec:hfdlrec
#   2. Clones/links repo to /opt/git/sigmond/hfdl-recorder
#   3. Creates venv at /opt/hfdl-recorder/venv with editable install
#   4. Builds libacars + dumphfdl into /opt/hfdl-recorder/bin
#      (skip with --no-build if dumphfdl is already on disk)
#   5. Renders config template (non-destructive — never overwrites)
#   6. Installs systemd unit template
#   7. Disables the ka9q-radio hfdl.service if running (we replace it)
#   8. Enables hfdl-recorder@<radiod_id> instances from config
#
# Idempotent: safe to re-run.

set -euo pipefail

SERVICE_USER="hfdlrec"
SERVICE_GROUP="hfdlrec"
REPO_SOURCE="/opt/git/sigmond/hfdl-recorder"
PREFIX="/opt/hfdl-recorder"
VENV_DIR="${PREFIX}/venv"
CONFIG_DIR="/etc/hfdl-recorder"
CONFIG_FILE="${CONFIG_DIR}/hfdl-recorder-config.toml"
SPOOL_DIR="/var/lib/hfdl-recorder"
LOG_DIR="/var/log/hfdl-recorder"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ui_info()  { echo "[INFO]  $*"; }
ui_warn()  { echo "[WARN]  $*" >&2; }
ui_error() { echo "[ERROR] $*" >&2; }

# --- Phase 0: arg parsing ---
DO_PULL=false
AUTO_YES=false
DO_BUILD=true
for arg in "$@"; do
    case "$arg" in
        --pull)     DO_PULL=true ;;
        --yes)      AUTO_YES=true ;;
        --no-build) DO_BUILD=false ;;
    esac
done

if [[ $EUID -ne 0 ]]; then
    ui_error "Must run as root (sudo)"
    exit 1
fi

# --- Phase 1: service user ---
if ! id -u "$SERVICE_USER" &>/dev/null; then
    ui_info "Creating service user $SERVICE_USER"
    useradd --system --shell /usr/sbin/nologin \
            --home-dir /nonexistent --no-create-home \
            "$SERVICE_USER"
fi

# --- Phase 2: repo + venv ---
if [[ ! -d "$REPO_SOURCE" ]]; then
    ui_info "Linking $REPO_ROOT -> $REPO_SOURCE"
    mkdir -p "$(dirname "$REPO_SOURCE")"
    ln -sfn "$REPO_ROOT" "$REPO_SOURCE"
fi

# Traversability check (Pattern A defense)
if ! sudo -u "$SERVICE_USER" test -r "$REPO_SOURCE/src/hfdl_recorder/__init__.py"; then
    ui_error "Service user $SERVICE_USER cannot read $REPO_SOURCE/src/hfdl_recorder/__init__.py"
    ui_error "Fix: ensure the repo is at /opt/git/sigmond/hfdl-recorder (not under a mode-700 home)"
    ui_error "  or: chmod g+rx the path and add $SERVICE_USER to the owner's group"
    exit 1
fi

if $DO_PULL; then
    ui_info "Pulling latest from origin"
    git -C "$REPO_SOURCE" pull --ff-only
fi

if [[ ! -d "$VENV_DIR" ]]; then
    ui_info "Creating venv at $VENV_DIR"
    mkdir -p "$(dirname "$VENV_DIR")"
    python3 -m venv "$VENV_DIR"
fi

ui_info "Installing hfdl-recorder (editable) into venv"
"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel >/dev/null
"$VENV_DIR/bin/pip" install -e "$REPO_SOURCE" >/dev/null

# Post-install verify
if ! sudo -u "$SERVICE_USER" "$VENV_DIR/bin/python3" -c 'import hfdl_recorder' 2>/dev/null; then
    ui_error "Post-install verify failed: $SERVICE_USER cannot import hfdl_recorder"
    exit 1
fi
ui_info "Post-install verify OK"

# --- Phase 3: dumphfdl C build ---
if $DO_BUILD; then
    if [[ -x "$PREFIX/bin/dumphfdl" ]]; then
        ui_info "dumphfdl already at $PREFIX/bin/dumphfdl (use --no-build to skip, or scripts/build-dumphfdl.sh --force to rebuild)"
    else
        ui_info "Building dumphfdl (libacars + dumphfdl)"
        "$REPO_SOURCE/scripts/build-dumphfdl.sh"
    fi
else
    ui_info "Skipping dumphfdl build (--no-build)"
fi

# --- Phase 4: config ---
mkdir -p "$CONFIG_DIR"
if [[ ! -f "$CONFIG_FILE" ]]; then
    ui_info "Rendering config template -> $CONFIG_FILE"
    cp "$REPO_SOURCE/config/hfdl-recorder-config.toml.template" "$CONFIG_FILE"
    ui_warn "Edit $CONFIG_FILE with your station_id and radiod settings"
else
    ui_info "Config exists at $CONFIG_FILE — not overwriting"
fi

# --- Phase 5: directories ---
for dir in "$SPOOL_DIR" "$LOG_DIR"; do
    mkdir -p "$dir"
    chown "$SERVICE_USER:$SERVICE_GROUP" "$dir"
done

# --- Phase 6: systemd ---
ui_info "Installing systemd unit template"
install -o root -g root -m 644 \
    "$REPO_SOURCE/systemd/hfdl-recorder@.service" \
    /etc/systemd/system/hfdl-recorder@.service
systemctl daemon-reload

# --- Phase 7: disable ka9q-radio's hfdl.service if active ---
# ka9q-radio ships a `hfdl.service` that uses pcmrecord + start-hfdl.sh
# to spawn dumphfdl per band. We replace that whole pipeline.
if systemctl is-active --quiet hfdl.service 2>/dev/null; then
    ui_warn "Disabling ka9q-radio hfdl.service (hfdl-recorder replaces it)"
    systemctl disable --now hfdl.service
fi

# --- Phase 8: enable instances ---
ui_info "Parsing radiod IDs from $CONFIG_FILE"
RADIOD_IDS=$("$VENV_DIR/bin/python3" -c "
import tomllib
with open('$CONFIG_FILE', 'rb') as f:
    cfg = tomllib.load(f)
blocks = cfg.get('radiod', [])
if isinstance(blocks, dict):
    blocks = [blocks]
for b in blocks:
    print(b.get('id', 'default'))
" 2>/dev/null)

if [[ -z "$RADIOD_IDS" ]]; then
    ui_warn "No radiod IDs found in config — no instances enabled"
else
    for rid in $RADIOD_IDS; do
        ui_info "Enabling hfdl-recorder@${rid}.service"
        systemctl enable "hfdl-recorder@${rid}.service"
        ui_info "  (not starting — review $CONFIG_FILE first)"
    done
fi

ui_info "Install complete. Edit $CONFIG_FILE then start instances with:"
ui_info "  sudo systemctl start hfdl-recorder@<radiod-id>"
