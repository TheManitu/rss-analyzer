# retrieval/content_filter.py

import re
from storage.duckdb_storage import DuckDBStorage
from config import TOPIC_MAPPING

class ContentFilter:
    """
    Filtert eine Liste von Artikeln anhand von Themen-Keywords, Duplikaten und Mindestgröße.
    """
    def __init__(self, topic_mapping: dict = TOPIC_MAPPING):
        self.topic_mapping = topic_mapping
        self.db = DuckDBStorage()

    def apply(self, candidates: list, question: str) -> list:
        """
        :param candidates: Liste von Dicts mit keys 'title','link','content','summary','topic'
        :param question:   Nutzerfrage zur Themenbestimmung
        :return: Gefilterte Liste von Kandidaten
        """
        q_lower = question.lower()
        # Thema finden
        topic = None
        for t, data in self.topic_mapping.items():
            if any(kw.lower() in q_lower for kw in data.get("keywords", [])):
                topic = t
                break
        keywords = self.topic_mapping.get(topic or "Allgemein", {}).get("keywords", [])

        seen = set()
        out = []
        for art in candidates:
            link = art.get("link")
            if link in seen:
                continue
            text = (art.get("title","") + " " + art.get("content","") + " " + art.get("summary","")).lower()
            # Keyword-Filter
            if keywords and not any(kw.lower() in text for kw in keywords):
                continue
            # Mindestlänge
            if len(text.split()) < 10:
                continue
            seen.add(link)
            out.append(art)
        return out


class QualityFlags:
    """
    Hält die Flag-Rate eines Artikels (Anteil true-Flags).
    """
    def __init__(self, rate: float):
        self.rate = rate


def check_quality_flags(article: dict) -> QualityFlags:
    """
    Liest aus der Tabelle `answer_quality_flags`, wie viele Flags gesetzt sind.
    :param article: Dict mit mindestens key 'link'
    :return: QualityFlags(rate), rate in [0,1]
    """
    db  = DuckDBStorage()
    con = db.connect(read_only=True)
    link = article.get("link")

    # Anzahl true-Flags
    row_true = con.execute(
        "SELECT COUNT(*) FROM answer_quality_flags WHERE link = ? AND flag = TRUE",
        (link,)
    ).fetchone()
    true_count = row_true[0] if row_true else 0

    # Gesamtzahl aller Flags
    row_all = con.execute(
        "SELECT COUNT(*) FROM answer_quality_flags WHERE link = ?",
        (link,)
    ).fetchone()
    all_count = row_all[0] if row_all else 0

    con.close()
    rate = (true_count / all_count) if all_count else 0.0
    return QualityFlags(rate)


def keyword_filter(keywords: list, top_n: int = 500) -> list:
    """
    Führt ein Pre-Filtering durch: liefert die Top-n Artikel-Links,
    deren title ODER content eines der Keywords enthält.
    """
    db  = DuckDBStorage()
    con = db.connect(read_only=True)

    # Baue WHERE-Klausel
    clauses = " OR ".join(
        f"title ILIKE '%{kw}%' OR content ILIKE '%{kw}%'"
        for kw in keywords
    ) or "1=1"

    query = f"SELECT link FROM articles WHERE {clauses} LIMIT {top_n};"
    rows = con.execute(query).fetchall()
    con.close()

    return [r[0] for r in rows]
