from flask import Flask
from api.utils import extract_topic_from_question

app = Flask(__name__)
# Falls du SYN_WEIGHT aus config.py brauchst:
from config import SYN_WEIGHT
app.config['SYN_WEIGHT'] = SYN_WEIGHT

with app.app_context():
    test_cases = {
        "Was ist neu bei GPT-4?": "OpenAI und GPT-Modelle",
        "Infos zur neuen Azure Copilot-Funktion": "Microsoft AI & Azure",
        # ...
    }
    for q, exp in test_cases.items():
        got = extract_topic_from_question(q)
        print(f"Q={q!r}\n → got: {got!r}, expected: {exp!r}\n")
