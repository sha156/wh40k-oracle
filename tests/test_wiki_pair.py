"""中英配对测试：精确匹配 → 阵营推断 → 阵营内模糊匹配。"""
from wiki_compile.canonical import CanonicalEntry
from wiki_compile.extract import EntityCandidate
from wiki_compile.pair import Pair, PairingResult, normalize_name, pair_entities

CANONICAL = [
    CanonicalEntry("1", "Fire Warriors", "TAU"),
    CanonicalEntry("2", "Commander Farsight", "TAU"),
    CanonicalEntry("3", "Ta'unar Supremacy Armour", "TAU"),
    CanonicalEntry("4", "Hormagaunts", "TYR"),
]


def _cand(zh, en, book="钛书"):
    return EntityCandidate(book=book, raw_heading=(zh or "") + " " + (en or ""),
                           name_zh=zh, name_en=en, pages=[1])


class TestNormalize:
    def test_case_and_typographic_apostrophe(self):
        # 弯引号（PDF提取常见）与直引号归一
        assert normalize_name("TA'UNAR SUPREMACY ARMOUR") == \
               normalize_name("Ta'unar Supremacy Armour")

    def test_extra_spaces_collapsed(self):
        assert normalize_name("FIRE  WARRIORS ") == "FIRE WARRIORS"


class TestPairEntities:
    def test_exact_match(self):
        r = pair_entities([_cand("火战士队", "FIRE WARRIORS")], CANONICAL)
        p = r.pairs[0]
        assert (p.zh, p.en, p.canonical_id, p.confidence) == (
            "火战士队", "Fire Warriors", "1", "exact")
        assert r.unmatched == []

    def test_fuzzy_restricted_to_book_faction(self):
        # 同书先有精确命中 TAU → 推断书=TAU → 模糊匹配只在 TAU 内找
        ents = [_cand("火战士队", "FIRE WARRIORS"),
                _cand("风暴烈阳指挥官", "COMANDER FARSIGHT")]  # 拼写缺字母 → 走模糊匹配
        r = pair_entities(ents, CANONICAL)
        confs = {p.en: p.confidence for p in r.pairs}
        assert confs["Commander Farsight"] == "fuzzy"

    def test_no_english_name_goes_unmatched(self):
        r = pair_entities([_cand("某中文条目", None)], CANONICAL)
        assert r.pairs == []
        assert r.unmatched[0].name_zh == "某中文条目"

    def test_no_close_match_goes_unmatched(self):
        r = pair_entities([_cand("完全无关", "TOTALLY UNRELATED THING")], CANONICAL)
        assert r.unmatched != []
