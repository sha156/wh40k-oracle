"""tests/test_audit_leftovers_r1.py — 第 1 轮审查遗留项（M1-M7 / L1-L4）的护栏。

每个 class 对应一条 finding，注释写明「不修会怎样」——日后有人回退实现，
能从失败信息直接读出后果，而不是只看到一个断言挂了。

配套报告：docs/superpowers/specs/2026-07-30-audit-round1-core-chain.md §5
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="wh40k.sqlite 不存在")


# ── R1-M1：参数类型错不该被当成「库里查不到」而静默降级 ───────────────

class TestCalcPointsParamError:
    """不修会怎样：LLM 把 unit_list 传成 dict/int 时，工具返回 found=False，
    `loop._EMPTY_CHECKS` 判空 → 当场降级 classic。模型看不到「应为列表」那句指路，
    白白丢掉一次它本来完全能自行恢复的机会。"""

    def test_param_error_is_flagged(self):
        from agent.tools import calc_points
        r = calc_points(unit_list={"name": "基里曼"})
        assert r["found"] is False
        assert r.get("param_error") is True, "参数错误必须打 param_error 标记"
        assert "列表" in r["note"], "note 要指路怎么改参，而不是只说失败"

    def test_param_error_does_not_trigger_degrade(self):
        from agent.loop import _EMPTY_CHECKS
        check = _EMPTY_CHECKS["calc_points"]
        assert check({"found": False, "units": [], "param_error": True}) is False, \
            "参数错误不是『库里没有』，判空即降级会没收模型的恢复机会"

    def test_real_misses_still_degrade(self):
        """成对负向：真正的『一个都没解析到』仍必须判空降级（基准 #109 的防线）。"""
        from agent.loop import _EMPTY_CHECKS
        check = _EMPTY_CHECKS["calc_points"]
        assert check({"found": False, "units": []}) is True
        assert check({"found": True, "units": [{"unresolved": True}]}) is True
        # 「查到了但库里没点数」是诚实答案，不许被兜底吞掉
        assert check({"found": True, "units": [{"unit_id": "x", "points": None}]}) is False


# ── R1-M2：镜像对局下 COUNTEROFFENSIVE 归属绝不能比对名字 ──────────────

class TestCounterOffensiveDirection:
    """不修会怎样：攻守同名（镜像对局）时守方问「我能不能用 CO 插队」，
    系统答「你本就先打，无需 COUNTEROFFENSIVE」——正好答反。
    这是既往那条 CRITICAL『用名字判方向』只修了 first_is_a 一半的残留。"""

    @staticmethod
    def _mirror(co_is_a=None, co_by=None, charged=False):
        """攻守同名。默认双方都不冲锋 ⇒ 同处 Remaining Combats 步（same_step=True），
        由 active player（a）先打——这正是「守方能否用 CO 插队」有意义的场景。"""
        from engines.simulator.fight_order import FighterState, judge
        a = FighterState("地狱兽", is_active_player=True, charged=charged)
        b = FighterState("地狱兽", is_active_player=False, charged=False)
        return judge(a, b, counter_offensive_by=co_by, counter_offensive_is_a=co_is_a)

    def test_mirror_with_explicit_side_answers_defender_correctly(self):
        v = self._mirror(co_is_a=False)          # b（守方）用 CO
        assert v.first_is_a is True              # a 是当前回合玩家，先打
        assert "本就先打" not in v.counter_offensive_note, \
            "守方问插队，不能答『你本就先打』——这正是 R1-M2 的错误输出"
        assert "插队" in v.counter_offensive_note

    def test_mirror_with_explicit_side_answers_attacker_correctly(self):
        v = self._mirror(co_is_a=True)           # a（先打方）用 CO
        assert "本就先打" in v.counter_offensive_note

    def test_mirror_with_only_name_discloses_instead_of_guessing(self):
        """只给名字而两边同名：名字给不出方向，必须显式披露而不是猜一个。"""
        v = self._mirror(co_by="地狱兽")
        note = v.counter_offensive_note
        assert "无法从名字判断" in note and "attacker" in note
        assert not note.startswith("地狱兽 本就先打"), "分不出方向时不许断言方向"

    def test_distinct_names_behaviour_unchanged(self):
        """成对回归：名字不同时结论与改动前一致（守方 CO → 插队说明）。"""
        from engines.simulator.fight_order import FighterState, judge
        a = FighterState("A兽", is_active_player=True, charged=True)
        b = FighterState("B兽", is_active_player=False, charged=False)
        v = judge(a, b, counter_offensive_by="B兽")
        assert "COUNTEROFFENSIVE" in v.counter_offensive_note
        v2 = judge(a, b, counter_offensive_by="A兽")
        assert "本就先打" in v2.counter_offensive_note

    def test_tool_layer_passes_side_not_name(self):
        """工具边界：ctx 给 attacker/defender 侧标识时，方向不经过名字。"""
        from agent.tools import judge_fight_order
        out = judge_fight_order({"attacker": "地狱兽", "defender": "地狱兽",
                                 "counter_offensive_by": "defender"})
        assert out["ok"] is True
        assert "本就先打" not in out["counter_offensive_note"]


# ── R1-M3：点评与验表必须给同一张军表同一个总分 ─────────────────────

class TestCritiqueTotalMatchesValidate:
    """不修会怎样：同一张军表在验表页显示 190、点评页显示 170（差额=强化点数），
    用户无从判断哪个对。判死刑的权威在 validate，点评页必须跟着它走。"""

    @needs_db
    def test_totals_agree_with_enhancement(self):
        from engines.roster import Roster, RosterUnit, validate
        from engines.roster.critique import critique
        roster = Roster("SM", "000001130", "strike_force", (
            RosterUnit("000000060", "Apothecary Biologis", 1, is_warlord=True,
                       enhancement="Eye of the Primarch"),
        ))
        v = validate(DB, roster)
        c = critique(DB, roster, n=20, seed=1)
        assert c.total_points == v.total_points, \
            "点评总分漏计强化点数 → 与验表页给出两个总分"

    @needs_db
    def test_unpriced_enhancement_is_surfaced_in_critique(self):
        """无法定价的强化在点评页也要说出来，否则差额查无实据。"""
        from engines.roster import Roster, RosterUnit
        from engines.roster.critique import critique
        roster = Roster("SM", "000001130", "strike_force", (
            RosterUnit("000000060", "Apothecary Biologis", 1, is_warlord=True,
                       enhancement="NotARealEnhancement"),
        ))
        c = critique(DB, roster, n=20, seed=1)
        assert any("未知" in s for s in c.summary)


# ── R1-M4：中文层异常不许把诚实披露一起吞掉 ──────────────────────────

class TestDatasheetZhFailureIsLogged:
    """不修会怎样：一个裸 `except Exception: pass` 同时罩住中文层加载与两源冲突检测，
    任一环节抛异常都会让『数值以官方英文为准』这句披露静默消失，且无任何日志。"""

    @needs_db
    def test_zh_layer_failure_logs_warning(self, monkeypatch, caplog):
        import agent.tools as tools
        import db_compile.blacklibrary as bl

        def boom(*a, **k):
            raise RuntimeError("模拟中文层表损坏")

        monkeypatch.setattr(bl, "load_zh_detail", boom)
        with caplog.at_level(logging.WARNING, logger="agent.tools"):
            out = tools.get_datasheet("Intercessor Squad")
        assert out.get("found") is True, "中文层挂掉不该影响英文权威块"
        assert any("中文层加载失败" in r.getMessage() for r in caplog.records), \
            "except 分支必须留痕（CLAUDE.md 明令），不许静默 pass"

    @needs_db
    def test_conflict_detection_failure_is_disclosed(self, monkeypatch, caplog):
        """冲突检测本身挂了 ⇒ 无法断言两源一致，必须如实说，不许沉默。"""
        import agent.tools as tools
        import db_compile.datasheet as dsmod

        real_load = None
        try:
            from db_compile.blacklibrary import load_zh_detail as real_load
        except Exception:  # pragma: no cover
            pytest.skip("黑图书馆中文层不可用")

        def boom(*a, **k):
            raise RuntimeError("模拟 diff 失败")

        monkeypatch.setattr(dsmod, "diff_core_stats", boom)
        # 找一个确实有中文层的单位
        with caplog.at_level(logging.WARNING, logger="agent.tools"):
            out = tools.get_datasheet("Intercessor Squad")
        if real_load(DB, out["datasheet"]["unit_id"]):
            assert "一致性检测未能完成" in out.get("note", ""), \
                "检测挂了却不吭声 = 让用户以为两源已核对过"


# ── R1-M5：守方消费点白名单只准有一份真源 ───────────────────────────

class TestTargetConsumedSingleSource:
    """不修会怎样：判据被手抄成第二份 if 链，将来只往其中一份加消费点，
    被丢弃的守方效果就不再被披露——『报告里没有』会被读成『没有被丢弃』。"""

    def test_judgement_reads_the_whitelist(self):
        from engines.simulator.effect_params import (TARGET_CONSUMED,
                                                     _target_effect_consumed)

        class E:
            def __init__(self, phase, op):
                self.phase, self.op, self.source = phase, op, "t"

        for phase, op in TARGET_CONSUMED:
            assert _target_effect_consumed(E(phase, op)) is True, \
                f"{phase}+{op} 在白名单里却被判成未消费"
        assert _target_effect_consumed(E("charge", "nonsense")) is False

    def test_new_consumption_point_is_picked_up_automatically(self, monkeypatch):
        """把一个新消费点塞进真源集合，判据必须立刻认它——手抄版做不到这件事。"""
        import engines.simulator.effect_params as ep

        class E:
            def __init__(self, phase, op):
                self.phase, self.op, self.source = phase, op, "t"

        assert ep._target_effect_consumed(E("save", "brand_new_op")) is False
        monkeypatch.setattr(ep, "TARGET_CONSUMED",
                            ep.TARGET_CONSUMED | {("save", "brand_new_op")})
        assert ep._target_effect_consumed(E("save", "brand_new_op")) is True

    def test_disclosure_text_lists_every_consumption_point(self):
        """披露文案曾漏掉 4 个已接通的消费点——文案与实现必须说同一件事。"""
        from engines.simulator.effect_params import (TARGET_CONSUMED,
                                                     _consumed_points_label)
        label = _consumed_points_label()
        for phase, op in TARGET_CONSUMED:
            assert op in label, f"消费点 {phase}+{op} 没出现在披露文案里"
        for op in ("wound", "bs_improve", "t_improve", "ap_improve"):
            assert op in label


# ── R1-M6：parse_ap 与 norm_stat_int 对称，解析不了要吼 ────────────────

class TestParseApSymmetry:
    """不修会怎样：`parse_ap('-1*')` 给 0 而 `norm_stat_int('-1*')` 给 -1，
    同一个文件两套标准；任何解析不了的 AP 一律静默当『无穿甲』，
    与 `(\\d+) pts` 对千分位零容忍是同一款失效形状。"""

    @pytest.mark.parametrize("raw,expect", [
        ("-1", -1), ("-2", -2), ("0", 0), ("-", 0), ("-0", 0), ("", 0), (None, 0),
        ("-1*", -1),        # `*` 脚注：norm_stat_int 早就认，parse_ap 从前不认
        ("‑1", -1),    # U+2011 非断字连字符
        ("−1", -1),    # U+2212 数学减号
        ("–1", -1),    # U+2013 en dash
    ])
    def test_parses_like_norm_stat_int(self, raw, expect):
        from engines.simulator.parse import parse_ap
        assert parse_ap(raw) == expect

    def test_unparseable_warns_instead_of_silent_zero(self, caplog):
        from engines.simulator.parse import parse_ap
        with caplog.at_level(logging.WARNING, logger="engines.simulator.parse"):
            assert parse_ap("完全不是数字") == 0
        assert any("无法解析 AP" in r.getMessage() for r in caplog.records), \
            "静默归零 = 归零发生在无人知晓的地方"

    def test_real_db_values_unchanged(self):
        """成对回归：真库里那 9 种取值的解析结果一个都不许变。"""
        from engines.simulator.parse import parse_ap
        assert [parse_ap(v) for v in
                ("0", "-1", "-2", "-3", "-4", "-5", "-6", "-", "-0")] == \
               [0, -1, -2, -3, -4, -5, -6, 0, 0]


# ── R1-M7：主检索空手不该把规则层保底一起扔掉 ────────────────────────

class TestRulesFloorSurvivesEmptyMerge:
    """不修会怎样：FAISS/BM25 任一侧抛异常导致 merged 为空时，
    已经查到的 layer=rules 保底结果被无条件 `return []` 丢掉——
    与 #117『降级把前面成功的工具结果一并作废』是同一个形状。"""

    @staticmethod
    def _fake_store(rules_docs):
        from langchain_core.documents import Document

        class Store:
            def similarity_search(self, query, k=None, fetch_k=None, filter=None):
                if (filter or {}).get("layer") == "rules":
                    return [Document(page_content=t,
                                     metadata={"layer": "rules", "book": "Core Rules",
                                               "source": "core.pdf", "page": i})
                            for i, t in enumerate(rules_docs)]
                return []          # 主检索空手
        return Store()

    def test_rules_floor_is_returned_when_main_retrieval_is_empty(self):
        import app
        out = app.hybrid_retrieve("深入打击", self._fake_store(["DEEP STRIKE 11.03"]),
                                  bm25_retriever=None, reranker=None)
        assert out, "规则层保底还活着，不该被一起丢掉"
        assert "DEEP STRIKE" in out[0]["text"]

    def test_still_empty_when_nothing_found_at_all(self):
        """成对负向：两边都空手时仍然返回空，不许凭空造结果。"""
        import app
        assert app.hybrid_retrieve("xyz", self._fake_store([]),
                                   bm25_retriever=None, reranker=None) == []


# ── R1-L1：工具返回截断要保尾（数值多在尾部）────────────────────────

class TestToolResultTruncationKeepsTail:
    """不修会怎样：get_datasheet 叠加中文层后整包超 4000 字，只留前 4000 字，
    而武器表/点数/同名消歧披露都在尾部——答案本身被切掉。"""

    def test_tail_is_preserved(self):
        from agent.llm_client import _render_loop_message as _to_api_message
        payload = "头" * 5000 + "【尾部关键数值】"      # 必须真的超过 4000 字才会触发截断
        msg = _to_api_message({"role": "tool", "name": "get_datasheet",
                               "content": payload})
        assert "【尾部关键数值】" in msg["content"]
        assert "中间省略" in msg["content"]

    def test_short_content_untouched(self):
        from agent.llm_client import _render_loop_message as _to_api_message
        msg = _to_api_message({"role": "tool", "name": "t", "content": "短内容"})
        assert msg["content"].endswith("短内容")


# ── R1-L2/L3：refine 缓存的诚实性口径 ────────────────────────────────

class TestRefineMetaHonesty:
    """L2 不修会怎样：LLM 失败后落的兜底页 meta 写 verify_ok=True——
    一个从没被校验过的页自称通过，_verify_warn_pages 的口径失真。
    L3 不修会怎样：分母含永不产出 .md 的空白页，覆盖率数学上到不了 1.0，
    空白页多的 PDF 被 --chinese-only 反复重扫。"""

    def test_fallback_page_is_not_marked_verified(self):
        src = Path("llm_refine.py").read_text(encoding="utf-8")
        assert '"verify_ok": None, "fallback": True' in src, \
            "兜底页不许自称 verify_ok=True（它压根没跑过 verify_numbers）"

    def test_coverage_excludes_blank_pages(self, tmp_path):
        from llm_refine import _refine_coverage
        book = tmp_path / "book"
        book.mkdir()
        for n in (1, 2, 3):
            (book / f"page_{n:03d}.md").write_text("x", encoding="utf-8")
        (book / "skipped_pages.json").write_text(json.dumps([4, 5]), encoding="utf-8")
        # 5 页 PDF：3 页 refine 过 + 2 页空白 ⇒ 覆盖率必须是 1.0 而不是 0.6
        assert _refine_coverage(book, 5) == pytest.approx(1.0)

    def test_coverage_falls_back_when_registry_missing(self, tmp_path):
        from llm_refine import _refine_coverage
        book = tmp_path / "book"
        book.mkdir()
        (book / "page_001.md").write_text("x", encoding="utf-8")
        assert _refine_coverage(book, 5) == pytest.approx(0.2)

    def test_coverage_survives_corrupt_registry(self, tmp_path):
        from llm_refine import _refine_coverage
        book = tmp_path / "book"
        book.mkdir()
        (book / "page_001.md").write_text("x", encoding="utf-8")
        (book / "skipped_pages.json").write_text("{坏掉的 json", encoding="utf-8")
        assert _refine_coverage(book, 5) == pytest.approx(0.2), \
            "登记表损坏应退回总页数口径（低估），不许抛异常也不许虚报"


# ── R1-L4：增量去重跨相对/绝对路径要能匹配 ──────────────────────────

class TestIncrementalDedupPathNormalization:
    """不修会怎样：默认 `--data-dir data`（相对路径）建的索引，
    改用绝对路径重跑时 source 原样字符串匹配不上 ⇒ 删 0 条 ⇒ 新旧 chunk 并存，
    正是 H3 当初要防的场景。"""

    def test_relative_and_absolute_are_the_same_key(self):
        from ingest import _source_key
        assert _source_key("data/a.pdf") == _source_key(str(Path("data/a.pdf").resolve()))

    def test_none_source_is_not_matched(self):
        from ingest import _source_key
        assert _source_key(None) == ""

    def test_delete_stale_chunks_matches_across_path_forms(self):
        from ingest import delete_stale_chunks

        class Doc:
            def __init__(self, source):
                self.metadata = {"source": source}

        class Store:
            def __init__(self):
                self.docstore = type("D", (), {})()
                self.docstore._dict = {
                    "1": Doc("data/a.pdf"),
                    "2": Doc(str(Path("data/b.pdf").resolve())),
                    "3": Doc("data/c.pdf"),
                }
                self.deleted = []

            def delete(self, ids):
                self.deleted = ids

        store = Store()
        # 传绝对路径，索引里存的是相对路径 —— 归一前删 0 条
        removed = delete_stale_chunks(store, {str(Path("data/a.pdf").resolve()),
                                              "data/b.pdf"})
        assert removed == 2, "相对/绝对路径混用时必须仍能删掉旧 chunk"
        assert set(store.deleted) == {"1", "2"}
