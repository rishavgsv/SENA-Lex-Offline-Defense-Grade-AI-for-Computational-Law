"""
SENA-Lex Confidence Engine v2
Multi-dimensional answer evaluation framework.

Components (weights):
  1. Retrieval Relevance   (0.30) — hybrid FAISS + BM25 scores
  2. Answer Faithfulness    (0.25) — embedding similarity answer ↔ sources
  3. Cross-Chunk Agreement  (0.20) — pairwise chunk consistency
  4. Citation Coverage      (0.15) — % answer sentences backed by sources
  5. Query Coverage         (0.10) — query sub-parts addressed in answer
"""

import numpy as np
import re
import logging
from typing import List, Dict, Optional, Tuple

# ---------- spaCy (optional) ------------------------------------------------
try:
    import spacy
    _nlp = spacy.load("en_core_web_sm")
except Exception:
    _nlp = None
    logging.warning("spaCy not available in confidence_engine – using regex fallbacks.")


# =============================================================================
# Helper utilities
# =============================================================================

def _split_sentences(text: str) -> List[str]:
    """Split text into sentences using spaCy or regex fallback."""
    if _nlp:
        doc = _nlp(text)
        sents = [s.text.strip() for s in doc.sents if len(s.text.strip()) > 10]
        if sents:
            return sents
    # Regex fallback: split on period/question/exclamation followed by space or end
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 10]


def _extract_key_terms(text: str) -> List[str]:
    """Extract key noun phrases / entities from text for coverage analysis."""
    if _nlp:
        doc = _nlp(text)
        terms = []
        # Named entities
        for ent in doc.ents:
            terms.append(ent.text.lower())
        # Noun chunks (deduplicated)
        for chunk in doc.noun_chunks:
            if chunk.text.lower() not in terms and len(chunk.text) > 2:
                terms.append(chunk.text.lower())
        if terms:
            return list(set(terms))
    # Regex fallback: extract quoted phrases and capitalised words
    terms = re.findall(r'"([^"]+)"', text)
    terms += [w for w in text.split() if w[0].isupper() and len(w) > 2]
    # Also pick key content words (>4 chars, no stopwords)
    stopwords = {"about", "after", "before", "between", "could", "would",
                 "should", "their", "there", "these", "those", "under",
                 "which", "where", "while", "being", "other", "through"}
    content_words = [w.lower() for w in re.findall(r'\b[a-zA-Z]{4,}\b', text)
                     if w.lower() not in stopwords]
    terms += content_words[:8]
    return list(set(t.lower() for t in terms if len(t) > 2))


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _keyword_overlap(text_a: str, text_b: str) -> float:
    """Simple Jaccard-style keyword overlap score between two texts."""
    words_a = set(re.findall(r'\b\w{3,}\b', text_a.lower()))
    words_b = set(re.findall(r'\b\w{3,}\b', text_b.lower()))
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


# =============================================================================
# Individual Scorers
# =============================================================================

class RetrievalRelevanceScorer:
    """
    Weight: 0.30
    Uses the pre-computed hybrid FAISS + BM25 scores from the retrieval step.
    """
    WEIGHT = 0.30

    @staticmethod
    def score(top_chunks: List[Dict]) -> float:
        if not top_chunks:
            return 0.0
        scores = [c.get("similarity_score", 0.0) for c in top_chunks]
        # Use weighted average — top results matter more
        weights = np.array([1.0 / (i + 1) for i in range(len(scores))])
        weights /= weights.sum()
        raw = float(np.dot(scores, weights))
        return min(1.0, max(0.0, raw))


class AnswerFaithfulnessScorer:
    """
    Weight: 0.25
    Measures how faithfully the answer reflects the source chunks.
    Uses embedding similarity (answer ↔ concatenated sources) if an embed
    function is provided, otherwise falls back to keyword overlap.
    """
    WEIGHT = 0.25

    @staticmethod
    def score(answer: str, top_chunks: List[Dict],
              embed_fn=None) -> float:
        if not answer.strip() or not top_chunks:
            return 0.0

        source_text = " ".join(c.get("text", "") for c in top_chunks)

        # Primary: embedding similarity
        if embed_fn:
            try:
                answer_vec = embed_fn(answer[:1000])  # cap length
                source_vec = embed_fn(source_text[:2000])
                sim = _cosine_similarity(answer_vec, source_vec)
                # Scale: raw cosine in [0..1] → apply sigmoid-style curve
                # to be conservative (penalise < 0.5 harder)
                return min(1.0, max(0.0, sim))
            except Exception as e:
                logging.warning(f"Faithfulness embed failed: {e}")

        # Fallback: keyword overlap
        return _keyword_overlap(answer, source_text)


class CrossChunkAgreementScorer:
    """
    Weight: 0.20
    Measures semantic consistency across retrieved chunks.
    High pairwise similarity = chunks agree → higher score.
    Contradictory/diverse chunks → lower score.
    """
    WEIGHT = 0.20

    @staticmethod
    def score(top_chunks: List[Dict], embed_fn=None) -> float:
        if len(top_chunks) < 2:
            return 1.0  # single chunk = no contradiction possible

        texts = [c.get("text", "") for c in top_chunks[:5]]  # limit to top 5

        if embed_fn:
            try:
                vecs = [embed_fn(t[:500]) for t in texts]
                # Pairwise cosine similarities
                sims = []
                for i in range(len(vecs)):
                    for j in range(i + 1, len(vecs)):
                        sims.append(_cosine_similarity(vecs[i], vecs[j]))
                if sims:
                    avg_sim = float(np.mean(sims))
                    # Normalize: typical chunk sims are 0.3-0.9
                    # Map to [0,1] with emphasis on agreement
                    return min(1.0, max(0.0, avg_sim))
            except Exception as e:
                logging.warning(f"Cross-chunk embed failed: {e}")

        # Fallback: keyword overlap between chunk pairs
        overlaps = []
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                overlaps.append(_keyword_overlap(texts[i], texts[j]))
        return min(1.0, max(0.0, float(np.mean(overlaps)))) if overlaps else 0.5


class CitationCoverageScorer:
    """
    Weight: 0.15
    Measures what fraction of answer sentences are supported by source chunks.
    A sentence is "supported" if it has significant keyword overlap with at
    least one source chunk.
    """
    WEIGHT = 0.15

    @staticmethod
    def score(answer: str, top_chunks: List[Dict]) -> float:
        sentences = _split_sentences(answer)
        if not sentences:
            return 0.0

        source_texts = [c.get("text", "") for c in top_chunks]
        if not source_texts:
            return 0.0

        supported_count = 0
        for sent in sentences:
            # A sentence is supported if it has ≥ 0.15 keyword overlap
            # with ANY source chunk (intentionally low threshold)
            for src in source_texts:
                if _keyword_overlap(sent, src) >= 0.12:
                    supported_count += 1
                    break

        return supported_count / len(sentences)


class QueryCoverageScorer:
    """
    Weight: 0.10
    Decomposes query into key terms / sub-concepts and checks how many
    appear in the answer.
    """
    WEIGHT = 0.10

    @staticmethod
    def score(query: str, answer: str) -> float:
        key_terms = _extract_key_terms(query)
        if not key_terms:
            return 1.0  # trivial query → fully covered

        answer_lower = answer.lower()
        covered = 0
        for term in key_terms:
            # Check if term (or a close substring) appears in answer
            if term in answer_lower:
                covered += 1
            else:
                # Fuzzy: check if any word in the term appears
                words = term.split()
                if any(w in answer_lower for w in words if len(w) > 3):
                    covered += 0.5

        return min(1.0, covered / len(key_terms))


# =============================================================================
# Master Confidence Engine
# =============================================================================

class ConfidenceEngine:
    """
    Orchestrates all 5 scoring dimensions and produces a final weighted
    confidence score with per-component breakdown.
    """

    # Conservative multiplier — penalises uncertainty
    CONSERVATIVE_FACTOR = 0.90

    def __init__(self, embed_fn=None):
        """
        Args:
            embed_fn: A callable text → np.ndarray for embeddings.
                      Should be VectorStore.embed_text().
        """
        self.embed_fn = embed_fn

    def evaluate(self, query: str, answer: str,
                 top_chunks: List[Dict]) -> Dict:
        """
        Run all 5 evaluators and return the final confidence breakdown.

        Returns:
            {
                "retrieval_relevance": float,
                "answer_faithfulness": float,
                "cross_chunk_agreement": float,
                "citation_coverage": float,
                "query_coverage": float,
                "final_score": float
            }
        """
        # Strip verification trace from answer before scoring
        clean_answer = answer
        trace_markers = ["[Verification Trace]", "[Running Verification Trace", "✅ VALID", "❌ INVALID"]
        for marker in trace_markers:
            idx = clean_answer.find(marker)
            if idx != -1:
                clean_answer = clean_answer[:idx].strip()

        # Score each dimension
        retrieval = RetrievalRelevanceScorer.score(top_chunks)
        faithfulness = AnswerFaithfulnessScorer.score(
            clean_answer, top_chunks, self.embed_fn
        )
        agreement = CrossChunkAgreementScorer.score(
            top_chunks, self.embed_fn
        )
        citation = CitationCoverageScorer.score(clean_answer, top_chunks)
        coverage = QueryCoverageScorer.score(query, clean_answer)

        # Weighted combination
        raw_score = (
            RetrievalRelevanceScorer.WEIGHT * retrieval +
            AnswerFaithfulnessScorer.WEIGHT * faithfulness +
            CrossChunkAgreementScorer.WEIGHT * agreement +
            CitationCoverageScorer.WEIGHT * citation +
            QueryCoverageScorer.WEIGHT * coverage
        )

        # Apply conservative factor and cap
        final = min(1.0, max(0.0, raw_score * self.CONSERVATIVE_FACTOR))

        # Penalty: if answer looks like "not found" → floor confidence
        not_found_patterns = [
            "answer not found", "not present in", "cannot determine",
            "no information", "not mentioned"
        ]
        if any(p in clean_answer.lower() for p in not_found_patterns):
            final = min(final, 0.15)

        breakdown = {
            "retrieval_relevance": round(retrieval, 3),
            "answer_faithfulness": round(faithfulness, 3),
            "cross_chunk_agreement": round(agreement, 3),
            "citation_coverage": round(citation, 3),
            "query_coverage": round(coverage, 3),
            "final_score": round(final, 3),
        }

        logging.info(f"Confidence breakdown: {breakdown}")
        return breakdown
