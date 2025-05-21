# retrieval/passage_retriever.py

from datetime import date
import faiss
import re
import torch
from sentence_transformers import SentenceTransformer

from config import (
    EMBEDDING_MODEL,
    RETRIEVAL_CANDIDATES,
    HYBRID_WEIGHT_SEMANTIC,
    IMPORTANCE_WEIGHT,
    RECENCY_WEIGHT,
    MIN_PASSTAGE_SCORE,
    SUMMARY_BOOST,
    RECENCY_MAX_DAYS,
    USE_STRICT_KEYWORD_FILTER
)
from topic_config import TOPIC_SYNONYMS
from api.utils import extract_topic_from_question


class PassageRetriever:
    """
    Retrieval-Augmented Generation:
      1) Keyword- & Topic-Filter (mit Synonymen)
      2) Semantische Suche primär auf Summaries
      3) Fallback auf Content-Chunks, falls nicht genug Summary-Passagen
      4) FAISS (CPU/GPU)
      5) Hybrid-Scoring mit Summary-Boost
      6) Top-K Auswahl
    """
    def __init__(self, storage_client):
        self.storage = storage_client
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.embedder = SentenceTransformer(EMBEDDING_MODEL, device=device)
        # GPU-Ressourcen für FAISS, falls verfügbar
        if device == "cuda" and hasattr(faiss, "StandardGpuResources"):
            self.faiss_gpu_res = faiss.StandardGpuResources()
        else:
            self.faiss_gpu_res = None

    def _split_passages(self, text: str) -> list[str]:
        """Split Content in Passagen von mind. 10 Wörtern."""
        return [p.strip() for p in text.split("\n") if len(p.split()) > 10]

    def _matches(self, art: dict, query_terms: list[str], topic: str) -> bool:
        """
        True, wenn art.topic exakt topic ist
        oder mindestens 2 query_terms in Keywords oder Summary vorkommen.
        """
        # harter Topic-Match
        if topic and topic.lower() != "allgemein":
            if art.get("topic", "").lower() == topic.lower():
                return True
        # Keyword-Match
        kws = set(self.storage.get_article_keywords(art["link"]) or [])
        summary_text = (art.get("summary") or "").lower()
        hits = sum(
            1
            for term in query_terms
            if term in kws or term in summary_text
        )
        return hits >= 2

    def retrieve(self, query: str) -> list[dict]:
        today = date.today()
        topic = extract_topic_from_question(query)

        # 0) Artikel-Pool nach Topic einschränken
        if topic and topic != "Allgemein":
            all_articles = self.storage.get_articles_by_topic(topic)
        else:
            all_articles = self.storage.get_all_articles()
        if not all_articles:
            return []

        # 1) Query-Terms + Synonyme
        base_terms   = re.findall(r"\w+", query.lower())
        synonyms     = TOPIC_SYNONYMS.get(topic, [])
        query_terms  = list(set(base_terms + synonyms))

        # 2) Keyword & Topic Filter
        filtered = [
            art for art in all_articles
            if self._matches(art, query_terms, topic)
        ]
        if USE_STRICT_KEYWORD_FILTER:
            # striktes Filtering ohne Fallback
            if not filtered:
                return []
        else:
            # fallback auf alle Artikel
            if not filtered:
                filtered = all_articles

        # 3) Summary-Passagen sammeln
        passages = []
        for art in filtered:
            summary = art.get("summary") or ""
            if len(summary.split()) >= 10:
                days_old = (today - art.get("published", today)).days
                recency  = max(0.0, (RECENCY_MAX_DAYS - days_old) / RECENCY_MAX_DAYS)
                passages.append({
                    "text":            summary,
                    "title":           art.get("title", ""),
                    "link":            art["link"],
                    "section_idx":     0,
                    "section_keyword": (self.storage.get_article_keywords(art["link"]) or [""])[0],
                    "importance":      art.get("importance", 0.0),
                    "recency":         recency
                })

        # 4) Fallback: Content-Passagen, falls zu wenige Summaries
        if len(passages) < RETRIEVAL_CANDIDATES:
            for art in filtered:
                content = art.get("content", "") or ""
                days_old = (today - art.get("published", today)).days
                recency  = max(0.0, (RECENCY_MAX_DAYS - days_old) / RECENCY_MAX_DAYS)
                for idx, sec in enumerate(self._split_passages(content), start=1):
                    passages.append({
                        "text":            sec,
                        "title":           art.get("title", ""),
                        "link":            art["link"],
                        "section_idx":     idx,
                        "section_keyword": (self.storage.get_article_keywords(art["link"]) or [""])[0],
                        "importance":      art.get("importance", 0.0),
                        "recency":         recency
                    })

        if not passages:
            return []

        # 5) Embeddings + FAISS-Index (CPU/GPU)
        texts = [p["text"] for p in passages]
        doc_emb = self.embedder.encode(texts, normalize_embeddings=True)
        q_emb   = self.embedder.encode([query], normalize_embeddings=True)

        dim = doc_emb.shape[1]
        if self.faiss_gpu_res:
            cpu_index = faiss.IndexFlatIP(dim)
            index     = faiss.index_cpu_to_gpu(self.faiss_gpu_res, 0, cpu_index)
        else:
            index = faiss.IndexFlatIP(dim)
        index.add(doc_emb)
        sims, _ = index.search(q_emb, len(texts))
        sims = sims[0]

        # 6) Hybrid-Scoring mit Summary-Boost
        max_imp = max((p["importance"] for p in passages), default=1.0) or 1.0
        results = []
        for i, sim in enumerate(sims):
            # Boost für Summary-Passage
            if passages[i]["section_idx"] == 0:
                sim *= SUMMARY_BOOST

            imp_score = passages[i]["importance"] / max_imp
            score = round(
                HYBRID_WEIGHT_SEMANTIC * sim +
                IMPORTANCE_WEIGHT       * imp_score +
                RECENCY_WEIGHT          * passages[i]["recency"],
                3
            )
            if score >= MIN_PASSTAGE_SCORE:
                entry = passages[i].copy()
                entry["score"] = score
                results.append(entry)

        # 7) Sortierung & Top-K zurückgeben
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:RETRIEVAL_CANDIDATES]
