# rag.py – Verbesserte Version des Retrieval-Augmented Generation (RAG)-Moduls
# Mit themenspezifischen Filtern und Begrenzung auf maximal 5 Quellen

import duckdb
import re
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
try:
    from ollama import chat
except Exception as e:
    chat = None
import json
import sys
from rss_analyzer.config import DB_PATH, EMBEDDING_MODEL, TOPIC_MAPPING
from rank_bm25 import BM25Okapi

# Initialisiere das SentenceTransformer-Modell
try:
    embedder = SentenceTransformer(EMBEDDING_MODEL)
except Exception as e:
    print("Fehler beim Laden des Embedding-Modells:", e, file=sys.stderr)
    sys.exit(1)

# Optional: Hier könnte ein CrossEncoder initialisiert werden, falls gewünscht.
# from sentence_transformers import CrossEncoder
# try:
#     cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
# except Exception as e:
#     print("Fehler beim Laden des CrossEncoders:", e, file=sys.stderr)
#     cross_encoder = None

def safe_chat(model, messages):
    """
    Wrapper für ollama.chat, der Fehler abfängt und im Fehlerfall eine Dummy-Antwort zurückgibt.
    """
    global chat
    if chat is None:
        print("ollama.chat ist nicht verfügbar. Fallback aktiviert.", file=sys.stderr)
        class DummyMessage:
            content = "Dummy Antwort"
        class DummyResponse:
            message = DummyMessage()
        return DummyResponse()
    try:
        return chat(model=model, messages=messages)
    except Exception as e:
        print(f"Chat-Aufruf Fehler mit Modell {model}: {e}", file=sys.stderr)
        class DummyMessage:
            content = f"Fehler im Chat-Modell {model}: {e}"
        class DummyResponse:
            message = DummyMessage()
        return DummyResponse()

def clean_text(text):
    """Bereinigt den Text von überflüssigen Leerzeichen."""
    return re.sub(r'\s+', ' ', text).strip()

def filter_content_by_keyword(content, keyword):
    paragraphs = re.split(r'\n+', content)
    filtered = [p for p in paragraphs if keyword in p.lower()]
    return "\n".join(filtered) if filtered else content

def filter_content_by_keywords(content, keywords, include_neighbors=False):
    """
    Extrahiert Absätze aus dem Artikel, die mindestens eines der angegebenen Schlüsselwörter
    (case-insensitive) enthalten. Bei include_neighbors werden benachbarte Absätze mitaufgenommen.
    """
    if not content or not keywords:
        return ""
    paragraphs = re.split(r'\n+', content)
    filtered_paragraphs = []
    for i, para in enumerate(paragraphs):
        lower_para = para.lower()
        for kw in keywords:
            pattern = rf"(^|\W){re.escape(kw.lower())}($|\W)"
            if re.search(pattern, lower_para):
                filtered_paragraphs.append(para)
                if include_neighbors:
                    if i > 0 and paragraphs[i-1] not in filtered_paragraphs:
                        filtered_paragraphs.append(paragraphs[i-1])
                    if i < len(paragraphs) - 1 and paragraphs[i+1] not in filtered_paragraphs:
                        filtered_paragraphs.append(paragraphs[i+1])
                break
    return "\n".join(filtered_paragraphs)

def extract_relevant_passages(content, query, top_n=3, threshold=0.6):
    """
    Zerlegt den Artikel in Absätze und bewertet jeden Absatz anhand der Query (heuristische Wortüberschneidung).
    Liefert die Top_n Absätze zurück, die einen Score >= threshold aufweisen.
    Falls kein Absatz den Schwellenwert erreicht, wird der bestbewertete Absatz zurückgegeben.
    """
    paragraphs = [p.strip() for p in re.split(r'\n+', content) if p.strip()]
    if not paragraphs:
        return ""
    query_words = set(query.lower().split())
    scored_paras = []
    for p in paragraphs:
        p_words = set(p.lower().split())
        score = len(query_words.intersection(p_words)) / (len(query_words) + 1e-10)
        if score >= threshold:
            scored_paras.append((p, score))
    if not scored_paras:
        best_paragraph = max(paragraphs, key=lambda p: len(query_words.intersection(set(p.lower().split()))))
        return best_paragraph
    scored_paras.sort(key=lambda tup: tup[1], reverse=True)
    top_paras = [p for p, s in scored_paras[:top_n]]
    return "\n".join(top_paras)

def get_relevant_articles(question, top_k=5, min_words=30):
    try:
        con = duckdb.connect(DB_PATH)
        rows = con.execute("SELECT rowid, title, content, link FROM articles").fetchall()
        con.close()
    except Exception as e:
        print("Fehler beim Laden der Artikel aus der DB:", e, file=sys.stderr)
        return ("", "")
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
    
    question_lower = question.lower()
    # Ermittlung des Hauptthemas anhand von TOPIC_MAPPING
    matched_topics = []
    for topic_name, data in TOPIC_MAPPING.items():
        for kw in data["keywords"]:
            if kw in question_lower:
                matched_topics.append((topic_name, data["importance"], data["keywords"]))
                break
    main_topic_keywords = []
    if matched_topics:
        matched_topics.sort(key=lambda x: x[1], reverse=True)
        main_topic_keywords = matched_topics[0][2]
    
    # Artikel vorfiltern, falls ein spezifisches Thema in der Frage vorkommt.
    if main_topic_keywords:
        filtered_articles = []
        filtered_texts = []
        for art, txt in zip(articles, texts):
            combined_text = (art["title"] + " " + art["content"]).lower()
            if any(kw in combined_text for kw in main_topic_keywords):
                filtered_articles.append(art)
                filtered_texts.append(txt)
        if filtered_articles:
            articles = filtered_articles
            texts = filtered_texts

    # Erhöhe den Suchbereich: breit gefasste Anfragen (z. B. "Was gibt es Neues zu ...") werden intensiver durchsucht.
    broad_triggers = ["neues", "neuigkeit", "neuigkeiten", "aktuell", "trends", "entwicklungen", "latest", "news"]
    broad_query = any(term in question_lower for term in broad_triggers)
    top_k_initial = 20 if broad_query else 15
    
    try:
        embeddings = embedder.encode(texts)
    except Exception as e:
        print("Fehler beim Berechnen der Embeddings:", e, file=sys.stderr)
        return ("", "")
    embedding_dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(embedding_dim)
    faiss.normalize_L2(embeddings)
    index.add(np.array(embeddings))
    
    try:
        q_vec = embedder.encode([question])
    except Exception as e:
        print("Fehler beim Einbetten der Frage:", e, file=sys.stderr)
        return ("", "")
    faiss.normalize_L2(q_vec)
    distances, indices = index.search(q_vec, top_k_initial)
    
    sources_items = []
    prompt_items = []
    used_article_indices = set()
    
    # Extrahiere relevante Schlüsselwörter aus der Frage (ohne Füllwörter)
    question_keywords = [w for w in re.findall(r'\w+', question_lower) if w not in {
        "und", "oder", "aber", "jedoch", "der", "die", "das", "ein", "eine", "einer", "einem",
        "den", "dem", "im", "in", "auf", "für", "von", "mit", "ist", "sind", "zum", "zur", "bei",
        "warum", "wieso", "weshalb", "wie", "wo", "was", "wann", "wer", "gibt", "es",
        "neu", "neues", "neuigkeit", "neuigkeiten", "aktuell", "trends", "entwicklungen", "latest", "news"
    } and (len(w) > 2 or w in ["ai", "ki"])]
    
    # Erster Durchlauf: Gehe die gefundenen Artikel durch und extrahiere den relevanten Content.
    for d, i in zip(distances[0], indices[0]):
        if i >= len(articles):
            continue
        art = articles[i]
        used_article_indices.add(i)
        if broad_query:
            keywords_for_filter = main_topic_keywords if main_topic_keywords else question_keywords
        else:
            keywords_for_filter = list(set(main_topic_keywords + question_keywords))
        relevant_content = filter_content_by_keywords(art["content"], keywords_for_filter, include_neighbors=True)
        if not relevant_content:
            paragraphs = [p for p in re.split(r'\n+', art["content"]) if p.strip()]
            if paragraphs:
                p_embeddings = embedder.encode(paragraphs)
                faiss.normalize_L2(p_embeddings)
                q_vec_flat = q_vec[0]
                sims = np.dot(p_embeddings, q_vec_flat)
                high_idx = [idx for idx, sim in enumerate(sims) if sim >= 0.8]
                if high_idx:
                    relevant_paras = [paragraphs[idx] for idx in high_idx]
                else:
                    best_idx = int(np.argmax(sims))
                    if sims[best_idx] >= 0.5:
                        relevant_paras = [paragraphs[best_idx]]
                    else:
                        relevant_paras = []
                relevant_content = "\n".join(relevant_paras)
        if not broad_query and main_topic_keywords and relevant_content:
            paras = [p for p in re.split(r'\n+', relevant_content) if p.strip()]
            paras = [p for p in paras if any(kw in p.lower() for kw in main_topic_keywords)]
            relevant_content = "\n".join(paras)
        if not relevant_content:
            continue
        combined_text = (art["title"] + " " + relevant_content).lower()
        # Filter: Für ChatGPT-Anfragen nur Artikel, die thematisch passen.
        if "chatgpt" in question_lower:
            relevant_topic_keywords = ["chatgpt", "gpt", "openai", "language model", "künstliche intelligenz", "ki"]
            if not any(kw in combined_text for kw in relevant_topic_keywords):
                continue
        # Filter: Für Windows-Anfragen nur Artikel, die windows-bezogene Begriffe enthalten.
        if "windows" in question_lower:
            windows_keywords = ["windows", "microsoft", "win10", "win11", "windows server", "betriebssystem", "update"]
            if not any(kw in combined_text for kw in windows_keywords):
                continue
        if art["link"]:
            sources_items.append(f'<li><a href="{art["link"]}" target="_blank">{art["title"]}</a></li>')
        else:
            sources_items.append(f'<li>{art["title"]}</li>')
        prompt_items.append(f"Title: {art['title']}\nContent: {relevant_content}\n")
    
    # Sekundärer Durchlauf: Falls weniger als 3 Quellen gefunden wurden, benutze einen gelockerten Schwellenwert.
    if len(sources_items) < 3:
        relaxed_threshold = 0.7
        for d, i in zip(distances[0], indices[0]):
            if i in used_article_indices:
                continue
            art = articles[i]
            if broad_query:
                keywords_for_filter = main_topic_keywords if main_topic_keywords else question_keywords
            else:
                keywords_for_filter = list(set(main_topic_keywords + question_keywords))
            relevant_content = filter_content_by_keywords(art["content"], keywords_for_filter, include_neighbors=True)
            if relevant_content:
                relevant_content = extract_relevant_passages(relevant_content, question, top_n=3, threshold=0.6)
            else:
                relevant_content = extract_relevant_passages(art["content"], question, top_n=3, threshold=0.6)
            if not relevant_content:
                continue
            combined_text = (art["title"] + " " + relevant_content).lower()
            if "chatgpt" in question_lower:
                relevant_topic_keywords = ["chatgpt", "gpt", "openai", "language model", "künstliche intelligenz", "ki"]
                if not any(kw in combined_text for kw in relevant_topic_keywords):
                    continue
            if "windows" in question_lower:
                windows_keywords = ["windows", "microsoft", "win10", "win11", "windows server", "betriebssystem", "update"]
                if not any(kw in combined_text for kw in windows_keywords):
                    continue
            if art["link"]:
                sources_items.append(f'<li><a href="{art["link"]}" target="_blank">{art["title"]}</a></li>')
            else:
                sources_items.append(f'<li>{art["title"]}</li>')
            prompt_items.append(f"Title: {art['title']}\nContent: {relevant_content}\n")
            used_article_indices.add(i)
            if len(sources_items) >= 3:
                break

    # Fallback: Falls keine Artikel gefunden wurden, verwende den bestbewerteten Artikel.
    if not prompt_items:
        if indices[0].size > 0:
            best_index = indices[0][0]
            art = articles[best_index]
            fallback_content = art["content"]
            sources_items = []
            if art["link"]:
                sources_items.append(f'<li><a href="{art["link"]}" target="_blank">{art["title"]}</a></li>')
            else:
                sources_items.append(f'<li>{art["title"]}</li>')
            prompt_items = [f"Title: {art['title']}\nContent: {fallback_content}\n"]
            fallback_note = "\n*Hinweis: Es wurden nur sehr wenige Artikel zum Thema gefunden. Bitte erweitere die Datenbank für dieses Thema.*\n"
            prompt_items.append(fallback_note)
        else:
            return ("", "")
    # Beschränke die Anzahl der Quellen auf maximal 5.
    if len(sources_items) > 5:
        sources_items = sources_items[:5]
        prompt_items = prompt_items[:5]

    sources_html = "<ol>" + "".join(sources_items) + "</ol>"
    prompt_text = "\n".join(prompt_items)
    return (sources_html, prompt_text)

def get_sources(question: str) -> str:
    try:
        sources_html, _ = get_relevant_articles(question)
        return sources_html
    except Exception as e:
        print("Fehler in get_sources:", e, file=sys.stderr)
        return ""

def grade_answer(answer: str, prompt_text: str, question: str) -> bool:
    grading_prompt = (
        f"Artikelinformationen:\n{prompt_text}\n\n"
        f"Frage: {question}\n\n"
        f"Generierte Antwort: {answer}\n\n"
        "Bewerte objektiv, ob die Antwort alle relevanten Informationen enthält und keine zusätzlichen, nicht fundierten (halluzinierten) Inhalte beinhaltet. "
        "Gib als Antwort ein JSON-Objekt mit dem Schlüssel 'binary_score' und dem Wert 'yes' oder 'no'."
    )
    try:
        response = safe_chat(model="phi3:medium", messages=[{'role': 'user', 'content': grading_prompt}])
        result = json.loads(response.message.content)
        return result.get("binary_score", "no").lower() == "yes"
    except Exception as e:
        print("Fehler im Grade-Call:", e, file=sys.stderr)
        return False

def get_detailed_answer(question: str, max_retries: int = 3) -> str:
    try:
        sources_html, prompt_text = get_relevant_articles(question)
    except Exception as e:
        print("Fehler in get_relevant_articles:", e, file=sys.stderr)
        return ("Keine qualifizierten Quellen gefunden, um die Frage zu beantworten.")
    
    if not prompt_text:
        return ("Keine qualifizierten Quellen gefunden, um die Frage zu beantworten. Bitte überprüfe deine Eingabe oder nutze alternativ eine Websuche.")
    
    initial_prompt = (
        f"Frage: {question}\n\n"
        f"Artikelinformationen:\n{prompt_text}\n\n"
        "Erstelle eine präzise und umfassende Antwort in fließendem Deutsch, die alle wesentlichen Informationen der angegebenen Artikel beinhaltet. "
        "Gib nur das Endergebnis ohne zusätzlichen Denktext aus."
    )
    try:
        first_response = safe_chat(model="llama2", messages=[{'role': 'user', 'content': initial_prompt}])
        current_answer = clean_text(first_response.message.content)
    except Exception as e:
        err = f"Fehler beim Abfragen des KI-Modells (llama2): {e}"
        print(err, file=sys.stderr)
        return err
    
    for attempt in range(max_retries):
        refine_prompt = (
            f"Frage: {question}\n\n"
            "Die vorherige Antwort scheint nicht alle relevanten Informationen präzise zu enthalten. Bitte verbessere die Antwort, "
            "indem du alle wichtigen Details aus den untenstehenden Artikeln berücksichtigst.\n\n"
            f"Vorherige Antwort: {current_answer}\n\n"
            f"Artikelinformationen:\n{prompt_text}\n\n"
            "Gib ausschließlich das finale Endergebnis ohne zusätzlichen Denktext aus."
        )
        try:
            refine_response = safe_chat(model="phi3:medium", messages=[{'role': 'user', 'content': refine_prompt}])
            current_answer = clean_text(refine_response.message.content)
        except Exception as e:
            err = f"Fehler beim Abfragen des KI-Modells (phi3:medium) im Refinement: {e}"
            print(err, file=sys.stderr)
            return err

    finalize_prompt = (
        f"Frage: {question}\n\n"
        "Formuliere abschließend eine präzise, fließend formulierte und zusammenfassende Antwort in Deutsch, "
        "basierend auf den untenstehenden Informationen. Gib ausschließlich das finale Endergebnis ohne zusätzlichen Erklärtext aus.\n\n"
        f"Antwort: {current_answer}"
    )
    try:
        final_response = safe_chat(model="phi3:medium", messages=[{'role': 'user', 'content': finalize_prompt}])
        final_answer = clean_text(final_response.message.content)
    except Exception as e:
        err = f"Fehler beim finalen Aufruf des KI-Modells (phi3:medium): {e}"
        print(err, file=sys.stderr)
        return err

    # Füge immer die verwendeten Quellen zur finalen Antwort hinzu.
    final_answer += "\n\nVerwendete Quellen:\n" + sources_html
    num_sources = sources_html.count("<li>")
    if num_sources < 3:
        final_answer += (
            "\n\n*Hinweis: Es wurden nur "
            f"{num_sources} relevante Quelle{'n' if num_sources != 1 else ''} gefunden. Bitte erweitere die Datenbank für dieses Thema.*"
        )
    return final_answer

if __name__ == "__main__":
    test_question = "Was gibt es Neues zu ChatGPT?"
    print("Quellen:")
    print(get_sources(test_question))
    print("\n--- Final überarbeitete Antwort ---")
    print(get_detailed_answer(test_question))
