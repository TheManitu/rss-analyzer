from sklearn.cluster import KMeans
from sentence_transformers import SentenceTransformer
from storage.duckdb_storage import DuckDBStorage

class KeywordClusterNormalizer:
    def __init__(self, db_path=None, n_clusters=50):
        self.storage = DuckDBStorage(db_path=db_path)
        self.model   = SentenceTransformer("all-MiniLM-L6-v2")
        self.n_clusters = n_clusters

    def run(self):
        # 1) Sammle alle Keywords
        con = self.storage.connect(read_only=True)
        rows = con.execute("SELECT DISTINCT keyword FROM article_keywords").fetchall()
        con.close()
        kws = [r[0] for r in rows]
        # 2) Embeddings berechnen
        embs = self.model.encode(kws, normalize_embeddings=True)
        # 3) Cluster bilden
        km = KMeans(n_clusters=min(self.n_clusters, len(kws)))
        labels = km.fit_predict(embs)
        # 4) Für jedes Cluster das repräsentative Keyword bestimmen
        rep = {}
        for lab, kw in zip(labels, kws):
            rep.setdefault(lab, []).append(kw)
        canon = {kw: sorted(group, key=lambda x: -group.count(x))[0] 
                 for lab, group in rep.items() for kw in group}
        # 5) Normalisieren in DB
        for link in self.storage.get_all_links():
            orig = self.storage.get_article_keywords(link)
            norm = [canon.get(kw, kw) for kw in orig]
            self.storage.upsert_article_keywords(link, norm)
