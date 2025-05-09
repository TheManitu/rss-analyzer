#!/usr/bin/env python3

import os
import duckdb
from pathlib import Path
from storage.duckdb_storage import DuckDBStorage
from config import DB_PATH

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_FILE = BASE_DIR / "storage" / "metrics_schema.sql"

def ensure_metrics_tables():
    sql = SCHEMA_FILE.read_text()
    conn = duckdb.connect(DB_PATH)
    conn.execute(sql)
    conn.close()
    print("✓ Metrik-Tabellen geprüft")

def main():
    ensure_metrics_tables()

    w_views   = float(os.getenv("W_VIEWS",   0.4))
    w_refs    = float(os.getenv("W_REFS",    0.5))
    w_flag    = float(os.getenv("W_FLAG",    0.1))
    w_content = float(os.getenv("W_CONTENT", 0.1))  # aktuell nicht verwendet

    print(f"→ Importance-Gewichte: views={w_views}, refs={w_refs}, flag={w_flag}")

    storage = DuckDBStorage(db_path=DB_PATH)
    storage.recalc_importance(
        w_views=w_views,
        w_refs=w_refs,
        w_flag=w_flag
    )


    print("✓ Importance erfolgreich neu berechnet.")

if __name__ == "__main__":
    main()
