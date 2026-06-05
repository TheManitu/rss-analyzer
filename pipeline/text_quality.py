import re
from html import unescape
from urllib.parse import urlparse

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional runtime dependency guard
    BeautifulSoup = None


WORD_RE = re.compile(r"\b[\w\-']+\b", re.UNICODE)
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")

BOILERPLATE_PATTERNS = [
    r"\badvertisement\b",
    r"\badvertorial\b",
    r"\bsponsored\b",
    r"\baffiliate\b",
    r"\bwe may earn (?:a )?commission\b",
    r"\bsign up\b",
    r"\bsubscribe\b",
    r"\bnewsletter\b",
    r"\blog in\b",
    r"\bregister\b",
    r"\baccept cookies\b",
    r"\bcookie settings\b",
    r"\bprivacy policy\b",
    r"\bterms of use\b",
    r"\ball rights reserved\b",
    r"\bshare this\b",
    r"\bplease enable javascript\b",
    r"\bthis article is also available in english\b",
    r"\btranslated with technical assistance\b",
    r"\beditorially reviewed before publication\b",
    r"\bweiterlesen\b",
    r"\babonnieren\b",
    r"\bnewsletter\b",
    r"\banzeige\b",
    r"\bwerbung\b",
    r"\bcookies?\b",
    r"\bdatenschutz\b",
    r"\bzum inhalt springen\b",
    r"\bmelde dich an\b",
    r"\bmelden sie sich an\b",
    r"\bzu seinem sechsten geburtstag\b",
    r"\bschreibenden zunft\b",
    r"\bzwischenstopps an der hochschule\b",
    r"\bschloss dort \d{4} seinen bachelor\b",
    r"\bredakteur(?:in)?\b",
]

BOILERPLATE_RE = re.compile("|".join(BOILERPLATE_PATTERNS), re.IGNORECASE)


def strip_html(text: str) -> str:
    """Return readable text from HTML or plain text."""
    value = unescape(text or "")
    if BeautifulSoup is not None and ("<" in value and ">" in value):
        soup = BeautifulSoup(value, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "button", "noscript", "svg", "iframe"]):
            tag.decompose()
        value = soup.get_text(separator="\n")
    else:
        value = TAG_RE.sub(" ", value)
    return re.sub(r"[ \t\f\v]+", " ", unescape(value)).strip()


def normalize_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", unescape(text or "")).strip()


def words(text: str) -> list[str]:
    return WORD_RE.findall(text or "")


def word_count(text: str) -> int:
    return len(words(text))


def is_boilerplate_line(line: str) -> bool:
    stripped = normalize_whitespace(line).strip(" -|")
    if not stripped:
        return True
    if len(stripped) <= 3:
        return True
    if BOILERPLATE_RE.search(stripped):
        return True
    line_words = words(stripped)
    if len(line_words) <= 4 and re.search(r"\b(menu|home|search|login|share|next|previous|rss)\b", stripped, re.I):
        return True
    return False


def clean_article_text(text: str) -> str:
    """Normalize text and drop obvious navigation, ads, cookie, and signup lines."""
    plain = strip_html(text)
    raw_lines = re.split(r"[\r\n]+|(?<=[.!?])\s+", plain)
    kept: list[str] = []
    seen = set()

    for raw in raw_lines:
        line = normalize_whitespace(raw)
        if is_boilerplate_line(line):
            continue
        fingerprint = line.lower()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        kept.append(line)

    return normalize_whitespace(" ".join(kept))


def boilerplate_density(text: str) -> float:
    lines = [normalize_whitespace(line) for line in re.split(r"[\r\n]+|(?<=[.!?])\s+", text or "") if normalize_whitespace(line)]
    if not lines:
        return 1.0
    bad = sum(1 for line in lines if is_boilerplate_line(line))
    return bad / len(lines)


def is_valid_source_link(link: str) -> bool:
    parsed = urlparse((link or "").strip())
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc:
        return False
    return True


def quality_reasons(text: str, min_words: int = 50) -> list[str]:
    clean = clean_article_text(text)
    terms = words(clean)
    reasons: list[str] = []

    if len(terms) < min_words:
        reasons.append(f"word_count<{min_words}")

    if clean:
        alnum = sum(1 for char in clean if char.isalnum() or char.isspace())
        if alnum / max(len(clean), 1) < 0.65:
            reasons.append("low_alnum_ratio")
    else:
        reasons.append("empty")

    if 30 <= len(terms) <= 1000:
        unique_ratio = len({term.lower() for term in terms}) / len(terms)
        if unique_ratio < 0.25:
            reasons.append("low_unique_word_ratio")

    if boilerplate_density(clean) > 0.35:
        reasons.append("high_boilerplate_density")

    if BOILERPLATE_RE.search(clean) and len(terms) < max(min_words * 2, 80):
        reasons.append("short_boilerplate_text")

    return reasons


def is_useful_article_text(text: str, min_words: int = 50) -> bool:
    return not quality_reasons(text, min_words=min_words)


def snippet(text: str, max_chars: int = 220) -> str:
    clean = clean_article_text(text)
    if len(clean) <= max_chars:
        return clean
    return clean[:max_chars].rsplit(" ", 1)[0].strip() + "..."
