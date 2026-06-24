#!/bin/bash
# Patchright Browser — Uninstaller
# Usage: bash uninstall.sh [--keep-data]
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo "╔═══════════════════════════════════════════╗"
echo "║    Patchright Browser — Uninstaller       ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

INSTALL_DIR="${PATCHRIGHT_HOME:-$HOME/.patchright-browser}"
KEEP_DATA=false

for arg in "$@"; do
    case $arg in
        --keep-data) KEEP_DATA=true ;;
    esac
done

if [ ! -d "$INSTALL_DIR" ]; then
    warn "Install dir not found: $INSTALL_DIR"
    exit 0
fi

# --- Kill running processes ---
pids=$(pgrep -f "patchright-bridge.py" 2>/dev/null || true)
if [ -n "$pids" ]; then
    warn "Killing bridge processes: $pids"
    kill $pids 2>/dev/null || true
    sleep 1
fi

pids=$(pgrep -f "dashboard.py" 2>/dev/null || true)
if [ -n "$pids" ]; then
    warn "Killing dashboard processes: $pids"
    kill $pids 2>/dev/null || true
    sleep 1
fi
info "Processes stopped"

# --- Remove bridge files ---
rm -f "$INSTALL_DIR/start.sh"
rm -f "$INSTALL_DIR/start-dashboard.sh"
rm -f "$INSTALL_DIR/bin/patchright-bridge.py"
rm -rf "$INSTALL_DIR/lib"
rm -f "$INSTALL_DIR/dashboard.py"
info "Bridge files removed"

# --- Remove data (optional) ---
if [ "$KEEP_DATA" = false ]; then
    rm -rf "$INSTALL_DIR/profiles"
    rm -rf "$INSTALL_DIR/configs"
    rm -rf "$INSTALL_DIR/thumbnails"
    rm -f "$INSTALL_DIR/profiles.json"
    rm -f "$INSTALL_DIR/proxies.json"
    info "Profile data removed"
else
    info "Profile data kept (--keep-data)"
fi

# --- Clean empty dirs ---
[ -d "$INSTALL_DIR/bin" ] && rmdir "$INSTALL_DIR/bin" 2>/dev/null || true
[ -d "$INSTALL_DIR/logs" ] && rmdir "$INSTALL_DIR/logs" 2>/dev/null || true

echo ""
info "Uninstallation complete!"
echo ""
if [ "$KEEP_DATA" = true ]; then
    echo "  Profile data kept at: $INSTALL_DIR/profiles/"
    echo "  To fully remove: rm -rf $INSTALL_DIR"
else
    echo "  All files removed from: $INSTALL_DIR"
fi
echo ""
echo "  Hermes config: remove 'patchright:' section from ~/.hermes/config.yaml"
echo ""
