
# RSS Analyzer mit RAG

Dieses Open-Source-Projekt sammelt, bereinigt und analysiert RSS-Feed-Artikel lokal und stellt eine interaktive Web-UI zur Verfügung. Es kombiniert klassische ETL-Techniken mit einer Retrieval-Augmented Generation (RAG)-Pipeline.

---

## Kernfunktionen

- **Robuste RSS-Ingestion**  
  - Paralleles Fetching (aiohttp), Duplikat-Check, HTML- und Cookie-Bereinigung  
  - Volltext-Scraping mit BeautifulSoup (nur ausgewählte Domains), Skip-Liste für problematische URLs  
  - Automatisches Entfernen kurzer Artikel (< 300 Wörter)  
  - Extractive Summaries (TextRank via Sumy) und regelbasierte Übersetzung (Apertium)  

- **Saubere Datenhaltung**  
  - DuckDB-Storage mit automatischer Schema-Migration (`content`, `summary`, `translation`)  
  - `clean_text()` entfernt HTML-Tags und Entities  
  - Nachreinigung aller ausgelieferten Texte vor UI-Darstellung  

- **RAG-Pipeline**  
  - Semantische Suche: Sentence-Transformer + FAISS  
  - Keyword-Suche: BM25  
  - Hybrid-Score-Fusion und Auswahl der Top-K Kontexte  

- **Prompt-Templates**  
  - Maximal 5 Quellen pro Antwort  
  - Wichtigste Artikel: Vollständige Zusammenfassung (≤ 500 Wörter)  
  - Nebensätze: Kurzfassung (≤ 200 Zeichen)  
  - Ausgabe ausschließlich auf Deutsch  
  - Prompt-Vorlagen im Verzeichnis `prompt_templates/`  

- **REST-API (Flask)**  
  - Endpoint `/search`: liefert Top-5 Kandidaten (`title`, `link`) als JSON für Frontend  
  - Antwortgenerierung mit LLM (Llama2 oder konfiguriertes Modell)  

- **Web-UI**  
  - Indexseite mit Suchfeld, Antwort und klickbarer Quellenliste  
  - Unter der Antwort eine Leerzeile und `.sources-box` für Quellenlinks  
  - Template-Filter `|striptags`, `first_words`, `truncatewords` in `app.py`  

- **Styling**  
  - `static/style.css` enthält `.sources-box`-Styles sowie allgemeines Layout  
  - Moderne Typografie über Google Fonts  

---

## Projektstruktur

rss-analyzer/ ├── docker/
│ └── docker-compose.yml # Zookeeper, Kafka, Spark ├── prompt_templates/
│ └── *.tpl
├── rss_analyzer/
│ ├── config.py
│ ├── ingestion/
│ │ └── rss_ingest.py
│ ├── storage/
│ │ └── duckdb_storage.py
│ ├── retrieval/
│ │ └── hybrid_retrieval.py │ ├── ranking/
│ │ └── cross_encoder_ranker.py │ ├── generation/
│ │ └── llm_generator.py
│ ├── evaluation/
│ │ └── quality_evaluator.py │ ├── api/
│ │ └── app.py
│ └── topic_tracker.py
├── templates/
│ └── *.html
├── static/
│ └── style.css
├── analytics/
│ └── spark_analytics.py
├── scripts/
│ └── recalc_importance.py
├── storage/
│ └── metrics_schema.sql
├── tests/
│ └── *.py
├── requirements.txt
└── README.md


---

## Installation & Start

1. **Klone das Repo**
   ```bash
   git clone https://github.com/<user>/rss-analyzer.git
   cd rss-analyzer

    DB zurücksetzen

  ```rm -f data/rssfeed.duckdb```

Dependencies installieren

```pip install -r requirements.txt```

Docker-Services starten

```docker-compose up -d --build```

Web-UI direkt lokal starten (ohne Kafka/Spark)

    ```python -m rss_analyzer.api.app```

    → http://localhost:5000

Tests

pytest tests/

Neue Funktionen

    Persistentes Question-Tracking

        Tabelle question_events in DuckDB speichert jede gestellte Frage (Timestamp, Question-Text, Topic, Kandidaten-Anzahl).

        API-Funktion store_question_event() in api/app.py legt Eintrag bei jeder Suche an.

    Dynamische Importance-Berechnung

        Methode recalc_importance() in storage/duckdb_storage.py gewichtet normierte Views, Frage-Refs und Quality-Flags.

        Skript scripts/recalc_importance.py initialisiert Metrik-Tabellen und berechnet articles.importance neu ohne Code-Änderung (Steuerung via ENV-Variablen W_VIEWS, W_REFS, W_FLAG).

    Erweitertes Analytics-Dashboard

        /analytics-Endpoint liefert nun:

            Top-10 meistgestellte Fragen (aus question_events)

            Fragen pro Stunde (aus question_events)

            Top-10 meistgelesene Artikel (aus article_metrics)

        Tabelle answer_quality_flags angelegt für späteres Qualitäts-Monitoring.

    Spark-Streaming

        Job analytics/spark_analytics.py liest Kafka-Events (UserQuestions, ArticleViews) und schreibt:

            article_metrics (Views + Refs)

            topic_metrics (Views + Questions)

            question_stats_history (globale Frage-Stats)

Neue Dateien

    storage/metrics_schema.sql: DDL für article_metrics, topic_metrics, question_events, answer_quality_flags, u.v.m.

    analytics/spark_analytics.py: PySpark-Job für Live-Aggregationen aus Kafka → DuckDB

    scripts/recalc_importance.py: CLI-Skript zum Neuberechnen von articles.importance

    Modifikation: storage/duckdb_storage.py ergänzt Methode recalc_importance()

    Modifikation: api/app.py fügt Funktion store_question_event() und /analytics-Logik hinzu

    Neues Modul: logging_service/kafka_config_and_logger.py (Kafka-Producer + Schemas)

Erweiterungsmöglichkeiten

    Antwort-Qualitätsmetriken

        Speichere den QualityEvaluator-Score pro Antwort in answer_quality_scores.

        Visualisiere im Dashboard, welche Artikel in besonders hochwertigen Antworten genutzt werden.

    Time-Series-Visualisierung

        Exporte nach Grafana/Prometheus für: Fragen- und Views-Trends, Entwicklung der importance-Scores.

    Feinere Rating-Modelle

        Manueller Nutzer-Feedback-Score (Like/Dislike), Recency-Bonus, Z-Score-Normierung.

    Skalierbare Storage-Backends

        Delta Lake / Iceberg für Time-Travel und Versionierung großer Datenmengen.

Verbesserungspotential

    Observability & Alerting

        Überwache Kafka-Offsets, Spark-Checkpoints, DuckDB-Latenzen.

        Alerts bei Anomalien: z.B. plötzlicher Anstieg von Zero-Candidate-Fragen oder Abfall der Average Quality.

    Automatische Gewichtungsoptimierung

        Grid-Search oder Bayesian Optimization für (W_VIEWS, W_REFS, W_FLAG) anhand historischer Daten.

    Langzeit-Archivierung

        Periodische Exporte nach Data Warehouse (z.B. BigQuery) für Deep-Dives.

    User-Segmentierung & Personalisierung

        Logge user_id und session_id für Verhaltensanalysen und personalisierte Empfehlungen.
