#!/usr/bin/env bash
# Chahlie Steam Deck — standalone installer (from release tarball)
# No git. No PyAudio compile. Just run: ./install.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${CHAHLIE_HOME:-$HOME/.local/share/chahlie}"
VENV_DIR="$INSTALL_DIR/venv"
BIN_LINK="$HOME/.local/bin/chahlie-deck"
RUN_LINK="$HOME/.local/bin/run-chahlie-deck"

echo ""
echo "  ⚾ Chahlie Steam Deck Edition"
echo "  ============================="
echo ""

# --- System packages (SteamOS / Arch) — prebuilt, no gcc needed ---
if command -v pacman &>/dev/null; then
    echo "→ Installing system audio packages (sudo password may be needed)..."
    sudo pacman -S --needed --noconfirm \
        pipewire-pulse \
        espeak-ng \
        python-pip \
        2>/dev/null || {
        echo ""
        echo "  Could not install system packages automatically."
        echo "  Run this manually, then re-run ./install.sh:"
        echo "    sudo pacman -S pipewire-pulse espeak-ng python-pip"
        echo ""
        exit 1
    }
fi

mkdir -p "$INSTALL_DIR" "$HOME/.local/bin"

# --- Python venv ---
if [[ ! -d "$VENV_DIR" ]]; then
    echo "→ Creating Python environment..."
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "→ Installing Chahlie (no compiler required)..."
pip install --upgrade pip wheel setuptools
pip install -e "$ROOT"
pip install -r "$ROOT/requirements-deck.txt"

# --- Config ---
if [[ ! -f "$INSTALL_DIR/.env" ]]; then
    cp "$ROOT/.env.deck.example" "$INSTALL_DIR/.env"
    echo "→ Created config at $INSTALL_DIR/.env"
    echo "  IMPORTANT: add your OLLAMA_API_KEY before launching!"
fi

# --- Launchers ---
cat > "$BIN_LINK" << LAUNCHER
#!/usr/bin/env bash
export CHAHLIE_PLUGINS_DIR="\${CHAHLIE_PLUGINS_DIR:-\$HOME/.chahlie/plugins}"
set -a
source "$INSTALL_DIR/.env"
set +a
exec "$VENV_DIR/bin/python" -m chahlie --deck "\$@"
LAUNCHER
chmod +x "$BIN_LINK"
cp "$BIN_LINK" "$RUN_LINK" 2>/dev/null || true

# Copy run script into install dir too
cp "$ROOT/run-chahlie-deck.sh" "$INSTALL_DIR/run.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/run.sh" 2>/dev/null || true

# --- Desktop shortcut ---
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/chahlie-deck.desktop" << DESKTOP
[Desktop Entry]
Name=Chahlie (Steam Deck)
Comment=Boston coding agent — voice + gamepad UI
Exec=$BIN_LINK
Icon=utilities-terminal
Terminal=true
Type=Application
Categories=Development;Utility;
StartupNotify=true
DESKTOP

echo ""
echo "  ✓ Installed successfully!"
echo ""
echo "  Next steps:"
echo "    1. nano $INSTALL_DIR/.env     # add OLLAMA_API_KEY"
echo "    2. chahlie-deck               # launch"
echo ""
echo "  Or find 'Chahlie (Steam Deck)' in your app menu."
echo ""
