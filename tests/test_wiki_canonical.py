# tests/test_wiki_canonical.py
"""Wahapedia CSV 解析测试（离线 fixture，不联网）。"""
from pathlib import Path

from wiki_compile.canonical import CanonicalEntry, load_canonical, parse_wahapedia_csv

# Wahapedia 导出格式：| 分隔，行尾多一个 |，可能带 BOM
FIXTURE = "﻿id|name|faction_id|role|\n" \
          "000001|Fire Warriors|TAU|Battleline|\n" \
          "000002|Commander Farsight|TAU|Character|\n" \
          "000003||TAU|Character|\n"          # 空名行应被 load_canonical 丢弃


class TestParseCsv:
    def test_parses_pipe_delimited_with_bom(self):
        rows = parse_wahapedia_csv(FIXTURE)
        assert rows[0]["name"] == "Fire Warriors"
        assert rows[0]["faction_id"] == "TAU"
        assert len(rows) == 3

    def test_trailing_pipe_ignored(self):
        rows = parse_wahapedia_csv(FIXTURE)
        assert "" not in rows[0]  # 行尾空字段不产生空键


class TestLoadCanonical:
    def test_load_skips_empty_names(self, tmp_path):
        (tmp_path / "Datasheets.csv").write_text(FIXTURE, encoding="utf-8")
        entries = load_canonical(tmp_path)
        assert entries == [
            CanonicalEntry(id="000001", name="Fire Warriors", faction_id="TAU"),
            CanonicalEntry(id="000002", name="Commander Farsight", faction_id="TAU"),
        ]
