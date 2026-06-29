# Chahlie Steam Deck Edition

**v2.5.1 "Tap the Glass"** — download, install, talk. No compiler needed.

## Download and run (easiest)

1. Go to **[GitHub Releases](https://github.com/AaronGrace978/Chahlie/releases)** and download:
   ```
   chahlie-deck-2.5.1-linux-x86_64.tar.gz
   ```

2. Open **Konsole** (Desktop Mode on your Deck):

   ```bash
   cd ~/Downloads
   tar -xzf chahlie-deck-*-linux-x86_64.tar.gz
   cd chahlie-deck-*-linux
   ./install.sh
   ```

3. Add your API key:

   ```bash
   nano ~/.local/share/chahlie/.env
   # set OLLAMA_API_KEY=your-key-here
   ```

4. Launch:

   ```bash
   chahlie-deck
   ```

That's it. No `git clone`, no gcc, no PyAudio compile errors.

The installer pulls **prebuilt** system packages (`pipewire-pulse`, `espeak-ng`) from SteamOS and only pip-installs pure-Python deps.

---

## Voice — talk to Chahlie

| Control | Action |
|---------|--------|
| **🎤 Talk** button or **F4** | Push-to-talk — speak your request |
| **🔊 TTS** button or **F5** | Toggle spoken replies |
| **F6** | Stop current speech |

Voice uses **pw-record** (mic) and **espeak-ng** (speaker) — both come from SteamOS repos, no compiling.

STT uses Google Web Speech by default (needs Wi‑Fi). For offline speech, install a [Vosk model](https://alphacephei.com/vosk/models) and set `CHAHLIE_VOSK_MODEL` in `.env`.

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
| Button | Maps to |
|--------|---------|
| A | Enter |
| B | Escape |
| X | F4 (Talk) |
| Y | F1 (Help) |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `gcc failed` / PyAudio error | Use the **release tarball** — PyAudio is no longer required |
| Install stops at pacman | Re-run `./install.sh` from v2.5.2+ — skips pacman when tools already exist |
| `steamos-readonly` / pacman fails | Install continues anyway; typed chat works, voice is optional |
| No mic | Usually pre-installed on SteamOS. If missing: `sudo steamos-readonly disable && sudo pacman -S pipewire-pulse` |
| No voice out | `sudo pacman -S espeak-ng` (often already installed) |
| Slow responses | Use `qwen3.5:cloud` or local `qwen3:8b` |

## Dev / git install (optional)

```bash
git clone https://github.com/AaronGrace978/Chahlie.git
cd Chahlie
bash scripts/install-steam-deck.sh
chahlie-deck
```

## Build a release tarball yourself

```bash
bash scripts/build-deck-release.sh
# → dist/chahlie-deck-VERSION-linux-x86_64.tar.gz
```

Made with love by **Cursor Boston** ⚾
