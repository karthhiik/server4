"""Content sanitizer to remove competitor names and placeholder instructions."""

import html as html_mod
import re
from typing import Optional


# Competitor blacklist - names that should never appear in slide content
# Use broader patterns to catch partial mentions
COMPETITOR_BLACKLIST = [
    "slidebean",
    "beautiful",  # Catch "Beautiful.ai", "Beautiful Blog", etc.
    "canva",
    "gamma",
    "tome",
    "pitch.com",
    "deckrobot",
    "slidesai",
    "prezi",
    "powtoon",
]

# Placeholder variable patterns that indicate template/mockup content instead of real data
PLACEHOLDER_PATTERNS = [
    r"\$[XYZ]\b",           # $X, $Y, $Z
    r"\$[XYZ]\.\d+[BMK]?", # $X.5B, $Y.2M
    r"\b[XYZ]%?\b",        # X, Y%, Z standing alone
    r"\bTBD\b",             # To Be Determined
    r"\bcoming soon\b",      # Vague placeholder
    r"\bplaceholder\b",
    r"^\s*~+\s*$",           # orphan placeholder glyphs
    r"^\s*[~<>{}\[\]/\\|&;]+\s*$",
    r"&(?:lt|gt|amp|quot|#39|#x27);?",
    r"<\s*(?:placeholder|insert|todo|tbd)[^>]*>",
    r"\[\s*(?:insert|placeholder|todo|tbd)[^\]]*\]",
    r"\{\s*(?:insert|placeholder|todo|tbd)[^}]*\}",
]

METRIC_YEAR_LABEL_PATTERNS = [
    r"\bmarket\b",
    r"\bsize\b",
    r"\bgrowth\b",
    r"\bcagr\b",
    r"\brate\b",
    r"\btam\b",
    r"\bsam\b",
    r"\bsom\b",
    r"\brevenue\b",
    r"\barr\b",
    r"\bmrr\b",
    r"\bdevices?\b",
    r"\bcustomers?\b",
    r"\busers?\b",
]

# Scraper artifact patterns from raw web crawling
SCRAPER_ARTIFACT_PATTERNS = [
    r"category\s*:\s*news",
    r"category\s*:\s*views",
    r"news and views",
    r"business conclave",
    r"industry leaders came",
    r"at the \w+ \w+ (conclave|summit|forum|conference)",
    r"\[pdf\]", r"\[doc\]", r"\[ppt\]", r"\[xls\]",  # File type markers
    r"constitution, polity", r"polity & governance",
    r"ai's perspective", r"perspective on \w+ \w+",  # Generic AI commentary
    r"^\[",  # Bullets starting with bracketed metadata
    r"published by", r"authored by", r"written by",
    r"^source\s*:", r"^url\s*:", r"^title\s*:",
]

# Instruction placeholder patterns that indicate the AI is outputting instructions instead of actual content
# NOTE: Patterns must be SPECIFIC instruction directives, not general business terms.
INSTRUCTION_PATTERNS = [
    r"^use\s+this\s+slide\b",
    r"^this\s+slide\s+should\b",
    r"^investor\s+numbers\s+must\b",
    r"^market\s+evidence\b",
    r"^demand\s+is\s+framed\b",
    r"^pricing\s+should\b",
    r"^roadmap\s+claims\s+should\b",
    r"^revenue\s+claims\s+stay\b",
    r"^architecture\s+should\b",
    r"^alternatives\s+should\b",
    r"^name\s+icp\b",
    r"^market\s+number\b",
    r"^buyer,\s*deployment\s+volume\b",
    r"^founder\s+bios?\b",
    r"^team\s+identities\b",
    r"^key point about\b",
    r"\b(?:should|must|need|needs|requires|required)\b.{0,80}\b(?:founder|user|input|slide|deck|claim|claims|market evidence|investor numbers|data room|roadmap|pricing|business model|assumptions)\b",
    r"\b(?:claims|numbers|evidence|metrics|assumptions|inputs)\b.{0,40}\b(?:should|must|need|needs|require|required)\b",
    r"\b(?:founder|user)-?provided\b",
    r"\bfounder\s+bios?\s+come\s+from\b",
    r"\bverified\s+team\s+input\b",
    r"\bexported\s+(?:materials|claims)\s+avoid\b",
    r"\bavoid\s+invented\b",
    r"\bno\s+invented\b",
    r"\b(?:current|this)\s+deck\s+should\b",
    r"\buntil\s+(?:the\s+)?(?:user|founder)\s+supplies\b",
]


def _competitor_pattern(competitor: str) -> str:
    """Token-aware competitor pattern that avoids matching inside words."""
    if competitor == "beautiful":
        return r"(?<![a-z0-9])beautiful(?:\.ai|\s+ai|\s+blog)(?![a-z0-9])"
    if "." in competitor:
        return re.escape(competitor)
    return rf"(?<![a-z0-9]){re.escape(competitor)}(?:\.ai)?(?![a-z0-9])"


def normalize_display_text(text: str) -> str:
    """Decode entities and collapse raw generator artifacts in visible copy."""
    if text is None:
        return ""
    cleaned = str(text)
    # Some paths produce entity-like fragments without a semicolon; normalize
    # them before html.unescape so exports never show raw "&lt" text.
    cleaned = (
        cleaned.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&lt", "<")
        .replace("&gt", ">")
    )
    cleaned = html_mod.unescape(cleaned)
    cleaned = cleaned.replace("\u00a0", " ")
    cleaned = re.sub(r"<\s*br\s*/?\s*>", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<\s*/?\s*(?:placeholder|insert|todo|tbd)[^>]*>", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<\s*1\s*ms\b", "less than 1 ms", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\[\s*(?:insert|placeholder|todo|tbd)[^\]]*\]", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\{\s*(?:insert|placeholder|todo|tbd)[^}]*\}", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def contains_placeholder(text: str) -> bool:
    """True if text contains placeholder variables like $X, Y%, Z, TBD."""
    if not text:
        return False
    text_lower = normalize_display_text(text).lower()
    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


def contains_scraper_artifact(text: str) -> bool:
    """True if text contains raw scraper metadata like 'Category: News And Views'."""
    if not text:
        return False
    text_lower = normalize_display_text(text).lower()
    for pattern in SCRAPER_ARTIFACT_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


def sanitize_stat_blocks(stat_blocks: list[dict[str, str]]) -> list[dict[str, str]]:
    """Filter out stat_blocks that contain placeholder variables or scraper artifacts."""
    sanitized = []
    for sb in stat_blocks:
        if not isinstance(sb, dict):
            continue
        value = normalize_display_text(sb.get("value", ""))
        label = normalize_display_text(sb.get("label", ""))
        caption = normalize_display_text(sb.get("caption", ""))
        # Skip if value or label contains placeholder or scraper artifact
        if contains_placeholder(value) or contains_placeholder(label) or contains_placeholder(caption):
            continue
        if contains_scraper_artifact(value) or contains_scraper_artifact(label) or contains_scraper_artifact(caption):
            continue
        # Skip if value is just a single letter placeholder
        if re.match(r"^[XYZ]$", value.strip(), re.IGNORECASE):
            continue
        # Reject bare years being used as business metrics. "2024" can be
        # a date, but it is not a market size, CAGR, revenue, or device count.
        if re.match(r"^(19|20)\d{2}$", value.strip()):
            label_lower = label.lower()
            if any(re.search(pattern, label_lower) for pattern in METRIC_YEAR_LABEL_PATTERNS):
                continue
        cleaned = dict(sb)
        cleaned["value"] = value
        cleaned["label"] = label
        if "caption" in cleaned:
            cleaned["caption"] = caption
        sanitized.append(cleaned)
    return sanitized


def contains_competitor_name(text: str) -> bool:
    """Check if text contains any competitor names."""
    text_lower = text.lower()
    for competitor in COMPETITOR_BLACKLIST:
        if re.search(_competitor_pattern(competitor), text_lower, flags=re.IGNORECASE):
            return True
    return False


def looks_like_instruction(text: str) -> bool:
    """Check if text looks like an instruction placeholder instead of actual content."""
    text_stripped = normalize_display_text(text).strip().lower()
    for pattern in INSTRUCTION_PATTERNS:
        if re.search(pattern, text_stripped, re.IGNORECASE):
            return True
    return False


def _looks_like_webpage_title(text: str) -> bool:
    """Detect raw webpage titles / search result names that leak into bullets."""
    if not text:
        return False
    # Long dash-separated titles: "Space Insurance Basics - Aerospace and Defense"
    if " - " in text and len(text) > 50:
        return True
    # URL fragments
    if re.search(r"https?://", text):
        return True
    # Title-case long strings with common web suffix words
    if len(text) > 60 and re.search(r"\b(News|Blog|Article|Medium|LinkedIn|Forbes|CNN|BBC)\b", text):
        return True
    # Parenthetical site references
    if re.search(r"\([^)]*\.(com|org|net|io)[^)]*\)", text):
        return True
    return False


def sanitize_bullet(bullet: str) -> Optional[str]:
    """
    Sanitize a bullet point.
    Returns None if the bullet should be filtered out (competitor name, instruction,
    scraper artifact, placeholder variable, or raw webpage title).
    """
    bullet = normalize_display_text(bullet)
    if not bullet or not bullet.strip():
        return None

    # Filter out competitor names
    if contains_competitor_name(bullet):
        return None

    # Filter out instruction placeholders
    if looks_like_instruction(bullet):
        return None

    # CRITICAL: Filter out scraper artifacts (raw web metadata)
    if contains_scraper_artifact(bullet):
        return None

    # CRITICAL: Filter out placeholder variables ($X, Y%, Z, TBD)
    if contains_placeholder(bullet):
        return None

    # CRITICAL: Filter out raw webpage titles / search result dumps
    if _looks_like_webpage_title(bullet):
        return None

    # Filter out very short bullets that might be fragments
    if len(bullet.strip().split()) < 3:
        return None

    return bullet.strip()


def sanitize_display_text(text: str) -> Optional[str]:
    """Return clean visible text or None if it is not audience-facing copy."""
    cleaned = normalize_display_text(text)
    if not cleaned:
        return None
    if contains_competitor_name(cleaned):
        return None
    if looks_like_instruction(cleaned):
        return None
    if contains_scraper_artifact(cleaned):
        return None
    if contains_placeholder(cleaned):
        return None
    if _looks_like_webpage_title(cleaned):
        return None
    return cleaned


# Temporarily expose for debugging
def _debug_why_filtered(bullet: str) -> Optional[str]:
    """Return the reason a bullet was filtered, or None if it passes."""
    if not bullet or not bullet.strip():
        return "empty"
    if contains_competitor_name(bullet):
        return f"competitor: {bullet[:60]}"
    if looks_like_instruction(bullet):
        return f"instruction: {bullet[:60]}"
    if contains_scraper_artifact(bullet):
        return f"scraper: {bullet[:60]}"
    if contains_placeholder(bullet):
        return f"placeholder: {bullet[:60]}"
    if _looks_like_webpage_title(bullet):
        return f"webpage_title: {bullet[:60]}"
    if len(bullet.strip().split()) < 3:
        return f"too_short: {bullet[:60]}"
    return None


def sanitize_bullets(bullets: list[str]) -> list[str]:
    """Sanitize a list of bullets, filtering out invalid ones."""
    sanitized = []
    for bullet in bullets:
        cleaned = sanitize_bullet(bullet)
        if cleaned:
            sanitized.append(cleaned)
    return sanitized


def sanitize_text(text: str) -> str:
    """Sanitize text by removing competitor mentions, instruction placeholders,
    scraper artifacts, and placeholder variables."""
    if not text:
        return text

    # Remove instruction placeholder patterns from body text
    text_stripped = normalize_display_text(text)
    sentences = text_stripped.split('. ')
    filtered_sentences = []
    for sentence in sentences:
        if looks_like_instruction(sentence):
            continue
        if contains_scraper_artifact(sentence):
            continue
        if contains_placeholder(sentence):
            continue
        filtered_sentences.append(sentence)

    if filtered_sentences:
        text = '. '.join(filtered_sentences)
    else:
        return ""

    # Remove competitor mentions with word boundaries to prevent mangling words
    for competitor in COMPETITOR_BLACKLIST:
        text = re.sub(_competitor_pattern(competitor), "[competitor]", text, flags=re.IGNORECASE)

    return text


def sanitize_body(body: str) -> str:
    """Sanitize body text by removing instruction placeholders and competitor mentions."""
    if not body:
        return body
    
    # Check if body is just instruction parroting (very short and matches patterns)
    body_stripped = body.strip()
    if looks_like_instruction(body_stripped):
        return ""  # Return empty if it's just instruction parroting
    
    # Otherwise sanitize normally
    return sanitize_text(body)


def sanitize_citation_url(url: str) -> Optional[str]:
    """Sanitize citation URL by filtering out competitor URLs."""
    if not url:
        return None
    
    url_lower = url.lower()
    for competitor in COMPETITOR_BLACKLIST:
        if re.search(_competitor_pattern(competitor), url_lower, flags=re.IGNORECASE):
            return None  # Filter out competitor URLs
    
    return url
