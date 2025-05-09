# evaluation/quality_evaluator.py

import numpy as np
import math
from datetime import datetime
from retrieval.content_filter import check_quality_flags
from storage.duckdb_storage import get_article_metadata
from sentence_transformers import SentenceTransformer

# Einmaliges Laden des Embedding-Modells
_embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def compute_embedding_similarity(text1: str, text2: str) -> float:
    """
    Cosinus-Ähnlichkeit zwischen zwei Texten über normalisierte Embeddings.
    """
    emb1 = _embedder.encode([text1], normalize_embeddings=True)[0]
    emb2 = _embedder.encode([text2], normalize_embeddings=True)[0]
    return float(np.dot(emb1, emb2))


def normalize(value: float, min_val: float, max_val: float) -> float:
    """
    Lineare Min–Max-Normalisierung auf [0,1].
    """
    if max_val == min_val:
        return 0.0
    return (value - min_val) / (max_val - min_val)


class QualityEvaluator:
    """
    Bewertet generierte Antworten nach Länge und Kontextzahl.
    """
    def __init__(self, threshold: float = 0.5):
        """
        :param threshold: Mindest-Qualität (0–1); wenn score < threshold, wird flag=True.
        """
        self.threshold = threshold

    def evaluate(self, answer: str, contexts: list) -> dict:
        """
        :param answer:   Generierte Antwort-Text
        :param contexts: Liste der verwendeten Artikel-Kontexte
        :return:         Dict mit 'score' (0–1) und 'flag' (bool)
        """
        words = answer.split()
        length_norm = min(len(words) / 200.0, 1.0)
        ctx_norm    = min(len(contexts) / 5.0,   1.0)
        # Gewichte: 70% Länge, 30% Kontext-Anzahl
        score = 0.7 * length_norm + 0.3 * ctx_norm
        flag  = score < self.threshold
        return {"score": score, "flag": flag}


def evaluate_quality(article) -> float:
    """
    (Alte Funktion zur Qualitätsbewertung von Artikeln via Flags.)
    """
    flags = check_quality_flags(article)
    return 1.0 - flags.rate


def compute_hybrid_importance(article,
                              w_meta: float     = 0.3,
                              w_semantic: float = 0.5,
                              w_quality: float  = 0.2) -> dict:
    """
    Hybrides Scoring von Artikeln:
      - Metadaten (publication_date, views, ref_count)
      - Semantische Relevanz (Embedding-Similarity)
      - Qualitäts-Indikatoren (Flag-Rate)
    """
    meta = get_article_metadata(article.id)
    age_days    = (datetime.utcnow() - meta['publication_date']).days
    age_score   = normalize(-age_days, -365*2, 0)
    views_score = normalize(meta.get('views', 0),    0, 1_000_000)
    refs_score  = normalize(meta.get('ref_count', 0), 0, 10_000)
    meta_score  = float(np.mean([age_score, views_score, refs_score]))

    sem_score  = compute_embedding_similarity(article.content, article.query)
    flags      = check_quality_flags(article)
    qual_score = 1.0 - flags.rate

    importance = w_meta * meta_score + w_semantic * sem_score + w_quality * qual_score
    return {
        'meta_score':     meta_score,
        'semantic_score': sem_score,
        'quality_score':  qual_score,
        'importance':     importance
    }


def _dcg(relevances: list[int]) -> float:
    """
    DCG-Berechnung für eine Liste binärer/multipler Relevanzen.
    """
    return sum((2**rel - 1) / math.log2(idx + 2) for idx, rel in enumerate(relevances))


def compute_ndcg(predictions: list, ground_truth: list) -> float:
    """
    NDCG = DCG(at actual) / DCG(at ideal).
    Hier binäre Relevanz: 1 wenn prediction in ground_truth, sonst 0.
    """
    relevances = [1 if p in ground_truth else 0 for p in predictions]
    ideal      = sorted(relevances, reverse=True)
    idcg       = _dcg(ideal)
    return _dcg(relevances) / idcg if idcg > 0 else 0.0


def compute_map(predictions: list, ground_truth: list) -> float:
    """
    Mean Average Precision (MAP) bei binärer Relevanz.
    """
    hits = 0
    sum_prec = 0.0
    for idx, p in enumerate(predictions, start=1):
        if p in ground_truth:
            hits += 1
            sum_prec += hits / idx
    return sum_prec / hits if hits > 0 else 0.0


def evaluate_ranking(predictions: list, ground_truth: list) -> dict:
    """
    Berechnet NDCG und MAP für gegebene Ranking-Listen.
    """
    return {
        'ndcg': compute_ndcg(predictions, ground_truth),
        'map':  compute_map(predictions, ground_truth)
    }
