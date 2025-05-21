from storage.duckdb_storage import DuckDBStorage
from keybert import KeyBERT

class KeywordExtractor:
    def __init__(self, db_path=None, model_name="all-MiniLM-L6-v2", top_n=5):
        self.storage = DuckDBStorage(db_path=db_path)
        self.extractor = KeyBERT(model=model_name)
        self.top_n = top_n

    def run(self, time_filter: str = '14_days'):
        articles = self.storage.get_all_articles(time_filter)
        for art in articles:
            text = f"{art['title']}. {art['description']} {art['content']}"
            kws = [kw for kw, _ in self.extractor.extract_keywords(text, top_n=self.top_n)]
            self.storage.upsert_article_keywords(art['link'], kws)
            print(f"[Keywords] {art['link']}: {kws}")

if __name__ == "__main__":
    extractor = KeywordExtractor()
    extractor.run()
