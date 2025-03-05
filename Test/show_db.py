import duckdb

DB_PATH = "rssfeed.duckdb"

def show_all_articles():
    con = duckdb.connect(DB_PATH)
    # Hole die ersten 5 Artikel, sortiert nach Veröffentlichungsdatum (neueste zuerst)
    rows = con.execute("SELECT title, link, published, topic, relevance, content FROM articles ORDER BY published DESC LIMIT 5").fetchall()
    con.close()
    print("\n--- Aktuelle Artikel in der DB ---")
    for row in rows:
        print("Titel:", row[0])
        print("Quelle:", row[1])
        print("Veröffentlicht:", row[2])
        print("Themen:", row[3])
        print("Relevanz:", row[4])
        print("Content:", row[5])  # Hier wird der vollständige Inhalt angezeigt
        print("-" * 80)

if __name__ == "__main__":
    show_all_articles()
