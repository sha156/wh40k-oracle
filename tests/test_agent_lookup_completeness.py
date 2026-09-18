"""Identity and inventory lookups must preserve faction and coverage boundaries."""
import json
import sqlite3

import pytest

from agent import tools
from db_compile.entity_resolver import EntityResolver


def test_resolved_candidate_opens_canonical_page_not_same_name_sibling(tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "index.md").write_text(
        "### Alpha\n| unit | [Commander](wrong.md) | | - |\n"
        "### Beta\n| unit | [Translated commander](right.md) | | - |\n",
        encoding="utf-8",
    )
    for filename, uid, faction in [("wrong.md", "101", "A"), ("right.md", "202", "B")]:
        (wiki / filename).write_text(
            f"---\nid: '{uid}'\nname_en: Commander\nfaction: {faction}\ntype: unit\n---\n\n{faction} rules",
            encoding="utf-8",
        )
    terms = tmp_path / "terms.json"
    terms.write_text(json.dumps({"pairs": [
        {"zh": "Old title", "en": "Commander", "canonical_id": "202", "faction_id": "B"},
        {"zh": "Other title", "en": "Commander", "canonical_id": "101", "faction_id": "A"},
    ]}), encoding="utf-8")
    app = tmp_path / "app.py"
    app.write_text("UNIT_ALIASES = {}", encoding="utf-8")
    resolver = EntityResolver(terms_path=terms, app_path=app)
    result = tools.get_entity("Commander (B)", wiki_root=wiki, resolver=resolver, app_path=app)
    assert result["found"]
    assert result["page"].fm.id == "202"
    assert result["page"].fm.faction == "B"
    # Canonical IDs must work too; the documented argument permits them.
    assert tools.get_entity("202", wiki_root=wiki, resolver=resolver, app_path=app)["page"].fm.id == "202"
    # Once the matching page is absent, do not substitute the other faction.
    (wiki / "right.md").unlink()
    missing = tools.get_entity("Commander (B)", wiki_root=wiki, resolver=resolver, app_path=app)
    assert not missing["found"] and missing["page"] is None


@pytest.fixture
def catalogue(tmp_path):
    path = tmp_path / "units.sqlite"
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE factions(id TEXT, name TEXT);
            CREATE TABLE units(id TEXT, faction_id TEXT, name_en TEXT, name_zh TEXT, points_json TEXT);
            CREATE TABLE official_mfm_points(faction_slug TEXT, kind TEXT, unit_name TEXT,
                source_url TEXT, fetched_at TEXT);
            INSERT INTO factions VALUES ('TL', 'Adeptus Titanicus'), ('ORK', 'Orks');
        """)
        for uid, name, current in [("1", "Warhound Titan", True), ("2", "Reaver Titan", True), ("3", "Old Titan", False)]:
            conn.execute("INSERT INTO units VALUES (?, 'TL', ?, NULL, ?)",
                         (uid, name, json.dumps({"mfm": {"current": current}})))
        for slug, kind, name in [("titan-legions", "unit", "WARHOUND TITAN"),
                                 ("titan-legions", "unit", "WARHOUND TITAN"),
                                 ("titan-legions", "unit", "REAVER TITAN"),
                                 ("titan-legions", "unit", "SOURCE ONLY TITAN"),
                                 ("titan-legions", "enhancement", "Example upgrade")]:
            conn.execute("INSERT INTO official_mfm_points VALUES (?,?,?,?,?)",
                         (slug, kind, name, "https://example.invalid/points", "2026-09-14"))
    return path


def test_inventory_counts_all_current_rows_but_not_tiers_or_missing_datasheets(catalogue):
    result = tools.list_faction_units("Adeptus Titanicus", db_path=catalogue, limit=1)
    assert result["found"]
    assert result["database_count"] == 2
    assert result["returned"] == 1 and result["next_offset"] == 1
    assert result["official_pages"][0]["unit_count"] == 3
    assert "SOURCE ONLY TITAN" in result["official_pages"][0]["unit_names"]
    assert result["scope"] == "current_database_datasheets"
    shared = result["shared_datasheets"]
    assert shared["aliases"]["chaos warlord titan"] == "warlord titan"
    assert shared["source"]["page"] == 2
    assert "published points" in shared["source"]["rule"]
    second = tools.list_faction_units("泰坦军团", db_path=catalogue, offset=1, limit=1)
    assert second["database_count"] == 2 and second["next_offset"] is None
    assert second["units"][0]["id"] != result["units"][0]["id"]


def test_inventory_unknown_faction_and_missing_db_do_not_claim_zero(catalogue, tmp_path):
    assert not tools.list_faction_units("Invented Army", db_path=catalogue)["found"]
    missing = tmp_path / "absent.sqlite"
    assert not tools.list_faction_units("TL", db_path=missing)["found"]
    assert not missing.exists()


@pytest.mark.parametrize("kwargs", [{"offset": -1}, {"limit": 51}, {"limit": True}, {"offset": "0"}])
def test_inventory_rejects_invalid_pagination(catalogue, kwargs):
    assert tools.list_faction_units("TL", db_path=catalogue, **kwargs)["param_error"]


def test_inventory_wire_result_keeps_every_returned_row():
    from agent.llm_client import _render_loop_message
    rows = [{"id": str(n), "name_en": "Long unit name " * 12} for n in range(50)]
    result = {"database_count": 70, "returned": 50, "next_offset": 50, "units": rows}
    wire = _render_loop_message({"role": "tool", "name": "list_faction_units", "content": result})
    assert len(wire["content"]) > 4000
    assert json.loads(wire["content"].split("\n", 1)[1]) == result


def test_duplicate_canonical_ids_fail_closed(tmp_path):
    from wiki_engine.operations.query_op import find_entity_by_id, load_index
    (tmp_path / "index.md").write_text(
        "| unit | [One](one.md) | | - |\n| unit | [Two](two.md) | | - |\n", encoding="utf-8")
    for filename in ["one.md", "two.md"]:
        (tmp_path / filename).write_text("---\nid: '202'\ntype: unit\n---\n\nExample", encoding="utf-8")
    assert find_entity_by_id("202", load_index(tmp_path), tmp_path) is None


def test_merged_card_source_scope_survives_wire_truncation(tmp_path):
    from agent.llm_client import _render_loop_message

    (tmp_path / "index.md").write_text(
        "| unit | [Commander](commander.md) | | - |\n", encoding="utf-8")
    (tmp_path / "commander.md").write_text(
        "---\nid: '202'\nname_en: Commander\ntype: unit\n"
        "version:\n  source: official-db\nsources:\n"
        "- book: Keyword patch\n  pages: [23]\n---\n\n" + "Weapon rows\n" * 800,
        encoding="utf-8")
    result = tools.get_entity("Commander", wiki_root=tmp_path)
    assert result["page"].fm.sources[0]["pages"] == [23]
    wire = _render_loop_message({"role": "tool", "name": "get_entity", "content": result})
    assert "中间省略" in wire["content"]
    assert result["source_scope"] in wire["content"]
    assert "不是逐字段出处" in result["source_scope"]
