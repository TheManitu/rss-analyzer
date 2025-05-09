import duckdb
from config import DB_PATH
from sentence_transformers import SentenceTransformer, util


class DuckDBStorage:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.create_table()
        self._ensure_keywords_table()

    def connect(self, read_only: bool = False):
        return duckdb.connect(self.db_path, read_only=read_only)

    def create_table(self):
        con = self.connect()
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
        con.execute("""
            DELETE FROM articles
            WHERE published < CURRENT_DATE - INTERVAL '14 days';
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

    def article_exists(self, title: str, link: str) -> bool:
        con = self.connect(read_only=True)
        count = con.execute(
            "SELECT COUNT(*) FROM articles WHERE LOWER(title)=LOWER(?) OR LOWER(link)=LOWER(?)",
            (title, link)
        ).fetchone()[0]
        con.close()
        return count > 0

    def insert_article(self, title, link, description, content, summary, translation, published, topic, importance, relevance):
        if self.article_exists(title, link):
            return
        con = self.connect()
        con.execute("""
            INSERT INTO articles
                (title, link, description, content, summary, translation,
                 published, topic, importance, relevance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (title, link, description, content, summary, translation,
              published, topic, importance, relevance))
        con.close()

    def get_all_links(self) -> list:
        con = self.connect(read_only=True)
        rows = con.execute("SELECT link FROM articles").fetchall()
        con.close()
        return [r[0] for r in rows]

    def get_all_articles(self, time_filter: str = '14_days') -> list:
        con = self.connect(read_only=True)
        cond = {
            'today':   "published = CURRENT_DATE",
            '3_days':  "published >= CURRENT_DATE - INTERVAL '3 days'",
            '7_days':  "published >= CURRENT_DATE - INTERVAL '7 days'",
            '14_days': "published >= CURRENT_DATE - INTERVAL '14 days'"
        }.get(time_filter, "1=1")

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
        return self.get_all_articles(time_filter)

    def execute(self, sql: str):
        con = self.connect()
        con.execute(sql)
        con.close()

    def recalc_importance(self, w_views=0.4, w_refs=0.5, w_flag=0.1):
        con = self.connect()
        max_views, max_refs = con.execute("""
            SELECT
              COALESCE(MAX(view_count),1),
              COALESCE(MAX(ref_count),1)
            FROM article_metrics;
        """).fetchone()

        con.execute(f"""
            UPDATE articles
            SET importance = (
                COALESCE((SELECT view_count FROM article_metrics WHERE link = articles.link), 0) / {max_views} * {w_views}
              + COALESCE((SELECT ref_count  FROM article_metrics WHERE link = articles.link), 0) / {max_refs} * {w_refs}
              - COALESCE((
                    SELECT COUNT(*)*1.0
                    FROM answer_quality_events q
                    WHERE q.link = articles.link AND q.flag = TRUE
                ) / NULLIF((SELECT ref_count FROM article_metrics WHERE link = articles.link), 0), 0) * {w_flag}
            );
        """)
        con.close()

    def upsert_article_keywords(self, link: str, keywords: list, conn=None):
        """
        Speichert pro Artikel die extrahierten Keywords.
        Alte Keywords für den Link werden vorher gelöscht.
        Optional: Verbindung mitliefern, um mehrfach-Öffnungen zu vermeiden.
        """
        own_con = False
        if conn is None:
            conn = self.connect()
            own_con = True

        conn.execute("DELETE FROM article_keywords WHERE link = ?", (link,))
        for kw in set(k.lower() for k in keywords if k.strip()):
            conn.execute(
                "INSERT INTO article_keywords (link, keyword) VALUES (?, ?)",
                (link, kw)
            )

        if own_con:
            conn.close()

    def get_matching_links(self, query_terms: list) -> set:
        if not query_terms:
            return set()
        con = self.connect(read_only=True)
        terms = [t.lower() for t in query_terms if t.strip()]
        placeholders = ",".join("?" for _ in terms)
        rows = con.execute(
            f"SELECT DISTINCT link FROM article_keywords WHERE keyword IN ({placeholders})",
            tuple(terms)
        ).fetchall()
        con.close()
        return {r[0] for r in rows}

    def get_matching_links_advanced(self, query_terms: list[str], top_n: int = 10) -> list[str]:
        """
        Kombiniert Keyword-Matching und semantische Ähnlichkeit zur Artikelauswahl.
        Gibt die besten Links zurück.
        """
        embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        # Schritt 1: Alle Artikel laden
        con = self.connect(read_only=True)
        rows = con.execute("""
            SELECT link, title, summary, content
            FROM articles
        """).fetchall()
        con.close()

        results = []
        query_text = " ".join(query_terms)
        query_emb = embedder.encode(query_text, normalize_embeddings=True)

        for link, title, summary, content in rows:
            text = f"{title} {summary or ''} {content or ''}"
            keyword_score = sum(1 for term in query_terms if term in text.lower())
            if keyword_score == 0:
                continue

            emb = embedder.encode(text, normalize_embeddings=True)
            sim_score = float(util.cos_sim(query_emb, emb)[0])
            combined_score = 0.7 * sim_score + 0.3 * min(keyword_score / 5.0, 1.0)
            results.append((link, combined_score))

        results.sort(key=lambda x: x[1], reverse=True)
        return [link for link, _ in results[:top_n]]


def get_article_metadata(link: str) -> dict:
    db = DuckDBStorage()
    con = db.connect(read_only=True)

    row = con.execute("SELECT published FROM articles WHERE link = ?", (link,)).fetchone()
    pub_date = row[0] if row else None

    stats = con.execute("SELECT view_count, ref_count FROM article_metrics WHERE link = ?", (link,)).fetchone()
    views     = stats[0] if stats else 0
    ref_count = stats[1] if stats else 0

    con.close()
    return {
        "publication_date": pub_date,
        "views":            views,
        "ref_count":        ref_count
    }
