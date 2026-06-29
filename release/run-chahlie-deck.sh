#!/usr/bin/env bash
# Quick launcher — works from the extracted tarball OR after install.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${CHAHLIE_HOME:-$HOME/.local/share/chahlie}"
VENV_DIR="$INSTALL_DIR/venv"

if [[ -x "$HOME/.local/bin/chahlie-deck" ]]; then
    exec "$HOME/.local/bin/chahlie-deck" "$@"
fi

if [[ ! -d "$VENV_DIR" ]]; then
    echo "Chahlie isn't installed yet. Run ./install.sh first."
    exit 1
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
if [[ -f "$INSTALL_DIR/.env" ]]; then
    set -a
    source "$INSTALL_DIR/.env"
    set +a
fi
cd "$ROOT"
exec python -m chahlie --deck "$@"
