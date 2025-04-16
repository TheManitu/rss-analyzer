"""
Diese Datei enthält Funktionen zur Erstellung von Prompts für das Retrieval-Augmented Generation (RAG)-Modul.
Die generierten Prompts zielen darauf ab, die Antwortqualität zu verbessern, indem sie die Antwort in drei
Stufen – Initial, Refinement und Finalisierung – anleiten.

Die erstellten Prompts fordern eine präzise, fundierte und formale Darstellung, die einem Fachartikel ähnelt.
Besonderer Fokus liegt auf der Beschreibung neuester Fortschritte der KI-Technologie und deren Auswirkungen
auf Social-Media-Plattformen sowie Implikationen für zukünftige Metaverse-Entwicklungen.
"""

def build_initial_prompt(question: str, article_info: str) -> str:
    """
    Erzeugt den initialen Prompt für die Antwortgenerierung.
    
    :param question: Die Benutzerfrage.
    :param article_info: Die zusammengefassten Artikelinformationen.
    :return: Den initialen Prompt als String.
    """
    prompt = (
        f"Frage: {question}\n\n"
        f"Artikelinformationen:\n{article_info}\n\n"
        "Bitte verfasse eine präzise, fundierte und gut strukturierte Antwort in fließendem Deutsch, "
        "die alle wesentlichen Informationen aus den Artikeln berücksichtigt. Die Antwort soll formal klingen "
        "und einem Auszug aus einem Fachartikel ähneln, der die neuesten Fortschritte in der KI-Technologie und "
        "deren Auswirkungen auf Social-Media-Plattformen thematisiert – inklusive Implikationen für zukünftige "
        "Entwicklungen im Metaverse. Verwende, wenn möglich, konkrete Beispiele (z. B. aus Forrester-Studien) und "
        "gib ausschließlich das finale Ergebnis ohne zusätzlichen Denktext aus."
    )
    return prompt

def build_refine_prompt(question: str, article_info: str, previous_answer: str) -> str:
    """
    Erzeugt den Prompt zur Verbesserung (Refinement) der bisher generierten Antwort.
    
    :param question: Die Benutzerfrage.
    :param article_info: Die zusammengefassten Artikelinformationen.
    :param previous_answer: Die bisher generierte Antwort.
    :return: Den Refinement-Prompt als String.
    """
    prompt = (
        f"Frage: {question}\n\n"
        "Die bisher erstellte Antwort scheint nicht alle wesentlichen Informationen der Artikel abzudecken oder "
        "ist unzureichend strukturiert. Bitte verbessere die Antwort, indem du alle wichtigen Details aus "
        "den folgenden Artikelinformationen berücksichtigst.\n\n"
        f"Vorherige Antwort: {previous_answer}\n\n"
        f"Artikelinformationen:\n{article_info}\n\n"
        "Formuliere eine präzisere, fließend strukturierte und umfassende Antwort in gutem, formalen Deutsch. "
        "Gib ausschließlich das finale Ergebnis ohne zusätzlichen Erklärtext oder Denkprozesse aus."
    )
    return prompt

def build_finalize_prompt(question: str, current_answer: str) -> str:
    """
    Erzeugt den finalen Prompt, um die endgültige Version der Antwort zu verfeinern und zusammenzufassen.
    
    :param question: Die Benutzerfrage.
    :param current_answer: Die bis dato generierte Antwort.
    :return: Den Finalisierungs-Prompt als String.
    """
    prompt = (
        f"Frage: {question}\n\n"
        "Basierend auf der untenstehenden Antwort, formuliere abschließend eine präzise, gut strukturierte und "
        "zusammenfassende Antwort, die alle wesentlichen Informationen klar darstellt. Die Antwort soll formell "
        "klingen, wie ein Auszug aus einem Fachartikel, der die neuesten Entwicklungen in der KI-Technologie sowie "
        "die damit verbundenen Auswirkungen auf Social-Media-Plattformen und zukünftige Metaverse-Entwicklungen erläutert. "
        "Verwende, wenn angebracht, konkrete Beispiele und erläutere Zusammenhänge prägnant.\n\n"
        f"Aktuelle Antwort: {current_answer}\n\n"
        "Gib ausschließlich das finale Endergebnis ohne zusätzliche Erklärungen oder Zwischenüberlegungen aus."
    )
    return prompt

if __name__ == "__main__":
    # Beispielhafte Nutzung der Prompt-Building-Funktionen
    beispiel_frage = "Was gibt es Neues zu Windows?"
    beispiel_artikel_info = (
        "Artikel 1: Update außer der Reihe: Microsoft korrigiert Richtlinien-Anzeigefehler\n"
        "Artikel 2: Neuer Mainframe von IBM – und natürlich mit KI\n"
        "Artikel 3: Windows 11 24H2: Update-Blocker wegen Wallpaper-Apps gelöst\n"
        "Artikel 4: heise-Angebot: iX-Workshop: Von C++ zu Rust - Jump Start in die moderne Systemsprache\n"
        "Artikel 5: Missing Link: 'Der große Plan'\n"
        "..."
    )
    beispiel_vorherige_antwort = "Bisherige Antwort: ..."

    print("Initial Prompt:\n", build_initial_prompt(beispiel_frage, beispiel_artikel_info))
    print("\nRefine Prompt:\n", build_refine_prompt(beispiel_frage, beispiel_artikel_info, beispiel_vorherige_antwort))
    print("\nFinalize Prompt:\n", build_finalize_prompt(beispiel_frage, beispiel_vorherige_antwort))
