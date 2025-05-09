# Makefile für RSS Analyzer mit Docker & Scripts

# Standard-Service-Name
SERVICE_API := api

.PHONY: build up down logs-api logs-all ingest \
        recalc_importance recalc_topics optimize_weights \
        archive_to_bigquery test extract_keywords \
        api log l keywords all top-articles clean

# Docker-Image bauen
build:
	docker-compose build

# All Services starten (im Hintergrund)
up: build
	docker-compose up --build -d

# Alle Services stoppen und entfernen
down:
	docker-compose down

# Logs
logs-api:
	docker-compose logs -f $(SERVICE_API)

logs-all:
	docker-compose logs -f

# RSS-Ingestion im API-Container
ingest:
	docker-compose exec $(SERVICE_API) python -m ingestion.rss_ingest

# Keywords aus Artikeln extrahieren
extract_keywords:
	@echo "Extrahiere Keywords fuer alle Artikel"
	docker-compose exec api python scripts/extract_keywords.py --start 0 --end 100

# Topics für alle Artikel neu zuordnen
recalc_topics:
	@echo "Weise Artikel einem Thema zu"
	docker-compose exec $(SERVICE_API) python scripts/recalc_topics.py

# Importance neu berechnen
recalc_importance:
	@echo "Berechne Importance neu"
	docker-compose exec $(SERVICE_API) python scripts/recalc_importance.py

# Top-Artikel nach importance exportieren
top-articles:
	@echo "Ermittle Top-Artikel"
	docker-compose exec $(SERVICE_API) python scripts/get_top_articles.py -n 20 -d 14 -o data/top_articles.json

# Gewichte optimieren (Grid-Search)
optimize_weights:
	docker-compose exec $(SERVICE_API) python scripts/optimize_weights.py

# Tabellen nach BigQuery exportieren
archive_to_bigquery:
	docker-compose exec $(SERVICE_API) python scripts/archive_to_bigquery.py

# Tests im API-Container ausführen
test:
	docker-compose exec $(SERVICE_API) pytest

# 🧠 Alles in richtiger Reihenfolge: Keywords, Topics, Importance, Top-Export
all: extract_keywords recalc_topics recalc_importance top-articles
	@echo "✅ Alle Artikel bewertet, verschlagwortet und Top-Artikel exportiert."

# Cleanup optional
clean:
	@echo "Lösche temporaere Dateien (optional anpassen)"
	@docker builder prune --force
	@docker volume prune --force

# === Alias-Ziele ===
api: logs-api
log: logs-api
l: logs-api
keywords: extract_keywords
