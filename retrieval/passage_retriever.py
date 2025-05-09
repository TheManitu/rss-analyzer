from datetime import date
import faiss
import re
from sentence_transformers import SentenceTransformer
from config import (
    EMBEDDING_MODEL,
    RETRIEVAL_CANDIDATES,
    HYBRID_WEIGHT_SEMANTIC,
    IMPORTANCE_WEIGHT,
    RECENCY_WEIGHT
)

class PassageRetriever:
    def __init__(self, storage_client):
        self.storage = storage_client
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)

    def _split_passages(self, text: str) -> list:
        return [p.strip() for p in text.split("\n") if len(p.split()) > 10]

    def _get_all_relevant_articles(self, query_terms: list) -> list:
        all_articles = self.storage.fetch_passages()
        matching_articles = []

        for article in all_articles:
            title = (article.get("title") or "").lower()
            content = (article.get("content") or "").lower()
            if any(term in title or term in content for term in query_terms):
                matching_articles.append(article)
                continue

            keywords = self.storage.get_article_keywords(article["link"])
            keywords_lower = {k.lower() for k in keywords}
            if any(any(term in k for k in keywords_lower) for term in query_terms):
                matching_articles.append(article)

        return matching_articles or all_articles  # Fallback auf alle

    def retrieve(self, query: str) -> list:
        query_terms = re.findall(r"\b\w{3,}\b", query.lower(), flags=re.UNICODE)
        today = date.today()

        # 1. Artikel finden, die irgendwo passen
        articles = self._get_all_relevant_articles(query_terms)

        # 2. Passagen extrahieren
        passages = []
        for a in articles:
            content = a.get("summary") or a.get("content", "")
            for p in self._split_passages(content):
                passages.append({
                    "text": p,
                    "title": a["title"],
                    "link": a["link"],
                    "importance": a.get("importance", 0),
                    "recency": max(0.0, (14 - (today - a.get("published", today)).days) / 14)
                })

        if not passages:
            return []

        # 3. Semantische Bewertung
        texts = [p["text"] for p in passages]
        doc_emb = self.embedder.encode(texts, normalize_embeddings=True)
        q_emb   = self.embedder.encode([query], normalize_embeddings=True)
        idx     = faiss.IndexFlatIP(doc_emb.shape[1])
        idx.add(doc_emb)
        dists, _ = idx.search(q_emb, len(texts))
        scores = dists[0]

        max_imp = max((p["importance"] for p in passages), default=1.0)
        results = []
        for i, s in enumerate(scores):
            total = (
                HYBRID_WEIGHT_SEMANTIC * s +
                IMPORTANCE_WEIGHT * (passages[i]["importance"] / max_imp) +
                RECENCY_WEIGHT * passages[i]["recency"]
            )
            results.append({
                "text": passages[i]["text"],
                "title": passages[i]["title"],
                "link": passages[i]["link"],
                "score": round(total, 3)
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:RETRIEVAL_CANDIDATES]
