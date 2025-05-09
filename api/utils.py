# app/api/utils.py

import re
import time
import duckdb
import numpy as np
from flask import session, current_app
from config import DB_PATH, TOPIC_MAPPING, EMBEDDING_MODEL, CROSS_ENCODER_MODEL
from sentence_transformers import SentenceTransformer, CrossEncoder

# Initialize embedding and cross-encoder models only once
_embedder = SentenceTransformer(EMBEDDING_MODEL)
_topic_names = list(TOPIC_MAPPING.keys())
_topic_embs = _embedder.encode(_topic_names, normalize_embeddings=True)
_cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)


def extract_topic_from_question(question: str) -> str:
    """
    Bestimmt das Topic anhand vordefinierter Keywords oder
    per semantischer Ähnlichkeit gegen Topic-Namen.
    """
    q = question.lower()
    # 1) Regelbasiert über TOPIC_MAPPING
    for topic, data in TOPIC_MAPPING.items():
        for kw in data.get("keywords", []):
            if kw.lower() in q:
                return topic

    # 2) Semantische Einordnung via Embeddings
    try:
        q_emb = _embedder.encode([question], normalize_embeddings=True)[0]
        sims = np.dot(_topic_embs, q_emb)
        best_idx = int(np.argmax(sims))
        return _topic_names[best_idx]
    except Exception:
        pass

    return "Allgemein"


def assign_topic_from_text(text: str) -> str:
    """
    Ordnet einem beliebigen Text ein Topic zu:
      1) Regelbasiert via Keywords
      2) Semantisch via Embeddings
      3) Feintuning via Cross-Encoder
    Rückgabe "Allgemein" als letzter Fallback.
    """
    t_lower = text.lower()
    # 1) Keyword-Check
    for topic, data in TOPIC_MAPPING.items():
        for kw in data.get("keywords", []):
            if kw.lower() in t_lower:
                return topic

    # 2) Semantische Ähnlichkeit
    try:
        txt_emb = _embedder.encode([text], normalize_embeddings=True)[0]
        sims = np.dot(_topic_embs, txt_emb)
        best_idx = int(np.argmax(sims))
        best_score = float(sims[best_idx])
        # Wir akzeptieren stets den besten, da Fragen zugeordnet werden sollen
        return _topic_names[best_idx]
    except Exception:
        pass

    # 3) Cross-Encoder-Feintuning
    try:
        pairs = [[topic, text] for topic in _topic_names]
        scores = _cross_encoder.predict(pairs)
        best_idx = int(np.argmax(scores))
        return _topic_names[best_idx]
    except Exception:
        pass

    return "Allgemein"


def store_question_event(question: str, topic: str, n_candidates: int):
    """
    Speichert eine Frage in DuckDB und updated Prometheus-Metriken.
    """
    con = duckdb.connect(DB_PATH)
    start = time.time()

    con.execute("""
        CREATE TABLE IF NOT EXISTS question_events (
            timestamp     TIMESTAMP,
            question      TEXT,
            topic         TEXT,
            n_candidates  INTEGER
        );
    """)
    existing = [c[1] for c in con.execute("PRAGMA table_info('question_events')").fetchall()]
    if "user_id" not in existing:
        con.execute("ALTER TABLE question_events ADD COLUMN user_id TEXT;")
    if "session_id" not in existing:
        con.execute("ALTER TABLE question_events ADD COLUMN session_id TEXT;")

    con.execute(
        """
        INSERT INTO question_events
            (timestamp, question, topic, n_candidates, user_id, session_id)
        VALUES
            (CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
        """,
        (question, topic, n_candidates, session.get("user_id"), session.get("session_id"))
    )

    duration = time.time() - start
    current_app.DB_LATENCY.observe(duration)

    total = con.execute("SELECT COUNT(*) FROM question_events").fetchone()[0]
    zeros = con.execute("SELECT COUNT(*) FROM question_events WHERE n_candidates = 0").fetchone()[0]
    current_app.ZERO_CAND.set(zeros / total if total else 0)

    con.close()
    current_app.Q_COUNT.inc()


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
