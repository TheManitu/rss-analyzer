# generation/prompt_template.py

"""
Prompt-Templates für initiale, refine- und finalize-Schritte,
optimiert für direkte, prägnante und selbstbewusste Antworten.
Antworten sollen zwischen 100 und 300 Wörtern umfassen,
sofern genügend Informationen vorliegen.
"""

def build_initial_prompt(question: str, contexts: list) -> str:
    contexts = contexts[:5]
    source_section = "\n\n".join(
        f"[{i+1}] {c['title']}\nSummary: {c.get('summary','')}"
        for i, c in enumerate(contexts)
    )
    return (
        f"Frage: {question}\n\n"
        "Du erhältst die folgenden Artikelsummaries (max. 5):\n"
        f"{source_section}\n\n"
        "Fasse zuerst kurz und prägnant den Inhalt dieser Summaries zusammen "
        "und beantworte anschließend die Frage direkt auf Basis dieser Informationen. "
        "Verwende ausschließlich diese Artikeldaten, erfinde keine Fakten oder Quellen. "
        "Vermeide Einleitungen, Füllsätze und Wiederholungen. "
        "Antworte in selbstbewusstem Ton und fließendem Deutsch. "
        "Deine Antwort sollte mindestens 100 und höchstens 300 Wörter umfassen, "
        "falls genügend Informationen vorhanden sind. "
        "Sind nicht ausreichend Daten verfügbar, gib das kurz an und antworte prägnant."
    )

def build_refine_prompt(question: str, contexts: list, previous_answer: str) -> str:
    contexts = contexts[:5]
    source_section = "\n\n".join(
        f"[{i+1}] {c['title']}\nSummary: {c.get('summary','')}"
        for i, c in enumerate(contexts)
    )
    return (
        f"Frage: {question}\n\n"
        "Verfeinere die folgende Antwort ausschließlich anhand der oben genannten Artikelsummaries. "
        "Erfinde keine neuen Fakten oder Quellen. Entferne redundante Informationen und Füllsätze. "
        "Achte darauf, dass die finale Antwort zwischen 100 und 300 Wörtern liegt. "
        "Antworte direkt und prägnant in selbstbewusstem Ton und fließendem Deutsch.\n\n"
        f"{source_section}\n\n"
        f"Vorherige Antwort:\n{previous_answer}"
    )

def build_finalize_prompt(question: str, contexts: list, current_answer: str) -> str:
    return (
        f"Frage: {question}\n\n"
        "Hier ist dein letzter Antwortentwurf. Formuliere nun die finale Version DIREKT, PRÄGNANT und "
        "SELBSTBEWUSST in fließendem Deutsch. Nutze ausschließlich die bereitgestellten Artikelsummaries, "
        "erfinde keine neuen Fakten oder Quellen. Entferne Wiederholungen und Füllsätze. "
        "Stelle sicher, dass die Antwort zwischen 100 und 300 Wörtern umfasst. "
        "Füge keine Quellenliste am Ende hinzu.\n\n"
        f"Antwort-Entwurf:\n{current_answer}"
    )
