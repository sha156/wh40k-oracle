# tests/test_db_compile_datasheet.py
"""datasheet：unit_id → 完整英文属性块（models + weapons + points）。"""
import json
import sqlite3

import pytest

from db_compile.datasheet import find_datasheet, lookup_datasheet


def _make_db(tmp_path):
    """自建最小库：1 阵营 + 1 单位（含 model 属性、1 远程 1 近战武器）。"""
    db = tmp_path / "t.sqlite"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        """
        CREATE TABLE factions (id TEXT PRIMARY KEY, name TEXT);
        CREATE TABLE datasheets (id TEXT PRIMARY KEY, name TEXT, faction_id TEXT);
        CREATE TABLE units (id TEXT PRIMARY KEY, faction_id TEXT, name_en TEXT,
                            name_zh TEXT, points_json TEXT, keywords_json TEXT, version TEXT);
        CREATE TABLE models (unit_id TEXT, name TEXT, m TEXT, t TEXT, sv TEXT,
                            invuln TEXT, w TEXT, ld TEXT, oc TEXT, count_options_json TEXT);
        CREATE TABLE weapons (id TEXT PRIMARY KEY, unit_id TEXT, name_zh TEXT, name_en TEXT,
                            range TEXT, a TEXT, bs_ws TEXT, s TEXT, ap TEXT, d TEXT, keywords_json TEXT);
        """
    )
    conn.execute("INSERT INTO factions VALUES ('CSM','Chaos Space Marines')")
    conn.execute("INSERT INTO datasheets VALUES ('000000929','Chaos Lord','CSM')")
    conn.execute(
        "INSERT INTO units VALUES ('000000929','CSM','Chaos Lord',NULL,?,?,NULL)",
        (json.dumps({"points": 85, "items": [{"line": "1", "desc": "1 model", "cost": 85}]}),
         json.dumps({"keywords": ["Infantry", "Character"], "faction_keywords": ["Chaos"]})),
    )
    conn.execute("INSERT INTO models VALUES ('000000929','Chaos Lord','6\"','4','3+','4','4','6+','1',NULL)")
    conn.execute(
        "INSERT INTO weapons VALUES ('000000929_w1','000000929',NULL,'Plasma pistol – standard',"
        "'12','1','3+','7','-2','1',?)", (json.dumps(["pistol"]),))
    conn.execute(
        "INSERT INTO weapons VALUES ('000000929_w2','000000929',NULL,'Accursed weapon',"
        "'Melee','6','3+','5','-2','1',NULL)")
    conn.commit()
    conn.close()
    return db


class TestLookupDatasheet:
    def test_returns_full_statblock(self, tmp_path):
        ds = lookup_datasheet(_make_db(tmp_path), "000000929")
        assert ds is not None
        assert ds.name_en == "Chaos Lord"
        assert ds.faction == "Chaos Space Marines"
        assert ds.points_min == 85
        assert ds.keywords == ["Infantry", "Character"]

    def test_model_profile(self, tmp_path):
        ds = lookup_datasheet(_make_db(tmp_path), "000000929")
        m = ds.models[0]
        assert (m.m, m.t, m.sv, m.invuln, m.w, m.oc) == ('6"', "4", "3+", "4", "4", "1")

    def test_weapons_split_ranged_and_melee(self, tmp_path):
        ds = lookup_datasheet(_make_db(tmp_path), "000000929")
        ranged = [w for w in ds.weapons if w.kind == "ranged"]
        melee = [w for w in ds.weapons if w.kind == "melee"]
        assert [w.name for w in ranged] == ["Plasma pistol – standard"]
        assert [w.name for w in melee] == ["Accursed weapon"]
        assert ranged[0].s == "7" and ranged[0].ap == "-2"
        assert ranged[0].keywords == ["pistol"]

    def test_missing_unit_returns_none(self, tmp_path):
        assert lookup_datasheet(_make_db(tmp_path), "999999999") is None


class TestFindDatasheet:
    def test_find_by_english_name(self, tmp_path):
        ds = find_datasheet(_make_db(tmp_path), "Chaos Lord")
        assert ds is not None and ds.unit_id == "000000929"

    def test_find_unknown_returns_none(self, tmp_path):
        assert find_datasheet(_make_db(tmp_path), "No Such Unit") is None
