import numpy as np
import faiss
import requests
import hashlib
import logging
import os
import json
from typing import List, Dict
import re
import concurrent.futures
import threading
from rank_bm25 import BM25Okapi

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = "nomic-embed-text"
FALLBACK_DIM = 512   # dimension used by the local TF-IDF fallback


# ---------------------------------------------------------------------------
# Lightweight local fallback embedder (no GPU / no Ollama required)
# Uses a fixed random projection of a simple bag-of-words vector so that
# semantically-similar texts land near each other in the projected space.
# This is purely for offline functionality; Ollama gives better results.
# ---------------------------------------------------------------------------

class _LocalFallbackEmbedder:
    """Deterministic random-projection BoW embedder – always works offline."""

    VOCAB_SIZE = 65536  # hash buckets

    def __init__(self, dim: int = FALLBACK_DIM):
        rng = np.random.default_rng(42)  # fixed seed → reproducible
        self._proj = rng.standard_normal((self.VOCAB_SIZE, dim)).astype("float32")
        # L2-normalise each row so dot-product ≈ cosine similarity
        norms = np.linalg.norm(self._proj, axis=1, keepdims=True) + 1e-9
        self._proj /= norms
        self.dim = dim

    def embed(self, text: str) -> np.ndarray:
        tokens = text.lower().split()
        vec = np.zeros(self.VOCAB_SIZE, dtype="float32")
        for token in tokens:
            idx = int(hashlib.md5(token.encode()).hexdigest(), 16) % self.VOCAB_SIZE
            vec[idx] += 1.0
        # Project to lower dimension
        result = vec @ self._proj           # shape: (dim,)
        norm = np.linalg.norm(result) + 1e-9
        return (result / norm).astype("float32")


_fallback_embedder = _LocalFallbackEmbedder(FALLBACK_DIM)


class VectorStore:
    def __init__(self, persist_dir: str = "data"):
        self.persist_dir = persist_dir
        self.index_path = os.path.join(persist_dir, "index.faiss")
        self.meta_path = os.path.join(persist_dir, "metadata.json")
        self.embeddings_path = os.path.join(persist_dir, "embeddings.npy")
        self.index = None
        self.bm25 = None
        self.metadata: List[Dict] = []
        self._embeddings: List[np.ndarray] = []  # cached embeddings for fast rebuild
        self.dim = FALLBACK_DIM
        self._ollama_available = self._check_embed_model()
        self.load_local()

    def _build_bm25(self):
        """Rebuilds the BM25 index from tokenized metadata texts."""
        if not self.metadata:
            self.bm25 = None
            return
        tokenized_corpus = [re.findall(r'\w+', doc["text"].lower()) for doc in self.metadata]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def _check_embed_model(self) -> bool:
        """Returns True if Ollama + the embedding model are reachable."""
        try:
            r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
            if r.status_code == 200:
                models = [m["name"].split(":")[0] for m in r.json().get("models", [])]
                if EMBED_MODEL in models:
                    logging.info(f"Ollama embedding model '{EMBED_MODEL}' ready.")
                    return True
                else:
                    logging.warning(
                        f"Embedding model '{EMBED_MODEL}' not found in Ollama. "
                        f"Run:  ollama pull {EMBED_MODEL}  –– falling back to local embedder."
                    )
        except Exception as e:
            logging.warning(f"Cannot reach Ollama ({e}). Using local fallback embedder.")
        return False

    def _embed_ollama(self, text: str) -> np.ndarray | None:
        """Try to get an embedding from Ollama. Returns None on failure."""
        try:
            r = requests.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text},
                timeout=30,
            )
            if r.status_code == 200:
                vec = np.array(r.json()["embedding"], dtype="float32")
                return vec
        except Exception as e:
            logging.warning(f"Ollama embedding call failed: {e}")
        return None

    def _embed(self, text: str) -> np.ndarray:
        """
        Get an embedding vector. Tries Ollama first; falls back to the local
        BoW projector if Ollama is unreachable or returns an error.
        """
        if self._ollama_available:
            vec = self._embed_ollama(text)
            if vec is not None:
                # Update dim if needed (first call sets the real Ollama dim)
                if self.index is None:
                    self.dim = len(vec)
                return vec
            # Ollama failed mid-session – switch to fallback for this call
            logging.warning("Ollama unreachable mid-session; using local fallback for this chunk.")

        # ── local fallback ──────────────────────────────────────────────────
        # If we already have an index built with Ollama dimensions we can't
        # mix in a different-dimension vector, so we pad/truncate to match.
        fb_vec = _fallback_embedder.embed(text)
        if self.index is not None and self.dim != FALLBACK_DIM:
            # Pad or truncate to match existing index dimension
            if FALLBACK_DIM < self.dim:
                fb_vec = np.pad(fb_vec, (0, self.dim - FALLBACK_DIM))
            else:
                fb_vec = fb_vec[: self.dim]
        return fb_vec

    def embed_text(self, text: str):
        """Public API for embedding text. Used by ConfidenceEngine."""
        return self._embed(text)

    def add_chunks(self, chunks: List[Dict], progress_callback=None):
        if not chunks:
            return

        total_chunks = len(chunks)
        embeddings = [None] * total_chunks
        
        progress_lock = threading.Lock()
        completed = 0

        def process_chunk(idx, chunk):
            nonlocal completed
            vec = self._embed(chunk["text"])
            embeddings[idx] = vec
            if progress_callback:
                with progress_lock:
                    completed += 1
                    progress_callback(completed, total_chunks)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_chunk, i, chunk) for i, chunk in enumerate(chunks)]
            concurrent.futures.wait(futures)

        # On the very first chunk set the actual dimension
        if self.index is None and len(embeddings) > 0 and embeddings[0] is not None:
            self.dim = len(embeddings[0])

        embeddings_np = np.stack(embeddings).astype("float32")

        if self.index is None:
            self.index = faiss.IndexFlatL2(self.dim)

        self.index.add(embeddings_np)
        self.metadata.extend(chunks)
        self._embeddings.extend(embeddings)  # cache for fast rebuild on delete
        self._build_bm25()
        logging.info(f"Indexed {len(chunks)} chunks. Total stored: {len(self.metadata)}")
        self.save_local()

    def remove_document(self, filename: str) -> int:
        """Remove all chunks belonging to a document and rebuild the index.
        Returns the number of chunks removed."""
        before = len(self.metadata)
        # Build keep-mask
        keep_indices = [i for i, c in enumerate(self.metadata) if c.get("document") != filename]
        removed = before - len(keep_indices)

        if removed == 0:
            return 0

        # Determine the chunks we are KEEPING
        kept_meta = [self.metadata[i] for i in keep_indices]

        if not kept_meta:
            # All documents removed — wipe everything
            self.metadata = []
            self._embeddings = []
            self.index = None
            self._build_bm25()
            self.save_local()
            logging.info(f"Removed all chunks for '{filename}'. Index is now empty.")
            return removed

        # If the embeddings cache is in sync, slice it directly (fast path)
        if len(self._embeddings) == before:
            kept_embeddings = [self._embeddings[i] for i in keep_indices]
        else:
            # Cache missing or stale — re-embed only the KEPT chunks (lazy, cheaper than all)
            logging.warning(
                f"Embedding cache missing/stale ({len(self._embeddings)} vs {before}). "
                "Re-embedding kept chunks only (this may take a moment)..."
            )
            kept_embeddings = [None] * len(kept_meta)
            def embed_kept(idx, chunk):
                kept_embeddings[idx] = self._embed(chunk["text"])
                
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(embed_kept, i, chunk) for i, chunk in enumerate(kept_meta)]
                concurrent.futures.wait(futures)

        # Commit
        self.metadata = kept_meta
        self._embeddings = kept_embeddings

        # Rebuild FAISS index
        embeddings_np = np.stack(self._embeddings).astype("float32")
        self.index = faiss.IndexFlatL2(self.dim)
        self.index.add(embeddings_np)
        self._build_bm25()
        self.save_local()
        logging.info(f"Removed {removed} chunks for '{filename}'. {len(self.metadata)} chunks remain.")
        return removed

    def save_local(self):
        os.makedirs(self.persist_dir, exist_ok=True)
        if self.index is not None:
            faiss.write_index(self.index, self.index_path)
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump({"dim": self.dim, "metadata": self.metadata}, f)
            # Save cached embeddings for fast rebuild on next load
            if self._embeddings and len(self._embeddings) == len(self.metadata):
                embeddings_np = np.stack(self._embeddings).astype("float32")
                np.save(self.embeddings_path, embeddings_np)
            elif os.path.exists(self.embeddings_path):
                # Cache length mismatch – remove stale cache so it gets rebuilt on next load
                os.remove(self.embeddings_path)
                logging.warning("Embedding cache length mismatch – deleted stale cache file.")
            logging.info(f"Saved FAISS index to {self.persist_dir}")
        else:
            # Index is empty (all documents deleted) — remove stale persistence files
            for path in [self.index_path, self.meta_path, self.embeddings_path]:
                if os.path.exists(path):
                    os.remove(path)
            logging.info(f"Cleared persisted index from {self.persist_dir}")

    def load_local(self):
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.metadata = data.get("metadata", [])
                    self.dim = data.get("dim", len(self.metadata[0]["text"]) if self.metadata else FALLBACK_DIM)
                # Load cached embeddings if available and length matches
                if os.path.exists(self.embeddings_path):
                    embeddings_np = np.load(self.embeddings_path)
                    if len(embeddings_np) == len(self.metadata):
                        self._embeddings = list(embeddings_np)
                        logging.info(f"Loaded cached embeddings ({len(self._embeddings)} vectors).")
                    else:
                        # Length mismatch — discard stale cache; will rebuild lazily on first delete
                        logging.warning(
                            f"Embedding cache length mismatch ({len(embeddings_np)} vs "
                            f"{len(self.metadata)} chunks). Cache will be rebuilt on next delete."
                        )
                        self._embeddings = []
                        if os.path.exists(self.embeddings_path):
                            os.remove(self.embeddings_path)
                else:
                    # No cached embeddings — will be rebuilt lazily on first delete
                    logging.warning(
                        "No cached embeddings found. "
                        "They will be rebuilt from kept chunks on the next delete operation."
                    )
                    self._embeddings = []
                self._build_bm25()
                logging.info(f"Loaded FAISS index from {self.persist_dir} (total vectors: {len(self.metadata)})")
            except Exception as e:
                logging.error(f"Failed to load local index: {e}")

    def search(self, query: str, top_k: int = 5, document_filter: str = None) -> List[Dict]:
        if self.index is None or len(self.metadata) == 0:
            return []

        query_vec = self._embed(query).reshape(1, -1)

        # 1. FAISS search over ALL chunks to avoid ignoring the filtered document
        k = len(self.metadata)
        faiss_distances, faiss_indices = self.index.search(query_vec, k)
        
        faiss_scores = {}
        for dist, idx in zip(faiss_distances[0], faiss_indices[0]):
            if idx != -1:
                # Convert L2 distance → 0-1 similarity score
                # Less aggressive penalty for L2 distance to slightly boost baseline confidence
                faiss_scores[idx] = float(1.0 / (1.0 + (dist / 2.0)))

        # 2. BM25 scores (calculate raw scores first)
        bm25_raw = {}
        if self.bm25:
            tokenized_query = re.findall(r'\w+', query.lower())
            scores = self.bm25.get_scores(tokenized_query)
            for i, score in enumerate(scores):
                bm25_raw[i] = score

        # 3. Filter chunks & Hybrid Scoring
        results = []
        for i, chunk_meta in enumerate(self.metadata):
            if document_filter and chunk_meta.get("document") != document_filter:
                continue
            
            results.append({
                "idx": i,
                "chunk": chunk_meta,
                "f_raw": faiss_scores.get(i, 0.0),
                "b_raw": bm25_raw.get(i, 0.0)
            })

        if not results:
            return []

        # 4. Normalize BM25 dynamically *after* filtering
        max_b = max((r["b_raw"] for r in results), default=0.0)
        if max_b <= 0:
            max_b = 1.0

        final_chunks = []
        for r in results:
            f_score = r["f_raw"]
            b_score = r["b_raw"] / max_b
            
            # Combine scores where Final Score = (0.7 * FAISS) + (0.3 * BM25)
            # Only include chunks that were found by either FAISS or BM25
            if f_score > 0 or b_score > 0:
                base_hybrid = (0.7 * f_score) + (0.3 * b_score)
                # Apply a slight curve to boost confidence for good matches
                hybrid_score = min(1.0, base_hybrid * 1.25)
                
                chunk = r["chunk"].copy()
                chunk["similarity_score"] = hybrid_score
                chunk["faiss_score"] = f_score
                chunk["bm25_score"] = b_score
                final_chunks.append(chunk)

        # Sort by hybrid score descending and return top_k
        final_chunks.sort(key=lambda x: x["similarity_score"], reverse=True)
        return final_chunks[:top_k]
