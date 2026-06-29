#!/usr/bin/env bash
# Build a downloadable Steam Deck release tarball (no git clone required).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(python3 -c "from chahlie import __version__; print(__version__)")"
CODENAME="$(python3 -c "from chahlie import __codename__; print(__codename__)")"
STAGE="$ROOT/dist/chahlie-deck-${VERSION}-linux"
ARCHIVE="$ROOT/dist/chahlie-deck-${VERSION}-linux-x86_64.tar.gz"

echo "Building Chahlie Deck release v${VERSION} \"${CODENAME}\"..."

rm -rf "$ROOT/dist"
mkdir -p "$STAGE"

# Copy package (exclude dev junk) — tar is available everywhere
tar -cf - -C "$ROOT" \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='dist' \
  --exclude='.cursor' \
  --exclude='venv' \
  --exclude='.chahlie' \
  . | tar -xf - -C "$STAGE"

# Launchers at tarball root
cp "$ROOT/release/Start Chahlie.desktop" "$STAGE/Start Chahlie.desktop"
cp "$ROOT/release/START-CHAHLIE.sh" "$STAGE/START-CHAHLIE.sh"
cp "$ROOT/release/PASTE-IN-KONSOLE.sh" "$STAGE/PASTE-IN-KONSOLE.sh"
cp "$ROOT/release/install.sh" "$STAGE/install.sh"
cp "$ROOT/release/run-chahlie-deck.sh" "$STAGE/run-chahlie-deck.sh"
cp "$ROOT/release/INSTALL.txt" "$STAGE/INSTALL.txt"
cp "$ROOT/release/README-FIRST.txt" "$STAGE/README-FIRST.txt"
cp "$ROOT/release/README-FIRST.txt" "$STAGE/!!! READ THIS FIRST !!!.txt"
cp "$ROOT/release/DECK-INSTALL.txt" "$STAGE/DECK-INSTALL.txt"
chmod +x "$STAGE/START-CHAHLIE.sh" "$STAGE/PASTE-IN-KONSOLE.sh" "$STAGE/install.sh" "$STAGE/run-chahlie-deck.sh" "$STAGE/Start Chahlie.desktop"

mkdir -p "$ROOT/dist"
tar -czf "$ARCHIVE" -C "$ROOT/dist" "chahlie-deck-${VERSION}-linux"

BYTES=$(wc -c < "$ARCHIVE" | tr -d ' ')
echo ""
echo "✓ Release built:"
echo "  $ARCHIVE"
echo "  Size: ${BYTES} bytes"
echo ""
echo "Upload to GitHub Releases, or copy to your Deck and run:"
echo "  tar -xzf chahlie-deck-${VERSION}-linux-x86_64.tar.gz"
echo "  cd chahlie-deck-${VERSION}-linux"
echo "  ./START-CHAHLIE.sh    # double-click this file"
