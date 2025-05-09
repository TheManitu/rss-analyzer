import logging
import uuid
import string
import re

from flask import (
    Blueprint, render_template, request, jsonify,
    current_app, session
)
from logging_service.kafka_config_and_logger import (
    log_user_question, log_answer_quality
)
from .utils import extract_topic_from_question, store_question_event
from storage.topic_tracker import update_topic, create_topic_table, get_all_topics
from retrieval.passage_retriever import PassageRetriever

logger = logging.getLogger("api.rag")
rag_bp = Blueprint("rag", __name__)

from api.filters import first_words, truncatewords
rag_bp.add_app_template_filter(first_words,  'first_words')
rag_bp.add_app_template_filter(truncatewords, 'truncatewords')

@rag_bp.before_app_request
def ensure_session_ids():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

@rag_bp.route("/", methods=["GET", "POST"])
def index():
    try:
        create_topic_table()
        answer = ""
        sources = []
        time_filter = request.args.get("time_filter", "14_days")
        retriever = PassageRetriever(current_app.storage)

        if request.method == "POST":
            q = request.form.get("question", "").strip()
            if not q:
                answer = "Bitte eine Frage eingeben."
            else:
                try:
                    top_passages = retriever.retrieve(q)
                except Exception as e:
                    logger.exception("Fehler bei PassageRetriever:")
                    top_passages = []

                if top_passages:
                    try:
                        answer = current_app.generator.generate(q, top_passages)
                    except Exception as gen_err:
                        logger.exception("Fehler bei Antwortgenerierung:")
                        answer = "Es gab ein Problem bei der Generierung der Antwort."

                    try:
                        eval_res = current_app.evaluator.evaluate(answer, top_passages)
                    except Exception as eval_err:
                        logger.exception("Fehler bei der Bewertung:")
                        eval_res = {"score": 0.0, "flag": True}

                    sources = [{"title": p["title"], "link": p["link"]} for p in top_passages]
                    answer += "\n\nQuellen:\n" + "\n".join(
                        f"- {s['title']}: {s['link']}" for s in sources
                    )

                    try:
                        topic = extract_topic_from_question(q)
                        log_user_question(q, topic, len(top_passages),
                                          [p["link"] for p in top_passages],
                                          session['user_id'], session['session_id'])
                        store_question_event(q, topic, len(top_passages))
                        update_topic(topic, delta=1)
                        log_answer_quality(
                            used_article_ids=[p["link"] for p in top_passages],
                            quality_score=eval_res["score"],
                            flag=eval_res["flag"],
                            user_id=session['user_id'],
                            session_id=session['session_id']
                        )
                    except Exception as log_err:
                        logger.exception("Fehler bei Logging/Tracking:")
                else:
                    try:
                        answer = f"Es wurden keine relevanten Passagen zu „{q}“ gefunden."
                        topic = extract_topic_from_question(q)
                        log_user_question(q, topic, 0, [], session['user_id'], session['session_id'])
                        store_question_event(q, topic, 0)
                        update_topic(topic, delta=1)
                        log_answer_quality([], 0.0, True, session['user_id'], session['session_id'])
                    except Exception as fallback_log:
                        logger.exception("Fehler im Logging bei leeren Treffern:")

        try:
            top_articles = current_app.storage.get_all_articles(time_filter="today")
            articles = current_app.storage.fetch_passages(time_filter=time_filter)
            counts = {
                'today': len(current_app.storage.get_all_articles('today')),
                '3_days': len(current_app.storage.get_all_articles('3_days')),
                '7_days': len(current_app.storage.get_all_articles('7_days')),
                '14_days': len(current_app.storage.get_all_articles('14_days'))
            }
            topics = get_all_topics()
        except Exception as view_err:
            logger.exception("Fehler beim Laden der Übersichtsdaten:")
            top_articles = []
            articles = []
            counts = {'today': 0, '3_days': 0, '7_days': 0, '14_days': 0}
            topics = []

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

    except Exception as e:
        logger.exception("❌ Unerwarteter Fehler in rag.index()")
        return render_template("index.html", answer="Ein interner Fehler ist aufgetreten.", sources=[])
    
@rag_bp.route("/search", methods=["POST"])
def api_search():
    try:
        try:
            data = request.get_json() or {}
            q = data.get("question", "").strip()
            if not q:
                return jsonify({"answer": "Bitte eine Frage eingeben.", "sources": []}), 400
        except Exception as parse_err:
            logger.exception("Fehler beim Parsen der Anfrage:")
            return jsonify({"answer": "Ungültiges Anfrageformat.", "sources": []}), 400

        retriever = PassageRetriever(current_app.storage)

        try:
            candidates = retriever.retrieve(q)
        except Exception as ret_err:
            logger.exception("Fehler beim PassageRetriever:")
            return jsonify({"answer": "Die semantische Suche ist derzeit nicht verfügbar.", "sources": []}), 500

        if not candidates:
            answer = f"Es wurden keine passenden Artikel oder Passagen zu „{q}“ gefunden."
            log_answer_quality([], 0.0, True, session['user_id'], session['session_id'])
            return jsonify({"answer": answer, "sources": []})

        try:
            filtered = current_app.filterer.apply(candidates, q)
            top = current_app.ranker.rerank(q, filtered)[:5]
        except Exception as filter_err:
            logger.exception("Fehler beim Filtern oder Reranken")
            top = candidates[:5]

        topic = extract_topic_from_question(q)
        try:
            log_user_question(q, topic, len(candidates),
                              [c["link"] for c in top],
                              session['user_id'], session['session_id'])
            store_question_event(q, topic, len(candidates))
            update_topic(topic, delta=1)
        except Exception as log_err:
            logger.exception("Fehler bei Logging/Tracking")

        try:
            answer = current_app.generator.generate(q, top)
        except Exception as gen_err:
            logger.exception("Fehler bei Antwortgenerierung")
            answer = "Es gab ein Problem bei der Antwortgenerierung."

        try:
            eval_res = current_app.evaluator.evaluate(answer, top)
        except Exception as eval_err:
            logger.exception("Fehler bei der Evaluierung")
            eval_res = {"score": 0.0, "flag": True}

        sources = [{"title": c["title"], "link": c["link"]} for c in top]
        answer += "\n\nQuellen:\n" + "\n".join(
            f"- {s['title']}: {s['link']}" for s in sources
        )

        log_answer_quality(
            used_article_ids=[c["link"] for c in top],
            quality_score=eval_res["score"],
            flag=eval_res["flag"],
            user_id=session['user_id'],
            session_id=session['session_id']
        )

        return jsonify({"answer": answer, "sources": sources})

    except Exception as e:
        logger.exception("❌ Unerwarteter Fehler in api_search()")
        return jsonify({"answer": "Ein interner Fehler ist aufgetreten.", "sources": []}), 500
