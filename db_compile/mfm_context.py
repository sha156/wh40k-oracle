"""Exact canonical chapter identity for price routing, without name inference."""
from __future__ import annotations

import json
from typing import Optional

CHAPTER_SLUGS = {
    "black templars": "black-templars", "blood angels": "blood-angels",
    "dark angels": "dark-angels", "deathwatch": "deathwatch",
    "space wolves": "space-wolves",
}
_GENERIC_CHAPTERS = {
    "ultramarines", "imperial fists", "iron hands", "raven guard",
    "salamanders", "white scars", "blood ravens",
}


def canonical_price_slug(faction_id: str, keywords_json: Optional[str]) -> Optional[str]:
    """Return a recognized SM route, or None for uncertain/mixed identity.

    Missing metadata is unresolved. An explicit array must identify
    Adeptus Astartes and at most one chapter.
    Order is inspected as supplied; it is never rewritten in canonical data.
    """
    if faction_id != "SM":
        return None
    if keywords_json is None:
        return None
    try:
        data = json.loads(keywords_json)
        keywords = data.get("faction_keywords")
    except (ValueError, TypeError, AttributeError):
        return None
    if not isinstance(keywords, list) or not keywords or not all(
            isinstance(value, str) for value in keywords):
        return None
    identities = [value.casefold() for value in keywords]
    if "adeptus astartes" not in identities or len(identities) != len(set(identities)):
        return None
    chapters = [value for value in identities if value != "adeptus astartes"]
    if not chapters:
        return "space-marines"
    if len(chapters) != 1:
        return None
    chapter = chapters[0]
    return CHAPTER_SLUGS.get(chapter) or (
        "space-marines" if chapter in _GENERIC_CHAPTERS else None)
