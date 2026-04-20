# Changelog

All notable changes to Chahlie will be documented in this file.

## [2.1.0] "Check Ya Work" - 2026-04-20

### Added
- ✅ **Self-verification loop** - Every Python file written by `write_file` is
  auto-verified for syntax errors and undefined names before the tool returns.
- ✅ **`chahlie/verifier.py`** - New module with AST-based static analysis:
  - `verify_python()` - syntax check + undefined-name detection
  - `verify_file()` - dispatches by file extension
  - Conservative scope tracking across imports, arg lists, comprehensions,
    `for`/`with`/`except` targets, walrus, `global`/`nonlocal`.
  - Auto-skips undefined-name check when `from x import *` is present
    (avoids false positives).
  - Zero external dependencies (pure stdlib `ast`).
- ✅ **`verify_code` tool** - Explicit re-verification tool the agent can call
  after fixes to confirm a file is clean.
- ✅ **CODE QUALITY PROTOCOL** - New section appended to `SYSTEM_PROMPT`
  telling Chahlie to treat verification errors/warnings as non-negotiable fixes
  before declaring a task complete.
- 🧪 **`test_verifier.py`** - 9 regression tests using real bugs from the 2.0.0
  self-modification session as fixtures (e.g. `weaknesses_counts` typo,
  `import_imports` undefined reference).

### Changed
- `write_file` now returns `success=False` with a structured error report when
  a Python file has syntax errors (the file is still written to disk, but the
  agent loop is forced to surface and fix the error).
- `write_file` appends a `VERIFICATION WARNINGS:` section to its output when
  undefined-name warnings are detected (success stays `True`, but the LLM
  sees the issues in context).

### Fixed
- `chahlie/ui.py` - `print_skyline()` referenced undefined `SKYLINE` instead
  of `BOSTON_SKYLINE`. Would have crashed on first call. Caught by the new
  verifier running against the existing codebase during dogfooding.

### Ignored
- `.chahlie/` - Runtime memory directory is now in `.gitignore` (per-user,
  per-project state; not source).

---

## [2.0.0] "Self-Aware Southie" - 2026-04-20

### Added
- 🧠 **Memory system** (`chahlie/memory/`) - Persistent learning across sessions
  - `memory_manager.py` - Session history, learnings, reflections, project context
  - `reflection.py` - Tool-use reflection, feedback sentiment, improvement plans
  - `pattern_learner.py` - Regex-based user coding style profile with confidence scoring
- 🧠 **Memory commands** - `/memory`, `/profile`, `/reflect`, `/learnings`
- 🧠 **Adaptive prompting** - System prompt is enhanced at runtime with
  learned user patterns and recent reflections.
- 🧠 **Per-tool-call reflection** - Every tool use is analyzed for insights
  that feed back into the next turn.

### Changed
- `ChahlieAgent.__init__` accepts `enable_memory` flag (defaults to `True`).
- CLI exposes `--no-memory` flag.
- Version bumped to 2.0.0 "Self-Aware Southie".

---

## [1.0.0] "Green Monstah" - 2026-04-15

### Added
- 🚀 Initial release of Chahlie - The Boston Coding Agent
- 🤖 Full agentic AI coding capabilities
- 🗣️ Authentic Boston personality with wicked good slang
- ☁️ Ollama Cloud support with multiple models (glm-5.1, qwen3.5, etc.)
- 🦙 Local Ollama support for offline/privacy use
- 🤖 Anthropic Claude support (legacy)
- 📁 File operations: read, write, search, create directories
- 🔍 Code search: find files and content
- 💻 Shell commands: run git, npm, pip, tests, etc.
- 🌐 Browser tools: open URLs and web search
- 🎨 Beautiful terminal UI with Boston skyline
- 🏙️ Cursor Boston branding throughout
- 📝 Commands: /help, /about, /fact, /providers, /cursorboston
- 📖 CONTRIBUTING.md for open source contributors
- 🔧 Cursor rules for development

### Boston Personality Features
- Drop your R's: cah, pahk, smaht, hahd
- Boston slang: kehd, wicked, pissa, no problemo
- Sports references: Red Sox, Celtics, Bruins, Patriots
- Local culture: Dunkin', the T, Fenway, Southie
- Encouragement with Boston flair

---

*Made with ❤️ in Boston by Cursor Boston*
