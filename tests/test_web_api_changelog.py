"""tests/test_web_api_changelog.py — 图鉴规则变更清单页后端。

覆盖两个端点（GET /codex/changelog[/{slug}]）与 `web_api/changelog_browse.py`。

这一层的核心是**对账**：`index.md` 的「各阵营改动一览」表声明了每个包多少条改动、
其中多少条是 🆕 增量，阵营页里实际有多少个 `###` 条目是另一侧。所以这里除了打真语料，
还专门合成几份**对不上的** wiki，确认对账真会红——一个只会在真语料上通过的对账
等于没有对账（"592 条改动"是这页的头条断言，悄悄少几条页面照样渲染得漂漂亮亮）。

真语料这一侧的条数**独立重数一遍**（`_disk_counts` 直接扫 markdown），不复用被测代码：
校验器与被校验对象共用同一套解析假设就会一起瞎，本仓库刚在核心规则切章上吃过这个亏。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Tuple

import pytest
from fastapi.testclient import TestClient

from web_api import changelog_browse as cgb
from web_api.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "wiki" / "changelog"

needs_wiki = pytest.mark.skipif(
    not (CHANGELOG / "index.md").is_file(),
    reason="wiki/changelog 不存在（未挂载 wiki 卷）")

# 契约（web/src/lib/wiki.ts）字段全集，camelCase。改这里 = 改契约，三处一起动。
INDEX_KEYS = {"intro", "generalSections", "noteSections", "factions", "total",
              "newCount"}
FACTION_ROW_KEYS = {"slug", "name", "version", "total", "newCount", "detail"}
PAGE_KEYS = {"slug", "nameZh", "nameEn", "version", "total", "newCount",
             "intro", "sections"}

# 实测磁盘数（2026-07-26 生成）。数字变了说明离线重跑了生成器且结果变了——
# 先确认是有意的，别顺手对齐成"测试通过"。
EXPECTED_PACKS = 28
EXPECTED_TOTAL = 592
EXPECTED_NEW = 128
EXPECTED_BLANK_ROWS = 2      # 首版无更新章节（deathwatch）+ 官方未列改动（混沌恶魔）

_NEW_MARK = "🆕"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_cache():
    cgb.clear_cache()
    yield
    cgb.clear_cache()


def _disk_counts() -> Dict[str, Tuple[int, int]]:
    """直接扫 markdown 数每页的 (条目数, 🆕 数)——对账的另一侧，不复用被测代码。"""
    out: Dict[str, Tuple[int, int]] = {}
    for page in (CHANGELOG / "factions").glob("*.md"):
        heads = [ln for ln in page.read_text(encoding="utf-8").splitlines()
                 if ln.startswith("### ")]
        out[page.stem] = (len(heads),
                          sum(1 for ln in heads if _NEW_MARK in ln))
    return out


# ── 首页（真实语料）────────────────────────────────────────────────

@needs_wiki
def test_index_shape_and_totals(client: TestClient) -> None:
    r = client.get("/codex/changelog")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == INDEX_KEYS
    assert not any("_" in k for k in body)               # 蛇形字段不许漏出去
    assert len(body["factions"]) == EXPECTED_PACKS
    assert set(body["factions"][0]) == FACTION_ROW_KEYS
    assert body["total"] == EXPECTED_TOTAL
    assert body["newCount"] == EXPECTED_NEW


@needs_wiki
def test_index_totals_match_independent_disk_recount(client: TestClient) -> None:
    """合计 == 直接扫 markdown 数出来的合计（两侧独立数，别共用解析假设）。"""
    disk = _disk_counts()
    assert len(disk) == EXPECTED_PACKS
    assert sum(t for t, _ in disk.values()) == EXPECTED_TOTAL
    assert sum(n for _, n in disk.values()) == EXPECTED_NEW
    body = client.get("/codex/changelog").json()
    for row in body["factions"]:
        if row["slug"] is None:
            continue
        assert disk[row["slug"]] == (row["total"], row["newCount"]), row


@needs_wiki
def test_rows_without_detail_page_keep_the_reason(client: TestClient) -> None:
    """没有明细页的两行：slug 为 null，明细列写的是原因，不许伪造一个空页面。"""
    rows = client.get("/codex/changelog").json()["factions"]
    blank = [r for r in rows if r["slug"] is None]
    assert len(blank) == EXPECTED_BLANK_ROWS
    for row in blank:
        assert row["total"] == 0 and row["newCount"] == 0
        assert row["detail"] and "查看" not in row["detail"]
        assert "[[" not in row["detail"]                  # wikilink 要压成纯文本


@needs_wiki
def test_general_updates_and_notes_are_separated(client: TestClient) -> None:
    """《通用规则更新》与口径说明分开下发，一览表本身不重复下发成小节。"""
    body = client.get("/codex/changelog").json()
    general = [s["title"] for s in body["generalSections"]]
    notes = [s["title"] for s in body["noteSections"]]
    assert general and all(t.startswith("通用规则更新") for t in general)
    assert notes                                          # 此刻是「数值层的 10→11 漂移」
    assert "各阵营改动一览" not in general + notes
    # 口径说明必须提到数值补丁那条线（本页只收文字改动，两者不要混读）
    text = "".join(sp.get("s", "") for s in body["noteSections"]
                   for b in s["blocks"] for sp in b.get("inline", []))
    assert "fp_errata" in text or "数值" in text


@needs_wiki
def test_index_intro_carries_the_red_highlight_disclosure(client: TestClient) -> None:
    """导语里那条「🆕 判据是官方红色高亮、不是 diff 猜的」必须下发。

    这是本页最重要的一条披露：手上只有 v1.1 一版，没有 v1.0 可 diff，
    红色高亮是唯一的一手证据。不显示它，读者会以为增量是我们比对出来的。
    """
    body = client.get("/codex/changelog").json()
    quotes = [b for b in body["intro"] if b["t"] == "quote"]
    assert quotes
    text = "".join(sp.get("s", "") for b in quotes for sp in b["inline"])
    assert "红色" in text and "diff" in text.lower()


# ── 阵营页（真实语料）──────────────────────────────────────────────

@needs_wiki
def test_faction_page_shape(client: TestClient) -> None:
    r = client.get("/codex/changelog/black-templars")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == PAGE_KEYS
    assert body["slug"] == "black-templars"
    assert body["version"].startswith("阵营包 v")
    disk = _disk_counts()["black-templars"]
    assert (body["total"], body["newCount"]) == disk
    assert body["sections"]                                # 有改动就必须有小节
    assert body["intro"]


@needs_wiki
def test_new_marks_land_on_entry_headings(client: TestClient) -> None:
    """🆕 标在条目标题（`###` 块）上，数量与页面自报一致。"""
    body = client.get("/codex/changelog/dark-angels").json()
    heads = [b["text"] for s in body["sections"] for b in s["blocks"]
             if b["t"] == "h" and b["level"] == 3]
    assert len(heads) == body["total"]
    assert sum(1 for h in heads if _NEW_MARK in h) == body["newCount"]
    assert body["newCount"] > 0                            # 黑暗天使确有增量（实测 12）


@needs_wiki
def test_pack_without_updates_is_200_not_503(client: TestClient) -> None:
    """首版无更新章节的包（deathwatch）：0 条是真话，导语里写了原因，不许 503。"""
    r = client.get("/codex/changelog/deathwatch")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0 and body["sections"] == []
    text = "".join(sp.get("s", "") for b in body["intro"]
                   for sp in b.get("inline", []))
    assert "没有" in text or "首版" in text


@needs_wiki
@pytest.mark.parametrize("slug", ["nope", "../index", "factions/nope",
                                  ".hidden"])
def test_unknown_or_traversal_slug_404(client: TestClient, slug: str) -> None:
    r = client.get("/codex/changelog/{}".format(slug))
    assert r.status_code == 404, (slug, r.status_code)


# ── 对账（合成语料：必须真会红）────────────────────────────────────

_INDEX = """---
id: changelog-index
name_zh: 规则变更清单
name_en: Rules Change Log
type: changelog
---

合计 **3 条**。

> 🆕 读自红色高亮，不是 diff 猜的。

## 各阵营改动一览

| 阵营包 | 版本 | 改动条数 | 其中新增 | 明细 |
|---|---:|---:|---:|---|
| 甲阵营 | v1.1 | 2 | 1 | [[changelog/factions/alpha.md\\|查看]] |
| 乙阵营 | v1.0 | 0 | 0 | 首版，无更新章节 |

## 数值层的漂移

数值漂移在别处。
"""

_ALPHA = """---
id: changelog-alpha
name_zh: 甲阵营 规则更新
name_en: Alpha Rules Updates
type: changelog
version:
  rules: 阵营包 v1.1（测试）
---

共 2 条改动，其中 1 条新增。

> 照抄官方。

## 军队规则

### 第一条 🆕

改为：随便。

### 第二条

改为：也随便。
"""

_BETA = """---
id: changelog-beta
name_zh: 乙阵营 规则更新
name_en: Beta Rules Updates
type: changelog
version:
  rules: 阵营包 v1.0（测试）
---

本阵营包没有「规则更新」章节。
"""


@pytest.fixture
def fake_changelog(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "wiki" / "changelog"
    (root / "factions").mkdir(parents=True)
    (root / "index.md").write_text(_INDEX, encoding="utf-8")
    (root / "factions" / "alpha.md").write_text(_ALPHA, encoding="utf-8")
    (root / "factions" / "beta.md").write_text(_BETA, encoding="utf-8")
    monkeypatch.setattr(cgb, "CHANGELOG_DIR", root)
    monkeypatch.setattr(cgb, "INDEX_PATH", root / "index.md")
    monkeypatch.setattr(cgb, "FACTIONS_DIR", root / "factions")
    cgb.clear_cache()
    return root


def test_synthetic_index_reconciles(fake_changelog: Path) -> None:
    """先确认这份合成语料本身是对得上账的——否则后面几条"必须红"证明不了任何事。"""
    index = cgb.changelog_index()
    assert index.total == 2 and index.new_count == 1
    assert [f.slug for f in index.factions] == ["alpha", None]
    assert index.factions[1].detail == "首版，无更新章节"
    assert [s.title for s in index.general_sections] == []
    assert [s.title for s in index.note_sections] == ["数值层的漂移"]


def test_entry_count_mismatch_is_503(fake_changelog: Path) -> None:
    """清单说 2 条、页里只剩 1 条 → 503 并点名两个数字。"""
    page = fake_changelog / "factions" / "alpha.md"
    page.write_text(_ALPHA.replace("### 第二条\n\n改为：也随便。\n", ""),
                    encoding="utf-8")
    cgb.clear_cache()
    with pytest.raises(cgb.WikiUnavailable) as exc:
        cgb.changelog_index()
    msg = str(exc.value)
    assert "alpha" in msg and "2/1" in msg and "1/1" in msg


def test_new_mark_count_mismatch_is_503(fake_changelog: Path) -> None:
    """条目数对得上、但 🆕 数不对 → 也必须 503。

    🆕 是这页的第二个头条数字（"128 条增量"），只对总数不对增量等于漏掉一半对账。
    """
    page = fake_changelog / "factions" / "alpha.md"
    page.write_text(_ALPHA.replace("### 第一条 🆕", "### 第一条"), encoding="utf-8")
    cgb.clear_cache()
    with pytest.raises(cgb.WikiUnavailable) as exc:
        cgb.changelog_index()
    assert "alpha" in str(exc.value)


def test_missing_detail_page_is_503(fake_changelog: Path) -> None:
    """清单点了名的明细页读不到 → 503，不许悄悄少给一行。"""
    (fake_changelog / "factions" / "alpha.md").unlink()
    cgb.clear_cache()
    with pytest.raises(cgb.WikiUnavailable) as exc:
        cgb.changelog_index()
    assert "alpha" in str(exc.value) and "读不到" in str(exc.value)


def test_unlisted_page_on_disk_is_503(fake_changelog: Path) -> None:
    """磁盘上多出一页清单没列的 → index 落后了，头条数字会偏小，必须吵。"""
    (fake_changelog / "factions" / "gamma.md").write_text(
        _ALPHA.replace("甲阵营", "丙阵营"), encoding="utf-8")
    cgb.clear_cache()
    with pytest.raises(cgb.WikiUnavailable) as exc:
        cgb.changelog_index()
    assert "gamma" in str(exc.value)


def test_manifest_column_change_is_503(fake_changelog: Path) -> None:
    """一览表列数变了 → 不猜，直接 503（列错位会把条数读成版本号）。"""
    (fake_changelog / "index.md").write_text(
        _INDEX.replace("| 甲阵营 | v1.1 | 2 | 1 |", "| 甲阵营 | v1.1 | 2 |"),
        encoding="utf-8")
    cgb.clear_cache()
    with pytest.raises(cgb.WikiUnavailable) as exc:
        cgb.changelog_index()
    assert "列数" in str(exc.value)


def test_missing_manifest_table_is_503(fake_changelog: Path) -> None:
    """一览表整节没了 → 503，不返回一个空的阵营列表。"""
    (fake_changelog / "index.md").write_text(
        _INDEX.replace("## 各阵营改动一览", "## 改了名字的节"), encoding="utf-8")
    cgb.clear_cache()
    with pytest.raises(cgb.WikiUnavailable) as exc:
        cgb.changelog_index()
    assert "各阵营改动一览" in str(exc.value)


def test_non_numeric_count_is_503(fake_changelog: Path) -> None:
    (fake_changelog / "index.md").write_text(
        _INDEX.replace("| 甲阵营 | v1.1 | 2 | 1 |", "| 甲阵营 | v1.1 | 若干 | 1 |"),
        encoding="utf-8")
    cgb.clear_cache()
    with pytest.raises(cgb.WikiUnavailable) as exc:
        cgb.changelog_index()
    assert "不是数字" in str(exc.value)


def test_missing_index_returns_503(client: TestClient, tmp_path,
                                   monkeypatch) -> None:
    """卷没挂上 → 503（HTTP 层也要是 503，不是 200 + 空清单）。"""
    monkeypatch.setattr(cgb, "INDEX_PATH", tmp_path / "nope" / "index.md")
    monkeypatch.setattr(cgb, "FACTIONS_DIR", tmp_path / "nope" / "factions")
    cgb.clear_cache()
    r = client.get("/codex/changelog")
    assert r.status_code == 503 and "挂载" in r.json()["detail"]


def test_corrupt_page_without_frontmatter_is_503(fake_changelog: Path) -> None:
    (fake_changelog / "factions" / "alpha.md").write_text("半截文件\n",
                                                          encoding="utf-8")
    cgb.clear_cache()
    with pytest.raises(cgb.WikiUnavailable) as exc:
        cgb.changelog_index()
    assert "frontmatter" in str(exc.value)


def test_error_detail_does_not_leak_absolute_path(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(cgb, "INDEX_PATH", tmp_path / "wiki" / "nope.md")
    monkeypatch.setattr(cgb, "FACTIONS_DIR", tmp_path / "wiki" / "factions")
    cgb.clear_cache()
    with pytest.raises(cgb.WikiUnavailable) as exc:
        cgb.changelog_index()
    assert str(tmp_path) not in str(exc.value)


def test_faction_page_counts_are_recounted_locally(fake_changelog: Path) -> None:
    """详情页的条数就地数，不回头拿清单的数字当门面。"""
    page = cgb.faction_changelog("alpha")
    assert (page.total, page.new_count) == (2, 1)
    assert page.version == "阵营包 v1.1（测试）"
    assert [s.title for s in page.sections] == ["军队规则"]
    blank = cgb.faction_changelog("beta")
    assert blank.total == 0 and blank.sections == [] and blank.intro
