-- storage/metrics_schema.sql

-- 1) Artikel-Metriken
CREATE TABLE IF NOT EXISTS article_metrics (
    link TEXT PRIMARY KEY,
    view_count INTEGER DEFAULT 0,
    ref_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2) Themen-Metriken
CREATE TABLE IF NOT EXISTS topic_metrics (
    topic           TEXT PRIMARY KEY,
    view_count      INTEGER DEFAULT 0,
    question_count  INTEGER DEFAULT 0,
    last_updated    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3) Globale Frage-Statistiken (History)
CREATE TABLE IF NOT EXISTS question_stats_history (
    timestamp            TIMESTAMP,
    total_questions      INTEGER,
    avg_candidates       DOUBLE,
    median_candidates    DOUBLE,
    zero_candidate_count INTEGER
);

-- 4) Audit-Trail aller Events (optional)
CREATE TABLE IF NOT EXISTS events_audit (
    timestamp   TIMESTAMP,
    event_type  TEXT,
    link        TEXT,
    info        TEXT
);

-- 5) **Neu**: Frage-Events
--    Hier speichern wir jede eingereichte Frage für Analytics.
CREATE TABLE IF NOT EXISTS question_events (
    timestamp     TIMESTAMP,
    question      TEXT,
    topic         TEXT,
    n_candidates  INTEGER
);

-- 6) Flags für schlechte Antworten pro Artikel
CREATE TABLE IF NOT EXISTS answer_quality_flags (
    link TEXT,
    flag BOOLEAN
);