# generation/prompt_template.py

from config import LLM_MODEL_INITIAL, LLM_MODEL_REFINE

def build_initial_prompt(question: str, contexts: list) -> str:
    """
    Erster Prompt:
    - Maximal 5 Artikel verwenden
    - Relevantesten Artikel vollständig zusammenfassen (max. 500 Wörter)
    - Alle anderen in Kurzform (max. 200 Zeichen)
    - Deutsch, formell, keine neuen Quellen
    - Quellenreferenzen nur [1]–[5] im Text
    - Quellenverzeichnis wird in der UI gerendert
    """
    # nur Top 5 Kontexte weitergeben
    contexts = contexts[:5]
    source_section = "\n\n".join(
        f"[{i+1}] Title: {c['title']}\nLink: {c['link']}\nContent: {c.get('text', c.get('content',''))}"
        for i, c in enumerate(contexts)
    )

    return (
        f"Frage: {question}\n\n"
        "Vorliegende Artikelquellen (maximal 5):\n"
        f"{source_section}\n\n"
        "Bitte beantworte **ausschließlich** anhand dieser Artikelquellen und erfinde **keine** weiteren. "
        "Bestimme den **relevantesten** Artikel zur Frage und fasse seinen gesamten Inhalt **vollständig** in **maximal 500 Wörtern** zusammen. "
        "Fasse **alle übrigen** Artikel nur in einer **Kurzbeschreibung** (max. 200 Zeichen) zusammen. "
        "Formuliere **prägnant und formell auf Deutsch** und zitiere jede Quelle im Text nur als [1] bis [5]. "
        "Das nummerierte Quellenverzeichnis wird in der UI separat als klickbare Links angezeigt."
    )

def build_refine_prompt(question: str, contexts: list, previous_answer: str) -> str:
    """
    Refinement-Prompt:
    - Gleiche Vorgaben wie initial
    - Erneute Betonung von 5 Quellen, Deutsch, keine „Quellen:“-Zeile im Fließtext
    """
    contexts = contexts[:5]
    source_section = "\n\n".join(
        f"[{i+1}] Title: {c['title']}\nContent: {c.get('text', c.get('content',''))}"
        for i, c in enumerate(contexts)
    )

    return (
        f"Frage: {question}\n\n"
        "Verfeinere die Antwort **ausschließlich** anhand der oben genannten Artikelquellen (maximal 5). "
        "Erfinde **keine** neuen Quellen. "
        "Fasse den relevantesten Artikel vollständig (max. 500 Wörter) und alle anderen kurz (max. 200 Zeichen) zusammen. "
        "Formuliere **prägnant und formell auf Deutsch** und zitiere nur [1]–[5] im Text. "
        "Das Quellenverzeichnis wird in der UI gerendert.\n\n"
        f"{source_section}\n\n"
        f"Vorherige Antwort: {previous_answer}\n\n"
        "Gib nur das verbesserte Ergebnis **ohne** zusätzliche Erklärungen aus."
    )

def build_finalize_prompt(question: str, current_answer: str) -> str:
    """
    Final-Prompt:
    - Letzte Erinnerung an Deutsch, Formell, Referenzen [1]–[5]
    - Keine „Quellen:“ im Fließtext
    - UI rendert klickenbare Links
    """
    return (
        f"Frage: {question}\n\n"
        f"Antwort‑Entwurf: {current_answer}\n\n"
        "Formuliere die finale Version **prägnant, fehlerfrei und formell auf Deutsch**. "
        "Verwende im Fließtext nur Quellenreferenzen [1]–[5] – **ohne** eine Quellenüberschrift. "
        "Das nummerierte Quellenverzeichnis mit klickbaren Links wird in der UI angezeigt."
    )
