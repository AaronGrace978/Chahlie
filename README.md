<div align="center">

<img src="assets/chahlie-banner.png" alt="Chahlie - Your Wicked Smart Coding Assistant" width="100%">

# 🏙️ Chahlie - The Boston Coding Agent

**An agentic AI coding assistant with authentic Boston personality**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Powered by Ollama](https://img.shields.io/badge/Powered%20by-Ollama%20Cloud-purple.svg)](https://ollama.com)

*Version 1.0.0 "Green Monstah"*

---

### 🏟️ Official Product of Cursor Boston

**Cursor Boston Ambassador: Robert Hunt**

**CMO: Aaron Grace**

---

</div>

## What is Chahlie?

Chahlie (Boston pronunciation of "Charlie", like [Charlie on the MTA](https://en.wikipedia.org/wiki/M.T.A._(song))) is a terminal-based AI coding agent that helps you write wicked good code. Built with authentic Boston personality, Chahlie is your helpful, slightly sarcastic coding buddy who never leaves your terminal.

## Features

- 🤖 **Full Agentic Capabilities** - Read/write files, run commands, search code
- 🗣️ **Boston Personality** - Authentic Boston slang and attitude
- 🎨 **Beautiful Terminal UI** - Clean, styled interface with Fenway Green theme
- ⚡ **Powered by Ollama Cloud** - Access top AI models via Ollama
- 🔧 **Tool Use** - Watches Chahlie work with real-time tool execution

## Installation

```bash
# Clone the repo
git clone https://github.com/AaronGrace978/Chahlie.git
cd Chahlie

# Install dependencies
pip install -r requirements.txt

# Set up your API key
cp .env.example .env
# Edit .env and add your OLLAMA_API_KEY from https://ollama.com/settings/keys

# Run Chahlie
python run.py
```

## Usage

```bash
# Start Chahlie
python run.py

# Or run as a module
python -m chahlie

# Check version
python -m chahlie --version

# Show about info
python -m chahlie --about
```

### Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help message |
| `/clear` | Clear conversation history |
| `/fact` | Get a random Boston fact |
| `/about` | About Chahlie |
| `/exit` | Exit Chahlie |

## Example Session

```
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   CHAHLIE                                                     ║
║   ───────                                                     ║
║   Ayyy, what's up kehd?                                       ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝

You: Can you help me create a Python script that fetches weather data?

💭 Hang on kehd, I'm workin' on it...

╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   CHAHLIE                                                     ║
║   ───────                                                     ║
║   No problemo! Let me whip that up for ya. I'll create a     ║
║   clean weather fetcher script...                             ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════╗
║   ✏️ write_file                                                ║
║   ─────────────                                               ║
║   path: weather.py                                            ║
║   content: (creating file...)                                 ║
╚═══════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════╗
║   ✓ write_file succeeded                                      ║
║   ───────────────────────                                     ║
║   Successfully wrote 847 characters to weather.py             ║
╚═══════════════════════════════════════════════════════════════╝
```

## Capabilities

Chahlie can help you with:

- **File Operations** - Read, write, and search files
- **Code Search** - Find code by pattern or content
- **Shell Commands** - Run git, npm, pip, tests, and more
- **Project Exploration** - Navigate and understand codebases
- **Code Writing** - Generate, refactor, and debug code

## Configuration

Create a `.env` file in the project root:

```bash
# Get your API key from https://ollama.com/settings/keys
OLLAMA_API_KEY=your-ollama-cloud-api-key-here

# Choose your model (optional, defaults to qwen3-coder-next)
OLLAMA_MODEL=qwen3-coder-next
```

### Available Ollama Cloud Models

| Model | Description | Best For |
|-------|-------------|----------|
| `glm-5.1` | **SOTA for agentic engineering** - SWE-Bench Pro leader | Default choice |
| `qwen3.5` | Multimodal powerhouse (6.3M pulls) - vision + tools | General coding |
| `devstral-small-2` | 24B model, excels at multi-file editing | Large codebases |
| `gemma4` | Frontier performance from Google - vision + tools | Reasoning |
| `deepseek-v3.2` | Efficient reasoning + agent performance | Complex tasks |
| `minimax-m2.7` | Latest for coding & agentic workflows | Productivity |

See all models at [ollama.com/search?c=cloud](https://ollama.com/search?c=cloud)

## Tech Stack

- **Python 3.10+**
- **Ollama Cloud** - AI backbone with top models
- **Rich** - Beautiful terminal UI
- **Click** - CLI framework

## Boston Flavor

Chahlie speaks with authentic Boston flair:

- ✅ *"Wicked pissa! That worked perfectly."*
- ✅ *"No problemo, kehd!"*
- ✅ *"That crashed hardah than the Big Dig budget."*
- ✅ *"Crushed it! Just like the '04 Sox."*

## Contributing

Contributions are welcome! This is a Cursor Boston community project.

## License

MIT License - Use it, modify it, make it wicked bettah.

---

<div align="center">

### 🏙️ Built with ❤️ in Boston

**[Cursor Boston](https://cursorboston.com)** - The home for Boston developers using Cursor

*Cursor Boston Ambassador: Robert Hunt • CMO: Aaron Grace*

---

*"Keep writin' wicked good code, kehd!"*

</div>
