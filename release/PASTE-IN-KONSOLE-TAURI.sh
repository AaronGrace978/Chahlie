#!/usr/bin/env bash
# Paste this ENTIRE file into Konsole on Steam Deck when the Tauri AppImage
# backend fails with "No module named 'encodings'".
#
# Uses your existing ~/.local/share/chahlie/venv and the code bundled inside
# the AppImage — no sudo, no pacman, no broken AppImage Python spawn.

set -euo pipefail

echo "⚾ Chahlie — Deck fallback launcher (venv + terminal UI)"
echo ""

APPIMAGE="${1:-}"
if [[ -z "$APPIMAGE" ]]; then
  APPIMAGE="$(ls "$HOME/Downloads"/Chahlie_*_amd64.AppImage 2>/dev/null | sort -V | tail -1 || true)"
fi
if [[ -z "$APPIMAGE" || ! -f "$APPIMAGE" ]]; then
  echo "Download the AppImage first, then run:"
  echo "  bash PASTE-IN-KONSOLE-TAURI.sh ~/Downloads/Chahlie_*_amd64.AppImage"
  exit 1
fi

VENV="${CHAHLIE_VENV:-$HOME/.local/share/chahlie/venv}"
PY="$VENV/bin/python"
ENV_FILE="${CHAHLIE_ENV_FILE:-$HOME/.local/share/chahlie/.env}"

if [[ ! -x "$PY" ]]; then
  echo "→ Creating venv at $VENV …"
  mkdir -p "$(dirname "$VENV")"
  python3 -m venv "$VENV" 2>/dev/null || python3 -m venv --system-site-packages "$VENV"
  "$PY" -m pip install --upgrade pip wheel
  "$PY" -m pip install fastapi "uvicorn[standard]" ollama anthropic rich python-dotenv requests click textual
fi

EXTRACT="$HOME/Downloads/chahlie-appimage-extract"
rm -rf "$EXTRACT"
mkdir -p "$EXTRACT"
echo "→ Extracting AppImage (one time)…"
(cd "$EXTRACT" && chmod +x "$APPIMAGE" && "$APPIMAGE" --appimage-extract >/dev/null)

ROOT="$EXTRACT/squashfs-root/usr/lib/Chahlie/_up_/_up_"
if [[ ! -f "$ROOT/chahlie/__init__.py" ]]; then
  echo "✗ Could not find bundled chahlie package in AppImage."
  exit 1
fi

mkdir -p "$(dirname "$ENV_FILE")"
if [[ ! -f "$ENV_FILE" ]]; then
  cat > "$ENV_FILE" << 'EOF'
CHAHLIE_BACKEND=ollama-cloud
OLLAMA_CLOUD_MODEL=qwen3.5:cloud
OLLAMA_API_KEY=
EOF
fi

export CHAHLIE_ENV_FILE="$ENV_FILE"
export PYTHONPATH="$ROOT"

echo ""
echo "→ Launching Chahlie Deck UI (uses your mic + gamepad controls)"
echo "  Paste API key in the UI or type /key"
echo "  Get a key: https://ollama.com/settings/keys"
echo ""

exec env -u PYTHONHOME -u PYTHONPATH -u LD_LIBRARY_PATH \
  CHAHLIE_ENV_FILE="$ENV_FILE" \
  PYTHONPATH="$ROOT" \
  "$PY" -m chahlie --deck
