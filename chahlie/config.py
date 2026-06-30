"""
Configuration for Chahlie
Supports Ollama Cloud and local Ollama backends
"""

import os
from dotenv import load_dotenv


def _load_env_files() -> None:
    """Load environment from the project `.env` plus the Deck/Tauri config file.

    The desktop shells (Tauri + Steam Deck) persist the API key to
    ``~/.local/share/chahlie/.env`` (overridable via ``CHAHLIE_ENV_FILE``).
    Without loading that file here, a previously saved key is ignored on a
    cold start and the welcome/setup screen wrongly reappears every launch.
    """
    # Project-local .env (developer workflow) takes priority.
    load_dotenv()

    candidate = os.getenv("CHAHLIE_ENV_FILE", "").strip()
    if not candidate:
        candidate = os.path.join(
            os.path.expanduser("~"), ".local", "share", "chahlie", ".env"
        )
    candidate = os.path.expanduser(candidate)
    if os.path.isfile(candidate):
        # override=False so explicit os.environ / project .env values win.
        load_dotenv(candidate, override=False)


_load_env_files()

# Backend Configuration
# Options: "ollama-cloud" (default), "ollama-local", "openai-compatible", or "anthropic"
BACKEND = os.getenv("CHAHLIE_BACKEND", "ollama-cloud")

# Ollama Cloud Configuration (https://ollama.com/search?c=cloud)
OLLAMA_CLOUD_API_KEY = os.getenv("OLLAMA_API_KEY")
OLLAMA_CLOUD_HOST = "https://ollama.com"  # Official Ollama Cloud API

# Available Ollama Cloud Models (as of April 2026):
# Top picks for agentic coding:
# - kimi-k2.6:cloud (256K context, long-horizon coding, tools, vision)
# - glm-5.1         (SOTA for agentic engineering, SWE-Bench Pro leader)
# - qwen3.5        (6.3M pulls - multimodal, thinking, tools)
# - devstral-small-2 (24B - excels at multi-file editing)
# - gemma4         (3.3M pulls - frontier performance, vision+tools)
# - deepseek-v3.2  (efficient reasoning + agent performance)
#
# Backwards compatibility:
# - OLLAMA_MODEL still works as a shared override for both cloud and local.
# - OLLAMA_CLOUD_MODEL / OLLAMA_LOCAL_MODEL can now be set independently.
_legacy_ollama_model = os.getenv("OLLAMA_MODEL", "").strip() or None
OLLAMA_CLOUD_MODEL = os.getenv(
    "OLLAMA_CLOUD_MODEL",
    _legacy_ollama_model or "kimi-k2.6:cloud",
)

# Local Ollama Configuration (for self-hosted)
OLLAMA_LOCAL_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_LOCAL_MODEL = os.getenv(
    "OLLAMA_LOCAL_MODEL",
    _legacy_ollama_model or "qwen3:8b",
)

# OpenAI-compatible proxy (llama.cpp, LiteLLM, or `python -m chahlie.llama_proxy`)
OPENAI_COMPATIBLE_URL = os.getenv(
    "OPENAI_COMPATIBLE_URL",
    os.getenv("LLAMA_PROXY_URL", "http://127.0.0.1:11435/v1"),
).rstrip("/")
OPENAI_COMPATIBLE_API_KEY = os.getenv(
    "OPENAI_COMPATIBLE_API_KEY",
    os.getenv("LLAMA_PROXY_API_KEY", ""),
).strip()
OPENAI_COMPATIBLE_MODEL = os.getenv(
    "OPENAI_COMPATIBLE_MODEL",
    os.getenv("LLAMA_PROXY_MODEL", _legacy_ollama_model or "qwen3:8b"),
)

# Anthropic Configuration (legacy)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

MAX_TOKENS = 8192

# --- Safety ---
# When True, run_command will prompt before executing potentially destructive
# commands (rm -rf, git push --force, DROP TABLE, dd, format, mkfs, etc.).
REQUIRE_APPROVAL = os.getenv("CHAHLIE_REQUIRE_APPROVAL", "true").lower() in ("1", "true", "yes")

# --- Streaming ---
# When True, responses are streamed token-by-token where the backend supports it.
STREAMING = os.getenv("CHAHLIE_STREAMING", "true").lower() in ("1", "true", "yes")

# --- Context compaction ---
# Approximate token budget before older history gets summarized. Rough heuristic:
# ~4 chars per token. When total history chars exceed COMPACT_THRESHOLD_CHARS,
# oldest turns are summarized by a cheap LLM call.
_COMPACT_DEFAULT = "16000" if os.getenv("CHAHLIE_DECK_MODE", "").lower() in ("1", "true", "yes") else "24000"
_COMPACT_PRESERVE_DEFAULT = "4" if os.getenv("CHAHLIE_DECK_MODE", "").lower() in ("1", "true", "yes") else "6"
COMPACT_THRESHOLD_CHARS = int(os.getenv("CHAHLIE_COMPACT_THRESHOLD_CHARS", _COMPACT_DEFAULT))
# How many most-recent turns to preserve verbatim during compaction.
COMPACT_PRESERVE_RECENT = int(os.getenv("CHAHLIE_COMPACT_PRESERVE_RECENT", _COMPACT_PRESERVE_DEFAULT))

# --- LLM-based reflection ---
# When True, certain reflections upgrade from rule-based to LLM-generated
# ("what went wrong in that tool call, one sentence").
LLM_REFLECTION = os.getenv("CHAHLIE_LLM_REFLECTION", "false").lower() in ("1", "true", "yes")

# --- Semantic memory retrieval ---
# When True, learnings are retrieved by embedding similarity instead of
# dumping all of them into the prompt. Requires an Ollama embedding model.
SEMANTIC_MEMORY = os.getenv("CHAHLIE_SEMANTIC_MEMORY", "false").lower() in ("1", "true", "yes")
EMBEDDING_MODEL = os.getenv("CHAHLIE_EMBEDDING_MODEL", "nomic-embed-text")
SEMANTIC_TOP_K = int(os.getenv("CHAHLIE_SEMANTIC_TOP_K", "5"))

# --- Cost meter ---
# Rough $/1M-token rates for the cost meter. Used only as a display heuristic.
COST_RATES = {
    # Ollama Cloud is free at time of writing; show 0.0 by default.
    "ollama-cloud": {"input": 0.0, "output": 0.0},
    "ollama-local": {"input": 0.0, "output": 0.0},
    "openai-compatible": {"input": 0.0, "output": 0.0},
    # Anthropic Sonnet 4 public pricing (per million tokens, USD):
    "anthropic":   {"input": 3.0, "output": 15.0},
}

# --- Model router ---
# Optional small/cheap model to use for trivial chat (greetings, thanks, etc.).
# If unset, all turns use OLLAMA_MODEL.
SMALL_MODEL = os.getenv("CHAHLIE_SMALL_MODEL", "").strip() or None
# Max user message length (chars) to consider routing to the small model.
ROUTER_MAX_TRIVIAL_CHARS = int(os.getenv("CHAHLIE_ROUTER_MAX_TRIVIAL_CHARS", "80"))

# --- Social fast-path ---
# Short banter / hype / gratitude messages do not need the full coding prompt,
# tool menu, project primer, or long conversation history. This fast-path keeps
# those turns snappy and caps the reply length.
SOCIAL_FAST_PATH = os.getenv("CHAHLIE_SOCIAL_FAST_PATH", "true").lower() in ("1", "true", "yes")
SOCIAL_MAX_INPUT_CHARS = int(os.getenv("CHAHLIE_SOCIAL_MAX_INPUT_CHARS", "140"))
SOCIAL_HISTORY_MESSAGES = int(os.getenv("CHAHLIE_SOCIAL_HISTORY_MESSAGES", "4"))
SOCIAL_MAX_REPLY_LINES = int(os.getenv("CHAHLIE_SOCIAL_MAX_REPLY_LINES", "4"))
SOCIAL_MAX_REPLY_CHARS = int(os.getenv("CHAHLIE_SOCIAL_MAX_REPLY_CHARS", "320"))
SOCIAL_MAX_TOKENS = int(os.getenv("CHAHLIE_SOCIAL_MAX_TOKENS", "160"))

# --- History tool-output trimming ---
# Full tool output goes into history for exactly ONE follow-up call (so the
# LLM can reason on it), then gets clamped to this many chars so it stops
# inflating every subsequent turn. 0 disables trimming.
_HISTORY_TOOL_DEFAULT = "800" if os.getenv("CHAHLIE_DECK_MODE", "").lower() in ("1", "true", "yes") else "1200"
HISTORY_TOOL_CHAR_CAP = int(os.getenv("CHAHLIE_HISTORY_TOOL_CHAR_CAP", _HISTORY_TOOL_DEFAULT))

# --- Debug / perf visibility ---
DEBUG_TIMING = os.getenv("CHAHLIE_DEBUG_TIMING", "false").lower() in ("1", "true", "yes")

# Seconds between heartbeat "still working..." events while waiting on an LLM.
HEARTBEAT_SECONDS = int(os.getenv("CHAHLIE_HEARTBEAT_SECONDS", "6"))

# HTTP request timeout for Ollama Cloud / local Ollama calls. Keeps us from
# hanging 30-60s on a wobbly cloud; instead we bail fast and our retry loop
# can handle the hiccup. If you have a slow local model, bump this.
_OLLAMA_TIMEOUT_DEFAULT = "18" if os.getenv("CHAHLIE_DECK_MODE", "").lower() in ("1", "true", "yes") else "25"
OLLAMA_REQUEST_TIMEOUT = float(os.getenv("CHAHLIE_OLLAMA_TIMEOUT", _OLLAMA_TIMEOUT_DEFAULT))

# --- Tool call dedupe ---
# Cache read-only tool calls within a single agent turn so repeated calls
# return the same result instead of re-executing. Always-on; set to False
# via env to disable if it causes issues.
TOOL_DEDUPE = os.getenv("CHAHLIE_TOOL_DEDUPE", "true").lower() in ("1", "true", "yes")

# --- Syntax highlighting ---
# When True, the classic CLI renders read_file output with Pygments colors.
SYNTAX_HIGHLIGHT = os.getenv("CHAHLIE_SYNTAX_HIGHLIGHT", "true").lower() in ("1", "true", "yes")

# --- Plugins ---
# Directory Chahlie scans for user-provided tool extensions on startup.
PLUGINS_DIR = os.getenv("CHAHLIE_PLUGINS_DIR", str(os.path.expanduser("~/.chahlie/plugins")))

# --- Persistent vector store (ChromaDB) ---
# When True AND `chromadb` is installed, semantic memory is persisted to
# .chahlie/vector_store/ in the project root. Survives restarts, so cold
# starts don't have to re-embed every learning + session summary.
# Falls back to in-process SemanticMemory if chromadb isn't importable.
PERSISTENT_VECTOR_STORE = os.getenv("CHAHLIE_PERSISTENT_VECTORS", "true").lower() in ("1", "true", "yes")

# --- Tree-of-Thoughts planning ---
# For non-trivial tasks, generate N candidate approaches in one cheap LLM call,
# score them, and prepend the winner to the system prompt as [Planned approach].
# Default OFF: it's 2 extra LLM calls per qualifying turn.
TOT_PLANNING = os.getenv("CHAHLIE_TOT_PLANNING", "false").lower() in ("1", "true", "yes")
TOT_MIN_TASK_CHARS = int(os.getenv("CHAHLIE_TOT_MIN_TASK_CHARS", "140"))
TOT_CANDIDATES = int(os.getenv("CHAHLIE_TOT_CANDIDATES", "3"))
# Optional override for the planner's model. Empty -> use the turn's routed
# model. Set to a small/fast model (e.g. qwen3.5:cloud) for cheap planning.
TOT_MODEL = os.getenv("CHAHLIE_TOT_MODEL", "").strip() or None

# --- Multi-model fallback chain ---
# Comma-separated list of Ollama model names to try in order if the primary
# model errors out with a transient failure AFTER exhausting its retries.
# Example: CHAHLIE_FALLBACK_MODELS=glm-5.1,devstral-small-2
# Applies to ollama-cloud and ollama-local backends only (Anthropic ignored).
_fallback_raw = os.getenv("CHAHLIE_FALLBACK_MODELS", "").strip()
FALLBACK_MODELS: list[str] = [m.strip() for m in _fallback_raw.split(",") if m.strip()]

# UI Theme - Fenway Green
THEME = {
    "primary": "#0C2340",      # Navy Blue
    "secondary": "#BD3039",    # Red Sox Red
    "accent": "#1E5631",       # Fenway Green
    "success": "#2ECC71",      # Success Green
    "warning": "#F39C12",      # Warning Orange
    "error": "#E74C3C",        # Error Red
    "text": "#FFFFFF",         # White text
    "muted": "#7F8C8D",        # Muted gray
}

# --- Steam Deck / voice ---
# Deck UI: python -m chahlie --deck
DECK_MODE = os.getenv("CHAHLIE_DECK_MODE", "false").lower() in ("1", "true", "yes")

# Default working directory for Deck (home folder, not the Chahlie install dir).
_workdir = os.getenv("CHAHLIE_WORKDIR", "").strip()
DECK_WORKDIR = os.path.expanduser(_workdir or "~") if DECK_MODE else ""

# Deck perf: fewer retries on flaky Wi‑Fi so hiccups fail fast to fallback/local reply.
DECK_MAX_RETRIES = int(os.getenv("CHAHLIE_DECK_MAX_RETRIES", "2"))

# Deck social: answer more banter locally (no cloud round-trip).
DECK_SOCIAL_LOCAL_CHARS = int(os.getenv("CHAHLIE_DECK_SOCIAL_LOCAL_CHARS", "80"))
VOICE_ENABLED = os.getenv("CHAHLIE_VOICE", "true").lower() in ("1", "true", "yes")
VOICE_TTS_ENABLED = os.getenv("CHAHLIE_VOICE_TTS", "true").lower() in ("1", "true", "yes")
VOICE_LANGUAGE = os.getenv("CHAHLIE_VOICE_LANGUAGE", "en-US")
VOICE_LISTEN_TIMEOUT = float(os.getenv("CHAHLIE_VOICE_TIMEOUT", "8"))
VOICE_TTS_RATE = int(os.getenv("CHAHLIE_VOICE_TTS_RATE", "175"))

# App Info
APP_NAME = "Chahlie"
APP_TAGLINE = "The Boston Coding Agent"
# Pulled from the package __init__ so we only bump version in one place.
from . import __version__ as APP_VERSION, __codename__ as APP_CODENAME  # noqa: E402

# Cursor Info
CURSOR = {
    "name": "Cursor",
    "website": "https://cursor.com",
    "download": "https://cursor.com/downloads",
    "tagline": "The AI Code Editor",
}

# Cursor Boston Info
CURSOR_BOSTON = {
    "name": "Cursor Boston",
    "tagline": "Boston's Home for AI-Powered Development",
    "website": "https://cursorboston.com",
    "github": "https://github.com/AaronGrace978/Chahlie",
    "x_twitter": "https://x.com/CursorBoston",
    "description": "The community for Boston developers building with Cursor IDE",
}

# Credits
CREDITS = {
    "organization": "Cursor Boston",
    "founder": "Roger Hunt",
    "founder_title": "Cursor Boston Ambassador",
    "cmo": "Aaron Grace",
}
