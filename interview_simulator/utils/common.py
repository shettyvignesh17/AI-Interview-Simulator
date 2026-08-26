import json
import re
from collections import Counter
from datetime import datetime, timezone


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "this",
    "to",
    "we",
    "with",
    "you",
    "your",
}


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def safe_json_loads(raw_value, default):
    if raw_value in (None, ""):
        return default

    try:
        return json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return default


def safe_json_dumps(value):
    return json.dumps(value, ensure_ascii=True)


def clamp(value, minimum=0.0, maximum=100.0):
    return max(minimum, min(maximum, value))


def tokenize(text):
    return re.findall(r"[A-Za-z0-9#+.-]+", (text or "").lower())


def unique_list(items):
    seen = set()
    ordered = []
    for item in items:
        normalized = item.strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(normalized)
    return ordered


def extract_significant_terms(text, limit=6):
    tokens = [
        token
        for token in tokenize(text)
        if len(token) > 2 and token not in STOP_WORDS and not token.isdigit()
    ]
    most_common = Counter(tokens).most_common(limit)
    return [item[0] for item in most_common]
