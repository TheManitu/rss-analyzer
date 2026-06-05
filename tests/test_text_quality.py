from pipeline.text_quality import clean_article_display_text, clean_article_text, clean_display_text, is_useful_article_text, is_valid_source_link


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


def test_clean_article_text_repairs_common_feed_mojibake():
    raw = "OpenAI\u00e2\u20ac\u2122s GPT-5.6 \u00e2\u20ac\u201d Qualit\u00c3\u00a4t, Gr\u00c3\u00b6\u00c3\u009fe und neue Hinweise\u00e2\u20ac\u00a6"

    cleaned = clean_article_text(raw)

    assert "OpenAI's GPT-5.6" in cleaned
    assert "Qualität" in cleaned
    assert "Größe" in cleaned
    assert "Hinweise..." in cleaned
    assert "\u00e2" not in cleaned
    assert "\u00c3" not in cleaned
    assert "\u00c2" not in cleaned
    assert "\ufffd" not in cleaned


def test_clean_display_text_repairs_existing_stored_titles_without_boilerplate_drop():
    title = "GPT-5.6 in OpenAI\u00e2\u0080\u0099s Codex Logs \u00e2\u0080\u0094 was dahinter steckt"

    cleaned = clean_display_text(title)

    assert cleaned == "GPT-5.6 in OpenAI's Codex Logs - was dahinter steckt"


def test_clean_article_text_removes_markdown_artifacts_from_scraped_sources():
    raw = (
        "## GPT-5.5 Instant Update ## We're updating **GPT-5.5 Instant** in ChatGPT. "
        "Learn more: [Managing active sessions](https://help.openai.com/articles/20001257). "
        "* Review sessions from settings."
    )

    cleaned = clean_article_text(raw)
    display = clean_article_display_text(raw, sentences_per_paragraph=1)

    assert "GPT-5.5 Instant Update" in cleaned
    assert "GPT-5.5 Instant in ChatGPT" in cleaned
    assert "Managing active sessions" in cleaned
    assert "##" not in cleaned
    assert "**" not in cleaned
    assert "](" not in cleaned
    assert "\n\n" in display


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
