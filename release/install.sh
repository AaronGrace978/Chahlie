#!/usr/bin/env bash
# Chahlie Steam Deck — standalone installer (from release tarball)
# No git. No PyAudio compile. Just run: ./install.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${CHAHLIE_HOME:-$HOME/.local/share/chahlie}"
VENV_DIR="$INSTALL_DIR/venv"
BIN_LINK="$HOME/.local/bin/chahlie-deck"
RUN_LINK="$HOME/.local/bin/run-chahlie-deck"

have_cmd() { command -v "$1" &>/dev/null; }

echo ""
echo "  ⚾ Chahlie Steam Deck Edition"
echo "  ============================="
echo ""

# --- Check what's already on the Deck (SteamOS ships most of this) ---
MISSING_PKGS=()
have_cmd pw-record || have_cmd parecord || MISSING_PKGS+=("pipewire-pulse")
have_cmd espeak-ng || have_cmd espeak || MISSING_PKGS+=("espeak-ng")

if [[ ${#MISSING_PKGS[@]} -eq 0 ]]; then
    echo "→ Audio tools already present (voice ready)."
elif command -v pacman &>/dev/null; then
    echo "→ Some audio tools missing: ${MISSING_PKGS[*]}"
    echo "  Trying to install via pacman (sudo password may be needed)..."
    echo ""
    if sudo pacman -S --needed --noconfirm "${MISSING_PKGS[@]}"; then
        echo "→ System packages installed."
    else
        echo ""
        echo "  ⚠ Could not install via pacman (SteamOS root is often read-only)."
        echo "  Chahlie will still install — you can type instead of using voice."
        echo ""
        echo "  If you want voice later, try in Desktop Mode:"
        echo "    sudo steamos-readonly disable"
        echo "    sudo pacman -S --needed ${MISSING_PKGS[*]}"
        echo "    sudo steamos-readonly enable"
        echo ""
        echo "  Press Enter to continue install anyway, or Ctrl+C to abort."
        read -r _
    fi
else
    echo "→ Audio tools missing and pacman not found — voice may not work."
    echo "  Chahlie will still install for typed chat."
fi

if ! have_cmd python3; then
    echo ""
    echo "  ✗ python3 is required but not found."
    echo "    Steam Deck should have it — try: sudo pacman -S python"
    exit 1
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
if have_cmd pw-record || have_cmd parecord; then
    echo "  Voice in:  mic ready"
else
    echo "  Voice:     mic not detected (typed chat still works)"
fi
if have_cmd espeak-ng || have_cmd espeak; then
    echo "  Voice out: speaker ready"
else
    echo "  Voice out: espeak not found (toggle TTS off or install espeak-ng)"
fi
echo ""
echo "  Next steps:"
echo "    1. nano $INSTALL_DIR/.env     # add OLLAMA_API_KEY"
echo "    2. chahlie-deck               # launch"
echo ""
echo "  Or find 'Chahlie (Steam Deck)' in your app menu."
echo ""
