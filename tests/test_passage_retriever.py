from retrieval.passage_retriever import PassageRetriever
from storage.duckdb_storage import DuckDBStorage

def main():
    print("🔍 Starte PassageRetriever-Test...")

    storage = DuckDBStorage()
    retriever = PassageRetriever(storage)

    frage = "Was gibt es Neues zur Künstlichen Intelligenz?"

    top_passagen = retriever.retrieve(frage)
    if not top_passagen:
        print("❌ Keine passenden Passagen gefunden.")
        return

    print(f"✅ {len(top_passagen)} relevante Passagen gefunden:\n")
    for i, p in enumerate(top_passagen, 1):
        print(f"[{i}] {p['title']} ({p['score']})")
        print(p['text'][:300].strip() + "...")
        print(f"→ {p['link']}\n")

if __name__ == "__main__":
    main()
