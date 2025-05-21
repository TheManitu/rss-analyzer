# pipeline/article_cleaner.py

import logging
import re
from datetime import date, timedelta

from storage.duckdb_storage import DuckDBStorage
from config import MIN_ARTICLE_WORDS

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --- Regex-Patterns ---
HTML_TAG_RE = re.compile(r'<[^>]+>')

def contains_html(text: str) -> bool:
    return bool(HTML_TAG_RE.search(text or ''))

def is_latin_only(text: str) -> bool:
    # erlaubt alle Zeichen im Unicode-Block Latin-1 (inkl. Umlaute)
    return not bool(re.search(r'[^\u0000-\u00FF]', text or ''))

def word_count(text: str) -> int:
    return len((text or '').split())

class ArticleCleaner:
    """
    Entfernt Artikel aus der DB, die:
    - älter als 7 Tage sind,
    - HTML-Tags enthalten,
    - nicht-lateinische Schrift enthalten,
    - oder kürzer als MIN_ARTICLE_WORDS sind.
    """

    def __init__(self, db_path: str | None = None):
        self.storage = DuckDBStorage(db_path=db_path)

    def run(self):
        self.clean()

    def clean(self):
        con = self.storage.connect()
        rows = con.execute(
            "SELECT link, content, published FROM articles"
        ).fetchall()

        cutoff = date.today() - timedelta(days=7)
        removed = 0

        for link, content, published in rows:
            reason = None

            # 1) älter als 7 Tage
            if published and published < cutoff:
                reason = f"älter als 7 Tage ({published})"

            # 2) HTML-Tags
            elif contains_html(content):
                reason = "enthält HTML-Tags"

            # 3) nicht-lateinische Schrift
            elif not is_latin_only(content):
                reason = "nicht-lateinische Schrift entdeckt"

            # 4) zu kurz
            elif word_count(content) < MIN_ARTICLE_WORDS:
                reason = f"zu kurz ({word_count(content)} Wörter)"

            if reason:
                con.execute(
                    "DELETE FROM articles WHERE link = ?",
                    (link,)
                )
                logger.info(f"[CLEANUP] {link} → gelöscht: {reason}")
                removed += 1

        con.commit()
        con.close()
        logger.info(f"[CLEANUP] Fertig. Insgesamt entfernt: {removed} Artikel.")
