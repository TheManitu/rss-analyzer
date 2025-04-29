# storage/duckdb_storage.py

import duckdb
from config import DB_PATH

class DuckDBStorage:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.create_table()

    def connect(self, read_only: bool = False):
        return duckdb.connect(self.db_path, read_only=read_only)

    def create_table(self):
        """
        Legt die articles-Tabelle an (ohne Auto-Increment).
        Entfernt automatisch alte Artikel (>14 Tage).
        """
        con = self.connect()
        # Artikeltabelle
        con.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                title TEXT,
                link TEXT,
                description TEXT,
                content TEXT,
                summary TEXT DEFAULT '',
                translation TEXT DEFAULT '',
                published DATE,
                topic TEXT,
                importance DOUBLE DEFAULT 0,
                relevance INTEGER DEFAULT 0,
                UNIQUE(title, link)
            );
        """)
        # Alte Artikel entfernen
        con.execute("""
            DELETE FROM articles
            WHERE published < CURRENT_DATE - INTERVAL '14 days';
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

    def insert_article(
        self,
        title: str,
        link: str,
        description: str,
        content: str,
        summary: str,
        translation: str,
        published,
        topic: str,
        importance: float,
        relevance: int
    ):
        """
        Fügt einen neuen Artikel ein, wenn er noch nicht existiert.
        """
        if self.article_exists(title, link):
            return
        con = self.connect()
        con.execute(
            """
            INSERT INTO articles
                (title, link, description, content, summary, translation,
                 published, topic, importance, relevance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
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

    def get_all_articles(self, time_filter: str = '14_days') -> list:
        """
        Liefert alle Artikel als Liste von Dicts zurück (für die UI).
        """
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
            ORDER BY importance DESC, published DESC;
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

    def fetch_passages(self, time_filter: str = '14_days') -> list:
        """
        Alias auf get_all_articles (für den Retriever).
        """
        return self.get_all_articles(time_filter)

    def execute(self, sql: str):
        """
        Utility für Ad-hoc-SQL (z.B. Cleanup oder Analysen).
        """
        con = self.connect()
        con.execute(sql)
        con.close()

    def recalc_importance(self, w_views=0.4, w_refs=0.5, w_flag=0.1):
        """
        Berechnet die 'importance' neu nach dem Modell:
          importance = w_views * norm_views
                     + w_refs  * norm_refs
                     - w_flag  * flag_rate

        norm_views = view_count / max(view_count)
        norm_refs  = ref_count  / max(ref_count)
        flag_rate  = Anteil geflaggter Antworten pro Artikel

        Erwartet:
         - Tabelle `article_metrics(link TEXT PRIMARY KEY, view_count INT, ref_count INT, last_updated TIMESTAMP)`
         - Tabelle `answer_quality_flags(link TEXT, flag BOOLEAN)` (optional; falls nicht vorhanden, setze w_flag=0)
        """
        con = self.connect()

        # Maximalwerte ermitteln (Vermeidung von Division durch 0)
        max_views, max_refs = con.execute("""
            SELECT
              COALESCE(MAX(view_count),1),
              COALESCE(MAX(ref_count),1)
            FROM article_metrics;
        """).fetchone()

        # importance für alle Artikel aktualisieren
        con.execute(f"""
            UPDATE articles
            SET importance = (
                -- normalisierte Views
                COALESCE((
                    SELECT view_count FROM article_metrics
                    WHERE link = articles.link
                ), 0) / {max_views} * {w_views}

                -- normalisierte Frage-Refs
              + COALESCE((
                    SELECT ref_count FROM article_metrics
                    WHERE link = articles.link
                ), 0) / {max_refs} * {w_refs}

                -- Qualitätsmalus durch Flag-Rate
              - COALESCE((
                    SELECT COUNT(*) * 1.0
                    FROM answer_quality_flags q
                    WHERE q.link = articles.link
                      AND q.flag = TRUE
                ) / NULLIF((
                    SELECT ref_count FROM article_metrics
                    WHERE link = articles.link
                ), 0), 0) * {w_flag}
            );
        """)
        con.close()
