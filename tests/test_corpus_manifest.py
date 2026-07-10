"""corpus_manifest：书名 → edition/layer 分层（11 版迁移 S1）。"""
import json
from pathlib import Path

from corpus_manifest import classify_book, edition_layer_tag, load_manifest

REPO_ROOT = Path(__file__).parent.parent


def _manifest(tmp_path, data):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return load_manifest(p)


class TestClassifyBook:
    def test_exact_name_wins_over_prefix(self, tmp_path):
        m = _manifest(tmp_path, {
            "books": {"Faction Pack Special": {"edition": "11", "layer": "rules"}},
            "prefixes": [{"prefix": "Faction Pack", "edition": "11", "layer": "overlay"}],
        })
        assert classify_book("Faction Pack Special", m)["layer"] == "rules"

    def test_prefix_rule(self, tmp_path):
        m = _manifest(tmp_path, {
            "prefixes": [{"prefix": "Faction Pack", "edition": "11", "layer": "overlay"}],
        })
        assert classify_book("Faction Pack Aeldari", m) == {
            "edition": "11", "layer": "overlay"}

    def test_unlisted_falls_back_to_defaults(self, tmp_path):
        m = _manifest(tmp_path, {"defaults": {"edition": "10", "layer": "codex-base"}})
        assert classify_book("星际战士10版中文", m) == {
            "edition": "10", "layer": "codex-base"}

    def test_missing_file_returns_builtin_defaults(self, tmp_path):
        m = load_manifest(tmp_path / "no_such.json")
        assert classify_book("任意书", m) == {"edition": "10", "layer": "codex-base"}

    def test_corrupt_file_returns_builtin_defaults(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not json", encoding="utf-8")
        m = load_manifest(p)
        assert classify_book("任意书", m)["layer"] == "codex-base"


class TestRealManifest:
    """真实 corpus_manifest.json 的关键映射回归（11 版语料分层的真源约定）。"""

    def setup_method(self):
        self.m = load_manifest(REPO_ROOT / "corpus_manifest.json")

    def test_core_rules_is_11_rules(self):
        assert classify_book("Core Rules - New 40K Core Rules", self.m) == {
            "edition": "11", "layer": "rules"}

    def test_faction_pack_is_11_overlay(self):
        assert classify_book("Faction Pack World Eaters", self.m) == {
            "edition": "11", "layer": "overlay"}

    def test_mfm_points_and_balance(self):
        assert classify_book("6月4日分数中文", self.m)["layer"] == "points"
        assert classify_book("6月4日平衡版中午", self.m)["layer"] == "balance"

    def test_chinese_codex_defaults_to_base(self):
        assert classify_book("星际战士10版中文", self.m) == {
            "edition": "10", "layer": "codex-base"}

    def test_blacklibrary_entry(self):
        assert classify_book("黑图书馆", self.m)["layer"] == "codex-base"


class TestEditionLayerTag:
    def test_edition_11_rules(self):
        assert edition_layer_tag("11", "rules") == "11版·核心规则"

    def test_edition_10_codex_base(self):
        assert edition_layer_tag("10", "codex-base") == "十版·codex兵牌基底"

    def test_unknown_layer_passes_through(self):
        assert edition_layer_tag("11", "misc-x") == "11版·misc-x"
