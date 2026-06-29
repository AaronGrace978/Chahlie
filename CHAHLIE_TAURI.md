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

## Steam Deck AppImage (recommended)

The AppImage is **self-bootstrapping**. On first launch it creates its own
Python virtualenv at `~/.local/share/chahlie/venv` and installs the backend
deps there — no `pip`, no `sudo`, no `pacman`, and no `CHAHLIE_PYTHON` needed.
A venv under `$HOME` sidesteps SteamOS's read-only root and PEP 668.

**Launch:**

```bash
chmod +x Chahlie_2.6.3_amd64.AppImage
./Chahlie_2.6.3_amd64.AppImage
```

If the window stays black on the Deck, run it in Desktop Mode with:

```bash
export WEBKIT_DISABLE_DMABUF_RENDERER=1
./Chahlie_2.6.3_amd64.AppImage
```

To force a specific interpreter, set `CHAHLIE_PYTHON=/path/to/python`.
The repo also ships a convenience launcher: `release/Launch-Chahlie-Tauri.sh`.

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
