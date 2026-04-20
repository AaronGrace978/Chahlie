# Changelog

All notable changes to Chahlie will be documented in this file.

## [2.2.0] "Big Dig" - 2026-04-20

Major expansion pass - fifteen enhancements in one sprint, all with
regression tests, while keeping the existing v2.1 memory + verification
systems untouched and green.

### Added

#### Tier 1 - everyday quality-of-life
- ✂️ **`edit_file` tool** (`chahlie/tools.py`) - surgical string replacement
  that requires an exactly-unique match. Cheaper and safer than `write_file`
  for modifying existing files. Auto-verifies the result on Python files.
- 🛑 **Approval mode for dangerous commands** (`chahlie/tools.py`) - matches
  `rm -rf`, `git push --force`, `git reset --hard`, `DROP TABLE`, `dd`, `mkfs`,
  `:(){:|:&};:`, `shutdown`, `sudo`, `chmod 777`, and raw-device redirects.
  Refuses by default if no approval prompter is installed. Interactive prompt
  is wired into the classic CLI; disable with `--no-approval` or
  `CHAHLIE_REQUIRE_APPROVAL=false`.
- 🧠 **Project auto-primer** (`chahlie/project_primer.py`) - scans the repo on
  startup for language/framework/branch/layout signals and injects a concise
  "PROJECT CONTEXT" block into the system prompt, so Chahlie doesn't waste
  turns asking what the project is. Runs on every session, zero dependencies.
- 🔍 **Multi-language verifier** (`chahlie/verifier.py`) - adds `verify_json`,
  `verify_yaml`, `verify_javascript` (`node --check` / `tsc --noEmit`),
  `verify_go` (`gofmt -e`), and `verify_rust` (`rustc --emit=dep-info`).
  Toolchain probes are graceful - a missing `node`/`tsc`/`gofmt`/`rustc`
  returns a clean result rather than failing.
- ⚡ **Streaming responses** (`chahlie/agent.py`, `chahlie/__main__.py`) -
  token-by-token streaming over the Ollama backends; disable with
  `--no-stream` or `CHAHLIE_STREAMING=false`. Streaming deltas are printed
  inline and flushed cleanly before tool results/panels.

#### Tier 2 - smarter
- 🗜️ **Context compaction** (`chahlie/context_manager.py`) - when dialogue
  history exceeds `COMPACT_THRESHOLD_CHARS` (default ~24KB), older turns get
  summarized by a cheap backend call into a single "earlier conversation
  summary" system message. Most-recent N turns are preserved verbatim.
- 🤔 **LLM-based reflection** - opt-in (`--llm-reflection` /
  `CHAHLIE_LLM_REFLECTION=true`). On tool/API failures, Chahlie asks the
  backend for a one-sentence post-mortem and prepends it to the
  rule-based reflection insights.
- 🧪 **`run_tests` tool** (`chahlie/tools.py`) - auto-detects pytest,
  `npm test`, `cargo test`, or `go test ./...` based on manifest files and
  runs the suite with a 5-minute timeout. Truncates output to the last 4KB.
- 🔮 **Semantic memory retrieval** (`chahlie/memory/semantic.py`) - tiny
  in-memory vector store using the configured Ollama embedding model
  (default: `nomic-embed-text`). Opt-in (`--semantic-memory`). When enabled,
  replaces the "dump all learnings" approach with a top-K cosine-similarity
  retrieval against the current user message. Silently disables itself if
  the embedding endpoint is unavailable (non-fatal).
- 📚 **Few-shot examples in `SYSTEM_PROMPT`** (`chahlie/personality.py`) -
  concrete good/bad examples for verification feedback, approval blocks, and
  delegation. Meant to ground smaller models that don't follow abstract rules.

#### Tier 3 - ambitious
- 🤝 **Sub-agent delegation** (`chahlie/subagent.py` + `delegate` tool) -
  spawns a fresh `ChahlieAgent(enable_memory=False)` for an exploration task,
  runs it to completion with a turn limit, and returns ONE synthesized
  answer. Individual tool events don't propagate to the parent.
- ↩️ **Transactional file edits** (`chahlie/transaction.py`) - snapshot a
  file's contents (or its non-existence) before a batch of writes; `rollback()`
  restores every touched file, `commit()` drops snapshots. Intended for
  multi-file refactors that need all-or-nothing semantics.
- 🧩 **Plugin system** (`chahlie/plugins.py`) - loads `*.py` files from
  `~/.chahlie/plugins/` (override with `CHAHLIE_PLUGINS_DIR`). Each plugin
  exports a `TOOLS = [{"definition": ..., "function": ...}]` list. Broken
  plugins never crash the agent - they're logged as warnings in `/plugins`.
- 💰 **Cost/token meter** (`chahlie/context_manager.py`) - rolling estimate
  of input/output tokens with per-backend USD rates in `COST_RATES`. Shown
  at end of every turn as a `cost` event and via `/cost` command.
- 🖥️ **Experimental Textual TUI** (`chahlie/tui.py`) - optional
  `python -m chahlie --tui` entrypoint. Scrollable log, live status bar with
  backend+cost, keybindings for clear/memory/quit. Falls back with a clean
  error message if `textual` isn't installed.

#### New commands / flags
- `/cost`, `/primer`, `/project`, `/plugins` - diagnostic commands
- `--no-stream`, `--no-approval`, `--llm-reflection`, `--semantic-memory`, `--tui` - CLI flags
- Env vars: `CHAHLIE_STREAMING`, `CHAHLIE_REQUIRE_APPROVAL`,
  `CHAHLIE_LLM_REFLECTION`, `CHAHLIE_SEMANTIC_MEMORY`,
  `CHAHLIE_COMPACT_THRESHOLD_CHARS`, `CHAHLIE_COMPACT_PRESERVE_RECENT`,
  `CHAHLIE_EMBEDDING_MODEL`, `CHAHLIE_SEMANTIC_TOP_K`, `CHAHLIE_PLUGINS_DIR`

### Changed
- `chahlie/agent.py` - substantial refactor to unify streaming/non-streaming
  paths, wire the cost meter into both backends, call `_maybe_compact` at
  the top of every tool loop, retrieve semantic hits into the system prompt,
  seed the semantic store from persisted learnings on startup, and propagate
  LLM-reflection notes through the reflection engine when enabled.
- `chahlie/personality.py` - extended `SYSTEM_PROMPT` with few-shot examples
  and an updated CODE QUALITY PROTOCOL covering `edit_file`, `run_tests`,
  multi-language verification, and approval blocks.
- `chahlie/tools.py` - new shared `_maybe_verify()` helper so `write_file`
  and `edit_file` report verification results identically; plugin dispatch
  hooked into `execute_tool`.

### Tests
- 🧪 **`test_v22.py`** - 25 new regression tests covering every new module:
  edit_file (5), approval mode (2), multi-language verifier (3), transactions
  (3), context manager (3), plugin loader (3), project primer (4), semantic
  memory offline fallback (2). All green alongside the existing 9 verifier
  tests and the memory smoke test.

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
