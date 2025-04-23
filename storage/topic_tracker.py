import duckdb
from config import DB_PATH

def create_topic_table():
    con = duckdb.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            topic TEXT PRIMARY KEY,
            article_count INTEGER DEFAULT 0,
            is_complete BOOLEAN DEFAULT FALSE,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.close()

def update_topic(topic_name, delta=1):
    con = duckdb.connect(DB_PATH)
    existing = con.execute(
        "SELECT article_count FROM topics WHERE topic = ?", (topic_name,)
    ).fetchone()
    if existing:
        new_count = existing[0] + delta
        is_complete = new_count >= 3
        con.execute(
            "UPDATE topics SET article_count = ?, is_complete = ?, last_updated = CURRENT_TIMESTAMP WHERE topic = ?",
            (new_count, is_complete, topic_name)
        )
    else:
        is_complete = delta >= 3
        con.execute(
            "INSERT INTO topics (topic, article_count, is_complete) VALUES (?, ?, ?)",
            (topic_name, delta, is_complete)
        )
    con.close()

def get_all_topics():
    con = duckdb.connect(DB_PATH)
    rows = con.execute(
        "SELECT topic, article_count, is_complete, last_updated FROM topics"
    ).fetchall()
    con.close()
    topics = []
    for topic, count, complete, last in rows:
        topics.append({
            "topic": topic,
            "article_count": count,
            "is_complete": complete,
            "last_updated": last
        })
    return topics

def print_topic_overview():
    topics = get_all_topics()
    print("Themenübersicht:")
    for t in topics:
        status = "abgedeckt" if t["is_complete"] else "fehlend"
        print(f" - {t['topic']}: {t['article_count']} Artikel ({status})")
