# Chahlie Steam Deck Edition

**v2.5.3** — extract, double-click, chat. That's it.

## The easy way (3 steps)

1. **Download** from [Releases](https://github.com/AaronGrace978/Chahlie/releases):
   `chahlie-deck-2.5.3-linux-x86_64.tar.gz`

2. **Extract** the zip in Downloads (right-click → Extract)

3. **Double-click** `START-CHAHLIE.sh`
   - First launch installs automatically (~1 minute)
   - The **UI opens** — a full-screen chat app (Textual TUI)
   - Paste your free API key when the welcome screen appears
   - Get a key at: https://ollama.com/settings/keys

After the first run, use the **"Start Chahlie"** icon on your Desktop.

---

## What you'll see

A proper app UI with:
- Chat window (type or talk to Chahlie)
- Toolbar buttons: Help · Clear · Memory · 🎤 Talk · 🔊 TTS · Quit
- Gamepad-friendly (map A=Enter, X=F4 Talk in Steam Input)

No `install.sh`. No `nano`. No pacman. No terminal required after the first double-click.

---

## If double-click doesn't work

Open Konsole and run:

```bash
cd ~/Downloads/chahlie-deck-*-linux
chmod +x START-CHAHLIE.sh
./START-CHAHLIE.sh
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Permission denied | `chmod +x START-CHAHLIE.sh` |
| First run slow | Normal — downloading Python packages once |
| No API key screen | Delete `~/.local/share/chahlie/.env` and restart |
| Want to re-setup | Delete `~/.local/share/chahlie/venv/.chahlie-ready` and restart |

Made with love by **Cursor Boston** ⚾
