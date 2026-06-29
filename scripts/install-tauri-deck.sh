#!/usr/bin/env bash
# Chahlie on Steam Deck — installs pip if missing, then Python deps.
# Works WITHOUT system pip (uses ensurepip or pacman).
set -euo pipefail

PY="${CHAHLIE_PYTHON:-/usr/bin/python3}"
command -v "$PY" >/dev/null 2>&1 || PY="$(command -v python3)"
if [[ -z "$PY" ]]; then
  echo "✗ python3 not found. Run: sudo pacman -S python"
  exit 1
fi

echo "⚾ Chahlie — Steam Deck setup"
echo "   Python: $PY"

bootstrap_pip() {
  if "$PY" -m pip --version &>/dev/null; then
    return 0
  fi
  echo "→ pip not found — bootstrapping…"
  if "$PY" -m ensurepip --user --default-pip 2>/dev/null || "$PY" -m ensurepip --user 2>/dev/null; then
    return 0
  fi
  if command -v pacman &>/dev/null; then
    echo "→ Trying pacman (may ask for sudo password)…"
    if sudo pacman -S --needed --noconfirm python-pip; then
      return 0
    fi
  fi
  echo "✗ Could not install pip. Try:"
  echo "    sudo pacman -S python-pip"
  echo "  Or use the Deck tarball (no pip needed):"
  echo "    https://github.com/AaronGrace978/Chahlie/releases/download/v2.5.12/chahlie-deck-2.5.12-linux-x86_64.tar.gz"
  exit 1
}

bootstrap_pip

echo "→ Installing Chahlie Python packages…"
"$PY" -m pip install --user --upgrade pip wheel setuptools 2>/dev/null || true

install_pkgs() {
  "$PY" -m pip install --user --upgrade \
    fastapi "uvicorn[standard]" ollama anthropic rich python-dotenv requests click textual \
    "$@"
}

install_pkgs --break-system-packages 2>/dev/null || install_pkgs

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
echo "✓ Python ready."
echo ""
echo "EASIEST (recommended — no AppImage headaches):"
echo "  curl -L -O https://github.com/AaronGrace978/Chahlie/releases/download/v2.5.12/chahlie-deck-2.5.12-linux-x86_64.tar.gz"
echo "  tar -xzf chahlie-deck-2.5.12-linux-x86_64.tar.gz"
echo "  cd chahlie-deck-2.5.12-linux && ./START-CHAHLIE.sh"
echo ""
echo "Or Tauri AppImage (after downloading from releases):"
echo "  export WEBKIT_DISABLE_DMABUF_RENDERER=1"
echo "  export CHAHLIE_PYTHON=$PY"
echo "  ./Chahlie_*_amd64.AppImage"
