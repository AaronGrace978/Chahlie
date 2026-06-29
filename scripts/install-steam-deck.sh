#!/usr/bin/env bash
# Chahlie Steam Deck Edition — one-shot installer
# Run from Desktop Mode:  bash scripts/install-steam-deck.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_DIR="${CHAHLIE_HOME:-$HOME/.local/share/chahlie}"
VENV_DIR="$INSTALL_DIR/venv"
BIN_LINK="$HOME/.local/bin/chahlie-deck"

echo ""
echo "  ⚾ Chahlie Steam Deck Edition installer"
echo "  ========================================"
echo ""

# System packages for voice on SteamOS / Arch
if command -v pacman &>/dev/null; then
    echo "→ Checking system audio packages (may prompt for sudo)..."
    sudo pacman -S --needed --noconfirm portaudio espeak-ng 2>/dev/null || true
fi

mkdir -p "$INSTALL_DIR" "$HOME/.local/bin"

if [[ ! -d "$VENV_DIR" ]]; then
    echo "→ Creating Python venv at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "→ Installing Chahlie + Deck dependencies..."
pip install --upgrade pip wheel
pip install -e "$ROOT_DIR"
pip install -r "$ROOT_DIR/requirements-deck.txt"

# Config
if [[ ! -f "$INSTALL_DIR/.env" ]]; then
    if [[ -f "$ROOT_DIR/.env" ]]; then
        cp "$ROOT_DIR/.env" "$INSTALL_DIR/.env"
        echo "→ Copied existing .env to $INSTALL_DIR/.env"
    else
        cp "$ROOT_DIR/.env.deck.example" "$INSTALL_DIR/.env"
        echo "→ Created $INSTALL_DIR/.env — add your OLLAMA_API_KEY!"
    fi
fi

# Launcher script
cat > "$BIN_LINK" << LAUNCHER
#!/usr/bin/env bash
cd "$INSTALL_DIR"
export CHAHLIE_PLUGINS_DIR="\${CHAHLIE_PLUGINS_DIR:-\$HOME/.chahlie/plugins}"
set -a
source "$INSTALL_DIR/.env"
set +a
exec "$VENV_DIR/bin/python" -m chahlie --deck "\$@"
LAUNCHER
chmod +x "$BIN_LINK"

# Desktop shortcut
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
echo "  ✓ Installed!"
echo ""
echo "  Launch:  chahlie-deck"
echo "  Or find 'Chahlie (Steam Deck)' in your app menu."
echo ""
echo "  Add to Steam (Gaming Mode):"
echo "    Steam → Add Game → Non-Steam Game → chahlie-deck"
echo "    Map controls: A=Enter, B=Esc, X=F4 (Talk), Y=F1 (Help)"
echo ""
echo "  Edit config:  nano $INSTALL_DIR/.env"
echo ""
