#!/usr/bin/env bash
# Chahlie on Steam Deck — uses a venv (no system pip, no pacman, no sudo).
# Works on read-only SteamOS.
set -euo pipefail

VENV="${CHAHLIE_VENV:-$HOME/.local/share/chahlie/venv}"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"

echo "⚾ Chahlie — Steam Deck setup (venv, no sudo)"
echo "   Venv: $VENV"

if [[ ! -x "$PY" ]]; then
  echo "→ Creating Python venv…"
  mkdir -p "$(dirname "$VENV")"
  if ! python3 -m venv "$VENV" 2>/dev/null; then
    python3 -m venv --system-site-packages "$VENV"
  fi
fi

if [[ ! -x "$PY" ]]; then
  echo "✗ Could not create venv. Switch to Desktop Mode and retry."
  exit 1
fi

echo "→ Upgrading pip in venv…"
"$PY" -m pip install --upgrade pip wheel setuptools

echo "→ Installing Chahlie packages…"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REQ="$ROOT/requirements-tauri.txt"
if [[ -f "$REQ" ]]; then
  "$PIP" install -r "$REQ"
else
  "$PIP" install fastapi "uvicorn[standard]" ollama anthropic rich python-dotenv requests click textual
fi

mkdir -p "$HOME/.local/share/chahlie"
if [[ ! -f "$HOME/.local/share/chahlie/.env" ]]; then
  cat > "$HOME/.local/share/chahlie/.env" << 'EOF'
CHAHLIE_BACKEND=ollama-cloud
OLLAMA_CLOUD_MODEL=qwen3.5:cloud
OLLAMA_API_KEY=
EOF
  echo "→ Created ~/.local/share/chahlie/.env"
fi

echo ""
echo "✓ Done. Python: $PY"
echo ""
echo "══════════════════════════════════════════════════════"
echo " EASIEST: Deck tarball (recommended)"
echo "══════════════════════════════════════════════════════"
echo "  cd ~/Downloads"
echo "  curl -L -O https://github.com/AaronGrace978/Chahlie/releases/download/v2.5.12/chahlie-deck-2.5.12-linux-x86_64.tar.gz"
echo "  tar -xzf chahlie-deck-2.5.12-linux-x86_64.tar.gz"
echo "  cd chahlie-deck-2.5.12-linux && ./START-CHAHLIE.sh"
echo ""
echo " Tauri AppImage (if you downloaded one):"
echo "  export WEBKIT_DISABLE_DMABUF_RENDERER=1"
echo "  export CHAHLIE_PYTHON=$PY"
echo "  ./Chahlie_*_amd64.AppImage"
