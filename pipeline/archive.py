#!/usr/bin/env python3
"""
Exportiere ausgewählte DuckDB-Tabellen nach BigQuery.

Usage:
  make archive_to_bigquery
  oder:
  docker-compose exec api python scripts/archive_to_bigquery.py
"""

import os
import duckdb
import pandas as pd
from google.cloud import bigquery

# Konfiguration aus ENV
DB_PATH    = os.getenv("DB_PATH", "/app/data/rssfeed.duckdb")
BQ_PROJECT = os.getenv("BQ_PROJECT")
BQ_DATASET = os.getenv("BQ_DATASET")

def export_table(con, table_name: str):
    """
    Lädt Tabelle als Pandas-DataFrame und schreibt sie nach BigQuery.
    """
    print(f"→ Exportiere Tabelle {table_name} …")
    df = con.execute(f"SELECT * FROM {table_name}").df()
    client   = bigquery.Client(project=BQ_PROJECT)
    table_id = f"{BQ_PROJECT}.{BQ_DATASET}.{table_name}"
    job_cfg  = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    job      = client.load_table_from_dataframe(df, table_id, job_cfg)
    job.result()
    print(f"✓ {len(df)} Zeilen: {table_id}")

def main():
    if not BQ_PROJECT or not BQ_DATASET:
        raise RuntimeError("BQ_PROJECT und BQ_DATASET müssen als ENV gesetzt sein")
    con = duckdb.connect(DB_PATH)
    print(f"✅ Verbunden: {DB_PATH}")
    # Liste der zu exportierenden Tabellen
    tables = [
        "articles",
        "article_metrics",
        "question_events",
        "answer_quality_events"
    ]
    for tbl in tables:
        export_table(con, tbl)
    con.close()
    print("\n✅ Alle Exporte abgeschlossen.")

if __name__ == "__main__":
    main()
