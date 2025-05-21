# ranking/cross_encoder_ranker.py

from sentence_transformers import CrossEncoder
from config import CROSS_ENCODER_MODEL

class CrossEncoderRanker:
    """
    Re-rankt eine Liste von Kandidaten-Passagen via Cross-Encoder,
    liefert die Kandidaten sortiert nach ihrem Score zurück
    und bietet alias rank = rerank für Kompatibilität.
    """

    def __init__(self):
        # Modell wird einmalig geladen
        self.model = CrossEncoder(CROSS_ENCODER_MODEL)  # :contentReference[oaicite:0]{index=0}:contentReference[oaicite:1]{index=1}

    def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        """
        Feintuning des Scores mit Cross-Encoder:

        - query: die Nutzerfrage
        - candidates: Liste von Dikt-Objekten mit mindestens dem Key "text"
        """
        # Extrahiere nur die Text-Passagen
        texts = [c["text"] for c in candidates]
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
