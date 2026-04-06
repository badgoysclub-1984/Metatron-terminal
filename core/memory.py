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
    # ------------------------------------------------------------------
    def batch_add(self, entries: List[Dict[str, Any]], skip_save: bool = False):
        """Add multiple memories in a single pass (efficient for loading)."""
        texts = [e["text"] for e in entries]
        metas = [e.get("metadata", {}) for e in entries]
        
        if self.encoder is not None:
            embs = self.encoder.encode(texts, batch_size=32, show_progress_bar=False).astype(np.float32)
        else:
            embs = np.stack([_text_hash_vector(t, self.dim) for t in texts])

        if self.index is not None:
            self.index.add(embs)
            
        for emb, text, meta in zip(embs, texts, metas):
            self.memories.append((emb, text, meta))
            
        if self.persist_path and not skip_save:
            self._save(self.persist_path)

    def add(self, text: str, metadata: Dict[str, Any], skip_save: bool = False):
        emb = self._encode(text)
        if self.index is not None:
            self.index.add(np.array([emb], dtype=np.float32))
        self.memories.append((emb, text, metadata))
        if self.persist_path and not skip_save:
            self._save(self.persist_path)

    # ------------------------------------------------------------------
    def recall(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        if not self.memories:
            return []
        
        # Keyword search (high-priority exact matches)
        q_lower = query.lower()
        exact_results = []
        for i, (_, t, m) in enumerate(self.memories):
            if q_lower in t.lower():
                exact_results.append({"text": t, "metadata": m, "distance": 0.0, "index": i})
        
        if len(exact_results) >= k:
            return exact_results[:k]

        # Semantic search
        if self.index is not None and self.index.ntotal > 0:
            qemb = self._encode(query)
            # Search for more than k to filter out duplicates if needed
            D, I = self.index.search(np.array([qemb], dtype=np.float32), min(k * 2, self.index.ntotal))
            results = list(exact_results)
            seen_indices = {r["index"] for r in exact_results}
            
            for dist, idx in zip(D[0], I[0]):
                if idx >= 0 and idx not in seen_indices:
                    _, text, meta = self.memories[idx]
                    results.append({"text": text, "metadata": meta, "distance": float(dist), "index": int(idx)})
                    seen_indices.add(idx)
                    if len(results) >= k:
                        break
            return results
        
        return exact_results[:k]

    # ------------------------------------------------------------------
    def _save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        # Only save text and metadata, embeddings are recomputed on load or handled by FAISS
        data = [{"text": t, "metadata": m} for _, t, m in self.memories]
        path.write_text(json.dumps(data, indent=2))

    def _load(self, path: Path):
        try:
            # Clear current state before loading
            self.memories = []
            if self.index is not None:
                self.index.reset()
                
            raw_text = path.read_text()
            if not raw_text.strip():
                return
            data = json.loads(raw_text)
            print(f"[VectorMemory] Loading {len(data)} entries via batch_add...")
            self.batch_add(data, skip_save=True)
        except Exception as exc:
            print(f"[VectorMemory] Warning: could not load memories: {exc}")

    def __len__(self) -> int:
        return len(self.memories)
