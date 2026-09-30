"""Reviewed source fragments cannot replace, omit or amend official identities."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from db_compile import ability_localization as localization


@pytest.fixture
def sources():
    path = Path(__file__).with_name("fixtures") / "reviewed_guilliman_abilities.json"
    return json.loads(path.read_text(encoding="utf-8"))


def project(sources):
    return localization.project_reviewed_abilities(
        sources["unit_id"], sources["chinese_abilities"], sources["english_abilities"])


def assert_all_official(entries, english):
    assert [entry["canonical_name_en"] for entry in entries] == [
        item["name_en"] for item in english]
    assert all(entry["source"] == "official-db" for entry in entries)
    assert [entry["contentHtml"] for entry in entries] == [
        item["text"] for item in english]


def test_reviewed_grouped_chinese_yields_every_official_identity_once(sources):
    entries = project(sources)
    canonical = [item["name_en"] for item in sources["english_abilities"]]
    assert len(entries) == len(set(canonical)) == 7
    assert [entry["canonical_name_en"] for entry in entries] == canonical
    assert [entry["source"] for entry in entries] == [
        "blacklibrary", "blacklibrary", "blacklibrary", "official-db",
        "blacklibrary", "blacklibrary", "official-db"]
    assert [entry["name"] for entry in entries] == [
        "圣典权威", "极限战士卫队", "命运战甲", "SUPREME COMMANDER",
        "十三军团原体【光环】", "战争之主", "Supreme Strategist"]


def test_grouped_paragraphs_are_split_without_duplicate_or_stale_effect(sources):
    entries = project(sources)
    source_blocks = sources["chinese_abilities"][1]["content"]
    assert entries[0]["content"] == [source_blocks[0]]
    assert "超级战略" not in json.dumps(entries, ensure_ascii=False)
    assert "每个回合一次" not in json.dumps(entries, ensure_ascii=False)
    assert "体形适中" not in json.dumps(entries, ensure_ascii=False)
    for entry, source_index, prefix in [
        (entries[4], 1, "◼ 十三军团原体【光环】："),
        (entries[5], 2, "◼ 战争之主："),
    ]:
        original = source_blocks[source_index]["content"][0]["text"]
        assert entry["content"][0]["content"][0]["text"] == original[len(prefix):]
        assert entry["contentHtml"] == "<p>" + original[len(prefix):] + "</p>"


def test_official_fallback_rules_keep_exact_english_and_keyword_markup(sources):
    entries = project(sources)
    for index in (3, 6):
        official = sources["english_abilities"][index]
        assert entries[index]["name"] == official["name_en"]
        assert entries[index]["contentHtml"] == official["text"]
        assert entries[index]["content"][0]["content"][0]["text"] == official["text"]
    assert "Once per battle round" in entries[6]["contentHtml"]
    assert '<span class="kwb">ADEPTUS</span>' in entries[6]["contentHtml"]


@pytest.mark.parametrize("change", ["body", "html", "name", "id", "extra_field"])
def test_any_original_chinese_source_change_invalidates_whole_review(sources, change):
    item = sources["chinese_abilities"][2]
    if change == "body":
        item["content"][0]["content"][0]["text"] += " New rule."
    elif change == "html":
        item["contentHtml"] += "<p>New rule.</p>"
    elif change == "extra_field":
        item["new_source_field"] = "New information"
    else:
        item[change] = "Changed"
    assert_all_official(project(sources), sources["english_abilities"])


@pytest.mark.parametrize("change", ["body", "name", "order", "add", "remove"])
def test_any_official_identity_or_body_change_preserves_all_current_rules(sources, change):
    official = sources["english_abilities"]
    if change == "body":
        official[6]["text"] = "Once per turn, use the new official effect."
    elif change == "name":
        official[1]["name_en"] = "Renamed Bodyguard"
    elif change == "order":
        official.reverse()
    elif change == "add":
        official.append({"name_en": "New Official Rule", "text": "Current added effect."})
    else:
        official.pop(1)
    assert_all_official(project(sources), official)


def test_official_metadata_does_not_change_name_and_body_review(sources):
    expected = project(sources)
    for item in sources["english_abilities"]:
        item["scope"] = "Review-independent metadata"
        item["id"] = "Database metadata"
    assert project(sources) == expected


def test_database_text_zh_alias_uses_the_same_official_hash(sources):
    expected = project(sources)
    for item in sources["english_abilities"]:
        item["text_zh"] = item.pop("text")
    assert project(sources) == expected


def test_raw_source_inputs_and_nested_fields_are_never_mutated(sources):
    original = copy.deepcopy(sources)
    entries = project(sources)
    assert sources == original
    entries[0]["content"][0]["content"][0]["text"] = "Edited display"
    entries[6]["content"][0]["content"][0]["text"] = "Edited fallback"
    assert sources == original


def test_unreviewed_units_keep_existing_selection_policy(sources):
    assert localization.is_reviewed_unit(sources["unit_id"])
    assert not localization.is_reviewed_unit("000000999")
    assert localization.project_reviewed_abilities("000000999", [], []) is None


def test_missing_chinese_source_returns_every_current_official_rule(sources):
    sources["chinese_abilities"] = []
    assert_all_official(project(sources), sources["english_abilities"])


def test_broken_reviewed_selection_falls_back_instead_of_omitting_rules(
        sources, tmp_path, monkeypatch):
    policy = json.loads(localization.POLICY.read_text(encoding="utf-8"))
    policy["records"][0]["chinese_selections"][0]["content_block_paths"] = [
        [1, "content", 99]]
    path = tmp_path / "review.json"
    path.write_bytes(json.dumps(policy, ensure_ascii=False).encode("utf-8"))
    monkeypatch.setattr(localization, "POLICY", path)
    assert_all_official(project(sources), sources["english_abilities"])
