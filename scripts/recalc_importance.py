#!/usr/bin/env python3
"""
Skript zum Neuberechnen der 'importance'-Spalte in der DuckDB.
1. Legt per metrics_schema.sql die Tabellen article_metrics und answer_quality_flags an (wenn nicht vorhanden).
2. Ruft DuckDBStorage.recalc_importance() auf, um die importance-Spalte in articles neu zu setzen.
Usage:
  docker-compose exec api python scripts/recalc_importance.py
"""

import os
import duckdb
from pathlib import Path
from storage.duckdb_storage import DuckDBStorage
from config import DB_PATH

# Pfad zum metrics_schema.sql im storage-Verzeichnis
BASE_DIR    = Path(__file__).resolve().parent.parent
SCHEMA_FILE = BASE_DIR / "storage" / "metrics_schema.sql"

def ensure_metrics_tables():
    """
    Liest das SQL-Skript metrics_schema.sql ein und führt es gegen die DuckDB aus,
    um die Tabellen article_metrics und answer_quality_flags zu erstellen.
    """
    sql = SCHEMA_FILE.read_text()
    conn = duckdb.connect(DB_PATH)
    conn.execute(sql)
    conn.close()
    print("✓ Metrik-Tabellen article_metrics und answer_quality_flags sind vorhanden (oder wurden angelegt).")

if __name__ == "__main__":
    # 1) Metrik-Tabellen anlegen, falls fehlend
    ensure_metrics_tables()

    # 2) Importance neu berechnen
    storage = DuckDBStorage(db_path=DB_PATH)

    # Gewichtungen über ENV-Variablen oder Default-Werte
    w_views = float(os.getenv("W_VIEWS", 0.4))
    w_refs  = float(os.getenv("W_REFS",  0.5))
    w_flag  = float(os.getenv("W_FLAG",  0.1))

    storage.recalc_importance(
        w_views=w_views,
        w_refs =w_refs,
        w_flag =w_flag
    )
    print(f"✓ importance neu berechnet (w_views={w_views}, w_refs={w_refs}, w_flag={w_flag})")
