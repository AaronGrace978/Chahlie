#!/usr/bin/env bash
# Inject Steam Deck display defaults into the AppImage *before* WebKitGTK loads.
#
# Setting env vars inside the Rust binary is too late: libwebkit/libgdk read them
# at process startup. This patches AppRun and repacks the AppImage.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPIMG_DIR="$ROOT/chahlie-tauri/src-tauri/target/release/bundle/appimage"

APPIMAGE="$(find "$APPIMG_DIR" -maxdepth 1 -type f -name 'Chahlie_*_amd64.AppImage' 2>/dev/null | head -1)"
if [[ -z "$APPIMAGE" ]]; then
  echo "⚠ No AppImage found — skipping Deck patch."
  exit 0
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "→ Patching AppImage for Steam Deck: $(basename "$APPIMAGE")"
cp "$APPIMAGE" "$WORK/"
(cd "$WORK" && chmod +x "$(basename "$APPIMAGE")" && "./$(basename "$APPIMAGE")" --appimage-extract >/dev/null)

APPDIR="$WORK/squashfs-root"
HOOK_DIR="$APPDIR/apprun-hooks"
mkdir -p "$HOOK_DIR"

cat > "$HOOK_DIR/chahlie-deck.sh" << 'EOF'
#!/usr/bin/env bash
# Chahlie — Steam Deck / SteamOS WebKitGTK defaults (before ELF load).
export GDK_BACKEND="${GDK_BACKEND:-x11}"
export WEBKIT_DISABLE_DMABUF_RENDERER="${WEBKIT_DISABLE_DMABUF_RENDERER:-1}"
export WEBKIT_DISABLE_COMPOSITING_MODE="${WEBKIT_DISABLE_COMPOSITING_MODE:-1}"
export WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS="${WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS:-1}"
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
export GSK_RENDERER="${GSK_RENDERER:-cairo}"
EOF
chmod +x "$HOOK_DIR/chahlie-deck.sh"

APP_RUN="$APPDIR/AppRun"
if ! grep -q 'chahlie-deck.sh' "$APP_RUN"; then
  awk '
    /linuxdeploy-plugin-gtk\.sh/ && !done {
      print
      print "source \"$this_dir\"/apprun-hooks/chahlie-deck.sh"
      done=1
      next
    }
    { print }
  ' "$APP_RUN" > "$APP_RUN.new"
  mv "$APP_RUN.new" "$APP_RUN"
  chmod +x "$APP_RUN"
fi

TOOL_CACHE="$ROOT/.cache/appimagetool"
if [[ ! -x "$TOOL_CACHE/AppRun" ]]; then
  mkdir -p "$ROOT/.cache"
  curl -fsSL -o "$ROOT/.cache/appimagetool-x86_64.AppImage" \
    "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
  chmod +x "$ROOT/.cache/appimagetool-x86_64.AppImage"
  (cd "$ROOT/.cache" && ./appimagetool-x86_64.AppImage --appimage-extract >/dev/null)
  TOOL_CACHE="$ROOT/.cache/squashfs-root"
fi

OUT_NAME="$(basename "$APPIMAGE")"
rm -f "$APPIMAGE"
ARCH=x86_64 "$TOOL_CACHE/AppRun" --no-appstream "$APPDIR" "$APPIMG_DIR/$OUT_NAME"
chmod +x "$APPIMG_DIR/$OUT_NAME"
echo "✓ Repacked $OUT_NAME with Steam Deck AppRun hook"
