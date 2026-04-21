"""
Tests for v2.4.0 "Juice Box" - persistent vectors, ToT planner,
multi-model fallback chain.

Every test uses stubbed clients / chat callables so nothing here touches
the network. Run with: python -m pytest test_v24_juice.py -q
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------
# semantic memory factory + in-memory backend (always available)
# ---------------------------------------------------------------


class _FakeEmbedClient:
    """Deterministic "embedding" client: text length -> 8-dim vector."""

    def embed(self, model: str, input: str):  # noqa: A002 - match ollama API
        base = [float((ord(c) % 7) + 1) for c in (input or "x")[:8]]
        while len(base) < 8:
            base.append(0.0)
        return {"embeddings": [base[:8]]}


def test_in_memory_semantic_add_and_search():
    from chahlie.memory.semantic import SemanticMemory

    store = SemanticMemory(_FakeEmbedClient(), "fake-embed")
    assert store.size == 0
    assert store.add("red sox pitching rotation", {"kind": "note"})
    assert store.add("celtics defensive schemes", {"kind": "note"})
    assert store.size == 2
    results = store.search("red sox", top_k=1)
    assert len(results) == 1
    score, entry = results[0]
    assert isinstance(score, float)
    assert "red sox" in entry.text or "celtics" in entry.text
    assert store.backend_name == "in-memory"


def test_semantic_empty_text_rejected():
    from chahlie.memory.semantic import SemanticMemory

    store = SemanticMemory(_FakeEmbedClient(), "fake-embed")
    assert not store.add("", {})
    assert not store.add("   ", {})
    assert store.size == 0


def test_semantic_factory_fallback_when_no_project_root():
    """With project_root=None, factory must fall through to in-memory."""
    from chahlie.memory.semantic import get_semantic_store, SemanticMemory

    store = get_semantic_store(_FakeEmbedClient(), "fake-embed", project_root=None)
    assert isinstance(store, SemanticMemory)
    assert store.backend_name == "in-memory"


def test_semantic_factory_fallback_when_chromadb_missing():
    """If chromadb import fails, factory must return the in-memory backend."""
    from chahlie.memory import semantic as sem_mod
    from chahlie.memory.semantic import get_semantic_store, SemanticMemory

    # Force PersistentSemanticMemory construction to blow up like chromadb is missing.
    def _boom(*a, **kw):
        raise ImportError("chromadb not installed (simulated)")

    with patch.object(sem_mod, "PersistentSemanticMemory", side_effect=_boom):
        store = get_semantic_store(
            _FakeEmbedClient(), "fake-embed",
            project_root=Path(tempfile.gettempdir()),
            prefer_persistent=True,
        )
    assert isinstance(store, SemanticMemory)


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("chromadb") is None,
    reason="chromadb not installed in this environment",
)
def test_persistent_semantic_round_trip(tmp_path):
    """If chromadb IS available, exercise the persistent backend end-to-end."""
    from chahlie.memory.semantic import PersistentSemanticMemory

    store = PersistentSemanticMemory(_FakeEmbedClient(), "fake-embed", tmp_path)
    assert store.backend_name == "chromadb"
    assert store.add("dunkin iced coffee is superior", {"kind": "opinion"})
    assert store.add("fenway green monster is 37 feet", {"kind": "fact"})
    assert store.size >= 2
    results = store.search("dunkin", top_k=2)
    assert results, "persistent store should return results after add"
    assert (tmp_path / ".chahlie" / "vector_store").exists()


# ---------------------------------------------------------------
# Tree-of-Thoughts planner
# ---------------------------------------------------------------


def _scripted_chat(responses):
    """Build a fake chat callable that yields scripted responses in order."""
    idx = {"i": 0}

    def _call(messages, model=None):
        i = idx["i"]
        idx["i"] = min(i + 1, len(responses) - 1)
        return [{"role": "assistant", "content": responses[i]}]

    return _call


def test_should_plan_flags_big_task():
    from chahlie.planner import should_plan

    big = "Please refactor the authentication module to support OAuth providers and add JWT refresh tokens with proper expiry handling."
    small = "yo buddy hi"
    assert should_plan(big, min_chars=80)
    assert not should_plan(small, min_chars=80)
    assert not should_plan("", min_chars=80)


def test_should_plan_rejects_short_tasks_without_keywords():
    from chahlie.planner import should_plan

    # Below min_chars AND has no keywords -> skip.
    assert not should_plan("write a haiku", min_chars=140)


def test_plan_task_parses_candidates_and_picks_winner():
    from chahlie.planner import plan_task

    candidates_text = (
        "APPROACH 1: Quick patch\n"
        "Just slap a try/except around the call and log the error. Fast but hides real issues.\n\n"
        "APPROACH 2: Add retries with backoff\n"
        "Wrap the call in an exponential-backoff retry. Handles transient failures cleanly.\n\n"
        "APPROACH 3: Refactor to a circuit breaker\n"
        "Introduce a full circuit-breaker pattern. Most robust but overkill for this bug.\n"
    )
    judgment_text = "CHOICE: 2\nREASON: best balance of simplicity and reliability"

    chat = _scripted_chat([candidates_text, judgment_text])
    plan = plan_task("Fix the flaky API call in our scheduler so it stops 500ing once a day.",
                     chat, model="fake", candidates=3)
    assert plan is not None
    assert len(plan.all_candidates) == 3
    assert plan.chosen.index == 2
    assert "retries" in plan.chosen.title.lower() or "backoff" in plan.chosen.body.lower()
    assert "simplicity" in plan.reason.lower()
    preamble = plan.as_preamble()
    assert "Planned approach" in preamble
    assert "retries" in preamble.lower() or "backoff" in preamble.lower()


def test_plan_task_handles_empty_generation():
    from chahlie.planner import plan_task

    chat = _scripted_chat(["", ""])
    plan = plan_task("big task please plan", chat, model="fake", candidates=3)
    assert plan is None


def test_plan_task_recovers_when_judge_output_is_garbage():
    from chahlie.planner import plan_task

    candidates_text = (
        "APPROACH 1: Do it fast\nShip something small and iterate.\n\n"
        "APPROACH 2: Do it right\nDesign the interface first, then implement.\n"
    )
    # Judge returns a free-form paragraph with no CHOICE/REASON lines.
    judge_text = "i think both are fine honestly pick whatever you want kehd"
    chat = _scripted_chat([candidates_text, judge_text])
    plan = plan_task("build feature X with lots of moving parts", chat, model="fake", candidates=2)
    assert plan is not None
    # Should fall back to first candidate on garbage judgment.
    assert plan.chosen.index == 1


# ---------------------------------------------------------------
# Multi-model fallback chain
# ---------------------------------------------------------------


def test_models_to_try_empty_chain_is_just_primary():
    from chahlie import agent as ag_mod
    from chahlie.agent import ChahlieAgent

    a = ChahlieAgent.__new__(ChahlieAgent)
    a.backend = "ollama-cloud"
    with patch.object(ag_mod, "FALLBACK_MODELS", []):
        assert a._models_to_try("qwen3.5:cloud") == ["qwen3.5:cloud"]


def test_models_to_try_appends_fallbacks_and_dedupes():
    from chahlie import agent as ag_mod
    from chahlie.agent import ChahlieAgent

    a = ChahlieAgent.__new__(ChahlieAgent)
    a.backend = "ollama-cloud"
    with patch.object(ag_mod, "FALLBACK_MODELS", ["glm-5.1", "qwen3.5:cloud", "devstral-small-2"]):
        chain = a._models_to_try("qwen3.5:cloud")
    assert chain == ["qwen3.5:cloud", "glm-5.1", "devstral-small-2"]


def test_models_to_try_anthropic_ignores_chain():
    from chahlie import agent as ag_mod
    from chahlie.agent import ChahlieAgent

    a = ChahlieAgent.__new__(ChahlieAgent)
    a.backend = "anthropic"
    with patch.object(ag_mod, "FALLBACK_MODELS", ["ignored-model"]):
        assert a._models_to_try("claude-sonnet-4") == ["claude-sonnet-4"]


# ---------------------------------------------------------------
# Integration sanity - the planner short-circuit path
# ---------------------------------------------------------------


def test_maybe_plan_task_skips_when_feature_off():
    from chahlie import agent as ag_mod
    from chahlie.agent import ChahlieAgent

    a = ChahlieAgent.__new__(ChahlieAgent)
    a.backend = "ollama-cloud"
    with patch.object(ag_mod, "TOT_PLANNING", False):
        assert a._maybe_plan_task("build me a cool feature " * 20, "fake") is None


def test_maybe_plan_task_skips_social_turn():
    from chahlie import agent as ag_mod
    from chahlie.agent import ChahlieAgent

    a = ChahlieAgent.__new__(ChahlieAgent)
    a.backend = "ollama-cloud"
    a.conversation_history = []
    # Force social detection ON for any input by stubbing the method.
    a._is_social_turn = lambda msg: True  # type: ignore[method-assign]
    with patch.object(ag_mod, "TOT_PLANNING", True):
        assert a._maybe_plan_task("yo buddy", "fake") is None
