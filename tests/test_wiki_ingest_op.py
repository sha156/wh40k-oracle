"""wiki_engine/operations/ingest_op.py 测试：find_affected_pages 级联命中。"""
from __future__ import annotations

from pathlib import Path

import pytest

from wiki_engine.models import WikiPage, WikiPageFrontmatter
from wiki_engine.operations.ingest_op import find_affected_pages


class TestFindAffectedPages:
    """CRITICAL #3：写盘→回读含多条长路径 raw 的页面，find_affected_pages 能正确命中。"""

    def _write_page(self, wiki_root: Path, raw: list) -> WikiPageFrontmatter:
        fm = WikiPageFrontmatter(
            id="tau-empire/units/fire-warriors",
            name_zh="火战士队",
            name_en="Fire Warriors",
            faction="tau-empire",
            type="unit",
            raw=raw,
        )
        units = wiki_root / "factions" / "tau-empire" / "units"
        units.mkdir(parents=True)
        (units / "fire-warriors.md").write_text(
            WikiPage(fm=fm, body="正文。").to_markdown(), encoding="utf-8")
        return fm

    def test_hits_page_via_long_raw_paths(self, tmp_path):
        wiki = tmp_path / "wiki"
        raw = [
            "data_refined/钛帝国十版CODEX-20251112/page_001.md",
            "data_refined/钛帝国十版CODEX-20251112/page_002.md",
            "data_refined/Faction Pack Tau Empire/page_010.md",
        ]
        fm = self._write_page(wiki, raw)

        affected = find_affected_pages(
            [Path("data_refined/钛帝国十版CODEX-20251112/page_002.md")], wiki)
        assert fm.id in affected

    def test_unrelated_file_no_hit(self, tmp_path):
        wiki = tmp_path / "wiki"
        self._write_page(wiki, ["data_refined/钛帝国十版CODEX-20251112/page_001.md"])

        affected = find_affected_pages(
            [Path("data_refined/其他书/page_099.md")], wiki)
        assert affected == []


class TestIngestPairingPath:
    """M：pairing_path 参数化 + 找不到时打印实际查找路径 + affected_pages 接线。"""

    def test_missing_pairing_prints_lookup_path(self, tmp_path, monkeypatch, capsys):
        from wiki_engine.operations.ingest_op import ingest
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        refined = tmp_path / "data_refined"
        refined.mkdir()
        missing = tmp_path / "nope" / "pairing.json"

        result = ingest([], refined, wiki, tmp_path / "cache",
                        pairing_path=missing)
        out = capsys.readouterr().out
        assert "配对文件不存在" in out
        assert str(missing.resolve()) in out
        # 后续步骤照常执行（不崩），日志已写
        assert (wiki / "log.md").exists()
        assert result["stats"] == {}

    def test_affected_pages_written_to_log(self, tmp_path, monkeypatch):
        """本次实际写入的页面路径要进 log.md 的 Affected Pages 列。"""
        import json
        from dataclasses import asdict

        from wiki_compile.pair import Pair
        from wiki_engine.operations.ingest_op import ingest
        from wiki_engine.synthesize import (
            SYNTH_PROMPT_VERSION,
            _cache_key,
            _save_cache,
            collect_source_fragments,
        )
        from wiki_compile.extract import EntityCandidate

        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        refined = tmp_path / "data_refined"
        (refined / "Book A").mkdir(parents=True)
        (refined / "Book A" / "page_001.md").write_text(
            "## 火战士队 FIRE WARRIORS\n属性内容", encoding="utf-8")

        pair = Pair(zh="火战士队", en="FIRE WARRIORS",
                    canonical_id="tau/units/fire-warriors", faction_id="TAU",
                    book="Book A", pages=[1], confidence="exact")
        pairing_path = tmp_path / "wiki_build" / "pairing.json"
        pairing_path.parent.mkdir(parents=True)
        pairing_path.write_text(json.dumps(
            {"pairs": [asdict(pair)], "unmatched": []},
            ensure_ascii=False), encoding="utf-8")

        # 预填缓存 → client=None 也能从缓存写出页面
        entity = EntityCandidate(book="Book A",
                                 raw_heading="火战士队 FIRE WARRIORS",
                                 name_zh="火战士队", name_en="FIRE WARRIORS",
                                 pages=[1])
        fragments = collect_source_fragments(entity, refined)
        key = _cache_key(SYNTH_PROMPT_VERSION, pair.canonical_id, fragments)
        fm = WikiPageFrontmatter(id=pair.canonical_id, name_zh="火战士队",
                                 name_en="FIRE WARRIORS", faction="钛帝国",
                                 type="unit")
        cache_dir = tmp_path / "cache"
        _save_cache(cache_dir, key, WikiPage(fm=fm, body="正文。"))

        wiki = tmp_path / "wiki"
        ingest([Path("data_refined/Book A/page_001.md")],
               refined, wiki, cache_dir, pairing_path=pairing_path)

        log = (wiki / "log.md").read_text(encoding="utf-8")
        # 最后一行 ingest 日志的 Affected Pages 列包含写入页面路径
        ingest_lines = [ln for ln in log.splitlines() if "| ingest |" in ln]
        assert ingest_lines, "log.md 必须有 ingest 条目"
        assert "fire-warriors" in ingest_lines[-1]
