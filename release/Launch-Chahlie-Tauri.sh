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
# Steam Deck — use venv python (works without system pip / read-only root)
VENV="${CHAHLIE_VENV:-$HOME/.local/share/chahlie/venv}"
if [[ -x "$VENV/bin/python" ]]; then
  export CHAHLIE_PYTHON="$VENV/bin/python"
elif [[ -z "${CHAHLIE_PYTHON:-}" ]]; then
  export CHAHLIE_PYTHON="/usr/bin/python3"
fi

# Bootstrap venv if missing
if [[ ! -x "$VENV/bin/python" ]]; then
  echo "→ Creating Chahlie venv (no sudo needed)…"
  mkdir -p "$(dirname "$VENV")"
  python3 -m venv "$VENV" 2>/dev/null || python3 -m venv --system-site-packages "$VENV"
  "$VENV/bin/pip" install --upgrade pip wheel
  "$VENV/bin/pip" install fastapi "uvicorn[standard]" ollama anthropic rich python-dotenv requests click textual
  export CHAHLIE_PYTHON="$VENV/bin/python"
fi

if ! "$CHAHLIE_PYTHON" -c "import fastapi" 2>/dev/null; then
  echo "→ Installing Python deps into venv…"
  "$VENV/bin/pip" install fastapi "uvicorn[standard]" ollama anthropic rich python-dotenv requests click textual
fi

chmod +x "$APP"
exec "$APP" "${@:2}"
