"""tests/test_db_official_zh_apply.py — 官方中文名映射 → 库（投影层）。

守的是落库那三个实测坑：
  ① 分队容器名只能走独立表：挂到 detachments 行上会静默丢掉 60/123
  ② enhancements 表原本没有 name_zh 列，得先 ALTER（旧库也要能跑）
  ③ 同一英文名在不同包里有不同官方译名——行级映射必须压过名级，
     否则这几条要么落错译名，要么整条丢
外加一条纪律：写完当场回查，应写数 ≠ 读回数就炸，不许报「已完成」。
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from db_compile.official_zh import OUT_PATH
from db_compile.official_zh_apply import (MAP_PATH, apply_official_zh, coverage,
                                          load_detachment_names_zh, load_mapping)
from db_compile.schema import ALL_DDL

DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")
needs_map = pytest.mark.skipif(not OUT_PATH.exists(),
                               reason="需要 db_compile/official_zh_names.json")


# ── 造一个小库 ────────────────────────────────────────────────────

def _db(tmp_path: Path, *, enh_name_zh_column: bool = True) -> Path:
    db = tmp_path / "t.sqlite"
    conn = sqlite3.connect(str(db))
    for ddl in ALL_DDL:
        if enh_name_zh_column or "enhancements" not in ddl:
            conn.execute(ddl)
    if not enh_name_zh_column:
        # 旧库形态：没有 name_zh 列
        conn.execute("CREATE TABLE enhancements (id TEXT PRIMARY KEY, faction_id TEXT,"
                     " detachment_id TEXT, detachment_name TEXT, name TEXT,"
                     " cost INTEGER, legend TEXT, description TEXT)")
    conn.executemany(
        "INSERT INTO stratagems (id, faction, detachment, name_zh, name_en) "
        "VALUES (?, ?, ?, ?, ?)",
        [("s1", "SM", "Gladius Task Force", None, "ARMOUR OF CONTEMPT"),
         ("s2", "SM", "Lion’s Blade Task Force", "旧人工译名", "ARMOUR OF CONTEMPT"),
         ("s3", "SM", "Gladius Task Force", None, "ONLY IN DEATH")])
    conn.executemany(
        "INSERT INTO enhancements (id, faction_id, detachment_name, name, cost) "
        "VALUES (?, ?, ?, ?, ?)",
        [("e1", "AE", "Windrider Host", "Archraider", 20),
         ("e2", "DRU", "Realspace Raid", "Archraider", 25)])
    conn.commit()
    conn.close()
    return db


def _map(tmp_path: Path, **over) -> Path:
    data = {
        "stratagems": {"ONLY IN DEATH": "唯死方休"},          # 名级：无冲突的那批
        "stratagems_by_id": {"s1": "蔑视甲胄", "s2": "蔑视战甲"},   # 行级：同名不同译
        "enhancements": {},
        "enhancements_by_id": {"e1": "大劫掠者", "e2": "至尊掠夺者"},
        "detachments": {"Gladius Task Force": "剑刃特遣队",
                        "Windrider Host": "风行者军团"},
    }
    data.update(over)
    path = tmp_path / "m.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def _names(db: Path, table: str, col: str = "name_zh"):
    conn = sqlite3.connect(str(db))
    try:
        return dict(conn.execute("SELECT id, {} FROM {}".format(col, table)))
    finally:
        conn.close()


# ── 行级压过名级（坑 ③）────────────────────────────────────────────

def test_row_level_beats_name_level_for_same_english_name(tmp_path):
    """同一英文名两个官方译名：按行各认各的，谁也不丢。

    这正是名级映射表达不了、只能整条丢弃的那类——落库以行级为准才接得住。
    """
    db = _db(tmp_path)
    apply_official_zh(db, map_path=_map(tmp_path))
    got = _names(db, "stratagems")
    assert got["s1"] == "蔑视甲胄"
    assert got["s2"] == "蔑视战甲"       # 顶掉了「旧人工译名」


def test_name_level_fills_rows_the_pairing_missed(tmp_path):
    """本行没配上、但同名条目在别处配上了——按英文名兜底。"""
    db = _db(tmp_path)
    rep = apply_official_zh(db, map_path=_map(tmp_path))
    assert _names(db, "stratagems")["s3"] == "唯死方休"
    assert rep["stratagems"]["by_id"] == 2 and rep["stratagems"]["by_name"] == 1


def test_superseded_old_names_are_reported_not_swallowed(tmp_path):
    db = _db(tmp_path)
    rep = apply_official_zh(db, map_path=_map(tmp_path))
    assert rep["stratagems"]["superseded_total"] == 1
    assert rep["stratagems"]["superseded"][0]["old"] == "旧人工译名"
    assert rep["stratagems"]["superseded"][0]["new"] == "蔑视战甲"


# ── 补结构（坑 ②）─────────────────────────────────────────────────

def test_old_db_without_name_zh_column_gets_altered(tmp_path):
    db = _db(tmp_path, enh_name_zh_column=False)
    rep = apply_official_zh(db, map_path=_map(tmp_path))
    assert "enhancements.name_zh" in rep["schema_added"]
    assert _names(db, "enhancements") == {"e1": "大劫掠者", "e2": "至尊掠夺者"}


def test_dry_run_writes_nothing_including_schema(tmp_path):
    """sqlite 的 DDL 不吃 rollback：dry-run 要是顺手 ALTER 了，就再也 dry 不回去了。"""
    db = _db(tmp_path, enh_name_zh_column=False)
    rep = apply_official_zh(db, map_path=_map(tmp_path), dry_run=True)
    assert rep["dry_run"] and rep["schema_pending"] == ["enhancements.name_zh"]
    assert rep["stratagems"]["targeted"] == 3        # 该写多少照样算得出来
    conn = sqlite3.connect(str(db))
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(enhancements)")}
        assert "name_zh" not in cols
        assert dict(conn.execute("SELECT id, name_zh FROM stratagems")) == {
            "s1": None, "s2": "旧人工译名", "s3": None}      # 一个字都没动
    finally:
        conn.close()


# ── 分队容器名走独立表（坑 ①）──────────────────────────────────────

def test_container_names_land_in_their_own_table(tmp_path):
    db = _db(tmp_path)
    apply_official_zh(db, map_path=_map(tmp_path))
    assert load_detachment_names_zh(db) == {"Gladius Task Force": "剑刃特遣队",
                                            "Windrider Host": "风行者军团"}
    conn = sqlite3.connect(str(db))
    try:
        # detachments.name_zh 存的是**分队规则名**的中文，不许被容器名污染
        assert not conn.execute("SELECT COUNT(*) FROM detachments").fetchone()[0]
    finally:
        conn.close()


def test_container_table_is_rebuilt_not_appended(tmp_path):
    """映射是这一层唯一真源：上一轮多出来的行留着就成了没人发现的幽灵译名。"""
    db = _db(tmp_path)
    apply_official_zh(db, map_path=_map(tmp_path))
    apply_official_zh(db, map_path=_map(
        tmp_path, detachments={"Gladius Task Force": "剑刃特遣队"}))
    assert load_detachment_names_zh(db) == {"Gladius Task Force": "剑刃特遣队"}


def test_unknown_container_names_are_reported(tmp_path):
    db = _db(tmp_path)
    rep = apply_official_zh(db, map_path=_map(
        tmp_path, detachments={"No Such Detachment": "查无此队"}))
    assert rep["detachments"]["orphans"] == ["No Such Detachment"]


# ── 幂等 + 对账 ───────────────────────────────────────────────────

def test_second_run_changes_nothing_and_says_so(tmp_path):
    db = _db(tmp_path)
    apply_official_zh(db, map_path=_map(tmp_path))
    rep = apply_official_zh(db, map_path=_map(tmp_path))
    assert rep["stratagems"]["superseded_total"] == 0
    assert rep["stratagems"]["already"] == rep["stratagems"]["targeted"]
    assert rep["verified"]["stratagems"] == rep["stratagems"]["targeted"]


def test_ids_missing_from_db_are_reported(tmp_path):
    """映射指向库里不存在的行＝库换过一轮 id。不报出来就只是「命中悄悄变少」。"""
    db = _db(tmp_path)
    rep = apply_official_zh(db, map_path=_map(
        tmp_path, stratagems_by_id={"s1": "蔑视甲胄", "ghost": "幽灵"}))
    assert rep["missing_ids_total"]["stratagems"] == 1
    assert rep["missing_ids"]["stratagems"] == ["ghost"]


# ── 映射文件本身的守卫 ────────────────────────────────────────────

def test_missing_section_raises_instead_of_landing_less(tmp_path):
    db = _db(tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"stratagems": {}}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="缺顶层键"):
        apply_official_zh(db, map_path=bad)


def test_invisible_characters_are_rejected_loudly(tmp_path):
    """零宽空格进了名字，按名字 join 会静默配不上，而报错信息里两串看着一模一样。"""
    path = _map(tmp_path, detachments={"Gladius Task Force": "剑刃​特遣队"})
    with pytest.raises(RuntimeError, match="不可见字符"):
        load_mapping(path)


def test_empty_value_is_rejected(tmp_path):
    path = _map(tmp_path, stratagems={"ONLY IN DEATH": "  "})
    with pytest.raises(RuntimeError, match="空键/空值"):
        load_mapping(path)


# ── 真库 / 真产物不变量 ───────────────────────────────────────────

@needs_map
def test_real_mapping_loads_clean():
    data = load_mapping(MAP_PATH)
    assert len(data["stratagems_by_id"]) >= 450
    assert len(data["enhancements_by_id"]) >= 200
    assert len(data["detachments"]) >= 100


@needs_db
@needs_map
def test_real_db_carries_the_official_layer():
    """库里必须已经叠了官方中文层——地板设在实测值下方当哨兵。

    覆盖率掉下地板 = 某一步把这层洗掉了（`enhancements --apply` 的 INSERT OR REPLACE
    就会），页面会悄悄退回英文/旧译名，不设哨兵没人会发现。
    """
    cov = coverage(DB)
    assert cov["stratagems"][0] >= 700, cov
    assert cov["enhancements"][0] >= 240, cov
    assert cov["detachments"][0] >= 100, cov
    zh = load_detachment_names_zh(DB)
    assert zh.get("Abhuman Auxiliaries") == "亚人类辅助军"
