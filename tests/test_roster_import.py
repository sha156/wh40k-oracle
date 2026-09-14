import json
import sqlite3
from contextlib import closing

import pytest
from engines.roster.parse import parse_roster
from engines.roster.points import _official_cost
from db_compile.point_tiers import minimum_unit_cost, model_count


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "roster.sqlite"
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.executescript("""
        CREATE TABLE factions(id TEXT,name TEXT);
        CREATE TABLE units(id TEXT,faction_id TEXT,name_en TEXT,name_zh TEXT);
        CREATE TABLE enhancements(id TEXT,detachment_id TEXT,detachment_name TEXT,faction_id TEXT,name TEXT);
        CREATE TABLE weapons(unit_id TEXT,name_en TEXT);
        INSERT INTO factions VALUES ('SM','Space Marines');
        INSERT INTO units VALUES ('squad','SM','Intercessor Squad','');
        INSERT INTO units VALUES ('hero','SM','Captain','');
        INSERT INTO enhancements VALUES ('e','d','Gladius Task Force','SM','Test Enhancement');
        INSERT INTO weapons VALUES ('squad','Bolt rifle');
        """)
    return path


def test_import_resolves_complete_list_and_equipment(db):
    result = parse_roster(db, "Faction: Space Marines\nDetachment: Gladius Task Force\n5x Intercessor Squad | weapons=Bolt rifle:5\nCaptain | models=1 | warlord | enhancement=Test Enhancement")
    assert result["complete"]
    assert [u["canonicalId"] for u in result["roster"]["units"]] == ["squad", "hero"]
    assert result["roster"]["units"][0]["loadout"] == [["Bolt rifle", 5]]
    assert result["roster"]["units"][1]["isWarlord"]


@pytest.mark.parametrize("bad", ["5x Imaginary unit", "Captain", "Captain | models=1 | ability=Flying", "Captain | models=1 | weapons=Fake Gun:1"])
def test_unrecognized_lines_never_disappear_or_validate_partial_roster(db, bad):
    result = parse_roster(db, "5x Intercessor Squad\n" + bad, "SM")
    assert not result["complete"]
    assert len(result["roster"]["units"]) == 1
    assert result["issues"][0]["line"] == 2
    assert result["issues"][0]["text"] == bad


def test_repeat_unit_price_and_paid_weapon_are_separate():
    rows = [{"tier": tier, "models": desc, "cost": cost} for tier, desc, cost in [
        ("YOUR 1ST TO 2ND UNITS COST", "5 models", 80),
        ("YOUR 3RD + UNIT COSTS", "5 models", 100),
        ("YOUR 1ST TO 2ND UNITS COST", "per Plasma cannon", 5),
        ("YOUR 3RD + UNIT COSTS", "per Plasma cannon", 5),
    ]]
    assert _official_cost(rows, 5, 2, [("Plasma cannon", 2)]) == 90
    assert _official_cost(rows, 5, 3, [("Plasma cannon", 2)]) == 110
    assert _official_cost(rows, 5, 3, []) is None
    assert _official_cost(rows, 7, 3, [("Plasma cannon", 2)]) is None


def test_surcharge_never_becomes_minimum_unit_price():
    items = [{"desc": "5 models", "cost": 80}, {"desc": "per Plasma cannon", "cost": 5}]
    assert minimum_unit_cost(items) == 80
    from db_compile.calc_points import _min_points
    from db_compile.datasheet import _parse_points
    raw = json.dumps({"mfm": {"current": True}, "items": items})
    assert _min_points(raw) == _parse_points(raw)[0] == 80
    assert model_count("1 Sword Brother, 4 Neophytes, 5 Initiates") == 10
    assert model_count("+ 1 Invader ATV") is None
    assert model_count("3 X and 3 Y") is None
