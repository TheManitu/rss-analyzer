# api/analytics.py

from flask import Blueprint, render_template, redirect, url_for, current_app
import duckdb
from config import DB_PATH
from storage.topic_tracker import get_all_topics

analytics_bp = Blueprint("analytics", __name__)

@analytics_bp.route("/dashboard")
def dashboard():
    topics = get_all_topics()
    return render_template("dashboard.html", topics=topics)

@analytics_bp.route("/analytics")
def analytics():
    con = duckdb.connect(DB_PATH, read_only=True)
    top_questions = con.execute("""
        SELECT question, COUNT(*) AS cnt
        FROM question_events
        GROUP BY question
        ORDER BY cnt DESC
        LIMIT 10
    """).fetchall()
    questions_by_hour = con.execute("""
        SELECT SUBSTR(CAST(timestamp AS VARCHAR),12,2) AS hour, COUNT(*) AS cnt
        FROM question_events
        GROUP BY hour
        ORDER BY hour
    """).fetchall()
    top_articles = con.execute("""
        SELECT link, view_count AS cnt
        FROM article_metrics
        ORDER BY view_count DESC
        LIMIT 10
    """).fetchall()
    con.close()
    return render_template(
        "analytics.html",
        top_questions=top_questions,
        questions_by_hour=questions_by_hour,
        top_articles=top_articles
    )

@analytics_bp.route("/audit")
def audit():
    con = duckdb.connect(DB_PATH, read_only=True)
    rows = con.execute(
        "SELECT link AS article_id, event_type, timestamp "
        "FROM events_audit ORDER BY timestamp DESC LIMIT 50"
    ).fetchall()
    con.close()
    return render_template("audit.html", audit=rows)

@analytics_bp.route("/redirect_to_dashboard")
def redirect_dash():
    return redirect(url_for("analytics.dashboard"))
