"""
Sub-agent delegation for Chahlie.

Spawns a throwaway ChahlieAgent instance (no memory, no streaming) to handle
a narrowly-scoped task - typically exploration ("grep the codebase and
summarize") - without polluting the parent agent's conversation history or
token budget.

The sub-agent returns ONE synthesized text answer; individual tool events
are NOT propagated to the parent UI, which is the whole point: the parent
gets a clean summary, not 50 lines of tool noise.

Usage from a tool function:

    from .subagent import delegate
    result = delegate("Find all places we call `subprocess.run` and list them.")

Implementation detail: we create a fresh ChahlieAgent with enable_memory=False
and streaming off, run it to completion, and gather the assistant text.
"""

from __future__ import annotations

from typing import Optional


def delegate(task: str, *, max_turns: int = 8, backend: Optional[str] = None) -> str:
    """Run a sub-agent to completion on `task` and return its final text.

    Errors are caught and returned as a human-readable string - the parent
    agent sees the failure in-band rather than raising.
    """
    # Local import avoids circular-import issues (agent <-> subagent).
    from .agent import ChahlieAgent

    try:
        sub = ChahlieAgent(backend=backend, enable_memory=False)
        final_text_parts = []
        turn_count = 0
        for event in sub.process(task):
            if event.type == "text":
                final_text_parts.append(event.content)
            elif event.type == "error":
                return f"[sub-agent error] {event.content}"
            elif event.type == "done":
                break
            elif event.type == "tool_use":
                turn_count += 1
                if turn_count > max_turns:
                    return (
                        "[sub-agent aborted] exceeded max_turns="
                        f"{max_turns}. Partial output:\n" + "".join(final_text_parts)
                    )
        return "".join(final_text_parts).strip() or "[sub-agent returned no text]"
    except Exception as e:
        return f"[sub-agent failed to start] {e}"
