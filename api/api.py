# app/api/api.py

import os
import logging
from flask import Flask, render_template, jsonify, request, session
from prometheus_client import Counter, Gauge, Histogram

# Ingestion & Storage
from ingestion.rss_ingest import RSSIngest
from storage.duckdb_storage import DuckDBStorage
from storage.topic_tracker import create_topic_table, update_topic, get_all_topics

# Pipeline-Module
from pipeline.article_cleaner                import ArticleCleaner
from pipeline.keyword_extraction_langaware   import LanguageAwareKeywordExtractor
from pipeline.topic_assignment               import TopicAssigner
from pipeline.relevance_scoring              import RelevanceScorer
from pipeline.segmentation                   import Segmenter
from pipeline.summarization                  import Summarizer
from pipeline.analyzer                       import DataAnalyzer
from pipeline.dashboard_generator            import DashboardGenerator

# RAG-Komponenten
from retrieval.passage_retriever    import PassageRetriever
from retrieval.content_filter       import ContentFilter
from ranking.cross_encoder_ranker   import CrossEncoderRanker
from generation.llm_generator       import LLMGenerator
from evaluation.quality_evaluator   import QualityEvaluator

from api.utils      import extract_topic_from_question, store_question_event
from api.filters    import first_words, truncatewords
from api.rag        import rag_bp

from config import RSS_FEEDS, FINAL_CONTEXTS

def create_app():
    logging.basicConfig(level=logging.INFO)
    app = Flask(__name__, template_folder="./templates", static_folder="./static")
    app.secret_key = os.getenv("FLASK_SECRET", "change_me")

    # Prometheus-Metriken
    app.Q_COUNT    = Counter("rss_questions_total",     "Anzahl Fragen gesamt")
    app.ZERO_CAND  = Gauge("rss_zero_candidate_ratio",  "Verhältnis Null-Treffer")
    app.DB_LATENCY = Histogram("duckdb_query_seconds",   "DB-Latenz in Sekunden")

    # Tabellen anlegen
    create_topic_table()
    storage = DuckDBStorage(db_path=os.getenv("DB_PATH"))
    app.storage = storage

    # Startup-Skip-Flags
    skip_ingest    = os.getenv("SKIP_INGEST_ON_STARTUP",       "false").lower() in ("1","true","yes")
    skip_kw        = os.getenv("SKIP_KEYWORDS_ON_STARTUP",     "false").lower() in ("1","true","yes")
    skip_topics    = os.getenv("SKIP_TOPICS_ON_STARTUP",       "false").lower() in ("1","true","yes")
    skip_relevance = os.getenv("SKIP_RELEVANCE_ON_STARTUP",    "false").lower() in ("1","true","yes")
    skip_segment   = os.getenv("SKIP_SEGMENTATION_ON_STARTUP", "false").lower() in ("1","true","yes")
    skip_summary   = os.getenv("SKIP_SUMMARIZATION_ON_STARTUP","false").lower() in ("1","true","yes")
    skip_analyzer  = os.getenv("SKIP_ANALYZER_ON_STARTUP",     "false").lower() in ("1","true","yes")
    skip_dashboard = os.getenv("SKIP_DASHBOARD_ON_STARTUP",    "false").lower() in ("1","true","yes")

    # 1) RSS-Ingestion
    if skip_ingest:
        logging.info("SKIP_INGEST_ON_STARTUP=true → RSS-Ingestion übersprungen")
    else:
        logging.info("Starte RSS-Ingestion …")
        try:
            RSSIngest(feeds=RSS_FEEDS, storage_client=storage).run()
        except Exception:
            logging.exception("Fehler bei RSS-Ingestion – überspringe und fahre fort")

    # 2) Keyword-Extraction
    if skip_kw:
        logging.info("SKIP_KEYWORDS_ON_STARTUP=true → Keyword-Extraction übersprungen")
    else:
        logging.info("Starte Keyword-Extraction …")
        try:
            LanguageAwareKeywordExtractor().run()
        except Exception:
            logging.exception("Fehler bei Keyword-Extraction – überspringe und fahre fort")

    # 3) Topic-Assignment
    if skip_topics:
        logging.info("SKIP_TOPICS_ON_STARTUP=true → Topic-Assignment übersprungen")
    else:
        logging.info("Starte Topic-Assignment …")
        try:
            TopicAssigner().run()
        except Exception:
            logging.exception("Fehler bei Topic-Assignment – überspringe und fahre fort")

    # 4) Relevance-Scoring
    if skip_relevance:
        logging.info("SKIP_RELEVANCE_ON_STARTUP=true → Relevance-Scoring übersprungen")
    else:
        logging.info("Starte Relevance-Scoring …")
        try:
            RelevanceScorer().run()
        except Exception:
            logging.exception("Fehler bei Relevance-Scoring – überspringe und fahre fort")

    # 5) Segmentation
    if skip_segment:
        logging.info("SKIP_SEGMENTATION_ON_STARTUP=true → Segmentation übersprungen")
    else:
        logging.info("Starte Segmentation …")
        try:
            Segmenter().run()
        except Exception:
            logging.exception("Fehler bei Segmentation – überspringe und fahre fort")

    # 6) Summarization
    if skip_summary:
        logging.info("SKIP_SUMMARIZATION_ON_STARTUP=true → Summarization übersprungen")
    else:
        logging.info("Starte Summarization …")
        try:
            Summarizer().run()
        except Exception:
            logging.exception("Fehler bei Summarization – überspringe und fahre fort")

    # 7) Data-Analysis
    if skip_analyzer:
        logging.info("SKIP_ANALYZER_ON_STARTUP=true → Data-Analyzer übersprungen")
    else:
        logging.info("Starte Data-Analyzer …")
        try:
            DataAnalyzer().run()
        except Exception:
            logging.exception("Fehler bei Data-Analyzer – überspringe und fahre fort")

    # 8) Dashboard
    if skip_dashboard:
        logging.info("SKIP_DASHBOARD_ON_STARTUP=true → Dashboard-Erstellung übersprungen")
    else:
        logging.info("Erzeuge Dashboard …")
        try:
            DashboardGenerator().run()
        except Exception:
            logging.exception("Fehler bei Dashboard-Erstellung – überspringe und fahre fort")

    # RAG-Komponenten initialisieren
    app.retriever = PassageRetriever(storage)
    app.filterer  = ContentFilter()
    app.ranker    = CrossEncoderRanker()
    app.generator = LLMGenerator()
    app.evaluator = QualityEvaluator(threshold=0.5)

    # Jinja-Filter registrieren
    app.add_template_filter(first_words,   "first_words")
    app.add_template_filter(truncatewords, "truncatewords")

    # Blueprint für /rag
    app.register_blueprint(rag_bp, url_prefix="/rag")

    @app.route("/")
    def index():
        topics       = get_all_topics()
        top_articles = storage.get_all_articles(time_filter="today") or storage.get_all_articles(time_filter="7_days")
        counts = {
            "today":   len(storage.get_all_articles(time_filter="today")),
            "3_days":  len(storage.get_all_articles(time_filter="3_days")),
            "7_days":  len(storage.get_all_articles(time_filter="7_days")),
            "14_days": len(storage.get_all_articles(time_filter="14_days")),
        }
        return render_template("index.html",
                               topics=topics,
                               top_articles=top_articles,
                               counts=counts)

    @app.route("/api/refresh", methods=["POST"])
    def refresh():
        try:    ArticleCleaner(db_path=os.getenv("DB_PATH")).run()
        except: logging.exception("Cleanup failed")
        try:    RSSIngest(feeds=RSS_FEEDS, storage_client=storage).run()
        except: logging.exception("Ingest failed")
        try:    LanguageAwareKeywordExtractor().run()
        except: logging.exception("Keywords failed")
        try:    TopicAssigner().run()
        except: logging.exception("Topics failed")
        try:    RelevanceScorer().run()
        except: logging.exception("Relevance failed")
        try:    Segmenter().run()
        except: logging.exception("Segmentation failed")
        try:    Summarizer().run()
        except: logging.exception("Summarization failed")
        try:    DataAnalyzer().run()
        except: logging.exception("Analyzer failed")
        try:    DashboardGenerator().run()
        except: logging.exception("Dashboard failed")
        return jsonify(status="ok")

    @app.route("/search", methods=["POST"])
    def search():
        data = request.get_json() or {}
        q    = data.get("question", "").strip()
        if not q:
            # so stellen wir sicher, dass kein positional argument error mehr auftritt
            response = jsonify(answer="Bitte eine Frage eingeben.", sources=[])
            response.status_code = 400
            return response

        # Retrieval
        passages = app.retriever.retrieve(q) or []

        # Logging & Topic-Tracking
        topic = extract_topic_from_question(q)
        store_question_event(q, topic, len(passages))
        update_topic(topic, delta=1)

        # Filter → Rank → Generate → Evaluate
        filtered = app.filterer.apply(passages, q)
        ranked   = app.ranker.rank(q, filtered)
        top_ctx  = ranked[:FINAL_CONTEXTS]
        answer   = app.generator.generate(q, contexts=top_ctx)
        eval_res = app.evaluator.evaluate(answer, top_ctx)

        # Kafka-Logging
        from logging_service.kafka_config_and_logger import log_user_question, log_answer_quality
        log_user_question(q, topic, len(passages),
                          [p["link"] for p in top_ctx],
                          session['user_id'], session['session_id'])
        log_answer_quality(used_article_ids=[p["link"] for p in top_ctx],
                           quality_score=eval_res["score"],
                           flag=eval_res["flag"],
                           user_id=session['user_id'], session_id=session['session_id'])

        # Quellen im JSON-Response
        sources = [{
            "title":       p.get("title"),
            "link":        p.get("link"),
            "section_idx": p.get("section_idx"),
            "snippet":     (p.get("section_text","")[:200] + "…") if p.get("section_text") else "",
            "score":       p.get("score", 0)
        } for p in top_ctx]

        return jsonify(answer=answer, sources=sources)

    return app

if __name__ == "__main__":
    create_app().run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=os.getenv("DEBUG", "false").lower() in ("1","true","yes")
    )
