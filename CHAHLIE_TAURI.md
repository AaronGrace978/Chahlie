# Chahlie Tauri — Desktop App (Steam Deck + Linux)

Native window with a React UI. The **Python agent** runs locally in the background — same brain as the terminal Deck UI.

## Quick start (dev)

```bash
# From repo root
pip install -r requirements-tauri.txt
cd chahlie-tauri && npm install
export CHAHLIE_ROOT=..
npm run tauri dev
```

Paste your Ollama API key in the welcome screen. Config lives at `~/.local/share/chahlie/.env`.

## Build installable app

```bash
bash scripts/build-tauri-release.sh
```

Outputs (under `chahlie-tauri/src-tauri/target/release/bundle/`):

- `Chahlie_*.AppImage` — download, `chmod +x`, double-click
- `chahlie_*.deb` — install with your package manager

## Steam Deck AppImage (recommended launcher)

The AppImage needs **system Python 3** + one-time pip deps. Do **not** rely on an old broken venv.

**One-time setup in Konsole:**

```bash
cd ~/Downloads
curl -L -O https://raw.githubusercontent.com/AaronGrace978/Chahlie/main/scripts/install-tauri-deck.sh
bash install-tauri-deck.sh
```

**Launch (every time):**

```bash
export WEBKIT_DISABLE_DMABUF_RENDERER=1
export CHAHLIE_PYTHON=/usr/bin/python3
./Chahlie_2.6.1_amd64.AppImage
```

Or use the bundled launcher script from the repo: `release/Launch-Chahlie-Tauri.sh`

### EGL / display crash on Deck

If you see `EGL_BAD_PARAMETER`, run in **Desktop Mode** with:

```bash
export WEBKIT_DISABLE_DMABUF_RENDERER=1
export GDK_BACKEND=x11
```

## Add to Steam (no Konsole after install)

1. Install the AppImage or `.deb`
2. **Steam → Add a Non-Steam Game**
3. Pick **Chahlie** from your app menu (or browse to the AppImage)
4. Launch from Gaming Mode like any other game

## vs Terminal Deck UI

| | Tauri (`chahlie-tauri`) | Textual (`--deck`) |
|--|-------------------------|---------------------|
| Window | Native GUI | Terminal TUI |
| Install | AppImage / .deb | Tarball + launcher |
| Steam | Add installed app | Add `chahlie-deck` |
| Python | System / existing venv | Bundled in tarball flow |

Both use **Ollama Cloud** (paste key once) or local Ollama via `.env`.

## Requirements

- Python 3.10+
- `pip install -r requirements-tauri.txt`
- Linux: WebKitGTK (Steam Deck Desktop Mode has this)

Made by **Cursor Boston** ⚾
