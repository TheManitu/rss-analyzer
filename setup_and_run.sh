#!/bin/bash
# Datei: setup_and_run.sh
# Zweck: Setup und Start der RSS Answers App (lokal oder Docker)

set -e

# 1. Vorbereitung: Abhängigkeiten prüfen
command -v docker >/dev/null 2>&1 || { echo >&2 "Docker ist nicht installiert. Abbruch."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo >&2 "Docker-Compose ist nicht installiert. Abbruch."; exit 1; }

# 2. Verzeichnisstruktur prüfen
if [ ! -d "templates" ] || [ ! -d "static" ]; then
  echo "Verzeichnisse 'templates/' und/oder 'static/' fehlen. Bitte sicherstellen."
  exit 1
fi

# 3. Environment-Variablen prüfen oder setzen (optional aus .env)
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# 4. Docker starten
echo "→ Starte Docker-Umgebung…"
docker-compose up -d --build

# 5. Warten auf Dienste (Kafka, API)
echo "→ Warte auf Kafka-Startup…"
sleep 10

# 6. Einmalige Initialjobs
echo "→ Führe Topic-Zuordnung und Wichtigkeit-Rekalkulation aus…"
docker-compose exec api python scripts/recalc_topics.py || true
docker-compose exec api python scripts/recalc_importance.py || true

echo "✓ Setup abgeschlossen. Aufrufbar unter: http://localhost:5000"
echo "Verfügbare Seiten: /dashboard, /analytics, /audit"
