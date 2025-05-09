#!/usr/bin/env python3
"""
scripts/recalc_topics.py

Weist jedem Artikel automatisch ein Thema aus TOPIC_MAPPING zu,
basierend auf der Häufigkeit der Stichwörter in Titel, Description,
Summary und einem Ausschnitt des Contents.

Verzichtet gänzlich auf Embeddings oder Cross-Encoder, läuft
sehr ressourcenschonend und stabil im Docker-Container.

Usage:
  make recalc_topics
  oder:
  docker-compose exec api python scripts/recalc_topics.py
"""

import logging
import duckdb
from config import DB_PATH, TOPIC_MAPPING

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    con = duckdb.connect(DB_PATH)
    logging.info("Lade alle Artikel für Topic-Zuordnung…")

    # Lade alle relevanten Felder
    rows = con.execute("""
        SELECT link, title, description, summary, SUBSTR(content, 1, 2000) AS snippet
        FROM articles
    """).fetchall()

    updated = 0
    for link, title, description, summary, snippet in rows:
        # Kombiniere Text und normalisiere
        text = " ".join(filter(None, [title, description, summary, snippet])).lower()

        # Wähle das Topic mit den meisten Keyword-Treffern
        best_topic = "Allgemein"
        max_hits   = 0
        for topic, data in TOPIC_MAPPING.items():
            hits = sum(text.count(kw.lower()) for kw in data.get("keywords", []))
            if hits > max_hits:
                max_hits   = hits
                best_topic = topic

        # Update in der DB, nur wenn sich geändert hat
        con.execute(
            "UPDATE articles SET topic = ? WHERE link = ? AND topic <> ?",
            (best_topic, link, best_topic)
        )
        updated += 1

    con.close()
    logging.info(f"Topic-Zuordnung abgeschlossen. {updated} Artikel durchlaufen.")

if __name__ == "__main__":
    main()
