"""
Semantic memory retrieval for Chahlie.

Embeds learnings and session summaries via the configured Ollama embedding
model, then at prompt-build time retrieves the top-K most relevant entries
for the current user message instead of dumping the entire memory into the
context window.

Gracefully no-ops if:
- SEMANTIC_MEMORY is disabled in config
- The embedding model isn't available
- The Ollama client isn't configured

Callers should always have a keyword-search / all-dump fallback.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple


@dataclass
class _Embedded:
    """Internal: a piece of text with its cached embedding."""
    text: str
    metadata: dict
    vector: List[float]


class SemanticMemory:
    """Tiny in-memory vector store. No external deps."""

    def __init__(self, client, embedding_model: str):
        self.client = client
        self.model = embedding_model
        self._store: List[_Embedded] = []
        self._healthy = True  # becomes False after a failed embed

    # --- embedding ---

    def _embed(self, text: str) -> Optional[List[float]]:
        if not self._healthy:
            return None
        try:
            resp = self.client.embed(model=self.model, input=text)
            # ollama-python returns either .embeddings (list of list) or .embedding
            vecs = getattr(resp, "embeddings", None)
            if vecs and isinstance(vecs, list) and vecs and isinstance(vecs[0], list):
                return list(vecs[0])
            vec = getattr(resp, "embedding", None)
            if vec:
                return list(vec)
            # dict-style response fallback
            if isinstance(resp, dict):
                if resp.get("embeddings"):
                    return list(resp["embeddings"][0])
                if resp.get("embedding"):
                    return list(resp["embedding"])
        except Exception:
            self._healthy = False
        return None

    # --- public API ---

    def add(self, text: str, metadata: Optional[dict] = None) -> bool:
        """Embed `text` and store it. Returns True on success."""
        if not text.strip():
            return False
        vec = self._embed(text)
        if vec is None:
            return False
        self._store.append(_Embedded(text=text, metadata=metadata or {}, vector=vec))
        return True

    def add_many(self, items: Iterable[Tuple[str, dict]]) -> int:
        count = 0
        for text, meta in items:
            if self.add(text, meta):
                count += 1
        return count

    def search(self, query: str, top_k: int = 5) -> List[Tuple[float, _Embedded]]:
        """Return (score, entry) pairs, highest-similarity first."""
        if not self._store:
            return []
        qvec = self._embed(query)
        if qvec is None:
            return []
        scored = [(_cosine(qvec, entry.vector), entry) for entry in self._store]
        scored.sort(key=lambda p: p[0], reverse=True)
        return scored[:top_k]

    @property
    def size(self) -> int:
        return len(self._store)

    @property
    def healthy(self) -> bool:
        return self._healthy


def _cosine(a: List[float], b: List[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
