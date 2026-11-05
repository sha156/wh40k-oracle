"""Scope reviewed same-name families and rebuild bridges to source identities.

The source's detail endpoint can return a different faction's same-name unit.
Four retained cache records have this confirmed failure, so their old bodies are
unusable until a new capture passes the endpoint identity checks. This policy
does not infer faction equivalence for other shared datasheets.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Iterable, Mapping, Optional


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

# Frozen, independently verified raw/cached lineage. These exceptions authorize
# community Chinese text only; they never import source stats into official cells.
_BINDINGS = {
    row["source_id"]: row for row in json.loads(
        Path(__file__).with_name("blacklibrary_identity_bindings.json").read_text("utf-8")
    )["bindings"]
}
_BOUND_IDS = frozenset(row["canonical_id"] for row in _BINDINGS.values()) | {"000000847"}
_BOUND_FAMILIES = frozenset(
    re.sub(r"[^a-z0-9]", "", row[field].lower())
    for row in _BINDINGS.values()
    for field in ("source_name_en", "canonical_name_en")
)


def _bound_signature(record: Mapping):
    key, family, _ = _signature(record)
    return _BINDINGS.get(key), key in _BINDINGS or family in _BOUND_FAMILIES


def _verified_binding(record: Mapping, binding: Mapping) -> bool:
    if (record.get("name_en") != binding["source_name_en"]
            or record.get("faction_zh") != binding["source_faction_zh"]
            or record.get("provenance") != binding["provenance"]):
        return False
    encoded = json.dumps(record, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest() == binding["record_sha256"]


def source_bound_detail_ids(conn: sqlite3.Connection, record: Mapping) -> Optional[list[str]]:
    """Resolve a reviewed spelling bridge without list names or old Chinese names.

    None delegates unrelated records to the existing matcher. An empty list is
    a final denial, so neither Chinese-name fallback nor an English lookalike can
    evade drift checks. The full cached fingerprint pins the verified raw fields
    and capture provenance to the audited manifest; new captures need review.
    """
    binding, governed = _bound_signature(record)
    if not governed:
        return None
    if binding is None or not _verified_binding(record, binding):
        return []
    columns = {r[1] for r in conn.execute("PRAGMA table_info(units)")}
    if not {"id", "name_en", "faction_id", "keywords_json"} <= columns:
        return []
    cid = binding["canonical_id"]
    row = conn.execute("SELECT name_en, faction_id, keywords_json FROM units WHERE id = ?",
                       (cid,)).fetchone()
    if not row or row[:2] != (binding["canonical_name_en"], binding["canonical_faction_id"]):
        return []
    try:
        keywords = json.loads(row[2])
    except (TypeError, ValueError):
        return []
    if keywords != binding["canonical_keywords"]:
        return []
    return [cid]


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
    binding, governed = _bound_signature(record)
    if governed:
        return binding is None or not _verified_binding(record, binding)
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
    # Source-bound targets (including the explicitly denied AdM Servitors reuse)
    # are available only through source_bound_detail_ids with canonical guards.
    candidates = [cid for cid in candidate_ids if cid not in _BOUND_IDS]
    if quarantined_detail(record):
        return []
    _, _, signature = _signature(record)
    if signature is None:
        return candidates
    _, _, canonical_id, canonical_faction, _ = signature
    if canonical_id in candidates and factions_by_id.get(canonical_id) == canonical_faction:
        return [canonical_id]
    return []
