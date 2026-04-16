<div align="center">

<img src="assets/chahlie-banner.png" alt="Chahlie - Your Wicked Smart Coding Assistant" width="100%">

# 🏙️ Chahlie - The Boston Coding Agent

**An agentic AI coding assistant with authentic Boston personality**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Powered by Ollama](https://img.shields.io/badge/Powered%20by-Ollama%20Cloud-purple.svg)](https://ollama.com)
[![Made with Cursor](https://img.shields.io/badge/Made%20with-Cursor-blue.svg)](https://cursor.com)

*Version 1.0.0 "Green Monstah"*

---

### 🏟️ Official Product of Cursor Boston

**Cursor Boston Ambassador: Roger Hunt** | **CMO: Aaron Grace**

[![Cursor Boston](https://img.shields.io/badge/Cursor%20Boston-Website-cyan.svg)](https://cursorboston.com)
[![Follow on X](https://img.shields.io/badge/Follow-@CursorBoston-black.svg)](https://x.com/CursorBoston)
[![Download Cursor](https://img.shields.io/badge/Download-Cursor%20IDE-blue.svg)](https://cursor.com/downloads)

---

</div>

## 🎬 Demo

<div align="center">

<!-- TODO: Add demo GIF here -->
*Demo GIF coming soon! Run `python run.py` to see Chahlie in action.*

```
┌─────────────────────────── CHAHLIE ───────────────────────────┐
│ Ayyy, what's up kehd? Ready to write some wicked good code?   │
└───────────────────────────────────────────────────────────────┘
You: Help me create a REST API

> On it like Big Papi on a fastball...
┌─────────────────────────── CHAHLIE ───────────────────────────┐
│ No problemo! Let me bang that out for ya...                   │
└───────────────────────────────────────────────────────────────┘
```

</div>

## What is Chahlie?

Chahlie (Boston pronunciation of "Charlie", like [Charlie on the MTA](https://en.wikipedia.org/wiki/M.T.A._(song))) is a terminal-based AI coding agent that helps you write wicked good code. Built with authentic Boston personality, Chahlie is your helpful, slightly sarcastic coding buddy who never leaves your terminal.

## Features

- 🤖 **Full Agentic Capabilities** - Read/write files, run commands, search code
- 🗣️ **Boston Personality** - Authentic Boston slang and attitude
- 🎨 **Beautiful Terminal UI** - Clean, styled interface with Fenway Green theme
- ⚡ **Powered by Ollama Cloud** - Access top AI models via Ollama
- 🔧 **Tool Use** - Watch Chahlie work with real-time tool execution
- 🌐 **Browser Tools** - Open URLs and search the web
- 🔄 **Multiple Providers** - Ollama Cloud, Local Ollama, or Anthropic Claude

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
| `/providers` | View available AI providers |
| `/cursorboston` | Learn about Cursor Boston |
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
cp .env.example .env
```

### AI Providers

Chahlie supports multiple AI backends:

#### 1. Ollama Cloud (Recommended)
```bash
CHAHLIE_BACKEND=ollama-cloud
OLLAMA_API_KEY=your-key-here  # Get from https://ollama.com/settings/keys
OLLAMA_MODEL=glm-5.1
```

#### 2. Local Ollama
```bash
CHAHLIE_BACKEND=ollama-local
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
```

#### 3. Anthropic Claude
```bash
CHAHLIE_BACKEND=anthropic
ANTHROPIC_API_KEY=your-key-here
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

Contributions are welcome! This is a **Cursor Boston** community project.

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Adding Boston personality and slang
- Supporting new AI providers
- Improving the UI
- Boston flavor guidelines

```bash
# Quick start for contributors
git clone https://github.com/AaronGrace978/Chahlie.git
cd Chahlie
pip install -r requirements.txt
cp .env.example .env
# Add your OLLAMA_API_KEY to .env
python run.py
```

## 💬 What People Are Saying

> *"Chahlie helped me refactor my entire codebase in half the time. Wicked pissa!"*
> — **Boston Developer**

> *"Finally, a coding assistant that speaks my language. No problemo!"*
> — **Cursor Boston Community Member**

> *"The Boston personality makes coding fun again. Crushed it!"*
> — **Open Source Contributor**

*Want to share your experience? Open a PR to add your testimonial!*

## 🚀 Featured Projects Built with Chahlie

Projects built using Chahlie will be featured here! 

**Want your project featured?** Open an issue or PR with:
- Project name and link
- Brief description
- How Chahlie helped

*Be the first to have your project featured!*

## 🤝 Join the Community

<div align="center">

[![Join Cursor Boston](https://img.shields.io/badge/Join-Cursor%20Boston%20Community-cyan?style=for-the-badge)](https://cursorboston.com)
[![Follow @CursorBoston](https://img.shields.io/badge/Follow-@CursorBoston-black?style=for-the-badge)](https://x.com/CursorBoston)
[![Star on GitHub](https://img.shields.io/badge/⭐_Star-This%20Repo-yellow?style=for-the-badge)](https://github.com/AaronGrace978/Chahlie)

</div>

- 🌐 **Website**: [cursorboston.com](https://cursorboston.com)
- 🐦 **Twitter/X**: [@CursorBoston](https://x.com/CursorBoston)
- 💻 **GitHub**: [Chahlie Repo](https://github.com/AaronGrace978/Chahlie)

## 📋 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.

**Current Version:** 1.0.0 "Green Monstah"

## License

MIT License - Use it, modify it, make it wicked bettah.

---

<div align="center">

### 🏙️ Built with ❤️ in Boston

**[Cursor Boston](https://cursorboston.com)** - Boston's Home for AI-Powered Development

*Cursor Boston Ambassador: Roger Hunt • CMO: Aaron Grace*

---

#### Connect With Us

[![Cursor Boston Website](https://img.shields.io/badge/🌐_Website-cursorboston.com-cyan?style=for-the-badge)](https://cursorboston.com)
[![Follow on X](https://img.shields.io/badge/🐦_Twitter-@CursorBoston-black?style=for-the-badge)](https://x.com/CursorBoston)
[![GitHub](https://img.shields.io/badge/💻_GitHub-Chahlie-green?style=for-the-badge)](https://github.com/AaronGrace978/Chahlie)

---

#### Made with Cursor

[![Download Cursor](https://img.shields.io/badge/⬇️_Download_Cursor-cursor.com-blue?style=for-the-badge)](https://cursor.com/downloads)
[![Cursor Website](https://img.shields.io/badge/🌐_Cursor-The_AI_Code_Editor-purple?style=for-the-badge)](https://cursor.com)

---

*"Keep writin' wicked good code, kehd!"*

</div>
