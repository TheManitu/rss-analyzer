# api/rag.py

import logging
import uuid

from flask import Blueprint, render_template, request, jsonify, current_app, session
from logging_service.kafka_config_and_logger import log_user_question, log_answer_quality
from api.utils import extract_topic_from_question, store_question_event
from storage.topic_tracker import update_topic, create_topic_table, get_all_topics
from api.filters import first_words, truncatewords
from config import FINAL_CONTEXTS

from retrieval.passage_retriever import PassageRetriever

# --- Logging so konfigurieren, dass INFO direkt auf STDOUT geht ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("api.rag")

rag_bp = Blueprint("rag", __name__)
rag_bp.add_app_template_filter(first_words,   "first_words")
rag_bp.add_app_template_filter(truncatewords, "truncatewords")


@rag_bp.before_app_request
def ensure_session_ids():
    if 'user_id'   not in session: session['user_id']   = str(uuid.uuid4())
    if 'session_id' not in session: session['session_id'] = str(uuid.uuid4())


@rag_bp.route("/", methods=["GET", "POST"])
def index():
    create_topic_table()
    answer, sources = "", []
    time_filter = request.args.get("time_filter", "14_days")

    if request.method == "POST":
        q = request.form.get("question", "").strip()
        if not q:
            answer = "Bitte eine Frage eingeben."
        else:
            topic = extract_topic_from_question(q).lower()

            # --- OpenAI-Sonderfall ---
            if topic == "openai":
                con = current_app.storage.connect()
                rows = con.execute(
                    """
                    SELECT title,
                           CASE 
                             WHEN summary IS NOT NULL AND summary<>'' THEN summary
                             ELSE substr(content,1,500)
                           END AS summary,
                           link
                    FROM articles
                    WHERE LOWER(topic)='openai'
                    ORDER BY published DESC
                    LIMIT ?
                    """, (FINAL_CONTEXTS,)
                ).fetchall()
                con.close()

                if rows:
                    log_user_question(q, topic, len(rows),
                                      [r[2] for r in rows],
                                      session['user_id'], session['session_id'])
                    store_question_event(q, topic, len(rows))
                    update_topic(topic, delta=1)

                    lines = []
                    for title, summary, link in rows:
                        sources.append({
                            "title":   title,
                            "link":    link,
                            "snippet": summary[:200] + "…"
                        })
                        lines.append(f"* **{title}**  \n{summary}  \n{link}")
                    answer = "Hier die neuesten Artikel zu OpenAI:\n\n" + "\n\n".join(lines)

                    log_answer_quality(
                        used_article_ids=[r[2] for r in rows],
                        quality_score=1.0,
                        flag=False,
                        user_id=session['user_id'],
                        session_id=session['session_id']
                    )
                else:
                    answer = "Es wurden keine aktuellen OpenAI-Artikel gefunden."

            # --- Standard-RAG für alle anderen Topics ---
            else:
                retriever = PassageRetriever(current_app.storage)
                try:
                    top_passages = retriever.retrieve(q)
                except Exception:
                    logger.exception("Fehler bei PassageRetriever:")
                    top_passages = []

                if not top_passages:
                    # kein Treffer
                    log_user_question(q, topic, 0, [], session['user_id'], session['session_id'])
                    store_question_event(q, topic, 0)
                    update_topic(topic, delta=1)
                    log_answer_quality([], 0.0, True, session['user_id'], session['session_id'])
                    answer = f"Es wurden keine relevanten Passagen zu „{q}“ gefunden."
                else:
                    # Loggen & Topic-Tracking
                    log_user_question(q, topic, len(top_passages),
                                      [p["link"] for p in top_passages],
                                      session['user_id'], session['session_id'])
                    store_question_event(q, topic, len(top_passages))
                    update_topic(topic, delta=1)

                    # Kontexte aus Summaries bauen
                    seen = set()
                    contexts = []
                    for p in top_passages:
                        if p["link"] in seen:
                            continue
                        seen.add(p["link"])
                        row = current_app.storage.connect().execute(
                            "SELECT title, summary FROM articles WHERE link = ?", (p["link"],)
                        ).fetchone()
                        title, summary = row
                        contexts.append({
                            "title":   title,
                            "summary": summary or p["text"],
                            "link":    p["link"]
                        })
                        if len(contexts) >= FINAL_CONTEXTS:
                            break

                    # Generieren
                    try:
                        answer = current_app.generator.generate(q, contexts=contexts)
                    except Exception as e:
                        logger.exception(f"LLM-Fehler: {e}")
                        answer = "Entschuldigung, aktuell kann keine Antwort generiert werden."

                    # Evaluierung
                    eval_res = current_app.evaluator.evaluate(answer, top_passages)
                    log_answer_quality(
                        used_article_ids=[p["link"] for p in top_passages],
                        quality_score=eval_res["score"],
                        flag=eval_res["flag"],
                        user_id=session['user_id'],
                        session_id=session['session_id']
                    )

                    # Quellen fürs UI
                    for ctx in contexts:
                        sources.append({
                            "title":   ctx["title"],
                            "link":    ctx["link"],
                            "snippet": ctx["summary"][:200] + "…"
                        })

    # --- Dashboard-Daten (unverändert) ---
    try:
        top_articles = current_app.storage.get_all_articles(time_filter="today")
        articles     = current_app.storage.get_all_articles(time_filter=time_filter)
        counts = {
            "today":   len(current_app.storage.get_all_articles("today")),
            "3_days":  len(current_app.storage.get_all_articles("3_days")),
            "7_days":  len(current_app.storage.get_all_articles("7_days")),
            "14_days": len(current_app.storage.get_all_articles("14_days")),
        }
        topics = get_all_topics()
    except Exception:
        logger.exception("Fehler beim Laden der Übersichtsdaten:")
        top_articles, articles, counts, topics = [], [], {}, []

    return render_template(
        "index.html",
        answer=answer,
        sources=sources,
        top_articles=top_articles,
        articles=articles,
        counts=counts,
        topics=topics,
        time_filter=time_filter
    )


@rag_bp.route("/search", methods=["POST"])
def api_search():
    data = request.get_json() or {}
    q = data.get("question", "").strip()
    if not q:
        return jsonify(answer="Bitte eine Frage eingeben.", sources=[]), 400

    topic = extract_topic_from_question(q).lower()

    # OpenAI-Sonderfall
    if topic == "openai":
        con = current_app.storage.connect()
        rows = con.execute(
            """
            SELECT title, summary, link FROM articles
            WHERE LOWER(topic)='openai' AND summary<>''
            ORDER BY published DESC LIMIT ?
            """, (FINAL_CONTEXTS,)
        ).fetchall()
        con.close()
        if rows:
            sources_json = []
            for t, s, l in rows:
                sources_json.append({
                    "title":   t,
                    "link":    l,
                    "snippet": s[:200] + "…"
                })
            log_user_question(q, topic, len(rows), [r[2] for r in rows],
                              session['user_id'], session['session_id'])
            log_answer_quality([r[2] for r in rows], 1.0, False,
                               session['user_id'], session['session_id'])
            return jsonify(answer="Hier die neuesten Artikel zu OpenAI.", sources=sources_json), 200
        else:
            return jsonify(answer="Keine aktuellen OpenAI-Artikel gefunden.", sources=[]), 200

    # Standard-RAG
    retriever = PassageRetriever(current_app.storage)
    try:
        top_passages = retriever.retrieve(q)
    except Exception:
        logger.exception("PassageRetriever-Fehler in api_search:")
        top_passages = []

    if not top_passages:
        log_user_question(q, topic, 0, [], session['user_id'], session['session_id'])
        log_answer_quality([], 0.0, True, session['user_id'], session['session_id'])
        return jsonify(answer=f"Keine relevanten Passagen zu „{q}“ gefunden.", sources=[]), 200

    # Logging & Tracking
    log_user_question(q, topic, len(top_passages),
                      [p["link"] for p in top_passages],
                      session['user_id'], session['session_id'])

    filtered = (current_app.filterer.filter(q, top_passages)
                if hasattr(current_app, "filterer") else top_passages)
    ranked   = (current_app.ranker.rank(q, filtered)
                if hasattr(current_app, "ranker")   else filtered)
    top      = ranked[:FINAL_CONTEXTS]

    # Kontexte aus Summaries
    contexts = []
    for p in top:
        row = current_app.storage.connect().execute(
            "SELECT title, summary FROM articles WHERE link = ?", (p["link"],)
        ).fetchone()
        title, summary = row
        contexts.append({
            "title":   title,
            "summary": summary or p["text"],
            "link":    p["link"]
        })

    # Antwort generieren
    try:
        answer = current_app.generator.generate(q, contexts=contexts)
    except Exception:
        answer = "Entschuldigung, aktuell kann keine Antwort generiert werden."

    eval_res = current_app.evaluator.evaluate(answer, top)
    log_answer_quality(
        used_article_ids=[p["link"] for p in top],
        quality_score=eval_res["score"],
        flag=eval_res["flag"],
        user_id=session['user_id'],
        session_id=session['session_id']
    )

    sources_json = [{
        "title":   ctx["title"],
        "link":    ctx["link"],
        "snippet": ctx["summary"][:200] + "…"
    } for ctx in contexts]

    return jsonify(answer=answer, sources=sources_json), 200
