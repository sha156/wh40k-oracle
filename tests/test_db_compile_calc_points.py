# tests/test_db_compile_calc_points.py
"""calc_points：P2 阶段无点数 CSV，须诚实报告缺失原因而非编造数值。"""
from db_compile.build import build_database
from db_compile.calc_points import (MISSING_COST_NOTE, UNKNOWN_UNIT_NOTE,
                                    calc_points)

FACTIONS_CSV = "﻿id|name|link|\nTAU|T'au Empire|https://x|\n"
DATASHEETS_CSV = (
    "﻿id|name|faction_id|source_id|legend|role|loadout|transport|virtual|"
    "leader_head|leader_footer|damaged_w|damaged_description|link|\n"
    "000000407|Commander Shadowsun|TAU|1|||||||||https://x|\n"
)


def _build_db(tmp_path):
    csv_dir = tmp_path / "wahapedia"
    csv_dir.mkdir()
    (csv_dir / "Factions.csv").write_text(FACTIONS_CSV, encoding="utf-8")
    (csv_dir / "Datasheets.csv").write_text(DATASHEETS_CSV, encoding="utf-8")
    db_path = tmp_path / "wh40k.sqlite"
    build_database(csv_dir, db_path)
    return db_path


class TestCalcPoints:
    def test_known_unit_without_cost_csv_reports_missing_note(self, tmp_path):
        db_path = _build_db(tmp_path)

        result = calc_points(db_path, ["000000407"])

        assert len(result) == 1
        assert result[0].unit_id == "000000407"
        assert result[0].name_en == "Commander Shadowsun"
        assert result[0].points is None
        assert result[0].note == MISSING_COST_NOTE

    def test_unknown_unit_id_reports_not_found(self, tmp_path):
        db_path = _build_db(tmp_path)

        result = calc_points(db_path, ["no-such-id"])

        assert result[0].points is None
        assert result[0].note == UNKNOWN_UNIT_NOTE

    def test_points_used_once_cost_csv_is_available(self, tmp_path):
        """回归护栏：一旦 units.points_json 有数据，calc_points 必须真正读取并返回，
        而不是无脑套用 MISSING_COST_NOTE（防止未来接入点数 CSV 时此函数没跟着更新）。"""
        import json
        import sqlite3

        db_path = _build_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "UPDATE units SET points_json = ? WHERE id = '000000407'",
            (json.dumps({"points": 95}),))
        conn.commit()
        conn.close()

        result = calc_points(db_path, ["000000407"])

        assert result[0].points == 95
        assert result[0].note is None
