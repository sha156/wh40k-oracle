# tests/test_db_compile_datasheet.py
"""datasheet：unit_id → 完整英文属性块（models + weapons + points）。"""
import json
import sqlite3

import pytest

from db_compile.datasheet import (
    AmbiguousUnitName,
    Datasheet,
    ModelProfile,
    diff_core_stats,
    find_datasheet,
    lookup_datasheet,
)


def _ds(models):
    return Datasheet(unit_id="1", name_en="X", name_zh=None, faction=None,
                     points_min=None, points_options=[], keywords=[],
                     models=models, weapons=[])


def _model(m="10", t="10", sv="3", w="12"):
    return ModelProfile(name="X", m=m, t=t, sv=sv, invuln="-", w=w, ld="6", oc="1")


class TestDiffCoreStats:
    """官方(Wahapedia) 与黑图书馆中文层的 M/T/SV/W 冲突检测。"""

    def test_detects_conflict(self):
        ds = _ds([_model(t="10", w="12")])
        zh = {"属性": [{"m": "10", "t": "9", "sv": "3", "w": "14"}]}
        got = {c["field"]: (c["official"], c["blackforum"]) for c in diff_core_stats(ds, zh)}
        assert got == {"T": ("10", "9"), "W": ("12", "14")}

    def test_no_conflict_when_equal_after_normalization(self):
        # 官方带寸/加号，黑图不带 —— 归一化后相等，不算冲突
        ds = _ds([_model(m='10"', sv="3+", t="10", w="12")])
        zh = {"属性": [{"m": "10", "t": "10", "sv": "3", "w": "12"}]}
        assert diff_core_stats(ds, zh) == []

    def test_skips_multi_model_units(self):
        ds = _ds([_model(), _model(t="8")])
        zh = {"属性": [{"m": "10", "t": "9", "sv": "3", "w": "14"}]}
        assert diff_core_stats(ds, zh) == []

    def test_skips_missing_blackforum_values(self):
        ds = _ds([_model(t="10")])
        zh = {"属性": [{"m": "10", "t": "?", "sv": "", "w": None}]}
        assert diff_core_stats(ds, zh) == []

    def test_empty_zh_returns_no_conflict(self):
        assert diff_core_stats(_ds([_model()]), None) == []


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

    def test_rejects_fuzzy_match_to_avoid_confident_wrong_answer(self, tmp_path):
        # "Chaos Lorr"(错别字) 会被 entity_resolver 模糊匹配到 Chaos Lord；
        # 数值权威路径必须拒绝 fuzzy，返回 None 而非错答案。
        assert find_datasheet(_make_db(tmp_path), "Chaos Lorr") is None

    @staticmethod
    def _add_we_twin(db):
        """往库里加一个跨阵营同名单位（评审 #25：Helbrute×4 场景的最小复刻）。"""
        conn = sqlite3.connect(str(db))
        conn.execute("INSERT INTO factions VALUES ('WE','World Eaters')")
        conn.execute("INSERT INTO datasheets VALUES ('000002632','Chaos Lord','WE')")
        conn.execute(
            "INSERT INTO units VALUES ('000002632','WE','Chaos Lord',NULL,NULL,NULL,NULL)")
        conn.execute("INSERT INTO models VALUES ('000002632','Chaos Lord','9\"','4',"
                     "'3+','4','5','6+','1',NULL)")
        conn.commit()
        conn.close()
        return db

    def test_cross_faction_same_name_raises_ambiguous(self, tmp_path):
        db = self._add_we_twin(_make_db(tmp_path))
        with pytest.raises(AmbiguousUnitName) as ei:
            find_datasheet(db, "Chaos Lord")
        assert set(ei.value.candidates) == {"Chaos Lord (CSM)", "Chaos Lord (WE)"}
        # hits 带 (unit_id, name_en, faction_id)，供 get_datasheet 生成候选属性预览
        assert {(h[0], h[2]) for h in ei.value.hits} == {
            ("000000929", "CSM"), ("000002632", "WE")}

    def test_faction_qualified_name_resolves_uniquely(self, tmp_path):
        # 候选串原样回填 → 走 entity_resolver 的 `名字 (阵营)` 消歧 → 精确命中
        db = self._add_we_twin(_make_db(tmp_path))
        from db_compile.entity_resolver import EntityResolver
        resolver = EntityResolver(db_path=db)
        ds = find_datasheet(db, "Chaos Lord (WE)", resolver=resolver)
        assert ds is not None and ds.unit_id == "000002632"
        ds2 = find_datasheet(db, "Chaos Lord (CSM)", resolver=resolver)
        assert ds2 is not None and ds2.unit_id == "000000929"
