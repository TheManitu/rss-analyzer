"""
Cross-Encoder Re-Ranking für präzises Ranking der Kandidaten.
"""
from sentence_transformers import CrossEncoder
from config import CROSS_ENCODER_MODEL, MAX_CONTEXTS

class CrossEncoderRanker:
    def __init__(self):
        # Cross-Encoder laden
        self.cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)

    def rerank(self, query: str, candidates: list) -> list:
        """
        Nimmt eine Liste von Kandidaten-Kontexten und rankt diese anhand eines CrossEncoders.
        :param query: Die Nutzerfrage
        :param candidates: Liste von Dicts mit keys 'id','title','text','link'
        :return: Top MAX_SOURCES Kandidaten nach Relevanz sortiert
        """
        if not candidates:
            return []
        # Erzeuge Paare (query, passage_text)
        pairs = [(query, c['text']) for c in candidates]
        # Cross-Encoder-Scores berechnen
        scores = self.cross_encoder.predict(pairs)
        # Paare mit Scores verbinden und sortieren
        scored = list(zip(candidates, scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        # Top MAX_SOURCES extrahieren
        top_candidates = [item[0] for item in scored[:MAX_CONTEXTS]]
        return top_candidates
