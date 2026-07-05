"""terms.json / terms.md / review_needed.md 生成与读取测试。"""
import json

from wiki_compile.extract import EntityCandidate
from wiki_compile.pair import Pair, PairingResult
from wiki_compile.terms import load_term_aliases, write_terms

RESULT = PairingResult(
    pairs=[Pair(zh="火战士队", en="Fire Warriors", canonical_id="1",
                faction_id="TAU", book="钛书", pages=[42], confidence="exact"),
           Pair(zh=None, en="Tiger Shark", canonical_id="7",
                faction_id="TAU", book="Faction Pack Tau Empire",
                pages=[13], confidence="exact")],
    unmatched=[EntityCandidate(book="钛书", raw_heading="谜之单位",
                               name_zh="谜之单位", name_en=None, pages=[99])])


class TestWriteTerms:
    def test_writes_three_files(self, tmp_path):
        write_terms(RESULT, tmp_path)
        data = json.loads((tmp_path / "terms.json").read_text(encoding="utf-8"))
        assert data["pairs"][0]["zh"] == "火战士队"
        assert "火战士队" in (tmp_path / "terms.md").read_text(encoding="utf-8")
        assert "谜之单位" in (tmp_path / "review_needed.md").read_text(encoding="utf-8")


class TestLoadTermAliases:
    def test_roundtrip(self, tmp_path):
        write_terms(RESULT, tmp_path)
        aliases = load_term_aliases(tmp_path / "terms.json")
        assert aliases == {"火战士队": "Fire Warriors"}  # zh 为 None 的不入别名

    def test_missing_file_returns_empty(self, tmp_path):
        assert load_term_aliases(tmp_path / "nope.json") == {}

    def test_top_level_list_returns_empty(self, tmp_path):
        # 合法 JSON 但顶层非 dict（schema 错误）→ 空表，不抛异常
        f = tmp_path / "terms.json"
        f.write_text("[1, 2, 3]", encoding="utf-8")
        assert load_term_aliases(f) == {}

    def test_pairs_not_a_list_returns_empty(self, tmp_path):
        # pairs 字段类型错误（非列表）→ 空表，不抛异常
        f = tmp_path / "terms.json"
        f.write_text(json.dumps({"pairs": "oops"}), encoding="utf-8")
        assert load_term_aliases(f) == {}

    def test_non_dict_item_in_pairs_skipped(self, tmp_path):
        # pairs 列表中混入非 dict 元素 → 跳过该项，其余正常项仍被读取
        f = tmp_path / "terms.json"
        f.write_text(json.dumps({"pairs": [
            "not-a-dict",
            {"zh": "火战士队", "en": "Fire Warriors"},
        ]}, ensure_ascii=False), encoding="utf-8")
        assert load_term_aliases(f) == {"火战士队": "Fire Warriors"}
