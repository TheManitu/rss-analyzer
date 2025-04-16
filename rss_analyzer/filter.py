"""
filter.py
----------
Diese Datei enthält alle Filter-Funktionen, die im RAG-Modul zur Extraktion relevanter Inhalte
aus den Artikeln verwendet werden.

Enthaltene Funktionen:
- filter_content_by_keywords: Extrahiert Absätze, die mindestens ein angegebenes Schlüsselwort enthalten.
- extract_relevant_passages: Zerlegt den Artikel in Absätze und wählt die Top-n Absätze aus, die semantisch
  zur Frage passen (mit Hilfe von Cosinus-Ähnlichkeit, basierend auf SentenceTransformer-Embeddings).
"""

import re
import numpy as np
from sentence_transformers import SentenceTransformer

def filter_content_by_keywords(content: str, keywords: list, include_neighbors: bool = False) -> str:
    """
    Extrahiert Absätze aus dem Inhalt, die mindestens eines der angegebenen Schlüsselwörter (case-insensitive)
    enthalten. Bei include_neighbors=True werden zusätzlich benachbarte Absätze mit aufgenommen.
    
    :param content: Der Text, in dem gefiltert werden soll.
    :param keywords: Liste von Schlüsselwörtern.
    :param include_neighbors: Falls True, werden auch benachbarte Absätze in die Ausgabe aufgenommen.
    :return: Gefilterter Text als String.
    """
    if not content or not keywords:
        return ""
    paragraphs = re.split(r'\n+', content)
    filtered_paragraphs = []
    for i, para in enumerate(paragraphs):
        para_lower = para.lower()
        for kw in keywords:
            pattern = rf"(^|\W){re.escape(kw.lower())}($|\W)"
            if re.search(pattern, para_lower):
                filtered_paragraphs.append(para)
                if include_neighbors:
                    if i > 0 and paragraphs[i - 1] not in filtered_paragraphs:
                        filtered_paragraphs.append(paragraphs[i - 1])
                    if i < len(paragraphs) - 1 and paragraphs[i + 1] not in filtered_paragraphs:
                        filtered_paragraphs.append(paragraphs[i + 1])
                break
    return "\n".join(filtered_paragraphs)

def extract_relevant_passages(content: str, query: str, top_n: int = 5, threshold: float = 0.8, embedder: SentenceTransformer = None) -> str:
    """
    Zerlegt den Artikel in Absätze und bewertet jeden Absatz semantisch anhand des Query-Texts.
    Es werden die Top-n Absätze zurückgegeben, deren Cosinus-Ähnlichkeitswert ≥ threshold liegt.
    Falls kein Absatz den Schwellwert erreicht, wird der beste Absatz zurückgegeben.
    
    :param content: Artikelinhalt, der in Absätze unterteilt wird.
    :param query: Die Frage oder der Query-Text, anhand dessen die Ähnlichkeit gemessen wird.
    :param top_n: Maximale Anzahl der zurückzugebenden Absätze.
    :param threshold: Minimal erforderliche Ähnlichkeit.
    :param embedder: Ein SentenceTransformer-Objekt, das für die Embedding-Berechnung verwendet wird.
                     Dieser Parameter muss gesetzt sein.
    :return: Relevante Passagen als zusammengefügter String.
    :raises ValueError: Falls kein embedder übergeben wurde.
    """
    if embedder is None:
        raise ValueError("Ein SentenceTransformer-Objekt (embedder) muss an extract_relevant_passages übergeben werden.")
        
    paragraphs = [p.strip() for p in re.split(r'\n+', content) if p.strip()]
    if not paragraphs:
        return ""
    query_vec = embedder.encode(query, normalize_embeddings=True)
    para_embeddings = embedder.encode(paragraphs, normalize_embeddings=True)
    sims = np.dot(para_embeddings, query_vec)
    
    scored_paras = [(para, sim) for para, sim in zip(paragraphs, sims) if sim >= threshold]
    if not scored_paras:
        best_index = int(np.argmax(sims))
        return paragraphs[best_index]
    
    scored_paras.sort(key=lambda x: x[1], reverse=True)
    top_paras = [p for p, sim in scored_paras[:top_n]]
    return "\n".join(top_paras)
