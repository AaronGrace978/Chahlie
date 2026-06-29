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

---

## You clicked the wrong file if Kate opened

| Wrong (opens Kate) | Right (runs Chahlie) |
|--------------------|----------------------|
| `START-CHAHLIE.sh` | `Start Chahlie.desktop` |
| Any `.py` file | `Start Chahlie.desktop` |
| `README-FIRST.txt` | `Start Chahlie.desktop` |

Kate is a **text editor**. You want the **`.desktop`** launcher file.
