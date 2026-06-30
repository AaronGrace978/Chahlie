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
| Ollama Cloud fails | Type `/key` to fix API key; try `CHAHLIE_FALLBACK_MODELS` in `.env`; see https://ollama.com/status |

Made with love by **Cursor Boston** ⚾
