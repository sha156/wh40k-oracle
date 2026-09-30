"""Synthetic exact ledger identities never inherit a fuzzy sibling's body/price."""
import hashlib
import inspect
import json
import sqlite3
from contextlib import closing

import pytest

from agent import tools
from db_compile.build import build_database
from db_compile.entity_resolver import EntityResolver
from db_compile.mfm_source import write_ledger
from db_compile.source_archive import project_deleted_details
from web_api import official_points
from web_api.formatter import _evidence_digest
from web_api.trace import TraceRecorder


CAPTURED = "2026-09-30T12:00:00Z"
ARMOUR = "Marneus Calgar in Armour of Antilochus"


@pytest.fixture
def price_db(tmp_path):
    source = tmp_path / "csv"
    source.mkdir()
    (source / "Factions.csv").write_text(
        "id|name|link|\nSM|Space Marines|https://example.invalid|\n"
        "AC|Adeptus Custodes|https://example.invalid|\n", encoding="utf-8")
    (source / "Datasheets.csv").write_text(
        "id|name|faction_id|source_id|legend|role|loadout|transport|virtual|"
        "leader_head|leader_footer|damaged_w|damaged_description|link|\n"
        "100|" + ARMOUR + "|SM|1||||||||||https://example.invalid|\n"
        "101|Kaius Alpha|SM|1||||||||||https://example.invalid|\n"
        "102|Current Squad|SM|1||||||||||https://example.invalid|\n"
        "103|Shared Hero|SM|1||||||||||https://example.invalid|\n",
        encoding="utf-8")
    db = tmp_path / "synthetic.sqlite"
    build_database(source, db)
    with closing(sqlite3.connect(db)) as conn, conn:
        for uid, cost, current in (("100", 155, False), ("101", 999, True),
                                   ("102", 90, True), ("103", 120, True)):
            items = [{"desc": "5 models" if uid == "102" else "1 model", "cost": cost}]
            if uid == "102":
                items.append({"desc": "10 models", "cost": 170})
            conn.execute("UPDATE units SET points_json=? WHERE id=?", (
                json.dumps({"points": cost, "items": items,
                            "mfm": {"current": current,
                                    "fetched_at": CAPTURED if current else "2026-09-14T12:00:00Z",
                                    "source_url": "https://example.invalid/space-marines"}}), uid))
        write_ledger(conn, snapshot())
    project_deleted_details(db, details=[{
        "id": 6, "name_en": "Marneus Calgar", "name_zh": "马涅乌斯.卡尔加（已删除）",
        "faction_zh": "极限战士", "score": 200,
        "composition": "Marneus Calgar and two Victrix Honour Guard",
    }])
    return db


def snapshot():
    def row(name, cost, models="1 model", tier="YOUR UNIT COSTS", kind="unit"):
        return {"kind": kind, "section": "UNITS", "unit": name,
                "tier": tier, "models": models, "cost": cost}

    pages = {
        "space-marines": [
            row("Marneus Calgar", 180), row("Marneus Calgar", 300, "2 models"),
            row("Kaius", 100), row("Kaius", 150, tier="YOUR 2ND UNIT COSTS"),
            row("Kaius", 10, "+ 1 Weapon", "YOUR WARGEAR COSTS"),
            row("Kaius (Prototype)", 110),
            row("Current Squad", 90, "5 models"), row("Current Squad", 170, "10 models"),
            row("Shared Hero", 120), row("Chapter Hero", 80),
            row("Enhancement Only", 20, kind="enhancement"),
        ],
        "adeptus-custodes": [row("Shared Hero", 120)],
        "blood-angels": [row("Chapter Hero", 80)],
        "dark-angels": [row("Chapter Hero", 80)],
    }
    return {"fetched_at": CAPTURED, "pages": {
        slug: {"url": "https://example.invalid/" + slug,
               "sha256": hashlib.sha256(slug.encode()).hexdigest(), "rows": rows}
        for slug, rows in pages.items()}}


def calculate(db, query, *, inject_resolver=True):
    kwargs = {"resolver": EntityResolver(db_path=db)} if inject_resolver else {}
    return tools.calc_points([query], db_path=db, **kwargs)["units"][0]


@pytest.mark.parametrize("query", ["Kaius", " kaius ", "Kaius (space-marines)",
                                   "Kaius（space-marines）"])
def test_exact_price_precedes_real_fuzzy_sibling(price_db, query):
    # No mocked resolver: the unqualified source name really resolves to a sibling.
    hit = EntityResolver(db_path=price_db).resolve("Kaius")
    assert hit.confidence == "fuzzy" and hit.canonical_id == "101"
    result = calculate(price_db, query)
    assert result["name_en"] == "Kaius" and result["points"] == 100
    assert result["unit_id"] is None and result["points_only"] is True
    assert not result.get("resolved_via")
    assert "datasheet" not in result and "models" not in result and "weapons" not in result
    assert [r["cost"] for r in result["official_prices"]] == [100, 150, 10]


@pytest.mark.parametrize("query", ["Shared Hero", "Chapter Hero"])
def test_equal_minima_never_resolve_cross_faction_identity(price_db, query):
    result = official_points.exact_unit(price_db, query)
    assert result["points"] is None
    assert result["ambiguous"] is True and result["faction_slug"] is None
    assert len(result["candidates"]) == (2 if query == "Shared Hero" else 3)
    assert {c["points"] for c in result["candidates"]} == ({120} if query == "Shared Hero" else {80})
    for candidate in result["candidates"]:
        exact = official_points.exact_unit(price_db, candidate["query"])
        assert exact["faction_slug"] == candidate["faction_slug"]
        assert exact["points"] == candidate["points"]
        assert not exact["ambiguous"]


def test_ledger_ambiguity_precedes_single_canonical_exact_match(price_db):
    assert EntityResolver(db_path=price_db).resolve("Shared Hero").canonical_id == "103"
    result = calculate(price_db, "Shared Hero")
    assert result["points"] is None and result["unit_id"] is None
    assert result["ambiguous"] and len(result["candidates"]) == 2


def test_exact_source_name_beats_alias_to_a_different_full_variant(price_db, tmp_path):
    aliases = tmp_path / "aliases.py"
    aliases.write_text('UNIT_ALIASES = {"Kaius": "Kaius Alpha"}\n', encoding="utf-8")
    resolver = EntityResolver(db_path=price_db, app_path=aliases)
    assert resolver.resolve("Kaius").confidence == "exact"
    result = tools.calc_points(["Kaius"], db_path=price_db, resolver=resolver)["units"][0]
    assert result["unit_id"] is None and result["points"] == 100
    assert result["name_en"] == "Kaius" and result["points_only"]


def test_single_ledger_faction_cannot_inherit_same_name_from_other_canonical_faction(price_db):
    with closing(sqlite3.connect(price_db)) as conn, conn:
        conn.execute("DELETE FROM official_mfm_points WHERE faction_slug='space-marines' AND unit_name='Shared Hero'")
    result = calculate(price_db, "Shared Hero")
    assert result["unit_id"] is None and result["points_only"]
    assert result["faction_slug"] == "adeptus-custodes" and result["points"] == 120


@pytest.mark.parametrize("chapter,matches", [("BLOOD ANGELS", True), ("ULTRAMARINES", False)])
def test_same_sm_faction_does_not_erase_exact_source_chapter(price_db, chapter, matches):
    with closing(sqlite3.connect(price_db)) as conn, conn:
        conn.execute("UPDATE units SET name_en='Chapter Hero',keywords_json=? WHERE id='103'", (
            json.dumps({"faction_keywords": ["ADEPTUS ASTARTES", chapter]}),))
        if matches:
            conn.execute("UPDATE units SET points_json=? WHERE id='103'", (
                json.dumps({"items": [{"desc": "1 model", "cost": 80}], "mfm": {"current": True}}),))
        conn.execute("UPDATE datasheets SET name='Chapter Hero' WHERE id='103'")
        conn.execute("DELETE FROM official_mfm_points WHERE unit_name='Chapter Hero' AND faction_slug!='blood-angels'")
    result = calculate(price_db, "Chapter Hero")
    assert result["unit_id"] == ("103" if matches else None)
    assert result["points"] == 80
    assert bool(result.get("points_only")) is not matches


@pytest.mark.parametrize("slug,cost", [("space-marines", 120), ("adeptus-custodes", 120),
                                      ("blood-angels", 80), ("dark-angels", 80)])
def test_exact_slug_qualification_is_lossless(price_db, slug, cost):
    name = "Shared Hero" if cost == 120 else "Chapter Hero"
    result = official_points.exact_unit(price_db, name, faction_slug=slug)
    assert result["points"] == cost and result["faction_slug"] == slug
    assert {r["faction_slug"] for r in result["official_prices"]} == {slug}
    assert not result["ambiguous"]


@pytest.mark.parametrize("query", ["Kaius (Prototype)", "Kaius (Prototype) (space-marines)"])
def test_parenthesized_full_variant_is_not_stripped_or_borrowed(price_db, query):
    result = official_points.exact_unit(price_db, query)
    assert result["name_en"] == "Kaius (Prototype)" and result["points"] == 110
    assert all(r["unit_name"] == "Kaius (Prototype)" for r in result["official_prices"])


@pytest.mark.parametrize("name,slug", [("Kaius", "adeptus-custodes"), ("Kaius", "SM"),
                                      ("Kaius Prime", "space-marines")])
def test_wrong_faction_or_variant_has_no_price_fallback(price_db, name, slug):
    assert official_points.exact_unit(price_db, name, faction_slug=slug) is None


@pytest.mark.parametrize("query", ["Marneus Calgar", "普通卡尔加", "卡尔加", "马涅乌斯·卡尔加"])
def test_ordinary_current_180_history_200_and_armour_history_155_remain_distinct(price_db, query):
    result = calculate(price_db, query)
    assert result["points"] == 180 and result["unit_id"] is None
    assert result["name_en"] == "Marneus Calgar" and result["historical_points"] == 200
    assert result["historical_record"]["is_current"] is False
    assert result["historical_record"]["identity_scope"]["model_counts"] == {"calgar": 1, "guard_models": 2}
    assert [r["cost"] for r in result["official_prices"]] == [180, 300]
    armour = calculate(price_db, ARMOUR)
    assert armour["unit_id"] == "100" and armour["points"] is None
    assert "历史点数不作为当前点数" in armour["note"]
    assert not armour.get("points_only") and not armour.get("historical_record")


def test_capture_provenance_is_not_relabelled_as_effective_date(price_db):
    result = official_points.exact_unit(price_db, "Kaius")
    assert result["faction_slug"] == "space-marines"
    assert result["price_status"] == "current_published"
    assert result["effective_date"] is None
    assert result["price_sources"] == [{
        "url": "https://example.invalid/space-marines",
        "sha256": hashlib.sha256(b"space-marines").hexdigest(),
        "captured_at": CAPTURED, "source_date": None,
    }]
    assert "2026-09-30" in result["note"] and "生效" in result["note"]
    assert result["source_scope"] and "兵牌" in result["source_scope"]


def test_scope_and_capture_survive_actual_bounded_price_digest(price_db):
    recorder = TraceRecorder({"calc_points": lambda: tools.calc_points(
        ["Kaius"], db_path=price_db, resolver=EntityResolver(db_path=price_db))})
    recorder.wrapped_tools()["calc_points"]()
    digest = _evidence_digest(recorder)
    assert "Kaius" in digest and "space-marines" in digest and "100" in digest
    assert CAPTURED in digest and "生效日期尚未验证" in digest
    assert "不提供或认证完整兵牌" in digest and "模拟规则" in digest


def test_unequal_cross_faction_prices_also_remain_unqualified(price_db):
    with closing(sqlite3.connect(price_db)) as conn, conn:
        conn.execute("UPDATE official_mfm_points SET cost=130 WHERE faction_slug='adeptus-custodes'")
    result = calculate(price_db, "Shared Hero")
    assert result["points"] is None and result["ambiguous"]
    assert {c["points"] for c in result["candidates"]} == {120, 130}


@pytest.mark.parametrize("query", ["102", "Current Squad", "101", "Kaius Alpha"])
def test_valid_current_canonical_ids_and_names_preserve_exact_prices(price_db, query):
    result = calculate(price_db, query)
    assert result["points"] == (90 if query in ("102", "Current Squad") else 999)
    assert result["unit_id"] == ("102" if query in ("102", "Current Squad") else "101")
    assert not result.get("points_only")


def test_current_canonical_direct_db_path_never_reads_default_db(price_db, monkeypatch):
    def wrong_database():
        pytest.fail("Internal copied-DB lookup used the unrelated default resolver")

    monkeypatch.setattr(tools, "_get_default_resolver", wrong_database)
    assert calculate(price_db, "Current Squad", inject_resolver=False)["points"] == 90


@pytest.mark.parametrize("query", ["Entirely Unknown Unit", "Enhancement Only"])
def test_unknown_name_does_not_invent_zero_or_body(price_db, query):
    assert official_points.exact_unit(price_db, query) is None
    result = calculate(price_db, query)
    assert result["points"] is None and result["unresolved"]
    assert not result.get("points_only")


def test_older_database_without_ledger_keeps_canonical_lookup(price_db):
    with closing(sqlite3.connect(price_db)) as conn, conn:
        conn.execute("DROP TABLE official_mfm_points")
    assert calculate(price_db, "Current Squad")["points"] == 90


def test_lookup_is_read_only_and_public_tool_signature_is_unchanged(price_db):
    before = price_db.read_bytes()
    official_points.exact_unit(price_db, "Chapter Hero")
    calculate(price_db, "Kaius")
    assert price_db.read_bytes() == before
    assert list(inspect.signature(tools.calc_points).parameters) == ["unit_list", "db_path", "resolver"]
