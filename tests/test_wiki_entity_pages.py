"""tests/test_wiki_entity_pages.py — 分队 / 战略 / 增强三类实体页渲染。

守的是三件在这个项目里反复出事的东西：
  ① 0 是真值：0 CP 的战略、0 分的增强都存在，不能当"空值"跳过
  ② 拆不出标准段时**原样保留 + 标注**，不许硬切（切错等于改规则）
  ③ 分队「容器名」≠「规则名」，缺列时必须报错而不是按 id 邻接猜
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from wiki_engine.entity_pages import (generate_all, has_column, load_payload_names,
                                      render_detachment, render_enhancement,
                                      render_stratagem)

ZH: dict = {}


def _rows(sql: str, values):
    """把字面值做成 sqlite3.Row（渲染函数按列名取值）。"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(sql)
    cols = [d[1] for d in conn.execute("PRAGMA table_info(t)")]
    conn.execute("INSERT INTO t ({}) VALUES ({})".format(
        ",".join(cols), ",".join("?" * len(cols))), values)
    return conn.execute("SELECT * FROM t").fetchone()


_STRAT_T = ("CREATE TABLE t (id TEXT, faction TEXT, detachment TEXT, name_zh TEXT, "
            "name_en TEXT, cp_cost TEXT, phase TEXT, text_zh TEXT, type TEXT)")
_ENH_T = ("CREATE TABLE t (id TEXT, faction_id TEXT, detachment_name TEXT, "
          "name TEXT, cost INTEGER, description TEXT)")
_DET_T = ("CREATE TABLE t (id TEXT, faction TEXT, name_zh TEXT, name_en TEXT, "
          "rule_text TEXT, detachment_name TEXT)")


# ── 战略 ──────────────────────────────────────────────────────────

def test_stratagem_sections_and_frontmatter():
    row = _rows(_STRAT_T, ("000009", "SM", "Gladius Task Force", None, "ARMOUR OF CONTEMPT",
                           "1", "Any phase", "<b>WHEN:</b> a<br><b>TARGET:</b> b<br>"
                           "<b>EFFECT:</b> c<br><b>RESTRICTIONS:</b> d", "Battle Tactic"))
    page, warns = render_stratagem(row, "星际战士", ZH)
    assert page.fm.type == "stratagem" and page.fm.cp == 1
    assert page.fm.detachment == "Gladius Task Force"
    assert page.fm.phase == "Any phase"
    for title in ("使用时机", "使用对象", "效果", "限制"):
        assert "## {}".format(title) in page.body
    assert not warns


def test_stratagem_zero_cp_is_a_real_value():
    """0 CP 战略存在。当成空值跳过，页面会显示成「CP 未知」——那是撒谎。"""
    row = _rows(_STRAT_T, ("1", "SM", "D", None, "FREEBIE", "0", "",
                           "<b>WHEN:</b> a<br><b>TARGET:</b> b<br><b>EFFECT:</b> c", ""))
    page, _ = render_stratagem(row, "星际战士", ZH)
    assert page.fm.cp == 0
    assert "cp: 0" in page.fm.to_yaml_text()
    assert page.body.startswith("0 CP")


def test_stratagem_unknown_cp_is_not_zero():
    row = _rows(_STRAT_T, ("1", "SM", "D", None, "X", "", "",
                           "<b>WHEN:</b> a<br><b>TARGET:</b> b<br><b>EFFECT:</b> c", ""))
    page, _ = render_stratagem(row, "星际战士", ZH)
    assert page.fm.cp is None
    assert "CP 未知" in page.body


def test_stratagem_unparseable_text_is_kept_verbatim():
    """没有标准段的战略：原样保留 + 显式标注，绝不硬切。"""
    row = _rows(_STRAT_T, ("1", "AE", "D", None, "ODD ONE", "1", "",
                           "Just prose, no labels at all.", ""))
    page, warns = render_stratagem(row, "艾达灵族", ZH)
    assert "## 原文（未识别出标准段落）" in page.body
    assert "Just prose, no labels at all." in page.body
    assert any("未识别" in w for w in warns)


def test_stratagem_type_drops_detachment_prefix():
    row = _rows(_STRAT_T, ("1", "AdM", "Eradication Cohort", None, "X", "1", "",
                           "<b>WHEN:</b> a<br><b>TARGET:</b> b<br><b>EFFECT:</b> c",
                           "Eradication Cohort – Wargear Stratagem"))
    page, _ = render_stratagem(row, "机械修会", ZH)
    assert page.fm.stratagem_type == "Eradication Cohort – Wargear Stratagem"
    assert "Wargear Stratagem" in page.body.splitlines()[0]


# ── 增强 ──────────────────────────────────────────────────────────

def test_enhancement_lifts_only_clause_into_limit_section():
    row = _rows(_ENH_T, ("2", "AC", "Black Ship Guardians", "The Vratine Aquila", 25,
                         "ANATHEMA PSYKANA model only. While a friendly unit is within 3\", "
                         "models in that unit have a 4+ invulnerable save."))
    page, _ = render_enhancement(row, "帝皇卫队", ZH)
    assert page.fm.cost == 25
    assert "## 携带限制" in page.body
    assert "ANATHEMA PSYKANA model only." in page.body.split("## 携带限制")[1]
    assert "**分数**：25 分" in page.body


def test_enhancement_without_limit_says_so_honestly():
    row = _rows(_ENH_T, ("3", "AC", "D", "Plain", 10, "Add 1 to something."))
    page, _ = render_enhancement(row, "帝皇卫队", ZH)
    assert "（源文本未提供）" in page.body.split("## 携带限制")[1]


def test_enhancement_zero_cost_is_real():
    row = _rows(_ENH_T, ("4", "AC", "D", "Free", 0, "x"))
    page, _ = render_enhancement(row, "帝皇卫队", ZH)
    assert page.fm.cost == 0
    assert "cost: 0" in page.fm.to_yaml_text()


# ── 分队 ──────────────────────────────────────────────────────────

def test_detachment_lists_children_and_rule():
    rule = _rows(_DET_T, ("000008370", "NEC", "指令协议", "Command Protocols",
                          "In your Command phase, do a thing.", "Awakened Dynasty"))
    page, warns = render_detachment(
        "Awakened Dynasty", "太空死灵", [rule],
        [("factions/太空死灵/enhancements/x.md", "增强甲")],
        [("factions/太空死灵/stratagems/y.md", "战略乙")],
        ZH, "000008370")
    assert page.fm.type == "detachment"
    assert page.fm.detachment == "Awakened Dynasty"
    assert page.fm.name_en == "Awakened Dynasty"          # 页名是容器名，不是规则名
    assert "Command Protocols" in page.body               # 规则名出现在正文里
    assert "[[factions/太空死灵/enhancements/x.md\\|增强甲]]" in page.body
    assert "[[factions/太空死灵/stratagems/y.md\\|战略乙]]" in page.body
    assert not warns


def test_detachment_without_rule_is_flagged_not_faked():
    page, warns = render_detachment("Orphan Container", "兽人", [], [], [], ZH, "x")
    assert "（源文本未提供）" in page.body
    assert any("无绑定" in w for w in warns)
    assert "（本分队在结构库中无增强条目）" in page.body


# ── 缺列必须报错 ──────────────────────────────────────────────────

def test_generate_requires_container_column(tmp_path):
    """缺 detachment_name 列时必须抛错。按 id 邻接反推实测会认错分队规则。"""
    db = tmp_path / "t.sqlite"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE detachments (id TEXT, faction TEXT, name_zh TEXT, "
                 "name_en TEXT, rule_text TEXT)")
    conn.execute("CREATE TABLE stratagems (id TEXT, faction TEXT, detachment TEXT, "
                 "name_zh TEXT, name_en TEXT, cp_cost TEXT, phase TEXT, text_zh TEXT)")
    conn.execute("CREATE TABLE enhancements (id TEXT, faction_id TEXT, "
                 "detachment_name TEXT, name TEXT, cost INTEGER, description TEXT)")
    conn.commit()
    assert not has_column(conn, "detachments", "detachment_name")
    conn.close()
    with pytest.raises(RuntimeError, match="detachment_name"):
        generate_all(db, tmp_path / "wiki")


# ── 译名来源 ──────────────────────────────────────────────────────

def test_payload_names_cover_enhancements():
    """增强中文名在库里是 0/1058，唯一来源就是 P7 载荷——这条断言是它的守卫。"""
    names = load_payload_names(Path("dsl_payloads"))
    assert names.get("enhancements"), "载荷里没有增强译名，增强页会全英文"
    assert len(names["enhancements"]) >= 300
    assert len(names.get("stratagems", {})) >= 600


def test_detachment_with_two_rules_lists_both():
    """同一阵营内同名容器可挂两条规则（混沌恶魔 Daemonic Incursion 实例）。
    取第一条会静默丢掉一条真规则。"""
    r1 = _rows(_DET_T, ("000008436", "CD", None, "Warp Rifts", "rule one text",
                        "Daemonic Incursion"))
    r2 = _rows(_DET_T, ("000009546", "CD", None, "Unnatural Energies", "rule two text",
                        "Daemonic Incursion"))
    page, warns = render_detachment("Daemonic Incursion", "混沌恶魔", [r1, r2],
                                    [], [], ZH, "000008436")
    assert "Warp Rifts" in page.body and "Unnatural Energies" in page.body
    assert "rule one text" in page.body and "rule two text" in page.body
    assert any("2 条分队规则" in w for w in warns)
