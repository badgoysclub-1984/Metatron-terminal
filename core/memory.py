#!/usr/bin/env python3
"""
METATRON OS — core/memory.py
Persistent Vector Memory (FAISS + sentence-transformers, with graceful fallback)
"""

import json
import hashlib
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from sentence_transformers import SentenceTransformer
    HAS_ST = True
except ImportError:
    HAS_ST = False

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

EMBED_DIM = 384          # all-MiniLM-L6-v2 output dimension
FALLBACK_DIM = 64        # hash-based fallback dimension


def _text_hash_vector(text: str, dim: int = FALLBACK_DIM) -> np.ndarray:
    """Deterministic pseudo-embedding from text hash (fallback when no ST)."""
    digest = hashlib.sha256(text.encode()).digest()
    arr = np.frombuffer(digest, dtype=np.uint8).astype(np.float32)
    # Tile/trim to dim
    repeats = (dim // len(arr)) + 1
    arr = np.tile(arr, repeats)[:dim]
    norm = np.linalg.norm(arr)
    return arr / (norm + 1e-8)


class VectorMemory:
    """
    Semantic memory store backed by FAISS + sentence-transformers.
    Falls back to keyword search + hash embeddings when libraries absent.
    """

    def __init__(self, dim: int = EMBED_DIM, persist_path: Optional[Path] = None):
        self.dim = dim if HAS_ST else FALLBACK_DIM
        self.persist_path = persist_path
        self.memories: List[Tuple[Optional[np.ndarray], str, Dict[str, Any]]] = []
        self.index: Optional[Any] = None

        if HAS_ST:
            self.encoder = SentenceTransformer("all-MiniLM-L6-v2")
        else:
            self.encoder = None

        if HAS_FAISS:
            self.index = faiss.IndexFlatL2(self.dim)

        if persist_path and persist_path.exists():
            self._load(persist_path)

    # ------------------------------------------------------------------
    def _encode(self, text: str) -> np.ndarray:
        if self.encoder is not None:
            return self.encoder.encode([text])[0].astype(np.float32)
        return _text_hash_vector(text, self.dim)

    # ------------------------------------------------------------------
    def add(self, text: str, metadata: Dict[str, Any]):
        emb = self._encode(text)
        if self.index is not None:
            self.index.add(np.array([emb], dtype=np.float32))
        self.memories.append((emb, text, metadata))
        if self.persist_path:
            self._save(self.persist_path)

    # ------------------------------------------------------------------
    def recall(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        if not self.memories:
            return []
        if self.index is not None and self.index.ntotal > 0:
            qemb = self._encode(query)
            D, I = self.index.search(np.array([qemb], dtype=np.float32), min(k, self.index.ntotal))
            results = []
            for dist, idx in zip(D[0], I[0]):
                if idx >= 0:
                    _, text, meta = self.memories[idx]
                    results.append({"text": text, "metadata": meta, "distance": float(dist)})
            return results
        # Keyword fallback
        q_lower = query.lower()
        return [
            {"text": t, "metadata": m}
            for _, t, m in self.memories
            if q_lower in t.lower()
        ][:k]

    # ------------------------------------------------------------------
    def _save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [{"text": t, "metadata": m} for _, t, m in self.memories]
        path.write_text(json.dumps(data, indent=2))

    def _load(self, path: Path):
        try:
            data = json.loads(path.read_text())
            for entry in data:
                self.add(entry["text"], entry.get("metadata", {}))
        except Exception as exc:
            print(f"[VectorMemory] Warning: could not load memories: {exc}")

    def __len__(self) -> int:
        return len(self.memories)
