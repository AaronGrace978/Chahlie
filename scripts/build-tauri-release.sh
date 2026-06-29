#!/usr/bin/env bash
# Build Chahlie Tauri desktop app (Linux AppImage + .deb)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAURI_DIR="$ROOT/chahlie-tauri"

echo "⚾ Building Chahlie Tauri…"
echo "   Workspace: $ROOT"

# Ensure Python deps for the sidecar server
if ! python3 -c "import fastapi, uvicorn" 2>/dev/null; then
  echo "→ Installing Python Tauri deps…"
  pip install -q -r "$ROOT/requirements-tauri.txt"
fi

export CHAHLIE_ROOT="$ROOT"

cd "$TAURI_DIR"
npm install
npm run tauri build

echo ""
echo "✓ Tauri build complete. Artifacts:"
find "$TAURI_DIR/src-tauri/target/release/bundle" -type f \( -name "*.deb" -o -name "*.AppImage" \) 2>/dev/null || true
