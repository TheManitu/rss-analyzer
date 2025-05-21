# generation/prompt_template.py

"""
Prompt-Templates:
 - build_merge_prompt: kombiniere bis zu 500 Wörter aus allen Summaries
 - build_answer_prompt: Artikel-Übersicht + Meta-Summary → Antwort
 - (refine/finalize bleiben unverändert)
"""

def build_merge_prompt(contexts: list[dict], word_limit: int) -> str:
    header = (
        f"Fasse die folgenden Artikelsummaries **detailliert** zu einer einzigen "
        f"Meta-Zusammenfassung (max. {word_limit} Wörter) zusammen. "
        "Berücksichtige alle Kernaussagen vollständig.\n\n"
    )
    sections = []
    for idx, c in enumerate(contexts, start=1):
        sections.append(
            f"[{idx}] {c['title']}\n"
            f"Link: {c['link']}\n"
            f"Summary:\n{c['summary']}\n"
        )
    return header + "\n".join(sections)


def build_answer_prompt(question: str,
                        contexts: list[dict],
                        merged_summary: str) -> str:
    # Artikel-Übersicht (Titel + Link)
    articles = "Relevante Artikel:\n" + "\n".join(
        f"[{i+1}] {c['title']} – {c['link']}"
        for i, c in enumerate(contexts)
    ) + "\n\n"

    header = f"Frage: {question}\n\n"
    body = (
        articles +
        "Meta-Zusammenfassung:\n" +
        merged_summary + "\n\n"
    )
    footer = (
        "WICHTIG: Antworte ausschließlich auf Basis der obigen Meta-Zusammenfassung. "
        "Erfinde keine neuen Fakten oder Quellen. Antworte ausführlich und fließend in Deutsch."
    )
    return header + body + footer


# bestehende refine/finalize Prompts (falls benötigt)

def build_refine_prompt(question: str, contexts: list[dict], previous_answer: str) -> str:
    ctxs = contexts[:5]
    sections = [
        f"[{i+1}] {c['title']}\nSummary:\n{c['summary']}\n"
        for i, c in enumerate(ctxs)
    ]
    return (
        f"Frage: {question}\n\n"
        "Verfeinere die folgende Antwort ausschließlich anhand der oben genannten Artikelsummaries:\n\n"
        + "".join(sections)
        + f"\nVorherige Antwort:\n{previous_answer}\n"
        "\nAntworte direkt und prägnant in fließendem Deutsch, ohne neue Fakten."
    )

def build_finalize_prompt(question: str, contexts: list[dict], current_answer: str) -> str:
    return (
        f"Frage: {question}\n\n"
        f"Hier dein letzter Antwortentwurf:\n{current_answer}\n\n"
        "Formuliere nun die finale, prägnante Version der Antwort ausschließlich "
        "unter Verwendung der bereitgestellten Artikelsummaries."
    )
