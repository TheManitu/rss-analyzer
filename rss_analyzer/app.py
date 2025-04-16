# app.py – Flask-Webanwendung

import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from rss_analyzer.database import get_all_articles, create_table
from rss_analyzer import rag
from rss_analyzer.topic_db import create_topic_table, update_topic, get_all_topics, print_topic_overview
from rss_analyzer.config import TOPIC_MAPPING
from kafka import KafkaProducer
import json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

producer = KafkaProducer(
    bootstrap_servers=['rss-kafka-ingest:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def extract_topic_from_question(question):
    question_lower = question.lower()
    for topic, data in TOPIC_MAPPING.items():
        for kw in data["keywords"]:
            if kw in question_lower:
                return topic
    return "Allgemein"

# Dummy-Implementierung für get_common_questions
def get_common_questions():
    """
    Diese Funktion gibt aggregierte Daten zu häufig gestellten Fragen zurück.
    Hier als Dummy-Implementierung – in der Praxis könntest Du Kafka/Spark verwenden,
    um echte Nutzerdaten zu aggregieren und in einer Tabelle zu speichern.
    """
    return [
        {"question": "Was gibt es Neues zu Windows?", "count": 15, "window": "2025-04-15 13:00-14:00"},
        {"question": "Was gibt es Neues zu ChatGPT?", "count": 10, "window": "2025-04-15 13:00-14:00"}
    ]

@app.template_filter()
def first_words(s, num_words=250):
    import re
    if not s:
        return ""
    clean = re.sub('<.*?>', '', s)
    words = clean.split()
    if len(words) > num_words:
        return " ".join(words[:num_words]) + "..."
    return clean

@app.template_filter()
def truncatewords(s, num_words=500):
    if not s:
        return ""
    words = s.split()
    if len(words) > num_words:
        return " ".join(words[:num_words]) + "..."
    return s

@app.route("/", methods=["GET", "POST"])
def index():
    answer = ""
    sources = ""
    try:
        if request.method == "POST":
            question = request.form.get("question", "").strip()
            if question:
                topic = extract_topic_from_question(question)
                update_topic(topic, delta=1)
                message = {"question": question, "topic": topic}
                producer.send("UserQuestions", message)
                sources = rag.get_sources(question)
                answer = rag.get_detailed_answer(question)
    except Exception as e:
        answer = f"Fehler in der Anfrageverarbeitung: {e}"
    top_articles = []
    articles = get_all_articles(time_filter=request.args.get("time_filter", "today"))
    return render_template("index.html", top_articles=top_articles, articles=articles, answer=answer, sources=sources)

@app.route("/search", methods=["POST"])
def search():
    try:
        data = request.get_json()
        question = data.get("question", "").strip()
        if not question:
            return jsonify({"answer": "Bitte geben Sie eine Frage ein.", "sources": ""})
        topic = extract_topic_from_question(question)
        update_topic(topic, delta=1)
        message = {"question": question, "topic": topic}
        producer.send("UserQuestions", message)
        sources = rag.get_sources(question)
        answer = rag.get_detailed_answer(question)
        return jsonify({"answer": answer, "sources": sources})
    except Exception as e:
        return jsonify({"answer": f"Fehler in der Anfrageverarbeitung: {e}", "sources": ""})

@app.route("/dashboard", methods=["GET"])
def dashboard():
    topics = get_all_topics()
    return render_template("dashboard.html", topics=topics)

@app.route("/analytics", methods=["GET"])
def analytics():
    # Nutzt die Dummy-Implementierung von get_common_questions, um aggregierte Nutzungsdaten zu liefern.
    common_questions = get_common_questions()
    return render_template("analytics.html", questions=common_questions)

# Optional: Weiterleitung von /analytics zu /dashboard (oder umgekehrt)
@app.route("/redirect_to_dashboard")
def redirect_to_dashboard():
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    create_table()
    create_topic_table()
    print_topic_overview()
    app.run(host="0.0.0.0", port=5000, debug=True)
