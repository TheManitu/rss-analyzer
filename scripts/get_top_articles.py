#!/usr/bin/env python3
import argparse
import json
from storage.duckdb_storage import DuckDBStorage

def get_top_articles(limit: int = 5):
    """
    Ruft die Top-Artikel von heute ab, sortiert nach Importance absteigend.
    """
    storage = DuckDBStorage()
    # Alle Artikel von heute laden (bereits nach importance sortiert)
    articles = storage.get_all_articles(time_filter='today')
    # Auf die gewünschte Anzahl kürzen
    return articles[:limit]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gibt die Top-N Artikel von heute basierend auf LLM-Importance aus"
    )
    parser.add_argument(
        "-n", "--number",
        type=int,
        default=5,
        help="Anzahl der Top-Artikel (Standard: 5)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Pfad zur JSON-Ausgabe (optional)"
    )
    args = parser.parse_args()

    top = get_top_articles(limit=args.number)
    if args.output:
        # JSON Export
        out = [
            {
                "title":      art["title"],
                "link":       art["link"],
                "published":  art["published"].isoformat() if hasattr(art["published"], "isoformat") else art["published"],
                "importance": float(art["importance"] or 0)
            }
            for art in top
        ]
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(out)} articles to {args.output}")
    else:
        # Konsolenausgabe
        for art in top:
            pub = art["published"].isoformat() if hasattr(art["published"], "isoformat") else art["published"]
            imp = art["importance"] or 0
            print(f"{pub} | {imp:5.3f} | {art['title']} → {art['link']}")
