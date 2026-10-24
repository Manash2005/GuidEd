import re
from typing import Optional

# Common filler patterns to strip from the beginning of user queries
FILLER_PREFIX_PATTERNS = [
    r"^(?:hi|hello|hey|good\s+(?:morning|afternoon|evening))\s*,?\s*",
    r"^(?:please\s+)?(?:can|could)\s+you\s+(?:please\s+)?(?:help|guide|assist)\s+(?:me\s+)?(?:with|to|in|on)?\s*",
    r"^(?:i\s+want\s+a\s+mentor\s+(?:who\s+can\s+help\s+me\s+)?(?:to\s+|in\s+|with\s+)?)\s*",
    r"^(?:i\s+want\s+to|i\s+would\s+like\s+to|i'd\s+like\s+to|i\s+need\s+to|i\s+am\s+trying\s+to|i'm\s+trying\s+to)\s*",
    r"^(?:i\s+am\s+looking\s+for|i'm\s+looking\s+for|looking\s+for|seeking|searching\s+for)\s*",
    r"^(?:i\s+need\s+advice\s+on|i\s+need\s+guidance\s+on|advice\s+on|guidance\s+on)\s*",
    r"^(?:which\s+mentors\s+have|who\s+are\s+the\s+best\s+mentors\s+for|find\s+me\s+a\s+mentor\s+(?:in|for)?)\s*",
    r"^(?:how\s+(?:do|can)\s+i|what\s+is\s+the\s+best\s+way\s+to)\s*",
    r"^(?:tell\s+me\s+about|explain|give\s+me\s+info\s+on)\s*"
]

STOP_WORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with",
    "by", "about", "as", "into", "like", "through", "after", "over", "between"
}

TRAILING_TRIM_WORDS = {
    "and", "or", "with", "in", "to", "for", "the", "a", "an", "of", "about", "who", "can"
}

def clean_title_case(words: list[str]) -> str:
    """Capitalizes words in title format while keeping minor words lowercase."""
    result = []
    for i, w in enumerate(words):
        lw = w.lower()
        if lw in {"ai", "ml", "llm", "llms", "b2b", "b2c", "saas", "pm", "vc", "sql", "aws"}:
            result.append(lw.upper())
        elif i > 0 and lw in STOP_WORDS:
            result.append(lw)
        else:
            result.append(w.capitalize())
    return " ".join(result)

def generate_conversation_title(query: str, max_words: int = 6, max_chars: int = 50) -> str:
    """
    Deterministically generates a concise, meaningful 3-6 word title (<= 50 chars)
    from a student's initial career question.
    """
    if not query or not query.strip():
        return "Career Conversation"

    text = query.strip()

    # Iteratively remove conversational filler prefixes
    cleaned = text
    for pattern in FILLER_PREFIX_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

    if not cleaned:
        cleaned = text

    # Remove trailing punctuation
    cleaned = re.sub(r"[?!.,;:]+$", "", cleaned).strip()

    # Split into first sentence or clause
    first_clause = re.split(r"[.?!;]|(?:\s+-\s+)", cleaned)[0].strip()
    if not first_clause:
        first_clause = cleaned

    words = re.findall(r"\b[\w+#\.\-]+\b", first_clause)
    if not words:
        words = re.findall(r"\b[\w+#\.\-]+\b", text)

    if not words:
        return "Career Mentorship"

    # Select up to max_words
    selected_words = words[:max_words]

    # Trim trailing conjunctions / prepositions so titles don't end in 'and', 'with', 'for'
    while len(selected_words) > 2 and selected_words[-1].lower() in TRAILING_TRIM_WORDS:
        selected_words.pop()

    # If fewer than 2 words, append appropriate contextual noun
    if len(selected_words) == 1:
        w_lower = selected_words[0].lower()
        if "product" in w_lower or "engineer" in w_lower or "design" in w_lower:
            selected_words.append("Career")
        elif "interview" in w_lower or "resume" in w_lower:
            selected_words.append("Prep")
        else:
            selected_words.append("Mentorship")

    formatted = clean_title_case(selected_words)

    # Enforce character limit
    if len(formatted) > max_chars:
        while len(formatted) > max_chars and len(selected_words) > 2:
            selected_words.pop()
            # Trim trailing conjunctions again
            while len(selected_words) > 2 and selected_words[-1].lower() in TRAILING_TRIM_WORDS:
                selected_words.pop()
            formatted = clean_title_case(selected_words)
        if len(formatted) > max_chars:
            formatted = formatted[:max_chars - 3].rstrip() + "..."

    return formatted
