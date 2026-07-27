# tests/test_db_compile_zh_coverage.py
"""兵牌中文技能覆盖对账 + 中文名桥。

两条纪律：
- 归因必须**穷尽** units 全表：各类计数之和恒等于 units 行数，漏一类当场露馅；
- 中文名桥只补英文名对不上的行，且只认一对一——歧义宁可少灌也不错配。

除 mock 用例外，末尾两条直接跑真库/真缓存（缺则跳过），断言的是「对账守恒」
与「补不到的单位不许凭空出现中文正文」这两件本轮真正要保的事。
"""
import json
import sqlite3
from pathlib import Path

import pytest

from db_compile.blacklibrary import _norm_zh, populate_zh_details
from db_compile.zh_coverage import CATEGORIES, audit, format_report

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "db" / "wh40k.sqlite"
LIST_CACHE = REPO / "db_sources" / "blacklibrary" / "units.json"
DETAILS_CACHE = REPO / "db_sources" / "blacklibrary" / "details.json"


def _mk_db(tmp_path, units):
    db = tmp_path / "t.sqlite"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE units (id TEXT PRIMARY KEY, name_en TEXT, name_zh TEXT)")
    conn.executemany("INSERT INTO units VALUES (?,?,?)", units)
    conn.commit()
    conn.close()
    return db


def _rec(name_en, name_zh, abilities):
    return {"id": 1, "faction_zh": "钛帝国", "name_zh": name_zh, "name_en": name_en,
            "score": 100,
            "detail": {"属性": [], "能力": abilities, "射击武器": [], "近战武器": [],
                       "简介": []}}


class TestNormZh:
    def test_strips_decorative_punctuation_only(self):
        assert _norm_zh("克拉维克·莫恩") == "克拉维克莫恩"
        assert _norm_zh("【传奇】地狱之末") == "传奇地狱之末"
        assert _norm_zh(" 战 群 统 领 ") == "战群统领"

    def test_does_not_conflate_different_names(self):
        # 一字之差就是另一张兵牌——归一化只碰标点，绝不做同义改写
        assert _norm_zh("克鲁特猎犬") != _norm_zh("克鲁特猎犬队")


class TestZhNameBridge:
    def test_bridges_when_english_name_differs_only_in_writing(self, tmp_path):
        db = _mk_db(tmp_path, [("u1", "Kravek Morne", "克拉维克·莫恩")])
        rep = populate_zh_details(
            db, [_rec("Warsmith Kravek Morne", "克拉维克·莫恩", [{"name": "技能A"}])])
        assert rep["matched"] == 1 and rep["matched_by_zh"] == 1
        conn = sqlite3.connect(str(db))
        row = conn.execute(
            "SELECT abilities_json FROM unit_zh_detail WHERE canonical_id='u1'").fetchone()
        conn.close()
        assert json.loads(row[0])[0]["name"] == "技能A"

    def test_english_match_wins_and_bridge_never_overwrites_it(self, tmp_path):
        # 两条源记录中文名相同，其一英文名能对上 u1——u1 必须留英文名匹配的那条
        db = _mk_db(tmp_path, [("u1", "Hellflayer", "地狱剥皮机")])
        rep = populate_zh_details(db, [
            _rec("Hellflayer", "地狱剥皮机", [{"name": "英文名命中"}]),
            _rec("Hellflayers", "地狱剥皮机", [{"name": "中文名桥"}]),
        ])
        assert rep["matched_by_zh"] == 0
        conn = sqlite3.connect(str(db))
        row = conn.execute(
            "SELECT abilities_json FROM unit_zh_detail WHERE canonical_id='u1'").fetchone()
        conn.close()
        assert json.loads(row[0])[0]["name"] == "英文名命中"

    def test_ambiguous_chinese_name_is_dropped_not_guessed(self, tmp_path):
        # 源侧同一中文名两条、英文名都对不上 → 无法判定指向谁，一条都不灌
        db = _mk_db(tmp_path, [("u1", "Some Unit", "重名单位")])
        rep = populate_zh_details(db, [
            _rec("Other A", "重名单位", [{"name": "甲"}]),
            _rec("Other B", "重名单位", [{"name": "乙"}]),
        ])
        assert rep["matched"] == 0 and rep["matched_by_zh"] == 0
        conn = sqlite3.connect(str(db))
        assert conn.execute("SELECT COUNT(*) FROM unit_zh_detail").fetchone()[0] == 0
        conn.close()


class TestAuditAttribution:
    def test_every_unit_lands_in_exactly_one_category(self, tmp_path):
        db = _mk_db(tmp_path, [("u1", "Alpha", "甲"), ("u2", "Beta", "乙"),
                               ("u3", "Gamma", "丙")])
        populate_zh_details(db, [_rec("Alpha", "甲", [{"name": "技能"}]),
                                 _rec("Beta", "乙", [])])
        lc = tmp_path / "units.json"
        lc.write_text(json.dumps([{"unitEnglishName": "Alpha", "unitName": "甲"},
                                  {"unitEnglishName": "Beta", "unitName": "乙"}]),
                      encoding="utf-8")
        dc = tmp_path / "details.json"
        dc.write_text(json.dumps([_rec("Alpha", "甲", [{"name": "技能"}]),
                                  _rec("Beta", "乙", [])]), encoding="utf-8")
        rep = audit(db, lc, dc)
        assert rep["total"] == 3
        assert sum(rep["counts"].values()) == 3
        assert rep["counts"]["zh_ok"] == 1
        assert rep["counts"]["zh_row_empty_abilities"] == 1
        assert rep["counts"]["absent_source_has_no_entry"] == 1
        assert set(rep["counts"]) == set(CATEGORIES)

    def test_source_entry_without_detail_is_not_blamed_on_missing_source(self, tmp_path):
        db = _mk_db(tmp_path, [("u1", "Kahl", "战群统领")])
        lc = tmp_path / "units.json"
        lc.write_text(json.dumps([{"unitEnglishName": "Kahl", "unitName": "战群统领"}]),
                      encoding="utf-8")
        dc = tmp_path / "details.json"
        dc.write_text(json.dumps([{"name_en": "Kahl", "name_zh": "战群统领",
                                   "detail": None}]), encoding="utf-8")
        rep = audit(db, lc, dc)
        assert rep["counts"]["absent_source_entry_without_detail"] == 1
        assert rep["counts"]["absent_source_has_no_entry"] == 0


@pytest.mark.skipif(not DB.exists() or not DETAILS_CACHE.exists(),
                    reason="需要真库与黑图缓存")
class TestRealCorpus:
    def test_reconciliation_is_exhaustive_on_real_db(self):
        rep = audit(DB, LIST_CACHE, DETAILS_CACHE)
        assert sum(rep["counts"].values()) == rep["total"]
        assert rep["total"] > 1700
        assert rep["counts"]["zh_ok"] > 1000
        assert "合计校验" in format_report(rep)

    def test_units_the_source_cannot_fill_have_no_invented_chinese_text(self):
        """补不到的单位在库里**不许**出现中文技能正文——防造数的机械门。

        分类为「中文层技能为空」的行，abilities_json 必须真的是空数组；分类为
        「源里没有/无正文」的行，unit_zh_detail 里必须根本没有这一行。
        """
        rep = audit(DB, LIST_CACHE, DETAILS_CACHE)
        conn = sqlite3.connect(str(DB))
        try:
            for u in rep["units"]:
                if u["category"] == "zh_row_empty_abilities":
                    raw = conn.execute(
                        "SELECT abilities_json FROM unit_zh_detail WHERE canonical_id=?",
                        (u["id"],)).fetchone()
                    assert json.loads(raw[0]) == [], u
                elif u["category"].startswith("absent_"):
                    assert conn.execute(
                        "SELECT COUNT(*) FROM unit_zh_detail WHERE canonical_id=?",
                        (u["id"],)).fetchone()[0] == 0, u
        finally:
            conn.close()

    def test_zh_name_bridge_survives_a_db_rebuild(self, tmp_path):
        """中文名桥的产物必须能从**已提交的代码 + 本地缓存**重跑出来。

        `db/wh40k.sqlite` 是 gitignored 的：库里有、代码里没有的东西，下次
        `db_compile build` 就会静默消失。这里在库的**副本**上重跑一次
        `populate_zh_details`（`build` 经 `update.restore_authority_layers` →
        `stage_zh_details` 走的就是这条），断言这六个只能靠中文名桥接上的单位
        重跑后仍在。真库一个字节都不动。

        名单来自 2026-07-27 的逐行核实（见 tests/test_web_api_ability_keywords.py
        顶部的 EXPECTED_ZH_ITEMS 注释）：它们的英文名与库内只差单复数或头衔前缀，
        `_en_to_ids` 一个都对不上，全靠 `_zh_to_ids` 一对一接。
        """
        expect = {
            "000003836": "Death Company Marines with Boltguns",
            "000000562": "Sentry Pylon",
            "000000121": "Uriel Ventris",
            "000000847": "Servitors",
            "000000397": "Servitors",
            "000003916": "Ynnari Kabalite Warriors",
        }
        import shutil
        copy = tmp_path / "repro.sqlite"
        shutil.copyfile(str(DB), str(copy))
        details = json.loads(DETAILS_CACHE.read_text(encoding="utf-8"))
        populate_zh_details(copy, details)
        conn = sqlite3.connect(str(copy))
        try:
            for cid, name_en in expect.items():
                row = conn.execute(
                    "SELECT name_zh FROM unit_zh_detail WHERE canonical_id=?",
                    (cid,)).fetchone()
                assert row and row[0], "重建后丢了中文层：{} {}".format(cid, name_en)
                # 英文名确实对不上 ⇒ 这一行只可能来自中文名桥，桥断了这里就红
                en = conn.execute("SELECT name_en FROM units WHERE id=?",
                                  (cid,)).fetchone()
                assert en and en[0] == name_en, (cid, en)
        finally:
            conn.close()

    def test_every_stored_ability_text_exists_verbatim_in_the_source_cache(self):
        """库里每条中文技能名都必须能在黑图缓存里逐字找到（抽 200 行对账）。

        这是造数的反向门：只要有一条中文正文不是从源里搬来的，这里就红。
        """
        src = json.loads(DETAILS_CACHE.read_text(encoding="utf-8"))
        src_names = set()
        for r in src:
            for a in ((r.get("detail") or {}).get("能力") or []):
                if isinstance(a, dict) and a.get("name"):
                    src_names.add(a["name"])
        conn = sqlite3.connect(str(DB))
        rows = conn.execute(
            "SELECT canonical_id, abilities_json FROM unit_zh_detail "
            "WHERE abilities_json NOT IN ('[]','null','') LIMIT 200").fetchall()
        conn.close()
        assert rows
        for cid, raw in rows:
            for a in json.loads(raw):
                if isinstance(a, dict) and a.get("name"):
                    assert a["name"] in src_names, (cid, a["name"])
