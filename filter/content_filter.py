"""
Inhaltliche Filterung: thematische Übereinstimmung, Qualitätskriterien, Duplikate.
"""
import re
from config import TOPIC_MAPPING

class ContentFilter:
    def __init__(self, topic_mapping: dict):
        self.topic_mapping = topic_mapping

    def apply(self, candidates: list, question: str) -> list:
        """
        Filtert Kandidatenpassagen basierend auf Thema, Duplikaten und Minimalqualität.
        :param candidates: Liste von Dicts mit mindestens keys 'id','title','text','link'.
        :param question: Die Nutzerfrage, zur Themenbestimmung.
        :return: Gefilterte Liste von Kandidaten.
        """
        filtered = []
        seen_ids = set()
        q_lower = question.lower()
        # Bestimme Hauptthema der Frage
        main_topic = None
        for topic, data in self.topic_mapping.items():
            if any(kw.lower() in q_lower for kw in data.get('keywords', [])):
                main_topic = topic
                break
        topic_keywords = self.topic_mapping.get(main_topic, {}).get('keywords', []) if main_topic else []

        for c in candidates:
            cid = c.get('id')
            if cid in seen_ids:
                continue
            text = (c.get('title','') + ' ' + c.get('text', c.get('content',''))).lower()
            # Thema-Filter
            if topic_keywords and not any(kw.lower() in text for kw in topic_keywords):
                continue
            # Minimaler Wortumfang
            if len(c.get('text', '').split()) < 10:
                continue
            seen_ids.add(cid)
            filtered.append(c)

        return filtered
