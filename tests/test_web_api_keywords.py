"""tests/test_web_api_keywords.py — 图鉴词条页后端（GET /codex/keywords[/{slug}]）。

覆盖：索引 200 且条数对得上、三档分布、详情反查表非空、未知 slug 404、
载荷缺失/损坏走 503（**不是**空列表）、响应键名是 camelCase 全集、缓存按 mtime 失效。

为什么要逐字段比对键集合而不是「断言两个键存在」：契约的价值在于前端 TS 类型和后端
出参**一字不差**。少一个字段前端编译不过还算好，多一个字段（比如索引页把 weapons
也传了）没人会发现——只是每次开页白传 300KB。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from web_api import keywords as kw
from web_api.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = REPO_ROOT / "wiki" / "indexes" / "keywords.json"

needs_payload = pytest.mark.skipif(
    not PAYLOAD.exists(), reason="wiki/indexes/keywords.json 不存在")

# 契约（web/src/lib/keywords.ts）的字段全集，camelCase。改这里 = 改契约，
# 必须同步 keywords.ts 与 web_api/contract.py，三处一起动。
SUMMARY_KEYS = {
    "slug", "base", "nameZh", "group", "section", "quickrefZh", "params",
    "engine", "rulePage", "ruleSection", "ruleSlug", "currentWeapons",
    "totalWeapons", "currentUnits", "totalUnits",
}
DETAIL_KEYS = SUMMARY_KEYS | {"weapons"}

# 实测（2026-07-27）：46 条里 33 条能落到核心规则正文，缺的 13 条**全部**是单位特有
# 词条（规则正文写在各自兵牌上，核心规则里本来就没有）。这两个数是"跳链没断"的对账锚：
# 掉下去说明 wiki/core-rules 少了章节页或配对键漂了，而页面上只会安静地少几个按钮。
EXPECTED_WITH_RULE_LINK = 33

# 实测分布（11 版 46 条）。数字变了说明离线生成器重跑且结果变了——先确认是有意的
# （换版 / 换库）再改这里，别顺手对齐成"测试通过"。
EXPECTED_TOTAL = 46
EXPECTED_GROUPS = {"universal": 32, "transitional": 1, "unit-specific": 13}


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


# ── 索引端点 ──────────────────────────────────────────────────────

@needs_payload
def test_keyword_index_returns_all_entries(client: TestClient) -> None:
    r = client.get("/codex/keywords")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == EXPECTED_TOTAL
    # 和载荷本身对账：端点不许在传输路上悄悄少条目
    raw = json.loads(PAYLOAD.read_text(encoding="utf-8"))["items"]
    assert [i["slug"] for i in items] == [i["slug"] for i in raw]


@needs_payload
def test_keyword_index_group_distribution(client: TestClient) -> None:
    """三档分布。混着列会骗读者，所以分档本身就是契约的一部分。"""
    items = client.get("/codex/keywords").json()["items"]
    tally = {}
    for it in items:
        tally[it["group"]] = tally.get(it["group"], 0) + 1
    assert tally == EXPECTED_GROUPS


@needs_payload
def test_keyword_index_fields_are_exact_camelcase_set(client: TestClient) -> None:
    """每一行的键集合 == 契约字段全集，不多不少。

    多出 weapons 就是索引页白传反查表；少一个就是前端 TS 拿到 undefined。
    """
    items = client.get("/codex/keywords").json()["items"]
    for it in items:
        assert set(it) == SUMMARY_KEYS, it.get("slug")
    # 顺带钉死：蛇形字段名一个都不许漏出去
    assert not any(k for it in items for k in it if "_" in k)


# ── 规则正文跳链（词条页「查看正文」的落点）─────────────────────────

@needs_payload
def test_rule_link_coverage_and_who_is_missing(client: TestClient) -> None:
    """33/46 有落点，缺的 13 条全是单位特有词条——不是"链接坏了"，是它们真没有。

    只断言"字段存在"抓不到任何东西：ruleSlug 全 None 时字段照样在，页面照样渲染，
    只是一个「查看正文」按钮都没有。所以这里锁数量 + 锁缺的是谁。
    """
    items = client.get("/codex/keywords").json()["items"]
    linked = [i for i in items if i["ruleSlug"]]
    assert len(linked) == EXPECTED_WITH_RULE_LINK
    assert {i["group"] for i in items if not i["ruleSlug"]} == {"unit-specific"}
    # 成对：只有节号没有章节页的链接无处可去，反之节号缺了就不知道滚到哪一节
    for it in items:
        assert bool(it["ruleSection"]) == bool(it["ruleSlug"]), it["slug"]


@needs_payload
def test_rule_link_points_at_a_real_section(client: TestClient) -> None:
    """落点必须真能翻到：章节页取得到，且那一章里确实有这个节号。

    这条是防死链的机械对账——「按钮点了跳过去什么都没有」在页面上看着只是"没滚动"。
    """
    items = client.get("/codex/keywords").json()["items"]
    linked = [i for i in items if i["ruleSlug"]]
    chapters: dict = {}
    for it in linked:
        slug = it["ruleSlug"]
        if slug not in chapters:
            r = client.get("/codex/rules/{}".format(slug))
            assert r.status_code == 200, (it["slug"], slug)
            chapters[slug] = {s["number"] for s in r.json()["sections"]}
        assert it["ruleSection"] in chapters[slug], (it["slug"], it["ruleSection"])


@needs_payload
def test_rule_link_survives_missing_quickref_section(client: TestClient) -> None:
    """速查表漏印节号的词条照样有落点——靠官方英文名配回，不是按顺序推出来的。

    PISTOL 的 section 是 null（速查表没印），但核心规则 24.27 确实是它。
    """
    detail = client.get("/codex/keywords/pistol").json()
    assert detail["section"] is None
    assert detail["ruleSection"] == "24.27"
    assert detail["ruleSlug"] == "24-core-abilities"


@needs_payload
def test_unit_specific_keyword_has_no_rule_link(client: TestClient) -> None:
    """单位特有词条诚实留空，不许拿 rulePage 或章节页凑一个链接出来。"""
    detail = client.get("/codex/keywords/ctan-power").json()
    assert detail["group"] == "unit-specific"
    assert detail["ruleSection"] is None and detail["ruleSlug"] is None


# ── 详情端点 ──────────────────────────────────────────────────────

@needs_payload
def test_keyword_detail_has_reverse_lookup(client: TestClient) -> None:
    """RAPID FIRE：反查表非空，且每行都带携带该武器的单位。

    反查（哪些武器带这个词条）是词条页存在的理由——兵牌页只能从武器看词条。
    """
    r = client.get("/codex/keywords/rapid-fire")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == DETAIL_KEYS
    assert body["base"] == "RAPID FIRE" and body["group"] == "universal"
    assert body["weapons"], "rapid-fire 反查表不该为空"
    assert all(set(w) == {"name", "units"} for w in body["weapons"])
    assert any(w["units"] for w in body["weapons"])
    # 计数字段与反查表口径一致（反查表按现役口径给）
    assert body["currentWeapons"] == len(body["weapons"])


@needs_payload
def test_keyword_detail_unknown_slug_404(client: TestClient) -> None:
    r = client.get("/codex/keywords/no-such-keyword-xyz")
    assert r.status_code == 404
    assert "词条" in r.json()["detail"]


@needs_payload
def test_keyword_detail_nullable_fields_stay_null(client: TestClient) -> None:
    """速查表漏印节号的条目 section 必须是 null，不许编一个像样的号码出来。"""
    items = client.get("/codex/keywords").json()["items"]
    missing = [i for i in items if i["section"] is None]
    assert missing, "载荷里本应有漏印节号的条目"
    detail = client.get("/codex/keywords/{}".format(missing[0]["slug"])).json()
    assert detail["section"] is None


# ── 载荷缺失 / 损坏：503，而不是空列表 ────────────────────────────

def test_missing_payload_returns_503(client: TestClient, tmp_path,
                                     monkeypatch) -> None:
    """卷没挂上 → 503。返回 200 + 空列表等于告诉用户「这一版没有词条」。"""
    monkeypatch.setattr(kw, "PAYLOAD_PATH", tmp_path / "nope.json")
    kw.clear_cache()
    assert client.get("/codex/keywords").status_code == 503
    r = client.get("/codex/keywords/rapid-fire")
    assert r.status_code == 503          # 缺资产优先于 404，别报成"词条不存在"
    assert "wiki_engine.keyword_index" in r.json()["detail"]   # 带修复办法


@pytest.mark.parametrize("blob", [
    "{ not json",                        # 半截文件（写盘中断）
    '{"generatedBy": "x"}',              # 缺 items
    '{"generatedBy": "x", "items": {}}',  # items 不是数组
    '{"generatedBy": "x", "items": []}',  # 空壳：生成器跑挂了，不是"这版没词条"
])
def test_corrupt_payload_returns_503(client: TestClient, tmp_path, monkeypatch,
                                     blob: str) -> None:
    bad = tmp_path / "keywords.json"
    bad.write_text(blob, encoding="utf-8")
    monkeypatch.setattr(kw, "PAYLOAD_PATH", bad)
    kw.clear_cache()
    assert client.get("/codex/keywords").status_code == 503


def test_error_detail_does_not_leak_absolute_path(tmp_path) -> None:
    """报错信息用仓库相对路径，别把服务器目录结构吐进 HTTP 响应。"""
    with pytest.raises(kw.KeywordPayloadError) as exc:
        kw.load_items(tmp_path / "keywords.json")
    assert str(tmp_path) not in str(exc.value)


# ── 缓存 ──────────────────────────────────────────────────────────

def _payload(*slugs: str) -> str:
    items = [{"slug": s, "base": s.upper(), "nameZh": s, "group": "universal",
              "section": None, "quickrefZh": None, "params": [],
              "engine": "仅标注", "rulePage": None, "currentWeapons": 0,
              "totalWeapons": 0, "currentUnits": 0, "totalUnits": 0,
              "weapons": []} for s in slugs]
    return json.dumps({"generatedBy": "test", "items": items}, ensure_ascii=False)


def test_cache_invalidates_on_file_change(tmp_path) -> None:
    """离线重跑生成器后不必重启 API：(mtime, size) 一变就重读。"""
    p = tmp_path / "keywords.json"
    p.write_text(_payload("a"), encoding="utf-8")
    kw.clear_cache()
    assert [i["slug"] for i in kw.load_items(p)] == ["a"]
    # 同一路径写第二份（长度不同，mtime 也变）
    p.write_text(_payload("a", "b"), encoding="utf-8")
    assert [i["slug"] for i in kw.load_items(p)] == ["a", "b"]


def test_cache_reuses_parsed_object(tmp_path) -> None:
    """文件没动就不重新解析：364KB 每请求解一遍是纯浪费。"""
    p = tmp_path / "keywords.json"
    p.write_text(_payload("a"), encoding="utf-8")
    kw.clear_cache()
    assert kw.load_items(p) is kw.load_items(p)


def test_list_keywords_strips_weapons(tmp_path) -> None:
    """索引层剥 weapons 是显式行为，不靠 Pydantic 的 extra=ignore 兜底。"""
    p = tmp_path / "keywords.json"
    p.write_text(_payload("a"), encoding="utf-8")
    kw.clear_cache()
    assert "weapons" not in kw.list_keywords(p)[0]
    assert "weapons" in kw.get_keyword("a", p)
    assert kw.get_keyword("nope", p) is None
