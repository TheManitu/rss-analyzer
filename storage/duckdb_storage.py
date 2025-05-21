# storage/duckdb_storage.py

import duckdb
import pickle
import logging
from datetime import date, timedelta
from config import DB_PATH
from pipeline.ingestion_filter import IngestionFilter
from api.utils import count_rejected_article

# Logger für Storage-Validierung
logger = logging.getLogger(__name__)

class DuckDBStorage:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._create_articles_table()
        self._ensure_keywords_table()
        self._ensure_sections_table()

    def connect(self, read_only: bool = False):
        return duckdb.connect(self.db_path, read_only=read_only)

    def execute(self, sql: str):
        con = self.connect()
        con.execute(sql)
        con.close()

    def _create_articles_table(self):
        con = self.connect()
        con.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                title TEXT,
                link TEXT PRIMARY KEY,
                description TEXT,
                content TEXT,
                summary TEXT DEFAULT '',
                translation TEXT DEFAULT '',
                published DATE,
                topic TEXT,
                importance DOUBLE,
                relevance INTEGER DEFAULT 0
            );
        """)
        con.close()

    def _ensure_keywords_table(self):
        con = self.connect()
        con.execute("""
            CREATE TABLE IF NOT EXISTS article_keywords (
                link    TEXT,
                keyword TEXT,
                UNIQUE(link, keyword)
            );
        """)
        con.close()

    def _ensure_sections_table(self):
        con = self.connect()
        con.execute("""
            CREATE TABLE IF NOT EXISTS article_sections (
                link            TEXT,
                section_idx     INTEGER,
                section_text    TEXT,
                section_keyword TEXT,
                embedding       BLOB,
                PRIMARY KEY(link, section_idx)
            );
        """)
        con.close()

    # --- Artikel-Operationen ---

    def get_all_links(self) -> list[str]:
        con = self.connect(read_only=True)
        rows = con.execute("SELECT link FROM articles").fetchall()
        con.close()
        return [r[0] for r in rows]

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
        # Validierung anhand Ingestion-Filter
        valid, reason = IngestionFilter.validate(title, content, topic)
        if not valid:
            logger.info(f"Verwerfe Artikel {link} in Storage: {reason}")
            count_rejected_article()
            return False
        # Duplikatscheck
        if self.article_exists(title, link):
            return False
        # Insert
        con = self.connect()
        con.execute("""
            INSERT INTO articles
                (title, link, description, content, summary, translation,
                 published, topic, importance, relevance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (title, link, description, content, summary, translation,
               published, topic, importance, relevance))
        con.close()
        return True

    def insert_summary(self, link: str, title: str, description: str,
                       summary: str, published: date):
        con = self.connect()
        con.execute("""
            INSERT OR REPLACE INTO articles
                (link, title, description, summary, published)
            VALUES (?, ?, ?, ?, ?);
        """, (link, title, description, summary, published))
        con.close()

    def get_all_articles(self, time_filter: str = '14_days') -> list[dict]:
        con = self.connect(read_only=True)
        cond = {
            'today':   "published = CURRENT_DATE",
            '3_days':  "published >= CURRENT_DATE - INTERVAL '3 days'",
            '7_days':  "published >= CURRENT_DATE - INTERVAL '7 days'",
            '14_days': "published >= CURRENT_DATE - INTERVAL '14 days'"
        }.get(time_filter, "1=1")
        rows = con.execute(f"""
            SELECT title, link, description, content, summary, translation,
                   published, topic, importance, relevance
            FROM articles
            WHERE {cond}
            ORDER BY importance DESC NULLS LAST, published DESC;
        """).fetchall()
        con.close()
        cols = ["title", "link", "description", "content", "summary",
                "translation", "published", "topic", "importance", "relevance"]
        return [dict(zip(cols, row)) for row in rows]

    # --- Keywords ---

    def upsert_article_keywords(self, link: str, keywords: list[str]):
        con = self.connect()
        con.execute("DELETE FROM article_keywords WHERE link = ?", (link,))
        for kw in set(k.lower() for k in keywords if k.strip()):
            con.execute(
                "INSERT INTO article_keywords (link, keyword) VALUES (?, ?)",
                (link, kw)
            )
        con.close()

    def get_article_keywords(self, link: str) -> list[str]:
        con = self.connect(read_only=True)
        rows = con.execute(
            "SELECT keyword FROM article_keywords WHERE link = ?", (link,)
        ).fetchall()
        con.close()
        return [r[0] for r in rows]

    def update_keywords(self, link: str, keywords: list[str]):
        return self.upsert_article_keywords(link, keywords)

    # --- Sections & Embeddings ---

    def upsert_article_sections(self, link: str, sections: list[dict]):
        con = self.connect()
        con.execute("DELETE FROM article_sections WHERE link = ?", (link,))
        for sec in sections:
            blob = pickle.dumps(sec['embedding'], protocol=pickle.HIGHEST_PROTOCOL)
            con.execute("""
                INSERT INTO article_sections
                    (link, section_idx, section_text, section_keyword, embedding)
                VALUES (?, ?, ?, ?, ?);
            """, (link, sec['idx'], sec['text'], sec['keyword'], blob))
        con.close()

    def get_article_sections(self, link: str) -> list[dict]:
        con = self.connect(read_only=True)
        rows = con.execute("""
            SELECT section_idx, section_text, section_keyword, embedding
            FROM article_sections
            WHERE link = ?
            ORDER BY section_idx;
        """, (link,)).fetchall()
        con.close()
        result = []
        for idx, text, keyword, blob in rows:
            emb = pickle.loads(blob)
            result.append({
                'idx': idx,
                'text': text,
                'keyword': keyword,
                'embedding': emb
            })
        return result

    def get_articles_by_topic(self, topic: str, time_filter: str = None) -> list[dict]:
        con = self.connect(read_only=True)
        if time_filter:
            days = int(time_filter.split('_')[0])
            cutoff = date.today() - timedelta(days=days)
            cursor = con.execute(
                "SELECT * FROM articles WHERE topic = ? AND published >= ?",
                (topic, cutoff)
            )
        else:
            cursor = con.execute(
                "SELECT * FROM articles WHERE topic = ?", (topic,)
            )
        rows = cursor.fetchall()
        cols = [col[0] for col in cursor.description]
        con.close()
        return [dict(zip(cols, row)) for row in rows]


def get_article_metadata(link: str) -> dict:
    """
    Liefert Metadaten für einen Artikel:
    - publication_date (aus articles.published)
    - views, ref_count (aus article_metrics)
    """
    db = DuckDBStorage()
    con = db.connect(read_only=True)

    row = con.execute(
        "SELECT published FROM articles WHERE link = ?",
        (link,)
    ).fetchone()
    publication_date = row[0] if row else None

    # Tabelle article_metrics muss separat angelegt werden
    stats = con.execute(
        "SELECT view_count, ref_count FROM article_metrics WHERE link = ?",
        (link,)
    ).fetchone()
    views     = stats[0] if stats else 0
    ref_count = stats[1] if stats else 0

    con.close()
    return {
        "publication_date": publication_date,
        "views":            views,
        "ref_count":        ref_count
    }
