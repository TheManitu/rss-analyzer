
# RSS Analyzer mit RAG

Dieses Open-Source-Projekt sammelt, bereinigt und analysiert RSS-Feed-Artikel lokal und stellt eine interaktive Web-UI zur Verfügung. Es kombiniert klassische ETL-Techniken mit einer Retrieval-Augmented Generation (RAG)-Pipeline.

---

## Änderungen seit letzter Version

- **Startup-Skip-Flags**: Neue Environment-Variablen zur feingranularen Steuerung, nun standardmäßig auf `false`, außer für `analyzer` und `dashboard`.
- **Makefile**: Ergänzt um dedizierte Targets für jeden Pipeline-Schritt (`ingest`, `keywords`, `topics` usw.) und Meta-Targets (`pipeline`, `all`).

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

```text
rss-analyzer/
├── docker/
│   └── docker-compose.yml     # Zookeeper, Kafka, Prometheus, Grafana, API, …
├── prompt_templates/
│   └── *.tpl
├── api/                       # Flask-Blueprints & App-Factory
│   ├── rag.py
│   ├── analytics.py
│   ├── utils.py
│   └── api.py
├── ingestion/
│   └── rss_ingest.py
├── storage/
│   └── duckdb_storage.py
├── retrieval/
│   ├── hybrid_retrieval.py
│   └── cross_encoder_ranker.py
├── evaluation/
│   └── quality_evaluator.py
├── filter/
│   └── content_filter.py
├── logging_service/
│   └── kafka_config_and_logger.py
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── app.js
├── data/
│   └── rssfeed.duckdb
├── scripts/
│   └── recalc_importance.py
├── tests/
│   └── *.py
├── requirements.txt
├── Makefile                  # neu hinzugefügt
└── README.md

Installation & Start

Repo klonen

    git clone https://github.com/<user>/rss-analyzer.git

    cd rss-analyzer

Datenbank zurücksetzen (optional)

    rm -f data/rssfeed.duckdb

Dependencies installieren

    pip install -r requirements.txt

Docker-Services starten

    make build    # Image bauen & alle Services starten

# oder einzeln:

    make up       # = make build

Web-UI lokal (ohne Kafka/Spark)

python -m api.app
# → http://localhost:5000

Tests

    pytest tests/

Docker-Compose Environment Variables

— Startup-Skip-Flags —
Steuern, ob einzelne Pipeline-Stages beim Container-Start übersprungen werden (Default false, außer analyzer und dashboard):

  environment:
    SKIP_INGEST_ON_STARTUP:       ${SKIP_INGEST_ON_STARTUP:-false}
    SKIP_KEYWORDS_ON_STARTUP:     ${SKIP_KEYWORDS_ON_STARTUP:-false}
    SKIP_TOPICS_ON_STARTUP:       ${SKIP_TOPICS_ON_STARTUP:-false}
    SKIP_RELEVANCE_ON_STARTUP:    ${SKIP_RELEVANCE_ON_STARTUP:-false}
    SKIP_SEGMENTATION_ON_STARTUP: ${SKIP_SEGMENTATION_ON_STARTUP:-false}
    SKIP_SUMMARIZATION_ON_STARTUP:${SKIP_SUMMARIZATION_ON_STARTUP:-false}
    SKIP_ANALYZER_ON_STARTUP:     ${SKIP_ANALYZER_ON_STARTUP:-true}
    SKIP_DASHBOARD_ON_STARTUP:    ${SKIP_DASHBOARD_ON_STARTUP:-true}

Makefile für Docker-basiertes Pipeline-Projekt

COMPOSE = docker-compose
SERV    = api

.PHONY: api build up down logs shell ingest keywords topics importance segmentation \
summarization analyzer dashboard pipeline all top-articles archive clean

# Show API logs
api:
	$(COMPOSE) logs -f $(SERV)

# ─── Docker-Lifecycle ─────────────────────────────────────────────────────────

build:
	$(COMPOSE) build

up: build
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs: up
	$(COMPOSE) logs -f $(SERV)

# Interaktive Shell im API-Container
shell: up
	$(COMPOSE) exec $(SERV) /bin/bash

# ─── Einzelne Pipeline-Schritte im laufenden Container ───────────────────────

ingest: up
	$(COMPOSE) exec -T $(SERV) python3 -m ingestion.rss_ingest

keywords: up
	$(COMPOSE) exec -T $(SERV) python3 pipeline/keyword_extraction_langaware.py

topics: up
	$(COMPOSE) exec -T $(SERV) python3 pipeline/topic_assignment.py

importance: up
	$(COMPOSE) exec -T $(SERV) python3 pipeline/relevance_scoring.py

segmentation: up
	$(COMPOSE) exec -T $(SERV) python3 pipeline/segmentation.py

summarization: up
	$(COMPOSE) exec -T $(SERV) python3 pipeline/summarization.py

analyzer: up
	$(COMPOSE) exec -T $(SERV) python3 pipeline/analyzer.py

dashboard: up
	$(COMPOSE) exec -T $(SERV) python3 pipeline/dashboard_generator.py

# ─── Komplett-Pipeline & Meta-Targets ────────────────────────────────────────

pipeline: ingest keywords topics importance segmentation summarization analyzer dashboard

all: up pipeline

# ─── Hilfs-Skripte im Container ───────────────────────────────────────────────

top-articles: up
	$(COMPOSE) exec -T $(SERV) python3 get_top_articles.py

archive: up
	$(COMPOSE) exec -T $(SERV) python3 archive_to_bigquery.py

# ─── Aufräumen ───────────────────────────────────────────────────────────────

clean:
	@echo "Docker builder und Volumes bereinigen..."
	docker builder prune --force
	docker volume prune --force

Makefile-Befehle

    ingest: RSS-Ingestion

    keywords: Keyword-Extraktion

    topics: Topic-Zuweisung

    importance: Importance-Scoring

    segmentation: Text-Segmentierung

    summarization: Zusammenfassung

    analyzer: Qualitätsanalyse

    dashboard: Dashboard-Erzeugung

    pipeline: Komplett-Pipeline

    all: up + pipeline

    clean: Aufräumen von Builder-Caches und Volumes
