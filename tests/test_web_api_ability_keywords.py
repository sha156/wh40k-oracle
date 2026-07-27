"""tests/test_web_api_ability_keywords.py — 兵牌**技能正文**里内嵌词条的切段层。

武器行的 USR 已经能逐条悬停（见 test_web_api_keyword_refs.py），这一份管的是另一处：
技能正文里的 `【致命一击】` / `[LETHAL HITS]` / `<span class="kwb">…</span>`。

同样用**真实库**测。这一层最大的风险不是"切不出词条"（页面上看得见），
而是两件看不见的事：

  ① **切段切丢了字**——`text` 与各段拼接不一致时，页面只是少了半句话，不报错。
     所以全库逐条对账拼接等式，不抽查。
  ② **给了一个查不到真源的空壳词条段**——那等于把 VEHICLE / ASTARTES 这类阵营
     关键词说成规则词条，点开却没有解释。判据只有一条：能不能在词条真源里查到。
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from web_api.contract import AbilityKwSpan, AbilityTextSpan
from web_api.entity_card import _ability
from web_api.keyword_refs import ability_spans

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "db" / "wh40k.sqlite"
PAYLOAD = REPO_ROOT / "wiki" / "indexes" / "keywords.json"
SECTIONS = REPO_ROOT / "wiki" / "core-rules" / "sections"

needs_assets = pytest.mark.skipif(
    not (DB_PATH.exists() and PAYLOAD.exists() and SECTIONS.is_dir()),
    reason="需要 db/wh40k.sqlite + wiki/indexes/keywords.json + wiki/core-rules/sections/")

# 实测口径（2026-07-27 黑图书馆缓存刷新后）。数字变了先确认是换库/换版，
# 别顺手对齐成"测试通过"。本次 3267→3280 / 190→188 的来源已逐条核实：
# 缓存从 2026-07-08 刷到 2026-07-27，源侧新增 2 条记录 + 43 条技能正文被官方改写
# （无视掩体 10→9、毁灭伤害 11→10、光环 5→6、隐蔽 2→1），四个词条全部仍能 resolve，
# 不是解析退化。
#
# 2026-07-27（本轮）3280→3296（+16 条目）：来源是 unit_zh_detail 1129→1135（+6 行），
# 已逐行核实是**合法数据增长**而非污染——这 6 行全部由 `populate_zh_details` 的
# **中文名桥**（英文名只差单复数/头衔前缀时靠中文名一对一接）灌入：
#   Death Company Marine(s) With Boltguns 3 + Sentry Pylon(s) 4 + Uriel Ventris 3
#   + Servitor(s) ×2 行 2+2 + Ynnari Kabalite Warriors 2  = 16 条目，与 +16 自洽。
# 桥当前共接 8 行 21 条目，另 2 行（克拉维克·莫恩 3 + 装备重型武器的天灾 2 = 5）
# 在上一轮就已入库（HEAD 的 wiki 页里能查到这两个中文名，其余 6 个查不到）。
# units 无中文层 586→580、空 abilities_json 仍是 16（没有新增空行），三个数自洽。
# 复现路径与钉死用例见 tests/test_db_compile_zh_coverage.py::TestZhNameBridgeIsReproducible。
EXPECTED_ZH_ITEMS = 3296        # unit_zh_detail 里的技能条目总数
EXPECTED_ZH_KW_SPANS = 188      # 其中切出的词条段（中文【】写法）
EXPECTED_EN_ROWS = 4009         # abilities 表行数
EXPECTED_EN_KW_SPANS = 443      # 其中切出的词条段（英文 [] 写法；kwb 里全是阵营关键词，
                                # 一条都不该在这里）


def _spans(raw_html: str):
    return _ability(None, "x", raw_html).rich


def _joined(ability) -> str:
    return "".join(s.s if isinstance(s, AbilityTextSpan) else s.kw.text
                   for s in ability.rich)


# ── 用户点名的那一条 ─────────────────────────────────────────────────

@needs_assets
def test_conscript_squad_imperial_law_has_two_live_keywords() -> None:
    """强征小队「帝国法律」正文里的【致命一击】【精准】要能查到官方解释。

    这条是用户原话点名的效果，也是「技能正文 ≠ 武器行」这件事的唯一样本级证据。
    """
    from web_api import codex

    card = codex.unit_card(DB_PATH, "000002685", lang="zh")
    assert card is not None
    law = next(a for a in card.abilities if a.name == "帝国法律")
    kws = [s.kw for s in law.rich if isinstance(s, AbilityKwSpan)]
    assert [k.text for k in kws] == ["【致命一击】", "【精准】"]
    assert [k.slug for k in kws] == ["lethal-hits", "precision"]
    assert [k.section for k in kws] == ["24.23", "24.28"]
    assert all(k.rule_slug == "24-core-abilities" for k in kws)
    # 解释是官方中文正文的逐字摘录，不是我们写的概括
    assert "如果攻击造成暴击命中，那么您可以选择让那次攻击自动致伤目标" in (kws[0].brief or "")
    # 正文一个字都没丢
    assert _joined(law) == law.text
    assert law.text and law.text.startswith("在战斗开始时，选择您对手军队中的一个单位。")


# ── 三种写法 ─────────────────────────────────────────────────────────

@needs_assets
def test_all_three_markups_are_recognised() -> None:
    """中文【】、英文 []、HTML kwb —— 三种写法都要认，判据统一是"查不查得到"。"""
    zh = _spans("<p>该攻击拥有【致命一击】和【速射 2】技能。</p>")
    assert [s.kw.slug for s in zh if isinstance(s, AbilityKwSpan)] == [
        "lethal-hits", "rapid-fire"]
    assert [s.kw.text for s in zh if isinstance(s, AbilityKwSpan)] == [
        "【致命一击】", "【速射 2】"]

    en = _spans("that attack has the [LETHAL HITS] and [SUSTAINED HITS 1] abilities.")
    assert [s.kw.slug for s in en if isinstance(s, AbilityKwSpan)] == [
        "lethal-hits", "sustained-hits"]

    kwb = _spans('weapons have the <span class="kwb">PRECISION</span> ability.')
    hit = [s.kw for s in kwb if isinstance(s, AbilityKwSpan)]
    assert [k.slug for k in hit] == ["precision"]
    # kwb 的标签整个剥掉，显示串里**不该**多出方括号
    assert hit[0].text == "PRECISION"
    assert _joined(_ability(None, "x", 'weapons have the <span class="kwb">PRECISION</span> ability.')) == (
        "weapons have the PRECISION ability.")


@needs_assets
def test_faction_keywords_in_kwb_stay_plain_text() -> None:
    """kwb 里装的绝大多数是阵营关键词（VEHICLE / ASTARTES），它们不是规则词条。

    给它们套一个可点的词条段，就是把"查不到解释"伪装成功能。
    """
    spans = _spans('If your Army Faction is <span class="kwb">HERETIC</span> '
                   '<span class="kwb">ASTARTES</span>, this unit …')
    assert all(isinstance(s, AbilityTextSpan) for s in spans)
    assert spans[0].s == "If your Army Faction is HERETIC ASTARTES, this unit …"


@needs_assets
def test_bracketed_prose_is_not_mistaken_for_a_keyword() -> None:
    """方括号里不是词条的东西一律退回纯文本，绝不硬认。"""
    for raw in ("see [1] below", "[这不是一个词条]", "[a very long sentence, with commas]"):
        spans = _spans(raw)
        assert all(isinstance(s, AbilityTextSpan) for s in spans), raw
        assert "".join(s.s for s in spans) == raw, raw


# ── 全库对账 ──────────────────────────────────────────────────────────

@needs_assets
def test_whole_library_spans_lose_no_text_and_have_no_hollow_keywords() -> None:
    """全库技能正文逐条切段，报绝对数字。

    两条硬断言：拼接等式（切丢字页面上看不出来）、词条段必须带 slug（空壳段
    = 把查不到解释伪装成功能）。
    """
    conn = sqlite3.connect(str(DB_PATH))
    try:
        zh_items = []
        for (aj,) in conn.execute("SELECT abilities_json FROM unit_zh_detail"):
            try:
                items = json.loads(aj or "[]") or []
            except (json.JSONDecodeError, TypeError):
                continue
            zh_items += [it for it in items if isinstance(it, dict)]
        en_rows = [t for (t,) in conn.execute("SELECT text_zh FROM abilities")]
    finally:
        conn.close()

    assert len(zh_items) == EXPECTED_ZH_ITEMS
    assert len(en_rows) == EXPECTED_EN_ROWS

    zh_kw = en_kw = 0
    for it in zh_items:
        ab = _ability(None, "x", it.get("contentHtml"))
        assert _joined(ab) == (ab.text or "")
        for s in ab.rich:
            if isinstance(s, AbilityKwSpan):
                zh_kw += 1
                assert s.kw.slug and s.kw.base, s.kw.text
    for raw in en_rows:
        ab = _ability(None, "x", raw)
        assert _joined(ab) == (ab.text or "")
        for s in ab.rich:
            if isinstance(s, AbilityKwSpan):
                en_kw += 1
                assert s.kw.slug and s.kw.base, s.kw.text

    assert (zh_kw, en_kw) == (EXPECTED_ZH_KW_SPANS, EXPECTED_EN_KW_SPANS)


@needs_assets
def test_ability_without_text_gets_no_spans() -> None:
    """没有正文的技能：rich 为空，不塞一个空段（空段在前端会画出一个多余的冒号）。"""
    ab = _ability("阵营技能", "派遣特工", "")
    assert ab.text is None and ab.rich == []
