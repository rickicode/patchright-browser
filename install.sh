#!/bin/bash
# Patchright Browser — Installer
# Usage: bash install.sh
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo "╔═══════════════════════════════════════════╗"
echo "║     Patchright Browser — Installer        ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# --- Checks ---
[ "$(id -u)" -eq 0 ] && error "Don't run as root. Run as normal user."

command -v python3 >/dev/null || error "python3 not found. Install Python 3.10+"
command -v node >/dev/null || error "node not found. Install Node.js 18+"

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python $PYTHON_VER"

# --- Config ---
INSTALL_DIR="${PATCHRIGHT_HOME:-$HOME/.patchright-browser}"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
info "Install dir: $INSTALL_DIR"

# --- Create directories ---
mkdir -p "$INSTALL_DIR"/{profiles,configs,proxies,logs,thumbnails}
info "Directories created"

# --- Install Python deps ---
info "Installing Python dependencies..."
pip3 install --user --quiet mcp requests 2>/dev/null || pip3 install --break-system-packages --quiet mcp requests 2>/dev/null
info "Python deps installed"

# --- Create default profile if none exist ---
if [ ! -f "$INSTALL_DIR/profiles.json" ]; then
    python3 -c "
import json, os
data = {'default': 'default', 'profiles': {
    'default': {
        'name': 'default',
        'description': 'Default browser profile',
        'caps': ['vision'],
        'viewport': {'width': 1280, 'height': 800},
        'locale': 'en-US',
        'timezone': '$(cat /etc/timezone 2>/dev/null || echo 'UTC')',
        'tags': []
    }
}}
with open('$INSTALL_DIR/profiles.json', 'w') as f:
    json.dump(data, f, indent=2)
"
    info "Default profile created"
fi

# --- Copy bridge script ---
mkdir -p "$INSTALL_DIR/bin"
cp "$REPO_DIR/bin/patchright-bridge.py" "$INSTALL_DIR/bin/"
cp -r "$REPO_DIR/lib" "$INSTALL_DIR/"
info "Bridge scripts installed"

# --- Install dashboard ---
cp "$REPO_DIR/dashboard.py" "$INSTALL_DIR/"
info "Dashboard installed"

# --- Create start script ---
cat > "$INSTALL_DIR/start.sh" << 'START'
#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
echo "Starting Patchright Bridge on port 9877..."
python3 bin/patchright-bridge.py "$@"
START
chmod +x "$INSTALL_DIR/start.sh"

# --- Create dashboard start script ---
cat > "$INSTALL_DIR/start-dashboard.sh" << 'DASH'
#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
PORT=${1:-9878}
echo "Starting Patchright Dashboard on port $PORT..."
python3 dashboard.py
DASH
chmod +x "$INSTALL_DIR/start-dashboard.sh"
info "Scripts created"

# --- Hermes config hint ---
echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║  Add to ~/.hermes/config.yaml:            ║"
echo "╚═══════════════════════════════════════════╝"
echo ""
echo "  patchright:"
echo "    url: http://127.0.0.1:9877/mcp/"
echo "    connect_timeout: 30"
echo "    enabled: true"
echo ""

# --- Done ---
info "Installation complete!"
echo ""
echo "  Start bridge:    $INSTALL_DIR/start.sh"
echo "  Start dashboard: $INSTALL_DIR/start-dashboard.sh"
echo "  Dashboard URL:   http://localhost:9878 (password: hijilabs7)"
echo "  Bridge URL:      http://127.0.0.1:9877/mcp/"
echo ""
