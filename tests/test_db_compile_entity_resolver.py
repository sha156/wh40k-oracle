# tests/test_db_compile_entity_resolver.py
"""entity_resolver：中文名/英文名/社区俗名 → canonical id（离线 fixture + 一个真实数据回归）。"""
import json
from pathlib import Path

from db_compile.entity_resolver import EntityResolver, load_unit_aliases

TERMS_JSON = json.dumps({
    "source": "test",
    "pairs": [
        {"zh": "影阳指挥官", "en": "Commander Shadowsun",
         "canonical_id": "000000407", "faction_id": "TAU",
         "book": "test", "pages": [1], "confidence": "exact"},
        {"zh": "远见指挥官", "en": "Commander Farsight",
         "canonical_id": "000000406", "faction_id": "TAU",
         "book": "test", "pages": [1], "confidence": "exact"},
    ],
})

FAKE_APP_PY = (
    "UNIT_ALIASES = {\n"
    '    "冷言": "影阳指挥官",\n'
    '    "查无此人": "不存在的规则书译名",\n'
    "}\n"
)


def _write_fixtures(tmp_path):
    terms_path = tmp_path / "terms.json"
    terms_path.write_text(TERMS_JSON, encoding="utf-8")
    app_path = tmp_path / "app.py"
    app_path.write_text(FAKE_APP_PY, encoding="utf-8")
    return terms_path, app_path


class TestLoadUnitAliases:
    def test_extracts_dict_without_executing_module(self, tmp_path):
        _, app_path = _write_fixtures(tmp_path)
        aliases = load_unit_aliases(app_path)
        assert aliases["冷言"] == "影阳指挥官"

    def test_missing_file_returns_empty(self, tmp_path):
        assert load_unit_aliases(tmp_path / "no_such_app.py") == {}


class TestEntityResolverFixture:
    def test_resolves_exact_zh_name(self, tmp_path):
        terms_path, app_path = _write_fixtures(tmp_path)
        resolver = EntityResolver(terms_path=terms_path, app_path=app_path)

        result = resolver.resolve("影阳指挥官")

        assert result.canonical_id == "000000407"
        assert result.name_en == "Commander Shadowsun"
        assert result.confidence == "exact"

    def test_resolves_exact_en_name_case_insensitive(self, tmp_path):
        terms_path, app_path = _write_fixtures(tmp_path)
        resolver = EntityResolver(terms_path=terms_path, app_path=app_path)

        result = resolver.resolve("commander shadowsun")

        assert result.canonical_id == "000000407"

    def test_resolves_community_alias_through_canonical_zh_name(self, tmp_path):
        terms_path, app_path = _write_fixtures(tmp_path)
        resolver = EntityResolver(terms_path=terms_path, app_path=app_path)

        result = resolver.resolve("冷言")

        assert result.canonical_id == "000000407"
        assert result.name_en == "Commander Shadowsun"

    def test_alias_pointing_to_unpaired_name_stays_unresolved(self, tmp_path):
        terms_path, app_path = _write_fixtures(tmp_path)
        resolver = EntityResolver(terms_path=terms_path, app_path=app_path)

        result = resolver.resolve("查无此人")

        assert result.canonical_id is None

    def test_fuzzy_match_typo(self, tmp_path):
        # 单独用只有一个词条的术语表，避免 "Commander Shadowsun"/"Commander Farsight"
        # 共享前缀导致模糊匹配出现真实的歧义候选（ambiguous 本身在别的用例里验证）。
        terms_path = tmp_path / "terms_single.json"
        terms_path.write_text(json.dumps({
            "source": "test",
            "pairs": [{"zh": "影阳指挥官", "en": "Commander Shadowsun",
                       "canonical_id": "000000407", "faction_id": "TAU",
                       "book": "test", "pages": [1], "confidence": "exact"}],
        }), encoding="utf-8")
        resolver = EntityResolver(terms_path=terms_path)

        result = resolver.resolve("Commander Shadowsu")  # 少一个字母

        assert result.canonical_id == "000000407"
        assert result.confidence == "fuzzy"

    def test_fuzzy_match_ambiguous_returns_candidates(self, tmp_path):
        terms_path, app_path = _write_fixtures(tmp_path)
        resolver = EntityResolver(terms_path=terms_path, app_path=app_path)

        result = resolver.resolve("Commander Shadowsu")  # 与两个已知英文名都相近

        assert result.canonical_id is None
        assert result.confidence == "ambiguous"
        assert len(result.candidates) >= 2

    def test_unknown_name_returns_none_confidence(self, tmp_path):
        terms_path, app_path = _write_fixtures(tmp_path)
        resolver = EntityResolver(terms_path=terms_path, app_path=app_path)

        result = resolver.resolve("完全不存在的单位名字XYZ")

        assert result.canonical_id is None
        assert result.confidence == "none"


class TestEntityResolverRealData:
    """用真实 wiki/terms.json + app.py 验证：中文单位名能解析到 canonical id
    （gnhf 停止条件③的直接验证）。"""

    def test_resolves_real_tau_unit_from_wiki_terms(self):
        repo_root = Path(__file__).parent.parent
        resolver = EntityResolver(
            terms_path=repo_root / "wiki" / "terms.json",
            app_path=repo_root / "app.py",
        )

        result = resolver.resolve("影阳指挥官")

        assert result.canonical_id == "000000407"
        assert result.name_en == "Commander Shadowsun"
        assert result.confidence == "exact"

    def test_resolves_second_real_tau_unit_from_wiki_terms(self):
        repo_root = Path(__file__).parent.parent
        resolver = EntityResolver(
            terms_path=repo_root / "wiki" / "terms.json",
            app_path=repo_root / "app.py",
        )

        result = resolver.resolve("远见指挥官")

        assert result.canonical_id == "000000406"
        assert result.name_en == "Commander Farsight"

    def test_current_unit_aliases_do_not_yet_overlap_pilot_terms(self):
        """诚实回归护栏：app.py 的 UNIT_ALIASES 是 P0 之前为其他阵营写的社区俗名，
        当前 wiki/terms.json 只配对了钛帝国/吞世者两个试点阵营（P1），二者暂无交集。
        一旦未来 wiki_compile 覆盖到这些阵营，此测试会失败，提示需要更新用例
        （而不是让 resolver 悄悄返回 None 却没人注意到）。"""
        repo_root = Path(__file__).parent.parent
        aliases = load_unit_aliases(repo_root / "app.py")
        resolver = EntityResolver(
            terms_path=repo_root / "wiki" / "terms.json",
            app_path=repo_root / "app.py",
        )

        resolved_any = any(
            resolver.resolve(nickname).canonical_id is not None
            for nickname in aliases
        )

        assert resolved_any is False
