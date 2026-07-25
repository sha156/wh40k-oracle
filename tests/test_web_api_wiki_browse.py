"""tests/test_web_api_wiki_browse.py — 图鉴分队页后端。

覆盖两个端点（GET /codex/factions/{fid}/detachments[/{slug}]）与它们底下的两层：
`web_api/wiki_blocks.py`（markdown → 块）与 `web_api/wiki_browse.py`（读盘 + 对账）。

重点盯三类「自信的错误」——它们不会让测试变红，只会让页面看着像对的：
  · 卷没挂上返回空列表（前端显示「这个阵营没有分队」）→ 必须 503
  · 子页少读了几条却照样 200（前端显示「这个分队只有 3 条战略」）→ 必须 503
  · 0 CP / 0 分被当成 null 显示成「未知」→ 0 是真值，必须原样是 0

真实语料的断言尽量走 `wiki_browse` 函数而不是 TestClient：全量对账要跑 324 个分队，
走 HTTP 会把限流配额（默认 120 次/分，全测试进程共享）吃光，反而制造假红。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

import pytest
from fastapi.testclient import TestClient

from web_api import wiki_blocks as wbk
from web_api import wiki_browse as wb
from web_api.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent
WIKI = REPO_ROOT / "wiki"
DET_ROOT = WIKI / "factions"

needs_wiki = pytest.mark.skipif(
    not (DET_ROOT / "太空死灵" / "detachments").is_dir(),
    reason="wiki/ 分队页不存在（未挂载 wiki 卷）")

# 契约（web/src/lib/wiki.ts）字段全集，camelCase。改这里 = 改契约，
# 必须同步 wiki.ts 与 web_api/contract.py，三处一起动。
SUMMARY_KEYS = {"slug", "nameEn", "nameZh", "ruleName",
                "stratagemCount", "enhancementCount"}
DETAIL_KEYS = SUMMARY_KEYS | {"factionId", "factionZh", "ruleSections",
                              "enhancements", "stratagems"}
STRAT_KEYS = {"id", "slug", "nameEn", "nameZh", "cp", "phase",
              "stratagemType", "sections"}
ENH_KEYS = {"id", "slug", "nameEn", "nameZh", "cost", "sections"}
BLOCK_KEYS = {
    "p": {"t", "inline"}, "quote": {"t", "inline"},
    "ul": {"t", "items"}, "ol": {"t", "items"},
    "table": {"t", "head", "rows"}, "h": {"t", "level", "text"},
}

# 实测磁盘条数（2026-07-25 生成）。数字变了说明离线重跑了 wiki_engine 且结果变了——
# 先确认是有意的，别顺手对齐成"测试通过"。
EXPECTED_DETACHMENTS = 324
EXPECTED_ENHANCEMENTS = 1058
EXPECTED_STRATAGEM_LINKS = 1647


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_cache():
    """每个用例前后都清缓存：合成 wiki 与真实 wiki 在同一进程里轮流上场。"""
    wb.clear_cache()
    yield
    wb.clear_cache()


def _disk_links(page: Path, section: str) -> List[str]:
    """直接从磁盘 markdown 数某节的链接条数（对账的另一侧，不复用被测代码）。"""
    out: List[str] = []
    in_sec = False
    for line in page.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_sec = line[3:].strip() == section
            continue
        if in_sec and line.strip().startswith("- ") and "[[" in line:
            out.append(line)
    return out


# ── 列表端点（真实语料）────────────────────────────────────────────

@needs_wiki
def test_list_matches_disk_file_count(client: TestClient) -> None:
    """列表条数 == 磁盘上的 .md 数。少一个就是悄悄漏了一个分队。"""
    r = client.get("/codex/factions/NEC/detachments")
    assert r.status_code == 200
    items = r.json()["items"]
    on_disk = sorted(p.stem for p in (DET_ROOT / "太空死灵" / "detachments").glob("*.md"))
    assert sorted(i["slug"] for i in items) == on_disk
    assert set(items[0]) == SUMMARY_KEYS
    assert not any("_" in k for i in items for k in i)   # 蛇形字段不许漏出去


@needs_wiki
def test_all_factions_total_matches_disk() -> None:
    """全 25 阵营合计对账（走函数层，别拿限流配额换这一条）。"""
    from wiki_engine.from_db import FACTION_DIRS
    total = sum(len(wb.list_detachments(fid)) for fid in FACTION_DIRS)
    on_disk = len(list(DET_ROOT.glob("*/detachments/*.md")))
    assert total == on_disk == EXPECTED_DETACHMENTS


@needs_wiki
def test_factions_without_detachments_return_empty_list(client: TestClient) -> None:
    """泰坦军团 / 无阵营工事 11 版本就没有分队——这时候空列表才是真话。

    与「wiki 没挂上」的区别由 wiki_browse 保证：那种情况走 503（见下面的用例）。
    """
    r = client.get("/codex/factions/TL/detachments")
    assert r.status_code == 200 and r.json()["items"] == []
    assert wb.list_detachments("UN") == []


@needs_wiki
def test_unknown_faction_404(client: TestClient) -> None:
    r = client.get("/codex/factions/NOPE/detachments")
    assert r.status_code == 404
    assert "阵营" in r.json()["detail"]


# ── 详情端点（真实语料）────────────────────────────────────────────

@needs_wiki
def test_detail_inlines_every_linked_child(client: TestClient) -> None:
    """内联子条目数 == 分队页链接清单条数（两侧独立数，不共用解析代码）。"""
    r = client.get("/codex/factions/NEC/detachments/awakened-dynasty")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == DETAIL_KEYS
    page = DET_ROOT / "太空死灵" / "detachments" / "awakened-dynasty.md"
    assert len(body["enhancements"]) == len(_disk_links(page, "增强"))
    assert len(body["stratagems"]) == len(_disk_links(page, "战略"))
    # 计数字段与内联数组必须同一个口径，否则前端"6 条战略"下面列出 5 条
    assert body["enhancementCount"] == len(body["enhancements"])
    assert body["stratagemCount"] == len(body["stratagems"])
    assert set(body["stratagems"][0]) == STRAT_KEYS
    assert set(body["enhancements"][0]) == ENH_KEYS


@needs_wiki
def test_every_detachment_reconciles() -> None:
    """全量对账：324 个分队，逐个核链接数 vs 内联数，合计也要对上。"""
    from wiki_engine.from_db import FACTION_DIRS
    enh = strat = 0
    for fid, zh in FACTION_DIRS.items():
        for item in wb.list_detachments(fid):
            detail = wb.detachment_detail(fid, item.slug)
            page = DET_ROOT / zh / "detachments" / (item.slug + ".md")
            assert len(detail.enhancements) == len(_disk_links(page, "增强")), item.slug
            assert len(detail.stratagems) == len(_disk_links(page, "战略")), item.slug
            enh += len(detail.enhancements)
            strat += len(detail.stratagems)
    assert enh == EXPECTED_ENHANCEMENTS
    assert strat == EXPECTED_STRATAGEM_LINKS


@needs_wiki
def test_rule_name_is_the_rule_not_the_detachment(client: TestClient) -> None:
    """ruleName 是分队**规则**名，不是分队名——搞反了整页都在说另一件事。"""
    body = client.get("/codex/factions/NEC/detachments/awakened-dynasty").json()
    assert body["nameEn"] == "Awakened Dynasty"
    assert body["ruleName"] == "指令协议 Command Protocols"
    # 没绑规则行的分队照实给 null，不拿分队名冒充
    assert wb.detachment_detail("ORK", "rollin-deff").rule_name is None


@needs_wiki
def test_same_slug_in_two_factions_resolves_by_faction_id() -> None:
    """Infestation Swarm 在基因窃取者教派与泰伦虫族各一个，路由带 faction_id 才不串。

    这两份正文碰巧一字不差（库里是两条独立记录，见下面比对的 id），所以断言要盯
    **id 与阵营**，不能盯正文——盯正文的话，哪天真串了也照样绿。
    """
    gc = wb.detachment_detail("GC", "infestation-swarm")
    tyr = wb.detachment_detail("TYR", "infestation-swarm")
    assert gc.faction_id == "GC" and gc.faction_zh == "基因窃取者教派"
    assert tyr.faction_id == "TYR" and tyr.faction_zh == "泰伦虫族"
    assert {s.id for s in gc.stratagems}.isdisjoint({s.id for s in tyr.stratagems})
    assert {e.id for e in gc.enhancements}.isdisjoint({e.id for e in tyr.enhancements})


@needs_wiki
def test_unknown_slug_404(client: TestClient) -> None:
    r = client.get("/codex/factions/NEC/detachments/no-such-detachment")
    assert r.status_code == 404
    assert "分队" in r.json()["detail"]


@needs_wiki
@pytest.mark.parametrize("slug", ["../index", "..", ".hidden", "a/b", ""])
def test_slug_traversal_rejected(slug: str) -> None:
    """slug 是文件名分量，不许含分隔符/`..`——别让人顺着它读到 wiki 之外。"""
    with pytest.raises(wb.NotFound):
        wb.detachment_detail("NEC", slug)


# ── 0 是真值，不是"未知" ───────────────────────────────────────────

@needs_wiki
def test_zero_cost_enhancement_stays_zero() -> None:
    """0 分增强（实测 117 条）的 cost 必须是 0；库里没这项数据的才是 null。"""
    costs = {e.slug: e.cost for e in wb.detachment_detail("ORK", "kaptin-killers").enhancements}
    assert costs["gnasher-squig-crates"] == 0
    assert 0 in costs.values()
    missing = {e.slug: e.cost for e in wb.detachment_detail("ORK", "rollin-deff").enhancements}
    assert missing["boarding-ramps"] is None


# ── wikilink / 表格 / 引用（真实语料）──────────────────────────────

@needs_wiki
def test_wikilinks_are_flattened_to_plain_text() -> None:
    """`[[路径\\|显示名]]` 只留显示名：前端没有 wiki 路由，画成链接就是一片 404。"""
    detail = wb.detachment_detail("ORK", "dread-mob")
    blob = json.dumps(detail.model_dump(by_alias=True), ensure_ascii=False)
    # 别用裸 "[[" 判：JSON 里的嵌套数组（"rows": [[…）天然带两个方括号，会假红
    assert not re.search(r"\[\[[^\]]+\]\]", blob)
    assert ".md" not in blob and "\\\\|" not in blob   # 路径与转义竖线都不许漏出来
    text = " ".join(sp["s"] for sec in detail.model_dump(by_alias=True)["ruleSections"]
                    for b in sec["blocks"] if b["t"] == "p"
                    for sp in b["inline"] if "s" in sp)
    assert "Mek" in text and "Gretchin" in text   # 显示名还在


@needs_wiki
def test_table_block_parsed_with_promoted_header() -> None:
    """空表头提升：`| | |` + 加粗首行 → 真表头，不留一条空白表头。"""
    detail = wb.detachment_detail("ORK", "dread-mob")
    tables = [b for sec in detail.rule_sections for b in sec.blocks if b.t == "table"]
    assert len(tables) == 1
    tbl = tables[0]
    assert tbl.head == ["D6", "BUTTON EFFECT"]
    assert [r[0] for r in tbl.rows] == ["1 2", "3 4", "5 6"]
    assert all(len(r) == len(tbl.head) for r in tbl.rows)
    assert "**" not in json.dumps(tbl.model_dump(), ensure_ascii=False)


@needs_wiki
def test_all_caps_table_keeps_every_row_as_data() -> None:
    """整张表都是全大写档位对时**没有表头**，首行不许被提成表头（会吞掉一档）。

    机械修会 Haloscreed Battle Clade 的源表是 `INCURSION: | 1 UNIT` /
    `STRIKE FORCE | 2 UNITS` / `ONSLAUGHT | 3 UNITS`，三行都是数据。按"首行全大写
    就是表头"提升的话，Incursion 那一档会从表体消失、变成一条读不通的表头，
    页面于是自信地宣称这张表只有 Strike Force 和 Onslaught 两档。
    """
    detail = wb.detachment_detail("AdM", "haloscreed-battle-clade")
    tables = [b for sec in detail.rule_sections for b in sec.blocks if b.t == "table"]
    assert len(tables) == 1
    tbl = tables[0]
    assert [r[0] for r in tbl.rows] == ["INCURSION:", "STRIKE FORCE", "ONSLAUGHT"]
    assert [r[1] for r in tbl.rows] == ["1 UNIT", "2 UNITS", "3 UNITS"]
    assert all(not c for c in tbl.head)      # 源表没有表头，就照实空着


def test_single_row_table_is_never_promoted() -> None:
    """只有一行的表提升后会变成空表——宁可少画表头也不吞内容。"""
    tbl = wbk.parse_blocks("| | |\n|---|---|\n| **D6** | **EFFECT** |\n".splitlines())[0]
    assert tbl.head == ["", ""] and tbl.rows == [["D6", "EFFECT"]]


@needs_wiki
def test_quote_block_carries_honest_disclosure() -> None:
    """页面里的诚实披露（「名下有 2 条规则，以下全部列出」）走 quote 块，不能掉。"""
    detail = wb.detachment_detail("ORK", "dread-mob")
    quotes = [b for sec in detail.rule_sections for b in sec.blocks if b.t == "quote"]
    assert quotes and "全部列出" in "".join(
        sp.s for sp in quotes[0].inline if hasattr(sp, "s"))


@needs_wiki
def test_all_blocks_have_exact_contract_shape() -> None:
    """扫一遍全部真实块：键集合必须和契约一字不差（多一个字段没人会发现）。"""
    from wiki_engine.from_db import FACTION_DIRS
    seen = set()
    for fid in FACTION_DIRS:
        for item in wb.list_detachments(fid):
            detail = wb.detachment_detail(fid, item.slug).model_dump(by_alias=True)
            sections = list(detail["ruleSections"])
            for child in detail["enhancements"] + detail["stratagems"]:
                sections += child["sections"]
            for sec in sections:
                assert set(sec) == {"title", "blocks"}
                for blk in sec["blocks"]:
                    assert set(blk) == BLOCK_KEYS[blk["t"]], blk["t"]
                    seen.add(blk["t"])
    assert seen == set(BLOCK_KEYS)      # 六种块型真实语料里都出现过


# ── 合成 wiki：缺件 / 0 CP / 缓存 ──────────────────────────────────

_DET_PAGE = """---
id: '000000001'
name_en: Test Detachment
faction: 太空死灵
type: detachment
detachment: Test Detachment
---

太空死灵的分队，分队规则「测试规则」。

## 分队规则

> 诚实披露一行。

### 测试规则 Test Rule

普通段落，带 [[factions/太空死灵/units/foo.md\\|某单位]] 与 [SUSTAINED HITS 1]。

| | |
|---|---|
| **BATTLE SIZE** | **NUMBER OF UNITS** |
| Incursion | 2 |

- 列表项甲
- 列表项乙

## 增强

- [[factions/太空死灵/enhancements/free-relic.md\\|白给圣物]]

## 战略

- [[factions/太空死灵/stratagems/zero-cp.md\\|零费战略]]
- [[factions/太空死灵/stratagems/no-cp.md\\|未知费战略]]
"""

_ZERO_CP = """---
id: '000000002'
name_zh: 零费战略
name_en: ZERO CP TRICK
faction: 太空死灵
type: stratagem
detachment: Test Detachment
cp: 0
phase: Fight phase
stratagem_type: Test – Battle Tactic Stratagem
---

0 CP、Fight phase、Battle Tactic Stratagem。

## 使用时机

Your Fight phase.

## 效果

Nothing happens.
"""

_NO_CP = """---
id: '000000003'
name_en: NO CP RECORDED
faction: 太空死灵
type: stratagem
detachment: Test Detachment
phase: Fight phase
---

## 效果

Unknown cost.
"""

_FREE_RELIC = """---
id: '000000004'
name_zh: 白给圣物
name_en: Free Relic
faction: 太空死灵
type: enhancement
detachment: Test Detachment
cost: 0
---

## 效果

Costs nothing.

## 携带限制

NECRONS model only.
"""


def _fake_wiki(root: Path) -> Path:
    base = root / "factions" / "太空死灵"
    (base / "detachments").mkdir(parents=True)
    (base / "stratagems").mkdir(parents=True)
    (base / "enhancements").mkdir(parents=True)
    (base / "units").mkdir(parents=True)
    (base / "detachments" / "test-detachment.md").write_text(_DET_PAGE, encoding="utf-8")
    (base / "stratagems" / "zero-cp.md").write_text(_ZERO_CP, encoding="utf-8")
    (base / "stratagems" / "no-cp.md").write_text(_NO_CP, encoding="utf-8")
    (base / "enhancements" / "free-relic.md").write_text(_FREE_RELIC, encoding="utf-8")
    return root


@pytest.fixture
def fake_wiki(tmp_path, monkeypatch) -> Path:
    root = _fake_wiki(tmp_path / "wiki")
    monkeypatch.setattr(wb, "WIKI_ROOT", root)
    wb.clear_cache()
    return root


def test_zero_cp_stratagem_stays_zero(fake_wiki: Path) -> None:
    """0 CP 是真值（核心战略里就有），null 才是"库里没这项数据"。混了就骗人。"""
    detail = wb.detachment_detail("NEC", "test-detachment")
    cps = {s.slug: s.cp for s in detail.stratagems}
    assert cps == {"zero-cp": 0, "no-cp": None}
    assert cps["zero-cp"] is not None           # 别让 0 被 falsy 判成缺失
    zero = next(s for s in detail.stratagems if s.slug == "zero-cp")
    assert zero.stratagem_type == "Test – Battle Tactic Stratagem"
    # 契约要求 phase/stratagemType 是字符串：缺数据给空串，不给 null
    assert next(s for s in detail.stratagems if s.slug == "no-cp").stratagem_type == ""


def test_synthetic_blocks_cover_every_shape(fake_wiki: Path) -> None:
    blocks = wb.detachment_detail("NEC", "test-detachment").rule_sections[0].blocks
    kinds = [b.t for b in blocks]
    assert kinds == ["quote", "h", "p", "table", "ul"]
    assert blocks[1].level == 3 and blocks[1].text == "测试规则 Test Rule"
    assert blocks[3].head == ["BATTLE SIZE", "NUMBER OF UNITS"]
    assert blocks[3].rows == [["Incursion", "2"]]
    assert [len(x) for x in blocks[4].items] == [1, 1]
    para = "".join(sp.s for sp in blocks[2].inline if hasattr(sp, "s"))
    assert "某单位" in para and "[[" not in para
    assert any(sp.t == "kw" and sp.s == "[SUSTAINED HITS 1]" for sp in blocks[2].inline)


def test_missing_child_page_returns_503(fake_wiki: Path, client: TestClient,
                                        monkeypatch) -> None:
    """链接列了 2 条战略、磁盘上只剩 1 条 → 503 并点名，绝不悄悄返回 1 条。"""
    (fake_wiki / "factions" / "太空死灵" / "stratagems" / "no-cp.md").unlink()
    wb.clear_cache()
    with pytest.raises(wb.WikiUnavailable) as exc:
        wb.detachment_detail("NEC", "test-detachment")
    msg = str(exc.value)
    assert "no-cp.md" in msg and "2 条" in msg and "1 条" in msg
    r = client.get("/codex/factions/NEC/detachments/test-detachment")
    assert r.status_code == 503 and "对不上账" in r.json()["detail"]


def test_missing_wiki_returns_503_not_empty_list(client: TestClient, tmp_path,
                                                 monkeypatch) -> None:
    """卷没挂上 → 503。返回 200 + 空列表 = 告诉用户「这个阵营没有分队」。"""
    monkeypatch.setattr(wb, "WIKI_ROOT", tmp_path / "nope")
    wb.clear_cache()
    r = client.get("/codex/factions/NEC/detachments")
    assert r.status_code == 503
    assert "wiki" in r.json()["detail"] and "挂载" in r.json()["detail"]
    assert client.get(
        "/codex/factions/NEC/detachments/awakened-dynasty").status_code == 503


def test_empty_faction_dir_is_breakage_not_zero(tmp_path, monkeypatch) -> None:
    """阵营目录在但里面空空如也 = 产物残缺，走 503；不是"这个阵营没有分队"。"""
    (tmp_path / "wiki" / "factions" / "太空死灵").mkdir(parents=True)
    monkeypatch.setattr(wb, "WIKI_ROOT", tmp_path / "wiki")
    wb.clear_cache()
    with pytest.raises(wb.WikiUnavailable):
        wb.list_detachments("NEC")


def test_corrupt_page_without_frontmatter_returns_503(fake_wiki: Path) -> None:
    """写了一半的页 → 503。半截页里的数值不能信，不能当规则端上去。"""
    page = fake_wiki / "factions" / "太空死灵" / "detachments" / "test-detachment.md"
    page.write_text("没有 frontmatter 的半截文件\n", encoding="utf-8")
    wb.clear_cache()
    with pytest.raises(wb.WikiUnavailable) as exc:
        wb.detachment_detail("NEC", "test-detachment")
    assert "frontmatter" in str(exc.value)


def test_error_detail_does_not_leak_absolute_path(tmp_path, monkeypatch) -> None:
    """报错信息用仓库相对路径，别把服务器目录结构吐进 HTTP 响应。"""
    monkeypatch.setattr(wb, "WIKI_ROOT", tmp_path / "wiki")
    wb.clear_cache()
    (tmp_path / "wiki" / "factions").mkdir(parents=True)
    with pytest.raises(wb.WikiUnavailable) as exc:
        wb.list_detachments("NEC")
    assert str(tmp_path) not in str(exc.value)


def test_cache_invalidates_on_file_change(fake_wiki: Path) -> None:
    """离线重跑 wiki_engine 后不必重启 API：(mtime, size) 一变就重读。"""
    assert wb.list_detachments("NEC")[0].name_en == "Test Detachment"
    page = fake_wiki / "factions" / "太空死灵" / "detachments" / "test-detachment.md"
    page.write_text(_DET_PAGE.replace("name_en: Test Detachment",
                                      "name_en: Renamed Detachment"),
                    encoding="utf-8")
    assert wb.list_detachments("NEC")[0].name_en == "Renamed Detachment"


# ── wiki_blocks 单元 ──────────────────────────────────────────────

@pytest.mark.parametrize("raw,want", [
    ("见 [[core-rules/rapid-fire.md|速射]] 一节", "见 速射 一节"),
    ("见 [[core-rules/rapid-fire.md\\|速射]] 一节", "见 速射 一节"),   # 表格里的转义写法
    ("[[factions/兽人/units/mek.md]] 单位", "mek 单位"),               # 无管道兜底
])
def test_flatten_wikilinks(raw: str, want: str) -> None:
    assert wbk.flatten_wikilinks(raw) == want


def test_table_cell_restores_escaped_pipe() -> None:
    """单元格里的 `\\|` 要还原成 `|`，但拆列必须按**未转义**的竖线拆。"""
    md = "| A | B |\n|---|---|\n| x \\| y | [[a/b.md\\|乙]] |\n"
    tbl = wbk.parse_blocks(md.splitlines())[0]
    assert tbl.head == ["A", "B"]
    assert tbl.rows == [["x | y", "乙"]]


def test_ragged_table_pads_instead_of_truncating() -> None:
    """列数不齐时补空格，不截断——截断是静默丢内容。"""
    tbl = wbk.parse_blocks("| A | B |\n|---|---|\n| 1 | 2 | 3 |\n".splitlines())[0]
    assert tbl.head == ["A", "B", ""] and tbl.rows == [["1", "2", "3"]]


def test_header_promotion_only_when_row_is_all_caps() -> None:
    """全大写首行才是掉进表体的表头；带小写的是数据行，硬提升等于伪造表头。"""
    promoted = wbk.parse_blocks(
        "| | |\n|---|---|\n| **D6** | EFFECT |\n| 1 | boom |\n".splitlines())[0]
    assert promoted.head == ["D6", "EFFECT"] and len(promoted.rows) == 1
    kept = wbk.parse_blocks(
        "| | |\n|---|---|\n| 1 | **Cholinergic:** Add 1 |\n".splitlines())[0]
    assert kept.head == ["", ""] and len(kept.rows) == 1


def test_ordered_list_keeps_lazy_continuation_in_one_list() -> None:
    """条目间隔着空行、正文另起一行——CommonMark 里仍是一个 6 项列表。

    不这么解析的话「战斗药剂」会渲染成六个各自从 1 开始编号的单项列表。
    """
    md = "1. Adrenalight\nAdd 1 to Attacks.\n\n2. Hypex\nAdd 2\" to Move.\n"
    blocks = wbk.parse_blocks(md.splitlines())
    assert len(blocks) == 1 and blocks[0].t == "ol" and len(blocks[0].items) == 2
    first = "".join(sp.s for sp in blocks[0].items[0] if hasattr(sp, "s"))
    assert first.startswith("Adrenalight") and "Attacks" in first


def test_paragraph_lines_are_not_merged() -> None:
    """相邻正文行各自成段：伪列表（**Incursion:** … / **Strike Force:** …）合并就读不通。"""
    md = "**Incursion:** Up to 500 pts\n**Strike Force:** Up to 1000 pts\n"
    blocks = wbk.parse_blocks(md.splitlines())
    assert [b.t for b in blocks] == ["p", "p"]


def test_lede_before_first_section_is_dropped() -> None:
    """导语是 cp/phase/detachment 拼出来的展示串，契约里都有字段，不重复下发。"""
    sections = wbk.parse_sections("1 CP、Fight phase 分队。\n\n## 效果\n\n正文。\n")
    assert [s.title for s in sections] == ["效果"]


def test_split_frontmatter_roundtrip() -> None:
    fm, body = wbk.split_frontmatter("---\nid: '007'\ncp: 0\n---\n\n正文\n")
    assert fm == {"id": "007", "cp": 0} and body.strip() == "正文"
    assert wbk.split_frontmatter("没有 frontmatter") == ({}, "没有 frontmatter")


def test_list_link_targets_reads_raw_paths() -> None:
    """链接清单要拿**路径**，不能靠显示名反查——名字跨阵营会撞。"""
    body = ("## 增强\n\n- [[factions/兽人/enhancements/a.md\\|甲]]\n"
            "- [[factions/兽人/enhancements/b.md\\|乙]]\n\n## 战略\n\n（无）\n")
    assert wbk.list_link_targets(body, "增强") == [
        ("factions/兽人/enhancements/a.md", "甲"),
        ("factions/兽人/enhancements/b.md", "乙"),
    ]
    assert wbk.list_link_targets(body, "战略") == []
