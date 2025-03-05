import os
from flask import Flask, render_template, request, jsonify
from rss_analyzer.database import get_all_articles
from rss_analyzer import rag

# Ermitteln des Projektstamms (Ordner, der 'rss_analyzer', 'templates' und 'static' enthält)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Flask-App erstellen und das Template- sowie Static-Verzeichnis explizit setzen
app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

def first_words(s, num_words=250):
    import re
    if not s:
        return ""
    clean = re.sub('<.*?>', '', s)
    words = clean.split()
    if len(words) > num_words:
        return " ".join(words[:num_words]) + "..."
    return clean

def truncatewords(s, num_words=500):
    if not s:
        return ""
    words = s.split()
    if len(words) > num_words:
        return " ".join(words[:num_words]) + "..."
    return s

# Filter registrieren
app.add_template_filter(first_words, "first_words")
app.add_template_filter(truncatewords, "truncatewords")

@app.route("/", methods=["GET", "POST"])
def index():
    answer = ""
    sources = ""
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        if question:
            sources = rag.get_sources(question)
            answer = rag.get_detailed_answer(question)
    # Hier setzen wir top_articles optional (kann später durch eine Funktion befüllt werden)
    top_articles = []
    articles = get_all_articles(time_filter=request.args.get("time_filter", "today"))
    return render_template("index.html", top_articles=top_articles, articles=articles, answer=answer, sources=sources)

@app.route("/search", methods=["POST"])
def search():
    data = request.get_json()
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"answer": "Bitte geben Sie eine Frage ein.", "sources": ""})
    sources = rag.get_sources(question)
    answer = rag.get_detailed_answer(question)
    return jsonify({"answer": answer, "sources": sources})

if __name__ == "__main__":
    app.run(debug=True)
