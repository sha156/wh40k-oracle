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
