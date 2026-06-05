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
            f"[{idx}] {c.get('title', 'Ohne Titel')}\n"
            f"Link: {c.get('link', '')}\n"
            f"Quellentyp: {c.get('source_type', 'unbekannt')}\n"
            f"Summary:\n{c.get('summary') or c.get('text') or c.get('content') or ''}\n"
        )
    return header + "\n".join(sections)


def build_answer_prompt(question: str,
                        contexts: list[dict],
                        merged_summary: str) -> str:
    # Artikel-Übersicht (Titel + Link)
    articles = "Relevante Artikel:\n" + "\n".join(
        f"[{i+1}] {c.get('title', 'Ohne Titel')} - {c.get('link', '')}"
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
        "Erfinde keine neuen Fakten oder Quellen. Belege jede zentrale Aussage mit "
        "Quellenmarkern wie [1] oder [2]. Wenn die Quellen die Frage nicht beantworten, "
        "sage klar, dass keine ausreichenden Daten in den Artikeln vorliegen. Gehe direkt "
        "auf die konkrete Nutzerfrage ein: beantworte erst die eigentliche Frage, danach "
        "ordne Details und Einschraenkungen ein. Schreibe in fluessigem Deutsch mit "
        "vollstaendigen Saetzen und kurzen Absaetzen; nutze Stichpunkte nur, wenn eine "
        "echte Aufzaehlung besser lesbar ist. Schneide relevante Einordnungen nicht ab. "
        "Strukturiere die Antwort mit den Abschnitten Kurzfazit, Gesicherter Stand, "
        "Feature-Einschaetzung, Release-Stand, Diskutierte unbestaetigte Hinweise "
        "und Quellenlage, wenn die Frage nach einem unveroeffentlichten oder "
        "versionierten Modell fragt. Behandle Geruechte, Leaks und Community-Posts nie "
        "als bestaetigte Produktinformationen, sondern erklaere ihre Aussagekraft im Text."
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
