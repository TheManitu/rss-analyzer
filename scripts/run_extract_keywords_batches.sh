#!/bin/bash

# Konfiguration
BATCH_SIZE=100
TOTAL_ARTIKEL=708
SERVICE_NAME=api

echo "🔁 Starte Keyword-Extraktion in Batches von $BATCH_SIZE Artikeln..."

for ((start=0; start<TOTAL_ARTIKEL; start+=BATCH_SIZE)); do
  end=$((start + BATCH_SIZE))
  if [ "$end" -gt "$TOTAL_ARTIKEL" ]; then
    end=$TOTAL_ARTIKEL
  fi

  echo "➡️ Bearbeite Artikel $start bis $end ..."
  docker-compose exec $SERVICE_NAME python scripts/extract_keywords.py --start "$start" --end "$end"

  if [ $? -ne 0 ]; then
    echo "❌ Fehler beim Batch $start–$end, abbrechen..."
    exit 1
  fi

  echo "✅ Batch $start–$end abgeschlossen"
done

echo "🎉 Alle Batches verarbeitet."
