#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  START CHAHLIE — double-click this file (or run in Konsole)
#  First launch auto-installs (~1 min). Then the UI opens.
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${CHAHLIE_HOME:-$HOME/.local/share/chahlie}"
VENV_DIR="$INSTALL_DIR/venv"
ENV_FILE="$INSTALL_DIR/.env"
MARKER="$VENV_DIR/.chahlie-ready"

mkdir -p "$INSTALL_DIR" "$HOME/.local/bin"

bootstrap() {
    if [[ -f "$MARKER" ]]; then
        return 0
    fi

    echo ""
    echo "  ⚾ Chahlie — first-time setup (about 1 minute)"
    echo "  ================================================"
    echo ""

    if ! command -v python3 &>/dev/null; then
        echo "  ✗ python3 not found. Open Desktop Mode — SteamOS includes Python."
        exit 1
    fi

    echo "  → Creating app environment..."
    python3 -m venv "$VENV_DIR"

    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"

    echo "  → Downloading dependencies (needs internet once)..."
    pip install --upgrade pip wheel setuptools -q
    pip install -e "$ROOT" -q
    pip install -r "$ROOT/requirements-deck.txt" -q

    if [[ ! -f "$ENV_FILE" ]]; then
        cp "$ROOT/.env.deck.example" "$ENV_FILE"
    fi

    # One-click launcher on Desktop
    DESKTOP_FILE="$HOME/Desktop/Start Chahlie.desktop"
    cat > "$DESKTOP_FILE" << DESKTOP
[Desktop Entry]
Version=1.0
Name=Start Chahlie
Comment=Boston coding agent for Steam Deck
Exec=bash -lc 'cd "$ROOT" && ./START-CHAHLIE.sh'
Icon=utilities-terminal
Terminal=true
Type=Application
Categories=Game;Utility;
StartupNotify=true
DESKTOP
    chmod +x "$DESKTOP_FILE" 2>/dev/null || true

  # App menu entry
    APP_DIR="$HOME/.local/share/applications"
    mkdir -p "$APP_DIR"
    cat > "$APP_DIR/chahlie-deck.desktop" << DESKTOP2
[Desktop Entry]
Name=Chahlie
Comment=Boston coding agent — Steam Deck UI
Exec=bash -lc 'cd "$ROOT" && ./START-CHAHLIE.sh'
Icon=utilities-terminal
Terminal=true
Type=Application
Categories=Development;Utility;
StartupNotify=true
DESKTOP2

    touch "$MARKER"
    echo ""
    echo "  ✓ Setup complete! Opening Chahlie UI..."
    echo ""
    sleep 1
}

bootstrap

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
export CHAHLIE_ENV_FILE="$ENV_FILE"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

cd "$ROOT"
exec python -m chahlie --deck "$@"
