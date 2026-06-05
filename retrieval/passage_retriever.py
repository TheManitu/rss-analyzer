# retrieval/passage_retriever.py

from datetime import date, datetime
import logging
import re

try:
    import faiss
except Exception:  # pragma: no cover - optional runtime dependency guard
    faiss = None

try:
    import torch
except Exception:  # pragma: no cover - optional runtime dependency guard
    torch = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional runtime dependency guard
    SentenceTransformer = None

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
from pipeline.text_quality import clean_article_text, is_useful_article_text

logger = logging.getLogger(__name__)

QUERY_STOPWORDS = {
    "was", "ist", "sind", "bei", "und", "oder", "der", "die", "das", "den", "dem",
    "des", "ein", "eine", "einer", "eines", "mit", "von", "zu", "zur", "zum", "im",
    "in", "am", "auf", "fuer", "für", "gibt", "neues", "aktuellen", "aktuelle",
    "wichtigsten", "passiert", "welche", "warum", "wie",
}

BROAD_MODEL_TERMS = {
    "ai", "ki", "ml", "gpt", "chat", "chats", "chatbot", "chatbots",
    "chatgpt", "openai", "model", "modell", "modelle",
    "projekt", "project", "projektname", "projektnamen", "projectname",
    "codename", "codenamen", "code", "name", "namen", "release", "features",
    "feature", "funktionen", "funktion", "informationen", "info", "infos", "hinweise",
    "stand", "quelle", "quellen",
}

VERSION_TERM_RE = re.compile(r"^(?:[a-z]+-)?\d+(?:\.\d+)+$")


def _keep_query_term(term: str) -> bool:
    return term not in QUERY_STOPWORDS and (len(term) > 2 or term in {"ai", "ki", "ml"})


def _query_base_terms(query: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:[-.][a-z0-9]+)*", (query or "").lower())


def required_query_terms(query: str) -> list[str]:
    required = []
    for term in _query_base_terms(query):
        if term in QUERY_STOPWORDS or term in BROAD_MODEL_TERMS:
            continue
        if VERSION_TERM_RE.match(term) or len(term) > 3:
            required.append(term)
    return list(dict.fromkeys(required))


def _compact_term(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def text_contains_term(text: str, term: str) -> bool:
    lowered = (text or "").lower()
    if term in lowered:
        return True
    compact_text = _compact_term(lowered)
    compact_term = _compact_term(term)
    return bool(compact_term and compact_term in compact_text)


def text_contains_required_terms(text: str, terms: list[str]) -> bool:
    return all(text_contains_term(text, term) for term in terms)


def _diverse_by_link(results: list[dict], limit: int) -> list[dict]:
    unique = []
    duplicates = []
    seen = set()
    for result in results:
        link = result.get("link")
        if link in seen:
            duplicates.append(result)
            continue
        seen.add(link)
        unique.append(result)
        if len(unique) >= limit:
            return unique
    return (unique + duplicates)[:limit]


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
        device = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"
        self.embedder = None
        if SentenceTransformer is not None:
            try:
                self.embedder = SentenceTransformer(EMBEDDING_MODEL, device=device)
            except Exception as exc:
                logger.warning("Embedding-Modell nicht verfuegbar, nutze Keyword-Fallback: %s", exc)
        # GPU-Ressourcen für FAISS, falls verfügbar
        if faiss is not None and device == "cuda" and hasattr(faiss, "StandardGpuResources"):
            self.faiss_gpu_res = faiss.StandardGpuResources()
        else:
            self.faiss_gpu_res = None

    def _split_passages(self, text: str) -> list[str]:
        """Split Content in Passagen von mind. 10 Wörtern."""
        clean = clean_article_text(text)
        parts = [p.strip() for p in re.split(r"[\r\n]+|(?<=[.!?])\s+", clean) if p.strip()]
        passages = []
        current = []
        for part in parts:
            current.extend(part.split())
            if len(current) >= 80:
                chunk = " ".join(current)
                if is_useful_article_text(chunk, min_words=10):
                    passages.append(chunk)
                current = []
        if current:
            chunk = " ".join(current)
            if is_useful_article_text(chunk, min_words=10):
                passages.append(chunk)
        return passages

    @staticmethod
    def _as_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value[:10]).date()
            except Exception:
                return date.today()
        return date.today()

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
        kws = {kw.lower() for kw in (self.storage.get_article_keywords(art["link"]) or [])}
        summary_text = (art.get("summary") or "").lower()
        title_text = (art.get("title") or "").lower()
        hits = sum(
            1
            for term in query_terms
            if _keep_query_term(term) and (
                term in kws
                or any(term in kw for kw in kws)
                or term in summary_text
                or term in title_text
            )
        )
        return hits >= 2

    def _matches_required_terms(self, art: dict, required_terms: list[str]) -> bool:
        if not required_terms:
            return True
        kws = " ".join(self.storage.get_article_keywords(art["link"]) or [])
        searchable = " ".join(
            str(art.get(key) or "")
            for key in ("title", "summary", "description", "content", "translation", "topic")
        )
        return text_contains_required_terms(f"{searchable} {kws}", required_terms)

    def _keyword_rank(self, query_terms: list[str], passages: list[dict]) -> list[dict]:
        max_imp = max((p["importance"] for p in passages), default=1.0) or 1.0
        terms = [term for term in query_terms if _keep_query_term(term)]
        hit_counts = [
            sum(
                1
                for term in terms
                if term in f"{passage.get('title', '')} {passage.get('text', '')}".lower()
            )
            for passage in passages
        ]
        require_hits = bool(terms) and max(hit_counts, default=0) > 0
        results = []
        for passage, hits in zip(passages, hit_counts):
            if require_hits and hits == 0:
                continue
            semantic = hits / max(len(terms), 1)
            if passage.get("section_idx") == 0:
                semantic *= SUMMARY_BOOST
            imp_score = passage["importance"] / max_imp
            score = round(
                HYBRID_WEIGHT_SEMANTIC * semantic +
                IMPORTANCE_WEIGHT * imp_score +
                RECENCY_WEIGHT * passage["recency"],
                3
            )
            if score >= MIN_PASSTAGE_SCORE:
                entry = passage.copy()
                entry["score"] = score
                results.append(entry)
        results.sort(key=lambda x: x["score"], reverse=True)
        return _diverse_by_link(results, RETRIEVAL_CANDIDATES)

    def retrieve(self, query: str) -> list[dict]:
        today = date.today()
        topic = extract_topic_from_question(query)

        # 0) Artikel-Pool nach Topic einschränken
        if topic and topic != "Allgemein":
            all_articles = self.storage.get_articles_by_topic(topic)
            if not all_articles:
                all_articles = self.storage.get_all_articles()
        else:
            all_articles = self.storage.get_all_articles()
        if not all_articles:
            return []

        # 1) Query-Terms + Synonyme
        base_terms   = _query_base_terms(query)
        synonyms     = TOPIC_SYNONYMS.get(topic, [])
        query_terms  = [term for term in set(base_terms + synonyms) if _keep_query_term(term)]
        required_terms = required_query_terms(query)

        # 2) Keyword & Topic Filter
        filtered = [
            art for art in all_articles
            if self._matches(art, query_terms, topic) and self._matches_required_terms(art, required_terms)
        ]
        if USE_STRICT_KEYWORD_FILTER:
            # striktes Filtering ohne Fallback
            if not filtered:
                return []
        else:
            # fallback auf alle Artikel
            if not filtered:
                if required_terms:
                    return []
                filtered = all_articles

        # 3) Summary-Passagen sammeln
        passages = []
        for art in filtered:
            summary = art.get("summary") or ""
            summary = clean_article_text(summary)
            if len(summary.split()) >= 10 and is_useful_article_text(summary, min_words=10):
                days_old = (today - self._as_date(art.get("published", today))).days
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
                days_old = (today - self._as_date(art.get("published", today))).days
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

        if self.embedder is None or faiss is None:
            return self._keyword_rank(query_terms, passages)

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
        return _diverse_by_link(results, RETRIEVAL_CANDIDATES)
