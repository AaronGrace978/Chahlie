#!/usr/bin/env bash
# Chahlie Steam Deck Edition — one-shot installer (from git clone)
# Run from Desktop Mode:  bash scripts/install-steam-deck.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Delegate to the standalone release installer
exec bash "$ROOT_DIR/release/install.sh"
