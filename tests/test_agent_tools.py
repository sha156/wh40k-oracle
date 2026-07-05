# tests/test_agent_tools.py
"""agent/tools.py：11 个工具——已具备能力接真实实现的行为，未建模能力的诚实占位。"""
import json

import pytest

from agent import tools as agent_tools
from db_compile.build import build_database
from db_compile.entity_resolver import EntityResolver

FACTIONS_CSV = "﻿id|name|link|\nTAU|T'au Empire|https://x|\n"
DATASHEETS_CSV = (
    "﻿id|name|faction_id|source_id|legend|role|loadout|transport|virtual|"
    "leader_head|leader_footer|damaged_w|damaged_description|link|\n"
    "000000407|Commander Shadowsun|TAU|1|||||||||https://x|\n"
)

INDEX_MD = """# WH40K Wiki Index

### 钛帝国

| 类型 | 名称 | 摘要 | Updated |
|------|------|------|---------|
| unit | [影阳指挥官](factions/tau-empire/units/commander-shadowsun.md) | 钛帝国指挥官 | 2026-07-01 |
"""

ENTITY_PAGE = """---
id: tau-empire/units/commander-shadowsun
name_zh: 影阳指挥官
name_en: Commander Shadowsun
type: unit
faction: TAU
---

## 影阳指挥官

钛帝国的指挥官单位。
"""

TERMS_JSON = json.dumps({
    "source": "test",
    "pairs": [
        {"zh": "影阳指挥官", "en": "Commander Shadowsun",
         "canonical_id": "000000407", "faction_id": "TAU",
         "book": "test", "pages": [1], "confidence": "exact"},
    ],
})

FAKE_APP_PY = 'UNIT_ALIASES = {\n    "冷言": "影阳指挥官",\n}\n'

CORE_RULE_PAGE = """---
id: lethal-hits
name_zh: 致命一击
name_en: Lethal Hits
type: core-rule
---

## 致命一击 LETHAL HITS

本武器攻击时，命中暴击对目标自动造伤。
"""


def _write_wiki_fixture(tmp_path):
    wiki_root = tmp_path / "wiki"
    (wiki_root / "factions" / "tau-empire" / "units").mkdir(parents=True)
    (wiki_root / "index.md").write_text(INDEX_MD, encoding="utf-8")
    (wiki_root / "factions" / "tau-empire" / "units" / "commander-shadowsun.md").write_text(
        ENTITY_PAGE, encoding="utf-8")
    return wiki_root


def _write_core_rules_fixture(tmp_path):
    core_dir = tmp_path / "core-rules"
    core_dir.mkdir()
    (core_dir / "lethal-hits.md").write_text(CORE_RULE_PAGE, encoding="utf-8")
    return core_dir


def _write_resolver_fixture(tmp_path):
    terms_path = tmp_path / "terms.json"
    terms_path.write_text(TERMS_JSON, encoding="utf-8")
    app_path = tmp_path / "app.py"
    app_path.write_text(FAKE_APP_PY, encoding="utf-8")
    return EntityResolver(terms_path=terms_path, app_path=app_path), app_path


class TestSearchWiki:
    def test_finds_entity_by_exact_zh_name(self, tmp_path):
        wiki_root = _write_wiki_fixture(tmp_path)

        result = agent_tools.search_wiki("影阳指挥官", wiki_root=wiki_root)

        assert result["found"] is True
        assert result["page"].fm.name_en == "Commander Shadowsun"

    def test_full_text_search_when_no_exact_match(self, tmp_path):
        wiki_root = _write_wiki_fixture(tmp_path)

        result = agent_tools.search_wiki("钛帝国", wiki_root=wiki_root)

        assert result["found"] is True
        assert result["page"] is None
        assert len(result["results"]) >= 1

    def test_empty_index_reports_not_found(self, tmp_path):
        wiki_root = tmp_path / "empty_wiki"
        wiki_root.mkdir()

        result = agent_tools.search_wiki("随便什么", wiki_root=wiki_root)

        assert result["found"] is False
        assert result["note"]

    def test_unknown_query_reports_not_found(self, tmp_path):
        wiki_root = _write_wiki_fixture(tmp_path)

        result = agent_tools.search_wiki("完全不存在的东西XYZ", wiki_root=wiki_root)

        assert result["found"] is False


class TestGetEntity:
    def test_direct_hit(self, tmp_path):
        wiki_root = _write_wiki_fixture(tmp_path)

        result = agent_tools.get_entity("影阳指挥官", wiki_root=wiki_root)

        assert result["found"] is True
        assert result["resolved_via"] is None

    def test_resolves_community_alias_via_entity_resolver(self, tmp_path):
        wiki_root = _write_wiki_fixture(tmp_path)
        resolver, app_path = _write_resolver_fixture(tmp_path)

        result = agent_tools.get_entity(
            "冷言", wiki_root=wiki_root, resolver=resolver, app_path=app_path)

        assert result["found"] is True
        assert result["resolved_via"] == {"alias_target": "影阳指挥官"}

    def test_unresolvable_name_reports_not_found(self, tmp_path):
        wiki_root = _write_wiki_fixture(tmp_path)
        resolver, app_path = _write_resolver_fixture(tmp_path)

        result = agent_tools.get_entity(
            "完全不存在的名字XYZ", wiki_root=wiki_root, resolver=resolver, app_path=app_path)

        assert result["found"] is False
        assert result["page"] is None


class TestGetKeywordDefinition:
    def test_matches_by_filename_slug(self, tmp_path):
        core_dir = _write_core_rules_fixture(tmp_path)

        result = agent_tools.get_keyword_definition("lethal-hits", core_rules_dir=core_dir)

        assert result["found"] is True
        assert result["page"].fm.name_zh == "致命一击"

    def test_matches_by_zh_name(self, tmp_path):
        core_dir = _write_core_rules_fixture(tmp_path)

        result = agent_tools.get_keyword_definition("致命一击", core_rules_dir=core_dir)

        assert result["found"] is True

    def test_matches_by_en_name_case_insensitive(self, tmp_path):
        core_dir = _write_core_rules_fixture(tmp_path)

        result = agent_tools.get_keyword_definition("lethal hits", core_rules_dir=core_dir)

        assert result["found"] is True

    def test_unknown_keyword_reports_not_found(self, tmp_path):
        core_dir = _write_core_rules_fixture(tmp_path)

        result = agent_tools.get_keyword_definition("完全没听过的技能", core_rules_dir=core_dir)

        assert result["found"] is False


class TestEntityResolverTool:
    def test_resolves_alias(self, tmp_path):
        resolver, _ = _write_resolver_fixture(tmp_path)

        result = agent_tools.entity_resolver("冷言", resolver=resolver)

        assert result["canonical_id"] == "000000407"
        assert result["confidence"] == "exact"

    def test_unknown_name_returns_none(self, tmp_path):
        resolver, _ = _write_resolver_fixture(tmp_path)

        result = agent_tools.entity_resolver("完全不存在XYZ", resolver=resolver)

        assert result["canonical_id"] is None


class TestCalcPoints:
    def test_wraps_db_compile_honestly_reports_missing_cost_csv(self, tmp_path):
        csv_dir = tmp_path / "wahapedia"
        csv_dir.mkdir()
        (csv_dir / "Factions.csv").write_text(FACTIONS_CSV, encoding="utf-8")
        (csv_dir / "Datasheets.csv").write_text(DATASHEETS_CSV, encoding="utf-8")
        db_path = tmp_path / "wh40k.sqlite"
        build_database(csv_dir, db_path)

        result = agent_tools.calc_points(["000000407"], db_path=db_path)

        assert result["found"] is True
        assert result["units"][0]["points"] is None
        assert "缺" in result["units"][0]["note"]

    def test_missing_db_reports_note_instead_of_crashing(self, tmp_path):
        result = agent_tools.calc_points(["000000407"], db_path=tmp_path / "no_such.sqlite")

        assert result["found"] is False
        assert result["units"] == []


class TestRagSearch:
    def test_wraps_existing_hybrid_retrieve_read_only(self):
        class FakeApp:
            @staticmethod
            def load_resources():
                return None, object(), None, None

            @staticmethod
            def build_bm25(_vectorstore):
                return None

            @staticmethod
            def hybrid_retrieve(query, vectorstore, bm25_retriever, reranker):
                return [{"text": "示例段落", "book": "测试书", "source": "x.pdf", "page": 3}]

        result = agent_tools.rag_search("任意问题", app_module=FakeApp)

        assert result["found"] is True
        assert result["passages"][0]["book"] == "测试书"

    def test_no_vectorstore_reports_not_built(self):
        class FakeApp:
            @staticmethod
            def load_resources():
                return None, None, None, None

        result = agent_tools.rag_search("任意问题", app_module=FakeApp)

        assert result["found"] is False
        assert "ingest.py" in result["note"]

    def test_exception_degrades_to_not_found(self):
        class FakeApp:
            @staticmethod
            def load_resources():
                raise RuntimeError("模拟资源加载失败")

        result = agent_tools.rag_search("任意问题", app_module=FakeApp)

        assert result["found"] is False
        assert "异常" in result["note"]


class TestUnmodeledToolsHonestPlaceholders:
    @pytest.mark.parametrize("fn, args", [
        (agent_tools.judge_fight_order, {}),
        (agent_tools.simulate_combat, {"attacker": "a", "defender": "b"}),
        (agent_tools.validate_roster, {"roster_text": "..."}),
        (agent_tools.critique_roster, {"roster_text": "..."}),
        (agent_tools.archive_answer, {"title": "t", "content": "c"}),
    ])
    def test_returns_explicit_not_modeled_placeholder(self, fn, args):
        result = fn(**args)

        assert result["ok"] is False
        assert result["modeled"] is False
        assert "未建模" in result["note"] or "未接线" in result["note"]


class TestToolRegistry:
    def test_registry_has_all_eleven_tools(self):
        assert len(agent_tools.TOOLS) == 11
        assert len(agent_tools.TOOL_SPECS) == 11

    def test_registry_names_match_spec_signatures(self):
        expected = {
            "search_wiki", "get_entity", "get_keyword_definition",
            "judge_fight_order", "simulate_combat", "validate_roster",
            "critique_roster", "calc_points", "archive_answer",
            "rag_search", "entity_resolver",
        }
        assert set(agent_tools.TOOLS) == expected
