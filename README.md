<div align="center">

<img src="assets/chahlie-banner.png" alt="Chahlie - Your Wicked Smart Coding Assistant" width="100%">

# 🏙️ Chahlie - The Boston Coding Agent

**An agentic AI coding assistant with authentic Boston personality**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Powered by Ollama](https://img.shields.io/badge/Powered%20by-Ollama%20Cloud-purple.svg)](https://ollama.com)
[![Made with Cursor](https://img.shields.io/badge/Made%20with-Cursor-blue.svg)](https://cursor.com)

*Version 2.3.0 "Southie Sharp"*

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

💡 Learning: write_file works well with these arguments
```

</div>

## What is Chahlie?

Chahlie (Boston pronunciation of "Charlie", like [Charlie on the MTA](https://en.wikipedia.org/wiki/M.T.A._(song))) is a terminal-based AI coding agent that helps you write wicked good code. Built with authentic Boston personality, Chahlie is your helpful, slightly sarcastic coding buddy who never leaves your terminal.

**NEW IN 2.0: MEMORY & SELF-IMPROVEMENT!** 🧠

Chahlie now learns from every interaction, adapts to YOUR coding style, and continuously improves through self-reflection. The more you work together, the better he gets - like a teammate who actually pays attention!

**NEW IN 2.1: SELF-VERIFICATION LOOP!** ✅

Every Python file Chahlie writes is automatically syntax-checked and scanned for undefined names *before* he declares the task done. Syntax errors force a retry; undefined-name warnings are surfaced inline so he can fix typos like `weaknesses_counts` vs `weakness_counts` without you ever seeing them. No more shipping broken code.

**NEW IN 2.3: SOUTHIE SHARP!** 🦈

Another sixteen enhancements focused on sharp feedback and safer edits:

- ✂️ **Diffs in every write** - `write_file` and `edit_file` now show a unified diff, not just a character count
- 🪟 **`open_file` tool** - actually launches Notepad/TextEdit/xdg-open when you say "open it up"
- 🌀 **Git-aware tools** - `git_status`, `git_diff`, `git_log` as first-class tools
- 🧹 **Real linter integration** - `lint_code` runs ruff/mypy/eslint when available (not just AST checks)
- 📂 **Rich `list_directory`** - now shows file sizes and modified times
- 👁️ **`watch_file` tool** - tail a log or poll a URL until a pattern appears
- 🔮 **Fuzzy "did you mean?"** - missing-file errors include close matches
- 💡 **Smart retry hints** - recognizes `git push` no-upstream, `ModuleNotFoundError`, `EADDRINUSE`, etc.
- 🚫 **Tool-call dedupe** - repeated `read_file` on the same path within a turn returns the cache
- ⏪ **`/undo` command** - revert the most recent write_file / edit_file
- 🌿 **Session branching** - `/fork <name>`, `/switch <name>`, `/branches` to snapshot exploratory conversations
- 🎨 **Syntax highlighting** - `read_file` output is colorized by language
- 🧭 **Project-scoped memory** - walks up to git root, so running from a subdir still uses the same memory
- 🎯 **Model router** - optional `CHAHLIE_SMALL_MODEL` handles trivial chat, big model reserved for code
- 🔁 **Test-failure auto-analysis** - when `run_tests` fails, a sub-agent drops a one-paragraph root-cause analysis into the output
- 🏷️ **Banner version fix** - no more "v1.0.0 Green Monstah" five versions later

**NEW IN 2.2: THE BIG DIG!** 🏗️

A full overhaul focused on speed, safety, and smarts. Chahlie now:

- ⚡ **Streams** responses token-by-token so you see him thinking live
- ✂️ **Edits files surgically** with `edit_file` instead of rewriting whole files
- 🛑 **Blocks dangerous commands** (`rm -rf`, force-push, `DROP TABLE`, etc.) until you approve
- 🧠 **Auto-primes the project** on startup (detects language/framework/layout so he doesn't ask "what is this repo?")
- 💰 **Tracks tokens and est. cost** per session via `/cost`
- 🗜️ **Compacts older history** automatically so long sessions don't blow the context window
- 🔍 **Verifies JS/TS/Go/Rust/JSON/YAML** (not just Python) when toolchains are installed
- 🧪 **Runs your tests** with `run_tests` (auto-detects pytest/npm/cargo/go)
- 🤝 **Delegates exploration** to throwaway sub-agents that return clean summaries
- 🧩 **Loads plugins** from `~/.chahlie/plugins/` to add your own tools
- ↩️ **Snapshots + rolls back** file edits if a multi-file change fails halfway through
- 🔮 **Semantic memory retrieval** (optional, `--semantic-memory`) - recalls relevant learnings by embedding similarity
- 🖥️ **Experimental Textual TUI** (optional, `--tui`) with a scrollable log and live cost meter

## Features

- 🤖 **Full Agentic Capabilities** - Read/write files, run commands, search code
- 🗣️ **Boston Personality** - Authentic Boston slang and attitude
- 🎨 **Beautiful Terminal UI** - Clean, styled interface with Fenway Green theme
- ⚡ **Powered by Ollama Cloud** - Access top AI models via Ollama
- 🔧 **Tool Use** - Watch Chahlie work with real-time tool execution
- 🌐 **Browser Tools** - Open URLs and search the web
- 🔄 **Multiple Providers** - Ollama Cloud, Local Ollama, or Anthropic Claude
- 🧠 **MEMORY SYSTEM** - Persistent learning across sessions
- 📊 **USER PROFILE** - Learns YOUR coding style and preferences
- 💡 **SELF-REFLECTION** - Analyzes own performance and improves
- 🔄 **ADAPTIVE PROMPTING** - Adjusts behavior based on learnings
- ✅ **SELF-VERIFICATION** - Auto-checks Python + JS/TS/Go/Rust/JSON/YAML before declaring done
- ✂️ **SURGICAL EDITS** - `edit_file` replaces exact strings instead of rewriting entire files
- 🛑 **APPROVAL MODE** - Dangerous commands require your explicit OK
- ⚡ **STREAMING** - Live token-by-token responses
- 🗜️ **AUTO-COMPACTION** - Old turns summarized on the fly to keep the context window sane
- 💰 **COST METER** - Running token + dollar estimate per session (`/cost`)
- 🤝 **SUB-AGENT DELEGATION** - Throwaway agents for exploration without context pollution
- 🧩 **PLUGIN SYSTEM** - Drop Python files in `~/.chahlie/plugins/` to add your own tools
- ↩️ **TRANSACTIONAL EDITS** - Snapshot + rollback for multi-file changes
- 🖥️ **OPTIONAL TUI** - Launch with `--tui` for a Textual-powered terminal app
- 🪟 **OS file opener** - `open_file` launches your default app on Win/macOS/Linux
- 🌀 **GIT-AWARE TOOLS** - First-class `git_status`, `git_diff`, `git_log`
- 🧹 **REAL LINTER INTEGRATION** - `lint_code` runs ruff/mypy/eslint
- 👁️ **WATCH FILES** - Tail logs or poll URLs until a pattern hits
- 🔮 **FUZZY "DID YOU MEAN?"** - Close-match suggestions on missing files
- 💡 **SMART RETRY HINTS** - Actionable fixes on common shell failures
- ⏪ **UNDO LAST WRITE** - `/undo` reverts the most recent file change
- 🌿 **SESSION BRANCHING** - `/fork`, `/switch`, `/branches`
- 🎨 **SYNTAX-HIGHLIGHTED reads** - Colorized `read_file` output
- 🎯 **MODEL ROUTER** - Optional small model for trivial chat
- 🔁 **TEST-FAILURE ANALYSIS** - Sub-agent root-causes failing tests inline

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

# Disable memory system (if needed)
python -m chahlie --no-memory
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
| **🧠 `/memory`** | **Show memory status and learnings** |
| **🧠 `/profile`** | **View your learned coding profile** |
| **🧠 `/reflect`** | **See Chahlie's self-reflection** |
| **🧠 `/learnings`** | **View all learned patterns** |
| **🏗️ `/cost`** | **Show token count and estimated session cost** |
| **🏗️ `/primer`** | **Show the auto-detected project context** |
| **🏗️ `/plugins`** | **List loaded plugins and any warnings** |
| **🦈 `/undo`** | **Revert the most recent write_file / edit_file** |
| **🦈 `/fork <name>`** | **Snapshot the current conversation to a branch** |
| **🦈 `/switch <name>`** | **Restore a saved conversation branch** |
| **🦈 `/branches`** | **List saved conversation branches** |

### CLI flags (v2.2)

```bash
python -m chahlie --help

  --no-stream          Disable token streaming
  --no-approval        Disable approval prompts for dangerous commands
  --llm-reflection     Enable LLM-based reflection on failures
  --semantic-memory    Enable embedding-based memory retrieval
  --tui                Launch the experimental Textual TUI
```

All of these also honor environment variables (`CHAHLIE_STREAMING`,
`CHAHLIE_REQUIRE_APPROVAL`, `CHAHLIE_LLM_REFLECTION`, `CHAHLIE_SEMANTIC_MEMORY`).

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

💡 Learning: write_file works well with these arguments

╔═══════════════════════════════════════════════════════════════╗
║   ✓ write_file succeeded                                      ║
║   ───────────────────────                                     ║
║   Successfully wrote 847 characters to weather.py             ║
╚═══════════════════════════════════════════════════════════════╝
```

## 🧠 Memory System (NEW!)

Chahlie's memory system is what separates him from every other coding assistant out there. While other tools forget everything when you close the terminal, Chahlie **remembers, learns, and improves**.

### What Chahlie Remembers:

1. **Session History** - Every conversation, every file modified, every command run
2. **Your Coding Style** - Naming conventions, code structure, documentation habits
3. **Tool Preferences** - Which tools work well, which ones need adjustment
4. **Communication Style** - Do you like verbose explanations or quick answers?
5. **Workflow Patterns** - TDD, refactor-first, or move-fast-and-break-things?

### How It Works:

```
┌─────────────────────────────────────────────────────────────┐
│                    CHAHLIE MEMORY SYSTEM                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. OBSERVE → Watches every interaction                     │
│                                                             │
│  2. REFLECT → Analyzes what worked, what didn't             │
│                                                             │
│  3. LEARN → Stores patterns with confidence scores          │
│                                                             │
│  4. ADAPT → Adjusts system prompt with learnings            │
│                                                             │
│  5. IMPROVE → Generates self-improvement plans              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Memory Commands:

#### `/memory` - Check Memory Status
```
🧠 CHAHLIE MEMORY STATUS

Sessions: 15
Learnings: 47
Reflections: 23
Has Context: True

Recent Learnings:
• User prefers variable_style: snake_case
• User prefers type_hints: uses_type_hints
• User prefers communication: concise
• write_file works well with these arguments
• run_command needs validation before execution
```

#### `/profile` - Your Coding Profile
```
📋 YOUR CODING PROFILE

Coding Style:
• User prefers variable_style: snake_case
• User prefers type_hints: uses_type_hints
• User prefers documentation: uses_docstrings

Communication:
• User prefers communication: concise

Workflow:
• User prefers workflow: test_driven

Confidence: 78%

The more we work together, the better I know ya!
```

#### `/reflect` - Chahlie's Self-Reflection
```
🤔 CHAHLIE'S SELF-REFLECTION

Focus Areas (what I'm working on):
• Low tool success rate (high priority)
• Command execution issues (medium priority)

Keep Doing (my strengths):
• High success rate on tool usage
• Clear communication

Reflections Analyzed: 23

Always improvin', always learnin'!
```

#### `/learnings` - All Learned Patterns
```
📚 ALL LEARNINGS (47 total)

1. [code_naming] User prefers variable_style: snake_case
   Confidence: 89% | Seen: 15x

2. [code_style] User prefers type_hints: uses_type_hints
   Confidence: 92% | Seen: 22x

3. [tool_success] write_file works well with these arguments
   Confidence: 78% | Seen: 8x
```

### Memory Storage:

All memory is stored locally in `.chahlie/memory/`:
```
.chahlie/
└── memory/
    ├── sessions.json       # Session history
    ├── learnings.json      # Learned patterns
    ├── context.json        # Project context
    ├── reflections.json    # Self-reflections
    └── user_profile.json   # Your coding profile
```

## ✅ Self-Verification Loop (NEW IN 2.1!)

Small LLMs ship typos. Qwen might write `weaknesses_counts` one line and `weakness_counts` the next and not notice. Chahlie now *does* notice - before you ever see the bug.

### How It Works

```
┌───────────────────────────────────────────────────────────────┐
│               CHAHLIE SELF-VERIFICATION LOOP                  │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  Chahlie writes a .py file                                    │
│              ↓                                                │
│  Auto-verifier runs (zero deps, pure stdlib ast)              │
│              ↓                                                │
│  ┌─ Syntax error?   → tool FAILS, agent MUST fix before done  │
│  ├─ Undefined name? → warning surfaced inline in tool output  │
│  └─ Clean?          → proceed as normal                       │
│              ↓                                                │
│  Chahlie fixes issues, optionally re-runs `verify_code`       │
│              ↓                                                │
│  ONLY THEN declares task complete                             │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### What Gets Checked

| Check | Severity | What it catches |
|-------|----------|-----------------|
| `E-SYNTAX` | Error (fails the write) | `def foo(:` and friends |
| `W-UNDEF` | Warning (inline in output) | Referenced names never bound anywhere (typos, renamed vars, missing imports) |
| Star-imports | Auto-skip | `from x import *` disables name check to avoid false positives |

### The `verify_code` Tool

Chahlie can also explicitly re-verify a file after fixes:

```python
verify_code(path="chahlie/memory/reflection.py")
# → "✓ chahlie/memory/reflection.py passed verification (no issues)"
```

### Real Example

During the v2.1 development session, Chahlie (running on qwen3.5) self-modified to add the memory system and shipped 5 bugs in one go:
- `weaknesses_counts` vs `weakness_counts` (typo)
- `import_imports` vs `import_lines` (wrong variable)
- Plus three more schema/lifecycle bugs

The verifier catches the first two **before** the file is considered successfully written. The regression test in `test_verifier.py` uses these exact bugs as fixtures to make sure Chahlie never regresses.

## Capabilities

Chahlie can help you with:

- **File Operations** - Read, write, and search files
- **Code Search** - Find code by pattern or content
- **Shell Commands** - Run git, npm, pip, tests, and more
- **Project Exploration** - Navigate and understand codebases
- **Code Writing** - Generate, refactor, and debug code
- **🧠 Learning Your Style** - Adapts to YOUR preferences
- **🧠 Self-Improvement** - Gets better with every session
- **✅ Self-Verification** - Catches its own typos before you see them

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
- ✅ *"I'm learnin' from every interaction, boss!"*

## Contributing

Contributions are welcome! This is a **Cursor Boston** community project.

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Adding Boston personality and slang
- Supporting new AI providers
- Improving the UI
- Memory system enhancements
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

> *"The memory system is a game-changer. Chahlie actually REMEMBERS how I like my code!"*
> — **Senior Software Engineer**

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

### Version 2.1.0 "Check Ya Work" (CURRENT)
**✅ SELF-VERIFICATION LOOP: Chahlie checks his own code before shipping**

- ✅ **Verifier module** (`chahlie/verifier.py`) - AST-based syntax + undefined-name detection, zero external deps
- ✅ **Auto-verify on `write_file`** - Python files are checked automatically after every write
- ✅ **Fail-fast on syntax errors** - Agent loop is forced to fix before declaring done
- ✅ **Warnings surfaced inline** - Undefined names appear in tool output so the LLM can self-correct
- ✅ **New `verify_code` tool** - Explicit re-check after fixes
- ✅ **CODE QUALITY PROTOCOL** - Added to system prompt so Chahlie knows to act on verification feedback
- 🧪 **Regression tests** (`test_verifier.py`) - 9 tests using real Chahlie bugs as fixtures
- 🐛 **Fixed pre-existing `SKYLINE` crasher in `ui.py`** - caught immediately by the new verifier

### Version 2.0.0 "Self-Aware Southie"
**🧠 MAJOR UPDATE: MEMORY & SELF-IMPROVEMENT SYSTEM**

- ✨ **Memory Manager** - Persistent session storage
- ✨ **Reflection Engine** - Self-analysis and improvement
- ✨ **Pattern Learner** - Learns YOUR coding style
- ✨ **Adaptive Prompting** - Adjusts behavior based on learnings
- ✨ **New Commands** - `/memory`, `/profile`, `/reflect`, `/learnings`
- ✨ **Real-time Learning** - Shows learnings as they happen
- 🎨 **Updated UI** - Memory status indicators

### Version 1.0.0 "Green Monstah"
- Initial release
- Full agentic capabilities
- Boston personality
- Multiple AI backends
- Beautiful terminal UI

See [CHANGELOG.md](CHANGELOG.md) for full version history.

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

*"Keep writin' wicked good code, kehd! And remember - I'm learnin' from every interaction!"*

</div>
