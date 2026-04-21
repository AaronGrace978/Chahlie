"""
Semantic memory retrieval for Chahlie.

Embeds learnings and session summaries via the configured Ollama embedding
model, then at prompt-build time retrieves the top-K most relevant entries
for the current user message instead of dumping the entire memory into the
context window.

Two backends, both implementing the same public API:
    - `SemanticMemory`          : in-process, zero-dep, wiped on restart
    - `PersistentSemanticMemory`: ChromaDB-backed, survives restarts

Use `get_semantic_store(client, model, project_root)` to pick the right
backend automatically. Falls back gracefully when `chromadb` isn't
importable or when persistence is disabled in config.

Callers should always have a keyword-search / all-dump fallback.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


@dataclass
class _Embedded:
    """Internal: a piece of text with its cached embedding."""
    text: str
    metadata: dict
    vector: List[float]


class SemanticMemory:
    """Tiny in-process vector store. No external deps."""

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
            vecs = getattr(resp, "embeddings", None)
            if vecs and isinstance(vecs, list) and vecs and isinstance(vecs[0], list):
                return list(vecs[0])
            vec = getattr(resp, "embedding", None)
            if vec:
                return list(vec)
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

    @property
    def backend_name(self) -> str:
        return "in-memory"


class PersistentSemanticMemory:
    """ChromaDB-backed persistent vector store.

    Stored under `<project_root>/.chahlie/vector_store/`. Uses the same
    Ollama embedding pipeline as SemanticMemory so the two are interchangeable
    at the API level - callers never need to know which backend they got.

    Construction can fail (chromadb missing, disk issue, etc.); callers
    should catch broadly and fall back to SemanticMemory.
    """

    COLLECTION_NAME = "chahlie_semantic"

    def __init__(self, client, embedding_model: str, project_root: Path):
        # Import inside __init__ so `import semantic` never crashes for users
        # who don't have chromadb installed.
        import chromadb
        from chromadb.config import Settings

        self.client = client
        self.model = embedding_model
        self._healthy = True

        store_dir = project_root / ".chahlie" / "vector_store"
        store_dir.mkdir(parents=True, exist_ok=True)

        self._chroma = chromadb.PersistentClient(
            path=str(store_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._chroma.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    # --- embedding (shared with in-memory backend) ---

    def _embed(self, text: str) -> Optional[List[float]]:
        if not self._healthy:
            return None
        try:
            resp = self.client.embed(model=self.model, input=text)
            vecs = getattr(resp, "embeddings", None)
            if vecs and isinstance(vecs, list) and vecs and isinstance(vecs[0], list):
                return list(vecs[0])
            vec = getattr(resp, "embedding", None)
            if vec:
                return list(vec)
            if isinstance(resp, dict):
                if resp.get("embeddings"):
                    return list(resp["embeddings"][0])
                if resp.get("embedding"):
                    return list(resp["embedding"])
        except Exception:
            self._healthy = False
        return None

    @staticmethod
    def _stable_id(text: str, metadata: dict) -> str:
        """Deterministic id so re-seeding the same learning is a no-op upsert."""
        payload = text + "||" + "|".join(f"{k}={v}" for k, v in sorted(metadata.items()))
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()

    # --- public API ---

    def add(self, text: str, metadata: Optional[dict] = None) -> bool:
        if not text.strip():
            return False
        vec = self._embed(text)
        if vec is None:
            return False
        meta = metadata or {}
        # Chroma rejects non-primitive metadata values; coerce to str.
        safe_meta = {k: (v if isinstance(v, (str, int, float, bool)) else str(v))
                     for k, v in meta.items()}
        try:
            self._collection.upsert(
                ids=[self._stable_id(text, meta)],
                embeddings=[vec],
                documents=[text],
                metadatas=[safe_meta] if safe_meta else None,
            )
            return True
        except Exception:
            self._healthy = False
            return False

    def add_many(self, items: Iterable[Tuple[str, dict]]) -> int:
        count = 0
        for text, meta in items:
            if self.add(text, meta):
                count += 1
        return count

    def search(self, query: str, top_k: int = 5) -> List[Tuple[float, _Embedded]]:
        if self.size == 0:
            return []
        qvec = self._embed(query)
        if qvec is None:
            return []
        try:
            res = self._collection.query(query_embeddings=[qvec], n_results=top_k)
        except Exception:
            self._healthy = False
            return []
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        # Chroma returns cosine DISTANCE (0 = identical). Convert to similarity.
        dists = (res.get("distances") or [[]])[0]
        out: List[Tuple[float, _Embedded]] = []
        for doc, meta, dist in zip(docs, metas, dists):
            score = 1.0 - float(dist)
            out.append((score, _Embedded(text=doc, metadata=meta or {}, vector=[])))
        return out

    @property
    def size(self) -> int:
        try:
            return int(self._collection.count())
        except Exception:
            return 0

    @property
    def healthy(self) -> bool:
        return self._healthy

    @property
    def backend_name(self) -> str:
        return "chromadb"


def get_semantic_store(
    client,
    embedding_model: str,
    project_root: Optional[Path] = None,
    *,
    prefer_persistent: bool = True,
):
    """Factory: prefer ChromaDB-backed storage, fall back to in-memory.

    Returns any object exposing `add`, `add_many`, `search`, `size`,
    `healthy`, `backend_name`. Callers don't need to care which backend.
    """
    if prefer_persistent and project_root is not None:
        try:
            return PersistentSemanticMemory(client, embedding_model, project_root)
        except Exception:
            # chromadb missing, disk issue, version mismatch, etc. - fall through.
            pass
    return SemanticMemory(client, embedding_model)


def _cosine(a: List[float], b: List[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
