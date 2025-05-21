#!/usr/bin/env python3
# pipeline/topic_assignment.py

import re
import logging
import numpy as np
from storage.duckdb_storage import DuckDBStorage
from config import (
    SYN_WEIGHT,
    TOPIC_TITLE_WEIGHT,
    TOPIC_THRESHOLD_FACTOR,
    TOPIC_EMB_MODEL,
    TOPIC_EMB_WEIGHT,
    TOPIC_EMB_THRESHOLD,
)
from topic_config import TOPIC_MAPPING, TOPIC_SYNONYMS
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class TopicAssigner:
    """
    Kombiniert:
     1) Harte Keyword-Matches (Body + Titel-Boost)
     2) Synonym-Matches
     3) Embedding-Ähnlichkeit gegen Topic-Prototypen
    """

    def __init__(self, db_path: str = None):
        # DB
        self.storage = DuckDBStorage(db_path=db_path)

        # Embedding-Modell initialisieren
        logger.info(f"[TopicAssigner] lade Embedding-Modell '{TOPIC_EMB_MODEL}'…")
        self.emb_model = SentenceTransformer(TOPIC_EMB_MODEL)
        # Topic-Prototypen einbetten
        self.topic_embs = {}
        for topic, conf in TOPIC_MAPPING.items():
            proto_text = topic + " " + " ".join(
                conf["keywords"] + TOPIC_SYNONYMS.get(topic, [])
            )
            self.topic_embs[topic] = self.emb_model.encode(proto_text, convert_to_numpy=True)

    def assign_topic(self, title: str, content: str) -> str:
        text_lower  = f"{title} {content}".lower()
        title_lower = title.lower()

        # 1) Körper- und Titel-Matches zählen
        base_scores = {}
        for topic, conf in TOPIC_MAPPING.items():
            body_hits  = sum(bool(re.search(rf"\b{re.escape(kw)}\b", text_lower))
                             for kw in conf["keywords"])
            title_hits = sum(bool(re.search(rf"\b{re.escape(kw)}\b", title_lower))
                             for kw in conf["keywords"])
            base_scores[topic] = body_hits + TOPIC_TITLE_WEIGHT * title_hits

        # 2) Synonym-Matches zählen
        syn_scores = {
            topic: sum(bool(re.search(rf"\b{re.escape(syn)}\b", text_lower))
                       for syn in TOPIC_SYNONYMS.get(topic, []))
            for topic in TOPIC_MAPPING
        }

        # 3) Kombinierter Regel-Score
        rule_scores = {
            t: base_scores[t] + SYN_WEIGHT * syn_scores[t]
            for t in TOPIC_MAPPING
        }

        # 4) Embedding-Score berechnen
        art_emb = self.emb_model.encode(f"{title} {content}", convert_to_numpy=True)
        emb_scores = {}
        for t, te in self.topic_embs.items():
            emb_scores[t] = float(
                np.dot(art_emb, te) /
                ((np.linalg.norm(art_emb) * np.linalg.norm(te)) + 1e-8)
            )

        # 5) Kombiniere zu finalen Scores
        final_scores = {
            t: rule_scores[t] + TOPIC_EMB_WEIGHT * emb_scores[t]
            for t in TOPIC_MAPPING
        }

        # 6) Valid-Filter: mind. 1 harter Treffer ODER Embedding-Ähnlichkeit über Threshold
        valid = {
            t: final_scores[t]
            for t in TOPIC_MAPPING
            if base_scores.get(t, 0) >= 1
               or syn_scores.get(t, 0) >= 1
               or emb_scores.get(t, 0) >= TOPIC_EMB_THRESHOLD
        }
        if not valid:
            return "Allgemein"

        # 7) Top-Topic vs. Zweitplatzierten vergleichen
        sorted_topics = sorted(valid.items(), key=lambda x: x[1], reverse=True)
        best_topic, best_score     = sorted_topics[0]
        runner_up_score = sorted_topics[1][1] if len(sorted_topics) > 1 else 0

        # 8) Nur übernehmen, wenn klar überlegen
        if runner_up_score <= 0 or best_score >= runner_up_score * TOPIC_THRESHOLD_FACTOR:
            return best_topic
        return "Allgemein"

    def run(self):
        articles = self.storage.get_all_articles()
        total    = len(articles)
        logger.info(f"[TopicAssigner] Starte Neuzuordnung für {total} Artikel…")

        changed = 0
        for art in articles:
            link      = art["link"]
            title     = art.get("title", "") or ""
            content   = art.get("content", "") or ""
            old_topic = art.get("topic", "Allgemein")
            new_topic = self.assign_topic(title, content)

            # immer loggen, was festgelegt wurde
            logger.info(
                f"[TopicAssigner] {link}\n"
                f"  Old: {old_topic}\n"
                f"  New: {new_topic}"
            )

            if new_topic != old_topic:
                con = self.storage.connect()
                con.execute(
                    "UPDATE articles SET topic = ? WHERE link = ?",
                    (new_topic, link)
                )
                con.commit()
                con.close()
                changed += 1

        logger.info(f"[TopicAssigner] {changed} von {total} Topics aktualisiert.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    TopicAssigner().run()
