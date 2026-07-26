"""tests/test_web_api_core_rules.py — 图鉴核心规则页后端。

覆盖两个端点（GET /codex/rules[/{slug}]）与它们底下的
`web_api/core_rules_browse.py` + `web_api/wiki_blocks.py` 的折叠块支持。

重点盯的是**不会让测试变红、只会让页面看着像对的**那几种错：

  · 折叠里的英文原文自带 `## BATTLEFIELD MORALE` 这类标题，按 `## ` 切小节就会把折叠
    腰斩、后半段英文漏成顶层假小节。实测语料里有 57 处，而**折叠块的个数一个不少**
    （156 个），只看计数完全看不出来。所以这里同时锁三件事：小节数、每节恰好一个折叠、
    每个小节名都带官方节号（假小节没有节号）。
  · 折叠的 summary 有两种文案，14 节写「（英文由 PDF 直提）」——那是 refine 产物丢了
    节号、改用英文 PDF 兜底的那些节。这行字是页面上唯一能看出英文来源的地方，
    归一化成一句固定话术等于把来源披露删掉。
  · 导语里那条「判定规则以英文原文为准」如果没下发，这一页就成了一份看着像官方定稿的
    中文规则书。所以断言导语必须有引用块。
  · 卷没挂上返回 200 + 空列表，在前端长得跟「这一版没有核心规则」一样 → 必须 503。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

import pytest
from fastapi.testclient import TestClient

from web_api import core_rules_browse as crb
from web_api.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent
SECTIONS = REPO_ROOT / "wiki" / "core-rules" / "sections"

needs_wiki = pytest.mark.skipif(
    not (SECTIONS / "16-actions.md").is_file(),
    reason="wiki/core-rules/sections 不存在（未挂载 wiki 卷）")

# 契约（web/src/lib/wiki.ts）字段全集，camelCase。改这里 = 改契约，
# 必须同步 wiki.ts 与 web_api/contract.py，三处一起动。
SUMMARY_KEYS = {"slug", "number", "nameZh", "nameEn", "sectionCount"}
CHAPTER_KEYS = SUMMARY_KEYS | {"intro", "sections"}

# 实测磁盘数（2026-07-26 生成）。数字变了说明离线重跑了生成器且结果变了——
# 先确认是有意的，别顺手对齐成"测试通过"。
EXPECTED_CHAPTERS = 24
EXPECTED_SECTIONS = 156
EXPECTED_EN_FROM_PDF = 14          # summary 写「（英文由 PDF 直提）」的节数

# 官方节号：小节名形如「执行行动 16.01」。折叠里漏出来的英文假小节没有它
_SECTION_NO = re.compile(r"\d{2}\.\d{2}$")

_ZH_DISCLOSURE = "英文原文"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_cache():
    """每个用例前后都清缓存：合成 wiki 与真实 wiki 在同一进程里轮流上场。"""
    crb.clear_cache()
    yield
    crb.clear_cache()


# ── 目录端点（真实语料）────────────────────────────────────────────

@needs_wiki
def test_chapter_list_matches_disk(client: TestClient) -> None:
    r = client.get("/codex/rules")
    assert r.status_code == 200
    items = r.json()["items"]
    on_disk = sorted(p.stem for p in SECTIONS.glob("*.md"))
    assert sorted(i["slug"] for i in items) == on_disk
    assert len(items) == EXPECTED_CHAPTERS
    assert set(items[0]) == SUMMARY_KEYS
    assert not any("_" in k for i in items for k in i)   # 蛇形字段不许漏出去


@needs_wiki
def test_chapter_numbers_are_zero_padded_and_sorted(client: TestClient) -> None:
    """章号保留两位前导零，且列表按章号升序——它同时是排序键。"""
    items = client.get("/codex/rules").json()["items"]
    numbers = [i["number"] for i in items]
    assert numbers == sorted(numbers)
    assert numbers == ["{:02d}".format(n) for n in range(1, EXPECTED_CHAPTERS + 1)]
    for item in items:
        assert item["slug"].startswith(item["number"] + "-")


@needs_wiki
def test_section_counts_sum_to_disk_total(client: TestClient) -> None:
    """各章节数之和 == 全库 156 节。少一节就是悄悄漏了一节规则。"""
    items = client.get("/codex/rules").json()["items"]
    assert sum(i["sectionCount"] for i in items) == EXPECTED_SECTIONS


# ── 章节详情（真实语料）────────────────────────────────────────────

@needs_wiki
def test_chapter_detail_shape(client: TestClient) -> None:
    r = client.get("/codex/rules/16-actions")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == CHAPTER_KEYS
    assert body["number"] == "16" and body["nameZh"] == "行动"
    assert body["nameEn"] == "ACTIONS"
    # 章名取书名号/冒号后的短名，样板前缀（"核心规则第 16 章"）不进字段
    assert "核心规则第" not in body["nameZh"]
    assert len(body["sections"]) == body["sectionCount"] == 1
    assert body["sections"][0]["title"] == "执行行动 16.01"


@needs_wiki
def test_every_section_has_exactly_one_english_fold() -> None:
    """156 节，每节恰好一个官方英文原文折叠块。

    这条同时是「按 `## ` 切小节没有腰斩折叠」的回归锚：折叠里的英文自带 `## ` 标题，
    切分不认折叠深度时，被腰斩的那一节仍会剩下 1 个折叠块（个数骗人），
    但会多出一堆没有节号的假小节——所以下一条用例连节号一起查。
    """
    total = 0
    for summary in crb.list_chapters():
        chapter = crb.chapter_detail(summary.slug)
        assert len(chapter.sections) == summary.section_count
        for section in chapter.sections:
            total += 1
            folds = [b for b in section.blocks if b.t == "details"]
            assert len(folds) == 1, (summary.slug, section.title, len(folds))
            assert folds[0].blocks, (summary.slug, section.title, "折叠是空的")
    assert total == EXPECTED_SECTIONS


@needs_wiki
def test_every_section_title_carries_official_number() -> None:
    """每个小节名都以官方节号收尾，且全库唯一。

    折叠里漏出来的英文假小节（BATTLEFIELD MORALE / RULES APPENDIX / SEE ALSO…）
    没有节号——这条断言就是拿它们当靶子的。
    """
    numbers: List[str] = []
    for summary in crb.list_chapters():
        for section in crb.chapter_detail(summary.slug).sections:
            m = _SECTION_NO.search(section.title.strip())
            assert m is not None, (summary.slug, section.title)
            # 节号的章部分必须与所在章一致（配错章比没有节号更难发现）
            assert m.group(0).split(".")[0] == summary.number
            numbers.append(m.group(0))
    assert len(set(numbers)) == len(numbers) == EXPECTED_SECTIONS


@needs_wiki
def test_english_source_disclosure_survives_transport() -> None:
    """折叠标签两种文案都要原样保留：14 节的英文是从英文 PDF 直提兜底来的。

    归一化成一句「官方英文原文」页面上就再也看不出这 14 节的英文另有来源。
    """
    variants: dict = {}
    for summary in crb.list_chapters():
        for section in crb.chapter_detail(summary.slug).sections:
            for fold in (b for b in section.blocks if b.t == "details"):
                variants[fold.summary] = variants.get(fold.summary, 0) + 1
    assert sum(variants.values()) == EXPECTED_SECTIONS
    from_pdf = {k: v for k, v in variants.items() if "PDF 直提" in k}
    assert sum(from_pdf.values()) == EXPECTED_EN_FROM_PDF, variants
    assert len(variants) == 2, variants          # 只该有这两种文案


@needs_wiki
def test_intro_carries_the_honest_disclosure(client: TestClient) -> None:
    """导语必须下发且带引用块——那条「判定规则以英文原文为准」在里面。

    丢了它，这一页看着就是一份官方中文规则定稿，而正文其实是 PDF 文本层直提。
    """
    for summary in crb.list_chapters():
        chapter = crb.chapter_detail(summary.slug)
        assert chapter.intro, summary.slug
        quotes = [b for b in chapter.intro if b.t == "quote"]
        assert quotes, (summary.slug, "导语没有引用块")
        text = "".join(sp.s for q in quotes for sp in q.inline if hasattr(sp, "s"))
        assert _ZH_DISCLOSURE in text, (summary.slug, text[:80])
    body = client.get("/codex/rules/16-actions").json()
    assert any(b["t"] == "quote" for b in body["intro"])


@needs_wiki
@pytest.mark.parametrize("slug", ["99-nope", "16-actions/../../etc", "../index",
                                  "16actions", "16-Actions"])
def test_unknown_or_traversal_slug_404(client: TestClient, slug: str) -> None:
    """未知 slug 与目录穿越一律 404（形态先卡正则，resolve 归属再兜一次）。"""
    r = client.get("/codex/rules/{}".format(slug))
    assert r.status_code == 404, (slug, r.status_code)


@needs_wiki
def test_empty_slug_is_not_found() -> None:
    """空 slug 走函数层断言：`GET /codex/rules/` 会被 FastAPI 重定向到目录端点，
    到不了这个分支，但内部调用可能传进空串。"""
    with pytest.raises(crb.NotFound):
        crb.chapter_detail("")


# ── 折叠块 tokenizer（合成语料）────────────────────────────────────

_FOLD_PAGE = """---
id: core-rules-99
name_zh: 核心规则第 99 章《测试》
name_en: 'Core Rules 99: TEST'
type: core-rule
---

导语一句话。

> 判定规则以英文原文为准。

## 测试小节 99.01

中文正文。

<details>
<summary>官方英文原文</summary>

English body.

## LEAKY HEADING

Still inside the fold.

</details>

## 第二节 99.02

第二节中文。

<details>
<summary>官方英文原文（英文由 PDF 直提）</summary>

Second English body.
</details>
"""


@pytest.fixture
def fake_rules(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "wiki" / "core-rules" / "sections"
    root.mkdir(parents=True)
    (root / "99-test.md").write_text(_FOLD_PAGE, encoding="utf-8")
    monkeypatch.setattr(crb, "SECTIONS_DIR", root)
    crb.clear_cache()
    return root


def test_heading_inside_fold_does_not_split_sections(fake_rules: Path) -> None:
    """折叠里的 `## LEAKY HEADING` 不许把小节切开，也不许漏成顶层假小节。

    这是本轮真踩到的坑：核心规则英文原文自带 `## ` 标题，实测 57 处。
    """
    chapter = crb.chapter_detail("99-test")
    assert [s.title for s in chapter.sections] == ["测试小节 99.01", "第二节 99.02"]
    fold = [b for b in chapter.sections[0].blocks if b.t == "details"][0]
    inner = [b for b in fold.blocks if b.t == "h"]
    # 那个标题应当留在折叠**内部**，当成折叠里的小标题渲染
    assert [h.text for h in inner] == ["LEAKY HEADING"]
    tail = [b for b in fold.blocks if b.t == "p"]
    assert any("Still inside the fold." in
               "".join(sp.s for sp in b.inline if hasattr(sp, "s")) for b in tail)


def test_fold_summary_variants_preserved(fake_rules: Path) -> None:
    chapter = crb.chapter_detail("99-test")
    summaries = [b.summary for s in chapter.sections for b in s.blocks
                 if b.t == "details"]
    assert summaries == ["官方英文原文", "官方英文原文（英文由 PDF 直提）"]


def test_intro_is_separate_from_sections(fake_rules: Path) -> None:
    chapter = crb.chapter_detail("99-test")
    assert [b.t for b in chapter.intro] == ["p", "quote"]
    # 导语不该混进任何小节里
    assert all(b.t != "quote" or "判定规则" not in
               "".join(sp.s for sp in b.inline if hasattr(sp, "s"))
               for s in chapter.sections for b in s.blocks)


def test_missing_dir_returns_503_not_empty_list(client: TestClient, tmp_path,
                                               monkeypatch) -> None:
    """卷没挂上 → 503。200 + 空列表 = 告诉用户「这一版没有核心规则」。"""
    monkeypatch.setattr(crb, "SECTIONS_DIR", tmp_path / "nope")
    crb.clear_cache()
    r = client.get("/codex/rules")
    assert r.status_code == 503
    assert "挂载" in r.json()["detail"]
    assert client.get("/codex/rules/16-actions").status_code == 404  # 目录没了 → 查无此章


def test_empty_dir_is_breakage(tmp_path, monkeypatch) -> None:
    """目录在、里面没有章节 = 产物残缺，走 503。"""
    root = tmp_path / "wiki" / "core-rules" / "sections"
    root.mkdir(parents=True)
    monkeypatch.setattr(crb, "SECTIONS_DIR", root)
    crb.clear_cache()
    with pytest.raises(crb.WikiUnavailable):
        crb.list_chapters()


def test_page_without_sections_is_breakage(fake_rules: Path) -> None:
    """一节都没切出来 = 页被截断，走 503；不是"这一章没有内容"。"""
    (fake_rules / "99-test.md").write_text(
        "---\nid: x\nname_zh: 空章\nname_en: EMPTY\n---\n\n只有导语。\n",
        encoding="utf-8")
    crb.clear_cache()
    with pytest.raises(crb.WikiUnavailable) as exc:
        crb.chapter_detail("99-test")
    assert "一节都没有" in str(exc.value)


def test_corrupt_page_without_frontmatter_returns_503(fake_rules: Path) -> None:
    (fake_rules / "99-test.md").write_text("没有 frontmatter 的半截文件\n",
                                           encoding="utf-8")
    crb.clear_cache()
    with pytest.raises(crb.WikiUnavailable) as exc:
        crb.chapter_detail("99-test")
    assert "frontmatter" in str(exc.value)


def test_error_detail_does_not_leak_absolute_path(tmp_path, monkeypatch) -> None:
    """报错信息用仓库相对路径，别把服务器目录结构吐进 HTTP 响应。"""
    monkeypatch.setattr(crb, "SECTIONS_DIR", tmp_path / "wiki" / "nope")
    crb.clear_cache()
    with pytest.raises(crb.WikiUnavailable) as exc:
        crb.list_chapters()
    assert str(tmp_path) not in str(exc.value)


def test_cache_invalidates_on_file_change(fake_rules: Path) -> None:
    """离线重跑生成器后不必重启 API：(mtime_ns, size) 一变就重读。

    注意判据里有 size：等长改写 + 同一时钟刻度内落盘是骗不过缓存的。真实场景下
    重跑生成器既改内容长度也隔着秒级时间，所以这条约束够用——但别拿等长改写写测试。
    """
    assert crb.chapter_detail("99-test").name_zh == "测试"
    page = fake_rules / "99-test.md"
    page.write_text(_FOLD_PAGE.replace("《测试》", "《改了名字的章》"), encoding="utf-8")
    assert crb.chapter_detail("99-test").name_zh == "改了名字的章"
