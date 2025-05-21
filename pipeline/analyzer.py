import pandas as pd
from storage.duckdb_storage import DuckDBStorage

class DataAnalyzer:
    def __init__(self, db_path=None):
        self.storage = DuckDBStorage(db_path=db_path)

    def run(self):
        con = self.storage.connect(read_only=True)
        df = con.execute("""
            SELECT link, topic, importance, summary,
                   (SELECT COUNT(*) FROM article_keywords k WHERE k.link = a.link) AS kw_count,
                   (SELECT COUNT(*) FROM article_sections s WHERE s.link = a.link) AS sec_count
            FROM articles a
        """).fetch_df()
        con.close()

        issues = []
        for _, row in df.iterrows():
            if not row['topic']:
                issues.append((row['link'], "Kein Topic zugewiesen"))
            if pd.isna(row['importance']):
                issues.append((row['link'], "Keine Importance"))
            if not isinstance(row['summary'], str) or len(row['summary'].split()) < 5:
                issues.append((row['link'], "Summary zu kurz oder fehlt"))
            if row['kw_count'] < 3:
                issues.append((row['link'], "Weniger als 3 Keywords"))
            if row['sec_count'] == 0:
                issues.append((row['link'], "Keine Sektionen gebildet"))
        # Ausgabe
        for link, msg in issues:
            print(f"[Analyzer-Fehler] {link}: {msg}")

if __name__ == "__main__":
    DataAnalyzer().run()
