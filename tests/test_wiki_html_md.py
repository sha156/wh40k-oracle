"""tests/test_wiki_html_md.py — 官方 HTML 片段 → wiki markdown。

这层是「分队/战略/增强」三类实体页的公共地基。它的失败模式不是崩溃，而是
**输出一段读着通顺、意思却变了的规则**——所以用例重点全在"不许静默丢东西"：
骰面图标、表格、相邻关键词合并、拆不出段时不硬切。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from wiki_engine.html_md import html_to_markdown, split_stratagem

DB = Path(__file__).resolve().parent.parent / "db" / "wh40k.sqlite"
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")


# ── 不许静默丢内容 ─────────────────────────────────────────────────

def test_dice_icon_becomes_digit():
    """<img d1.png> 是骰面。丢了它，「结果为 1-2 时」会变成「结果为 时」。"""
    md, warns = html_to_markdown(
        'On a roll of <img src="/wh40k10ed/img/d1.png"> or '
        '<img src="/wh40k10ed/img/d2.png">, nothing happens.')
    assert md == "On a roll of 1 or 2, nothing happens."
    assert not warns


def test_non_dice_image_is_reported_not_swallowed():
    md, warns = html_to_markdown('see <img src="/img/logo.png"> here')
    assert "logo.png" in warns[0]


def test_unknown_tag_is_reported():
    md, warns = html_to_markdown("<blink>x</blink>")
    assert any("blink" in w for w in warns)


# ── 表格 ──────────────────────────────────────────────────────────

def test_table_becomes_markdown_with_empty_header():
    """全库 404 个 td、0 个 th——这些表没有表头。把首行提成表头＝凭空造语义。"""
    md, _ = html_to_markdown(
        "<table><tr><td>1</td><td>甲</td></tr><tr><td>2</td><td>乙</td></tr></table>")
    lines = [l for l in md.splitlines() if l.strip()]
    # 空表头（收尾会把连续空格压成一个，故是 "| | |" 而非 "|  |  |"）——不撒谎胜过好看
    assert lines[0] == "| | |"
    assert lines[1] == "|---|---|"
    assert lines[2] == "| 1 | 甲 |"
    assert lines[3] == "| 2 | 乙 |"


def test_table_with_th_keeps_first_row_as_header():
    md, _ = html_to_markdown(
        "<table><tr><th>档位</th><th>数量</th></tr><tr><td>突袭</td><td>1</td></tr></table>")
    lines = [l for l in md.splitlines() if l.strip()]
    assert lines[0] == "| 档位 | 数量 |"
    assert lines[2] == "| 突袭 | 1 |"


def test_layout_table_is_passed_through():
    """Wahapedia 档位表常套两层，外层只有一个单元格。包一层会渲染出 1×1 空壳表。"""
    md, _ = html_to_markdown(
        "<table><tr><td><table><tr><td>A</td><td>B</td></tr></table></td></tr></table>")
    assert "| A | B |" in md
    assert md.count("|---|") == 1          # 只有内层那张表


def test_pipe_in_cell_is_escaped():
    """竖线不转义会把表格切出多余的列。"""
    md, _ = html_to_markdown("<table><tr><td>a|b</td><td>c</td></tr></table>")
    assert "| a\\|b | c |" in md


# ── 关键词 ────────────────────────────────────────────────────────

def test_adjacent_keyword_spans_merge():
    """<span kwb>ADEPTUS</span> <span kwb>CUSTODES</span> 是一个关键词，不是两个。"""
    md, _ = html_to_markdown(
        'friendly <span class="kwb">ADEPTUS</span> <span class="kwb">CUSTODES</span> units')
    assert "ADEPTUS CUSTODES" in md


def test_known_keyword_becomes_bare_link_unknown_stays_text():
    """认得的才做裸链交给 crosslinks；认不得的留纯文本——红链是 lint error 不是 TODO。"""
    md, _ = html_to_markdown('<span class="kwb">BLAST</span> weapons')
    assert "[[BLAST]]" in md
    md2, _ = html_to_markdown('<span class="kwb">ADEPTUS CUSTODES</span> units')
    assert "[[" not in md2


def test_kwbu_variants_are_keywords_too():
    md, _ = html_to_markdown('<span class="tt kwbu">BLAST</span>')
    assert "[[BLAST]]" in md


# ── 行内与列表 ────────────────────────────────────────────────────

def test_bold_italic_lists():
    md, _ = html_to_markdown("<b>甲</b> 与 <i>乙</i><ul><li>一</li><li>二</li></ul>")
    assert "**甲**" in md and "*乙*" in md
    assert "- 一" in md and "- 二" in md


def test_ordered_list_numbers():
    md, _ = html_to_markdown("<ol><li>甲</li><li>乙</li></ol>")
    assert "1. 甲" in md and "2. 乙" in md


def test_empty_input():
    assert html_to_markdown(None) == ("", [])
    assert html_to_markdown("   ") == ("", [])


# ── 战略分段 ──────────────────────────────────────────────────────

def test_split_standard_three_sections():
    secs, order, warns = split_stratagem(
        "<b>WHEN:</b> Your Shooting phase.<br><br>"
        "<b>TARGET:</b> One unit.<br><br>"
        "<b>EFFECT:</b> It shoots twice.")
    assert order == ["使用时机", "使用对象", "效果"]
    assert secs["使用时机"] == "Your Shooting phase."
    assert secs["效果"] == "It shoots twice."
    assert not warns


def test_split_with_restrictions():
    """RESTRICTIONS 实测 133 条，是正式第四段不是附注。"""
    secs, order, _ = split_stratagem(
        "<b>WHEN:</b> a<br><b>TARGET:</b> b<br><b>EFFECT:</b> c<br>"
        "<b>RESTRICTIONS:</b> once per battle")
    assert order[-1] == "限制"
    assert secs["限制"] == "once per battle"


def test_split_trigger_variant():
    """6 条灵族战略用 TRIGGER 而不是 WHEN，语义同段。"""
    secs, order, _ = split_stratagem(
        '<span class="aeText">TRIGGER:</span> When charged.<br>'
        '<b>TARGET:</b> x<br><b>EFFECT:</b> y')
    assert order[0] == "使用时机"
    assert secs["使用时机"] == "When charged."


def test_split_without_bold_tags():
    """AoI / TYR 各有一条段标签没加 <b>，同样要认。"""
    secs, order, _ = split_stratagem(
        "WHEN: Your Movement phase.<br><br>TARGET: One unit.<br><br>EFFECT: It moves.")
    assert order == ["使用时机", "使用对象", "效果"]


def test_split_returns_empty_when_no_sections():
    """拆不出标准段时返回空 dict，让调用方原样保留整段——硬切等于改规则。"""
    secs, order, warns = split_stratagem("Just some prose without labels.")
    assert secs == {} and order == []
    assert any("未识别" in w for w in warns)


def test_split_keeps_stray_lead_text():
    secs, order, warns = split_stratagem(
        "Some preamble.<br><b>WHEN:</b> now<br><b>TARGET:</b> x<br><b>EFFECT:</b> y")
    assert "Some preamble." in secs["使用时机"]
    assert any("游离文本" in w for w in warns)


# ── 真库全量冒烟 ──────────────────────────────────────────────────

@needs_db
def test_all_stratagems_convert_without_exception():
    """1682 条全过一遍：不许有崩溃，也不许有大面积拆不出段。"""
    conn = sqlite3.connect(str(DB))
    rows = conn.execute("SELECT id, text_zh FROM stratagems").fetchall()
    conn.close()
    parsed = 0
    empty = 0
    for _sid, raw in rows:
        secs, _order, _w = split_stratagem(raw)
        if secs:
            parsed += 1
        elif not (raw or "").strip():
            empty += 1
    # 实测 1673/1682 三段齐全；余下是 6 条灵族图标式 + 2 条无 <b> + 1 条垃圾行，
    # 前两类本模块已能认，所以真正拆不出的应当极少
    assert parsed >= len(rows) - 5, "拆不出段的战略过多：{}".format(len(rows) - parsed - empty)


@needs_db
def test_all_detachment_rules_convert_without_exception():
    conn = sqlite3.connect(str(DB))
    rows = conn.execute("SELECT id, rule_text FROM detachments").fetchall()
    conn.close()
    bad = []
    for did, raw in rows:
        md, warns = html_to_markdown(raw)
        if any("解析失败" in w for w in warns):
            bad.append(did)
    assert not bad, "HTML 解析崩溃：{}".format(bad[:5])
