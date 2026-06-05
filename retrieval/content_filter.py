import re
from storage.duckdb_storage import DuckDBStorage
from pipeline.text_quality import clean_article_text, is_useful_article_text, is_valid_source_link

class ContentFilter:
    """
    Filtert Artikel/Passagen anhand von Duplikaten, Quellen und Textqualitaet.
    """
    def __init__(self, min_words: int = 10):
        self.db = DuckDBStorage()
        self.min_words = min_words

    def apply(self, candidates: list[dict], question: str) -> list[dict]:
        """
        :param candidates: Liste von Dicts mit keys wie 'title','link','content','summary','text'
        :param question:   Nutzerfrage zur Themenbestimmung (wird aktuell nicht genutzt)
        :return: Gefilterte Liste von Kandidaten
        """
        seen = set()
        out = []
        for art in candidates:
            link = (art.get("link") or "").strip()
            if link and not is_valid_source_link(link):
                continue

            text = clean_article_text(" ".join(
                str(art.get(key) or "")
                for key in ("title", "text", "section_text", "content", "summary", "description")
            ))
            fingerprint = link or re.sub(r"\W+", " ", text.lower())[:160]
            if not fingerprint or fingerprint in seen:
                continue
            if not is_useful_article_text(text, min_words=self.min_words):
                continue

            cleaned = dict(art)
            if cleaned.get("text"):
                cleaned["text"] = clean_article_text(cleaned["text"])
            if cleaned.get("summary"):
                cleaned["summary"] = clean_article_text(cleaned["summary"])
            if cleaned.get("content"):
                cleaned["content"] = clean_article_text(cleaned["content"])
            seen.add(fingerprint)
            out.append(cleaned)
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

    clean_keywords = [str(kw).strip() for kw in keywords if str(kw).strip()]
    if clean_keywords:
        clauses = " OR ".join("title ILIKE ? OR content ILIKE ?" for _ in clean_keywords)
        params = []
        for kw in clean_keywords:
            like = f"%{kw}%"
            params.extend([like, like])
        params.append(top_n)
        rows = con.execute(f"SELECT link FROM articles WHERE {clauses} LIMIT ?;", params).fetchall()
    else:
        rows = con.execute("SELECT link FROM articles LIMIT ?;", (top_n,)).fetchall()
    con.close()

    return [r[0] for r in rows]
