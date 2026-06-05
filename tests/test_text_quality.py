from pipeline.text_quality import clean_article_text, is_useful_article_text, is_valid_source_link


def test_clean_article_text_removes_boilerplate():
    raw = """
    <nav>Home Search Login</nav>
    <p>Advertisement</p>
    <article>
      <p>Kubernetes erweitert seine Sicherheitsfunktionen fuer Cluster und Workloads.</p>
      <p>Die neue Version verbessert Automatisierung, Richtlinien und Deployment-Prozesse fuer Plattformteams.</p>
      <p>Sign up for our newsletter</p>
    </article>
    """

    cleaned = clean_article_text(raw)

    assert "Advertisement" not in cleaned
    assert "newsletter" not in cleaned.lower()
    assert "Kubernetes erweitert" in cleaned
    assert "Deployment-Prozesse" in cleaned


def test_is_useful_article_text_rejects_ad_only_content():
    bad = "Advertisement. Sign up for our newsletter. Accept cookies. Privacy policy."
    good = (
        "OpenAI veroeffentlicht ein neues Modell fuer Entwickler. "
        "Der Artikel beschreibt konkrete Funktionen, API-Aenderungen, Risiken und Beispiele. "
        "Mehrere Quellen erklaeren Auswirkungen auf Produktentwicklung und Automatisierung."
    )

    assert not is_useful_article_text(bad, min_words=5)
    assert is_useful_article_text(good, min_words=20)


def test_is_useful_article_text_rejects_author_bio_scrape():
    bio = (
        "Zu seinem sechsten Geburtstag bekam Silas einen Gameboy geschenkt, was bei ihm eine "
        "Leidenschaft fuer die Tech- und Gaming-Welt entfachte. Mit zwei linken Haenden gesegnet, "
        "ueberliess er das Tuefteln anderen und entschied sich stattdessen fuer die schreibende Zunft. "
        "Nach Zwischenstopps an der Hochschule Mannheim schloss er dort 2018 seinen Bachelor ab."
    )

    assert not is_useful_article_text(bio, min_words=20)


def test_source_links_must_be_http_urls():
    assert is_valid_source_link("https://example.com/article")
    assert is_valid_source_link("http://example.com/article")
    assert not is_valid_source_link("javascript:alert(1)")
    assert not is_valid_source_link("/relative/path")
