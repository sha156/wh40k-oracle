"""tests/test_wiki_keyword_index.py — 武器词条（USR）索引与反查。

守三件事：
  ① 归一化正确（不归一化实测会得到 518 个假 distinct，真值 46）
  ② 分档判定不骗人（通用 / 十版遗留 / 单位特有 三档，依据是 11 版速查表这个真源）
  ③ 索引里的每一条链接都指向**真实存在**的页（生成物不进 lint 的断链扫描，
     所以它的链接正确性只能由本文件保证）
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from wiki_engine.keyword_index import (DEFAULT_PDF, classify, collect,
                                       engine_status, generate, load_glossary,
                                       normalize_keyword, parse_quickref,
                                       _rule_page, _zh_base)

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "db" / "wh40k.sqlite"
WIKI = REPO / "wiki"
PDF = REPO / DEFAULT_PDF

needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")
needs_pdf = pytest.mark.skipif(not PDF.exists(), reason="需要 11 版通用技能速查表 PDF")


# ── 归一化 ────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,base,param", [
    ("RAPID FIRE 2", "RAPID FIRE", "2"),
    ("rapid fire d6+3", "RAPID FIRE", "D6+3"),       # 骰子档位，不能塌成常量
    ("ANTI-INFANTRY 4+", "ANTI-INFANTRY", "4+"),     # 命中门槛不是攻击次数
    ("  twin-linked  ", "TWIN-LINKED", None),
    ("BLAST", "BLAST", None),
    ("SUSTAINED HITS D", "SUSTAINED HITS", "D"),
])
def test_normalize_keyword(raw, base, param):
    assert normalize_keyword(raw) == (base, param)


def test_normalize_does_not_eat_name_digits():
    """词条名自带的数字不能被当成档位剥掉（回归护栏）。"""
    assert normalize_keyword("C'TAN POWER")[0] == "C'TAN POWER"
    assert normalize_keyword("PLASMA WARHEAD")[0] == "PLASMA WARHEAD"


# ── 速查表解析（通用 USR 判定的真源）────────────────────────────────

@needs_pdf
def test_parse_quickref_covers_11e_keywords():
    qr = parse_quickref(PDF)
    assert len(qr) >= 30
    for name in ("CLEAVE", "CLOSE-QUARTERS", "PSYCHIC", "SUSTAINED HITS",
                 "ONE SHOT", "BLAST", "RAPID FIRE"):
        assert name in qr, "速查表漏了 {}".format(name)
    # 速查表（汉化组）写「横扫」；这里断言的是**解析器读对了 PDF**，
    # 不是断言译名政策——全库译名以 GW 官方中文为准（官方 24.06 是「劈砍」），
    # 差异在 wiki/indexes/keywords.md 的「译名差异」节里如实披露
    assert qr["CLEAVE"].name_zh == "横扫"
    assert qr["CLEAVE"].section == "24.06"
    assert qr["CLOSE-QUARTERS"].section == "24.07"
    assert qr["PSYCHIC"].section == "24.29"


@needs_pdf
def test_parse_quickref_does_not_invent_missing_section():
    """PDF 里「连击 SUSTAINED HITS」那行确实没印节号——留空，不按顺序推断补全。"""
    qr = parse_quickref(PDF)
    assert qr["SUSTAINED HITS"].section is None


def test_parse_quickref_missing_file_raises(tmp_path):
    """PDF 缺失时必须抛错。静默返回空 → 46 个词条会全被归进「单位特有」，
    页面看着正常、实际全错。"""
    with pytest.raises(FileNotFoundError):
        parse_quickref(tmp_path / "nope.pdf")


def test_parse_quickref_too_few_entries_raises(tmp_path):
    """PDF 换版/文本层坏掉时也要吼，不能拿半张表当真源。"""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "nothing useful here")
    target = tmp_path / "broken.pdf"
    doc.save(str(target))
    doc.close()
    with pytest.raises(ValueError, match="速查表只解析出"):
        parse_quickref(target)


# ── 分档 ──────────────────────────────────────────────────────────

@needs_pdf
def test_classify_three_buckets():
    qr = parse_quickref(PDF)
    assert classify("BLAST", qr) == "universal"
    assert classify("ANTI-VEHICLE", qr) == "universal"      # ANTI-X 全族归 ANTI
    # 官方 24.27 [手枪] 仍在册、与 24.07 [近距离] 规则等同，正被逐步取代 → 过渡期
    assert classify("PISTOL", qr) == "transitional"
    assert classify("BUBBLECHUKKA", qr) == "unit-specific"
    assert classify("C'TAN POWER", qr) == "unit-specific"


def test_engine_status_is_honest():
    """「仅标注」不能说成「数值建模」——模拟器报告的诚实度依赖这条。"""
    assert engine_status("BLAST") == "数值建模"
    assert engine_status("ANTI-INFANTRY") == "数值建模"
    assert engine_status("PRECISION") == "仅标注"           # 点名附着角色未建模
    assert engine_status("PISTOL") == "仅标注"
    assert engine_status("BUBBLECHUKKA") == "未纳入"


# ── 规则页解析 ────────────────────────────────────────────────────

def test_rule_page_follows_alias_not_only_slug():
    """页名与词条名常不一致：[PSYCHIC] 的页叫 psychic-attacks、
    [CLOSE-QUARTERS] 的页仍叫 pistol。只按 slug 找会误判成「没有规则页」。"""
    assert _rule_page("PSYCHIC", WIKI, "灵能") == "core-rules/psychic-attacks.md"
    assert _rule_page("CLOSE-QUARTERS", WIKI, "近距离") == "core-rules/pistol.md"
    assert _rule_page("ANTI-VEHICLE", WIKI, "针对载具") == "core-rules/anti.md"
    assert _rule_page("BUBBLECHUKKA", WIKI, "泡泡炮") is None   # 无页就是无页，不造红链


# ── 真库端到端 ────────────────────────────────────────────────────

@needs_db
@needs_pdf
def test_generate_index_is_complete_and_linked(tmp_path):
    rep = generate(DB, WIKI, PDF)
    text = (WIKI / "indexes" / "keywords.md").read_text(encoding="utf-8")

    # 对账：三档之和 == 词条总数（不许有词条掉出分档）
    assert sum(rep["groups"].values()) == rep["keywords"]
    assert rep["keywords"] >= 40
    assert rep["groups"]["universal"] >= 30

    # 三档小节都在
    for title in ("通用武器词条", "过渡期词条", "单位特有词条", "反查：哪些武器带这个词条"):
        assert "## {}".format(title) in text or "## {}（".format(title) in text

    # 每个通用词条都链到真实存在的规则页
    section = text.split("## 通用武器词条")[1].split("## 过渡期")[0]
    rows = [l for l in section.splitlines()
            if l.startswith("| ") and not l.startswith("| 词条") and not l.startswith("|---")]
    assert len(rows) >= 30
    for row in rows:
        assert row.startswith("| [[core-rules/"), "通用词条未链到规则页：{}".format(row)

    # 索引里出现的每一个链接目标都必须真实存在（生成物不进 lint 断链扫描）
    for target in set(re.findall(r"\[\[([^\]|\\]+)", text)):
        assert (WIKI / target).exists(), "索引里有断链：{}".format(target)


@needs_db
def test_collect_pairs_match_recount():
    """统计口径可复算：(武器行, 词条) 对数 == 各词条 rows 之和。"""
    stats, tally = collect(DB)
    assert tally["pairs"] == sum(s.rows for s in stats.values())
    assert tally["pairs"] > 5000
    # 归一化生效：档位变体不会各成一条基础词条
    assert "RAPID FIRE 2" not in stats and "RAPID FIRE" in stats
    assert len(stats) < 60, "疑似未归一化（真值 ~46）"


@needs_db
def test_every_keyword_has_chinese_name():
    """索引是给中文读者看的：词条列不许出现裸英文。"""
    stats, _ = collect(DB)
    gloss = load_glossary(DB)
    missing = [b for b, st in stats.items() if not _zh_base(b, st.variants, gloss)]
    assert not missing, "无中文名的词条：{}".format(missing)
