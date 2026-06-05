#!/usr/bin/env python3
# pipeline/segmentation.py

import logging
import re
try:
    import nltk
    from nltk.tokenize import sent_tokenize
except Exception:  # pragma: no cover - optional runtime dependency guard
    nltk = None
    sent_tokenize = None
from storage.duckdb_storage import DuckDBStorage

# Stelle sicher, dass beide Tokenizer-Modelle vorhanden sind
if nltk is not None:
    for resource in ('punkt', 'punkt_tab'):
        try:
            nltk.data.find(f'tokenizers/{resource}')
        except LookupError:
            nltk.download(resource)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Segmenter:
    """
    Zerlegt Artikel-Content in überlappende Satz-Windows
    und speichert sie in der Tabelle "article_sections".
    """

    def __init__(self, db_path=None, section_size=5, section_overlap=2):
        self.storage = DuckDBStorage(db_path=db_path)
        self.section_size    = section_size
        self.section_overlap = section_overlap

    def _split_into_windows(self, text: str) -> list[str]:
        """
        1) in Sätze splitten
        2) überlappende Fenster der Größe section_size erzeugen
        """
        if sent_tokenize is not None:
            sentences = sent_tokenize(text)
        else:
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]
        windows = []
        i = 0
        while i < len(sentences):
            window = sentences[i : i + self.section_size]
            windows.append(" ".join(window))
            i += max(1, self.section_size - self.section_overlap)
        return windows

    def run(self):
        logger.info("Segmenter: Lade alle Artikel …")
        articles = self.storage.get_all_articles()
        total    = len(articles)

        for idx, art in enumerate(articles, start=1):
            link    = art["link"]
            content = art.get("content") or art.get("summary") or ""
            windows = self._split_into_windows(content)

            con = self.storage.connect()
            # Tabelle richtig benennen
            con.execute(
                "DELETE FROM article_sections WHERE link = ?",
                [link]
            )

            # Jetzt die neuen Windows abspeichern
            for sec_idx, sec_text in enumerate(windows):
                con.execute(
                    "INSERT INTO article_sections (link, section_idx, section_text) VALUES (?, ?, ?)",
                    [link, sec_idx, sec_text]
                )
            con.commit()
            con.close()

            logger.info(f"[Segmentation {idx}/{total}] {link} → {len(windows)} sections")

        logger.info("Segmenter: Alle Artikel segmentiert.")
