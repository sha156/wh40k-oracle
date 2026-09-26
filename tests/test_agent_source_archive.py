"""Historical source cards remain evidence without becoming current roster units."""
import json
import sqlite3
from contextlib import closing

import pytest

from agent import tools
from agent.loop import AgentResult, _is_empty_result
from db_compile.build import build_database
from db_compile.entity_resolver import EntityResolver
from db_compile.source_archive import project_deleted_details
from web_api.formatter import _derive_cites, _evidence_digest
from web_api.trace import TraceRecorder


@pytest.fixture
def archive_db(tmp_path):
    source = tmp_path / "csv"
    source.mkdir()
    (source / "Factions.csv").write_text(
        "id|name|link|\nSM|Space Marines|https://example.org|\n", encoding="utf-8")
    (source / "Datasheets.csv").write_text(
        "id|name|faction_id|source_id|legend|role|loadout|transport|virtual|"
        "leader_head|leader_footer|damaged_w|damaged_description|link|\n"
        "armour|Marneus Calgar in Armour of Antilochus|SM|1||||||||||https://example.org|\n"
        "guilliman|Roboute Guilliman|SM|1||||||||||https://example.org|\n", encoding="utf-8")
    db = tmp_path / "units.sqlite"
    build_database(source, db)
    with sqlite3.connect(str(db)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM units").fetchone()[0] == 2
        for uid, cost in (("armour", 155), ("guilliman", 355)):
            conn.execute("UPDATE units SET points_json=? WHERE id=?",
                         (json.dumps({"points": cost}), uid))
    project_deleted_details(db, details=[{
        "id": 6, "name_en": "Marneus Calgar", "name_zh": "马涅乌斯.卡尔加（已删除）",
        "faction_zh": "极限战士", "score": 200,
        "composition": "Marneus Calgar and two Victrix Honour Guard",
    }])
    return db, EntityResolver(db_path=db)


@pytest.mark.parametrize("query", ["普通卡尔加", "卡尔加", "Marneus Calgar", "马涅乌斯·卡尔加"])
def test_points_keep_historical_and_current_variants_separate(archive_db, query):
    db, resolver = archive_db
    result = tools.calc_points(["guilliman", query, "armour"], db_path=db, resolver=resolver)
    current, old, armour = result["units"]
    assert current["points"] == 355
    assert armour["points"] == 155
    assert old["points"] is None
    assert old["unit_id"] is None
    assert old["historical_points"] == 200
    assert old["historical_record"]["source_id"] == "6"
    scope = old["historical_record"]["identity_scope"]
    assert scope["model_counts"] == {"calgar": 1, "guard_models": 2}
    assert "two Victrix Honour Guard" in scope["composition_evidence"]
    assert "不得反称缓存未区分这些版本" in old["note"]
    assert "raw" not in old["historical_record"]
    assert not old.get("unresolved")
    assert not _is_empty_result("calc_points", tools.calc_points([query], db_path=db, resolver=resolver))


@pytest.mark.parametrize("tool", ["get_datasheet", "get_entity", "entity_resolver"])
def test_archive_lookup_survives_empty_result_gate(archive_db, tool, tmp_path):
    db, resolver = archive_db
    if tool == "get_datasheet":
        result = tools.get_datasheet("马涅乌斯·卡尔加", db_path=db, resolver=resolver)
        assert result["datasheet"] is None
    elif tool == "get_entity":
        result = tools.get_entity("普通卡尔加", wiki_root=tmp_path / "wiki", resolver=resolver)
        assert result["page"] is None
    else:
        result = tools.entity_resolver("Marneus Calgar", resolver=resolver)
        assert result["canonical_id"] is None
    assert result["historical_record"]["raw"]["score"] == 200
    assert not _is_empty_result(tool, result)


def test_current_exact_identity_wins_over_older_archive(archive_db):
    db, _ = archive_db
    with sqlite3.connect(str(db)) as conn:
        conn.execute("UPDATE datasheets SET name='Marneus Calgar' WHERE id='armour'")
        conn.execute("UPDATE units SET name_en='Marneus Calgar' WHERE id='armour'")
    result = tools.calc_points(["Marneus Calgar"], db_path=db, resolver=EntityResolver(db_path=db))
    assert result["units"][0]["points"] == 155
    assert "historical_record" not in result["units"][0]


def test_historical_citation_and_digest_never_claim_current_authority(archive_db):
    db, resolver = archive_db
    recorder = TraceRecorder({"get_datasheet": lambda name: tools.get_datasheet(name, db_path=db, resolver=resolver)})
    recorder.wrapped_tools()["get_datasheet"]("普通卡尔加")
    cites = _derive_cites(AgentResult(answer="Historical 200", intent="查"), recorder)
    assert len(cites) == 1
    assert "历史" in cites[0].book and "黑图书馆" in cites[0].book
    assert "L3" not in cites[0].book and "Munitorum" not in cites[0].book
    assert cites[0].url is None  # The source endpoint is POST-only, not a detail permalink.
    digest = _evidence_digest(recorder)
    assert "historical_points" in digest and "200" in digest
    assert "第三方" in digest and "当前" in digest
    assert "retained_source_unit_composition" in digest
    assert "two Victrix Honour Guard" in digest
    assert "安提洛库斯之铠版本" in digest


def test_points_only_archive_call_has_own_citation(archive_db):
    db, resolver = archive_db
    recorder = TraceRecorder({"calc_points": lambda: tools.calc_points(["普通卡尔加"], db_path=db, resolver=resolver)})
    recorder.wrapped_tools()["calc_points"]()
    cites = _derive_cites(AgentResult(answer="Historical 200", intent="查"), recorder)
    assert len(cites) == 1 and "历史" in cites[0].book


@pytest.fixture
def official_archive_db(archive_db):
    db, resolver = archive_db
    with closing(sqlite3.connect(str(db))) as conn, conn:
        conn.execute("""CREATE TABLE official_mfm_points(
            faction_slug TEXT, ordinal INTEGER, kind TEXT, unit_name TEXT,
            models TEXT, tier TEXT, cost INTEGER, fetched_at TEXT, source_url TEXT)""")
        conn.execute("""INSERT INTO official_mfm_points VALUES(
            'space-marines', 1, 'unit', 'Marneus Calgar', '1 model',
            'YOUR UNIT COSTS', 250, 'fixture', 'https://example.invalid/current-points')""")
    return db, resolver


@pytest.mark.parametrize("query", ["Marneus Calgar", "普通卡尔加", "卡尔加", "马涅乌斯·卡尔加"])
def test_exact_official_ledger_precedes_archive_and_keeps_history_distinct(
        official_archive_db, query):
    db, resolver = official_archive_db
    recorder = TraceRecorder({"calc_points": lambda: tools.calc_points(
        [query], db_path=db, resolver=resolver)})
    result = recorder.wrapped_tools()["calc_points"]()
    unit = result["units"][0]
    assert unit["points"] == 250 and unit["points_only"]
    assert unit["unit_id"] is None  # A price-only match does not invent a datasheet.
    assert unit["historical_points"] == 200
    assert unit["historical_record"]["is_current"] is False
    assert unit["name_en"] == "Marneus Calgar"
    assert "raw" not in unit["historical_record"]
    assert result["official_sources"] == [{
        "url": "https://example.invalid/current-points", "fetched_at": "fixture"}]
    cites = _derive_cites(AgentResult(answer="Current 250; historical 200", intent="查"), recorder)
    assert any(c.book == "Munitorum Field Manual" for c in cites)
    assert any("历史" in c.book for c in cites)


def test_ambiguous_official_prices_are_not_replaced_with_historical_price(official_archive_db):
    db, resolver = official_archive_db
    with closing(sqlite3.connect(str(db))) as conn, conn:
        conn.execute("""INSERT INTO official_mfm_points VALUES(
            'other-faction', 1, 'unit', 'Marneus Calgar', '1 model',
            'YOUR UNIT COSTS', 260, 'fixture', 'https://example.invalid/other-points')""")
    unit = tools.calc_points(["普通卡尔加"], db_path=db, resolver=resolver)["units"][0]
    assert unit["points"] is None and unit["points_only"]
    assert {r["cost"] for r in unit["official_prices"]} == {250, 260}
    assert unit["historical_points"] == 200
