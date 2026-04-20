"""
Chahlie's Agent Core - v2.2 "Big Dig"

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
from dataclasses import dataclass
from datetime import datetime
from typing import Generator, Optional

from .config import (
    BACKEND,
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
    OLLAMA_CLOUD_HOST, OLLAMA_CLOUD_API_KEY, OLLAMA_LOCAL_HOST, OLLAMA_MODEL,
    MAX_TOKENS,
    STREAMING,
    COMPACT_THRESHOLD_CHARS, COMPACT_PRESERVE_RECENT,
    LLM_REFLECTION,
    SEMANTIC_MEMORY, EMBEDDING_MODEL, SEMANTIC_TOP_K,
    COST_RATES, PLUGINS_DIR,
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
                self._seed_semantic_memory()
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
            self.client = Client(
                host=OLLAMA_CLOUD_HOST,
                headers={'Authorization': f'Bearer {OLLAMA_CLOUD_API_KEY}'},
            )
            self.model = OLLAMA_MODEL
        else:  # ollama-local
            from ollama import Client
            self.client = Client(host=OLLAMA_LOCAL_HOST)
            self.model = OLLAMA_MODEL

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
        if self.memory:
            self.memory.end_session("Session cleared by user")
            self.memory.start_session()

    # -----------------------------------------------------------------
    # prompt construction
    # -----------------------------------------------------------------

    def _get_enhanced_system_prompt(self, user_message: str = "") -> str:
        """Base prompt + project primer + learned user patterns + recent reflections."""
        parts = [SYSTEM_PROMPT]

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

    def _call_ollama(self, messages: list[dict], stream: bool) -> Generator[dict, None, None]:
        """Yields incremental chunks when streaming, or a single chunk otherwise."""
        tools = self._ollama_tools()
        if not stream:
            resp = self.client.chat(
                model=self.model, messages=messages, tools=tools, stream=False,
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
            model=self.model, messages=messages, tools=tools, stream=True,
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

        system_prompt = self._get_enhanced_system_prompt(user_message)
        self.cost.add_input(system_prompt)

        self.conversation_history.append({"role": "user", "content": user_message})
        self.current_task = user_message[:200]
        self.task_start_time = datetime.now()

        use_stream = STREAMING

        while True:
            # Compact history if it's grown too large
            self.conversation_history, compacted = self._maybe_compact(self.conversation_history)
            if compacted:
                yield AgentEvent(
                    type="thinking",
                    content="(compacting older turns to stay within context)",
                )

            messages = [{"role": "system", "content": system_prompt}] + self.conversation_history
            yield AgentEvent(type="thinking", content=get_working())

            try:
                final_payload = None
                streamed_text = ""
                for chunk in self._call_ollama(messages, stream=use_stream):
                    if chunk.get("stream_delta"):
                        streamed_text += chunk["content"]
                        yield AgentEvent(type="text", content=chunk["content"], data={"streaming": True})
                    else:
                        final_payload = chunk
            except Exception as e:
                yield AgentEvent(type="error", content=f"Ollama Error: {e}")
                if self.memory:
                    note = self._llm_reflect_on_failure("api_call", {}, str(e))
                    self.reflection_engine.reflect_on_tool_use(
                        "api_call", {}, False, note or str(e),
                    )
                return

            if final_payload is None:
                yield AgentEvent(type="error", content="Empty response from backend")
                return

            content = final_payload.get("content", "") or streamed_text
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
                yield AgentEvent(type="text", content=content)

            if not tool_calls:
                yield AgentEvent(type="cost", content=self.cost.format(), data={"cost": self.cost.cost_usd})
                yield AgentEvent(type="done", content=get_success())
                if self.memory:
                    self.reflection_engine.reflect_on_user_feedback(user_message, "neutral")
                return

            # Execute tool calls
            for tool_call in tool_calls:
                yield from self._execute_and_emit(tool_call.get("function", {}))

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

        result = execute_tool(tool_name, tool_args)

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

        self.conversation_history.append({"role": "user", "content": user_message})
        self.current_task = user_message[:200]
        self.task_start_time = datetime.now()

        while True:
            self.conversation_history, compacted = self._maybe_compact(self.conversation_history)
            if compacted:
                yield AgentEvent(type="thinking", content="(compacting older turns to stay within context)")

            yield AgentEvent(type="thinking", content=get_working())
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=MAX_TOKENS,
                    system=self._get_enhanced_system_prompt(user_message),
                    tools=TOOL_DEFINITIONS + self.plugin_definitions,
                    messages=self.conversation_history,
                )
            except Exception as e:
                yield AgentEvent(type="error", content=f"API Error: {e}")
                if self.memory:
                    note = self._llm_reflect_on_failure("api_call", {}, str(e))
                    self.reflection_engine.reflect_on_tool_use("api_call", {}, False, note or str(e))
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
