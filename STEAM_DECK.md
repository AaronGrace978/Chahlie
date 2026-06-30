# Chahlie Steam Deck

## DO NOT open files in Kate. Click the launcher.

### Step 1 — Download
https://github.com/AaronGrace978/Chahlie/releases/latest

Download `chahlie-deck-*-linux-x86_64.tar.gz`

### Step 2 — Extract
Right-click the download → **Extract Here**

### Step 3 — Run (pick ONE)

**Option A — Double-click (recommended)**

1. Open the extracted folder in **Dolphin** (file manager, not Kate)
2. Double-click **`Start Chahlie.desktop`**
3. If it asks: right-click → **Allow Launching** → double-click again

**Option B — Konsole (if double-click fails)**

Open **Konsole** (the terminal app). Copy and paste this entire line, press Enter:

```
cd ~/Downloads/chahlie-deck-*-linux && chmod +x START-CHAHLIE.sh && ./START-CHAHLIE.sh
```

### Step 4 — Paste API key in the UI
Get a free key: https://ollama.com/settings/keys

Type `/key` anytime to update your key.

### Where to type

The **gold box at the bottom** says **▶ TYPE HERE**. That's your message box.

- Tap the gold-bordered input area, or press **F7** to focus the keyboard
- **Enter** sends your message
- If you only see toolbar buttons, scroll down — the input sits below them in a gold-framed bar

---

## Website

Baseball-themed landing page (GitHub Pages): **https://aarongrace978.github.io/Chahlie/**

---

## You clicked the wrong file if Kate opened

| Wrong (opens Kate) | Right (runs Chahlie) |
|--------------------|----------------------|
| `START-CHAHLIE.sh` | `Start Chahlie.desktop` |
| Any `.py` file | `Start Chahlie.desktop` |
| `README-FIRST.txt` | `Start Chahlie.desktop` |

Kate is a **text editor**. You want the **`.desktop`** launcher file.

## Voice — talk to Chahlie

| Control | Action |
|---------|--------|
| **🎤 Talk** button or **F4** | Push-to-talk — speak your request |
| **🔊 TTS** button or **F5** | Toggle spoken replies |
| **F6** | Stop current speech |

Voice uses your Deck mic + speaker. STT goes through Google Web Speech by default (needs Wi‑Fi). For **offline speech**, install a [Vosk model](https://alphacephei.com/vosk/models) and set:

```bash
CHAHLIE_VOSK_MODEL=/path/to/vosk-model-small-en-us-0.15
```

## Deck UI controls

### On-screen toolbar
**Help** · **Clear** · **Memory** · **🎤 Talk** · **🔊 TTS** · **Quit**

### Keyboard / Steam Input
| Key | Action |
|-----|--------|
| F1 | Help |
| F2 | Clear conversation |
| F3 | Memory summary |
| F4 | Talk (mic) |
| F5 | Toggle TTS |
| F7 | Focus text input (map Steam **Start** → F7) |
| Enter | Send message |
| Ctrl+C | Quit |

### Suggested Steam Input (Gaming Mode)
Map these in Steam when you add `chahlie-deck` as a Non-Steam Game:

| Button | Maps to |
|--------|---------|
| A | Enter |
| B | Escape |
| X | F4 (Talk) |
| Y | F1 (Help) |
| Start | F7 (Type) |
| D-pad | Arrow keys (scroll) |

### Dangerous command approval
When Chahlie wants to run something risky (`rm -rf`, `git push --force`, etc.), a **modal** pops up. **A / Y = Approve**, **B / N = Deny** — works with touch or gamepad.

## Run from source (dev)

```bash
pip install -r requirements.txt -r requirements-deck.txt
cp .env.deck.example .env   # add your key
bash scripts/chahlie-deck.sh
# or: python -m chahlie --deck
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No mic | `sudo pacman -S portaudio` then reinstall PyAudio |
| No voice out | `sudo pacman -S espeak-ng` |
| Textual won't start | `pip install textual>=0.50` |
| Slow responses | Use `qwen3.5:cloud` or local `qwen3:8b`; disable semantic memory |
| Approval stuck | Use touch buttons on the modal; A=approve B=deny |
| Can't type / keyboard dead | Tap the input bar or press **F7**. Toolbar buttons steal focus — we refocus after taps. In Gaming Mode use Desktop Mode keyboard or **F4 Talk** |
| Chahlie won't scan/organize my files | Make sure `CHAHLIE_WORKDIR=/home/deck` is in `~/.local/share/chahlie/.env`. Re-run `START-CHAHLIE.sh` from a fresh release — older builds started in the Chahlie install folder by mistake |
| Says "I'm only a coding assistant" | Update to v2.7.0+ — Deck mode includes personal-assistant + native Deck tools. Try: *"launch Steam"*, *"check battery"*, *"set volume to 40"* |
| Ollama Cloud fails | Type `/key` to fix API key; try `CHAHLIE_FALLBACK_MODELS` in `.env`; see https://ollama.com/status |
| Want to use a friend's GPU | Run `python -m chahlie.llama_proxy` on their machine; set `CHAHLIE_BACKEND=openai-compatible` and `OPENAI_COMPATIBLE_URL` on your Deck |

## Deck native commands (v2.7+)

Tell Chahlie anything you'd do on the Deck — he'll use his tools:

| You say | Chahlie does |
|---------|----------------|
| "Launch Hades" / "open Firefox" | `deck_launch` |
| "How's my battery?" / "disk space?" | `deck_system_info` |
| "Set volume to 60" / "mute" | `deck_set_volume` |
| "Brightness 80%" | `deck_set_brightness` |
| "Open Big Picture" | `deck_steam` |

He still handles files, shell commands, git, and coding — the whole machine is in play.

## Llama proxy (share with friends)

On a PC with Ollama running:

```bash
ollama serve
python -m chahlie.llama_proxy --port 11435
```

On your Deck (`~/.local/share/chahlie/.env`):

```bash
CHAHLIE_BACKEND=openai-compatible
OPENAI_COMPATIBLE_URL=http://192.168.x.x:11435/v1
OPENAI_COMPATIBLE_MODEL=qwen3:8b
```

Made with love by **Cursor Boston** ⚾
