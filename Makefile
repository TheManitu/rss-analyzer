# Makefile für Docker-basiertes Pipeline-Projekt

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

keywordsold: up
	$(COMPOSE) exec -T $(SERV) python3 pipeline/keyword_extraction.py

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
