"""wiki_engine/synthesize.py 测试：片段收集、缓存键、faction facts、实体类型推断。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from dataclasses import asdict
from types import SimpleNamespace

from wiki_compile.extract import EntityCandidate
from wiki_compile.pair import Pair
from wiki_engine.models import WikiPage, WikiPageFrontmatter
from wiki_engine.synthesize import (
    _cache_key,
    _infer_entity_type,
    _infer_faction_id,
    _save_cache,
    _verify_numbers,
    build_faction_facts,
    collect_source_fragments,
    synthesize_all,
    synthesize_page,
    SYNTH_PROMPT_VERSION,
)


def _make_fake_client(record: list, body: str = "## 属性表\n合成正文。"):
    """OpenAI 兼容假客户端：记录 messages，返回固定 body。"""
    def create(**kwargs):
        record.append(kwargs["messages"])
        msg = SimpleNamespace(content=body)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])
    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def _write_pairing(path, pairs):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(
        {"pairs": [asdict(p) for p in pairs], "unmatched": []},
        ensure_ascii=False), encoding="utf-8")


class TestInferEntityType:
    def test_detachment(self):
        entity = EntityCandidate(
            book="test", raw_heading="## 空育分队",
            name_zh="空育分队", name_en=None, pages=[1],
        )
        assert _infer_entity_type(entity) == "detachment"

    def test_enhancement(self):
        entity = EntityCandidate(
            book="test", raw_heading="## 纯化装置",
            name_zh="纯化装置（Enhancement）", name_en=None, pages=[1],
        )
        assert _infer_entity_type(entity) == "unit"  # "强化"不在 name_zh 中

    def test_stratagem(self):
        entity = EntityCandidate(
            book="test", raw_heading="## 战略打击",
            name_zh="战略打击", name_en=None, pages=[1],
        )
        assert _infer_entity_type(entity) == "stratagem"

    def test_default_unit(self):
        entity = EntityCandidate(
            book="test", raw_heading="## 火战士队 FIRE WARRIORS",
            name_zh="火战士队", name_en="FIRE WARRIORS", pages=[1],
        )
        assert _infer_entity_type(entity) == "unit"


class TestInferFactionId:
    def test_faction_pack(self):
        fid = _infer_faction_id("Faction Pack Tau Empire")
        assert "tau" in fid.lower()

    def test_chinese_codex(self):
        fid = _infer_faction_id("钛帝国十版CODEX-20251112")
        assert "钛" in fid or "di" in fid.lower()


class TestCollectSourceFragments:
    def test_existing_pages(self, tmp_path):
        refined = tmp_path / "data_refined" / "Test Book"
        refined.mkdir(parents=True)
        (refined / "page_001.md").write_text("# Page 1\ntest content", encoding="utf-8")
        (refined / "page_003.md").write_text("# Page 3\nmore content", encoding="utf-8")

        entity = EntityCandidate(
            book="Test Book", raw_heading="Test Entity",
            name_zh="测试", name_en="TEST", pages=[1, 3],
        )
        fragments = collect_source_fragments(entity, tmp_path / "data_refined")
        assert len(fragments) == 2
        paths = [str(f[0].name) for f in fragments]
        assert "page_001.md" in paths
        assert "page_003.md" in paths

    def test_missing_book_dir(self, tmp_path):
        entity = EntityCandidate(
            book="Nonexistent", raw_heading="X",
            name_zh="X", name_en=None, pages=[1],
        )
        fragments = collect_source_fragments(entity, tmp_path / "data_refined")
        assert fragments == []


class TestCacheKey:
    def test_different_fragments_different_keys(self, tmp_path):
        refined = tmp_path / "data_refined"
        f1 = [(Path("a.md"), "hello"), (Path("b.md"), "world")]
        f2 = [(Path("a.md"), "hello"), (Path("b.md"), "WORLD")]  # different content
        k1 = _cache_key(SYNTH_PROMPT_VERSION, "test/id", f1)
        k2 = _cache_key(SYNTH_PROMPT_VERSION, "test/id", f2)
        assert k1 != k2

    def test_same_fragments_same_key(self):
        f1 = [(Path("a.md"), "hello"), (Path("b.md"), "world")]
        f2 = [(Path("a.md"), "hello"), (Path("b.md"), "world")]
        k1 = _cache_key(SYNTH_PROMPT_VERSION, "test/id", f1)
        k2 = _cache_key(SYNTH_PROMPT_VERSION, "test/id", f2)
        assert k1 == k2


class TestVerifyNumbers:
    def test_no_extra_numbers(self):
        sources = ["M 6 T 3 SV 4+ W 2 LD 7+ OC 2"]
        output = "| M | T | SV | W | LD | OC |\n| 6 | 3 | 4+ | 2 | 7+ | 2 |"
        bad = _verify_numbers(sources, output)
        assert bad == []

    def test_hallucinated_number(self):
        sources = ["M 6 T 3 SV 4+"]
        output = "M 6 T 3 SV 4+ OC 99"  # OC 99 不在输入中
        bad = _verify_numbers(sources, output)
        # "99" is in output but not in sources
        assert len(bad) > 0

    def test_multiple_sources(self):
        s1 = "M 6 T 3"
        s2 = "W 2 OC 1"
        output = "M 6 T 3 W 2 OC 1"
        bad = _verify_numbers([s1, s2], output)
        assert bad == []


class TestSynthesizeAllCrossBook:
    """HIGH #4：跨书同名实体必须各自拿到自己书的源文本。"""

    def test_same_name_entities_use_own_book_fragments(self, tmp_path):
        refined = tmp_path / "data_refined"
        (refined / "Book A").mkdir(parents=True)
        (refined / "Book B").mkdir(parents=True)
        (refined / "Book A" / "page_001.md").write_text(
            "## 火战士队 FIRE WARRIORS\nTOKEN_ALPHA 属性", encoding="utf-8")
        (refined / "Book B" / "page_001.md").write_text(
            "## 火战士队 FIRE WARRIORS\nTOKEN_BETA 属性", encoding="utf-8")

        pairs = [
            Pair(zh="火战士队", en="FIRE WARRIORS",
                 canonical_id="faction-a/units/fire-warriors",
                 faction_id="FA", book="Book A", pages=[1], confidence="exact"),
            Pair(zh="火战士队", en="FIRE WARRIORS",
                 canonical_id="faction-b/units/fire-warriors",
                 faction_id="FB", book="Book B", pages=[1], confidence="exact"),
        ]
        pairing_path = tmp_path / "wiki_build" / "pairing.json"
        _write_pairing(pairing_path, pairs)

        record: list = []
        client = _make_fake_client(record)
        stats = synthesize_all(
            pairing_path=pairing_path,
            refined_root=refined,
            wiki_root=tmp_path / "wiki",
            cache_dir=tmp_path / "cache",
            client=client,
            max_workers=1,
        )
        assert stats["synthesized"] == 2

        user_prompts = ["\n".join(m["content"] for m in msgs) for msgs in record]
        # 两个 job 必须各自拿到自己书的片段，不能都命中 Book A
        assert any("TOKEN_ALPHA" in p for p in user_prompts)
        assert any("TOKEN_BETA" in p for p in user_prompts)


class TestSynthesizeAllCacheRefresh:
    """HIGH #5：缓存命中路径也必须刷新 name_zh/name_en/id 配对元数据。"""

    def test_cache_hit_refreshes_pair_metadata(self, tmp_path):
        refined = tmp_path / "data_refined"
        (refined / "Book A").mkdir(parents=True)
        (refined / "Book A" / "page_001.md").write_text(
            "## 火战士队 FIRE WARRIORS\n属性内容", encoding="utf-8")

        pair = Pair(zh="火战士队", en="FIRE WARRIORS",
                    canonical_id="tau-empire/units/fire-warriors",
                    faction_id="tau-empire", book="Book A", pages=[1],
                    confidence="exact")
        pairing_path = tmp_path / "wiki_build" / "pairing.json"
        _write_pairing(pairing_path, [pair])

        # 预填缓存：陈旧的 name_zh 和 id
        entity = EntityCandidate(book="Book A", raw_heading="火战士队 FIRE WARRIORS",
                                 name_zh="火战士队", name_en="FIRE WARRIORS", pages=[1])
        fragments = collect_source_fragments(entity, refined)
        key = _cache_key(SYNTH_PROMPT_VERSION, pair.canonical_id, fragments)
        stale_fm = WikiPageFrontmatter(
            id="stale/old-id", name_zh="旧名字", name_en="FIRE WARRIORS",
            faction="tau-empire", type="unit")
        cache_dir = tmp_path / "cache"
        _save_cache(cache_dir, key, WikiPage(fm=stale_fm, body="缓存正文"))

        wiki_root = tmp_path / "wiki"
        stats = synthesize_all(
            pairing_path=pairing_path,
            refined_root=refined,
            wiki_root=wiki_root,
            cache_dir=cache_dir,
            client=None,  # 无 LLM——只能走缓存
            max_workers=1,
        )
        assert stats["cached"] == 1

        written = list(wiki_root.rglob("*.md"))
        assert len(written) == 1
        page = WikiPage.from_markdown(written[0].read_text(encoding="utf-8"))
        assert page.fm.id == pair.canonical_id
        assert page.fm.name_zh == "火战士队"
        assert page.fm.name_en == "FIRE WARRIORS"


class TestSynthesizeAllPathConflict:
    """HIGH #6：两个 job 解析到同一文件路径时，跳过并计入 stats，不静默覆盖。"""

    def test_duplicate_target_path_skipped_and_counted(self, tmp_path):
        refined = tmp_path / "data_refined"
        (refined / "Book A").mkdir(parents=True)
        # 两个实体：中文名不同但英文名相同 → entity_page_path 相同
        (refined / "Book A" / "page_001.md").write_text(
            "## 火战士 FIRE WARRIORS\n内容一", encoding="utf-8")
        (refined / "Book A" / "page_002.md").write_text(
            "## 火战士队 FIRE WARRIORS\n内容二", encoding="utf-8")

        pairs = [
            Pair(zh="火战士", en="FIRE WARRIORS",
                 canonical_id="fa/units/fire-warriors-1",
                 faction_id="FA", book="Book A", pages=[1], confidence="exact"),
            Pair(zh="火战士队", en="FIRE WARRIORS",
                 canonical_id="fa/units/fire-warriors-2",
                 faction_id="FA", book="Book A", pages=[2], confidence="exact"),
        ]
        pairing_path = tmp_path / "wiki_build" / "pairing.json"
        _write_pairing(pairing_path, pairs)

        record: list = []
        client = _make_fake_client(record)
        wiki_root = tmp_path / "wiki"
        stats = synthesize_all(
            pairing_path=pairing_path,
            refined_root=refined,
            wiki_root=wiki_root,
            cache_dir=tmp_path / "cache",
            client=client,
            max_workers=2,
        )
        assert stats.get("path_conflicts", 0) == 1
        # 只写出一个文件
        written = list(wiki_root.rglob("*.md"))
        assert len(written) == 1


class TestVerifyWarnFlag:
    """MEDIUM #11：_verify_numbers 命中时结果写入 frontmatter verify_warn。"""

    def test_hallucinated_number_sets_verify_warn(self, tmp_path):
        entity = EntityCandidate(book="Book A", raw_heading="X UNIT",
                                 name_zh="X", name_en="UNIT", pages=[1])
        fragments = [(Path("page_001.md"), "M 6 T 3")]
        client = _make_fake_client([], body="M 6 T 3 OC 99")  # 99 是幻觉数字
        page = synthesize_page(client, entity, None, fragments, {})
        assert page is not None
        assert page.fm.verify_warn is True

    def test_clean_output_no_verify_warn(self, tmp_path):
        entity = EntityCandidate(book="Book A", raw_heading="X UNIT",
                                 name_zh="X", name_en="UNIT", pages=[1])
        fragments = [(Path("page_001.md"), "M 6 T 3")]
        client = _make_fake_client([], body="M 6 T 3")
        page = synthesize_page(client, entity, None, fragments, {})
        assert page is not None
        assert page.fm.verify_warn is False


class TestSynthesizeAllJoinByBookPages:
    """问题1：实体联结键必须是 (book, pages)，不能拿规范名精确匹配原文大写名。"""

    def test_canonical_en_joins_uppercase_heading_via_book_pages(self, tmp_path):
        """pair.en 是 Wahapedia 规范名，refined 标题是全大写原文 → 仍能联结。"""
        refined = tmp_path / "data_refined"
        (refined / "Book A").mkdir(parents=True)
        (refined / "Book A" / "page_001.md").write_text(
            "## VESPID STINGWINGS\nTOKEN_VESPID 属性", encoding="utf-8")

        pair = Pair(zh=None, en="Vespid Stingwings",
                    canonical_id="000000427", faction_id="TAU",
                    book="Book A", pages=[1], confidence="exact")
        pairing_path = tmp_path / "wiki_build" / "pairing.json"
        _write_pairing(pairing_path, [pair])

        record: list = []
        client = _make_fake_client(record)
        stats = synthesize_all(
            pairing_path=pairing_path,
            refined_root=refined,
            wiki_root=tmp_path / "wiki",
            cache_dir=tmp_path / "cache",
            client=client,
            max_workers=1,
        )
        assert stats["skipped"] == 0
        assert stats["synthesized"] == 1
        user_prompts = ["\n".join(m["content"] for m in msgs) for msgs in record]
        assert any("TOKEN_VESPID" in p for p in user_prompts)

    def test_name_fallback_when_pages_drift(self, tmp_path):
        """pages 不一致（extract 重跑后漂移）时，归一化名字在同书内兜底匹配。"""
        refined = tmp_path / "data_refined"
        (refined / "Book A").mkdir(parents=True)
        (refined / "Book A" / "page_001.md").write_text(
            "## 维斯普刺翼蜂 VESPID STINGWINGS\nTOKEN_FALLBACK 属性", encoding="utf-8")

        # pair.pages 记的是旧的 [1, 2]，实际 extract 只有 [1]
        pair = Pair(zh="维斯普刺翼蜂", en="Vespid Stingwings",
                    canonical_id="000000427", faction_id="TAU",
                    book="Book A", pages=[1, 2], confidence="exact")
        pairing_path = tmp_path / "wiki_build" / "pairing.json"
        _write_pairing(pairing_path, [pair])

        record: list = []
        client = _make_fake_client(record)
        stats = synthesize_all(
            pairing_path=pairing_path,
            refined_root=refined,
            wiki_root=tmp_path / "wiki",
            cache_dir=tmp_path / "cache",
            client=client,
            max_workers=1,
        )
        assert stats["synthesized"] == 1
        assert stats["skipped"] == 0

    def test_name_fallback_does_not_cross_books(self, tmp_path):
        """兜底名字匹配限定同书：别的书里同名实体不能顶上来。"""
        refined = tmp_path / "data_refined"
        (refined / "Book B").mkdir(parents=True)
        (refined / "Book B" / "page_001.md").write_text(
            "## VESPID STINGWINGS\n别书内容", encoding="utf-8")

        pair = Pair(zh=None, en="Vespid Stingwings",
                    canonical_id="000000427", faction_id="TAU",
                    book="Book A", pages=[1], confidence="exact")
        pairing_path = tmp_path / "wiki_build" / "pairing.json"
        _write_pairing(pairing_path, [pair])

        stats = synthesize_all(
            pairing_path=pairing_path,
            refined_root=refined,
            wiki_root=tmp_path / "wiki",
            cache_dir=tmp_path / "cache",
            client=_make_fake_client([]),
            max_workers=1,
        )
        assert stats["synthesized"] == 0
        assert stats["skipped"] == 1


class TestFactionResolution:
    """问题2：fm.faction 应来自 pair.faction_id 的中文阵营名，而非书名 slug。"""

    def _run(self, tmp_path, faction_id, cache_page=None):
        refined = tmp_path / "data_refined"
        (refined / "钛帝国十版-20251112").mkdir(parents=True)
        (refined / "钛帝国十版-20251112" / "page_001.md").write_text(
            "## 火战士队 FIRE WARRIORS\n属性内容", encoding="utf-8")
        pair = Pair(zh="火战士队", en="Fire Warriors",
                    canonical_id="000000401", faction_id=faction_id,
                    book="钛帝国十版-20251112", pages=[1], confidence="exact")
        pairing_path = tmp_path / "wiki_build" / "pairing.json"
        _write_pairing(pairing_path, [pair])

        cache_dir = tmp_path / "cache"
        client = _make_fake_client([])
        if cache_page is not None:
            entity = EntityCandidate(
                book="钛帝国十版-20251112", raw_heading="火战士队 FIRE WARRIORS",
                name_zh="火战士队", name_en="FIRE WARRIORS", pages=[1])
            fragments = collect_source_fragments(entity, refined)
            key = _cache_key(SYNTH_PROMPT_VERSION, pair.canonical_id, fragments)
            _save_cache(cache_dir, key, cache_page)
            client = None  # 只能走缓存

        wiki_root = tmp_path / "wiki"
        stats = synthesize_all(
            pairing_path=pairing_path,
            refined_root=refined,
            wiki_root=wiki_root,
            cache_dir=cache_dir,
            client=client,
            max_workers=1,
        )
        written = list(wiki_root.rglob("*.md"))
        return stats, written

    def test_faction_id_maps_to_chinese_name(self, tmp_path):
        stats, written = self._run(tmp_path, faction_id="TAU")
        assert stats["synthesized"] == 1
        assert len(written) == 1
        page = WikiPage.from_markdown(written[0].read_text(encoding="utf-8"))
        assert page.fm.faction == "钛帝国"
        assert "钛帝国" in str(written[0])
        assert "20251112" not in str(written[0])  # 不再是书名 slug 目录

    def test_missing_faction_id_falls_back_to_book_inference(self, tmp_path):
        stats, written = self._run(tmp_path, faction_id="")
        assert stats["synthesized"] == 1
        page = WikiPage.from_markdown(written[0].read_text(encoding="utf-8"))
        from wiki_engine.synthesize import _infer_faction_id
        assert page.fm.faction == _infer_faction_id("钛帝国十版-20251112")

    def test_cache_hit_refreshes_faction_and_tags(self, tmp_path):
        stale_fm = WikiPageFrontmatter(
            id="stale/old-id", name_zh="火战士队", name_en="FIRE WARRIORS",
            faction="钛帝国十版-20251112", type="unit")
        stale_fm.generate_tags()
        stats, written = self._run(
            tmp_path, faction_id="TAU",
            cache_page=WikiPage(fm=stale_fm, body="缓存正文"))
        assert stats["cached"] == 1
        assert len(written) == 1
        page = WikiPage.from_markdown(written[0].read_text(encoding="utf-8"))
        assert page.fm.faction == "钛帝国"
        assert "unit/钛帝国" in page.fm.tags
        assert "钛帝国十版-20251112" not in page.fm.tags
        assert "钛帝国" in str(written[0])


class TestBuildFactionFacts:
    def test_single_faction(self):
        pairs = [
            Pair(zh=None, en="Fire Warriors", canonical_id="fw",
                 faction_id="TAU", book="Test", pages=[1], confidence="exact"),
            Pair(zh="指挥官", en="Commander", canonical_id="cmd",
                 faction_id="TAU", book="Test", pages=[2], confidence="exact"),
        ]
        facts = build_faction_facts(pairs)
        assert "TAU" in facts
        # faction_slug of TAU is "tau"
        assert facts["TAU"]["faction_slug"] == "tau"
