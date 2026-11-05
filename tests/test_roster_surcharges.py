"""Unknown equipment cannot silently bypass an official per-weapon price."""
import json
import sqlite3

import pytest

from engines.roster import Roster, RosterUnit, validate
from engines.roster.points import _official_cost, recompute


ROWS = [
    {"tier": "YOUR UNIT COSTS", "models": "1 model", "cost": 225},
    {"tier": "YOUR UNIT COSTS", "models": "Per Paid cannon", "cost": 15},
]


@pytest.fixture
def priced_db(tmp_path):
    db = tmp_path / "surcharges.sqlite"
    with sqlite3.connect(str(db)) as conn:
        conn.executescript("""
            CREATE TABLE factions(id TEXT, name TEXT);
            CREATE TABLE units(id TEXT, name_en TEXT, faction_id TEXT,
                               points_json TEXT, keywords_json TEXT);
            CREATE TABLE weapons(unit_id TEXT, name_en TEXT);
            CREATE TABLE enhancements(detachment_id TEXT, faction_id TEXT,
                                      detachment_name TEXT, name TEXT, cost INTEGER);
            INSERT INTO factions VALUES('AC', 'Adeptus Custodes');
            INSERT INTO weapons VALUES('tank', 'Paid cannon'), ('tank', 'Free cannon');
        """)
        conn.execute("INSERT INTO units VALUES(?,?,?,?,?)", (
            "tank", "Fixture tank", "AC", json.dumps({"mfm": {"tiers": ROWS}}),
            json.dumps({"keywords": ["CHARACTER"]})))
    return db


@pytest.mark.parametrize("name,expected", [
    ("Typo cannon", None), ("Paid cannon", 240),
    ("Paid cannon - focused", 240), ("Free cannon", 225),
])
def test_only_verified_free_or_paid_equipment_can_be_priced(priced_db, name, expected):
    roster = Roster("AC", None, "strike_force", (
        RosterUnit("tank", "Fixture tank", 1, is_warlord=True, loadout=((name, 1),)),))
    assert recompute(priced_db, roster).units[0].points == expected
    report = validate(priced_db, roster)
    if expected is None:
        assert any(i.code == "unit_unpriced" and i.surfaced_only for i in report.issues)
    else:
        assert report.total_points == expected and report.issues == ()


def test_unknown_equipment_without_a_weapon_catalog_is_not_assumed_free():
    assert _official_cost(ROWS, 1, 1, (("Typo cannon", 1),)) is None


@pytest.mark.parametrize("count", [0, -1, True, 1.5])
def test_invalid_equipment_count_cannot_reduce_or_skip_the_price(count):
    assert _official_cost(ROWS, 1, 1, (("Paid cannon", count),)) is None
