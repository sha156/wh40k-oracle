"""Official keyword extraction must survive retirement without invented identities."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from wiki_engine import keyword_index as ki
from wiki_engine.core_rules_zh import EN_PDF, ZH_PDF
from wiki_engine.pdf_sections import PdfSection

REPO = Path(__file__).resolve().parents[1]
needs_sources = pytest.mark.skipif(
    not (REPO / EN_PDF).exists() or not (REPO / ZH_PDF).exists(),
    reason="Retained official English/Chinese Core Rules PDFs are absent")


def section(num, title, body="Official rule text", asides=()):
    return PdfSection(num, title, body, 1, asides)


@needs_sources
def test_official_source_has_complete_named_abilities():
    entries = ki.parse_quickref(REPO / EN_PDF)
    assert len(entries) == 35
    for name, num, zh in [
        ("ANTI", "24.03", "针对"),
        ("CLEAVE", "24.06", "劈砍"),
        ("CLOSE-QUARTERS", "24.07", "近距离"),
        ("LEADER", "24.22", "领袖"),
        ("PISTOL", "24.27", "手枪"),
        ("SUPPORT", "24.34", "辅助"),
        ("SUSTAINED HITS", "24.36", "连击"),
        ("TWIN-LINKED", "24.38", "双联"),
    ]:
        assert entries[name].section == num
        assert entries[name].name_zh == zh
    assert not {"ABILITIES", "DUPLICATED ABILITIES", "SCOUT MOVE"} & set(entries)


@pytest.mark.parametrize("path", [
    "data/11版40K通用技能速查表.pdf",
    "restored/data_refined/11版40K通用技能速查表/copied.pdf",
    "data/沃坦联盟CODEX-双子星版 V1.30.pdf",
])
def test_keyword_parser_rejects_retired_explicit_inputs(path):
    with pytest.raises(ValueError, match="Source retired"):
        ki.parse_quickref(Path(path))


def test_official_headings_determine_identities_not_a_whitelist():
    en = {
        "24.03": section("24.03", "[ANTI]"),
        "24.06": section("24.06", "[UNFAMILIAR\u2011ABILITY]"),
        "24.34": section("24.34", "LEADER 24.22 / SUPPORT"),
    }
    zh = {
        "24.03": section("24.03", "[针对]"),
        "24.06": section("24.06", "[官方新技能]"),
        "24.34": section("24.34", "40000 应用程序”中查看详情。 领袖 24.22/辅助"),
    }
    entries = ki._entries_from_sections(en, zh)
    assert set(entries) == {"ANTI", "UNFAMILIAR-ABILITY", "SUPPORT"}
    assert entries["UNFAMILIAR-ABILITY"].name_zh == "官方新技能"
    assert entries["SUPPORT"].name_zh == "辅助"
    assert ki.classify("UNFAMILIAR-ABILITY", entries) == "universal"
    assert ki.classify("CLEAVE", entries) == "unit-specific"


def test_section_pairing_and_duplicate_identity_fail_closed():
    en = {"24.05": section("24.05", "[BLAST]")}
    with pytest.raises(ValueError, match="section numbers"):
        ki._entries_from_sections(en, {})
    zh = {"24.05": section("24.05", "[爆炸]")}
    en["24.06"] = section("24.06", "[BLAST]")
    zh["24.06"] = section("24.06", "[重复名字]")
    with pytest.raises(ValueError, match="Duplicate official ability"):
        ki._entries_from_sections(en, zh)


def test_empty_rule_body_is_not_accepted_as_official_coverage():
    en = {"24.05": section("24.05", "[BLAST]", "")}
    zh = {"24.05": section("24.05", "[爆炸]")}
    with pytest.raises(ValueError, match="Empty official ability"):
        ki._entries_from_sections(en, zh)


@pytest.mark.parametrize("equivalence,replacement,expected", [
    (True, True, "transitional"),
    (True, False, "universal"),
    (False, True, "universal"),
])
def test_pistol_transition_requires_actual_official_text(equivalence, replacement, expected):
    body = "[PISTOL] and [CLOSE\u2011QUARTERS] are identical for all rules purposes." if equivalence else "Ordinary rule."
    aside = "Designer’s Note: [PISTOL] is a pre-existing ability that will be superseded by [CLOSE-QUARTERS] as this edition progresses." if replacement else ""
    en = {"24.27": section("24.27", "[PISTOL]", body, (aside,))}
    zh = {"24.27": section("24.27", "[手枪]")}
    entries = ki._entries_from_sections(en, zh)
    assert ki.classify("PISTOL", entries) == expected
    assert ki.classify("PISTOL", {}) == "unit-specific"


@needs_sources
@pytest.mark.parametrize("token,num", [
    ("ANTI-INFANTRY 4+", "24.03"),
    ("CLEAVE 2", "24.06"),
    ("RAPID FIRE D6+3", "24.30"),
    ("LETHAL HITS: VEHICLE", "24.23"),
    ("SUSTAINED HITS 1: INFANTRY/BEASTS", "24.36"),
])
def test_official_parameterized_and_conditional_families(token, num):
    entries = ki.parse_quickref(REPO / EN_PDF)
    assert entries[ki.keyword_family(token)].section == num
    assert ki.classify(token, entries) == "universal"


def test_retired_chinese_companion_is_rejected_before_pdf_read():
    with pytest.raises(ValueError, match="Source retired"):
        ki.parse_quickref(Path("missing-official.pdf"),
                          zh_pdf_path=Path("data/11版40K通用技能速查表.pdf"))


def test_both_languages_missing_same_section_still_fails(tmp_path, monkeypatch):
    """Matching subsets do not prove complete official coverage."""
    from wiki_engine import pdf_sections

    en_pdf, zh_pdf = tmp_path / "english.pdf", tmp_path / "chinese.pdf"
    en_pdf.touch()
    zh_pdf.touch()
    monkeypatch.setattr(pdf_sections, "split_sections", lambda *args: {
        "24.05": section("24.05", "[BLAST]")})
    with pytest.raises(ValueError, match="chapter 24 incomplete"):
        ki.parse_quickref(en_pdf, zh_pdf)


@needs_sources
def test_changed_pdf_is_reparsed_not_served_from_path_cache(monkeypatch):
    from wiki_engine import pdf_sections

    # Warm any existing shared path cache, then simulate new PDF content.
    ki.parse_quickref(REPO / EN_PDF)
    monkeypatch.setattr(pdf_sections, "split_sections", lambda *args: {})
    with pytest.raises(ValueError, match="chapter 24 incomplete"):
        ki.parse_quickref(REPO / EN_PDF)


@needs_sources
@pytest.mark.skipif(not (REPO / "db/wh40k.sqlite").exists()
                    or not (REPO / "wiki/core-rules").exists(),
                    reason="Actual database/wiki assets are absent")
def test_official_generated_payload_preserves_api_and_glossary(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from web_api import keywords
    from web_api.main import app

    report = ki.generate(REPO / "db/wh40k.sqlite", REPO / "wiki", REPO / EN_PDF,
                         out_root=tmp_path)
    payload_path = tmp_path / ki.PAYLOAD_REL
    items = {i["base"]: i for i in json.loads(payload_path.read_text(encoding="utf-8"))["items"]}
    assert report["core_rules_entries"] == report["quickref_entries"] == 35
    assert report["groups"] == {"universal": 36, "transitional": 1, "unit-specific": 13}
    stats, _ = ki.collect(REPO / "db/wh40k.sqlite")
    glossary = ki.load_glossary(REPO / "db/wh40k.sqlite")
    assert set(items) == set(stats)
    for base, st in stats.items():
        assert items[base]["nameZh"] == ki._zh_base(base, st.variants, glossary)
        assert items[base]["quickrefZh"] is None  # No retired secondary aliases.
    assert items["SUSTAINED HITS"]["section"] == "24.36"
    text = (tmp_path / ki.INDEX_REL).read_text(encoding="utf-8")
    assert "GW 官方核心规则第 24 章" in text
    assert "汉化组速查表" not in text

    monkeypatch.setattr(keywords, "PAYLOAD_PATH", payload_path)
    with TestClient(app) as client:
        response = client.get("/codex/keywords/pistol")
        assert response.status_code == 200
        pistol = response.json()
        assert pistol["section"] == pistol["ruleSection"] == "24.27"
        assert pistol["ruleSlug"] == "24-core-abilities"
        assert pistol["group"] == "transitional"
        assert pistol["quickrefZh"] is None
