"""
Context window management for Chahlie.

Two responsibilities:

1. **Token-estimate tracking** across conversation history so we can display
   a running cost meter and know when to compact.
2. **Compaction**: when total history grows past the configured threshold,
   summarize the oldest turns (leaving the most recent N verbatim) via a
   cheap LLM call, and replace them with the summary.

Deliberately doesn't depend on tiktoken etc. - we use a simple 4-chars-per-token
heuristic which is good enough for rate-limit decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional


CHARS_PER_TOKEN_HEURISTIC = 4


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN_HEURISTIC)


def estimate_messages_chars(messages: List[dict]) -> int:
    total = 0
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, str):
            total += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    for v in block.values():
                        if isinstance(v, str):
                            total += len(v)
                elif isinstance(block, str):
                    total += len(block)
    return total


@dataclass
class CostMeter:
    """Tracks input/output token estimates and computes an optional dollar cost."""
    input_tokens: int = 0
    output_tokens: int = 0
    input_rate: float = 0.0   # USD per million input tokens
    output_rate: float = 0.0  # USD per million output tokens

    def add_input(self, text: str) -> None:
        self.input_tokens += estimate_tokens(text)

    def add_output(self, text: str) -> None:
        self.output_tokens += estimate_tokens(text)

    @property
    def cost_usd(self) -> float:
        return (
            (self.input_tokens / 1_000_000.0) * self.input_rate
            + (self.output_tokens / 1_000_000.0) * self.output_rate
        )

    def format(self) -> str:
        total = self.input_tokens + self.output_tokens
        if self.input_rate == 0 and self.output_rate == 0:
            return f"~{total:,} tokens (in {self.input_tokens:,} / out {self.output_tokens:,})"
        return (
            f"~{total:,} tokens | est. ${self.cost_usd:.4f} "
            f"(in {self.input_tokens:,} / out {self.output_tokens:,})"
        )


def compact_history(
    messages: List[dict],
    *,
    threshold_chars: int,
    preserve_recent: int,
    summarize_fn: Callable[[List[dict]], str],
) -> tuple[List[dict], bool]:
    """Compact `messages` if total chars exceeds threshold.

    Parameters
    ----------
    messages : list of {"role", "content"} dicts (the system message, if any,
        should be EXCLUDED - compaction runs on the dialogue history only).
    threshold_chars : size in characters above which compaction triggers.
    preserve_recent : how many most-recent messages to leave verbatim.
    summarize_fn : callable taking the older turns and returning a summary
        string. Passing a noop `lambda _: ""` disables summarization and
        simply drops the oldest turns.

    Returns
    -------
    (new_messages, did_compact)
    """
    if estimate_messages_chars(messages) <= threshold_chars:
        return messages, False

    if len(messages) <= preserve_recent:
        return messages, False

    head = messages[:-preserve_recent]
    tail = messages[-preserve_recent:]

    summary_text = ""
    try:
        summary_text = summarize_fn(head) or ""
    except Exception:
        summary_text = ""

    if not summary_text:
        # Fallback: truncate head into a single terse notice instead of dropping silently
        summary_text = (
            f"[Older history truncated - {len(head)} earlier messages omitted "
            f"to stay within context window.]"
        )

    summary_msg = {
        "role": "system",
        "content": f"[Earlier conversation summary]\n{summary_text}",
    }
    return [summary_msg] + tail, True
