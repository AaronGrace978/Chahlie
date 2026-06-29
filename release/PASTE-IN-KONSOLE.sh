#!/usr/bin/env bash
# Paste this ENTIRE file into Konsole if nothing else works.
echo "Looking for Chahlie..."
FOUND=""
for d in \
    "$HOME/Downloads"/chahlie-deck-*-linux \
    "$HOME/Downloads"/Chahlie \
    "$HOME"/chahlie-deck-*-linux \
    "$HOME"/Chahlie; do
    if [[ -f "$d/START-CHAHLIE.sh" ]]; then
        FOUND="$d"
        break
    fi
done
if [[ -z "$FOUND" ]]; then
    FOUND="$(find "$HOME/Downloads" "$HOME" -maxdepth 3 -name START-CHAHLIE.sh 2>/dev/null | head -1)"
    FOUND="$(dirname "$FOUND" 2>/dev/null || true)"
fi
if [[ -z "$FOUND" || ! -f "$FOUND/START-CHAHLIE.sh" ]]; then
    echo ""
    echo "CANNOT FIND CHAHLIE."
    echo "1. Download from: github.com/AaronGrace978/Chahlie/releases"
    echo "2. Right-click the .tar.gz -> Extract Here (in Downloads)"
    echo "3. Run this script again"
    echo ""
    read -r -p "Press Enter..."
    exit 1
fi
echo "Found: $FOUND"
cd "$FOUND" || exit 1
chmod +x START-CHAHLIE.sh
bash START-CHAHLIE.sh
