# Chahlie Steam Deck Edition

**v2.5.0 "Green Monster"** — talk to your Boston coding agent on the go.

Chahlie's Steam Deck build gives you a polished **1280×800 UI**, **voice input/output**, **touch-friendly buttons**, and **gamepad-ready approvals** — the same agentic coding brain as desktop, tuned for handheld.

## Quick install (Desktop Mode)

```bash
git clone https://github.com/AaronGrace978/Chahlie.git
cd Chahlie
bash scripts/install-steam-deck.sh
```

Then launch:

```bash
chahlie-deck
```

Or add **Chahlie (Steam Deck)** from your KDE app menu, or register it as a **Non-Steam Game** for Gaming Mode.

## First-time setup

1. Copy deck config and add your API key:
   ```bash
   cp .env.deck.example ~/.local/share/chahlie/.env
   nano ~/.local/share/chahlie/.env
   ```
2. Set `OLLAMA_API_KEY` (get one at [ollama.com/settings/keys](https://ollama.com/settings/keys)).
3. For offline play, switch to `CHAHLIE_BACKEND=ollama-local` and run `ollama pull qwen3:8b`.

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

Install voice deps if you skipped the installer:

```bash
pip install -r requirements-deck.txt
# SteamOS also needs: sudo pacman -S portaudio espeak-ng
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

## Deck-tuned settings

`.env.deck.example` enables:
- Compact social replies (good on a small screen)
- Voice on by default
- Approval prompts on (safer on a handheld)
- Optional lighter memory (commented) if performance dips

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No mic | `sudo pacman -S portaudio` then reinstall PyAudio |
| No voice out | `sudo pacman -S espeak-ng` |
| Textual won't start | `pip install textual>=0.50` |
| Slow responses | Use `qwen3.5:cloud` or local `qwen3:8b`; disable semantic memory |
| Approval stuck | Use touch buttons on the modal; A=approve B=deny |
| Can't type / keyboard dead | Tap the input bar or press **F7** (map Steam **Start**→F7). Toolbar buttons steal focus — we refocus after taps now. In Gaming Mode use Desktop Mode keyboard or **F4 Talk** |
| Ollama Cloud fails | Check `OLLAMA_API_KEY` in `~/.local/share/chahlie/.env`; try `CHAHLIE_FALLBACK_MODELS`; see https://ollama.com/status |

## What's in the box

- `chahlie/deck_ui.py` — Fenway-themed Deck UI (Textual)
- `chahlie/voice.py` — STT/TTS module
- `scripts/install-steam-deck.sh` — release installer
- `requirements-deck.txt` — voice + UI extras

Made with love by **Cursor Boston** ⚾
