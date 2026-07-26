# tests/test_wiki_canonical.py
"""Wahapedia CSV 解析测试（离线 fixture，不联网）。"""
from pathlib import Path

from wiki_compile.canonical import (CanonicalEntry, audit_wahapedia_csv,
                                    load_canonical, parse_wahapedia_csv)

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


class TestBareNewlineContinuation:
    """回归：legend/description 里的**裸换行**不得把一条记录劈成两行。

    Wahapedia 导出不做 CSV 引号转义，正文里可以直接出现换行。旧解析器按物理行读，
    实测 Stratagems.csv 的 THREAT‑COGITATION TARGETERS 被劈成「6 列 + 7 列」：
    前半截 phase/detachment/description 三列全空，后半截整体左移一格落成一条
    id='Shooting phase'、faction='rapid elimination.' 的垃圾行。
    """

    # 复刻真实形态：第 2 条记录的 legend 中间断行，第 3 条正常（证明续接后能收住）
    SPLIT = ("﻿faction_id|name|id|legend|phase|\n"
             "AdM|ALPHA|000001|a normal legend|Shooting phase|\n"
             "AdM|THREAT|000002|identify targets and assist in their\n"
             "rapid elimination.|Shooting phase|\n"
             "AdM|OMEGA|000003|another legend|Fight phase|\n")

    def test_continuation_merges_into_one_row(self):
        rows = parse_wahapedia_csv(self.SPLIT)
        assert len(rows) == 3
        assert [r["id"] for r in rows] == ["000001", "000002", "000003"]

    def test_continued_row_fields_not_shifted(self):
        r = parse_wahapedia_csv(self.SPLIT)[1]
        assert r["faction_id"] == "AdM"
        assert r["name"] == "THREAT"
        assert r["phase"] == "Shooting phase"
        # 换行原样留在字段里——它本来就是原文的一部分，不该被吞掉也不该改成空格
        assert r["legend"] == "identify targets and assist in their\nrapid elimination."

    def test_no_garbage_row_from_the_tail_half(self):
        rows = parse_wahapedia_csv(self.SPLIT)
        assert not [r for r in rows if r["id"] in ("Shooting phase", "Fight phase")]
        assert not [r for r in rows if r["faction_id"] == "rapid elimination."]

    def test_audit_reconciles_split_record(self):
        a = audit_wahapedia_csv(self.SPLIT)
        assert a["physical_lines"] == 4      # 物理行比真实条目多 1
        assert a["expected_rows"] == 3
        assert a["parsed_rows"] == 3
        assert a["delta"] == 0 and a["reconciled"] is True

    def test_audit_flags_unreconcilable_when_body_has_bare_pipe(self):
        # 正文混入裸 `|` → 分隔符口径失效，如实报 None 而不是猜一个数
        a = audit_wahapedia_csv("﻿id|name|\n000001|a|b|\n")
        assert a["expected_rows"] is None
        assert a["delta"] is None
        assert a["reconciled"] is False

    def test_overflowing_row_does_not_swallow_next_line(self):
        rows = parse_wahapedia_csv("﻿id|name|\n000001|a|b|\n000002|c|\n")
        assert [r["id"] for r in rows] == ["000001", "000002"]

    def test_truncated_tail_row_is_emitted_not_dropped(self):
        # 文件末尾被截断：如实产出残行（缺的列留空），静默吞掉才是真的坑
        rows = parse_wahapedia_csv("﻿id|name|phase|\n000001|a|Shooting|\n000002|b")
        assert len(rows) == 2
        assert rows[1] == {"id": "000002", "name": "b", "phase": ""}

    def test_empty_text_returns_no_rows(self):
        assert parse_wahapedia_csv("") == []
        assert audit_wahapedia_csv("")["reconciled"] is True


class TestRealCsvReconciliation:
    """真库 CSV 全量对账：11 个文件解析行数 vs 文件真实条目数，差额必须为 0。"""

    def test_every_shipped_csv_reconciles(self):
        csv_dir = Path("db_sources/wahapedia")
        files = sorted(csv_dir.glob("*.csv"))
        assert files, "db_sources/wahapedia 下没有 CSV"
        bad = {}
        for p in files:
            a = audit_wahapedia_csv(p.read_text(encoding="utf-8"))
            if not a["reconciled"]:
                bad[p.name] = a
        assert not bad, f"解析与文件条目数对不上：{bad}"

    def test_stratagems_has_one_bare_newline_record(self):
        # 差额守卫的真实靶子：物理行 1482、真实条目 1481
        a = audit_wahapedia_csv(
            (Path("db_sources/wahapedia") / "Stratagems.csv").read_text(
                encoding="utf-8"))
        assert a["physical_lines"] == a["parsed_rows"] + 1


class TestLoadCanonical:
    def test_load_skips_empty_names(self, tmp_path):
        (tmp_path / "Datasheets.csv").write_text(FIXTURE, encoding="utf-8")
        entries = load_canonical(tmp_path)
        assert entries == [
            CanonicalEntry(id="000001", name="Fire Warriors", faction_id="TAU"),
            CanonicalEntry(id="000002", name="Commander Farsight", faction_id="TAU"),
        ]
