#!/usr/bin/env bash
# Chahlie Tauri launcher for Steam Deck — fixes EGL + Python backend.
set -euo pipefail

APP="${1:-}"
if [[ -z "$APP" ]]; then
  APP="$(ls "$HOME/Downloads"/Chahlie_*_amd64.AppImage 2>/dev/null | sort -V | tail -1)"
fi
if [[ -z "$APP" || ! -f "$APP" ]]; then
  echo "Usage: bash Launch-Chahlie-Tauri.sh [/path/to/Chahlie.AppImage]"
  exit 1
fi

# Steam Deck / WebKit EGL workaround
export WEBKIT_DISABLE_DMABUF_RENDERER=1
export GDK_BACKEND=x11

# Always prefer system Python for AppImage (avoid broken old venvs)
export CHAHLIE_PYTHON="${CHAHLIE_PYTHON:-/usr/bin/python3}"
if ! command -v "$CHAHLIE_PYTHON" &>/dev/null; then
  CHAHLIE_PYTHON="$(command -v python3)"
  export CHAHLIE_PYTHON
fi

echo "→ Using Python: $CHAHLIE_PYTHON"

if ! "$CHAHLIE_PYTHON" -c "import fastapi, uvicorn" 2>/dev/null; then
  echo "→ Installing Chahlie Python deps (one time, needs internet)…"
  "$CHAHLIE_PYTHON" -m pip install --user --upgrade pip wheel 2>/dev/null || true
  "$CHAHLIE_PYTHON" -m pip install --user \
    fastapi "uvicorn[standard]" ollama anthropic rich python-dotenv requests click textual \
    --break-system-packages 2>/dev/null || \
  "$CHAHLIE_PYTHON" -m pip install --user \
    fastapi "uvicorn[standard]" ollama anthropic rich python-dotenv requests click textual
fi

chmod +x "$APP"
exec "$APP" "${@:2}"
