from flask import Flask

from api.rag import answer_question, context_limit_for_question
from config import SYN_WEIGHT


class FakeRetriever:
    def retrieve(self, question):
        return [
            {
                "title": "OpenAI API Update",
                "link": "https://news.example/openai-api",
                "text": "OpenAI aktualisiert seine API mit neuen Werkzeugen fuer Entwickler und besseren Sicherheitsfunktionen.",
                "score": 0.95,
            },
            {
                "title": "Newsletter",
                "link": "https://news.example/newsletter",
                "text": "Advertisement. Sign up for our newsletter. Accept cookies.",
                "score": 0.9,
            },
            {
                "title": "Bad URL",
                "link": "javascript:alert(1)",
                "text": "OpenAI Meldung mit ungueltiger Quelle.",
                "score": 0.8,
            },
        ]


class FakeStorage:
    rows = {
        "https://news.example/openai-api": (
            "OpenAI\u00e2\u20ac\u2122s API Update",
            "OpenAI aktualisiert seine API mit neuen Werkzeugen fuer Entwickler, besserer Kontrolle und zusaetzlichen Sicherheitsfunktionen. Teams koennen Integrationen dadurch stabiler bauen.",
            "",
            "",
        ),
        "https://news.example/newsletter": (
            "Newsletter",
            "Advertisement. Sign up for our newsletter. Accept cookies.",
            "",
            "",
        ),
    }

    def connect(self, read_only=False):
        return FakeConnection(self.rows)


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.link = None

    def execute(self, query, params=()):
        self.link = params[0]
        return self

    def fetchone(self):
        return self.rows.get(self.link)

    def close(self):
        pass


class FakeGenerator:
    def generate(self, question, contexts):
        return f"{contexts[0]['title']} nennt neue API-Werkzeuge und Sicherheitsfunktionen [1]."


class FakeEvaluator:
    def evaluate(self, answer, contexts):
        return {"score": 1.0, "flag": False}


def test_answer_question_returns_quality_sources_only():
    app = Flask(__name__)
    app.config["SYN_WEIGHT"] = SYN_WEIGHT
    app.storage = FakeStorage()
    app.retriever = FakeRetriever()
    app.generator = FakeGenerator()
    app.evaluator = FakeEvaluator()

    with app.app_context():
        answer, sources, contexts, passages, topic, eval_res = answer_question("Was ist neu bei OpenAI?")

    assert "OpenAI's API Update" in answer
    assert "[1]" in answer
    assert topic == "OpenAI & GPT-Modelle"
    assert len(sources) == 1
    assert sources[0]["title"] == "OpenAI's API Update"
    assert sources[0]["link"] == "https://news.example/openai-api"
    assert sources[0]["source_type"] == "third_party"
    assert sources[0]["domain"] == "news.example"
    assert "Drittquelle" in sources[0]["discussion"]
    assert "GPT-/OpenAI-Fragen" in sources[0]["discussion"]
    assert sources[0]["credibility_score"] > 0
    assert "\u00e2" not in sources[0]["title"]
    assert all("newsletter" not in source["snippet"].lower() for source in sources)
    assert len(contexts) == 1
    assert len(passages) == 3
    assert eval_res["flag"] is False


def test_context_limit_expands_for_leak_questions():
    assert context_limit_for_question("Was sind die geleakten Informationen zu GPT-5.6?") >= 7
    assert context_limit_for_question("Was ist neu bei OpenAI?") == 5
