#!/bin/bash
# run_scraper.sh – Startet den RSS Scraper

# Wechsle in das Hauptverzeichnis Deines Projektes (Passe den Pfad ggf. an)
cd /app || { echo "Verzeichnis /app nicht gefunden!"; exit 1; }

# Optional: Aktiviere das virtuelle Python-Environment, falls verwendet
# source venv/bin/activate

# Starte den Scraper; falls Dein Scraper als Modul in rss_analyzer implementiert ist:
python -m rss_analyzer.scraper

# Alternativ, falls scraper.py direkt ausführbar ist:
# ./scraper.py
