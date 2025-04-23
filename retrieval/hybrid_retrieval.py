"""
Hybride Suche: semantische Vektorsuche (FAISS) + BM25 (rank_bm25), Fusion der Ergebnisse.
"""
from sentence_transformers import SentenceTransformer
import faiss
from rank_bm25 import BM25Okapi
from config import (
    EMBEDDING_MODEL,
    TOP_K_VECTORIZATION,
    TOP_K_BM25,
    HYBRID_WEIGHT_SEMANTIC,
    HYBRID_WEIGHT_KEYWORD,
    MAX_CONTEXTS,
)

class HybridRetrieval:
    def __init__(self, storage_client):
        self.storage  = storage_client
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)

    def retrieve(self, query: str) -> list:
        """
        Führt eine hybride Suche durch und liefert die TOP MAX_CONTEXTS Kandidatenpassagen,
        sortiert nach Hybrid-Score.
        :param query: Die Nutzerfrage
        :return: Liste von Dicts mit 'id','title','text','link','score'
        """
        # 1) Hole alle Passagen
        passages = self.storage.fetch_passages()
        texts    = [p.get('text', p.get('content', '')) for p in passages]
        if not passages:
            return []

        # 2) Semantische Suche via FAISS
        doc_emb = self.embedder.encode(texts, normalize_embeddings=True)
        q_emb   = self.embedder.encode([query], normalize_embeddings=True)
        dim     = doc_emb.shape[1]
        index   = faiss.IndexFlatIP(dim)
        index.add(doc_emb)
        distances, indices = index.search(q_emb, TOP_K_VECTORIZATION)
        sem_scores = distances[0]
        sem_idxs   = indices[0]

        # 3) BM25‑Suche
        tokenized   = [t.split() for t in texts]
        bm25        = BM25Okapi(tokenized)
        raw_scores  = bm25.get_scores(query.split())
        max_bm      = max(raw_scores) if max(raw_scores) > 0 else 1.0
        bm25_scores = [s / max_bm for s in raw_scores]

        # 4) Score‑Fusion
        hybrid = []
        for idx in range(len(passages)):
            # sem_score nur, wenn idx unter den TOP_K_VECTORIZATION war
            sem = float(sem_scores[list(sem_idxs).index(idx)]) if idx in sem_idxs else 0.0
            kw  = bm25_scores[idx]
            score = HYBRID_WEIGHT_SEMANTIC * sem + HYBRID_WEIGHT_KEYWORD * kw
            hybrid.append((idx, score))

        # 5) Sortiere und picke Top MAX_CONTEXTS
        hybrid.sort(key=lambda x: x[1], reverse=True)
        selected = []
        for idx, score in hybrid[:MAX_CONTEXTS]:
            # Kopie, damit original nicht verändert wird
            ctx = passages[idx].copy()
            ctx['score'] = score
            selected.append(ctx)

        return selected
