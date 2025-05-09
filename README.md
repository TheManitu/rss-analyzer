
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
  - Template-Filter `|striptags`, `first_words`, `truncatewords` in `api/`  

- **Styling**  
  - `static/style.css` enthält `.sources-box`-Styles sowie allgemeines Layout  
  - Moderne Typografie über Google Fonts  

---

## Projektstruktur

rss-analyzer/
├── docker/
│ └── docker-compose.yml # Zookeeper, Kafka, Prometheus, Grafana, API, …
├── prompt_templates/
│ └── *.tpl
├── api/ # Flask-Blueprints & App-Factory
│ ├── rag.py
│ ├── analytics.py
│ ├── utils.py
│ └── api.py
├── ingestion/
│ └── rss_ingest.py
├── storage/
│ └── duckdb_storage.py
├── retrieval/
│ └── hybrid_retrieval.py
│ └── cross_encoder_ranker.py
├── evaluation/
│ └── quality_evaluator.py
├── filter/
│ └── content_filter.py
├── logging_service/
│ └── kafka_config_and_logger.py
├── templates/
│ └── index.html
├── static/
│ ├── style.css
│ └── app.js
├── data/
│ └── rssfeed.duckdb
├── scripts/
│ └── recalc_importance.py
├── tests/
│ └── *.py
├── requirements.txt
├── Makefile
└── README.md


---

## Installation & Start

1. **Repo klonen**  
   bash
  ``` git clone https://github.com/<user>/rss-analyzer.git```
   ```cd rss-analyzer```

    Datenbank zurücksetzen (optional)

```rm -f data/rssfeed.duckdb```

Dependencies installieren

```pip install -r requirements.txt```

Docker-Services starten

```make build```      # Image bauen & alle Services starten
# oder einzeln:
```make up```         # = make build

Web-UI direkt lokal (ohne Kafka/Spark)

```python -m api.app```
# → http://localhost:5000

Tests

    ```pytest tests/```

Makefile-Befehle

# Build und Start
```make build```           # Image bauen und alle Services im Hintergrund starten
```make up ```             # Alias für make build
```make down```            # Alle Services stoppen und entfernen

# Logs
```make logs-api```        # API-Logs (alias: make log, make l)
```make logs-all```        # Logs aller Services
```make logs-kafka```      # Kafka-Logs
```make logs-prometheus``` # Prometheus-Logs
```make logs-grafana```    # Grafana-Logs

# Ingestion & Analytics
```make ingest```          # RSS-Ingestion im API-Container (stoppt Spark temporär)
```make recalc```          # Neuberechnung der article.importance via scripts/recalc_importance.py

# Weitere Aliase
```make log```             # Alias für make logs-api
```make l ```              # Alias für make logs-api

Neue Funktionen seit letztem Release

    Persistentes Question-Tracking

        Tabelle question_events in DuckDB speichert jede Suche

        /metrics-Endpoint für Prometheus

    Hybride Importance-Berechnung

        Methode recalc_importance() in duckdb_storage.py

        CLI-Script make recalc

    Erweitertes Analytics-Dashboard

        /analytics: Top-Fragen, Stunden-Verteilung, Artikel-Views

    ContentFilter Modul

        Themen- und Duplikatsfilterung vor Retrieval

    Qualitätsmetriken

        NDCG & MAP im quality_evaluator.py

Erweiterungsmöglichkeiten

    Observability & Alerts über Grafana/Prometheus

    Personalisierung via user_id/session_id

    Automatische Gewichtungsoptimierung (Bayes/Grid Search)

    Langzeit-Archivierung in BigQuery oder Data Warehouse
