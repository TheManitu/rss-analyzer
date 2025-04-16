# rag_modular.py – Modularer Ansatz für Retrieval-Augmented Generation (RAG)

import duckdb
import re
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer, CrossEncoder
try:
    from ollama import chat
except Exception as e:
    chat = None
import json
import sys
from rss_analyzer.config import DB_PATH, EMBEDDING_MODEL, TOPIC_MAPPING
from rank_bm25 import BM25Okapi

# ---- Konfigurationsparameter ----
DEFAULT_CONFIG = {
    "use_precomputed_embeddings": False,   # Option: Vorberechnete Embeddings verwenden (hier aktuell nicht implementiert)
    "use_query_expansion": False,          # Option: Query Expansion aktivieren (derzeit Platzhalter)
    "use_cross_encoder_rerank": False,     # Option: Zusätzliche Re-Rankung via CrossEncoder
    "weight_semantic": 0.7,                # Gewichtung für semantische Suche bei breiten Fragen
    "weight_keyword": 0.3,                 # Gewichtung für Keyword Matching bei breiten Fragen
    "top_n_general": 5,                    # Für breite Fragen, mindestens 5 Artikel
    "top_n_specific": 3                    # Für spezifische Anfragen, mindestens 3 Artikel
}

# ---- Optional: Initialisierung des CrossEncoders ----
def init_cross_encoder():
    try:
        # Beispielmodell; in der Realität ggf. feintunen oder anpassen
        return CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    except Exception as e:
        print("Fehler beim Laden des CrossEncoders:", e, file=sys.stderr)
        return None

# ---- Query Expansion (Platzhalter) ----
def query_expansion(query: str) -> str:
    """
    Erweitert die Nutzerfrage um Synonyme oder verwandte Begriffe.
    (Dies ist ein Platzhalter. Hier kannst Du z. B. NLP-Tools wie WordNet oder Modelle zur Synonymerkennung einbauen.)
    """
    # Hier einfach Rückgabe der originalen Query.
    return query

# ---- Heuristik zur Klassifikation der Anfrage (breit vs. spezifisch) ----
def is_broad_query(query: str) -> bool:
    q = query.lower()
    broad_indicators = ["gibt es neues", "neuigkeiten", "aktuellen stand", "trends", "overview", "what's new", "latest"]
    if any(phrase in q for phrase in broad_indicators):
        return True
    return False

# ---- Berechne semantische Scores ----
def compute_semantic_scores(query: str, articles: list, embedder: SentenceTransformer) -> np.array:
    query_vec = embedder.encode(query, normalize_embeddings=True)
    doc_embeddings = [embedder.encode(art['text'], normalize_embeddings=True) for art in articles]
    semantic_scores = np.dot(doc_embeddings, query_vec)
    if semantic_scores.max() > 0:
        semantic_scores = semantic_scores / semantic_scores.max()
    return semantic_scores

# ---- Berechne Keyword-Scores mit BM25 ----
def compute_keyword_scores(query: str, articles: list, bm25_index: BM25Okapi) -> np.array:
    tokenized_query = query.split()
    keyword_scores = bm25_index.get_scores(tokenized_query)
    if keyword_scores.max() > 0:
        keyword_scores = keyword_scores / keyword_scores.max()
    return keyword_scores

# ---- Kombiniere Scores hybride ----
def hybrid_scores(query: str, articles: list, config: dict, embedder: SentenceTransformer, bm25_index: BM25Okapi) -> np.array:
    semantic = compute_semantic_scores(query, articles, embedder)
    keyword = compute_keyword_scores(query, articles, bm25_index)
    weight_sem = config.get("weight_semantic", 0.7)
    weight_kw = config.get("weight_keyword", 0.3)
    return weight_sem * semantic + weight_kw * keyword

# ---- Optionale CrossEncoder-Re-Rankung ----
def rerank_with_cross_encoder(query: str, articles: list, current_indices: list, cross_encoder: CrossEncoder) -> list:
    if cross_encoder is None:
        return current_indices
    # Erstelle Query-Dokument-Paare
    pairs = [(query, articles[i]['text']) for i in current_indices]
    scores = cross_encoder.predict(pairs)
    # Sortiere die Indizes anhand der Scores (höhere Score = relevanter)
    sorted_indices = [i for _, i in sorted(zip(scores, current_indices), key=lambda x: x[0], reverse=True)]
    return sorted_indices

# ---- Hauptfunktion: Modularer Retrieval-Prozess ----
def modular_retrieval(query: str, articles: list, config: dict = None, embedder: SentenceTransformer = None) -> (str, bool):
    """
    Führt eine hybride Suche aus und liefert als Ergebnis eine HTML-Liste der ausgewählten Artikel.
    
    Parameters:
      query (str): Nutzerfrage.
      articles (list): Liste von Artikeln, z. B. [{'title': ..., 'text': ..., 'link': ...}, ...].
      config (dict): Konfiguration (siehe DEFAULT_CONFIG).
      embedder: Optional; SentenceTransformer-Instanz.
    
    Returns:
      Tuple[str, bool]: (HTML-Liste als String, Flag ob weniger als 3 Artikel gefunden wurden)
    """
    if config is None:
        config = DEFAULT_CONFIG
    if embedder is None:
        embedder = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Optionale Query Expansion
    if config.get("use_query_expansion", False):
        query = query_expansion(query)
    
    broad = is_broad_query(query)
    top_n = config.get("top_n_general", 5) if broad else config.get("top_n_specific", 3)
    
    # BM25-Index aufbauen
    tokenized_corpus = [art['text'].split() for art in articles]
    bm25_index = BM25Okapi(tokenized_corpus)
    
    # Berechnung hybrider Scores
    combined_scores = hybrid_scores(query, articles, config, embedder, bm25_index)
    top_indices = combined_scores.argsort()[::-1][:top_n]
    top_indices = list(top_indices)
    
    # Falls CrossEncoder Re-Rankung aktiviert ist, anwenden
    if config.get("use_cross_encoder_rerank", False):
        cross_encoder = init_cross_encoder()
        top_indices = rerank_with_cross_encoder(query, articles, top_indices, cross_encoder)
    else:
        cross_encoder = None
    
    selected_articles = [articles[i] for i in top_indices]
    few_sources_flag = False
    if len(selected_articles) < 3:
        few_sources_flag = True
    
    html_list_items = [f"<li>{art.get('title', 'Unbenannter Artikel')}</li>" for art in selected_articles]
    html_list = "<ol>\n" + "\n".join(html_list_items) + "\n</ol>"
    return html_list, few_sources_flag

# ---- Beispiel-Testmodul ----
if __name__ == "__main__":
    # Dummy-Datenbank (in der Praxis aus DuckDB laden)
    articles_db = [
        {"title": "OpenAI und KI-Trends 2024", "text": "OpenAI präsentiert neue KI-Modelle und innovative Ansätze in der Forschung.", "link": "https://beispiel.de/openai"},
        {"title": "Technologie-News im Überblick", "text": "Technologische Innovationen aus aller Welt; spannende Entwicklungen in KI, Robotik und mehr.", "link": "https://beispiel.de/tech-news"},
        {"title": "Innovative Ansätze in der KI", "text": "Verschiedene Unternehmen stellen 2024 ihre neuesten KI-Modelle vor. OpenAI nimmt dabei eine führende Rolle ein.", "link": "https://beispiel.de/innovative-ki"},
        {"title": "Künstliche Intelligenz und Alltag", "text": "KI-Anwendungen sind immer häufiger im Alltag anzutreffen: von Chatbots bis zu intelligenten Assistenten.", "link": "https://beispiel.de/ki-alltag"},
        {"title": "Fortschritte in der KI-Forschung", "text": "Die Forschung in der künstlichen Intelligenz macht rasant Fortschritte. Neue Modelle werden kontinuierlich entwickelt.", "link": "https://beispiel.de/ki-forschung"}
    ]
    
    # Beispielanfrage
    query_example = "Was gibt es Neues zu OpenAI?"
    html_list, few_flag = modular_retrieval(query_example, articles_db)
    print("Ausgewählte Artikel:")
    print(html_list)
    if few_flag:
        print("Hinweis: Es wurden nur wenige relevante Artikel gefunden. Bitte erweitere die Datenbank für dieses Thema.")
