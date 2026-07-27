# tests/test_agent_tools.py
"""agent/tools.py：12 个工具——已具备能力接真实实现的行为，未建模能力的诚实占位。"""
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


def _write_ambiguous_resolver_fixture(tmp_path):
    """同名跨阵营（Helbrute×2）→ resolve() 报 ambiguous 并回填 `名字 (阵营)` 候选串。"""
    terms_path = tmp_path / "terms_ambiguous.json"
    terms_path.write_text(json.dumps({
        "source": "test",
        "pairs": [
            {"zh": "地狱魔像CSM", "en": "Helbrute", "canonical_id": "000000001",
             "faction_id": "CSM", "book": "test", "pages": [1], "confidence": "exact"},
            {"zh": "地狱魔像WE", "en": "Helbrute", "canonical_id": "000000002",
             "faction_id": "WE", "book": "test", "pages": [1], "confidence": "exact"},
        ],
    }), encoding="utf-8")
    app_path = tmp_path / "app_ambiguous.py"
    app_path.write_text("UNIT_ALIASES = {}\n", encoding="utf-8")
    return EntityResolver(terms_path=terms_path, app_path=app_path)


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

    def test_ambiguous_note_orders_recheck_not_bounce_to_user(self, tmp_path, monkeypatch):
        """ambiguous 被 loop 判为「非空」→ 经典链兜底不触发，此时 note 若让模型反问用户，
        这条路径就是「不降级也不作答」的死胡同（基准 #63：0 检索源、judge 判答非所问 ❌）。
        note 必须指挥模型逐个候选重查。"""
        wiki_root = _write_wiki_fixture(tmp_path)
        monkeypatch.setattr(agent_tools, "entity_resolver", lambda name, resolver=None: {
            "canonical_id": None, "name_en": None,
            "confidence": "ambiguous", "candidates": ["甲指挥官", "乙指挥官"]})

        result = agent_tools.get_entity("无匹配统帅ZZZ", wiki_root=wiki_root)

        assert result["found"] is False
        note = result["note"]
        assert "甲指挥官" in note and "乙指挥官" in note      # 候选一个不少地透出
        assert "重新调用 get_entity" in note                  # 指挥模型自己去查证
        # 反问用户只能是查证候选之后的兜底，不能是首选动作
        assert "需向用户反问确认" not in note
        assert note.index("重新调用 get_entity") < note.index("才反问用户")

    def test_ambiguous_still_counts_as_non_empty_for_loop(self, tmp_path, monkeypatch):
        """评审 #25 通道不能因上面的措辞调整而被改回「空结果 → 降级 classic」。"""
        from agent.loop import _is_empty_result

        wiki_root = _write_wiki_fixture(tmp_path)
        monkeypatch.setattr(agent_tools, "entity_resolver", lambda name, resolver=None: {
            "canonical_id": None, "name_en": None,
            "confidence": "ambiguous", "candidates": ["甲指挥官", "乙指挥官"]})

        result = agent_tools.get_entity("无匹配统帅ZZZ", wiki_root=wiki_root)

        assert _is_empty_result("get_entity", result) is False


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


class TestEntityResolverEmptyPathHonesty:
    """空手返回必须把「这条名字映射没命中」和「这个东西不存在」的界线说穿（#63/#109 同型）。

    entity_resolver 此前是本通道里唯一一个空手时连 note 都没有的工具：ambiguous 被
    loop._EMPTY_CHECKS 判为非空（评审 #25）→ 不降级，模型拿到裸 dict 无任何下一步指引。
    """

    def test_unresolved_note_gives_next_step_and_forbids_negative_assertion(self, tmp_path):
        resolver, _ = _write_resolver_fixture(tmp_path)

        result = agent_tools.entity_resolver("完全不存在XYZ", resolver=resolver)

        note = result["note"]
        assert "≠" in note                                    # 界线说穿
        assert "禁止" in note and "不存在" in note             # 明令禁止否定性断言
        assert "get_datasheet" in note and "get_entity" in note  # 指出下一步换哪个工具

    def test_ambiguous_note_orders_recheck_not_bounce_to_user(self, tmp_path):
        resolver = _write_ambiguous_resolver_fixture(tmp_path)

        result = agent_tools.entity_resolver("Helbrute", resolver=resolver)

        assert result["canonical_id"] is None
        assert len(result["candidates"]) == 2
        note = result["note"]
        assert "原样" in note                                  # 候选串可回填重查
        assert "退回给用户" in note                            # 反问只能是查证后的兜底

    def test_note_does_not_change_loop_empty_verdicts(self, tmp_path):
        """加 note 不得动判空口径：ambiguous 仍非空（评审 #25），彻底解析失败仍判空降级。"""
        from agent.loop import _is_empty_result

        ambiguous = agent_tools.entity_resolver(
            "Helbrute", resolver=_write_ambiguous_resolver_fixture(tmp_path))
        resolver, _ = _write_resolver_fixture(tmp_path)
        miss = agent_tools.entity_resolver("完全不存在XYZ", resolver=resolver)

        assert _is_empty_result("entity_resolver", ambiguous) is False
        assert _is_empty_result("entity_resolver", miss) is True


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
        assert "无法计算点数" in result["units"][0]["note"]

    def test_missing_db_reports_note_instead_of_crashing(self, tmp_path):
        result = agent_tools.calc_points(["000000407"], db_path=tmp_path / "no_such.sqlite")

        assert result["found"] is False
        assert result["units"] == []

    def test_string_unit_list_wrapped_not_split_per_char(self, tmp_path):
        # M#4：LLM 把 unit_list 传成单个字符串时包成 [str]，
        # 不再被逐字符拆成 9 个"单位"胡乱查询
        csv_dir = tmp_path / "wahapedia"
        csv_dir.mkdir()
        (csv_dir / "Factions.csv").write_text(FACTIONS_CSV, encoding="utf-8")
        (csv_dir / "Datasheets.csv").write_text(DATASHEETS_CSV, encoding="utf-8")
        db_path = tmp_path / "wh40k.sqlite"
        build_database(csv_dir, db_path)

        result = agent_tools.calc_points("000000407", db_path=db_path)

        assert result["found"] is True
        assert len(result["units"]) == 1  # 一个整体单位名，而非 9 个字符
        assert result["units"][0]["unit_id"] == "000000407"

    def test_non_list_unit_list_returns_param_error(self, tmp_path):
        # M#4：非列表也非字符串 → 明确参数错误，不裸崩也不硬查
        result = agent_tools.calc_points(12345, db_path=tmp_path / "no_such.sqlite")

        assert result["ok"] is False
        assert result["found"] is False
        assert result["units"] == []
        assert "unit_list" in result["note"]

    def _fixture_db(self, tmp_path):
        csv_dir = tmp_path / "wahapedia"
        csv_dir.mkdir()
        (csv_dir / "Factions.csv").write_text(FACTIONS_CSV, encoding="utf-8")
        (csv_dir / "Datasheets.csv").write_text(DATASHEETS_CSV, encoding="utf-8")
        db_path = tmp_path / "wh40k.sqlite"
        build_database(csv_dir, db_path)
        return db_path

    def test_chinese_name_is_resolved_to_id_not_reported_as_unknown(self, tmp_path):
        """基准 #109：底层是纯 id 查表，中文名一律「未找到该 unit id」。
        名字解析必须由这层包装补上，否则模型拿到的就是一次全空返回。"""
        db_path = self._fixture_db(tmp_path)
        resolver, _ = _write_resolver_fixture(tmp_path)

        result = agent_tools.calc_points(["冷言"], db_path=db_path, resolver=resolver)

        unit = result["units"][0]
        assert unit["unit_id"] == "000000407"          # 中文名真的查到了这一行
        assert unit.get("unresolved") is not True
        assert unit["resolved_via"]["canonical_id"] == "000000407"
        assert "unresolved" not in result

    def test_unknown_name_note_forbids_negative_assertion(self, tmp_path):
        """**工具查不到 ≠ 该单位不存在**。基准 #109 的硬错就是模型把这次查询失败
        升级成了「泰坦军团不是 40K 阵营、四个泰坦无官方点数」的否定性事实断言
        （而库=官网，四个点数都在）。note 必须当场把这条界线说穿并指路重查。"""
        db_path = self._fixture_db(tmp_path)
        resolver, _ = _write_resolver_fixture(tmp_path)

        result = agent_tools.calc_points(
            ["完全不存在XYZ"], db_path=db_path, resolver=resolver)

        assert result["units"][0]["unresolved"] is True
        assert result["unresolved"] == ["完全不存在XYZ"]
        for note in (result["note"], result["units"][0]["note"]):
            assert "查不到 ≠" in note                    # 明确否认「查不到=不存在」
            assert "否定性断言" in note                   # 明确禁止该输出形态
            assert "get_datasheet" in note               # 给出可执行的重查路径
            # 工具自己绝不能给出「不存在/无官方点数」的结论——只能说没解析到
            assert "该单位在库中不存在" not in note

    def test_all_names_unresolved_counts_as_empty_for_loop(self, tmp_path):
        """一个都没解析到 → 判空降级 rag_search 兜底，别把空手留给模型自由发挥。"""
        from agent.loop import _is_empty_result

        db_path = self._fixture_db(tmp_path)
        resolver, _ = _write_resolver_fixture(tmp_path)

        allmiss = agent_tools.calc_points(
            ["完全不存在XYZ", "也不存在ABC"], db_path=db_path, resolver=resolver)
        partial = agent_tools.calc_points(
            ["冷言", "完全不存在XYZ"], db_path=db_path, resolver=resolver)

        assert _is_empty_result("calc_points", allmiss) is True
        # 「查到了但库里没点数」是诚实答案，不该被兜底吞掉
        assert _is_empty_result("calc_points", partial) is False

    def test_resolver_failure_does_not_crash_the_whole_call(self, tmp_path):
        """解析器炸了只该让那一个名字变 unresolved，不能把整次算分带崩。"""
        db_path = self._fixture_db(tmp_path)

        class _Boom:
            def resolve(self, name):
                raise RuntimeError("resolver 挂了")

        result = agent_tools.calc_points(["随便什么名"], db_path=db_path, resolver=_Boom())

        assert result["found"] is True
        assert result["units"][0]["unresolved"] is True


@pytest.mark.skipif(not agent_tools.DB_PATH.exists(), reason="需要 db/wh40k.sqlite")
class TestCalcPointsRealDbTitanRegression:
    """基准 #109 的真库钉子：一次问四个泰坦，四个中文名必须全部查到官方点数。

    gold 来自官方 MFM 实时站 titan-legions 页（2026-07-27 快照），库内四行与之逐条一致。
    """

    TITANS = {"战犬泰坦": 1100, "掠夺者泰坦": 2200,
              "天罚战争使者泰坦": 2600, "战将泰坦": 3500}

    def test_four_titans_all_resolved_with_official_points(self):
        result = agent_tools.calc_points(list(self.TITANS))

        assert "unresolved" not in result
        assert len(result["units"]) == 4          # 问四个就要回四个，不许漏项
        got = {u["query"]: u["points"] for u in result["units"]}
        assert got == self.TITANS


def _mk_same_name_db(tmp_path, zh_alias_target="000004"):
    """造一张「同名跨阵营」库：Helbrute × 4 阵营各一行 + 一个只指向其中一行的中文别名。

    这正是真库的形状——中文索引是「中文名 → 单个 cid」的扁平表，所以中文名查询会稳稳
    落到四选一里的某一张（基准 #118）。另加一个同阵营重复行的单位，钉住「重印不算歧义」。
    """
    import json
    import sqlite3

    db = tmp_path / "wh40k.sqlite"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        "CREATE TABLE factions(id TEXT,name TEXT);"
        "CREATE TABLE datasheets(id TEXT,name TEXT,faction_id TEXT);"
        "CREATE TABLE units(id TEXT,faction_id TEXT,name_en TEXT,name_zh TEXT,"
        "points_json TEXT,keywords_json TEXT,version TEXT);"
        "CREATE TABLE models(unit_id TEXT,name TEXT,m TEXT,t TEXT,sv TEXT,"
        "invuln TEXT,w TEXT,ld TEXT,oc TEXT,base TEXT,count_options_json TEXT);"
        "CREATE TABLE weapons(id TEXT,unit_id TEXT,name_zh TEXT,name_en TEXT,"
        "range TEXT,a TEXT,bs_ws TEXT,s TEXT,ap TEXT,d TEXT,keywords_json TEXT);"
        "CREATE TABLE aliases(alias TEXT,canonical_id TEXT,lang TEXT);"
    )
    for fid, name in (("CSM", "Chaos Space Marines"), ("DG", "Death Guard"),
                      ("TS", "Thousand Sons"), ("WE", "World Eaters")):
        conn.execute("INSERT INTO factions VALUES(?,?)", (fid, name))
    rows = (("000001", "CSM", 130), ("000002", "DG", 110),
            ("000003", "TS", 110), ("000004", "WE", 120))
    for uid, fid, cost in rows:
        conn.execute("INSERT INTO datasheets VALUES(?,'Helbrute',?)", (uid, fid))
        conn.execute("INSERT INTO units VALUES(?,?,'Helbrute','地狱兽',?,NULL,NULL)",
                     (uid, fid, json.dumps({"points": cost, "items": [{"cost": cost}]})))
        conn.execute("INSERT INTO models VALUES(?,'Helbrute','6\"','9','2+','-','8','7','1','60mm',NULL)",
                     (uid,))
    # 同阵营重印（上游按「书」建模）——不是跨阵营歧义，不该触发消歧披露
    for uid in ("000010", "000011"):
        conn.execute("INSERT INTO datasheets VALUES(?,'Terminator Squad','CSM')", (uid,))
        conn.execute("INSERT INTO units VALUES(?,'CSM','Terminator Squad','终结者小队',?,NULL,NULL)",
                     (uid, json.dumps({"points": 180, "items": [{"cost": 180}]})))
    conn.execute("INSERT INTO aliases VALUES('地狱兽',?,'zh')", (zh_alias_target,))
    conn.execute("INSERT INTO aliases VALUES('终结者小队','000010','zh')")
    conn.commit()
    conn.close()
    return db


def _resolver_for(db):
    from db_compile.entity_resolver import EntityResolver

    return EntityResolver(db_path=db)


class TestSameNameCrossFactionDisambiguation:
    """基准 #118：地狱兽 / Helbrute 在库里是 4 张各自独立的兵牌，点数并不相同。

    旧实现只把四选一里的那一张返回给模型（中文名索引是扁平表，四选一照报 exact），
    模型于是答「地狱兽当前点数为 120 分」——一个数字、不说阵营（gold 判错情形 ①）。
    修法必须同时躲开另两种判错：② 因歧义拒答/反问（#63 方向），③ 凭记忆补数（#109 方向），
    所以下面既断言「已查到的那个数值仍在」，也断言「四个阵营的点数全都给了模型」。
    """

    EXPECTED = {"Helbrute (CSM)": 130, "Helbrute (DG)": 110,
                "Helbrute (TS)": 110, "Helbrute (WE)": 120}

    def test_get_datasheet_zh_name_discloses_all_four_factions(self, tmp_path):
        db = _mk_same_name_db(tmp_path)

        result = agent_tools.get_datasheet("地狱兽", db_path=db,
                                           resolver=_resolver_for(db))

        # ② 反面：照常给出兵牌，不因歧义降级成 found=False
        assert result["found"] is True
        siblings = result["same_name_other_factions"]
        assert {s["candidate"]: s["points"] for s in siblings} == self.EXPECTED
        # ③ 反面：四个点数都由库给出，模型无需（也不许）凭记忆补
        assert all(s["points"] is not None for s in siblings)
        assert sum(s["is_the_one_answered_above"] for s in siblings) == 1
        assert "必须消歧" in result["note"]

    def test_calc_points_zh_name_keeps_value_and_adds_all_factions(self, tmp_path):
        db = _mk_same_name_db(tmp_path)

        result = agent_tools.calc_points(["地狱兽"], db_path=db,
                                          resolver=_resolver_for(db))

        unit = result["units"][0]
        assert unit["points"] == 120           # 已查到的数值不许因为消歧而消失
        assert {s["candidate"]: s["points"]
                for s in unit["same_name_other_factions"]} == self.EXPECTED
        assert result["same_name_cross_faction"] == ["地狱兽"]

    def test_calc_points_en_name_expands_candidates_into_points(self, tmp_path):
        """英文名多命中此前只回候选、一个点数都不给——模型只能反问或凭记忆填数。"""
        db = _mk_same_name_db(tmp_path)

        result = agent_tools.calc_points(["Helbrute"], db_path=db,
                                          resolver=_resolver_for(db))

        unit = result["units"][0]
        assert unit["ambiguous"] is True
        assert {s["candidate"]: s["points"]
                for s in unit["same_name_other_factions"]} == self.EXPECTED
        assert "unresolved" not in result      # 有数据可给，就不是「没查到」

    def test_same_faction_reprint_is_not_treated_as_ambiguous(self, tmp_path):
        """同 name_en 同阵营的重印行（duplicate-units-audit）不是跨阵营歧义，别误报。"""
        db = _mk_same_name_db(tmp_path)

        result = agent_tools.calc_points(["终结者小队"], db_path=db,
                                          resolver=_resolver_for(db))

        assert result["units"][0]["points"] == 180
        assert "same_name_other_factions" not in result["units"][0]
        assert "same_name_cross_faction" not in result

    def test_plain_canonical_id_input_is_unchanged(self, tmp_path):
        """纯 id 入参是军表/web 的既有约定，行为不许被这次消歧改动波及。"""
        db = _mk_same_name_db(tmp_path)

        result = agent_tools.calc_points(["000004"], db_path=db,
                                          resolver=_resolver_for(db))

        assert result == {"found": True, "units": [
            {"unit_id": "000004", "name_en": "Helbrute", "points": 120, "note": None}]}


@pytest.mark.skipif(not agent_tools.DB_PATH.exists(), reason="需要 db/wh40k.sqlite")
class TestSameNameCrossFactionRealDb:
    """基准 #118 的真库钉子：四张 Helbrute 兵牌的官方点数必须一次全给到模型。"""

    def test_helbrute_four_factions_points_from_real_db(self):
        result = agent_tools.get_datasheet("地狱兽")

        assert result["found"] is True
        got = {s["faction"]: s["points"]
               for s in result["same_name_other_factions"]}
        assert got == {"CSM": 130, "DG": 110, "TS": 110, "WE": 120}


class TestDefaultResolverSingletonThreadSafety:
    """M#7：无锁单例竞态——并发首调只允许构造一次 EntityResolver。"""

    def test_concurrent_first_call_constructs_once(self, monkeypatch):
        import threading
        import time

        constructed = []

        class SlowResolver:
            def __init__(self, **kwargs):
                constructed.append(1)
                time.sleep(0.05)  # 拉大竞态窗口

        monkeypatch.setattr(agent_tools, "EntityResolver", SlowResolver)
        monkeypatch.setattr(agent_tools, "_default_resolver", None)

        barrier = threading.Barrier(6)
        results = []

        def worker():
            barrier.wait()
            results.append(agent_tools._get_default_resolver())

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(constructed) == 1  # 双检锁：只构造一次
        assert all(r is results[0] for r in results)  # 拿到同一实例


class TestGetDatasheet:
    def test_missing_db_reports_note_instead_of_crashing(self, tmp_path):
        result = agent_tools.get_datasheet("Chaos Lord", db_path=tmp_path / "no_such.sqlite")

        assert result["found"] is False
        assert result["datasheet"] is None
        assert "wh40k.sqlite" in result["note"]

    def test_returns_statblock_for_known_unit(self, tmp_path):
        import json
        import sqlite3

        db = tmp_path / "wh40k.sqlite"
        conn = sqlite3.connect(str(db))
        conn.executescript(
            "CREATE TABLE factions(id TEXT,name TEXT);"
            "CREATE TABLE datasheets(id TEXT,name TEXT,faction_id TEXT);"
            "CREATE TABLE units(id TEXT,faction_id TEXT,name_en TEXT,name_zh TEXT,"
            "points_json TEXT,keywords_json TEXT,version TEXT);"
            "CREATE TABLE models(unit_id TEXT,name TEXT,m TEXT,t TEXT,sv TEXT,"
            "invuln TEXT,w TEXT,ld TEXT,oc TEXT,base TEXT,count_options_json TEXT);"
            "CREATE TABLE weapons(id TEXT,unit_id TEXT,name_zh TEXT,name_en TEXT,"
            "range TEXT,a TEXT,bs_ws TEXT,s TEXT,ap TEXT,d TEXT,keywords_json TEXT);"
        )
        conn.execute("INSERT INTO factions VALUES('CSM','Chaos Space Marines')")
        conn.execute("INSERT INTO datasheets VALUES('929','Chaos Lord','CSM')")
        conn.execute("INSERT INTO units VALUES('929','CSM','Chaos Lord',NULL,?,NULL,NULL)",
                     (json.dumps({"points": 85, "items": [{"cost": 85}]}),))
        conn.execute("INSERT INTO models VALUES('929','Chaos Lord','6\"','4','3+','4','4','6+','1','40mm',NULL)")
        conn.commit()
        conn.close()

        result = agent_tools.get_datasheet("Chaos Lord", db_path=db)

        assert result["found"] is True
        ds = result["datasheet"]
        assert ds["name_en"] == "Chaos Lord"
        assert ds["models"][0]["t"] == "4"
        assert ds["points_min"] == 85


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


class TestRagSearchFailureStatesAreDistinguishable:
    """rag_search 是唯一一个空手结果一定会被模型看到的工具（loop 的降级分支显式排除了它），
    所以「检索管线坏了」和「语料里零命中」必须能被区分——否则工具故障会被写成
    「档案里没有这条规则」的否定性事实断言（#109 同型）。"""

    @staticmethod
    def _app_returning(passages):
        class FakeApp:
            @staticmethod
            def load_resources():
                return None, object(), None, None

            @staticmethod
            def build_bm25(_vectorstore):
                return None

            @staticmethod
            def hybrid_retrieve(query, vectorstore, bm25_retriever, reranker):
                return passages

        return FakeApp

    def test_zero_hit_note_forbids_negative_assertion_and_gives_next_step(self):
        result = agent_tools.rag_search("任意问题", app_module=self._app_returning([]))

        assert result["found"] is False
        assert not result.get("error")            # 检索跑通了，只是零命中
        note = result["note"]
        assert "≠" in note and "禁止" in note
        assert "get_datasheet" in note            # 指出下一步换哪个工具

    def test_pipeline_failure_is_flagged_as_error_not_as_missing_content(self):
        class FakeApp:
            @staticmethod
            def load_resources():
                raise RuntimeError("模拟资源加载失败")

        result = agent_tools.rag_search("任意问题", app_module=FakeApp)

        assert result["error"] is True
        assert "不是" in result["note"]           # 明说这不是「语料里没有」

    def test_unbuilt_store_is_flagged_as_error_too(self):
        class FakeApp:
            @staticmethod
            def load_resources():
                return None, None, None, None

        result = agent_tools.rag_search("任意问题", app_module=FakeApp)

        assert result["error"] is True
        assert "环境故障" in result["note"]

    def test_successful_hit_carries_no_error_flag(self):
        """负向成对：正常命中不许被打上 error，否则模型会把有效结果当故障丢掉。"""
        app = self._app_returning([{"text": "t", "book": "b", "source": "s", "page": 1}])

        result = agent_tools.rag_search("任意问题", app_module=app)

        assert result["found"] is True
        assert not result.get("error")


class TestUnmodeledToolsHonestPlaceholders:
    @pytest.mark.parametrize("fn, args", [
        # simulate_combat（P4-e）/ judge_fight_order（P5-e）已建模，移出未建模占位清单
        # （见 test_simulator_wiring 的 judge_fight_order 真实判定测试）
        (agent_tools.validate_roster, {"roster_text": "..."}),
        (agent_tools.critique_roster, {"roster_text": "..."}),
        (agent_tools.archive_answer, {"title": "t", "content": "c"}),
    ])
    def test_returns_explicit_not_modeled_placeholder(self, fn, args):
        result = fn(**args)

        assert result["ok"] is False
        assert result["modeled"] is False
        assert "未建模" in result["note"] or "未接线" in result["note"]

    @pytest.mark.parametrize("fn", [agent_tools.validate_roster,
                                    agent_tools.critique_roster])
    def test_roster_stub_note_is_current(self, fn):
        # gnhf 审查模块 5 M3：P6 已于 2026-07-14 上线，占位文案不许再说「计划于 P6」
        # ——要把用户引导到军表实验室页签，而非陈述过时假事实
        note = fn(roster_text="...")["note"]
        assert "计划于" not in note
        assert "军表实验室" in note


class TestToolRegistry:
    def test_registry_has_all_tools(self):
        assert len(agent_tools.TOOLS) == 12
        assert len(agent_tools.TOOL_SPECS) == 12

    def test_registry_names_match_spec_signatures(self):
        expected = {
            "search_wiki", "get_entity", "get_keyword_definition",
            "judge_fight_order", "simulate_combat", "validate_roster",
            "critique_roster", "calc_points", "get_datasheet", "archive_answer",
            "rag_search", "entity_resolver",
        }
        assert set(agent_tools.TOOLS) == expected
