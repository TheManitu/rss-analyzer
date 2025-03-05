import duckdb
from rss_analyzer.config import DB_PATH

def create_table(incremental=False):
    """
    Erstellt die Tabelle 'articles'.
    Bei incremental=True werden alte Artikel gelöscht statt der gesamten Tabelle.
    Hinweis: Wir verzichten hier auf eine explizite ID-Spalte, da DuckDB einen impliziten `rowid` bereitstellt.
    """
    con = duckdb.connect(DB_PATH)
    if not incremental:
        con.execute("DROP TABLE IF EXISTS articles")
        con.execute("""
            CREATE TABLE articles (
                title TEXT,
                link TEXT,
                description TEXT,
                content TEXT,
                published DATE,
                topic TEXT,
                importance INTEGER DEFAULT 0,
                relevance INTEGER DEFAULT 0,
                UNIQUE(title, link)
            )
        """)
    else:
        con.execute("""
            DELETE FROM articles
            WHERE published < CURRENT_DATE - INTERVAL '14 days'
        """)
    con.close()

def insert_article(title, link, description, content, published, topic, importance, relevance):
    """Fügt einen Artikel in die Datenbank ein, falls er noch nicht vorhanden ist."""
    if article_exists(title, link):
        return
    con = duckdb.connect(DB_PATH)
    try:
        con.execute("""
            INSERT INTO articles (title, link, description, content, published, topic, importance, relevance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, link, description, content, published, topic, importance, relevance))
    except Exception as e:
        print(f"Fehler beim Einfügen des Artikels: {e}")
    finally:
        con.close()

def article_exists(title, link):
    """Überprüft, ob ein Artikel mit dem gegebenen Titel oder Link bereits existiert."""
    con = duckdb.connect(DB_PATH)
    res = con.execute("SELECT COUNT(*) FROM articles WHERE title = ? OR link = ?", (title, link)).fetchone()[0]
    con.close()
    return res > 0

def get_all_articles(time_filter='today'):
    """
    Liefert alle Artikel aus der DuckDB, sortiert nach Relevanz und Veröffentlichungsdatum.
    Es werden nur Artikel zurückgegeben, bei denen der Inhalt vorhanden ist.
    """
    con = duckdb.connect(DB_PATH)
    if time_filter == 'today':
        date_condition = "published = CURRENT_DATE"
    elif time_filter == '3_days':
        date_condition = "published >= CURRENT_DATE - INTERVAL '3 days'"
    elif time_filter == '7_days':
        date_condition = "published >= CURRENT_DATE - INTERVAL '7 days'"
    elif time_filter == '14_days':
        date_condition = "published >= CURRENT_DATE - INTERVAL '14 days'"
    else:
        date_condition = "published = CURRENT_DATE"
    
    query = f"""
    SELECT title, published, topic, importance, description, link, content, relevance
    FROM articles
    WHERE {date_condition} AND content IS NOT NULL AND TRIM(content) <> ''
    ORDER BY relevance DESC, published DESC
    """
    rows = con.execute(query).fetchall()
    con.close()
    articles = []
    for row in rows:
        articles.append({
            "title": row[0],
            "published": row[1],
            "topic": row[2],
            "importance": row[3],
            "description": row[4],
            "link": row[5],
            "content": row[6],
            "relevance": row[7]
        })
    return articles
