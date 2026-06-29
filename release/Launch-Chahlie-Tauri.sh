#!/usr/bin/env bash
# Chahlie Tauri launcher for Steam Deck
set -euo pipefail

APP="${1:-}"
if [[ -z "$APP" ]]; then
  APP="$(ls "$HOME/Downloads"/Chahlie_*_amd64.AppImage 2>/dev/null | sort -V | tail -1)"
fi
if [[ -z "$APP" || ! -f "$APP" ]]; then
  echo "Usage: bash Launch-Chahlie-Tauri.sh /path/to/Chahlie.AppImage"
  echo ""
  echo "Download AppImage from:"
  echo "  https://github.com/AaronGrace978/Chahlie/releases/tag/v2.6.1-tauri"
  exit 1
fi

export WEBKIT_DISABLE_DMABUF_RENDERER=1
export GDK_BACKEND=x11
export CHAHLIE_PYTHON="${CHAHLIE_PYTHON:-/usr/bin/python3}"

# Bootstrap pip + deps if needed
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/../scripts/install-tauri-deck.sh" ]]; then
  bash "$SCRIPT_DIR/../scripts/install-tauri-deck.sh"
elif [[ -f "$HOME/Downloads/install-tauri-deck.sh" ]]; then
  bash "$HOME/Downloads/install-tauri-deck.sh"
else
  if ! "$CHAHLIE_PYTHON" -m pip --version &>/dev/null; then
    "$CHAHLIE_PYTHON" -m ensurepip --user --default-pip 2>/dev/null || \
    "$CHAHLIE_PYTHON" -m ensurepip --user 2>/dev/null || \
    sudo pacman -S --needed python-pip
  fi
  "$CHAHLIE_PYTHON" -m pip install --user fastapi "uvicorn[standard]" ollama anthropic rich python-dotenv requests click textual --break-system-packages 2>/dev/null || \
  "$CHAHLIE_PYTHON" -m pip install --user fastapi "uvicorn[standard]" ollama anthropic rich python-dotenv requests click textual
fi

chmod +x "$APP"
exec "$APP" "${@:2}"
