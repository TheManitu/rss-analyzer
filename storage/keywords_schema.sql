-- storage/keywords_schema.sql

-- Tabelle für extrahierte Keywords pro Artikel
CREATE TABLE IF NOT EXISTS article_keywords (
    link    TEXT,
    keyword TEXT
);