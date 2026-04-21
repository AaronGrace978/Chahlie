"""
Chahlie's Agent Core - v2.3.2 "Speed Pass"

Full-featured agent loop with:
- Ollama Cloud / local Ollama / Anthropic backends
- Streaming responses (where supported)
- Persistent memory with adaptive prompting
- Self-verification loop via tools.write_file / edit_file
- Context compaction (summarize old turns)
- LLM-based reflection (optional)
- Semantic memory retrieval (optional)
- Cost/token meter
- Plugin loader
- Project auto-primer
- Sub-agent delegation
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Generator, Optional

import re
from .config import (
    BACKEND,
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
    OLLAMA_CLOUD_HOST, OLLAMA_CLOUD_API_KEY, OLLAMA_LOCAL_HOST,
    OLLAMA_CLOUD_MODEL, OLLAMA_LOCAL_MODEL,
    MAX_TOKENS,
    STREAMING,
    COMPACT_THRESHOLD_CHARS, COMPACT_PRESERVE_RECENT,
    LLM_REFLECTION,
    SEMANTIC_MEMORY, EMBEDDING_MODEL, SEMANTIC_TOP_K,
    COST_RATES, PLUGINS_DIR,
    SMALL_MODEL, ROUTER_MAX_TRIVIAL_CHARS,
    TOOL_DEDUPE,
    HISTORY_TOOL_CHAR_CAP, DEBUG_TIMING, HEARTBEAT_SECONDS,
    OLLAMA_REQUEST_TIMEOUT,
    SOCIAL_FAST_PATH, SOCIAL_MAX_INPUT_CHARS, SOCIAL_HISTORY_MESSAGES,
    SOCIAL_MAX_REPLY_LINES, SOCIAL_MAX_REPLY_CHARS, SOCIAL_MAX_TOKENS,
)
import time
import threading

# Read-only tools whose output is safe to cache within a single agent turn.
_DEDUPABLE_TOOLS = {
    "read_file", "list_directory", "search_files", "search_content",
    "git_status", "git_diff", "git_log", "verify_code",
}

# Heuristic regex for trivial chat that doesn't need the big model.
_TRIVIAL_PATTERNS = [
    re.compile(r"^(hi|hey|yo|sup|hello|hola|howdy|ayy+)\b", re.I),
    re.compile(r"\b(thanks|thank you|thx|ty|appreciate it|nice|cool|sweet|sick|pissa)\b", re.I),
    re.compile(r"^(what'?s up|wud up|whats good|how'?s it going)", re.I),
    re.compile(r"^(bye|later|peace|gn|good night|good morning)\b", re.I),
]
_SOCIAL_PATTERNS = _TRIVIAL_PATTERNS + [
    re.compile(r"\b(let'?s go+|lfg|wooo+|yooo+|legend|my boy|buddy|bud|bro|dude|love you)\b", re.I),
    re.compile(r"\b(take this|have a|grab a|here'?s a)\b", re.I),
    re.compile(r"\b(donut|muffin|cookie|coffee|beer|snack|pizza)\b", re.I),
]
_CODING_KEYWORDS = {
    "code", "coding", "bug", "fix", "debug", "implement", "build", "feature",
    "refactor", "test", "tests", "readme", "changelog", "commit", "push",
    "pr", "git", "file", "folder", "directory", "notepad", "terminal",
    "shell", "command", "run", "tool", "open", "write", "edit", "read",
    "python", "javascript", "typescript", "rust", "java", "class",
    "function", "method", "api", "server", "database", "sql", "npm", "pip",
    "lint", "mypy", "ruff", "eslint", "error", "stacktrace", "traceback",
    "repo", "branch", "merge", "undo", "watch_file",
}

_HEART_TEXT = re.compile(r"(<3|❤|❤️|love ya|love you)", re.I)
_SLEEPY_TEXT = re.compile(r"(z{3,}|sleep|nap|bedtime|good ?night)", re.I)
_STATUS_TEXT = re.compile(r"(how we doin|how we doing|what'?s up|how'?s it going|sup|yo)\b", re.I)
_THANKS_TEXT = re.compile(r"\b(thanks|thank you|thx|ty|appreciate it)\b", re.I)

# Variety pools for local social replies. We rotate through these so three
# "sup"s in a row don't get three identical canned lines.
_REPLY_POOLS = {
    "heart": [
        "<3 right back at ya, kehd.",
        "Love ya too, bud. Always.",
        "Ayy, feelin' it. <3",
    ],
    "sleepy": [
        "Catch some Z's, bud. I'll be right here when you're ready to cook again.",
        "Grab some rest, kehd. Code'll still be here in the mornin'.",
        "Alright, nighty-night. Dream of clean diffs.",
    ],
    "thanks": [
        "Anytime, kehd. Happy to help.",
        "No sweat, bud.",
        "You got it, kehd. That's what I'm here for.",
    ],
    "status": [
        "Wicked good, bud. How you makin' out?",
        "Livin' the dream, kehd. What's on the docket?",
        "Can't complain, bud. What are we cookin' up?",
        "All systems green. Whaddya need?",
        "Doin' alright over here. You wanna build somethin'?",
    ],
    "greeting": [
        "Ayyy, what's good, kehd?",
        "Yo bud. How we rollin'?",
        "Hey hey, what're we into today?",
        "What's cookin', kehd?",
    ],
    "generic": [
        "Ayyy, I'm here, kehd.",
        "Right here, bud. Whaddya got?",
        "Listenin', kehd. Go ahead.",
    ],
    "junk": [
        "Whaddya mean, kehd? Gimme somethin' to chew on.",
        "Uhh, speak English to me, bud. What're we doin'?",
        "I'm not followin', kehd. Try that one more time?",
        "That's a new one on me, bud. What're ya after?",
    ],
}

# Patterns for input that is NOT a real request (numeric gibberish, single
# punctuation, repeated characters, keyboard-mash). Handled locally so we
# don't hit the cloud with nothing to actually answer.
_JUNK_INPUT = re.compile(
    r"""
    ^(?:
        \d+             |   # only digits
        [^\w\s]+        |   # only punctuation
        (\w)\1{2,}      |   # same char 3+ times (aaa, !!!)
        [asdfjkl;'\s]{1,6}| # short keyboard-row mash
        test|testing    |   # "test"
        \.+|\?+|!+
    )$
    """,
    re.I | re.VERBOSE,
)

# -----------------------------------------------------------------
# Intent router: fast-path common "open X" / "go to Y" commands
# directly to the open_browser tool so we can skip the LLM entirely.
# Saves ~1.5-3s and ~1500 input tokens per matched turn.
# -----------------------------------------------------------------
_INTENT_OPEN_RE = re.compile(
    r"^(?:please\s+|hey\s+|yo\s+|could\s+you\s+|can\s+you\s+)*"
    r"(?:open(?:\s+up)?|launch|start|fire\s+up|boot\s+up|"
    r"go\s+to|goto|navigate\s+to|browse\s+to|take\s+me\s+to|pull\s+up|"
    r"bring\s+up|load(?:\s+up)?)\s+(.+?)"
    r"(?:\s+(?:please|for\s+me|kehd|bud|buddy|bro|dude|man|plz))?"
    r"[\s.!?,]*$",
    re.IGNORECASE,
)

# Generic search intent: "google X", "search for X", "look up X"
_INTENT_SEARCH_RE = re.compile(
    r"^(?:please\s+)?(?:google|search(?:\s+for)?|look\s+up|find\s+me)\s+(.+?)[\s.!?]*$",
    re.IGNORECASE,
)

# "open" with these targets means a FILE or LOCAL thing, not a browser.
# Bail out of the intent router in that case.
_INTENT_FILE_BLOCKLIST = (
    "file", "readme", "todo", "notepad", "notes", "note",
    "tab", "shell", "terminal", "powershell", "bash", "cmd",
    "config", "settings", "preferences", ".env", "env",
    "editor", "cursor", "vscode", "code", "project", "folder",
    "directory", "dir", "repo", "window", "app", "ide",
    "issue", "pr", "pull request",
)

_BROWSER_ALIASES = {
    "chrome": "https://google.com",
    "google chrome": "https://google.com",
    "firefox": "https://google.com",
    "mozilla": "https://google.com",
    "edge": "https://google.com",
    "microsoft edge": "https://google.com",
    "safari": "https://google.com",
    "brave": "https://google.com",
    "opera": "https://google.com",
    "browser": "https://google.com",
    "the browser": "https://google.com",
    "a browser": "https://google.com",
    "my browser": "https://google.com",
    "web": "https://google.com",
    "the web": "https://google.com",
    "internet": "https://google.com",
    "the internet": "https://google.com",
}

_SITE_ALIASES = {
    "google": "https://google.com",
    "youtube": "https://youtube.com",
    "yt": "https://youtube.com",
    "github": "https://github.com",
    "gh": "https://github.com",
    "gmail": "https://mail.google.com",
    "google mail": "https://mail.google.com",
    "mail": "https://mail.google.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "reddit": "https://reddit.com",
    "linkedin": "https://linkedin.com",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "so": "https://stackoverflow.com",
    "hackernews": "https://news.ycombinator.com",
    "hacker news": "https://news.ycombinator.com",
    "hn": "https://news.ycombinator.com",
    "facebook": "https://facebook.com",
    "fb": "https://facebook.com",
    "instagram": "https://instagram.com",
    "ig": "https://instagram.com",
    "amazon": "https://amazon.com",
    "netflix": "https://netflix.com",
    "spotify": "https://spotify.com",
    "discord": "https://discord.com",
    "twitch": "https://twitch.tv",
    "chatgpt": "https://chat.openai.com",
    "openai": "https://openai.com",
    "claude": "https://claude.ai",
    "anthropic": "https://anthropic.com",
    "cursor": "https://cursor.com",
    "ollama": "https://ollama.com",
    "ollama docs": "https://docs.ollama.com",
    "docs": "https://docs.ollama.com",
    "wikipedia": "https://wikipedia.org",
    "maps": "https://maps.google.com",
    "google maps": "https://maps.google.com",
    "drive": "https://drive.google.com",
    "google drive": "https://drive.google.com",
}

# Any URL-ish string (has a dot and a TLD-looking suffix, no whitespace).
_URLISH_RE = re.compile(
    r"^(?:https?://)?(?:[\w-]+\.)+[a-z]{2,24}(?:[:/]\S*)?$",
    re.IGNORECASE,
)

# Action verbs that signal a direct, tool-using imperative. Used to strip
# primer + learnings from the system prompt for these turns (saves tokens).
_ACTION_TURN_RE = re.compile(
    r"^\s*(?:please\s+|hey\s+|yo\s+|could\s+you\s+|can\s+you\s+)?"
    r"(?:open|launch|start|run|execute|kill|stop|restart|"
    r"install|uninstall|update|upgrade|list|show|cat|print|grep|"
    r"git|npm|pip|poetry|cargo|make|build|deploy|clone|fetch|pull|push|"
    r"commit|checkout|diff|status|log|"
    r"mkdir|touch|cp|mv|rm|copy|move|rename|delete|remove|"
    r"go\s+to|goto|navigate|browse|search|google|find)\b",
    re.IGNORECASE,
)

# Questions / explanatory requests are NOT action turns even if they
# contain an action verb ("can you explain how git works?").
_EXPLAIN_TURN_RE = re.compile(
    r"^\s*(?:why|how\s+come|what\s+is|what\s+does|what'?s|"
    r"can\s+you\s+explain|explain|tell\s+me\s+about|describe|teach\s+me|"
    r"help\s+me\s+understand)\b",
    re.IGNORECASE,
)
from .personality import SYSTEM_PROMPT, get_working, get_success
from .tools import TOOL_DEFINITIONS, execute_tool, register_plugin_dispatch
from .memory import ChahlieMemory, ReflectionEngine, PatternLearner
from .memory.semantic import SemanticMemory
from .context_manager import CostMeter, compact_history, estimate_messages_chars
from .project_primer import prime_project, render_primer_prompt
from .plugins import load_plugins


@dataclass
class AgentEvent:
    """Events emitted by the agent during processing."""
    type: str  # thinking | text | tool_use | tool_result | error | done | reflection | cost
    content: str
    data: Optional[dict] = None


class _Heartbeat:
    """Background 'still thinking' printer so a slow LLM call doesn't look hung.

    Starts a daemon thread that prints every `interval_s` seconds until
    `stop()` is called or `tickle()` fires (first-byte from the stream).
    """

    def __init__(self, *, interval_s: int, on_tick):
        self.interval = max(2, int(interval_s or 6))
        self.on_tick = on_tick
        self._ticked = False
        self._stopped = False
        self._thread: Optional[threading.Thread] = None
        self._started_at = 0.0
        self._last_bucket = 0

    def start(self) -> None:
        if self.interval <= 0:
            return
        self._started_at = time.time()
        self._last_bucket = 0
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def tickle(self) -> None:
        # First byte: don't ever print a heartbeat from this call onward.
        self._ticked = True

    def stop(self) -> None:
        self._stopped = True

    def _run(self) -> None:
        try:
            while not self._stopped:
                time.sleep(min(0.25, self.interval))
                if self._stopped or self._ticked:
                    return
                elapsed = int(time.time() - self._started_at)
                bucket = elapsed // self.interval
                if bucket > self._last_bucket:
                    try:
                        self.on_tick(elapsed)
                    except Exception:
                        pass
                    self._last_bucket = bucket
        except Exception:
            pass


class ChahlieAgent:
    """Chahlie - the Boston Coding Agent."""

    def __init__(self, backend: str = None, enable_memory: bool = True):
        self.backend = backend or BACKEND
        self.conversation_history: list[dict] = []
        self.enable_memory = enable_memory

        # --- Backend + client ---
        self._init_client()

        # --- Memory ---
        if self.enable_memory:
            self.memory = ChahlieMemory()
            self.reflection_engine = ReflectionEngine(self.memory)
            self.pattern_learner = PatternLearner(self.memory)
            self.memory.start_session()
        else:
            self.memory = None
            self.reflection_engine = None
            self.pattern_learner = None

        # --- Semantic memory (optional) ---
        self.semantic: Optional[SemanticMemory] = None
        if SEMANTIC_MEMORY and self.enable_memory and hasattr(self, "client") and self.backend != "anthropic":
            try:
                self.semantic = SemanticMemory(self.client, EMBEDDING_MODEL)
                # Seed in a daemon thread - embedding every past learning
                # can take several seconds on cold-cache embedding models,
                # and we don't want that blocking the first prompt.
                threading.Thread(
                    target=self._seed_semantic_memory, daemon=True,
                ).start()
            except Exception:
                self.semantic = None

        # --- Plugins ---
        defs, dispatch, warnings = load_plugins(PLUGINS_DIR)
        self.plugin_definitions = defs
        for name, fn in dispatch.items():
            register_plugin_dispatch(name, fn)
        self.plugin_warnings = warnings

        # --- Project primer ---
        self.primer = prime_project(".")

        # --- Cost meter ---
        rates = COST_RATES.get(self.backend, {"input": 0.0, "output": 0.0})
        self.cost = CostMeter(input_rate=rates["input"], output_rate=rates["output"])

        # --- Task tracking (used by reflection engine) ---
        self.current_task: Optional[str] = None
        self.task_start_time: Optional[datetime] = None

        # --- Per-turn tool-result cache (cleared at the start of each user msg) ---
        self._tool_cache: dict = {}

        # --- Last local social reply, so we don't repeat ourselves ---
        self._last_social_reply: str = ""

    # -----------------------------------------------------------------
    # initialization helpers
    # -----------------------------------------------------------------

    def _init_client(self) -> None:
        if self.backend == "anthropic":
            from anthropic import Anthropic
            self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
            self.model = ANTHROPIC_MODEL
        elif self.backend == "ollama-cloud":
            from ollama import Client
            self.client = self._make_ollama_client(
                Client,
                host=OLLAMA_CLOUD_HOST,
                headers={'Authorization': f'Bearer {OLLAMA_CLOUD_API_KEY}'},
            )
            self.model = OLLAMA_CLOUD_MODEL
        else:  # ollama-local
            from ollama import Client
            self.client = self._make_ollama_client(Client, host=OLLAMA_LOCAL_HOST)
            self.model = OLLAMA_LOCAL_MODEL

    @staticmethod
    def _make_ollama_client(client_cls, **kwargs):
        """Instantiate an ollama.Client with a bounded timeout.

        Older versions of the `ollama` Python package don't accept a `timeout`
        kwarg, so we try it first and fall back silently.
        """
        try:
            return client_cls(timeout=OLLAMA_REQUEST_TIMEOUT, **kwargs)
        except TypeError:
            return client_cls(**kwargs)

    # -----------------------------------------------------------------
    # history hygiene
    # -----------------------------------------------------------------

    def _trim_stale_tool_results(self) -> None:
        """Clamp tool/user-role tool_result payloads in OLD history entries to
        HISTORY_TOOL_CHAR_CAP chars. The most recent tool block is left alone
        so the current turn still has full context.
        """
        if HISTORY_TOOL_CHAR_CAP <= 0 or len(self.conversation_history) < 4:
            return

        cap = HISTORY_TOOL_CHAR_CAP
        suffix = "\n... (output trimmed for context)"
        # Walk all but the last 2 entries; the tail stays full-fidelity.
        for msg in self.conversation_history[:-2]:
            role = msg.get("role")
            content = msg.get("content")

            # Ollama-style: {"role": "tool", "content": "...big blob..."}
            if role == "tool" and isinstance(content, str) and len(content) > cap:
                msg["content"] = content[:cap] + suffix

            # Anthropic-style: {"role": "user", "content": [{"type": "tool_result", "content": "..."}]}
            if role == "user" and isinstance(content, list):
                for block in content:
                    if (
                        isinstance(block, dict)
                        and block.get("type") == "tool_result"
                        and isinstance(block.get("content"), str)
                        and len(block["content"]) > cap
                    ):
                        block["content"] = block["content"][:cap] + suffix

    def _timing(self, label: str, start: float) -> None:
        if DEBUG_TIMING:
            dur_ms = int((time.time() - start) * 1000)
            print(f"[chahlie-timing] {label}: {dur_ms}ms", flush=True)

    def _seed_semantic_memory(self) -> None:
        """Populate the semantic store from persisted learnings + session summaries."""
        if not self.semantic or not self.memory:
            return
        items = []
        for learning in self.memory.learnings:
            items.append((
                f"[{learning.category}] {learning.pattern} (example: {learning.example})",
                {"kind": "learning", "id": learning.id, "confidence": learning.confidence},
            ))
        for session in self.memory.sessions[-30:]:
            summary = session.summary or f"Session {session.id}"
            items.append((
                f"session: {summary}; decisions: {', '.join(session.key_decisions)}",
                {"kind": "session", "id": session.id},
            ))
        self.semantic.add_many(items)

    # -----------------------------------------------------------------
    # session lifecycle
    # -----------------------------------------------------------------

    def reset(self) -> None:
        self.conversation_history = []
        self._tool_cache.clear()
        if self.memory:
            self.memory.end_session("Session cleared by user")
            self.memory.start_session()

    # -----------------------------------------------------------------
    # model router
    # -----------------------------------------------------------------

    def _select_model(self, user_message: str) -> str:
        """Choose a model for this turn. Defaults to self.model; downgrades to
        SMALL_MODEL for short trivial chat when configured."""
        if not SMALL_MODEL or self.backend == "anthropic":
            return self.model
        return SMALL_MODEL if self._is_social_turn(user_message) else self.model

    # -----------------------------------------------------------------
    # session branching
    # -----------------------------------------------------------------

    def fork_session(self, name: str) -> Optional[str]:
        if not self.memory:
            return None
        path = self.memory.save_branch(name, self.conversation_history)
        return str(path)

    def switch_session(self, name: str) -> Optional[str]:
        if not self.memory:
            return None
        payload = self.memory.load_branch(name)
        if payload is None:
            return None
        self.conversation_history = payload.get("conversation_history", [])
        self._tool_cache.clear()
        return name

    def list_branches(self) -> list:
        if not self.memory:
            return []
        return self.memory.list_branches()

    # -----------------------------------------------------------------
    # prompt construction
    # -----------------------------------------------------------------

    def _is_social_turn(self, user_message: str) -> bool:
        """Heuristic: detect short hype / gratitude / banter turns.

        We keep this conservative. Anything that smells like an actual coding
        request should stay on the full agent path.
        """
        if not SOCIAL_FAST_PATH:
            return False
        text = (user_message or "").strip()
        if not text or len(text) > SOCIAL_MAX_INPUT_CHARS:
            return False
        lowered = text.lower()
        tokens = set(re.findall(r"[a-zA-Z_]+", lowered))
        if _CODING_KEYWORDS.intersection(tokens):
            return False
        if any(ch in text for ch in ("`", "{", "}", "[", "]", "(", ")", "\\", "/", "=")):
            return False
        return any(rx.search(text) for rx in _SOCIAL_PATTERNS)

    def _extract_text_content(self, content) -> str:
        """Flatten assistant/user content into plain text for lightweight history."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
            return "\n".join(p for p in parts if p)
        return ""

    def _history_for_turn(self, *, social_mode: bool) -> list[dict]:
        """Use only the recent conversational tail for social turns."""
        if not social_mode:
            return self.conversation_history

        tail: list[dict] = []
        for msg in reversed(self.conversation_history):
            role = msg.get("role")
            if role not in ("user", "assistant"):
                continue
            text = self._extract_text_content(msg.get("content"))
            if not text.strip():
                continue
            tail.append({"role": role, "content": text})
            if len(tail) >= SOCIAL_HISTORY_MESSAGES:
                break
        return list(reversed(tail))

    def _social_system_prompt(self) -> str:
        return (
            "You are Chahlie, a playful Boston-flavored assistant.\n"
            "The user is making casual social banter, not asking for code work.\n"
            f"Reply in at most {SOCIAL_MAX_REPLY_LINES} short lines, warm and punchy.\n"
            "Do NOT call tools. Do NOT list options unless asked. Do NOT write long stories.\n"
            "Keep the tone fun, direct, and conversational."
        )

    def _shorten_social_reply(self, text: str) -> str:
        """Clamp social replies so the model can't monologue."""
        text = (text or "").strip()
        if not text:
            return text
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            lines = lines[:SOCIAL_MAX_REPLY_LINES]
            text = "\n".join(lines)
        if len(text) <= SOCIAL_MAX_REPLY_CHARS:
            return text
        clipped = text[:SOCIAL_MAX_REPLY_CHARS].rsplit(" ", 1)[0].rstrip()
        return (clipped or text[:SOCIAL_MAX_REPLY_CHARS]).rstrip(" .,!?:;") + "..."

    # Regex patterns for chat-template / stop-token leaks that some broken
    # Ollama model tags spit into output (e.g. qwen3-coder-next:cloud was
    # leaking <|im_end|> + hallucinating fake user turns).
    _TEMPLATE_LEAK_RE = re.compile(
        r"<\|(?:im_end|im_start|endoftext|end_of_turn|eot_id|start_header_id|"
        r"end_header_id|assistant|user|system|tool|observation)\|>.*",
        re.IGNORECASE | re.DOTALL,
    )
    # Runaway repetition: same short fragment repeating 8+ times in a row is
    # almost certainly the model looping (`\\ \\ \\ ...`, `so so so...`).
    _RUNAWAY_REPEAT_RE = re.compile(
        r"(.{1,12}?)\1{8,}", re.DOTALL,
    )

    def _sanitize_model_output(self, text: str) -> tuple[str, bool]:
        """Strip chat-template leaks and detect runaway repetition.

        Returns (cleaned_text, was_truncated). If the model leaked its own
        template tokens or got stuck in a tight loop, we trim everything
        from the first offense onward so the user sees a clean reply.
        """
        if not text:
            return text, False

        truncated = False
        m = self._TEMPLATE_LEAK_RE.search(text)
        if m:
            text = text[:m.start()].rstrip()
            truncated = True

        m = self._RUNAWAY_REPEAT_RE.search(text)
        if m:
            text = text[:m.start()].rstrip()
            truncated = True

        return text, truncated

    def _is_transient_ollama_error(self, err: Exception | str) -> bool:
        """Recognize provider/network wobble that is worth handling gently."""
        text = str(err).lower()
        # Also look at the exception class name - httpx/urllib3 timeouts don't
        # always mention "timeout" in the stringified message.
        cls_name = type(err).__name__.lower() if isinstance(err, BaseException) else ""
        if "timeout" in cls_name or "readtimeout" in cls_name or "connecterror" in cls_name:
            return True
        return any(token in text for token in (
            "503", "502", "504",
            "service temporarily unavailable",
            "bad gateway",
            "gateway timeout",
            "timeout",
            "timed out",
            "read operation",
            "temporarily unavailable",
            "connection reset",
            "connection aborted",
            "remote end closed",
            "remote disconnected",
            "eof occurred",
        ))

    def _social_fallback_reply(self, user_message: str) -> str:
        """Tiny local fallback when cloud chat is down for a banter-only turn.

        This is intentionally simple and deterministic: if the provider is
        wobbling, don't fail hard on `<3` or `yo buddy`, just answer warmly.
        """
        text = (user_message or "").strip()
        lowered = text.lower()
        if _HEART_TEXT.search(text):
            return "<3 right back at ya, kehd. Ollama Cloud's bein' a little cranky, but I'm still here."
        if _SLEEPY_TEXT.search(lowered):
            return "Catch some Z's, kehd. I'll be right here when you're ready to bang out more code."
        if _STATUS_TEXT.search(lowered):
            return "Doin' alright, bud. Cloud's hittin' a speed bump, but we're still in the game."
        return "Still here, kehd. Cloud's havin' a moment, but I'm ready when it clears up."

    def _is_junk_input(self, user_message: str) -> bool:
        """Detect gibberish / test input that has no real request in it."""
        text = (user_message or "").strip()
        if not text or len(text) > 12:
            return False
        return bool(_JUNK_INPUT.match(text))

    # -----------------------------------------------------------------
    # intent router (fast-path direct tool dispatch, no LLM)
    # -----------------------------------------------------------------
    def _try_intent_shortcut(self, user_message: str) -> Optional[tuple[str, dict, str]]:
        """Try to resolve a message to a direct tool call.

        Returns (tool_name, tool_args, summary) on a match, else None.
        `summary` is the short Chahlie-flavored reply that goes into history.
        """
        text = (user_message or "").strip()
        if not text or len(text) > 160:
            return None

        # --- search intent: "google X", "search for X" ---
        sm = _INTENT_SEARCH_RE.match(text)
        if sm:
            query = sm.group(1).strip().strip('"\'').rstrip(".?!,")
            if query and len(query) >= 2:
                return (
                    "web_search",
                    {"query": query},
                    f"Googlin' '{query}' for ya, kehd. Check the browser.",
                )

        # --- open/go-to intent ---
        m = _INTENT_OPEN_RE.match(text)
        if not m:
            return None
        target_raw = m.group(1).strip().strip('"\'').rstrip(".?!,").strip()
        target = target_raw.lower()
        if not target:
            return None

        # Bail if target mentions a file/editor/terminal concept -
        # "open the config file" is a filesystem task, not a browser one.
        if any(kw in target for kw in _INTENT_FILE_BLOCKLIST):
            return None
        # Bail if the target looks like a path (Windows or POSIX).
        if "\\" in target_raw or target_raw.startswith("/") or re.match(r"^[a-z]:[\\/]", target_raw, re.I):
            return None

        url: Optional[str] = None
        if target in _BROWSER_ALIASES:
            url = _BROWSER_ALIASES[target]
        elif target in _SITE_ALIASES:
            url = _SITE_ALIASES[target]
        else:
            cleaned = re.sub(r"^(the|a|an|my)\s+", "", target).strip()
            if cleaned in _BROWSER_ALIASES:
                url = _BROWSER_ALIASES[cleaned]
            elif cleaned in _SITE_ALIASES:
                url = _SITE_ALIASES[cleaned]
            elif _URLISH_RE.match(cleaned):
                url = cleaned if cleaned.startswith(("http://", "https://")) else f"https://{cleaned}"
            elif "." in cleaned and " " not in cleaned and "/" not in cleaned.split(".", 1)[0]:
                # Bare domain like "example.com"
                url = f"https://{cleaned}"

        if not url:
            return None

        # Friendly confirmation. Short — no re-prompting the LLM.
        if url in _BROWSER_ALIASES.values() and target in _BROWSER_ALIASES:
            summary = "Browser's comin' up, kehd."
        else:
            summary = f"Pullin' up {url}, kehd."
        return ("open_browser", {"url": url}, summary)

    def _is_action_turn(self, user_message: str) -> bool:
        """Short, imperative, tool-using turn — safe to prune the prompt for."""
        text = (user_message or "").strip()
        if not text or len(text) > 200:
            return False
        if self._is_social_turn(text) or self._is_junk_input(text):
            return False
        if _EXPLAIN_TURN_RE.match(text):
            return False
        return bool(_ACTION_TURN_RE.match(text))

    def _should_answer_social_locally(self, user_message: str) -> bool:
        """Return True for tiny banter / junk that does not need a model call."""
        text = (user_message or "").strip()
        if not text or len(text) > 40:
            return False
        if self._is_junk_input(text):
            return True
        if self._is_social_turn(text):
            lowered = text.lower()
            return any((
                _HEART_TEXT.search(text),
                _SLEEPY_TEXT.search(lowered),
                _STATUS_TEXT.search(lowered),
                _THANKS_TEXT.search(lowered),
            ))
        lowered = text.lower()
        return any((
            _HEART_TEXT.search(text),
            _SLEEPY_TEXT.search(lowered),
            text in {"<3", "❤️", "❤"},
        ))

    def _pick_reply(self, pool_name: str) -> str:
        """Pick a reply from a named pool, avoiding an immediate repeat."""
        pool = _REPLY_POOLS.get(pool_name) or _REPLY_POOLS["generic"]
        candidates = [line for line in pool if line != self._last_social_reply]
        if not candidates:
            candidates = pool
        choice = random.choice(candidates)
        self._last_social_reply = choice
        return choice

    def _social_local_reply(self, user_message: str) -> str:
        """Fast, varied reply for ultra-short social turns.

        Pools rotate so repeated "sup"s don't get three identical canned
        responses. `<3`, `ty`, and sleepy messages still get the appropriate
        vibe but pull from a small pool.
        """
        text = (user_message or "").strip()
        lowered = text.lower()
        if self._is_junk_input(text):
            return self._pick_reply("junk")
        if _HEART_TEXT.search(text):
            return self._pick_reply("heart")
        if _SLEEPY_TEXT.search(lowered):
            return self._pick_reply("sleepy")
        if _THANKS_TEXT.search(lowered):
            return self._pick_reply("thanks")
        # "how's it going?" / "what's up?" -> status pool
        if _STATUS_TEXT.search(lowered) and any(
            kw in lowered for kw in ("how", "what", "goin", "going", "doin", "doing")
        ):
            return self._pick_reply("status")
        # Bare "yo" / "hey" / "sup" -> greeting pool (different flavor)
        if re.match(r"^(yo+|sup|hey+|hi+|hello|howdy|ayy+)\b", lowered):
            return self._pick_reply("greeting")
        return self._pick_reply("generic")

    def _get_enhanced_system_prompt(
        self,
        user_message: str = "",
        *,
        lightweight: bool = False,
        action_mode: bool = False,
    ) -> str:
        """Base prompt + project primer + learned user patterns + recent reflections.

        `lightweight=True` -> tiny social prompt (banter only).
        `action_mode=True` -> core personality + a short tool-loop hint, but NO
          project primer, NO learned patterns, NO semantic retrieval. Saves
          ~1.5-3k input tokens on every direct imperative turn.
        """
        if lightweight:
            return self._social_system_prompt()
        if action_mode:
            return (
                SYSTEM_PROMPT
                + "\n\nDIRECT-ACTION MODE:\n"
                "- The user asked for a specific, concrete action. Just do it.\n"
                "- Call the appropriate tool immediately. Don't narrate a plan.\n"
                "- One short sentence of confirmation at the end is plenty.\n"
                "- In multi-tool loops: only write NEW text each step. "
                "Do NOT restate or repeat previous sentences from this turn.\n"
            )
        parts = [SYSTEM_PROMPT]

        # Same multi-step dedup hint for full prompts. Models (esp. qwen3.5)
        # love to restate their prior message before each tool call - this
        # tells them to stop.
        parts.append(
            "MULTI-STEP TURN DISCIPLINE:\n"
            "- When you take multiple tool-calling steps in one turn, each new "
            "assistant message should contain ONLY new information.\n"
            "- Never repeat the preamble or prior sentences from earlier in the "
            "same turn. The user already saw those.\n"
        )

        primer_text = render_primer_prompt(self.primer)
        if primer_text:
            parts.append(primer_text)

        if not self.memory:
            return "\n\n".join(parts)

        profile = self.pattern_learner.get_user_profile()
        adaptations: list[str] = []

        if profile.get("coding_style"):
            adaptations.append("USER CODING STYLE (learned):")
            for _, pattern in profile["coding_style"].items():
                adaptations.append(f"- {pattern}")

        if profile.get("communication_style"):
            adaptations.append("\nUSER COMMUNICATION PREFERENCES:")
            for _, pattern in profile["communication_style"].items():
                if "concise" in pattern.lower():
                    adaptations.append("- Keep responses brief and direct")
                elif "detailed" in pattern.lower():
                    adaptations.append("- Provide thorough explanations")

        # Semantic retrieval: replace the "dump all learnings" approach when enabled
        if self.semantic and self.semantic.healthy and user_message.strip():
            hits = self.semantic.search(user_message, top_k=SEMANTIC_TOP_K)
            if hits:
                adaptations.append("\nRELEVANT MEMORY (retrieved by similarity):")
                for score, entry in hits:
                    adaptations.append(f"- ({score:.2f}) {entry.text}")
        else:
            recent_reflections = self.memory.get_reflections(limit=3)
            if recent_reflections:
                adaptations.append("\nRECENT LEARNINGS (from self-reflection):")
                for ref in recent_reflections:
                    for learning in ref.get("learnings", []):
                        adaptations.append(f"- {learning.get('pattern', '')}")

        if adaptations:
            parts.append("\n".join(adaptations))

        return "\n\n".join(parts)

    # -----------------------------------------------------------------
    # context compaction (summarize old turns when history grows large)
    # -----------------------------------------------------------------

    def _maybe_compact(self, messages: list[dict]) -> tuple[list[dict], bool]:
        if estimate_messages_chars(messages) <= COMPACT_THRESHOLD_CHARS:
            return messages, False

        def summarize(head: list[dict]) -> str:
            return self._summarize_turns(head)

        return compact_history(
            messages,
            threshold_chars=COMPACT_THRESHOLD_CHARS,
            preserve_recent=COMPACT_PRESERVE_RECENT,
            summarize_fn=summarize,
        )

    def _summarize_turns(self, turns: list[dict]) -> str:
        """Ask the model to compress older conversation history to a short summary."""
        try:
            if self.backend == "anthropic":
                resp = self.client.messages.create(
                    model=self.model,
                    max_tokens=600,
                    system=(
                        "You compress a conversation history into 4-6 terse bullet "
                        "points preserving decisions, file changes, and open TODOs. "
                        "Do NOT add commentary; just the bullets."
                    ),
                    messages=[{"role": "user", "content": json.dumps(turns)[:12000]}],
                )
                for block in resp.content:
                    if getattr(block, "type", "") == "text":
                        return block.text
                return ""
            resp = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system",
                     "content": "Compress this conversation to 4-6 terse bullet points (decisions, file changes, open TODOs). No commentary."},
                    {"role": "user", "content": json.dumps(turns)[:12000]},
                ],
                stream=False,
            )
            return getattr(resp.message, "content", "") or ""
        except Exception:
            return ""

    # -----------------------------------------------------------------
    # LLM-based reflection (opt-in)
    # -----------------------------------------------------------------

    def _llm_reflect_on_failure(self, tool_name: str, args: dict, error: str) -> str:
        if not LLM_REFLECTION:
            return ""
        try:
            prompt = (
                f"Tool '{tool_name}' failed with arguments {json.dumps(args)[:400]}.\n"
                f"Error: {error[:400]}\n"
                "In ONE sentence, what likely went wrong and what should be tried next? "
                "Be terse and actionable."
            )
            if self.backend == "anthropic":
                resp = self.client.messages.create(
                    model=self.model, max_tokens=120,
                    system="You are a debugging partner. One-sentence answers only.",
                    messages=[{"role": "user", "content": prompt}],
                )
                for block in resp.content:
                    if getattr(block, "type", "") == "text":
                        return block.text.strip()
                return ""
            resp = self.client.chat(
                model=self.model, stream=False,
                messages=[
                    {"role": "system",
                     "content": "You are a debugging partner. One-sentence answers only."},
                    {"role": "user", "content": prompt},
                ],
            )
            return (getattr(resp.message, "content", "") or "").strip()
        except Exception:
            return ""

    # -----------------------------------------------------------------
    # backend calls
    # -----------------------------------------------------------------

    def _ollama_tools(self) -> list[dict]:
        tools = []
        for tool in TOOL_DEFINITIONS + self.plugin_definitions:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            })
        return tools

    def _call_ollama(
        self,
        messages: list[dict],
        stream: bool,
        *,
        model: Optional[str] = None,
        tools: Optional[list[dict]] = None,
    ) -> Generator[dict, None, None]:
        """Yields incremental chunks when streaming, or a single chunk otherwise."""
        tools = self._ollama_tools() if tools is None else tools
        use_model = model or self.model
        if not stream:
            resp = self.client.chat(
                model=use_model, messages=messages, tools=tools, stream=False,
            )
            yield {
                "role": resp.message.role,
                "content": resp.message.content or "",
                "tool_calls": [
                    {"function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in (resp.message.tool_calls or [])
                ],
            }
            return

        # Streaming path
        accumulated = ""
        final_tool_calls: list[dict] = []
        for chunk in self.client.chat(
            model=use_model, messages=messages, tools=tools, stream=True,
        ):
            delta_text = ""
            msg = getattr(chunk, "message", None)
            if msg is not None:
                piece = getattr(msg, "content", "") or ""
                if piece:
                    delta_text = piece
                    accumulated += piece
                tcs = getattr(msg, "tool_calls", None) or []
                if tcs:
                    final_tool_calls = [
                        {"function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in tcs
                    ]
            if delta_text:
                yield {"role": "assistant", "content": delta_text, "stream_delta": True}
            if getattr(chunk, "done", False):
                break
        yield {
            "role": "assistant",
            "content": accumulated,
            "tool_calls": final_tool_calls,
            "final": True,
        }

    # -----------------------------------------------------------------
    # main processing loops (ollama + anthropic)
    # -----------------------------------------------------------------

    def _process_ollama(self, user_message: str) -> Generator[AgentEvent, None, None]:
        if self.memory:
            self.memory.track_message("user", user_message)
        self.cost.add_input(user_message)
        self._tool_cache.clear()
        social_mode = self._is_social_turn(user_message)

        if self._should_answer_social_locally(user_message):
            content = self._shorten_social_reply(self._social_local_reply(user_message))
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": content})
            if self.memory:
                self.memory.track_message("assistant", content)
                self.reflection_engine.reflect_on_user_feedback(user_message, "neutral")
            self.cost.add_output(content)
            yield AgentEvent(type="text", content=content)
            yield AgentEvent(type="cost", content=self.cost.format(), data={"cost": self.cost.cost_usd})
            yield AgentEvent(type="done", content=get_success())
            return

        # Intent router - direct-dispatch common "open <site>" / "search X"
        # requests without a model call at all.
        shortcut = self._try_intent_shortcut(user_message)
        if shortcut:
            yield from self._run_intent_shortcut(user_message, *shortcut)
            return

        _t = time.time()
        action_mode = self._is_action_turn(user_message)
        system_prompt = self._get_enhanced_system_prompt(
            user_message, lightweight=social_mode, action_mode=action_mode,
        )
        self._timing("system_prompt_build", _t)
        self.cost.add_input(system_prompt)

        self.conversation_history.append({"role": "user", "content": user_message})
        self.current_task = user_message[:200]
        self.task_start_time = datetime.now()

        use_stream = STREAMING and not social_mode
        routed_model = self._select_model(user_message)
        ollama_tools = [] if social_mode else None

        # Text already emitted in PRIOR iterations of this turn's tool loop.
        # Used to strip the "Chahlie restates everything" preamble bug where
        # the model repeats its earlier message before each new tool call.
        prior_turn_text = ""

        while True:
            if not social_mode:
                # Trim stale tool outputs before any compaction check so the
                # estimator doesn't see bloated payloads from prior turns.
                self._trim_stale_tool_results()
                self.conversation_history, compacted = self._maybe_compact(self.conversation_history)
                if compacted:
                    yield AgentEvent(
                        type="thinking",
                        content="(compacting older turns to stay within context)",
                    )

            messages = [{"role": "system", "content": system_prompt}] + self._history_for_turn(social_mode=social_mode)
            yield AgentEvent(type="thinking", content=get_working())

            final_payload = None
            streamed_text = ""
            last_error: Optional[Exception] = None
            # Retry transient cloud wobbles (503/502/504/timeouts) with
            # exponential backoff. Real requests like "open chrome" should
            # not die on a single blip.
            max_attempts = 3
            backoff = 1.5
            for attempt in range(1, max_attempts + 1):
                final_payload = None
                streamed_text = ""
                last_error = None
                call_start = time.time()
                heartbeat = _Heartbeat(
                    interval_s=HEARTBEAT_SECONDS,
                    on_tick=lambda elapsed: print(f"[chahlie] still working... {elapsed}s", flush=True),
                )
                heartbeat.start()
                # Kill-switch ceiling for runaway generations: ~32KB of
                # visible text is roughly 8K tokens. If we blow past that
                # we abort the stream — something is broken upstream.
                runaway_char_cap = 32_000
                aborted_runaway = False
                # Preamble-dedup state for the multi-step repeat bug.
                # If the model starts this iteration by restating text we
                # already showed the user in a previous iteration of the
                # same turn, we suppress that prefix before yielding.
                dedup_target = prior_turn_text
                dedup_buffer = ""
                dedup_active = bool(dedup_target)
                try:
                    for chunk in self._call_ollama(
                        messages, stream=use_stream, model=routed_model, tools=ollama_tools,
                    ):
                        heartbeat.tickle()  # first byte -> stop the heartbeat
                        if chunk.get("stream_delta"):
                            piece = chunk["content"]
                            streamed_text += piece
                            emit_piece = piece
                            if dedup_active:
                                dedup_buffer += piece
                                if dedup_target.startswith(dedup_buffer):
                                    # Still inside the prior-text prefix;
                                    # hold the piece back, don't emit yet.
                                    cleaned, was_trunc = self._sanitize_model_output(streamed_text)
                                    if was_trunc or len(streamed_text) > runaway_char_cap:
                                        streamed_text = cleaned or streamed_text[:runaway_char_cap]
                                        aborted_runaway = True
                                        break
                                    continue
                                if dedup_buffer.startswith(dedup_target):
                                    # Prior prefix fully consumed - emit the
                                    # new tail and turn dedup off.
                                    emit_piece = dedup_buffer[len(dedup_target):]
                                    dedup_active = False
                                else:
                                    # Diverged mid-prefix (model paraphrased
                                    # instead of verbatim). Emit buffered
                                    # content as-is and give up.
                                    emit_piece = dedup_buffer
                                    dedup_active = False
                            if emit_piece:
                                yield AgentEvent(type="text", content=emit_piece, data={"streaming": True})
                            # Early abort on template leak / looping repetition.
                            cleaned, was_trunc = self._sanitize_model_output(streamed_text)
                            if was_trunc or len(streamed_text) > runaway_char_cap:
                                streamed_text = cleaned or streamed_text[:runaway_char_cap]
                                aborted_runaway = True
                                break
                        else:
                            final_payload = chunk
                    heartbeat.stop()
                    self._timing("ollama_call", call_start)
                    if aborted_runaway:
                        yield AgentEvent(
                            type="thinking",
                            content=(
                                "(model went off the rails — trimmed output. "
                                "Consider swappin' models in .env if it keeps happenin'.)"
                            ),
                        )
                    break  # success
                except Exception as e:
                    last_error = e
                    try:
                        heartbeat.stop()
                    except Exception:
                        pass
                    # If we already streamed visible text to the user this
                    # attempt, don't retry - we'd duplicate output in the UI.
                    if streamed_text:
                        break
                    if not self._is_transient_ollama_error(e) or attempt == max_attempts:
                        break
                    wait_s = backoff ** attempt
                    yield AgentEvent(
                        type="thinking",
                        content=f"(cloud hiccup, retryin' in {wait_s:.1f}s... try {attempt + 1}/{max_attempts})",
                    )
                    time.sleep(wait_s)

            if last_error is not None:
                if social_mode and self._is_transient_ollama_error(last_error):
                    content = self._shorten_social_reply(self._social_fallback_reply(user_message))
                    self.cost.add_output(content)
                    self.conversation_history.append({"role": "assistant", "content": content})
                    if self.memory:
                        self.memory.track_message("assistant", content)
                    yield AgentEvent(type="text", content=content)
                    yield AgentEvent(type="cost", content=self.cost.format(), data={"cost": self.cost.cost_usd})
                    yield AgentEvent(type="done", content=get_success())
                    return
                if self._is_transient_ollama_error(last_error):
                    yield AgentEvent(
                        type="error",
                        content=(
                            "Ollama Cloud's takin' a nap, kehd. Tried 3 times and "
                            "it's still wobbly.\n\n"
                            "Try one of these:\n"
                            "  • Wait a minute and ask again\n"
                            "  • Switch to local Ollama: set CHAHLIE_BACKEND=ollama-local\n"
                            "  • Switch to Anthropic:    set CHAHLIE_BACKEND=anthropic\n"
                            "  • Check status:           https://ollama.com/status"
                        ),
                    )
                else:
                    yield AgentEvent(type="error", content=f"Ollama Error: {last_error}")
                if self.memory:
                    note = self._llm_reflect_on_failure("api_call", {}, str(last_error))
                    self.reflection_engine.reflect_on_tool_use(
                        "api_call", {}, False, note or str(last_error),
                    )
                return

            if final_payload is None:
                yield AgentEvent(type="error", content="Empty response from backend")
                return

            content = final_payload.get("content", "") or streamed_text
            # Scrub chat-template leaks & runaway repetition before anything
            # touches history, cost, or UI (non-streaming path doesn't get
            # caught by the per-chunk guard above).
            content, _ = self._sanitize_model_output(content)
            if social_mode:
                content = self._shorten_social_reply(content)
            tool_calls = final_payload.get("tool_calls", []) or []
            self.cost.add_output(content)

            assistant_msg: dict = {"role": "assistant", "content": content}
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            self.conversation_history.append(assistant_msg)
            if self.memory:
                self.memory.track_message("assistant", content)

            # Emit non-streamed text once (streaming path already yielded deltas)
            if content and not use_stream:
                emit_text = content
                if prior_turn_text and content.startswith(prior_turn_text):
                    emit_text = content[len(prior_turn_text):].lstrip()
                if emit_text:
                    yield AgentEvent(type="text", content=emit_text)

            # Remember what the model has cumulatively said in this turn so
            # the next iteration can strip any restated preamble.
            prior_turn_text = content or prior_turn_text

            if not tool_calls:
                yield AgentEvent(type="cost", content=self.cost.format(), data={"cost": self.cost.cost_usd})
                yield AgentEvent(type="done", content=get_success())
                if self.memory:
                    self.reflection_engine.reflect_on_user_feedback(user_message, "neutral")
                return

            # Execute tool calls
            for tool_call in tool_calls:
                yield from self._execute_and_emit(tool_call.get("function", {}))

    def _run_intent_shortcut(
        self,
        user_message: str,
        tool_name: str,
        tool_args: dict,
        summary: str,
    ) -> Generator[AgentEvent, None, None]:
        """Execute a directly-routed tool without an LLM call.

        Used by the intent router for things like 'open chrome' or 'google X'
        where the user's intent is unambiguous and we can save ~1.5-3s and
        ~1500 input tokens by skipping the model entirely.
        """
        self.conversation_history.append({"role": "user", "content": user_message})
        self.current_task = user_message[:200]
        self.task_start_time = datetime.now()

        yield AgentEvent(
            type="tool_use",
            content=f"Using {tool_name}",
            data={"tool": tool_name, "input": tool_args},
        )

        result = execute_tool(tool_name, tool_args)
        if self.memory:
            self.memory.track_tool_use(tool_name, tool_args, result.success)

        yield AgentEvent(
            type="tool_result",
            content=result.output if result.success else (result.error or ""),
            data={
                "tool": tool_name, "success": result.success,
                "output": result.output, "error": result.error,
                "input": tool_args,
            },
        )

        final_text = summary if result.success else (
            f"Couldn't pull that off, kehd: {result.error or 'unknown error'}"
        )
        self.conversation_history.append({"role": "assistant", "content": final_text})
        if self.memory:
            self.memory.track_message("assistant", final_text)
        self.cost.add_output(final_text)

        yield AgentEvent(type="text", content=final_text)
        yield AgentEvent(
            type="cost", content=self.cost.format(), data={"cost": self.cost.cost_usd},
        )
        yield AgentEvent(type="done", content=get_success())

    def _execute_and_emit(self, func: dict) -> Generator[AgentEvent, None, None]:
        tool_name = func.get("name", "")
        tool_args = func.get("arguments", {})
        if isinstance(tool_args, str):
            try:
                tool_args = json.loads(tool_args)
            except Exception:
                tool_args = {}

        yield AgentEvent(
            type="tool_use", content=f"Using {tool_name}",
            data={"tool": tool_name, "input": tool_args},
        )

        cache_key = None
        if TOOL_DEDUPE and tool_name in _DEDUPABLE_TOOLS:
            try:
                cache_key = (tool_name, json.dumps(tool_args, sort_keys=True, default=str))
            except Exception:
                cache_key = None

        if cache_key is not None and cache_key in self._tool_cache:
            result = self._tool_cache[cache_key]
            # Mark it as a cache hit in the output so the LLM knows it's a repeat.
            # We don't want to bill input tokens twice for the exact same payload.
        else:
            result = execute_tool(tool_name, tool_args)
            if cache_key is not None and result.success:
                self._tool_cache[cache_key] = result

        if self.memory:
            self.memory.track_tool_use(tool_name, tool_args, result.success)
            if tool_name in ("write_file", "edit_file"):
                self.memory.track_file_modified(tool_args.get("path", "unknown"))
            elif tool_name == "run_command":
                self.memory.track_command(tool_args.get("command", ""), result.success)

            reflection = self.reflection_engine.reflect_on_tool_use(
                tool_name, tool_args, result.success, result.output or result.error or "",
            )
            if not result.success:
                note = self._llm_reflect_on_failure(tool_name, tool_args, result.error or "")
                if note:
                    reflection.setdefault("insights", []).insert(0, note)
            if reflection.get("insights"):
                yield AgentEvent(
                    type="reflection",
                    content=f"Learning: {reflection['insights'][0]}",
                    data=reflection,
                )

        yield AgentEvent(
            type="tool_result",
            content=result.output if result.success else (result.error or ""),
            data={
                "tool": tool_name, "success": result.success,
                "output": result.output, "error": result.error,
                "input": tool_args,
            },
        )

        tool_result_msg = {
            "role": "tool",
            "content": result.output if result.success else f"Error: {result.error}",
        }
        self.conversation_history.append(tool_result_msg)
        self.cost.add_input(tool_result_msg["content"] or "")

    # -----------------------------------------------------------------
    # Anthropic path (preserved from v2.1 + new hooks)
    # -----------------------------------------------------------------

    def _process_anthropic(self, user_message: str) -> Generator[AgentEvent, None, None]:
        if self.memory:
            self.memory.track_message("user", user_message)
        self.cost.add_input(user_message)
        social_mode = self._is_social_turn(user_message)

        if self._should_answer_social_locally(user_message):
            content = self._shorten_social_reply(self._social_local_reply(user_message))
            self.conversation_history.append({"role": "user", "content": user_message})
            if self.memory:
                self.memory.track_message("assistant", content)
                self.reflection_engine.reflect_on_user_feedback(user_message, "neutral")
            self.conversation_history.append({"role": "assistant", "content": [{"type": "text", "text": content}]})
            self.cost.add_output(content)
            yield AgentEvent(type="text", content=content)
            yield AgentEvent(type="cost", content=self.cost.format(), data={"cost": self.cost.cost_usd})
            yield AgentEvent(type="done", content=get_success())
            return

        # Intent router short-circuit (same as the ollama path).
        shortcut = self._try_intent_shortcut(user_message)
        if shortcut:
            yield from self._run_intent_shortcut(user_message, *shortcut)
            return

        self.conversation_history.append({"role": "user", "content": user_message})
        self.current_task = user_message[:200]
        self.task_start_time = datetime.now()

        # Cached system prompt: one build per user message, reused across
        # every tool-loop iteration. Avoids re-running the pattern-learner
        # profile + semantic search on every API call.
        _t = time.time()
        action_mode = self._is_action_turn(user_message)
        cached_system = self._get_enhanced_system_prompt(
            user_message, lightweight=social_mode, action_mode=action_mode,
        )
        self._timing("system_prompt_build", _t)

        while True:
            if not social_mode:
                self._trim_stale_tool_results()
                self.conversation_history, compacted = self._maybe_compact(self.conversation_history)
                if compacted:
                    yield AgentEvent(type="thinking", content="(compacting older turns to stay within context)")

            yield AgentEvent(type="thinking", content=get_working())

            kwargs = dict(
                model=self.model,
                max_tokens=SOCIAL_MAX_TOKENS if social_mode else MAX_TOKENS,
                system=cached_system,
            )
            if not social_mode:
                kwargs["tools"] = TOOL_DEFINITIONS + self.plugin_definitions
            kwargs["messages"] = self._history_for_turn(social_mode=social_mode)

            response = None
            last_error: Optional[Exception] = None
            max_attempts = 3
            backoff = 1.5
            for attempt in range(1, max_attempts + 1):
                heartbeat = _Heartbeat(
                    interval_s=HEARTBEAT_SECONDS,
                    on_tick=lambda elapsed: print(f"[chahlie] still working... {elapsed}s", flush=True),
                )
                heartbeat.start()
                call_start = time.time()
                try:
                    response = self.client.messages.create(**kwargs)
                    heartbeat.stop()
                    self._timing("anthropic_call", call_start)
                    last_error = None
                    break
                except Exception as e:
                    last_error = e
                    try:
                        heartbeat.stop()
                    except Exception:
                        pass
                    if not self._is_transient_ollama_error(e) or attempt == max_attempts:
                        break
                    wait_s = backoff ** attempt
                    yield AgentEvent(
                        type="thinking",
                        content=f"(API hiccup, retryin' in {wait_s:.1f}s... try {attempt + 1}/{max_attempts})",
                    )
                    time.sleep(wait_s)

            if last_error is not None or response is None:
                err = last_error if last_error is not None else Exception("empty response")
                if self._is_transient_ollama_error(err):
                    yield AgentEvent(
                        type="error",
                        content=(
                            "API's takin' a nap, kehd. Tried 3 times and it's "
                            "still wobbly.\n\nWait a minute and ask again, or "
                            "switch backends in your .env."
                        ),
                    )
                else:
                    yield AgentEvent(type="error", content=f"API Error: {err}")
                if self.memory:
                    note = self._llm_reflect_on_failure("api_call", {}, str(err))
                    self.reflection_engine.reflect_on_tool_use("api_call", {}, False, note or str(err))
                return

            assistant_content = []
            has_tool_use = False
            text_content = ""
            tool_blocks = []

            for block in response.content:
                if block.type == "text":
                    text_content += block.text
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    has_tool_use = True
                    assistant_content.append({
                        "type": "tool_use", "id": block.id,
                        "name": block.name, "input": block.input,
                    })
                    tool_blocks.append(block)

            if social_mode:
                text_content = self._shorten_social_reply(text_content)
                assistant_content = [{"type": "text", "text": text_content}] if text_content else []
                has_tool_use = False

            self.cost.add_output(text_content)

            if text_content:
                yield AgentEvent(type="text", content=text_content)
            if self.memory:
                self.memory.track_message("assistant", text_content)

            self.conversation_history.append({"role": "assistant", "content": assistant_content})

            if not has_tool_use or response.stop_reason == "end_turn":
                if not has_tool_use:
                    yield AgentEvent(type="cost", content=self.cost.format(), data={"cost": self.cost.cost_usd})
                    yield AgentEvent(type="done", content=get_success())
                    if self.memory:
                        self.reflection_engine.reflect_on_user_feedback(user_message, "neutral")
                    return

            tool_results = []
            for block in tool_blocks:
                yield AgentEvent(
                    type="tool_use", content=f"Using {block.name}",
                    data={"tool": block.name, "input": block.input},
                )
                result = execute_tool(block.name, block.input)
                if self.memory:
                    self.memory.track_tool_use(block.name, block.input, result.success)
                    if block.name in ("write_file", "edit_file"):
                        self.memory.track_file_modified(block.input.get("path", "unknown"))
                    elif block.name == "run_command":
                        self.memory.track_command(block.input.get("command", ""), result.success)
                    reflection = self.reflection_engine.reflect_on_tool_use(
                        block.name, block.input, result.success, result.output or result.error or "",
                    )
                    if not result.success:
                        note = self._llm_reflect_on_failure(block.name, block.input, result.error or "")
                        if note:
                            reflection.setdefault("insights", []).insert(0, note)
                    if reflection.get("insights"):
                        yield AgentEvent(
                            type="reflection",
                            content=f"Learning: {reflection['insights'][0]}",
                            data=reflection,
                        )
                yield AgentEvent(
                    type="tool_result",
                    content=result.output if result.success else (result.error or ""),
                    data={
                        "tool": block.name, "success": result.success,
                        "output": result.output, "error": result.error,
                        "input": block.input,
                    },
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result.output if result.success else f"Error: {result.error}",
                    "is_error": not result.success,
                })
                self.cost.add_input(result.output or result.error or "")

            self.conversation_history.append({"role": "user", "content": tool_results})

            if response.stop_reason == "end_turn":
                yield AgentEvent(type="cost", content=self.cost.format(), data={"cost": self.cost.cost_usd})
                yield AgentEvent(type="done", content=get_success())
                return

    # -----------------------------------------------------------------
    # public API
    # -----------------------------------------------------------------

    def process(self, user_message: str) -> Generator[AgentEvent, None, None]:
        if self.backend == "anthropic":
            yield from self._process_anthropic(user_message)
        else:
            yield from self._process_ollama(user_message)

    def chat(self, user_message: str) -> str:
        final_text = ""
        for event in self.process(user_message):
            if event.type == "text":
                final_text += event.content
        return final_text

    def get_memory_summary(self) -> dict:
        if not self.memory:
            return {"enabled": False}
        return {
            "enabled": True,
            "summary": self.memory.get_summary(),
            "user_profile": self.pattern_learner.get_user_profile(),
            "improvement_plan": self.reflection_engine.generate_improvement_plan(),
        }

    def get_cost_summary(self) -> dict:
        return {
            "input_tokens": self.cost.input_tokens,
            "output_tokens": self.cost.output_tokens,
            "cost_usd": self.cost.cost_usd,
            "formatted": self.cost.format(),
            "backend": self.backend,
            "model": self.model,
        }

    def get_primer_summary(self) -> dict:
        return self.primer

    def __del__(self):
        try:
            if self.memory and self.memory.current_session_start:
                self.memory.end_session("Session ended")
        except Exception:
            pass
