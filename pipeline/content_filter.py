# pipeline/content_filter.py

class ContentFilter:
    """
    Einfacher Content-Filter für RAG: entfernt sehr kurze Passagen.
    """

    def __init__(self, min_length: int = 50):
        # Minimalzahl Worte pro Passage
        self.min_length = min_length

    def filter(self, passages: list[str]) -> list[str]:
        """
        Filtert alle Passagen mit weniger als min_length Wörtern heraus.
        :param passages: Liste von Text-Segmenten
        :return: Gefilterte Liste, nur Passagen >= min_length
        """
        return [
            p for p in passages
            if len(p.split()) >= self.min_length
        ]
