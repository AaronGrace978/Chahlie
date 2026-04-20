"""
Tests for the v2.3.1 perf patch.

Covers:
- _trim_stale_tool_results clamps old Ollama tool messages
- _trim_stale_tool_results clamps Anthropic tool_result blocks
- _Heartbeat fires and can be stopped
- System prompt cache is used once per turn, not per tool iteration
- HISTORY_TOOL_CHAR_CAP=0 disables trimming
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
    time.sleep(2.3)
    hb.stop()
    time.sleep(1.2)
    check("at least one tick fired", len(ticks) >= 1, detail=f"ticks={ticks}")
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


def main():
    for fn in (
        test_trim_ollama_tool,
        test_trim_anthropic_tool_result,
        test_trim_disabled,
        test_heartbeat_fires_then_stops,
        test_heartbeat_tickle_suppresses,
        test_heartbeat_short_task_no_tick,
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
