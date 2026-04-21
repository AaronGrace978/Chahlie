# Changelog

All notable changes to Chahlie will be documented in this file.

## [2.4.0] "Juice Box" - 2026-04-21

Three juicy upgrades that land as opt-in features so nothing changes for
existing users until they flip a flag. Every new code path has a clean
no-op fallback.

### Added

- **Persistent vector store** (`chahlie/memory/semantic.py`) - semantic
  memory can now be backed by ChromaDB, stored under
  `<project>/.chahlie/vector_store/`. Embeddings survive restarts so cold
  starts stop re-embedding every learning + session summary. New
  `PersistentSemanticMemory` class + `get_semantic_store()` factory that
  falls back to the in-process `SemanticMemory` when `chromadb` isn't
  importable. Toggle with `CHAHLIE_PERSISTENT_VECTORS` (default `true`;
  harmless when chromadb is missing).

- **Tree-of-Thoughts planner** (`chahlie/planner.py`) - new standalone
  module. For qualifying tasks (>= `CHAHLIE_TOT_MIN_TASK_CHARS` and
  matching keywords like "build", "refactor", "implement"), generates
  `CHAHLIE_TOT_CANDIDATES` distinct approaches in ONE cheap LLM call,
  then picks the best in a second call. Winner gets prepended to the
  system prompt as a `[Planned approach]` preamble so the main tool
  loop starts with direction. Default OFF (`CHAHLIE_TOT_PLANNING=false`)
  - flip it on when you want Chahlie to think before leaping. Cost: 2
  small LLM calls per qualifying turn.

- **Multi-model fallback chain** - `CHAHLIE_FALLBACK_MODELS` is a
  comma-separated list of Ollama models to try in order when the
  primary model exhausts its retries with a transient error and
  hasn't streamed any visible text yet. Example:
  `CHAHLIE_FALLBACK_MODELS=glm-5.1,devstral-small-2`. Anthropic backend
  ignores this (single-model by design). Empty list (default) = zero
  behavior change.

### Changed

- `ChahlieAgent.__init__` now constructs semantic memory through
  `get_semantic_store()` so the persistent vs. in-memory decision is
  centralized. The old `SemanticMemory` class is untouched and still
  the default when chromadb isn't available.
- Retry loop in `_process_ollama` now advances through `model_chain`
  on transient failure instead of bailing out immediately.

### Tests

- `test_v24_juice.py` - 15 new tests covering:
  - in-memory semantic store add/search/empty-rejection
  - factory fallback when project_root is None or chromadb is missing
  - full persistent round-trip (runs when chromadb is installed)
  - `should_plan()` heuristic (keyword triggers + length gates)
  - `plan_task()` end-to-end with scripted chat (candidate parsing,
    winner selection, garbage-judgment recovery, empty-generation)
  - `_models_to_try()` (empty chain, dedupe, Anthropic ignore)
  - `_maybe_plan_task()` gating (feature-off, social turns)
- `test_v232_speed_pass.py::test_version` loosened to `>= 2.3.2` so
  minor version bumps stop tripping the regression gate.
- **Full suite: 73/73 green.**

### Dependencies

- `chromadb>=0.5.0` added to `requirements.txt` as an OPTIONAL dep.
  Chahlie silently degrades to in-memory semantic storage when it's
  missing, so no existing install will break.

## [2.3.1] "Southie Sharp" (perf patch) - 2026-04-20

Follow-up to 2.3.0 targeting response latency. Observed symptom: token
usage growing ~1.5k per tool-using turn because full `read_file` outputs
stayed in history forever and the Anthropic path was rebuilding the
system prompt every tool-loop iteration.

### Added
- **History tool-output trimming** - old `role=tool` messages (Ollama) and
  old `tool_result` blocks (Anthropic) are clamped to
  `CHAHLIE_HISTORY_TOOL_CHAR_CAP` chars (default 1200). The latest two
  messages are always preserved full-fidelity so the current turn keeps
  complete context.
- **Heartbeat printer** - when the LLM goes silent for more than
  `CHAHLIE_HEARTBEAT_SECONDS` (default 6), prints `[chahlie] still
  working... Ns` until first-byte arrives. Stops on its own; cancellable.
- **Debug timing mode** - `CHAHLIE_DEBUG_TIMING=true` prints per-phase ms
  timings (`system_prompt_build`, `ollama_call`, `anthropic_call`) so the
  next time something feels slow we can actually see where.
- **Lazy semantic seeding** - `_seed_semantic_memory()` now runs in a
  daemon thread so cold-cache embedding calls don't block the first user
  prompt on startup.

### Changed
- Anthropic path now caches the enhanced system prompt per user message
  and reuses it across every tool-loop iteration (was rebuilding it on
  each iteration, which also re-ran semantic search when enabled).

### Tests
- `test_perf_patch.py` - 9 new tests for history trimming (Ollama + Anthropic
  shapes + disabled), heartbeat fire/stop, heartbeat tickle suppression,
  heartbeat short-task no-tick. **81 total tests green.**

## [2.3.0] "Southie Sharp" - 2026-04-20

Another sixteen-enhancement sprint, this time focused on sharper feedback
on every code change (unified diffs, real linters, did-you-mean hints) and
safer exploration (undo, session branching, tool-result dedupe). All
existing v2.1 and v2.2 regression tests stayed green.

### Added

#### Quick wins
- 🪟 **`open_file` tool** - cross-platform launch of the user's default app
  (`os.startfile` on Windows, `open` on macOS, `xdg-open` elsewhere). Fixes
  the "you said 'open it up' and I read_file'd it instead" UX miss.
- 📂 **Richer `list_directory`** - now shows `FILE|DIR`, human-readable size,
  and modified time per entry. Missing-directory errors include fuzzy hints.
- 🌀 **Git-aware tools** - `git_status`, `git_diff`, `git_log` as first-class
  tools with structured output. Faster than the model guessing `git` flags
  and parsing free-form stdout.
- ✂️ **Diff preview** (`chahlie/differ.py`) - `write_file` and `edit_file`
  now include a unified diff + `+N / -M` summary in their success output, so
  you can see EXACTLY what changed instead of just "wrote 271 characters".
- 🎨 **Syntax-highlighted `read_file`** - the classic CLI pipes `read_file`
  output through `rich.syntax.Syntax` using a lexer detected from the file
  extension. Toggle with `CHAHLIE_SYNTAX_HIGHLIGHT=false`.
- 🏷️ **Banner version fix** - `config.APP_VERSION` and `APP_CODENAME` now
  pull from `chahlie/__init__.py` so the banner stops reporting "v1.0.0
  Green Monstah" five versions later.

#### Meaningful
- 🧭 **Project-scoped memory (git-root detection)** - `ChahlieMemory()`
  walks up from `cwd` looking for a `.git` directory and pins `.chahlie/`
  to the project root. Running from a nested subdir no longer fragments
  memory into multiple `.chahlie/` stores.
- 🧹 **`lint_code` tool** - runs `ruff` + `mypy` for Python, `eslint` for
  JS/TS, each only when installed. Reports per-linter exit codes. Gracefully
  returns "no linters installed" instead of failing.
- 💡 **Smart retry hints** (`chahlie/retry_hints.py`) - when `run_command`
  fails, we append a concrete hint for known patterns:
  "has no upstream branch" → `git push -u origin HEAD`,
  `ModuleNotFoundError: '<X>'` → `pip install <X>`,
  `command not found: <X>` → PATH hint,
  `EADDRINUSE :8080` → port-in-use hint, plus ~10 more.
- 🚫 **Tool-call dedupe** - `read_file`, `list_directory`, `search_*`,
  `git_*`, `verify_code` results are cached within a single agent turn.
  Keyed on `(tool_name, json.dumps(args, sort_keys=True))`. Cache clears
  at the start of every user message.
- ⏪ **`/undo` command** - reverts the most recent `write_file` or
  `edit_file`. `tools.py` maintains a 20-entry undo stack with previous
  file contents; if the file didn't exist before the write, undo deletes it.

#### Ambitious
- 🔮 **Fuzzy file-path matching** (`chahlie/fuzzy.py`) - `read_file`,
  `edit_file`, `list_directory`, and `open_file` errors for missing paths
  now include a "Did you mean: ..." suffix using `difflib.get_close_matches`
  over both full paths and basenames. Skips `.git`, `node_modules`, `dist`,
  `.venv`, `.chahlie`, etc. Scans at most 2000 files.
- 🎯 **Model router** - optional `CHAHLIE_SMALL_MODEL` env var. Trivial chat
  (greetings, thanks, short messages matching a small regex set) routes to
  the small model; code and long messages stay on the main model. Cuts
  per-session cost without hurting coding quality.
- 🌿 **Session branching** - `ChahlieMemory.save_branch(name, history)`,
  `load_branch(name)`, `list_branches()`. Stored as JSON under
  `.chahlie/branches/<name>.json`. Exposed via `/fork <name>`,
  `/switch <name>`, `/branches`.
- 🔁 **Test-failure auto-analysis** - when `run_tests` exits non-zero, we
  call the sub-agent with the failure output and append a one-paragraph
  root-cause + next-action diagnosis to the tool result. Parent agent sees
  the analysis inline; sub-agent has no memory so it doesn't pollute
  learnings.
- 👁️ **`watch_file` tool** - polls a file or URL at 1Hz until a regex
  matches or `timeout_s` elapses (clamped to 1-300s). Enables "run this
  migration and tell me when 'migrated 100%' appears in the log" flows.

### Changed
- `chahlie/tools.py` - shared `_record_undo()` hook in `write_file` /
  `edit_file`, fuzzy-match suffixes appended to file-not-found errors,
  retry-hint suffixes appended to `run_command` failures, 6 new tools
  wired into dispatch (`open_file`, `git_status`, `git_diff`, `git_log`,
  `lint_code`, `watch_file`).
- `chahlie/agent.py` - per-turn `_tool_cache`, `_select_model()` router,
  `fork_session()` / `switch_session()` / `list_branches()` methods. Tool
  result events now include `input` so the UI can pick lexers for syntax
  highlighting. `_call_ollama` accepts an optional `model=` override.
- `chahlie/ui.py` - `print_tool_result` now takes `tool_input` and
  syntax-highlights `read_file` output via the Pygments lexer map. `/help`
  table updated with Big Dig + Southie Sharp commands.
- `chahlie/__main__.py` - `/undo`, `/fork`, `/switch`, `/branches`
  commands added. Forwards `tool_input` to `print_tool_result`.
- `chahlie/memory/memory_manager.py` - `ChahlieMemory()` now defaults to
  the git-root via `_find_project_root()`; adds `save_branch`,
  `load_branch`, `list_branches`, and `_safe_branch_name` helper.
- `chahlie/config.py` - new env toggles: `CHAHLIE_SMALL_MODEL`,
  `CHAHLIE_ROUTER_MAX_TRIVIAL_CHARS`, `CHAHLIE_TOOL_DEDUPE`,
  `CHAHLIE_SYNTAX_HIGHLIGHT`. `APP_VERSION`/`APP_CODENAME` now sourced
  from the package `__init__.py`.

### Tests
- 🧪 **`test_v23.py`** - 38 new regression tests covering every new module:
  banner wiring (2), list_directory metadata (2), open_file guardrail (1),
  git tools (2), lint_code graceful (1), watch_file timeout+match (2), diff
  in writes (3), undo (3), fuzzy match (2), retry hints (4), differ (3),
  project-root detection (2), branch name sanitization (3), session
  branching (4), model router (2), tool dedupe (2). All green alongside
  the 25 Big Dig tests, 9 verifier tests, and the memory smoke test -
  **72 total**.

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
