-- File: storage/metrics_schema.sql

-- Zeitreihe: Fragen pro Topic
CREATE TABLE IF NOT EXISTS topic_questions_history (
    timestamp TIMESTAMP,
    topic TEXT,
    question_count INTEGER
);

-- Zeitreihe: Frage-Kandidaten-Statistik
CREATE TABLE IF NOT EXISTS question_stats_history (
    timestamp TIMESTAMP,
    total_questions INTEGER,
    avg_candidates DOUBLE,
    median_candidates DOUBLE,
    zero_candidate_count INTEGER
);

-- Metriken pro Artikel (wird laufend aktualisiert)
CREATE TABLE IF NOT EXISTS article_metrics (
    article_id INTEGER PRIMARY KEY,
    view_count INTEGER,
    ref_count INTEGER,
    rating_score DOUBLE,
    last_updated TIMESTAMP
);
