#!/usr/bin/env python3
import os
import duckdb
import json
from datetime import date
from config import DB_PATH

def get_top_articles(limit: int = 10, days_window: int = 14):
    con = duckdb.connect(DB_PATH, read_only=True)
    # Optional: zuerst importance neu berechnen, wenn Du das Modell angepasst hast
    # con.execute("CALL recalc_importance();")

    # Wähle Artikel der letzten X Tage, sortiere nach importance absteigend
    query = f"""
        SELECT title, link, published, importance
        FROM articles
        WHERE published >= CURRENT_DATE - INTERVAL '{days_window} days'
        ORDER BY importance DESC
        LIMIT {limit};
    """
    rows = con.execute(query).fetchall()
    con.close()
    return rows

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Gibt die Top-Artikel nach importance aus"
    )
    parser.add_argument("-n", "--number", type=int, default=10,
                        help="Anzahl der Top-Artikel")
    parser.add_argument("-d", "--days", type=int, default=14,
                        help="Zeitraum (Tage) zurück")
    parser.add_argument("-o", "--output", type=str,
                        help="Pfad zur JSON-Ausgabe (optional)")
    args = parser.parse_args()

    top = get_top_articles(limit=args.number, days_window=args.days)
    if args.output:
        # JSON export
        out = [
            {
                "title": t,
                "link": l,
                "published": p.isoformat(),
                "importance": float(imp)
            }
            for t, l, p, imp in top
        ]
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(out)} articles to {args.output}")
    else:
        # Konsolenausgabe
        for title, link, published, importance in top:
            print(f"{published} | {importance:.3f} | {title} → {link}")
