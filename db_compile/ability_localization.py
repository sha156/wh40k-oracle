"""Project explicitly reviewed Chinese fragments onto official ability identities.

The review is tied to both complete source payloads. It cannot follow a renamed,
added or amended ability by guessing. A changed reviewed source instead produces
every current official ability in English; unreviewed units return ``None`` so
their existing selection policy remains in control.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


POLICY = Path(__file__).with_name("ability_localization.json")
_PARAGRAPH = re.compile(r"<p(?:\s[^>]*)?>.*?</p>", re.DOTALL | re.IGNORECASE)


def _digest(value: Any) -> str:
    """Canonical JSON hash; preserve all Chinese fields and ordered list items."""
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalise_english(abilities: List[dict]) -> List[Dict[str, str]]:
    """Discard database metadata, retaining the official names and bodies exactly."""
    return [{"name_en": str(item.get("name_en") or item.get("name") or ""),
             "text": str(item.get("text") or item.get("text_zh") or "")}
            for item in abilities]


def _official_entry(ability: Dict[str, str]) -> dict:
    body = ability["text"]
    return {
        "name": ability["name_en"],
        "content": [{"type": "text", "content": [{"style": "", "text": body}]}],
        # Preserve official HTML verbatim, including its keyword spans.
        "contentHtml": body,
        "source": "official-db",
        "canonical_name_en": ability["name_en"],
    }


def _at_path(value: Any, path: List[Any]) -> Any:
    for key in path:
        value = value[key]
    return value


def _chinese_entry(chinese: List[dict], selection: dict) -> dict:
    """Copy exact reviewed blocks and remove only their reviewed heading prefix."""
    blocks = [copy.deepcopy(_at_path(chinese, path))
              for path in selection["content_block_paths"]]
    original_html = _at_path(chinese, selection["html_path"])
    paragraphs = _PARAGRAPH.findall(original_html)
    chosen_html = "".join(paragraphs[index]
                          for index in selection["html_paragraph_indices"])
    prefix = selection.get("strip_heading_prefix")
    if prefix:
        spans = blocks[0]["content"]
        text = spans[0]["text"]
        if not text.startswith(prefix):
            raise ValueError("Reviewed Chinese heading prefix no longer matches")
        spans[0]["text"] = text[len(prefix):]
        # The exact paragraph was fingerprinted. Refuse to remove a similarly
        # named heading, or a later occurrence inside the rule body.
        html_heading = re.match(r"(<p(?:\s[^>]*)?>)" + re.escape(prefix),
                                chosen_html, re.IGNORECASE)
        if not html_heading:
            raise ValueError("Reviewed Chinese HTML heading no longer matches")
        chosen_html = (html_heading.group(1) +
                       chosen_html[html_heading.end():])
    name = (selection["display_name"] if "display_name" in selection else
            _at_path(chinese, selection["name_path"]))
    return {
        "name": name,
        "content": blocks,
        "contentHtml": chosen_html,
        "source": "blacklibrary",
        "canonical_name_en": selection["canonical_name_en"],
    }


def _review_for(unit_id: str) -> Optional[dict]:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    if policy.get("schema_version") != 1:
        raise ValueError("Unsupported reviewed ability policy schema")
    return next((record for record in policy["records"]
                 if record["unit_id"] == str(unit_id)), None)


def is_reviewed_unit(unit_id: str) -> bool:
    """Allow consumers to query official abilities only for reviewed units."""
    return _review_for(unit_id) is not None


def project_reviewed_abilities(
    unit_id: str,
    chinese_abilities: List[dict],
    english_abilities: List[dict],
) -> Optional[List[dict]]:
    """Return complete reviewed display entries, or ``None`` for unreviewed IDs.

    English input accepts ``name_en``/``name`` and ``text``/``text_zh`` fields.
    Its order must be the official database's ``ORDER BY rowid`` order. Neither
    input is mutated. Reviewed units always retain every official identity and
    its order, including when a source change invalidates Chinese selections.
    """
    review = _review_for(unit_id)
    if review is None:
        return None
    official = _normalise_english(english_abilities)
    fallback = [_official_entry(ability) for ability in official]
    if (_digest(chinese_abilities) != review["chinese_abilities_sha256"] or
            _digest(official) != review["english_abilities_sha256"]):
        return fallback
    selections = {item["canonical_name_en"]: item
                  for item in review["chinese_selections"]}
    try:
        return [(_chinese_entry(chinese_abilities, selections[ability["name_en"]])
                 if ability["name_en"] in selections else _official_entry(ability))
                for ability in official]
    except (KeyError, IndexError, TypeError, ValueError):
        # A broken selection is not permission to hide an official rule.
        return fallback
