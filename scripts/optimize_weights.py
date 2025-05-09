#!/usr/bin/env python3
"""
Grid-Search über (w_views, w_refs, w_flag) unter der Nebenbedingung
w_views + w_refs + w_flag = 1, um die Fehlerquadratsumme (MSE)
zwischen predicted importance und actual importance (articles.importance)
zu minimieren.

Usage:
  make optimize_weights
  docker-compose exec api python scripts/optimize_weights.py
"""

import os
import sys
import duckdb
import numpy as np
from itertools import product

# Pfad zur DB aus ENV oder Default
DB = os.getenv("DB_PATH", "/app/data/rssfeed.duckdb")

def load_metrics():
    """
    Lädt:
      - actual_imp: die in articles.importance gespeicherte Importance
      - view_count, ref_count aus article_metrics
      - flag_rate aus answer_quality_events
    """
    con = duckdb.connect(DB)
    df = con.execute("""
        SELECT
          a.link,
          a.importance       AS actual_imp,
          COALESCE(m.view_count, 0) AS view_count,
          COALESCE(m.ref_count,  0) AS ref_count,
          -- Flag-Rate = #TRUE Flags / ref_count
          COALESCE(q.true_flags, 0) * 1.0 /
            NULLIF(COALESCE(m.ref_count,0), 0) AS flag_rate
        FROM articles a
        LEFT JOIN article_metrics m
          ON m.link = a.link
        LEFT JOIN (
          SELECT link, COUNT(*) AS true_flags
          FROM answer_quality_events
          WHERE flag = TRUE
          GROUP BY link
        ) q ON q.link = a.link;
    """).df()
    con.close()
    return df

def predict_importance(df, wv, wr, wf):
    """
    Rechnet predicted importance:
      wv * norm_views + wr * norm_refs - wf * flag_rate
    Normiert view_count und ref_count jeweils auf [0,1].
    """
    max_v = df['view_count'].max() or 1.0
    max_r = df['ref_count'].max()  or 1.0
    df['norm_views'] = df['view_count'] / max_v
    df['norm_refs']  = df['ref_count']  / max_r
    return wv * df['norm_views'] + wr * df['norm_refs'] - wf * df['flag_rate']

def main():
    print("🔄 Lade Metriken aus DuckDB…")
    df = load_metrics()

    # Falls keine Daten, Abbruch mit Standard-Gewichten
    if df.empty:
        print("⚠️ Keine historischen Metriken gefunden. Verwende Standards:")
        print("   W_VIEWS=0.4, W_REFS=0.5, W_FLAG=0.1")
        sys.exit(0)

    best_mse    = float('inf')
    # Start mit euren Default-Gewichten, damit nie None formatiert wird
    best_params = (0.4, 0.5, 0.1)

    # Schrittweite 0.1, wv, wr ∈ [0,1], wf = 1 - wv - wr
    grid = np.linspace(0, 1, 11)
    for wv, wr in product(grid, repeat=2):
        wf = 1.0 - wv - wr
        if wf < 0:
            continue
        preds = predict_importance(df.copy(), wv, wr, wf)
        # mse: falls preds leer, bleibt worst_score
        mse = float(((preds - df['actual_imp'])**2).mean()) if len(preds) else float('inf')
        if mse < best_mse:
            best_mse    = mse
            best_params = (wv, wr, wf)

    wv, wr, wf = best_params
    print("\n🏆 Beste Gewichte (sum = 1):")
    print(f"  w_views = {wv:.2f}")
    print(f"  w_refs  = {wr:.2f}")
    print(f"  w_flag  = {wf:.2f}")
    print(f"  MSE     = {best_mse:.6f}")

    print("\nSetze diese Werte in dein Environment bzw. docker-compose.yml:")
    print(f"  - IMPORTANCE_RECALC_VIEWS={wv:.2f}")
    print(f"  - IMPORTANCE_RECALC_REFS ={wr:.2f}")
    print(f"  - IMPORTANCE_RECALC_FLAG ={wf:.2f}")

if __name__ == "__main__":
    main()
