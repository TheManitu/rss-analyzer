# rss_analyzer/rag.py
import duckdb
import re
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from ollama import chat
from rss_analyzer.config import DB_PATH, EMBEDDING_MODEL

embedder = SentenceTransformer(EMBEDDING_MODEL)

def clean_text(text):
    """Bereinigt den Text von überflüssigen Leerzeichen."""
    return re.sub(r'\s+', ' ', text).strip()

def get_relevant_articles(question, top_k=5, min_words=30):
    """
    Liest alle Artikel aus der DuckDB, berechnet mittels SentenceTransformer-Embeddings
    und FAISS die semantische Ähnlichkeit zum Frage-Text.
    """
    con = duckdb.connect(DB_PATH)
    rows = con.execute("SELECT rowid, title, content, link FROM articles").fetchall()
    con.close()
    if not rows:
        return ("", "")
    articles = []
    texts = []
    for row in rows:
        title = row[1]
        content = row[2]
        link = row[3]
        if content is None:
            continue
        content_clean = content.lower()
        if len(content.split()) < min_words or "inhalt fehlt" in content_clean:
            continue
        articles.append({"rowid": row[0], "title": title, "content": content, "link": link})
        texts.append(title + " " + content)
    if not articles:
        return ("", "")
    # Berechne Embeddings für alle gefilterten Artikel
    embeddings = embedder.encode(texts)
    embedding_dim = embeddings.shape[1]
    # FAISS-Index (hier noch mit IndexFlatL2 – in Patch 2 optimieren wir auf HNSW)
    index = faiss.IndexFlatL2(embedding_dim)
    faiss.normalize_L2(embeddings)
    index.add(np.array(embeddings))
    # Frage in Vektor umwandeln
    q_vec = embedder.encode([question])
    faiss.normalize_L2(q_vec)
    distances, indices = index.search(q_vec, top_k)
    
    sources_items = []
    prompt_items = []
    question_lower = question.lower()
    ai_keywords = ["ki", "ai", "künstliche intelligenz", "6g"]
    
    for i in indices[0]:
        if i >= len(articles):
            continue
        art = articles[i]
        combined_text = (art["title"] + " " + art["content"]).lower()
        if "apple" in question_lower and "samsung" in combined_text:
            continue
        if any(kw in question_lower for kw in ai_keywords):
            if not any(kw in combined_text for kw in ai_keywords):
                continue
        if art["link"]:
            sources_items.append(f'<li><a href="{art["link"]}" target="_blank">{art["title"]}</a></li>')
        else:
            sources_items.append(f'<li>{art["title"]}</li>')
        prompt_items.append(f"Title: {art['title']}\nContent: {art['content']}\n")
    if not prompt_items:
        return ("", "")
    sources_html = "<ul>" + "".join(sources_items) + "</ul>"
    prompt_text = "\n".join(prompt_items)
    return (sources_html, prompt_text)

def get_sources(question: str) -> str:
    sources_html, _ = get_relevant_articles(question)
    return sources_html

def get_detailed_answer(question: str) -> str:
    sources_html, prompt_text = get_relevant_articles(question)
    if not prompt_text:
        return "Keine qualifizierten Quellen gefunden, um die Frage zu beantworten."
    
    initial_prompt = (
        f"Frage: {question}\n\n"
        f"Artikelinformationen:\n{prompt_text}\n\n"
        "Erstelle eine präzise, ausführliche Antwort in deutscher Sprache, die ausschließlich die wesentlichen Informationen aus den oben genannten Artikeln enthält. "
        "Verwende klare und verständliche Formulierungen und gehe nur auf die relevanten Aspekte ein."
    )
    try:
        first_response = chat(
            model="deepseek-r1:7b",
            messages=[{'role': 'user', 'content': initial_prompt}]
        )
        first_answer = clean_text(first_response.message.content)
        refine_prompt = (
            "Überarbeite die folgende Antwort so, dass sie in fließendem, präzisem und verständlichem Deutsch formuliert ist und ausschließlich die wesentlichen Informationen in ca. 300 Wörtern enthält. "
            "Falls nötig, entferne spekulative oder unklare Aussagen.\n\n"
            f"Antwort: {first_answer}"
        )
        second_response = chat(
            model="deepseek-r1:14b",
            messages=[{'role': 'user', 'content': refine_prompt}]
        )
        final_answer = clean_text(second_response.message.content)
        return final_answer
    except Exception as e:
        return f"Fehler beim Abfragen des DeepSeek-Modells: {e}"

if __name__ == "__main__":
    question = "Was gibt es Neues zu AI?"
    print("Quellen:")
    print(get_sources(question))
    print("\n--- Final überarbeitete DeepSeek Antwort ---")
    print(get_detailed_answer(question))
