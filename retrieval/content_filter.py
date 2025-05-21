import re
from storage.duckdb_storage import DuckDBStorage

class ContentFilter:
    """
    Filtert eine Liste von Artikeln anhand von Duplikaten und Mindestgröße.
    """
    def __init__(self):
        self.db = DuckDBStorage()

    def apply(self, candidates: list[dict], question: str) -> list[dict]:
        """
        :param candidates: Liste von Dicts mit keys 'title','link','content','summary','topic'
        :param question:   Nutzerfrage zur Themenbestimmung (wird aktuell nicht genutzt)
        :return: Gefilterte Liste von Kandidaten
        """
        seen = set()
        out = []
        for art in candidates:
            link = art.get("link")
            if link in seen:
                continue
            text = (art.get("title","") + " " +
                    art.get("content","") + " " +
                    art.get("summary","")).lower()
            # Mindestlänge: mindestens 10 Wörter
            if len(text.split()) < 10:
                continue
            seen.add(link)
            out.append(art)
        return out

    # Für Kompatibilität mit api.py (ruft `.filter(...)` auf)
    def filter(self, question: str, candidates: list[dict]) -> list[dict]:
        return self.apply(candidates, question)


class QualityFlags:
    """
    Hält die Flag-Rate eines Artikels (Anteil true-Flags).
    """
    def __init__(self, rate: float):
        self.rate = rate


def check_quality_flags(article: dict) -> QualityFlags:
    """
    Liest aus der Tabelle `answer_quality_flags`, wie viele Flags gesetzt sind.
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
    Führt ein Pre-Filtering durch: liefert Top-n Artikel-Links,
    deren title ODER content eines der Keywords enthält.
    """
    db  = DuckDBStorage()
    con = db.connect(read_only=True)

    clauses = " OR ".join(
        f"title ILIKE '%{kw}%' OR content ILIKE '%{kw}%'"
        for kw in keywords
    ) or "1=1"

    query = f"SELECT link FROM articles WHERE {clauses} LIMIT {top_n};"
    rows = con.execute(query).fetchall()
    con.close()

    return [r[0] for r in rows]
