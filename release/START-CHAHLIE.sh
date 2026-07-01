#!/usr/bin/env bash
# Chahlie Steam Deck launcher — keeps window open on errors, shows what's wrong.

pause() {
    echo ""
    echo "  Press Enter to close this window..."
    read -r _
}

die() {
    echo ""
    echo "  ✗ $*"
    pause
    exit 1
}

# Find the real app folder (not the nested release/ subfolder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR"
if [[ ! -f "$ROOT/chahlie/__init__.py" ]]; then
    if [[ -f "$ROOT/../chahlie/__init__.py" ]]; then
        ROOT="$(cd "$ROOT/.." && pwd)"
    else
        die "Cannot find Chahlie files. Open the extracted chahlie-deck folder, not a subfolder."
    fi
fi

INSTALL_DIR="${CHAHLIE_HOME:-$HOME/.local/share/chahlie}"
VENV_DIR="$INSTALL_DIR/venv"
ENV_FILE="$INSTALL_DIR/.env"
MARKER="$INSTALL_DIR/.chahlie-ready"
PYTHON=""
WORK_DIR="${CHAHLIE_WORKDIR:-$HOME}"

read_version() {
    grep -m1 '__version__' "$ROOT/chahlie/__init__.py" 2>/dev/null \
        | sed -E 's/.*"([^"]+)".*/\1/' || echo "unknown"
}

CURRENT_VERSION="$(read_version)"

pick_python() {
    if [[ -x "$VENV_DIR/bin/python" ]]; then
        PYTHON="$VENV_DIR/bin/python"
        return 0
    fi
    if command -v python3 &>/dev/null; then
        PYTHON="$(command -v python3)"
        return 0
    fi
    die "python3 not found. You're in Desktop Mode, right?"
}

# Test the REAL launch environment: from $HOME, using -m chahlie (not a local ./chahlie folder).
chahlie_works() {
    pick_python
    (cd "$WORK_DIR" && "$PYTHON" -m chahlie --version &>/dev/null)
}

needs_install() {
    if [[ ! -f "$MARKER" ]]; then
        return 0
    fi
    # Reinstall when the tarball version changes
    local installed_ver
    installed_ver="$(head -1 "$MARKER" 2>/dev/null || true)"
    if [[ "$installed_ver" != "$CURRENT_VERSION" ]]; then
        echo "  → Upgrading $installed_ver → $CURRENT_VERSION..."
        return 0
    fi
    # Reinstall when the editable install is broken (common after moving the folder)
    if ! chahlie_works; then
        return 0
    fi
    return 1
}

install_deps() {
    echo ""
    echo "  ⚾ Chahlie — setup"
    echo "  =================="
    echo "  Folder:  $ROOT"
    echo "  Version: $CURRENT_VERSION"
    echo ""

    pick_python

    echo "  → Setting up Python environment (needs internet, ~1-2 min)..."
    echo ""

    if ! "$PYTHON" -m venv "$VENV_DIR" 2>/dev/null; then
        echo "  (venv default failed, trying with system packages...)"
        "$PYTHON" -m venv --system-site-packages "$VENV_DIR" 2>/dev/null || true
    fi

    if [[ -x "$VENV_DIR/bin/python" ]]; then
        PYTHON="$VENV_DIR/bin/python"
        echo "  → Installing into: $VENV_DIR"
        "$VENV_DIR/bin/pip" install --upgrade pip wheel setuptools || true
        "$VENV_DIR/bin/pip" install -e "$ROOT" || die "pip install failed. Check internet connection."
        "$VENV_DIR/bin/pip" install -r "$ROOT/requirements-deck.txt" || die "Could not install dependencies."
    else
        echo "  → Using user install (no venv)..."
        "$PYTHON" -m pip install --user --upgrade pip wheel setuptools 2>/dev/null || \
            "$PYTHON" -m ensurepip --upgrade 2>/dev/null || true
        "$PYTHON" -m pip install --user -e "$ROOT" --break-system-packages 2>/dev/null || \
            "$PYTHON" -m pip install --user -e "$ROOT" || die "pip install failed."
        "$PYTHON" -m pip install --user -r "$ROOT/requirements-deck.txt" --break-system-packages 2>/dev/null || \
            "$PYTHON" -m pip install --user -r "$ROOT/requirements-deck.txt" || die "Could not install dependencies."
    fi

    mkdir -p "$INSTALL_DIR"
    [[ -f "$ENV_FILE" ]] || cp "$ROOT/.env.deck.example" "$ENV_FILE"

    # Desktop shortcut with correct path
    cat > "$HOME/Desktop/Start Chahlie.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Start Chahlie
Exec=bash -lc 'cd "$ROOT" && bash "$ROOT/START-CHAHLIE.sh"'
Icon=utilities-terminal
Terminal=true
Categories=Game;
EOF
    chmod +x "$HOME/Desktop/Start Chahlie.desktop" 2>/dev/null || true

    echo "$CURRENT_VERSION" > "$MARKER"
    echo ""
    echo "  ✓ Setup done!"
    echo ""
}

verify() {
    pick_python
    echo "  → Checking install (from $WORK_DIR)..."
    if ! chahlie_works; then
        echo "  Install incomplete — retrying..."
        rm -f "$MARKER"
        install_deps
        if ! chahlie_works; then
            die "Still broken after reinstall. Try: rm -rf $INSTALL_DIR/venv $MARKER"
        fi
    fi
    echo "  ✓ Ready. Opening UI..."
    echo ""
}

if needs_install; then
    install_deps
fi
verify

export CHAHLIE_ENV_FILE="$ENV_FILE"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

export CHAHLIE_DECK_MODE=true
export CHAHLIE_WORKDIR="$WORK_DIR"
cd "$WORK_DIR"
if "$PYTHON" -m chahlie --deck "$@"; then
    exit 0
else
    CODE=$?
    echo ""
    echo "  ✗ Chahlie exited with error (code $CODE)"
    pause
    exit "$CODE"
fi
