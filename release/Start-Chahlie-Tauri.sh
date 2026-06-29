#!/usr/bin/env bash
# One command to launch Chahlie Tauri on Steam Deck.
# Sets display env vars BEFORE the AppImage loads WebKitGTK.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="${1:-}"
if [[ -z "$APP" ]]; then
  APP="$(ls "$DIR"/Chahlie_*_amd64.AppImage "$HOME/Downloads"/Chahlie_*_amd64.AppImage 2>/dev/null | sort -V | tail -1 || true)"
fi
if [[ -z "$APP" || ! -f "$APP" ]]; then
  echo "Put Chahlie_*_amd64.AppImage next to this script or in ~/Downloads"
  exit 1
fi

export GDK_BACKEND=x11
export WEBKIT_DISABLE_DMABUF_RENDERER=1
export WEBKIT_DISABLE_COMPOSITING_MODE=1
export WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1
export LIBGL_ALWAYS_SOFTWARE=1
export GSK_RENDERER=cairo

VENV="${CHAHLIE_VENV:-$HOME/.local/share/chahlie/venv}"
if [[ -x "$VENV/bin/python" ]]; then
  export CHAHLIE_PYTHON="$VENV/bin/python"
fi

chmod +x "$APP"
exec "$APP"
