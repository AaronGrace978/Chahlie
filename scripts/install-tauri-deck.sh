#!/usr/bin/env bash
# One-shot Python setup for Chahlie Tauri on Steam Deck
set -euo pipefail

PY="${CHAHLIE_PYTHON:-/usr/bin/python3}"
command -v "$PY" >/dev/null || PY="$(command -v python3)"

echo "⚾ Chahlie Tauri — Python setup"
echo "   Python: $PY"

"$PY" -m pip install --user --upgrade pip wheel setuptools 2>/dev/null || true

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REQ="$ROOT/requirements-tauri.txt"
if [[ -f "$REQ" ]]; then
  "$PY" -m pip install --user -r "$REQ" --break-system-packages 2>/dev/null || \
    "$PY" -m pip install --user -r "$REQ"
else
  "$PY" -m pip install --user \
    fastapi "uvicorn[standard]" ollama anthropic rich python-dotenv requests click textual \
    --break-system-packages 2>/dev/null || \
  "$PY" -m pip install --user \
    fastapi "uvicorn[standard]" ollama anthropic rich python-dotenv requests click textual
fi

mkdir -p "$HOME/.local/share/chahlie"
if [[ ! -f "$HOME/.local/share/chahlie/.env" ]]; then
  if [[ -f "$ROOT/.env.deck.example" ]]; then
    cp "$ROOT/.env.deck.example" "$HOME/.local/share/chahlie/.env"
  else
    cat > "$HOME/.local/share/chahlie/.env" << 'EOF'
CHAHLIE_BACKEND=ollama-cloud
OLLAMA_CLOUD_MODEL=qwen3.5:cloud
OLLAMA_API_KEY=
EOF
  fi
  echo "→ Created ~/.local/share/chahlie/.env — add your key in the app"
fi

echo ""
echo "✓ Ready. Launch with:"
echo "  export WEBKIT_DISABLE_DMABUF_RENDERER=1"
echo "  export CHAHLIE_PYTHON=$PY"
echo "  ./Chahlie_*_amd64.AppImage"
