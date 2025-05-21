
# app/api/utils.py

import re
import time
import duckdb
from flask import session, current_app
from config import DB_PATH
from topic_config import TOPIC_MAPPING, TOPIC_SYNONYMS
from prometheus_client import Counter

# Metrik für verworfene Artikel
REJECTED_ARTICLES = Counter(
    'rejected_articles_total',
    'Anzahl der Artikel, die im Persistenz-Layer verworfen wurden'
)


def extract_topic_from_question(question: str) -> str:
    """
    Liefert das Topic für eine Nutzerfrage zurück,
    basierend auf gewichteter Synonym- und Keyword-Analyse.
    """
    q = question.lower()
    best_topic = "Allgemein"
    best_score = 0
    syn_weight = current_app.config.get("SYN_WEIGHT", 2)

    for topic, conf in TOPIC_MAPPING.items():
        score = 0
        for syn in TOPIC_SYNONYMS.get(topic, []):
            if re.search(rf"\b{re.escape(syn)}\b", q):
                score += syn_weight
        for kw in conf.get("keywords", []):
            if re.search(rf"\b{re.escape(kw)}\b", q):
                score += 1
        if score > best_score:
            best_score = score
            best_topic = topic

    return best_topic if best_score > 0 else "Allgemein"


def assign_topic_from_text(text: str) -> str:
    """
    Ordnet einem beliebigen Text ein Topic zu.
    Nutzt dieselbe Logik wie extract_topic_from_question.
    """
    return extract_topic_from_question(text)


def store_question_event(question: str, topic: str, n_candidates: int):
    """
    Speichert eine Frage in DuckDB (Tabelle question_events) und
    aktualisiert die Prometheus-Metriken DB_LATENCY, ZERO_CAND, Q_COUNT.
    """
    con = duckdb.connect(DB_PATH)
    start = time.time()

    con.execute("""
        CREATE TABLE IF NOT EXISTS question_events (
            timestamp     TIMESTAMP,
            question      TEXT,
            topic         TEXT,
            n_candidates  INTEGER,
            user_id       TEXT,
            session_id    TEXT
        );
    """)
    cols = [col[1] for col in con.execute("PRAGMA table_info('question_events')").fetchall()]
    if "user_id" not in cols:
        con.execute("ALTER TABLE question_events ADD COLUMN user_id TEXT;")
    if "session_id" not in cols:
        con.execute("ALTER TABLE question_events ADD COLUMN session_id TEXT;")

    con.execute("""
        INSERT INTO question_events
            (timestamp, question, topic, n_candidates, user_id, session_id)
        VALUES
            (CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
    """, (
        question,
        topic,
        n_candidates,
        session.get("user_id"),
        session.get("session_id")
    ))

    duration = time.time() - start
    current_app.DB_LATENCY.observe(duration)
    total = con.execute("SELECT COUNT(*) FROM question_events").fetchone()[0]
    zeros = con.execute("SELECT COUNT(*) FROM question_events WHERE n_candidates = 0").fetchone()[0]
    current_app.ZERO_CAND.set(zeros / total if total else 0)

    con.close()
    current_app.Q_COUNT.inc()


def count_rejected_article():
    """
    Erhöht den Zähler der im Persistenz-Layer verworfenen Artikel.
    """
    REJECTED_ARTICLES.inc()


def first_words(s: str, num_words: int = 250) -> str:
    """
    Entfernt HTML-Tags und gibt die ersten `num_words` Wörter zurück.
    """
    if not s:
        return ""
    clean = re.sub(r"<.*?>", "", s)
    words = clean.split()
    if len(words) <= num_words:
        return clean
    return " ".join(words[:num_words]) + "…"


def truncatewords(s: str, num_words: int = 500) -> str:
    """
    Schneidet den Text nach `num_words` Wörtern ab.
    """
    if not s:
        return ""
    words = s.split()
    if len(words) <= num_words:
        return s
    return " ".join(words[:num_words]) + "…"
