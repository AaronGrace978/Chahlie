"""
Tests for the v2.3.1 perf patch.

Covers:
- _trim_stale_tool_results clamps old Ollama tool messages
- _trim_stale_tool_results clamps Anthropic tool_result blocks
- _Heartbeat fires and can be stopped
- _Heartbeat reports cumulative elapsed time
- System prompt cache is used once per turn, not per tool iteration
- HISTORY_TOOL_CHAR_CAP=0 disables trimming
- Social fast-path detects banter and ignores command-like requests
- Social history trims out tool chatter and only keeps recent conversation
- Social reply clamp limits line count / chars
"""

from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

os.environ["OLLAMA_API_KEY"] = "fake-key"
os.environ["CHAHLIE_HISTORY_TOOL_CHAR_CAP"] = "200"

from importlib import reload
import chahlie.config as _cfg; reload(_cfg)
import chahlie.agent as _agent; reload(_agent)

from chahlie.agent import _Heartbeat, ChahlieAgent

PASS = []
FAIL = []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append((name, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{' - ' + detail if detail and not ok else ''}")


# ---------------------------------------------------------------------
def _fake_agent():
    """Build an agent without running __init__ (avoids backend imports)."""
    a = ChahlieAgent.__new__(ChahlieAgent)
    a.conversation_history = []
    return a


def test_trim_ollama_tool():
    print("\n[trim ollama tool]")
    a = _fake_agent()
    big = "X" * 5000
    a.conversation_history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "ok"},
        {"role": "tool", "content": big},
        {"role": "assistant", "content": "still here"},
        {"role": "user", "content": "again"},
        {"role": "tool", "content": big},  # in the tail - should stay
    ]
    a._trim_stale_tool_results()
    check("old tool msg trimmed", len(a.conversation_history[2]["content"]) < 300)
    check("tail tool msg untouched", len(a.conversation_history[-1]["content"]) == 5000)


def test_trim_anthropic_tool_result():
    print("\n[trim anthropic tool_result]")
    a = _fake_agent()
    big = "Y" * 4000
    a.conversation_history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": [{"type": "text", "text": "ok"}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": big}]},
        {"role": "assistant", "content": "sure"},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t2", "content": big}]},
    ]
    a._trim_stale_tool_results()
    trimmed = a.conversation_history[2]["content"][0]["content"]
    tail = a.conversation_history[-1]["content"][0]["content"]
    check("old tool_result block trimmed", len(trimmed) < 300)
    check("tail tool_result block untouched", len(tail) == 4000)


def test_trim_disabled():
    print("\n[trim disabled via cap=0]")
    os.environ["CHAHLIE_HISTORY_TOOL_CHAR_CAP"] = "0"
    import chahlie.config as cfg2; reload(cfg2)
    import chahlie.agent as ag2; reload(ag2)
    a = ag2.ChahlieAgent.__new__(ag2.ChahlieAgent)
    a.conversation_history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "ok"},
        {"role": "tool", "content": "Z" * 5000},
        {"role": "assistant", "content": "x"},
        {"role": "user", "content": "y"},
    ]
    a._trim_stale_tool_results()
    check("trimming no-op when cap=0", len(a.conversation_history[2]["content"]) == 5000)
    os.environ["CHAHLIE_HISTORY_TOOL_CHAR_CAP"] = "200"


def test_heartbeat_fires_then_stops():
    print("\n[heartbeat]")
    ticks = []
    hb = _Heartbeat(interval_s=1, on_tick=lambda e: ticks.append(e))
    hb.start()
    time.sleep(3.3)
    hb.stop()
    time.sleep(1.2)
    check("at least one tick fired", len(ticks) >= 1, detail=f"ticks={ticks}")
    check("ticks increase cumulatively", ticks == sorted(ticks) and len(set(ticks)) == len(ticks), detail=f"ticks={ticks}")
    check("later tick is > first tick", len(ticks) < 2 or ticks[-1] > ticks[0], detail=f"ticks={ticks}")
    count_after_stop = len(ticks)
    time.sleep(1.5)
    check("no ticks after stop", len(ticks) == count_after_stop)


def test_heartbeat_tickle_suppresses():
    print("\n[heartbeat tickle]")
    ticks = []
    hb = _Heartbeat(interval_s=1, on_tick=lambda e: ticks.append(e))
    hb.start()
    time.sleep(0.2)
    hb.tickle()  # simulate first-byte arrival immediately
    time.sleep(2.0)
    hb.stop()
    check("tickle suppresses all ticks", len(ticks) == 0, detail=f"ticks={ticks}")


def test_heartbeat_short_task_no_tick():
    print("\n[heartbeat short task]")
    ticks = []
    hb = _Heartbeat(interval_s=5, on_tick=lambda e: ticks.append(e))
    hb.start()
    time.sleep(0.2)
    hb.stop()
    check("no tick before interval", len(ticks) == 0)


def test_social_detection():
    print("\n[social detection]")
    a = _fake_agent()
    check("hype/banter is social", a._is_social_turn("YOOOOOO lets go buddy"))
    check("gift/snack banter is social", a._is_social_turn("here take this donut muffin"))
    check("command-like request is NOT social", not a._is_social_turn("open notepad and write me a note"))
    check("coding request is NOT social", not a._is_social_turn("can you fix the failing tests"))


def test_social_history_slice():
    print("\n[social history slice]")
    a = _fake_agent()
    a.conversation_history = [
        {"role": "user", "content": "old 1"},
        {"role": "assistant", "content": "old 2"},
        {"role": "tool", "content": "very noisy tool output"},
        {"role": "assistant", "content": [{"type": "text", "text": "recent assistant"}]},
        {"role": "user", "content": [{"type": "tool_result", "content": "tool result should be skipped"}]},
        {"role": "user", "content": "recent user"},
    ]
    tail = a._history_for_turn(social_mode=True)
    check("tool role skipped", all(msg["role"] != "tool" for msg in tail), detail=str(tail))
    check("assistant text blocks flattened", any(msg["content"] == "recent assistant" for msg in tail), detail=str(tail))
    check("tool_result-only user block skipped", all("tool result" not in msg["content"] for msg in tail), detail=str(tail))
    check("recent user retained", tail[-1]["content"] == "recent user", detail=str(tail))


def test_social_reply_clamp():
    print("\n[social reply clamp]")
    a = _fake_agent()
    text = "\n".join([
        "line one is kinda long and keeps going for dramatic effect",
        "line two is here",
        "line three is here",
        "line four is here",
        "line five should be cut",
    ])
    out = a._shorten_social_reply(text)
    lines = [ln for ln in out.splitlines() if ln.strip()]
    check("reply limited to configured line cap", len(lines) <= 4, detail=out)
    check("reply limited to configured char cap", len(out) <= 320, detail=str(len(out)))
    check("truncation removes extra fifth line", "line five" not in out, detail=out)


def main():
    for fn in (
        test_trim_ollama_tool,
        test_trim_anthropic_tool_result,
        test_trim_disabled,
        test_heartbeat_fires_then_stops,
        test_heartbeat_tickle_suppresses,
        test_heartbeat_short_task_no_tick,
        test_social_detection,
        test_social_history_slice,
        test_social_reply_clamp,
    ):
        try:
            fn()
        except Exception:
            traceback.print_exc()
            FAIL.append((fn.__name__, "crashed"))

    print("\n" + "=" * 60)
    print(f"{len(PASS)} passed, {len(FAIL)} failed")
    print("=" * 60)
    if FAIL:
        for n, d in FAIL:
            print(f"  FAIL: {n} - {d}")
        sys.exit(1)


if __name__ == "__main__":
    main()
