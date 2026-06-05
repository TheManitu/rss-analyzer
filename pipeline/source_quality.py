from urllib.parse import urlparse

from pipeline.text_quality import clean_article_text


OFFICIAL_DOMAINS = {
    "openai.com",
    "help.openai.com",
    "platform.openai.com",
    "chatgpt.com",
}

COMMUNITY_DOMAINS = {
    "reddit.com",
    "x.com",
    "twitter.com",
    "threads.net",
}

SPECULATION_TERMS = {
    "rumor",
    "rumour",
    "leak",
    "leaked",
    "spotted",
    "expected",
    "reported",
    "reportedly",
    "slated",
    "could",
    "might",
    "possibly",
    "unconfirmed",
    "speculation",
    "prediction market",
    "odds",
    "canary",
    "backend log",
    "codex log",
    "geruecht",
    "gerücht",
    "leak",
    "unbestätigt",
    "unbestaetigt",
    "vermutlich",
    "könnte",
    "koennte",
    "erwartet",
}


def source_domain(link: str) -> str:
    host = urlparse((link or "").strip()).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def is_official_source(link: str) -> bool:
    domain = source_domain(link)
    return any(domain == official or domain.endswith("." + official) for official in OFFICIAL_DOMAINS)


def is_community_source(link: str) -> bool:
    domain = source_domain(link)
    return any(domain == community or domain.endswith("." + community) for community in COMMUNITY_DOMAINS)


def has_speculation_signals(title: str, text: str) -> bool:
    combined = f"{clean_article_text(title)} {clean_article_text(text)}".lower()
    return any(term in combined for term in SPECULATION_TERMS)


def classify_source(link: str, title: str = "", text: str = "") -> dict:
    official = is_official_source(link)
    community = is_community_source(link)
    speculative = has_speculation_signals(title, text)

    if official:
        source_type = "official"
        score = 1.0
    elif community:
        source_type = "community"
        score = 0.25
    elif speculative:
        source_type = "speculative"
        score = 0.35
    else:
        source_type = "third_party"
        score = 0.6

    if speculative and not official:
        score = min(score, 0.35)

    return {
        "source_type": source_type,
        "credibility_score": score,
        "is_official": official,
        "is_speculative": speculative or community,
    }


def credibility_label(ctx: dict) -> str:
    source_type = ctx.get("source_type")
    if source_type == "official":
        return "offizielle Quelle"
    if ctx.get("is_speculative"):
        return "unbestätigte Quelle"
    if source_type == "third_party":
        return "Drittquelle"
    return source_type or "Quelle"
