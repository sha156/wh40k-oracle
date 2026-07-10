# tests/test_db_compile_crosscheck.py
"""crosscheck：BSData↔Wahapedia 属性交叉校验的纯函数与聚合逻辑 + 读库/读文件路径。"""
import sqlite3

from db_compile.crosscheck import (
    cmp_val,
    cross_check,
    load_wahapedia_units,
    match_key,
    parse_bsdata_units,
    run,
    stats_agree,
)


class TestCmpVal:
    def test_strips_quote_and_space_noise(self):
        # 同值不同写法应相等，不报假分歧
        assert cmp_val('20+"') == cmp_val('20"+')
        assert cmp_val('10"') == cmp_val("10")
        assert cmp_val('6"') == cmp_val("6 ")

    def test_real_difference_survives(self):
        assert cmp_val('12"') != cmp_val('14"')
        assert cmp_val("2+") != cmp_val("3+")


class TestMatchKey:
    def test_case_insensitive(self):
        assert match_key("Abaddon The Despoiler") == match_key("Abaddon the Despoiler")

    def test_trims(self):
        assert match_key("  Chaos Lord  ") == "chaos lord"


class TestStatsAgree:
    def test_format_noise_agrees(self):
        a = {"M": '20+"', "T": "5", "SV": "2+", "W": "9"}
        b = {"M": '20"+', "T": "5", "SV": "2+", "W": "9"}
        assert stats_agree(a, b)

    def test_real_diff_disagrees(self):
        a = {"M": '12"', "T": "8", "SV": "3+", "W": "10"}
        b = {"M": '14"', "T": "8", "SV": "3+", "W": "10"}
        assert not stats_agree(a, b)


class TestCrossCheck:
    def _wah(self):
        # Wahapedia 侧 value 是 list：同 key 可挂多个跨阵营同名单位（不折叠）
        return {
            "chaos lord": [{"name": "Chaos Lord", "faction_id": "CSM",
                            "M": '6"', "T": "4", "SV": "3+", "W": "4"}],
            "defiler": [{"name": "Defiler", "faction_id": "CSM",
                         "M": '12"', "T": "10", "SV": "3+", "W": "10"}],
            "orphan unit": [{"name": "Orphan Unit", "faction_id": "TYR",
                             "M": '5"', "T": "3", "SV": "5+", "W": "1"}],
        }

    def _bs(self):
        return {
            # 同值不同写法 → 一致
            "chaos lord": {"name": "Chaos Lord", "M": "6", "T": "4", "SV": "3+", "W": "4"},
            # M 真分歧 → 进 discrepancies
            "defiler": {"name": "Defiler", "M": '14"', "T": "10", "SV": "3+", "W": "10"},
            # orphan unit 不在 BSData
        }

    def test_counts_and_rates(self):
        rep = cross_check(self._wah(), self._bs())
        assert rep.wahapedia_total == 3
        assert rep.matched == 2  # chaos lord + defiler
        assert rep.agreed == 1   # 仅 chaos lord
        assert rep.match_rate == round(2 / 3 * 100, 1)
        assert rep.agreement_rate == 50.0

    def test_discrepancy_detail(self):
        rep = cross_check(self._wah(), self._bs())
        assert len(rep.discrepancies) == 1
        d = rep.discrepancies[0]
        assert d == {"name": "Defiler", "faction": "CSM", "field": "M",
                     "wahapedia": '12"', "bsdata": '14"'}

    def test_unmatched_listed(self):
        rep = cross_check(self._wah(), self._bs())
        assert rep.unmatched_wahapedia == ["Orphan Unit"]

    def test_empty_wahapedia_safe(self):
        rep = cross_check({}, self._bs())
        assert rep.match_rate == 0.0
        assert rep.agreement_rate == 0.0

    def test_duplicated_names_all_compared_and_disclosed(self):
        # 跨阵营同名（如 Ministorum Priest）：两条都要进比对池并披露，绝不静默折叠
        wah = {
            "shared priest": [
                {"name": "Shared Priest", "faction_id": "AS",
                 "M": '6"', "T": "3", "SV": "5+", "W": "3"},
                {"name": "Shared Priest", "faction_id": "AM",
                 "M": '5"', "T": "3", "SV": "5+", "W": "3"},
            ],
        }
        bs = {"shared priest": {"name": "Shared Priest",
                                "M": "6", "T": "3", "SV": "5+", "W": "3"}}
        rep = cross_check(wah, bs)
        assert rep.wahapedia_total == 2   # 不是 1——两条都计
        assert rep.matched == 2           # 两条都参与比对
        assert rep.agreed == 1            # AS 版一致
        assert rep.duplicated_names == ["Shared Priest"]
        # AM 版的 M 分歧被逮到（旧实现折叠后另一条永不进比对池）
        assert len(rep.discrepancies) == 1
        d = rep.discrepancies[0]
        assert (d["faction"], d["field"], d["wahapedia"]) == ("AM", "M", '5"')


def _make_wah_db(tmp_path):
    """按真实 schema 建最小 units+models 库。"""
    db = tmp_path / "wh40k.sqlite"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        "CREATE TABLE units(id TEXT PRIMARY KEY, faction_id TEXT, name_en TEXT,"
        " name_zh TEXT, points_json TEXT, keywords_json TEXT, version TEXT);"
        "CREATE TABLE models(unit_id TEXT, name TEXT, m TEXT, t TEXT, sv TEXT,"
        " invuln TEXT, w TEXT, ld TEXT, oc TEXT, count_options_json TEXT);")
    conn.executemany(
        "INSERT INTO units(id, faction_id, name_en) VALUES(?,?,?)",
        [("u1", "AS", "Shared Priest"),
         ("u2", "AM", "Shared Priest"),
         ("u3", "CSM", "Chaos Lord")])
    # u1 两个 model 档位：首行（rowid 最小）才是基准档
    conn.executemany(
        "INSERT INTO models(unit_id, name, m, t, sv, w) VALUES(?,?,?,?,?,?)",
        [("u1", "Priest", '6"', "3", "5+", "3"),
         ("u1", "Priest on Bike", '12"', "4", "5+", "4"),
         ("u2", "Priest", '5"', "3", "5+", "3"),
         ("u3", "Chaos Lord", '6"', "4", "3+", "4")])
    conn.commit()
    conn.close()
    return db


class TestLoadWahapediaUnits:
    """此前零测试的读库函数：确定性首档位 + 同名不折叠。"""

    def test_first_model_row_is_deterministic(self, tmp_path):
        out = load_wahapedia_units(_make_wah_db(tmp_path))
        lord = out["chaos lord"][0]
        assert (lord["M"], lord["T"], lord["SV"], lord["W"]) == ('6"', "4", "3+", "4")
        # u1 取首行 Priest 档（M=6"），不是骑行档（M=12"）——
        # 旧 GROUP BY 裸列取哪行是 SQLite 未定义行为
        u1 = [u for u in out["shared priest"] if u["faction_id"] == "AS"][0]
        assert u1["M"] == '6"'

    def test_cross_faction_same_name_not_folded(self, tmp_path):
        out = load_wahapedia_units(_make_wah_db(tmp_path))
        priests = out["shared priest"]
        assert len(priests) == 2
        assert {u["faction_id"] for u in priests} == {"AS", "AM"}
        # 两条属性各自独立（AM 版 M=5"）
        by_fid = {u["faction_id"]: u for u in priests}
        assert by_fid["AM"]["M"] == '5"'


_GOOD_CAT = """<catalogue xmlns="http://www.battlescribe.net/schema/catalogueSchema">
  <sharedProfiles>
    <profile name="Chaos Lord" typeName="Unit">
      <characteristics>
        <characteristic name="M">6"</characteristic>
        <characteristic name="T">4</characteristic>
        <characteristic name="SV">3+</characteristic>
        <characteristic name="W">4</characteristic>
      </characteristics>
    </profile>
  </sharedProfiles>
</catalogue>
"""


class TestParseBsdataSkippedFiles:
    def test_bad_cat_recorded_not_silently_skipped(self, tmp_path):
        (tmp_path / "good.cat").write_text(_GOOD_CAT, encoding="utf-8")
        (tmp_path / "bad.cat").write_text("<catalogue><未闭合", encoding="utf-8")
        units, skipped = parse_bsdata_units(tmp_path)
        assert "chaos lord" in units
        assert units["chaos lord"]["M"] == '6"'
        assert len(skipped) == 1
        assert skipped[0]["path"].endswith("bad.cat")
        assert skipped[0]["error"]  # 带具体解析错误信息

    def test_all_good_no_skipped(self, tmp_path):
        (tmp_path / "good.cat").write_text(_GOOD_CAT, encoding="utf-8")
        units, skipped = parse_bsdata_units(tmp_path)
        assert skipped == []
        assert len(units) == 1


class TestRunIntegration:
    def test_report_carries_skipped_and_duplicates(self, tmp_path):
        db = _make_wah_db(tmp_path)
        bsdir = tmp_path / "bsdata"
        bsdir.mkdir()
        (bsdir / "good.cat").write_text(_GOOD_CAT, encoding="utf-8")
        (bsdir / "bad.cat").write_text("not xml at all <", encoding="utf-8")
        rep = run(bsdir, db)
        assert rep.wahapedia_total == 3
        assert len(rep.skipped_files) == 1
        assert rep.skipped_files[0]["path"].endswith("bad.cat")
        assert rep.duplicated_names == ["Shared Priest"]
        # Chaos Lord 命中 BSData 且一致
        assert rep.matched == 1 and rep.agreed == 1
