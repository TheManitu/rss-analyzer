# ranking/cross_encoder_ranker.py

import logging

try:
    from sentence_transformers import CrossEncoder
except Exception:  # pragma: no cover - optional runtime dependency guard
    CrossEncoder = None

from config import CROSS_ENCODER_MODEL

logger = logging.getLogger(__name__)

class CrossEncoderRanker:
    """
    Re-rankt eine Liste von Kandidaten-Passagen via Cross-Encoder,
    liefert die Kandidaten sortiert nach ihrem Score zurück
    und bietet alias rank = rerank für Kompatibilität.
    """

    def __init__(self):
        # Modell wird einmalig geladen
        self.model = None
        if CrossEncoder is not None:
            try:
                self.model = CrossEncoder(CROSS_ENCODER_MODEL)
            except Exception as exc:
                logger.warning("CrossEncoder nicht verfuegbar, nutze bestehende Scores: %s", exc)

    def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        """
        Feintuning des Scores mit Cross-Encoder:

        - query: die Nutzerfrage
        - candidates: Liste von Dikt-Objekten mit mindestens dem Key "text"
        """
        if not candidates:
            return []
        if self.model is None:
            return sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)
        # Extrahiere nur die Text-Passagen
        texts = [c.get("text") or c.get("summary") or c.get("content") or "" for c in candidates]
        # Erzeuge Paare [query, passage]
        pairs = [[query, t] for t in texts]
        # Vorhersage der Scores
        scores = self.model.predict(pairs)

        # Aktualisiere die Kandidaten mit neuem Score
        for cand, score in zip(candidates, scores):
            cand["score"] = float(score)

        # Sortiere absteigend nach Score
        return sorted(candidates, key=lambda x: x["score"], reverse=True)

    # Alias, damit api.py sowohl `rank` als auch `rerank` aufrufen kann
    rank = rerank
