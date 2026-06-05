from flask import Flask

from api.utils import extract_topic_from_question
from config import SYN_WEIGHT


def test_extract_topic_from_question():
    app = Flask(__name__)
    app.config["SYN_WEIGHT"] = SYN_WEIGHT

    with app.app_context():
        assert extract_topic_from_question("Was ist neu bei GPT-4?") == "OpenAI & GPT-Modelle"
        assert extract_topic_from_question("Infos zur neuen Azure Copilot-Funktion") == "Microsoft AI & Azure"
        assert extract_topic_from_question("Welche Kubernetes Features sind neu?") == "Container & Kubernetes"
        assert extract_topic_from_question("Was ist heute wichtig?") == "Allgemein"
