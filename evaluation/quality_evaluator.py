"""
Optionale Qualitätsprüfung: Validierung der Quellenbezüge in der Antwort.
"""
import re

class QualityEvaluator:
    def __init__(self, threshold: float = 1.0):
        """Init mit Score-Schwelle für Flagging."""
        self.threshold = threshold

    def evaluate(self, answer: str, contexts: list) -> dict:
        """
        Überprüft, ob die in der Antwort referenzierten Quellen mit den gelieferten Kontexten übereinstimmen.
        :param answer: Generierter Antworttext mit Referenzen [1], [2], ...
        :param contexts: Liste der Kontext-Dicts
        :return: Dict mit 'score' (0.0–1.0) und 'flag' (True, wenn score < threshold)
        """
        refs = re.findall(r"\[(\d+)\]", answer)
        total = len(refs)
        valid = sum(1 for r in refs if 1 <= int(r) <= len(contexts))
        score = valid / total if total > 0 else 1.0
        flag = score < self.threshold
        return {"score": score, "flag": flag}
