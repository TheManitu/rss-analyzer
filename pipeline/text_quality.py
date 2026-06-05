import re
import unicodedata
from html import unescape
from urllib.parse import urlparse

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional runtime dependency guard
    BeautifulSoup = None


WORD_RE = re.compile(r"\b[\w\-']+\b", re.UNICODE)
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
CONTROL_RE = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f]")
MOJIBAKE_RE = re.compile(r"[\u00c2\u00c3\u00e2\ufffd]")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((?:https?://|mailto:)[^)]+\)")
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
MARKDOWN_HEADING_RE = re.compile(r"(?m)(^|\s)#{1,6}\s+")
MARKDOWN_CLOSING_HEADING_RE = re.compile(r"\s+#{1,6}(\s|$)")
MARKDOWN_STRONG_RE = re.compile(r"(\*\*|__)")

MOJIBAKE_REPLACEMENTS = {
    "\u00e2\u20ac\u2122": "'",
    "\u00e2\u0080\u0099": "'",
    "\u00e2\u20ac\u02dc": "'",
    "\u00e2\u0080\u0098": "'",
    "\u00e2\u20ac\u0153": '"',
    "\u00e2\u0080\u009c": '"',
    "\u00e2\u20ac\u009d": '"',
    "\u00e2\u0080\u009d": '"',
    "\u00e2\u20ac\u201c": " - ",
    "\u00e2\u0080\u0093": " - ",
    "\u00e2\u20ac\u201d": " - ",
    "\u00e2\u0080\u0094": " - ",
    "\u00e2\u20ac\u00a6": "...",
    "\u00e2\u0080\u00a6": "...",
    "\u00e2\u20ac\u00a2": "-",
    "\u00e2\u0080\u00a2": "-",
    "\u00e2\u201e\u00a2": "TM",
    "\u00e2\u0084\u00a2": "TM",
    "\u00c2\u00a0": " ",
    "\u00c2\u00ad": "",
    "\u00c2\u00a9": "©",
    "\u00c2\u00ae": "®",
    "\u00c3\u0084": "Ä",
    "\u00c3\u0096": "Ö",
    "\u00c3\u009c": "Ü",
    "\u00c3\u00a4": "ä",
    "\u00c3\u00b6": "ö",
    "\u00c3\u00bc": "ü",
    "\u00c3\u009f": "ß",
    "\u00c3\u00a9": "é",
    "\u00c3\u00a8": "è",
    "\u00c3\u00a1": "á",
    "\u00c3\u00a0": "à",
    "\u00c3\u00b3": "ó",
    "\u00c3\u00b2": "ò",
    "\u00c3\u00ba": "ú",
    "\u00c3\u00b1": "ñ",
    "\u00c3\u00a7": "ç",
}

TYPOGRAPHIC_REPLACEMENTS = {
    "’": "'",
    "‘": "'",
    "“": '"',
    "”": '"',
    "–": " - ",
    "—": " - ",
    "…": "...",
    "•": "-",
}

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


def _mojibake_score(text: str) -> int:
    return len(MOJIBAKE_RE.findall(text or "")) + len(CONTROL_RE.findall(text or "")) + (text or "").count("\ufffd") * 3


def repair_text_encoding(text: str) -> str:
    """Repair common UTF-8 mojibake from feeds while preserving normal Unicode text."""
    value = text or ""
    if not value:
        return ""

    if _mojibake_score(value):
        best = value
        best_score = _mojibake_score(value)
        for encoding in ("latin-1", "cp1252"):
            try:
                candidate = value.encode(encoding).decode("utf-8")
            except UnicodeError:
                continue
            candidate_score = _mojibake_score(candidate)
            if candidate_score < best_score and len(candidate) >= max(1, int(len(value) * 0.7)):
                best = candidate
                best_score = candidate_score
        value = best

    for broken, fixed in MOJIBAKE_REPLACEMENTS.items():
        value = value.replace(broken, fixed)
    for typographic, plain in TYPOGRAPHIC_REPLACEMENTS.items():
        value = value.replace(typographic, plain)

    value = CONTROL_RE.sub("", value)
    value = value.replace("\ufffd", "")
    return unicodedata.normalize("NFKC", value)


def strip_markdown_artifacts(text: str) -> str:
    value = text or ""
    if not value:
        return ""
    value = MARKDOWN_IMAGE_RE.sub(r"\1", value)
    value = MARKDOWN_LINK_RE.sub(r"\1", value)
    value = re.sub(r"\[([^\]]+)\]", r"\1", value)
    value = MARKDOWN_HEADING_RE.sub(lambda match: "\n\n" if match.group(1).strip() == "" else "\n\n", value)
    value = MARKDOWN_CLOSING_HEADING_RE.sub("\n\n", value)
    value = re.sub(r"(?m)^\s*[-*+]\s+", "- ", value)
    value = re.sub(r"\s+\*\s+", " ", value)
    value = MARKDOWN_STRONG_RE.sub("", value)
    value = re.sub(r"(?<!\w)\*([^*\n]+)\*(?!\w)", r"\1", value)
    value = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"\1", value)
    return value


def strip_html(text: str) -> str:
    """Return readable text from HTML or plain text."""
    value = repair_text_encoding(unescape(text or ""))
    if BeautifulSoup is not None and ("<" in value and ">" in value):
        soup = BeautifulSoup(value, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "button", "noscript", "svg", "iframe"]):
            tag.decompose()
        value = soup.get_text(separator="\n")
    else:
        value = TAG_RE.sub(" ", value)
    value = strip_markdown_artifacts(value)
    return re.sub(r"[ \t\f\v]+", " ", repair_text_encoding(unescape(value))).strip()


def normalize_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", repair_text_encoding(unescape(text or ""))).strip()


def clean_display_text(text: str) -> str:
    """Clean short display fields without applying article boilerplate removal."""
    return normalize_whitespace(strip_html(text))


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


def clean_article_display_text(text: str, sentences_per_paragraph: int = 3) -> str:
    """Clean long article bodies while keeping readable paragraph breaks for UI display."""
    plain = strip_html(text)
    raw_parts = re.split(r"\n{2,}|[\r\n]+|(?<=[.!?])\s+", plain)
    kept: list[str] = []
    seen = set()
    for raw in raw_parts:
        line = normalize_whitespace(raw)
        if is_boilerplate_line(line):
            continue
        fingerprint = line.lower()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        kept.append(line)

    paragraphs: list[str] = []
    current: list[str] = []
    for line in kept:
        current.append(line)
        paragraph = " ".join(current)
        if len(current) >= sentences_per_paragraph or len(paragraph) >= 520:
            paragraphs.append(paragraph)
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs)


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
