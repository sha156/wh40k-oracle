"""db_compile/dup_units.py 测试：疑似重复单位排查（只读、只出报告）。"""
from __future__ import annotations

import json
import sqlite3

import pytest

from db_compile.dup_units import audit, format_report, normalize_en, normalize_zh


def _mk_db(path, units, datasheets=(), zh_rows=()):
    conn = sqlite3.connect(str(path))
    conn.executescript(
        "CREATE TABLE units (id TEXT PRIMARY KEY, faction_id TEXT, name_en TEXT,"
        " name_zh TEXT, points_json TEXT, keywords_json TEXT, version TEXT);"
        "CREATE TABLE datasheets (id TEXT PRIMARY KEY, name TEXT, faction_id TEXT,"
        " source_id TEXT, role TEXT, link TEXT);"
        "CREATE TABLE unit_zh_detail (canonical_id TEXT PRIMARY KEY, abilities_json TEXT);"
        "CREATE TABLE abilities (id TEXT, owner_id TEXT);"
        "CREATE TABLE weapons (id TEXT, unit_id TEXT);"
        "CREATE TABLE models (unit_id TEXT);"
    )
    conn.executemany("INSERT INTO units (id, faction_id, name_en, name_zh, points_json)"
                     " VALUES (?,?,?,?,?)", units)
    conn.executemany("INSERT INTO datasheets (id, name, faction_id, source_id, role, link)"
                     " VALUES (?,?,?,?,?,?)", datasheets)
    conn.executemany("INSERT INTO unit_zh_detail (canonical_id, abilities_json)"
                     " VALUES (?,?)", zh_rows)
    conn.commit()
    conn.close()


CURRENT = json.dumps({"points": 80, "items": [{"desc": "1 model", "cost": 80}],
                      "mfm": {"fetched_at": "2026-07-26"}})
LEGACY = json.dumps({"points": 105, "items": [{"desc": "1 model", "cost": 105}]})


class TestNormalize:
    @pytest.mark.parametrize("a,b", [
        ("Hellflayers", "Hellflayer"),
        ("Flesh Hounds", "flesh hound"),
        ("Land Raider Crusader", "land-raider crusader"),
        ("Furies", "Fury"),
    ])
    def test_plural_and_punctuation_collapse(self, a, b):
        assert normalize_en(a) == normalize_en(b)

    def test_double_s_not_stripped(self):
        # Boss ≠ Bos：ss 结尾不当复数处理
        assert normalize_en("Warboss") == "warboss"

    def test_distinct_units_stay_distinct(self):
        assert normalize_en("Bloodletters") != normalize_en("Bloodcrushers")

    def test_zh_drops_whitespace_only(self):
        assert normalize_zh(" 地狱 剥皮机 ") == "地狱剥皮机"


class TestAudit:
    def test_finds_plural_pair_and_picks_current(self, tmp_path):
        db = tmp_path / "t.sqlite"
        _mk_db(db,
               units=[("1", "CD", "Hellflayers", "地狱剥皮机", CURRENT),
                      ("2", "CD", "Hellflayer", "地狱剥皮机", LEGACY),
                      ("3", "CD", "Bloodletters", "血letter", CURRENT)],
               datasheets=[("1", "Hellflayers", "CD", "S1", "Other", "http://x/Hellflayers"),
                           ("2", "Hellflayer", "CD", "S2", "Other", "http://x/Hellflayer"),
                           ("3", "Bloodletters", "CD", "S1", "Other", "http://x/B")],
               zh_rows=[("2", json.dumps([{"name": "a"}]))])
        rep = audit(db)
        assert rep["counts"]["groups"] == 1
        assert rep["counts"]["units_involved"] == 2
        g = rep["groups"][0]
        assert [m["id"] for m in g["members"]] == ["1", "2"]   # 现役排前
        assert g["members"][0]["verdict"] == "likely_current"
        assert g["members"][1]["verdict"] == "likely_legacy"
        assert g["members"][1]["has_zh_row"] is True
        assert g["members"][1]["zh_abilities"] == 1

    def test_both_current_stays_undecided(self, tmp_path):
        """两条都在现行 MFM 表里 → 多半是官方真有两张同名兵牌，不替用户拍板。"""
        db = tmp_path / "t.sqlite"
        _mk_db(db,
               units=[("1", "SM", "Impulsor", "冲击者突击艇", CURRENT),
                      ("2", "SM", "Impulsor", "冲击者突击艇", CURRENT)],
               datasheets=[("1", "Impulsor", "SM", "S1", "Other", "http://x/Impulsor"),
                           ("2", "Impulsor", "SM", "S2", "Other", "http://x/Impulsor-1")])
        rep = audit(db)
        assert rep["counts"]["groups_undecided"] == 1
        assert {m["verdict"] for m in rep["groups"][0]["members"]} == {"undecided"}
        # Wahapedia 自带的同名消歧后缀是"上游本来就有两张"的直接证据
        assert rep["groups"][0]["members"][1]["link_dup_suffix"] == "1"

    def test_same_name_different_faction_is_not_a_group(self, tmp_path):
        db = tmp_path / "t.sqlite"
        _mk_db(db,
               units=[("1", "SM", "Land Raider", "兰德掠袭者", CURRENT),
                      ("2", "CSM", "Land Raider", "兰德掠袭者", CURRENT)],
               datasheets=[("1", "Land Raider", "SM", "S1", "", ""),
                           ("2", "Land Raider", "CSM", "S2", "", "")])
        assert audit(db)["counts"]["groups"] == 0

    def test_zh_name_bridges_title_prefix(self, tmp_path):
        """英文名差个头衔前缀、中文名相同 → 判据 (b) 接上。"""
        db = tmp_path / "t.sqlite"
        _mk_db(db,
               units=[("1", "AM", "Lord Solar Leontus", "利昂图斯", CURRENT),
                      ("2", "AM", "Leontus", "利昂图斯", LEGACY)],
               datasheets=[("1", "Lord Solar Leontus", "AM", "S1", "", ""),
                           ("2", "Leontus", "AM", "S2", "", "")])
        rep = audit(db)
        assert rep["counts"]["groups"] == 1
        assert rep["groups"][0]["size"] == 2

    def test_clean_db_reports_nothing(self, tmp_path):
        db = tmp_path / "t.sqlite"
        _mk_db(db,
               units=[("1", "CD", "Bloodletters", "血letter", CURRENT),
                      ("2", "CD", "Bloodcrushers", "血crusher", CURRENT)],
               datasheets=[("1", "Bloodletters", "CD", "S1", "", ""),
                           ("2", "Bloodcrushers", "CD", "S1", "", "")])
        rep = audit(db)
        assert rep["counts"] == {"groups": 0, "units_involved": 0,
                                 "groups_decided": 0, "groups_undecided": 0}
        assert "疑似重复组：0" in format_report(rep)

    def test_audit_writes_nothing(self, tmp_path):
        """红线：只出报告，一行数据都不许改。用连接前后的库字节做机械证据。"""
        db = tmp_path / "t.sqlite"
        _mk_db(db,
               units=[("1", "CD", "Hellflayers", "地狱剥皮机", CURRENT),
                      ("2", "CD", "Hellflayer", "地狱剥皮机", LEGACY)],
               datasheets=[("1", "Hellflayers", "CD", "S1", "", ""),
                           ("2", "Hellflayer", "CD", "S2", "", "")])
        before = db.read_bytes()
        audit(db)
        assert db.read_bytes() == before

    def test_report_lists_every_member(self, tmp_path):
        db = tmp_path / "t.sqlite"
        _mk_db(db,
               units=[("1", "CD", "Hellflayers", "地狱剥皮机", CURRENT),
                      ("2", "CD", "Hellflayer", "地狱剥皮机", LEGACY)],
               datasheets=[("1", "Hellflayers", "CD", "S1", "Other", "http://x/H"),
                           ("2", "Hellflayer", "CD", "S2", "Other", "http://x/H2")])
        text = format_report(audit(db))
        assert "疑似重复组：1（涉及 2 行）" in text
        assert "000001144" not in text        # 用的是本测试库，不是真库
        assert "Hellflayers" in text and "Hellflayer /" in text
        assert "likely_current" in text and "likely_legacy" in text
