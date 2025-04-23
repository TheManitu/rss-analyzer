import duckdb
from config import DB_PATH

class DuckDBStorage:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.create_table()

    def connect(self, read_only=False):
        return duckdb.connect(self.db_path, read_only=read_only)

    def create_table(self):
        con = self.connect()
        # Initiale Tabelle anlegen
        con.execute("""
            CREATE TABLE IF NOT EXISTS articles (
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
        # Spalten summary und translation hinzufügen, falls sie fehlen
        try:
            con.execute("ALTER TABLE articles ADD COLUMN summary TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            con.execute("ALTER TABLE articles ADD COLUMN translation TEXT DEFAULT ''")
        except Exception:
            pass
        # Alte Artikel automatisch entfernen (>14 Tage)
        con.execute("""
            DELETE FROM articles
            WHERE published < CURRENT_DATE - INTERVAL '14 days'
        """)
        con.close()

    def article_exists(self, title: str, link: str) -> bool:
        con = self.connect(read_only=True)
        count = con.execute(
            "SELECT COUNT(*) FROM articles WHERE LOWER(title)=LOWER(?) OR LOWER(link)=LOWER(?)",
            (title, link)
        ).fetchone()[0]
        con.close()
        return count > 0

    def insert_article(self, title, link, description, content,
                       summary, translation, published, topic, importance, relevance):
        if self.article_exists(title, link):
            return
        con = self.connect()
        con.execute(
            """
            INSERT INTO articles
                (title, link, description, content, summary, translation,
                 published, topic, importance, relevance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, link, description, content, summary, translation,
             published, topic, importance, relevance)
        )
        con.close()

    def get_all_links(self) -> list:
        """
        Liefert alle in der DB gespeicherten Links zurück.
        """
        con = self.connect(read_only=True)
        rows = con.execute("SELECT link FROM articles").fetchall()
        con.close()
        return [r[0] for r in rows]

    def get_all_articles(self, time_filter='14_days'):
        con = self.connect(read_only=True)
        if time_filter == 'today':
            cond = "published = CURRENT_DATE"
        elif time_filter == '3_days':
            cond = "published >= CURRENT_DATE - INTERVAL '3 days'"
        elif time_filter == '7_days':
            cond = "published >= CURRENT_DATE - INTERVAL '7 days'"
        elif time_filter == '14_days':
            cond = "published >= CURRENT_DATE - INTERVAL '14 days'"
        else:
            cond = "1=1"
        rows = con.execute(f"""
            SELECT title, published, topic, importance,
                   description, link, content, summary, translation, relevance
            FROM articles
            WHERE {cond}
            ORDER BY relevance DESC, published DESC
        """).fetchall()
        con.close()

        articles = []
        for t, p, topic, imp, desc, link, content, summ, trans, rel in rows:
            articles.append({
                "title":       t,
                "published":   p,
                "topic":       topic,
                "importance":  imp,
                "description": desc,
                "link":        link,
                "content":     content,
                "summary":     summ,
                "translation": trans,
                "relevance":   rel
            })
        return articles

    def fetch_passages(self, time_filter='14_days'):
        return self.get_all_articles(time_filter)

    def execute(self, sql: str):
        # Utility für Ad-hoc-SQL (z.B. Cleanup)
        con = self.connect()
        con.execute(sql)
        con.close()
