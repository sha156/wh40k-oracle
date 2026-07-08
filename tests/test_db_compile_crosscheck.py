# tests/test_db_compile_crosscheck.py
"""crosscheck：BSData↔Wahapedia 属性交叉校验的纯函数与聚合逻辑。"""
from db_compile.crosscheck import (
    cmp_val,
    cross_check,
    match_key,
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
        return {
            "chaos lord": {"name": "Chaos Lord", "M": '6"', "T": "4", "SV": "3+", "W": "4"},
            "defiler": {"name": "Defiler", "M": '12"', "T": "10", "SV": "3+", "W": "10"},
            "orphan unit": {"name": "Orphan Unit", "M": '5"', "T": "3", "SV": "5+", "W": "1"},
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
        assert d == {"name": "Defiler", "field": "M", "wahapedia": '12"', "bsdata": '14"'}

    def test_unmatched_listed(self):
        rep = cross_check(self._wah(), self._bs())
        assert rep.unmatched_wahapedia == ["Orphan Unit"]

    def test_empty_wahapedia_safe(self):
        rep = cross_check({}, self._bs())
        assert rep.match_rate == 0.0
        assert rep.agreement_rate == 0.0
