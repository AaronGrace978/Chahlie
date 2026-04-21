"""
Tree-of-Thoughts planner for Chahlie.

For non-trivial tasks, generates N candidate high-level approaches in one
cheap LLM call, then has the model pick the best one in a second call.
The winning plan is returned as a short paragraph that the agent prepends
to its system prompt for the current turn, so the main tool loop starts
with a clear direction instead of chasing the first idea it thinks of.

Design notes:
- TWO LLM calls max (generate + judge). Anything more is too expensive for
  a default feature. If the judge call fails, we fall back to candidate #1.
- Output is text; parsing is forgiving. We explicitly do NOT require the
  model to emit strict JSON - experience shows small models regularly
  break JSON output under pressure.
- Completely stateless. No dependence on agent internals beyond the
  caller passing in a chat callable.

Usage from agent.py:

    from .planner import plan_task
    plan = plan_task(
        task=user_message,
        chat=lambda msgs, model=None: self._call_ollama(msgs, stream=False, model=model),
        model=planner_model,
        candidates=3,
    )
    if plan:
        system_prompt = plan.as_preamble() + "\\n\\n" + system_prompt
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Optional

ChatFn = Callable[[list, Optional[str]], Iterable[dict]]


# Heuristic triggers - only bother planning when the user is clearly asking
# for a multi-step job. Keeps default overhead near zero.
_PLANNING_KEYWORDS = (
    "build", "implement", "refactor", "migrate", "design", "architect",
    "add feature", "add a feature", "redesign", "rewrite", "overhaul",
    "set up", "scaffold", "plan", "investigate", "debug the", "fix the bug",
    "make it support", "integrate", "wire up", "port", "upgrade",
)


@dataclass
class Approach:
    index: int
    title: str
    body: str


@dataclass
class Plan:
    chosen: Approach
    reason: str
    all_candidates: List[Approach] = field(default_factory=list)

    def as_preamble(self) -> str:
        """Render the plan as a short system-prompt preamble."""
        lines = [
            "[Planned approach - chosen before acting]",
            f"Title: {self.chosen.title}",
            "Steps/rationale:",
            self.chosen.body.rstrip(),
        ]
        if self.reason:
            lines.append(f"Why this over the alternatives: {self.reason}")
        return "\n".join(lines)


def should_plan(task: str, *, min_chars: int = 140) -> bool:
    """Cheap pre-check: is this task big enough to justify a planning call?"""
    text = (task or "").strip()
    if len(text) < min_chars:
        return False
    lowered = text.lower()
    if any(kw in lowered for kw in _PLANNING_KEYWORDS):
        return True
    # Multi-sentence requests with lots of "and" often imply multi-step work.
    if text.count("\n") >= 2 or text.count(".") >= 3:
        return True
    return False


def plan_task(
    task: str,
    chat: ChatFn,
    *,
    model: Optional[str] = None,
    candidates: int = 3,
) -> Optional[Plan]:
    """Run the two-shot ToT planner. Returns None on any failure.

    `chat(messages, model=...)` is expected to yield dict chunks; we only
    need the final assembled text. The caller passes in a closure that
    wraps their existing chat primitive (see module docstring for an
    example).
    """
    candidates = max(2, min(5, int(candidates)))
    approaches = _generate_candidates(task, chat, model=model, n=candidates)
    if not approaches:
        return None
    chosen_idx, reason = _judge_candidates(task, approaches, chat, model=model)
    # Clamp to valid range; default to first candidate on parse failure.
    if chosen_idx < 0 or chosen_idx >= len(approaches):
        chosen_idx = 0
    return Plan(chosen=approaches[chosen_idx], reason=reason, all_candidates=approaches)


# ---------------------------------------------------------------
# internals
# ---------------------------------------------------------------


_GENERATE_PROMPT = """You are a planning assistant. The user wants to accomplish the task below.

Propose exactly {n} DISTINCT high-level approaches. Each approach should be 2-4 sentences describing the strategy, key trade-offs, and the first concrete step.

Format each approach on its own block EXACTLY like this (keep the headers verbatim):

APPROACH 1: <short title>
<2-4 sentence description>

APPROACH 2: <short title>
<2-4 sentence description>

(and so on up to {n})

Do not add extra commentary before or after the approaches. Do not use markdown headers. Just the blocks above.

TASK:
{task}"""


_JUDGE_PROMPT = """You are reviewing {n} candidate approaches to the task below.

Pick the SINGLE best approach. Consider: correctness, simplicity, how well it fits the stated task, and risk of going off-track.

Output EXACTLY two lines and nothing else:

CHOICE: <the number, 1 through {n}>
REASON: <one short sentence explaining why>

TASK:
{task}

CANDIDATES:
{candidates_block}"""


def _collect_text(chat: ChatFn, messages: list, model: Optional[str]) -> str:
    """Run a single-turn chat call and concatenate any text content."""
    parts: List[str] = []
    try:
        for chunk in chat(messages, model):
            if not isinstance(chunk, dict):
                continue
            content = chunk.get("content") or ""
            if content and not chunk.get("stream_delta"):
                # Non-streaming final payload - this is what we want.
                parts.append(content)
            elif content and chunk.get("stream_delta"):
                parts.append(content)
    except Exception:
        return ""
    return "".join(parts).strip()


def _generate_candidates(
    task: str, chat: ChatFn, *, model: Optional[str], n: int,
) -> List[Approach]:
    messages = [
        {"role": "system", "content": "You are a concise planning assistant. Follow the user's format exactly."},
        {"role": "user", "content": _GENERATE_PROMPT.format(n=n, task=task.strip())},
    ]
    raw = _collect_text(chat, messages, model)
    if not raw:
        return []
    return _parse_approaches(raw, expected=n)


def _parse_approaches(raw: str, *, expected: int) -> List[Approach]:
    """Parse blocks that start with `APPROACH <n>:` headers."""
    # Split on "APPROACH N:" headers while keeping the header text.
    parts = re.split(r"(?im)^\s*APPROACH\s+(\d+)\s*:\s*", raw)
    # re.split with a capturing group yields: [before, num, block, num, block, ...]
    approaches: List[Approach] = []
    if len(parts) <= 1:
        return approaches
    # Iterate pairs of (number, body).
    it = iter(parts[1:])
    for num_str in it:
        body = next(it, "").strip()
        if not body:
            continue
        first_line, _, rest = body.partition("\n")
        title = first_line.strip().rstrip(".") or f"Approach {num_str}"
        detail = rest.strip() or first_line.strip()
        try:
            idx = int(num_str)
        except ValueError:
            idx = len(approaches) + 1
        approaches.append(Approach(index=idx, title=title, body=detail))
        if len(approaches) >= expected:
            break
    return approaches


def _judge_candidates(
    task: str,
    approaches: List[Approach],
    chat: ChatFn,
    *,
    model: Optional[str],
) -> tuple[int, str]:
    """Returns (zero-based winning index, short reason). Falls back to (0, '')."""
    if len(approaches) == 1:
        return 0, "only one viable approach generated"

    block_lines: List[str] = []
    for i, a in enumerate(approaches, start=1):
        block_lines.append(f"APPROACH {i}: {a.title}\n{a.body}")
    candidates_block = "\n\n".join(block_lines)

    messages = [
        {"role": "system", "content": "You are a careful reviewer. Output only the required two lines."},
        {"role": "user", "content": _JUDGE_PROMPT.format(
            n=len(approaches), task=task.strip(), candidates_block=candidates_block,
        )},
    ]
    raw = _collect_text(chat, messages, model)
    if not raw:
        return 0, ""
    return _parse_judgment(raw, max_idx=len(approaches))


def _parse_judgment(raw: str, *, max_idx: int) -> tuple[int, str]:
    choice_match = re.search(r"(?im)^\s*CHOICE\s*:\s*(\d+)", raw)
    reason_match = re.search(r"(?im)^\s*REASON\s*:\s*(.+)$", raw)
    if not choice_match:
        # Last-ditch: any number in the first 30 chars.
        fallback = re.search(r"\b([1-9])\b", raw[:60])
        if fallback:
            idx1 = int(fallback.group(1))
        else:
            return 0, ""
    else:
        idx1 = int(choice_match.group(1))
    idx0 = max(1, min(max_idx, idx1)) - 1
    reason = reason_match.group(1).strip() if reason_match else ""
    return idx0, reason
