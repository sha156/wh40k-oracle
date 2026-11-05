"""Reviewed same-name source families cannot fan out across canonical factions."""
from copy import deepcopy

import pytest

from db_compile.blacklibrary_identity import quarantined_detail, scoped_detail_ids


FAMILIES = [
    (577, "MINISTORUM PRIEST", "修女会", "000001553", "AS", False),
    (992, "Ministorum Priest", "帝国特勤", "000003812", "AoI", True),
    (122, "WATCH CAPTAIN ARTEMIS", "死亡守望", "000003872", "SM", False),
    (1001, "Watch Captain Artemis", "帝国特勤", "000003814", "AoI", True),
    (121, "WATCH MASTER", "死亡守望", "000003871", "SM", False),
    (1002, "Watch Master", "帝国特勤", "000003815", "AoI", True),
    (238, "LORD OF CHANGE", "混沌恶魔", "000001120", "CD", False),
    (1094, "LORD OF CHANGE", "闪耀军团", "000004124", "TS", True),
]
FACTIONS = {cid: faction for _, _, _, cid, faction, _ in FAMILIES}
FACTIONS["000001394"] = "AM"


def record(source_id, name, faction, verified=False):
    result = {"id": source_id, "name_en": name, "faction_zh": faction,
              "detail": {"能力": [{"name": "Captured ability"}]}}
    if verified:
        result["provenance"] = {"status": "verified_capture"}
    return result


@pytest.mark.parametrize("source_id,name,faction,cid,canonical_faction,suspect", FAMILIES)
def test_reviewed_source_targets_only_its_exact_canonical_row(
        source_id, name, faction, cid, canonical_faction, suspect):
    captured = record(source_id, name, faction, verified=True)
    candidates = list(FACTIONS)
    assert scoped_detail_ids(captured, candidates, FACTIONS) == [cid]
    assert scoped_detail_ids(captured, candidates[::-1], FACTIONS) == [cid]
    assert not quarantined_detail(captured)
    assert scoped_detail_ids(captured, [other for other in candidates if other != cid], FACTIONS) == []


@pytest.mark.parametrize("source_id,name,faction,cid,canonical_faction,suspect", FAMILIES)
def test_legacy_cache_is_accepted_only_for_the_four_verified_original_sources(
        source_id, name, faction, cid, canonical_faction, suspect):
    captured = record(source_id, name, faction)
    expected = [] if suspect else [cid]
    assert scoped_detail_ids(captured, list(FACTIONS), FACTIONS) == expected
    assert quarantined_detail(captured) is suspect
    captured["provenance"] = {"status": "retained_previous_cache", "reason": "failed"}
    assert scoped_detail_ids(captured, list(FACTIONS), FACTIONS) == expected


@pytest.mark.parametrize("field,value", [
    ("id", 9999), ("faction_zh", "不同阵营"), ("name_en", "Another Priest"),
    ("faction_zh", None), ("name_en", None), ("id", True),
])
def test_source_signature_drift_is_quarantined(field, value):
    captured = record(577, "MINISTORUM PRIEST", "修女会", verified=True)
    captured[field] = value
    assert quarantined_detail(captured)
    assert scoped_detail_ids(captured, list(FACTIONS), FACTIONS) == []


def test_canonical_faction_drift_is_not_guessed():
    captured = record(577, "MINISTORUM PRIEST", "修女会", verified=True)
    changed = dict(FACTIONS, **{"000001553": "AoI"})
    assert scoped_detail_ids(captured, list(FACTIONS), changed) == []
    assert scoped_detail_ids(captured, list(FACTIONS), {}) == []


def test_normalized_english_spelling_keeps_verified_family_identity():
    captured = record("122", "Watch-Captain Artemis", "死亡守望", verified=True)
    assert scoped_detail_ids(captured, list(FACTIONS), FACTIONS) == ["000003872"]


def test_unrelated_shared_unit_preserves_all_candidate_factions_without_mutation():
    captured = record(50, "Skitarii Rangers", "机械修会")
    candidates = ["rangers_adm", "rangers_qi"]
    factions = {"rangers_adm": "AdM", "rangers_qi": "QI"}
    before = deepcopy(captured)
    assert scoped_detail_ids(captured, candidates, factions) == candidates
    assert not quarantined_detail(captured)
    assert captured == before


def test_suspect_source_does_not_inherit_verification_from_previous_provenance():
    captured = record(992, "Ministorum Priest", "帝国特勤")
    captured["provenance"] = {"status": "retained_previous_cache",
                              "previous": {"status": "verified_capture"}}
    assert scoped_detail_ids(captured, list(FACTIONS), FACTIONS) == []
