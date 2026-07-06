# tests/test_db_compile_build.py
"""db_compile.build：CSV → wh40k.sqlite（离线 fixture，不联网）。"""
import json
import sqlite3

from db_compile.build import EXPECTED_CSV, build_database

FACTIONS_CSV = ("﻿id|name|link|\n"
                 "TAU|T'au Empire|https://wahapedia.ru/.../t-au-empire|\n"
                 "AC|Adeptus Custodes|https://wahapedia.ru/.../adeptus-custodes|\n")

DATASHEETS_CSV = (
    "﻿id|name|faction_id|source_id|legend|role|loadout|transport|virtual|"
    "leader_head|leader_footer|damaged_w|damaged_description|link|\n"
    "000000407|Commander Shadowsun|TAU|1|legend text|Character|loadout text|||"
    "||||https://wahapedia.ru/.../commander-shadowsun|\n"
    "000001478|Commander In Enforcer Battlesuit|TAU|1||Character|||||||"
    "|https://wahapedia.ru/.../commander-in-enforcer|\n"
)

TERMS_JSON = json.dumps({
    "source": "wahapedia wh40k10ed",
    "pairs": [
        {"zh": "影阳指挥官", "en": "Commander Shadowsun",
         "canonical_id": "000000407", "faction_id": "TAU",
         "book": "test", "pages": [1], "confidence": "exact"},
    ],
})


def _write_fixture_csv_dir(tmp_path):
    csv_dir = tmp_path / "wahapedia"
    csv_dir.mkdir()
    (csv_dir / "Factions.csv").write_text(FACTIONS_CSV, encoding="utf-8")
    (csv_dir / "Datasheets.csv").write_text(DATASHEETS_CSV, encoding="utf-8")
    return csv_dir


class TestBuildDatabase:
    def test_imports_factions_and_datasheets(self, tmp_path):
        csv_dir = _write_fixture_csv_dir(tmp_path)
        db_path = tmp_path / "wh40k.sqlite"

        report = build_database(csv_dir, db_path)

        assert report.row_counts["factions"] == 2
        assert report.row_counts["datasheets"] == 2
        assert report.row_counts["units"] == 2

        conn = sqlite3.connect(str(db_path))
        try:
            cur = conn.execute("SELECT name FROM factions WHERE id = 'TAU'")
            assert cur.fetchone() == ("T'au Empire",)
            cur = conn.execute(
                "SELECT name, faction_id FROM datasheets WHERE id = '000000407'")
            assert cur.fetchone() == ("Commander Shadowsun", "TAU")
        finally:
            conn.close()

    def test_creates_all_core_tables_even_when_empty(self, tmp_path):
        csv_dir = _write_fixture_csv_dir(tmp_path)
        db_path = tmp_path / "wh40k.sqlite"

        build_database(csv_dir, db_path)

        conn = sqlite3.connect(str(db_path))
        try:
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            for expected in ("factions", "datasheets", "units", "models",
                              "weapons", "abilities", "stratagems",
                              "detachments", "aliases"):
                assert expected in tables
            # 无源 CSV 的表只建结构，行数为 0
            assert conn.execute("SELECT COUNT(*) FROM models").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM abilities").fetchone()[0] == 0
        finally:
            conn.close()

    def test_reports_missing_csv_honestly(self, tmp_path):
        csv_dir = _write_fixture_csv_dir(tmp_path)
        db_path = tmp_path / "wh40k.sqlite"

        report = build_database(csv_dir, db_path)

        assert "Datasheets_models_cost.csv" in report.missing_csv
        assert "Datasheets.csv" not in report.missing_csv
        assert "Factions.csv" not in report.missing_csv
        assert set(report.missing_csv) < set(EXPECTED_CSV)

    def test_units_get_name_zh_from_terms_json(self, tmp_path):
        csv_dir = _write_fixture_csv_dir(tmp_path)
        db_path = tmp_path / "wh40k.sqlite"
        terms_path = tmp_path / "terms.json"
        terms_path.write_text(TERMS_JSON, encoding="utf-8")

        build_database(csv_dir, db_path, terms_path=terms_path)

        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute(
                "SELECT name_zh, points_json, keywords_json FROM units "
                "WHERE id = '000000407'").fetchone()
            assert row[0] == "影阳指挥官"
            # 点数/词条 CSV 未下载：诚实留 NULL，不编造
            assert row[1] is None
            assert row[2] is None
            # 无中文配对的单位：name_zh 应为 NULL 而非空字符串
            row2 = conn.execute(
                "SELECT name_zh FROM units WHERE id = '000001478'").fetchone()
            assert row2[0] is None
        finally:
            conn.close()

    def test_rebuild_is_idempotent(self, tmp_path):
        csv_dir = _write_fixture_csv_dir(tmp_path)
        db_path = tmp_path / "wh40k.sqlite"

        build_database(csv_dir, db_path)
        report2 = build_database(csv_dir, db_path)

        assert report2.row_counts["datasheets"] == 2
