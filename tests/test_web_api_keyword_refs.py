"""tests/test_web_api_keyword_refs.py — 兵牌词条 → 官方解释的解析层。

用**真实库与真实 wiki 产物**测，不用捏造的 fixture：这一层的全部风险都在
「真源里到底查不查得到」，拿自己造的两条数据是测不出来的。

覆盖四类断言：
  ① 三个点名单位的真实词条（艾弗森刺客 4 条、强征小队、危机火刃战斗服）
  ② 中英两侧解析出同一批 slug（跨语言身份一致，否则中英各说各话）
  ③ **全库对账**：80 个英文 token × 中英两侧 = 160 次解析，查不到身份的必须是 0；
     查不到解释的必须**全部**是单位特有词条（它们的规则本来就不在核心规则里）
  ④ 诚实降级：查不到的词条只有 text，绝不带 brief
"""
from __future__ import annotations

import collections
import json
import sqlite3
from pathlib import Path

import pytest

from web_api.keyword_refs import resolve, resolve_all, split_tokens

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "db" / "wh40k.sqlite"
PAYLOAD = REPO_ROOT / "wiki" / "indexes" / "keywords.json"
SECTIONS = REPO_ROOT / "wiki" / "core-rules" / "sections"

needs_assets = pytest.mark.skipif(
    not (DB_PATH.exists() and PAYLOAD.exists() and SECTIONS.is_dir()),
    reason="需要 db/wh40k.sqlite + wiki/indexes/keywords.json + wiki/core-rules/sections/")

# 实测口径（2026-07-27）。数字变了先确认是换库/换版，别顺手对齐成"测试通过"。
EXPECTED_TOKENS = 80            # 全库武器 keywords_json 拆出的去重 token 数
EXPECTED_NO_BRIEF = 13          # 查得到身份但核心规则无正文的词条（全部是单位特有）
EXPECTED_SECTIONS = 156         # 核心规则 24 章的小节数，且节号两两不同
EXPECTED_ZH_FORMS = 230         # 80 个 token 全都有中文名，其中 50 个带档位 ×3 个人写形态


# ── 拆分 ─────────────────────────────────────────────────────────────

def test_split_tokens_handles_comma_strings() -> None:
    """库里一格常是逗号串；中英文逗号都要认，空白压平。"""
    assert split_tokens(["heavy, devastating wounds"]) == [
        "heavy", "devastating wounds"]
    assert split_tokens(["针对步兵3+，手枪"]) == ["针对步兵3+", "手枪"]
    assert split_tokens([" rapid  fire 3 "]) == ["rapid fire 3"]
    assert split_tokens([]) == [] and split_tokens(None) == []


# ── 点名样本 ──────────────────────────────────────────────────────────

@needs_assets
def test_eversor_assassin_four_keywords_resolve() -> None:
    """艾弗森刺客处刑者手枪的 4 个词条：中文名、节号、章节页、官方正文全都查得到。"""
    from web_api import codex

    card = codex.unit_card(DB_PATH, "000000872", lang="zh")
    assert card is not None
    gun = next(w for w in card.ranged if w.name == "处刑者手枪")
    assert [k.text for k in gun.kw] == ["针对步兵3+", "手枪", "精准", "连击3"]
    assert [k.slug for k in gun.kw] == [
        "anti-infantry", "pistol", "precision", "sustained-hits"]
    assert [k.section for k in gun.kw] == ["24.03", "24.27", "24.28", "24.36"]
    assert all(k.rule_slug == "24-core-abilities" for k in gun.kw)
    # 解释是官方中文正文的逐字摘录，不是概括
    briefs = {k.slug: k.brief for k in gun.kw}
    assert "未修正结果为 Y+ 的致伤掷骰将造成暴击致伤" in briefs["anti-infantry"]
    assert "那次攻击将造成 X 数量的额外命中" in briefs["sustained-hits"]


@needs_assets
def test_pistol_section_recovered_by_english_name() -> None:
    """PISTOL 在 keywords.json 里 section 是 null（速查表漏印），靠官方英文名配回 24.27。

    这条是「链接逻辑必须容忍 section 缺失」的正面用例：不是不给链接，
    而是有第二条**可验证**的配对路径；配不上才留空，绝不按顺序推断编号。
    """
    raw = {i["base"]: i for i in json.loads(
        PAYLOAD.read_text(encoding="utf-8"))["items"]}
    assert raw["PISTOL"]["section"] is None      # 前提：载荷里真的没有节号
    ref = resolve("手枪")
    assert (ref.section, ref.rule_slug) == ("24.27", "24-core-abilities")
    assert "[手枪]和[近距离]在所有规则中都被视为同一个规则" in (ref.brief or "")


@needs_assets
def test_zh_and_en_tokens_resolve_to_same_identity() -> None:
    """同一个词条中英两种写法必须落到同一个 slug/section——两套解析必然打架。"""
    for zh, en in (("针对步兵3+", "ANTI-INFANTRY 3+"), ("连击3", "sustained hits 3"),
                   ("精准", "precision"), ("双联", "TWIN-LINKED")):
        a, b = resolve(zh), resolve(en)
        assert a.slug == b.slug and a.section == b.section, (zh, en)
        assert a.text == zh and b.text == en          # 显示文本各自原样，不互相覆盖


@needs_assets
def test_zh_parameterised_keyword_forms_resolve() -> None:
    """中文侧的档位写法全都要认——**技能正文里的人写形态和对照表里的紧凑写法不一样**。

    对照表存的是 `速射1`（离线从武器行学来的），而技能正文与核心规则正文里写的是
    `【速射 1】` / `[速射 X]` / 光秃秃的 `速射`。不做归一化的后果很具体：同一个词条
    在武器行能悬停，出现在技能正文里就退成纯文本，页面上看着只像"这条没做"。
    """
    for token in ("速射1", "速射 1", "速射 X", "速射D", "速射", "[速射 1]", "【速射 3】"):
        ref = resolve(token)
        assert (ref.slug, ref.base) == ("rapid-fire", "RAPID FIRE"), token
        assert ref.section == "24.30", token
        assert ref.text == " ".join(token.split())       # 显示文本原样，不被归一化改写

    for token, slug in (("连击 3", "sustained-hits"), ("连击", "sustained-hits"),
                        ("针对步兵 3+", "anti-infantry"), ("热熔 4", "melta"),
                        ("劈砍", "cleave")):
        assert resolve(token).slug == slug, token


@needs_assets
def test_zh_base_stripping_does_not_swallow_a_different_keyword() -> None:
    """`劈砍狠`（DEAD CHOPPY）不能被剥成 `劈砍`（CLEAVE）+ 一个「狠」字。

    档位尾巴只认 ASCII 就是为这条：放开中文尾巴，页面会给出另一条规则的解释，
    而且看上去毫不心虚（有词条名、有官方节号、有正文）。
    """
    assert resolve("劈砍狠").slug == "dead-choppy"
    assert resolve("劈砍").slug == "cleave"
    # 编出来的中文尾巴一律不认，退成纯文本
    for fake in ("速射狠", "精准度", "手枪套"):
        ref = resolve(fake)
        assert (ref.slug, ref.brief) == (None, None), fake


@needs_assets
def test_zh_and_en_agree_on_every_library_keyword() -> None:
    """全库 80 个 token 的中文写法（紧凑 / 带空格 / 去档位 / X 档）逐条与英文侧对账。

    抽查几条证明不了这层——归一化错一处，就有一批词条只在某些页面上能悬停。
    """
    conn = sqlite3.connect(str(DB_PATH))
    try:
        gloss = {en.upper(): zh for en, zh in conn.execute(
            "SELECT term_en, term_zh FROM zh_keyword_glossary")}
        tokens = set()
        for (kj,) in conn.execute("SELECT keywords_json FROM weapons"):
            try:
                items = json.loads(kj or "[]") or []
            except (json.JSONDecodeError, TypeError):
                continue
            tokens.update(t.upper() for t in split_tokens(items))
    finally:
        conn.close()
    assert len(tokens) == EXPECTED_TOKENS

    import re as _re
    checked = 0
    for tok in sorted(tokens):
        zh = gloss.get(tok)
        if not zh:
            continue
        want = resolve(tok)
        assert want.slug, tok
        forms = [zh]
        m = _re.fullmatch(r"([一-鿿]+)([0-9DX+\-]+)", zh)
        if m:                       # 带档位的：补上人写的三种形态
            forms += [m.group(1) + " " + m.group(2), m.group(1), m.group(1) + " X"]
        for form in forms:
            got = resolve(form)
            assert (got.slug, got.section) == (want.slug, want.section), (form, tok)
            checked += 1
    # 中文覆盖面是这条断言的头条数字：变了先查是不是换库，别顺手对齐
    assert checked == EXPECTED_ZH_FORMS


@needs_assets
def test_dice_param_variants_normalize_to_base() -> None:
    """变量档位（D / D6+ / D3）也是档位，不能留在基名里分裂出假词条。"""
    for token in ("RAPID FIRE D", "RAPID FIRE D6+", "RAPID FIRE D3",
                  "SUSTAINED HITS D"):
        ref = resolve(token)
        assert ref.slug in ("rapid-fire", "sustained-hits"), token
        assert ref.section, token


# ── 诚实降级 ──────────────────────────────────────────────────────────

@needs_assets
def test_unknown_token_degrades_to_plain_text() -> None:
    """查不到就只有 text。带出任何 brief 都意味着有人在编解释。"""
    ref = resolve("这不是一个词条")
    assert ref.text == "这不是一个词条"
    assert (ref.slug, ref.base, ref.brief, ref.section, ref.rule_slug) == (
        None, None, None, None, None)


@needs_assets
def test_unit_specific_keyword_has_identity_but_no_rule_text() -> None:
    """单位特有词条：查得到身份与中文名，但核心规则里本来就没有它的正文。"""
    ref = resolve("泡泡炮")
    assert (ref.slug, ref.name_zh, ref.group) == (
        "bubblechukka", "泡泡炮", "unit-specific")
    assert ref.brief is None and ref.section is None and ref.rule_slug is None


# ── 全库对账 ──────────────────────────────────────────────────────────

@needs_assets
def test_whole_library_keyword_coverage() -> None:
    """全库武器词条逐条过一遍解析，报绝对数字。

    「抽查几条通过」证明不了覆盖率——这一层要么全库都查得到，要么就有一批词条
    在某些兵牌上静默退成纯文本，而页面上完全看不出来。
    """
    conn = sqlite3.connect(str(DB_PATH))
    try:
        gloss = {en.upper(): zh for en, zh in conn.execute(
            "SELECT term_en, term_zh FROM zh_keyword_glossary")}
        tokens: collections.Counter = collections.Counter()
        for (kj,) in conn.execute("SELECT keywords_json FROM weapons"):
            try:
                items = json.loads(kj or "[]") or []
            except (json.JSONDecodeError, TypeError):
                continue
            for tok in split_tokens(items):
                tokens[tok.upper()] += 1
    finally:
        conn.close()

    assert len(tokens) == EXPECTED_TOKENS

    unresolved, no_brief = [], set()
    for tok in tokens:
        for text in (tok, gloss.get(tok, tok)):     # 英文侧 + 中文本地化侧
            ref = resolve(text)
            if not ref.slug:
                unresolved.append(text)
            elif not ref.brief:
                no_brief.add(ref.slug)
                # 没正文的，必须是"规则不在核心规则里"，不是"我们没查到"
                assert ref.group == "unit-specific", (text, ref.group)
            else:
                # 有正文就必须有节号与章节页，否则页面上会出现无处可去的引用
                assert ref.section and ref.rule_slug, text

    assert unresolved == []
    assert len(no_brief) == EXPECTED_NO_BRIEF


@needs_assets
def test_section_numbers_are_unique_across_core_rules() -> None:
    """156 节、156 个互不相同的官方节号。

    节号是词条 → 规则页的唯一配对键。真源里出现过一个被 PDF 版面污染的标题
    （'…领袖  24.22/辅助 24.34'），按「第一个节号」取会把它认成 24.22 的重复、
    真正的 24.34 就此消失——而两个页面都照常渲染。这条断言就是那道闸。
    """
    from web_api import keyword_refs

    keyword_refs.clear_cache()
    by_no, _by_en = keyword_refs._sections()
    assert len(by_no) == EXPECTED_SECTIONS
    total = sum(len(c.sections) for c in _all_chapters())
    assert total == EXPECTED_SECTIONS


def _all_chapters():
    from web_api import core_rules_browse as crb
    return [crb.chapter_detail(s.slug) for s in crb.list_chapters()]


@needs_assets
def test_brief_excludes_english_original_fold() -> None:
    """解释只取中文正文；折叠里的英文原文不能混进来（混了就是中英夹杂的一坨）。"""
    ref = resolve("精准")
    assert ref.brief and "PRECISION" not in ref.brief
    assert "Each time" not in ref.brief


@needs_assets
def test_resolve_all_keeps_order_and_count() -> None:
    """一格逗号串 → 逐条 ref，顺序与条数照原样（漏一条页面上看不出来）。"""
    refs = resolve_all(["ANTI-INFANTRY 3+, PISTOL, PRECISION, SUSTAINED HITS 3"])
    assert [r.text for r in refs] == [
        "ANTI-INFANTRY 3+", "PISTOL", "PRECISION", "SUSTAINED HITS 3"]
    assert all(r.slug for r in refs)
