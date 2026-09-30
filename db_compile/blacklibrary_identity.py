"""Scope the four reviewed same-name families to their verified source identities.

The source's detail endpoint can return a different faction's same-name unit.
Four retained cache records have this confirmed failure, so their old bodies are
unusable until a new capture passes the endpoint identity checks. This policy
does not infer faction equivalence for other shared datasheets.
"""
from __future__ import annotations

import re
from typing import Iterable, Mapping


# source ID: (normalized English family, source faction, canonical ID, faction,
#             requires a newly verified capture)
_REVIEWED = {
    "577": ("ministorumpriest", "修女会", "000001553", "AS", False),
    "992": ("ministorumpriest", "帝国特勤", "000003812", "AoI", True),
    "122": ("watchcaptainartemis", "死亡守望", "000003872", "SM", False),
    "1001": ("watchcaptainartemis", "帝国特勤", "000003814", "AoI", True),
    "121": ("watchmaster", "死亡守望", "000003871", "SM", False),
    "1002": ("watchmaster", "帝国特勤", "000003815", "AoI", True),
    "238": ("lordofchange", "混沌恶魔", "000001120", "CD", False),
    "1094": ("lordofchange", "闪耀军团", "000004124", "TS", True),
}
_FAMILIES = frozenset(signature[0] for signature in _REVIEWED.values())


def _family(record: Mapping) -> str:
    name = record.get("name_en")
    return re.sub(r"[^a-z0-9]", "", name.lower()) if isinstance(name, str) else ""


def _signature(record: Mapping):
    source_id = record.get("id")
    # bool is an int in Python, but is not a valid source identity.
    key = str(source_id) if isinstance(source_id, (str, int)) and not isinstance(source_id, bool) else ""
    return key, _family(record), _REVIEWED.get(key)


def quarantined_detail(record: Mapping) -> bool:
    """Reject drifted reviewed identities and unverified known wrong responses.

    Unknown signatures in these four families need review. Legacy originals are
    accepted without provenance; the four confirmed wrong retained bodies are
    accepted only after top-level ``verified_capture`` provenance replaces them.
    """
    _, family, signature = _signature(record)
    if signature is None:
        return family in _FAMILIES
    expected_family, expected_faction, _, _, needs_verification = signature
    if family != expected_family or record.get("faction_zh") != expected_faction:
        return True
    provenance = record.get("provenance")
    verified = isinstance(provenance, dict) and provenance.get("status") == "verified_capture"
    return needs_verification and not verified


def scoped_detail_ids(record: Mapping, candidate_ids: Iterable[str],
                      factions_by_id: Mapping[str, str]) -> list[str]:
    """Return allowed canonical candidates without mutating inputs or guessing.

    Candidates for unrelated English families retain existing multi-faction
    behavior. A reviewed identity needs both its exact canonical ID and faction;
    a changed canonical build therefore fails closed rather than reassigning it.
    """
    candidates = list(candidate_ids)
    if quarantined_detail(record):
        return []
    _, _, signature = _signature(record)
    if signature is None:
        return candidates
    _, _, canonical_id, canonical_faction, _ = signature
    if canonical_id in candidates and factions_by_id.get(canonical_id) == canonical_faction:
        return [canonical_id]
    return []
