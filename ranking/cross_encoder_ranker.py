# ranking/cross_encoder_ranker.py

from sentence_transformers import CrossEncoder
from config import CROSS_ENCODER_MODEL

class CrossEncoderRanker:
    def __init__(self):
        self.cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)

    def rerank(self, query: str, candidates: list) -> list:
        if not candidates:
            return []
        # Titel + Summary kombinieren
        pairs = [
            (query, f"{c['title']}. {c['summary']}") 
            for c in candidates
        ]
        scores = self.cross_encoder.predict(pairs)
        # Kandidaten mit Score paaren und sortieren
        scored = list(zip(candidates, scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        # Nur Kandidaten zurückgeben (Limit in app.py)
        return [item[0] for item in scored]
